"""本機完整檢查：ruff、格式、mypy、import-linter、pytest 依序執行。

通常用法（Windows、macOS、Linux 皆同）::

    uv run python scripts/check.py          # 快速版，依改動路徑分流（TS-1，見下）
    uv run python scripts/check.py --all    # 快速版，不分流、全部步驟都跑
    uv run python scripts/check.py --full   # 完整版（pytest -m ""、TRPG_FULL=1），不分流
    uv run python scripts/check.py --testmon  # 試用（TS-2）：只跑後端時由 testmon 選測試，不寫戳記

分流（TS-1）：比對 ``origin/main``（``TRPG_CHECK_BASE`` 可改）的 merge-base 到工作區的改動。
只動 ``client/`` 時只跑前端的 install、typecheck、test、build，加上會讀 ``client/`` 檔案的 pytest；
只動 ``src/``、``tests/``、``scripts/`` 時略過前端三步；動到 ``content/``、``config/``、
API schema（``client/openapi.json``、``client/src/api/schema.d.ts``）、``pyproject.toml``、
``uv.lock``、``package.json``、lockfile、本腳本，或判斷不出來時全跑。``*.md`` 不影響分流。
一開頭印一行說明這次跑哪些、略過哪些、為什麼。規則細節見 ``docs/dev/上手-測試.md``。

pytest 平行數預設 12（QF-3a 從 8 調高），可用環境變數 ``TRPG_PYTEST_WORKERS`` 覆寫
（數字或 ``auto``）。
單一測試預設逾時 300 秒（標 slow 的 1800 秒），見 ``pyproject.toml`` 的 ``timeout``。
pytest 經看門狗 ``scripts/run_pytest.py`` 執行（QF-3a）：超過 10 分鐘沒有測試跑完就用 PID 結束
自己開的整棵程序樹、重跑一次，再卡住判失敗並寫出卡在哪個測試（``TRPG_PYTEST_STALL_MINUTES`` 可改）。

多個 agent 同時工作時：每個 agent 在自己的 worktree 執行本腳本（不要共用同一個 checkout），
並設 ``UV_NO_SYNC=1``（或用 ``uv run --frozen``）避免 ``uv run`` 自動同步、重裝套件。
跑 pytest 前會清掉 ``tests/**/__pycache__`` 中多個行程同時寫入留下的 ``*.pyc.<pid>`` 暫存檔。

每個步驟都會執行（方便一次看到全部問題），最後印出各步驟結果摘要；
任一步失敗時以非零代碼結束。``warn_only`` 的步驟（6Q-A 情境覆蓋表）非零時只標「警告」，
不影響結束碼。``lint-imports`` 未安裝時只印出警告並略過，不算失敗
（``tests/test_architecture.py`` 提供等效的依賴方向檢查）。前端檢查（``pnpm -C client``
的 ``install --frozen-lockfile``、``typecheck``、``test``）在找不到 pnpm 時同樣略過
（尋找順序 ``corepack`` → ``pnpm`` → ``npx``，見 ``trpg.cli.frontend.pnpm_command``；MAC-1）。

全部步驟通過（沒有失敗、也沒有略過）且追蹤中的檔案沒有未 commit 的修改時，在
``<git common dir>/pm-check-pass/<HEAD 的 tree hash>`` 寫一個戳記（QF-5）。push hook 看到要推的
內容已有戳記，就不再重跑本腳本；合併後內容有任何不同（tree hash 變了）就照常重跑。
分流跑（有步驟被略過）改寫在 ``pm-check-pass-split/<tree hash>``（內容記 commit、範圍、基準），
hook 不看這個位置，所以分流跑不會讓 hook 略過完整檢查（TS-1）。

試用 testmon（TS-2）：加 ``--testmon`` 時，只有分流結果是「只跑後端」、而且後端改動都是
``.py`` 才用 ``pytest-testmon`` 選測試（``--testmon-forceselect``，和 ``-m`` 一起篩）；其他範圍照
上面的分流、不用 testmon。開頭那一行會寫選了幾個、略過幾個（``scripts/testmon_select.py`` 先只收集
算出來）。testmon 選過的跑法**不寫任何通過戳記**。試用中，不能取代交件前的 ``--all``。

工具的尋找順序：目前 Python 環境的模組（``sys.executable -m <tool>``）→
與 ``sys.executable`` 同一資料夾的執行檔 → ``PATH`` 上的執行檔（``shutil.which``）。
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from trpg.cli.frontend import pnpm_command

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WATCHDOG_SCRIPT = "scripts/run_pytest.py"


AREA_BACKEND = "backend"
AREA_CLIENT = "client"


@dataclass(frozen=True)
class Step:
    title: str
    module: str | None  # 可用 ``python -m`` 執行的模組名稱
    executable: str  # 對應的指令名稱
    args: tuple[str, ...]
    optional: bool = False
    script: str | None = None  # 用 ``sys.executable <PROJECT_ROOT/script>`` 執行的腳本
    warn_only: bool = False  # 非零時只算「警告」，不影響結束碼
    area: str = AREA_BACKEND  # TS-1 分流：這一步屬於後端還是前端


def pytest_workers() -> str:
    """pytest 的平行數：環境變數 ``TRPG_PYTEST_WORKERS``（數字或 ``auto``），預設 12。"""
    value = os.environ.get("TRPG_PYTEST_WORKERS", "").strip() or "12"
    if value != "auto" and not (value.isdigit() and int(value) >= 0):
        raise SystemExit(f"TRPG_PYTEST_WORKERS 必須是非負整數或 auto，收到：{value!r}")
    return value


def _client_step(title: str, *args: str) -> Step:
    """``pnpm -C client <args>``；找不到 pnpm（corepack／pnpm／npx 皆無）時略過（不算失敗）。"""
    return Step(title, None, "pnpm", ("-C", "client", *args), optional=True, area=AREA_CLIENT)


STEPS: tuple[Step, ...] = (
    Step("ruff check", "ruff", "ruff", ("check", ".")),
    Step("ruff format --check", "ruff", "ruff", ("format", "--check", ".")),
    Step("mypy", "mypy", "mypy", ()),
    Step("lint-imports", None, "lint-imports", (), optional=True),
    # QF-3a：經看門狗 scripts/run_pytest.py 跑（卡住時只結束自己的程序樹、重跑一次）。
    Step("pytest", None, "pytest", ("-q", "-n", pytest_workers()), script=WATCHDOG_SCRIPT),
    # 前端（Phase 3-3）：找不到 pnpm（沒有安裝 Node）時印出警告並略過，不算失敗。
    _client_step("client install", "install", "--frozen-lockfile"),
    _client_step("client typecheck", "typecheck"),
    _client_step("client test", "test"),
    # 6Q-A：情境覆蓋表（只讀內容）；有被標出的項目時結束碼 3，這裡只算警告。
    Step(
        "situation coverage",
        None,
        "python",
        ("--quiet", "--warn-exit"),
        script="scripts/situation_coverage.py",
        warn_only=True,
    ),
)

# --- TS-1：依改動路徑分流 ----------------------------------------------------------------

SCOPE_ALL = "all"  # 全跑（等於 TS-1 以前不加參數的行為）
SCOPE_BACKEND = "backend"  # 只跑後端：略過前端的 install／typecheck／test
SCOPE_CLIENT = "client"  # 只跑前端：install／typecheck／test／build，加上讀 client/ 的 pytest

BASE_REF = "origin/main"
BASE_ENV = "TRPG_CHECK_BASE"  # 改比對基準（例如驗收時用 HEAD）；預設 origin/main
CLIENT_BUILD = _client_step("client build", "build")  # 只在「只跑前端」時加（全跑時 hook 另跑建置）
CLIENT_PYTEST_TITLE = "pytest（讀 client/ 的測試）"

# 動到就全跑的檔案與資料夾（TS-1 規格第 1 項）。
ALL_DIRS = ("content/", "config/")
ALL_FILES = frozenset(
    {
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        "scripts/check.py",
        "client/openapi.json",  # API schema：後端 OpenAPI 的快照
        "client/src/api/schema.d.ts",  # API schema：由 openapi.json 產生的前端型別
    }
)
ALL_BASENAMES = frozenset(
    {"package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "package-lock.json", "yarn.lock"}
)
BACKEND_DIRS = ("src/", "tests/", "scripts/")
CLIENT_DIR = "client/"


@dataclass(frozen=True)
class Plan:
    """這次要跑的範圍。``base`` 是比對的基準（merge-base 的 commit；判斷不出來時 None）。"""

    scope: str
    reason: str
    base: str | None = None
    changed: int = 0
    paths: tuple[str, ...] = ()  # 改動的檔（TS-2：判斷 testmon 追不追得到）


def _path_area(path: str) -> str | None:
    """改動的檔案屬於哪一區（``all``／``backend``／``client``）；``None``＝不影響（``*.md``）。"""
    if path.startswith(ALL_DIRS) or path in ALL_FILES or path.rsplit("/", 1)[-1] in ALL_BASENAMES:
        return SCOPE_ALL
    if path.endswith(".md"):
        return None
    if path.startswith(CLIENT_DIR):
        return SCOPE_CLIENT
    if path.startswith(BACKEND_DIRS):
        return SCOPE_BACKEND
    return SCOPE_ALL  # 不認得的位置（docs/ 的圖檔、.claude/、.github/ 等）：判斷不出來就全跑


def base_ref() -> str:
    """比對基準：環境變數 ``TRPG_CHECK_BASE``，沒設時 ``origin/main``。"""
    return os.environ.get(BASE_ENV, "").strip() or BASE_REF


def plan_scope(changed: list[str] | None, base: str | None) -> Plan:
    """依改動清單決定範圍；清單是 None（git 失敗、沒有基準）時全跑。"""
    if changed is None or base is None:
        return Plan(SCOPE_ALL, f"找不到 {base_ref()} 或 git 失敗，判斷不出改動範圍")
    count = len(changed)
    paths = tuple(sorted(changed))
    areas: dict[str, list[str]] = {}
    for path in sorted(changed):
        area = _path_area(path)
        if area is not None:
            areas.setdefault(area, []).append(path)
    if SCOPE_ALL in areas:
        first = areas[SCOPE_ALL][0]
        more = f" 等 {len(areas[SCOPE_ALL])} 個" if len(areas[SCOPE_ALL]) > 1 else ""
        return Plan(
            SCOPE_ALL, f"動到 {first}{more}（內容、設定、相依、API schema 或本腳本）", base, count
        )
    if not areas:
        return Plan(
            SCOPE_ALL, "沒有程式、測試或資料的改動（只有 .md 或沒有改動），照舊全跑", base, count
        )
    if set(areas) == {SCOPE_CLIENT}:
        reason = "只動 client/（沒動 package.json、lockfile、API schema）"
        return Plan(SCOPE_CLIENT, reason, base, count)
    if set(areas) == {SCOPE_BACKEND}:
        reason = "只動 src/、tests/、scripts/，沒動 client/ 與 API schema 快照"
        return Plan(SCOPE_BACKEND, reason, base, count, paths)
    return Plan(SCOPE_ALL, "前端與後端都有改動", base, count)


def changed_paths() -> tuple[list[str] | None, str | None]:
    """相對 :func:`base_ref` 的 merge-base 的改動與基準 commit。

    改動＝已 commit＋還沒 commit＋未追蹤的檔（``--no-renames``：改名的新舊路徑都算）。
    任何一步 git 失敗時回傳 ``(None, None)``（呼叫端會全跑）。"""
    base = _git("merge-base", "HEAD", base_ref())
    if not base:
        return None, None
    diff = _git("-c", "core.quotePath=false", "diff", "--name-only", "--no-renames", base)
    untracked = _git("-c", "core.quotePath=false", "ls-files", "--others", "--exclude-standard")
    if diff is None or untracked is None:
        return None, None
    lines = [*diff.splitlines(), *untracked.splitlines()]
    return sorted({line.strip() for line in lines if line.strip()}), base


_CLIENT_REF = re.compile(r"""["']client[/"']""")


def client_reading_tests(root: Path = PROJECT_ROOT) -> list[str]:
    """會讀 ``client/`` 檔案的 pytest 測試檔（只跑前端時一起跑，免得漏掉前後端對照的測試）。

    - 原始碼裡有 ``"client"`` 或 ``"client/...`` 字串的 ``tests/**/test_*.py``；
    - 有這種字串的輔助模組（``tests/`` 裡非 ``test_*`` 的檔、``scripts/`` 的腳本），
      再加上提到它模組名稱的測試檔。寧可多跑。
    """
    tests = sorted((root / "tests").glob("**/*.py"))
    texts = {path: path.read_text(encoding="utf-8", errors="replace") for path in tests}
    helpers = [p for p in sorted((root / "scripts").glob("**/*.py")) if p.name != "check.py"]
    helpers += [p for p in tests if not p.name.startswith("test_")]
    hits = {p for p in tests if p.name.startswith("test_") and _CLIENT_REF.search(texts[p])}
    for helper in helpers:
        text = texts.get(helper) or helper.read_text(encoding="utf-8", errors="replace")
        if not _CLIENT_REF.search(text) or helper.stem == "__init__":
            continue
        word = re.compile(rf"\b{re.escape(helper.stem)}\b")
        hits |= {p for p in tests if p.name.startswith("test_") and word.search(texts[p])}
    return sorted(p.relative_to(root).as_posix() for p in hits)


def steps_for(plan: Plan, client_tests: list[str] | None = None) -> tuple[list[Step], list[Step]]:
    """依範圍挑步驟，回傳（要跑的、略過的）。"""
    if plan.scope == SCOPE_ALL:
        return list(STEPS), []
    if plan.scope == SCOPE_BACKEND:
        run = [s for s in STEPS if s.area == AREA_BACKEND]
        return run, [s for s in STEPS if s.area != AREA_BACKEND]
    run = [s for s in STEPS if s.area == AREA_CLIENT] + [CLIENT_BUILD]
    skipped = [s for s in STEPS if s.area != AREA_CLIENT]
    files = client_reading_tests() if client_tests is None else client_tests
    if files:
        pytest_step = next(s for s in STEPS if s.title == "pytest")
        run.append(
            dataclasses.replace(
                pytest_step, title=CLIENT_PYTEST_TITLE, args=(*pytest_step.args, *files)
            )
        )
    return run, skipped


def describe(plan: Plan, run: list[Step], skipped: list[Step]) -> str:
    """一開頭印的那一行：跑哪些、略過哪些、為什麼。"""
    label = {SCOPE_ALL: "全跑", SCOPE_BACKEND: "只跑後端", SCOPE_CLIENT: "只跑前端"}[plan.scope]
    base = (
        f"基準 {plan.base[:10]}（{base_ref()} 的 merge-base），改動 {plan.changed} 個檔"
        if plan.base
        else "沒有基準"
    )
    ran = "、".join(s.title for s in run)
    left = "、".join(s.title for s in skipped) or "無"
    return f"分流：{label}（{base}）。原因：{plan.reason}。跑：{ran}。略過：{left}。"


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.name == "nt":
        # 讓舊版 Windows 主控台啟用 ANSI 色碼（無副作用的慣用做法）。
        os.system("")
    return sys.stdout.isatty()


COLOR = _use_color()


def _paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if COLOR else text


def green(text: str) -> str:
    return _paint(text, "32")


def red(text: str) -> str:
    return _paint(text, "31")


def yellow(text: str) -> str:
    return _paint(text, "33")


def find_command(step: Step) -> list[str] | None:
    """找出執行此步驟的指令；找不到時回傳 None。"""
    if step.script is not None:
        return [sys.executable, str(PROJECT_ROOT / step.script)]
    if step.executable == "pnpm":
        return pnpm_command()
    if step.module is not None and importlib.util.find_spec(step.module) is not None:
        return [sys.executable, "-m", step.module]
    bin_dir = Path(sys.executable).parent
    for name in (step.executable, f"{step.executable}.exe"):
        candidate = bin_dir / name
        if candidate.is_file():
            return [str(candidate)]
    found = shutil.which(step.executable)
    return [found] if found else None


def _full_step(step: Step) -> Step:
    if step.title != "pytest":
        return step
    return dataclasses.replace(step, args=(*step.args, "-m", "not llm"))


def clean_stale_pyc() -> int:
    """刪除 ``tests/**/__pycache__/*.pyc.<pid>``（並行寫入中斷留下的暫存檔）；回傳刪除數。"""
    count = 0
    for path in (PROJECT_ROOT / "tests").glob("**/__pycache__/*.pyc.*"):
        try:
            path.unlink()
            count += 1
        except OSError:
            pass
    return count


def run_step(step: Step) -> str:
    """執行一個步驟，回傳 ``"通過"``、``"失敗"``、``"警告"``（``warn_only``）或 ``"略過"``。"""
    print(f"\n=== {step.title} ===", flush=True)
    if step.script == WATCHDOG_SCRIPT and (removed := clean_stale_pyc()):
        print(f"已清除 {removed} 個殘留的 .pyc 暫存檔。", flush=True)
    command = find_command(step)
    if command is None:
        if step.optional:
            hint = "（corepack／pnpm／npx 皆無）" if step.executable == "pnpm" else ""
            message = f"警告：找不到 {step.executable}{hint}，略過此步驟（不算失敗）。"
            print(yellow(message), flush=True)
            return "略過"
        print(red(f"錯誤：找不到 {step.executable}，請先執行 `uv sync`。"), flush=True)
        return "失敗"
    env = None
    if step.script == WATCHDOG_SCRIPT:
        # QF-3a：check.py 被單獨結束（例如 hook 逾時）時，看門狗會跟著收掉整棵 pytest 樹。
        env = {**os.environ, "TRPG_WATCHDOG_PARENT_PID": str(os.getpid())}
    completed = subprocess.run([*command, *step.args], cwd=PROJECT_ROOT, check=False, env=env)
    if completed.returncode == 0:
        return "通過"
    return "警告" if step.warn_only else "失敗"


STAMP_DIR = "pm-check-pass"


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return done.stdout.strip() if done.returncode == 0 else None


SPLIT_STAMP_DIR = "pm-check-pass-split"
"""分流跑（略過了步驟）的戳記位置。push hook 只看 ``pm-check-pass``，所以分流戳記不會讓它放行。"""


def write_pass_stamp(plan: Plan | None = None) -> Path | None:
    """追蹤中的檔案都已 commit 時，為 HEAD 的 tree 寫通過戳記；回傳戳記路徑（沒寫則 None）。

    全跑（``plan`` 是 None 或範圍 ``all``）寫 ``pm-check-pass/<tree>``（hook 看到就略過）；
    分流跑寫在 ``pm-check-pass-split/<tree>``，hook 不看。內容：commit、範圍、比對基準。"""
    if _git("status", "--porcelain", "--untracked-files=no") != "":
        return None
    tree = _git("rev-parse", "HEAD^{tree}")
    commit = _git("rev-parse", "HEAD")
    common = _git("rev-parse", "--path-format=absolute", "--git-common-dir")
    if not (tree and commit and common):
        return None
    scope = SCOPE_ALL if plan is None else plan.scope
    base = plan.base if plan is not None and plan.base else "-"
    folder = STAMP_DIR if scope == SCOPE_ALL else SPLIT_STAMP_DIR
    stamp = Path(common) / folder / tree
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(f"{commit}\nscope: {scope}\nbase: {base}\n", encoding="utf-8", newline="")
    return stamp


# --- TS-2：試用 testmon -------------------------------------------------------------------

TESTMON_FLAG = "--testmon"
TESTMON_PYTEST_ARG = "--testmon-forceselect"  # addopts 有 -m，用 forceselect 才會真的篩
TESTMON_SELECT_SCRIPT = "scripts/testmon_select.py"


@dataclass(frozen=True)
class TestmonPreview:
    """testmon 這次會選的測試數（``scripts/testmon_select.py`` 只收集算出來）。"""

    __test__ = False  # 不是 pytest 的測試類別

    selected: int
    skipped: int
    new_db: bool


def testmon_blocker(plan: Plan) -> str | None:
    """這次不能用 testmon 的原因；可以用時回傳 None。

    只在「只跑後端」時用。後端改動有非 ``.py`` 的檔（例如測試的快照、JSON）時也不用：
    testmon 只追 Python 原始碼，追不到這些檔。"""
    if plan.scope != SCOPE_BACKEND:
        label = {SCOPE_ALL: "全跑", SCOPE_CLIENT: "只跑前端"}[plan.scope]
        return f"這次範圍是{label}，testmon 只在只跑後端時用"
    blind = [p for p in plan.paths if not p.endswith((".py", ".md"))]
    if blind:
        more = f" 等 {len(blind)} 個" if len(blind) > 1 else ""
        return f"改動有 testmon 追不到的非 .py 檔（{blind[0]}{more}）"
    return None


def testmon_preview() -> TestmonPreview | None:
    """先只收集一次，算出 testmon 會選幾個、略過幾個；失敗時 None（呼叫端退回不用 testmon）。"""
    command = [sys.executable, str(PROJECT_ROOT / TESTMON_SELECT_SCRIPT)]
    try:
        done = subprocess.run(
            command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    lines = done.stdout.strip().splitlines()
    if done.returncode != 0 or not lines:
        return None
    try:
        data = json.loads(lines[-1])
        return TestmonPreview(int(data["selected"]), int(data["skipped"]), bool(data["new_db"]))
    except (ValueError, KeyError, TypeError):
        return None


def with_testmon(run: list[Step]) -> list[Step]:
    """把 pytest 步驟換成由 testmon 選測試的跑法。"""
    return [
        dataclasses.replace(s, args=(*s.args, TESTMON_PYTEST_ARG)) if s.title == "pytest" else s
        for s in run
    ]


def describe_testmon(preview: TestmonPreview | None, blocker: str | None) -> str:
    """開頭那一行後半：這次有沒有用 testmon、選了幾個、略過幾個。"""
    if blocker is not None:
        return f"指定 --testmon，但不用 testmon：{blocker}。"
    if preview is None:
        return "指定 --testmon，但 testmon 預先收集失敗，退回不用 testmon。"
    note = "（還沒有 .testmondata，這次全跑並建資料）" if preview.new_db else ""
    return (
        f"這次用 testmon（試用）：選了 {preview.selected} 個測試、略過 {preview.skipped} 個"
        f"{note}；不寫通過戳記。"
    )


def testmon_setup(plan: Plan, run: list[Step]) -> tuple[list[Step], str, bool]:
    """``--testmon``：回傳（要跑的步驟、開頭那一行要加的說明、這次是否真的用 testmon）。"""
    blocker = testmon_blocker(plan)
    preview = testmon_preview() if blocker is None else None
    note = describe_testmon(preview, blocker)
    if preview is None:
        return run, note, False
    return with_testmon(run), note, True


def _plan_for(args: list[str]) -> Plan:
    """``--full``／``--all`` 不看 git、全跑；其他依改動分流。"""
    full = "--full" in args
    if full:
        # 完整版：包含標 slow 的測試與前端完整組合；後面的 -m "not llm" 覆蓋 addopts 的 -m，
        # 但仍排除需要真模型的 llm 測試。
        os.environ["TRPG_FULL"] = "1"
    if full or "--all" in args:
        return Plan(SCOPE_ALL, "指定 --full" if full else "指定 --all")
    return plan_scope(*changed_paths())


USAGE = "用法：scripts/check.py [--all | --full] [--testmon]"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = sys.argv[1:] if argv is None else argv
    if any(a not in ("--full", "--all", TESTMON_FLAG) for a in args):
        print(USAGE)
        return 2
    full = "--full" in args
    plan = _plan_for(args)
    run, skipped = steps_for(plan)
    line = describe(plan, run, skipped)
    use_testmon = False
    if TESTMON_FLAG in args:
        run, note, use_testmon = testmon_setup(plan, run)
        line += note
    print(line, flush=True)
    results = [(step.title, run_step(_full_step(step) if full else step)) for step in run]

    print("\n=== 檢查結果摘要 ===")
    for title, result in results:
        painted = {"通過": green, "失敗": red, "警告": yellow, "略過": yellow}[result](result)
        print(f"  {title:<22} {painted}")
    for step in skipped:
        print(f"  {step.title:<22} {yellow('分流略過')}")

    failed = [title for title, result in results if result == "失敗"]
    if failed:
        print(red(f"\n失敗：{len(failed)} 個步驟（{'、'.join(failed)}）"))
        return 1
    print(green("\n全部檢查通過。"))
    if use_testmon:
        print("這次由 testmon 選測試（試用），不寫通過戳記；交件前照舊跑 --all。")
        return 0
    if all(result in ("通過", "警告") for _, result in results) and (
        stamp := write_pass_stamp(plan)
    ):
        if plan.scope == SCOPE_ALL:
            print(f"已寫入通過戳記：{stamp}（push 時同內容不再重跑）")
        else:
            print(f"已寫入分流戳記：{stamp}（只記錄；push hook 照常重跑）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
