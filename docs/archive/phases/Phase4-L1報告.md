# Phase 4-L1 報告｜LLMClient、MockLLMClient、本機 OpenAI 相容 client

實作者完成。規格：`docs/phases/Phase4計畫.md` 第 2 節。

## 1. 交付內容

| 檔案 | 內容 |
|---|---|
| `src/trpg/llm/client.py` | `LLMClient`（`Protocol`，`complete(messages, *, json_schema=None) -> str`）、`MockLLMClient`、`OpenAICompatClient`（httpx，同步） |
| `src/trpg/llm/errors.py` | `LLMError` 基底、`LLMUnavailable`（連不上、5xx）、`LLMTimeout`、`LLMBadResponse`（非 JSON、缺 choices、4xx、schema 全被拒）；訊息為中文並附啟動提示 |
| `src/trpg/llm/config.py` | `LLMConfig`（pydantic、frozen、`extra="forbid"`）、`load_llm_config(path, env)` |
| `src/trpg/cli/llm.py` | `trpg llm ping` |
| `config/llm.toml` | 設定檔（進版控，不含金鑰） |
| `tests/llm/test_client.py` | 全部測試（不需網路；HTTP 用 `httpx.MockTransport`） |

`MockLLMClient(responses)`：依序回傳；元素若是 `Exception` 實例則拋出（模擬逾時等）；回應用完拋 `LLMUnavailable`。`calls` 記錄每次的 messages、`schemas` 記錄每次的 `json_schema`。

## 2. 設定檔與環境變數

位置：`config/llm.toml`（專案根目錄）；`TRPG_LLM_CONFIG` 可指定其他路徑（指定的檔案不存在會報錯；預設檔不存在則用內建預設值）。

| 欄位 | 預設 | 說明 |
|---|---|---|
| `base_url` | `http://localhost:8001/v1` | 8001 避開 `trpg serve` 的 8000 |
| `model` | `swift` | |
| `api_key` | `local` | 本機模型任意字串；真金鑰請用環境變數 |
| `timeout_s` | `120.0` | |
| `max_retries` | `3` | 每個候選最多嘗試次數；**client 本身不重試**，留給 4-L5 的重試迴圈 |
| `temperature` | `0.7` | |
| `max_tokens` | `2048` | |
| `json_schema_mode` | `auto` | `auto`／`response_format`／`guided_json`／`none` |
| `fallback_alert_permille` | `200` | 退回率警示線（4-L5／L9 使用） |

環境變數（優先於檔案）：`TRPG_LLM_BASE_URL`、`TRPG_LLM_MODEL`、`TRPG_LLM_TIMEOUT_S`、`TRPG_LLM_API_KEY`、`TRPG_LLM_CONFIG`。

## 3. JSON schema 約束

- 主要寫法：`response_format: {"type": "json_schema", "json_schema": {"name": "response", "schema": <schema>, "strict": true}}`（OpenAI 相容、vLLM 0.27 支援）。
- 退回：伺服器對該寫法回 HTTP 400／422 時，`auto` 模式改用頂層 `guided_json: <schema>`（vLLM 擴充參數）重送，並記住成功的寫法，之後不再先試被拒絕的。兩種都被拒絕 → `LLMBadResponse`。
- `none`：不附約束（只靠 prompt 與事後驗證）。
- 本段未連真模型，哪一種寫法實際可用須由使用者／4-L9 驗證；`auto` 就是為此設計。

## 4. `trpg llm ping`

```
uv run trpg llm ping [--config <path>]
```

送一則最小請求，成功時印出模型名稱、`base_url`、回應時間與回應前 80 字，結束碼 0；連不上／逾時／回應異常時印中文錯誤（含「請確認本機模型已用 F:\WSL\start.bat 啟動、連接埠與設定檔一致」），不丟 traceback，結束碼 1。

## 5. 測試與標記

- `pyproject.toml` 註冊 `llm` 標記；`addopts` 改為 `-m 'not slow and not llm'`；`scripts/check.py --full` 的 `-m ""` 改為 `-m "not llm"`（仍跑 slow、不跑 llm）。
- 真模型 ping：`uv run pytest -m llm tests/llm -q`（先啟動本機模型）。
- 依賴：`httpx` 原本只在 dev 群組，client 屬執行期程式，已移到 `dependencies`（同版本，`uv.lock` 同步調整，`uv lock --check` 通過；沒有新增套件）。
- 依賴方向：`trpg.llm` 只匯入 `trpg.llm`；`trpg.cli.llm` 匯入 `trpg.llm`；`tests/test_architecture.py` 通過。

## 6. 給使用者的啟動說明

1. 把 `F:\WSL\settings.ini` 的 `PORT` 改為 `8001`（避開 `trpg serve` 的 8000；開發端不會動這個檔）。若想維持 8000，改 `config/llm.toml` 的 `base_url`。
2. 執行 `F:\WSL\start.bat` 啟動 vLLM（約吃 88% VRAM，等載入完成）。
3. 回到專案執行 `uv run trpg llm ping`，看到模型名稱與回應時間即成功。
4. 只用環境變數臨時換位址：`$env:TRPG_LLM_BASE_URL="http://localhost:9000/v1"`。

## 7. 待 PM 決定

1. `max_retries` 只存在設定中，client 不做網路層重試（避免和 4-L5 的候選重試疊加）；如要 client 層對 `LLMUnavailable`／`LLMTimeout` 自動重試請指示。
2. `json_schema_mode=auto` 的退回只認 HTTP 400／422；vLLM 若是靜默忽略 `response_format`（200 但無約束），不會退回，仍靠 4-L5 的驗證擋下。
3. `strict: true` 是否被 vLLM 0.27 的 outlines／xgrammar 後端接受、巢狀 `$ref`／`oneOf` 支援度，須真模型驗證（4-L9 或使用者手動 `-m llm`）。
4. `httpx` 由 dev 移到執行期依賴（無新套件）。
5. 開啟推理（thinking）的模型若回 `content: null`，目前視為 `LLMBadResponse`；是否要讀 `reasoning_content` 待真模型確認。
