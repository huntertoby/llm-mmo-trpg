# Phase QF-3 計畫：測試加速

> 來源：專案 PM 轉使用者決定（2026-11-21）：「排小段加速」。排在 HC-W2 推送之後、HC-4b 之前。
> 現況：推送前檢查的 pytest 每次 800～940 秒，共 17664 個測試；一週前約 750 秒、1.5 萬個。紀錄在 `.claude/pm-logs/push-check-20261120-*.log`。機器 16 核，`scripts/check.py` 預設 `TRPG_PYTEST_WORKERS=8`。

## 範圍

1. **worker 數**：實測 10、12 兩種，以及現在的 8，各記秒數。
   - 要改的話只改 `scripts/check.py` 的預設值，不改 `.claude/pm-workflow.json`。
   - 11-13 有過一次紀錄：多個 agent 同時跑時，xdist worker 掛掉卡死。挑一個有其他 agent 同時工作也穩的數字，並寫理由；穩不穩看報告裡寫的觀察，不必真的開 agent 壓測。
2. **最慢的測試**：用 `--durations=30` 找出最慢的 30 個。
   - 能加速就加速：共用 fixture（`scope="module"`／`"session"`，要確認沒有共享可變狀態）、縮小參數組合但覆蓋的分支不能少、hypothesis 的 `max_examples` 只在有理由時調。
   - **不准先改標 slow**：想改標 slow 的，列在報告「待 PM 決定」，寫清楚是哪個測試、理由、少掉什麼覆蓋，由 PM 轉專案 PM 決定。
3. **不准**拿掉任何檢查、改 hook 的門檻、或改 `.claude/pm-workflow.json`。

## 驗收

- 報告寫在 `docs/phases/PhaseQF-3報告.md`，要有：
  - 改前、改後的 pytest 秒數。用同一份 `scripts/check.py` 指令量，記錄當時有沒有別的程序在跑。
  - worker 數實測表（8／10／12）。
  - 最慢 30 個測試的清單，每個寫處置：加速了多少、不動的理由、或建議改標 slow。
- 改過的測試，測試數量不能少（改前、改後的 collected 數字都要寫）。
- 交件前跑一次 `uv run python scripts/check.py`，結束碼要 0；ruff、format、mypy、lint-imports 也要 0。前端沒改就不用跑。
- **全量不要和別的 agent 的測試同時跑**；這段派出時 PM 不會同時派別的 agent。
