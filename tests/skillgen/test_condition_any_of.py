"""Phase 3W-2b 第 4 點：條件真正的「或」（``ConditionSpec.any_of``）。

表格測試（成立／不成立的每種組合）、schema 限制、預算（取最寬鬆倍率）、驗證器、卡片文字，以及修正類
「第二個關鍵字」「條件放寬」改用它之後的行為（實戰中任何一個分支成立，修正就生效）。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.content.skills import ConditionSpec, SkillDef, condition_text
from trpg.engine import BattleState
from trpg.engine import modifiers as mods
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.state import StatusInstance
from trpg.shared.rng import Rng
from trpg.shared.types import Team
from trpg.skillgen.budget import _condition_multiplier, skill_budget
from trpg.skillgen.flash_derive import apply_variation, at_tier
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.whiteboard import compose_whiteboard

BURNING: dict[str, Any] = {"type": "target_has_status", "status": "burning"}
WET_SURFACE: dict[str, Any] = {"type": "target_on_surface", "surface": "water"}
LOW_HP: dict[str, Any] = {"type": "target_hp_below", "permille": 400}
HEIGHT: dict[str, Any] = {"type": "height_advantage"}


def _spec(first: dict[str, Any], *others: dict[str, Any]) -> ConditionSpec:
    return ConditionSpec.model_validate({**first, "any_of": list(others)} if others else first)


def _scene() -> BattleState:
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    state = make_state(
        m,
        [
            spawn(Team.ALLY, (3, 3), caster_template([], max_hp=99)),
            spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=100)),
        ],
    )
    return give_turn(state, U1)


def _met(state: BattleState, spec: ConditionSpec) -> bool:
    foe = state.units[U2]
    return condition_met(state, state.units[U1], spec, Subject(foe, foe.xy))


# 每列：(目標燃燒中, 目標血量低, 預期 [A, B, A 或 B])
TABLE = [
    (False, False, (False, False, False)),
    (True, False, (True, False, True)),
    (False, True, (False, True, True)),
    (True, True, (True, True, True)),
]


@pytest.mark.parametrize(("burning", "low", "expected"), TABLE)
def test_or_is_true_when_any_branch_holds(
    burning: bool, low: bool, expected: tuple[bool, bool, bool]
) -> None:
    state = _scene()
    foe = state.units[U2]
    if burning:
        foe.statuses.append(StatusInstance("burning", 2))
    if low:
        foe.hp = 30
    a, b = _spec(BURNING), _spec(LOW_HP)
    either = _spec(BURNING, LOW_HP)
    assert (_met(state, a), _met(state, b), _met(state, either)) == expected


def test_three_way_or_and_order_does_not_matter() -> None:
    state = _scene()
    state.units[U2].hp = 30
    assert _met(state, _spec(BURNING, WET_SURFACE, LOW_HP))
    assert _met(state, _spec(LOW_HP, BURNING, WET_SURFACE))
    assert not _met(state, _spec(BURNING, WET_SURFACE, HEIGHT))


def test_without_any_of_nothing_changes() -> None:
    state = _scene()
    assert not _met(state, _spec(BURNING))
    assert condition_met(state, state.units[U1], None, Subject(None, (0, 0)))


def test_schema_limits() -> None:
    with pytest.raises(ValidationError):  # 不可巢狀
        _spec(BURNING, {**LOW_HP, "any_of": [HEIGHT]})
    with pytest.raises(ValidationError):  # 最多再 2 個
        _spec(BURNING, LOW_HP, WET_SURFACE, HEIGHT)
    with pytest.raises(ValidationError):  # 不可是空的
        ConditionSpec.model_validate({**BURNING, "any_of": []})
    assert _spec(BURNING).any_of is None


def test_card_text_joins_branches_with_or() -> None:
    text = condition_text(_spec(BURNING, LOW_HP), status_name=lambda s: "燃燒")
    assert "燃燒" in text and "，或" in text and "40%" in text


def test_budget_uses_the_most_lenient_multiplier() -> None:
    lib = library()
    budget = lib.budget
    harsh = next(c for c in lib.ruleset.conditions.conditions if c.harshness == "harsh")
    common = next(c for c in lib.ruleset.conditions.conditions if c.harshness == "common")
    assert budget.condition_permille["common"] > budget.condition_permille["harsh"]
    table = lib.ruleset.conditions.by_id()
    alone = _condition_multiplier(harsh.id, table, budget)
    mixed = _condition_multiplier(
        harsh.id, table, budget, (ConditionSpec.model_validate({"type": common.id}),)
    )
    assert mixed > alone
    assert mixed == _condition_multiplier(common.id, table, budget)


# ---------------------------------------------------------------------------
# 修正類「第二個關鍵字」「條件放寬」
# ---------------------------------------------------------------------------


def _modifier_skills() -> list[SkillDef]:
    lib = library()
    return [
        at_tier(s, 3)
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "modifier" and s.modifiers and s.modifiers[0].condition is not None
    ]


def _board_modifier(seed: int) -> SkillDef:
    """3W-4b 的修正型被動白板（燃燒中的敵人受你的傷害提高之類）。"""
    return compose_whiteboard(seed, kind="passive", tier=3, library=library())


def _modifier_whiteboards() -> list[SkillDef]:
    out = []
    for seed in range(60):
        board = _board_modifier(seed)
        if board.kind == "modifier" and board.modifiers and board.modifiers[0].condition:
            out.append(board)
    return out


def test_whiteboards_with_a_modifier_condition_exist() -> None:
    assert len(_modifier_whiteboards()) >= 1


def test_second_keyword_makes_a_single_rule_with_any_of() -> None:
    lib = library()
    boards = _modifier_whiteboards()
    made = 0
    for board in boards:
        old = board.modifiers[0].condition
        assert old is not None
        for keyword in ("wet", "ignite", "frozen"):
            variation = Variation(
                source="minor", template="mod_keyword", category="modifier", keyword=keyword
            )
            got = apply_variation(lib, board, variation, bonus=40, rng=Rng(5))
            if got is None:
                continue
            made += 1
            assert len(got.modifiers) == len(board.modifiers)  # 規則數不變，條件變成「或」
            new = got.modifiers[0].condition
            assert new is not None and new.any_of is not None and len(new.any_of) == 1
            assert new.type == old.type
            assert validate_skill(got, lib) == []
            report = skill_budget(got, lib)
            assert report.ratio >= report.min_ratio
    assert made >= 1


def test_relax_adds_an_or_branch_and_still_validates() -> None:
    lib = library()
    made = 0
    for board in _modifier_whiteboards():
        variation = Variation(source="minor", template="mod_relax", category="modifier")
        got = apply_variation(lib, board, variation, bonus=40, rng=Rng(5))
        if got is None:
            continue
        made += 1
        old = board.modifiers[0].condition
        new = got.modifiers[0].condition
        assert old is not None and new is not None
        assert new.permille != old.permille or new.any_of is not None  # 放寬了
        assert validate_skill(got, lib) == []
    assert made >= 1


def test_modifier_applies_when_either_branch_holds_in_the_engine() -> None:
    """引擎端：帶 ``any_of`` 的修正規則，任何一個分支成立就生效（預算之外的實戰一致）。"""
    lib = library()
    rule = SkillDef.model_validate(
        {
            "id": "skill_t_or_mod",
            "name_zh": "測試或修正",
            "tier": 3,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": "any",
            "ap_cost": None,
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": [
                {
                    "applies_to": {"all_attacks": True},
                    "change": {"damage_permille": 200},
                    "condition": {**BURNING, "any_of": [LOW_HP]},
                }
            ],
        }
    )
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(4, 3)])
    results = []
    for burning, low in ((False, False), (True, False), (False, True), (True, True)):
        state = give_turn(
            make_state(
                m,
                [
                    spawn(Team.ALLY, (3, 3), caster_template([rule], max_hp=99)),
                    spawn(Team.ENEMY, (4, 3), no_reactions(max_hp=100)),
                ],
                skills=[rule],
            ),
            U1,
        )
        foe = state.units[U2]
        if burning:
            foe.statuses.append(StatusInstance("burning", 2))
        if low:
            foe.hp = 30
        subject = Subject(foe, foe.xy)
        results.append(mods.damage_permille(state, state.units[U1], mods.ATTACK, subject))
    assert results[0] == 1000
    assert results[1] == results[2] == results[3] == 1200
    del lib
