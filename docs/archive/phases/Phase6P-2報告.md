# Phase 6P-2 完成報告：收尾小項②（世界層）

規格：`docs/phases/Phase6計畫.md` 第 1 節 6P-2 列（6D-R2 待決 4、6C-R2 待決 4）。

## 做了什麼

### 1. 查地點圖一律經 `location_map`（commit 683a7d5e）

`content/` 以外剩下直接查 `library.world_maps` 的地方都改成 `library.location_map(...)`：

| 位置 | 原本 | 現在 |
|---|---|---|
| `world/battlefield.py` `contact_battlefield` | `world_maps.get(encounter.region)` | `location_map(...)` |
| `world/field.py` `_take_exit`（跨區出口） | `world_maps.get(region)` | `location_map(...)` |
| `world/atlas.py` `region_name`、`region_state` | `world_maps.get(region)` | `location_map(...)` |
| `api/world_atlas_view.py` `atlas_view` | `s.region in library.world_maps` | `location_map(s.region) is not None` |
| `api/world_presenter.py` `_teleports` | `r in library.world_maps or r == CAPITAL_REGION` | `location_map(r) is not None or r == CAPITAL_REGION` |

找不到時照舊回 `None`（或原本的錯誤），一般區域的行為不變。**迭代區域清單**的地方（`atlas._gates_into`、`atlas_regions`、`_teleports` 的亮起清單、`absence_view`、`cli` 的內容進度）照舊用 `world_maps`，因為主城本來就不該在區域清單裡（同 6D-R2）。`content/` 內部載入與驗證用的 `world_maps` 參數不動。

測試（`tests/world/test_capital_hub.py`）：
- `test_no_direct_world_maps_lookup`：掃 `src/trpg`（`content/` 除外），不得出現 `world_maps.get(`、`world_maps[`、`in library.world_maps`。
- `test_capital_through_atlas_paths`：主城走 `region_name`／`region_state` 不出錯、名字是主城的；不存在的區照舊是 `later`。

### 2. walk 最大格數由 `rules.yaml` 決定（commit 3c98a44b）

- 拿掉 `trpg.world.field_actions.WALK_PATH_CAP`。
- 請求格式改成**寬上限** `WALK_PATH_FORMAT_MAX = 1000`（放在 `trpg.content.world_rules`，只防過大的請求）；`WalkAction.path` 的 `max_length` 用它，OpenAPI 的 `maxItems` 從 30 變 1000。
- 規則 `field.walk_max_steps` 的上限從 `le=30` 改成 `le=WALK_PATH_FORMAT_MAX`；超過寬上限就是內容錯誤。
- 處理時（`trpg.world.field._walk_path`）照規則檢查，錯誤訊息改成「一次最多走 N 格（這次送了 M 格；請分段送）」。API 回 422，`detail` 是這句話（原本 31 格是請求格式的 422，沒有說明）。
- `FieldView` 加欄位 `walk_max_steps`（預設 30），`field_view` 照規則填入。
- 前端：`WorldField.tsx` 的分段送改成 `chunkPath(path, cur.walk_max_steps)`；`chunkPath` 收到不合法的值（非正整數）時退回預設 `WALK_MAX = 30`。三個 `client/src/world` 測試的 `FieldView` 夾具補上 `walk_max_steps: 30`（型別要求）。
- `client/openapi.json`、`client/src/api/schema.d.ts` 重產。
- `content/world/rules.yaml` 只改註解，數值仍是 30。

測試：
- `tests/world/test_field.py`：`test_walk_limit_is_30_cells`（30 格可走、31 格回清楚的錯誤、規則改 2 時 3 格不行、2 格可以）、`test_walk_limit_follows_rules`（規則改 45：45 格可走、46 格錯誤；世界畫面的 `walk_max_steps` 跟著是 45）、`test_walk_request_format_cap`（寬上限 1000、規則值不得超過）。
- `tests/api/test_world_field_api.py`：畫面帶 `walk_max_steps == 30`；31 格的 422 `detail` 含清楚訊息。
- `client/src/world/fieldModel.test.ts`：照伺服器給的上限切段（45、10、不合法值退回 30）。
- OpenAPI 快照測試通過。

## 跑過的檢查

- `pytest tests/world tests/api tests/content -n 8 -x`：4215 通過、1 略過。
- 前端：`tsc --noEmit` 通過；`vitest run src/world` 329 通過。（工作樹原本沒有 `client/node_modules`，用 `pnpm install --frozen-lockfile --offline` 從 store 裝回，沒有新增相依；`node_modules` 不進 git。）
- `ruff check`、`ruff format --check`、`mypy src`（512 檔）、`lint-imports`（13 kept）通過。
- 重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 一致（88 動作、313 事件）。
- 沒跑全量。

## 待 PM 決定

1. **寬上限取 1000**：只防過大的請求；規則值超過 1000 會是內容錯誤。實地地圖目前最大不到 40×40，1000 綽綽有餘。若要完全沒有格式上限（只靠規則），改成拿掉 `max_length` 即可，但請求大小就沒有保護。
2. **主城的行為差異（算修正）**：`contact_battlefield` 在主城就地開打時，原本查不到地點（`None`），現在會拿到主城的城鎮地點；跨區出口若指向主城，原本一律「還沒開放」，現在能走（目前內容沒有通往主城的跨區出口，實際不會觸發）。其他區域行為不變。
3. **`world_presenter.py` 的改動**：限制寫「世界 presenter 只加欄位」，但第 1 項要求全專案統一，所以 `_teleports` 的一行查詢也改了（行為不變：主城的樞紐圖是必有的內容，且保留 `or r == CAPITAL_REGION`）。若不要動它可以單獨 revert 那一行。
4. **OpenAPI 衝突提醒**：6P-1 若也重產 `client/openapi.json`／`schema.d.ts`，合併時這兩個檔可能衝突，重跑 `scripts/export_openapi.py` 與 `pnpm -C client gen:api` 即可。
