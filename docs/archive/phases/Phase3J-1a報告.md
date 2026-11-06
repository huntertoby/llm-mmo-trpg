# Phase 3J-1a 報告｜形態核心規則（玩法決定 #48，06 6.30）

> 規格：`docs/phases/Phase3J計畫.md` 第 4.1 節。天生武器的特性（惡魔兩下、巨人推擊 +1、狼人流血、樹人觸及 2、貓背刺暴擊）與其餘 5 種形態資料屬於 3J-1b，本段沒有做；定向蓄力（3J-2）、身分（3J-3）、正式技能（3J-4）、外觀（3J-5）也沒有碰。

## 做了什麼

### 1. 資料：`content/forms.yaml` 與 schema（`src/trpg/content/forms.py`）

| 欄位 | 內容 |
|---|---|
| 表格層級 | `upkeep_stamina: 5`（物理）、`upkeep_mana: 3`（心智）、`cooldown: 2`（離開後該形態的冷卻） |
| `FormDef` | `id`、`name_zh`、`category`（`physical`／`mental`）、`natural_weapon`、`effects`、`entry`、`look`（外觀 id） |
| 天生武器 `NaturalWeapon` | `dice`、`attack`（`melee`／`ranged`）、`range`、`attrs`（1～2 個；同類取較高、一物理一心智取平均，同 08 8.11）、`element`（固定）或 `element_choices`（進入時選）、`damage_permille`（天生武器傷害加成，元素化身 +10%）、`traits`（**預留給 3J-1b，本段必須留空**，填了會被 schema 擋下）。`weapon_def()` 產生形態內實際使用的 `WeaponDef`（id `form_<形態>`，沒有詞條與小特性）。 |
| 形態效果 `FormEffects` | `defense_permille`、`move`、`max_hp_permille`、`damage_taken`（依元素，可寫 `chosen`）、`heal_permille`、`flat_height`（高度差 N 以內當平地走）。**沒有任何六屬性欄位**。 |
| 進入獎勵 `FormEntry` | `shield_max_hp_permille`（＋`shield_duration`）、`heal_max_hp_permille`、`next_attack_hit`、`next_attack_crit`、`move`（本回合）、`conceal`、`burst`（範圍傷害，元素可寫 `chosen`）、`heal_adjacent`（骰＋屬性 × ‰） |
| 本段的 5 種 | 熊、貓、巨鵰、元素化身、狼人，數值照 6.30 表（貓的背刺暴擊 +1、狼人的流血是天生武器特性，3J-1b） |

規則包 `Ruleset.forms`（嵌入戰鬥狀態，重播不依賴資料檔）、`Ruleset.form_def()`。

### 2. 原語 `enter_form`（`skill_primitives.yaml`）

- 只能是姿態（`kind: stance`）**唯一**的效果、形狀 `self`、參數 `form`（必填，引用 `forms.yaml`，跨檔案檢查）。姿態骨架 `stance` 的核心原語加上 `enter_form`。
- AP：照姿態（`core.stance_ap_cost` ＝ 1）。
- **欄位**：`SkillDef.slot_kind`——形態技能雖然是姿態，**佔主動欄位**（`skill_slot_problems`、`roguelite/auto.py`、普攻精通的空欄數都改看它）。
- **預算**：`base_points: 11`（固定），係數 `skill_budget.yaml` 的 `form_coefficient_permille: 1000`（照姿態計、另列一項；預算器標示「形態係數」）。`trpg content check`：289 個技能通過預算與結構驗證。
- `skillgen/validate.py`：姿態必須施加姿態狀態的規則，對形態技能豁免。
- 工坊：參數選單（`option_params.py` 的 `form`）、中文參數名、`workshop_text.yaml` 加 2 條（`原語.enter_form`、`原語.enter_form.form`，**實作者初稿，待玩法 PM 改寫**；表格 157 條）。

### 3. 引擎（`src/trpg/engine/forms.py` 狀態轉換、`src/trpg/engine/rules/forms.py` 純查詢）

| 規則 | 實作 |
|---|---|
| 狀態 | `UnitState.form: FormState | None`（形態 id、進入時選的元素、手上的武器、進入前的裝備狀態、最大 HP 加減量、進入的技能）、`form_cooldowns`、`next_attack_hit`／`next_attack_crit`；`clone` 與 JSON 往返都涵蓋 |
| 進入 | 先移除一般姿態（`status_removed: replaced`）、離開目前形態（`switched`）；普攻武器換成天生武器、主手的普攻附加與武器特性強化詞條拿掉（存在 `FormState`，離開時換回）；最大 HP 依 ‰ 加減（加減量無條件捨去；目前 HP 不變但不超過新上限）；發出 `form_entered`；進入獎勵（護盾、治療、隱蔽、範圍傷害、治療相鄰友方交給效果佇列；命中／暴擊與本回合移動直接寫入）。已在該形態中、或該形態冷卻中不能施放（`skill_problem`）。 |
| 互斥 | 施加任何姿態狀態 → 離開形態（`form_left: stance`）；進入形態 → 移除姿態 |
| 取消 | `end_stance` 在形態中也合法、免費（`cancelled`）；`legal_actions`、`has_only_end_turn` 一併考慮形態 |
| 被迫解除 | 倒下（`downed`）、撤離（`escaped`）、戰鬥結束（`end_battle` 先解除全部形態，`battle_end`；所以帶出戰鬥的 HP 不會超過原本上限） |
| 換普攻 | 形態中 `unit.weapon` 是天生武器——普攻、藉機攻擊、反擊等「用武器打」的路徑自動改用它（屬性 × 0.3、雙屬性取較高）；手上武器的普攻特性（震退、收割……）自然不生效 |
| 武器技仍看手上武器 | `held_weapon(unit)`：`engine/skills/`（射程、武器需求、命中、骰子、縮放屬性、精通、手持條件）、技能形狀轉換、收割（武器技）、武器技的元素來源（`attack_element_sources(held=True)`，連同主手的武器元素詞條）都看手上的武器；`attack_value` 多了 `weapon` 參數 |
| 形態效果 | 防禦 → `defense_value_permille`（直接相加，同防禦姿態）；移動 → `move_points_for_turn`（回合開始結算，同石膚）；受傷 → `damage_taken_permille`（依元素）；治療加成 → `modifiers.heal_permille`；天生武器傷害加成 → `modifiers.damage_permille`（只套普攻，計入全身上限）；高度差當平地 → `unit_step_cost` |
| 維持費 | 自己的回合開始（耐力回復之後）：物理扣耐力、心智扣法力（`form_upkeep_paid`）；付不起 → 自動解除（`form_left: upkeep`），移動點數重算 |
| 冷卻 | 離開（任何原因）後該形態冷卻 2；自己的回合開始 −1（同技能冷卻的倒數）；別的形態不受影響 |
| 下一次攻擊 | `roll_attack` 讀 `next_attack_hit`／`next_attack_crit`（暴擊範圍下限 2）；普攻與技能的擲命中之後歸零；離開形態也歸零 |
| 事件 | `form_entered`（元素、進入後的最大 HP 與 HP）、`form_left`（原因、冷卻、離開後的最大 HP 與 HP）、`form_upkeep_paid`（資源、數量、剩餘） |
| 動作 | `use_skill` 多了 `form_element`：只有元素可選的形態可以帶、要在清單內；省略取清單第一個 |
| `LOG_FORMAT` | `/77` → `/78`（`runner.py` 文件字串與 11 個測試字面值一起改） |

### 4. 文字、檢視、前端

- **卡片句與戰鬥紀錄全部由資料產生**（`src/trpg/content/form_text.py`；放在 content 層讓引擎的 `UnitView` 也能用）：例「化身為熊（物理形態，持續到取消）：普攻改用熊爪 1d8 近戰（力量／體質取較高 × 0.3）；形態中：最大 HP +15%、防禦 +10%、移動 −1；進入時：護盾＝最大 HP 的 10%（2 回合）；每回合開始 −5 耐力（不夠就自動解除）；離開後這個形態冷卻 2 回合」。卡片的算法列多一行「天生武器（普攻）：…（目前 +N）」（有持有者時）。戰鬥紀錄：「X 化身為熊，最大 HP 64，HP 56」「X 維持熊形態：−5 耐力（剩 33）」「X 的熊形態倒下而解除（冷卻 2 回合）…」。
- `UnitView.form`（`FormView`：形態 id、名稱、類別、外觀 id、元素、天生武器句〔含目前 +N〕、效果、維持費）與 `form_cooldowns`（`FormCooldownView`）；形態中 `weapon_*` 欄位**仍是手上的武器**（紙娃娃與武器技用）。
- 預覽：連鎖結果新增 `form`（「X 進入形態」）。
- 前端（只做文字）：單位資訊（`UnitInfo.tsx` 的 `formRows`）列「形態／天生武器／效果／維持／形態冷卻」；預覽文字；技能圖示部件 `enter_form`。OpenAPI、`schema.d.ts`、`glossary.json`、`skill_icons.json` 重產；vitest 夾具補 `form`、`form_cooldowns`。沒有新的彈出卡片。
- 不畫外觀（3J-5）。

### 5. AI

- 沒在姿態或形態中、AP 夠 → 形態技能一律是候選（`_placement_estimate`），由預覽的 `form_entered` 收益決定：`support` 權重 × `ai_profiles.yaml` 的 `form.enter_value`（初值 8，同姿態狀態的價值）；進入獎勵的護盾、治療、傷害照一般事件計分。
- 已在姿態或形態中不換；不主動取消（維持費不夠時由規則自動解除）。

### 6. 測試用技能與 build

- `content/skills/skill_form_{bear,cat,roc,elemental,werewolf}.yaml`：「化身為熊」等 5 招（稀有、1 階、`category: spell`、`weapon_req: any`，只為測試；正式技能在 3J-4）。巨鵰、元素化身的縮放屬性在 `skill_scaling.yaml` 的 `overrides` 附理由。
- 靶場可試：技能工坊「裝上試玩」可直接選這 5 招；另加對照組 build `build_form_tester`（`reference: true`，不列入矩陣與隨機抽選），`trpg battle --ally-build build_form_tester` 可跑。
- 這 5 招**不進通用池**（`candidates._general_pool` 排除形態技能；它們沒有關鍵字，否則會被升級的「新方向」抽到），身分與技能池在 3J-3。

## 驗收對照

| 驗收條件（4.1） | 證明 |
|---|---|
| 1. forms.yaml 與 schema、5 種資料 | `tests/engine/test_forms.py` 全部（資料實際跑引擎）；`trpg content check` 通過 |
| 2. 進入 1 AP、和姿態互斥、自己回合取消免費、倒下或戰鬥結束解除、佔主動欄位、預算照姿態 | `test_entering_a_form_costs_one_ap_and_swaps_the_basic_attack`（5 種參數化）、`test_entering_a_form_replaces_a_stance_and_a_stance_ends_the_form`、`test_end_stance_cancels_a_form_for_free_and_restores_the_hand_weapon`、`test_a_form_ends_when_the_unit_goes_down`、`test_a_form_ends_when_the_battle_ends`、`test_form_skills_take_an_active_slot`；預算：`trpg content check`（289 個技能通過） |
| 3. 換普攻（屬性 × 0.3、雙屬性取較高），武器技仍看手上武器 | `test_natural_weapon_damage_matches_the_card_bonus`（熊、貓、狼人、巨鵰）、`test_weapon_skills_still_use_the_hand_weapon_in_a_form` |
| 4. 形態效果、維持費、自動解除、單一形態冷卻 2、進入獎勵 | `test_bear_effects_and_entry_shield`、`test_cat_effects_and_next_attack_crit_range`、`test_roc_effects_and_next_attack_hit`、`test_roc_walks_height_one_as_flat`、`test_elemental_chooses_an_element_and_bursts_adjacent_enemies`、`test_elemental_defaults_to_the_first_element_and_rejects_others`、`test_werewolf_effects_and_entry_heal`、`test_upkeep_is_paid_at_each_turn_start`（4 種參數化）、`test_upkeep_that_cannot_be_paid_ends_the_form_and_its_move_bonus`、`test_switching_forms_leaves_the_old_one_and_cools_only_it`、`test_form_cooldown_ticks_on_own_turn_starts` |
| 5. 狀態、UnitView、存檔、重播、事件、LOG_FORMAT、紀錄與卡片句、HUD | `test_state_in_a_form_round_trips_through_json`、`test_unit_view_shows_the_form_the_hand_weapon_and_form_cooldowns`、`tests/engine/test_state_clone.py`、`tests/narrative/test_form_cards.py`（3 個）、`client/src/ui/unitInfoForm.test.ts`、`previewText.test.ts` 的「describes entering a form」 |
| 6. AI | `test_the_ai_enters_a_form_when_it_has_nothing_better_and_never_cancels` |
| 7. 開發起始包或靶場可試 | 工坊裝上試玩可選；`build_form_tester`（下面的重播） |
| 8. 行為一致測試 | 同上（`tests/engine/test_forms.py` 33 個） |
| 8. 天生武器 `damage_dealt`＝卡片「目前 +N」 | `test_natural_weapon_damage_matches_the_card_bonus`：卡片算法列的 N ＝ `damage_dealt.scaled_permille ÷ 1000`，傷害 ＝ 骰 1 ＋ N |
| 8. 重播一致 | `test_a_battle_with_forms_replays_identically`；CLI 重播見下 |
| 9. 一場含進入形態的重播 | `trpg battle --map open_plain --ally-build build_form_tester --seed 3 --log-json …` → `trpg battle replay …`：「重播驗證通過：117 個動作、318 個事件，最終狀態一致（open_plain，種子 3）」。紀錄中有「化身為熊」、每回合「維持熊形態：−5 耐力」、「熊形態倒下而解除（冷卻 2 回合）」 |

## 驗收指令（摘要）

| 指令 | 結果 |
|---|---|
| `UV_NO_SYNC=1 uv run pytest -q -n 8 tests/engine tests/content tests/skillgen tests/narrative` | 7222 passed, 1 skipped |
| `UV_NO_SYNC=1 uv run pytest -q -n 8 tests/api tests/roguelite` | 468 passed |
| `UV_NO_SYNC=1 uv run pytest -q -n 8 -m "slow or not slow" tests/cli --timeout=3000` | 第一次 145 passed、3 failed（技能數 284→289 的字面值、`skills_list`／`skills_show_all` 快照）；改字面值、`UPDATE_CLI_SNAPSHOTS=1` 重產後 `test_budget_cli.py`＋`test_output_snapshots.py` 8 passed。**戰鬥快照的雜湊全部不變**（既有戰鬥行為沒有改變），只有技能清單兩個雜湊變了 |
| `corepack pnpm -C client test` | 106 files、1000 tests passed |
| `corepack pnpm -C client build` | 通過（只有既有的 chunk 大小提示） |
| `uv run ruff check .`／`uv run ruff format --check .` | All checks passed／1012 files already formatted |
| `uv run mypy` | Success: no issues found in 734 source files |
| `uv run lint-imports` | Contracts: 7 kept, 0 broken |
| `uv run trpg content check` | 404 個檔案；289 個技能通過預算與結構驗證 |
| 重產 | `uv run python -m tests.narrative.icon_fixture`、`uv run python scripts/export_client_fixtures.py`、`uv run python scripts/export_openapi.py` → `corepack pnpm -C client gen:api` |
| 一場含形態的重播 | `trpg battle --map open_plain --ally-build build_form_tester --seed 3 --log-json …`、`trpg battle replay …`：重播驗證通過（117 個動作、318 個事件，最終狀態一致） |

沒有跑完整的 `scripts/check.py`（依指示由 PM 跑）。

## 待 PM 決定

1. **進入時目前 HP 不變**：最大 HP +15%（熊）只提高上限，目前 HP 不跟著加；離開時最大 HP 減回、目前 HP 不超過上限。加減量無條件捨去（999 的 −10% 是 −99）。設計沒寫，採保守做法。
2. **形態的移動加減在回合開始結算**（同石膚、加速）：當回合進入或取消不改目前的移動點數；只有回合開始付不起維持費自動解除時重算。貓／狼人當回合變身不會立刻多 1 格。
3. **「下一次攻擊」的進入獎勵**（貓暴擊範圍 +2、巨鵰命中 +2）：用在下一次擲命中的攻擊（普攻或技能；多目標技能只有第一次擲骰吃到），用掉或離開形態時失效，不會跨回合到期。
4. **元素化身的範圍傷害「1 格內」取曼哈頓距離 1**（上下左右 4 格），自動命中、不加屬性；元素選擇在 `use_skill.form_element`，省略＝火焰。**AI 一律省略（永遠火焰）、前端沒有選元素的介面**——3J-4 或前端段要補。
5. **形態技能的類別**：測試技能用 `category: spell`（武器技只能 `melee`／`ranged`），所以**沉默中不能進入形態**；正式技能（3J-4）要不要另訂。
6. **物理形態的維持費 −5 和耐力回復 +5（3H-5）打平**：維持費在耐力回復之後扣，滿耐力回復的主角實際上「免費」維持物理形態（重播裡每回合都是「−5（剩 33）」）。是否要改扣在回復之前、或調數值，請平衡時決定。
7. **主手詞條**：形態中主手的「普攻附加」與「武器特性強化」詞條全部不生效（含符文、連擊、分裂、召喚物繼承）；武器技仍吃主手的「武器元素詞條」。火器武器技在形態中，站定／距離修正讀的是天生武器（沒有），這個邊角沒有處理。
8. **AI 不從姿態換成形態**（沿用 2E-2「不主動換姿態」），也不在形態之間輪替；輪替留給 3J-1b（規格寫「AI 權重補輪替」）。
9. **進入獎勵的護盾持續 2 回合**（同護盾原語預設）；設計只寫「護盾＝最大 HP 的 10%」。
10. **工坊會出現 `enter_form`**（姿態骨架的核心原語）；隨機組合器不會產生形態技能（姿態只從姿態狀態組），通用池也排除形態技能。是否開放工坊做形態技能請在 3J-3／3J-4 決定。

## 複雜度類 noqa

沒有新增（`C901`、`PLR0911`、`PLR0912`、`PLR0915` 都沒有新增；AI 估值的分支以合併條件處理，沒有加 noqa）。
