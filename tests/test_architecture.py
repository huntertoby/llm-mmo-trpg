"""架構守則檢查（import-linter 的保底，並額外檢查禁用的非確定性 API）。

以 ``ast`` 靜態掃描 ``src/trpg/``，不實際匯入模組：

1. 依賴方向（CLAUDE.md 守則 5）：
   - ``trpg.engine`` 不得匯入 llm、narrative、api、roguelite、sim、skillgen、cli。
   - ``trpg.shared`` 不得匯入任何其他 ``trpg`` 子套件。
2. 確定性：``engine``、``shared``、``content``、``skillgen``、``sim``、``roguelite`` 內
   不得使用 ``random``、``secrets``、``uuid4``／``uuid1``、``os.urandom``、時間函式等。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
PACKAGE_ROOT = SRC_ROOT / "trpg"

ENGINE_FORBIDDEN = (
    "trpg.llm",
    "trpg.narrative",
    "trpg.api",
    "trpg.roguelite",
    "trpg.sim",
    "trpg.skillgen",
    "trpg.cli",
)

DETERMINISTIC_PACKAGES = ("engine", "shared", "content", "skillgen", "sim", "roguelite")

# 整個模組禁止匯入。
BANNED_MODULES = ("random", "secrets")

# 禁止的「模組 → 名稱」（from X import Y）。
BANNED_FROM_IMPORTS: dict[str, frozenset[str]] = {
    "time": frozenset(
        {"time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns"}
    ),
    "uuid": frozenset({"uuid1", "uuid4"}),
    "os": frozenset({"urandom"}),
}

# 禁止的屬性存取（以點分名稱的結尾比對，例如 ``datetime.datetime.now`` 也會符合 ``datetime.now``）。
BANNED_ATTRIBUTES = (
    "time.time",
    "time.time_ns",
    "time.monotonic",
    "time.monotonic_ns",
    "time.perf_counter",
    "time.perf_counter_ns",
    "datetime.now",
    "datetime.utcnow",
    "datetime.today",
    "date.today",
    "uuid.uuid1",
    "uuid.uuid4",
    "os.urandom",
)


@dataclass(frozen=True)
class Violation:
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


def module_name_for(path: Path) -> str:
    """把 ``src/trpg/a/b.py`` 轉成 ``trpg.a.b``（``__init__.py`` 對應套件本身）。"""
    rel = path.relative_to(SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_relative(module: str | None, level: int, current: str, is_package: bool) -> str:
    if level == 0:
        return module or ""
    base = current.split(".")
    if not is_package:
        base = base[:-1]
    if level > 1:
        base = base[: len(base) - (level - 1)]
    if module:
        base = [*base, module]
    return ".".join(base)


def imported_modules(tree: ast.AST, current: str, is_package: bool) -> list[tuple[int, str]]:
    """回傳 (行號, 被匯入的模組完整名稱)。``from pkg import sub`` 也會列出 ``pkg.sub``。"""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(node.module, node.level, current, is_package)
            found.append((node.lineno, base))
            found.extend((node.lineno, f"{base}.{alias.name}") for alias in node.names)
    return found


def _is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = _dotted_name(node.value)
        return None if inner is None else f"{inner}.{node.attr}"
    return None


def nondeterminism_violations(tree: ast.AST, location: str) -> list[Violation]:
    """找出禁用的非確定性 API 使用。"""
    out: list[Violation] = []
    for node in ast.walk(tree):
        where = f"{location}:{getattr(node, 'lineno', 0)}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in BANNED_MODULES:
                    out.append(Violation(where, f"禁止匯入 {alias.name}"))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            top = node.module.split(".")[0]
            if top in BANNED_MODULES:
                out.append(Violation(where, f"禁止 from {node.module} import ..."))
            banned_names = BANNED_FROM_IMPORTS.get(node.module, frozenset())
            out.extend(
                Violation(where, f"禁止 from {node.module} import {alias.name}")
                for alias in node.names
                if alias.name in banned_names
            )
        elif isinstance(node, ast.Attribute):
            dotted = _dotted_name(node)
            if dotted is not None:
                for banned in BANNED_ATTRIBUTES:
                    if dotted == banned or dotted.endswith("." + banned):
                        out.append(Violation(where, f"禁止使用 {dotted}"))
                        break
        elif isinstance(node, ast.Call):
            # __import__("random")、importlib.import_module("random")
            func = _dotted_name(node.func)
            if (
                func in {"__import__", "importlib.import_module", "import_module"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.split(".")[0] in BANNED_MODULES
            ):
                out.append(Violation(where, f"禁止動態匯入 {node.args[0].value}"))
    return out


def dependency_violations(
    tree: ast.AST, current: str, is_package: bool, location: str
) -> list[Violation]:
    """檢查 engine 與 shared 的依賴方向。"""
    out: list[Violation] = []
    subpackages = sorted(
        f"trpg.{p.name}" for p in PACKAGE_ROOT.iterdir() if (p / "__init__.py").is_file()
    )
    for lineno, target in imported_modules(tree, current, is_package):
        where = f"{location}:{lineno}"
        if _is_within(current, "trpg.engine"):
            for forbidden in ENGINE_FORBIDDEN:
                if _is_within(target, forbidden):
                    out.append(Violation(where, f"trpg.engine 不得匯入 {target}"))
        if _is_within(current, "trpg.shared"):
            for sub in subpackages:
                if sub != "trpg.shared" and _is_within(target, sub):
                    out.append(Violation(where, f"trpg.shared 不得匯入 {target}"))
    return out


def _source_files() -> list[Path]:
    return sorted(PACKAGE_ROOT.rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ---------------------------------------------------------------------------
# 實際專案的檢查
# ---------------------------------------------------------------------------


def test_source_tree_is_found() -> None:
    files = _source_files()
    assert files, "找不到 src/trpg 下的原始碼"
    modules = {module_name_for(p) for p in files}
    for sub in ("shared", "engine", "content", "skillgen", "sim", "llm", "narrative"):
        assert f"trpg.{sub}" in modules
    for sub in ("roguelite", "api", "cli"):
        assert f"trpg.{sub}" in modules


def test_dependency_direction() -> None:
    violations: list[Violation] = []
    for path in _source_files():
        current = module_name_for(path)
        tree = _parse(path)
        violations += dependency_violations(
            tree, current, path.name == "__init__.py", str(path.relative_to(SRC_ROOT))
        )
    assert not violations, "依賴方向違規：\n" + "\n".join(map(str, violations))


def test_no_nondeterministic_apis_in_deterministic_packages() -> None:
    violations: list[Violation] = []
    for package in DETERMINISTIC_PACKAGES:
        for path in sorted((PACKAGE_ROOT / package).rglob("*.py")):
            violations += nondeterminism_violations(_parse(path), str(path.relative_to(SRC_ROOT)))
    assert not violations, "確定性違規：\n" + "\n".join(map(str, violations))


# ---------------------------------------------------------------------------
# 掃描器本身的自我測試（確保上面的檢查不是空轉）
# ---------------------------------------------------------------------------


def _nd(source: str) -> list[Violation]:
    return nondeterminism_violations(ast.parse(source), "<snippet>")


def test_scanner_detects_banned_imports_and_calls() -> None:
    bad_snippets = [
        "import random",
        "import random as r",
        "from random import randint",
        "import secrets",
        "from uuid import uuid4",
        "import uuid\nuuid.uuid4()",
        "import time\ntime.time()",
        "import time\ntime.perf_counter()",
        "from time import monotonic",
        "import datetime\ndatetime.datetime.now()",
        "from datetime import datetime\ndatetime.utcnow()",
        "from datetime import date\ndate.today()",
        "import os\nos.urandom(4)",
        "__import__('random')",
        "import importlib\nimportlib.import_module('random')",
    ]
    for snippet in bad_snippets:
        assert _nd(snippet), f"應偵測到違規：{snippet!r}"


def test_scanner_allows_safe_code() -> None:
    ok_snippets = [
        "from trpg.shared.rng import Rng",
        "import time\ntime.sleep",  # 只引用 sleep 不算讀取時間
        "import datetime\ndatetime.timedelta(days=1)",
        "x = {'random': 1}",
    ]
    for snippet in ok_snippets:
        assert not _nd(snippet), f"不應判為違規：{snippet!r}"


def test_scanner_detects_dependency_violations() -> None:
    cases = [
        ("trpg.engine.grid", False, "from trpg.llm import client"),
        ("trpg.engine.grid", False, "import trpg.cli.main"),
        ("trpg.engine", True, "from trpg import narrative"),
        ("trpg.engine.grid", False, "from ..sim import runner"),
        ("trpg.shared.rng", False, "from trpg.engine import x"),
        ("trpg.shared.rng", False, "from trpg.content.loader import load_content_file"),
        ("trpg.shared", True, "from ..cli import main"),
    ]
    for current, is_package, source in cases:
        found = dependency_violations(ast.parse(source), current, is_package, "<snippet>")
        assert found, f"應偵測到依賴違規：{current}: {source!r}"


def test_scanner_allows_legal_dependencies() -> None:
    cases = [
        ("trpg.engine.grid", False, "from trpg.shared.rng import Rng"),
        ("trpg.engine.grid", False, "from trpg.content.schemas import ElementTable"),
        ("trpg.shared.types", False, "from trpg.shared.errors import TrpgError"),
        ("trpg.shared.types", False, "from .errors import TrpgError"),
        ("trpg.cli.main", False, "from trpg.llm import client"),
    ]
    for current, is_package, source in cases:
        found = dependency_violations(ast.parse(source), current, is_package, "<snippet>")
        assert not found, f"不應判為依賴違規：{current}: {source!r} -> {found}"
