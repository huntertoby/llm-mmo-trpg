# Phase HC-W2 計畫：工坊開放 2（形狀查表、形態、裝備規則、物品生成）

> 來源：HC-B 裁定第 3 項、HC-4a 裁定第 4 項（見兩份報告最後的「開發 PM 裁定」）。使用者的目標：「以後這種變數類都要搞個CONFIG 之類的東西 才好改動」。
> **數字一律照現值搬或照現值開，不試數值，不跑平衡量測。**

## 範圍

1. **形狀的查表倍率**：錐形、十字、環形、連鎖的 `by_value_permille` 查表，以及它們的基礎值，照 HC-B 報告第 3 項的建議搬到 `skill_budget.yaml` 的 `shape_budget.<id>.by_value.<值>`，值不變，開進工坊預算表的「形狀」組。說明要寫清楚每一格對應的參數值（例：錐形長度 3）。
2. **形態、裝備規則、物品生成開進工坊**：`content/forms.yaml`、`content/rules/equipment.yaml`、`content/item_gen.yaml` 現在都不是工坊的對象。
   - 照 `src/trpg/api/tuning/` 既有 target 的做法（例：`kind: rules`、`kind: budget`），各加一個 target 或併進既有的。
   - 只開「計價或規則數值」（冷卻、持續、護盾、上限、機率、點數等）。結構欄位不開（id、清單、名稱）。
   - 每個欄位要有中文名稱和「調高、調低會怎樣」的說明。
   - 欄位多的照 HC-B 的方式分組。
   - 如果某個檔因為匯入方式讀不到草稿（像 HC-B 遇到的 `forbidden_files`），就照 HC-B 的方式處理；真的處理不了的，寫原因。

## 不做

- 不改任何數值、公式。
- 不動 `docs/design/`、`config/`、`llm.toml`。

## 驗收

- 逐招預算比對（全部內建技能）和 78 場戰鬥比對都是 different=0（`ruleset_hash` 以外）。比對腳本可沿用 HC-B 的。
- 工坊測試：改錐形查表的一格，預算表上對應技能的預算比例跟著變；改一個形態欄位、一個裝備規則欄位、一個物品生成欄位的草稿，各自能存、能驗證。
- `scripts/hardcoded/classify.py --check` 是 0；搬過的項目在清單上改成 done。
- 截圖：工坊新開的三個表各一張，加上形狀組展開的一張，存在 `docs/art/shots/hc-w2/`。
- 交件前跑完所有非 slow 的測試目錄（分目錄、一次一組、最多 `-n 8`；`tests/llm` 和 `tests/skillgen` 不同時跑），加上 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`；ruff、format、mypy、lint-imports、前端 tsc、vitest、build 都要 0。
- 快照、夾具先預測再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- 報告寫在 `docs/phases/PhaseHC-W2報告.md`。
