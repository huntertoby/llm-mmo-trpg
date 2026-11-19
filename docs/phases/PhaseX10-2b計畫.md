# Phase X10-2b 計畫：正式換算 ×10

> 來源：#169 題 10；`docs/design/05-*.md` 5.4.1；`docs/phases/PhaseX10-2a報告.md`（含開發 PM 裁定）。
> 這段要改全部內容，**期間不能有其他 agent 同時改 `content/`**。

## 範圍
1. **換算**：
   - 開工前先重跑 `scripts/x10/rescale.py --tuned-md`，更新 `docs/phases/X10-工坊調過的欄位.md`。
   - 跑 `rescale.py`，`quantity_scale` 變成 10。
   - 換算結果和 `docs/phases/X10-換算預覽.csv` 對照，列出不一樣的地方。
   - `rescale.py` 的換算結果獨立成一個 commit。
2. **X10-2a 裁定的補件**：
   - 下限改成 × scale：`mana_cost` 打折後的法力下限、`minimal_filler` 的回復法力下限。
   - `skill_budget.yaml` 裡「法力每點」之類的註解，改成新單位的說法。
   - 數值工坊 `tuning_fields.yaml` 的建議範圍照 X10-1 清單 ×10（如果換算腳本還沒做到）。
3. **快照、夾具**：
   - 數字會全面改變，這段准許重產，但要分類核對：
     - 先列出預測會變的快照、夾具檔；
     - 重產後抽樣核對，每類至少 3 筆，確認是「×10 或捨去差異」；
     - 不是這兩種原因的變動逐筆說明。
   - 卡片文字的骰子先照 2d8 的寫法，數字欄位照新值。怎麼顯示 X10-3 再決定。
4. **回歸**：
   - 跑 X10-2a 同一組 78 場，和換算前的基準比勝方、輪數、HP 比例。
   - 寫成摘要表，差異用 X10-2a 的兩個捨去來源解釋；有別的原因就逐場列。
   - **不修數值。**

## 驗收
- ruff、format、mypy、lint-imports、`trpg content check` 結束碼 0。
- 相關測試分目錄跑，最多 `-n 8`。`tests/llm` 和 `tests/skillgen` 不同時跑。不要用 `-m ""`，不跑全量（交件後 PM 跑）。
- 每個 commit 都跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 斷言寫死舊數字的測試改成新數字，不放寬斷言；改了哪些依目錄列在報告。
- `LOG_FORMAT`、提議 schema、`PROMPT_VERSION` 有變就升號。OpenAPI 有變就重產。
- 前端：tsc、vitest、build 結束碼 0；前端夾具只改數字。
- 報告寫在 `docs/phases/PhaseX10-2b報告.md`。
