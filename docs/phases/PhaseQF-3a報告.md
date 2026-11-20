# Phase QF-3a 報告：pytest 看門狗與 worker 掛掉後卡死

基準：main `62ff4a66b`。分支 `worktree-agent-ac07524435a530ac8`，沒 push。規格：`docs/phases/PhaseQF-3計畫.md`「追加」第 4～7 項（QF-3b 已取消，沒做）。

**結論：卡死的根因找到了，是 pytest-xdist 3.8 `--dist loadgroup` 的排程 bug，已修。** worker 掛掉後，xdist 補上的新 worker 只拿到 1 個測試，而 worker 要等到「下一個測試」才會開始跑手上那個，所以整組永遠不再前進。worker **為什麼會掛**沒有重現到；留證機制已經裝好，下次掛掉會留下是哪個測試、stack、是逾時還是被外部結束。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 4 看門狗 | `0ef383726` | `scripts/run_pytest.py`、`tests/pytest_trace.py`（留證）、`scripts/check.py` 改走看門狗、`docs/dev/上手-測試.md`、假卡住測試 `tests/infra/stuck_suite/hang_case.py` |
| 5 worker 掛掉後卡死 | `3619da9c7` | `tests/xdist_loadgroup.py`（修正的排程）、`tests/infra/test_xdist_loadgroup.py`、示範檔 `crash_case.py`、`timeout_case.py` |
| 6 worker 數 8 → 12 | `79b074bee` | `scripts/check.py` 預設值 |
| 7 push hook 路徑＋補修 | `d2178837d` | check.py 傳自己的 PID 給看門狗（被單獨結束時看門狗收整棵樹）；排程補修第三個問題（兩個 worker 接連掛掉的 `KeyError`） |
| 報告 | 本 commit | |

## 2. 看門狗（第 4、7 項）

**用法**：`uv run python scripts/run_pytest.py [看門狗選項] <pytest 參數>`。`scripts/check.py` 的 pytest 步驟已經改走它。agent 怎麼呼叫寫在 `docs/dev/上手-測試.md`（派工範本由開發 PM 改）。

**觸發條件**：

- 「進展」＝任何一個測試跑完（`tests/pytest_trace.py` 寫的 `END` 行數增加）。還沒有任何測試開始時（收集階段）看 pytest 有沒有輸出。
- 超過 **10 分鐘**沒有進展算卡住（`--stall-minutes`，或環境變數 `TRPG_PYTEST_STALL_MINUTES`）。
- 例外：正在跑的測試如果自己的逾時比門檻長（標 slow 的 1800 秒），等到它的逾時＋60 秒才算，`--full` 的長模擬不會被誤殺。300 秒的一般測試不延長。
- 卡住時：用 PID 結束自己開的 pytest 和底下所有程序（Windows `taskkill /T /F /PID <自己開的 pid>`；其他系統是自己開的 session 的 process group），**沒有用程序名稱**；寫 `stuck.txt`，自動重跑一次（`--retries`，預設 1）；再卡住就判失敗，結束碼 **124**。
- 其他會收樹的情況：Ctrl+C（結束碼 130）；看門狗的父程序消失（check.py 會把自己的 PID 放在 `TRPG_WATCHDOG_PARENT_PID`；check.py 被單獨結束時，看門狗 2 秒內收掉整棵 pytest 樹，結束碼 130）。
- 既有的 `timeout = 300`（slow 1800）照留。
- 留證在 `.claude/pm-logs/pytest/<時間>-<pid>/attempt-<N>/`：`output.log`、`trace/*.trace`、`trace/*.stacks`、`stuck.txt`。全部通過、沒有 worker 掛掉時自動刪掉；有失敗、有 worker 掛掉、有 stack、卡住時保留。

**實測**：見第 4 節（假卡住測試）與第 7 節（父程序被單獨結束）。

## 3. worker 掛掉與卡死（第 5 項）

### 3.1 卡死的根因：xdist 3.8 `loadgroup` 補排

在暫存資料夾用 4 個測試（其中一個 `os._exit(1)`，模擬 pytest-timeout 的 thread 方式逾時）跑 `-n 2`：

| 分配方式 | 結果 |
|---|---|
| `--dist loadgroup`（專案設定，xdist 原本的排程） | `[gw0] node down` → `replacing crashed worker gw0` → 新 worker gw2 收集完（4 個），**之後永遠不動**，剩下的測試沒跑 |
| `--dist load` | 補上的 worker 把剩下的跑完 |
| `--dist loadgroup`＋本段修正 | `1 failed, 3 passed in 3.39s` |

原因（`xdist/scheduler/loadscope.py`，`loadgroup` 繼承它）：

1. 新 worker 收集完時，`schedule()` 只對每個 worker 呼叫一次 `_reschedule`，新 worker 拿到一個工作單位。`loadgroup` 下沒標 `xdist_group` 的測試一個就是一個單位，所以新 worker 手上只有 **1 個測試**。xdist 的 worker 要知道下一個測試（teardown 要用 nextitem）或收到 shutdown 才會開始跑最後一個，於是新 worker 一直等、master 也一直等它回報。這就是「補上新 worker 之後 master 不再前進」。跑到 99% 時其他 worker 都已經收到 shutdown，不會再有別的事件把它叫醒。
2. 掛掉時正在跑的那個測試會被放回佇列重跑（`--dist load` 不會）。如果它是因為逾時掛掉，重跑又要等 300 秒。
3. 兩個 worker 接連掛掉時，補上的兩個新 worker 中先收集完的那個觸發 `schedule()`，對還沒收集完的另一個也排工作，`registered_collections[node]` 的 `KeyError` 讓 master INTERNALERROR。**2026-11-19 07:40 的推送前檢查紀錄（`push-check-20261119-074000.log`）就是這樣結束的**：gw7、gw3 接連 `node down`，最後 `KeyError: <WorkerController gw9>`。

修法（`tests/xdist_loadgroup.py`，`tests/conftest.py` 匯入 `pytest_xdist_make_scheduler`，`--dist loadgroup` 時換成 `SafeLoadGroupScheduling`）：補排時每個 worker 排兩次（和 xdist 第一次分配一樣），佇列空了送 shutdown；掛掉時那個測試照樣回報失敗（`worker 'gwN' crashed while running ...`），但不重跑；還沒收集完的 worker 先不排。三種情況都有測試（`tests/infra/test_xdist_loadgroup.py`，在暫存資料夾跑示範檔，限 90 秒，超過用 PID 收樹判失敗）。

開發 PM 看到的線索都對得上：11-20 22:19 有一個 worker 掛掉、xdist 補了一個新的，之後整組不再前進；HC-W2 那次卡了 2 小時 42 分、8 個 worker 只剩 2 個（其他 worker 已經收到 shutdown 正常結束，剩下的是等不到工作的新 worker）。

### 3.2 worker 為什麼會掛：沒有重現，留證機制已裝

- 開發 PM 的單獨重跑沒有重現；本段量全量兩次也都沒有 worker 掛掉（第 5 節）。
- `pyproject.toml` 是 `timeout_method = "thread"`：逾時時 pytest-timeout 把 stack 印到 worker 的 stderr 再 `os._exit`，xdist 只看到 `node down: Not properly terminated`，stack 沒留下。11-20 那次「卡在 99%」很像是某個測試偶爾卡住超過 300 秒。
- 留證（`tests/pytest_trace.py`，只在看門狗設了 `TRPG_PYTEST_TRACE_DIR` 時啟用）：
  - 每個 worker 的 `.trace` 記每個測試的 START／END：只有 START 沒有 END 的就是掛掉時在跑的測試。
  - 每個測試在逾時前 5 秒（逾時很短時取四分之一）用 `faulthandler.dump_traceback_later` 把所有執行緒的 stack 寫進 `.stacks`；行程致命錯誤（access violation 等）也寫進同一檔。測試 `test_timed_out_worker_leaves_its_stack_in_a_file` 驗證過：4 秒逾時的測試，worker 被結束，`.stacks` 有測試函式和它呼叫的函式名稱。
- **下次掛掉怎麼判斷原因**：
  - `.stacks` 有那個測試的 stack → 逾時（看 stack 卡在哪裡）。
  - `.stacks` 沒東西、`.trace` 停在 START，而且那個測試開始到掛掉不到 300 秒 → 行程是被外部結束的（例如有人用程序名稱殺 python），或資源不足被系統結束。
- 兩個懷疑方向（多 agent 搶資源、別的 agent 用名稱殺程序）都沒辦法在本段驗證；機制能分辨這兩種和逾時。

## 4. 假卡住測試的實測（第 4 項驗收）

假測試 `tests/infra/stuck_suite/hang_case.py`：檔名不符合 `test_*.py`，預設不收集；另外沒設 `TRPG_WATCHDOG_DEMO=1` 時整檔跳過，兩層都擋，進不了推送前檢查（`pytest --collect-only tests/infra` 只收到 `test_*.py` 的 9 個）。裡面 2 個馬上通過的測試，和 1 個 `@pytest.mark.timeout(0)`、無限 `sleep` 的 `test_hangs_forever`（關掉 pytest-timeout，只靠看門狗）。

指令：`TRPG_WATCHDOG_DEMO=1 uv run python scripts/run_pytest.py --stall-minutes 0.5 tests/infra/stuck_suite/hang_case.py -n 2 -p no:cacheprovider -q`

| 步驟 | 結果 |
|---|---|
| 卡住 | 2 個測試跑完後 30 秒沒有進展，第 1 次判卡住 |
| 只殺自己那棵 | `taskkill /T /F /PID <看門狗開的 pytest>`；事後用 PID 查 4 個 worker（第 1 次 gw0 57404、gw1 40288，第 2 次 gw0 58844、gw1 49040）都已不存在。沒有用程序名稱，其他 python 程序（包括呼叫看門狗的程序）不受影響 |
| 重跑 | 自動重跑一次，同樣卡住 |
| 判失敗並寫出卡住的測試 | 結束碼 **124**，共 73 秒；兩次的 `stuck.txt` 都寫 `[gw0-<pid>] tests/infra/stuck_suite/hang_case.py::test_hangs_forever（已 32 秒）`，同一段也印在輸出 |

另外兩個 worker 掛掉的示範（`crash_case.py`、`crash_twice_case.py`）和逾時留證（`timeout_case.py`）也在 `stuck_suite/`，同樣兩層擋住，由 `tests/infra/test_xdist_loadgroup.py` 複製到暫存資料夾跑（9 個測試共約 15 秒；第一次跑曾經 66 秒，之後連跑 4 次都是 15 秒，沒找到原因，看起來是第一次啟動的成本）。

## 5. 全量秒數（第 6 項）

量的時候沒有別的 agent 在跑測試。兩次都走看門狗、同一台機器（16 核）。

| worker | 指令 | 測試數 | pytest 秒數 | worker 掛掉 |
|---|---|---|---|---|
| 8 | `scripts/run_pytest.py -q -n 8`（第 6 項改預設前、第 7 項前） | 17685 passed, 8 skipped | **814 秒**（13 分 34 秒） | 0 |
| 12 | `scripts/check.py`（預設 12，交件前那次） | 17687 passed, 8 skipped | **695 秒**（11 分 34 秒） | 0 |

- 12 個快約 15%。兩次差 2 個測試，是第 7 項加的測試（各幾秒以內），不影響比較。
- 各只量一次，沒有重複量變異。

## 6. 檢查

| 檢查 | 結束碼 |
|---|---|
| `uv run python scripts/check.py`（看門狗、workers 12，在 `d2178837d`） | **0**（全部 9 步通過，共 798 秒） |
| 其中 ruff check／ruff format --check／mypy／lint-imports | 0／0／0／0 |
| 其中 pytest | 0（17687 passed, 8 skipped） |
| 其中 client install／typecheck／test | 0（vitest 4820 passed） |
| `scripts/run_pytest.py -q tests/infra` | 0（9 passed） |
| 假卡住示範 | 124（預期） |
| 父程序被單獨結束的示範 | 1.7 秒內 worker 全部結束（第 7 節） |

報告 commit 只改這份文件，沒有重跑。

## 7. push hook（第 7 項）

- hook 逾時沒收樹的部分專案 PM 已在 plugin 修好（`taskkill /T`），本段沒改 plugin。
- 這條路徑現在多兩層保護：check.py 的 pytest 走看門狗（10 分鐘沒進展就收樹重跑，不會再等到 hook 的 1800 秒）；check.py 被單獨結束時，看門狗看到 `TRPG_WATCHDOG_PARENT_PID` 消失也會收掉整棵 pytest 樹。
- 實測（暫存的驅動腳本，只用自己開的 PID）：模擬 check.py 的父程序 P 設好 `TRPG_WATCHDOG_PARENT_PID` 後開看門狗跑 `hang_case.py`；假測試開始後只結束 P（`taskkill /F /PID`，不帶 `/T`）；**1.7 秒後**兩個 worker 都不存在。
- 收不到的情況：如果 hook 只結束最外層的 `uv`，而 `uv` 底下的 check.py 還活著，這層看不到（check.py 本身沒死）；這要靠 plugin 的 `/T`。另外 `uv run` 和 venv 的 `python.exe` 在 Windows 會多一層轉接程序，所以 check.py 明確傳 PID，不用 `os.getppid()`。

## 8. 待 PM 決定

1. **派工範本與其他文件**：`CLAUDE.md`（第 11 條與常用指令）、`docs/開發PM交接.md`（平行數「預設 8」兩處、pytest 指令範例）還是寫直接 `uv run pytest`。規格說派工範本由開發 PM 改，這段沒動這些文件；`docs/dev/上手-測試.md` 已寫好呼叫方式。
2. **xdist 修正放在 `tests/`**：`SafeLoadGroupScheduling` 繼承 xdist 3.8 的內部類別、覆寫 `remove_node`／`_reschedule`／`schedule`。升級 pytest-xdist 時要重看（上游修了就可以拿掉）。`pyproject.toml` 沒鎖上限（`pytest-xdist>=3.8.0`）；要不要鎖 `<3.9` 或在升級時再看，請 PM 決定。這段採最保守做法：不改相依版本。
3. **掛掉時那個測試不重跑**：修正後跟 `--dist load` 一樣，掛掉的測試直接記失敗（`worker 'gwN' crashed while running ...`），推送前檢查會因此失敗、不會被重跑蓋掉。這是刻意的（讓偶發逾時被看到），列出來讓 PM 知道。
4. **看門狗門檻 10 分鐘**照規格預設。12 個 worker 時全量 11.5 分鐘，正常情況下每秒都有測試跑完；要不要調短（例如 5 分鐘）請 PM 決定。
5. **worker 掛掉的原因**還沒查到（第 3.2 節）。下次出現時，留證資料夾會保留並印出路徑；建議到時把 `.stacks`／`stuck.txt` 附給 PM 再判斷。
