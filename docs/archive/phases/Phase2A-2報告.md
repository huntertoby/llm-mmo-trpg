# Phase 2A-2 完成報告：條件與 AI

## 1. 摘要

技能條件（5 種，技能層級決定能否使用、效果層級對每個對象分別判斷）、敵人技能（盜賊頭目、盜賊弓手各自裝備技能，其他敵人維持普攻當對照組）與完整一些的效用 AI（候選篩選、法力與冷卻的機會成本、友軍誤傷、治療只算實際補到的量、場地型技能的位置價值）全部完成。6.0 的 10 項 PM 決定都已處理：武器技使用武器的 `crit_range`、`affects: all` 一律排除施放者、`preview` 顯示擊倒成功率、場地型技能放寬為候選。新增 5 個技能（3 個使用條件的英雄技、2 個敵人技），`scripts/sim_demo_maps.py` 加上技能使用統計。`uv run python scripts/check.py` 五項全過，**702 個測試**（2A-1 結束時 639 個；另有 4 個 slow 平衡測試預設不跑）。效能：四張示範地圖「每個動作含 AI」的中位數都 ≤ 8 ms，但 `ruined_fort` 約 6.9–7.3 ms，餘裕不大（見第 5、6 節）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `ea89459` | 條件：`content/skill_conditions.yaml`（5 種條件，含 `harshness`）、`ConditionDef`／`ConditionTable`／`ConditionSpec` schema 與跨檔案驗證（`Ruleset.conditions`）、`engine/skills/conditions.py`（條件求值）、`checked_area`（`legal_actions`、`resolve`、AI 共用的技能層級條件）、解譯器的效果層級條件；決定 #3（武器技 `crit_range`）、#4（`affects: all` 排除施放者）、#5（`TargetPreview.knock_chance`）；3 個示範條件技能（餘燼爆發、高處狙擊、處決）；`trpg skills list／show` 顯示條件；測試 `test_skill_conditions.py`（17）、`test_skill_decisions.py`（9）與內容測試 |
| `a0e0096` | 敵人技能（`skill_cleave`、`skill_fire_arrow`，盜賊頭目、盜賊弓手裝備）、AI：`skill_candidates`（`ai_profiles.yaml`）、`mana`／`cooldown`／`exposed` 權重、場地型技能候選、友方站上有害新表面的扣分、超額傷害截斷、擊倒對抗成功率的收益、`legal_actions_with_areas`（AI 重用影響範圍）；情境測試 `test_skill_ai_scenarios.py`（21） |
| `065beb4` | `scripts/sim_demo_maps.py` 的技能使用統計與 `tests/test_sim_scripts.py` |
| `1ac9de6` | 效能：單體技能先以射程篩掉不可能合法的目標；場地型技能只在「有敵人打得到自己、自己卻打不到」時才是候選 |
| （本報告的 commit） | `docs/phases/Phase2A-2報告.md` |

## 3. 驗收條件逐條結果

### 6.0 的 PM 決定

| # | 決定 | 結果 | 證據 |
|---|---|---|---|
| 1 | 敵方沒有技能、我方勝率偏高：由 6.2 處理，只列出新勝率 | ✅ | 第 5 節（勝率仍偏高，不調整） |
| 2 | 場地型技能放寬；弓手在敵方弓手射擊範圍內、沒有掩護時，施放煙幕箭或改站到掩護後 | ✅ | `test_archer_in_the_enemys_longer_reach_throws_smoke_at_its_own_position`、`test_vanish_is_also_a_field_skill_that_protects_the_caster`、`test_archer_can_still_walk_behind_cover_instead_of_throwing_smoke`、`test_no_smoke_when_nobody_can_hit_us`、`test_smoke_between_the_enemy_and_us_is_a_candidate` |
| 3 | 武器技使用武器的 `crit_range`；法術技維持自然 20 | ✅ | `test_decisions.py::test_weapon_skill_crits_on_the_weapons_crit_range`（匕首 19 暴擊、單手劍不會）、`test_spell_skill_crits_only_on_a_natural_20`、`test_preview_uses_the_weapon_crit_range_for_weapon_skills`（匕首暴擊率 2/20，單手劍 1/20） |
| 4 | `affects: all` 一律排除施放者 | ✅ | `test_skill_scenarios.py::test_affects_all_never_hits_the_caster_even_when_the_shape_includes_them`（取代 2A-1 的 `..._includes_the_caster_...`） |
| 5 | `preview` 顯示擊倒對抗成功率 | ✅ | `TargetPreview.knock_chance`；`test_preview_reports_the_knock_prone_contest_chance`（與逐一列舉 d20 相同）、`test_the_knock_chance_follows_the_attribute_matchup`、`test_no_knock_chance_without_a_knock_prone_effect` |
| 6 | 冷卻的紀錄 | ✅ 接受，沒有改動 | — |
| 7 | `spawn()` 預設移除技能；AI 情境測試在「有技能」條件下撰寫 | ✅ | 新的 AI 情境全部用 `_scene(...)`（`caster_template` 裝備真正的技能） |
| 8 | 單體技能選友方或物件的條件：接受保守判斷 | ✅ 沒有改動 | — |
| 9 | `apply_status` 預設對敵方 | ✅ 沒有改動 | — |
| 10 | `noqa` 的複雜度例外：新程式不再加 | ✅ | 本階段沒有新增任何 `noqa`（`git diff bf46d5a -- src` 中新增的行沒有 `noqa`；條件求值、`_Cast` 的條件過濾、AI 的 `_field_value`／`_outgunners` 都拆成小函式） |

### 6.4 驗收條件

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `check.py` 五項全過；2A-1 驗收條件仍成立 | ✅ | `uv run python scripts/check.py`：ruff check／ruff format／mypy／lint-imports／pytest 全部通過（702 passed, 4 deselected）。2A-1 的測試全數保留；改動只有：`affects: all` 的測試（決定 #4）、`test_skills_list_is_a_table_of_every_skill` 改為比對實際技能數、`test_demo_maps.py` 吊橋戰改用種子 6（見待 PM 決定 #8） |
| 2 | 每種條件的成立／不成立各一個測試（技能層級與效果層級） | ✅ | 技能層級：`test_skill_condition_target_hp_below`（含 `test_target_hp_below_is_strict_at_the_boundary`）、`..._self_hp_below`、`..._height_advantage`、`..._target_on_surface`、`..._target_has_status`、`test_an_area_skill_condition_needs_one_matching_unit_in_the_area`。效果層級：`test_effect_condition_target_hp_below`、`..._self_hp_below`、`..._height_advantage`、`..._target_on_surface`、`..._target_has_status`；另有逐對象判斷（`test_effect_condition_is_judged_per_target`）、效果順序（`test_effect_condition_sees_the_state_left_by_earlier_effects`）、地形類（`..._filters_tiles`）與傳送（`..._on_teleport_is_judged_on_the_caster`）。載入驗證：`test_condition_problems_are_rejected_at_load`（6 × 2 層級） |
| 3 | AI 情境測試 | ✅ | 見下 |
| 3a | 三個敵人排成一列：弓手選穿透射擊而非普攻 | ✅ | `test_archer_picks_piercing_shot_when_three_enemies_line_up`（方向 east，分數高於所有普攻）；對照 `test_archer_prefers_a_plain_attack_when_only_one_enemy_is_in_line` |
| 3b | 範圍技能會打到友方：換方向或改用其他動作 | ✅ | `test_the_ai_aims_the_cone_where_it_does_not_burn_an_ally`、`test_the_ai_uses_something_else_when_every_direction_would_burn_an_ally`、`test_a_fire_skill_is_fine_when_the_ally_is_outside_the_cone`；`affects: all` 的直接誤傷沿用 `test_skill_ai.py::test_friendly_fire_lowers_the_score_of_an_all_affecting_skill` |
| 3c | 友方受重傷：風暴使使用聖域 | ✅ | `test_stormcaller_casts_sanctuary_when_an_ally_is_badly_hurt`；`test_a_scratch_is_not_worth_a_sanctuary`、`test_sanctuary_counts_only_the_hp_actually_restored`（治療只算實際補到的量） |
| 3d | 法力只夠用一次強技能：沒有目標價值時不浪費 | ✅ | `test_the_ai_saves_its_only_big_spell_when_nothing_is_worth_it`、`test_the_ai_does_not_spend_its_last_mana_on_a_target_a_plain_attack_finishes`、`test_the_ai_does_spend_the_mana_when_the_target_value_is_there`、`test_mana_and_cooldown_weights_lower_a_skills_score` |
| 4 | 效能：四張示範地圖每個動作含 AI 的中位數 ≤ 8 ms，附 1C／2A-1／2A-2 三欄 | ✅（餘裕小） | 第 5 節：2A-2 為 3.1–3.5／4.6–4.9／5.1–5.4／5.4–6.4／6.9–7.3 ms（test_heights／bridge／oil／swamp／ruined_fort，連跑 3 次） |
| 5 | `sim_demo_maps.py` 技能使用統計 | ✅ | 第 5 節：每個技能的使用次數、命中率、平均傷害（另加平均治療）；`tests/test_sim_scripts.py` |
| 6 | 重播與確定性測試仍通過 | ✅ | `test_skill_determinism.py`（7）、`test_determinism.py` 全數通過；敵人帶技能後 hypothesis 屬性測試自動涵蓋條件與敵方技能。`trpg battle --map oil_depot --seed 42 --log-json …` → `replay`：「重播驗證通過：76 個動作、318 個事件，最終狀態一致（oil_depot，種子 42）」 |

另有：`test_enemies_actually_use_their_skills_in_demo_battles`（oil_depot／bridge_chasm 各 4 個種子，敵方確實使用 `skill_cleave`／`skill_gale_kick`／`skill_fire_arrow`）、`test_only_the_boss_and_the_archer_have_skills`、`test_a_fire_arrow_can_target_and_ignite_an_oil_barrel`、`test_legal_actions_with_areas_lists_the_same_actions_and_one_area_per_skill_action`。

## 4. 設計與實作說明

**條件**

- `ConditionSpec`（`type` ＋ `permille`／`surface`／`status`）是 `SkillDef.condition` 與 `EffectSpec.condition` 的型別；條件類型與參數範圍來自 `content/skill_conditions.yaml`（引擎實作的 5 種必須全部定義，同形狀表的做法），載入時檢查類型存在、必要參數齊全、範圍、引用的狀態與表面（中文訊息，指出檔案與欄位）。`harshness`（`common`／`harsh`）只存不用，留給 2B。
- 判斷對象 `Subject(unit, xy)`：單位類條件（`target_hp_below`、`target_has_status`）需要單位；格子類條件（`height_advantage`、`target_on_surface`）看格子；`self_hp_below` 只看施放者。`target_hp_below` 用整數比較 `hp × 1000 < permille × max_hp`（剛好等於不算「低於」）。
- **技能層級**：`checked_area` ＝ `compute_area` ＋ 技能條件，`legal_actions`（經 `selections`）、`resolve` 與 AI 都用它，所以不成立的選取不在 `legal_actions`、直接 `resolve` 拋 `IllegalActionError`（「技能條件不成立：處決 需要「目標血量低於 40%」」）。`self_hp_below` 看施放者；其他條件要求影響範圍內（不含施放者所在格）至少有一個對象成立，單體技能就是被選中的目標。
- **效果層級**：解譯器在展開每個效果時用 `targets(affects, condition)`／`tiles(affects, condition)` 過濾，判斷的是「結算到該效果當下」的狀態（所以同一個技能內，先施加燃燒、再「若目標燃燒中」的效果會成立，順序顛倒則不會）。地形類效果逐格判斷（格子上若有單位，單位類條件也看得到它）；`teleport` 以施放者為對象；帶條件的傷害只對條件成立的格子補元素觸及與物件傷害。
- 預覽：`_damage_expectation` 只計入條件成立的傷害效果，讓期望值仍是精確的；`test_preview_of_a_conditional_damage_skill_matches_the_resolution` 驗證固定骰值時預覽的最小傷害與實際結算相同（燃燒中與否各一）。

**其他決定**

- 決定 #3：`skill_profile` 的武器技 `crit_range` 取武器的；`roll_attack`、預覽的暴擊率與 `_forced_natural` 本來就吃 `AttackProfile.crit_range`，所以預覽一致。
- 決定 #4：`roll_hits` 對 `affects: all` 的友方不含施放者；施放者因此不擲骰、不受傷。
- 決定 #5：`_knock_chance` 比照 `_maneuver_chance`（技能的縮放屬性對相同屬性的比例修正 ＋ 熟練，列舉 d20）；是「命中之後」的對抗成功率。AI 把它換算成收益（`status` 權重 × 命中率 × 成功率，目標已倒地則不算）。

**AI（`engine/ai/utility.py`）**

- 候選篩選 `skill_estimate`（`worth_previewing` 在技能上的對應）：不跑引擎，依影響範圍內的敵人（×3）、受傷友方（有治療時 ×2）、其他友方（−3）、可破壞物件（+1）估分；傳送用虛擬位置價值；**場地型技能**（所有效果只作用在格子或自己身上）在沒有上述對象時，看是否有「打得到我、我卻打不到」的敵人，且影響範圍涵蓋自己或擋在視線上（`_field_value`）。每種技能只保留前 `skill_candidates`（`ai_profiles.yaml`，預設 3）個選取跑完整 `preview`。
- 評分：沿用 `preview` 的收益與位置價值差，新增 ①法力與冷卻的機會成本（`skill_cost`：`mana`×法力 ＋ `cooldown`×冷卻回合 ＋ HP 代價視為對自己的傷害）；②對友方的影響：技能讓友方站上有害的新表面，每名扣 `friendly_fire × 8`（`_SURFACE_HARM`；表面傷害在下個回合才發生，預覽看不到，所以另外計）；③超額傷害截斷：對單一目標的期望傷害不超過其剩餘 HP（擊倒由 `kill` 計分），否則 AI 會把 12 點法力花在 1 HP 的敵人身上；④擊倒對抗成功率；⑤治療仍用 `preview.healed`（`Healed` 事件的實際補到量，已被最大 HP 截斷）。
- 位置價值新增 `exposed`（弓手 20）：能打到自己、自己卻打不到的敵人數（對方射程更長，或自己被煙幕／隱蔽遮住）。**只算不對稱的情況**：互相打得到的對射不扣分，否則弓手會因為 `threat` 與 `exposed` 抵銷而不敢進入射擊位置（第一次嘗試時 `test_archer_prefers_covered_firing_position` 就是因此失敗）。煙幕、隱匿、掩護因而在「被壓制」時有明確的正收益。
- `legal_actions_with_areas`（`engine/battle.py`）：`legal_actions` 的同一份結果，另回傳每個技能動作的影響範圍（以 `id(action)` 為鍵），AI 評估時不必重算 `compute_area`。`legal_actions` 的行為與順序不變。
- 權重（`ai_profiles.yaml`）：`mana`（四種模式皆 1）、`cooldown`（弓手 2、其餘 1）、`exposed`（弓手 20）；為了讓聖域在付出機會成本後仍值得，`heal` 權重由 4 調為 莽夫 8、弓手 6、狡猾 6、守衛 10（未經模擬調整）。

**敵人技能**：盜賊頭目 `[橫掃劈砍（cone 2，×1.0，AP 2，法力 4，冷卻 2）, 颶風踢（既有，推 2）]`、法力 14；盜賊弓手 `[火焰箭矢（single 武器射程，×0.8 火焰，AP 1，法力 3）]`、法力 9（對油桶使用會引爆）。盜賊與盜賊盾衛維持只有普攻。

## 5. 數據表

**新增的示範技能（`uv run trpg skills list` 為權威；2A-1 的 14 個見 2A-1 報告）**

| 持有者（法力） | 技能 | 骨架 | 形狀 | 效果 | AP | 法力／冷卻 | 條件 |
|---|---|---|---|---|---|---|---|
| 法師（40） | 餘燼爆發 `skill_cinder_burst` | strike | single 5 | 1d6 火焰；**若目標帶有「燃燒」**再 3d6 火焰 | 2 | 8／2 | 效果層級 `target_has_status` |
| 弓手（24） | 高處狙擊 `skill_high_ground_shot` | strike | single（武器射程） | 武器傷害 ×1.0；**若居高臨下**再 ×0.8 | 2 | 5／2 | 效果層級 `height_advantage` |
| 戰士（20） | 處決 `skill_execute` | strike | single（武器射程） | 武器傷害 ×2.0 | 1 | 5／2 | 技能層級 `target_hp_below 400‰` |
| 盜賊頭目（14） | 橫掃劈砍 `skill_cleave` | area | cone 2 | 武器傷害 ×1.0 | 2 | 4／2 | — |
| 盜賊弓手（9） | 火焰箭矢 `skill_fire_arrow` | strike | single（武器射程） | 武器傷害 ×0.8（火焰） | 1 | 3／— | — |

「站在高處時射程提升」沒有做（條件只決定能否使用或效果是否生效，不改變形狀參數）；`target_on_surface`、`self_hp_below` 的示範由測試專用技能覆蓋。

**示範地圖勝率與輪數**（`uv run python scripts/sim_demo_maps.py --seeds 20`；效用 AI，種子 0–19，`max_rounds=30`；只列出不調整）

| 地圖 | 我方勝 | 敵方勝 | 平手 | 我方勝率 | 平均輪數 | 輪數範圍 | 每場時間 | 2A-1 勝率／平均輪數 |
|---|---|---|---|---|---|---|---|---|
| `bridge_chasm` | 18 | 2 | 0 | 90% | 4.40 | 3–6 | 555 ms | 80%／4.75 |
| `oil_depot` | 10 | 10 | 0 | 50% | 5.00 | 3–7 | 829 ms | 40%／5.00 |
| `swamp` | 12 | 8 | 0 | 60% | 4.80 | 3–7 | 630 ms | 55%／4.95 |
| `ruined_fort` | 17 | 3 | 0 | 85% | 3.95 | 2–8 | 551 ms | 70%／4.95 |

**效能：每個動作（含 AI）的中位數**（`scripts/bench_battle.py --repeat 10 --utility-repeat 5`，種子 42，預設陣容，連跑 3 次的範圍；本工作區波動約 ±15%）

| 地圖 | 1C | 2A-1（範圍） | 2A-2（範圍） | 2A-2 平均（範圍） |
|---|---|---|---|---|
| `test_heights_8x8` | 2.48 ms | 2.99–3.26 ms | 3.14–3.54 ms | 4.3–4.6 ms |
| `bridge_chasm` | 2.27 ms | 2.31–2.68 ms | 4.58–4.94 ms | 6.4–7.3 ms |
| `oil_depot` | 3.44 ms | 2.70–2.98 ms | 5.09–5.38 ms | 7.4–8.2 ms |
| `swamp` | 3.65 ms | 2.53–3.97 ms | 5.39–6.36 ms | 6.1–6.7 ms |
| `ruined_fort` | 2.47 ms | 2.34–2.59 ms | 6.90–7.28 ms | 8.2–8.5 ms |

中位數都 ≤ 8 ms，但比 2A-1 高出約一倍；`ruined_fort` 餘裕只有約 10%。成本主要是技能的完整 `preview`：弓手有 5 個技能，每回合最多 9 個技能預覽（每個約 0.6 ms）；拿掉所有單位的技能時 `ruined_fort` 的中位數是 2.8 ms。已做的最佳化：影響範圍重用（`legal_actions_with_areas`）、射程外目標先篩掉、場地型技能只在被壓制時是候選、`_outgunned_by` 先比距離。`skill_candidates` 由 3 降到 2 的影響不明顯（單體技能的候選數本來就受敵人數限制）。

**技能使用統計**（同一批 80 場；命中率＝命中次數／擲骰次數，範圍技能對每個目標各擲一次；平均傷害＝該技能直接造成的傷害 ÷ 使用次數，不含爆炸、表面、狀態的間接傷害；只列出，不調整）

| 技能 | 陣營 | 使用次數 | 命中率 | 平均傷害／次 | 平均治療／次 |
|---|---|---|---|---|---|
| 火焰箭 `skill_fire_bolt` | 我方 196 | 196 | 121/191（63%） | 11.4 | — |
| 碎骨重擊 `skill_bone_crusher` | 我方 90 | 90 | 48/90（53%） | 4.0 | — |
| 橫掃劈砍 `skill_cleave` | 敵方 49 | 49 | 36/69（52%） | 4.3 | — |
| 處決 `skill_execute` | 我方 44 | 44 | 30/44（68%） | 8.2 | — |
| 旋風斬 `skill_whirlwind` | 我方 40 | 40 | 53/75（71%） | 5.6 | — |
| 灰燼誓約 `skill_ashen_oath` | 我方 35 | 35 | 32/55（58%） | 15.3 | — |
| 連鎖閃電 `skill_chain_lightning` | 我方 34 | 34 | 53/89（60%） | 22.1 | — |
| 餘燼爆發 `skill_cinder_burst` | 我方 34 | 34 | 17/34（50%） | 15.5 | — |
| 高處狙擊 `skill_high_ground_shot` | 我方 17 | 17 | 12/17（71%） | 7.2 | — |
| 鉤索箭 `skill_grapple_arrow` | 我方 13 | 13 | 7/13（54%） | 3.0 | — |
| 聖域 `skill_sanctuary` | 我方 13 | 13 | — | 0.0 | 14.0 |
| 火焰箭矢 `skill_fire_arrow` | 敵方 11 | 11 | 6/10（60%） | 2.9 | — |
| 穿透射擊 `skill_piercing_shot` | 我方 9 | 9 | 11/19（58%） | 9.3 | — |
| 颶風踢 `skill_gale_kick` | 我方 1、敵方 2 | 3 | 2/2（100%） | 2.7 | — |
| 閃現 `skill_blink` | 我方 2 | 2 | — | 0.0 | — |
| 煙幕箭 `skill_smoke_arrow` | 我方 2 | 2 | — | 0.0 | — |

隱匿、喚潮、石牆術在 80 場中一次都沒被使用，煙幕箭與閃現各 2 次（見待 PM 決定 #3）。

## 6. 待 PM 決定

1. **勝率沒有因為敵人技能而下降**：`bridge_chasm` 90%、`ruined_fort` 85%（2A-1 為 80%／70%）。敵人技能在 80 場中只被用了 62 次（橫掃劈砍 49、火焰箭矢 11、颶風踢 2），一場平均不到 1 次；盜賊頭目常在使用前就倒下。依 6.0 #1 不調整；2C 是否要調整敵方陣容、技能或英雄法力？
2. **效能餘裕小**：`ruined_fort` 的中位數 6.9–7.3 ms（目標 ≤ 8 ms），主因是弓手的 5 個技能每回合約 9 次預覽。是否接受？若要更多餘裕，2C 可考慮：①LOS 快取（`has_line_of_sight` 佔約 14%）、②單體技能對同一目標的重複預覽合併、③`skill_candidates` 依技能種類設定，或④對「分數上限一定不如普攻」的技能跳過預覽。
3. **場地型技能很少被用**：煙幕箭 2 次、閃現 2 次、隱匿／喚潮／石牆術 0 次。我的實作只在「被壓制」（打得到我、我打不到）時才給煙幕與隱蔽價值（`exposed`），而且喚潮、石牆術沒有對應的位置價值。是否要在 2C 幫它們加價值（例如喚潮配合雷電、石牆術製造掩護）？
4. **條件的細節請確認**：①技能層級的目標類條件在範圍技能上是「範圍內至少有一個（非施放者）對象成立」；②效果層級判斷的是結算到該效果當下的狀態（同一技能內效果的先後會影響條件）；③`teleport` 的效果條件以施放者為對象；④條件傷害對可破壞物件以「格子」判斷（沒有單位，所以單位類條件不成立）；⑤目前只支援單一條件（沒有且／或組合）。
5. **AI 權重的調整沒有經過模擬**：`mana`（1）、`cooldown`（1／弓手 2）、`exposed`（弓手 20）、`_SURFACE_HARM`（8）、`heal`（8／6／6／10）都是我為了讓情境測試成立、並不影響 Phase 1 測試而定的初值；2C 應統一用模擬調整。另外超額傷害截斷（期望傷害不超過目標剩餘 HP）也影響了普攻的評分（Phase 1 的 AI 測試仍全數通過）。
6. **`exposed` 只算不對稱的壓制**：對射時不會使用煙幕或隱匿（實際上對射時用煙幕往往是好主意）。這是為了不讓弓手不敢進入射擊位置；若希望更積極，需要另一個「換位置前先處理對方優勢」的機制。
7. **友方站上有害新表面的懲罰**只在 `UseSkill` 計算（表面傷害發生在下個回合，預覽看不到），且只看「有害表面」（有傷害或狀態），不估計持續時間與實際傷害。
8. **`test_demo_maps.py` 的吊橋戰從種子 42 改為種子 6**：敵方有技能且 AI 改變後，種子 42 的吊橋戰沒有出現「矮牆掩護」的畫面（敵方獲勝）；種子 6 同時出現木橋、墜落、半掩護與環境預告。其他三張圖仍用 42。
9. **新增 API `legal_actions_with_areas`**（`engine/battle.py`，`legal_actions` 是它的第一個回傳值）：為了讓 AI 重用影響範圍。若 PM 希望引擎對外 API 保持精簡，可以改成內部函式（AI 目前從 `trpg.engine.battle` 匯入）。
10. **內容細節**：①示範條件技能的數值（餘燼爆發額外 3d6、高處狙擊額外 ×0.8、處決 ×2.0 且限血量低於 40%）和敵人技能都是估計值；②`condition_text` 放在 `trpg.content.skills`（CLI 與引擎錯誤訊息共用）；③「站在高處時射程與傷害提升」只做了傷害提升。

## 7. 給下一階段的備註

- 2B 的預算：`ConditionDef.harshness` 已存在；`EffectSpec.condition`／`SkillDef.condition` 都是 `ConditionSpec`，可直接依 `type` 查表給倍率。條件類型清單的單一來源是 `content/skill_conditions.yaml`（`REQUIRED_CONDITIONS` 與引擎實作同步，新增條件要同時改兩處）。
- 新增條件類型的步驟：`skill_conditions.yaml` 加一筆 → `REQUIRED_CONDITIONS` 加 ID → `engine/skills/conditions.py::condition_met` 加分支 → `condition_text` 加文字。
- AI：`skill_estimate` 的估計與 `_field_value` 是「誰值得預覽」的唯一入口；要加新的技能價值（例如喚潮配雷電）優先在 `_gains`／位置價值加，而不是在估計裡硬寫。`UtilityAI.skill_candidates` 可在建構時覆寫（測試用）。
- 測試輔助：`tests/engine/skill_helpers.py` 的 `battle`／`cast`／`hit_with`／`script_rolls` 不能用真正的技能 ID（`make_state(skills=[...])` 會與 `content/` 重複）；要測真正的技能請用 `test_skill_decisions.py::_real_battle` 或 `test_skill_ai_scenarios.py::_scene` 的做法（`caster_template(["skill_xxx"])` 直接裝備）。
- 效能：見待 PM 決定 #2。要分析成本分佈，可在 `trpg.engine.ai.utility.preview` 上包一層計數與計時（我用過的臨時腳本沒有放進 repo）。

## 8. 附錄：代表性的 CLI 輸出節錄

`uv run trpg battle --map oil_depot --seed 42`（敵方頭目使用橫掃劈砍，打爆了油桶）：

```
— 盜賊頭目 的回合（AP 3，移動 5，法力 14/14）
  盜賊頭目 施放「橫掃劈砍」（AP 2，法力 4，冷卻 2 回合）→ 影響 4 格
  盜賊頭目 以「橫掃劈砍」攻擊 戰士：d20=9 修正 +0 熟練 +2 = 11（目標 11）→ 命中
  ⟳ 戰士 反應：格擋（耐力 −10）
    油桶 受到 10 點物理傷害［骰 2+4］，HP 8 → 0
    戰士 受到 6 點物理傷害［骰 6+3］（元素修正 ×0.9）（格擋 ×0.5），HP 60 → 54
  ＊ 油桶 (5, 6) 被摧毀！
  (4, 6) 出現了油
  (5, 6) 出現了油
  (5, 7) 出現了油
```

`uv run trpg battle --map oil_depot --seed 3`（敵方弓手的火焰箭矢點燃油桶，爆炸波及我方弓手）：

```
— 盜賊弓手 的回合（AP 3，移動 5，法力 9/9）
  盜賊弓手 施放「火焰箭矢」（AP 1，法力 3）→ 影響 1 格
    油桶 受到 6 點火焰傷害［骰 4］，HP 8 → 2
  ＊ 油桶 (5, 6) 爆炸了！
  ＊ 油桶 (5, 6) 炸毀！
  (6, 6) 的油變成了火焰
    弓手 受到 8 點爆炸火焰傷害［骰 4+4］，HP 42 → 34
  盜賊弓手 攻擊 弓手：d20=20 修正 -1 熟練 +2 = 21（目標 11）→ 自然 20，暴擊！
```

`uv run trpg battle --map oil_depot --seed 42`（我方法師使用條件技能「餘燼爆發」）與 `trpg skills show`：

```
法師 施放「餘燼爆發」（AP 2，法力 8，冷卻 2 回合）→ 影響 1 格
法師 以「餘燼爆發」攻擊 盜賊2：d20=2 修正 +0 熟練 +2 = 4（目標 11）→ 失手
```

```
餘燼爆發（skill_cinder_burst）
  代價 AP 2，法力 8，冷卻 2 回合
  形狀 單體（射程 5）
  效果：
    1. 1d6＋智力加成的火焰傷害（敵方）
    2. 3d6＋智力加成的火焰傷害（敵方），若目標帶有狀態「燃燒」

處決（skill_execute）
  代價 AP 1，法力 5，冷卻 2 回合
  形狀 單體（射程 武器射程）
  使用條件 目標血量低於 40%
```

`uv run trpg battle replay <log>` → `重播驗證通過：76 個動作、318 個事件，最終狀態一致（oil_depot，種子 42）。`
