# Phase 5B-5 完成報告：事件與任務的前端與路由

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 18 節（先寫規格、commit `adeed107` 後實作；當時是第 17 節，合併 main 的 5A-M2 規格後改為第 18 節，「之後各段規格」改第 19 節，程式與測試裡的節號同步改）。
> 沒有動 `trpg.engine`、戰鬥紀錄文字、單位特性、`trpg.roguelite`。`trpg.world` 只動兩處：`narration.py`（提示語對照 `story_masks`）、`step.py`（三選一待選時也收 `narrate`，代決 5B5-11）。

## 1. 交付

| # | 項目 | 檔案 | commit |
|---|---|---|---|
| 1 | 5B-5 詳細規格 | `docs/phases/Phase5計畫.md` 第 18 節 | `adeed107` |
| 2 | 隱藏地點提示語取代「某處」、`storyteller/2` | `content/world/maps/cloud_ridge.yaml`、`src/trpg/content/{world_map,world_narration}.py`、`src/trpg/world/narration.py`、`src/trpg/narrative/storyteller.py`、`src/trpg/llm/prompts/storyteller.py`、相關測試 | `e2dfd2b7` |
| 3 | 路由、流程、顯示資料、大世界 LLM 開關、OpenAPI | `src/trpg/api/{world_flow,world_story_view,world_story_schemas}.py`（新）；`world.py`、`world_schemas.py`、`world_presenter.py`、`routes/world.py`、`llm_source.py`、`run_presenter.py`（`offer_out` 公開，輸出不變）、`app.py`、`state.py`；`src/trpg/world/step.py`；`tests/api/test_world_events_api.py`（新 13 例）；`client/openapi.json`、`schema.d.ts` | `fdbb492d` |
| 4 | 前端：事件卡、情境判定、判定結果、這裡的人、聊天、任務日誌與線頭、三選一、酒館、LLM 開關 | `client/src/world/{EventCard,NpcPanel,QuestLog}.tsx`、`story.ts`、`story.test.ts`（新）；`WorldPanel.tsx`、`growth.ts`、`screens/WorldScreen.tsx`、`api/{types,client}.ts`、`styles/world.css` | `2e8fc2a6` |
| 5 | 合併 main（5A-M2 規格衝突，只有計畫文件） | `docs/phases/Phase5計畫.md` | `00b0235d` |
| 6 | 本報告 | `docs/phases/Phase5B-5報告.md` | 最後一筆 |

## 2. API 清單（新增與改動）

| 方法與路徑 | 內容 |
|---|---|
| `POST /api/world/characters/{id}/actions` | 加 `accept_quest`、`offer_pick`（`pick` 可為 `null`＝跳過、`replace`）、`talk`、`tavern`。**動作之後有沒敘述過的事件就自動送一次 `event_story` → `narrate`**（實際只有 `travel` 會觸發）。`situation`／`narrate` 不收（422），只能經下面的端點由伺服器組提議。 |
| `POST …/situation` | `{template}`：打開情境判定解法，說書人寫情境敘述（`narrate` scene `situation`）；送出前可以換解法。 |
| `POST …/situation/answer` | `{template, text, cite}`：`text` 只進 LLM 的 `<player_input>`；`cite` 只能是 `situation_facts` 的 `clue`／`npc_bond`／`exchange`（其他 422）。提議（模型關＝`default_proposal`）→ 引用併進用心清單 → `situation` 動作（**第一次送出即定案**，再送 422）→ 結果敘述。LLM 提議被引擎拒絕時改用降級提議。 |
| `POST …/chat` | `{npc, text}`：所在地點的 NPC 自由聊天（`narrate` scene `chat`），不改狀態；NPC 不在這裡 422。 |
| `GET／POST /api/world/llm` | 大世界 LLM 開關：`{enabled, default, overridden, notice_zh}`；`POST {enabled: true|false|null}`（`null` 回到伺服器設定；打開先探測，連不到維持關閉＋提示）。 |

`WorldView` 新增：`event`（事件卡：角色、動機、旁白與多講一點、來源、誰／想要／阻礙／賭注、接的線頭、解法〔情境判定可用、其他「之後開放」〕、離開＝作罷、最近打開的情境〔做法、屬性、方法、基準難度、情境敘述、可引用事實〕；旁白從日誌讀，重新整理也在）、`situation_result`（屬性、方法、兩顆骰與模式、修正、用心清單逐筆、總值、DC、結果、獎懲、結果敘述）、`npcs_here`（好感度值、級別、級距「中立（−9～19）」、這一級聊得到什麼）、`dialog`、`quests`、`quests_here`、`pending_offer`（重用一輪的 `OfferOut`）、`threads`、`rumors`；`here.can_tavern`。事件句子新增：遇到事件、作罷、情境判定、判定結果、留下／擠掉線頭、接任務、完成一步、完成任務、三選一、學會技能、劇情技能、好感度變化（含級別變化）、說話、酒館。地點圖與目前地點的說明文字也套提示語（藥師谷原本寫「通往隱藏地點『丹爐洞』」）。

## 3. 畫面流程

```
地點圖（點相鄰地點走）
 ├ 走到觸發事件 → 右側「事件：〔地點〕」卡：角色・動機／旁白（多講一點）／解法按鈕（不能用的寫原因）／離開＝作罷
 │    └ 點「情境判定：…」→ 情境敘述、可用屬性與方法、基準難度、持有線索與往來晶片（點一下引用）、文字輸入（字數）
 │         └「送出（送出後就定案，不能重來）」→「判定結果」卡（算式、兩顆骰、用心清單 ✔／✘、結果敘述、獎懲）
 ├ 右側「這裡的人」：NPC＋好感度級距；「說話」（傳聞／入口／祕密）、「聊天」展開對話紀錄與輸入；「可以接的任務」→ 接任務
 ├ 城鎮服務「酒館」→ 右側列本週傳聞
 ├「任務與線頭」切換左欄：任務日誌（✔ 已完成、▶ 目前、・ 還沒到）、線頭（範圍、剩多久、相關 NPC、指向）
 ├ 任務三選一待選 → 左欄固定顯示三選一（重用一輪 OfferPicker）：學這招／跳過；其他動作停用（後端也擋）
 └ 標頭「說書人用本機模型」勾選（伺服器預設開／關；連不到時提示）
```

## 4. 瀏覽器驗證紀錄（Claude_Browser；後端＋前端同一個伺服器 `127.0.0.1:8057`）

`corepack pnpm -C client build` 後用 `.scratch_5b5/serve.py`（`create_app(static_dir=client/dist, save_dir=.scratch_5b5/saves)`，`TRPG_LLM_BASE_URL=http://127.0.0.1:9/v1`、`TRPG_LLM_GENERATE=false`：說書人降級，打開也連不到，不會碰 8001）。原本要用 8050，但 8050 已被本機另一個程式（非本 agent）佔用，改 8057；結束時只停了自己開的伺服器。預覽視窗在背景、截圖逾時，紀錄用 `get_page_text`／`read_page`／DOM 查詢；地點圖移動在 800 寬時座標點擊沒有生效，改用頁面內 `element.click()`（走前端同一個處理函式），其他按鈕都用 `computer` 點擊。

1. 建角（頁面內 `fetch` 建「驗收五」：火焰法杖、點燃＋標記）→ 首頁「進入大世界（測試）」。右側出現「說書人用本機模型（伺服器預設關）」、霧渡鎮服務多「酒館」、「任務與線頭」、「這裡的人：渡婆婆 鎮長 中立（−9～19）・目前 0／柳掌櫃 商人 中立（−9～19）・目前 0」、「可以接的任務：霧渡新手路（新手・渡婆婆）／霧中裂痕（主線・渡婆婆）」。
2. 點「接任務」（霧渡新手路）→ 紀錄「接下任務「霧渡新手路」。」、按鈕變「任務與線頭（任務 1）」。
3. 渡婆婆「說話」→ 對話紀錄「渡婆婆：〔傳聞〕夜裡鎮上有燈籠隊在找失蹤的人，失蹤的都往山裡去了」；「聊天」→ 輸入「婆婆，最近鎮上有什麼怪事？」→「說」→ 紀錄「你：婆婆，最近鎮上有什麼怪事？／渡婆婆：渡婆婆看了你一眼，沒有多說。」（降級模板），輸入框清空。
4. 「酒館」→「酒館：本週傳聞」三則（冬湖熊巢、古松祭壇雷雨夜、劍冢殘劍）；紀錄「在酒館聽到 3 則本週傳聞。」
5. 走 渡口石階 → 竹林小徑 → 雨中梯田：**事件卡**「事件：雨中梯田／斷崖幫哨兵　收過路費／在雨中梯田，斷崖幫哨兵擋在你面前。／多講一點（模板文字）／戰鬥（之後開放）／情境判定：威嚇（意志、力量）／交涉：付錢（之後開放）／走到別的地點，這件事就此作罷。」點「多講一點」→「斷崖幫哨兵想要收過路費。擋在中間的是你。賭上的是金幣。」
6. 點「情境判定：威嚇」→「情境判定：威嚇哨兵讓路／斷崖幫哨兵的事還沒了結。你打算威嚇哨兵讓路。／可用屬性：意志、力量・方法：威嚇・基準難度 13／你持有的線索與往來：〔交換條件〕拿出 1 份補給交換」。點晶片引用、輸入回答（29 字）→「送出（送出後就定案，不能重來）」。
7. **判定結果**卡：「判定結果：成功　威嚇哨兵讓路／意志・威嚇（模型關閉：照預設提議）／d20 12（一般）＋0屬性＋1用心＋0種族 ＝ 13 vs DC 13（基準 13）／兩顆骰：12、19／✔〔交換條件〕拿出補給交換／威嚇哨兵讓路，成了。／獲得 55 經驗／補給 −1／留下線頭：二當家記恨你」；事件卡消失；紀錄多「疤面的好感度 −10（−10・冷淡）：中立 → 冷淡。」狀態列經驗 55、補給 4。頁面內再送一次答案 → **422「目前沒有事件可以判定（同一件事只能判定一次）」**。
8. 回渡口石階遇敵（中途在霧渡鎮又觸發「夜裡的燈籠隊」事件，離開時紀錄「…的事就此作罷」）→ 點「開戰」→ 戰鬥主角動作用頁面內 `fetch` 打完（打贏 4 輪，戰鬥畫面是既有的）→「← 回到地點圖」。
9. **任務推進一步**：左欄固定「任務給的技能三選一／霧渡新手路：渡口石階：趕走搶渡船的盜賊／在野外：選了先放進備用…」三張卡（火焰爆／火痕／召喚元素之靈），「任務與線頭」停用、地點圖不可點。選火痕 →「學這招」→ 紀錄「學會「火痕」，放進備用。」；靈感 1、經驗 455。
10. **任務日誌**：點「任務與線頭」→「霧渡新手路 新手・渡婆婆／✔ 渡口石階：趕走搶渡船的盜賊／▶ 竹林小徑：突破雨裡包圍的霧狼／・ 雨中梯田：平息盜賊和修士的衝突／線頭：二當家記恨你 個人・2 天 23 小時後到期・疤面」。
11. **浮動卡 6.5.1**（好感度晶片的 `Hint`）：1600×900 觸發元素 y 440.7、卡片 y 388.7＋高 52.4（貼齊上方、無空隙、在視窗內）；800×600 卡片 x 69～309、y 238.7（貼齊觸發元素 y 290.7），`scrollWidth` 785 < 800、沒有水平捲動。說明卡只有兩行字，沒有「捲到底」可測；本段新增的說明一律用共用 `Hint`，沒有新的彈出層（`floatCardRule.test.ts` 通過）。

## 5. 代決（照規格 18.9）

| # | 事項 | 代決 |
|---|---|---|
| 5B5-1 | 大世界 LLM 開關 | 伺服器層級、只存記憶體；預設照 `generate`（`TRPG_LLM_GENERATE`）；打開先探測，連不到維持關閉＋提示 |
| 5B5-2 | LLM 在哪裡呼叫 | 世界寫入鎖裡依序（5～10 人；人多再改鎖外組請求） |
| 5B5-3 | 自動事件旁白 | 任何 `actions` 之後有沒敘述的事件就送一次 |
| 5B5-4 | 點選引用 | `clue`／`npc_bond`／`exchange` 併進用心清單（排前面、不重複、≤ 4 筆），引擎照常核對、上限 +2；弱點不能引用；模型關閉時引用照樣算 |
| 5B5-5 | `<player_input>` | 前端送純文字欄位，後端 `wrap_player_input` 包 `<player_input>` 並跳脫（前端自己包會被跳脫兩次）；測試確認注入字串只在 `<player_input>` 內、被跳脫、系統訊息沒有 |
| 5B5-6 | 旁白與情境敘述的來源 | 從世界動作日誌讀（事件觸發之後的 `narrate`），不另存 |
| 5B5-7 | 戰鬥、交涉、放棄、機遇解法 | 列出但停用「之後開放」；離開地點＝作罷 |
| 5B5-8 | 對話紀錄 | 只在前端保留（頁面開著的期間） |
| 5B5-9 | 提示語 | `LocationDef.hint_zh`（名詞片語）：丹爐洞「谷底一處隱密的洞窟」、鶴歸崖「霧裡一座沒見過的山崖」；沒填用「一條還沒發現的路」；NPC 祕密的代替文字「……」。骨架、線頭、任務、聊天內容、傳聞、地點說明都套 |
| 5B5-10 | 任務日誌位置 | 左欄切換；三選一待選時左欄固定（閃現優先） |
| 5B5-11（實作補） | 三選一待選時的敘述 | 情境判定或戰鬥完成步驟後馬上有三選一待選，結果敘述仍要進日誌：`world_step` 有待選時也收 `narrate`（敘述不改數值） |

## 6. 待 PM 決定

1. **提示語文字**是開發 PM／實作者定的名詞片語（例沒有照抄「谷底似乎還有一條路」，因為它要嵌進「通往…」「找到…」「藥師谷深處有座沒人敢進的…」這類句子）；請玩法 PM 看一下措辭。柳掌櫃友善時給的任務入口、隱藏任務「丹爐之謎」的說明也因此看不到「丹爐洞」三個字（揭露前一律提示語），是否要讓「任務入口」例外公開名稱，需要玩法 PM 決定。
2. **城鎮也會觸發事件**（驗證時霧渡鎮觸發「夜裡的燈籠隊」）——是 5B-1 既有規則（骨架地點含霧渡鎮），不是本段改的；若城鎮不該出事件請玩法 PM 說。
3. **戰鬥結果句子只回在同步的那個請求**（5A-5 待決 1 的延伸）：任務步驟完成、三選一的句子也一樣；任務日誌與三選一畫面本身不受影響。
4. **LLM 在寫入鎖裡**（5B5-2）：真模型一次約 4～13 秒，期間其他人的動作會排隊；人多時再改。
5. **用心清單引用的規則**（5B5-4）：模型關閉時引用照樣算，是依 9.6.4「核對得到的事實」推定；若玩法 PM 認為引用只該給 LLM 參考，改 `world_flow._with_cites` 一處。
6. 真模型沒有測（不連 8001）；`storyteller/2` 的 hints 指令要在真模型上看一輪。

## 7. 檢查

- 合併 main（`00b0235d`）之後：
  - `pytest tests/api tests/world tests/narrative tests/content/test_world_map.py tests/content/test_world_narration.py tests/llm tests/test_architecture.py -n 8 -m "not llm" --timeout=3000`：1405 passed、2 failed → 修正後 `tests/api` 377 passed。失敗①OpenAPI 快照只差合併後改的節號文字（重產）；②`test_battle_writes_back_to_world` 既有偶發：賽季種子隨機，遇到精英時經驗是 3 份（300）不是 100，斷言改成 100 或 300。
  - `pytest tests/cli -m "slow or not slow" -n 8 --timeout=3000`：180 passed（快照不用重產）。
  - `npx vitest run`：126 檔、1211 passed；`corepack pnpm -C client build`：通過。
  - `ruff check .`、`ruff format --check .`、`mypy`（1045 檔）、`lint-imports`（9 kept）：全部通過。
- OpenAPI：`scripts/export_openapi.py` ＋ `gen:api` 重產，`test_openapi_snapshot` 通過。
- 新增的 `# noqa`：只有測試一處 `SLF001`（`test_player_text_only_in_player_input` 依題目補 Mock 回應）。沒動戰鬥，不需戰鬥重播；沒跑全量 `scripts/check.py`。

## 8. 5B-5b（事件卡打開放棄、交涉、戰鬥解法；穿陣刺；固定時鐘）

1. **`event_solve` 接上 API 與事件卡**：`WorldActionRequest`（`world_schemas.py`）加入 `EventSolveAction`，走既有 `POST …/actions`；`EventSolutionView` 新增 `cost_supplies`、`can_pay`、`waive_thread`、`waive_zh`（持有且沒過期的可抵線頭）。可用條件寫在 `world_story_view._solution_problem`：放棄隨時可用；交涉補給不足且沒線頭時停用「補給不足（要 N）」，持有 `waive_thread` 時事件卡多一顆「用〔線頭〕抵」；戰鬥在不能遇敵的地點停用「這裡打不起來」，選了戰鬥解法後（`pending_event.combat_solution`）整張卡顯示「戰鬥中」；機遇仍「之後開放」。戰鬥解法開一般遭遇，沿用遭遇面板的 `fight`／`retreat`，打完那次由 `settle_event_combat` 結算。前端：`EventCard` 新增 `onSolve`，`story.ts` 新增 `solutionClick`／`waiveLabel`，提示語依解法種類。OpenAPI 與 `schema.d.ts` 已重產。測試：`tests/api/test_world_events_api.py` 新增放棄、交涉（補給不足／足夠）、線頭抵用、戰鬥解法打完結算共 5 項；vitest 補 `story.test.ts`。瀏覽器實測（後端 8060、前端 5220，降級模式）：交涉用人情線頭抵用（線頭用掉、留下「渡船夫的女兒」）與放棄皆成功、事件卡消失。
2. **新技能「穿陣刺」**（`skill_formation_pierce`）：近戰武器技、`line` 2 格、傷害 1400‰、耐力 8、冷卻 2、`scaling_attr: str`，預算 75.0% 合格。加給 `sect_array_disciple`；另外是 1 階普通、無關鍵字的手寫技能，自動進通用池。內建技能數 374 → 375；`refactor_3wr2.json`、`skill_icons.json` 已重產。
3. **固定時鐘**：`tests/api/test_world_api.py` 的 `Clock`（每呼叫一次 +7 秒，結果隨呼叫次數變）換成 `FixedClock`（永遠 `NOON`），`test_world_api.py`、`test_world_events_api.py`、`test_world_growth_api.py` 三個檔案全部改用；全過。`tests/api/test_world_story.py` 沒有用時鐘。
