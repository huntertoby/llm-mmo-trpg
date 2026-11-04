"""``world/newcomer.yaml`` 與新手任務各步的 ``teach``（Phase 6F-2；#99、#125）的 schema。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import load_library
from trpg.content.world_newcomer import BATTLE_HINT_TRIGGERS, BattleHint, NewcomerContent
from trpg.content.world_quests import QuestStepDef

BASE: dict[str, Any] = {
    "start_region": "cloud_ridge",
    "guide_capital_zh": "到霧渡鎮找渡婆婆",
    "guide_capital_how_zh": "站上傳送陣",
    "guide_town_zh": "找渡婆婆",
    "main_advice_zh": "建議先完成{quest}",
}


def test_loaded_content() -> None:
    lib = load_library()
    newcomer = lib.world_newcomer
    assert newcomer is not None
    assert {h.trigger for h in newcomer.battle_hints} == {
        "ice_present",
        "trap_present",
        "lethal_terrain",
        "pushed",
    }
    starter = lib.world_quests.quest("cloud_ridge", "starter_ferry")
    assert starter is not None
    assert [[h.id for h in s.teach] for s in starter.steps] == [
        ["move_attack"],
        ["water_lightning", "freeze_water"],
        ["reaction_auto"],
    ]
    hints = [*newcomer.battle_hints, *(h for s in starter.steps for h in s.teach)]
    assert all(h.trigger in BATTLE_HINT_TRIGGERS for h in hints)


def test_newcomer_rejects_duplicates_and_bad_advice() -> None:
    hint = {"id": "a", "trigger": "pushed", "text_zh": "x"}
    with pytest.raises(ValidationError, match="重複"):
        NewcomerContent.model_validate({**BASE, "battle_hints": [hint, hint]})
    with pytest.raises(ValidationError, match="quest"):
        NewcomerContent.model_validate({**BASE, "main_advice_zh": "先做新手路"})
    NewcomerContent.model_validate(BASE)


def test_hint_schema() -> None:
    with pytest.raises(ValidationError):
        BattleHint.model_validate({"id": "a", "trigger": "unknown", "text_zh": "x"})
    with pytest.raises(ValidationError):
        BattleHint.model_validate({"id": "a", "trigger": "pushed", "text_zh": "長" * 61})
    step = {
        "id": "s",
        "text_zh": "t",
        "when": [{"kind": "win_battle"}],
        "teach": [{"id": "a", "trigger": "battle_start", "text_zh": "x"}] * 2,
    }
    with pytest.raises(ValidationError, match="teach"):
        QuestStepDef.model_validate(step)
