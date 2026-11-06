# Phase 6C-6 完成報告：區域圖（只能看）＋傳送石

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-6 列。依據：`docs/design/21-探索地圖與城鎮.md` 21.1、21.2、21.6、21.9 第 1、3、13、14 條；`Phase6B-2報告.md`、`Phase6B-5報告.md`、`Phase6A-4f報告.md`。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 去過的地點 | `world/state.py`：`CharacterState.visited_locations`（`LocationRef`，排序、不重複）、`has_visited`；`CHAR_FORMAT` 升成 `trpg-char/4`（`/1`～`/3` 照讀）。`world/town.py`：`with_visited_location`。`world/step.py`：建角時記下起始小鎮；`world_step` 換了地點時記下出發與抵達的地點 |
| 從城鎮傳送 | `world/field.py`：`teleport_origin`（站在傳送石上＝那一顆；在城鎮裡，含室內＝城鎮室外圖的第一顆；其他＝`None`）；`use_teleport_stone` 改用它，錯誤訊息改成「要站在傳送石上或在城鎮裡才能傳送」 |
| 季末重置 | `server/season_policy.py`：`visited_locations` 歸為數值類（同 `revealed`） |
| 伺服器（只加欄位） | `api/world_schemas.py`：`WorldLocationView.fog`、`quest_marks`；`WorldMapView.stones`（新的 `RegionStoneView`：`id`、`location`、`unlocked`、`here`）、`can_teleport`、`teleport_problem_zh`、`art_url`（插畫路徑，現在一律 `None`）。新檔 `api/world_region_view.py`（迷霧、任務標記、傳送石）；`world_presenter._map_view` 最後呼叫它。OpenAPI 與 `schema.d.ts` 已重產 |
| 前端 | 新檔 `world/RegionMap.tsx`（面板）、`world/regionModel.ts`（純函式）、`styles/region-map.css`；`screens/WorldScreen.tsx` 接上 M 鍵與地圖鈕；`WorldHud.tsx` 地圖鈕說明改成「區域圖（M）」、開著時亮框 |
| 測試 | `tests/world/test_region_teleport.py`（12 個）；`client/src/world/regionModel.test.ts`（9 個）；`tests/world/test_field.py` 拿掉「在城鎮入口不能傳送」那一筆（規則改了，改測在新檔） |
| 截圖 | `docs/art/6c6_town_teleport.jpg`（在霧渡鎮打開，可以傳送）、`docs/art/6c6_field_viewonly.jpg`（在雨中梯田、沒站在傳送石上打開，只能看） |

## 2. 規則細節

**迷霧三段**（後端算，`fog`）
- 去過＝`visited_locations` 中這一區的地點，加上目前位置、到過小鎮那一區的城鎮（舊存檔沒有紀錄時也看得到）。
- 剪影＝和去過的地點有連線（只算畫出來的連線，隱藏地點未發現時不算）但沒去過。
- 其他＝霧。隱藏地點在發現前照舊不在回應裡，所以三段都不會出現。
- 前端：去過的顯示名字、建議等級、清空狀態、任務標記；剪影是灰點、「？？？」與建議等級；霧只畫一團雲，沒有名字、等級、標記。霧裡的連線不畫；兩端都去過是實線，一端是剪影是虛線。
- `cleared`、`name_zh` 在回應裡照舊（舊節點圖還在用）；區域圖在前端依迷霧隱藏。

**記錄去過**
- 只在「換了地點」時記（出發與抵達都記），不換地點的動作（聊天、敘述等）角色狀態不變，既有「動作不改數值」的測試照舊通過。
- 確定性：只看動作前後的 `region`、`location`，排序後存。
- 日誌不升版：這只是另外記下來，不改任何規則；舊日誌重播的其他結果不變。

**從圖上傳送**
- `can_teleport`：站在傳送石上或在城鎮裡，而且沒有戰鬥、遭遇、閃現、三選一待選。
- 可以點：`can_teleport` 而且已解鎖、不是現在出發的那一顆。點了送 `use_teleport_stone`，面板關掉。
- 其他時候：已解鎖的傳送石也畫鎖頭，滑過說明原因；還沒解鎖的畫灰色加鎖頭，說明「先親自走到這顆傳送石」。
- 傳送石只列在去過或剪影地點的室外圖上（霧裡的不給）；室內圖的傳送石不列（`use_teleport_stone` 本來就不能傳到室內）。只列本區，跨區是 6D-5 的大世界圖。

**任務標記**：進行中任務的目前這一步，條件是 `at_location` 或帶地點的 `win_battle`，就標在那個地點（依任務 ID）。霧裡的地點不標。

**面板**：M 或右上地圖鈕打開，再按 M、Esc、點 ×、點外面關閉。開著時功能列的快捷鍵不作用（只認 M、Esc）。進戰鬥或離開實地地圖時自動收起。

## 3. 測試與實測

- 後端：`uv run pytest -n 8 tests/world tests/api tests/server tests/test_architecture.py`：1531 passed、1 skipped。`ruff check .`、`ruff format --check .`、`mypy src`（505 檔）、`lint-imports`（13 kept）通過。
- 前端：`vitest`（`regionModel`、`mapView`、`hud`）81 passed；`tsc --noEmit` 通過；`pnpm build` 通過。
- 實測：自己開的伺服器（埠 8303、暫存存檔、Mock LLM、直接掛 `client/dist`，沒有開 vite，因為 vite 的代理寫死 8000），1040×720。
  - 新角色在霧渡鎮按 M：霧渡鎮彩色、相連的三處是「？？？」、其他是霧；「可以傳送」。
  - 改存檔加上幾個去過的地點與傳送石：在霧渡鎮點雨中梯田的傳送石 → 傳過去；站在傳送石上再開，霧渡鎮的變成可點。
  - 往下走一格再開：「只能看」，傳送石都是鎖頭；點了不送動作、位置不變。
  - M 開關、Esc 關閉、連按 Esc 再 M 都正常（一開始連按會失靈，改成同步的開關後修好）。

## 4. 待 PM 決定

1. **在城鎮裡傳送是改了引擎外的世界規則**：`use_teleport_stone` 原本只認「站在傳送石上」；照 21.1「站在傳送石上或城鎮裡」，在城鎮裡（含室內）也可以，出發的那一顆記成城鎮的傳送石。不需要先解鎖城鎮的那一顆。
2. **朋友足跡沒有畫**：現有的足跡資料只有 `travel` 日誌與首殺，而且要掃整份日誌，不適合放進每次的世界畫面；6B-4 也在改朋友相關的欄位。區域圖先不畫，等足跡改成實地地圖上的標記（21.6）時再接。
3. **「第一次親自走過渡口，荒原才亮起」**（21.9 第 4 條）：這是大世界圖的事，留給 6D-5；`visited_locations` 已經可以拿來判斷（有沒有到過 `ashen_waste` 的灰渡口）。
4. **剪影的連線**：剪影地點之間（兩端都沒去過）的連線不畫，只畫至少一端去過的。如果想讓玩家看到更多路，可以改成兩端都不在霧裡就畫。
5. **任務標記的範圍**：只標「到達」與「在某地點打贏」的步驟；聊天（NPC）、情境、旗標類的步驟沒有固定地點，不標。也沒有標「可以接的任務」。
6. **城鎮自己的傳送石**：在城鎮裡時顯示「你在這裡」，不能點；沒走上去也一樣。
7. **舊存檔**：`visited_locations` 是空的，只看得到目前位置與到過小鎮的城鎮；之後走動才慢慢補上。沒有從日誌回推。

## 5. 備註

- 沒有改引擎、`world/battle.py`、`field_enemies.py`、`WorldField.tsx`、render。`world_step` 只加了一段（`with_visit` 之後），6C-2 合併時可能在同一區附近，衝突應該很好解。
- `CHAR_FORMAT` 升成 `trpg-char/4`；如果 6C-2 也升版，合併時要再往上加一號。
- 區域插畫：`WorldMapView.art_url` 有值時，`.region-map-canvas` 用它當背景，節點照座標疊在上面；內容檔還沒有放插畫路徑的欄位（等有插畫時在 `world/maps/<region>.yaml` 加一個選填欄位即可）。

## 6. Commit

- `2a473869` feat(world): visited locations, town teleport origin, region map fog and stones (6C-6)
- `e6f01ea6` feat(client): read-only region map with fog, markers and stone teleport (6C-6)
- `deb14288` fix(client): region map M/Esc toggle uses a sync ref; 6C-6 screenshots
