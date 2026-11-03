# Phase 6B-4 完成報告：霧渡鎮城鎮互動（建築、NPC、室內、朋友）

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 1 節 6B-4 列、5.3；21.5、21.7；`Phase6B-3報告.md` 待決 2、3；`Phase6B-5報告.md`（「這裡」面板、浮動面板框）；`Phase6C-3報告.md`。
> 開工前已 `git merge main`（含 6B-3、6B-5、6B-6、6C-3，沒有衝突）。沒有改引擎、`src/trpg/world/`、`content/`，也沒有動 `camera.ts`、`HudIcons.tsx`（功能列圖示）。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| NPC 好感與「！」、朋友站位、外觀（純顯示） | 新檔 `src/trpg/api/world_field_people.py` |
| 欄位（只加不改） | `world_field_schemas.py`：`FieldNpcView` 加 `rank`、`rank_zh`、`alert`、`alert_zh`、`look`；新 `FieldFriendView`；`FieldView.friends`。`chronicle_schemas.py`：`ChronicleHeroView`、`ChronicleKillView`、`ChronicleBoardView` 加 `character_id`（朋友名片只列他的紀錄） |
| 組裝 | `world_field_view.py`：NPC 改由 `_npcs()` 組（帶好感與「！」）、加 `friends`；主角外觀抽成共用的 `look_of()` |
| OpenAPI | `client/openapi.json`、`client/src/api/schema.d.ts` 重產 |
| 頭頂圖示層 | 新檔 `client/src/world/FieldHeads.tsx`（表情、「！」、對話泡泡、朋友名牌）、`fieldPeople.ts`（純函式）、`fieldPeople.css` |
| 浮動面板 | 新檔 `client/src/world/FieldPanels.tsx`：`HudNpcPanel`、`HudHirePanel`、`FriendCard` |
| 接線 | `WorldField.tsx`（圖示層、朋友名單凍結、泡泡、點朋友直接開名片）；`fieldModel.ts`（NPC／朋友單位、`friend` 目標、說明列）；`hud.ts`（面板 `npc`、`hire`、`friend`）；`NpcPanel.tsx`（`only` 屬性）；`screens/WorldScreen.tsx`（互動改開對應面板） |
| 不畫血條 | `battle/drawModel.ts` 的 `UnitDraw` 加選填 `noBar`；`render/unitSprite.ts` 一行：`noBar` 時不畫小血條（戰鬥單位不受影響） |
| 測試 | 新檔 `tests/api/test_world_field_people.py`（14 項）、`client/src/world/fieldPeople.test.ts`（21 項）；`fieldModel.test.ts` 夾具補欄位、NPC 說明列的預期值 |
| 截圖（寬 800） | `docs/art/6b4_street_npcs.jpg`、`docs/art/6b4_tavern_interior.jpg`、`docs/art/6b4_friend_shadow.jpg` |

## 2. 對照規格

**1. NPC 站在街上與室內**
- 人設卡和內容都沒有外觀資料，所以 `look` 一律是 `null`。前端照舊用預設紙娃娃（範本 `npc_<id>`）。欄位已經留好，之後有外觀資料就直接套用。
- NPC 和朋友頭上**不畫小血條**（6B-3 待決 3）。主角照畫。
- 好感表情：照 5 級畫成 SVG 小臉，嘴的彎度依序是：敵視 −1（另有皺眉）、冷淡 −0.5、中立 0、友善 0.6、信賴 1。臉色也分級。
- 「！」由伺服器的 `alert` 決定（見待決 1）。金底是有任務，淡藍底是有傳聞，會輕輕上下跳。滑過時說明列顯示「渡婆婆（好感：中立・有任務可以接）」。
- 對話泡泡（21.7）：這次請求 NPC 說的話，取前 1～2 句、最多 40 字，約 6 秒後收起；換地圖時也收起。

**2. 走到旁邊（或按 E、點它）就開面板**
- 都用 6B-5 的面板框，同時只開一個，不再捲動整頁（6B-3 待決 2）：

| 目標 | 開啟 |
|---|---|
| NPC | 新面板 `npc`：頭像（好感表情）、名字、「！」說明，下面只有這位 NPC 的說話、聊天和他給的任務 |
| `hire` | 新面板 `hire`：隊伍加上直接展開的雇用清單；不能雇用時寫出理由 |
| 朋友 | 新面板 `friend`：名片 |
| 其他設施 | 照 6B-5（商店、鐵匠、公告板、成長；酒館送 `tavern` 並開「這裡」） |

- 點頭上的圖示，等於點那個人。

**3. 室內**：6B-2 已經支援進門換圖。室內的 NPC 與設施走同一套（石記鐵鋪的石師傅一樣有表情與「！」）。
- 實測走進霧渡鎮酒館，點雇用櫃檯會開 `hire` 面板。
- 酒館室內圖本身沒有 NPC（6C-3 的內容），截圖裡只有櫃檯。

**4. 朋友（影子）**
- 對象：其他角色在這個城鎮存的影子（#102：在城鎮整備後就會存），不含自己。
  - 只在城鎮的主地圖出現，室內沒有。
  - 依主人 ID 排序，最多 8 位。
- 位置（確定性）：
  - 候選格是從入口走得到的可站格，扣掉入口、出口、門、傳送石、設施、營火、事件點、情境物件。候選格依（y, x）排序。
  - 取 `fnv1a64(主人 ID) % 候選數` 那一格；撞到別的朋友就往後找下一格。
  - 沒有用 `hash()`，也沒有用亂數。
- 不即時（21.5）：
  - 伺服器每次都照當下算。
  - 前端在同一張地圖上沿用進來時的名單（`frozenFriends`）；換了地圖（進城、進出室內）才換新名單。
- 畫法：用存影子時的外觀（範本、`doll_look`、武器、裝備；不含共鳴詞條），頭上一個紫色「影」名牌，沒有血條。
- 點了直接開名片，不用走過去：
  - build 來自 `PartyView.shadows`：等級、定位、技能、稱號、存的地點、借用上限。
  - 編年史：讀 `GET /api/world/chronicle`，用新的 `character_id` 只列他的季末紀錄、首殺、賽季 Boss 評分。

## 3. 測試與實測

**後端**
- 這次跑的測試都通過：`test_world_field_people.py`、`test_world_field_api.py`、`test_openapi_snapshot.py`、`test_world_league.py`、`test_title_display.py`、`test_season_reset_api.py`、`test_world_party_api.py`，共 38 項。
  - 表格測試：好感級別與「！」共 10 種情況，涵蓋任務、傳聞、聊過、敵視、冷淡、友善的任務入口、已接。
  - 畫面上的 NPC 帶好感與「！」、`look` 為空。
  - 朋友站位：和名單順序無關、重跑結果相同、不重疊、都是可站格而且不在保留格、單人時只看自己的 ID。
  - 朋友只在城鎮主地圖出現、不含自己、隔一小時位置不變、室內與沒有世界狀態時為空、最多 8 位。
- 其他檢查：
  - `ruff check .`、`ruff format --check .` 通過。
  - `mypy src`（504 檔）通過。
  - `lint-imports`：13 kept。
  - swamp 種子 7 重播通過（88 個動作、313 個事件）。

**前端**
- `vitest run src/world`：18 個檔、226 項通過。新的 `fieldPeople.test.ts` 有 21 項：
  - 表情表格；
  - 「！」與表情對應；
  - 頭頂圖示層：3 張臉、2 個「！」、朋友只畫名牌；
  - 頭頂位置會扣掉抬高；
  - NPC 與朋友 `noBar`、主角沒有；
  - 預設範本與朋友的外觀；
  - 朋友的點擊、說明列、E 鍵；
  - 名單凍結；
  - 編年史篩選；
  - 泡泡；
  - NPC、雇用、朋友三個面板的內容與可開條件。
- `tsc --noEmit`、`pnpm build` 通過，只有原本就有的 chunk 大小警告。
- `vitest run src/ui` 有 1 項原本就失敗，和這段無關：`floatCardRule.test.ts` 抓到 `world/WorldHud.tsx` 的 `role="dialog"` 不在白名單。這是 6B-5 的檔案，我沒有改它（見待決 6）。

**自己開伺服器實測**
- 環境：API 8301、vite 5304（暫存設定，已刪），存檔放 scratchpad 的暫存資料夾。用完兩個程序都停了；vite 的子程序是用它自己監聽 5304 的 PID 結束的。
- 開發模式（不用登入）建了兩個角色：
  - 「阿博」：休息一次，存下影子。
  - 「阿霧」：進霧渡鎮。
- 結果：
  1. 阿博的影子站在 (14, 8)，頭上有「影」，沒有血條。渡婆婆頭上是「！」（任務），柳掌櫃是「！」（傳聞），兩人都是中立臉，都沒有血條。
  2. 點阿博：開名片，顯示「Lv 1・火焰法杖・存在霧渡鎮」、技能「火球、烙印」，編年史寫「還沒有紀錄」。
  3. 點渡婆婆：走到旁邊，開 NPC 面板（頭像、只有她和她給的兩個任務）。按「說話」後關掉面板，她頭上出現泡泡。
  4. 點酒館的門：換到酒館室內。點雇用櫃檯，開出雇用面板（隊伍＋傭兵 9、影子 1）。

## 4. 待 PM 決定（都已照最保守的做法做完）

1. **「！」的條件**（規格只寫「有新傳聞或可接任務」）：
   - `quest`：這位 NPC 給的任務還沒接、開始條件成立、沒有敵視；或他依目前好感聊得出指向還沒接的任務入口（例：柳掌櫃友善時的藥師谷洞窟）。
   - `rumor`：今天（6 點刷新）還沒和他說過話，而且他依目前好感聊得出傳聞。所以中立以上的 NPC 每天都會亮一次，說過話就消失。
   - 兩種都有時顯示 `quest`。
   - 伺服器沒有記「聽過哪幾條傳聞」，所以「新」用「今天還沒聊」代替。如果要「沒聽過才算新」，需要在角色狀態加欄位（`src/trpg/world/` 的範圍）。
2. **NPC 外觀**：人設卡沒有外觀欄位，`FieldNpcView.look` 先一律是 `null`，NPC 用預設紙娃娃。要分辨不同 NPC，需要美術或內容補外觀資料。
3. **朋友的範圍**：沒有好友系統，所以「朋友」＝其他角色在這個城鎮存的影子，最多 8 位（依主人 ID）。要有好友名單時再加篩選。
4. **改到 `client/src/render/unitSprite.ts` 一行、`battle/drawModel.ts` 一個選填欄位**：渲染器原本一定畫血條，不改就做不到「NPC 不畫血條」。戰鬥單位沒有這個欄位，行為不變。
5. **頭頂圖示用 DOM 疊在畫布上**（跟著鏡頭平移），不是畫進 Pixi。這樣方便點擊和測試，也不動渲染器；缺點是不會被前景的建築遮住。NPC 站在主角正下方一格時，他的圖示會疊在主角身上（見街上的截圖）。
6. **原本就有的前端測試失敗**：`src/ui/floatCardRule.test.ts` 抓到 6B-5 的 `WorldHud.tsx` 浮動面板 `role="dialog"` 不在白名單。我沒有改；應該把它加進白名單，或改成白名單裡的 `DialogFrame` 類元件。
7. **朋友名片的編年史**：每次打開名片都讀一次 `/api/world/chronicle`（全部季），在前端篩出這個人的紀錄。資料量大了以後，可以改成伺服器端篩選。
8. **建築外觀**：設施的建築造型由 6C-3 的地圖內容畫（牆、屋頂），這段沒有另外加設施標記。像酒館裡的雇用櫃檯，只有滑過時說明列寫出名稱。
