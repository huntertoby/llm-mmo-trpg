# Phase HC-4b 報告：技能規則的預設值搬進 content

依據：`docs/phases/PhaseHC-4b計畫.md`；HC-4a、HC-W2、QF-3a 的開發 PM 裁定；做法照 HC-4a。
基準：main `ff22b9965`（worktree 開工時落後，先 fast-forward 到這裡）。分支 `worktree-agent-a06ad5a9134a85692`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`、`client/`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 技能規則搬家 | `b3cbec1e7` | `skill_rules.py` 預設值改必填；`skills/constants.py` 的規則型上限與 `SkillDef.tier`、`_check_tier_budget` 搬到 `core.yaml` 的 `skill_limits`，改在 `Ruleset` 層檢查；工坊多 5 格 |
| 2a 刪戰鬥核心 6 條 done 規則 | `aad0c04a2` | `classes.yaml`；刪掉後沒有筆數變成沒歸類 |
| 2b 總減傷上限＋元素修正下限一起開 | `0c357f36b` | 兩格開進工坊、說明寫要一起改；只改一格時錯誤掛在那一格 |
| 2c 鎖 xdist `<3.9` | `bdcc8584d` | `pyproject.toml`；`uv.lock` 只有 xdist 那一行 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試；第 1 項另跑逐招預算比對與 78 場戰鬥比對。

## 2. 第 1 項：技能規則搬家

### 2.1 `skill_rules.py`（103 筆 → 0）
- **預設值改必填（79 筆）**：`skill_budget.yaml` 每一欄都有寫（逐欄核對過；其中 `summon_trait_chain／trip／knockback`、`summon_detonate_targets` 的內容檔值本來就和程式預設不同，以內容檔為準，結果不變）。涵蓋 `CostAllowance` 6、`ModifierBudget` 1、`RetierGrowthRules` 4、`FlashCostRules` 1、`FlashTransformRules` 3、`CharacterTierRules` 5、`BudgetRules` 55、`scale_expected_steps_milli`、四張查表。`BudgetRules` 的 `min_character_tier`、`retier_growth`、`flash_cost`、`flash_transform` 本身也改必填（原本是空物件預設）。
- **四張查表的長度**（`obstacle／inscribe／shield_duration_permille`、`wind_spread_permille`，`py-content-rule-bounds-budget-durations`）：schema 不再寫死 10／5／2／2 項（只留 `min_length=1` 護欄）。`skillgen/budget.py` 查表改用表的項數夾住（超過項數用最後一項；現有資料下和原本的 `min(…,10)`、`min(…,5)`、`min(max(d,2),3)` 完全等價）。刻印表的項數改在載入時對照 `core.rune_max_rounds`（`budget_rule_problems`）。
- **`ap_coefficient_permille` 的鍵要剛好是 1、2、3**：從 `BudgetRules._check` 搬到載入內容庫時對照 `core.skill_limits.max_ap_cost`（`budget_rule_problems`，錯誤指向 `skill_budget.yaml`）。

### 2.2 `skills/constants.py`（18 筆 → 2）與 `SkillDef.tier`、`_check_tier_budget`
新增 `core.yaml` 的 `skill_limits`（值照搬）：

| 欄位 | 值 | 原本 |
|---|---:|---|
| `tiers` | 5 | `SkillDef.tier` 的 `le=5`、`CoreRules._check_tier_budget` 的 1～5 |
| `max_ap_cost` | 3 | `MAX_AP_COST` |
| `max_effects` | 4 | `MAX_EFFECTS` |
| `max_cooldown` | 6 | `_MAX_COOLDOWN`（`SkillCost.cooldown`） |
| `min_crit_range` | 15 | `MIN_SKILL_CRIT_RANGE` |
| `max_grant_duration` | 4 | `MAX_GRANT_DURATION` |
| `max_summon_count` | 2 | `MAX_SUMMON_COUNT` |
| `max_on_kill_effects` | 2 | `MAX_ON_KILL_EFFECTS` |
| `max_refund_ap` | 2 | `MAX_REFUND_AP` |
| `max_zone_effects` | 2 | `_MAX_ZONE_EFFECTS` |
| `max_branch_effects` | 2 | `_MAX_BRANCH_EFFECTS` |
| `max_consume_then` | 2 | `_MAX_CONSUME_THEN` |
| `max_cooldown_restore` | 2 | `_MAX_COOLDOWN_RESTORE` |
| `max_modifiers` | 2 | `_MAX_MODIFIERS`／`MAX_MODIFIERS` |
| `max_mastery_modifiers` | 4 | `_MAX_MASTERY_MODIFIERS` |
| `max_variant_replacements` | 2 | `_MAX_VARIANT_REPLACEMENTS` |

- schema（`SkillDef`、`SkillCost`、`VariantSpec`）只留下限（至少 1 個效果、AP 至少 1……）與護欄；上限改由新模組 `content/skills/limits.py` 的 `skill_limit_problems(skill, limits)` 檢查（技能本身＋複合技能第二段＋每個變奏型態）。呼叫的地方：
  - 載入內容庫：`library/skill_checks.py` 的 `_check_skills`（錯誤訊息和原本的 schema 訊息同字句，數字從規則組字）。
  - 技能驗證器：`validate_skill` 新增違規代碼 `cap.limits`，和 `reference` 一樣先擋（階級、AP 超出時預算查表會失敗）；效果數照舊由 `cap.effects` 報（改讀規則）。
  - 技能工坊草稿：`draft_check.check_draft` 照舊當成 schema 錯誤（不算預算）。
- 產生器改讀規則：`composer_dual`、`flash_ops`（4 處）、`skill_tier`、`options`（修正規則條數）、`option_nested`（返還 AP 的上限與說明）、`proposal/build.py`、`proposal_layouts.py`、`validate.py`、`scripts/flash_minor_coverage.py`。
- **不搬、改判**：`MAX_VARIANTS`（2）改判 guard：實際上限是 `core.yaml` 的 `variant_max_by_rarity`，`Ruleset` 層本來就檢查。
- **留到 HC-4b2**：`_MAX_DISPLACE`、`_MAX_ON_HIT_EFFECTS` 只剩 `skills/modifiers.py`（HC-4b2 範圍）在用，`classes.yaml` 留 todo。技能本身推拉距離的上限原本 `SkillDef` 和原語表（`skill_primitives.yaml` 的參數範圍 1–2）各擋一次，現在只留原語表（見待決 3）。

### 2.3 新開的工坊欄位（`tuning_fields.yaml`）
「核心戰鬥規則」（`rules/core.yaml`）組：

| 欄位 | 名稱 | 建議範圍 |
|---|---|---|
| `skill_limits.max_cooldown` | 技能冷卻上限（回合） | 3～12 |
| `skill_limits.min_crit_range` | 技能擴大暴擊的極限（自然骰） | 13～19 |
| `skill_limits.max_grant_duration` | 暫時獲得技能的最長輪數 | 2～8 |
| `skill_limits.max_refund_ap` | 擊殺返還 AP 的上限 | 1～4 |
| `skill_limits.max_cooldown_restore` | 回復資源縮短冷卻的上限（回合） | 1～4 |
| `element_mod_floor_permille`（第 2b 項） | 元素修正下限（‰） | 125～500 |

「裝備規則」組（第 2b 項）：`caps.damage_reduction_permille`（總減傷上限，‰，500～875）。

沒開的（結構，產生器、LLM 提議、工坊選項都照它）：`skill_limits.tiers`、`max_ap_cost`、`max_effects`、`max_summon_count`、`max_on_kill_effects`、`max_zone_effects`、`max_branch_effects`、`max_consume_then`、`max_modifiers`、`max_mastery_modifiers`、`max_variant_replacements`。`skill_budget.yaml` 的 `retier_growth.*`、`min_character_tier.*` 數字欄位本來就在內容檔（這段只拿掉程式預設），沒加進工坊（待決 4）。

### 2.4 測試
只改測試資料與移層的檢查：原本「`SkillDef.model_validate` 會擋上限」的例子改成檢查 `limit_problems`（`tests/skillgen/helpers.py` 新增）或載入內容庫時擋，訊息逐字比；下限的例子改比新的「至少 1」字句。新增 `test_budget_rule_mismatch_is_rejected_when_loading`、`test_ruleset_limits_have_chinese_messages` 等。`test_skill_tier` 的「清空放大旋鈕」改成明寫內容檔的 4 個數值欄位。`scripts/x10/fields.yaml` 把 `skill_limits.*` 列進 keep。

## 3. 第 2 項：前幾段的收尾

- **2a**：刪掉 `py-content-{battle,equipment,forms,item-budget,parts,rules}-config-number` 6 條（都是 HC-4a 搬完、0 筆的 done 規則）。刪掉後沒歸類 0、各類筆數不變。
- **2b**：兩格一起開（2.3）。說明都寫「兩格要一起改：總減傷上限必須等於 1000 − 元素修正下限，只改一格會驗證失敗，兩格都會標出錯誤」。載入檢查（`Ruleset`）的訊息改成寫出兩邊的值並說「兩格要一起改」；工坊檢查（`api/tuning/check.py`）在錯誤指向的檔沒改過時，把錯誤掛到訊息點名的改過的欄位上（原本會落到頁首）。新測試 `tests/api/tuning/test_reduction_pair_hc4b.py`（4 項：兩格都開、只改一格擋在那格、兩格一起改通過、兩格不一致兩格都標）。HC-W2 測試的「不開」清單拿掉這一格。
- **2c**：`pytest-xdist>=3.8.0,<3.9`，`uv lock` 後 `uv.lock` 只變 xdist 的 specifier 一行；`tests/infra` 9 passed。

## 4. config todo 與歸類（`classify.py`）

| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `ff22b9965` | 965 | 38 | 8862 | 196 | 369 |
| 後端 交件 | **840** | 38 | 8875 | 194 | 386 |
| 前端（沒動） | 26 | 0 | 5440 | 98 | 0 |

- config 少 125：`skill_rules.py` 103、`skills/constants.py` 16（15 筆搬走＋`MAX_VARIANTS` 改 guard；剩 2 筆給 HC-4b2）、`rules.py` 的階級數 4、`SkillDef.tier` 1、`skillgen/budget.py` 1（查表改讀項數）。
- guard 多 17：`SkillLimits` 的 schema 護欄 16＋`MAX_VARIANTS`。
- text 少 2：「AP 1、2、3」「階級 1 到 5」的訊息改從規則組字；`limits.py` 的召喚數量訊息照舊 text todo（新規則 `py-content-skills-limits-text-text`）。
- 改 done 的規則：`py-content-skill-rules-config-number`、`py-content-rule-bounds-budget-durations`、`py-content-rules-tier-count`、新的 `py-content-skills-constants-moved`（都 0 筆）。`py-content-rule-bounds-skills` 拿掉 `tier`。`寫死數值-清單.md` 用 `--md` 重產。

## 5. 不變比對

- **逐招預算（434 招）**：基準＝`git archive ff22b9965 src content`；腳本把每招的完整 `BudgetReport`（repr）與 `validate_skill` 的違規一起存成 JSON 逐招比。第 1 項中途兩次、交件前一次，都是 **`skills=434 same=434 different=0`**。
- **78 場戰鬥**（同 HC-4a 的 78 場與腳本）：第 1 項後、交件前各一次，都是 **`battles=78 events=26446 different=0`**（事件總數同 HC-4a）。內嵌規則包只多了 `core.skill_limits`（所以 `ruleset_hash` 會變），其他欄位逐字相同。
- parity、CLI 快照：見第 6 節，沒重產。OpenAPI 重產後沒有差異（`client/openapi.json` 不變）。

## 6. 檢查（最後一個程式 commit `bdcc8584d`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 逐招預算比對 434 招 | different=0 |
| 78 場戰鬥比對 | different=0 |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979 passed） |

分目錄（`run_pytest.py -q tests/<目錄> -n 8`，一次一組，最後一個 commit 上全部重跑）：

| 目錄 | 結束碼 | 結果 |
|---|---|---|
| api | 0 | 1372 passed、1 skipped |
| bot | 0 | 67 |
| cli | 0 | 148 |
| content | 0 | 3169 |
| engine | 0 | 5120 |
| infra | 0 | 9 |
| llm | 0 | 495 |
| narrative | 0 | 479 |
| roguelite | 0 | 279 |
| server | 0 | 77 |
| shared | 0 | 76 |
| sim | 0 | 180 |
| skillgen | 0 | 4637 passed、7 skipped |
| world | 0 | 1328 |
| 頂層 `tests/test_*.py` | 0 | 256 |

- 開發中的失敗都是 2.4 的移層測試（content 19、engine 9、skillgen 3、api/tuning 3），修好後該檔與整個目錄重跑為 0（上表）。其中 skillgen 有 1 個不是單純改預期：工坊草稿 `tier: 9` 原本被 schema 擋，上限移出 schema 後會進到預算而 `KeyError`，因此加了 2.2 的草稿檢查（當成 schema 錯誤）。
- 看門狗沒有回報 worker 掛掉或卡住（交件那一輪的 log 沒有 `node down`、沒有保留留證資料夾）。
- 前端沒動，沒跑 vitest／tsc／build。

## 7. 待 PM 決定（5 件；都照最保守的做了）

1. **改 done 的規則要不要也刪**：規格寫「改完的那一區 status 改成 done」，我照做（4 條、都 0 筆）。但依第 2a 項的理由（之後新寫的預設值會被當成 done 放過），這幾條也可以在下一段刪掉。
2. **錯誤訊息的字句**：上限移出 schema 後，`SkillDef` 只擋下限，訊息改成「至少 1」（例：`ap_cost: 0` 原本是「必須是 1 到 3」，現在是「至少 1」，上限 3 的訊息在 `Ruleset` 層才出現）。工坊的 `ap_cost`、`cost.cooldown` 錯誤仍掛在原欄位上（測試照新字句改）。
3. **技能的推拉距離上限只剩原語表**：原本 `SkillDef`（`_MAX_DISPLACE`）和 `skill_primitives.yaml` 的參數範圍（1–2）重複擋；現在技能本身只看原語表（內容檔），沒有另外對照 `core.max_displace_distance`。修正規則（`modifiers.py`）的 `_MAX_DISPLACE` 留給 HC-4b2。
4. **工坊只開 5 個規則數值**（＋2b 的 2 格）：結構型的上限沒開（2.3）；`retier_growth`、`min_character_tier` 的數字欄位本來就在內容檔，這段沒加進工坊。要開的話直接加 `tuning_fields.yaml` 的「技能預算表」，但要給分組（目前 HC-B 的分組沒有對應的「升階」「角色階級」組）。
5. **範圍外的小改動**：為了讓數字只存在內容檔，動了 `skillgen/budget.py`（查表改讀項數，結果等價）、`skillgen` 其他讀上限的地方（2.2）、`skillgen/draft_check.py`、`api/tuning/check.py`（2b 的錯誤掛欄位）。`skillgen/option_nested.py` 的 `NESTED_PARAMS` 子效果數（1、2）還是寫死，和 `skill_limits` 的巢狀上限同值，屬 HC-5，沒改。

## 8. 平衡疑慮（無）

沒有。只換數字放的地方，434 招預算與 78 場戰鬥逐字相同。

## 開發 PM 裁定（2026-11-21）

通過，已用 --no-ff 合併。434 招逐招預算和 78 場戰鬥比對都是 different=0，config todo 965 → 840。

待決五件：
1. **0 筆的 done 規則**：刪。HC-4b2 開頭先把這 4 條刪掉，理由同第 2a 項。
2. **上限移到 Ruleset 層才報錯**：同意。
3. **推拉距離上限**：同意現狀。HC-4b2 搬 `_MAX_DISPLACE` 的時候，要加上和 `core.max_displace_distance` 的對照驗證。
4. **`retier_growth`、`min_character_tier` 沒開**：要開。HC-4b2 在預算表加一組「階級與升階」，把這兩項放進去。結構型的上限照舊不開。
5. **範圍外改的檔**：接受，因為結果等價，而且都是跟著上限搬家連帶要改的地方。`NESTED_PARAMS` 留給 HC-5。
