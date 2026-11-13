# Phase KW-1b 完成報告｜修 KW-1 合併後全量檢查的 4 條失敗

> 基準：main `f49912db6`（worktree 原本在 `aea340f2c`，開工前 fast-forward）。

## 1. 預測（動手前寫下）

| 修法 | 預測會變的測試／快照 |
|---|---|
| 1. `trpg llm propose` 的關鍵字輪替改用 `start_ids()`（`--keywords` 指定時仍接受全部關鍵字） | `test_mock_n3_snapshot` 通過且**快照不重產**：`rng.choice` 在 12 個與 16 個裡取同一個索引時，前 12 個順序一樣，原本抽到 `concealed`、`summon`、`poisoned` 的那幾次會回到原樣。`tests/llm/test_prompt_prefix.py`（同樣 `count=3, seed=0`）仍通過。其他快照不變。 |
| 2. `test_summons_e1.py` 灌注表測試改看 `start_ids()` ＋ PENDING 提醒 | 只有這條變（失敗 → 通過）。 |
| 3. `test_form_start.py` 開局池 ≥ 3 改看 `start_ids()` ＋ PENDING 提醒 | 只有這條變（失敗 → 通過）。 |
| 4. `content/workshop_text.yaml` 補一筆 `條件.self_stack_at_least.stack` | 這條通過；同檔 `test_table_has_the_164_rewritten_entries` 的筆數 172 → 173 會失敗，要同步改（不是放寬，是表多一筆）。`tests/content/test_no_design_numbers_txt1.py`、`tests/api/test_player_text.py` 仍通過（改寫沒有數字）。 |
