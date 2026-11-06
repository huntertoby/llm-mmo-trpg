# Phase 3G-3b 報告：裝備詞條——授予動作（第 9 類）、授予反應（第 10 類）、改變規則（第 11 類）（G3b）

規格：`docs/phases/Phase3G計畫.md` 第 0、3 節（第 3～6 項）、第 5 節；設計：`docs/design/08-裝備.md` 8.21.2.9～8.21.2.11、8.21.3、8.24（第 9～11 類共 9 條）。
分支 `worktree-agent-a365493ea3e51b8e2`（從 main 的 c89ab75 分出），未 push、未合併。

## 新增與修改的檔案

| 檔案 | 內容 |
|---|---|
| `content/skills/skill_gear_grapple.yaml`、`skill_gear_smoke_bomb.yaml`、`skill_gear_shield_wall.yaml`（新） | 授予的三個常駐技能（1 AP；冷卻 3／4／3；鉤爪單體射程 4 拉 2 格、煙霧彈 `square3` 射程 3 煙霧 2 回合、盾牆 `ground_tile` 射程 1 土牆 2 回合）。沒碰其他技能內容。 |
| `src/trpg/engine/gear.py` | `gear_skill_ids`／`granted_skills`；`geared_template` 把授予的技能接進範本的 `skills`（卸下裝備＝不帶詞條＝沒有技能） |
| `src/trpg/engine/gear_reactions.py`（新） | 第 10 類：`gear_reaction_rules`（開戰時替持有者加規則）、`redirect_affix`、額外次數 `extra_uses_left`／`reaction_available`／`spend_reaction` |
| `src/trpg/engine/reactions.py` | 反應次數檢查與花費走 `gear_reactions`；`try_intercept` 拆成「守護動作 → 攔截反應技 → 裝備的 `redirect_damage`」；監視射擊有額外次數時保留 `overwatch` 狀態到最後一次 |
| `src/trpg/engine/lifecycle.py` | `make_unit` 把裝備的反應規則附在持有者規則後面；倒下時 `spawn_on_downed` 的判斷也看裝備 |
| `src/trpg/engine/activations.py`、`rule_changes.py` | 第 11 類：`active_rule_change` 除了啟動過的傳說，也讀裝備的規則詞條（`has_rule_source`、裝備包成 `skill_gear_rule_*` 來源）；既有的「同時最多 1 個」檢查（`activation_problem`）自動涵蓋裝備 |
| `src/trpg/content/battle.py`、`environment.py`、`content/reactions.yaml` | 新反應事件 `ally_hit_in_range`、反應效果 `redirect_damage`、內建反應 `redirect_damage`（替隊友承受） |
| `src/trpg/content/equipment.py`、`content/rules/equipment.yaml` | 硬上限 `caps.rule_affixes: 1`；`loadout_problems` 檢查改變規則詞條全身最多 1 個（不同 id） |
| `src/trpg/content/library.py` | 載入時檢查：授予的技能存在且是主動技、反應詞條的反應與事件（`extend_trigger` 的事件須為該反應支援、`grant` 須為 `redirect_damage` 並有 `range`） |
| `src/trpg/engine/view.py` | `UnitView.gear_skills`（`GearSkillView`：技能、欄位、物品、詞條，只列己方）、`ReactionRuleView.gear_source_zh`；新事件文字 |
| `content/items.yaml`、`content/units/gear_tester_g3b.yaml`、`gear_tester_g3b_sentinel.yaml` | 測試物品 7 件（鉤爪護手、壁壘塔盾、護衛鎖甲、哨兵頭盔、三件傳說項鍊）與兩個測試單位 |
| `client/openapi.json`、`schema.d.ts` | 重產（只新增欄位與型別） |
| `client/src/battle/gearSkills.ts`、`targeting.ts`、`reactions.ts`、`ui/SkillBar.tsx`、`ui/ReactionPanel.tsx`、`styles.css`（檔尾新增） | 技能列「來自裝備・欄位：物品」、反應設定「來自裝備・物品：詞條」 |
| `tests/engine/test_gear_g3b.py`（60）、`client/src/battle/gearSkills.test.ts`（3）、既有測試對應更新 | 見下方逐條驗收 |

## 設計重點

- **第 9 類**：授予的技能在開戰時併進單位 `skills`，所以行動合法性、預覽、冷卻、AI 候選、技能列全部沿用技能的既有路徑；`gear_skills` 只是來源說明。同一詞條掛兩件只授予一次；單位本來就有同一技能時不重複。
- **第 10 類**
  - `extend_trigger`（遠程也可格擋）：加一條 `block` 規則、事件 `targeted_by_attack`；模式與「耐力不足不觸發」沿用持有者原本的 `block` 規則（沒有則 `auto`）。`SetReactionMode` 以反應 id 為單位，所以兩條規則一起切換。
  - `grant`（替隊友承受）：新內建反應 `redirect_damage`、事件 `ally_hit_in_range`。在 `try_intercept` 中，守護動作與攔截反應技之後，詞條範圍（`range` 2，曼哈頓距離）內的友方（依單位 ID，第一個願意的）替受攻擊的隊友承受整次攻擊（同攔截：不重擲命中）。每輪 1 次用 `gear_round_counts[詞條 id]`；拒絕（詢問模式）不扣次數。佔用一般的反應次數。
  - `extra_uses`（監視射擊 +1）：先用 `reactions_per_round`，用完才用額外次數（`gear_round_counts["extra:<反應>"]`，每輪清除）；只對詞條指定的反應有效。監視射擊還有額外次數時狀態保留，最後一次才移除。
  - 反應詢問走原本的暫停點（`prompt` → `pending` → `resume`）。
- **第 11 類**：`active_rule_change(state, 單位, kind)` 是四類規則（慈焰、移山、血痕、殘影）共同的查詢，呼叫端本來就以「造成效果的單位／推動者／步行者／倒下者」為鍵，所以只作用在持有者；本段只把裝備加成另一個來源。同時生效最多 1 個：穿戴驗證擋兩條不同的規則詞條；裝備規則生效時 `activation_problem` 擋啟動型傳說的規則改變。
- 預覽與 AI 走同一個結算流程，不需另寫：授予技能的預覽、對隊友攻擊時的攔截、持有者火焰的治療都在預覽事件裡。

## LOG_FORMAT

`trpg-battle-log/42` → **`trpg-battle-log/43`**：單位 `skills` 含授予技能、反應規則含裝備規則、新反應事件 `ally_hit_in_range`／內建反應 `redirect_damage`、`gear_round_counts` 的 `extra:<反應>` 鍵、`caps.rule_affixes`、新技能 `skill_gear_*`。`/42` 不相容。合併時若 3-24c 或 3G-G5b 也遞增，由 PM 處理版號。另外新增三個技能，`tests/narrative` 的圖示 fixture（`client/src/render/fixtures/skill_icons.json`）已重產，3-24c 也新增技能時合併請再重產一次。

## 逐條驗收

證據都在 `tests/engine/test_gear_g3b.py`（60 個），除非另註。

| 規格 | 證據 |
|---|---|
| 9 條詞條載入、引用檢查 | `test_nine_whitelist_affixes_load_and_reference_existing_things`、`test_library_rejects_bad_action_and_reaction_references`、`test_gear_skills_are_content_with_the_stated_costs` |
| `affix_act_grapple` | `test_grapple_pulls_a_target_in_range_two_tiles_and_goes_on_cooldown`（4 格外拉近 2 格、1 AP、冷卻 3）、`test_grapple_cannot_reach_beyond_four_tiles` |
| `affix_act_smoke` | `test_smoke_bomb_makes_smoke_for_two_rounds`（3×3、2 輪、冷卻 4、3 格外不合法） |
| `affix_act_shield_wall` | `test_shield_wall_raises_a_temporary_obstacle_in_front`（前方 1 格、暫時、冷卻 3） |
| **授予的技能卸下即失去** | `test_grapple_is_granted_by_gear_and_lost_without_it`、`test_grant_does_not_duplicate_...`、`test_same_granting_affix_on_two_items_grants_the_skill_once`；前端 `gearSkills.test.ts`（卸下後按鈕消失） |
| 技能列顯示來源 | `test_granted_skills_are_listed_with_their_equipment_source`（`gear_skills`；敵方看不到）；截圖 `docs/phases/img/3G-3b-skill-bar.png` |
| AI 能用授予的技能 | `test_ai_ranks_a_granted_skill_among_its_candidates`、`test_ai_uses_the_granted_skill_to_drag_an_enemy_into_lava`（AI 選鉤爪把殘血敵人拉進岩漿） |
| 預覽 | `test_preview_of_a_granted_skill_shows_cost_and_effect` |
| `affix_react_ranged_block` | `test_ranged_block_lets_the_owner_block_ranged_attacks`（傷害減半）、`test_block_by_default_does_not_trigger_against_ranged`、`test_ranged_block_keeps_working_against_melee`、`test_ranged_block_follows_the_mode_of_the_existing_block_rule`、`test_set_reaction_mode_switches_the_gear_rule_too`、`test_ranged_block_only_changes_its_owner` |
| **反應暫停點（格擋）** | `test_ranged_block_pauses_for_a_decision_in_prompt_mode`（暫停 → 接受格擋／拒絕不格擋） |
| `affix_react_guard_ally` | `test_guard_ally_redirects_an_attack_on_a_teammate_within_range`、`..._does_not_trigger_beyond_its_range`、`..._when_the_owner_is_attacked`、`test_guard_ally_is_once_per_round_and_resets_each_round`、`..._off_mode_never_triggers`、`test_guard_ally_is_gone_without_the_gear` |
| **反應暫停點（替隊友承受）** | `test_guard_ally_pauses_for_a_decision_and_can_be_declined`（暫停；拒絕後攻擊仍打隊友、次數未用掉；接受後攔截） |
| `affix_react_double_overwatch` | `test_double_overwatch_fires_twice_then_ends`、`..._fires_once_per_round_without_the_gear`、`..._keeps_the_status_after_the_first_shot`、`..._extra_use_comes_back_each_round`、`..._does_not_give_other_reactions_extra_uses` |
| 反應設定顯示來源 | `test_ranged_block_rule_shows_as_coming_from_gear`、`test_guard_ally_shows_in_the_reaction_settings_as_gear`；截圖 `3G-3b-reaction-settings.png` |
| 預覽反映反應 | `test_guard_ally_preview_redirects_too` |
| `affix_rule_fire_mends` | `test_fire_mends_heals_allies_hit_by_the_holders_fire`、`..._still_burns_enemies_the_holder_and_other_elements`、`..._is_not_active_without_the_gear` |
| `affix_rule_move_any_object` | `test_move_any_object_lets_the_holder_push_an_earth_wall_from_the_start`、`..._pushes_other_blocking_objects`（3 種）、`..._does_not_move_floor_objects`、`..._is_off_without_the_gear` |
| `affix_rule_bleeding_wake` | `test_bleeding_wake_marks_each_adjacent_enemy_once_per_move`、`..._respects_the_trigger_depth_limit`、`..._is_off_without_the_gear` |
| **規則改變只影響持有者／不影響全域** | `test_fire_mends_only_applies_to_the_holders_own_fire`（敵人與無裝備隊友的火照常傷人）、`test_fire_mends_does_not_change_other_units_results_at_all`（非持有者的結算，持有者穿不穿裝備事件逐筆相同）、`test_move_any_object_does_not_let_other_units_push`、`test_bleeding_wake_does_not_apply_to_other_units_movement` |
| **同時生效的規則改變最多 1 個** | `test_two_different_rule_affixes_fail_the_loadout_check`、`test_setup_rejects_two_rule_affixes`、`test_the_same_rule_affix_on_two_items_counts_once`、`test_a_gear_rule_blocks_activating_a_legendary_rule_change` |
| 預覽與 AI 反映規則改變 | `test_fire_mends_preview_shows_the_heal_only_for_the_holder`（持有者預覽顯示治療、無裝備為傷害）、`test_fire_mends_ai_scores_the_ally_hit_as_a_heal_not_friendly_fire` |
| 序列化 | `test_granted_things_survive_serialization` |
| 一場 `--log-json` ＋ `replay` | `test_g3b_gear_battle_log_json_and_replay`；手動見下 |
| 前端 | `client/src/battle/gearSkills.test.ts` |

手動 `--log-json` ＋ `replay`：

```
uv run trpg battle --map test_flat_6x6 --allies gear_tester_g3b,gear_tester_g3b_sentinel --enemies bandit,bandit --seed 3 --log-json g3b.json
uv run trpg battle replay g3b.json
重播驗證通過：46 個動作、140 個事件，最終狀態一致（test_flat_6x6，種子 3）。
（種子 5：49 個動作、153 個事件，也一致；種子 3 內 attack_intercepted 2 次、種子 5 內 4 次——替隊友承受在實戰出現）
```

截圖（`docs/phases/img/`；本機 8123 埠的伺服器，已關閉，沒有碰 8000 埠）：`3G-3b-skill-bar.png`（技能列：鉤爪、盾牆、煙霧彈標示「來自裝備・欄位：物品」）、`3G-3b-reaction-settings.png`（反應設定：格擋與替隊友承受標示來自哪件裝備與詞條）。截圖時為了看到第三排技能，用瀏覽器開發工具暫時把底部面板調高（沒有改原始碼，見待 PM 決定 #7）。

## 新增的複雜度 noqa

**沒有。**

## 種子變動

**沒有換任何釘種子的測試**（授予的技能與反應只在裝備詞條存在時出現，既有單位不穿裝備，行為不變）。

## 待 PM 決定

1. **授予的技能的 category**：`category: weapon` 只允許 `melee`／`ranged`，所以三個裝備技寫成 `category: spell`、`weapon_req: any`、法力 0（法術技的 `hit_by_spell` 反應與法術反射會作用在它們上；目前三個技能不打傷害，影響很小）。若要改成不受武器種類限制的新類別，需改 schema。
2. **煙霧彈（裝備）**的中文名加了「（裝備）」以和 `skill_smoke_bomb` 區分。
3. **`extend_trigger` 的實作**是加一條規則：持有者沒有原本的 `block` 規則時也會加（等於授予遠程格擋）；模式沿用原規則。
4. **替隊友承受**：距離用曼哈頓距離 ≤ `range`（2），不檢查視線；排在「守護動作」與「攔截反應技」之後；佔本輪一般反應次數；每輪 1 次是詞條本身的限制。被攻擊者是持有者自己時不觸發。守護者承受時，攻擊附帶的位移與武器特性（例如震退）也作用在守護者身上（同既有的攔截）。
5. **監視射擊額外次數**：額外次數與一般反應次數分開記；一般次數已被別的反應用掉時，這輪只剩額外的 1 次；`reactions_per_round` 若改大，狀態在額外次數用完前不會移除。
6. **改變規則「同時最多 1 個」**：穿戴驗證（不同詞條 id 超過 1 個失敗，`caps.rule_affixes`）；同詞條掛兩件算 1。裝備規則一律生效、不需啟動，所以持有者無法再啟動型傳說的規則改變。測試物品的傳說項鍊只是測試用，沒有掉落。
7. **技能列高度**：底部面板高度固定（約 166px），主角再加 3 個裝備技能時技能列會超出（既有行為，非本段新增）；是否要讓技能列可捲動或自動長高，請 PM／美術 PM 決定。
8. **血痕的文字**：規則資料沿用既有的「步行經過時對相鄰敵人施加流血」，與設計文字「留下流血表面」不完全相同（沒有表面）。
9. **AI 對授予技能的評分**：鉤爪、煙霧彈沒有傷害時分數為負（與既有的 `skill_smoke_bomb` 同），只有在能達成目標（例如拉進岩漿擊殺）時才會被選；平衡階段再調權重。
10. **`gear_source_zh`／`gear_skills` 只在己方單位列出**；反應設定的來源文字用「物品名：詞條文字」，同一反應多條規則共用同一段文字。

## 最終檢查

`uv run python scripts/check.py`：ruff check／format、mypy、lint-imports、pytest、client typecheck、client test **全部通過**（第一次全量有 12 個失敗：新技能的預算「過弱」檢查、技能總數 163→166 與 CLI 輸出快照、圖示 fixture；已處理——`skillgen/validate.py` 對標籤 `gear` 的技能不套「過弱」下限、更新數量與快照、校準測試排除 `skill_gear_*`，第二次全量全過）。
`corepack pnpm -C client build`：成功（只有既有的 chunk 大於 500 kB 警告）。

另列待 PM 決定 #11：裝備授予的技能預算算在詞條上，所以驗證器對標籤 `gear` 的技能不套「過弱」下限、階級預算校準也排除它們。
