# Phase 3W-6b 完成報告

依玩法 PM 決定（`docs/design/06-技能.md` 6.34，commit cd4bcbcc）修 3W-6 的兩點。

## 1. 做了什麼

1. **閃現區只留在「下一場前」和營火**：`client/src/screens/RunScreen.tsx` 的 `FlashSection` 條件改成只在 `progress` 且非「繼續戰鬥」時出現；裝備三選一、升級、完整技能三選一不再顯示。營火沿用 `RunCampfire` 內的閃現區。
   - 排版掃描：開發入口 `flash` 畫面改進「下一場前」節點（標籤「戰後・下一場前（靈感閃現）」）。後端 `dev-advance` 新增 `to=next_battle`（打完至少一場後的 battle 節點）；帶 `insight>0` 時把學會的技能都標成「先上場用過」，閃現區才有按鈕可掃（AI 代打會把能閃的都先閃掉）。這是開發用路由，不影響正式 API；沒有改 API 型別，不需重新產生 `schema.d.ts`。
2. **傳承的「先上場用過」照白板自己的**：檢查後端 `inherit()` 本來就是以接受傳承的白板 `target` 的狀態為底（`used` 不受舊技能影響），用法統計也只併白板的。為避免日後被改掉，程式裡明寫 `"used": target.used` 並加註解。新增測試證明行為：
   - 白板沒用過、舊技能用過 → 傳承後 `problem_of` 回「要先在戰鬥中用過」，API 卡片 `can_flash=False`（不顯示「可以閃現了」）。
   - 白板用過 → 傳承後可以閃，`can_flash=True`。
   - 存檔結構不變，不遞增版號。

## 2. 驗收

- ruff check、ruff format --check、mypy、lint-imports：全過。
- pytest（`tests/roguelite`、`tests/api`，`-n 8`）：531 passed。
- 前端：vitest 1174 passed、tsc 無錯、build 成功。
- `runPostBattle()`：1440×900 全 PASS；800×600 全 PASS（含閃現的出題前／指定類別／選項、營火重閃／溶掉／傳承）。裝備、升級、完整技能三選一畫面確認沒有 `.run-flash`；下一場前與營火有。
- 截圖：`docs/phases/img/3W-6b-next-battle-flash.jpg`（1440×900，下一場前的閃現區）。
- 預覽伺服器用 8084，已用自己的 PID 結束；視窗已回 desktop。

## 3. 待 PM 決定

1. 第 2 點後端行為在 3W-6 就已符合決定（3W-6 報告看到的「可以閃現了」是白板自己已用過的狀態），所以只加註解與測試，沒有行為變更。
2. 「繼續戰鬥」（戰鬥進行中重新進入）的畫面沿用原本規則：不顯示閃現區。
3. 開發路由 `dev-advance` 的 `to=next_battle` 是新增的測試用目標，若不想擴充可改回以營火掃描，但「下一場前」就沒有自動化掃描。
