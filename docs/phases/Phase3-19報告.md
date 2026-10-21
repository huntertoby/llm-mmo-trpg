# Phase 3-19 報告：高度「整格抬高」與地形升降動畫

實作者：implementer agent（opus）｜分支 `worktree-agent-ac1b37ed388c12fd7`（從 main `cc9c86d` 分出）｜規格：`docs/phases/Phase3計畫.md` 19.3、19.4；美術定案 `docs/art/3-18倒地與高度.md` 第 5 節（第 3 節粒子）。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `4d5e9fc` | `battle/elevation.ts`（純函式）：`RAISE = 6`、`tileLift`、`topReserve`／`stagePixels`、`liftedOrigin`／`liftedCenter`、`pickTile`（由南往北、前排優先）、`drawRows`、`occluded`、`edgeMarks`、`easeOut`／`liftHeightAt`、`heightShifts`；`stageLayout.ts` 的 `fitScale`／`scaledSize`／`clientToTile`／`cardPlacement` 改用它（含上方預留） |
| `68f8216` | 繪圖：場景移入 `world`（y ＝ 上方預留），`RowStack` 由北到南一排一排畫（地形與崖面 → 表面裝飾 → 物件 → ▲N → 高亮 → 陷阱 → 單位）；崖面、描邊、遮擋剪影、升降動畫（`render/heightArt.ts`、幾何在 `render/heightShapes.ts`）；高亮、範圍與路徑預覽、預告、浮動數字、行動連線、技能特效起點與落點、滑鼠框全部用抬高後的座標（特效以 `at` 參數傳入，預設 `tileCenter`）；拿掉 A 方案的貼圖崖面、細邊線、`castShadow`、`drawHeight` 懸崖線與 `heightModel.heightDecor`；頂面亮度改 `rgba(255,246,220,0.10×h)`；播放計畫新增 `lift` 步驟（`terrain_changed` 前後高度不同），`BattleScreen` 只加 3 行轉呼叫 |
| `e638c8f` | 修正：播放結束時會用同樣的結果再重畫一次，原本會把進行中的升降動畫截斷；改成目標高度不變的動畫在重畫後接著播 |
| （本檔） | 報告與截圖 |

新增檔：`client/src/battle/elevation.ts`(+test)、`client/src/render/heightShapes.ts`(+test)、`client/src/render/heightArt.ts`、`client/src/render/rowLayers.ts`。
未動 3-18a 的檔案（`skillParts.ts`、`skillIcon.ts`、`SkillBar.tsx`、技能卡元件、`vfxPalette.ts`、工坊）；`styles.css`、API 型別、後端皆未改。

## 2. 驗收條件

### 19.4-1 vitest

| 項目 | 證據（測試） |
|---|---|
| `tileLift` | `elevation.test.ts`「tileLift › 每階抬高 RAISE（6）…」「頂面座標、畫布預留都由 tileLift 推出」 |
| `clientToTile` 平地 | `elevation.test.ts`「pickTile › 平地：就是格子座標」；`stageLayout.test.ts` 原有平地測試全數保留通過 |
| 前排高格蓋住後排：點頂面、點崖面 | 「pickTile › 前排高格蓋住後排：點前排的頂面與崖面都選前排，後排露出的部分選後排」「後排高格：頂面往上抬，點頂面選它」 |
| 地圖邊緣 | 「pickTile › 地圖邊緣：範圍外回傳 null」 |
| 縮放後 | 「clientToTile（含預留與縮放）› 每一格頂面中心換算回同一格（各種縮放與位移）」「縮放後：點前排高格的崖面選前排，點後排露出的頂面選後排」「畫布大小、縮放都含上方預留」「浮動卡頂端對齊抬高後的頂面」 |
| 繪製順序（北→南） | 「drawRows 繪製順序 › 由北到南一排一排，同排由西到東；空排也在」 |
| 遮擋判定 | 「遮擋判定與描邊 › 南鄰比自己高才算被擋；同高、較低、地圖底邊都不算」「較低的鄰邊才描線，地圖外不畫」 |
| 補間取值 | 「升降補間 › ease-out…」「從舊高度補到新高度；時間到或 0 秒直接是結果」「heightShifts：只取高度真的改變的格子，同格多次合併」；`heightShapes.test.ts`「播放計畫的升降動畫」三條（view 之後播、速度縮放 slow 600／normal 300／fast 150 ms、略過時沒有升降）；崖面地層線、虛線 3/2、碎土 6～8 顆、塵土圈 |

`corepack pnpm -C client test`：42 個檔案、471 個測試全過。

### 19.4-2 瀏覽器實測（`uv run trpg serve --port 8319`，用本 worktree 的 `client/dist`；懸崖前哨、飛翼流、種子 1）

- **點選高台後面一排**：主角站在 (1,4) 高台上，點 (1,3) 露出的上半部 → 主角移到 (1,3)（後排格子點得到）；之後 (1,3) 南鄰較高，主角出現剪影。滑鼠換算以 DOM 事件驗證：後排 (4,1) 露出部分 → 「高度 0」；被前排 (4,2)（高 3）蓋住的位置與其崖面 → 「高度 3」；站在高 2 格、南鄰高 3 的隊友 C，點身體上半 → 顯示 C 的單位卡（後排單位點得到）。
- **築高台動畫**：施放後五格 0→1（(3,4) 1→2），格上物件與單位一起移動；以 `playLift` 放慢補間截到中途一格（約 49%），碎土粒子可見。下降（3→1）跑過一次無錯誤（主控台沒有錯誤）。
- 截圖：
  - `docs/phases/img/3-19-mixed-map.png`：平地與高台（高 1、2、3）混合，▲N、崖面、北緣亮邊、東西暗線、被擋單位 C 的剪影。
  - `docs/phases/img/3-19-silhouette.png`、`3-19-silhouette-hero.png`：被南邊高格擋住的單位（隊伍色虛線輪廓）。
  - `docs/phases/img/3-19-preview-on-plateau.png`：築高台的範圍預覽（橘色）畫在高台頂面上；`3-19-targets-on-plateau.png`：目標紅框對齊抬高後的頂面。
  - `docs/phases/img/3-19-lift-midway.png`：升起動畫中途（三格約補到一半，邊緣碎土）。
- **1600×900**：DOM 量測 `scrollWidth 1600 / scrollHeight 900`（無捲軸）；畫布 622×646 CSS px（＝ 480×(480+18) × 1.296），完整落在戰場容器 1270×662 內。縮放與拖曳版面沿用既有機制（畫布大小只多了預留，`fitScale` 已計入）。

### 19.4-3 檢查

- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest、client install／typecheck／test **全部通過**。
- `corepack pnpm -C client build`：成功（只有既有的 chunk > 500 kB 警告）。

## 3. 複雜度 noqa

前端沒有 ruff 複雜度規則；後端未改。新增 noqa：**0**（`src/` 共 55 個，前後相同）。

## 4. 修改既有測試的清單

- `battle/heightModel.test.ts`：`heightDecor`／`CLIFF_MIN_DIFF` 已刪除（規格 19.3-5），「clientToTile 不受高度影響」改由 `elevation.test.ts` 的新換算測試取代；保留 `pedestalScale` 與格子尺寸測試。
- `render/art.test.ts`：貼圖規格不再有 `drop`／`shadowN`／`shadowW`／`lowerW`／`lowerE`（崖面與投影移出貼圖），四條相關測試合併成「高度只影響頂面亮度」；快取鍵測試把 `{ drop: 15 }` 換成 `{ wallFace: true }`。

## 5. 待 PM 決定

1. **高亮的圖層**：規格只說跟著頂面位移。我把移動、預覽、目標框等高亮放在各排之內（物件與 ▲N 之上、單位之下，沿用原本「高亮在單位底下」的順序），所以南邊的高格會蓋住北邊一排高亮的下緣（最多 18px）；滑鼠框與反應觸發框仍在最上層。若要高亮永遠畫在最上層（樣張的畫法），只需把它移到 `world` 層。
2. **崖頂亮唇**：第 5 節第 2 條只寫「崖頂一條 2px 亮唇」；我在每個抬高的格子都畫（南鄰同高時會被南鄰蓋住，效果等同只在南鄰較低時出現）。
3. **不可站立的格子也照高度抬高**（例如高台上的牆是高 3）：沿用地圖資料的高度，沒有特例；深淵、岩漿目前地圖上都是高 0。
4. **單位底座陰影（3-14 `pedestalScale`）保留**：規格沒要求拿掉；整格抬高後它的必要性降低，可在 3-18b 一併決定。
5. **畫布上方預留以「目前畫面」的最高格計算**：升起使最高格變高時，畫布在動畫開始時就長高 6px（版面會跳一下）；下降時若舊高度超過新的預留，最上排在補間中會被畫布上緣切掉一點。
6. **升降期間的高亮與剪影**：高亮、剪影用結果高度，補間中不跟著動（播放期間通常沒有高亮）；移動動畫開始時先隱藏該單位的剪影，重畫後再依新位置判斷。
7. **升起的震動**：用既有的震動等級 1、振幅再乘 0.6、時間為補間的 0.6 倍；「震動」版面設定關閉時不震。
8. **升降與浮動數字的時序**：升降不等待（與技能特效相同），浮動數字直接出現在結果高度。
9. **BattleRenderer.ts 從 815 行增為 924 行**：新邏輯大多拆到 `rowLayers.ts`、`heightArt.ts`、`heightShapes.ts`、`elevation.ts`；`draw()` 改成呼叫 `drawUnit`／`resumeLifts`，`setHighlights` 拆出 `markPen`、`drawFrames`。3-18b 也會改這個檔，若要再拆（例如把單位繪製搬出去）建議在 3-18b 一起做。

## 6. 代表性輸出節錄

```
=== 檢查結果摘要 ===
  ruff check             通過
  ruff format --check    通過
  mypy                   通過
  lint-imports           通過
  pytest                 通過
  client install         通過
  client typecheck       通過
  client test            通過

全部檢查通過。
```

戰鬥紀錄（築高台）：`(2, 3) 的高度 0 → 1／(1, 4) 的高度 0 → 1／(2, 4) 的高度 0 → 1／(3, 4) 的高度 1 → 2／(2, 5) 的高度 0 → 1`。
