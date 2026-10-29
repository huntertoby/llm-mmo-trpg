"""普攻流的兩個普攻附加詞條（Phase 3-32a，``docs/design/08-裝備.md`` 8.25）。

- **連擊** ``affix_attack_combo``（``strike: combo``）：每第 N 次普攻命中，對同一個目標多攻擊一次
  （要重新擲命中，傷害為 ``strike_permille``）。計數是 ``UnitState.attack_hits_landed``：只算普攻
  的命中、不含連擊多出來的那一下，也不受技能命中影響；只有帶連擊詞條的單位會累計。
- **分裂** ``affix_attack_cleave``（``strike: cleave``）：普攻命中後，對目標相鄰（四方向）的另一個
  敵人造成 ``strike_permille`` 的傷害（自動命中、不暴擊）；多個時取 HP 最低、再依座標（x、y）。

兩者 **每回合最多 1 次**（計數在 ``UnitState.gear_turn_counts``，自己回合開始時清除；藉機攻擊
也算）；多出來的一下（連擊）不會再觸發連擊或分裂，所以不會疊加。同 id 的詞條只生效最強的 1 條
（連擊取 N 較小者，:func:`trpg.content.equipment.affix_strength`）。結算在目標受傷、武器特性結算
之後，由 :func:`trpg.engine.reactions.perform_unit_attack` 的單次攻擊呼叫 :func:`after_attack_hit`。
"""

from __future__ import annotations

from collections.abc import Callable

from trpg.content.equipment import AttackAffix, affix_text
from trpg.engine.context import Ctx
from trpg.engine.effects import execute
from trpg.engine.effects.models import DamageEffect
from trpg.engine.events import GearTriggered
from trpg.engine.gear.enhance import strike_affixes
from trpg.engine.gear.state import GearAffix
from trpg.engine.modifiers import ATTACK, damage_element
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.statuses import weapon_attribute, weapon_scale_attr
from trpg.engine.state import UnitState
from trpg.engine.weapon_traits import attack_dice

__all__ = ["STRIKE_CLEAVE", "STRIKE_COMBO", "after_attack_hit", "cleave_target"]

STRIKE_COMBO = "attack_combo"
"""``gear_triggered.trigger``：連擊。"""
STRIKE_CLEAVE = "attack_cleave"
"""``gear_triggered.trigger``：分裂。"""


def cleave_target(ctx: Ctx, attacker: UnitState, target: UnitState) -> UnitState | None:
    """分裂的對象：目標相鄰（曼哈頓距離 1）、存活的另一個敵人，取 HP 最低、再依座標；沒有時
    ``None``。"""
    found = [
        u
        for u in ctx.state.living_units()
        if u.team is not attacker.team and u.id != target.id and manhattan(u.xy, target.xy) == 1
    ]
    return min(found, key=lambda u: (u.hp, u.xy)) if found else None


def _ready(unit: UnitState, entry: GearAffix) -> bool:
    return unit.gear_turn_counts.get(entry.affix.id, 0) < 1


def _fire(ctx: Ctx, unit: UnitState, entry: GearAffix, trigger: str, other: UnitState) -> None:
    """記下本回合用掉這條詞條，並發出 ``gear_triggered``。"""
    key = entry.affix.id
    unit.gear_turn_counts[key] = unit.gear_turn_counts.get(key, 0) + 1
    ctx.emit(
        GearTriggered,
        unit_id=unit.id,
        affix_id=key,
        name_zh=affix_text(entry.affix, entry.value),
        trigger=trigger,
        other_id=other.id,
        trigger_depth=ctx.trigger_depth,
    )


def _permille(entry: GearAffix) -> int:
    affix = entry.affix
    assert isinstance(affix, AttackAffix) and affix.strike_permille is not None
    return affix.strike_permille


def _cleave(ctx: Ctx, attacker: UnitState, target: UnitState, entry: GearAffix) -> None:
    victim = cleave_target(ctx, attacker, target)
    if victim is None:
        return
    _fire(ctx, attacker, entry, STRIKE_CLEAVE, victim)
    state, weapon = ctx.state, attacker.weapon
    execute(
        ctx,
        [
            DamageEffect(
                target_id=victim.id,
                source_id=attacker.id,
                cause="attack",
                element=damage_element(state, attacker, ATTACK, weapon.element),
                dice=attack_dice(state, attacker),
                flat=weapon.flat,
                scaled_permille=weapon_attribute(ctx.rules, attacker)
                * ctx.core.basic_attack_attr_multiplier_permille,
                scale_attr=weapon_scale_attr(attacker),
                min_damage=ctx.core.min_damage_on_hit,
                multiplier_permille=_permille(entry),
            )
        ],
    )


def after_attack_hit(
    ctx: Ctx,
    attacker: UnitState,
    target: UnitState,
    attack_again: Callable[[int], None],
) -> None:
    """一次普攻命中（傷害與武器特性結算完）之後的分裂與連擊。``attack_again(permille)`` 是對
    ``target`` 多攻擊一次的函式（傷害倍率 ``permille``）；呼叫端不會對連擊多出來的那一下再呼叫
    本函式。"""
    if not attacker.gear.affixes or not attacker.alive:
        return
    if target.alive:
        for entry in strike_affixes(attacker, "cleave"):
            if _ready(attacker, entry):
                _cleave(ctx, attacker, target, entry)
    for entry in strike_affixes(attacker, "combo"):
        attacker.attack_hits_landed += 1
        if (
            entry.value
            and attacker.attack_hits_landed % entry.value == 0
            and target.alive
            and attacker.alive
            and _ready(attacker, entry)
        ):
            _fire(ctx, attacker, entry, STRIKE_COMBO, target)
            attack_again(_permille(entry))
