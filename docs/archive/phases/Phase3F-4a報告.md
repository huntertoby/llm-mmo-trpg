# Phase 3F-4a 報告：複合技能的四種即時第二段（打帶跑、聚集、擊殺接續、命中加碼）

> 規格：`docs/phases/Phase3F計畫.md` 0.3、0.4、4.1、4.3（3F-4a）；設計：`docs/design/06-技能.md` 6.23。4.2（延遲段、AI 評估、工坊、網頁）屬 3F-4b，本段沒有做；API 已能完成 `pending` 選取，OpenAPI 與 `client/src/api/schema.d.ts` 已重新產生。規格與設計沒有衝突。

## 1. commit

| commit | 內容 |
|---|---|
| 363105d | schema（`followup.when` 五種、各種類的結構檢查）、驗證器（各段依種類檢查）、預算（觸發機率、元素連鎖加價 `composite_self_combo_permille`、`skillgen/combo.py`）、`trpg skills budget` 與工坊檢查的明細；引擎（`engine/skills/followups.py`、`_run_second`、`pending` 種類 `followup`、`Decision.followup_target`、`resume` 的接受路徑、預覽、`accept_all`、AI 略過新種類）；敘事文字；四個示範技能與裝備；測試（`tests/engine/test_composite_followups.py` 34 個、`tests/skillgen/test_composite_followup_budget.py` 10 個）與既有測試修改、CLI 快照重錄 2 筆 |
| 25684be | API：`BattleResponse.followup_options`、`DecisionRequest.followup_target`；OpenAPI、`schema.d.ts` 重新產生；`tests/api/test_followup_api.py`（3 個） |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。

## 2. 交付項目

### 2.1 資料格式（四種的範例）

`followup.when` 由 `after_move` 擴充為 `after_move | after_action | after_gather | on_kill | on_hit`（`FollowupWhen`）。檢查以 `content/skills.py` 的 `_FOLLOWUP_CHECKS` 依種類分派（3F-3a 的「位移 → 動作」規則原封不動搬進 `_check_after_move`）。

```yaml
# 動作 → 位移（打帶跑）：content/skills/skill_retreating_slash.yaml（節錄）
skeleton: area
shape: {type: cone, size: 2}
effects: [{type: damage, multiplier_permille: 800}]
followup:
  when: after_action
  skeleton: displace
  shape: {type: ground_tile, range: 2}
  effects: [{type: leap}]          # 第二段只能是一個自身位移原語；落點由施放者選

# 聚集 → 範圍打擊：skill_gravity_burst.yaml
skeleton: displace
shape: {type: ring, radius: 2}
effects: [{type: pull, distance: 1}]   # 聚集段只能是一個 pull；環形的聚集點是施放者
followup:
  when: after_gather
  skeleton: area
  shape: {type: square3, range: 0}     # 以聚集點為中心；range 必須等於聚集段（環形為 0）
  effects: [{type: damage, dice: 1d12, element: fire}]

# 擊殺 → 接下一段：skill_death_spiral.yaml
skeleton: strike
shape: {type: single, range: 2}
effects: [{type: damage, dice: 2d6, element: fire}]
followup:
  when: on_kill
  skeleton: strike
  shape: {type: single, range: 3}
  effects: [{type: dash}, {type: damage, dice: 3d6, element: fire}]   # 可以先位移再動作

# 命中 → 加碼段：skill_armor_break_combo.yaml
skeleton: strike
shape: {type: single, range: 1}
effects:
  - {type: damage, dice: 1d8, element: lightning}
  - {type: apply_status, status: vulnerable, duration: 1}
followup:
  when: on_hit
  skeleton: area
  shape: {type: cone, size: 2}         # 自動朝命中的目標
  effects: [{type: damage, dice: 1d6, element: lightning}]
```

各種類的結構規則（schema）：

| `when` | 第一段 | 第二段 |
|---|---|---|
| `after_move` | 恰好一個自身位移（不變） | 動作；形狀 `FOLLOWUP_SHAPES`，十字／方陣 `range: 0` |
| `after_action` | 動作；不能有 `FOLLOWUP_FORBIDDEN`（含自身位移） | 恰好一個自身位移（`COMPOSITE_MOVES`），形狀照該原語 |
| `after_gather` | 恰好一個 `pull`；形狀 `cross`／`square3`（聚集點＝選的中心格）或 `ring`（聚集點＝施放者） | `cross`／`square3`，`range` 等於聚集段的 `range`（環形為 0） |
| `on_kill` | 動作，必須有 `damage` | 動作或位移（`FOLLOWUP_SHAPES` ＋ `ground_tile`；可含一個自身位移，例如衝鋒接傷害） |
| `on_hit` | 動作，必須有 `damage` | 動作；形狀 `FOLLOWUP_SHAPES`，十字／方陣 `range: 0` |

共同：主動、不是陷阱、沒有 `cost.on_miss`、兩段合計 ≤ 4 個效果、第二段以 `followup_skill()` 用同一套 schema 檢查。驗證器（`_composite_violations`）：只有一個位移原語的段（位移段）與聚集段只檢查骨架 `displace`、形狀與互斥（聚集段的形狀由 schema 限定，`displace` 骨架本身沒有環形）；其他段照自己的骨架完整檢查。稀有度原因「複合技能（動作 → 位移）」等依種類命名。

### 2.2 結算（`engine/skills/interpreter.py` 的 `_run_second`、`engine/skills/followups.py`）

第一段照一般技能結算後：

1. 施放者倒下 → `effect_fizzled`（`followup_caster_down`），第二段不結算。
2. 觸發條件：`on_kill` 要第一段的事件中有被施放者攻擊傷害的敵人倒下（同技能內 `on_kill` 的判定）；`on_hit` 要第一段命中敵人。不成立 → `followup_not_triggered`。`after_action`、`after_gather` 一定結算。
3. 第二段的選取與原點：
   - `after_action`、`on_kill`：從施放者 **目前的位置** 選（原點＝施放者位置；規格讓實作者定的 `on_kill` 起算點選施放者）。動作帶 `followup_target` 就直接用（AI、重播）；沒帶時：沒有任何合法選取 → `followup_no_target`；預覽 → 只算到第二段之前；正式結算 → **暫停**（`Pending.kind == "followup"`）。
   - `after_gather`：以聚集點為中心（`gather_pick`），不能帶 `followup_target`。
   - `on_hit`：自動對命中的同一個目標（依單位 ID 的第一個命中的敵人）——單體選它、直線／錐形朝它的方向（`facing_between`）、十字／方陣以施放者為中心；不能帶 `followup_target`。
4. 選取在當下不合法 → `followup_no_target`；合法 → `skill_followup`（`when`、`origin`、`tiles`）＋第二段的事件。

`pull` 本來就朝中心格型的中心拉（`skill_primitives.yaml`），所以聚集不需要改引擎的拉扯規則。

### 2.3 `pending` 選取（同 `copy_skill` 的做法，但暫停在第一段之後）

- `legal_actions` 對 `after_action`／`on_kill` 只列第一段的選取（`followup_target: null`）；`after_gather` 的影響範圍含以聚集點為中心的打擊段；`on_hit` 只列第一段。
- 玩家送出沒有 `followup_target` 的動作 → 第一段結算 → 暫停（狀態顯示到第一段為止，代價已付）。`resume` 的 `Decision`：
  - `accept: true` ＋ `followup_target`：先在暫停的狀態檢查選取（`second_problem`；不合法拋 `IllegalActionError`，暫停不變），再以「原動作＋`followup_target`」從動作之前的狀態重新結算（結算確定，第一段結果相同），只回傳暫停之後的事件。結果與一次帶完整選取的動作逐位元相同（測試）。
  - `accept: false`：走一般的決定流程，重新結算時第二段取用這個決定，發出 `followup_declined`（只放棄第二段）。
  - `accept: true` 沒給選取：`IllegalActionError`。
- `runner.accept_all`（自動對戰、未指定決策時）取第一個合法選取，沒有時放棄。
- API：`BattleResponse.followup_options`（`followup_target` ＋ `tiles`）、`DecisionRequest.followup_target`；暫停時 `/actions` 回 409、壞選取 `/decision` 回 400。

### 2.4 預覽

`after_move` 照舊（以施放前推算落點）。其他種類取最多後果的模擬裡的 `skill_followup` 事件當 `landing`（第二段原點）與 `followup_tiles`；第二段沒結算（沒觸發、或還沒選目標）時為空。`affected_tiles` 已含模擬中兩段的範圍。

### 2.5 預算

- `after_action`、`after_gather`：（第一段 ＋ 第二段）× 1.15（同基本型）。
- `on_kill`：（第一段 ＋ 第二段 × `on_kill_expected_permille` 300‰）× 1.15；`on_hit`：第二段 × `modifier.hit_rate_permille` 600‰（「預估命中率」只有這個既有係數）。
- 元素連鎖：再 ×（1000 ＋ `composite_self_combo_permille`）÷ 1000，初值 1000（翻倍），放 `content/skill_budget.yaml`。
- `SegmentBudget.chance_permille`、`BudgetReport.self_combo_permille`／`self_combo_reasons`；`trpg skills budget` 顯示「× 觸發機率 300‰」「× (1000 + 連鎖加價 1000) ÷ 1000」與每條「連鎖：…」；工坊檢查 `SegmentLine.chance_permille`、`BudgetSummary.self_combo_permille`／`self_combo_reasons`。
- 段名：位移段／動作段（位移 → 動作）、動作段／位移段、聚集段／打擊段、第一段／擊殺後的第二段、第一段／命中後的第二段。

### 2.6 元素連鎖規則的做法（6.23「同一招不能自己造環境又引爆它」）

**選擇：不拒絕，預算加價**（`skillgen/combo.py` 的 `self_combo_reasons`）。判斷只看技能資料明寫的東西：

- 第一段產生的：`create_surface` 的表面、`apply_status` 的狀態（含巢狀的 `then`、賭注分支、擊殺時效果）。
- 第二段的：效果的 `element`、`create_surface` 的表面、`consume_status` 的狀態。
- 形成連鎖：`interactions.yaml` 中 `trigger: element` 的規則，元素是第二段的元素、而 `surface`（或 `unit_surface`）是第一段的表面（例：油 → 火 `fire_ignites_oil`）；`trigger: surface_created` 的規則，第二段造的表面遇到第一段的表面；第一段的狀態的 `removed_by_element` 含第二段的元素（例：冰凍 → 火）；第二段 `consume_status` 消耗第一段施加的狀態。
- 武器傷害沒寫元素時繼承武器（施放前不知道），不算。順序是單向的（第二段造、第一段引爆不可能發生）。
- 選加價而不是拒絕：加價 1000‰ 讓這種技能幾乎一定超出預算（等於實質禁止），但保留之後用模擬調低的空間，也讓工坊能顯示原因而不是只說「不合法」。四個示範技能與 3F-3 的兩個都沒有連鎖（測試）。

### 2.7 示範技能與裝備

| 技能 | 種類 | 內容 | 預算 | 裝在 |
|---|---|---|---|---|
| 回馬斬 `skill_retreating_slash`（武器技近戰、T1、AP 2、法力 5、冷卻 3） | 動作 → 位移 | 錐形 2 武器 ×0.8 → 跳躍 2 格（自選落點） | （7.28 ＋ 3.00）× 1.15 ＝ 11.82 ÷ 16.45 ＝ 71.9% | 單位範本 `hero_fighter`（原本 5 個主動） |
| 引力爆 `skill_gravity_burst`（法術、T2、AP 2、法力 7、冷卻 3） | 聚集 → 範圍打擊 | 環形 2 拉 1 格 → 以自己為中心方陣 1d12 火 | （4.84 ＋ 13.00）× 1.15 ＝ 20.52 ÷ 21.33 ＝ 96.2% | `build_fire`（原本 5 個主動） |
| 死亡迴旋 `skill_death_spiral`（法術、T1、AP 2、法力 5、冷卻 3） | 擊殺 → 接下一段 | 單體 2 格 2d6 火 → 擊殺時衝到 3 格內敵人身邊 3d6 火 | （7.00 ＋ 13.50 × 0.3）× 1.15 ＝ 12.71 ÷ 16.45 ＝ 77.2% | `build_bomber`（原本 5 個主動） |
| 破甲連擊 `skill_armor_break_combo`（法術、T1、AP 2、法力 5、冷卻 2） | 命中 → 加碼段 | 單體 1 格 1d8 雷＋易傷 1 → 命中時朝目標錐形 2 1d6 雷 | （7.47 ＋ 4.55 × 0.6）× 1.15 ＝ 11.74 ÷ 15.75 ＝ 74.5% | `build_striker`（原本 5 個主動） |

- 照 3F-3a 的做法：AI 這段不用新種類，所以裝在 **主動欄位有空位** 的地方，不換下任何技能、不改變既有戰鬥（7 場 CLI 戰鬥快照逐字相同，包括 `battle_oil_depot_fire_7`、`battle_swamp_striker_5`）。
- 近戰 build 的主動欄位全滿、只有 `hero_fighter` 有一格近戰空位，所以只有回馬斬照規格做成近戰武器技；死亡迴旋、破甲連擊做成法術（`weapon_req: any`）裝在法杖 build，引力爆本來就是法術（見待決 #1）。

### 2.8 AI

`composite_estimate` 對新種類一律回傳 `None`（不納入候選），AI 不會選，也不會出錯（`test_the_ai_does_not_use_the_new_kinds_yet`）；`legal_actions` 照常列出。3F-4b 再評估。

## 3. 驗收條件逐條（4.3，3F-4a）

| 條件 | 結果與證據 |
|---|---|
| 四種 `when` 的結算 | `tests/engine/test_composite_followups.py`：`test_after_action_pauses_for_the_landing_after_the_action`（錐形先結算、暫停、選落點後跳到 (1, 3)、事件 `skill_followup(when=after_action, origin=(3,3))`）、`test_after_gather_pulls_then_bursts_around_the_gather_point`（(5,3)→(4,3)、(3,1)→(3,2)，環外不動，方陣打到兩人）、`test_on_kill_asks_for_the_next_target_only_after_a_kill`（擊倒後暫停、衝到 (3,5) 打下一個）、`test_on_hit_follows_up_toward_the_same_target`（錐形範圍 (3,3)、(4,2)、(4,3)、(4,4)，目標被打兩次、身後的敵人被打、錐形外的不被打） |
| 不觸發時第二段不結算 | `test_on_kill_does_nothing_without_a_kill`（`followup_not_triggered`、帶了 `followup_target` 也不動）、`test_on_kill_without_a_next_target_does_not_pause`（`followup_no_target`）、`test_on_hit_does_nothing_on_a_miss`、`test_after_action_does_not_happen_when_the_caster_falls`（還擊打倒施放者 → `followup_caster_down`） |
| schema | `test_legal_kinds_pass_the_schema_and_the_structure_rules`（7 組合法）、`test_illegal_kinds_are_rejected`（9 組不合法：第一段有位移、第二段不是單一位移、聚集段不是單一 pull、聚集形狀、聚集射程不同、第一段沒傷害、on_hit 第二段放跳躍、第二段放召喚、合計超過 4 個效果） |
| 元素連鎖規則 | `tests/skillgen/test_composite_followup_budget.py`：`test_oil_then_fire_doubles_the_points`、`test_a_status_the_second_element_removes_is_a_combo`、`test_no_combo_without_an_interaction` |
| 預算折算 | `test_the_total_is_first_plus_second_times_the_chance_plus_15_percent`（四個示範）、`test_the_chances_come_from_the_existing_coefficients`、`test_the_cli_budget_shows_the_chance_and_the_combo`、`test_the_workshop_check_lists_the_chance_and_the_combo` |
| `pending` 選取 | 引擎：暫停、`legal_actions` 為空、`state_to_json` 往返、接受、與一次帶完整選取逐位元相同（`test_after_action_pauses_…`、`test_on_kill_asks_…`）、壞選取與沒給選取保持暫停、放棄只略過第二段且代價照付（`test_after_action_bad_choice_keeps_the_pause_and_decline_skips_the_move`）。API：`tests/api/test_followup_api.py` 3 個（`followup_options`、GET 讀回、409、400、完成、放棄） |
| 重播 | `test_a_battle_with_a_paused_followup_replays_exactly`（`run_battle` 中主角施放不帶第二段的回馬斬、`accept_all` 回答；`replay` 與 `BattleLog` JSON 往返後重播逐字一致）；API：`test_the_decision_completes_the_slash_and_the_log_replays`（`trpg battle replay` 的 `cmd_replay`「重播驗證通過」） |
| 每種一個示範技能裝進 build | `test_each_demo_skill_is_valid_and_equipped[4 個]`（驗證器零違規、裝在 2.7 表的位置） |
| 預覽 | `test_after_gather_preview_shows_the_burst`、`test_on_hit_preview_shows_the_shockwave` |
| `check.py` 全過 | `uv run python scripts/check.py`（HEAD 25684be）：ruff、format、mypy、lint-imports、pytest **3146** 個、client install／typecheck、vitest **206** 個——「全部檢查通過。」 |

## 4. 修改既有測試與快照的原因

| 檔案 | 原因 |
|---|---|
| `tests/engine/helpers.py` | 新增 `answered(result)`：暫停時以 `accept_all` 回答到不再暫停 |
| `tests/engine/test_determinism.py`、`test_skill_determinism.py`、`test_status_determinism.py` | 亂數走訪 `legal_actions` 的測試：`hero_fighter` 有了回馬斬，列出的動作沒帶第二段、結算會暫停；改成暫停時用 `answered` 回答（`test_resolve_does_not_modify_input_state` 原本斷言「一定不暫停」，改為「暫停只會是 `followup`，回答後輸入仍不變」） |
| `tests/api/test_routes.py` | 決定步驟的 JSON 多了 `followup_target: null` |
| `tests/cli/test_budget_cli.py` | 技能數 143 → 147 |
| `tests/cli/test_striker_trapper_battle.py` | `build_striker` 技能數 6 → 7（破甲連擊） |
| `tests/skillgen/test_workshop_options.py` | `test_every_shipped_skill_fits_the_options` 略過 3F-4a 的四種（工坊選項推導是 3F-4b） |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 `skills_list`、`skills_show_all`（新增 4 個技能）；7 場戰鬥快照不變 |

## 5. 新增的複雜度 noqa

**沒有新增** C901、PLR0911、PLR0912、PLR0915。`interpreter._run_second` 有 `# noqa: PLR0917`（6 個位置參數，不屬複雜度類；同模組的慣例）。

## 6. `LOG_FORMAT`

維持 **`/34`**。新增的都是有預設值的欄位（`Decision.followup_target`）、既有 Literal 多一個值（`Pending.kind`／`PendingResolution.kind` 的 `followup`）與新的 `effect_fizzled.reason` 字串（`followup_not_triggered`、`followup_caster_down`、`followup_declined`；`reason` 是 `str`）；舊紀錄照常讀取與重播（AI 沒有改變，範本的改動只影響新建立的戰鬥）。升版會讓 roguelite 戰鬥中存檔失效，所以不升。

## 7. CLI 輸出節錄

```text
$ uv run trpg skills budget skill_armor_break_combo
破甲連擊（skill_armor_break_combo）  階級 T1  稀有度 稀有  骨架 strike  AP 2
  【第一段】骨架 strike  形狀 single
    1. damage          1d8 平均            形狀 ×1     對象 ×1    條件 ×1     ＝ 4.50（基礎 4.50）
    2. apply_status    vulnerable 4×0.5    形狀 ×1     對象 ×1    條件 ×1     ＝ 2.00（基礎 2.00）
    raw 6.50 × 條件 無 × 協同 damage+debuff ×1.15 ＝ 第一段點數 7.47
  【命中後的第二段】骨架 area  形狀 cone
    3. damage          1d6 平均            形狀 ×1.3   對象 ×1    條件 ×1     ＝ 4.55（基礎 3.50）
    raw 4.55 × 條件 無 × 協同 無 ＝ 命中後的第二段點數 4.55
  複合加成 +150‰：（7.47 ＋ 4.55 × 觸發機率 600‰）× (1000 + 150) ÷ 1000 ＝ 11.74
  ...
  比例 ＝ total ÷ 可用預算 ＝ 74.5%（合格區間 70.0%–100.0%）→ 合格
  驗證：通過
```

回馬斬兩段選取（引擎，測試場景：戰士在 (3, 3)、盜賊在 (4, 3)、(5, 4)）：

```text
動作： {"unit_id":"unit_0001","type":"use_skill","skill_id":"skill_retreating_slash","direction":"east"}
  戰士 施放「回馬斬」（AP 2，法力 5，冷卻 3 回合）→ 影響 4 格
  戰士 以「回馬斬」攻擊 盜賊1：d20=6 修正 +0 熟練 +2 = 8（目標 11）→ 失手
  戰士 以「回馬斬」攻擊 盜賊2：d20=3 修正 +0 熟練 +2 = 5（目標 11）→ 失手
暫停： followup skill_retreating_slash
決定： {"type":"decision","unit_id":"unit_0001","accept":true,"followup_target":{"target_pos":{"x":1,"y":3}}}
  ✦ 戰士 在 (3, 3) 接著施展「回馬斬」的第二段→ 影響 1 格
  戰士 跳躍到 (1, 3)
```

## 8. 待 PM 決定（最多 10 點）

1. **示範技能的裝備與型態**：近戰 build 主動欄位全滿，照 3F-3a 裝在有空位的地方（不換技能、不改戰鬥）：回馬斬 → `hero_fighter`；引力爆 → `build_fire`；死亡迴旋、破甲連擊做成 **法術**（`weapon_req: any`）→ `build_bomber`、`build_striker`。3F-4b 讓 AI 會用後，若要改成近戰武器技並換進近戰 build，再決定換下哪一招。
2. **`on_kill` 第二段從施放者的位置起算**（規格讓實作者定）；第二段可含一個自身位移（死亡迴旋＝衝鋒＋傷害）。「擊殺」＝第一段攻擊造成傷害的任何敵人倒下（不限選的目標）。
3. **`on_hit` 的「同一個目標」**：第一段命中的敵人中依單位 ID 的第一個；錐形／直線朝它的方向（兩軸距離相同時取左右），十字／方陣以施放者為中心。第二段不能帶 `followup_target`。
4. **聚集段只能是一個 `pull`**（像位移段只能是一個位移），形狀 `cross`／`square3`／`ring`；`displace` 骨架的形狀表沒有環形，聚集段不檢查骨架形狀表（schema 限定）。打擊段的 `range` 必須等於聚集段（中心一定在射程內）。十字／方陣的聚集只能拉 1 格內的敵人，意義不大，示範用環形（以施放者為中心）。
5. **`after_action` 的第二段只能是一個自身位移**，不能接動作；落點不限「往後」（回馬斬的「後跳」由玩家自己選格）。
6. **元素連鎖選「預算加價」不選「schema 拒絕」**（理由見 2.6），只看資料明寫的表面、狀態與元素；武器繼承的元素不算。
7. **`legal_actions` 對 `after_action`／`on_kill` 只列不帶第二段的動作**（同 `copy_skill`），因此所有自動走訪 `legal_actions` 的程式要能回答 `pending`（`runner.advance` 已用 `accept_all`；三個亂數走訪測試已改）。AI 用的展開（像 `copy_skill` 的 `expand_copy`）留給 3F-4b。
8. **放棄第二段 `accept: false` 只略過第二段**（第一段已結算、代價已付），發出 `followup_declined`；暫停中沒有預覽（`/preview` 回 409），網頁要預覽第二段可在 3F-4b 加（同 `copy_skill` 的 `_preview_copy`）。
9. **觸發機率**：`on_hit` 用 `modifier.hit_rate_permille`（600‰，修正規則的預估命中率）——預算裡唯一的既有命中率係數；`composite_self_combo_permille` 初值 1000。皆未經模擬。
10. **`LOG_FORMAT` 維持 `/34`**（理由見第 6 節）。
