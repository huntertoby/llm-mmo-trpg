"""架構守則檢查（import-linter 的保底，並額外檢查禁用的非確定性 API）。

以 ``ast`` 靜態掃描 ``src/trpg/``，不實際匯入模組：

1. 依賴方向（CLAUDE.md 守則 5）：
   - ``trpg.engine`` 不得匯入 llm、narrative、api、roguelite、sim、skillgen、cli。
   - ``trpg.shared`` 不得匯入任何其他 ``trpg`` 子套件。
   - ``trpg.narrative`` 不得匯入 cli、api、roguelite、sim（Phase 3-1：描述模組給 CLI 與網頁共用）。
   - ``trpg.api`` 不得匯入 ``trpg.cli``（Phase 3-2：CLI 可以匯入 api 來啟動伺服器，反之不行）。
   - ``trpg.content`` 不得匯入 ``trpg.skillgen``（Phase 2B-2 4.1：驗證器依賴內容資料，不能反過來）。
   - ``trpg.content`` 不得匯入 ``trpg.engine``（CODE-1 I4：engine 大量匯入 content，反向會成環）。
   - ``trpg.skillgen`` 不得匯入 ``trpg.llm``（Phase 4-L4：skillgen 不呼叫 LLM；大小估算放 shared）。
   - ``trpg.roguelite`` 不得匯入 api、cli、sim、llm、narrative（Phase 3-5a：只用 engine、content、
     skillgen）。
   - ``trpg.world`` 不得匯入 api、cli、sim、llm、narrative；engine、content、shared、roguelite、
     skillgen、narrative 不得匯入 ``trpg.world``（Phase 5A-2，``docs/phases/Phase5計畫.md`` 2.3）。
   - ``trpg.bot`` 只直接匯入 ``trpg.server`` 服務層與 ``trpg.shared``（5D-R2 起不再匯入
     ``trpg.api``）；engine、world、api、shared、content、roguelite、server 不得匯入 ``trpg.bot``
     （Phase 5E-2，計畫 29.2）。
   - ``trpg.server``（領域服務，5D-R2）不得匯入 api、cli、bot、sim、llm、narrative；engine、world、
     shared、content、roguelite、skillgen、narrative 不得匯入 ``trpg.server``。
   - 外部套件 ``discord``（discord.py）只能在 ``trpg.bot`` 匯入；``scripts/`` 只透過
     ``trpg.bot`` 用它（Phase 5E-2b，計畫 32.2）。
2. 確定性：``engine``、``shared``、``content``、``skillgen``、``sim``、``roguelite``、``world`` 內
   不得使用 ``random``、``secrets``、``uuid4``／``uuid1``、``os.urandom``、時間函式、內建 ``hash()``
   等。
3. 季末重置政策表（Phase 5D-R2，09 9.7、#91）：``trpg.server.season_policy`` 裡每個存檔模型的每個
   欄位都標了數值類或紀念類；新增欄位沒分類就失敗（這一條實際匯入模型）。5F-5：表裡每個模型都有
   季末重置的處理（``trpg.server.season_reset.HANDLERS``），處理方式和分類一致。
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
    "trpg.world",
    "trpg.bot",
    "trpg.server",
)

CONTENT_FORBIDDEN = ("trpg.skillgen", "trpg.engine", "trpg.world", "trpg.bot", "trpg.server")

NARRATIVE_FORBIDDEN = (
    "trpg.cli",
    "trpg.api",
    "trpg.roguelite",
    "trpg.sim",
    "trpg.world",
    "trpg.server",
)

API_FORBIDDEN = ("trpg.cli", "trpg.bot")

SKILLGEN_FORBIDDEN = ("trpg.llm", "trpg.world", "trpg.server")

ROGUELITE_FORBIDDEN = (
    "trpg.api",
    "trpg.cli",
    "trpg.sim",
    "trpg.llm",
    "trpg.narrative",
    "trpg.world",
    "trpg.bot",
    "trpg.server",
)

WORLD_FORBIDDEN = (
    "trpg.api",
    "trpg.cli",
    "trpg.sim",
    "trpg.llm",
    "trpg.narrative",
    "trpg.bot",
    "trpg.server",
)

SERVER_FORBIDDEN = ("trpg.api", "trpg.cli", "trpg.bot", "trpg.sim", "trpg.llm", "trpg.narrative")

BOT_FORBIDDEN = (
    "trpg.api",
    "trpg.world",
    "trpg.engine",
    "trpg.roguelite",
    "trpg.content",
    "trpg.skillgen",
    "trpg.sim",
    "trpg.llm",
    "trpg.narrative",
    "trpg.cli",
)

FORBIDDEN_BY_SOURCE: dict[str, tuple[str, ...]] = {
    "trpg.engine": ENGINE_FORBIDDEN,
    "trpg.content": CONTENT_FORBIDDEN,
    "trpg.narrative": NARRATIVE_FORBIDDEN,
    "trpg.api": API_FORBIDDEN,
    "trpg.roguelite": ROGUELITE_FORBIDDEN,
    "trpg.skillgen": SKILLGEN_FORBIDDEN,
    "trpg.world": WORLD_FORBIDDEN,
    "trpg.bot": BOT_FORBIDDEN,
    "trpg.server": SERVER_FORBIDDEN,
}

# 外部套件 → 唯一可以匯入它的 trpg 子套件（Phase 5E-2b：discord.py 只在 trpg.bot）。
EXTERNAL_ONLY_IN: dict[str, str] = {"discord": "trpg.bot"}
SCRIPTS_ROOT = SRC_ROOT.parent / "scripts"

DETERMINISTIC_PACKAGES = ("engine", "shared", "content", "skillgen", "sim", "roguelite", "world")

# 禁止呼叫的內建函式（字串的 ``hash()`` 每次執行不同，守則 2；Phase 5A-2 起）。
BANNED_BUILTIN_CALLS = frozenset({"hash"})

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
            out += _call_violations(node, where)
    return out


def _call_violations(node: ast.Call, where: str) -> list[Violation]:
    """禁止的呼叫：內建 ``hash()``、動態匯入 ``random``（``__import__``、``import_module``）。"""
    out: list[Violation] = []
    func = _dotted_name(node.func)
    if func in BANNED_BUILTIN_CALLS:
        out.append(Violation(where, f"禁止呼叫內建 {func}()"))
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
        for source, forbidden_list in FORBIDDEN_BY_SOURCE.items():
            if _is_within(current, source):
                out.extend(
                    Violation(where, f"{source} 不得匯入 {target}")
                    for forbidden in forbidden_list
                    if _is_within(target, forbidden)
                )
        if _is_within(current, "trpg.shared"):
            for sub in subpackages:
                if sub != "trpg.shared" and _is_within(target, sub):
                    out.append(Violation(where, f"trpg.shared 不得匯入 {target}"))
    return out


def external_import_violations(tree: ast.AST, current: str, location: str) -> list[Violation]:
    """外部套件只能在指定的子套件匯入（``current`` 是腳本時用 ``scripts.<名稱>``）。"""
    out: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [(node.lineno, node.module)]
        else:
            continue
        for lineno, name in names:
            top = name.split(".")[0]
            owner = EXTERNAL_ONLY_IN.get(top)
            if owner is not None and not _is_within(current, owner):
                out.append(Violation(f"{location}:{lineno}", f"{top} 只能在 {owner} 匯入"))
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
    for sub in ("roguelite", "api", "cli", "world"):
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


def test_external_packages_only_in_owner() -> None:
    violations: list[Violation] = []
    for path in _source_files():
        violations += external_import_violations(
            _parse(path), module_name_for(path), str(path.relative_to(SRC_ROOT))
        )
    for path in sorted(SCRIPTS_ROOT.rglob("*.py")):
        violations += external_import_violations(
            _parse(path), f"scripts.{path.stem}", str(path.relative_to(SCRIPTS_ROOT.parent))
        )
    assert not violations, "外部套件匯入違規：\n" + "\n".join(map(str, violations))


def test_scanner_detects_external_import_violations() -> None:
    bad = [
        ("trpg.api.app", "import discord"),
        ("trpg.world.step", "from discord import app_commands"),
        ("scripts.discord_bot", "import discord.ext.commands"),
    ]
    for current, source in bad:
        assert external_import_violations(ast.parse(source), current, "<snippet>"), source
    ok = [
        ("trpg.bot.discord_adapter", "import discord"),
        ("trpg.bot.discord_adapter", "from discord import app_commands"),
        ("trpg.api.app", "import discordant"),
        ("scripts.discord_bot", "from trpg.bot.discord_adapter import run_bot"),
    ]
    for current, source in ok:
        assert not external_import_violations(ast.parse(source), current, "<snippet>"), source


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
        "x = hash('abc')",
    ]
    for snippet in bad_snippets:
        assert _nd(snippet), f"應偵測到違規：{snippet!r}"


def test_scanner_allows_safe_code() -> None:
    ok_snippets = [
        "from trpg.shared.rng import Rng",
        "import time\ntime.sleep",  # 只引用 sleep 不算讀取時間
        "import datetime\ndatetime.timedelta(days=1)",
        "x = {'random': 1}",
        "class A:\n    def __hash__(self) -> int:\n        return 1",
        "from trpg.shared.rng import fnv1a64\nfnv1a64(b'x')",
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
        ("trpg.content.library", False, "from trpg.skillgen.validate import validate_skill"),
        ("trpg.content", True, "import trpg.skillgen"),
        ("trpg.content.skills", False, "from ..skillgen import budget"),
        ("trpg.narrative.events", False, "from trpg.cli.render import x"),
        ("trpg.narrative.skills", False, "import trpg.sim.matrix"),
        ("trpg.narrative", True, "from ..api import app"),
        ("trpg.api.app", False, "from trpg.cli.main import main"),
        ("trpg.api.routes.battles", False, "import trpg.cli.battle"),
        ("trpg.api", True, "from ..cli import render"),
        ("trpg.world.step", False, "from trpg.api.app import create_app"),
        ("trpg.world.step", False, "from trpg.narrative.events import describe_event"),
        ("trpg.world", True, "from ..llm import client"),
        ("trpg.world.clock", False, "import trpg.sim.matrix"),
        ("trpg.engine.grid", False, "from trpg.world.step import world_step"),
        ("trpg.content.library", False, "import trpg.world.state"),
        ("trpg.shared.rng", False, "from trpg.world import clock"),
        ("trpg.roguelite.progress", False, "from trpg.world.state import CharacterState"),
        ("trpg.skillgen.validate", False, "from ..world import step"),
        ("trpg.narrative.events", False, "from trpg.world.actions import TravelAction"),
        ("trpg.bot.service", False, "from trpg.world.save import write_atomic"),
        ("trpg.bot.service", False, "import trpg.engine.runner"),
        ("trpg.world.step", False, "from trpg.bot.service import BotService"),
        ("trpg.engine.grid", False, "import trpg.bot"),
        ("trpg.api.app", False, "from trpg.bot.config import load_bot_settings"),
        ("trpg.bot.service", False, "from trpg.api.app import create_app"),
        ("trpg.world.step", False, "from trpg.server.accounts import AccountStore"),
        ("trpg.engine.grid", False, "import trpg.server"),
        ("trpg.server.accounts", False, "from trpg.api.auth import require_account"),
        ("trpg.server.notes", False, "from trpg.bot.service import BotService"),
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
        ("trpg.skillgen.validate", False, "from trpg.content.library import ContentLibrary"),
        ("trpg.cli.budget", False, "from trpg.skillgen.validate import validate_skill"),
        ("trpg.narrative.events", False, "from trpg.engine.events import EventBase"),
        ("trpg.narrative.skills", False, "from trpg.content.library import ContentLibrary"),
        ("trpg.api.sessions", False, "from trpg.sim.lineup import build_allies"),
        ("trpg.api.app", False, "from trpg.narrative.events import describe_event"),
        ("trpg.cli.main", False, "from trpg.api.app import create_app"),
        ("trpg.world.step", False, "from trpg.roguelite.state import RunState"),
        ("trpg.world.step", False, "from trpg.engine.runner import LOG_FORMAT"),
        ("trpg.world.step", False, "from trpg.content.library import ContentLibrary"),
        ("trpg.api.world", False, "from trpg.world.step import world_step"),
        ("trpg.bot.service", False, "from trpg.server.accounts import AccountStore"),
        ("trpg.api.auth", False, "from trpg.server.accounts import AccountStore"),
        ("trpg.server.notes", False, "from trpg.world.state import CharacterState"),
        ("trpg.bot.service", False, "from trpg.shared.errors import TrpgError"),
    ]
    for current, is_package, source in cases:
        found = dependency_violations(ast.parse(source), current, is_package, "<snippet>")
        assert not found, f"不應判為依賴違規：{current}: {source!r} -> {found}"


# ---------------------------------------------------------------------------
# 玩家技能池（Phase 5F-3b）：只能經 trpg.content.player_pool.player_skills 取池
# ---------------------------------------------------------------------------

PLAYER_POOL_PACKAGES = ("skillgen", "llm", "roguelite", "world", "api")
"""玩家拿得到技能的套件（生成器、候選、閃現、工坊、LLM 提議、大世界、網頁）。"""

_LIBRARY_NAMES = frozenset({"library", "lib", "self.library", "self._library"})
_ITERATING_CALLS = frozenset({"sorted", "list", "tuple", "set", "frozenset", "iter", "enumerate"})

LIBRARY_SKILLS_ITERATION_ALLOWED: dict[tuple[str, str], str] = {
    ("trpg.llm.naming", "name_skill"): "避免撞名：比對所有內建技能名（含敵人專用）",
    ("trpg.llm.naming", "template_text"): "避免撞名：比對所有內建技能名（含敵人專用）",
    ("trpg.llm.flash_eval", "evaluate_flash"): "避免撞名：比對所有內建技能名",
    ("trpg.skillgen.proposal_coverage", "round_trip_inventory"): "開發工具：全部手寫技能的結構盤點",
    ("trpg.skillgen.library_check", "library_violations"): "內容檢查：全部內建技能（含敵人專用）"
    "的預算與結構（NW-1a 從 trpg.cli.budget 搬來）",
    ("trpg.api.world_presenter", "event_lines"): "技能 ID → 中文名對照（顯示用）",
    ("trpg.api.world_growth_view", "skill_names"): "技能 ID → 中文名對照（顯示用）",
}
"""（模組, 函式）→ 可以直接走訪 ``library.skills`` 的理由（不是玩家技能池）。"""


def _library_skills(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "skills"
        and _dotted_name(node.value) in _LIBRARY_NAMES
    )


def _iterated_nodes(tree: ast.AST) -> list[ast.AST]:
    """被走訪的運算式：``for``／推導式的來源、``sorted(...)`` 等的參數、``.values()`` 等的本體。"""
    found: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.comprehension)):
            found.append(node.iter)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _ITERATING_CALLS:
                found += node.args[:1]
            elif isinstance(func, ast.Attribute) and func.attr in ("values", "items", "keys"):
                found.append(func.value)
    return found


def player_pool_violations(tree: ast.AST, current: str, location: str) -> list[Violation]:
    """直接走訪 ``library.skills`` 的地方（沒在 :data:`LIBRARY_SKILLS_ITERATION_ALLOWED`）。"""
    violations: list[Violation] = []
    functions = [
        n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for function in functions:
        if (current, function.name) in LIBRARY_SKILLS_ITERATION_ALLOWED:
            continue
        for node in _iterated_nodes(function):
            if _library_skills(node):
                violations.append(
                    Violation(
                        f"{location}:{getattr(node, 'lineno', 0)}",
                        f"{function.name} 直接走訪 library.skills；玩家技能池請用 "
                        "trpg.content.player_pool.player_skills",
                    )
                )
    return sorted(set(violations), key=str)


def test_player_skill_pools_go_through_player_skills() -> None:
    """生成器、候選、閃現、工坊、LLM 提議等玩家技能池的入口都經過 ``player_skills``（排除
    ``enemy_only``），不直接走訪 ``library.skills``（5F-3b）。"""
    violations: list[Violation] = []
    for path in _source_files():
        current = module_name_for(path)
        if not any(_is_within(current, f"trpg.{p}") for p in PLAYER_POOL_PACKAGES):
            continue
        violations += player_pool_violations(_parse(path), current, str(path.relative_to(SRC_ROOT)))
    assert not violations, "\n".join(str(v) for v in violations)


def test_scanner_detects_library_skills_iteration() -> None:
    bad = (
        "def f(library):\n    return [s for s in sorted(library.skills)]\n",
        "def f(library):\n    return list(library.skills.values())\n",
        "def f(self):\n    for k, s in self.library.skills.items():\n        pass\n",
        "def f(lib):\n    for k in lib.skills:\n        pass\n",
    )
    for source in bad:
        assert player_pool_violations(ast.parse(source), "trpg.skillgen.x", "<snippet>"), source
    good = (
        "def f(library, k):\n    return library.skills.get(k)\n",
        "def f(library, k):\n    return k in library.skills\n",
        "def f(library):\n    return list(player_skills(library).values())\n",
        "def f(hero):\n    return sorted(hero.skills)\n",
    )
    for source in good:
        assert not player_pool_violations(ast.parse(source), "trpg.skillgen.x", "<snippet>"), source


def test_every_saved_field_has_a_season_reset_kind() -> None:
    """季末重置政策表（5D-R2）：表裡每個模型的欄位剛好都分類（新增欄位沒分類、刪掉的欄位還在表裡
    都失敗）；分類只有數值類／紀念類；拿不準的欄位都標數值類。"""
    from trpg.server.accounts import AccountRecord  # noqa: PLC0415 — 只有這條檢查要匯入模型
    from trpg.server.first_kills import FirstKill  # noqa: PLC0415
    from trpg.server.notes import LocationNote  # noqa: PLC0415
    from trpg.server.season_policy import (  # noqa: PLC0415
        NUMERIC,
        PROVISIONAL,
        SEASON_POLICY,
    )
    from trpg.world.state import CharacterState, RecipeRecord, WorldState  # noqa: PLC0415

    required = {CharacterState, WorldState, RecipeRecord, FirstKill, AccountRecord, LocationNote}
    assert required <= set(SEASON_POLICY), "存檔模型沒有列進季末重置政策表"
    problems: list[str] = []
    for model, policy in SEASON_POLICY.items():
        fields = set(model.model_fields)
        problems += [
            f"{model.__name__}.{name}：沒有分類（數值類或紀念類）"
            for name in sorted(fields - set(policy))
        ]
        problems += [
            f"{model.__name__}.{name}：表裡有、模型沒有" for name in sorted(set(policy) - fields)
        ]
        problems += [
            f"{model.__name__}.{name}：分類 {kind!r} 不認得"
            for name, kind in sorted(policy.items())
            if kind not in {"numeric", "memorial"}
        ]
    names = {m.__name__: m for m in SEASON_POLICY}
    for model_name, field in sorted(PROVISIONAL):
        found = names.get(model_name)
        if found is None or SEASON_POLICY[found].get(field) != NUMERIC:
            problems.append(f"{model_name}.{field}：待決的欄位要暫標數值類")
    assert not problems, "季末重置政策表：\n" + "\n".join(problems)


def _expected_handlers(numeric: tuple[str, ...], memorial: tuple[str, ...]) -> set[str]:
    if not memorial:
        return {"replace", "delete"}
    if not numeric:
        return {"keep"}
    return {"split"}


def test_season_reset_handles_every_policy_model() -> None:
    """季末重置（5F-5）：政策表裡每個模型都有重置處理，處理方式和分類一致（整個數值類＝刪掉或換新、
    整個紀念類＝不動、混合＝分開且紀念類欄位都有去處）；``CARRIED`` 的每一項都有處理函式。
    不能只分類卻不清（實際清掉的行為由 ``tests/server/test_season_reset.py`` 逐欄位檢查）。"""
    from trpg.server.season_policy import (  # noqa: PLC0415
        CARRIED,
        MEMORIAL,
        NUMERIC,
        SEASON_POLICY,
        fields_of_kind,
    )
    from trpg.server.season_reset import (  # noqa: PLC0415
        CARRIED_HANDLERS,
        HANDLERS,
        SPLIT_CARRIERS,
    )

    problems = [f"{m.__name__}：政策表有、重置沒有處理" for m in set(SEASON_POLICY) - set(HANDLERS)]
    problems += [f"{m.__name__}：重置有處理、表裡沒有" for m in set(HANDLERS) - set(SEASON_POLICY)]
    for model, (kind, _) in HANDLERS.items():
        if model not in SEASON_POLICY:
            continue
        memorial = fields_of_kind(model, MEMORIAL)
        expected = _expected_handlers(fields_of_kind(model, NUMERIC), memorial)
        if kind not in expected:
            problems.append(
                f"{model.__name__}：處理 {kind!r} 和分類不符（應為 {sorted(expected)}）"
            )
        carrier = SPLIT_CARRIERS.get(model)
        if kind == "split" and carrier is None:
            problems.append(f"{model.__name__}：分開處理但沒有留下紀念類欄位的模型")
        if kind == "split" and carrier is not None:
            lost = sorted(set(memorial) - set(carrier.model_fields))
            problems += [f"{model.__name__}.{n}：紀念類欄位沒有去處" for n in lost]
    names = {m.__name__: m for m in SEASON_POLICY}
    for model_name, field in sorted(CARRIED):
        found = names.get(model_name)
        if found is None or SEASON_POLICY[found].get(field) != NUMERIC:
            problems.append(f"{model_name}.{field}：CARRIED 的欄位要是數值類")
    problems += [f"{m}.{f}：CARRIED 沒有處理函式" for m, f in set(CARRIED) - set(CARRIED_HANDLERS)]
    problems += [f"{m}.{f}：處理函式不在 CARRIED" for m, f in set(CARRIED_HANDLERS) - set(CARRIED)]
    assert not problems, "季末重置：\n" + "\n".join(sorted(problems))
