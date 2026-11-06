# Phase 6A-4c 報告：戰鬥 D 版③——選移動時的路徑畫法、格子浮出、區外變暗

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6A-4c 列（含併入的 6A-3 驗收結論）；`docs/design/05-戰鬥.md` 5.10（冰面滑倒、不滑行）；`docs/archive/art/戰鬥D版樣張.md` 第 3、5、6 節（worktree 上仍是舊版說法，照 6A-4c 列：冰面小牌「滑倒 xx%・失敗停在這格」、冰面滑倒不放驚嘆號）。`docs/archive/art/6A-3與6A-4a檢查.md` 不在 main，照 6A-4c 列的文字做。

開工先合併 `worktree-agent-a2b7add5fd43e85ca`（6A-4b）與 `main`，沒有衝突。只動 `client/`（另加 3 張截圖與本報告）；沒有改後端，也沒有新增相依。path-preview 的回應欄位夠用，沒有缺。

## 1. 交付內容

### 1.1 選移動時的路徑（資料全部來自伺服器）

- `client/src/battle/pathPreview.ts`（純函式）：把 `PathPreviewOut` 轉成要畫的東西（`pathDraw`）。
  - **分段顏色**（`stepKind`）：走進那一格的段。
    - 白實線：一般；
    - 藍虛線 `#1e78d0`：冰面；
    - 紅實線：陷阱或火（另含 `deadly`）；
    - 灰虛線：到不了，包含 `reach` 為 `unreachable` 和 `interrupted`。
    - `possible` 的段畫淡一點（alpha 0.6）。
  - **每格中心一個點**（不含起點）。伺服器回傳「完全沒有路」（起點＋終點不相鄰）時不畫線，只標到不了。
  - **特殊格外框**：只框走得到的格子。冰是藍，陷阱與火是紅，油是油色。
  - **結果小牌**：一格最多一張，各段用「・」接；不確定的事件加「（可能）」。
    - 「滑倒 45%・失敗停在這格」：機率取 `chance_permille`。滑倒造成的倒地不另寫。
    - 「陷阱 −8・定身（可能）」：傷害只算放陷阱那個人造成的部分。
    - 「點燃」「潮濕」：潮濕看格子的表面是不是水。
    - 另有：反應（藉機攻擊等）含傷害、墜落、致命地形、其他狀態、其他傷害、倒下。
  - **驚嘆號**：放在有 `stopped` 事件的格子（被陷阱定住、被打斷）。
    - 冰面滑倒（`prone` 且同格有 `slip_check`）不放；撤離也不放。
    - 被移走（`displaced`）時放在新位置。
  - **「到不了」**：終點的 `reach` 是 `unreachable`／`interrupted`，或 `reachable: false` 時，終點畫虛線框＋淡影，下方加「到不了」小牌。
  - `hoverPathQuery` 決定要問哪條路徑：
    - 走得到的格子：用 `classifyActions` 那個移動動作的 `path`（和點下去實際送出的一致）；
    - 走不到的空格：只給 `dest`；
    - 滑過自己、單位、地圖外，或不在選移動時，不問。
- `client/src/battle/pathFetch.ts`（`PathPreviewFetcher`）：**節流 120ms＋快取**。
  - 第一次立刻送；120ms 內滑過的格子，時間到時只送最後一格。
  - 同一條路徑在同一個戰鬥狀態下只問一次；送出中的請求不重送。
  - 晚到的舊回應只進快取，不蓋掉目前的結果。
  - 戰鬥狀態改變（`response` 換了）時清快取，之前送出的請求作廢。
  - React 包裝在 `client/src/ui/usePathPreview.ts`；API 是 `api.pathPreview`（`client/src/api/client.ts`）。
- `client/src/battle/pathGeometry.ts`：
  - `roundedPieces`：直線段加圓角，轉角的弧前半屬於進來的段、後半屬於出去的段，換色點在轉角正中間；
  - `dashRuns`：依弧長切虛線；
  - `outerEdges`：格子群的外緣。
- `client/src/render/pathArt.ts`：畫法，畫筆用介面，測試用紀錄器代替 Pixi。
  - 路徑：黑色底線＋彩色線，粗 4，轉角半徑 12，虛線 7／5；
  - 每格的點、外框、虛線框、紅色驚嘆號泡泡；
  - 小牌：深色圓角底、圖示色邊；圖示是自己畫的冰菱形、陷阱圈、火、水滴、斜線、狀態點；
  - `placeTags`：小牌依序試右上、右下、左上、左下，避開已放的小牌和驚嘆號；四個位置都疊到時往上疊。
- `BattleRenderer.setHighlights` 新增 `path`、`range` 兩個欄位（選填）。路徑畫在其他高亮之上，驚嘆號最後畫。`useHighlights` 只在選移動時接上路徑預覽：主角回合，沒有選技能、指揮、灌注、隊友指令，也沒有滑過面板按鈕。

### 1.2 格子浮出、戰鬥區外變暗

- **可走格**（`MOVE_SOFT`）：每格內縮的圓角方塊，白描邊（alpha 0.75）＋藍填色 `#5aa8ff`（alpha 0.34）；外緣加亮線 `#c8e4ff`。冰湖與水上都看得出來。
- **選技能時**（`range` ＝ 合法目標格）：
  - 整張圖的格線極淡地浮出（白色，alpha 0.07）；
  - 施放範圍用極淡的暖色圓角格，外緣加亮線；
  - 預覽命中範圍改成橘色圓角格，外緣加亮線；
  - 目標紅框改成圓角。
- **戰鬥區外柔和變暗**：
  - 戰場外圍一圈柔和的暗影：`.battle-canvas` 的 box-shadow；
  - 邊緣往內淡淡的暗角：`BattleCanvas` 內的 `.battle-vignette`，不擋滑鼠。
  - 現在的戰鬥地圖就是整張畫布，沒有「戰鬥區」的範圍資料，所以暗角做在畫布邊緣。

### 1.3 併入的 6A-3 驗收結論

- **選取時紀錄縮短讓開**（`battle/logRoom.ts`、`screens/battle/useLogRoom.ts`）：
  - 選取中（選技能、基本動作，或隊友指令）量選取面板的底邊；面板或戰場大小改變時重量（ResizeObserver）。
  - 底部固定；最大高度 ＝ 選取面板底下到紀錄底部、留 8px，也不超過原本的 58%。
  - 不到 3 行時，固定成 3 行的高度（`tight`），可以捲動，捲到最新一行。
  - 選取結束就恢復。釘住的也縮。
  - 瀏覽器實測（800×600，選「點燃」並展開紀錄）：選取面板底邊 174，紀錄上緣 190.8，class 是 `log-dock open squeezed`；按 Esc 後恢復成 `log-dock`。
- **「已選定○○」留在「?」旁**：
  - `OpHint` 多一個 `tag`，說明句收進「?」後，在「?」旁畫小標籤（`.op-hint-tag`）；
  - 兩段選取用 `hurlPickedTag`（已舉起／已選定／已鎖定），複合技能用 `compositePickedTag`；
  - 說明句裡也改用同一個函式組字，兩邊一致。

## 2. 測試

- 新增 `client/src/battle/pathPreview.test.ts`（26 個）：
  - 分段與顏色（白／藍虛線 `#1e78d0`／紅／灰虛線、可能段）；
  - 外框；「完全沒有路」不畫線；
  - 小牌文字（滑倒 45%、陷阱 −8・定身（可能）、點燃、潮濕、到不了的格子不出牌、傷害數字）；
  - 停點驚嘆號（陷阱定住有、冰面滑倒沒有、被移走放新位置、撤離沒有）；到不了；
  - 要問哪條路徑；圓角與虛線幾何；外緣；
  - **節流**：第一次立刻送，120ms 內只送最後一格；**快取**：再滑回來不重送；舊回應不蓋掉；狀態改變後清掉；
  - 畫法（紀錄器）：底線與各段顏色、冰面虛線、點、外框、虛線框、驚嘆號、可走格的白描邊與外緣；
  - 小牌不互相疊。
- 新增 `client/src/ui/logRoom6a4c.test.ts`（7 個）：
  - 最大高度＝面板底下到紀錄底部留 8px；
  - 沒有選取時不限；空間夠時縮短（不超過 58%）；不到 3 行時固定 3 行；釘住的也縮；
  - 「?」旁的小標籤；小標籤與說明句一致。
- 執行結果：
  - `vitest run src/ui src/screens src/battle/{pathPreview,composite,targeting,legend328,scenePreview}.test.ts`：22 個檔案、228 個全過；
  - `tsc --noEmit` 通過；
  - `corepack pnpm -C client build` 通過（只有原本的 chunk 大小警告）；
  - 瀏覽器 console 沒有錯誤；
  - 網路：滑過 3 格再滑回，`path-preview` 只送 3 次。
- 沒有跑全量，照規定。

## 3. 截圖（`docs/art/`，800×600）

- `6a4c_path_plain.jpg`：一般路徑。冰湖，主角往上再往右，白線、圓角、每格一點；可走格是白描邊＋藍填色，外緣亮線；戰場邊緣暗角。
- `6a4c_path_ice_trap.jpg`：經過陷阱與冰。
  - 陷阱格紅線、紅框，小牌「陷阱 −6～14・定身（可能）」，上方紅色驚嘆號（可能被定住）；
  - 之後兩格冰：藍虛線、藍框，小牌「滑倒 55%・失敗停在這格（可能）」，沒有驚嘆號。
- `6a4c_path_unreachable.jpg`：到不了。前段白線、冰上那段藍虛線（小牌「滑倒 55%・失敗停在這格」），超出移動點數的後半段灰虛線；原終點虛線框＋淡影，標「到不了」。

截圖做法：
- 冰湖地圖本身沒有陷阱，敵人也不一定會放，所以截圖用的本機伺服器是 scratch 腳本（不進版控）：照常 `create_app`，每場開局後在主角東邊兩格放一個已揭露的敵方陷阱。
- 路徑預覽照樣由伺服器的引擎算，前端沒有任何假資料。
- 伺服器開在 8297 埠，存檔放在暫存資料夾，用完已停掉；沒有碰 `saves/`。

## 4. 待 PM 決定（都已照最保守的做法做完）

1. **選移動時，滑過空格不出格子資訊卡**：
   - 原因：資訊卡會整塊蓋住路徑和小牌（實測很嚴重）。所以畫出路徑提示時不出空格的資訊卡，地表效果已經寫在小牌上。
   - 單位的資訊卡照舊；選技能時照舊。
   - 規格沒寫，如果要保留資訊卡，可以改成延遲出現或放在別處。
2. **一格最多一張小牌**：連續兩格冰會各自寫「滑倒 55%・失敗停在這格」，畫面比較擠。要不要合併成一張（例如「冰 2 格・各 55%」），請決定。
3. **陷阱的「（可能）」**：前面有冰（可能滑倒停下）時，陷阱本身也會標「（可能）」，例如「陷阱 −6～14（可能）・定身（可能）」，忠於伺服器的 `certain`。
4. **驚嘆號也放在「可能」的停點**：例如定身要過抵抗時。只有冰面滑倒、撤離不放。
5. **紅色段的範圍**：除了陷阱、火，致命地形（`deadly`）也算紅。另外加了反應（藉機攻擊）、墜落、倒下的小牌段（圖示是斜線）。
6. **走不到的格子也會問 `dest`**：滑過走不到的空格時，伺服器給最長的合法前段，終點標到不了。牆、深淵這類完全沒有路的格子只標「到不了」框，不畫線。
7. **淡影的畫法**：用白色淡填色代表淡影，沒有像樣張那樣畫主角的半透明殘影。殘影要用紙娃娃，等 6A-4d 的動畫方案。
8. **戰鬥區外變暗做在畫布邊緣**：目前沒有「戰鬥區」的範圍資料（整張圖就是戰場），所以做成畫布外圈暗影＋邊緣暗角。之後如果就地開打有更大的場景，可以改成真的區外變暗。
9. **紀錄縮短只在「選取」時**：選技能、基本動作、隊友指令時才縮。只是滑過敵人、出現預覽框時不縮（避免紀錄一直跳）。
10. **不到 3 行時固定 3 行**：這時紀錄會疊到選取面板下面（面板在上層），只看得到最新 3 行。

## 5. Commit

- `ede46417` feat(client): path preview drawing, soft tile lift and battle vignette (6A-4c)
- `1bff85c2` feat(client): log dock shrinks during selection, picked tag beside op hint (6A-4c)
- `0cc771da` feat(client): non-overlapping path tags, hide tile card over path; 6A-4c screenshots
- 報告：最後一個 commit

## 6. 範圍

- 新檔：
  - `battle/pathPreview.ts`、`battle/pathGeometry.ts`、`battle/pathFetch.ts`、`battle/logRoom.ts`；
  - `render/pathArt.ts`、`ui/usePathPreview.ts`、`screens/battle/useLogRoom.ts`；
  - 兩個測試檔。
- 修改：
  - 只加 API 方法與型別：`api/client.ts`、`api/types.ts`；
  - 高亮與路徑：`render/BattleRenderer.ts`（`setHighlights` 與新的 `drawPath`）、`screens/battle/useHighlights.ts`；
  - 暗角：`ui/BattleCanvas.tsx`；
  - 紀錄與「?」：`ui/BattleLogDock.tsx`、`ui/OpHint.tsx`、`ui/ActionPanel.tsx`、`screens/BattleScreen.tsx`；
  - 抽出小標籤函式：`battle/targeting.ts`、`battle/composite.ts`；
  - 樣式：`styles/battle-layout.css`、`styles/log-dock.css`。
- 沒有動 `client/src/world/`、`WorldScreen.tsx`、HUD 相關、ink 系列。
- 為了建置與測試，在 worktree 執行了 `corepack pnpm -C client install --frozen-lockfile --prefer-offline`，照 lockfile 安裝，沒有新增相依。
