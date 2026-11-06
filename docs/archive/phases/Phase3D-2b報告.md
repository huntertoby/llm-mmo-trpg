# Phase 3D-2b 報告：傳送他人 `teleport_target` ＋ 任意兩者互換 `swap_any`

## 1. commit

| commit | 內容 |
|---|---|
| 87bfaf7 | 兩個原語（schema、兩段選取形狀 `unit_then_tile`／`unit_pair`、選取與列舉、結算、位移檢定、預算、骨架）、`UseSkill.second_target_id`、`MoveMode` `teleported`、`maneuver_rolled` 的 `teleport`／`swap` 與 `resist_bonus`、核心規則兩個抵抗加成、`swap` 改用位移檢定、預覽 `displace_checks`／`displace_chance`、紀錄文字、示範技能「放逐」「虛空互換」、新 build `build_banisher`、`LOG_FORMAT` `/20`；`tests/engine/test_displace_others.py` |
| 1db27f5 | API `PreviewOut.displace_checks`／`displace_permille`、重新產生 `openapi.json`／`schema.d.ts`；`tests/api/test_displace_api.py` |
| 140bdb9 | 網頁：兩段選取推廣到單位（傳送：單位 → 落點；互換：單位 → 單位）、預覽標記與成功率文字、動作標籤、vitest |
| 8693b5a | AI：便宜估計（`engine/ai/displace.py`）與預覽收益（`utility._displace_gains`）；`tests/engine/test_displace_ai.py` |
| 29f561d | 測試：AI 虛空互換戰鬥的重播 |
| f8601e1 | 網頁：互換第二段的提示文字 |
| （本報告） | 報告 |

開發期間 main 上有玩法 PM 的 docs commit（d11fd9e、efecd31 等）；我沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 位移檢定（統一，0.5 #1）

設計 6.19 寫的「位移的對抗判定」「同一般位移」，引擎裡唯一一套 d20 的位移類判定是技巧動作與技能擊倒用的 `maneuvers.contest`（`d20 ＋ 比例修正（技能縮放屬性 vs 目標同屬性）＋ 熟練 − 抵抗加成 ≥ hit_target`，自然 1 失敗、自然 20 成功）。技能的推擊本身沒有獨立的抵抗，只靠技能的命中判定，所以我把「位移檢定」定為 `contest`，三個原語一律使用：

| 原語 | 敵方的檢定 | 友方 |
|---|---|---|
| `swap`（3D-2，一併改） | `contest`，抵抗加成 0；**不再擲命中**（紀錄 `maneuver_rolled` 的 `maneuver: swap`）。「調虎離山」的傷害仍有自己的命中判定，所以對敵人是兩次獨立擲骰（交換、傷害） | 自動成功 |
| `swap_any` | 每個敵方各擲一次（依單位 ID，全部擲出），任一個抵抗成功則整個互換失敗；抵抗加成 0 | 全是友方不檢定 |
| `teleport_target` | 抵抗加成 `teleport_enemy_resist_bonus`（+2）；落點是致命地形再加 `teleport_lethal_resist_bonus`（+8，共 +10） | 不檢定 |

`maneuver_rolled` 新增欄位 `resist_bonus`（已從 `total` 扣除，`modifier` 不含）；`maneuver` 新增 `teleport`、`swap`。預覽中抵抗判定是分歧點（`min` 視為抵抗成功、`max` 視為失敗）。

### 2.2 成功率計算（d20 精確計算）

「同級」＝兩者縮放屬性相同，比例修正 0；熟練 +2；`hit_target` 11。成功條件：自然骰 ＋ 0 ＋ 2 − 抵抗 ≥ 11，也就是自然骰 ≥ 9 ＋ 抵抗；自然 1 一律失敗、自然 20 一律成功。

| 情況 | 抵抗加成 | 需要的自然骰 | 成功率 |
|---|---|---|---|
| `swap`、`swap_any` 對敵人 | 0 | ≥ 9 | 12/20 ＝ **60%** |
| `teleport_target` 對敵人（一般格） | +2 | ≥ 11 | 10/20 ＝ **50%** |
| `teleport_target` 對敵人（致命地形） | +10（初值 +2 ＋ +8） | ≥ 19 | 2/20 ＝ **10%** |

規格要的「同級約 10–15%」：總加成 +9 是 15%（需要 ≥ 18）、+10 是 10%（需要 ≥ 19），整數加成沒有 12.5%。我選 **+10（10%）**：施放者屬性比目標高時成功率會上升（修正 +2 → 20%、+4 → 30%），保守選下緣才不會被屬性差距拉得太高。測試：`test_the_success_chances_at_the_same_level_are_60_50_and_10_percent`（`contest_chance` 精確機率）、`test_a_deadly_landing_is_almost_impossible`（自然 18 失敗、19、20 成功、1 失敗）、`test_the_check_scales_with_the_casters_attribute`（強者上升、弱者只剩自然 20 ＝ 5%）。

實際英雄（智力 16）對盜賊弓手（智力較低）的比例修正是 +4，致命地形成功率 **30%**（預覽顯示 30%，需要自然 ≥ 15）。放在 `content/rules/core.yaml`，PM 可調。

### 2.3 原語與形狀

- **形狀**（`content/skill_shapes.yaml`，`REQUIRED_SHAPES` 11 → 13）：`unit_then_tile`（targeting `unit_tile`）與 `unit_pair`（targeting `unit_pair`），都有 `range` 參數、稀有以上，與投擲的 `object_then_tile` 同一個兩段選取模式。
- **`UseSkill.second_target_id`**（新欄位）：互換的第二個單位；傳送沿用 `target_id`（被傳送的單位）＋ `target_pos`（落點）。欄位對不上形狀時拋 `IllegalActionError`（`_require_fields`）。
- **`teleport_target` 選取**（`targeting._unit_tile_area`）：被傳送的單位要存活、不能是自己、在射程與視線內（含致盲距離上限與對敵人的隱蔽限制，與一般單位目標相同）；落點要在射程與視線內，沒有單位，可站立或是致命地形（`teleport_landing_problem`）；**Boss（`boss` 標籤）對致命地形免疫：選不到**（錯誤訊息「X 是 Boss，對傳送到致命地形免疫」），`legal_actions` 不列。落點與單位的合法組合都由 `_teleport_candidates` 列舉（單位依 ID × 落點依 `(y, x)`）。
- **`swap_any` 選取**（`_unit_pair_area`）：兩個不同的存活單位（順序不拘，不必含施放者），都在射程與視線內，兩格都要能讓對方站上去；`legal_actions` 每一組只列一次（依單位 ID 排序）。
- **結算**：`teleport_target` 用新的 `MoveMode` `teleported`：落點的陷阱、表面、致命地形照常結算；**不墜落**（比照傳送）；不觸發離開相鄰格的反應；不觸發 `on_enter_surface` 被動（比照 `teleport`）。`swap_any` 重用 3D-2 的 `SwapUnitsEffect`（`mode: swap`，墜落、陷阱、表面都照常）。非 Boss 的精英落在致命地形時照既有規則（受最大 HP 比例傷害並移到安全格）。
- **schema**：兩個原語只能用在主動技能、必須搭配各自的形狀、**必須是技能唯一的效果**（`SkillDef._check_pair_moves`）；兩者不能在陷阱技能；`unit_then_tile`／`unit_pair` 只給手寫技能（隨機組合器不使用）。
- **預算**（初值，未經模擬）：`teleport_target` 固定 11 點、`swap_any` 固定 12 點（結構型、稀有以上）。兩個只有單一效果的技能必須達到 70% 的下限，所以點數比其他位移原語高（放逐 73.2%、虛空互換 80.2%；形狀會讓機制標籤帶 `area`，協同 ×1.1）。致命地形的低成功率沒有另外折價：預算是固定點數，沒有「成功機率」維度（見待決 #3）。
- **骨架**：`displace` 的核心原語加兩者；`mechanics._DISPLACE` 涵蓋。

### 2.4 預覽、API、網頁

- `Preview.displace_checks`（`DisplaceCheck`：`unit_id`、`chance`、`resist_bonus`、`lethal`）與 `displace_chance`（全部敵方都被勝過的機率；友方不檢定為 `None`）；`MoveInfo` 新增 `kind: teleport`。Boss 免疫的原因寫在 `Preview.notes`（「X 是 Boss：對傳送到致命地形免疫，致命地形不能選為落點」）。API：`PreviewOut.displace_checks`（`success_permille`、`resist_bonus`、`lethal`）、`displace_permille`。
- 網頁（兩段選取推廣）：`TargetSet.hurls`（第一段 ID → 第二段）現在也裝單位；`pairKind` 區分投擲／傳送／互換；互換兩個方向都登記（先點哪個都可以），第二段以格子上的單位判定。面板提示依種類顯示「要傳送的單位／落點（致命地形的成功率極低，Boss 不能選）」「要互換的第一個單位／第二個單位」，「重選單位」按鈕。預覽：被傳送的單位原位「傳」、落點「落」（致命地形紅框「險」）、文字「傳送：… → …」、「位移檢定：X 成功率 50%（抵抗 +2）」、致命地形「⚠ 傳送到致命地形：X 要過極難的抵抗（抵抗 +10），成功率只有 10%；失敗時不會移動」、互換多個敵人時「互換成功率：36%」、友方「友方不需檢定，必定成功」。動作標籤「技能：放逐 → X → (4, 1)」「技能：虛空互換 → X ⇄ Y」。
- 紀錄文字：`對 X 使出傳送：d20=17 修正 +4 熟練 +2 抵抗 -10 = 13（目標 11）→ 成功`、`X 被傳送到 (4, 1)`。

### 2.5 示範技能與 build

| 技能 | 內容 | 預算 |
|---|---|---|
| 放逐 `skill_banish`（rare，法術，AP 2，射程 5，法力 6，冷卻 3） | `teleport_target` | 73.2% |
| 虛空互換 `skill_void_swap`（rare，法術，AP 2，射程 5，法力 5，冷卻 3） | `swap_any` | 80.2% |

既有 13 個 build 的主動欄位已滿或不是法術流，所以**新增第 14 個 build `build_banisher`（放逐流）**：火焰法杖、智力 16，技能 放逐、虛空互換、火焰箭、咒印飛彈、碎障爆破、閃現。

### 2.6 AI

`engine/ai/displace.py`：便宜估計 `displace_estimate`（不跑引擎）：被移動的單位走向致命地形（10）、有害表面（4）、我方陷阱（3）的收益；友方離開危險、**HP ≤ 40% 的隊友離開兩格內的敵人**；分數不為正的選取不納入候選（候選數受 `skill_candidates` 上限，列舉再多也不會變慢）。`utility._displace_gains`：預覽最多後果的模擬中，被移動的單位走到更危險或更安全的格子（敵人進致命地形＝`kill`＋`env_kill`，其餘 1/4 已由既有 `_kill_gains` 計入；友方進致命地形＝損失；有害表面＝`surface`；受傷的隊友脫離敵人＝`kill` × 少掉的敵人數），整體乘上位移成功率（`_gain_frame` 的 `hit`）。

## 3. 驗收條件逐條（2B.1）

| # | 結果 | 證據 |
|---|---|---|
| 1 | 傳送：友方必成 | `test_teleporting_an_ally_never_rolls_and_always_works`（沒有擲骰事件）、`test_an_ordinary_enemy_dies_in_lava_and_an_ally_can_be_sent_there_without_a_roll` |
| 1 | 傳送：敵方抵抗 | `test_an_enemy_resists_with_plus_two_at_the_same_level[10／11]`（自然 10 抵抗、11 成功；`resist_bonus` 2、不擲命中） |
| 1 | 傳送：致命地形極難、以固定種子造出成功與失敗 | `test_a_deadly_landing_is_almost_impossible[18／19／20／1]`（以 `with_rolls` 固定亂數）；`test_a_fixed_seed_makes_both_a_success_and_a_failure_on_a_normal_tile`（真的種子 0–39 找出成功與失敗各一）；`test_the_roll_is_deterministic_for_a_fixed_seed`；PM 實測情境見第 6 節（種子 1 成功、種子 0 失敗） |
| 1 | Boss 免疫 | `test_a_boss_cannot_be_sent_into_deadly_terrain`（選取被拒、`legal_actions` 不列）、`test_a_boss_is_checked_normally_on_an_ordinary_tile`（一般格照常檢定）、`test_the_preview_has_no_check_for_allies_and_explains_boss_immunity`（預覽說明原因）、`test_a_boss_is_never_banished_into_deadly_terrain`（AI） |
| 1 | 落點不能站或有單位被拒 | `test_teleport_rejects_bad_landings[5 組]`（有敵人、被傳送者自己的格子、超出射程、木箱擋路、地圖外）、`test_teleport_needs_a_line_of_sight_to_the_landing_and_the_unit`、`test_teleport_cannot_target_a_unit_beyond_the_reach`、`test_teleport_validates_the_unit_then_the_landing`（缺欄位、自己、多餘欄位） |
| 1 | 落點互動 | 表面 `test_the_landing_surface_applies`、陷阱與不墜落 `test_the_landing_trap_triggers_but_falling_does_not`、致命地形死亡／精英 `test_an_ordinary_enemy_dies_in_lava…`、`test_a_non_boss_elite_takes_the_percent_damage_and_is_moved_to_safety`、不觸發藉機攻擊 `test_teleporting_away_does_not_provoke_an_opportunity_attack` |
| 2 | 互換：兩友方不檢定 | `test_swapping_two_allies_never_rolls`、`test_swapping_with_the_caster_works_too`、`test_the_caster_does_not_have_to_be_one_of_the_two_and_order_does_not_matter` |
| 2 | 含敵人檢定、任一抵抗成功則失敗 | `test_an_enemy_in_the_pair_rolls_the_ordinary_displacement_check[8／9]`、`test_every_enemy_rolls_and_one_resist_fails_the_whole_swap`（兩個敵人各擲、其中一個抵抗 → 沒有任何移動） |
| 2 | 兩格可站判定 | `test_swapping_needs_both_tiles_to_be_standable_and_two_distinct_units`（同一個單位、缺欄位、多餘欄位、其中一格是岩漿）、`test_swap_any_needs_sight_and_reach_for_both`、`test_legal_actions_list_each_pair_once` |
| 2 | 落點互動 | `test_swapped_units_resolve_their_new_tiles`（火焰表面）、`test_a_swapped_unit_triggers_a_trap_on_its_new_tile` |
| 2 | Boss 換到致命地形免疫 | **規則上不會發生**（互換要求兩格都能站，致命地形不可站，見待決 #4）；`test_a_boss_is_swapped_like_anyone_else_and_never_lands_in_deadly_terrain` |
| 2 | 0.5 #1：`swap` 一併統一 | `test_swap_with_an_enemy_needs_the_displace_check`（`tests/engine/test_self_moves.py`：`maneuver: swap`、沒有 `AttackRolled`）、`test_the_preview_of_a_swap_skill_shows_the_displacement_check` |
| 3 | 成功率計算 | 第 2.2 節 |
| 3 | 預覽顯示成功率（API 與 vitest） | API：`tests/api/test_displace_api.py::test_the_preview_carries_the_success_chances`、`tests/api/test_routes.py`（預覽欄位集合）；引擎：`test_the_preview_shows_the_success_chance_of_an_ordinary_landing`（50%）、`test_the_preview_shows_the_deadly_landing_as_ten_percent`（10%）、`test_the_preview_of_a_pair_multiplies_the_enemy_chances`（36%）；vitest：`scenePreview.test.ts` 的 "displacing others"（標記、成功率、致命地形警示、互換總成功率、友方、Boss 說明）、`targeting.test.ts` 的 "teleporting and swapping others"（兩段選取、互換兩個方向、提示文字）、`actions.test.ts`（標籤）。**PM 瀏覽器驗收見第 6 節** |
| 4 | 示範技能裝進 build | `build_banisher`（放逐、虛空互換）：`tests/content/test_sim_builds.py`、`test_the_demo_skills_are_valid_and_rare`；`tests/content/test_coverage.py` 允許清單維持為空 |
| 4 | AI 使用紀錄（`trpg sim maps --seeds 5 --ally-build build_banisher`，10 張地圖 × 5 種子 ＝ 50 場） | 放逐 **16 次**（dark_forest 4、frozen_lake 5、lava_crossing 4、open_plain 1、ruined_fort 1、swamp 1），虛空互換 **2 次**（frozen_lake 1、open_plain 1）；測試：`test_the_ai_banishes_an_enemy_into_deadly_terrain`、`test_the_ai_does_not_banish_when_nothing_is_gained`、`test_the_ai_swaps_a_nearly_dead_ally_out_of_the_enemies_reach`、`test_the_ai_uses_the_displacement_skills_in_real_battles` |
| 4 | `check.py` 全過、重播一致 | `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（2165 passed）、client typecheck、vitest（106 passed）全部通過；重播：`test_an_ai_battle_with_banishments_replays`（frozen_lake 種子 0）、`test_an_ai_battle_with_a_void_swap_replays`（open_plain 種子 0），「重播驗證通過」 |

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/engine/test_self_moves.py::test_swap_with_an_enemy_needs_a_hit` → `…needs_the_displace_check` | 0.5 #1：`swap` 對敵人改用位移檢定，不再擲命中 |
| `tests/content/test_sim_builds.py` | `BUILD_IDS` 加入 `build_banisher`（14 個 build） |
| `tests/content/test_skill_rules_content.py` | `displace` 骨架核心多了 `teleport_target`、`swap_any` |
| `tests/cli/test_budget_cli.py` | 技能總數 94 → 96 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/19` → `/20` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 兩筆重錄（新增 2 個技能、`swap` 的說明文字改為位移檢定）；戰鬥類快照沒有變 |
| `tests/api/test_routes.py` | 預覽回應的欄位集合多了 `displace_checks`、`displace_permille` |

## 5. 新增的複雜度 noqa

沒有 C901、PLR0911、PLR0912、PLR0915。`skill_estimate` 加了第三種位置型技能後超過 PLR0911／PLR0912，我把傳送與跳躍、投擲與推倒、位移他人拆到 `_special_estimate`；`_candidates` 的兩段選取分派改成表（`_TWO_STAGE`）。唯一新增的是 **`# noqa: PLR0917`**（位置參數過多，不屬複雜度類）在 `utility._special_estimate`（8 個位置參數），理由同既有的 `skill_estimate`：同一組參數（狀態、單位、技能、動作、範圍、場景、權重、位置價值）要原樣傳遞，改成包裝物件只會多一層。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/20`**（本段只升一次）：新原語、新形狀、`UseSkill.second_target_id`、`unit_moved` 的 `teleported`、`maneuver_rolled` 的 `teleport`／`swap` 與 `resist_bonus`、核心規則兩個抵抗加成，以及 `swap` 對敵人改用位移檢定（`/19` 的紀錄重播 `swap` 結果不同）。

## 7. PM 瀏覽器驗收：「傳送他人」重現步驟

本機以 API 流程重現（同一個種子結果固定）；建立戰鬥：地圖 `lava_crossing`（熔岩渡口）、`hero_build: build_banisher`（放逐流）。主角 AP 3、移動 5、法力 40；放逐 AP 2、射程 5。

**情境 A（成功，丟進岩漿）— 種子 1**

1. 第 1 輪，主角在 **(0, 3)**；敵人：盜賊弓手1 (6, 4)、盜賊弓手2 (7, 2)、盜賊盾衛1 (6, 5)、盜賊盾衛2 (8, 5)（API 的實際座標；盜賊弓手2 是 `unit_0007`）。
2. 主角移動到 **(3, 1)**（消耗 5 點移動）。
3. 選技能「放逐」→ 第 1 段（紅框）點 **盜賊弓手2 (7, 2)** → 第 2 段（紅框是所有合法落點，含岩漿）點 **(4, 1)**（岩漿格）。
4. 預覽應顯示：被傳送的單位原位「傳」、(4, 1) 紅框「險」，「⚠ 傳送到致命地形：盜賊弓手2 要過極難的抵抗（抵抗 +10），成功率只有 30%；失敗時不會移動」。（英雄智力 16 對弓手有 +4 比例修正：30%；同級是 10%。）
5. 送出：d20=15 → 15 ＋ 4 ＋ 2 − 10 ＝ 11 ≥ 11，成功；「盜賊弓手2 被傳送到 (4, 1)」「掉進了岩漿！」「受到 26 點致命地形傷害，HP 26 → 0」「盜賊弓手2 倒下了」。

**情境 B（失敗）— 種子 0**

1. 第 1 輪，主角在 (0, 3)；移動到 **(1, 1)**（消耗 3）。
2. 放逐 → 點 **盜賊弓手2 (6, 1)** → 點 **(4, 1)**（岩漿）。
3. 送出：d20=1 → 失敗，盜賊弓手2 留在原地，只看到對抗紀錄。

**情境 C（成功）— 種子 2**：移動到 (2, 3)，放逐 → 盜賊弓手1 (6, 4) → (4, 1)，d20=16 成功、掉進岩漿。

**其他可看的：**一般格（成功率 50%／同級；預覽「位移檢定：X 成功率 N%（抵抗 +2）」）；對友方傳送預覽「傳送：友方不需檢定，必定成功」；`open_plain` 種子 0 的 AI 戰鬥有虛空互換（把快倒下的主角與隊友弓手互換）。選技能「虛空互換」時第 1 段點任一單位（紅框含主角與所有射程內的單位）、第 2 段點另一個單位。我沒有用瀏覽器實測畫面（由 PM 驗收），目前只有 vitest 與 API 測試覆蓋。

## 8. 待 PM 決定（最多 10 點）

1. **「位移檢定」的定義**：我以技巧動作與擊倒用的 `contest`（技能縮放屬性 vs 目標同屬性）統一三個原語；技能的推擊本身沒有獨立抵抗，所以「技能推擊的同一套抵抗」找不到更接近的對象。`swap` 因此不再擲命中；「調虎離山」（換位＋傷害）對敵人變成兩次獨立擲骰（換位的對抗、傷害的命中）。若希望換位與傷害共用同一次擲骰，要另外設計。
2. **抵抗加成數值**：敵人 +2、致命地形再 +8（共 +10），同級 60% → 50% → 10%；英雄對低智力敵人（修正 +4）致命地形為 30%。想要同級 15% 把 `teleport_lethal_resist_bonus` 改成 7；想固定在 10–15% 不受屬性影響，需要把對抗改成不吃比例修正（目前吃）。
3. **預算**：`teleport_target` 11 點、`swap_any` 12 點是為了讓「只有一個效果」的技能達到 70% 下限；致命地形的低成功率沒有折價（固定點數沒有成功機率維度）。若要「期望價值以低成功率計」需要新增預算欄位（例如依落點是否致命的係數）。全部是初值、未經模擬。
4. **Boss 免疫在 `swap_any` 規則上不會發生**：互換要求兩格都能站，致命地形不可站，所以沒有「Boss 被換進致命地形」的情況（3D-2 待決 #2 同理）；`swap_any` 的 Boss 照常檢定。
5. **兩個原語必須是技能唯一的效果**（schema）：沒有「傳送＋傷害」這類組合。要允許附帶效果需決定目標怎麼算（傳送前的位置？落點？）與命中判定要不要擲。
6. **友方可被傳送進致命地形**（必定成功，友軍誤傷，AI 不會這樣選）；施放者不能傳送自己（用既有的 `teleport`）。
7. **`teleported` 的細節**：不墜落、不觸發 `on_enter_surface` 被動、不觸發離開相鄰格的反應，但落點的陷阱與表面照常結算（規格 2B 的「落點互動照常結算」）；非 Boss 精英落在致命地形受最大 HP 比例傷害並移到安全格（既有規則），不免疫。
8. **`swap_any` 含多個敵人時全部擲出**（不在第一個抵抗成功時短路），紀錄看得到每一個；亂數用量固定，比較好重播與解釋。
9. **新增第 14 個 build `build_banisher`**；AI 價值全是初值：放逐 16 次／50 場、虛空互換只有 2 次／50 場（隊友受傷被包夾才用；`sim maps` 預設陣容的隊友很少落到 40% HP 以下）。致命地形的 AI 收益（擊倒權重 × 成功率）沒有特別壓低，要不要讓 AI 更積極或更保守看平衡階段。
10. **網頁互換第二段的點選優先**：第二段時點到另一個合法單位就直接送出（不會改選第一個），要改選請點同一個單位或按「重選單位」（提示文字已說明）；沒有用瀏覽器實測。

## 9. 代表性輸出

`uv run trpg battle --map lava_crossing --seed 7 --ally-build build_banisher`（連續一段，輸出第 119–135 行）：放逐流英雄用放逐把盜賊盾衛2 傳送到岩漿 (4, 1)；致命地形的抵抗總加成 −10，d20=17 剛好成功。

```
    放逐流英雄 受到 9 點物理傷害［骰 5］，HP 30 → 21
  盜賊弓手2 攻擊 放逐流英雄：d20=4 修正 +0 熟練 +2 = 6（目標 11）→ 失手
  盜賊弓手2 結束回合
— 放逐流英雄 的回合（AP 3，移動 5，法力 28/40）
  放逐流英雄 施放「放逐」（AP 2，法力 6，冷卻 3 回合）→ 影響 2 格
  放逐流英雄 對 盜賊盾衛2 使出傳送：d20=17 修正 +4 熟練 +2 抵抗 -10 = 13（目標 11）→ 成功
  盜賊盾衛2 被傳送到 (4, 1)
  盜賊盾衛2 掉進了岩漿！
    盜賊盾衛2 受到 27 點致命地形傷害，HP 27 → 0
  ＊ 盜賊盾衛2 倒下了！
  放逐流英雄 施放「咒印飛彈」（AP 1，法力 3）→ 影響 1 格
  放逐流英雄 以「咒印飛彈」攻擊 盜賊盾衛1：d20=14 修正 -1 熟練 +2 = 15（目標 11）→ 命中
  ⟳ 盜賊盾衛1 反應：格擋（耐力 −10）
    盜賊盾衛1 受到 6 點暗影傷害［骰 4］（格擋/加成 ×0.5），HP 32 → 26
  放逐流英雄 對 盜賊盾衛1 施加「被標記」（智力 16 vs 感知 10）：d20=6 修正 +3 熟練 +2 = 11（目標 11）→ 施加成功
  盜賊盾衛1 獲得狀態「被標記」（1 回合）
  放逐流英雄 從 (3, 5) 移動到 (4, 5)（消耗 1 移動）
  放逐流英雄 結束回合
```

另：`open_plain` 種子 0 的虛空互換（沒有敵人，不檢定）：

```
  放逐流英雄 施放「虛空互換」（AP 2，法力 5，冷卻 3 回合）→ 影響 2 格
  放逐流英雄 交換位置，換到 (4, 4)
  標準隊友（弓手） 交換位置，換到 (3, 1)
```
