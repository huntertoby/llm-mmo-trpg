"""武器小特性（Phase 3-24a1，``docs/design/08-裝備.md`` 8.11）。

每個特性都是 ``content/weapons.yaml`` 武器資料上的參數，這裡只讀參數、不寫死數值：

- 斧 ``armor_break``：普攻命中後，目標帶 ``armor_broken`` 狀態（防禦值降低、持續 N 回合）。
- 錘 ``knockback``：普攻命中後沿攻擊方向把目標推 N 格（沿用推擊與撞擊規則）。
- 權杖 ``blessing``：普攻命中時，最近的隊友（不含自己與召喚物）回復 HP。
- 圖騰杖 ``summon_dice_bonus``：召喚者的召喚物普攻多加 N 顆傷害骰（:func:`attack_dice`）。
- 鞭 ``entangle``（Phase 3I-1）：普攻命中後，目標帶 ``entangled``（下回合移動點數減少，
  :func:`entangle_effect`）。鐮刀 ``reap`` 在 :func:`trpg.engine.modifiers.damage_permille`，
  拳套 ``counter`` 在 :func:`trpg.engine.reactions.hit_reactions`。

遠程武器（Phase 3-24a2）：

- 弩 ``pierce_line``：普攻之後，同一直線上的後方敵人也被擊中（:func:`pierce_line_targets`）；
  ``ignore_height`` 在 :func:`trpg.engine.rules.combat.situational_modifier`；
- 火槍 ``magazine``：開火用掉子彈（:func:`spend_ammo`），裝填是 ``Reload`` 動作；
  ``gunshot``：開火讓隱蔽的自己被揭露（:func:`gunshot_reveals`）；``steady``、``range_mod``、
  ``ignore_cover``、``armor_pierce_permille`` 在 :mod:`trpg.engine.rules.weapons` 與命中判定。

矛的 ``reach``（藉機攻擊範圍）在 :func:`trpg.engine.reactions.opportunity_attacks`，弓的 ``lob``
（拋射）在 :func:`trpg.engine.rules.geometry.has_line_of_sight`。
"""

from __future__ import annotations

from trpg.content.battle import Dice, SummonHitRule
from trpg.content.rules import SummonInfusion
from trpg.engine.attack_element import effective_attack_element
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CreateSurfaceEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    PushEffect,
)
from trpg.engine.gear.enhance import gear_on_hit_statuses
from trpg.engine.ids import ARMOR_BROKEN, BLEED, ENTANGLED, PRONE, REVEALED
from trpg.engine.infusion import active_infusions, template_of
from trpg.engine.maneuvers import contest
from trpg.engine.rules.combat import attack_reach, is_concealed
from trpg.engine.rules.forms import natural_bleed
from trpg.engine.rules.geometry import XY, axis_direction, bresenham, has_line_of_sight, manhattan
from trpg.engine.state import BattleState, UnitState
from trpg.shared.types import Attribute, Surface

__all__ = [
    "TRIP_ATTR",
    "apply_hit_traits",
    "attack_dice",
    "blessing_target",
    "chain_targets",
    "entangle_effect",
    "gunshot_reveals",
    "height_permille",
    "pierce_line_targets",
    "spend_ammo",
]


def attack_dice(state: BattleState, attacker: UnitState, *, backstab: bool = False) -> Dice:
    """普攻的傷害骰：武器的骰子；召喚物另加召喚者武器的 ``summon_dice_bonus`` 顆同面數的骰
    （圖騰杖的統御；召喚者已不在場時不加）。``backstab``：這次是背刺，加上武器的
    ``backstab_dice`` 顆（匕首的背刺強化，Phase 3-32a）。"""
    dice = attacker.weapon.dice
    if backstab and attacker.weapon.backstab_dice > 0:
        dice = Dice(count=dice.count + attacker.weapon.backstab_dice, sides=dice.sides)
    if attacker.owner_id is None:
        return dice
    owner = state.units.get(attacker.owner_id)
    if owner is None:
        return dice
    bonus = owner.weapon.summon_dice_bonus
    return dice if bonus <= 0 else Dice(count=dice.count + bonus, sides=dice.sides)


def blessing_target(state: BattleState, attacker: UnitState) -> UnitState | None:
    """祝禱的對象：離 ``attacker`` 最近的隊友（不含自己與召喚物；同距離取單位 ID 較小者）。"""
    allies = [
        u
        for u in state.living_units()
        if u.team is attacker.team and u.id != attacker.id and not u.is_summon
    ]
    if not allies:
        return None
    return min(allies, key=lambda u: (manhattan(u.xy, attacker.xy), u.id))


def _infusion_effects(
    ctx: Ctx, attacker: UnitState, target: UnitState, infusions: tuple[SummonInfusion, ...]
) -> list[EffectBase]:
    """召喚物生效的灌注關鍵字（3-33b、3-33e1）在普攻命中後附加的狀態、表面、額外傷害與絆倒。"""
    batch: list[EffectBase] = []
    if not target.alive:
        return batch
    for infusion in infusions:
        if infusion.status is not None:
            batch.append(
                ApplyStatusEffect(
                    source_id=attacker.id,
                    target_id=target.id,
                    status_id=infusion.status,
                    duration=infusion.duration,
                )
            )
        if infusion.surface is not None:
            batch.append(
                CreateSurfaceEffect(
                    source_id=attacker.id,
                    pos=target.xy,
                    surface=infusion.surface,
                    team=attacker.team,
                )
            )
        if infusion.extra_damage is not None:
            batch.append(
                DamageEffect(
                    source_id=attacker.id,
                    target_id=target.id,
                    element=infusion.extra_element,
                    dice=infusion.extra_damage,
                    min_damage=ctx.core.min_damage_on_hit,
                )
            )
        if infusion.trip and _try_trip(ctx, attacker, target):
            batch.append(
                ApplyStatusEffect(source_id=attacker.id, target_id=target.id, status_id=PRONE)
            )
    return batch


def height_permille(state: BattleState, attacker: UnitState, target: UnitState) -> int:
    """高處關鍵字（3-33e1）：召喚物站得比目標高時，普攻傷害加成（‰）；其他情況 0。"""
    if state.tile(*attacker.xy).height <= state.tile(*target.xy).height:
        return 0
    return sum(i.height_permille for i in active_infusions(state, attacker))


TRIP_ATTR = Attribute.DEX
"""倒地灌注的絆倒對抗用的屬性（Phase 3-41a 抽成常數，技能卡說明引用同一個值）。"""


def _try_trip(ctx: Ctx, attacker: UnitState, target: UnitState) -> bool:
    """倒地關鍵字的絆倒：每隻召喚物每輪 1 次、目標還沒倒地時，擲敏捷對抗；成功才倒地。"""
    if attacker.trip_round == ctx.state.round or target.has_status(PRONE):
        return False
    attacker.trip_round = ctx.state.round
    return contest(ctx, "trip", attacker, target, TRIP_ATTR)


def _in_water(state: BattleState, unit: UnitState) -> bool:
    return state.tile(*unit.xy).surface is Surface.WATER


def _rule_holds(
    state: BattleState, rule: SummonHitRule, attacker: UnitState, target: UnitState
) -> bool:
    if rule.when == "target_in_water":
        return _in_water(state, target)
    if rule.when == "self_in_water":
        return _in_water(state, attacker)
    return True


def chain_targets(
    state: BattleState, attacker: UnitState, target: UnitState, rule: SummonHitRule
) -> list[UnitState]:
    """雷電連鎖的對象：``target`` 附近（``chain_radius`` 內）的其他敵人，由近到遠（同距離依 ID），
    最多 ``chain_targets`` 名。"""
    near = [
        u
        for u in state.living_units()
        if u.team is not attacker.team
        and u.id != target.id
        and manhattan(u.xy, target.xy) <= rule.chain_radius
    ]
    near.sort(key=lambda u: (manhattan(u.xy, target.xy), u.id))
    return near[: rule.chain_targets]


def _hit_rule_effects(ctx: Ctx, attacker: UnitState, target: UnitState) -> list[EffectBase]:
    """召喚物範本的 ``hit_rules``（3-33e1）：條件成立時的狀態與水面連鎖。"""
    template = template_of(ctx.state, attacker)
    batch: list[EffectBase] = []
    if template is None or not target.alive:
        return batch
    for rule in template.hit_rules:
        if not _rule_holds(ctx.state, rule, attacker, target):
            continue
        if rule.status is not None:
            batch.append(
                ApplyStatusEffect(
                    source_id=attacker.id,
                    target_id=target.id,
                    status_id=rule.status,
                    duration=rule.duration,
                )
            )
        for other in chain_targets(ctx.state, attacker, target, rule):
            batch.append(
                DamageEffect(
                    source_id=attacker.id,
                    target_id=other.id,
                    element=effective_attack_element(ctx.rules, attacker, is_basic=True),
                    dice=attacker.weapon.dice,
                    flat=attacker.weapon.flat,
                    multiplier_permille=rule.chain_permille,
                    min_damage=ctx.core.min_damage_on_hit,
                )
            )
    return batch


def entangle_effect(
    state: BattleState, attacker: UnitState, target: UnitState, penalty: int
) -> ApplyStatusEffect:
    """鞭的纏繞（Phase 3I-1）：``entangled``（數值＝移動點數減少量）。命中發生在目標自己的回合
    （例如反應攻擊）時持續 2，讓它作用在目標的「下一個」回合；不擲抵抗（狀態沒有
    ``save_attr``）。"""
    own_turn = state.active_unit == target.id
    rounds = state.ruleset.status_def(ENTANGLED).duration or 1
    return ApplyStatusEffect(
        source_id=attacker.id,
        target_id=target.id,
        status_id=ENTANGLED,
        duration=rounds + 1 if own_turn else rounds,
        amount=penalty,
    )


def apply_hit_traits(ctx: Ctx, attacker: UnitState, target: UnitState) -> None:
    """``attacker`` 的普攻命中 ``target``、傷害結算之後：依武器參數結算命中特性。"""
    weapon = attacker.weapon
    if not attacker.alive:
        return
    batch: list[EffectBase] = []
    if weapon.armor_break is not None and target.alive:
        batch.append(
            ApplyStatusEffect(
                source_id=attacker.id,
                target_id=target.id,
                status_id=ARMOR_BROKEN,
                duration=weapon.armor_break.rounds,
                amount=-weapon.armor_break.defense_permille,
            )
        )
    bleed = natural_bleed(ctx.rules, attacker)
    if bleed > 0 and target.alive:  # 形態的天生武器：命中流血（狼人，3J-1b）
        batch.append(
            ApplyStatusEffect(
                source_id=attacker.id, target_id=target.id, status_id=BLEED, duration=bleed
            )
        )
    if weapon.entangle is not None and target.alive:
        batch.append(entangle_effect(ctx.state, attacker, target, weapon.entangle.move_penalty))
    if weapon.blessing is not None:
        ally = blessing_target(ctx.state, attacker)
        if ally is not None:
            batch.append(
                HealEffect(
                    source_id=attacker.id,
                    target_id=ally.id,
                    dice=weapon.blessing.dice,
                    flat=weapon.blessing.flat,
                )
            )
    if target.alive:  # 裝備的普攻附加：命中附帶狀態（3G-G2）
        for status, rounds in gear_on_hit_statuses(ctx.state, attacker):
            batch.append(
                ApplyStatusEffect(
                    source_id=attacker.id, target_id=target.id, status_id=status, duration=rounds
                )
            )
    infusions = active_infusions(ctx.state, attacker)
    batch += _infusion_effects(ctx, attacker, target, infusions)
    batch += _hit_rule_effects(ctx, attacker, target)
    execute(ctx, batch)
    direction = axis_direction(target.xy[0] - attacker.xy[0], target.xy[1] - attacker.xy[1])
    knockback = weapon.knockback + sum(i.knockback for i in infusions)
    if knockback > 0 and direction is not None and target.alive:
        limit = ctx.core.max_displace_distance  # 推擊距離上限（6.6），超過的每 1 格改為撞擊傷害
        execute(
            ctx,
            [
                PushEffect(
                    source_id=attacker.id,
                    target_id=target.id,
                    direction=direction,
                    distance=min(knockback, limit),
                    extra_collisions=max(0, knockback - limit),
                )
            ],
        )


def spend_ammo(attacker: UnitState) -> None:
    """有彈匣的武器開火：用掉 1 發（沒有彈匣的武器不動作）。"""
    if attacker.weapon.magazine > 0 and attacker.ammo > 0:
        attacker.ammo -= 1


def gunshot_reveals(state: BattleState, attacker: UnitState) -> bool:
    """開火前：武器有槍聲，而且自己現在是隱蔽的（開火後要被揭露）。"""
    return attacker.weapon.gunshot and is_concealed(state, attacker)


def reveal_after_gunshot(ctx: Ctx, attacker: UnitState) -> None:
    """槍聲：施加 ``revealed``（不算隱蔽，連黑暗與草叢也一樣，持續到下一個自己的回合結束）。"""
    if attacker.alive:
        execute(
            ctx,
            [ApplyStatusEffect(target_id=attacker.id, status_id=REVEALED, source_id=attacker.id)],
        )


def pierce_line_targets(
    state: BattleState, attacker: UnitState, target: UnitState
) -> list[UnitState]:
    """弩的穿透：從 ``attacker`` 經過 ``target`` 延伸的直線上，``target`` 後方、射程內、視線沒被擋住
    的敵人（由近到遠，最多 ``pierce_line`` 名）。直線是 Bresenham 直線的延伸，所以和普攻的視線
    判斷一致；遇到擋住視線的地形就停止。"""
    limit = attacker.weapon.pierce_line
    ax, ay = attacker.xy
    dx, dy = target.xy[0] - ax, target.xy[1] - ay
    distance = abs(dx) + abs(dy)
    if limit <= 0 or distance == 0:
        return []
    reach = attack_reach(state, attacker)
    k = reach // distance + 2
    end: XY = (ax + dx * k, ay + dy * k)
    found: list[UnitState] = []
    passed = False
    for cell in bresenham(attacker.xy, end)[1:]:
        if cell == target.xy:
            passed = True
            continue
        if not passed:
            continue
        if not state.in_bounds(*cell) or manhattan(attacker.xy, cell) > reach:
            break
        if not has_line_of_sight(state, attacker.xy, cell):
            break
        unit = state.unit_at(*cell)
        if unit is not None and unit.alive and unit.team is not attacker.team:
            found.append(unit)
            if len(found) >= limit:
                break
    return found
