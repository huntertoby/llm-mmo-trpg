# Phase 3W-R2 報告｜旋鈕統一、內容即資料、拆檔

依據：`docs/phases/Phase3W計畫.md` 第 6 節（3W 大段審查 ③④⑤⑥⑦⑧與開發 PM 決定）。實作者：opus。**不改遊戲規則與數值行為**；存檔結構與戰鬥紀錄結構都沒有改（`trpg-run/13`、`LOG_FORMAT` 不遞增）。

## 1. Commit

| commit | 內容 |
|---|---|
| `f6e25df2` | 重構前的行為快照（對照測試＋夾具） |
| `e03e631a` | ③ `skillgen/knobs.py`：完整技能與升階重配共用旋鈕 |
| `7a45fe2d` | ④ 規則常數移到資料（白板、升階重配、輔助技；`MAX_EFFECTS`、`MAX_AP_COST`） |
| `98e8ede8` | ⑤ 模擬報表改用觀察者，不再在執行期替換 `offers.as_complete` |
| `c246ad6c` | ⑥ 後端下發可重閃的欄、傳承規則；前端只讀 |
| `6cfaba5d` | ⑧ 召喚類補充大變化只做自己那一支（`summon_evolution_options(only=…)`） |
| `f29bdc3f` | ⑦ `flash.py` 拆成 `flash_derive`／`flash_offer`／`flash_category`（只搬檔） |
| （本報告） | 報告 |

## 2. 做了什麼

### ③ 預算旋鈕統一
- 新模組 `skillgen/knobs.py`：`strength_knobs`（預算器的骰子／倍率／推拉＋修正幅度與接續段，`index` 指向 `knob_targets`）、`has_strength_knobs`、`param_knobs`（原 `skill_tier._param_knobs`）、`knob_targets`、`next_moves`／`KnobMove`、`knob_order`（原 `complete._targets`／`_moves`／`_Move`／`_order`）。
- `complete.py` 的 `_strength_knobs` 只多加召喚與姿態的旋鈕；`_param_knobs` 直接用 `knobs.param_knobs`。`skill_tier.py` 拿掉 `_param_knobs`、`param_knobs` 包裝、`_has_strength_knobs`、`_PUSH_PULL`、`_TUNED_FIELDS`，改用 `knobs`。
- **`_climb` 沒有併進 `retune`**：`retune` 是依目標比例（或抽 75～95%）的亂數調整、可往下調；`_climb` 是確定性、只加不減的逐格爬升，改成 `retune` 的一種模式會改變每一招的結果。保留 `_climb`，只共用旋鈕蒐集（寫在 `complete.py` 模組說明）。

### ④ 內容即資料
- `skill_composer.yaml` 的 `whiteboard`（`WhiteboardRules`）：`simple_shapes`、`self_move_effects`、`displace_effects`、`terrain_effects`。`whiteboard_check.py` 拿掉 `SELF_MOVES`／`DISPLACE`／`_SIMPLE_SHAPES`／`_TERRAIN`；比例窗改讀 `library.budget.min_ratio_permille`／`max_ratio_permille`（訊息字串照樣是「70%～100%」）。
- `skill_budget.yaml` 的 `retier_growth`（`RetierGrowthRules`）：`terrain_effects`、`area_effects`；`skill_tier._TERRAIN`／`_AREA` 改讀它；`_MAX_EFFECTS`／`_MAX_AP` 改用 `content.skills.constants.MAX_EFFECTS` 與新的公開 `MAX_AP_COST`（`_MAX_AP_COST` 仍指向它）。
- `flash_templates.yaml` 新增 `support`（`SupportSkillRule`：`harm_effects`／`help_effects`／`ally_effects`）；`is_support_skill(skill, table)` 改讀它（簽名多一個 `table`，呼叫處都更新）。
- `flash_ops.py` 三處 `4` → `MAX_EFFECTS`（語意是一招的效果原語上限，不是稀有度的 `max_effects`），拿掉三個 `noqa: PLR2004`。
- pydantic 預設值等於原本的常數；YAML 也明寫。新測試 `tests/content/test_rule_lists_3wr2.py`：列出的原語與形狀都存在、值與搬移前相同。

### ⑤ 模擬報表不再替換函式
- `roguelite/offers.py`：`observe_complete(observer)`（`ContextVar`，同 `llm_hook` 的做法）；`as_complete` 做出完整技能後通知觀察者 `(原本, 完整)`，不影響結果。
- `auto_play(..., on_complete=…)`：在整輪期間裝上觀察者（迴圈本體搬到 `_auto_play`，邏輯不變）。
- `sim/flash_report.py`：拿掉 `_recording_as_complete` 與 `vars(_offers)[...]` 替換；`_Collector.complete(before, after)` 用 `complete_gain_permille` 記 ‰。

### ⑥ 前端不自己推規則
- 後端（`roguelite/flashes.py`）：`reflash_slots`（照 `reflash_problem`）、`carryable_records`（逐筆照 `_carried_problem`，含 3W-R1 的「模板已不存在」）、`inherit_target_problem`、`inherit_source_problem`、`max_carry`（`inherit_problem` 與 `_carried_problem` 也改用它們，訊息不變）。
- API：`FlashRulesOut.max_carry`；`SkillFlashOut` 新增 `reflash_slots: [{slot, transform_hint}]`、`carryable: [nth]`、`inherit_problem_zh`、`inherit_target`。
- 前端 `client/src/run/flash.ts`：`reflashSlots(f)`、`inheritTargets`、`carryable`、`maxCarry`、新的 `inheritProblem` 都只讀後端欄位；`CampfireSkillCare.tsx` 的「不能傳承」原因改用後端字串。`reflashSlots` 少了 `rules` 參數。
- `export_openapi.py` → `gen:api` 重產；`export_client_fixtures.py` 重匯出（無差異）。`client/src/run/fixtures/run_*.json`（原本是 API 實際回應存的）用後端同一組函式補上新欄位，其餘內容逐字不變（腳本比對過）。

### ⑧ `flash_major` 一對一對照表
- `_apply_summon` 直接用 `template.op`（`summon_deepen`／`summon_count`／`summon_bridge` 本來就是召喚分歧進化的模板 ID），呼叫 `summon_evolution_options(..., only=template.op)` 只做那一支。未知的 `op` 由原本的 `KeyError` 變成「做不出來」（`None`）。新測試：`only` 的結果 == 全部做完再篩。

### ⑦ 拆檔（只搬檔）
- `skillgen/flash.py`（1220 行）刪除，拆成：
  - `flash_derive.py`：錯誤型別、`apply_variation`、`derive_chain`、`derive_skill`、`flashed_identity`、`history_error`、`at_tier`／`at_role_tier`、`power_floor`、`with_budget_bonus`、`variation_rng`、`unimplemented_ops`、`TRANSFORM_OPS`；
  - `flash_offer.py`：`FlashRequest`、選項來源（`DataOrderSource`、`UsageSource`、`ProposingSource`）、`FlashOption`／`FlashOffer`、`_Builder`、`make_offer`、`choose`、`skill_before`、`history_problem`、`category_counts`／`category_ranking`；
  - `flash_category.py`：`is_support_skill`、`template_kinds`、`allowed_categories`。
- 跨模組用到的私有名稱改成公開（只改名）：`_kinds` → `template_kinds`、`_records` → `history_records`、`_evolution_template` → 沿用既有的 `evolution.evolution_template`（同一行程式）。`_derive_on_current(request, …)` → `derive_on_current(base, current, state, variation, *, seed, tier)`（只把 `request` 的欄位攤開，避免 derive 依賴 offer）。
- 沒有保留相容再匯出；所有 import（src、tests）與文件參照都改到新模組。import-linter 7 條合約照常。

## 3. 行為不變的證據

- **對照測試** `tests/skillgen/test_refactor_3wr2.py`（slow，732 項）＋夾具 `tests/skillgen/fixtures/refactor_3wr2.json`，在重構 **之前**（`f6e25df2`）產生：
  - 所有 301 個內建技能的 `complete_strength` 結果（SHA-256）；
  - 所有內建技能 `retier` 1→2→3（例外型別也記）；
  - 閃現出題：ID 排序等距約 40 招 ×（種子 3／階級 1、種子 11／階級 1、種子 5／階級 2），連續出題並選擇 3 次（含第 3 次大變化）的 `FlashOffer` JSON。
  - 每一個 commit 之後都跑過，全部相同。重產：`uv run python -m tests.skillgen.test_refactor_3wr2`。
- ⑤ 模擬報表小規模對照：`run_flash_sim(["none", "all"], 種子 1～3)` 的 `RunMetrics` repr ＋ `format_flash_report` 輸出，重構前後逐位元組相同（`complete_gains` 例：(137, 142)、(121, 120)、(184, 2)）。
- ⑥ 前端夾具：拿掉新欄位後與原檔逐字相同；vitest 舊的重閃／傳承斷言照舊通過（改為讀後端資料）。

## 4. 驗收

- `ruff check`、`ruff format --check`（1197 檔）、`mypy`（840 檔）、`lint-imports`（7 kept）全過；沒有新增 `noqa`（反而拿掉 `flash_ops.py` 的三個）。
- pytest（`-m "(slow or not slow) and not llm"`，`-n 8`）：`tests/skillgen`＋`tests/roguelite` 3860 passed／14 skipped；`tests/api`＋`tests/sim`＋`tests/content`＋`tests/llm`＋`tests/test_architecture.py` 2138 passed；`tests/cli`（`--timeout=3000`）156 passed。
- 前端：`gen:api` 重產；vitest 120 檔 1175 passed；`build`（含 `tsc --noEmit`）通過。
- 新測試：`test_refactor_3wr2.py`（732）、`tests/content/test_rule_lists_3wr2.py`（2）、`test_offers.py::test_observe_complete_notifies_and_restores`、`test_flash_api.py::test_the_backend_sends_reflash_slots_and_inherit_rules`、`test_summon_evolution.py::test_only_builds_just_that_branch`、`flash.test.ts` 新增後端資料驅動的傳承／重閃斷言。
- 未跑 `scripts/check.py` 與大型模擬；沒有開瀏覽器預覽（畫面只換資料來源，字串相同）。

## 5. 檔案行數（前 → 後）

| 檔案 | 前 | 後 |
|---|---|---|
| `src/trpg/skillgen/flash.py` | 1220 | — |
| `src/trpg/skillgen/flash_derive.py` | — | 491 |
| `src/trpg/skillgen/flash_offer.py` | — | 759 |
| `src/trpg/skillgen/flash_category.py` | — | 44 |
| `src/trpg/skillgen/knobs.py` | — | 120 |
| `src/trpg/skillgen/complete.py` | 274 | 227 |
| `src/trpg/skillgen/skill_tier.py` | 556 | 519 |
| `src/trpg/skillgen/whiteboard_check.py` | 175 | 169 |
| `src/trpg/skillgen/flash_ops.py` | 753 | 755 |
| `src/trpg/skillgen/flash_major.py` | 743 | 739 |
| `src/trpg/skillgen/summon_evolution.py` | 220 | 224 |
| `src/trpg/sim/flash_report.py` | 526 | 511 |
| `src/trpg/roguelite/offers.py` | 306 | 332 |
| `src/trpg/roguelite/auto.py` | 244 | 261 |
| `src/trpg/roguelite/flashes.py` | 434 | 477 |
| `src/trpg/api/run_presenter.py` | 522 | 535 |
| `src/trpg/api/run_schemas.py` | 620 | 639 |
| `client/src/run/flash.ts` | 246 | 251 |
| `client/src/run/CampfireSkillCare.tsx` | 279 | 278 |

## 6. 待 PM 決定

1. **`ruleset_hash` 會變**：④ 在 `skill_composer.yaml`、`skill_budget.yaml`、`flash_templates.yaml` 加了欄位（值與原本的常數相同），內容檔的雜湊跟著變。照既有規則，**舊版本存的「戰鬥中」存檔**讀檔時會因 `ruleset_hash` 不符被拒（戰鬥之間的存檔不受影響）。這與任何內容改版相同，存檔結構本身沒改；若要讓這次例外放行，需要另外決定。
2. **`_climb` 保留**（見 ③）：併成 `retune` 的模式會改變完整技能的數值，屬規則變更，沒做。
3. **觀察者用 `ContextVar`**（⑤）：`auto_play(on_complete=…)` 在整輪期間裝上，`as_complete` 讀它；沒有把觀察者一路傳進 `apply_choice` → `progress` → `make_offer`（改動面大）。若 PM 偏好明確參數傳遞，可再排。
4. **前端可帶走的變化現在多了一條規則**（⑥）：`carryable` 逐筆照後端 `_carried_problem`，所以「模板在目前內容已不存在」的小變化（3W-R1 的內容改版情形）不會列出；原本前端只看 `source == "minor"`，會列出後送出才被拒。一般情況結果相同。
5. **重閃欄照 `reflash_problem` 過濾**（⑥）：目前資料下與原本前端相同；若之後 `reflash_needs_use: true` 或完整技能 `can_reflash: false`，沒用過的欄會直接不列出（原本前端會列出、送出才被拒）。
6. **重複的地形原語清單**：`whiteboard.terrain_effects` 與 `retier_growth.terrain_effects` 各寫一份（分屬組合器與預算兩個資料檔）；內容測試保證都指向存在的原語。若要合成一個來源（例如原語定義上加分類標籤），會動到 `skill_primitives.yaml` 的 schema，未做。
7. `flash.py` 沒有保留相容再匯出（規格說優先更新 import）；外部腳本若還匯入 `trpg.skillgen.flash` 需改成新模組。
