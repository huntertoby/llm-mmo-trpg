# Phase HC-4b3 計畫：閃現模板的預設值搬進 content

> 來源：`docs/phases/寫死數值-清單.md` HC-4 節；HC-4b2 計畫「不做」第 1 條。專案 PM 轉使用者（2026-11-21）：「我看沒人在動了ㄟ」，之後各段連續往下做。
> 原則：**結果不變**。只換數字放的地方，數值不變。做法照 HC-4a、HC-4b、HC-4b2（計畫和報告）。

## 範圍

1. **先分清楚**：`src/trpg/content/flash_templates.py` 的 config todo 有 54 筆，text todo 有 2 筆（`FlashTemplate._check`、`_ladder`）。
   - 逐筆判斷它是哪一類：
     - **config**：遊戲數值或規則（例如 `CompleteSkillRules.flashes`、`budget_permille`、`summon_power_steps`、`FlashPricing`、`PriceRule`）。
     - **text**：組字或訊息裡的數字，留給 HC-6。
     - **guard／const**：純護欄或結構常數，照 `classes.yaml` 的分類規則歸類，並寫上理由。
   - 列表裡掛在本檔、但看起來屬於別檔的 where（`FieldDecor._shape`、`FieldMapDef._kind_problems`、`_map_stone_checks`、`_npc_problems`），先確認實際位置。不在本檔的，不在這段搬，只修正規則的 `files` 或 `where`。
2. **搬家**：
   - **config 類**：
     - 內容檔（`content/flash_templates.yaml` 等）有寫的：拿掉程式預設值，改成必填。
     - 沒寫的：先把值寫進 content，再改成必填。
     - 「有某欄才用到」的欄位：可省略，用到時必填。
   - **遊戲規則型的上下限**：搬進 content 規則檔，在 `Ruleset` 層驗證。
     - `_MAX_FORM_MAGNITUDE` 這類和別處規則有關的上限，要加對照驗證。例如它若和 `core` 或 `skill_limits` 的某格是同一個意思，就照 HC-4b 裁定 3 的做法處理。
   - **開進工坊**：搬進 content 的計價和規則數值，照 HC-B 的分組放進工坊。閃現計價類放進預算表的對應分組；沒有合適分組才新開，並寫理由。每格要有中文名稱，說明寫清楚調高、調低的效果。
   - 改完後，本檔規則的 `status` 改成 done。
3. **收尾**：
   - 刪掉 `classes.yaml` 裡改成 done 之後變成 0 筆的規則。刪完沒歸類的要是 0。
   - 順手處理 HC-4b2 改成 done 但現在 0 筆的規則（如果有）。

## 不做

- 2 筆 text 留給 HC-6。
- `skillgen/` 的閃現常數（`flash_ops.py`、`flash_major.py` 等）留給 HC-5。
- 不動 `docs/design/`、`config/`、`llm.toml`。不改任何數值。

## 驗收

- **比對**（對照基準 commit）：
  - 434 招逐招預算 different=0。
  - 78 場戰鬥 different=0（`ruleset_hash` 除外）。
  - parity、CLI 快照都不變。
  - **閃現出題不變**：用既有工具或小腳本跑固定種子的小樣本（閃現候選、完成技能、計價），前後逐位元組比對 different=0。腳本放在 scratch，不進 repo；用法和結果寫進報告。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- **測試一律經看門狗**：`uv run python scripts/run_pytest.py -q <路徑> -n 8`。交件前要跑：
  - 所有目錄的非 slow 測試，各跑一輪（一次一組；`tests/llm` 和 `tests/skillgen` 不同時跑）；
  - `-m slow tests/skillgen/test_refactor_parity.py tests/cli`；
  - 前端有改的話，tsc、vitest、build 也要跑，結束碼都要是 0。
- **快照、夾具**：先預測會變的地方，再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-4b3報告.md`，要附：
  - 54 筆的分類結果表；
  - config todo 剩幾筆（HC-4b2 後是 753）；
  - 新開的工坊欄位。
