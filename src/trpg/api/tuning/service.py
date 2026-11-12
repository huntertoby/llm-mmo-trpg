"""數值工坊的服務層（NW-1a；技能、招式組、地圖戰 NW-2a）：把白名單、草稿、驗證、差異、寫回、模擬
串起來，給端點用。

伺服器內一份（``app.state.tuning``）；只在 ``dev_mode`` 且 ``TRPG_TUNING=1`` 時建立（三道門見
:mod:`trpg.api.tuning.routes`）。所有資料放 ``<save_dir>/tuning/``（不在 ``content/``、不進 git）。
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

from trpg.api.tuning.check import (
    Prepared,
    kind_resolver,
    library_errors,
    prepare,
    schema_errors,
    to_changes,
)
from trpg.api.tuning.diff import change_views, diff_rows, make_diff
from trpg.api.tuning.drafts import Change, Draft, DraftStore, merge
from trpg.api.tuning.git_guard import Git, GitError
from trpg.api.tuning.objects import (
    ObjectNotFoundError,
    field_limits,
    list_objects,
    object_detail,
    object_file,
)
from trpg.api.tuning.schemas import (
    TuningApplyResult,
    TuningBudgetResult,
    TuningChangeIn,
    TuningCheckResult,
    TuningDiff,
    TuningDraftView,
    TuningFieldError,
    TuningGroupIn,
    TuningGroupPreset,
    TuningGroupPreview,
    TuningHistoryEntry,
    TuningMinMovesFlag,
    TuningObjectDetail,
    TuningObjectSummary,
    TuningSimBoss,
    TuningSimBuild,
    TuningSimJob,
    TuningSimMap,
    TuningSimOptions,
    TuningSimRequest,
    TuningStatus,
)
from trpg.api.tuning.sim_jobs import MAX_BATTLES, SimJobs, SimRequestError
from trpg.api.tuning.skills import (
    GROUP_PRESETS,
    add_budget_side_changes,
    budget_result,
    group_preview,
)
from trpg.api.tuning.workspace import Workspace, tree_digest
from trpg.api.tuning.writeback import (
    RESTART_NOTE_ZH,
    WritebackError,
    apply_prepared,
    reverse_of_commit,
    writeback_problem,
)
from trpg.content.enemy_moves import BOSS, ELITE, MOB, move_shortfalls
from trpg.content.library import ContentLibrary, load_library
from trpg.content.loader import parse_yaml
from trpg.content.skills import SkillDef
from trpg.content.tuning_fields import TuningFields, load_tuning_fields
from trpg.sim.boss_probe import BOSS_NAMES, BOSSES, BUILDS
from trpg.sim.skill_probe import map_jobs, probe_maps

__all__ = [
    "DEFAULT_MAP_SEEDS",
    "DEFAULT_SIM_SEEDS",
    "MAX_SIM_MAPS",
    "TUNING_ENV",
    "DraftInputError",
    "TuningService",
    "tuning_enabled",
]

TUNING_ENV: Final = "TRPG_TUNING"
DEFAULT_SIM_SEEDS: Final = 3
"""預設「小」：1 個頭目 × 8 build × 3 種子＝24 場（第 0.0 節第 5 點）。"""
DEFAULT_MAP_SEEDS: Final = 24
"""地圖戰預設：1 張圖 × 24 種子（NW-2 5.6）。"""
MAX_SIM_MAPS: Final = 3
_NOT_RESTARTED_ZH: Final = "這次開伺服器以來沒有寫回；遊戲用的是目前的數值。"


def tuning_enabled(flag: bool | None = None) -> bool:
    """第二道門：``flag`` 沒給時看環境變數 ``TRPG_TUNING=1``。"""
    return flag if flag is not None else os.environ.get(TUNING_ENV) == "1"


def _today() -> str:
    return date.today().isoformat()


class DraftInputError(ValueError):
    """草稿的輸入不對（422，訊息是中文）。"""


def _confirmed(
    what: str, need: Sequence[str], messages: Sequence[str], given: Sequence[str]
) -> None:
    """寫回前的「我確定」：``given`` 要恰好等於 ``need``，否則丟 :class:`WritebackError`（409）。"""
    want, got = sorted(set(need)), sorted(set(given))
    if want == got:
        return
    if not got:
        raise WritebackError("；".join(messages))
    raise WritebackError(
        f"勾「我確定」的和{what}不符：要確認 {'、'.join(want) or '（沒有）'}，"
        f"收到 {'、'.join(got)}；請重新驗證"
    )


class TuningService:
    """數值工坊（一個伺服器一份）。"""

    def __init__(
        self,
        content_dir: Path,
        save_dir: Path,
        library: ContentLibrary | None = None,
        *,
        sims: SimJobs | None = None,
        today: Callable[[], str] = _today,
    ) -> None:
        self.content_dir = content_dir
        self.root = save_dir / "tuning"
        self.library = library
        self.table: TuningFields = load_tuning_fields(content_dir)
        self.kind_of = kind_resolver(self.table)
        self.drafts = DraftStore(self.root / "drafts")
        self.workspace = Workspace(content_dir, self.root / "work")
        self.sims = sims if sims is not None else SimJobs(self.root / "sims")
        self.git = Git.find(content_dir)
        self.today = today
        self.writes: list[str] = []
        self._check_lock = threading.Lock()
        self._gen_lock = threading.Lock()
        self._generation = 0
        self._base: ContentLibrary | None = None
        self._base_shortfalls: frozenset[str] | None = None

    def _rules_library(self) -> ContentLibrary:
        """算預算用的內容庫：伺服器啟動時載入的那份（沒有時載一次專案內容）。預算只依賴表
        （``skill_budget.yaml``、原語、狀態…），不依賴別招，工坊也改不到這些表。"""
        if self.library is not None:
            return self.library
        if self._base is None:
            self._base = load_library(self.content_dir)
        return self._base

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

    def objects(self, kind: str | None = None) -> list[TuningObjectSummary]:
        table = self.table
        if kind is not None:
            target = table.target(kind)
            if target is None:
                return []
            table = table.model_copy(update={"targets": (target,)})
        return list_objects(self.content_dir, table, self.library)

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
        changes, errors = to_changes(items, self.kind_of)
        if errors:
            raise DraftInputError("；".join(f"{e.path}：{e.message_zh}" for e in errors))
        return self._view(self.drafts.put(Draft(name=name, changes=tuple(changes))))

    def delete_draft(self, name: str) -> bool:
        return self.drafts.delete(name)

    # -- 驗證、差異 --------------------------------------------------------

    def _prepare(self, changes: Sequence[Change]) -> Prepared:
        """對到白名單、字面替換，再加預算例外的附帶改動（NW-2a T5）。"""
        prepared = prepare(self.content_dir, self.table, changes)
        if not prepared.errors and any(k == "skill" for k in prepared.kinds.values()):
            add_budget_side_changes(prepared, self.content_dir, self._rules_library(), self.today())
        return prepared

    def _validate(
        self, changes: Sequence[Change], extra: Sequence[TuningFieldError] = ()
    ) -> tuple[TuningCheckResult, Prepared]:
        started = time.perf_counter()
        prepared = self._prepare(changes)
        fields = [*extra, *prepared.errors]
        page: list[str] = []
        if not fields:
            more, page = schema_errors(prepared)
            fields += more
        if not fields and not page and prepared.texts:
            loaded: list[ContentLibrary] = []
            more, page = library_errors(self.workspace.draft(prepared.texts), prepared, loaded)
            fields += more
            if loaded and any(k == "unit" for k in prepared.kinds.values()):
                prepared.needs_moves = self._min_move_flags(loaded[0])
        result = TuningCheckResult(
            ok=not fields and not page,
            field_errors=fields,
            page_errors=page,
            seconds=round(time.perf_counter() - started, 2),
            needs_confirm_budget=prepared.needs_confirm,
            side_changes=prepared.side,
            needs_confirm_min_moves=prepared.needs_moves,
        )
        return result, prepared

    def _min_move_flags(self, draft: ContentLibrary) -> list[TuningMinMovesFlag]:
        """草稿讓哪些單位新低於 #149 的招數下限（R1；改前就低於的不算，目前內建沒有）。"""
        if self._base_shortfalls is None:
            self._base_shortfalls = frozenset(move_shortfalls(self._rules_library()))
        fresh = [s for s in move_shortfalls(draft) if s not in self._base_shortfalls]
        by_unit: dict[str, list[str]] = {}
        for item in fresh:
            by_unit.setdefault(re.split(r"[/=]", item, maxsplit=1)[0], []).append(item)
        flags: list[TuningMinMovesFlag] = []
        for unit_id in sorted(by_unit):
            unit = draft.units.get(unit_id)
            name = unit.name_zh if unit is not None else unit_id
            flags.append(
                TuningMinMovesFlag(
                    unit_id=unit_id,
                    name_zh=name,
                    shortfalls=by_unit[unit_id],
                    message_zh=(
                        f"{name}（{unit_id}）低於 #149 的招數下限"
                        f"（一般 {MOB} 招、精英 {ELITE} 招、頭目每階段 {BOSS} 招）："
                        f"{'、'.join(by_unit[unit_id])}；要寫回請勾「我確定」"
                    ),
                )
            )
        return flags

    def check(self, name: str, items: Sequence[TuningChangeIn] | None = None) -> TuningCheckResult:
        """驗證草稿（給了 ``items`` 就驗它，不必先存）。同一時間只做一個；後到的取代先到的。"""
        if items is None:
            changes: Sequence[Change] = self.drafts.get(name).changes
            errors: list[TuningFieldError] = []
        else:
            changes, errors = to_changes(items, self.kind_of)
        with self._gen_lock:
            self._generation += 1
            mine = self._generation
        with self._check_lock:
            if mine != self._generation:
                return TuningCheckResult(ok=False, superseded=True)
            return self._validate(changes, errors)[0]

    def diff(self, name: str) -> TuningDiff:
        prepared = self._prepare(self.drafts.get(name).changes)
        return make_diff(self.content_dir, self.table, prepared)

    # -- 技能：預算、分組 --------------------------------------------------

    def budget(self, skill_id: str, items: Sequence[TuningChangeIn] = ()) -> TuningBudgetResult:
        """一招套上 ``items``（只取這招的檔）之後的預算比例與違規（NW-2a T4）。"""
        target = self.table.target("skill")
        if target is None:
            raise ObjectNotFoundError("數值工坊沒有開技能")
        path = object_file(self.content_dir, target, skill_id)
        rel = path.relative_to(self.content_dir).as_posix()
        library = self._rules_library()
        changes, errors = to_changes([i for i in items if i.file == rel], self.kind_of)
        text = path.read_bytes().decode("utf-8")
        if changes and not errors:
            prepared = prepare(self.content_dir, self.table, changes)
            errors = list(prepared.errors)
            if not errors:
                fields, page = schema_errors(prepared)
                errors = fields + [TuningFieldError(file=rel, path="", message_zh=p) for p in page]
                text = prepared.texts.get(rel, text)
        skill = None
        if not errors:
            try:
                skill = SkillDef.model_validate(parse_yaml(text.removeprefix("﻿")))
            except (ValidationError, ValueError) as exc:
                errors = [TuningFieldError(file=rel, path="", message_zh=str(exc))]
        listed = self._listed_exceptions()
        if skill is None:
            rules = library.budget
            return TuningBudgetResult(
                skill_id=skill_id,
                ratio_permille=None,
                ratio_text="—",
                min_ratio_permille=rules.min_ratio_permille,
                max_ratio_permille=rules.max_ratio_permille,
                verdict="error",
                verdict_zh="改動有錯",
                known_exception=skill_id in listed,
                field_errors=errors,
                error_zh="改動有錯，先修正再看預算",
            )
        return budget_result(skill, library, listed)

    def _listed_exceptions(self) -> list[str]:
        """磁碟上（寫回後的最新）``known_budget_exceptions``。"""
        data = parse_yaml((self.content_dir / "skill_budget.yaml").read_text(encoding="utf-8"))
        found = data.get("known_budget_exceptions") if isinstance(data, dict) else None
        return [str(x) for x in found] if isinstance(found, list) else []

    def group_preview(self, request: TuningGroupIn) -> TuningGroupPreview:
        target = self.table.target("skill")
        if target is None:
            raise ObjectNotFoundError("數值工坊沒有開技能")

        def limits(data: Any, path: str) -> tuple[int | None, int | None]:
            found = target.field_for(path)
            if found is None:
                return None, None
            return field_limits(self.content_dir, data, found, path)

        return group_preview(self.content_dir, target, request, self._rules_library(), limits)

    def presets(self) -> list[TuningGroupPreset]:
        return list(GROUP_PRESETS)

    # -- 寫回、還原 --------------------------------------------------------

    def apply(
        self, name: str, confirm_budget: Sequence[str] = (), confirm_min_moves: Sequence[str] = ()
    ) -> TuningApplyResult:
        draft = self.drafts.get(name)
        with self._check_lock:
            result, prepared = self._validate(draft.changes)
            if not result.ok:
                reasons = [f"{e.path}：{e.message_zh}" for e in result.field_errors]
                text = "；".join(reasons + result.page_errors)
                raise WritebackError(f"草稿驗證沒過，沒有寫回：{text}")
            _confirmed(
                "超出預算的技能",
                [f.skill_id for f in prepared.needs_confirm],
                [f.message_zh for f in prepared.needs_confirm],
                confirm_budget,
            )
            _confirmed(
                "低於 #149 招數下限的單位",
                [f.unit_id for f in prepared.needs_moves],
                [f.message_zh for f in prepared.needs_moves],
                confirm_min_moves,
            )
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
            maps=[TuningSimMap(id=m, name_zh=library.maps[m].name_zh) for m in probe_maps(library)],
            map_default_seeds=DEFAULT_MAP_SEEDS,
            map_seconds_per_battle=self.sims.map_seconds_per_battle,
        )

    def _sim_roots(self, draft_name: str) -> tuple[Prepared, str, Path, Path]:
        prepared = prepare(self.content_dir, self.table, self.drafts.get(draft_name).changes)
        fields: list[TuningFieldError] = list(prepared.errors)
        page: list[str] = []
        if not fields:
            fields, page = schema_errors(prepared)
        if fields or page:
            raise SimRequestError("草稿有錯，先修正再模擬（按「驗證」看哪裡錯）")
        digest = tree_digest(self.content_dir)
        _tree, before_root = self.workspace.base(digest)
        after_root = self.workspace.draft(prepared.texts, digest)
        return prepared, digest, before_root, after_root

    def start_sim(self, request: TuningSimRequest) -> TuningSimJob:
        if request.scenario == "map":
            return self._start_map(request)
        library = self._live()
        if request.boss is None:
            raise SimRequestError("頭目戰要選頭目")
        _prepared, digest, before_root, after_root = self._sim_roots(request.draft)
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

    def _start_map(self, request: TuningSimRequest) -> TuningSimJob:
        library = self._live()
        maps = list(dict.fromkeys(request.maps or ()))
        allowed = set(probe_maps(library))
        bad = [m for m in maps if m not in allowed]
        if not maps or len(maps) > MAX_SIM_MAPS or bad:
            raise SimRequestError(
                f"地圖要選 1～{MAX_SIM_MAPS} 張有預設遭遇的地圖"
                + (f"（不能用：{'、'.join(bad)}）" if bad else "")
            )
        known = {b.id for b in library.builds.builds}
        inject = [(i.build, i.skill) for i in request.inject]
        allies = list(request.allies) if request.allies else None
        if (
            allies is None and inject
        ):  # 「裝到 build」：我方沒指定時就用那幾個 build（標準隊友補滿）
            allies = list(dict.fromkeys(b for b, _s in inject))
        bad_builds = sorted({b for b in (allies or []) if b not in known})
        bad_builds += sorted({b for b, _s in inject if b not in known})
        if bad_builds:
            raise SimRequestError(f"build 不對：{'、'.join(bad_builds)}")
        missing = sorted({s for _b, s in inject if s not in library.skills})
        if missing:
            raise SimRequestError(f"沒有這招：{'、'.join(missing)}")
        prepared, digest, before_root, after_root = self._sim_roots(request.draft)
        probe = list(dict.fromkeys(request.probe)) or sorted(
            Path(c.file).stem for c in prepared.changes if c.file.startswith("skills/")
        )
        jobs = map_jobs(maps, request.seeds, allies, inject, probe)
        return self.sims.start_map(
            jobs=jobs,
            probe=probe,
            before_root=before_root,
            after_root=after_root,
            before_key=SimJobs.map_before_key(digest, jobs),
        )

    def shutdown(self) -> None:
        self.sims.shutdown()
