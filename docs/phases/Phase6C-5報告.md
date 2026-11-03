# Phase 6C-5 完成報告：地圖上的東西

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-5 列、0.4 Q7。依據：21.4、21.6、21.9 第 8～12、14 條、21.10 第 6、9 條；09 9.6.11 #112、#114；6C-1b／6C-3／6C-4／6D-1／6D-2／6D-4／6B-5／6C-6 報告。開工前已 `git merge main`（含 6C-2、6C-6，無衝突）。

> 沒有改引擎（`src/trpg/engine/`）、戰鬥畫面元件、`client/src/render`、`WorldField` 的移動動畫。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 感知判定抽出共用 | 新檔 `world/perception.py`（`perception_modifier`、`reveal_location`、`can_perceive`、`perceive`）；`world/step.py` 改用它（`perception_modifier`、`reveal_location` 照舊從 `step` 匯出） |
| 地圖上的東西 | 新檔 `world/field_things.py`：隱藏入口感知、事件「！」放置與開卡、營火判定、情境物件、潛行 |
| 走路的鉤子 | `world/field.py`：`FieldHooks.sense`（走完一段、觸發出口前）、`touches_event`、停下原因加 `"event"`；`step._HOOKS` 的 `arrive` 改成「6C-1 的 arrive_watch ＋ 抵達格感知」 |
| 動作與事件 | `world/field_actions.py`：`SneakAction`（`sneak`）、`UseFieldObjectAction`（`use_field_object`）、`SneakStartedEvent`、`EventMarkedEvent`、`FieldObjectUsedEvent`；併進 `WorldAction`／`WorldEvent` 與 API 的 `WorldActionRequest` |
| 角色狀態 | `world/state.py`：`FieldEventMark`、`ObjectUse`；`CharacterState.field_event`、`sneaking`、`object_uses`；`trpg-char/5` |
| 敵人 | `world/field_enemies.py`：`sight_range`（潛行減半）、`FieldSpawn.until_quest` 過濾 |
| 內容格式 | `content/fields.py`：`FieldSpawn.until_quest`；`FieldSpot` 加 `name_zh`、`use`（note／event／encounter）、`event`、`note_zh`、`requires_thread`、`requires_flag`、`locked_zh` |
| 內容 | 新手固定戰 3 隊加 `until_quest: starter_ferry`；情境物件 11 個寫上用途與說明（見 3.4） |
| 亂數 | `world/rng.py`：新串流 `spot`（挑事件點，候選 >1 才抽） |
| 存檔 | `trpg-char/4` → `/5`（只多選填欄位）、`trpg-wlog/5` → `/6`（照 6B-2 的做法：舊日誌照讀、標成規則已變不能重播）；`server/season_policy.py` 三個新欄位歸「數值類」 |
| API | `world_field_schemas.py`：`FieldView.campfires`、`event_mark`、`situation_objects`、`sneaking`、`sneak_cost`、`sneak_problem_zh`、`footprints`、`note_stone`；`WorldLocationView.footprints`。新檔 `api/world_field_things.py`（組這些欄位、`FieldSocial`、句子 `things_line`）；`WorldStore.field_social`；`world_view(..., social=)`。OpenAPI 與 `schema.d.ts` 已重產 |
| 前端 | `fieldModel.ts`（`thingMarks`、物件與石碑互動目標、滑過說明）、新檔 `FieldThings.tsx`＋`fieldThings.css`（情境物件說明卡、潛行畫面）、`hud.ts`（`sneakState`、R 鈕狀態）、`WorldScreen.tsx`（R 送 `sneak`、物件卡、石碑開留言板）、`RegionMap.tsx`／`regionModel.ts`（足跡標記）、`WorldField.tsx`（只加潛行的 class） |
| 測試 | `tests/world/test_field_things.py`（33）、`tests/api/test_world_field_things.py`（6）、`tests/content/test_field_spots.py`（4）、`client/src/world/fieldThings.test.ts`（14）；既有測試只改版號字串與 fixture 欄位 |
| 截圖 | `docs/art/6c5_marks_footprints.jpg`、`docs/art/6c5_object_card.jpg`、`docs/art/6c5_sneak.jpg` |

## 2. 規則怎麼落實

**1. 隱藏入口**（#112、21.9 第 10 條）
- 走路時逐格（實際走過的格子，含被敵人截短的路徑）檢查：`hidden_until: reveal` 且還沒發現的門，曼哈頓距離 ≤ 3，門通往的地點 `reveal` 有 `perception_nearby`、今天還沒判定 → 擲一次（`reveal` 串流，DC＝`perception.dc_for(level_min)`，和原本完全同一個函式）。走出口或門抵達新地圖時，抵達格也檢查一次；傳送不檢查。
- 成功：`revealed` 加入該地點 → 門可站、出現在畫面上；發 `PerceptionCheckEvent`＋`LocationRevealedEvent`（原本的句子）。失敗：記今天，同一天不再判。
- 抵達「有實地地圖的地點」時不再做舊的「對相鄰隱藏地點判定」（改成走到入口 3 格內）；沒有實地地圖的地點照舊。
- 丹爐洞的 `reveal` 只有 `situation`，所以藥師谷的洞口不會被感知發現（照內容）。

**2. 事件「！」**（21.6、21.9 第 9 條）
- `_travel` 照舊呼叫 `roll_event`（機率、骨架、保底、線頭優先都不變）。觸發時，若目的地有實地地圖：改放到地點的事件點（室外圖＋所屬室內圖），優先和骨架同名的事件點，沒有就全部事件點；候選 >1 用 `spot` 串流挑。`pending_event` 先不設，記在 `field_event`；事件列表裡的 `EventTriggeredEvent` 換成 `EventMarkedEvent`。
- 走路碰到（同一張圖、站上或四方向相鄰、沒有別的事件卡開著）就停下（`stopped="event"`），把事件搬到 `pending_event`（`at` 改成開卡的時刻，說書人敘述從這時算）並發 `EventTriggeredEvent`，之後的機遇保底、任務推進照舊吃這個事件。同一趟只開一次。
- 換地點（走出口、傳送、撤退、全滅）時沒碰到的「！」消失；地點沒有任何事件點時照舊直接開卡。
- 城鎮照現行會擲事件（非戰鬥），一樣放到事件點（霧渡鎮的 `tavern_storyteller` 在酒館室內圖上）。

**3. 營火**（#114）：站在 `campfires` 格子上時，「營地的敵人還在不能紮營」不算；城鎮、精英巢穴、Boss、遭遇中、補給不足照舊不行；花費照 `camp_cost`。已清空或非戰鬥地點照舊任意處可紮營。

**4. 情境物件**：站在旁邊（四方向相鄰或同一格）送 `use_field_object`。
- `event`：開這個地點的骨架（要在 `event_candidates` 裡：地點、時段、天氣、once、unlock_only 照舊），每個物件每天一次（`object_uses`），有事件卡開著時不行。情境判定照骨架的模板（`situation`／`event_solve` 照舊）。
- `encounter`：產生這個地點的遭遇（`make_encounter`，`from_location`＝原地），開戰照舊用 Boss 地圖（沒有接觸點，不切 12×12）。
- `note`：只有說明卡，不送動作。`requires_thread` 沒持有＝不顯示；`requires_flag` 沒開＝鎖住、顯示 `locked_zh`。

**5. 潛行**（Q7）：R 鈕／R 鍵送 `sneak`，花 `hasten.cost`（1）補給；`sneaking` 到「換地點」為止（走出口、傳送等都結束；進出室內不算換地點）。敵人視野距離 `4 // 2 = 2`（扇形與遮擋規則不變），畫面上的視野格也跟著縮。城鎮、室內、沒有實地地圖、遭遇中、已在潛行、補給不足時拒絕。沒有實地地圖的地點照舊用 `travel` 的 `hasten`。

**6. 新手固定戰**（21.10 第 9 條）：`FieldSpawn.until_quest`；角色的該任務 `done` 時那一隊不出現（只影響這個角色）。渡口石階、竹林小徑、雨中梯田的 3 隊寫 `until_quest: starter_ferry`。

**7. 朋友的足跡與留言標記**
- 來源：其他角色存檔的 `visited_locations`（6C-6）＋目前位置。`WorldStore.field_social` 依角色 ID 讀；已在記憶體的角色直接用，其他的依檔案修改時間快取（不放進 `_chars`、不觸發三選一預算），**不掃世界日誌**。每次世界畫面讀一次 `notes.json` 算留言數。
- 實地地圖：最多 3 位朋友（依角色 ID），每位在「入口與各出口內側一格」中依 `fnv1a64("<地圖>:<角色>")` 挑兩端，沿 BFS 最短路每隔一格畫一個「足」（最多 8 個）。所以腳印是「代表性的路」，不是真的走過的路。室內圖不畫。
- 留言石碑：地點有留言時，畫在入口附近第一個空的可站格（「碑」，點了開留言板）。
- 區域圖：去過或剪影的地點列出去過的朋友名字（最多 3 位），節點旁畫「足」，滑過看名字；霧裡不給。

**8. 確定性**：只看內容與角色狀態；事件點、門依內容順序；新亂數只有 `spot` 串流（且只在候選 >1 時抽）。足跡與石碑純顯示、不耗亂數。

## 3. 測試與實測

- 後端：`UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8`：見第 7 節。`ruff check .`、`ruff format --check .`、`mypy src`（510 檔）、`lint-imports`（13 kept）通過；`trpg content check` 通過（雲嶺 18／18、荒原 18／18、主城 1／1）。
- 表格測試（`test_field_things.py`）：感知成功揭露門（門可站、畫面出現）、失敗同一天不再判隔天再判、遠處不判、抵達時不再判相鄰；「！」放在同名事件點、碰到才開且只開一次、沒有事件點時直接開、離開就消失、城鎮放在酒館；營火上紮營（敵人還在的冬湖）、城鎮不行；祭壇開事件每天一次、只能看的物件／鎖住的通道／不存在的物件拒絕、要在旁邊、熔岩封口跟著旗標、暗門要線頭、觀門開 Boss 戰；潛行花補給視野減半、不能重複、城鎮與補給不足拒絕、到下一張地圖結束；新手固定戰 3 張圖 × 任務完成與否。
- 重播測試：感知揭露門後走進鶴歸崖、事件「！」開卡、潛行縮視野，各重播兩次逐字一致；角色存檔來回與 `/4` 舊檔照讀。
- 前端：`vitest run src/world src/screens` 21 檔 259 項通過（新 `fieldThings.test.ts`：標記與優先序、滑過說明、互動目標、潛行鈕三種狀態、物件卡、區域圖足跡）；`tsc --noEmit`、`pnpm build` 通過。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。
- 實測（自己開的伺服器，埠 8306、暫存存檔、Mock LLM、直接掛 `client/dist`，1040×720）：冬湖畫面有「！」、營火「火」、朋友腳印「足」、留言石碑「碑」；點營火旁走過去碰到「！」就開事件卡；雲頂觀站在觀門下按 E 開說明卡，按「挑戰」出現霧鎖真人的遭遇；斷崖幫寨潛行中，上方「潛行中」、視野縮成 4 格、R 鈕亮著。截圖是內建瀏覽器縮到 800×600 輸出的。

## 4. 接上與沒接上的情境物件

| 物件 | 接法 |
|---|---|
| `horned_fire_altar`（角魔祭壇） | `event: noon_altar`（只在白天合格，照骨架） |
| `fortress_stele`（廢墟要塞） | `event`（同名骨架） |
| `cooling_well_relic`（冷卻井） | `event`（同名骨架） |
| `summit_gate`（雲頂觀）、`pit_gate`（熔心坑） | `encounter`：Boss 戰 |
| `pit_lava_seal`（廢墟要塞） | 說明卡；`requires_flag: heart_pit_open`（沒開＝「還過不去」）。真正擋路照舊是熔心坑的 `unlock_flag` |
| `gang_fort_secret_door`（斷崖幫寨） | 說明卡；`requires_thread: gang_fort_secret_door`（持有才顯示）。先手效果照舊由遭遇表的 `ally_first_threads` 給 |
| `rift_mist_wall`（源晶裂痕） | **只有說明卡**：內容沒有「主線推進前擋住」的旗標（雲頂觀沒有 `unlock_flag`），所以不擋路 |
| `ash_well`、`iron_forge_anvil`、`red_sand_well`（三村落） | 說明卡（守點目標） |
| 主城 20 個（浮橋、石碑、守印人、書記等）、`capital_mentor_hall` 的 `scribe`／`grimoire_shelf` | **沒接**：照 6D-4 報告留給 6D-5 接面板；畫面上顯示為「物件」，點了是沒有文字的說明卡 |

另外：古松祭壇、劍冢等祭壇／遺跡的地圖上沒有情境物件（內容沒畫），所以沒有可接的。

## 5. 待 PM 決定

**規則類**

1. **營火點在敵人還在的營地上也能紮營**：#114「敵人還在的營地不能紮營」＋#120「另有固定營火點」，我解讀成營火點不受這條限制（不然營火點沒有作用，現有營火點在營地種類的只有冬湖）。其他限制（城鎮、精英巢穴、Boss、遭遇中）照舊。
2. **「！」要碰到才開，在那之前事件卡不出現**：玩家可以不碰直接離開，事件就消失（不記失敗、不算「放棄」）。距離上次事件的步數在擲出時就歸零（照「事件發生了」算）。
3. **「碰到」＝站上或四方向相鄰**，走路經過也會停下開卡；有事件卡開著時不觸發。
4. **城鎮事件也放「！」**：照現行城鎮會擲事件（21.10 第 5 條寫「城鎮不觸發事件」，但規格說「照現行」），放到事件點；霧渡鎮唯一的骨架事件點在酒館室內，要走進酒館才看得到。
5. **事件骨架的時段、天氣以擲出時為準**：碰到時如果已換時段，照擲出時的骨架（只更新 `at`）。
6. **情境物件開事件每天一次**（6 點刷新）；`once` 的骨架另外照 `once` 規則。Boss 門不限次數（同原本走進 Boss 地點）。
7. **潛行結束的時機＝換地點**：進出室內不算；傳送、撤退、全滅也會結束。
8. **潛行在城鎮與室內拒絕**（沒有敵人；避免白花補給）。
9. **新手固定戰「任務完成」＝整個 `starter_ferry` 完成**；任務還在進行（例如第 1 步做完）時，第 1 步的固定戰照 6C-1b 每趟重新出現。
10. **抵達有實地地圖的地點不再做「相鄰隱藏地點」的感知**（21.9 第 10 條改成 3 格內）。傳送抵達的那一格不判，下一步才判。
11. **霧牆不擋路**（見第 4 節）：要擋需要一個旗標（例如主線某步驟），請決定用哪個。

**數值／解讀類（照最保守的預設做完）**

12. 「3 格內」用曼哈頓距離；判定是逐格做，第一次進入範圍就判。
13. 事件點挑選：同名優先，否則全部事件點均勻挑（`spot` 串流）。
14. 足跡：最多 3 位朋友、每位最多 8 個腳印、畫在「代表性的路」上（不是真的路徑；真的路徑要記每一步，日誌與存檔都太大）。區域圖最多列 3 個名字。
15. 足跡的來源包含「所有其他角色」（目前沒有好友名單）；伺服器每次世界畫面讀一次所有角色存檔（有快取），角色很多時可能要改成世界快照裡的索引。
16. 留言石碑只有一塊、放在入口附近，不分每則留言。

## 6. Commit

- `93d8f2eb` feat(world): map things - hidden door perception, event marks, campfires, objects, sneak (6C-5)
- `bbba6536` feat(client): map things marks, object card, sneak button, footprints (6C-5)
- 報告與截圖：見最後一個 commit

後端 1～7 項做在同一個 commit（共用狀態欄位與存檔版號，拆開會有中間狀態測試不過），前端一個 commit。

**新增的 `# noqa`**（守則 12，都是參數個數 PLR0917，沒有複雜度類）：`perception.perceive`、`field_things._sense_doors`／`sense_walk`（和 `field.SenseFn` 同簽名）／`_event_problem`／`object_status`、`field_enemies._shown`（多了角色）、`api/world_field_things.things_update`、`world_presenter._map_view`（多了 `social`）；`footprint_cells` 一個 PLR2004（「兩個端點」）。

## 7. 測試結果（交件前）

- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8`：4141 passed、1 skipped。
- `ruff check .`、`ruff format --check .`（1935 檔）、`mypy src`、`lint-imports`（13 kept）通過。
- 前端：`vitest run src/world src/screens` 259 通過；`tsc --noEmit`、`pnpm build` 通過。
- swamp 種子 7 重播通過（88 動作、313 事件）。
