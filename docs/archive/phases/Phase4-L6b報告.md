# Phase 4-L6b 報告（網頁版 LLM 開關）

規格：`docs/phases/Phase4計畫.md` 3J 節。實作者：sonnet。全部測試用 `MockLLMClient` 或 `httpx.MockTransport` 假的連線失敗；**沒有連 8001 埠**（瀏覽器實測的伺服器用 `TRPG_LLM_BASE_URL=http://127.0.0.1:9/v1` 指到不存在的位址）。存檔格式不變（`trpg-run/10`，`RunState.llm` 與 `llm_log` 4-L6 起就有）。

## 做了什麼

1. **API**
   - `POST /api/runs` 新增選填 `llm: bool`（預設 `false`）。`llm: true` 時伺服器先探測模型：`GET {base_url}/models`，逾時 3 秒（`DEFAULT_PROBE_TIMEOUT_S`），讀 `config/llm.toml`／環境變數。連得到 → `run.llm = true`、裝上提議器；連不到（拒絕連線、逾時、DNS、HTTP 5xx、設定檔壞掉）→ **不報錯**，這一輪當作關閉，回應 `llm_notice = "本機模型未啟動，這一輪使用一般技能生成。"`，照常開局。
   - `RunResponse` 新增 `llm`（這輪有沒有開）、`llm_notice`（只在建立的回應帶出一次，之後的 GET 不再有）、`llm_stats`（題數、成功、退回、退回率千分比、呼叫次數、提醒線、是否超過提醒線、命名數／生成／組合式；與 CLI `llm_lines` 同算法；沒開且沒題目為 `null`）。
   - `src/trpg/api/llm_source.py`：`LlmProvider`（`probe`／`proposer`／`alert_permille`）、`LocalLlmProvider`（真的，可注入 `transport`、`config_path`）、`MockLlmProvider`（測試）。`create_app(llm=…)` 可注入，預設 `LocalLlmProvider()`。`trpg.api` 與 `trpg.roguelite` 的 import-linter 契約不變（提議器經既有的 `roguelite.llm_hook.use_proposer` 掛接）。
   - `RunSession.proposer`：`finish_battle`（戰後升級候選）與 `apply_choice`（營火重骰、前進節點）兩處用 `use_proposer(...)` 包住；讀檔時 `run.llm` 為真就重新裝上提議器（讀檔不探測連線，之後呼叫失敗走既有的 3 次重試與退回）。重播與讀檔不呼叫 LLM 的行為不變（生成的技能存在 run 裡）。
   - 已重新匯出 `client/openapi.json`、`schema.d.ts`。
2. **前端**
   - 開新一輪畫面：「LLM 生成升級技能」勾選（預設關），用共用 `<Hint>` 浮動卡說明「由本機模型生成升級技能；需要先啟動本機模型。沒有啟動時，這一輪照常使用一般技能生成。」；樣式蓋過 `.start-form label` 的直排（同測試模式勾選）。關閉時請求不帶 `llm`（`withLlm`，與以往逐字相同）。
   - 開局後 `RunScreen` 用既有 `NoticeBanner` 顯示 `llm_notice`（12 秒後自動關、可手動關）。
   - 候選卡：`tag.source == "llm"` 顯示「源晶推演」小標記（`<Hint>` 說明「這張技能由本機模型提議，數值由規則補齊。」）。
   - 一輪結束摘要：有 `llm_stats` 時顯示「LLM 生成」面板（題數／成功／退回率／呼叫次數、命名統計、超過提醒線時一行橘色提醒）。
   - 文字與純函式集中在 `client/src/run/llmFlow.ts`（`withLlm`、`isLlmTag`、`llmSummaryLines`）。

## 測試與驗收

- `tests/api/test_run_llm_api.py`（12 個）：預設關閉不探測也不呼叫提議器、候選沒有 `llm` 來源；開關打開＋連得到 → `llm` 為真且無提示、營火重骰經提議器產生候選、統計自洽；連不到 → 當作關閉、提示只在建立時出現一次、不呼叫提議器；沒有設定來源也降級；真的 `LocalLlmProvider` 配假的連線失敗（`ConnectError`）降級；存檔讀回後 `llm` 仍為真並重新裝上提議器；探測：200 → 可用，503／連線逾時／連線失敗／壞設定檔 → 提示。
- `client/src/run/llmFlow.test.ts`（3 個）：關閉時請求不帶 `llm`、標記只在來源為 `llm` 時有、摘要文字與提醒。
- 通過：`ruff check`、`ruff format --check`、`mypy`（794 檔）、`lint-imports`（7 契約）、`tests/api` 318、`tests/test_architecture.py`＋`tests/llm`＋`tests/roguelite/test_llm_run.py` 148、`tests/cli`＋`tests/roguelite` 357（`--timeout=3000`）、vitest 1107、`tsc`、`pnpm build`。（沒有跑完整 `check.py`，依指示。）
- **瀏覽器實測**（伺服器埠 8013，`TRPG_LLM_BASE_URL` 指向 `127.0.0.1:9`，用完以自己的 PID 關閉；視窗已 `resize_window` 回 `desktop`）：
  - 開局：開新一輪 → 選種族／出身／關鍵字 → 勾選 LLM 開關 → 「自動配點並開始」→ 頁面進入一輪，頂端出現「本機模型未啟動，這一輪使用一般技能生成。」，下一場畫面正常。
  - 浮動卡「滑進 → 捲到底 → 釘住 → 關閉」（開關的說明卡）：1600×900 與 800×600 都是：滑過後卡片貼齊觸發元素上方（1600×900：卡底 641.7、觸發元素頂 642.1，無空隙）、滑鼠移入卡片不關閉、點一下 → `pinned`、Esc → 關閉（DOM 卡片數 0）。這張卡只有兩行字（`scrollHeight == clientHeight`），沒有捲動可測；超高內容的捲動屬共用元件（本段未改）。
  - 排版煙霧檢查 `runCase(title, {viaRun: true})`：1600×900、800×600、1600×900＋`shortBottom` 三個情況都「全 PASS」（9 項）。注意：自動化的 `startBattle` 在頁面剛載入時偶爾因關鍵字預覽回應較慢，關鍵字被取消而全部「找不到…」，重載後重跑即過（與本段無關，已在本機伺服器第一次預覽較慢時重現三次）。
- **未能實測**：候選卡的「源晶推演」標記與一輪結束摘要面板（需要有模型或在瀏覽器注入 Mock 提議器才會出現 `source: "llm"`；這兩處只有 API 測試、vitest 純函式與型別檢查覆蓋，沒有在瀏覽器看過）。

## 沒做／範圍外

- 不連真模型（4-L9）；`config/llm.toml` 的 `generate` 預設值不影響網頁（網頁以請求的 `llm` 為準）。
- 沒有 `trpg serve --llm-mock`（瀏覽器目前無法離線看到 `llm` 來源的候選）。

## 待 PM 決定

1. **候選卡來源標記文字**請玩法 PM 定：暫用「源晶推演」（卡片小標記）、說明「這張技能由本機模型提議，數值由規則補齊。」；開關文字「LLM 生成升級技能」、說明文字、連不到時的提示「本機模型未啟動，這一輪使用一般技能生成。」也是暫定（集中在 `client/src/run/llmFlow.ts` 與 `src/trpg/api/llm_source.py`）。
2. **探測方式與逾時**：`GET /models`、3 秒；模型載入中但還沒就緒、回 4xx 都視為「可用」（只有連線失敗、逾時、5xx 才降級）。若要更嚴格（例如真的送一句 chat）請指示。
3. **開局時才探測一次**：開局連得到但之後模型關掉，每次候選走既有的 `LLMUnavailable` 立即退回，不再提示；結束摘要的退回率會反映。要不要中途再提示由 PM 決定。
4. **請求執行時間**：LLM 候選在請求執行緒內同步生成（持有一輪的鎖），本機模型約 8 秒／題，一組候選最多約 3 題，戰後結算那次請求可能要等十幾～數十秒；前端 busy 狀態沿用「載入中」，沒有專用的進度提示。要不要做非同步／進度提示可另排。
5. **讀檔**：讀到 `llm: true` 的存檔時不探測連線，直接裝提議器；模型沒開時走退回（不提示）。
6. **`config/llm.toml` 的 `generate`** 不影響網頁（只看請求欄位）；若要「設定檔預設開」需另決定。
7. **提議器每個 session 一份**（`naming` 的已用名稱記在提議器內），重啟伺服器後讀檔會重建，名稱撞到時由既有的「（二）」處理（同 4-L7 待決 1）。
8. 前端沒有針對開局＋摘要的元件測試（專案沒有 React 元件測試設施），只有純函式 vitest。

## noqa

無新增。
