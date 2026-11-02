"""NPC 好感度（Phase 5B-4；``docs/phases/Phase5計畫.md`` 16.6）。

- 每個 NPC 一個值（−100～100，沒有＝0），5 級門檻照 09 9.6.11 #116
  （``content/world/affinity.yaml``）。
- 只影響對話內容與任務分支，**不影響任何數值**（9.6.7 #5）。
- 聊天能給什麼（玩法 PM 定，照 #85 2a）：中立給一般傳聞、友善給隱藏任務入口、信賴才說人設卡的祕密。
  :func:`talk_entries` 是引擎（``talk`` 動作）與外層（說書人的 ``hooks_zh``）共用的同一個函式。

純函式：不讀時間、不耗亂數。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.world_quests import (
    AFFINITY_RANKS,
    AffinityRank,
    AffinityRankDef,
    AffinityRules,
    SocialTable,
    TalkEntry,
)
from trpg.world.actions import AffinityChangedEvent
from trpg.world.state import CharacterState

__all__ = [
    "DEFAULT_AFFINITY_RULES",
    "affinity_of",
    "affinity_rules",
    "change_affinity",
    "rank_at_least",
    "rank_of",
    "social_of",
    "talk_entries",
    "trusted_npcs",
]

DEFAULT_AFFINITY_RULES = AffinityRules(
    ranks=(
        AffinityRankDef(id="hostile", name_zh="敵視", min=-100),
        AffinityRankDef(id="cold", name_zh="冷淡", min=-49),
        AffinityRankDef(id="neutral", name_zh="中立", min=-9),
        AffinityRankDef(id="friendly", name_zh="友善", min=20),
        AffinityRankDef(id="trusted", name_zh="信賴", min=60),
    )
)
"""沒有 ``world/affinity.yaml`` 時的級距（9.6.11 #116）。"""


def affinity_rules(library: ContentLibrary) -> AffinityRules:
    rules = library.world_quests.affinity
    return DEFAULT_AFFINITY_RULES if rules is None else rules


def affinity_of(char: CharacterState, npc: str) -> int:
    """角色對 ``npc`` 的好感度（沒有紀錄＝0）。"""
    return char.affinity.get(npc, 0)


def rank_of(library: ContentLibrary, char: CharacterState, npc: str) -> AffinityRank:
    return affinity_rules(library).rank_of(affinity_of(char, npc))


def rank_at_least(rank: AffinityRank, need: AffinityRank) -> bool:
    return AFFINITY_RANKS.index(rank) >= AFFINITY_RANKS.index(need)


def change_affinity(
    library: ContentLibrary, char: CharacterState, npc: str, delta: int, source: str
) -> tuple[CharacterState, AffinityChangedEvent]:
    """好感度加減 ``delta``（夾在上下限）。"""
    rules = affinity_rules(library)
    before = affinity_of(char, npc)
    value = rules.clamp(before + delta)
    affinity = {**char.affinity, npc: value}
    char = char.model_copy(update={"affinity": dict(sorted(affinity.items()))})
    event = AffinityChangedEvent(
        npc=npc,
        delta=value - before,
        value=value,
        from_rank=rules.rank_of(before),
        rank=rules.rank_of(value),
        source=source,
    )
    return char, event


def social_of(library: ContentLibrary, region: str) -> SocialTable | None:
    return library.world_quests.social.get(region)


def talk_entries(library: ContentLibrary, char: CharacterState, npc: str) -> tuple[TalkEntry, ...]:
    """``npc`` 依角色目前的好感度能給的聊天內容（資料順序；敵視、冷淡時沒有）。"""
    table = social_of(library, char.region)
    if table is None:
        return ()
    rank = rank_of(library, char, npc)
    return tuple(t for t in table.talk if t.npc == npc and rank_at_least(rank, t.rank))


def trusted_npcs(library: ContentLibrary, char: CharacterState) -> frozenset[str]:
    """角色信賴級的 NPC（他們的祕密可以說出口，玩法 PM 定）。"""
    rules = affinity_rules(library)
    return frozenset(n for n, v in char.affinity.items() if rules.rank_of(v) == "trusted")
