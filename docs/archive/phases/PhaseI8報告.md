# Phase I8 報告：client 的 `dev/` 開發工具移出正式主 bundle、畫廊頁搬到 `client/dev/`

依據：`docs/phases/整理提案-程式.md` 2.1 節 I8（使用者已同意照提案做）。分支 `dev/i8`。

## 做了什麼

1. **dev 入口改動態載入**
   - `client/src/main.tsx`：拿掉 `installLayoutSmoke` 的靜態 import，改成
     `if (import.meta.env.DEV || isDevMode(location.search)) void import("./dev/layoutSmoke").then(m => m.installLayoutSmoke(window))`。
     **正式 build 帶 `?dev=1`（或 `dev=true`）照樣有 `window.__layoutSmoke`**（`runCase`、`runTown`、`runScreens`…）。
   - `client/src/App.tsx`：拿掉 `createDevRun`、`DEV_ENTER_EVENT`、`devScreenParam` 的靜態 import；原本 `?dev=1` 才掛的 effect 改成在 effect 內 `import("./dev/devScreens")`，載入後才掛事件與處理 `&screen=`；卸載時用 `cancelled` 旗標避免載入完才掛上的監聽漏拆。主程式不再直接用 `DEV_ENTER_EVENT`，所以不需另開常數小檔。
   - 結果：`layoutSmoke`（含 `townSmoke`）、`devScreens` 成為獨立 chunk，不帶 `?dev=1` 的正式首頁不會下載。
2. **畫廊頁搬家**：`client/*-gallery.html` 共 **25 個** → `client/dev/`（`git mv`，內容不變；它們的 `<script src="/src/dev/…">` 是絕對路徑，不用改）。`client/` 根目錄只剩 `index.html`。`client/src/dev/*` 檔頭註解裡的畫廊路徑同步改成 `client/dev/…`、`/dev/…`。
3. **vite 設定沒改**：正式 build 本來就只有 `index.html` 一個入口（畫廊頁從來沒進 `dist/`），dev server 以 `client/` 為根，`/dev/xxx-gallery.html` 直接可開。

## bundle 大小（`pnpm -C client build`）

| | 主 chunk `index-*.js` | gzip |
|---|---|---|
| 改前（main `e34bcd2c`） | 2,262.56 kB | 729.25 kB |
| 改後 | 2,236.43 kB | 720.43 kB |
| 差 | −26.13 kB（−1.2%） | −8.82 kB（−1.2%） |

拆出的 chunk：`layoutSmoke-*.js` 25.72 kB（gzip 9.23 kB）、`devScreens-*.js` 0.75 kB（gzip 0.50 kB）。

提案估的 −10～15% 沒達到：29 檔 6,350 行裡，畫廊程式本來就只被畫廊頁引用、從未進正式 bundle；真正被主程式拉進來的只有 `layoutSmoke`＋`townSmoke`＋`devScreens`。

## 搬過的檔與新網址（`pnpm -C client dev` 後）

`/dev/<名稱>-gallery.html`，名稱：ambient、audio、creature、doll、event-art、fix6f6、form、fx、gear、map、mapmarks、qk3、qk8、region、scale、skill、status-anim、status、story、summon、theme、uie3、wait、walk、weaponicon。
例：舊 `/doll-gallery.html?skin=q&set=key` → 新 `/dev/doll-gallery.html?skin=q&set=key`。

## 驗收

- `pnpm typecheck` 過；`pnpm test`（vitest 全量）272 檔 3,287 個全過；`pnpm build` 過。
- 正式 build＋`TRPG_DEV_ROUTES=1 uv run trpg serve --port 8158`：
  - `/`（不帶 dev）：`window.__layoutSmoke` 為 `undefined`，沒有下載 `layoutSmoke`／`devScreens` chunk。
  - `/?dev=1&screen=level_up`：直接進升級畫面（`devScreens` 動態載入路徑正常）。
  - `runTown`：1600×900、1040×624、800×600 **全 PASS**。
  - `runCase`：1040×624 全 PASS；1600×900、800×600 各 **1 項 FAIL**「戰鬥：四角飾件沒有壓到內容（hero-card 左下 × `svg.skill-chip-glyph`）」。**用 main `e34bcd2c` 的 build 在 800×600 重跑同樣 FAIL**，是既有問題，與本段無關（見待 PM 決定 1）。
- dev server（`--port 5187`）開 fx、doll、story、audio、map、gear、uie3、ambient、theme、walk 共 10 個畫廊，都能載入、沒有 JS 錯誤（uie3 要 `?char=` 與 API，沒帶時是空頁，同改前）。

## 待 PM 決定

1. `runCase` 戰鬥的「四角飾件壓到技能小圖示」FAIL 在 main 上就有（1600×900、800×600），應是近期 RT／UI 段帶進來的，需另排修正（不在本段範圍）。
2. 以下現行文件仍寫舊畫廊網址（根目錄 `/xxx-gallery.html`），本段不在檔案範圍、沒改：`docs/art/AU-2檢查.md`、`docs/art/音效與音樂方案.md`、`docs/art/sample/tools/qk_compare.py`（註解）、`client/src/render/qSample.ts`（註解）、`client/src/ui/floatCardRule.test.ts`（說明字串只寫檔名 `story-gallery.html`，仍正確）。`CLAUDE.md`、`docs/部署說明.md`、`docs/開發PM交接.md` 沒有畫廊網址。各 `docs/phases/Phase*報告.md` 與 `docs/archive/` 屬歷史紀錄未改。美術 PM 的檢查清單若要開畫廊，網址前面要加 `/dev/`。
