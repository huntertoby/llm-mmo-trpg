# Phase 6V-2 報告：致命與水面地形外觀

> 2026-11-04，實作者（agent）。只改 `client/`，只換畫法；數值、規則、Python、API、格子與致命判定都沒動。沒有新增相依。
> 規格來源：`docs/archive/art/Fable審查.md` 第 2 節 A（#11 雲海、#12 熔岩、#13 水面、致命標記）。

## 1. 做了什麼

| 項 | 之前 | 現在 | 在哪 |
|---|---|---|---|
| 雲海／深淵（`chasm`） | 灰色毛玻璃方格（雲嶺）、近黑漸層（預設） | 白雲團鋪滿格子、邊緣羽化、底下透淡藍。雲團照 `worldPaintedArt.js` 的 `cloudPuff`／`cloudBank` 縮小（左上亮、邊緣羽化到透明）。鄰格也是雲海時，連鄰格種子的雲團一起畫（裁在本格內），格與格之間雲團接得起來。崖緣照舊（雲嶺青石崖線、預設灰紫崖唇） | `render/hazardTerrainArt.ts`（`drawCloudSea`）、`terrainArt.ts`（`drawChasm`）、`cloudRidgeTerrain.ts`（`cloudChasm`）。晶冠共用預設的 `drawChasm`，一起換 |
| 熔岩（`lava`） | 橘底加散落結殼（靜態） | 照 `ashenRegionArt.js` 熔岩河：橘紅底（`#c2410c`）、亮橘光團、亮黃熱紋（`#ffd36b`）、黑色岩殼小板塊與裂紋線；靠岸（`lip`）那一邊一圈凹凸的冷卻黑殼。荒原底色略暗（×0.92） | `hazardTerrainArt.ts`（`drawLavaBase`）、`terrainArt.ts`（`drawLava`）、`ashenTerrain.ts`（`ashLava`） |
| 熔岩的慢速漂移 | 無 | 每格 2 片岩殼塊（normal 混色）＋ 1 團熱光（add 混色、染橘）沿同一方向漂，一格 11 秒；漂到格緣前淡出、另一邊淡入。方向、相位只看格子座標雜湊，時間 → 相位（`terrainShimmer`），不用 `Math.random`。減少動態時 `SurfaceAnimator.setEnabled(false)` → 不登記、已登記的藏起來，畫面是靜態貼圖 | `surfaceAnim.ts`（`terrainShimmer`、`tileShimmer`、`ANIMATED_TERRAINS`、`SHIMMER.lavaDriftMs`）、`statusAnimArt.ts`（`crust`、`ember` 兩張共用小貼圖）、`surfaceAnimLayer.ts`（地形也走同一套 shimmer） |
| 致命標記 | 整格大紅 X ＋ 整格紅框 | 四角各一個 6px 的小紅角標（縮 2px、線寬 1.5、透明度 0.85）。滑過、路徑預覽（經過的格、停點、滑倒、到不了）、預覽範圍、可選目標、已選格碰到致命格時整格疊淡紅（0.22）。**只是畫法**：`TileDraw.deadly` 與路徑預覽的規則不動 | `render/lethalMarks.ts`（`lethalCornerPaths`、`drawLethalCorners`、`lethalTintCells`）、`BattleRenderer.ts`（`tileSprite`、`setHighlights` → `drawLethalTints`） |
| 水面（`water` 表面） | 藍色圓角併塊＋白色波浪線 | 填滿格子；岸邊（鄰格不是水）留 4px 濕痕（地面壓深一階）與一條細水線；深一點的水色暈；細反光線 1px。6N-9 的飄動反光線照舊。水色依區域：雲嶺清藍 `#3f93d6`、荒原深灰藍 `#3b4f63`、主城晶藍 `#4aa6e4`；`look.water_tint`（雨中梯田的綠）優先；其他區域與未知區域用預設 `PAL.water` | `hazardTerrainArt.ts`（`drawWaterFill`）、`regionArt.ts`（`WATER_BY_REGION`、`waterColorOf`）、`terrainArt.ts`（`drawSurface` 水面不走併塊） |

### 效能

- 雲海、熔岩、水面都還是「一格一張離屏貼圖、依規格鍵快取」（`ArtTextures.tile`），沒有每幀重建 Graphics。
- 熔岩漂移只用 2 張共用的小貼圖（`crust` 20×14、`ember` 36×30）當 Sprite，每幀只改位置、透明度、縮放；和 6N-9 水面反光線同一條路（`SurfaceAnimator.apply`），沒有遮罩。6R-F 提的遮罩熱點是轉場（appear／vanish）用的，這段沒加同類。
- 致命角標畫在既有的那張 `Graphics`（每格本來就有一張畫崖面、描邊），淡紅是 `setHighlights` 時一張 `Graphics` 畫完所有格。

## 2. 檔案清單

新增：

- `client/src/render/hazardTerrainArt.ts`：雲海、熔岩底圖、水面的 Canvas 畫法（純函式，只看座標雜湊）。
- `client/src/render/lethalMarks.ts`：角標折線、淡紅格的計算與 Pixi 畫法。
- `client/src/render/hazard6v2.test.ts`：14 項測試（見第 3 節）。

修改：

- `client/src/render/terrainArt.ts`、`cloudRidgeTerrain.ts`、`ashenTerrain.ts`、`regionArt.ts`：接上新畫法與區域水色。
- `client/src/render/surfaceAnim.ts`、`surfaceAnimLayer.ts`、`statusAnimArt.ts`：熔岩漂移。
- `client/src/render/BattleRenderer.ts`：角標與淡紅。
- `client/src/render/regionArt.test.ts`、`regionArt4.test.ts`：鎖住舊畫法的期望更新（預設畫法雜湊 `1837b83c` → `6aa45e1d`；「表面各區完全一樣」排除水面、改成各區水色不同；荒原岩漿改成檢查發光、熱紋、2～3 片結殼）。
- `docs/art/6v2_01`～`6v2_11`：前後截圖。

## 3. 測試

- `client/src/render/hazard6v2.test.ts`（14 項）：
  - 雲海：同格同圖、不同格不同；底下淡藍、≥ 5 團羽化雲；鄰格是雲海時雲團更多；`cloudNeighbors` 依 `lip` 排除崖那一側；預設、雲嶺、晶冠的 `chasm` 都走雲海、崖緣仍在。
  - 熔岩：底圖確定性；發光、熱紋、結殼都有；靠岸的邊多冷卻黑殼；預設與荒原同一套（荒原底色略暗）；漂移：時間 → 相位確定性、一格 ≥ 8 秒、全程在格內（0.05～0.95）、漂到端點時透明度 < 0.25、岩殼 normal 混色、熱光 add；`SurfaceAnimator` 關掉時 0 個節點，開著時每格 1 個，再關掉就藏起來（減少動態靜止）。
  - 致命標記：四條折線、6px、縮 2px；淡紅只疊在致命格（滑過、路徑段終點與點、預覽、目標、已選），去重、依 (y, x) 排序。
  - 水面：各區水色與 `look.water_tint` 優先、未知區域用預設、`constructor` 鍵不當畫法；四鄰都是水時整格、岸邊留 4px 與水線；`drawTile` 的水面沒有 `clip()`。
  - 來源掃描：動到的 10 個檔案沒有 `Math.random(`（註解除外）。
- 既有測試：致命判定（`drawModel.test`、`glossary`）與路徑預覽（`pathPreview.test`）沒動、照過。
- 交件前：`vitest run` 全部 **228 檔、2494 項通過**；`corepack pnpm -C client build` 通過（tsc ＋ vite）。

## 4. 截圖對照（`docs/art/`，1280×800，全部靜音：無頭 Chrome `--mute-audio`、網址 `?mute=1`）

| 位置 | 之前 | 之後 | 滑過致命格 |
|---|---|---|---|
| 霧渡鎮左下的雲海（`tour_02` 同位置） | `6v2_01_tour02_before.jpg`：灰色毛玻璃方格加淡紅 X | `6v2_02_tour02_after.jpg`：白雲團、羽化、透淡藍；四角小紅角標 | `6v2_03_tour02_hover.jpg`：滑過的那格整格淡紅 |
| 灰渡口（`tour_08` 同位置） | `6v2_04_tour08_before.jpg`：暗紅方格加大 X；水面是藍色圓角方塊加白波浪 | `6v2_05_tour08_after.jpg`：紅 X 不再出現、只剩角標；水面填滿、深灰藍、岸邊濕痕、細反光線 | `6v2_06_tour08_hover.jpg` |
| 雲海吊橋戰鬥（`6n6` 同地圖） | `6v2_07_6n6_before.jpg`：中央一整列灰玻璃加紅 X | `6v2_08_6n6_after.jpg`：一整列雲海，橋在雲上 | `6v2_09_6n6_hover.jpg`：選移動時滑到雲海格，淡紅＋「到不了」 |
| 岩漿渡橋戰鬥（真正的 `lava` 格） | `6v2_10_lava_before.jpg`：橘底加散落結殼、紅 X | `6v2_11_lava_after.jpg`：橘紅發光、熱紋、黑殼裂紋、靠岸黑殼；角標 | — |

注意：`tour_08`（灰渡口）畫面裡那一大片「暗紅方格」其實是 **`chasm`（荒原的黑色裂谷畫法 `ashChasm`）**，不是 `lava`；地圖檔 `ash_ferry.yaml` 寫明「灰河沒有水的地形，深水照 6C-3 的做法用深淵畫」。這次照規格只換了 `lava` 的畫法，`ashChasm` 沒動（去掉大 X 後是黑底、底部淡紅光、角標），見待決第 1 點。真正的熔岩格在岩漿渡橋、熔岩洞窟、鐵匠村、幫派車道，對照用岩漿渡橋。

## 5. 效能量測（同一場景、同一台機器，無頭 Chrome、ANGLE D3D11，`requestAnimationFrame` 4 秒平均）

| 場景 | 之前 | 之後 |
|---|---|---|
| 霧渡鎮（雲海 ~20 格、水面 0） | 165.2 fps | 165.1 fps |
| 灰渡口（裂谷 ~100 格、水面 9 格） | 165.0 fps | 165.1 fps |
| 雲海吊橋戰鬥（雲海 14 格） | 164.4 fps | 164.8 fps |
| 岩漿渡橋戰鬥（熔岩 12 格 → 36 個漂移 Sprite） | 165.2 fps | 164.1 fps |

都被螢幕更新率（165 Hz）壓住，看不出差異；熔岩每格 3 個 Sprite 的每幀更新和 6N-9 水面每格 2 個同一量級。沒有可用的大片熔岩實地圖可以在戰鬥開始畫面選（熔核之坑不在單場清單），沒有量到 100 格以上的熔岩。

## 6. 方法

- 自己的伺服器 `uv run trpg serve --port 8333`，存檔在 `scratchpad/v2/saves`（`TRPG_SAVE_DIR`），`TRPG_LLM_GENERATE=false`、`TRPG_LLM_BASE_URL=http://127.0.0.1:9`、`TRPG_DEV_ROUTES=1`；build 版。
- 自己 spawn 的無頭 Chrome（CDP 9333、`--mute-audio`、自己的 user-data-dir），Node 24 內建 WebSocket 寫的最小 CDP 驅動（`scratchpad/v2/cdp.mjs`、`shoot.mjs`），不裝套件。
- 大世界的位置：建一個測試角色，改 scratchpad 存檔的 `region`／`location`／`field` 搬到霧渡鎮與灰渡口（`scratchpad/v2/relocate.py`），重啟伺服器。戰鬥用 `?dev=1` 開始畫面選地圖、「一鍵開局」。
- 結束時伺服器、Chrome 都用自己的 PID 結束；沒碰 `tmp_x`、`saves/`；沒用 8000／8001／8010／8366／8399／5388。

## 7. 待 PM 決定

1. **荒原的 `chasm`（黑色裂谷）要不要跟著改**：Fable 審查 #12 看到的「暗紅方格」是 `ashChasm`，在灰渡口代表灰河深水、在冷卻井代表裂谷。這次沒動它（規格寫的是 `lava`）。選項：(a) 照舊黑裂谷；(b) 荒原的 `chasm` 改成深灰藍的深水（加暗色層與緩慢大波紋，對應規格表的「深水」列）——但其他荒原圖的裂谷也會變成水；(c) 內容加一個 `deep_water` 地形再分開畫。保守做法是 (a)，請美術 PM 看 `6v2_05` 決定。
2. **雲嶺的 `lava`（地熱泉）**：3-37b 把雲嶺的 `lava` 畫成橘紅泉水加白煙（`cloudLava`），這次沒改成熔岩河（雲嶺沒有熔岩的設定）。漂移層會在雲嶺的 `lava` 上也畫岩殼塊（`terrainShimmer` 只看地形 ID）。目前內容裡雲嶺沒有 `lava` 格，所以看不到；若之後要用，請決定雲嶺要不要關掉漂移。
3. **角標的紅在白雲上很醒目**（`6v2_03`）：照規格 6px、同危險區色。若美術 PM 覺得在雲海上太跳，可把 `LETHAL_CORNER_ALPHA`（0.85）降到 0.6，或雲海格改用深一階的紅。
4. **原型數值**（照最保守預設做完）：雲團每格 5～7 團、半徑 11～20、透明度 0.62～0.82；熔岩漂移一格 11 秒、岩殼縮放 0.7～1.0、透明度 ≤ 0.78；水面濕痕 4px、水面透明度 0.86；淡紅 0.22。都是常數，改不動規則。
5. **深水／淺水**：內容裡沒有 `deep_water` 表面或地形，規格表的「深水加一層暗色與緩慢的大波紋」沒有對應的 ID 可畫，沒做。

## 8. 檢查清單（Fable 審查第 2 節 A「檢查」）

- [x] `tour_02`、`tour_08`、`6n6` 三張同樣位置重拍，前後各一張（另加滑過致命格各一張、岩漿渡橋前後各一張）。
- [x] 雲海像雲（白雲團、羽化、透淡藍）。
- [x] 熔岩像熔岩（真正的 `lava` 格：岩漿渡橋）；灰渡口那片是裂谷，見待決 1。
- [x] 水面像水（填滿、岸邊濕痕、細反光線、水色依區域）。
- [x] 紅 X 不再出現。
- [x] 致命格仍一眼分得出：四角角標＋滑過、路徑預覽、選目標時整格淡紅。
- [x] 致命判定與路徑預覽的既有測試不變；來源掃描沒有新增 `Math.random`。
- [x] 減少動態時熔岩靜止（測試鎖住；畫面就是靜態貼圖）。

## 9. commit（worktree 分支，沒 push、沒合併）

- `f9f213fa` feat(client): 6V-2 cloud-sea chasm, glowing lava with drift, corner lethal marks, filled water
- `e85f4f2e`、`d46cb4fe` test(client): 測試型別與行尾修正（讓 `pnpm build` 的 tsc 過）
- `ffdf0759` feat(client): 6V-2 lava crust plates smaller with crack lines; lighter drifting crust
- 截圖與這份報告：最後一個 commit
