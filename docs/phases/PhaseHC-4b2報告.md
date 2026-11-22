# Phase HC-4b2 報告：技能挑選、組合器、分歧進化、修正規則的預設值搬進 content

依據：`docs/phases/PhaseHC-4b2計畫.md`；HC-4b 報告的開發 PM 裁定 1、3、4。做法照 HC-4a、HC-4b。
基準：main `37eecc23d`（worktree 開工時在 `0fcee7f46`，先 fast-forward）。分支 `worktree-agent-a6dfd6a944423ba7e`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 收尾：刪 4 條 0 筆的 done 規則 | `d3b04864f` | `classes.yaml`；刪掉後沒歸類 0、筆數不變 |
| 2 搬家 | `1d4d3257c` | 四個檔的預設值改必填；規則型上下限搬到 `core.yaml`／載入檢查；`_MAX_DISPLACE` 加對照驗證；規則數值開進工坊（含新的「技能分歧進化」表） |
| 3 「階級與升階」分組 | `f6cbed3c2` | 預算表加一組，開 `retier_growth`、`min_character_tier` 共 32 格 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試；第 2 項另跑第 5 節的五種比對。

## 2. 第 1 項：收尾

刪掉 `py-content-skill-rules-config-number`、`py-content-rule-bounds-budget-durations`、`py-content-rules-tier-count`、`py-content-skills-constants-moved`（都 0 筆）。刪掉後沒有筆數變成沒歸類（`classify.py --check` 0、各類筆數不變），不用補規則。

## 3. 第 2 項：搬家

### 3.1 `skill_pick.py`（41 筆 → 0）
- `PickPoolRules` 13、`PickWeights` 25、`WishTagRules` 6 個預設值改必填（`skill_pick.yaml` 每格都有寫、值相同）；`SkillPickRules.pool／weights／wish_tags` 也改必填。`ContentLibrary.skill_pick` 改成必填欄位。
- 願望標籤上限（`max_keywords`、`max_effects`、`max_elements_dual` 的 `le=2`）：07 7.6 的規則數字就是 `skill_pick.yaml` 的值，schema 不再另外寫死（只留 `ge=0`）。沒有另外的 `Ruleset` 對照（見待決 1）。

### 3.2 `composer_rules.py`（22 筆 → 0）
- 改必填：`blow_distances`、`borrow_cooldown`、`RecipeSummonUnit.range`、`LlmTopicRules` 3 個、`LlmCostRules.max_cooldown`、白板的 `ap_cost`、`fallback_ap_cost`、`max_attempts`；`llm_topic`、`llm_cost`、`recipes` 本身也改必填。
- **沒寫進內容檔的先寫進去**：白板 `summon_ap_cost: 1`、`summon_cooldown_max: 4`、`self_ap_cost: 1`（原本靠程式預設），再改必填。
- **AP 1～3**（`CostStep.ap`、白板四個 AP 的 `le=3`、`ap_weights` 的鍵）：搬到 `composer_rule_problems(composer, core, basic_summon_units)`，載入內容庫時對照 `core.skill_limits.max_ap_cost`（錯誤指向 `skill_composer.yaml`）。
- **自身狀態代價 2–3**（`CostRules._check_self_status_duration`）：改讀 `SelfStatusCost.duration` 的 schema 上下限，不另寫數字（那兩個數字留在 `specs.py`，仍是 config todo，不在這段範圍）。
- **1 階基本召喚物的射程**：`composer_recipes._tier_units` 原本在基本召喚物不在 `summon_units` 時用 `RecipeSummonUnit(unit=b)`（預設射程 4）。`range` 改必填後拿掉這條退路，改成載入時檢查基本召喚物都在 `recipes.summon_units`（現有內容兩隻都在，射程照那一項，結果不變）。
- `_MIN_SIDES`（骰子至少 2 面）改判 guard。

### 3.3 `skill_evolution.py`（8 筆 → 0）
- 改必填：`deepen_hp_permille`、`count_power_permille`、`far_distance`、`spread_targets_permille`、`bridge_keyword_tries`、`summon`。
- `count_number` 的 `ge=2, le=2`：改成載入時檢查要等於 `core.skill_limits.max_summon_count`（`_check_evolution`）。
- `skill_evolution.yaml` 改成必備檔（原本沒有檔案時用全預設的 `EvolutionTable()`；全專案只有 `content/` 一份內容，都有這個檔）。`ContentLibrary.evolution` 改成必填欄位。

### 3.4 `skills/modifiers.py`（10 筆）＋`skills/constants.py`（2 筆）→ 0
新增 `core.yaml` 的 `skill_limits.modifier_bounds`（值照搬；`modifiers` 是工坊禁開的欄位名，所以叫 `modifier_bounds`）：

| 欄位 | 值 | 原本 |
|---|---:|---|
| `damage_permille_min` | -500 | `ModifierChange.damage_permille` 的 `ge` |
| `heal_permille_min` | -500 | `heal_permille` 的 `ge` |
| `hit_bonus_max` | 3 | `hit_bonus` 的 ±3 |
| `cooldown_delta_max` | 2 | `cooldown_delta` 的 `ge=-2` |
| `push_distance_delta_max` | 2 | `push_distance_delta` 的 `le` |
| `range_delta_max` | 2 | `range_delta` 的 `le` |
| `summon_duration_delta_max` | 2 | `summon_duration_delta` 的 `le` |
| `max_add_tags` | 3 | `_check_tags` 的 1～3 |
| `max_on_hit_effects` | 2 | `_MAX_ON_HIT_EFFECTS` |
| `on_hit_max_displace` | 2 | `_MAX_DISPLACE` |

- `ModifierChange` 只留另一側的界線（`le=1000`、`le=-1`、`ge=1`、`ge=-1`）與「至少 1 個」；上下限由 `skills/limits.py` 的 `skill_limit_problems` 檢查（新的 `_modifier_problems`），所以載入內容庫、技能驗證器（`cap.limits`）、技能工坊草稿三處都會擋（同 HC-4b）。
- **HC-4b 裁定 3**：`CoreRules._check_modifier_displace` 檢查 `push_distance_delta_max`、`on_hit_max_displace` 都不能大於 `max_displace_distance`，訊息寫「兩格要一起改」。
- `form_upkeep_permille` 的 `ge=-1000`（減免 100%）改判 guard（數學下限）。
- 讀上下限的產生器改讀規則：`skillgen/options.py`（技能工坊選項的範圍、標籤數、命中後效果數；輸出不變）、`skillgen/flash_ops.py`（閃現「綿延」「冷卻」的上限，刪 `MAX_SUMMON_DURATION_DELTA`、`MAX_COOLDOWN_DELTA`）。

### 3.5 開進工坊（第 2 項，共 23 格＋一張新表）

「核心戰鬥規則」（`rules/core.yaml`）：

| 欄位 | 名稱 | 建議範圍 |
|---|---|---|
| `skill_limits.modifier_bounds.damage_permille_min` | 修正規則：傷害減少的下限（‰） | −1000～−250 |
| `…heal_permille_min` | 修正規則：治療量減少的下限（‰） | −1000～−250 |
| `…hit_bonus_max` | 修正規則：命中加減的上限 | 1～6 |
| `…cooldown_delta_max` | 修正規則：命中後冷卻最多縮短幾回合 | 1～4 |
| `…push_distance_delta_max` | 修正規則：推拉距離加成的上限（格） | 1～2 |
| `…range_delta_max` | 修正規則：射程加成的上限（格） | 1～4 |
| `…summon_duration_delta_max` | 修正規則：召喚物持續加成的上限（輪） | 1～4 |
| `…on_hit_max_displace` | 修正規則：命中後推拉的最遠距離（格） | 1～2 |

「技能組合器的附帶配方」（`skill_composer.yaml`）：`whiteboard.summon_ap_cost`（召喚白板的 AP）、`whiteboard.self_ap_cost`（自身位移／增益白板的 AP）、`whiteboard.summon_cooldown_max`（召喚白板的冷卻上限）、`structure.borrow_cooldown`（組合器做的預支技能的冷卻）、`llm_cost.max_cooldown`（LLM 提議的冷卻上限）、`recipes.summon_units[*].range`（整招召喚的射程，8 隻各一格）。

新表「技能分歧進化」（`skill_evolution.yaml`，新的對象種類 `skill_evolution`）：`summon.deepen_hp_permille`（召喚技加深：最大 HP 多幾‰）、`summon.count_power_permille`（召喚技數量型：每隻的強度）。新種類要改 `tuning_fields.py`（`TARGET_MODELS`、`TABLE_KINDS`、`TuningTarget.kind`）、`api/tuning/objects.py`（名稱、頂端提示），前端 `client/src/api/client.ts`、`TuningScreen.tsx` 各加一行讀這張表。

沒開的（結構或程式參數）：`modifier_bounds.max_add_tags`、`max_on_hit_effects`；願望標籤每類最多幾個；`blow_distances`（旋鈕階梯）；`whiteboard.max_attempts`、`llm_topic.*`、`bridge_keyword_tries`（重試次數、選單大小）；`count_number`（等於 `max_summon_count`）；`far_distance`、`spread_targets_permille`（用法統計的門檻，不是計價）。

說明都寫了調高、調低的效果；會和別的格互相限制的（推拉距離、白板 AP、LLM 冷卻上限）寫了要一起改。

## 4. 第 3 項：「階級與升階」分組

預算表（`skill_budget.yaml`）新增分組「階級與升階」，32 格：
- `retier_growth`：`stretch.apply_status.duration`、`stretch.create_surface.duration`、`magnitude_step`、`magnitude_max`、`max_extra_cooldown`、`max_cooldown`、`max_extra_ap`、`target_tolerance_permille`（8）。
- `min_character_tier`：`kinds.modifier／stance`、`skeletons.summon／trap／stance`、`primitives` 10 個、`shapes.square3／chain`、`line_length`、`line_tier`、`followup`、`second_element`、`dual_scaling`、`terrain_area[*].min_cells`（24）。
- 每格有中文名稱，說明寫調高、調低的效果。`terrain_area[*].tier` 的路徑含工坊禁開的欄位名 `tier`，沒開（見待決 3）。
- `test_budget_table_hcb` 的「結構」清單拿掉 `retier_growth.`、`min_character_tier.`，只留 `min_character_tier.terrain_area[`。

## 5. 不變比對（基準 `git archive 37eecc23d src content`）

| 比對 | 結果 |
|---|---|
| 逐招預算 434 招（完整 `BudgetReport` repr＋`validate_skill` 違規；另比 `skill_pick`、`composer`、`evolution` 三張表的 `model_dump`） | `skills=434 same=434 different=0`、表 0 差異（第 2 項中途、第 2 項後各一次） |
| 78 場戰鬥（同 HC-4a 的 78 場與腳本） | `battles=78 events=26446 different=0`；內嵌規則包只多 `core.skill_limits.modifier_bounds`（所以 `ruleset_hash` 會變） |
| 組合器出題：`scripts/recipe_census.py --seeds 4 --tiers 1,3 --rarities common,epic` | `cells=204 same=204 different=0`（排除計時欄位） |
| 許願出題：`scripts/wish_coverage.py run --seeds 3 --tiers 1,2` | `buckets=384 same=384 different=0`（排除計時欄位 `seconds`） |
| 挑選模式三選一：4 個 build × 種子 0、1 × 升級白板／完整技能，`pick_slots` 每格候選的技能全文、分數、分項 | 16 份、48 格、148 個候選，JSON 逐位元組相同 |

parity、CLI 快照：見第 6 節，沒重產。OpenAPI 重產後沒有差異（`client/openapi.json` 不變）。

## 6. 檢查（最後一個程式 commit `f6cbed3c2`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1764 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 逐招預算比對 434 招 | different=0 |
| 78 場戰鬥比對 | different=0 |
| recipe census／wish coverage／挑選三選一 | 都 different=0 |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979 passed） |
| `pnpm -C client typecheck` | 0 |
| `pnpm -C client test` | 0（393 檔、4820 項） |
| `pnpm -C client build` | 0 |

分目錄（`run_pytest.py -q tests/<目錄> -n 8`，一次一組，最後一個 commit 上全部重跑）：

| 目錄 | 結束碼 | 結果 |
|---|---|---|
| api | 0 | 1383 passed、1 skipped |
| bot | 0 | 67 |
| cli | 0 | 148 |
| content | 0 | 3209 |
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
| 頂層 `tests/test_*.py` | 0 | 257 |

- 開發中的失敗都是移層／新欄位造成的測試預期（`test_modifier_schema` 2、`test_skill_composer_content` 1、`test_x10_fields`／`rescale` 2、`test_hardcoded_scan` 抽查 2、`test_heal_summon_modifiers` 1、工坊 2），修好後該檔與整個目錄重跑為 0。
- 看門狗沒有回報 worker 掛掉或卡住（交件那一輪的 log 沒有 `node down`、沒有 `stuck.txt`）。`.claude/pm-logs/pytest/` 裡保留的三個資料夾是開發中有失敗的那幾輪（失敗時自動保留），不是卡住。
- 新增測試：`tests/content/test_rule_defaults_hc4b2.py`（少寫一格就驗證失敗、進化檔必備、數量型對照、推拉距離對照、願望上限）、`tests/api/tuning/test_workshop_open_hc4b2.py`（新開欄位的值與說明、進化表、推拉與白板 AP 超限被擋、「階級與升階」分組）；`test_modifier_schema` 加上下限移層的逐字訊息與邊界值。

## 7. config todo 與歸類（`classify.py --stats`）

| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `37eecc23d` | 840 | 38 | 8875 | 194 | 386 |
| 後端 交件 | **753** | 38 | 8889 | 194 | 398 |
| 前端（只加兩行） | 26 | 0 | 5440 | 98 | 0 |

- config 少 87：`skill_pick.py` 41、`composer_rules.py` 22、`skill_evolution.py` 8、`skills/modifiers.py` 10、`skills/constants.py` 2，加上讀規則後消失的 `flash_ops.py` 2、`options.py` 2。
- 四個目標檔的 config 都是 0（`_MIN_SIDES`、`form_upkeep_permille` 的 −1000 改判 guard）。
- 0 筆而刪掉的規則（照 HC-4b 裁定 1，不留 done）：`py-content-rule-bounds`、`py-content-rule-bounds-wish`、`py-content-composer-rules-config-number`、`py-content-skill-evolution-config-number`、`py-content-skill-pick-config-number`、`py-content-skills-constants-config-number`、`py-content-skills-modifiers-config-number`。`py-content-rule-bounds-skills` 拿掉搬走的欄位。`寫死數值-清單.md` 用 `--md` 重產。

## 8. 待 PM 決定（都照最保守的做了）

1. **願望標籤上限沒有另外的 `Ruleset` 對照**：07 7.6 的「關鍵字、效果最多 2 個，元素 2 階起 2 個」就是 `skill_pick.yaml` 的值，我只拿掉 schema 重複寫的 `le=2`，沒有開進工坊（UI 與 LLM 標籤的結構）。`world_rules.yaml` 另有 `max_keywords`（舊許願流程，預設 2）不在範圍。
2. **`skill_evolution.yaml` 改成必備檔**：原本缺檔時用程式預設值；改必填後缺檔就載入失敗（全專案只有一份內容，都有這個檔）。
3. **升降地形格數表的「階級」欄沒開**：路徑 `min_character_tier.terrain_area[*].tier` 含工坊一律禁開的欄位名 `tier`（`FORBIDDEN_SEGMENTS`），只開了格數 `min_cells`。要開得放寬禁開名單或改 YAML 的鍵名。
4. **新開一張工坊表「技能分歧進化」**：為了開召喚技進化的兩個幅度，加了對象種類 `skill_evolution`（後端與前端各幾行，前端 tsc／vitest／build 都過）。不想多一張表的話，可以改放到預算表的「召喚」組，但檔不同、要改寫回邏輯。
5. **範圍外的小改動**：`skillgen/options.py`、`skillgen/flash_ops.py` 改讀 `modifier_bounds`（同 HC-4b 的連帶改動，輸出不變）；`skillgen/composer_recipes.py` 拿掉基本召喚物的預設射程退路（3.2）。`skillgen/skill_pick.py` 的 `thin_reasons(epic_min_effects=2)` 函式預設值（config todo 1 筆，和 `weights.thin_epic_min_effects` 同值）不在規格列的檔，沒改。

## 9. 平衡疑慮（無）

沒有。只換數字放的地方，434 招預算、78 場戰鬥、組合器、許願、挑選模式的出題都逐項相同。

## 開發 PM 裁定（2026-11-21）

合併進 main（`--no-ff`）。合併後在 main 上重跑 ruff、format、mypy、lint-imports、`classify.py --check`，結束碼都是 0；新增和改動的 4 個測試檔 100 passed。全量檢查由 push hook 跑。

待 PM 決定的 5 件：
1. **願望標籤上限**：照做。數字只寫在 `skill_pick.yaml` 一處，不另加對照，也不開進工坊。
2. **`skill_evolution.yaml` 改成必備檔**：照做。專案只有一份內容，缺檔就載入失敗比默默用預設好。
3. **`terrain_area[*].tier` 不開**：照做。工坊不開 `tier` 欄位的規則不變。
4. **新增工坊表 `skill_evolution`**：保留。召喚技進化的幅度不是預算計價，獨立一張表比塞進預算表清楚。
5. **範圍外的小改動**：接受，輸出都不變。`skillgen/skill_pick.py` 的 `thin_reasons` 預設值併進 HC-5（skillgen 常數）。
