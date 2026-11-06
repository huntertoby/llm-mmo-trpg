# Phase 3-24a1 報告：武器擴充第一批（斧、錘、矛、權杖、圖騰杖＋弓拋射）

規格：`docs/phases/Phase3計畫.md` 25.1。分支 `worktree-agent-a41126876d9190497`（從 main 的 26c2226 分出），未 push、未合併。

## 武器資料新增的參數欄位（`content/weapons.yaml`／`WeaponDef`）

全部選填、預設為「無特性」，引擎只讀參數、不寫死數值（`src/trpg/engine/weapon_traits.py`）。

| 欄位 | 預設 | 用在 | 讀取處 |
|---|---|---|---|
| `secondary_scaling_attr` | 無 | 錘（力量／體質取平均、無條件捨去） | `rules/statuses.weapon_attribute` |
| `armor_break {defense_permille, rounds}` | 無 | 斧：−100‰、1 回合 | `weapon_traits.apply_hit_traits` → 狀態 `armor_broken` |
| `knockback` | 0 | 錘：1 | 同上，`PushEffect`（沿用推擊與撞擊） |
| `reach` | 1 | 矛：2（≤ range） | `reactions.opportunity_attacks` |
| `blessing {flat, dice}` | 無 | 權杖：flat 3 | `apply_hit_traits`，`HealEffect` |
| `summon_dice_bonus` | 0 | 圖騰杖：1 | `weapon_traits.attack_dice`（普攻與物件攻擊） |
| `lob` | 0 | 弓：1 | `geometry.has_line_of_sight(lob=)`；普攻、武器技、AI 掃描 |

另新增：狀態 `armor_broken`（`StatusDef.defense_break`，數值存在 `StatusInstance.amount`，無 budget_points）、AI 權重 `reach_spacing`、`knock_angle`（`AiWeights`，brute 與 flanker 設值）。`WeaponDef.is_melee` 改為看大類（矛射程 2 仍是近戰：背刺、倒地優勢等）。API 只新增 `weapon_traits_zh`（UnitView、RunHero、BuildSummary）。

新武器：斧（單手、力量 1d8）、錘（雙手、力量／體質 1d12）、矛（雙手、力量 1d10、射程 2）、權杖（單手、感知 1d6、射程 4）、圖騰杖（雙手、意志 1d6、射程 4）。白板主角：`build_blank_axe／hammer／spear／priest／totemist`（不改既有 22 個 build）。

## LOG_FORMAT

**未遞增**（仍 `trpg-battle-log/37`）：沒有新事件，只新增有預設值的武器欄位；破甲、震退、祝禱沿用既有事件。

## 逐條驗收

| 規格 | 證據 |
|---|---|
| 1 斧破甲 −10% 1 回合 | `tests/engine/test_weapons_24a1.py`：`test_axe_hit_applies_armor_broken_and_lowers_defense_by_10_percent`、`..._miss_applies_nothing`、`test_changing_the_armor_break_parameters_changes_the_behavior`（改成 −300／2 回合行為跟著變）、`test_armor_break_takes_the_largest_value...` |
| 2 錘震退（撞擊） | `test_hammer_hit_pushes_...`、`..._miss_does_not_push`、`..._into_a_wall_collides_...`、`..._into_another_unit_hurts_both`、`test_changing_knockback_changes_the_push_distance`、`test_hammer_attack_value_averages_strength_and_constitution` |
| 3 矛 2 格與 2 格藉機攻擊 | `test_spear_attacks_a_target_two_tiles_away_but_not_three`、`test_spear_gets_an_opportunity_attack_when_a_target_leaves_its_two_tile_reach`、`..._does_not_react_while_the_target_stays_inside_the_reach`、`test_sword_has_no_opportunity_attack_at_two_tiles`、`test_changing_reach_changes_the_opportunity_range` |
| 4 權杖祝禱 | `test_scepter_hit_heals_the_nearest_ally_by_the_data_amount`、`..._miss_does_not_heal`、`test_changing_blessing_...`、`test_blessing_ignores_summons_and_downed_allies_and_needs_one`、`test_scepter_range_is_four` |
| 5 圖騰杖統御 | `test_summon_attack_gets_the_owners_extra_damage_die`、`..._rolls_the_extra_die`、`test_changing_summon_dice_bonus_...`、`test_totem_staff_scales_with_will_and_has_range_four` |
| 6 弓拋射（越過與不越過） | `test_bow_lobs_over_a_one_high_object...`、`test_bow_lobs_over_a_one_high_ridge_but_not_a_two_high_one`（lob 2 可越過）、`test_a_lob_cannot_pass_a_real_wall_or_darkness`、`test_a_two_high_object_stack_...`、`test_lob_keeps_the_half_cover_penalty`（cover −2）、`test_lob_applies_to_weapon_skills_and_the_ai_scan` |
| 7 AI 與預覽 | `test_ai_spearman_stops_at_two_tiles_instead_of_closing_in`、`test_reach_spacing_weight_is_data_driven`、`test_ai_hammer_prefers_the_angle_that_makes_the_knockback_collide`、`test_preview_lists_the_on_hit_traits_and_the_forced_push`、`test_preview_damage_includes_the_summon_extra_die` |
| 8 前端 | vitest `paperdoll.test.ts`（新武器造型、形制進快取鍵）；截圖見下 |
| `--log-json` ＋ `replay` | `tests/cli/test_weapons_24a1_cli.py`（5 個白板主角打整場，特性在整場中發動，重播一致；另 4 個在 ruined_fort 重播） |
| 資料驗證 | `test_new_weapons_are_data_with_the_specified_parameters`、`test_weapon_schema_rejects_inconsistent_parameters`、`test_trait_text_follows_the_parameters`、`test_content_has_a_blank_hero_for_each_new_weapon` |
| `check.py`、`pnpm build` | 見文末「最終檢查」 |

截圖（`docs/phases/img/`）：`3-24a1-weapon-icons.png`（斧、錘、矛、權杖、圖騰杖圖示；圖騰杖依美術規格：兩張刻臉＋羽毛＋頂端綠珠）、`3-24a1-new-run-spear.png`、`3-24a1-run-hero-panel-spear.png`、`3-24a1-run-hero-panel-totemist.png`（英雄面板特性一行）、`3-24a1-battle-spear-unit-info.png`（單位資訊特性列）、`3-24a1-battle-spear-attack-at-two.png`（矛 2 格出手）、`3-24a1-battle-hammer-kill-bow-trait.png`（錘擊倒；敵方弓手特性「拋射」）。

## AI 軌跡改變而換種子（弓有拋射，弓手能越過 1 格高障礙，AI 行為隨之改變）

- `test_charge_ai`（兩個測試）bridge_chasm：種子 2 → 1
- `test_facing_backstab::test_ai_battle_with_backstabs_replays` dark_forest：3 → 0
- `test_hurl_object::test_an_ai_battle_hurls_objects_and_replays` narrow_halls：5 → 11
- `test_basic_actions_cli::test_open_plain_battle_uses_guard_swap_and_aim_and_replays` open_plain：3 → 98
- `test_reaction_events_3d3`（build_ranged／open_plain／掩護射擊）：1 → 3
- `test_rewrites_4b`（build_guardian／open_plain，兩個參數）：2 → 0
- `test_summon_ai`（兩處）dark_forest：10 → 0
- `test_ai_utility::_crossroads`：場景弓手改用 `lob: 0` 的弓（否則會越過高台射遠處敵人，場景意圖不同）
- `test_pierce::test_a_stone_pillar_still_blocks_the_shot`：同上，改用 `lob: 0` 的弓（石柱是 1 格高物件，弓現在能越過）
- `tests/cli/snapshots/cli_output_hashes.json`：以 `UPDATE_CLI_SNAPSHOTS=1` 重錄（4 個雜湊）
- `tests/content/test_coverage.py`、`tests/skillgen/test_budget.py`：`armor_broken` 列入允許清單／預期表
- `client/src/render/fixtures/skill_icons.json`：重產（新增狀態改變隨機技能的條件抽選）。**合併時若 3-23 也改了技能產生器，需重跑 `uv run python -m tests.narrative.icon_fixture`**
- `client/src/render/skillParts.ts`：新增 `armor_broken` 狀態圖示（vitest 要求每個狀態有圖示）

## 新增的複雜度 noqa

無。

## 待 PM 決定

1. 拋射與單位：引擎目前單位本就不擋視線，所以「越過單位」無差別；是否要讓單位擋視線（會動到所有武器）？
2. 拋射只對「物件（視為 1 層高）與地形高差」生效，牆壁地形與黑暗表面不可越過；有拋射時視線不再對稱（只看射擊方向）。
3. 弓拋射也套用到武器技（category weapon）；法術技不套用。
4. 祝禱對象為最近隊友（不含自己與召喚物，同距離取 ID 小者），不管是否滿血；回復量 flat 3（初值）。要不要改成「最近的受傷隊友」？
5. 權杖、圖騰杖傷害元素為物理（規格未指定；權杖是否改為聖光？）。
6. 傷害骰、數值為初值未經模擬：錘 1d12、矛 1d10、斧 1d8、權杖與圖騰杖 1d6（射程 4）；請模擬後定案。
7. 矛兵緊貼敵人再離開（相鄰 → 距離 2）不觸發藉機攻擊（仍在 2 格內）；反應技 `enemy_leaves_adjacent` 仍只看相鄰。
8. 破甲：多個來源取最大、不疊加；`rounds: 1` 為目標回合結束時移除；防禦值最低 1。
9. AI 權重 `reach_spacing: 7`、`knock_angle: 2` 為初值，只加在 brute 與 flanker。
10. 錘擊倒時推擊的撞擊傷害歸給攻擊者；圓盾延到裝備段（規格已說明）。

## 最終檢查

- `scripts/check.py`：ruff、ruff format --check、mypy、lint-imports 全過；其中的平行全量 pytest 在本機卡在 96%（多個 xdist 工作程序長時間無進度，疑為機器同時有其他 agent 在跑、與程式碼無關），已中止。改以分段方式涵蓋全部測試目錄、全數通過：第一次全量跑 14 個失敗（皆為上節列出的 AI 軌跡／清單項目）修正後，`tests/engine tests/content tests/skillgen tests/narrative tests/api tests/test_architecture.py`（3107 passed）、`tests/cli`（100 passed ＋ 快照 1 passed）、`tests/roguelite tests/shared tests/sim` 與被修改的 AI 戰鬥測試（396 passed）、`tests/api tests/content tests/test_play_script.py tests/test_sim_scripts.py`（704 passed）。**建議 PM 合併後在乾淨環境重跑一次完整 `check.py`。**
- `corepack pnpm -C client build` 成功；`corepack pnpm -C client test`：540 passed。
