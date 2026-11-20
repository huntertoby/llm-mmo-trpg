# Phase HC-4a 計畫：content schema 數字重新歸類，戰鬥核心先搬

> 來源：`docs/phases/寫死數值-清單.md` HC-4 節；`docs/phases/PhaseHC-1報告.md` 開發 PM 裁定第 2 點。
> 原則：**結果不變**。這段只換數字放的地方，數值不變。

## 範圍
1. **新增 `guard` 類，並重新歸類 `src/trpg/content/` 的數字**（照 HC-1 裁定 2）：
   - 執行時用到的預設值（內容沒寫、靠預設值生效的）：歸 config todo。
   - 純驗證用的上下限：歸 `guard`，status 是 done，留在 schema 不搬。
   - 例外：本身就是遊戲規則的上下限（例如「最多 2 個元素」「主動技 AP 1～3」），歸 config todo。
   - `classify.py` 和涵蓋測試都要認得 `guard`。報告寫出重新歸類後各類的筆數。
2. **戰鬥核心搬家**（清單 HC-4 a：`rules.py`、`battle.py`、`forms.py`、`parts.py`、`equipment.py`、`item_budget.py`）：
   - config 類的預設值，內容檔有寫的，就拿掉程式預設值，改成必填；內容檔沒寫的，先把值寫進 content，再改成必填。
   - 遊戲規則型的上下限，搬到 content 的規則檔（例如 `rules/core.yaml`），schema 改成讀規則。schema 讀不到規則的地方，改在 `Ruleset` 層驗證。
   - 搬進 content 的數值要加進 `tuning_fields.yaml`，讓使用者能在工坊調。哪些值該開放給工坊，照最保守的做：先開放使用者明顯會想調的，其他列在報告。
   - 每處改完，把 py 那一區的規則 status 改成 done。只改 py 那一區。

## 驗收
- 78 場戰鬥不變比對 different=0。parity、CLI 快照都不變。
- ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要 0。
- 交件前所有目錄的非 slow 測試各跑一輪，再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 每項一個 commit。報告寫在 `docs/phases/PhaseHC-4a報告.md`，附 config todo 剩幾筆。
