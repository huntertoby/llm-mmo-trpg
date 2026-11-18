# Phase PK-4b 報告：許願池不標偏離路線、挑選模式也標「源晶推演」

依據：`docs/phases/PhasePK-4報告.md` 第 7 節待決 6、9；玩法 PM 答覆 `docs/玩法PM交接.md` 4.1.27 題 4、題 5（main 上的版本；本 worktree 開在較早的 commit，該節是用 `git show main:` 讀的）。

## 1. 改了什麼（只動前端，沒改 Python、API、OpenAPI）

1. **許願池的三選一不標「偏離路線」**（commit `85cb4bade`）
   - `client/src/run/OfferPicker.tsx`：新 prop `hideOffRoute`（預設 `false`）；為真時不畫 `off-route-tag`，卡也不加 `off-route` 紫框。
   - `client/src/world/QuestLog.tsx`：`WorldOfferPending` 在 `pending.source === "wish"` 時傳 `hideOffRoute`。用 `source` 判斷，所以許願池不論是願望驅動還是開關關掉的舊流程（WP-1～3）都不標；任務、機會的三選一與一輪的升級、完整技能三選一照舊。
2. **挑選模式（`pick: llm`）的卡也標「源晶推演」**（commit `a51e88967`）
   - 查證：卡片資料本來就帶 `pick`（`OfferTagOut.pick`，PK-2 起；`run_presenter.offer_out` 照抄 `OfferTag.pick`），前端拿得到，**不用補 API 欄位，也沒重產 OpenAPI**。
   - `client/src/run/llmFlow.ts`：新常數 `LLM_PICK_HINT`＝「這張技能的名字和描述由本機模型取；效果和數值都照規則出題。」；新函式 `llmTagHint(tag)`：`source == "llm"` → 照舊 `LLM_SOURCE_HINT`；否則 `pick == "llm"` → `LLM_PICK_HINT`；其他 `null`。`isLlmTag` 改成兩種都算（目前只剩測試在用）。
   - `OfferPicker.tsx`：小標改看 `llmTagHint`，說明卡用對應的那一句。`pick: top`（分數第一名、沒請或請失敗）不畫。
   - 閃現的選變體畫面沒動（見第 4 節第 1 點）。

## 2. 測試

- 新增 `client/src/run/pk4bOfferTags.test.ts`（5）：許願池不畫偏離標籤與框、其他三選一照畫；兩句說明的字；`llmTagHint`／`isLlmTag` 各種組合；升級與許願的 `pick: llm` 卡有小標、`pick: top` 沒有、自由設計照舊有。
- vitest `src/run src/world src/screens src/ui`：1707 passed，結束碼 0（第一個 commit 前跑 `src/run src/world` 1017 passed、拆開後的三個檔 11 passed，都是 0）。
- `tsc -b`：0（兩個 commit 各跑一次）。`vite build`：0（截圖用）。
- 沒改 Python，所以沒跑 ruff、format、mypy、lint-imports、pytest；沒改 API，沒重產 OpenAPI。沒跑全量 `check.py`、沒跑模擬。快照沒動。

## 3. 實機截圖（`docs/phases/PK-4b資料/`）

做法：暫存區啟動器 `create_app(llm=MockLlmProvider(), static_dir=本 worktree 的 client/dist)`、`TRPG_DEV_ROUTES=1`、`127.0.0.1:8798`；存檔在暫存區，角色 alice 寫在主城守池人正下方朝北、任務幣 9（上手筆記第 147 條）。無頭 Chrome（`--headless=new --mute-audio --remote-debugging-address=127.0.0.1`、除錯埠 9712、`--force-device-scale-factor=1`、CDP `deviceScaleFactor 1`，量到 `devicePixelRatio = 1`、網址 `?mute=1`），1280×1900。開之前 `netstat` 確認 8798、9712 沒人用；結束時用自己記下的 PID（Chrome 19720 含子程序、伺服器 17268）關掉，兩個埠都沒在聽。模型是 Mock，沒碰 LM Studio。

- `01-許願池三選一-無偏離-源晶推演.png`：文字許願「想把敵人凍在火裡」，API 回的 `off_route = [0,1,2]`、三張都是 `pick: llm`；畫面三張都沒有「偏離路線」標籤與紫框，都有「源晶推演」小標；滑過第一張的小標，說明卡是「這張技能的名字和描述由本機模型取；效果和數值都照規則出題。」。
- `02-升級三選一-源晶推演-偏離照舊.png`：一輪（開發起始包、種子 2、`llm: true`）`dev-advance?to=gear_offer` 後正常送 `gear_pick` 跳過，進升級三選一（`dev-advance` 直接到 `level_up` 時 AI 代打不帶挑選器，三張都是 `pick: top`，所以改走這條）。標示 `composer/top`、`composer/llm`、`composer/top`，`off_route = [2]`：中間那張（挑選模式）有「源晶推演」、滑過出挑選模式的說明；偏離的那張照舊標「偏離路線」與紫框；`pick: top` 的卡沒有小標。

## 4. 待 PM 決定

1. **閃現的選變體畫面沒加卡層級的小標。** 閃現的選項沒有 `pick` 欄位（`FlashOptionOut` 只有 `name_source`、`note_zh`）。現狀：本機模型取的名稱後面本來就有「源晶推演」（FL-1g，說明卡是 11-13 定的「這個名字是源晶照你這一路的戰鬥推演出來的…」），挑選模式的大變化、轉型都走這條；**只有本機模型寫了描述（`note_zh`）、但沒改名的小變化沒有標記**。要不要給這種選項也加小標（放在描述旁、用挑選模式的說明句）？前端拿得到 `note_zh` 就能判斷，不用改 API；但前端分不出那句描述是挑選模式還是 LF-1 舊的 LLM 變化寫的。我照最保守的做法沒動。
2. 許願池不標偏離用的是 `pending.source === "wish"`，開關關掉的舊流程（`wish_off`）也不標。4.1.27 題 4 的理由（方向由玩家決定）兩種流程都成立，照此做；若只要願望驅動才不標，改一行。
3. `isLlmTag` 改成兩種都算，現在畫面已不用它（改用 `llmTagHint`），只留給測試與以後用；要刪也可以。

## 5. 程序

自己起的伺服器與 Chrome 都已結束；8798、9712 沒在聽。`client/node_modules` 是這次 `pnpm install --frozen-lockfile` 裝的（worktree 本來沒有）。
