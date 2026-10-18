# Phase 2C-4 完成報告：Phase 2 收尾

分支：`main`（基於 `f296b21`）。範圍：`docs/phases/Phase2C-4計畫.md` 全部 5 個交付項目。沒有調整任何勝率、輪數、技能數值；AI 權重只補上規格給的初值。

## 1. 摘要

- `lava_crossing` 種子 19 的平手修好了；為了讓全部 1,800 場完成度檢查都分出勝負，另外修了三個同類的 AI 僵局（見第 4 節）。**9 設定 × 10 地圖 × 20 種子：exception 0、max_actions 0、draw 0。**
- `brute`／`archer`／`guard` 補上環境權重（`use_environment` 指令對它們終於有作用）。
- 平衡 slow 測試標成 `xfail(strict=False)`；其餘 slow 測試通過。
- 新增 `trpg sim completion`（完成度檢查）與快速／slow 測試。
- 「Phase 2 驗收」13 條：11 條 ✅、2 條 ⚠️（觸發系統的技能層級執行尚未實作，移到補模板 B）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `dfbd145` | Count cover only from enemies in weapon range to fix lava_crossing standoff（3.1） |
| `569adb7` | Add baseline environment weights for brute, archer and guard profiles（3.2） |
| `ae4e96d` | Mark the demo-map balance test as xfail until balance is revisited（3.3） |
| `83852ef` | Measure AI approach by walking distance and ignore concealed enemies for keep_distance（3.4 修正） |
| `666532d` | Release hold_start after three rounds without any HP change（3.4 修正） |
| `b67463e` | Add trpg sim completion: 9 commander configs x maps x seeds completion check（3.4） |
| （下一個） | Document walking-distance approach and concealed keep_distance in ai_profiles.yaml |
| （本報告） | Add Phase 2C-4 report |

## 3. 驗收條件逐條結果

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `scripts/check.py` 五項全過 | ✅ | ruff check、ruff format、mypy、lint-imports、pytest 全通過：1094 passed、7 deselected（slow） |
| 2 | 3.1 根本原因與修法、回歸測試名稱 | ✅ | 第 4.1 節；`tests/engine/test_ai_deadlock.py::test_lava_crossing_seed_19_finishes_with_a_winner`、`test_archers_out_of_range_of_each_other_still_approach`、`test_cover_counts_only_enemies_that_can_reach_the_unit`、`test_a_melee_unit_walks_around_a_chasm_even_though_it_first_gets_farther_away`、`test_walking_distance_falls_back_to_manhattan_when_the_enemy_is_unreachable`、`test_an_archer_steps_within_two_tiles_to_attack_a_concealed_enemy`、`test_keep_distance_still_applies_to_visible_enemies`。已確認掩護的三項（前三項）與隱蔽測試在修正前失敗。`trpg sim maps --maps lava_crossing --seeds 20`：無 draw、無 long_battle |
| 3 | 3.2 三項測試、yaml 數字與表一致 | ✅ | `tests/engine/test_ai_env_weights.py`：`test_every_behavior_profile_has_all_environment_weights`（3 個模式，5 個權重 > 0 且與規格的表逐格相等）、`test_brute_shoves_an_enemy_into_the_chasm_instead_of_a_plain_attack`（推擊分數高於最高的攻擊分數並被選中）、`test_use_environment_order_raises_the_environment_scores`（3 個模式，推下深淵的分數在 ×2 指令下較高） |
| 4 | 3.3 slow 結果；非平衡 slow 全通過 | ✅ | 見第 5.2 節（`pytest -q -m slow`：3 passed、2 xfailed、2 xpassed） |
| 5 | 3.4 摘要表三種異常為 0；slow 與快速測試；確定性與 `--jobs` 無關 | ✅ | 第 5.1 節；`tests/sim/test_completion.py`（快速 6 個、slow 1 個）；`test_completion_output_is_identical_between_runs_and_jobs`；指令證明：`trpg sim completion --maps open_plain,lava_crossing --seeds 2 --jobs 1`（兩次）與 `--jobs 2` 的標準輸出 md5 都是 `dee8a93352587d1aae97af3e1eeccd6a` |
| 6 | 3.5 Phase 2 驗收總表 | ✅ | 第 6 節 |
| 7 | 因 AI 軌跡改變而更新期望值的既有測試 | 見下 | 只有 `tests/cli/test_demo_maps.py` |
| 8 | `trpg battle --log-json` 再 `replay` 一致 | ✅ | 附錄：`frozen_lake` 種子 7 |

**被更新期望值的既有測試（第 7 條）**：只有 `tests/cli/test_demo_maps.py::test_demo_map_battle_has_winner_and_interactions`（`SEEDS` 對照表）。該測試用固定種子要求戰鬥紀錄中出現某些互動字樣，檔案註解本來就寫「AI 或內容改動後種子會漂移，依需要重選」。改動：`bridge_chasm` 6 → 26、`ruined_fort` 42（預設）→ 1；斷言（字樣清單、勝負、環境預告）都沒改。原因：掩護只算射程內的敵人後，吊橋戰與廢墟要塞的舊種子不再出現「命中 −2：矮牆掩護」／「半掩護 -2」；之後環境權重與走路步數的接近距離又改變軌跡，吊橋戰換過兩次種子。其餘 1,094 個測試無須修改。

## 4. 設計與實作說明

### 4.1 `lava_crossing` 平手的根本原因與修法

重現：`trpg battle --map lava_crossing --seed 19`（`sim maps --seeds 20` 報表列出的 draw 種子）。我方戰士與法師在前幾輪陣亡，剩下 **我方弓手（2, 7）** 對 **敵方弓手（6, 1）＋盜賊盾衛（7, 1）**，之後 25 輪每名單位每回合都是「結束回合」。

根本原因：雙方弓手各自躲在半掩護物件後（我方在石柱與矮牆旁，敵方在矮牆 (6, 2) 後），彼此距離 10、都在弓的射程 8 之外。位置價值的 `cover` 權重（弓手 12）算的是「看得到我、且對我形成半掩護的敵人數」，**不管那名敵人打不打得到我**；離開掩護的位置要扣 12，而接近的收益 `approach` 每格只有 1，所以任何接近的移動分數都 ≤ 0。盾衛（守衛）靠 `protect` 跟著弓手，同樣不動。

修法（AI 評分，優先順序第一）：`_covered_from` 只計算「在其武器射程內」的敵人（掩護只在對方打得到自己時才有意義）。沒有加任何「回合到了就強制攻擊」的規則。

### 4.2 為了讓 1,800 場都打得完而追加的三個修正

第一次跑完整的完成度檢查（9 × 10 × 20）出現 5 個 draw，三種根本原因，各自修在 AI 評分或腳本指揮官：

1. **接近距離用曼哈頓距離，繞路的第一步永遠是負分**（4 個 draw：`lava_crossing` 種子 16、18，`bridge_chasm` 種子 0，`cliff_outpost` 種子 13）。橋被燒斷或擊毀後，隔河（深淵、岩漿）的雙方只剩一條繞遠的陸路；近戰單位每繞一步曼哈頓距離就變大，`approach` 為負，永遠不繞。修法：`approach`（含集火目標的 `approach`）改用 **走路步數**：每次決策開始時對每名敵人做一次廣度優先搜尋（只看地形、物件與爬升限制，與移動規則的 `step_cost`／`is_standable` 一致，不看單位），`_Walk` 在同一次決策的 `rank`／`score_action`／虛擬移動之間共用（約 0.15 ms／敵人，`sim maps --maps lava_crossing --seeds 20` 9.0 秒 → 9.5 秒）。動作後的狀態裡敵人若被推開，沿用原位置的步數加上被推開的距離；新出現的單位（召喚物）與完全走不到的敵人退回曼哈頓距離。`keep_distance`、`protect`、`objective` 仍用曼哈頓距離。
2. **`hold_start` 指揮官讓守位永遠不解除**（`ruined_fort`，我方 `hold_start`，3 個種子都平手，種子 10 的敵方 `hold_start` 版本也是）。我方守在起始格，敵方弓手因為站在高處（`height` 15／層）不下來，雙方都不動。修法（腳本指揮官，優先順序第二）：連續 `HOLD_QUIET_ROUNDS = 3` 輪沒有任何單位的 HP 變化就解除守位並且不再下指令。守位只是評分扣分，敵人進入射程時單位本來就會還擊，所以不需要「敵人進入射程」的條件。
3. **兩名隱蔽的弓手互相等待**（`dark_forest`，敵方 `hold_start`，種子 7；解除守位後的殘局）。隱蔽的目標只有 2 格內才能被選為目標，而 `keep_distance` 對 2 格內的每名敵人扣 40，弓手永遠不會走進 2 格去攻擊。修法：`keep_distance` 不計隱蔽的敵人。

### 4.3 環境權重（3.2）

照規格的表補上 `brute`／`archer`／`guard` 的 `env_damage`、`env_kill`、`push`、`surface`、`expose`，`ai_profiles.yaml` 加註解（原則：環境收益約為本身傷害權重的 0.3 倍、環境擊倒約等於本身的擊倒權重；初值未經模擬）。`cunning` 不變。

### 4.4 完成度檢查（3.4）

- 選擇 **子指令** `trpg sim completion [--maps a,b] [--seeds 20] [--seed-start 0] [--jobs N]`（不另寫 `scripts/` 腳本）。實作在 `trpg.sim.completion`（`completion_configs()`、`run_completion()`、`format_completion()`）與 `trpg.cli.sim_completion`。
- 9 種設定：無指揮官、我方 × 4 個指揮官、敵方 × 4 個指揮官（`CompletionConfig`）。90 個（設定, 地圖）各成一個 `BatchSpec`，共用 `run_batches` 的工作行程；結果依種子排序後才彙總。
- 標準輸出只有摘要表與異常清單；執行時間在標準錯誤。有任何 `exception`、`max_actions`、`draw` 時結束碼為 1。
- 測試：快速測試用 `open_plain`、`lava_crossing` × 9 設定 × 1 種子；slow 測試用全部 10 張地圖 × 9 設定 × 3 種子（270 場，`--jobs 2`）。

## 5. 數據

### 5.1 完成度檢查（`trpg sim completion --seeds 20 --jobs 2`，1,800 場，執行時間 446.1 秒）

```
完成度檢查：9 種設定 × 10 張地圖 × 20 個種子（0–19）＝ 1800 場，max_rounds=30
每格：我方勝率／平均輪數／異常數（exception、max_actions、draw）

| 設定 | bridge_chasm | cliff_outpost | dark_forest | frozen_lake | lava_crossing | narrow_halls | oil_depot | open_plain | ruined_fort | swamp |
|---|---|---|---|---|---|---|---|---|---|---|
| 無指揮官 | 80%／4.6／0 | 65%／4.5／0 | 95%／4.3／0 | 85%／5.4／0 | 75%／4.3／0 | 90%／4.0／0 | 50%／5.0／0 | 65%／4.8／0 | 70%／3.9／0 | 65%／4.7／0 |
| 我方 focus_lowest_hp | 80%／4.9／0 | 55%／5.2／0 | 95%／4.0／0 | 90%／5.5／0 | 85%／4.4／0 | 95%／4.0／0 | 50%／5.7／0 | 85%／5.2／0 | 80%／4.2／0 | 80%／4.2／0 |
| 我方 hold_start | 70%／6.5／0 | 50%／6.2／0 | 65%／5.8／0 | 95%／6.5／0 | 70%／5.8／0 | 85%／5.8／0 | 55%／6.3／0 | 40%／5.1／0 | 80%／9.6／0 | 95%／4.9／0 |
| 我方 protect_weakest | 75%／5.5／0 | 70%／5.0／0 | 80%／4.5／0 | 90%／5.3／0 | 90%／5.0／0 | 85%／5.0／0 | 50%／5.1／0 | 70%／4.8／0 | 90%／4.0／0 | 80%／4.4／0 |
| 我方 use_env | 85%／4.3／0 | 70%／4.5／0 | 90%／4.7／0 | 95%／5.6／0 | 85%／4.9／0 | 90%／3.9／0 | 40%／5.0／0 | 70%／4.7／0 | 60%／3.8／0 | 65%／4.8／0 |
| 敵方 focus_lowest_hp | 80%／4.5／0 | 55%／5.0／0 | 95%／4.7／0 | 80%／5.4／0 | 90%／4.0／0 | 85%／4.0／0 | 35%／5.7／0 | 55%／5.3／0 | 65%／3.9／0 | 65%／4.5／0 |
| 敵方 hold_start | 85%／6.0／0 | 100%／4.7／0 | 100%／3.2／0 | 100%／4.7／0 | 75%／5.1／0 | 100%／3.4／0 | 95%／5.0／0 | 100%／5.0／0 | 95%／4.2／0 | 100%／2.5／0 |
| 敵方 protect_weakest | 85%／4.8／0 | 80%／4.8／0 | 95%／4.2／0 | 95%／4.7／0 | 80%／4.0／0 | 95%／3.5／0 | 50%／5.2／0 | 65%／5.0／0 | 75%／4.0／0 | 75%／4.4／0 |
| 敵方 use_env | 80%／4.7／0 | 65%／4.5／0 | 95%／4.0／0 | 90%／5.3／0 | 85%／4.2／0 | 95%／4.2／0 | 50%／5.2／0 | 70%／4.6／0 | 70%／4.0／0 | 65%／4.7／0 |

異常合計：exception 0、max_actions 0、draw 0 —— 通過
```

勝率與輪數只記錄、不調整。`我方 use_env` 與 `敵方 use_env` 的列現在和「無指揮官」不同（以前對非狡猾型的單位是空操作）。

### 5.2 `uv run pytest -q -m slow`（136.6 秒）

| 測試 | 結果 |
|---|---|
| `tests/sim/test_skill_fuzz.py::test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible` | passed |
| `tests/skillgen/test_random_composer.py::test_one_thousand_seeds_are_all_valid_and_spread_out` | passed |
| `tests/sim/test_completion.py::test_every_map_and_config_completes_without_exception_max_actions_or_draw` | passed |
| `tests/engine/test_demo_balance.py::test_demo_map_win_rate_and_length[bridge_chasm]` | xfailed |
| `tests/engine/test_demo_balance.py::test_demo_map_win_rate_and_length[ruined_fort]` | xfailed |
| `tests/engine/test_demo_balance.py::test_demo_map_win_rate_and_length[oil_depot]` | xpassed |
| `tests/engine/test_demo_balance.py::test_demo_map_win_rate_and_length[swamp]` | xpassed |

xfail reason：「平衡延後到效果模板補齊之後；目標勝率 35–65%、平均輪數 4–6」。斷言本身沒有改。與 2C-3 時「3 個已知失敗」比，AI 修正後 `oil_depot`、`swamp` 剛好落在區間內（XPASS），但這是 AI 改動的副作用，不代表平衡完成。

### 5.3 build × 地圖類型矩陣（`trpg sim matrix --seeds 20 --jobs 2`，1,200 場，290.8 秒；僅記錄）

#### 勝率矩陣（地圖類型內有多張地圖時取平均）
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 62.5% | 25.0% | 70.0% | 70.0% | 80.0% | 95.0% | 70.0% | 90.0% |
| build_fire | 82.5% | 55.0% | 70.0% | 80.0% | 100.0% | 90.0% | 80.0% | 90.0% |
| build_storm | 95.0% | 40.0% | 80.0% | 77.5% | 100.0% | 90.0% | 70.0% | 80.0% |
| build_tank | 57.5% | 25.0% | 75.0% | 67.5% | 90.0% | 90.0% | 80.0% | 80.0% |
| build_ranged | 77.5% | 35.0% | 65.0% | 80.0% | 95.0% | 100.0% | 50.0% | 50.0% |
| build_assassin | 57.5% | 15.0% | 65.0% | 72.5% | 90.0% | 95.0% | 45.0% | 75.0% |

#### build 英雄 DPR 矩陣
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 6.85 | 6.61 | 9.19 | 5.21 | 6.49 | 6.85 | 6.79 | 8.38 |
| build_fire | 18.17 | 20.35 | 13.51 | 15.28 | 14.82 | 16.61 | 17.53 | 12.40 |
| build_storm | 20.03 | 20.35 | 43.65 | 14.78 | 16.98 | 16.14 | 20.45 | 11.32 |
| build_tank | 5.15 | 6.33 | 7.85 | 4.87 | 5.01 | 5.69 | 7.44 | 4.98 |
| build_ranged | 13.14 | 12.15 | 11.42 | 11.00 | 10.34 | 13.26 | 12.87 | 8.83 |
| build_assassin | 6.75 | 6.95 | 8.58 | 5.61 | 6.24 | 5.23 | 7.66 | 7.87 |

#### 排名矩陣（* ＝ 前段，前 2 名）
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake | 前段次數 |
|---|---|---|---|---|---|---|---|---|---|
| build_push | 4 | 4 | 4 | 5 | 6 | 2* | 4 | 2* | 2 |
| build_fire | 2* | 1* | 3 | 1* | 2* | 4 | 1* | 1* | 6 |
| build_storm | 1* | 2* | 1* | 3 | 1* | 5 | 3 | 3 | 4 |
| build_tank | 6 | 5 | 2* | 6 | 5 | 6 | 2* | 4 | 2 |
| build_ranged | 3 | 3 | 5 | 2* | 3 | 1* | 5 | 6 | 2 |
| build_assassin | 5 | 6 | 6 | 4 | 4 | 3 | 6 | 5 | 0 |

#### 6.8 標準檢查
1. 沒有任何 build 在所有地圖類型都排名前段：通過
2. 每個 build 至少在一種地圖類型排名前段：不通過：build_assassin

2C-3 時不通過標準 2 的是 build_tank（前段 0 次）；AI 修正後變成 build_assassin（前段 0 次）。數字全面漂移（例如 `oil_depot` 各 build 勝率 15–55%），2C-3 的矩陣已經過時，平衡階段請重跑。

## 6. Phase 2 驗收（對照 `docs/專案計畫.md` 第 14 節）

| # | 項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 原語、形狀、條件、代價、觸發的資料檔 | ⚠️ | 原語 `content/skill_primitives.yaml`、形狀 `skill_shapes.yaml`、條件 `skill_conditions.yaml`、代價（法力、冷卻、HP）在技能的 `cost` 與 `skill_budget.yaml`，另有 `skill_exclusions.yaml`、`skill_synergies.yaml`、`skill_composer.yaml`、`skeletons/`；測試 `tests/content/test_skill_rules_content.py`、`test_skill_composer_content.py`、`test_skills_content.py`（`uv run pytest -q tests/content` 全通過）。**觸發**：事件 → 效果的觸發對照表（`trpg.engine.triggers`、`content/reactions.yaml`、`content/interactions.yaml`）已實作並由資料驅動；**技能層級的觸發**（`passive`／`reaction`／`stance` 骨架的 `on_hit` 等時機）schema 可表示，但骨架被停用、戰鬥中不執行（`test_disabled_skeletons_are_rejected`）。缺的部分移到補模板 B |
| 2 | 技能 JSON 解譯執行 | ✅ | `tests/engine/test_skill_primitives.py`、`test_skill_shapes.py`、`test_skill_conditions.py`、`test_skill_scenarios.py`、`test_skill_decisions.py`、`test_skill_determinism.py`；23 個示範技能 `test_every_demo_skill_passes_validation` |
| 3 | 預算計算 | ✅ | `tests/skillgen/test_budget.py`：`test_hand_case_1_weapon_skill` … `_7_synergy_stack_and_debuff`（`Fraction` 精確相等的手算案例）、`test_shape_multiplier_table`、`test_ap_coefficients_and_reaction` |
| 4 | 硬性上限與互斥規則 | ✅ | `tests/skillgen/test_validate.py`：`test_more_than_four_effects_are_rejected`、`test_push_and_pull_are_capped_at_two_tiles`、`test_at_most_one_rule_rewrite_primitive`、`test_exclusion_1_…` 到 `test_exclusion_6_…`（6 條互斥規則）、`test_common_skills_cannot_use_rarer_content` |
| 5 | 隨機組合器（不用 LLM） | ✅ | `tests/skillgen/test_random_composer.py`（含 slow `test_one_thousand_seeds_are_all_valid_and_spread_out`，passed）；`trpg skills random --seed N` |
| 6 | 批次模擬器 | ✅ | `tests/sim/test_batch.py`（含報表與 `--jobs` 無關）；`trpg sim maps`、本階段的 `trpg sim completion`（1,800 場） |
| 7 | 第一批 8 種地圖類型、10–15 張手工地圖 | ✅ | `trpg map list`：10 張非測試地圖，類型 bridge_chasm、ruined_heights、forest、frozen_lake、corridor、oil_depot、open_plain、swamp（共 8 種）；`tests/content/test_map_archetypes.py` |
| 8 | 效用 AI 的戰術指令接口與控制分派（腳本指令測試） | ✅ | `tests/engine/test_orders.py`（約 19 項：指令 schema、控制分派優先順序、5 種指令對評分的影響、無效指令等同沒有指令、指令寫入紀錄與重播）、`tests/sim/test_commanders.py`；4 個腳本指揮官 × 全部地圖的完成度檢查（5.1） |
| 9 | 驗收：隨機 1,000 個技能全部可執行且無例外 | ✅ | `uv run python scripts/skill_fuzz.py --count 1000 --seed-start 0`（實際重跑，19 秒）：組合成功 1000/1000、通過驗證 1000/1000、可施放 1000/1000、AI 對戰 100 場（我方勝 98／敵方勝 2／平手 0）、例外 0 個；slow 測試 `test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible` passed |
| 10 | 驗收：超預算與違規者被拒 | ✅ | `tests/skillgen/test_validate.py::test_over_budget_is_rejected_with_the_ratio`、`test_too_weak_is_rejected_with_the_ratio`、`test_budget_boundaries_are_inclusive`、`test_exclusion_*`、`test_disabled_skeletons_are_rejected` |
| 11 | 驗收：觸發深度上限生效 | ⚠️ | 目前有的是效果佇列的連鎖深度上限 `max_chain_depth`（環境連鎖、爆炸、表面、雷電傳導等一切入列的效果）：`tests/engine/test_effects.py::test_chain_limit`、`tests/engine/test_environment.py::test_chain_reaction_stops_at_depth_limit`；指標與報表會列出 `chain_limit` 異常（`tests/sim/test_batch.py::test_chain_limit_boss_burst_and_one_shot_anomalies`）。技能層級的觸發（被動、反應技）尚未實作，所以「技能觸發的深度上限」沒有東西可測，移到補模板 B |
| 12 | 驗收：模擬報表產出 DPR、控制回合、異常清單 | ✅ | `trpg sim maps --maps oil_depot --seeds 5` 的輸出含「陣營 DPR」「單位範本 DPR」「控制回合」「技能使用」「異常」各表；`tests/sim/test_batch.py`、`test_metrics.py`、`test_skill_report.py`（`trpg sim skills`：技能 DPR 分佈與離群） |
| 13 | 驗收：build × 地圖類型矩陣 | ✅ | `trpg sim matrix --seeds 20 --jobs 2`（實際重跑，5.3 節）：勝率、英雄 DPR、排名矩陣與 6.8 兩條標準；`tests/sim/test_matrix.py`。標準 2 在資料上不通過（build_assassin），這是平衡問題，不是功能缺漏 |

## 7. 待 PM 決定

1. **接近距離改為走路步數（4.2-1）是比規格預期更大的 AI 改動**：影響所有地圖的軌跡（但沒有改引擎規則）。這是修好橋被燒斷後的僵局的唯一原則性做法；若你偏好更窄的修法（例如只在「沒有任何接近動作為正」時才改用走路步數），請告知。步數不計爬升成本，也不看單位。
2. **`keep_distance` 不計隱蔽的敵人（4.2-3）**：副作用是弓手也會走進隱蔽近戰敵人的 2 格內。目前只有 `dark_forest` 與草叢相關。
3. **掩護只算射程內的敵人（4.1）**：弓手不再因為「遠方有敵人看得到我而我有掩護」而偏好某格；`bridge_chasm` 的「命中 −2：矮牆掩護」字樣因此少了很多（示範測試的種子要重選，見第 3 節）。
4. **`hold_start` 的解除條件**：連續 3 輪全場 HP 總和不變。常數 `HOLD_QUIET_ROUNDS = 3` 未經調整。其他三個指揮官沒有被改。
5. **3.2 環境權重的實際效果未經模擬**：只用單元情境證明 ×2 指令有作用。完成度表中 `use_env` 列和無指揮官列確實不同，但沒有做 A/B。
6. **2C-3 之後所有勝率表已過時**：`oil_depot` 現在約 50%（2C-3 為 45%，各 build 15–55%），`lava_crossing` 75%（2C-3 為 90%），`ruined_fort` 70%（85%）。平衡階段請重跑 `sim maps`、`sim matrix`、`sim skills`。
7. **demo-balance 的 xfail**：`oil_depot`、`swamp` 現在 XPASS（`strict=False`，不會失敗）。平衡階段完成後請移除 xfail。
8. **完成度檢查採子指令而非腳本**；`tests/sim/test_completion.py` 的快速測試合計約 30 秒（最慢的是三次完成度檢查的 `--jobs` 比較），整套預設測試時間因此增加約半分鐘。若覺得太慢可把 `test_completion_output_is_identical_between_runs_and_jobs` 改成 slow。
9. **Phase 2 驗收 #1、#11 標 ⚠️**：技能層級的觸發系統（`on_hit` 等）尚未實作，不為了打勾而實作。請決定是否排入補模板 B。
10. **`trpg sim completion` 的退出碼**：有異常時為 1（與 `scripts/skill_fuzz.py` 一致）。若 CI 需要別的行為請告知。

## 8. 給補模板 A 的備註

- **走路步數在決策開始時算一次**：技能若在同一次決策內建立或摧毀障礙（`create_obstacle`、`destroy_object`、`raise_terrain`、`lower_terrain`），該決策內的預覽仍用決策開始時的步數（下一次決策才會更新）。若補模板 A 的保護／阻擋型模板大量改變地形，可考慮在 `score_action` 對這類技能改用預覽後狀態重算（`_Walk` 已經可獨立建構）。
- **`protect`、`defend`、`status_values` 與環境權重（3.2）全是初值**：補保護型模板（build_tank 沒有前段類型的原因）後，需要重新檢查守衛的 `protect` 權重與 `defend` 的價值；`use_environment` 指令現在對所有行為模式生效，環境類模板（推擊、表面、爆炸）的 AI 價值會同時受 3.2 權重與指令影響。
- **`cover` 只算射程內的敵人**：若新模板提高射程（例如長射程法術），掩護的吸引力範圍會隨敵方射程改變。
- **完成度檢查是新模板的守門員**：每次補模板後跑 `trpg sim completion --seeds 3 --jobs 2`（約 1 分鐘）；`draw` 出現時先用 `trpg battle --map … --seed … --ally-commander …` 找出剩下的單位為什麼沒有正分的動作（本階段的三種原因都是「單步評分看不到兩步以上的計畫」）。

## 9. 附錄：代表性的 CLI 輸出節錄

`trpg battle --map frozen_lake --seed 7 --log-json /tmp/fl7.json`：

```
勝方：我方勝利（第 5 輪結束，99 個動作，389 個事件）
```

`trpg battle replay /tmp/fl7.json`：

```
重播驗證通過：99 個動作、389 個事件，最終狀態一致（frozen_lake，種子 7）。
```

`trpg sim completion --maps open_plain,lava_crossing --seeds 2`（節錄，`--jobs 1` 與 `--jobs 2` 輸出的 md5 相同）：

```
完成度檢查：9 種設定 × 2 張地圖 × 2 個種子（0–1）＝ 36 場，max_rounds=30
每格：我方勝率／平均輪數／異常數（exception、max_actions、draw）

| 設定 | open_plain | lava_crossing |
|---|---|---|
| 無指揮官 | 100%／5.5／0 | 50%／2.5／0 |
| 我方 hold_start | 100%／4.5／0 | 100%／4.0／0 |
...
異常合計：exception 0、max_actions 0、draw 0 —— 通過
```
