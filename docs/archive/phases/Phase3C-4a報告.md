# Phase 3C-4a 報告：源力 ＋ 傳說定位 ＋ `grant_ap`、`reset_cooldown`、`cheat_death`

## 1. commit

| commit | 內容 |
|---|---|
| 951ffec | 引擎與內容：源力（`UnitState.source`、`UnitSpawn.source`、`core.yaml` 的 `source_max`／`source_min_at_start`）、源泉格（`MapDef.source_wells`、`BattleState.source_wells`，放在 `ruined_fort`、`dark_forest`）、擊倒精英 +1、`SourceChanged` 事件、`battle_result()`；傳說 schema（`SkillCost.source`）、三個改寫規則型原語與狀態 `undying`、預算折抵、驗證器的冷卻規則、3 個手寫傳說與 build 裝備、AI 評分、組合器不產生傳說、`LOG_FORMAT` `/14`；測試 |
| 540591c | AI 數值修正：實戰中 AI 從來不施放傳說（見 4.6），改成「給予的 AP 不扣這次動作花的 AP」並提高初值 |
| 12ede21 | CLI：HUD 顯示「源力 n/3」、網格與 `map show` 以 `$` 標源泉格、新事件與源力代價的紀錄文字、技能卡片與列表顯示源力成本；CLI 快照重錄 |
| bdbcd60 | API 與前端：`UnitView.source／source_max`、`BattleView.source_wells`、`SkillCard.source_cost`、重新產生 `openapi.json`／`schema.d.ts`；HUD 源力數字、源力不足的技能按鈕停用並顯示原因；vitest 1 個、API 測試 3 個 |
| 8454093 | 測試小整理（匯入移到檔頭） |
| 516f2ec | 組合器排除改寫規則型原語（光環骨架的核心含它們，明確指定史詩光環時曾抽到）；測試 1 個 |
| （本報告） | 報告 |

## 2. 交付項目

### 2.1 源力（6.1）

- `UnitState.source`（整數），上限 `core.yaml` 的 `source_max: 3`、我方保底 `source_min_at_start: 1`（`CoreRules` 有預設值，舊紀錄的規則包也能讀）。
- `UnitSpawn.source: int | None`；開場值由 `trpg.engine.setup.starting_source` 計算：敵人一律 0；我方 `clamp(max(值 or 保底, 保底), 0, 上限)`。地圖事件的援軍也是 0。
- 事件 `SourceChanged`（`unit_id`、`before`、`after`、`reason: skill | well | kill_elite`，另有 `skill_id`／`pos`／`other_id`）。全部經過 `trpg.engine.source.change_source`（截斷在 0 與上限之間）。
- **源泉格做成地圖資料 `source_wells: [[x, y], ...]`**（不是物件）：物件有 HP、會擋路、會被推動與點燃，源泉不需要這些；做成座標清單最單純，也不影響卡路檢查。戰鬥狀態 `source_wells`（依 (y, x) 排序，可序列化、可重播），我方單位 **以任何方式抵達**（走、被推、傳送）時 +1 並移除（`effects/handlers.arrive`，在致命地形判定之後）。敵方踏上去不取用。schema 檢查：在地圖內、不與物件重疊、不在起始區、不重複。
  - `ruined_fort`：(4, 1)、(4, 8)；`dark_forest`：(5, 0)、(4, 9)（兩軍之間、南北兩側）。
- 擊殺精英：沿用既有的 `elite` 標籤（`bandit_boss` 已經有，也是致命地形用的同一個標籤），**沒有另加 `elite: true` 欄位**（見待決 #1）。`_damage` 擊倒帶 `elite` 標籤的單位時，傷害來源若是仍在場上的我方單位則 +1。
- 戰鬥結果：`trpg.engine.results.battle_result(state) -> BattleResult`（`ended`、`winner`、`end_reason`、`round`、`allies: tuple[AllyResult]`，每個我方單位的 `template_id`、HP、倒下／撤離與 **剩餘 `source`**；`source_of(template_id)` 方便 3-5 寫回存檔）。由 `trpg.engine` 匯出。3-5 只要在建立 `UnitSpawn` 時填 `source=存檔值`、戰後讀 `battle_result(...).source_of(...)` 即可（0.4）。

### 2.2 傳說定位（6.2）

- `SkillCost.source: int | None`（1–2）。schema（`SkillDef._check_legendary`）：傳說必須有、非傳說不能有、只有主動技能可以有。
- 「傳說必須含 1 個改寫規則型原語或修正規則」是跨檔案檢查（要看原語的 `category`）：`skill_problems` 的 `_legendary_problems`，載入內容庫與驗證器（`reference`）都會擋。
- 驗證器 `cap.rule_rewrite_cost`：有 `cost.source` 時改看 `skill_budget.yaml` 的 `rule_rewrite_min_cooldown_with_source: 2`（或每場一次）；沒有源力時仍是冷卻 ≥ 4。每技能最多 1 個改寫規則型原語（`max_rule_rewrite: 1`，沿用）。
- 預算折抵：`allowance.source_per_point: 250`‰、`source_cap: 500`‰（仍受 `total_cap: 500` 截斷）。初值，未經模擬。
- 引擎：`resource_problem` 檢查「源力不足：需要 n，目前 m」（`legal_actions` 也因此不列出）；施放時 `SkillUsed.source` 記錄花費，之後發出 `SourceChanged(reason=skill)`。
- 隨機組合器：傳說需要手寫的源力代價與改寫規則型原語，**組合器不再產生傳說**——不指定稀有度時抽到傳說改為史詩（其他種子結果不變），指定 `rarity="legendary"` 時拋出 `ComposeError`（見待決 #3）。

### 2.3 三個改寫規則型原語（6.3）

`content/skill_primitives.yaml`：`category: rule_rewrite`、`min_rarity: epic`、只能對自己或友方（`forbid_affects`）。結算在 `trpg.engine.rewrites`（新模組）與解譯器的 `_Cast.rewrite`。

| 原語 | 實作 | 點數（初值） |
|---|---|---|
| `grant_ap`（`amount` 1–2） | 目標是行動者：立刻加 AP，上限 ＝ `ap_per_turn ＋ ap_carry_max`（4），超過的不保留；目標不在自己的回合：存進 `UnitState.ap_pending`，它下次回合開始時加上（同一上限）。同一單位 **每輪** 最多被給一次（`ap_granted_round`），之後的給予發出 `effect_fizzled(already_granted)`。事件 `ApGranted(amount, ap_after, deferred)` | 4／AP |
| `reset_cooldown`（`which: all | tag`、`tag`） | 目標友方的冷卻歸零（每個發出 `SkillCooldownChanged(remaining=0)`）；不重置帶 `cost.source` 的技能、不重置這個技能本身、施放者自己永遠不受影響（範圍技包含自己也一樣）；`tag` 以 `modifiers.effective_tags` 比對（含修正規則加上的標籤）。全部對象都沒有可重置的冷卻時 `effect_fizzled(no_cooldown)` | 7 |
| `cheat_death`（`duration` 1–2） | 對目標施加 `undying`（不擲抵抗）。`statuses.yaml` 新狀態 `undying`（預設 2 回合、`turn_end` 倒數、有益、新旗標 `prevents_death`、沒有 `budget_points`，只能由此原語施加）。`_damage` 讓 HP 降到 0 時改為 1，發出 `DeathCheated(prevented)` 與 `StatusRemoved(reason=spent)`。**墜落（`cause: fall`）與致命地形（`deadly_terrain`／`mode: lethal`）照樣生效** | 8 |

- 光環骨架（`aura`）的核心原語加入這三個（不必新增骨架）；隨機組合器排除 `category: rule_rewrite` 的原語（`composer_parts._composable`），只有手寫技能使用。
- AI（`trpg.engine.ai.utility`）：`_supports` 認得三個原語（還沒被給過 AP／有可重置的冷卻／還沒有不死），所以會被列為候選；評分 `_rewrite_gains`：給予的 AP × `ap_points`（給友方再 × 600‰，所以優先給自己）、重置的冷卻回合 × `cooldown_points`、不死 × `undying_points` × 目標已損失 HP 比例（滿血 0）、每點源力扣 `source_points`，全部 × 行為模式的 `damage` 權重。數值在 `content/ai_profiles.yaml` 的 `rewrite:`（初值）。

### 2.4 手寫傳說（全部 T1、AP 1、法術技、任何武器、光環骨架）

| 技能 | 效果 | 代價 | 預算 | 裝備 |
|---|---|---|---|---|
| 時隙湧流 `skill_time_surge` | 自己立刻 +2 AP | 源力 1、冷卻 2 | 84.7% | build_ranged |
| 重振號令 `skill_rallying_cry` | 單體友方（射程 4）冷卻全部歸零 | 源力 1、冷卻 3 | 71.4% | build_support |
| 不滅誓約 `skill_undying_oath` | 單體友方或自己（射程 3）不死 2 回合 | 源力 2、冷卻 3 | 76.2% | build_healer |

### 2.5 CLI、API、前端（6.4）

- CLI：單位表「HP … 法力 … 源力 2/3 耐力 …」（只有我方；敵方一律 0 不顯示）；網格與 `trpg map show` 以 `$` 標源泉格並列入圖例；紀錄文字：`✦ X 汲取了源泉 (4, 1)：源力 1 → 2，源泉消失了`、`✦ X 花費源力：源力 2 → 0`、`✦ X 擊倒了 盜賊頭目，獲得源力：…`、`X 獲得 2 AP（現在 4 AP）`、`✦ X 的「不死」擋下了致命傷害，HP 留在 1`；`施放「…」（AP 1，冷卻 3 回合，源力 2）`；`skills list／show` 的代價含「源力 n」，效果文字涵蓋三個原語。
- API：`UnitView.source`、`source_max`；`BattleView.source_wells`（雙方都看得到）；`SkillCard.source_cost`（`/api/skills/{id}`）。源力不足的 `use_skill` 回 400，`detail` 為「源力不足：需要 1，目前 0」。
- 前端：HUD 多一個「源力 n/3」小方塊；技能按鈕在源力不足時停用、`title` 顯示「源力不足：需要 n，目前 m」（`targeting.skillButtons`，冷卻中優先）。源泉格在畫布上 **沒有畫**（見待決 #8）。

## 3. 驗收條件逐條

1. **源力**：`tests/engine/test_source.py`
   - 開場值 `None`／0／1／2／3／5 → 1／1／1／2／3／3、敵人給 3 仍為 0：`test_starting_source_uses_the_floor_and_the_cap`（參數化 6 個）；保底與上限讀 `core.yaml`：`test_the_floor_and_cap_come_from_core_rules`。
   - 源泉格取得後消失、`SourceChanged(reason=well)`：`test_an_ally_entering_a_well_gains_one_source_and_the_well_disappears`；路過也算、已滿仍取走且不超過上限：`test_a_well_walked_through_counts_and_a_full_unit_still_takes_it`；敵人不取用：`test_an_enemy_does_not_take_a_well`；序列化：`test_source_wells_survive_serialization_and_replay_state`；地圖驗證：`test_source_well_placement_is_validated`、正式地圖 `test_shipped_maps_with_source_wells`。
   - 擊殺精英 +1：`test_downing_an_elite_gives_the_killer_one_source`；一般敵人不給：`test_downing_a_normal_enemy_gives_nothing`；內容中只有 `bandit_boss`：`test_only_bandit_boss_is_an_elite_in_content`。
   - 花費與事件順序：`test_casting_a_legendary_spends_source`；戰鬥結果帶出剩餘源力：`test_battle_result_reports_remaining_source_for_allies`。
   - 紀錄文字：`tests/narrative/test_events_text.py::test_source_and_rewrite_events_read_in_chinese`。
2. **傳說 schema**：`tests/content/test_legendary_schema.py`——缺 `cost.source`：`test_a_legendary_without_source_cost_is_rejected`；非傳說帶 `cost.source`：`test_a_non_legendary_with_source_cost_is_rejected`（普通／稀有／史詩）；沒有改寫或修正規則：`test_a_legendary_without_a_rule_rewrite_or_modifier_is_rejected`；另有 1–2 的範圍、只有主動技能、冷卻 ≥ 2（花源力）與 ≥ 4（不花）、每技能最多 1 個改寫規則型、預算折抵：`test_source_cost_is_one_or_two`、`test_only_active_skills_can_spend_source`、`test_source_relaxes_the_rule_rewrite_cooldown`、`test_a_non_legendary_rule_rewrite_still_needs_cooldown_four`、`test_at_most_one_rule_rewrite_per_skill`、`test_the_source_allowance_is_part_of_the_budget`。
3. **三個原語的規則與邊界**：`tests/engine/test_rewrites.py`
   - `grant_ap`：立刻生效 `test_grant_ap_gives_the_caster_ap_immediately`；超過上限捨去 `test_grant_ap_above_the_turn_cap_is_lost`；**每輪一次**（第二次 `already_granted`、下一輪又可以）`test_grant_ap_only_once_per_unit_per_round`；給友方延到它的回合並受上限 `test_grant_ap_to_an_ally_waits_for_their_turn_and_respects_the_cap`；不能對敵 `test_grant_ap_cannot_target_enemies`。
   - `reset_cooldown`：**不重置源力技能**、不重置自己這招、施放者不受影響 `test_reset_cooldown_clears_ally_cooldowns_except_source_skills_and_itself`；`which: tag` `test_reset_cooldown_by_tag`；沒有冷卻或範圍含自己 `test_reset_cooldown_on_self_or_without_cooldowns_fizzles`；參數檢查 `test_reset_cooldown_needs_which_and_tag_rules`。
   - `cheat_death`：施加 `test_cheat_death_applies_undying_to_an_ally`；**擋下致命傷害一次**（HP 1、`DeathCheated`、`spent`，第二擊倒下）`test_undying_blocks_lethal_damage_once`；墜落與致命地形不擋 `test_undying_does_not_stop_falls_or_deadly_terrain`；非致命不消耗 `test_undying_does_not_trigger_on_non_lethal_damage`。
   - AI：有源力時施放、沒有源力時不施放 `test_the_ai_casts_the_ap_legendary_on_itself_when_it_has_source`；滿血不給不死、受傷的隊友才給 `test_the_ai_saves_undying_for_a_wounded_ally`。
4. **源力不足不能施放（中文錯誤）**：引擎 `tests/engine/test_source.py::test_not_enough_source_is_rejected_in_chinese`（不在 `legal_actions`、`IllegalActionError`「源力不足：需要 2，目前 1」）；API `tests/api/test_source_api.py::test_casting_without_source_is_400_in_chinese`（400、`detail` 含「源力不足：需要 1，目前 0」、狀態不變）；前端 `targeting.test.ts` 的「disables a legendary when the hero lacks source and says how much is needed」。API 視圖與卡片：`test_views_carry_source_and_wells`、`test_skill_card_has_the_source_cost`。
5. **至少 2 個手寫傳說；`check.py` 全過；重播一致**：3 個傳說（2.4），`test_the_demo_legendaries_are_valid_equipped_and_cover_each_primitive`（驗證、預算、裝備、涵蓋三個原語）；`tests/content/test_coverage.py` 允許清單維持為空（`undying` 由 `cheat_death` 間接施加）。`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**1865 passed**）、client install／typecheck／vitest（**76**）全部通過。重播：
   - `trpg battle --map ruined_fort --seed 4 --ally-build build_healer --log-json …` → `battle replay`：「重播驗證通過：133 個動作、353 個事件，最終狀態一致（ruined_fort，種子 4）。」（含源泉、不滅誓約、不死擋下致命傷害）
   - `ruined_fort` 種子 1 `build_ranged`（含時隙湧流）：「重播驗證通過：86 個動作、235 個事件」。

## 4. 修改既有測試的原因

- `tests/skillgen/helpers.py`、`tests/skillgen/test_validate.py`：原本用假的改寫規則型原語 `grant_ap` 測驗證器；現在資料裡有真的 `grant_ap`，假原語改名 `fake_rewrite`（測試內容不變）。`test_epic_and_legendary_are_at_least_as_permissive_as_rare` 的傳說案例補上 `cost.source`（schema 現在要求）。
- `tests/skillgen/test_random_composer.py`：組合器不再產生傳說——`RARITIES` 去掉 `legendary`、「每個骨架都能組」改用史詩、新增 `test_legendary_is_hand_written_only`。
- `tests/engine/test_dual_scaling_mastery.py::test_dual_scaling_needs_epic_or_better`：傳說案例補上源力代價與 `grant_ap`，讓它只差雙屬性這一項。
- `tests/skillgen/test_budget.py`、`tests/skillgen/test_validate.py::test_beneficial_flags_in_content`：狀態表多了 `undying`（沒有預算點數、有益）。
- `tests/content/test_skill_rules_content.py`：光環骨架的核心原語多三個；三個改寫規則型原語的最低稀有度是 epic。
- `tests/content/test_coverage.py`：`_STATUS_VIA_PRIMITIVE` 加 `undying → cheat_death`（同 `shielded → shield`）。
- `tests/cli/test_budget_cli.py`：技能數 72 → 75（3 處）。
- `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py`：`LOG_FORMAT` `/13` → `/14`。
- `tests/cli/test_demo_maps.py`：單位表多了「源力 1/3」。
- `client/src/battle/testFixtures.ts`：`UnitView` 多了 `source`／`source_max`、`BattleView` 多了 `source_wells`（`oil_depot_seed3.json` 沒重錄，型別檢查通過）。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json`，9 筆全部）：`skills_list`、`skills_show_all`（新增 3 個技能）；7 場戰鬥都變了——單位表多了「源力 n/3」；`test_heights_8x8` 種子 42 另外多一個事件（擊倒盜賊頭目的 `source_changed`，243 → 244 個事件，戰鬥內容逐字相同，以臨時 worktree 比對確認）。

## 5. 新增的複雜度 noqa

**無**（沒有新增 C901／PLR0911／PLR0912／PLR0915）。`ai/utility._supports` 一度超過 PLR0911，把三個原語的判斷抽成 `_rewrite_supports` 解決；`interpreter._Cast.build` 與 `targeting.resource_problem` 原本就有 `PLR0911` 的 noqa，各多一個分支／回傳，沒有新增 noqa。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/14`**（本段只升一次）。理由：（1）擊倒精英會多出 `source_changed` 事件，`/13` 的紀錄用新程式重跑事件會不同；（2）狀態多了 `source`、`ap_pending`、`ap_granted_round`、`source_wells`，設定多了 `UnitSpawn.source`；（3）新事件 `source_changed`／`ap_granted`／`death_cheated`、`skill_used.source`、`status_removed` 的新原因 `spent`；（4）規則包多了三個原語、`undying` 狀態與源力規則。

## 7. 待 PM 決定（最多 10 點）

1. **精英用既有的 `elite` 標籤，沒有加 `elite: true` 欄位**：規格寫「單位範本加 `elite: true`」，但 `bandit_boss` 早就有 `tags: [elite, …]`，而且致命地形的精英規則也用這個標籤；再加一個布林欄位會有兩個來源不一致的風險。若 PM 想把「擊殺給源力」與「致命地形減傷」分開，再加欄位。
2. **傳說的「修正規則」分支目前寫不出來**：規格允許傳說帶修正規則，但修正技能（`kind: modifier`）裝在被動欄位、不能有代價，而源力只能由主動技能花。驗證規則已寫成「改寫規則型原語 **或** 修正規則」，但實際上傳說只能是主動技能 ＋ 改寫規則型原語。若要「花源力啟動一段時間的修正規則」，需要新機制（例如施放後在 N 回合內套用修正）。
3. **組合器不產生傳說**：抽到傳說時降為史詩（其他種子結果不變），所以 `rarity_weights.legendary: 10` 實際上併入史詩；指定傳說時拋錯。組合器要能產生傳說，需要讓它會寫源力代價與改寫規則型原語（3C-6 組合器整理時可考慮）。
4. **改寫規則型原語的最低稀有度是 epic**（不是 legendary），所以史詩也能手寫「冷卻 ≥ 4 或每場一次、不花源力」的改寫規則型技能（6.6 原本的規則）；目前沒有這種手寫技能。組合器一律不使用改寫規則型原語（明確指定史詩光環時原本會抽到，516f2ec 排除）。若 PM 希望改寫規則型專屬傳說，把三個原語的 `min_rarity` 改 `legendary` 即可。
5. **`grant_ap` 的兩個解讀**：「本回合上限」取 `ap_per_turn ＋ ap_carry_max`（4）；「每回合最多被給一次」實作為 **每輪** 一次（自己每輪只有一個回合，所以對自己等價；對友方較嚴格）。給 **不在自己回合** 的友方時，AP 存到它下次回合開始才加（否則回合開始重設 AP 會把它洗掉）——這不算「立刻」，請確認。
6. **`reset_cooldown` 的「不能重置自己」**：實作為兩者都做——不重置這個技能本身，也不影響施放者自己（`forbid_affects` 含 `self`，範圍技含自己時也略過自己）。只清冷卻，不恢復 `uses_per_battle` 次數。
7. **源泉格**：我方以任何方式抵達都算（走、被推、傳送）；**已滿 3 點時仍會取走源泉**（紀錄顯示「已達上限」）——照規格字面「+1（不超過上限），源泉消失」；若希望滿的單位不取走，改 `take_source_well` 一行。敵人踏上去不取用也不破壞。AI 不會主動去搶源泉（位置價值沒有源泉這一項），實戰中多半是隊友順路經過拿到。
8. **前端只做最小**：HUD 數字與按鈕停用原因；**源泉格沒有畫在畫布上**（API 已有 `source_wells`，3C-6 顯示時加），技能卡片視圖也沒有特別標示源力成本（成本文字已在 `cost` 裡）。
9. **AI 的傳說使用率**：數值（`ai_profiles.yaml` 的 `rewrite`）是初值。抽查 `ruined_fort`、`dark_forest`、`open_plain` 等地圖種子 1–5：時隙湧流在 build_ranged 每場都會用（第一個有源力的回合就用）；不滅誓約只在少數場次用到（治療的分數通常更高）；**重振號令一次都沒被 AI 用過**（隊友常沒有長冷卻）。「拿到這招後決策有沒有改變」留給 PM 試玩與 3C-6 matrix。
10. **預算初值**（未經模擬）：`grant_ap` 每 AP 4 點、`reset_cooldown` 7 點、`cheat_death` 8 點；源力折抵每點 250‰（上限 500‰）；三個示範傳說落在 71–85%。另外「源力折抵」與冷卻折抵一起受 `total_cap: 500` 截斷，所以花 2 點源力的傳說再加冷卻也不會更便宜。

## 8. 代表性輸出

`uv run trpg battle --map ruined_fort --seed 4 --ally-build build_healer`（輸出第 395–450 行，連續未刪節；治療英雄先前在第 4 輪汲取源泉 (4, 1)，源力 1 → 2）：

```
  盜賊1 攻擊 治療英雄：d20=4 修正 +0 熟練 +2 = 6（目標 11）→ 失手
  盜賊1 結束回合
— 盜賊弓手2 的回合（AP 4，移動 5，法力 9/9）
  盜賊弓手2 結束回合，保留 1 AP
— 盜賊弓手1 的回合（AP 4，移動 5，法力 9/9）
  盜賊弓手1 結束回合，保留 1 AP
— 治療英雄 的回合（AP 3，移動 5，法力 0/40）
  治療英雄 施放「不滅誓約」（AP 1，冷卻 3 回合，源力 2）→ 影響 1 格
    ✦ 治療英雄 花費源力：源力 2 → 0
  治療英雄 獲得狀態「不死」（2 回合）
  治療英雄 攻擊 盜賊1：d20=3 修正 -2 熟練 +2 = 3（目標 11）→ 失手
  治療英雄 攻擊 盜賊1：d20=1 修正 -2 熟練 +2 = 1（目標 11）→ 自然 1，失手
  治療英雄 結束回合
～ 環境回合 ～

=== 第 7 輪 ===
    0  1  2  3  4  5  6  7  8  9
 0  0.  0.  0A  0c  0.  0.  0.  0.  0.  0.
 1  0.  0-  0b  0.  0.  0@  0@  0@  0@  0.
 2  0.  0.  0.  0.  0.  0@  0.  2_  2a  0.
 3  0.  0.  0.  0[  0.  0@  0.  1.  2.  0.
 4  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
 5  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
 6  0.  0.  0.  0[  0.  0@  0&  1.  2d  0.
 7  0.  0.  0.  0.  0.  0@  0.  2_  2.  0.
 8  0.  0.  0.  0.  0$  0@  0@  0@  0@  0.
 9  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
  圖例：[ 木箱、- 倒木、_ 矮牆、& 油桶、$ 源泉
  A 我方 治療英雄：HP 20/40 法力 0/40 源力 0/3 耐力 10 位置 (2, 0) 武器 冰霜法杖［不死1］
  B 我方 標準隊友（戰士）：倒下
  C 我方 標準隊友（弓手）：倒下
  a 敵方 盜賊弓手1：HP 26/26 法力 9/9 耐力 30 位置 (8, 2) 武器 弓
  b 敵方 盜賊1：HP 9/30 耐力 20 位置 (2, 1) 武器 匕首
  c 敵方 盜賊2：HP 30/30 耐力 30 位置 (3, 0) 武器 匕首
  d 敵方 盜賊弓手2：HP 26/26 法力 9/9 耐力 30 位置 (8, 6) 武器 弓

— 盜賊2 的回合（AP 3，移動 5）
  盜賊2 攻擊 治療英雄：d20=17 修正 +0 熟練 +2 = 19（目標 11）→ 命中
    治療英雄 受到 8 點物理傷害［骰 4］，HP 20 → 12
  盜賊2 攻擊 治療英雄：d20=14 修正 +0 熟練 +2 = 16（目標 11）→ 命中
    治療英雄 受到 7 點物理傷害［骰 3］，HP 12 → 5
  盜賊2 攻擊 治療英雄：d20=2 修正 +0 熟練 +2 = 4（目標 11）→ 失手
  盜賊2 結束回合
— 盜賊1 的回合（AP 3，移動 5）
  盜賊1 對 治療英雄 使出推擊：d20=5 修正 +2 熟練 +2 = 9（目標 11）→ 失敗
  盜賊1 對 治療英雄 使出推擊：d20=8 修正 +2 熟練 +2 = 12（目標 11）→ 成功
  治療英雄 無法移動到 (2, 0)
  治療英雄 撞上了地圖邊緣！少走 1 格，受到 1 次撞擊
    治療英雄 受到 5 點撞擊物理傷害［骰 5］，HP 5 → 1
  ✦ 治療英雄 的「不死」擋下了致命傷害，HP 留在 1
  治療英雄 的「不死」擋下致命傷害後消失了
  盜賊1 對 治療英雄 使出推擊：d20=16 修正 +2 熟練 +2 = 20（目標 11）→ 成功
  治療英雄 無法移動到 (2, 0)
  治療英雄 撞上了地圖邊緣！少走 1 格，受到 1 次撞擊
    治療英雄 受到 1 點撞擊物理傷害［骰 1］，HP 1 → 0
  ＊ 治療英雄 倒下了！
```

同一場以 `--log-json` 存檔後 `trpg battle replay`：「重播驗證通過：133 個動作、353 個事件，最終狀態一致（ruined_fort，種子 4）。」
