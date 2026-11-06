# Phase 6C-8 報告：地圖標記換新畫法＋兩項順手修改

實作者，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 1 節 6C-8 列、`docs/art/地圖標記.md`（代決 #58）、`map-marks.png`、`sample/mapMarks.js`、`docs/art/6A-4g與6C-5與6M-4與6C-7檢查.md` 第 1、3、5 節。只動 `client/`（另加本報告與 3 張截圖）。

## 1. 做了什麼

| 項目 | 檔案 | 內容 |
|---|---|---|
| 地圖標記 | 新 `render/mapMarks.ts`；`world/fieldModel.ts`（`mapThings`、`watchEyes`、`thingMarks` 只剩物件）；`render/BattleRenderer.ts`（`Highlights.things／eyes`、`drawThings`、`tickBobs`） | 照 `mapMarks.js` 移植：事件「！」（金泡泡＋地上淡金光，泡泡上下浮 3px、週期 1.6 秒）、營火（石圈＋交叉柴＋火苗＋暖光；熄火版也有畫法）、留言石碑（石板＋刻線＋釘紙；未讀紅點版也有畫法）、朋友腳印（每格兩步、左右腳交替、越舊越淡，Pixi Graphics 直接畫）。貼圖程式繪製、全場共用快取，沒有亂數。不畫格子框、不寫字 |
| 敵人視野 | `render/regionBlobs.ts`（`dash`、`edgeColor`、`dashRun`）；`mapMarks.sightStyle` | 沿用 6A-4g 併塊：淡紅 0.20、外緣紅色虛線 [7, 4]；潛行時 0.10、虛線 [3, 5] 更淡。格角黑點沒有了 |
| 誰在看 | `mapMarks.drawWatchEye`、`eyeTexture`；`fieldModel.watchEyes` | 有視野的敵群頭上一個眼睛（白底紅瞳，格子上緣再往上 18px）；潛行時上眼皮蓋下（半閉） |
| 說明卡 | 不動 | `hoverText` 照舊（「！」、營火、石碑、腳印的滑過說明都沒變，有測試） |
| 戰鬥上方鋪滿 | `styles/battle-hud.css` | `.board-scroll` 上緣從 `--hud-top` 改成 0，地圖鋪到最上面，行動順序列疊在地圖上；它本來就在 `FADE_BLOCKS`（`order`），照 0.38 規則變淡。底部列照舊扣掉高度、不在變淡的塊裡 |
| 剪影白閃 | 新 `render/silhouetteFlash.ts`；`artTextures.ts`（`formFlash`、`summonFlash`、`figureFlash`）；`unitSprite.ts`（`overlayFlashKind`、`flashTexture`）；`inkForm.ts`、`summonArt.ts`（`ground` 參數）；`BattleRenderer.overlayHit` | 形態、有外觀的召喚物、倒下或倒地狀態的人受擊：同一張圖不含地上影子（影子、水窪、光環都不畫）再畫一次、轉成白色剪影（像素運算，等同 `brightness(0) invert(1)`），疊在小人正後面、同錨點縮放位置旋轉，不透明度照人形受擊片段（開頭 0.85、1/4 時消失），結束拿掉。不畫白圓、不整格變白、不需要骨架 |

## 2. 測試

- 新 `render/mapMarks.test.ts`（17 項）：標記清單與優先序、腳印越舊越淡、腳印幾何（每格兩步四個橢圓在格內、沿方向、左右交替、鞋尖朝前）、視野樣式（平常／潛行）、telegraph 裡不再有「！」等與視野、`dashRun` 切虛線（跨轉角接著量）、眼睛只給有視野的敵群與潛行半閉、各畫法沒有 `fillText`／格子大小的 `rect`、狀態不同畫法不同、浮動週期。
- 新 `render/silhouetteFlash.test.ts`（7 項）：**像素測試**——`whiteCanvas` 身體變白、不透明度不變、透明處維持透明；疊回含影子的原圖後只有剪影 64 像素變白，影子與剪影外逐像素不變。畫法測試——形態與非人形召喚物 `ground = false` 時不畫影子；哪些單位疊剪影（形態、召喚物、倒下、倒地狀態；站著的紙娃娃與異形不疊）；`flashTexture` 要對的貼圖；`overlayFlash` 節點位置、不透明度、清除。
- `battle/hudFade.test.ts` 加 3 項：CSS 地圖上緣 0、底部照舊扣底部列；行動順序列底下有單位時變淡、CSS 0.38；底部列不在變淡的塊裡。
- `world/fieldThings.test.ts` 改成新行為（物件照舊是框；其他四種改 `mapThings`、說明卡不變）。
- 跑過：`vitest run src/world src/render src/battle/hudFade.test.ts src/battle/vfx*.test.ts` 76 檔 917 項通過（`inkCreature`、`inkRace` 兩個全組合自測在平行時逾時 5 秒，單獨重跑 33 項通過）；`tsc --noEmit`、`pnpm build` 通過。

## 3. 截圖（自己開的伺服器，埠 8311、暫存存檔、直接掛 `client/dist`，1040×720 縮到 800）

- `docs/art/6c8_winter_lake_marks.jpg`：冬湖——左邊營火與上方「！」、主角北邊的留言石碑、沿 x＝11 往北的朋友腳印、虛線併塊的視野、兩隊敵群頭上的眼睛。
- `docs/art/6c8_patrol_sight_eye.jpg`：同一處按 R 潛行——視野縮半、更淡、虛線更短，敵群的眼睛半閉、四周暗角。
- `docs/art/6c8_battle_top_fill.jpg`：冬湖就地開打——地圖從畫面最上面開始（畫布 top 8px），行動順序列疊在地圖上；底部列照舊。
- 暫存存檔用腳本建（`alice` 站冬湖、手動放一個「！」在帳篷事件點、`frank` 去過冬湖產生腳印、一則留言），沒碰 `saves/`。

## 4. 待 PM 決定

1. **營火熄火版沒接**：伺服器的 `campfires` 沒有「今天紮過營」欄位，前端一律畫點著的（熄火畫法已做好，`MapThing.lit`）。要接需在 `FieldSpotView` 加欄位（不在本段範圍）。
2. **石碑紅點沒接**：伺服器只給留言數、沒有「未讀」，保守不畫紅點（畫法已做好，`unread`）。
3. **情境物件照舊是淡色框＋「◎」**：本段任務只列四種標記；物件沒有自己的美術，`objectHint`（1 格內金色虛線圈＋小手）沒做，物件提示照 6C-5。
4. **火苗沒有晃動**：只做了「！」的浮動；火苗是靜態貼圖（晃動要每幀換貼圖或拆圖層，先不做）。
5. **腳印的「越舊越淡」**用伺服器給的順序（同一位朋友第一個最淡）；伺服器沒有時間資料。和門同一格被略過的腳印仍算在總數裡（差一點點透明度）。
6. **眼睛高度**固定在格子上緣往上 18px；大型異形頭比較高時會蓋在身上。
7. **剪影白閃沒有實機截圖**：靠像素與節點測試；冬湖戰鬥沒有形態／召喚物被打的場面。沒有骨架的單位不往後彈（只閃）。
8. 戰鬥上方鋪滿後，`--hud-top` 只剩提示浮層（`board-toasts`）在用。

## 5. Commit

- `3d95bb9b` feat(client): battle map extends under the turn order bar (6C-8)
- `59f89f8f` feat(client): forms, summons and downed units flash white silhouette on hit (6C-8)
- `0177af95` feat(client): field map marks drawn as shapes, dashed sight blob, watch eye (6C-8)
- 本報告與截圖一個 docs commit。
