# Phase 4｜LLM 技能生成（本機模型）

> 設計：`docs/phases/Phase4-LLM技能提議設計.md`（3E-2g，原型 `src/trpg/skillgen/proposal.py`）；`docs/專案計畫.md` Phase 4 段落；世界觀 `docs/玩法PM交接.md` 第 4 節、`docs/art/世界觀美術意見.md`。開發 PM 2026-10-23 起草。

## 0. 使用者決定（2026-10-23，專案 PM 轉達）

使用者原話（逐題）：「1.暫定用『碎界』 是什麼 2.llm 適用這個 wsl 那個地端 3.當然 4.好 5.好」；專案 PM 說明碎界與本機模型的注意事項後：「好」。

| # | 題目 | 決定 |
|---|---|---|
| 1 | 世界觀 | **暫定「碎界」**：源晶核心崩裂，世界碎成漂浮的界域，各界域保留不同文明風格（奇幻、東方、魔導科技、災變、海境）；技能力量＝源晶頻率。只用於 prompt 的語氣與名詞；名稱與描述之後可以重新生成 |
| 2 | 模型 | **使用者的本機模型，不用雲端 API**：`F:\WSL` 的 vLLM 0.27.1，模型 `Swift-Qwen3.8-27B-abliterated-NVFP4`（RTX 5090），OpenAI 相容 API，`base_url http://localhost:<PORT>/v1`，模型名稱 `swift`，API key 任意，上下文 32768，`MAX_SEQS=8`。名稱與描述也用同一個模型 |
| 3 | 數值 | **LLM 只選結構（效果、形狀、條件、觸發），數值一律由預算器補** |
| 4 | 給 LLM 的短說明 | **內容資料加「給 LLM 看的短說明」**（現有 `description_zh` 是給開發者的） |
| 5 | 重試與退回 | **每個候選最多 3 次**；退回順序 隨機組合器 → 技能池 → 工坊選項；**退回率 > 20% 就提醒**（報表與 PM 回報） |

**PM 技術決定**

| 項目 | 決定 |
|---|---|
| 連接埠 | vLLM 的 `settings.ini` 預設 `PORT=8000`，和 `trpg serve` 衝突。專案設定檔的 LLM `base_url` **可設定、預設 `http://localhost:8001/v1`**；請使用者把 `F:\WSL\settings.ini` 的 `PORT` 改為 8001（由專案 PM 轉達，開發端不改 `F:\WSL` 的任何檔案）。`trpg serve` 若已用 8001 則請使用者換其中一邊，設定檔可改 |
| 設定檔 | `config/llm.toml`（或 `pyproject` 外的獨立檔，實作時定）：`base_url`、`model`、`timeout_s`、`max_retries`、`fallback_alert_permille: 200`；環境變數可覆寫（`TRPG_LLM_BASE_URL` 等）；**API key 不進版控** |
| 上下文 | 32k：提議 prompt 依情境縮小 schema（只給相關的原語、形狀、條件），**目標 ≤ 30k token**；以字元數估算並有測試上限 |
| 結構化輸出 | 呼叫時附 vLLM 的 JSON schema 約束（OpenAI 相容 `response_format: {type: json_schema, ...}` 或 `extra_body.guided_json`，實作時以 vLLM 0.27 支援的為準並有退回），再走三道檢查 |
| 測試 | 一律 `MockLLMClient`、不需網路；需要真模型的整合測試標 `@pytest.mark.llm`（預設不跑、也不在 `--full`），寫明啟動方式（`F:\WSL\start.bat`）。模型吃約 88% VRAM，開發時預設用 Mock |
| 確定性 | 生成的 `SkillDef` 寫進 run 紀錄，重播與讀檔不再呼叫 LLM（守則 1、3） |

## 1. 段落與順序（照設計文件 7 節，依決定調整；一次最多 2 個 agent）

| 段 | 內容 | 驗收重點 | 模型 | 前置／平行 |
|---|---|---|---|---|
| 4-L1 | `trpg.llm`：`LLMClient` 介面（`complete(messages, *, json_schema=None) -> str`）、`MockLLMClient`（依序回傳預設回應、記錄收到的 messages）、`OpenAICompatClient`（httpx、`base_url`／`model`／`timeout` 讀設定檔、JSON schema 約束、錯誤分類：連不上／逾時／非 JSON）；設定檔與環境變數；`trpg llm ping` CLI（手動檢查本機模型） | Mock 行為；設定讀取與覆寫；HTTP 用假 transport 測（不需網路）；`@pytest.mark.llm` 的真模型 ping 測試（預設不跑）；依賴方向（`engine` 不匯入 `llm`） | sonnet | 現在派；與 4-L3 平行 |
| 4-L2 | 版本化 prompt（`src/trpg/llm/prompts/`）：系統指令（碎界語氣與名詞表）、資料區、`<player_input>` 包裝與跳脫；prompt 版本號寫進 run 紀錄 | 玩家文字含 `</player_input>`、指令字樣時仍只在資料區；prompt 快照測試 | sonnet | 4-L1 後 |
| 4-L3 | 提議模型正式化：`required_when` 搬進 YAML（取代原型的 `CONDITIONALLY_REQUIRED`）、觸發參數搬進 `skill_triggers.yaml` 的 `params`、**原語／形狀／條件／觸發與參數加給 LLM 的短說明**（`llm_hint`，碎界無關的中性描述）；**提議模型移除數值欄位**（只留結構與列舉），數值交給 4-L5 的預算器 | 模型由 YAML 產生、與現有驗證一致的表格測試；`llm_hint` 全覆蓋測試 | sonnet | 現在派；與 4-L1 平行（只動 `content/`、`skillgen/proposal.py`） |
| 4-L4 | schema 子集：依稀有度、骨架、題目關鍵字篩原語、形狀、條件；prompt＋schema 總長 ≤ 30k token（字元估算）（詳見 3A 節） | 大小上限測試；篩掉的原語提議得到 `union_tag_invalid` | sonnet | 4-L2、4-L3 後 |
| 4-L5 | （詳見 3B 節）重試迴圈＋退回＋**數值補齊**：`propose_skill(client, request) -> (SkillDef, source, attempts)`；結構合格後由預算器（`composer_tuning.tune`）補數值；3 次上限；退回 組合器 → 技能池 → 工坊選項；統計退回率 | Mock「壞 → 壞 → 好」「壞 ×3 → 組合器」；數值一律來自預算器 | **opus** | 4-L4 後 |
| 4-L5b | 小測試後修正（詳見 3D 節）：組合規則進 schema、稀有度篩列舉、錯誤 path、先修可修再回報、骨架資訊進 `available` | 見 3D | **opus** | 4-L5 後 |
| 4-L5c | 第二次小測試後小修（詳見 3E 節）：開關只能 true、列舉去掉不能施加的狀態、估算不算 schema、專屬錯誤代碼、CLI 不出不可能題目 | 見 3E | sonnet | 4-L5b 後 |
| 4-L6 | 接進候選產生器（**另含 3C 節原語多樣性 1～3**）：`llm` 來源、結果寫進 run 紀錄、重播不呼叫 LLM；Mock 失敗時候選仍有 3 個；設定關閉 LLM 時照舊 | 存檔重播一致 | sonnet | 4-L5 後 |
| 4-L7 | 名稱與敘事（同一個本機模型；只寫文字；長度、禁字、碎界名詞；失敗時組合式名稱） | Mock 輸出過長／空字串／含指令字樣 | sonnet | 4-L5 後；可與 4-L6 平行 |
| 4-L8 | 開放更多結構：`followup`（複合）、`reaction`、只能巢狀的原語、代價類欄位 | 往返覆蓋率從 163／217 提高 | sonnet | 4-L6 後 |
| 4-L9 | 真實模型評估腳本（**另含 3C 節的強制與自由測試**）：50 組升級候選的通過率、各錯誤 `code` 的重試次數、退回率（> 20% 警示）、主題一致性抽樣；**需使用者先啟動本機模型** | 只在 PM 指定時跑（`@pytest.mark.llm`／腳本） | sonnet | 4-L8 後；Phase 4 🎯 好玩檢查點前 |

## 2. 4-L1 規格

見上表 4-L1 列。補充：
1. `LLMClient` 為 `Protocol` 或抽象類別；`complete` 同步即可（Phase 4 單人）；回傳原始字串，解析與驗證由呼叫端（4-L5）做。
2. `OpenAICompatClient`：`POST {base_url}/chat/completions`，`model`、`messages`、`temperature`（設定檔）、`max_tokens`（設定檔）、JSON schema 約束；錯誤轉成自訂例外 `LLMUnavailable`／`LLMTimeout`／`LLMBadResponse`（中文訊息，提示「請確認本機模型已用 F:\WSL\start.bat 啟動、連接埠與設定檔一致」）。
3. 設定檔放版控（不含金鑰，`api_key` 預設 `"local"`）；環境變數 `TRPG_LLM_BASE_URL`、`TRPG_LLM_MODEL`、`TRPG_LLM_TIMEOUT_S` 覆寫。
4. `trpg llm ping`：送一則最小請求，印出模型名稱與回應時間；連不上時給上述中文提示（不丟 traceback）。

驗收（4-L1）：pytest（Mock 依序回傳與記錄、設定讀取與環境變數覆寫、OpenAI 相容請求格式與錯誤分類用 `httpx.MockTransport`、CLI ping 成功／失敗訊息）；`@pytest.mark.llm` 真模型 ping（預設不跑；`pyproject.toml` 註冊標記並預設排除）；`ruff`、`mypy`、`test_architecture`。

## 3. 4-L3 規格

見上表 4-L3 列。補充：`llm_hint` 每條一句中文、不含階段編號與欄位名；提議模型去掉數值後，3E-2g 的往返測試改為「結構往返」（數值由測試用的固定預算器補或比對結構）；`proposal.py` 的公開 API 變更寫進報告。驗收：pytest（YAML 產生的模型與現有驗證一致、`required_when` 取代常數、觸發 `params`、`llm_hint` 全覆蓋、提議不含數值欄位）；`ruff`、`mypy`。

## 3A. 4-L4 規格（schema 子集；開發 PM 2026-10-23）

見上表 4-L4 列。目標：給定一個「題目」，產生 **只含相關結構** 的提議模型、JSON schema 與 prompt 的 `available` 資料區，總長控制在本機模型上下文內。數值不在範圍（4-L3 已移除；4-L5 由預算器補）。

1. **題目** `ProposalRequest`（`src/trpg/skillgen/proposal_subset.py`，frozen dataclass）：`tier`、`rarity`、`kind`（`active`／`passive`／`stance`，可省略＝依骨架）、`skeleton`（可省略）、`keywords`（0–2 個，`skill_keywords.yaml` 的 ID）。未知 ID 丟 `ValueError`（中文訊息）。
2. **篩選** `select_subset(library, request) -> ProposalSubset`（純函式、確定性、結果欄位一律排序後的 tuple）。依序：
   - **骨架**：有指定就只用它；沒指定時取 `enabled`、`kinds` 含 `kind`、且不是提議模型排除的骨架（`reaction`／`modifier`／`trap`）的全部骨架。
   - **稀有度**：去掉 `min_rarity` 高於 `rarity` 的原語（形狀、條件若 YAML 有同類欄位也照做）。
   - **骨架範圍**：原語 ⊆ 所選骨架的 `core.primitives` ∪ `secondary.primitives`（被動／架式骨架若沒有 `core`，照現有驗證器對該骨架允許的原語）；形狀 ⊆ 骨架的 `shapes`。
   - **關鍵字**：只看 **專屬** 規則（`grade` 省略者，與候選產生器一致）。`makes`／`uses` 的 `effect` 來源 → 必收原語；`condition` → 必收條件；`trigger` → 必收觸發；`shape` → 必收形狀（都要先通過上面兩道，過不了就不收，記進 `dropped`）。
   - **補足**：必收集合 ＋ 骨架核心原語之外，依 YAML 順序補其他合法原語／條件，直到第 4 點的大小上限為止（先砍條件、再砍附帶原語；核心與必收永不砍）。
   - 沒有任何合法骨架或核心原語時丟 `SubsetError`（4-L5 會退回組合器）。
   - `ProposalSubset` 帶 `skeletons`、`primitives`、`shapes`、`conditions`、`triggers`、`keywords` 與 `dropped: tuple[tuple[str, str], ...]`（ID、中文原因），供報告與除錯。
3. **模型**：`build_proposal_models(library, *, primitives=…, shapes=…, conditions=…, triggers=…, skeletons=…)`——新增後四個篩選參數（預設 `None`＝全部，現有呼叫不變）；`skeleton`、`shape`、`condition`、`trigger` 的 union／`Literal` 只含子集。篩掉的值被提議時在 ① 得到 `union_tag_invalid`（形狀、條件、觸發）或 `literal_error`（骨架），且 `allowed` 只列子集內的值。`build_subset_models(library, subset)` 為便利包裝。
4. **大小**：`trpg.llm.prompts` 加 `estimate_tokens(text) -> int`（保守估算：ASCII 字元 ÷ 3 ＋ 非 ASCII 字元 × 1，向上取整），及 `PROMPT_TOKEN_BUDGET = 30_000`（32768 上下文扣掉 `max_tokens` 2048 與餘裕）。**system ＋ user 訊息 ＋ `json.dumps(schema)` 的估算合計 ≤ 30k**。第 2 點的「補足」用同一個估算決定停在哪裡（`select_subset` 收一個 `token_budget` 參數，預設 `PROMPT_TOKEN_BUDGET` 扣掉固定 prompt 的估算；skillgen 不得匯入 `trpg.llm`，常數以參數傳入或在 skillgen 自己定義同值常數並有測試確認兩者一致）。
5. **`available` 格式**（定 4-L2 待決 #4）：`available_payload(library, subset) -> dict`，結構
   `{"skeletons": [{id, hint}], "primitives": [{id, hint, params: {name: hint}}], "shapes": [{id, hint}], "conditions": [{id, hint}], "triggers": [{id, hint}], "keywords": [{id, name_zh, hint}]}`；
   `hint` 一律用 4-L3 的 `llm_hint`（骨架沒有 `llm_hint` 時用 `description_zh`；若該欄含欄位名或階段編號，補 `llm_hint` 到骨架 YAML，並擴充 4-L3 的覆蓋測試）；不放數值、`min`／`max`。只列子集內的項目，依 ID 排序。
6. **組裝**：`trpg.llm.prompts` 加 `build_proposal_prompt(library, request, *, player_text=None, previous_proposal=None, errors=None) -> ProposalPrompt(messages, json_schema, models, subset)`，內部呼叫 `select_subset`、`build_subset_models`、`available_payload`、`build_skill_proposal_messages`；`request` 區塊放 `tier`、`rarity`、`kind`、`skeleton`、`keywords`（ID ＋ 中文名）。prompt 內容有變就照 4-L2 規則升 `PROMPT_VERSION` 並更新快照。
7. **登記**：`content/llm/world_shattered.yaml` 登記進 `content/registry.py`（4-L2 待決 #1），`trpg content validate`（或現有的全內容驗證測試）會驗到它。
8. **範圍外**：不呼叫 LLM、不寫重試迴圈（4-L5）、不接候選產生器（4-L6）、不改引擎與 `LOG_FORMAT`。

驗收（4-L4）：pytest——
- 大小：**矩陣測試**（每個稀有度 × 每個可用骨架 × 不指定骨架，各配 0／1／2 個關鍵字的固定抽樣，至少 100 組）每組估算 ≤ 30k，並在報告列出最大值與平均；
- 篩選：稀有度擋下的原語、骨架外的原語、篩掉的形狀與條件，提議時分別得到 `union_tag_invalid`／`literal_error` 且 `allowed` 不含它；
- 關鍵字：每個有專屬 `effect` 規則的關鍵字，在至少一個合法骨架下其原語出現在子集中（表格測試）；不合法時進 `dropped`；
- 確定性：同一題目兩次產生的 schema 與 `available` 位元組相同；
- 往返：子集包含某手寫技能所需的全部結構時，`proposal_from_skill` 的提議仍能通過 ①②（抽 10 個可表達的手寫技能）；
- `available` 格式快照、`hint` 不含欄位名；`registry` 含世界觀檔；**新增依賴規則「`trpg.skillgen` 不得匯入 `trpg.llm`」**（`pyproject.toml` import-linter ＋ `tests/test_architecture.py`）。
- `ruff`、`mypy`。報告 `Phase4-L4報告.md`（含大小統計、`dropped` 常見原因、待 PM 決定）。

## 3B. 4-L5 規格（重試＋退回＋數值補齊；開發 PM 2026-10-23）

**真模型實測（4-L5 前，PM 2026-10-23；`F:\WSL` PORT 8001、CTX 32768）**：
- `trpg llm ping` 3.5 秒；`pytest -m llm` 1 過。
- **strict `response_format`（含巢狀 `$ref`／`oneOf`）vLLM 0.27 接受**，輸出一律符合 schema（4-L1 待決 #3 結案）。
- **schema 不佔 prompt token**（只用於約束解碼）：最大題目（rare、不指定骨架、`ignite`）實際 `prompt_tokens` 2,525（4-L4 估算 23,988 是把 schema 算進去了）。上下文不是問題，`token_budget` 不必縮。
- **Qwen3 預設會思考**：`max_tokens` 2048 全被思考用掉，`content` 為空（`finish_reason=length`，約 45 秒）。關掉思考（`chat_template_kwargs: {enable_thinking: false}`）約 6 秒、輸出約 170 token、結構全合格；剩下的錯誤都是規則層：`budget.weak`、`exclusion.no_cooldown_big_area`、`skeleton.core_share`。

規格（模組依賴：`skillgen` 不匯入 `llm`；迴圈放 `trpg.llm`，數值補齊與退回放 `trpg.skillgen`）：

1. **client**：`LLMConfig` 加 `enable_thinking: bool = false`（`config/llm.toml` 寫明；`TRPG_LLM_ENABLE_THINKING` 覆寫），有設定時請求帶 `chat_template_kwargs: {"enable_thinking": …}`。回應若被 ```` ``` ```` 包住或前面有 `<think>…</think>`，解析前去掉（`evaluate_proposal` 前做，函式放 `trpg.llm`）。`finish_reason == "length"` 且內容空 → `LLMBadResponse`（中文訊息提示思考用光輸出）。
2. **預算補數值** `budget_filler(library, *, seed) -> NumberFiller`（`trpg.skillgen`，取代 `minimal_filler` 在正式流程的角色）：先補必填最小值（沿用 `minimal_filler` 的規則），再以提議的效果建立旋鈕（重用隨機組合器建旋鈕的程式，不要另寫一套），呼叫 `composer_tuning.tune` 把預算比例調進 `[low, high]`；確定性（同提議＋同 seed → 同數值）。LLM 給的形狀參數（`range` 等）保留不調。
3. **規則層的數值錯誤由引擎修，不回 LLM**：補數值後跑 `validate_skill`，若錯誤只剩「數值可修」的代碼——`budget.*`、`skeleton.core_share`（調高核心旋鈕／降附帶）、`exclusion.no_cooldown_*`（補最小合法冷卻，冷卻的預算折抵照現有規則）——就在引擎內修一次再驗；修不好才把錯誤回給 LLM。可修代碼清單是資料（模組常數或 YAML），報告列出。AP／冷卻當「便宜／慢熱」旋鈕（4-L3 待決 #2）**這段不做**，記待決，4-L8 再議。
4. **迴圈** `propose_skill(client, library, request, ctx, *, seed, max_attempts=config.max_retries) -> ProposalOutcome`（`trpg.llm.propose`）：每次用 `build_proposal_prompt`（重試時帶 `previous_proposal` 與 `feedback_payload`）→ `client.complete(messages, json_schema=…)` → 清理 → `evaluate_proposal(..., fill=budget_filler(...))` ＋ 第 3 點。`ProposalOutcome`：`skill`、`source`（`llm`／`composer`／`pool`／`workshop`）、`attempts`、每次的錯誤 `code` 清單、每次耗時（秒，只供報表，不進確定性狀態）。
   - `LLMUnavailable` → 立即退回（不再重試）；`LLMTimeout`／`LLMBadResponse` 算一次嘗試。
   - `SubsetError` → 立即退回。
   - 4-L4 待決 #6（巢狀才用的原語出現在頂層選項）：這段 **只靠重試回饋**，報表統計 `skeleton.secondary` 次數，4-L9 再決定是否分開。
5. **退回** `fallback_skill(library, request, ctx, *, seed) -> (SkillDef, source)`（`trpg.skillgen`）：① 隨機組合器帶題目關鍵字（現有 `from_composer` 的做法）② 技能池 ③ 工坊選項推導（`skillgen/options.py`）取第一組可行值；三者都失敗才丟例外。確定性。
6. **統計** `ProposalStats`（累加多個 `ProposalOutcome`）：一次通過率、平均嘗試次數、退回率、各 `code` 次數、各來源次數、平均耗時；退回率 > `fallback_alert_permille` 時 `alert=True`。
7. **CLI** `trpg llm propose [--tier N] [--rarity R] [--skeleton S] [--keyword K]... [--seed N] [-n 次數] [--mock]`：跑 n 個題目（題目由 seed 確定性輪替稀有度／骨架／關鍵字，參數有給就固定），印出每個結果一行（來源、嘗試次數、錯誤 code、耗時、技能名）與 `ProposalStats` 摘要表（中文）。`--mock` 用 `MockLLMClient` 回傳 `proposal_from_skill` 產生的提議（給測試與 demo）。這就是 PM 的「4-L5 後小測試」工具。
8. **範圍外**：不接候選產生器、不寫 run 紀錄（4-L6）；不寫名稱／敘事（4-L7，提議裡的 `name_zh` 照用）。

驗收（4-L5）：pytest（全部用 `MockLLMClient`）——「壞 → 壞 → 好」得 `llm`、`attempts=3`，第 2、3 次的 user 訊息含上一份提議與錯誤；「壞 ×3」→ `composer`；`LLMUnavailable` → 一次就退回；只剩 `budget.weak` 的提議不回 LLM 就通過（Mock 只收到 1 次呼叫）；`exclusion.no_cooldown_*` 由引擎補冷卻；數值一律來自 `budget_filler`（同提議同 seed 兩次結果相同、比例在 `[low, high]`）；回應帶 ```` ``` ```` 或 `<think>` 仍解析；`enable_thinking` 寫進請求（`httpx.MockTransport`）；退回三層各自觸發；`ProposalStats` 與 alert；CLI `--mock -n 3` 輸出快照。另加 `@pytest.mark.llm` 一個真模型測試（1 個題目、結果是 `llm` 或退回皆可，只驗流程不丟例外）。`ruff`、`mypy`、`lint-imports`。報告 `Phase4-L5報告.md`。

## 3C. 原語多樣性（使用者決定，2026-10-23）

使用者問「如何解決模型只選特定詞條、偏遠或模型不偏好的詞條；怎麼驗證每個詞條都有機率被選到」，開發 PM 說明後使用者原話：「好，把題目指定核心原語、輪替選單、run 內配額寫進 4-L6，強制與自由測試寫進 4-L9」。

原則：**結構的多樣性由引擎決定，不交給模型的偏好**；模型只在給定結構下組合、命名。三點都必須確定性（種子決定），結果寫進 run 紀錄，重播不重抽。

**4-L6 加做**
0. **「自然」主題**（玩法決定 #48，10 `6797b09`）：「自然」是主題名稱、不是元素——LLM 生成「自然」主題技能時用毒素、大地、風、治療、藤蔓召喚物、荊棘牆組合；主題詞加在 `content/llm/` 的世界觀或命名資料（不改元素表）。
1. **題目指定核心原語**：`ProposalRequest` 加 `core_primitive`（可省略）。候選產生器出題時，用 run 的種子在「該骨架與稀有度合法的核心原語」中加權抽一個；`select_subset` 收到時只開放它當核心（核心位置的 union 只有它；附帶原語照舊）。抽不到合法組合就省略（退回 4-L4 行為）。
2. **輪替選單**：附帶原語、條件不全給——由種子從合法集合抽一部分（數量為設定值，例如附帶 6 個、條件 4 個；關鍵字必收的照收），並且 `available` 與 schema 的列舉 **順序由種子打亂**（避免模型偏好排在前面的項目）。打亂只影響呈現，驗證結果不變。
3. **run 內配額**：run 狀態記錄已出現在候選中的原語次數；第 1 點的加權對「本 run 沒出現過或出現少」的原語提高權重（權重表放 `content/`，例如 `skill_composer.yaml` 新增區塊；不寫死在程式）。和現有關鍵字的 `behavior_weights` 並存：先依關鍵字定題目，再在題目合法範圍內依配額選核心原語。
- 測試：同種子同 run 狀態得同題目；1000 個種子下每個合法核心原語都被抽到過、分布不偏離設定權重太多（表格測試）；配額讓第二次出現的機率下降；打亂順序不改變 `evaluate_proposal` 結果。

**4-L9 加做（真模型，需使用者開模型）**
4. **強制測試（會不會用）**：每個開放的原語各出 3 題，題目把它設為 `core_primitive`，量通過率（一次通過、重試後通過、退回）與錯誤 `code`。通過率低的原語列出，原因分「說明不清」（改 `llm_hint`）或「格式難」（改 schema／子集）。
5. **自由測試（會不會選）**：不指定 `core_primitive`、依第 2 點輪替選單跑約 300 題，統計每個原語「出現在選單次數、被選次數、選中率」；0 次或低於平均三分之一的列出。以隨機組合器的分布當基準對照。
6. 兩項用平行請求（`MAX_SEQS=8`），報表輸出成表格（Markdown＋CSV），寫進 4-L9 報告；調整建議（`llm_hint`、權重、選單大小）由 PM 決定，不在評估腳本內自動改。

## 3D. 4-L5b 規格（小測試後修正：讓隱藏規則看得見；開發 PM 2026-10-23；opus）

**來由**：4-L5 後真模型小測試（`trpg llm propose -n 10 --seed 0`，見 4.5）一次通過 0%、退回 50%。錯誤分析：
- `value_error` 15 次：`SkillDef`／`EffectSpec` 的 model_validator 裡的組合規則（例：「`charge_through` 的形狀必須是 `ground_tile`」「`charge_through` 以外的效果必須明寫 `affects: self`」），schema 與 `llm_hint` 都沒寫，模型只能靠重試猜；錯誤 `path` 空白。
- `rarity.status` 3 次：狀態的稀有度限制沒反映在 schema 的列舉。
- `skeleton.core`／`core_share`：`available` 的骨架只有一句說明，沒寫核心原語與占比、附帶原語上限。
- `exclusion.stun_single_long_cooldown`：引擎能補冷卻，但不在可修清單；且 **引擎修補 0 次**——現在只有「全部錯誤都可修」時才修。

順序照「schema → 引擎修補 → 題目資訊 → prompt 措辭」：

1. **組合規則進 schema（優先）**：盤點 `SkillDef`／`EffectSpec` 的 model_validator 中「某原語要求特定形狀／位置／其他效果 `affects`」這類規則，能變成資料的搬進 YAML（例如原語的 `requires_shape`、`must_be_first`、`others_affect`），提議模型依此產生：例如帶 `charge_through` 的提議走專用分支（形狀只有 `ground_tile`、其他效果 `affects` 只有 `self`）。若 discriminated union 難以表達「依效果決定形狀」，可改成在 `select_subset`／題目層處理（題目指定核心原語時直接帶入限制），擇一並寫進報告。引擎驗證器改讀同一份資料（唯一來源），行為不變（現有測試全過）。**可先參考工坊 `skillgen/options.py`、`option_conform.py`，它們已經依骨架推導合法選項。**
2. **稀有度篩列舉**：`select_subset` 依 `rarity` 篩掉該稀有度不可用的狀態（及其他有稀有度限制的 ID 列舉），規則來源與 `rarity.status` 驗證相同。
3. **錯誤 path**：`stage: skill` 的錯誤盡量帶 path（至少指出是哪個效果 `effects[i]` 或 `shape`）；做不到的保持空白。
4. **引擎修補改為「先修可修的，再回報其餘」**：補數值後先套用所有可修代碼的修補，再驗證；剩下的錯誤（修補後的）才回給 LLM（4-L5 待決 #5）。可修清單加 `exclusion.stun_single_long_cooldown`（補到規則要求的冷卻）與其他「補冷卻即可」的 `exclusion.*`，以及 `skeleton.secondary_share`（4-L5 待決 #4）。清單仍是資料。
5. **骨架資訊進 `available`**：每個骨架加 `core`（原語清單與最低占比）、`secondary`（清單與最多幾個）、`shapes`；文字用中性中文短句。`PROMPT_VERSION` 升號、快照更新。
6. **重跑小測試**：完成後以 `MockLLMClient` 測試覆蓋上面每一條（例：帶 `charge_through` 的提議只能選 `ground_tile`、普通稀有度的狀態列舉不含高稀有度狀態、混合錯誤時引擎仍先修冷卻）。**真模型由 PM 跑**（不要執行 `-m llm`）。
7. **範圍外**：關鍵字強制（4-L5 待決 #1 → 4-L6）、AP／冷卻旋鈕與無旋鈕結構（#2、#3 → 4-L8／4-L9）。

驗收（4-L5b）：上述測試；所有手寫技能仍通過驗證、`proposal_from_skill` 往返數不下降（163／217 以上）；`ruff`、`mypy`、`lint-imports`；報告 `Phase4-L5b報告.md`（盤點出的規則清單：搬進 YAML 的／留在程式的與理由）。PM 驗收後重跑 `trpg llm propose -n 10 --seed 0` 與另一個種子比較。

## 3E. 4-L5c 規格（第二次小測試後的小修；開發 PM 2026-10-23；sonnet）

**來由**：4-L5b 後真模型小測試（見 4.6）退回率從 50% 降到 10%／33%；剩下的錯誤抓實際訊息後都是小洞：
- `value_error`（14 次）大多是 **只能填 true 的開關欄位**（`explode`、`split_heal` 等）：schema 允許 `false`，模型填 `false` 就被驗證器擋（「explode 只能填 true（不爆骰就省略）」）。
- `budget.unavailable`（5 次）：**沒有預算點數的狀態**（例：`charging` 蓄力）出現在 `apply_status` 的列舉裡，技能不能施加。
- `keyword.required`：技能沒接上關鍵字 → 4-L6 處理（4-L5 待決 #1）。
- CLI 題目輪替會出不可能的題目（例：普通稀有度範圍裡的 `epic／stance／marked`），三層退回都失敗。

1. **只能填 true 的開關**：提議模型中這類欄位只能是 `true`（`Literal[True]`／`const: true`，可省略）；清理步驟另把 `false` 視為省略（雙保險）。清單由資料推導（YAML 參數型別或旗標），不寫死。
2. **列舉只放技能能用的 ID**：`apply_status` 等列舉去掉沒有 `budget_points`（或其他規則禁止技能施加）的狀態；規則來源與 `budget.unavailable` 相同。巢狀位置一樣。
3. **token 估算不算 schema**（4-L5b 待決 #6；真模型實測 schema 不佔 prompt）：`select_subset` 的補足改以「訊息」估算為準（≤ `PROMPT_TOKEN_BUDGET`），schema 另設字元上限（健全性檢查，數值由實作者以現況最大值 ×2 定，報告列出）；4-L4 的大小矩陣測試照新算法更新。
4. **專屬錯誤代碼**（4-L5b 待決 #11）：4-L5b 搬進 YAML 的組合規則與第 1 點的開關，`stage: skill` 的錯誤給穩定代碼（例：`combo.position`、`combo.sole_effect`、`combo.others_affect`、`combo.max_per_skill`、`combo.active_only`、`flag.true_only`）；其他驗證器維持 `value_error`。
5. **CLI 不出不可能的題目**：`trpg llm propose` 的輪替在出題時先檢查可行（`select_subset` 不丟 `SubsetError` 且退回至少一層可行），不可行就依種子換下一組；明確用參數指定的題目照跑。
6. 範圍外：關鍵字強制（4-L6）、旋鈕與 AP（4-L8／4-L9）。

驗收（4-L5c）：Mock 測試覆蓋 1～5；`proposal_from_skill` 往返數不下降；`ruff`、`mypy`、`lint-imports`；`PROMPT_VERSION` 有改 prompt 才升。報告 `Phase4-L5c報告.md`。PM 驗收後重跑種子 0、1 的小測試。

## 3F. 4-L6 規格（接進候選產生器＋原語多樣性；開發 PM 2026-10-29 細化；sonnet，約 1 段，必要時拆 a／b）

> 恢復 Phase 4。上次暫停在 4-L5c（2026-10-23）；之後 Phase 3 後段新增了大量內容（3-47～3R、3T 整理），本節補「受影響的既有功能」。

**受影響的既有功能（盤點）**
- 候選產生器（`trpg.skillgen.candidates`）與一輪的升級三選一、營火：新增 `llm` 來源；`content/roguelite.yaml` 的來源比例。
- run 紀錄與存檔（`trpg-run/7`）：生成的 `SkillDef`、題目（關鍵字、核心原語、選單種子）、`attempts`、來源寫進 run；重播與讀檔不呼叫 LLM。存檔格式有變就遞增並保持舊存檔可讀。
- 設定：`config/llm.toml` 新增「LLM 生成開關」（預設關：沒有本機模型時照舊）；API／前端不改（候選卡片照常顯示，來源標記可選）。
- **Phase 3 後段新內容與 LLM 的界線**（守則 3、4）：形態（`enter_form`、`leave_form`、`in_form`、`form_bonus_permille`）、種族技、定向蓄力只由手寫內容提供 → **LLM 題目不出「形態」關鍵字**（沿用 `KeywordDef.composable: false`），核心原語抽籤排除 `enter_form`／`leave_form`；`clear_surface`、`blow_surface`、`shockwave`、`raise_terrain`／`lower_terrain`（限大地技能元素）照 YAML 旗標與互斥規則決定可不可抽。新增的 `SkillDef.element`（技能元素）納入提議模型（3-54d 已有）並受 `terrain_needs_earth` 規則約束。
- 3T-1 的旋鈕與 change 種類 YAML：預算器補數值走它；提議 schema 的 change 欄位仍不開放（4-L8）。
- 3T-2：提議 JSON 欄位 `layout`（原 `form`）、`PROMPT_VERSION` `skill-proposal/3`。

**交付項目**
1. **`llm` 來源**：候選產生器在開關打開時，依 `content/roguelite.yaml` 設定的比例（初值寫進報告）出 LLM 題目，呼叫 `propose_skill`；失敗（含 3 次重試後退回）時候選仍湊滿 3 個（退回順序照第 0 節決定 5）。開關關閉時行為與現在逐字相同（候選、亂數串流不變；表格測試）。
2. **關鍵字**（4-L5 待決 #1）：LLM 技能必須帶題目關鍵字（`keyword.required` 檢查走同一個驗證器）；做不到算失敗走重試／退回。
3. **3C 節原語多樣性 0～3**：「自然」主題詞、題目指定核心原語（`core_primitive`）、輪替選單（附帶原語、條件抽部分＋順序由種子打亂）、run 內配額（權重表放 `content/skill_composer.yaml`）；測試照 3C 節。
4. **確定性**：題目、選單、打亂全由 run 種子決定；生成結果寫進 run，重播與讀檔不呼叫 LLM（`MockLLMClient` 記錄呼叫次數＝0 的測試）。
5. **退回率提醒**：一輪結束時統計 LLM 退回率，> 20%（`fallback_alert_permille`）寫進 run 摘要與 CLI `trpg run show`。
6. CLI：`trpg run new|auto --llm`（或讀設定），`--llm-mock` 用 Mock 跑完整一輪（CI 用）。
7. 行為一致測試：Mock 回傳合格提議 → 候選出現該技能且數值由預算器補、比例 70～100%；Mock 回傳壞 JSON／不帶關鍵字／形態原語 → 重試後退回、候選仍 3 個；開關關閉＝現狀；存檔往返與重播不呼叫 LLM。
8. **範圍外**：名稱與敘事（4-L7）、開放更多結構（4-L8）、真模型評估（4-L9，需使用者開模型）。
9. 驗收：pytest（skillgen、llm、roguelite、api、content、`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy、lint-imports、一輪 `trpg run auto --llm-mock` 跑完並重播一致。報告 `Phase4-L6報告.md`。

## 3G. 4-L7 規格（名稱與敘事；開發 PM 2026-10-29；sonnet，約 0.6 段）

**受影響的既有功能**：`SkillDef.name_zh` 與 `narrative`（`concept`、`cast_flavor`）、4-L6 的 LLM 候選（目前名稱沿用提議裡的 `name_zh`）、組合器的組合式名稱（退回用）、卡片與戰鬥紀錄、run 紀錄（生成文字寫進 run，重播不呼叫）、`trpg.llm.prompts`（版本號）、`test_player_text.py`（玩家文字不露英文代號）。
1. **命名與敘事 prompt**（同一個本機模型、`LLMClient` 介面）：輸入技能結構（原語、元素、形狀、關鍵字、主題）與碎界語氣／名詞表（`content/llm/`），輸出 `name_zh`（長度上限、全形中文）、`concept`、`cast_flavor`（各有長度上限）；JSON schema 約束。**只寫文字，不能改任何數值或結構**（守則 3）。
2. **檢查**：長度、空字串、禁字（指令字樣、英文代號、`<player_input>` 等標籤、程式碼片段）、和既有技能名稱重複；不過就重試（上限照設定），仍失敗用組合式名稱與模板敘事（現有組合器的做法）。
3. **接點**：4-L6 的 LLM 候選在結構合格後呼叫命名；組合器與技能池的候選不呼叫（照舊）。開關跟 4-L6 同一個 `generate`。結果寫進 run 紀錄，重播與讀檔不呼叫 LLM。
4. 測試一律 `MockLLMClient`：輸出過長／空字串／含指令字樣／含英文代號／重名 → 退回組合式名稱；合格 → 卡片顯示生成名稱與敘事；重播不呼叫。
5. 驗收：pytest（llm、skillgen、roguelite、narrative、api、`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy、lint-imports、一輪 `trpg run auto --llm-mock`。報告 `Phase4-L7報告.md`。

## 3H. 4-L8 規格（開放更多結構；開發 PM 2026-10-29；**opus**，約 1 段，必要時拆 a／b）

**目的**：提高「手寫技能能不能用提議模型表達」的結構往返覆蓋率（4-L3 時 163／217；現在技能 301 招，先重量現況），並讓 LLM 能提議目前被擋掉的結構。
**受影響的既有功能**：`trpg.skillgen.proposal*`（提議模型由 `skill_primitives.yaml` 產生、`proposal_subset` 子集、`proposal_layouts` 版型、`proposal_numbers` 數值拆補）、預算器補數值（3T-1 的旋鈕）、驗證器（同源）、4-L6 候選產生器、`llm_hint`（新開放的部分要有說明）、prompt 版本號、`trpg llm propose` CLI 與 Mock 快照。

1. **先量**：寫一個往返盤點（`proposal_from_skill` 對全部手寫技能），列出不能表達的技能與原因分類（followup、reaction、只能巢狀的原語、代價欄位、修正規則、形態／種族專屬、其他），寫進報告第 1 節。
2. **開放**（依盤點的數量決定順序，每項都要 schema、子集篩選、`llm_hint`、預算器補數值、驗證同源、Mock 測試）：
   - `followup`（複合技能：第二段骨架與觸發時機 `when`，照 06 6.23 的規則）；
   - `reaction`（反應技能，照觸發表 `skill_triggers.yaml`）；
   - 只能巢狀的原語（例如只出現在 zone、陷阱、召喚物等內部的效果）；
   - 代價類欄位（`cost.self_status`、`cost.overdraft`、HP 代價等，照 06 6.5 的上限，數值由預算器補）。
   **不開放**：形態（`enter_form`／`leave_form`／`in_form`／`form_bonus_permille`）、種族技、修正規則的 change 欄位（`modifier` 骨架維持關閉；3T-1 待決 1、7，另案由 PM 決定）。
3. 往返覆蓋率測試：開放後的數字寫進測試下限（不得下降）；每個新開放結構至少 1 個手寫技能往返成功。
4. `PROMPT_VERSION` 遞增；`SCHEMA_CHAR_LIMIT` 與 token 估算照舊（開放後 schema 變大，子集要確保不超過上限；超過時依規則縮小，不超出 30k）。
5. 測試一律 `MockLLMClient`；需要真模型的標 `@pytest.mark.llm`。
6. 驗收：pytest（skillgen、llm、content、roguelite、`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy、lint-imports；`trpg llm propose -n 10 --seed 0`（Mock）輸出正常。報告 `Phase4-L8報告.md`（含盤點表與開放前後覆蓋率）。

## 3I. 4-L8b 規格（4-L8 待決收尾；開發 PM 2026-10-29；sonnet，約 0.5 段）
1. **只能巢狀的效果**（`refund_ap`、`refund_cooldown`、`damage_multiplier`、`self_damage_of_hit` 等）：在 `skill_primitives.yaml` 加旗標（例如 `nested_only: true` 與允許的父結構），提議 schema 與子集照旗標產生，coverage 檢查涵蓋；`ash_harvest`、`blood_sacrifice` 往返成功，覆蓋率下限隨之提高。
2. **AP、冷卻、耐力成為預算旋鈕**（4-L3 待決 #2、4-L8 待決 #6）：補值器可以調高費用讓超預算的結構回到 70～100%（例如 `leap_slam` 類複合技能）；上限照 06 6.5（冷卻最多 5 等）；手寫技能預算不變（比照 3T-1 的前後對照）。
3. **候選產生器也出反應題**（4-L8 待決 #10）：照 `trpg llm propose` 的輪替，反應技的比例放 `content/`（初值寫進報告）。
4. 命名關閉時，敘事也換成模板敘事（4-L8 待決 #8）；`trpg llm propose` 加 `--naming`（#9）。
5. 驗收：pytest（skillgen、llm、content、roguelite、`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy、lint-imports；`trpg llm propose --mock -n 10 --seed 0`、`trpg run auto --llm-mock` 正常。報告 `Phase4-L8b報告.md`。

## 3J. 4-L6b 規格（網頁版 LLM 開關；開發 PM 2026-10-29；sonnet，約 0.4 段；不需要真模型）
**受影響的既有功能**：`POST /api/runs`（新增選填欄位，例如 `llm: true`）、run 狀態（記錄這一輪有沒有開 LLM；存檔已有 `LlmRecord`，格式若變就遞增並保持舊存檔可讀）、前端開新一輪畫面（`StartPicker`）、升級三選一的候選卡（`OfferTagOut.source == "llm"` 可顯示小標記「源晶推演」之類，文字請沿用既有世界觀用語或寫進報告待玩法 PM 確認）、一輪結束摘要（LLM 題數、退回率、> 20% 提醒）。
1. API：開新一輪可選擇開 LLM；伺服器端讀 `config/llm.toml` 的連線設定；**連不到本機模型時不報錯**，該輪自動當作關閉並在回應與畫面上提示一次（例如「本機模型未啟動，這一輪使用一般技能生成」）。連線檢查要有逾時，不能卡住開局。
2. 前端：開新一輪畫面加一個開關（預設關），旁邊用共用浮動卡說明「由本機模型生成升級技能；需要先啟動本機模型」；候選卡顯示 LLM 來源標記；一輪摘要顯示 LLM 統計。彈出卡片照 6.5.1。
3. 測試：API 用 `MockLLMClient`／假的連線失敗（不連 8001）；開關關閉時行為與現在逐字相同；連不到模型時退回一般生成並提示；vitest 涵蓋開關與標記。
4. 驗收：pytest（api、roguelite、llm，`-m "(slow or not slow) and not llm"`、`tests/cli --timeout=3000`）、ruff、format、mypy、vitest、tsc、build、排版煙霧檢查（`runCase(title, {viaRun: true})`）；內建瀏覽器走一次開局（開關打開、沒有模型 → 看到提示並照常開局）。報告 `Phase4-L6b報告.md`。

## 4. 驗收紀錄

### 4.1 4-L1 驗收（2026-10-23）

- PM 合併（無衝突）；ruff、mypy、`tests/llm`＋`test_architecture`＋`tests/cli/test_cli.py` 36 全過；`trpg llm ping` 在模型未啟動時給中文提示（連不上 `http://localhost:8001/v1`，請用 `F:\WSL\start.bat` 啟動、確認連接埠與 `config/llm.toml` 一致），不丟 traceback。`src/trpg/llm/`（`client.py`、`config.py`、`errors.py`）、`config/llm.toml`（`base_url` 8001、`model=swift`、`api_key=local`、`timeout_s=120`、`max_retries=3`、`json_schema_mode=auto`、`fallback_alert_permille=200`）、環境變數 `TRPG_LLM_*`、`TRPG_LLM_CONFIG`；JSON schema 約束先送 `response_format: json_schema`（strict），HTTP 400／422 時退回 `guided_json`；`llm` 標記預設排除（`--full` 也排除）；`httpx` 移到執行期依賴。報告 `Phase4-L1報告.md`。
- 待 PM 決定：#1 client 不做網路層重試（4-L5 處理）、#2 vLLM 回 200 但忽略約束時靠 4-L5 驗證擋下、#4 `httpx` 執行期依賴、#5 `content: null` 視為壞回應 → 接受；#3 strict 與巢狀 `$ref`／`oneOf` 支援度 → 使用者啟動模型後跑 `uv run pytest -m llm` 或 4-L9 驗證；#6 PORT → 已請專案 PM 轉達。

### 4.2 4-L2 驗收（2026-10-23）

- PM 合併（無衝突）；ruff、mypy、`tests/llm`＋`test_architecture`＋`tests/content` 941 全過。`src/trpg/llm/prompts/`（`builder.py`：`PROMPT_VERSION="skill-proposal/1"`、`build_skill_proposal_messages` 回傳 `[system, user]`、`prompt_record` 帶 `prompt_version`＋`system_hash`；`escape.py`：`escape_text`、`wrap_player_input`；`world.py`）；`content/llm/world_shattered.yaml`（碎界語氣、5 界域、名詞表，換世界觀只換此檔）。system 只放固定指令；user 資料區依序 `<request>`、`<available>`、`<previous_proposal>`、`<errors>`、`<player_input>`；跳脫 `&<>` 為實體、移除控制與零寬字元、玩家文字截斷 500 字；11 筆惡意字串測試與 SHA-256 快照（改 prompt 沒改版本號會失敗）。報告 `Phase4-L2報告.md`。
- 待 PM 決定：#1 世界觀檔未登記進 `content/registry.py` → **4-L4 一併登記**；#2 玩家文字 500 字、#3 指令字樣不過濾只隔離、#5 重試回饋放同一則 user 訊息、#6 回饋 JSON 也跳脫 → 接受；#4 `available` 格式 → 4-L4 定。

### 4.3 4-L3 驗收（2026-10-23）

- PM 合併（無衝突）；**`check.py --full` 全過（28 分 5 秒，比前兩次慢很多 → 交接 3.00 列為先查）**；`swamp` 種子 60 `--log-json` ＋ `replay` 一致。`llm_hint` 196 條（原語、形狀、條件、觸發與參數；一句、不含欄位名與世界觀名詞，有測試）；`required_when` 進 YAML（取代 `_filled_by_category`／`CONDITIONALLY_REQUIRED`）；觸發參數進 `skill_triggers.yaml` `params`；提議模型移除 53 個數值欄位；`skillgen/proposal_numbers.py`（`split_numbers`／`apply_numbers`／`fixed_filler`／`minimal_filler`）；`to_skill_def(proposal, ctx, fill)`。結構往返仍 163／217。報告 `Phase4-L3報告.md`（含 4-L5 預算器要補的項目）。
- 待 PM 決定（留給接手的開發 PM 在 4-L4／4-L5 規格處理）：#1 形狀參數（`range`、`size`、`radius`、`jumps`、`jump_range`）保留給 LLM 選 → 暫接受；#2 `ap_cost`／`mana`／`cooldown`／`max_per_round` 全採預設、LLM 無法表達便宜／慢熱 → **建議 4-L5 加 AP／冷卻旋鈕**；#3 `range_delta` 移除、#5 `unless_filled` 舊行為 → 接受；#4 `minimal_filler` 只保證 schema 合法 → 4-L5 換成預算器；#6 `TriggerSpec` 驗證器仍寫死 → 3E-3。

### 4.4 4-L4 驗收（2026-10-23）

- PM 合併（無衝突，`77a234c`）；ruff、format、mypy、lint-imports（7 契約，新增「skillgen 不得匯入 llm」）、`tests/llm`＋`tests/skillgen`＋`tests/content`＋`tests/cli`＋`test_architecture` 1878 全過；`swamp` 種子 60 重播一致。`skillgen/proposal_subset.py`（`ProposalRequest`、`select_subset`、`ProposalSubset`、`SubsetError`、`build_subset_models`、`available_payload`）；`build_proposal_models` 加 `shapes`／`conditions`／`triggers`／`skeletons` 篩選；`llm/prompts/proposal.py` 的 `build_proposal_prompt`；`shared/tokens.py`（`estimate_tokens`、`PROMPT_TOKEN_BUDGET=30000`）；世界觀模型移到 `content/world.py` 並登記進 registry；`PROMPT_VERSION` 不變。大小：138 組可行題目最大 24,999、平均 16,540 估算 token。PM 實測 rare／不指定骨架／`ignite`：41 個原語、11 個骨架、25,475。報告 `Phase4-L4報告.md`。
- 待 PM 決定 → 決定：#1 估算放 `trpg.shared.tokens`、#2 只有核心永不砍（關鍵字原語最後才砍）、#4 緊湊 JSON 估算、#7 `kind` 隨骨架收斂、#8 骨架不可用丟 `SubsetError` → **接受**；#3 補足填滿約 24k、#5 「省略 `primitives`＝不限」的骨架子集偏大 → **4-L9 用真實 tokenizer 與通過率實測後再決定是否縮小**（`token_budget` 可調）；#6 巢狀才用的原語出現在頂層選項 → **4-L5 規格處理**（分開巢狀與頂層可用原語，或靠重試回饋）；#9 `unit_then_tile`／`object_then_tile` 只給手寫技能 → **4-L8 在形狀 YAML 加旗標排除**。

### 4.5 4-L5 驗收與真模型小測試（2026-10-23）

- PM 合併（無衝突，`4f3ebdd`）；ruff、format、mypy、lint-imports（7 契約）、`tests/llm`＋`skillgen`＋`cli`＋`roguelite`＋`test_architecture` 1126 全過。`trpg.llm.propose`（`propose_skill`、`ProposalOutcome`、`ProposalStats`）、`budget_filler`、引擎修補（`REPAIRABLE_CODES`）、三層退回（`FallbackError`）、`enable_thinking=false`、回應清理、`trpg llm propose`。隨機組合器改用共用 `effect_knobs`，400 種子＋關鍵字輸出雜湊不變。手寫結構以預算器補數值：合格 37 → 110／161。報告 `Phase4-L5報告.md`。
- **真模型小測試**（`trpg llm propose -n 10 --seed 0`，126 秒）：一次通過 0%、平均嘗試 2.70、**退回 50%（超過 20% 提醒）**、平均 11.8 秒／題；來源 llm 5、composer 4、workshop 1；錯誤 `value_error` 15、`rarity.status` 3、`reference` 3、`exclusion.stun_single_long_cooldown` 2、`skeleton.core_share` 2；引擎修補 0 次。原因與修正見 **3D 節（4-L5b）**。
- 待 PM 決定 → 決定：#4 `skeleton.secondary_share` 列可修、#5 修補後才回報 → **4-L5b 做**；#1 LLM 技能不強制帶題目關鍵字 → **4-L6 做**（和 3C 節一起）；#2 `budget.over` 難修、#3 無旋鈕結構（召喚、`topple` 等 44／161）→ **4-L8／4-L9 決定**；#6 工坊保底不保證關鍵字、#7 退回欄位來源、#8 CLI 稀有度輪替與 mock 耗時、#9 `chat_template_kwargs` 一律送、#10 `attempts` 計法 → **接受**。

### 4.6 4-L5b 驗收與第二次小測試（2026-10-23）

- PM 合併（無衝突，`1bbbae0`）；ruff、format、mypy、lint-imports、`tests/skillgen`＋`llm`＋`content`＋`engine`＋`cli`＋`api`＋`test_architecture` 4803 全過（合併時發現 `test_budget` 寫死嘲諷 4 點 → 改 3，`81b4c9d`；是 PM 改嘲諷時漏跑的測試）；重播一致。組合規則進 `skill_primitives.yaml`（`position`、`sole_effect`、`others_affect`、`max_per_skill`、`active_only`，19 個原語），驗證器讀同一份；提議頂層以 `form` 區分（`charge_through` 專用型態等）；狀態依稀有度篩；`stage: skill` 帶 path；先修可修再回報；可修清單加 `skeleton.secondary_share` 與補冷卻類 `exclusion.*`；`available` 加型態與骨架核心／附帶／形狀；`PROMPT_VERSION` → `skill-proposal/2`。報告 `Phase4-L5b報告.md`。
- **第二次真模型小測試**：種子 0——一次通過 40%、平均嘗試 1.8、**退回 10%**、8.0 秒／題（4-L5 後同種子：0%、2.7、50%、11.8 秒）；種子 1（9 題，1 題是 CLI 出的不可能題目）——一次通過 33%、2.1、退回 33%、10.7 秒；引擎修補用到 2 次。剩下錯誤與修法見 **3E 節（4-L5c）**。schema 根層 `oneOf` 真模型接受（待決 #1 結案）。
- 待 PM 決定 → 決定：#6 schema 移出 token 估算、#11 專屬錯誤代碼 → **4-L5c 做**；#2、#3、#4、#5、#7、#8、#9、#10、#12、#13、#14 → **接受**。

### 4.7 4-L5c 驗收與第三次小測試（2026-10-23）

- PM 合併（無衝突，`38210a3`）；ruff、format、mypy、lint-imports、`tests/content`＋`skillgen`＋`llm`＋`cli`＋`engine`＋`api`＋`test_architecture` 4855 全過；重播一致。YAML 參數 `true_only`（`damage.explode`、`split_heal`）→ 提議 `Literal[True]`、清理把 `false` 當省略、錯誤代碼 `flag.true_only`；`apply_status` 列舉只放有 `budget_points` 的狀態（排除 `armor_broken`、`charging`、`revealed`、`shielded`、`soul_link`、`time_bomb`、`undying`，由資料推導）；token 估算只算訊息（矩陣最大 6,540、平均 2,640），另設 `SCHEMA_CHAR_LIMIT = 125_000`；`combo.*` 專屬代碼；CLI 輪替先檢查可行。報告 `Phase4-L5c報告.md`。
- **第三次真模型小測試**（各 10 題）：

| | 4-L5 後（種子 0） | 4-L5b 後（種子 0／1） | **4-L5c 後（種子 0／1）** |
|---|---|---|---|
| 一次通過 | 0% | 40%／33% | **40%／60%** |
| 平均嘗試 | 2.70 | 1.80／2.11 | **1.80／1.70** |
| 退回 | 50% | 10%／33% | **20%／20%**（合計 4／20，剛好在 20% 提醒線、未超過） |
| 平均耗時 | 11.8 秒 | 8.0／10.7 秒 | **12.5／8.4 秒**（種子 0 有一題 `json_invalid` 重試花 49.6 秒） |
| 引擎修補 | 0 次 | 2 次 | **9 次** |

  剩下錯誤：`value_error` 8（其他驗證器）、`budget.weak` 5（無旋鈕結構，4-L8）、`skeleton.secondary_share` 4、`reference` 2、`json_invalid` 1。不再派修正段（使用者暫停）；留給 4-L6／4-L8 一併處理。
- 待 PM 決定 → 決定：#1 `PROMPT_VERSION` 不升（模板沒變，`available` 是資料）、#2 選單縮小與輪替 → 4-L6（3C 節）、#3 `SCHEMA_CHAR_LIMIT` 超過走退回、#4 可行性檢查較慢、#5 mock 快照錯誤代碼變化、#6 「最多一個位移原語」仍在程式 → **接受**（#6 留 3E-3／4-L8 搬 YAML）。

**Phase 4 暫停點（2026-10-23，使用者：「讓正在跑的 4-L2、4-L3 做完就停」）**：4-L1～L3 完成，下一段 4-L4（見 `docs/開發PM交接.md` 3.00）。


### 4.8 4-L6 驗收（2026-10-29，開發 PM）
- 報告 `Phase4-L6報告.md`。`llm` 候選來源（`candidates.llm_share_permille` 800‰、主題 `llm_theme_permille` 100‰，初值）；每種候選最多一次 LLM，失敗退回組合器 → 技能池；`keyword.required` 強制；形態關鍵字不出題、`enter_form`／`leave_form` 不進核心抽籤；3C 的 0～3（「自然」主題、`core_primitive`、輪替選單附帶 6／條件 4、`available` 由種子打亂、run 內配額 `skill_composer.yaml` `llm_topic`）；新增 `weapon.incompatible` 檢查；生成結果寫進 run（`trpg-run/8`，/5～/7 可讀）、重播不呼叫；退回率 > 20% 寫進摘要；`trpg run new|auto --llm／--llm-mock`；`config/llm.toml` `generate`（預設 false）；`OfferTagOut.source` 加 `"llm"`。
- 合併後全量（除 llm）：pytest 8593、vitest 1104、mypy、lint-imports、build 全過；`trpg run auto --seed 5 --llm-mock` 跑完（Mock 只能挑手寫技能，7 題全部退回、觸發提醒——Mock 的限制，真模型看 4-L9）。
- 待決 → 決定：#2 schema 列舉順序不打亂（只打亂 `available`）、#3 每種候選只請一次、#4、#6、#7、#8 → 接受，4-L9 看真模型再調；#1 Mock 成功率 → 接受（不另寫 Mock）；#5 網頁開關 → 之後的前端段（API 欄位＋設定畫面）。

### 4.9 4-L7 驗收（2026-10-29，開發 PM）
- 報告 `Phase4-L7報告.md`。命名 prompt `skill-naming/1`；長度上限與禁字在 `content/llm/world_shattered.yaml` `naming`；`trpg.llm.naming`（長度、空字串、字元集、禁字、重名；3 次後退回組合式名稱「元素・骨架」＋模板敘事）；`make_proposer(..., naming=)` 只對 `llm` 來源命名；存檔 `trpg-run/9`（/5～/8 可讀），`LlmRecord` 加 `name_source`／`name_attempts`／`name_codes`。合併後 ruff、mypy、llm／roguelite／skillgen 2391 通過；`trpg run auto --seed 1 --llm-mock` 命名 1 個成功。
- 待決 → 決定：#2 提議 schema 移除 `name_zh`、#8 prompt 版本號寫進 run 紀錄 → 併入 4-L8；#1 去重看不到本輪持有技能、#3 呼叫次數、#4 敘事禁阿拉伯數字、#5 禁字表 → 4-L9 看真模型再調；#6、#7 接受。

### 4.10 4-L8 驗收（2026-10-29，開發 PM）
- 報告 `Phase4-L8報告.md`。往返盤點 `skillgen/proposal_coverage.py`，覆蓋率 241／301 → **264／301**（測試下限 264）；開放代價欄位（每場一次、HP 代價、失手反噬；源力、每場次數、層數、HP 比例由補值器補）、`reaction`、`followup`（第二段骨架／形狀／位移範圍、旋鈕調第二段）；提議 schema 移除 `name_zh`；`LlmRecord` 加 `prompt_version`／`naming_prompt_version`；存檔 `trpg-run/10`（/5～/9 可讀）；`PROMPT_VERSION` `skill-proposal/4`。schema 最大 91,020 字元、prompt 最大 8,069 token。
- 待決 → 決定：#1、#6、#8、#9、#10 → **4-L8b**；#2 HP 代價 200‰、#3 說明搬 YAML、#4 第二段全開、#5 `displace` 沒有 `ring`、#7 傳說源力 → 接受，4-L9 看真模型再調。

### 4.11 4-L8b 驗收（2026-10-29，開發 PM）
- 報告 `Phase4-L8b報告.md`。`skill_primitives.yaml` 新增頂層 `nested_only_effects`（`parents`），往返覆蓋率 264 → **266／301**；AP、冷卻、耐力成為補值器旋鈕（15 階、冷卻上限 5、只用於主動技能；手寫技能預算逐字相同；`leap_slam` 子集 0／10 → 10／10）；候選反應題 `candidates.llm_reaction_permille` 100‰；命名關閉時敘事換模板、`trpg llm propose --naming`。合併後 ruff、mypy、skillgen／llm／roguelite／content 4000 通過。
- 待決 → 決定：#1～#5、#7 接受（初值，4-L9 看真模型再調）；#6 命名開關傳進 schema 組裝 → 4-L9 後的小修；**#8 驗收指令改成 `-m "(slow or not slow) and not llm"`**（`llm` 標記的測試會連 8001 埠），之後的派工 prompt 照此寫。
- **4-L9 需要使用者啟動本機模型**，已請專案 PM 詢問時間（2026-10-29）。

### 4.12 4-L6b 驗收（2026-10-29，開發 PM）
- 報告 `Phase4-L6b報告.md`。`POST /api/runs` 選填 `llm`（預設關）；開局 `GET {base_url}/models` 探測、逾時 3 秒，連不到當作關閉並帶 `llm_notice` 一次；`RunResponse` 加 `llm`／`llm_notice`／`llm_stats`；`trpg.api.llm_source`（`LocalLlmProvider`、`MockLlmProvider`）；前端開關、`NoticeBanner`、候選卡「源晶推演」標記、一輪摘要 LLM 統計；存檔不變（`trpg-run/10`）。合併後全量（除 llm，含 3T-6）：pytest 8732、vitest 1107、mypy、lint-imports、build、重播（lava_crossing 種子 3，角魔）全過。
- 玩法 PM 定案文字：標記「源晶推演」維持；開關改「用本機模型生成升級技能」；提示改「連不到本機模型，這一輪改用一般技能生成。」（開發 PM 已改）。待決 #2～#9 接受（只探測一次、同步生成、讀檔不探測、`generate` 不影響網頁）；`trpg serve --llm-mock`（瀏覽器離線看 LLM 候選）→ 需要時再加。
