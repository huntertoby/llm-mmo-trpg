# Phase 3T-4d 報告｜武器小圖示微調

> 依 `docs/art/3T-4c檢查.md`，只動小圖示模式（`render/inkWeapons.ts`）；戰場小人畫法不變。

## 完成
- 指虎：直立；方塊壓扁（寬 11.2、高 5）；4 個相連半圓指節（高 1.75 ＝ 方塊 35%）；握孔改橫向長條（6.8 x 1.6）。
- 矛：矛頭疊加 4/3 倍（配合既有 1.5 倍 ＝ 原尺寸 2 倍）；戟維持 1.5 倍。
- 霰彈槍：槍托縮為約 60%，改往左下收窄的楔形；雙管不動。

## 驗收
- `tsc --noEmit`、`pnpm build` 通過；`vitest run src/render src/battle src/ui` 93 檔 890 測試全過（含 `weaponIcon3t4c.test.ts` 非圖示模式雜湊不變）。未跑 `check.py`。
- 對照圖：`img/3T-4d-after-28px.png`（28px、2x）、`img/3T-4d-after.png`（96px）。

## 待 PM 決定
1. 矛頭 2 倍後長度占全長比例以全圖縮放計可能超過 25%（規格兩句數字互相有出入，我以「2 倍」為準）；請看圖判斷。
