# Phase KW-1b 完成報告｜修 KW-1 合併後全量檢查的 4 條失敗

> 基準：main `f49912db6`（worktree 原本在 `aea340f2c`，開工前 fast-forward）。

## 1. 預測（動手前寫下）

| 修法 | 預測會變的測試／快照 |
|---|---|
| 1. `trpg llm propose` 的關鍵字輪替改用 `start_ids()`（`--keywords` 指定時仍接受全部關鍵字） | `test_mock_n3_snapshot` 通過且**快照不重產**：`rng.choice` 在 12 個與 16 個裡取同一個索引時，前 12 個順序一樣，原本抽到 `concealed`、`summon`、`poisoned` 的那幾次會回到原樣。`tests/llm/test_prompt_prefix.py`（同樣 `count=3, seed=0`）仍通過。其他快照不變。 |
| 2. `test_summons_e1.py` 灌注表測試改看 `start_ids()` ＋ PENDING 提醒 | 只有這條變（失敗 → 通過）。 |
| 3. `test_form_start.py` 開局池 ≥ 3 改看 `start_ids()` ＋ PENDING 提醒 | 只有這條變（失敗 → 通過）。 |
| 4. `content/workshop_text.yaml` 補一筆 `條件.self_stack_at_least.stack` | 這條通過；同檔 `test_table_has_the_164_rewritten_entries` 的筆數 172 → 173 會失敗，要同步改（不是放寬，是表多一筆）。`tests/content/test_no_design_numbers_txt1.py`、`tests/api/test_player_text.py` 仍通過（改寫沒有數字）。 |

## 2. 每條的修法

1. **`tests/cli/test_llm_propose_cli.py::test_mock_n3_snapshot`——修程式，快照不變。**
   判斷：該排除。`trpg llm propose` 的輪替題目是模擬遊戲裡會出的 LLM 題目；KW-1 的 `start_hidden` 已經讓三選一的新方向、許願池、開局都不出這四個關鍵字，而且新條件 `self_stack_at_least` 是 `handwritten_only`、不在 LLM schema，組合器也做不出（`composable: false`）。輪替抽到它們只會量到遊戲裡不會出現的題目。
   改法：`src/trpg/cli/llm.py::propose_requests` 輪替改抽 `library.keywords.start_ids()`；`--keywords` 明確指定時仍接受全部關鍵字（未知關鍵字檢查照舊用 `ids()`）。KW-2 拿掉 `start_hidden` 時輪替自動恢復成全部（屆時這個快照會照預期改變，要重產）。
2. **`tests/engine/test_summons_e1.py::test_the_infusion_table_covers_all_ten_keywords`——縮小範圍＋PENDING 提醒。**
   改看 `start_ids()` 減中毒、形態 ＝ 十個灌注關鍵字；前面加 `set(ids()) - set(start_ids()) == PENDING`（四個層數關鍵字）。
3. **`tests/roguelite/test_form_start.py::test_the_form_start_pool_holds_only_the_tier_one_forms`——縮小範圍＋PENDING 提醒。**
   「其他池 ≥ 3 招」只對 `start_ids()` 裡的池檢查；前面加 `set(starter_pools) - start_ids() == PENDING`。
4. **`tests/skillgen/test_workshop_feedback.py::test_every_dev_text_has_a_player_rewrite_and_every_rewrite_is_used`——補玩家改寫，斷言不動。**
   `content/workshop_text.yaml` 加一筆（放在 `條件.self_hp_below` 後）：
   - id：`條件.self_stack_at_least.stack`
   - source：層數 ID（stacks.yaml，只能是累積在自己身上的）
   - player：**要看哪一種層數；只能選累積在你自己身上的（例如連擊點、怒氣、專注、氣），疊在敵人身上的不行。**（實作者初稿，請玩法 PM 確認）
   同檔 `test_table_has_the_164_rewritten_entries` 筆數 172 → 173，註解加一行。

**PENDING 提醒確實會失敗**：暫時把 `skill_keywords.yaml` 四個 `start_hidden: true` 改成 `false` 跑第 2、3 條，兩條都在提醒那一行失敗（`set() == {...}`），之後已還原。

## 3. 縮小範圍的測試清單與檢查數

| 測試 | 範圍前 | 範圍後 | 恢復時機 |
|---|---|---|---|
| `test_summons_e1.py::test_the_infusion_table_covers_all_ten_keywords` 第二個斷言 | 16 個關鍵字（扣中毒、形態後 14 個比對灌注表） | 12 個（扣中毒、形態後 10 個） | KW-2 拿掉 `start_hidden`：PENDING 斷言失敗，要決定這四個灌注不灌注 |
| `test_form_start.py::test_the_form_start_pool_holds_only_the_tier_one_forms` 「其他池 ≥ 3」 | `starter_pools` 全部的池（16 個裡有池的） | 只看 12 個開局關鍵字的池 | 同上 |

（第 1 條改的是程式、第 4 條是補資料，都沒縮小測試範圍。）

## 4. 預測與實際

| 預測 | 實際 |
|---|---|
| `test_mock_n3_snapshot` 通過、快照不重產 | 一致：通過，`tests/cli/snapshots/` 沒有 diff |
| `tests/llm/test_prompt_prefix.py` 仍通過 | 一致 |
| 第 2、3 條只有自己變 | 一致 |
| 第 4 條通過；`test_table_has_the_164_rewritten_entries` 172 → 173 失敗要同步改 | 一致：先失敗（`173 == 172`），改筆數後 26 passed |
| `test_no_design_numbers_txt1.py`、`test_player_text.py` 仍通過 | 一致 |

## 5. 同類問題再掃一次

列出 `tests/` 下所有會枚舉關鍵字的測試檔（內容含 `keywords.ids/start_ids/keywords/by_id`、`keyword_pools(`、`starter_pools(`、`skill_keywords`、`KEYWORDS`、迴圈走關鍵字，或檔名含 keyword／wish／candidat／_start／whiteboard／infusion／sample），共 67 個檔，含 slow（`test_skill_infusion.py`、`test_candidates.py`、`test_evolution.py`、`test_upgrade_topup.py` 有 slow 標記）：
`uv run pytest -q -m "not llm" -n 8 <67 個檔>` → **1977 passed、13 skipped、0 failed（結束碼 0）**。沒有找到其他同類失敗。

## 6. 檢查與結束碼

| 檢查 | 結束碼 / 結果 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0（1586 個檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（672 個檔、412 個技能） |
| 4 條＋相關檔（`test_llm_propose_cli`、`test_summons_e1`、`test_form_start`、`test_workshop_feedback`、`test_prompt_prefix`、`test_no_design_numbers_txt1`、`test_player_text`） | 0 |
| 枚舉關鍵字的 67 個檔（含 slow，`-n 8`） | 0：1977 passed、13 skipped |

沒有跑全量 `check.py`；沒有改引擎，沒有跑戰鬥重播。

## 7. 待 PM 決定

1. 第 4 條的玩家改寫（第 2 節）請玩法 PM 確認或改字。
2. KW-2 拿掉 `start_hidden` 時：第 2 條要決定四個層數關鍵字有沒有召喚灌注（06 6.27.1）；`trpg llm propose` 的 Mock 快照屆時會變，要重產。

## 開發 PM 裁定

- 接受，已合併。第 2、3 條縮小檢查範圍，比照專案 PM 對 KW-1 的同意：PENDING 提醒已實測，拿掉 start_hidden 時會失敗。第 1、4 條沒有縮小範圍。
- 第 4 條的玩家改寫轉交玩法 PM 確認，列在 `docs/開發PM交接.md` 3.0001。
- KW-2 派工時要寫明三件事：
  - 灌注表要決定層數關鍵字有沒有召喚灌注；
  - 重產 llm propose 的 Mock 快照；
  - 列出恢復前後各檢查了幾個關鍵字。
