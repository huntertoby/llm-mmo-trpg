# Phase TS-1 計畫：check.py 依改動路徑分流（A 步）

> 來源：使用者同意分兩步做測試分流，專案 PM 於 2026-11-22 轉達。
> - 使用者原話：
>   - 「其實我在想比如說我只動戰鬥的話 那只要跑戰鬥的test就好了 動前端只要跑前端的test的測試就好了 會有影響的測試就好了 有必要都要跑全量嗎」
>   - 「不能那種有call到的function測試就好？」
>   - 對建議「先做 A 照資料夾分；再試 B 只跑有用到的測試……先試跑對照沒漏才正式用」回答：「好」。
>
> 這段只做 **A**。B（pytest-testmon 這類工具）等 A 合併以後另開一段。
>
> 和 KD-1、HC-8、WL-2 平行進行，改的檔案不重疊。只動：
> - `scripts/check.py`
> - 它的測試
> - `tests/infra/` 裡和第 3 項有關的檔案
> - `docs/dev/` 的上手筆記
>
> **不改的檔案**（要改先問開發 PM）：
> - plugin 的 hook：`F:\PythonProject\ai_agent_test\plugins\pm-workflow\hooks\pm_hooks.py`
> - `.claude/pm-workflow.json`
> - `CLAUDE.md`

## 範圍

1. **check.py 依改動路徑選步驟**：
   - 改動範圍：相對 `origin/main` 的 merge-base，加上工作區還沒 commit 的改動。
   - 只動 `client/`：只跑前端的 install、typecheck、test、build，略過 pytest 和後端的靜態檢查。
   - 只動後端的程式或測試，而且沒動 API schema：略過前端測試。
     - 「API schema」指會影響 `client/src/api/schema.d.ts` 的部分。
     - 怎麼判斷由你定，例如 openapi 的產生結果有沒有變。
   - 下面任一種情況就全跑：
     - 動到 `content/`、`config/`、API schema、`pyproject.toml`、`uv.lock`、`client/package.json`、lockfile；
     - 動到 `scripts/check.py` 本身；
     - 判斷不出來，例如沒有 `origin/main`、git 失敗。
   - `--full` 照舊全跑。
   - 每次執行一開頭印一行，說明這次跑哪些、略過哪些、為什麼。
   - 每條規則都要有測試，用假的改動清單測。
2. **通過戳記**：
   - 戳記要記錄「這次是分流跑」和比對的基準，也就是 merge-base 的 commit。
   - 先讀 hook 的 `skip_if_tree_stamped` 是怎麼判斷的（只讀，不改），確認分流戳記不會讓 hook 誤放行。
     - 會誤放行的例子：同一個 tree 在不同基準下要跑的範圍不同。
     - 如果現在的 hook 沒辦法分辨，就讓分流跑寫在另一個戳記位置，或不寫戳記。做法報告寫清楚。
   - 要改 hook 或 `.claude/pm-workflow.json` 時，只在報告寫出建議的改法，不要自己改。
3. **查 `crash_case.py` 的 240 秒逾時**：
   - 這筆是開發 PM 交接佇列的 (k)。
   - `.claude/pm-logs/push-check-20261122-105910.log` 那次全量時，`tests/infra/test_xdist_loadgroup.py::test_loadgroup_finishes_after_a_worker_crash` 逾時。子測試都過了，但外層 240 秒內沒有收尾。
   - 查清楚它在負載下還會不會發生，以及原因。
   - 照 QF-4b 放寬「兩個 worker 一起掛」那題的做法處理，例如放寬時限；理由要寫進報告。
4. **文件**：
   - `docs/dev/` 對應的上手筆記，寫清楚：分流規則、怎麼強制全跑、戳記的意思。
   - 報告附上 CLAUDE.md 第 11 條**建議改寫的全文**，附上面的使用者原話，由 PM 轉使用者確認後再改。

## 不做

- 不做 B（testmon）。
- 不改 hook、`.claude/pm-workflow.json`、`CLAUDE.md`。
- 不改其他測試的內容。

## 驗收

- **分流規則的測試**：每一種改動路徑各一個，都要通過。
- **實際跑三次**，記錄每次跑了哪些步驟、花多久：
  - 只改 `client/` 一個檔；
  - 只改後端一個檔；
  - 改 `content/` 一個檔。

  三次都用暫時的改動，跑完還原，不要 commit。
- **靜態檢查**：ruff、format、mypy、lint-imports 的結束碼都要是 0。
- **全量檢查**：全部 commit 之後，先問開發 PM「準備跑 check.py」，收到回覆才跑。用 `--full`，再加上 slow 的 parity、cli。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseTS-1報告.md`。
