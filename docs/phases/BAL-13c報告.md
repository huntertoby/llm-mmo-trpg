# BAL-13c 報告：連鎖衰減與雷電擴散每輪一次

依 `docs/phases/PhaseBAL計畫.md` 第 8 節「BAL-13c」（玩法決定 #77、#78；06 6.5「連鎖衰減」、05 互動規則表下的擴散規則）。

## 1. 做了什麼

**#77 連鎖衰減（引擎）**
- `core.yaml` 新欄位 `chain_falloff_permille: 250`、`chain_floor_permille: 250`（`CoreRules`）。`chain` 形狀第 n 個目標（從 0 起）的威力 ＝ `max(1000 − n × 250, 250)`‰：100／75／50／25%。
- `SkillArea.chained` 標記「`units` 是連鎖依序跳到的單位」（只有 `compute_area` 算出連鎖時為真）；`Cast.chain_permille(unit)` 依該順序給倍率，不在連鎖裡的單位（例如施放者自己）為 1000。
- 套在傷害（`attack_damage`，乘進 `multiplier_permille`）、治療、聖光雙效的治療、護盾；狀態、表面、位移等非數值效果照常。
- `DamageEffect`／`damage_dealt` 新欄位 `chain_permille`（已含在 `multiplier_permille`，供紀錄分開顯示）；戰鬥紀錄文字多一段「（連鎖衰減 ×0.75）」，「加成」的換算扣掉它。
- **擴散基準也乘衰減**：`base_amount`（雷電擴散的基準）原本不含格擋等倍率；連鎖衰減是攻擊本身變弱，所以乘在基準上（跳到第 3 個人的那一擊，它引發的擴散也只剩一半）。見待決 2。

**#78 雷電擴散每輪一次（引擎）**
- 單位狀態新欄位 `conducted_round`（最近一次受到 `cause: conduct` 傷害的輪數，0 為從未），在戰鬥狀態內、隨 `clone` 複製，可重播。
- 結算 `cause: conduct` 的傷害時：本輪已受過擴散就不結算（不發事件），否則記下本輪。互動表產生擴散效果時也先濾掉本輪已受過的單位（同一批效果裡的重複由結算時的檢查擋下）。
- 「一輪」用 `state.round`（所有單位都行動完一次才 +1；輪與輪之間的環境回合算在剛結束的那一輪）。不論幾次雷擊、幾個施放者；直接命中（`cause: attack`）不受影響、也不記錄。

**#77 預算（`content/skill_shapes.yaml`）**
- 原本 `base 1000 ＋ 每跳 250‰`（每多一個目標的期望份量 0.25，不衰減）。改成每跳 `250 × 該跳衰減後威力`：1 跳 1000＋187.5、2 跳 ＋125、3 跳 ＋62.5，四捨五入：

| 跳數 | 舊倍率 | 新倍率 |
|---|---|---|
| 1 | 1250 | **1188** |
| 2 | 1500 | **1313** |
| 3 | 1750 | **1375** |

- `tests/skillgen/test_chain_falloff_budget.py` 由 `core.yaml` 的衰減欄位重算對照，並檢查只降不升。

**內建連鎖技重算預算**

| 技能 | 舊 | 新倍率下（不改） | 改後 |
|---|---|---|---|
| `skill_chain_lightning`（2 跳） | 2d8，75.0% | 2d8，65.6%（過弱） | **2d8＋1，72.9%**（第一個目標平均 9 → 10） |
| `skill_spark_chain`（1 跳） | 1d8，74.8% | 1d8，71.0%（合格） | 不改 |

- `chain_lightning` 候選：3d6（76.6%）會讓完整技能的增益 +190‰ 超過 +150‰ 上限（`test_complete_3w5b`，骰子一階跳太大、沒有細旋鈕可補），2d10（80.2%）改變較大，取最接近原比例且完整技能仍在 +120～150‰ 的 2d8＋1（+150‰）。
- 其他用到 `chain` 形狀的（閃現 `reshape_chain`、修正技能 `shape_to: chain`、組合器）照新倍率自動計價。

**#78 擴散倍率**：`content/interactions.yaml` 兩條 `lightning_conducts_*` 的 `damage_permille` 1000 → 500。

**說明文字**：`chain` 形狀的 `description_zh` 與工坊三筆說明（原文與玩家語氣）補「每跳威力 −25%（最低 25%），狀態照常」；雷電元素說明補「同一輪內每個單位最多受一次擴散傷害」；格子資訊的擴散句補「（傷害 ×0.5，每輪每個單位最多一次）」（讀互動表的倍率）；`InteractionOutcome` 文件字串補規則。

**紀錄格式**：`LOG_FORMAT` `/91` → `/92`（事件、效果與單位狀態多了欄位，結算改變）；`runner.py` 文件字串與 `docs/phases/戰鬥紀錄格式變更.md` 補這一版，測試字面值（`battle-log/91` 9 處、`endswith("/91")` 3 處、roguelite 夾具 1 處）一起改。

## 2. 模擬（30 場 × 10 圖，新前段判定）

腳本 `scripts/bal13c_matrix.py`：`run` 只跑用 chain／雷的 build（storm、striker、runeweaver、tank〔雷之手〕、push〔魔劍斬〕；10 圖 × 種子 0～29，`--jobs 4`，260 秒），`merge` 把它們的格子換進 BAL-12d 全矩陣（`docs/phases/BAL-12/12d_matrix.json`，同種子）再用 `assemble_matrix` 重算名次與 06 6.8 兩條標準。其他 build 沒有 chain／雷，結算與種子不變（BAL-13a 試驗的 fire 基準 79.0% 與 12d 相同；BAL-12e 的強度只在填了 `magnitude_permille` 的技能生效，內建技能都沒填），所以沿用 12d 的格子。產出：`docs/phases/BAL-13/13c_matrix_part.json`、`13c_matrix_storm_conduct1000.json`、`13c_merge.txt`、`13c_merge_conduct1000.txt`、`13c_matrix_stats.txt`、`13c_matrix.log`。

| build | BAL-12d | 本段（擴散 500‰） | 擴散改回 1000‰（其餘同本段） | DPR 12d → 本段 | 輪數 12d → 本段 |
|---|---|---|---|---|---|
| storm | 79.7%（13a 基準 81.3%） | **73.0%** | 75.0% | 31.2 → 23.2 | 3.6 → 4.1 |
| push | 59.3% | 60.3% | — | 8.4 → 8.3 | 5.3 |
| striker | 56.3% | 56.3% | — | 12.9 → 12.8 | 4.8 |
| tank | 47.7% | 47.7% | — | 3.5 → 3.3 | 7.4 |
| runeweaver | 47.0% | 46.3% | 47.3% | 10.4 → 10.1 | 4.7 |

- storm 73.0% ≥ 70%，照規格維持 500‰；1000‰ 那組只是參考（規格要求 < 70% 才量，因為只多 1 分鐘就一起量了）。兩組差 2 點，在 300 場的雜訊（約 ±2.5pt）內，storm 的下修主要來自連鎖衰減與每輪一次。
- storm 沼澤 24 → 18 勝（DPR 66.1 → 35.4）、暗林 DPR 32.2 → 21.6、熔岩渡口 39.5 → 24.7：擴散重的圖降最多。
- striker、tank 的勝場在 10 張圖全都不變，只有沼澤的 DPR 小降（雷電擴散很少發生）；push 的魔劍斬不是連鎖，+1.0 是雜訊。
- **新前段判定**：storm 仍是 **全類型前段**（8 類名次 1～7：bridge 1、ruined_heights 7、forest 6、frozen_lake 5、corridor 5、oil_depot 4、open_plain 5、swamp 3；1000‰ 時 1～7 名、更靠前）。無前段名單和 12d 相同（9 個：assassin、striker、charger、banisher、gambler、seer、winged、wallburn、runeweaver）。
- 勝率 > 75% 的剩 fire 79.0%（本段沒動）。

## 3. 快照變動

- 行為快照 `tests/skillgen/fixtures/refactor_3wr2.json` 重產：完整技能 1／301（`skill_chain_lightning`）、升階重配 2／301（`skill_chain_lightning`、`skill_spark_chain`：連鎖倍率變了，重配的骰子與跳數跟著變）、閃現 0／129。
- CLI 輸出快照：`UPDATE_CLI_SNAPSHOTS=1` 重產，3 筆變動：`skills_list`、`skills_show_all`（連鎖閃電 2d8 → 2d8＋1）、`battle_swamp_striker_5`（沼澤的擴散倍率與每輪一次）。`battle_halls_storm_9` 等其他戰鬥不變。
- client fixture：`glossary.json`（雷電元素說明、擴散規則句）、`skill_icons.json`（1 行：隨機組合器抽到的技能因連鎖倍率改變）重產。`vfx_random_skills.json` 沒有測試檢查、建立後從未重產，沒有動。OpenAPI 不含事件，不變。

## 4. 測試

- 新增 `tests/engine/test_chain_conduct_bal13c.py`：連鎖傷害每跳 1000／750／500／250、較陡衰減時的下限、治療與護盾衰減而狀態照常、單體不衰減；擴散每輪一次（跨雷擊與施放者、直接命中照常、下一輪重新計算、同一批兩次雷擊只擴散一次）。
- 新增 `tests/skillgen/test_chain_falloff_budget.py`（形狀倍率對照衰減公式）。
- 寫死 1000‰ 的 4 個擴散測試：`test_environment.py` 兩個改讀互動表倍率（擴散 ＝ `max(基準 × damage_permille ÷ 1000, min_damage)`）；`test_phase1c_decisions.py` 兩個用 `tests/engine/helpers.py` 新的 `with_conduct_permille(state, 1000)`（規則包副本），斷言不變。
- 寫死形狀倍率的：`test_skill_shaping.py`（`shape_to: chain` 預算）改讀 content；`test_budget.py::test_shape_multiplier_table`（4.2 倍率表）改新值。
- 沒有需要重挑種子的測試。

## 5. 檢查

ruff check、ruff format --check、mypy（919 檔）、lint-imports（7 kept）通過。pytest：engine 3906 通過；skillgen 相關檔＋content＋narrative＋`tests/api` 兩個夾具與玩家文字測試 2925 通過（含 slow 的行為快照）；cli＋api 461 通過；roguelite＋sim＋架構 372 通過；CLI 輸出快照（slow）重產後通過。skillgen＋content＋narrative＋api＋roguelite 全目錄在第二個 commit 之前跑過一次（5643 通過，3 個失敗已在第二個 commit 修正：倍率表、完整技能 +150‰、圖示夾具），之後只重跑相關檔。重播 `trpg battle --map swamp --seed 7 --log-json` → `battle replay` 一致（100 個動作、303 個事件）。

## 6. 待 PM 決定

1. **（規則）擴散基準也乘連鎖衰減**：規格沒寫。現行把衰減乘在 `base_amount`（跳到第 3 個人那一擊引發的擴散也只剩 50%），格擋與穿透則照舊不影響基準。若要「擴散一律用未衰減的傷害」，改 `handlers._damage` 的 `base_amount` 一行。
2. **（原型數值）`chain_lightning` 2d8 → 2d8＋1**（72.9%，第一個目標平均 +1）：重算後 65.6% 低於下限，必須加；3d6（76.6%）較接近原比例，但完整技能 +190‰ 超過 +150‰ 上限，所以選 2d8＋1。`spark_chain` 新倍率下 71.0% 仍合格，沒有加強（規格寫「可以」變強，取保守）。
3. **（原型數值）連鎖形狀倍率 1188／1313／1375**：照「每跳期望份量 0.25 × 衰減後威力」校正、四捨五入；狀態等非數值效果不衰減，但同一個形狀倍率也乘在狀態點數上，所以 **只上狀態的連鎖技變便宜了**（例：連鎖減速 3 跳原本 ×1.75、現在 ×1.375）。要不要讓非數值效果維持舊倍率（需要預算分開算形狀倍率）？
4. **（範圍）不算 #77／#78 的連鎖**：雷靈（`summon_thunder_spirit`）站在水裡的攻擊連鎖（武器特性 `chain_targets`，已有自己的 500‰ 倍率）不是 `chain` 形狀、也不是互動表的擴散，兩條新規則都沒套用。
5. **（規則）「一輪」的邊界**：用 `state.round`；輪與輪之間的環境回合（例如天氣、表面）造成的擴散算在剛結束的那一輪。同一輪被擋下的擴散不發事件（紀錄裡看不到「本輪已受過擴散」），要的話可以加一個事件。
6. **（量測方式）** 只重跑 5 個用 chain／雷的 build，其他 18 個沿用 BAL-12d 的格子（理由見第 2 節）；規格寫「30 場全矩陣」，全量在平行上限 4 時約 75 分鐘，超過時間預算。合併後的排名就是新判定的全矩陣排名，但若 PM 要逐格重跑，需另排時間。
7. **（文字）** 卡片的形狀行（「連鎖（射程 5，跳躍 2，跳躍距離 3）」）沒有寫衰減，只有形狀說明、工坊說明（實作者初稿，待玩法 PM 改寫）、雷電元素說明與格子資訊寫了。要不要在卡片的形狀行加「每跳 −25%」？
8. **（原型數值）storm 73.0%** 仍是唯一的全類型前段 build；`twin_strike`（BAL-13a 的另一個選項）沒動。
