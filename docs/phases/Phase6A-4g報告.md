# Phase 6A-4g 完成報告：6A-4e／6C-2 驗收收尾

> 實作者 agent，2026-11-04。依據：`docs/art/6A-4d至6M-3六段檢查.md` 第 4 節、第 7 節第 3、4 項；`Phase6A-4e報告.md` 待決 2、6；`Phase6B-5報告.md`（出口半透明）；`Phase6C-2報告.md`；`Phase6A-4a報告.md`（地表併塊）。
> 只動 `client/`（另加截圖與本報告）。開工前已 `git merge main`、`git merge origin/claude/art-pm-8f4e6d`，無衝突。

## 交付

| 項目 | 檔案 | commit |
|---|---|---|
| 1. 戰鬥地圖左右鋪滿、HUD 塊底下有單位或可點格時半透明 | 新檔 `client/src/battle/hudFade.ts`（純函式）＋測試、新檔 `client/src/screens/battle/useHudFade.ts`；`BattleScreen.tsx`（接上 hook、`data-hud-faded`）；`styles/battle-hud.css` | `21ffe6a5` |
| 2. 敵人視野改成併塊、拿掉格角黑點 | 新檔 `client/src/render/regionBlobs.ts`＋測試；`render/BattleRenderer.ts`（`Highlights.regions` 與一段呼叫）；`world/fieldModel.ts` 的 `fieldHighlights`（＋測試） | `c41bdfbc` |
| 3. 刪除舊 SidePanel、ResizeHandle、欄寬設定與舊 CSS | 刪 `ui/SidePanel.tsx`、`ui/ResizeHandle.tsx`；`battle/layoutPrefs.ts` 只剩縮放；`ui/LayoutPanel.tsx`、`screens/battle/useBoardViewport.ts`、`battleTools.tsx`、`dev/layoutSmoke.ts`；CSS；新測試 `ui/legacyLayout.test.ts` | `deef54b5` |
| 截圖、報告 | `docs/art/6a4g_battle_800.jpg`、`6a4g_battle_800_faded.jpg`、`6a4g_encounter_sight.jpg`；本檔 | 最後一個 commit |

## 1. 地圖鋪滿＋HUD 半透明

- `.board-scroll` 的左右 inset 改回 0（上方行動順序列與底部列照舊扣掉）。800×600 單場戰鬥的自動縮放從約 65% 變成 **77%**（這張地圖是高度先頂到；寬的地圖會更明顯）。
- 規則沿用 6B-5：HUD 塊（含半格緩衝）底下有**單位**或**可點的格子**（移動、攻擊／目標、方向、攀跳落點）時，那一塊 `opacity: 0.38`，滑上去（`:hover`／`:focus-within`）恢復。
- 會判斷的塊：主角卡、選取面板、行動順序、右上戰況＋工具鈕、環境預告、召喚物面板、釘選小卡、左下紀錄。底部技能列與回合操作在地圖可用區域外，不判斷。
- 做法：`useHudFade` 每次重畫後、捲動與視窗大小改變時（一幀一次）量 HUD 各塊與畫布矩形，用 `tileClientRect` 把格子換成畫面矩形（含抬高），`fadedHudBlocks` 算出結果，寫到 `.battle-board` 的 `data-hud-faded`，CSS 用 `~=` 選擇器套半透明。React 元件不用各自加 class。
- 實機（無頭 Chrome、API 8308、vite 5311、存檔在 scratchpad 暫存資料夾；用完已停、暫存 vite 設定已刪）：
  - `__layoutSmoke.runCase` 在 **800×600、1040×624、1600×900 三種大小都全 PASS**，`scan()` 0 項；三種大小預設縮放下 HUD 底下沒有單位，`data-hud-faded` 為空。
  - 800×600 放大到 120% 再往下捲 110px，讓單位跑到左上、右上底下：`data-hud-faded="hero order corner"`，主角卡與戰況框的計算後 opacity 都是 0.38（`6a4g_battle_800_faded.jpg`）。

## 2. 遭遇時的紅色格子

- **查清楚黑點**：紅格是實地地圖上**敵人的視野**（`sightCells`），原本用環境預告的 `telegraph` 畫法，每格紅框＋右上角一個徽章底圓；視野的 `glyph` 是空字串，所以只剩黑色小圓。**黑點沒有任何意思**（不是起始區空位），所以直接拿掉，不另做圖示。滑過視野格照舊有說明「敵人的視野」（`hoverText`，本來就有）。
- 新的畫法：`fieldHighlights` 不再把視野放進 `telegraph`，改放 `Highlights.regions`（一組格子＋顏色）。`regionBlobs.ts` 重用 `surfaceBlobs` 的 `blobShape`／`blobEdges`：每格依四鄰與斜鄰算形狀，全部一次填淡紅（0.16），再只描露在外面的外緣（2px、0.8），接縫不描。門與傳送石那格照舊排除；精英的「精」照舊是小徽章。
- 繪製放新檔，`BattleRenderer` 只加了 `regions` 欄位與一段呼叫（沒動 `unitSprite`，`world/` 只改 `fieldModel.ts` 的 `fieldHighlights`，沒碰標記）。
- 實機：渡口石階（暫存伺服器多一條只在腳本裡的路由把角色搬到 (1, 6)），往東走一格觸發遭遇；遭遇卡、鏡頭框住戰場，視野是併成一塊的淡紅範圍（`6a4g_encounter_sight.jpg`）。

## 3. 刪除舊版面

- 刪：`SidePanel.tsx`、`ResizeHandle.tsx`；`layoutPrefs` 的 `sideWidth`／`bottomHeight`／`heroWidth`、`layoutLimits`、`dragValue`、`clampTo`、`SIDE_MIN` 等（`LayoutPrefs` 只剩 `zoom`；以前存下的舊欄位讀取時忽略，存檔鍵不變）；`LayoutPanel` 的三條滑桿與 `hudA`／`limits`／`narrow` 參數；`useBoardViewport` 的 `limits`、`layoutStyle`（`--side-w` 等 CSS 變數）。
- 排版煙霧 `dev/layoutSmoke.ts`：拿掉三條拖曳線的量測與檢查（`bottomHandle` 等欄位、`handleCheck`、`LEGACY_HANDLE_CHECKS`、`no-handles` 項）與 `shortBottom` 選項。
- CSS：`.resize-handle*`、`.battle-screen.side-collapsed`、`.battle-side*`、`.side-toggle*`、`.side-telegraph`、`.battle-hero*`（含窄螢幕版）、`log-dock.css` 的 `.battle-side.no-log .side-telegraph`；`var(--side-w/--hero-w/--bottom-h, 預設)` 換成原本的預設值。
- `floatCardRule.test.ts` 的白名單拿掉 `.resize-handle`。
- 新測試 `ui/legacyLayout.test.ts`：掃原始碼（不含註解與測試檔）與樣式，確認沒有 `SidePanel`、`ResizeHandle`、舊設定名稱、舊 class 與 CSS 變數。

## 測試

- 新增：`battle/hudFade.test.ts` 7 項（格子換算；單位在 HUD 塊下、可點格在下含緩衝、都沒有、多塊順序與量不到的塊）、`render/regionBlobs.test.ts` 4 項（兩格併塊接縫不描、單格、3×3 中間整格、去重與固定）、`ui/legacyLayout.test.ts` 3 項；改寫 `world/fieldModel.test.ts` 視野 2 項、`battle/layoutPrefs.test.ts`、`dev/layoutSmoke.test.ts`。
- `vitest run src/world src/render src/battle src/ui src/dev src/screens`：149 檔 **1513 項全通過**。
- `tsc --noEmit`、`pnpm build` 通過（只有原本的 chunk 大小警告）。
- 沒跑全量 `scripts/check.py`（照規定）。

## 待 PM 決定

1. **上下沒有鋪滿**：照派工只把左右 inset 改 0；上方行動順序列（52px）與底部列仍扣掉。要不要連上下也鋪滿（行動順序與底部列也套半透明），請決定。
2. **半透明的判斷範圍**：照 6B-5 用「格子＋半格緩衝」，只看單位所在格，沒把單位頭頂（站在格子上方約半格）算進去；選技能時的淡色施放範圍（`range`）與影響預覽不算「可點的格子」。
3. **右上戰況框整塊一起變淡**：工具鈕的彈出面板在戰況框裡面，戰況框變淡時，滑鼠離開彈出面板後面板也跟著變淡（滑回去恢復）。
4. **抬高的格子**：視野併塊每格照自己的抬高位置畫，高台邊上的接縫會錯開一點（截圖中段石階可見）；和地表併塊的現況一致。
5. **其他沒用到的舊 CSS**：`battle-layout.css` 裡還有 `.battle-bar`、`.save-note`、`.skip-toggle`、`.top-popup-empty`、`.turn-controls-row`、`.turn-objective`、`.turn-round`、`.hud-row` 在原始碼裡找不到引用，但不是這次指定的舊版面（窄欄／分隔線／欄寬），保守起見沒刪。
6. `docs/開發PM交接.md` 若有提到 `runCase` 的 `shortBottom` 選項或拖曳線檢查，需要 PM 順手改（這段只動 `client/`）。
