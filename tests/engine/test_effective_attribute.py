"""Phase 2D-1 3.1／3.9 第 10 項：引擎內所有屬性判定都經過 ``effective_attribute``。"""

from __future__ import annotations

import ast
from pathlib import Path

from tests.engine.helpers import PROJECT_ROOT

ENGINE = PROJECT_ROOT / "src" / "trpg" / "engine"
STATUSES = ENGINE / "rules" / "statuses.py"
BASE_USERS = {
    ENGINE / "battle.py": {"begin_battle", "_initiative_order"},
    ENGINE / "skills" / "scaling.py": {"mastery_active"},
}
"""先攻（戰鬥開始時擲，用基礎屬性）與專精加成（Phase 2H-2：配點決定專精，不受戰鬥中增益影響）
是可以用 ``base_attribute`` 的地方。"""


def _functions_with_attribute_reads(path: Path) -> list[tuple[str, int]]:
    """``path`` 內直接讀 ``<x>.attributes[...]`` 的 (所在函式, 行號)。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[str, int]] = []

    def visit(node: ast.AST, owner: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = (
                child.name if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) else owner
            )
            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Attribute)
                and child.value.attr == "attributes"
            ):
                found.append((owner, child.lineno))
            visit(child, name)

    visit(tree, "<module>")
    return found


def test_only_effective_attribute_and_base_attribute_read_attributes_directly() -> None:
    offenders: list[str] = []
    for path in sorted(ENGINE.rglob("*.py")):
        for owner, line in _functions_with_attribute_reads(path):
            allowed = path == STATUSES and owner in {"effective_attribute", "base_attribute"}
            if not allowed:
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{line}（{owner}）")
    assert not offenders, "直接讀 .attributes[...]：" + "；".join(offenders)


def test_base_attribute_is_only_used_for_initiative() -> None:
    offenders: list[str] = []
    for path in sorted(ENGINE.rglob("*.py")):
        if path == STATUSES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed = BASE_USERS.get(path, set())

        def visit(
            node: ast.AST, owner: str, path: Path = path, allowed: set[str] = allowed
        ) -> None:
            for child in ast.iter_child_nodes(node):
                name = (
                    child.name
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                    else owner
                )
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == "base_attribute"
                    and owner not in allowed
                ):
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{child.lineno}（{owner}）")
                visit(child, name)

        visit(tree, "<module>")
    assert not offenders, "base_attribute 只供先攻使用：" + "；".join(offenders)
