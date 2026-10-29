# Phase 3U-3 報告｜戰後畫面補進全站排版掃描

規格：`docs/phases/Phase3U計畫.md` 第 3 節。3U-2（人物比例）由另一位實作者進行，本段未碰。

## 1. 開發用入口

不打戰鬥就進戰後畫面。兩段式，**只在開發模式可用**：

- 後端 `POST /api/runs/{run_id}/dev-advance?to=<目標>`（`src/trpg/api/routes/runs.py`）：用既有的 `auto_play`（AI 代打，確定性）把一輪推進到目標節點。目標：`gear_offer`（裝備三選一）、`level_up`（升級選技）、`campfire`（營火）、`campfire_offer`（營火，已重骰出技能候選）、`ended`（一輪結束）。**伺服器要設環境變數 `TRPG_DEV_ROUTES=1`，否則一律 404**；戰鬥進行中回 409。不改存檔格式，也不碰正式流程（只多一條端點；沒有改 API schema，`to` 是查詢參數，回傳沿用 `RunResponse`，所以不需要重新產生 `types.ts`）。
- 前端 `client/src/dev/devScreens.ts`：以第一個開發者起始包、固定種子 1（這個種子的 AI 打得到營火）開一輪，再呼叫 `dev-advance`。
  - 網址：`/?dev=1&screen=gear_offer|level_up|campfire|campfire_offer|ended`（沒帶 `?dev=1` 就不啟用）。
  - 頁面內：`await window.__layoutSmoke.enterDevScreen("campfire")`（`App.tsx` 聽 `trpg:dev-enter-run` 事件，同樣只在 `?dev=1` 時聽）。

啟動範例：`TRPG_DEV_ROUTES=1 uv run trpg serve --port 8034`。

## 2. 掃描涵蓋

`runScreens(title)` 結尾新增 5 個戰後畫面（沿用 3U-1 的「浮動卡有底色」「文字溢出／相鄰重疊」兩項）：裝備三選一、升級選技、營火、營火候選、一輪結束。每個畫面：

1. 進入畫面，**把所有 `<details>`（成長面板的技能卡）展開**後量一次；
2. 滑過該畫面的 `.part-tip`（第一個、中間、最後一個）各量一次浮動卡底色與溢出／重疊。

另新增 `window.__layoutSmoke.runPostBattle(title)`：只掃戰後畫面，不用從首頁開始。

偵測器改良：`isShown` 加上 `checkVisibility({contentVisibilityAuto:true})`，關著的 `<details>` 內容不再被當成顯示中。

用法（同 `docs/開發PM交接.md` 6.2 第 5 步，另需 `?dev=1` 與伺服器 `TRPG_DEV_ROUTES=1`）：開 `/?dev=1` → `localStorage.clear()` → 重新載入 → `await window.__layoutSmoke.runScreens("全站掃描")`（或只掃戰後：`runPostBattle`）。

## 3. 掃描結果與修正

最終版本：1600×900、1280×720、800×600 三種視窗，`runScreens`（57 項）全 PASS（headless Chrome）；戰後部分單獨掃（36 項）三種視窗也全 PASS。

掃描發現（逐條）：

1. **營火／升級的技能成長面板：展開的技能卡在窄視窗被擠成約 200px**（`.growth-row` 第一欄 `minmax(120px, 1fr)`），效果文字「生成「油」表面 3 回合（影響的格子）」頂到卡片邊框，超出 li 5px（偵測器在 800 寬、含捲軸的內建瀏覽器回報 `溢出 li 187>182`）；卡片頭部「主動・範圍・法術技・花法力」也被迫斷行。修正：`styles/run.css` 在寬度 ≥ 641px 時，含展開 `details` 的那一列第一欄改為 `minmax(260px, 1fr)`。前後截圖：`img/3U-3-growth-card-before.png`／`3U-3-growth-card-after.png`（800×600，營火，展開第一個技能）。
2. 偵測器誤報：關著的 `<details>` 內容仍被量到（同一個 li）→ 已修偵測器（見第 2 節）。
3. 其他戰後畫面（裝備三選一、升級、營火候選、結束摘要）：未發現溢出、重疊或無底色浮動卡。裝備卡「目前的裝備」圖示滑過、技能卡零件滑過的浮動卡全部有底色。畫面參考：`img/3U-3-gear-offer.png`、`img/3U-3-level-up.png`（1280×720）。

## 4. 驗收

- vitest 全量：118 檔、1149 項全過（新增 `dev/devScreens.test.ts`）；`tsc --noEmit` 通過；`pnpm build` 通過。
- 後端：新增 `tests/api/test_run_start_api.py::test_dev_advance_…`（預設 404、非法目標 422、依序到 gear_offer／level_up／campfire／campfire_offer）；該檔 5 項全過；`ruff check`、`ruff format --check`、`mypy`（`routes/runs.py`）通過。未跑完整 pytest 與 `scripts/check.py`。
- 排版掃描：見第 3 節，三種視窗全 PASS。
- 截圖用 headless Chrome（內建瀏覽器的分頁會被同時進行的 3U-2 工作拿去導航、且截圖存不了檔）。

## 5. 待 PM 決定

1. 開發入口放在後端環境變數 `TRPG_DEV_ROUTES=1` ＋ 前端 `?dev=1` 兩層：既有 `/api/runs/dev-packs` 沒有後端閘門，我對會改狀態的端點採較嚴格做法；若想統一，請告知。
2. 夾具用「AI 代打」的真實回應（種子 1、第一個開發者起始包），不是手寫假資料；好處是型別與內容永遠與正式流程一致，代價是依賴種子 1 的 AI 打得到營火（測試已鎖定；內容檔改動導致打不到時測試會失敗提醒）。
3. `runScreens` 現在需要 `?dev=1` 與 `TRPG_DEV_ROUTES=1` 才能跑完戰後段落；沒開時戰後段落記為「進得了畫面」FAIL，而不是略過。
4. 展開技能卡那一列的欄位與同表其他列不對齊（只有展開的那列第一欄較寬）；若要全列對齊需改成固定欄寬，會讓所有列的說明欄變窄，本段未做。
5. 戰鬥中的 `runCase`（含 `shortBottom`）本段未重跑，與本段修改無關。
6. 這個 worktree 的伺服器埠用 8034，已用自己的 PID 關閉。
