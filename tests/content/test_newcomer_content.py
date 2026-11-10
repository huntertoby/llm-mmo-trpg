"""主題合併（R2）。

原 ``test_newcomer_content_6f2.py``：

``world/newcomer.yaml`` 與新手任務各步的 ``teach``（Phase 6F-2；#99、#125）的 schema。

原 ``test_newcomer_guide_name_rt5c.py``：

新手指引點名任務 NPC 的完整名字（Phase RT-5c 小修 10；docs/archive/art/RT-5b檢查.md 第 2 節）。

前端用指引文字裡的名字認出主線給任務的人（``opening.mainQuestNpc``），文字一改成不含名字，畫面就默默退回
三個一樣的「！」。這裡鎖住：任務欄（``guide_town_zh``）與主城指引（``guide_capital_zh``）都含新手任務
（``kind: starter``）給任務的人的完整名字，而且不是只含別名（「婆婆」不算「渡婆婆」）。
之後 ``GuideView`` 加 ``npc`` 欄位就不用再比對名字（技術債）。
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.library.world import _range_problems, _RangeRefs
from trpg.content.world_newcomer import (
    BATTLE_HINT_TRIGGERS,
    BattleHint,
    NewcomerContent,
    RangeContent,
)
from trpg.content.world_quests import QuestStepDef

# --- 原 test_newcomer_content_6f2.py ---

BASE: dict[str, Any] = {
    "start_region": "cloud_ridge",
    "guide_capital_zh": "到霧渡鎮找渡婆婆",
    "guide_capital_how_zh": "站上傳送陣",
    "guide_town_zh": "找渡婆婆",
    "main_advice_zh": "建議先完成{quest}",
}


def _range_data(library: ContentLibrary) -> dict[str, Any]:
    assert library.world_newcomer is not None and library.world_newcomer.range is not None
    return library.world_newcomer.range.model_dump(mode="json")


def _problems(library: ContentLibrary, data: dict[str, Any]) -> list[str]:
    refs = _RangeRefs(
        skills=library.skills, weapons=library.weapons, units=library.units, maps=library.maps
    )
    return _range_problems(RangeContent.model_validate(data), refs)


def test_range_starters_loaded(library: ContentLibrary) -> None:
    """#150 入門武器（OB-1）。"""
    data = _range_data(library)
    assert data["starters"] == {
        "melee": "one_handed_sword",
        "ranged": "bow",
        "focus": "fire_staff",
    }
    assert _problems(library, data) == []


def test_range_starters_must_cover_racks(library: ContentLibrary) -> None:
    data = _range_data(library)
    del data["starters"]["focus"]
    with pytest.raises(ValidationError, match="starters"):
        RangeContent.model_validate(data)


@pytest.mark.parametrize(("weapon", "message"), [("no_such", "不存在"), ("bow", "不是可用的")])
def test_range_starter_must_exist_and_match_class(
    library: ContentLibrary, weapon: str, message: str
) -> None:
    data = _range_data(library)
    data["starters"]["melee"] = weapon
    assert any(message in p for p in _problems(library, data))


def test_loaded_content(library: ContentLibrary) -> None:
    lib = library
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


# --- 原 test_newcomer_guide_name_rt5c.py ---


def test_guide_text_names_the_starter_giver_in_full(library: ContentLibrary) -> None:
    lib = library
    newcomer = lib.world_newcomer
    assert newcomer is not None
    region = newcomer.start_region
    table = lib.world_quests.quests[region]
    starters = [q for q in table.quests if q.kind == "starter"]
    assert len(starters) == 1
    giver = starters[0].giver
    npcs = {n.id: n for n in lib.world_event_content.npcs[region].npcs}
    assert giver in npcs
    name = npcs[giver].name_zh
    assert name == "渡婆婆"
    for text in (newcomer.guide_town_zh, newcomer.guide_capital_zh):
        assert name in text, f"指引「{text}」沒有點名 {name}"
    # 別名比完整名字短、被包在完整名字裡：只靠子字串會把「婆婆」配到「渡婆婆」，前端改用完整名字比對
    aliases = list(getattr(npcs[giver], "aliases_zh", []) or [])
    assert "婆婆" in aliases
    assert all(alias in name for alias in aliases)
