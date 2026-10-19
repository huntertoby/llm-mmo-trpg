# Phase 3C-1 報告：撥開

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 8a9f2f2 | 引擎：`Interact` 加 `mode: "shove_aside"` ＋ `side`；推與撥開共用 `object_move_problem`；`interact_actions`／`interact_options`；`ObjectMoved`／`PushEffect` 加 `how`；敘事「被撥到」；`tests/engine/test_shove_aside.py`（22 個） |
| ae3447d | API：`BattleResponse.interact_options`（相鄰可推物件的推／撥左／撥右，含是否合法與中文原因、落點）；重新產生 `openapi.json`／`schema.d.ts`；`tests/api/test_shove_aside.py` |
| ac9dd73 | 前端：「撥開物件」模式與面板（每個物件一列「往左撥 ←／往右撥 →」，不合法灰掉並顯示原因）；vitest 新增 5 個 |
| 04f15ec | 地圖卡路檢查：`src/trpg/sim/push_check.py`、`scripts/map_push_check.py`、`tests/sim/test_push_check.py` |
| ab2ec7d | 報告 |

## 2. 設計重點

- **方向換算**：以「主角 → 物件」為前方 `(dx, dy)`（`y` 向下，北為 `y − 1`），左 ＝ 逆時針 90° ＝ `(dy, −dx)`，右 ＝ `(−dy, dx)`。例：物件在東邊時，左 ＝ 北、右 ＝ 南。
- **共用合法性**：`battle.object_move_problem(state, unit, obj, direction, verb)`（可推動、相鄰、高度差 ≤ `interact_height_limit`、目標格放得下）；`interact_problem(state, unit, obj, mode, side)` 只負責換算方向。錯誤訊息推為「推不動：…」，撥開為「撥不動：…」，其餘原因（已摧毀、無法推動、必須相鄰、高度差過大）共用。
- **動作格式**：`mode="push"` 時 `side` 必須為 `None`、`mode="shove_aside"` 時 `side` 必填（pydantic 驗證）。`legal_actions` 每個物件依序列出 推、左撥、右撥（只列合法者）。
- **事件**：沿用 `ObjectMoved`，新增 `how: "push" | "shove_aside"`（預設 `push`，舊紀錄可直接重播）。`PushEffect` 同樣加 `how`，只影響事件說明，結算（含落到深淵摧毀、其餘互動）與推完全相同。
- **API**：`legal_actions` 只列合法動作；為了「不合法的方向灰掉並顯示原因」，另加 `interact_options`（主角回合才有；AP 不足時每項原因為「AP 不足」）。
- **前端**：新增基本模式「撥開物件」（`ModeKind` 加 `shove_aside`）；面板上列出主角相鄰的每個可推物件與左右兩個按鈕，按鈕文字的箭頭是畫面上物件實際移動的方向（例：物件在主角下方時「往左撥 →」）。滑過按鈕會預覽、點擊送出。「推動物件」模式維持原樣（點物件即推）。撥開模式下點戰場上的物件不會送出（要用面板選方向）。

## 3. 驗收條件逐條

1. **撥開左、右各一個測試（8 種落點）**：通過。`tests/engine/test_shove_aside.py::test_shove_aside_landing_for_all_eight_cases`（4 個方向 × 左右，驗證落點、`how`、主角不動、AP 扣 1）；`test_legal_actions_list_push_and_both_sides`；`test_interact_side_validation`（push 帶 side、撥開缺 side 皆被 pydantic 拒絕）。
2. **撥到牆、單位、其他物件、地圖外、高度差過大被拒（中文）**：通過。`test_shove_aside_into_wall_is_rejected`、`…_onto_unit_…`（另一側有單位）、`…_onto_other_object_…`、`…_out_of_map_…`（會被推出地圖）、`…_target_too_high_…`（另一側比較高）、`…_height_difference_between_actor_and_object_…`（高度差過大：相差 2 層）、`…_not_adjacent_not_pushable_and_no_ap_…`。
3. **撥開油桶到火表面上，與推過去的結果相同**：通過，但有註記（待 PM 決定 #1）。`test_shove_aside_barrel_onto_fire_matches_pushing_it_there`：推與撥開的事件種類、油桶狀態、表面完全相同。**目前互動表沒有「物件被移到火表面上」的規則**，所以兩者都只是移動、不會點燃；另有 `test_shove_aside_barrel_into_chasm_falls_like_a_push`（撥開與推到深淵都「墜落」摧毀，事件序列相同），證明移動後的互動照常結算。
4. **對敵人不能撥開**：通過。`test_shove_aside_cannot_target_a_unit`（以單位 ID 當物件 ID → 「找不到物件」；`legal_actions` 不含任何對單位 ID 的互動）。`Interact` 本來就只對物件。
5. **網頁上選物件可以撥開**：前端 `tsc --noEmit`、vitest 73 個全過（含新增 5 個：模式建立、撥開不可直接點物件、`asideRows` 左右與不合法原因、只有推時不顯示撥開、動作標籤）。API 層測試 `tests/api/test_shove_aside.py` 驗證回應的 `interact_options`、POST 撥開、非法撥開的中文錯誤。瀏覽器目視由 PM 驗收（我沒有在瀏覽器試）。`check.py` 全過（ruff、format、mypy、lint-imports、pytest、client install／typecheck／test 全部通過）。
6. **地圖卡路摘要表**：見第 6 節。
7. **同種子同輸入重播一致**：通過。`tests/engine/test_shove_aside.py::test_replay_with_a_shove_aside_is_identical`（`run_battle` 以腳本化 policy 撥開一次，輸出 `--log-json` 同格式 JSON，`cmd_replay` 回報「重播驗證通過」）；另以腳本實跑：`uv run trpg battle replay <log>` → `重播驗證通過：24 個動作、66 個事件，最終狀態一致（open_plain，種子 3）。`（紀錄含一次撥開）。

## 4. AI、CLI

- **AI**：`UtilityAI` 對所有非移動／攻擊／技能的合法動作都用 `preview` 評分，`Interact` 本來就在候選中；撥開兩個方向自動進入候選並用同一套評分（沒改程式）。引擎測試中 AI 在含撥開的場面跑完整場且重播一致。目前 AI 的評分沒有「撥開以創造機會」的專門價值（與推相同），不要求用得好。
- **CLI**：專案目前沒有讓玩家下達互動指令的 CLI（`trpg battle` 是 AI 對戰、`replay` 重播紀錄），所以沒有新增語法；戰鬥紀錄文字已支援「木箱 被撥到 (x, y)」。紀錄 JSON 的動作格式為 `{"type":"interact","object_id":…,"mode":"shove_aside","side":"left"}`。

## 5. 修改既有測試期望值

無。既有測試全部維持原樣（`ObjectMoved` 新增的 `how` 有預設值，舊測試與舊紀錄不受影響）。`client/src/battle/fixtures/oil_depot_seed3.json` 未重錄（回應少了 `interact_options` 欄位，前端測試不讀它）。

## 6. 地圖卡路檢查

`uv run python scripts/map_push_check.py`（邏輯在 `trpg.sim.push_check`）。以 BFS（只看地形與高度；所有存活物件視為不可通行，木橋等架在深淵上的物件除外；不看單位與移動點數）檢查我方起始區能否走到敵方起始區；不通時列出單次推／撥能打通的移動；通時另檢查單次移動會不會封死通路。

| 地圖 | 可推動物件 | 擋路的可推物件 | 狀態 | 單次移動可打通 | 單次移動會封路 |
|---|---|---|---|---|---|
| bridge_chasm | crate(3, 1)、crate(6, 8) | 同左 | 通 | — | — |
| cliff_outpost | crate(1, 2)、crate(8, 4)、crate(2, 7) | 同左 | 通 | — | — |
| dark_forest | — | — | 通 | — | — |
| frozen_lake | crate(2, 4)、crate(9, 5) | 同左 | 通 | — | — |
| lava_crossing | crate(3, 2)、crate(6, 7) | 同左 | 通 | — | — |
| narrow_halls | crate(1, 2)、crate(10, 2)、oil_barrel(3, 3)、oil_barrel(8, 3) | crate 兩個 | 通 | — | — |
| oil_depot | oil_barrel ×4、crate(3, 2)、crate(3, 7) | crate 兩個 | 通 | — | — |
| open_plain | crate(5, 4)、crate(4, 5) | 同左 | 通 | — | — |
| ruined_fort | crate(3, 3)、crate(3, 6)、oil_barrel(6, 6) | crate 兩個 | 通 | — | — |
| swamp | crate(3, 8) | 同左 | 通 | — | — |

結論：10 張正式地圖在「所有物件都視為不可通行」時仍然通，沒有地圖需要靠推／撥開才打通，也沒有單次移動會封死通路。`oil_barrel` 本身不帶 `blocks_move`（單位可以走過），只有 `crate` 會擋路。`tests/sim/test_push_check.py` 以合成走廊驗證檢查器本身（一格寬走廊中的箱子 → 「不通」、有側邊空位 → 能打通）。

## 7. 複雜度 noqa

新增：無；移除：無。

## 8. `LOG_FORMAT`

**未升**（維持 `trpg-battle-log/11`）。只新增動作欄位 `side`（預設 `None`）、`mode` 的新值、事件欄位 `how`（預設 `push`）；舊紀錄仍可由新引擎重播，沒有舊行為改變。

## 9. 待 PM 決定

1. **規格驗收 3 的前提不成立**：目前沒有「物件移到火表面上就點燃」的互動規則（`interactions.yaml` 只有元素觸及；物件被推到火上只是移動，推與撥開都一樣）。已測推與撥開結果相同，並另測推入深淵的互動。若希望「油桶被推到火上會爆炸」，需要新增互動規則（不在 3C-1 範圍）。
2. **`legal_actions` 沒有列不合法的撥開**，而是另加 `BattleResponse.interact_options` 給前端灰掉與顯示原因；也可以改成把不合法選項放進 `legal_actions`，但會破壞「legal_actions 皆合法」的約定。
3. **撥開模式不能直接點物件**：避免左右不明確；需點面板按鈕。若希望點物件後在物件旁彈出左右箭頭，屬於 3C-5 的顯示範圍。
4. **「推動物件」與「撥開物件」是兩個獨立的模式按鈕**（規格寫「選了可推物件後，除了推，顯示撥開」）：現有模式機制是先選模式再選目標，沿用最小改動；若要改成先選物件，需要調整選取流程。
5. **左右在介面上的標示**：按鈕文字為「往左撥／往右撥」（相對主角 → 物件方向）加箭頭（畫面上物件實際移動方向）。
6. **CLI 沒有玩家互動指令**（專案目前沒有這種 CLI），故沒有新增語法。
7. **卡路檢查的假設**：不看單位、移動點數與反應；所有存活物件（含草叢）視為不可通行，結果偏保守。
8. **`ObjectMoved.how` 只區分推與撥開**；風、技能的推擊仍記為 `push`。

## 10. 代表性輸出

- 戰鬥紀錄（`open_plain` 種子 3，主角往左撥木箱）：
  ```
  — 戰士 的回合（AP 3，移動 5，法力 20/20）
    戰士 從 (0, 3) 移動到 (5, 3)（消耗 5 移動）
    木箱 被撥到 (6, 4)
    戰士 獲得狀態「防禦」
  ```
- 重播：`重播驗證通過：24 個動作、66 個事件，最終狀態一致（open_plain，種子 3）。`
- API：`interact_options` 例：`{"object_id":"obj_0001","mode":"shove_aside","side":"left","legal":false,"reason":"撥不動：木箱另一側被擋住","to_pos":{"x":3,"y":1}}`
- 引擎：`Interact(unit_id, object_id, mode="shove_aside", side="left"|"right")`；錯誤：`撥不動：木箱另一側有單位`。
