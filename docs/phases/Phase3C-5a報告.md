# Phase 3C-5a 報告：場景物件原語——投擲物件 `hurl_object`、推倒 `topple`

## 1. commit

| commit | 內容 |
|---|---|
| b049634 | 引擎、內容與測試：物件標籤 `penetrable`／`topplable`、新物件枯樹與倒塌物、推倒（通用規則＋原語 `topple`）、投擲物件（原語 `hurl_object`＋形狀 `object_then_tile`）、新事件、紀錄文字、兩個示範技能與 build 裝備、地圖擺放、前端物件外觀、`LOG_FORMAT` `/16`；`test_hurl_object.py`（14）、`test_topple.py`（15）；更新既有測試與 CLI 快照 |
| 2ee3d00 | API 測試 `tests/api/test_hurl_api.py`（3）：物件＋落點的兩段選取以一個完整的 `use_skill` 表達 |
| （本報告） | 報告 |

（開發期間 main 上另有其他 session 的 `docs/` commit，與本段無關。）

## 2. 交付項目

### 2.1 物件標籤與地圖（7A.1）

- `OBJECT_TAGS` 新增 `penetrable`（木箱、倒木；3C-5b 的穿透使用，本段只加標籤；內容沒有「木牆」）與 `topplable`（石柱、枯樹）。
- 新物件：枯樹 `dead_tree`（`Y`，HP 20：`blocks_move`、`blocks_sight`、`breakable`、`flammable`、`topplable`）、倒塌物 `rubble`（`m`：`blocks_move`、`half_cover`，不可破壞）。石柱加 `topplable`。
- 新核心規則（`content/rules/core.yaml`，初值）：`topple_length: 2`、`topple_damage_dice: 2d6`、`topple_rubble_object: rubble`（載入時檢查物件存在）、`hurl_scatter_radius: 1`。
- 地圖：
  - 可推倒物件：`ruined_fort` 加兩根石柱（缺口前 (4, 2)、(4, 7)）、`dark_forest` 加兩棵枯樹 (3, 4)、(6, 5)、`narrow_halls` 的 4 根石柱變成可推倒並在南走廊加一棵枯樹 (6, 6)。另外 `bridge_chasm`、`cliff_outpost`、`frozen_lake`、`lava_crossing` 原本的石柱也都變成可推倒。
  - 可投擲物件：`oil_depot` 加 3 個木箱（共 9 個 pushable）、`narrow_halls` 加 2 個木箱（共 6 個）。**沒有改 `open_plain`**（見待決 #1）。
  - `scripts/map_push_check.py`：10 張正式地圖全部「通」（見 3.3）。

### 2.2 推倒（7A.3）

- **通用規則**（`engine/effects/world.py::_push_object` → `_topple`）：`topplable` 物件被 `PushEffect` 推到時不移動，往推的方向倒下。會走到這裡的有：互動的推（`Interact mode: push`）、技能的推擊（`push`，不含 `pull`）、風（互動表新規則 `wind_topples_object`，`object_tag: topplable`）。
- 範圍（`topple_line`，只讀狀態，3C-5b 預覽可以直接用）：從物件的下一格起 `topple_length` 格；地圖外、不可走的地形（牆）與致命地形 **跳過**；有 `breakable` 物件的格子照壓（物件受傷）；不阻擋移動的非破壞物件（草叢）不影響；阻擋移動又不能破壞的物件（倒塌物）擋住倒下，停在它之前。
- 結算：發出 `ObjectToppled`（物件、種類、位置、方向、壓住的格子、壓到的單位與物件、倒塌物位置、來源）→ 原物件移除（`ObjectDestroyed`，原因 `toppled`）→ 倒塌物 `ObjectCreated`。觸發表（`triggers._topple_damage`）對壓到的單位各一個 `DamageEffect(cause="topple", dice=2d6)`（物理、套用抗性）＋ `ApplyStatusEffect(prone)`（不擲抵抗），壓到的 `breakable` 物件一個 `DamageObjectEffect(cause="topple")`；全部歸給推的人。
- 倒塌物：原格與壓住的格子中，從最後一格往回找第一個放得下的（沒有單位、沒有其他物件、可走、非致命）；壓到的單位站在最後一格時退一格，都放不下時退回原格。
- 撥開：`topplable` 物件不能撥開（`interact_problem` 回「撥不動：石柱只能推倒，不能撥開」，`interact_options` 一併列出推（合法）與兩個撥開方向（不合法＋原因））；推倒不檢查目標格（倒下的格子有人才是重點）。
- **原語 `topple`**（結構型、rare、固定 6 點、`acts_on: tile`、只能搭配 `single`）：目標必須是射程內看得到的 `topplable` 物件（不必是 `breakable`；以單位為目標拋 `IllegalActionError`），往「施放者 → 物件」的主要軸向倒下（方向型形狀用形狀方向），規則同上。
- 新的傷害原因 `topple`（紀錄「壓傷物理傷害」）、物件摧毀原因 `toppled`／`hurled`。

### 2.3 投擲物件（7A.2）

- 形狀 `object_then_tile`（`targeting: object_tile`，rare，參數 `range` 1–6 ＝ 落點距施放者的上限）：`UseSkill` 同時給 `target_object_id`（被舉起的物件）與 `target_pos`（落點）。物件須 `pushable`、在 `hurl_object` 效果的 `range` 內、看得到；落點在形狀射程與視線內、不是牆、不是物件原本的格子。**物件的飛行路徑不檢查阻擋**。影響範圍只有落點。
- 原語 `hurl_object`（結構型、rare、`allowed_shapes: [object_then_tile]`）：參數 `range`（必填，可舉起的距離）、`dice`（必填）、`knock_prone`（選填，新的參數型別 `bool`）。`SkillDef` 檢查：`hurl_object` 與 `object_then_tile` 必須一起出現、恰好一個、只能是主動技能。
- 結算（`interpreter._Cast.hurl_object`）：命中判定照技能（落點的敵方單位擲命中；空格不擲）；命中的單位受 `dice` 物理傷害（暴擊、格擋、修正規則照常；不加屬性），`knock_prone: true` 時再以 `knock_prone` 原語同一套對抗判定擊倒；然後 `HurlObjectEffect` 讓物件落地：
  - `explosive`：在落點爆炸（`ObjectExploded` 的位置是落點，沿用爆炸觸發表）。
  - 其他 `breakable`：碎掉（`ObjectDestroyed`，原因 `hurled`）。
  - 其他：放在落點；落點有單位或物件時放在 `hurl_scatter_radius`（1）內最近的空格（同距離依 `(y, x)`）；附近沒有空格就摧毀（`hurled`），落點是致命地形也摧毀（`fell`）。
  - 事件 `ObjectHurled`（`outcome`：`exploded`／`shattered`／`placed`／`lost`、`placed_pos`）。
- 預算：新算法 `hurl_object` ＝ 骰子平均 × `hurl_object_discount_permille`（`skill_budget.yaml`，初值 800）＋（`knock_prone` 時）擊倒原語的 3 點。
- 基本動作不能投擲：`Interact` 沒有落點欄位（`extra="forbid"`），其他技能同時帶物件與落點會被拒（「不能指定：target_pos」）。

### 2.4 示範技能與 build（數值皆為初值，未經模擬）

| 技能 | 內容 | 預算 | 裝備 |
|---|---|---|---|
| 念力投擲 `skill_telekinetic_hurl`（rare，法術，AP 2） | `object_then_tile` 射程 4；`hurl_object` range 4、3d6、擊倒；法力 5、冷卻 2 | 72.4% | build_fire（主動第 6 個） |
| 震地推倒 `skill_quake_topple`（rare，武器，AP 1） | `single` 射程 2；`topple`；法力 3、冷卻 2 | 76.9% | build_push（主動第 6 個） |

- 既有的颶風踢、破城衝撞（單體、可以石柱為目標）也會推倒石柱（`test_a_skill_push_topples_the_pillar_away_from_the_caster`）。
- 兩個原語加進 `displace` 骨架的核心原語、`object_then_tile` 加進它的形狀（手寫技能的結構驗證需要）；隨機組合器 **不使用**（`composer_parts._HAND_WRITTEN_PRIMITIVES`／`_HAND_WRITTEN_SHAPES`，在抽籤前排除，所以既有種子的隨機技能不變）。

### 2.5 紀錄文字、API、前端

- CLI／事件文字：`✦ 火焰流英雄 把油桶 (3, 3) 丟向 (6, 5)`（放下時「，落在那裡」／「，彈落到 (x, y)」、沒地方放「，找不到落腳處」）、`✦ 盜賊弓手 推倒了石柱 (7, 5)，往西倒下，壓住 (6, 5)（壓到 …）`、物件摧毀「摔得粉碎／倒下了」、傷害「壓傷物理傷害」；`skills show` 的效果文字涵蓋兩個原語。
- API：**兩段選取以一個完整的 `use_skill`（`target_object_id` ＋ `target_pos`）表達**，`legal_actions` 列出每一組合法的（物件, 落點），客戶端可以依 `target_object_id` 分組做「先選物件、再選落點」；只給物件會回 400。OpenAPI 沒有改變（`UseSkill` 原本就有這兩個欄位；事件在 API 是 `dict`）。
- 前端：只加了枯樹「樹」與倒塌物「礫」的外觀（`glossary.ts`）；兩段選取的介面屬 3C-5b（見待決 #4）。

## 3. 驗收條件逐條（3C-5a）

1. **投擲**（`tests/engine/test_hurl_object.py`，14 個，全過）
   - 落點有單位：`test_the_unit_at_the_landing_tile_is_hit_and_the_crate_shatters`（擲命中、2d6 物理、木箱碎掉、事件順序命中 → 傷害 → 落地）。
   - 空格：`test_an_empty_landing_tile_has_no_roll_and_keeps_the_object`（不擲命中、物件放在落點）。
   - `explosive` 爆炸：`test_a_hurled_oil_barrel_explodes_at_the_landing_tile`（爆炸在落點、3×3 敵人受爆炸傷害）。
   - `breakable` 碎掉：同第一個測試（`ObjectDestroyed` 原因 `hurled`）。
   - 落點被占用時放最近空格：`test_an_occupied_landing_tile_puts_the_object_on_the_nearest_free_tile`（候選依 (y, x)，前兩格被占，放在第三格）。
   - 沒有空格時摧毀：`test_no_free_tile_nearby_destroys_the_object`；落在深淵：`test_landing_in_a_chasm_destroys_the_object`。
   - 不在視線內被拒：`test_the_flight_is_not_blocked_but_the_landing_must_be_in_sight`（飛越牆壁可以、牆後的落點被拒）。
   - 基本動作不能投擲：`test_basic_actions_cannot_hurl`。
   - 其他：`test_hurl_selection_rejections`（太遠、不是 pushable、落點＝原格、超出射程、只給物件、多給方向）、`test_legal_actions_list_object_and_landing_pairs`、`test_a_knocked_down_target_with_the_demo_skill`、`test_hurl_object_and_its_shape_must_come_together`、`test_the_demo_skill_budget_discounts_the_dice_and_adds_the_knockdown`、`test_an_ai_battle_hurls_objects_and_replays`。
   - API：`tests/api/test_hurl_api.py`（`test_legal_actions_carry_object_and_landing_pairs`、`test_posting_a_pair_hurls_the_object`、`test_a_pair_with_only_the_object_is_rejected`）。
2. **推倒**（`tests/engine/test_topple.py`，15 個，全過）
   - 四個方向：`test_a_pushed_pillar_falls_in_the_push_direction`（參數化 4 個；含原物件移除、倒塌物位置、其餘格不留物件、互動 1 AP）。
   - 壓到單位（傷害＋倒地，歸給推的人）：`test_units_under_the_pillar_take_damage_and_fall_prone`。
   - 壓到 `breakable` 物件：`test_a_breakable_object_under_the_pillar_takes_the_same_damage`。
   - 被非破壞物件擋住：`test_a_non_breakable_object_stops_the_fall`。
   - 壓到地圖外（與牆）：`test_tiles_off_the_map_and_walls_are_skipped`。
   - 倒塌物位置：`test_the_rubble_goes_to_the_last_tile_that_can_hold_it`（＋上面幾個測試的 `rubble_pos`）。
   - 撥開被拒：`test_topplable_objects_cannot_be_shoved_aside`（含 `interact_options` 的原因）；另 `tests/engine/test_shove_aside.py` 的石柱撥開。
   - 其他：枯樹 `test_a_dead_tree_falls_too`、技能推擊 `test_a_skill_push_topples_the_pillar_away_from_the_caster`、原語 `test_the_topple_primitive_targets_a_topplable_object_in_range`、風 `test_wind_topples_a_pillar`、重播 `test_a_battle_with_a_topple_is_deterministic_and_replays`。
3. **地圖與示範技能**
   - `uv run python scripts/map_push_check.py`：10 張正式地圖狀態全部「通」，沒有「單次移動會封路」（oil_depot 9 個、narrow_halls 6 個可推動物件）。
   - 手寫技能：`skill_telekinetic_hurl`（`hurl_object`）、`skill_quake_topple`（`topple`）；兩者都被 build 裝備，`tests/content/test_coverage.py` 允許清單維持為空。推倒也可用既有的颶風踢／破城衝撞示範。
4. **`check.py` 全過；重播一致**
   - `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（1952 passed）、client install／typecheck／vitest（78）全部通過。
   - 重播：`trpg battle --map narrow_halls --seed 9 --ally-build build_fire --log-json …` → `trpg battle replay`：「重播驗證通過：70 個動作、204 個事件，最終狀態一致（narrow_halls，種子 9）。」（兩次投擲）；`bridge_chasm` 種子 11 `build_guardian`（敵方盜賊弓手推倒石柱）：「重播驗證通過：161 個動作、426 個事件，最終狀態一致（bridge_chasm，種子 11）。」；測試 `test_an_ai_battle_hurls_objects_and_replays`、`test_a_battle_with_a_topple_is_deterministic_and_replays`。

## 4. 修改既有測試的原因

- `tests/content/test_skill_rules_content.py`：`displace` 骨架的核心原語多了 `hurl_object`、`topple`。
- `tests/engine/test_cover.py::test_new_object_tags`：倒木多了 `penetrable`。
- `tests/engine/test_maneuvers.py::test_interact_rejections`、`tests/engine/test_shove_aside.py::test_shove_aside_not_adjacent_not_pushable_and_no_ap_are_rejected`：原本用石柱當「無法推動」的物件，石柱現在可以推倒，改用矮牆；後者另外斷言石柱「只能推倒，不能撥開」。
- `tests/engine/test_collision.py::test_ai_battles_with_collisions_are_deterministic_and_replay`：`oil_depot` 種子 3 → 1。地圖多了木箱後種子 3 的戰局不再出現撞擊；測試意圖（AI 戰鬥中有撞擊且重播一致）不變。
- `tests/cli/test_budget_cli.py`：技能數 78 → 80（兩處）；`tests/cli/test_battle_cli.py`、`test_skills_cli.py`：`LOG_FORMAT` `/15` → `/16`。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json` 5 筆）：`skills_list`、`skills_show_all`（多 2 個技能）、`battle_bridge_guardian_11`（bridge_chasm 的石柱可以推倒，敵方盜賊弓手推倒了一根）、`battle_halls_storm_9`（narrow_halls 地圖改動）、`battle_oil_depot_fire_7`（oil_depot 地圖改動＋build_fire 多了念力投擲）。其餘 4 筆不變。

## 5. 新增的複雜度 noqa

**無**（沒有新增 C901、PLR0911、PLR0912、PLR0915）。`_Cast.build` 加兩個原語後超過 PLR0912，改成「只需要 `(effect, spec)` 的原語」查表（`_Cast._SIMPLE`）解決，既有的 `# noqa: PLR0911` 保留。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/16`**（本段只升一次）。理由：推石柱、枯樹改為推倒（通用規則），`/15` 的紀錄重播會得到不同結果；另外新增效果 `hurl_object`、事件 `object_hurled`／`object_toppled`、傷害原因 `topple`、摧毀原因 `hurled`／`toppled`、規則包多了物件、形狀、原語與 4 個核心規則欄位。

## 7. 待 PM 決定（最多 10 點）

1. **`open_plain` 沒有加可投擲物件**：規格建議 `oil_depot`、`open_plain`，但 `tests/content/test_map_archetypes.py` 規定平原最多 4 個物件，設計 6.15 也寫念力流「不利的地圖：空曠平原」。改成 `oil_depot` ＋ `narrow_halls`（倉庫型的走廊大廳）。要讓平原也有東西丟需要放寬平原的類型限制。
2. **兩個射程**：效果的 `range` ＝ 可以舉起的物件距離（物件要看得到），形狀的 `range` ＝ 落點距離；示範技能都是 4。落點不能是牆或物件原本的格子；物件高度不檢查。
3. **投擲傷害只有 `dice`**（不加縮放屬性，字面照規格「受 dice 物理傷害」），擊倒用 `knock_prone` 原語同一套對抗判定（會失敗）；預算 ＝ 骰子平均 × 800‰ ＋ 擊倒 3 點，示範技能 72.4%（3d6＋擊倒）。**失手時物件照樣落地**，油桶照樣在落點爆炸（AI 實戰中失手後爆炸仍打到目標）。
4. **API 不暫停**：兩段選取以一個完整的 `use_skill` 表達，`legal_actions` 列出全部（物件, 落點）組合（每個物件約 20–40 個落點），不像 `copy_skill` 那樣暫停。3C-5b 做網頁介面前，網頁上點物件會直接用該物件在 `legal_actions` 裡的 **第一個** 落點（`buildTargets` 每個目標只取第一個動作），可能不是玩家想要的；3C-5b 要改成點物件後再選落點。
5. **散落半徑 1**：「最近的空格」限制在 `hurl_scatter_radius: 1`（4 格）內，否則「沒有空格」永遠不會發生；落在致命地形的非破壞物件直接摧毀（原因 `fell`）。目前內容裡所有 pushable 物件都可破壞，所以「放下／散落／找不到空格」只在測試專用的巨石上發生——要不要加一個不可破壞的可投擲物件（例如石塊）由玩法 PM 決定。
6. **推倒的格子規則**：規格寫「壓到其他物件時，breakable 受傷害，其他物件擋住」；我把 **不阻擋移動的非破壞物件（草叢）** 當成地面，不擋也不受傷（否則一叢草就能擋住倒下的石柱）。致命地形的格子也跳過；高度不影響。被壓的單位倒地 **不擲抵抗**（照規格「受傷害並 prone」）。
7. **倒塌物**：放在最後一個放得下的格子（有單位就往回退，最差在原格）；倒塌物 **不可破壞、永久** 阻擋移動，可能讓窄路被永久堵住（`map_push_check.py` 只模擬推動物件，不模擬推倒）。要不要給倒塌物 HP 或讓它可以再被推倒，請玩法 PM 看。
8. **技能推擊也會推倒**：所有 `push` 效果（不含 `pull`）會推倒影響範圍內每一格的 `topplable` 物件（不需要命中）；目前有 `push` 的技能都是單體，只有以石柱為目標時才會推倒。`topple` 原語限 `single` 形狀、只能以物件為目標，固定 6 點（示範技能 76.9%）。
9. **AI 使用率**（不要求用得好，3C-5b 處理）：build_fire 的念力投擲在 `narrow_halls` 種子 5、9–15 每場 1–2 次，`ruined_fort` 種子 13 一次，`oil_depot` 種子 1–8 都沒有用；build_push 在 `narrow_halls`／`ruined_fort`／`dark_forest` 各 6 個種子都沒有推倒過石柱或枯樹（震地推倒的評分只看到「目標物件有 HP」）。敵方 AI 會用互動推倒石柱（bridge_chasm 種子 11），但那次沒有壓到人。
10. **預算與初值**：`hurl_object_discount_permille: 800`、`topple` 6 點、`topple_damage_dice: 2d6`、`topple_length: 2` 都是初值、未經模擬；隨機組合器不產生兩個原語與 `object_then_tile` 形狀（只給手寫技能，比照改寫規則型）。預覽（`Preview.outcomes`）沒有新增 `object_hurled`／`object_toppled` 種類（網頁預覽屬 3C-5b）。

## 8. 代表性輸出

`uv run trpg battle --map narrow_halls --seed 9 --ally-build build_fire`（輸出第 43–57 行，連續未刪節；火焰流英雄走到南走廊，用念力投擲把 (3, 3) 的油桶丟向 (6, 5) 的盜賊弓手——命中失手，但油桶在落點爆炸，並點燃旁邊的枯樹）：

```
— 火焰流英雄 的回合（AP 3，移動 5，法力 40/40）
  火焰流英雄 施放「火焰箭」（AP 1，法力 6）→ 影響 1 格
    石柱 受到 11 點火焰傷害［骰 3］，HP 60 → 49
  ★ 火焰流英雄 的被動「烈焰護身」觸發（施放帶標籤的技能後，深度 1）（法力 2）
    火焰流英雄 獲得 10 點護盾
  火焰流英雄 從 (0, 3) 移動到 (3, 5)（消耗 5 移動）
  火焰流英雄 施放「念力投擲」（AP 2，法力 5，冷卻 2 回合）→ 影響 1 格
  火焰流英雄 以「念力投擲」攻擊 盜賊弓手2：d20=2 修正 +0 熟練 +2 = 4（目標 11）→ 失手
  ✦ 火焰流英雄 把油桶 (3, 3) 丟向 (6, 5)
  ＊ 油桶 (6, 5) 爆炸了！
  ＊ 油桶 (6, 5) 炸毀！
  (6, 6) 出現了火焰
  枯樹 (6, 6) 著火了（1 次環境回合後燒毀）
    盜賊弓手2 受到 12 點爆炸火焰傷害［骰 6+4］（元素修正 ×1.25），HP 26 → 14
  火焰流英雄 結束回合
```

同一場 `--log-json` 存檔後 `trpg battle replay`：「重播驗證通過：70 個動作、204 個事件，最終狀態一致（narrow_halls，種子 9）。」
