# Phase 6D-ART2 完成報告：主城建築與街景（室外）＋6B-ART1 驗收補充三項

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6D-ART2 列、`docs/archive/art/Phase6剩餘美術移植需求.md` 第 2 節（主規格）、`docs/art/城鎮與室內圖庫.md` 第 1 節、樣張 `docs/art/town-tiles.png` 第 1、3 節（`sample/townTiles.js`）。
開發 PM 中途補了三項（依美術 PM 的 6B-ART1 驗收紀錄），也在這一段做完，見第 3 節。

**只換外觀，不改規則，沒有動任何地圖格子**。沿用 6B-ART1 的 `buildings` 與物件 `look`；沒有採用代決 #34。主城 3 間室內是 6B-ART1 做的，這段沒有碰。

## 1. 交付內容

### 1.1 資料格式（`src/trpg/content/fields.py`）

- `BUILDING_KINDS` 加主城的 4 種：`stone_hall`、`mentor_hall`、`tent`、`fountain`。
- `fountain` 可以蓋在水表面上（`WATER_BUILDINGS`）：範圍內每一格要是牆、門或水表面。其他種類照舊只能蓋在牆或門上。
- 物件 `look` 加 3 種：`crystal_lamp`（源晶燈）、`stele`（橋頭石碑）、`sky_bridge`（浮橋）。規則照原本的 `kind`。

### 1.2 API

- `FieldBuildingView.sign`（選填，`jar`／`anvil`／`scroll`／`null`）：照建築範圍內的門通往的室內設施決定。順序同前端的室內種類：導師＝書卷 ＞ 鐵匠或附魔＝鐵砧 ＞ 酒館＝酒罈。沒有門＝`null`。
- 這是補充第 2 項要的「照門通往的室內」；前端沒有室內圖的設施資料，所以由伺服器算。
- 已重新產生 `client/openapi.json`、`client/src/api/schema.d.ts`。
- 傳送陣的開放狀態**沒有新增伺服器欄位**：前端讀既有的 `atlas.regions`。

### 1.3 內容（`content/world/fields/capital/capital.yaml`）

只加 `buildings` 與 `look`，格子沒動。

| 項目 | 加的內容 |
|---|---|
| 技能導師殿 | `mentor_hall` [13,1] 5×4（門 [15,4]） |
| 酒館 | `stone_hall` [2,9] 4×4（東牆的門 [5,11]） |
| 鐵匠鋪 | `stone_hall` [25,10] 4×3（西牆的門 [25,11]） |
| 傭兵營 | `tent` [12,19] 2×2、`tent` [18,19] 2×2 |
| 許願池 | `fountain` [4,3] 2×2（水表面上） |
| 五座浮橋 | 10 格 `wooden_bridge` 加 `look: sky_bridge` |
| 橋頭石碑 | 5 根 `stone_pillar` 加 `look: stele`（紋章照同一格情境物件的 `stele_region`） |
| 源晶燈 | 廣場四角 [11,9] [20,9] [11,14] [20,14] 的 `stone_pillar` 加 `look: crystal_lamp` |

### 1.4 前端畫法

全部用程式繪製，沒有下載素材，畫法是確定性的。

| 檔案 | 內容 |
|---|---|
| `render/capitalArt.ts`（新） | 白石藍頂金邊建築、導師殿的發光晶尖塔、帆布帳篷、噴水池、傳送陣光圈與中央晶柱、五面區旗、源晶燈、石碑紋章、浮橋；`paintBuilding` 分派全部建築種類 |
| `render/townArt.ts` | 種類表、`roof`／`sign` 選填欄位、`roofRows`、`signOf`、`signFromView`；幾個畫圖小工具改成 export |
| `render/interiorArt.ts` | 家具外觀加 3 種（交給 capitalArt 畫）、`bridgeRails` |
| `render/sceneryModel.ts` | 側牆的門（`side`、`drawY`）、傳送陣（`PlazaScene`）；`roofCovers` 照屋頂列數 |
| `render/sceneryLayer.ts` | 建築改用 `paintBuilding`；傳送陣光圈一列切一條放進該排的裝飾層、晶柱與區旗放物件層；側牆門的入口光圈在門外側 |
| `render/terrainArt.ts` | `capital` 區只換石板：晶冠的石板加金色菱形嵌線（約 1/7 格） |
| `world/fieldScenery.ts` | 換算側牆的門、屋頂列數、招牌、浮橋方向與相連、石碑區域、傳送陣；`buildingDoorCells`、`openRegionsOf` |
| `world/fieldModel.ts`、`world/WorldField.tsx` | `fieldDrawModel` 多傳已開放的區；建築的門不畫門框 |

細節：

- **建築**：
  - 酒館、鐵匠鋪：照 `stoneHall()`，白石立面、金邊、藍瓦、金色屋脊，藍框招牌只畫圖示；
  - 導師殿：同上，屋頂中央一座發光的晶尖塔；
  - 帳篷：條紋帆布、門簾、繩與木樁、頂上一面小旗；底下鋪一塊踩平的地面蓋住牆格；
  - 噴水池：照 `fountain()`，屋頂不往上蓋。
- **側牆的門**：主城酒館與鐵匠鋪的門在東、西牆，不在最下一列。
  - 門板畫在同一欄的最下一列（建築正面）；
  - 入口光圈畫在門外側那一格，也就是玩家真正走進門的那一格；
  - 開關門動畫照真正的門格。
- **中央傳送陣**：只在 `region: capital` 的室外地圖，取第一顆傳送石。
  - 金色雙圈加五區光圈，由正北起順時針：晶冠、雲嶺、樞市、灰燼、霜潮；
  - 已開放的區畫該區顏色並發光，沒開放的是灰色；
  - 中央一根晶柱。
- **五面區旗**：立在光圈外圈（相對傳送石 (0,−2)、(3,−1)、(2,2)、(−2,2)、(−3,−1)），順序與顏色同光圈。只畫，不佔格。
- **源晶燈**：石座、白石柱、發光晶石。
- **橋頭石碑**：圓頂石碑加金邊，中央刻該區紋章（晶石、雲上的山、符文圈、火焰、雪花）。不寫字。
- **浮橋**：木板橋面，兩側繩欄（鄰格也是浮橋就不畫，兩格接成一座寬橋），往地圖邊那一端淡進雲裡（「斷在雲上」）。方向依物件在地圖的哪一邊。
- 封印廣場、技能工坊、整備亭照需求「先照現有物件畫」，沒有改。

## 2. 測試

- 後端：
  - `UV_NO_SYNC=1 uv run pytest -q tests/content -n 8`：2580 passed；
  - `tests/api -k field`：83 passed；`test_openapi_snapshot`：通過；
  - `uv run trpg content check`：通過（主城 1／1）；
  - `ruff check`、`ruff format --check`、`mypy`（改動的 2 檔）、`lint-imports`（13 kept）：通過。
- 後端新增的測試：
  - `tests/content/test_field_buildings.py`：
    - **主城的地圖格子雜湊不變**：拿掉 `buildings`、`look` 後是 `73a7cad0ebf4dfb6`，和加欄位前（31f1be3c）一樣；
    - 主城 6 棟建築、3 扇門都在建築範圍內、10 格浮橋、4 座源晶燈、5 座石碑都對得到 `stele_region`；
    - 噴水池可以蓋在水表面上；噴水池蓋在非水格、其他種類蓋在水上都會失敗。
  - `tests/api/test_world_field_buildings.py`：招牌照門通往的室內。霧渡鎮 jar／anvil／無／無；餘燼集 jar／anvil／無／無；主城 scroll／jar／anvil／無…。
- 前端：
  - `tsc --noEmit`、`vite build`：通過；
  - vitest `src/world` 加 `render/townArt`、`render/capitalArt`、`render/regionArt4`：31 檔 408 passed。
- 前端新增的測試：
  - `render/capitalArt.test.ts`：主城 5 種建築、傳送陣光圈與晶柱、五面區旗、源晶燈、五種石碑紋章、浮橋四方向的**畫法確定性**（記錄器比對指令序列）與不寫字。另外測：
    - 光圈顏色照開放狀態：全灰 5 圈；開 2 區時 2 圈有色、3 圈灰；
    - 導師殿多一次發光；
    - 招牌與屋頂列數進快取鍵；
    - 浮橋繩欄的方向換算；
    - 主城只換石板。
  - `world/capitalScenery.test.ts`：主城建築換算、側牆的門、傳送陣（排序、去重、室內與其他地圖沒有）、`openRegionsOf`、街景物件；補充三項見第 3 節。
  - 調整舊測試：
    - `townArt.test.ts`：建築改用 `paintBuilding`，10 種外觀、13 種家具；
    - `regionArt4.test.ts`：區域表多 `capital`。
- **實機看過一次**：
  - 自己開的伺服器在 8325 埠，存檔在暫存資料夾，用 build 版。結束後只關了自己的程序；
  - 主城：從導師殿出門、在廣場走動、看鐵匠鋪的側門。大世界圖上只有雲嶺開放，傳送陣也只有綠圈亮，兩邊一致；
  - 從大世界圖傳送到霧渡鎮，看渡婆那一帶；
  - 主控台沒有錯誤。
  - 瀏覽器分頁已經滿了，所以借用 6B-ART1 留下的 8321 分頁（tab-8）改連 8325，沒有關任何分頁。
  - 實機發現兩個問題，已修：
    - 光圈整張放在最上一排時，會被下面幾排的地形蓋住，所以改成一列切一條；
    - 帳篷兩側原本會露出牆格。
- 截圖：
  - `docs/art/6dart2_capital.jpg`（主城全景）
  - `docs/art/6dart2_plaza.jpg`（特寫：中央傳送陣、區旗、源晶燈）
  - `docs/art/6dart2_smithy_side_door.jpg`（特寫：鐵匠鋪的側門、招牌、沒有門框）
  - `docs/art/6dart2_mist_granny.jpg`（霧渡鎮渡婆那一帶，補充第 1 項）

## 3. 開發 PM 補充三項（6B-ART1 驗收）

1. **屋後站著東西時，屋頂不往上蓋**：
   - 範圍正北那一列站著 NPC、設施、情境物件或傳送石時，那一棟的 `roof` 是 0，屋頂收在自己的範圍內，該格的人不再被蓋住。路過的玩家不算，照舊畫虛線剪影。
   - 霧渡鎮渡婆的屋子、餘燼集南邊鐵娘後面那棟（[6,13]）都因此不往上蓋，地圖格子沒動。截圖 `6dart2_mist_granny.jpg` 裡渡婆完整可見。
   - 測試：NPC、設施、情境物件、傳送石各一種會觸發；範圍外與玩家不會觸發；別棟照舊。
2. **廢鐵屋、鍛爐屋照門通往的室內掛招牌**：
   - 酒館掛酒罈、鐵匠掛鐵砧，沒有門的不掛，用伺服器的 `sign`。
   - 結果：餘燼集酒館現在有酒罈招牌；爐叔鐵鋪照舊是鐵砧；兩間沒有門的棚屋沒有招牌。霧渡鎮的白牆屋舍照原本的種類表，外觀不變。
   - 測試：API 的 sign、前端換算、畫法不同。
3. **建築的門拿掉淡黃色門框**：
   - 畫成建築門板的門（最下一列與側牆的門）不再畫框；滑過的說明與點擊照舊（`hoverText`、`portalAt` 沒動）。
   - 不屬於建築的門保留框。
   - 測試：`fieldHighlights` 只剩非建築門的框，`hoverText` 照舊。

## 4. 檢查清單（需求第 2 節）

- [x] 建築和 `town-tiles.png` 第 3 節一致：白石藍頂金邊、導師殿晶尖塔、招牌只有圖示（截圖 `6dart2_capital.jpg`）。
- [x] 傳送陣的光圈顏色和開放狀態一致，五面區旗都在：測試，加上實機（只開雲嶺＝只有綠圈亮，`6dart2_plaza.jpg`）。
- [x] 浮橋、石碑、源晶燈、許願池都換好（全景截圖；許願池的水表面照舊，噴水池疊在上面）。
- [x] 規則不變：
  - 主城的內容雜湊不變，地形與物件位置、種類沒改，`tests/content` 全過；
  - 規則與引擎都沒動，所以沒有另外跑引擎重播（同 6B-ART1 的做法）。
- [x] 地面：主城的石板換成晶冠白石板加金色嵌線。

## 5. 待 PM 決定

以下都已照最保守的做法先做。

1. **側牆的門畫在建築正面**：主城酒館、鐵匠鋪的門在東、西牆。這次的建築是正面視角，看不到側牆，所以：
   - 門板畫在同一欄的最下一列；
   - 入口光圈畫在門外側（真正走進去的那一格）；
   - 因此門板和光圈差了一格的高度（截圖 `6dart2_smithy_side_door.jpg`）。
   - 要更準確的話，有兩個做法：畫側面的門，或把門移到最下一列（後者是規則格，要使用者同意）。
2. **金色嵌線的密度**：沿用晶冠的嵌線（約 1/7 格）。整片主城看起來偏密，要「偶有」可以降到 1/12 左右（一行常數）。
3. **傳送石的「◆」標示保留**：它疊在中央晶柱上。補充第 3 項只講門，所以沒拿掉；要的話可以只對主城傳送陣取消。
4. **浮橋的 `look: sky_bridge`**：需求表沒有列浮橋的資料寫法，這是新加的 look 值。
5. **區旗的位置**：需求只寫「外圈立五面區旗」，這裡排成光圈外的五角形。旗子只畫、不佔格，人可以站在旗子那格（會疊在一起）。
6. **招牌改由伺服器算**（`FieldBuildingView.sign`）：前端拿不到室內圖的設施。這是只畫的選填欄位。
7. **大世界圖沒有資料時**（沒有 `atlas`），傳送陣全部畫灰色。

## 6. 改動的檔案

- 後端：
  - `src/trpg/content/fields.py`
  - `src/trpg/api/world_field_schemas.py`
  - `src/trpg/api/world_field_view.py`
  - `client/openapi.json`、`client/src/api/schema.d.ts`（重新產生）
- 內容：`content/world/fields/capital/capital.yaml`
- 前端：
  - 新檔 `render/capitalArt.ts`；
  - 改動 `render/townArt.ts`、`interiorArt.ts`、`sceneryModel.ts`、`sceneryLayer.ts`、`terrainArt.ts`（一行表項）；
  - 改動 `world/fieldScenery.ts`、`fieldModel.ts`、`WorldField.tsx`。
- 測試：
  - 新檔 `render/capitalArt.test.ts`、`world/capitalScenery.test.ts`；
  - 改動 `render/townArt.test.ts`、`render/regionArt4.test.ts`、`tests/content/test_field_buildings.py`、`tests/api/test_world_field_buildings.py`。
- 沒有碰 6N-3、6N-9、6N-10 的檔案（skillClips、skillSequence、技能播放、狀態與地表動畫、NPC 小動作），也沒有改 BattleRenderer。沒有新增相依，沒有碰 `saves/`、`tmp_x`。
- `world/` 三個檔案與 `api/` 兩個檔案超出「只動 client/src/render」的範圍。原因：
  - 外觀換算本來就在 6B-ART1 的 `world/fieldScenery.ts`；
  - 傳送陣要讀大世界圖，要從 `WorldField` 傳進來；
  - 補充第 2、3 項要用到 `fieldModel` 與 API。
