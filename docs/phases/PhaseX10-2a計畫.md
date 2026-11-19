# Phase X10-2a 計畫：程式認得 `quantity_scale`（先設 1，不改任何結果）

> 來源：#169 題 10；`docs/design/05-*.md` 5.4.1；`docs/phases/X10-影響盤點.md`；`docs/phases/PhaseX10-1報告.md`（第 6 節的係數清單、第 8 節待決和開發 PM 裁定）。
> ×10 拆兩步：
> - **X10-2a（這段）**：程式全部改成讀 `quantity_scale`，值先設 1，所有結果都不變。
> - **X10-2b**：跑換算腳本，把值改成 10，跑回歸。

## 範圍
1. `content/rules/core.yaml` 加 `quantity_scale: 1`，schema 只接受 1 或 10。
   - `scripts/x10/rescale.py` 改用這個值當防重跑的標記：已經是 10 就拒絕；換算時把它改成 10。拿掉每檔首行註解的做法（裁定 7）。
2. **引擎**：
   - 擲出的骰子面值 × `quantity_scale`，d20 不乘。
   - 寫死的「1 點」下限（`effects/handlers.py`、`practice.py`）改成 × `quantity_scale`。
3. **預算**：吃固定值的點數改成先 ÷ `quantity_scale` 再計，地方列在 X10-1 報告第 6 節：
   - `budget.py` 的 `flat_bonus`、`heal_flat`、自爆 `flat`、法力和耐力、回復法力；
   - `flash_ops.py`。
   - `mana_per_point`、`restore_mana_point_permille` 改成「每 `quantity_scale` 點」計價，欄位格式照需要改。
4. **LLM、組合器**：
   - `proposal_numbers.py` 補的最低花費改成 `quantity_scale`。
   - 組合器的法力等範圍取值步距改成 `quantity_scale`（裁定 5）。
5. **AI 評分**：量類（傷害、HP、護盾等）÷ `quantity_scale` 再評分（裁定 2）。`ai_profiles.yaml` 不動。
   - `fields.yaml` 裡待定的 349 個值改列不變，`infuse_threat_damage` 也改回不變。
6. **Python 預設值**（X10-1 待決 6 列的那些）改成 × `quantity_scale`，或改成從 content 讀。

## 驗收
- **`quantity_scale: 1` 時，戰鬥不變比對要 different=0**，範圍和 X10-1 一樣，外加 4 張頭目圖。
- **另外做一個不 commit 的試跑**：在 worktree 裡跑 `rescale.py`（設成 10），再跑同一組戰鬥。
  - 比較勝負、輪數、每個單位的 HP 比例；
  - 列出差異和原因（例如捨去），寫進報告。
  - 不修數值，跑完把試跑還原。
- 單元測試：骰子 ×scale、d20 不乘、預算在 scale 1 和 10 時點數相同（拿同一招技能，換算前後比）。
- ruff、format、mypy、lint-imports、`trpg content check` 結束碼 0。
- 相關測試分目錄跑，最多 `-n 8`；不要用 `-m ""`，不跑全量。
- 每個 commit 都跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 快照不應該變。
- 每項一個 commit，每個 commit 單獨跑也要乾淨。
- 報告寫在 `docs/phases/PhaseX10-2a報告.md`。
