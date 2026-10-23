# Phase 3-47 報告：排版煙霧檢查＋說明卡不多包一層＋工坊小修

## 做了什麼

1. **`Hint` 不產生外層元素**（`client/src/ui/Hint.tsx`）：`cloneElement` 把事件與 ref 掛到唯一的子元素（子元素自己的處理函式先執行）；`text` 為空原樣回傳；子元素不是單一 DOM 元素時丟出清楚錯誤（`hintChild`）。「按鈕自己的選單開著（`aria-expanded`）時不顯示、已開的立刻關」保留（改讀子元素的 props）。兩處子元素是元件：`Hud` 的 `Bar` 改成在內部包 Hint（新 `hint` 參數）、工坊 `SkillIconView` 外面加 `<span class="ws-size-demo">`。移除全部 `> .hint-tip >` CSS 與 `.hint-tip{display:contents}`，順手去掉重複的選擇器。新 vitest `Hint.test.ts`（輸出與沒有 Hint 完全相同、父子仍是直接子節點、錯誤訊息、`aria-expanded`）。
2. **排版煙霧檢查**（`client/src/dev/layoutSmoke.ts`，`main.tsx` 掛 `window.__layoutSmoke`）：純函式 `evaluate`／`formatTable`／`alphaOf` 有 vitest（`layoutSmoke.test.ts`，每種壞法各自 FAIL、量不到不算過）；`runCase` 在頁面內開戰鬥（固定種子 20261024、起始武器弓）、量測、回傳 PASS／FAIL 表。**沒有安裝任何新套件。**
3. **煙霧檢查發現並修了兩個既有版面錯誤（窄螢幕 800×600）**：播放列被切到畫面外（底部列高度不夠，改讓窄螢幕也用 `short` 緊湊排法）、六顆播放按鈕文字折成兩行且最右一顆超出視窗 3px（`white-space: nowrap`＋窄螢幕縮小間距與內距）。這兩項在舊版（基線）800×600 就 FAIL。
4. **工坊小修**：玩家模式隱藏「進階：直接編輯 YAML」面板與檢查結果的規則代碼（`?dev=1` 照舊）；巢狀效果的提示文字不再提 YAML；「必須第一個／最後一個」效果在加入時自動排到正確位置（`insertEffect`，一般效果夾在兩者之間；vitest）；縮放屬性採「提示」方案：法術技且還沒選效果時，基本設定步驟的限制清單多一句提醒（`options.py`，pytest 一個）。
5. 文件：`docs/開發PM交接.md` 6.2 第 5 點改寫成這個流程；6.5.1 的 CSS 注意事項改成「說明卡不包層」。

## 煙霧檢查步驟（可重跑）

1. `corepack pnpm -C client build`；背景 `UV_NO_SYNC=1 uv run trpg serve --port 8012`（只關自己的）。
2. 每個情況：`resize_window`（寬×高）→ `navigate http://127.0.0.1:8012/?anim=0.1` → `javascript_tool`：`await window.__layoutSmoke.runCase("標題")`（底部最矮加 `{shortBottom:true}`）。
3. 結束 `resize_window` preset `desktop`，停掉自己的伺服器。

## 結果（本分支）

| 情況 | 結束回合寬 | 播放列在畫面內／一行 | 三條拖曳線 | 格子卡提示列 | 更多動作選單 | 無 .hint-tip | 總計 |
|---|---|---|---|---|---|---|---|
| 1600×900 | 250/250 = 100% | PASS／PASS | PASS | PASS | PASS | PASS | 全 PASS |
| 800×600（窄螢幕，沒有拖曳線） | 220/220 = 100% | PASS／PASS | 略過（確認不存在） | PASS | PASS | PASS | 全 PASS |
| 1600×900 底部列最矮 | 250/250 = 100% | PASS／PASS | PASS | PASS | PASS | PASS | 全 PASS |

## 怎麼驗證會 FAIL

`git show df405c7:client/src/ui/Hint.tsx > client/src/ui/Hint.tsx`（舊的外包 span 版），`vite build`，1600×900 跑 `runCase`：6 項 FAIL（結束回合寬 58/250 = 23%、播放列與 6 顆按鈕被擠出視窗、三條拖曳線找不到、`.hint-tip` 36 個）。還原後重建，全 PASS。另外舊 Hint＋舊 CSS 的基線在 800×600 為 7 項 FAIL（其中 2 項是上面修掉的既有錯誤）。

## 檢查

vitest 全部（含新增）、typecheck、build 通過；`tests/skillgen` 相關 pytest、ruff、format、mypy（skillgen）通過。未跑 `scripts/check.py`。未改 API，OpenAPI 無變動。

## noqa

無。

## 待 PM 決定

1. 窄螢幕改用緊湊排法（`short` class）是我的處理方式，視覺上右欄按鈕略小；若想保留原尺寸需要加高窄螢幕的底部列（196px）。
2. 縮放屬性只做「提示」，沒有搬到效果步驟之後（搬動要改後端步驟順序與前置條件，約 0.2 段）；若要真的搬再另派。
3. 玩家模式下，工坊無法編輯「巢狀效果」（賭注分支等，原本靠 YAML）；是否要在一般介面開放，另議。
4. `layoutSmoke` 掛在正式前端 bundle（數 KB、無副作用）；若不想放進正式包，可改成僅 `?dev=1` 時動態載入。
5. 煙霧檢查需要人（或 agent）用內建瀏覽器跑；若要進 CI，需要 Playwright 之類的新套件，請使用者同意後再裝。
