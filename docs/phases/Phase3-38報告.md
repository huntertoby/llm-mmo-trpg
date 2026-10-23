# Phase 3-38 完成報告｜可燃標記平時淡化

## 做了什麼

- 可燃小火苗從物件貼圖拆成獨立一層：`objectArt.ts` 匯出 `drawFlammableMark`（畫法不變）與 `hasFlammableMark`（可燃且不是橋）；`drawObject` 不再畫火苗。
- `BattleRenderer` 在每個可燃物件上疊一個火苗節點（有貼圖的用全場共用的火苗貼圖；沒貼圖的退回原本的小圓點），平時透明度 `FLAME_DIM = 0.4`，明顯時 1。新增 `setFlameEmphasis(on)`：只改既有節點的透明度，不重畫。`draw()` 重建節點後由 `BattleCanvas` 立刻套回目前狀態。
- 判斷寫成純函式 `client/src/battle/flameMarks.ts`：`skillIgnites`、`fireOnField`、`flameEmphasis`。`BattleScreen` 用目前選取（瞄準中）模式的技能卡與 `DrawModel` 算出 `flameOn`，經 `BattleCanvas` 傳給繪製器。

## 判斷規則（明顯條件，任一成立）

1. 選取中的技能卡 `keywords.makes` 含 `ignite`，或 `icon.elements` 含 `fire`（不寫死技能 ID；技能卡尚未載入視為不點火）。
2. 場上有火：任何格子 `surface === "fire"`、任何物件 `burning`、任何單位狀態含 `burning`。

不需改 API：`SkillCard` 已有 `keywords.makes` 與 `icon.elements`，沒有重產 OpenAPI／快照。

## 快取做法

- 物件貼圖鍵 `objectArtKey` 移除 `flammable`，可燃與否不再讓物件貼圖多一份。
- 火苗貼圖全場只有一張（鍵 `m|flammable`），淡化／明顯靠節點透明度切換，不產生第二份貼圖。
- `ObjectArtSpec.flammable` 欄位保留（`artSpecs.ts` 仍填入），只是不影響貼圖。

## 檢查結果

- typecheck 通過；vitest 78 檔 827 測試通過（新增 `flameMarks.test.ts` 表格測試 10 列＋單項；`regionArt.test.ts` 改為驗證可燃不影響物件貼圖與鍵、火苗貼圖獨立可畫）；`pnpm build` 通過。
- 實機（內建瀏覽器，8011 埠，1600×900，竹林 `dark_forest`，火焰法杖＋點燃／倒地）：
  - 平時（沒選技能、場上沒火）：小火苗淡化，仍隱約可見。
  - 選取點火技能（引火重擊、火痕、火焰箭皆測過）：全場小火苗立即變明顯；取消選取後恢復淡化。
  - 場上有火（火焰箭點燃枯樹、格子出現火表面，取消選取後）：全場小火苗維持明顯。
- 已還原視窗（desktop）並關閉 8011 伺服器。

## noqa

無。

## 待 PM 決定

- 淡化透明度 `FLAME_DIM` 先 0.28 實機覺得幾乎看不見，改為 0.4；是否再調由美術 PM 驗收時決定（單一常數，在 `BattleRenderer.ts`）。
- 「場上有火」目前包含任何燃燒中的單位（含敵我）；若只想看地形／物件上的火，可拿掉單位那一項。
- 淡化／明顯目前是瞬間切換，沒有淡入淡出動畫；需要的話可後續加。
