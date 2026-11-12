# Phase QI-3 計畫：Q 版小圖示移植第 3 段（⑤狀態圖示：狀態框裡的圖、控制類框底色、角落級數）

> 草稿（開發 PM 助手 2026-11-12，依據本機 main `e1c24f8d`）。開發 PM 確認第 0 節「待開發 PM 確認」後再定稿、push、派工。
> 美術依據：`docs/art/Q版小圖示-狀態移植需求.md`（以下簡稱「需求」，引用寫「需求 x.y」）；樣張以 `5b838d65` 之後的 `docs/art/sample/qIconsStatus.js` 為準（依賴第 4 批 `10b1040f`、真 1 倍修正 `0caaa84f`）；紀錄 `docs/art/Q版小圖示-第5批狀態.md`（以下簡稱「紀錄」）第 7、8 節；審查 `docs/art/Q版小圖示-第5批狀態-審查.md` 末段「第 2 版複審」（通過、沒有必修）。
> 前一段：`docs/phases/PhaseQI-1計畫.md` 第 0.0 節（畫布＝顯示尺寸 × 固定 2、材質色用 `material.ts`、截圖規則）照樣適用；`docs/phases/PhaseQI-2計畫.md`（D6：③④先、共用圖樣畫法建在 `client/src/render/qIcon/`，32 種狀態圖樣做成可呼叫的表 `STATUS`）。
> **切兩段**：QI-3a 搬畫法＋開發頁（新檔、不接到遊戲畫面）→ QI-3b 接線（換掉 `paintStatusIcon` 的畫法、角落級數、實機截圖）。理由與前置見第 4 節。

## 0.0 開發 PM 定稿（2026-11-12，已回美術 PM）

- **③④先、⑤沿用 `qIcon/`**（需求第 4 節第 1 點）：狀態沿用的 40 個、借用的 4 個、新畫用到的零件，一律 import QI-2b 已搬的 `qIcon/parts.ts`（`STATUS`、`entry`、`BOX`）、`qIcon/skills.ts`（`ACT`）、`qIcon/legacy48.ts`（`ART.status`、`ART.hud.move`、`drop`）、`qIcon/core.ts`（`render`、`halo`、`blit`、`ICON_RES`、`outlinePx`、`blank`…），**不重搬、不另畫**。
- **不改 `qIcon/core.ts`、`qIcon/weapons.ts`**；需要時只加 `export`（列進報告）。QI-2b 的 `parts.ts`、`skills.ts`、`legacy48.ts` 同樣只加 `export`，不改畫法。
- **元素架勢的級數要顯示**：狀態卡 20 的角落數字顯示級數（需求第 4 節第 2 點選 (a)）。
- **晶能湧動／晶能狂湧用角落數字 1／2 區分**（需求第 4 節第 6 點）。
- **舊存檔不必相容**（使用者原話：「存檔都可以刪除」）。本段本來就不動存檔與後端；若實作中發現要碰存檔格式，照最簡單的做、不寫轉換。
- **每段合併前跑與改動相關的 slow 測試**；快照／雜湊**不得整批重產**，每項變動要證明來自本段（拿掉本段改動回到舊值）。
- **截圖**：每段 ≤ 10 張；jpg 品質 80；真 1 倍／最近鄰放大特寫可用 PNG，單張 ≤ 300 KB（同 QI-2 D7）。
- 其餘技術點見第 0 節（開發 PM 確認前照「建議」欄做）。

## 0. 待開發 PM 確認

「建議」是規格目前寫進去的做法（最保守）；確認後改掉對應列或移進 0.0。

| # | 問題 | 出處 | 建議（暫採） |
|---|---|---|---|
| 1 | **`fitK`（圖樣收進框內緣的縮放）執行期量，還是建置時算成表** | 需求 2.4 第 9 列、第 4 節第 4 點；樣張 `qIconsStatus.js` 187–195 行（6 倍遮罩＋`getImageData`，從 1 往下每次 0.02） | **表＋執行期退回**：3a 把樣張的 `innerPath`／`maskOf`／`outsideFrac`／`fitK` 逐行搬成 TS（執行期版），在開發頁用真瀏覽器跑出「名詞表 118 個 × 框 16.8／9 × `res` 1／2（`inset` 只有頭頂染底的 7 個隨 `res` 變）」的表，存成 `qIcon/statusFit.json`（或 `.ts`，檔頭寫「由開發頁 `?set=fitgen` 產生，不手改」）。遊戲端先查表、查不到（開發頁 52 等非標準尺寸、之後新狀態）才執行期量；量不到（沒有 `getImageData`，例 vitest 假畫布）退回 1。理由：遊戲路徑不呼叫 `getImageData`、結果確定、vitest 測得到；表和樣張 `fitK` 逐筆相同由瀏覽器比對證明（第 7 節） |
| 2 | **`paintStatusIcon` 怎麼拿到 `unitPx`、`res`** | 需求 2.2 第 3 點（「簽名不變」）對 2.4 第 6 列（要 `unitPx`／`res`）；`skillIcon.ts` 369 行 `AssemblyTile.draw: (ctx) => …` | **加兩個選填尾參數**：`paintStatusIcon(ctx, id, cx, cy, size, unitPx = 1, res = ICON_RES)`（舊呼叫照樣成立）；`AssemblyTile.draw` 加選填第二參數 `info?: { px: number; res: number }`，由 `tileCanvas` 傳入，其他部件不用改；`statusIconTile` 用 `info.px / 100` 與 `info.res`。不用 `ctx.getTransform()` 反推（假畫布回單位矩陣，測不到） |
| 3 | **頭頂圖示在實際螢幕尺寸會被 Pixi 重新取樣**（地圖縮放 × `minMark` 反向放大），抵銷整數像素對齊與 1 裝置像素底色圈 | 需求第 4 節第 3 點；`render/unitSprite.ts` 919–928、1099–1112 行（`Sprite` 寬高設 `ROW_ICON_FEET` 11）；`render/minMark.ts` | **接受、不改出圖**：3b 在 1600 與 800 寬實機量頭頂圖示的螢幕 px（寫進報告），附放大截圖給美術看底色圈；「照實際尺寸出圖」若美術要，另排一段（會動 Pixi 貼圖與快取，風險大） |
| 4 | **角落級數的寫法與優先順序** | 需求第 4 節第 2、6 點；`ui/statusCard.ts` 177–181 行 `statusCorner()`（`remaining` → `amount` → 空）；元素架勢、晶能湧動／狂湧在 `content/statuses.yaml` 都是 `expires: never` | **阿拉伯數字 `1`～`5`，級數優先於回合數與數值**（美術建議級數優先）。判斷：元素架勢照 ID 樣式 `^stance_(physical\|fire\|ice\|lightning\|poison\|wind\|earth\|holy\|shadow)_([1-5])$`（和樣張 `entry` 同一個規則）；晶能湧動／狂湧用 `ui/statusCard.ts` 裡一張兩筆的小表 `{ crystal_surge: 1, crystal_surge_2: 2 }`（前端名單，比照 `CREATURE_CHARGE_SKILLS`；後端不動，需求 3.3 第 14 點）。vitest 斷言這些 ID 在名詞表快照裡都存在（改名會擋）。用壹～伍要另調角落字型，不採 |
| 5 | **姿態臂章 `stancePlate`／`hexPts` 的共用**：樣張 `qIconsStatus.js` 23–25 行把第 4 批的 `hexPts`、`stancePlate`「原樣」再寫一份；但需求 2.3 要求「同一個題材只有一份畫法」。QI-2b 的 `parts.ts` 目前沒有匯出這兩個 | 需求 2.3 (a)(b)、3.3 第 12 點；`git show worktree-agent-a734462686bcdc403:client/src/render/qIcon/parts.ts` 的 export 清單 | **在 `parts.ts` 只加 `export`**，`status.ts` import 使用，不再寫一份；若 QI-2b 合併後的實作和樣張第 4 批的 `stancePlate` 不同（參數或座標），停下回報，不自己改 |
| 6 | **`glyphColor`、`CTRL_COLOR`、`OWN_COLOR`、`POL_COLOR`、`GLYPH`、`drawGlyph` 怎麼處理** | 需求 3.3 第 9、11 點；`skillParts.ts` 208–228 行（部件圓片 `statusTile` 用 `glyphColor`／`GLYPH`／`drawGlyph`）、`qSummon.ts` 103 行（`drawGlyph`）、`qSummonSpirit.test.ts`（`GLYPH`） | **全部保留、值不改**（部件圓片與召喚物頭頂還在用，見第 0 節第 7 列）；新增 `CLASS_BG`（放 `status.ts`）。`paintStatusIcon` 不再呼叫 `glyphColor`／`drawGlyph`。`statusIcon.test.ts` 裡 `glyphColor` 的斷言**保留**（改放進「部件圓片用的顏色」那一組，比需求說的「改成驗框底色」更嚴），另外新增框底色的斷言；報告寫哪些已不被 `paintStatusIcon` 用、還留給誰 |
| 7 | **`statusTile`（部件圓片 24／工坊選項；戰場頭頂的定時炸彈、蓄力徽章裡的圖）落在兩份規格之間**：需求 1.2 說它屬第③＋④批；`PhaseQI-2計畫.md` 0.0 第 2 點說「`statusTile`、`statusIconTile` 不動（第⑤批再換）」、T-C6 鎖它的畫面不變 | 需求 1.2、第 7 節第 1 點；QI-2 0.0、T-C6；`unitSprite.ts` 144 行、`skillIcon.ts` 471、583 行 | **本段不換 `statusTile`**（照需求 1.2 的範圍），QI-2c 的 T-C6 裡 `statusTile` 那一半保持不變；報告列為空檔，請開發 PM 問美術要不要排一個小段（換成 `parts.ts` 的 `STATUS` 圓片，32 種以外怎麼畫要美術定） |
| 8 | **快取鍵加 `res`** | 需求 2.4 第 10 列；`statusIcon.ts` 687 行 `statusIconKey`、`skillIcon.ts` 508 行 `tileKey` | **兩個都加**：`statusIconCanvas(id, size, res = ICON_RES)`、`statusIconKey(id, size, res)`；`tileCanvas(tile, px, res = ICON_RES)`、`tileKey(t, px, res)`。遊戲固定 2，開發頁可給 1。`fontEpoch` 照舊 |
| 9 | **開發頁**：擴充現有 `client/dev/status-gallery.html`（`src/dev/statusGallery.ts`），還是另開一頁 | 需求 1.3 末列、第 5 節前言、第 7 節第 2 點 | **擴充現有頁**：上半的 52px 總表改成依參數畫；下半的 `BattleRenderer` 戰場保留（`&scene=0` 可關）；標題「32 個狀態」順手改成實際數量 |
| 10 | 樣張端的 `tools/qStatusLive.js`（「現行」欄的打包）移植後要不要重產 | 需求 3.3 第 15 點；紀錄第 8 節末條 | **本段不重產**（樣張端、美術的檔，不影響驗收）；報告提醒美術 PM 需要時照紀錄第 8 節的做法重產 |

## 1. PM 決定

| # | 決定 | 出處 |
|---|---|---|
| D1 | 順序：③④（QI-2）先於⑤；⑤沿用 `qIcon/` 已搬的部件，不重搬（同一題材一份畫法） | 開發 PM 2026-11-12；需求第 4 節第 1 點；QI-2 D6 |
| D2 | 元素架勢級數顯示在狀態卡角落 | 開發 PM 2026-11-12；需求第 4 節第 2 點 |
| D3 | 晶能湧動／狂湧角落顯示 1／2 | 開發 PM 2026-11-12；需求第 4 節第 6 點 |
| D4 | 截圖：每段 ≤ 10 張；真 1 倍／最近鄰特寫可 PNG ≤ 300 KB，其他 jpg 80 | 開發 PM 2026-11-12；`docs/開發PM交接.md` 6.5.2 |
| D5 | 類別底色定案：`hard #d4ac20`、`movement #2f78c8`、`mental #8a4ccc`，不透明，疊在現行深底上；只看 `control_group` 欄位（纏繞不染） | 需求 3.1 第 1、2 點（美術 PM 定案） |
| D6 | 染底的框分兩級：框邊長 ≥ 12 CSS px（狀態卡 16.8）圖樣包 1 裝置像素外框 `#16121a`；< 12（頭頂 9）不包外框、`fitK` 內縮 1 裝置像素、暈眩／沉默／嘲諷改用 `HEAD_TINT` 的形 | 需求 3.2 第 5、6 點（美術 PM 定） |

## 2. 目標與範圍外

**目標**：名詞表全部 **118 個**狀態（`content/statuses.yaml`；遊戲端不寫死清單）的狀態框裡改畫 Q 版圖樣（沿用第④批 40、借用 4、新畫 74：手畫 39＋元素架勢 7 種紋章 × 5 級），控制類 7 個的框填類別底色；框形、框色、框線寬、深底、排序與排版、身上特效**都不動**（需求 1.2）。兩個顯示處：狀態卡 20（`StatusBadge` → `statusIconTile`，框 16.8）、戰場頭頂 11（`statusIconCanvas`，框 9）。狀態卡角落加元素架勢級數與晶能 1／2（D2、D3）。**3a 只建新檔與開發頁、遊戲畫面不變；3b 一次接上**。

**範圍外**：`statusTile`（部件圓片、工坊選項、頭頂定時炸彈／蓄力徽章裡的圖，第 0 節第 7 列）；`qSummon.ts` 召喚物頭頂的元素小圖（⑤b）；靈魂連結與第④批效果「分擔傷害」統一（第④批的可修，需求第 6 節）；需求第 6 節「仍像別的東西」「頭頂 11 認不出題材」各點（可接受、不改）；後端與 API（需求 3.3 第 14 點：不動）；頭頂照螢幕實際尺寸出圖（第 0 節第 3 列）；刪舊畫法（第 0 節第 6 列）；樣張端 `qStatusLive.js`（第 0 節第 10 列）；`qIcon/core.ts`、`weapons.ts` 的畫法。

## 3. 工作環境

- Windows、Git Bash。前端 `corepack pnpm -C client …`；Python（只有跑樣張自查時）一律 `uv run python`。
- 新 worktree 第一次：`uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`；之後 Python 指令加 `UV_NO_SYNC=1`。
- 預覽埠（不用 8000、8001、5195）：QI-3a vite 5280～5284、靜態伺服器（載樣張比對）8136～8137；QI-3b vite 5285～5289、`trpg serve` 8138～8140。vite 的 `/api` 寫死轉 8000，要接自己的 `trpg serve` 另寫暫存設定檔、用完刪掉，不改 `vite.config.ts`（上手-前端第四節第 13 點）。
- 瀏覽器網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`，截圖用 `--force-device-scale-factor=1`。
- 結束前用自己記下的 PID 關掉 vite、`trpg serve`、靜態伺服器與無頭 Chrome，確認沒有殘留；不用 `taskkill /IM`、`pkill`。
- 等背景程序用完成通知，不寫 `until`／`while` 輪詢迴圈。
- agent 與子 agent 一律指定 Opus 5.5（Agent 工具 `model: "opus"`），prompt 寫明往下也一樣。
- 只跑相關測試（第 9 節）；不跑 `scripts/check.py`、不跑模擬。不要 push。每完成一個交付項目就 commit（第一行英文，例 `feat(qi3a): port Q status icon art to TS`），結尾帶 Co-Authored-By。
- 要讀的：`CLAUDE.md`；需求全文；`docs/dev/上手-前端戰鬥畫面與動畫.md`（全文）；`docs/art/上手-畫法.md` 2.1、2.5、2.8、2.9；紀錄第 1、2、8 節；`docs/phases/PhaseQI-2b報告.md`（`parts.ts`、`legacy48.ts` 的搬法與和樣張不同處）；3b 另讀 `PhaseQI-2c報告.md`（`tileCanvas` 改了什麼、T-C6）。

## 4. 切段

| 段 | 內容 | 改的檔（主要） | 前置 |
|---|---|---|---|
| **QI-3a** 搬畫法＋開發頁 | `qIconsStatus.js` 逐行搬成 TS；框的小模組（從 `statusIcon.ts` 原樣搬出）；`fitK` 執行期版＋產表；開發頁參數；和樣張逐像素對照；驗收第 1～4、8 項截圖 | 新 `client/src/render/qIcon/status.ts`、新 `qIcon/statusFit.json`（或 `.ts`）、新 `client/src/render/statusFrame.ts`（檔名可調）、`render/statusIcon.ts`（**只把** `Polarity`、`polarityOf`、`framePath`、`FRAME_COLOR`、深底色搬到新模組並 re-export，行為不變）、`qIcon/parts.ts`（只加 export，第 0 節第 5 列）、`dev/statusGallery.ts`、`client/dev/status-gallery.html`、新測試檔 | **QI-2b 合併後才派**（要 import `parts.ts`、`skills.ts`、`legacy48.ts`）。和 QI-2c 平行時：3a 不碰 `skillIcon.ts`、`skillParts.ts`、`unitSprite.ts`、`ui/`；`statusIcon.ts` 的搬移若 QI-2c 也改到同檔，3a 排在 2c 之後 |
| **QI-3b** 接線 | `paintStatusIcon` 換 Q 版（深底 → 類別底色 → 框線 → `blit` 圖樣）；`statusIconCanvas`／`statusIconTile`／`tileCanvas` 傳 `unitPx`、`res`；快取鍵加 `res`；角落級數；既有測試改寫；實機截圖；`__layoutSmoke` | `render/statusIcon.ts`、`render/skillIcon.ts`（`statusIconTile`、`tileCanvas`、`tileKey`、`AssemblyTile`）、`render/unitSprite.ts`（`rowIconTexture` 的鍵只跟著 `statusIconKey` 走，排版不動）、`ui/statusCard.ts`（`statusCorner`）、`dev/statusGallery.ts`（實際組裝）、既有測試改寫 | **QI-2c 與 QI-3a 都合併後才派**（2c 改 `tileCanvas` 的貼圖對齊與 T-C6；3b 要改同一個函式與那條測試） |

理由：① 樣張 `qIconsStatus.js` 38.5 KB（118 個圖樣＋`fitK` 量測＋框流程），逐行搬、產表、加開發頁參數、和樣張逐像素比對（118 × 2 種框 × 2 種 `res`）與 7 張特寫，已接近一段上限。② 接線要改 `paintStatusIcon`、`tileCanvas` 介面、角落數字、改寫 `statusIcon.test.ts` 多條與 QI-2c 的 T-C6、實機兩種寬度截圖與 `__layoutSmoke`，和搬畫法放一起會超過 25 萬 token。③ 「搬畫法／接線」這樣切，3a 合併後遊戲畫面完全不變，不需要旗標；3a 可以在 QI-2c 進行時先做（檔案不重疊）。若 3a 超量，可在 `status.ts` 與對照做完時交件，開發頁截圖併進 3b。

## 5. 受影響的既有功能

| 區塊 | 受影響的 | 改／不改 | 理由 |
|---|---|---|---|
| 後端、內容、API、存檔 | 無：不加欄位（級數從 `status_id` 末碼讀，晶能用前端兩筆小表） | 不改 | 需求 3.3 第 14 點；舊存檔不必相容（0.0），本段也用不到 |
| 狀態圖示框 | `framePath`、`FRAME_COLOR`、框線寬、深底：3a 只搬位置（re-export，值與行為逐字相同）；3b 照樣張 `paint()` 的流程畫，框線寬改成「以 CSS px 算再除 `unitPx`」（20、11 兩種尺寸算出來和現行相同，需求 2.4 第 5 列） | 搬位置（3a）、流程改（3b） | 需求 1.2、3.1 |
| 狀態框裡的圖 | `paintStatusIcon`：`glyphColor`＋`drawGlyph` 線條圖 → Q 版圖樣（自帶本色）＋控制類框底色 | 改（3b） | 需求 1.1 |
| 不認得的狀態 | 照遊戲端畫名稱第一個字，字色改米白 `#f2e6c8`、底照類別規則 | 改（3b） | 需求 2.4 第 4 列 |
| 狀態卡 `StatusBadge`（`Hud.tsx`、`UnitInfo.tsx`） | 元件不改；`statusIconTile` 的畫法與 `tileCanvas` 傳參；角落 `statusCorner` 加級數 | 改（3b） | 需求 1.3；D2、D3 |
| 戰場頭頂狀態列 | `rowIconTexture` → `statusIconCanvas(id, 11)`：圖換掉；`ROW_MAX_ICONS`（2）、「+N」膠囊、`statusRowLayout`、`minMark` 倍率、排序 `statusRank` 都不動 | 只換圖（3b） | 需求 1.2、3.3 第 10 點 |
| 身上特效 | `bodyEffects`、`bodyUnder`、`bodyOver` | 不改 | 需求 1.2 |
| 部件圓片 `statusTile`、召喚物頭頂 `drawGlyph` | 仍用 `GLYPH`／`drawGlyph`／`glyphColor` | 不改 | 第 0 節第 6、7 列 |
| `tileCanvas`／`AssemblyTile` | `draw` 多一個選填 `info`、鍵加 `res`；其他部件的畫面不變 | 改介面（3b） | 第 0 節第 2、8 列；QI-2c T-C6 的 `statusTile` 那一半照舊鎖住 |
| 字型重畫 | `fontLoad.ts` 清 `clearStatusIconCache`：保留（「第一個字」還用字型）；新的 `fitK` 快取不靠字型 | 不改 | 需求 2.4 第 10 列 |
| 開發頁 | `status-gallery.html` 加參數（第 6 節 A4） | 改（3a、3b） | 需求第 5 節前言 |
| 排版煙霧檢查 | 若 QI-2c 已把 `TileCanvas` 的 canvas 納入 `icons()`，狀態卡的 canvas 一起量；否則 3b 加上（畫布＝顯示 × 2、顯示寬高整數） | 視 2c 結果（3b） | QI-1b `iconScaleIssues` |
| 快照 | `render/__snapshots__/`（`creaturePose`、`inkDollSnapshot`）與狀態圖示無關，預期不變 | 不改 | 有變就停下回報 |

## 6. 交付項目

### QI-3a 搬畫法＋開發頁（不接到遊戲畫面）

- **A1 框的小模組**：新 `render/statusFrame.ts`（檔名可調）：把 `statusIcon.ts` 的 `Polarity`、`isPolarity`、`polarityOf`、`framePath`、`FRAME_COLOR` 與深底色常數 `rgba(12,12,16,0.88)` **原樣搬過去**，`statusIcon.ts` re-export（既有 import 不用改）。目的：`qIcon/status.ts` 要用狀態的框，又不能 import `statusIcon.ts`（3b 起 `statusIcon.ts` 要 import `status.ts`，會循環；`importCycles.test.ts` 會擋）。注意：`qIcon/skills.ts` re-export 的 `framePath` 是 `skillGlyphs.ts` 的技能框，**不是**這個。
- **A2 狀態圖樣**：新 `client/src/render/qIcon/status.ts`，由 `qIconsStatus.js`（`5b838d65` 之後）逐行搬：共用零件（`shieldBlue`、`bladeSword`、`bolt`、`crystal`、`upArrow`、`slimArrow`、`bust`、`heart`、`star4`、`pole`、`medal`、`core`、`dome`… 實際用到的）、`NEW`、`EMBLEM`、`ELEMENTS`、`HEAD_TINT`、`CLASS_BG`、`BASE_BG`、`FRAME`、`GLYPH_K`（0.74）、`HEAD_MAX`（12）、`CARD_FRAME`（16.8）、`HEAD_FRAME`（9）、`entry(id)`、`def(id, cpx, head)`、`glyph(id, cpx, res, { ow, head })`、`innerPath`、`innerWidth`、`outsideFrac`、`fitK`、`tintInset`、`paint(ctx, id, cx, cy, size, unitPx, res, { tint })`、`headCanvas`、`cardCanvas`（開發頁與比對用）。
  - 依賴照 0.0：第④批 `STATUS`／`entry("effect", "reveal"|"delayed_damage"|"cheat_death")`／`BOX` 從 `parts.ts`；`ACT.shield`／`summon`／`mark` 從 `skills.ts`；`ART.status`、`ART.hud.move`、`drop` 從 `legacy48.ts`；`render`、`halo`、`blit`、`outlinePx`、`blank`、`H` 的小工具從 `core.ts`。`hexPts`、`stancePlate` 從 `parts.ts`（只加 export，第 0 節第 5 列）。
  - 極性、類別、名稱一律讀遊戲端名詞表（`battle/glossary.ts` 的 `statusLook`／`statusName`、A1 的 `polarityOf`），不搬樣張的 `G()`／`lookOf`／`polOf`／`clsOf`（需求 2.2 第 2 點）。
  - 不認得的狀態（`entry` 回空）：`paint` 畫名稱第一個字（`fillText`，字型同現行 `bold 13px ${FONT}` 換算、字色 `#f2e6c8`），底照類別規則（需求 2.4 第 4 列）；`null`／空字串畫「?」。不丟例外。
  - 貼圖一律 `core.ts` 的 `blit`，最後一個參數＝`unitPx × res`（需求 3.2 第 8 點）；沒有畫布時 `glyph` 回 `null`、不貼。
  - `res` 預設 `ICON_RES`，不另寫 `DPR = 2`。
- **A3 `fitK` 表**：照第 0 節第 1 列：執行期版逐行搬（`maskOf` 用 `blank()` 建畫布、`Path2D`）；開發頁 `?set=fitgen` 在瀏覽器跑出表（鍵 `id|框邊長 toFixed(2)|inset toFixed(2)`，涵蓋名詞表全部 × {16.8, 9} × `res` {1, 2} 會用到的 `inset`），存 `qIcon/statusFit.json`（檔頭或旁邊 README 註明產法，不手改）；`fitK` 先查表、查不到才量、量不到回 1。
- **A4 開發頁**：擴充 `dev/statusGallery.ts`＋`client/dev/status-gallery.html`：`?px=`（20＝狀態卡構圖、11＝頭頂構圖、52＝原總表）、`&res=1|2`（1＝真 1 倍）、`&zoom=<k>`（最近鄰放大，`image-rendering: pixelated`）、`&set=all|ctrl|debuff|buff|shield|neutral|stance|element|boss|near|cls|unknown|fitgen|compare`（對到第 8.2 節；`near`＝需求第 5 節第 4 項的撞圖組、`cls`＝控制類 7 個＋`tint=0` 對照列、`unknown`＝`brand_new_status`、空字串與增益／減益／中性／有類別的假狀態各一）、`&tint=0`（不染底）、`&from=&n=`（分張）、`&label=0`、`&scene=0`（關掉下半的戰場）；掛 `window.__qiStatusDev`（`paint`、`fitTable()`、`fitK`，像素比對與產表用）。檔頭寫參數說明；標題「32 個狀態」改實際數量。3a 的開發頁直接呼叫 `status.ts` 的 `headCanvas`／`cardCanvas`（3b 改成走遊戲端 `statusIconCanvas`／`statusIconTile`＋`tileCanvas`）。
- **A5 測試**：第 7 節 T-A1～T-A9。
- **A6 和樣張逐像素對照**（第 7 節末段）與截圖（第 8.2 節）。
- **A7 報告與上手筆記**（第 10 節）。

### QI-3b 接線

- **B1 `paintStatusIcon`**：`render/statusIcon.ts` 的 `paintStatusIcon(ctx, id, cx, cy, size, unitPx = 1, res = ICON_RES)` 改呼叫 `status.ts` 的 `paint`（流程：框 → 深底 → 類別底色 → 框線 → `blit` 圖樣；需求 2.2 第 3 點、3.3 第 9 點）。`glyphColor` 等保留（第 0 節第 6 列）。檔頭註解（「圖樣顏色由 `control_group` → …」）照新畫法改寫。
- **B2 頭頂**：`statusIconCanvas(id, size, res = ICON_RES)`：畫布 `round(size × res)`、`ctx.scale(res, res)`、`paintStatusIcon(ctx, id, size/2, size/2, size − 2, 1, res)`；`statusIconKey` 加 `res`（`unitSprite.rowIconTexture` 的鍵跟著變，其餘不動）。
- **B3 狀態卡**：`AssemblyTile.draw` 加選填 `info`；`tileCanvas(tile, px, res = ICON_RES)` 傳 `{ px, res }`、`tileKey` 加 `res`；`statusIconTile(id)` 的 `draw` 用 `paintStatusIcon(ctx, id, 50, 50, 84, info.px / 100, info.res)`（沒有 `info` 時退 `px = 20`、`res = ICON_RES`，並在註解寫明）。半徑 49 的圓形裁切與 QI-2c 的整數像素貼圖照 2c 的實作。
- **B4 角落級數**：`ui/statusCard.ts` 的 `statusCorner(s)` 照第 0 節第 4 列：元素架勢 → 級數；晶能湧動／狂湧 → 1／2；其餘照現行（`remaining` → `amount` → 空）。`StatusCardParts.tsx` 不改。
- **B5 開發頁**：`status-gallery.html` 的 `px=20`／`11` 改走遊戲端 `statusIconTile`＋`tileCanvas`／`statusIconCanvas`（`&live=0` 可切回 3a 的 `status.ts` 直畫，比對用）；加 `&set=corner`（元素架勢 9 × 5 級＋晶能兩個＋有回合數、有數值、空各一，畫 `StatusBadge` 同款的角落）。
- **B6 測試、截圖、報告與上手筆記**：第 7 節 T-B1～T-B8；既有測試改寫（逐條寫「舊斷言 → 新斷言」，不放寬）；第 8.2 節截圖；第 10 節。

## 7. 行為一致測試

資料一律用名詞表快照 `client/src/battle/fixtures/glossary.json`（118 個狀態），不手寫清單；數字寫在斷言旁並註明出處（需求 1.1）。vitest 假畫布用 `test/fakeCanvas.ts`（`setQCanvasFactory`）。

### QI-3a（vitest）

| # | 測什麼 |
|---|---|
| T-A1 | **118 個都有 Q 版圖樣**：名詞表每個狀態 `entry(id)` 不是空（不走「第一個字」）；來源分組數量 沿用 40（`STATUS` 32＋聖輝／暗影架勢貳～伍 8）、借用 4、新畫 74（手畫 39＋紋章 35）（需求 1.1）；借用的 4 個確實呼叫 `parts.ts`／`skills.ts` 那一份（比假畫布呼叫紀錄和直接呼叫該部件相同） |
| T-A2 | **元素架勢各級同圖**：9 元素 × 5 級，同元素 5 級的 `def` 呼叫紀錄相同、`level` 為 1～5；聖輝、暗影的 2～5 級和 1 級同圖；姿態 9 個與元素架勢都用同一個 `stancePlate`（需求 3.3 第 12 點） |
| T-A3 | **框底色**：`stun`、`frozen` → `#d4ac20`；`slow`、`root` → `#2f78c8`；`taunted`、`feared`、`silenced` → `#8a4ccc`；`entangled` 與其餘 111 個只填深底；呼叫紀錄的順序是 深底 → 類別底色 → 框線 → 圖樣（需求 3.1 第 1、2 點） |
| T-A4 | **外框與頭頂形**：狀態卡（框 16.8）染底的 7 個 `glyph` 的 `ow = 1/res`、不染底的 `ow = 0`（圖樣 ≤ 14px）；頭頂（框 9）染底的 `ow = 0`、`inset = 1/res`、暈眩／沉默／嘲諷走 `HEAD_TINT`、其他 4 個走原本的形；`tint: false` 時不染、不內縮（需求 3.2 第 5、6 點） |
| T-A5 | **貼圖對齊整數裝置像素**：框 16.8（`unitPx` 0.2）、9（`unitPx` 1）、開發頁 52 × `res` 1、2 × 五類極性（含不認得）——`blit` 左上角 × `unitPx × res` 是整數；沒有 4 個以上參數的縮放 `drawImage`（需求 3.2 第 8 點） |
| T-A6 | **`fitK` 表**：涵蓋名詞表全部 × {16.8, 9} × 兩種 `res` 用到的 `inset`；值在 [0.7, 1]（內縮的在 [0.4, 1]）且是 0.02 的整數倍；`fitK` 對表上的鍵回表值、不呼叫 `getImageData`（假畫布記錄） |
| T-A7 | **框線寬**：`max(1.5, 框 CSS px × 0.09) / unitPx`；狀態卡 20 與頭頂 11 算出的 ctx 線寬和現行 `max(1.5, size × 0.09)` 相同（7.56 單位、1.5 px，需求 2.4 第 5 列） |
| T-A8 | **不認得、不丟例外**：`brand_new_status`、`""`、`null`、不認得的極性 → 畫名稱第一個字（字色 `#f2e6c8`）或「?」；全部 × 尺寸 × `res` 畫兩次（先暖快取）呼叫紀錄相同 |
| T-A9 | **遊戲畫面不變**：`statusIcon.ts` 的既有測試（`statusIcon.test.ts` 全部）不改一字仍通過；`git diff <起點>..HEAD -- client/src` 除新檔、`dev/`、`qIcon/parts.ts` 的 export 與 A1 的搬移外沒有別的 |

另外（瀏覽器，寫進報告；照 QI-2b 的做法）：開發頁同一頁載入靜態伺服器上的樣張（`qIcons.js`、`qIconsWeapons.js`、`qIconsSkills.js`、`qIconsParts.js`、`qIconsStatus.js`，樣張的 `M`／`MAT` 若有用到先換成 `material.ts` 的色），餵同一份名詞表：
1. **圖**：118 個 × `cardCanvas(20)`／`headCanvas(11)` × `res` 1、2，`getImageData` 逐像素比，寫出相同的個數、不同的列表（最大像素數與原因）。需求 2.2 第 4 點要求逐像素相同；只允許的差異是名詞表來源不同造成的（應為 0）與 `color.ts` 的 `mix` 四捨五入，其他差異先停下回報。
2. **`fitK`**：表的每一筆和樣張 `QIconsStatus.fitK` 相同（0 差異）。
3. **自查表**：`uv run python docs/art/sample/tools/qicons_shots.py --audit status` 的結果附在報告（需求第 5 節末 (c)）。

### QI-3b（vitest）

| # | 測什麼 |
|---|---|
| T-B1 | **`paintStatusIcon` 換成 Q 版**：對名詞表全部，呼叫紀錄等於直接呼叫 `status.ts` 的 `paint`（同參數）；不再出現 `glyphColor` 的顏色作為圖樣色 |
| T-B2 | **頭頂**：`statusIconCanvas(id, 11)` 畫布 22 × 22、框邊長 9、`unitPx` 1、`res` 2；`res = 1` 時 11 × 11；`statusIconKey` 含 `res`，不同 `res` 不同鍵 |
| T-B3 | **狀態卡**：`tileCanvas(statusIconTile(id), 20)` 畫布 40 × 40、`paint` 收到 `unitPx` 0.2、`res` 2（`blit` 單位 0.4）；`tileKey` 含 `res`；`TileCanvas px={20}` 的畫布＝顯示 × `ICON_RES` |
| T-B4 | **不動的確認**：QI-2c T-C6 的 `statusTile` 那一半照舊通過（基準不改）；`statusIconTile` 那一半改成本段新基準（在報告寫「舊基準 → 新基準」，並說明唯一差異來自本段） |
| T-B5 | **角落**：名詞表裡全部 `stance_<元素>_<級>`（45 個）→ `"1"`～`"5"`，即使 `remaining`／`amount` 有值也優先；`crystal_surge` → `"1"`、`crystal_surge_2` → `"2"`；這兩個 ID 與 45 個架勢 ID 都在名詞表快照裡；其他狀態照現行（`ui/statusCard.test.ts` 原有 3 條不改） |
| T-B6 | **排序與排版不動**：`statusRank`、`sortStatuses`、`statusRowLayout`、`bodyEffects` 的既有測試不改一字通過；`ui/statusBadges.test.ts`、`badgeCapsule.test.ts`、`narrowMapLayout.test.ts`、`summonBadges.test.ts` 通過 |
| T-B7 | **部件圓片與召喚物不受影響**：`skillParts.ts` 的 `statusColor()` 仍等於 `glyphColor()`；`qSummonSpirit.test.ts` 不改通過 |
| T-B8 | **既有測試改寫**（`render/statusIcon.test.ts`）：「每個狀態都有 status_look、圖樣」→ 驗 Q 版 `entry` 每個都有（`GLYPH[id]` 那半條保留給部件圓片）；「四組原本重複的圖樣已分開」→ 對同樣 6 對比 Q 版 `def` 的呼叫紀錄不同（若有一對是美術刻意同形——例護盾家族「同一面盾」靠記號分——先查呼叫紀錄；真的相同就停下回報，不刪那一對）；「圖樣顏色」與 `glyphColor("new_buff")` → 保留（第 0 節第 6 列）並另加框底色斷言（T-A3 的值走 `paintStatusIcon`）；「不認得的狀態畫名稱第一個字」→ 加字色 `#f2e6c8`。逐條寫進報告，不放寬 |

## 8. 驗收條件

### 8.1 共通

1. 本段第 7 節的測試全過；改寫的既有測試在報告逐條說明「舊斷言 → 新斷言」。
2. `corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、`corepack pnpm -C client build` 三個結束碼都是 0（分開記）。`render/inkDollSnapshot.test.ts`、`render/creaturePose.test.ts` 通過且快照沒有變。
3. **合併前的 slow 測試**：本段不動後端與內容，相關的是前端讀的快照——`UV_NO_SYNC=1 uv run pytest -q tests/api/test_client_fixtures.py`（確認 `glossary.json` 沒被動、仍是最新）；若實作中動到任何 Python 或 `content/`，停下回報（超出範圍）。
4. **QI-3a**：遊戲畫面不變（T-A9）；不改 `qIcon/core.ts`、`qIcon/weapons.ts`；`parts.ts`／`skills.ts`／`legacy48.ts` 只多 `export`（`git diff` 為證）。
5. **QI-3b `window.__layoutSmoke`**：`corepack pnpm -C client build` 後啟動自己的 `trpg serve`（存檔放暫存區），1600×900、1040×624、800×600 各 `localStorage.clear()` → 開 `/?dev=1&anim=0.1&mute=1` → `await window.__layoutSmoke.runCase("標題")` 全 PASS；另跑 `icons()` 全 PASS（含狀態卡的 canvas，第 5 節）。
6. **QI-3b 浮動卡實測**（6.5.1）：1600×900 與 800×600 各做一次「從狀態徽章滑進卡片 → 卡內捲到底 → 釘住 → 關閉」：主角 HUD 狀態列與單位資訊的 `StatusBadge`（`PartTip`）。結果寫進報告。
7. 截圖存 `docs/art/shots/qi3/`，檔名前綴 `3a-`、`3b-`；每段 ≤ 10 張（D4）；真 1 倍／最近鄰放大特寫用 PNG、其他 jpg 80，單張 ≤ 300 KB；`--force-device-scale-factor=1` 拍；6 倍放大用最近鄰。實機到不了的用開發頁畫並在報告「實機未看」逐項列出。報告寫完整路徑。
8. 需求第 5 節末 (a)～(c) 寫進報告：(a) 逐像素對照方式與結果（3a）；(b) `glyphColor`、`CTRL_COLOR`、`OWN_COLOR`、`POL_COLOR`、`GLYPH`、`drawGlyph` 哪些已不被狀態框用、還留給誰（3b）；(c) `fitK` 和樣張自查表一致與否（3a）。

### 8.2 截圖分配（對到需求第 5 節 8 項）

「真 1 倍」＝開發頁 `res=1`；「DPR 2」＝`res=2`；兩種都最近鄰放大 6 倍、裝置像素比 1 拍。張數不夠時把真 1 倍與 DPR 2 拼在同一張。

| 需求項 | 段 | 內容 | 張數估計 |
|---|---|---|---|
| 1 118 個狀態卡構圖 | 3a | `px=20` 真 1 倍＋DPR 2，×6，分兩張（照 `from`／`n`） | 2（PNG） |
| 2 118 個頭頂構圖 | 3a | `px=11` 真 1 倍＋DPR 2，×6，分兩張 | 2（PNG） |
| 3 控制類 7 個 | 3a | `set=cls`：20、11 各真 1 倍＋DPR 2，加 `tint=0` 一列 | 1（PNG） |
| 4 撞圖組 | 3a | `set=near`：暖色四六角、冷色四六角、岩石／殼／甲七個、晶能兩個；20、11 真 1 倍 | 1（PNG） |
| 8 不認得的狀態 | 3a | `set=unknown`：20、11 DPR 2 | 1（PNG，可併進第 3 項那張） |
| 5 元素架勢 9 × 5 級在狀態卡（含角落數字）＋晶能 1／2 | 3b | `set=corner`：20 DPR 2（走遊戲端 `StatusBadge` 同款角落）；另附一列證明各級同圖 | 1（PNG） |
| 6 實機戰場頭頂狀態列 | 3b | 控制類、持續傷害、增益、中性各至少一個；排序、2 個加「+N」；**1600 寬、800 寬各一張**（jpg）；頭頂一格放大看底色圈（PNG，可拼兩種寬度）；報告寫兩種寬度下圖示的實際螢幕 px（第 0 節第 3 列） | 3 |
| 7 實機狀態卡 | 3b | 主角 HUD 狀態列與單位資訊各一，含角落（回合數、數值、空、架勢級數）、控制類染底；裁切合成一張 | 1～2（jpg） |

合計 3a 約 6～7 張、3b 約 5～6 張。

## 9. 開發中跑的測試

- **QI-3a**：`corepack pnpm -C client exec vitest run src/render/qIcon/ src/render/statusIcon.test.ts src/test/importCycles.test.ts <新測試檔>`。
- **QI-3b**：`corepack pnpm -C client exec vitest run src/render/statusIcon.test.ts src/render/skillIcon.test.ts src/render/qIcon/ src/render/qSummonSpirit.test.ts src/ui/statusCard.test.ts src/ui/statusBadges.test.ts src/ui/badgeCapsule.test.ts src/ui/narrowMapLayout.test.ts src/ui/summonBadges.test.ts src/ui/floatCardRule.test.ts src/dev/layoutSmoke.test.ts src/test/importCycles.test.ts <QI-2c T-C6 的測試檔> <新測試檔>`。
- 每次 commit 前 `corepack pnpm -C client typecheck`；交件前跑第 8.1 節第 2、3 點（三個結束碼分開記，全部 0 才交）。

## 10. 報告格式

各段寫 `docs/phases/PhaseQI-3a報告.md`、`PhaseQI-3b報告.md`：

1. 做了什麼（交付項目逐條，附 commit）。
2. 驗收逐條（測試名稱或指令輸出為證；結束碼分開記）。
3. 改寫的既有測試（舊斷言 → 新斷言）；快照變動說明（預期沒有；有就先停下回報）。
4. 需求第 5 節末 (a)～(c) 中本段負責的；截圖清單（完整路徑、對到第 8.2 節哪一項、真 1 倍或 DPR 2）；「實機未看」清單。
5. 3a：和樣張不同的地方（依賴改 import、名詞表來源、`fitK` 表）逐條；`parts.ts` 等加的 export 清單；`fitK` 表的產法與筆數；超過 80 行的函式（逐行搬的長函式不拆，和樣張對照用）。
6. 3b：頭頂圖示在 1600／800 寬的實際螢幕 px；`__layoutSmoke` 與浮動卡實測結果表；請使用者重開伺服器檢查的重點（戰場頭頂狀態、主角狀態列、單位資訊的狀態、控制類的黃／藍／紫底、架勢角落級數、晶能 1／2）。
7. **待 PM 決定**：最多 10 點，每點附出處；原型數值與解讀類照最保守做完再列。第 0 節第 7 列（`statusTile` 空檔）在 3b 報告再提一次。
8. 順手更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`：第一節表加 `qIcon/status.ts`、`statusFrame.ts`、`statusFit.json` 的職責與 `paintStatusIcon` 的新流程；開發入口表加 `status-gallery.html` 的參數；第四節加踩到的坑；第五節測試表加一列。

## 附：起草時查到的疑點（給開發 PM／美術 PM）

1. **`statusTile` 空檔**（第 0 節第 7 列）：需求 1.2 把它劃給③④，QI-2 0.0 把它留給⑤，兩邊都不換。
2. **需求 2.2 第 3 點「`paintStatusIcon` 的簽名不變」和 2.4 第 6 列「要拿到 `unitPx`、`res`」字面衝突**：用選填尾參數兩邊都滿足（第 0 節第 2 列）。
3. **樣張把第 4 批 `hexPts`／`stancePlate`「原樣」再寫一份**，和需求 2.3「同一題材一份畫法」不一致；規格改成 import（第 0 節第 5 列）。
4. **紀錄第 8 節寫頭頂「最多 3 格」**，需求 1.2 寫 `ROW_MAX_ICONS`＝2：實際戰場用 `unitSprite.ts` 的 `ROW_MAX_ICONS = 2`；`statusIcon.ts` 的 `ROW_SLOTS = 3` 只是 `statusRowLayout` 的預設參數。兩者都不動，不影響實作。
5. **`statusIcon.test.ts`「四組原本重複的圖樣已分開」**含 `guarded`／`shielded`／`defending` 三兩成對，而美術說「護盾家族 6 個同一面盾」是刻意同形（靠記號分）；Q 版呼叫紀錄應仍不同，但若有一對完全相同，T-B8 規定停下回報。
6. **架勢與晶能是否真的沒有 `remaining`／`amount`**：`statuses.yaml` 都是 `expires: never`，`StatusView.amount` 直接取 `StatusInstance.amount`（`engine/view.py` 648 行），助手推斷是 `null`、未實跑；角落規則已定為級數優先，所以不影響顯示，3b 在報告寫實測值即可。
