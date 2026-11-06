# Phase 3-24a2 報告：遠程武器——弩、長槍（火器）＋造型

規格：`docs/phases/Phase3計畫.md` 25.2。分支 `worktree-agent-ad9f0c6250a57949c`（從 main 的 2644292 分出），未 push、未合併。

## 武器資料新增的參數欄位（`content/weapons.yaml`／`WeaponDef`）

全部選填、預設為「無特性」，引擎只讀參數、不寫死數值（命中、暴擊、傷害的修正集中在
`src/trpg/engine/rules/weapons.py`；其餘在 `weapon_traits.py`、`rules/combat.py`、`reactions.py`）。

| 欄位 | 預設 | 用在 | 讀取處 |
|---|---|---|---|
| `pierce_line` | 0 | 弩：5（穿透一直線，最多再擊中幾名後方敵人） | `weapon_traits.pierce_line_targets` → `reactions.perform_unit_attack` |
| `ignore_height` | false | 弩：true（不受高度影響） | `combat.situational_modifier` |
| `magazine` | 0 | 長槍：1（0 ＝ 不用裝填；有彈匣即直射，不可同時有 `lob`，載入時驗證） | `UnitState.ammo`、`combat.reach_problem`、`basics.reload_problem` |
| `reload_ap` | 1 | 長槍：1 | `basics.do_reload`、預覽 AP |
| `gunshot` | false | 長槍：true（槍聲） | `weapon_traits.gunshot_reveals`／`reveal_after_gunshot` |
| `steady {hit, crit_range}` | 無 | 長槍：`{hit: 2, crit_range: 2}`（站定狙擊） | `rules/weapons.weapon_hit_bonus`／`crit_range_cut` |
| `ignore_cover` | false | 長槍：true（無視半掩護） | `combat.half_cover`、`weapon_profile.pierce` |
| `armor_pierce_permille` | 0 | 長槍：250（穿透 25% 防禦） | `combat.defense_value_permille(cut=)` |
| `range_mod [{min_distance, max_distance, hit, damage_permille}]` | 空 | 長槍：貼臉（1～1 格）命中 −2、傷害 ×500‰；4 格以上傷害 ×1250‰ | `rules/weapons.weapon_hit_bonus`／`range_damage_permille` |

另新增：
- **武器動作** `Reload`（動作 `reload`，事件 `WeaponReloaded`）、單位狀態 `ammo`（開場＝武器的 `magazine`）；`UnitView` 只新增欄位 `ammo`、`magazine`（API 型別只新增欄位）。
- 動作分類常數 `BASIC_ACTION_TYPES`（10）／`WEAPON_ACTION_TYPES`（`reload`）／`MANAGEMENT_ACTION_TYPES`，有測試確保每一種動作都被歸類。
- AI：`BasicActionAiRules.reload_points`（20）、`AiWeights.line_up`（弓手模式 3，只對帶 `pierce_line` 的武器有作用）。
- 新武器：弩（雙手、敏捷 1d8、射程 6）、長槍（雙手、敏捷 1d12、射程 8）；白板主角 `build_blank_crossbow`、`build_blank_longgun`（不改既有 22 個 build）。
- 每個武器的特性說明一行（`trait_lines_zh`，資料改參數說明跟著變），HUD 在有彈匣時顯示彈匣格與「空膛」。

## LOG_FORMAT

**遞增：`trpg-battle-log/38` → `/39`**（新動作 `reload`、新事件 `weapon_reloaded`、單位 `ammo`、武器新欄位；`runner.py` 的說明已記）。測試中寫死 `/38` 的四處已改 `/39`。合併時若別的分支也遞增，衝突交 PM 處理。

## 逐條驗收

| 規格 | 證據 |
|---|---|
| 1 弩：穿透一直線 | `tests/engine/test_weapons_24a2.py`：`test_crossbow_bolt_pierces_every_enemy_on_the_line_each_with_its_own_roll`、`test_pierce_stops_at_the_weapon_range`、`test_pierce_ignores_allies_and_units_off_the_line`、`test_pierce_follows_a_diagonal_line_within_range`、`test_pierce_stops_at_a_wall_that_blocks_sight`、`test_changing_pierce_line_changes_how_many_enemies_are_pierced`（改參數 0／1）、`test_bow_does_not_pierce` |
| 1 弩：不受高度影響 | `test_crossbow_is_unaffected_by_height_and_the_data_decides`（弓高打低 +、弩 0；弩去掉 `ignore_height` 就受影響、弓加上就不受影響） |
| 1 弩：不用裝填 | `test_crossbow_needs_no_reload_and_has_no_magazine`、`test_reload_is_illegal_for_weapons_without_a_magazine`、`test_reload_never_shows_up_for_other_weapons` |
| 2 長槍：彈匣、開火後空膛、裝填（1 AP、更多動作、空膛才出現） | `test_longgun_starts_loaded_and_the_shot_empties_the_magazine`、`test_reload_appears_only_when_empty_costs_ap_and_refills`、`test_reload_needs_enough_ap`、`test_magazine_and_reload_cost_come_from_the_data`（參數化：彈匣 2、裝填 2 AP）、`test_attacking_an_object_also_spends_a_round`、`test_ammo_survives_the_state_round_trip`；前端 vitest `reload.test.ts`（裝填只在伺服器列出時出現在「更多動作」、標籤「裝填」） |
| 2 長槍：槍聲解除隱蔽 | `test_gunshot_reveals_a_shooter_hiding_in_the_grass`（含 `gunshot: false` 對照）、`test_gunshot_does_nothing_when_not_concealed` |
| 2 長槍：直射（不能拋射、視線被擋不能打） | `test_longgun_is_direct_fire_and_cannot_lob_over_an_object`（弓可越過同一個石柱）、`test_weapon_schema_rejects_inconsistent_parameters`（`magazine` 與 `lob` 並存會被拒） |
| 2 長槍：站定狙擊（命中 +2、暴擊範圍 +2、可和瞄準疊加） | `test_steady_shot_gets_the_hit_bonus_and_wider_crit_range_when_not_moved`、`test_a_real_move_clears_the_steady_bonus`、`test_steady_stacks_with_aim`、`test_changing_the_steady_parameters_changes_the_bonus`、`test_preview_hit_chance_reflects_steady_and_point_blank` |
| 2 長槍：直射穿甲（無視半掩護、穿透 25% 防禦） | `test_longgun_ignores_half_cover_and_a_bow_does_not`（含參數對照）、`test_longgun_pierces_a_quarter_of_the_targets_defense`（250／500／0）、`test_armor_pierce_stacks_additively_with_armor_break` |
| 2 長槍：貼臉 −2 命中、−50% 傷害；4 格以上 +25% | `test_point_blank_is_penalized_and_far_shots_hit_harder`（1／2／3／4／7 格）、`test_point_blank_damage_is_really_lower`、`test_changing_range_mod_changes_the_behavior`、`test_range_mod_does_not_touch_other_weapons` |
| 2 彈匣狀態存在戰鬥狀態、顯示在 HUD | `UnitState.ammo`（clone／序列化測試見上）；HUD 彈匣格與空膛提示，vitest `reload.test.ts`（`ammoPips`、`ammoText`）；截圖 |
| 3 AI | `test_simple_ai_reloads_an_empty_gun`、`test_utility_ai_reloads_when_empty_and_shoots_standing_still`（站定直接開火、空膛先裝填）、`test_ai_line_up_prefers_a_position_that_lines_up_several_enemies`（弩找一線穿多人的站位，低權重）；避免貼臉靠弓手模式既有的 `keep_distance` 與貼臉懲罰本身（預覽命中率與傷害已含懲罰） |
| 4 造型：弩（輕、重、連弩）、長槍（燧發、獵槍、狙擊），不再退回畫弓 | vitest `weapons24a2.test.ts`（外觀表、形制進快取鍵、三形制畫法互不相同且確定性、4 朝向都畫得出來、未知形制退回預設）；截圖 `3-24a2-weapon-icons-crossbows-longguns.png` |
| 5 基本動作總數仍不超過 10（裝填算進去時檢查上限） | `test_basic_action_cap_stays_at_ten_and_reload_is_a_weapon_action`（每種動作必須歸類；基本動作 10、武器動作 1）、`tests/engine/test_vault.py::test_basic_actions_stay_within_the_limit_of_ten`（改為排除 `reload`，見「待 PM 決定」#1）、vitest `reload.test.ts` |
| 資料驗證 | `test_new_weapons_are_data_with_the_specified_parameters`、`test_trait_text_follows_the_parameters`、`test_blank_heroes_for_the_new_weapons_exist` |
| `--log-json` ＋ `replay` | `tests/cli/test_weapons_24a2_cli.py`：白板槍手與白板弩手在 open_plain 打整場（槍手整場有裝填、每次開火之間必有一次裝填），`format == /39`，`battle replay` 重播一致；另在 ruined_fort、narrow_halls 重播一致 |
| 反應 | `tests/engine/test_weapons_24a2_reactions.py`：遠程武器不藉機攻擊（`requires_melee_weapon`），不用掉子彈 |
| `check.py`、`pnpm build` | 見文末「最終檢查」 |

截圖（`docs/phases/img/`）：`3-24a2-weapon-icons-crossbows-longguns.png`（三種弩、三種長槍的小圖示與紙娃娃，三個朝向）、`3-24a2-empty-magazine-reload-menu.png`（開火後 HUD「彈匣 0/1（空膛，需要裝填）」、普攻灰掉、「更多動作」選單出現「裝填」）、`3-24a2-after-reload-hud.png`（裝填後戰鬥紀錄「裝填（花 1 AP，彈匣 1 發）」、彈匣 1/1）、`3-24a2-crossbow-unit-info-traits.png`（單位資訊列出弩的特性）。

## AI 軌跡改變而換種子

**沒有**：既有武器的行為與數值沒有改變（新參數預設為無特性、AI 新權重只對新武器有作用），所有既有釘種子的測試與 CLI 雜湊快照都不需更動；`skill_icons.json` 也不需重產。

## 新增的複雜度 noqa

無（`_legal_actions` 的武器動作抽成 `_weapon_actions`、`_basic_ap_cost` 改查表，避免超標）。

## 待 PM 決定

1. **裝填是「武器動作」、不算進基本動作的 10 個**（規格寫「新基本動作或武器動作」）：基本動作維持 10、另有武器動作 1，總數上限測試（`test_vault.py`）改為排除 `reload`。若 PM 要把裝填算進 10 個，需要拿掉一個基本動作。
2. **穿透一直線的解讀**：從射擊者經過目標延伸的直線（Bresenham 的延伸），射程內、視線未被擋（牆、黑暗）的後方敵人，最多 `pierce_line`（初值 5，實際上是整條射程）名；每名各自擲命中、各自受傷（不減傷）；友方與單位本身不擋；主目標失手時箭仍會飛過去。
3. **不受高度影響**只取消「高打低／低打高」的命中修正，不影響視線與近戰高度限制；因為讀的是攻擊者的武器，持弩者的武器技同樣沒有高度修正。
4. **彈藥只管普攻（含打物件）**：武器技（`category: weapon`）打出去不耗彈、也不吃站定、距離修正、穿甲、槍聲；是否要讓火器的武器技也耗彈留給玩法 PM。彈匣空時才能裝填（長槍滿膛不出現裝填；手槍 2 發的「開兩槍才裝填」同一套規則可用）。
5. **槍聲**：開火前若自己隱蔽（含站在黑暗、草叢），開火後獲得 `revealed`（不算隱蔽、不能再隱蔽，持續到自己下一個回合結束）；狀態型 `concealed` 本來就會因潛行偷襲在攻擊後移除。
6. **站定**＝本回合還沒主動移動（步行、衝鋒、跑步都算移動；強制位移與傳送不算）；回合外的反應攻擊沿用上一個自己回合的旗標。遠程武器不藉機攻擊（既有的 `requires_melee_weapon`），所以沒有「貼臉藉機射擊」。
7. **數值都是初值、未經模擬**：長槍 1d12（每回合開火 1 次＋裝填 1 次，期望略低於弓的兩發，遠距 +25% 與站定加成補足）、弩 1d8（射程 6）、貼臉 −2／−50%、遠距 +25%、穿甲 25%。請平衡階段模擬後定案。
8. **AI**：`reload_points: 20`（遠大於一般走位，空膛一定先裝填）、`line_up: 3`（只加在弓手模式）；沒有為「站定」另加權重——AI 在射程內有目標時一律先開火，不會先走位；簡易 AI 空膛時也先裝填。
9. **造型**：武器資料上弩、長槍各是一種武器，預設畫輕弩與燧發長槍（`WEAPON_LOOKS`）；三種形制（`form`）的畫法已在紙娃娃與小圖示支援，等裝備段（G 系列）的裝備外觀指定形制。畫法依 `docs/art/sample/paperdoll.js`，三種長槍在紙娃娃上很小、靠槍托、護木、瞄準鏡區分。
10. 單位仍不擋視線（承 3-24a1 待決 #1），所以直線上的單位不會擋住弩的穿透視線。

## 最終檢查

- `uv run python scripts/check.py`：ruff check、ruff format --check、mypy、lint-imports、pytest（**3544 passed**，195.85 秒，含平行全量）、client install／typecheck／test **全部通過**（輸出「全部檢查通過。」）。
- `corepack pnpm -C client test`：53 個檔案、**569 passed**；`corepack pnpm -C client build` 成功。
- 本段新增測試：`tests/engine/test_weapons_24a2.py`（40）、`test_weapons_24a2_reactions.py`（2）、`tests/cli/test_weapons_24a2_cli.py`（7）、vitest `weapons24a2.test.ts`、`reload.test.ts`。
- 截圖用 preview 在非 8000 埠（8123、5287）的臨時伺服器拍攝，拍完已關閉；臨時的圖示展示頁沒有提交。
