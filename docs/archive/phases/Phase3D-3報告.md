# Phase 3D-3 報告：修正變形 ＋ 新反應時機 ＋ 3C-5a 的修正

## 1. commit

| commit | 內容 |
|---|---|
| c4c5b7e | 3C-5a 的修正：投擲的油桶摔破漏油（不爆炸）、倒塌物可破壞；AI 與預覽跟著調整；改寫／新增投擲與推倒的測試 |
| 715eae5 | 四個新反應事件 `hit_by_spell`、`ally_downed`、`enemy_enters_adjacent`、`ally_targeted`；四個示範反應技與 build 裝備；引擎、預覽、API 測試 |
| 20b30c7 | 修正規則讓技能變形：`area_delta`、`shape_to`、`allow_self_target`；`skill_shapes.yaml` 的轉換表；預算；三個示範修正技能；引擎、預覽、API、預算測試；`LOG_FORMAT` `/22`（程式碼部分） |
| 6e7311a | `LOG_FORMAT` 相關測試與 CLI 快照重錄 |
| （本報告） | 報告 |

開發期間 main 上有玩法 PM 的 docs commit；我沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 3C-5a 的修正（3.2A）

- **投擲的油桶改成漏油**：`HurlObjectEffect` 新欄位 `ignite`（技能帶火元素）；爆炸物只有在 `ignite`、或落點本來有火焰表面時才爆炸（`outcome: exploded`）。否則走 `shattered`：物件摧毀（原因 `hurled`），`object_destroyed` 觸發表把原因 `hurled` 也當作會漏油（原本只有 `damage`），所以依油桶原本的 `spill` 規則，**落點與上下左右 4 格變成油**，不爆炸。落點的單位照樣被砸（物理傷害與擊倒）。
- **「技能帶火元素」的定義**（`modifiers.skill_is_fiery`）：技能標籤有 `fire`（含修正規則 `add_tags` 加上的）、技能有元素為火的效果、或修正規則的 `add_element: fire` 讓物理傷害變火。這樣改造型「燃燒投擲」可以做出來，念力投擲本身（標籤 arcane／spell／telekinesis，沒有火）不爆炸。
- **AI**：`scene_objects._hurl_value`：油桶只在「技能帶火或落點有火」時才計爆炸範圍；不爆炸而漏油時，只有行動者有火焰技能（`has_fire_follow_up`：裝備的主動技能，標籤或效果帶火，不含投擲技能自己）才把油（落點與上下左右）上的敵人納入候選。預覽收益：`utility._oil_setup_gains` 在同樣條件下，站在油上的敵人增加的數目 × `surface` 權重的一半（油本身不是有害表面，原本不會計分）。「鋪油後同回合或下回合有火焰技能」用「有沒有裝備火焰技能」近似，沒有檢查冷卻與法力（規格寫「最簡單近似」）。
- **預算**：念力投擲 `hurl_object` 的預算公式本來就沒有計入爆炸（骰子平均 × 800‰ ＋ 擊倒 3），數值不變（72.4%）；爆炸從「附贈」變成「要先鋪油再點火的兩步連招」，是玩法面的削弱，預算沒有跟著調降（見待決 #1）。
- **倒塌物可破壞**：`rubble` 加 `breakable` 與 `max_hp: 15`（同木箱）。`scripts/map_push_check.py`：10 張正式地圖全部「通」。倒下的柱子現在會壓到舊的倒塌物（它是可破壞物件，和木箱一樣受傷），所以內容裡已沒有「阻擋移動又不能破壞」的物件；`topple_line` 對這種物件的分支保留（測試用自訂物件驗證）。

### 2.2 四個新反應事件（3.2）

| 事件 | 觸發點 | 另一方 | 實作 |
|---|---|---|---|
| `hit_by_spell` | 敵方 `category: spell` 的技能命中持有者後、傷害（與格擋）結算之前 | 施放者 | `_Cast._roll_one`（單體攔截之後），`reactions.spell_hit_reactions` |
| `ally_downed` | 持有者視野（`has_line_of_sight`）內的友方倒下之後；**等效果佇列清空**才處理（`ctx.downed` ＋ `settle`），所以技能或普攻結算完才反應 | 倒下的友方 | `skill_triggers.observe` 收集 `unit_downed`、`_settle_downed` → `reactions.ally_downed_reactions` |
| `enemy_enters_adjacent` | 敵方單位**主動移動**（步行 `_do_move`、衝鋒 `_dash_walk`、直線衝撞 `_charge_walk`）的每一步之後，若新位置與持有者相鄰、移動前不相鄰 | 該敵人 | `reactions.enemy_enters_adjacent_reactions`；強制位移、傳送、跳躍、互換不算 |
| `ally_targeted` | 相鄰友方被敵方單體技能（形狀 `single`、有敵對效果）或普攻選為目標、命中判定之前 | 攻擊者 | `_Cast.react_to_targeting`（`run` 中 `roll_hits` 之前）與 `_attack_once`；反應讓攻擊者或目標倒下時這次攻擊落空 |

- 反應的次數（`reactions_per_round`）、冷卻、法力、`prompt`／`auto`／`off` 三種模式與 `pending` 暫停流程都沿用既有機制（`_react`／`_decide`／`_use`）；`trigger_event_seq` 新增四個比對器，網頁的詢問文字（引發詢問的事件文字）自然帶出。
- 資料：`ReactionEvent`、`SKILL_REACTION_EVENTS`、`ReactionWhen`、`view.REACTION_TRIGGER_TEXT`（規則的中文說明）、`content/reactions.yaml` 的說明註解都已加入。`ally_downed` 的反應技形狀必須是 `self`（另一方已經倒下，無法當目標），由 schema 檢查。
- **隨機組合器不產生新事件**：`LEGACY_REACTION_EVENTS`（原本四個）給組合器，既有種子的組合結果不變（snapshot 沒有因此改變）。
- 示範技能（全部稀有、T1，預算在 70–100%）：

| 技能 | 事件 | 內容 | 預算 | 裝備 |
|---|---|---|---|---|
| 反咒 `skill_counterspell` | `hit_by_spell` | 對施放者 2d6 暗影傷害，法力 4、冷卻 1 | 77.9% | build_banisher |
| 悲憤 `skill_grief_rage` | `ally_downed` | 自己獲得激昂 2 回合 ＋ 1d8 護盾，冷卻 2 | 92.0% | build_tank |
| 迎頭痛擊 `skill_ambush_stab` | `enemy_enters_adjacent` | 對進入者一次武器傷害，冷卻 1 | 79.4% | build_assassin |
| 掩護射擊 `skill_covering_fire` | `ally_targeted` | 對攻擊者 80% 武器傷害 ＋ 緩速 1 回合，冷卻 1 | 80.5% | build_ranged |

  每人反應欄位只有 1 個，所以四個技能各裝在一個沒有反應技的 build，沒有新增 build。

### 2.3 修正規則讓技能變形（3.1）

資料（`ModifierChange` 新增三種，仍是「恰好一種」）：

```yaml
change: {area_delta: 1}            # 範圍型形狀大小 +1（只能是 1）
change: {shape_to: line}           # line | chain | cone
change: {allow_self_target: true}
```

- 三種 change 的對象：`area_delta`、`shape_to` 可用於 `all_attacks`、`all_skills`、`skill_tags`；`allow_self_target` 用於 `all_skills`、`skill_tags`（不能套用在基本動作；schema 拒絕）。條件只能是 `self_hp_below`（選目標前就決定，同 `range_delta`）。
- **形狀轉換表放在 `content/skill_shapes.yaml` 的 `conversions`**（內容即資料）：`single → line`（size 3）、`single → chain`（jumps 1、jump_range 2、保留 `range` 並截斷到 1–6，`"weapon"` 取施放者武器射程）、`line → cone`（保留 `size`，截斷到 2–4）。載入時驗證（形狀存在、目標在 `line／chain／cone`、參數在範圍內、必要參數齊全、不重複）。表列之外的組合（例如環形 → 直線、單體 → 錐形）不轉。技能的效果原語若不允許新形狀（`skill_primitives.yaml` 的 `allowed_shapes`，例如衝鋒必須是單體）也不轉。
- **引擎做法**：`modifiers.shaped_skill(state, unit, skill)` 產生變形後的技能（`model_copy`，ID、標籤、效果、代價不變，只改 `shape` 與 `include_caster`；沒有變化時回傳原物件）。套用在 `legal_actions` 的技能列舉（`_usable_skills`）、`use_skill`（實際結算）、預覽（`modifiers.acting_skill`，7 處）。所以合法動作、預覽、網頁目標選取（網頁用 `legal_actions` 的 `direction`／`target_id` 與預覽的 `affected_tiles`）與結算一致。只有 `kind: active` 的技能變形（姿態、反應技、被動不變）。
- **套用順序**（確定性）：依技能 ID、規則索引，先依序套用 `shape_to`（可接續轉，例如單體 → 直線 → 錐形），再把每條 `area_delta` 的 +1 加上去（上限為 `skill_shapes.yaml` 的參數最大值；`cross`、`square3` 只有 `range`，大小固定，不受影響），最後看 `allow_self_target`。
- **`allow_self_target` 的詮釋**（待決 #2）：單體形狀本來就能選自己（`legal_actions` 已列出，已驗證），所以這條規則的作用是：對有友方效果（`affects: allies`）的技能，影響範圍不含施放者的範圍型形狀（直線、錐形、十字、方陣、環形、指定格）把施放者算進影響單位。新增 `SkillDef.include_caster`（變形後的技能才會是 `true`，資料檔不必寫）。搭配 `shape_to: line` 的療癒技能就是「一道掃過整排隊友、也包含自己的光束」。
- **預算**（`skill_budget.yaml` 的 `modifier`）：沿用「使用次數 × 每次價值」，再 × `shape_benefit_permille`（新，400‰，站位剛好受益的比例）。`shape_to` 的每次價值＝基準武器傷害 7 ×（轉換後 − 轉換前的形狀倍率）：直線 ＋400‰ → 2.8、連鎖 ＋250‰ → 1.75、錐形（自 3 格直線）＋200‰ → 1.4；`area_delta` 1.4（flat）、`allow_self_target` 2.8（flat）。「預算計算在修正技能本身」：`trpg skills budget` 每條規則一列，列出形狀倍率前後值。
- **描述**：`trpg skills show` 顯示三種規則的中文說明（`narrative/skills.py`）。
- **示範修正技能**（史詩 T1，都是 80.0%）：震懾餘波 `skill_lingering_roar`（`skill_tags: [shout, area]` 範圍 +1：挑釁怒吼的環形半徑 1 → 2，build_tank）、慈悲光束 `skill_beam_of_mercy`（`skill_tags: [heal]` 單體 → 直線，build_healer）、自我療癒 `skill_self_mending`（`skill_tags: [heal]` `allow_self_target`，build_healer）。回春因此變成「影響 4 格」（直線 3 格 ＋ 自己）的光束，AI 照常使用。

## 3. 驗收條件逐條

### 3D-3 驗收 1：三種 change 的合法／不合法、預覽一致、預算重算

| 項目 | 證據 |
|---|---|
| 三種 change 合法例子、不合法例子 | `tests/content/test_modifier_schema.py::test_every_change_kind_has_a_valid_example`（13 種 change 各一個合法例子，含新增三種）、`test_invalid_modifier_skills_are_rejected`（新增 10 個不合法例子：`area_delta` 0／2、套用在基本動作、`allow_self_target` 套在 `all_attacks`、為 false、**不允許的形狀轉換 `shape_to: ring`／`single`**、兩種 change、條件不是 `self_hp_below`） |
| 轉換表本身被驗證 | `tests/engine/test_skill_shaping.py::test_the_conversion_table_is_validated`（目標不在 line／chain／cone、重複、參數超出範圍、缺必要參數、`keep` 不是原形狀的參數、缺目標形狀、形狀不存在） |
| 表列之外的轉換不轉 | `test_pairs_outside_the_conversion_table_are_refused`（環形、錐形不能變直線；單體不能直接變錐形；十字不能變錐形）、`test_skills_whose_effects_need_the_original_shape_are_not_converted`（猛虎衝撞維持單體） |
| 各 change 的行為 | `area_delta`：`test_area_delta_adds_one_to_a_cone_and_the_area_grows`（錐形 2 → 3：4 格 → 9 格）、`test_area_delta_grows_each_sized_shape`、`test_area_delta_stops_at_the_shape_maximum`、`test_area_delta_leaves_fixed_size_shapes_alone`、`test_area_delta_stacks_and_respects_the_condition`、`test_only_matching_skills_and_only_active_skills_are_reshaped`；`shape_to`：`test_single_to_line_changes_the_selections_and_hits_everyone_on_the_line`、`test_single_to_chain_keeps_the_range_and_clamps_it`、`test_single_to_chain_uses_the_weapon_range_for_weapon_range_skills`、`test_line_to_cone_keeps_the_size_up_to_the_cone_maximum`、`test_conversions_chain_in_skill_id_order_and_area_delta_comes_last`；`allow_self_target`：`test_a_line_heal_includes_the_caster_only_with_allow_self_target`、`test_allow_self_target_is_a_no_op_for_single_target_heals_and_attacks` |
| 變形後的預覽、合法動作與結算一致 | `test_the_preview_shows_the_reshaped_area_and_matches_the_resolution`（預覽影響格／影響單位 ＝ 結算的傷害對象）、`test_preview_and_legal_actions_include_the_caster_in_a_self_inclusive_line`、`test_legal_actions_never_list_an_action_the_resolution_would_refuse`（變形後每個合法動作都能結算）；API：`tests/api/test_skill_shaping_api.py::test_a_converted_heal_is_selected_by_direction_and_includes_the_caster`（`legal_actions` 變成方向選取、預覽的格子 ＝ 結算 `skill_used` 的格子、施放者在範圍內） |
| 預算重算 | `test_the_budget_of_shape_to_is_the_shape_multiplier_difference`（直線／連鎖／錐形的點數 ＝ 7 ×（轉換後 − 轉換前倍率）× 6 次 × 400‰）、`test_the_budget_of_the_other_shape_changes_uses_the_flat_points`、`test_the_shipped_shape_modifiers_pass_the_budget_and_validation`；`trpg skills budget skill_beam_of_mercy`：80.0% 合格 |

### 驗收 2：四個反應事件的觸發／不觸發、網頁詢問模式（API）

`tests/engine/test_reaction_events_3d3.py`（29 個）：

| 事件 | 觸發 | 不觸發 |
|---|---|---|
| `hit_by_spell` | `test_hit_by_spell_fires_before_the_spell_damage_and_targets_the_caster`（命中 → 反應 → 反咒傷害 → 法術傷害的順序）、`test_a_shield_reaction_is_up_before_the_spell_damage` | `test_hit_by_spell_ignores_weapon_skills_basic_attacks_and_misses`（普攻、武器技、未命中） |
| `ally_downed` | `test_ally_downed_fires_after_a_visible_ally_goes_down` | `test_ally_downed_ignores_enemies_itself_and_allies_that_survive`、`test_ally_downed_needs_the_owner_to_see_the_ally`（牆擋住視線）、`test_ally_downed_respects_the_reactions_per_round_limit` |
| `enemy_enters_adjacent` | `test_enemy_enters_adjacent_fires_when_a_walker_arrives_next_to_the_owner`、`test_a_dash_into_the_owners_reach_triggers`、`test_the_reaction_can_kill_the_walker_before_he_takes_the_next_step` | `test_a_walker_that_stays_two_tiles_away_does_not_trigger`、`test_allies_walking_next_to_the_owner_do_not_trigger`、`test_forced_movement_next_to_the_owner_does_not_trigger`（鉤索箭把敵人拉到旁邊） |
| `ally_targeted` | `test_ally_targeted_fires_before_the_attack_is_rolled`、`test_ally_targeted_also_fires_for_a_single_target_skill`、`test_ally_targeted_that_downs_the_attacker_cancels_his_attack` | `test_ally_targeted_needs_the_target_next_to_the_owner_and_not_the_owner`、`test_ally_targeted_ignores_area_skills_and_enemy_targets` |

詢問模式：各事件的引擎 `prompt` 測試（`*_is_asked_in_prompt_mode`／`test_hit_by_spell_ask_the_player_with_prompt_mode`：暫停、`pending` 欄位、接受與拒絕）；**API**：`tests/api/test_new_reactions_api.py`（8 個）——四個事件各自：`GET` 回 `awaiting: decision`、`pending.kind/unit_id/skill_id/reaction/trigger_unit_id`、單位 `reaction_rules` 帶 `event`、`mode: prompt` 與中文 `trigger_zh`；`POST /decision` 接受 → 事件有 `reaction_triggered`、拒絕 → `reaction_declined`，之後 `pending` 清空。預覽：`test_previews_include_the_new_reactions`（四個事件的預覽 `max_events` 都含反應）。AI 整場與重播：`test_ai_battles_with_the_new_reactions_replay`（assassin／open_plain 種子 1「迎頭痛擊」、tank／swamp 種子 0「悲憤」、ranged／narrow_halls 種子 0「掩護射擊」；`hit_by_spell` 的整場需要敵方施放法術技，現有遭遇幾乎沒有，由引擎測試涵蓋）。

### 驗收 3：3.2A

| 項目 | 證據（`tests/engine/test_hurl_object.py`、`test_topple.py` 等） |
|---|---|
| 油桶投擲漏油、不爆炸 | `test_a_hurled_oil_barrel_spills_oil_and_does_not_explode`（無 `object_exploded`、無爆炸傷害；落點與上下左右 4 格變成油，斜角不會；落點單位照樣被砸） |
| 落點有火時爆炸 | `test_a_hurled_oil_barrel_explodes_when_it_lands_on_fire` |
| 火元素投擲時爆炸 | `test_a_fire_element_hurl_makes_the_oil_barrel_explode`（標籤 fire）、`test_a_fire_damage_effect_in_the_skill_also_counts_as_fire`、`test_a_modifier_that_turns_damage_to_fire_makes_the_barrel_explode` |
| 木箱不漏油 | `test_a_crate_still_just_shatters_without_oil` |
| 預覽 | `test_scene_preview.py::test_a_hurl_preview_shows_where_the_object_goes_and_what_happens`（桶：`shattered`；落點有火：`exploded`） |
| AI | `test_scene_ai.py::test_hurl_estimate_counts_the_explosion_when_the_barrel_lands_on_fire`、`test_hurl_estimate_counts_oil_only_when_the_caster_has_a_fire_skill`；整場：`test_an_ai_battle_hurls_objects_and_replays`（build_fire／narrow_halls 種子 2：AI 丟油桶、出現油、重播一致） |
| 倒塌物可被打掉 | `test_rubble_is_a_breakable_object_with_the_crate_hp_and_can_be_destroyed`（HP 同木箱、可攻擊摧毀）、`test_a_toppled_pillar_crushes_old_rubble_because_rubble_is_breakable`、`test_a_non_breakable_object_stops_the_fall`（改用測試自訂的不可破壞物件） |
| `map_push_check.py` | `uv run python scripts/map_push_check.py`：10 張地圖狀態全部「通」，「單次推倒會封路」欄全為 — |

### 驗收 4：`check.py` 全過、重播一致

`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2303 passed**）、client typecheck、vitest（110 passed）全部通過。重播：`test_ai_battles_with_the_new_reactions_replay`（3 場）、`test_ai_battles_with_reshaped_skills_replay`（healer、tank 各一場）、`test_an_ai_battle_hurls_objects_and_replays`，另有 `battle` CLI 快照（既有戰鬥的雜湊沒有變）。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/engine/test_hurl_object.py::test_a_hurled_oil_barrel_explodes_at_the_landing_tile` | 規格明訂改成漏油；改寫為漏油、落點有火爆炸、火元素爆炸三個測試（另加修正規則與木箱的測試）；`arena` 輔助函式多註冊測試技能 |
| `test_hurl_object.py::test_an_ai_battle_hurls_objects_and_replays`、`test_scene_ai.py::test_sim_metrics_count_scene_events`、`…::test_sim_maps_takes_an_ally_build_and_prints_the_scene_line` | AI 行為隨油桶規則改變：原本的種子（narrow_halls 9）不再丟東西，改成 narrow_halls 種子 2 |
| `test_scene_ai.py::test_hurl_estimate_counts_the_explosion_not_only_the_landing_tile` | 估計值隨規則改變：改成「落點有火才算爆炸」，另加「沒火：空格落點無價值」「有火焰技能：油算進去」 |
| `test_scene_preview.py::test_a_hurl_preview_…` | 油桶預期結果改為 `shattered`；加落點有火的 `exploded` |
| `tests/engine/test_topple.py::test_a_non_breakable_object_stops_the_fall` | 倒塌物變成可破壞，原本拿它當「不可破壞的擋路物件」；改用測試自訂的不可破壞物件 |
| `tests/skillgen/test_composer_skeleton_driven.py::test_reaction_events_have_a_single_source` | 組合器的事件來源改為 `LEGACY_REACTION_EVENTS`（只用原本四個），並確認新事件不在組合器內 |
| `tests/content/test_modifier_schema.py` | 加入三種新 change 的合法／不合法例子 |
| `tests/cli/test_budget_cli.py` | 技能總數 97 → 101（四個反應技）→ 104（三個修正技能） |
| `tests/cli/test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/21` → `/22` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 兩筆重錄（新增 7 個技能）；所有戰鬥類快照沒有變 |

## 5. 新增的複雜度 noqa

沒有 C901、PLR0911、PLR0912、PLR0915。開發中 `narrative.skills._change_text` 與 `skillgen.budget._modifier_value` 一度超過 PLR0911，各拆出 `_other_change_text` 與 `_structured_value`。新增的非複雜度 noqa：`skill_triggers._settle_downed` 的 `PLC0415`（延後匯入反應模組，與同檔既有的 `_resolve_one` 相同理由：避免循環匯入）、兩個測試內的 `PLC0415`。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/22`**（本段只升一次）：新的修正規則內容（`area_delta`／`shape_to`／`allow_self_target`、`skill_shapes.yaml` 的 `conversions`、`SkillDef.include_caster`）、四個新反應事件（單位反應規則的 `when.event` 新值）、投擲油桶的結算改變（舊紀錄裡投擲的油桶用新版程式重播會得到不同結果，所以不能向下相容）、倒塌物可破壞。沒有新增事件型別。

## 7. 待 PM 決定（最多 10 點）

1. **念力流的預算與玩法**：油桶不再爆炸後，念力投擲的預算公式本來就沒算爆炸，所以點數沒有調；實際強度下降（要火焰技能配合才有爆炸）。AI 只用「有裝備火焰技能」近似「兩步連招」，沒看冷卻與法力。是否要在平衡階段把念力投擲（或新做一個「燃燒投擲」改造型技能）重新調整？
2. **`allow_self_target` 的詮釋**：單體治療本來就能選自己（已驗證），所以我定義為「範圍型形狀的影響範圍把施放者算進去」（對有友方效果的技能才有意義；單體技能不變）。若 PM 想要的是別的意思（例如「單體技能的 `affects: allies` 本來排除自己」——現況不是這樣），請指示。
3. **`area_delta` 的「square 邊長」**：現有形狀沒有可變大小的方形（`square3` 固定 3×3，`cross` 只有射程），所以只有直線／錐形的 `size` 與環形／範圍光環的 `radius` 會變大；已在上限時沒有效果（不報錯）。
4. **轉換參數與保留規則**：單體 → 直線固定 3 格、單體 → 連鎖 1 跳（跳距 2）並保留射程（上限 6）、直線 → 錐形保留長度（上限 4）。數值寫在 `skill_shapes.yaml` 的 `conversions`，可調。轉換後的技能不會重新跑預算與驗證（只在修正技能上計價）。
5. **修正規則的預算初值**：每次價值取基準傷害 × 形狀倍率差，再 × `shape_benefit_permille`（400‰）；三個示範修正技能都落在 80.0%。`shape_benefit_permille` 與 `area_delta`（1.4）、`allow_self_target`（2.8）的 flat 點數都是初值，沒有模擬。
6. **只有主動技能變形**：姿態、反應技、被動不受 `shape_to`／`area_delta`／`allow_self_target` 影響（反應技形狀只能是 self／single，轉換會破壞規則）；也沒有套用在被複製的技能（`copy_skill`）。
7. **`enemy_enters_adjacent` 的「主動移動」**：算步行、衝鋒（`dash`）、直線衝撞；**不算**傳送、跳躍（`leap`）、互換位置（與藉機攻擊一致，這幾種不觸發藉機攻擊；與 3D-1 #4「`moved_this_turn` 只看步行與 `dash`」也一致）。若要把 `leap`、自身傳送算進去需要另訂。
8. **`ally_downed` 的時機**：等整個技能／整次攻擊／效果佇列結算完才反應（不是在倒下那個效果當下），所以範圍技一次擊倒多個友方時，持有者依倒下順序各有機會反應（受每輪次數限制）；視野用 `has_line_of_sight`（距離上限 24 格曼哈頓，濃霧縮短）。
9. **`ally_targeted` 的範圍**：只有單體形狀、帶敵對效果的技能與普攻（含藉機攻擊）；範圍技、連鎖、物件目標、被動觸發不算。每個相鄰友方（依單位 ID）各有一次機會，攻擊者或目標倒下就停止；反應讓攻擊者倒下時，那次攻擊不擲命中（已發出的反應事件保留）。
10. **玩家看不到反應技的觸發時機**：`trpg skills show` 與技能卡片目前沒有「反應時機」這一行（既有反應技也沒有；單位的 `reaction_rules` 有中文 `trigger_zh`）。完整顯示留給 3C-6。另外 `hit_by_spell` 在現有遭遇中幾乎不會被敵人觸發（敵方很少施放法術技），build_banisher 的反咒在整場模擬中看不到。

## 8. 代表性輸出

`uv run trpg battle --map narrow_halls --seed 2 --ally-build build_fire`（連續一段，輸出第 203–226 行）：念力投擲先把油桶丟向敵人（砸死一個盜賊，油桶摔破漏油、**沒有爆炸**），接著同一回合火焰攻擊點燃落點旁的油，盜賊盾衛起火，隊友走進火裡受傷——「先鋪油、再點火」的兩步連招。

```
— 火焰流英雄 的回合（AP 3，移動 5，法力 6/40）
  火焰流英雄 的「灰燼誓約」冷卻結束
  火焰流英雄 施放「念力投擲」（AP 2，法力 5，冷卻 2 回合）→ 影響 1 格
  火焰流英雄 以「念力投擲」攻擊 盜賊：d20=15 修正 +0 熟練 +2 = 17（目標 11）→ 命中
    盜賊 受到 13 點物理傷害［骰 1+6+6］，HP 7 → 0
  ＊ 盜賊 倒下了！
  ✦ 火焰流英雄 把油桶 (3, 3) 丟向 (7, 5)
  ＊ 油桶 (7, 5) 摔得粉碎！
  (6, 5) 出現了油
  (7, 5) 出現了油
  (8, 5) 出現了油
  (7, 6) 出現了油
  火焰流英雄 攻擊 盜賊盾衛：d20=15 修正 -1 熟練 +2 = 16（目標 11）→ 命中
  ⟳ 盜賊盾衛 反應：格擋（耐力 −10）
    盜賊盾衛 受到 2 點火焰傷害［骰 1］（格擋/加成 ×0.5），HP 32 → 30
  (8, 5) 的油變成了火焰
  盜賊盾衛 獲得狀態「燃燒」（2 回合）
  火焰流英雄 從 (3, 5) 移動到 (5, 5)（消耗 2 移動）
  火焰流英雄 的「護盾」結束了
  火焰流英雄 結束回合
— 標準隊友（戰士） 的回合（AP 3，移動 5）
    標準隊友（戰士） 受到 3 點火焰傷害［骰 3］，HP 25 → 22
  標準隊友（戰士） 從 (6, 5) 移動到 (7, 5)（消耗 1 移動）
  標準隊友（戰士） 攻擊 盜賊盾衛：d20=7 修正 -1 熟練 +2 = 8（目標 11）→ 失手
```
