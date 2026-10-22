# Phase 3-32a 報告｜普攻流的規則、內容與模擬對照

> 規格：`docs/phases/Phase3計畫.md` 35.1；設計：`docs/design/08-裝備.md` 8.25、8.24（#40 的 6 列）、8.21.5.3。
> 所有數值都是初值，放在 `content/`，未經平衡；模擬只量不調。

## 1. 交付內容

### 1.1 規則與引擎

| 項目 | 做法 | 位置 |
|---|---|---|
| 普攻精通（空格加傷） | 修正規則新增 `empty_slots_cap`（1～6）：`damage_permille` 變成「主動技能欄每空 1 格加這麼多‰」，最多算 cap 格。空格數＝`core.skill_slots.active`（6）減去單位裝備的主動技能數（修正型被動、裝備授予的常駐技能不算），**每次普攻結算當下**由引擎從技能欄算出，不存狀態；只能搭配正的 `damage_permille` 且只套用在普攻（`applies_to.actions`），不可與 `per_turn_limit` 並用。結果和其他傷害加成合計後套全身 +50% 上限 | `content/skills.py` `ModifierSpec`、`engine/modifiers.py` `empty_active_slots`／`_rule_amount` |
| 普攻連擊 `affix_attack_combo` | `AttackAffix.strike: combo`（N＝`value` 2～3、`strike_permille: 500`）。每第 N 次**普攻**命中，對同一個目標多攻擊一次：重新擲命中、傷害 ×50%、不花 AP、不用子彈；**每回合 1 次**（`gear_turn_counts`，藉機攻擊也算）。計數存在新欄位 `UnitState.attack_hits_landed`（只算普攻命中、不含連擊多出來的一下、不受技能命中影響；只有帶連擊詞條的單位才累計）。多出來的一下不會再觸發連擊或分裂，所以不會疊加 | `engine/strikes.py`、`engine/reactions.py` `_attack_once`（`extra_permille`）、`engine/state.py` |
| 分裂 `affix_attack_cleave` | `strike: cleave`。普攻命中且目標還活著時，對目標相鄰（曼哈頓距離 1）的**另一個敵人**造成 50% 傷害（同一把武器的骰子與縮放、自動命中、不暴擊）；多個時依固定順序取 HP 最低、再依座標（x、y）；每回合 1 次 | 同上 |
| 4 條武器特性強化 | 只改武器參數、`weapons` 限定對應武器：`affix_trait_bow_lob_cover`（`ignore_cover` 開關，新增開關型參數支援）、`affix_trait_bow_high_range`（新武器參數 `high_range`，站得比目標高時射程 +N；`attack_reach(state, attacker, target_xy)`）、`affix_trait_longgun_still_crit`（`steady.crit_range` +1，暴擊最低 18 照舊）、`affix_trait_dagger_backstab_die`（新武器參數 `backstab_dice`，背刺的普攻多 N 顆傷害骰；`attack_dice(..., backstab=True)`，預覽同步） | `content/battle.py` `WeaponDef`、`content/weapon_params.py`、`engine/rules/combat.py`、`engine/weapon_traits.py`、`engine/preview.py` |
| 重複詞條 | 8.21.5.3 的「非數值詞條同 id 只生效最強 1 條」本來就由 `diminish()` 處理（非數值類別只有排第一的 1000‰），combo、cleave 屬普攻附加（非數值類）已涵蓋。補強「最強」的判定：新增 `affix_strength()`，連擊的 N 越小越強（取負數），所以參數不同時取觸發較頻繁者。裝備視圖 `AffixLineView` 已有 `active`，新增 `duplicate_of`：沒生效的重複詞條所重複的那一條（「部位＋詞條文字」，例如「手的每第 2 次普攻命中：…」）；生效中的詞條與遞減中仍生效的數值詞條為 `None`。OpenAPI（`client/openapi.json`、`client/src/api/schema.d.ts`）已同步 | `content/equipment.py` `affix_strength`、`engine/gear.py`、`engine/view.py` |
| `LOG_FORMAT` | `trpg-battle-log/47` → **`/48`**（單位狀態新欄位 `attack_hits_landed`、武器新參數、普攻因連擊／分裂／精通而結果不同）；各測試的 `/47` 斷言已改。PM 合併時請依實際順序定號 | `engine/runner.py` |

### 1.2 內容

- `content/skills/skill_attack_mastery.yaml`：**普攻精通**（`kind: modifier`、epic、階級 1）：普攻 +80‰／空格、最多 3 格。預算 72%（`empty_slots_permille: 500`，見待 PM 決定 #3）；關鍵字見 #3。
- `content/affixes.yaml` 新增 6 條（白名單 34 → 40）：

| id | 文字 | 部位 | 初值 |
|---|---|---|---|
| `affix_attack_combo` | 每第 {n} 次普攻命中：多攻擊一次（50% 傷害；每回合 1 次） | 武、手 | N＝2～3 |
| `affix_attack_cleave` | 普攻命中後，對目標相鄰的另一個敵人造成 50% 傷害（每回合 1 次） | 武 | 50% |
| `affix_trait_bow_lob_cover` | 弓的拋射無視半掩護 | 武（限弓） | — |
| `affix_trait_bow_high_range` | 弓站在高處時射程 +1 | 武（限弓） | +1 |
| `affix_trait_longgun_still_crit` | 長槍站定時暴擊範圍再 +1 | 武（限長槍） | +1（受下限 18 約束） |
| `affix_trait_dagger_backstab_die` | 匕首背刺的普攻傷害骰 +1 顆 | 武（限匕首） | +1 顆 |

- 對照用 build（`content/sim/builds.yaml`，新欄位 `reference: true`，**不列入 build 矩陣與 `trpg run auto` 隨機抽選**，所以既有基線與種子不受影響）：`build_attack_archer`（普攻流弓手：精通＋3 招主動技〔穿透、居高、狙擊〕，主動欄空 3 格＝普攻 +24%；裝備 `item_sim_attack_bow`：連擊 N＝2、分裂、高處射程）與 `build_skill_archer`（技能流弓手：同屬性同武器，主動欄放滿 6 招＋穿木者，普通長弓 `item_test_bow`）。
- 小腳本：`scripts/sim_attack_flow.py`（邏輯在 `src/trpg/sim/attack_flow_report.py`）。

### 1.3 順手修的 3-31 問題

CLI 戰鬥輸出（`trpg battle`）遇到 `gear_triggered` 的 `trigger` 是 `attack_rune`（3-31）時會 `KeyError`（那個名稱不在 `skill_triggers.yaml`），3-31 的驗收剛好沒遇到符文觸發所以沒被抓到。`narrative/events.py` 加了 `_ATTACK_TRIGGER_ZH`（普攻符文、普攻連擊、普攻分裂），並有測試涵蓋。

## 2. 驗收證據

| 驗收項目 | 證據 |
|---|---|
| 精通依空格數、上限 3 格 | `tests/engine/test_attack_flow.py` `test_mastery_scales_with_empty_active_slots_and_caps_at_three`（0／3／4／5／6 個主動技 → +24%／+24%／+16%／+8%／0）、`…counts_the_bar_when_the_attack_resolves`（戰鬥中改技能欄，下一次結算跟著變）、`…ignores_passives_and_only_applies_to_basic_attacks` |
| 計入 +50% 上限 | `test_mastery_counts_towards_the_fifty_percent_damage_cap`（精通 240＋玻璃 400 → 截斷為 1500）、`test_mastery_damage_reaches_the_damage_event`（傷害事件倍率 1240） |
| 精通 schema／預算／關鍵字 | `test_mastery_passive_is_valid_and_within_budget`、`test_empty_slots_cap_schema_limits` |
| combo 計數與每回合 1 次 | `test_combo_fires_on_every_nth_basic_hit_once_per_turn_and_resets`（回合 1 命中 1～4：第 2 次觸發、第 4 次同回合不再；回合 2 命中 5、6：第 6 次觸發）、`…every_third_when_n_is_three`、`…extra_hit_is_half_damage_and_does_not_count_as_a_hit`（倍率 1000／500、計數不增）、`…needs_to_roll_again_and_can_miss`、`…counts_only_basic_attacks`（技能命中不計）、`…does_not_stack_when_two_copies_are_worn` |
| cleave 選目標與每回合 1 次 | `test_cleave_hits_the_lowest_hp_adjacent_enemy_for_half_once_per_turn`（HP 最低、傷害倍率 500、其他相鄰與非相鄰敵人不受傷、同回合第二次不再）、`…resets_next_turn`、`…ties_break_by_coordinates`、`…needs_another_adjacent_enemy_and_a_living_target`、`…never_hits_allies` |
| 四條特性強化只在對應武器、數值正確 | `test_traits_only_appear_on_their_own_weapon[4 條]`（掛在別的武器被 `item_problems` 擋下）、`test_bow_lob_cover_ignores_half_cover`（實際半掩護判定）、`test_bow_high_range_adds_one_only_from_higher_ground`（高處射程 9、平地 8）、`test_longgun_still_crit_widens_the_steady_window_within_the_cap`（庫存長槍已在下限 18：不變；站定暴擊餘裕 1 時 +1）、`test_dagger_backstab_die_adds_a_die_only_for_backstabs`（背刺 2 顆、沒詞條 1 顆） |
| 重複詞條只生效 1 條、`duplicate_of` 正確 | `test_combo_keeps_the_more_frequent_duplicate_only`、`test_equipment_view_marks_inactive_duplicates_with_the_winning_slot`、`test_diminishing_numeric_duplicates_stay_active_until_the_fourth`、`test_equal_duplicates_report_the_first_slot` |
| 詞條擲出與部位、內容 | `test_new_affixes_roll_on_the_listed_slots`、`tests/content/test_equipment_content.py`（白名單 40 條、往返 schema）、`test_reference_builds_are_valid_and_kept_out_of_the_matrix` |
| 同種子確定、`--log-json` ＋ `replay` | `test_full_battle_with_the_attack_flow_replays_identically`（整場戰鬥重播事件與最終狀態逐位元相同，並檢查戰報文字）；CLI：`ruined_fort` 種子 31 與 `bandit_lair` 種子 1 以普攻流弓手 `--log-json`，`trpg battle replay` 皆「最終狀態一致」；原本 `hero_fighter,hero_archer,hero_mage` 種子 31 也一致 |
| 模擬 | `tests/sim/test_attack_flow_report.py`（確定性、覆蓋每格）；摘要表見第 3 節 |

## 3. 三情境對照（普攻流弓手 vs 技能流弓手，每格 20 場，種子 0～19）

`uv run python scripts/sim_attack_flow.py --seeds 20 --jobs 4`（約 1～2 分鐘）。情境：**長戰單體**＝英雄單獨（open_plain）對 1 個 `std_enemy_t5`（HP 71）；**範圍戰**＝英雄＋標準隊友（open_plain）對 4 個盜賊；**Boss 戰**＝英雄＋標準隊友對 `bandit_lair` 預設陣容（盜賊首領＋護衛）。效用 AI。

| 情境 | build | 勝率 | 英雄 DPR | 英雄傷害/場 | 英雄存活 | 平均輪數 |
|---|---|---|---|---|---|---|
| 長戰單體 | 普攻流弓手 | 85% | 18.9 | 73 | 85% | 4.0 |
| 長戰單體 | 技能流弓手 | 80% | 13.6 | 75 | 80% | 5.6 |
| 範圍戰 | 普攻流弓手 | 95% | 16.1 | 47 | 90% | 3.3 |
| 範圍戰 | 技能流弓手 | 100% | 12.0 | 39 | 90% | 3.5 |
| Boss 戰 | 普攻流弓手 | 65% | 15.0 | 79 | 25% | 10.3 |
| Boss 戰 | 技能流弓手 | 45% | 9.3 | 50 | 20% | 9.2 |

觀察（只陳述，不調數值）：

- 長戰單體：每場英雄總傷害幾乎相同（73 vs 75），符合「長戰單體約等於技能流」；DPR 差距來自普攻流打得比較快（輪數 4.0 vs 5.6）。
- 範圍戰：普攻流傷害/場仍高於技能流（47 vs 39），勝率沒有更高（95% vs 100%，差 1 場）。目標是「範圍輸技能流」，**這個技能流弓手沒有範圍技**（穿透、居高、狙擊、監視、破甲箭、定點射擊皆單體或直線），所以範圍面沒有被測到；分裂（只打 1 個相鄰敵人）是普攻流唯一的範圍來源。
- Boss 戰：普攻流（傷害 79、勝率 65%）明顯高於技能流（50、45%），**超過「不超過技能流」的目標**。可能原因：技能流弓手的 6 招在 AI 手上用得不夠好（技能流 DPR 9.3 偏低）；也可能普攻流的三個詞條加精通合計偏強。需要 PM 決定要不要先檢查技能流對照組。
- 規格要求「不調數值」，建議的旋鈕在待 PM 決定 #9。

## 4. 待 PM 決定

1. **`LOG_FORMAT` `/48`**：單位狀態加欄位，已升號；與 3-33b 的號碼合併時請 PM 定。
2. **`affix_trait_longgun_still_crit` 在庫存長槍上沒有效果**：長槍站定暴擊範圍已是 2（20−2＝18），剛好是下限 18，詞條 +1 被「暴擊最低 18 照舊」截回。詞條在武器還有餘裕時有效（測試涵蓋），但現況擲到等於沒有。建議二擇一：把長槍基礎站定暴擊範圍改為 1（19 起，詞條補到 18）；或把詞條改成別的站定加成（例如站定命中 +1）。我沒有動長槍基礎值（會改動既有平衡）。
3. **普攻精通的預算與關鍵字**：名稱「普攻精通」、稀有度 epic（修正型被動最低）請玩法 PM 審；新增預算旋鈕 `modifier.empty_slots_permille: 500`（以滿格估算再打 5 折，因為空著技能欄本身就是代價，72%）；精通沒有自然對應的關鍵字，依先例（「標記」makes 已有「無條件全攻擊傷害」暫定規則）在 `skill_keywords.yaml` 加一條暫定規則 `{change: damage_permille, applies_to: actions, unconditional: true, grade: provisional}`（`applies_to` 新增 `actions`），暫定關鍵字數 16 → 17。
4. **連擊細節**：多出來的一下要**重新擲命中**（可以失手、可以暴擊）、傷害 ×50%、不花 AP／子彈、不再觸發連擊與分裂；計數只算普攻命中（技能命中不算、多出來的不算）；與既有 `every_n_hits` 觸發詞條（算全部命中）是兩套計數。若 PM 要連擊多出來的一下自動命中，改 `_attack_once` 一處即可。
5. **分裂細節**：目標被這次普攻打倒時不分裂（沿用 3-31 命中後效果「目標仍存活」的規則）；相鄰＝四方向；自動命中、不暴擊、傷害 ×50%（沒有其他傷害加成）；不會打到友方。
6. **弓特性實作取向**：`bow_lob_cover` 以武器的 `ignore_cover` 實作，弓的**所有**普攻（不只是拋射）無視半掩護；`bow_high_range` 的高處射程加成只用在合法性檢查（`attack_problem`），AI 的移動估算、預覽射程範圍與前端格子高亮仍用基礎射程（因為取決於目標格，要改前端與 AI 才完整，留給後續）。
7. **`duplicate_of` 格式**：一條字串「部位＋的＋詞條文字」（例如「主手的…」）；若 3-32b 想自己組句（部位、詞條名分開），可以改成結構化欄位。連擊「取最強」以 N 小者為準。
8. **對照用 build 與物品**：新增 `BuildDef.reference: true`（不列入矩陣與隨機抽選）；`item_sim_attack_bow` 放在 `items.yaml`（測試物品，不是掉落表）。技能流對照組的 6 招與普攻流的 3 招是我依弓手技能池挑的，不代表設計。
9. **模擬結論與建議旋鈕**（不調數值）：普攻流在 Boss 戰與範圍戰的傷害高於技能流。若 PM 認為要壓低，候選旋鈕：精通 80‰/空格 → 60‰（`skill_attack_mastery.yaml`）、連擊／分裂 500‰ → 400‰（`affixes.yaml` 的 `strike_permille`）。建議先確認技能流對照組沒有被 AI 低估（目前技能流 Boss 戰 DPR 僅 9.3），再由 PM 在驗收時背景跑大量模擬（例如各情境 200 場）。
10. 另：3-31 的 `attack_rune` 戰報文字 KeyError 已順手修（見 1.3）；`docs/phases/Phase3-31報告.md` 的驗收未涵蓋，建議在 3-31 的驗收紀錄補一行。

## 5. 完整檢查

- 複雜度：沒有新增任何 `noqa`（`PLR0911` 等超標時都拆了函式）。
- `ruff check .`、`ruff format --check .`、`mypy`（528 個檔案）：全過。
- `uv run python scripts/check.py` **一次跑完全過**（ruff、格式、mypy、lint-imports、pytest 平行全量、client install／typecheck／vitest 695 個）；沒有卡在 97%，不需要分段。
- 事件格式變動：`LOG_FORMAT` 升為 `/48`（見 1.1）；`client/openapi.json`、`schema.d.ts`、`skill_icons.json`、CLI 快照 `cli_output_hashes.json` 已重產（`UPDATE_CLI_SNAPSHOTS=1`）。前端沒有改程式（只有型別檔多一個選填欄位 `duplicate_of`）。
