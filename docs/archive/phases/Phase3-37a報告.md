# Phase 3-37a 報告｜區域主題底層

規格：`docs/phases/Phase3計畫.md` 第 41 節共同規則與 41.1；需求以 `docs/art/雲嶺移植需求.md` 第 1 節為準。本段只做底層；雲嶺畫法留給 3-37b，**正式地圖沒有動**。

## 做了什麼

| 項目 | 內容 |
|---|---|
| 資料表 `content/regions.yaml`（新） | `regions`：五區 ID（`cloud_ridge`、`crystal_crown`、`arcane_hub`、`ashen_waste`、`frost_tide`）與中文名、各區的預設 `look`（目前皆空）；`default_region: crystal_crown`；`look_keys`：`look` 的鍵與允許的值（`wall: [canyon_rock]`、`floor: [plank_walk, paddy]`、`grass: []`、`water_tint: [green]`）。值只列非預設畫法。新增區或覆寫值只改這個檔。 |
| `trpg/content/regions.py`（新） | `RegionTable`（驗證：ID 不重複、預設區存在、區域自己的 look 合法）、`sanitize_map_theme()`。已登錄到 `registry.KNOWN_CONTENT_FILES`（`trpg content check`）。 |
| `MapDef`（maps.py） | 選填 `region: str \| None`（只驗 ID 格式）、`look: dict[str, str]`（預設空）。schema 層不綁死五區名單。 |
| `load_library` | 若有 `regions.yaml`：載入並對每張地圖 `sanitize_map_theme`（丟棄未知值、併入區域預設 look），警告寫入 `ContentLibrary.map_warnings` 並 `logging.warning`。`ContentLibrary` 新增 `regions`、`map_warnings`（皆有預設值）。 |
| 引擎狀態與視圖 | `BattleState.region`、`BattleState.look`（`begin_battle` 從地圖複製；`clone` 同步）；`BattleView` 新增 `region: str \| None`、`look: dict[str, str]`。純顯示資料，不進任何結算。 |
| 前端 `render/regionArt.ts`（新） | `ArtTheme`（`region`、`look` 正規化字串）、`lookKey`、`themeOf`、`themeKey`、`pickThemed`（look 覆寫優先於區域；只讀自己的屬性）。 |
| `TileArtSpec`／`ObjectArtSpec` | 兩者 `extends ArtTheme`，快取鍵加 `themeKey`。`DrawModel` 新增 `region`、`look`，`buildDrawModel` 由 API 視圖填入；`BattleRenderer` 把主題傳給物件規格。 |
| 「ID → 畫法」表骨架 | `terrainArt.ts`：`REGION_TERRAIN_DRAW`、`LOOK_TERRAIN_DRAW`；`objectArt.ts`：`REGION_OBJECT_DRAW`、`LOOK_OBJECT_DRAW`。目前皆為空物件；`drawTile`／`drawObject` 先查主題表、查不到退回原本畫法。雲嶺在 3-37b 加進這些表。 |

## 未知值處理方式（擇一：載入時警告並退回預設）

- 地圖檔寫了表裡沒有的 `region` → 載入時改為 `None`（預設畫法）並記警告；未知的 `look` 鍵或值 → 該項被丟棄並記警告。**地圖照常載入**。
- `MapDef` 本身只驗 ID 格式（`ID_PATTERN`），格式不對的 `region` 仍是驗證錯誤（與其他 ID 欄位一致）。
- 前端再多一層：伺服器給的值若不在畫法表內（含 `constructor` 這類鍵），一律退回預設畫法，不出錯。
- 目前 12 張正式地圖與測試地圖都沒寫 `region`／`look`，`map_warnings` 為空。

## API 變更

`BattleView` 加 `region`、`look`（皆選填、有預設，舊客戶端不受影響）。已重產 `client/openapi.json`、`client/src/api/schema.d.ts`；`scripts/export_client_fixtures.py` 重跑後固定檔無差異；`tests/api/test_openapi_snapshot.py` 通過。

## 戰鬥紀錄與雜湊

沒有影響：`LOG_FORMAT` 不變；事件、動作、`rng_state` 不含新欄位；專案中沒有狀態雜湊。`trpg battle --map swamp --seed 60 --log-json` ＋ `trpg battle replay`：95 個動作、304 個事件，重播通過。

## 測試

- pytest：`tests/content`、`tests/api/test_openapi_snapshot.py`、`tests/test_architecture.py`、`tests/engine/test_state_clone.py` 共 921 項全過；新增 `tests/content/test_regions.py`（9 項：五區表、既有地圖無主題、有效值保留、未知 region／look 丟棄並警告、地圖 schema 接受任意字串但擋格式錯誤、表驗證、視圖帶出主題、`load_library` 遇未知值仍載入）。
- ruff check、ruff format、mypy（全專案 610 檔）通過。Python 用 worktree 內 `uv sync` 建的 `.venv`（`UV_NO_SYNC=1 uv run`）。
- vitest 795 → 804（新增 `render/regionArt.test.ts` 9 項：`lookKey`／`themeOf` 正規化、`buildDrawModel` 帶出主題、快取鍵區分 region 與 look（格子與物件）、`pickThemed` 命中與未知值、**每種地形與物件（含未知）× 未知／尚無畫法的主題的繪圖呼叫序列與預設完全相同**，即既有地圖畫面不變）；typecheck、`pnpm build` 通過。
- 實機：以 vite（5197 埠，自行啟動後已關閉，未動使用者的 8000 埠）開 `/fx-gallery.html`，1600×900，畫面與 3-36b 相同、主控台無錯誤；已還原視窗並關閉分頁。

## `# noqa`

無新增（`load_library` 原已有 `PLR0915` 的 noqa；新增邏輯抽成 `_apply_map_themes` 避免再超標）。

## 待 PM 決定

1. **未知值警告與否**：目前是丟棄並記警告（logging，不中斷）。若要讓 `trpg content check` 把 `map_warnings` 印出來或視為失敗，3-37b 前可再加。
2. **區域預設 look**：`regions.yaml` 每區有 `look` 欄位（目前空），載入時併入地圖；若 3-37b 想用「雲嶺預設 `floor`／`wall`」之類，直接填表即可，不用改程式。
3. **預設區的名稱**：`crystal_crown` 在表中，但前端把「省略」與「`crystal_crown`」都當預設（`crystal_crown` 目前不在任何畫法表內）。若之後晶冠城邦想有別於預設畫法，要在畫法表補一列。
4. **`look` 鍵的畫法由誰認**：`look` 值只在 `regions.yaml`（後端）與前端畫法表（`LOOK_*_DRAW`）兩處登錄；新增值要兩邊同步，前端沒有對應時自動退回預設。
5. `water_tint` 這類「微調顏色而非換整個畫法」的覆寫，不適合放進「ID → 畫法」表，3-37b 實作沼澤水底色時需要在表面繪圖處另讀 `look`（規格有 `look` 字串可用，`pickThemed` 之外的小工具待 3-37b 補）。
