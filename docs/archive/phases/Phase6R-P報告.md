# Phase 6R-P 完成報告：後端整理段

來源：開發 PM 的 Phase 6 後段 Python 審查摘要（排進 6R-P 的 8 項）。沒做 Phase 7 前置的兩項（`SlideOverride` 泛化、任意 Action 的分支推演）。

## 逐項

| # | 做了什麼 | commit |
|---|---|---|
| 1 | `PathPreviewOut` 加 `stops: tuple[XY, ...]`（必填，照 `PathPreview.stops`）。`worst_stop` 的說明改成實際語意：第一個與 `stop` 不同的停點。重產 `client/openapi.json`、`client/src/api/schema.d.ts`。前端沒改 UI，只在 `pathPreview.test.ts` 的 `preview()` 夾具補 `stops`，讓型別能過。 | 71679248 |
| 2 | `field_map_report`／`field_map_problems` 加選填參數 `quest_steps`（區域 → 任務 ID → 步驟 ID）。`None` 表示不檢查，和 `npcs` 一樣。新的 `_gate_problems` 檢查出口 gate：`gate.quest` 要是地圖**同區**的任務（和 `exit_open` 用 `found.region` 找任務一致），`gate.step` 要是那個任務的步驟。`library._load_world_fields` 從 `world_quests` 傳進去，所以載入正式內容時就會檢查。現有內容（crystal_rift 的霧牆）通過檢查。 | 4b4d7709 |
| 3 | `WORLD_RULES_VERSION` 的 docstring 補上 1～6 每一版的說明，和行內註解一致。對照 git 歷史後，修正原本寫錯的「2＝6E-1／6E-3」：6D-R2 和 6E-1／6E-3 兩條分支各自從 1 升到 2，合併時取 3。另外加一段「沒有升版的規則改動」，寫明 6P-2 為什麼不升版。 | 4facaed2 |
| 4 | `_merge`／`_fold`／`_paired`／`_widen` 合成 `_merge_all` → `_fold` → `_combine`：從最少後果開始，依序併入各分支。`_combine` 的最小值改用 `other.amount_min`，`None` 時取對方的值。PathEvent 的 `amount_min` 說明也照著更新。 | 97fb2ecb |
| 5 | `walk_max_steps` 的預設值統一用 `FieldRules().walk_max_steps`：`FieldView.walk_max_steps` 的預設值、`_walk_max_steps` 沒有世界規則時的回退都從這裡取。OpenAPI 不變，預設值仍是 30。 | 2f6dec8e |
| 6 | `OBJECT_LOOKS = get_args(ObjectLook.__value__)`，不再寫兩份。mypy 通過，不需要 noqa。順手把 `ObjectLook` 斷行的 docstring 接成段落。 | 49a58bc1 |
| 7 | `_building_sign`／`_buildings` 多收 `char`，還沒發現的 reveal 門用 `hidden_door` 跳過，判斷和 `_doors` 相同。 | 2f6dec8e |
| 8 | 建 `PathPreview`（一步都不能走的分支）和 `PathStep` 時改用關鍵字參數。`world/battlefield.py` 模組 docstring 斷開的兩段（開打距離、退回模板）接回段落。 | e6887979 |

第 5、7 項都改 `api/world_field_view.py`，所以放在同一個 commit。

### 第 4 項的等價性

用隨機事件比對新舊實作（20000 組，2～4 個分支）：

- **2 個分支的預覽完全一致**：只有最少／最多後果、沒有冰面分支的都屬於這種。
- `_widen` 改用 `other.amount_min` 實際上沒有差別，因為分支的原始事件 `amount_min == amount_max`。
- 唯一的差別在 3 個以上分支：某個傷害事件只在最多後果出現（`amount_min=None`），之後的冰面分支也有它時，舊版維持 `None`，新版取那個分支的值。前端會從「−最大值」變成「−最小～最大」，事件仍標「可能」。這是第 4 項要求的行為，現有測試全過。

## 有沒有升版

**沒有升版**，`WORLD_RULES_VERSION` 維持 6。我查了 6P-2 的兩處行為改變，目前的內容都觸發不到：

1. **`contact_battlefield` 在主城拿得到地點**：這只影響戰場名字。主城是安全區，`field_map_report` 規定不可有 `spawns`，所以碰不到地圖上的敵人。
2. **跨區出口通往主城現在能走**：`content/world/fields` 裡（主城以外）沒有任何 `region: capital` 或 `to: capital` 的出口。主城只能傳送抵達。

另外，6P-2 的 walk 上限改由規則決定，但規則值仍是 30，和原本的程式上限相同，只有被拒絕時的訊息不同。理由都寫進了 docstring，也註明內容加了上面兩種情況之一時要升版。

## 檔案清單

- `src/trpg/api/path_schemas.py`
- `src/trpg/engine/path_preview.py`
- `src/trpg/content/fields.py`
- `src/trpg/content/library.py`
- `src/trpg/world/save.py`
- `src/trpg/world/battlefield.py`
- `src/trpg/api/world_field_view.py`
- `src/trpg/api/world_field_schemas.py`
- `client/openapi.json`、`client/src/api/schema.d.ts`（產生的）
- `client/src/battle/pathPreview.test.ts`（只補夾具欄位）
- 測試：`tests/api/test_path_preview_api.py`、`tests/content/test_fields.py`、`tests/engine/test_path_preview.py`、`tests/world/test_field.py`、`tests/content/test_field_buildings.py`、`tests/api/test_world_field_buildings.py`

## 測試

新增 18 個測試，另外在 1 個既有測試加了斷言：

| 項目 | 新增 |
|---|---|
| 1 | API 冰＋陷阱測試加 `stops` 斷言：與引擎一致、超過 1 個、`stop` 在前、`worst_stop` 在 `stops` 裡 |
| 2 | 3 個：任務寫錯、步驟寫錯（同一個 parametrize 的 2 組，含「不給 `quest_steps` 就不檢查」）、別區的任務也算錯 |
| 4 | 12 個：合併表格 11 組（最少／最多後果傷害不同、順序顛倒、只在一邊、多分支更低／更高／缺少、只在最多後果之後又出現、兩個來源），加上非傷害事件與 `stopped` 原因 1 個 |
| 5 | 1 個：`FieldView` 預設值、沒有世界規則時的回退都等於 `FieldRules().walk_max_steps` |
| 6 | 1 個：`OBJECT_LOOKS == get_args(ObjectLook.__value__)` |
| 7 | 1 個：reveal 門沒發現時沒有招牌，發現後才有 |

只跑了相關的測試檔，都通過：

- `test_path_preview`、`test_ice_slide`、`test_path_preview_api`、`test_owner_guard`、`test_openapi_snapshot`
- `test_fields`、`test_cloud_fields`、`test_capital_field`、`test_ashen_fields`、`test_field_buildings`
- `test_world_field_buildings`、`test_world_field_api`、`test_field`、`test_mist_wall`、`test_battlefield`

前端：`tsc --noEmit` 通過，`vitest run src/battle/pathPreview.test.ts` 35 個通過。工作樹原本沒有 `node_modules`，我用 `pnpm install --frozen-lockfile` 裝回，沒有新增相依。

每次 commit 前都過了 `ruff check`、`ruff format --check`、`mypy src`（512 檔）、`lint-imports`（13 kept）。沒有新增 noqa，沒跑全量。

重播：`trpg battle --map swamp --seed 7` 再跑 `battle replay`，結果一致（88 個動作、313 個事件）。

## 待 PM 決定

1. **第 4 項「`amount_min` 為 None 時取對方的值」會改變 3 個以上分支的顯示**：見上面的「等價性」。如果要維持舊行為（只在最多後果出現過的傷害一直沒有最小值），`_combine` 改成 `event.amount_min is None` 時保留 `None` 即可，一行。
2. **第 2 項沒有區域任務表時的處理**：區域在 `world_quests` 裡沒有任務表時，那區的 gate 一律算錯（出口永遠打不開，只剩 `open_flag`）。和 `npcs` 缺區就不檢查的做法不同。如果希望只寫 `open_flag` 的 gate 也能過，要另外放寬。目前 `quest`／`step` 是必填欄位，所以照錯誤處理。
3. **第 1 項 `stops` 設成必填**：前端型別因此要求夾具補欄位。如果希望舊的前端夾具不用改，可以給預設值 `()`，但 OpenAPI 就會變成選填。
