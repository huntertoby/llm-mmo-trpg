# Phase LLM-1 報告：提示前綴重排（KV 前綴快取）

目的（使用者原話：「分析速度慢原因 如果不用lm studio能更快或者有其他量化方法就用」）：本機模型（LM Studio，gemma-4-12b-it，讀題約 115～128 token/秒、生成 10 token/秒）每題讀題 43 秒。LM Studio 的 KV 前綴快取實測有效（同前綴第二題 43 → 1.5 秒），但原本的 prompt 把每題變動的內容放最前、9.4k 字的固定目錄放後面，三題共同前綴只 13%。**本段只改 prompt 的組裝順序與目錄呈現，不改規則、不改 JSON schema 的欄位與限制、不改驗證器、不放寬子集。** 沒有連真模型（LM Studio 當時在換模型）；真模型對照由 PM 在 main 上跑（第 7 節）。

範圍修正（使用者原話：「順序打亂當初目的就是讓他技能多樣性啊」）：目錄打亂（`menu_order`／`menu_seed`、閃現 `catalog.shuffled`）是為了位置偏好與多樣性，**沒有拿掉**，改成「目錄固定在前綴（吃快取）＋ 題目區尾端每題隨機的建議清單」（第 1 種做法，預設），並把「整份目錄依一個種子打亂」做成可切換的參數（第 2 種做法）。見第 2 節。

## 1. Commit

| commit | 內容 |
|---|---|
| `2a4053f1` | perf(llm): put fixed catalog before per-question fields for prefix cache（提議路徑） |
| `050b1e33` | perf(llm): flash prompt keeps catalog fixed and moves count out of system（閃現） |
| `e661eec4` | perf(llm): storyteller shares style and safety prefix across scenes（說書人） |
| `ff559296` | perf(llm): naming summary orders fixed fields before effect_summary and taken_names（命名） |
| `037814e4` | chore(llm): timeout 240s and serial skill_eval by default（設定） |
| `4911185e` | test(llm): prompt prefix acceptance test（驗收測試） |
| （本報告） | docs: Phase LLM-1 report |

## 2. 每項改了什麼

### 2.1 提議路徑（`trpg llm propose`、一輪 `trpg run --llm`、API、skill_eval 共用）

檔案：`src/trpg/llm/prompts/builder.py`、`src/trpg/llm/prompts/proposal.py`、`src/trpg/skillgen/proposal_subset.py`。

- **區塊順序**：`<guide>`（固定說明）→ `<available>`（固定全目錄）→ `<request>`（題目）→ `<previous_proposal>` → `<errors>` → `<player_input>`。system 的區塊清單同步改；`PROMPT_VERSION` → `skill-proposal/11`。
- **`<guide>`**（`GUIDE_ZH`）：`budget_note_zh`、`keyword_note_zh`（文字不變）、`core_primitive_note_zh`（改成樣板「題目有 core_primitive 時…」，題目區只帶 ID）、`allowed_note_zh`（只能用 `<request>.allowed 的 ID`）、`suggested_note_zh`（建議清單不是限制）。每題相同，跟著 system 進前綴。
- **`<available>` 改送固定全目錄**（`catalog_payload(library, kind, order_seed=None)`）：這個種類（active／reaction／passive／stance）的全部骨架、原語、形狀、條件、觸發、版型、代價（`rarity=None` 列全部）、followup，依 ID 排序；格式同原本的 `available_payload`，但不含每題不同的 `keywords`，也不看稀有度與階級。主動技 13,309 字（估 7,364 token）、反應技 4,883 字、被動 5,061 字、姿態 4,395 字。
- **`<request>`**（`_request_payload`，**照呼叫端鍵順序、不排序**；`builder._json(sort_keys=False)`）：`style`（有區域時）→ `weapon_class` → `tier` → `kind` → `rarity` → `keywords`（含 `hint` 與 `ways`，從 `<available>` 搬過來）→ `core_primitive` → `skeleton` → `theme` → `allowed` → `suggested`。
  - `allowed`（`allowed_payload`）：**這題可用的 ID 清單**＝與 JSON schema／驗證器完全相同的子集（版型、骨架、原語、形狀、條件、觸發、代價、followup）。`select_subset` 的預算、子集、`build_subset_models`、schema 全部不變（測試 `test_player_text_stays_in_its_block_and_subset_ignores_retries`、`test_prompt_structure` 比對 allowed ＝ subset）。
  - `suggested`（`suggested_payload`，**多樣性的替代做法**）：有 `menu_seed` 時，依 `Rng(menu_seed).fork("suggest/<label>")` 從這題的 allowed 打亂後抽：骨架全列、原語與形狀各 `llm_topic.secondary_count`（6）個、條件 `condition_count`（4）個；`menu_seed=None`（CLI `trpg llm propose`）時沒有這段（與原本「CLI 不打亂」一致）。`menu_seed` 的另一個用途（輪替選單、`_rotate` 決定子集成員）完全不變。
- **第 2 種做法（可切換）**：`ProposalRequest.display_seed: int | None = None`，有值時整份固定目錄由它打亂（`menu_order`）；呼叫端可一輪固定一個種子（同一輪內命中快取、跨輪仍多樣；代價是每輪第一題重讀）。預設 `None`＝第 1 種。目前沒有呼叫端設定它。
- `skill_eval.py:224` 的 `menu_seed` 保留（驅動輪替子集與 suggested）。

### 2.2 閃現（`src/trpg/llm/prompts/flash.py`、`src/trpg/llm/flash_propose.py`）

- system 裡的 `{count}` 移除（改寫成「提議 `<request>` 的 count 個」）；重試收下部分變化後 count 變，system 不再變。
- 區塊順序：`<catalog>` → `<skill>` → `<usage>` → `<held_keywords>` → `<request>` → `<already>` → `<previous_proposal>` → `<errors>`。
- `<catalog>` 與 schema 列舉改用 `build_catalog` 的固定順序（不打亂；與 `scripts/eval_flash_diversity.py` 量位置偏好用的同一個順序）。原本 `catalog.shuffled(request.seed, tag)` 的結果改取前 `SUGGESTED_PER_WANT × want`（2 × 4 ＝ 8）個模板放進 `<request>.suggested_order`（system 說明它是建議起點、不是限制）。
- 第 2 種做法：`propose_variations(..., shuffle_catalog=True)` 回到 BAL-10c 的整份目錄打亂（仍放在最前）。
- `FLASH_PROMPT_VERSION` → `flash-variation/4`。

### 2.3 說書人（`src/trpg/llm/prompts/storyteller.py`、`src/trpg/narrative/storyteller.py`）

- system：世界簡介 → `STORY_STYLE` → `STORY_SAFETY` → `STORY_TASKS[scene]`（任務段移到最後）。`STORY_PROMPT_VERSION` → `storyteller/3`。
- 資料區：`<world>` → `<allowed>` → `<npcs>` → `<threads>` → `<scene>` → `<player_input>` → `<previous_output>` → `<errors>`。`<world>`（區域、語氣）比 `<allowed>`／`<npcs>`（地點層級）更少變，所以放在它們前面（PM 指示是 allowed／npcs 放 scene／world 之前；world 放最前只會多命中，不會少）。玩家輸入仍在資料區尾端、仍包在 `<player_input>`。

### 2.4 命名（`src/trpg/llm/naming.py`、`src/trpg/llm/prompts/naming.py`）

`skill_summary` 改成固定鍵順序：`style` → `weapon` → `tier` → `kind` → `rarity` → `theme` → `skeleton` → `shape` → `effects` → `keywords` → `element` → `effect_summary` → `added_effects` → `taken_names`；`build_naming_messages` 不再 `sort_keys`。system 不變；`NAMING_PROMPT_VERSION` → `skill-naming/5`（快照雜湊與 /4 相同，因為快照用的 `{"skeleton": …}` 只有一個鍵）。

### 2.5 設定

- `config/llm.toml`：`timeout_s` 120 → 240（註解：p50 59 秒，120 會讓慢的題提早逾時又重送全文）。`LLMConfig` 的程式預設值（120）沒改。
- `skill_eval.run_items` 預設 `workers` 8 → 1、`scripts/eval_llm_skills.py --workers` 預設 8 → 1（交錯送題會讓前綴快取失效；要平行時明確傳參數）。既有測試都明確傳 `workers`，沒有鎖預設值。

### 2.6 測試

- 新增 `tests/llm/test_prompt_prefix.py`（本段驗收，10 條）：CLI 三題共同前綴 ≥ 80%（實測 89.8%）；同題重試 ≥ 90%（96.6%）；一輪 `make_topic` 三題 ≥ 80%（92.0%）；固定全目錄＋重試回饋＋1,024 輸出 ≤ 16,384（`LOCAL_CONTEXT_TOKENS`）；`display_seed` 只改目錄順序；閃現 system 不含 count 且目錄在前；閃現重試前綴 ≥ 80% 並有 `suggested_order`；閃現目錄固定順序／`shuffle_catalog` 打亂；不同招的閃現 system 相同；說書人四場景 system 共同前綴 ≥ 60%（79.2%）。
- 更新（只改順序與版本，不改驗證器與 schema 語意）：`tests/llm/test_prompts.py`（`test_block_order` 新順序、新增 `test_request_keeps_the_callers_key_order`、快照 /11）、`tests/llm/test_proposal_prompt.py`（`test_prompt_structure`：區塊順序、allowed ＝ subset）、`tests/llm/test_flash_propose.py`（版本 /4、`test_suggested_order_follows_the_question_seed_and_catalog_stays_fixed` 取代「schema 順序隨種子」：固定目錄下 schema 同序、`suggested_order` 隨種子不同、`shuffle_catalog=True` 時 schema 隨種子不同）、`tests/llm/test_naming.py`（快照 /5）、`tests/narrative/test_storyteller.py`（快照 /3、安全規則在任務前）、`tests/skillgen/test_topup_6s2.py`（`keyword_note_zh` 改在 `<guide>`；原本 `plain.tokens < 3_500` 的 8k 上下文保護改成「＋1,024 ≤ 16,384」——固定全目錄本來就比子集大，見第 6 節）。

## 3. 前綴比例改前／改後（字元；照 `audit.py` 的算法：`[system]`＋`[user]` 串起來從頭比對）

| 路徑 | 改前 共同前綴／最長 | 改前 % | 改後 共同前綴／最長 | 改後 % |
|---|---|---|---|---|
| `trpg llm propose` 三題（seed 0：epic／rare／epic） | 1,485／11,324 | 13.1% | 15,251／16,984 | **89.8%** |
| 同一題第 1 次 vs 重試 | 11,290／11,873 | 95.1% | 16,931／17,532 | **96.6%** |
| 一輪 `make_topic` 三題（2 階、cloud_ridge、melee） | 1,342／6,299 | 21.3% | 15,349／16,676 | **92.0%** |
| 命名三招 | 1,653／2,077 | 79.6% | 1,727／2,095 | 82.4% |
| 閃現：同一招重試（count 不變） | 2,337／2,547 | 91.8% | 2,559／2,787 | 91.8% |
| 閃現：同一招重試（收下 1 個後 count 4 → 3） | ≈60 字（system 第 60 字就不同） | ≈2% | 2,309／2,856 | **80.8%** |
| 閃現：三招不同技能 | 1,281／2,385 | 53.7% | 1,214／2,650 | 45.8%（註 1） |
| 說書人：四種場景 system | 79／1,039 | 7.6% | 831／1,049 | **79.2%** |
| 說書人：同地點 event（天氣、時段不同） | 1,366／1,878 | 72.7% | 1,846／1,899 | **97.2%** |
| 說書人：event vs chat（整份） | 79／1,877 | 4.2% | 834／1,895 | **44.0%** |

註 1：不同技能的閃現目錄本來就不同（只列這招套得上的模板），原本 53.7% 是因為稽核樣本的 `<request>`（flash_nth、major、role_tier）三招剛好相同；實際遊戲中這些會變。現在 system（1,066 字，40%）＋目錄在前，重試與同招才是快取能吃到的情況。

## 4. 讀題秒數估算（照稽核報告第 6 節：真實 token ≈ 粗估 × 0.85，命中部分固定 1.5 秒，未命中部分 ÷ 115 token/秒）

| 路徑 | 改前每次讀題 | 改後：第一題（冷） | 改後：之後每題（命中） |
|---|---|---|---|
| `trpg llm propose`（粗估 8,379 token ≈ 7,120 真實） | 43 秒（實測；命中 13% → 約 35 秒） | 約 62 秒（固定全目錄比 1 階 epic 子集多約 2,500 粗估 token） | 未命中 487 粗估 ≈ 414 真實 → **約 5 秒** |
| 一輪 `make_topic`（8,311 ≈ 7,060 真實） | 15～27 秒（命中 21% → 8～20 秒） | 約 61 秒 | 未命中 365 ≈ 310 真實 → **約 4 秒** |
| 同題重試 | 約 4 秒 | — | 未命中 199 ≈ 169 → **約 3 秒**（中間不能插其他請求） |
| 閃現重試（count 變） | 約 7～10 秒（system 變、全部重讀） | — | 未命中 ≈ 230 → **約 3 秒** |
| 說書人跨場景 | 約 7 秒 | — | 未命中 428 ≈ 364 → **約 5 秒**；同地點 event 約 2 秒 |
| 命名 | 約 3 秒（若前一請求也是命名） | — | 約 3 秒 |

目標「讀題 ≤ 8 秒」：命中時達到；每個程序的第一題與快取被踢掉後的第一題（例如提議→命名交錯、換種類 active↔reaction、`workers > 1`）要付 60 秒左右，比原本的 43 秒多約 19 秒。真模型實測才能確認 LM Studio 保留幾段前綴（稽核報告第 6 節第 6 點）。

## 5. 多樣性量測（改前／改後）

### 5.1 `scripts/eval_flash_diversity.py --mock`（502 題；Mock 不看 prompt，提議由 `mock_flash_client` 依種子輪流類別取，所以這個數字只能證明「改 prompt 沒有改到目錄、驗證與補位」，量不到模型的位置偏好）

| 指標 | 改前 | 改後 |
|---|---|---|
| 目錄出現過的模板／LLM 至少提出一次／共提出 | 63／56／1,270 | 63／56／1,270（相同） |
| 提出分布的熵／套得上分布的熵 | 5.16／5.47 bit | 5.16／5.47 bit（相同） |
| 位置偏好（提出的模板落在目錄前／中／後段） | 52.7%／32.7%／14.6% | 52.7%／32.7%／14.6%（相同） |
| 回應中第一個提出的（前／中／後段） | 64.5%／23.7%／11.8% | 64.5%／23.7%／11.8%（相同） |

（Mock 的「前段 52.7%」是 Mock 自己依類別輪流取、而目錄依類別分組造成的，不是模型偏好；BAL-10c 報告也說位置偏好只有真模型量得到。）

### 5.2 真模型（PM 在 main 上跑；改前基準在 BAL-10c／4-L11 之後沒有留下真模型的位置偏好數字，這次要先跑一次改前再跑改後）

```bash
# 改前（main 合併前的 commit）與改後各跑一次；位置偏好看「## 整體分散度」那段的前／中／後段與第一個提出的比例，目標接近 33%
TRPG_LLM_CONFIG=config/llm.local.toml uv run python scripts/eval_flash_diversity.py --real --csv /tmp/flash_div.csv --workers 1
```

### 5.3 提議路徑的多樣性

提議路徑沒有既有的位置偏好量測；多樣性原本就由引擎決定（核心原語加權抽、輪替選單決定子集成員），這兩者不變。本段只把「呈現順序打亂」改成「題目區的 suggested 隨機清單」，真模型是否仍偏好目錄前段，由 5.2 同一批真模型對照看通過率與 `trpg llm propose` 的核心原語／骨架分布。

## 6. 測試結果摘要

- `uv run ruff check`、`uv run ruff format --check`：通過。
- `uv run mypy`（全專案 1,380 檔）：通過。`uv run lint-imports`：13 個契約全部 kept。
- 相關測試（`-n 4`）：`tests/llm`（含新的 `test_prompt_prefix.py` 10 條）、`tests/narrative`、`tests/skillgen/test_proposal_subset.py`、`test_llm_source.py`、`test_proposal_l8.py`、`test_topup_6s2.py`、`test_topup_6s2c.py`、`test_proposal_layouts.py`、`test_proposal_l8b_topic.py`、`test_witness_6ew.py`、`test_fallback_6s2b.py`、`tests/cli/test_llm_propose_cli.py`、`tests/cli/test_run_cli.py`、`tests/api/test_world_story.py`、`tests/api/test_run_llm_api.py`、`tests/roguelite`：**1,194 passed**。沒跑全量（守則 11）。
- 重播：`trpg battle --map swamp --seed 7` → `trpg battle replay`：通過（88 個動作、313 個事件，最終狀態一致）。

## 7. PM 在 main 上做真模型對照的指令

```bash
# 提議（改前基準：一次通過 2、重試通過 4、退回 4、p50 58.7 秒、總 621 秒）
TRPG_LLM_CONFIG=config/llm.local.toml uv run trpg llm propose -n 10 --seed 1
# 閃現多樣性與位置偏好（見 5.2）
TRPG_LLM_CONFIG=config/llm.local.toml uv run python scripts/eval_flash_diversity.py --real --csv /tmp/flash_div.csv --workers 1
```

看三個數字：通過率（目標 ≥ 6/10）、每題秒數（第一題約 60 秒，之後目標 ≤ 8 秒；若之後每題仍 40 秒以上，代表 LM Studio 沒命中——先確認 `config/llm.local.toml` 沒有讓請求交錯、再試 `json_schema_mode = "none"` 排除 80k 字元 schema 的文法編譯時間）、位置偏好（接近 33%）。三者衝突時只回報數字（第 8 節）。

## 8. 待 PM 決定

1. **固定全目錄 vs 固定子集**：本段採固定全目錄（主動技 13.3k 字、估 7.4k token；真實約 6.3k）。另一個選項「固定子集但不打亂」（同稀有度的題目才共用前綴、跨稀有度／關鍵字重讀 9k 字）沒有實作。全目錄的代價：(a) 每個程序第一題約 62 秒（比原本 43 秒多 19 秒）；(b) 模型看到的選項比這題能用的多（`allowed` 才是限制，schema 照樣擋住不合法的輸出），12B 模型是否因此更常提不合法的 ID（`union_tag_invalid`／`literal_error`）要看真模型通過率；(c) `followup`、`cost_on_miss`、全部 `cost_penalty` 狀態在目錄裡永遠列出，低稀有度題目靠 `allowed.followup: false`／`allowed.costs` 說明不可用。
2. **多樣性做法**：預設第 1 種（固定目錄＋題目區隨機 `suggested`／`suggested_order`）；第 2 種（`display_seed`／`shuffle_catalog=True`）已可切換但沒有呼叫端用。若真模型的位置偏好回到 BAL-10c 之前的水準（第一個提議取自目錄前三分之一 > 50%），選項：改用第 2 種（一輪一個種子）、或加大 `suggested` 數量（`secondary_count`、`SUGGESTED_PER_WANT`）。**通過率、讀題秒數、多樣性三者衝突時，請依第 7 節的數字決定，本段沒有取捨。**
3. **說書人 `<world>` 放最前**（PM 指示是 allowed／npcs 放 scene／world 之前）：`<world>` 只有區域名與語氣，比地點層級的 allowed／npcs 更少變，放最前只會多命中；若要嚴格照指示改成 allowed → npcs → world，只動 `narrative/storyteller.py` 一行。
4. **`style` 放在 `<request>` 最前而不是 `<guide>`**：PM 指示把 style 列在固定說明；本段放在題目區第一個鍵——區域換了只重讀題目區（~400 token），放 `<guide>` 則換區域時整份 13k 字目錄都要重讀。
5. **`core_primitive_note_zh` 改成樣板**：原本每題帶「核心效果必須使用原語 X」，現在 `<guide>` 固定寫「題目有 core_primitive 時…」、題目區只帶 `core_primitive` ID；文意相同，但模型是否照樣遵守要看真模型的 `core.required` 類錯誤。
6. **`timeout_s` 240**：只改 `config/llm.toml`；`LLMConfig` 程式預設仍 120（環境變數 `TRPG_LLM_TIMEOUT_S` 可覆寫）。`config/llm.local.toml` 若另設 timeout 要一併改。
7. **`workers` 預設 1**：`skill_eval.run_items` 與 `scripts/eval_llm_skills.py`；要回到平行就傳 `--workers 8`。
8. **`tests/skillgen/test_topup_6s2.py` 的 `plain.tokens < 3_500`**（6S-2 的 8k 上下文保護）改成「＋1,024 ≤ 16,384」：固定全目錄下單題最小也約 8k 粗估 token，8k 上下文的機器跑不了提議路徑（本機現在是 16k）。
9. **命名與提議交錯**：提議→命名→下一題提議的順序沒改（稽核第 6 節第 6 點「先全部提議、再全部命名」沒做，因為一輪的候選是逐個產生的）；若 LM Studio 只留一段前綴，命名會把提議的快取踢掉，每題提議仍要重讀 60 秒。真模型對照時若「之後每題」仍接近 60 秒，這是第一個要查的點（可先用 `trpg llm propose` 不帶 `--naming` 驗證快取本身有效）。

## LLM-1A（2026-11-06）：目錄打亂改回預設

**使用者決定**：E4B 真模型對照 LLM-1 後變差（閃現位置偏好前段 33% → 73%、熵 3.80 → 3.60、propose 一次通過 8 → 5），使用者選 A（原話「A」）：**打亂全部改回來，其他保留**。說書人、命名的前綴改善、`timeout_s` 240、`workers` 1 不動。

**改了什麼**

| commit | 內容 |
|---|---|
| `fd5ceb09` | 提議：`<available>`（全目錄）改由題目的 `menu_seed` 打亂（`catalog_payload(order_seed=menu_seed)`）；拿掉 `ProposalRequest.display_seed`、`suggested_payload`、`<request>.suggested` 與 `<guide>.suggested_note_zh`。`menu_seed=None`（CLI `trpg llm propose`）仍依 ID 排序，與 LLM-1 之前相同。區塊順序、`allowed`、子集、schema、驗證不變。`PROMPT_VERSION` → `skill-proposal/12` |
| `20d81048` | 閃現：`propose_variations(shuffle_catalog=True)` 為預設（BAL-10c 的整份目錄打亂，同一招重試同序）；拿掉 `suggested_order`、`SUGGESTED_PER_WANT` 與 system 的說明。`{count}` 移出 system 保留。`FLASH_PROMPT_VERSION` → `flash-variation/5` |
| `b67c2843` | 測試：`test_prompt_prefix.py` 拿掉「一輪三題共同前綴 ≥ 80%」，改驗「不同 menu_seed 的目錄順序不同、同種子相同、無 suggested」「打亂只改 `<available>` 順序不改內容」「閃現預設打亂、`shuffle_catalog=False` 才固定」；保留同題重試 ≥ 90%、閃現重試 ≥ 80%、說書人跨場景 ≥ 60%、CLI 三題（無 menu_seed）≥ 80%。`test_flash_propose.py` 同步 |

驗收：ruff、format、mypy、lint-imports 通過；`tests/llm tests/narrative tests/skillgen tests/cli`（`-n 4`）4,817 passed；重播 swamp 種子 7 一致。

**E4B 真模型數字**（`config/llm.local.toml`，gemma-4-small＝E4B MLX 4bit；temperature 0.7，每次跑都有抽樣誤差）

| 指標 | 改前（LLM-1 之前） | LLM-1 | LLM-1A |
|---|---|---|---|
| propose 10 題：一次通過／重試通過／退回 | 8／1／1 | 5／—／— | 3／6／1 |
| propose 平均每題／總耗時 | 13.8 秒／149 秒 | — | 17.2 秒／172 秒 |
| 閃現位置偏好 前／中／後段 | 33／44／22% | 73／—／—% | 33／56／11% |
| 閃現第一個提出的 前／中／後段 | — | — | 50／25／25% |
| 閃現提出分布的熵 | 3.80 bit | 3.60 bit | 3.56 bit |
| 閃現平均每題 | 22.0 秒 | — | 18.8 秒 |

說明：`trpg llm propose` 沒有 `menu_seed`，LLM-1A 的 prompt 與 LLM-1 只差 `<guide>` 少一句建議清單說明，所以 propose 這列量不到打亂的效果；通過率 3/10 低於 LLM-1 的 5/10，較可能是全目錄（LLM-1 保留的部分）＋抽樣誤差，不是打亂造成。閃現的前段偏好回到 33%，熵沒有回升（40 題、樣本小）。

若改回 12B（讀題 43 秒），可再關打亂量一次前綴快取的效益。

## LLM-1B（2026-11-06）：提議改回「只送這題能用的子集」

**使用者決定**：LLM-1A 的 E4B 對照（一次通過 3／10）仍低於 LLM-1 之前（8／10），使用者選 a（原話「a.」）：**propose 的 `<available>` 改回只送這題能用的子集**，題目區不再需要 allowed 清單。LLM-1A 的「依 menu_seed 打亂」、區塊順序（`<guide>` 固定說明在前、變動欄位在後）、說書人、命名的前綴改善、`timeout_s` 240、`workers` 1 都保留。另依玩法 PM（09 9.6.10 #137 字面）改說書人煙霧測試的斷言。

**改了什麼**

| commit | 內容 |
|---|---|
| `0480e29f` | 提議：`<available>` 改回 `available_payload(library, subset)`（`select_subset` 的子集，依 `menu_seed` 打亂；關鍵字的 `hint`／`ways` 回到 `<available>.keywords`，`<request>.keywords` 只剩 `id`／`name_zh`，與 LLM-1 之前相同）；拿掉 `<request>.allowed`、`<guide>.allowed_note_zh`、`catalog_payload`、`allowed_payload`、`_full_subset`。system 改回「`<available>` 是這一題可用的選項；只能使用 `<available>` 中列出的選項」。區塊順序、`<guide>`（預算、關鍵字、核心原語說明）、題目區鍵順序不變；子集、schema、驗證器不變。`PROMPT_VERSION` → `skill-proposal/13`。測試：`test_prompt_prefix.py`（CLI 三題改驗「共同前綴至少涵蓋 system＋`<guide>`」，實測 3,073 字／最長 11,515 字＝26.7%，`</guide>` 在第 1,619 字；同題重試 ≥ 90% 保留；打亂只改子集順序；無 `allowed`）、`test_proposal_prompt.py`（`<available>` ＝ `available_payload(subset)`、題目區沒有 `allowed`）、`test_upgrade_topup.py`（token 檢查加回 LLM-1 之前的 `plain.tokens < 3_500`，並保留「＋1,024 ≤ 16,384」）、`test_prompts.py`（快照 /13） |
| `deecb9b5` | `tests/llm/test_neutral_address_real_model.py`：斷言改成「若提到主角，必須用名字、稱謂或『你』，不能用他／她」，不再要求每段都提到主角；點名率（提到主角的題數／說書人總題數）跑完印在終端，只當參考值、不設門檻 |

驗收：ruff、format、mypy（1,379 檔）、lint-imports（14 contracts）通過；`tests/llm tests/skillgen tests/narrative tests/cli`（`-n 4`）4,842 passed、14 skipped；重播 swamp 種子 7 一致（88 動作、313 事件）。

**E4B 真模型數字**（`config/llm.local.toml`，gemma-4-small＝E4B MLX 4bit；temperature 0.7，每次跑都有抽樣誤差）

`trpg llm propose -n 10 --seed 1`（總耗時＝10 題耗時加總）：

| 指標 | 改前（LLM-1 之前） | LLM-1A | LLM-1B 第 1 次 | LLM-1B 第 2 次 |
|---|---|---|---|---|
| 一次通過／重試通過／退回 | 8／1／1 | 3／6／1 | 4／4／2 | 6／3／1 |
| 平均每題 | 13.8 秒 | 17.2 秒 | 19.7 秒 | 15.6 秒 |
| 總耗時 | 149 秒 | 172 秒 | 197 秒 | 156 秒 |

- 第 1 次跑的最後約 30 秒與 mock 測試（`-n 4`）同時進行，第 2 次單獨跑；兩次差距（4 → 6）大致就是抽樣誤差的幅度。
- 兩次都退回第 9 題（common／collision：`keyword.required`、`value_error`、`reference`，由 workshop 保底）；第 1 次另退回第 1 題（epic／wet：三次都 `skeleton.core`＋`budget.weak`，由 composer 保底）。`value_error` 兩次各 4～5 個，是重試的主因。

`pytest -q tests/llm -m llm -n 0 --timeout=900`：**11 過、0 失敗，98 秒**。說書人點名率 **2／4**（參考值）；沒有任何一題用他／她指稱主角。情境判定 2 題、舊的 3 題（ping、propose_one、one_upgrade_item）都過。

**待 PM 決定**

1. **通過率仍未回到改前的 8／10**：LLM-1B 兩次 4／10、6／10。與改前相比還留著的差異：`<guide>` 在 `<available>` 之前（改前預算說明在 `<request>` 裡、`<request>` 在最前）、system 的區塊說明句、`menu_seed`（CLI 沒有，不影響這個指令）。若要確認是不是抽樣誤差，可多跑幾次同指令取平均；若要再往改前靠，下一步是把 `<request>` 移回最前（會失去 system＋guide 之外的前綴快取，但子集版本本來跨題就只共用到 guide）。
2. **`test_upgrade_topup.py` 的 `plain.tokens < 3_500`**（6S-2 的 8k 上下文保護）照子集改回後重新加上（目前實測通過）。

## LLM-1C（2026-11-06）：提議的區塊順序改回 LLM-1 之前

**使用者決定**：技能提議的一次通過率要回到 LLM-1 之前的水準（E4B 約 7／10）。LLM-1B 改回子集後仍是「system → `<guide>` → `<available>` → `<request>`」，E4B 5 次平均 5.4／10。這段把提議路徑的 user 訊息改回 LLM-1 之前（commit `a6e25fd2`）的結構。說書人、命名、閃現、`timeout_s` 240、`workers` 1 不動。

**改了什麼**

| commit | 內容 |
|---|---|
| `269ca0e4` | `prompts/builder.py`、`prompts/proposal.py` 以 `a6e25fd2` 為準還原：`<request>` 在最前（鍵排序），`budget_note_zh`、`keyword_note_zh`（有關鍵字才帶）、`core_primitive_note_zh`（每題帶「核心效果必須使用原語 X」）放回 `<request>` 內；接著 `<available>`（仍是 LLM-1B 的子集＋依 `menu_seed` 打亂）；`<previous_proposal>`、`<errors>` 在最後。拿掉 `<guide>`、`GUIDE_ZH`、`CORE_PRIMITIVE_NOTE_ZH`、`build_skill_proposal_messages(guide=…)` 與題目區的呼叫端鍵順序。system 的任務與區塊說明句改回改前寫法。保留 `LOCAL_CONTEXT_TOKENS`（測試用）。`PROMPT_VERSION` → `skill-proposal/14`（快照雜湊與 /10 相同）。測試：`test_prompts.py`（區塊順序改回 request → available、題目區鍵排序、快照 /14）、`test_proposal_prompt.py`、`test_prompt_prefix.py`（CLI 三題改驗「共同前綴至少涵蓋 system」，實測 1,485／11,342 字；同題重試前綴實測 98%，≥ 90% 斷言仍成立）、`test_upgrade_topup.py`（說明回到題目區、無關鍵字題目不帶 `keyword_note_zh`） |

驗收：ruff、format、mypy（1,291 檔）、lint-imports（14 contracts）通過；`tests/llm tests/skillgen tests/narrative tests/cli`（`-n 4`）4,842 passed、14 skipped；重播 swamp 種子 7 一致（88 動作、313 事件）。

**E4B 真模型數字**（`config/llm.local.toml`，gemma-4-small＝E4B MLX 4bit；temperature 0.7；`trpg llm propose -n 10 --seed 1`，兩次都單獨跑、期間不跑其他測試）

| 指標 | 改前（LLM-1 之前，平均） | LLM-1B（5 次平均） | LLM-1C 第 1 次 | LLM-1C 第 2 次 | LLM-1C 平均 |
|---|---|---|---|---|---|
| 一次通過 | 7 | 5.4 | 6 | 5 | 5.5 |
| 重試通過 | — | — | 1 | 3 | 2 |
| 退回 | — | — | 3 | 2 | 2.5 |
| 平均每題 | 13.8 秒 | — | 16.9 秒 | 17.4 秒 | 17.2 秒 |
| 總耗時 | 149 秒 | — | 169 秒 | 174 秒 | 172 秒 |

- 第 1 次退回 1、2（epic：`skeleton.secondary`／`rune.tag`、`skeleton.condition`，composer 保底）與 9（common／collision：`keyword.required` 三次，workshop 保底）；第 2 次退回 6（`value_error` 三次）與 9（同上）。第 9 題在 LLM-1B、LLM-1C 四次都退回。
- 兩次平均 5.5，與 LLM-1B 的 5.4 差不多；區塊順序看起來不是通過率差距的主因，樣本小、抽樣誤差約 ±1～2。

**待 PM 決定**

1. **通過率沒有回到約 7**：prompt 的 system＋user 結構與 `a6e25fd2` 已相同（快照雜湊一致），剩下的差異是 `<available>` 子集內容（LLM-1 之後內容／關鍵字的改動、`menu_seed` 打亂在 CLI 不作用）、`timeout_s` 240、以及取樣誤差。若要確認，可在 `a6e25fd2` 直接跑同指令 3～5 次當同機基準（「改前 7」可能本身偏高）。
2. **第 9 題（common／collision）固定退回**：`keyword.required` 是主要原因，與區塊順序無關，可另開一段看 collision 的 ways 寫法。
