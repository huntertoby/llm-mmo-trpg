# Phase 5A-ART6 完成報告：四區換皮①（灰燼荒原＋晶冠城邦）

規格：`docs/phases/Phase5計畫.md` 第 1 節 5A-ART6 列、第 43.0／43.1 節；主規格 `docs/art/四區移植需求.md` 第 1～3、7 節；畫法移植自 `docs/art/sample/regions4.js`。**只動了 `client/` 與 `docs/`，`src/`、`content/` 沒有改。**

## 交付

| 項目 | 內容 | 檔案 |
|---|---|---|
| 灰燼地形 7 種 | 焦土裂地（部分格子有細熔岩光裂縫：先畫 3 寬黑縫，再疊 1.4 寬、模糊 5 的橘光）、枯黃草、灰燼地、焦黑岩壁（岩縫＋偶爾的餘燼點，有立面時多畫 12px 深色立面）、黑色裂谷（近黑漸層；底部紅光透明度 0.28，只畫在格子下半；四邊崖線照 `lip`）、岩漿（整格亮橘＋2～3 片黑色結殼）、灰水坑（暗灰水＋灰膜，邊緣是焦土） | `client/src/render/ashenTerrain.ts` |
| 灰燼物件 9 種 | 破木箱（鐵包角、一角破洞）、殘牆（`drawLowWall`＋灰燼 `LowWallPalette`，崩缺畫在壓頂石內，不比矮牆頂高）、斷柱（畫到格頂）、鏽鐵油桶（共用危險記號）、焦黑倒木、枯草堆、焦木渡橋（橫直兩向）、枯樹（畫到格頂）、灰水浮板（依耐久級距 0／1／2 變化，最後缺一塊板） | `client/src/render/ashenObjects.ts` |
| 晶冠點綴 | `stone`＝預設石板＋約 1/7 格金色菱形嵌線（`#e8bb48` 1.5 寬）與晶光點；`wall`＝白石城牆（米白錯縫磚，有立面時正面＋金邊）；`chasm`＝預設深淵＋4 個晶光碎點；`stone_pillar`＝晶柱（模糊 10、透明度 0.5 的外光，金色底座）。其他 ID 不在表內，退回預設 | `client/src/render/crystalTerrain.ts`、`crystalObjects.ts` |
| 接表 | `REGION_TERRAIN_DRAW`／`REGION_OBJECT_DRAW` 各加 `ashen_waste`、`crystal_crown`。晶冠的石板與深淵要在預設畫法上疊點綴，為了不循環匯入，由 `terrainArt` 把預設畫法傳進 `crystalTerrain({ stone, chasm })` | `terrainArt.ts`、`objectArt.ts` |
| 共用小工具 | `hazardMark`（四區共用的黃色三角危險記號）、`glowLine`、`dot` | `client/src/render/artDraw.ts` |
| 測試 | `regionArt4.test.ts`（18 項）：預設畫法輸出雜湊鎖住（region 空字串）、表只有三區；灰燼 7 地形／9 物件都換、技能物件與表面不換、未知 ID 退回預設、牆立面、裂谷紅光 ≤ 0.3 且在下半、岩漿 2～3 片結殼、裂縫光參數與比例（20×20 格 ≤ 38%）、危險記號、橋橫直、浮板依耐久變化；晶冠表只有 4 個 ID、其他 ID（含未知）與預設完全相同、嵌線約 1/7 且非嵌線格與預設完全相同、城牆金邊只在有立面時、深淵 4 個晶點、晶柱外光 | `client/src/render/regionArt4.test.ts` |
| 區域畫廊 | 新增 5 個場景：灰燼 7 地形＋9 物件（裂谷與岩漿並排）、灰燼岩漿渡橋、灰燼熔心坑（冷卻井是水表面）、晶冠 7 地形＋9 物件、同場景沒標區域（對照） | `client/src/dev/regionGallery.ts` |

## 檢查

| 項目 | 結果 |
|---|---|
| vitest `src/render`、`src/dev` | 37 檔、395 項全過（含新的 `regionArt4.test.ts`、既有的 `regionArt.test.ts`） |
| `tsc --noEmit` | 通過 |
| `pnpm build` | 通過（只有原本就有的 chunk 大小警告） |
| 前端快照 | 沒有快照變動 |
| ruff／mypy | 沒動 Python，不用跑 |

## 截圖

實戰（自己的 worktree 伺服器，埠 8291；內容與存檔都用 scratchpad 的副本，repo 的 `content/`、`saves/` 沒動；驗完已停伺服器、關分頁、還原視窗）：

| 檔案 | 內容 |
|---|---|
| `docs/art/art6_open_plain.jpg` | 焦土外圍（`open_plain`）：枯黃草、焦黑倒木、破木箱 |
| `docs/art/art6_dark_forest.jpg` | 枯木林（`dark_forest`）：枯樹、枯草堆、焦黑岩壁、倒木 |
| `docs/art/art6_lava_crossing.jpg` | 岩漿渡橋（`lava_crossing`）：岩漿＋焦木渡橋、焦土裂地、斷柱、殘牆、破木箱 |
| `docs/art/art6_molten_heart_pit.jpg` | 熔心坑（`molten_heart_pit`）：四格冷卻井維持藍色的水 |

畫廊（vite 開發伺服器，埠 5291，驗完已停；主控台沒有錯誤）：

| 檔案 | 內容 |
|---|---|
| `docs/art/art6_gallery_ashen.jpg` | 灰燼四個場景縮圖（7 地形＋9 物件、岩漿渡橋、熔心坑） |
| `docs/art/art6_gallery_ashen_zoom.jpg` | 灰燼 7 地形＋9 物件場景放大：黑色裂谷與亮橘岩漿並排一眼分得開 |
| `docs/art/art6_gallery_crystal.jpg` | 晶冠 7 地形＋9 物件，下方接著沒標區域的對照場景 |

**實戰的做法說明**：大世界要練到 5 級、走到灰燼荒原，熔心坑還要世界事件旗標，這段沒有開發捷徑能直接傳送。所以我用「戰鬥原型」頁的練習戰，在 scratchpad 的內容副本裡把四張地圖的 `region` 改成 `ashen_waste`（`dark_forest` 原本是 `cloud_ridge`），效果和大世界 `reskin()` 換區一樣（灰燼的 `look` 是空的）。熔心坑是 Boss 地圖，練習戰的地圖清單不列，副本裡另外把它的 `archetype` 改成 `open_plain` 才選得到；地形、物件、表面都是原檔。

## 待 PM 決定

1. **裂縫光的比例**：需求第 2 節寫「約 45% 的格子有裂縫光」，規格 43.0 第 3 條寫「同一張圖最多約 1/3 的格子有」。我照比較保守的 1/3（`ASH_GLOW_RATE`），岩壁餘燼點、倒木與枯樹的餘燼點也用同一個比例。實戰截圖看起來焦土上的裂縫還是不少；想更少或照 45% 只要改這個常數。
2. **晶柱外光的強度**：「比頭目外光淡」沒有數值。我用模糊 10、外光色透明度 0.5（`CRYSTAL_PILLAR_GLOW_ALPHA`），貼圖是靜態的所以不會閃。
3. **晶冠城牆的金邊只在有立面時畫**：前端的牆是俯視一格，沒有立面的牆（南鄰也是牆）就只畫米白錯縫的頂面，不畫金邊。樣張是每格都畫頂面＋正面。
4. **灰燼岩壁立面高 12px**（預設與雲嶺是 9px）：為了「深色立面」看得出來。要和其他區一樣也可以改回 9。
5. **殘牆的崩缺位置**：畫在牆的右端（不和右鄰相連的那一格），連續的牆中間約 1/3 格也會有；高度都在壓頂石內。
6. **灰水坑、裂谷照 `lip` 畫邊**：樣張每格各自畫內縮的邊框，這裡改成只在和其他地形相接的那一邊畫（同雲嶺寒潭的做法），相連的水坑、裂谷才接得起來。
7. **焦木渡橋的方向**：樣張畫的是南北向；東西向（`vertical` 為 false）時轉 90°。
8. **戰場上的致命標記**：裂谷上的紅色 X 是 `BattleRenderer` 統一疊的致命標記（不是這段畫的），在灰燼的黑色裂谷上比預設區醒目。要不要依區調淡，不在這段範圍。
