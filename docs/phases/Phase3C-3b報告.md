# Phase 3C-3b 報告：表面歸屬 ＋ `on_enter_surface` ＋ `consume_status` ＋ 基本推擊貼牆撞擊

## 1. commit

| commit | 內容 |
|---|---|
| b05e54a | 引擎、內容、前端型別：`Tile.surface_creator`（`set_surface` 的 `creator`、視圖、OpenAPI／`schema.d.ts`）、`on_enter_surface` 觸發時機（`TriggerSpec.surface`、`skill_triggers.yaml`、`skill_triggers._on_enter_surface`）、`consume_status` 原語（`EffectSpec.then／scale／splash`、`skill_primitives.yaml`、解譯器、預算、紀錄文字）、`consume_status` 骨架、基本推擊貼牆合法（`shove_problem`）、兩個示範技能與 build 裝備、`LOG_FORMAT` `/13` |
| 2908b64 | 測試：`test_surface_triggers.py`（15）、`test_consume_status.py`（22）、`test_surface_consume_schema.py`（7）、`test_collision.py` 的貼牆推擊測試（9），以及既有測試與 CLI 快照更新 |
| （本報告） | 報告 |

## 2. 交付項目

### 2.1 表面 `creator`（5.1）

- `Tile.surface_creator: UnitId | None`。`set_surface(..., creator=)`：`create_surface` 效果以 `effect.source_id` 寫入；表面被清除（`none`）時一併清掉；表面種類相同但 creator 不同時也算變更。
- 蔓延（`ElementTouchEffect` 無來源）、天氣、地圖原有表面、到期後轉換的表面（`expires_to`）、地圖事件的 `ChangeTile` 都是 `None`。環境互動產生的表面（`interactions.py`）本來就把觸及它的 `source_id` 傳進 `CreateSurfaceEffect`，所以自動「沿用觸及它的來源」（例如 A 的油被 B 的火觸及，變成 B 的火）。
- `TileView.surface_creator`（視圖與 API）；`Tile` 為 dataclass，`clone`／序列化／重播沿用；`skill_fuzz` 的 `Tile(...)` 位置參數補上 creator。

### 2.2 `on_enter_surface`（5.1）

- 觀察 `UnitMoved`（`walk`、`forced`；傳送不算）：落點格的 `surface_creator` 是持有者、進入者與持有者不同陣營、`trigger.surface` 省略或與落點表面相同時，記一筆 `Fired`（另一方＝進入者），走既有的延後結算／深度檢查／次數／代價管線。
- 回合開始站在上面、表面出現在腳下（都不會產生 `UnitMoved`）自然不觸發。
- `TriggerSpec.surface`：只有 `on_enter_surface` 可填，不可為 `none`。`content/skill_triggers.yaml` 新增 `on_enter_surface`（係數 350‰、`min_rarity: epic`、`random_composer: false`，初值未經模擬）；`REQUIRED_TRIGGERS` 加入。
- 示範：潮汐絆腳 `skill_tide_snare`（史詩被動）：敵人踏進你造的水時施加緩速 2 回合；裝備於 `build_storm`（召水 `skill_summon_tide` 造出的水表面有 creator）。預算 75.8%。

### 2.3 `consume_status`（5.2）

- 格式：`{type: consume_status, status, then: [...1–2 個...], scale?, splash?, stack?}`。`then` 只能用 `damage`／`heal`／`shield`／`apply_status`，不可自帶 `affects`／`condition`（對象一律是被消耗的單位）。被消耗的對象由 `consume_status` 自己的 `affects`（預設敵方，需命中）決定。
- 結算（`interpreter._Cast.consume_status`）：對象有該狀態 → 先立刻移除（`StatusRemoved`，新原因 `consumed`）、再結算 `then`（自動命中、不暴擊、無格擋；狀態照常擲抵抗）；對象沒有該狀態 → 略過；全部對象都沒有 → 發出 `EffectFizzled(reason="no_status")`。
- `scale: remaining_rounds`：`then` 的骰數 × 被消耗狀態的剩餘回合（永久狀態為 1）；`scale: stacks`：同時消耗目標身上 `stack`（必須是目標型層數）的全部層數，骰數 × 層數（無層數為 1）。倍率至少 1、至多 `core.yaml` 的 `consume_status_max_scale`（初值 3）。
- `splash: 1`：`then` 也作用在被消耗者曼哈頓距離 1 內的存活敵方單位（相對於施放者陣營）。
- 預算（`skill_budget.yaml`，初值）：`then` 各效果基礎點數合計 × `consume_status_scale_expected`（2，僅有 `scale` 時）× (1000＋`consume_status_splash_permille` 500)÷1000（僅有 `splash` 時）× `consume_status_discount_permille`（700，「需要先有狀態」折扣）；形狀與對象倍率照一般效果。
- 骨架 `consume_status`（`content/skeletons/consume_status.yaml`；核心 `consume_status` 占 70% 以上、可附帶 0–1 個有害效果；單體、錐形、十字、3×3）；隨機組合器不產生（`random_composer._HAND_WRITTEN_ONLY`）。
- 紀錄文字（`narrative/skills.py`）、`trpg skills show／budget` 顯示。
- 示範：引爆燃燒 `skill_detonate_burning`（稀有，AP 2，法力 6，冷卻 2）：消耗燃燒，`2d6` 火焰 × 剩餘回合並波及相鄰敵人；裝備於 `build_fire`。預算 72.3%。

### 2.4 基本推擊貼牆撞擊（5.4）

- `shove_problem` 不再檢查目標身後第一格；只保留「距離減半後為 0」。`_push_unit` 本來就會在第一步被擋時發出 `MoveBlocked` ＋ `Collided`（少走 1 格），所以對抗成功時目標不移動、受 1 次撞擊，撞到單位或可破壞物件時對方也受傷（3C-3a 的規則）；對抗失敗不撞。
- `legal_actions`、預覽（`collisions`）、API 與前端（都由 `legal_actions` 與預覽驅動）、AI（預覽事件的環境傷害）自動跟著更新，沒有額外程式碼。

## 3. 驗收條件逐條（3C-3b 適用的部分）

- **2. 表面 `creator`（序列化、視圖、重播；舊行為不變）**：`tests/engine/test_surface_triggers.py`：`test_a_skill_created_surface_records_its_creator_and_team`、`test_environment_surfaces_have_no_creator`、`test_replacing_a_surface_takes_the_new_creator_and_clearing_it_drops_the_creator`、`test_interaction_surfaces_keep_the_source_that_touched_them`、`test_the_view_exposes_the_surface_creator_and_it_survives_cloning`。重播：`trpg battle --map open_plain --seed 1 --ally-build build_storm --log-json …` → `battle replay`「重播驗證通過：48 個動作、171 個事件」；`oil_depot` 種子 7（`build_fire`）「100 個動作、380 個事件」。沒有 creator 的舊行為由既有測試與全部 pytest（1804 passed）證明。
- **1. `on_enter_surface` 觸發／不觸發**：觸發：`test_an_enemy_walking_into_the_holders_surface_triggers_it`（在移動事件之後）、`test_a_forced_move_into_the_surface_triggers_it`。不觸發：友方進入 `test_a_friendly_unit_entering_does_not_trigger`、持有者自己走進 `test_the_holders_own_walk_does_not_trigger`、沒有 creator `test_a_surface_with_no_creator_does_not_trigger`、別人造的 `test_someone_elses_surface_does_not_trigger_the_holder`、`surface` 參數過濾 `test_the_surface_parameter_filters_by_surface_kind`、腳下出現或回合開始站著 `test_a_surface_appearing_under_a_unit_or_standing_on_it_does_not_trigger`、傳送 `test_a_teleport_into_the_surface_does_not_trigger`。schema：`tests/content/test_surface_consume_schema.py::test_surface_param_only_belongs_to_on_enter_surface`。
- **3. `consume_status` 有狀態／無狀態／兩種 scale**：`tests/engine/test_consume_status.py`：有狀態 `test_it_removes_the_status_then_resolves_the_effects`；無狀態 `test_without_the_status_nothing_resolves`、`test_a_different_status_is_not_consumed`；`remaining_rounds` `test_scale_remaining_rounds_multiplies_the_dice`、上限與永久狀態 `test_scale_is_capped_and_a_permanent_status_counts_as_one`；`stacks` `test_scale_stacks_consumes_the_targets_stacks`、`test_scale_stacks_without_stacks_is_one_and_without_the_status_keeps_the_stacks`；濺射 `test_splash_also_hits_adjacent_enemies_but_not_allies_or_far_units`；`then` 施加狀態、預覽不改狀態、確定性、結構與跨檔案驗證（參數化 9 種錯誤）。
- **4. 互相觸發停在深度上限**：3C-3a 的 `test_two_passives_that_trigger_each_other_stop_at_the_depth_limit` 沿用；本段新增 `test_enter_surface_chains_stop_at_the_depth_limit`（`on_enter_surface` 的被動把敵人推向下一格油而再次觸發自己，`max_trigger_depth=2` 時只結算深度 1、2，第 3 層發出 `TriggerLimitReached`）。
- **5. 每個新時機與原語至少一個手寫技能；`check.py` 全過；重播一致**：`skill_tide_snare`（`on_enter_surface`，build_storm）、`skill_detonate_burning`（`consume_status`，build_fire）；`tests/content/test_surface_consume_schema.py::test_demo_skills_pass_validation_and_budget`、`test_demo_skills_are_equipped_by_builds`、`tests/content/test_coverage.py`（允許清單維持為空）；`uv run python scripts/check.py` 的 ruff、format、mypy、lint-imports、pytest（1804 passed）、client install／typecheck／vitest（75）全部通過。
- **5.4 基本推擊貼牆**：貼牆 `test_shove_against_a_wall_is_legal_and_the_target_takes_one_collision`、貼單位 `test_shove_against_a_unit_hurts_both`、貼物件與可破壞物件 `test_shove_against_an_object_and_a_breakable_object`、地圖邊緣 `test_shove_at_the_map_edge`、對抗失敗不撞 `test_a_failed_contest_does_not_collide`、減半為 0 仍不合法 `test_a_halved_distance_of_zero_is_still_illegal`、預覽顯示撞擊傷害 `test_the_shove_preview_shows_the_collision_damage`／`test_the_shove_preview_against_a_unit_lists_both_victims`、AI 評分 `test_the_ai_scores_a_wall_shove_higher_than_a_shove_in_the_open`；`tests/engine/test_phase1c_decisions.py::test_blocked_shove_is_legal_and_collides`（5 種阻擋）。

## 4. 修改既有測試的原因

- `tests/engine/test_collision.py`：`test_shove_into_a_wall_next_to_the_target_stays_illegal`（3C-3a 的「仍不合法」）依 5.4 刪除，換成上面的貼牆推擊測試。
- `tests/engine/test_phase1c_decisions.py`：`test_blocked_shove_is_illegal`（5 種：物件、牆、較高、單位、地圖外）改為 `test_blocked_shove_is_legal_and_collides`，期望由「不合法」改為「合法、對抗成功時撞擊 1 次且不移動」（Phase 1C #10 被 5.4 取代；`Interact` 推不動仍不合法，沒有動）。
- `tests/engine/test_event_filter.py::_trapper_battle`：種子 7 改為 1。推擊合法使 AI 的行動改變，種子 7 的戰鬥不再放置陷阱，測試前提「戰鬥放過陷阱且有未觸發的陷阱」不成立；種子 1 放 2 個、2 個都沒觸發。
- `tests/content/test_skill_rules_content.py`：骨架 13 改為 14（加 `consume_status`，測試名改為 `…fourteen…`）；`tests/skillgen/test_validate.py`：骨架範例表加 `consume_status`。
- `tests/cli/test_budget_cli.py`：技能數 70 改為 72（兩處）。
- `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py`：`LOG_FORMAT` `/12` 改為 `/13`。
- `client/src/battle/testFixtures.ts`：`TileView` 多了 `surface_creator`，fixture 加 `surface_creator: null`（`oil_depot_seed3.json` 沒重錄，型別檢查通過）。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json`，8 筆全部）：`skills_list`、`skills_show_all`（新增 2 個技能）；6 場戰鬥快照雜湊都變了——基本推擊貼牆變合法，AI 的行動選擇與骰序列因此改變，另外 `build_fire`／`build_storm` 加了技能。

## 5. 新增的複雜度 noqa

**無**（沒有新增 C901／PLR0911／PLR0912／PLR0915）。`consume_status` 的結算拆成 `consume_status`／`_consume_scale`／`_consume_then`／`_then_effect`，`apply_status` 抽出 `_status_effects` 共用。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/13`**（本段只升一次）。理由：（1）基本推擊貼牆變合法，`/12` 的紀錄用新版程式重跑 AI 會不同；（2）規則包加了 `on_enter_surface` 觸發時機與 `consume_status` 原語、核心規則 `consume_status_max_scale`，`/12` 紀錄內嵌的觸發表會被 `REQUIRED_TRIGGERS` 拒絕；（3）`status_removed.reason` 新增 `consumed`、格子狀態新增 `surface_creator`。

## 7. 待 PM 決定（最多 10 點）

1. **`scale: stacks` 的語意**：規格寫「stacks（目標型層數）」，但層數（`stacks.yaml`）與狀態是兩套東西。我的做法：`scale: stacks` 必須另填 `stack`（目標型層數，如 `sunder`），目標有 `status` 時同時消耗該層數的全部層數並以層數為倍率；沒有 `status` 時整個原語不結算、層數保留。若 PM 想的是「狀態本身有層數」，需要先在狀態系統加層數欄位，我沒做。目前沒有任何手寫技能使用 `stacks`（只有測試）。
2. **濺射範圍與對象**：`splash: 1` ＝ 曼哈頓距離 1 的存活敵方單位（不含被消耗者自己、不含隊友），濺射到的單位不需命中判定、也不會被消耗它們身上的狀態。`splash` 只允許 1。
3. **`then` 的對象固定是被消耗者（與濺射範圍）**，不能自帶 `affects`；所以「引爆後治療自己」這類效果寫不出來。`then` 限 `damage`／`heal`／`shield`／`apply_status`，不含 `push`／地形（想要「引爆後推開」時再開放）。
4. **永久狀態的 `remaining_rounds` 倍率為 1**，倍率上限 `consume_status_max_scale: 3`（`core.yaml`）。引爆燃燒（`2d6`）在剩餘回合 2 時平均 14 點再加濺射；未經模擬，示範戰鬥中偏強還是偏弱請 3C-6 matrix 觀察。
5. **`on_enter_surface` 的「進入」＝ `UnitMoved`（walk／forced）**，傳送不算；每一步都算（走過一條由持有者造的油，每踏進一格都可能觸發，受 `max_per_round` 限制）。表面被換成另一種表面（例如油被點燃成火）後 creator 沿用觸及者，所以「持有者造的油被敵人點燃」會變成敵人的火，不再觸發持有者的被動。
6. **環境蔓延出來的表面 creator 為 `None`**（規格）：火從持有者造的火蔓延到旁邊格，新火沒有 creator；若想讓蔓延沿用原 creator 需要改 `_spread_fire`，我沒做。
7. **基本推擊貼牆時 `MoveBlocked` 事件仍會發出**（沿用 3C-3a 的 `_push_unit`），紀錄文字會先顯示「無法移動到 …」再顯示「撞上了…」；前端沒有額外提示「這一推會撞牆」，只有預覽的「撞擊傷害」行（前端除型別外無改動）。
8. **AI 與貼牆推擊**：AI 完全沿用預覽評分，沒有特別調整；6 個戰鬥快照因 AI 更常使用推擊而改變。沒有跑 `sim matrix` 觀察是否有 build 因此爆衝。
9. **示範技能分配**：`skill_detonate_burning` 放 `build_fire`（主動 5/6）、`skill_tide_snare` 放 `build_storm`（被動 1/3）；`build_fire` 的燃燒來源只有 `skill_fire_bolt`（1 回合燃燒，引爆只有 1 倍），3C-6 整理 build 時請一併看。
10. **預算初值**：`consume_status` 的 `then` 期望倍率 2、濺射 ＋50%、需先有狀態折扣 0.7；`on_enter_surface` 係數 350‰；示範技能落在 72.3% 與 75.8%（接近下限），平衡階段再調。

## 8. 代表性輸出

```
$ uv run trpg battle --map oil_depot --seed 7 --ally-build build_fire    （連續片段）
  盜賊弓手 從 (5, 4) 移動到 (3, 6)（消耗 4 移動）
  盜賊弓手 刷新狀態「燃燒」（2 回合）
  盜賊弓手 結束回合
— 火焰流英雄 的回合（AP 3，移動 5，法力 26/40）
  火焰流英雄 施放「引爆燃燒」（AP 2，法力 6，冷卻 2 回合）→ 影響 1 格
  火焰流英雄 以「引爆燃燒」攻擊 盜賊2：d20=10 修正 -1 熟練 +2 = 11（目標 11）→ 命中
  盜賊2 的「燃燒」被消耗了
    盜賊2 受到 18 點火焰傷害［骰 6+4］，HP 15 → 0
  ＊ 盜賊2 倒下了！
    盜賊頭目 受到 10 點火焰傷害［骰 1+1］，HP 51 → 41
  ★ 火焰流英雄 的被動「烈焰護身」觸發（施放帶標籤的技能後，深度 1）（法力 2）
    火焰流英雄 獲得 13 點護盾（取較大值，共 14）
  火焰流英雄 施放「火焰箭」（AP 1，法力 6）→ 影響 1 格
```

同一場以 `--log-json` 存檔後 `trpg battle replay`：「重播驗證通過：100 個動作、380 個事件，最終狀態一致（oil_depot，種子 7）。」
