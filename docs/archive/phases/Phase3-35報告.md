# Phase 3-35 報告：前端字型換成 Noto Sans TC

## 下載與授權
- 日期：2026-10-23。來源只有 Google Fonts CSS2 API、`fonts.gstatic.com` 的 woff2、`google/fonts` 的 `OFL.txt`（`scripts/fetch_font.py` 寫死只允許這三個網域，可重跑）。
- 字重 400、700；woff2 共 216 檔（各 108 個 unicode-range 切片），總大小 8,553,664 bytes（約 8.16 MiB）。
- 授權：SIL OFL 1.1，`OFL.txt` 放在 `client/src/assets/fonts/noto-sans-tc/`，字型檔與 `noto-sans-tc.css`（相對路徑、保留 `unicode-range`、`font-display: swap`）都已 commit。
- 沒有新增任何 npm 套件。

## 套用
- `styles.css`：匯入字型 CSS；body 字型 `"Noto Sans TC", "Microsoft JhengHei", system-ui, sans-serif`；`font-weight` 800／600 全改 700（等寬字不動）。
- `render/labels.ts` 的 `FONT` 同一清單；`render/skillParts.ts` 的 `ctx.font` 改用 `FONT`、字重 800 改 700。
- 新增 `render/fontLoad.ts`：`waitForFonts()`（400／700，逾時 3 秒不卡畫面）。`main.tsx` 先等字型再 render；`BattleCanvas` 建立後也先等。
- 快取處理：`document.fonts` 的 `loadingdone` 事件（切片晚到時）會清掉技能圖示快取（`clearSkillIconCache`）並遞增 `fontEpoch`；`BattleCanvas`、`SkillIconView`、`TileCanvas` 訂閱它重畫。裝備圖示與 Pixi 美術貼圖沒有文字，不需清除。

## 檢查
- `pnpm typecheck` 通過；`pnpm test` 768 全過（新增 `render/fontLoad.test.ts`：字型清單一致、@font-face 只有 400／700 且無外部網址）。
- `pnpm build` 成功；`dist` 內有 woff2（小檔被 Vite 內嵌，獨立檔 105 個），`grep` 無任何 `fonts.googleapis.com`／`fonts.gstatic.com`。
- `scripts/fetch_font.py` 通過 ruff check／format／mypy（用主資料夾的 venv；worktree 沒同步相依）。

## 截圖
瀏覽器 1600×900 視窗，在 worktree 建置的前端上實測（本機 8011 埠，已關閉）：主選單、技能卡、戰鬥畫面（浮動「+守護」、頭頂 a／b／c／d 徽章、技能列卡片）皆為 Noto Sans TC，字形清楚不跑版；`document.fonts.check('700 16px "Noto Sans TC"')` 為 true。內建截圖工具無法存檔，故未放圖檔；美術 PM 可重開伺服器目視確認。

## 待 PM 決定
1. 字型總量約 8.2 MiB（216 檔；瀏覽器只載入用到的切片）。若要縮小，可只留常用切片，但需另行授權取得子集。
2. 截圖未存成檔案（工具限制），如需附圖請美術 PM／使用者自行擷取。
3. 完成後請使用者重開伺服器（`client/dist` 需重新建置）。
