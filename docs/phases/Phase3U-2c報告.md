# Phase 3U-2c 報告：戰場狀態圖示最多 2 個＋「+N」角標

## 做了什麼（只動 `client/src/render/unitSprite.ts` 與其測試）

- 狀態列一律最多 `ROW_MAX_ICONS = 2` 個圖示（有「灌」徽章時也一樣），依 `sortStatuses` 優先序取前 2；超過時在第 2 個圖示右上角疊小圓「+N」角標（半徑 4.5、字 7），不多佔一格。圖示大小維持 `ROW_ICON_FEET = 11`（88px 格約 20px）。不再使用 `statusRowLayout` 的第 3 格與整格「+N」。
- 新增 `rowPlacement(n, badgeLeft)`：整排放在字母標記右緣與召喚物回合數徽章左緣之間。一般單位間距 12（兩圖示含角標不出格）；召喚物（右下有回合數徽章）空間只有約 20px，容不下 2 個 11px 圖示，間距縮到約 8（圖示大小不變，兩圖示輕微重疊 3px），不蓋到回合數。`rowShiftForMarker(n, pitch)` 增加間距參數（預設值與原行為相同）。
- 測試：`unitSprite.test.ts` 新增 3 項（最多 2 個、一般單位不出格不碰標記、召喚物擠在標記與回合數之間）。

## 驗收

- tsc 通過；`src/render` 31 檔 316 項、完整 vitest 119 檔 1157 項全過；build 通過。
- 排版煙霧檢查：1600×900、1600×900 加 `shortBottom`、800×600 三情況全 PASS（每情況先 `localStorage.clear()` 再 navigate）。
- 截圖：`docs/phases/img/3U-2c-after-88.png`（`scale-gallery#cell88`，headless Chrome、dpr 2；場面每個單位 3 個狀態，皆顯示 2 個圖示＋「+1」）。
- 預覽伺服器埠 8054，已用自己的 PID 關閉；視窗已 `resize_window` 回 desktop。

## 待 PM 決定

1. 召喚物（有回合數徽章）時兩圖示輕微重疊（約 3px）是為了不出格、不蓋回合數；若要完全不重疊，需縮小圖示或移動回合數徽章（後者在 `unitLook.ts`，不在本段範圍）。
2. 召喚物同時帶定時炸彈時，回合數徽章左移 16px，狀態列已沒有空間，目前以最小間距 6 硬排（可能與炸彈／回合數徽章相鄰）；此情況極少見，未另處理。
