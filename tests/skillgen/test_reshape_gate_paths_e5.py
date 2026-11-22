"""進戰鬥的規則包都經過預算閘門（E5，開發 PM 裁定 A 的條件 2）。

兩層鎖：

1. **結構**：``src/trpg`` 裡所有 ``Ruleset.with_skills(...)`` 都只能在
   :mod:`trpg.skillgen.reshape_gate` 裡呼叫（其他地方一律用 ``gated_with_skills``）；
   ``load_library(...)`` 不是包在 ``gate_library(...)`` 裡的，只能是下面列出理由的地方。
   新增一條開戰路徑時忘了接，這裡就會失敗。
2. **實際跑**：帶裝備授予的變形修正技的內容庫，經過內容庫載入（``load_checked_library``：CLI、數值
   工坊）、網頁伺服器（``create_app``：API 開戰、靶場、大世界、循環賽都用它的內容庫）、加 LLM 技能
   （``gated_with_skills``：roguelite、API 一輪、大世界遭遇、循環賽、工坊靶場、技能工坊試打）之後，
   表裡都查得到那個組合（含新加的技能）。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.engine.test_reshape_gate_e5 import BOUNCE, LINE, STRIKE, gear_library
from trpg.api import primitive_coverage
from trpg.api.app import create_app
from trpg.content.skills import SkillDef
from trpg.engine.reshape_gate import gate_key
from trpg.skillgen.reshape_gate import gated_with_skills

SRC = Path(__file__).resolve().parents[2] / "src" / "trpg"

WITH_SKILLS_ALLOWED = {"skillgen/reshape_gate.py"}
"""``Ruleset.with_skills`` 只能在這裡呼叫（``gated_with_skills`` 本身）。"""

LOAD_LIBRARY_ALLOWED = {
    "api/primitive_coverage.py": "load_checked_library：載入後 return gate_library(library)",
    "api/tuning/service.py": "_rules_library：只算預算，不開戰（工坊的模擬另外包 gate_library）",
    "skillgen/random_composer.py": "default_library：組合器產生技能用，不開戰",
}
"""``load_library`` 沒有直接包在 ``gate_library`` 裡的呼叫點與理由。"""


def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    found: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if called == name:
            found.append(node)
    return found


def _inside_gate(tree: ast.AST, call: ast.Call) -> bool:
    """``call`` 在某個 ``gate_library(...)`` 呼叫的參數裡。"""
    for node in _calls(tree, "gate_library"):
        if any(child is call for arg in node.args for child in ast.walk(arg)):
            return True
    return False


def _sources() -> list[tuple[str, ast.AST]]:
    out: list[tuple[str, ast.AST]] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel.startswith("content/"):  # 定義處（Ruleset.with_skills、load_library）
            continue
        out.append((rel, ast.parse(path.read_text(encoding="utf-8"))))
    return out


def test_every_with_skills_call_goes_through_the_gate() -> None:
    raw = [
        f"{rel}:{call.lineno}"
        for rel, tree in _sources()
        if rel not in WITH_SKILLS_ALLOWED
        for call in _calls(tree, "with_skills")
    ]
    assert raw == [], "請改用 trpg.skillgen.reshape_gate.gated_with_skills（E5 預算閘門）"


def test_every_load_library_call_is_gated_or_listed() -> None:
    raw = [
        f"{rel}:{call.lineno}"
        for rel, tree in _sources()
        if rel not in LOAD_LIBRARY_ALLOWED
        for call in _calls(tree, "load_library")
        if not _inside_gate(tree, call)
    ]
    assert raw == [], "請包 gate_library(...)，或在 LOAD_LIBRARY_ALLOWED 寫明不開戰的理由"


KEYS = (gate_key(BOUNCE, STRIKE), gate_key(LINE, "attack"))


def test_load_checked_library_fills_the_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI（``trpg battle``、``trpg run``…）與數值工坊寫回、驗證都用 ``load_checked_library``。"""
    raw = gear_library(gated=False)
    assert raw.ruleset.reshape_gates == {}
    monkeypatch.setattr(primitive_coverage, "load_library", lambda _dir=None: raw)
    gated = primitive_coverage.load_checked_library()
    assert all(k in gated.ruleset.reshape_gates for k in KEYS)


def test_web_server_library_is_gated(tmp_path: Path) -> None:
    """API 開戰、靶場、大世界遭遇與循環賽都從伺服器的內容庫建規則包。"""
    app = create_app(gear_library(gated=False), save_dir=tmp_path / "saves", prep_placement=False)
    for name in ("store", "runs", "world"):
        lib = app.state.store.library if name == "store" else getattr(app.state, name).library
        assert all(k in lib.ruleset.reshape_gates for k in KEYS), name


def test_llm_skills_added_later_are_gated() -> None:
    """LLM／組合器技能加進規則包之後，新技能也查得到（查不到就會變成「這招不能套用」）。"""
    lib = gear_library(gated=False)
    data = lib.ruleset.skill_def(STRIKE).model_dump(mode="json")
    generated = SkillDef.model_validate(dict(data, id="skill_llm_t_strike", name_zh="生成技"))
    ruleset = gated_with_skills(lib, [generated])
    assert gate_key(BOUNCE, generated.id) in ruleset.reshape_gates
    assert all(k in ruleset.reshape_gates for k in KEYS)
