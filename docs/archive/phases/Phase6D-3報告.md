# Phase 6D-3 報告：餘燼集城鎮室內圖與設施（內容）

**依據**：
- `docs/phases/Phase6計畫.md` 第 1 節 6D-3 列、第 2 節、第 6 節
- `docs/phases/Phase6D-2報告.md`（餘燼集門口格 `[3, 5]`、`[19, 5]` 已留好）
- `docs/design/19-灰燼荒原與賽季主線.md` 19.5（NPC 人設卡）、`docs/design/09` 9.6.1
- 玩法 PM 草稿 `玩法PM-Phase6荒原實地地圖草稿.md` 第 2 張、待確認 10
- 範例：霧渡鎮的酒館與鐵鋪室內圖（`content/world/fields/cloud_ridge/interiors/`）

**動了哪些檔案**：
- `content/world/fields/ashen_waste/interiors/ember_market_tavern.yaml`（新增）
- `content/world/fields/ashen_waste/interiors/ember_market_smithy.yaml`（新增）
- `content/world/fields/ashen_waste/ember_market.yaml`：加兩扇門、移除鎮上的事件點、更新註解
- `tests/content/test_ashen_fields.py`：擴充
- 這份報告

沒有改程式（`src/`），也沒動其他實地地圖。開工時 worktree 沒有 6D-2，先 `git merge main`，沒有衝突。

## 1. 交付內容

| 室內圖 | 大小 | 門（餘燼集） | 出口 | 設施 | NPC | 事件點 |
|---|---|---|---|---|---|---|
| `ember_market_tavern` 餘燼集酒館 | 10×8 | `tavern_door` `[3, 5]` | 南邊 `[4,7]`、`[5,7]` → arrive `tavern_door` | `tavern`（櫃檯 `[6,2]`）、`hire`（告示 `[8,1]`） | 無 | `tavern_veteran`（`[2,3]`，老兵的桌旁） |
| `ember_market_smithy` 爐叔鐵鋪 | 10×8 | `smithy_door` `[19, 5]` | 南邊 `[4,7]`、`[5,7]` → arrive `smithy_door` | `smithy`（鐵砧 `[3,2]`）、`enchanter`（餘燼附魔台，石柱 `[7,2]`） | `smith_lu` 爐叔（`[4,2]`，鐵砧旁） | 無 |

**餘燼集外圖**：
- 加 `doors`：`tavern_door` → `ember_market_tavern`、`smithy_door` → `ember_market_smithy`（照 6D-2 註解寫好的兩行）。
- `tavern_veteran` 事件點從酒館門口外 `[3, 6]` 移進酒館室內；鎮上不再有事件點。
- 鎮上 NPC 仍是鐵娘、灰鬚；設施仍是商店、懸賞板、導師。

**灰鬚站位**：照 19.5 與草稿（第 2 張「灰鬚站在酒館外的牆邊」、待確認 10「放在餘燼集」），維持在街上 `[7, 4]`，導師設施 `[6, 4]`。人設卡 `location: ember_market` 與草稿一致，沒有衝突。

## 2. 測試

`tests/content/test_ashen_fields.py` 新增與調整：
- `test_ember_market_town`：兩扇門的 ID／位置／目標；門格與門外（南）一格站得上、從入口走得到；不是隱藏門；NPC 站位走得到；鎮上沒有事件點。
- `test_ember_market_has_exactly_two_interiors`：餘燼集恰好兩張室內圖，荒原其他地點沒有室內圖。
- `test_ember_market_interiors`（兩張各一）：`interior_of`、10×8、沒有門／傳送石／敵人；門與出口互指（出口回餘燼集、arrive 指回那扇門）；設施、NPC、事件點照上表；出口內側站得上且走回入口；NPC、事件點從入口走得到；每個設施旁至少一格走得到；爐叔與鐵砧相鄰。
- `test_event_spots_use_this_places_skeletons`：地點的事件點改成「室外加這個地點的室內圖」合起來比對（`tavern_veteran` 在室內）。
- `test_hidden_entrances_use_hidden_until`：通往室內圖的門跳過（只檢查通往隱藏地點的門）。
- 文件字串跟著更新（「現在不寫門」改掉）。

## 3. 檢查結果

- `uv run pytest -q tests/content -n 8`：2474 通過
- `ruff check`、`ruff format --check`（tests/content）、`mypy src`（503 檔無問題）、`lint-imports`（13 kept）：通過
- `trpg content check`：`實地地圖：雲嶺 18／18、灰燼荒原 18／18（另有室內圖 4 張）`；沒有警告、沒有待補
- 重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 驗證通過（88 個動作、313 個事件；與舊報告的 76／250 不同是 main 上既有的變動，本段沒動 `src/`）

## 4. 待 PM 決定

1. **酒館老兵沒有 NPC**：草稿第 2 張把「酒館老兵（在室內）」列在 NPC，但 19.5 沒有這張人設卡，fields 驗證要求 NPC 對到人設卡。最保守做法：只放事件點 `tavern_veteran`，不放 NPC、不新增人設卡。要補人設卡需玩法 PM 決定。
2. **酒館沒有說書人事件點**：霧渡鎮酒館有 `tavern_storyteller`，餘燼集的事件骨架只有 `tavern_veteran` 屬於餘燼集，所以只放這一個。
3. **室內擺設是原型**：櫃檯、桌子、酒桶、鐵砧、廢鐵料堆、淬火桶用既有物件（crate、low_wall、rubble、stone_pillar）拼，外觀等美術段。
