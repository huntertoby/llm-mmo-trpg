# Phase HC-5a 計畫：閃現生成常數搬進 content

> 來源：`docs/phases/寫死數值-清單.md` HC-5 節 a 項；HC-4d 報告的開發 PM 裁定 1（`TrapSpec.rounds`）。
> 原則：**結果不變**。只換數字放的地方，數值不變。做法照 HC-4b3（閃現模板）與 HC-4c（引擎常數經規則包帶入）的計畫和報告。

## 範圍

1. **閃現常數搬家**：`src/trpg/skillgen/` 底下的 config todo。
   - `flash_ops.py` 25、`flash_major.py` 23、`flash_offer.py` 11
   - `flash_trade.py`、`flash_reclaim.py` 各 4
   - `flash_derive.py`、`flash_cost.py` 各 2
   - 共 71 筆。
   - 模組常數（步階、上限、權重、預設代價）搬進 content 的閃現規則：優先放 `content/flash_templates.yaml` 既有的區塊；不合適就新開區塊，並寫理由。
   - 由 `FlashTable` 或 `ContentLibrary` 帶進 skillgen，skillgen 不准自己讀檔。
   - 拿不準是 config 還是結構常數的，照 `classes.yaml` 的分類規則判斷，並附上理由。`docs/dev/上手-引擎戰鬥結算.md` 第七節有寫法。
   - 量類數字（法力、耐力等）要照 `scripts/x10/fields.yaml` 登記成 scale 或 keep。程式裡原本有 `* scale` 的，照舊。
2. **`TrapSpec.rounds`**（HC-4d 裁定 1）：
   - 程式預設的 2 改成必填，或改成「用到時必填」。
   - `skillgen` 裡兩處組陷阱的地方、工坊草稿表單，改成明確帶值，值照舊是 2。
   - 改完後，`src/trpg/content/` 的 config todo 要是 0。
3. **開進工坊**：
   - 搬進 content 的閃現計價與規則數值，放進工坊的 `flash` 表（HC-4b3 開的）。
   - 每格要有中文名稱，說明寫清楚調高、調低會怎樣。
   - 數量多、意思相近的，可以只開幾格代表，其餘列在報告。
4. **收尾**：搬完後變成 0 筆的規則，直接刪掉。刪完後，沒歸類的要是 0。

## 不做

- 組合器、候選、提議類（`composer_*.py`、`candidates.py`、`proposal_*.py`、`skill_tier.py`、`evolution.py` 等）留給 HC-5b，包括 `skill_pick.py` 的 `thin_reasons`、`NESTED_PARAMS`。
- **不碰這 3 個測試檔**：`tests/skillgen/test_upgrade_topup.py`、`tests/skillgen/test_player_text.py`、`tests/roguelite/test_test_mode.py`。它們同時由 QF-4 在改。如果真的要改，寫進報告，由 PM 合併後處理。
- 不動 `docs/design/`、`config/`、`llm.toml`。不改任何數值。

## 驗收

- **比對**（對照基準 commit）：
  - 434 招逐招預算 different=0。
  - 78 場戰鬥 different=0（`ruleset_hash` 除外）。
  - **閃現出題** different=0：406 招完整技能、174 組出題，可以沿用 HC-4b3 的腳本。
  - parity、CLI 快照不變。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- **測試一律經看門狗**：
  - 開發中只跑相關測試：`uv run python scripts/run_pytest.py -q <路徑> -n 8`。
  - **交件前一次跑完全部非 slow**：`uv run python scripts/run_pytest.py -q tests -n 8`。
  - 再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
  - 前端有改的話，tsc、vitest、build 都要跑。
- **快照、夾具**：先預測會變的地方，再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-5a報告.md`，要附：
  - config todo 剩幾筆（HC-4d 後是後端 372）；
  - 新開的工坊欄位。
