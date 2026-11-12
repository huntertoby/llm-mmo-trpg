"""數值工坊的服務層（NW-1a）：把白名單、草稿、驗證、差異、寫回、模擬串起來，給端點用。

伺服器內一份（``app.state.tuning``）；只在 ``dev_mode`` 且 ``TRPG_TUNING=1`` 時建立（三道門見
:mod:`trpg.api.tuning.routes`）。所有資料放 ``<save_dir>/tuning/``（不在 ``content/``、不進 git）。
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

from trpg.api.tuning.check import Prepared, library_errors, prepare, schema_errors, to_changes
from trpg.api.tuning.diff import change_views, diff_rows, make_diff
from trpg.api.tuning.drafts import Change, Draft, DraftStore, merge
from trpg.api.tuning.git_guard import Git, GitError
from trpg.api.tuning.objects import list_objects, object_detail
from trpg.api.tuning.schemas import (
    TuningApplyResult,
    TuningChangeIn,
    TuningCheckResult,
    TuningDiff,
    TuningDraftView,
    TuningFieldError,
    TuningHistoryEntry,
    TuningObjectDetail,
    TuningObjectSummary,
    TuningSimBoss,
    TuningSimBuild,
    TuningSimJob,
    TuningSimOptions,
    TuningSimRequest,
    TuningStatus,
)
from trpg.api.tuning.sim_jobs import MAX_BATTLES, SimJobs, SimRequestError
from trpg.api.tuning.workspace import Workspace, tree_digest
from trpg.api.tuning.writeback import (
    RESTART_NOTE_ZH,
    WritebackError,
    apply_prepared,
    reverse_of_commit,
    writeback_problem,
)
from trpg.content.library import ContentLibrary
from trpg.content.tuning_fields import TuningFields, load_tuning_fields
from trpg.sim.boss_probe import BOSS_NAMES, BOSSES, BUILDS

__all__ = [
    "DEFAULT_SIM_SEEDS",
    "TUNING_ENV",
    "DraftInputError",
    "TuningService",
    "tuning_enabled",
]

TUNING_ENV: Final = "TRPG_TUNING"
DEFAULT_SIM_SEEDS: Final = 3
"""預設「小」：1 個頭目 × 8 build × 3 種子＝24 場（第 0.0 節第 5 點）。"""
_NOT_RESTARTED_ZH: Final = "這次開伺服器以來沒有寫回；遊戲用的是目前的數值。"


def tuning_enabled(flag: bool | None = None) -> bool:
    """第二道門：``flag`` 沒給時看環境變數 ``TRPG_TUNING=1``。"""
    return flag if flag is not None else os.environ.get(TUNING_ENV) == "1"


class DraftInputError(ValueError):
    """草稿的輸入不對（422，訊息是中文）。"""


class TuningService:
    """數值工坊（一個伺服器一份）。"""

    def __init__(
        self,
        content_dir: Path,
        save_dir: Path,
        library: ContentLibrary | None = None,
        *,
        sims: SimJobs | None = None,
    ) -> None:
        self.content_dir = content_dir
        self.root = save_dir / "tuning"
        self.library = library
        self.table: TuningFields = load_tuning_fields(content_dir)
        self.drafts = DraftStore(self.root / "drafts")
        self.workspace = Workspace(content_dir, self.root / "work")
        self.sims = sims if sims is not None else SimJobs(self.root / "sims")
        self.git = Git.find(content_dir)
        self.writes: list[str] = []
        self._check_lock = threading.Lock()
        self._gen_lock = threading.Lock()
        self._generation = 0

    # -- 狀態與對象 --------------------------------------------------------

    def status(self) -> TuningStatus:
        problem = writeback_problem(self.git, self.content_dir)
        return TuningStatus(
            can_write=problem is None,
            reason_zh=problem,
            restart_needed=bool(self.writes),
            restart_note_zh=RESTART_NOTE_ZH if self.writes else _NOT_RESTARTED_ZH,
            drafts=self.drafts.names(),
            sim_running=self.sims.running,
        )

    def objects(self) -> list[TuningObjectSummary]:
        return list_objects(self.content_dir, self.table)

    def object(self, kind: str, object_id: str) -> TuningObjectDetail:
        return object_detail(self.content_dir, self.table, kind, object_id, self.library)

    # -- 草稿 --------------------------------------------------------------

    def _view(self, draft: Draft) -> TuningDraftView:
        return TuningDraftView(
            name=draft.name, changes=change_views(self.content_dir, self.table, draft.changes)
        )

    def draft(self, name: str) -> TuningDraftView:
        return self._view(self.drafts.get(name))

    def put_draft(self, name: str, items: Iterable[TuningChangeIn]) -> TuningDraftView:
        changes, errors = to_changes(items)
        if errors:
            raise DraftInputError("；".join(f"{e.path}：{e.message_zh}" for e in errors))
        return self._view(self.drafts.put(Draft(name=name, changes=tuple(changes))))

    def delete_draft(self, name: str) -> bool:
        return self.drafts.delete(name)

    # -- 驗證、差異 --------------------------------------------------------

    def _validate(
        self, changes: Sequence[Change], extra: Sequence[TuningFieldError] = ()
    ) -> tuple[TuningCheckResult, Prepared]:
        started = time.perf_counter()
        prepared = prepare(self.content_dir, self.table, changes)
        fields = [*extra, *prepared.errors]
        page: list[str] = []
        if not fields:
            more, page = schema_errors(prepared)
            fields += more
        if not fields and not page and prepared.texts:
            more, page = library_errors(self.workspace.draft(prepared.texts), prepared)
            fields += more
        result = TuningCheckResult(
            ok=not fields and not page,
            field_errors=fields,
            page_errors=page,
            seconds=round(time.perf_counter() - started, 2),
        )
        return result, prepared

    def check(self, name: str, items: Sequence[TuningChangeIn] | None = None) -> TuningCheckResult:
        """驗證草稿（給了 ``items`` 就驗它，不必先存）。同一時間只做一個；後到的取代先到的。"""
        if items is None:
            changes: Sequence[Change] = self.drafts.get(name).changes
            errors: list[TuningFieldError] = []
        else:
            changes, errors = to_changes(items)
        with self._gen_lock:
            self._generation += 1
            mine = self._generation
        with self._check_lock:
            if mine != self._generation:
                return TuningCheckResult(ok=False, superseded=True)
            return self._validate(changes, errors)[0]

    def diff(self, name: str) -> TuningDiff:
        prepared = prepare(self.content_dir, self.table, self.drafts.get(name).changes)
        return make_diff(self.content_dir, self.table, prepared)

    # -- 寫回、還原 --------------------------------------------------------

    def apply(self, name: str) -> TuningApplyResult:
        draft = self.drafts.get(name)
        with self._check_lock:
            result, prepared = self._validate(draft.changes)
            if not result.ok:
                reasons = [f"{e.path}：{e.message_zh}" for e in result.field_errors]
                text = "；".join(reasons + result.page_errors)
                raise WritebackError(f"草稿驗證沒過，沒有寫回：{text}")
            rows = diff_rows(self.content_dir, self.table, prepared.changes)
            done = apply_prepared(
                content_dir=self.content_dir,
                git=self.git,
                prepared=prepared,
                rows=rows,
                backups=self.root / "backups",
            )
        self.writes.append(done.commit)
        self.drafts.delete(name)
        return done

    def revert(self, name: str, commit: str) -> TuningDraftView:
        """把某筆 ``tune:`` commit 的反向改動單併進草稿（不直接寫回；照樣驗證後再寫回）。"""
        changes = reverse_of_commit(self.git, self.content_dir, self.table, commit)
        draft = self.drafts.get(name)
        merged = Draft(name=name, changes=merge(draft.changes, changes))
        return self._view(self.drafts.put(merged))

    def history(self, limit: int = 20) -> list[TuningHistoryEntry]:
        if self.git is None:
            return []
        try:
            rows = self.git.tune_log(limit)
        except GitError:
            return []
        return [TuningHistoryEntry(commit=r.commit, summary=r.summary, date=r.date) for r in rows]

    # -- 模擬 --------------------------------------------------------------

    def _live(self) -> ContentLibrary:
        if self.library is None:
            raise SimRequestError("伺服器沒有載入內容庫，不能模擬")
        return self.library

    def sim_options(self) -> TuningSimOptions:
        library = self._live()
        names = {b.id: b.name_zh for b in library.builds.builds}
        return TuningSimOptions(
            bosses=[
                TuningSimBoss(key=k, name_zh=BOSS_NAMES[k], unit_id=v[0])
                for k, v in BOSSES.items()
                if v[0] in library.units
            ],
            builds=[TuningSimBuild(id=b, name_zh=names.get(b, b)) for b in BUILDS],
            default_seeds=DEFAULT_SIM_SEEDS,
            max_battles=MAX_BATTLES,
            workers=self.sims.workers,
            seconds_per_battle=self.sims.seconds_per_battle,
        )

    def start_sim(self, request: TuningSimRequest) -> TuningSimJob:
        library = self._live()
        prepared = prepare(self.content_dir, self.table, self.drafts.get(request.draft).changes)
        fields: list[TuningFieldError] = list(prepared.errors)
        page: list[str] = []
        if not fields:
            fields, page = schema_errors(prepared)
        if fields or page:
            raise SimRequestError("草稿有錯，先修正再模擬（按「驗證」看哪裡錯）")
        digest = tree_digest(self.content_dir)
        _tree, before_root = self.workspace.base(digest)
        after_root = self.workspace.draft(prepared.texts, digest)
        builds = list(request.builds) if request.builds else list(BUILDS)
        return self.sims.start(
            library,
            which=request.boss,
            builds=builds,
            seeds=request.seeds,
            before_root=before_root,
            after_root=after_root,
            before_key=SimJobs.before_key(digest, request.boss, builds, request.seeds),
        )

    def shutdown(self) -> None:
        self.sims.shutdown()
