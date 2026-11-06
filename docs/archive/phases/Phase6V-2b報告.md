# Phase 6V-2b 報告：致命角標外圍、灰渡口深水、水面羽化

> 2026-11-04，實作者（agent）。只換外觀：數值、規則、致命判定、路徑預覽都沒動。沒有新增相依。
> 規格來源：`docs/archive/art/6V-2檢查.md` 第 2 節（2.1～2.4）。

## 1. 做了什麼

| 項 | 之前（6V-2） | 現在 | 在哪 |
|---|---|---|---|
| 2.1 致命角標 | 每格四角都畫，大片區的角拼成紅十字網格 | 一個角只在共用它的 3 格（橫、直、斜）裡有「非致命格」時才畫。單格、一列照舊四角；大片區只剩外圈；L 形的凹角、孔洞四周都描出來。**地圖外不算非致命格**（貼地圖邊那一側不畫）。透明度維持 0.85；滑過、預覽時整格淡紅照舊 | `render/lethalMarks.ts`（`lethalCornerMask`、`lethalCornersOf`、`drawLethalCorners` 多一個 mask 參數）、`BattleRenderer.ts` |
| 2.2 灰渡口深水 | 灰河是荒原的黑色裂谷（`ashChasm`） | 實地地圖新欄位 `look.chasm_style: deep_water`，只有 `ash_ferry.yaml` 填。畫成深灰藍深水（`#34495c`，比荒原水面深一階）：濕泥岸 → 羽化的水 → 一層暗色 → 跨格的暗斑與很淡的大波紋（鄰格也是深水時連鄰格的一起畫，格與格接得起來）。不畫裂谷崖緣與底部紅光。另加一層慢速大波紋動畫（每格 2 道、9 秒一格、淡入淡出）；減少動態時靜止 | Python：`content/fields.py`（`FieldLook`、`ChasmStyle`）、`api/world_field_schemas.py`（`FieldView.chasm_style`）、`api/world_field_view.py`；前端：`hazardTerrainArt.ts`（`drawDeepWater`）、`terrainArt.ts`（`LOOK_TERRAIN_DRAW` 加 `chasm_style=deep_water`）、`regionArt.ts`（`chasmStyleOf`）、`world/fieldModel.ts`（`fieldLook`）、`surfaceAnim.ts`（`terrainAnimated`、`deepWaterSwell`）、`statusAnimArt.ts`（`swell` 貼圖）、`surfaceAnimLayer.ts` |
| 2.3 水面 | 岸邊 4px 硬邊濕痕＋一條細水線 | 濕痕與水面都羽化（`featherFill`：中間實心、岸側 12px 內平滑淡到 0、兩岸相接的角用 1/4 圓放射漸層，各塊不重疊）；水線拿掉。荒原水色 `#3b4f63` → `#45627a` | `hazardTerrainArt.ts`（`featherFill`、`drawWaterFill`）、`regionArt.ts` |
| 2.4 雲嶺 lava | 漂移層只看地形 ID，雲嶺的 lava 也會有岩殼漂 | `terrainShimmer`／`tileShimmer` 多一個主題參數；雲嶺（`LAVA_DRIFT_OFF_REGIONS`）的 lava 沒有漂移層，其他區域照舊 | `surfaceAnim.ts`、`surfaceAnimLayer.ts` |

順手修的（同一段畫法裡）：6V-2 水面的「深一點的水色暈」寫成 `rgba(shade(color, 0.8), …)`，但 `shade` 回傳 `rgb(…)` 不是 `#rrggbb`，結果畫成 0.45 的**黑色**暈，是單格水看起來像深色玻璃的原因之一。改成 `mix(color, "#000000", 0.2)`。

### 規則沒變的證明

- `chasm_style` 只進畫面：`ash_ferry` 的格子仍是 `chasm`（致命）。
- 規則雜湊照 6V-1 的做法排除整個地圖 `look`（`tests/content/test_field_buildings.py::_rule_hash`），並把 `ash_ferry` 加進 `RULE_HASHES`：雜湊 `ba92570cc37240f9` 是改之前算的，改之後一樣。其他已鎖的圖（霧渡鎮、餘燼集、主城與 7 間室內）的雜湊也沒變。

### schema

- `FieldLook.chasm_style: Literal["default", "deep_water"] = "default"`；省略 ＝ `default`。內容模型 `extra="forbid"`，未知鍵、未知值**載入時報錯**（照開發 PM 交代的「pydantic schema 要驗證」）。見待決 1。
- API：`FieldView.chasm_style`（預設 `default`）。已跑 `scripts/export_openapi.py` 與 `pnpm gen:api`。前端收到不認得的值當 `default`（`chasmStyleOf`）。

## 2. 檔案清單

新增：

- `tests/content/test_field_look_6v2b.py`（4 項）
- `client/src/render/hazard6v2b.test.ts`（16 項）
- `docs/art/6v2b_01`～`6v2b_07`（截圖）
- 本報告

修改：

- Python：`src/trpg/content/fields.py`、`src/trpg/api/world_field_schemas.py`、`src/trpg/api/world_field_view.py`
- 內容：`content/world/fields/ashen_waste/ash_ferry.yaml`（只加 `look`）
- 測試：`tests/content/test_field_buildings.py`（雜湊排除 `look`、加 `ash_ferry`）
- API 產物：`client/openapi.json`、`client/src/api/schema.d.ts`
- 前端：`render/lethalMarks.ts`、`BattleRenderer.ts`、`hazardTerrainArt.ts`、`terrainArt.ts`、`regionArt.ts`、`surfaceAnim.ts`、`surfaceAnimLayer.ts`、`statusAnimArt.ts`、`world/fieldModel.ts`
- 前端測試：`hazard6v2.test.ts`（`ANIMATED_TERRAINS` 多 `chasm`、荒原水色、岸邊改查羽化漸層）、`regionArt4.test.ts`（荒原水色）、7 個 `FieldView` 假資料補 `chasm_style: "default"`（型別必填）

沒碰：人物繪製、`src/trpg/llm`、`content/llm`、雲嶺的實地地圖、新手任務。

## 3. 測試

- `tests/content/test_field_look_6v2b.py`（4）：schema 只收 `default`／`deep_water`、未知鍵報錯；只有灰渡口用 `deep_water`（冷卻井照舊）；灰渡口深淵仍是 `chasm`、`deadly`；`field_view` 的 `chasm_style` 照地圖檔給。
- `client/src/render/hazard6v2b.test.ts`（16）：
  - 角標（6）：單格、一列、大片 5×5（內部 0、總角數 100 → 36）、L 形（凹角）、孔洞、地圖邊。
  - 深水（6）：`chasmStyleOf`／`fieldLook`；荒原＋`deep_water` 走深水畫法、沒有紅光、確定性、不同格不同；其他荒原裂谷與雲嶺雲海照舊；內側整格水、岸側羽化；大波紋確定性、在格內、端點淡出；**減少動態時 0 個節點**、一般裂谷不登記、關掉後藏起來。
  - 水面（3）：荒原 `#45627a`；單格水沒有整格硬邊濕痕與水線、4 邊 4 角都淡到 0；`featherFill` 各塊面積剛好鋪滿一格（不重疊）。
  - 雲嶺 lava（1）：`terrainAnimated`、`terrainShimmer`、`tileShimmer` 都空，`SurfaceAnimator` 不登記；其他區域照舊 3 個。
- 交件前：client 全部 `vitest run` **233 檔、2552 項通過**；`corepack pnpm -C client build` 通過（tsc ＋ vite）。
- Python：`ruff check`、`ruff format --check`、`mypy src`、`lint-imports` 通過；相關測試 `tests/content/test_field_look_6v2b.py`、`test_field_buildings.py`、`test_ashen_fields.py`、`test_fields.py`、`test_regions.py`、`tests/api/test_world_field_api.py`、`test_world_field_r3.py`、`test_openapi_snapshot.py` 通過。沒跑全量（守則 11）。

## 4. 截圖對照（`docs/art/`，1280×800，build 版、自己的伺服器 8333，無頭 Chrome `--mute-audio`、網址 `?mute=1`）

| 位置 | 之前 | 之後 |
|---|---|---|
| 灰渡口 | `6v2_05_tour08_after.jpg`：黑色裂谷、整片紅十字網格 | `6v2b_02_tour08_after.jpg`：灰河是深灰藍深水、有暗斑與淡波紋；角標只剩河岸一圈；水面格岸邊羽化、色調提亮 |
| 灰渡口滑過深水內部 | `6v2_06_tour08_hover.jpg` | `6v2b_03_tour08_hover.jpg`：內部沒有角標，滑過整格淡紅照舊 |
| 霧渡鎮雲海 | `6v2_02_tour02_after.jpg` | `6v2b_01_tour02_after.jpg`：雲海只剩外緣角標 |
| 雲海吊橋戰鬥 | `6v2_08_6n6_after.jpg` | `6v2b_04_6n6_after.jpg`：2 格寬的雲海只描外側，中間那條縫不再有角標 |
| 岩漿渡橋戰鬥 | `6v2_11_lava_after.jpg` | `6v2b_05_lava_after.jpg`：同上 |
| 熔岩洞窟（補：較大片的熔岩） | — | `6v2b_06_lava_cave_after.jpg`：實地圖兩列寬的熔岩河，只描外圈 |
| 深水與水面近看 | — | `6v2b_07_tiles_closeup.png`：dev 模組直接畫的貼圖（荒原＋`deep_water`），看羽化與深水接縫 |

注意：
- 截圖時伺服器的時間是晚上（6V-2 是中午），霧渡鎮和灰渡口的光線不同；相機位置也和 6V-2 略有差（6F-3 之後的 HUD 安全相機），地點與角色位置相同。
- 熔核之坑的實地圖沒有熔岩格（只有註解提到），所以改拍熔岩洞窟。

## 5. 方法

- 伺服器：`uv run trpg serve --port 8333`，存檔在 `scratchpad/v2b/saves`（從 6V-2 的 scratchpad 複製測試角色），`TRPG_LLM_GENERATE=false`、`TRPG_LLM_BASE_URL=http://127.0.0.1:9`、`TRPG_DEV_ROUTES=1`。搬地圖用 `scratchpad/v2b/relocate.py`，每次搬完用自己的 PID 重啟。
- 近看圖：vite 開發伺服器 5333，Chrome 裡直接 `import("/src/render/terrainArt.ts")` 畫一塊貼圖（`scratchpad/v2b/tiles.mjs`）。
- 結束時伺服器、vite、Chrome 都用自己的 PID 結束；沒碰 `tmp_x`、`saves/`；沒用 8000／8001／8010／8344／5344。

## 6. 待 PM 決定

1. **`chasm_style` 不認得的值**：美術 PM 的 2.2 寫「欄位值不認得時當作沒有」，開發 PM 交代「pydantic schema 要驗證」。我照 schema 驗證做（`Literal`，載入時報錯），比較保守：內容打錯字會立刻被抓到。前端收到不認得的值仍當 `default`。若要改成「警告後忽略」（同 `regions.yaml` 的 `look_keys`），只要改 `FieldLook` 的驗證。
2. **地圖外算不算非致命格**：我照「地圖外不是格子」處理，貼地圖邊的那一側不畫角標（灰渡口西緣、南緣的河就沒有沿地圖邊的一排角標）。若希望地圖邊也描，`lethalCornersOf` 改成地圖外算安全格即可。
3. **原型數值**（照最保守的預設做完，都是常數）：深水 `#34495c`、暗色層 0.18、暗斑 0.32、靜態波紋 0.2、濕泥岸 `#4a4541`；大波紋 9 秒一格、透明度 ≤ 0.2；水面羽化 12px（濕痕 4px、0.26）。
4. **深水的動畫**：滑過整格淡紅、角標都照舊；深水格本身每格 2 個 Sprite（同 6N-9 水面）。灰渡口約 100 格深水 → 約 200 個 Sprite，實測 165 fps（被螢幕更新率壓住，和 6V-2 一樣）。
5. **雲嶺 lava 的判斷用區域 ID 寫死**（`LAVA_DRIFT_OFF_REGIONS = ["cloud_ridge"]`）。若之後別的區也有「不是熔岩的 lava」，或要改成內容資料（例如地圖 `look`），再請決定。

## 7. commit（worktree 分支，沒 push、沒合併）

- `7c8e5cff` feat(content): 6V-2b field look.chasm_style (deep_water for ash_ferry), FieldView.chasm_style
- `301b7b17` feat(client): 6V-2b lethal corner marks only on the outline of deadly areas
- `6075d520` feat(client): 6V-2b deep-water chasm for ash_ferry, feathered water shores, no lava drift in cloud ridge
- `0b051c6e` fix(client): 6V-2b seamless deep water, smoother shore feather, water halo colour bug
- 截圖與這份報告：最後一個 commit
