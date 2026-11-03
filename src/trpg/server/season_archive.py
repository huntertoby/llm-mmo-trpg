"""舊季的唯讀封存與重播查證（Phase 5F-5c；09 9.7 季末重置細節，玩法 PM 2026-11-03 代決）。

- **位置**：存檔資料夾裡固定的 ``archive/<季 ID>/``（不只在 ``saves-backups/`` 的備份裡）：
  ``log.jsonl``（世界日誌）、``league/``（循環賽賽程與每一場的戰鬥紀錄）、``season_boss/``（賽季
  Boss 首殺那一場的戰鬥紀錄），加上 ``manifest.json``（每個檔的 sha256）。路徑相對於世界資料夾的
  紀錄（例 ``FirstKill.battle_log``）在封存裡照同一個相對路徑找。
- **唯讀**：只有季末重置（:func:`archive_season`）會寫，寫完把每個檔設成唯讀（``os.chmod``；Windows
  是唯讀屬性、macOS 是 0444）。其餘的程式只讀不寫。
- **查證**：:func:`verify_first_kill`、:func:`verify_league_match` 從封存（目前這一季從世界資料夾）
  讀戰鬥紀錄，確定性重播後比對最終狀態與事件，再比對保留下來的紀念紀錄（首殺、循環賽名次的依據）。
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from trpg.engine.events import EVENT_LIST_ADAPTER
from trpg.engine.runner import BattleLog, log_format_problem, log_replay_problem, replay
from trpg.engine.state import state_to_json
from trpg.server.first_kills import FirstKill, load_first_kills
from trpg.server.league import LeagueMatch, LeagueRecord
from trpg.shared.errors import TrpgError
from trpg.shared.types import Team
from trpg.world.layout import (
    ARCHIVE_DIR,
    FIRST_KILL_DIR,
    FIRST_KILLS_FILE,
    LEAGUE_DIR,
    LEAGUE_FILE,
    LEAGUE_MATCHES_DIR,
    LOG_FILE,
)
from trpg.world.league import match_winner

__all__ = [
    "ARCHIVED",
    "ARCHIVE_DIR",
    "ARCHIVE_FORMAT",
    "MANIFEST_FILE",
    "ArchiveFile",
    "ArchiveManifest",
    "ArchiveRecordNotFoundError",
    "ReplayCheck",
    "archive_season",
    "season_archive_dir",
    "verify_first_kill",
    "verify_league_match",
]

ARCHIVE_FORMAT: Final = "trpg-season-archive/1"
MANIFEST_FILE: Final = "manifest.json"
ARCHIVED: Final[tuple[str, ...]] = (LOG_FILE, LEAGUE_DIR, FIRST_KILL_DIR)
"""季末從世界資料夾搬進封存的東西：世界日誌、循環賽、賽季 Boss 首殺的戰鬥紀錄。"""
_READ_ONLY: Final = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH


class ArchiveRecordNotFoundError(TrpgError):
    """要查證的首殺或循環賽場次不存在（404）。"""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArchiveFile(_Model):
    path: str
    """相對於封存資料夾（``/`` 分隔）。"""
    sha256: str
    size: int


class ArchiveManifest(_Model):
    """``archive/<季>/manifest.json``。"""

    format: Literal["trpg-season-archive/1"] = ARCHIVE_FORMAT
    season_id: str
    archived_at: int
    files: tuple[ArchiveFile, ...]
    """依路徑排序。"""


def season_archive_dir(save_dir: Path, season_id: str) -> Path:
    """一季的封存資料夾 ``<存檔資料夾>/archive/<季>/``。"""
    return save_dir / ARCHIVE_DIR / season_id


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.name != MANIFEST_FILE)


def _free(target: Path) -> Path:
    """``target`` 已存在（中斷後重跑）時用 ``<名字>-2`` 起的空位，不蓋掉已封存的。"""
    if not target.exists():
        return target
    n = 2
    while True:
        found = target.with_name(f"{target.stem}-{n}{target.suffix}")
        if not found.exists():
            return found
        n += 1


def archive_season(save_dir: Path, world_dir: Path, season_id: str, now: int) -> Path:
    """季末重置用（唯一會寫封存的地方）：把 :data:`ARCHIVED` 從世界資料夾搬進
    ``archive/<季>/``、寫 ``manifest.json``，再把封存裡每個檔設成唯讀。回傳封存資料夾。"""
    target = season_archive_dir(save_dir, season_id)
    target.mkdir(parents=True, exist_ok=True)
    for name in ARCHIVED:
        source = world_dir / name
        if source.exists():
            source.rename(_free(target / name))
    manifest_path = target / MANIFEST_FILE
    if manifest_path.exists():  # 中斷後重跑：舊的清單是唯讀，先打開再重寫
        os.chmod(manifest_path, stat.S_IRUSR | stat.S_IWUSR)
    files = tuple(
        ArchiveFile(path=p.relative_to(target).as_posix(), sha256=_sha256(p), size=p.stat().st_size)
        for p in _files(target)
    )
    manifest = ArchiveManifest(season_id=season_id, archived_at=now, files=files)
    manifest_path.write_text(manifest.model_dump_json(indent=1) + "\n", encoding="utf-8")
    for path in [*_files(target), manifest_path]:
        os.chmod(path, _READ_ONLY)
    return target


# ---------------------------------------------------------------------------
# 查證（只讀）
# ---------------------------------------------------------------------------


class ReplayCheck(_Model):
    """一次查證的結果。"""

    kind: Literal["first_kill", "league_match"]
    season_id: str
    subject_zh: str
    """查的是哪一筆（例「碎晶之主的首殺：勇者c1」）。"""
    source: Literal["archive", "world"]
    """封存（舊季）或世界資料夾（目前這一季）。"""
    battle_log: str | None
    """重播的戰鬥紀錄（相對於來源資料夾）；精英首殺沒有戰鬥紀錄。"""
    ok: bool
    passed: tuple[str, ...]
    """通過的檢查。"""
    problems: tuple[str, ...]
    """不一致或查不了的地方（空＝一致）。"""


class _Source:
    """查證讀檔的地方：舊季＝封存，目前這一季（沒有封存）＝世界資料夾。只讀。"""

    def __init__(self, save_dir: Path, world_dir: Path, season_id: str) -> None:
        archived = season_archive_dir(save_dir, season_id)
        self.kind: Literal["archive", "world"] = "archive" if archived.is_dir() else "world"
        self.root = archived if self.kind == "archive" else world_dir
        self.manifest: dict[str, str] = {}
        path = archived / MANIFEST_FILE
        if self.kind == "archive" and path.is_file():
            found = ArchiveManifest.model_validate_json(path.read_text(encoding="utf-8"))
            self.manifest = {f.path: f.sha256 for f in found.files}

    def hash_problem(self, relative: str) -> str | None:
        """封存的檔和清單上的 sha256 不同＝被改過。"""
        expected = self.manifest.get(relative)
        if self.kind != "archive" or expected is None:
            return None
        path = self.root / relative
        if path.is_file() and _sha256(path) != expected:
            return f"封存檔 {relative} 和封存清單的 sha256 不同（封存後被改過）"
        return None


def _replay_problems(text: str) -> tuple[BattleLog | None, list[str]]:
    """重播一份戰鬥紀錄：格式、規則包雜湊、最終狀態與事件都要和紀錄一致。"""
    try:
        found = json.loads(text).get("format")
    except (json.JSONDecodeError, AttributeError):
        return None, ["戰鬥紀錄不是有效的 JSON"]
    problem = log_format_problem(found)
    if problem is not None:
        return None, [problem]
    try:
        log = BattleLog.model_validate_json(text)
    except ValidationError as exc:
        return None, [f"戰鬥紀錄的內容不合法：{exc.error_count()} 個錯誤"]
    problem = log_replay_problem(log)
    if problem is not None:
        return log, [problem]
    try:
        run = replay(log.setup, log.seed, log.actions)
    except TrpgError as exc:  # 紀錄被改過時，動作可能在重播裡不合法
        return log, [f"重播失敗：{exc}"]
    problems: list[str] = []
    if state_to_json(run.state) != state_to_json(log.final_state):
        problems.append("重播的最終狀態和紀錄不同")
    recorded = EVENT_LIST_ADAPTER.dump_json(log.events)
    if recorded != EVENT_LIST_ADAPTER.dump_json(run.events):  # type: ignore[arg-type]
        problems.append("重播的事件和紀錄不同")
    return log, problems


def _log_entry(source: _Source, seq: int) -> dict[str, object] | None:
    path = source.root / LOG_FILE
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if isinstance(entry, dict) and entry.get("seq") == seq:
            return entry
    return None


def _check_log_entry(
    source: _Source, kill: FirstKill, passed: list[str], problems: list[str]
) -> None:
    entry = _log_entry(source, kill.seq)
    hashed = source.hash_problem(LOG_FILE)
    if hashed is not None:
        problems.append(hashed)
    if entry is None:
        problems.append(f"世界日誌裡找不到序號 {kill.seq}")
    elif entry.get("character_id") != kill.character_id:
        problems.append(f"世界日誌序號 {kill.seq} 是別的角色（{entry.get('character_id')}）")
    else:
        passed.append(f"世界日誌序號 {kill.seq} 是 {kill.name} 的動作")


def verify_first_kill(save_dir: Path, world_dir: Path, season_id: str, target: str) -> ReplayCheck:
    """查證一筆首殺（``season_id`` 那一季、``target``＝精英種類或賽季 Boss ID）：世界日誌的序號是
    那個角色的動作；有戰鬥紀錄（賽季 Boss）就確定性重播、而且是我方勝。找不到首殺拋
    :class:`ArchiveRecordNotFoundError`。"""
    kill = next(
        (
            k
            for k in load_first_kills(world_dir / FIRST_KILLS_FILE)
            if k.season_id == season_id and k.target == target
        ),
        None,
    )
    if kill is None:
        raise ArchiveRecordNotFoundError(f"{season_id} 沒有 {target} 的首殺紀錄")
    source = _Source(save_dir, world_dir, season_id)
    passed: list[str] = []
    problems: list[str] = []
    _check_log_entry(source, kill, passed, problems)
    if kill.battle_log is not None:
        path = source.root / kill.battle_log
        if not path.is_file():
            problems.append(f"找不到戰鬥紀錄 {kill.battle_log}")
        else:
            hashed = source.hash_problem(kill.battle_log)
            problems += [] if hashed is None else [hashed]
            log, found = _replay_problems(path.read_text(encoding="utf-8"))
            problems += found
            if log is not None and not found:
                passed.append(f"戰鬥紀錄重播一致（{len(log.actions)} 個動作）")
                if log.final_state.winner is Team.ALLY:
                    passed.append("那一場是我方勝")
                else:
                    problems.append("戰鬥紀錄的結果不是我方勝")
    return ReplayCheck(
        kind="first_kill",
        season_id=season_id,
        subject_zh=f"{kill.target_name_zh}的首殺：{kill.name}",
        source=source.kind,
        battle_log=kill.battle_log,
        ok=not problems,
        passed=tuple(passed),
        problems=tuple(problems),
    )


def _league_record(source: _Source, season_id: str) -> LeagueRecord | None:
    path = source.root / LEAGUE_DIR / LEAGUE_FILE
    if not path.is_file():
        return None
    record = LeagueRecord.model_validate_json(path.read_text(encoding="utf-8"))
    return record if record.season_id == season_id else None


def _compare_match(log: BattleLog, match: LeagueMatch, passed: list[str]) -> list[str]:
    state = log.final_state
    problems: list[str] = []
    winner = match_winner(state, match.spec())
    if winner != match.winner:
        problems.append(
            f"重播的勝方（{winner or '和局'}）和賽程紀錄（{match.winner or '和局'}）不同"
        )
    if state.round != match.rounds:
        problems.append(f"重播的輪數 {state.round} 和賽程紀錄 {match.rounds} 不同")
    if state.end_reason != match.end_reason:
        problems.append(f"重播的結束原因 {state.end_reason} 和賽程紀錄 {match.end_reason} 不同")
    if not problems:
        passed.append(f"勝方、輪數（{match.rounds}）與結束原因和賽程紀錄一致")
    return problems


def verify_league_match(
    save_dir: Path, world_dir: Path, season_id: str, match_id: str
) -> ReplayCheck:
    """查證一場循環賽：確定性重播那一場的戰鬥紀錄，再比對賽程紀錄的勝方、輪數與結束原因（名次的
    依據）。找不到那一季的賽程或那一場拋 :class:`ArchiveRecordNotFoundError`。"""
    source = _Source(save_dir, world_dir, season_id)
    record = _league_record(source, season_id)
    match = None if record is None else record.match(match_id)
    if match is None:
        raise ArchiveRecordNotFoundError(f"{season_id} 的循環賽沒有場次 {match_id}")
    relative = f"{LEAGUE_DIR}/{LEAGUE_MATCHES_DIR}/{match_id}.json"
    passed: list[str] = []
    problems: list[str] = []
    for name in (f"{LEAGUE_DIR}/{LEAGUE_FILE}", relative):
        hashed = source.hash_problem(name)
        problems += [] if hashed is None else [hashed]
    path = source.root / relative
    if match.status != "done":
        problems.append(f"這一場沒有跑完（{match.status}）")
    elif not path.is_file():
        problems.append(f"找不到戰鬥紀錄 {relative}")
    else:
        log, found = _replay_problems(path.read_text(encoding="utf-8"))
        problems += found
        if log is not None and not found:
            passed.append(f"戰鬥紀錄重播一致（{len(log.actions)} 個動作）")
            problems += _compare_match(log, match, passed)
    return ReplayCheck(
        kind="league_match",
        season_id=season_id,
        subject_zh=f"循環賽 {match_id}（{match.a} 對 {match.b}）",
        source=source.kind,
        battle_log=relative,
        ok=not problems,
        passed=tuple(passed),
        problems=tuple(problems),
    )
