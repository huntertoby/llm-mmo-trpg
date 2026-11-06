# Phase 6L-2b 報告：預先生成的時機與數量、閃現 note 的古風詞檢查

- 依據：06 6.34.7（預先生成）、#132（第一次閃現提前到新手第 1 步後；預先生成原則）；玩法 PM 決定（經專案 PM 轉達）。
- 分支：worktree 分支，從 main 的 820cd63e（含 6L-2、6F-4c、RT-3、6F-7）開始。沒有 push、沒有合併。

## 1. 逐項做了什麼

### 1.1 大世界機遇：每份三選一最多 1 張請 LLM

- `CandidateRules.llm_max_calls`（`src/trpg/skillgen/candidates.py`）：一份候選最多請 LLM 幾次，0＝不設。
  - 擲到請 LLM 的種類依「加深 → 橋接 → 新方向」先到先用；請滿之後的種類直接走組合器與技能池。
  - 擲骰用的仍是各種類獨立的 `fork`，不消耗其他亂數，組合器的結果不變。
- `make_offer(..., llm_max_calls=0)`（`src/trpg/roguelite/offers.py`）：預設 0，roguelite 照舊（每種候選各擲一次）。快取鍵不受影響（LLM 來源開著時本來就不快取）。
- 大世界的機遇生成函式（`world_pregen.provider_generators` 的 `offer`）傳 `OPPORTUNITY_LLM_CARDS`＝1。
- 世界引擎沒改：LLM 版仍由 `checked_offer` 驗證，日誌記最後給出的三選一，重播讀日誌。

### 1.2 破霧：接主線第 1 步就開始；完成時最多靜默等 2 秒

- 預測（`_story_requests`）：原本只看「下一步」的獎勵；改成看還沒做的步驟裡 **第一個給劇情技能的步驟**。
  - 雲嶺主線第 1 章：破霧在第 2 步（`enter_temple`）。現在接任務（`steps_done`＝0）就開始預先生成。
  - 兩份照舊：現在的等級一份、加上「做到那一步為止每步經驗」後的等級一份（可能升級、換階級）。上限 `STORY_LIMIT`＝2 不變。
  - 角色的關鍵字或等級在路上變了，鍵就換了，照 6L-2 的規則丟掉舊的、排新的。
- 等待（`WorldPregen._await`）：劇情技能的期限改成 `STORY_WAIT_SECONDS`＝2 秒；閃現、機遇維持 `WAIT_SECONDS`＝10 秒。
  - 劇情技能沒有等待提示（6L-2 待決 1），完成那一步的動作最多慢 2 秒，之後給內容版「破霧」。

### 1.3 閃現的 `note_zh`：古風詞檢查

- 新增 `trpg.llm.naming.check_archaic_text(label, body, rules, archaic_ok=…)`，規則照 6L-1 定稿：
  - 「施主」（`archaic.always`）任何區都不行；
  - 區域風格不允許古風詞時（中性、主城、荒原……），27 個 `archaic.terms` 不行；
  - 「訣」（`archaic.suffixes`）只限雲嶺。note 是一句話，不是名稱，所以這裡看 **任何位置**，不只結尾。
- `flash_propose.note_checker` 接上：區域用 `FlashRequest.region`（原技能取得地點的界域，6L-2 追加 1）。
  - 不過的項目帶錯誤碼 `flash.note_zh.archaic` 重試（4-L11 的流程），用盡就照常用模板補。
  - 檢查在 LLM 層（提議被收下之前）；日誌存的是收下的提議，重播不受影響。roguelite 的閃現走同一個來源，也一起檢查（中性區）。
- 盤點「玩家看得到的 LLM 文字」：
  - 技能名稱、`concept`、`cast_flavor`：6L-1 起經 `check_naming`（含 `check_archaic`）。閃現大變化的命名、劇情技能、機遇候選都走這條。
  - 閃現變化的 `note_zh`：這次補上。
  - 沒有其他 LLM 寫給玩家看的技能文字。
- 提示詞沒改，`FLASH_PROMPT_VERSION` 不升。

### 1.4 閃現：戰後就開始預先生成

- `flash_wait_request(..., anywhere=True)`：預測時不看地點。條件照舊：
  - 沒有待選閃現、沒有遭遇（戰鬥中不預測）；
  - 靈感夠；
  - 那招可以閃（`problem_of`：用過、次數沒滿）。
- 出題的輸入不含所在地點（`FlashRequest.region` 是技能的取得區域），所以戰後預測的鍵和回城後出題的鍵相同。測試確認了這點，也確認回城時不會重做。
- 新手第一次閃現（#132）：渡口戰打贏那一刻，就拿到第 1 點靈感，招式也用過了，所以戰果一寫回就開始生成。
- 上限照舊：每角色 `FLASH_LIMIT`＝3 招、全服 `QUEUE_LIMIT`＝12 筆。
- 等待提示端點（`/pregen/wait`）照舊只在城鎮與營火出題時用（不傳 `anywhere`）。

## 2. 12B 量測（新手渡口戰後 → 第一次閃現）

- 環境：LM Studio `http://127.0.0.1:1234/v1`、`gemma-4-12b-it`、`reasoning_effort=none`，一次一個請求。
  - 設定在暫存的 `scratchpad/l2b/llm12b.toml`，用 `TRPG_LLM_CONFIG` 指定。沒改 repo 設定，也沒碰模型伺服器。
- 腳本：`scratchpad/l2b/measure12b.py`（沒進版控）。在行程內用 `create_app`＋`TestClient` 走真的 API，預先生成用真的 `WorldPregen`，時鐘是 `time.monotonic`。
- 走法（腳本推進）：
  1. 建角（主城），傳送到雲嶺，接新手鏈，`travel` 到渡口石階。
  2. 把遭遇設成固定戰 `bandit_raiders`（同 API 測試的 `_as_fixed_fight`），效用 AI 打完。
  3. 戰果寫回的那一刻記為 t0，預先生成從這時開始。
- 戰後到按下閃現，照 **實際時間** 睡，不等佇列。真人節奏是我定的假設：
  - 看戰果 5 秒、選白板 15 秒、走回霧渡鎮 20 秒、葛蘭配點 25 秒、打開閃現 5 秒，合計約 70 秒。
  - 中間照實送 `offer_pick`、`travel mist_ferry`、`allocate` 三個動作。
- 最後照前端的做法：先問 `/pregen/wait`，再送 `flash`，從日誌讀來源。
- 每輪結束先等背景工作做完再開下一輪，確保一次只有一個請求。
- 種子 1 的固定戰沒打贏，略過，所以 6 個種子跑出 5 次。

| 種子 | 戰後到按閃現（秒） | 等待提示 | 等待秒數 | 來源 | 收下的 LLM 變化 | 生成耗時（秒） | 被拒的錯誤碼（每次嘗試） |
|---|---:|---|---:|---|---:|---:|---|
| 0 | 70.1 | ready | 0.0 | llm | 4／4 | 41.1 | — |
| 2 | 72.7 | ready | 0.0 | llm | 4／4 | 4.3 | missing_added → 合格 |
| 3 | 70.4 | ready | 0.0 | llm | 4／4 | 2.5 | — |
| 4 | 72.8 | ready | 0.0 | partial | 3／4（1 個模板補） | 4.1 | missing_added、effect_mismatch、missing_added |
| 5 | 70.4 | ready | 0.0 | llm | 4／4 | 4.0 | effect_mismatch → 合格 |

- **結論**：
  - **5／5 次在按下閃現時已經做好**，等待 0 秒。
  - 4 次是完整 LLM 版，1 次 partial（3 個 LLM 變化＋1 個模板）。LLM 參與比例 5／5，完整 LLM 版 4／5。
  - 生成耗時 2.5～41 秒。41 秒那次是第一輪，可能是模型剛熱身。在 70 秒的回城時間內都做完了。
  - 戰後到回城之間的 `offer_pick`（白板放進備用）、`allocate` 沒有改到出題的鍵，每輪只生成 1 次（`calls`＝1），沒有白做。
  - 新手兩招裡，只有用過的那一招會預先生成（另一招沒上場，不能閃）。
  - 這次的 `note_zh` 古風詞檢查沒有被觸發。被拒的都是 4-L11 的一致性錯誤碼。
- 沒測：玩家 70 秒內就按閃現的情況。依 6L-2 的數字（單次 18～41 秒），30 秒內按的話，偶爾會看到等待提示。

## 3. 版號

| 版號 | 前 | 後 | 理由 |
|---|---|---|---|
| `WORLD_RULES_VERSION` | 12 | **12（不升）** | 照 `save.py` docstring：只有改了 `trpg.world` 裡會讓 **同樣的日誌** 重播出不同結果的程式才加。這次世界引擎沒改。第 1 項改的是 API 層的生成函式與 roguelite `make_offer` 的選填參數（預設不變）；日誌記最後給出的三選一，重播照讀，舊日誌重播結果相同。第 2、4 項是 API 層的時機，第 3 項是 LLM 層的驗證 |
| `trpg-wlog`／`trpg-char` | `/8` | `/8` | 沒有新欄位 |
| roguelite 存檔與規則 | — | 不變 | `llm_max_calls` 預設 0，roguelite 不傳 |
| `FLASH_PROMPT_VERSION` 等 prompt 版號 | — | 不變 | 提示詞沒改 |

- 所以和 6F-4d 不會撞號。

## 4. 檔案

- 修改：
  - `src/trpg/skillgen/candidates.py`（`CandidateRules.llm_max_calls`）
  - `src/trpg/roguelite/offers.py`（`make_offer` 的 `llm_max_calls`）
  - `src/trpg/api/world_pregen.py`（機遇 1 張、劇情技能提早預測與 2 秒、閃現戰後預測）
  - `src/trpg/llm/naming.py`（`check_archaic_text`）、`src/trpg/llm/flash_propose.py`（`note_checker` 接古風詞）
- 新增測試：`tests/api/test_world_pregen_6l2b.py`（5 個）、`tests/llm/test_flash_note_archaic.py`（4 個）。
- 沒碰：skillgen 的利用者白板、`whiteboard_candidates`、梯田內容、人物繪製、前端、API schema（OpenAPI 沒變）。

## 5. 測試

- 新增 9 個：`tests/api/test_world_pregen_6l2b.py` 5 個，`tests/llm/test_flash_note_archaic.py` 4 個：
  - 機遇每份最多 1 張請 LLM；roguelite 不設上限，照舊多張。
  - 破霧在第 1、2 步都預測到，過了那一步就不預測。
  - 破霧最多等 2 秒（假時鐘，2～3 秒內回 `None`）。
  - 閃現在野外戰後就預測，鍵和回城出題相同，回城不重做；靈感不夠或沒用過時不預測。
  - `note_zh` 古風詞：中性區 27 詞、「施主」任何區都不行、「訣」只限雲嶺；不合格的帶錯誤碼重試。
- 重播不呼叫 LLM：沿用 6L-2 的 `test_store_logs_sources_and_replays_without_llm`，這次有跑、通過。日誌格式與世界引擎都沒改。
- 跑過的範圍：
  - `tests/api/test_world_pregen.py`、`test_world_pregen_6l2b.py`、`test_offer_prefetch.py`、`tests/world/test_generated_6l2.py`、`tests/skillgen/test_llm_source.py`、`tests/llm/test_story_skill.py`、`tests/test_architecture.py`：**67 通過**。
  - `tests/roguelite`、`tests/llm`、`tests/api/test_openapi_snapshot.py`：**587 通過**。
- client：vitest 全部 244 檔、2737 個通過；`corepack pnpm -C client build` 結束碼 0。
- 每次 commit 前：ruff check、ruff format --check、mypy src（531 檔）、lint-imports（13 條契約）都通過；`trpg battle --map bandit_lair --seed 62` 加上 `battle replay` 驗證通過。
- 沒跑：全量 `check.py`、CLI 快照、`tests/world` 全部（照規格交 PM）。
- noqa：沒有新增。

## 6. 待 PM 決定

1. **`WORLD_RULES_VERSION` 不升（12）**：判斷理由見第 3 節。另一種做法是在引擎的 `checked_offer` 也擋「超過 1 張 LLM」，但這樣舊日誌重播會變，要升到 13。我採不改引擎（上限只在生成端）。
2. **note 的「訣」看任何位置**，不只結尾：名稱的規則是結尾，但 note 是一句話。採較嚴的做法，中性區的 note 不能出現「訣」字。
3. **閃現戰後預測的成本**：每打完一場，用過的招式的用法統計就會變，鍵跟著換，背景會重做（上限 3 招、全服 12 筆不變）。連續打很多場的玩家，大多數生成會被丟掉；做到一半的請求也中斷不了（6L-2 待決 2）。新手量測裡只有 1 次生成，沒有浪費。要不要改成只在「離城鎮或營火近」或「最後一場之後」才預測，請 PM 決定。
4. **破霧提早預測的命中率**：接任務時的預測，用的是當下的關鍵字與等級。做到第 2 步之前換了裝備或升級，鍵就換了，要重做。如果第 2 步完成時還沒做完，就在 2 秒後給內容版。
5. **量測的真人節奏（70 秒）是假設**，沒有真人實測。
