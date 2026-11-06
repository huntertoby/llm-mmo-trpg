# Phase 3D-2 報告：自身位移（`dash`、`leap`、`swap`）

## 1. commit

| commit | 內容 |
|---|---|
| 9f39d4a | 三個原語（schema、選取、結算、效果處理器、預算、骨架）、事件 `unit_dashed`、`unit_moved` 新 `mode`、紀錄文字、AI（`leap`）、4 個示範技能、新 build `build_charger`、隨機組合器（`dash` 置頂）、`LOG_FORMAT` `/19`；`tests/engine/test_self_moves.py` 的引擎部分 |
| c110252 | 預覽 `Preview.moves`／API `PreviewOut.moves`／網頁標記與預覽文字／OpenAPI 與 `schema.d.ts` 重新產生／vitest／互動測試（連段條件、`on_move`、預覽、API、紀錄文字、組合器、重播、AI 使用） |
| c1e374a | 修正 c110252 漏掉的兩處（API 預覽欄位集合測試多了 `moves`；`test_self_moves.py` 的 mypy 型別） |
| （本報告） | 報告 |

過程中玩法 PM 在同一個資料夾 commit 了 `docs/`（3a019e1、ab16301 等）。**我誤用一次 `git commit --amend` 把測試檔併進了 ab16301，隨即以 `git reset --mixed ab16301` 還原**：ab16301 的內容與雜湊不變，我的修正獨立成 c1e374a；沒有 stash、沒有 push。

## 2. 交付項目

### 2.1 原語（`content/skill_primitives.yaml`、`src/trpg/engine/skills/mobility.py`）

| 原語 | 選取 | 結算 |
|---|---|---|
| `dash` | 形狀只能 `single`，目標是單位（物件、自己都不行）。路徑：從施放者到目標 **相鄰格** 的最短步行路徑（高度、地形、恐懼照步行規則；**不經過任何單位**，含友方），路徑成本（爬升 +1）≤ 技能射程；已經相鄰時路徑只有起點（不移動、仍可施放）。定身或倒地時 `skill_problem` 回報不能用 | **一律最先結算**（schema 要求它是第一個效果、一個技能最多一個位置原語），在命中判定之前：發 `unit_dashed`（路線），一步一步 `move_unit(mode=dash)`——每一步前先給相鄰敵人藉機攻擊／`enemy_leaves_adjacent` 反應技的機會；陷阱、墜落、表面照常；被定身／擊倒／暈眩／倒下就停。走完後把影響範圍的原點改成施放者的新位置（推擊由這裡往外推）。目標不在相鄰格（被擋下、目標倒下）→ `effect_fizzled`（`dash_blocked`），**其餘效果全部不結算**。算 `moved_this_turn`、觸發 `on_move` 被動 |
| `leap` | 形狀 `ground_tile`；落點：地圖內、射程內、不是原地、可站立且非致命、沒有單位、與起點高度差 ≤ 1 層；起點到落點的 Bresenham 直線上不能有：牆壁、同時 `blocks_move` 與 `blocks_sight` 的物件（石柱、土牆、枯樹）、比兩端都高出超過 1 層的地形。**不要求視線**，單位與低矮物件（低牆、木箱）不擋。定身或倒地時不能用 | `move_unit(mode=leap)`；不呼叫藉機攻擊、不算 `moved_this_turn`、不觸發 `on_move`；落點的陷阱與表面照常結算（和 `teleport` 不同，傳送不觸發陷阱） |
| `swap` | 形狀 `single`、目標是單位（不能是自己）；`affects` 只能 `enemies` 或 `allies`（不能 `all`／`self`／`tiles`）；兩格都要 `is_standable`。對敵人（`affects: enemies`）要 **命中判定**（沿用一般技能的攻擊擲骰），失手不換；友方自動成功 | 新效果 `swap_units`：兩個單位各自 `arrive`（`mode=swap`）——表面、陷阱、墜落、致命地形、源泉、撤離照常；任一格不能站（結算時再檢查）→ `effect_fizzled`（`swap_blocked`）。不算 `moved_this_turn`、不觸發 `on_move` |

- 三者都只能用在主動技能（反應技、姿態、被動、陷阱、修正規則的命中後效果都不行；`SkillDef._check_self_moves`）。
- 預算（初值，未經模擬）：`dash` 3、`leap` 3、`swap` 4（皆結構型、稀有以上、固定點數）。`dash` 標為 `harmful: true`，讓 `strike` 骨架（附帶限有害原語）也放得下。機制標籤 `displace` 涵蓋三者（`mechanics._DISPLACE`）。
- 骨架：`displace` 的附帶原語加 `dash`、核心加 `leap`、`swap`；`strike` 的附帶原語改成明列清單 `[apply_status, push, pull, knock_prone, dash]`（等於原本的 fallback 加 `dash`）。
- 隨機組合器：`dash` 可被抽到（`displace`、`strike`），並在組好效果後移到第一個（`_dash_first`，旋鈕索引一併位移）；`leap` 與 `swap` 只給手寫技能（`_HAND_WRITTEN_PRIMITIVES`）——第一次沒加時，組合器抽出的 `leap` 技能帶著「目標需有狀態」的條件，在落點是空格時永遠不能施放，`test_skill_fuzz` 抓到了。
- 事件：新增 `unit_dashed`（`unit_id`、`target_id`、`path`）；`MoveMode` 加 `dash`／`leap`／`swap`。`LOG_FORMAT` 升為 **`trpg-battle-log/19`**（本段只升一次）。
- 紀錄文字：`unit_dashed` 整段顯示（`➤ X 衝向 Y：(a)→(b)→(c)`），衝鋒逐步的 `unit_moved` 靜默；`leap`「跳躍到」、`swap`「交換位置，換到」；`effect_fizzled` 新顯示 `dash_blocked`／`dash_no_path`／`swap_blocked`（其他原因仍靜默）。

### 2.2 使用者指定的組合：衝鋒 ＋ 傷害 ＋ 擊退 2 格

`content/skills/skill_tiger_charge.yaml`「猛虎衝撞」：`displace` 骨架、稀有、武器技（近戰）、AP 2、射程 4、`effects: [dash, damage ×0.8, push 2]`、法力 5、冷卻 3。預算 76.6%（合格），骨架占比通過。結算順序：衝鋒 → 命中判定 → 傷害 → 推擊（撞牆／撞單位照 3C-3a 觸發撞擊）。

### 2.3 示範技能與 build

| 技能 | 原語 | 備註 |
|---|---|---|
| 猛虎衝撞 `skill_tiger_charge` | `dash`＋`damage`＋`push` | 使用者指定組合 |
| 騰躍 `skill_vault_leap` | `leap`＋自身 `empowered` | 預算 85.8% |
| 調虎離山 `skill_decoy_swap` | `swap`（敵人，需命中）＋`damage` ×0.4 | 預算 83.4% |
| 護衛換位 `skill_guard_swap` | `swap`（友方）＋友方 `guarded` | 預算 98.1% |

既有 12 個 build 的主動欄位只有 `build_guardian`（5/6）有空位且該 build 已被技能數與 AI 測試固定，所以 **新增 `build_charger`（衝鋒流，第 13 個 build）**：單手劍、力量 16、上述四招＋颶風踢＋盾擊（6 個主動）。

### 2.4 預覽與網頁

- `Preview.moves`（`MoveInfo`：`kind`、`unit_id`、`other_id`、`path`，取自最多後果模擬）→ API `PreviewOut.moves`（`MoveOut`）；衝鋒的每一步不再重複列成「移動」連鎖結果（改由 `moves` 顯示），被擊退的單位與撞擊傷害沿用既有的 `certain`／`possible`／`collisions`。
- 網頁：`scenePreview.ts` 新增標記 `dash_path`／`dash_end`（衝）／`leap_to`（躍）／`swap`（換）與預覽文字三行（衝鋒路線、跳躍落點、交換的兩格）；`BattleRenderer` 繪製；`animation.ts` 補 `dash`（60 ms）、`leap`（220 ms）、`swap`（180 ms）的動畫速度；`types.ts` 的 `MoveMode`。

### 2.5 AI

沿用預覽評分（規格的最簡近似）；唯一的程式改動是 `skill_estimate`：含 `leap` 的技能與 `teleport` 同樣用「施放者放到落點後的位置價值變化」估計（否則跳躍的影響範圍沒有單位，永遠不會被選為候選）。`dash`（影響範圍有敵人）與 `swap`（敵人＋3、友方有 `guarded` 增益＋2）不需要特別處理。

## 3. 驗收條件逐條（規格 2.1）

| # | 結果 | 證據 |
|---|---|---|
| 1 | 三個原語的合法與不合法例子 | `tests/engine/test_self_moves.py`：`test_dash_must_be_the_first_effect`、`test_a_skill_has_at_most_one_self_move`、`test_self_moves_are_active_only[×3]`、`test_primitive_shape_and_affects_restrictions`（schema）；`test_dash_is_out_of_range_when_the_path_is_longer_than_the_reach`（路徑比射程長）、`test_dash_goes_around_an_obstacle_when_the_reach_allows`、`test_dash_does_not_pass_through_any_unit`、`test_dash_is_unavailable_while_rooted_or_prone`、`test_the_dash_target_must_be_a_unit`；`test_leap_landing_rules`（有單位／深淵／原地／超出射程／高度差）、`test_leap_ignores_low_terrain_but_not_pillars_or_walls`、`test_leap_ignores_line_of_sight_but_candidates_exclude_illegal_tiles`、`test_leap_is_unavailable_while_rooted`；`test_swap_cannot_target_yourself_and_respects_affects`、`test_swap_needs_both_tiles_to_be_standable`（交換格不能站）、`test_swap_with_an_enemy_needs_a_hit`（對敵失手＝不換） |
| 2 | 落點互動 | 衝鋒經過陷阱：`test_dash_triggers_a_trap_on_the_way_and_a_rooting_trap_stops_it`；跳到油上與落點陷阱：`test_leap_lands_in_oil_and_a_trap_triggers_on_landing`；換位：`test_swap_puts_an_enemy_into_the_surface_the_caster_was_standing_in`（火焰）、`test_swap_lands_the_enemy_on_an_enemy_trap_of_the_casters_team`（陷阱）、`test_swap_onto_a_ledge_makes_the_falling_unit_take_fall_damage`（墜落）。**「把敵人換到致命地形」做不到：見待決 #2** |
| 3 | 反應：衝鋒會被藉機攻擊、跳躍不會 | `test_dashing_away_from_an_adjacent_enemy_triggers_an_opportunity_attack`、`test_leap_does_not_trigger_opportunity_attacks`（同一情境走路會被攻擊） |
| 4 | 使用者指定組合 | schema、骨架、預算：`trpg skills budget skill_tiger_charge`（76.6%，驗證通過）、`trpg content check`（94 個技能通過）；引擎：`test_charge_damage_and_push_into_a_wall_triggers_a_collision`（衝鋒→傷害→推 2 格撞牆，事件順序 `UnitDashed` < `AttackRolled` < `Collided`、傷害依序 `attack`、`collision`×2）、`test_charge_pushes_the_target_away_from_the_new_position`（推擊原點是衝鋒後的位置）、`test_a_blocked_charge_resolves_nothing_after_it`（被陷阱定身擋下：傷害、擊退、撞擊都不結算）；組合器：`test_the_composer_can_draw_displace_with_dash_and_dash_is_always_first`（種子 454、476 抽到 `dash`＋`push`＋`damage`）；預覽：`test_the_preview_shows_the_charge_route_the_landing_and_the_collision_damage`。**PM 瀏覽器實測的重現步驟見第 6 節** |
| 5 | 手寫技能、AI、vitest、`check.py`、重播 | 4 個手寫技能都裝在 `build_charger`（`tests/content/test_coverage.py` 允許清單維持為空）；AI 使用次數見下表；vitest 96（原 92，新增 4：`scenePreview.test.ts` 3、`log.test.ts` 1）；`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（2096 passed）、client typecheck、vitest 全部通過；重播：`test_charger_battles_replay_exactly[×3]`、`trpg battle --map ruined_fort --ally-build build_charger --seed 1 --log-json … ` → `battle replay`：「重播驗證通過：85 個動作、248 個事件」 |

其他互動（規格 2 節文字）：`test_a_dash_satisfies_moved_this_turn_but_standing_still_does_not`、`test_dash_triggers_on_move_passives_but_leap_and_swap_do_not`、`test_the_api_preview_carries_the_moves`、`test_the_narrative_describes_dashes_leaps_and_swaps`、`test_a_blocked_charge_is_explained_in_the_log`、`test_the_ai_uses_every_self_move_somewhere`。

### AI 使用紀錄

`trpg sim maps --seeds 5 --ally-build build_charger`（10 張地圖 × 5 個種子 ＝ 50 場，主角用 `build_charger` ＋ 2 名標準隊友）：

| 技能 | 次數（50 場合計） |
|---|---|
| 猛虎衝撞（`dash`） | 42 |
| 騰躍（`leap`） | 34 |
| 護衛換位（`swap`，友方） | 29 |
| 調虎離山（`swap`，敵人） | 19 |

（各地圖「每場次數 × 場數」加總取整；預設陣容的 `sim maps --seeds 5` 沒有這些技能，異常類別與 3D-1 一致：`one_shot`、`boss_burst`。）

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_sim_builds.py` | `BUILD_IDS` 加入 `build_charger`（13 個 build；測試名稱 twelve → thirteen） |
| `tests/content/test_skill_rules_content.py` | `displace` 骨架核心多了 `leap`、`swap`，附帶多了 `dash` |
| `tests/cli/test_budget_cli.py` | 技能總數 90 → 94 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/18` → `/19` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 兩筆重錄（新增 4 個技能）；戰鬥類快照沒有變 |
| `tests/api/test_routes.py` | 預覽回應的欄位集合多了 `moves` |

## 5. 新增的複雜度 noqa

無（C901、PLR0911／0912／0915 都沒有新增；`dash` 拆成 `dash`／`_dash_walk`／`_dash_continues`／`_dash_failed`，`leap_problem` 拆出 `_landing_problem`，`_candidates` 拆出 `_tile_candidates`）。測試檔裡有函式內匯入的 `# noqa: PLC0415`，不屬於複雜度類。

`LOG_FORMAT`：**升為 `/19`**（見 2.1）。

## 6. PM 瀏覽器驗收：「衝鋒 ＋ 傷害 ＋ 擊退撞牆」重現步驟

- 建立戰鬥：地圖 `dark_forest`（黑暗森林）、`hero_build: build_charger`（不指定 `ally_builds`，補 2 名標準隊友）、種子 **0**。
- 第 1 輪，主角（衝鋒流英雄）在 **(0, 3)**，我方標準隊友（戰士）(1, 4)、標準隊友（弓手）(2, 2)；敵人：盜賊1 (7, 3)、盜賊2 (8, 5)、**盜賊3 (5, 3)**、盜賊弓手 (6, 1)。
- 步驟：① 移動到 **(3, 2)**（5 點移動花 4 點；路徑 (0,3)→(0,2)→(1,2)→(2,2)→(3,2)，可穿過隊友）；② 選技能「猛虎衝撞」；③ 點敵人 **盜賊3 (5, 3)**。
- 預覽應顯示：衝鋒路線 (3,2)→(4,2)→(5,2)、命中率 55%、傷害 2–8、撞擊傷害最多 12。
- 本機以 API 流程重現的結果（種子 0 固定）：命中（d20=11，盜賊3 格擋 ×0.4），衝到 (5, 2)，受到 5 點傷害後被往南推，(5, 4) 是牆，「撞上了牆壁！少走 2 格，受到 2 次撞擊」（3＋6 點），HP 30 → 16。
- 其他可看的情境：`ruined_fort` 種子 1 第 1 輪移動到 (5, 4) 後對盜賊 (8, 3) 衝鋒（少走 1 格）；`open_plain` 種子 2 第 1 輪移動到 (2, 1) 後衝鋒 (4, 3)。

## 7. 待 PM 決定

1. **`swap` 對敵人用「命中判定」**（沿用一般技能的攻擊擲骰，失手不換），沒有另做屬性對抗；規格寫「命中判定或對抗」，3D-2b 則寫「位移對抗」。3D-2b 實作時要不要統一成同一種抵抗方式，請 PM 決定。
2. **「把敵人換到致命地形」做不到**：交換要求兩格都能讓對方站上去，而單位所在的格子永遠不是致命地形（深淵、岩漿不可站立；木橋架在上面時也不致命），所以「換到致命地形」在規則上不可能發生。我改以火焰表面、我方陷阱、墜落（高低差）來示範落點互動；處理器對不能站的格子會 `effect_fizzled`（`swap_blocked`，有測試）。若 PM 要「真的丟進深淵」那是 3D-2b 的 `teleport_target`（允許致命落點）。
3. **`dash` 的路徑不經過任何單位（含友方）**：規格寫「不經過單位」，步行本身可以穿過友方，我取較嚴格的解讀；已經在目標身旁時仍可施放（不移動）。
4. **定身或倒地時 `dash`／`leap` 不能用**（`skill_problem`）：規格沒寫；保守起見比照步行，傳送（`teleport`）本來就不受影響，維持原狀。
5. **衝鋒被擋下時其餘效果全部不結算**（包含對自己的效果）：規格寫「後續效果若目標不在射程內就不結算」，我統一成「目標不在相鄰格」就全部不結算，並在紀錄顯示「衝鋒被擋下」。
6. **`leap` 的詮釋**：落點與起點高度差 ≤ 1；路徑上的牆、同時擋行動與視線的物件、高出兩端超過 1 層的地形會擋，單位與低矮物件（低牆、木箱、岩礫）不擋；不要求視線；落點的陷阱與表面照常觸發（與 `teleport` 不同）。數值與詮釋若與玩法 PM 想的不同請告知。
7. **新增第 13 個 build `build_charger`**（衝鋒流）：既有 build 的主動欄位已滿（見 3D-1 待決 #10）；3C-6 整理 build 時可再決定要不要併入既有 build。
8. **預算初值**：`dash` 3、`leap` 3、`swap` 4；`dash` 標為 `harmful: true`（讓 `strike` 骨架也放得下，隨機組合器因此會抽到「突進打擊」）。猛虎衝撞 76.6%、騰躍 85.8%、調虎離山 83.4%、護衛換位 98.1%，皆未經模擬。
9. **隨機組合器**：`dash` 會出現在 `displace` 與 `strike`（組好後移到第一個）；`leap` 與 `swap` 只給手寫技能。`strike` 骨架的附帶原語改為明列清單（行為等同原 fallback ＋ `dash`），但因抽籤池多了 `dash`，既有種子抽到的 `strike` 技能可能不同（`skills_list` 快照不受影響，因為快照只含手寫技能）。
10. **AI 沒有「先走位再衝鋒」的規劃**（3D-1 待決 #7 的延伸）：衝鋒只在目前位置就在射程內時被評分；衝勢劈砍（`moved_this_turn`）仍幾乎不被使用。`tiger_charge` 在 sim 中命中率偏低（樣本小，未調整）。

## 8. 代表性的 CLI 輸出節錄

`trpg battle --map ruined_fort --ally-build build_charger --seed 1`（連續的一段：衝鋒＋傷害＋擊退撞牆，接著調虎離山把敵人換到高處下方、墜落）：

```
— 衝鋒流英雄 的回合（AP 3，移動 5，法力 9/24）
  衝鋒流英雄 的「猛虎衝撞」冷卻結束
  衝鋒流英雄 施放「猛虎衝撞」（AP 2，法力 5，冷卻 3 回合）→ 影響 1 格
  ➤ 衝鋒流英雄 衝向 盜賊弓手2：(7, 3)→(7, 4)→(8, 4)→(8, 5)
  衝鋒流英雄 以「猛虎衝撞」攻擊 盜賊弓手2：d20=17 修正 +0 熟練 +2 高度 -2 = 17（目標 11）→ 命中
    盜賊弓手2 受到 10 點物理傷害［骰 8］（格擋/加成 ×0.8），HP 24 → 14
  盜賊弓手2 被推到 (8, 7)
  盜賊弓手2 無法移動到 (8, 8)
  盜賊弓手2 撞上了牆壁！少走 1 格，受到 1 次撞擊
    盜賊弓手2 受到 4 點撞擊物理傷害［骰 4］，HP 14 → 10
  衝鋒流英雄 施放「調虎離山」（AP 1，法力 3，冷卻 3 回合）→ 影響 1 格
  衝鋒流英雄 以「調虎離山」攻擊 盜賊弓手2：d20=11 修正 +0 熟練 +2 高度 -2 = 11（目標 11）→ 命中
  衝鋒流英雄 交換位置，換到 (8, 7)
  盜賊弓手2 交換位置，換到 (8, 5)
  盜賊弓手2 從 2 層高處跌落！
    盜賊弓手2 受到 2 點墜落傷害，HP 10 → 8
    盜賊弓手2 受到 4 點物理傷害［骰 7］（格擋/加成 ×0.4），HP 8 → 4
  衝鋒流英雄 從 (8, 7) 移動到 (7, 5)（消耗 3 移動）
  衝鋒流英雄 結束回合
```
