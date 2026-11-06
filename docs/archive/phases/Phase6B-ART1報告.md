# Phase 6B-ART1 完成報告：霧渡鎮、餘燼集的建築與門＋7 間室內

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6B-ART1 列、`docs/archive/art/Phase6剩餘美術移植需求.md` 第 1 節（主規格）。
開發 PM 補充：主城 3 間室內（導師殿、酒館、鐵匠鋪）也在這一段做，6D-ART2 只做主城室外。

**只換外觀，不改規則，也沒有動任何地圖格子**。新增的兩個欄位都是選填、只畫；沒有採用代決 #34 的「載入時展開成牆」。

## 1. 交付內容

### 1.1 資料格式（`src/trpg/content/fields.py`）

- `FieldMapDef.buildings`：`{kind, at, size}`，左上角加寬高（格）。單檔驗證：
  - 範圍內每一格都要是 `wall` 地形，或是門的格子；
  - 不可蓋到出口、不可超出地圖、不可和別棟重疊；
  - `size` 至少 1×1。
- 認得的 `kind`：`tavern`、`smithy`、`hall`、`house`、`scrap_house`、`forge_house`（`BUILDING_KINDS`）。
  - 不認得的 `kind` 照樣載入，前端畫成 `house`；`content check` 列為警告。
- 物件加選填欄位 `look`：新類別 `FieldObjectPlacement(MapObjectPlacement)`，只用在實地地圖，戰鬥地圖的 schema 沒有改。
  - 只收 9 種：`barrel`、`table`、`bar`、`counter`、`anvil`、`forge`、`candle`、`crystal_statue`、`shelf`。
  - 規則照原本的 `kind`。

### 1.2 API

- `FieldView.buildings`（`FieldBuildingView`：kind、x、y、width、height），以及 `FieldObjectView.look`。
- 已重新產生 `client/openapi.json` 與 `client/src/api/schema.d.ts`。

### 1.3 前端畫法

全部用程式繪製，沒有下載素材，畫法是確定性的。

| 檔案 | 內容 |
|---|---|
| `render/townArt.ts` | 建築：白牆黛瓦（照 `explore.js` 的 house），廢鐵屋與鍛爐屋（照 `ashenTiles.js` 的 scrapHouse）。另有門框、門板、入口光圈、招牌圖示 |
| `render/interiorArt.ts` | 室內：地板（木板、石板、紅地毯）、外圈牆邊、出口格、後牆（1.6 格）加擺設、9 種家具外觀加附魔台 |
| `render/sceneryModel.ts` | 純資料型別、`interiorPieces`、`roofCovers` |
| `world/fieldScenery.ts` | 從 `FieldView` 算出建築、門、室內、家具（純函式） |
| `render/sceneryLayer.ts` | 把上面這些放進 BattleRenderer 的逐排圖層；門板動畫 |

**建築**

- 立面畫在範圍內，屋頂往上多蓋 1 格。
- 建築放在範圍最下一列的物件層：
  - 北邊各排的人先畫，所以會被屋頂蓋住；
  - 站在門口或屋前的人畫在建築上面；
  - 被屋頂蓋住的人另外畫虛線剪影，做法和被高格擋住時一樣；
  - 頭頂圖示是 DOM，不會被蓋住。
- 外觀細節：
  - 酒館：朱紅邊、窗戶有燈光、掛燈籠，招牌是酒罈；
  - 鐵鋪：招牌是鐵砧，煙囪冒煙；
  - 導師堂：招牌是書卷；
  - 民宅：沒有招牌；
  - 廢鐵屋：布簾門；
  - 鍛爐屋：煙囪有火光，招牌是鐵砧。
- 招牌只畫圖示，不寫字。

**門**

- 只有建築最下一列的門格，才畫成木門或布簾門（門框、門洞、門板）。門前一格畫入口光圈。
- 隱藏門揭露前，伺服器本來就不給，所以不畫；那一格照舊是建築的牆面。
- 沒有門格的建築（導師堂、渡婆的屋子），正中央畫一扇關著的裝飾門，不畫入口光圈。

**門打開 0.2 秒**

- `doorClips.ts` 加了 `DOOR_OPEN_MS = 200` 和 `doorOpenness(open|close, u)`。
- 進門：`leaveMap` 讓門板和 6M-4 的離開片段同時開始轉開。門軸在左緣，用水平縮放表現往內轉開。
- 出門：抵達時門是開著的，`arriveMap` 讓門板和抵達片段同時關回去。
- 0.2 秒比淡出（80＋220 毫秒）短，換地圖的總長不變，仍是 520 毫秒。

**室內**

- 室內的種類照設施決定：導師 ＞ 鐵匠或附魔 ＞ 酒館。配色照區域：荒原用鐵灰牆、焦木地板。
- 外框：
  - 最上一列是後牆，1.6 格高，放在第 2 排的裝飾層；
  - 左、右、下方的牆格畫成暗處，靠房間那一邊加一道牆邊；
  - 下方的出口格畫門墊和入口光圈。
- 後牆擺設（只畫、不佔格），會避開緊貼後牆那一列的物件：
  - 酒館：酒架、壁爐（火光）；
  - 鐵匠鋪：兩座鍛爐、武器架；
  - 導師殿：晶石像、書架。
- 地板：酒館、鐵匠鋪是木板；導師殿是石板，中央鋪紅地毯（4 格寬）。
- 附魔台：`enchanter` 設施那一格的物件畫成發光符文繞圈的台子。那一格沒有物件時，用正北一格的物件（主城鐵匠鋪就是這種情形）。
- 室內不畫區域的裝飾薄霧。這層霧本來就是純裝飾，雲嶺室內原本整片飄霧。

### 1.4 內容：每張圖加了什麼

只加 `buildings` 與 `look` 兩個欄位，沒有移動任何格子。

| 地圖 | 加的內容 |
|---|---|
| 霧渡鎮 | `tavern` [1,2] 6×4（門 [3,5]）、`smithy` [16,2] 6×4（門 [18,5]）、`hall` [1,10] 3×2、`house` [10,14] 4×3（渡婆的屋子） |
| 餘燼集 | `scrap_house` [1,2] 6×4（酒館，門 [3,5]）、`forge_house` [17,2] 6×4（爐叔鐵鋪，門 [19,5]）、`scrap_house` [6,13] 3×3、`scrap_house` [16,12] 5×3 |
| 霧渡鎮酒館 | 櫃檯 [2..4,3] `bar`、桌子 [6,4][7,4] `table` |
| 石記鐵鋪 | 鐵砧 [4,2] `anvil`、[1,5] `shelf`；附魔台 [7,2] 自動 |
| 餘燼集酒館 | 櫃檯 [5..7,2] `bar`、老兵的桌子 [2,4] `table`、酒桶 [7,5] `barrel` |
| 爐叔鐵鋪 | 鐵砧 [3,2] `anvil`、淬火桶 [8,5] `barrel`；附魔台 [7,2] 自動；廢鐵料堆照原本的 rubble 畫 |
| 樞島酒館 | 櫃檯 [5..7,2] `bar`、桌子 [2,3][2,5] `table`、酒桶 [8,5] `barrel` |
| 樞島鐵匠鋪 | 鐵砧 [3,2] `anvil`、淬火桶 [8,5] `barrel`；附魔台 [7,2] 自動（設施站位在 [7,3]） |
| 技能導師殿 | 魔導書書架 [1..3,1] `shelf`、講壇 [6,1] `counter`、源晶燈 [1,5][8,5] `candle` |

## 2. 測試

- 後端（`UV_NO_SYNC=1 uv run pytest -q tests/content tests/api -n 8`）：3283 passed、1 skipped。新增的測試：
  - `tests/content/test_field_buildings.py`（26 項）：
    - 欄位驗證：牆或門可以；非牆、超出範圍、0 寬、蓋到出口、重疊都會失敗；`look` 只收認得的值；不認得的 kind 是警告；
    - **地圖格子完全不變**：9 張圖拿掉 `buildings`、`look` 後的內容雜湊，和加欄位之前（e8c6735b）一樣。雜湊涵蓋地形、高度、物件位置與種類、出口、門、NPC、設施等全部欄位；
    - 內容的棟數、7 間室內都有 `look`、`field_map_report` 沒有錯誤。
  - `tests/api/test_world_field_buildings.py`：畫面帶出建築與 `look`。
- `ruff check`、`ruff format --check`、`mypy src`（512 檔）、`lint-imports`（13 kept）、`uv run trpg content check` 都通過。
- 前端：`tsc --noEmit` 和 `vite build` 通過；vitest `src/world` 加 `render/townArt.test.ts` 共 362 passed。新增的測試：
  - `world/fieldScenery.test.ts`：建築與門的換算、不認得退回 house、隱藏門不畫、布簾門、屋頂遮擋判定、窗戶位置、室內種類與配色、後牆擺設避開物件、家具相連、附魔台、外框各格、紅地毯、門動畫時間軸；
  - `render/townArt.test.ts`：6 種建築、門、地板、牆、後牆、10 種家具的**畫法確定性**（用記錄器比對兩次繪圖的指令序列），以及不寫字、種類之間畫法不同；
  - `world/mapTransit.test.ts` 加一項：進門時門板和離開片段同時從 0 毫秒開始開門；出門時關門；進到室內不播門。
- 實機看過一次：自己開的伺服器在 8321 埠，存檔放在暫存資料夾，用 build 版，沒有開 vite。
  - 霧渡鎮：進酒館、出門。
  - 餘燼集：走進爐叔鐵鋪。為了到這兩張圖，改了暫存存檔的位置。
  - 主城導師殿。
  - 主控台除了重開伺服器時的連線錯誤之外，沒有其他錯誤。
- 截圖：
  - `docs/art/6bart1_mist_ferry.jpg`（霧渡鎮）
  - `docs/art/6bart1_ember_market.jpg`（餘燼集）
  - `docs/art/6bart1_mist_tavern.jpg`（霧渡鎮酒館）
  - `docs/art/6bart1_ember_smithy.jpg`（爐叔鐵鋪）
  - `docs/art/6bart1_capital_mentor_hall.jpg`（導師殿）

## 3. 檢查清單（需求 1.5）

- [x] 霧渡鎮 4 棟（酒館、鐵鋪、導師堂、渡婆的屋子）、餘燼集 4 棟（廢鐵屋酒館、鍛爐屋、兩間廢鐵棚屋）的外觀照樣張；招牌只有圖示。
- [x] 建築範圍內都是牆或門（資料測試）。走路、視線、戰鬥規則和以前一樣：
  - 內容的規則雜湊不變，地形與物件沒有改；
  - `tests/content`、`tests/api` 全過。
  - 這一段沒有另外跑引擎重播，因為規則與引擎都沒動。
- [x] 屋頂遮住北邊的人，被遮住的人有虛線剪影；頭頂圖示不被遮（DOM）。截圖裡渡婆、鐵娘可以看到。
- [x] 進門時 0.2 秒開門，出門時關門（時間軸測試；實機進出過酒館）。隱藏門揭露前不出現。
- [x] 7 間室內都有後牆、擺設、地板、入口光圈；家具照 `look` 畫；附魔台發光：
  - [x] 霧渡鎮酒館（酒架、壁爐、吧檯、圓桌；截圖）
  - [x] 石記鐵鋪（兩座鍛爐、武器架、鐵砧、貨架、附魔台）
  - [x] 餘燼集酒館（荒原配色；酒架、壁爐、吧檯、桌子、酒桶）
  - [x] 爐叔鐵鋪（荒原配色；兩座鍛爐、武器架、鐵砧、附魔台、淬火桶；截圖）
  - [x] 樞島酒館（酒架、壁爐、吧檯、兩張桌子、酒桶）
  - [x] 樞島鐵匠鋪（兩座鍛爐、武器架、鐵砧、附魔台、淬火桶）
  - [x] 技能導師殿（石板、紅地毯、晶石像、書架、講壇、兩座燭台；截圖）
- [x] HUD 不擋住室內的 NPC 和櫃檯。室內畫在畫面中央，左右留白；截圖的三間都可以看到。

## 4. 待 PM 決定

以下都已照最保守的做法先做。

1. **渡婆站在自己屋子的北邊**（[11,13]，屋子是 [10,14] 起）。照「屋頂往上多蓋 1 格」，她會被屋頂蓋住，現在只看得到剪影和頭頂圖示。
   - 要改的話，有兩個做法：把渡婆移到屋子南邊（這是規則格，要使用者同意），或把這棟屋子畫成朝北。
   - 霧渡鎮的格子沒有動。
2. **餘燼集的酒館沒有招牌**：需求表裡 `scrap_house` 沒有招牌，所以照表做。要的話可以讓 `scrap_house` 依門通往的室內設施掛招牌。
3. **`look` 和 `kind` 的對應沒有強制**：需求表的「對應的 kind」只當參考。現有內容的櫃檯、鐵砧都是 `crate`，所以 schema 只檢查 `look` 是不是認得的值。
4. **建築正面的門仍然保留原本的「門」標示**（淡黃框）：滑鼠提示也靠它，所以沒拿掉。要的話可以只對建築的門取消。
5. **附魔台的位置**：主城鐵匠鋪的 `enchanter` 設施是站位 [7,3]，台子是正北的 [7,2]。規則是：設施那一格沒有物件時，取正北一格的物件。
6. **後牆擺設放不下就不畫**：主城導師殿的後牆被書架物件和講壇佔掉，第二座書架放不下，所以只畫晶石像和一座書架。
7. 室內不畫區域裝飾薄霧（只影響外觀）。

## 5. 改動的檔案

- 後端：
  - `src/trpg/content/fields.py`
  - `src/trpg/api/world_field_schemas.py`
  - `src/trpg/api/world_field_view.py`
  - `client/openapi.json`、`client/src/api/schema.d.ts`（重新產生）
- 內容：
  - `content/world/fields/cloud_ridge/mist_ferry.yaml`
  - `content/world/fields/ashen_waste/ember_market.yaml`
  - 7 張室內圖（`interiors/*.yaml`）
- 前端新檔：
  - `render/townArt.ts`、`render/interiorArt.ts`、`render/sceneryModel.ts`、`render/sceneryLayer.ts`
  - `world/fieldScenery.ts`
- 前端只加的改動：
  - `render/BattleRenderer.ts`：加入外觀層、`playDoor`、屋頂剪影、室內不畫霧；
  - `render/doorClips.ts`：門的時間軸；
  - `battle/drawModel.ts`：選填欄位 `scenery`；
  - `world/fieldModel.ts`：帶上 `scenery`；
  - `world/mapTransit.ts`、`world/WorldField.tsx`：開關門。
- 測試：上面列的新測試檔；另外三個 field 測試的 fixture 補了 `buildings: []`。
- 沒有碰 6N-1 的檔案（`inkPose`、`motionClips`、`unitSprite`、`battle` 技能播放）、6P-1 與 6P-2 的檔案，也沒有新增相依。
