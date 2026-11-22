# 階段 TS-1 報告：check.py 依改動路徑分流（A 步）

基準：main `2ea576e2d`。分支 `worktree-agent-aff44d50b5282cf31`，沒有 push。規格：`docs/phases/PhaseTS-1計畫.md`。

## 結果（一兩句）

`check.py` 不加參數時，會依「`origin/main` 的 merge-base 到工作區」的改動選步驟。分流跑的戳記另外放在 `pm-check-pass-split/`，hook 不看，所以不會誤放行。crash_case 的兩次逾時都是子測試全部回報後，主行程沒收尾，不像是機器太忙。處理方式照 QF-4b 放寬到 540 秒，另外在逾時前把主行程的 stack 留下來。

## 交付項目
| 項目 | 狀態 | commit |
|---|---|---|
| 1 check.py 依改動路徑選步驟 | 完成 | `ba08ceecc` |
| 2 通過戳記（分流跑另放位置，記範圍與基準） | 完成 | `08081d223` |
| 3 crash_case 240 秒逾時：查原因、放寬、留證 | 完成（原因只查到一半，見第 3 節） | `e1fefb52d` |
| 4 文件：`docs/dev/上手-測試.md` 一之一、一之二節，第五節補時限 | 完成 | `be816db3f` |
| 報告 | 本檔 | （本 commit） |

### 1. 分流規則表

改動範圍：`git merge-base HEAD origin/main` 到工作區的改動，用 `git diff --name-only --no-renames <base>` 再加 `git ls-files --others --exclude-standard`。改名時新舊路徑都算。環境變數 `TRPG_CHECK_BASE` 可以換基準。

| 改動 | 範圍 | 跑 | 略過 |
|---|---|---|---|
| 只動 `client/`，可以夾 `.md` | 前端 | client install、typecheck、test、build，加上「讀 client/ 的 pytest」（目前 18 檔） | ruff、format、mypy、lint-imports、其他 pytest、situation coverage |
| 只動 `src/`、`tests/`、`scripts/`，可以夾 `.md` | 後端 | ruff、format、mypy、lint-imports、pytest、situation coverage | client install、typecheck、test |
| `content/`、`config/`（底下的 `.md` 也算）、`pyproject.toml`、`uv.lock`、`.python-version`、任何 `package.json`、`pnpm-lock.yaml`、`pnpm-workspace.yaml`、`package-lock.json`、`yarn.lock`、`client/openapi.json`、`client/src/api/schema.d.ts`、`scripts/check.py` | 全跑 | 全部 | — |
| 前端、後端都有動 | 全跑 | 全部 | — |
| 其他位置，例如 `docs/` 的非 `.md` 檔、`.claude/`、`.github/`、根目錄設定 | 全跑 | 全部 | — |
| 只有 `.md`，或沒有改動 | 全跑 | 全部 | — |
| 沒有 `origin/main`、git 失敗 | 全跑 | 全部 | — |
| `--all` | 全跑，不看 git | 全部（非 slow） | — |
| `--full` | 照舊 | 全部＋slow、`TRPG_FULL=1` | — |

- **API schema 的判斷**：檢查 `client/openapi.json`、`schema.d.ts` 這兩個檔有沒有改動。後端改了 API 卻沒重產 openapi.json 時，`tests/api/test_openapi_snapshot.py` 會失敗，只跑後端時也一樣擋得下來（這個測試屬於後端）。重產之後，這兩個檔一變就落到全跑。我沒有另外在 check.py 裡動態產 openapi 來比對，因為快照測試已經涵蓋。
- **「讀 client/ 的 pytest」**：規格寫「只動 client 時略過 pytest」，但有後端測試會讀 client 的檔案，例如 `test_client_fixtures`、`test_hardcoded_scan`、`test_range_text`、`test_tile_info`、`test_appearance`、`test_openapi_snapshot`。整個略過的話，前端改了會漏掉這些前後端對照的測試，所以我把它們一起跑（見待 PM 決定 1）。挑法寧可多跑：測試檔裡有 `"client"` 或 `"client/` 字串，或提到有這種字串的輔助模組或腳本的模組名，就算進來。
- **client build**：規格寫只動 client 時要跑 build，原本的 STEPS 沒有 build（全跑時 build 由 hook 另外跑），所以只在前端範圍加這一步。
- 每次執行一開頭印一行，例如：`分流：只跑後端（基準 2ea576e2db（origin/main 的 merge-base），改動 3 個檔）。原因：…。跑：…。略過：…。` 摘要表的最後也會把略過的步驟標成「分流略過」。
- 測試：`tests/infra/test_check_split.py`，共 42 個。每條路徑規則各一個（含參數化），另外測 git 失敗、merge-base 失敗、diff 加未追蹤檔、`TRPG_CHECK_BASE`、三種範圍的步驟、讀 client 測試的挑法（假的資料夾）、開頭那一行、兩種戳記位置、`--full` 和 `--all` 不看 git、未知參數。

### 2. 戳記與 hook 的結論

- 讀了 hook 的 `tree_stamped`（只讀）：它只看 `<common>/pm-check-pass/<tree>` 這個檔**存不存在**，不讀內容；找不到時往回最多 30 個 first-parent 祖先，祖先到 HEAD 之間只改 `*.md` 也放行。`skip_checks_if_only` 是看「還沒 push 的 commit 加上工作區的檔」是否全部符合 `*.md`。
- 所以 hook **分不出**同一個 tree 在不同基準下分流範圍不同的情形。做法：
  - 範圍 `all`（全跑，包括 `--all`、`--full`、被觸發的全跑）通過時，照舊寫 `pm-check-pass/<tree>`，hook 照舊略過。
  - 分流跑通過時寫 `pm-check-pass-split/<tree>`，hook 不看，不會因此放行。
  - 兩種內容都是三行：`<commit>`、`scope: <all|backend|client>`、`base: <merge-base 或 ->`。hook 不讀內容，所以加行不影響它。
- 副作用：hook 自己跑的也是不加參數的 check.py，所以 push 時 hook 也會分流，基準是 `origin/main`，也就是這次要推的內容。實作 agent 交件前如果是分流跑，hook 會再分流跑一次，不能像以前一樣看戳記略過（見待 PM 決定 2）。
- **建議的 hook 改法（我沒改）**：在 `.claude/pm-workflow.json` 的檢查設定加一個欄位，例如 `"skip_if_split_stamped": "pm-check-pass-split"`。hook 找到這個位置的 `<tree>` 戳記時，讀它的 `base:`，跟 `git merge-base HEAD @{u}` 比對；一樣才略過。同一個 tree、同一個基準，改動清單就一樣，範圍也一樣，跟現在全跑戳記的保證相同。另一個做法是不改 hook，改由 check.py 自己在開頭檢查「這個 tree 已有同基準的分流戳記」就直接結束 0。這也在規格外，留給 PM 決定。

### 3. crash_case 逾時的原因與處理

- 證據：
  - 11-22 10:59 那次全量（`.claude/pm-logs/push-check-20261122-105910.log`）。子程序的輸出到 `[gw2] [100%] PASSED test_b` 就停了，四個子測試都回報了，但 240 秒內沒有印出結尾摘要。
  - 留證 `.claude/pm-logs/pytest/20261122-105955-60332/attempt-1/trace/` 顯示，同一刻（11:06:16）在另一個 worker 開始的「兩個 worker 一起掛」那題，13.6 秒就跑完了。這題結束後，同一個 worker 接著跑的 timeout_case 也只花 13 秒。
  - 11-21 17:28 「兩個 worker 一起掛」那題的 240 秒逾時（QF-4b 放寬的原因）也是一樣的樣子：`[gw3] [100%] PASSED test_c` 之後就停了。
- 本機重現：
  - 20 個吃滿 CPU 的程序同時跑時，單獨跑 15 次，每次 33～60 秒，全部正常結束。
  - 用 `-n 12` 讓 36 份同時跑，模擬全量時從 xdist worker 裡開子 pytest，每份 22～30 秒，全部正常。
  - 合計 51 次，沒有卡住。
- 判斷：**不是單純太慢**。比較像 xdist／execnet 在補開 worker 後的收尾階段很少見地卡住：主行程在等 workerfinished，或卡在 `teardown_nodes`。我讀了 `dsession.py`、`loadscope.py`、`execnet/multi.py` 和我們的 `SafeLoadGroupScheduling`，沒找到確定會卡住的路徑。所以原因只查到「卡在收尾」這一層。
- 處理（`e1fefb52d`）：
  - 照 QF-4b 的做法，把只掛一個的那題也放寬到內層 540 秒、外層 `timeout(600)`。常數改成兩題共用的 `CRASH_LIMIT_SECONDS`、`CRASH_TIMEOUT_SECONDS`。timeout_case 維持 240 秒。
  - 子程序的 conftest 在主行程（沒有 `PYTEST_XDIST_WORKER` 的那個）用 `faulthandler.dump_traceback_later`，在時限前 20 秒把所有執行緒的 stack 寫進 `master-hang.stacks`。逾時的失敗訊息會附上這份 stack；子測試已到 `[100%]` 時，會註明「卡在主行程收尾」。
  - 我用 `hang_case.py` 限 40 秒實測過：失敗訊息裡有主行程停在 `dsession.py loop_once` 的 stack。這個驗證用的測試沒有 commit。
- 理由：規格要求照 QF-4b 放寬。放寬只能解決「太慢」那種情形；如果真的是卡死，放寬只是把失敗延到 540 秒才報。但下次再發生時，報告裡會有主行程的 stack，就能查到底（見待 PM 決定 3）。

### 4. CLAUDE.md 第 11 條建議改寫的全文

> 使用者原話（TS-1 計畫，專案 PM 2026-11-22 轉達）：「其實我在想比如說我只動戰鬥的話 那只要跑戰鬥的test就好了 動前端只要跑前端的test的測試就好了 會有影響的測試就好了 有必要都要跑全量嗎」「不能那種有call到的function測試就好？」；對「先做 A 照資料夾分；再試 B 只跑有用到的測試……先試跑對照沒漏才正式用」回答：「好」。

建議全文如下。只改粗體「依改動分流」那幾句，其他照原文：

11. **節省 token 與時間**（2026-11-02 更新，使用者：「好那都改 寫入」；2026-11-04 放寬 agent 數與全量頻率，使用者：「放寬、排」「同意，改第 11 條」）：開發中只跑**直接相關**的測試檔（`uv run pytest -q tests/<路徑> -x`，平行最多 `-n 8`），CLI 輸出快照與大範圍測試只在交件前跑一次；每次 commit 與每段合併只跑 `ruff check`、`ruff format --check`、`mypy`、`lint-imports`、相關測試與一場重播；**一般的完整檢查交給 push hook（每次推到程式、測試、資料時自動跑；只改 `.md` 文件的推送略過），PM 不另外手動跑全量；階段結束審查前跑一次 `scripts/check.py --full`（含 slow 測試）**（2026-11-21 使用者選「拿掉 PM 手動那次」「只改文件就不跑」）；**`scripts/check.py` 不加參數時依改動路徑分流：只動 `client/` 只跑前端（加上讀 client 檔的後端測試），只動 `src/`、`tests/`、`scripts/` 略過前端測試；動到 `content/`、`config/`、API schema、相依或 lockfile、`check.py` 本身，或判斷不出來時全跑；`--all` 強制全跑，規則見 `docs/dev/上手-測試.md`**（2026-11-22 使用者：「動前端只要跑前端的test的測試就好了 會有影響的測試就好了」，對先照資料夾分回答「好」）；實作 agent 交件前，**全部 commit 之後**在自己的 worktree 跑一次 `uv run python scripts/check.py`（內含看門狗；2026-11-21 使用者：「改成一次跑完」），**全跑通過時**會寫下這份內容的通過戳記；合併後內容沒變時 push hook 看到戳記就不再重跑完整檢查，只跑前端建置（2026-11-21 使用者：「拿掉第二次重複的測試」）；**分流跑的戳記 hook 不認，push 時 hook 會依要推的內容再分流跑一次**。合併時若 main 已有別的改動，內容不同、hook 照常重跑；開發中仍只跑相關測試；待決事項中的原型數值與解讀類，agent 照最保守的預設直接做完並寫進報告，PM 的確認累積到下一段順手改、不另開收尾段（規則類照舊先問）；**同時進行的 agent 最多 4 個，平行的 agent 不可改同一批檔案**；**全部測試（`scripts/check.py`、hook 的 push 檢查）同一時間只跑一份**，平行的 agent 交件前要錯開，由開發 PM 排順序（2026-11-21 使用者：「好，請開發 PM 錯開跑」）。大型模擬（`trpg sim completion`／`matrix` 全量）除非規格要求，否則不跑。數值由使用者自己在數值工坊調：PM 與 agent 不試數值、不量平衡，有疑慮記進 `docs/design/平衡待查.md`（2026-11-21 使用者選「改成記平衡待查」）。

（如果 PM 採用待 PM 決定 2 的「交件前加 `--all`」，把「跑一次 `uv run python scripts/check.py`」改成「跑一次 `uv run python scripts/check.py --all`」，並刪掉最後那句粗體。）

## 驗收條件
| 條件 | 結果 | 證據（測試名、截圖路徑） |
|---|---|---|
| 分流規則的測試：每種改動路徑各一個 | 通過，42 passed | `tests/infra/test_check_split.py` |
| 實跑：只改 `client/` 一個檔 | 還沒跑（等開發 PM 排隊通知） | — |
| 實跑：只改後端一個檔 | 還沒跑（等開發 PM 排隊通知） | — |
| 實跑：改 `content/` 一個檔 | 還沒跑（等開發 PM 排隊通知） | — |
| 靜態檢查 | 通過 | 見下表 |
| 全量 `--full`＋slow parity、cli | 還沒跑（等開發 PM 排隊通知） | — |
| 每項一個 commit | 通過 | 見交付項目 |

## 檢查指令結果
| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0 |
| `uv run pytest -q tests/infra/test_check_split.py` | 0（42 passed） |
| `uv run pytest -q tests/infra -n 4` | 0（51 passed） |

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）
| 事項 | 我的做法 | 其他選項 |
|---|---|---|
| 1 只動 client 時，規格寫略過 pytest | 仍跑「讀 client/ 檔案的 pytest」（目前 18 檔，有幾個是寧可多跑挑進來的），避免漏掉前後端對照的測試 | 完全照規格略過 pytest |
| 2 交件前的 check.py 是分流跑時，hook 不認戳記，push 時會再分流跑一次 | 照規格「hook 分不出來就另放位置」：分流戳記放 `pm-check-pass-split/`，不改 hook | (a) 交件前改跑 `--all`，維持「hook 不重跑」；(b) 照第 2 節的建議改 hook，比對 `base:`；(c) check.py 自己看到同 tree、同基準的分流戳記就直接結束 |
| 3 crash_case 逾時的真正原因 | 照 QF-4b 放寬到 540 秒，加上主行程 stack 留證 | 子測試已到 `[100%]` 才逾時的，改判通過並印警告（不擋 push，但可能遮住排程卡死）；或另開一段專查 xdist 收尾 |
| 4 只有 `.md` 或沒有改動時 | 全跑（判斷不出來就全跑）；hook 本來就略過只改 `.md` 的推送 | 不跑任何步驟 |
| 5 `docs/` 底下非 `.md` 的檔（圖、`.py`、csv） | 全跑：前端 dev 頁會讀 `docs/art`，後端有測試讀 `docs/art/sample/tools` | 歸到前端或後端 |
| 6 新增 `--all`、`TRPG_CHECK_BASE` | 規格要求文件寫「怎麼強制全跑」，所以加了 `--all`；驗收要只比對暫時改動，所以加了 `TRPG_CHECK_BASE` | 拿掉，只留 `--full` |
| 7 只動 client 時跑的 client build | 加在 check.py 裡；push 時 hook 也會再跑一次 build | 拿掉 check.py 那一步，只靠 hook |

## PM 裁定
（由開發 PM 填）
