# Phase 6L-2 報告：大世界接上三個 LLM 入口，加上預先生成

- 依據：06 6.34.7（預先生成，#132 一併寫入）、06 6.34.1、07 7.6、#126；使用者決定「要（推薦）」「等，超過 10 秒改給組合器版（推薦）」。
- 追加兩項（玩法 PM，經專案 PM 轉達）：閃現名照原技能的界域（6L-1 待決 4）、古風詞檢查的適用範圍定稿（6L-1 待決 5）。
- 分支：worktree 分支，含 main 的 9682ce4e，並 merge 了 2b92b4b1（6F-4b）。沒有 push、沒有合併進 main。

## 1. 三個入口的做法

共同的機制（`src/trpg/world/generated.py`）：

- 世界引擎（純函式）需要 LLM 內容時，組一個 **請求**（`FlashGenRequest`、`StoryGenRequest`、`OfferGenRequest`），交給目前裝上的 **供應者**（`using_generated`）。引擎不知道背景執行緒，也不讀時間。
- 供應者回傳一筆 **紀錄**（`FlashGen`、`StoryGen`、`OfferGen`），或 `None`。
- 引擎照樣驗證（守則 3），不合格就用降級版。
- 不論有沒有拿到，引擎都把 **最後給出的版本與來源** 收進清單。API 層把清單寫進日誌那一筆的 `generated`。
- 紀錄的鍵由請求的 **完整輸入** 算 blake2b（`input_key`），預測錯了只會沒命中。
- 重播：`trpg.world.replay.replay` 每一筆都用那一筆的 `generated` 當供應者（`recorded`），**完全不呼叫 LLM**。舊日誌沒有紀錄時，全部用組合器、模板與內容版，結果和 6L-2 以前相同。

| 入口 | 引擎位置 | LLM 提議什麼 | 引擎驗證 | 降級 | 來源標記 |
|---|---|---|---|---|---|
| 閃現與重閃 | `growth._flash` → roguelite `open_flash(source=…)` | 變化（類別、模板、參數、note），沿用 3W-7 `LlmFlashSource` | `make_offer` 逐一套用；套不上的用模板補 | 模板（`UsageSource`） | `FlashOfferedEvent.source`：`llm`／`partial`／`template` |
| 劇情技能「破霧」 | `quests._grant_story_skill`（`story_gen.py`） | 元素（選單內）＋名稱、概念、施放描述 | 元素在選單內；`retheme` 後預算分數 **完全相同**、驗證器問題數不增加；文字長度、沒有英文 | 內容版（原樣的破霧） | `StorySkillGrantedEvent.source`：`llm`／`content` |
| 機遇完整技能（古松祭壇） | `solutions._opportunity_offer` | 完整技能三選一（4-L6 的提議器，`make_offer` 開 LLM） | 完整技能、同階級、候選與標示一一對應 | 組合器與技能池（照常同步算，PERF-3 快取照用） | `SkillOfferedEvent.made_by`：`llm`／`composer` |

- **白板三選一不接 LLM**（#69）：任務三選一的 `quests._offer` 沒動。
- **劇情技能**（`src/trpg/llm/story_skill.py`、`src/trpg/skillgen/story_theme.py`）分兩步：
  1. **元素**：玩家裝備中技能的關鍵字（只看專屬規則）在 `skill_keywords.yaml` 有「`effect: damage` ＋ `element`」製造規則的元素，就是選單，依持有數排序。
     - 例：點燃 → 火焰、凍結 → 冰霜、隱蔽 → 暗影。
     - 新 prompt `story-element/1`，schema 用 `enum` 限定在選單內，帶錯誤重試最多 3 次。
     - 換元素只換 **頂層傷害效果** 的元素、技能主題元素與標籤裡的元素名；形狀、骰子、費用、冷卻、骨架都不動。
  2. **名稱與描述**：交給 4-L7 命名步驟 `name_skill`，`region` 是任務所在區（雲嶺 → 東方，#126）。
     - 換了元素時加 `before`，要求文字提到新的元素。
  - 任何一步失敗（模型關閉、用盡重試、命名退回組合式名稱）就整招用內容版。
  - 玩家沒有對得到元素的關鍵字時，元素不換，名稱與描述照樣請 LLM。
- **機遇**：提議器是 `provider.proposer`（同 roguelite），`make_offer(run.llm=True)`。
  - 至少一張候選的來源是 `llm` 才算 LLM 版，否則記 `composer`，引擎照常算。
  - 題目帶 `region=trigger.region`（雲嶺），沿用 6L-1 的區域風格接線。

### 追加 1：閃現名照原技能的界域

- 角色新增 `skill_regions`：取得時的技能 ID → 取得地點的區域。
  - 任務、機遇三選一選到時記；`PendingOffer.region` 記出題時的區域，舊存檔用角色當下的區域。
  - 劇情技能記任務所在區。
  - 閃現選定、傳承後，新 ID 沿用原技能的區域。
- 查詢 `growth.skill_region`：先查表；查不到就沿著閃現前的原技能（`flash[...].base_id`）與階級重配前的 ID（`<原 ID>_t<階級>`）往回找。
- 沒有紀錄（創角、舊存檔）＝`None`＝中性。
- 閃現出題時把它放進 `FlashRequest.region`。6L-1 已經讓閃現 prompt 依它套用風格，這次只補上傳值，沒有改提示詞，`FLASH_PROMPT_VERSION` 不升。
- 季末重置政策表：`CharacterState.skill_regions` 列為數值類（跟著技能走）。

### 追加 2：古風詞檢查的適用範圍（定稿）

- 命名驗證 `check_archaic`（6L-1）已經是定稿的行為：
  - 中性區的名稱、`concept`、`cast_flavor` 都檢查 27 個古風詞（含「仙」「罡」）；
  - 「施主」在任何區的技能名都不行；
  - 「訣」結尾只有雲嶺可以用。
  - 這次補上定稿測試。
- `trpg.llm.style_eval`：中性區的驗收除了名稱，也看 `concept`、`cast_flavor`（結尾規則只看名稱）。
  - `skill_eval` 的 CSV 最後多兩欄 `concept`、`cast_flavor`，`scripts/eval_style.py` 讀得到就檢查，舊 CSV 照讀。
- 提示詞沒改，`PROMPT_VERSION`、`NAMING_PROMPT_VERSION` 都不升。

## 2. 預先生成（`src/trpg/api/world_pregen.py`）

| 入口 | 什麼時候預先生成 | 上限 |
|---|---|---|
| 閃現 | 角色在城鎮或營火、沒有待選閃現與遭遇、靈感夠時，裝備中可以閃的技能（不指定類別、依技能列順序） | 每角色 `FLASH_LIMIT`＝3 招 |
| 劇情技能 | 進行中任務的下一步獎勵有劇情技能時（完成前、以及加上這一步經驗後各一份，升級可能換階級） | 每角色 `STORY_LIMIT`＝2 份 |
| 機遇 | `pending_event` 有可用的機遇解法時 | 每角色 `OPPORTUNITY_LIMIT`＝1 份 |
| 全服 | 暫存區（排隊中＋做好的） | `QUEUE_LIMIT`＝12 筆，超過丟最舊、還沒開始的 |

- 預測的時機：每個世界動作之後、角色第一次讀進來時（同 PERF-3）。
- **單一佇列**：一條背景執行緒（`max_workers=1`），同一時間只有一個 LLM 請求。測試確認同時進行數最多 1。
- **只放記憶體**：結果不寫日誌、不寫存檔。預測換了（角色狀態變了）就丟掉這個角色沒再被預測到的；拿去用的那一筆從暫存區拿掉。
- **玩家真的打開時**（`WorldPregen.supplier`，在 `WorldStore._apply` 裡裝上）：
  - 好了就給。
  - 沒好就等，最多 `WAIT_SECONDS`＝10 秒，從第一次等待算起；等待提示等過的時間也算在內，不會再等一次 10 秒。
  - 超過就回 `None`，引擎改給組合器、模板或內容版。
  - 沒預測到的請求（例：指定類別的閃現）當場排進佇列再等。
- **等待提示**：`POST /api/world/characters/{id}/pregen/wait`，body 是 `{kind: flash|opportunity, skill, slot, category, solution}`。
  - 不扣點、不寫日誌，等待時不佔世界的寫入鎖。
  - 回 `ready`／`timeout`／`none`／`off`。
  - 機遇只有選的是可用的機遇解法時才等；其他解法回 `none`。
- **前端**（`client/src/world/pregen.ts`、`PregenWaitDialog.tsx`、`WorldScreen.tsx`）：
  - 世界的 LLM 開著時，`flash`（含重閃）與 `event_solve` 送出前先問。
  - 超過 400ms 才跳出共用彈窗 `DialogFrame`：「說書人正在構思……」，加「取消」。
  - 取消＝不送那個動作（沒有扣點），伺服器那邊的等待自己結束。
  - RT-3 的羽毛筆動畫沒接。
- **模型關閉**（世界的 LLM 開關關、健康檢查說不可用；`WorldLlm.usable`）：不預測、不等、不呼叫，引擎一律降級，日誌照樣記降級的來源。
- **計時只在 API 層**：`clock` 可注入假時鐘，等待迴圈用 `poll_seconds` 輪詢 future，不是 shell 的 until 迴圈。
- 提供者：`LlmProvider` 多一個 `story_proposer(library)`。本機用 `make_story_proposer`，Mock 用 `mock_story_proposer`。閃現用既有的 `flash_source`，機遇用既有的 `proposer`。

## 3. 日誌與存檔欄位

| 位置 | 欄位 | 說明 |
|---|---|---|
| `WorldLogEntry` | `generated: tuple[FlashGen \| StoryGen \| OfferGen, ...] = ()` | 這個動作最後給出的生成內容與來源（依發生順序，以 `kind` 區分）。**空的時候不寫**，沒有生成內容的那一行和 `/7` 逐字相同 |
| `FlashGen` | `key`、`record: FlashLlmRecord` | 提議的變化、來源、嘗試、錯誤碼、prompt 版本 |
| `StoryGen` | `key`、`skill`、`source`、`element`、`name_zh`、`concept`、`cast_flavor`、`prompt_version` | 內容版只有 `source="content"` |
| `OfferGen` | `key`、`source`、`offer: SkillOffer \| None` | 組合器版不存候選（引擎照常算） |
| `CharacterState` | `skill_regions: dict[str, str]` | 技能的取得地點界域 |
| `PendingOffer` | `region: str \| None` | 三選一的取得區域 |
| 事件 | `FlashOfferedEvent.source`、`StorySkillGrantedEvent.source`、`SkillOfferedEvent.made_by` | 畫面與統計用（事件不存檔） |

- 劇情技能與機遇候選套用後的技能本身照舊存在角色的 `generated_skills`、`pending_offers`。

## 4. 版號（照 `save.py` docstring 評估）

| 版號 | 前 | 後 | 理由 |
|---|---|---|---|
| `trpg-wlog` | `/7` | `/8` | 每筆多了 `generated`；`/7` **照讀**（新增 `READABLE_WLOG_FORMATS`，標頭照常解析），寫回時標頭改 `/8` |
| `trpg-char` | `/7` | `/8` | `skill_regions`、`PendingOffer.region`；`/1`～`/7` 照讀（只多了選填欄位，舊技能＝中性） |
| `WORLD_RULES_VERSION` | 10（6F-4b） | **11** | 引擎改從供應者拿內容，劇情技能可以換元素與文字。模型關閉時和 10 結果相同，但新日誌在 10 的程式重播不出 LLM 版本，保守升版。舊日誌照規則鍵標成「規則已變、不能重播」 |

- 合併 2b92b4b1 時 `save.py` 衝突：main 把規則版號升到 10（6F-4b），我原本也寫 10。照專案 PM 指示改成 11，docstring 的第 11 條接在 6F-4b 的第 10 條後面，兩邊說明都保留。
- main 沒有升 char、wlog，這兩個維持我這邊的 `/8`。
- `WorldScreen.tsx` 衝突：main 加了 `</DialogHudBox.Provider>`。等待彈窗放在 Provider 裡面最後一個，兩邊都保留。
- API 有改（新端點、事件欄位）：已跑 `scripts/export_openapi.py` 與 `corepack pnpm -C client gen:api`。合併後重新匯出，沒有差異。

## 5. 驗收證據

| 驗收 | 證據 |
|---|---|
| 1. 同一角色重播後，閃現選項完全相同 | `tests/world/test_generated_6l2.py::test_flash_replay_reads_log_only`：LLM 出題 → 日誌行讀回 → `replay`（外面裝了會報錯的供應者）→ `pending_flash` 相同。`tests/api/test_world_pregen.py::test_store_logs_sources_and_replays_without_llm`：WorldStore 實際寫的日誌重播，生成函式換成會報錯的，閃現與機遇結果相同 |
| 2. 模型關閉時三個入口都能降級 | `test_flash_falls_back_when_model_off`（結果和 6L-2 以前逐字相同）；`test_story_skill_rethemed_by_keywords` 的內容版部分（名稱「破霧」、來源 content）；`test_opportunity_falls_back[False]`（和 6L-2 以前相同）；`test_model_off_does_nothing`、`test_store_without_pregen_still_records_fallback`；LLM 層 `test_model_off_falls_back` |
| 3. 「破霧」用東方風格，元素跟著關鍵字換，骨架和預算不變 | `test_story_skill_rethemed_by_keywords`：請求的區域是雲嶺；預設主角（凍結、隱蔽）→ 冰霜；骨架、形狀、費用、AP、效果種類相同，預算分數相同。`tests/llm/test_story_skill.py::test_llm_picks_element_and_names_in_region_style`：命名 prompt 含「雲嶺」「東方山城」。`test_retheme_keeps_skeleton_and_budget` |
| 4. 古松祭壇的機遇招用雲嶺風格 | `test_opportunity_offer_from_llm`：`OfferGenRequest.region == "cloud_ridge"`，`PendingOffer.region`、選到的技能 `skill_regions` 都是雲嶺。題目區域進 LLM prompt 的接線是 6L-1 的 `tests/llm/test_region_style.py`（`TopicRequest.region` → `style`）。Mock 提議器對史詩題目常退回，所以這條測試用「組合器的三選一、第一張標成 LLM」模擬成功，驗證引擎的接收路徑 |

其他：

- 驗證失敗會降級：劇情技能的元素不在選單內 → 內容版；機遇的階級不對 → 組合器；LLM 層一直挑選單外的元素 → 重試 3 次後內容版。
- 出題本身不合法時不問 LLM（`test_flash_not_asked_when_illegal`）。
- 舊日誌行（`/7`）、舊角色（`/7`）照讀（`test_log_line_without_generated_is_unchanged`、`test_old_char_without_regions_is_neutral`）。
- 預先生成沒趕上：假時鐘每次 +1 秒 → `wait` 回 `timeout`（≥10 秒）、引擎拿到 `None`（`test_late_result_waits_then_falls_back`）。
- 沒用到的結果丟掉（`test_unused_results_dropped`）；生成函式出錯 → `None`（`test_generator_error_falls_back`）。

## 6. 12B 實測

12B_PLACEHOLDER

## 7. 檔案

- 新增：
  - `src/trpg/world/generated.py`、`src/trpg/world/story_gen.py`、`src/trpg/skillgen/story_theme.py`
  - `src/trpg/llm/story_skill.py`、`src/trpg/llm/prompts/story.py`
  - `src/trpg/api/world_pregen.py`
  - `client/src/world/pregen.ts`、`client/src/world/pregen.test.ts`、`client/src/world/PregenWaitDialog.tsx`
  - 測試：`tests/world/test_generated_6l2.py`、`tests/api/test_world_pregen.py`、`tests/llm/test_story_skill.py`
- 修改：
  - 世界：`src/trpg/world/{growth,quests,solutions,replay,save,state,actions}.py`
  - roguelite：`src/trpg/roguelite/flashes.py`（`open_flash` 的 `source`、`region`；`flash_request` 的 `region`）
  - 季末重置：`src/trpg/server/season_policy.py`
  - API：`src/trpg/api/{world,app,world_flow,llm_source}.py`、`src/trpg/api/routes/world.py`
  - LLM：`src/trpg/llm/{style_eval,skill_eval}.py`、`scripts/eval_style.py`
  - 前端：`client/src/api/{client,types}.ts`、`client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/screens/WorldScreen.tsx`
- 測試裡改字面值：`tests/world/test_{field,field_lineup_seed,field_things,field_visit_generation,newcomer_6f4,opportunity_hints,region_teleport,save}.py`、`tests/api/test_world_field_api.py`（格式 `/7` → `/8`）；`tests/world/test_field_ctx_replay.py`（凍結雜湊比較前拿掉新欄位 `skill_regions`）；`tests/llm/test_region_style.py`（+2）。
- 白板組合器、`skill_composer.yaml`、新手任務內容、人物繪製都沒碰。

## 8. 測試

- 新增 30 個：world 11、api 9、llm 8（劇情技能）、region style +2。
- `tests/world` 全部、`tests/api/test_world_pregen.py`、`test_offer_prefetch.py`、`test_openapi_snapshot.py`、`tests/llm/test_story_skill.py`、`tests/test_architecture.py`（合併 6F-4b 之後）：**1075 通過**。
- `tests/llm`、`tests/roguelite`、`tests/api`、`tests/content/test_skill_same_name.py`、`test_world_narration.py`、`tests/test_architecture.py`：**1378 通過、1 略過**（開發模式的 owner guard，原本就略過）。
- client：vitest 全部 VITEST_PLACEHOLDER；`corepack pnpm -C client build` 通過。
- 每次 commit 前 ruff check、ruff format --check、mypy src（529 檔）、lint-imports（13 條契約）都通過；一場 `trpg battle --map bandit_lair --seed 62` ＋ `replay` 驗證通過。
- 沒跑：全量 `check.py`、CLI 快照（照規格，交 PM）。

## 9. noqa

- `solutions._opportunity_offer`：`# noqa: PLR0917`（6 個位置參數，都是 `make_offer` 的參數；同檔 `_opportunity` 的既有寫法）。
- 其他沒有新增。

## 10. 待 PM 決定

1. **劇情技能等待時沒有前端提示**：劇情技能是在任務步驟完成時（任何動作都可能觸發）由引擎發的，前端事先不知道哪個動作會完成那一步。
   - 現在：沒趕上時，伺服器在那個動作裡最多等 10 秒，前端只看到動作比較慢，沒有可取消的彈窗。
   - 預先生成在「任務接到那一步」就開始，一般會趕上。
   - 要彈窗的話，要讓畫面知道「這個動作會完成劇情步驟」，或改成領取時另外一個動作。
2. **沒趕上的工作不能中斷**：超過 10 秒改給降級版之後，背景那筆 LLM 請求會跑完（HTTP 呼叫中斷不了），結果丟掉。單一佇列裡後面的工作要等它。上限是 12 筆、閃現每角色 3 招，是保守值。
3. **機遇的 LLM 比例**：完整技能三選一照 roguelite 的 `llm_share_permille`＝800，每種候選 80% 先請 LLM。12B 對史詩題目退回多（見第 6 節），實際常常是組合器版。要不要調是平衡問題。
4. **劇情技能的元素選單**只看「傷害元素」的製造規則。潮濕、倒地、撞擊、標記這類沒有傷害元素的關鍵字對不到元素，破霧保持神聖、只換文字。另外，換元素時標籤裡的元素名一起換（破霧的「風」標籤會變成新元素），請玩法 PM 確認。
5. **閃現的 `note_zh`** 沒有加古風詞檢查（追加 2 只指定 `concept`、`cast_flavor`）；閃現的大變化命名本來就走命名驗證。
6. **預先生成的數量**（閃現 3 招、劇情 2 份、機遇 1 份、全服 12 筆）與 400ms 才顯示提示是保守預設。
7. **機遇的候選另外存一份**：LLM 版的三選一整份存在日誌（`OfferGen.offer`，含技能定義），一筆約數 KB。組合器版不存，重播時照常算。
