# BAL-5 完成報告｜AI 行為修正（B19、B1、B5）

規格：`docs/phases/PhaseBAL計畫.md` 與派工說明（方向由玩法 PM 定）。只動 AI 模組（`src/trpg/engine/ai/`）、AI 權重的 schema（`src/trpg/content/environment.py` 的 `AiWeights`／`SummonAiRules`／`AiProfileTable`）與 AI 權重資料（`content/ai_profiles.yaml`）；沒有動傷害、規則欄位、敵人與法力數值、Boss 陣容。戰鬥紀錄結構沒變，`LOG_FORMAT` 不遞增。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| B19 近距離武器站位 | 由武器資料推導「最佳距離」（`range_mod` 傷害千分比最高的最近距離）；最佳距離 ≤ 2 格且比射程近的武器＝近距離武器（目前只有霰彈槍，不寫死 ID）。位置價值加 `close_range`（打得到的敵人中距離千分比最高者 × 權重 ÷ 1000），保持距離只計比最佳距離更近的敵人 | 新 `engine/ai/weapon_range.py`；`utility.py`（`_keep_radius`、`_close_range_term`） |
| B19 根因修正：單發火器不開火 | 位置價值以「已裝填」複本計算（`_loaded`）。原本開火讓彈匣變空，威脅、被壓制等位置項目以為「打不到任何敵人」，霰彈槍在 1 格內的普攻分數是負的（實測 −13），AI 改防禦或結束回合 | `utility.py` |
| B1 範圍技加分 | 技能分數加 `multi_target` × 預期多打到的敵人數（要命中判定的敵人算命中率、不用判定且最少結果就受傷的算 1，扣掉最大的一個；只打到 1 名時 0） | `utility.py`（`extra_targets`） |
| B5 灌注估值 | `infuse_value_permille` 700 → 1000、`infuse_threat_damage` 4 → 2；灌注分數另乘「省下的 AP」＝技能 AP ÷ 灌注 AP（至少 1） | `engine/ai/infuse.py`（`ap_ratio`）、`utility.py` |
| B5 特性估值 | 護盾（`shield_round_permille`）、拉扯（`pull_round_points`）、纏繞（`snare_likelihood_permille`）、高台（`platform_points`，每名遠程友方一次性） | `engine/ai/summon.py`（`_trait_value`） |
| 資料 | 表格層級新增 `weapon_ai`、`skill_ai`（同 `objective_ai` 的方式填入每個行為模式的 `weights`）；`summon:` 加 4 欄 | `content/ai_profiles.yaml` |
| 測試 | `tests/engine/test_ai_close_range_bal5.py`（8）、`test_ai_multi_target_bal5.py`（3）、`test_summon_ai_bal5.py`（8） | — |

## 2. 前後對照

量測腳本放在 scratchpad（不入庫），用與 BAL-3 相同的模擬函式（`run_matrix`、`_run_packs`、`run_attack_flow`）；「前」用同一份程式碼、在記憶體把新權重設 0 或舊值，或用 BAL-3 時的程式碼（數字與 BAL-3 報表一致）。

### B19 霰彈槍（白板 build × 10 張預設地圖 × 10 種子；DPR＝打到所有目標的總傷害 ÷ 存活輪數）

| 指標 | 前 | 後 | 目標 |
|---|---|---|---|
| 霰彈槍勝率 | 32.0% | **48.0%** | — |
| 霰彈槍 DPR | 1.28 | 3.97 | — |
| DPR／單手劍（5.12 → 5.09） | 24.9% | **78.1%** | 75–125% ✓ |
| 攻擊距離分布（3 種子 × 10 圖探針） | 1 格 5、2 格 7、3 格 52、4 格 13（77 次） | 1 格 36、2 格 37、3 格 39、4 格 12（128 次） | 往 1～2 格靠 |
| 手槍（同樣受惠於「已裝填」修正） | 53%／DPR 3.76 | 58%／5.02 | 只列 |

`close_range` 掃描（勝率／DPR 比）：0＝48%／69.9%（只有裝填修正）、12＝44%／73.3%、24＝46%／75.5%、**40＝48%／77.6%（採用）**。單手劍勝率 57% 不變。未調任何傷害。

### B1 範圍技選用（`build_skill_archer`／`build_attack_archer`）

| 指標 | 前 | 後 | 門檻 |
|---|---|---|---|
| 範圍戰：有 ≥ 2 敵可打時選範圍技（20 種子，3-32d 同探針） | 46%（18／39） | **78%**（29／37） | ≥ 70% ✓ |
| 同上，Boss 戰（參考） | — | 48%（18／37） | — |
| Boss 擊殺輪數比（含設限，204 場） | 0.87 | **0.88** | ≥ 0.90 ✗ |
| Boss 擊殺輪數比（只計打倒的場） | 0.90 | 0.96 | — |
| 範圍清場輪數比（含設限） | 1.18 | **1.17** | ≥ 1.15 ✓ |

`sim_attack_flow --diagnose` 等效（`run_attack_flow`，每格 34 種子 × 6 格＝204 場）。`multi_target` 48 時 Boss 比值反而 0.80（雜訊與「技能流 Boss 擊殺率 29%」主導），所以維持 24。Boss 擊殺輪數比仍差 0.02：含設限的平均被沒打倒的場（以 30 輪計）大幅拉動，技能流 Boss 擊殺率 32～35% 是主因；依規格「仍不達標才動基礎普攻」，這屬 PM 決定（見第 4 節）。

### B5 召喚物（4～7 個起始包 × 6 張地圖〔5 張正式圖＋bandit_lair〕× 7 種子）

| 指標 | 前 | 後 |
|---|---|---|
| 灌注次數／有召喚場：dev_summoner | 0.16 | 0.23 |
| 同上：dev_spirit | 0.21 | 0.53 |
| 同上：dev_summoner_bone | 0.39 | 0.65 |
| dev_summoner × bandit_lair 40 場灌注次數 | 2 | 4 |
| 高台圖騰包勝率 | 71.4% | **73.8%**（輪數 5.6 → 6.4） |
| 守護靈包／吸引圖騰包／藤蔓包勝率（「前」＝特性估值為 0） | 71.4%／64.3%／69.0% | 78.6%／73.8%／73.8% |

**灌注頻率大降的原因**（探針：dev_summoner 6 圖 × 2 種子，記錄每個施放者回合的灌注候選）：灌注候選 13 次中 11 次輸給「自己直接施放同一招火焰箭」。兩者花同樣 1 AP、同樣法力，但灌注分數再乘 0.7 與偏悲觀的存活率（每個威脅 4 點）≈ 只剩直接施放的 1/3，所以只有施放者自己打不到時才會灌注。3H-2 讓主角法力依屬性提高（`core.yaml resources`），施放者幾乎每回合都放得起火焰箭，這種「自己打不到」的情況變少——這部分是推論，沒有回到 3H 前的提交驗證。修正後灌注與直接施放在同樣條件下公平比較（存活率仍然扣），所以頻率上升但不會蓋過直接施放；要更常灌注只能讓灌注「優於」直接施放（`infuse_value_permille` 1300 時 dev_summoner 0.29、骷髏 0.90，勝率不變），見待決 #3。

**AI 有沒有把遠程角色帶上高台**：有召喚高台的我方回合中，遠程角色站在高台上約 30%（86／291 回合，前）→ 23%（111／480，後；高台存在的回合變多）。圖騰被放在離敵人平均 4.5 格處。試過把高台召喚物改放在施放者旁邊、遠離敵人：圖騰被打倒 28 → 8～10 隻，但勝率掉到 50%——圖騰實際的價值是**替我方吸引火力**，所以已撤回這個改動，只保留一次性的高台估值。高台估值若乘輪數，AI 會反覆召喚圖騰（64 → 90 隻）、戰鬥拖長而勝率不變，所以改成一次性。

## 3. 測試與檢查

- `ruff check`、`ruff format --check`（src、tests、scripts）、`mypy src`、`lint-imports`（7 條契約）：通過。
- pytest（`-m "(slow or not slow) and not llm"`）：`tests/engine` 3874 passed（2 個種子覆蓋測試先失敗，見下）、`tests/sim`＋`roguelite`＋`narrative`＋`api` 962 passed（1 個先失敗，見下）、`tests/cli`＋`skillgen`＋`shared`＋`test_architecture` 4034 passed（快照先失敗，見下）、`tests/content` 通過。
- 重播：`trpg battle --map swamp --seed 7 --log-json` ＋ `trpg battle replay` 通過（60 個動作、223 個事件）。
- 確定性：新項目都是整數／`Fraction` 運算，沒有亂數、沒有依賴 set 順序（`extra_targets` 用 dict、只取總和與最大值）。

AI 軌跡改變而改的既有測試（只換種子或地圖，斷言不變）：

| 測試 | 改動 |
|---|---|
| `tests/engine/test_status_determinism.py` | 種子 (7, 10) → (9, 10)（7 不再出現流血） |
| `tests/engine/test_reaction_events_3d3.py` | build_ranged：open_plain 種子 3 → dark_forest 種子 1（open_plain 0～39 都沒觸發掩護射擊） |
| `tests/sim/test_skill_fuzz.py` | 回氣觸發的種子 2 → 0 |
| `tests/cli/snapshots/cli_output_hashes.json` | `UPDATE_CLI_SNAPSHOTS=1` 重產（`battle_oil_depot_fire_7`、`battle_swamp_striker_5` 兩個雜湊） |

`noqa`：`extra_targets` 一處 `PLR2004`（「至少 2 個敵人」的常數 2，語意直接）。沒有新增複雜度類 `noqa`。沒有跑 `scripts/check.py`。模擬總計約 30 分鐘（背景與前景合計）。

## 4. 待 PM 決定（AI／原型數值，玩法 PM 可定）

1. **B19 權重** `weapon_ai.close_range: 40`（掃描 0／12／24／40；40 時 DPR 比 77.6%）。近距離武器的判定：最佳距離 ≤ 2 格且比射程近；火槍（遠距加成，最佳距離 4）**刻意不套用**，只受「已裝填」修正影響。是否也讓遠距加成武器往最佳距離靠，請決定。
2. **B1 權重** `skill_ai.multi_target: 24`（每多打到一名敵人 24 分；弓手傷害權重 6，約 4 點傷害）。範圍戰選用率 78% 已達標；**Boss 擊殺輪數比 0.88 仍差 0.02**（只計打倒的場 0.96），依規格下一步是動基礎普攻，請 PM 決定是否進行，或改用「只計打倒的場」判讀。
3. **B5 灌注**：`infuse_value_permille` 700 → 1000、`infuse_threat_damage` 4 → 2、乘省下的 AP。BAL-3 待決 #2 要的驗收數字：目前 0.23～0.65 次／有召喚場；要不要訂目標（例如 ≥ 0.5），以及是否接受 > 1000‰（讓灌注優於直接施放）。
4. **B5 特性初值**：`shield_round_permille: 1000`、`pull_round_points: 3`、`snare_likelihood_permille: 400`、`platform_points: 2`（一次性，每名遠程友方）。高台的價值實際上在「圖騰吸引火力」而不是高台本身；遠程角色站上高台約 23～30% 的回合。是否要 AI 主動帶遠程角色上高台（會讓圖騰離敵人遠、失去誘餌效果）需要玩法上的取捨。
5. **與 BAL-4b 合併**：本段改了 AI 軌跡，BAL-4b 的勝率斷言若受影響由 PM 處理；兩段都動 `content/ai_profiles.yaml` 的機率不高（BAL-4b 不改 AI 權重）。
