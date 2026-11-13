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
| `llm/config.py` | `LLMConfig`、`load_llm_config(path)`：`config/llm.toml`＋環境變數（`TRPG_LLM_CONFIG` 指另一份、`TRPG_LLM_REASONING_EFFORT`、`TRPG_LLM_GENERATE`…） |
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
| `api/world_pregen.py` | 大世界預先生成：單一背景佇列、只放記憶體、等最多 10 秒（`WAIT_SECONDS`） |
| `world/generated.py` | 世界引擎拿生成內容的介面：請求（`FlashGenRequest`…）、`supply`、`recorded`（重播） |
| `roguelite/llm_hook.py` | 一輪的掛接點（`use_proposer`、`use_flash_source`；`trpg.roguelite` 不能匯入 `trpg.llm`） |
| `skillgen/flash_text.py` | **LF-1**：`VariationText`、`clean_text`／`clean_name`／`clean_note`（引擎端的最後一道文字檢查） |

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
2. **本機模型**：`config/llm.toml` 預設 `localhost:8001`（使用者的 vLLM，可能沒開）；LM Studio 用 `config/llm.local.toml`（gitignored）。Qwen、Gemma 都要 `reasoning_effort = "none"`，否則思考吃光 `max_tokens`、回應是空的（調查報告 B.1）。模型名照 `GET /v1/models`。
3. **Mock 命名撞名**：同一題多個選項用同一個種子時 Mock 給同一個名字，命名會 `name_zh.duplicate` 退回（LF-1 前 `name_offer` 就有這個問題，`name_texts` 已依選項分流種子）。
4. **Mock 命名寫不到橋接加上的效果**（`narrative.missing_added`）：Mock 的 `concept` 只列效果摘要，橋接那一項常退回組合式名稱；測試不要假設每個大變化都命名成功。
5. **描述的一致性檢查很嚴**（實測 `note_zh.missing_added` 常擋）：LF-2 起不合格只丟說明（`flash.note_dropped.*`）、變化照收；測資料流要說明留下來時，仍可用 `monkeypatch` 把 `flash_propose.note_checker` 換成一律通過（`tests/llm/test_flash_texts_lf1.py::lenient_notes`）。
6. **`make_offer` 的呼叫順序**（LF-1 起）：先 `proposed`、再 `texts`、再轉型與補位。改這裡要跑 slow 的 `tests/skillgen/test_refactor_parity.py`（閃現出題的 JSON 雜湊）。
7. **大變化題目的命名延遲**：每個大變化／轉型一次命名呼叫（本機 Qwen 3.8 27B 實測一題 4 個選項約 9 秒），大世界預先生成來不及時整題退回模板（PhaseLF計畫 第 7 節待決 5）。

## 五、相關測試

| 改了什麼 | 跑哪些 |
|---|---|
| 閃現提議、命名、文字 | `tests/llm/test_flash_propose.py`（含 slow）、`test_flash_lf2.py`、`test_flash_texts_lf1.py`、`test_flash_note_*.py`、`test_naming.py`；`tests/skillgen/test_flash_text_lf1.py` |
| 一輪的閃現紀錄 | `tests/roguelite/test_flash_llm_run.py`、`test_flash_texts_run_lf1.py`、`test_save.py` |
| 大世界生成、日誌、重播 | `tests/world/test_generated_content.py`、`test_flash_texts_world_lf1.py`、`test_save.py`、`test_replay.py`；`tests/api/test_world_pregen.py`、`test_world_pregen_schedule.py` |
| prompt 文字 | `tests/llm/test_prompts.py`、`test_prompt_prefix.py` |
| 依賴方向 | `uv run lint-imports`、`tests/test_architecture.py` |

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
