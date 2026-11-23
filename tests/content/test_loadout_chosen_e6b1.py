"""E6-b1 第 3 項：裝備快照帶玩家的勾選（``Loadout.chosen``，08 8.27、8.30 第 4 點，#180）。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.test_gear import _loadout
from trpg.content.equipment import Loadout, chosen_key
from trpg.engine.runner import LOG_FORMAT

GRAPPLE = ("affix_act_grapple", None)


def test_chosen_defaults_to_empty_and_is_not_dumped() -> None:
    loadout = _loadout({"main_hand": [GRAPPLE]})
    assert loadout.chosen == ()
    assert "chosen" not in loadout.model_dump(mode="json")
    assert "chosen" not in Loadout().model_dump(mode="json")


def test_chosen_round_trips() -> None:
    loadout = _loadout({"main_hand": [GRAPPLE]}).model_copy(
        update={"chosen": (chosen_key("main_hand", GRAPPLE[0]),)}
    )
    dumped = loadout.model_dump(mode="json")
    assert dumped["chosen"] == ["main_hand:affix_act_grapple"]
    assert Loadout.model_validate(dumped) == loadout


@pytest.mark.parametrize(
    "bad",
    [
        ("affix_act_grapple",),  # 沒有欄位
        ("no_such_slot:affix_act_grapple",),
        ("main_hand:",),
        ("main_hand:affix_a", "main_hand:affix_a"),  # 重複
    ],
)
def test_chosen_must_be_slot_and_affix_id(bad: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        Loadout(chosen=bad)


def test_stale_choice_is_not_an_error() -> None:
    """換裝後留下的舊勾選（身上沒有那條詞條）不算錯誤。"""
    Loadout(chosen=("feet:affix_no_longer_worn",))


def test_log_format_is_139() -> None:
    prefix, _, number = LOG_FORMAT.rpartition("/")
    assert prefix == "trpg-battle-log"
    assert int(number) >= 139
