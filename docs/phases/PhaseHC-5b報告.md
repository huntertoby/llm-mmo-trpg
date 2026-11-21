# Phase HC-5b 報告：組合器與候選常數搬進 content

依據：`docs/phases/PhaseHC-5b計畫.md`；HC-5a、QF-4b 報告最後的開發 PM 裁定。
基準：main `16126a539`（worktree 開工時就在這裡）。分支 `worktree-agent-a734fa11c38dad6cc`，沒 push。
數值一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`、`CLAUDE.md`、`.claude/`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 組合器與候選常數搬家 | `551661bc8` | `skillgen/` 的 config todo 搬進 5 個內容檔；6 筆判成結構常數；預算表新數字一起開（見 2.6） |
| 2 護主、伴生代價只留一份 | `cd21b85cc` | 組合器配方改讀閃現轉型模板；強度嘗試順序共用新模組 `skillgen/beside_power.py` |
| 3 陷阱輪數在輸入層補值 | `ed8b98690` | `draft.fill_trap_rounds`；工坊檢查、匯出、自訂技能、LLM 提議 |
| 4 伴生被動加快取 | `eaadde9f6` | 照護主的 `memo` |
| 5 開進工坊 | `a5f418d44` | 組合器 15 格、進化 6 格、挑選 1 格（預算表的在第 1 項） |
| 6 收尾 | `493410f2a` | 刪掉 33 條變成 0 筆的規則，`--md` 重產清單 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check` 與相關測試（第 1 項的 commit 有一個新測試檔留了 2 個 lint 錯，第 3 項的 commit 順手修掉）。

## 2. 第 1 項：搬到哪裡

### 2.1 `content/skill_composer.yaml`（`ComposerRules`，全部必填）

| 原本 | 新格 | 值 |
|---|---|---|
| `composer_parts._fixed_effect` 定時炸彈的 `randint(1,3)`、`randint(0,2)` | `structure.delayed_damage_rounds`、`delayed_damage_radius`（`IntRange`） | 1～3、0～2 |
| `composer_parts._GAMBLE_WIN`、`_GAMBLE_BACKLASH`、`chance(700)` | `structure.gamble_win_permille`、`gamble_backlash_permille`、`gamble_backlash_chance_permille` | [1500,2000,2500,3000]、[250,500,750]、700 |
| `composer_dual._FIRST_MULTIPLIER` | `structure.second_element_multiplier_permille` | 300 |
| `validate.POINT_BLANK_MIN_REACH`、`composer_parts._POINT_BLANK_MIN_RANGE`（閃現距離加碼也讀它） | `condition.point_blank_min_reach` | 2 |
| `composer_parts._sacrifice_effect` 的 `randint(0,2)` | `sacrifice.radius` | 0～2 |
| `composer_special._LADDERS` 的 7 個數值階梯 | `special.ladders`（新 model `SpecialLadders`，7 個欄位都必填） | 照原值 |
| `composer_special._rule` 的 300 | `special.condition_permille` | 300 |
| 源力 `(1, 2)`（兩處）、給 AP `(1,2)`、射程 `(3,4)`、免死 `(1,2)`、轉移 `(200…500)`、`(2,3)` | `special.source_points`、`grant_ap_amounts`、`rewrite_ranges`、`cheat_death_durations`、`redirect_permille`、`redirect_durations` | 照原值 |
| `_lasting_candidates` 的法力 `(1,4,8,12) × scale`、冷卻 `(2…6)` | `special.lasting_mana`（換算前單位，程式照舊 × `quantity_scale`）、`lasting_cooldowns` | 照原值 |
| `option_variant` 表單的 `min=-3, max=3` | `variant.range_delta` | -3～3 |
| `proposal_subset.MAX_KEYWORDS`、`proposal_topic.WITNESS_MIN_KEYWORDS`、`proposal/models._MAX_NESTED`、`_MAX_TAGS` | `llm_topic.max_keywords`、`witness_min_keywords`、`max_nested_effects`、`max_tags` | 2、2、2、8 |
| `proposal_numbers.DEFAULT_ACTIVE_AP`（`proposal_fallback` 也用） | `llm_cost.default_ap`（載入檢查不超過 `max_ap_cost`） | 2 |
| `composer_recipes._PARAM_PERMILLE`、`_HALF` | `recipes.param_permille`、`high_ground_permille`、`exploit_surface_permille` | 500、500、500 |

**新開區塊 `search`（`ComposerSearch`＋子區塊 `proposal`）**：理由同 HC-5a 的 `rules.search`——重抽次數、候選上限、試組用的假設值不是玩法數值，但改了會改變做得出來的招，所以進資料；集中一處、工坊不開。

| 原本 | 新格 | 值 |
|---|---|---|
| `random_composer.MAX_ATTEMPTS`、`VARIANT_ATTEMPTS`、`KEYWORD_TRIES` | `search.composer_attempts`、`variant_attempts`、`keyword_tries` | 100、25、300 |
| `composer_special._ATTEMPTS`、`_CORE_TRIES` | `search.special_attempts`、`special_core_tries` | 60、16 |
| `skill_tier.RETIER_ATTEMPTS` | `search.retier_attempts` | 3 |
| `evolution.MAX_VARIANT_DRAFTS` | `search.evolution_variant_drafts` | 8 |
| `complete._MAX_STEPS` | `search.complete_max_steps` | 40 |
| `option_effect_rules._assumed_cooldown` 的 `or 9` | `search.probe_cooldown` | 9 |
| `proposal_budget.REPAIR_TUNES`；`proposal_fallback.COMPOSER_TRIES`、`WORKSHOP_MAX_SHAPES`、`WORKSHOP_MAX_EFFECTS`；`proposal_topic.CORE_RETRIES`；`proposal_topup.TOPUP_MAX`、`TOPUP_GROUP_MAX`、`FILLER_STATUS_MAX`；`proposal_witness.WITNESS_MAX` 與 6 個 `_*`、`_shape` 的 3 | `search.proposal.*`（16 格） | 照原值 |

### 2.2 `content/skill_budget.yaml`（`BudgetRules`）
| 原本 | 新格 | 值 |
|---|---|---|
| `budget._plain_base_points` 護盾持續表的 `max(d, 2) - 2` | `shield_duration_start` | 2 |
| `budget._REFERENCE_PARAM` | `modifier.shape_to_reference_size` | 3 |
| `budget._EXEMPT_MIN_TIER` | `retier_growth.weak_floor_exempt_min_tier` | 2 |
| `skill_tier._SUMMON_HP_STEPS`、`_cost_variants` 的 `(1000,500,0)`、`_rock_drafts` 的 300 | `retier_growth.summon_hp_steps`、`cost_scales_permille`、`rock_multiplier_permille` | 照原值 |

### 2.3 `content/skill_evolution.yaml`（`EvolutionTable`）
進化本來就有自己的檔（`library.evolution`，HC-4b2 開了工坊表），所以放這裡、沒放組合器檔。`evolution._LOW_MULTIPLIER_FLOOR`／`_STEP` → `low_multiplier_floor` 300、`low_multiplier_step` 100；`_knobs` 的 `2 if not knobs` → `first_knob_weight` 2；`EXTRA_COOLDOWN_STEPS`、`MIN_COOLDOWN`、`MAX_EVOLVED_COOLDOWN` → `extra_cooldown_steps` 2、`min_cooldown` 2、`max_cooldown` 5。`cost_attempts` 多一個 `library` 參數（`summon_evolution`、`scripts/budget_knob_audit.py`、一個測試跟著改）。

### 2.4 `content/skill_pick.yaml`（`pool`）
`pick_offer.MAX_OFF_ROUTE` → `max_off_route` 2；`SLOT_KEYWORD_TRIES`（許願池共用）→ `slot_keyword_tries` 30；`wish_pick.WISH_CARDS`、`WISH_SEED_PERMILLE`、`WISH_TAG_EXTRA` → `wish_cards` 3、`wish_seed_permille` 1500、`wish_tag_extra` 3。`llm/wish_pick.py`、`world/wish.py` 原本匯入 `WISH_CARDS`，改讀內容庫。`wish_candidates` 的 schema `ge=3` 改成 `ge=1`＋載入檢查「不能小於 `wish_cards`」。

### 2.5 `content/roguelite.yaml`（`candidates`）
`candidates.BRIDGE_VARIANT_CAP` → `candidates.bridge_variant_cap` 400。`CandidateRules` 的 `composer_share_permille`、`composer_tries`、`bridge_variant_cap` 改成 `None`＝照 `roguelite.yaml`（原本程式預設 500、8、400，同內容檔）；取值用新方法 `share()`、`tries()`、`bridge_cap()`。`whiteboard_candidates.generate_whiteboard_candidates` 的 `tries=8` 同樣改成 `None`＝`candidates.composer_tries`。

### 2.6 改讀既有規則（同值，不另開格）
| 原本 | 改讀 | 值 |
|---|---|---|
| `random_composer`（兩處）、`composer_recipes` 的 `rng.choice((2,3))`；`options._trigger_field` 的 `min=2, max=3` | `skill_limits.every_n_hits` | (2,3) |
| `options._self_status_choice` 的 `(2,3)`；`self_penalty._MIN_DURATION` | `skill_limits.min/max_self_status_duration` | 2、3 |
| `option_nested.NESTED_PARAMS` 的上限 2（5 處） | `skill_limits.max_consume_then`／`max_zone_effects`／`max_branch_effects`／`max_on_kill_effects` | 2 |
| `option_nested._SPECIAL` 的 100、10000 | `EffectSpec.damage_multiplier_permille` 的 schema 上下限 | 100、10000 |
| `proposal/models._MAX_VARIANTS` | `content.skills.MAX_VARIANTS`（`SkillDef` 的變奏上限） | 2 |
| `proposal/schema_shape.VARIANT_SWAP_MAX` | `skill_limits.max_variant_replacements`（`shape_schema`、`split_variants` 多一個 `swap_max` 參數） | 2 |
| `proposal_costs.hp_cost_permille` 的 999 | `SkillCost.hp_percent` 的 schema 上限 | 999 |
| `random_composer._compose_plain` 的 `randint(1, 5)` | `skill_limits.tiers` | 5 |
| `composer_rider` 的 `per_stack_permille: 50` | `builder.per_stack.start`（旋鈕最弱一格） | 50 |

### 2.7 判成結構常數（`classes.yaml` 新規則，const）
- `py-skillgen-grade-codes-hc5b`：`candidates.ROUTE_OFF` 與 `_Search._grade` 的 2、`pick_offer.LEVEL_OFF`／`LEVEL_OFF_RELAXED`、`whiteboard_candidates._SPARE`。理由：好壞等級代碼，只用來比大小與當清單索引，像列舉值。
- `py-skillgen-composer-core-count-hc5b`：`composer_parts._core_count` 的 `min(len, 2)`。理由：骨架核心數模式名叫 `up_to_two`，2 是模式的定義。

### 2.8 其他
- `option_fill._scalar` 的「沒有骰面就 6」是死碼（骰子欄位只由 `option_params.dice_field` 產生，一定帶組合器的骰面），改成 `assert`，照 HC-5a `_op_light` 的前例。
- `proposal_subset.ProposalRequest` 的關鍵字個數上限要讀內容庫，所以改到 `select_subset` 檢查（錯誤型別、訊息照舊 `ValueError`「關鍵字最多 2 個…」；「不可重複」照舊在建構時擋）。
- `proposal/convert.to_skill_def`、`penalty_cost`、`apply_cost_choices`、`hp_cost_permille` 的 `library` 改成必填（唯一的呼叫端一直有傳）；拿掉「沒有內容庫」的分支與 `DEFAULT_HP_PERMILLE`。`hp_per_permille` 是 0 時改回傳 `hp_cap`（現值 200，同原本的 200；現在內容檔是 1，走不到）。
- `scripts/x10/fields.yaml`：新格全部 keep（次數、格數、回合、‰、AP；`lasting_mana` 是換算前單位，同 HC-5a 的轉型代價）。
- 預算表的新數字在第 1 項就開進工坊：`test_budget_table_hcb.py` 要求預算檔每個整數不是開了就是列在「結構」清單，`test_workshop_open_hc4b2.py` 要求 `retier_growth` 的整數都在「階級與升階」組，不開這兩個測試就紅。
- 新測試：`tests/content/test_rule_defaults_hc5b.py`（少寫一格就驗證失敗 65 例、值等於舊常數、`default_ap` 與 `wish_cards` 的載入檢查）。改的舊測試只換讀值的地方（拿掉的公開常數）。

## 3. 第 2 項：護主、伴生代價只留一份
- 新模組 `skillgen/beside_power.py`：`beside_template()`（找 `to_passive_companion`、`to_reaction_guardian`，缺了丟 `ValueError`）、`beside_power_tries()`（原 `flash_major._power_tries`）。
- `composer_recipes` 拿掉 `_GUARDIAN_RANGE`、`_GUARDIAN_COSTS`、`_COMPANION_COSTS`、`_POWER_STEP`、`_MIN_POWER` 與自己的 `_power_tries`，改讀轉型模板的 `draft_costs`、`draft_range` 與共用函式。閃現與組合器現在只有一份。
- 測試 `tests/skillgen/test_beside_shared_hc5b.py`：模板的值等於舊常數、強度順序同舊的組合器。

## 4. 第 3 項：陷阱輪數在輸入層補值
- `skillgen/draft.fill_trap_rounds(data, library)`：`trap` 有填但沒有 `rounds` 時補 `composer.trap.enter_rounds.min`（2）。沒有 `id` 時先用**補值前**的內容算 `draft_id`——HC-5a 之前輪數是 schema 驗證時才補的，不進 ID 雜湊；不這樣做，工坊技能的 ID 會跟以前不一樣。
- 呼叫點：`check_draft`（工坊檢查）、`/api/workshop/export`、`api/workshop.custom_skill_defs`（戰鬥請求帶的自訂技能）、`proposal/convert._skill_data`（LLM 提議；ID 照補值前算）。內容檔的 `TrapSpec.rounds` 照舊必填。
- LLM 提議：陷阱骨架在 `CLOSED_SKELETONS`，提議模型目前做不出陷阱，所以這一處是預防；補值放在驗證前，之後開了也同樣結果。
- 測試：`tests/skillgen/test_trap_rounds_input_hc5b.py`、`tests/api/test_trap_rounds_api_hc5b.py`（沒寫輪數＝寫 2，檢查與匯出的回應完全相同）。
- **和 HC-5a 之前比對**（scratch `trap_dump.py`；內容庫 3 個陷阱技，去掉輪數後跑 `check_draft` 與 `custom_skill_defs`）：基準 `5188031d0` 與交件的 JSON **逐位元組相同**；`16126a539`（HC-5a 後）3 個都報錯，就是這次修的。

## 5. 第 4 項：伴生被動加快取
`random_composer._compose_passive_recipe` 在 `is_companion(recipe)` 時用 `library_memo(lib, "composer.companion.ratio")` 傳給 `_tune_drafts`，做法同 QF-4b 的護主。測試 `tests/skillgen/test_companion_memo_hc5b.py`：40 個種子，空快取、快取命中、新內容庫三次結果逐位元組相同。

## 6. 第 5 項：新開的工坊欄位

| 表 | 分組 | 欄位 |
|---|---|---|
| `skill_composer` | 組合器的特殊效果 | `structure.gamble_backlash_chance_permille`、`second_element_multiplier_permille`、`delayed_damage_rounds.min/max`、`delayed_damage_radius.min/max`、`sacrifice.radius.min/max` |
| | 修正技能與傳說 | `special.condition_permille` |
| | 組合器的配方 | `recipes.param_permille`、`high_ground_permille`、`exploit_surface_permille`、`condition.point_blank_min_reach`、`llm_cost.default_ap`、`llm_topic.max_keywords` |
| `skill_evolution` | 進化的強度與代價 | `low_multiplier_floor`、`low_multiplier_step`、`first_knob_weight`、`extra_cooldown_steps`、`min_cooldown`、`max_cooldown` |
| `pick` | （表沒有分組） | `pool.max_off_route` |
| `budget`（第 1 項） | 特殊效果的算法／修正技能／階級與升階 | `shield_duration_start`、`modifier.shape_to_reference_size`、`retier_growth.weak_floor_exempt_min_tier`、`rock_multiplier_permille`、`summon_hp_steps[*]`（8 列）、`cost_scales_permille[*]`（3 列） |

- 每格有中文名稱、說明寫了調高與調低；有上下限的寫「只能 a～b」或「不能超過 X」。現值都在建議範圍內（測試檢查）。
- 新測試 `tests/api/tuning/test_workshop_open_hc5b.py`；`test_triggers_composer_sk5.py` 的「組合器表剛好這些欄位」接上新欄位。
- **沒開的**：`search` 全部、`special.ladders` 與其他候選清單（值階梯，同 HC-4b3 不開階梯）、`gamble_*_permille` 清單、`llm_topic` 的其他 3 格（提議 schema 的形狀）、`variant.range_delta`（表單範圍）、`pool.slot_keyword_tries`／`wish_seed_permille`／`wish_tag_extra`（搜尋參數）、`pool.wish_cards`（見待決 4）、`candidates.bridge_variant_cap`（搜尋參數）。
- 前端沒改，沒跑 tsc、vitest、build；沒截圖。OpenAPI 重產沒有差異。

## 7. 第 6 項：收尾
刪掉 33 條變成 0 筆的規則：`py-skillgen-*-config-number` 32 條（budget、candidates、complete、composer-dual/parts/rider/special、evolution、option-effect-rules/fill/nested/variant、options、pick-offer、proposal-models/schema-shape/budget/costs/fallback/numbers/subset/topic/topup/witness、random-composer、self-penalty、skill-pick、skill-tier、validate、whiteboard-candidates、wish-pick），加上 `py-scale-generator-costs`（第 2 項後 `composer_recipes.py` 的護主法力也沒了）。基準就是 0 筆的 11 條照舊不動。`classify.py --check` 沒歸類 0，清單用 `--md` 重產。

## 8. config todo 與歸類（`classify.py --stats`）

| | config（全 todo） | scale | const | text | guard |
|---|---:|---:|---:|---:|---:|
| 後端 基準 `16126a539` | 299 | 22 | 8952 | 193 | 451 |
| 後端 交件 | **164** | 18 | 8984 | 193 | 450 |
| 前端（沒改） | 22 | 0 | 5441 | 98 | 0 |

- `skillgen/` 的 config：135 → **0**（搬進 content 124、判 const 6、第 2 項 5）。剩下的 164 筆在 `api` 62、`world` 42、`llm` 37、`engine` 17、`server` 4、`narrative` 1、`roguelite` 1（HC-6、HC-7 的範圍）。
- scale 少 4：`composer_recipes` 護主代價的法力（現在讀轉型模板）。

## 9. 不變比對（基準 `git archive 16126a539 src content config scripts`）
腳本在 scratch，沿用 QF-4b 的 `budget434.py`、`compare78.py`、`flash_dump.py`／`flash_cmp.py`、`pick_dump.py`、`topup_dump.py`、`census_cmp.py`。基準用 archive 的 `src/`、`content/`、`scripts/`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`，並確認載入的 `trpg` 路徑）。第 1 項後（new1）與第 4 項後（new2）各跑一次。

| 比對 | 第 1 項後 | 第 4 項後 |
|---|---|---|
| 逐招預算 434 招 | 檔案逐位元組相同 | 同左 |
| 閃現出題（含兩種用法統計） | 規則、計價、加成、大變化、退回相同；完整技能 `same=406 different=0`；出題 `items=522 rows=3966 same=522 different=0`；閃現表 dump 0 差異 | 同左 |
| 組合器 `recipe_census.py --seeds 4 --tiers 1,3 --rarities common,epic` | `cells=204 same=204 different=0` | 同左 |
| `wish_coverage.py run --seeds 3 --tiers 1,2` | `buckets=384 same=384 different=0` | 同左 |
| 挑選模式三選一 48 格（4 build × 種子 0、1 × 白板／完整） | JSON 逐位元組相同 | 同左 |
| 升級補足（256 題＋KEYWORD_CASES） | JSON 逐位元組相同 | 同左 |
| 78 場戰鬥（去掉 `ruleset_hash` 與內嵌規則包） | | `battles=78 events=26206 different=0`；內嵌規則包 0 差異 |

- 預測會變的地方：內容庫的 `model_dump` 只多了新格（值是原本的常數）；閃現表、戰鬥內嵌規則包不含這幾個檔，所以預測 78 場、`ruleset_hash`、parity 夾具、CLI 快照都不變，沒有重產。
- `wish_coverage.py` 本身改了一行（讀 `pool.slot_keyword_tries`），基準用 archive 裡的舊版。

## 10. 檢查（最後一個程式 commit `493410f2a`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1781 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| `classify.py --check` | 0（沒歸類 0） |
| 相關測試（第 1 項：`tests/skillgen tests/llm tests/roguelite tests/api/tuning` 等，-n 8） | 0（5785 passed；預算表 2 個失敗在同一個 commit 裡開欄位後修好，再跑 53 passed） |
| 第 2～5 項的相關測試 | 都是 0 |
| 78 場戰鬥比對 | different=0 |
| `scripts/check.py` | check.py 由 PM 在 main 跑（PM 指示：main 已有別的 commit，這裡的通過戳記用不上） |
| `-m slow tests/skillgen/test_refactor_parity.py tests/cli` | 由 PM 合併後在 main 跑 |

- 沒有新增 `# noqa`（`trap_dump.py` 等 scratch 腳本不進 repo）。

## 11. 待 PM 決定（都照最保守的做了）
1. **新開 `search` 區塊**：組合器、升階、進化、完整技能、工坊探測與 LLM 提議的搜尋參數集中在 `skill_composer.yaml` 的 `search`（照 HC-5a `rules.search` 前例，工坊不開）。`complete_max_steps` 是完整技能（閃現）的步數上限，也放這裡而不是 `flash_templates.yaml` 的 `complete`；要搬過去告訴我。
2. **進化常數放 `skill_evolution.yaml`**（不是規格列的三個檔）：進化本來就有自己的檔與工坊表。
3. **改讀既有規則的 9 類**（2.6）：同值，但語意綁到別的格（例：工坊改了 `every_n_hits`，組合器抽 N 與表單範圍跟著變；改了 `max_variant_replacements`，送給 LLM 的變奏 schema 跟著變）。
4. **`pool.wish_cards` 沒開進工坊**：許願的畫面與 LLM 提示詞多處寫「3 張」，改了數字文案不會跟著變（HC-6 的 text 範圍）。
5. **判成 const 的 6 筆**（2.7）：等級代碼與 `up_to_two`。要改回 config 告訴我。
6. **`exploit_surface_permille` 另開一格**：原本「關鍵字被利用時」的狀態／表面二選一也用 `_PARAM_PERMILLE`（500），但意思不同（是否指定 vs 指定哪一種），分成兩格；值都是 500。
7. **`ProposalRequest` 的關鍵字個數改到 `select_subset` 檢查**：建構時不再擋 3 個關鍵字，第一次 `select_subset` 才丟同樣的 `ValueError`。
8. **`wish_candidates` 的 schema 下限 3 改成「不能小於 `wish_cards`」**（載入檢查）；**`hp_per_permille` 是 0 時回傳 `hp_cap`**（原本寫死 200，現值同；內容檔是 1，走不到）。
9. **預算表的升階檔（`summon_hp_steps[*]`、`cost_scales_permille[*]`）開了**：既有測試要求預算檔每個整數都開或列為結構；這兩個是搜尋用的階梯，要改列成「結構」不開的話告訴我。
10. **範圍外的小改動**：`option_fill` 死碼改 `assert`；`to_skill_def` 等 4 個函式的 `library` 改必填；`flash_major._power_tries` 搬到 `beside_power.py`；`scripts/wish_coverage.py`、`budget_knob_audit.py`、`bal12b_measure.py`、`pick_compare.py`、`archive/composer_rejects.py` 跟著拿掉的常數改。輸出不變。

## 12. 平衡疑慮（無）
沒有。只換數字放的地方；所有比對 different=0。

## 開發 PM 裁定（2026-11-21）

已用 `--no-ff` 合併進 main（60cc26891），PM 在 main 上跑 `uv run python scripts/check.py`：結束碼 0。slow 的 parity 與 `tests/cli` 也通過（979 passed），parity 和 CLI 快照都不必重產，和預測一致。已推上 GitHub。同一次推送也帶上 PM 修的 `test_trap_traces_rg2`（半徑 0＝看不到，b8ffbd6e2）。

待 PM 決定的 10 件，都照做：
1. `search` 區塊不開進工坊，比照 HC-5a 的 `rules.search`。
2. 進化常數放 `skill_evolution.yaml`。
3. 9 類改讀既有規則：值相同，以後那幾格一改，這裡會跟著變；這是有意的。
4. `wish_cards` 不開進工坊：畫面和提示詞寫死「3 張」，要開得先改那兩處，交給 HC-6 文字段一起處理。
5. 6 筆判成 const：等級代碼和 `up_to_two` 是結構，照做。
6. `exploit_surface_permille` 另開一格：照做。
7. 關鍵字個數改在 `select_subset` 檢查：照做。
8. `wish_candidates` 改成載入時檢查；`hp_per_permille` 為 0 時回傳 `hp_cap`：照做，現有內容裡沒有 0。
9. 升階的兩組檔數開進工坊：照做，這是既有測試要求每個整數都要開。
10. 範圍外的小改動：接受。
