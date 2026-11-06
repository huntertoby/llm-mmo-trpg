# Phase 3E-2d 報告｜前端點擊式選單與 Esc 衝突

> 範圍：`client/`（F1、F2、F8、F12）。分支 `worktree-agent-a0b3b78a1de478715`，未 push。

## 做了什麼

1. **共用 `usePopupMenu`**（`client/src/ui/usePopupMenu.ts`）：Esc 關閉並 `stopPropagation()`、點外面關閉（`.float-card` portal 不算外面）、同時只開一張（模組層級登錄，新開的先關舊的）、可受控（頂端面板）或自管（更多動作）。
2. **改用它**：`TurnControls.tsx` 的 `.more-list`；`BattleTopBar.tsx` 的 `.top-popup`（抽成 `TopTool` 子元件，原 `<span>` 改 `<div>`）。CSS 新增 `.popup-menu`（`position: absolute; z-index: 30; overflow-y: auto; overscroll-behavior: contain`），`.more-list`、`.top-popup` 只留位置與尺寸；`.more-list` 最大高度改 `min(50vh, 360px)`。
3. **Esc 衝突（F1）**：`useFloatCard.tsx`、`useTileCard.ts` 的 document keydown 處理 Esc 時 `stopPropagation()`，BattleScreen 的 window 監聽不再取消瞄準。`BattleScreen.tsx` 移除已失效的「`popup !== null` 時 Esc」分支（改由 hook 處理）。
4. **`.decision-card`（F8）**：`max-height: calc(100vh - 70px); overflow-y: auto`。
5. **規則測試（F12）**：`floatCardRule.test.ts`
   - **發現舊 CSS 規則形同虛設**：vitest 不處理 CSS，`import styles from "../styles.css?raw"` 在測試裡是空字串（長度 0），所有 CSS 規則都是對空字串空過。改成 `node:fs` 直接讀檔（加 `@ts-expect-error`，專案沒裝 `@types/node`），並加「讀到的 CSS 長度 > 10000」守門測試。改讀真檔後，原有的 `position: fixed` 白名單規則仍全過。
   - 新增：CSS `position: absolute/fixed` 且 `z-index ≥ 20` 只能是 `.float-card`、`.unit-float`、`.decision-card`、`.popup-menu`、`.resize-handle`；`.more-list`／`.top-popup` 不得自己定位；`.decision-card` 要有 `max-height` 與 `overflow-y: auto`；`MUST_USE_POPUP_MENU`（`BattleTopBar`、`TurnControls`）必須呼叫 `usePopupMenu` 並套 `popup-menu`；hook 必須含 `stopPropagation()` 與 `pointerdown`。
   - `role=tooltip` 規則收緊為只能出現在共用元件（`SHARED`），不再以「檔案內有 FloatCard」放行。
   - 原始碼掃描由只掃 `.tsx` 擴到 `.ts`（排除測試與 `.d.ts`）。
   - 移除 `.modal-backdrop` 規則與白名單；一併移除無人使用的 `.fallback-list`（舊規則抓不到，新規則會擋）。
6. **順手**：`summonArt.ts` 藤蔓底影移到「不加外框」的 `drawSummonGround`，透明度 0.45 → 0.35。

## 驗收

- `corepack pnpm -C client exec vitest run`：72 檔、762 測試全過。
- `corepack pnpm -C client typecheck`：通過。`corepack pnpm -C client build`：通過（僅既有的 chunk 大小警告）。
- 未跑 `scripts/check.py`、未跑 Python 測試（只動 `client/`）。

## 瀏覽器實測

自己啟動 `trpg serve --port 8100`（serve 建置後的 `client/dist`），瀏覽器窗格 1024×768（等比縮成 800×600 截圖）；詢問視窗另以 `resize_window` 設成 800×600。測完已關閉伺服器（沒有動使用者的 8000／8001）。

| 項目 | 結果 |
|---|---|
| 「更多動作」點開 → Esc | 關閉 |
| 「更多動作」開著 → 點「反應設定」 | 只剩頂端面板一張（`.popup-menu` 數量 1） |
| 頂端面板（反應設定、圖例）→ Esc | 關閉 |
| 頂端面板 → 點空白處 | 關閉 |
| 頂端面板內容超高（JS 把 `max-height` 設 150px） | 可在面板內捲到底（`scrollTop` 172），面板不關閉 |
| 選技能進入瞄準（紅格）＋滑到技能按鈕顯示技能卡 → Esc | **第一次 Esc 只關卡片，瞄準仍在；第二次 Esc 才取消瞄準** |
| 800×600 詢問視窗（`.decision-card`，JS 注入 30 行假內容） | 高度 ≤ 530px、頂 58／底 588 都在視窗內，捲到底看得到底部按鈕 |

限制與註明：
- **截圖沒有存成檔案**：瀏覽器窗格的截圖只回傳在對話裡，無法寫進 `docs/phases/img/`，所以沒有 `3E-2d-*.png`。
- 瞄準＋卡片的實測是「滑過顯示」的技能卡；用 click 釘住與滑過走同一個 document keydown 處理（`useFloatCard`），沒有另外分開實測釘住版。
- 詢問視窗用注入的 `.decision-card` 元素驗證 CSS（要觸發真實的反應詢問太繞）。
- 「更多動作」目前只有 1 項，無法真實測內容超高；捲動由 `.popup-menu` 的 `overflow-y: auto` 保證，與頂端面板同一條 CSS。
- 畫布點擊正常，沒有改用 JS 驅動。藤蔓底影只有單元測試與型別檢查，沒有目視（測試戰鬥沒有召喚藤蔓）。

## 待 PM 決定

1. **Esc 不再取消隊友指令選目標**：原本 BattleScreen 在頂端面板開著時，Esc 會關面板並順便 `cancel()`；現在由 hook 只關面板（與浮動卡一致），再按一次 Esc 才取消瞄準。若要維持舊行為，要在 `BattleTopBar` 加關閉回呼。
2. **點外面關閉頂端面板會連點到地圖**：pointerdown 關面板後，同一下 click 仍會送到棋盤（與浮動卡釘住版一致）。若要「第一下只關面板」需要另做 capture 攔截。
3. **更多動作與浮動卡／頂端面板的互斥**：「同時只開一張」目前只在點擊式選單之間互斥；浮動卡（滑過）與選單可並存。
4. **CSS 規則測試原本是空過**（見上）：其他測試若也用 `?raw` 讀 CSS 或其他非 JS 資源，建議排一次盤點。
5. `.resize-handle`（`position: absolute; z-index: 20`）列為版面例外，不是彈出層。
6. 截圖無法存檔，PM 若要留存請在本機瀏覽器補拍。
