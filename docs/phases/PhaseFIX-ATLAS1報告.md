# FIX-ATLAS1 報告：大世界圖滑過鎖住浮島出現空的深色框

使用者回報（原話）：「荒原 怎麼有個圖跑不出來」。大世界圖滑過灰燼荒原（鎖住，世界事件：霧潮入侵），說明卡下面多一塊約 450×250 的深色圓角矩形。

## 1. 重現

- 自己的 `uv run trpg serve --port 8765`（存檔在本 worktree 的 `saves/`），`?mute=1`，新角色 → 靶場選路出發 → 主城按 M 開大世界圖。新角色的灰燼荒原預設就是鎖住，不必佈置。
- 滑過灰燼荒原：說明卡只有一張（`body` 底下只有一個 `float-card … hint-tip-box`），空框不是第二張卡也不是圖。
- 空框就是浮島的透明點擊區 `button.atlas-island.map-hit.locked[data-testid=atlas-ashen_waste]` 本身：滑過時 `getComputedStyle().backgroundColor` = `rgb(54, 54, 74)`（`#36364a`），大小、位置與空框一致（1600×900 時是 322×182 CSS px；hit box 隨地圖大小縮放，使用者截圖的 450×250 是較大視窗下的同一個框）。

## 2. 根因

浮島、傳送鈕、區域圖的地點／任務／傳送石都是 `<button class="… map-hit">`，外觀全畫在畫布上，`.map-hit { background: transparent }`（特異度 0,1,0）。
`styles/base.css` 的共用 `button:hover:not(:disabled) { background: #36364a }`（0,2,1）特異度較高，滑過時蓋掉透明底。可開的浮島（`.atlas-island.openable:hover`，0,3,0）、傳送鈕（`.atlas-town.go:hover`）、可傳送的傳送石（`.region-stone.go:hover`）有自己更高的規則所以看不出來；**沒有自己滑過樣式的點擊區**——鎖住／之後的賽季的浮島、你所在的主城、區域圖的地點、任務、`here`／`view`／`locked` 傳送石——滑過都會整塊塗成深灰。不是缺圖。

## 3. 修法

`client/src/styles/base.css`：共用規則改成 `button:hover:not(:disabled, .map-hit)`（特異度不變，其他按鈕行為不變），透明點擊區不再吃共用底色；要滑過效果的點擊區照舊自己寫。沒有加 `display:none`、沒動說明卡的文字與版面。

## 4. 測試

新增 `client/src/world/mapHitHover.test.ts`（5 項）：掃 `client/src` 全部 CSS 會塗底色的 `:hover` 規則，用簡化的選擇器比對（類型、class、`:hover`、`:disabled`、`:not(…)`，祖先段只認地圖外框的 class）對：
- 大世界圖實際 render 出來的所有點擊區（含 busy 時 disabled 的傳送鈕）：不吃沒指名 class 的共用滑過底色；
- 不能點的點擊區（鎖住／之後的賽季浮島、主城、區域圖地點三種霧、城鎮、任務、三種非 go 傳送石）：滑過時沒有任何規則塗底色；
- 可開浮島、傳送鈕仍有自己的滑過底色；並檢查掃描真的抓得到這三條規則。

已確認把 `base.css` 改回原樣時 3 項失敗（列出 `atlas-ashen_waste ← styles/base.css: button:hover:not(:disabled)` 等），改回修法後全過。

實機（修後，1024×768 內建瀏覽器）逐一滑過量 `backgroundColor`：晶冠城邦、魔導樞市、灰燼荒原、霜潮海境、主城 = `rgba(0,0,0,0)`；雲嶺（可開）= `rgba(255,240,200,0.12)`、傳送到霧渡鎮 = `rgba(255,255,255,0.22)`（原本的滑過效果保留）。滑過灰燼荒原時說明卡只有一張。區域圖（非主城區）實機沒走到，只由上面的 CSS 掃描測試涵蓋（同一條規則）。

6.5.1 的「滑進卡片 → 捲到底 → 釘住 → 關閉」：本段沒改浮動卡元件與說明卡，未重跑（只確認滑過只出一張卡）。

## 5. 截圖（1600×900，無頭 Chrome `--mute-audio`、CDP，jpg 80）

- 修前：`docs/art/shots/fix-atlas1/before-ashen-hover-1600.jpg`（說明卡下的 `#36364a` 實心框）
- 修後：`docs/art/shots/fix-atlas1/after-ashen-hover-1600.jpg`（框消失，鎖住的荒原插畫照常可見）

## 6. 結束碼

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test`（310 檔、3997 項） | 0 |
| `corepack pnpm -C client build` | 0 |
| `vitest run src/world/mapHitHover.test.ts src/world/atlas.test.ts` | 0（17 項） |

未跑 `scripts/check.py`、模擬；未 push。自己開的伺服器（8765）與無頭 Chrome（CDP 9347）已用自己的 PID 關掉，兩埠已不在聽。

## 7. 待 PM 決定

1. 鎖住／之後的賽季浮島現在滑過完全沒有視覺回饋（只有說明卡）。是否要給不能點的浮島一個淡的滑過效果（例如比可開的更淡的光暈），交美術 PM 決定；本段照「最保守＝不加新樣式」處理。
