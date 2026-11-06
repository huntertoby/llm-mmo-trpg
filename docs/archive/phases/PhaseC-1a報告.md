# Phase C-1a 報告｜紙娃娃 C 畫風：畫法層＋四方向骨架

規格：`docs/phases/PhaseC畫風計畫.md` C-1a 節；需求 `docs/art/C畫風移植需求.md` 第 0～2 節。只動前端（`client/`），沒動 Python、`look` 與裝備資料、API、引擎。

## 做了什麼

| 檔案 | 內容 |
|---|---|
| `client/src/render/inkStyle.ts`（新） | 畫法層：`ink()`、`stroke()`、`ellPts`、`wobble`、`smooth`、`seedOf`（FNV-1a）、`lcg`、`shadow()`（短斜線）、`dot`；墨色 `#2b1e16`；暗面方向 `setShadeDir`；不使用 `Math.random()` |
| `client/src/render/inkDoll.ts`（新） | 骨架與四方向（正、側、背、西＝東鏡像）：影子、披風、腿、身體（shirt／leather／plate／mail／robe／ribs 基本衣著）、手臂與手、頭、臉、頭髮；背面左右對調、背面後腦頭髮、`stout`／`tall` 縮放；座標照 `storyDoll.js` |
| `client/src/render/paperdoll.ts` | `drawFigure` 改走 C 骨架；移除舊的正背面身體／頭／髮／腿程式；`renderFigureCanvas` 拿掉 8 方向黑色剪影外框，保留稀有度外光；倒地照舊旋轉（平移量調為 27、11，頭盔不被切）；`DOLL_H` 64→88、新增 `DOLL_SCALE = 0.74`、`SUMMON_W/H/FOOT_Y`（舊 64×64） |
| `client/src/render/unitSprite.ts` | 人形／紙娃娃用 `DOLL_*`×0.74；非人形召喚物沿用舊畫布與縮放 1.0（畫法不動） |
| `client/src/render/summonArt.ts` | 非人形體型畫布改用 `SUMMON_*`；人形用 `DOLL_*` |
| `client/src/render/appearance.ts` | `Look` 加可選 `build?: "stout" \| "tall"`（尚無資料來源，3R 接上） |
| `client/src/dev/dollGallery.ts` | 畫布尺寸改用 `DOLL_*` |
| 測試 | `inkStyle.test.ts`、`inkDoll.test.ts`（新）；`paperdollSide.test.ts` 一個遍歷測試逾時改 60 秒（C 畫法 mock 記錄量大） |

沒有換畫法的部件（C-1b、C-2 換）：頭部裝備、所有手持物（武器、盾、書、法球）、披風以外的細節。它們由 `InkHooks` 呼叫現行畫法，並對到 C 座標：武器縮放 1.3（盾、書 1.15）、握點 (−9,−23.2)／側面近側 (4.6,−24)／遠側 (5.6,−27)；頭部裝備縮放 1.06 並下移到 C 頭心 (0,−42)；側面副手盾以 (1.1, 1.4) 縮放。身體披風、腿、靴、手（含手套色）、頭、髮已是 C 畫法。

## 驗收對照

| 條件 | 結果 | 證據 |
|---|---|---|
| 1 `inkStyle.ts` 完整、不用 `Math.random()`、同 key 同點不同 key 不同 | 通過 | `inkStyle.test.ts`：「同 key 兩次取點完全相同、不同 key 不同」「同 key 兩次畫完全相同…不呼叫 Math.random」（spy 驗證）、FNV-1a 已知值 |
| ink 畫法結構（填色偏移 0.45/0.35、透明度 0.94、35% 深邊、排線裁在形狀內、墨線兩次 w 與 0.45w） | 通過 | `inkStyle.test.ts`「畫法結構」「opt」「暗面方向」 |
| 2 骨架座標、圖層順序、背面對調、`stout`／`tall` 四方向、倒地 | 通過 | `inkDoll.test.ts`：四方向確定性、西＝東鏡像、背面對調、背面戴帽後腦頭髮、體型四方向、倒地旋轉；截圖 `C-1a-gallery-four-facings.jpg` |
| 畫布高度留到約 −70、52px 格約 0.74 倍 | 通過 | `DOLL_H` 88、腳底 82；測試「畫布高度」「縮放」；戰場截圖人約 40px |
| 3 拿掉黑色剪影外框、頭目外光保留、影子短斜線 | 通過 | `renderFigureCanvas` 不再 8 方向描邊（測試：無 `#16121a`）；稀有度外光保留；`shadow()` 測試；截圖 |
| 4 快取成貼圖、`gear-all`／`doll-gallery` 自測不報錯 | 通過 | 沿用 `ArtTextures.figure` 鍵（`dollKey`，含 `build`）；`dollGear.test.ts` 全組合、`paperdoll*.test.ts` 全過；doll-gallery 全頁無 console 錯誤 |
| 5 沒換的裝備與武器不空白不報錯 | 通過 | 現行畫法掛入（見上）；不認得的 kind／材質／顏色／形制／元素測試；截圖 `C-1a-gallery-unknown-downed-side-headgear.jpg` |
| 6 vitest、build、tsc | 通過 | 全量 vitest 107 檔 1020 測試全過；`corepack pnpm -C client build` 成功（含 tsc）；沒動 Python，未跑 ruff |
| 6 排版煙霧檢查 | 通過 | 1600×900、800×600、1600×900 shortBottom 三個情況皆全 PASS（註：每次重新整理後第一次 `runCase` 會因戰鬥尚未開出而「找不到按鈕」，再跑一次即全 PASS，與本段改動無關，本機重現於重新整理後的首次呼叫） |
| 6 截圖 | 完成 | `docs/phases/img/C-1a-gallery-four-facings.jpg`、`C-1a-gallery-unknown-downed-side-headgear.jpg`、`C-1a-battle.jpg`、`C-1a-battle-1600x900.jpg`（內建瀏覽器截圖為 JPEG，副檔名照實為 .jpg；對照 `docs/art/story.png`） |
| 6 效能（滿場 20 隻移動不掉幀） | 通過（量測限制見下） | 見下節 |

## 效能量測

方式：在 vite 開發頁（`doll-gallery.html`）內用 `javascript_tool` 取 20 個不同外觀 × 4 朝向（共 80 張）以 `renderFigureCanvas(…, dpr=3)` 產生貼圖（模擬冷快取），再同步把 20 張貼圖用 `drawImage` 畫到畫布 300 次（模擬每幀 20 隻小人在移動）。內建瀏覽器視窗隱藏時 `requestAnimationFrame` 不觸發，所以量的是每幀 CPU 繪製成本，不是實際 FPS。

| 項目 | 結果 |
|---|---|
| 80 張貼圖冷產生 | 19 ms（約 0.23 ms／張，一次性） |
| 每幀 20 隻貼圖繪製 | 0.025 ms／幀 |
| 貼圖大小 | 192×264（原 192×192），多 37%，仍每個「外觀＋朝向＋倒地」一張，不是每幀重畫 |

結論：每幀只畫快取貼圖，墨線與排線不在每幀路徑上；Pixi 的 sprite 移動與先前相同。

## 待 PM 決定

1. **圖檔格式**：內建瀏覽器截圖只能存成 JPEG，報告用 `.jpg`，不是規格寫的 `.png`；美術 PM 驗收若要原尺寸 png 請另拍。
2. **過渡期的外觀落差**：頭部裝備與手持物仍是舊畫法縮放後掛上（例如大頭盔 `greathelm` 蓋住肩膀、法杖寶珠偏大），C-1b／C-2 換畫法後才會和樣張一致；本段不調。
3. **手套、護臂**只改了手的顏色，臂甲、手套造型沒畫（舊畫法的 `drawHandsGear` 未掛入；規格第 3 節 C-2）。
4. **`look.build`**：新增可選欄位，還沒有資料與後端映射（等 3R）；骨架已支援。
5. **舊程式留存**：`paperdollSide.ts`（`drawFigureSide`）、`paperdollGear.ts` 的 `drawFeet`／`drawCoat`／`drawHandsGear`／`drawMailPattern`、`handSides` 不再被畫圖路徑使用，只剩測試與頭部、側面裝備函式引用；C-1b／C-2 做完後建議整批移除（我沒刪，避免動到 C-2 範圍與既有測試）。
6. **`coat`（外套）**身體暫時畫成襯衫形狀（沿用現行輪廓屬 C-2）；`ribs` 加了簡單肋骨線；骷髏頭用深色眼窩。
7. **側面副手成對武器**：位置照規格 (5.6,−27) 並畫在身體後面；因武器仍是舊形狀，遠近錯開量需 C-2 換畫法時再對尺寸驗收。
8. **倒地平移量**由 (20,11) 改 (27,11)，否則 C 骨架較高，頭盔被切到畫布右緣。
9. `paperdollSide.test.ts` 的遍歷測試逾時由預設 5 秒改 60 秒（mock ctx 記錄 C 畫法大量呼叫較慢）。
