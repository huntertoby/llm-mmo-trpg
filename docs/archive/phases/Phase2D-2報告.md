# Phase 2D-2 完成報告：負面狀態、術士與收尾

分支：`main`（基於 `66da005`）。範圍：`docs/phases/Phase2D計畫.md` 第 4 節（2D-2）。

## 1. 摘要

- 新增四個負面狀態（`feared`、`silenced`、`blinded`、`marked`）與四個欄位（`fear_source`、`blocks_spells`、`attack_range_cap`、`grants_advantage_against`）、控制類別 `mental`、4 個術士技能與 `build_warlock`（共 9 個 build）。
- AI：`status_values` 加入四個新狀態，沉默對沒有可用法術技的目標價值為 0；其餘照合法動作行動。
- `trpg battle --ally-build`、矩陣「保護矩陣」與保護指標（`shield_provided`、`teammate_survival`）。
- 全量收尾：fuzz 1000 無例外；slow 測試 3 通過；completion 1800 場、matrix 1620 場，三種異常皆 0。
- 沒有任何既有測試因軌跡改變而更新期望值；`LOG_FORMAT` 維持 `/7`。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `266d3b3` | 四個狀態與欄位、`mental`、4 個術士技能、`build_warlock`、AI 價值與沉默判斷、情境測試（4.1–4.5） |
| `c107a80` | `trpg battle --ally-build`、保護指標與保護矩陣（4.0、4.6-4） |
| 本報告的 commit | 本報告；另含 renderer 文字小修（`source_lost` 改為「來源離場」，恐懼也會用到） |

## 3. 驗收結果（4.7）

1. `uv run python scripts/check.py` 五項全過（ruff、format、mypy、lint-imports、pytest：1172 passed、7 deselected；報告完成後與 renderer 小修後再跑一次，同樣五項全過）。✅
2. 4.5 的測試（`tests/engine/test_negative_statuses.py`，另 `tests/cli/test_budget_cli.py`）：
   1. 情境：`test_feared_unit_cannot_step_closer_to_the_source`、`test_fear_only_restricts_the_distance_to_its_own_source`、`test_feared_attacks_have_disadvantage_against_anyone`、`test_fear_is_removed_when_its_source_goes_down`、`test_reapplying_fear_changes_the_source`、`test_a_cornered_feared_unit_can_still_end_its_turn`、`test_a_feared_ai_unit_never_proposes_a_move_toward_the_source`、`test_silence_blocks_spells_but_keeps_weapon_skills_and_basic_attacks`、`test_blinded_attacks_are_capped_at_two_tiles_and_have_disadvantage`、`test_blinded_unit_still_walks_and_can_end_its_turn`、`test_marked_targets_are_attacked_with_advantage`、`test_marked_concealed_targets_can_still_be_selected_at_range`
   2. mental：`test_mental_statuses_use_the_mental_diminishing_window[feared|silenced]`、`test_applying_a_mental_status_records_the_window`、`test_bosses_do_not_convert_mental_statuses[feared|silenced]`
   3. preview：`test_preview_matches_the_roll_for_advantage_statuses[feared|blinded|marked]`
   4. AI：`test_cunning_ai_silences_a_spellcaster_but_not_a_unit_without_spells`
   5. 預算：`tests/cli/test_budget_cli.py`（33 個內建技能通過）；`trpg skills budget --all`：通過 33 個、違規 0 個。
   - 另：`tests/cli/test_battle_cli.py::test_ally_build_uses_build_heroes_and_fills_with_companions`、`test_ally_build_rejects_unknown_builds_and_allies_together`；`tests/sim/test_protection_metrics.py`（3 項）。✅
3. 4.6 的 1–5 見第 5、6 節；exception、max_actions、draw 皆為 0。✅
4. `trpg battle --map ruined_fort --seed 1 --ally-build build_warlock --ally-commander protect_weakest --log-json f` 再 `trpg battle replay f`：「重播驗證通過：85 個動作、226 個事件，最終狀態一致（ruined_fort，種子 1）。」另 open_plain 種子 5：77 個動作、232 個事件一致。節錄見第 8 節。✅
5. 因軌跡改變而更新期望值的既有測試：**無**。以下是資料／數量變動（不是軌跡）：
   - `tests/content/test_skill_rules_content.py`：`min_rarity` 表加入 `marked`（common；其餘三者 rare）。
   - `tests/skillgen/test_budget.py`：`budget_points` 表加入四個狀態。
   - `tests/engine/test_status_ai.py`：`status_values` 集合加入四個狀態。
   - `tests/cli/test_budget_cli.py`：技能數 29 → 33。`tests/sim/test_skill_report.py`：30 → 34 個技能。
   - `tests/content/test_sim_builds.py`：build 清單 8 → 9 個。

## 4. 設計與實作說明

- **欄位與規則**（皆經 `trpg.engine.rules.statuses` 的函式判斷，引擎其他地方不看狀態 ID）：
  - 恐懼：`path_map`（可達格、合法動作、AI 規劃）與 `plan_move`（逐步驗證）都禁止讓與來源的曼哈頓距離變小的一步；強制位移不受影響；攻擊有劣勢（`advantage_sources`，所以 `preview` 自動一致）；來源倒下或離場時與嘲諷同一條路徑移除（`StatusRemoved` 原因 `source_lost`），刷新時來源改為最新施放者。
  - 沉默：`skill_problem` 排除 `category: spell`，所以不在合法動作內；武器技與基本攻擊照常。
  - 致盲：`attack_problem` 與單位選取（`_unit_target_problem`，含友方單位）限制距離 ≤ 2；攻擊有劣勢。格子／方向／自身型技能不受限。
  - 被標記：`advantage_sources` 給優勢；`concealment_problem` 對帶有者不成立（隱蔽的劣勢仍在，與優勢抵消為一般擲骰）。
- **`mental`**：`control_group` 新增 `mental`，走既有的遞減與 `boss_converted_status`（只轉換 `hard`），所以 Boss 不轉換。
- **數值**：`feared` 2 回合／5 點／rare／wis；`silenced` 1／5／rare／wil；`blinded` 1／4／rare／wis；`marked` 2／4／common／wis。`status_values` 加 `{feared: 6, silenced: 5, blinded: 5, marked: 4}`（初值，未經模擬）。
- **AI**：`_status_gains` 的價值函式多帶目標；`blocks_spells` 的狀態對「沒有法力足夠的法術技」的目標價值為 0。恐懼、致盲、被標記沒有另外加權重。
- **技能**（`trpg skills budget --all` 全過）：`skill_hex_bolt` 91.5%、`skill_dread_gaze` 70.4%、`skill_hush` 70.4%、`skill_blinding_dark` 78.0%。
- **build_warlock**：屬性比照法師，武器 `fire_staff`，`ai_profile: cunning`，技能為四個新技能。
- **`trpg battle --ally-build`**：build 英雄 ＋ companions（不足 3 人補齊）；與 `--allies` 互斥；未知 build 結束碼 2。
- **保護指標**：`UnitMetrics.shield_provided`（護盾吸收量歸給該護盾最後一次施加者）；`TemplateRow.shield_provided`、`teammate_survival`（我方實例：結束時未倒下的隊友 ÷ 隊友人數）；矩陣新增「保護矩陣」，格式為 `治療量／護盾吸收量／承受傷害／隊友存活率`，不進排名與 6.8 標準。

## 5. 收尾數據（4.6）

### 5.1 `scripts/skill_fuzz.py --count 1000`（22.6 秒）

組合成功 1000/1000、通過驗證 1000/1000、可施放 1000/1000；AI 對戰 100 場（我方勝 98、敵方勝 2、平手 0）；**例外 0**。2D 全部新原語與新狀態都出現：

```
原語（效果數）：
  apply_status        470   24.5%
  cleanse              44    2.3%
  create_obstacle      26    1.4%
  create_surface      169    8.8%
  damage              657   34.3%
  destroy_object       25    1.3%
  heal                 89    4.6%
  knock_prone         108    5.6%
  lower_terrain        29    1.5%
  pull                 59    3.1%
  push                 97    5.1%
  raise_terrain        27    1.4%
  shield               81    4.2%
  teleport             35    1.8%
施加的狀態（效果數）：
  bleed                27    5.7%
  blinded              18    3.8%
  burning              30    6.4%
  concealed            13    2.8%
  defending             6    1.3%
  empowered            33    7.0%
  feared               20    4.3%
  guarded              33    7.0%
  hasted               17    3.6%
  marked               38    8.1%
  poison               24    5.1%
  prone                 6    1.3%
  regenerating         28    6.0%
  root                 12    2.6%
  silenced             17    3.6%
  slow                 23    4.9%
  stun                  4    0.9%
  taunted              42    8.9%
  vulnerable           42    8.9%
  weaken               37    7.9%
施加的狀態（效果數）：
  bleed                27    5.7%
  blinded              18    3.8%
  burning              30    6.4%
  concealed            13    2.8%
  defending             6    1.3%
  empowered            33    7.0%
  feared               20    4.3%
  guarded              33    7.0%
  hasted               17    3.6%
  marked               38    8.1%
  poison               24    5.1%
  prone                 6    1.3%
  regenerating         28    6.0%
  root                 12    2.6%
  silenced             17    3.6%
  slow                 23    4.9%
  stun                  4    0.9%
  taunted              42    8.9%
  vulnerable           42    8.9%
  weaken               37    7.9%
```

### 5.2 `uv run pytest -q -m slow`（161 秒）

| 測試 | 結果 |
|---|---|
| `tests/sim/test_completion.py::test_every_map_and_config_completes_without_exception_max_actions_or_draw` | PASSED |
| `tests/sim/test_skill_fuzz.py::test_one_thousand_skills_pass_everything_and_the_summary_is_reproducible` | PASSED |
| `tests/skillgen/test_random_composer.py::test_one_thousand_seeds_are_all_valid_and_spread_out` | PASSED |
| `tests/engine/test_demo_balance.py::test_demo_map_win_rate_and_length[bridge_chasm]` | XFAIL（平衡，延後） |
| `…[ruined_fort]` | XFAIL（平衡，延後） |
| `…[oil_depot]`、`…[swamp]` | XPASS（依 2C-4 決定 #7 不動） |

非平衡的 slow 測試全部通過。

### 5.3 `trpg sim completion --seeds 20 --jobs 2`（1800 場，557.3 秒）

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
執行時間 557.3 秒（1800 場，--jobs 2）
```

### 5.4 `trpg sim matrix --seeds 20 --jobs 2`（9 個 build × 10 張地圖 × 20 種子 ＝ 1800 場，8 分 37 秒；只記錄）

#### 勝率矩陣（地圖類型內有多張地圖時取平均）
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 62.5% | 25.0% | 70.0% | 70.0% | 80.0% | 95.0% | 70.0% | 90.0% |
| build_fire | 82.5% | 55.0% | 70.0% | 80.0% | 100.0% | 90.0% | 80.0% | 90.0% |
| build_storm | 95.0% | 40.0% | 80.0% | 77.5% | 100.0% | 90.0% | 70.0% | 80.0% |
| build_tank | 47.5% | 30.0% | 40.0% | 57.5% | 95.0% | 80.0% | 30.0% | 70.0% |
| build_ranged | 77.5% | 35.0% | 65.0% | 80.0% | 95.0% | 100.0% | 50.0% | 50.0% |
| build_assassin | 57.5% | 15.0% | 65.0% | 72.5% | 90.0% | 95.0% | 45.0% | 75.0% |
| build_support | 62.5% | 20.0% | 60.0% | 60.0% | 100.0% | 85.0% | 55.0% | 85.0% |
| build_healer | 55.0% | 25.0% | 70.0% | 70.0% | 95.0% | 95.0% | 55.0% | 75.0% |
| build_warlock | 77.5% | 45.0% | 60.0% | 72.5% | 95.0% | 85.0% | 75.0% | 90.0% |

#### build 英雄 DPR 矩陣
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 6.85 | 6.61 | 9.19 | 5.21 | 6.49 | 6.85 | 6.79 | 8.38 |
| build_fire | 18.17 | 20.35 | 13.51 | 15.28 | 14.82 | 16.61 | 17.53 | 12.40 |
| build_storm | 20.03 | 20.35 | 43.65 | 14.78 | 16.98 | 16.14 | 20.45 | 11.32 |
| build_tank | 1.41 | 2.25 | 2.17 | 1.32 | 1.35 | 0.94 | 2.54 | 2.18 |
| build_ranged | 13.14 | 12.15 | 11.42 | 11.00 | 10.34 | 13.26 | 12.87 | 8.83 |
| build_assassin | 6.75 | 6.95 | 8.58 | 5.61 | 6.24 | 5.23 | 7.66 | 7.87 |
| build_support | 4.76 | 6.36 | 5.64 | 4.07 | 4.76 | 5.22 | 7.53 | 4.11 |
| build_healer | 1.58 | 2.31 | 2.61 | 1.67 | 1.83 | 1.19 | 2.92 | 1.33 |
| build_warlock | 17.08 | 17.94 | 18.54 | 13.68 | 14.90 | 16.74 | 18.53 | 13.15 |

#### 保護矩陣（build 英雄每場平均；只列數字，不進排名與 6.8 標準）：治療量／護盾吸收量（它施放的護盾）／承受傷害／隊友存活率
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 0.0／0.0／42.4／51.2% | 0.0／0.0／58.6／20.0% | 0.0／0.0／47.7／52.5% | 0.0／0.0／40.3／47.5% | 0.0／0.0／39.4／67.5% | 0.0／0.0／35.0／82.5% | 0.0／0.0／48.0／60.0% | 0.0／0.0／36.5／67.5% |
| build_fire | 0.0／0.0／26.0／68.8% | 0.0／0.0／35.3／37.5% | 0.0／0.0／32.5／55.0% | 0.0／0.0／34.1／72.5% | 0.0／0.0／18.2／90.0% | 0.0／0.0／25.9／85.0% | 0.0／0.0／30.4／67.5% | 0.0／0.0／26.1／75.0% |
| build_storm | 0.0／0.0／29.0／72.5% | 0.0／0.0／36.6／32.5% | 0.0／0.0／26.9／67.5% | 0.0／0.0／35.8／71.2% | 0.0／0.0／22.8／92.5% | 0.0／0.0／25.4／85.0% | 0.0／0.0／34.0／57.5% | 0.0／0.0／26.3／60.0% |
| build_tank | 0.0／10.4／44.2／31.2% | 0.0／22.8／52.0／22.5% | 0.0／14.9／48.7／20.0% | 0.0／10.3／42.4／36.3% | 0.0／5.5／17.8／47.5% | 0.0／8.0／34.2／50.0% | 0.0／20.5／55.2／12.5% | 0.0／4.1／29.4／42.5% |
| build_ranged | 0.0／0.0／30.6／57.5% | 0.0／0.0／43.4／20.0% | 0.0／0.0／42.5／52.5% | 0.0／0.0／33.7／73.8% | 0.0／0.0／31.5／80.0% | 0.0／0.0／32.6／95.0% | 0.0／0.0／42.0／32.5% | 0.0／0.0／39.5／40.0% |
| build_assassin | 0.0／0.0／43.1／50.0% | 0.0／0.0／48.9／15.0% | 0.0／0.0／45.8／50.0% | 0.0／0.0／44.6／60.0% | 0.0／0.0／39.2／67.5% | 0.0／0.0／31.4／90.0% | 0.0／0.0／47.5／37.5% | 0.0／0.0／40.2／67.5% |
| build_support | 0.0／0.0／33.2／47.5% | 0.0／0.0／38.7／15.0% | 0.0／0.0／29.8／47.5% | 0.0／0.0／31.4／48.8% | 0.0／0.0／12.1／82.5% | 0.0／0.0／20.9／77.5% | 0.0／0.0／33.5／42.5% | 0.0／0.0／21.0／65.0% |
| build_healer | 49.2／6.2／49.0／46.2% | 59.5／6.2／63.4／17.5% | 65.9／8.0／50.0／60.0% | 50.8／4.6／46.0／61.3% | 44.6／2.4／18.3／77.5% | 62.6／1.7／31.6／87.5% | 61.9／5.1／55.2／45.0% | 40.8／2.1／43.8／52.5% |
| build_warlock | 0.0／0.0／29.0／62.5% | 0.0／0.0／36.9／42.5% | 0.0／0.0／33.8／57.5% | 0.0／0.0／34.9／66.2% | 0.0／0.0／25.7／87.5% | 0.0／0.0／24.3／82.5% | 0.0／0.0／31.1／60.0% | 0.0／0.0／23.7／72.5% |

#### 排名矩陣（* ＝ 前段，前 3 名）
| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake | 前段次數 |
|---|---|---|---|---|---|---|---|---|---|
| build_push | 5 | 6 | 3* | 6 | 9 | 2* | 4 | 3* | 3 |
| build_fire | 2* | 1* | 2* | 1* | 2* | 5 | 1* | 2* | 7 |
| build_storm | 1* | 3* | 1* | 3* | 1* | 6 | 3* | 5 | 6 |
| build_tank | 9 | 5 | 9 | 9 | 7 | 9 | 9 | 8 | 0 |
| build_ranged | 4 | 4 | 5 | 2* | 5 | 1* | 7 | 9 | 2 |
| build_assassin | 7 | 9 | 6 | 5 | 8 | 3* | 8 | 6 | 1 |
| build_support | 6 | 8 | 8 | 8 | 3* | 8 | 5 | 4 | 1 |
| build_healer | 8 | 7 | 4 | 7 | 6 | 4 | 6 | 7 | 0 |
| build_warlock | 3* | 2* | 7 | 4 | 4 | 7 | 2* | 1* | 4 |

#### 6.8 標準檢查（前段 ＝ 前 3 名，9 個 build）
1. 沒有任何 build 在所有地圖類型都排名前段：通過
2. 每個 build 至少在一種地圖類型排名前段：不通過：build_tank、build_healer

**與 2C-4 矩陣的對照**（2C-4 為 6 個 build，前段 ＝ 前 2 名）：

- 原有 5 個 build（push、fire、storm、ranged、assassin）的勝率與 DPR 與 2C-4 **逐格相同**（新狀態不影響不使用它們的 build；對手的 AI 也沒有改動）。
- `build_tank`（2D-1 改版為嘲諷＋護盾）：前段類型數 2C-4 為 2（swamp、open_plain）→ 現在 **0**（9 個 build 的前 3 名）；勝率大致下降（swamp 75% → 40%、open_plain 80% → 30%、bridge_chasm 57.5% → 47.5%），英雄 DPR 5–8 → 1–2.5。
- 新增 build：`build_warlock` 前段 4 次（bridge_chasm、oil_depot、open_plain、frozen_lake），英雄 DPR 約 13–19；`build_support` 前段 1 次；`build_healer` 前段 0 次。
- 標準 2：2C-4 不通過者為 `build_assassin`（現在前段 1 次，通過）；現在不通過者為 `build_tank`、`build_healer`（均為 0 次）。這是平衡問題，不調整。
- 保護矩陣：`build_healer` 每場平均治療 41–66、護盾吸收 2–8；`build_tank` 護盾吸收 4–23、承受傷害 18–55；各 build 的隊友存活率主要隨地圖難度（oil_depot 最低）而非 build 變化。tank 與 healer 在保護矩陣上有數字，但沒有轉化為勝率。

## 6. Phase 2D 驗收（`docs/專案計畫.md` 第 14 節）

| # | 項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 效果模板 `shield`、`damage_reduction`、`taunt`、`buff_attr`、`haste`、`heal_over_time`、`cleanse` | ✅ | `shield`、`cleanse` 為原語（`content/skill_primitives.yaml`）；其餘為狀態（決定 B）：`guarded`（減傷）、`taunted`（嘲諷）、`empowered`（`attr_bonus`）、`hasted`、`regenerating`；情境測試見 2D-1 報告 3 節與 `tests/engine/test_shield.py`、`test_support_statuses.py`、`test_taunt.py` |
| 2 | 狀態 `fear`、`silence`、`blind`、`mark`（`marked`） | ✅ | `feared`、`silenced`、`blinded`、`marked`（`content/statuses.yaml`）；`tests/engine/test_negative_statuses.py` |
| 3 | 技能可以施加 `defending` | ✅ | `defending` 有 `budget_points: 2`；`skill_purify` 施加之；`test_a_skill_can_apply_defending_to_an_ally_like_the_defend_action` |
| 4 | 效用 AI 能評分並使用這些效果 | ✅ | `ally_status_values`、`shield`／`support` 權重、`support` 行為模式、嘲諷服從（2D-1）；四個負面狀態的 `status_values`、沉默判斷（`test_cunning_ai_silences_a_spellcaster_but_not_a_unit_without_spells`）；第 8 節的實戰紀錄顯示 AI 實際施放 |
| 5 | 驗收：新模板與狀態都有資料檔、預算、解譯與情境測試 | ✅ | 資料檔 `content/statuses.yaml`、`content/skills/`；預算 `trpg skills budget --all` 33/33；解譯與情境測試如上 |
| 6 | 驗收：隨機組合器能組出含新模板的技能，1,000 個技能無例外 | ✅ | 5.1：shield 81、cleanse 44，所有新狀態出現，例外 0 |
| 7 | 驗收：build 矩陣補上保護型與輔助型 build 後重跑並附報表 | ✅ | 5.4：9 個 build（tank 改版、support、healer、warlock）全量重跑，含保護矩陣；只記錄，未調整 |

另外：「完成度」（completion）全量異常 0；slow 測試通過。

## 7. 待 PM 決定

1. `skill_hex_bolt` 的 `marked` 持續 1（規格未指定；預設 2 會讓預算 119.6% 且核心占比不足）。
2. `skill_dread_gaze`、`skill_hush` 法力 3、無冷卻（規格 5 法力＋冷卻只有 61–67%，低於下限 70%）；兩者都貼著 70.4% 的下限，平衡階段調整時要同時看預算。
3. `build_warlock` 武器用 `fire_staff`，AI 為 `cunning`；沒有調整任何數值。
4. 致盲的距離上限也套用在 **友方** 單位目標的技能（規格寫「以單位為目標的技能」）；格子、方向、自身型技能不受限。
5. 沉默的價值判斷以「有法力足夠的法術技」為準，不看冷卻與 AP。
6. 恐懼只限制「主動移動的每一步」；藉機攻擊、撤離與強制位移不受影響。恐懼來源不在場上時限制不存在。
7. 控制回合統計（`CONTROL_STATUSES`）仍只有 stun、root、slow，沒有加入 feared、silenced、blinded，以免改動既有報表；要衡量術士的控制時需要擴充。
8. 保護矩陣的「護盾吸收量」歸給施放者，不是承受者；矩陣標準 2（每個 build 至少一種類型前段）仍不通過：`build_tank`、`build_healer`，它們的價值不在勝率，需要平衡階段決定指標或調整數值。
9. 規格說 `marked` 不另加 AI 權重；AI 會對已被標記的目標重複施放「咒印飛彈」（傷害仍有分數，狀態只是刷新），沒有特別避免。
10. renderer 的 `source_lost` 文字改為「來源離場」（原為「嘲諷者離場」），因為恐懼也會用到；只影響顯示。

## 8. 附錄：代表性 CLI 輸出

`trpg battle --map ruined_fort --seed 1 --ally-build build_warlock --ally-commander protect_weakest`（節錄）：

```
  術士英雄 施放「咒印飛彈」（AP 1，法力 3）→ 影響 1 格
  術士英雄 以「咒印飛彈」攻擊 盜賊2：d20（優勢 18、1）=18 修正 -1 熟練 +2 = 19（目標 11）→ 命中
    盜賊2 受到 13 點暗影傷害［骰 5］，HP 14 → 1
  術士英雄 對 盜賊2 施加「被標記」（智力 16 vs 感知 10）：d20=9 修正 +3 熟練 +2 = 14（目標 11）→ 施加成功
  盜賊2 刷新狀態「被標記」（1 回合）
  術士英雄 施放「恐懼凝視」（AP 1，法力 3）→ 影響 1 格
  術士英雄 以「恐懼凝視」攻擊 盜賊2：d20（優勢 1、20）=20 修正 -1 熟練 +2 = 21（目標 11）→ 自然 20，暴擊！
  術士英雄 對 盜賊2 施加「恐懼」（智力 16 vs 感知 10）：d20=6 修正 +3 熟練 +2 = 11（目標 11）→ 施加成功
  盜賊2 獲得狀態「恐懼」（2 回合）
  術士英雄 結束回合
  ...
  盜賊2：HP 1/30 法力 ... 武器 匕首［恐懼2、被標記1］
  ...
  術士英雄 受到 10 點物理傷害［骰 6］，HP 10 → 0
  ＊ 術士英雄 倒下了！
  盜賊2 的「恐懼」解除了（來源離場）
```

```
重播驗證通過：85 個動作、226 個事件，最終狀態一致（ruined_fort，種子 1）。
```

## 9. 給補模板 B（2E）的備註

- **需要事件觸發的狀態**：`regenerating`、`burning` 等回合開始效果仍是狀態欄位（`on_turn_start_*`）；2E 的 `on_turn_start` 觸發可以統一這些欄位。`marked`（被命中時的額外效果，例如「引爆標記」）、`feared`（恐懼者受傷時解除）是最自然的 `on_damaged`／`on_hit` 候選。
- **來源綁定的狀態**：嘲諷與恐懼都有「來源離場即移除」（`is_removed_with_source`）；若 2E 新增以來源為條件的被動、姿態或陷阱，請沿用這個函式，不要再各自判斷。
- **護盾與嘲諷 vs. 「替隊友擋攻擊」反應技**：現在護盾綁在單位身上，吸收只認「骰值傷害」；擋攻擊的反應若把傷害轉給守護者，應該在護盾與減傷之前改寫目標，再讓守護者的護盾／減傷照常結算。嘲諷是「攻擊其他人有劣勢」的軟強制；擋攻擊反應不應該重新成為嘲諷者的攻擊目標，否則兩者規則會互相抵消。`shield_provided` 的歸屬是「最後一次施加者」，反應技轉移傷害時要決定吸收歸誰。
- **致盲、恐懼與反應**：目前藉機攻擊與反應技的目標限制不看 `attack_range_cap`；若 2E 的反應技也要受致盲影響，需要在反應的目標驗證加上同一個檢查。
