"""影子循環賽的賽果與背景執行（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.5～36.6）。

- 賽果是衍生資料（同首殺紀錄）：由「凍結的報名＋賽季種子＋內容」決定，任何時候都能重算查證；不進
  ``trpg-world/1``、不影響世界重播。
- 存檔 ``<世界資料夾>/league/league.json``（``trpg-league/1``）＋``league/matches/<id>.json``
  （每場的 :class:`~trpg.engine.runner.BattleLog`，``trpg battle replay`` 同格式）；原子寫入。
- :meth:`LeagueStore.start`：截止後（賽季第 ``signup_close_day + 1`` 天起）、至少 2 位參賽者時
  凍結報名、排好賽程。已經開過就沿用（只接續 ``pending``）。
- :class:`LeagueRunner`：一條背景執行緒依序跑 ``pending`` 的場次；每場跑完就寫檔（重啟後再開跑只接續
  沒跑完的）；每 ``batch_size`` 場讓出一次執行緒；單場出錯標 ``error`` 繼續下一場。
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.library import ContentLibrary
from trpg.content.world_season import LeagueRules
from trpg.engine.runner import BattleLog
from trpg.shared.errors import TrpgError
from trpg.world.calendar import season_day
from trpg.world.league import (
    LeagueMatchSpec,
    LeagueSpawn,
    league_rules,
    league_schedule,
    league_spawns,
    match_loser,
    match_setup,
    match_winner,
    play_match,
)
from trpg.world.save import write_atomic
from trpg.world.state import LeagueEntry, WorldState

__all__ = [
    "LEAGUE_DIR",
    "LEAGUE_FORMAT",
    "LeagueError",
    "LeagueMatch",
    "LeagueMatchNotFoundError",
    "LeagueRecord",
    "LeagueRunner",
    "LeagueStanding",
    "LeagueStore",
    "standings",
    "start_problem",
]

LEAGUE_FORMAT: Final = "trpg-league/1"
LEAGUE_DIR: Final = "league"
MATCH_ID_PATTERN: Final = r"^m[0-9]{4,}$"
MIN_ENTRIES: Final = 2
"""開跑至少要幾位參賽者。"""

_LOG = logging.getLogger(__name__)

type MatchStatus = Literal["pending", "done", "error"]


class LeagueError(TrpgError):
    """循環賽現在不能開跑（截止前、不到 2 人、這一季沒有循環賽；409）。"""


class LeagueMatchNotFoundError(TrpgError):
    """沒有這一場（或還沒跑完；404）。"""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LeagueMatch(_Model):
    """一場的賽程與結果。"""

    id: str = Field(pattern=MATCH_ID_PATTERN)
    a: str
    b: str
    map: str
    seed_index: int = Field(ge=0)
    seed: int = Field(ge=0)
    ally: str
    """站我方、先手的帳號。"""
    status: MatchStatus = "pending"
    winner: str | None = None
    """贏的帳號；和局或還沒打＝``None``。"""
    rounds: int = Field(default=0, ge=0)
    end_reason: str | None = None
    error: str | None = None

    @property
    def enemy(self) -> str:
        return self.b if self.ally == self.a else self.a

    def spec(self) -> LeagueMatchSpec:
        return LeagueMatchSpec(
            id=self.id,
            a=self.a,
            b=self.b,
            map=self.map,
            seed_index=self.seed_index,
            seed=self.seed,
            ally=self.ally,
        )


class LeagueRecord(_Model):
    """``league.json``：一季的循環賽（凍結的報名、賽程與結果）。"""

    format: Literal["trpg-league/1"] = LEAGUE_FORMAT
    season_id: str
    started_at: int = Field(ge=0)
    entries: tuple[LeagueEntry, ...]
    """開跑當下凍結的報名（依帳號排序）。"""
    matches: tuple[LeagueMatch, ...]

    @property
    def done(self) -> int:
        return sum(1 for m in self.matches if m.status != "pending")

    def match(self, match_id: str) -> LeagueMatch | None:
        return next((m for m in self.matches if m.id == match_id), None)

    def with_match(self, match: LeagueMatch) -> LeagueRecord:
        return self.model_copy(
            update={"matches": tuple(match if m.id == match.id else m for m in self.matches)}
        )


@dataclass(frozen=True)
class LeagueStanding:
    """排行榜的一列（代決 5F4-7、5F4-8）。"""

    rank: int
    account: str
    wins: int
    losses: int
    draws: int
    played: int


def standings(record: LeagueRecord) -> tuple[LeagueStanding, ...]:
    """勝場多 → 負場少 → 報名較早；分數相同（勝、負都一樣）的名次相同。"""
    tally = {e.account: [0, 0, 0] for e in record.entries}
    for match in record.matches:
        if match.status != "done":
            continue
        for account in (match.a, match.b):
            tally[account][2] += 1 if match.winner is None else 0
        if match.winner is not None:
            tally[match.winner][0] += 1
            loser = match_loser(match.spec(), match.winner)
            assert loser is not None
            tally[loser][1] += 1
    played = {e.account: 0 for e in record.entries}
    for match in record.matches:
        if match.status == "done":
            played[match.a] += 1
            played[match.b] += 1
    order = sorted(
        record.entries, key=lambda e: (-tally[e.account][0], tally[e.account][1], e.entered_at)
    )
    rows: list[LeagueStanding] = []
    for index, entry in enumerate(order):
        wins, losses, draws = tally[entry.account]
        rank = index + 1
        if rows and (rows[-1].wins, rows[-1].losses) == (wins, losses):
            rank = rows[-1].rank
        rows.append(
            LeagueStanding(
                rank=rank,
                account=entry.account,
                wins=wins,
                losses=losses,
                draws=draws,
                played=played[entry.account],
            )
        )
    return tuple(rows)


def start_problem(library: ContentLibrary, world: WorldState, now: int) -> str | None:
    """現在不能開跑的理由（中文）；可以時 ``None``。"""
    rules = league_rules(library)
    if rules is None:
        return "這一季沒有影子循環賽"
    if season_day(library, world, now) <= rules.signup_close_day:
        return f"報名還沒截止（第 {rules.signup_close_day} 天截止）"
    if len(world.league_entries) < MIN_ENTRIES:
        return f"參賽者不到 {MIN_ENTRIES} 位"
    return None


def new_record(rules: LeagueRules, world: WorldState, now: int) -> LeagueRecord:
    """凍結報名、排好賽程（全部 ``pending``）。"""
    specs = league_schedule(rules, world.season_seed, world.league_entries)
    return LeagueRecord(
        season_id=world.season_id,
        started_at=now,
        entries=world.league_entries,
        matches=tuple(LeagueMatch(**s.model_dump()) for s in specs),
    )


class LeagueStore:
    """``<root>/league/`` 的讀寫（一把鎖；背景執行緒與 API 共用）。"""

    def __init__(self, library: ContentLibrary, root: Path) -> None:
        self.library = library
        self.root = root
        self._lock = threading.RLock()
        self._record: LeagueRecord | None = None
        self._loaded = False

    @property
    def folder(self) -> Path:
        return self.root / LEAGUE_DIR

    def _record_path(self) -> Path:
        return self.folder / "league.json"

    def _match_path(self, match_id: str) -> Path:
        return self.folder / "matches" / f"{match_id}.json"

    def record(self, season_id: str | None = None) -> LeagueRecord | None:
        """目前的循環賽（沒開過、或檔案是別季的＝``None``）。"""
        with self._lock:
            if not self._loaded:
                path = self._record_path()
                if path.is_file():
                    self._record = LeagueRecord.model_validate_json(
                        path.read_text(encoding="utf-8")
                    )
                self._loaded = True
            record = self._record
        if record is not None and season_id is not None and record.season_id != season_id:
            return None
        return record

    def _save(self, record: LeagueRecord) -> None:
        with self._lock:
            write_atomic(self._record_path(), record.model_dump_json(indent=1))
            self._record = record
            self._loaded = True

    def start(self, world: WorldState, now: int) -> LeagueRecord:
        """開跑（或沿用已排好的賽程）；不能開跑時拋 :class:`LeagueError`。"""
        with self._lock:
            existing = self.record(world.season_id)
            if existing is not None:
                return existing
            problem = start_problem(self.library, world, now)
            if problem is not None:
                raise LeagueError(f"不能開始循環賽：{problem}")
            rules = league_rules(self.library)
            assert rules is not None
            record = new_record(rules, world, now)
            self._save(record)
            return record

    def log(self, match_id: str) -> BattleLog:
        """一場的戰鬥紀錄；沒有這一場或還沒跑完拋 :class:`LeagueMatchNotFoundError`。"""
        record = self.record()
        match = None if record is None else record.match(match_id)
        path = self._match_path(match_id)
        if match is None or match.status != "done" or not path.is_file():
            raise LeagueMatchNotFoundError(f"找不到循環賽的場次 {match_id}")
        return BattleLog.model_validate_json(path.read_text(encoding="utf-8"))

    def log_text(self, match_id: str) -> str:
        self.log(match_id)  # 檢查存在
        return self._match_path(match_id).read_text(encoding="utf-8")

    def play(
        self, match: LeagueMatch, spawns: Mapping[str, LeagueSpawn] | None = None
    ) -> LeagueMatch:
        """跑一場並寫檔（紀錄先寫、結果後寫）；回傳更新後的場次。出錯時標 ``error``。"""
        record = self.record()
        assert record is not None
        rules = league_rules(self.library)
        try:
            if rules is None:
                raise LeagueError("這一季沒有影子循環賽")
            prepared = spawns if spawns is not None else league_spawns(self.library, record.entries)
            spec = match.spec()
            setup = match_setup(self.library, rules, prepared, spec)
            run = play_match(self.library, setup, spec.seed)
            write_atomic(self._match_path(match.id), run.to_log().model_dump_json())
            done = match.model_copy(
                update={
                    "status": "done",
                    "winner": match_winner(run.state, spec),
                    "rounds": run.state.round,
                    "end_reason": run.state.end_reason,
                    "error": None,
                }
            )
        except Exception as exc:  # 單場出錯不擋其他場（36.6）
            _LOG.exception("循環賽 %s 出錯", match.id)
            done = match.model_copy(update={"status": "error", "error": str(exc)[:500]})
        with self._lock:
            current = self.record()
            assert current is not None
            self._save(current.with_match(done))
        return done


class LeagueRunner:
    """背景跑循環賽（同時只會有一條執行緒）。"""

    def __init__(self, store: LeagueStore) -> None:
        self.store = store
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def run_pending(self, limit: int | None = None) -> int:
        """在呼叫的執行緒裡依序跑 ``pending`` 的場次（最多 ``limit`` 場）；回傳跑了幾場。"""
        record = self.store.record()
        if record is None:
            return 0
        rules = league_rules(self.store.library)
        batch = 1 if rules is None else rules.batch_size
        pending: Sequence[LeagueMatch] = [m for m in record.matches if m.status == "pending"]
        if limit is not None:
            pending = pending[:limit]
        spawns = league_spawns(self.store.library, record.entries) if pending else {}
        count = 0
        for match in pending:
            if self._stop.is_set():
                break
            self.store.play(match, spawns)
            count += 1
            if count % batch == 0:
                time.sleep(0)  # 每批讓出一次執行緒（不卡伺服器的其他請求）
        return count

    def start(self) -> bool:
        """開一條背景執行緒跑完 ``pending``；已經在跑時不再開（回傳 ``False``）。"""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop.clear()
            self._thread = threading.Thread(target=self._work, name="trpg-league", daemon=True)
            self._thread.start()
            return True

    def _work(self) -> None:
        try:
            self.run_pending()
        except Exception:  # pragma: no cover - run_pending 已經逐場接住
            _LOG.exception("循環賽背景執行中斷")

    def join(self, timeout: float | None = None) -> None:
        """等背景執行緒結束（測試、關機用）。"""
        with self._lock:
            thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def shutdown(self) -> None:
        """請背景執行緒在這一場跑完後停下（伺服器關機）。"""
        self._stop.set()
        self.join(5.0)
