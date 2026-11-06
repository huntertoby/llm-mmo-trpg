# Phase 3-6 報告｜試玩前收尾

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `3ed57b1` | 後端：自動存檔、`GET /api/battles/{id}/history`、`GET /api/runs/rules`、`/api/builds` 與存檔列表補欄位、8.3 一致性測試 |
| `b804642` | 前端：重新整理先問伺服器、戰鬥紀錄還原、配點數由 API 提供、開新一輪顯示英雄資料、灰掉原因改中性提示、存檔列表中文名與勝敗、「開始 Boss 戰」空格 |
| （本報告 commit） | `docs/phases/Phase3-6報告.md` |

### 設計重點

- **自動存檔**（`src/trpg/api/runs.py`）：`RunStore.autosave` 覆寫同一個存檔檔。觸發點：開新一輪、開始或接續戰鬥、升級／營火選擇、戰鬥結算（`RunStore.sync`，節點改變）、每個戰鬥動作／決定／隊友指令（戰鬥端點在釋放戰鬥的鎖之後呼叫 `autosave_battle(battle_id)`，由戰鬥 ID 找到所屬的一輪；單獨開的戰鬥找不到就略過）。鎖的順序維持「一輪 → 戰鬥」。寫檔失敗（`OSError`）只記警告，不讓遊戲動作失敗。手動「存檔」保留。
- **重新整理**：`resumeRun`（`client/src/run/flow.ts`）先 `GET /api/runs/{id}`，只有 404 才 `POST /api/runs/load`；其他錯誤照丟。
- **戰鬥紀錄還原**：新增 `GET /api/battles/{id}/history`，由 `BattleSession.history()` 從開場重播所有步驟，回傳每步的事件（含中文 `text`，不含戰場視圖，約為 `StepOut` 的零頭大小）。前端在進入戰鬥且回應沒有任何步驟（接續或讀檔）時取回並放在紀錄前面。
- **開局規則**：`GET /api/runs/rules` → `{start_points, base_attribute}`；前端移除寫死的 `START_POINTS`，改由 API，屬性基礎值也從 API。
- **`/api/builds`** 補 `max_hp`、`weapon`、`weapon_name_zh`（`max_mana` 本來就有）；開新一輪畫面顯示「主角：HP・法力・武器」。
- **存檔列表**（`SaveSummary`）補 `build_name_zh`、`victory`；列表顯示 build 中文名，已結束標「已結束（勝利）」或「已結束（失敗）」。
- **灰掉原因**：新增 `NoticeBanner`（中性藍灰色、`role="status"`、5 秒自動消失、可按 × 關閉），點灰掉技能改用它，不再用紅色 `ErrorBanner`。
- **文字**：`開始Boss 戰`／`繼續Boss 戰` 改為有空格；其餘按鈕與標籤以腳本掃過所有 `.ts`／`.tsx`，沒有其他寫死的中英相鄰文字（動態拼接的名稱沿用專案「中文名稱不加空格」的慣例，未動）。
- OpenAPI 快照與 `schema.d.ts` 已重新產生。

## 2. 驗收條件逐條

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | 自動存檔：戰鬥中每個動作後與每個節點後存檔都是最新 | 通過。`tests/api/test_run_autosave.py::test_every_battle_action_autosaves`（開局、開戰、每個動作後，檔案讀回來的 `RunState`、步驟、指令、種子都與伺服器記憶體相同）、`::test_every_node_change_autosaves`（打完整輪：戰鬥結束當下——還沒有任何一輪請求——檔案已結算到下一節點；升級、營火、結束後都與記憶體一致；列表顯示已結束與勝敗）、`::test_autosave_failure_does_not_break_the_game`、`::test_standalone_battles_do_not_autosave` |
| 2 | 重新整理不丟步驟、戰鬥紀錄有內容 | 通過。pytest：`::test_get_run_keeps_the_in_memory_battle_and_steps`（GET 後同一場戰鬥、同樣的戰場）、`::test_history_restores_the_battle_log_after_load`（歷史事件文字 ＝ 一路收到的事件；讀檔後的新戰鬥歷史相同）。vitest：`src/run/flow.test.ts` 的「重新整理後回到一輪」4 例（有就用、404 才讀存檔、其他錯誤不讀存檔、紀錄還原條件）、`src/battle/historyLog.test.ts`。瀏覽器實測（內建瀏覽器，埠 8765，存檔在暫存資料夾）：用 API 建一輪、打 2 個動作，重新整理後回到同一場同一步（第 1 輪、HP 與位置不變），戰鬥紀錄 46 行（含開場先攻、行動順序），已關閉伺服器 |
| 3 | 8.2 各項 | 通過。配點數：`test_rules_endpoint_gives_start_points`；英雄 HP／法力／武器：`test_builds_give_hp_mana_and_weapon`，瀏覽器看到「主角：HP 60・法力 20・武器 單手劍」與「另有 4 點自由分配」；存檔列表：`test_save_list_has_build_name_and_victory`、`flow.test.ts` 的 saveLabel 兩例，瀏覽器看到「火焰流・種子 5　0/6 場・Lv1・戰鬥中」；中性提示：新增 `NoticeBanner`（沒有元件測試基礎設施，未在瀏覽器實際點到灰掉技能，見待決定 3）；Boss 空格：`flow.test.ts` 的「開始 Boss 戰」「繼續 Boss 戰」 |
| 4 | 8.3 兩個一致性測試 | 通過。`::test_api_battle_log_replays_with_the_cli`（API 打完一場 → `/log` → `cmd_replay` 通過，且重播最終狀態的 SHA-256 等於一輪歷程的 `state_digest`）、`::test_api_load_and_cli_auto_from_finish_identically`（同一個戰鬥中存檔：CLI `run auto --from` 的最終 `RunState`、`auto_play` 直接接續、API 讀檔後以效用 AI 主角打完的最終 `RunState` 三者相等，歷程 `state_digest` 逐場相同） |
| 5 | `pnpm build` 成功、`check.py` 全過 | 通過。`corepack pnpm -C client build` 成功（`client/dist` 已更新，僅有既有的 chunk 大小警告）；`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest、client install／typecheck／test（27 檔、254 個）全部通過 |

## 3. 複雜度 noqa

沒有新增或移除（C901、PLR0911、PLR0912、PLR0915 總數前後相同）。

## 4. 修改既有測試期望值

- `tests/api/test_runs_api.py::test_save_mid_battle_load_and_continue_matches`：自動存檔會在原本的戰鬥打完時覆寫存檔，所以改為在手動存檔後先保留一份檔案內容，打完原戰鬥後再寫回，才能讀「存檔當下」的檔案。斷言本身不變。
- `client/src/run/flow.test.ts`：「開始Boss 戰」→「開始 Boss 戰」（規格要求）。

## 5. 待 PM 決定

1. **自動存檔會覆寫手動存檔**：同一輪只有一個檔案，手動存檔不再能當成「回到某個時間點」的備份（重新試同一個戰鬥中的狀態需要自行複製檔案）。若要保留「手動存檔點」，需另外設計第二個檔案（例如 `run-<id>.manual.json`），這次沒做。
2. **自動存檔失敗只記警告**（如磁碟唯讀）：畫面沒有任何提示，使用者不知道沒存到。是否要在回應或畫面上加一個「自動存檔失敗」的提示？目前採最保守做法，不打斷遊戲。
3. **灰掉原因的中性提示未在瀏覽器實際點擊驗證**：沒有元件測試基礎設施，也沒有用腳本點到灰掉的技能；樣式與自動消失請 PM 驗收時順便看（5 秒，藍灰色，可按 × 關閉）。
4. **單獨開的戰鬥（首頁「開戰」、技能工坊試玩）不自動存檔**：只有屬於一輪的戰鬥才存。
5. **戰鬥中有「自動推進超過上限」的錯誤時不存檔**：該請求拋錯，已結算的步驟留在記憶體，下一個動作成功後才存。極少見，未特別處理。
6. **每個動作都重寫整個存檔**（約 20 KB 以上，`indent=1`）：目前不影響操作；若之後戰鬥步驟很多或存檔變大，可改成不縮排或只在戰鬥間隔寫入。
7. **`/history` 每次呼叫都從開場重播整場戰鬥**：只在重新整理或讀檔進入戰鬥時呼叫一次（每場約數百步，毫秒級）；沒有快取。
8. **已結束的存檔仍列在「繼續一輪」但讀取鈕停用**（0.14 #8 已接受）：現在標示「已結束（勝利／失敗）」，沒有刪除功能。
9. **`HeroOut` 沒有加武器中文名**：一輪進行中的英雄面板仍不顯示武器；只有開新一輪畫面（`/api/builds`）顯示。若要在一輪中也顯示，是小改動。
10. **試玩前提醒**：專案根目錄的 `saves/` 內有 PM 之前留下的存檔（`run-3a674c2a0525.json`、`run-pm-boss-3.json`），其中戰鬥中的存檔內容雜湊若與目前內容檔不符，會被拒絕讀取並顯示中文原因（既有行為）。

## 6. 代表性輸出節錄

- 內建瀏覽器重新整理後（API 先建一輪、打 2 個動作）：戰鬥紀錄第一行為「戰鬥開始：懸崖前哨（10×10）」，接著「先攻：…」「行動順序：盜賊弓手 → 標準隊友（弓手） → 盜賊 → 標準隊友（戰士） → 火焰流英雄」，共 46 行。
- 開新一輪畫面：「主角：HP 60・法力 20・武器 單手劍」「六項屬性起始都是 10；另有 4 點自由分配。」
- 首頁「繼續一輪」：「火焰流・種子 5　0/6 場・Lv1・戰鬥中」。
