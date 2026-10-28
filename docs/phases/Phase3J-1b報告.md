# Phase 3J-1b 報告｜天生武器特性＋其餘 5 種形態資料＋3J-1a 小修

> 規格：`docs/phases/Phase3J計畫.md` 第 4.2 節與第 4.4 節。3J-2（定向蓄力）、3J-3（身分）、3J-4（正式技能）、3J-5（外觀）沒有碰；龍的吐息先用一般遠程普攻代替（暫），3J-2 接。

## 做了什麼

### 1. 天生武器特性（`content/forms.yaml` 的 `natural_weapon.traits`）

| 特性（參數） | 形態 | 實作 |
|---|---|---|
| `strikes: 2` 普攻打兩下 | 惡魔（雙刃，暗影，敏捷） | 傳給 `WeaponDef.strikes`；沿用雙匕首的連擊路徑，**每一下各自擲命中與傷害**，目標在第一下倒下就不打第二下 |
| `knockback: 1` 命中推擊 | 巨人（巨拳 1d10） | 傳給 `WeaponDef.knockback`；沿用震退（推擊與撞擊規則） |
| `reach: 2` 觸及（射程 2 的近戰） | 樹人（枝條，感知） | 傳給 `WeaponDef.reach`；藉機攻擊範圍 2；schema 檢查 `reach <= range` |
| `bleed: 1` 命中流血 | 狼人 | `weapon_traits.apply_hit_traits` 命中後施加 `bleed` 1 回合（`ids.BLEED`；規則函式 `rules.forms.natural_bleed`） |
| `backstab_crit: 1` 背刺暴擊範圍再 +1 | 貓 | `AttackProfile.backstab_crit`（只有普攻的 `weapon_profile` 會帶），`positional_bonus` 在背刺時加到核心規則的背刺加成上；非背刺不影響 |

`traits` 從預留的 `tuple[str, ...]` 改成 `NaturalTraits` 模型（全是整數參數，引擎只讀參數）。卡片句與戰鬥說明由資料產生（`form_text.natural_trait_lines`）：「普攻打 2 下（各自擲命中）」「命中推擊 1 格」「觸及 2」「命中流血 1 回合」「背刺暴擊範圍再 +1」。

### 2. 其餘 5 種形態資料（照 6.30 表）

| 形態 | 類別 | 天生武器 | 形態效果 | 進入獎勵 |
|---|---|---|---|---|
| 惡魔 | 物理 | 雙刃 1d6 近戰，暗影，敏捷，打 2 下 | 移動 +1 | 本回合移動 +2 |
| 巨人 | 物理 | 巨拳 1d10 近戰，力量，推擊 1 | 移動 −1 | 本回合你造成的撞擊傷害 +50%（新欄位 `entry.collision_permille: 500`） |
| 暗影形態 | 心智 | 暗影觸 1d6 遠程 3，意志 | 受物理 −20%、受神聖 +50% | 隱蔽 1 回合 |
| 樹人 | 心智 | 枝條 1d6 近戰射程 2，感知，觸及 2 | 治療 +20%、移動 −2、受火焰 +50% | 治療相鄰友方 1d8＋感知 × 0.5 |
| 龍 | 心智 | **暫**：吐息 1d8 遠程 3，智力，進入時選火／冰／雷（3J-2 換成蓄力吐息） | 最大 HP +10%、移動 −1 | 護盾＝最大 HP 的 5% |

- 巨人的撞擊加成：`FormState.entered_round`（新）＝進入的輪數；`rules.forms.form_collision_permille` 在「進入的那一輪、輪到自己行動」時回傳 1500，`triggers._collision_damage`（單位與可破壞物件的撞擊）乘上去。離開形態即失效。
- 測試用技能 `skill_form_{demon,giant,shadow,treant,dragon}`（同 3J-1a 的 5 招：稀有、1 階、`category: spell`、`weapon_req: any`，不進通用池），`skill_scaling.yaml` 補 3 條 overrides（暗影／樹人／龍）。靶場可試：新 reference build `build_form_tester_2`（一組最多 6 個主動欄位，所以第二組放新的 5 種；`trpg battle --ally-build build_form_tester_2`）。技能 291 → 296。

### 3. 4.4 補充

1. **「下一次攻擊」作用在所有命中擲骰**：原本在每次擲骰後就歸零。改成整次攻擊用完才歸零——普攻（`perform_unit_attack`：含穿透與連擊的每一下）、技能（`Cast.roll_hits` 對每個目標擲完之後）、衝撞（`_charge_hit`）。離開形態仍會歸零。
2. **沉默**：新函式 `rules.forms.is_spell_for_silence(rules, skill)`——一般技能看 `category`；進入形態的技能看**形態類別**（心智形態算法術、沉默時不能用；物理形態不算，沉默擋不住）。資料與驗證器同源（技能 `category` 維持 `spell`，由形態資料決定）；套用在 `resource_problem` 與 `copy_free_problem`。
3. **惡魔「本回合移動 +2」**：進入獎勵 `move` 本來就是當回合生效（`unit.move_points += entry.move`），其他形態的移動加減仍在下回合開始結算；加表格測試鎖住。
4. **工坊文字**：`content/workshop_text.yaml` 的 `原語.enter_form`、`原語.enter_form.form` 的 player 句換成玩法 PM 給的版本（逐字）。

### 4. AI 輪替

已在形態中時，其他形態的技能也是候選（一般姿態中仍不換、不主動取消、不重複進入同一形態——合法性檢查擋掉）。輪替的價值是 `ai_profiles.yaml` 新欄位 `form.rotate_value`（初值 4，低於 `enter_value` 8，進入獎勵的護盾／治療／傷害另外計分）。靶場實測（`build_form_tester_2`，open_plain 種子 3）：龍 → 樹人 → 龍輪替，重播通過。

### 5. 其他

- `LOG_FORMAT` `/78` → `/79`（`runner.py` 文件字串與 11 個測試字面值一起改）。
- API／OpenAPI 沒有新增欄位（形態文字由資料產生，`UnitView.form` 結構不變），所以沒有重產 OpenAPI／`schema.d.ts`。重產了 `skill_icons.json`（`client/src/render/fixtures/`，純資料，技能新增造成；沒有碰任何繪圖程式）與 CLI 快照（只有 `skills_list`、`skills_show_all` 兩個雜湊變，戰鬥相關雜湊全部不變）。

## 驗收對照

| 驗收條件 | 證明 |
|---|---|
| 惡魔兩下各擲命中 | `test_demon_strikes_twice_and_each_strike_rolls_to_hit`、`test_demon_strikes_roll_independently`（第一下命中第二下失手） |
| 巨人推擊 +1 | `test_giant_punch_pushes_one_tile`、`test_giant_data` |
| 狼人命中流血 1 回合 | `test_werewolf_hit_causes_one_round_of_bleed`、`test_werewolf_miss_does_not_bleed` |
| 樹人觸及 2 | `test_treant_attacks_at_range_two_and_provokes_at_reach_two`、`test_treant_gets_opportunity_attack_when_a_foe_leaves_reach_two`、`test_bear_gets_no_opportunity_attack_at_distance_two` |
| 貓背刺暴擊範圍 +1 | `test_cat_backstab_crit_range_is_one_wider_than_other_forms`、`test_cat_backstab_trait_does_not_apply_without_a_backstab` |
| 5 種形態資料（效果＋進入獎勵）| `test_all_ten_forms_are_defined`、`test_demon_data_and_entry_move_applies_this_turn`、`test_giant_data`、`test_shadow_data_taken_modifiers_and_conceal`、`test_treant_data_heal_bonus_and_heals_adjacent_allies`、`test_dragon_data_hp_move_and_shield` |
| 4.4.1 下一次攻擊吃所有擲骰 | `test_next_attack_bonus_applies_to_both_demon_strikes_and_is_then_spent`（兩下都 +2、用掉後歸零）、`test_next_attack_bonus_applies_to_every_target_of_an_area_skill`（錐形技能兩個目標都 +2）、`test_next_attack_bonus_is_lost_when_leaving_the_form` |
| 4.4.2 沉默 | `test_silence_blocks_mental_form_skills`（巨鵰、暗影、樹人、龍）、`test_silence_does_not_block_physical_form_skills`（熊、貓、狼人、惡魔、巨人） |
| 4.4.3 惡魔移動 +2 當回合 | `test_demon_data_and_entry_move_applies_this_turn` |
| 4.4.4 工坊文字 | `content/workshop_text.yaml`（逐字）；`trpg content check` 通過 |
| 巨人撞擊 +50% | `test_giant_entry_boosts_collision_damage_this_turn_only`（進入當輪 ＝ 失效時的 1.5 倍）、`test_collision_bonus_ignores_other_forms_and_other_turns` |
| 卡片句 | `test_card_sentence_describes_the_traits`（8 個參數） |
| AI 輪替 | `test_the_ai_may_rotate_to_another_form_but_never_cancels_or_repeats`、`test_the_ai_does_not_use_a_form_skill_while_in_a_plain_stance_or_on_cooldown`；3J-1a 的 `test_the_ai_enters_a_form_...` 改成「不換一般姿態、不重複進入同一形態」 |
| 重播一致 | `test_a_rotation_battle_with_the_new_forms_replays_identically`；CLI：`trpg battle --map open_plain --ally-build build_form_tester_2 --seed 3 --log-json …` → `trpg battle replay …`：「重播驗證通過：111 個動作、295 個事件，最終狀態一致（open_plain，種子 3）」 |

## 驗收指令（摘要）

| 指令 | 結果 |
|---|---|
| `UV_NO_SYNC=1 uv run pytest -q -n 8 tests/engine tests/content tests/skillgen tests/narrative` | 7298 passed（前一次 3 個 `LOG_FORMAT` 字面值已改，重跑通過）、1 skipped |
| `uv run pytest -q -n 8 tests/api tests/roguelite` | 468 passed |
| `uv run pytest -q -n 8 -m "slow or not slow" tests/cli --timeout=3000` | 第一次 145 passed、3 failed（技能數 291→296 的字面值、`skills_list`／`skills_show_all` 快照）；改字面值、`UPDATE_CLI_SNAPSHOTS=1` 重產後 `test_budget_cli.py`＋`test_output_snapshots.py` 8 passed |
| `corepack pnpm -C client test` | 109 files、1032 tests passed |
| `corepack pnpm -C client build` | 通過（只有既有的 chunk 大小提示） |
| `uv run ruff check .`／`ruff format --check .` | All checks passed／1021 files already formatted |
| `uv run mypy` | Success: no issues found in 736 source files |
| `uv run lint-imports` | 7 kept, 0 broken |
| `uv run trpg content check` | 411 個檔案；296 個技能通過預算與結構驗證 |

沒有跑完整的 `scripts/check.py`（依指示由 PM 跑）。

## 待 PM 決定

1. **龍的天生武器暫用一般遠程普攻**（吐息 1d8 遠程 3、智力、進入時選火／冰／雷；沒有蓄力）。3J-2 接定向蓄力時要換掉這個欄位的語意（`forms.yaml` 檔頭已註記）。
2. **巨人「推擊距離 +1」解讀為天生武器命中後推 1 格**（`knockback: 1`，沿用震退）。若設計想的是「基本動作『推』的距離 +1」，需要另一個參數，請玩法 PM 確認。
3. **巨人的撞擊傷害 +50% 的「本回合」**＝進入的那一輪、輪到巨人自己行動時（其他單位回合的反應造成的撞擊不加成；同一輪內再進入會重新計）。範圍是巨人造成的所有撞擊（單位與可破壞物件），含技能的推擊，不只普攻。
4. **樹人的射程**：枝條「近戰、觸及 2」做成近戰、射程 2、`reach 2`（所以能打距離 2 的目標，也能對離開距離 2 的敵人藉機攻擊）。
5. **暗影形態的神聖傷害「+50%」用受傷倍率 1500‰、物理 −20% 用 800‰**，與同形態內其他受傷修正相乘（沒有疊加時就是單一倍率）。
6. **沉默**：形態技能的 `category` 仍寫 `spell`（測試技能），是否沉默由形態類別決定；正式技能（3J-4）若改成武器技類別，`weapon_req` 規則（武器技只能 `melee`／`ranged`）會讓物理形態技能需要手持武器——3J-4 需決定正式技能的類別寫法（建議維持 `spell` ＋ 由形態類別決定沉默）。
7. **AI 輪替的 `rotate_value` 初值 4 未經模擬**；AI 會在進入獎勵夠好且別的形態沒冷卻時切換（每次花 1 AP，離開的形態冷卻 2 回合）。是否太常切換請平衡階段看模擬。
8. **3J-1a 待 PM 項目仍待決**（物理維持費 −5 和耐力回復 +5 打平＝免費、元素化身選元素的介面、火器武器技在形態中的邊角、工坊是否開放形態技能）；本段沒有改動。
9. **`build_form_tester_2`**：主動欄位上限 6，所以 10 種形態分成兩個 reference build；`build_form_tester` 維持原本 5 種。
10. `client/src/render/fixtures/skill_icons.json` 因新增 5 個技能重產（純資料；另一位同時做紙娃娃畫風的 agent 若也重產它，合併時以重產結果為準）。

## 複雜度類 noqa

沒有新增（`C901`、`PLR0911`、`PLR0912`、`PLR0915` 都沒有新增）。
