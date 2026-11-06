# Phase 3T-3 完成報告：`content/skills.py` 拆成 `content/skills/` 套件

純搬移，行為不變。以 AST 腳本依頂層定義搬移（保留註解、屬性 docstring、`@cache`、`# noqa`），各模組的 import 依實際用到的名稱自動產生。

## 模組對照表（依相依順序，後者只匯入前者，無循環）

| 新模組 | 行數 | 內容（原 `skills.py` 行號約略） |
|---|---|---|
| `constants.py` | 812 | 所有純資料常數與型別別名（原 209–328、1514–1777 常數、1892–1900、1947–2024、2286–2298 等）、`rarity_rank`、`_unique` |
| `shapes.py` | 281 | `ParamDef`、`ShapeBudget`、`ShapeCells`、`ShapeDef`、`ShapeConversion`、`ShapeTable`（329–573） |
| `primitives.py` | 324 | `RequiredWhen`、`PrimitiveKnob`／`Param`／`Def`／`Table`、`default_affects`（575–900） |
| `conditions.py` | 116 | `ConditionDef`／`Table`／`Spec`、`condition_text` 與相關私有函式（902–1038） |
| `effects.py` | 388 | `ShapeSpec`、`ScaleSpec`、`EffectSpec`、YAML 參數表、組合規則、`_check_composition`、`EFFECT_PARAM_FIELDS`（1040–1430） |
| `specs.py` | 151 | `SelfStatusCost`、`SkillCost`、`FollowupSpec`、`NarrativeDef`、`Provenance`、`TriggerSpec`（1432–1566） |
| `followup.py` | 135 | `_check_after_*`／`_check_on_*`／`_check_delayed` 與 `_FOLLOWUP_CHECKS`（1778–1890） |
| `reactions.py` | 47 | `ReactionSpec`、`TrapSpec`（1904–1937） |
| `modifiers.py` | 285 | `ModifierTarget`、`ModifierChange`、`ModifierSpec`（2027–2279） |
| `variants.py` | 122 | `VariantWhen`、`VariantEffectSwap`、`walk_effect`、`VariantSpec`（2301–2400） |
| `skill.py` | 1309 | `SkillDef`（單一類別 ~1150 行，無法再依主題拆）、`SkillTable`、`_FOLLOWUP_CACHE`／`_VARIANT_CACHE`（2411–3572） |
| `queries.py` | 114 | `on_hit_carrier`、`skill_elements`、`is_wind_skill`、`weapon_problem`、`held_gear`、`skill_slot_problems`（4142–4249） |
| `problems.py` | 578 | `_Refs` 與各 `_*_problems`、`param_required_for`、`granted_skill_problems`、`skill_problems`、`legendary_cores`、`_modifier_problems`（3580–4139） |
| `__init__.py` | 652 | 原模組 docstring；重新匯出所有名稱（公開名稱列入 `__all__`，私有名稱以 `X as X` 匯出，故測試匯入私有名稱照常可用）；`__all__` 與原本一致 |

## 重點
- 前向參照：因所有 pydantic 模型都在「被引用者之後」定義，不需要 `model_rebuild`，也沒有 `TYPE_CHECKING` 以外的延遲匯入。
- 呼叫端改動：**無**（`src/`、`tests/` 一行都沒改）。`from trpg.content.skills import X`（含私有名稱）全部照常。
- 不改欄位、驗證器、錯誤訊息。`_FOLLOWUP_CACHE`／`_VARIANT_CACHE` 仍在 `skill.py` 內被 `SkillDef` 使用。
- 合併衝突提示：4-L6 若小改了舊 `content/skills.py`，請依上表找到新模組套用（可用原行號對照）。`src/trpg/skillgen/option_nested.py` 註解仍寫「skills.py」，未動。

## 驗收
`ruff check`、`ruff format --check`、`mypy`（772 檔）、`lint-imports`（7 契約全保持）皆過；`tests/content tests/skillgen tests/test_architecture.py` 3585 passed、1 skipped；`tests/engine` 3744、`tests/narrative`＋`tests/api` 575、`tests/llm` 89、`tests/roguelite` 188、`tests/cli`（含 slow）153 全過，快照無變動。

## 待 PM 決定
- `skill.py` 仍 1309 行（`SkillDef` 單一類別）；若要再縮，需把 `SkillDef` 的方法抽成 mixin／模組函式，屬行為相關重構，未在本段做。
- `constants.py` 812 行，若覺得太大可再依主題（形狀／原語／修正）拆。
