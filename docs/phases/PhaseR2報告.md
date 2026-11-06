# Phase R2 報告：階段代號命名的測試檔按主題改名／合併

依據：`docs/phases/整理提案-程式.md` 2.2 節 R2（使用者已同意照提案做）。分支 `dev/r2`。

## 結果摘要

| 項目 | pytest | vitest |
|---|---|---|
| 處理的舊檔 | 116 | 76 |
| 新檔 | 83 | 51 |
| 合併組數 | 21 組（54 個舊檔） | 19 組（44 個舊檔） |
| 純改名 | 62 | 32 |
| 測試數（改前 → 改後） | 14298／15290（992 deselected）→ 14298／15290（992 deselected） | 3094 → 3094 |
| 測試檔數（改前 → 改後） | 727 → 694 | 271 → 246 |
| 合併後最大單檔 | 832 行（`tests/skillgen/test_whiteboard.py`） | 812 行（`client/src/ui/badgeCapsule.test.ts`） |

各目錄測試數前後（`pytest --collect-only`）：api 791→791、content 2718→2718、narrative 347→347、roguelite 229→229、world 1079→1079、cli 143→143、engine 4222→4222、skillgen 3977→3977。

驗收：各批 `pytest -q tests/<目錄> -x -n 4` 全過；`ruff check`、`ruff format --check`、`mypy`（1357 檔）、`lint-imports`（14 條契約）、`pnpm -C client typecheck`、全量 vitest（246 檔 3094 個）全過。pytest 全量沒跑（PM 合併後跑）。

## 做法

- **只搬檔與合併**：`git mv` 保留歷史；斷言、測試邏輯、`src/` 都沒改。
- **pytest 合併**：模組 docstring 併成「主題合併（R2）＋各原檔 docstring」；import 去重後由 ruff 排序；每段前加 `# --- 原 xxx.py ---`。後面檔案與前面同名的頂層名稱（helper、常數、fixture、測試函式）**改名不合併**：底線開頭的加前綴（`_ok` → `_6f4_ok`），大寫常數加後綴（`LIB` → `LIB_48F`），fixture／測試函式加代號（`client` → `client_6f4`、`test_new_recipes_have_a_witness` → `test_6f4f_new_recipes_have_a_witness`）；同一合併組裡代號重複時改用完整原檔名（`LIB_WORKSHOP_RUNE_HINT_48F`）。合併組內原本互相 import 的那行拿掉。
- 兩處同一物件從兩個模組各 import 一次（`RunState`、`SkillRarity`、`whiteboard_problems`，已確認 `is` 相同），合併後只留一行 import（ruff F811）。
- **vitest 合併**：第一個檔照原樣放在模組層，後面的檔整個包進 `describe("原 xxx.test.ts", () => { … })`，所以各檔自己的 helper、`beforeAll`／`afterAll`、`vi.spyOn` 只作用在自己的測試，不需改名；內容不縮排（避免動到多行字串）。import 依模組合併；同名但來自不同模組的 import 加別名，在包裝區塊裡用 `const X = X__原檔;`／`type X = X__原檔;` 遮蔽（`Rect`、`ROW_EDGE` 等 6 處）。有頂層 `await` 或 `vi.mock` 的檔只放在合併組的第一個（`mail6t1d` 排在 `mail6t1b` 前；`hazard6v2`／`hazard6v2b` 的 `vi.mock` 內容不同，分成兩檔）。
- 合併後的 vitest 測試全名多一層「原 xxx.test.ts」；pytest 的節點 ID 跟著檔名變。
- `xdist_group` 的 7 個檔都不在這次範圍，沒動。`__snapshots__/*.snap` 兩個檔對應的測試沒改名，不必搬。fixture 檔（`fixtures/*_3wr1.json`、`*_3wr2.json`）檔名沒改。
- **引用同步**：其他測試 `from tests.<dir>.<舊檔> import …` 全部改成新路徑（含 `test_bal8_options.py` 等 bal 檔、`tests/api/test_new_reactions_api.py`）；註解與 docstring 裡寫到舊檔名的（`scripts/budget_knob_audit.py`、`test_flash_major.py`、`test_whiteboard_bal19f.py`、`test_proposal_l10b.py`、`test_world_loot_api.py`、`test_form_start.py`、client 4 個檔）改成新檔名。`docs/開發PM交接.md`、`CLAUDE.md` 沒有引用。`docs/archive/` 與已結案報告沒改。

## 保留原名的檔與原因

| 檔 | 原因 |
|---|---|
| `tests/engine/test_polish_3c6a.py` | 3C-6a 累積小修的雜項（穿透紀錄、推擊、奪取增益、AI 超載、CLI…），沒有單一主題 |
| `client/src/battle/polish3c5c2.test.ts`、`battle/polish3c6a.test.ts`、`battle/uiT1.test.ts` | 試玩小修雜項，同上 |
| `client/src/render/art5.test.ts` | 戰場最小大小、矮異形狀態列、道童杖頭光三件不相干的事 |
| pytest 的 `bal*`、`l*`（L5c／L8／L10）、`e1`／`e2a`／`e2b`、`f2`、`g2`／`g3a`／`g3b`、`perf2`／`perf3`、`phase1c`、`uie3b` 共 56 檔 | 提案的 109 個只算「數字開頭」的階段代號；這批是平衡段／LLM 段等的代號，而且多數檔名前半已是主題（例 `test_flash_bal10b.py`）。沒列在本段規格內，待 PM 決定要不要下一段處理 |

## 改名對照表（舊 → 新）

### pytest

| 舊 | 新 |
|---|---|
| `tests/api/test_first10_text_6f1.py` | `tests/api/test_newcomer_api.py` |
| `tests/api/test_newcomer_api_6f2.py` | `tests/api/test_newcomer_api.py` |
| `tests/api/test_newcomer_api_6f4.py` | `tests/api/test_newcomer_api.py` |
| `tests/api/test_opening_rt5.py` | `tests/api/test_capital_opening_api.py` |
| `tests/api/test_skill_card_stats_6a1.py` | `tests/api/test_skill_card_stats.py` |
| `tests/api/test_workshop_earth_54d.py` | `tests/api/test_workshop_element_api.py` |
| `tests/api/test_world_dev_boss_6f3.py` | `tests/api/test_world_dev_boss.py` |
| `tests/api/test_world_field_r3.py` | `tests/api/test_world_field_terrain_cache.py` |
| `tests/api/test_world_pregen_6l2b.py` | `tests/api/test_world_pregen_schedule.py` |
| `tests/api/test_world_pregen_6l2c.py` | `tests/api/test_world_pregen_schedule.py` |
| `tests/api/test_world_store_r3.py` | `tests/api/test_world_store_cache.py` |
| `tests/content/test_field_look_6v2b.py` | `tests/content/test_field_look.py` |
| `tests/content/test_field_decor_6v4b.py` | `tests/content/test_field_look.py` |
| `tests/content/test_newcomer_content_6f2.py` | `tests/content/test_newcomer_content.py` |
| `tests/content/test_newcomer_guide_name_rt5c.py` | `tests/content/test_newcomer_content.py` |
| `tests/content/test_rule_lists_3wr2.py` | `tests/content/test_rule_lists.py` |
| `tests/content/test_world_5b4b.py` | `tests/content/test_world_town_quests.py` |
| `tests/content/test_world_5b4c.py` | `tests/content/test_world_cloud_ridge.py` |
| `tests/engine/test_24c.py` | `tests/engine/test_collided_sacrifice_firearm.py` |
| `tests/engine/test_ai_shield_break_6f3.py` | `tests/engine/test_ai_shield_break.py` |
| `tests/engine/test_ai_weights_3e.py` | `tests/engine/test_ai_weights.py` |
| `tests/engine/test_arcane_blade_3i3.py` | `tests/engine/test_arcane_blade.py` |
| `tests/engine/test_wind_54a.py` | `tests/engine/test_wind.py` |
| `tests/engine/test_blow_deadly_54b.py` | `tests/engine/test_wind.py` |
| `tests/engine/test_wind_spread_54b.py` | `tests/engine/test_wind.py` |
| `tests/engine/test_boss_triggers_5f3.py` | `tests/engine/test_boss_triggers.py` |
| `tests/engine/test_complete_strength_3w5b.py` | `tests/engine/test_complete_skill_strength.py` |
| `tests/engine/test_earth_54b.py` | `tests/engine/test_earth.py` |
| `tests/engine/test_earth_54e.py` | `tests/engine/test_earth.py` |
| `tests/engine/test_earth_54d.py` | `tests/engine/test_earth_element.py` |
| `tests/engine/test_form_identity_3j3.py` | `tests/engine/test_form_identity.py` |
| `tests/engine/test_form_release_3j4c.py` | `tests/engine/test_form_release.py` |
| `tests/engine/test_forms_3j1b.py` | `tests/engine/test_form_traits.py` |
| `tests/engine/test_forms_3j4.py` | `tests/engine/test_form_pools.py` |
| `tests/engine/test_mechanics_5am1.py` | `tests/engine/test_cloud_ridge_mechanics.py` |
| `tests/engine/test_mechanics_5am2.py` | `tests/engine/test_cloud_ridge_mechanics.py` |
| `tests/engine/test_mechanics_5am2b.py` | `tests/engine/test_cloud_ridge_mechanics.py` |
| `tests/engine/test_offhands_3i2.py` | `tests/engine/test_offhands.py` |
| `tests/engine/test_reaction_events_3d3.py` | `tests/engine/test_reaction_events.py` |
| `tests/engine/test_rewrites_4b.py` | `tests/engine/test_rewrite_primitives.py` |
| `tests/engine/test_ring_shape_6f3.py` | `tests/engine/test_ring_shape.py` |
| `tests/engine/test_rune_snare_48f.py` | `tests/engine/test_rune_skills.py` |
| `tests/engine/test_rune_ward_48h.py` | `tests/engine/test_rune_skills.py` |
| `tests/engine/test_seeds_54c.py` | `tests/engine/test_element_seeds.py` |
| `tests/engine/test_stack_auto_consume_52b.py` | `tests/engine/test_stack_auto_consume.py` |
| `tests/engine/test_stance_upkeep_3w2b.py` | `tests/engine/test_stance_upkeep.py` |
| `tests/engine/test_weapon_affinity_3i5.py` | `tests/engine/test_weapon_affinity.py` |
| `tests/engine/test_weapon_element_3k1.py` | `tests/engine/test_weapon_element.py` |
| `tests/engine/test_weapons_24a1.py` | `tests/engine/test_weapon_traits.py` |
| `tests/engine/test_weapons_24a2.py` | `tests/engine/test_weapons_ranged.py` |
| `tests/engine/test_weapons_24a2_reactions.py` | `tests/engine/test_weapons_ranged.py` |
| `tests/engine/test_weapons_3i1.py` | `tests/engine/test_weapons_gauntlet_scythe_whip.py` |
| `tests/engine/test_weapons_3i4.py` | `tests/engine/test_weapons_dual_dagger_firearm.py` |
| `tests/cli/test_weapons_24a1_cli.py` | `tests/cli/test_weapon_traits_cli.py` |
| `tests/cli/test_weapons_24a2_cli.py` | `tests/cli/test_weapons_ranged_cli.py` |
| `tests/narrative/test_card_attributes_55.py` | `tests/narrative/test_card_attributes.py` |
| `tests/narrative/test_keyword_hints_51.py` | `tests/narrative/test_keyword_hints.py` |
| `tests/narrative/test_rule_texts_41a.py` | `tests/narrative/test_rule_texts.py` |
| `tests/narrative/test_rule_texts_41c.py` | `tests/narrative/test_rule_texts.py` |
| `tests/narrative/test_wind_events_54a.py` | `tests/narrative/test_wind_events_text.py` |
| `tests/roguelite/test_form_start_3j4b.py` | `tests/roguelite/test_form_start.py` |
| `tests/roguelite/test_retier_3w9.py` | `tests/roguelite/test_retier.py` |
| `tests/roguelite/test_truth_3wr1.py` | `tests/roguelite/test_retier.py` |
| `tests/skillgen/test_affinity_3i5.py` | `tests/skillgen/test_weapon_affinity.py` |
| `tests/skillgen/test_complete_3w5b.py` | `tests/skillgen/test_complete_skill.py` |
| `tests/skillgen/test_composer_3c6b.py` | `tests/skillgen/test_composer_new_options.py` |
| `tests/skillgen/test_composer_24c.py` | `tests/skillgen/test_composer_new_options.py` |
| `tests/skillgen/test_composer_traits_3t8.py` | `tests/skillgen/test_composer_new_options.py` |
| `tests/skillgen/test_condition_any_of_3w2b.py` | `tests/skillgen/test_condition_any_of.py` |
| `tests/skillgen/test_dual_3i3.py` | `tests/skillgen/test_arcane_blade.py` |
| `tests/skillgen/test_exploit_6f4b.py` | `tests/skillgen/test_exploit_starter_links.py` |
| `tests/skillgen/test_exploit_6f4c.py` | `tests/skillgen/test_exploit_starter_links.py` |
| `tests/skillgen/test_exploit_6f4d.py` | `tests/skillgen/test_exploit_starter_links.py` |
| `tests/skillgen/test_exploit_6f4e.py` | `tests/skillgen/test_exploit_starter_links.py` |
| `tests/skillgen/test_exploit_6f4f.py` | `tests/skillgen/test_exploit_starter_links.py` |
| `tests/skillgen/test_exploit_6f4g.py` | `tests/skillgen/test_exploit_starter_links.py` |
| `tests/skillgen/test_topup_6s2.py` | `tests/skillgen/test_upgrade_topup.py` |
| `tests/skillgen/test_topup_6s2c.py` | `tests/skillgen/test_upgrade_topup.py` |
| `tests/skillgen/test_fallback_6s2b.py` | `tests/skillgen/test_upgrade_topup.py` |
| `tests/skillgen/test_flash_fill_3w2b.py` | `tests/skillgen/test_flash_fill.py` |
| `tests/skillgen/test_flash_shield_3w2b.py` | `tests/skillgen/test_flash_shield.py` |
| `tests/skillgen/test_flash_stance_3w2b.py` | `tests/skillgen/test_flash_stance.py` |
| `tests/skillgen/test_flash_terrain_3w2b.py` | `tests/skillgen/test_flash_terrain.py` |
| `tests/skillgen/test_whiteboard_3w4.py` | `tests/skillgen/test_whiteboard.py` |
| `tests/skillgen/test_whiteboard_3w4b.py` | `tests/skillgen/test_whiteboard.py` |
| `tests/skillgen/test_whiteboard_3w2b.py` | `tests/skillgen/test_whiteboard.py` |
| `tests/skillgen/test_keywords_rune_48e.py` | `tests/skillgen/test_keywords_rune.py` |
| `tests/skillgen/test_passive_fallback_6f1.py` | `tests/skillgen/test_passive_fallback.py` |
| `tests/skillgen/test_pools_24c.py` | `tests/skillgen/test_keyword_pools.py` |
| `tests/skillgen/test_pools_27.py` | `tests/skillgen/test_keyword_pools.py` |
| `tests/skillgen/test_proposal_54d.py` | `tests/skillgen/test_proposal_element.py` |
| `tests/skillgen/test_wind_54a.py` | `tests/skillgen/test_wind.py` |
| `tests/skillgen/test_refactor_3wr2.py` | `tests/skillgen/test_refactor_parity.py` |
| `tests/skillgen/test_skill_tier_3w9.py` | `tests/skillgen/test_skill_tier.py` |
| `tests/skillgen/test_retier_growth_3w9b.py` | `tests/skillgen/test_skill_tier.py` |
| `tests/skillgen/test_stack_expansion_52.py` | `tests/skillgen/test_stack_expansion.py` |
| `tests/skillgen/test_stack_workshop_52b.py` | `tests/skillgen/test_stack_expansion.py` |
| `tests/skillgen/test_witness_6ew.py` | `tests/skillgen/test_proposal_witness.py` |
| `tests/skillgen/test_workshop_3h8.py` | `tests/skillgen/test_workshop_menus.py` |
| `tests/skillgen/test_workshop_48c.py` | `tests/skillgen/test_workshop_feedback.py` |
| `tests/skillgen/test_workshop_48f.py` | `tests/skillgen/test_workshop_feedback.py` |
| `tests/skillgen/test_workshop_rune_hint_48f.py` | `tests/skillgen/test_workshop_feedback.py` |
| `tests/skillgen/test_workshop_text_48f.py` | `tests/skillgen/test_workshop_feedback.py` |
| `tests/skillgen/test_workshop_48d.py` | `tests/skillgen/test_workshop_nested.py` |
| `tests/skillgen/test_workshop_48h_schema.py` | `tests/skillgen/test_workshop_schema_errors.py` |
| `tests/skillgen/test_workshop_48h_rules.py` | `tests/skillgen/test_workshop_option_rules.py` |
| `tests/world/test_capital_figures_6v1.py` | `tests/world/test_capital_figures.py` |
| `tests/world/test_capital_figures_6v3.py` | `tests/world/test_capital_figures.py` |
| `tests/world/test_cleared_for_6f3.py` | `tests/world/test_cleared_for.py` |
| `tests/world/test_cross_class_6t1b.py` | `tests/world/test_cross_class.py` |
| `tests/world/test_field_6c5b.py` | `tests/world/test_field_campfire.py` |
| `tests/world/test_field_enemies_6c1b.py` | `tests/world/test_field_enemy_rules.py` |
| `tests/world/test_first_flash_6f2.py` | `tests/world/test_first_flash.py` |
| `tests/world/test_generated_6l2.py` | `tests/world/test_generated_content.py` |
| `tests/world/test_newcomer_6f2.py` | `tests/world/test_newcomer.py` |
| `tests/world/test_newcomer_6f4.py` | `tests/world/test_newcomer.py` |

### vitest

| 舊 | 新 |
|---|---|
| `client/src/audio/au3.test.ts` | `client/src/audio/battleSfx.test.ts` |
| `client/src/battle/cleanup6rf.test.ts` | `client/src/battle/variantSelection.test.ts` |
| `client/src/battle/viewGrip6rf.test.ts` | `client/src/battle/variantSelection.test.ts` |
| `client/src/battle/fix6f6.test.ts` | `client/src/battle/floatTextTiming.test.ts` |
| `client/src/battle/impact6h1.test.ts` | `client/src/battle/impactFeel.test.ts` |
| `client/src/battle/impact6h1b.test.ts` | `client/src/battle/impactFeel.test.ts` |
| `client/src/battle/tileCard318b.test.ts` | `client/src/battle/tileCard.test.ts` |
| `client/src/battle/vfx318b.test.ts` | `client/src/battle/skillVfx.test.ts` |
| `client/src/battle/vfx354a.test.ts` | `client/src/battle/skillVfx.test.ts` |
| `client/src/render/ambient6n10.test.ts` | `client/src/render/ambientMotion.test.ts` |
| `client/src/render/appearance318b.test.ts` | `client/src/render/appearanceFallback.test.ts` |
| `client/src/render/hazard6v2.test.ts` | `client/src/render/hazardTiles.test.ts` |
| `client/src/render/hazard6v2b.test.ts` | `client/src/render/hazardTileEdges.test.ts` |
| `client/src/render/lanternGlow6q1.test.ts` | `client/src/render/lanternGlow.test.ts` |
| `client/src/render/npcWorkSide6q1.test.ts` | `client/src/render/npcWorkFacing.test.ts` |
| `client/src/render/reducedMotion6rf.test.ts` | `client/src/render/reducedMotion.test.ts` |
| `client/src/render/regionArt4.test.ts` | `client/src/render/regionReskins.test.ts` |
| `client/src/render/regionArt7.test.ts` | `client/src/render/regionReskins.test.ts` |
| `client/src/render/scene6v3.test.ts` | `client/src/render/sceneDecor.test.ts` |
| `client/src/render/texHold6rf.test.ts` | `client/src/render/textureHold.test.ts` |
| `client/src/render/uiE4.test.ts` | `client/src/render/exitSigns.test.ts` |
| `client/src/render/weaponIcon3t4c.test.ts` | `client/src/render/shortWeaponIcon.test.ts` |
| `client/src/render/weapons24a2.test.ts` | `client/src/render/weaponLooks.test.ts` |
| `client/src/render/weapons3i1.test.ts` | `client/src/render/weaponLooks.test.ts` |
| `client/src/render/weapons3i4.test.ts` | `client/src/render/weaponLooks.test.ts` |
| `client/src/run/lookOptions6r2.test.ts` | `client/src/run/lookOptions.test.ts` |
| `client/src/ui/battleHud6a4e.test.ts` | `client/src/ui/battleHud.test.ts` |
| `client/src/ui/logRoom6a4c.test.ts` | `client/src/ui/battleLogRoom.test.ts` |
| `client/src/ui/motionPrefs6h1.test.ts` | `client/src/ui/motionPrefs.test.ts` |
| `client/src/ui/rt3b.test.ts` | `client/src/ui/eventCardScroll.test.ts` |
| `client/src/ui/skillBar6f6.test.ts` | `client/src/ui/skillBarWidth.test.ts` |
| `client/src/ui/skillCard6a1.test.ts` | `client/src/ui/skillCard.test.ts` |
| `client/src/ui/statusCard6a2.test.ts` | `client/src/ui/statusCard.test.ts` |
| `client/src/ui/textless6a3.test.ts` | `client/src/ui/textlessHints.test.ts` |
| `client/src/ui/uiE1.test.ts` | `client/src/ui/entryScreen.test.ts` |
| `client/src/ui/uiE1b.test.ts` | `client/src/ui/entryScreen.test.ts` |
| `client/src/ui/uiE2.test.ts` | `client/src/ui/sharedPopup.test.ts` |
| `client/src/ui/uiE3c.test.ts` | `client/src/ui/floatCardLayout.test.ts` |
| `client/src/ui/fix6f10.test.ts` | `client/src/ui/summonBadges.test.ts` |
| `client/src/ui/fix6f10b.test.ts` | `client/src/ui/summonBadges.test.ts` |
| `client/src/ui/fix6f11.test.ts` | `client/src/ui/summonBadges.test.ts` |
| `client/src/ui/fix6f12.test.ts` | `client/src/ui/statusBadges.test.ts` |
| `client/src/ui/fix6f13.test.ts` | `client/src/ui/statusBadges.test.ts` |
| `client/src/ui/fix6f14.test.ts` | `client/src/ui/badgeFacing.test.ts` |
| `client/src/ui/fix6f15.test.ts` | `client/src/ui/badgeFacing.test.ts` |
| `client/src/ui/fix6f16.test.ts` | `client/src/ui/badgeFacing.test.ts` |
| `client/src/ui/fix6f18.test.ts` | `client/src/ui/badgeCapsule.test.ts` |
| `client/src/ui/fix6f19.test.ts` | `client/src/ui/badgeCapsule.test.ts` |
| `client/src/ui/fix6f20.test.ts` | `client/src/ui/badgeCapsule.test.ts` |
| `client/src/ui/fix6f7.test.ts` | `client/src/ui/narrowSkillLayout.test.ts` |
| `client/src/ui/rt3b6f7.test.ts` | `client/src/ui/narrowSkillLayout.test.ts` |
| `client/src/ui/fix6f8.test.ts` | `client/src/ui/narrowMapLayout.test.ts` |
| `client/src/ui/fix6f9.test.ts` | `client/src/ui/narrowMapLayout.test.ts` |
| `client/src/workshop/options3h8.test.ts` | `client/src/workshop/playerOptions.test.ts` |
| `client/src/workshop/player48c.test.ts` | `client/src/workshop/playerOptions.test.ts` |
| `client/src/workshop/display48f.test.ts` | `client/src/workshop/playerOptions.test.ts` |
| `client/src/workshop/stackGroups52.test.ts` | `client/src/workshop/playerOptions.test.ts` |
| `client/src/workshop/nested48d.test.ts` | `client/src/workshop/nestedEffects.test.ts` |
| `client/src/workshop/effectRules48h.test.ts` | `client/src/workshop/effectRules.test.ts` |
| `client/src/world/decor6v4b.test.ts` | `client/src/world/capitalDecor.test.ts` |
| `client/src/world/plaza6v4.test.ts` | `client/src/world/capitalDecor.test.ts` |
| `client/src/world/figures6v1.test.ts` | `client/src/world/capitalFigures.test.ts` |
| `client/src/world/figures6v3.test.ts` | `client/src/world/capitalFigures.test.ts` |
| `client/src/world/fix6f6world.test.ts` | `client/src/world/propYSort.test.ts` |
| `client/src/world/mail6t1d.test.ts` | `client/src/world/mailPanel.test.ts` |
| `client/src/world/mail6t1b.test.ts` | `client/src/world/mailPanel.test.ts` |
| `client/src/world/popupBox6f3.test.ts` | `client/src/world/popupHudClear.test.ts` |
| `client/src/world/rt5.test.ts` | `client/src/world/capitalOpening.test.ts` |
| `client/src/world/rt5b.test.ts` | `client/src/world/capitalOpening.test.ts` |
| `client/src/world/rt5c.test.ts` | `client/src/world/capitalOpeningReview.test.ts` |
| `client/src/world/rt5d.test.ts` | `client/src/world/capitalOpeningReview.test.ts` |
| `client/src/world/story6c7.test.ts` | `client/src/world/storyDialog.test.ts` |
| `client/src/world/tracker6f2.test.ts` | `client/src/world/questTracker.test.ts` |
| `client/src/world/uiE3.test.ts` | `client/src/world/panelIcons.test.ts` |
| `client/src/world/uiE3b.test.ts` | `client/src/world/panelIcons.test.ts` |
| `client/src/battle/legend328.test.ts` | `client/src/battle/legend.test.ts` |

## 待 PM 決定

1. 上表「保留原名」的 56 個 bal／L／E／G 系列 pytest 檔要不要另排一段改名（多數只需去掉後綴，但會和現有檔名撞，例如 `test_flash_bal10b`／`bal11b`／`bal12c`／`bal19e` 四個要合併）。
2. 提案寫的「在 `docs/archive/README.md` 註明舊報告的測試路徑已失效」：本段規格不准動 `docs/archive/`，沒寫；要不要由 PM 補一行。
3. 合併檔裡改名的同名 helper（例 `_ok`／`_6f4_ok`、`LIB`／`LIB_48F`）多半其實相同，留給 R5 收斂。
