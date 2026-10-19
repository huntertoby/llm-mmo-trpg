# Phase 3-4a 報告：逐步播放、glossary、HUD、技能列與預覽

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 10705f3 | API：`BattleResponse.initial_view`、`StepOut.view`、`GET /api/glossary`（`trpg/api/glossary.py`）；重新產生 `openapi.json`／`schema.d.ts`；`tests/api/test_views_glossary.py` |
| （次一個） | 前端：逐步播放（`battle/playback.ts`）、glossary 載入（`battle/glossary.ts` 只留色塊與圖示）、HUD、先攻列 HP 小條、技能列與目標選取（`battle/targeting.ts`）、預覽（`battle/previewText.ts`、`ui/usePreview.ts`）、播放速度三段；vitest 20 個新測試 |
| （次二個） | 修正 glossary 模組文件字串過長（ruff E501） |
| （再下一個） | 播放停頓微調、被動技能代價文字、本報告 |

## 2. 驗收條件逐條

1. **開場先看到戰場與「戰鬥開始」，再一步步看到比主角快的單位行動**：實作者在內建瀏覽器確認。oil_depot、種子 3：橫幅「戰鬥開始」約 1 秒；之後「行動中」依序變為 C 標準隊友 → b 盜賊2 → B → c → d → a，最後輪到 A 主角（取樣記錄）；播放中按「跳到結尾」立即回到主角回合。待 PM 確認觀感。
2. **`initial_view`、`steps[i].view` 的 pytest；OpenAPI 快照更新**：通過。`tests/api/test_views_glossary.py::test_create_has_initial_view_and_per_step_views`（3 個種子；`initial_view` 等於開場狀態的視圖，每步 `view` 等於 `replay(setup, seed, 前 k 步)` 的視圖，最後一步等於 `view`）、`test_action_initial_view_is_the_view_before`、`test_get_has_no_steps_and_equal_views`；`tests/api/test_openapi_snapshot.py` 通過。
3. **速度三段可切換並記住；播放中可略過**：vitest `playback.test.ts`（正常 500 ms／快 150 ms／略過一格、剩餘紀錄補齊）；瀏覽器確認「快」寫入 `localStorage["trpg.playSpeed"]`、「跳到結尾」按鈕在播放中出現並生效。舊的「略過動畫」勾選已移除。
4. **`/api/glossary` 涵蓋所有 content ID；前端不手寫中文名**：`test_glossary_covers_every_content_id`（地形、表面、物件、狀態、層數、反應、元素、屬性）。前端 `glossary.ts` 只剩顏色、圖示、地板型旗標與固定 UI 文字（方向、結束原因）。App 啟動時讀 `/api/glossary`。
5. **HUD**：`ui/Hud.tsx` 顯示 HP／護盾、法力、耐力、AP、移動、反應是否可用、層數、狀態（含剩餘回合）、腳下表面、冷卻；先攻列每個單位有代號與 HP 小條、行動者強調。瀏覽器確認顯示。**AP「含保留點數」：引擎目前沒有保留 AP 的欄位，只顯示剩餘 AP**（見待決定 1）。
6. **技能列選技能、格上選目標、預覽、施放；傳送類不再塞滿「其他動作」**：瀏覽器確認：選「閃現」標出 9 個紅框目標，滑到目標格顯示預覽（確定：移動到 (2, 3)、獲得「隱蔽」），點擊後主角位移、法力 20 → 15、狀態「隱蔽 2 回合」。「其他動作」改為收合備援（本次為 0 項）。vitest `targeting.test.ts`（含真實回應：所有技能動作都落在技能按鈕上，備援清單沒有技能）。方向型以四個箭頭按鈕或點相鄰格（單元測試），瀏覽器沒有實際試到方向型技能；Esc／右鍵取消只有程式碼，未在瀏覽器實測。
7. **網頁戰鬥紀錄以 `trpg battle replay` 重播**：以 API 腳本打完 oil_depot 種子 3（技能優先，10 個請求）：「重播驗證通過：90 個動作、254 個事件，最終狀態一致」。另有 `tests/api/test_full_battle.py` 既有整場測試（全過）。
8. **`check.py` 全過；複雜度 noqa 不增加**：見第 3 節與最後的指令輸出。
9. **畫面描述與 3-4b 注意事項**：見第 6、7 節。

## 3. 複雜度 noqa

新增：無；移除：無；總數維持不變。

## 4. 修改既有測試期望值

- `client/src/battle/log.test.ts`：`StepOut` 多了必填的 `view`，測試輔助函式補 `view: smallView()`。
- `client/src/battle/drawModel.test.ts`：`SURFACES.oil.name` 改為 `surfaceName("oil")`（名稱改由 glossary 提供）。
- `client/src/battle/fixtures/oil_depot_seed3.json` 重新存檔（回應多了 `initial_view`、`steps[i].view`）；新增 `fixtures/glossary.json` 與 `src/test/setup.ts`（vitest 啟動時載入真實名詞表）。

## 5. 待 PM 決定

1. **AP 保留點數**：設計文件寫「剩餘 AP（含保留點數）」，引擎沒有保留機制；HUD 只顯示剩餘 AP。有需要時另開引擎項目。
2. **回應變大**：`steps[i].view` 每步附完整視圖。oil_depot 種子 3 建立戰鬥（29 步）約 600 KB，一般回應數十到一百多 KB；本機可接受。若之後嫌大，可改成只傳與前一步的差異。
3. **播放長度**：規格「每個 AI 動作約 0.5 秒」，但一個單位常有「移動、攻擊、移動、結束」多步。實作為：純移動步驟停頓 150 ms（有動畫）、其他動作 500 ms、結束回合 0。oil_depot 種子 3 的開場仍要約十餘秒（有「快」與「跳到結尾」可用）。數值在 `battle/playback.ts`，PM 試玩後可調。
4. **技能卡片的 `AP None`**：被動／反應技（`ap_cost` 為 `None`）的 `SkillCard.cost` 會出現「AP None」字串（後端 `cost_parts` 行為，非本段範圍）；前端暫時顯示為「被動／反應」。建議之後在後端修正。
5. **glossary 多加「層數」類別**（HUD 要顯示層數中文名），不在規格列表內。
6. **基本動作的選取方式**：防禦、結束姿態、起身為按鈕立即執行；攻擊、推擊、絆倒、推動物件需先按按鈕再點目標（不選時仍可直接點敵人普攻、點藍格移動）。自身型技能先選取（顯示預覽）再按「施放」。
7. **預覽對象**：沒選技能時滑過敵人預覽普攻；滑過移動格不預覽。預覽結果以同一狀態快取，防抖 120 ms。
8. **逐步播放的紀錄**：每一步各自彙總步行（跨步驟的連續步行不再合併為一行）；「跳到結尾」時補上未播放的紀錄。
9. **播放時的主角步驟停頓**：主角自己的動作之後停 150 ms（快：0）。
10. 瀏覽器的滑鼠座標工具在小視窗有偏移，滑過格子的預覽是以派送指標事件驗證；PM 真實滑鼠操作請一併確認。

## 6. 畫面結構（新增／變更）

- `api/`：`client.ts` 加 `glossary()`、`preview()`；`types.ts` 加 `Glossary`、`PreviewOut`、`Direction`。
- `battle/`：`playback.ts`（`playbackPlan`、`frameOps`、`remainingLines`）、`targeting.ts`（技能按鈕、動作模式、目標與點選解析）、`previewText.ts`、`glossary.ts`（`setGlossary`、名稱查詢、顏色表）。
- `render/BattleRenderer.ts`：`Highlights` 增加 `directions`（方向箭頭）、`preview`（影響範圍，橘色）。
- `ui/`：`Hud`、`SkillBar`、`SkillCardView`、`ActionPanel`（基本動作、目標說明、預覽、備援）、`SpeedControl`、`useSkillCards`、`usePreview`；`TurnBar` 加 HP 小條。
- `screens/BattleScreen.tsx`：播放器（`play`／`runOp`，用 `flushSync` 換畫面讓動畫找得到單位）、模式選取、Esc／右鍵取消、預覽候選動作（滑過格子 > 面板按鈕 > 自身型）。

## 7. 給 3-4b 的注意事項

- 反應詢問視窗與反應規則設定可沿用 `DecisionDialog`；播放器已在回應結束後才顯示它（`response.awaiting === "decision" && !busy`）。
- 環境預告、連鎖預覽事件：`PreviewOut` 目前只有 `certain`／`possible` 摘要；連鎖事件要擴充 API 並在 `previewText.ts` 加顯示。
- 隊友快捷指令呼叫 `PUT /orders`（`api/client.ts` 尚未包裝）。
- 新增內容類別時，先更新 `trpg/api/glossary.py` 並重存 `client/src/battle/fixtures/glossary.json`（以 `TestClient` 取 `/api/glossary`）。
- API 回應格式改變時重存 `fixtures/oil_depot_seed3.json`。
