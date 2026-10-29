# Phase 3W-1 完成報告：白板與靈光一閃——資料與規則核心

> 實作者：implementer（opus）。規格：`docs/phases/Phase3W計畫.md` 第 1 節 3W-1 列、第 0 節盤點、第 2 節（3W-1 範圍）、第 3 節開工補充；PM 補充 #70（出題價格與類別、轉型保底）、#71（溶掉技能：記錄花掉的點數）。設計：`docs/design/06-技能.md` 6.34（含 #70、#71 更新）、6.28、6.6。
> 分支：`worktree-agent-a49c107fba249a694`（已 fast-forward 到 main `7666fb3b`），未 push。
> 範圍：只交付純函式＋資料＋測試；**沒有**接一輪流程、前端、存檔版本，舊的技能點／等級／進化原樣保留並存。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `a90fed18` | `content/flash_templates.yaml`＋schema `trpg.content.flash_templates`、內容庫載入與跨檔案檢查、`SkillDef.budget_bonus_permille`＋預算器、閃現狀態 `trpg.skillgen.flash_state`、狀態表格測試 |
| `c56f8d9a` | 規則核心 `trpg.skillgen.flash`（套用變化、推出技能、出題介面、預設候選來源、選擇）、`evolution.py` 公開入口、核心測試 |
| （本報告） | `docs/phases/Phase3W-1報告.md` |

## 2. 驗收（3W-1 範圍）

| 項目 | 結果 | 證據（`tests/skillgen/`） |
|---|---|---|
| 資料 schema（小變化、大變化沿用進化模板、轉型）＋設定（#70 價格、類別） | 通過 | `test_flash.py::test_content_matches_decisions_69_and_70`、`test_schema_rejects_bad_tables`（5 種錯誤）、`test_library_checks_major_templates_against_the_evolution_table` |
| 閃現狀態（每招次數、變化歷程、先上場用過） | 通過 | `test_flash_state.py`：`test_flash_needs_use_and_stops_at_five`、`test_counts_as_used_by_skill_kind`（主動放出即算；被動／反應／姿態／修正打完一場；8 列）、`test_after_battle_never_clears_a_recorded_use`、`test_flash_appends_and_resets_use_reflash_replaces_and_keeps_count` |
| 預算上限 +40‰／次（完整技能 +120‰） | 通過 | `test_each_flash_raises_the_budget_cap_by_forty_permille`（0～5 次）、`test_a_complete_skill_counts_as_three_flashes_with_120_permille`、`test_flash.py::test_budget_bonus_scales_the_usable_budget`（0／40／120／200：total 不變、可用預算 ×(1000＋b)/1000） |
| 套用變化 → 新 `SkillDef`、預算器依新上限重調、仍受 6.6 與驗證器約束 | 通過 | `test_range_plus_adds_one_range_and_retunes_within_the_raised_cap`、`test_area_plus_grows_size_or_radius`（比例在窗內、total ≤ 基礎可用預算 ×(1000＋40n)/1000、`validate_skill` 零違規、階級／種類／AP 不變）、`test_templates_that_do_not_fit_return_none`、`test_five_flashes_raise_the_cap_step_by_step_and_derive_matches_the_pick` |
| 重閃不加次數、不需上場；第 3 次重閃出大變化 | 通過 | `test_reflash_replaces_one_slot_and_reapplies_the_later_ones`、`test_the_third_flash_or_reflashing_it_is_major` |
| 完整技能：不能再閃、只重閃調整欄位 | 通過 | `test_complete_skill_reflashes_its_adjustment_slot_only` |
| #70 出題：不指定 1 點 4 個混合（≥2 類）、指定 2 點 3 個、轉型保底 | 通過 | `test_open_major_offer_mixes_deepen_and_bridge`、`test_open_minor_offer_covers_two_categories_when_it_can`、`test_focused_offer_costs_two_and_stays_in_its_category`、`test_transform_is_guaranteed_on_the_major_flash`（不指定佔 4 個之一、指定另列第 4 個、重閃第 3 次也有、小變化沒有）、`test_categories_follow_skill_kind`、`test_pricing_follows_decision_70` |
| #71 花掉的點數與溶掉退回（一半、無條件捨去） | 通過 | `test_dissolve_refunds_half_rounded_down`（7 列）、`test_dissolve_example_from_decision_71`（3 次其中 1 次指定＋重閃 1 次＝5 點退 2；完整技能只算重閃） |
| 確定性：同種子同選項、存檔往返 | 通過 | `test_offers_are_deterministic_and_round_trip`、`test_state_round_trips_through_json`、`derive_skill(...) == 選到的技能`（多個測試） |
| 行為一致（實戰） | 通過（3W-1 部分） | `test_a_flashed_skill_plays_in_the_engine_as_its_card_says`：閃現後的火焰箭（射程 6）進規則包、技能卡可建、6 格外的敵人是合法目標（原技能不是）、結算傷害落在預覽範圍內 |
| 舊系統不受影響 | 通過 | 手寫技能都沒有加成（`test_handwritten_skills_have_no_bonus`）；CLI 快照（`test_output_snapshots.py`，含 `skills show` 與 7 場戰鬥雜湊）**沒有**重產、全部通過 |

跑過的檢查：`ruff check .`、`ruff format --check .`、`mypy`（803 檔）、`lint-imports`（7 kept）；pytest（`-m "(slow or not slow) and not llm"`）：`tests/skillgen/test_flash*.py`（62）、`test_budget.py`、`test_evolution.py`、`test_validate.py`、`test_summon_evolution.py`、`tests/content`、`tests/test_architecture.py`、`tests/test_primitive_coverage.py`、`tests/roguelite/test_evolution.py`、`tests/engine/test_skill_determinism.py`（重播）、`tests/cli/test_budget_cli.py`＋`test_output_snapshots.py`（`--timeout=3000`）全部通過。依指示沒有跑完整 `scripts/check.py`。

第 2 節中屬於後段的項目（每類模板實際跑引擎、「先上場用過」接一輪、第 3 次一定有加深與橋接的保證、轉型欄位卸下、舊存檔轉換）由 3W-2／3W-3／3W-5 做；本段提供了它們要用的函式與測試樣板。

## 3. 資料結構

### 3.1 `content/flash_templates.yaml`（`trpg.content.flash_templates.FlashTable`，掛在 `ContentLibrary.flash`；不嵌入規則包）

| 區段 | 內容 |
|---|---|
| `rules` | `max_flashes: 5`、`major_flash: 3`、`budget_step_permille: 40`、`needs_use: true`、`reflash_needs_use: false`、`dissolve_refund_permille: 500`、`insight_per_win: 1`（3W-5 接）、`complete: {flashes: 3, budget_permille: 120, can_flash: false, can_reflash: true}` |
| `pricing` | `open: {cost: 1, options: 4, min_categories: 2}`、`focused: {cost: 2, options: 3}`、`reflash_same_price: true`、`allow_focus: true`、`transform_guaranteed: true` |
| `categories` | 小變化：`area` 範圍、`combo` 連段、`element` 元素與關鍵字、`cost` 費用（只限主動）、`extend` 延長與收割、`support` 輔助（`support_only`）、`trigger` 觸發（被動／反應）；大變化：`deepen` 加深、`bridge` 橋接。每類有 `kinds`（可用的技能種類） |
| `minor` | 小變化模板（`id`、`category`、`op`、`kinds`、`prefix_zh`、`summary_zh`、`delta`、`shapes`）。目前只有 `area_plus`、`range_plus` |
| `major` | 大變化：`{id, category: deepen|bridge, evolution: <skill_evolution.yaml 的模板 ID>}`，8 個（沿用 3-26b 的全部進化模板） |
| `transforms` | 轉型：`{id, to: passive|reaction, trigger|reaction, scale_permille, prefix_zh, summary_zh}`；先放 6.34.5 的兩個例子，3W-3 實作 |

載入時檢查：類別／模板 ID 不重複、小變化模板的類別是小變化類別（大變化同理）、`major_flash ≤ max_flashes`、大變化引用的進化模板存在且分支＝類別、轉型的觸發時機存在（`library._load_flash`）。

### 3.2 預算上限加成

- `SkillDef.budget_bonus_permille: int | None`（1～1000；省略＝沒有）。`BudgetReport.bonus_permille`，`usable` 再 ×（1000＋它）÷ 1000，所以驗證器的 70～100% 窗與組合器調整器的 75～95% 目標都自動以「提高後的上限」為基準。不影響結算（引擎不讀它）。
- CLI `trpg skills budget` 在有加成時多印「× (1000 + 閃現 N‰) ÷ 1000」。
- 規則包序列化每招多一個 `budget_bonus_permille: null` 鍵 → `hash_ruleset` 改變（照 `戰鬥紀錄格式變更.md` 1.2：有預設值的欄位不升 `LOG_FORMAT`，舊紀錄會因雜湊不符被拒）；CLI 文字輸出不變。

### 3.3 閃現狀態（`trpg.skillgen.flash_state`，pydantic、frozen、可存檔）

- `Variation`：`source`（`minor`／`major`／`transform`）、`template`、`category`、`keyword`、`shape`、`element`；`key()` 是穩定字串。**這就是 LLM 變化提議（3W-7）要輸出的結構**。
- `FlashRecord`：`nth`（第幾次；完整技能調整欄為 0）、`variation`、`reflashes`（該欄重閃次數）。
- `SkillFlash`：`base_id`（原本的技能 ID，存放的鍵）、`records`、`used`、`complete`、`adjustment`、`spent`（#71：實際花掉的靈感點）。
- 函式：`acquire`、`flash_count`、`bonus_permille`、`next_nth`、`slot_is_major`、`flash_problem`、`reflash_problem`、`price`、`seed_tag`、`counts_as_used`、`after_battle`、`with_flash(…, cost=)`、`with_reflash(…, cost=)`、`dissolve_refund`。

## 4. 介面（`trpg.skillgen.flash`）

- `apply_variation(library, skill, variation, *, bonus, rng) -> SkillDef | None`：模板 → 草稿 → 設預算加成 → 重調（小變化／轉型：`evolution.retune`，不折抵；大變化：`evolution.finish_draft`，同 3-26b 的骨架與冷卻折抵）→ `validate_skill`。橋接要真的帶該關鍵字。
- `derive_skill(library, base, state, seed) -> SkillDef`：從原技能依歷程逐筆套用（第 i 次 +40i‰，亂數 `Rng(seed).fork("flash/<原技能>/<i>/<該欄重閃次數>").fork(variation.key())`）；ID `<原 ID>_fl_<歷程 SHA-256 前 10 碼>`、名稱有大變化／轉型時「{前綴}・{原名}」、`provenance: level_up, parents: [原 ID]`。套不上時 `FlashError`。
- `FLASH_OPS`（小變化 `op` → 草稿函式；目前 `area`、`range`）、`TRANSFORM_OPS`（轉型模板 ID → 草稿函式；空）、`unimplemented_ops(table)`。
- **出題（可替換）**：
  - `FlashRequest(base, state, usage, seed, slot=None, category=None, held_keywords={})`：`slot=None` 閃現、否則重閃第 slot 次；`category` 是「指定類別（可省略）」。
  - `FlashOptionSource`（Protocol）：`ranked(library, request, category, skill) -> Sequence[Variation]`（該類排好序的候選）、`transforms(library, request, skill)`。預設 `DataOrderSource`（資料順序，測試用）。
  - `make_offer(library, request, source=None) -> FlashOffer`：依 `pricing` 與類別組題（見下）；每個候選真的套一次，只留合格的；`FlashOffer`（`base_id`、`nth`、`slot`、`reflashes`、`category`、`major`、`cost`、`options: FlashOption(variation, skill, summary_zh)`）可直接存進一輪。
  - `choose(state, offer, index) -> (新狀態, 技能)`：直接取題目裡算好的技能（不重抽、不重算），`spent += offer.cost`；題目過期（次數或該欄重閃次數已變）或不屬於這招時拒絕。
- 組題規則：不指定時類別順序由 `Rng(seed).fork(seed_tag(..., category))` 洗牌、每輪每類取一個合格變化湊滿 4 個（做得到時自然 ≥ 2 類）；指定時從該類依 `ranked` 取 3 個；大變化有合法轉型時，不指定佔 4 個之一（位置由種子決定），指定時接在後面當第 4 個。指定了這一次不可用的類別丟 `ValueError`。
- `allowed_categories(table, skill, major=)`、`is_support_skill(skill)`（保守判定：沒有傷害、而且有治療／護盾或作用於友方的效果）、`with_budget_bonus`。

## 5. 給 3W-2～3W-7 的接點

- **3W-2（小變化）**：在 `flash_templates.yaml` 的 `minor` 加模板（每類），在 `FLASH_OPS` 登錄 `op`（簽名 `(skill, template, variation, library) -> list[草稿]`，草稿是 `(技能欄位 dict, 效果 dict 列表)`，強度不用管）；`test_every_minor_op_in_the_data_is_implemented` 會擋漏登錄。需要新參數時加到 `FlashTemplate`（schema）與 `Variation`（`keyword`／`shape`／`element` 已有）。「類別內依用法統計排序」寫一個新的 `FlashOptionSource`（取代 `DataOrderSource`），`FlashRequest.usage` 已帶統計。費用類（蓄力／輕巧）改 `cost`／`ap_cost` 即可，預算器會依新的 AP 係數與代價折抵重調。
- **3W-3（大變化、轉型）**：大變化已可用（沿用 8 個進化模板）；「至少各 1 加深與橋接」目前靠輪流取兩類自然滿足，要保證可在來源或 `_mixed` 加檢查。轉型在 `TRANSFORM_OPS` 登錄（模板 ID → 草稿；草稿要把 `kind` 改成 `passive`／`reaction` 並填 `trigger`／`reaction`、`ap_cost: null`），預算器會照被動／反應的係數重算；保底規則已做好且有測試（測試用假轉型）。欄位卸下是 3W-5。
- **3W-4（白板產生）**：產生完整技能時用 `with_budget_bonus(skill, rules.complete.budget_permille)` 再調強度，取得後 `acquire(id, complete=True)`。
- **3W-5（一輪）**：`RunState` 存 `dict[原技能 ID, SkillFlash]` 與待選的 `FlashOffer`；戰鬥後 `after_battle(state, kind, casts=…, finished_equipped=…)`；閃現前 `flash_problem`＋點數 ≥ `price(...).cost`，重閃前 `reflash_problem`；選完把 `choose` 回傳的技能放進 `generated_skills` 並換掉裝備中的舊 ID（ID 每次都不同，`with_skills` 不會撞）；讀存檔時可用 `derive_skill` 重算驗證。溶掉：`dissolve_refund(rules, state)` 退點、移除技能與狀態。靈感點每贏一場 `rules.insight_per_win`。
- **3W-6（前端）**：題目的 `cost`、`major`、`category`、每個選項的 `summary_zh` 與完整 `SkillDef`（可直接做技能卡比較）；溶掉確認顯示 `dissolve_refund`。
- **3W-7（LLM）**：LLM 輸出一個 `Variation`（pydantic），用 `apply_variation` 驗證並由預算器補數值；不合格時退回 `FlashOptionSource` 的模板候選。可寫成一個包裝 `DataOrderSource` 的來源，把 LLM 的變化排在最前面。
- **3W-8（模擬）**：`bonus_permille`、`skill_budget(...).ratio`、`Variation.template` 即可統計。

## 6. 新增的複雜度 noqa

無（`src` 沒有新增任何 `noqa`）。測試檔有 2 個 `PLC0415`（函式內匯入私有的 `_load_flash`），不是複雜度類。

## 7. 待 PM 決定

1. **重調可能讓數值變低**：每次套用都把旋鈕歸零、再隨機調到組合器窗內（75～95% 的提高後上限），所以閃現後的骰子不保證比閃現前大（只保證上限變高）。要不要加「重調下限＝閃現前的點數」？（3W-2 可做，需改 `composer_tuning.tune` 的目標區間。）
2. **加成怎麼乘**：+40‰ 乘在整個可用預算上（含 AP 係數與代價折抵之後），驗證窗的下限 70% 也跟著提高。「佔同階預算」照字面是「階級預算的 4%」，兩者只在有代價折抵時有差。
3. **名稱只在大變化／轉型時改**（取最後一個的前綴）；小變化沿用原名。
4. **完整技能的重閃**：設計是「換掉其中一個附帶效果或形狀」，目前做成一個「調整欄」（第 0 次）：每次重閃把一個小變化套在原本的完整技能上，再重閃就換掉它（不累積）。真正「拿掉某個附帶效果再換」要等完整技能的結構定下來（3W-4／3W-5）。
5. **重閃時後面的變化會重新套用**：重閃第 k 次後，第 k+1 次以後的變化在新技能上重套；有任何一筆套不上，那個重閃選項就不出現。
6. **輔助技的判定**（`is_support_skill`）是保守版：沒有傷害、且有治療／護盾或對友方的效果。
7. **姿態、修正型可以出的類別**：姿態只列在加深／橋接，修正型沒有任何類別（6.34.4 沒寫到）；`categories.kinds` 可直接改。
8. **規則包雜湊改變**：`SkillDef` 多一個欄位，`hash_ruleset` 改變，舊的戰鬥紀錄與戰鬥中存檔照 1.2 的策略被拒；未升 `LOG_FORMAT`、存檔版本未動（3W-5 遞增）。
9. **`insight_per_win` 暫放在 `flash_templates.yaml`**：它是 roguelite 參數，3W-5 可移到 `roguelite.yaml`。
10. **3W-4 合併衝突提醒**：本段改了 `content/library.py`（新欄位 `flash`、`_load_flash`）、`skillgen/evolution.py`（檔尾新增公開入口）；3W-4 若也動 `library.py` 的 `ContentLibrary` 欄位或載入段，合併時兩邊都保留即可。
