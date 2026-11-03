"""影子循環賽的賽果與背景執行（Phase 5F-4；``docs/phases/Phase5計畫.md`` 36.5～36.6）。

- 賽果是衍生資料（同首殺紀錄）：由「凍結的報名＋賽季種子＋內容」決定，任何時候都能重算查證；不進
  ``trpg-world/1``、不影響世界重播。
- 存檔 ``<世界資料夾>/league/league.json``（``trpg-league/1``）＋``league/matches/<id>.json``
  （每場的 :class:`~trpg.engine.runner.BattleLog`，``trpg battle replay`` 同格式）；原子寫入。
- :meth:`LeagueStore.start`：截止後（賽季第 ``signup_close_day + 1`` 天起）、至少 2 位參賽者時
  凍結報名、排好賽程。已經開過就沿用（只接續 ``pending``）。
- :class:`LeagueRunner`：一條背景執行緒依序跑 ``pending`` 的場次；每場跑完就寫檔（重啟後再開跑只接續
  沒跑完的）；每 ``batch_size`` 場讓出一次執行緒；單場出錯標 ``error`` 繼續下一場。

5F-4b：

- **規則改了就整個重跑**（開發 PM 保守代決）：賽程記下開跑當下的規則鍵（:func:`rules_key`：戰鬥
  紀錄版號＋規則包雜湊＋循環賽規則）。再開跑時規則鍵不同 → 舊的賽程連同戰鬥紀錄搬到
  ``league/archive/``、標「規則已變、不能重播」，用同一份凍結的報名重排、全部重跑（不跨 ruleset
  重播）。規則鍵不同的賽程不會接續跑（不混兩套規則）。
- **排名**（6.8 BAL-12a）：勝場多 → 所有場次己方剩餘 HP 比例（‰）合計多 → 總輪數少；三項都同＝
  同名次（獎金平分）。
- **編年史**：全部場次跑完時把最終排名寫進 :mod:`trpg.server.chronicle`（紀念類）。
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.content.library import ContentLibrary
from trpg.content.world_season import LeagueRules
from trpg.engine.ruleset_hash import hash_ruleset
from trpg.engine.runner import LOG_FORMAT, BattleLog
from trpg.engine.state import BattleState
from trpg.server.chronicle import LeagueChronicleRank, LeagueChronicleSeason, LeagueChronicleStore
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
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
from trpg.world.shadows import shadow_role_zh
from trpg.world.state import LeagueEntry, WorldState

__all__ = [
    "LEAGUE_DIR",
    "LEAGUE_FORMAT",
    "STALE_ZH",
    "LeagueError",
    "LeagueMatch",
    "LeagueMatchNotFoundError",
    "LeagueRecord",
    "LeagueRunner",
    "LeagueStanding",
    "LeagueStore",
    "chronicle_season",
    "rules_key",
    "standings",
    "start_problem",
]

LEAGUE_FORMAT: Final = "trpg-league/1"
LEAGUE_DIR: Final = "league"
MATCH_ID_PATTERN: Final = r"^m[0-9]{4,}$"
MIN_ENTRIES: Final = 2
"""開跑至少要幾位參賽者。"""
PERMILLE: Final = 1000
STALE_ZH: Final = "規則已變、不能重播"

_LOG = logging.getLogger(__name__)

type MatchStatus = Literal["pending", "done", "error"]


def _now() -> int:
    return int(time.time())


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
    ally_hp_permille: int = Field(default=0, ge=0, le=PERMILLE)
    """（5F-4b）結束時先手那位剩餘 HP ÷ 最大 HP（‰；倒下＝0）。"""
    enemy_hp_permille: int = Field(default=0, ge=0, le=PERMILLE)
    """（5F-4b）結束時後手那位剩餘 HP 比例（‰）。"""

    def hp_permille_of(self, account: str) -> int:
        """某一方結束時的剩餘 HP 比例（‰）。"""
        return self.ally_hp_permille if account == self.ally else self.enemy_hp_permille

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
    rules_key: str | None = None
    """（5F-4b）開跑當下的規則鍵（:func:`rules_key`）；``None``＝5F-4 的舊賽程（視為規則已變）。"""
    reruns: int = Field(default=0, ge=0)
    """（5F-4b）因為規則改了而整個重跑過幾次。"""
    stale_zh: str | None = None
    """（5F-4b）搬進 ``archive/`` 的舊賽程才有：「規則已變、不能重播」。"""

    @property
    def finished(self) -> bool:
        """全部場次都跑完（含出錯的）。"""
        return all(m.status != "pending" for m in self.matches)

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
    """排行榜的一列（代決 5F4-7；同分照 6.8 BAL-12a，5F-4b）。"""

    rank: int
    account: str
    wins: int
    losses: int
    draws: int
    played: int
    hp_permille_total: int = 0
    """所有場次己方剩餘 HP 比例（‰）的合計。"""
    rounds_total: int = 0
    """所有場次的總輪數。"""
    tied: bool = False
    """和別人同名次（三項都相同；獎金平分）。"""

    @property
    def score(self) -> tuple[int, int, int]:
        """排序鍵：勝場多 → HP 比例合計多 → 總輪數少。"""
        return (-self.wins, -self.hp_permille_total, self.rounds_total)


def _tally(record: LeagueRecord) -> dict[str, LeagueStanding]:
    """每位參賽者的勝負和、場數、HP 比例合計、總輪數（名次之後再排）。"""
    rows = {e.account: [0, 0, 0, 0, 0, 0] for e in record.entries}
    for match in record.matches:
        if match.status != "done":
            continue
        for account in (match.a, match.b):
            row = rows[account]
            row[2] += 1 if match.winner is None else 0
            row[3] += 1
            row[4] += match.hp_permille_of(account)
            row[5] += match.rounds
        if match.winner is not None:
            rows[match.winner][0] += 1
            loser = match_loser(match.spec(), match.winner)
            assert loser is not None
            rows[loser][1] += 1
    return {
        account: LeagueStanding(
            rank=0,
            account=account,
            wins=r[0],
            losses=r[1],
            draws=r[2],
            played=r[3],
            hp_permille_total=r[4],
            rounds_total=r[5],
        )
        for account, r in rows.items()
    }


def standings(record: LeagueRecord) -> tuple[LeagueStanding, ...]:
    """勝場多 → 所有場次己方剩餘 HP 比例合計多 → 總輪數少（6.8 BAL-12a，5F-4b）；三項都相同的
    名次相同（``tied``，獎金平分）。同名次之間依報名先後列出。"""
    tally = _tally(record)
    entered = {e.account: e.entered_at for e in record.entries}
    order = sorted(tally.values(), key=lambda r: (r.score, entered[r.account], r.account))
    counts: dict[tuple[int, int, int], int] = {}
    for row in order:
        counts[row.score] = counts.get(row.score, 0) + 1
    ranked: list[LeagueStanding] = []
    for index, row in enumerate(order):
        same = bool(ranked) and ranked[-1].score == row.score
        rank = ranked[-1].rank if same else index + 1
        ranked.append(replace(row, rank=rank, tied=counts[row.score] > 1))
    return tuple(ranked)


def chronicle_season(
    library: ContentLibrary, record: LeagueRecord, now: int
) -> LeagueChronicleSeason:
    """編年史的這一季最終排名（名次、名字、build 名；5F-4b）。"""
    by_account = {e.account: e for e in record.entries}
    return LeagueChronicleSeason(
        season_id=record.season_id,
        finished_at=now,
        matches=len(record.matches),
        ranks=tuple(
            LeagueChronicleRank(
                rank=row.rank,
                account=row.account,
                name=by_account[row.account].name,
                build_zh=shadow_role_zh(library, by_account[row.account].snapshot),
                wins=row.wins,
                losses=row.losses,
                draws=row.draws,
                hp_permille_total=row.hp_permille_total,
                rounds_total=row.rounds_total,
                tied=row.tied,
            )
            for row in standings(record)
        ),
    )


def rules_key(library: ContentLibrary) -> str:
    """目前的規則鍵（5F-4b）：戰鬥紀錄版號＋規則包雜湊＋循環賽規則的雜湊。和賽程記下的不同＝規則
    改了（舊的戰鬥紀錄不能重播，整個賽程要重跑）。"""
    rules = league_rules(library)
    league = "" if rules is None else rules.model_dump_json()
    digest = hashlib.sha256(league.encode()).hexdigest()[:16]
    return f"{LOG_FORMAT}|{hash_ruleset(library.ruleset)}|{digest}"


def _hp_permille(state: BattleState, team: Team) -> int:
    """一方主角（不是召喚物）結束時的剩餘 HP 比例（‰）。"""
    hero = next((u for u in state.units_sorted() if u.team is team and u.owner_id is None), None)
    if hero is None or hero.max_hp <= 0:
        return 0
    return max(0, min(PERMILLE, hero.hp * PERMILLE // hero.max_hp))


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


def new_record(
    rules: LeagueRules,
    world: WorldState,
    now: int,
    *,
    key: str | None = None,
    entries: Sequence[LeagueEntry] | None = None,
    reruns: int = 0,
) -> LeagueRecord:
    """凍結報名、排好賽程（全部 ``pending``）。``entries`` 給了＝重跑時沿用上一次凍結的報名。"""
    frozen = tuple(world.league_entries if entries is None else entries)
    specs = league_schedule(rules, world.season_seed, frozen)
    return LeagueRecord(
        season_id=world.season_id,
        started_at=now,
        entries=frozen,
        matches=tuple(LeagueMatch(**s.model_dump()) for s in specs),
        rules_key=key,
        reruns=reruns,
    )


class LeagueStore:
    """``<root>/league/`` 的讀寫（一把鎖；背景執行緒與 API 共用）。"""

    def __init__(
        self, library: ContentLibrary, root: Path, *, clock: Callable[[], int] | None = None
    ) -> None:
        self.library = library
        self.root = root
        self.clock: Callable[[], int] = clock if clock is not None else _now
        self.chronicle = LeagueChronicleStore(root)
        """編年史（最終排名，5F-4b）。"""
        self._lock = threading.RLock()
        self._record: LeagueRecord | None = None
        self._loaded = False
        self._key: str | None = None

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

    def rules_key(self) -> str:
        """目前內容的規則鍵（內容庫不會在執行中換掉，算一次）。"""
        if self._key is None:
            self._key = rules_key(self.library)
        return self._key

    def stale(self, record: LeagueRecord) -> bool:
        """賽程是用別套規則跑的（規則已變、紀錄不能重播）。"""
        return record.rules_key != self.rules_key()

    def archived(self) -> tuple[LeagueRecord, ...]:
        """因為規則改了而搬走的舊賽程（依開跑時間）。"""
        folder = self.folder / "archive"
        if not folder.is_dir():
            return ()
        found = [
            LeagueRecord.model_validate_json(p.read_text(encoding="utf-8"))
            for p in sorted(folder.glob("league-*.json"))
        ]
        return tuple(sorted(found, key=lambda r: (r.started_at, r.reruns)))

    def _archive(self, record: LeagueRecord) -> None:
        """把舊賽程與戰鬥紀錄搬進 ``archive/``，標「規則已變、不能重播」。"""
        folder = self.folder / "archive"
        tag = f"{record.season_id}-{record.started_at}-{record.reruns}"
        stale = record.model_copy(update={"stale_zh": STALE_ZH})
        write_atomic(folder / f"league-{tag}.json", stale.model_dump_json(indent=1))
        matches = self.folder / "matches"
        if matches.is_dir():
            target = folder / f"matches-{tag}"
            if target.exists():
                shutil.rmtree(target)
            matches.rename(target)

    def start(self, world: WorldState, now: int) -> LeagueRecord:
        """開跑（或沿用已排好的賽程）；規則改了就整個重跑（5F-4b）；不能開跑時拋
        :class:`LeagueError`。"""
        with self._lock:
            existing = self.record(world.season_id)
            rules = league_rules(self.library)
            if existing is not None and not self.stale(existing):
                return existing
            if existing is not None:
                if rules is None:
                    raise LeagueError("不能重跑循環賽：這一季沒有影子循環賽")
                self._archive(existing)
                record = new_record(
                    rules,
                    world,
                    now,
                    key=self.rules_key(),
                    entries=existing.entries,
                    reruns=existing.reruns + 1,
                )
                _LOG.warning("循環賽規則已變：整個賽程重跑（第 %d 次）", record.reruns)
                self._save(record)
                return record
            problem = start_problem(self.library, world, now)
            if problem is not None:
                raise LeagueError(f"不能開始循環賽：{problem}")
            assert rules is not None
            record = new_record(rules, world, now, key=self.rules_key())
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
                    "ally_hp_permille": _hp_permille(run.state, Team.ALLY),
                    "enemy_hp_permille": _hp_permille(run.state, Team.ENEMY),
                }
            )
        except Exception as exc:  # 單場出錯不擋其他場（36.6）
            _LOG.exception("循環賽 %s 出錯", match.id)
            done = match.model_copy(update={"status": "error", "error": str(exc)[:500]})
        with self._lock:
            current = self.record()
            assert current is not None
            updated = current.with_match(done)
            self._save(updated)
            if updated.finished and not current.finished:
                self._write_chronicle(updated)
        return done

    def _write_chronicle(self, record: LeagueRecord) -> None:
        """全部跑完：最終排名寫進編年史（衍生資料；寫入失敗只記 log）。"""
        try:
            self.chronicle.write(chronicle_season(self.library, record, self.clock()))
        except Exception:
            _LOG.exception("循環賽的編年史寫入失敗（%s）", record.season_id)


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
        if record is None or self.store.stale(record):
            return 0  # 規則已變的賽程不接續（不混兩套規則；要重跑先 start）
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
