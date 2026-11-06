# Phase 6D-R2 報告：收尾審查整理②

規格：`docs/phases/Phase6計畫.md` 第 1 節 6D-R2 列（6D-R 第 4、5、6 點）。不改引擎、不改規則。

## 1. 主城地點圖改成內容檔

- 新增 `content/world/maps/capital.yaml`：`hub: true`、1 個城鎮地點 `capital`（名稱「樞島」，同主城實地地圖）、沒有連線、`pos` 50／50。
- `LocationMapDef` 加 `hub`：只能有 1 個地點、不可有連線（還是要過「恰好 1 個城鎮」等既有驗證）。這種圖不查地點數 15～25，也不查 `regions.yaml`。
- 載入（`_load_world_maps`）：`hub` 的圖放進新的 `ContentLibrary.hub_maps`，**不進 `world_maps`**，所以區域清單、季末重置、內容進度都看不到它。只有 `region: capital` 可以標 `hub`，而且主城的地點圖一定要標，不然就是內容錯誤。
- 新增 `ContentLibrary.location_map(region)`：先查區域圖，再查樞紐圖。`world_map_of` 改成經過它，找不到時拋 `WorldError`，不會 `KeyError`。`capital_map` 留著，改成直接回傳 `world_map_of(…, "capital")`，`model_construct` 的臨時組圖拿掉了。
- 修掉直接索引的地方：
  - `world/encounters.py`：`roll_lineup`、`reinforce_lineup` 改用 `world_map_of`。`reinforce_lineup` 碰到沒有遭遇表的地點（主城、Boss 戰）會原樣回傳，不再 `KeyError`。
  - `api/absence_view.py`、`world/atlas.py`：改成迭代 `world_maps.items()`。
- `.get(region)` 的地方也統一改用 `location_map`：`notes_schemas`、`world_field_people._is_town`、`world_field_view._place_name`、`server/announce.location_name`、`world/narration`。這樣主城的地名顯示「樞島」，不會顯示 ID `capital`。
- 鍛造設施表原本寫死 `CAPITAL_REGION: {CAPITAL_LOCATION: "town"}`，改成從 `hub_maps` 推。
- 測試（`tests/world/test_capital_hub.py`）：
  - 內容檔與存取：`hub_maps`、`world_map_of`、`location_map`，地名和實地地圖一致。
  - `hub` 驗證、主城沒標 `hub` 時報錯。
  - 主城遭遇：抽陣容是 `WorldError`。
  - **在主城挑戰賽季 Boss 全滅**：10 級、1 HP、沒帶傭兵，確實打輸。之後有 `season_boss_failed`，人留在主城，前後的 `world_view` 都組得出來；`reinforce_lineup` 不會 `KeyError`。
  - **主城的缺席畫面**：含「某地開放了」，照常組得出來。

## 2. 主城物件的 `panel`／`stele_region`

- `FieldSpot` 加兩個欄位：
  - `panel`：`ObjectPanel` = `board`／`league`／`pavilion`／`skills`。
  - `stele_region`：ID 格式。
- 驗證：
  - 單一物件：兩個欄位只能填一個，填了的物件 `use` 必須是 `note`。
  - 單張地圖：營火點與事件點不能填；不是主城的地圖不能填。
  - 跨檔案：`stele_region` 必須是 `regions.yaml` 的區域（`_check_stele_regions`，含還沒有地點圖的三區）。
- 主城內容補上欄位：
  - `capital.yaml`：五塊橋頭石碑填 `stele_region`；封印台、裂界投影、擊殺石碑、守印人填 `board`，循環賽報名台填 `league`，整備亭填 `pavilion`。
  - `capital_mentor_hall.yaml`：書記、魔導書書架填 `skills`。
- API：
  - `FieldSituationObjectView` 帶 `panel`、`stele_region`。
  - `WorldMapView` 加 `hub`，主城為 `true`。
  - 已重新產生 `openapi.json` 和 `schema.d.ts`。
- 前端：
  - 拿掉 `CAPITAL_PANELS`、`capitalPanel`、`steleRegion`（`stele_` 前綴）。
  - 新增 `objectHud(obj)`，讀伺服器給的兩個欄位。
  - `WorldScreen.interactHud` 從 `view.field.situation_objects` 找到物件，交給 `objectHud`，不再判斷 `region === "capital"`。
  - `firstMapLayer` 改看 `map.hub`。
- **SPOTS 與 ISLAND_GEO 合成一份**：兩者語意相同（浮島位置與大小）。6F-ART1 之後 SPOTS 只剩「表裡沒有的區」的備用位置在用。
  - 合併後只留 `render/worldMapArt.ts` 的 `ISLAND_GEO`。
  - `islandGeo(region, index)`：表裡沒有的區照 `regions` 的順序沿外圈排，和原本 `fallbackSpot` 的換算等價。
  - `AtlasIsland` 的 `spot` 換成 `index`（主城為 -1）；`atlasModel` 的 `IslandSpot`、`CAPITAL_SPOT`、`SPOTS`、`fallbackSpot` 拿掉。
- 測試：
  - `tests/world/test_capital.py::test_capital_objects_carry_panel_and_stele`：API 的欄位與 `hub`。
  - `test_capital_hub.py::test_panel_and_stele_validation`。
  - `client/src/world/atlas.test.ts`：`objectHud`、`hub`、主城的 geo 就是 `ISLAND_GEO.capital`、外圈備用位置。

## 3. 這一趟固定陣容的重生世代

- `FieldVisit` 加 `generations: tuple[int, ...]`：開新的一趟時，照世界現在的狀態記下每隊（`spawns` 的索引）的重生世代。另有 `FieldVisit.generation(i)`，沒記到時回傳 `None`。
- `lineup_seed(…, generation=None)`：`_contact_model` 傳入這一趟的世代。地圖上看到的陣容和碰到時記下的 `lineup_seed` 都固定用進圖時的世代。別人打贏 personal 隊伍讓世代加一，要下一趟（換地點後重新進圖）才生效。
- 舊存檔的 `field_visit` 沒有 `generations`（或索引超出範圍）時，照世界現在的世代，也就是原本的做法。
- 存檔照 6B-2 的做法遞增：`CHAR_FORMAT` 升成 `trpg-char/6`，`/1`～`/5` 照讀（只多了選填欄位）。陣容種子的判法改了，所以 `WORLD_RULES_VERSION` 升成 2（6D-R1 的規則：舊日誌標成規則已變、不能重播）。`trpg-wlog` 的版號沒動。
- 測試（`tests/world/test_field_visit_generation.py`）：
  - 進圖時記下世代。
  - **兩個角色同圖、alice 打贏 personal 隊伍**：世界的世代加一，但 bob 這一趟看到的陣容不變；bob 走過去碰到時記的 `lineup_seed` 仍是進圖時的世代。bob 重新進圖後換成新的世代。
  - `trpg-char/5` 的舊存檔照讀。
- 其他測試的調整：
  - 測試裡寫死 `trpg-char/5` 的地方改成 `/6`。
  - `test_field_ctx_replay.py` 的凍結雜湊：比較前拿掉 6D-R2 才加的 `generations` 鍵（`DROPPED`）。陣容種子本來就遮掉了，其他行為沒變，雜湊照舊相同。

## 4. 測試與檢查

- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8 -x`：4255 通過、1 跳過（開發模式那一項，原本就跳過）。
- ruff check、ruff format --check、mypy src（511 檔）、lint-imports（13 contracts）：通過。
- `uv run trpg content check`：通過（實地地圖：雲嶺 18／18、灰燼荒原 18／18、主城 1／1）。
- swamp 種子 7 重播：通過（88 個動作、313 個事件）。
- 前端：`tsc --noEmit` 通過；vitest `src/world`、`src/render` 75 個檔案、877 項通過；`pnpm build` 通過。
- 沒有新增 `# noqa`、沒有新增相依。

## 5. 變更的檔案

- 內容：
  - `content/world/maps/capital.yaml`（新增）
  - `content/world/fields/capital/capital.yaml`
  - `content/world/fields/capital/interiors/capital_mentor_hall.yaml`
- 內容 schema 與載入：`src/trpg/content/world_map.py`、`fields.py`、`library.py`
- 世界：
  - `src/trpg/world/common.py`、`encounters.py`、`atlas.py`、`narration.py`
  - `field_enemies.py`：只動 `_next_visit`、`lineup_seed`、`_contact_model` 的世代相關處
  - `state.py`、`save.py`、`__init__.py`
- API 與伺服器：`src/trpg/api/world_field_schemas.py`、`world_field_things.py`、`world_schemas.py`、`world_presenter.py`、`absence_view.py`、`notes_schemas.py`、`world_field_people.py`、`world_field_view.py`、`src/trpg/server/announce.py`
- 前端：
  - `client/src/world/atlasModel.ts`、`atlasScene.ts`、`client/src/render/worldMapArt.ts`、`client/src/screens/WorldScreen.tsx`、`client/src/dev/mapGallery.tsx`
  - 測試資料：`atlas.test.ts`、`regionMapArt.test.ts`、`regionModel.test.ts`
  - `openapi.json`、`schema.d.ts`
- 測試：新增 `tests/world/test_capital_hub.py`、`tests/world/test_field_visit_generation.py`；修改 `tests/world/test_capital.py`、`test_field_ctx_replay.py`，以及上面提到寫死版號的測試。

## 待 PM 決定

**原型與解讀類**（照最保守的預設做了）：

1. **主城在城鎮限定的畫面上**：改用 `location_map` 之後，`world_field_people._is_town` 把主城也當城鎮，主城室外圖會顯示站在城裡的朋友影子。原本因為查不到主城的地點圖而不顯示。我認為主城本來就是城鎮，這是修正。如果主城不要顯示朋友影子，要另外排除。
2. **共享清空的隊伍在同一趟內重生**：陣容也照進圖時的世代。例如自己打贏一隊營地敵人、它在這一趟內又重生，看到的會是同一批。照規格寫的「下一趟才生效」一律套用，沒有區分隊伍種類。
3. **`WORLD_RULES_VERSION` 1 → 2、`CHAR_FORMAT` `/5` → `/6`**：如果 6E-1／6E-3 也升這兩個版號，合併時會衝突，保留較大的值再加一即可。
4. **沒有改的直接查詢**：`world/battlefield.py:235`、`world/field.py:456` 還是 `library.world_maps.get(...)`，查不到時回傳 `None`，不會 `KeyError`。這兩個檔正由 6E-1／6E-3 修改，照指示避開，之後可以順手改成 `location_map`。
5. **`reinforce_lineup` 遇到沒有遭遇表的地點**：改成不增援，原本會 `KeyError`。目前正式流程不會走到這裡，算防禦性處理。
6. **`panel`／`stele_region` 只准主城用**：其他地圖填了就是內容錯誤。以後別的城鎮要用，放寬 `FieldMapDef._panel_problems` 即可。
