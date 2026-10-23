# 美術 PM 交接文件

> 給接手的美術 PM（新對話中的 Claude）。最後更新：2026-10-23。**只讀這份就能開始**；需要時再讀 `CLAUDE.md`、`docs/專案計畫.md`（待決定 #5）。
> 所有美術成果都已由開發 PM 併進 main（截至 main `53040e7`）；美術 PM 的 worktree 分支 `claude/art-pm-20b75c` 沒有未合併的東西。

## 1. 角色

- **美術 PM**：畫面風格的提案、樣張、外觀規則（哪些資料欄位決定外觀）、移植需求與驗收。對應待決定 #5 的美術半邊（世界觀屬玩法 PM）。
- 使用者（huntertoby）是 **最終決策者**，不是工程師。一律用繁體中文；回覆精簡、有結論，比較用表格，附圖。
- 美術 PM **不改** `docs/phases/`、不改正式程式（`client/`、`src/`）；只寫 `docs/art/` 與這份交接。

| 角色 | 交接文件 | 和美術 PM 的關係 |
|---|---|---|
| 專案 PM | `docs/專案PM交接.md` | 使用者的主要對口；轉達使用者回饋與決定 |
| 開發 PM | `docs/開發PM交接.md` | 把美術定案寫成階段規格、派實作者，完成後請美術 PM 驗收。3-25 起由新開發 PM 負責 |
| 玩法 PM | `docs/玩法PM交接.md` | 世界觀、裝備、召喚物等設計；外觀欄位要寫進設計文件時找美術 PM 對齊 |

## 2. 工作方式

1. **樣張**：在自己的 worktree 分支做獨立網頁（`docs/art/sample/*.html`＋同名的 `*.js` 畫法），不接進遊戲。完成後 commit，由開發 PM 併進 main。
2. **截圖**：用無頭 Chrome 直接拍，不需要伺服器：

   ```bash
   "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --user-data-dir=<scratchpad>/chrome-prof --allow-file-access-from-files --virtual-time-budget=3000 --force-device-scale-factor=1.25 --window-size=1545,900 --screenshot=<worktree>/docs/art/xxx.png "file:///<worktree>/docs/art/sample/xxx.html"
   ```

   - Edge 無頭模式在使用者電腦上沒有輸出。
   - Browser pane 開 `file://` 時不會載入同資料夾的 `.js`，只能用上面的指令。
   - 檢查小尺寸時用 `--force-device-scale-factor=1`。
3. **給使用者看**：圖存 `docs/art/`，用 `SendUserFile` 傳。使用者在手機上可能看不到嵌入的圖，必要時用 `display: "attach"` 重傳。
4. **規則優先於圖**：LLM 會不斷生成新內容，所以提案一律寫成「哪些資料欄位決定外觀」。不認得的值一律退回預設，**不得出錯**。樣張頁要附「全組合自測」，例如 `gear-all.html` 頁首。
5. **素材授權**：只用 CC0 或自製。下載任何東西前，先取得使用者同意。目前全部是程式繪製，沒有外部素材；Kenney 已在 3-16 移除。
6. **移植與驗收流程**：
   1. 寫「移植需求＋檢查清單」交給開發 PM（範例：`裝備外觀移植需求.md`、`召喚物外觀.md` 的「定案」以下）。
   2. 開發 PM 派工、合併後，會通知美術 PM 驗收。
   3. 用 `git show origin/main:docs/phases/img/<截圖>` 取出截圖來看，並看報告。
   4. 驗收結果寫成 `docs/art/<段落>檢查.md`：結論、要改的清單、實作者問題的決定。commit 後回給開發 PM。
7. **傳話規則**：
   - **回報只放結論**：做了什麼、結果、卡在哪、要使用者決定什麼；細節寫在 `docs/art/`，訊息只附檔案位置與 commit。
   - **少傳訊息**（2026-10-23，為了省 token）：只在三種情況傳訊息：有結論要轉交或要使用者決定、卡住、需要對方決定。不傳「已收到、副知、回到待命」，收到告知也不回。
   - 需要使用者選的事，附一張選項表給專案 PM（或直接問使用者）。

## 3. 已完成、已採用的美術（全部在 main）

| 項目 | 狀態 | 文件與圖 |
|---|---|---|
| 程式繪製的地形、表面、物件、紙娃娃小人 | 使用者採用，3-16 實作 | `移植需求.md`、`美術風格比較.md`、`3-16a檢查.md`、`3-16b檢查.md` |
| 組裝式技能圖示 | 使用者採用，3-17 實作 | `移植需求.md` 5.3、`skill-icons-assembled.png` |
| 技能卡減雜：方向二「組裝算式」 | 使用者採用，3-18 | `技能卡減雜.md` |
| 倒地圖示：可復活＝綠愛心、救不回＝灰墓碑 | 3-18 | `3-18倒地與高度.md` 1 節 |
| 整格抬高（每階 6px）＋遮擋虛線剪影 | 使用者選 B，3-18／3-19 | `3-18倒地與高度.md` 5 節、`3-18b-3-19檢查.md` |
| 矮牆改畫（暖色石塊＋外框） | 3-18b | `矮牆.md` |
| 組裝式裝備外觀：9 格全部造型，通用版 | 使用者採用（命名選 A），G5a 圖示／G5b 紙娃娃／G5c 小修 | `組裝式裝備.md`、`裝備外觀移植需求.md`、`3G-5a檢查.md`、`3G-5b檢查.md`、`gear-all.png` |
| 武器擴充 #34 的造型（弩、槍、拳套、鐮刀、鞭、成對武器、圖騰杖） | 已併進裝備外觀 | `組裝式裝備.md`「武器擴充」、`weapons-34.png` |
| 召喚物 17 種（體型 × 元素 × 大小 × 特徵） | 使用者定案，3-33h1／h2 實作 | `召喚物外觀.md`、`3-33h1檢查.md`、`summons.png` |

**重要的視覺決定**（之後別推翻，除非使用者要）：
- 外框色＝稀有度（普通灰、優良綠、稀有藍、史詩紫、傳說金）。關鍵字色票由技能圖示、裝備、召喚物共用。
- **小人身上的外光只代表頭目**；裝備稀有度不讓小人發光。
- 鐵 `#7a828b`、鋼 `#a9b6c6`、銅 `#b06a3c`；圖示和紙娃娃共用同一套材質色票。
- 大面積防具（身、頭、手、腳）的元素混色是 0.25／0.15；武器、副手、飾品是 0.4／0.25。
- 圖示顯示尺寸 ≤ 36px 時不畫關鍵字小圖樣。
- 地面影子不加深色外框（否則會變成黑洞）。

## 4. 待辦

| 項目 | 何時 | 說明 |
|---|---|---|
| 世界觀定案後：色票與風格包 | 等使用者定世界觀（待決定 #5，目前暫緩） | 美術意見在 `世界觀美術意見.md`（五區視覺方向、魔導科技建議）；風格包示意在 `gear-styles-guns.png`（東方、魔導、科技、現代）。每個風格約 0.5～1 段 |
| 戰場效果與狀態圖示 | 等使用者選（4 題） | 樣張與移植需求已完成：`戰場效果與狀態圖示.md`、`battlefield-fx.png`、`status-icons.png`。選定後交開發 PM（建議拆 2 段） |
| 冰橋（召喚物） | 玩法 PM 之後評估 | 不在 17 種內 |
| 召喚物新增 `trait` 值 | 有新召喚物時 | 前端目前認得 9 個；新增前由美術 PM 補畫法並更新 `召喚物外觀.md` |
| 手部細節 | 低優先 | 臂甲、露指手套在小人上很難分（`3G-5b檢查.md`） |

## 5. 樣張檔一覽（`docs/art/sample/`）

| 檔案 | 內容 |
|---|---|
| `scene.js`、`procedural.js`、`compare.html` | 第一次風格比較（色塊、Kenney、程式繪製） |
| `paperdoll.js`、`dolls.html` | 紙娃娃（已含 9 格新部件、新武器） |
| `skillIcons.js`、`parts.js`、`assembled.js`、`assembled.html` | 組裝式技能圖示 |
| `declutter.html` | 技能卡減雜三方向 |
| `downed.html`、`height.html`、`height2.html`、`lowwall.html` | 倒地、高度、矮牆 |
| `gearArt.js` | 裝備圖示產生器（含 `resolve()`、`dollItem()`；`legacy` 標記的造型不要用） |
| `gear-all.html`、`gear-sizes.html` | 裝備總覽＋全組合自測、尺寸檢查 |
| `gear2～5.html` | 裝備範例、風格包＋槍、#34 武器、數值卡 |
| `summonArt.js`、`summons.html` | 召喚物 17 種 |
| `fx.js`、`battlefield-fx.html`、`status-icons.html` | 戰場效果、狀態圖示提案（10-23） |
| `current.js` | 遊戲現況畫法的打包（client/src/render → IIFE），樣張「現況」欄用；重打包方法：用 main 的 vite 以 lib 模式打包 terrainArt／objectArt／skillIcon |
