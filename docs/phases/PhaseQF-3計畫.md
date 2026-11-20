# Phase QF-3 計畫：測試加速

> 來源：專案 PM 轉使用者決定（2026-11-21）：「排小段加速」。排在 HC-W2 推送之後、HC-4b 之前。
> 現況：推送前檢查的 pytest 每次 800～940 秒，共 17664 個測試；一週前約 750 秒、1.5 萬個。紀錄在 `.claude/pm-logs/push-check-20261120-*.log`。機器 16 核，`scripts/check.py` 預設 `TRPG_PYTEST_WORKERS=8`。

> **2026-11-21 更新**：專案 PM 轉使用者決定：「那 排小段加速 就不用了」。**QF-3b（加速，下面「範圍」第 1～3 項和「驗收」）取消**，只做 QF-3a（防卡死，見「追加」第 4～5 項）。順序：HC-W2 合併並推送 → QF-3a → HC-4b。

## 範圍（QF-3b，已取消）

1. **worker 數**：實測 10、12 兩種，以及現在的 8，各記秒數。
   - 要改的話只改 `scripts/check.py` 的預設值，不改 `.claude/pm-workflow.json`。
   - 11-13 有過一次紀錄：多個 agent 同時跑時，xdist worker 掛掉卡死。挑一個有其他 agent 同時工作也穩的數字，並寫理由；穩不穩看報告裡寫的觀察，不必真的開 agent 壓測。
2. **最慢的測試**：用 `--durations=30` 找出最慢的 30 個。
   - 能加速就加速：共用 fixture（`scope="module"`／`"session"`，要確認沒有共享可變狀態）、縮小參數組合但覆蓋的分支不能少、hypothesis 的 `max_examples` 只在有理由時調。
   - **不准先改標 slow**：想改標 slow 的，列在報告「待 PM 決定」，寫清楚是哪個測試、理由、少掉什麼覆蓋，由 PM 轉專案 PM 決定。
3. **不准**拿掉任何檢查、改 hook 的門檻、或改 `.claude/pm-workflow.json`。

## 驗收（QF-3b，已取消）

- 報告寫在 `docs/phases/PhaseQF-3報告.md`，要有：
  - 改前、改後的 pytest 秒數。用同一份 `scripts/check.py` 指令量，記錄當時有沒有別的程序在跑。
  - worker 數實測表（8／10／12）。
  - 最慢 30 個測試的清單，每個寫處置：加速了多少、不動的理由、或建議改標 slow。
- 改過的測試，測試數量不能少（改前、改後的 collected 數字都要寫）。
- 交件前跑一次 `uv run python scripts/check.py`，結束碼要 0；ruff、format、mypy、lint-imports 也要 0。前端沒改就不用跑。
- **全量不要和別的 agent 的測試同時跑**；這段派出時 PM 不會同時派別的 agent。

## 追加：防卡死（2026-11-21）

> 專案 PM 轉使用者決定：「併進去」，指把防卡死併進 QF-3。因為範圍變大，拆成兩段，依序派：**QF-3a 防卡死**（下面兩項）先做，**QF-3b 加速**（上面第 1～3 項）接著做。兩段都會改 `scripts/check.py`，所以不平行。QF-3a 的報告寫在 `docs/phases/PhaseQF-3a報告.md`，QF-3b 的寫在 `PhaseQF-3報告.md`。

4. **看門狗**：寫一支共用的小腳本（例如 `scripts/run_pytest.py`），所有跑測試的地方都改用它，包括 `scripts/check.py` 和 agent 自己跑的 pytest。
   - 規則：輸出超過 N 分鐘沒有進展（預設 10 分鐘，可以用參數改），就只結束自己開的那棵程序樹（用 PID 往下找子程序），然後自動重跑一次。重跑還卡住就判失敗，寫清楚卡在哪個測試：用 `-v` 或 `--log` 類的方式記下最後開始、還沒結束的測試。
   - **不准用程序名稱去殺 python。**
   - 既有的每個測試 300 秒上限照留。
   - 寫進 `docs/dev/` 的上手筆記（測試那份，沒有就新開 `上手-測試.md`），寫清楚 agent 應該怎麼呼叫這支腳本。派工範本由開發 PM 自己改。
5. **查 worker 為什麼會死**：
   - 開 `faulthandler`（例如 `-p faulthandler`、`faulthandler_timeout`），或用其他做法，讓 worker 死前留下 traceback 和原因，存到檔案。
   - 線索：
     - 2026-11-20 18:40 HC-W2 的 `tests/api -n 8` 卡了 2 小時 42 分，8 個 worker 只剩 2 個；
     - 11-13 也出現過同一型；
     - HC-W2 會用 `-v` 重跑 `tests/api`，結果寫在 `docs/phases/PhaseHC-W2報告.md`。
   - 兩個懷疑方向：多個 agent 同時跑，資源不夠；或者某個 agent 收尾時用名稱殺程序，誤殺了別人的 worker。
   - 能定位就修掉根因；定位不到，就把留證的機制保留下來。

**QF-3a 驗收**：
- 報告要寫：
  - 看門狗的觸發條件；
  - 實測結果：故意寫一個會卡住的假測試驗證「卡住 → 只殺自己那棵 → 重跑 → 判失敗並寫出卡住的測試」。假測試要放在預設不收集的地方，或用 marker 擋掉，不能進入推送前檢查；
  - 根因的結論。
- `uv run python scripts/check.py`（改用看門狗後）結束碼 0；ruff、format、mypy、lint-imports 也是 0。

## 追加：worker 數（2026-11-21）

> 專案 PM 轉使用者決定：「同時跑的份數從 8 調到 12」。

6. **QF-3a 一併做**：`scripts/check.py` 的 `TRPG_PYTEST_WORKERS` 預設值從 8 改成 12。報告附改前（8）、改後（12）各一次的全量秒數；量的時候不能有別的 agent 同時跑測試（這段派出時 PM 不會同時派別的 agent）。QF-3b 的其他部分照舊取消。
