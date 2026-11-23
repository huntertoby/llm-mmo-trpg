"""``scripts/check.py --testmon``（TS-2 試用）：只在只跑後端時用、不寫戳記、開頭那一行。"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE = "0123456789abcdef0123456789abcdef01234567"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_script_ts2", ROOT / "scripts" / "check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass 需要從 sys.modules 找到模組
    spec.loader.exec_module(module)
    return module


check = _load()

BACKEND = (["src/trpg/engine/a.py", "tests/engine/test_a.py"], BASE)
PREVIEW = check.TestmonPreview(selected=12, skipped=345, new_db=False)


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    changed: tuple[list[str], str],
    preview: object = PREVIEW,
) -> tuple[list[tuple[str, tuple[str, ...]]], list[object], list[str]]:
    """跑 main；回傳（跑過的步驟與參數、寫戳記的呼叫、預先收集的呼叫）。"""
    ran: list[tuple[str, tuple[str, ...]]] = []
    stamps: list[object] = []
    previews: list[str] = []

    def fake_run(step: object) -> str:
        ran.append((step.title, step.args))  # type: ignore[attr-defined]
        return "通過"

    def fake_stamp(plan: object) -> None:
        stamps.append(plan)

    def fake_preview() -> object:
        previews.append("called")
        return preview

    monkeypatch.setattr(check, "run_step", fake_run)
    monkeypatch.setattr(check, "changed_paths", lambda: changed)
    monkeypatch.setattr(check, "write_pass_stamp", fake_stamp)
    monkeypatch.setattr(check, "client_reading_tests", lambda: [])
    monkeypatch.setattr(check, "testmon_preview", fake_preview)
    assert check.main(args) == 0
    return ran, stamps, previews


def _pytest_args(ran: list[tuple[str, tuple[str, ...]]]) -> tuple[str, ...]:
    return next(args for title, args in ran if title == "pytest")


# --- 後端範圍才啟用 ---------------------------------------------------------------------------


def test_backend_scope_uses_testmon_and_writes_no_stamp(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ran, stamps, previews = _run_main(monkeypatch, ["--testmon"], BACKEND)
    assert previews == ["called"]
    assert check.TESTMON_PYTEST_ARG in _pytest_args(ran)
    assert "client test" not in [title for title, _ in ran]
    assert stamps == []  # 不寫任何戳記（hook 看的、分流的都不寫）
    out = capsys.readouterr().out
    first = out.splitlines()[0]
    assert first.startswith("分流：只跑後端")
    assert "這次用 testmon（試用）：選了 12 個測試、略過 345 個" in first
    assert "不寫通過戳記" in first


def test_new_testmon_database_says_so_on_the_first_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    preview = check.TestmonPreview(selected=18000, skipped=0, new_db=True)
    _run_main(monkeypatch, ["--testmon"], BACKEND, preview)
    first = capsys.readouterr().out.splitlines()[0]
    assert "選了 18000 個測試、略過 0 個（還沒有 .testmondata" in first


def test_without_the_flag_backend_scope_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    ran, stamps, previews = _run_main(monkeypatch, [], BACKEND)
    assert previews == []
    assert check.TESTMON_PYTEST_ARG not in _pytest_args(ran)
    assert len(stamps) == 1  # 照 TS-1：分流戳記照寫


# --- 前端、全跑範圍不啟用 -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("changed", "label"),
    [
        ((["client/src/a.ts"], BASE), "只跑前端"),
        ((["content/units/a.yaml"], BASE), "全跑"),
        ((["src/trpg/a.py", "client/src/a.ts"], BASE), "全跑"),
    ],
)
def test_other_scopes_do_not_use_testmon(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    changed: tuple[list[str], str],
    label: str,
) -> None:
    ran, stamps, previews = _run_main(monkeypatch, ["--testmon"], changed)
    assert previews == []
    assert all(check.TESTMON_PYTEST_ARG not in args for _, args in ran)
    assert len(stamps) == 1  # 沒用 testmon：戳記規則照 TS-1
    first = capsys.readouterr().out.splitlines()[0]
    assert f"指定 --testmon，但不用 testmon：這次範圍是{label}" in first


@pytest.mark.parametrize("flag", ["--all", "--full"])
def test_forced_full_runs_do_not_use_testmon(monkeypatch: pytest.MonkeyPatch, flag: str) -> None:
    monkeypatch.setenv("TRPG_FULL", "")
    ran, stamps, previews = _run_main(monkeypatch, [flag, "--testmon"], BACKEND)
    assert previews == []
    assert all(check.TESTMON_PYTEST_ARG not in args for _, args in ran)
    assert len(stamps) == 1


def test_non_python_backend_change_does_not_use_testmon(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    changed = (["src/trpg/a.py", "tests/fixtures/snap.json"], BASE)
    ran, _, previews = _run_main(monkeypatch, ["--testmon"], changed)
    assert previews == []
    assert check.TESTMON_PYTEST_ARG not in _pytest_args(ran)
    first = capsys.readouterr().out.splitlines()[0]
    assert "testmon 追不到的非 .py 檔（tests/fixtures/snap.json）" in first


def test_failed_preview_falls_back_without_testmon(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ran, stamps, _ = _run_main(monkeypatch, ["--testmon"], BACKEND, preview=None)
    assert check.TESTMON_PYTEST_ARG not in _pytest_args(ran)
    assert len(stamps) == 1
    first = capsys.readouterr().out.splitlines()[0]
    assert "testmon 預先收集失敗，退回不用 testmon" in first


def test_markdown_alongside_backend_python_still_uses_testmon() -> None:
    plan = check.plan_scope(["src/trpg/a.py", "docs/a.md"], BASE)
    assert check.testmon_blocker(plan) is None


def test_failed_testmon_run_returns_one_and_writes_no_stamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stamps: list[object] = []
    monkeypatch.setattr(
        check, "run_step", lambda step: "失敗" if step.title == "pytest" else "通過"
    )
    monkeypatch.setattr(check, "changed_paths", lambda: BACKEND)
    monkeypatch.setattr(check, "write_pass_stamp", stamps.append)
    monkeypatch.setattr(check, "testmon_preview", lambda: PREVIEW)
    assert check.main(["--testmon"]) == 1
    assert stamps == []


# --- 預先收集的結果解析 -----------------------------------------------------------------------


class _Done:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


@pytest.mark.parametrize(
    ("done", "expected"),
    [
        (_Done(0, 'noise\n{"selected": 3, "skipped": 9, "new_db": false}\n'), (3, 9, False)),
        (_Done(1, '{"selected": 3, "skipped": 9, "new_db": false}'), None),
        (_Done(0, ""), None),
        (_Done(0, "not json"), None),
        (_Done(0, '{"selected": 3}'), None),
    ],
)
def test_preview_parses_the_last_json_line(
    monkeypatch: pytest.MonkeyPatch, done: _Done, expected: tuple[int, int, bool] | None
) -> None:
    monkeypatch.setattr(check.subprocess, "run", lambda *a, **k: done)
    result = check.testmon_preview()
    if expected is None:
        assert result is None
    else:
        assert result == check.TestmonPreview(*expected)
