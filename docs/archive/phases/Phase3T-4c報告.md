# Phase 3T-4c 報告｜短武器圖示造型

> 實作：sonnet implementer，2026-10-29。只動前端圖示（小圖示模式），依 `Phase3T計畫.md` 3.4 與 `docs/art/3T-4b檢查.md`。

## 1. 完成項目（全部只在 `inIconMode` 生效，小人與戰場畫法不變）

| 武器 | 圖示造型 |
|---|---|
| 手槍 | 不斜放（`iconAngle` ＝ 0，槍口朝右）；側面 L 形：鋼色槍管橫向、握把從槍管後端往左下斜（長約槍管一半）；尖角（`sharp`） |
| 拳套 | 正面指虎：鋼色方塊、上緣 4 個圓指節、下方深色握孔、無尖刺；**直立不斜放** |
| 霰彈槍 | 雙管上下並排，長度 16.5（長槍 22 的 75%），槍托較寬（高 6.8，原 5.6）；`blunderbuss` 喇叭口維持原樣 |
| 匕首 | 護手改細橫桿（寬 4.4 ＝ 刀身 2 倍、厚 0.9）；補握柄與刀身（長 8）合計全長約 13，刀身約 60% |
| 矛、戟 | 矛頭、戟斧頭用 `iconHead` 放大 1.5 倍（以頭柄交接處為中心） |
| 連枷 | 鏈與球放大 1.5 倍 |

程式：`render/inkGear.ts`（匕首）、`render/inkWeapons.ts`（其餘）、`render/weaponIcon.ts`（角度）。

## 2. 驗收

- `tsc --noEmit` 通過、`pnpm build` 通過；`vitest run src/render src/battle src/ui` 全過（含新增）。未跑 `check.py`。
- **小人不受影響的證據**：新增 `weaponIcon3t4c.test.ts`，對 10 種造型（匕首、手槍、左輪、拳套、指虎、霰彈槍、雙管、矛、戟、連枷）記錄非圖示模式的全部 canvas 呼叫並取雜湊，與 3T-4c 之前（HEAD~1 的程式）算出的雜湊逐一相同；另測圖示模式與非圖示模式不同、矛頭有 1.5 倍縮放、拳套有 6 個填色形狀。
- 對照圖（headless Chrome，`client/weaponicon-gallery.html`）：`img/3T-4c-after.png`（96px 每格）、`img/3T-4c-after-28px.png`（實際 28px、2x 螢幕）。前圖可看 `img/3T-4b-after*.png`。

## 3. 待 PM 決定

1. 拳套「正面指虎」直立不斜放（規格只明說手槍不斜放；斜放 45° 會讓指節與握孔難讀）。若要斜放，改 `iconAngle`／`isDiagonal` 兩處。`weapons3i1.test.ts` 的 fist 預期因此改回 `false`。
2. 28px 下指節只有約 1px 高，指虎輪廓靠方塊＋握孔辨識；若覺得不夠可加大凸起（`drawFistIcon` 的半徑 1.8）。
3. 28px 下矛與戟已可分（戟頭有側刃），但矛頭放大後仍偏小，因為整支長柄武器以全長縮放。
4. 霰彈槍槍托在圖示上偏大塊（不放大無法顯示「較寬」），請美術 PM 看圖判斷。
5. 匕首原本沒畫握柄，圖示模式補了一段短握柄（深褐 `#3a2a1c`）；非圖示模式不動。
6. 手槍變體（左輪、燧發、derringer）沿用同一個圖示握把與槍管，圓筒、擊錘仍照原畫。
7. `client/weaponicon-gallery.html` 與 `src/dev/weaponIconGallery.ts` 為 3T-4b 的開發頁，本次未動、未進正式 build。
