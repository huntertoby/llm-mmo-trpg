# Phase 4-L3 報告｜提議模型正式化＋給 LLM 的短說明

> 規格：`docs/phases/Phase4計畫.md` 第 0 節決定 #3、#4 與第 1、3 節。實作者撰寫。

## 1. 交付

| 項目 | 內容 |
|---|---|
| `llm_hint` | 原語 54、形狀 12、條件 15、觸發 14，加上它們的每個參數（共 196 條，一句中文、中性）寫進對應的 `content/skill_*.yaml`；schema 欄位 `llm_hint`（`PrimitiveDef`／`PrimitiveParam`／`ShapeDef`／`ParamDef`／`ConditionDef`／`SkillTriggerDef`）。提議模型的 `description` 與 JSON Schema 說明改用它（原本是 `description_zh`／`player_description`）。 |
| `required_when` | `PrimitiveParam.required_when`（`RequiredWhen`：`category` 或 `unless_filled` 恰好一種，須搭配 `required: true`）。YAML：`damage.dice: {category: spell}`、`inscribe.element: {unless_filled: tag}`。驗證器的 `_filled_by_category` 與提議的 `CONDITIONALLY_REQUIRED` 都刪除，兩邊共用 `param_required_for`。 |
| 觸發 `params` | `skill_triggers.yaml` 的 `every_n_hits.n`（int 2–3，必填）、`on_cast_tag.tag`（必填）、`on_status_applied.status`、`on_enter_surface.surface`；提議的觸發模型由此產生。`TriggerSpec` 的驗證器維持原樣，由表格測試保證與 YAML 一致。 |
| 去數值 | 提議模型不含數值欄位；新模組 `skillgen/proposal_numbers.py` 集中定義與拆補。 |

## 2. `proposal.py` 公開 API 變更

- `to_skill_def(proposal, ctx)` → `to_skill_def(proposal, ctx, fill)`：`fill: NumberFiller` 必填（`(dict) -> dict`，補上數值）。ID 現在由補完數值後的內容雜湊（同結構不同數值得到不同 ID）。
- `evaluate_proposal(raw, models, library, ctx)` → 多一個 keyword `fill: NumberFiller | None = None`；省略時用保守的 `minimal_filler(library)`（只補驗證必填的數值：int 取 YAML 最小值、骰子 `1d4`、主動技能 AP 2、`scaling` 步進 10／上限 100、必填條件門檻取最小值）。**不保證通過預算**；4-L5 傳入預算器。
- `proposal_from_skill(skill)` → `proposal_from_skill(skill, library)`，輸出已去數值；要連同數值用 `proposal_numbers.split_numbers`。
- 刪除 `CONDITIONALLY_REQUIRED`、`DICE_PATTERN`。新增匯出 `NumberFiller`。
- `proposal_numbers.py`：`split_numbers`／`apply_numbers`（互為反運算，測試涵蓋全部內建技能）、`fixed_filler`（把某份數值放回去，測試用的固定預算器）、`minimal_filler`、`numeric_param_names`。
- 結構往返覆蓋率不變：163／217（其餘為原型刻意不開放的部分）。

## 3. 移除的數值欄位（共 53 個）

- 效果參數 43 個（30 個原語，凡 YAML 型別為 `int` 或 `dice`）：`damage`（dice、multiplier_permille、lifesteal_permille）、`heal`／`shield`／`charge_through`／`detonate_runes`（dice）、`push`／`pull`（distance、collision_dice）、`apply_status`／`create_surface`／`create_obstacle`／`cheat_death`／`reveal`／`grant_skill`／`inscribe`（duration）、`raise_terrain`／`lower_terrain`／`add_stack`／`grant_ap`／`extra_reaction`／`restore_resource`（amount）、`consume_stack`（per_stack_permille）、`consume_status`（splash）、`redirect_damage`（permille、duration）、`hurl_object`（dice、range）、`revive`（hp_permille）、`delayed_damage`（dice、radius、rounds）、`summon`（count、duration、max_hp_permille、power_permille）、`zone`（duration、speed）、`gamble`（chance_permille）、`sacrifice_summon`（dice、radius）。
- 條件參數 2 個：`target_hp_below.permille`、`self_hp_below.permille`。
- `scaling` 的 `per_step_permille`、`cap_permille`（只留 `by`）。
- 技能層級：`ap_cost`、`cost`（整個欄位；`mana`、`cooldown`）。
- 觸發：`max_per_round`、`max_distance`。變奏：`range_delta`。

保留為列舉選擇：形狀參數（`range`、`size`、`radius`、`jumps`、`jump_range` 的範圍整數）、`every_n_hits.n`（2／3）、`dispel.count`（1／all）、`affects`、`target`。

### 預算器（4-L5）需要補的項目

1. 所有必填的數值：`dice`（heal、shield、charge_through、hurl_object、delayed_damage、detonate_runes、sacrifice_summon、法術 damage）、`push`／`pull.distance`、`add_stack.amount`、`consume_stack.per_stack_permille`、`grant_ap.amount`、`restore_resource.amount`、`redirect_damage.permille`、`revive.hp_permille`、`delayed_damage.rounds／radius`、`sacrifice_summon.radius`、`summon.duration`、`zone.duration`、`gamble.chance_permille`、`grant_skill.duration`、`hurl_object.range`、`reveal.duration`、`extra_reaction.amount`、必填條件的 `permille`。
2. **現有 `composer_tuning.tune` 的旋鈕沒有涵蓋、但提議不再給的欄位**：技能層級 `ap_cost`、`cost.mana`、`cost.cooldown`（必填但預算器不調：主動技能 `ap_cost` 必填；預設補 2，法力 0、無冷卻）、觸發的 `max_per_round`（預設 1）、`max_distance`（預設不限）、選填數值（`multiplier_permille`、各 `duration`、`lifesteal_permille` 等省略時引擎用預設，預算器只在需要時才調）。

## 4. `llm_hint` 範例

- 原語 `damage`：「對目標造成傷害；法術用骰子加屬性加成，武器用武器傷害乘上倍率。」
- 參數 `apply_status.status`：「要施加的狀態。」
- 形狀 `cone`：「朝一個方向打出一片向外展開的扇形。」（參數 `size`：「扇形向外延伸的深度。」）
- 條件 `from_behind`：「施放者站在目標背後時才成立。」
- 觸發 `on_cast_tag`：「持有者施放帶指定標籤的技能後自動發動。」（參數 `tag`：「技能必須帶有的標籤。」）

測試 `tests/content/test_llm_hint.py`：全覆蓋；每條恰好一句、以句號結尾、≤ 60 字、不含 snake_case 欄位名、階段編號與世界觀名詞。

## 5. 測試與檢查

`tests/content`、`tests/skillgen`、`tests/test_architecture.py`、`tests/api/test_openapi_snapshot.py`（1673 項）、`ruff check`、`ruff format --check`、`mypy` 全過。新增：`tests/content/test_llm_hint.py`、`tests/content/test_required_when_and_trigger_params.py`；改寫 `tests/skillgen/test_proposal.py`（提議不含數值、模型逐原語對照 YAML、觸發模型對照 YAML、結構往返）。未跑完整 `scripts/check.py`。`content/` 的改動沒有影響 `client/openapi.json` 與前端快照，不需重產。

## 6. 待 PM 決定

1. **形狀參數保留**（`range`、`size`、`radius`、`jumps`、`jump_range`）：視為幾何結構、以列舉整數讓 LLM 選；預算器目前不調它們。若希望也交給預算器，需要新增預算器旋鈕。
2. **`ap_cost`、`mana`、`cooldown`、`max_per_round` 全部移除**並採預設（AP 2、法力 0、無冷卻、每輪 1 次）：LLM 因此無法表達「便宜／慢熱」的取捨；若要保留這些取捨，建議 4-L5 的預算器加入 AP／冷卻旋鈕（預算有代價折抵）。
3. **`variants.range_delta` 一併移除**（無上下限的整數）；變奏仍可替換形狀與加／換效果。
4. **預設補值器不保證通過預算**，只保證 schema 合法；`minimal_filler` 的條件門檻取 YAML 最小值（例如血量低於 1‰）會讓條件幾乎不成立，僅作為保守的占位。
5. **`unless_filled` 保留原行為**：同技能內「任一」同類型效果填了該參數即可，沒有改成逐效果判斷。
6. 觸發的 `TriggerSpec` 驗證器仍寫死各參數的規則（只與 YAML 用表格測試對齊）；若要完全由 YAML 驅動需改動 `trpg.content.skills`，超出本段範圍。
