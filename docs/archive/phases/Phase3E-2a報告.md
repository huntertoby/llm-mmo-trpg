# Phase 3E-2a 報告｜技能資料安全（變奏漏擋＋統一效果走訪）

規格：`docs/phases/Phase3E計畫.md` 3.1／3.3；問題來源：`docs/phases/Phase3審查-Python.md` 第 1、3 點。

## 做了什麼

### ① 變奏漏擋
- `content/skill_primitives.yaml`：`zone`、`delayed_damage`、`copy_skill` 加旗標 `lookup_by_skill_id: true`；`PrimitiveDef` 新欄位 `lookup_by_skill_id`（預設 false）。
- 移除寫死的 `VARIANT_FORBIDDEN_PRIMITIVES` 與 `SkillDef._all_effect_specs`（只走基礎效果）。
- 檢查移到跨檔案驗證 `content/library.py` 的 `_variant_lookup_problems`（`_variant_reference_problems` 內呼叫）：基礎型態與 **每個變奏展開後的型態**（`variant_form`，含 `add_effect`／`replace_effect`）只要含旗標原語就回報「帶變奏的技能不能含「X」效果……」。內容庫載入與技能驗證器（共用 `skill_reference_problems`）都會擋。R1 實測案例（`skill_tidal_spear` 加 `delayed_damage` 變奏）已有回歸測試。
- 語意漏洞：
  - `engine/copying.py`：`LastCast` 只存技能 ID，看不出當時的型態，帶變奏的技能改為明確不能複製（中文訊息）。
  - `engine/skill_triggers.py`：命中後修正規則比對改用實際施放的型態（從 `ctx.events` 最近一筆同施放者、同技能的 `skill_used.variant` 取 `variant_form`）。
  - `engine/ai/utility.py`：AI 召喚範本改用 `cast_form(state, action)`（生效型態）。

### ② 統一效果走訪
- `SkillDef.iter_effects(include_followup=, include_variants=, include_backlash=, include_modifiers=)` 與模組函式 `walk_effect`（`content/skills.py`，涵蓋 `then`／`win`／`lose`／`on_kill`／zone 的 `effects`）。
- 四份走訪改用：`content/skills.py`（變奏檢查）、`content/keyword_derive.py`（`skill_effect_specs`；`walk_effect` 改由 skills 再匯出）、`engine/skill_infusion.py`、`skillgen/combo.py`（現在涵蓋 zone 子效果）。

## 測試
- `tests/content/test_iter_effects.py`（新）：zone 子效果、複合第二段、陷阱、反噬、修正規則、變奏（含巢狀擊殺時效果）逐項表格測試，加全部內建技能的超集合測試。
- `tests/content/test_variant_schema.py`：原「ValidationError」測試改為跨檔案驗證；新增變奏 `add_effect`／`replace_effect` 偷帶 `delayed_damage`、加 `zone` 皆被擋、旗標只在 `zone`／`delayed_damage`／`copy_skill`、內建技能全部仍合法。
- `tests/engine/test_rewrites_4b.py`：帶變奏的技能不能複製。
- `client/src/render/fixtures/skill_icons.json` 重產（隨機組合器因 combo 補上 zone 子效果而產生不同的樣本）。
- 跑過：`tests/content`、`tests/skillgen`、`tests/engine`、`tests/cli`、`tests/api`、`tests/narrative`、`tests/test_architecture.py` 及其餘目錄，全過；`ruff check`、`ruff format --check`、`mypy` 全過。未跑完整 `scripts/check.py`。

## LOG_FORMAT
未改。引擎行為只在「複製帶變奏的技能」與「帶變奏技能的命中後修正比對」兩個邊角改變（舊紀錄若剛好含這兩種情況重播會不同）；是否升版請 PM 合併時決定。

## 待 PM 決定
1. 旗標檢查放在跨檔案驗證（需要 ruleset），schema 層（`SkillDef.model_validate`）本身不再擋；直接建 `SkillDef` 而不經驗證器的程式碼不會被擋。若要 schema 層也擋，需要讓 `SkillDef` 取得原語表。
2. `copy_skill` 對帶變奏技能採「不能複製」；替代做法是 `LastCast` 加 `variant` 欄位（改狀態序列化，要升 `LOG_FORMAT`）。
3. 命中後修正比對的型態改從 `ctx.events` 找 `skill_used`；`AttackRolled` 沒有 `variant` 欄位。若要更直接可在事件加欄位（升 `LOG_FORMAT`）。
4. 上述兩個引擎行為改變是否需要升 `LOG_FORMAT`（目前沒升）。
5. `iter_effects` 預設只走 `effects` 巢狀；反噬與修正命中後效果需旗標，沿用各呼叫端原本的涵蓋範圍（例如 `skill_ban` 仍不含反噬），是否要全面納入由 PM 決定。
