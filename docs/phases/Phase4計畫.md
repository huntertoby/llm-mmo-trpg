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
| 4-L4 | schema 子集：依稀有度、骨架、題目關鍵字篩原語、形狀、條件；prompt＋schema 總長 ≤ 30k token（字元估算） | 大小上限測試；篩掉的原語提議得到 `union_tag_invalid` | sonnet | 4-L2、4-L3 後 |
| 4-L5 | 重試迴圈＋退回＋**數值補齊**：`propose_skill(client, request) -> (SkillDef, source, attempts)`；結構合格後由預算器（`composer_tuning.tune`）補數值；3 次上限；退回 組合器 → 技能池 → 工坊選項；統計退回率 | Mock「壞 → 壞 → 好」「壞 ×3 → 組合器」；數值一律來自預算器 | **opus** | 4-L4 後 |
| 4-L6 | 接進候選產生器：`llm` 來源、結果寫進 run 紀錄、重播不呼叫 LLM；Mock 失敗時候選仍有 3 個；設定關閉 LLM 時照舊 | 存檔重播一致 | sonnet | 4-L5 後 |
| 4-L7 | 名稱與敘事（同一個本機模型；只寫文字；長度、禁字、碎界名詞；失敗時組合式名稱） | Mock 輸出過長／空字串／含指令字樣 | sonnet | 4-L5 後；可與 4-L6 平行 |
| 4-L8 | 開放更多結構：`followup`（複合）、`reaction`、只能巢狀的原語、代價類欄位 | 往返覆蓋率從 163／217 提高 | sonnet | 4-L6 後 |
| 4-L9 | 真實模型評估腳本：50 組升級候選的通過率、各錯誤 `code` 的重試次數、退回率（> 20% 警示）、主題一致性抽樣；**需使用者先啟動本機模型** | 只在 PM 指定時跑（`@pytest.mark.llm`／腳本） | sonnet | 4-L8 後；Phase 4 🎯 好玩檢查點前 |

## 2. 4-L1 規格

見上表 4-L1 列。補充：
1. `LLMClient` 為 `Protocol` 或抽象類別；`complete` 同步即可（Phase 4 單人）；回傳原始字串，解析與驗證由呼叫端（4-L5）做。
2. `OpenAICompatClient`：`POST {base_url}/chat/completions`，`model`、`messages`、`temperature`（設定檔）、`max_tokens`（設定檔）、JSON schema 約束；錯誤轉成自訂例外 `LLMUnavailable`／`LLMTimeout`／`LLMBadResponse`（中文訊息，提示「請確認本機模型已用 F:\WSL\start.bat 啟動、連接埠與設定檔一致」）。
3. 設定檔放版控（不含金鑰，`api_key` 預設 `"local"`）；環境變數 `TRPG_LLM_BASE_URL`、`TRPG_LLM_MODEL`、`TRPG_LLM_TIMEOUT_S` 覆寫。
4. `trpg llm ping`：送一則最小請求，印出模型名稱與回應時間；連不上時給上述中文提示（不丟 traceback）。

驗收（4-L1）：pytest（Mock 依序回傳與記錄、設定讀取與環境變數覆寫、OpenAI 相容請求格式與錯誤分類用 `httpx.MockTransport`、CLI ping 成功／失敗訊息）；`@pytest.mark.llm` 真模型 ping（預設不跑；`pyproject.toml` 註冊標記並預設排除）；`ruff`、`mypy`、`test_architecture`。

## 3. 4-L3 規格

見上表 4-L3 列。補充：`llm_hint` 每條一句中文、不含階段編號與欄位名；提議模型去掉數值後，3E-2g 的往返測試改為「結構往返」（數值由測試用的固定預算器補或比對結構）；`proposal.py` 的公開 API 變更寫進報告。驗收：pytest（YAML 產生的模型與現有驗證一致、`required_when` 取代常數、觸發 `params`、`llm_hint` 全覆蓋、提議不含數值欄位）；`ruff`、`mypy`。

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

**Phase 4 暫停點（2026-10-23，使用者：「讓正在跑的 4-L2、4-L3 做完就停」）**：4-L1～L3 完成，下一段 4-L4（見 `docs/開發PM交接.md` 3.00）。

