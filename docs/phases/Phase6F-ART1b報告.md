# Phase 6F-ART1b 報告：大世界圖第 2 版＋浮島漂浮＋地景座標資料測試

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6F-ART1b 列（含併入的 6F-ART1 驗收 `docs/archive/art/6F-ART1檢查.md`）、`docs/art/雲嶺區域插畫.md` 第 3 節最後、第 4、5 節。只動 `client/`（另加這份報告與截圖）。

## 1. 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/worldMapArt.ts` | 改寫成第 2 版共用層：浮島位置 `ISLAND_GEO`（換成第 2 版樣張座標）、版面與點擊區、有明暗的壓扁雲（`cloudPuff`／`cloudBank`）、天空（漸層、左上太陽光暈與光束、碎界裂痕、遠方雲層）、長草的小浮石、下方雲層、最前排雲、島下雲層投影、浮橋（開放＝木板吊橋加繩索欄柱；未開放＝一串光點）、金框鎖頭徽章、深藍底金色雙框襯線字牌、帶小晶石的傳送鈕、「你在〇〇」、標題、圖例、外框（暗角＋四角金飾） |
| `client/src/render/worldIslandArt.ts`（新） | 浮島本體：四色岩層倒錐（右側壓暗、裂縫、雲嶺與主城垂根）、島緣厚度（左亮右暗）、頂面內緣陰影與左上高光；雲嶺（河、梯田、竹林、松林、小鎮、雪山、山腰雲）、荒原（發光裂縫、赤沙、熔岩河、枯木、岩山、火山）、主城（花圃、石板路、廣場、房屋、城牆、晶塔）；雲嶺瀑布、荒原熔岩瀑布；未開放的島照地景畫在暫存畫布，再去色（grayscale 0.85）貼回、罩薄霧纏雲、加徽章 |
| `client/src/render/worldMapPainter.ts`（新） | `AtlasPainter`（從 worldMapArt 搬過來）：快取、組合、漂浮 |
| `client/src/world/frameLoop.ts`（新） | 逐格迴圈 `startFrameLoop`（停止時取消 requestAnimationFrame）、`shouldAnimate`、`prefersReducedMotion`／訂閱 |
| `client/src/world/MapStage.tsx` | `StagePaint` 加 `animated`；`paintOverlay` 多一個 `t`（靜態＝null）；動畫時用逐格迴圈，元件卸載（面板關掉）、減少動態、尺寸變都會停 |
| `client/src/world/AtlasMap.tsx` | 底層鍵改成 `atlasBaseKey`（尺寸＋各島狀態），開動畫 |
| `client/src/render/regionArtCloud.ts`、`regionArtAshen.ts` | 只把 `POS` 改成 export（給資料測試） |
| 測試 | 新 `render/worldMapArt.test.ts`（14 項）、`render/regionArtPos.test.ts`（4 項）；`regionMapArt.test.ts` 刪掉第 1 版的 3 項大世界畫法測試（搬到新檔重寫），版面、SSR 測試留著 |

區域圖兩張沒動。

## 2. 快取與漂浮

- **底層（不動）**：天空整組（天空、小浮石、下方雲層）照尺寸快取；上面畫島下投影和未開放航線光點，鍵＝尺寸＋各島位置與狀態。
- **上層每一格只貼圖**：浮島本體（每島一張離屏圖，範圍 `bodyBounds`）→ 前景一張（開放的浮橋＋最前排雲）→ 每島標記一張（字牌、傳送鈕／你在〇〇、自己的藍圈定位釘，範圍 `marksBounds`）→ 標題圖例外框一張。每格只有 `clearRect` 和 `drawImage`（測試鎖住）。
- **漂浮**：`floatOffset(region, t) = 3·sin(2πt/週期 + 相位)`；週期 5000～6000 ms、相位都由區域 ID 的 FNV-1a 雜湊決定（確定性、不用內建 hash）。島本體和它的標記用同一個位移；天空、雲、浮橋不動；DOM 點擊區不動。
- **重做時機**：本體只看（區域、開放與否、位置、尺寸）；`can_teleport` 變只重畫標記和標題。快取上限 40 張（LRU）。
- **不跑的情況**：`prefers-reduced-motion: reduce`（畫一次靜態，位移 0）、面板關著（AtlasMap 卸載 → 取消 rAF）、畫布沒有尺寸。

## 3. 測試

- `vitest run src/world src/render/regionMapArt.test.ts src/render/regionArt* src/render/worldMapArt.test.ts src/test src/ui/floatCardRule.test.ts src/ui/legacyLayout.test.ts`：**35 檔、447 項全過**。
- `tsc --noEmit` 通過；`pnpm run build` 通過（只有原本的 chunk 大小警告）。
- 新測試：第 2 版確定性（`Math.random` 換成丟錯，兩次畫出的指令連同每張離屏圖都一樣）；光影、瀑布、熔岩瀑布、金框、襯線字、去色、每座未開放島一個徽章；光點航線數量；點擊區版面與字牌放大；離屏圖範圍包得住所畫的全部路徑點（防裁切）；振幅 ≤3 且到得了 ~3、週期 5～6 秒、相位錯開；逐格只平移不重畫（沒有新離屏圖、繪圖計數不變、x 不變、y 差＝位移差、標記和本體一起動）；只重畫有變的部分；天空快取；點擊區沒有動畫；逐格迴圈停止後不再要下一格；減少動態／沒尺寸時不跑；讀 matchMedia。
- 資料測試：用 `test/sourceScan` 的 `listFiles`／`readFile`（node fs）讀 `content/world/maps/*.yaml`，雲嶺、荒原地景檔的 `POS` 要和 yaml 全部地點（含隱藏）一模一樣；另檢查 `REGION_ART` 每個地景都登記了座標（之後新增地景檔忘了登記也會失敗）。
- 實機（headless Chrome 開 `map-gallery.html?map=atlas`）：不同時間點兩張截圖不同（有在漂浮）；加 `--force-prefers-reduced-motion` 時兩張完全一樣。

截圖：`docs/art/6f_art1b_atlas.jpg`（1340×980，取代 `6f_art1_atlas.jpg` 的驗收用途；舊檔沒刪）。

## 4. 待 PM 決定（都已照最保守做法做完）

1. **浮島位置改用第 2 版樣張座標**（主城 650,350；雲嶺 260,360；荒原 610,600 等，大小也照第 2 版）。
2. **標題小字仍看 `can_teleport`**（6F-ART1 已同意的做法），沒照樣張寫死「在城鎮裡：點城鎮直接傳送」。
3. **字牌第二行**：已開放寫等級（`level_zh`），沒有等級（主城）寫城鎮名；未開放寫條件。和樣張一致。
4. **字牌放大改成整組以字牌上緣為中心放大**（第 1 版是每個牌各自放大，放大時會疊在一起）；傳送鈕點擊區跟著換算。
5. **未開放但有地景畫法的區**（例如雲嶺若被鎖）：照地景畫再去色；樣張只有晶冠、樞市、霜潮三種，其他沒畫法的區只鋪底色。
6. **岩層多邊形的下緣從 `ry*4` 收到 `ry*2.3`**：反正被倒錐裁掉，畫面不變，離屏圖才不用開那麼大。
7. **記憶體**：每格不重畫的代價是多 2 張整張大小的離屏圖（前景、外框），加上每島 2 張裁切圖；DPR 2 時整張約 17 MB 一張。如果之後在低階裝置吃緊，可以把外框改成第三張 DOM 畫布。
8. **未開放島的去色**用 `ctx.filter`；不支援 filter 的瀏覽器（舊 Safari）會變成彩色但仍有霧和徽章。
9. 截圖仍是開發樣張頁（真實 content 位置＋樣張假狀態），不是實際存檔；舞台四周的邊和第 1 版一樣。
