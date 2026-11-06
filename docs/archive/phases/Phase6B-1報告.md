# Phase 6B-1 完成報告：實地地圖資料格式與驗證

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 0 節、第 1 節 6B-1 列、第 2 節；`docs/design/21-探索地圖與城鎮.md` 21.2、21.3、21.5、21.6、21.10；`docs/design/18-雲嶺內容.md` 18.3。
> 沒有改引擎（`src/trpg/engine/`），也沒有改 `world/` 的狀態與動作。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| schema 與驗證 | `src/trpg/content/fields.py`（`FieldMapDef`、`field_map_report()`、`field_map_problems()`、`field_progress()`） |
| 共用驗證工具 | `src/trpg/content/maps.py`：抽出公開函式 `grid_rows`、`grid_shape_problems`、`passable_grid`、`reachable_from`、`placement_problems` 與 `TileSource` 協定；`MapDef`、`check_map` 改呼叫它們，錯誤訊息一字不變，舊的私有名稱 `_passable_grid`、`_reachable_from` 保留成別名 |
| 載入 | `src/trpg/content/library.py`：`world/fields/<region>/*.yaml`（室外）與 `world/fields/<region>/interiors/*.yaml`（室內）；`ContentLibrary` 新增 `field_maps`、`field_warnings`、`field_pending` |
| `trpg content check` | `src/trpg/cli/main.py`：印出「實地地圖：雲嶺 x／18、灰燼荒原 y／18（另有室內圖 n 張）」、警告、待補 |
| 草稿 | `content/world/fields/cloud_ridge/mist_ferry.yaml`（24×18）、`ferry_steps.yaml`（20×12 路徑圖）、`interiors/mist_ferry_tavern.yaml`、`interiors/mist_ferry_smithy.yaml`（各 10×8） |
| 測試 | `tests/content/test_fields.py`（52 項，表格測試）；`tests/cli/test_cli.py` 的 content check 測試加 3 行斷言 |

## 2. 格式重點

- 地形、高低差、物件、表面的寫法和 `MapDef` 一樣，驗證也是同一套函式，所以 6C-2 可以直接從實地地圖切出 12×12。
- **出口** `{id, at: [[x,y],…], to, arrive, region?}`；ID 慣例 `to_<目的地點>`，所以對面回來的出口一律叫 `to_<本地點>`。
- **門** `{id, at, to, hidden_until?}`：`to` 是本地點的室內圖，或相鄰的隱藏地點。門沒有 `arrive`：室內圖與隱藏地點那一側用出口回來，出口的 `arrive` 指向門的 ID。
- **渡口兩種寫法都支援**（2.6、Q2）：
  - 渡口是路徑圖（預設，21.10 第 1 條）：`ashen_ferry` 自己有地圖，尾端出口寫 `region: ashen_waste`。
  - 渡口只是出口：`ashen_ferry` 沒有地圖，霧渡鎮直接放一個 `region: ashen_waste` 的出口，這個出口同時算作「霧渡鎮－渡口」那條連線。
  - 兩種寫法都有測試，包含跨區配對（`ashen_ferry` ↔ `ash_ferry`）。
- 驗證結果分三類：
  - **錯誤**：載入失敗，和其他內容一樣丟 `ContentError`。
  - **警告**：尺寸、傳送石數，不影響通過。
  - **待補**：對面還沒畫的出口與門，不是錯誤。

## 3. 驗證涵蓋（2.3 逐條）

1. 地形與物件 ID 在表裡；網格與 `size` 一致；出口格在邊緣上；所有座標都在地圖內；出口、門、傳送石、入口、NPC 不重疊。
2. 一條連線＝一對出口：每條連線都要有出口；`arrive` 必須互指；沒有連線的出口算錯；同一個目的地的出口不能重複。隱藏地點用門，門要寫 `hidden_until: reveal`；用出口通往隱藏地點也算錯。
3. 雲頂觀只能從源晶裂痕進入：連線限制已經擋住，另外再加一條：Boss 地點不能有傳送石（錯誤）。裂界門不是地點，畫不出來。
4. 從 `entry` 走得到每個出口格、門、傳送石，以及 NPC 與設施的旁邊。沿用 `passable_grid`、`reachable_from`，一步最多往上 `max_climb_height` 層。
5. 尺寸照 21.3 的種類範圍檢查，超出只警告。
6. 傳送石每區 2～3 個、城鎮 1 個，不符合只警告；傳送石 ID 在全部地圖裡不能重複（錯誤）。
7. 還沒畫的地點不算錯。`content check` 目前印出：雲嶺 2／18、灰燼荒原 0／18、室內圖 2 張；警告 1 項（雲嶺傳送石 1 個）；待補 3 項（往竹林小徑、獵戶小屋、渡口）。

另外做了這些檢查：
- NPC 必須是本區的人設卡（這區沒有人設卡檔時不檢查），而且人設卡上的地點就是這張地圖的地點（室內圖算所屬的地點）。
- 室內圖只能有回到所屬地點的出口，不能有門或傳送石；所屬地點必須已經有實地地圖。
- 檔案位置：室外圖的檔名等於 `location`，室內圖的檔名等於 `id`，資料夾名稱等於 `region`。

## 4. 測試與檢查結果

- `UV_NO_SYNC=1 uv run pytest -q tests/content -n 8`：2242 passed。
- `tests/content/test_fields.py`：52 passed。
- `tests/cli/test_cli.py -k content_check`：4 passed。
- `ruff check .`、`ruff format --check .`、`mypy src`（494 檔）、`lint-imports`（13 kept）都通過。
- `uv run trpg content check`：通過。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。
- 複雜度：沒有新增 `# noqa`。

## 5. 待 PM 決定（都已照最保守的做法做完）

1. **新增的欄位**（規格沒列）：
   - `FieldMapDef.name_zh`：選填，室內圖用，例如「霧渡鎮酒館」。
   - `FieldMapDef.layout`：選填，尺寸檢查用。省略時依地點種類推定：town→town、gate→path、secret／elite_lair→lair、boss→boss，其他→site。渡口石階的種類是 camp，但要畫成路徑圖，所以明寫 `layout: path`。
   - `FieldExit.region`：跨區出口才寫。
2. **尺寸範圍**（數值類，只警告）：`fields.LAYOUT_SIZES`，比較長邊與短邊，橫放、直放都可以。
   - 路徑 16～24 × 8～14；營地類與小鎮 20～28 × 14～22；巢穴與秘境 12～20 × 10～18。
   - Boss 前廳 10～14 × 6～10：Boss 地點的實地地圖我解讀成「前廳」，Boss 戰照舊用 20.6 的 Boss 地圖。
   - 主城 28～36 × 20～28；室內 8～12 × 6～10。
3. **「走得到」的解讀**：
   - 出口的每一格都要走得到。
   - NPC 要站得上，而且旁邊有一格走得到。
   - 設施本身或旁邊走得到就可以，所以設施可以放在建築的牆或櫃檯物件上。
   - `spawns` 與巡邏點要站得上；`campfires`、`event_spots`、`situation_objects` 只檢查在地圖內，其他留給 6C-5。
   - `spawns.group` 只檢查 ID 格式，不比對遭遇表（6C-1 再接）。
4. **Boss 地點不能有傳送石**是錯誤（理由：雲頂觀只從源晶裂痕進入）；入口不能和出口或門重疊也是錯誤。室內圖不能有門與傳送石，之後如果要地下室之類的再放寬。
5. **霧渡鎮的設施怎麼放**：
   - 鎮上：商店（柳掌櫃的攤位）、懸賞板（`notice_board`）、導師堂（`mentor`）、傳送石。
   - 酒館室內：酒館與雇用（`hire`）。
   - 鐵匠鋪室內：鐵匠（石師傅）與附魔台（21.5「鐵匠鋪含附魔台」）。
   - 18.3 寫霧渡鎮有「導師」，但導師 NPC 青崖道長的人設卡在青霧觀山門，所以導師堂只放設施、不放 NPC。請確認霧渡鎮要不要有導師設施。
6. **地形**：沒有水的地形，霧河先用深淵（`chasm`）加木棧橋（`wooden_bridge`）代替；建築用牆。0.2 第 6 條說不新增地形或物件 ID，外觀等 6B-ART1。
7. **給 6B-2 的提醒**：
   - 從出口過去會出現在對面出口的格子上，站上出口格就換圖，所以 6B-2 要決定是「站上出口格」還是「從出口格往外走一步」才觸發，免得一到就被送回去。這段只驗證格式。
   - `entry` 已保證不在出口或門上。

## 6. 過程中修正

- 第一次跑 `tests/content` 時，`test_without_world_event_files` 失敗：這個測試會刪掉 `world/npcs/`，而草稿裡的 NPC 因此比對不到人設卡。
- 修正：某一區沒有 NPC 人設卡檔時，就不檢查那一區的 NPC（和其他選填內容的處理方式一致）。有人設卡檔時照樣嚴格檢查。
- 修正後重跑，全部通過。
