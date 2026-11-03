# Phase 6F-ART1 報告：區域插畫與大世界圖（B 俯視彩繪）

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6F-ART1 列、`docs/art/雲嶺區域插畫.md` 第 4、5 節。

## 1. 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/regionMapArt.ts` | 共用層：`P()`（1280×860，左右 80、上下 70）、雪山／松樹／雲團、地點圖示（9 種＋秘境圓圈）、名字牌、等級牌、清空、任務、傳送石、自己、腳印、霧材質與挖洞、路、足跡、標題、指北針、圖例、外框；點擊區矩形 `spotHitBox`／`stoneHitBox`／`questHitBox` 與 `hitPercent` |
| `client/src/render/regionArtCloud.ts`、`regionArtAshen.ts` | 雲嶺、荒原地景與 `afterFog`（雪峰尖；火山口＋噴煙），照樣張 painted 分支逐段移植（scroll 分支沒移植） |
| `client/src/render/regionMapPainter.ts` | 地景登記表 `REGION_ART`、快取（LRU 4 張）、`paintBase`／`paintOverlay` |
| `client/src/render/worldMapArt.ts` | 大世界圖：天空（快取）、浮島（頂面、島緣、倒錐）、浮橋、鎖、字牌、傳送鈕、「你在〇〇」、圖例；`AtlasPainter` |
| `client/src/render/artRandom.ts` | 加 `seeded(seed)`（mulberry32，與樣張 `rng(seed)` 同序列）；原 `rng()` 改成呼叫它（輸出不變） |
| `client/src/world/MapStage.tsx` | 共用舞台：等比縮放置中、兩張 canvas（底層／上層各自看自己的鍵才重畫）、透明點擊區層、字型版本訂閱、`labelScale`、`fitStage` |
| `client/src/world/regionModel.ts` | 加 `regionScene()`（伺服器欄位 → 插畫場景）；`RegionEdge` 加 `a`、`b`、`silhouettes` |
| `client/src/world/atlasScene.ts` | 大世界插畫場景（狀態、條件、等級取自 `maps` 的 `level_zh`） |
| `client/src/world/RegionMap.tsx`、`AtlasMap.tsx` | 底圖換成 `MapStage`；DOM 節點改成透明點擊、滑過區（說明卡、傳送、點島進區域圖不變）；拿掉 6C-6 的灰點、雲團、連線 SVG、島 SVG 與 `art_url` 背景 |
| `client/src/styles/region-map.css`、`atlas.css` | 刪掉節點、連線、霧團、浮島 SVG、浮動動畫樣式；加 `.map-stage*`、`.map-hit`、`.map-hit-label` |
| `client/map-gallery.html`、`client/src/dev/mapGallery.tsx` | 開發用樣張頁（不進正式 build）：`?map=cloud_ridge｜ashen_waste｜atlas`，地點讀 `content/world/maps/*.yaml`，狀態照樣張假資料 |
| `client/src/render/regionMapArt.test.ts` | 新測試 26 項 |

沒有新增伺服器欄位、沒有新增相依，沒動 `fieldTiles.ts`、`client.ts`、`battle/`、`render` 的滑行動畫、`atlasModel.ts`（含 `CAPITAL_PANELS`）。

## 2. 畫法與快取

- **底層**：地景照 `baseKey(region, 像素寬, 像素高, 字型版本)` 快取在離屏 canvas，同一區同尺寸開兩次直接貼上。大世界的天空照尺寸快取。
- **上層**：`overlayKey`＝場景 JSON＋尺寸＋字牌倍數＋字型版本，變了才重畫。霧的整張材質（520 團雲＋陰影）也照（區域、尺寸）快取，狀態變時只複製材質、重新挖洞（去過 190／剪影 105、0.72／兩端去過的路上三點 120）。
- **點擊區**：和畫布用同一套 `P()`，以百分比定位在舞台上，所以縮放時一定對齊（實機在 700、1000、1360 寬下點傳送石、滑過地點、點島都對得上）。
- **確定性**：全部用 `seeded(固定種子)`；測試裡把 `Math.random` 換成會丟錯的版本，兩區地景、霧上地景、大世界圖各畫兩次，指令完全一樣。
- **字牌**：舞台寬小於 900px 時，地點的標記（圖示、名字牌、等級牌、勾、任務、傳送石）以地點為中心放大 `900/寬` 倍，點擊區跟著放大。

## 3. 測試

- `corepack pnpm exec vitest run src/world src/render/regionMapArt.test.ts src/render/regionArt.test.ts src/ui/floatCardRule.test.ts src/ui/legacyLayout.test.ts src/test src/dev`：**34 檔、403 項全過**。
- `tsc --noEmit` 通過；`pnpm run build` 通過（只有原本就有的 chunk 大小警告）。
- 新測試涵蓋：快取鍵（區域、尺寸、字型）、同區開兩次只畫一次、LRU 上限、狀態變只重畫上層（地景和霧材質都不重畫）、迷霧三段（霧裡的地點、路、任務、傳送石都不在場景；挖洞半徑）、路的實線／虛線／不畫、足跡選路規則與越接近越清楚、點擊區對齊 `P()`、`labelScale`／`fitStage`、大世界方位、三種狀態、傳送鈕與「你在〇〇」、SSR 畫面保留點擊區與 testid。
- 原本的 `atlas.test.ts`、`regionModel.test.ts` 不用改就通過。

截圖（headless Chrome 開 `map-gallery.html`，1340×980）：

- `docs/art/6f_art1_cloud_ridge.jpg`
- `docs/art/6f_art1_ashen_waste.jpg`
- `docs/art/6f_art1_atlas.jpg`

## 4. 第 5 節檢查清單

- [x] **兩區地景和樣張一致**：雲嶺的山、竹林、梯田、吊橋、霧河、冬湖、藥圃、源晶裂痕；荒原的火山、熔岩河、石橋、枯木林、焦油坑、冷卻井 4 口、灰泥沼、赤沙、廢墟要塞，和 `region-painted.png`、`region-ashen.png` 逐張對過（參數照搬，種子相同）。
- [x] **三段迷霧**：霧裡的地點、通往霧裡的路、霧裡的任務和傳送石都不畫，也沒有點擊區（測試＋SSR 檢查）；隱藏地點後端本來就不送；兩端都是剪影的路不畫。地景避開地點用的是內容檔的全部 pos（含隱藏），所以發現隱藏地點不會改變地景，地景空隙也不會洩漏它（見待決 1）。
- [x] **標記**：去過、清空、剪影「？？？」＋等級（渡口不寫）、傳送石解鎖／沒解鎖（灰色加鎖）、任務「！」、自己（藍圈＋定位釘）、足跡都畫得出來，位置和地點一致（截圖可見）。
- [x] **傳送石與說明卡**：點傳送石照 6C-6 的規則（`go` 才送；`here`／`locked`／`view` 只看）；滑過地點有原本的說明卡（實機確認）。
- [x] **大世界圖**：方位（西雲嶺、南荒原、北晶冠、東樞市、東南霜潮、主城中央）、三種狀態、浮橋（開放木板／未開放虛線）、傳送鈕、「你在〇〇」都正確；點已開放的島進該區區域圖（實機確認：點荒原的島開出荒原區域圖）。
- [x] **確定性**：同一區開兩次地景完全一樣（測試比對全部繪圖指令；不用 `Math.random`）。

## 5. 待 PM 決定（都已照最保守的做法做完）

1. **地景避開地點的座標寫死在地景檔**（從 `content/world/maps/*.yaml` 抄的全部 pos，含隱藏地點）。理由：伺服器不送隱藏地點，用伺服器資料的話，發現隱藏地點時地景會變、且地景的空隙會洩漏隱藏地點。代價：之後改 yaml 的 pos，要同步改這兩支檔（地點標記本身照伺服器 pos，不受影響）。
2. **大世界浮島位置用樣張的畫布座標**（`worldMapArt.ts` 的 `ISLAND_GEO`）。`atlasModel.ts` 的 `SPOTS` 因為 6D-R2 要改同一檔，我沒動；現在只在表裡沒有的新區當備援位置用。之後可以把 `SPOTS` 改成由 `ISLAND_GEO` 推出、只留一份。
3. **字牌放大是整組標記一起放大**（不只字牌），排版才不會散開；標題、圖例、指北針照畫布縮放。
4. **DOM 圖例列拿掉**（圖例畫在畫布右下角），「M 大世界圖／Esc 關閉」移到標題列。
5. **足跡沒有看得到的路可以畫時**（例如連到的地點都在霧裡），腳印畫在地點左下旁邊。
6. **一個地點有多顆傳送石時**畫布只畫一顆（有任一顆解鎖就畫亮的），點擊區往下疊放；現在的內容每個地點最多一顆。
7. **大世界標題牌的小字**改成看 `can_teleport`：「可以點城鎮直接傳送」／「在城鎮或傳送石上才能傳送」（樣張寫死前者）。
8. 面板最大寬 1100 改成 1320，讓 1280 的畫布可以原尺寸放進去。
9. 浮島的上下漂浮動畫（6D-5 的 CSS）因為改畫在畫布上而沒了；要的話之後可以加在上層。
10. 截圖用開發樣張頁（真實 content 的地點和連線＋樣張的假狀態），不是真實存檔；headless 截圖時舞台四周留了些邊，實機瀏覽器會填滿面板。
