# Phase 3T-1 報告｜修正規則 change 種類與預算旋鈕進 YAML

> 規格：`docs/phases/Phase3T計畫.md` 表的 3T-1 列與第 2 節驗收；依據 `docs/phases/Phase3後段審查-Python.md` 第 1、2 點（P1、P2）。
> 純整理：戰鬥快照雜湊、重播、卡片文字不變（CLI 快照沒有重產）。改變 LLM 補數值結果的地方見第 3 節。

## 1. 做了什麼

### ① 修正規則的 change 種類（P1）

- **新增 `content/modifier_changes.yaml`**（21 種，依原本 `MODIFIER_CHANGES` 的順序）：每種宣告 `name_zh`（玩家名稱）、`applies_to`（可套用對象）、`self_only`、`reshapes`（技能變形）、`per_turn_limit`、`nonzero`、`true_only`，以及 `budget`（`unit: structured|magnitude|count|flag`、`points`／`points_if_negative`（`points_milli` 的鍵）、`signed`、`per`、`note`、`hit_gated`）。檔頭寫明欄位意義與「新增一種要補哪裡」。
- **新模組 `src/trpg/content/modifier_changes.py`**：`ModifierChangeDef`／`ModifierChangeTable`／`ChangeBudget` schema、`bundled_modifier_changes()`（schema 匯入時讀內建 `content/`，同 `yaml_sources` 的做法）、`modifier_change_problems()`。
- **`content/skills.py`**：`MODIFIER_CHANGES`、`CHANGE_TARGETS`、`SELF_ONLY_CHANGES`、`SHAPE_CHANGES`、`PER_TURN_LIMIT_CHANGES` 改由 YAML 推導；`ModifierChange._check` 裡寫死的「不可為 0」「只能 true」清單改成 `NONZERO_CHANGES`、`TRUE_ONLY_CHANGES`（也由 YAML 推導）。數值範圍與型別仍是 `ModifierChange` 的欄位（見待 PM 決定 #1）。推導結果與舊常數逐一比對完全相同。
- **`skillgen/budget.py`**：`_modifier_value` 改依 YAML 的 `budget` 計算。原本的 `per = {...}[kind]`（漏寫就是執行時 `KeyError`）、無數值旗標 tuple、每 100‰ tuple、三行逐種類的 `sign` 特例、`_HIT_GATED`、`_SHAPE_GATED` 全部刪掉；由其他資料算的 5 種（傷害‰、治療‰、推擊格數、命中後效果、形狀轉換）改成登錄表 `STRUCTURED_CHANGES`（每種一個函式，原 `if` 鏈拆開）。
- **`skillgen/player_text.py`**：刪掉 `CHANGE_TEXT`，改讀 YAML 的 `name_zh`（新增 `change_text(library, kind)`，`options.py` 改用它）；`_FIELD_ZH` 裡 20 個 change 種類的項目刪掉（原本就被 `CHANGE_TEXT` 蓋過、從沒被用到；`range_delta` 的 `_WORDS_ZH` 覆蓋保留，輸出不變）。
- **`engine/modifiers.py`**：新增宣告表 `CHANGE_HANDLERS`（種類 → 套用它的查詢函式）。
- **`narrative/skills.py`**：新增宣告表 `DESCRIBED_CHANGES`（卡片文字 `_change_text` 有寫法的種類；原本最後一個分支是 `assert`，漏寫會在執行時才炸）。
- **內容庫**：`ContentLibrary.modifier_changes`（從內容資料夾載入；**不嵌入規則包**，避免改到戰鬥紀錄與 `Ruleset`）；`registry.KNOWN_CONTENT_FILES` 加一筆。

**載入時檢查（漏寫報中文 `ContentError`，不再是執行時 `KeyError`）**：

| 檢查 | 位置 | 錯誤路徑 |
|---|---|---|
| YAML 的種類 ＝ `ModifierChange` 的欄位（雙向） | `load_library` → `_check_modifier_changes` | `modifier_changes.yaml` |
| `budget.points`／`points_if_negative` 在 `skill_budget.yaml` 的 `modifier.points_milli` | 同上 | 同上 |
| 引擎 `CHANGE_HANDLERS`、卡片文字 `DESCRIBED_CHANGES`、`structured` 種類在 `STRUCTURED_CHANGES` | `primitive_coverage.check_primitive_coverage`（CLI、API 啟動） | 同上 |
| 玩家文字 | YAML `name_zh` 必填（schema） | — |

### ② 預算旋鈕（P2）

- **`PrimitiveParam.knob`**（`content/skills.py`，新 `PrimitiveKnob`）：`none`、一個旋鈕或旋鈕列表（取第一個成立的）。欄位：`ladder`（`dice`、`multipliers`、`push_pull_distances`、`blow_distances`、`status_duration`、`surface_duration`、`stack_amount`、`per_stack`、`param_range`）、`weight`（`caller`／`core`／`other`／`status`／`surface` 或整數）、`start`／`max`／`step`（只給 `param_range`）、`categories`／`exclude_categories`、`when`（同效果其他參數的值）。`param_range` 需要 int 參數有 min／max（schema 檢查）。
- **`content/skill_primitives.yaml`**：43 個參數加上 `knob`（檔頭有說明）。原本 `fixed` 表與 `lookups` 的每一項都改寫成 YAML（例：武器傷害 `multiplier_permille` 用 `exclude_categories: [spell]`、法術傷害 `dice` 用 `categories: [spell]`；賭注 `{ladder: param_range, start: 300, step: 50}`；法力回復 `when: {resource: [mana]}`），其他有數值參數、非 fixed 原語的參數明寫 `knob: none`。
- **`skillgen/composer_parts.py`**：`effect_knobs` 改成依參數順序讀 YAML 的旋鈕；階梯實作是登錄表 `KNOB_LADDERS`；`fixed` 表、`_status_knobs`／`_surface_knobs`／`_stack_knobs`、`_GAMBLE_CHANCES` 刪掉。簽名不變（組合器與 `proposal_budget` 不用改）。
- **coverage**：`primitive_coverage.knob_problems`——`budget_basis` 不是 `fixed` 的原語，每個 `int`／`dice` 參數都必須宣告 `knob`（或 `knob: none`），`ladder` 要在 `KNOB_LADDERS`；併進 `check_primitive_coverage`。
- **補上的旋鈕**：`grant_ap.amount`（1–2）、`extra_reaction.amount`（1，見待決 #3）、`summon.duration`（1–4）、`zone.duration`（1–4）、`revive.hp_permille`（100–1000，每 100）、`restore_resource.amount` 的 `resource: cooldown`（1–2，見待決 #2）；權重都是 `other`。

### ③ LLM 提議 schema 的 change 欄位

**沒有做，留給 4-L8。** 現行提議模型（`skillgen/proposal.py`）根本沒有 `modifiers` 欄位，`modifier` 骨架在 `CLOSED_SKELETONS`、`PROPOSAL_KINDS` 不含修正型；要產生 change 欄位等於開放修正型技能（還要 `applies_to`、條件、per_turn_limit 等），超出「純整理」。現在已備好的資料：種類、可套用對象、self_only 等在 `modifier_changes.yaml`；數值範圍可用 `options.py` 已有的 `model_range(ModifierChange.model_fields[name])` 取得。

## 2. 行為一致的證據

| 項目 | 方法 | 結果 |
|---|---|---|
| 舊常數 vs YAML 推導 | 執行 HEAD 版 `skills.py` 的常數段與新常數比對 | `MODIFIER_CHANGES`（含順序）、`CHANGE_TARGETS`、`SELF_ONLY_CHANGES`、`SHAPE_CHANGES` 完全相同 |
| 預算 | 另開 HEAD 的 worktree，對內容庫全部 301 招 `skill_budget(...)` 的 `repr` 前後比對 | 逐字相同（含修正技能的每列點數與說明文字） |
| 旋鈕 | 前後對 786 種輸入（每個原語、每種狀態／表面／層數、法力／冷卻／耐力資源 × spell／weapon／body × 權重 1／3）比對 `effect_knobs` | 只有第 3 節列出的 6 種原語不同，其餘逐字相同 |
| CLI 快照（戰鬥雜湊、`skills list`、`skills show` 全部） | `tests/cli/test_output_snapshots.py`（slow） | 通過，**沒有**重產 |
| 卡片文字／圖示 fixture | 重產 `tests.narrative.icon_fixture`、`scripts/export_client_fixtures.py` | 無差異 |

## 3. 會改變結果的地方（逐條）

只影響 `effect_knobs` → LLM 提議的預算補值（`proposal_budget.budget_filler`）。隨機組合器只對旋鈕原本就有的原語呼叫 `add_knobbed`（這 6 種走 `ctx.add(spec, ())`），所以組合器輸出不變；手寫技能與戰鬥不變。

| 效果 | 之前 | 之後 | 影響 |
|---|---|---|---|
| `grant_ap` | 沒有旋鈕（停在最小值 1） | `amount` (1, 2)，權重 other | 預算過弱時可補到 2 AP |
| `extra_reaction` | 沒有 | `amount` (1,) | 只有一階，`can_up` 為假，不抽亂數；實際結果不變 |
| `summon` | 沒有（`duration` 停在 LLM 給的值或最小值） | `duration` (1, 2, 3, 4) | 旋鈕會先重設為 1 再往上調；召喚技能的持續輪數由預算器決定 |
| `zone` | 沒有 | `duration` (1, 2, 3, 4) | 同上 |
| `revive` | 沒有 | `hp_permille` (100, 200, …, 1000) | 復活 HP 比例由預算器決定 |
| `restore_resource`（cooldown） | 沒有（只有 mana 有） | `amount` (1, 2) | 冷卻回復可補到 2 |

另外：`skill_primitives.yaml` 的 `PrimitiveParam` 多了 `knob` 欄位，`Ruleset` 序列化（戰鬥紀錄 JSON 內嵌的規則包）每個參數多一個 `knob` 鍵；`ruleset_hash`（內容檔雜湊）因內容檔變動而改變——和任何內容修改一樣，**戰鬥中的舊 roguelite 存檔無法重播**（戰鬥之間的存檔照常可讀）。CLI 的文字輸出不受影響。

## 4. 測試

- `tests/test_primitive_coverage.py` 新增 11 個：真實內容的 change 種類完全對應（YAML ＝ 欄位 ＝ 引擎 ＝ 卡片文字，structured ＝ 登錄表）；新種類缺項一次列出三處；非 structured 不需登錄；YAML 與欄位／點數鍵對不上；`load_library` 少寫一種時丟 `ContentError`（路徑 `modifier_changes.yaml`）；coverage 缺引擎時丟錯；真實內容旋鈕完整；缺旋鈕、`knob: none`、fixed 原語不需要；階梯沒實作；`param_range` 範圍不合法；`load_checked_library` 刪掉一個旋鈕時丟錯。
- `tests/skillgen/test_proposal_budget.py` 新增 12 個參數化：6 個新旋鈕與 4 個原本旋鈕的階梯與權重、`cleanse` 沒有旋鈕、傷害依類別換骰子／倍率。
- 跑過：`tests/skillgen tests/content tests/narrative tests/api tests/llm tests/test_architecture.py tests/test_primitive_coverage.py`（4263 passed、1 skipped）、`tests/engine/test_modifiers.py`、`tests/engine/test_heal_summon_modifiers.py`、`-m "slow or not slow" tests/cli`（153 passed）；`ruff check`、`ruff format --check`、`mypy`（757 檔無問題）、`lint-imports`（7 kept）。依指示沒有跑完整 `scripts/check.py`。

## 5. 複雜度 noqa

沒有新增任何 `# noqa`。

## 6. 待 PM 決定

1. **change 的數值範圍仍在 Python**：`ModifierChange` 的欄位（`ge`／`le`、型別、`shape_to` 的 Literal）沒有搬進 YAML。搬過去要自己做範圍驗證，pydantic 的錯誤訊息（工坊玩家看得到，經 `plainify`）會改變；目前用「YAML 種類 ＝ 欄位」雙向檢查保證兩邊一致。是否在 4-L8 開放修正型時一併搬？
2. **審查寫的「restore_resource（耐力）」不存在**：`resource` 只能是 `mana` 或 `cooldown`（`EffectSpec.resource: Literal["mana", "cooldown"]`）。實際缺旋鈕的是 `cooldown`，已補 `amount` 1–2（上限沿用 `_MAX_COOLDOWN_RESTORE = 2`）。若原意是新增耐力回復，那是新玩法，需玩法 PM 決定。
3. **`extra_reaction.amount` 範圍只有 1**：照規格補了 `param_range` 旋鈕（只有一階，實際無作用）；範圍放寬時自動生效。若寧可明寫 `knob: none` 請告知。
4. **新旋鈕的階梯與權重是保守選擇**：都用參數自己的 min～max、權重 other；`revive` 每 100‰ 一階；`summon` 只調 `duration`（`count`／`power_permille`／`max_hp_permille` 是分歧進化的參數，`knob: none`）。未跑模擬；是否要用 `trpg sim` 看 LLM 提議的召喚／區域技分佈再調。
5. **其他非 fixed 原語仍是 `knob: none` 的數值參數**（行為照舊、未補）：`create_obstacle.duration`、`shield.duration`、`hurl_object.range`、`delayed_damage.rounds`／`radius`、`sacrifice_summon.radius`、`zone.speed`、`grant_skill.duration`、`damage` 的 `lifesteal_permille`／`form_bonus_permille`／`spread` 等。是否要補，請 PM 決定。
6. **change 種類的常數讀內建 `content/`**：`trpg.content.skills` 的模組常數（schema 驗證用）固定讀專案內建資料（同 3E-2f 的 `yaml_sources`），`TRPG_CONTENT_DIR` 指向別的資料夾時，`ContentLibrary.modifier_changes` 讀那個資料夾、常數仍是內建的；兩邊都經同一個欄位檢查。
7. **LLM 提議 schema 的 change 欄位留給 4-L8**（理由見 1 ③）。
