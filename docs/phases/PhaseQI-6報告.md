# Phase QI-6 報告：⑧ 事件卡 Q 版小圖示＋⑧b 頭頂泡泡（搬畫法、接線、開發頁、截圖）

> 實作者（Opus 5.5），2026-11-12。需求：`docs/art/Q版小圖示-事件卡移植需求.md`（第 4 節照美術建議，使用者「照建議」）。起點：本機 main（含 `366cb145`）。未 push。後端、`content/` 沒動。資訊面板（PNL）的部分沒做，只留了需求 2.3 的「圖樣本身」入口。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| 搬畫法 | 新檔 `client/src/render/qIcon/event.ts`：由 `docs/art/sample/qIconsEvent.js`（⑧ 第 2 版、⑧b 第 2 版）逐行搬，28 個圖示＋d20＋泡泡表 9 個；`legacy48.ts` 加 `ART.event`（戰鬥、說服、調查、交易＋`eventSword`、`crossSword`、`heart`） | `a42d0cdc` |
| 接線 | `storyIconArt.ts` 改呼叫 `QE.paint`（`SolutionGlyph`、`MiscGlyph`、`AttrIcon`、`D20` props 不變）；小牌 `eventArtParts.drawBadgeIcon`（`eventArt.ts`、`eventArtAwaken.ts`）；泡泡 `bubble()` 改 `QE.drawBubble`；`EventCard` 的插圖照實際顯示寬出圖（`eventArtScale`） | `3246efc3` |
| 開發頁 | `client/dev/event-gallery.html`＋`src/dev/eventGallery.ts`（`?set=a|d20|badge|bubble|art|hash`、`&res=`、`&zoom=`、`&w=`、`&grp=`、`&full=0`、`&label=0`）；`src/dev/eventLegacy.ts`＝舊小牌／泡泡畫法，只給「現行｜Q」並排 | `28325e6a`、`7567ac39` |
| 測試 | 新 `render/qIcon/qIconEvent.test.ts`（16 項）；改既有 2 檔（第 3 節） | `39f407a2`、`3246efc3` |
| 截圖 | `docs/art/shots/qi6/` 10 張 | `7567ac39` |
| 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md` | 本 commit |

## 2. 逐條對需求

| 需求 | 結果 |
|---|---|
| 1.1 選項 8、其他 5、屬性 6、d20 | `drawStoryIcon` → `QE.paint`；圓環照 `drawChip`（深底 `#2a241e`、線寬 max(1.2, 6%)），裁在圓環內緣 `size/2 − 線寬/2`；圖樣照原尺寸 `blit` 對齊整數裝置像素 |
| 1.1 小牌 8 | `eventArt.ts` 的 `ICON[s.icon](…, BADGE_ICON_INK)` → `drawBadgeIcon(ctx, s.icon, 21, 20)`（中心 (21,20)、邊長 14、不包外框）；膠囊、金邊、標題字照現行（截圖 3、6） |
| 1.1 泡泡（⑧b） | `bubble()` 的 `ICON[icon](ctx, x, y − 15, 13)` → `QE.drawBubble(ctx, icon, x, y − 15, QE.ctxRes(ctx))`；泡泡框照現行 |
| 1.2 不動的 | 框、地物營火 `ICON.rest(…, 22)`、`townArt.ts`、`mapMarks`、`Portrait`、選項列排法、`SolutionGlyph` 預設 18 都沒動 |
| 1.3 行為改變 9 點 | 照樣張搬，沒改 |
| 2.1 沿用已移植 | 全部直接呼叫：`parts.entry`（隱蔽、激昂、生命、揭露、打擊、源力）、`ART.hud.exit`、`core.fistArt`、`hud.def`（warn、bar_N、coin）；`ART.event` 四個搬進 `legacy48.ts` |
| 2.2 新畫 | 都在 `qIcon/event.ts` |
| 2.3 圖樣本身入口 | `QE.bareGlyph(id, px, res)`（照 `infoPanels.js` 的 `evBare`：px＝圖樣本身邊長，小牌 fill 當 1）；測試 T6 |
| 3 第 1～3 點 | 大小、外框、d20 四色階與外框 16→1／24→1.2／64→1.6、點數常數照現行：T2～T4、截圖 1、2 |
| 3 第 4、5 點 | 小牌 14 不包外框；泡泡驚嘆號、問號近黑 `#16121a` 不包外框、彩色包 1px：T5、截圖 3、4 |
| 3 第 6 點 | 另開兩張表：`QE.BADGE_Q`（小牌）、`QE.BUBBLE`（泡泡）；舊 `ICON` 只留地物營火的 `rest` |
| 3 第 7 點 | 見第 4 節 (c) |
| 3 第 8～10 點 | 卷軸照 `bar_J` 身體＋三道字線 `#5a4a30`；同題材共用；Q 版卷軸只在泡泡 |
| 4 第 1～7 點 | 見第 5 節 (b) |

## 3. 改到的既有測試（舊 → 新）

雜湊／快照：**沒有重產任何快照或 fixture**（`render/__snapshots__/`、`qi3bStatusBaseline.json`、`qi2dBaseline.json` 都沒動；事件卡圖示沒有基準檔）。

`render/storyIconArt.test.ts`（檔頭註明 QI-6；假 ctx 改成可共用紀錄，並以 `setQCanvasFactory` 把 Q 版另建的畫布記進同一份）：
1. 「8 種選項、4＋1 種其他、6 屬性都有，外圈色照樣張」：舊＝`SOLUTION_ART`／`MISC_ART`／`ATTR_ART` 的鍵與 `.ring` → 新＝`QE.list(grp)` 的 id 與 `ringOf(id)`（四個色值不變）。
2. 「每個圖示：深底＋圖示色的圓環，縮到 48 格裡畫墨線（有填色、有描線）」→「深底＋圓環色照現行，圖樣裁在圓環內緣、照原尺寸貼上」：舊斷言 `scale(size/48)`、`stroke()` 次數 > 1 → 新斷言線寬、`arc(…, size/2 − 線寬/2)`、`clip()`、`drawImage(object,…)`、`fill()` > 1（深底、圓環色斷言不變）。
3. 「沒有 DOM 時留同大小的框」：`data-ring` 的期望值由 `SOLUTION_ART[icon].ring` 改 `ringOf(icon)`（值相同）。
4. describe「事件插圖小牌：黑色圖示改淺色，彩色不動」兩項 → 「小牌與泡泡換 Q 版」兩項：舊＝小牌的問號／驚嘆號用 `BADGE_ICON_INK`、泡泡的 `ICON.bang/ask/coin` 顏色 → 新＝小牌在膠囊之後、標題字之前 `drawImage(object,14,13,14,14)`；泡泡的驚嘆號近黑 `#16121a`、9 個的外框寬、`bubble()` 的圖樣位置。
5. 其他（確定性、d20 四項、擲骰兩項、離屏快取、6Q-1 兩項）程式不變；紀錄改成含 Q 版子畫布後照樣通過。

`render/eventArt.test.ts`「同一場景與背景只畫一次」：數 `document.createElement` 次數；小牌、泡泡的 Q 版圖樣另建畫布會被算進去（2 → 6），改成這一項期間 `setQCanvasFactory(fakeCanvasFactory(…))`，期望值仍是 2。

## 4. (a) 指紋；(c) 插圖縮放與整數像素；結束碼；浮動卡；截圖

**(a) 指紋（43 行）**：開發頁 `event-gallery.html?set=hash`（自己的 vite 5316）與樣張 `q-icons-event.html?part=hash`，同一個無頭 Chrome（`--disable-gpu --mute-audio`，自己的 `--user-data-dir`）、同一個 FNV 與行格式：
- 和**材質色換成 `material.ts` 的樣張**（`qIcons.js` 的 `M`、`qIconsWeapons.js` 的 `MAT` 的鋼、鐵、銅換遊戲端色，上手筆記第 20、35 點的做法）比：**43 行全部相同**（28 個圖示每個大小 2 倍／1 倍、d20 六色 64、泡泡 9 個 × 四種底色）。
- 和原樣張比：41 行相同，不同的 2 行是 `combat`（劍的鋼色 `M.steel`）與 `force`（鐵拳 `PW` 的鐵色），原因只有材質色（遊戲端一律用 `material.ts`，QI-1 第 0.0 節第 3 點）。

**(c) 插圖縮放下的整數像素**：
- 小牌、泡泡的圖用「當下的變換」算每單位幾個裝置像素（`QE.ctxRes(ctx)`＝`getTransform()` 的縮放），照那個解析度出圖（`render(…, 14, res)`），`blit` 把左上角貼到整數裝置像素。
- 事件插圖原本是 728×312（×2）的圖片再用 CSS `background-size: 100%` 縮到卡寬（800 寬時約 296px，等於整張重新取樣）。現在 `EventCard` 量插圖實際顯示寬（`getBoundingClientRect`，含外層 CSS 縮放）× `devicePixelRatio`，`eventArtScale` 回傳「每插圖單位幾個裝置像素」＝round(寬 × DPR)／364，`eventArtUrl` 照這個解析度出圖（畫布寬＝顯示的裝置像素寬），所以 CSS 不再縮放、小牌與泡泡的圖對到裝置像素。量到之前先用 2（舊值）；`ResizeObserver` 改寬時重畫；快取上限 48 張。
- 覺醒插圖（`OpeningDialog`，畫布 ×4 再 CSS 縮放）沒改出圖方式，小牌照 `ctxRes`（4）出圖，畫布整張仍會被 CSS 縮放（待決 2）。

**結束碼**：`corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（318 檔、4113 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告）。相關 vitest：`src/render/storyIconArt.test.ts src/render/eventArt.test.ts src/render/eventArtAwakenQ.test.ts src/world src/test src/ui/floatCardRule.test.ts src/render/qIcon` 64 檔 845 項過，另 `qIconEvent.test.ts` 16 項。

**浮動卡（6.5.1）**：自己的 `trpg serve`（8156，存檔在暫存區）、無頭 Chrome（9336），事件卡的 DC 說明卡，1600×900 與 800×600 各一次：100 ms 時 0 張、550 ms 開 1 張 → 沿直線滑進卡片仍開著 → 卡內捲動：內容一次放得下（可捲量 0）→ 點一下釘住（`.float-card.pinned`）→ 滑鼠移開仍在 → Esc 關閉。兩尺寸都過。

**實機資料**：建角走開發模式 `POST /api/world/characters`（帶 `weapon`、`keywords`）；事件卡與判定結果用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch`，把 `/api/world/characters/…` 回應的 `event`／`situation_result` 換成 `dev/storyGallery.tsx` 同款的假資料（程式與後端不動，上手筆記第 46 點的做法）。800×600 實量：事件卡 `.world-event` 寬 339.7、插圖寬 295.7（需求寫 354；量到的差異應是外層縮放，待決 4）。

**截圖**（`docs/art/shots/qi6/`，10 張；開發頁 PNG 裝置像素比 1、最近鄰；實機 jpg 80；單張 ≤ 201 KB）

| 檔 | 對到第 5 節 | 內容 |
|---|---|---|
| `docs/art/shots/qi6/1-dev-sol-misc-attr-true1x-dpr2-x4.png` | 1、2、3 | 選項 8（24）、其他 5（16／14／12，說書人與說明兩個大小）、六屬性（20／18）：每格實際大小＋真 1 倍＋res 2，×4 |
| `docs/art/shots/qi6/2-dev-d20-six-true1x.png` | 4 | d20 六色 × 64（寫 17，×2）／24／20／16（×4），真 1 倍 |
| `docs/art/shots/qi6/3-dev-badge-live-q-art460-354-true1x.png` | 5 | 小牌 8 個「現行｜Q」膠囊底並排；10 張插圖＋覺醒插圖在卡寬 460、354 的左上小牌真 1 倍裁切 ×4 |
| `docs/art/shots/qi6/4-dev-bubble-used-spare-art460-354.png` | 6、7 | 用到的 4 個泡泡「現行｜Q」× res 1、2；備用 6 個 × 四種底色 × res 1、2；四張插圖裡的泡泡在卡寬 460、354 的裁切（res 1、2，最近鄰） |
| `docs/art/shots/qi6/5-dev-art460-bubble-scenes.jpg` | 8 | 伏擊、村民求助、商隊、朋友的足跡四張整張，卡寬 460（小牌與泡泡都是 Q 版） |
| `docs/art/shots/qi6/6-world-1600-event-card.jpg` | 9、5、6 | 實機 1600×900：事件卡（商隊插圖小牌金幣＋白泡泡金幣、線頭 14、說明 14、選項 24、情境判定 d20 24＋DC、屬性 20、說明 14、線索 16、擲骰 d20 16） |
| `docs/art/shots/qi6/7-world-800-event-card.jpg` | 9 | 實機 800×600：同上 |
| `docs/art/shots/qi6/8-world-1600-result.jpg` | 9 | 實機 1600×900：判定結果（模型關閉 14、兩顆 64 骰、屬性 18、d20 20、說明 12、線索 16、說書人 14） |
| `docs/art/shots/qi6/9-world-800-result.jpg` | 9 | 實機 800×600：同上 |
| `docs/art/shots/qi6/10-world-1600-awaken-badge.jpg` | 5 | 實機 1600×900：開場覺醒插圖，左上小牌換 Q 版源晶 |

**實機未看**：小牌劍、問號、營火、驚嘆號、警告、留言與伏擊／求助／足跡三種泡泡（實機只拍了商隊場景，其他在開發頁 3～5 張畫出來）；備用 6 個泡泡（沒有場景用到）；實機 DPR 2（`event-scene@2x` 那張沒拍，開發頁 res 2 代替）。

## 5. (b) 第 4 節的處理、死碼

- 第 1 點（備用 6 個泡泡）：照美術建議一起搬，`QE.BUBBLE` 9 個都有，`bubble()` 收到任何 `IconId` 都畫 Q 版。
- 第 2 點：新畫的在 `qIcon/event.ts`；`ART.event` 四個在 `legacy48.ts`；四個元件 props 不變。
- 第 3 點（覺醒插圖）：一起換成 Q 版源晶（`eventArtAwaken.ts` 呼叫 `drawBadgeIcon(ctx, "portal", 21, 20)`；截圖 3、10）。
- 第 4 點：另開兩張表 `BADGE_Q`、`BUBBLE`；`ICON` 只留地物營火。
- 第 5 點：`QE.bareGlyph(id, px, res)`（回傳畫布；資訊面板段自己決定要不要再包快取或圖片網址）。
- 第 6 點死碼，**刪了**（沒有呼叫處）：`storyIconArt.ts` 的 `SOLUTION_ART`、`MISC_ART`、`ATTR_ART`、`drawD20`、`drawChip`、`glowOn`、`disc`、`shine`、`K`；`eventArtParts.ts` 的 `ICON` 除 `rest` 以外 8 個、`bang`、`BADGE_ICON_INK`、`ink` 參數。`inkStyle.ts` 別處還在用，沒動。
- **留下**：舊小牌與泡泡畫法另存一份在 `client/src/dev/eventLegacy.ts`（只給開發頁並排）；`dev/storyGallery.tsx` 只用 `D20_COLOR`（仍在）與元件，不受影響。
- 第 7 點：開發頁照建議（見第 1 節）。

## 6. 和樣張不同的地方

- 依賴改 import；材質色用 `material.ts`（劍、鐵拳暗一階，見 4 (a)）。
- `canvas(id, px, res, opt)`（樣張 `(id, px, zoom, opt)`）；沒有畫布時 `glyph` 回 null、不貼。
- 沒搬：`live`、`topic`、`D20_ZH`、`GRP_ZH`、`BUBBLE_ZH`、`bubbleGlyph` 的 `noPre`。
- 多了：`bareGlyph`、`ctxRes`、`BADGE_Q`；`drawBadge` 收 `res`（樣張 `(ctx, icon, x, y, s, res)` 的 `s` 沒用到，拿掉）。

## 7. 待 PM 決定

1. **事件插圖改成照顯示寬出圖**（`EventCard` 的 `eventArtScale`＋`ResizeObserver`，需求 3 第 7 點的延伸）：不改的話整張 728 寬圖片會被 CSS 縮到卡寬，小牌與泡泡的 1px 外框照樣糊。代價是視窗改大小時會重畫一次插圖（快取上限 48 張）；插圖左上角若落在小數像素仍有半像素位移。
2. **覺醒插圖的畫布沒改出圖方式**（×4 畫布再 CSS 縮放）：小牌是 Q 版，但會被整張縮放取樣；要清楚得照 1. 的做法改 `OpeningDialog`，範圍超出本段。
3. **指紋要換材質色才全同**：和原樣張比 `combat`、`force` 兩行不同，原因是遊戲端用 `material.ts`（QI-1 0.0 節第 3 點）；美術 PM 看圖時劍刃、鐵拳會比樣張暗一階。
4. **800×600 實量事件卡寬 339.7、插圖寬 295.7**，不是需求寫的 354：本段沒動版面，只記錄實量。
5. **舊小牌／泡泡畫法留在 `dev/eventLegacy.ts`**：只為開發頁「現行｜Q」並排；美術驗收後可刪。
6. **`bareGlyph` 只回傳畫布**：資訊面板段（PNL-1a）若要圖片網址或快取，在那段加。
7. **`storyIconArt.test.ts` 的假 ctx 改成共用紀錄**（Q 版子畫布記進同一份），既有斷言的期望值除第 3 節列的以外都沒改。

## 開發 PM 裁定（2026-11-12，第八任開發 PM）

已驗收並以 --no-ff 合入 main。合併後 typecheck 0、vitest 318 檔 4113 passed、build 0。

1. 事件插圖照顯示寬出圖：保留（快取上限 48 張）。
2. 覺醒插圖仍 ×4 縮放：記入待排，和資訊面板段一起看，美術驗收若要求清楚再單獨排。
3. 材質色差一階（劍刃、鐵拳）：交美術 PM 判斷是改樣張還是改 material.ts；本段不動。
4. 800×600 事件卡寬 339.7／插圖 295.7 與需求 354 不同：只記錄，交美術 PM 看。
5. dev/eventLegacy.ts：美術驗收通過後刪（併入下一個前端段順手做）。
6. bareGlyph 的圖片網址或快取：PNL-1a 再加。
