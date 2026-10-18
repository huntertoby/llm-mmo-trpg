# Phase 2B-3 完成報告：隨機組合器與 1,000 技能驗收

> 實作者撰寫｜對應 `docs/phases/Phase2B計畫.md` 第 5 節與 5.0 的 PM 決定

## 1. 摘要

- 先做 5.0 的 PM 決定：`tier_budget` 改為 14／18／23／29／36；三個變弱的 T2 示範技能（餘燼爆發、聖域、毒霧）提高強度而不降階；水表面預設持續 3 回合；狀態與表面加 `beneficial`，光環骨架的核心必須有益。
- 新增隨機組合器 `compose_random_skill`（骨架 → 核心原語 → 形狀 → 效果 → 條件 → 代價 → 調整強度到 0.75–0.95 → 驗證），確定性、可序列化、可重抽。
- 新增 `trpg.sim.skill_fuzz` 與 `scripts/skill_fuzz.py`：`--count 1000` 的結果是 **1,000 個全部通過驗證、全部可施放、0 個例外**，執行時間約 17 秒（目標 ≤ 3 分鐘），兩次執行的摘要逐字相同。
- 新增 CLI `trpg skills random`。`scripts/check.py` 五項全過（924 個測試）；慢速測試只剩 2B-2 已知的三個平衡測試失敗（只列出，見 5.3）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `fc1c88b` | 5.0：`tier_budget`、水持續、`beneficial` 旗標、光環核心檢查（`skeleton.core_beneficial`）、T2 示範技能調整、相關測試更新 |
| `060d3fb` | 隨機組合器（`random_composer`、`composer_parts`、`composer_tuning`）、`skill_yaml`、`validate.share_violations`、組合器測試 |
| `d75602e` | `trpg skills random`（含 `print_skill_budget` 重構）與 CLI 測試 |
| `0ef5eaf` | `trpg.sim.skill_fuzz`、`scripts/skill_fuzz.py` 與測試（含 `@pytest.mark.slow` 的 1,000 個版本） |
| `7e3cc5d` | 修正：隨機技能不重複同一種效果（兩個 `create_surface` 只有後者生效）、不重複同一個狀態 |
| （本報告） | `docs/phases/Phase2B-3報告.md` |

## 3. 驗收條件逐條結果

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | `scripts/check.py` 五項全過 | 通過：ruff check／format、mypy、lint-imports、pytest（924 passed，6 deselected）。 |
| 2 | `skill_fuzz.py --count 1000`：1,000 個全部通過驗證、全部可施放、0 個例外 | 通過，完整摘要在 5.2。測試：`tests/sim/test_skill_fuzz.py::test_one_hundred_seeds_pass_validation_cast_and_run_without_exceptions`（預設 100 個）、`::test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible`（slow，1,000 個，已執行通過）；`tests/skillgen/test_random_composer.py::test_one_thousand_seeds_are_all_valid_and_spread_out`（slow，已通過）。 |
| 3 | 5 階級、4 稀有度、6 骨架都出現；任一骨架 ≤ 40% | 通過：階級 T1–T5 各 17–21%；稀有度四種皆有（普通 33.6%、稀有 37.8%、史詩 19.3%、傳說 9.3%）；六種骨架皆有，最大是控場 20.5%。測試：`test_distribution_over_the_fast_seeds_has_every_group`（100 個種子，最大 ≤ 40%）與上述 slow 測試（1,000 個，≤ 400）。 |
| 4 | 確定性：同種子同技能；`skill_fuzz` 兩次摘要完全相同 | 通過：`cmp fuzzA.txt fuzzB.txt` 回報 IDENTICAL（兩次 1,000 個的標準輸出逐字相同；時間印在標準錯誤）。測試：`test_same_seed_gives_the_same_skill_field_by_field`、`test_the_summary_is_identical_between_two_runs_and_lists_the_distributions`。 |
| 5 | 抽 3 個不同骨架的隨機技能，附 `trpg skills random` 輸出與戰鬥紀錄 | 見第 8 節（種子 19 連段、54 控場、105 位移）。 |
| 6 | 2B-1、2B-2 的驗收測試仍通過 | 通過：整個預設測試套件（含 `tests/engine`、`tests/content`、`tests/skillgen`、`tests/cli`）924 passed。5.0 造成的數值變動已同步更新測試（見 4.1）。 |

規格 5.3／5.4 的其他項目：每種啟用骨架、每種稀有度、每個階級都能以指定參數產出技能（`test_every_enabled_skeleton_can_be_composed`、`test_every_rarity_can_be_composed`、`test_every_tier_can_be_composed`）；存成 YAML 再載入結果相同（`test_skills_survive_a_yaml_round_trip`）；CLI 測試在 `tests/cli/test_skills_cli.py`。

## 4. 設計與實作說明

### 4.1 5.0 的改動（先 commit）

- `content/rules/core.yaml`：`tier_budget: {1: 14, 2: 18, 3: 23, 4: 29, 5: 36}`。
- #2：`surfaces.yaml` 的 `water` 加 `duration: 3`（`oil` 維持永久）。這也改變了遊戲內行為：冰到期後變的水、技能產生的水都會在 3 個環境回合後消失（`test_surface_duration_and_expiry` 的期望值同步改成 `surface_remaining == 3`）。
- #5：`StatusDef`／`SurfaceDef` 新增 `beneficial: bool`（預設 `false`）。`defending`、`concealed` 與 `holy` 為 `true`。`aura.yaml` 的核心新增 `beneficial_only: true`（資料旗標，`SkeletonCore` 新欄位），驗證器對核心的 `apply_status`／`create_surface` 檢查，違規代碼 `skeleton.core_beneficial`。
- 因 `tier_budget` 改變而更新的測試：`test_budget.py`（T2 手算案例、水的持續案例）、`test_skill_rules_content.py`、`test_budget_cli.py`（灰燼誓約的可用預算 20.88、比例 76.6%）。兩個隨技能強度調整而改的戰鬥測試：`test_skill_decisions.py`（餘燼爆發多了骰子，腳本骰值補到 6 顆）、`test_skill_preview.py`（聖域治療改為 1d10）。新增 `test_aura_core_status_and_surface_must_be_beneficial`、`test_beneficial_flags_in_content`。

### 4.2 組合器模組結構

| 模組 | 內容 |
|---|---|
| `skillgen/random_composer.py` | 公開 API：`compose_random_skill`、`compose_with_stats`（另回傳重抽次數）、`ComposeError`、`default_library`。決定稀有度、骨架、分類，然後最多 50 次嘗試。 |
| `skillgen/composer_parts.py` | 一次嘗試的零件：`Ctx`、`Knob`（強度旋鈕）、核心原語、形狀與參數、效果（狀態、表面、傷害、治療……）、條件、代價。 |
| `skillgen/composer_tuning.py` | 強度調整。 |
| `skillgen/skill_yaml.py` | `skill_to_yaml`／`skill_from_yaml`（`safe_dump`／`safe_load`＋驗證，與載入 `content/skills/` 同一條路）。 |
| `sim/skill_fuzz.py`、`scripts/skill_fuzz.py` | 執行驗收。 |
| `cli/skills_random.py` | `trpg skills random`。 |

流程與取捨：

1. **頂層參數只抽一次**：階級（1–5 均勻）、稀有度（普通 35／稀有 35／史詩 20／傳說 10）、骨架（對該稀有度「可行」的骨架均勻）、分類（光環 85% 法術，其餘各半）。「可行」由資料推導：骨架啟用、有主動技能、有符合稀有度的核心原語、要求條件時有符合稀有度的條件——所以普通稀有度只會出現打擊、範圍、控場、光環，位移與連段至少稀有（指定不可行組合會拋出 `ComposeError`）。
2. **每次嘗試重抽其餘一切**（同一個 `Rng` 繼續）：核心原語 → 形狀（骨架允許、稀有度夠、核心原語接受，例如傳送只能搭配 `ground_tile`）→ 效果與附帶效果（受骨架的 `secondary` 規則限制，數量受稀有度上限限制）→ 條件（稀有以上 30%，連段必有；目標型條件只在影響範圍內有別的單位時使用）→ **AP 與代價**。
3. **AP 在結構決定之後才選**：依權重（1／2／3 ＝ 35／50／15）排出嘗試順序，每個 AP 各抽一次代價（法力、冷卻、每場次數；大範圍形狀與暈眩會強制冷卻）並調整強度，第一個成功的為準。AP 決定可用預算，同一個結構換個 AP 常常就合格；加了這步之後，控場與位移的失敗率大幅下降（改動前 200 個種子有 2 個 50 次仍失敗）。指定 `ap_cost` 時只嘗試該值。
4. **調整強度**（`composer_tuning`）：旋鈕有骰子（顆數 1–8、面數 {4,6,8,10,12}，依平均值排序的階梯）、武器倍率（500‰–10000‰）、狀態與表面的持續（有預設持續的才有；硬控不可延長、移動類最多 +1）、推拉距離。全部從最弱開始，抽一個目標比例（均勻分佈在 0.75–0.93），再隨機（核心旋鈕權重 6，其他 1–2）往上調，直到達到目標；調一格就超過 0.95 或讓骨架占比限制（核心占比、控場傷害 ≤ 40% 等）變差的旋鈕被封鎖。先試一格估計每格增量，再依缺口一次跳多格。比例用 `Fraction`。
5. **驗證**：最後呼叫 4.1 的 `validate_skill`，有違規就重抽。組合器本身不會「修正」任何違規，所以規格的「失敗則重抽」完全由驗證器把關。
6. **確定性**：只用 `Rng(seed)`；選項一律先排序再抽；不使用 `set` 迭代順序。組合結果同時是純資料，`skill_to_yaml` 後再載入逐欄位相等。
7. **「不得對友方施加有害狀態或表面」**（5.0 #5）：有益狀態（`beneficial`）才會用 `affects: self／allies`；有害狀態只用預設對象（敵方）；自身形狀的技能不會有對敵方的效果（含有害狀態）。測試 `test_no_harmful_status_or_surface_is_aimed_at_allies` 檢查 300 個種子。

產出的技能：`id` ＝ `skill_rand_<seed>`、`name_zh` ＝「元素・骨架 #種子」（例如「火焰・範圍 #123」）、`tags` ＝ 元素＋骨架＋機制標籤、`provenance.origin: level_up`、`narrative` 為暫定文字。`category` 與 `weapon_req` 一致（武器技 `melee`／`ranged`，法術技 `focus`／`any`）。武器技 35% 帶元素（否則繼承武器，名稱顯示「物理」）。

### 4.3 執行驗收工具

- 戰場：`test_flat_6x6`，起始區改成指定站位（施放者 (0,3)、友方 (0,4)、敵人在同一列距離 1／3／5，第二名敵人在第一名後方一格，放不下時在上方一格）。施放者依 `weapon_req` 用戰士（近戰）、弓手（遠程）、法師（法器或任何），法力 99、沒有反應、只裝備這個技能。
- **條件的布置**：有條件的技能（尤其 `height_advantage` 在平地永遠不成立）先把場面布置成條件成立（目標 HP 設為 1、目標帶有狀態、目標腳下是指定表面、施放者的格子升高一層、施放者 HP 設為 1）。沒布置時 300 個種子中有 35 個（11.7%）不可施放，所以「可施放率 100%」指的是條件成立之後。
- 每個合法選取最多 8 個（等距抽樣），在 `clone` 上 `resolve`，**另外也 `preview`**（AI 評分用到，預覽出錯同樣是引擎問題）。
- AI 對戰：`index % 10 == 0` 的技能（共 100 場）：施放者（只裝備該技能）＋弓手 對 盜賊與盜賊弓手，`UtilityAI`，`max_rounds=20`，種子 ＝ 技能種子。
- 例外清單格式：種子、技能 YAML、例外的 **最後一行**（`型別: 訊息`；規格寫「traceback 第一行」，第一行永遠是 `Traceback (most recent call last):`，沒有資訊，所以改取最後一行）。
- 摘要不含時間（時間印在標準錯誤），所以兩次輸出逐字相同；結束代碼：全乾淨為 0，否則 1。
- `scripts/skill_fuzz.py --show-battle <種子>`：印出該種子技能的 YAML 與完整 AI 戰鬥紀錄（報告第 8 節用）。

## 5. 數據表

### 5.1 5.0 #1：T2 示範技能調整前後對照

`tier_budget` 的 T2 從 15 改成 18 後，T2 示範技能的可用預算乘 1.2。下表比較三個狀態：①2B-2 結束（T2 ＝ 15）；②只改 `tier_budget`、技能不動；③調整強度後（本階段）。比例合格區間是 70%–100%。

| 技能 | ①total／可用／比例 | ②total／可用／比例 | ③total／可用／比例 | 調整 |
|---|---|---|---|---|
| 灰燼誓約（area） | 16.00／17.40／92.0% | 16.00／20.88／76.6% 合格 | 不動 | — |
| 連鎖閃電（area） | 13.50／15.75／85.7% | 13.50／18.90／71.4% 合格 | 不動 | —（接近下限，見待 PM 決定 #9） |
| **餘燼爆發**（strike） | 12.43／17.10／72.7% | 12.43／20.52／**60.6% 過弱** | **16.40／20.52／79.9%** | 基礎傷害 1d6 → 1d8；燃燒時追加 3d6 → 4d6 |
| **聖域**（aura） | 13.50／18.00／75.0% | 13.50／21.60／**62.5% 過弱** | **17.10／21.60／79.2%** | 治療 1d6 → 1d10（神聖表面不動） |
| **毒霧**（control） | 14.00／18.00／77.8% | 14.00／21.60／**64.8% 過弱** | **18.00／21.60／83.3%** | 中毒持續 3 → 5 回合；易傷持續 2（預設持續，明確寫出，點數不變） |

其他 18 個示範技能（T1）不受影響（`tier_budget[1]` 沒變）；喚潮的水表面現在預設持續 3 回合，點數與 2B-2 相同（1 點，比例 74.9%）。`trpg skills budget --all`：23 個通過、0 個違規。`scripts/calibrate_tier_budget.py` 現在只剩「T1 ＝ 13、T2 ＝ 18 為最佳」的歷史輸出，不再用來決定 `tier_budget`（PM 已決定曲線）。

### 5.2 `skill_fuzz.py --count 1000 --seed-start 0` 完整摘要

指令：`uv run python scripts/skill_fuzz.py --count 1000 --seed-start 0`；**執行時間 17.1 秒**（第二次 17.7 秒；環境：雲端工作區，單執行緒）。

```
隨機技能驗收：種子 0–999，共 1000 個
  組合成功 1000/1000；通過驗證 1000/1000
  可施放 1000/1000（100.0%）；合法選取共執行 2803 次
  AI 對戰 100 場（我方勝 97、敵方勝 2、平手 1）
  例外 0 個
  平均重抽次數 0.714（最多 19 次；0 表示第一次就成功）

骨架：
  area                190   19.0%
  aura                198   19.8%
  combo                99    9.9%
  control             205   20.5%
  displace            110   11.0%
  strike              198   19.8%
稀有度：
  common              336   33.6%
  rare                378   37.8%
  epic                193   19.3%
  legendary            93    9.3%
階級：
  T1                  172   17.2%
  T2                  199   19.9%
  T3                  211   21.1%
  T4                  212   21.2%
  T5                  206   20.6%
形狀：
  allies_in_radius    112   11.2%
  chain                59    5.9%
  cone                120   12.0%
  cross                30    3.0%
  ground_tile          54    5.4%
  line                121   12.1%
  ring                 79    7.9%
  self                 86    8.6%
  single              258   25.8%
  square3              81    8.1%
AP：
  AP 1                470   47.0%
  AP 2                420   42.0%
  AP 3                110   11.0%
分類：
  spell               572   57.2%
  weapon              428   42.8%

預算比例分佈（total ÷ 可用預算，10 個區間）：
    70%– 73%      0
    73%– 76%     11  #
    76%– 79%     88  #############
    79%– 82%    133  ###################
    82%– 85%    174  #########################
    85%– 88%    184  ###########################
    88%– 91%    201  ##############################
    91%– 94%    163  ########################
    94%– 97%     46  ######
    97%–100%      0
```

補充（不在摘要內，另跑腳本得到）：各骨架的平均重抽次數——範圍 0.03、光環 0.11、連段 0.00、打擊 0.00、位移 1.02、**控場 2.80**（最多 19）；各稀有度——普通 0.43、稀有 0.98、史詩 0.62、傳說 0.84。有條件的技能：稀有 153、史詩 67、傳說 38 個，普通 0 個（條件從稀有起）。

### 5.3 勝率（`sim_demo_maps.py --seeds 20`，只列出）

| 地圖 | 我方勝 | 敵方勝 | 我方勝率 | 平均輪數 | 輪數範圍 | 2B-2 勝率 |
|---|---|---|---|---|---|---|
| bridge_chasm | 15 | 5 | 75% | 4.20 | 3–7 | 70% |
| oil_depot | 9 | 11 | 45% | 4.75 | 3–7 | 35% |
| swamp | 17 | 3 | 85% | 4.20 | 2–8 | 85% |
| ruined_fort | 17 | 3 | 85% | 4.35 | 3–6 | 85% |

餘燼爆發、聖域、毒霧的強化讓我方（法師、弓手）略強。`pytest -m slow` 的 `test_demo_balance.py`：bridge_chasm、swamp、ruined_fort 三個勝率測試失敗（> 65%），oil_depot 與兩個回合數測試通過——與 2B-2 相同的三個失敗，依 5.0 #3 只列出、2C 處理。

### 5.4 效能

`skill_fuzz`：1,000 個技能（組合、驗證、站位搜尋、最多 8 個選取的 resolve＋preview、100 場 AI 對戰）約 17 秒；其中純組合 1,000 個約 1.9 秒（每個 ≈ 2 ms）。

## 6. 待 PM 決定

1. **隨機技能的強度只受預算約束，未經戰鬥平衡驗證**：AI 對戰 100 場我方勝 97 場（施放者有一個預算內的隨機技能，對手是盜賊小隊），與預算沒有衝突但可能顯示 T4–T5 的大傷害技能對 Phase 1 的單位（HP 26–60）過強（例如種子 19：T5 8d8＋暴擊一擊 79 點）。階級曲線（14→36）加屬性成長要怎麼與敵人 HP 對應，是 2C 的平衡課題；建議 2C 的 build 矩陣一併評估。
2. **代價折抵可以疊得很高**：冷卻（上限 +300‰）、每場次數（最多 +400‰）、法力（上限 +150‰）、HP（上限 +200‰）加總可達 +1050‰，隨機技能最高約 +72.5%（種子 38：冷卻 5、每場 1 次、法力 15 的 7d8 神聖十字，AP 3）。是否要為總折抵設上限（例如 +50%）？
3. **控場（與位移）的結構型效果點數偏低**：控場平均需要 2.8 次重抽，位移 1.0，其他骨架 ≈ 0（最多 19 次，仍在 50 次內，0 個失敗）。高階（T4–T5）的純結構型控場技能必須靠「附帶傷害」（受 40% 占比限制）或延長持續才達得到預算。若要讓控場在高階更自然，可考慮調整 `skill_primitives.yaml` 的結構型點數（2B-2 禁止動，現在沒有）。
4. **AP 與稀有度權重、骨架／形狀的抽選機率是我設的初值**：稀有度 35／35／20／10；AP 嘗試順序權重 35／50／15（因為「結構太強或太弱時換 AP」，實際分佈偏向 AP 1：47%／42%／11%）；分類 50／50（光環 85% 法術）；武器技 35% 帶元素。常數目前寫在 `random_composer.py` 與 `composer_parts.py`。要不要移到 `content/`（守則 4，內容即資料）？我沒有移，因為 5.1 沒要求，且它們是組合器的調參而不是遊戲內容。
5. **預算比例分佈偏上半段**：目標均勻分佈在 0.75–0.93，實際集中在 79%–94%（峰值 88%–91%），沒有 70%–73% 與 97%–100% 的技能。原因是旋鈕每次「跳」的步長與一格超過 0.95 就封鎖。若 PM 想要更接近均勻或更靠近 100%，可以調整 `LOW`／`HIGH` 與目標區間（`composer_tuning.py`）。
6. **主題、協同與名稱都是暫定**：元素（名稱與傷害）與狀態、表面互相獨立隨機（例如「火焰・控場」可能附帶冰霜相關的表面）；沒有協同導向的選擇，武器技 65% 顯示「物理」。「有主題、有協同」的 build 留給 Phase 3 的 LLM 管線；這裡只保證預算內合法。
7. **AI 很少使用控場與位移類隨機技能**：100 場 AI 對戰中，施放者實際用到該技能的比例 —— 打擊 17/21、光環 12/21、範圍 9/12、連段 3/13、控場 3/17、位移 2/16。屬於 AI 權重（2A-2 待決定 #5，2C 統一調整）；不影響本階段驗收（只要求不丟例外）。
8. **條件的布置**：fuzz 對有條件的技能先把場面布置成條件成立（見 4.3），否則 `height_advantage` 在平地永遠不可施放。若 PM 認為「可施放」應該指不布置也能施放，需要改規格（例如條件型技能改在有高度差的地圖測試）。
9. **連鎖閃電維持原樣**：改成 T2 ＝ 18 後比例 71.4%，接近下限但合格，我沒有動（規格只要求「不合格的」提高強度）。
10. **`beneficial` 的預設值是 `false`**：新增的狀態或表面若忘了標記就視為有害（對光環是保守方向）。`defending` 標成 `true`（目前沒有技能能施加它，不影響驗證）。

## 7. 給下一階段的備註（2C）

- 組合器的產物可直接進 build 矩陣：`compose_random_skill(seed, tier=, rarity=, skeleton=, category=, ap_cost=)`；`trpg.sim.skill_fuzz.battle_setup(library, skill)` 是「單一技能＋固定陣容」的戰鬥設定，批次模擬器可以重用。
- `Violation.rule` 是穩定代碼；`validate.share_violations` 現在是公開函式（組合器與之後的 LLM 管線可用來在調整強度時避免破壞骨架占比）。
- 大部分隨機技能的單次期望傷害與 Phase 1 單位的 HP 比例沒有校準（待 PM 決定 #1）；做 DPR 報表時請把 `tier_budget` 與屬性成長一起看。
- `scripts/skill_fuzz.py --show-battle <種子>` 可以直接重現任何一個種子的戰鬥，除錯用。
- 引擎沒有因本階段的 fuzz 而修改（沒有找到例外）；若之後新增原語或形狀，把它加進骨架資料後 fuzz 會自動涵蓋。

## 8. 附錄：代表性的 CLI 輸出節錄

三個不同骨架的隨機技能（預設參數，種子 19、54、105）。YAML 省略了 `schema_version`、`rank`、`kind`、`narrative`、`provenance`，並把短的區塊改寫成 flow 風格以節省篇幅（實際輸出是 block 風格，內容相同）。

### 8.1 連段：`trpg skills random --seed 19`

```
# 種子 19（重抽 0 次）
id: skill_rand_19
name_zh: '大地・連段 #19'
tier: 5
rarity: epic
skeleton: combo
category: spell
weapon_req: focus
ap_cost: 3
scaling_attr: int
shape:
  type: chain
  range: 6
  jumps: 1
  jump_range: 1
effects:
- type: damage
  dice: 8d8
  element: earth
- type: damage
  dice: 3d4
  element: earth
  condition:
    type: target_has_status
    status: stun
- type: knock_prone
cost:
  mana: 20
  cooldown: 2
tags: [earth, combo, damage, area, displace]

大地・連段 #19（skill_rand_19）  階級 T5  稀有度 史詩  骨架 combo  AP 3
  效果點數 ＝ 基礎點數 × 形狀 × 對象 × 效果條件：
    1. damage          8d8 平均            形狀 ×1.25  對象 ×1    條件 ×1     ＝ 45.00（基礎 36.00）
    2. damage          3d4 平均            形狀 ×1.25  對象 ×1    條件 ×0.85  ＝ 7.97（基礎 7.50）
    3. knock_prone     固定                形狀 ×1.25  對象 ×1    條件 ×1     ＝ 3.75（基礎 3.00）
  raw ＝ 56.72
  機制標籤 damage、area、displace
  協同係數 area+displace ×1.1
  total ＝ raw × 條件 × 協同 ＝ 62.39
  可用預算 ＝ tier_budget 36 × AP 係數 1.60 × (1000 + 折抵 200‰) ÷ 1000 ＝ 69.12
  代價折抵 冷卻 2 回合 +100‰、法力 20 +100‰
  比例 ＝ total ÷ 可用預算 ＝ 90.3%（合格區間 70.0%–100.0%）→ 合格
  驗證：通過
```

戰鬥紀錄（`scripts/skill_fuzz.py --show-battle 19`，第 1 輪法師的回合）：

```
— 法師 的回合（AP 3，移動 5，法力 99/99）
  法師 施放「大地・連段 #19」（AP 3，法力 20，冷卻 2 回合）→ 影響 2 格
  法師 以「大地・連段 #19」攻擊 盜賊：d20=6 修正 +0 熟練 +2 = 8（目標 11）→ 失手
  法師 以「大地・連段 #19」攻擊 盜賊弓手：d20=20 修正 +0 熟練 +2 = 22（目標 11）→ 自然 20，暴擊！
    盜賊弓手 受到 79 點大地傷害［骰 3+6+2+1+4+1+8+7+4+6+5+7+3+6+5+3］，HP 26 → 0
  ＊ 盜賊弓手 倒下了！
  法師 結束回合
```

### 8.2 控場：`trpg skills random --seed 54`

```
# 種子 54（重抽 2 次）
id: skill_rand_54
name_zh: '火焰・控場 #54'
tier: 4
rarity: common
skeleton: control
category: spell
weapon_req: any
ap_cost: 1
scaling_attr: int
shape: {type: line, size: 3}
effects:
- {type: apply_status, status: burning, duration: 4}
- {type: damage, dice: 1d6, element: fire}
cost: {mana: 9}
tags: [fire, control, damage, area, dot]

火焰・控場 #54（skill_rand_54）  階級 T4  稀有度 普通  骨架 control  AP 1
    1. apply_status    burning 3×2         形狀 ×1.4   對象 ×1    條件 ×1     ＝ 8.40（基礎 6.00）
    2. damage          1d6 平均            形狀 ×1.4   對象 ×1    條件 ×1     ＝ 4.90（基礎 3.50）
  raw ＝ 13.30
  total ＝ raw × 條件 × 協同 ＝ 13.30
  可用預算 ＝ tier_budget 29 × AP 係數 0.50 × (1000 + 折抵 45‰) ÷ 1000 ＝ 15.15
  比例 ＝ total ÷ 可用預算 ＝ 87.8%（合格區間 70.0%–100.0%）→ 合格
  驗證：通過
```

戰鬥紀錄（種子 54，第 1 輪）：

```
— 法師 的回合（AP 3，移動 5，法力 99/99）
  法師 施放「火焰・控場 #54」（AP 1，法力 9）→ 影響 3 格
  法師 以「火焰・控場 #54」攻擊 盜賊：d20=1 修正 +0 熟練 +2 = 3（目標 11）→ 自然 1，失手
  法師 施放「火焰・控場 #54」（AP 1，法力 9）→ 影響 3 格
  法師 以「火焰・控場 #54」攻擊 盜賊：d20=10 修正 +0 熟練 +2 = 12（目標 11）→ 命中
  盜賊 獲得狀態「燃燒」（4 回合）
    盜賊 受到 12 點火焰傷害［骰 4］，HP 30 → 18
  法師 施放「火焰・控場 #54」（AP 1，法力 9）→ 影響 3 格
  法師 以「火焰・控場 #54」攻擊 盜賊：d20=2 修正 +0 熟練 +2 = 4（目標 11）→ 失手
  法師 結束回合
```

### 8.3 位移：`trpg skills random --seed 105`

```
# 種子 105（重抽 0 次）
id: skill_rand_105
name_zh: '火焰・位移 #105'
tier: 5
rarity: rare
skeleton: displace
category: spell
weapon_req: any
ap_cost: 1
scaling_attr: int
shape: {type: cone, size: 4}
effects:
- {type: push, distance: 1}
- {type: apply_status, status: poison, duration: 5}
- {type: damage, dice: 1d4, element: fire}
condition: {type: target_hp_below, permille: 294}
cost: {mana: 10, cooldown: 1}
tags: [fire, displace, damage, area, dot]

火焰・位移 #105（skill_rand_105）  階級 T5  稀有度 稀有  骨架 displace  AP 1
    1. push            2×1 格              形狀 ×2     對象 ×1    條件 ×1     ＝ 4.00（基礎 2.00）
    2. apply_status    poison 3×1.66667    形狀 ×2     對象 ×1    條件 ×1     ＝ 10.00（基礎 5.00）
    3. damage          1d4 平均            形狀 ×2     對象 ×1    條件 ×1     ＝ 5.00（基礎 2.50）
  raw ＝ 19.00
  技能條件倍率 ×0.85
  機制標籤 damage、area、displace、dot
  協同係數 area+displace ×1.1
  total ＝ raw × 條件 × 協同 ＝ 17.77
  可用預算 ＝ tier_budget 36 × AP 係數 0.50 × (1000 + 折抵 100‰) ÷ 1000 ＝ 19.80
  比例 ＝ total ÷ 可用預算 ＝ 89.7%（合格區間 70.0%–100.0%）→ 合格
  驗證：通過
```

戰鬥紀錄（種子 105，第 1 輪；目標盜賊弓手 HP 4/26，低於 29.4%，條件成立）：

```
— 法師 的回合（AP 3，移動 5，法力 99/99）
  法師 施放「火焰・位移 #105」（AP 1，法力 10，冷卻 1 回合）→ 影響 10 格
  法師 以「火焰・位移 #105」攻擊 盜賊弓手：d20=13 修正 +0 熟練 +2 = 15（目標 11）→ 命中
  盜賊弓手 被推到 (4, 1)
  盜賊弓手 獲得狀態「中毒」（5 回合）
    盜賊弓手 受到 13 點火焰傷害［骰 3］（元素修正 ×1.25），HP 4 → 0
  ＊ 盜賊弓手 倒下了！
```

更多樣本可用 `trpg skills random --seed N --count C` 產生。
