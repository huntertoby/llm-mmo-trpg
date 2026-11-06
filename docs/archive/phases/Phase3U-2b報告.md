# Phase 3U-2b 報告｜戰場狀態圖示列移到腳邊

依 `docs/art/人物放大.md` 末節與 `docs/phases/Phase3U計畫.md` 第 4 節。只動 `client/src/render/unitSprite.ts`（＋新測試檔）。

## 做了什麼

| 項目 | 改動 |
|---|---|
| 位置 | 狀態列中心 y ＝ `T*0.36 − 4 − 圖示/2`：HP 條（含護盾條）正上方 4px、置中；仍在 `statusRow` 最後加入，畫在小人與光環之上 |
| 大小 | 新常數 `ROW_ICON_FEET = 11`（舊 `ROW_ICON` 14；48px 邏輯格 11、88px 格約 20px）；「+N」框圓角 3、字 8 |
| 上移規則 | 全部拿掉：`ROW_Y`、`ROW_RISE_HUMAN`（9.4）、`ROW_RISE_BEAST`（7.8）、高瘦 `buildRowRise`、形態 `formRowRise` 在 unitSprite 不再使用；「灌」徽章造成的右移 `ROW_INFUSED_SHIFT` 也拿掉（徽章在左上，不再碰到） |
| 避字母標記 | `rowShiftForMarker(n)`：整排右移到左緣離字母圓右緣 ≥ 1px（1 個圖示不用讓、2 個約 3px、3 個約 8.8px） |
| 不動 | 字母標記、召喚物回合數徽章、HP 條、`ROW_ICON`／`statusRowLayout` 預設值（`statusIcon.ts`，仍有測試使用） |
| 測試 | 新增 `unitSprite.test.ts`（3 項：列在 HP 條上方且在格內、88px 圖示約 20px、避字母標記） |

## 驗收

- tsc 通過；vitest 全量 **1154 passed**（119 檔）；`pnpm build` 通過。
- 排版煙霧檢查（內建瀏覽器，自己的 8044 埠，自己開的分頁；結束 `resize_window` desktop、關分頁、只殺自己的 PID）：1600×900、shortBottom、800×600 皆全 PASS。每次載入後第一次、或偶爾一次「更多動作選單開著時沒有說明卡」會 FAIL（滑過說明卡 0 張，為 hover 時序的既有現象，重跑即 PASS；與本段無關）。
- 截圖：`docs/phases/img/3U-2b-after-88.png`（`scale-gallery#cell88` 同一場面，headless Chrome、dpr 2；前圖為 `3U-2-after-88.png`）。

## 觀察（給美術 PM）
1. 狀態列不再離開自己的格子，不蓋臉、不壓上一格的單位或血條。
2. 3 個圖示時整排右移約 9px 讓字母標記，第三個圖示的右緣會略超出自己的格子右緣（接近格間縫）。若不想超出，可改最多 2 個圖示＋「+N」或再縮小。
3. 圖示現在會蓋住自己的腳與光環（規格要求）；召喚物右下的回合數徽章在 HP 條位置高度，與右移後的圖示不重疊。

## 待 PM 決定
1. **大小數字矛盾**：規格寫「約 60%」與「88px 格約 20px」；現行 14（邏輯 48px 格）在 88px 格是約 25.7px，60% 只有約 15px，20px 是約 78%。我採 20px（`ROW_ICON_FEET = 11`）。若要 60%（約 8.4）請告知。
2. 「灌」徽章時仍保留最多 2 格的排版（只拿掉右移）；徽章在左上已不衝突，可恢復為 3 格。
3. 3 個圖示右移後的右緣略超格（見觀察 2）。
