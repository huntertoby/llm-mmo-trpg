"""Phase 2B-1 3.1／3.3／3.4：新狀態與控制規則的內容 schema。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.battle import StatusDef
from trpg.content.library import Ruleset, load_library
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute

# (預設持續, save_attr, control_group)
EXPECTED = {
    "slow": (2, Attribute.DEX, "movement"),
    "root": (1, Attribute.STR, "movement"),
    "stun": (1, Attribute.CON, "hard"),
    "frozen": (1, Attribute.CON, "hard"),
    "weaken": (2, Attribute.CON, None),
    "vulnerable": (2, Attribute.WIL, None),
    "bleed": (3, None, None),
    "poison": (3, None, None),
}


@pytest.mark.parametrize(("status_id", "expected"), sorted(EXPECTED.items()))
def test_new_statuses_match_the_spec_table(
    status_id: str, expected: tuple[int, Attribute | None, str | None]
) -> None:
    duration, save_attr, group = expected
    definition = library().ruleset.status_def(status_id)
    assert definition.duration == duration
    assert definition.expires == "turn_end" and definition.stacking == "refresh"
    assert (definition.save_attr, definition.control_group) == (save_attr, group)


def test_new_statuses_carry_their_numbers_as_data() -> None:
    rules = library().ruleset
    assert rules.status_def("slow").move_permille == 500
    assert rules.status_def("root").prevents_move
    assert rules.status_def("stun").skip_turn
    assert rules.status_def("weaken").damage_dealt_permille == 750
    assert rules.status_def("vulnerable").damage_taken_permille == 1250
    assert rules.status_def("poison").healing_received_permille == 500
    bleed = rules.status_def("bleed").on_turn_start_damage
    poison = rules.status_def("poison").on_turn_start_damage
    assert bleed is not None and (bleed.dice.count, bleed.dice.sides) == (1, 4)
    assert poison is not None and (poison.dice.count, poison.dice.sides) == (1, 4)
    assert (str(bleed.element), str(poison.element)) == ("physical", "poison")


def test_core_rules_define_diminishing_returns_and_boss_conversion() -> None:
    core = library().ruleset.core
    assert core.control_dr_rounds == 2
    assert core.control_dr_resist_permille == 1500
    assert core.boss_control_conversion == {"stun": "slow", "frozen": "slow"}


def test_a_control_status_needs_a_save_attribute() -> None:
    with pytest.raises(ValidationError, match="save_attr"):
        StatusDef(
            id="freeze",
            name_zh="凍結",
            description_zh="測試",
            duration=1,
            expires="turn_end",
            control_group="hard",
        )


def test_boss_conversion_must_reference_known_statuses() -> None:
    rules = library().ruleset
    data = rules.model_dump(mode="json")
    data["core"]["boss_control_conversion"] = {"stun": "ghost"}
    with pytest.raises(ValidationError, match="ghost"):
        Ruleset.model_validate(data)
    data["core"]["boss_control_conversion"] = {"slow": "root"}  # 來源必須是 hard 類別
    with pytest.raises(ValidationError, match="hard"):
        Ruleset.model_validate(data)


def test_ai_status_values_must_reference_known_statuses(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    path = root / "ai_profiles.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    load_library(root)  # 對照組：原樣可以載入
    text = path.read_text(encoding="utf-8").replace(
        "status_values: {", "status_values: {ghost: 1, "
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ContentError, match="ghost"):
        load_library(root)
