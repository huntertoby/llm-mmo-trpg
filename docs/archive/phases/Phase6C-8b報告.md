# Phase 6C-8b 報告：6C-8 驗收收尾

實作者，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 1 節 6C-8b 列、`docs/archive/art/6C-8檢查.md` 第 2 節第 2、4 項、`docs/art/地圖標記.md` 第 1 節、`sample/mapMarks.js` 的 `objectHint`。只動 `client/`（另加本報告與 2 張截圖）。

## 1. 做了什麼

| 項目 | 檔案 | 內容 |
|---|---|---|
| 情境物件提示 | `render/mapMarks.ts`（`MapThing` 加 `object_hint`、`drawObjectHint`、`objectHintAlpha`、`OBJECT_HINT_MS`）；`world/fieldModel.ts`（`thingEntries`）；`render/BattleRenderer.ts`（`drawThings`、`tickBobs`、`breaths`） | 主角在 1 格內（`nearTarget`：站在上面或四方向相鄰，和按 E 同一個判定）時：物件底下一圈金色虛線橢圓（中心在格子 0.7 高處、19×8、虛線 [4, 3]），不透明度照樣張呼吸（0.45～0.85，週期 1.4 秒）；右上一個小手（深色圓底＋淡金手）。離開就不畫。淡色框和「◎」拿掉（`thingMarks`、`THING_COLOR` 一併刪掉，沒有別處在用）。說明卡、`hoverText` 不變 |
| 眼睛高度 | `render/unitSprite.ts`（新 `unitTopY`）；`render/mapMarks.ts`（`eyeOffset(T, unitTop)`、`EYE_GAP = 6`、`EYE_HALF_H = 5`）；`BattleRenderer.drawThings` | 眼睛下緣放在該敵群單位圖實際頂端再往上 6px。頂端：異形 ＝ 身體最高點（`bodyTop`）× 體型（含精英）× 戰場縮放（頭目 ×0.9），和 6A/5A-ART5 狀態列的算法相同；人形 ＝ 頭頂 `DOLL_HEAD_TOP` × 精英 × 外觀大小。找不到單位時退回 6C-8 的位置（格子上緣往上 18px） |
| 開發用畫面 | 新 `client/mapmarks-gallery.html`、`src/dev/mapMarksGallery.ts` | 用真正的 `BattleRenderer`＋`fieldDrawModel`＋`fieldHighlights` 擺兩個場景（不屬於正式 build），截圖用 |

## 2. 測試

- `render/mapMarks.test.ts` 加：眼睛下緣 ＝ 單位頂端 − 6px（人形、large 傀儡、huge 熊）；頂端隨實際高度（軟泥比人矮、large 比 medium 高、頭目比 large 高、遠高於人、精英人形比一般高；人形高度 ＝ `DOLL_HEAD_TOP`×縮放）；呼吸不透明度 0.45～0.85、週期 1.4 秒；虛線圈位置與虛線、小手在右上；兩個新畫法沒有 `fillText`、沒有格子框。
- `world/fieldThings.test.ts`：telegraph 裡不再有物件框／「◎」；靠近／離開（正下方、左邊、站上去有；斜角、遠處沒有；不能用與只能看的也有）；`fieldHighlights.things` 帶提示；說明卡照舊；不畫提示時仍佔住那格（營火不會畫到物件上）。
- 跑過：`vitest run src/world src/render/mapMarks.test.ts src/render/art5.test.ts src/render/unitSprite.test.ts src/render/BattleRenderer*.test.ts` 28 檔 354 項通過；`tsc --noEmit`、`pnpm build` 通過。
- 瀏覽器裡看過：虛線圈相隔 0.7 秒截兩次深淺不同（有在呼吸）。

## 3. 截圖（vite 5315、開發用畫面，800 寬）

- `docs/art/6c8b_object_hint.jpg`：主角站在木箱左邊，木箱底下金色虛線圈＋右上小手；右上另一個木箱離得遠，沒有提示。
- `docs/art/6c8b_creature_eye.jpg`：人形、large 傀儡、huge 熊（頭目）、軟泥四隊敵群，眼睛各自在頭頂上方；下方是虛線視野。

## 4. 待 PM 決定

1. **截圖不是實機**：伺服器目前不給實地敵群的外觀（`FieldEnemyView` 沒有 `doll_look`，前端一律畫人形），所以實際遊戲裡眼睛都在人形高度；大型異形與頭目是在開發用畫面裡把外觀補上驗證的。要實機出現需伺服器給外觀（不在本段範圍）。情境物件的截圖也在開發用畫面裡擺（省去建暫存存檔）。
2. **人形頂端用頭頂 `DOLL_HEAD_TOP`（不含角、帽）**：戴高帽或有角的人形，眼睛可能離帽頂不到 6px；形態、非人形召喚物沒有另算（實地敵群不會是這兩種），照人形算。
3. **提示畫在標記層**（和其他標記一樣在單位與物件之上），虛線圈只有描線，會疊在物件底部一點點；要真正畫在物件「底下」需拆一層地面標記。
4. **所有情境物件都提示**（含不能用、只能看的），因為按 E 都會開說明卡；若只要能用的才提示，改 `thingEntries` 一行。
5. 走路動畫途中提示照伺服器回來的位置更新（跟其他標記一樣，不逐幀判定）。

## 5. Commit

- `a076eb02` feat(client): situation object hint ring and hand within 1 tile, watch eye above drawn unit top (6C-8b)
- `d294bcb5` feat(client): map marks dev gallery for object hint and watch eye (6C-8b)
- 本報告與截圖一個 docs commit。
