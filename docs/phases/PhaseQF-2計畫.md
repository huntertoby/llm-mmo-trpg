# Phase QF-2 計畫：預告與環境回合不一致（油庫，種子 13502）

> 來源：`docs/phases/PhaseHC-2報告.md` 待決 5。
> `tests/engine/test_environment_turn.py::test_property_telegraph_matches_every_environment_turn_on_demo_maps` 被 hypothesis 抽到油庫、種子 13502，結果失敗。HC-2 的基準 b8803ebb7 上也會失敗，所以不是 HC-2 造成的。
> 小段。**不准放寬斷言。**

## 範圍
1. 用固定參數重現：油庫、種子 13502。找出預告和實際環境回合從哪一步開始不一樣，查出根本原因。
   - 往回查是哪個 commit 開始出錯（例如用 git bisect，或在 X10-2b 前後各跑一次）。也有可能早就存在，只是 hypothesis 一直沒抽到。
2. 修正：預告和實際結果不一致，就修讓它們不一致的程式。
   - 如果是規則問題，例如捨去或兩邊算法不同，先停下來回報，不要自己決定哪一邊才對。
3. 把這組參數加成固定的 `@example`，當回歸測試。

## 驗收
- 修完後，這個 property 測試在固定的例子和 hypothesis 隨機抽樣下都要通過；hypothesis 用 `--hypothesis-seed` 換 3 個種子各跑一次。
- 78 場戰鬥的不變比對：不一樣的場次要逐場說明。照理只有預告文字會變，戰鬥結果不該變。
- ruff、format、mypy、lint-imports 都是 0；交件前跑 engine、cli 的非 slow 測試，再跑 `-m slow tests/cli`。
- 報告寫在 `docs/phases/PhaseQF-2報告.md`，要寫清楚根本原因和從哪個 commit 開始。
