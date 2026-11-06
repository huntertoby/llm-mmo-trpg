# Phase 2A-1 完成報告：技能資料與解譯器

## 1. 摘要

技能系統的資料層與引擎層全部完成：`content/` 新增形狀表、原語表與 14 個示範技能（覆蓋 10 種形狀（全部由示範技能）、11 種原語（9 種由示範技能、`destroy_object` 與 `raise_terrain`／`lower_terrain` 由測試專用技能）、兩種 `category`、四種 `weapon_req`），四位英雄裝備技能與法力。引擎新增 `UseSkill` 動作、形狀模組、技能解譯器（全部經過效果佇列）、法力／冷卻／每場次數／HP 代價、表面擁有者；`preview` 與效用 AI 支援技能；CLI 顯示技能紀錄與法力，並新增 `trpg skills list／show`。PM 決定 #1（半掩護看高度）、#2（平衡測試改 slow）、#8（技能推擊被擋只是停下）都已實作並有測試。`uv run python scripts/check.py` 五項全過，共 **639 個測試**（1C 結束時 529 個；另有 4 個 slow 平衡測試預設不跑）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `800e4fe` | 決定 #1：`cover_object_between` 加入第 5 條（掩護物高度 ＋ 1 ≥ 目標高度）與 2 個測試；決定 #2：`test_demo_balance.py` 標為 `slow`、`pyproject.toml` 註冊 marker 並預設 `-m "not slow"` |
| `cfc9803` | 技能資料層：`content/skills.py`（`SkillDef`、`ShapeDef`、`PrimitiveDef`、跨檔驗證與中文錯誤訊息）、`skill_shapes.yaml`、`skill_primitives.yaml`、14 個 `content/skills/skill_*.yaml`、`weapon_class`、單位 `skills`／`max_mana`、`core.yaml` 的 `spell_attr_multiplier_permille` 與 `skill_slots`、`trpg content check` 納入、31 個內容測試 |
| `e8f126d` | 引擎：`UseSkill` 動作、`engine/skills/{shapes,targeting,interpreter}.py`、`AttackProfile`（命中參數抽象）、`maneuvers.contest`（擊倒共用對抗）、法力／冷卻／次數／HP 代價、表面擁有者（`surface_team`）、`legal_actions`、`SkillUsed`／`SkillCooldownChanged` 事件、`LOG_FORMAT` → `/4`、`preview` 的 `targets`／`healed`、效用 AI 技能評分（`AiWeights.heal`）、CLI（紀錄、回合標頭、`trpg skills list／show`） |
| `e98ce8c` | 測試：形狀、原語、情境、預覽、確定性、AI、CLI（共 +110 個）；AI 候選篩選；施放行格式 `施放「X」（…）→ 影響 N 格`；`skills list` 表格 |
| （本報告的 commit） | `docs/phases/Phase2A-1報告.md` |

## 3. 驗收條件逐條結果

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `scripts/check.py` 五項全過；Phase 1 情境測試仍成立 | ✅ | 最後一次 `uv run python scripts/check.py`：ruff check／ruff format／mypy／lint-imports／pytest 全部通過（639 passed, 4 deselected）。Phase 1 的 529 個測試全數保留；唯一的改動是測試輔助函式 `spawn()` 預設不帶技能（見第 4 節）與兩處字串（`trpg-battle-log/4`、單位表多了「法力」） |
| 2 | 決定 #1：高 2 台上的目標，旁邊地面木箱不提供半掩護；地面目標旁的木箱仍提供 | ✅ | `tests/engine/test_cover.py` 的 2 個新測試（commit `800e4fe`） |
| 3 | 每種形狀至少一個測試（邊界、牆壁、視線、`line` 被物件截斷、`chain` 跳躍與同距離排序） | ✅ | `tests/engine/test_skill_shapes.py` 22 個：`test_self_shape_is_caster_tile`、`test_single_*`（單位／物件／射程／視線／武器射程）、`test_line_in_each_direction_is_cut_by_the_map_edge`、`test_line_stops_before_a_wall_and_empty_line_is_illegal`、`test_line_includes_a_sight_blocking_object_then_stops`、`test_cone_*`、`test_cross_*`、`test_center_shape_needs_sight_only_to_the_center`、`test_square3_*`、`test_ground_tile_*`、`test_ring_*`、`test_allies_in_radius_*`、`test_chain_jumps_to_the_nearest_unhit_enemy`、`test_chain_ties_on_distance_break_by_unit_id`、`test_chain_stops_when_nothing_is_in_reach_or_sight`、`test_direction_shapes_list_only_non_empty_directions`、`test_center_shapes_list_every_legal_center_in_row_major_order` |
| 4 | 每種原語至少一個測試；`push` 被擋住停在前一格；steadfast 減半為 0 時不移動且動作合法 | ✅ | `tests/engine/test_skill_primitives.py` 18 個：damage（法術、失手、暴擊、武器技）、heal、push（含 `test_push_blocked_by_an_obstacle_stops_on_the_previous_tile`、`test_steadfast_halves_push_and_zero_distance_is_still_legal`、`test_push_from_a_center_shape_pushes_away_from_the_center`）、pull、knock_prone、teleport（不觸發藉機攻擊、觸發表面）、apply_status、create_surface、destroy_object、create_obstacle、raise／lower_terrain |
| 5 | 情境測試（八項） | ✅ | `tests/engine/test_skill_scenarios.py` 18 個。灰燼誓約 × 油桶：`test_ashen_oath_cone_detonates_an_oil_barrel_and_the_blast_resolves_normally`；喚潮 × 連鎖閃電：`test_summon_tide_then_chain_lightning_conducts_through_the_water`；旋風斬 × 火焰武器：`test_weapon_skill_with_a_fire_weapon_deals_fire_damage`；三個敵人各擲一次、失手仍產生表面：`test_area_skill_rolls_per_enemy_and_misses_still_create_the_surface`、`test_surface_is_created_even_when_every_enemy_misses`；holy 只治療己方、fire 燒到己方：`test_a_holy_surface_made_by_a_skill_only_heals_the_casters_team`、`test_a_fire_surface_created_by_a_skill_burns_the_casters_allies`（另有地圖預置表面保持中立 `test_a_map_placed_holy_surface_is_neutral_and_heals_both_teams`）；預設不傷友方／`affects: all` 會：`test_default_area_damage_never_rolls_against_or_hurts_allies`、`test_affects_all_rolls_against_and_damages_allies_in_the_area`、`test_affects_all_includes_the_caster_when_the_shape_includes_them`；法力／AP／次數／HP 不足（不在 `legal_actions`、`resolve` 拋 `IllegalActionError`）：`test_not_enough_mana_makes_the_skill_illegal`、`test_not_enough_ap_makes_the_skill_illegal`、`test_uses_per_battle_runs_out`、`test_hp_cost_must_leave_the_caster_standing`；冷卻 2（第 1 輪用、第 2 輪不可用、第 3 輪可用，法力不回復）：`test_cooldown_two_skips_exactly_one_own_turn` |
| 6 | 載入時拒絕：`weapon_req` 不相容、超過欄位上限、效果 > 4、推擊 3 格、不存在的原語，且有中文訊息 | ✅ | `tests/content/test_skills_content.py`：`test_unit_weapon_incompatible_with_skill_rejected_at_load`（「需要遠程武器，但單位的武器是法器」）、`test_unit_skill_slots_exceeded_rejected_at_load`（「主動技能超過欄位上限：7 個（上限 6）」）、`test_more_than_four_effects_rejected`、`test_push_and_pull_distance_limited_to_two`、`test_unknown_primitive_rejected_at_load`（「未知的效果原語 'meteor'」），以及形狀／原語參數、teleport 限制、檔名等共 31 個。開戰時另檢查裝備：`test_loadout_incompatible_with_the_weapon_is_rejected_at_battle_start` |
| 7 | 固定骰值時，`preview` 與實際結算一致（單體、範圍、連鎖、會引爆物件） | ✅ | `tests/engine/test_skill_preview.py` 6 個：`test_preview_of_a_single_target_skill_brackets_the_actual_damage`（最小骰命中＝預覽最小、暴擊最大骰＝預覽最大，命中率對照逐一列舉 d20）、`test_preview_expected_damage_matches_exhaustive_enumeration`、`test_preview_of_an_area_skill_lists_every_target_tile_and_the_explosion`（含油桶爆炸：確定的連鎖 ⊆ 實際、實際 ⊆ 確定＋可能）、`test_preview_of_a_chain_skill_covers_the_whole_chain`、`test_preview_of_a_heal_reports_the_range_per_ally`、`test_preview_rejects_illegal_skill_actions`。固定骰值用 `skill_helpers.script_rolls`（猴子補丁 `Rng.roll`） |
| 8 | 確定性：同種子與動作列表重播一致（含技能）；hypothesis 隨機選 `legal_actions` 不拋例外 | ✅ | `tests/engine/test_skill_determinism.py` 7 個：`test_same_seed_same_battle_with_skills[3 張地圖]`、`test_use_skill_actions_round_trip_and_replay_reproduces_the_battle`、`test_property_random_legal_actions_with_skills_never_raise`（偏向技能；檢查 `resolve` 不修改輸入、法力／HP／冷卻不變式、`has_only_end_turn` 一致）、`test_property_every_listed_skill_action_resolves_and_replays`、`test_illegal_use_skill_leaves_the_state_untouched`。既有的 `test_determinism.py` 屬性測試因英雄現在帶技能，也自動涵蓋技能 |
| 9 | `trpg battle --map oil_depot --seed 42` 紀錄中至少 3 種技能；`--log-json` 後 `replay` 一致 | ✅ | `tests/cli/test_skills_cli.py::test_oil_depot_battle_uses_at_least_three_different_skills_and_replays`。實際輸出用了 6 種：閃現、旋風斬、灰燼誓約、火焰箭、碎骨重擊、穿透射擊；`uv run trpg battle replay …` → `重播驗證通過：90 個動作、384 個事件，最終狀態一致（oil_depot，種子 42）。` |
| 10 | 四張示範地圖各 20 種子的勝率與平均輪數（只列出） | ✅ | 見第 5 節 |

其他交付項目：`trpg content check` 納入技能檔（`test_content_check_includes_skill_files`）；`trpg skills list／show`（`test_skills_list_is_a_table_of_every_skill`、`test_skills_show_prints_the_full_content_and_an_effect_summary`）；AI 測試 `tests/engine/test_skill_ai.py` 5 個。

## 4. 設計與實作說明

**模組結構**

- `trpg.content.skills`：`SkillDef` 等 schema（`extra="forbid"`、不可變）與跨檔案驗證函式（形狀／原語參數範圍、狀態／物件引用、`weapon_req` 與 `category`、teleport 限制），所有訊息為繁體中文並指出檔案與技能 ID。形狀與原語是 `content/skill_shapes.yaml`、`skill_primitives.yaml` 的資料（參數範圍、`harmful`、`acts_on`、`allowed_shapes`、預留的 `base_points`／`min_rarity`）；引擎載入時檢查「引擎實作的形狀都有資料」。
- `trpg.engine.skills.shapes`：純函式，只做幾何（影響格子依 `(y, x)` 排序）。`targeting`：`skill_problem`（代價與冷卻）、`compute_area`（驗證選取並算影響範圍，不合法拋 `IllegalActionError`）、`selections`（`legal_actions` 與 AI 共用）、`skill_profile`／`damage_parameters`（命中與傷害參數，解譯器與預覽共用）。`interpreter.use_skill`：支付代價 → `skill_used` → 對每個敵方單位（依 ID）擲命中 → 依技能中原語的順序逐個展開成效果並 **經由 `execute`** 結算（一個原語連同連鎖結算完才處理下一個）。
- 命中判定抽成 `AttackProfile`（攻擊值、近戰、受高度限制、暴擊範圍），普攻取自武器、技能取自技能；`roll_attack`／`half_cover`／`advantage_state` 都吃 profile。`maneuvers.contest` 是推擊、絆倒、技能擊倒共用的對抗判定（`ManeuverRolled.maneuver` 增加 `knock_prone`、`skill_id`）。
- 帶元素傷害「每格只觸及一次」：有單位或物件受到傷害的格子由傷害的觸發表觸及，其餘影響格以 `tile_only` 的 `element_touch` 補上（空格的油被火焰錐形點燃）。
- 預覽：`Preview.targets`（每個擲命中的單位的命中率、暴擊率、傷害範圍與期望值，期望值依各傷害效果的骰子分布精確計算）、`Preview.healed`；`affected_tiles` 含完整影響範圍。擊倒對抗是 `contest(primary=False)`：預覽中 `min` 視為失敗、`max` 視為成功（分歧點，落在「可能」）。
- 效用 AI：每個技能先以便宜估計（敵人數、受傷友方、可破壞物件；傳送技能用虛擬位置價值）篩出前 3 個選取（`SKILL_CANDIDATES`），其餘照原流程用完整 `preview` 評分；`_gains` 對技能改用「每個目標各自命中率」的期望傷害，友方傷害算負分，新增 `heal` 權重（`ai_profiles.yaml`）。

**重要的取捨**

- `SkillDef` 的 `affects` 預設值由原語 `harmful` 決定；`skill_vanish`（對自己加隱蔽）需要明寫 `affects: self`，否則預設為敵方而什麼都不會發生。
- 測試輔助函式 `tests/engine/helpers.py::spawn()` 以範本 ID 指定時預設 **移除範本的技能**（`skills=()`），讓 Phase 1 的 AI／戰鬥情境測試維持原本意義（英雄一旦有技能，AI 會選技能而非普攻）；新測試用 `caster_template([...])` 或 `skills=None` 取得技能。
- 測試專用技能走 `make_state(..., skills=[...])`（把技能加進 `Ruleset` 並重建索引），不放 `content/`。多目標的固定骰值用 `script_rolls`（`with_rolls` 以搜尋種子實作，超過約 4 顆骰就找不到）。
- `LOG_FORMAT` 升為 `trpg-battle-log/4`（`/3` 的紀錄含單位狀態不同，無法重播）。
- 引擎依賴方向不變：`engine` 不匯入 `cli`／`sim`／`llm`…；`import-linter` 與 `test_architecture.py` 通過。

## 5. 數據表

**示範技能（14 個；`uv run trpg skills list` 為權威）**

| 英雄（法力） | 技能 | 骨架 | 形狀 | 效果 | AP | 法力／冷卻 |
|---|---|---|---|---|---|---|
| 戰士（20） | 碎骨重擊 `skill_bone_crusher` | strike | single（武器射程） | 武器傷害 ×1.5、knock_prone | 2 | 4／2 |
| | 旋風斬 `skill_whirlwind` | area | ring 1 | 武器傷害 ×1.0（元素繼承武器） | 2 | 6／3 |
| | 颶風踢 `skill_gale_kick` | displace | single（武器射程） | 武器傷害 ×0.8、push 2 | 1 | 3／2 |
| 弓手（24） | 穿透射擊 `skill_piercing_shot` | area | line 5 | 武器傷害 ×1.0 | 2 | 6／2 |
| | 鉤索箭 `skill_grapple_arrow` | displace | single（武器射程） | 武器傷害 ×0.6、pull 2 | 1 | 3／2 |
| | 煙幕箭 `skill_smoke_arrow` | control | square3（射程 5） | create_surface darkness | 1 | 4／3 |
| | 隱匿 `skill_vanish` | control | self | apply_status concealed 2 回合（`affects: self`） | 1 | 3／4 |
| 法師（40） | 火焰箭 `skill_fire_bolt` | strike | single 5 | 2d8 火焰、apply_status burning | 1 | 6／— |
| | 灰燼誓約 `skill_ashen_oath` | area | cone 3 | 2d6 火焰、create_surface fire 2 回合 | 2 | 12／2 |
| | 閃現 `skill_blink` | displace | ground_tile 3 | teleport | 1 | 5／3 |
| 風暴使（40） | 連鎖閃電 `skill_chain_lightning` | area | chain（射程 5、跳 2、距 3） | 1d10 雷電 | 2 | 10／— |
| | 喚潮 `skill_summon_tide` | control | cross 4 | create_surface water | 1 | 6／2 |
| | 石牆術 `skill_stone_wall` | control | ground_tile 3 | create_obstacle earth_wall | 1 | 5／2 |
| | 聖域 `skill_sanctuary` | aura | allies_in_radius 2 | heal 1d6、create_surface holy（友方腳下） | 2 | 10／3 |

覆蓋：形狀 10/10 全部由示範技能覆蓋（self＝隱匿）；原語 11 種中示範技能覆蓋 9 種（damage、heal、push、pull、knock_prone、teleport、apply_status、create_surface、create_obstacle），`destroy_object` 與 `raise_terrain`／`lower_terrain` 由 `test_skill_primitives.py` 的測試專用技能覆蓋（依規格 5.2）；`category` 兩種；`weapon_req` 四種（melee、ranged、focus、any）；至少 1 個技能使用 `affects: all`（測試專用）。

**示範地圖勝率與輪數**（`uv run python scripts/sim_demo_maps.py --seeds 20`；效用 AI，種子 0–19，`max_rounds=30`；只列出不調整）。我方英雄有技能，敵方暫時沒有（2A-2 才加）。

| 地圖 | 我方勝 | 敵方勝 | 平手 | 我方勝率 | 平均輪數 | 輪數範圍 | 每場時間 | 1C 勝率／平均輪數 |
|---|---|---|---|---|---|---|---|---|
| `bridge_chasm` | 16 | 4 | 0 | 80% | 4.75 | 3–8 | 304 ms | 60%／5.75 |
| `oil_depot` | 8 | 12 | 0 | 40% | 5.00 | 3–8 | 408 ms | 40%／5.30 |
| `swamp` | 11 | 9 | 0 | 55% | 4.95 | 3–9 | 319 ms | 50%／4.80 |
| `ruined_fort` | 14 | 6 | 0 | 70% | 4.95 | 3–7 | 307 ms | 55%／4.95 |

`-m slow` 的 `test_demo_balance.py` 因此有 2 項超出 1C 的 35%–65% 區間（`bridge_chasm`、`ruined_fort`）；依決定 #2 預設不跑，也不調整。

**效能：每個動作（含 AI）的中位數**（`scripts/bench_battle.py --repeat 10 --utility-repeat 5`，種子 42，預設陣容，連跑 3 次的範圍；本工作區波動約 ±30%）

| 地圖 | 1C 中位數 | 2A-1 中位數（範圍） | 2A-1 平均（範圍） |
|---|---|---|---|
| `test_heights_8x8` | 2.48 ms | 2.99–3.26 ms | 3.2–3.6 ms |
| `bridge_chasm` | 2.27 ms | 2.31–2.68 ms | 4.2–4.3 ms |
| `oil_depot` | 3.44 ms | 2.70–2.98 ms | 4.4 ms |
| `swamp` | 3.65 ms | 2.53–3.97 ms | 3.7–3.9 ms |
| `ruined_fort` | 2.47 ms | 2.34–2.59 ms | 3.4 ms |

中位數與 1C 相當（約 2.3–4.0 ms，仍符合 1C 的 ≤ 5 ms 目標）；平均值較高是因為技能的完整 `preview`（每技能最多 3 個選取）。因為戰鬥更短（技能殺得快），各場動作數也較少，量測雜訊相對較大。

## 6. 待 PM 決定

1. **敵方沒有技能，勝率明顯偏向我方**（`bridge_chasm` 80%、`ruined_fort` 70%）。2A-2 加入敵人技能後再看；是否需要在 2A-2 之前先調整英雄的法力或冷卻？（預設：不調，2C 統一處理。）
2. **AI 篩選的後果**：依 5.3 只考慮「範圍內有敵人、可破壞物件，或受傷友方（治療）」的選取，因此純場地技能（煙幕箭、石牆術、單獨的喚潮、隱匿）只在範圍內剛好有敵人時才會被用；閃現（傳送）以位置價值評估，不受此限。2A-2 的完整 AI（6.3）是否放寬？
3. **技能暴擊範圍固定為自然 20**（不使用武器的 `crit_range`）。規格 4.1 只寫「自然 20」，這是最保守的解讀；是否要讓武器技沿用武器暴擊範圍？
4. **`affects: all` 且形狀包含施放者時，施放者會對自己擲命中並受傷**（規格 3.4 的字面解讀）。是否要改成永遠排除施放者？
5. **knock_prone 在預覽中是分歧點**（`min` 失敗、`max` 成功），`Preview.targets` 不含擊倒成功率，只有「可能」的連鎖。是否要補一個成功率欄位？
6. **冷卻語意**：使用當回合設定冷卻 N，之後每個自己的回合開始 −1；因此冷卻 2 ＝ 隔一回合。目前每個冷卻中的技能在每次自己回合開始都會發一個 `skill_cooldown_changed` 事件（包含歸 0），戰鬥紀錄只顯示「冷卻結束」。是否滿意？
7. **測試輔助函式 `spawn()` 預設移除技能**（保護 Phase 1 的 AI 情境測試）。若 PM 希望 Phase 1 的情境也在「有技能」的條件下成立，需要重寫那 9 個 AI 測試。
8. **單體技能能否選友方／物件為目標**：目前依效果決定——對敵方需有 `enemies`／`all`／`tiles` 效果；對友方需有 `allies`／`all`／`tiles`（或 `self` 且目標是自己）；物件需有傷害或地形類（`tiles`）效果，且不擲骰。`ground_tile` 與 `cross`（range 0）可選施放者自己所在的格子。規格未寫明，採最保守的合法性。
9. **`skill_vanish` 與 `affects`**：`apply_status` 屬於有害原語，預設對敵方；自我強化必須明寫 `affects: self`。2B 做預算／LLM 產生技能時是否要讓 `harmful` 的預設更直覺（例如依 `status` 本身的好壞）？
10. **引擎的 `noqa`**：為了維持 ruff 的複雜度規則，`compute_area`、`skill_problem`、`roll_attack` 等函式加了 `noqa`（PLR0912／0915／0911／0917），沒有重構。2B 之前是否要拆分？

## 7. 給下一階段的備註

- 2A-2 的條件系統：`SkillDef.condition` 與 `EffectSpec.condition` 欄位已存在且目前必須為 `null`；解譯器的 `_Cast.build` 以 `ResolvedEffect` 逐個展開，要加條件只需在 `run()` 迴圈前後過濾。
- 敵人技能：單位範本的 `skills`／`max_mana` 已可用；`_check_loadouts` 在開戰時驗證，`UtilityAI` 對任何陣營一視同仁，所以只要在敵方範本填 `skills` 與 `max_mana` 即可（記得先確認 `weapon_class` 相容）。
- `preview` 對 `UseSkill` 的 `targets` 只涵蓋「有擲命中」的單位；若 2A-2 的 AI 要評估友方治療價值，用 `Preview.healed`。
- 測試專用技能用 `tests/engine/skill_helpers.py`（`battle`、`cast`、`of`、`hit_with`、`script_rolls`）與 `helpers.make_skill`。
- `AiWeights.heal` 已加入四個行為模式（守衛 10、其餘 4），數值未經模擬調整。

## 8. 附錄：代表性的 CLI 輸出節錄

`uv run trpg battle --map oil_depot --seed 42`（節錄）：

```
— 法師 的回合（AP 3，移動 5，法力 35/40）
  法師 施放「灰燼誓約」（AP 2，法力 12，冷卻 2 回合）→ 影響 9 格
  法師 以「灰燼誓約」攻擊 盜賊弓手：d20=16 修正 +0 熟練 +2 = 18（目標 11）→ 命中
  法師 以「灰燼誓約」攻擊 盜賊頭目：d20=2 修正 +1 熟練 +2 = 5（目標 11）→ 失手
    矮牆 受到 14 點火焰傷害［骰 5+1］，HP 40 → 26
    盜賊弓手 受到 20 點火焰傷害［骰 2+6］（元素修正 ×1.25），HP 15 → 0
  ＊ 盜賊弓手 倒下了！
  (2, 3) 出現了火焰
  (3, 3) 出現了火焰
  …
  盜賊頭目 獲得狀態「燃燒」（2 回合）
  法師 施放「火焰箭」（AP 1，法力 6）→ 影響 1 格
```

`uv run trpg skills show skill_ashen_oath`：

```
灰燼誓約（skill_ashen_oath）
  階級 T2（等第 1）  稀有度 稀有  種類 主動  骨架 area
  分類 法術技  武器需求 法器  縮放屬性 智力
  代價 AP 2，法力 12，冷卻 2 回合
  形狀 錐形（大小 3）
  效果：
    1. 2d6＋智力加成的火焰傷害（敵方）
    2. 生成「火焰」表面 2 回合（影響的格子）
  標籤 fire、ash、area
  概念 在燒毀村莊中覺醒的灰燼之力
  施放 灰燼從你掌心捲起，化作燎原之火
  來源 builtin，綁定，不可交易
```

`uv run trpg battle replay <log>` → `重播驗證通過：90 個動作、384 個事件，最終狀態一致（oil_depot，種子 42）。`
