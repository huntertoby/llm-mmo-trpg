"""看目標的暴擊傷害加成提示（CR-1c，``docs/design/05-戰鬥.md`` 5.4.2 第 8 點）：單位有「條件看目標」
的暴擊傷害修正技時，「▸ 詳細」最後加一行「另有看目標的加成，攻擊預覽時才算」；沒有時不出現。
單位卡上，看不到修正技名稱的陣營（其他陣營）一律不給這一行；主角面板（一輪中）也有。"""

from __future__ import annotations

from typing import Any

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import SID, U1, U2, battle
from trpg.api.hidden_info import mask_view
from trpg.content.skills import SkillDef
from trpg.engine import BattleState
from trpg.engine.crit_damage import TARGET_RULE_HINT_ZH
from trpg.engine.view import UnitView, project_for
from trpg.shared.types import Team

TARGET = {"type": "target_hp_below", "permille": 400}
SELF = {"type": "self_hp_below", "permille": 500}


def _modifier(condition: dict[str, Any] | None, change: int = 250) -> SkillDef:
    data = library().ruleset.skill_def("skill_attack_mastery").model_dump(mode="json")
    rule: dict[str, Any] = {
        "applies_to": {"all_attacks": True},
        "change": {"crit_damage_permille": change},
    }
    if condition is not None:
        rule["condition"] = condition
    data.update(id=SID, name_zh="斬首", modifiers=[rule])
    return SkillDef.model_validate(data)


def _view(state: BattleState, viewer: Team, uid: str = U1) -> UnitView:
    return next(u for u in project_for(state, viewer).units if u.id == uid)


def test_a_target_conditional_rule_adds_the_hint() -> None:
    state = battle(_modifier(TARGET), [(4, 3)])
    me = _view(state, Team.ALLY)
    assert me.crit_damage_hint_zh == TARGET_RULE_HINT_ZH == "另有看目標的加成，攻擊預覽時才算"
    # 數字不算看目標的加成（面板沒有目標），來源也不列它
    assert me.crit_damage_permille == 2000
    assert me.crit_damage_detail_zh is not None and "斬首" not in me.crit_damage_detail_zh


@pytest.mark.parametrize(
    "condition",
    [None, SELF],
    ids=["no-condition", "self-only"],
)
def test_no_hint_without_a_target_conditional_rule(condition: dict[str, Any] | None) -> None:
    state = battle(_modifier(condition), [(4, 3)])
    assert _view(state, Team.ALLY).crit_damage_hint_zh is None


def test_any_of_with_a_target_branch_counts() -> None:
    state = battle(_modifier({"type": "self_hp_below", "permille": 500, "any_of": [TARGET]}), [])
    assert _view(state, Team.ALLY).crit_damage_hint_zh == TARGET_RULE_HINT_ZH


def test_other_teams_never_see_the_hint() -> None:
    """看不到修正技名稱的陣營（其他陣營）：最保守，不透露有這類修正技。"""
    state = battle(_modifier(TARGET), [(4, 3)])
    foe_view = _view(state, Team.ENEMY)
    assert foe_view.crit_damage_permille == 2000
    assert foe_view.crit_damage_hint_zh is None


def test_hidden_units_hide_the_hint() -> None:
    state = battle(_modifier(TARGET), [(4, 3)])
    view = mask_view(project_for(state, Team.ALLY), frozenset({U2}))
    foe = next(u for u in view.units if u.id == U2)
    assert foe.crit_damage_hint_zh is None
