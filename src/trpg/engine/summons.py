"""召喚（Phase 3D-4a，``docs/design/06-技能.md`` 6.16 B）。

- 召喚物由 ``summon`` 原語在 ``ground_tile`` 選的空格產生（範本在規則包的 ``summons``，
  ``content/units/summons/``），屬於召喚者陣營，``owner_id`` 記錄召喚者，由效用 AI 控制。
- **行動順序**：插在先攻順序中召喚者之後（同一召喚者已有的召喚物之後），不擲先攻；召喚者在
  自己的回合施放時，召喚物這一輪就緊接著行動。
- **持續**：``summon_expires_round`` ＝ 施放輪 ＋ ``duration``；召喚者在那一輪（或之後）的回合結束
  時消失（:func:`expire_summons`），所以召喚物恰好行動 ``duration`` 次（召喚者被跳過回合也照常
  倒數）。召喚者倒下或撤離時一併消失（:mod:`trpg.engine.lifecycle`）。
- **上限**：同一召喚者同時存在的召喚物超過 ``summon_limit_per_owner``（不得高於硬上限
  ``summon_hard_cap``，:func:`summon_limit`）時，最舊的先消失；持續輪數不超過
  ``summon_max_duration``。
- **成長**（Phase 3-33b，6.29.1）：召喚當下依施放者等級與技能縮放屬性快照 HP、普攻固定傷害與傷害加成
  （:func:`growth_of`），之後不隨施放者變化。
- **灌注**（:mod:`trpg.engine.infusion`）：召喚物記下灌注的關鍵字，普攻命中後附加對照表的效果。
- 召喚物沒有源力、不取用源泉、不計入勝負條件、不能撤離（各自的規則模組檢查 ``is_summon``）。
- **圖騰**（Phase 3D-4b，範本的 ``totem``）：沒有 AP（不移動、不攻擊），自己的回合開始時讓範圍內的
  友方獲得狀態（:func:`pulse_totem`）。
- **範本特性**（3-33e1／3-33e2b）：``pulse``（回合開始的脈動：造表面、治療、護盾、拉扯，
  :func:`pulse_summon`）、``snare``（藤蔓，敵人踏入相鄰格時纏住）、``platform``（高台圖騰，召喚時升起
  高台，消失時恢復）、``inert``（沒有行動的純功能圖騰）。
- 消失的召喚物保留在 ``units`` 中（``dismissed``），事件與紀錄仍可引用它的名字。
"""

from __future__ import annotations

from fractions import Fraction
from typing import NamedTuple

from trpg.content.battle import Dice, SummonPulse, TotemSpec, WeaponDef
from trpg.content.maps import MAX_HEIGHT
from trpg.content.rules import CoreRules
from trpg.content.skills import EffectSpec
from trpg.engine import modifiers
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import (
    ApplyStatusEffect,
    CreateSurfaceEffect,
    DamageEffect,
    EffectBase,
    HealEffect,
    PushEffect,
    RaiseTerrainEffect,
    ShieldEffect,
)
from trpg.engine.effects.world import push_distance, unit_push_block
from trpg.engine.events import (
    DetonateReason,
    EffectFizzled,
    EventBase,
    SnareTriggered,
    SummonDetonated,
    SummonPulled,
    TotemPulsed,
    UnitMoved,
    UnitSummoned,
)
from trpg.engine.gear_summon import gear_summon_duration, inherit_attack_gear
from trpg.engine.ids import CONCEALED, PRONE, next_unit_id
from trpg.engine.infusion import active_infusions, default_infusion, template_of
from trpg.engine.lifecycle import dismiss_summon, make_unit, summons_of
from trpg.engine.rules.geometry import XY, manhattan, neighbors4
from trpg.engine.rules.movement import is_deadly, is_standable
from trpg.engine.rules.statuses import effective_attribute
from trpg.engine.skills.targeting import summon_site_problem
from trpg.engine.state import BattleState, UnitState
from trpg.engine.summon_variants import apply_summon_spec
from trpg.engine.triggers import register_trigger
from trpg.shared.rng import PERMILLE
from trpg.shared.types import Pos, UnitId

__all__ = [
    "Growth",
    "detonate_if_adjacent",
    "detonate_on_downed",
    "expire_summons",
    "growth_of",
    "pulse_summon",
    "pulse_totem",
    "summon_inert",
    "summon_limit",
    "summon_unit",
    "totem_of",
]


class Growth(NamedTuple):
    """召喚當下依施放者快照的成長量：最大 HP 加值、普攻固定傷害加值、傷害加成（‰）。"""

    hp: int
    flat: int
    bonus_permille: int


def summon_limit(core: CoreRules, delta: int = 0) -> int:
    """同一召喚者同時存在的召喚物上限：``summon_limit_per_owner`` ＋ 召喚專精的修正 ``delta``
    （3-33f1），至少 1，不得超過硬上限 ``summon_hard_cap``。"""
    return max(1, min(core.summon_limit_per_owner + delta, core.summon_hard_cap))


def growth_of(state: BattleState, owner: UnitState, skill_id: str) -> Growth:
    """``owner`` 以 ``skill_id`` 召喚時的成長量（6.29.1）：等級 ``L`` 與技能縮放屬性修正 ``M``
    （``(有效屬性 − ability_mod_base) ÷ ability_mod_divisor``，下限 0；技能不存在時 0）。"""
    core = state.ruleset.core
    growth = core.summon_growth
    mod = 0
    try:
        attr = state.ruleset.skill_def(skill_id).scaling_attr
    except KeyError:
        pass
    else:
        value = effective_attribute(state.ruleset, owner, attr)
        mod = max(0, (value - core.ability_mod_base) // core.ability_mod_divisor)
    levels = max(0, owner.level - 1)
    return Growth(
        hp=growth.hp_per_level * levels + growth.hp_per_attr_mod * mod,
        flat=(growth.flat_per_level_permille * levels + growth.flat_per_attr_mod_permille * mod)
        // PERMILLE,
        bonus_permille=growth.bonus_per_level_permille * levels
        + growth.bonus_per_attr_mod_permille * mod,
    )


def _order_index(state: BattleState, owner_id: UnitId) -> int:
    """新召喚物在先攻順序中的位置：召喚者之後、同一召喚者已有的召喚物之後。"""
    order = state.turn_order
    if owner_id not in order:
        return len(order)
    index = order.index(owner_id) + 1
    while index < len(order) and state.units[order[index]].owner_id == owner_id:
        index += 1
    return index


def _insert_in_order(state: BattleState, uid: UnitId, index: int) -> None:
    state.turn_order.insert(index, uid)
    # 插在目前位置之前（或正好插在行動者的位置）時，目前位置往後移一格，維持指向同一個單位
    if index < state.turn_pos or (index == state.turn_pos and state.active_unit is not None):
        state.turn_pos += 1


def _skill_use(state: BattleState, skill_id: str) -> modifiers.Use | None:
    """召喚技能的修正用途；技能不存在（例如測試用的假 ID）時為 ``None``。"""
    try:
        return modifiers.skill_use(state.ruleset.skill_def(skill_id))
    except KeyError:
        return None


def _hp_permille(state: BattleState, owner: UnitState, skill_id: str) -> int:
    """召喚者的修正規則 ``summon_hp_permille``：召喚物最大 HP 倍率（‰；Phase 3-24b1）。"""
    use = _skill_use(state, skill_id)
    return PERMILLE if use is None else modifiers.summon_hp_permille(state, owner, use)


def _empowered_weapon(
    state: BattleState, owner: UnitState, skill_id: str, weapon: WeaponDef, flat: int
) -> WeaponDef:
    """召喚者的修正規則 ``summon_attack_dice``：召喚物武器的傷害骰多幾顆（Phase 3-24b1）；
    再加上成長的固定傷害 ``flat``（Phase 3-33b）。"""
    use = _skill_use(state, skill_id)
    extra = 0 if use is None else modifiers.summon_attack_dice(state, owner, use)
    update: dict[str, object] = {}
    if extra > 0:
        update["dice"] = Dice(count=weapon.dice.count + extra, sides=weapon.dice.sides)
    if flat > 0:
        update["flat"] = weapon.flat + flat
    return weapon.model_copy(update=update) if update else weapon


def summon_unit(  # noqa: PLR0917
    ctx: Ctx,
    owner: UnitState,
    template_id: str,
    xy: XY,
    duration: int,
    skill_id: str,
    *,
    order_index: int | None = None,
    orphan: bool = False,
    infusion: str | None = None,
    spec: EffectSpec | None = None,
) -> list[EventBase]:
    """``owner`` 在 ``xy`` 召喚 ``template_id``，持續 ``duration`` 輪。位置不合法或範本不存在時
    發出 ``effect_fizzled``；超過上限時先讓最舊的召喚物消失。

    ``order_index``／``orphan``（Phase 3D-6，``on_downed_spawn``）：召喚者已倒下，分身排在指定的
    先攻位置，``unit_summoned`` 標記 ``orphan``（到期改在環境回合處理）。

    ``infusion``（Phase 3-33b）：灌注的關鍵字（已由動作檢查過）；省略時取施放者第一個可選的。

    ``spec``（Phase 3-33f2）：技能的 ``summon`` 效果；分歧進化的 HP、強度、小特性與第二個灌注
    （:mod:`trpg.engine.summon_variants`）從這裡來。召喚物持續的輪數另外加上施放者的召喚持續詞條。"""
    state = ctx.state
    try:
        summon = state.ruleset.summon_def(template_id)
    except KeyError:
        pos = Pos(x=xy[0], y=xy[1])
        return [ctx.emit(EffectFizzled, effect_kind="summon", pos=pos, reason="unknown_summon")]
    if summon_site_problem(state, xy) is not None:
        pos = Pos(x=xy[0], y=xy[1])
        return [ctx.emit(EffectFizzled, effect_kind="summon", pos=pos, reason="summon_blocked")]
    events: list[EventBase] = []
    existing = summons_of(ctx, owner.id)
    use = _skill_use(state, skill_id)
    limit = summon_limit(
        ctx.core, 0 if use is None else modifiers.summon_limit_delta(state, owner, use)
    )
    while len(existing) >= limit:
        events += dismiss_summon(ctx, existing.pop(0), "limit")
    uid = next_unit_id(state)
    same = sum(1 for u in state.units.values() if u.template_id == template_id)
    grown = growth_of(state, owner, skill_id)
    weapon = _empowered_weapon(state, owner, skill_id, summon.weapon, grown.flat)
    if infusion is None:
        infusion = default_infusion(state, owner)
    unit = make_unit(
        uid,
        template=summon.template,
        weapon=weapon,
        team=owner.team,
        pos=Pos(x=xy[0], y=xy[1]),
        name=f"{summon.template.name_zh}{same + 1}",
        rules=state.ruleset,
        facing=owner.facing,  # 召喚物與召喚者同向（Phase 3D-8d）
    )
    unit.owner_id = owner.id
    role_permille = ctx.core.summon_role_hp_permille.get(summon.template.role or "", PERMILLE)
    base_hp = (unit.max_hp + grown.hp) * role_permille // PERMILLE  # 依定位的 HP 係數（3-33f1）
    unit.max_hp = base_hp * _hp_permille(state, owner, skill_id) // PERMILLE
    unit.level = owner.level
    unit.summon_bonus_permille = grown.bonus_permille + (
        0 if use is None else modifiers.summon_damage_permille(state, owner, use)
    )
    unit.infusion = infusion
    unit.bonus_infusion = None if spec is None else spec.infusion  # 橋接進化（3-33f2）
    infusions = active_infusions(state, unit)  # 固有與施放時選的灌注（3-33e1）
    unit.max_hp = unit.max_hp * (PERMILLE + sum(i.hp_permille for i in infusions)) // PERMILLE
    apply_summon_spec(state, unit, spec)  # 加深與數量型進化（3-33f2）
    unit.gear = inherit_attack_gear(owner, unit.gear)  # 繼承 1 條普攻附加詞條（3-33f2）
    unit.hp = unit.max_hp
    unit.summon_mode = summon.template.default_mode
    duration = min(duration, ctx.core.summon_max_duration) + gear_summon_duration(owner)
    if use is not None:  # 召喚專精（3-33f1）：持續輪數加在上限之後
        duration += modifiers.summon_duration_delta(state, owner, use)
    unit.summon_expires_round = state.round + duration
    unit.initiative = owner.initiative  # 不擲先攻：顯示用，順序由插入位置決定
    state.units[uid] = unit
    index = _order_index(state, owner.id) if order_index is None else order_index
    _insert_in_order(state, uid, index)
    events.append(
        ctx.emit(
            UnitSummoned,
            unit_id=uid,
            owner_id=owner.id,
            template_id=template_id,
            team=owner.team,
            pos=unit.pos,
            skill_id=skill_id,
            expires_round=unit.summon_expires_round,
            order_index=index,
            orphan=orphan,
            max_hp=unit.max_hp,
            infusion=infusion,
        )
    )
    if summon.template.platform is not None:  # 高台圖騰（3-33e2b）：旁邊升起 1 格高台
        _raise_platform(ctx, owner, unit)
    conceal = max((i.conceal_rounds for i in infusions), default=0)
    if conceal > 0:  # 隱蔽灌注（3-33e1）：召喚時獲得隱蔽
        execute(
            ctx,
            [
                ApplyStatusEffect(
                    target_id=uid, status_id=CONCEALED, duration=conceal, source_id=owner.id
                )
            ],
        )
    return events


def expire_summons(ctx: Ctx, owner: UnitState) -> list[EventBase]:
    """召喚者的回合結束：到期（``summon_expires_round`` ≤ 目前輪數）的召喚物消失。"""
    events: list[EventBase] = []
    for summon in summons_of(ctx, owner.id):
        expires = summon.summon_expires_round
        if expires is not None and expires <= ctx.state.round:
            events += dismiss_summon(ctx, summon, "expired")
    return events


def totem_of(state: BattleState, unit: UnitState) -> TotemSpec | None:
    """``unit`` 是圖騰時回傳它的光環規格，否則 ``None``。"""
    if not unit.is_summon:
        return None
    try:
        return state.ruleset.summon_def(unit.template_id).template.totem
    except KeyError:
        return None


def summon_inert(state: BattleState, unit: UnitState) -> bool:
    """召喚物回合內沒有行動（Phase 3-33e2a）：圖騰，或範本寫了 ``inert``（土牆）。"""
    if totem_of(state, unit) is not None:
        return True
    template = template_of(state, unit)
    return template is not None and template.inert


def _blast_tiles(ctx: Ctx, unit: UnitState, radius: int) -> list[XY]:
    """爆心與曼哈頓距離 ``radius`` 以內的格子（地圖內，依 ``(y, x)`` 排序）。"""
    x0, y0 = unit.xy
    cells = [
        (x, y)
        for y in range(y0 - radius, y0 + radius + 1)
        for x in range(x0 - radius, x0 + radius + 1)
        if abs(x - x0) + abs(y - y0) <= radius and ctx.state.in_bounds(x, y)
    ]
    return cells


def _detonate(ctx: Ctx, unit: UnitState, reason: DetonateReason) -> None:
    template = template_of(ctx.state, unit)
    assert template is not None and template.detonate is not None
    spec = template.detonate
    victims = [
        u
        for u in ctx.state.units_sorted()
        if u.alive and u.team is not unit.team and manhattan(u.xy, unit.xy) <= spec.radius
    ]
    ctx.emit(
        SummonDetonated,
        unit_id=unit.id,
        pos=unit.pos,
        radius=spec.radius,
        reason=reason,
        targets=[u.id for u in victims],
    )
    if unit.alive:  # 自爆後消失（被打倒的已經離場）
        dismiss_summon(ctx, unit, "detonated")
    batch: list[EffectBase] = [
        DamageEffect(
            source_id=unit.id,
            target_id=u.id,
            element=spec.element,
            dice=spec.dice,
            flat=spec.flat,
            min_damage=ctx.core.min_damage_on_hit,
        )
        for u in victims
    ]
    if spec.surface is not None:
        batch += [
            CreateSurfaceEffect(source_id=unit.id, pos=xy, surface=spec.surface, team=unit.team)
            for xy in _blast_tiles(ctx, unit, spec.radius)
        ]
    execute(ctx, batch)


def detonate_if_adjacent(ctx: Ctx, unit: UnitState, reason: DetonateReason) -> bool:
    """會自爆的召喚物（範本 ``detonate``）與任一敵人相鄰時爆炸並消失（Phase 3-33e2a）；
    回傳是否爆炸了。"""
    template = template_of(ctx.state, unit)
    if template is None or template.detonate is None or not unit.alive:
        return False
    if not any(
        u.alive and u.team is not unit.team and manhattan(u.xy, unit.xy) == 1
        for u in ctx.state.living_units()
    ):
        return False
    _detonate(ctx, unit, reason)
    return True


def detonate_on_downed(ctx: Ctx, unit: UnitState) -> None:
    """會自爆的召喚物被打倒時爆炸（Phase 3-33e2a；單位已標記倒下，只結算爆炸）。"""
    template = template_of(ctx.state, unit)
    if template is not None and template.detonate is not None:
        _detonate(ctx, unit, "downed")


def _platform_site(state: BattleState, owner: UnitState, unit: UnitState) -> XY | None:
    """高台升起的格子：圖騰旁邊（距離 1）可站立、沒有單位與物件、不是致命地形、還升得高的格子；
    多個時取離召喚者最近的（方便攀上去），再依座標 ``(y, x)``。"""
    sites = [
        xy
        for xy in neighbors4(state, unit.xy)
        if is_standable(state, xy)
        and not is_deadly(state, xy)
        and state.unit_at(*xy) is None
        and state.tile(*xy).object_id is None
        and state.tile(*xy).height < MAX_HEIGHT
    ]
    if not sites:
        return None
    return min(sites, key=lambda xy: (manhattan(xy, owner.xy), xy[1], xy[0]))


def _raise_platform(ctx: Ctx, owner: UnitState, unit: UnitState) -> None:
    site = _platform_site(ctx.state, owner, unit)
    if site is None:
        return
    unit.platform_pos = Pos(x=site[0], y=site[1])
    execute(ctx, [RaiseTerrainEffect(source_id=unit.id, pos=site, amount=1)])


def pulse_summon(ctx: Ctx, unit: UnitState) -> None:
    """召喚物自己的回合開始時的脈動（水精、守護靈、吸引圖騰）：腳下造表面、治療附近受傷的友方
    （不含自己與倒下者；依 ID 順序）、護盾給最虛弱的友方、把最近的敵人拉近 1 格。沒有 ``pulse`` 的
    召喚物不動作。"""
    template = template_of(ctx.state, unit)
    if template is None or template.pulse is None:
        return
    pulse = template.pulse
    batch = _surface_and_heal(ctx, unit, pulse)
    shield = _shield_effect(ctx, unit, pulse)
    if shield is not None:
        batch.append(shield)
    execute(ctx, batch)
    if pulse.pull_radius > 0 and unit.alive:
        _pull_nearest_enemy(ctx, unit, pulse.pull_radius)


def _surface_and_heal(ctx: Ctx, unit: UnitState, pulse: SummonPulse) -> list[EffectBase]:
    batch: list[EffectBase] = []
    if pulse.surface is not None:
        batch.append(
            CreateSurfaceEffect(
                source_id=unit.id, pos=unit.xy, surface=pulse.surface, team=unit.team
            )
        )
    if pulse.heal_dice is None and pulse.heal_flat == 0:
        return batch
    for ally in ctx.state.living_units():
        if (
            ally.team is unit.team
            and ally.id != unit.id
            and ally.hp < ally.max_hp
            and manhattan(ally.xy, unit.xy) <= pulse.heal_radius
        ):
            batch.append(
                HealEffect(
                    source_id=unit.id,
                    target_id=ally.id,
                    dice=pulse.heal_dice,
                    flat=pulse.heal_flat,
                )
            )
    return batch


def weakest_ally(state: BattleState, unit: UnitState) -> UnitState | None:
    """最虛弱的友方（含召喚者與其他召喚物，不含自己）：HP 比例最低，再依目前 HP、單位 ID。"""
    allies = [u for u in state.living_units() if u.team is unit.team and u.id != unit.id]
    if not allies:
        return None
    return min(allies, key=lambda u: (Fraction(u.hp, u.max_hp), u.hp, u.id))


def _shield_effect(ctx: Ctx, unit: UnitState, pulse: SummonPulse) -> EffectBase | None:
    if pulse.shield_dice is None and pulse.shield_flat == 0:
        return None
    target = weakest_ally(ctx.state, unit)
    if target is None:
        return None
    return ShieldEffect(
        source_id=unit.id, target_id=target.id, dice=pulse.shield_dice, flat=pulse.shield_flat
    )


def _pull_step(state: BattleState, enemy: UnitState, totem: UnitState) -> XY | None:
    """``enemy`` 往 ``totem`` 拉近 1 格的方向（長軸優先，距離相同時先 x）；第一個沒被擋住的方向，
    都不行時 ``None``。已經相鄰的拉不動（那一格是圖騰自己）。"""
    if push_distance(state, enemy, 1) == 0:  # 堅守的單位拉不動
        return None
    dx, dy = totem.xy[0] - enemy.xy[0], totem.xy[1] - enemy.xy[1]
    steps = [(1 if dx > 0 else -1, 0)] if dx != 0 else []
    if dy != 0:
        vertical = (0, 1 if dy > 0 else -1)
        steps = [*steps, vertical] if abs(dx) >= abs(dy) else [vertical, *steps]
    for sx, sy in steps:
        nxt = (enemy.xy[0] + sx, enemy.xy[1] + sy)
        if nxt != totem.xy and unit_push_block(state, enemy.xy, nxt, enemy.id) is None:
            return (sx, sy)
    return None


def _pull_nearest_enemy(ctx: Ctx, totem: UnitState, radius: int) -> None:
    """吸引圖騰：``radius`` 以內最近（再依座標 ``(y, x)``）、拉得動的敵人往自己拉近 1 格。"""
    state = ctx.state
    candidates = sorted(
        (u for u in state.living_units() if u.team is not totem.team and u.id != totem.id),
        key=lambda u: (manhattan(u.xy, totem.xy), u.xy[1], u.xy[0], u.id),
    )
    for enemy in candidates:
        if manhattan(enemy.xy, totem.xy) > radius:
            break
        step = _pull_step(state, enemy, totem)
        if step is None:
            continue
        ctx.emit(SummonPulled, unit_id=totem.id, target_id=enemy.id, from_pos=enemy.pos)
        execute(
            ctx,
            [PushEffect(source_id=totem.id, target_id=enemy.id, direction=step, distance=1)],
        )
        return


@register_trigger("unit_moved")
def _snare_trigger(ctx: Ctx, event: EventBase, depth: int) -> list[EffectBase]:
    """藤蔓（``snare``）：敵人移動到藤蔓相鄰的格子時纏住（緩速＋倒地），每隻藤蔓每輪最多 1 次
    （傳送復位不算）。"""
    assert isinstance(event, UnitMoved)
    state = ctx.state
    mover = state.units.get(event.unit_id)
    if mover is None or not mover.alive or event.mode == "teleport":
        return []
    effects: list[EffectBase] = []
    for vine in state.units_sorted():
        template = template_of(state, vine) if vine.alive and vine.is_summon else None
        snare = None if template is None else template.snare
        if (
            snare is None
            or vine.team is mover.team
            or vine.snare_round == state.round
            or manhattan(vine.xy, mover.xy) != 1
        ):
            continue
        vine.snare_round = state.round
        ctx.emit(
            SnareTriggered,
            unit_id=vine.id,
            target_id=mover.id,
            status_id=snare.status,
            prone=snare.prone,
        )
        effects.append(
            ApplyStatusEffect(
                depth=depth,
                source_id=vine.id,
                target_id=mover.id,
                status_id=snare.status,
                duration=snare.duration,
            )
        )
        if snare.prone:
            effects.append(
                ApplyStatusEffect(
                    depth=depth, source_id=vine.id, target_id=mover.id, status_id=PRONE
                )
            )
    return effects


def totem_targets(state: BattleState, totem: UnitState, spec: TotemSpec) -> list[UnitState]:
    """光環範圍內的友方（含圖騰所在格的距離 0；不含圖騰自己與其他圖騰），依單位 ID 排序。"""
    return [
        u
        for u in state.units_sorted()
        if u.alive
        and u.team is totem.team
        and u.id != totem.id
        and totem_of(state, u) is None
        and manhattan(u.xy, totem.xy) <= spec.radius
    ]


def pulse_totem(ctx: Ctx, totem: UnitState) -> None:
    """圖騰的回合開始：範圍內的友方獲得（或刷新）光環狀態；範圍內沒有友方時不發事件。"""
    spec = totem_of(ctx.state, totem)
    if spec is None:
        return
    targets = totem_targets(ctx.state, totem, spec)
    if not targets:
        return
    ctx.emit(
        TotemPulsed,
        unit_id=totem.id,
        status_id=spec.status,
        duration=spec.duration,
        radius=spec.radius,
        targets=[u.id for u in targets],
    )
    execute(
        ctx,
        [
            ApplyStatusEffect(
                target_id=u.id, status_id=spec.status, duration=spec.duration, source_id=totem.id
            )
            for u in targets
        ],
    )
