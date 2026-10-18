# Phase 2B-1 完成報告：新狀態與控制遞減

## 1. 摘要

7 種新狀態（緩速、定身、暈眩、虛弱、易傷、流血、中毒）、技能施加狀態時的抵抗判定、控制遞減、Boss 硬控轉換、預覽的抵抗成功率、AI 的狀態價值，以及 4 個示範技能全部完成。數值效果都以 `statuses.yaml` 的欄位表示，移動點數、傷害、治療的狀態倍率各自集中在 `engine/rules/statuses.py` 與 `handlers.py` 的單一計算點。`uv run python scripts/check.py` 五項全過，**764 個測試**（2A-2 結束時 702 個；4 個 slow 平衡測試預設不跑）。效能：四張示範地圖與 `test_heights_8x8` 每個動作（含 AI）的中位數都在 4.7 ms 以下，沒有退化，不需要啟用決定 #2 的最佳化。勝率與技能使用見第 5 節（只列出、不調整）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `5d032e5` | 7 種狀態與數值效果：`StatusDef` 新欄位（`move_permille`、`prevents_move`、`skip_turn`、`damage_dealt_permille`、`damage_taken_permille`、`healing_received_permille`、`save_attr`、`control_group`）、`engine/rules/statuses.py`、暈眩跳過回合（`TurnSkipped`）且不能反應、定身擋主動移動、傷害／治療倍率（`DamageDealt.status_ppm`、`Healed.received_permille`）、`core.yaml` 的 `control_dr_rounds`／`control_dr_resist_permille`／`boss_control_conversion`、`UnitState.control_dr`、`LOG_FORMAT` → `/5`；測試 `test_statuses.py`（17） |
| `72a6303` | 抵抗判定、控制遞減、Boss 轉換：`engine/control.py`（`plan_status`、`status_effect`、`status_save_chance`）、事件 `StatusSaveRolled`／`StatusResisted`／`StatusConverted`、解譯器接上、`preview` 的 `TargetPreview.status_chances`（`StatusChance`）、CLI 渲染；測試 `test_status_control.py`（22） |
| `d435cc2` | AI 與示範技能：`ai_profiles.yaml` 的 `status_values`、`_status_gains`、4 個技能（寒鎖、放血斬、盾擊、毒霧）與裝備、AI 情境測試 `test_status_ai.py`（9）、確定性測試 `test_status_determinism.py`（2） |
| `6481df6` | 內容測試 `tests/content/test_statuses_content.py`（12 個含參數化） |
| （本報告的 commit） | `docs/phases/Phase2B-1報告.md` |

## 3. 驗收條件逐條結果

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `check.py` 五項全過；2A 的驗收測試仍成立 | ✅ | `uv run python scripts/check.py`：ruff check／ruff format／mypy／lint-imports／pytest 全部通過（764 passed, 4 deselected）。2A 的測試只改了三處：`test_skill_ai_scenarios.py::test_only_the_boss_the_archer_and_the_shieldbearer_have_skills`（盾衛現在有盾擊，原本的「只有頭目與弓手有技能」更新）、`LOG_FORMAT` 的 `/4` → `/5`（`test_battle_cli.py`、`test_skills_cli.py`）、`test_state_clone.py`（新欄位 `control_dr`） |
| 2 | 每種新狀態至少一個測試驗證效果 | ✅ | 緩速：`test_slow_halves_the_move_points_rounding_down`（速度 5 → 2）。定身：`test_root_blocks_voluntary_movement_but_not_forced_movement`（`legal_actions` 沒有 `Move`、`resolve` 拒絕、被推擊仍會移動）、`test_without_root_the_unit_can_move`。暈眩：`test_stun_skips_the_whole_turn_and_expires`、`test_stun_still_ticks_damage_and_cooldowns_at_turn_start`、`test_a_stunned_unit_cannot_react`（對照：沒暈眩時藉機攻擊會觸發）。虛弱／易傷：`test_weaken_scales_the_attackers_attack_damage`（10 → 7）、`test_weaken_only_applies_to_attack_damage`、`test_vulnerable_scales_dice_damage_taken`（10 → 12）、`test_vulnerable_does_not_scale_percentage_damage`、`test_weaken_and_vulnerable_multiply_and_floor_once`（疊乘 9.375 → 9，而非逐步捨去的 8；16 → 15）、`test_status_multipliers_respect_the_minimum_damage`。流血／中毒：`test_bleed_and_poison_tick_at_turn_start`（物理／毒素各一）、`test_bleed_lasts_three_turns`、`test_poison_halves_healing_received`、`test_poison_healing_rounds_down`。內容層：`test_statuses_content.py`（持續、`save_attr`、`control_group`、各數值欄位） |
| 3 | 抵抗判定：成功與失敗各一、友方不擲、表面不擲 | ✅ | 失敗（施加）：`test_a_failed_save_applies_the_status`；成功（被抵抗）：`test_a_successful_save_resists_the_status`（`StatusSaveRolled.applied=False` ＋ `StatusResisted`，被抵抗不記錄遞減）；公式：`test_the_save_uses_the_ratio_formula`；先命中才擲：`test_the_status_needs_a_hit_before_the_save`；無 `save_attr` 命中即施加：`test_statuses_without_save_attr_apply_on_hit`；友方與自己：`test_no_save_is_rolled_against_allies_or_self`；表面（把火焰表面的進入效果改成定身）：`test_statuses_from_surfaces_are_applied_without_a_save` |
| 4 | 控制遞減 | ✅ | `test_the_second_root_inside_the_window_uses_150_percent_defense`（兩次 `StatusSaveRolled`：防禦值 12 → 18、`diminished` 為 True、`modifier` 分別等於 `hit_table.modifier(16, 12)` 與 `modifier(16, 18)`，且第二次較低；`control_dr == {"movement": 輪數 + 2}`）；期滿恢復：`test_the_window_covers_round_r_plus_2_and_then_recovers`（第 1、3 輪遞減、第 4 輪恢復）；類別互不影響：`test_control_groups_do_not_affect_each_other`（`movement` 與 `hard` 雙向、無類別的虛弱不受影響）；記錄：`test_a_status_application_records_the_diminishing_window_for_its_group` |
| 5 | Boss：暈眩 → 緩速，事件標示轉換 | ✅ | `test_stun_on_a_boss_becomes_slow`（`StatusConverted(stun → slow)`、轉換後仍擲抵抗（敏捷）、持續 1 回合、遞減記在 `movement`）、`test_a_converted_status_keeps_an_explicit_duration`、`test_a_converted_status_can_still_be_resisted`、`test_a_boss_is_not_converted_for_other_control_or_for_non_bosses`、`test_the_demo_boss_carries_the_boss_tag_and_the_shield_bash_stuns` |
| 6 | 固定骰值時預覽與實際一致，且顯示抵抗成功率 | ✅ | `test_preview_reports_the_resist_chance`（`TargetPreview.status_chances`，與逐一列舉 d20 相同，`resist_chance` ＝ 1 − 施加率）、`test_preview_matches_the_resolution_with_fixed_rolls`（參數化：抵抗成功 → 與 `min_state` 的狀態與遞減記錄相同；抵抗失敗 → 與 `max_state` 相同）、`test_preview_includes_the_diminishing_penalty`、`test_preview_reports_the_converted_status_for_a_boss`、`test_preview_omits_statuses_without_a_save` |
| 7 | AI 情境 | ✅ | ①：`test_a_free_melee_unit_closes_the_distance`（對照：沒定身就走過去）、`test_a_rooted_melee_unit_never_tries_to_move`（`legal_actions` 與 `rank` 都沒有 `Move`，選擇防禦或結束回合）、`test_a_rooted_melee_unit_uses_a_skill_when_something_is_in_reach`（定身的頭目旁邊有英雄 → 攻擊或技能）、`test_a_rooted_ranged_unit_still_shoots`、`test_a_slowed_unit_still_picks_an_action`（移動不超過 2 格）。②：`test_the_mage_roots_an_approaching_melee_enemy`（只有寒鎖時選寒鎖打逼近的盜賊）、`test_the_mage_with_a_damage_skill_too_still_chooses_by_score`（火焰箭與寒鎖都被評分，寒鎖高於普攻）、`test_the_mage_does_not_reroot_an_already_rooted_enemy`、`test_status_values_are_defined_for_every_new_status` |
| 8 | 確定性 | ✅ | `test_status_determinism.py::test_same_seed_same_battle_and_replay_with_the_new_statuses`（種子 3、7：兩次相同、`replay` 重播一致，戰鬥中出現暈眩、流血、中毒、易傷、抵抗判定與 `turn_skipped`）、`test_property_random_legal_actions_with_the_new_statuses`（hypothesis：隨機合法動作、純函式、`control_dr` 類別合法、暈眩的單位不會成為行動者）；2A 的 `test_skill_determinism.py`、`test_determinism.py` 全數仍通過（英雄現在多帶新技能） |
| 9 | 效能 ≤ 8 ms | ✅ | 見第 5 節效能表（最高 4.7 ms，`ruined_fort`） |
| 10 | 報告附勝率、輪數與技能使用表 | ✅ | 見第 5 節 |

## 4. 設計與實作說明

**模組結構**

- `content/battle.py::StatusDef`：新欄位全部有預設值（1000／False／None），欄位說明寫在 docstring 與 `statuses.yaml` 開頭註解。`control_group` 必須搭配 `save_attr`（載入時檢查）。`Ruleset` 檢查 `boss_control_conversion` 的來源是 `hard` 類別的狀態、目標存在；`REQUIRED_STATUSES` 擴為 11 個；`ai_profiles.yaml` 的 `status_values` 引用的狀態必須存在（`ContentError`）。
- `engine/rules/statuses.py`：`move_points_for_turn`、`is_rooted`、`skip_turn_status`、`damage_dealt_permille`、`damage_taken_permille`、`healing_received_permille`。多個狀態影響同一欄位時依狀態 ID 排序相乘、逐步捨去（目前每個欄位只有一個狀態會改變它）。
- 計算點各一處：移動點數在 `turns.start_turn`；主動移動在 `movement.available_move_budget`（`legal_actions`、`reachable_tiles`、AI 路徑共用）與 `battle.plan_move`；傷害在 `handlers._damage`；治療在 `handlers._heal`；反應在 `reactions._usable`。沒有任何地方散落判斷狀態 ID。
- 傷害公式：`raw × 元素修正 × 天氣 × 格擋 × 狀態倍率` 一次乘完最後無條件捨去一次；`status_ppm`（虛弱 × 易傷，百萬分比）記在 `DamageDealt`，預覽的期望值表重用它。虛弱只作用於 `cause: attack`；易傷作用於所有 `mode: roll` 的傷害（含持續傷害、爆炸、導電、表面），不含 `percent_max_hp`（墜落、致命地形）與 `lethal`。
- 暈眩：`turns.skip_turn_if_stunned` 在 `advance_turn` 迴圈裡於 `start_turn`（冷卻 −1、持續傷害、表面）之後呼叫；AP 與移動點數歸零、發出 `TurnSkipped`、照常 `end_turn`（狀態倒數）後繼續找下一位。回合開始時被持續傷害打倒的單位不會走到這裡。暈眩（任何 `skip_turn` 狀態）期間 `reactions._usable` 一律不可用。
- `engine/control.py`：`plan_status`（純函式）算出 Boss 轉換、`save_attr`、遞減後的守方屬性值（`value × 1500 // 1000`，至少 1）；`status_effect` 擲骰並發出 `StatusConverted`、`StatusSaveRolled`（含攻守雙方屬性值、遞減與否、完整修正，測試直接驗證）與 `StatusResisted`；`status_save_chance` 以窮舉 d20 計算施加率，`preview` 重用。**遞減記錄在 `handlers.apply_status`**（所有來源一致）：只要成功施加帶 `control_group` 的狀態就寫 `unit.control_dr[group] = 目前輪數 + control_dr_rounds`。
- 預覽：抵抗判定視為分歧點（`min` ＝ 被抵抗、`max` ＝ 施加成功），所以 `min_state` 沒有狀態、`max_state` 有；`TargetPreview.status_chances` 只列需要抵抗判定的狀態（已含 Boss 轉換後的實際狀態與遞減）。
- AI：`ai_profiles.yaml` 新增表格層級的 `status_values`（單位是「等值的傷害點數」，初值：暈眩 12、定身 6、緩速 4、虛弱 5、易傷 6、流血 6、中毒 6），載入時填入每個行為模式（`AiProfile.status_values`，行為模式可自行覆寫）。`utility._status_gains`：不需抵抗判定的狀態（`min` 事件裡的 `StatusApplied`）收益 ＝ 命中率 × 價值；需要抵抗判定的狀態收益 ＝ 該目標的命中率 × 施加率 × 價值，目標已帶有該狀態時為 0；價值 ＝ 行為模式的 `damage` 權重 × 等值點數，沒列出的狀態（燃燒、倒地……）維持原本的 `status` 權重。`skill_estimate` 不需要改（範圍內有敵人就是候選）。
- CLI：新事件的中文紀錄（`render._describe_control`）、傷害顯示「（狀態 ×0.9375）」、治療顯示「（治療 ×0.5）」。

**重要取捨**

- 定身連倒地站起也不行（站起算主動移動，`available_move_budget` 回傳 `None`）。
- 友方與自己被施加狀態不擲抵抗，但仍會做 Boss 轉換與記錄遞減（看 `ApplyStatusEffect` 的目標，不看來源）。
- 技能之外的來源（表面、地圖事件、環境）呼叫 `apply_status` 效果時不擲抵抗、**也不做 Boss 轉換**（目前沒有這種來源；見待 PM 決定 #1）。
- 暈眩在自己的回合內才被施加（例如被反應打到）時，要到下一個自己的回合才會跳過；而持續 1 回合會在這個回合結束時倒數掉，所以等於沒效果。目前沒有這種來源，沒有特別處理。
- 新技能數值（預算之後由 2B-2 驗證）：寒鎖 法術單體 5 格、1d6 冰霜 ＋ 定身 1 回合、法力 5、冷卻 2；放血斬 武器單體 ×0.8 ＋ 流血、法力 4、冷卻 2；盾擊 武器近戰單體 ×0.5 ＋ 暈眩 1 回合、法力 4、冷卻 4（盾衛法力 8，只能用兩次）；毒霧 法術 `square3`（射程 5）、毒＋易傷、2 AP、法力 10、冷卻 3，不裝備。
- 技能欄位沒有超過上限：法師與戰士各 5 個主動技能（上限 6），沒有換下任何技能。

## 5. 數據表

### 效能（`scripts/bench_battle.py`，每個動作含 AI 的中位數）

「2A-2」為本階段開工前（commit `c007c9a`）在同一台機器上的重跑結果，不是報告上的舊數字。

| 情境 | 2A-2 | 2B-1 |
|---|---|---|
| test_heights_8x8 | 2766 µs | 1916 µs |
| bridge_chasm | 3437 µs | 3830 µs |
| oil_depot | 3801 µs | 3609 µs |
| swamp | 4115 µs | 3856 µs |
| ruined_fort | 5221 µs | 4657 µs |

全部 ≤ 8 ms，且沒有明顯退化（差異在量測雜訊內；英雄與盾衛多了技能，但敵方戰鬥也因結局不同而變短）。

### 勝率（`scripts/sim_demo_maps.py`，種子 0–19，只列出、不調整）

| 地圖 | 我方勝 | 敵方勝 | 我方勝率 | 平均輪數 | 輪數範圍 | 2A-2 勝率／平均輪數 |
|---|---|---|---|---|---|---|
| bridge_chasm | 17 | 3 | 85% | 4.25 | 3–6 | 90%／4.40 |
| oil_depot | 10 | 10 | 50% | 4.75 | 3–7 | 50%／5.00 |
| swamp | 12 | 8 | 60% | 4.40 | 3–6 | 60%／4.80 |
| ruined_fort | 20 | 0 | 100% | 4.00 | 2–7 | 85%／3.95 |

### 技能使用（全部地圖、全部種子）

| 技能 | 陣營 | 次數 | 命中率 | 平均傷害／次 |
|---|---|---|---|---|
| 火焰箭 | 我方 | 194 | 63% | 11.2 |
| **放血斬** | 我方 | 102 | 57% | 2.1 |
| 碎骨重擊 | 我方 | 79 | 56% | 6.0 |
| 橫掃劈砍 | 敵方 | 58 | 60% | 5.0 |
| 旋風斬 | 我方 | 37 | 66% | 5.9 |
| 餘燼爆發 | 我方 | 32 | 50% | 14.9 |
| 灰燼誓約 | 我方 | 31 | 52% | 13.3 |
| 連鎖閃電 | 我方 | 31 | 58% | 21.9 |
| 處決 | 我方 | 27 | 78% | 10.4 |
| **寒鎖** | 我方 | 19 | 68% | 8.1 |
| 高處狙擊 | 我方 | 18 | 61% | 6.7 |
| 聖域 | 我方 | 13 | — | — |
| 穿透射擊 | 我方 | 10 | 60% | 9.3 |
| 鉤索箭 | 我方 | 8 | 12% | 1.4 |
| 火焰箭矢 | 敵方 | 6 | 60% | 2.5 |
| **盾擊** | 敵方 | 5 | 20% | 0.4 |
| 颶風踢 | 敵方 | 2 | 50% | 2.0 |
| 煙幕箭 | 我方 | 2 | — | — |
| 閃現 | 我方 | 1 | — | — |

觀察（不調整）：放血斬被用得很頻繁（102 次，我方戰士幾乎每回合都用，流血的價值 ＝ 6 點等值傷害 ×「戰士 `damage` 權重 10」大於它的法力與冷卻成本）；盾衛的盾擊只用 5 次（法力只有 8、冷卻 4）；毒霧沒有人裝備。`ruined_fort` 我方勝率由 85% 升到 100%，是英雄多了控制與持續傷害的結果，2C 統一處理。

## 6. 待 PM 決定

1. **非技能來源的 Boss 轉換與抵抗**：表面、地圖事件、環境若將來也能施加 `stun`，現在不會轉換（也不擲抵抗，符合 3.2「表面、環境維持現有規則」）。要不要把 Boss 轉換搬進 `handlers.apply_status`，讓所有來源都轉換？目前沒有這類來源，我維持只在技能路徑轉換。
2. **AI 狀態價值的尺度**：我用「等值傷害點數 × 行為模式的 `damage` 權重」，所以重傷害的行為模式（莽夫 10）比重位置的（守衛 3）更看重狀態。初值未經模擬，2C 要一起調；放血斬使用過頻（見第 5 節）是第一個可看的現象。
3. **定身是否連站起也不行**：我讓倒地＋定身的單位完全不能行動（站起算主動移動）。若希望站起仍可，需要改 `available_move_budget`。
4. **虛弱與易傷的適用範圍**：虛弱只作用於 `cause: attack`（含藉機攻擊、反應攻擊與技能）；易傷作用於所有骰值傷害（含爆炸、導電、持續傷害、表面），只排除百分比傷害與致命地形。雷電導電的基準值 `base_amount` 含虛弱（攻擊者側）、不含易傷（受害者側，由各單位自己套用）。
5. **轉換後的持續時間**：Boss 的暈眩轉成緩速時，持續時間沿用暈眩的 1 回合（不是緩速預設的 2 回合）。若要用緩速的預設，改 `control.status_effect` 一行。
6. **遞減的記錄範圍**：任何成功施加帶 `control_group` 的狀態都記錄（含友方、自己、表面來源、Boss 轉換後的狀態）；被抵抗不記錄；重複成功會把期限刷新為 R＋2。
7. **同一技能內兩個同類別控制**：解譯器逐個原語結算，第二個原語的抵抗判定會看到第一個造成的遞減，但 `preview` 的施加率用施放前的遞減狀態計算（不一致只出現在這種技能；示範技能沒有）。
8. **暈眩在自己的回合內被施加**：到下個自己的回合才跳過，持續 1 回合在這個回合結束就倒數掉，等於沒效果。目前沒有這種來源，未處理；若將來有（反應技能、陷阱），要決定是否改成「下一個完整回合」。
9. **示範技能的數值**：寒鎖冰霜傷害 1d6、盾衛法力 8、毒霧沒有傷害等都是估計值，2B-2 的預算驗證可能要求調整；毒霧是沒有傷害原語的技能，AI 與預覽的「命中」仍照常運作（以法術命中判定）。
10. **勝率變化**：新技能讓 `ruined_fort` 變成 20–0；`bridge_chasm` 85%。照 2B 計畫決定 #1 只列出，2C 處理。

## 7. 給下一階段的備註

- 2B-2 的預算：`statuses.yaml` 還沒有 `budget_points`；新狀態的 `control_group`、`save_attr` 已存在，可直接推導「控制」標籤（4.2 的機制標籤）。`skill_frost_shackle`、`skill_rending_strike` 的 `skeleton` 我分別標為 `control`、`strike`；`skill_shield_bash` 標為 `control`（2B-2 規定暈眩技能形狀只能是 `single` 且冷卻 ≥ 4，已符合），`skill_venom_cloud` 為 `control`（`square3` 有冷卻 3，符合互斥規則 1）。
- 新增狀態效果的步驟：`statuses.yaml` 加欄位或一個狀態 → `engine/rules/statuses.py` 加一個查詢函式 → 在唯一的計算點呼叫（`start_turn`／`_damage`／`_heal`／`movement`）。新增控制類別：`StatusDef.control_group` 的 `Literal` 加一個值即可，遞減與預覽自動套用。
- 測試輔助：`tests/engine/test_statuses.py` 的 `_with_status(state, uid, status_id, remaining)`（直接掛狀態，不記錄遞減）與 `_hit`（固定傷害）可重用；要驗證抵抗判定請在建立戰鬥**之後**再 `script_rolls`（先攻也會用到 `Rng.roll`）。
- `trpg battle --allies bandit_shieldbearer,hero_mage,hero_fighter --enemies bandit_boss,bandit,bandit_shieldbearer` 可以看到盾擊與暈眩（見附錄）。
- 日誌格式升為 `trpg-battle-log/5`，舊紀錄無法重播。

## 8. 附錄：代表性的 CLI 輸出節錄

`uv run trpg battle --map test_flat_6x6 --seed 2 --allies bandit_shieldbearer,hero_mage,hero_fighter --enemies bandit_boss,bandit,bandit_shieldbearer`（盾衛盾擊命中戰士、暈眩成功，戰士下個回合被跳過）：

```
  盜賊盾衛2 施放「盾擊」（AP 1，法力 4，冷卻 4 回合）→ 影響 1 格
  盜賊盾衛2 以「盾擊」攻擊 戰士：d20=12 修正 -1 熟練 +2 = 13（目標 11）→ 命中
  ⟳ 戰士 反應：格擋（耐力 −10）
    戰士 受到 1 點物理傷害［骰 3］（元素修正 ×0.9）（格擋 ×0.25），HP 46 → 45
  盜賊盾衛2 對 戰士 施加「暈眩」（力量 13 vs 體質 14）：d20=20 修正 +0 熟練 +2 = 22（目標 11）→ 施加成功
  戰士 獲得狀態「暈眩」（1 回合）
  ...
— 戰士 的回合（AP 3，移動 5，法力 2/20）
  戰士 受到「暈眩」影響，跳過這個回合
  戰士 的「暈眩」結束了
  戰士 結束回合
```

同一場戰鬥中，另一次盾擊被抵抗：

```
  盜賊盾衛1 對 盜賊 施加「暈眩」（力量 13 vs 體質 12）：d20=6 修正 +0 熟練 +2 = 8（目標 11）→ 被抵抗
  盜賊 抵抗了「暈眩」
```

盾擊打在盜賊頭目身上（Boss 硬控轉換，`test_stun_on_a_boss_becomes_slow` 的情境）：

```
  盜賊盾衛 施放「盾擊」（AP 1，法力 4，冷卻 4 回合）→ 影響 1 格
  盜賊盾衛 以「盾擊」攻擊 盜賊頭目：d20=20 修正 +0 熟練 +2 = 22（目標 11）→ 自然 20，暴擊！
  盜賊頭目 是首領：「暈眩」轉為「緩速」
  盜賊盾衛 對 盜賊頭目 施加「緩速」（力量 13 vs 敏捷 10）：d20=10 修正 +2 熟練 +2 = 14（目標 11）→ 施加成功
  盜賊頭目 獲得狀態「緩速」（1 回合）
```
