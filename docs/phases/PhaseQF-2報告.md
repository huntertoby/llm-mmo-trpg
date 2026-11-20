# Phase QF-2 報告：油庫種子 13502 的 property 失敗

基準：開工時 `git merge main`（`77033e33a`）。分支 `worktree-agent-a3c16038a3efdeafd`，沒 push。

**結論：預告和實際環境回合沒有不一致，引擎程式沒有錯。** 失敗的是測試最後一行「不可空轉」的檢查。第一次交件時停下回報，PM 選 A（加強測試），本段照做。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 重現、根本原因、起點 | `99167df53`（只有報告） | 見第 2、3 節 |
| 2 加強測試（PM 選 A） | 本 commit | 見第 4 節 |
| 3 `@example(seed=13502, map_index=1)` | 本 commit | 固定回歸例 |
| 報告 | 本 commit | |

PM 指示 2、3 和報告更新做成一個 commit。

## 2. 根本原因

重現：油庫、種子 13502、`max_rounds=8`，`run_battle` 產生 33 個動作，第 2 輪就打完。

- 整場只有**一次**環境回合（第 1 輪結束），出現在第 23 個動作（unit_0007 的 EndTurn）裡。
- 這個 EndTurn 的事件，在 `environment_started` 前面是：
  `turn_ended → turn_started(unit_0006) → damage_dealt(燃燒 75，66→0) → unit_downed(unit_0006) → round_ended`
  也就是：輪到 unit_0006 時，回合開始被燃燒燒死，順序走完，直接進環境回合。
- 測試原本的規則是：EndTurn 之後、環境回合之前有改變戰場的事件，「EndTurn 前的預告」前提就不成立，該次不比較。所以這次被跳過，比較次數 = 0。
- 戰鬥在第 2 輪、第二次環境回合之前就結束，`state.round == 2`。
- 舊的最後一行 `assert environment_turns >= 1 or state.round == 1` 因此不成立。

**預告其實是對的**：我把被跳過的這次拿來比，EndTurn 前的預告與實際事件（去掉 seq）**逐筆相同**。燒死的單位不在火焰波及的格子，所以剛好不影響。

HC-2 報告待決 5 寫的是「斷言不成立」，計畫書寫成「預告和環境回合對不上」，實際上是前者。

## 3. 從哪個 commit 開始

用暫時的 git worktree（放在 scratchpad，沒動主 checkout，結束後已 `git worktree remove`、prune，bisect 已 reset）手動 bisect。範圍是 `37dad65f4`（好）～`77033e33a`（壞），共 8 步。

- **第一個壞的 commit：`c2ac0d11f` feat(engine): per-unit turn AP, party 4 and elite 4（AP-1 item 1，#168）**。
- 之前：這場打到第 7 輪、83 個動作，可比較的環境回合 6 次，全部相同。
- 之後：隊伍每回合 4 AP，戰鬥變短，只剩那一次被跳過的環境回合。
- 每個測過的 commit，預告與實際不一致的次數都是 0。和 X10 系列、HC-2 都無關；是 AP-1 改了這個種子的戰鬥走向，hypothesis 每次只抽 12 例，到 HC-2 才抽到。
- 「不可空轉」那行從 `380d033ef`（加 property 測試時）就在，沒改過。

## 4. 新舊斷言的差別

檔案：`tests/engine/test_environment_turn.py`，`test_property_telegraph_matches_every_environment_turn_on_demo_maps`。

| | 舊 | 新 |
|---|---|---|
| EndTurn 前的預告 | 沒跳過的環境回合要逐筆相同 | **完全保留**，同樣要逐筆相同 |
| 環境回合開始當下的預告 | 沒有 | **每一次**實際環境回合都要逐筆相同，沒有例外 |
| 每次結算的數量檢查 | 沒有 | 「當下預告」的筆數 = `environment_started` 筆數 = `environment_ended` 筆數 |
| 最後一行 | `environment_turns >= 1 or state.round == 1`（只數沒跳過的） | `late_compared == actual_turns`，且 `late_compared >= 1 or state.round == 1` |
| 固定例 | 無 | `@example(seed=13502, map_index=1)` |

- 「當下取預告」的做法：用 `mock.patch("trpg.engine.turns.run_environment", ...)` 包住引擎唯一一個環境回合的呼叫點。在真正的環境回合之前，先對當下的戰鬥狀態跑 `telegraph()`，再呼叫原本的 `run_environment`。
- 環境回合的亂數是由種子與輪數算出來的（`environment_rng`），不受結算中途的亂數影響，所以可以要求逐筆相同。
- 沒有放寬：舊的比對全部還在；新的比對涵蓋每一次環境回合；最後一行改成「每一次都比到」，而且至少 1 次。

## 5. 檢查

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0 |
| `lint-imports` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（沒有新增數字） |
| `pytest tests/engine/test_environment_turn.py` | 0（9 passed，含固定例） |
| property，`--hypothesis-seed=1` | 0 |
| property，`--hypothesis-seed=20261120` | 0 |
| property，`--hypothesis-seed=987654321` | 0 |
| `pytest tests/engine -m "not slow" -n 8` | 0（5120 passed） |

- 78 場不變比對沒跑：只改測試，引擎程式沒動，戰鬥結果不會變。
- PM 這輪只要求 engine，`tests/cli` 的非 slow 和 slow 都沒跑（理由同上）。

## 6. 待 PM 決定

- 無。
