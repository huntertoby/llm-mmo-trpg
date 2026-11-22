# Phase HC-4c 計畫：AI 與環境的預設值搬進 content

> 來源：
> - `docs/phases/寫死數值-清單.md` HC-4 節 c 項；
> - HC-4b3 報告最後的開發 PM 裁定 3～5。
>
> 原則：**結果不變**，只換數字放的地方，數值不變。做法照 HC-4a、HC-4b、HC-4b2、HC-4b3 的計畫和報告。

## 範圍

1. **HC-4b3 留下的收尾**（裁定 3～5）：
   - **`flash_templates.py` 還沒動的幾格改成必填**：`tighten_permille`（改歸 config）、`form_magnitudes` 的 range、`insight_per_win`、`cost_cuts` 的步距、`PriceRule.min_categories`。
     - 值以內容檔為準。內容檔沒寫的，先把現在實際生效的值寫進去。
     - `insight_per_win` 現在是程式寫 1、內容檔寫 2，實際生效的是 2，照 2。
   - **刪掉 `scale_permille` 欄位**：刪之前先 grep 前端、`content/`、`tests/`，確認真的沒有地方用到。有用到就不刪，寫進報告。
   - **刪掉 11 條 0 筆的 done 規則**：在 `classes.yaml`，是 HC-2、HC-3、HC-4a 留下的。刪完後沒歸類的筆數要是 0。0 筆的 todo 規則不動。
2. **AI 與環境搬家**：config todo 共 145 筆。
   - `src/trpg/content/environment.py`：90 筆，AI 權重。
   - `src/trpg/engine/ai/*`：55 筆，包括 `race.py` 13、`skill_estimate.py`、`rune.py`、`displace.py` 各 5 等。
   - **content 的 schema 預設值**：內容檔（`content/ai_profiles.yaml`、`content/terrain.yaml` 等）有寫的，拿掉程式預設值、改成必填；沒寫的，先把值寫進 content，再改成必填。「有某欄才用到」的欄位可以省略，用到時必填。
   - **`engine/ai/*` 的模組常數**（AI 評分權重、半徑、門檻）：
     - 搬進 content 的 AI 規則，例如 `ai_profiles.yaml` 或 `core.yaml` 的 AI 區塊。新開檔要寫理由。
     - 由 `Ruleset` 或戰鬥狀態裡已有的規則包帶進引擎。引擎不准讀檔，也不准匯入 `trpg.llm` 等禁止的模組，照 `CLAUDE.md` 實作守則 1、5。
     - 規則包內容一變，`ruleset_hash` 也會變，這是預期的。
     - 純結構常數（例如方向數、索引）照分類規則歸成 const 或 guard，並寫理由，不要硬搬。
   - **開進工坊**：
     - AI 權重照 HC-B 的分組放；工坊已有 AI 相關的表（例如 parts／ai），就放進去。
     - 每格要有中文名稱，說明寫清楚調高、調低的效果。
     - 數量多、意思相近的，可以只開代表性的幾格，其餘寫進報告。
   - 改完的那一區，`classes.yaml` 的 status 改成 done。

## 不做

- `world_*.py`、`fields.py`、`races.py`、`roguelite.py` 的數值，留給 HC-4d。
- `skillgen/` 的常數，留給 HC-5。
- text 類的數值，留給 HC-6。
- 不動 `docs/design/`、`config/`、`llm.toml`，不改任何數值。

## 驗收

- **比對**（對照基準 commit）：
  - 434 招逐招預算 different=0。
  - **78 場戰鬥 different=0**，`ruleset_hash` 除外。AI 動作的選擇也包含在內，這是這段最重要的比對。
  - 閃現出題小樣本 different=0，可以沿用 HC-4b3 的腳本。
  - parity、CLI 快照都不變。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- **測試一律經看門狗**：`uv run python scripts/run_pytest.py -q <路徑> -n 8`。交件前要跑：
  - 所有目錄的非 slow 測試，各跑一輪。一次跑一組，`tests/llm` 和 `tests/skillgen` 不同時跑。
  - `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
  - 前端有改的話，tsc、vitest、build 也要跑，結束碼都要是 0。
- **快照、夾具**：先預測會變的地方，再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-4c報告.md`，要附：
  - config todo 剩幾筆（HC-4b3 後是 699）；
  - 新開的工坊欄位。
