# Phase 3C-3a 報告：撞擊規則 ＋ `on_collision`、`on_cast_tag`、`on_status_applied`

## 1. commit

| commit | 內容 |
|---|---|
| 04a01ba | 引擎、內容、API、前端：撞擊規則（`Collided` 事件、`cause: collision`、`collision_damage_dice`、`push`／`pull` 的 `collision_dice`、`push_distance_delta` 超過上限改為撞擊）、三個新觸發時機（`TriggerSpec.tag／status`、`content/skill_triggers.yaml`、`skill_triggers.collect_cast`）、預覽 `collisions`、四個示範技能與 build 裝備、`LOG_FORMAT` `/12`、重新產生 `openapi.json`／`schema.d.ts` |
| bc31a4a | 測試：`test_collision.py`（20）、`test_new_triggers.py`（16）、`test_collision_triggers_schema.py`（6）、vitest 1 個；更新既有測試與 CLI 快照 |
| （本報告） | 報告 |

（開發期間 main 上沒有其他 session 的新 commit 影響本段。）

## 2. 交付項目

### 2.1 撞擊規則（5.0）

- **規則**（`engine/effects/world.py::_push_unit`）：被 `PushEffect` 推動的 **單位** 因障礙停下時，發出 `Collided`（`unit_id`、`obstacle`：`wall`／`edge`／`object`／`unit`／`excess`、`shortfall`、`pos`、`source_id`、`other_id`、`object_id`、`dice`）；障礙對照：地圖外 → `edge`、有單位 → `unit`、`blocks_move` 物件 → `object`、其他（不可走的地形、過高的階梯）→ `wall`。墜落（`UnitFell`）不會讓推擊停下，落入致命地形或倒下則直接結束、不算撞擊。
- **傷害**（`engine/triggers.py` 的 `collided` 觸發函式，與 `unit_fell` 同一模式）：每少走 1 格，被推單位與撞到的單位各一個 `DamageEffect(cause="collision")`（物理、骰 `collision_damage_dice`＝`1d6`，沒有屬性加成、套用目標的物理抗性），撞到 `breakable` 物件時再一個 `DamageObjectEffect`；傷害歸給位移來源。效果的 `depth` ＋ 1，所以照常受 `max_chain_depth`／`max_trigger_depth` 限制。
- **`DamageCause` 新增 `collision`**；事件文字與紀錄顯示「撞擊物理傷害」；`ObjectDamaged.cause` 也是 `collision`。
- **`push_distance_delta` 超過上限**：`modifiers.displace_split` 回傳 `(距離, 額外撞擊次數)`；距離仍截斷在 `max_displace_distance`，超過的每 1 格在推完之後發出一個 `Collided(obstacle="excess")`（就算沒撞到東西）。基本動作推擊（`battle.shove_split`）與技能 `push`／`pull`（`interpreter.displace`）都走這條路。`displace_distance` 保留為只取距離的包裝。
- **技能加強撞擊**：`EffectSpec.collision_dice`（`push`／`pull` 可省略，`content/skill_primitives.yaml` 宣告）；填了就取代預設骰。預算：每顆骰加 `collision_die_points`（`skill_budget.yaml`，初值 1）點，`trpg skills budget` 顯示「＋ 撞擊 2d6（2 點）」。
- **預覽**：`Preview.collisions`（`(單位, 最少, 最多)`，行動者造成的所有撞擊傷害）；API `PreviewOut.collisions`；前端預覽多一行「撞擊傷害 〈單位〉 最多 N」，`collided` 事件文字列入連鎖事件。
- **AI**：不需要另寫評分——預覽的模擬事件本來就包含 `DamageDealt`，`_event_damage` 把非 `attack` 原因的傷害算成「環境傷害」（對敵人加分、對友方扣分）；測試 `test_ai_scores_a_push_into_a_wall_higher_than_the_same_push_in_the_open` 確認把敵人推向牆的分數較高。
- 颶風踢（推 2 格）撞牆確實造成撞擊傷害，技能數值沒改：`test_gale_kick_into_a_wall_deals_collision_damage`。

### 2.2 新觸發時機（5.1）

| 時機 | 收集點 | 另一方 |
|---|---|---|
| `on_cast_tag`（`trigger.tag` 必填） | 主動技能與反應技施放完（`use_skill`／`use_reaction_skill` 的 `holding` 結尾）呼叫 `collect_cast`；標籤用 `modifiers.effective_tags`（含 `add_tags`） | 無，效果作用在持有者 |
| `on_status_applied`（`trigger.status` 可省略） | 觀察 `StatusApplied`（來源 ＝ 持有者；抵抗成功不會產生此事件） | 被施加的單位 |
| `on_collision` | 觀察 `Collided`（來源 ＝ 持有者） | 被推的單位 |

- 全部走既有的收集 → 延後結算 → 深度檢查管線（`max_trigger_depth`、每輪次數、代價、沉默、條件都沿用）。
- `content/skill_triggers.yaml` 新增三項（係數 350／400／300‰，`min_rarity: epic`，初值未經模擬），新欄位 `random_composer: false`（帶參數的時機隨機組合器不產生，所以隨機技能與既有種子的輸出不變）；`REQUIRED_TRIGGERS` 加入三項。
- schema：`TriggerSpec` 驗證 `tag`（只能搭配 `on_cast_tag` 且必填）與 `status`（只能搭配 `on_status_applied`）；`skill_problems` 檢查 `status` 存在。

### 2.3 示範技能（全部有 build 裝備；`test_coverage.py` 允許清單維持為空）

| 技能 | 內容 | 預算比例 | 裝備 |
|---|---|---|---|
| 破城衝撞 `skill_battering_ram`（稀有，AP 2） | 傷害 80% ＋ 推 2 格、撞擊骰 `2d6` | 70.8% | build_push |
| 裂骨印記 `skill_fracture_mark`（史詩被動） | `on_collision`：對被撞單位施加流血 3 回合 | 70.7% | build_push |
| 蝕心追擊 `skill_creeping_blight`（史詩被動） | `on_status_applied`（任何狀態）：對該單位造成 1d8 暗影傷害 | 79.6% | build_warlock |
| 烈焰護身 `skill_ember_ward`（史詩被動） | `on_cast_tag: fire`：自己獲得 1d6 護盾 | 70.7% | build_fire（被動欄位第 3 個） |

## 3. 驗收條件逐條（3C-3a 適用的部分）

1. **撞擊**：全部通過（`tests/engine/test_collision.py`）。
   - 撞牆、少走 2 格受兩次：`test_pushed_into_a_wall_two_tiles_short_takes_two_collision_hits`；少走 1 格一次：`test_one_tile_short_is_one_hit`。
   - 撞地圖邊緣：`test_map_edge_collision`。
   - 撞單位（雙方受傷、歸給推擊者）：`test_hitting_another_unit_hurts_both_and_credits_the_pusher`。
   - 撞可破壞物件（物件也受傷）：`test_hitting_a_breakable_object_damages_the_object_too`；過高的階梯算牆：`test_a_step_up_blocks_like_a_wall`。
   - 墜落不算撞擊：`test_falling_into_deadly_terrain_is_not_a_collision`、`test_falling_down_a_ledge_is_not_a_collision`；自由推擊沒有撞擊：`test_a_free_push_has_no_collision`。
   - `push_distance_delta` 超過上限改為撞擊傷害：`test_push_distance_over_the_cap_becomes_collision_damage`（颶風踢＋重踏：距離 2 格、一次 `excess` 撞擊，在移動事件之後）；3C-2 的 `test_heavy_stomp_push_distance_is_capped_at_two_tiles` 仍通過。
   - 基本動作推擊也適用：`test_basic_shove_collides_too`；第一格就被擋的推擊仍不合法：`test_shove_into_a_wall_next_to_the_target_stays_illegal`。
   - 技能骰：`test_collision_dice_replace_the_default`、`test_battering_ram_uses_its_own_collision_dice`。
   - 預覽顯示撞擊傷害：`test_preview_shows_the_possible_collision_damage`、`test_preview_without_a_collision_is_empty`；API `test_preview_returns_the_numbers_and_does_not_change_the_session`（含 `collisions` 鍵）；vitest「lists the possible collision damage per unit」。
2. **三個時機各有觸發與「不該觸發」測試**：通過（`tests/engine/test_new_triggers.py`）。
   - `on_cast_tag`：觸發在技能結算之後 `test_on_cast_tag_triggers_after_the_tagged_skill_resolves`；不該觸發：其他標籤／沒標籤 `test_on_cast_tag_ignores_other_tags_and_untagged_skills`、別人施放 `test_on_cast_tag_is_not_triggered_by_a_basic_attack_or_by_another_units_cast`；修正規則加上的標籤 `test_on_cast_tag_sees_tags_added_by_modifier_rules`。
   - `on_status_applied`：`test_on_status_applied_triggers_and_targets_the_unit_that_got_the_status`、省略 `status` `…_without_a_status_filter_accepts_any_status`；不該觸發：其他狀態 `…_ignores_other_statuses`、**抵抗成功** `…_does_not_trigger_when_the_status_is_resisted`（`StatusResisted`、沒有 `StatusApplied`）、對自己施加 `…_ignores_statuses_the_holder_puts_on_itself`、別人施加 `…_ignores_statuses_applied_by_others`。
   - `on_collision`：`test_on_collision_triggers_for_the_unit_that_caused_the_collision`（撞擊傷害之後才觸發）、`…_for_the_excess_collision_too`；不該觸發：別人推的／沒有來源 `…_when_someone_else_pushed`、沒有撞擊 `…_without_a_collision`、**主動移動被擋或走路** `…_when_an_active_move_is_blocked_or_walks`。
3. **互相觸發停在深度上限**：`test_two_passives_that_trigger_each_other_stop_at_the_depth_limit`（A：施加燃燒 → 緩速、B：施加緩速 → 燃燒；深度 1、2、3 結算，第 4 層 `TriggerLimitReached`，戰鬥照常結束）。
4. **每個新時機至少一個手寫技能；`check.py` 全過；重播一致**：通過。`test_demo_skills_use_the_new_triggers_and_pass_validation_and_budget`、`test_coverage.py`（允許清單為空）；`uv run python scripts/check.py` → ruff、format、mypy、lint-imports、pytest（1750 passed）、client install／typecheck／test（75 passed）全部通過。重播：`test_ai_battles_with_collisions_are_deterministic_and_replay`（build_push、oil_depot 種子 3：同輸入輸出逐字相同、`--log-json` → `battle replay` 重播驗證通過，含撞擊與 `on_collision`）；指令實測「重播驗證通過：110 個動作、326 個事件，最終狀態一致（oil_depot，種子 3）」。
5. 其他：新觸發時機的 schema 測試 `tests/content/test_collision_triggers_schema.py`（參數與時機相符、未知狀態被拒、`min_rarity: epic`、隨機組合器不產生、`collision_dice` 預算 ＋2 點、只能用在 push／pull）。

（5.3 的表面 `creator`、`on_enter_surface`、`consume_status` 屬 3C-3b，沒有做。）

## 4. 修改既有測試的原因

- `tests/content/test_modifier_schema.py`：重踏的中文描述加了「，超過的每格改為一次撞擊傷害」（`push_distance_delta` 的新行為）。
- `tests/content/test_skill_triggers_content.py`：觸發時機 9 → 12（係數表加三項）、`on_cast_tag` 沒有另一方（`has_other: false`）。
- `tests/cli/test_budget_cli.py`：技能數 66 → 70（新增 4 個示範技能，兩處）。
- `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py`：`LOG_FORMAT` `/11` → `/12`。
- `tests/cli/test_guardian_battle.py::test_a_unit_with_riposte_hits_back_in_an_ai_battle`：種子 3 → 2。加入撞擊傷害後種子 3 的戰局改變（先攻順序與骰序列被撞擊傷害的擲骰往後推），不再出現還擊；種子 2 的戰局有還擊。測試意圖（AI 戰鬥中還擊會發生）不變。
- `tests/api/test_routes.py`：預覽回應多了 `collisions` 鍵。
- `tests/engine/test_modifiers.py`：只改 `test_heavy_stomp_push_distance_is_capped_at_two_tiles` 的說明文字（斷言不變）。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json`，6 筆）：`skills_list`、`skills_show_all`（新增 4 個技能）、`battle_default_flat_42`、`battle_bridge_guardian_11`、`battle_frozen_lake_push_3`、`battle_oil_depot_fire_7`（戰鬥中出現撞擊傷害，擲骰序列改變；撞擊是通用規則，所以有推擊的戰鬥都會變，其餘 2 筆戰鬥快照雜湊不變）。

## 5. 新增的複雜度 noqa

**無**（沒有 C901／PLR0911／PLR0912／PLR0915）。開發中 `_push_unit` 與 `_collide` 一度觸發 `SIM113`、`PLR0917`，改用 `for step in range(...)` 與 keyword-only 參數解決。新增的非複雜度 noqa：`tests/engine/test_collision.py` 的 `PLC0415`（一個測試內延後匯入 AI，與 `test_ai_utility.py` 相同寫法）。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/12`**（本段只升一次）。理由：撞擊是通用規則，`/11` 的紀錄含推擊遇到障礙的情形，新版引擎重播會多出撞擊傷害與 `collided` 事件而不一致；規則包也加了 `collision_damage_dice` 與三個觸發時機（`/11` 紀錄內嵌的舊觸發表會被 `REQUIRED_TRIGGERS` 拒絕）。`/11` 的紀錄無法由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **基本動作推擊第一格就被擋仍不合法**（沿用 `shove_problem`）：所以推擊的撞擊只會在「推 2 格、第二步被擋」時出現（目前基本動作推 1 格，只有重踏＋改 `shove_distance` 才會推 2 格）。設計文件說「牆和狹窄地形不再只是擋路」，若要讓玩家把敵人 **貼牆推擊** 就吃撞擊傷害，需要放寬 `shove_problem`（改成第一格被擋也合法、少走 1 格受撞擊）。這會改變推擊的合法性與 AI 列舉，我先不動。
2. **過高的階梯（`too_high`）算 `wall`**：規格列的障礙是「`blocks_move` 物件、不可走地形、其他單位、地圖邊界」，階梯沒寫到；我把「被推往比目前高的格子」視為撞牆（保守地讓撞擊更常發生）。想排除的話只需改 `_COLLISION_OBSTACLES`。
3. **撞擊傷害套用目標的物理抗性**（`apply_element_mod` 預設開，實測有「元素修正 ×0.9」），只是「不加屬性」；`min_damage` 沿用預設 1。若要完全固定的 `1d6`，改成不套用元素修正即可。
4. **同一次撞擊的每一格各擲一次骰**（少走 2 格 ＝ 2 個 `DamageDealt`），也因此 `on_damaged` 類被動可能被觸發兩次。若要合成一次（骰數 × 格數）要改 `triggers._collision_damage`。
5. **`excess`（超過上限）的撞擊也算 `Collided`**，所以會觸發 `on_collision`（規格說「就算沒撞到東西也算」但沒說是否算「撞擊」）；若又同時撞到東西，會有兩個 `Collided`（先 `wall`／`unit`……、再 `excess`）。steadfast 單位的距離減半 **不算** 撞擊。
6. **`on_status_applied` 的邊界**：刷新持續時間（目標已有該狀態）算「成功施加」；對自己施加（來源 ＝ 目標）、環境與沒有來源的施加都不算。
7. **`on_cast_tag` 只計主動技能與反應技的施放**，被動觸發、陷阱觸發、命中後效果不算；反應技施放也算。標籤比對含 `add_tags` 修正（只一層，沿用 3C-2）。
8. **`on_collision` 自己撞自己（來源 ＝ 被推者）與沒有來源的撞擊（環境）不觸發**；對被撞單位已被撞擊傷害打倒時，`target: other` 的效果不結算（與 `on_kill` 以外的一般規則相同）。
9. **示範技能分配**：本來想做「燃燒時追加傷害」，但 `build_striker` 的測試規定剛好 3 個技能，所以改成不限狀態的「蝕心追擊」放 `build_warlock`；`build_fire` 的被動欄位因此已滿（灼傷之痕、餘燼循環、烈焰護身）。這些加進 build 會改變 4 場 CLI 快照戰鬥與之後 `sim matrix` 的結果；3C-6 整理 build 時請 PM 一併看。
10. **預算初值**：三個時機係數 350／400／300‰、`collision_die_points: 1`（每顆撞擊骰 1 點，不論面數、也不扣預設骰）；示範技能落在 70.7%–79.6%（接近下限），3C-6 的 `sim matrix` 後再調。

## 8. 代表性輸出

```
$ uv run trpg battle --map oil_depot --seed 3 --ally-build build_push
  位移流英雄 施放「破城衝撞」（AP 3，法力 4，冷卻 3 回合）→ 影響 1 格
  位移流英雄 以「破城衝撞」攻擊 盜賊1：d20=19 修正 +0 熟練 +2 = 21（目標 11）→ 命中
  ⟳ 盜賊1 反應：格擋（耐力 −10）
    盜賊1 受到 5 點物理傷害［骰 8］（格擋/加成 ×0.4），HP 22 → 17
  盜賊1 無法移動到 (4, 2)
  盜賊1 撞上了盜賊2！少走 2 格，受到 2 次撞擊
  盜賊1 被推得太猛，受到衝擊（1 次撞擊）          ← 重踏讓推擊超過 2 格上限，多出的 1 格改為撞擊
    盜賊1 受到 6 點撞擊物理傷害［骰 3+3］，HP 17 → 11
    盜賊1 受到 8 點撞擊物理傷害［骰 6+2］，HP 11 → 3
    盜賊1 受到 7 點撞擊物理傷害［骰 2+5］，HP 3 → 0
  ＊ 盜賊1 倒下了！
    盜賊2 受到 8 點撞擊物理傷害［骰 2+6］，HP 30 → 22
    盜賊2 受到 6 點撞擊物理傷害［骰 2+4］，HP 22 → 16
  ★ 位移流英雄 的被動「嗜血」觸發（擊倒時，深度 1），對象 盜賊1（法力 2）
...
  ★ 位移流英雄 的被動「裂骨印記」觸發（造成撞擊後，深度 1），對象 盜賊弓手（法力 2）
  盜賊弓手 獲得狀態「流血」（3 回合）
重播驗證通過：110 個動作、326 個事件，最終狀態一致（oil_depot，種子 3）。
```
