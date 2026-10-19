"""賭博型技能的文字（Phase 3D-7a）：技能卡片、代價（失手反噬）與戰鬥紀錄。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from tests.engine.skill_helpers import SID, U1, U2, battle, cast, of
from tests.engine.test_gamble import gamble_skill, miss_skill, script_randint
from trpg.engine.events import BacklashTriggered, DamageDealt, GambleRolled
from trpg.narrative.events import describe_event
from trpg.narrative.skills import miss_text, skill_card


def test_the_gamble_card_lists_both_branches_with_their_chances() -> None:
    lib = library()
    card = skill_card(lib, lib.skills["skill_blood_sacrifice"])
    assert card.effects[1] == (
        "賭注（命中後擲 d1000）——60%：本次傷害 ×2｜40%：你受到本次傷害的 50%（不致命）"
    )
    assert "gamble" in card.tags


def test_the_miss_backlash_shows_in_the_cost_and_in_miss_text() -> None:
    lib = library()
    skill = lib.skills["skill_all_in"]
    assert miss_text(lib, skill) == "失手（含自然 1）時：你獲得「倒地」"
    assert skill_card(lib, skill).cost[-1] == "失手（含自然 1）時：你獲得「倒地」"
    assert miss_text(lib, lib.skills["skill_blood_sacrifice"]) is None


def test_the_battle_log_describes_the_roll_the_backlash_and_the_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = battle(gamble_skill(), [(5, 3)])
    missed = battle(miss_skill(), [(5, 3)])
    script_randint(monkeypatch, [19, 900, 3, 4])
    result = cast(state, target_id=U2)
    (rolled,) = of(result, GambleRolled)
    text = describe_event(rolled, result.state) or ""
    assert "賭上了" in text and "d1000=900" in text and "60%" in text and text.endswith("失敗")
    back = [e for e in of(result, DamageDealt) if e.cause == "backlash"]
    assert "反噬物理傷害" in (describe_event(back[0], result.state) or "")
    script_randint(monkeypatch, [1])
    (trigger,) = of(cast(missed, target_id=U2), BacklashTriggered)
    assert "失手了，遭到反噬" in (describe_event(trigger, missed) or "")
    assert SID in trigger.skill_id and trigger.unit_id == U1
