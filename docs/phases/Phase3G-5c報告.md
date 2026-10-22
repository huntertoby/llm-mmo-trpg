# Phase 3G-G5c 報告：紙娃娃與圖示小修

> 實作者：implementer。依 `docs/art/3G-5b檢查.md` 做小修，只動前端繪圖與色票；沒有改引擎、API、`styles.css`。

## 逐條對照

| # | 項目 | 結果 |
|---|---|---|
| 1 | 雙匕首放大 | 通過。刃長 ×1.35（刃尖 -10 → -12.8）；成對匕首兩把各往外多 2px（`drawFigure` 的 `spread`，只在主副手都是匕首時）；刃色混白 15%。截圖 `img/3G-5b-paired.png`（已覆蓋） |
| 2 | 鐵、鋼色票統一 | 通過。`appearance.ts` 的 `MATERIAL` 改為鐵 `#6e757d/#474c52`、鋼 `#a9b6c6/#6d7a8a`，與 `artPalette.ts` 的圖示色票相同；舊單位（鐵鋼武器、鎖甲、板甲）因此略暗 |
| 3 | 拿掉裝備稀有度外光 | 通過。`dollGear()` 不再回傳 `rarity`，`resolveDoll` 只保留範本的 `rarity`（頭目記號）。測試改為「裝備稀有度不影響外光；bandit_boss 仍為 epic」 |
| 4 | 銅改色、鱗片紋 | 通過。銅 `#b06a3c/#6e3e20`，圖示（`artPalette.ts`）與紙娃娃（`appearance.ts`）同步；鱗片紋改為暗色描邊弧線、線寬 1.2px（`drawMailPattern`）。截圖 `img/3G-5c-copper.png`、`img/3G-5b-sets.png`（已覆蓋） |
| 5 | 手部形制辨識度 | 依 PM 決定接受現狀，未做 |

## 驗收

- vitest 全過（59 檔、642 項）、`tsc --noEmit`、`vite build` 通過。
- 完整 `scripts/check.py`：見交付訊息（最後執行一次）。
- 截圖用 `client/doll-gallery.html`（臨時 vite 埠 5199，已關閉；未動使用者的 8000 埠）。

## 待 PM 決定

- 無阻擋項。觀察：鱗甲暗色描邊在小尺寸下已能看出鱗片又不像膚色；鐵鋼變暗後，鐵盔與背景（#2b2f38）對比略降，若覺得太沉可再微調鐵的主色。
