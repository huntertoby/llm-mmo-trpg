# Phase 6D-R1 報告：收尾審查整理①

規格：`docs/phases/Phase6計畫.md` 第 1 節 6D-R1 列＋專案 PM 派工的 8 點。
開工時 `git merge main` 已是最新（含 6C-R3，沒有衝突）。沒有改引擎，也沒有新增相依。

## 1. 安全：實地地圖靜態地形改成經角色取

- 舊路由 `GET /api/world/fields/{map_id}` 已移除。改成 `GET /api/world/characters/{character_id}/fields/{map_id}`（`src/trpg/api/routes/world.py`）。
  - 擁有者檢查沿用 `require_world_access`：別人的角色 404「找不到角色」，未登入 401。
  - 只給這個角色看得到的圖（`world_field_view.visible_field_map`），包括：
    - 目前地點的室外圖與它的室內圖；
    - 去過（`visited_locations`）的地點的室外圖與室內圖；
    - 已發現（`revealed`）的地點的室外圖與室內圖。
  - 看不到的圖和不存在的圖一樣回 404，訊息都是「找不到實地地圖 {map_id}」，沒辦法用狀態碼列舉地圖 ID。
- **隱藏門**：還沒發現的隱藏門格，地形畫成 `wall`（`HIDDEN_DOOR_TERRAIN`）、表面 `none`、不可站，和真的牆分不出來。
  - 靜態地形一律這樣畫。
  - 每個角色直接帶的地形（`inline_tiles`／`with_tiles=1`）照這個角色是否發現來畫，也不再洩漏。
- **`open_cells`**：型別從座標改成整格 `FieldTileView`。發現後，那一格的真地形（真的地形 ID、表面、可站）放在這裡，前端直接蓋在靜態地形上。這是 API 型別變更，OpenAPI 已重產。
- `GET /api/world/characters/{id}?with_tiles=1`：`field.tiles` 直接帶地形，給前端當退路。

## 2. `WORLD_RULES_VERSION`

- 位置：`src/trpg/world/save.py`，值為 `1`。
- 規則鍵改成 `戰鬥紀錄版號|w世界規則版號|規則包雜湊|內容 digest`。digest 範圍照 PM 決定維持全部內容。
- `docs/開發PM交接.md` 6.6 加一行說明何時要加一：世界規則程式改動、會讓同一份日誌重播出不同結果時，在同一個 commit 加一。
- **注意**：規則鍵的格式變了，現有存檔的世界日誌在第一次載入時會整份標成「規則已變、不能重播」，標頭重寫一次。這是引入版號的預期行為。

## 3. 殘行容錯集中到 `trpg.world.save`

- 新增 `log_lines(text)`，回傳（完整行, 有沒有丟掉殘行）。
  - `read_log` 與 `loads_log` 都經過它。
  - 連標頭都沒寫完時，回空的 `WorldLog(torn=True)`，不拋例外。
  - `WorldLog` 加 `torn` 欄位。
- 改用新函式的讀者：
  - `WorldStore.entries` 拿掉自己的 `_complete_lines`，改看 `log.torn`。
  - Bot 公告（`announce._active_on`，經 `loads_log`）。
  - 封存查證（`season_archive._log_entry`，經 `log_lines`）。

## 4. 內容檢查

- Boss 營火檢查也套用到室內圖：照室內圖所屬地點（`place`）判斷。
- 傳送石數量不足改成錯誤：
  - 城鎮不是恰好 1 個：錯誤。
  - 一區的野外傳送石不在 2～3 個：那一區的地點全部畫完時是錯誤；還沒畫完時記成待補（`pending`）。
- 目前內容沒有這類問題，`trpg content check` 通過（雲嶺 18／18、灰燼荒原 18／18、主城 1／1）。

## 5. 整理

- `world_field_view._static_grid` 併進 `field.field_grid`：`char` 可以傳 `None`，代表只看內容、隱藏門一律當未發現。另新增 `field.hidden_cells(char, found)`。
- `field._cross_region` 與 `step._cross_fn` 合一：
  - 地點查找與開放檢查只在 `_cross_region` 做一次。
  - `CrossFn` 改成接收（地點圖, 地點）；`_cross_fn` 只剩一次 `_travel_to`。
- `SenseFn`／`CrossFn` 的 docstring 位置修正。
- `visit_for`／`with_visit` 改成共用 `_next_visit`：同一次 `draw` 取種子，兩邊一定拿到同一個值。不再用 `peek`。

## 6. `tests/world/test_capital.py`

座標改成從內容推，不再寫死正式座標：

- 傳送石格：`_stone`；`entry`：`_entry`、`_off_stone`。
- 出口格：`_exit_cell`；門格：`_door_cell`。
- 主城裡走兩格：`_near`。

霧渡鎮是凍結複本，照舊寫死。

## 7. 前端

- `client/src/world/fieldTiles.ts`：
  - 快取的鍵只用伺服器回傳的 `hash`。
  - 同一張圖、同一個雜湊同時只發一個請求。
  - 失敗時重試一次；仍失敗就呼叫 `fetchInline`（`GET …/characters/{id}?with_tiles=1`）。
  - `withOpenCells` 改成整格覆蓋。
- `client/src/api/client.ts` 改用新路由。
- OpenAPI 已重產（`client/openapi.json`、`schema.d.ts`）。

## 8. 測試

- `tests/api/test_world_field_access.py`（新增）：
  - 權限表格：（自己／別人／未登入）×（目前地點、室內、去過、沒去過、隱藏未發現、隱藏已發現、未解鎖區、不存在）。
  - 舊路由已不存在。
  - 每一扇隱藏門（從內容推，含 herb_valley、north_slope、tar_pits）在靜態地形都是牆、無表面、不可站，那一格沒有物件。
  - `inline_tiles` 也會隱藏未發現的門；`with_tiles=1` 會帶地形。
- `tests/api/test_world_store_r3.py`：
  - `WORLD_RULES_VERSION` 加一時，日誌標成 stale。
  - 規則鍵有 4 段。
  - `read_log` 會略過殘行。
- 殘行容錯：`tests/api/test_announce.py`、`tests/server/test_season_archive.py` 各一個，寫到一半的檔案都不拋例外。
- Boss 室內營火錯誤，以及傳送石數量的錯誤與待補：`tests/content/test_fields.py`。
- 前端 `fieldTiles.test.ts`：快取只用回傳 hash、合併同時請求、重試一次、退回伺服器帶地形、整格覆蓋。
- 為配合新行為修改的既有測試：
  - `test_field.py::test_old_world_log_is_stale`：測試字串補上結尾換行（沒換行的最後一行現在算殘行）。
  - `test_world_field_r3.py`、`test_world_field_api.py`：改用新路由與新的 `open_cells`。

**結果**
- pytest：`tests/world tests/api tests/content tests/server tests/bot tests/test_architecture.py -n 8`：4311 通過、1 略過（開發模式開的擁有者檢查，原本就略過）。
- vitest：`fieldTiles`／`fieldModel`／`fieldPeople`／`fieldThings` 共 71 個通過。
- 其他檢查：
  - `tsc --noEmit` 通過，`pnpm build` 通過。
  - ruff、ruff format --check、`mypy src`（511 檔）、lint-imports（13 個契約）全過。
  - `trpg content check` 通過。
  - swamp 種子 7 重播通過（88 個動作、313 個事件）。
- 沒有新增 `# noqa`。

## 待 PM 決定

1. **哪些圖看得到**：已發現（`revealed`）但還沒走到的隱藏地點，以及去過的地點的室內圖，目前都給看。如果要更嚴，可以改成只給 `visited_locations`。
2. **隱藏門的偽裝**：隱藏門格保留真高度，地形換成牆。如果周圍的牆高度明顯不同，仍可能被看出來；要更保險的話，可以改用相鄰牆的高度。
3. **區域傳送石數**：那一區還沒畫完時記成待補，不算錯誤（不然局部地圖的表格測試全會失敗）。目前正式內容兩區都畫完了，所以實際上就是錯誤。
4. **城鎮傳送石不是 1 個**：也一起從警告升成錯誤（規格只點名區域數；這是保守的解讀）。
5. **現有存檔**：規則鍵格式改了，伺服器上現有的世界日誌第一次載入時會整份標成不能重播。
6. **封存查證**：只略過最後一行的殘行；檔案中間壞掉的行仍照舊拋例外，沒有放寬。`season_reset` 的日誌行數統計沒有改。
7. 新路由在 `h` 命中時照舊回 `Cache-Control: private, immutable`；網址含角色 ID，不會跨角色共用。
