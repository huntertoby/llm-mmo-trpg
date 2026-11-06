# Phase 3-3 報告：前端骨架（格子渲染與基本操作）

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 56a2fa9 | `create_app(static_dir=…)` 把建置好的前端掛在 `/`（API 路由優先）；`trpg serve` 在 `client/dist/index.html` 存在時一併提供網頁，否則印出建置提示；`tests/api/test_static_client.py` |
| 4622b03 | `client/` 骨架：Vite 8 ＋ React 18.3.1 ＋ TypeScript 5.9（`strict`）＋ PixiJS 8.22；`pnpm-lock.yaml`、`packageManager: pnpm@12.14.0`；`scripts/export_openapi.py` → `client/openapi.json` → `gen:api`（openapi-typescript 7.13）→ `client/src/api/schema.d.ts`；`src/api/{types,client}.ts`；OpenAPI 快照測試；`.gitignore` 加 `node_modules/`（`client/dist` 已由既有的 `dist/` 涵蓋） |
| ed3ba41 | 純邏輯 `src/battle/`（繪製模型、合法動作分類與標籤、紀錄彙總、動畫計畫、座標換算、對照表）與 vitest 30 個測試 |
| 2e5af66 | 戰鬥畫面：PixiJS 繪製器、React 元件、開始畫面、戰鬥畫面 |
| 738aed6 | `scripts/play.py`（一鍵試玩）、`scripts/check.py` 加前端三步（找不到 `corepack` 時略過）、`tests/test_play_script.py` |
| （本報告） | `docs/phases/Phase3-3報告.md` |

套件版本全部鎖定為精確版本（`package.json` 無 `^`）：`react`／`react-dom` 18.3.1、`pixi.js` 8.22.0、`vite` 8.3.4、`@vitejs/plugin-react` 6.1.2、`vitest` 5.0.5、`typescript` 5.9.3、`openapi-typescript` 7.13.0、`@types/react` 18.3.31、`@types/react-dom` 18.3.7。TypeScript 用 5.x 而非 7.0：openapi-typescript 的 peer 相依是 `typescript ^5`。

## 2. 驗收條件逐條

1. **`build`、`typecheck`、`test` 全過**：通過。
   - `corepack pnpm -C client build`：`tsc --noEmit && vite build` → `✓ built in 249ms`（`dist/index.html` 0.85 kB、主程式 `index-*.js` 449 kB／gzip 140 kB）。
   - `corepack pnpm -C client typecheck`：無錯誤。
   - `corepack pnpm -C client test`：`Test Files 5 passed (5)、Tests 30 passed (30)`。
2. **OpenAPI 快照測試；`schema.d.ts` 由腳本產生、進 git**：通過。`tests/api/test_openapi_snapshot.py::test_openapi_matches_the_client_snapshot`（比較 `create_app().openapi()` 與 `client/openapi.json` 解析後的內容；失敗訊息提示執行 `uv run python scripts/export_openapi.py` 與 `corepack pnpm -C client gen:api`）、`test_the_generated_schema_exists`。
3. **`scripts/play.py` 建置並啟動**（PM 驗收）：實作者確認過：前端原始碼比 `dist` 新時，`uv run python scripts/play.py --no-browser --port 8766` 依序執行 `install`、`build` 後啟動 uvicorn，`curl -i http://127.0.0.1:8766/` 得到 `HTTP/1.1 200 OK`、`content-type: text/html`、內容 `<!doctype html><html lang="zh-Hant-TW">…`；`/api/maps` 照常回 10 張地圖。測試：`tests/test_play_script.py`（需要建置的判斷 2 個、`--no-build --no-browser` 轉呼叫 `trpg serve --port` 1 個）。結束時已關閉程序。
4. **在瀏覽器打完一場**（PM 驗收）：實作者用 Claude 內建瀏覽器實際試過一次（`trpg serve` 背景執行、結束後關閉）：吊橋深淵／位移流 開戰 → 點藍色格子移動（紀錄出現「A 位移流英雄 從 (0, 3) 移動到 (1, 5)（消耗 4 移動）」）→ 結束回合（看得到 AI 移動、我方 B 倒下淡化、木橋燒毀）→ 勾「略過動畫」連按結束回合直到「敗北……（全滅）・第 5 輪」；第二場狹窄長廊從「其他動作」使用「技能：魔劍斬 → 木箱 (1, 2)」，木箱被摧毀、AP 與法力扣除、冷卻顯示。瀏覽器主控台沒有錯誤。點選敵人攻擊的路徑只以 vitest 驗證（`actionForClick` 3 個測試），這次試玩沒有實際點到可攻擊的敵人。
5. **逐格移動動畫、以 `view` 為準；中文紀錄、彙總步行**：通過（邏輯以測試為證，動畫的觀感 PM 驗收）。
   - `src/battle/log.test.ts`：連續步行合併成一行、其他事件文字依序並去掉 CLI 縮排、`teleport` 不合併且前後的步行各自成行、不同單位不合併、沉默事件不打斷合併、跨步驟（同一單位連續）合併。
   - `movePlan`：`walk`／`forced`／`teleport` 依序、`teleport` 時間 0、`forced` 比 `walk` 快。
   - 戰鬥畫面流程：收到回應 → 寫紀錄 → `BattleRenderer.animate`（舊畫面上的單位逐格補間）→ `setShown(res.view)` 以新 `view` 整個重畫。
6. **網頁戰鬥的紀錄以 `trpg battle replay` 重播通過**（PM 驗收）：實作者在上面第 4 點那場網頁戰鬥結束後，取下載連結 `/api/battles/{id}/log` 的內容執行 `uv run trpg battle replay web_battle.json`：「重播驗證通過：104 個動作、272 個事件，最終狀態一致（bridge_chasm，種子 337536239）。」
7. **`scripts/check.py` 全過（含前端）；複雜度 noqa 不增加**：通過。摘要：ruff check、ruff format --check、mypy、lint-imports、pytest（1587 passed）、client install、client typecheck、client test 全部「通過」。複雜度類 noqa 20 → 20。
8. **畫面結構與已知限制**：見第 7、8 節。

## 3. 複雜度 noqa

- 新增：無。移除：無。總數（src／scripts／tests 的 C901／PLR0911／PLR0912／PLR0915）20 → 20。
- 其他 noqa：`scripts/play.py` 一個 `PLC0415`（建置完才載入 `trpg.cli.main`）；`tests/test_play_script.py` 一個 `PLC0415`（monkeypatch 用）。

## 4. 修改既有測試期望值

無。新增測試：`tests/api/test_openapi_snapshot.py`（2）、`tests/api/test_static_client.py`（5）、`tests/test_play_script.py`（3）；pytest 1577 → 1587。

## 5. 待 PM 決定

1. **顯示用名稱寫在前端對照表**：`client/src/battle/glossary.ts` 抄了地形、表面、物件、狀態、反應、結束原因的中文名與「可燃」「地板型」標記（顏色本來就該在前端）。內容新增種類時前端退回顯示 ID，不會壞，但要手動同步。要不要加一個 `/api/glossary`（由內容庫產生名稱與標籤），讓前端只保留顏色？本段沒做，因為規格只允許 5.4 的後端改動。
2. **「其他動作」清單很長**：傳送類技能（例如「閃現」）每個目的地都是一個合法動作，清單可達數十項（可捲動）。3-4 換成正式技能 UI（先選技能再選目標）時會解決。
3. **`StepOut.events` 在 OpenAPI 是任意 JSON**：前端手寫窄化型別（`src/api/types.ts` 的 `EventBase`／`UnitMovedEvent`），沒有改 API。3-4 若要依事件做更多動畫，可考慮在 API 端把事件改成 discriminated union（OpenAPI 會變大很多）。
4. **openapi-typescript 把有預設值的欄位標成必填**：`CreateBattleRequest.max_rounds` 在前端另外宣告為可省略；其他請求目前沒有受影響。
5. **錯誤後的同步**：任何請求失敗（400／409／500）時顯示 `detail`，並再 `GET /api/battles/{id}` 以伺服器狀態為準；`stalled` 顯示「戰鬥中止」與下載紀錄。
6. **單位代號**：前端照 CLI 規則（依單位 ID 排序，我方 A、B……、敵方 a、b……，含倒下的單位）在前端計算；伺服器回應的事件文字只用單位中文名（同名敵人分不出），前端自己產生的步行行用「代號 名稱」。要不要讓伺服器的 `text` 也帶代號？
7. **倒下的單位淡化留在原格**（撤離的單位移除）；動畫只移動未倒下的單位，援軍等中途出現的單位不播動畫，播放完直接以 `view` 出現。
8. **種子**：開始畫面的種子預設為 0～2³¹ 的隨機數（瀏覽器 `Math.random`，只決定開局，不影響重播）；輸入框接受到 2⁵³−1（JavaScript 安全整數），伺服器接受到 2⁶⁴−1。
9. **`trpg serve` 找前端的位置**：以原始碼路徑推得 `<專案根>/client/dist`（`CLIENT_DIST`）。以後若打包安裝 `trpg`，需要改成設定或參數。
10. **pnpm 12 的提示**：`pnpm install` 會印出「Agent skills awaiting approval: pixi.js」（pixi.js 套件附帶的 AI 代理技能檔，需 `pnpm approve`）。不影響建置；實作者沒有核准，請 PM 決定是否忽略。

## 6. 代表性輸出節錄

`uv run python scripts/check.py`：

```
=== 檢查結果摘要 ===
  ruff check             通過
  ruff format --check    通過
  mypy                   通過
  lint-imports           通過
  pytest                 通過
  client install         通過
  client typecheck       通過
  client test            通過
全部檢查通過。
```

網頁戰鬥（吊橋深淵）紀錄節錄（右下角紀錄區）：

```
1  c 盜賊弓手 從 (9, 5) 移動到 (6, 4)（消耗 4 移動）
1  盜賊弓手 結束回合
1  — 位移流英雄 的回合（AP 3，移動 5，法力 20/20）
1  A 位移流英雄 從 (0, 3) 移動到 (1, 5)（消耗 4 移動）
```

開發模式：`uv run trpg serve` 與 `corepack pnpm -C client dev` 同時執行時，`curl http://127.0.0.1:5173/api/maps` 經 Vite proxy 取得地圖列表（已確認，程序已關閉）。

## 7. 畫面結構（給 3-4）

```
client/
  index.html、vite.config.ts（/api → 127.0.0.1:8000 proxy；vitest 設定）、tsconfig.json
  openapi.json                    scripts/export_openapi.py 產生
  src/
    main.tsx、App.tsx             App：開始畫面 ↔ 戰鬥畫面（key = battle_id）
    styles.css                    深色主題，寬度 < 900px 時改直排
    api/
      schema.d.ts                 openapi-typescript 產生（勿手改）
      types.ts                    schema 別名 ＋ 事件窄化型別（EventBase、UnitMovedEvent、isUnitMoved）
      client.ts                   fetch 包裝 api.{maps,builds,skill,createBattle,battle,act,decide}、ApiError、logUrl
    battle/                       純邏輯（無 React／PixiJS，vitest 測）
      glossary.ts                 顏色與名稱對照表（換美術只改這裡）
      geometry.ts                 TILE_SIZE、tileCenter／tileOrigin、pixelToTile、posKey
      units.ts                    unitMarkers（A／a）、unitNames（label＝「代號 名稱」）
      drawModel.ts                buildDrawModel(view, heroId) → DrawModel（tiles／objects／units／traps）
      actions.ts                  classifyActions → {moves, attacks, others(含中文標籤), endTurn}、actionForClick、actionLabel、skillIdsOf
      log.ts                      logLines(steps, names)：步行彙總
      animation.ts                movePlan(steps)：移動動畫計畫
      testFixtures.ts、fixtures/oil_depot_seed3.json（真實建立戰鬥回應）、*.test.ts
    render/
      BattleRenderer.ts           PixiJS：圖層 tiles → objects → highlights → traps → units → hover；
                                  draw(model)、setHighlights({moves, attacks, hover})、animate(plan, skip)、點擊／滑過回呼
    ui/                           React 元件
      BattleCanvas.tsx            建立／銷毀 BattleRenderer，model 或 highlights 變更時重畫
      TurnBar.tsx                 輪數、地圖與天氣、行動者、先攻順序
      UnitInfo.tsx                單位資訊（HP／護盾／法力／耐力／AP／狀態／層數／冷卻）
      ActionPanel.tsx             其他動作清單、結束回合、略過動畫
      BattleLog.tsx               戰鬥紀錄（自動捲到底）
      DecisionDialog.tsx          反應詢問（接受／拒絕、代價）
      EndPanel.tsx                勝負、再來一場、下載紀錄
      ErrorBanner.tsx、useSkillNames.ts（技能名快取，/api/skills/{id}）
    screens/
      StartScreen.tsx             地圖、build、種子 → POST /api/battles
      BattleScreen.tsx            狀態：response（最新回應）、shown（畫面上的 view）、lines、busy、hover、selected；
                                  run(call)：鎖住 → 回應 → 紀錄 → 動畫 → setShown；錯誤時 GET 重新同步
```

3-4 接手的切入點：技能範圍與連鎖預覽在 `BattleRenderer.setHighlights` 加圖層（預覽 API 已有 `affected_tiles`）；正式技能 UI 取代 `ActionPanel` 的「其他動作」；反應設定與正式詢問視窗取代 `DecisionDialog`；HUD 擴充 `TurnBar`／`UnitInfo`；隊友快捷按鈕呼叫 `PUT /orders`（`api/client.ts` 尚未包裝）。

測試用的真實回應 `fixtures/oil_depot_seed3.json` 由 `TestClient(create_app()).post("/api/battles", json={"map_id": "oil_depot", "seed": 3, "hero_build": "build_fire"})` 的 JSON 存成；API 回應格式改了需要重存。

## 8. 已知限制

- 物件的「可燃」以右上角橘點表示，燃燒中以橘紅外框加「火」字表示；地板型物件（木橋、薄冰、草叢）畫成半透明整格。致命地形（深淵、岩漿、冰窟）畫紅框與叉號，牆壁畫磚紋。都是色塊，沒有美術。
- 高度只用明暗與左上角數字表示，沒有立體效果；深淵等不可站立的地形不做明暗。
- 只有移動有動畫（逐格補間；`forced` 較快、`teleport` 直接出現）；攻擊、傷害、表面變化沒有動畫，播放完以 `view` 整個重畫。分頁在背景時動畫有保底計時，不會卡住。
- 點擊只處理「敵人 → 普攻」與「格子 → 移動」；攻擊物件、技能、推擊等都在「其他動作」清單。同一目的地多條路徑只取第一條（不能選路線）。
- 沒有技能範圍預覽、HUD、反應設定、戰術指令按鈕、部署（3-4）；沒有一輪流程與存檔（3-5）。
- 目前內容沒有 `prompt` 反應（3-2 報告 #1），所以反應詢問框在一般試玩中不會出現；它的程式路徑沒有在瀏覽器實際觸發過。
- 每次重畫都重建所有 PixiJS 物件（目前的地圖都不大，試玩時沒有感覺到效能問題；更大的地圖再最佳化）。
- 主程式 bundle 約 449 kB（PixiJS 為主），本機使用不影響。
