# Q 版小圖示第 5 批（狀態圖示）：移植需求（給開發 PM）

美術 PM，2026-11-12。這是 Q 版小圖示的第三份移植需求，對應開發的移植段「⑤ 狀態」（`docs/美術PM交接.md` 0.01 節的分段：「(⑤，含 `statusIcon.ts` 的 `glyphColor`)」）。格式照第一份 `Q版小圖示-武器防具移植需求.md`。

- **定案依據**：使用者看過第 5 批，沒有意見（2026-11-12，原話：「沒意見」）。第 5 批第 2 版過審（`Q版小圖示-第5批狀態-審查.md`「第 2 版複審」：通過、沒有必修；文件 commit `7cf5c19e`）。
- **樣張版本**：第 5 批的圖 `5b838d65`（第 2 版）；依賴的第 4 批畫法 `10b1040f`（第 4 批第 2 版，含 `blit` 對齊）、真 1 倍修正 `0caaa84f`（`QIconsWeapons.blit()`）。**以 `5b838d65` 之後的 `docs/art/sample/` 為準**。
- **紀錄**（逐款描述、撞圖、仍不好認）：`docs/art/Q版小圖示-第5批狀態.md`。其第 8 節「給開發移植的重點」已整理進本文第 3 節，第 7、8 節的待決整理進第 4、6 節。
- 畫法規則 14 條：`docs/art/Q版小圖示樣張.md` 第 2 節（精簡版在 `docs/art/上手-畫法.md` 2.3；狀態圖示專用的做法在 2.9）。
- **開發 PM 對第一份需求的決定沿用**（`docs/phases/PhaseQI-1計畫.md` 0.0 節與 D3、D4）：畫布像素＝顯示尺寸 × 固定 2（`ICON_RES`）、CSS 顯示原尺寸、圖樣貼到整數裝置像素；開發頁另外可以切 1 倍只給驗收截圖用。
- **沒有實機截圖**：樣張的「現行」欄是遊戲端原始程式打包的 `docs/art/sample/tools/qStatusLive.js`（`statusIcon.ts`、`skillIcon.ts` 的 `statusIconTile`／`tileCanvas`）。
- **和技能圖示移植需求的關係**：第③＋④批（技能主圖、徽章與部件）的移植需求另一份正在寫（`docs/art/Q版小圖示-技能圖示移植需求.md`）。第④批的 32 種狀態圖樣在那份是「部件圓片裡的圖」，在這份是「狀態框裡的圖」——**同一套圖樣畫法**，依賴關係與誰先移植見 2.3 節、第 4 節第 1 點。

## 1. 目標與範圍

### 1.1 要換掉的畫法（只換框裡的圖，加上控制類的框底色）

| 遊戲端 | 現在 | 換成 |
|---|---|---|
| `client/src/render/statusIcon.ts` 的 `paintStatusIcon()` | 框（`framePath`、`FRAME_COLOR`、深底 `rgba(12,12,16,0.88)`）＋單色線條圖樣（`GLYPH` 查表、`drawGlyph`），圖樣顏色由 `glyphColor()` 決定 | 框照舊；**控制類的框底色**改填類別底色；框裡畫 Q 版圖樣（自帶本色） |
| 同檔 `statusIconCanvas(id, size)`（戰場頭頂，`ROW_ICON_FEET` 11px） | `size × 2` 的畫布、`paintStatusIcon(ctx, id, size/2, size/2, size−2)` | 同上，框邊長 9px 那一級（3.2 節第 6 點：頭頂用的不包外框、留底色圈） |
| `client/src/render/skillIcon.ts` 的 `statusIconTile(id)`＋`tileCanvas(tile, 20)`（主角狀態卡、單位資訊的狀態列） | 100 單位方塊、裁成半徑 49 的圓，`paintStatusIcon(ctx, id, 50, 50, 84)` → 框邊長 16.8px | 同上，框邊長 16.8px 那一級（3.2 節第 5 點：染底的包 1 裝置像素外框） |

**範圍數量**：名詞表的狀態＝`content/statuses.yaml` 全部 **118 個**（遊戲端不寫死清單，靠名詞表 `status_look`；`statusIcon.test.ts` 第一條已斷言 118）。圖樣來源（紀錄第 1 節）：

- **沿用第④批 40 個**：第④批 `qIconsParts.js` 的 `STATUS` 32 個直接呼叫；聖輝、暗影架勢貳～伍級 8 個用壹級的圖。
- **借用 4 個**：被揭露＝第④批效果「揭露」、定時炸彈＝第④批效果「定時炸彈」、免死＝第④批效果「免死」、護盾＝第③批記號「護盾」。
- **新畫 74 個**：手畫 39 個＋元素架勢 7 種紋章 × 5 級 35 個（戰意、烈焰、寒霜、雷霆、劇毒、疾風、大地；各級同一個圖）。

### 1.2 不動的（規則 13：框不動，只換框裡的圖）

- **框**：`framePath`（增益圓、減益圓角方、中性六角）、框色 `FRAME_COLOR`（增益 `#3fbf6a`、減益 `#e04848`、中性 `#c8a048`）、框線寬 `max(1.5, 框邊長 × 0.09)`、預設深底 `rgba(12,12,16,0.88)`、狀態卡外層 `.stat-badge`（24px 深褐方塊，`client/src/styles/status-card.css` 130 行）與 `tileCanvas` 的半徑 49 圓形裁切。
- **排序與排版**：`statusRank`、`sortStatuses`、`statusRowLayout`、`unitSprite.ts` 的頭頂列（`ROW_MAX_ICONS`＝2、「+N」膠囊）與 `minMark.ts` 的最小尺寸（`MIN_STATUS_GLYPH_PX`）（紀錄第 8 節）。
- **身上特效**：`bodyEffects`、`bodyUnder`、`bodyOver`（冰塊、星星、泡泡、藤蔓、持續傷害粒子）。
- **角落數字的現行邏輯**：`ui/statusCard.ts` 的 `statusCorner()`（剩餘回合 → 數值 → 空）、`StatusCardParts.tsx` 的 `.stat-corner`。要不要加級數見第 4 節第 2 點。
- **不在這一段的狀態相關畫法**（屬第③＋④批的技能圖示移植需求，或之後的批次）：
  - `skillIcon.ts` 的 `statusTile(id)`（技能組裝列、工坊選項的**部件圓片**，`skillParts.ts` 的 `statusGlyph`／`statusColor`）；
  - `unitSprite.ts` 的 `statusTexture()`（戰場上定時炸彈、蓄力徽章裡的圖，用的是 `tileCanvas(statusTile(id), 24)` 部件圓片）；
  - `qSummon.ts` 用 `drawGlyph` 在召喚物頭上畫的元素小圖（⑤b 元素關鍵字小圖樣再處理，紀錄第 8 節）。

### 1.3 用到這些畫法的地方（`client/src/` 查到的呼叫處；驗收截圖照這張表拍）

| 元件 | 檔案 | 尺寸（CSS px） |
|---|---|---|
| `StatusBadge`（`TileCanvas tile={statusIconTile(id)} px={20}`） | `ui/StatusCardParts.tsx`；用在 `ui/Hud.tsx`（主角狀態列）、`ui/UnitInfo.tsx`（單位資訊） | 20（框 16.8） |
| 戰場頭頂狀態列（`rowIconTexture()` → `statusIconCanvas(id, ROW_ICON_FEET)`，Pixi `Sprite` 寬高設成 11） | `render/unitSprite.ts`（`ROW_ICON_FEET` 定義在 `render/rowLayout.ts`） | 11（框 9）；實際螢幕尺寸隨地圖縮放與 `minMark` 倍率變（第 4 節第 3 點） |
| 開發頁 | `client/dev/status-gallery.html`（`src/dev/statusGallery.ts`：上半是 `paintStatusIcon(ctx, id, 30, 30, 52)` 的 118 個＋不認得的值，下半是真正的 `BattleRenderer` 戰場） | 52（另有戰場） |

## 2. 來源與移植方式

### 2.1 樣張畫法檔（`docs/art/sample/`）

| 檔案 | 內容 | 這一段用到的 API |
|---|---|---|
| `qIconsStatus.js`（`window.QIconsStatus`） | 第 5 批：118 個狀態的圖樣、類別底色、狀態框（框的邏輯只在這個檔） | `entry(id)` → `{ zh, topic, src, kind, d, level? }`；`def(id, cpx, head)`；`glyph(id, cpx, res, { ow, head })`；`paint(ctx, id, cx, cy, 框邊長, unitPx, res, { tint })`；`headCanvas(id, 11, zoom, { res })`（頭頂）；`cardCanvas(id, 20, zoom, { res })`（狀態卡）；`fitK(id, 框邊長, inset)`；`innerPath`、`innerWidth`、`outsideFrac`、`tintInset`；常數 `CLASS_BG`、`BASE_BG`、`FRAME`、`GLYPH_K`（0.74）、`HEAD_TINT`、`HEAD_MAX`（12）、`CARD_FRAME`（16.8）、`HEAD_FRAME`（9）；`NEW`、`EMBLEM`、`ELEMENTS`、`list()`、`polOf`、`clsOf` |
| `qIconsParts.js`（`window.QIconsParts`，第④批） | 32 個狀態圖樣（`STATUS`）、效果部件（揭露、定時炸彈、免死）、圖樣格比例 | `entry(cat, id)`、`list().status`、`BOX`（48/36：圖樣格邊長＝圖樣本身的 1.333 倍） |
| `qIconsSkills.js`（`window.QIconsSkills`，第③批） | 效果記號（護盾、召喚的小靈、準星…）、元素道具 | `ACT[id].d`／`.def`、`ELEMENT` |
| `qIcons.js`（`window.QIcons`） | 共用：剪影外框、畫法小工具、風格樣張的部分圖樣 | `render(def, px, res, { ow })`、`outlinePx`、`OUT`、`H`（`mix、f、rr、ci、el、poly、ln、starPts、flame、drop、halo、blank`）；**風格樣張的圖**：`ART.status`（第④批 `STATUS` 的冰凍、恐懼、倒地、加速由它縮進來）、`ART.hud.move`（纏繞的靴子） |
| `qIconsWeapons.js`（`window.QIconsWeapons`） | 只用貼圖對齊 | `blit(ctx, cv, x, y, a, res)` |

樣張頁：`q-icons-status.html`（`?part=a（&group=ctrl｜debuff｜buff｜shield｜neutral｜stance｜element｜boss）｜b（&group=all｜near）｜cls｜scene｜audit｜review（&only=id,…）｜hash｜true1x（&group=card｜head）`；紀錄第 10 節）。現行打包：`tools/qStatusLive.js`（自動產生，不要手改）。資料：`qPartsData.js` 的 `QPARTS_GLOSSARY.statuses`（後端 `build_glossary` 匯出，含 `status_look`）。

### 2.2 建議的移植方式

1. **照樣張原樣搬成 TypeScript，不另畫簡化版**（品質底線第 5 條）。`qIconsStatus.js` 的 `NEW`、`EMBLEM`、`HEAD_TINT`、共用零件（`shieldBlue`、`stancePlate`、`bladeSword`、`bolt`、`crystal`、`upArrow`、`slimArrow`、`bust`、`heart`、`star4`、`pole`、`medal`、`core`、`dome`…）、`entry`、`def`、`glyph`、`innerPath`、`fitK`、`paint` 逐行搬。新檔放 QI-1a 已建的 `client/src/render/qIcon/` 下（例 `status.ts`，檔名由開發決定），共用核心用 `client/src/render/qIcon/core.ts`（QI-1a 已有 `render`、`halo`、`blit`、`ICON_RES`、`outlinePx`、`blank`…），不另寫一份。
2. **清單與欄位用遊戲端的名詞表**（`battle/glossary.ts` 的 `statusLook`／`statusName`），不搬樣張的 `G()`／`lookOf`。極性、類別判斷照現行 `polarityOf()`（不認得 → neutral，和樣張 `polOf` 相同）。
3. **出圖照樣張 `paint()` 的流程**：框（照現行）→ 底色（深底；有類別再填類別底色）→ 框線 → 圖樣 `glyph()` 用 `blit()` 貼在框中心。`paintStatusIcon()` 的簽名不變，呼叫處（`statusIconCanvas`、`statusIconTile`、開發頁）不用改；但它需要知道 `unitPx` 與 `res`（2.4 節第 6 列）。
4. 搬完用樣張頁對照：同一個狀態、同一個尺寸與 `res`，遊戲端的圖和樣張 `headCanvas`／`cardCanvas` 的圖應該逐像素相同（`blit` 兩邊都有，不像裝備格會差對齊位移）。差異要列出原因。

### 2.3 和第③＋④批移植的依賴（共用同一套圖樣畫法）

狀態圖樣**不是獨立的一個檔**：118 個裡 44 個（沿用 40＋借用 4）直接呼叫第③、④批的畫法，新畫的也呼叫它們的零件。這一段要用到的別批畫法：

| 來源 | 用到的 | 誰用 |
|---|---|---|
| `qIconsParts.js`（第④批） | `STATUS` 32 個、`entry("effect", "reveal"｜"delayed_damage"｜"cheat_death")`、`BOX` | 沿用 40、借用 3、回春護盾的芽（`STATUS.regenerating`） |
| `qIconsSkills.js`（第③批） | `ACT.shield`、`ACT.summon`、`ACT.mark`；第④批 `STATUS` 裡又用到 `ACT` 的 `slow`、`dot`、`mark`、`curse` 與 `ELEMENT.poison` | 護盾、號令、烙印護盾、第④批的幾個狀態 |
| `qIcons.js`（風格樣張） | `ART.status` 的 `frozen`、`feared`、`prone`、`hasted`；`ART.hud.move` | 第④批的 4 個狀態、纏繞 |

完整的呼叫清單：待開發查證（照樣張逐行搬時順著 `QP.entry`、`QS.ACT`、`Q.ART` 往下追）。QI-1a 的 `core.ts` 只搬了 `qIcons.js` 的共用部分與八把武器樣本（`PhaseQI-1計畫.md` A1：「技能、物品、狀態、HUD 那幾區不搬」），`ART.status`、`ART.hud.move` 與 `H.drop` 這一段要補（`core.ts` 目前有沒有 `drop`：待開發查證）。

**誰先移植、共用檔放哪：開發 PM 決定**（第 4 節第 1 點）。美術的要求只有兩條：(a) 同一個題材在部件圓片與狀態框裡**呼叫同一份畫法**，不各搬一份；(b) 後移植的那一段沿用先移植那一段的檔，不重搬。

### 2.4 樣張與遊戲端對不上的地方（逐條）

| # | 項目 | 樣張 | 遊戲端 | 移植怎麼做 |
|---|---|---|---|---|
| 1 | 圖樣大小 | 圖樣本身（±10 單位）＝框邊長 × `GLYPH_K`（0.74）× `fitK`；畫在 48 格、±10 單位放大 1.8 倍，圖樣格邊長＝圖樣本身 × `BOX` | `ctx.scale(size/26 × 0.95)`：±10 單位 ≈ 框邊長 × 0.73 | 照樣張 |
| 2 | 圖樣顏色 | 每個圖樣自帶本色；類別色畫在框底色（`CLASS_BG`） | `glyphColor()`：`CTRL_COLOR` → 持續傷害元素色 → `OWN_COLOR` 14 個 → `POL_COLOR` | 照樣張；`glyphColor` 怎麼處理見 3.3 節第 9 點 |
| 3 | 元素架勢 | 各級同一個圖（`stance_<元素>_<級>`，`level` 只記在 `entry` 裡，不畫） | `elementStanceGlyphs()`：劍＋元素小記號＋底下 1～5 顆級數點 | 照樣張，不畫級數點；級數見第 4 節第 2 點 |
| 4 | 不認得的狀態 | `def()` 退回 `QP.entry("status", id)`（樣張的 118 個都有圖，沒走到） | `drawGlyph()` 畫名稱第一個字（`fillText`），顏色跟 `glyphColor` | **照遊戲端**畫名稱第一個字；字色米白（`#f2e6c8`），底照類別規則（紀錄第 8 節） |
| 5 | 框線寬 | `max(1.5, 框的 CSS px × 0.09) / unitPx`（以 CSS px 算） | `max(1.5, size × 0.09)`（以 ctx 單位算；狀態卡在 100 單位的 tile 裡畫） | 照樣張。20 與 11 兩種尺寸兩邊算出來相同（狀態卡 7.56 單位＝1.512 px；頭頂 1.5 px）；其他尺寸（開發頁 52、之後若 `TileCanvas` 用別的 px）才會不同 |
| 6 | 畫圖時知不知道 `unitPx`、`res` | `paint(ctx, id, cx, cy, size, unitPx, res)` 明確收；`cardCanvas` 傳 `px/100`、頭頂傳 1 | `paintStatusIcon(ctx, id, cx, cy, size)` 沒有這兩個；`statusIconTile` 的 `draw: (ctx) => …` 只收 ctx，`tileCanvas(tile, px)` 才知道 `px` 與 `DPR` | `paintStatusIcon` 要能拿到 `unitPx` 與 `res`（加參數、或 `AssemblyTile.draw` 多傳、或從 `ctx.getTransform()` 算）：做法由開發決定。`blit()`、框線寬、`fitK` 的內縮都要用到 |
| 7 | 內部解析度 | `res` 可給 1（真 1 倍）或 2 | `statusIcon.ts`、`skillIcon.ts` 各自寫死 `DPR = 2` | 用 `core.ts` 的 `ICON_RES`；開發頁可切 1（`PhaseQI-1計畫.md` D4） |
| 8 | 圖樣外框 | `glyph()`：圖樣 ≤14px 不包外框；狀態卡染底的框給 `ow: 1/res`（1 裝置像素）；頭頂染底的給 `ow: 0` 並換 `HEAD_TINT` | 現行線條圖樣沒有外框 | 照樣張（3.2 節第 5、6 點） |
| 9 | `fitK` 的算法 | 執行期畫一張 6 倍的遮罩與圖樣、`getImageData` 量出框的像素，從 1 往下每次 0.02（`fitMemo` 記住） | 沒有 | 結果要和樣張一樣；執行期量或建置時算成表由開發決定（第 4 節第 4 點） |
| 10 | 快取鍵 | — | `statusIconKey` ＝ `id｜polarity｜control_group｜dot_element｜第一個字｜size`；`tileKey` ＝ `px｜tile.id` | 兩個都要再加 `res`（若開發頁或之後不固定 2）。`fontEpoch` 照舊（只有「第一個字」用到字型） |
| 11 | 名詞表來源 | `qPartsData.js`（第④批匯出的快照） | `/api/glossary`、測試用 `client/src/battle/fixtures/glossary.json` | 照遊戲端；兩者都是後端 `build_glossary`，118 個一致 |

## 3. 一定要做對的重點

每條後面括號是出處（`紀錄` ＝ `Q版小圖示-第5批狀態.md`，`審查` ＝ `Q版小圖示-第5批狀態-審查.md`，`上手` ＝ `上手-畫法.md`，`第一份` ＝ `Q版小圖示-武器防具移植需求.md`）。

### 3.1 框與底色

1. **類別 → 框的底色**（美術 PM 定案，不改）：先填現行深底 `rgba(12,12,16,0.88)`，有 `control_group` 時再填一層**不透明**的類別底色。框線最後畫。（紀錄第 2 節、8 節第 2 點；審查第 1 版「對美術 PM 5 點暫定決定的意見」第 1 點）

   | `control_group` | 狀態 | 底色 |
   |---|---|---|
   | `hard`（硬控） | 暈眩 `stun`、冰凍 `frozen` | `#d4ac20`（亮芥末黃） |
   | `movement`（移動） | 緩速 `slow`、定身 `root` | `#2f78c8`（中藍） |
   | `mental`（心智） | 嘲諷 `taunted`、恐懼 `feared`、沉默 `silenced` | `#8a4ccc`（中紫） |
   | 沒有類別 | 其他 111 個 | 現行深底 `rgba(12,12,16,0.88)`（不另填） |

   不要用半透明疊在深底上（第 1 版樣張對照 (b) 的 45% 疊色在 1 倍下變成褐色）。（紀錄第 2 節；上手 2.9）
2. **類別只看資料欄位**：纏繞 `entangled` 現行用移動藍的專屬色，但它沒有 `control_group`，照資料**不染底**（Q 版是靴子加繩子）。之後新增的狀態只要 `control_group` 對就自動染底。（紀錄第 2 節）
3. **極性照現行**：框形、框色、線寬不動（1.2 節）；`polarityOf` 不認得的退 neutral。

### 3.2 圖樣大小、外框與貼圖

4. **圖樣收進框線內緣（`fitK`）**：圖樣本身邊長＝框邊長 × 0.74 × `fitK(id, 框邊長, inset)`。`fitK` 從 1 往下每次 0.02，直到圖樣畫到框內緣以外的像素 ≤0.5%；最小 0.7（留底色圈的那一級 0.4）。**狀態卡（框 16.8）與頭頂（框 9）各算一次**；框內緣照 `innerPath()`（圓＝半徑扣半條框線、圓角方＝邊長扣一條框線、六角＝對邊距離扣一條框線）。固定比例會蓋到框線（第 1 版量到 29 個出框）。（紀錄第 1 節、8 節第 3 點；上手 2.9）
5. **狀態卡 20（框邊長 ≥ `HEAD_MAX` 12 CSS px）染底的 7 個：圖樣包 1 個裝置像素的外框**（`#16121a`，`glyph(…, { ow: 1/res })`）。黃星在黃底、紫對話框在紫底沒有外框會黏住；這是規則 8「≤14px 不包外框」的例外（美術 PM 定）。不染底的照規則 8 不包外框。（紀錄第 2 節、8 節第 4 點；審查第 1 版意見第 2 點）
6. **頭頂 11（框邊長 < 12）染底的 7 個：不包外框，圖樣四周留 1 個裝置像素的底色圈**：`inset = tintInset(框邊長, res, 類別)` ＝ `1/res` CSS px，`fitK` 的目標改成「框內緣再內縮 `inset`」（`innerPath(pol, size, inset)`），這一級最小縮放 0.4。並且**暈眩、沉默、嘲諷改用頭頂用的形**（`HEAD_TINT`）：暈眩＝一顆米白大星（`#fbf3dc`，省掉暈眩弧與小星）、沉默＝淡紫白對話框（`#f0e2ff`、深色叉）、嘲諷＝四道橘青筋往外推、中心留洞露紫。狀態卡用原本的形。第 1 版頭頂包外框被退（嘲諷的紫只剩角縫、暈眩糊成芥末色一團）。（紀錄第 2 節、8 節第 4 點、12 節必修 1 與可修 1；審查第 1 版必修 1、第 2 版複審）
7. **「類別色看得到」優先於「圖樣認得出」**：頭頂真 1 倍圖樣只剩 4～5px，底色圈一定要在；不要為了圖樣大一點把底色圈拿掉。（上手 2.9；紀錄第 7 節第 2 點）
8. **貼圖對齊整數裝置像素**：圖樣先畫成 canvas（邊長 `round(圖樣格 × res)`），照原尺寸 `blit()` 貼、左上角四捨五入到整數裝置像素，**不要** `drawImage(cv, x, y, a, a)` 縮放貼到小數位置（1px 外框會被抹成半透明、整塊糊掉）。`blit` 的最後一個參數是「ctx 每單位幾個裝置像素」：頭頂 `statusIconCanvas`＝`res`（原點在整數像素上），狀態卡 `statusIconTile` 在 100 單位的 tile 裡＝`px / 100 × res`（20px、res 2 時 0.4）。（紀錄第 8 節第 5 點；上手 2.5 最後幾條；第一份 3.1 第 1 點；`Q版小圖示-前三批真1倍補查.md` 結論）

### 3.3 `glyphColor` 與其他程式

9. **`glyphColor` 不再決定狀態框裡的圖樣顏色**。`paintStatusIcon` 改成：框照現行 → 深底 → 類別底色（`CLASS_BG[control_group]`）→ 框線 → Q 版圖樣。現行 `CTRL_COLOR` 可以改名或改值成第 1 點的表；`OWN_COLOR`、`POL_COLOR` 狀態框不再用。**但** `skillParts.ts` 的 `statusColor()` 仍呼叫 `glyphColor()` 給技能的**部件圓片**（`statusTile`）上色：這一段若比第③＋④批先移植，`glyphColor()` 與 `CTRL_COLOR` 的原值要留給部件圓片，另開一個取類別底色的函式；若後移植，看③④換完 `statusTile` 之後還有沒有人用再刪。`GLYPH`、`drawGlyph` 同理（部件圓片、`qSummon.ts` 還在用）。（紀錄第 8 節第 1、4 點；本文查證：`client/src/render/skillParts.ts` 208～228 行、`qSummon.ts` 103 行）
10. **排序照現行 `statusRank`**：硬控 → 移動／心智控制 → 持續傷害 → 其他減益 → 增益 → 中性，同級依 ID；`sortStatuses`、`statusRowLayout`、頭頂最多 2 個圖示加「+N」、`bodyEffects` 都不動。它們讀 `control_group`／`dot_element`／`polarity`，和圖樣顏色無關。（紀錄第 8 節第 3 點）
11. **測試要改的**：`render/statusIcon.test.ts` 的「圖樣顏色：硬控黃、移動控制藍、心智控制紫、持續傷害用元素色」（92～101 行）與 `glyphColor("new_buff")`（123 行）改成驗**框底色**（硬控 `#d4ac20`、移動 `#2f78c8`、心智 `#8a4ccc`、其他不填）；「每個狀態都有圖樣」（45 行，`GLYPH[id]`）改成驗 Q 版查表每個都有；「四組原本重複的圖樣已分開」（75 行）改成 Q 版圖樣的對應斷言。逐條在報告寫「舊斷言 → 新斷言」，不要放寬。其他測試有沒有讀 `glyphColor`／`GLYPH` 的：待開發查證。（紀錄第 8 節第 3 點；本文查證）
12. **元素架勢**：`stance_<元素>_<級>` 的 9 個元素各一個圖，1～5 級同一個；聖輝、暗影用第④批的壹級圖，其他 7 個是新的紋章（`EMBLEM`）。姿態 9 個與元素架勢 9 種都是**同一個六角臂章**（第④批 `stancePlate` 原樣），靠臂章底色與紋章分，是刻意的（剪影排會一樣）。（紀錄第 3、5 節、6.2 節）
13. **第④批的 32 個不要重畫**：直接呼叫第④批那一份（2.3 節），連第④批第 2 版補的 15 種狀態也是。同一個題材在部件圓片、狀態框用同一個形。（紀錄第 1、3 節；上手 2.8「沿用上一批的記號，直接呼叫」）
14. **後端不用動**：不需要多帶欄位；級數若要進角落，`status_id` 末碼就是級數。（紀錄第 8 節）
15. **只在樣張端的**：`tools/qStatusLive.js` 是樣張頁「現行」欄用的打包檔，移植完它會和遊戲端不同，不影響驗收；要重產照紀錄第 8 節最後一條（vite lib 模式、`pixi.js` external、檔頭寫「自動產生」）。（紀錄第 8 節）

## 4. 要開發 PM 決定的事

| # | 項目 | 說明 | 美術建議 |
|---|---|---|---|
| 1 | **這一段與第③＋④批誰先移植、共用檔放哪** | 2.3 節：狀態 44 個直接呼叫③④的畫法，新畫的也用它們的零件。③④先：這一段只加狀態的檔、沿用③④已搬的部件。⑤先：這一段要先搬第④批 `STATUS` 與相依部件、第③批的幾個 `ACT`、`qIcons.js` 的 `ART.status`／`ART.hud.move`，③④之後沿用、不重搬。檔名、模組切法（例 `client/src/render/qIcon/` 下 `parts.ts`、`skills.ts`、`status.ts`）由開發定 | ③④先（部件是狀態的上游）。不論哪個先，同一個題材只有一份畫法 |
| 2 | **狀態卡角落數字要不要顯示元素架勢的級數** | 現況（只讀 `client/src/`、沒有實機確認）：`ui/statusCard.ts` 的 `statusCorner(s)` 依序是 `remaining`（剩餘回合）不是 null 就寫回合數 → 否則 `amount` 不是 null 就寫數值 → 都沒有就空；`StatusBadge` 只有非空時畫 `.stat-corner`；測試在 `ui/statusCard.test.ts`。元素架勢在 `content/statuses.yaml` 是 `expires: never`（推斷 `remaining` 是 null），級數目前只在名稱（壹～伍）與說明卡，**角落不顯示級數**。架勢有沒有 `amount`（例如維持費）：待開發查證。選項：(a) 架勢的角落改顯示級數（1～5 或壹～伍），並定和回合數／數值誰優先；(b) 照舊，級數只放說明卡。頭頂 11 沒有角落數字，戰場上看不到級數（現行也看不到） | **(a) 架勢顯示級數**：架勢沒有回合數，角落是 20px 唯一讀得出級數的地方（圖上 5 顆點每顆不到 1px，現行真 1 倍也看不到）。若架勢也有 `amount`，美術建議級數優先。最後由開發 PM 定 |
| 3 | **頭頂圖示在實際螢幕尺寸的取樣** | 頭頂的畫布是 `11 × 2` 裝置像素，但 Pixi `Sprite` 依地圖縮放（`BattleRenderer` 的 `resolution` ＝ `devicePixelRatio × scale`）與 `minMark` 的反向放大顯示，螢幕上的尺寸通常不是 11 CSS px，會被重新取樣，抵銷 3.2 節第 8 點的整數像素對齊與第 6 點的 1 裝置像素底色圈。實際各寬度下的螢幕尺寸：待開發查證 | 美術要的是結果：1600 寬與 800 寬實機的頭頂圖示，底色圈看得到、外框不比樣張真 1 倍糊（驗收第 6 項）。做法（照實際尺寸出圖、或接受）由開發 PM 定，不擋移植 |
| 4 | `fitK` 執行期量或建置時算成表 | 2.4 節第 9 列。執行期量要 `getImageData`（vitest 沒有真畫布，要假畫布或略過）；建置時算要多一個產表腳本，表要涵蓋狀態卡 16.8、頭頂 9 × 兩種 `res`（染底的 `inset` 隨 `res` 變） | 都可以；結果要和樣張的 `fitK` 一樣（報告附 118 × 兩種框的對照） |
| 5 | `paintStatusIcon` 怎麼拿到 `unitPx`、`res` | 2.4 節第 6 列 | 都可以；只要 `blit` 對齊與框線寬照樣張 |
| 6 | 晶能湧動／狂湧要不要也用角落數字顯示「1／2」 | 兩個在頭頂 11 分不開（現行也一樣），20 真 1 倍是一支對兩支箭頭、分得開。審查第 2 版複審：「是同一件事的兩階，角落數字可以補（交開發 PM 決定）」。兩個都是 `expires: never`、沒有級數欄位 | 不急；做第 2 點時一起看，不做也不擋 |

**需要玩法 PM 決定的：沒有。** 後端不用動（第 3 節第 14 點）。

## 5. 驗收（美術 PM 會看的截圖）

每項都要有截圖；實機到不了的用開發頁（`client/dev/status-gallery.html`，`src/dev/statusGallery.ts`，可擴充）畫出來，並在報告寫「實機未看」。瀏覽器網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`。

**最小尺寸一律交兩種**：(a) **DPR 2**（遊戲的內部解析度 `ICON_RES`）；(b) **真 1 倍**（畫布寬高＝CSS px，內部解析度 1）。兩種都用最近鄰放大 6 倍（`image-rendering: pixelated`）；截圖用裝置像素比 1 拍（放大 6 倍的一個像素在截圖裡是 6×6 的純色方塊）。開發頁目前只畫 52px、固定 ×2，沒有參數；請照 `PhaseQI-1計畫.md` A7 的樣子加 `?px=`（20＝狀態卡構圖、11＝頭頂構圖）、`&res=1|2`、`&zoom=`、`&set=`（對到下表各項）、`&tint=0`（不染底，對照用）：待開發查證做法。

**截圖格式**（使用者 11-12 規則，`docs/開發PM交接.md` 6.5.2）：只有**真 1 倍／最近鄰放大的特寫**可以用 PNG（單張 ≤300 KB）；其他（情境、版面、實機）jpg 品質 80、單張 ≤300 KB；**每段 ≤10 張**（PNG 也算），可以把幾項拼成一張對照圖。存 `docs/art/shots/<段名>/`（段名由開發 PM 定），報告寫完整路徑。

| # | 要看的 | 尺寸 | 對照的樣張截圖（`docs/art/` 下） |
|---|---|---|---|
| 1 | 118 個，狀態卡構圖（現行的框＋Q 版圖樣） | 20 真 1 倍＋DPR 2（6 倍最近鄰） | `shots/qicons/true1x/status-card20-01.png`～`-05.png`；分類特寫 `closeup/qicons/status/a-ctrl.png`、`a-debuff.png`、`a-buff.png`、`a-shield.png`、`a-neutral.png`、`a-stance.png`、`a-element.png`、`a-boss.png` |
| 2 | 118 個，頭頂構圖 | 11 真 1 倍＋DPR 2（6 倍最近鄰） | `shots/qicons/true1x/status-head11-01.png`～`-04.png` |
| 3 | 控制類 7 個：染底、狀態卡 20 的 1 裝置像素外框、頭頂 11 的底色圈與 `HEAD_TINT` 三個形（暈眩米白星、沉默淡紫白對話框、嘲諷往外推的青筋）；加一列 `tint=0` 對照 | 20、11 各真 1 倍＋DPR 2 | `closeup/qicons/status/cls.png`、`v2-changed.png` |
| 4 | 撞圖組：暖色四個六角（狂怒、烈焰姿態、焰刃、烈焰架勢）、冷色四個六角（堅守、霜刃、冰川、寒霜架勢）、岩石／殼／甲（穩若磐石、大地架勢、硬殼、熔殼、破甲、易傷、石膚）、晶能湧動／狂湧 | 20、11 真 1 倍 | `closeup/qicons/status/v2-near-hex.png`、`v2-near-rock.png`；`shots/qicons/status-near-1.png`、`status-near-2.png`；剪影排 `shots/qicons/status-b.png` |
| 5 | 元素架勢 9 種 × 5 級在狀態卡（含角落數字，照第 4 節第 2 點的決定；不顯示級數也要拍一張證明各級同圖） | 20 DPR 2；實機或開發頁 | `closeup/qicons/status/a-element.png` |
| 6 | 實機戰場頭頂狀態列：控制類、持續傷害、增益、中性各至少一個；排序（`statusRank`）、2 個加「+N」；**1600 寬與 800 寬各一張**（地圖縮放不同，第 4 節第 3 點）；另附頭頂一格的放大圖看底色圈 | 實機 | `shots/qicons/status-scene.png`、`status-scene@2x.png` |
| 7 | 實機狀態卡：主角 HUD 狀態列（`Hud.tsx`）與單位資訊（`UnitInfo.tsx`）各一張，含角落數字（回合數、數值、空）、控制類染底 | 實機 | `shots/qicons/status-scene.png`、`status-scene@2x.png` |
| 8 | 不認得的狀態（開發頁的 `brand_new_status` 與空字串）：名稱第一個字、米白字；增益、減益、中性與有類別各一 | 20、11 DPR 2 | 沒有樣張（2.4 節第 4 列照遊戲端），美術看清楚與否 |

上面 8 項拼圖後要在 10 張以內（例：第 1、2 項各拼成 2 張 PNG、第 3、4 項各 1 張 PNG、第 5、8 項合 1 張、第 6 項 2 張 jpg、第 7 項 1 張 jpg）。

另外請在報告寫明：(a) 2.2 節第 4 點的對照方式與結果（遊戲端與樣張 `headCanvas`／`cardCanvas` 逐像素相同的有幾個，不同的列出原因）；(b) `glyphColor`、`CTRL_COLOR`、`OWN_COLOR`、`POL_COLOR`、`GLYPH`、`drawGlyph` 哪些已拿掉、哪些還留著給誰用（3.3 節第 9 點）；(c) `fitK` 的結果和樣張自查表（`uv run python docs/art/sample/tools/qicons_shots.py --audit status`）一致與否。

## 6. 待決／已知未修（都不擋移植）

審查第 2 版複審沒有必修；下面是複審列的可接受、待之後處理的項目。移植照現在的樣張即可；之後改了樣張再另給增量。

**跨批（第④批的可修，不擋這一段）**
- **靈魂連結與第④批效果「分擔傷害」不同形**：狀態是兩個扣在一起的淡紫雙環，第④批的效果圓片是 Y 形分岔箭頭；唯一施加靈魂連結的效果就是分擔傷害，玩家對不起來。複審建議之後把第④批的效果圓片統一成同一個雙環（18px 圓片要另看真 1 倍的洞還在不在），算第④批的可修。統一時只改第④批那一個效果圓片，狀態這邊不變。（紀錄第 5、7 節；審查第 2 版複審「靈魂連結與分擔傷害要不要統一」）

**仍像別的東西（可接受，使用者沒意見）**
- 破甲像 T 恤（T 字形亮鋼胸甲＋黑裂縫；比第 1 版的紙箱接近「甲」）；之後要改是在肩上加圓肩甲片的暗面或兩個鉚釘。
- 穩若磐石像一塊石頭，偶爾像方糖、麵包（不再像墓碑）。
- 界崩像兩塊碎石、蓄力像旋轉的光球、歸一的霧旋看不出是霧、反傷護盾像長角的盾。
- 隱蔽的兜帽在六角框裡縮到 0.8（頭頂 0.7），比同排小一圈。
（紀錄 6.3 節；審查第 2 版複審）

**頭頂 11px 真 1 倍認不出題材的（現行同尺寸也一樣）**
- 暈眩：黃底上一塊米白，看不出星（類別色看得到）。
- 沉默：紫底上一塊淡色長方，看不出叉（類別色看得到）。
- 晶能湧動與晶能狂湧分不開（20 真 1 倍分得開；角落數字見第 4 節第 6 點）。
- 另外：緩速的錶只剩一個金點、嘲諷是紫方塊四角橘點、破甲是一塊灰白、應變與穩若磐石只剩米白／灰一團；元素架勢與姿態在頭頂主要靠臂章底色分（焰刃與烈焰架勢最近）。
（紀錄 6.1 節；審查第 2 版複審「畫圖 agent 自承的四項」）

**已知、交使用者時已講明的（不是缺陷）**
- 控制類別色從「圖樣顏色」改成「框的底色」（硬控黃、移動藍、心智紫）；狀態卡 20 的染底圖樣多一圈細外框，頭頂 11 改成不包外框、四周留一圈底色，暈眩、沉默、嘲諷在頭頂用簡化的形。
- 元素架勢 5 級同一個圖；級數與晶能湧動／狂湧的階要不要用角落數字顯示由開發 PM 定（第 4 節第 2、6 點）；戰場頭頂看不到級數（現行也看不到）。
- 誓約之力易／中／難同形，只差銅、銀、金（20、11 真 1 倍都分得開，比現行的點數好分）。
- 姿態 9 個與元素架勢 9 種同一個六角臂章、護盾家族 6 個同一面盾、熔核三個與殼兩個同形換色：刻意同形，靠底色或記號分。
- 首領戰的狀態（源晶、熔核、殼、陣）都是新題材，有幾個偏抽象。
- 樣張只在樣張頁看過，沒有實機圖；遊戲端固定 DPR 2，真 1 倍是最壞情況。
（審查第 2 版複審「交使用者時要講明的」；紀錄第 11 節）

## 7. 順手記（不屬這次範圍，排不排由開發 PM 決定）

- 戰場上定時炸彈、蓄力徽章裡的狀態圖（`unitSprite.ts` 的 `statusTexture()`，用部件圓片 `statusTile` 24px）會跟著第③＋④批的部件圓片換，不在這一段。
- 開發頁 `statusGallery.ts` 的標題寫「32 個狀態」，實際列的是名詞表全部（118 個）；擴充參數時可以順手改字。
