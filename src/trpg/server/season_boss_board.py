"""賽季 Boss 的通關評分榜與首殺戰鬥紀錄（Phase 5F-3；``docs/phases/Phase5計畫.md`` 37.7）。

- 評分榜（#87：輪數、全隊存活、有沒有人倒下；只給榮譽稱號）：``<世界資料夾>/season_boss_board.json``
  （``trpg-bossboard/1``）。每個角色每季只留最好的一次（分數高 → 輪數少 → 日誌序號小）。由世界日誌的
  ``season_boss_cleared`` 事件決定的衍生資料，不進 ``trpg-world/1``；紀念類（#91，季末保留）。
- 首殺戰鬥紀錄（#101「可重播查證」）：首殺那一場用開戰前的角色＋步驟重算（同一份設定與種子），存成
  ``BattleLog``（``<世界資料夾>/season_boss/<season_id>-first-kill.json``），``trpg battle replay``
  可驗證。

只有遊戲伺服器寫；呼叫者持有世界的寫入鎖。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.content.library import ContentLibrary
from trpg.engine.runner import replay
from trpg.shared.errors import TrpgError
from trpg.world.actions import FightAction
from trpg.world.battle import prepare_battle
from trpg.world.layout import BOSS_BOARD_FILE, FIRST_KILL_DIR
from trpg.world.save import write_atomic
from trpg.world.season_events import SeasonBossClearedEvent
from trpg.world.state import CharacterState

__all__ = [
    "BOSS_BOARD_FILE",
    "BOSS_BOARD_FORMAT",
    "FIRST_KILL_DIR",
    "BossBoardEntry",
    "BossBoardError",
    "SeasonBossBoard",
    "first_kill_log_json",
    "load_boss_board",
]

BOSS_BOARD_FORMAT: Final = "trpg-bossboard/1"


class BossBoardError(TrpgError):
    """評分榜檔壞了或格式不認得。"""


class BossBoardEntry(BaseModel):
    """評分榜的一筆（一個角色這一季最好的一次）。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    season_id: str
    boss: str
    character_id: str
    account_id: str | None = None
    name: str
    """當下的角色名（玩家文字；放進公告前要中和）。"""
    score: int = Field(ge=0)
    rounds: int = Field(ge=0)
    survivors: int = Field(ge=0)
    allies: int = Field(ge=0)
    no_down: bool
    title_zh: str
    region: str
    location: str
    """出發挑戰的地點（給別人看時照 5C-3f 套隱藏地點提示語）。"""
    seq: int = Field(ge=0)
    at: int = Field(ge=0)

    def rank_key(self) -> tuple[int, int, int]:
        return (-self.score, self.rounds, self.seq)


class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal["trpg-bossboard/1"] = BOSS_BOARD_FORMAT
    entries: tuple[BossBoardEntry, ...] = ()


def load_boss_board(path: Path) -> tuple[BossBoardEntry, ...]:
    """讀評分榜（檔案不存在＝空）；依季、名次排序。"""
    if not path.is_file():
        return ()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BossBoardError(f"評分榜 {path} 讀不了：{exc}") from exc
    if not isinstance(raw, dict) or raw.get("format") != BOSS_BOARD_FORMAT:
        found = raw.get("format") if isinstance(raw, dict) else None
        raise BossBoardError(f"不認得的評分榜格式：{found!r}（需要 {BOSS_BOARD_FORMAT}）")
    try:
        data = _File.model_validate(raw)
    except ValidationError as exc:
        raise BossBoardError(f"評分榜 {path} 的內容不合法：{exc}") from exc
    return tuple(sorted(data.entries, key=lambda e: (e.season_id, e.rank_key())))


def first_kill_log_json(
    library: ContentLibrary, char_before: CharacterState, action: FightAction
) -> str:
    """首殺那一場的 ``BattleLog`` JSON：開戰前的角色（身上有賽季 Boss 的遭遇）＋這次的步驟重算。"""
    prepared = prepare_battle(library, char_before)
    run = replay(prepared.setup, prepared.seed, list(action.steps))
    return run.to_log().model_dump_json(indent=None) + "\n"


class SeasonBossBoard:
    """``<世界資料夾>/season_boss_board.json`` 與首殺戰鬥紀錄的讀寫。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / BOSS_BOARD_FILE

    def all(self) -> tuple[BossBoardEntry, ...]:
        return load_boss_board(self.path)

    def top(self, season_id: str, limit: int = 10) -> tuple[BossBoardEntry, ...]:
        """這一季的前 ``limit`` 名（依名次）。"""
        return tuple(e for e in self.all() if e.season_id == season_id)[:limit]

    def record(
        self,
        char_before: CharacterState,
        char_after: CharacterState,
        event: SeasonBossClearedEvent,
        *,
        season_id: str,
        account_id: str | None,
        seq: int,
        now: int,
    ) -> BossBoardEntry | None:
        """記一次通關；同角色同季只留最好的一次。回傳寫進去的那一筆（沒有更好時 ``None``）。"""
        encounter = char_before.pending_encounter
        entry = BossBoardEntry(
            season_id=season_id,
            boss=event.boss,
            character_id=char_after.character_id,
            account_id=account_id,
            name=char_after.hero.name_zh,
            score=event.score,
            rounds=event.rounds,
            survivors=event.survivors,
            allies=event.allies,
            no_down=event.no_down,
            title_zh=event.title_zh,
            region=char_after.region if encounter is None else encounter.region,
            location=char_after.location if encounter is None else encounter.location,
            seq=seq,
            at=now,
        )
        existing = self.all()
        same = [
            e for e in existing if (e.season_id, e.character_id) == (season_id, entry.character_id)
        ]
        if same and same[0].rank_key() <= entry.rank_key():
            return None
        kept = [e for e in existing if e not in same]
        data = _File(
            entries=tuple(sorted([*kept, entry], key=lambda e: (e.season_id, e.rank_key())))
        )
        text = json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2)
        write_atomic(self.path, text + "\n")
        return entry

    def save_first_kill_log(self, season_id: str, log_json: str) -> str:
        """存首殺戰鬥紀錄；回傳相對於世界資料夾的路徑（已存在時不覆寫，首殺只有一場）。"""
        relative = f"{FIRST_KILL_DIR}/{season_id}-first-kill.json"
        path = self.root / relative
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(path, log_json)
        return relative
