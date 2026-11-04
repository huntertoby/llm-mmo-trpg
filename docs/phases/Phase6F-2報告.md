# Phase 6F-2 報告：新手流程（#99 戰鬥短提示、#125 開局在主城、#132 第一次閃現、指引 U2～U4）

> 實作者：implementer agent（2026-11-04）。基準 main `b8730217`（含 6F-1）；中途照協調者指示合併 `9167d4ce`（#132 設計文件，連帶 main 上 RT-2／RT-4／6H-1 的合併）。分支 `worktree-agent-a54b089b590e95983`，沒有 push、沒有合併回 main。
> 截圖：`docs/art/6f2_01`～`6f2_17`（無頭 Chrome，自己的伺服器 8355、CDP 9355，Mock LLM）。

## 1. 做了什麼

| # | 項目 | 做法 |
|---|---|---|
| 1 | #125 開局在主城 | 新角色由 API 建在主城（`trpg.api.world.spawn_region`：有 `world/newcomer.yaml` 且有主城地點圖時是 `capital`，站在主城實地地圖的 `entry`＝中央廣場傳送石旁）。`new_character` 本身不變（仍照傳進來的區域）。 |
| 2 | 第一次傳送免費 | 不加旗標。條件＝「在主城、`visited_towns` 沒有新手區」（`trpg.world.atlas.free_first_teleport`）。成立時：區域傳送（`teleport`）可以去雲嶺；傳送石（`use_teleport_stone`）可以直接去霧渡鎮的傳送石（`free_first_stone`，**不寫進 `teleport_stones`**）；大世界圖上雲嶺顯示「已開放」；站在主城傳送石上時，選單列出霧渡鎮。到過霧渡鎮後照 #120 一般規則（霧渡鎮的傳送石要自己走到過才解鎖）。「到過」選現成的 `visited_towns`（舊存檔建角時就有 `cloud_ridge`，所以不受影響）。 |
| 3 | 開場 | 主城第一個畫面跳一則對話框（共用 `DialogFrame`）：說書人、守印人兩句（玩法 PM 給的原文，放在 `newcomer.yaml` 的 `opening`，模型關閉時就用這兩句），下面「任務提示：到霧渡鎮找渡婆婆（站上中央廣場的傳送陣，或按 M 打開地圖傳送到雲嶺）」。每個角色只跳一次（本機）。這段沒有呼叫 LLM（`content/llm`、`src/trpg/llm` 沒碰）。 |
| 4 | 指引（U2） | `WorldView.guide`：還沒到過霧渡鎮＝「到霧渡鎮找渡婆婆」＋怎麼去；到了、還沒接新手任務＝「找頭上有「！」的渡婆婆說話」；任務追蹤器排在最前。追蹤器完全沒東西時寫「找頭上有「！」的人說話」（原本「—」）。 |
| 5 | 方向與出口（U3） | `QuestLogView.route_zh`：目前這一步的目標地點（`at_location`／`win_battle`），在區域地點圖上找最短路（只走看得到的地點，鄰居依 ID 排序），取下一站與目前實地地圖上通往它的出口，方向照出口在地圖的哪一邊。例：「往東邊的出口 → 渡口石階」「往東邊的出口 → 渡口石階（再往竹林小徑）」。人已經在目標地點時不顯示。追蹤器與任務面板都顯示。 |
| 6 | 主線建議（U4） | 新手任務鏈完成前，主線（`kind: main`）在「可以接的任務」、任務日誌與追蹤器標「建議先完成霧渡新手路」（`advice_zh`；任務名從內容取）。 |
| 7 | #99 戰鬥短提示 | 新手任務各步加 `teach`（`content/world/quests/cloud_ridge.yaml`，schema `BattleHint`），通用四種在 `newcomer.yaml` 的 `battle_hints`。戰鬥中 `WorldView.battle_hints`＝進行中任務目前這一步「在這裡打贏」的 `teach`＋通用四種。畫面（`client/src/world/battleHints.ts`、`client/src/ui/BattleHints.tsx`）照戰況判斷觸發，放在戰場上方既有的提示欄（`.board-toasts`，不是新的彈出層），一次一則；「知道了」關掉後下一則成立的才出；「不再顯示提示」全部關。每種每個角色只出一次（localStorage，鍵含角色 ID）。只影響畫面。 |
| 8 | #132 第一次閃現 | 導師任務鏈第 1 步「觀摩」改成「這次閃現，或之前閃過」（新的狀態型條件 `flashed`）；新手時的閃現在接導師任務時就算完成。`WorldView.lesson`：新手第 1 步完成、在城鎮、沒閃過、有靈感點、有戰鬥中用過的招＝閃現引導（說書人「剛才那一招還在你手裡發燙。」、導師「讓剛用過的招靈光一閃。」，列出可以閃的招）；閃過且 3 級以上＝改教重閃。畫面跳對話框，「打開成長面板（G）」或「略過」，每種每個角色只跳一次（本機）。閃現本身照原本的成長面板（06 6.34.3，組合器版變化），不另給點。 |

- 首頁副標題、建角說明的「從雲嶺的霧渡鎮出發」改成主城開局的說法。
- 沒做：C1～C3、#128～#130、U11～U15。

## 2. 版號

- **`WORLD_RULES_VERSION` 7 → 8**（`save.py` 文件字串已補第 8 條）：第一次免費傳送（`teleport`、`use_teleport_stone` 的判定）；任務條件多一種 `flashed`。
- `CHAR_FORMAT`（`trpg-char/6`）、wlog 格式（`trpg-wlog/7`）**不變**：沒有新的存檔欄位（「到過」用 `visited_towns`；提示與教學看過與否記在本機）。
- API 有新欄位：`WorldView.guide`、`battle_hints`、`lesson`，`QuestLogView.route_zh`／`advice_zh`，`QuestHereView.advice_zh`；已跑 `export_openapi` 與 `gen:api`。

## 3. 提示與文字清單

| 用途 | 文字 | 來源 |
|---|---|---|
| 開場・說書人 | 傳送陣的光暗了下去。你在樞島中央醒來，晶柱還在低鳴。五座浮橋斷在雲上，各自指向一個界域。 | 玩法 PM |
| 開場・守印人 | 新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。 | 玩法 PM |
| 指引（主城） | 到霧渡鎮找渡婆婆 | prompt |
| 指引（主城・怎麼去） | 站上中央廣場的傳送陣，或按 M 打開地圖傳送到雲嶺 | **暫定** |
| 指引（霧渡鎮） | 找頭上有「！」的渡婆婆說話 | **暫定**（筆記 U2 是「找頭上有『！』的人說話」，這裡加了名字） |
| 追蹤器空白 | 找頭上有「！」的人說話 | 筆記 U2 |
| 主線建議 | 建議先完成霧渡新手路 | 筆記 U4 |
| 方向格式 | 往東邊的出口 → 渡口石階（再往竹林小徑） | **暫定**（格式） |
| 第 1 場 `move_attack` | 點藍格移動，點紅框攻擊；每回合有 AP（開場） | 筆記 U1 |
| 第 2 場 `water_lightning` | 敵人站在水上，雷電會擴散（有敵人站在水面上時） | 筆記 U1 |
| 第 2 場 `freeze_water` | 冰凍會把水變成冰（戰場上有水面時） | 筆記 U1 |
| 第 3 場 `reaction_auto` | 反應技能在敵人行動時自動觸發（主角有反應規則，或有人的反應觸發了） | 筆記 U1 |
| 通用 `ice_surface` | 冰面很滑：走上去要過敏捷判定，失敗會摔倒並滑出去 | **暫定** |
| 通用 `trap_tile` | 格子上有陷阱：踩到就會觸發，能繞就繞 | **暫定** |
| 通用 `lethal_terrain` | 深淵、岩漿、冰窟是致命地形：被推進去會直接倒下，別背對它站 | **暫定** |
| 通用 `pushed` | 被推撞時撞到人或牆會多受傷：別貼著隊友或牆站成一排 | **暫定** |
| 閃現教學 | 說書人：剛才那一招還在你手裡發燙。／導師：讓剛用過的招靈光一閃。 | #132 |
| 重閃教學 | 導師：閃過的變化不滿意，可以重閃其中一次，換成別的變化（照樣花靈感）。 | **暫定** |
| 導師任務第 1 步 | 觀摩：在營火或城鎮完成一次閃現（新手時的第一次閃現也算） | 18.7.5 |

## 4. 截圖

| 檔案 | 內容 |
|---|---|
| `6f2_01_home` | 正式首頁（副標題改成主城開局） |
| `6f2_02_create` | 建角（人類・雲嶺出身・雷電法杖・帶電＋潮濕） |
| `6f2_03_capital_opening` | 主城中央廣場醒來：開場兩句＋任務提示；右側追蹤器是指引 |
| `6f2_04_capital_stone` | 站上主城傳送石：「傳送：霧渡鎮」（還沒走到過也列出） |
| `6f2_05_mist_ferry_guide` | 傳到霧渡鎮：追蹤器換成「找頭上有「！」的渡婆婆說話」 |
| `6f2_06_granny_advice` | 渡婆婆：新手路照常、主線標「建議先完成霧渡新手路」 |
| `6f2_07_tracker_route` | 接下新手路：追蹤器「往東邊的出口 → 渡口石階」 |
| `6f2_08_ferry_steps` | 到了渡口石階（在目標地點，方向那行不顯示） |
| `6f2_09_battle_hint` | 第一場開戰：「點藍格移動，點紅框攻擊；每回合有 AP」 |
| `6f2_10_battle_hint_next` | 關掉後出下一則（這張地圖有致命地形） |
| `6f2_11_battle_hint_800` | 800×600 的提示列（改完不折行的前一張；之後加了 nowrap） |
| `6f2_12_flash_lesson` | 打贏後回霧渡鎮：閃現教學（列出「雷槍」） |
| `6f2_13_growth_panel` | 「打開成長面板（G）」 |
| `6f2_14_flash_options` | 閃現「雷槍」的 4 個變化（組合器版） |
| `6f2_15_after_flash` | 選完，教學不再出現 |
| `6f2_16_tracker_1600_hover`、`6f2_17_tracker_800_hover` | 追蹤器說明卡（6.5.1 實測） |

第一場戰鬥是手動開戰看提示；打完那場是用效用 AI 代打（`auto_steps`，只動自己的暫存存檔 `scratchpad/f2/saves`），再回到網頁繼續。

## 5. 6.5.1 與排版

- 追蹤器每一條仍是共用 `<Hint>`；實測「滑過 → 滑進卡片 → 卡片內捲動 → 點一下釘住 → 移開仍在 → Esc 關閉」：**1600×900、800×600 都通過**，卡片在畫面內（800×600 時追蹤器自動收合，先點開再測）。追蹤器高度 112 → 150（多了方向與建議兩行），800×600 時內容沒被裁（scrollHeight＝clientHeight）。
- 戰鬥短提示、開場、閃現教學都不是新的彈出層：提示放在既有的 `.board-toasts` 欄，對話框用 `DialogFrame`。沒有 `title=`。`floatCardRule.test.ts` 通過。
- 排版煙霧檢查在 `/?dev=1&anim=0.1`（先 `localStorage.clear()`）：1600×900、1040×624、800×600 的 `runCase` 與 `runScreens` **全 PASS**。注意：伺服器要帶 `TRPG_DEV_ROUTES=1`，`runScreens` 的戰後畫面才進得去（沒帶時 6 項 Not Found，不是版面問題）。

## 6. 檔案

- Python：`src/trpg/content/world_newcomer.py`（新）、`src/trpg/content/world_quests.py`（`teach`、`Flashed`）、`src/trpg/content/library.py`、`src/trpg/world/atlas.py`、`src/trpg/world/town.py`、`src/trpg/world/field.py`、`src/trpg/world/quests.py`、`src/trpg/world/save.py`、`src/trpg/api/world.py`、`src/trpg/api/world_newcomer_view.py`（新）、`src/trpg/api/world_presenter.py`、`src/trpg/api/world_schemas.py`、`src/trpg/api/world_story_schemas.py`、`src/trpg/api/world_field_view.py`
- 內容：`content/world/newcomer.yaml`（新）、`content/world/quests/cloud_ridge.yaml`
- 前端：`client/src/ui/BattleHints.tsx`（新）、`client/src/world/battleHints.ts`（新）、`client/src/world/OpeningDialog.tsx`（新，含閃現教學）、`client/src/screens/BattleScreen.tsx`（只加 `hints` prop 與一行掛載）、`client/src/screens/WorldScreen.tsx`、`client/src/screens/HomeScreen.tsx`、`client/src/world/WorldHud.tsx`、`client/src/world/hud.ts`、`client/src/world/NpcPanel.tsx`、`client/src/world/QuestLog.tsx`、`client/src/world/WorldCharacterPicker.tsx`、`client/src/styles/world-hud.css`、`client/src/styles/battle-layout.css`、`client/src/api/types.ts`、`client/src/api/schema.d.ts`、`client/openapi.json`
- 沒碰 `client/src/render/`、`client/src/battle/`、`content/llm/`、`src/trpg/llm/`、傭兵內容。
- 測試：新增 `tests/world/test_newcomer_6f2.py`（10）、`tests/world/test_first_flash_6f2.py`（4）、`tests/api/test_newcomer_api_6f2.py`（5）、`tests/content/test_newcomer_content_6f2.py`（3）、`client/src/world/battleHints.test.ts`（9）、`client/src/world/tracker6f2.test.ts`（5）；修改 `tests/api/conftest.py`、`pyproject.toml`（marker）。

## 7. 測試

- Python：`tests/world tests/api tests/content`（`-n 8`）**4322 通過、1 略過、0 失敗**。
- client：vitest 全部 **224 檔、2434 個**：一次全跑時 `src/render/inkCreature.test.ts`「全組合自測」失敗 1 個，單獨重跑 15/15 通過（render 沒動；判斷是全跑時負載造成的逾時）。`corepack pnpm -C client build` 通過。
- 每次 commit 前：ruff check、ruff format --check、mypy src、lint-imports、swamp 種子 7 重播（88 動作、313 事件，一致）。
- 重播：免費傳送（區域與傳送石兩種）、第一次閃現＋接導師任務，各自重播兩次逐字一致。

## 8. noqa

無新增。

## 9. 待 PM 決定

1. **舊的世界 API 測試怎麼建角**：6F-2 以前的 `tests/api` 世界測試都假設建角後在雲嶺小鎮（約 100 個）。我在 `tests/api/conftest.py` 加了 session 範圍的 fixture，讓它們照舊在 `START_REGION` 出生；測開局的測試標 `@pytest.mark.capital_spawn` 走正式流程。要不要之後逐一改成從主城出發，請開發 PM 決定。
2. **看過與否記在本機**：戰鬥提示「每種每個角色只出一次」、開場、閃現教學「只跳一次」都記在 localStorage（設計文件沒寫記在哪；保守做法，不動存檔格式）。換電腦或清瀏覽器資料會再出現一次。要記在角色上的話要加欄位、升 `CHAR_FORMAT`。
3. **「不再顯示提示」關掉後沒有地方再打開**（只能清本機資料）。要不要放進設定齒輪，請美術／玩法 PM 決定。
4. **3 級時還沒閃過的人**：設計寫「升到 3 級時導師改教重閃」。我的做法：閃過的人到 3 級教重閃；3 級還沒閃過（之前略過）的人照樣先教閃現（沒有東西可以重閃）。請玩法 PM 確認。
5. **閃現教學只在城鎮**（任何城鎮，含主城）出現；營火不跳（06 6.34.3 營火也能閃）。#132 寫「回到霧渡鎮時」，所以保守只做城鎮。
6. **主城傳送石的選單**：原本站在傳送石上只列「走到過的」傳送石（主城的傳送石雖然一開始就解鎖，但從別的傳送石的選單裡不列）。我只多列了第一次免費的那顆霧渡鎮傳送石，沒改原本的行為。主城傳送石要不要在其他傳送石的選單列出，是另一題。
7. **通用提示的觸發**：「被推撞」只看我方有強制位移（`unit_moved` 的 `forced`）；「反應」在主角有任何反應規則時開場就成立（預設都有藉機攻擊，所以第 3 場一開場就出）。若要改成「第一次有人觸發反應時」才出，改 `battleHints.ts` 的一個分支即可。
8. **暫定文字**：第 3 節標「暫定」的 9 句，請玩法 PM 確認。
9. **開場只在還沒到過霧渡鎮時有**：舊角色（已到過）不會跳；新角色若在主城就先跳去別處（只能去雲嶺）也不影響。
