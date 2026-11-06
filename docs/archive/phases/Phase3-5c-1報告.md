# Phase 3-5c-1 報告：roguelite 一輪的網頁畫面

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| ead031c | 後端：存檔加 `ruleset_hash`（內容庫的穩定 SHA-256）；`RunStore.load` 對戰鬥中的存檔檢查雜湊，不符回 422 與中文原因；pytest 4 個 |
| 9a3c0cb | 前端：`client/src/run/flow.ts`（流程狀態純函式）、`flow.test.ts`（23 個 vitest）；`api/client.ts`、`api/types.ts` 只新增一輪的方法與型別別名 |
| 56755bd | 前端畫面：`RunNewScreen`、`RunScreen`（進度）、`RunLevelUp`、`RunCampfire`、`RunEnded`；`run/` 的元件（配點、主角面板、候選選擇器）；`App.tsx` 路由與重新整理後自動回到進行中的一輪；`StartScreen` 入口與「繼續一輪」存檔列表；`BattleScreen` 只加 `runMode`（存檔鈕、主角倒下提示） |
| （本報告） | 報告 |

沒有 push、stash、reset、amend。`schema.d.ts`、`openapi.json` 沒有改（API 的路徑與回應格式沒變）。

### 1.1 設計說明

- **流程**：首頁「開新一輪」→ 選 build、配 4 點（或「自動配點並開始」）、種子 → 進度畫面（主角 HP／法力／源力／屬性／技能、6 場進度、下一場地圖與敵人）→「開始第 N 場」呼叫 `POST /api/runs/{id}/battle`，沿用戰鬥畫面 → 結束後按「回到一輪」（`GET /api/runs/{id}` 結算）→ 升級（配 2 點、三選一或跳過、欄位滿時選要換掉的）→ 營火（重骰、選或放棄、離開）→ 結束摘要（勝敗、各場地圖與結果與輪數、主角狀態、開新一輪）。
- **戰鬥畫面的接點**：`BattleScreen` 新增選填 `runMode`；有值時戰鬥中顯示「存檔」按鈕（呼叫 `POST /save`，戰鬥中也可以），主角倒下時顯示「主角倒下，隊友繼續作戰」（0.12 #5）。「← 回到一輪」沿用 `exitLabel`，戰鬥中途離開也可以，之後「繼續第 N 場」會接續同一個戰鬥工作階段。
- **偏離路線**（0.12 #7）：候選卡片有紫色虛線框與標籤「偏離路線：縮放屬性與目前主屬性（智力）不同」；顯示順序由 `displayOrder(一輪種子, 組別識別字)`（FNV-1a ＋ mulberry32 洗牌）決定，同一組永遠相同、重新整理後也相同，但偏離路線的位置不固定（vitest 掃 60 個種子，三個位置都出現）。
- **欄位滿**：前端以 `kind_id` 預先判斷（主動 6、被動含修正 3、反應 1、姿態 1；與後端 `skill_slot_problems` 相同）；規則改變型傳說等前端看不出的限制，由後端 422 觸發「替換清單改列全部技能」。
- **重新整理**（規格 `localStorage`）：進行中的 `run_id` 存在 `trpg.currentRun`（讀寫都 try/catch；格式不合法視為沒有）；重新整理後先 `POST /api/runs/load`，存檔不存在（404，還沒存過）才退而用 `GET /api/runs/{id}` 讀伺服器記憶體。存檔在戰鬥中就直接進入該場戰鬥（重播到存檔當下）。讀不回來（內容檔已變更等）時忘掉這一輪，首頁頂端顯示原因。一輪結束後清掉該 key；「回首頁」也會清掉（之後可從「繼續一輪」讀檔）。
- **0.12 #8 雜湊**：`trpg.roguelite.save.ruleset_hash(library)` ＝ 所有已載入內容檔（相對路徑排序，`model_dump(mode="json")`，排序鍵 JSON，SHA-256）；`RunSave.ruleset_hash: str | None = None`，API 存檔時寫入（每個 `RunStore` 第一次用到才算並快取，約 20 ms）。讀檔時：戰鬥中的存檔雜湊不符或沒有此欄位 → 422「內容檔已變更，無法重播戰鬥中的存檔；可讀取戰鬥之間的存檔」；戰鬥之間的存檔不檢查。存檔格式維持 `trpg-run/1`（新欄位可省略，舊存檔照常讀取）。CLI `run auto --save`、`run new` 寫的存檔是戰鬥之間或已結束，不需要雜湊，所以沒有改 CLI。

## 2. 驗收條件（7.4 的 3-5c-1）

1. **開新一輪 → 進度 → 戰鬥 → 升級 → 營火 → 結束摘要，每個畫面都可從網頁操作** — 通過（瀏覽器實測）。以 `trpg serve --port 8123`（暫時啟動後已關閉，存檔放在暫存資料夾）：首頁「開新一輪」→「自動配點並開始」→ 進度畫面 → 「開始第 1 場」→ 戰鬥畫面（有「存檔」、「← 回到一輪」）；升級畫面（配 2 點到力量、選傳說技能、技能欄滿出現「換掉…」清單、換掉火焰箭、確定）→ 回到進度畫面「下一場：第 2 場」且技能清單已換；營火畫面（HP 40/40、法力回滿、源力 3、「重骰技能候選（剩 1 次）」「離開營火」）；結束摘要畫面（失敗、各場結果表、主角狀態）。升級／營火／結束的存檔是用 `auto_play` 在 AutoStop 停下後 `write_save` 做出來讀入的（沒有親手打完整輪；完整打完整輪交給 3-6 驗收）。
2. **流程狀態純函式有 vitest** — 通過。`client/src/run/flow.test.ts`：`runView：每種節點`（`battle`、Boss、讀檔回來在戰鬥中、`level_up`、缺候選丟錯、`campfire` 兩種、`ended` 勝敗）、`主角倒下與歷程`、`候選顯示順序`、`屬性配點`、`技能欄位`、`升級確定鈕與送出內容`、`存檔列表與目前的一輪`，共 23 個。
3. **戰鬥中存檔 → 重新整理 → 回到同一場同一步** — 通過。瀏覽器：戰鬥中按「存檔」→ 重新整理 → 直接回到「第 1／30 輪」的同一場戰鬥（讀檔重播）。後端 `tests/api/test_runs_api.py::test_save_mid_battle_load_and_continue_matches`（戰場與合法動作與存檔時相同）。
4. **雜湊不符的戰鬥中存檔被拒並顯示中文原因（pytest）** — 通過。`tests/api/test_runs_api.py::test_mid_battle_load_rejects_a_changed_ruleset_hash`、`test_old_mid_battle_save_without_hash_is_rejected`、`test_between_battles_save_ignores_the_hash`；`tests/roguelite/test_save.py::test_ruleset_hash_is_stable_and_follows_content`。前端把 422 的 `detail` 顯示在首頁頂端提示（重新整理時）或錯誤列（從「繼續一輪」讀取時）。
5. **偏離路線有標籤、位置不固定** — 通過。`OfferPicker`（標籤與說明文字、紫色虛線框）；vitest `偏離路線（索引 2）出現在各個位置`、`同一組永遠相同，且是 0..n-1 的排列`。
6. **主角倒下提示** — 通過（程式與型別；未在瀏覽器親眼看到，因為需要主角真的在戰鬥中倒下）。`BattleScreen`：`runMode` 且 `shownHero.downed` 時顯示「主角倒下，隊友繼續作戰」；歷程與結束摘要也標「主角曾倒下」（vitest `recordText`、`downedBattles`）。
7. **`pnpm build` 成功、`check.py` 全過** — `corepack pnpm -C client build` 成功；`check.py` 結果全部通過（ruff、format、mypy、lint-imports、pytest、client typecheck、vitest 239 個）。

## 3. 複雜度 noqa

沒有新增或移除。複雜度類 noqa（C901、PLR0911、PLR0912、PLR0915）總數前後相同。

## 4. 修改既有測試期望值

沒有。

## 5. 待 PM 決定

1. **重新整理一律先讀存檔**（照規格）：重新整理後若玩家在上次存檔之後又打了一些步驟，這些進度會回到存檔點（伺服器記憶體裡其實還有）。若希望「重新整理不丟進度」，可改成先 `GET /api/runs/{id}`、失敗才讀檔；一行即可，請決定。
2. **沒有自動存檔**：只有玩家按「存檔」才寫檔；伺服器重啟後沒存過的一輪就消失（首頁會顯示找不到）。是否要在每個節點（戰後、升級後、營火後）自動存檔？
3. **開局點數 4 寫在前端**（`START_POINTS`）：API 沒提供 `start_free_points`；若之後 `roguelite.yaml` 改了要同步。可改為 API 回傳。
4. **`/api/builds` 不含屬性與 HP**：開新一輪畫面只能顯示 build 的主題與起始技能名稱，看不到英雄的武器與 HP、法力（3-5c-2 負責 `/api/builds` 加 `max_mana`，可一併補）。
5. **起始技能組已經滿欄**（例如主動 6/6、被動 3/3、反應 1/1）：第一次升級幾乎一定要替換技能；畫面已處理，但手感上第一次選牌就要丟掉一張，請試玩時觀察。
6. **「繼續一輪」列出存檔時只顯示 build id（例如 build_banisher）**，沒有中文名（`SaveSummary` 沒有 build 名稱）；可在 API 補 `build_name_zh`。
7. **伺服器重啟後**，已讀過的一輪的 `/api/skills/{id}`（技能卡片）要先讀檔才查得到；前端用 `primeSkillCard` 在進入一輪時先把主角技能放進快取，所以戰鬥畫面名稱正確。戰鬥畫面單獨重新整理的情況（無一輪）屬於 3-5c-2 範圍。
8. **一輪結束的存檔**在「繼續一輪」列表中顯示但「讀取」按鈕停用（沒有可玩的內容）；也可改成直接不列。
9. **前端沒有元件測試**（vitest 環境為 node，只收 `*.test.ts`）：畫面行為靠 flow 純函式測試與本次瀏覽器實測；若要測元件需加 jsdom 與 testing-library。
10. 暫時啟動的 `trpg serve --port 8123` 已關閉；沒有動 8000 埠。

## 6. 代表性輸出

```
$ corepack pnpm -C client exec vitest run src/run
 Test Files  1 passed (1)
      Tests  23 passed (23)

$ uv run pytest -q tests/api/test_runs_api.py tests/roguelite/test_save.py -x
26 passed
```
