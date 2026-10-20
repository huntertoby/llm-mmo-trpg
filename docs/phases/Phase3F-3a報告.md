# Phase 3F-3a 報告：複合技能「位移 → 動作」（資料格式、結算、選取、預算）

> 規格：`docs/phases/Phase3F計畫.md` 3.1、3.2、3.3、3.5（3F-3a）；設計：`docs/design/06-技能.md` 6.23（基本型）。3.4（AI、工坊選項、網頁）屬 3F-3b，本段沒有做。

## 1. commit

| commit | 內容 |
|---|---|
| f189f07 | schema、驗證、預算：`FollowupSpec`／`SkillDef.followup`／`followup_skill()`、`composite_tax_permille`、`skill_budget` 兩段明細、驗證器的兩段規則、`trpg skills budget`／`skills show`／`skills list` 顯示第二段、工坊檢查 `BudgetSummary.segments`；示範技能「瞬影旋斬」裝在 `hero_fighter`；CLI 快照重錄 2 筆 |
| 5c6cdb1 | 引擎：`UseSkill.followup_target`（`FollowupTarget`）、動作段結算（`skill_followup` 事件、`followup_blocked`／`followup_no_target`）、`legal_actions` 組合、預覽 `landing`／`followup_tiles`、AI 略過複合技能、修正規則的變形不套用在複合技能；`tests/engine/test_composite_skills.py`（35）、`tests/skillgen/test_composite_budget.py`（6） |
| 51de9b9 | API：`PreviewOut.landing`／`followup_tiles`；OpenAPI 與 `client/src/api/schema.d.ts` 重新產生；`tests/api/test_composite_api.py`（2） |
| 88b24c1 | API：`SkillCard.followup`（第二段的一句話）；OpenAPI、`schema.d.ts` 重新產生 |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 資料格式（3.1）

```yaml
# content/skills/skill_shadow_whirl.yaml（節錄）
id: skill_shadow_whirl
name_zh: 瞬影旋斬
tier: 1
rarity: rare
kind: active
skeleton: displace            # 位移段（技能本身）的骨架
category: weapon
weapon_req: melee
ap_cost: 2
scaling_attr: str
shape: {type: ground_tile, range: 4}
effects:
  - {type: teleport}          # 位移段：恰好一個施放者自身位移原語
followup:                     # 動作段（第二段）
  when: after_move            # 本段只有 after_move（預設值）；3F-4 再加 after_action、on_kill、on_hit、delayed
  skeleton: area
  shape: {type: cone, size: 2}
  effects:
    - {type: damage, multiplier_permille: 900}
cost: {mana: 6, cooldown: 3}
```

- **骨架**：位移段用 `displace`（沒有新增 `mobility` 骨架）。`displace` 的核心原語不含 `dash`（它是附帶原語），但位移段固定是一個自身位移原語，所以位移段不跑核心／占比檢查，只檢查骨架是 `displace`、形狀在骨架允許的形狀內（`composite.skeleton`、`skeleton.shape`）。這樣不用動 `displace.yaml`（改核心會影響隨機組合器）。
- **schema（`SkillDef._check_followup`）**：只有主動技能；不能是陷阱、不能有 `cost.on_miss`；位移段恰好一個 `COMPOSITE_MOVES`（`teleport`、`leap`、`dash`、`charge_through`、`shadowstep`）；動作段形狀限 `FOLLOWUP_SHAPES`（`single`、`line`、`cone`、`cross`、`square3`、`ring`），`cross`／`square3` 必須 `range: 0`（以落點為中心）；動作段不能含 `FOLLOWUP_FORBIDDEN`（所有自身位移、`teleport_target`、`swap_any`、`summon`、`zone`、`place_trap`，以及保守加上的 `copy_skill`、`rule_change`、`gamble`、`hurl_object`）；兩段合計 ≤ 4 個效果。`FollowupSpec` 沒有 `followup` 欄位，結構上不能套娃。
- **動作段 = 一個展開的技能**：`SkillDef.followup_skill()` 沿用本技能的 ID、名稱、類別、武器需求、縮放、階級、稀有度與代價，換上動作段的骨架、形狀、效果、條件，並以 **同一套 schema** 驗證（例如動作段的法術傷害沒填元素會被擋下）。引擎、驗證器、預算都以它處理動作段。結果以模組層級快取（依物件 identity，上限 4096 筆）。
- **跨檔案檢查**：`skill_reference_problems` 對動作段再跑一次（訊息前綴 `followup.`）。
- **驗證器**（`validate_skill`）：複合技能走 `_composite_violations`——位移段（骨架、形狀、互斥）＋動作段（照自己骨架的核心、附帶、占比、互斥、改寫型原語與復活規則，規則代碼前綴 `followup.`、訊息前綴「動作段：」）＋稀有度（`rarity.composite` 至少 rare；動作段用到的形狀／原語／狀態的最低稀有度也算進來；效果數上限以兩段合計）＋預算。工坊的「最低稀有度」共用 `rarity_requirements`，所以也會顯示「複合技能（位移 → 動作）」與「動作段的…」。
- **元素連鎖規則**（6.23「同一招不能造環境又引爆」）：本段沒有做。「位移 → 動作」的位移段只能是一個自身位移原語，不會造表面或施加狀態，所以不可能形成連鎖；留給 3F-4（其他種類）。

### 2.2 結算（3.2）

- `use_skill`：先驗證位移段（`checked_area`），再以 **預定落點** 驗證動作段的選取（`followup_selection`；在狀態複本上把施放者放到落點），兩者都合法才支付代價；`skill_used.tiles` 是兩段的聯集。
- 預定落點（`targeting.followup_origin`，依 `followup.when` 分派到 `_FOLLOWUP_ORIGINS`，之後的種類加在同一張表）：`teleport`／`leap` 是選的格子；`dash` 是衝鋒路徑的終點（目標相鄰格）；`charge_through` 是路線停下的格子（被地形擋住時是擋住前的格子，不是選的終點）；`shadowstep` 是選的落點（`choose`）或背後格（`behind`）。
- 位移段照原本規則結算（`_Cast.run()`），然後 `_run_followup`：施放者還站著 **而且就在預定落點** 才結算動作段——發出 `skill_followup`（`origin`、`tiles`、`when`），以落點為原點重新算動作段的範圍並結算（命中、傷害、背刺都照常；同一個技能 ID）。否則發 `effect_fizzled`（`effect_kind: followup`）：`followup_blocked`（被擋下、倒下、沒到落點）或 `followup_no_target`（位移後動作段的選取不再合法，例如單體目標已不在射程）。
- 衝鋒與衝撞在中途被定身、倒地等停下時算「被擋下」，動作段不結算（同 `dash` 規則）；衝撞被地形擋住而停在路線終點（`route.stop`）不算被擋下，以停下的格子為原點。
- 結算完的轉向：動作段有單位目標時面向它，否則沿用位移段的主要目標（衝鋒、瞬步）；近戰命中的轉身與潛行偷襲的解除合併兩段處理。
- 修正規則的變形（`shape_to`、`area_delta`、`allow_self_target`）不套用在複合技能（`modifiers.shaped_skill` 直接回傳原技能，保守做法）。
- 複合技能位移段以單位為目標時（衝鋒、瞬步）不檢查「此技能無法對敵方／友方使用」（位移段本身沒有對目標的效果，目標只是位移的參照）；瞬步仍要求敵人。

### 2.3 選取（3.2）

- `UseSkill.followup_target: FollowupTarget | None`：`direction`（直線、錐形）、`target_id`／`target_object_id`（單體）；以落點為中心的形狀（十字、方陣、環）不用給（給 `target_pos` 的話必須是落點）。一般技能帶 `followup_target` 會被拒絕（「只有複合技能可以指定 followup_target」）。
- `legal_actions`（`targeting._composite_selections`）：位移段每個合法選取 × 動作段在預定落點的每個合法選取。組合數的上限來自形狀本身：方向型只有東南西北 4 個；單體只列落點射程內的目標；以落點為中心的形狀只有 1 個（`followup_target` 為 `null`）。一次列舉只複製一次狀態（之後只改施放者位置）。
- AI（`UtilityAI._skill_candidates`）：略過複合技能（3F-3b 再評估）；`legal_actions` 照常列出，AI 不會選，也不會出錯。

### 2.4 預覽（3.2）

- `Preview.landing`（落點）與 `Preview.followup_tiles`（動作段的影響格）；`affected_tiles`／`affected_units` 含兩段。
- 命中率、暴擊率、傷害範圍：預覽本來就以引擎模擬整個動作，所以動作段的 `attack_rolled`、`damage_dealt` 都在模擬事件裡；命中率以擲骰當下的位置（落點）計算（沿用 `_positions_at_roll`）。期望傷害與擊倒、狀態的機率用「兩段效果接起來」的技能估計（`_preview_skill`）。
- API：`PreviewOut.landing`、`PreviewOut.followup_tiles`；`SkillCard.followup`（第二段的一句話，例如「到達落點後，以落點為原點：錐形（大小 2）：武器傷害 ×0.9（敵方）」）。

### 2.5 預算（3.3）

- `content/skill_budget.yaml`：`composite_tax_permille: 150`（`BudgetRules`，預設 150）。
- `skill_budget`：複合技能走 `_composite_budget`——位移段（`move_segment()`）與動作段（`followup_skill()`）各自完整計算（各自的骨架、形狀倍率、條件、協同），總點數 ＝（位移段 ＋ 動作段）×（1000 ＋ 150）÷ 1000；可用預算照技能本身的 AP 與代價折抵。`BudgetReport.segments`（`SegmentBudget`：標籤、骨架、形狀、效果點數、raw、條件、協同、total）、`composite_tax_permille`。
- `trpg skills budget`：兩段各自列出效果點數與該段點數，再列「複合加成」（見第 7 節）。
- 工坊檢查（`check_draft`）：`BudgetSummary.segments`（`SegmentLine`）與 `composite_tax_permille`。

### 2.6 示範技能

| 技能 | 內容 | 預算 |
|---|---|---|
| 瞬影旋斬 `skill_shadow_whirl`（rare、位移段 displace、武器技近戰、力量、AP 2、法力 6、冷卻 3） | 傳送到 4 格內的空格 → 落點錐形（大小 2）武器傷害 ×0.9 | 位移段 4.00 ＋ 動作段 8.19，×1.15 ＝ 14.02 ÷ 16.52 ＝ **84.9%** |

- 裝在 **單位範本 `hero_fighter`**（原本 5 個主動技能，有一個空欄位），沒有裝進 sim build：所有近戰 build 的主動欄位都已滿（6 個），換掉任何一個都會改變既有種子的 AI 行為（`build_charger`、`build_assassin` 有多個固定種子的戰鬥測試）。因為 AI 不選複合技能，加進 `hero_fighter` 不改變任何戰鬥（7 場 CLI 快照戰鬥逐字相同）。API 試玩用「裝上試玩」：`build_charger` ＋ `custom_skills: [瞬影旋斬]` ＋ `replace_skills: [skill_guard_swap]`（`tests/api/test_composite_api.py`）。3F-3b 整理 build 時再正式裝進 build（見待決 #1）。

## 3. 驗收條件逐條（3.5，3F-3a）

### 驗收 1：schema

| 項目 | 證據（`tests/engine/test_composite_skills.py`） |
|---|---|
| 合法：位移原語 × 動作形狀 | `test_legal_composites_pass_the_schema_and_the_structure_rules`：`teleport`、`leap`、`dash`、`charge_through`、`shadowstep` × 錐形、十字（10 組），schema 通過、驗證器除預算外沒有違規 |
| 不合法：動作段再放位移／召喚／區域 | `test_illegal_composites_are_rejected[...]`：`leap`（「不能套娃」）、`summon`、`zone` |
| 不合法：效果合計超過 4 | 同上：位移 1 ＋ 動作 4（「兩段合計最多 4 個效果」） |
| 不合法：位移段放兩個效果 | 同上：`teleport` ＋ `damage`、只有 `damage`（「位移段只能有一個」） |
| 其他 | 同上：十字 `range` 不是 0、動作段用連鎖、被動技能帶 `followup`；`test_the_followup_is_checked_with_its_own_skeleton_and_the_composite_needs_rare`（動作段 `strike` 骨架配錐形 → `followup.skeleton.shape`；`common` → `rarity.composite`；位移段骨架不是 `displace` → `composite.skeleton`）；`test_the_demo_skill_is_valid_and_equipped` |

### 驗收 2：結算

| 項目 | 測試 |
|---|---|
| 落點為原點的錐形 | `test_teleport_then_cone_uses_the_landing_as_the_origin`（落點前方被打、落點背後與「原位置的錐形」內的敵人沒被打；事件順序 `skill_used` → 傳送 → `skill_followup` → 命中判定） |
| 以落點為中心的形狀 | `test_leap_then_cross_hits_around_the_landing`、`test_a_cross_followup_target_pos_must_be_the_landing` |
| 位移被擋下時動作段不結算 | `test_a_blocked_dash_skips_the_followup`（捕獸夾定身：`dash_blocked`、`followup_blocked`，沒有傷害，紀錄文字）、`test_a_charge_stopped_by_a_rooting_trap_skips_the_followup` |
| `dash`、`charge_through` 停下的位置才是原點 | `test_dash_then_cone_starts_from_the_tile_beside_the_target`（原點是目標相鄰格）、`test_charge_through_stopped_by_a_wall_uses_the_stop_as_the_origin`（選 (6, 3)、牆在 (4, 3)，原點 (3, 3)） |
| 瞬步 → 單體 | `test_shadowstep_then_single_attacks_from_behind`（動作段吃到背刺） |
| `followup_target` 的檢查 | `test_followup_target_is_only_for_composites_and_required_for_directions` |
| 選取 | `test_legal_actions_pair_each_landing_with_four_directions_at_most`、`test_single_followups_list_only_targets_in_reach_of_the_landing`、`test_the_ai_does_not_pick_composites_and_does_not_crash` |

### 驗收 3：預算（`tests/skillgen/test_composite_budget.py`）

- `test_the_total_is_both_segments_plus_15_percent`：三種組合，`total == (位移段 total ＋ 動作段 total) × 115/100`，`segments` 標籤、`usable` 照技能本身。
- `test_the_tax_is_150_permille_in_the_content`、`test_each_segment_uses_its_own_shape_multiplier`（錐形 2 ×1.3、十字 ×1.8）。
- `trpg skills budget` 顯示明細：`test_the_cli_budget_shows_both_segments_and_the_tax`（輸出見第 7 節）。
- 工坊檢查：`test_the_workshop_check_lists_both_segments`、`test_a_common_composite_is_flagged_by_the_workshop_check`。

### 驗收 4：預覽、重播、check

- 預覽與實際一致：`test_the_preview_shows_both_ranges_and_matches_the_result`（`landing`、`followup_tiles` ⊂ `affected_tiles`；預覽的目標＝實際被打的單位；`skill_used.tiles`＝預覽範圍；實際傷害落在預覽的最少–最多之間）；API：`tests/api/test_composite_api.py::test_cast_a_composite_through_the_api_and_replay_it`（預覽 `landing`、`followup_tiles`，施放後事件有 `skill_followup`、文字含「第二段」）。
- 重播：`test_a_battle_with_a_composite_cast_replays_exactly`（`test_flat_6x6` 種子 2，主角第一次能打到敵人時施放瞬影旋斬，其餘交給 AI；`replay` 與經過 `BattleLog` JSON 往返後的重播，最終狀態逐字一致）；API 戰鬥紀錄 `cmd_replay`「重播驗證通過」。
- `uv run python scripts/check.py`：全部通過（第 8 節）。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/cli/test_budget_cli.py` | 技能數 141 → 142（新增瞬影旋斬） |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 2 筆：`skills_list`、`skills_show_all`（新增技能；列表多「→ 第二段：…」）。**7 場戰鬥快照全部沒變**（AI 不選複合技能，`hero_fighter` 多一個技能不影響戰鬥） |
| `tests/api/test_routes.py` | 預覽多 `landing`、`followup_tiles` 兩個欄位 |
| `tests/narrative/test_skills_text.py` | 加一行：`SkillCard.followup` 只在複合技能有值 |

## 5. 新增的複雜度 noqa

**沒有新增 C901、PLR0911、PLR0912、PLR0915。** `mobility.self_move_landing` 有 `# noqa: PLR0917`（6 個位置參數；不屬複雜度類，同模組其他函式的慣例）。

## 6. `LOG_FORMAT`

維持 **`/34`**。新增的都是有預設值的欄位（`SkillDef.followup`、`UseSkill.followup_target`）與新事件 `skill_followup`；舊紀錄照常讀取與重播（AI 沒有改變、`hero_fighter` 多的技能存在紀錄的 `setup` 裡，舊紀錄的範本不受影響）。新紀錄只有在用了複合技能時才含新欄位與新事件，舊版程式讀不了這種紀錄，但這是向前相容，不是重播一致性的問題；升版會讓 roguelite 戰鬥中存檔全部失效（`save.engine != LOG_FORMAT`），所以不升（見待決 #9）。

## 7. CLI 與紀錄輸出節錄

```text
$ uv run trpg skills budget skill_shadow_whirl
瞬影旋斬（skill_shadow_whirl）  階級 T1  稀有度 稀有  骨架 displace  AP 2
  【位移段】骨架 displace  形狀 ground_tile
    1. teleport        固定                形狀 ×1     對象 ×1    條件 ×1     ＝ 4.00（基礎 4.00）
    raw 4.00 × 條件 無 × 協同 無 ＝ 位移段點數 4.00
  【動作段】骨架 area  形狀 cone
    2. damage          武器 ×0.9           形狀 ×1.3   對象 ×1    條件 ×1     ＝ 8.19（基礎 6.30）
    raw 8.19 × 條件 無 × 協同 無 ＝ 動作段點數 8.19
  複合加成 +150‰：（4.00 ＋ 8.19）× (1000 + 150) ÷ 1000 ＝ 14.02
  ...
  total ＝ 兩段點數加總 × 複合加成 ＝ 14.02
  可用預算 ＝ tier_budget 14 × AP 係數 1.00 × (1000 + 折抵 180‰) ÷ 1000 ＝ 16.52
  比例 ＝ total ÷ 可用預算 ＝ 84.9%（合格區間 70.0%–100.0%）→ 合格
  驗證：通過
```

施放（`test_flat_6x6` 種子 2，重播測試的那一場；動作與事件文字）：

```text
動作：{'unit_id': 'unit_0001', 'type': 'use_skill', 'skill_id': 'skill_shadow_whirl',
       'target_pos': {'x': 2, 'y': 2}, 'followup_target': {'direction': 'east'}}
  戰士 施放「瞬影旋斬」（AP 2，法力 6，冷卻 3 回合）→ 影響 5 格
  戰士 被傳送到 (2, 2)
  ✦ 戰士 在 (2, 2) 接著施展「瞬影旋斬」的第二段→ 影響 4 格
  戰士 以「瞬影旋斬」攻擊 盜賊弓手：d20=4 修正 +0 熟練 +2 = 6（目標 11）→ 失手
```

## 8. 檢查

- `uv run python scripts/check.py`（HEAD 88b24c1）：ruff check、ruff format --check、mypy、lint-imports、pytest（**3082** 個）、client install、client typecheck、vitest（**191** 個）全部通過——「全部檢查通過。」
- 3F-3b 需要的：AI 評估、工坊選項推導（「要不要接動作段」）、戰鬥網頁兩段選取都還沒做；前端只重新產生了型別。

## 9. 待 PM 決定（最多 10 點）

1. **示範技能裝在 `hero_fighter`，沒有進 sim build**：近戰 build 主動欄位都滿，換掉任何一個會改變既有種子的 AI 戰鬥。3F-3b 讓 AI 會用複合技能後，再決定換進哪個 build（建議 `build_charger` 換下 `skill_guard_swap`，或 `build_assassin`）。
2. **位移段骨架用 `displace`、不另開 `mobility`**；位移段不跑核心與占比檢查（`dash` 在 `displace` 是附帶原語）。
3. **動作段禁用清單比規格多**：除了位移、召喚、區域、陷阱，另禁 `copy_skill`、`rule_change`、`gamble`、`hurl_object`（需要另外選取或改變整個施放流程）。另外複合技能不能有 `cost.on_miss`、不能是陷阱。
4. **以落點為中心的 `cross`／`square3` 規定 `range: 0`**，`followup_target` 不用給；若想要「落地後再對射程內某格放十字」需要另外決定。
5. **衝鋒、衝撞中途被定身／倒地即視為被擋下**（動作段不結算）；被地形擋住而停在路線的停點則照常結算（停點就是原點）。
6. **位移段以單位為目標時（衝鋒）敵我都可以選**（位移段本身不影響目標）；所以「衝到隊友身邊再放錐形」是合法的。瞬步仍要求敵人。
7. **修正規則的變形（`shape_to`、`area_delta`、`allow_self_target`）不套用在複合技能**（保守做法）；其他修正（傷害‰、命中、冷卻、射程……）照常以技能 ID 套用到兩段。
8. **`legal_actions` 沒有額外的硬上限**：組合數由形狀限制（方向 4 個、單體只列落點射程內、中心形狀 1 個）。傳送射程 4 的錐形技能約為「落點數 × 4」（空曠地圖約 150 個動作）。3F-3b 的 AI 若嫌多，再加候選上限。
9. **`LOG_FORMAT` 維持 `/34`**（理由見第 6 節）。若 PM 希望「新欄位一律升版」，改成 `/35` 只需改一行與兩個測試，但 roguelite 戰鬥中存檔會失效。
10. **元素連鎖規則（6.23）本段沒有實作**：「位移 → 動作」的位移段不會造表面或狀態，不可能連鎖；3F-4 的其他種類再做（3F-4 規格已寫）。
