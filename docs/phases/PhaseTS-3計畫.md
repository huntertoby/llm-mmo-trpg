# Phase TS-3 計畫：移除 testmon 試用模式

> 來源：
> - 使用者 2026-11-23 對「試用模式和兩個套件留不留」回答「A」，也就是移除（專案 PM 轉達）。
> - `docs/phases/PhaseTS-2報告.md`：結論和開發 PM 驗收。
>
> 和 CR-1c 平行。CR-1c 動的是 `client/`、`src/trpg/engine/crit_damage.py`、`src/trpg/roguelite/hero_crit.py`、view 這一帶，這段都不要碰。

## 範圍

1. 拿掉 `scripts/check.py` 的 `--testmon` 參數，以及它相關的程式。不加參數和 `--all` 的行為、戳記規則都要和 TS-2 之前完全一樣。
2. 刪掉 `scripts/testmon_select.py` 和 `tests/infra/test_check_testmon.py`。
3. 用 `uv remove --dev` 移除 `pytest-testmon`、`coverage` 兩個套件，`pyproject.toml`、`uv.lock` 一起 commit。
   - 先查 `coverage` 有沒有被別的地方用到，例如其他套件的相依。用到的話只移除 testmon，並寫進報告。
4. `.gitignore` 拿掉 `.testmondata*` 那行。
5. `docs/dev/上手-測試.md` 拿掉試用模式那一節。另外補一句：曾試過 testmon，不採用，原因見 TS-2 報告。
6. TS-2 報告和計畫留著當紀錄，不改。

## 不做

- 不改 hook、`.claude/pm-workflow.json`、`CLAUDE.md`。
- 不改其他測試。

## 驗收

- 用 grep 檢查全專案（`docs/archive/` 和 TS-2 的報告、計畫除外），已經找不到 `testmon`。
- 靜態檢查，結束碼都要是 0：ruff、format、mypy、lint-imports。
- 跑 `tests/infra/` 的相關測試。
- **全量檢查**：全部 commit 之後，用 SendMessage 問開發 PM「TS-3 準備跑 check.py」，**收到「可以跑」才跑** `check.py --all`。在那之前不要交件。
- 每項一個 commit。報告寫在 `docs/phases/PhaseTS-3報告.md`。
