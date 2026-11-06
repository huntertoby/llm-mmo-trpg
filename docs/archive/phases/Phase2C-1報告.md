# Phase 2C-1 完成報告：批次模擬器與報表

> 實作者撰寫｜對應 `docs/phases/Phase2C計畫.md` 第 3 節

## 1. 摘要

- 兩項規則小改先完成：代價折抵加總上限 `total_cap: 500`（`trpg skills budget` 顯示截斷）；組合器的調參常數搬到 `content/skill_composer.yaml`（pydantic schema、`ContentLibrary.composer`），`skill_fuzz.py --count 1000` 的摘要搬移前後 `cmp` 逐字相同。
- 新增 `trpg.sim.metrics`（單場指標：傷害歸屬、DPR、控制回合、擊倒、治療、技能使用、AP、異常原始數據）與 `trpg.sim.batch`（`BatchSpec`／`run_batch(es)`／`BatchReport`／7 種異常偵測／文字與 JSON 報表），支援多行程，報表與 `--jobs` 無關。
- 新增 `trpg sim maps [--maps] [--seeds] [--seed-start] [--jobs] [--json]`；`scripts/sim_demo_maps.py` 改為它的薄包裝。
- `scripts/check.py` 五項全過（973 個測試，另有 6 個 slow 預設不跑）。`--seeds 20`（4 張示範地圖、80 場）：`--jobs 1` 約 55–59 秒、`--jobs 4` 約 33–35 秒（2 核心機器）；標準輸出兩次執行、`--jobs 1` 與 `--jobs 4` 逐字相同。數字只列出、沒有調整。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `eef6c06` | 3.1-1：`allowance.total_cap: 500`、`BudgetReport.allowance_raw_permille／allowance_permille／allowance_capped`、`trpg skills budget`（單一技能與 `--all`）顯示截斷與測試 |
| `87a3ac4` | 3.1-2：`content/skill_composer.yaml`、`trpg.content.composer_rules.ComposerRules`、組合器改讀資料、`tests/content/test_skill_composer_content.py` |
| `f3b5d26` | 3.3：`trpg.sim.metrics` 與 `tests/sim/test_metrics.py` |
| `f5d4e8c` | 3.2、3.4、3.5：`trpg.sim.batch`、`trpg sim maps`、`scripts/sim_demo_maps.py` 薄包裝、`tests/sim/test_batch.py`、`tests/cli/test_sim_cli.py`、`tests/test_sim_scripts.py` |
| `4446401`、`69b219e` | 墜落／致命地形的傷害來源追溯（強制位移→行動者；橋被打壞→最後打到橋的單位）、致命地形不計入 `one_shot`、報表加「每場平均動作數」 |
| （本報告） | `docs/phases/Phase2C-1報告.md` |

## 3. 驗收條件逐條結果

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `scripts/check.py` 五項全過 | ✅ | ruff check、ruff format、mypy、lint-imports、pytest 全部通過（973 個測試，另有 6 個 slow 預設不跑） |
| 2 | 折抵加總截斷在 +500‰；`budget --all` 顯示截斷；列出受影響的示範技能；fuzz 1,000 個全過 | ✅ | `tests/skillgen/test_budget.py::test_hand_case_6_cost_allowance_caps`（各項上限後加總 900 → 500）、`test_total_allowance_cap_comes_from_skill_budget_yaml`、`test_allowance_below_the_total_cap_is_untouched`、`test_total_allowance_cap_applies_after_each_part_cap`；`tests/cli/test_budget_cli.py::test_budget_shows_when_the_allowance_is_capped`（單一技能「代價折抵 +850‰ → 上限 +500‰」，`--all` 欄位「+850→500」）。**受影響的示範技能：0 個**（23 個示範技能的折抵最高 +220‰，見 5.1）。`skill_fuzz.py --count 1000`：組合成功 1000/1000、通過驗證 1000/1000、可施放 1000/1000、例外 0（5.2） |
| 3 | `skill_composer.yaml` 有 schema 與載入測試；搬移前後 fuzz 摘要 `cmp` 相同 | ✅ | `tests/content/test_skill_composer_content.py`（載入、階梯由資料導出、7 種錯誤資料被拒絕、缺檔案是 `ContentError`）；搬移前（已含折抵上限）與搬移後的 `skill_fuzz.py --count 1000` 摘要 `cmp` → 無輸出（逐字相同，見 4.2、5.2） |
| 4 | `battle_metrics` 單元測試：傷害歸屬、DPR、控制回合、擊倒數逐項核對 | ✅ | `tests/sim/test_metrics.py`：`test_damage_is_attributed_to_sources_and_split_into_direct_and_indirect`、`test_dpr_divides_by_the_rounds_the_unit_was_in_the_battle`、`test_kills_credit_the_last_damage_source_and_healing_the_healer`、`test_control_turns_are_attributed_to_the_last_applier`、`test_skill_usage_attribution_follows_the_skill_until_the_next_attack`（手工事件序列，數值手算）；`test_real_battle_totals_are_consistent_with_the_event_log`（固定種子的真實戰鬥：承受傷害＝事件加總、可追溯傷害＝造成＋誤傷、擊倒數、回合數、AP） |
| 5 | 每種異常至少一個觸發情境 | ✅ | `tests/sim/test_batch.py`：`exception`＝`test_an_exception_in_one_battle_is_recorded_and_the_batch_continues`（policy 丟例外，只取最後一行）；`max_actions`＝`test_max_actions_is_reported_with_the_seed`（`max_actions=5`）；`draw`＝`test_draw_when_the_round_limit_is_reached`（一律結束回合、`max_rounds=2`）；`long_battle`＝`test_long_battle_when_more_than_ten_rounds`（12 輪）；`chain_limit`、`boss_burst`、`one_shot`＝`test_chain_limit_boss_burst_and_one_shot_anomalies`（含 one_shot 只列前 5 個種子）；另在 `tests/sim/test_metrics.py`：`test_anomaly_raw_data_boss_burst_chain_limit_and_result`、`test_boss_downed_in_round_one_is_a_burst_otherwise_each_action_is_checked`、`test_one_shot_counts_actions_that_remove_a_non_boss_units_whole_hp`、`test_periodic_damage_is_not_part_of_the_single_action_damage`、`test_deadly_terrain_is_a_designed_kill_so_it_is_not_a_one_shot_but_can_burst_a_boss` |
| 6 | 確定性：同 `BatchSpec` 兩次相等；`--jobs 1` 與 `--jobs 2` 相等 | ✅ | `test_same_spec_twice_gives_equal_reports`、`test_report_does_not_depend_on_the_number_of_jobs`（2 張地圖 × 3 種子，`jobs=1` 與 `jobs=2` 的報表與文字完全相等）、`test_seed_order_in_the_spec_does_not_change_the_report`；CLI：`tests/cli/test_sim_cli.py::test_stdout_is_identical_across_runs_and_jobs` |
| 7 | 附 `--seeds 20` 完整標準輸出與 `--jobs 1`／`--jobs 4` 執行時間 | ✅ | 附錄 8.1；`--jobs 1`：54.8–58.7 秒；`--jobs 4`：33.2–35.5 秒（`cmp` 確認兩者標準輸出相同、再跑一次也相同） |

## 4. 設計與實作說明

### 4.1 代價折抵上限（3.1-1）

`content/skill_budget.yaml` 的 `allowance.total_cap: 500`（‰）。`_allowance_parts` 仍列出各項（各自已套用原本的上限），`BudgetReport` 新增 `allowance_cap`，`allowance_permille ＝ min(各項加總, allowance_cap)`，另提供 `allowance_raw_permille` 與 `allowance_capped`。`trpg skills budget <id>` 在截斷時多印一行（例如 `代價折抵 +725‰ → 上限 +500‰`）；`--all` 新增「折抵‰」欄（`+160` 或 `+850→500`）。

### 4.2 組合器資料檔（3.1-2）

`content/skill_composer.yaml` ↔ `trpg.content.composer_rules.ComposerRules`（`ContentLibrary.composer`、`KNOWN_CONTENT_FILES`、`trpg content check` 皆已涵蓋）。搬進資料檔的項目（判斷標準：屬於「機率與範圍」的調參）：

- 頂層：稀有度權重、AP 權重、法術占比（含骨架覆寫）、法術武器需求「任何」機率與屬性權重、武器技近戰／敏捷機率、帶元素機率。
- 階梯：骰子（面數、最大顆數）、武器倍率（三段 `range`）、持續上限與各類額外回合與旋鈕權重、推拉距離。
- 結構：核心／其他旋鈕權重、位移第二核心、連段第二段傷害、控場自我增益、暈眩最低冷卻、大範圍半徑／錐形大小、十字／3×3 的零距離機率與最小施放距離、後備附帶原語、目標型條件清單。
- 條件機率與範圍、代價（法力、冷卻、每場次數的機率與範圍）、強度調整（比例區間 750–950‰、目標餘裕、步數、跳格比例）。

仍在程式碼的：`MAX_ATTEMPTS`（50，演算法的重抽上限）、`_BIG_SHAPES`／`_ALLY_SHAPES`（形狀的結構性質）、骨架可行性判斷、亂數呼叫的順序。`LOW`／`HIGH` 常數改為 `tuning_bounds(library)`；`dice_ladder` 改為接受 `DiceRules`。
過程中發現一個陷阱：把 `rank >= rare and chance(300)` 提前求值會多消耗一次亂數（原本在 `required` 時短路），第一次搬移的 `cmp` 因此不同；改成延遲求值後逐字相同。比較對象是「折抵上限之後、搬移之前」與「搬移之後」兩份摘要，`cmp` 無輸出。

### 4.3 單場指標 `trpg.sim.metrics`

- `battle_metrics(run) → BattleMetrics`（pydantic、可 pickle／序列化）；核心是純函式 `metrics_from_events(units, events, bounds, actors, ap_spent, winner, rounds, actions)`，測試可以手工建事件。
- **動作邊界**：`BattleRun` 只有平坦的事件列表，沒有「這些事件屬於哪個動作」。`StepTrace` 是 `run_battle(on_step=…)` 的回呼，記錄每步結束時的事件累計數、行動者與每個單位花掉的 AP；`run_tracked` 回傳 `TrackedRun`（`BattleRun` 子類別）。一般的 `BattleRun`（沒有記錄）傳給 `battle_metrics` 時會重播一次取得（`test_metrics_do_not_depend_on_how_the_run_was_recorded` 證明兩者結果相同）。引擎沒有修改。
- **傷害**：用實際扣掉的 HP（`hp_before − hp_after`）。直接＝`cause == "attack"`；間接＝其他；來源取 `source_id`；追溯不到歸環境（依受害陣營）；打到自己陣營的傷害另記 `damage_friendly`，不計入直接／間接、也不進 DPR。
- **墜落與致命地形**（引擎沒有為它們記 `source_id`）：同一個動作內被強制位移 → 歸該動作的行動者；腳下的橋在同一個動作內被打壞 → 歸最後打到那個物件的單位；其餘歸環境。擊倒數歸給「對該單位最後一次造成傷害的敵方單位」。
- **DPR**＝造成的（直接＋間接）傷害 ÷ 存活輪數（每個 `round_started` 時仍在場的單位 +1，援軍從抵達後的下一輪起算；分母 `max(1, …)`）。陣營 DPR＝每場（陣營傷害 ÷ 輪數）再對各場平均。
- **控制回合**：`turn_started` 當下單位帶有 stun／root／slow 的次數（依 `status_applied`／`status_removed`／`status_converted` 追蹤，最後一次施加者），歸給施加者；報表分「我方／敵方／環境」。
- **技能使用**：沿用 `sim_demo_maps.py` 的歸屬規則（`skill_used` 之後、下一個 `attack_rolled` 之前的 attack 傷害與治療歸該技能），差別見「待 PM 決定」#1。
- **AP**：非 `EndTurn`／`Decision` 的動作，行動者仍是行動中單位時，AP 的減少量；報表的「AP／回合」＝總 AP ÷ 總回合數（含被暈眩跳過的回合）。取得了，所以沒有省略。

### 4.4 批次模擬 `trpg.sim.batch`

- `BatchSpec(name, setup, seeds, policy_factory, max_actions=DEFAULT_MAX_ACTIONS)`；`UtilityPolicyFactory(profiles)` 是可 pickle 的預設 factory（每場新建一個 `UtilityAI`）；`map_spec(library, map_id, seeds)` 用地圖 `encounter`、`max_rounds=30`。
- `run_batches(specs, jobs)`：把全部 (規格, 種子) 攤平成工作，`jobs>1` 時用一個 `multiprocessing.Pool`（`initializer` 只傳一次規格），結果依種子排序後才彙總，所以與 `jobs` 無關。每場戰鬥的例外被捕捉：`MaxActionsExceeded` → `max_actions`，其他 → `exception`（型別＋訊息最後一行）；失敗的場次不進彙總（`completed` < `battles`）。`jobs>1` 在 `fork` 以外的啟動方式需要 `policy_factory` 可 pickle。
- `BatchReport`（pydantic；`REPORT_LIST_ADAPTER` 可轉 JSON）：勝負、輪數（平均／中位數／最小／最大）、每場平均動作數、陣營 DPR（直接／間接／友軍誤傷／受環境傷害）、單位範本表、控制回合、技能使用表、從未使用的技能（地圖上有單位裝備、整批沒用過）、異常。`format_report` 是文字格式（繁中、markdown 表格），不含時間。
- **異常門檻**（模組常數，`trpg.sim.metrics`／`trpg.sim.batch`）：`LONG_BATTLE_ROUNDS = 10`（輪數 > 10）；`BOSS_TAG = "boss"`、`BOSS_BURST_FRACTION_PERMILLE = 500`（Boss 第 1 輪被擊倒，或單一動作對它造成 ≥ 50% 最大 HP）；`one_shot`：單一動作對非 Boss 單位造成 ≥ 最大 HP，只計數、列出前 `ONE_SHOT_SEED_LIMIT = 5` 個種子；`chain_limit`：`chain_limit_reached` 事件總數；`draw`：達到 `max_rounds` 平手；`exception`／`max_actions` 見上。「單一動作」的傷害不含 `status`、`surface`（回合推進的持續傷害）；`deadly_terrain` 不計入非 Boss 的 `one_shot`（設計好的秒殺，否則每個推下深淵都是異常），對 Boss 仍計入 `boss_burst`。
- `trpg sim maps`（`trpg.cli.sim`）：預設跑全部有 `encounter` 的非 `test_*` 地圖（依 ID 排序）；標準輸出只有報表；執行時間與 `--json` 路徑印在標準錯誤。`scripts/sim_demo_maps.py` 是 `main(["sim", "maps", *argv])` 的薄包裝。舊的 `collect_skill_stats` 邏輯在 `trpg.sim.metrics`，原本測它的 `tests/test_sim_scripts.py` 改測薄包裝，歸屬測試移到 `tests/sim/test_metrics.py`。
- 為 2C-2 預留：`BatchSpec` 是 frozen dataclass，可新增 `controllers`／指揮官欄位（預設空）；`policy_factory` 已是「每場新建」，指揮官的紀錄可以放進 `BattleOutcome`。

## 5. 數據表

### 5.1 折抵上限對示範技能的影響

23 個示範技能的代價折抵（各項已套用各自上限後的加總）最高為 +220‰（盾擊），遠低於 +500‰，**沒有任何示範技能因此改變可用預算或比例**（前後比例相同；`trpg skills budget --all` 通過 23 個、違規 0 個）。隨機技能：種子 0–999 中有 32 個的折抵加總超過 +500‰（最高 +725‰，種子 38：冷卻 5、每場 1 次、法力 15），這些技能的可用預算被壓低，組合器因此重新抽出別的結構。

`trpg skills budget --all`（截斷後）：

```
技能預算總表（共 23 個；合格區間以 total ÷ 可用預算計）：
  ID                        名稱        T  AP  total   可用    折抵‰      比例    違規
  skill_ashen_oath          灰燼誓約    2  2   16.00   20.88   +160       76.6%   —
  skill_blink               閃現        1  1   7.00    8.22    +175       85.1%   —
  skill_bone_crusher        碎骨重擊    1  2   13.50   15.68   +120       86.1%   —
  skill_chain_lightning     連鎖閃電    2  2   13.50   18.90   +50        71.4%   —
  skill_cinder_burst        餘燼爆發    2  2   16.40   20.52   +140       79.9%   —
  skill_cleave              橫掃劈砍    1  2   12.74   15.68   +120       81.2%   —
  skill_execute             處決        1  2   11.90   15.75   +125       75.6%   —
  skill_fire_arrow          火焰箭矢    1  1   5.60    7.11    +15        78.8%   —
  skill_fire_bolt           火焰箭      1  1   6.00    7.21    +30        83.2%   —
  skill_frost_shackle       寒鎖        1  1   6.50    7.88    +125       82.5%   —
  skill_gale_kick           颶風踢      1  1   6.80    7.80    +115       87.1%   —
  skill_grapple_arrow       鉤索箭      1  1   6.80    7.80    +115       87.1%   —
  skill_high_ground_shot    高處狙擊    1  2   11.76   15.75   +125       74.7%   —
  skill_piercing_shot       穿透射擊    1  2   12.60   15.82   +130       79.6%   —
  skill_rending_strike      放血斬      1  1   6.90    7.84    +120       88.0%   —
  skill_sanctuary           聖域        2  2   17.10   21.60   +200       79.2%   —
  skill_shield_bash         盾擊        1  2   12.90   17.08   +220       75.5%   —
  skill_smoke_arrow         煙幕箭      1  1   6.67    8.19    +170       81.4%   —
  skill_stone_wall          石牆術      1  1   5.40    7.17    +25        75.3%   —
  skill_summon_tide         喚潮        1  1   5.40    7.21    +30        74.9%   —
  skill_vanish              隱匿        1  1   6.00    7.80    +115       76.9%   —
  skill_venom_cloud         毒霧        2  2   18.00   21.60   +200       83.3%   —
  skill_whirlwind           旋風斬      1  2   12.60   16.52   +180       76.3%   —
通過 23 個，違規 0 個。
```

### 5.2 `skill_fuzz.py --count 1000`

| 階段 | 組合成功 | 通過驗證 | 可施放 | 合法選取 | AI 對戰（我方勝／敵方勝／平手） | 例外 | 平均重抽 |
|---|---|---|---|---|---|---|---|
| 折抵上限之前（2B-3） | 1000 | 1000 | 1000 | 2803 | 97／2／1 | 0 | 0.714 |
| 折抵上限之後、搬移資料檔之前 | 1000 | 1000 | 1000 | 2805 | 97／2／1 | 0 | 0.707 |
| 搬移資料檔之後 | 與上一列逐字相同（`cmp` 無輸出） | | | | | | |

### 5.3 `trpg sim maps --seeds 20`（只列出）

| 地圖 | 我方勝率 | 平均輪數 | 輪數範圍 | 每場平均動作 | 異常 |
|---|---|---|---|---|---|
| bridge_chasm | 75.0% | 4.20 | 3–7 | 73.6 | boss_burst ×1、one_shot ×1 |
| oil_depot | 45.0% | 4.75 | 3–7 | 89.9 | boss_burst ×1 |
| ruined_fort | 85.0% | 4.35 | 3–6 | 81.0 | 無 |
| swamp | 85.0% | 4.20 | 2–8 | 73.7 | boss_burst ×2、one_shot ×6 |

四張地圖都沒有 `exception`、`max_actions`、`draw`、`long_battle`、`chain_limit`。勝率與 2B-3 報告的 `sim_demo_maps.py`（75／45／85／85%）完全相同（同樣的 AI、同樣的種子），代表新指標沒有改變戰鬥本身。

### 5.4 執行時間（2 核心機器，80 場）

| `--jobs` | 時間 |
|---|---|
| 1 | 54.8 秒、57.3 秒、58.7 秒（三次） |
| 4 | 33.2 秒、34.4 秒、35.5 秒（三次） |

## 6. 待 PM 決定

1. **傷害用「實際扣掉的 HP」，不含溢出**，也只計對敵方的傷害；舊 `sim_demo_maps.py` 的「平均傷害／次」用事件的 `amount`（含溢出、含友軍），所以技能的平均傷害比 2B-3 報告略低（例如擊殺時的溢出不計）。DPR 與「單一動作 ≥ 最大 HP」都以實際扣血為準。若 PM 想用含溢出的數字（衡量「爆發潛力」），是一行的改動。
2. **墜落／致命地形的傷害來源**：引擎的 `DamageEffect` 沒有為它們帶 `source_id`，我在指標層追溯（強制位移→行動者；橋被打壞→最後打到橋的單位）。追溯不到的仍歸環境：火燒掉的橋、油桶連鎖爆炸、站在表面上的傷害、自己走進去。例如 `oil_depot` 敵方「受環境傷害」每場 13.95。要不要在引擎裡讓這些傷害帶來源（2C-2 碰引擎時順手）？位移流 build 的 DPR（2C-3）會依賴它。
3. **`boss_burst` 的門檻 50% 對 80 HP 的盜賊頭目太敏感**：4 張地圖共 4 次 boss_burst，其中 3 次剛好是 40／80（恰好 50%），不是失控的爆發。是否改成 > 50% 或 60%？`one_shot` 出現在 `swamp`（6 次）與 `bridge_chasm`（1 次）；這裡只列出，沒有分析是哪個技能造成。
4. **控制回合的實際數字接近 0**（stun 0.05／場、root 0.05／場，其餘 0），確認 2B-3 待決定 #7（AI 很少用控場與位移）：示範地圖的 `skill_frost_shackle` 每場 0.3–0.8 次、命中率 33–57%，但對應的控制回合只有 0.05（原因——抵抗判定或目標先倒下——沒有分析）；`skill_gale_kick`、`skill_grapple_arrow`、`skill_smoke_arrow`、`skill_vanish` 在多數地圖「從未使用」。留給 2C-4 調權重。
5. **友軍誤傷不計入 DPR**，另列「友軍誤傷／場」（`swamp` 我方 6.60，主要是連鎖閃電）。若要把它當作「淨傷害」扣除，需要 PM 決定。
6. **勝率的分母是「完成的場次」**；`exception`／`max_actions` 的場次只出現在異常清單，不進任何彙總。目前示範地圖沒有這種場次。
7. **「從未使用的技能」只看地圖上有單位裝備的技能**；不含隨機技能（那是 `trpg sim skills`，2C-3）。
8. **文字報表格式與舊腳本不同**：舊腳本把技能使用統計合併成一張跨地圖的表，現在每張地圖一節、各自一張表（需要跨地圖合併時用 `--json`）。
9. **`jobs > 1` 的移植性**：Linux 預設 `fork` 沒問題；Windows／macOS（`spawn`）需要 `policy_factory` 可 pickle。2C-2 的指揮官 factory 請做成模組層級的可呼叫物件（類別），不要用 lambda。
10. **組合器仍留在程式碼的常數**（`MAX_ATTEMPTS`、`_BIG_SHAPES`／`_ALLY_SHAPES`）我判斷屬於演算法／結構性質；若 PM 希望也進資料檔，請指示。

## 7. 給下一個子階段的備註

- 2C-2：`run_tracked(setup, seed, policy, max_actions=…)` 目前直接呼叫 `run_battle`；加上 `controllers` 後在這裡轉傳即可。`StepTrace` 的 `actors` 已含行動者，指揮官紀錄（`order_log`）可以另外存進 `BattleOutcome`／`BattleMetrics`。`CommandedAI` 要放進 `policy_factory`，必須每場新建並且可 pickle。
- 2C-3：`build_report`／`format_report` 對任何 `BatchSpec` 都適用（不限地圖預設陣容），矩陣需要的「build 英雄的 DPR、存活率」可以由 `TemplateRow`（以單位範本 ID 區分）取得——build 英雄的範本 ID 要唯一。`BattleMetrics.units` 有每個實例的 DPR，若需要「某個 ID 的實例」直接用它。分階標準敵人的 DPR 報表同理。
- 2C-4：參數掃描可以直接呼叫 `run_batches`，用不同的 `AiProfileTable`／`BattleSetup` 組出多個 `BatchSpec`。報表是純資料，可序列化後比較。
- `skill_composer.yaml` 的任何數值變動都會改變「種子 → 技能」的對應（包含 `tests/skillgen` 與 fuzz 摘要），調整後請重跑 fuzz 並重寫摘要。

## 8. 附錄：代表性的 CLI 輸出節錄

### 8.1 `uv run trpg sim maps --seeds 20`（完整標準輸出；`--jobs 1` 與 `--jobs 4` 逐字相同）

```
批次模擬：效用 AI，種子 0–19（20 場／地圖），max_rounds=30

## bridge_chasm（20 場，完成 20 場，max_rounds=30）

勝負：我方 15（75.0%）／敵方 5（25.0%）／平手 0（0.0%）
輪數：平均 4.20、中位數 4、最小 3、最大 7
動作數：每場平均 73.6

陣營 DPR（每輪傷害，每場平均）與環境：
| 陣營 | DPR | 直接 | 間接 | 友軍誤傷／場 | 受環境傷害／場 |
|---|---|---|---|---|---|
| 我方 | 36.72 | 29.73 | 6.99 | 3.00 | 0.35 |
| 敵方 | 22.07 | 15.72 | 6.34 | 0.00 | 5.85 |

單位範本（每個實例的平均）：
| 範本 | 陣營 | 實例 | DPR | 承受傷害 | 治療量 | 擊倒 | 存活率 | AP／回合 |
|---|---|---|---|---|---|---|---|---|
| hero_archer | 我方 | 20 | 13.01 | 17.4 | 0.0 | 0.80 | 75.0% | 2.70 |
| hero_fighter | 我方 | 20 | 8.88 | 52.1 | 0.0 | 0.75 | 30.0% | 2.15 |
| hero_mage | 我方 | 20 | 19.81 | 26.4 | 0.0 | 1.70 | 75.0% | 2.71 |
| bandit | 敵方 | 40 | 1.04 | 29.9 | 0.0 | 0.00 | 2.5% | 1.49 |
| bandit_archer | 敵方 | 20 | 11.56 | 22.2 | 0.0 | 0.20 | 25.0% | 2.76 |
| bandit_boss | 敵方 | 20 | 12.37 | 71.9 | 0.0 | 0.95 | 25.0% | 2.40 |

控制回合（施加者 → 目標在自己回合開始時帶著該狀態；每場平均）：
| 施加者 | stun | root | slow |
|---|---|---|---|
| 我方 | 0.00 | 0.00 | 0.00 |
| 敵方 | 0.00 | 0.00 | 0.00 |
| 環境 | 0.00 | 0.00 | 0.00 |

技能使用：
| 技能 | 陣營 | 次／場 | 命中率 | 平均傷害／次 | 平均治療／次 |
|---|---|---|---|---|---|
| skill_fire_bolt | 我方 | 2.90 | 67.2% | 8.6 | — |
| skill_cleave | 敵方 | 1.45 | 51.5% | 5.5 | — |
| skill_rending_strike | 我方 | 0.90 | 61.1% | 1.6 | — |
| skill_cinder_burst | 我方 | 0.85 | 52.9% | 13.4 | — |
| skill_ashen_oath | 我方 | 0.75 | 52.0% | 13.6 | — |
| skill_high_ground_shot | 我方 | 0.75 | 66.7% | 8.1 | — |
| skill_bone_crusher | 我方 | 0.70 | 71.4% | 7.1 | — |
| skill_frost_shackle | 我方 | 0.35 | 57.1% | 4.4 | — |
| skill_execute | 我方 | 0.20 | 75.0% | 7.2 | — |
| skill_blink | 我方 | 0.15 | — | 0.0 | — |
| skill_grapple_arrow | 我方 | 0.05 | 0.0% | 0.0 | — |
| skill_whirlwind | 我方 | 0.05 | 66.7% | 8.0 | — |

從未使用的技能：skill_fire_arrow、skill_gale_kick、skill_piercing_shot、skill_smoke_arrow、skill_vanish

異常：
- boss_burst ×1：種子 10
    種子 10：單一動作對 unit_0007 造成 40／80
- one_shot ×1：種子 1（1 次）

## oil_depot（20 場，完成 20 場，max_rounds=30）

勝負：我方 9（45.0%）／敵方 11（55.0%）／平手 0（0.0%）
輪數：平均 4.75、中位數 5、最小 3、最大 7
動作數：每場平均 89.9

陣營 DPR（每輪傷害，每場平均）與環境：
| 陣營 | DPR | 直接 | 間接 | 友軍誤傷／場 | 受環境傷害／場 |
|---|---|---|---|---|---|
| 我方 | 33.50 | 29.89 | 3.60 | 0.75 | 4.25 |
| 敵方 | 26.18 | 26.18 | 0.00 | 0.00 | 13.95 |

單位範本（每個實例的平均）：
| 範本 | 陣營 | 實例 | DPR | 承受傷害 | 治療量 | 擊倒 | 存活率 | AP／回合 |
|---|---|---|---|---|---|---|---|---|
| hero_archer | 我方 | 20 | 12.70 | 36.6 | 0.0 | 0.95 | 40.0% | 2.89 |
| hero_fighter | 我方 | 20 | 9.11 | 55.5 | 0.0 | 0.95 | 25.0% | 2.88 |
| hero_mage | 我方 | 20 | 18.46 | 33.0 | 0.0 | 0.90 | 40.0% | 2.88 |
| bandit | 敵方 | 55 | 6.42 | 24.6 | 0.0 | 0.27 | 23.6% | 2.43 |
| bandit_archer | 敵方 | 20 | 10.32 | 23.1 | 0.0 | 0.25 | 20.0% | 2.66 |
| bandit_boss | 敵方 | 20 | 11.57 | 69.2 | 0.0 | 0.85 | 35.0% | 2.79 |

控制回合（施加者 → 目標在自己回合開始時帶著該狀態；每場平均）：
| 施加者 | stun | root | slow |
|---|---|---|---|
| 我方 | 0.00 | 0.00 | 0.00 |
| 敵方 | 0.00 | 0.00 | 0.00 |
| 環境 | 0.00 | 0.00 | 0.00 |

技能使用：
| 技能 | 陣營 | 次／場 | 命中率 | 平均傷害／次 | 平均治療／次 |
|---|---|---|---|---|---|
| skill_cleave | 敵方 | 2.10 | 67.3% | 8.6 | — |
| skill_fire_bolt | 我方 | 1.50 | 60.0% | 7.4 | — |
| skill_rending_strike | 我方 | 1.50 | 63.3% | 1.8 | — |
| skill_bone_crusher | 我方 | 1.20 | 62.5% | 6.4 | — |
| skill_ashen_oath | 我方 | 1.00 | 50.0% | 11.8 | — |
| skill_whirlwind | 我方 | 0.85 | 71.4% | 5.8 | — |
| skill_cinder_burst | 我方 | 0.80 | 75.0% | 23.8 | — |
| skill_frost_shackle | 我方 | 0.30 | 33.3% | 2.3 | — |
| skill_execute | 我方 | 0.20 | 50.0% | 5.8 | — |
| skill_grapple_arrow | 我方 | 0.20 | 50.0% | 0.8 | — |
| skill_piercing_shot | 我方 | 0.20 | 37.5% | 6.8 | — |
| skill_high_ground_shot | 我方 | 0.15 | 100.0% | 2.7 | — |

從未使用的技能：skill_blink、skill_fire_arrow、skill_gale_kick、skill_smoke_arrow、skill_vanish

異常：
- boss_burst ×1：種子 6
    種子 6：單一動作對 unit_0007 造成 40／80

## ruined_fort（20 場，完成 20 場，max_rounds=30）

勝負：我方 17（85.0%）／敵方 3（15.0%）／平手 0（0.0%）
輪數：平均 4.35、中位數 4、最小 3、最大 6
動作數：每場平均 81.0

陣營 DPR（每輪傷害，每場平均）與環境：
| 陣營 | DPR | 直接 | 間接 | 友軍誤傷／場 | 受環境傷害／場 |
|---|---|---|---|---|---|
| 我方 | 26.41 | 24.54 | 1.87 | 0.25 | 2.55 |
| 敵方 | 22.31 | 22.31 | 0.00 | 0.00 | 1.80 |

單位範本（每個實例的平均）：
| 範本 | 陣營 | 實例 | DPR | 承受傷害 | 治療量 | 擊倒 | 存活率 | AP／回合 |
|---|---|---|---|---|---|---|---|---|
| hero_archer | 我方 | 20 | 9.03 | 29.3 | 0.0 | 0.85 | 75.0% | 2.71 |
| hero_fighter | 我方 | 20 | 5.71 | 36.5 | 0.0 | 1.25 | 75.0% | 2.34 |
| hero_mage | 我方 | 20 | 15.88 | 33.0 | 0.0 | 1.65 | 55.0% | 2.83 |
| bandit | 敵方 | 40 | 4.12 | 30.0 | 0.0 | 0.03 | 0.0% | 2.32 |
| bandit_archer | 敵方 | 40 | 10.49 | 24.9 | 0.0 | 0.45 | 10.0% | 2.31 |

控制回合（施加者 → 目標在自己回合開始時帶著該狀態；每場平均）：
| 施加者 | stun | root | slow |
|---|---|---|---|
| 我方 | 0.00 | 0.05 | 0.00 |
| 敵方 | 0.00 | 0.00 | 0.00 |
| 環境 | 0.00 | 0.00 | 0.00 |

技能使用：
| 技能 | 陣營 | 次／場 | 命中率 | 平均傷害／次 | 平均治療／次 |
|---|---|---|---|---|---|
| skill_fire_bolt | 我方 | 2.70 | 68.5% | 9.3 | — |
| skill_rending_strike | 我方 | 1.45 | 62.1% | 1.8 | — |
| skill_bone_crusher | 我方 | 0.90 | 61.1% | 6.1 | — |
| skill_ashen_oath | 我方 | 0.80 | 52.6% | 10.8 | — |
| skill_frost_shackle | 我方 | 0.80 | 37.5% | 2.7 | — |
| skill_whirlwind | 我方 | 0.40 | 53.8% | 3.2 | — |
| skill_execute | 我方 | 0.30 | 50.0% | 3.8 | — |
| skill_fire_arrow | 敵方 | 0.10 | 50.0% | 0.5 | — |
| skill_blink | 我方 | 0.05 | — | 0.0 | — |
| skill_cinder_burst | 我方 | 0.05 | 100.0% | 19.0 | — |
| skill_high_ground_shot | 我方 | 0.05 | 0.0% | 0.0 | — |

從未使用的技能：skill_gale_kick、skill_grapple_arrow、skill_piercing_shot、skill_smoke_arrow、skill_vanish

異常：無

## swamp（20 場，完成 20 場，max_rounds=30）

勝負：我方 17（85.0%）／敵方 3（15.0%）／平手 0（0.0%）
輪數：平均 4.20、中位數 4、最小 2、最大 8
動作數：每場平均 73.7

陣營 DPR（每輪傷害，每場平均）與環境：
| 陣營 | DPR | 直接 | 間接 | 友軍誤傷／場 | 受環境傷害／場 |
|---|---|---|---|---|---|
| 我方 | 43.65 | 32.57 | 11.08 | 6.60 | 0.00 |
| 敵方 | 20.29 | 20.29 | 0.00 | 0.00 | 0.00 |

單位範本（每個實例的平均）：
| 範本 | 陣營 | 實例 | DPR | 承受傷害 | 治療量 | 擊倒 | 存活率 | AP／回合 |
|---|---|---|---|---|---|---|---|---|
| hero_archer | 我方 | 20 | 11.26 | 20.9 | 0.0 | 1.05 | 80.0% | 2.71 |
| hero_fighter | 我方 | 20 | 10.35 | 43.0 | 0.0 | 0.50 | 45.0% | 2.89 |
| hero_stormcaller | 我方 | 20 | 28.88 | 31.1 | 9.6 | 2.00 | 60.0% | 2.76 |
| bandit | 敵方 | 20 | 5.03 | 29.3 | 0.0 | 0.05 | 10.0% | 2.71 |
| bandit_archer | 敵方 | 20 | 10.85 | 24.8 | 0.0 | 0.20 | 10.0% | 2.87 |
| bandit_boss | 敵方 | 20 | 9.90 | 78.0 | 0.0 | 0.65 | 10.0% | 2.97 |
| bandit_shieldbearer | 敵方 | 20 | 1.38 | 28.6 | 0.0 | 0.10 | 15.0% | 1.54 |

控制回合（施加者 → 目標在自己回合開始時帶著該狀態；每場平均）：
| 施加者 | stun | root | slow |
|---|---|---|---|
| 我方 | 0.00 | 0.00 | 0.00 |
| 敵方 | 0.05 | 0.00 | 0.00 |
| 環境 | 0.00 | 0.00 | 0.00 |

技能使用：
| 技能 | 陣營 | 次／場 | 命中率 | 平均傷害／次 | 平均治療／次 |
|---|---|---|---|---|---|
| skill_chain_lightning | 我方 | 1.90 | 60.0% | 23.2 | — |
| skill_cleave | 敵方 | 1.70 | 53.5% | 6.3 | — |
| skill_rending_strike | 我方 | 1.30 | 57.7% | 1.6 | — |
| skill_bone_crusher | 我方 | 0.90 | 66.7% | 5.1 | — |
| skill_sanctuary | 我方 | 0.55 | — | 0.0 | 17.5 |
| skill_whirlwind | 我方 | 0.55 | 66.7% | 6.6 | — |
| skill_execute | 我方 | 0.50 | 70.0% | 11.0 | — |
| skill_piercing_shot | 我方 | 0.25 | 36.4% | 5.6 | — |
| skill_shield_bash | 敵方 | 0.25 | 40.0% | 1.6 | — |
| skill_gale_kick | 敵方 | 0.05 | 100.0% | 3.0 | — |
| skill_high_ground_shot | 我方 | 0.05 | 100.0% | 3.0 | — |
| skill_summon_tide | 我方 | 0.05 | 100.0% | 0.0 | — |

從未使用的技能：skill_fire_arrow、skill_grapple_arrow、skill_smoke_arrow、skill_stone_wall、skill_vanish

異常：
- boss_burst ×2：種子 5, 13
    種子 5：單一動作對 unit_0007 造成 52／80
    種子 13：單一動作對 unit_0007 造成 40／80
- one_shot ×6：種子 3（1 次）, 5（2 次）, 15（1 次）, 17（2 次）
```

### 8.2 `trpg skills budget`（折抵截斷）

`trpg skills random --seed 38` 的預算摘要：

```
  可用預算 ＝ tier_budget 29 × AP 係數 1.60 × (1000 + 折抵 500‰) ÷ 1000 ＝ 69.60
  代價折抵 冷卻 5 回合 +250‰、每場 1 次 +400‰、法力 15 +75‰
  代價折抵 +725‰ → 上限 +500‰
  比例 ＝ total ÷ 可用預算 ＝ 85.3%（合格區間 70.0%–100.0%）→ 合格
```
