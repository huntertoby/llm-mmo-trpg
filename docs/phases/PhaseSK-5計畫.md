# Phase SK-5 計畫：工坊新對象種類＋許願池補抽吸血

> 來源：
> - `docs/phases/PhaseSK-3b報告.md` 待決 4
> - `PhaseWC-2報告.md` 待決 11
> - `PhaseSK-4報告.md` 待決 4
> - 玩法交接 4.1.34 第 10 點（445c4545c）
>
> **數字一律是初值，不試數值，不跑平衡量測。**

## 範圍

1. **工坊新增對象種類**：
   - 新增 `skill_triggers`，開放新觸發的係數，例如「被利用時」的 300。
   - 新增 `skill_composer`，開放下列組合器數值：
     - SK-2b 的四個機率；
     - SK-3b 的兩個新串流機率；
     - WC-2 的 `passive.around_permille`、`structure.stack_rider_permille`、`summon_rider_permille`；
     - SK-4 的 `lifesteal_permille`、`lifesteal_amount_permille`。
   - 白名單寫在 `tuning_fields.yaml`。工坊介面要能看到、能改，改完要通過內容驗證。
   - 不開放結構性欄位，例如 `lifesteal_skeletons` 這種清單。
2. **許願池補抽吸血**：
   - 許願標籤同時有「傷害」和「治療」時，像召喚、換元素那樣，專門補抽吸血版本的候選，照 07 7.6 第 2 點「照標籤專門做候選」。
   - 只許「治療」時不補抽。
   - 重跑 `scripts/wish_coverage.py`，報告「傷害＋治療」格的變化。

## 驗收

- 相關目錄的測試分目錄、一次一組，最多 `-n 8`。`tests/llm` 和 `tests/skillgen` 不同時跑。
  - 不要用 `-m ""`。
  - 每個 commit 都要跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 以下檢查的結束碼都要是 0：ruff、format、mypy、lint-imports、`trpg content check`、前端 tsc，以及工坊相關的 vitest。
- 戰鬥不變比對要 different=0：工坊沒改任何值時，結果要和改前相同。
- 快照、夾具要先預測，再逐鍵核對。版號有升就列出。API 有改就重產 OpenAPI。
- 工坊介面要有實機截圖，測試要靜音。
- 報告寫在 `docs/phases/PhaseSK-5報告.md`。
