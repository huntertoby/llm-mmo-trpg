# Phase C｜紙娃娃 C 手繪墨線繪本（美術；使用者：「C畫風擴畫參考」「好就這樣」）

> 需求與檢查清單：`docs/art/C畫風移植需求.md`（**以它為準**）；樣張 `docs/art/story.png`，畫法以 `docs/art/sample/storyDoll.js` 為準。比較與評估 `docs/art/紙娃娃畫風大改.md`。
> 排程（2026-10-29，使用者「外觀先等」）：C-1、C-2 排在 3J-5（形態外觀）與 3R-3a／b（種族外觀）之前；3J、3R 的規則與流程照常先做。C-3 召喚物 2026-10-29 使用者決定一起換（「摔落A 換」），排在 C-2 之後。
> 開發 PM 把美術 PM 估的 C-1（約 1.5 段）拆成 C-1a、C-1b。

## 受影響的既有功能（流程改善 A）

`client/src/render/paperdoll.ts`、`paperdollGear.ts`、`paperdollSide*.ts`、`dollGear.ts`、`unitSprite.ts`（剪影外框、影子、快取、畫布高度）、`summonArt.ts`（只受 `DOLL_H` 影響時跟著改，非人形召喚物畫法不動）、`dev/dollGallery.ts`、`gearGallery.ts`（檢查頁）、比對像素或顏色的 vitest（照新畫法更新）、頭頂狀態列位置（畫布高度變了要確認）。**不動**：`look` 與裝備資料、API、引擎、技能圖示、裝備圖示、狀態圖示、戰場效果、地形、物件。

## C-1a｜畫法層＋四方向骨架（sonnet；約 0.7 段）

1. 新檔 `client/src/render/inkStyle.ts`：`ink()`、`stroke()`、`ellPts`、`wobble`、`smooth`、`seedOf`（FNV-1a）＋LCG，照需求第 1 節與 `storyDoll.js`；**不准 `Math.random()`**；墨色 `#2b1e16`；vitest：同 key 兩次取點完全相同、不同 key 不同。
2. 骨架與四方向（需求第 2 節）：座標、圖層順序、背面左右對調、`stout`／`tall` 四方向、倒地照舊；畫布高度留到約 −70（`DOLL_H` 調整，頭頂狀態列跟著確認）；52px 格約 0.74 倍。身體部件先用基本衣著（無裝備時的樣子），頭、臉、頭髮、手、腿、身體都換成 `ink()`。
3. 拿掉 8 方向黑色剪影外框；頭目外光保留；地面影子改成短斜線。
4. 快取成貼圖（沿用 `renderFigureCanvas` 的快取鍵）；`gear-all`／`doll-gallery` 自測不報錯。
5. 本段還沒換畫法的裝備與武器維持現行畫法也可以（C-1b、C-2 換），但不能空白或報錯。
6. 驗收：vitest、build、tsc、ruff（若動到 Python）、排版煙霧檢查；內建瀏覽器截 `doll-gallery` 四方向與實戰各一張（`docs/phases/img/C-1a-*.png`），對照 `docs/art/story.png`；效能：滿場 20 隻小人移動不掉幀（寫量測方式與結果）。報告 `PhaseC-1a報告.md`。

## C-1b｜樣張畫過的裝備與武器（sonnet；約 0.7 段；C-1a 後）

需求第 3、4 節中樣張畫過的：身體 `shirt`／`leather`／`plate`／`robe`、頭 `helmet`／`hood`／`wizard_hat`、腳 `boots`／`greaves`、披風、圓盾；武器 `sword`、`dagger`、`axe`、`staff`（杖頭光暈元素色）、`bow`；握點照第 4 節。驗收同 C-1a，截圖 `C-1b-*.png`。

## C-2｜其餘裝備 kind 與武器（sonnet；約 1～1.5 段，再拆；C-1b 後）

需求第 3、4 節其餘 kind 與武器（含 #34、魔導劍、成對武器正面／側面遠側往前上錯開約 3px／背面），檢查清單「裝備與武器」全部打勾。細節在 C-1b 驗收後寫。

## C-3｜召喚物 17 種（sonnet；約 1 段，可能再拆；C-2 後；使用者 2026-10-29：「摔落A 換」）

照需求第 6 節：17 種的規則照 `docs/art/召喚物外觀.md`（體型 × 元素 × 大小 × 特徵），輪廓沿用 `summonArt.ts`，改用 `ink()` 畫；拿掉黑色剪影外框；光環與影子同需求第 1、5 節；新 `trait` 不認得時退回預設。人形召喚物用紙娃娃，C-1、C-2 做完自動換。檢查清單「召喚物」全部打勾；截圖 `summon-gallery`。細節在 C-2 驗收後寫。
