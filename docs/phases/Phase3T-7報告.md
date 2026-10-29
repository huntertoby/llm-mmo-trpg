# Phase 3T-7 報告：前端戰鬥畫面拆分

外觀與行為不變的整理段（審查 W10、前端審查 F6／F7）。只動 `client/`，未碰後端與設計文件。

## 1. 結果摘要

- `client/src/screens/BattleScreen.tsx`：**1268 行 → 397 行**（主元件只剩組裝：幾個 hook 呼叫＋ JSX；自己只有 4 個 `useState`／`useRef` 類 hook：提示、存檔訊息、彈出面板、兩個 ref）。
- `onTileClick` 抽成純函式 `battle/tileClick.ts`（`decideTileClick`），新增 38 列表格測試。
- `client/src/styles.css`（3782 行、696 個單位）→ `client/src/styles/` 11 個檔＋`index.css`，規則逐字相同。
- vitest 117 檔／1145 測試全過；`tsc`＋`vite build` 成功；排版煙霧檢查三情況全 PASS（拆分前、HOOK 拆完、CSS 拆完各跑一次）。

## 2. 拆分對照表

### BattleScreen（`client/src/screens/battle/`，點擊規則在 `client/src/battle/`）

| 原本在 BattleScreen 內的部分 | 新位置 |
|---|---|
| `onTileClick` 的判斷規則 | `battle/tileClick.ts` `decideTileClick(state, tile)` → 判別聯集（ignore／pin／command_dest／act／submit／order／hurl_pick／hint） |
| `onTileClick` 執行結果（釘卡、送出、提示…）、`onTileHover`、資訊卡內容、收合偏好 | `screens/battle/useTileInteraction.ts` |
| 回應／畫面視圖／紀錄／忙碌／橫幅／速度／震動；`sleep`／`runOp`／`play`／`run`；開場第一次播放；接續戰鬥還原紀錄 | `screens/battle/usePlayback.ts` |
| 主角、技能卡、`classified`、按鈕、基本／種族模式、複製與複合第二段暫停、`model`、環境預告標記、焦點格、`canAct`／`canOrder` | `screens/battle/useBattleData.ts`（純 `useMemo` 派生） |
| 選取狀態：模式、投擲第一段、指揮、灌注、面板預覽、隊友指令目標；回應換了就取消 | `screens/battle/useSelection.ts` |
| `send`／`act`／灌注關鍵字選擇／`decide`／`decideCopy`／`decideWith`／反應設定／隊友指令／「之後都自動」補送 | `screens/battle/useBattleActions.ts` |
| `cancel`、`pickMode`／`pickSkill`／`pickOrder`、召喚物指揮與灌注取得選項 | `screens/battle/useSelectionCommands.ts` |
| Esc 鍵 | `screens/battle/useBattleKeys.ts` |
| 預覽請求、`Highlights` 合成、滑過紀錄／預告疊標示、圖例、可燃火苗 | `screens/battle/useHighlights.ts` |
| 版面偏好、右欄收合、縮放（Ctrl＋滾輪／錨點還原）、中鍵平移、版面 CSS 變數 | `screens/battle/useBoardViewport.ts` |
| 縮放控制列 | `screens/battle/ZoomControls.tsx` |
| 底部列（主角卡＋技能列＋回合操作／結束面板） | `screens/battle/BattleBottomBar.tsx` |
| 四種對話框（複合第二段、灌注、複製、反應詢問） | `screens/battle/BattleDialogs.tsx` |
| 頂端列四個彈出面板的內容 | `screens/battle/battleTools.tsx` |
| `CommandSession`／`InfuseSession` 型別 | 移到 `battle/summonControl.ts`（`ui/SummonPanel.tsx` 改由此匯入） |

DOM 結構、class、事件與屬性逐字相同（`board-scroll` 的平移事件改用展開的 `panHandlers`，內容同原本）。

### styles.css（`client/src/styles/`，`index.css` 依層疊順序匯入）

| 檔案 | 內容 | 單位數 |
|---|---|---|
| `base.css` | 變數、重設、按鈕／表單預設、面板、錯誤訊息、字型匯入 | 16 |
| `start.css` | 開始畫面 | 9 |
| `battle-layout.css` | 戰鬥版面、戰場縮放、拖曳線、右欄、底部列、回合操作／播放列、窄螢幕、勝利條件列 | 95 |
| `hud.css` | 主角狀態卡、源力、彈匣、裝備充能、層數名稱 | 30 |
| `skill-bar.css` | 技能列、稀有度、種族技、常駐鈕與更多動作、關鍵字、戰場變奏 | 66 |
| `battle-panels.css` | 反應詢問／設定、環境預告、隊友指令、圖例、動作面板、召喚物操控與灌注 | 69 |
| `battle-log.css` | 戰鬥紀錄 | 26 |
| `float-card.css` | 共用浮動卡、說明框、部件說明、格子／單位資訊卡、點擊式選單 | 49 |
| `workshop.css` | 技能工坊 | 91 |
| `run.css` | roguelite 一輪（開局、營火、升級、進化、技能點、測試模式） | 96 |
| `gear.css` | 裝備圖示、測試裝備欄、詞條、三選一與背包 | 80 |

合計 696 個單位（規則／@media／@keyframes／@import）。

## 3. 外觀與行為不變的證據

1. **CSS 內容**：腳本解析原檔與新檔，比對 696 個單位的正規化文字（含重複次數）：缺 0、多 0（唯一改動是字型 `@import` 的相對路徑 `./assets` → `../assets`）。
2. **層疊順序**：因為拆檔會改變規則先後，寫了腳本檢查「跨檔、順序被翻轉、選擇器可能作用於同一元素、宣告同族屬性、優先權相同」的規則對：共 15 組，逐一人工檢視——皆為不同元件（如 `.selected` 在工坊卡／召喚模式／裝備格、不同容器下的 `button`／`ul`／`input`），或宣告值相同（`cursor: pointer`），判定安全。檔案順序即按此選定。
3. **DOM 計算樣式快照**：用 headless Chrome（CDP）對開始畫面、技能工坊、開新一輪、戰鬥畫面（1600×900 與 800×600，含彈出面板切換）取每個元素約 50 個計算樣式屬性，舊碼 vs 新碼：戰鬥 10 組 **0 差異**；其餘三張只差「關鍵字按鈕的順序」（每次載入伺服器隨機排序，與 CSS 無關）。
4. **截圖對照**（`docs/phases/img/3T-7-before-*`、`3T-7-after-*`，同一伺服器種子、全新存檔資料夾）：
   - 技能工坊 1600×900：**逐像素相同**。
   - 戰鬥 1600×900、1600×900（底部列最矮）：排除右下角「更多動作」選單開啟瞬間後，只剩 `(772–870, 422–517)` 一小塊 60～90 px 的差異——拆分前同一份程式跑兩次也有同樣位置與數量的差異（單位／格子脈動動畫的相位），非本段造成。
   - 戰鬥 800×600：差異集中在右下「更多動作」選單展開動畫的相位（舊圖在動畫中途、新圖已展開；選單內容與位置相同）。
   - 開始畫面：只差下方關鍵字按鈕的隨機順序。
5. **排版煙霧檢查**（`3T-7-before-smoke.txt`、`3T-7-after-smoke.txt`；`runCase(title, {viaRun:true})`，先 `localStorage.clear()`）：1600×900、800×600、1600×900＋`shortBottom` 三個情況，拆分前與拆分後皆**全 PASS**（每情況 9 項，含格子資訊卡提示列、更多動作選單無說明卡、無 `.hint-tip`）。
6. 浮動卡（6.5.1）：未新增任何彈出層；`HoverFloat`／`TileCard`／`Hint`／`DialogFrame` 的使用處與屬性不變，格子資訊卡與更多動作選單的行為由煙霧檢查覆蓋。**未另外手動實測「滑進卡片 → 捲到底 → 釘住 → 關閉」**（本段沒改浮動卡元件與規則）。

## 4. 測試

- 新增 `battle/tileClick.test.ts`：38 列（Shift 釘住、非自己回合釘住、無模式攻擊／移動／釘住、模式送出／關釘住的卡／複製暫停、推擊被擋提示、撥開忽略、投擲兩段、隊友指令五種、指揮選終點／換終點／打敵人／非回合）。
- 既有 `floatCardRule.test.ts`、`fontLoad.test.ts` 改讀 `styles/*.css`（原本讀 `styles.css`）。
- 全量 vitest 117 檔／1145 測試通過；`corepack pnpm -C client build`（tsc＋vite）成功。未跑 `scripts/check.py`（依規格）。

## 5. commit

1. `refactor(client): extract onTileClick into pure decideTileClick with table tests`
2. `refactor(client): add battle state hooks (playback, data, selection, actions, keys)`
3. `refactor(client): add battle view hooks (tile interaction, highlights, board viewport)`
4. `refactor(client): assemble BattleScreen from hooks and sub-components`
5. `refactor(client): split styles.css into per-screen files under styles/`
6. 本報告與截圖。

## 6. 待 PM 決定

1. 主元件 397 行大半是 JSX 與傳給子元件的 props（hook 之間用參數傳遞，沒有 Context）。若要再縮，可把 `BattleBoard`（戰場＋縮放＋提示＋模式面板＋召喚物面板）抽成子元件，或改用 Context；本段未做以免擴大範圍。
2. CSS 檔順序即層疊順序，`index.css` 有註解提醒。日後新增規則建議放進對應檔案末端；跨檔覆蓋同優先權規則時要注意順序。是否要加 vitest 檢查（例如禁止同一選擇器出現在兩個檔案）可後續再議。
3. `useBattleData`／`useHighlights` 等 hook 沒有單獨的 vitest（需要 React 測試環境，專案目前 `environment: "node"` 且沒有 testing-library）；行為由煙霧檢查與截圖覆蓋。要不要引入 jsdom／testing-library？
4. 彈出面板（反應設定、隊友指令、圖例、版面）在 headless 快照中點擊沒有展開（DOM 與未點擊相同），所以這四個面板的 CSS 只靠靜態順序檢查，沒有計算樣式比對；建議驗收時人工開一次。
5. 本機 8014 埠已被別的程序佔用（非本人啟動），改用 8024；報告中的伺服器皆在結束時關閉。
