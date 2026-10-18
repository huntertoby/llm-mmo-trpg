# Phase 2C-3 完成報告：地圖類型與 build 矩陣

分支：`worktree-agent-a99e841f472df6b68`（基於 main `40ebb0b`）。範圍：`docs/phases/Phase2C計畫.md` §0、0.1 的 #2 與 #3、1、2、5、7。勝率與 6.8 標準只列出，沒有調整任何數值。

## 1. 摘要

- 引擎的墜落、致命地形、爆炸與燃燒物件傷害現在都帶 `source_id`，指標層直接使用；追不到來源者算環境（0.1 #2）。`boss_burst` 門檻改為最大 HP 的 60%（0.1 #3）。
- 地圖有必填 `archetype`，新增 `trpg map list`；非測試地圖共 10 張，涵蓋 8 種類型（新增 6 張：dark_forest、narrow_halls、open_plain、frozen_lake、lava_crossing、cliff_outpost）。
- 新增 `content/sim/builds.yaml`（6 個 build）、標準隊友（`sim_companion_fighter`、`sim_companion_archer`）與標準敵人 `std_enemy_t1`..`t5`。
- 新增 `trpg sim matrix`（排名、類型平均、6.8 兩條標準）與 `trpg sim skills [--demo] [--random N] [--seeds 10] [--jobs N]`。
- 冰窟地圖實測時暴露一個引擎 bug（滑倒的單位停在友軍格上），已修並補測試。

## 2. Commit 清單

| commit | 內容 |
|---|---|
| `df76ce5` | Carry damage sources through falls, deadly terrain and burning objects |
| `ab58cfe` | Use event sources in battle metrics; raise boss_burst threshold to 60% |
| `5ce33b1` | Add required MapDef.archetype and trpg map list |
| `5b0f21a` | Slide a unit back when it falls prone mid-move on an ally's tile |
| `3705639` | Add six maps, ice_hole terrain and thin_ice object |
| `45e320d` | Add representative builds, standard companions and tiered standard enemies |
| `77ac925` | Add trpg sim matrix and trpg sim skills |
| （本報告） | Add Phase 2C-3 report |

## 3. 驗收結果

| 項目 | 結果 | 證據 |
|---|---|---|
| 0.1 #2 傷害來源 | 通過 | `tests/engine/test_damage_sources.py`（8 項）；`tests/sim/test_metrics.py::test_falls_and_deadly_terrain_use_the_source_carried_by_the_event`、`test_fall_damage_with_a_source_counts_as_indirect_damage_of_that_unit`、`test_a_source_on_the_same_team_is_friendly_fire_not_dps`。已移除指標層的推擠者／橋推測。 |
| 0.1 #3 boss_burst ≥ 60% | 通過 | `BOSS_BURST_FRACTION_PERMILLE = 600`；`test_boss_burst_threshold_is_sixty_percent_of_max_hp` |
| 5.6-1 archetype 必填、`map list` | 通過 | `tests/content/test_map_archetypes.py`（缺 archetype 驗證失敗、`map list` 輸出） |
| 5.6-2 10 張地圖涵蓋 8 類型 | 通過 | `test_map_archetypes.py`（10 張非測試地圖、8 種類型）；每張地圖 `check_map` 與 encounter 通過 |
| 5.6-3 `sim maps --seeds 20` 全部地圖無 exception／max_actions | 通過 | 見 §5.1；全部 200 場完成，無 exception、無 max_actions。`lava_crossing` 有 1 場打滿 30 輪平手（輪數最大 30），屬 max_rounds 而非異常 |
| 5.6-4 builds、companions、標準敵人載入與預算檢查 | 通過 | `tests/content/test_sim_builds.py`、`library._check_builds` |
| 5.6-5 `sim matrix` 排名與兩條標準 | 通過（功能）；標準 2 不通過（資料，見 §5.2） | `tests/sim/test_matrix.py`（排名、平手規則、類型平均、兩條標準） |
| 5.6-6 matrix 輸出確定且與 `--jobs` 無關 | 通過 | `test_a_real_matrix_is_deterministic_and_independent_of_jobs`、`test_matrix_cli_output_is_identical_between_runs_and_jobs` |
| 5.6-7 `sim skills` 報表（百分位、>P95×1.2 標出、骨架彙總、確定性） | 通過 | `tests/sim/test_skill_report.py`（7 項）；實跑見 §5.3 |
| 全套檢查 | 通過 | `scripts/check.py` 五項全綠，1037 passed、6 slow deselected |

## 4. 設計說明

- **傷害來源**：`UnitFell`、`EnteredDeadlyTerrain` 加 `source_id`；`ObjectState.burn_source` 記錄點燃者，燃燒傷害沿用。`arrive` 的 `source_id` 為 keyword-only。
- **冰窟**：依 PM 決定，用致命地形 `ice_hole`（同 chasm）＋可破壞物件 `thin_ice`（同木橋，`breakable` ＋ `over_chasm`，max_hp 6）。冰面使用既有 ice 表面（DEX DC12 倒地檢定）。
- **滑倒 bug**：單位經過友軍格時倒地，會停在友軍格上造成後續 `IllegalActionError`。`_do_move` 追蹤走過的路徑，結束時若與另一個活單位同格，以 teleport 退回最近的空格（`tests/engine/test_move_stacking.py`）。
- **矩陣**：每張地圖內依 勝率 → 英雄 DPR → build 順序 排名；前段 = 前 `max(1, n // 3)` 名（6 個 build 為 2 名）；同一類型有兩張地圖時先平均再排名。標準 1：沒有 build 在所有類型都前段；標準 2：每個 build 至少在一種類型前段。只有一種類型時標準 1 僅供參考。
- **技能報表**：百分位線性內插；離群標記 DPR > 同階 P95 × 1.2（`DPR_OUTLIER_FACTOR_PERMILLE = 1200`）；只標出不退回。施放者只裝備該技能，加一名無技能標準弓手，對 3 名同階標準敵人，`test_flat_6x6`，max_rounds=20。
- **輸出**：標準輸出只有報表；執行時間與 `--json` 寫入訊息印在標準錯誤。

## 5. 資料

### 5.1 `trpg sim maps --seeds 20`（種子 0–19，max_rounds=30）

| 地圖 | 我方勝率 | 平均輪數 | 輪數範圍 |
|---|---|---|---|
| bridge_chasm | 75% | 4.20 | 3–7 |
| cliff_outpost | 85% | 5.05 | 4–9 |
| dark_forest | 95% | 4.25 | 2–9 |
| frozen_lake | 90% | 5.85 | 4–11 |
| lava_crossing | 90%（1 場平手） | 7.15 | 3–30 |
| narrow_halls | 90% | 4.55 | 2–9 |
| oil_depot | 45% | 4.75 | 3–7 |
| open_plain | 80% | 4.25 | 3–6 |
| ruined_fort | 85% | 4.35 | 3–6 |
| swamp | 85% | 4.20 | 2–8 |

### 5.2 `trpg sim matrix --seeds 20 --jobs 2`（6 build × 10 地圖 × 20 種子 = 1200 場，執行時間 539.2 秒）

勝率（類型內有多張地圖時取平均）：

| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 45.0% | 30.0% | 80.0% | 70.0% | 80.0% | 90.0% | 55.0% | 90.0% |
| build_fire | 75.0% | 45.0% | 70.0% | 85.0% | 90.0% | 95.0% | 40.0% | 100.0% |
| build_storm | 77.5% | 30.0% | 80.0% | 87.5% | 95.0% | 95.0% | 90.0% | 95.0% |
| build_tank | 37.5% | 10.0% | 75.0% | 65.0% | 90.0% | 90.0% | 60.0% | 100.0% |
| build_ranged | 55.0% | 20.0% | 50.0% | 82.5% | 75.0% | 100.0% | 60.0% | 100.0% |
| build_assassin | 35.0% | 15.0% | 65.0% | 67.5% | 95.0% | 95.0% | 40.0% | 80.0% |

排名矩陣（* ＝ 前段，前 2 名）：

| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake | 前段次數 |
|---|---|---|---|---|---|---|---|---|---|
| build_push | 4 | 3 | 2* | 4 | 5 | 5 | 4 | 5 | 1 |
| build_fire | 2* | 1* | 4 | 2* | 3 | 3 | 5 | 2* | 4 |
| build_storm | 1* | 2* | 1* | 1* | 1* | 2* | 1* | 4 | 7 |
| build_tank | 5 | 6 | 3 | 6 | 4 | 6 | 3 | 3 | 0 |
| build_ranged | 3 | 4 | 6 | 3 | 6 | 1* | 2* | 1* | 3 |
| build_assassin | 6 | 5 | 5 | 5 | 2* | 4 | 6 | 6 | 1 |

6.8 標準：
1. 沒有任何 build 在所有地圖類型都排名前段：**通過**（build_storm 7／8，差 frozen_lake 一個類型）。
2. 每個 build 至少在一種地圖類型排名前段：**不通過：build_tank**（前段 0 次，最佳第 3 名）。

英雄 DPR 矩陣的完整數字在 `trpg sim matrix` 的輸出中（build_storm 在 swamp 達 36.66、build_tank 多數地圖 < 10）。

### 5.3 `trpg sim skills`

- `--demo --seeds 10 --jobs 2`：23 個技能、230 場、67.6 秒。1 階 P5／P50／P95 = 8.45／11.52／14.70（門檻 17.64），**標出 `skill_fire_bolt`（DPR 20.64）**；2 階 8.97／11.32／23.54（門檻 28.25），無標出。
- `--random 200 --seeds 10 --jobs 2`：200 個技能、2000 場、340.8 秒。各階 P95（門檻）：1 階 14.44（17.33）、2 階 17.03（20.44）、3 階 16.26（19.51）、4 階 19.00（22.80）、5 階 28.68（34.42）；**沒有任何技能被標出**。
- 骨架彙總（隨機 200）：strike 平均 DPR 16.21、使用率 0.56；area 15.43；combo 14.28（使用率 0.12）；control 12.30（勝率 17.9%）；displace 12.17（勝率 17.5%）；aura 9.46。
- 示範技能中 smoke_arrow、vanish、blink、stone_wall、summon_tide、gale_kick 在此情境使用 0 次（施放者 AI 在平地對固定敵人不會選用），DPR 實為基礎武器攻擊。這是情境限制，不代表技能強度。

## 6. 待 PM 決定

1. **標準 2 不通過**：build_tank 在 8 個類型都不是前段（最佳第 3）。依規格只列出；是調 build、調坦克相關數值，還是接受「前段」定義（前 2 名）？
2. **oil_depot 勝率偏低**（我方 45%；各 build 10–45%），遠低於其他地圖（75–95%）。是否為預期的高難度地圖？
3. **build_storm 在 7／8 類型前段**，只差 frozen_lake；標準 1 雖通過但很接近邊界。
4. **前段定義**：目前為前 `max(1, n // 3)` 名。n = 6 時為 2 名；若 build 數增加，前段會隨之增加。
5. **`lava_crossing` 有 1 場打滿 30 輪平手**：疑似雙方都不願過岩漿。是否需要 AI 或地圖調整（2C-2 領域，未動）？
6. **技能報表情境**：1v3 同階標準敵人、平地、無位移需求，使 control／displace／aura 類技能 DPR 與使用率偏低或為 0。是否要為這些骨架另設情境？
7. **`skill_fire_bolt`** 在示範技能中被標出（DPR 20.64，使用 2.28 次／輪，1 AP）；隨機技能無標出。是否視為退回候選？
8. **標準敵人與隊友**的數值我依既有 tier 預算推定，未經 PM 審核；`build_*` 技能清單同。
9. **冰窟**用 deadly terrain ＋ thin_ice（依指示）；冰面的 DEX DC12 倒地檢定對 AI 的影響（敵人常在冰上倒地）尚未評估。
10. **滑倒退回**用 teleport 事件表示，客戶端將來需要處理這種位移。

## 7. 給下一個子階段的備註

- `trpg sim matrix` 全量約 9 分鐘（--jobs 2）；日常驗證可用 `--builds`、`--maps`、`--seeds` 縮小。
- 地圖類型平均目前只對 `bridge_chasm`／`swamp` 有兩張地圖的類型有意義（矩陣欄位以類型命名）。
- `sim skills` 的 caster 與敵人是以技能階級對應 `std_enemy_t{tier}`；新增階級需補標準敵人。
- 未修改 2C-2 區域（`trpg.engine.ai`、`runner.py`、`ai_profiles.yaml`、`trpg battle`／`trpg sim maps` 的指揮官參數）。

## 8. 附錄：frozen_lake 開局（種子 0）

```
戰鬥開始：冰湖（12×10），種子 0
=== 第 1 輪 ===
    0  1  2  3  4  5  6  7  8  9  10 11
 0  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
 1  0.  0.  0.  0.i 0.i 0.i 0.i 0.i 0.i 0.  0.  0.
 2  0.  0.  0|  0.i 0O  0.i 0.i 0.i 0.i 0.  0.  0.
 3  0A  0.  0.  0.i 0.i 0.i 0:  0.i 0.i 0.  0_  0d
 4  0.  0B  0[  0.i 0.i 0.i 0.i 0.i 0O  0.  0c  0.
 5  0.  0C  0.  0O  0.i 0.i 0.i 0.i 0.i 0[  0b  0.
 6  0.  0_  0.  0.i 0.i 0:  0.i 0.i 0.i 0.  0.  0a
 7  0.  0.  0.  0.i 0.i 0.i 0.i 0O  0.i 0|  0.  0.
 8  0.  0.  0.  0.i 0.i 0.i 0.i 0.i 0.i 0.  0.  0.
 9  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
  圖例：[ 木箱、_ 矮牆、| 石柱、: 薄冰、i 冰（表面）
  盜賊1 從 (11, 6) 移動到 (6, 6)（消耗 5 移動）
  盜賊1 敏捷檢定：d20=6 +2 = 8（DC 12）→ 失敗
  盜賊1 獲得狀態「倒地」
```
