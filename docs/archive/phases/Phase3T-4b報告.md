# Phase 3T-4b 報告｜武器小圖示重調＋單一火色

> 實作：sonnet implementer，2026-10-29。只動前端。依 `Phase3T計畫.md` 3.2 與 `docs/art/3T-4檢查.md`。

## 1. 完成項目

1. **單一火色**：`artPalette.PAL.fire`、`statusIcon`（infused_fire）、`glossary`／`telegraph` 的炸彈色（0xff7a1a）全改 `#ff6a1a`。非測試程式已無 `#ff7a1a`（`palette.ts` 檔頭註解的歷史說明、測試裡的任意顏色參數保留）。
2. **武器小圖示改向量直繪**（`render/weaponIcon.ts`）：先在暫時畫布畫一次只量外框（不顯示），算縮放後在圖示大小直接重畫，不再放大點陣圖。
   - 墨線寬：新增 `inkStyle.withIconMode`（`lineScale`、`headScale`，跟著畫布走、結束還原，小人與戰場不受影響）；`ink`／`stroke`／排線的寬度乘 `lineScale`，使圖示上主墨線約 1.2px（28px 圖示，其他尺寸等比）。
   - 縮放：外框長邊填滿圖示 80%（留白各 10%）；45° 斜放時外框近正方，對角線同樣約 80%。
   - 頭部放大 1.5 倍（`inkStyle.iconHead`，以頭與柄交接處為中心，柄不變，墨線寬度除回去）：斧（兩刃）、錘（錘頭）、錘矛（球與凸緣）、鐮刀（刃）、法杖杖頭（光暈、爪、球）、權杖（環與寶石）。
   - 錘頭在小圖示模式用尖角橫長方塊（`sharp`），錘矛維持圓頭。
   - 一律 45° 斜放：槍弩（槍口朝 +x）逆時針 45°，其餘順時針 45°；小圖示模式不再加握法傾斜（`leanOf`）。`isDiagonal` 改為恆真並新增 `iconAngle`。
3. 開發用一覽頁 `client/weaponicon-gallery.html`（`?px=28`）列全部武器 kind 與主要形制。

## 2. 驗收

- `tsc --noEmit`、`pnpm build` 通過；`vitest run src/render src/battle src/ui`：92 檔 886 測試全過（新增 `weaponIcon.test.ts`、`inkStyle.test.ts` 小圖示模式 2 測；`weapons3i1.test.ts` 的 fist 斜放預期改為 true）。未跑完整 `check.py`。
- 小人／戰場畫法未動（icon 模式只在 weaponIcon 開啟；`leanOf` 只在 icon 模式回 0）。未另做 doll／gear gallery 位元比對（**待 PM 抽查**）。
- 前後對照（headless Chrome，`?px=96`；每格＝一種 kind／形制）：
  - 前：`img/3T-4b-before.png`
  - 後：`img/3T-4b-after.png`
  - 實際 28px（2x 螢幕）：`img/3T-4b-after-28px.png`

## 3. 待 PM 決定

1. 規格「墨線約 1.2～1.5px」解讀為 28px 圖示上的 CSS 像素，取下限 1.2（1.35 時細木柄全被墨線蓋住）。若要改，只動 `LINE_PX`。
2. 「一律 45°」連弓、法杖、拳套也斜放（原本直立）；槍弩朝右上。
3. 頭部放大未含：圖騰杖、連枷球、矛頭、戟斧（規格未列）。
4. 手槍、霰彈槍、拳套、匕首本身的造型（護手圓盤、槍握把大塊）沒動，在圖示上仍偏糊／偏大，屬造型而非畫法問題。
5. 外框量測用 lineScale=1 的細線，最終加粗後外緣略超出約 1px，被 10% 留白吸收。
6. `client/weaponicon-gallery.html` 與 `src/dev/weaponIconGallery.ts` 新增為開發頁（不進正式 build），可刪。
7. 英雄面板實際畫面未做實機截圖（以一覽頁 28px 代替）。
