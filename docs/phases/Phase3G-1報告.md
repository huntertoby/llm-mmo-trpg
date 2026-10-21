# Phase 3G-1 報告：裝備欄位、詞條 schema、遞減與上限（G1）

規格：`docs/phases/Phase3G計畫.md` 第 0、1 節；設計：`docs/design/08-裝備.md` 8.21、8.21.5.2～8.21.5.3、8.23、8.24。
分支 `worktree-agent-a262b08facd80f7a0`（從 main 的 2644292 分出），未 push、未合併。

## 新增與修改的檔案

| 檔案 | 內容 |
|---|---|
| `src/trpg/content/slots.py` | 9 個欄位 `Slot`、8 種物品種類 `SlotType`、欄位固定順序 `SLOTS`、欄位 → 種類、中文名（獨立小模組，避免 `battle.py` ↔ `equipment.py` 循環匯入） |
| `src/trpg/content/equipment.py` | 11 類詞條的依類別區分聯合型別 `AffixDef`（`category` 為 discriminator）、`AffixTable`、`ItemDef`／`ItemTable`、`EquipmentRules`／`EquipmentCaps`、裝備快照 `Loadout`／`EquippedItem`／`EquippedAffix`、`item_problems`、`resolve_loadout`、`loadout_problems` |
| `content/affixes.yaml` | 8.24 的 31 條詞條（11 類，每類 2～3 條） |
| `content/items.yaml` | 13 件測試用物品（每種物品種類至少一件、戒指 3 枚；每件 1～3 條，只用第 1、2、8 類） |
| `content/rules/equipment.yaml` | 遞減權重 `[1000, 500, 250]`、每件詞條上限 4、全部硬上限 |
| `content/units/gear_tester.yaml` | 9 欄都穿上測試物品的戰士（`--log-json` ＋ `replay` 驗收用） |
| `src/trpg/content/battle.py` | `UnitTemplate.equipment: dict[Slot, str]`（選填，預設空） |
| `src/trpg/content/library.py` | 載入三個新檔、`Ruleset.equipment`（預設值，嵌入規則包）、`ContentLibrary.affixes／items／loadout_of()`、詞條引用檢查、單位與 build 的裝備檢查、總減傷上限與 `element_mod_floor_permille` 一致性檢查 |
| `src/trpg/engine/gear_state.py` | 單位的裝備狀態 `GearState`（`GearItem`、`GearAffix`、`GearBonus`） |
| `src/trpg/engine/gear.py` | 遞減、`build_gear`、`geared_template`、戰鬥中查詢、全部硬上限函式 |
| `src/trpg/engine/state.py` | `UnitState.gear`、`SpawnTemplate.equipment`（`clone` 一併複製） |
| `src/trpg/engine/setup.py` | `UnitSpawn.equipment: Loadout`；`build_setup` 由範本解析快照（含援軍範本） |
| `src/trpg/engine/lifecycle.py` | `make_unit(..., equipment=)`：建 `GearState`、數值類併進範本 |
| `src/trpg/engine/battle.py`、`effects/world.py`、`roguelite/progress.py` | 開戰／援軍／一輪的主角傳入裝備；`_check_loadouts` 加穿戴合法性 |
| `src/trpg/engine/modifiers.py`、`rules/combat.py`、`rules/statuses.py`、`skills/targeting.py`、`turns.py` | 各一行接上裝備查詢（見「G2／G3 接點」） |
| `src/trpg/engine/events.py`、`narrative/events.py` | 新事件 `gear_hp_lost` 與敘事文字 |
| `src/trpg/engine/view.py` | `UnitView.equipment`（唯讀摘要：`EquipmentSlotView`、`AffixLineView`） |
| `src/trpg/engine/runner.py` | `LOG_FORMAT` → `trpg-battle-log/39` |
| `client/openapi.json`、`client/src/api/schema.d.ts` | 重產（只新增欄位與型別） |
| `client/src/battle/testFixtures.ts` | 測試用 `UnitView` 補上 `equipment: []`（必填的回應欄位） |
| `tests/content/test_equipment_content.py`、`tests/engine/test_gear.py` | 新測試（53 ＋ 33 個） |
| `tests/content/test_con_hp.py`、`tests/cli/*`（4 檔） | 新單位的 HP 表、紀錄格式 `/39` |

## 設計重點

- **詞條 schema**：共用欄位（`id`、`name_zh`（`{n}` 為數值）、`slots`、`weapons`、`weapon_class`、`item_tags`（依物品種類限定，例如 `{offhand: [shield]}`＝「副（限盾）、身」）、`legendary_only`、`value {min,max}`、`value_unit`）＋各類別欄位：
  - 1 `stat`：`stat`（`attribute`／`max_hp`／`element_resist`／`defense`／`move`）＋`attribute`／`element`
  - 2 `conditional`：`effect`（`hit`／`damage`／`defense`）＋`condition`（沿用 `ConditionSpec` 與既有條件 id）＋`negate`
  - 3 `keyword`：`keyword`、`direction`（create／exploit）、`include_attack`、`change`（`status_duration`／`damage_permille`／`area_delta`）、`status`、`amount`
  - 4 `attack`：`add_element` 或 `on_hit_status`＋`status_duration`
  - 5 `weapon_trait`：`param`（武器資料參數路徑，例如 `armor_break.rounds`）＋`delta` 或 `scale_permille`
  - 6 `trigger`：`trigger`（`skill_triggers.yaml`）、`n`、`melee_only`、`effect_target`、`effects`（沿用 `EffectSpec`）、`limit`（per_turn／per_round）
  - 7 `charge`：`stack`、`max_stacks`、`gain_trigger`、`cost_stacks`、`cost_ap`、`effects`
  - 8 `cost`：`upside`／`downside`（`CostPart`：`damage_permille`、`damage_taken_permille`、`move`、`defense_permille`、`cooldown_delta`、`turn_start_hp_loss`、`hit`；schema 檢查 upside 全有利、downside 全不利）
  - 9 `action`：`skill`（授予的常駐技能 id）
  - 10 `reaction`：`mode`（`extend_trigger`／`grant`／`extra_uses`）、`reaction`、`event`、`range`、`uses`、`limit`
  - 11 `rule`：`rule`（`rule_changes.yaml`），必須 `legendary_only`
- **裝備快照**：`UnitSpawn.equipment`（`Loadout`）內嵌物品與詞條的完整定義，戰鬥紀錄的 `setup` 自帶，重播不讀資料檔。主手沒有物品時 `UnitSpawn.weapon` 就是主手（舊資料不必改）；主手有物品時，物品的 `weapon` 必須等於單位的 `weapon`（單一真相來源仍是 `weapon`）。
- **計算位置**：開戰時 `build_gear` 一次算好遞減（存在 `UnitState.gear`，戰鬥中不變）；數值類（屬性、基礎最大 HP、個別元素抗性、速度）由 `geared_template` 併進範本，最大 HP 之後照常加體質（裝備的體質也算）；條件數值與代價型的其他數值存成 `GearBonus`，戰鬥中查詢時判斷條件並套上限。**先遞減、再套上限**。
- **遞減**：同 id 依數值大到小、同值依欄位固定順序排序；權重 1000／500／250／0‰；同一個數值部分 **加總後才捨去**（往 0 的方向），例如 5、5、5 → 8.75 → 8。非數值類同 id 只有第一條權重 1000、其餘 0。代價型的數值是固定的，兩面都乘同一組權重。
- 所有數值都是整數或千分比（`value_unit: permille` 時 150 ＝ 15%）。

## LOG_FORMAT

`trpg-battle-log/38` → **`trpg-battle-log/39`**：`UnitSpawn.equipment`、`SpawnTemplate.equipment`、`UnitTemplate.equipment`、`UnitState.gear`、`Ruleset.equipment`、新事件 `gear_hp_lost`。`/38` 的紀錄不相容（規格已接受）。合併時若 3-24a2／3-24b1 也遞增，由 PM 處理版號。

## 逐條驗收

| 規格（第 1 節） | 證據 |
|---|---|
| 1 欄位與 `slot_type` 驗證 | `test_equipment_content.py`：`test_slot_list_and_types`、`test_slot_type_must_match`、`test_full_loadout_is_legal`（9 欄全穿） |
| 1 雙手與成對武器占用副手 | `test_two_handed_weapon_occupies_off_hand`（含沒有主手物品、只有舊 `weapon` 的情形）、`test_paired_weapon_occupies_off_hand` |
| 1 副手不能放第二把武器 | `test_off_hand_cannot_hold_a_second_weapon` |
| 1 同一枚戒指不能裝兩次 | `test_same_ring_cannot_be_worn_twice` |
| 2 白名單 31 條全部通過 schema | `test_whitelist_has_all_31_affixes_in_11_categories`、`test_every_whitelist_affix_round_trips_through_schema`（31 個參數化）、`test_categories_are_discriminated`、`test_defense_conditions_must_be_self_evaluable`、`test_cost_affix_sides_must_point_the_right_way`、`test_rule_affix_must_be_legendary_only`、`test_duplicate_affix_ids_rejected` |
| 2 測試用物品（每欄至少一件、1～3 條） | `test_test_items_cover_every_slot_with_1_to_3_affixes`；物品合法性 `test_item_problems_detect_slot_value_and_unknown_affix`（不可出現的欄位、超出範圍、缺 value、限錘、限盾、身體不限盾、傳說、法杖已有元素、超過 4 條）、`test_item_cannot_repeat_an_affix`、`test_weapon_items_need_a_weapon` |
| 3 穿到單位上、`BattleSetup` 快照、`weapon` 視為主手 | `test_main_hand_item_must_match_unit_weapon`、`test_units_without_equipment_have_empty_gear`、`test_setup_rejects_illegal_loadout`（`BattleSetupError`）、`test_gear_state_round_trips_through_json` |
| 4 第 1 類 數值 | `test_gear.py`：`test_stat_affixes_merge_into_unit_totals`（力量、最大 HP、火抗）、`test_constitution_from_gear_also_raises_hp`、`test_strength_from_gear_changes_attack_value`（預覽傷害上限變大）、`test_fire_resist_reduces_fire_damage_modifier` |
| 4 第 2 類 條件數值 | `test_height_hit_only_from_high_ground`（`height_advantage`）、`test_still_defense_only_when_not_moved`（`moved_this_turn` 否、作用在持有者防禦）、`test_low_hp_damage_only_below_half`（`self_hp_below` 500‰，剛好一半不算） |
| 4 第 8 類 代價型 | `test_glass_raises_damage_dealt_and_taken`（+20%／受傷 +10%）、`test_blood_loses_hp_at_turn_start_but_never_kills`（2 HP；剩 2 → 1；剩 1 不扣、不發事件）、`test_blood_reduces_cooldown_with_floor_of_one`（含 `pay_skill_cost`）、`test_swift_adds_move_and_lowers_defense` |
| 5 遞減（兩件 100＋50、三件、四件） | `test_numeric_affixes_diminish`（6 組參數：1 件 16、2 件 24、3 件 28、4 件 28、大到小 8＋16 → 20、加總後捨去 5×3 → 8）、`test_ties_follow_slot_order`、`test_numeric_fourth_copy_is_inactive`、`test_conditional_affixes_diminish_before_condition` |
| 5 非數值同 id 只算 1 條 | `test_non_numeric_same_id_counts_once`（兩件 `affix_trig_kill_ap` 只有主手那條生效） |
| 6 硬上限 | `test_damage_bonus_capped_at_50_percent_after_diminishing`（525 → 500）、`test_move_bonus_capped_at_two`（3 → 2）、`test_element_resist_capped_at_50_percent`（400＋150 → 500；範本本身 600 維持）、`test_total_damage_reduction_still_floored_at_75_percent`、`test_blood_reduces_cooldown_with_floor_of_one`（冷卻最低 1）、`test_cap_helpers_for_later_segments`（暴擊範圍 18、AP 回復 +1、冷卻）、`test_equipment_rules_from_yaml`、`test_diminishing_weights_must_start_at_1000_and_not_grow` |
| 6 代價型超過 2 條驗證失敗 | `test_more_than_two_cost_affixes_fail`（內容層）、`test_setup_rejects_illegal_loadout`（開戰時） |
| 7 預覽含裝備加成 | `test_preview_includes_gear_hit_and_damage`（`preview()` 的命中率與傷害上限都變大；`/preview` 端點呼叫同一個 `preview`） |
| 7 `UnitView` 裝備摘要 | `test_unit_view_lists_equipment`（9 欄、物品名、詞條文字「力量 +2」「火焰抗性 +10%」；沒有裝備的敵人為空）；`openapi.json`、`schema.d.ts` 已重產（`tests/api/test_openapi_snapshot.py` 通過） |
| 舊 build（只有 `weapon_id`）行為不變 | `test_old_build_with_only_weapon_behaves_the_same`（主手放一件沒有詞條的同把武器，整場事件逐筆相同）；既有 engine／api／roguelite／cli 測試全部通過、**沒有換任何種子** |
| 含裝備的 `--log-json` ＋ `replay` | `test_gear_battle_log_json_and_replay`；手動：見下 |
| `check.py` 全過、`pnpm build` 成功 | 見文末「最終檢查」 |

手動 `--log-json` ＋ `replay`：

```
uv run trpg battle --map test_flat_6x6 --allies gear_tester --enemies bandit,bandit --seed 7 --log-json g.json
uv run trpg battle replay g.json
重播驗證通過：66 個動作、202 個事件，最終狀態一致（test_flat_6x6，種子 7）。
（紀錄內 7 個 gear_hp_lost 事件；試裝戰士最大 HP 84 ＝ 48 ＋ 裝備 24（16＋12×50%＋8×25%）＋ 體質 12）
```

## G2／G3 的接點

| 接點 | 位置 | 說明 |
|---|---|---|
| 生效中的詞條 | `unit.gear.active_affixes(category)`（`GearState`） | G2 取 `keyword`／`attack`／`weapon_trait`，G3 取 `trigger`／`charge`／`action`／`reaction`／`rule`；非數值類已經「同 id 只留 1 條」 |
| 數值部分的遞減 | `gear.diminished_total(entries, amount)` | 同 id 的條目依 `weight_permille` 加總後捨去；技能強化與武器特性強化的數字直接用 |
| 傷害加成上限 +50% | `gear.cap_damage_bonus(rules, total)`；目前在 `gear_damage_permille` 內套用 | G2 的技能強化傷害要 **先加進同一個總和再截斷**：建議在 `gear_damage_permille` 的 `_sum` 加上技能強化的部分（依 `Use` 選取），不要在 `modifiers` 另外加 |
| 命中、傷害 | `modifiers.hit_bonus`／`modifiers.damage_permille` 末端各加一項 `gear_*` | 普攻、技能、預覽共用；被動觸發與陷阱（`interpreter._modifier` 的非 `modified` 施放）不吃裝備加成 |
| 防禦 | `rules/combat.defense_value_permille` ＋ `gear_defense_permille(unit)` | 只看持有者自己的條件 |
| 受到的傷害 | `rules/statuses.damage_taken_permille` × `gear_damage_taken_permille` | 只影響骰值傷害（與易傷同一處） |
| 冷卻 | `skills/targeting.pay_skill_cost` → `gear_cooldown`（下限 `caps.cooldown_min`） | G2 的「冰技能冷卻 −1」等可把 `cooldown_delta` 加進同一處 |
| 回合開始 | `turns._turn_start_hooks` → `gear_turn_start(ctx, unit)` | G3 的 `on_turn_start` 類裝備觸發可接在這裡；事件 `gear_hp_lost` |
| 暴擊範圍 18 | `gear.cap_crit_range` | **尚未接上**（G1 沒有暴擊來源）；G2 加暴擊範圍時套在 `combat.positional_bonus` 的結果上 |
| AP 回復 +1 | `gear.cap_ap_gain(rules, gained_this_round, amount)` | **尚未接上**；G3 的 `affix_trig_kill_ap` 需要「本輪已回復多少」的計數（可沿用 `UnitState.ap_granted_round` 的做法另加欄位） |
| 推擊距離上限 2 | 既有 `modifiers.displace_split`（`max_displace_distance`） | G2 的錘震退 +1 照用 |
| 觸發連鎖 | 既有 `core.max_trigger_depth` | G3；每條每回合 1 次的計數建議以 `affix_id` 為鍵另存（不要混進 `trigger_counts` 的技能 id） |
| 詞條引用檢查 | `library._affix_reference_problems` | 目前不檢查 `charge.stack`（`fury` 由 G3 加）、`action.skill`（G3 加技能）、`weapon_trait.weapons`（長槍由 3-24a2 加）、`reaction` 的 `grant` 模式；加入後請補上檢查 |
| 文字 | `equipment.affix_text`、`UnitView.equipment[*].affixes[*]`（含 `active`、`weight_permille`） | G4 的「來自裝備、遞減與截斷後的實際值」可用 `GearState.merged`／`uncapped`／`bonuses` |

## 新增的複雜度 noqa

**沒有**（新程式碼都在 C901 15 以內，未加任何 `# noqa`）。

## 待 PM 決定

1. **頭、身體、手、腳、項鍊、戒指的基礎數值**：目前沒有防具資料（`armor_bonus` 只在單位範本上），規格說沒有基礎資料的欄位為 0，所以 **身體也是 0**（8.12 的防具類型留待之後的防具資料）。
2. **主手物品必須等於單位的 `weapon`**：保守做法，單一真相來源仍是 `weapon`；G4 換主手武器時要同時改 `weapon` 與 `equipment.main_hand`。
3. **同一枚戒指** 以「同一個物品 id」判斷（目前沒有物品實例 id）；兩枚不同物品掛同 id 詞條照常遞減。
4. **全身傷害加成上限 +50%** 目前只算裝備來源（條件數值、代價型），**不含技能的修正型被動**（避免改變既有平衡）；G2 的技能強化詞條會算進去。是否要連技能修正一起算，請決定。
5. **單一元素抗性 50%** 解讀為「個別元素抗性（`element_mods`）」；分組抗性（`resist`）不在此上限內（總減傷仍由既有的 75% 下限守住）。範本本身已超過 50% 的不會因穿裝備而下降。
6. **遞減的捨去**：同一數值部分 **先加總再捨去**（往 0 的方向），不是每條各自捨去；負值也往 0 捨去。
7. **代價型的遞減**：兩面都乘同一組權重（第二件「血契」：失去 1 HP、冷卻 −0）。
8. **裝備加成不作用在被動觸發與陷阱的效果**（沿用修正規則「只修正你的動作」的範圍）；條件數值的防禦只能用只看持有者自己的條件（`moved_this_turn`、`self_hp_below`、`self_concealed`）。
9. **回合開始失去 HP** 用新事件 `gear_hp_lost`（不是傷害：不吃抗性、護盾、易傷，也不觸發受傷類觸發），時機在狀態與表面的回合開始效果之後、持續區域之前。
10. **白名單 id 的暫定值**：技能強化的 `keyword`（`ignite`、`prone`、`shock`）要以 3-24b1 的關鍵字推導為準；長槍的武器 id 暫定 `longgun`、參數 `point_blank`，要以 3-24a2 為準；授予動作的技能 id（`skill_gear_*`）與充能 `fury` 由 G3 建立。

## 最終檢查

`uv run python scripts/check.py`（最後跑一次）：

```
pytest: 3581 passed in 223.73s
client test: Test Files 51 passed (51), Tests 555 passed (555)
=== 檢查結果摘要 ===
  ruff check             通過
  ruff format --check    通過
  mypy                   通過
  lint-imports           通過
  pytest                 通過
  client install         通過
  client typecheck       通過
  client test            通過
全部檢查通過。
```

`corepack pnpm -C client build`：成功（只有既有的 chunk 大於 500 kB 警告）。

沒有跑大型模擬（規格沒有要求，數值都是初值）。
