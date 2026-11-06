# Phase 6C-R3 報告：審查整理③（存檔與效能）＋實地敵群外觀

規格：`docs/phases/Phase6計畫.md` 第 1 節 6C-R3 列（含「另含」的敵群外觀）；`docs/phases/Phase6C-R2報告.md` 待決 6。
開工時已 `git merge main`（含 6C-R2，沒有衝突）。不動引擎。沒有新增相依。

## 1. 世界日誌標頭加 `rules_key`

- `src/trpg/world/save.py`：
  - `log_rules_key(library)` ＝ `戰鬥紀錄版號|規則包雜湊|內容 digest 前 16 碼`，做法比照 `server/league.py` 的 `rules_key`。
  - `content_digest(library)` 是確定性的 SHA-256，不用內建 `hash()`。內容包含三部分：
    - 全部內容檔：沿用 `roguelite.save.ruleset_hash`，依相對路徑排序、用排序鍵 JSON。
    - 內容庫裡的實地地圖：依地圖 ID 排序。
    - 大世界規則。
  - 後兩項另外算，是因為測試用 `dataclasses.replace` 換掉的內容不會進 `files`。
- 標頭新增 `rules_key` 欄位，鍵的順序固定（`dumps_log_header`）。格式版號維持 `trpg-wlog/7`：舊程式讀新標頭時會忽略多出的欄位。版號機制保留，只用在格式變更。
- 讀檔（`WorldStore.entries`）時，如果標頭的 `rules_key` 和目前的不同或沒有記，`stale_through` 就設成最後一筆，處理方式同現行的「規則已變、不能重播」。下一次寫入時標頭會重寫成新的鍵。
- 規則鍵算一次約 0.2 秒，所以依內容庫物件快取（`api/world.py` 的 `_rules_key_of`）。

## 2. 日誌改成只 append

- 每個動作只在檔尾附加一行（`append_log_line`：附加、flush、fsync）。
- 只有以下情況會用 `write_atomic` 重寫整份：檔案不存在、標頭改變（`stale_through` 或 `rules_key` 變了、舊格式升版）、上次讀到不完整的最後一行。
- **寫到一半中斷**：最後一行沒有換行，代表 append 被打斷。讀檔時丟掉那一行並記 warning。那個動作的角色存檔排在日誌之後才寫，所以兩邊一致。接著整份重寫一次。
- 舊檔照讀（`trpg-wlog/1`～`/6` 照舊標成 stale）。
- 測試確認 append 寫出的檔和 `dumps_log` 整份重寫的結果逐字相同，而且標頭沒變時完全不會整份重寫。

## 3. 足跡索引、留言快取、`prepare_battle` 快取

- **足跡**：拿掉 `_peek`／`_peeks`，以及每次請求都要做的 glob＋stat。
  - 改成記憶體索引 `_visits`：角色 ID →（名字, 去過的地點＋目前位置）。
  - 第一次用到時掃一次角色資料夾建立索引，之後由 `_save_char` 更新。
  - 季末重置（`_forget`）時清掉。
- **朋友（城鎮影子）**：本來就是從世界快照的影子讀，沒有掃檔，不用改。
- **留言**：`LocationNoteStore` 加記憶體快取，寫入時更新。因為管理腳本 `scripts/location_notes.py` 會在伺服器執行中直接改 `notes.json`（`tests/api/test_notes.py::test_script_list_and_delete`），快取另外比對檔案的修改時間與大小：每次一個 stat，不讀檔。
- **`prepare_battle`**：新增 `WorldStore.prepared_battle(char)`，依「角色 ID＋同一個角色存檔物件＋同一個內容庫」快取。角色存檔是不可變物件，同一個物件就代表同樣的輸入。世界畫面的遭遇面板改用它（`world_view(..., prepare=...)`）；開戰（`WorldStore.battle`）照舊重算。

## 4. 靜態 tiles 快取

沒有退回整張 tiles 的做法，照規格做。

- **新端點** `GET /api/world/fields/{map_id}?h=…`（`FieldTilesView`）：回傳 `map_id`、`hash`、`width`、`height`、`tiles`。
  - `hash` 是地形排序鍵 JSON 的 SHA-256 前 16 碼，內容一樣就一樣。
  - `h` 等於目前的雜湊時，回 `Cache-Control: private, max-age=86400, immutable`；雜湊不同或省略時照樣回傳目前的地形。
  - 地圖不存在時回 404。
  - 端點掛在同一個 router 上，帳號檢查和其他大世界端點相同。
- **靜態地形的 `walkable`**：「發現才出現」的隱藏門一律當成還沒發現（不可站）。這和沒發現的角色原本看到的一樣，不會洩漏門的位置。這個角色已發現的隱藏門放在 `FieldView.open_cells`。
  - 測試確認「靜態地形＋`open_cells`」等於原本每個角色各自算的地形。
- **`WorldView.field`**：`tiles` 變成空的，另外帶 `tiles_hash`、`open_cells` 和動態部分。
  - 只有世界畫面的端點這樣做（`world_view(..., inline_tiles=False)`）。
  - 直接呼叫 `field_view()` 時預設仍內嵌 tiles，既有的 Python 測試不受影響。
- **前端**：
  - 新增 `client/src/world/fieldTiles.ts`：依雜湊做記憶體快取，套上 `open_cells`。
  - `client/src/api/client.ts` 裡所有回傳世界畫面的請求（含 `worldBattle` 的 `world`）都先補上地形。
  - 其餘畫面不動：`field.tiles` 補完後和原本一樣。
- OpenAPI 重產（`client/openapi.json`、`client/src/api/schema.d.ts`）。三個前端測試的 FieldView 假資料補上 `tiles_hash`、`open_cells`。

## 5. 實地敵群外觀

- `FieldEnemyView.look`（`FieldHeroView`，欄位同戰鬥 `UnitView`：`template_id`、`doll_look`（含異形的 `creature`）、`weapon_id`、`weapon_class`、`race_look`、`equipment`）。
  - 帶頭單位＝陣容第一名；沒有敵方時用第三方第一名。範本用 `enemy_catalog().template(...)`，裝備用 `loadout_of`。
- 前端 `fieldModel.ts` 的 `enemyUnit` 套用 `withLook`，敵方也帶種族外觀。異形照戰鬥的畫法畫（`unitSprite.creatureOf` 讀 `doll_look.creature`）。`look` 是 `null` 時照舊用範本 ID。

## 6. 重播雜湊測試改用測試專用內容（6C-R2 待決 6）

- `tests/world/frozen_replay/*.json`：凍結 2026-11-04 的正式內容，共約 65 KB。內容有：
  - 大世界規則
  - 雲嶺的地點圖
  - 遭遇表
  - 事件骨架、事件規則
  - 任務
  - 主角範本
- `tests/world/test_field_ctx_replay.py` 用 `frozen_library()` 在凍結的實地地圖之外，再換上這些片段。
- 凍結後的雜湊仍等於 `BEFORE_6CR2`，代表凍結內容和正式內容相同。
- 新增 `test_replay_ignores_official_world_content`：把正式內容的規則、遭遇表、事件改掉，雜湊不變。
- 還綁著正式內容的部分：戰鬥規則包（地形、物件、核心數值）與敵人範本（陣容名稱），見待決 6。

## 7. 測試與檢查

- 新測試：
  - `tests/api/test_world_store_r3.py`（11 個）：
    - 內容 digest 確定性、標頭記規則鍵
    - 規則鍵不一致或沒記時標 stale、鍵相同時保持可重播
    - append 和重寫等價、stale 時標頭只重寫一次、不完整最後一行
    - 索引在存檔後更新、不再掃資料夾
    - 留言快取跟著寫入與外部修改
    - `prepare_battle` 快取
  - `tests/api/test_world_field_r3.py`（7 個）：
    - tiles 快取與雜湊跟著內容
    - 靜態地形＝沒發現隱藏門的角色的地形
    - 已發現的隱藏門進 `open_cells`
    - 端點與快取標頭、404
    - 敵群外觀欄位、異形 `creature` 帶到 `doll_look`
  - `client/src/world/fieldTiles.test.ts`（5 個）與 `fieldModel.test.ts` 新增 2 個：同一個雜湊只下載一次、雜湊變了重新下載、`open_cells`、敵群外觀（異形、人形＋種族外觀、沒有外觀）。
- 結果：
  - `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8 -x`：4225 通過、1 略過。
  - `ruff check`、`ruff format --check`、`mypy src`（511 檔）、`lint-imports`（13 個契約）全過。
  - 前端：`tsc --noEmit` 0 錯；`vitest run src/world src/api src/render` 74 檔、846 個通過；`vite build` 成功（只有原本就有的 chunk 大小警告）。
  - swamp 種子 7 重播：通過（88 個動作、313 個事件，和 6C-R2 相同）。
- 沒有在瀏覽器實際開畫面看敵群外觀與地形載入（只有單元測試）。

## 8. 效能小量測

量測腳本：`C:\Users\tobby\AppData\Local\Temp\claude\F--PythonProject-LLM-MMO-TRPG\1d5765dc-41d9-4065-87b3-f552cc36f094\scratchpad\perf_r3.py`。

- 條件：TestClient、正式內容、200 個其他角色存檔，模擬伺服器重啟後的請求，每項 30 次取中位數。
- 舊版：用同一支腳本、`PYTHONPATH` 指到 `main` 的 `src`／`content`。

| 項目 | 6C-R2（main） | 6C-R3 |
|---|---|---|
| 世界畫面 `GET /characters/{id}`（200 個角色存檔，重啟後第一次） | 800 ms | 798 ms（掃一次建索引） |
| 世界畫面之後每次 | **16.0 ms** | **8.7 ms** |
| 世界畫面回應大小 | 85,430 B（霧渡鎮 432 格內嵌） | 52,193 B（地形另取一次 33,368 B，之後依雜湊快取） |
| 走一格（日誌 2000 筆＋200 個角色） | **28.5 ms**（整份重寫 224 KB） | **13.2 ms**（append 一行） |

重啟後第一次請求兩版差不多，因為都要讀 200 個存檔。差別在之後：舊版每次都要 glob＋stat 200 個檔、讀留言檔，有遭遇時還要重跑 `prepare_battle`；新版都走記憶體。

## 9. 動到的檔案

- 後端：
  - `src/trpg/world/save.py`
  - `src/trpg/api/world.py`
  - `src/trpg/api/world_presenter.py`
  - `src/trpg/api/world_field_view.py`
  - `src/trpg/api/world_field_schemas.py`
  - `src/trpg/api/routes/world.py`
  - `src/trpg/server/notes.py`
- 前端：
  - `client/src/api/client.ts`
  - `client/src/api/types.ts`
  - `client/src/api/schema.d.ts`
  - `client/openapi.json`
  - `client/src/world/fieldTiles.ts`（新）
  - `client/src/world/fieldModel.ts`
  - 三個測試假資料
- 測試：
  - `tests/api/test_world_store_r3.py`（新）
  - `tests/api/test_world_field_r3.py`（新）
  - `tests/api/test_world_field_api.py`
  - `tests/world/test_field_ctx_replay.py`
  - `tests/world/frozen_replay/`（新）

## 10. 待 PM 決定

**原型與解讀類**（照最保守的做法做完了）：

1. **內容 digest 涵蓋全部內容檔**，不只實地地圖與 `world/`。單位、技能、物品也會影響世界步驟（戰鬥、成長），所以任何內容變更都會讓舊日誌標成「規則已變、不能重播」。如果要只看 `world/` 底下的內容，改 `content_digest` 一處就好。
2. **6C-R3 以前寫的 `/7` 日誌沒有記 `rules_key`**：第一次載入時整份標成 stale（無法確認當時的規則）。
3. **足跡索引在第一次用到時建立**，等於伺服器啟動後掃一次。伺服器執行中如果有別的程式直接改角色檔，索引看不到；原本依修改時間會看到。目前沒有這種寫入者。留言檔有管理腳本會直接改，所以留言快取另外比對修改時間。
4. **`prepare_battle` 快取只用在畫面上**，開戰照舊重算（最保守）。
5. **地圖不存在的 404** 借用 `WorldCharacterNotFoundError`（已經對應到 404），訊息是「找不到實地地圖」。要的話之後可以另開一個錯誤類別。
6. **重播雜湊測試仍綁著戰鬥規則包與敵人範本**。這兩樣要凍結就得複製整個規則包，所以沒有做；改了的話照 6C-R2 的做法重算雜湊就好。
7. **敵群外觀沒有套用精英詞綴的外觀變化**：只用範本的 `doll_look`，精英照舊靠 `tags: ["elite"]` 放大加光。戰鬥中套用詞綴後的外觀是否不同，沒有比對。
