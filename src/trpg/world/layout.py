"""存檔資料夾與世界資料夾的版面（Phase 5F-R1）：所有檔名、資料夾名的唯一來源。

``<存檔資料夾>/``（``TRPG_SAVE_DIR`` 或專案的 ``saves/``）::

    world/                     WORLD_DIR：大世界（遊戲伺服器的 WorldStore、季末重置）
    archive/<季>/              ARCHIVE_DIR：舊季的唯讀封存（5F-5c）

``world/`` 裡（:data:`WORLD_ENTRIES` 列全；季末重置的 ``WORLD_FILES`` 每一項都要有處理）::

    world.json                 世界狀態
    log.jsonl                  世界動作日誌
    chars/<角色>.json          角色
    notes.json                 地點留言
    league/                    循環賽（league.json、matches/<場次>.json、archive/league-*.json）
    first_kills.json           首殺紀錄
    season_boss_board.json     賽季 Boss 評分榜
    season_boss/               賽季 Boss 首殺的戰鬥紀錄
    chronicle/                 編年史（league.json、seasons.json）
    league_history/            5F-5 的舊位置（5F-5c 起改搬進封存）
    server.lock                遊戲伺服器的心跳檔（5F-R1）

只放常數與組路徑的小函式；``trpg.world`` 是下層模組，``trpg.server``、``trpg.api`` 都從這裡取。
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

__all__ = [
    "ARCHIVE_DIR",
    "BOSS_BOARD_FILE",
    "CHARS_DIR",
    "CHRONICLE_DIR",
    "FIRST_KILLS_FILE",
    "FIRST_KILL_DIR",
    "LEAGUE_ARCHIVE_DIR",
    "LEAGUE_CHRONICLE_FILE",
    "LEAGUE_DIR",
    "LEAGUE_FILE",
    "LEAGUE_HISTORY_DIR",
    "LEAGUE_MATCHES_DIR",
    "LOG_FILE",
    "NOTES_FILE",
    "SEASON_CHRONICLE_FILE",
    "SERVER_LOCK_FILE",
    "WORLD_DIR",
    "WORLD_ENTRIES",
    "WORLD_FILE",
    "char_path",
    "world_dir_of",
]

# -- 存檔資料夾 ---------------------------------------------------------------

WORLD_DIR: Final = "world"
ARCHIVE_DIR: Final = "archive"

# -- 世界資料夾的第一層 -------------------------------------------------------

WORLD_FILE: Final = "world.json"
LOG_FILE: Final = "log.jsonl"
CHARS_DIR: Final = "chars"
NOTES_FILE: Final = "notes.json"
LEAGUE_DIR: Final = "league"
FIRST_KILLS_FILE: Final = "first_kills.json"
BOSS_BOARD_FILE: Final = "season_boss_board.json"
FIRST_KILL_DIR: Final = "season_boss"
CHRONICLE_DIR: Final = "chronicle"
LEAGUE_HISTORY_DIR: Final = "league_history"
SERVER_LOCK_FILE: Final = "server.lock"

WORLD_ENTRIES: Final[tuple[str, ...]] = (
    WORLD_FILE,
    LOG_FILE,
    CHARS_DIR,
    NOTES_FILE,
    LEAGUE_DIR,
    FIRST_KILLS_FILE,
    BOSS_BOARD_FILE,
    FIRST_KILL_DIR,
    CHRONICLE_DIR,
    LEAGUE_HISTORY_DIR,
    SERVER_LOCK_FILE,
)
"""世界資料夾第一層的每一種檔案與資料夾（季末重置的 ``WORLD_FILES`` 要和這裡一致）。"""

# -- 子資料夾裡 ---------------------------------------------------------------

LEAGUE_FILE: Final = "league.json"
"""``league/league.json``：目前的賽程。"""
LEAGUE_MATCHES_DIR: Final = "matches"
"""``league/matches/<場次>.json``：每一場的戰鬥紀錄。"""
LEAGUE_ARCHIVE_DIR: Final = "archive"
"""``league/archive/``：規則變了、不能重播的舊賽程（和存檔資料夾的 :data:`ARCHIVE_DIR` 不同）。"""
LEAGUE_CHRONICLE_FILE: Final = "league.json"
"""``chronicle/league.json``：循環賽最終排名。"""
SEASON_CHRONICLE_FILE: Final = "seasons.json"
"""``chronicle/seasons.json``：每一季的季末紀錄。"""


def world_dir_of(save_dir: Path) -> Path:
    """存檔資料夾裡的世界資料夾。"""
    return save_dir / WORLD_DIR


def char_path(world_dir: Path, character_id: str) -> Path:
    """一個角色的存檔。"""
    return world_dir / CHARS_DIR / f"{character_id}.json"
