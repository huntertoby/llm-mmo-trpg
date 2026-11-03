# Phase 6C-R2 報告：審查整理②（世界層）＋ 6C-5b（6C-5 收尾）＋渡口算步數（21.10 第 20 條）

規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-R2、6C-5b 列；`docs/design/21-探索地圖與城鎮.md` 21.10 第 9、13～20 條。
開工時已 `git merge main`（含 6D-5 與玩法 PM 86a0b050 的 21.10 第 20～23 條）。不動引擎、不動 `client/`。

## 1. 規則常數搬進 `rules.yaml` 的 `field:`

- 新的 `FieldRules`（`src/trpg/content/world_rules.py`）：`sight_range` 4、`sneak_sight_divisor` 2、`perceive_range` 3、`cut_size` 12、`min_enemy_cells` 4、`min_ally_cells` 3、`walk_max_steps` 30。預設值和原本的常數一樣，`content/world/rules.yaml` 也寫了一份（附說明）。沒寫 `field:` 的舊 content 照常載入。
- 拿掉的常數：`SIGHT_RANGE`（`sight_range()` 改成要傳內容庫）、`PERCEIVE_RANGE`、`CUT`／`MIN_ENEMY`／`MIN_ALLY`（`cut_origin()` 的邊長改成必填）、`WALK_MAX_STEPS`。
- **`walk` 的長度**：規則上限改由 `field.walk()` 檢查（超過回「一次最多走 N 格」）。`WalkAction.path` 的 `max_length=30` 留著，改名叫 `WALK_PATH_CAP`，只當請求格式的上限。原因是它會進 OpenAPI 快照，而這段不能動 `client/openapi.json`。所以 `field.walk_max_steps` 設了 `le=30`（見待決 4）。

## 2. 兩個 `FRIENDS_MAX` 改名

- `api/world_field_people.py`：`TOWN_FRIENDS_MAX`（8，一張城鎮圖最多站幾位朋友）。
- `api/world_field_things.py`：`FOOTPRINT_FRIENDS_MAX`（3，一張圖最多畫幾位朋友的腳印）。

## 3. 可達性 BFS 共用

- `content/maps.py` 新增 `grid_bfs()`、`grid_path()`，四方向展開順序固定是北、東、南、西。三份 BFS 原本就都是這個順序，所以結果不變。
- `reachable_from()` 改用 `grid_bfs`。
- `FieldGrid.reachable()`、`FieldGrid.shortest_path()` 包一層，朋友站位與腳印改用這兩個。

## 4. 室外圖索引

`ContentLibrary.outdoor_map(region, location)` 第一次查詢時建好 (區域, 地點) → 室外圖的索引，放在 `outdoor_index`。它是不參與比較的快取，`dataclasses.replace` 之後會是新的空索引。同一個地點有好幾張圖時取 ID 最小的，和原本依 ID 排序掃描的結果一樣。`world.field.outdoor_map` 與 `atlas.cross_gate` 都改用索引。

## 5. `FieldCtx`：收掉 13 個 `noqa: PLR0917`

- `world/field.py` 新增 frozen `FieldCtx(library, world, map, now)`。角色一路會更新，所以另外傳。
- `WatchFn`、`SenseFn` 改成 `(ctx, char, walked)`。
- 改用 `ctx` 的函式：`walk_watch`、`sense_walk`、`_sense_doors`、`_shown`、`_start`、`_take_exit`、`_take_door`、`_event_problem`、`object_status`。
- 改成 keyword-only 參數的函式：
  - `walk(..., *, hooks)`
  - `perceive(..., hidden, *, region, today)`
  - `things_update(library, world, char, grid, *, now, social)`：地圖從 `grid.map` 取，不另外傳
  - `world_presenter._map_view(..., *, in_battle, social, region)`
- **收掉 13 個，世界層與 api 層的 PLR0917 沒有剩下**：`things_update`、`_map_view`、`walk`、`_take_exit`、`_take_door`、`_shown`、`_start`、`walk_watch`、`_sense_doors`、`sense_walk`、`_event_problem`、`object_status`、`perceive`。
- 不屬於這段範圍、沒有動的：
  - `world/solutions.py`：3 個（解法結算）
  - `world/step.py` 的 `_league`：分派表簽名
  - engine、skillgen 裡的那些

## 6. 種子函式、assert

- **種子函式**：`world/rng.py` 新增 `peek()`，`draw()` 也改用它。`visit_for` 用 `peek(...)` 算這一趟的種子，`with_visit` 用 `draw` 推進計數，兩者共用同一個函式，不再假設兩邊算出同一個值。
- **`world/field.py` 的 4 個 assert 改成 `WorldActionError`**：
  - `_walk_path`：沒有位置
  - `walk`：找不到地圖
  - `_cross_region`：跨區出口沒寫區
  - `use_teleport_stone`：傳送石的地圖沒有地點
- `field_enemies.py` 的 2 個 assert 也一起改了：
  - `_start`：沒有目標就不開打
  - `_cut`：沒有位置就當原地
- `perception.perceive` 的 assert 改成 `WorldActionError`。

## 7. 陣容種子改由世界衍生（存檔／重播行為變更）

- **種子算法**：`lineup_seed(world, region, location, spawn)` ＝ `spawn_seed(season_seed, region, location, spawn, generation)`。它用 `derive_seed` 計算，角色段寫 `@<region>/<location>/<spawn>`，串流用新的 `lineup`，計數就是重生世代。所以同一隊、所有角色看到的陣容一樣。
- **角色層不變**：巡邏起點與駐守朝向照舊用這一趟的種子。世界層 tick 是後期的事。
- **重生世代**：`DefeatedSpawn` 新增 `wins`（預設 1），代表被打贏過幾次，也就是現在這一隊的世代；查詢用 `WorldState.spawn_generation()`。
  - 共享清空的隊伍：打贏時 +1。`_clear_if_done` 對齊重生時間時不加。
  - `personal` 的隊伍和不共享的地點（例：村落）：照舊只對自己消失。世界另外記一筆，`respawn_at` 寫當下，所以不會讓這一隊對任何人消失。有這一筆，下一次碰到才會換一批陣容、所有人看到的也一樣。沒有這一筆的話，路徑地點整季都是同一批陣容（見待決 2）。
- **存檔格式（照 6B-2 的做法）**：
  - 世界：`trpg-world/3`，`/1`、`/2` 照讀，舊資料的 `wins` 當作 1。
  - 日誌：`trpg-wlog/7`，`/6` 以前照讀並標成「規則已變、不能重播」，寫回時記 `stale_through`。
  - 6C-5b 與渡口的規則變更也算在這一版號裡。

## 8. 規則測試改用測試專用地圖

- **凍結複本**：`tests/world/fields/` 放了霧渡鎮、渡口石階、霧渡鎮的酒館與鐵匠鋪，是照 2026-11-04 正式內容凍結的複本，檔頭有說明。
- **注入方式**：
  - `tests/world/helpers.with_test_fields()` 把這些地圖注入內容庫。
  - `tests/world/conftest.py`、`tests/api/conftest.py` 的 `field_library` 都改成注入後的版本。
  - 規則測試寫死的座標（入口 (11, 9)、傳送石 (12, 8)、東側出口、渡口石階的抵達格）都照這份，正式內容改版不會連帶弄壞規則測試。
- **正式內容**：結構性質照舊在 `tests/content/` 測，例如每個駐守切得出戰場、出入口配對。
- **保守做法**：沒有把這些測試重畫成更小的地圖。凍結的複本尺寸和正式地圖一樣，但只給測試用。這樣舊測試的座標一行都不用改，風險最小。

## 9. 6C-5b

- **①營火點**（`step.camp_problem`，21.10 第 13 條）：
  - `CLEAR_FIRST_KINDS = {camp, elite_lair, boss}`：這三種地點，連站在營火點上也要等「已清空」才能紮營。這是 6C-5 的改變：原本營地的營火點在敵人還在時就能用。
  - 精英巢穴、Boss 不在營火點上時照舊不能紮營。
  - 其他地點（路徑、村落、遺跡、祭壇……）有巡邏也能紮營。
- **②新手固定戰**：
  - 新增 `FieldSpawn.until_step`，要和 `until_quest` 一起寫，schema 會檢查。
  - 那一步完成（`steps_done` > 那一步的索引），或整個任務完成，這一隊就不再出現。沒寫步驟時照舊，要整個任務完成。
  - 正式內容的三場固定戰都補上了步驟：`ferry_bandits`、`bamboo_wolves`、`terrace_clash`。
- **③走路抵達格的感知**：
  - 從沒有實地地圖的地點用 `travel` 走進有實地地圖的地點時，抵達格（`entry`）也做隱藏入口的感知（`step._sense_arrival`）。
  - 走出口、門、跨區出口抵達，原本就會判。
  - 傳送、撤退、全滅回城抵達都不判（21.10 第 17 條）。

## 10. 渡口算一步（21.10 第 20 條，開發 PM 追加）

- 跨區出口新增 `FieldHooks.cross` 鉤子。`step._cross_fn` 會換到對面那一區，做一次 `travel`（`_travel` 拆出 `_travel_to`），照常擲遇敵、擲事件，事件的步數照常推進。
- 不趕路，過渡口本身不另外花東西。
- 走進渡口圖本來就是一次 `travel`，不用改。
- 其他不變：渡口兩端不能直接傳送，主城任何地方都能休息，從主城挑戰賽季 Boss 輸了留在主城。

## 11. 測試與檢查

- **新增測試**：
  - `tests/world/test_rules_content.py`：`field:` 載入與預設值；沒寫時用預設；不合法的值擋下。
  - `tests/world/test_field_ctx_replay.py`：**重構不改行為**。走一串固定動作：進出酒館、踩傳送石、走出口到渡口石階、碰到駐守、撤退、潛行、走回霧渡鎮。每一步的事件、角色、世界取 SHA-256，遮掉 `lineup_seed`、`format`、`wins`，結果等於用同一支腳本在 `680b2d38`（重構前，舊程式＋舊 content）算出的值 `d2aedac4…`。另一項檢查這串動作確實走過了每一個鉤子。
  - `tests/world/test_field_lineup_seed.py`：
    - 同一隊、兩個角色，這一趟的種子不同，但陣容一樣；
    - 兩個角色走路碰到時記下的 `lineup_seed` 一樣；
    - 打贏後重生世代 +1、陣容換一批；別隊、別季的種子都不同；只對齊重生時間時世代不變；
    - `trpg-world/2` 照讀；`trpg-wlog/6` 標成規則已變。
  - `tests/world/test_field_6c5b.py`：
    - 營火表格：6 種地點 × 站不站在營火上 × 清空與否，15 列；
    - 固定戰照步驟消失的表格（5 列）；
    - `until_step` 一定要配 `until_quest`；
    - `travel` 抵達格 3 格內有隱藏入口就判定（表格 2 列）；
    - 傳送抵達不判。
  - `tests/world/test_capital.py`：新增**渡口重播測試**。從霧渡鎮走進渡口、再走進灰渡口，各有一次 `traveled`、`encounter_check`、`event_check`，`travel` 計數 +2，補給不變，重播兩次逐字一致。原本「不擲骰」的斷言改成擲 1 次。
  - `tests/content/test_field_spots.py`：`until_step` 要是那個任務的步驟。
- **改到的既有測試**：
  - 常數改成數字或規則；
  - 版號 /3、/7；
  - 不共享地點打贏後，世界只記重生世代；
  - `object_status` 改傳 `FieldCtx`。
- **結果**：
  - `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8`：4206 passed、1 skipped
  - `ruff check`、`ruff format --check`、`mypy src`（511 檔）、`lint-imports`（13 kept）：通過
  - `trpg content check`：通過
  - swamp 種子 7 重播：`trpg battle replay` 驗證通過（88 個動作、313 個事件，和 6D-5 相同）
  - 沒有跑全量測試與模擬。

## 12. 動到的檔案

- `content/world/rules.yaml`；`content/world/fields/cloud_ridge/{ferry_steps,bamboo_path,rain_terraces}.yaml`（`until_step`）
- `src/trpg/content/`：`world_rules.py`、`maps.py`、`library.py`、`fields.py`
- `src/trpg/world/`：`field.py`、`field_enemies.py`、`field_things.py`、`field_actions.py`、`battlefield.py`、`perception.py`、`rng.py`、`state.py`、`save.py`、`step.py`、`atlas.py`、`__init__.py`
- `src/trpg/api/`：`world_field_people.py`、`world_field_things.py`、`world_field_view.py`、`world_presenter.py`
- `tests/world/`：`fields/`（新）、`helpers.py`、`conftest.py`，以及上面列的測試；`tests/api/conftest.py` 與兩個朋友測試

## 13. 待 PM 決定

**規則類**（照最保守做法先做了，需要確認）：

1. **Boss 地點的營火點**：Boss 不在 `battle.clear_kinds` 裡，不會被寫成「已清空」。所以照 21.10 第 13 條，Boss 地點的營火點實際上永遠不能用。目前正式內容沒有 Boss 地點畫營火點，沒有影響。要不要讓打贏 Boss 也寫「已清空」？
2. **只對自己消失的隊伍也記重生世代**（`personal`、不共享清空的地點）：打贏後世界記 `wins` +1，`respawn_at` 寫當下，不會讓它對任何人消失。這樣下一次碰到換一批陣容，所有人看到的一樣。如果不記，路徑地點整季都是同一批陣容；原本是每一趟換一批。需要確認這個解讀。
3. **營地的營火點**：6C-5 原本「敵人還在也能用」，現在要先清空，照 21.10 第 13 條字面做。冬湖帳篷旁的營火要先清空才能用，和第 13 條的例子一致。

**原型與解讀類**（照預設做了）：

4. **`walk_max_steps` 上限 30**：請求格式的上限要跟著 OpenAPI 快照走，這段不能改 `client/`，所以規則值最大只能到 30。要放寬時，同時改 `WALK_PATH_CAP` 並重產 OpenAPI。
5. **凍結的測試地圖**：用的是正式地圖的複本（同尺寸），不是重畫的小地圖。之後正式霧渡鎮改版，規則測試不受影響；如果要改用更小的地圖，可以排進之後的整理段。
6. **重構前後的雜湊**：比對雜湊綁著真的雲嶺地點圖、事件與規則內容。之後這些內容改了就要重算，在 `680b2d38` 上用同一支腳本跑一次就好。
