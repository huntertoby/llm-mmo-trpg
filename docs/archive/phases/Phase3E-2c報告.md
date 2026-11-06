# Phase 3E-2c 報告｜測試基礎

## 改動

1. **`src/trpg/sim/parallel.py`（新）**：`run_tasks(fn, context, tasks, jobs=)`，用 `ProcessPoolExecutor` ＋ spawn、`initializer` 只送一次共用內容；jobs==1 或工作 <=1 時在本行程執行。工作行程異常結束時丟 `BrokenProcessPool`，不再像 `multiprocessing.Pool` 無限重開而卡住。
2. `sim/batch.py`、`sim/attack_flow_report.py` 改用 `run_tasks`，刪掉各自的全域變數與 `Pool`。
3. **pytest-timeout**（`uv add --dev`）：`pyproject.toml` 設 `timeout = 300`、`timeout_method = "thread"`；新增 `tests/conftest.py`，標 slow 的測試自動放寬為 1800 秒。
4. jobs>1 的測試（8 支）標 `@pytest.mark.xdist_group("sim_pool")`，`addopts` 加 `--dist loadgroup`，使這些測試在 xdist 下串行同一 worker，不同時開多組行程池。
5. `scripts/check.py`：pytest 前清除 `tests/**/__pycache__/*.pyc.<pid>`；docstring 寫明 agent 在自己 worktree 跑、`UV_NO_SYNC=1` 或 `uv run --frozen`。
6. 測試 `tests/sim/test_parallel.py`：結果順序與 jobs 無關、jobs<1 報錯、工作行程 `os._exit(1)` 時丟 `BrokenProcessPool`（60 秒逾時保護）。

## 時間（`UV_NO_SYNC=1`，機器上另有一個 agent 同時執行）

- `scripts/check.py` 快速版：全過，約 113 秒。
- `scripts/check.py --full`：全過，pytest 4666 passed、1 xfailed、3 xpassed（326.65 秒）；前端 756 passed；總計約 336 秒。
- 前後對照：改動前未另行量測（原版會在子行程失敗時卡住，無可比時間）。

## 子行程失敗測試

`test_a_crashing_worker_raises_instead_of_hanging`：全程在 60 秒保護內丟出 `BrokenProcessPool`，通過。

## 建議的文件文字（PM 更新 `docs/開發PM交接.md`／`CLAUDE.md`）

- 多 agent 同時工作：每個 agent 用自己的 worktree，不共用主 checkout 的 `.venv`／`__pycache__`；執行時設 `UV_NO_SYNC=1` 或用 `uv run --frozen`；合併進行中不要同時跑 pytest。
- pytest 預設單測逾時 300 秒（slow 1800）；新增會開行程池（`jobs>1`）的測試要加 `@pytest.mark.xdist_group("sim_pool")` 或標 slow。

## 待 PM 決定

1. 逾時預設 300 秒、slow 1800 秒為我的取值，規格只給 300；slow 的放寬值是否合適。
2. `timeout_method = "thread"`：逾時時整個 pytest 行程會被終止（xdist worker 會被重開），換來 Windows 也有效；若偏好只讓單測失敗需改 signal（Windows 不支援）。
3. `--dist loadgroup` 放進 `addopts`（所有 xdist 執行生效）；單檔、不用 `-n` 時無影響。
4. 殘留 `.pyc.<pid>` 只在 `check.py` 的 pytest 步驟前清；直接跑 `uv run pytest` 不會清。未做 `PYTHONDONTWRITEBYTECODE`，以免拖慢匯入。
5. `random_composer._relabel`（R12 後半）依規格留給 3E-3，未動。
6. `tests/engine/test_demo_balance.py` 自己也用 `ProcessPoolExecutor`（slow），未改用 `sim/parallel.py`。
