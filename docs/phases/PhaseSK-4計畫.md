# Phase SK-4 計畫：吸血配方＋覆蓋表資料不進版控

> 來源：玩法交接 4.1.34 第 10 點（組合器加吸血配方，下次補配方時做）；`docs/phases/PhaseWC-2b報告.md` 開發 PM 裁定。
> **數字一律是初值，接數值工坊；不試數值，不跑平衡量測。**

## 範圍

1. **吸血配方**：
   - 組合器可以在打擊骨架、範圍骨架的傷害效果上附 `lifesteal_permille`。
   - 機率和千分比都是初值，放在 `skill_composer.yaml` 或對應的預算檔。預算要照現行規則計價。
   - 驗證器、LLM schema、提示詞如果需要跟著放寬，就升版號。
   - 聖光雙效照舊只靠手寫，不做。
2. **覆蓋表資料不進版控**：
   - `docs/phases/WC-2資料/buckets.json`（8.3 MB）和 WC-1 的同類大檔，改成不進版控：加進 `.gitignore`，並用 `git rm --cached` 移除。
   - `scripts/wish_coverage.py` 的說明要寫怎麼重產。
   - 小的摘要檔和覆蓋表 md 照舊留著。
3. 重跑 `scripts/wish_coverage.py`，更新 `docs/phases/許願覆蓋表-WC2.md`，報告「傷害＋治療」格的變化。

## 驗收

- 相關目錄的測試分目錄、一次一組，最多 `-n 8`。`tests/llm` 和 `tests/skillgen` 不同時跑。
  - 不要用 `-m ""`。
  - **每個 commit 都要跑 slow 的 parity 和 CLI 快照**：`-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- ruff、format、mypy、lint-imports、`trpg content check` 的結束碼都要是 0。
- 戰鬥不變比對要 different=0。
- 快照、夾具先預測會變哪些鍵，再逐鍵核對。版號有升就列出。
- 報告寫在 `docs/phases/PhaseSK-4報告.md`。

## 下一段（不在本段）

工坊新增對象種類（`skill_triggers`、`skill_composer`）要等本段合併後才開，因為兩段都會碰 `skill_composer.yaml`。
