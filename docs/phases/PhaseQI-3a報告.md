# Phase QI-3a 報告：Q 版狀態圖示｜搬畫法＋開發頁（不接到遊戲畫面）

> 實作者（Opus 5.5），2026-11-12。規格：`docs/phases/PhaseQI-3計畫.md`（QI-3a 部分；第 0.0 節定稿、第 0 節 1～10 點照「建議」）。起點：main `a5825a77`（含 `10423205` QI-2b、`5f68bbcb` QI-3 規格）。未 push。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| A1 框的小模組 | 新 `client/src/render/statusFrame.ts`：`Polarity`、`isPolarity`、`polarityOf`、`framePath`、`FRAME_COLOR`、深底 `STATUS_BASE_BG`（`rgba(12,12,16,0.88)`）從 `statusIcon.ts` 原樣搬出；`statusIcon.ts` re-export（`FRAME_COLOR`、`framePath`、`polarityOf`、`STATUS_BASE_BG`、`Polarity`），`paintStatusIcon` 的深底字面值換成同值常數，其他不動 | `b70440b6` |
| A2 狀態圖樣 | 新 `client/src/render/qIcon/status.ts`：由 `qIconsStatus.js` 逐行搬 `slimArrow`、`pole`、`MEDAL`／`medal`、`CORE`／`core`、`dome`、`EMBLEM`（7）、`ELEMENTS`、`NEW`（43）、`entry`、`CLASS_BG`、`CLASS_ZH`、`BASE_BG`、`FRAME`、`GLYPH_K`、`CARD_FRAME`／`HEAD_FRAME`、`HEAD_TINT`、`def`、`glyph`、`innerPath`、`innerWidth`、`maskOf`、`outsideFrac`、`fitK`（＋`fitKMeasured`、`fitKey`）、`HEAD_MAX`、`tintInset`、`paint`、`headCanvas`、`cardCanvas`、`list(ids)`。極性／類別／名稱讀遊戲端名詞表；不認得的狀態畫名稱第一個字（米白 `#f2e6c8`；null／空字串「?」） | `b70440b6` |
| A3 `fitK` 表 | 新 `client/src/render/qIcon/statusFit.json`（250 筆）：開發頁 `?set=fitgen` 在無頭 Chrome（`--disable-gpu`）量出；`fitK` 先查表、查不到才量、量不到回 1 | `6cc307e6` |
| A4 開發頁 | `client/src/dev/statusGallery.ts`＋`client/dev/status-gallery.html`：`?px=`、`&res=`、`&zoom=`、`&set=all\|ctrl\|debuff\|buff\|shield\|neutral\|stance\|element\|boss\|near\|cls\|unknown\|fitgen\|compare\|none`、`&tint=0`、`&from=&n=`、`&label=0`、`&old=1`、`&scene=0`、`&kind=`、`&sample=`；`window.__qiStatusDev`；標題改成實際數量（118）；下半戰場保留（仍是現行畫法） | `6cc307e6`、`df343a7a` |
| A5 測試 | 新 `client/src/render/qIcon/qIconStatus.test.ts`（T-A1～T-A8，15 項） | `df7484f6` |
| A6 對照與截圖 | 第 4 節；`docs/art/shots/qi3/` 6 張 | `df343a7a` |
| A7 | 本報告、上手筆記 | 本 commit |

**`parts.ts` 加的 export（只加 `export`，畫法沒動）**：`bust`、`heart`、`star4`、`bolt`、`crystal`、`shieldBlue`、`upArrow`、`bladeSword`、`diagSword`、`hexPts`、`stancePlate`（11 個）。`stancePlate`／`hexPts` 和樣張第 4 批 `qIconsParts.js` 84～85 行逐字相同（規格第 0 節第 5 列的停止條件沒有觸發）；其餘 9 個和 `qIconsStatus.js` 裡「原樣抄一份」的字面相同，所以改成 import 同一份（需求 2.3「同一題材一份畫法」）。**`core.ts`、`weapons.ts`、`skills.ts`、`legacy48.ts` 沒改**。

## 2. 驗收逐條

| # | 條件 | 結果 |
|---|---|---|
| 8.1-1 | T-A1～T-A8 | 過：`src/render/qIcon/qIconStatus.test.ts` 15 項。T-A1（118 個 `entry` 都不是 null；沿用 40／借用 4／新畫 74＝手畫 39＋紋章 35；32 個＝`STATUS`；借用 4 個與第④批 32 個的呼叫紀錄和直接呼叫部件相同）；T-A2（9 元素 × 5 級同元素同紀錄、`level` 1～5（聖輝／暗影壹級見待決 5）；54 個姿態與架勢第一筆都是 `hexPts(10.6)` 的六角）；T-A3（7 個類別底色、其他 111 個只填深底、順序 深底→類別底色→框線→`drawImage`，118 × 卡／頭頂 × res 1、2）；T-A4（卡染底 7 個有外框且 dilate 位移＝1 裝置像素、不染底的沒有、圖樣 ≤14px；頭頂染底不包外框、圖樣邊長＝表上 `inset=1/res` 那筆算出、暈眩／沉默／嘲諷走 `HEAD_TINT` 其他 4 個同形；`tint:false` 不染、不內縮、不換形）；T-A5（卡／頭頂／52 × res 1、2 × 增益、減益、中性、染底、不認得：`blit` 左上 × `unitPx×res` 為整數、貼圖寬＝畫布寬；不認得的沒有貼圖、有 `fillText`）；T-A6（118 × 2 框 × 2 res 都在表、值範圍與 0.02 倍數、表 250 筆；查表不呼叫任何畫布方法、表外的鍵回 1）；T-A7（卡 `lineWidth=7.560`、頭頂 `1.500`，和現行 `paintStatusIcon` 相同）；T-A8（不認得 `b`、`?`、`怪`，字色 `#f2e6c8`；怪極性退六角、有類別照染；全部 × 尺寸 × res 畫兩次紀錄相同；沒有畫布時不丟例外） |
| 8.1-1 | T-A9 遊戲畫面不變 | `render/statusIcon.test.ts` 沒改、通過；`git diff --stat a5825a77..HEAD -- client/src client/dev`：新檔 `statusFrame.ts`、`qIcon/status.ts`、`qIcon/statusFit.json`、`qIcon/qIconStatus.test.ts`；改 `dev/statusGallery.ts`、`client/dev/status-gallery.html`、`qIcon/parts.ts`（只有 11 個 `const`→`export const`）、`statusIcon.ts`（A1 的搬移與 re-export，+5／−22）。沒有其他 |
| 8.1-2 | 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`corepack pnpm -C client test` **0**（293 檔、3655 項）；`corepack pnpm -C client build` **0**（只有既有的 chunk 大小警告） |
| 8.1-2 | 快照 | `inkDollSnapshot.test.ts`、`creaturePose.test.ts` 在整包通過；跑完 `git status` 乾淨（快照沒變） |
| 8.1-3 | slow 測試 | `UV_NO_SYNC=1 uv run pytest -q tests/api/test_client_fixtures.py`：4 passed；沒有動 Python、`content/` |
| 8.1-4 | 3a 範圍 | 見 T-A9；`core.ts`、`weapons.ts`、`skills.ts`、`legacy48.ts` 的 diff 為空 |
| 8.1-7 | 截圖 | 6 張 PNG（最近鄰 ×6 特寫），單張 ≤ 237 KB；無頭 Chrome `--force-device-scale-factor=1`、`--mute-audio`、網址 `?mute=1` |
| 8.1-8 | (a)、(c) | 第 4 節；(b) 是 3b |
| — | 相關測試 | `vitest run src/render/qIcon/ src/render/statusIcon.test.ts src/test/importCycles.test.ts`：6 檔 95 項過 |

## 3. 改寫的既有測試、快照

沒有改任何既有測試；快照沒有變動。

## 4. 需求第 5 節末 (a)、(c)、截圖、實機未看

**(a) 和樣張逐像素對照**：自己的 vite（5280）開 `status-gallery.html?set=compare&sample=http://127.0.0.1:8136/`，同一頁從自己的 CORS 靜態伺服器（8136）抓 `qIcons.js`、`qIconsWeapons.js`、`qIconsSkills.js`、`qIconsParts.js`、`qIconsStatus.js` 原始碼，載入前把 `qIcons.js` 的 `M` 換成 `core.ts` 的 `M`、`qIconsWeapons.js` 的 `MAT` 鐵鋼銅換成 `material.ts`（上手第四節第 35 點），`QPARTS_GLOSSARY` 餵同一份 `glossary.json`；兩邊交錯著畫同一個 `cardCanvas`／`headCanvas`、`getImageData` 逐像素比。每組 (px, res) 一頁剛載入的頁面。無頭 Chrome `--disable-gpu`：

| 比對 | 組數 | 0 像素不同 |
|---|---|---|
| 狀態卡 20 × res 1 | 118 | 118 |
| 狀態卡 20 × res 2 | 118 | 118 |
| 頭頂 11 × res 1 | 118 | 118 |
| 頭頂 11 × res 2 | 118 | 118 |
| `tint=0`：20、11 × res 1、2 | 472 | 472 |
| 開發頁 52 × res 2（表外，執行期量） | 118 | 118 |
| `fitK` 表 250 筆 vs 樣張 `QIconsStatus.fitK` | 250 | 250 |

沒有 ±1 雜訊，沒有 `mix` 四捨五入差異。

**GPU 與軟體繪製的差**：一開始用開 GPU 的無頭 Chrome 產表，和美術自查表比有 12 列不同；改用 `--disable-gpu` 量則和自查表 118 列全同。同一台機器兩種繪製量出的 `fitK` 有 14／250 筆不同（差 0.02～0.04，例：緩速頭頂 `inset 1` 0.64 vs 0.60、守護頭頂 0.92 vs 0.90）。**表採 `--disable-gpu` 的值**（理由：美術審過的自查表與真 1 倍樣張都用 `qicons_shots.py` 的 `--disable-gpu` 產；軟體繪製跨機器較穩定）。在開 GPU 的頁面跑同一比對：`fitK` 236／250 相同、頭頂 11 res 2 有 3 個（隱蔽、連心、硬殼）、res 1 有 4 個（隱蔽、緩速、加速、硬殼）不同——都是樣張即時量出不同的 `fitK`，不是搬錯（待決 1）。

**(c) `fitK` 和自查表**：`uv run python docs/art/sample/tools/qicons_shots.py --audit status` 結果「共 118 個狀態，不過 0 個；沿用第 4 批 40、借用 4、新畫 74」；表上「縮放 卡／頭頂」欄（頭頂取 `res 1` 的 `inset`）和 `statusFit.json` 的 `id|16.80|0.00` 與頭頂那筆逐列比對：118 列 0 差異。

**`fitK` 表產法與筆數**：`status-gallery.html?mute=1&set=fitgen&scene=0` 在 `--disable-gpu` 無頭 Chrome 開，讀 `document.body.dataset.fit` 存成 `statusFit.json`（檔內 `_note` 寫明，不手改）。鍵 `id|框邊長 toFixed(2)|inset toFixed(2)`：118 × {16.80, 9.00} × inset 0（含 `tint=0` 對照）＝236，加上頭頂染底 7 個 × {0.50, 1.00}＝14，共 250。

**截圖**（`docs/art/shots/qi3/`，全部 PNG、最近鄰 ×6、裝置像素比 1；每格左＝真 1 倍、右＝DPR 2）

| 檔 | 對到 8.2 | 內容 |
|---|---|---|
| `docs/art/shots/qi3/3a-01-card20-true1x-dpr2-a.png` | 第 1 項 | 狀態卡 20，名詞表第 1～60 個，真 1 倍｜DPR 2 |
| `docs/art/shots/qi3/3a-02-card20-true1x-dpr2-b.png` | 第 1 項 | 同上第 61～118 個 |
| `docs/art/shots/qi3/3a-03-head11-true1x-dpr2-a.png` | 第 2 項 | 頭頂 11，第 1～60 個，真 1 倍｜DPR 2 |
| `docs/art/shots/qi3/3a-04-head11-true1x-dpr2-b.png` | 第 2 項 | 同上第 61～118 個 |
| `docs/art/shots/qi3/3a-05-cls-unknown-20-11.png` | 第 3、8 項 | 控制類 7 個（染底）＋`tint=0` 對照；不認得的 brand_new_status、空字串、增益／減益／中性／硬控假狀態——每格 20 真 1 倍、20 DPR 2、11 真 1 倍、11 DPR 2 |
| `docs/art/shots/qi3/3a-06-near-20-11-true1x.png` | 第 4 項 | 撞圖組：暖色四六角、冷色四六角、岩石／殼／甲七個、晶能兩個——20、11 真 1 倍 |

**實機未看**：本段不接遊戲畫面，全部用開發頁畫（第 5～7 項是 3b）。

## 5. 和樣張不同的地方、長函式

- 依賴改 import（`STATUS`／`entry`／`BOX` 與 11 個共用零件從 `parts.ts`、`ACT` 從 `skills.ts`、`ART.hud.move`／`drop` 從 `legacy48.ts`、小工具從 `core.ts`）；框用 `statusFrame.ts`（和現行同一份）。
- 名詞表：用遊戲端 `statusLook`／`statusName`／`polarityOf`；`list()` 改成 `list(ids)`（呼叫端給清單）。
- 不認得的狀態：畫名稱第一個字（需求 2.4 第 4 列），不走樣張 `def()` 的第④批退回。
- `fitK`：查表 → `fitKMeasured`（樣張原式）→ 量不到回 1。
- 型別：`ln(…, "butt")` 照傳（`BUTT` 常數轉型）；`NEW` 加型別註記，鎖霧大陣用 `NEW["array_ward"]!`；查表處加 `!`／`as`；`ACT.mark.def`、`ACT.summon.def` 照傳（`as Tint`）。值都沒改。
- 沒有畫布時：`glyph` 回 null、`paint` 只畫框、`headCanvas`／`cardCanvas` 回 null。
- 超過 80 行的函式：**沒有**（樣張是單行長函式，照搬）。

## 6. 待 PM 決定

1. **`fitK` 表用軟體繪製（`--disable-gpu`）的量測值**：和美術自查表一致；GPU 繪製量出的 14／250 筆差 0.02～0.04。遊戲端一律查表，所以玩家的瀏覽器不會再量（第 4 節）。若要改用 GPU 的值請告知（重跑 `?set=fitgen` 即可）。
2. **`parts.ts` 多匯出 9 個零件**（規格只點名 `stancePlate`、`hexPts`）：`bust`、`heart`、`star4`、`bolt`、`crystal`、`shieldBlue`、`upArrow`、`bladeSword`、`diagSword`，因為樣張狀態檔是「原樣抄一份」，改成呼叫同一份符合需求 2.3。畫法沒動、逐像素比對 0 差異。
3. **`statusFit.json` 多存了 `tint=0` 的 7 筆頭頂鍵**（只開發頁對照用；遊戲不會用到），讓開發頁對照不需即時量。
4. **開發頁 `px` 不是 20 時一律用頭頂構圖**（框 px−2；`&kind=card` 可強制）；52 的 `fitK` 不在表上，在瀏覽器即時量（和樣張逐像素相同）。
5. **聖輝、暗影架勢壹級的 `entry().level` 是 undefined**（`entry` 先查第④批 `STATUS`，和樣張相同）。3b 的角落級數照規格用 ID 樣式判斷，不受影響；上手筆記第四節第 38 點已記。
6. **開發頁的假狀態**（`dev_fake_buff` 等 4 個）只在開發頁加進名詞表，畫「不認得」用；名稱「祝福（假）」等是開發頁自擬。
7. **截圖 6 張**（規格估 6～7）：第 8 項（不認得）併進第 3 項那張；沒有另拍 52 總覽。
8. **截圖放 `docs/art/shots/qi3/`**：派工說不改 `docs/art/` 既有檔，這裡只新增 6 張。
9. **樣張端 `tools/qStatusLive.js` 本段不重產**（第 0 節第 10 列）：請美術 PM 需要時照紀錄第 8 節重產。
10. **`statusTile` 空檔**（第 0 節第 7 列；0.0 已併進 3b）：3b 報告再提。

## 7. 上手筆記更新

`docs/dev/上手-前端戰鬥畫面與動畫.md`：檔頭 QI-3 狀態改成「3a 已做、未接畫面」；第一節表加 `qIcon/status.ts`、`statusFit.json`、`statusFrame.ts` 一列；開發入口表加 `status-gallery.html` 的參數；第四節加第 37 點（`fitK` 隨 GPU／軟體繪製不同，表與比對都用 `--disable-gpu`）、第 38 點（聖輝／暗影壹級沒有 `level`）；第五節測試表加「狀態圖示 Q 版畫法」一列。

## 8. 請使用者重開伺服器檢查的重點

本段**遊戲畫面完全不變**、沒有改內容與 API，不用重開。要看圖：自己的 vite 開 `/dev/status-gallery.html?mute=1&px=20,11&res=1,2&zoom=6&set=cls`（參數見 `dev/statusGallery.ts` 檔頭）。
