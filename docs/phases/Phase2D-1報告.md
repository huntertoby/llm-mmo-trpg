# Phase 2D-1 完成報告：保護、增益與嘲諷

分支：`main`（基於 `efe8fa0`）。範圍：`docs/phases/Phase2D計畫.md` 第 3 節（2D-1）。沒有做第 4 節（2D-2）。

## 1. 摘要

- 新增 5 個增益／嘲諷狀態（`guarded`、`empowered`、`hasted`、`regenerating`、`taunted`）、護盾（`shielded`，帶 `amount`）、`shield`／`cleanse` 原語、6 個新內建技能、`support` 行為模式與有效屬性。
- 有效屬性統一走 `effective_attribute`，原始碼掃描測試保證沒有漏網。組合器、fuzz、報表、渲染、metrics 全部接上。
- `build_tank` 改為嘲諷＋護盾並採 `guard`，新增 `build_support`、`build_healer`（共 8 個 build）。
- check.py 五項全過（1141 passed）；fuzz 1000 無例外；completion 與 matrix 皆能跑完（completion 異常 0）。
- `LOG_FORMAT` 升為 `trpg-battle-log/7`；沒有任何既有測試因軌跡改變而更新期望值。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `d23841e` | 增益狀態、護盾與淨化原語、有效屬性、嘲諷、6 個新技能與對應測試（3.1–3.4、3.6） |
| `f083608` | 組合器支援 shield／cleanse 與 aura 的 `single` 形狀；fuzz 摘要列出原語與狀態（3.5） |
| `9a365d3` | `support` AI 測試、護盾 metrics、戰鬥紀錄渲染（3.7） |
| 本報告前一個 commit | `content/sim/builds.yaml`：tank 改版、新增 support／healer（3.8） |
| 本 commit | 本報告 |

## 3. 驗收結果（3.10）

1. check.py 五項（ruff、格式、mypy、lint-imports、pytest）全過：1141 passed、7 deselected，import-linter 3 kept。✅
2. 3.9 的 11 項測試（檔案：`tests/engine/`）：
   1. `test_support_statuses.py`：`test_guarded_takes_seventy_percent_of_the_damage`、`test_guarded_and_vulnerable_multiply_in_order_and_floor_once`
   2. `test_empowered_adds_two_to_every_effective_attribute`、`test_empowered_changes_the_hit_chance_and_preview_matches_the_roll`、`test_empowered_boosts_spell_scaling_and_the_status_save`
   3. `test_hasted_multiplies_the_move_points_by_one_and_a_half`、`test_hasted_and_slow_multiply_in_order`
   4. `test_regenerating_heals_at_turn_start_and_lasts_three_turns`、`test_regenerating_is_halved_by_poison`、`test_regenerating_never_exceeds_max_hp`
   5. `test_shield.py`：`test_shield_amount_is_dice_plus_half_the_scaling_attribute`、`test_a_second_shield_keeps_the_larger_amount_and_refreshes_the_duration`、`test_damage_hits_the_shield_before_hit_points`、`test_a_partial_absorb_damages_the_rest_and_removes_the_depleted_shield`、`test_percentage_damage_ignores_the_shield`、`test_a_shield_expires_with_its_duration_and_keeps_its_amount_while_ticking`、`test_preview_matches_the_actual_damage_through_a_shield`、`test_a_shielded_state_round_trips_through_json`
   6. `test_cleanse_removes_only_harmful_statuses_in_id_order`、`test_cleanse_without_harmful_statuses_emits_nothing`、`test_the_validator_rejects_cleanse_against_enemies`
   7. `test_a_skill_can_apply_defending_to_an_ally_like_the_defend_action`
   8. `test_taunt.py`：`test_attacking_anyone_but_the_taunter_has_disadvantage`、`test_a_taunt_without_a_source_has_no_effect`、`test_the_taunt_is_removed_when_its_source_goes_down`、`test_reapplying_the_taunt_changes_the_source_to_the_latest_caster`、`test_the_taunting_roar_skill_taunts_adjacent_enemies`、`test_a_taunted_ai_attacks_the_taunter_even_when_another_target_is_weaker`、`test_a_taunted_ai_that_cannot_reach_the_taunter_acts_normally`
   9. `test_support_ai.py`：`test_a_support_unit_protects_a_hurt_ally_in_melee_instead_of_attacking`、`test_buffs_are_not_recast_on_a_full_health_ally_who_already_has_them`、`test_the_shield_gain_is_scored_by_the_shield_weight`、`test_a_partially_remaining_buff_is_only_worth_the_extra_duration`、`test_cleanse_is_valued_by_the_statuses_it_removes`、`test_the_support_profile_exists_and_values_support_over_damage`、`test_a_non_support_profile_still_prefers_its_own_job`
   10. `test_effective_attribute.py`：`test_only_effective_attribute_and_base_attribute_read_attributes_directly`、`test_base_attribute_is_only_used_for_initiative`
   11. `tests/cli/test_budget_cli.py`（全部內建技能含新技能通過預算）與 `tests/sim/` 的 fuzz 測試；另有 `scripts/skill_fuzz.py` 1000 次（見 3）。

   全部通過。✅
3. `scripts/skill_fuzz.py --count 1000`：1000/1000 組合、驗證、可施放，例外 0；AI 對戰 100 場（我方勝 97、敵方勝 3、平手 0）。原語：`shield` 81、`cleanse` 44。狀態：`guarded` 36、`empowered` 35、`hasted` 20、`regenerating` 29、`taunted` 38、`defending` 6。✅
4. `trpg skills budget --all`：通過 29 個、違規 0 個（含 6 個新技能）。✅
5. `trpg sim completion --seeds 3 --jobs 2`：270 場，exception 0、max_actions 0、draw 0 —— 通過（97.8 秒）。✅
6. `trpg sim matrix --seeds 3 --jobs 2`：8 個 build × 10 張地圖共 240 場全部跑完，異常場次 0（結果見第 5 節，不解讀）。✅
7. `trpg battle --map open_plain --seed 7 --allies hero_fighter,hero_stormcaller,hero_archer --ally-commander protect_weakest --log-json f` 後 `trpg battle replay f`：「重播驗證通過：100 個動作、290 個事件，最終狀態一致」。含 build 英雄的戰鬥（種子 2）重播同樣通過（171 個動作、503 個事件）；節錄見第 8 節。✅
8. 因軌跡改變而更新期望值的既有測試：**無**。以下既有測試因資料或格式變動而更新（不是軌跡）：
   - `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py`：紀錄格式 `/6` → `/7`。
   - `tests/cli/test_budget_cli.py`：技能數 23 → 29。`tests/sim/test_skill_report.py`：24 → 30 個技能。
   - `tests/content/test_skill_rules_content.py`：aura 的形狀與核心原語、`min_rarity` 集合加入 shield／cleanse 與新狀態。
   - `tests/engine/test_status_ai.py`：`status_values` 集合加入 `taunted`。
   - `tests/skillgen/test_budget.py`：`budget_points` 表；「`defending` 不可施加」改為 `shielded` 不可施加。
   - `tests/skillgen/test_validate.py`：不可用預算的狀態改用 `shielded`、aura 禁用形狀改用 line、有益狀態旗標集合。
   - `tests/content/test_sim_builds.py`：build 清單由 6 個改為 8 個。

## 4. 設計說明

- **有效屬性**：`effective_attribute = 基礎屬性 ＋ 狀態 attr_bonus 總和`；先攻只用 `base_attribute`。命中、防禦、豁免、法術縮放、護盾量、preview、AI 評分都用有效屬性。
- **護盾**：`StatusInstance.amount`；在所有倍率之後、HP 之前吸收，只吸收骰點傷害（百分比與致命模式不吸收）。新護盾取較大量並刷新持續時間。事件：`ShieldGained`、`ShieldAbsorbed`（先於 `DamageDealt` 與耗盡的 `StatusRemoved`）、`DamageDealt.absorbed`。
- **嘲諷**：軟性強制。攻擊者帶 `forces_target` 且目標不是嘲諷來源時給劣勢；來源倒下或逃離時移除；重新施加時來源更新為最新施放者。
- **淨化**：移除所有非有益狀態，依 ID 排序。
- **AI**：`support` 行為模式；`_support_gains` 只算技能（護盾量、友方狀態價值、淨化價值）；被嘲諷的單位場景焦點為嘲諷者，若有分數大於 0 的行動能打到嘲諷者就只在這些行動與移動中選。
- **預算**：`shield` 以骰平均計、`cleanse` 固定 3；`shielded` 無 `budget_points`，不能由 `apply_status` 施加。
- **其他**：metrics 與批次報表新增「護盾吸收／場」；renderer 補上護盾與淨化文字。

## 5. 數據表

預算（節錄新技能）：`skill_war_hymn` 86.4%；`skill_taunting_roar` 93.5%；`skill_renewal` 99.7%；`skill_purify` 71.1%。完整輸出見 `trpg skills budget --all`。

Matrix（勝率，地圖類型內有多張地圖時取平均；未解讀）：

| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake |
|---|---|---|---|---|---|---|---|---|
| build_push | 50.0% | 0.0% | 66.7% | 66.7% | 100.0% | 100.0% | 100.0% | 66.7% |
| build_fire | 100.0% | 66.7% | 66.7% | 83.3% | 100.0% | 100.0% | 100.0% | 100.0% |
| build_storm | 100.0% | 66.7% | 66.7% | 83.3% | 100.0% | 100.0% | 100.0% | 66.7% |
| build_tank | 66.7% | 0.0% | 0.0% | 83.3% | 100.0% | 66.7% | 33.3% | 100.0% |
| build_ranged | 83.3% | 100.0% | 33.3% | 83.3% | 100.0% | 100.0% | 100.0% | 0.0% |
| build_assassin | 66.7% | 66.7% | 66.7% | 83.3% | 100.0% | 100.0% | 100.0% | 66.7% |
| build_support | 66.7% | 0.0% | 33.3% | 66.7% | 100.0% | 66.7% | 33.3% | 100.0% |
| build_healer | 33.3% | 66.7% | 66.7% | 83.3% | 100.0% | 66.7% | 100.0% | 66.7% |

排名前段次數：push 0、fire 6、storm 7、tank 0、ranged 2、assassin 0、support 1、healer 0。6.8 標準：(1) 通過；(2) 不通過（push、tank、assassin、healer 沒有任何類型排名前段）。

英雄 DPR 平均：tank 與 healer 約 0–3，support 約 2.8–7.7（輔助型 build 的價值不在 DPR，目前矩陣沒有衡量保護／治療貢獻）。

## 6. 待 PM 決定

1. `DamageDealt.amount` 保持「護盾前的名目傷害」，另設 `absorbed`；實際損失為 `hp_before - hp_after`。統計與渲染已用實際值。
2. 嘲諷優先於 `focus` 指令；來源為 None 的嘲諷無效果。
3. 預算偏離規格：`skill_war_hymn` 持續時間 4（預設 2 只有約 65%）；`skill_purify` 只收法力 1、無冷卻（規格 mana 4／cooldown 2 僅 64%）；`skill_taunting_roar` 法力 0、冷卻 2。
4. `shield`、`cleanse` 的 `min_rarity` 設為 common（規格沒寫）。
5. `cleanse` 也會移除 `prone`（視為非有益）。
6. 再生的治療算進來源的 `healing_done`，技能報表的 `avg_healed` 可能包含它。
7. `guarded` 與 `vulnerable` 依序相乘 700×1250，只在最後無條件捨去一次。
8. 護盾沒有禁止施加在敵人身上（`cleanse` 才有 `forbid_affects`）。
9. 防禦（Defend）動作的 preview 不計 `ally_status_values`，維持與 `defend_score` 一致。
10. matrix 標準 2 不通過：tank／healer／support 的 DPR 與勝率都偏低，目前矩陣只量 DPR 與勝率，沒有量保護價值（建議 2D-2 或之後討論指標與 build 調整，我沒有動數值）。

## 7. 給下一個子階段（2D-2）的備註

- `effective_attribute` 是唯一入口；新增任何讀屬性的地方請走它，掃描測試會擋。
- `shield_absorbed` 已在 `UnitMetrics`／`TeamSummary`；2D-2 要加新指標可沿用同一條線。
- `ally_status_values` 與 `AiWeights.support`／`shield` 是新欄位；調整行為時優先改 `content/ai_profiles.yaml`。
- `build_support`／`build_healer` 使用 `frost_staff`（focus），`skill_frost_shackle`、`skill_sanctuary` 武器需求相容，不需替換技能。
- 全量 completion（`--seeds 20`）與矩陣解讀都留給 2D-2。

## 8. 附錄：代表性 CLI 輸出

`trpg battle replay`（種子 7，`--ally-commander protect_weakest`）：

```
重播驗證通過：100 個動作、290 個事件，最終狀態一致（open_plain，種子 7）。
```

含 build 英雄的戰鬥（open_plain，種子 2，我方 build_tank／build_healer／build_support）節錄：

```
— 坦克英雄 的回合（AP 3，移動 5，法力 20/20）
我方指令：保護 坦克英雄
  坦克英雄 施放「守護之盾」（AP 1，法力 4，冷卻 1 回合）→ 影響 1 格
    坦克英雄 獲得 13 點護盾
— 治療英雄 的回合（AP 3，移動 5，法力 40/40）
  治療英雄 施放「回春」（AP 1，法力 5，冷卻 1 回合）→ 影響 1 格
  坦克英雄 獲得狀態「再生」（3 回合）
  ...
    治療英雄 的護盾吸收了 2 點傷害，剩餘 13
重播驗證通過：171 個動作、503 個事件，最終狀態一致（open_plain，種子 2）。
```
