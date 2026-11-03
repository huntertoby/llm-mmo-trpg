# Phase 6B-2 完成報告：世界狀態加座標與走路動作

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 0 節、第 1 節 6B-2 列、第 3 節；`docs/design/21-探索地圖與城鎮.md` 21.2、21.9、21.10；`Phase6B-1報告.md` 第 5 節。
> 沒有改引擎（`src/trpg/engine/`），也沒有做前端畫面（6B-3）、敵人與就地開打（6C）。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| 位置模型 | `world/state.py`：`FieldPos`（`map`、`x`、`y`、`facing`）、`CharacterState.field`、`CharacterState.teleport_stones`；`CHAR_FORMAT` 升成 `trpg-char/2` |
| 動作與事件 | 新檔 `world/field_actions.py`：`WalkAction(path)`、`UseTeleportStoneAction(to)`；事件 `walked`、`field_entered`、`teleport_stone_unlocked`、`teleport_stone_used`。已加進 `WorldAction`、`WorldEvent` |
| 走路邏輯 | 新檔 `world/field.py`：`placed`（放到 `entry`）、`stale_field`、`walk`、`use_teleport_stone`、`arrival`（抵達格）、`field_grid` |
| 接上世界動作 | `world/step.py`：`walk`、`use_teleport_stone` 的處理；`travel` 在有實地地圖的地點拒絕；其他動作換了地點時清掉舊位置 |
| 存檔與日誌 | `world/save.py`：`WLOG_FORMAT` 升成 `trpg-wlog/2`，新增 `read_log`／`WorldLog`；舊格式的處理見第 3 節 |
| 伺服器 | `api/world.py`（`WorldStore` 記下舊紀錄到哪一筆）；新檔 `api/world_field_schemas.py`、`api/world_field_view.py`；`WorldView.field`；動作端點收 `walk`、`use_teleport_stone`；事件句子 |
| 季末重置政策 | `server/season_policy.py`：`field`、`teleport_stones` 歸為數值類，和 `region`、`location`、`revealed` 一樣（架構測試要求每個存檔欄位都要分類） |
| OpenAPI | `client/openapi.json`、`client/src/api/schema.d.ts` 重產；前端只更新了產生出來的型別 |
| 測試 | `tests/world/test_field.py`（34 項）、`tests/api/test_world_field_api.py`（3 項）；`tests/world/test_save.py` 的版號與壞格式表格 |

## 2. 規則怎麼落實（對照 3.1～3.4）

**位置**
- `field` 一定屬於所在地點的實地地圖或它的室內圖。
- `field` 是 `None` 的情況有兩種：舊存檔，或所在地點沒有實地地圖。
- 需要座標時（世界畫面、`walk`、`use_teleport_stone`）由 `placed()` 放到 `entry`，這一步不寫進日誌。重播時 `walk` 也會先呼叫 `placed()`，所以算出來的結果一樣。
- 其他動作換了地點（撤退、全滅回城、`travel`、跨區 `teleport`）時，`world_step` 會把舊位置清成 `None`，之後同樣放到 `entry`。這只影響有 `field` 的角色，5A～5F 的既有行為不變。

**走路**
- 每一步的檢查：
  - 四方向相鄰。
  - 可站：沿用 `passable_grid`，所以木棧橋這類 `over_chasm` 物件可以走，`blocks_move` 物件不行。
  - 往上最多 `max_climb_height` 層。
  - 不是 NPC 站的格子。
  - 不是還沒發現的隱藏門。
- 一次最多 30 格，由 pydantic 檢查，超過時 API 回 422。
- 有未處理的遭遇時拒絕。
- 走格子不抽亂數，也不動時間、補給、`event_steps`（Q3）。
- 中途碰到出口、門或傳送石就停在那一格並觸發，後面的路徑不走（不算錯）。

**出口**
- 呼叫原本的 `_travel(to)`：檢查、遇敵擲骰、`roll_event`、機遇提示、`_perceive` 都沿用，擲骰順序和以前一樣，`hasten` 一律 false。
- 抵達位置：放在對面 `arrive` 出口的第 i 格往內一格（i 超出時取最後一格）。那一格不能站時，依和 i 的距離試其他格；都不行就站 `entry`。抵達格不會是出口、門或傳送石。
- 目的地點還沒有實地地圖時 `field` 是 `None`，照舊用 `travel`。

**門**
- 通往室內圖時不擲骰、不扣時間，`location` 不變。
- 通往隱藏地點時算一次 `travel`。
- 從室內圖或隱藏地點回來時，站在門外一格：照南、北、西、東的順序，取第一個可站、而且不是出口、門或傳送石的格子。

**傳送石**
- 踩上就解鎖，不自動傳送。
- `use_teleport_stone` 的條件：
  - 要站在傳送石上。
  - 目標已解鎖，而且不是同一顆。
  - 跨區時要去過那一區的小鎮（照 `teleport` 的規則）。
- 傳送不擲骰；傳到城鎮會記下 `visited_towns`。

**`travel`**
- 所在地點（含它的室內圖）有實地地圖時拒絕，訊息是「這裡有實地地圖，請走到出口」。

**重播**
- 日誌記整串路徑，重播逐格重算。
- 測試的兩條路線，各重播兩次，結果和實際玩的逐字相同：
  - 無遇敵：霧渡鎮 → 傳送石 → 渡口石階走一圈 → 回霧渡鎮。
  - 每步遇敵：霧渡鎮 → 渡口石階遇敵 → 撤退 → 進出酒館。

**API**
- `WorldView.field` 包含：地形與高低差（逐格，欄位名稱同戰鬥的 `TileView`）、物件（同 `ObjectView`，ID 是 `o<x>_<y>`）、出口、門（隱藏的不給）、傳送石（含是否解鎖）、NPC（含名字）、設施、自己的位置與朝向。
- 新動作走既有的 `require_world_access` 路由依賴，6S-1 的擁有者檢查照樣套用。

## 3. 存檔格式

**`trpg-char/1` → `trpg-char/2`**
- 新增的都是選填欄位，舊檔照讀。`CharacterState` 的 before validator 直接換版號，`loads_char` 也接受舊版號。
- 舊角色的 `field` 是 `None`，之後放到 `entry`。

**`trpg-wlog/1` → `trpg-wlog/2`**
- 舊紀錄是舊規則寫的：當時有實地地圖的地點還能 `travel`，現在會被拒絕，所以標成「規則已變、不能重播」，比照 `LOG_FORMAT` 遞增時的處理。
- 做法：
  - 舊日誌照讀，敘述查詢、上線人數照常運作。
  - 下一次寫回時，標頭改成 `{"format": "trpg-wlog/2", "stale_through": <最後一筆舊紀錄的序號>, "stale_zh": "規則已變、不能重播"}`。
  - `read_log()` 回傳 `WorldLog.stale_through`。
- 檔案還是同一個 `log.jsonl`，所以 `layout.py` 與季末重置不用改。
- `WORLD_FORMAT` 沒有變。

**CLI 快照與 fixture**
- 沒有因為格式變更而失效的。`tests/api` 的 client fixture 測試通過，沒有重產。

## 4. 測試與檢查結果

- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/test_architecture.py tests/server -n 8`：全部通過（world＋api＋architecture 共 1355 項加 1 項 skip；server 與 architecture 共 89 項）。
- `tests/world/test_field.py` 34 項、`tests/api/test_world_field_api.py` 3 項。
- `ruff check .`、`ruff format --check .`、`mypy src`（498 檔）、`lint-imports`（13 kept）都通過。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。

**新增的 `# noqa`**（守則 12）：
- 三個 `# noqa: PLR0917`，都在 `world/field.py`，分別是 `walk`、`_take_exit`、`_take_door`。
- 理由：它們要接世界動作處理的同一組參數（`library`、`world`、`char`、`action`/位置、`now`），外加呼叫者傳入的 `travel` 函式。傳入 `travel` 是為了避免 `field` ↔ `step` 循環匯入。
- 複雜度（C901／PLR0912／0915）沒有新增 noqa。

## 5. 待 PM 決定（都已照最保守的做法做完）

**規則類**

1. **既有測試改用沒有實地地圖的內容庫**：
   - 做法：`tests/world`、`tests/api` 的 `library` fixture 改成拿掉 `field_maps` 的內容庫（`tests/world/helpers.py` 的 `without_fields`）；實地地圖的測試用新的 `field_library`。
   - 原因：照規格，霧渡鎮與渡口石階有實地地圖之後，原本 50 項從霧渡鎮 `travel` 的測試會被拒絕。
   - 那些測試驗的是 5A～5F 的地點移動、事件、戰鬥規則，在沒有地圖的地點仍然成立。
   - 請確認這個做法可以接受。
2. **6B-3 之前，正式遊戲在霧渡鎮與渡口石階走不了**：前端還是點地點送 `travel`，伺服器會拒絕。6B-2 和 6B-3 最好一起合併，或者合併 6B-2 時先不上線。
3. **傳送石每次踩上都停下**：規格寫「碰到…傳送石就停在那一格」，已解鎖的也停。如果城裡走路被打斷太煩，可以改成只在第一次解鎖時停。
4. **NPC 站的格子不能走**：規格只寫了地形、高低差、物件，NPC 擋路是我加的保守做法。6B-1 的驗證不保證 NPC 不會擋住通道，目前兩張草稿沒有被擋住的情形。
5. **跨區出口**（`region` 和本區不同）：目前拒絕，訊息是「跨區的出口還沒開放，請用傳送」。現有草稿沒有這種出口（往灰燼荒原的渡口在雲嶺區內），渡口尾端進荒原要等 6D-1 再接。
6. **用 `travel` 進入有地圖的地點時**（從還沒畫地圖的地點過來），站 `entry`，不站「朝向出發地點的那個出口」。規格只定義了舊存檔放 `entry`，這種情況我照同樣的做法處理。
7. **門外一格**：照南、北、西、東的順序找第一個可站格。現有草稿的門外都只有一格可站，沒有歧義。
8. **在同一張地圖裡走動不清營火狀態**（`camped_at`）：營火是以地點為單位；踩出口換地點時，照原本的 `travel` 清掉。

**數值／解讀類**

9. **事件句子**：走格子不出句子（21.7 文字減量），進室內出「走進霧渡鎮酒館。」，傳送石解鎖、使用各一句，踩出口照舊出「走到…」。
10. **`use_teleport_stone` 抵達時站在目標傳送石上**（不是旁邊一格）。傳送過去不算「走上去」，所以不會觸發停下或解鎖；可以馬上再傳回去。
