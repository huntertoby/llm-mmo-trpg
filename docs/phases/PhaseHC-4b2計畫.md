# Phase HC-4b2 計畫：技能挑選、組合器、閃現模板的預設值搬進 content

> 來源：`docs/phases/寫死數值-清單.md` HC-4 節；HC-4b 報告最後的開發 PM 裁定。
> 原則：**結果不變**。只換數字放的地方，數值不變。做法照 HC-4a、HC-4b（兩份計畫和報告）。

## 範圍

1. **收尾**（HC-4b 裁定 1）：
   - 刪掉 HC-4b 改成 done、但現在 0 筆的 4 條 `classes.yaml` 規則。
   - 刪掉後若有數字變成沒歸類，照分類補上正確的規則。
2. **搬家**：
   - **要搬的檔**：
     - `src/trpg/content/skill_pick.py`（config todo 約 41 筆）
     - `content/composer_rules.py`（約 22）
     - `content/skill_evolution.py`（約 8）
     - `content/skills/modifiers.py`（約 10，含 `_MAX_DISPLACE`、`_MAX_ON_HIT_EFFECTS`）
   - **搬法**：
     - 有寫進內容檔的：拿掉程式預設值，改成必填。
     - 沒寫進內容檔的：先把值寫進 content，再改成必填。
   - **其他規則**：
     - 「有某欄才用到」的欄位：可省略，用到時必填。
     - 遊戲規則型的上下限：搬進 content 規則檔，在 `Ruleset` 層驗證。
     - `_MAX_DISPLACE` 搬家時，加上和 `core.max_displace_distance` 的對照驗證（HC-4b 裁定 3）。
   - **開進工坊**：搬進 content 的計價和規則數值都開進工坊，照 HC-B 的分組放。
3. **「階級與升階」分組**（HC-4b 裁定 4）：
   - 在預算表加一組「階級與升階」，把 `retier_growth`、`min_character_tier` 開進去。
   - 每格要有中文名稱，說明寫清楚調高、調低的效果。

## 不做

- `flash_templates.py`（約 54 筆）另排一段（HC-4b3）：閃現的模板文字和數字混在一起，要先分清楚。
- `NESTED_PARAMS` 留給 HC-5。
- 不動 `docs/design/`、`config/`、`llm.toml`。不改任何數值。

## 驗收

- **比對**：
  - 434 招逐招預算比對 different=0。
  - 78 場戰鬥比對 different=0（`ruleset_hash` 除外）。
  - parity、CLI 快照都不變。
  - 挑選模式和組合器的出題結果不變：用既有的 recipe census 或 `scripts/wish_coverage.py` 小樣本，前後比對。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- **測試一律經看門狗**：`uv run python scripts/run_pytest.py -q <路徑> -n 8`。交件前要跑：
  - 所有目錄的非 slow 測試，各跑一輪（一次一組；`tests/llm` 和 `tests/skillgen` 不同時跑）；
  - `-m slow tests/skillgen/test_refactor_parity.py tests/cli`；
  - 前端有改的話，tsc、vitest、build 也要跑，結束碼都要是 0。
- **快照、夾具**：先預測會變的地方，再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-4b2報告.md`，附上 config todo 剩幾筆，以及新開的工坊欄位。
