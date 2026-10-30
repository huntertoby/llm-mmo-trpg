"""技能與效果的條件（docs/phases/Phase2A計畫.md 6.1、6.4 第 2 條）：五種條件各有成立與不成立的
測試，技能層級（能否使用）與效果層級（對每個對象是否生效）都要。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import make_skill
from tests.engine.skill_helpers import SID, U1, U2, U3, battle, cast, hit_with, of
from trpg.content.skills import ConditionSpec, SkillDef
from trpg.engine import BattleState, UseSkill, legal_actions
from trpg.engine.events import AttackRolled, StatusApplied
from trpg.engine.state import StatusInstance
from trpg.shared.errors import IllegalActionError
from trpg.shared.types import Pos, Surface

BURN: dict[str, Any] = {"type": "apply_status", "status": "burning"}
SINGLE5: dict[str, Any] = {"type": "single", "range": 5}
HIGH_CASTER = "\n".join(
    ["0000000", "0000000", "0000000", "0002000", "0000000", "0000000", "0000000"]
)


def _skill(condition: dict[str, Any], *, effect_level: bool = False) -> SkillDef:
    effect = {**BURN, "condition": condition} if effect_level else BURN
    return make_skill(SID, SINGLE5, [effect])


def _usable(state: BattleState) -> bool:
    return any(isinstance(a, UseSkill) and a.skill_id == SID for a in legal_actions(state))


def _set_hp(state: BattleState, uid: str, hp: int) -> BattleState:
    unit = state.units[uid]  # type: ignore[index]
    unit.hp = hp
    return state


def _burning(state: BattleState, uid: str) -> BattleState:
    state.units[uid].statuses.append(StatusInstance("burning", 2))  # type: ignore[index]
    return state


def _with_condition(raw: dict[str, Any] | None) -> SkillDef:
    skill = make_skill(SID, SINGLE5, [BURN])
    cond = None if raw is None else ConditionSpec.model_validate(raw)
    return skill.model_copy(update={"condition": cond})


# ---------------------------------------------------------------------------
# 技能層級：不成立時不在 legal_actions，resolve 拋 IllegalActionError
# ---------------------------------------------------------------------------


def _assert_gate(met: BattleState, unmet: BattleState) -> None:
    assert _usable(met)
    assert not _usable(unmet)
    with pytest.raises(IllegalActionError, match="技能條件不成立"):
        cast(unmet, target_id=U2)
    assert cast(met, target_id=U2).state is not None


def test_skill_condition_target_hp_below() -> None:
    skill = _with_condition({"type": "target_hp_below", "permille": 400})
    full = battle(skill, [(4, 3)])
    max_hp = full.units[U2].max_hp
    low = _set_hp(battle(skill, [(4, 3)]), U2, max_hp * 400 // 1000 - 1)
    _assert_gate(low, full)


def test_target_hp_below_is_strict_at_the_boundary() -> None:
    skill = _with_condition({"type": "target_hp_below", "permille": 500})
    state = battle(skill, [(4, 3)])
    state.units[U2].max_hp = 36  # 邊界測試要偶數 HP（範本 HP 隨平衡調整）
    half = state.units[U2].max_hp // 2
    assert not _usable(_set_hp(battle(skill, [(4, 3)]), U2, half))  # 剛好 50% 不算「低於」
    assert _usable(_set_hp(battle(skill, [(4, 3)]), U2, half - 1))


def test_skill_condition_self_hp_below() -> None:
    skill = _with_condition({"type": "self_hp_below", "permille": 500})
    healthy = battle(skill, [(4, 3)])
    hurt = _set_hp(battle(skill, [(4, 3)]), U1, healthy.units[U1].max_hp // 2 - 1)
    _assert_gate(hurt, healthy)


def test_skill_condition_height_advantage() -> None:
    skill = _with_condition({"type": "height_advantage"})
    above = battle(skill, [(4, 3)], heights=HIGH_CASTER)
    level = battle(skill, [(4, 3)])
    _assert_gate(above, level)
    below = battle(skill, [(3, 3)], caster=(4, 3), heights=HIGH_CASTER)  # 施放者較低
    assert not _usable(below)


def test_skill_condition_target_on_surface() -> None:
    skill = _with_condition({"type": "target_on_surface", "surface": "water"})
    wet = battle(skill, [(4, 3)], surfaces=((4, 3, "water"),))
    dry = battle(skill, [(4, 3)], surfaces=((4, 3, "oil"),))
    _assert_gate(wet, dry)


def test_skill_condition_target_has_status() -> None:
    skill = _with_condition({"type": "target_has_status", "status": "burning"})
    lit = _burning(battle(skill, [(4, 3)]), U2)
    _assert_gate(lit, battle(skill, [(4, 3)]))


def test_an_area_skill_condition_needs_one_matching_unit_in_the_area() -> None:
    skill = make_skill(
        SID, {"type": "square3", "range": 5}, [{"type": "damage", "dice": "1d6", "element": "fire"}]
    ).model_copy(update={"condition": ConditionSpec(type="target_has_status", status="burning")})
    state = battle(skill, [(4, 3), (5, 3)])
    assert not _usable(state)
    assert _usable(_burning(state, U3))  # 範圍（中心 (4,3) 的 3×3）內有一個燃燒中的敵人


def test_no_condition_means_always_usable() -> None:
    assert _usable(battle(_with_condition(None), [(4, 3)]))


# ---------------------------------------------------------------------------
# 效果層級：對每個對象分別判斷，不成立的對象不受這個效果影響
# ---------------------------------------------------------------------------


def _applied(result: Any) -> set[str]:
    return {e.target_id for e in of(result, StatusApplied) if e.status_id == "burning"}


def test_effect_condition_target_hp_below() -> None:
    skill = _skill({"type": "target_hp_below", "permille": 400}, effect_level=True)
    state = battle(skill, [(4, 3)])
    low = _set_hp(battle(skill, [(4, 3)]), U2, state.units[U2].max_hp * 300 // 1000)
    assert _applied(cast(hit_with(low), target_id=U2)) == {U2}
    assert _applied(cast(hit_with(state), target_id=U2)) == set()


def test_effect_condition_self_hp_below() -> None:
    skill = _skill({"type": "self_hp_below", "permille": 500}, effect_level=True)
    state = battle(skill, [(4, 3)])
    hurt = _set_hp(battle(skill, [(4, 3)]), U1, state.units[U1].max_hp // 4)
    assert _applied(cast(hit_with(hurt), target_id=U2)) == {U2}
    assert _applied(cast(hit_with(state), target_id=U2)) == set()


def test_effect_condition_height_advantage() -> None:
    skill = _skill({"type": "height_advantage"}, effect_level=True)
    assert _applied(cast(hit_with(battle(skill, [(4, 3)], heights=HIGH_CASTER)), target_id=U2)) == {
        U2
    }
    assert _applied(cast(hit_with(battle(skill, [(4, 3)])), target_id=U2)) == set()


def test_effect_condition_target_on_surface() -> None:
    skill = _skill({"type": "target_on_surface", "surface": "water"}, effect_level=True)
    wet = battle(skill, [(4, 3)], surfaces=((4, 3, "water"),))
    dry = battle(skill, [(4, 3)])
    assert _applied(cast(hit_with(wet), target_id=U2)) == {U2}
    assert _applied(cast(hit_with(dry), target_id=U2)) == set()


def test_effect_condition_target_has_status() -> None:
    skill = _skill({"type": "target_has_status", "status": "prone"}, effect_level=True)
    prone = battle(skill, [(4, 3)])
    prone.units[U2].statuses.append(StatusInstance("prone", None))
    assert _applied(cast(hit_with(prone), target_id=U2)) == {U2}
    assert _applied(cast(hit_with(battle(skill, [(4, 3)])), target_id=U2)) == set()


def test_effect_condition_is_judged_per_target() -> None:
    """同一次範圍技能：只有站在水面的敵人吃到有條件的效果。"""
    effect = {**BURN, "condition": {"type": "target_on_surface", "surface": "water"}}
    skill = make_skill(SID, {"type": "square3", "range": 5}, [effect])
    state = battle(skill, [(4, 3), (5, 3)], surfaces=((5, 3, "water"),))
    result = cast(hit_with(state, [(20, 19)]), target_pos=_pos(4, 3))
    assert len(of(result, AttackRolled)) == 2  # 命中照常每個敵人各擲一次
    assert _applied(result) == {U3}


def test_effect_condition_sees_the_state_left_by_earlier_effects() -> None:
    """效果依序結算：第一個效果施加燃燒，第二個「目標燃燒中才…」的效果因此成立。"""
    second = {
        "type": "apply_status",
        "status": "prone",
        "condition": {"type": "target_has_status", "status": "burning"},
    }
    skill = make_skill(SID, SINGLE5, [BURN, second])
    result = cast(hit_with(battle(skill, [(4, 3)])), target_id=U2)
    assert {e.status_id for e in of(result, StatusApplied)} == {"burning", "prone"}
    swapped = make_skill(SID, SINGLE5, [second, BURN])
    result = cast(hit_with(battle(swapped, [(4, 3)])), target_id=U2)
    assert {e.status_id for e in of(result, StatusApplied)} == {"burning"}


def test_effect_condition_on_a_ground_effect_filters_tiles() -> None:
    effect = {
        "type": "create_surface",
        "surface": "fire",
        "condition": {"type": "target_on_surface", "surface": "oil"},
    }
    skill = make_skill(SID, {"type": "cross", "range": 3}, [effect])
    state = battle(skill, [(6, 6)], surfaces=((4, 3, "oil"),))
    result = cast(state, target_pos=_pos(3, 3))
    assert result.state.tile(4, 3).surface is Surface.FIRE
    assert result.state.tile(3, 3).surface is Surface.NONE


def test_effect_condition_on_teleport_is_judged_on_the_caster() -> None:
    effect = {"type": "teleport", "condition": {"type": "self_hp_below", "permille": 500}}
    skill = make_skill(SID, {"type": "ground_tile", "range": 3}, [effect])
    healthy = battle(skill, [(6, 6)])
    result = cast(healthy, target_pos=_pos(4, 3))
    assert result.state.units[U1].xy == (3, 3)  # 條件不成立：沒有傳送
    hurt = _set_hp(battle(skill, [(6, 6)]), U1, healthy.units[U1].max_hp // 4)
    assert cast(hurt, target_pos=_pos(4, 3)).state.units[U1].xy == (4, 3)


def _pos(x: int, y: int) -> Pos:
    return Pos(x=x, y=y)
