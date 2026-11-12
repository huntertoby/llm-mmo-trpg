# Phase MAC-2 報告：LM Studio MLX 相容

日期：2026-11-06。環境：Mac mini（arm64、16 GB）、LM Studio（MLX 引擎）＋ `gemma-4-12b-it`（4bit）、`config/llm.local.toml`（gitignored）。

## 根因（PM 驗證＋本段補充實測）

- LM Studio MLX 對帶 `oneOf` 的 `response_format` 回 HTTP 400（`oneOf constraints are not supported. Enable 'coerce_one_of'…`），auto 模式退到 `guided_json`，LM Studio 回 200 但**完全忽略**約束 → 模型自由發揮 → pydantic 全炸、100% 退回組合器。
- 本段補充實測（2026-11-06，`scratchpad/probe_oneof*.py`，未進專案）：MLX **只在證明不了各分支互斥時**才拒絕 `oneOf`——頂層 `oneOf` 兩分支都允許額外欄位、或分支相同 → 400；分支帶 `const` 判別欄位且 `additionalProperties: false` → 200；巢狀在 `properties` 下的 `oneOf` → 200。提議 schema（頂層 `oneOf`＋`$defs` 內 30 處 `oneOf`，分支不帶 `additionalProperties: false`）屬於前者；整份遞迴改成 `anyOf` 後 → 200，輸出符合結構。

## 做了什麼

| 項目 | 內容 | 檔案 |
|---|---|---|
| 1. `oneOf` → `anyOf` 改寫 | `LLMConfig.oneof_as_anyof: bool = True`（docstring 寫原因）；`rewrite_oneof_as_anyof()` 遞迴走過所有 dict／list（`properties`、`items`、`$defs`、`allOf`、`anyOf`…），只改鍵名、其他鍵不動、回傳新 dict（原 dict 不碰）；同層已有 `anyOf` 時不動該層的 `oneOf`（避免鍵相撞，pydantic 不會產生這種 schema）。`_body` 的 `response_format` 與 `guided_json` 兩種寫法都經 `_prepare_schema` 套用 | `src/trpg/llm/config.py`、`src/trpg/llm/client.py` |
| 2. 退回 `guided_json` 的警告 | client 原本沒有 logger／回呼，新增 `logging.getLogger("trpg.llm")`；auto 模式第一次被拒退回下一種寫法時發一則 warning：「伺服器拒絕 response_format（HTTP 400），已退回 guided_json；LM Studio 等伺服器會忽略 guided_json，輸出可能不符 schema」，同一個 client 只發一次。`_SchemaRejectedError` 帶 `status`。CLI 沒設 logging 時由 Python 的 lastResort handler 印到 stderr（實測有印） | `src/trpg/llm/client.py` |
| 3. `accepted_schema_mode` | `OpenAICompatClient` 新屬性：伺服器接受的寫法（`response_format`／`guided_json`／`None`）。`_post` 改為回傳 `httpx.Response`，`complete` 在 2xx 時先記住寫法再解析內容——伺服器接受寫法與回覆是否解析得了分開（guided_json 被忽略時模型自由發揮、回覆解析失敗，不能誤報成「都不接受」） | `src/trpg/llm/client.py` |
| 4. `trpg llm ping` 印 schema 寫法 | 純文字 ping 成功後再帶 `PING_SCHEMA` 呼叫一次，印「schema 寫法：response_format／guided_json／都不接受」（`json_schema_mode = "none"` 時印 `none`；回覆解析失敗時加註「（回覆解析失敗：…）」）。`PING_SCHEMA` 是**頂層 `oneOf`、兩個會重疊的分支**（與提議 schema 同類，見根因），才測得出改寫是否生效 | `src/trpg/cli/llm.py` |
| 5. 單元測試 | 11 個 mock 測試（`httpx.MockTransport`，沿用 `tests/llm/test_client.py` 的寫法，沒改那個檔）：改寫函式（巢狀、其他鍵不變、原 dict 未改、同層已有 anyOf）、request body 兩種寫法都無 `oneOf`、`oneof_as_anyof=False` 不改寫、400 退回時 warning 只一次、接受時無 warning、全拒時一次 warning、ping 印三種寫法＋解析失敗註記 | `tests/llm/test_schema_rewrite.py`（新） |

未改：`src/trpg/llm/errors.py`、`tests/llm/test_client.py`、`tests/llm/test_propose.py`、`config/llm.toml`、`docs/部署說明.md`（MAC-1 agent 的檔；要補的文字在下方「待 PM 決定」）。引擎隔離不變（`lint-imports` 13 kept）。

## Mock 測試與靜態檢查

| 指令 | 結果 |
|---|---|
| `uv run ruff check src/trpg/llm src/trpg/cli tests/llm` | 通過 |
| `uv run ruff format --check src/trpg/llm src/trpg/cli tests/llm` | 61 檔已格式化 |
| `uv run mypy src/trpg/llm src/trpg/cli tests/llm/test_schema_rewrite.py` | 0 錯誤（42 檔） |
| `uv run lint-imports` | 13 kept, 0 broken |
| `uv run pytest -q tests/llm tests/cli -x -n 4`（不含 `-m llm`） | 510 passed |

## 真模型驗收（LM Studio MLX、gemma-4-12b-it、`config/llm.local.toml`）

| 項目 | 結果 |
|---|---|
| `trpg llm ping`（改寫開） | 0.5 秒、「schema 寫法：response_format」 |
| `trpg llm ping`（暫存設定 `oneof_as_anyof = false`） | stderr 先印退回警告，「schema 寫法：guided_json」 |
| `uv run pytest -q tests/llm -m llm -n 0 --timeout=900` | 3 passed、101.6 秒（propose_one 53.7 秒、upgrade_item 41.5 秒、ping 2.1 秒） |
| `trpg llm propose -n 10 --seed 1` | 10 題、總耗時 621 秒；**一次通過 2（20%）、重試通過 4（40%）、退回 4（40%：composer 3、workshop 1）**；每題秒數 p50 58.7、max 112.0（min 16.1）；平均嘗試 2.30；來源 llm 6／composer 3／workshop 1 |

失敗原因分類（錯誤碼計數，10 題共 23 次嘗試）：

| 類別 | 錯誤碼 | 次數 | 判定 |
|---|---|---|---|
| 語意規則（pydantic 自訂驗證器 `ValueError`） | `value_error` | 9 | 模型品質，不修（第 1 題連 3 次×2 個 → composer） |
| 骨架規則 | `skeleton.secondary_count` 3、`skeleton.secondary` 1、`skeleton.secondary_share` 1 | 5 | 模型品質（第 4 題連 3 次 → composer） |
| 關鍵字 | `keyword.required` 3 | 3 | 模型品質（第 9 題 `collision` 連 3 次沒帶到 → workshop） |
| 參照 | `reference` 3 | 3 | 模型品質（第 7 題連 3 次 → composer） |
| 預算 | `budget.weak` 1 | 1 | 模型品質（第 8 題第 2 次，第 3 次通過） |
| **結構／schema／解析** | `missing`、`literal_error`、`union_tag_invalid`、`json_invalid`… | **0** | 本段該修的類別：沒有出現，schema 約束已被 MLX 強制 |

改寫前（PM 驗證）是 100% 退回組合器；改寫後退回 40%（仍超過 `fallback_alert_permille = 200` 的提醒線）。stderr 沒有任何退回 `guided_json` 的警告（整場都用 `response_format`）。引擎修補 `exclusion.no_cooldown_big_area` 4 次。

註：驗收中途 LM Studio 把模型閒置卸載了（`lms ps` 空、API 回「No models loaded」）；用 `lms load google/gemma-4-12b --identifier gemma-4-12b-it -y --ttl 7200 -c 16384` 載回（識別字與設定檔一致）。`-m llm` 的 `-p no:xdist` 與 `addopts` 的 `--dist loadgroup` 衝突，改用 `-n 0`。

## Commit 清單

1. `ec8dea2c` feat(llm): rewrite oneOf to anyOf for LM Studio MLX, warn on guided_json fallback (MAC-2)
2. `db451a3e` fix(llm): ping probe uses overlapping top-level oneOf; keep accepted mode even if reply unparsable (MAC-2)
3. （本報告）

## 待 PM 決定

1. **`config/llm.toml` 要補的文字**（放在 `enable_thinking` 之後；我不能改該檔）：

   ```toml
   # LM Studio 上的 Gemma 不認 chat_template_kwargs，要 reasoning_effort = "none" 才不思考；
   # vLLM 不一定接受 none，所以預設不送（註解掉）。環境變數 TRPG_LLM_REASONING_EFFORT 可覆寫。
   # reasoning_effort = "none"
   # MAC-2：送出前把 JSON schema 的 oneOf 改成 anyOf。LM Studio 的 MLX 引擎不支援（證明不了分支互斥的）
   # oneOf：response_format 回 400、退到 guided_json 又被整個忽略。專案只用 oneOf 做判別式 union，
   # 改 anyOf 語意相同（vLLM 的 xgrammar 本來就這樣近似）。只有在伺服器要求嚴格 oneOf 時才關。
   oneof_as_anyof = true
   ```

   另建議在檔頭的環境變數清單加 `TRPG_LLM_REASONING_EFFORT`（`config.py` 已支援，檔頭漏列）。

2. **`docs/部署說明.md` 要補的 LM Studio 段落**（第 3 節 macOS 或「本機模型」處）：

   > **LM Studio（macOS，MLX 引擎）**：載入模型後把 `config/llm.toml` 的 `base_url` 改成 `http://127.0.0.1:1234/v1`、`model` 改成 LM Studio 顯示的識別字（例 `gemma-4-12b-it`），Gemma 要加 `reasoning_effort = "none"`（不然會把 `max_tokens` 用在思考上）。不想動進版控的檔就複製成 `config/llm.local.toml`（gitignored）再 `TRPG_LLM_CONFIG=config/llm.local.toml`。用 `uv run trpg llm ping` 確認：最後一行要是「schema 寫法：response_format」；若印「guided_json」代表伺服器拒絕了 schema、LM Studio 會忽略約束（確認 `oneof_as_anyof` 沒被關掉）。LM Studio 會把閒置的模型卸載，長時間驗收前用 `lms load <model> --identifier <識別字> --ttl 7200` 載入。

3. **`budget.weak` 等驗證退回是否該調 prompt**：本次 `budget.weak` 只出現 1 次（且重試後通過），不是主因；主因是 `value_error`（9）與骨架規則（5）、`reference`（3）、`keyword.required`（3）。這些都是模型自由度內的品質問題（schema 擋不住的語意規則），本段沒改 prompt。若 PM 要降退回率，建議下一段先看 `value_error` 的具體訊息分布（本次只記了錯誤碼），再決定是否在 prompt 補規則提示；gemma-4-12b 4bit 的 p50 約 59 秒／題，提示加長會再拉長時間。

4. **保守做法**：
   - `oneof_as_anyof` 沒有加環境變數覆寫（`_ENV_OVERRIDES`），需要時再加。
   - 改寫只改鍵名，不做 `coerce_one_of` 以外的任何近似；同層同時有 `oneOf` 與 `anyOf` 時不動（pydantic 不會產生）。
   - warning 走 `logging`（`trpg.llm`），沒有加回呼參數；`trpg run`／`serve` 若想把它顯示給玩家要另外接 logging。
   - ping 的 schema 探測失敗（回覆解析失敗）不改變回傳碼（仍 0），只在輸出加註；探測遇到非 `LLMBadResponse` 的錯誤（逾時、連不上）則回 1。
   - 探測結果「只有證明不了互斥的 `oneOf` 才被拒」是對這版 LM Studio（2026-11-06）的觀察，未查 LM Studio 原始碼；`PING_SCHEMA` 用了會被拒的形狀，之後 LM Studio 若改行為，ping 仍會如實反映。
