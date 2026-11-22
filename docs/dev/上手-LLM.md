# 上手：LLM 整合（`src/trpg/llm/`、LLM 出招流程、閃現的名稱與描述）

> 給實作 agent：派工 prompt 指到這份時，讀完就能改 LLM 提議、命名、預先生成與日誌重播。
> 2026-11-13 LF-1 新開，依據當時的 main（`WLOG_FORMAT` `trpg-wlog/10`、`LOG_FORMAT` `trpg-battle-log/119`、`FLASH_PROMPT_VERSION` `flash-variation/5`）。
> 2026-11-13 LF-2 更新：`FLASH_PROMPT_VERSION` `flash-variation/6`（減少白白重問，見第六節）；日誌與存檔格式沒變。
> 規格 `docs/phases/PhaseLF計畫.md`（LF-1～LF-3）；調查與實測 `docs/phases/LLM閃現調查報告.md`。閃現規則本身看 `docs/dev/上手-內容資料與模擬.md` 第四節第 35～41 點。
> 改到這一塊時順手更新這份。

## 一、這一塊在哪些檔

| 檔案 | 職責 |
|---|---|
| `llm/client.py` | `LLMClient`（Protocol：`complete(messages, json_schema=)`）、`MockLLMClient`（依序回應；回應是例外就拋）、`OpenAICompatClient`（本機 OpenAI 相容端點） |
| `llm/config.py` | `LLMConfig`、`load_llm_config(path)`：`config/llm.toml`＋環境變數（`TRPG_LLM_CONFIG` 指另一份、`TRPG_LLM_REASONING_EFFORT`、`TRPG_LLM_GENERATE`…）。HC-7 b：程式裡要預設值（重試次數、退回率提醒、連線檢查逾時）一律讀 `LLM_DEFAULTS`（schema 預設，只留這一份）；新鍵 `probe_timeout_s`（3.0）、`situation_attempts`（2）、`story_attempts`（2）只在 schema，`config/llm.toml` 沒加；情境判定與說書人照 client 帶的設定（`client_config(client)`，Mock 用預設） |
| `llm/errors.py` | `LLMUnavailable`（立刻停、退回）、`LLMTimeout`／`LLMBadResponse`（算一次嘗試） |
| `llm/response.py` | `clean_response`：去 `<think>`、程式碼框 |
| `llm/propose.py`、`candidate_source.py` | 完整技能提議（4-L5～L8）：重試迴圈、`make_proposer`、`mock_proposer`、`mock_naming_client` |
| `llm/naming.py`、`prompts/naming.py` | 命名步驟 `name_skill`（名稱＋`concept`＋`cast_flavor`；字數、字元集、禁字、重名、簡體、古風、敘事與效果一致）；`apply_naming` |
| `llm/flash_propose.py`、`prompts/flash.py` | **閃現**：`propose_variations`（挑類別／模板／參數＋`note_zh`，大變化另有 `name_zh`）、`judge_items`、`note_checker`／`name_checker`／`note_words`（LF-2）、`LlmFlashSource`、`RecordedSource`、`name_texts`（LF-1）、`mock_flash_source`、`FlashProposalStats` |
| `llm/flash_repair.py` | **LF-2**：本地修正（`repair_fields`：類別、單一參數、多填參數、空白；`normalize_note`／`normalize_name`：空白、半形、重複句號、超長截到標點） |
| `llm/story_skill.py`、`prompts/story.py` | 大世界劇情技能換元素與文字 |
| `llm/situation.py`、`prompts/storyteller.py` | 情境判定、說書人 |
| `llm/consistency.py` | 敘事與效果一致（`skill_facts`、`check_mentions`、`check_added`）、世界觀詞用量 |
| `llm/flash_eval.py`、`skill_eval.py`、`style_eval.py` | 真模型評估工具（`trpg llm …`） |
| `api/llm_source.py` | `LlmProvider`：`LocalLlmProvider`（讀設定、ping）、`MockLlmProvider`（測試；`flash_naming=True` 開 Mock 命名） |
| `api/world_pregen.py` | 大世界預先生成：單一背景佇列（WP-2 起許願插隊排最前面）、只放記憶體、等最多 10 秒（HC-7 b 起等待秒數與每人上限在 `content/skill_pick.yaml` 的 `pregen`；挑選模式的時間預算在 `budget_seconds`） |
| `world/generated.py` | 世界引擎拿生成內容的介面：請求（`FlashGenRequest`…）、`supply`、`recorded`（重播） |
| `roguelite/llm_hook.py` | 一輪的掛接點（`use_proposer`、`use_flash_source`；`trpg.roguelite` 不能匯入 `trpg.llm`） |
| `skillgen/flash_text.py` | **LF-1**：`VariationText`、`clean_text`／`clean_name`／`clean_note`（引擎端的最後一道文字檢查） |
| `llm/wish.py`、`prompts/wish.py` | **WP-1 許願池**：`match_wish`（願望 → 1～2 個關鍵字，`WISH_PROMPT_VERSION` `wish-match/1`）、`WishSource`（對關鍵字的 client＋把願望放進 `<player_input>` 的技能提議器）、`mock_wish_client` |
| `world/wish.py` | **WP-1**：許願的規則（`wish_problem`、`wish_menu`、`wishes_left`、`wish_request`、`apply_wish`）；只經 `supply` 拿 `WishGen` |

## 二、資料怎麼流（LLM 出招流程，各入口共用）

```
請求（純資料；鍵 = input_key(完整輸入)）
  → [API] world_pregen：背景單一佇列（預測：戰後那招能閃了就排）
       └ 生成函式：prompt → client.complete(json_schema) → clean_response → JSON／pydantic
                   → 引擎驗證 → 不合格帶 <errors> 重試（≤ max_retries）→ 紀錄
  → [世界引擎] supply(請求, 種類, 退路, accept)：拿暫存（沒好就等 ≤ 10 秒），不對就用退路
       └ 最後給出的版本 → WorldLogEntry.generated（世界日誌）
  → [重播] recorded(日誌紀錄) 當供應者，不呼叫 LLM
```

- 一輪（roguelite）沒有預先生成：`open_flash` 同步呼叫來源，紀錄進 `RunState.flash_llm_log`，選項連同套用後的技能存在 `pending_flash`（讀檔不再呼叫）。
- **閃現的文字（LF-1）**：
  1. `propose_variations` 收下合格項目的 `note_zh` → 紀錄 `texts`（`VariationText{key, note_zh}`）。
  2. `LlmFlashSource(naming=…)`：用紀錄的提議出一次題（純函式 `make_offer`＋`RecordedSource`），對大變化與轉型選項 `name_skill`，名稱寫進 `texts`；沒有描述時用命名的 `concept`（`clean_note` 過了才用）。命名的 Mock 種子依選項分流（同題不撞名）。
  3. `make_offer` 先呼叫 `proposed`、再呼叫 `texts`（`TextSource`；用 `getattr`，沒有就空），`_Builder.option` 套用前 `clean_text` 掛到變化上——提議的、補位的、轉型保底只要鍵對得上都有文字。
  4. 變化（`Variation.name_zh`／`note_zh`）跟著 `FlashRecord` 存進閃現狀態；`flash_derive.flashed_identity` 用最後一個大變化／轉型的 `name_zh`（`clean_name` 過了才用），所以重推、升階重配、下一次閃現都留得住。
  5. 大世界：`provider_generators.flash` → `FlashLlmRecord`（含 `texts`）→ `growth._flash_source` 的 `_RecordedFlash(accepted, texts)`。
- **確定性**：`Variation.key()` 不含文字（子亂數、去重、合併照舊）；文字只影響名稱、技能 ID（歷程雜湊包含文字）。

## 三、必守的規矩

1. 引擎（`trpg.engine`）不碰 LLM；世界引擎與一輪只經過 `supply`／`llm_hook` 拿**資料**（守則 1、5）。
2. LLM 只提議：結構走目錄與驗證器，數值由預算器補；文字由 `skillgen.flash_text`／`llm.naming` 檢查，不合格只丟文字（守則 3）。
3. 一律經 `LLMClient`，測試用 `MockLLMClient`／`mock_*`，**不連網路**（守則 6）。
4. 玩家文字只進 `<player_input>`（守則 7；閃現目前沒有玩家文字，許願池會有）。
5. 新的紀錄欄位一律 `exclude_if` 空值：沒有 LLM 文字的存檔、日誌逐字不變；世界日誌多欄位就升 `WLOG_FORMAT`、把舊版加進 `READABLE_WLOG_FORMATS`。改了世界規則的程式才升 `WORLD_RULES_VERSION`。
6. 改任何 prompt 文字要升該 prompt 的版本號（`FLASH_PROMPT_VERSION`、`NAMING_PROMPT_VERSION`…；快照測試會抓）。
7. Mock 預設不命名閃現（`mock_flash_source(naming=False)`、`MockLlmProvider(flash_naming=False)`），所以既有快照不動；要測命名就明確打開。

## 四、常踩的坑

1. **新 worktree 沒有 `.venv`**：先 `uv sync --frozen`，之後 `UV_NO_SYNC=1`。
2. **本機模型**：`config/llm.toml` 預設 `localhost:8001` 上 LM Studio 的 `swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp@iq4_xs`、溫度 0.7、`enable_thinking = false` 加 `reasoning_effort = "none"`（2026-11-22 使用者改用 Swift 27B，專案 PM 轉；只設 enable_thinking 它仍會思考，見 `docs/phases/Swift-Qwen27B品質評估.md`；舊預設是 Gemma，LB-CF）；另一份設定檔只有設了 `TRPG_LLM_CONFIG` 才會讀。Qwen、Gemma 都要 `reasoning_effort = "none"`，否則思考吃光 `max_tokens`、回應是空的（調查報告 B.1）；換回 vLLM 時要拿掉這行（vLLM 可能不接受 none）。模型名照 `GET /v1/models`。
3. **Mock 命名撞名**：同一題多個選項用同一個種子時 Mock 給同一個名字，命名會 `name_zh.duplicate` 退回（LF-1 前 `name_offer` 就有這個問題，`name_texts` 已依選項分流種子）。
4. **Mock 命名寫不到橋接加上的效果**（`narrative.missing_added`）：Mock 的 `concept` 只列效果摘要，橋接那一項常退回組合式名稱；測試不要假設每個大變化都命名成功。
5. **描述的一致性檢查很嚴**（實測 `note_zh.missing_added` 常擋）：LF-2 起不合格只丟說明（`flash.note_dropped.*`）、變化照收；測資料流要說明留下來時，仍可用 `monkeypatch` 把 `flash_propose.note_checker` 換成一律通過（`tests/llm/test_flash_texts_lf1.py::lenient_notes`）。
6. **`make_offer` 的呼叫順序**（LF-1 起）：先 `proposed`、再 `texts`、再轉型與補位。改這裡要跑 slow 的 `tests/skillgen/test_refactor_parity.py`（閃現出題的 JSON 雜湊）。
7. **大變化題目的命名延遲**：每個大變化／轉型一次命名呼叫（本機 Qwen 3.8 27B 實測一題 4 個選項約 9 秒），大世界預先生成來不及時整題退回模板（PhaseLF計畫 第 7 節待決 5）。
8. **LM Studio 換模型規則（必守；2026-11-14 使用者，LB-2b 起）**：之前換模型沒先卸載已載入的模型就載新的，顯存不夠、溢出到 RAM 用 CPU 跑（LB-2 重測 Gemma 只剩 30 t/s）。碰 LM Studio 的工作一律照做：
   1. 換模型前先卸載全部：`C:\Users\tobby\.lmstudio\bin\lms.exe unload --all`（再用 `lms.exe load <model id>` 載入目標模型；只用環境變數 `TRPG_LLM_MODEL` 或腳本參數指定模型，不改 `config/llm*.toml`）。
   2. 量測前查 `GET http://localhost:8001/api/v0/models`，確認 `state=loaded` 的**只有目標模型一個**；不只一個就停下回報。
   3. 保留 60 t/s 門檻（`scripts/llm_model_compare.py` 的 `MIN_TPS`），沒達到就停下回報，不硬跑。
   4. 全部跑完後把 `config/llm.toml` 的預設模型（目前是 `swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp@iq4_xs`）載回來（`lms.exe load`），維持使用者原狀；使用者已自己載好時不載入、不切換。
   - LM Studio 一次只跑一個量測；不要啟動、關閉 LM Studio 本身，也不要改它的設定。

## 五、相關測試

| 改了什麼 | 跑哪些 |
|---|---|
| 閃現提議、命名、文字 | `tests/llm/test_flash_propose.py`（含 slow）、`test_flash_lf2.py`、`test_flash_texts_lf1.py`、`test_flash_note_*.py`、`test_naming.py`；`tests/skillgen/test_flash_text_lf1.py` |
| 一輪的閃現紀錄 | `tests/roguelite/test_flash_llm_run.py`、`test_flash_texts_run_lf1.py`、`test_save.py` |
| 大世界生成、日誌、重播 | `tests/world/test_generated_content.py`、`test_flash_texts_world_lf1.py`、`test_save.py`、`test_replay.py`；`tests/api/test_world_pregen.py`、`test_world_pregen_schedule.py` |
| prompt 文字 | `tests/llm/test_prompts.py`、`test_prompt_prefix.py` |
| 許願池（WP-1、WP-2） | `tests/world/test_wish.py`、`tests/llm/test_wish_match.py`、`tests/api/test_wish_pregen.py`、`tests/api/test_wish_api_wp2.py`（API、面板、等待、插隊）；主城 `panel`：`tests/world/test_capital.py`、`test_capital_figures.py`、`client/src/world/atlas.test.ts` |
| 依賴方向 | `uv run lint-imports`、`tests/test_architecture.py` |

技能提議 prompt／schema（LB-2、LB-2b）：`tests/llm/test_schema_shape_lb2.py`、`test_passive_ways_lb2b.py`、`test_variant_range_lb2b.py`、`test_proposal_prompt.py`、`test_prompts.py`（版本快照）；`tests/skillgen/test_proposal*.py`、`test_upgrade_topup.py`。真模型量測：`scripts/llm_model_compare.py`＋`scripts/llm_failure_stats.py`（先照第四節第 8 點換模型）。

- **LB-2b（`skill-proposal/16`）**：被動題目的關鍵字 `ways` 先列 `uses`（條件、觸發）、`makes` 裡做成被動一定超預算的效果不列（`skillgen/proposal_passive.py::unfit_effect_rules`：最省的被動＝係數最高的觸發＋最省的核心效果＋最小數值、不加條件，用 `skill_budget` 實算；組不出合法技能就照列）；`ProposalSubset.tier` 只在 `select_subset` 最後放進去，挑大小時不篩。變奏開放 `range_delta`（`Literal[1, 2]`，照組合器只開加值），`VARIANT_SWAP_FIELDS` 5 項 → 變奏分支 15 支；`proposal_from_skill` 仍把 `range_delta` 當數值拿掉（Mock 提議器不變）。初版重測 Gemma 在 line／cone／ring 上填 `range_delta`（50 次嘗試 26 次被擋），所以變奏說明列出這題「有射程的形狀」（形狀定義有 `range` 參數），回饋附 `RANGE_DELTA_ADVICE`；被動說明要求明寫 `"affects": "self"`、`passive.affects` 回饋附 `PASSIVE_AFFECTS_ADVICE`。判定都不變。
- **LB-2c（`skill-proposal/17`，玩法 PM 4.1.18）**：只收窄送給約束解碼的 schema、改 prompt 與回饋，提議模型與驗證都不變（Mock 不受影響）。① `ProposalRequest.wants_variants`（預設 `False`；現有出題都沒有「要變奏」的資料）為真才有 `variants` 欄位與變奏說明（`prompts/proposal.py::variant_limit`；被動一律 0），`VARIANTS_NONE_ZH` 拿掉。② `self_on_high_ground` 拿掉 `handwritten_only`（定義定案：所在格高度 ≥ 1、飛行不算）。③ 被動題目 `fixed_category` → `schema_shape.fix_category`：頂層只留 `spell` 分支、`category`／`weapon_req` 寫成 `const` spell／any，`fields_note_zh.category` 改 `FIXED_CATEGORY_NOTE_ZH`；被動的 `budget.over` 回饋附 `PASSIVE_BUDGET_ADVICE`（`advise(error, library, skill)`，舉這個稀有度係數最高的觸發，目前是 `every_n_hits（n: 3）`）。④ `RANGE_DELTA_ADVICE` 拿掉「single 並填數字 range」的例子。測試 `tests/llm/test_proposal_lb2c.py`。

本機 LLM 冒煙（手動、少量）：寫一支暫存腳本，`load_llm_config(Path("config/llm.local.toml"))` → `OpenAICompatClient` → `LlmFlashSource(client, naming=client)` → `make_offer`，印 `record.names` 與每個選項的 `skill.name_zh`、`variation.note_zh`（LF-1 報告第 3 節有輸出範例）。

## 六、LF-2：閃現提議少白白重問（`flash-variation/6`）

1. **要幾個**：`want = min(題目選項數, catalog.combinations)`（目錄的（模板, 參數）組合數）。目錄是空的時照舊 `wanted` = 題目選項數、不呼叫。大變化題目仍要 4 個（其中一格之後讓給轉型保底，第 4 個提議用不到；待 PM 決定）。
2. **哪些算錯、會重試**：只有結構問題——不在目錄、類別不存在、參數不在選單、該填沒填（選單 2 個以上）、套不上、格式不對、多餘欄位；而且只為還缺的數量重試（`<request>.count`、schema `maxItems` 都是剩下的數量）。錯誤回饋只列這些。
3. **本地修正**（`llm/flash_repair.py`，不送回模型，記 `flash.repaired.*`）：`category`（模板在目錄裡只對一個類別）、`param_filled`（選單只有一個值）、`param_dropped`（不用填卻填了）、`space`（代號前後空白、參數空字串）、`duplicate`（重複的直接丟）、`note_space`／`note_width`（半形標點與數字轉全形）／`note_period`／`note_cut`（超過 40 字截到最後一個標點，逗號換句號）、`name_space`／`name_width`。
4. **說明只丟說明**：字元、長度、一致性（4-L11）、古風詞、世界觀詞不過 → `flash.note_dropped.<原因>`（`english`、`charset`、`too_long`、`missing_added`、`effect_mismatch`、`archaic`、`world_terms`），變化照收。代碼和修正碼一起放在 `FlashProposalRecord.codes`（被拒絕的在前），`rejected` 只列結構錯誤的模板。
5. **schema**（`prompts/flash.py::flash_schema(catalog, count, major=)`）：每個模板一個 `oneOf` 分支（`template`、`category` 是 `const`，參數只列該模板的選單且必填，沒有選單的分支沒有該欄位），`note_zh` 必填；大變化另有必填 `name_zh`（**不設 `maxLength`**：語法約束會把名稱從中間截斷，實測「焰息・延燒一瞬・雲嶺版・」）。`OpenAICompatClient` 依 `oneof_as_anyof` 改成 `anyOf`。模板超過 `MAX_SCHEMA_BRANCHES`（40）個時退回扁平列舉。
6. **prompt**：`<request>` 多 `categories`（可用類別）、`choices`（每個模板的參數組合數）；`<catalog>` 每列多 `note_words`（`note_words()`：引擎用 `skill_facts` 差集算「這個變化會加上的效果」，每組列前 3 個詞、「／」分隔；有參數時依參數值列）。
7. **命名併進提議**：大變化題目的 `name_zh` 過了 `name_checker`（`naming.check_name`：字數、字元集、禁字、重名、世界觀詞、古風詞；名稱提到的詞要對得上；加上的效果要被名稱或同一項說明提到；「・」最多一個、不在頭尾）就寫進 `texts`，`name_texts` 對它記 `FlashNameRecord(attempts=0)`、不另呼叫；不合格（`flash.name_dropped.*`）、補位的大變化、轉型保底照 LF-1 呼叫 `name_skill`。
8. **詞表**：`content/llm/effect_words.yaml` 的風加「風屬、風系、風勢、山風、陣風」。
9. **統計**：`FlashProposalStats` 多 `naming_calls`、`names_merged`、`notes_dropped`、`repairs`、`mean_round_trips`，`summary_lines` 多四行（`scripts/eval_flash_llm.py` 照印）。
10. **Mock 不受影響**：Mock 回應的項目本來就合格、不帶說明與名稱，也不看 prompt 與 schema；這段沒有任何快照、parity 夾具改變。
11. **本機小樣本**：`docs/phases/PhaseLF-2報告.md` 第 3 節（7 招 × 3 種題目，和調查報告 B.2 同一組）；腳本做法是包一層會記錄的 client 跑 `make_offer(LlmFlashSource(client, naming=client))`，數提議與命名各幾次呼叫。

## 七、LF-3：閃現的名稱與描述進 API 與畫面

1. **API**：`FlashOptionOut.note_zh`（LLM 的一句話描述，純文字、不帶術語標記；沒有＝`None`）、`name_source`（`llm`／`template`）。兩個都由 `api/flash_text.py::option_llm_text(variation, after)` 算：描述再過一次 `clean_note`；名稱只有大變化、轉型帶了 `clean_name` 合格的名稱、**而且** `after.name_zh` 真的等於它才算 `llm`（小變化沿用原名一律 `template`，即使原名是之前閃現的 LLM 名稱）。`run_presenter._pending` 一處填，一輪與大世界共用。
2. **前端**：選項卡在大標下面多一列「名稱 原名 → 新名」（新名稱跟畫面上的原名不同才列，組合式名稱也列），本機模型取的名稱後面一顆紫色「源晶推演」小標記（`LLM_SOURCE_LABEL`，滑過出 `FLASH_LLM_NAME_HINT`）；描述接在名稱列下面一行（`.fc-note`，次要字、最多兩行）。下固定區不動。程式在 `run/flashChoice.ts`（`renamedTo`、`llmNamed`、`noteOf`）、`run/FlashChoiceParts.tsx`（`DiffRows` 的 `rename`、`note`）。
3. **開發頁夾具**：`scripts/export_flash_choice_fixture.py` 多一組 `llm`（點燃斬閃過兩次後第 3 次大變化，**真的出題** `make_offer`，用一個帶 `texts()` 的 `DataOrderSource` 子類掛文字）。`client/dev/flash-choice.html?set=llm`。
4. **實機（大世界）要點**：`pregen/wait` 的 10 秒**從第一次等待算起**，重問不會重新計時；LF-1 的程式（每個大變化另呼叫命名）實測整題超過 10 秒 → 退回組合式名稱。要拍 LLM 版：讀一次角色（開始預先生成）後先等 60～90 秒再送閃現（LF-3 報告第 3 節）。
5. **測試**：`tests/api/test_flash_llm_text_lf3.py`、`client/src/run/lf3FlashLlmText.test.ts`。

## 八、WP-1：許願池（`docs/phases/PhaseWP計畫.md`）

1. **資料流**（同第二節的共用流程，第四個入口）：世界動作 `wish{text}` → `world/wish.py::apply_wish` 組 `WishGenRequest`（鍵＝`input_key("wish/{角色}/{offers_made}", 願望＋選單＋出題用的角色狀態)`）→ `supply(…, WishGen, 退路 WishGen(source="none"), accept)` → API 層 `world_pregen.wish_generator`：`match_wish`（願望只在 `<player_input>`）→ 對到了就 `use_proposer(source.proposer(願望))` 裡 `make_offer(..., pinned_keyword=第 1 個, region_keywords=全部, region=None, llm_max_calls=llm_cards)` → `WishGen{source: llm|partial|none, keywords, offer}` → 日誌 `generated` → 重播 `recorded`。
2. **不預測**：玩家當場打字；`supplier` 收到才排進單一佇列、等最多 10 秒（同閃現）。`prefetch` 不會丟掉 `kind == "wish"` 的暫存（WP-2 的等待提示先排、動作再來拿）。
3. **引擎驗證**（`_acceptor`）：關鍵字在選單、不重複、1～`max_keywords` 個，否則整筆不收 → 動作被拒（`WISH_NO_MATCH_ZH`，不扣錢不算次數）；三選一要過 `checked_offer` 而且每張帶第 1 個關鍵字，否則改成 `partial`（引擎照關鍵字算組合器版），日誌記的是引擎收下的版本。
4. **願望文字**只在動作裡（日誌有）與 prompt 的 `<player_input>`（對關鍵字、提議技能兩步；`make_proposer(player_text=)` → `propose_skill`）；`WishGen` 不存願望，命名步驟不看願望。
5. **Mock**：`mock_wish_client` 用「名稱有任一字出現在願望裡」對關鍵字（「凍」→ 冰凍、「燃」→ 點燃）。Mock 提議器做不出冰凍的完整技能（`literal_error`），所以冰凍願望在 Mock 下是 `partial`；要測 `llm` 版用點燃（`tests/api/test_wish_pregen.py`）。
6. **測試**：`tests/world/test_wish.py`（規則、退路、存檔）、`tests/llm/test_wish_match.py`（`<player_input>`、重試、prompt 快照）、`tests/api/test_wish_pregen.py`（生成函式、佇列、日誌與重播、最小顯示）。
7. **WP-2（API、面板、等待、插隊）**：
   - 請求：`WorldActionRequest` 多 `WishAction`（`{kind:"wish", text?}` 或 `{kind:"wish", keywords:[…]}`；TS 型別的 `keywords` 是必填，文字許願送 `[]`）。
   - 面板：`WorldView.wish`（`api/world_wish_view.py::wish_view`、schema 在 `api/world_wish_schemas.py`）：人在主城才有；`cost`、`refund`、`coins`、`left`、`per_week`、`available`／`blocked_zh`、`llm`、`text_max_chars`、`max_keywords`、`menu`（ID、名稱、`description_zh`）、`title_zh`（許願池物件名）、`speaker`／`line_zh`（守池人物件的頭像與 `note_zh`）。`blocked_zh` 走 `wish_block`：戰鬥中 → 待選閃現 → 待選三選一（和 `world_step` 先擋的字相同）→ `wish_problem`。`llm`＝`store.pregen` 裝上而且 `pregen.enabled()`（文字許願只經預先生成的供應者）；`routes/world.py::_view` 傳 `wish_llm`。
   - `PendingOfferView` 多 `source`（`quest`／`opportunity`／`wish`）、`refund`（都不拿退幾任務幣）。
   - 等待：`PregenWaitRequest.kind` 多 `wish`＋`text`（`keywords` 收但選單許願一律 `none`）。`world_pregen.wish_wait_request` 和動作組同一把鍵（願望先 `strip`）；空白、超過字數、`wish_block` 不過＝`none`（不白打 LLM；等待端點不看戰鬥中，那時動作本來就 409）。
   - **插隊**：`WorldPregen` 不再直接把 `_run` 丟給執行緒池；`_submit` 把 `_Entry`（帶自己的 `Future` 與內容庫視圖）放進 `_urgent`（`URGENT_KINDS`＝`{"wish"}`）或 `_normal` 兩條 deque，再丟一個 `_next` 工作；`_next` 從 `_urgent` 先拿、`set_running_or_notify_cancel` 失敗（被取消）就略過。結果：許願排在所有還沒開始的預測前面、許願之間照先後、正在跑的那一筆不被打斷。測試 `tests/api/test_wish_api_wp2.py::test_wish_jumps_the_queue`、`test_cancelled_wish_is_skipped`。
   - 主城：`wishing_pool`、`pool_keeper` 的 `panel: wish`（`ObjectPanel` 多 `wish`）；WP-3 起前端點這兩個開許願池面板（`world/WishPanel.tsx`；前端的事看 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第一節「許願池面板」列）。
   - Mock 注意：Mock 提議器做不做得出完整技能跟技能種子（角色 ID、賽季種子）有關；要測 `llm` 版用 `alice`＋`make_world()`（同 `test_wish_pregen`）。

## 九、PK-2：挑選模式接上三選一（`skill_pick.yaml` 的 `enabled`，預設開）

1. **開關**：`content/skill_pick.yaml` 的 `enabled`（`SkillPickRules.enabled`；不進數值工坊，工坊沒有布林欄位）。只有傳 `make_offer(..., pick=True)` 的呼叫端生效：原型升級（`progress._level_up`）、原型完整技能（`progress._complete_offer`）、大世界機遇（`solutions._opportunity_offer`、`world_pregen.offer`、`offer_prefetch` 的機遇工作、`opportunity_wait_request` 的鍵）。大世界任務、許願池沒傳，照舊。關掉＝逐字回到 PK-2 前（`tests/roguelite/test_pick_offer_pk2.py::test_switch_off_is_the_old_flow`）。
2. **出題**：`skillgen/pick_offer.py`：先跑原本的產生器（白板或完整技能，不請 LLM）決定格子，每格另外抽（`pick.slot/<格>`，`slot_seeds`／`complete_slot_seeds`，湊到 `top_k` 就停）只收同關鍵字、同種類、同路線的組合器技能；非傷害保底格（`pick.nondamage/<格>`）；打分 `score_candidate(keywords=格子關鍵字)`。手上技能只用 ID＋設計鍵擋（不比名稱：組合式名稱常同名）。
3. **LLM**：`llm_hook.use_picker`／`current_picker`；`trpg.llm.pick.make_offer_picker`（每格 `pick_skill(strict=True)`，一份三選一 10 秒用完剩下的格子不請、候選少於 `min_for_llm` 不請）、`mock_offer_picker(index=)`。`LlmProvider.picker()`、`RunSession.picker`、`cli/run_llm.py` 都裝上。回來的技能結構和候選不同就不收（`same_structure`）。
4. **紀錄**：`OfferTag.pick`（`llm`／`top`，`None` 不寫出）→ API `OfferTagOut.pick`；`LlmRecord` 照 PK-1 的四欄。`WLOG_FORMAT` `trpg-wlog/11`、`WORLD_RULES_VERSION` 34。
5. **加嚴的名稱檢查**：`effect_words.yaml` 的 `strict: true` 詞組（高處、墜落、地形、打擊、形狀、單字風／土石）只在 `strict=True` 看；`consistency.strict_facts` 多 `condition:`、`shape:`。閃現、自由設計命名不受影響（`check_added` 也略過 strict 詞組）。
6. **測試**：`tests/roguelite/test_pick_offer_pk2.py`、`tests/llm/test_pick_pk2.py`；改到 `VICTORY`（`build_fire` 種子 1）。

## 十、PK-3：閃現接上挑選模式（`skill_pick.yaml` 的 `flash_enabled`，預設開）、三選一放寬

1. **開關**：`flash_enabled`（和三選一的 `enabled` 分開；都不進數值工坊）。只有來源會挑選（`skillgen.flash_pick.PickingSource`：`LlmFlashSource`、`RecordedSource`、世界的 `_RecordedFlash`）時 `make_offer` 才走挑選；`UsageSource`（沒開 LLM）照舊。關掉＝逐字回到 LF-2 的提議流程（`tests/llm/test_flash_pick_pk3.py::test_switch_off_is_the_lf2_flow`）。測 LF-2 程式本身的測試用 `tests.engine.helpers.lf2_library()`（開關關掉的內容庫）。
2. **出題**：`flash_offer._Layout.options(())`（沒有提議、沒有文字）＝原本那一份；`_slots` 每格的第一個候選就是它，其餘依同一類的 `ranked` 往下取合格的（`builder.option`，強度下限照舊），同類的格子輪流分、不重複，每格最多 `pool.flash_top_k`（4）；轉型保底固定（只取名）。所以 Mock 挑 0＝沒有 LLM 時那一份。`flash_slots(library, request)` 給測試與比較腳本。
3. **LLM**：`llm/flash_pick.py::pick_variations`（`flash-pick/1`，`prompts/flash_pick.py`）一次回答全部格子（`{"s0": {pick, note_zh, name_zh?}}`；`pick` 是每格的 enum）。描述照 LF-2（不合格只丟）；名稱（大變化、轉型格）照 LF-2 的名稱檢查＋**加嚴詞組只看多字詞**（`consistency.multi_char_strict`；單字風、土、石、斬、劈不看），不合格帶 `<errors>` 重問（最多 `max_retries` 次、10 秒）。連不上或用完＝每格第一個、沒有文字。
4. **紀錄**：`FlashProposalRecord`／`FlashLlmRecord` 多 `picks`（空值不寫出）；`accepted`＝每格選中的變化。重播 `flash_pick.picks_by_key`。世界 `trpg-wlog/12`（`/11` 照讀）、`WORLD_RULES_VERSION` 35；預先生成改呼叫 `LlmFlashSource.prepare`（照開關挑或提議）。
5. **Mock**：`mock_flash_source(pick_index=0)`（`flash_pick.mock_flash_pick_client`，不寫文字）。
6. **三選一（`skillgen/pick_offer.py`）**：`_Maker.level` 給放寬層級（`LEVEL_EXACT`／`RELAXED`／`OFF`／`OFF_RELAXED`）；全部關鍵字＋路線符合的不到 `pool.relax_until`（3）時依序補下一層，扣 `weights.keyword_relaxed_penalty`、`route_off_penalty`；`_cap_off_route`：LLM 挑出的偏離讓一份超過 2 張時改回第一名。`skill_pick.drop_thin`：單薄的不進前 K（全都單薄才照分數）。
7. **組合器**：`composer_parts.build_condition` 不把「第一輪」掛在非傷害效果、不給刻紋掛條件、整招沒有傷害時技能層級不抽第一輪也不給帶刻紋的招抽條件（玩法 PM 4.1.23）；驗證器不改。
8. **測試**：`tests/llm/test_flash_pick_pk3.py`、`tests/roguelite/test_flash_pick_run_pk3.py`、`tests/roguelite/test_pick_offer_pk3.py`、`tests/skillgen/test_composer_odd_pk3.py`。比較腳本 `scripts/pick_slot_stats.py`（每格候選數）、`scripts/flash_pick_compare.py`（閃現 LF-2 vs 挑選），`scripts/pick_compare.py report` 併成 `docs/phases/PhasePK-3比較.md`。

## 十一、SK-1：距離條件、變奏讀出招順序、閃現側變（`skill-proposal/19`）

1. **條件**：`point_blank`（貼身，距離 1）、`long_range`（遠距，距離 ≥ `rules/core.yaml` 的 `far_distance`）；條件表進 schema 就自動進提議 prompt，所以升了 `skill-proposal/18`。`moved_this_turn` 的 `harshness` 改成新的一級 `mild`（`condition_permille.mild`）。
2. **變奏**：`VariantWhen.caster_cast_tag`（本回合施放過帶這個標籤的技能；沒填不輸出）；提議 schema 的 `when` 多一支（`skill-proposal/19`）。
3. **閃現**：13 個新小變化模板（`flash_templates.yaml` 標「SK-1」的那幾個）；`side: true` 的是側變，一次出題最多 `rules.max_side_per_offer`（1）張，由 `flash_offer._Builder.sides` 記數，挑選模式的候選也一樣。利用地面、距離加碼、換觸發的參數放 `Variation.keyword`（表面 ID、條件 ID、觸發時機），LF-2 的目錄照樣列成 `keyword` 選單；`flash-pick/2`、`flash-variation/6` 的 prompt 文字沒改。
4. 測「某個重現案例在舊模板下才成立」的測試用 `tests.engine.helpers.without_sk1_flash()`。

## 十二、SK-2b：新原語進骨架選單、新驗證（`skill-proposal/20`）

1. **骨架**：鉤（`hook`）進位移骨架核心；吸收表面（`absorb_surface`）進打擊、蓄力／終結的附帶與光環的核心；疾病擴散（`contagion`）進打擊、範圍、控場、陷阱的附帶。打擊的附帶是 `harmful_only`，吸收表面靠 `SecondaryRules.harmless_ok` 例外（判斷一律用 `SecondaryRules.admits`，選單說明會寫「… 例外」）。`llm_topic.core_exclude` 沒加它們（LLM 可以出鉤、吸收表面當核心）。
2. **schema**：吸收表面的 `amount`、`dice` 有旋鈕（`when: {gain: …}`），預算器會補；淨化多 `count`（1 或 all）。
3. **驗證**：`cap.distance_condition`（貼身要最大射程 ≥ 2、遠距要 ≥ `far_distance`；只看主動技、固定射程或直線／錐形長度）、`cap.contagion_source`（疾病擴散要在施加燃燒、流血、中毒之後）。
4. 隨機組合器：三個原語仍在 `_HAND_WRITTEN_PRIMITIVES`（一般抽選不抽），只由獨立串流加入（`composer.hook`、`composer.absorb_core`、`composer.absorb`、`composer.contagion`；機率在 `skill_composer.yaml` 的 `structure`）。
5. **SK-3b（`skill-proposal/21`）**：反應事件清單 `proposal/builder.LLM_REACTION_EVENTS`＝`SKILL_REACTION_EVENTS`＋重擲的兩個時機（只能配 `reroll`，驗證器擋）；反應骨架核心多 `reroll`；新觸發 `on_keyword_exploited` 本來就在觸發清單（照 `skill_triggers.yaml` 全部列），llm_hint 改寫。組合器只用獨立串流 `composer.exploit`／`composer.reroll`（`skill_composer.yaml` 的 `exploit_passive_permille`、`reroll_reaction_permille`；題目指定關鍵字時不走）。鎖「LLM 題目樣本」的舊測試用 `tests.engine.helpers.without_sk3b_offers()`，組合器樣本用 `sk3b_streams(lib, 0)`。
