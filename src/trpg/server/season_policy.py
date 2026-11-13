"""季末重置政策表（Phase 5D-R2；09 9.7「季末重置」、#91）。

每個存檔模型的每個欄位標成一類：

- ``"numeric"``（數值類）：季末清掉（等級、技能、裝備、材料、任務幣、世界狀態……）。
- ``"memorial"``（紀念類）：季末保留（帳號、稱號、編年史、印記收藏、排行榜與 Boss 擊殺紀錄）。

5D-R2 只有分類與檢查（``tests/test_architecture.py``：表裡每個模型的欄位都要分類，新增欄位沒分類
就失敗）。5F-5 的重置流程在 :mod:`trpg.server.season_reset`，照這張表清掉數值類、保留紀念類（架構
測試另外檢查表裡每個模型都有重置處理）。

角色（``CharacterState``）整個是數值類：#91 的「等級、技能、裝備、材料、任務幣」都在角色身上，
角色本身也清掉（角色上限按賽季算，帳號保留歸屬紀錄，5D-R2）。

5F-5（玩法 PM 2026-11-03 代決，第 1 節 5F-5 列）：5D-R2 暫標數值類的欄位都定案為數值類
（:data:`PROVISIONAL` 清空）；其中幾個季末先寫進紀念紀錄再清（:data:`CARRIED`）：角色的名字與外觀
（下季建角色可以沿用）、打過的精英與完成的事件（編年史文字）、配方的首位發現者。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Literal

from pydantic import BaseModel

from trpg.server.accounts import AccountRecord, AccountTitle
from trpg.server.chronicle import (
    ChronicleHero,
    LeagueChronicle,
    LeagueChronicleRank,
    LeagueChronicleSeason,
    RecipeDiscovery,
    SeasonChronicle,
    SeasonChronicleEntry,
)
from trpg.server.first_kills import FirstKill
from trpg.server.league import LeagueMatch, LeagueRecord
from trpg.server.notes import LocationNote
from trpg.server.season_boss_board import BossBoardEntry
from trpg.world.state import CharacterState, RecipeRecord, WorldState

__all__ = [
    "CARRIED",
    "HERO_LEGACY_FIELDS",
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
    "opening",  # TR-1（#134）未完成開局（在靶場）；角色整個是數值類
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
    "field",  # 6B-2 實地地圖上的位置（同 region、location）
    "teleport_stones",  # 6B-2 解鎖的傳送石（同 revealed）
    "field_visit",  # 6C-1 這一趟的實地地圖敵人（同 field）
    "visited_locations",  # 6C-6 去過的地點（區域圖的迷霧，同 revealed）
    "field_event",  # 6C-5 地圖上的「！」（同 pending_event）
    "sneaking",  # 6C-5 潛行（同 field_visit）
    "object_uses",  # 6C-5 情境物件每天一次（同 perception_marks）
    "hints_seen",  # 6F-4 出過的提示與教學（新角色要重新教，同 perception_marks）
    "hints_off",  # 6F-4「不再顯示提示」（跟著角色走，同 hints_seen）
    "level_seen",  # 6F-4 看過的升級畫面（同 level）
    "skill_regions",  # 6L-2 技能的取得地點界域（跟著技能走，同 generated_skills）
    "gear_origin",  # 6T-1a 裝備的來歷與綁定（跟著裝備走，同 gear）
    "mailbox",  # 6T-1a 信箱：季末沒領的信連同附件清掉（玩法 PM 3.5 代決；季末前 3 天寄件時提示）
    "free_race_change_used",  # 6R-1 這一季用過免費換種族（#138；新角色下一季另算）
    "wish_week",  # WP-1 本週許願的次數（07 7.6、#88；同 shop_week）
)

_WORLD: Final[dict[str, ResetKind]] = _all(
    NUMERIC,
    "format",
    "season_id",
    "season_seed",
    "season_start",
    "flags",
    "cleared",
    "defeated_spawns",  # 6C-1b 實地地圖上被打贏的隊伍（同 cleared）
    "threads",
    "timed_flags",
    "shadows",
    "recipes",
    "rolled_day",  # 5F-1 賽季日程
    "activity",
    "world_events",
    "bounty_claims",
    "level_bonus",
    "shop_price",  # 5F-5b 世界事件失敗的商店價格加成（到季末）
    "seal_keys",  # 5F-3 賽季 Boss（世界狀態；紀念的首殺與評分榜在伺服器檔）
    "seal_full_at",
    "boss_attempts",
    "boss_clears",
    "league_entries",  # 5F-4 影子循環賽的報名
    "trades",  # 6T-1a 這一季的交易帳（稽核報表；同 recipes 以外的世界狀態）
    "weapon_mix",  # 6T-1a 主手大類比例（每天 6 點算，#135）
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
    "titles",
)
"""帳號保留（#91；5F-3b 的紀念稱號 ``titles`` 也是）。``characters`` 是歸屬紀錄
（不轉移，#100），角色上限只算當季
（``character_seasons``），所以不用修剪。"""

_ACCOUNT_TITLE: Final[dict[str, ResetKind]] = _all(
    MEMORIAL, "id", "name_zh", "season_id", "character_id", "at"
)
"""帳號的紀念稱號（5F-3b，#91「只給榮譽稱號」）：季末保留。"""

_NOTE: Final[dict[str, ResetKind]] = _all(
    NUMERIC, "note_id", "region", "location", "character_id", "name", "text", "at"
)
"""地點留言（#105）：數值類，季末刪掉（5F-5 玩法 PM 代決定案，:data:`PROVISIONAL` 已清空）。"""

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

_SEASON_CHRONICLE: Final[dict[str, ResetKind]] = _all(MEMORIAL, "format", "seasons")
_SEASON_CHRONICLE_ENTRY: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "season_id",
    "name_zh",
    "started_at",
    "reset_at",
    "next_season_id",
    "heroes",
    "recipes",
)
_CHRONICLE_HERO: Final[dict[str, ResetKind]] = _all(
    MEMORIAL,
    "character_id",
    "account_id",
    "name",
    "race",
    "doll",
    "level",  # 5F-5c 編年史列事實細節
    "elites",
    "bosses",
    "first_kills",
    "chapters",
    "events",
    "recipes",
    "league_rank",
    "text_zh",
)
_RECIPE_DISCOVERY: Final[dict[str, ResetKind]] = _all(
    MEMORIAL, "code", "name_zh", "discoverer", "discoverer_name", "discovered_at", "season_id"
)
"""編年史的季末紀錄（5F-5）：上季角色（編年史文字、名字與外觀）、配方的首位發現者。紀念類。"""

SEASON_POLICY: Final[Mapping[type[BaseModel], Mapping[str, ResetKind]]] = {
    CharacterState: _CHARACTER,
    WorldState: _WORLD,
    RecipeRecord: _RECIPE,
    FirstKill: _FIRST_KILL,
    BossBoardEntry: _BOSS_BOARD,
    AccountRecord: _ACCOUNT,
    AccountTitle: _ACCOUNT_TITLE,  # 5F-3b
    LocationNote: _NOTE,
    LeagueRecord: _LEAGUE_RECORD,  # 5F-4
    LeagueMatch: _LEAGUE_MATCH,
    LeagueChronicle: _CHRONICLE,  # 5F-4b 編年史
    LeagueChronicleSeason: _CHRONICLE_SEASON,
    LeagueChronicleRank: _CHRONICLE_RANK,
    SeasonChronicle: _SEASON_CHRONICLE,  # 5F-5 季末紀錄
    SeasonChronicleEntry: _SEASON_CHRONICLE_ENTRY,
    ChronicleHero: _CHRONICLE_HERO,
    RecipeDiscovery: _RECIPE_DISCOVERY,
}
"""存檔模型 → 欄位 → 數值類／紀念類。"""

SAVED_MODELS: Final[tuple[type[BaseModel], ...]] = tuple(SEASON_POLICY)
"""要分類的存檔模型（角色、世界、配方紀錄、首殺、賽季 Boss 評分榜、帳號、地點留言、循環賽、
編年史）。"""

PROVISIONAL: Final[frozenset[tuple[str, str]]] = frozenset()
"""拿不準、暫標數值類的欄位（模型名, 欄位）。5D-R2 列的四項（配方表、精英擊殺與完成的事件、角色名、
地點留言）5F-5 由玩法 PM 代決，全部定案為數值類，其中要留下的部分改由 :data:`CARRIED` 寫進紀念
紀錄。之後新增拿不準的欄位再列在這裡。"""

HERO_LEGACY_FIELDS: Final[tuple[str, ...]] = ("name_zh", "race", "doll")
"""角色 ``hero``（``UnitTemplate``）裡季末寫進編年史、下季建角色用得到的欄位：外觀（名字、紙娃娃）
與上季的種族（5F-5c：種族不算外觀，只當新角色的預設、可以免費改）。等級、技能、裝備、屬性等其他
欄位照數值類清掉。"""

CARRIED: Final[Mapping[tuple[str, str], str]] = {
    ("CharacterState", "hero"): "名字、紙娃娃（外觀）與種族（預設）→ 編年史的上季角色",
    ("CharacterState", "elite_kills"): "擊倒過的精英 → 編年史文字",
    ("CharacterState", "finished_skeletons"): "完成的事件 → 編年史文字",
    ("CharacterState", "level"): "季末的等級 → 編年史文字（5F-5c）",
    ("CharacterState", "quests"): "完成的主線章節 → 編年史文字（5F-5c）",
    ("WorldState", "boss_clears"): "打倒賽季 Boss 的角色 → 編年史文字（5F-5c）",
    ("WorldState", "league_entries"): "報名的角色（對到循環賽名次）→ 編年史（5F-5c）",
    ("WorldState", "recipes"): "配方的首位發現者（RecipeRecord 的紀念類欄位）→ 編年史",
}
"""數值類、但季末先寫進紀念紀錄再清掉的欄位（模型名, 欄位）→ 去處（5F-5，玩法 PM 2026-11-03）。
:mod:`trpg.server.season_reset` 每一項都要處理（架構測試檢查）。"""


def fields_of_kind(model: type[BaseModel], kind: ResetKind) -> tuple[str, ...]:
    """這個模型某一類的欄位（依欄位定義順序）。"""
    policy = SEASON_POLICY[model]
    return tuple(name for name in model.model_fields if policy.get(name) == kind)
