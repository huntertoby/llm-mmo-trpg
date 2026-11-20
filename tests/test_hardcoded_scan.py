"""寫死數值的涵蓋檢查（HC-1；``docs/phases/PhaseHC-1計畫.md`` 第 4 項）。

``scripts/hardcoded/scan_py.py``（``src/trpg/``）和 ``scan_ts.py``（``client/src/``）列出的每一個
數字字面值、含數字的中文字串，都要被 ``scripts/hardcoded/classes.yaml`` 的某一條規則歸類
（config／scale／const／text／layout／guard）。新寫的數字沒有規則時這裡失敗：先決定它是玩法數值（搬進
content 或工坊設定）、量類、真的常數、說明文字、排版還是 schema 的護欄，再寫進歸類檔。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_DIR = Path(__file__).resolve().parents[1] / "scripts" / "hardcoded"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"hardcoded_{name}", _DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cl = _load("classify")
scan_py = _load("scan_py")
scan_ts = _load("scan_ts")


@pytest.fixture(scope="module")
def result() -> Any:
    return cl.classify()


def test_every_hardcoded_number_is_classified(result: Any) -> None:
    assert not result.unclassified, cl.unclassified_message(result)


def test_todo_classes_and_status(result: Any) -> None:
    """const／layout／guard 不用搬（done）；config／scale／text 的 status 是 todo 或 done。"""
    for rule in result.classes.rules:
        if rule.cls in ("const", "layout", "guard"):
            assert rule.status == "done", rule.id
        else:
            assert rule.status in ("todo", "done"), rule.id


def _class_of(result: Any, file: str, predicate: Any) -> set[str]:
    return {rule.cls for hit, rule in result.assigned if hit.file == file and predicate(hit)}


@pytest.mark.parametrize(
    ("file", "owner", "expected"),
    [
        ("src/trpg/content/forms.py", "upkeep_mana", "scale"),
        ("src/trpg/content/battle.py", "MAX_ATTRIBUTE", "guard"),
        ("src/trpg/content/battle.py", "_MAX_DICE_COUNT", "guard"),
        ("src/trpg/content/skill_pick.py", "max_elements_dual", "config"),
        ("src/trpg/content/composer_rules.py", "ap_cost", "config"),
        ("src/trpg/skillgen/flash_ops.py", "RELAX_PERMILLE", "config"),
        ("src/trpg/content/rules.py", "_PERMILLE", "const"),
    ],
)
def test_backend_spot_checks(result: Any, file: str, owner: str, expected: str) -> None:
    found = _class_of(result, file, lambda hit: hit.owner == owner and hit.kind == "number")
    assert found == {expected}, (file, owner, found)


@pytest.mark.parametrize(
    ("file", "needle", "expected"),
    [
        ("client/src/run/flow.ts", "SLOT_LIMITS", "config"),
        ("client/src/run/flash.ts", "const FALLBACK", "config"),
    ],
)
def test_frontend_spot_checks(result: Any, file: str, needle: str, expected: str) -> None:
    found = _class_of(result, file, lambda hit: needle in hit.context and hit.kind == "number")
    assert found == {expected}, (file, needle, found)


# ---------------------------------------------------------------------- 掃描器
_PY_SAMPLE = '''
"""模組說明：最多 3 招。"""
LIMIT = 5
OFF = -2
FLAGS = (0, 1, -1, True)


def f(x: int = 7) -> str:
    for _ in range(4):
        pass
    if x > 12:
        return f"每回合 {x} 次，最多 2 招"
    return "沒有數字的中文"
'''


def test_scan_py_lists_literals_and_cjk_strings() -> None:
    hits = scan_py.scan_source("src/trpg/x.py", _PY_SAMPLE)
    numbers = {(h.value, h.slot, h.scope) for h in hits if h.kind == "number"}
    assert numbers == {
        ("5", "=LIMIT", "<module>"),
        ("-2", "=OFF", "<module>"),
        ("7", "def:x", "f"),
        ("12", "cmp:x", "f"),
    }
    texts = {(h.kind, h.value) for h in hits if h.kind != "number"}
    assert texts == {("docstring", "模組說明：最多 3 招。"), ("text", "每回合 {x} 次，最多 2 招")}


_TS_SAMPLE = """
const SIZE = { width: 12, limit: 3 };
const label = "最多 2 個";
const re = /a\\d{2}/;
function Card({ n }: { n: number }) {
  const t = `第 ${n} 段，共 4 段`;
  return <div title="12px">剩 3 回合</div>;
}
const neg = -5, skip = [0, 1, -1];
"""


def test_scan_ts_lists_literals_jsx_and_templates() -> None:
    hits = scan_ts.scan_source("client/src/x.tsx", _TS_SAMPLE)
    numbers = sorted((h.value, h.slot) for h in hits if h.kind == "number")
    assert numbers == [("-5", "=neg"), ("12", "{width}"), ("3", "{limit}")]
    texts = {h.value for h in hits if h.kind == "text"}
    assert texts == {"最多 2 個", "第 ${n} 段，共 4 段", "剩 3 回合"}
    jsx = next(h for h in hits if h.value == "剩 3 回合")
    assert jsx.scope == "Card"


# ---------------------------------------------------------------------- 歸類檔的寫法
def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "classes.yaml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "rule",
    [
        "{id: a, class: nope, status: todo}",
        "{id: a, class: const, status: todo}",
        "{id: a, class: guard, status: todo}",
        "{id: a, class: config, status: later}",
        "{id: a, class: config, status: todo, colour: red}",
        "{class: config, status: todo}",
        "{id: a, class: config, status: todo, text: '('}",
        "{id: a, class: config, status: todo, not: {}}",
    ],
)
def test_bad_rules_are_rejected(tmp_path: Path, rule: str) -> None:
    with pytest.raises(cl.ClassesError):
        cl.load_classes(_write(tmp_path, f"rules:\n  - {rule}\n"))


def test_duplicate_rule_ids_are_rejected(tmp_path: Path) -> None:
    rule = "  - {id: a, class: const, status: done}\n"
    text = "rules:\n" + rule + rule
    with pytest.raises(cl.ClassesError):
        cl.load_classes(_write(tmp_path, text))


def test_first_matching_rule_wins_and_not_excludes(tmp_path: Path) -> None:
    text = """
rules:
  - {id: hp, class: scale, status: todo, owner: '*hp*', not: {owner: '*permille*'}}
  - {id: rest, class: config, status: todo, kind: number}
"""
    classes = cl.load_classes(_write(tmp_path, text))
    hits = scan_py.scan_source("src/trpg/x.py", "max_hp = 40\nhp_permille = 500\n")
    assert [classes.classify(h).id for h in hits] == ["hp", "rest"]


def test_unclassified_message_explains_how_to_fix(tmp_path: Path) -> None:
    classes = cl.load_classes(_write(tmp_path, "rules: []\n"))
    hits = scan_py.scan_source("src/trpg/x.py", "LIMIT = 5\n")
    message = cl.unclassified_message(cl.classify(hits, classes))
    assert "classes.yaml" in message
    assert "src/trpg/x.py:1" in message
    assert "value: ['5']" in message
