# Phase LB-2c 報告｜變奏欄位只在題目要求時給、`self_on_high_ground` 開放、被動 schema 固定 spell／any

> 2026-11-14。基底 main `261a45aec`。依據：玩法 PM 交接 4.1.18 第 1、2、3、5 點（不用問使用者）。
> 沒改 `config/`、`docs/design/`；沒放寬任何驗證或引擎規則；沒做平衡量測或模擬；沒動存檔。
> 原始資料：`docs/phases/LB-2c資料/`。

## 一、白話結論

- 五項都做完。全部是「送給本機模型的 schema 收窄＋prompt／回饋文字」，提議模型（驗證用的 pydantic）與驗證器都沒改，所以 Mock 與所有快照都不變（照預測）。
- **Gemma 0.7 重測一輪：一次通過 15/20、LLM 最終通過 18/20、退回 2/20**（LB-2b 兩輪：一次通過 7、6；最終 17、12；退回 3、8）。每題中位數 2.96 秒（LB-2b 4.84～5.77）。**變奏錯誤 0 條**（LB-2b 61/96），29 次嘗試沒有一次帶變奏。
- **Q12 仍退回技能池**，但卡的地方又變了：第 2 次被 `keyword.required` 擋時，回饋列的「可用寫法」是 `raise_terrain、lower_terrain`（這段回饋沒套 LB-2b 的被動過濾，也不列條件），模型第 3 次就照著改成隆起地形 → 超預算＋沒填大地。見第七節第 1 點。

## 二、五項改動

### 1. 題目沒要求變奏時 schema 不給變奏欄位（4.1.18 第 1 點）

- **「題目要求變奏」怎麼判定**：`ProposalRequest.wants_variants: bool = False`（`skillgen/proposal_subset.py`）。現有的出題資料（升級候選、許願池、`trpg llm` 評估題目、`llm_model_compare` 的 20 題）**沒有任何「要變奏」的欄位或關鍵字**，所以照最保守做法一律 `False`＝目前所有題目都不給變奏欄位。之後出題指定戰場變奏、或許願池的願望講到地形時，由呼叫端設 `True`（這次沒有接任何呼叫端）。
- `prompts/proposal.py::variant_limit(library, request, subset)`：`wants_variants` 為真且不是被動題目時＝稀有度上限，否則 0；`_models_and_schema` 用它呼叫 `shape_schema(variant_limit=…)`（0 ＝ 拿掉 `variants` 欄位，沿用 LB-2 的 `limit_variants`）。被動一律 0（驗證器：只有主動技能能帶變奏；之前被動題目的 schema 其實還有 `variants` 欄位）。
- prompt：`fields_note_zh.variants`（`VARIANTS_NOTE_ZH`）只在 `variant_limit > 0` 時出現；稀有度不能帶變奏時的「不要填 variants」（`VARIANTS_NONE_ZH`）一併拿掉（沒有欄位就不用說）。`range_delta` 照 LB-2b 開著（`wants_variants=True` 時 15 支變奏分支照舊）。
- **沒改的**：系統指令的「代價、變奏、條件都是選填；題目沒要求就不要填」與 `BUDGET_NOTE_ZH` 的「選填欄位（代價、變奏、條件）越少越好」是固定文字，沒動（改系統指令會動到 prompt 前綴快取與快照；意思也不矛盾）。提議模型照舊收 `variants`（模型不照 schema 時驗證照舊判，不放寬也不收緊；見第七節第 3 點）。

### 2. `self_on_high_ground` 開放給 LLM（4.1.18 第 2 點）

- `content/skill_conditions.yaml` 拿掉 `handwritten_only: true`，比照 KW-2 對 `self_stack_at_least` 的做法（只拿掉旗標；隨機組合器的條件清單沒加，既有種子不變）。提議子集（`legal_conditions`）、提議 schema（`_condition_union`）、工坊選項（`condition_choice` 不再標 `unavailable_zh`）、驗證器（`condition.handwritten_only` 不再擋工坊／白板來源）都是讀這個旗標，所以一次全開。閃現原本就不擋（有 `parents`）。
- 定義不改：施放者所在格高度 ≥ 1、飛行不算。「待 PM」註解改成定案說明（附 4.1.18）：yaml 註解、`content/skills/constants.py` 的條件說明、`engine/skills/conditions.py` 的行內註解（只改註解）。`harshness` 照占位 `common`。
- 效果：Q12 的 `ways` 多了「條件 self_on_high_ground」；鷹眼（`skill_eagle_eye`）在 Q12 的提議模型下轉得過去。

### 3. 被動題目 schema 固定 spell／any、`budget.over` 回饋（4.1.18 第 3 點）

- `prompts/proposal.py::fixed_category`：被動題目、子集骨架都規定同一組 `required_category`／`required_weapon_req`（`skeletons/passive.yaml`：spell／any）時回傳它；照資料推、不寫死。
- `schema_shape.py::fix_category`：頂層只留收這一類的分支（類別分支後被動只剩 `SkillProposal_spell`、`SkillProposal_on_self_spell`），`category`／`weapon_req` 改成 `const`；全部分支都不收時照原樣回傳（不讓 schema 無解）。不分支的退路也套。只改 schema，驗證器的 `passive.category` 照舊。
- prompt：被動題目的 `fields_note_zh.category` 改成 `FIXED_CATEGORY_NOTE_ZH`（「這題的骨架固定 category: spell、weapon_req: any，照填。」），不再講 weapon 的配對。
- 回饋：`advise(error, library, skill=None)` 多一個參數（規則層的錯誤才帶技能）；**被動技能**的 `budget.over` 附 `PASSIVE_BUDGET_ADVICE`：「被動的可用預算看觸發的係數：請換係數高的觸發（這個稀有度最高的是 every_n_hits（n: 3）），或換便宜的狀態」。觸發照技能稀有度能用的、用 LB-2b 的 `best_trigger` 算（不寫死）。主動技能的 `budget.over` 不加。

### 4. 拿掉 `RANGE_DELTA_ADVICE` 的 single 例子（4.1.18 第 5 點）

- 「或把技能形狀改成有數字射程的形狀（例：single 並填數字 range）」→ 去掉括號例子。

### 5. `PROMPT_VERSION` `skill-proposal/16 → /17`

- 只在 `tests/llm/test_prompts.py` 新增 `/17` 一鍵，雜湊同 /16（這次改動都在 `build_proposal_prompt`／`evaluate` 這層，快照只雜湊 `build_skill_proposal_messages` 的固定輸入）。

## 三、快照逐鍵（先預測、再跑）

| 快照 | 預測 | 結果 |
|---|---|---|
| `tests/llm/test_prompts.py` `SNAPSHOTS` | 只新增 `skill-proposal/17`，雜湊同 /16 | 一致 |
| `tests/cli/snapshots/cli_output_hashes.json` 24 鍵（`skills_list`、`skills_show_all/00`～`15`、7 場戰鬥） | 全部不變：技能列表／詳情不印 `handwritten_only`，戰鬥不碰提議與條件旗標 | 全部不變（`-m slow tests/cli` 通過） |
| `tests/cli/snapshots/llm_propose_mock.txt`（`--mock -n 3`） | 不變：Mock 用提議模型驗證，模型只多一個條件（超集）；三題（combo_point、fury、marked）的候選手寫技能沒有用到 `self_on_high_ground` | 不變 |
| `tests/skillgen/fixtures/refactor_3wr2.json`（完整強度、升階重配、閃現） | 不變：都不經過提議 schema；閃現技能有 `parents`，本來就不擋 | 不變（slow 通過） |

**沒有重產任何快照。** 另外要注意：schema 不再帶變奏、被動又只剩一類分支，所以「分支後超過 `SCHEMA_CHAR_LIMIT` 改用不分支模型」的題目變少——340 題（1～5 階 × 4 稀有度 × 無關鍵字＋16 關鍵字）裡不分支的從 140 題降到 8 題，最大 schema 從 122,110 升到 124,601 字元（仍 ≤ 125,000）。這 132 題的驗證模型從「不分支」變「依類別分支」，合格的提議兩種都收（Mock 不變就是這個原因），不合格時錯誤代碼可能從 `passive.category` 之類變成 `literal_error`。見第七節第 2 點。

## 四、改了的既有測試（逐條理由）

1. `tests/llm/test_proposal_prompt.py::test_prompt_structure`：原本斷言 schema ＝ `shape_schema(…, variant_limit=稀有度上限)`；題目沒要求變奏，改成 `variant_limit=0`（4.1.18 第 1 點）。
2. `tests/llm/test_schema_shape_lb2.py::test_prompt_schema_splits_category_and_variants`：要測變奏分支與 `maxItems`，題目加 `wants_variants=True`；common 那題也加（仍斷言沒有 `variants`，稀有度上限 0）。
3. 同檔 `test_field_notes_cover_hidden_rules`：變奏說明的斷言改用 `wants_variants=True` 的題目；common 原本斷言有「不要填 variants」，`VARIANTS_NONE_ZH` 已拿掉，改成斷言沒有 `variants` 說明。
4. `tests/llm/test_variant_range_lb2b.py`：`EPIC_COMBO` 與「說明列出有射程的形狀」那題加 `wants_variants=True`（LB-2b 測的是要求變奏時的 schema 與說明）；`_tidal` 那幾條用提議模型驗證，模型沒變，斷言不動。

都沒有放寬斷言（判定的測試一條沒改）。新測試 `tests/llm/test_proposal_lb2c.py`（12 條，全部離線）：沒要求變奏時 schema／說明都沒有、要求時 15 支分支＋說明、被動永遠沒有、模型照舊收變奏；`self_on_high_ground` 不再 `handwritten_only`、工坊可選、工坊來源不擋、Q12 的 ways 與 schema 有它、鷹眼過得了 Q12 模型；被動 schema 每支都是 const spell／any、主動仍兩類、`fix_category` 丟分支但不會清空；被動 `budget.over` 附修法、主動不附；`RANGE_DELTA_ADVICE` 沒有例子。

## 五、驗收

- `ruff check`、`ruff format --check`、`uv run mypy`（不帶參數，1630 檔，含 tests）、`lint-imports`（14 kept）通過。
- `tests/llm` 全部＋`tests/skillgen` 的 proposal／option／workshop／whiteboard／keyword／upgrade／candidates／stack 相關＋許願池與工坊 API＋`tests/test_architecture.py`＋`tests/engine/test_stack_demos_kw2.py`＋`tests/world/test_wish.py`＋`tests/roguelite/test_flash_llm_run.py`：2157 passed、14 skipped（`-n 8`）。
- 交件前一次：`pytest -m slow tests/cli tests/skillgen/test_refactor_parity.py` 972 passed；`tests/cli/test_llm_propose_cli.py` 8 passed。
- **戰鬥不變比對**（照 LB-2 第八節：改前＝main `261a45aec` 用 `git archive` 解開 src 與 content、`PYTHONPATH` 指過去；地圖 bandit_lair、bridge_chasm、cliff_outpost、dark_forest、frozen_lake、lava_crossing、oil_depot、open_plain × 種子 1、2＋頭目圖 cloud_summit、molten_heart_pit、rift_gate × 種子 3～12；地圖預設陣容、效用 AI、30 輪；比整份 `--log-json`）：
  - 整份比：46 場都不同——**每一場唯一的差別是內嵌規則包裡 `conditions[21]`（`self_on_high_ground`）的 `handwritten_only` 欄位不見了，以及因此變的 `ruleset_hash`**。
  - 拿掉內嵌規則包（`setup.ruleset`、`final_state.ruleset`、`ruleset_hash`）後比事件、動作、指令、最終狀態：`battles=46 events=19276 different=0`。也就是說差別只因條件開放（候選池的旗標），戰鬥行為完全一樣。
  - KW-2 拿掉 `self_stack_at_least` 的旗標時也是同樣情形（戰鬥 CLI 輸出不印規則包，所以 CLI 快照不動）。

## 六、Gemma 0.7 重測（一輪）

- 換模型規則照做：開始前 `GET /api/v0/models` loaded 只有 `google/gemma-4-26b-a4b-qat`，已載入所以**沒有換模型、沒有 unload／load**；量速 209.6 t/s（≥ 60）、VRAM 22.2 GB；跑完再查一次，仍只有 Gemma。沒啟動、關閉 LM Studio，沒改它的設定與 `config/llm*.toml`（模型與思考只用腳本參數）。
- 指令：`uv run python scripts/llm_model_compare.py --model google/gemma-4-26b-a4b-qat --reasoning-effort none --temperature 0.7 --label gemma_lb2c_t07_r1 --out docs/phases/LB-2c資料/gemma_lb2c_t07_r1.json`；錯誤統計 `scripts/llm_failure_stats.py` → `stats_gemma_lb2c_t07_r1.md`。

| 項目 | LB-2 基準 Gemma 0.7 | LB-2b Gemma 第 1 輪 | LB-2b Gemma 第 2 輪 | **LB-2c Gemma** |
|---|---|---|---|---|
| 一次通過 | 5/20 | 7/20 | 6/20 | **15/20** |
| LLM 最終通過 | 11/20 | 17/20 | 12/20 | **18/20** |
| 退回 | 9/20 | 3/20 | 8/20 | **2/20**（第 4 題工坊保底、第 12 題技能池） |
| 平均嘗試 | 2.25 | 2.0 | 2.15 | **1.45** |
| 每題秒數中位數 | 4.12 | 4.84 | 5.77 | **2.96** |
| 命名成功 | 11/11 | 16/17 | 12/12 | 17/18 |
| 帶變奏的嘗試 | 17/45 | 58/83（兩輪合計） | | **0/29** |
| 變奏相關錯誤 | 11/44 | 61/96（兩輪合計） | | **0/19** |

- 通過的題目：1、2、3、5、6、7、8、9、10、11、13、14、15、16、17、18、19、20。
- 29 次嘗試、19 條錯誤：`skeleton.secondary_count` 3、`budget.weak` 2、`keyword.required` 2、`skeleton.core` 2、`skeleton.core_share` 2，其餘各 1。
- 同條件兩輪的差距之前就很大（LB-2b 17 對 12），這次只有一輪，大方向可信（變奏錯誤歸零是結構性的：schema 沒有欄位），通過率的數字要保守看。
- **Q12（史詩被動＋高處）**：三次都用 `on_turn_start`＋自己統御＋護盾。第 1 次 `passive.affects`（統御 affects allies）；第 2 次改對 affects，但沒帶到高處 → `keyword.required`，回饋寫「可用寫法（high_ground：raise_terrain、lower_terrain）」；第 3 次照回饋加了隆起地形 → `exclusion.terrain_needs_earth`＋`budget.over` 142.9%（新的被動修法回饋有附上，但已是最後一次）。category／weapon_req 三次都是 spell／any（schema 固定了）。

## 七、待 PM 決定

1. **`keyword.required` 的回饋把 Q12 帶回升降地形**（重測新發現）：`skillgen/proposal_budget.py::_topup_advice` 列「可用寫法」用 `keyword_way_texts(…, primitives=models.primitive_ids)`，只列效果原語，**沒套 LB-2b 的被動過濾（`unfit_effect_rules`），也不列條件**（`height_advantage`、`self_on_high_ground`）。prompt 的 `ways` 已經改好，回饋卻反過來推模型去用一定超預算的地形。屬引導、不是規則；建議下一段讓回饋的寫法和 prompt 的 `ways` 同源（被動先列條件、拿掉放不進預算的）。這段範圍外，沒動。
2. **分支／不分支的退路變少**：schema 變小後，340 題裡用不分支模型的從 140 題降到 8 題（第三節）；最大 schema 124,601 字元，離 125,000 只剩 399。之後 schema 再長就會開始退回不分支（不會壞，只是失去類別分支）。和 LB-2 待決 4、LB-2b 待決 8 一起看。
3. **模型不照 schema 時仍可能帶變奏**：這次只收窄 schema（照 4.1.18「schema 不給變奏欄位」），驗證用的提議模型照舊收 `variants`，所以沒有約束解碼的 client（例如 LB-1 swift 那種 `guided_json` 被忽略的情況）送來的變奏仍會照一般規則判、合格就收。要不要連提議模型也在題目沒要求時拒收變奏？那會改 Mock（手寫技能帶變奏的候選會被換掉）與快照，所以這段沒做。
4. **系統指令與 `BUDGET_NOTE_ZH` 仍提到「變奏」**（「選填…題目沒要求就不要填」）：意思和新做法一致，沒改；要完全拿掉得改系統指令（動 prompt 前綴與快照）。
5. 被動 `budget.over` 回饋舉的觸發是「技能稀有度能用、係數最高」的 `every_n_hits（n: 3）`（全表算，不看這題子集）；目前被動只有 epic，子集與全表一致。
6. `wants_variants` 目前沒有任何呼叫端會設 `True`；許願池「願望講到地形」要接時再排。

## 八、commit

1. `3be7c35c9` fix(lb-2c): drop the single-range example from RANGE_DELTA_ADVICE; bump skill-proposal/17（第 4、5 項）
2. `ee7046255` feat(lb-2c): open self_on_high_ground to LLM, workshop, whiteboards and flash（第 2 項）
3. `4bb157255` feat(lb-2c): variants only when the topic asks; passive schema fixes spell/any（第 1、3 項＋測試；兩項都改 `prompts/proposal.py` 同一段，合成一個 commit）
4. `5ec029fc8` docs(lb-2c): LLM onboarding note for skill-proposal/17（上手-LLM 第五節）
5. docs(lb-2c): report and retest data（本報告、`LB-2c資料/`）

## 開發 PM 裁定（2026-11-14）

- **驗收通過，合併。** 五項都是收窄送給模型的 schema，加上改 prompt 和回饋文字，驗證器和提議模型都沒動。改了 4 處既有測試，都是跟著新做法改，沒有放寬。快照照預測全部不變，只新增 `skill-proposal/17` 一鍵。
- 戰鬥不變比對：整份 log 比 46 場都不同，原因只有內嵌規則包裡 `self_on_high_ground` 少了 `handwritten_only`，`ruleset_hash` 跟著變。拿掉規則包後比事件、動作、最終狀態，different=0。接受：這是 4.1.18 決定開放這個條件造成的，戰鬥行為沒變。
- 重測（Gemma 0.7 一輪）：一次通過 15/20、最終通過 18/20、退回 2/20，變奏錯誤 0。比 LB-2b 好，但只跑了一輪。
- 待決 1（`_topup_advice` 列「可用寫法」時沒套被動過濾，Q12 被回饋帶回升降地形）：記入佇列。範圍很小，但專案 PM 交代自由設計不再往外擴；挑選模式提案有結論前先不排，若提案不通過再併進下一段 LB。
- 待決 2（最大 schema 124,601 字元，離 125k 上限只剩 399）：跟 LB-2 待決 4 一起看，同樣等提案結論。
- 待決 3、4：維持現狀。
- 待決 5（`wants_variants` 目前沒有呼叫端）：之後接許願池時再排。
- LB-CF 待決 1（上手筆記第四節第 2 點還寫「預設 vLLM」）：開發 PM 已順手改好。
