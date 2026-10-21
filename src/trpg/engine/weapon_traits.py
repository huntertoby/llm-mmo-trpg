"""武器小特性（Phase 3-24a1，``docs/design/08-裝備.md`` 8.11）。

每個特性都是 ``content/weapons.yaml`` 武器資料上的參數，這裡只讀參數、不寫死數值：

- 斧 ``armor_break``：普攻命中後，目標帶 ``armor_broken`` 狀態（防禦值降低、持續 N 回合）。
- 錘 ``knockback``：普攻命中後沿攻擊方向把目標推 N 格（沿用推擊與撞擊規則）。
- 權杖 ``blessing``：普攻命中時，最近的隊友（不含自己與召喚物）回復 HP。
- 圖騰杖 ``summon_dice_bonus``：召喚者的召喚物普攻多加 N 顆傷害骰（:func:`attack_dice`）。

矛的 ``reach``（藉機攻擊範圍）在 :func:`trpg.engine.reactions.opportunity_attacks`，弓的 ``lob``
（拋射）在 :func:`trpg.engine.rules.geometry.has_line_of_sight`。
"""

from __future__ import annotations

from trpg.content.battle import Dice
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import ApplyStatusEffect, EffectBase, HealEffect, PushEffect
from trpg.engine.ids import ARMOR_BROKEN
from trpg.engine.rules.geometry import axis_direction, manhattan
from trpg.engine.state import BattleState, UnitState

__all__ = ["apply_hit_traits", "attack_dice", "blessing_target"]


def attack_dice(state: BattleState, attacker: UnitState) -> Dice:
    """普攻的傷害骰：武器的骰子；召喚物另加召喚者武器的 ``summon_dice_bonus`` 顆同面數的骰
    （圖騰杖的統御；召喚者已不在場時不加）。"""
    dice = attacker.weapon.dice
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
    execute(ctx, batch)
    direction = axis_direction(target.xy[0] - attacker.xy[0], target.xy[1] - attacker.xy[1])
    if weapon.knockback > 0 and direction is not None and target.alive:
        execute(
            ctx,
            [
                PushEffect(
                    source_id=attacker.id,
                    target_id=target.id,
                    direction=direction,
                    distance=weapon.knockback,
                )
            ],
        )
