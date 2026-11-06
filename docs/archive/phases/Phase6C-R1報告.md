# Phase 6C-R1 報告：前端規則測試不再空跑

規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-R1 列（reviewer 2026-11-04 第 1、8 點）。只動 `client/`。

## 做了什麼

1. **共用掃檔工具 `client/src/test/sourceScan.ts`**（新）
   - `listFiles`／`readSources`／`readStyleFiles`／`readFile`：執行時用 `node:fs` 的 `readdirSync`（遞迴，略過 `node_modules`）讀 `client/src/**/*.ts(x)`（不含 `*.test.ts(x)`、`.d.ts`）與 `client/src/**/*.css`，路徑排序。不再用 `import.meta.glob`，所以不受 vitest fsModuleCache（`node_modules/.vitest-cache`）凍結檔案清單影響。
   - `stripTsComments`：用 typescript 的剖析器（`ts.createSourceFile`，內部驅動 scanner、會正確 re-scan 正則／樣板字串／JSX）取得每個語彙單元，只在單元之間的 trivia 用 `getLeadingCommentRanges`＋`getTrailingCommentRanges` 找註解，換成空白（換行與位置不變）。字串、樣板字串、正則、JSX 文字裡的 `//`、`/*` 不會被當註解，也不會吃到下一個 `*/`。說明：只用裸 scanner 無法分辨 `/` 是除號還是正則、`}` 是否回到樣板字串、`'` 是否在 JSX 文字裡，所以用剖析器驅動 scanner；typescript 本來就在 devDependencies，沒有新增相依。
   - `stripCssComments`：CSS 註解，略過字串裡的 `/*`。
   - 測試 `client/src/test/sourceScan.test.ts`：去註解的邊界情況（字串／樣板／正則／JSX 文字／`{/* */}`）、讀得到 `world/story.css` 等，另加一條**守門規則：所有測試檔不得使用 `import.meta.glob`**（之後新測試不會再踩同一個坑）。
2. **四個測試改用 fs 工具**
   - `ui/floatCardRule.test.ts`：原始碼與 CSS 都用 fs；CSS 規則改掃 `src/**/*.css`（多了 `world/story.css`、`world/fieldPeople.css`、`world/fieldThings.css`、`assets/fonts/.../noto-sans-tc.css`），違規訊息帶檔名；加「讀得到 world/story.css、原始碼 > 100 檔」的防空跑檢查。
   - `ui/legacyLayout.test.ts`：同上（CSS 也改掃 `src/**/*.css`）。
   - `render/skillIcon.test.ts`：`content/*.yaml`、`content/skeletons/*.yaml` 改用 fs 讀。
   - `battle/actionInfo.test.ts`：`ui/TurnControls.tsx` 改用 fs 讀。
3. **規則新抓到的違規與處理**（見下節）。
4. **`usePathPreview` 的 battleId 綁死**：`battle/pathFetch.ts` 加 `PathPreviewScope`（送出請求時才讀目前的 battleId；`update(battleId, stateKey)` 變了回傳 true，hook 隨之 `reset` fetcher 清快取並作廢在途請求）。`ui/usePathPreview.ts` 改用它；回傳的預覽也比對 battleId，換戰鬥不會短暫顯示舊戰鬥同一格的路徑；`useEffect` 相依加 `battleId`。測試在 `battle/pathPreview.test.ts`（換戰鬥後同一條路徑向新 battleId 重問、狀態變也清；hook 原始碼不再出現 `api.pathPreview(battleId`）。

## 規則新抓到的違規清單與處理

| 位置 | 規則 | 處理 |
|---|---|---|
| `client/src/dev/storyGallery.tsx:113` | 內聯 `position: "absolute"` | 列入新的白名單 `INLINE_POSITION_OK`，原因：開發用樣張頁（`story-gallery.html`，不進正式 build），是假戰場底圖的格線層，不是彈出層 |
| `client/src/dev/storyGallery.tsx:127` | 同上 | 同上（下方 NPC 頭像對照面板的版面） |

- 新掃到的 `world/*.css`、字型 CSS：**沒有違規**（fixed 規則、absolute＋z-index ≥ 20 規則都過）。
- 改用 typescript 去註解後，`title=`、`role=tooltip`、`createPortal`、`role=dialog` 等規則沒有新增違規。
- 6C-8／6D-5 正在改的檔（地圖標記、fieldModel、regionBlobs、unitSprite、hudFade、RegionMap、WorldScreen）：本段掃描時**沒有違規**（是 main 現況；它們合併後由同一組規則檢查）。

## 驗證

- `corepack pnpm -C client exec vitest run`：清掉 `node_modules/.vitest-cache` 後跑一次 **179 檔／1829 測試全過**；不清再跑一次（快取生效，transform 11% → 3%）**179／1829 全過**，結果一致。
- 故意違規（不清快取）：新增暫存 `src/ui/zzTmpViolation.tsx`（內聯 `position: "absolute"`＋`title=`）與 `src/world/zzTmp.css`（`position: absolute; z-index: 50`），`floatCardRule` 三條規則都抓到：`ui/zzTmpViolation.tsx:1 <div title=…>`、`ui/zzTmpViolation.tsx:1`、`world/zzTmp.css: .zz-tmp`。驗完刪掉、再跑 14／14 過。
- 補充：本 worktree 一開始沒有 `node_modules`（沒有快取），舊版 `floatCardRule` 第一次跑就抓到 storyGallery 兩處，與 reviewer「有快取時空跑」的判斷一致。
- `tsc --noEmit` 過；`corepack pnpm -C client build` 過（只有既有的 chunk 大小警告）。

## 待 PM 決定

- `client/src/dev/summonGallery.ts` 仍用 `import.meta.glob` 讀 `content/summon_looks.yaml`：那是瀏覽器開的 dev 頁、不是測試，不受 vitest 快取影響，沒改（新守門規則只管測試檔）。
- storyGallery 選擇列白名單而非改共用元件：dev 頁的版面用途，不是彈出層；若 PM 希望 dev 頁也不得有內聯定位，可改成 class 寫進 CSS（約 10 分鐘）。
