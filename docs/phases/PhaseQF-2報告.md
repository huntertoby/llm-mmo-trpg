# Phase QF-2 報告：油庫種子 13502 的 property 失敗（停下回報）

基準：開工時 `git merge main`（`77033e33a`）。分支 `worktree-agent-a3c16038a3efdeafd`，沒 push。

**結論：預告和實際環境回合沒有不一致，程式沒有錯。** 失敗的是測試最後一行的「不可空轉」檢查，要修只能改測試或改預告規則，兩條都要 PM 決定，所以照派工指示停下，**沒有改任何程式和測試**。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 重現、找根本原因、找起點 | （無程式改動） | 見第 2、3 節 |
| 2 修正 | **未做**，停下回報 | 見第 5 節 |
| 3 `@example` 回歸 | **未做** | 現在加進去一定失敗，要等第 5 節決定 |
| 報告 | 本 commit | |

## 2. 根本原因

重現：油庫、種子 13502、`max_rounds=8`，`run_battle` 產生 33 個動作，第 2 輪就打完。

- 整場只有**一次**環境回合（第 1 輪結束），出現在第 23 個動作（unit_0007 的 EndTurn）裡。
- 這個 EndTurn 的事件，在 `environment_started` 前面是：
  `turn_ended → turn_started(unit_0006) → damage_dealt(燃燒 75，66→0) → unit_downed(unit_0006) → round_ended`
  也就是：輪到 unit_0006 時，回合開始被燃燒燒死，順序走完，直接進環境回合。
- 測試的 docstring 寫明這種情況「預告的前提不成立，該次不比較」（`damage_dealt`、`unit_downed` 不在 `_NON_BOARD_EVENTS`）。所以這次環境回合被跳過，`environment_turns = 0`。
- 戰鬥在第 2 輪、第二次環境回合之前就結束（unit_0007 被打倒），`state.round == 2`。
- 於是最後一行 `assert environment_turns >= 1 or state.round == 1` 不成立。

**預告其實是對的**：我把這次被跳過的環境回合拿來比，EndTurn 之前取得的預告與實際的環境回合事件（去掉 seq）**逐筆相同**（6 格油被點燃、unit_0001 踩到火上燃燒）。燒死的 unit_0006 不在火焰波及的格子，所以剛好不影響結果。

HC-2 報告待決 5 寫的是「斷言不成立」，計畫書寫成「預告和環境回合對不上」，實際上是前者；整段 bisect 範圍內每個測過的 commit，`mismatch` 都是 0。

## 3. 從哪個 commit 開始

用暫時的 git worktree（放在 scratchpad，沒動主 checkout，結束後已 `git worktree remove` 並 prune）手動 bisect，範圍 `37dad65f4`（好）～`77033e33a`（壞），8 步：

- **第一個壞的 commit：`c2ac0d11f` feat(engine): per-unit turn AP, party 4 and elite 4 (AP-1 item 1, #168)**。
- 之前：這場打到第 7 輪、83 個動作，可比較的環境回合 6 次，全部相同。
- 之後：隊伍每回合 4 AP，戰鬥變短，只剩第 2 輪結束、只有那一次被跳過的環境回合。
- 所以不是 X10 系列造成的；AP-1 改了這個種子的戰鬥走向，讓它剛好落進「整場唯一一次環境回合被跳過」的情況。hypothesis 每次只抽 12 例，一直到 HC-2 才抽到。
- 「不可空轉」那行從最早的 `380d033ef`（加 property 測試時）就在，沒改過。

## 4. 檢查

- 沒有改程式和測試，所以沒跑 ruff、format、mypy、lint-imports、測試，也沒跑 78 場比對（不會有差異）。
- 重現與 bisect 用的腳本放在 scratchpad，沒有進 repo。

## 5. 待 PM 決定（1 件）

1. **這個失敗怎麼處理**（不能在「不放寬斷言、只改程式」下修好，因為程式沒錯）：
   - **A. 加強測試，讓被跳過的環境回合也要比**（我傾向這個）：
     - 用 `unittest.mock.patch` 包住 `trpg.engine.turns.run_environment`，在真的環境回合開始前，對當下的狀態取一次預告，再和實際事件比。環境回合的亂數由種子與輪數衍生（`environment_rng`），不受結算中途的 rng 影響，所以這樣取得的預告可以要求逐筆相同。
     - 原本「EndTurn 前的預告」比對完全保留；新增的是「每一次環境回合都要和開始當下的預告相同」，不再有跳過的情況。
     - 但最後那行「不可空轉」要改成數新的比對次數（或兩種合計），對「EndTurn 前預告」這一種來說，種子 13502 仍然是 0 次。**這算不算放寬斷言，要 PM 判斷。**
   - **B. 改預告規則**：預告也要先模擬「本輪還沒行動的單位在回合開始時的效果」（例如燃燒燒死），再跑環境回合。這是規則改動，影響玩家看到的預告，要玩法 PM 決定。
   - **C. 換掉這個種子不處理**：不建議，等於讓 hypothesis 忽略一個真實存在的情況。
   - 不管選哪個，`@example(seed=13502, map_index=1)` 都照計畫加。
