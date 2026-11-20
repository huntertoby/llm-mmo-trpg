# AR-X10 報告：狀態提示換行、走路預覽用字

依據：`docs/phases/PhaseAR-X10計畫.md`、`docs/art/X10-3d驗收.md`（小修 1、2）、`docs/phases/PhaseX10-3d報告.md`。
基準：開工時 `git merge main`（`1b7457517`）。分支 `worktree-agent-a8ac2033f5a82916c`，沒 push。
只動前端。沒改 HC-2 的檔案（`scripts/hardcoded/classes.yaml`、`client/src/run/AttributeAllocator.tsx`、`run_campfire.json`、後端 content），也沒改 `docs/design/`、`config/`。

## 1. 交付與 commit

| # | 項目 | commit |
|---|---|---|
| 1 | 狀態提示的骰子行自己一行、次要字色 | `33e9679f7` |
| 2 | 走路預覽用字（不加負號、「可能」改前綴、陷阱加全形冒號） | `fc0bf7822` |
| — | 截圖＋狀態提示開發頁（兩項的補拍） | `2bc5af43a` |
| — | 報告 | （本檔所在的 commit） |

## 2. 項目 1：狀態提示的骰子行

- 原本 `StatusBadge` 的說明是 `statusTile().tip`：說明和 `rules_zh` 全部用空白接成一句。所以骰子行看起來像接在傷害句後面。
- 新增 `client/src/ui/tipParts.ts`：
  - `tipParts(lines)` 把說明和規則句切成段。一般句照舊用空白接成一段；遇到骰子行就另起一段，標成 `secondary`。
  - 骰子行用 `DICE_NOTE_RE = /^擲 \d+d\d+，每點 ×\d+$/` 辨認，格式是後端 `dice_note` 產生的固定寫法。
- `StatusCardParts.tsx` 新增 `statusTipParts(id, spread)`：
  - 「會擴散」的那行照舊放在最後。
  - 對照表沒有這個狀態時，照舊寫「狀態」。
- `PartTip.tsx` 多一個選填的 `parts`。每段是一個 `part-tip-text`；次要段多加 `part-tip-secondary`。
- `float-card.css` 的 `.part-tip-text.part-tip-secondary` 設 `margin-top: 0; color: var(--muted)`。
  - 規則字是 `#d0d0dc`，次要字是 `--muted #9a98a6`，和技能長說明的 `skill-card-dice`（`small muted`）同一個字色。
  - 字級沒改，不加任何分隔符號。
- 結果（實測 computed style）：
  - 第一段「身上著火，…刷新持續時間。 回合開始時受到 10–60 火焰傷害」，`rgb(208,208,220)`。
  - 第二段「擲 1d6，每點 ×10」，`rgb(154,152,166)`。
- `statusTile().tip` 沒改：組裝列的部件說明照舊是一句。
- 新測試 `client/src/ui/arX10StatusTip.test.ts`（5 條）涵蓋：
  - 燃燒提示的分段
  - 骰子行在中間時另起一段
  - 會擴散、對照表沒有的狀態
  - 「擲 d1000」這類句子不會被當成骰子行
  - CSS

## 3. 項目 2：走路預覽用字（`client/src/battle/pathPreview.ts`）

- `damageText`：
  - 範圍寫「60–140 傷害」，最小值等於最大值時寫「140 傷害」。
  - `amount_min` 是 null 時寫「最多 140 傷害」。
  - 不再出現負號。
- 新的 `maybe(text, certain)`：不確定時在前面加「可能」。數字開頭的項目中間空一格，例如「可能 30 傷害」。
- 新的 `trapText`：
  - 陷阱確定：「陷阱：60–140 傷害・可能定身」，「可能」只加在不確定的狀態上。
  - 陷阱本身不確定：整張寫「可能觸發陷阱：60–140 傷害・定身」，裡面的狀態不再加「可能」。
  - 冰面之後：不加「可能」（照舊畫紅色虛線）。
  - 沒有傷害也沒有狀態時，只寫「陷阱」，不加冒號。
- 其他項目：
  - 點燃寫「可能點燃」，其他狀態寫「可能＋狀態名」。
  - 反應寫「可能藉機攻擊 最多 50 傷害」。
  - 墜落寫「可能墜落」，致命地形寫「可能致命地形」，倒下寫「可能倒下」。
  - 其餘傷害照傷害的寫法，例如「可能 30 傷害」。
- 冰面那張（`slipRunText`）沒動。
- `pathPreview.test.ts`：
  - 原有的期望字串跟著改（陷阱兩處、冰後陷阱、`damageText` 三條、「不加可能」的檢查）。
  - 新增一組 AR-X10 的 7 條，涵蓋上面每一種寫法，並檢查小牌裡沒有「−」和「（可能）」。
- 開發頁 `client/src/dev/x10PathGallery.ts`：
  - 800 寬的地圖縮放 0.531 → 0.62（照驗收附註，用實機 800 寬的自動縮放）。
  - 加 `&scale=` 參數可以覆寫縮放；標題和註解改成新用字。

## 4. 截圖（`docs/art/shots/ar-x10/`）

做法：
- 無頭 Chrome，參數 `--headless=new --mute-audio --force-device-scale-factor=1`，除錯埠 9791／9792。
- 網址都帶 `mute=1`，視口用 CDP 設定，`deviceScaleFactor` 1。
- 開發頁用 vite dev server（埠 5191）。結束時 vite 和兩個 Chrome 都停了，三個埠都已關閉。

| 檔案 | 內容 | 來源 |
|---|---|---|
| `1-status-burning-1600.jpg` | 1600×900，滑過燃燒圖示的提示卡：傷害句下面一行淡字「擲 1d6，每點 ×10」 | 開發頁 `client/dev/ar-x10-status.html`（正式的 `Hud` → `StatusBadge` → `PartTip`，CDP 滑鼠移到圖示上） |
| `1b-status-burning-crop-1x.png` | 同上，左上 560×360 裁切，真 1 倍 | 同上 |
| `2-path-preview-800-1x.png` | 800 寬、地圖縮放 0.62、真 1 倍：「陷阱：60–140 傷害・可能定身」 | 開發頁 `client/dev/x10-3d-path.html?w=800`（真的 `pathDraw` ＋ `BattleRenderer`） |
| `2b-path-preview-800-x6.png` | 上一張的戰場部分（305×96）最近鄰 ×6 | 同上 |

- 燃燒提示用開發頁拍，沒有用實機：
  - 實機要開伺服器、打一場、點燃敵人才拍得到（X10-3d 的做法）。
  - 開發頁畫的是同一個 React 元件、同一份 CSS、同一份名詞表夾具，說明卡的內容和排法跟實機一樣。
  - 只差周圍不是戰場。若美術 PM 要實機的圖，再補拍。

## 5. 新增字串的歸類（HC-1）

- `classify.py --check` 結束碼 0，沒歸類 0 筆。`tests/test_hardcoded_scan.py` 22 個全過，結束碼 0。
- 掃描器抓到的新數值都已被檔案層級的規則涵蓋，`classes.yaml` 不用補規則：
  - `client/src/dev/x10PathGallery.ts:21` 的 `0.62`，歸到 const／`ts-dev`。
  - 新開發頁 `client/src/dev/arX10StatusGallery.tsx` 的數值同樣是 `ts-dev`。
- 下面這些介面字掃描器沒有列出（函式內的樣板字串與正規式），規則上都屬於前端介面文字：
  - `pathPreview.ts` 的「傷害」「最多」「可能」「可能觸發陷阱」「陷阱：」
  - `tipParts.ts` 的骰子行正規式

## 6. 檢查（最後一個 commit 的樹）

| 檢查 | 結束碼 |
|---|---|
| `tsc --noEmit`（client） | 0 |
| `vitest run`（全部，391 檔、4812 條） | 0 |
| `npm run build`（tsc ＋ vite build） | 0 |
| `scripts/hardcoded/classify.py --check` | 0 |
| `pytest tests/test_hardcoded_scan.py` | 0 |

沒動後端，所以沒跑 ruff／mypy／pytest 其他部分；沒跑全量。

## 7. 待 PM 決定

1. **反應那張的用字**：規格只說陷阱加全形冒號。反應照舊用空格，寫成「可能藉機攻擊 最多 50 傷害」，沒有改成「可能藉機攻擊：最多 50 傷害」。要不要統一加冒號？
2. **「可能」接數字**：其餘傷害不確定時寫「可能 30 傷害」，中間空一格，和「最多 140 傷害」一樣。也可以改成「可能受 30 傷害」。
3. **陷阱不確定、狀態也不確定**：照規格的例子，整張寫「可能觸發陷阱：…・定身」，狀態不再加「可能」。這樣看不出「觸發了也不一定定身」。要不要在這種情況照舊加「可能定身」？
4. **其他地方的骰子行還是接在同一句**：
   - 腳下表面的提示（`SurfaceBadge`）和組裝列部件說明（`statusTile` / `surfaceTile` 的 tip）都還是用空白接成一句。
   - 規格只要求狀態提示，所以沒動。要統一時，在 `SurfaceBadge` 改傳 `parts={tipParts(...)}` 即可。
   - 層數說明（`StackTip`）本來就是逐行、加「・」，也沒動。
5. **骰子行靠固定格式辨認**：前端用正規式認「擲 NdM，每點 ×K」。後端改這個句型時，前端會退回接成同一句。比較穩的做法是在 `/api/glossary` 加結構化欄位，但那要改後端，不在這段範圍。

## 開發 PM 裁定（2026-11-21）

合併：`Merge AR-X10`（--no-ff）。截圖轉美術 PM 驗收。

待決 5 件：
- 1、2、3：玩家看得到的字，轉給玩法 PM 決定；決定後併進下一個前端段。
- 4：排進 HC-6（說明文字段），照同一種排法改：腳下表面的提示、組裝列的部件說明。
- 5：同意。在 `/api/glossary` 加結構化的骰子欄位，前端改成讀這個欄位，不再比對句型。排進 HC-6。

## 8. 追加：玩法 PM 回覆待決 1～3、美術 PM 的小牌字級（2026-11-21）

開工前 merge main（含 AR-X10 合併、玩法交接、`docs/art/AR-X10驗收.md`），沒有衝突。

| 項目 | commit |
|---|---|
| 用字：反應與陷阱一律「名稱：效果」、「可能受 N 傷害」、陷阱不確定時狀態看要不要另外擲 | `b3c03ed4e` |
| 小牌字級下限：畫面字 ≥ 10 px | `dee10a3b2` |
| 補拍 800 寬真 1 倍與真正的最近鄰 ×6 | `e24b0dc9c` |

### 8.1 用字（`pathPreview.ts`）

- **名稱：效果**：新增 `named(name, items)`，陷阱和反應共用。
  - 反應寫成「可能藉機攻擊：最多 50 傷害」，確定時寫「藉機攻擊：最多 50 傷害」。
  - 沒有傷害時只寫名稱，例如「可能藉機攻擊」。
- **「可能」接數字加「受」**：`maybe` 遇到數字開頭時寫「可能受 30 傷害」「可能受 6–9 傷害」。
  - 「最多 50 傷害」「60–140 傷害」照舊，不加「受」。
- **陷阱不確定時的狀態**：每個狀態照自己的 `certain` 判斷。
  - 狀態還要另外擲：「可能觸發陷阱：60–140 傷害・可能定身」。
  - 觸發就一定附上：「可能觸發陷阱：60–140 傷害・定身」。
  - 陷阱確定和冰後的寫法不變。
- `pathPreview.test.ts`：
  - 改期望字串：「可能受 30 傷害」，以及陷阱不確定的那條。
  - 補第 3 點兩種情況各一條。
  - 補反應「名稱：效果」一條（3 種寫法）。
  - 44 條全過。

### 8.2 小牌字級下限（`render/pathArt.ts`、`render/battle/highlightLayer.ts`、`render/BattleRenderer.ts`）

- 做法同延遲預告字（BM-1）：用 `minMarkScale` 算倍率，整張小牌（底、圖示、字）一起反向放大。
  - 新常數 `PATH_TAG_FONT = 12`、`MIN_PATH_TAG_FONT_PX = 10`。
  - `pathTagScale(boardScale)` 算倍率，`pathTagFontPx(boardScale)` 算畫面上的字級。
  - 地圖縮放 0.62 時倍率約 1.344，畫面字 10 px（原本 12 × 0.62 ≈ 7.4 px）。
  - 1600 寬（1.308）時倍率是 1，和原本一樣。
  - 不設上限：小牌變寬蓋到旁邊的格子，照美術 PM 的說法可以接受。
- 字的解析度乘上倍率（`scaleTagNode`），放大後不會糊。
- `placeTags` 多一個參數 `h`，傳放大後的高度，所以放在格子上方時會往上移整張高度。
- 「到不了」小牌同樣套用倍率，置中位置照放大後的寬度算。
- `HighlightLayer`：
  - 畫小牌時記下節點，由 `pathTagRescale` 套用倍率並擺位。
  - `BattleRenderer.setScale` 也呼叫 `pathTagRescale`，所以只改縮放、沒有重畫高亮時，小牌也會跟著改。
  - 每次 `setHighlights` 先清掉舊紀錄。
- 新測試 `client/src/render/arX10PathTagFont.test.ts`（4 條）：
  - 縮放 0.62 時，算出的畫面字級 ≥ 10 px。
  - 縮放 0.3～0.83 都 ≥ 10 px；1600 寬倍率是 1。
  - 擺位用放大後的高度。
  - 高亮層和 `setScale` 都有接上倍率。
- HC-1：
  - 新常數 `PATH_TAG_FONT` 12、`MIN_PATH_TAG_FONT_PX` 10 被既有的 `ts-render` 規則歸到 layout。
  - `classify --check` 沒歸類 0 筆，`classes.yaml` 不用補規則。

### 8.3 補拍（覆蓋原檔）

| 檔案 | 內容 |
|---|---|
| `2-path-preview-800-1x.png` | 800 寬、地圖縮放 0.62、真 1 倍，800×190。小牌「陷阱：60–140 傷害・可能定身」放大後畫面字 10 px |
| `2b-path-preview-800-x6.png` | 上一張戰場部分（左上 10,30，305×126）的最近鄰 ×6 |

- `2b` 的做法：在 Chrome 裡用 canvas `imageSmoothingEnabled = false` 放大，直接 `toDataURL` 存檔，不經過截圖。
- 存檔前逐像素比對過：每個 6×6 方塊都和原圖的那一個像素同色，不符的像素 0 個。
- 上一版用 canvas 畫到頁面上再截圖，結果是平滑放大；這次已修正。
- 環境：
  - 開發頁 `client/dev/x10-3d-path.html?w=800&mute=1`，vite 埠 5191。
  - 無頭 Chrome 加 `--mute-audio`，除錯埠 9793。
  - 結束時 vite 和 Chrome 都停了，兩個埠都已關閉。

### 8.4 檢查（`e24b0dc9c` 的樹）

| 檢查 | 結束碼 |
|---|---|
| `tsc --noEmit` | 0 |
| `vitest run`（392 檔、4818 條） | 0 |
| `npm run build` | 0 |
| `classify.py --check` | 0 |
| `pytest tests/test_hardcoded_scan.py` | 0 |

### 8.5 待 PM 決定（1 件）

1. **陷阱不確定時，狀態目前一律會帶「可能」**。
   - 前端是照狀態事件的 `certain` 判斷「還要不要另外擲」。
   - 但伺服器（`engine/path_preview.py`）的 `certain` 意思是「最少、最多後果兩次模擬都出現」。陷阱本身只在一次模擬裡觸發時，跟著它的狀態也只在那一次出現，所以一定是 `false`。
   - 結果：實機目前只會出現「可能觸發陷阱：…・可能定身」。「觸發就一定附上 → 不加」那條測試有寫，但要等伺服器分得出來才會用到。
   - 要分得出來，伺服器要在狀態事件上多帶一個資訊，說明「陷阱觸發之後這個狀態還要不要另外擲（抵抗）」。這要改後端，不在這段範圍。

## 開發 PM 裁定，補件（2026-11-21）

合併：`Merge AR-X10 follow-up`（--no-ff）。截圖轉美術 PM。

待決 1 件：接受。實機上，陷阱不確定時狀態一律會判成「可能」，這是保守的做法，不會說錯。
- 要分出「觸發就一定附上」，後端的狀態事件得多帶一個欄位，標明觸發後還要不要另外擲。
- 這件排進佇列，和 HC-6 的 glossary 結構化欄位一起做。
