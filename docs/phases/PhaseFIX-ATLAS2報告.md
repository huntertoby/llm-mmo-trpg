# FIX-ATLAS2 報告：鎖住浮島滑過回饋＋頭目小頭像檢查門檻

兩項小修。A 照美術 PM 第九任定的規則（FIX-ATLAS1 待決 1 的答覆）；B 照 `docs/art/PB-1c驗收.md`「開發問的」第 1 點。

## A. 鎖住浮島滑過回饋（commit `dc6b437d`）

- **做法（畫布層）**：`world/AtlasMap.tsx` 對 `status !== "open"` 的浮島（鎖住、之後的賽季）的點擊區掛 `onPointerEnter／onPointerLeave`，記在 state `hoverLocked`，放進 `overlayKey` 並傳給 `AtlasPainter.paintOverlay(…, { hoverLocked })`。
  `render/worldMapPainter.ts`：貼浮島本體時，被滑過的那座不能去的島改貼「稍亮的一張」＝原本體離屏圖＋`globalCompositeOperation = "source-atop"` 疊 `LOCKED_HOVER_FILL`（`rgba(255,255,255,0.09)`，`LOCKED_HOVER_LIGHT = 0.09`），只亮在島的不透明像素上；用 `WeakMap` 依本體離屏圖快取，不重畫本體。位置、大小、張數、字牌、鎖頭都不變。
- **沒有加的**：CSS 底色、框、金色光暈、放大、濾鏡；游標維持 `.map-hit` 的 `default`。
- **解鎖浮島**：`.atlas-island.openable` 的手指游標與 `.atlas-island.openable:hover { background: rgba(255, 240, 200, 0.12) }` 逐字未動；painter 收到開放的島（含主城）一律忽略。
- 「鎖住浮島」解讀為 FIX-ATLAS1 待決 1 所說的「鎖住／之後的賽季浮島」兩種都適用（見待 PM 決定 1）。
- 實機量測（開發頁、1600×900、overlay 畫布裡荒原點擊區內不透明像素的平均亮度）：滑過前 157.45 → 滑過中 165.76 → 滑出 157.44（含島上方的前景雲一起平均，所以約 +5%；島本體本身是 +9% 白疊加）。滑過中 `cursor` = `default`、`backgroundColor` = `rgba(0, 0, 0, 0)`；雲嶺滑過 `pointer`、`rgba(255, 240, 200, 0.12)`（照舊）。
- 開發頁 `client/dev/map-gallery.html` 加 `?map=atlas&ashen=locked`（灰燼荒原改成鎖住、條件「世界事件：霧潮入侵」），截圖用。

### 新增測試

- `client/src/render/worldMapArt.test.ts` 新 describe「FIX-ATLAS2：鎖住浮島滑過只讓本體稍亮」（4 項）：亮度參數 8～10%、`source-atop`、`fillStyle`、整張 `fillRect`、沒有陰影／濾鏡／放大／漸層，稍亮那張和本體同大小；鎖住與之後的賽季的島滑過時主畫布指令與不滑過完全一樣（同位置、同張數、本體不重畫，只多做一張稍亮的）；開放的島、主城、不存在的區傳進來不做稍亮那張；連續滑過不重做。
- `client/src/world/mapHitHover.test.ts` 新 describe「FIX-ATLAS2：鎖住浮島滑過不用『能去』的語言」（3 項）：四座不能去的浮島滑過時沒有任何 `:hover` 規則設底色、box-shadow、transform、scale、filter、outline、border；命中的 cursor 宣告依特異度最高的是 `default`（`button { cursor: pointer }` 被 `.map-hit` 蓋掉），且沒有 `:hover` 換游標；解鎖浮島兩條規則逐字不變。
- FIX-ATLAS1 原有 5 項照過（未改）。

### 截圖（1600×900，無頭 Chrome `--mute-audio`、CDP，jpg 80，開發頁 `?map=atlas&ashen=locked&mute=1`）

- `docs/art/shots/fix-atlas2/locked-ashen-before-hover-1600.jpg`：滑過前
- `docs/art/shots/fix-atlas2/locked-ashen-hover-1600.jpg`：滑過灰燼荒原（同位置；島本體稍亮、說明卡一張、沒有框）
- `docs/art/shots/fix-atlas2/open-cloud-ridge-hover-1600.jpg`：解鎖的雲嶺滑過對照（原本的淡金底色）

注意：浮島會上下漂浮 ±3px，前後兩張的島位置可能差幾個像素；9% 白在縮小的截圖上差異細微（設計就是「稍微亮一點」）。

## B. 頭目部位小頭像檢查門檻（commit `940a669c`）

- `client/src/render/qIcon/bossParts.ts`：新增 `PORTRAIT_BBOX_MIN = { px: 20, res: 1, w: 12, h: 15, maxCenterDx: 0.5 }` 與 `portraitBboxOk(w, h, centerDx)`（只做檢查，畫法未動）。
- 開發頁 `client/dev/bossparts-gallery.html`（`src/dev/bossPartsGallery.ts`）：量測說明加上「20px 真 1 倍外接框寬 ≥12、高 ≥15、置中」，20px × 1 那格的 `body.dataset.check` 多一欄 `bboxOk`。實測（本次 main）：20px × 1 外接框 **14×15**、偏移 0、`bboxOk: true`（PB-1c 報告時是 12×15；兩者都過新門檻）。
- `docs/art/頭目部位-移植需求.md` 1.4：那一句改成「20px 真 1 倍外接框寬 ≥12、高 ≥15、置中（依 PB-1c 驗收 `PB-1c驗收.md` 改；原寫 ≥14px）」，其他沒動。

### 改到的既有測試（舊 → 新）

| 檔案 | 舊 | 新 |
|---|---|---|
| `qIconBossParts.test.ts` | `20px：裁切框寬佔顯示邊長 75%（15px ≥ 14）、水平置中`（寬 15、中心 10） | `20px 真 1 倍：裁切框寬佔顯示邊長 75%（15px）、高 16.4px，都不小於外接框門檻（寬 ≥12、高 ≥15）、水平置中`（原斷言保留，加寬 ≥12、高 ≥15） |
| 同上（新增） | — | `外接框門檻（PB-1c 驗收）：20px 真 1 倍外接框寬 ≥12、高 ≥15、置中`（12×15 偏移 0 過；11 寬、14 高、偏移 1 不過） |

## 結束碼

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test`（316 檔、4088 項） | 0 |
| `corepack pnpm -C client build` | 0 |
| `vitest run src/world/mapHitHover.test.ts src/world/atlas.test.ts src/render/worldMapArt.test.ts` | 0（38 項） |
| `vitest run src/render/qIcon/qIconBossParts.test.ts` | 0（10 項） |

雜湊／快照沒有重產。未跑 `scripts/check.py`、模擬；未 push。自己開的 vite（5791）與無頭 Chrome（CDP 9351）已用自己的 PID 關掉，兩埠已不在聽。

## 待 PM 決定

1. 「鎖住浮島」本段套用到 `status` 不是 `open` 的全部浮島（鎖住＋之後的賽季，四座）；若美術 PM 只要「鎖住」那種，改 `AtlasMap.tsx` 的 `locked` 條件即可。
2. 亮度取 9% 白（`source-atop`），沒有用 `ctx.filter = "brightness(…)"`（Safari 的 canvas 不支援 filter）。
3. 鍵盤焦點（Tab 到鎖住浮島）沒有加稍亮，只有滑鼠滑過；照現狀保留 `.map-hit:focus-visible` 的青色外框。
