# Phase AP-2b 計畫：預支技能 0 法力

> 來源：`docs/phases/PhaseAP-2報告.md` 待決 3 與開發 PM 裁定；`docs/design/06-技能.md` 6.10 最低花費的例外、6.3「預支」（玩法 PM 39a686810）。
> **不試數值，不跑平衡量測。** 小段，只做這一件。

## 範圍
1. 帶 `borrow_ap` 原語的技能不受「主動法術技至少 1 法力、武器技至少 1 耐力」的最低花費限制：0 法力、0 耐力。
   - 驗證器、組合器、產生器、LLM 提議、工坊都要放行。最低花費的規則在 `src/trpg/content/skill_rules.py` 和 `src/trpg/skillgen/` 底下幾個檔，先列出全部用到的地方再改。
   - 其他技能照舊擋。
2. 基本款預支技能「搶拍」改成 0 法力，卡片和說明照實寫。
3. 其他已有的預支技能、夾具一起照新規則（先預測，再逐鍵核對）。

不做：給精英、頭目裝預支（AP-2 待決 4，另外排）。

## 驗收
- 單元測試：帶預支的技能 0 法力、0 耐力可以通過；不帶預支的 0 法力照舊被擋。
- 戰鬥不變比對：不帶預支的戰鬥 different=0。
- LLM schema、提示詞有改就升版號；`LOG_FORMAT` 有升就列出。
- 每個 commit 都要乾淨，單獨跑也要過。
- 每個 commit 都跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。測試分目錄、一次一組，最多 `-n 8`；不要用 `-m ""`。
- ruff、format、mypy、lint-imports、`trpg content check` 結束碼 0；有動到前端就跑 tsc 和相關 vitest。
- 報告寫在 `docs/phases/PhaseAP-2b報告.md`。
