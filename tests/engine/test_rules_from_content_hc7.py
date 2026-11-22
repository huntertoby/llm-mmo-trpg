"""HC-7 a.1：引擎寫死的規則數字搬進 content（``core.yaml``、``ai_profiles.yaml``、詞條、誓約），
值照搬；引擎改讀規則包。"""

from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.content.equipment import AttackAffix
from trpg.content.rules import CoreRules
from trpg.content.world_oaths import OathCheck
from trpg.engine import build_setup
from trpg.engine.battle import begin_battle
from trpg.engine.oaths import OathSetup
from trpg.engine.parts import part_reason_zh
from trpg.engine.rules.combat import positional_bonus, weapon_profile
from trpg.engine.state import BattleState


def _state() -> BattleState:
    setup = build_setup(library(), "test_flat_6x6", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    return begin_battle(setup, 2).state


def _with_core(state: BattleState, **update: int) -> BattleState:
    core = state.ruleset.core.model_copy(update=update)
    state.ruleset = state.ruleset.model_copy(update={"core": core})
    return state


def test_values_moved_unchanged() -> None:
    rules = library().ruleset
    assert rules.core.crit_range_floor == 2
    assert rules.core.opening_status_max_duration == 2
    assert rules.core.defense_break_default_permille == 100
    assert rules.core.boss_parts.high_or_far_distance == 4
    assert (rules.ai.infused_pick.enemy_points, rules.ai.infused_pick.ally_hit_penalty) == (10, 15)


@pytest.mark.parametrize(
    "field", ["crit_range_floor", "opening_status_max_duration", "defense_break_default_permille"]
)
def test_core_fields_are_required(field: str) -> None:
    data = library().ruleset.core.model_dump()
    del data[field]
    with pytest.raises(ValidationError, match=field):
        CoreRules.model_validate(data)


def test_crit_range_floor_is_read_from_rules() -> None:
    state = _state()
    ally, enemy = sorted(state.units.values(), key=lambda u: u.team.value)[:2]
    profile = replace(weapon_profile(state, ally), crit_range=1)
    assert positional_bonus(state, ally, enemy, profile).crit_range == 2
    _with_core(state, crit_range_floor=5)
    assert positional_bonus(state, ally, enemy, profile).crit_range == 5


def test_part_reason_far_distance_is_read_from_rules() -> None:
    rules = library().ruleset
    assert part_reason_zh(rules, "need_high_or_far") == "要從高處（高 1 層以上）或 4 格外才打得到"
    parts = rules.core.boss_parts.model_copy(update={"high_or_far_distance": 6})
    changed = rules.model_copy(update={"core": rules.core.model_copy(update={"boss_parts": parts})})
    assert "6 格外" in part_reason_zh(changed, "need_high_or_far")
    assert part_reason_zh(changed, "broken") == "已經破了"


def test_inscribe_rune_needs_rounds() -> None:
    affix = library().affixes["affix_attack_rune_inscribe"]
    assert isinstance(affix, AttackAffix)
    assert affix.rune_rounds == 2  # 內容檔寫明（原本引擎的預設 2）
    data = affix.model_dump(exclude={"rune_rounds"})
    with pytest.raises(ValidationError, match="rune_rounds"):
        AttackAffix.model_validate(data)


def test_oath_setup_needs_penalty_rounds() -> None:
    check = OathCheck(kind="attack_each_turn")
    with pytest.raises(ValidationError, match="penalty_rounds"):
        OathSetup(template="oath_test", check=check)  # type: ignore[call-arg]
