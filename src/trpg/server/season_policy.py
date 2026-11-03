"""季末重置政策表（Phase 5D-R2；09 9.7「季末重置」、#91）。

每個存檔模型的每個欄位標成一類：

- ``"numeric"``（數值類）：季末清掉（等級、技能、裝備、材料、任務幣、世界狀態……）。
- ``"memorial"``（紀念類）：季末保留（帳號、稱號、編年史、印記收藏、排行榜與 Boss 擊殺紀錄）。

這一段只有分類與檢查（``tests/test_architecture.py``：表裡每個模型的欄位都要分類，新增欄位沒分類
就失敗）；真正的重置流程在 5F-5。拿不準的欄位暫時標「數值類」（保守：季末會清掉），列在
:data:`PROVISIONAL`，待使用者決定。

角色（``CharacterState``）整個是數值類：#91 的「等級、技能、裝備、材料、任務幣」都在角色身上，
角色本身也清掉（角色上限按賽季算，帳號保留歸屬紀錄，5D-R2）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Literal

from pydantic import BaseModel

from trpg.server.accounts import AccountRecord
from trpg.server.chronicle import LeagueChronicle, LeagueChronicleRank, LeagueChronicleSeason
from trpg.server.first_kills import FirstKill
from trpg.server.league import LeagueMatch, LeagueRecord
from trpg.server.notes import LocationNote
from trpg.server.season_boss_board import BossBoardEntry
from trpg.world.state import CharacterState, RecipeRecord, WorldState

__all__ = [
    "MEMORIAL",
    "NUMERIC",
    "PROVISIONAL",
    "SAVED_MODELS",
    "SEASON_POLICY",
    "ResetKind",
    "fields_of_kind",
]

ResetKind = Literal["numeric", "memorial"]
NUMERIC: Final = "numeric"
MEMORIAL: Final = "memorial"


def _all(kind: ResetKind, *names: str) -> dict[str, ResetKind]:
    return dict.fromkeys(names, kind)


_CHARACTER: Final[dict[str, ResetKind]] = _all(
    NUMERIC,
    "format",
    "character_id",
    "hero",
    "origin",
    "level",
    "xp",
    "hp",
    "mana",
    "stamina",
    "region",
    "location",
    "supplies",
    "revealed",
    "perception_marks",
    "rng_counters",
    "pending_encounter",
    "camped_at",
    "bench",
    "fatigued",
    "attribute_points",
    "visited_towns",
    "event_steps",
    "pending_event",
    "threads",
    "next_battle",
    "insight",
    "flash",
    "flash_bases",
    "pending_flash",
    "skill_usage",
    "skill_tier",
    "attribute_spent",
    "elite_kills",
    "oath",
    "oath_broken_next",
    "oath_cooldown_until",
    "last_battle",
    "quests",
    "affinity",
    "pending_offers",
    "offers_made",
    "story_flags",
    "talk_days",
    "unlocked_skeletons",
    "opportunities",
    "opportunity_tier_ups",
    "finished_skeletons",
    "failed_skeletons",
    "met_opportunities",
    "opportunity_hint_day",
    "mercenaries",
    "shadows",
    "party_ai",
    "shadow_ai",
    "companions",
    "companion_bench",
    "companion_affinity",
    "gold",
    "quest_coins",
    "bag",
    "pouch",
    "shop_week",
    "shop_affinity",
    "gear",
    "equipment",
    "pending_loot",
    "gear_mods",
    "crafts",
    "generated_skills",
    "daily_goals",  # 5F-1 今日目標
    "seal_key_sources",  # 5F-3 封印鑰匙、區域 Boss 保底掉落
    "boss_drop_days",
    "bounty_days",  # 5F-1b 每天第一場懸賞遭遇
    "news_seen_at",  # 5F-1b「你不在的時候」看過的時刻
)

_WORLD: Final[dict[str, ResetKind]] = _all(
    NUMERIC,
    "format",
    "season_id",
    "season_seed",
    "season_start",
    "flags",
    "cleared",
    "threads",
    "timed_flags",
    "shadows",
    "recipes",
    "rolled_day",  # 5F-1 賽季日程
    "activity",
    "world_events",
    "bounty_claims",
    "level_bonus",
    "seal_keys",  # 5F-3 賽季 Boss（世界狀態；紀念的首殺與評分榜在伺服器檔）
    "seal_full_at",
    "boss_attempts",
    "boss_clears",
    "league_entries",  # 5F-4 影子循環賽的報名
)
"""世界狀態整個是數值類（#91「世界狀態」）；新的一季換新的 ``season_id``、種子與開始時間。"""

_RECIPE: Final[dict[str, ResetKind]] = {
    **_all(MEMORIAL, "code", "name_zh", "discoverer", "discoverer_name", "discovered_at"),
    "season_id": MEMORIAL,
    **_all(NUMERIC, "recipe", "hidden", "base", "steps", "listed"),
}
"""配方紀錄：首位發現者那部分（配方碼、名稱、發現者、時間、賽季）是紀念類，可以在 5F-5 收進
編年史；配方內容與配方表狀態跟著 ``WorldState.recipes`` 清掉（數值類）。"""

_FIRST_KILL: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "kind",
    "target",
    "target_name_zh",
    "character_id",
    "name",
    "region",
    "location",
    "seq",
    "at",
    "season_id",
    "account_id",  # 5F-3
    "battle_log",
)
"""首殺是「Boss 擊殺紀錄」（#91 紀念類），整筆保留；``season_id`` 分季。"""

_BOSS_BOARD: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "season_id",
    "boss",
    "character_id",
    "account_id",
    "name",
    "score",
    "rounds",
    "survivors",
    "allies",
    "no_down",
    "title_zh",
    "region",
    "location",
    "seq",
    "at",
)
"""賽季 Boss 的通關評分榜（Phase 5F-3；#91「排行榜與 Boss 擊殺紀錄」紀念類），整筆保留。"""

_ACCOUNT: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "format",
    "account_id",
    "username",
    "password",
    "disabled",
    "characters",
    "character_seasons",
    "discord_id",
    "admin",
    "created_at",
    "sessions",
)
"""帳號保留（#91）。``characters`` 是歸屬紀錄（不轉移，#100），角色上限只算當季
（``character_seasons``），所以不用修剪。"""

_NOTE: Final[dict[str, ResetKind]] = _all(
    NUMERIC, "note_id", "region", "location", "character_id", "name", "text", "at"
)
"""地點留言（#105）：#91 沒提到；暫標數值類（待決）。"""

_LEAGUE_RECORD: Final[dict[str, ResetKind]] = {
    **_all(
        MEMORIAL,
        "format",
        "season_id",
        "started_at",
        "matches",
        "rules_key",
        "reruns",
        "stale_zh",
    ),
    "entries": NUMERIC,
}
"""循環賽（5F-4）：賽程、勝負是「排行榜」（#91 紀念類）；凍結的報名帶著 build 快照與打法，季末清掉
（數值類；5F-4b 玩法 PM 代決「凍結的快照照樣清掉」，名次、名字、build 名改留在編年史）。"""

_LEAGUE_MATCH: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "id",
    "a",
    "b",
    "map",
    "seed_index",
    "seed",
    "ally",
    "status",
    "winner",
    "rounds",
    "end_reason",
    "error",
    "ally_hp_permille",
    "enemy_hp_permille",
)
"""循環賽的一場（排行榜的依據，紀念類；戰鬥紀錄檔跟著保留，季末也能重播查證）。"""

_CHRONICLE: Final[dict[str, ResetKind]] = _all(MEMORIAL, "format", "seasons")
_CHRONICLE_SEASON: Final[dict[str, ResetKind]] = _all(
    MEMORIAL, "season_id", "finished_at", "matches", "ranks"
)
_CHRONICLE_RANK: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "rank",
    "account",
    "name",
    "build_zh",
    "wins",
    "losses",
    "draws",
    "hp_permille_total",
    "rounds_total",
    "tied",
)
"""編年史的循環賽最終排名（5F-4b，玩法 PM 代決：紀念類，季末保留）。"""

SEASON_POLICY: Final[Mapping[type[BaseModel], Mapping[str, ResetKind]]] = {
    CharacterState: _CHARACTER,
    WorldState: _WORLD,
    RecipeRecord: _RECIPE,
    FirstKill: _FIRST_KILL,
    BossBoardEntry: _BOSS_BOARD,
    AccountRecord: _ACCOUNT,
    LocationNote: _NOTE,
    LeagueRecord: _LEAGUE_RECORD,  # 5F-4
    LeagueMatch: _LEAGUE_MATCH,
    LeagueChronicle: _CHRONICLE,  # 5F-4b 編年史
    LeagueChronicleSeason: _CHRONICLE_SEASON,
    LeagueChronicleRank: _CHRONICLE_RANK,
}
"""存檔模型 → 欄位 → 數值類／紀念類。"""

SAVED_MODELS: Final[tuple[type[BaseModel], ...]] = tuple(SEASON_POLICY)
"""要分類的存檔模型（角色、世界、配方紀錄、首殺、賽季 Boss 評分榜、帳號、地點留言、循環賽、
編年史）。"""

PROVISIONAL: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("WorldState", "recipes"),
        ("RecipeRecord", "recipe"),
        ("RecipeRecord", "hidden"),
        ("RecipeRecord", "base"),
        ("RecipeRecord", "steps"),
        ("RecipeRecord", "listed"),
        ("CharacterState", "elite_kills"),
        ("CharacterState", "finished_skeletons"),
        ("CharacterState", "hero"),
        ("LocationNote", "note_id"),
        ("LocationNote", "region"),
        ("LocationNote", "location"),
        ("LocationNote", "character_id"),
        ("LocationNote", "name"),
        ("LocationNote", "text"),
        ("LocationNote", "at"),
    }
)
"""拿不準、暫標數值類的欄位（模型名, 欄位）。待使用者決定（5D-R2 報告「待 PM 決定」）：

- 配方表要不要跨季（#91 只說數值類全清；配方能直接打出裝備，偏數值類）。
- 角色的精英擊殺、完成的事件骨架是不是「編年史」（目前是角色進度；編年史可由世界日誌與首殺算）。
- 角色名（``hero`` 裡）要不要留給編年史／排行榜（首殺已經存下當時的名字）。
- 地點留言要不要跨季。

（5F-4 的「循環賽凍結的報名要不要跨季」5F-4b 已定：快照照樣清掉，最終排名留在編年史。）
"""


def fields_of_kind(model: type[BaseModel], kind: ResetKind) -> tuple[str, ...]:
    """這個模型某一類的欄位（依欄位定義順序）。"""
    policy = SEASON_POLICY[model]
    return tuple(name for name in model.model_fields if policy.get(name) == kind)
