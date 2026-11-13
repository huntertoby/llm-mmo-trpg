# Phase LF-3 報告｜閃現的 LLM 名稱與描述：API 與前端

> 實作 agent，2026-11-13。規格 `docs/phases/PhaseLF計畫.md` 第 5 節。依據 main `d0f18f65`（FL-1b 合併後），交件前已 merge main `247dd6f6`（FL-1f、LF-2）。
> 使用者核可（專案 PM 轉達）：「都按照建議」。

## 1. 做了什麼

| 項目 | 做法 | 檔案 |
|---|---|---|
| API 新欄位（只加不改） | `FlashOptionOut.note_zh: str \| None = None`、`name_source: Literal["llm", "template"] = "template"` | `src/trpg/api/run_schemas.py` |
| 算法 | `option_llm_text(variation, after)`：描述照樣過 `clean_note`（守則 3：變化上的文字出題時已檢查，這裡再擋一次，例如手改存檔）；名稱只有大變化／轉型帶 `clean_name` 合格的名稱，**而且** 套用後的技能名稱真的是它，才算 `llm` | `src/trpg/api/flash_text.py` |
| 填欄位 | `_pending` 一處，一輪與大世界共用（`world_growth_view` 用同一個 `pending_flash_out`） | `src/trpg/api/run_presenter.py` |
| OpenAPI 與前端型別 | `scripts/export_openapi.py`、`pnpm gen:api` 重產；merge main 後再產一次（沒有再變） | `client/openapi.json`、`client/src/api/schema.d.ts` |
| 選項卡 | 大標下面：①「名稱 原名 → 新名」一列（新名稱與畫面上的原名不同才列；組合式名稱也列），新名稱主文字色粗字、無底無框；本機模型取的名稱後面一顆紫色小膠囊「源晶推演」（沿用候選卡的 LLM 標記字），滑過出說明卡；② LLM 的一句話描述接在名稱列下面（整列寬、次要字 L3、最多兩行）。都沒有就不佔位 | `client/src/run/flashChoice.ts`（`renamedTo`、`llmNamed`、`noteOf`、定稿字）、`client/src/run/FlashChoiceParts.tsx`（`DiffRows` 的 `rename`、`note`）、`client/src/screens/RunFlashPending.tsx`、`client/src/styles/flash-choice.css`（`.fc-now.name`、`.fc-src`、`.fc-note`） |
| 下固定區 | 不動（大標＋一句話＋確定照 FL-1b；描述不進下固定區，免得高度跳） | — |
| 開發頁夾具 | 新增 `llm` 組：點燃斬閃過兩次後第 3 次大變化，`make_offer` **真的出題**，文字由帶 `texts()` 的來源掛上（引擎 `clean_text`）；第 3 個只有描述、名稱是組合式。既有四組只多兩個欄位（`template`／`null`），字不變 | `scripts/export_flash_choice_fixture.py`、`client/src/dev/fixtures/flashChoice.json`、`client/src/dev/flashChoiceGallery.tsx`（註解） |
| 技能卡、技能庫的名稱（規格 5.3） | 查過前後端：名稱一律讀技能定義的 `name_zh`，沒有地方自己組「{前綴}・{原名}」，不用改 | — |
| 等待提示 | 沿用 6L-2，不動 | — |

沒碰：`content/flash_templates.yaml`、`src/trpg/skillgen/`、`src/trpg/llm/`、`config/llm.toml`、`docs/design/`。

## 2. 測試

- `tests/api/test_flash_llm_text_lf3.py`（5 條，Mock、不連網路）：大變化帶 LLM 名稱 → `llm`＋描述；英文名稱與描述被丟 → `template`／`None`；變化上帶不合格描述（手改）不送出、小變化帶名稱不算、名稱沒被用上不算；一輪走 Mock LLM 提議（描述檢查換成一律通過）→ 選項帶描述、第 1 次全是 `template`；API 端到端（`MockLlmProvider`）兩個新欄位都在。
- `client/src/run/lf3FlashLlmText.test.ts`（10 條）：純函式、夾具（`llm` 組來源 `llm, llm, template, llm`；其他組全 `template`、沒描述）、選項卡順序（大標 → 名稱列 → 新名稱 → 描述）、沒有文字時和 FL-1b 一樣、小變化只多描述、描述是純文字（術語標記與 HTML 照字面跳脫）。
- 快照預測：會變的只有 OpenAPI（`client/openapi.json`）與開發頁夾具；`test_openapi_snapshot.py` 比的就是重產後的檔，通過；後端沒有其他快照、parity 夾具受影響（實際也沒有失敗）。

## 3. 本機 LLM 實機截圖（`docs/art/shots/LF-3/`，DPR 1，網址 `?mute=1`，無頭 Chrome `--mute-audio`）

做法：`localhost:8001` 沒回應，改用 LM Studio `100.87.188.89:1234`（`swift-1.5-qwen3.8-27b-uncensored-dynamic-mtp`，`reasoning_effort = "none"`；設定在 worktree 的 `config/llm.local.toml`，gitignored、沒 commit）。自己的 `trpg serve --port 8795`（`TRPG_SAVE_DIR` 指暫存區、`TRPG_LLM_CONFIG` 指本機設定、`TRPG_DEV_ROUTES=1`），建置好的前端。開發角色（單手劍、點燃＋潮濕）：停伺服器把招標成「上場用過」、補靈感點（暫存區腳本），API 閃兩次（第 1、2 次小變化，LLM 描述已經出現），第 3 次（大變化）先讀角色讓預先生成跑、等 60 秒再送閃現 → `pregen/wait` 直接 `ready`、四個選項都是 LLM 名稱（merge LF-2 之後重拍，名稱併進提議呼叫）。無頭 Chrome 除錯埠 9563。

| 檔案 | 內容 |
|---|---|
| `lf3_01_world_none_1600.jpg` | 1600×900 大世界，都沒選：四張卡都有「名稱 引火射 → 燎原閃／灼心／斷鏈／餘燼低語」＋「源晶推演」＋一句描述 |
| `lf3_02_world_pick_1600.jpg` | 1600 選中第 1 張（換個形狀）：卡上名稱列、描述、範圍「新 2 格」、傷害一降一升；下固定區照 FL-1b |
| `lf3_03_world_scrolled_1600.jpg` | 1600 選項區捲到底（轉型那張：名稱列＋描述＋種類／AP／耐力…） |
| `lf3_04_card_detail_1600.png` | 1600 真 1 倍裁切：選中那張卡的名稱列、小標記、描述 |
| `lf3_05_world_none_800.jpg` | 800×600（首頁「繼續」進入），窄版都沒選 |
| `lf3_06_world_pick_800.jpg` | 800 選中第 1 張 |
| `lf3_07_world_pick_last_800.jpg` | 800 選中最後一張（轉型）：「前」欄被長字撐寬，新名稱與「源晶推演」折成兩行 |

實機看到的 LLM 字（第 3 次，大變化）：
- `major_reshape`：**燎原閃**｜「將單體打擊擴展為範圍，讓火焰與雷電同時覆蓋更多敵人。」
- `major_intensify`：**灼心**｜「加深點燃效果，使燃燒狀態持續更久，強化火焰傷害。」
- `major_kill_chain`：**斷鏈**｜「擊殺敵人時返還行動點，讓連段攻擊更流暢。」
- `to_passive_on_hit`（轉型）：**餘燼低語**｜「被動觸發的火焰傷害，讓目標陷入燃燒狀態。」

**實測順帶發現（LF-1 程式，merge LF-2 前）**：同一個大變化題目，`pregen/wait` 10 秒逾時（10 秒從第一次等待算起，再問也不重新計時）→ 整題退回組合式名稱（餘波・／灼燃・／擴散・／恆久・引火射）。merge LF-2 後名稱併進提議呼叫，這次是提前讀角色、等 60 秒才閃，所以沒量到 LF-2 下的實際延遲（沒做量測）。

伺服器、無頭 Chrome 都是自己開的，交件前已關（8795、9563 沒在聽）。**要說明一件事**：第一次開無頭 Chrome 用的除錯埠 9481，Chrome 的 log 顯示 IPv4 綁不上（只聽 `[::1]`），但 `127.0.0.1:9481` 當時有回應、我的 CDP 腳本連了上去並把那個分頁導到我的 8795 首頁、按了「繼續」與成長鈕——那很可能是**別人（其他 agent）開在 9481 的 Chrome**（畫面上的靈感點和我的伺服器對不上）。發現後改用確認沒人聽的 9563 重拍；9481 那個瀏覽器我沒有關它。如果有其他 agent 這時段的瀏覽器截圖怪怪的，可能是這個原因。上手筆記已補「先 `netstat` 確認埠沒人用」。

## 4. 檢查（交件前，merge main 之後）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1564 檔） |
| `uv run lint-imports` | 0（14 kept） |
| `pytest -n 8`：`tests/api/test_flash_llm_text_lf3.py`、`test_openapi_snapshot.py`、`test_flash_api.py`、`test_flash_text_fl1b.py`、`test_flash_text_fl1f.py`、`test_flash_changes_fl1a.py`、`test_client_fixtures.py`、`test_world_growth_api.py` | 0（72 passed） |
| `vitest run src/run/lf3FlashLlmText.test.ts src/run/fl1bFlashChoice.test.ts src/run/flash.test.ts` | 0（50 passed） |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client build` | 0 |

沒跑全量 `check.py`、沒做平衡量測與模擬。

## 5. 待 PM 決定（照最保守的做法先做；美術 PM 驗收時再看）

1. **名稱放法**：移植需求沒寫。做成「前 → 後」的第一列「名稱 原名 → 新名」，用同一格線、不新增圖示；新名稱用「主文字色粗字、無底無框」（名稱沒有好壞，不借變好的金底或變弱的三角）。
2. **組合式名稱也列**：大變化、轉型沒有 LLM 名稱時（命名不合格、模型沒開、Mock）也列「名稱 原名 → 潮濕・點燃斬」，只是沒有小標記。這讓 FL-1b 的轉型那幾張卡多一列（`?set=transform`／`stance`）。要「只有 LLM 名稱才列」的話改 `RunFlashPending.tsx` 一行（`rename` 加 `llmNamed(o)` 條件）。
3. **名稱來源的小標記**：只標 `llm`，`template` 不標（不搶版面）。字沿用候選卡的「源晶推演」（`LLM_SOURCE_LABEL`，玩法 PM 2026-10-29 定案）與同一組紫色；說明卡字「這個名稱由本機模型提議；效果與數值照規則。」是 LF-3 暫定字，請玩法 PM 定。
4. **描述放法**：照規格「名稱下方一行」，整列寬、L3 次要字、12.5px（窄版 12px）、最多兩行（`line-clamp: 2`）；不加引號、不加圖示；不進下固定區（下固定區最小高度照 FL-1b，不跳）。小變化沒有名稱列時，描述直接接在大標下面。
5. **小變化沿用之前的 LLM 名稱**時 `name_source` 是 `template`（這次閃現沒有取名）；畫面上小變化本來就不列名稱，所以看不到差別。
6. **窄版折行**：轉型這種「前」欄字很長的卡，新名稱與小標記會折成兩行（`lf3_07`）。沒有另外壓縮。
7. **大世界大變化的 10 秒門檻**：見第 3 節實測，LF-1 程式下會整題退回組合式名稱；LF-2 後的實際延遲沒量。

## 6. 需要使用者決定

無。

## 7. 平衡疑慮

無（只多顯示文字）。

## 8. 沒驗證

- 一輪（roguelite）營火的選變體沒拍實機（同一個元件；開發頁 `?set=llm&mode=run` 可看，也沒拍）。
- 大世界從「成長」面板點閃現、等待提示對話框那條 UI 路徑：這次閃現用 API 送（等預先生成好），畫面是讀進來的待選面板。

## 開發 PM 裁定

- 接受，已合併。LF 三段（LF-1～3）完成，LLM 閃現的名稱與描述從後端一路顯示到前端。
- 待 PM 決定 1、2、4、5、6：照 agent 的做法維持，由美術 PM 驗收時一併看名稱列的放法、組合式名稱也列、描述、窄版折行。美術要改的話，另開小修。
- 待 PM 決定 3：來源標記說明卡的字轉交玩法 PM 定，回覆後只換字。
- 10 秒門檻：LF-1 程式下大變化會逾時退回；LF-2 之後的實際延遲沒有量到。排在許願池第一段順手量一次。只量延遲，不是數值量測。
- 沒驗證：一輪營火實機，以及大世界從成長面板點閃現、等待對話框的 UI 路徑。也交美術驗收時看。
- 除錯埠 9481 誤操作到不明的 Chrome 分頁：已回報專案 PM。上手筆記已補「先用 netstat 確認埠沒人用」，往後的派工單也一併提醒。
