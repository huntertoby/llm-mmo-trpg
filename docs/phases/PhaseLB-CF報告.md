# LB-CF 報告：預設模型改 Gemma（溫度 0.7）

使用者決定（專案 PM 轉，原話「Gemma 溫度 0.7」）。

## 1. 改了什麼

- `config/llm.toml`
  - `model = "swift"` → `model = "google/gemma-4-26b-a4b-qat"`（上一行加註解，註明 LB-CF 與使用者原話）。
  - `reasoning_effort = "none"`：取消註解。註解改寫成：Gemma 在 LM Studio 上不設就會思考（思考吃光 `max_tokens`、回應是空的），用 Gemma 時這行必要；**vLLM 可能不接受 none，換回 vLLM 時要拿掉這行，或用環境變數 `TRPG_LLM_REASONING_EFFORT` 覆寫**。另外補一句：環境變數設空字串**不會**清掉這行（`load_llm_config` 只套用非空的環境變數），所以只能拿掉這行，或覆寫成伺服器接受的值。
  - `temperature = 0.7` 與其他設定都沒動。
- `src/trpg/llm/config.py` 的 `LLMConfig` 預設值（`model="swift"`、`reasoning_effort=None`）**沒動**：規格只說改 `config/llm.toml`。
- `config/llm.local.toml`：**不存在**（主資料夾與 worktree 都沒有；`.gitignore` 的 `*.local.*` 會忽略它）。程式也不會自動讀它，只有設 `TRPG_LLM_CONFIG` 才會用。使用者帳號的環境變數也沒有任何 `TRPG_*`。所以目前**沒有任何東西覆寫 `config/llm.toml`**。

## 2. 測試

改了兩個寫死舊預設值的斷言（`tests/llm/test_client.py`），理由都是「讀的是 `config/llm.toml` 本身，預設模型照使用者決定換了」：

- `test_default_config_file_loads`：`cfg.model == "swift"` → `"google/gemma-4-26b-a4b-qat"`；另外補上 `cfg.reasoning_effort == "none"`、`cfg.temperature == 0.7`。其他斷言都沒放寬。
- `test_ping_success`：`"模型：swift"` → `"模型：google/gemma-4-26b-a4b-qat"`（`trpg llm ping` 不帶 `--config` 時讀預設檔）。

`test_reasoning_effort_only_sent_when_set` 用的是 `client_with(...)` 自己的設定，不讀 `llm.toml`，所以不受影響、沒改。

| 檢查 | 結果 |
|---|---|
| `pytest -n 8 tests/llm tests/api/test_run_llm_api.py tests/cli` | 593 passed |
| `ruff check`、`ruff format --check` | 通過 |
| `mypy`（不帶參數） | Success: no issues found in 1629 source files |
| `lint-imports` | 14 kept, 0 broken |

## 3. 實機

- LM Studio（localhost:8001）：開工前與結束後各查一次 `GET /api/v0/models`，`state=loaded` 的**只有** `google/gemma-4-26b-a4b-qat`。沒有載入或卸載任何模型。
- 伺服器：自己起在 `127.0.0.1:8123`（不用 8000／8001），前端用 `pnpm -C client build`，瀏覽器網址帶 `?mute=1`，視窗 800×600（截圖 1:1，DPR 1）。結束時只結束自己起的兩個伺服器程序（PID 23028、39824）。
- 量測包裝：在暫存資料夾寫了一支啟動器，照 `trpg serve` 的方式建 app，只多兩件事（**沒改專案程式**）：
  1. 包住 `make_proposer` 與 `OpenAICompatClient.complete`，把每個候選與每次呼叫的秒數寫進日誌；
  2. 加一個量測用路由：本場戰鬥讓 AI 代打主角（和模擬同一個 AI），打完照遊戲本身的 `sync` 結算（會裝上這一輪的 LLM 提議器）。手打 8 輪撤離太慢，所以戰鬥用代打；開局、節點選擇、候選生成都走遊戲本身的 API 流程。

### 流程

1. 網頁開局（人類、晶冠城邦、魔導劍、倒地＋點燃、勾選「用本機模型生成升級技能」）→ 回應 `llm: true`、`llm_notice: null`（沒有「連不到本機模型」）。
2. 第 1 場後的升級是**白板三選一**：候選三個都是 `composer`，也沒有任何 LLM 呼叫。這是設計如此：`content/roguelite.yaml` 的 `whiteboard: true` 時，升級的白板候選關掉 LLM 來源（`roguelite/offers.py`）；LLM 只用在第 3、5 場後的**完整技能三選一**（`complete_skill_after: [3, 5]`）。
3. 這一輪第 3 場代打輸了（一輪結束），所以再用和網頁相同的開局請求（`POST /api/runs`，`llm: true`）開了 4 輪（種子 11／22／33／44），推進到完整技能三選一。種子 22 因為我的代打路由在沒有戰鬥時出錯（測試包裝的問題，不是遊戲的問題）中斷。種子 44 的那一輪用網頁讀回來截圖。

### 每個 LLM 候選（日誌 `CANDIDATE`；秒數＝提議＋命名的總時間）

| 一輪（種子） | 題目 | 結果 | 嘗試次數 | 命名 | 秒數 |
|---|---|---|---|---|---|
| 11 | 2 階 稀有 倒地 | 退回（`tier.dual_scaling` ×3） | 3 | — | 6.01 |
| 33 | 2 階 史詩 倒地 | **LLM 生成「重壓之墜」** | 3 | llm（2 次） | 9.27 |
| 33 | 2 階 稀有 倒地＋點燃 | 退回（`value_error`、`variant.v1.budget.over`） | 3 | — | 7.39 |
| 33 | 2 階 稀有 召喚物 | 退回（`budget.weak`） | 3 | — | 9.75 |
| 44 | 2 階 稀有 倒地 | **LLM 生成「裂隙瞬躍」** | 1 | llm（1 次） | 4.95 |
| 44 | 2 階 史詩 倒地＋點燃 | 退回（`range_delta` 用在 ring、`skeleton.secondary`、`budget.weak` 等） | 3 | — | 7.35 |

- 單次模型呼叫 0.49～5.10 秒（每題第一次 3.3～5.1 秒，重試約 1～2 秒）。
- API 回應的來源欄位（`node.offer.tags[].source`）：種子 33 `重壓之墜 = llm`、種子 44 `裂隙瞬躍 = llm`；其他候選是 `pool`／`composer`（退回或本來就不是 LLM 位置）。
- `llm_stats`：種子 33 是 3 題成功 1、種子 44 是 2 題成功 1、種子 11 是 1 題成功 0；退回率都超過 20% 提醒線（`alert: true`）。
- **沒有出現**「連不到本機模型」，也沒有 HTTP 錯誤；所有 `chat/completions` 都是 200。失敗全部是驗證器擋下（雙屬性縮放、預算、骨架附帶原語、`range_delta` 用在沒有數字射程的形狀）。

## 4. 截圖（`docs/phases/LB-CF資料/`）

- `01-開局勾選LLM.jpg`：開局畫面，「用本機模型生成升級技能」已勾。
- `02-第1場後白板升級-組合器.jpg`：第 1 場後的白板升級（設計上不走 LLM）。
- `03-第3場後完整技能三選一.jpg`：種子 44 第 3 場後的完整技能三選一上半。
- `04-LLM候選-裂隙瞬躍.jpg`：同一題的 LLM 候選「裂隙瞬躍」（加深：倒地）。
- `伺服器日誌節錄.txt`：量測日誌（每次呼叫秒數、每個候選的結果、驗證器擋下的原因）。

## 5. 待 PM 決定

1. `docs/dev/上手-LLM.md` 第四節第 2 點還寫「`config/llm.toml` 預設 `localhost:8001`（使用者的 vLLM）；LM Studio 用 `config/llm.local.toml`」，現在預設檔已經是 LM Studio 的 Gemma。規格沒要求改文件，所以我沒改；建議下一段順手更新。
2. `LLMConfig` 的程式預設值仍是 `model="swift"`、`reasoning_effort=None`（只有找不到設定檔時才用到）。照規格「其他設定都不動」沒改；要不要跟著改請 PM 決定。
3. 實機 Gemma 在完整技能題的退回率偏高（6 題成功 2）。這是觀察，不是這段的範圍；照「數值由使用者自己調」沒有做任何量測或調整。
4. 開局後的升級（白板）不走 LLM，要到第 3 場後才看得到 LLM 候選；使用者若期待「第一次升級就看到 LLM 技能」，需要另外確認。
5. 實機時開了 5 輪，存檔留在本機的存檔資料夾（gitignored），照守則沒有刪。
