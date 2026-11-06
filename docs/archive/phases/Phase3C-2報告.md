# Phase 3C-2 報告：修正規則（修正型被動 ＋ 改造型技能）

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| aeb6876 | 內容層：`kind: modifier`、`SkillDef.modifiers`（`ModifierSpec`／`ModifierTarget`／`ModifierChange`）、被動欄位 2 → 3（修正技能算被動欄位）、骨架 `modifier`、`core.yaml` 的 `max_displace_distance`、`skill_budget.yaml` 的 `modifier` 預算段、驗證器、中文描述（`trpg.narrative.skills.modifier_summary`、`SkillCard.modifiers`）、CLI `skills list／show／budget`、4 個示範技能與 build 裝備、`tests/content/test_modifier_schema.py` |
| 255e07d | 引擎：`trpg.engine.modifiers`（新模組）與各套用點（普攻、藉機攻擊、推擊、絆倒、互動、技能施放）、命中後效果走被動觸發管線、預覽（命中率、傷害、AP、射程）、API `PreviewOut.ap_cost／reach`、重新產生 `openapi.json`／`schema.d.ts`、CLI 快照重錄、`tests/engine/test_modifiers.py` |
| e8cebb1 | 前端：技能卡片顯示「修正：…」、預覽最後一行顯示修正後的「AP n　射程 m」；vitest 新增 1 個 |
| 15c7860 | 預算說明的動作名稱改中文 |
| （本報告） | 報告 |

（開發期間 main 上另有 PM 的文件 commit `bf1d930`～`9b5e4fa`，我沒有改動它們；第 4 節規格內容未變，只把後續段號改為 3C-3a／3C-6。）

## 2. 資料格式與設計理由（之後很難改，請 PM 特別看這節）

```yaml
kind: modifier            # 裝在被動欄位、不花 AP、沒有 trigger
skeleton: modifier        # 新骨架（第 13 個；min_rarity: epic）
shape: {type: self}       # 固定
effects: []               # 必須為空：效果寫在 modifiers
cost: 省略                # 必須為空（沒有法力、冷卻……）
modifiers:                # 1～2 條
  - applies_to:           # 至少一項，多項為「或」
      actions: [attack, shove, trip, interact]
      skill_tags: [push]
      all_attacks: false  # 普攻 ＋「有對敵方傷害效果」的技能 ＝ 修正型被動
      all_skills: false   # 施放的所有技能（新增，見待決 #2）
    condition: {type: target_has_status, status: burning}   # 沿用 skill_conditions.yaml，可省略
    change: {damage_permille: 100}                          # 恰好一種
```

- **放在 `SkillDef` 而不是另開資料表**：修正技能和其他技能一樣是「一張技能卡」（稀有度、標籤、敘事、來源、可裝備），之後的掉落、交易、「技能依用法進化」（6.14.1）都以技能為單位；只多一個欄位、一個 `kind`，其他系統（裝備、欄位、API 卡片、驗證器）幾乎不用分支。
- **`change` 恰好一種（正交）**：每種改變的預算、套用點、預覽都是獨立的一條路徑；想要「推遠 1 格但 AP +1」就寫兩條規則（重踏）。一個技能上限 2 條。
- **每種 `change` 可套用的對象寫成一張表**（`content.skills.CHANGE_TARGETS`）：推擊／絆倒／互動沒有命中骰與傷害、基本動作沒有冷卻與標籤，所以例如 `cooldown_delta` 套在 `attack` 會在 schema 就被拒。
- **選目標之前就要決定的改變**（`ap_delta`、`range_delta`、`add_element`、`add_tags`）的條件只能是 `self_hp_below`：AP 與射程在列合法動作時就要知道，不能依目標而變（否則 `legal_actions` 與實際花費會不一致）。
- **數值一律整數**：傷害‰ 加總後乘進既有的 `multiplier_permille` 一次（`1000 ＋ Σ`，下限 0，整數除法）；命中加值是整數；距離截斷在 `max_displace_distance`。
- **確定性**：所有查詢都依「技能 ID 排序 → 規則索引」走過持有者的規則（`modifiers.unit_rules`），與裝備順序無關；元素取第一條成立的規則。引擎內只讀 `BattleState`，不需要新的狀態欄位（修正技能是靜態的）。
- **一次動作以 `modifiers.Use` 表示**（基本動作或技能）：套用點只需要問「這次是哪個動作」，新增套用點（例如 3C-3 的觸發時機）不用改資料格式。
- **命中後效果走被動觸發的同一條管線**（`skill_triggers`）：自然受 `max_trigger_depth` 限制、與被動觸發同樣延後到攻擊結算後、同樣的排序；事件沿用 `SkillTriggered`（`trigger: "modifier_on_hit"`，沒有代價）。
- **向下相容**：所有新欄位都有預設值（`SkillDef.modifiers=()`、`AttackRolled.modifier_bonus=0`、`CoreRules.max_displace_distance=2`），沒有修正技能時引擎行為與事件逐字不變（CLI 快照中沒有修正技能的 5 場戰鬥雜湊未變）。

### 2.1 套用點

| change | 普攻 | 推擊／絆倒／互動 | 技能（主動、姿態、反應技） | 預覽 |
|---|---|---|---|---|
| `ap_delta` | `battle.action_ap_cost` | 同左 | `targeting.skill_ap_cost(state, skill, caster)` | `Preview.ap_cost` |
| `range_delta` | `combat.attack_reach`（近戰性質仍看武器） | — | `targeting.shape_reach(state, …)`（只改有 `range` 的形狀；近戰性質看未修正射程） | `Preview.reach` |
| `hit_bonus` | `roll_attack(bonus=)`，事件 `modifier_bonus` | — | 同左 | 命中率加入同一個加值 |
| `damage_permille` | 傷害效果的 `multiplier_permille`（含攻擊物件） | — | 同左（含物件） | 由模擬事件的倍率計算期望值 |
| `add_element` | 物理普攻改元素（攻擊物件也算） | — | `damage_parameters(modified=True)` | 同一函式 |
| `push_distance_delta` | — | 推擊距離（`battle.shove_distance`，合法性檢查也用它） | `push`／`pull` 效果 | 模擬 |
| `cooldown_delta` | — | — | 命中判定當下決定、全部效果結算後縮短，發 `SkillCooldownChanged` | — |
| `add_tags` | — | — | `modifiers.effective_tags`：其他規則的 `skill_tags` 以實際標籤比對（3C-3 `on_cast_tag` 可直接用） | — |
| `on_hit_effects` | 命中後觸發（深度 +1） | — | 同左 | 模擬（min／max） |

被動觸發、陷阱觸發與命中後效果本身 **不受** 修正（`_TriggeredCast.modified = False`），避免遞迴與重複計算預算。

### 2.2 預算（初值，未經模擬）

`規則點數 ＝ 每場預估使用次數 ×（命中後才生效的再 × 命中率 0.6）× 每次的價值 × 條件倍率`，`可用預算 ＝ tier_budget × 0.3`（`skill_budget.yaml` 的 `modifier`）。使用次數：普攻 6、推擊 2、絆倒 2、互動 1、所有攻擊 10、所有技能 6、每個標籤 3（上限 12）。每次價值：傷害 ＝ 基準武器傷害 7 × ‰、推擊距離 ＝ `push` 原語 2 點／格、命中 +1 ＝ 0.35、冷卻 −1 ＝ 1.2、AP −1 ＝ 3.0、AP +1 ＝ −0.5（代價）、射程 ±1 ＝ 0.5、元素 ＝ 1.0、標籤 ＝ 0.2／個、命中後效果 ＝ 效果本身的點數。`trpg skills budget <id>` 每條規則一列。

## 3. 示範技能（全部史詩、T1，數值為初值）

| 技能 | 規則 | 預算比例 | 裝備 |
|---|---|---|---|
| 灼傷之痕 `skill_searing_scar`（修正型被動） | `all_attacks`；目標燃燒中時傷害 +100‰ | 85.0% | build_fire |
| 雷之手 `skill_thunder_hand` | `actions: [attack]`；`add_element: lightning` | 85.7% | build_tank |
| 重踏 `skill_heavy_stomp` | `actions: [shove]`＋`skill_tags: [push]`：`push_distance_delta: 1`；同對象 `ap_delta: 1` | 83.3% | build_push |
| 餘燼循環 `skill_ember_cycle` | `all_skills`；目標燃燒中且命中時 `cooldown_delta: -1` | 87.4% | build_fire |

## 4. 驗收條件逐條

1. **schema 測試**：通過。`tests/content/test_modifier_schema.py::test_every_change_kind_has_a_valid_example`（9 種 change 各一個合法例子）、`test_invalid_modifier_skills_are_rejected`（26 個參數化不合法例子：空 `applies_to`、重複動作、標籤格式、兩種 change、沒有 change、數值 0／超出範圍、物理元素、空標籤、change 與對象不相容 ×4、選目標前的改變用目標條件、命中後效果的原語不允許／超過 2 個／法術傷害缺元素、0 條與 3 條規則、`effects` 非空、形狀非 self、有代價、技能層級條件、`ap_cost`、`trigger`）、`test_only_modifier_skills_may_have_modifiers`、`test_self_hp_condition_is_allowed_on_pre_target_changes`、`test_cross_file_checks_cover_rule_conditions_and_on_hit_effects`。
2. **每種 change 至少一個引擎測試**：通過（`tests/engine/test_modifiers.py`）。
   - `damage_permille`：`test_searing_scar_adds_ten_percent_damage_only_against_burning_targets`（倍率 1000 → 1100，只對燃燒中的目標）、`test_searing_scar_also_modifies_attack_skills`、`test_modifiers_do_not_change_triggered_passive_effects`。
   - `hit_bonus`：`test_hit_bonus_is_added_to_the_attack_total_and_recorded`。
   - `cooldown_delta`：`test_ember_cycle_shortens_the_cooldown_after_hitting_a_burning_target`（燃燒 3 → 2、未燃燒維持 3）、`test_ember_cycle_needs_a_hit`。
   - `push_distance_delta`：`test_heavy_stomp_shoves_two_tiles_for_two_ap`、**上限處理** `test_heavy_stomp_push_distance_is_capped_at_two_tiles`（颶風踢本來 2 格，仍是 2 格）。
   - `ap_delta`：`test_heavy_stomp_shoves_two_tiles_for_two_ap`、`test_ap_delta_makes_an_action_illegal_without_enough_ap`、`test_ap_delta_never_goes_below_one`。
   - `range_delta`：`test_range_delta_extends_basic_attack_and_skill_range`。
   - `add_element`：**普攻獲得雷元素後在水上導電** `test_thunder_hand_basic_attack_becomes_lightning_and_conducts_through_water`、`test_add_element_does_not_override_an_existing_element`。
   - `add_tags`：`test_add_tags_lets_another_modifier_match_the_skill`（加上 fire 標籤後，另一條「fire 技能傷害 +20%」規則套到颶風踢：400‰ → 480‰）。
   - `on_hit_effects`：`test_on_hit_effects_apply_after_a_hit_as_a_depth_one_trigger`、`test_on_hit_effects_do_nothing_on_a_miss`、**深度限制** `test_on_hit_effects_respect_max_trigger_depth`（`max_trigger_depth: 0` → `TriggerLimitReached`）。
3. **預覽與實際結算一致**：通過。`test_preview_matches_resolution_for_modified_attacks`（命中率＝以實際擲骰的加值窮舉、最少後果的傷害倍率＝實際 1100‰、實際傷害落在預覽範圍、`ap_cost`＝實際扣的 AP、`reach`）、`test_preview_matches_resolution_for_modified_skills_and_maneuvers`（技能 AP 2 與射程 2、推擊落點、推擊 AP）、`test_preview_hit_chance_includes_the_skill_hit_bonus`。API：`tests/api/test_routes.py::test_preview_returns_the_numbers_and_does_not_change_the_session`（回應含 `ap_cost`、`reach`）；前端 `previewText.test.ts` 的「shows the (modified) AP cost and reach」。
4. **被動欄位 3**：通過。`test_three_passive_slot_skills_are_allowed_and_four_are_rejected`（嗜血＋致命破綻＋灼傷之痕可以；再加餘燼循環 →「被動（含修正）技能超過欄位上限：4 個（上限 3）」）。
5. **確定性**：通過。`test_stacking_order_is_by_skill_id_then_rule_index_regardless_of_equip_order`（兩種裝備順序結果相同：元素取 ID 較小者、‰ 加總 1350）、`test_battles_with_modifiers_are_deterministic_and_replay`（同種子兩次 `run_battle` 事件逐筆相同、含雷電普攻；`--log-json` 同格式 → `cmd_replay`「重播驗證通過」）。
6. **`check.py` 全過；示範技能有 build 裝備、`test_coverage.py` 通過**：`uv run python scripts/check.py` → ruff、format、mypy、lint-imports、pytest（1704 passed）、client install／typecheck／test（74 passed）全部通過。`tests/content/test_coverage.py` 通過（新骨架 `modifier` 被示範技能使用、允許清單維持為空、所有手寫技能都有 build 裝備）；`tests/content/test_sim_builds.py` 驗證 build 內每個技能 `validate_skill == []` 且預算合格。

## 5. 修改既有測試的原因

- `tests/content/test_skill_rules_content.py`：骨架數 12 → 13、啟用清單加 `modifier`（新骨架）；測試改名 `test_all_thirteen_skeletons_have_a_data_file`。
- `tests/skillgen/test_validate.py::test_each_enabled_skeleton_has_a_valid_example`：補 `modifier` 骨架的例子（灼傷之痕）。
- `tests/cli/test_budget_cli.py`：技能數 62 → 66（兩處，新增 4 個示範技能）。
- `tests/api/test_routes.py`：預覽回應多了 `ap_cost`、`reach` 兩個鍵，並檢查 `ap_cost ≥ 1`。
- **CLI 快照重錄**（`tests/cli/snapshots/cli_output_hashes.json`）：`skills_list`、`skills_show_all`（新增 4 個技能）、`battle_oil_depot_fire_7`（build_fire 裝上灼傷之痕與餘燼循環，戰鬥內容改變）。其餘 5 場戰鬥（含 build_push 的 frozen_lake 種子 3：這場主角沒有推擊、也沒用帶 push 標籤的技能）雜湊不變。

## 6. 複雜度 noqa

新增：**無**（沒有 C901／PLR0911／PLR0912／PLR0915）。開發中 `skill_triggers._on_attack` 與 `_resolve_one` 一度超標，改為把命中後效果的收集移到 `observe`、結算分派移到 `settle` 解決；描述函式改用格式表。其他新增的非複雜度 noqa：`content/skills.py` 的 `PLR2004`（規格的「1～3 個標籤」常數）、`skill_triggers._resolve_on_hit` 的 `PLC0415`（延後匯入解譯器，與既有 `_resolve_one` 相同理由：避免循環匯入）。

## 7. `LOG_FORMAT`

**未升**（維持 `trpg-battle-log/11`）。新增的欄位都有預設值：`SkillDef.modifiers`、`SkillDef.kind` 的新值、`CoreRules.max_displace_distance`、`SkillSlots`（數值改在 `core.yaml`，紀錄內嵌的是當時的規則包）、`AttackRolled.modifier_bonus`；`/11` 的舊紀錄內嵌舊規則包，沒有修正技能，重播結果逐字不變。含修正技能的新紀錄無法由舊程式讀取（與 3C-1 相同的處理）。

## 8. 待 PM 決定

1. **修正的對象是「持有者的動作」**：普攻（含藉機攻擊）、推擊、絆倒、互動、主動／姿態／反應技。被動觸發、陷阱觸發、命中後效果本身不受修正（避免遞迴與預算重複）。若希望「灼傷之痕」也加成被動觸發的傷害，需要另訂。
2. **新增 `applies_to.all_skills`**：規格只列 `actions`、`skill_tags`、`all_attacks`，但示範「餘燼循環：所有技能」需要它。`all_attacks` 定義為「普攻 ＋ 有對敵方傷害效果的技能」。
3. **`push_distance_delta` 超過 2 格直接截斷**（最保守）；上限放在 `core.yaml` 的 `max_displace_distance: 2`。已看到 3C-3a 規格會改成撞擊傷害，屆時只需改 `modifiers.displace_distance` 一處。
4. **`add_element` 只改物理傷害**；法術技的傷害一定有元素，所以實際上只影響普攻與武器技（武器為物理時）。多條規則時取技能 ID 最小的那條。
5. **`add_tags` 只做一層**：`add_tags` 規則以技能原本的標籤比對；其他規則以「原本 ＋ 加上的」標籤比對。另：現有技能沒有 `displace` 標籤（推擊技能的標籤是 `push`），所以重踏用 `skill_tags: [push]`。
6. **條件判斷的時機**：傷害看結算到該傷害當下的目標、命中看擲骰前、冷卻看命中判定當下（效果結算前，所以「這一擊才點燃」不算）、命中後效果看觸發結算時（同被動）。選目標前的改變只接受 `self_hp_below`。
7. **命中後效果**沒有代價、沒有每輪次數上限、自動命中、目標已倒下時不結算；原語限 `damage`、`apply_status`、`push`、`pull`、`knock_prone`、`create_surface`。預算以使用次數控制；若擔心多段攻擊疊太多，可加 `max_per_round`。
8. **預算初值**（第 2.2 節）：係數 0.3、命中率 0.6、各對象使用次數、AP +1 只算 −0.5／次（不對稱，否則「重踏」會變成負分）。示範技能都落在 83–87%；需要 3C-6 的 `sim matrix` 校正。
9. **雷之手在水裡會電到自己與隊友**：沿用既有導電規則，`trpg battle --map swamp --seed 5 --ally-build build_tank` 中坦克英雄普攻站在水裡的頭目，自己與隊友各受 12 點傳導傷害（傳導以格擋前的傷害為基準，比直接傷害 6 點還高）。這是「拿到這招後站位要改變」的好例子，但數值可能偏痛，屬玩法問題。
10. **顯示**：冷卻被縮短時戰鬥紀錄沒有文字（`SkillCooldownChanged` 在剩餘 > 0 時本來就不出文字）；前端只在技能卡片列出修正規則、在預覽最後一行顯示 AP 與射程，完整 UI 在 3C-6。新骨架 `modifier` 是第 13 個骨架，隨機組合器不會產生修正技能。

## 9. 代表性輸出

```
$ uv run trpg skills show skill_searing_scar
灼傷之痕（skill_searing_scar）
  階級 T1（等第 1）  稀有度 史詩  種類 修正  骨架 modifier
  分類 法術技  武器需求 任何武器  縮放屬性 智力
  代價 無（裝在被動欄位、不花 AP）
  形狀 自身
  修正規則（裝在被動欄位，持續生效）：
    1. 你的所有攻擊（普攻與攻擊技能）：傷害 +10%，若目標帶有狀態「燃燒」

$ uv run trpg skills budget skill_heavy_stomp
重踏（skill_heavy_stomp）  階級 T1  稀有度 史詩  骨架 modifier  修正（被動欄位，不花 AP）
  規則點數 ＝ 使用次數（× 命中率）× 每次價值 × 規則條件：
    1. modifier.push_distance_delta 推擊＋標籤 push 5 次 × 推擊 +1 格 … ＝ 6.00（基礎 6.00）
    2. modifier.ap_delta 推擊＋標籤 push 5 次 × AP +1 … ＝ -2.50（基礎 -2.50）
  total ＝ raw × 條件 × 協同 ＝ 3.50
  可用預算 ＝ tier_budget 14 × 修正係數 0.30 × (1000 + 折抵 0‰) ÷ 1000 ＝ 4.20
  比例 ＝ total ÷ 可用預算 ＝ 83.3%（合格區間 70.0%–100.0%）→ 合格

$ uv run trpg battle --map swamp --seed 5 --ally-build build_tank   （雷之手）
  坦克英雄 攻擊 盜賊頭目：d20=14 修正 +1 熟練 +2 = 17（目標 11）→ 命中
    盜賊頭目 受到 6 點雷電傷害［骰 6］（天氣 ×1.2）（格擋/加成 ×0.5），HP 80 → 74
    坦克英雄 受到 12 點傳導雷電傷害，HP 46 → 34
    盜賊盾衛 受到 12 點傳導雷電傷害，HP 32 → 20
```
