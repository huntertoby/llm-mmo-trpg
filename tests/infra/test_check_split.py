"""``scripts/check.py`` 依改動路徑分流（TS-1）：每條規則用假的改動清單測。"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE = "0123456789abcdef0123456789abcdef01234567"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_script_ts1", ROOT / "scripts" / "check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass 需要從 sys.modules 找到模組
    spec.loader.exec_module(module)
    return module


check = _load()


def _scope(*paths: str) -> str:
    return str(check.plan_scope(list(paths), BASE).scope)


# --- 規則：每一種改動路徑各一個 -----------------------------------------------------------


def test_only_client_runs_client_scope() -> None:
    assert _scope("client/src/battle/vfx.ts") == check.SCOPE_CLIENT


def test_client_with_markdown_is_still_client_scope() -> None:
    assert _scope("client/src/ui/Panel.tsx", "docs/phases/PhaseTS-1報告.md") == check.SCOPE_CLIENT


@pytest.mark.parametrize(
    "path", ["src/trpg/engine/resolve.py", "tests/engine/test_combat.py", "scripts/run_pytest.py"]
)
def test_only_backend_runs_backend_scope(path: str) -> None:
    assert _scope(path) == check.SCOPE_BACKEND


def test_backend_with_markdown_is_still_backend_scope() -> None:
    assert _scope("src/trpg/api/app.py", "docs/dev/上手-測試.md") == check.SCOPE_BACKEND


@pytest.mark.parametrize(
    "path",
    [
        "content/skills/fire.yaml",
        "content/README.md",  # content/ 底下的 .md 也全跑
        "config/models.yaml",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        "client/package.json",
        "client/pnpm-lock.yaml",
        "client/openapi.json",  # API schema 快照
        "client/src/api/schema.d.ts",  # API schema 前端型別
        "scripts/check.py",
    ],
)
def test_trigger_paths_run_everything(path: str) -> None:
    assert _scope(path) == check.SCOPE_ALL
    # 跟其他改動混在一起也一樣全跑。
    assert _scope("src/trpg/engine/resolve.py", path) == check.SCOPE_ALL
    assert _scope("client/src/battle/vfx.ts", path) == check.SCOPE_ALL


def test_client_and_backend_together_run_everything() -> None:
    assert _scope("client/src/battle/vfx.ts", "src/trpg/api/app.py") == check.SCOPE_ALL


UNKNOWN = ["docs/art/sample/x.png", ".github/workflows/ci.yml", ".claude/pm-workflow.json", "x.txt"]


@pytest.mark.parametrize("path", UNKNOWN)
def test_unknown_paths_run_everything(path: str) -> None:
    assert _scope(path) == check.SCOPE_ALL


def test_no_changes_or_only_markdown_run_everything() -> None:
    assert _scope() == check.SCOPE_ALL
    assert _scope("docs/phases/PhaseTS-1報告.md", "README.md") == check.SCOPE_ALL


def test_unknown_change_list_runs_everything() -> None:
    plan = check.plan_scope(None, None)
    assert plan.scope == check.SCOPE_ALL
    assert plan.base is None
    assert "判斷不出" in plan.reason


# --- git 失敗、基準 -----------------------------------------------------------------------


def _fake_git(answers: Mapping[str, str | None]) -> object:
    def fake(*args: str) -> str | None:
        for key, value in answers.items():
            if key in args:
                return value
        raise AssertionError(args)

    return fake


def test_missing_origin_main_gives_no_change_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check, "_git", _fake_git({"merge-base": None}))
    assert check.changed_paths() == (None, None)
    assert check.plan_scope(*check.changed_paths()).scope == check.SCOPE_ALL


def test_git_diff_failure_gives_no_change_list(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = {"merge-base": BASE, "diff": None, "ls-files": ""}
    monkeypatch.setattr(check, "_git", _fake_git(answers))
    assert check.changed_paths() == (None, None)


def test_change_list_merges_diff_and_untracked(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = {"merge-base": BASE, "diff": "src/a.py\nclient/b.ts\n", "ls-files": "tests/new.py\n"}
    monkeypatch.setattr(check, "_git", _fake_git(answers))
    assert check.changed_paths() == (["client/b.ts", "src/a.py", "tests/new.py"], BASE)


def test_base_ref_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(check.BASE_ENV, raising=False)
    assert check.base_ref() == "origin/main"
    monkeypatch.setenv(check.BASE_ENV, "HEAD")
    assert check.base_ref() == "HEAD"


# --- 步驟 ---------------------------------------------------------------------------------


def _titles(steps: list[object]) -> list[str]:
    return [s.title for s in steps]  # type: ignore[attr-defined]


def test_all_scope_runs_every_step() -> None:
    run, skipped = check.steps_for(check.Plan(check.SCOPE_ALL, "x"))
    assert _titles(run) == _titles(list(check.STEPS))
    assert skipped == []


def test_backend_scope_skips_the_client_steps() -> None:
    run, skipped = check.steps_for(check.Plan(check.SCOPE_BACKEND, "x", BASE))
    assert _titles(skipped) == ["client install", "client typecheck", "client test"]
    assert "pytest" in _titles(run) and "mypy" in _titles(run)
    assert "situation coverage" in _titles(run)


def test_client_scope_runs_client_steps_build_and_client_reading_tests() -> None:
    run, skipped = check.steps_for(
        check.Plan(check.SCOPE_CLIENT, "x", BASE), ["tests/api/test_openapi_snapshot.py"]
    )
    assert _titles(run) == [
        "client install",
        "client typecheck",
        "client test",
        "client build",
        check.CLIENT_PYTEST_TITLE,
    ]
    assert run[-1].args[-1] == "tests/api/test_openapi_snapshot.py"
    assert run[-1].script == check.WATCHDOG_SCRIPT
    assert "pytest" in _titles(skipped) and "ruff check" in _titles(skipped)


def test_client_scope_without_client_reading_tests_has_no_pytest() -> None:
    run, _ = check.steps_for(check.Plan(check.SCOPE_CLIENT, "x", BASE), [])
    assert check.CLIENT_PYTEST_TITLE not in _titles(run)


def test_client_reading_tests_finds_direct_and_helper_references(tmp_path: Path) -> None:
    (tmp_path / "tests" / "pkg").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "tests" / "pkg" / "test_direct.py").write_text(
        'P = ROOT / "client" / "src"\n', encoding="utf-8"
    )
    (tmp_path / "tests" / "pkg" / "fixture_maker.py").write_text(
        'OUT = "client/src/x.json"\n', encoding="utf-8"
    )
    (tmp_path / "tests" / "pkg" / "test_via_helper.py").write_text(
        "from tests.pkg.fixture_maker import OUT\n", encoding="utf-8"
    )
    (tmp_path / "scripts" / "export_thing.py").write_text('C = "client/a"\n', encoding="utf-8")
    (tmp_path / "tests" / "test_via_script.py").write_text(
        'S = ROOT / "scripts" / "export_thing.py"\n', encoding="utf-8"
    )
    (tmp_path / "tests" / "test_unrelated.py").write_text(
        "def test_x(client): ...\n", encoding="utf-8"
    )
    assert check.client_reading_tests(tmp_path) == [
        "tests/pkg/test_direct.py",
        "tests/pkg/test_via_helper.py",
        "tests/test_via_script.py",
    ]


def test_real_client_reading_tests_include_the_known_ones() -> None:
    found = set(check.client_reading_tests())
    assert {
        "tests/api/test_client_fixtures.py",
        "tests/api/test_openapi_snapshot.py",
        "tests/test_hardcoded_scan.py",
        "tests/shared/test_range_text.py",
    } <= found


def test_describe_says_what_runs_what_is_skipped_and_why() -> None:
    plan = check.Plan(check.SCOPE_BACKEND, "只動 src/", BASE, 3)
    line = check.describe(plan, *check.steps_for(plan))
    assert line.startswith("分流：只跑後端")
    assert BASE[:10] in line and "改動 3 個檔" in line
    assert "原因：只動 src/" in line
    assert "跑：ruff check" in line
    assert "略過：client install、client typecheck、client test" in line


# --- 戳記與 main ----------------------------------------------------------------------------


def _stamp_git(common: Path) -> object:
    answers = {
        "status": "",
        "HEAD^{tree}": "tree123",
        "HEAD": "commit456",
        "--git-common-dir": str(common),
    }

    def fake(*args: str) -> str | None:
        return answers[args[-1]] if args[-1] in answers else answers[args[0]]

    return fake


def test_full_scope_stamp_goes_where_the_hook_looks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(check, "_git", _stamp_git(tmp_path))
    stamp = check.write_pass_stamp(check.Plan(check.SCOPE_ALL, "x", BASE, 1))
    assert stamp == tmp_path / "pm-check-pass" / "tree123"
    assert stamp.read_text(encoding="utf-8") == f"commit456\nscope: all\nbase: {BASE}\n"


@pytest.mark.parametrize("scope", ["client", "backend"])
def test_split_stamp_goes_elsewhere(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scope: str
) -> None:
    monkeypatch.setattr(check, "_git", _stamp_git(tmp_path))
    stamp = check.write_pass_stamp(check.Plan(scope, "x", BASE, 1))
    assert stamp == tmp_path / "pm-check-pass-split" / "tree123"
    assert stamp.read_text(encoding="utf-8") == f"commit456\nscope: {scope}\nbase: {BASE}\n"
    assert not (tmp_path / "pm-check-pass").exists()


def _run_main(monkeypatch: pytest.MonkeyPatch, args: list[str], changed: object) -> list[str]:
    ran: list[str] = []

    def fake_run(step: object) -> str:
        ran.append(step.title)  # type: ignore[attr-defined]
        return "通過"

    monkeypatch.setattr(check, "run_step", fake_run)
    monkeypatch.setattr(check, "changed_paths", changed)
    monkeypatch.setattr(check, "write_pass_stamp", lambda plan: None)
    monkeypatch.setattr(check, "client_reading_tests", lambda: [])
    assert check.main(args) == 0
    return ran


def test_main_splits_by_change_list(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ran = _run_main(monkeypatch, [], lambda: (["client/src/a.ts"], BASE))
    assert ran == ["client install", "client typecheck", "client test", "client build"]
    first = capsys.readouterr().out.splitlines()[0]
    assert first.startswith("分流：只跑前端")


@pytest.mark.parametrize("flag", ["--full", "--all"])
def test_flags_force_everything_without_looking_at_git(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    monkeypatch.setenv("TRPG_FULL", "")

    def no_git() -> object:
        raise AssertionError("不該看改動")

    ran = _run_main(monkeypatch, [flag], no_git)
    assert ran == _titles(list(check.STEPS))


def test_unknown_argument_prints_usage() -> None:
    assert check.main(["--nope"]) == 2
