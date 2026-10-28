# 美術 PM 交接文件

> 給接手的美術 PM（新對話中的 Claude）。最後更新：2026-10-28（使用者換對話，原話：「我的WEAKLY 終於重製啦 幫我說讓他們交接一下 我想換對話」）。**只讀這份就能開始**；需要時再讀 `CLAUDE.md`、`docs/專案計畫.md`。
> **分支**：美術 PM 的 worktree 分支是 `claude/art-pm-5ea9fb`。最後一次交接時，main 還沒有的只有這份交接文件和驗收工具（`docs/美術PM交接.md`、`docs/art/sample/tools/vite.artpm-live.mjs`）。**下一任開發 PM 接手後，先把 `claude/art-pm-5ea9fb` 併進 main**；下一任美術 PM 可以沿用這個分支，或從 main 開新分支（先確認已合併）。
> **目前沒有進行中的美術工作**；整體開發停在 3-54b 之後（使用者：「做到 3-54b 先停 token 要沒了」）。

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
   1. 寫「移植需求＋檢查清單」交給開發 PM（範例：`種族與側面移植需求.md`、`戰場效果與狀態圖示.md` 第 4 節）。
   2. 開發 PM 派工、合併後，會附截圖（`docs/art/port/<段>/`）請美術 PM 驗收。開發 PM 的截圖常縮到 800 寬，**驗收時自己用原尺寸重拍**。
   3. 看前端的方法（都不用動正式程式）：
      - **開發樣張頁**（最常用）：`.claude/launch.json` 的 `client-main-dev` 會用主資料夾的 client 開 vite（5181），用無頭 Chrome 拍 `http://localhost:5181/<頁>.html`：`doll-gallery`（紙娃娃四方向、側面頭部裝備⑥、武器⑦）、`status-gallery`（狀態圖示）、`fx-gallery`（戰場效果）、`region-gallery`（雲嶺）。
      - **實戰**：`api-8012`（`trpg serve` 開在 8012）＋`client-live-5182`（vite 設定在 `docs/art/sample/tools/vite.artpm-live.mjs`，/api 轉 8012），用內建瀏覽器開 5182。**不要用 8000（使用者）、8001（本機 LLM）**，也不要關掉不是自己啟動的程序（CLAUDE.md 守則 13）。`.claude/launch.json` 不在 git 裡，換對話後照上面兩個名字重建。
      - **動畫**：網址加 `?anim=0.1`（所有動畫慢 10 倍），內建瀏覽器每張截圖約 1 秒也拍得到途中畫面；播放列另有「極慢」。
      - 主資料夾的 main 偶爾已合併但還沒 push；需要時直接讀 `F:/PythonProject/LLM-MMO-TRPG/` 底下的檔案（只讀）。
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
| 戰場效果與狀態圖示（狀態外框依增益／減益／中性、頭頂狀態列、身上特效 5 類、冰牆／荊棘／裂痕／陷阱／區域三種樣式／煙霧上層） | 3-36a、3-36b 完成並驗收；3-38 可燃火苗平時淡化 | `戰場效果與狀態圖示.md`、`3-36a檢查.md`、`3-36b檢查.md`、`3-38檢查.md` |
| 碎界五區世界觀美術（色票、五區換皮規則、地圖覆寫） | 使用者 10-23 全選 A（魔導科技、五區、各區有槍、先做雲嶺）；雲嶺 3-37a／b 完成並驗收（雲海山谷已調暗） | `碎界五區比較.md`、`區域外觀換法.md`、`雲嶺移植需求.md`、`3-37b檢查.md`、`realms.png`；戰場配對見共用筆記 `美術PM-五區戰場外觀.md` |
| 魔導劍（#46） | 10-24 樣張完成、交開發 PM（第二批武器） | `魔導劍.md`、`arcane-blade.png` |
| 形態外觀（#48，第一批 10 種：熊、貓、鳥、惡魔、巨人、元素化身、暗影、樹人、狼人、龍） | 全部另畫、帶主角主色、比召喚物大一號＋形態光環；樣張定稿交開發 PM（排在 3J，尚未實作） | `形態外觀.md` 最後一節「定稿方向」、`forms10.png`、`sample/formArt.js` |
| 可玩種族外觀（方案乙，10 族，龍裔甲乙丙戊）＋真側面 A | 使用者 10-24 確認；**真側面 3S-1／3S-2／3S-3 完成並驗收**；種族 3R-3a（耳／角／尾／膚色／衝突，含成對武器遠側錯開小修）、3R-3b（體型／紋路／鬍子／獠牙／龍裔）待做 | `種族與側面移植需求.md`、`可玩種族評估.md`、`側面畫法.md`、`3S-1～3檢查.md`、`races.png`、`races-side.png`、`dragonkin.png` |
| 字型 Noto Sans TC（400、700） | 3-35 完成 | — |
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
| 3R-3a、3R-3b 種族外觀驗收 | 開發 PM 做完後（規格 `docs/phases/Phase3R計畫.md`；3R-3a 另含成對武器遠側往前上錯開約 3px 的小修） | 照 `種族與側面移植需求.md` 檢查清單；直接用真側面掛鉤 `SideHooks.race` |
| 形態 10 種：待移植、再驗收 | 3J 做完後（規格 `docs/phases/Phase3J計畫.md`） | 照 `形態外觀.md` 定稿方向 |
| 魔導劍 | 已在 3I 實作（`client/src/render/arcaneBlade.test.ts`）；側面版在 3S-3 截圖看過 OK | 正面、背面與裝備圖示還沒正式驗收：開 `doll-gallery` 看一眼，照 `魔導劍.md` 檢查清單 |
| 種族技特效（4 項，約 0.25 段） | 玩法定案後 | 應變、穩若磐石狀態圖示；狐火誘餌外觀；拋錨錨鏈線（`可玩種族評估.md`） |
| 「移動中陷進地板」往北的情況 | 有空時補驗 | 往南、往西已驗 OK；用 `?anim=0.1` 慢動作 |
| 其他四區（晶冠、樞市、灰燼、霜潮）換皮 | 開發排到時 | 換法表在 `區域外觀換法.md`＋共用筆記 `美術PM-五區戰場外觀.md` |
| 冰橋（召喚物） | 玩法 PM 之後評估 | 不在 17 種內 |
| 召喚物新增 `trait` 值 | 有新召喚物時 | 前端目前認得 9 個 |
| 手部細節 | 低優先 | 臂甲、露指手套在小人上很難分 |

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
| `realms.js`、`realms.html` | 碎界五區比較（＋霓虹另案） |
| `arcane-blade.html` | 魔導劍（#46，sword 的 form: arcane） |
| `forms.html` | 形態（變身，#48）：bear、cat、demon（summonArt.js 新 variant） |
| `raceArt.js`、`races.html`、`dragonkin.html` | 可玩種族部件與衝突規則 |
| `sideArt.js`、`side-views.html`、`races-side.html` | 真側面畫法（可調轉向） |
| `formArt.js`、`forms10.html` | 形態 10 種（定稿） |
| `current.js` | 遊戲現況畫法的打包（client/src/render → IIFE），樣張「現況」欄用；重打包方法：用 main 的 vite 以 lib 模式打包 terrainArt／objectArt／skillIcon |
