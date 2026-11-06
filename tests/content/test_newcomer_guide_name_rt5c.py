"""新手指引點名任務 NPC 的完整名字（Phase RT-5c 小修 10；docs/archive/art/RT-5b檢查.md 第 2 節）。

前端用指引文字裡的名字認出主線給任務的人（``opening.mainQuestNpc``），文字一改成不含名字，畫面就默默退回
三個一樣的「！」。這裡鎖住：任務欄（``guide_town_zh``）與主城指引（``guide_capital_zh``）都含新手任務
（``kind: starter``）給任務的人的完整名字，而且不是只含別名（「婆婆」不算「渡婆婆」）。
之後 ``GuideView`` 加 ``npc`` 欄位就不用再比對名字（技術債）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary


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
