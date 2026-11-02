# Phase 5A-1 完成報告：地點圖資料與 schema

> 實作者：implementer agent（2026-11-02）。規格：`docs/phases/Phase5計畫.md` 第 5 節。
> 只動 `content/`、`src/trpg/content/`、`tests/content/`、本報告；沒有建立 `trpg.world`，沒有動引擎、API、前端、roguelite、`content/skills/`、`src/trpg/skillgen/`。

## 1. 交付清單

| # | 項目 | 檔案 |
|---|---|---|
| 1 | 各區戰場地圖池 `RegionDef.map_pool` ＋ 五區資料（05 5.1、#43） | `src/trpg/content/regions.py`、`content/regions.yaml` |
| 2 | 地點圖 schema 與單檔／跨檔案驗證 | `src/trpg/content/world_map.py`（新） |
| 3 | 載入：`ContentLibrary.world_maps`、`world/maps/` 資料夾 | `src/trpg/content/library.py` |
| 4 | 雲嶺 18 個地點＋連線初稿 | `content/world/maps/cloud_ridge.yaml`（新） |
| 5 | 測試 | `tests/content/test_world_map.py`（新，30 個） |
| 6 | 本報告 | `docs/phases/Phase5A-1報告.md` |

## 2. Schema 摘要

- `RegionDef.map_pool: tuple[Archetype, ...] = ()`：空＝不檢查；不可重複、不可含 `test`／`training`／`boss`。
- `world_map.py`（`__all__` 明列）：
  - `LocationKind`（11 種，含 Q16 的 `boss`、`gate`）、`RevealMethod`（4 種）、`MapPos`（0～100）。
  - `LocationDef`：`id`、`name_zh`、`kind`、`level_min`／`level_max`（`level_max` 省略時載入補成 `level_min`）、`battle_maps`、`hidden`、`reveal`、`gate_to`、`unlock_flag`、`description_zh`、`pos`。
  - `LocationMapDef`：`region`、`name_zh`、`level_min`／`level_max`、`town`、`locations`、`edges`（無向）；方法 `location_by_id()`、`neighbors(id)`（排序後回傳，未知 ID 拋 `KeyError`）、`summary()`。
  - `world_map_problems(world_map, *, regions, maps) -> list[str]`（排序過）。
  - 常數 `MIN_LOCATIONS = 15`、`MAX_LOCATIONS = 25`（9.6.2）。
- 載入：`content/world/maps/*.yaml`，鍵＝`region`；資料夾不存在＝`{}`。用專用的 `_load_world_maps`（不改 `_load_dir`），檔名必須等於 `region`、同區兩檔 → `ContentError`、跨檔案有問題 → `ContentError`（指出檔案）。檔案加進 `library.files`，`trpg content check` 會列出「`world/maps/cloud_ridge.yaml`：雲嶺：18 個地點（隱藏 2）、21 條連線、等級 1～6」。

## 3. 驗證規則（錯誤訊息繁中、指出地點 ID）

單檔（`LocationDef` 自己驗地點層級的；`LocationMapDef` 驗整張圖）：

1. 地點數 15～25。
2. 地點 ID 不重複。
3. `town` 恰好 1 個且等於 `town` 欄位。
4. `town`、`gate` 不可有等級；其餘 `level_min` 必填；`level_min <= level_max`；都在區域範圍內；區域 `level_min <= level_max`。
5. `battle_maps`：`town`／`gate`／`village`／`caravan` 必須空；`camp`／`elite_lair`／`secret` 至少 1；不可重複。
6. `secret` ⇒ `hidden`；`hidden` ⇒ `reveal` 至少 1；`town`、`gate` 不可隱藏；`reveal` 不可重複。
7. `gate_to` 只有 `gate` 可填且必填；不可等於本區。
8. `edges` 兩端都是本圖地點、不可自連、無向去重後不可重複。
9. 連通（前面都通過才檢查）：從 `town` BFS 走得到全部地點；拿掉所有隱藏地點後，所有非隱藏地點仍走得到。鄰接表依 ID 排序，`deque` BFS，不依賴 set／dict 順序。

跨檔案（`world_map_problems`）：`region`、`gate_to` 在 `regions.yaml`；`battle_maps` 都在 `content/maps/`；非 `boss` 地點的地圖類型必須在該區 `map_pool`（池空則跳過）；`archetype: boss` 的地圖只能放在 `boss` 地點。

## 4. 測試

- `tests/content/test_world_map.py` 30 個：雲嶺載入（18 點、2 隱藏、town、summary）、18.3 對照、跨檔案通過、不經隱藏地點的連通、`neighbors` 排序與 `mist_ferry` 的鄰居、五區地圖池（7 種、4 通用、元素 3 種）、`map_pool` 驗證、地點數 14／26、ID 重複、小鎮、等級、戰鬥地圖、隱藏、gate、連線、連通（孤立點、隱藏唯一通路、加繞路就通過）、BFS 與連線順序無關、載兩次相同、跨檔案錯誤四種、boss 地點可放 Boss 地圖、壞檔 → `ContentError`、檔名≠region、沒有 `world/` 資料夾照常載入、`library.files` 有新檔。
- **雲嶺的連線條數不寫死**（開發 PM 指示：連線是 Q1 初稿，玩法 PM 可能改）；規格 5.5 表寫的「21 條連線」改成只驗「有連線」＋規則（連通、隱藏不是唯一通路）。
- 執行結果見第 7 節。

## 5. 用了 18 號文件的哪些內容

- 18.3 全部 18 個地點：名稱、種類、建議等級、戰鬥地圖（經 5.3 的模板對照）、「內容」欄抄進 `description_zh`。
- 18.1 雲嶺等級範圍 1～6。
- 隱藏方式依據：丹爐洞 ←「藥師谷…通往隱藏地點」→ `situation`；鶴歸崖 ←「感知判定或朋友足跡」＋事件 18 線頭 → `perception_nearby, quest_clue, friend_footprint`。
- 往灰燼荒原的渡口 ←「世界事件 #1『霧潮入侵』成功後開放」→ `unlock_flag: mist_tide_success`。

## 6. 開發 PM 自定的東西（照規格 5.3／5.4，未自行更動）

- 地點 ID、種類對照（Boss → `boss`、傳送 → `gate`，Q16）、座標 `pos`：照 5.3 表。
- 連線 21 條：照 5.4 初稿（Q1，待玩法 PM 代決）。改連線只動 `content/world/maps/cloud_ridge.yaml`。
- 戰場模板對照：山寺石階、鶴歸崖 → `cliff_outpost`；劍冢 → `ruined_fort`（都是 `ruined_heights`）；竹林 → `dark_forest`；雨中梯田 → `swamp`；峽谷棧道／狹窄長廊 → `narrow_halls`；雲海吊橋 → `bridge_chasm`；高原草甸／開闊平原 → `open_plain`；冬湖 → `frozen_lake`。

## 7. 檢查結果

- `uv run pytest -q tests/content/test_world_map.py tests/content/test_regions.py tests/content/test_loader.py -x -n 8`：62 passed。
- `uv run pytest -q tests/content tests/cli tests/test_architecture.py -m "slow or not slow" -n 8 --timeout=1800`：**1897 passed**（5 分 10 秒）。
- `uv run trpg content check`：通過，共 495 個檔案，列出 `world/maps/cloud_ridge.yaml` 的摘要。
- `ruff check .`、`ruff format --check src tests scripts`、`mypy`（945 檔）、`lint-imports`（7 個契約全部 KEPT）：通過。
- **注意（不是本段造成的）**：`ruff format --check .` 會檢查 Markdown 內的 Python 程式碼區塊，`docs/phases/Phase5計畫.md` 第 260 行起的 schema 範例（對齊用的空白註解）會被判定「需要重新格式化」，所以 `scripts/check.py` 的格式步驟會失敗。這個檔案是 PM 的規格，本段沒有改它；建議 PM 用 `uv run ruff format docs/phases/Phase5計畫.md` 修一下。

## 8. 代決清單（實作者照最保守做法，標「代決」）

1. **代決**：`world_map_problems` 在 `regions=None`（內容沒有 `regions.yaml`）時回報問題「缺少 regions.yaml，無法檢查區域」，而不是略過；`regions.yaml` 本來就在 `KNOWN_CONTENT_FILES`，實際內容不受影響。
2. **代決**：地點與區域的 `level_min` 加 `ge=1`（規格只對區域寫了 `ge=1`）；建議等級不可能是 0。
3. **代決**：`level_max` 省略時在載入時（`mode="before"`）補成 `level_min`，所以 `model_dump()` 會帶出 `level_max`；`town`／`gate` 維持 `None`。
4. **代決**：`neighbors()` 對未知地點拋 `KeyError`（不回傳空 tuple），避免 5A-2 打錯 ID 時默默當成死路。
5. **代決**：檔名必須等於 `region`（比照 `_load_dir` 的「檔名＝id」）；同區兩檔先報「已有另一份地點圖」。
6. **代決**：`boss` 地點放非 Boss 類型地圖時不檢查地圖池（規格寫「非 `boss` 地點的地圖」才檢查）。
7. **代決**：連通檢查只在前面的結構檢查都通過後才跑（避免未知端點時再多報一串連通錯誤）。
8. **代決**：`unlock_flag` 鎖住的地點在連通檢查中視為一般地點（規格沒寫；渡口是葉節點，不影響雲嶺）。之後若要求「未解鎖地點不可是唯一通路」，加一條同隱藏地點的檢查即可。
9. **代決**：import-linter／`tests/test_architecture.py` 不動：規格 2.3 寫明 5A-1 不建立 `trpg.world`，契約在 5A-2 加。

## 9. 待 PM 決定

- **Q1（D2）連線**：21 條仍是初稿，待玩法 PM 代決；測試不綁條數，改了只動資料。
- **雲頂觀沒有戰鬥地圖**：5F-2 補 Boss 專屬地圖時要同時把它加進 `battle_maps`（schema 已允許 `boss` 地點放 `archetype: boss` 地圖）。
- 雲嶺地點用到的地圖中只有 `dark_forest`、`bridge_chasm` 標 `region: cloud_ridge`；其他地圖的區域換皮是 5A-4 的事（本段未改地圖檔）。
- 18 號文件整份（D1）仍待使用者確認；使用者改了地點只動 `content/world/maps/cloud_ridge.yaml`。
