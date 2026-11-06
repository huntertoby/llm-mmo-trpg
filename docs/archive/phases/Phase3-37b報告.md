# Phase 3-37b 報告｜雲嶺換皮（含 3-36b 小修、3-37a 待決 #1）

規格：`docs/phases/Phase3計畫.md` 41 共同規則、41.1.1 決定 #1、41.2（含玩法 PM 決定）、40.2.1；需求 `docs/art/雲嶺移植需求.md` 第 2～4、6 節。

## 做了什麼

| 項目 | 內容 |
|---|---|
| 雲嶺地形 7 種 | `render/cloudRidgeTerrain.ts`：青石板（帶苔）、偏青草地、黃土小徑、白牆黛瓦（瓦頂＋白立面）、雲海山谷（白霧＋青石崖線）、地熱泉（橘紅＋白煙）、寒潭（深青黑水＋霜邊）。`CLOUD` 色票照需求第 2 節。 |
| 雲嶺物件 9 種 | `render/cloudRidgeObjects.ts`：竹籠貨箱、白牆矮垣（共用矮牆外框規則，抽出 `lowWallArt.ts` 改傳色盤）、朱紅樑柱、酒罈（紅布封口＋危險記號）、倒竹、矮竹叢、竹木吊橋（繩索）、老松、寒潭薄冰（裂痕分 3 級）。可燃小火苗、受損裂痕仍由 `drawObject` 統一疊上。 |
| 表組裝 | `REGION_TERRAIN_DRAW.cloud_ridge`、`REGION_OBJECT_DRAW.cloud_ridge`、`LOOK_TERRAIN_DRAW`（`floor=plank_walk`／`floor=paddy` 對石、草、土；`wall=canyon_rock` 對牆）。 |
| `water_tint` | `regionArt.ts` 的 `lookValue`、`WATER_TINT`、`waterTintOf`；`terrainArt` 的水面表面讀它換底色，反光線不變；不認得的值＝預設水色。 |
| 薄霧 | `REGION_MIST`／`mistLevel`（資料表，目前只有 cloud_ridge：平常 0.2、霧天 0.4）；`DrawModel.weather`（選填，來自 `weather_id`）；`BattleRenderer.drawMist` 在各排 `veil` 層每格畫一團（衰減到格緣為 0，相鄰格接得起來）。純裝飾，不碰視線規則。 |
| 正式地圖 | `bridge_chasm`、`dark_forest` 加 `region: cloud_ridge`，`name_zh` 改「雲海吊橋」「竹林」；id、機制、其他地圖不動。更新 `objective.test.ts` 的舊名與 `test_regions.py`。 |
| 區域第三種樣式 | `zones.ts` 新增 `zoneEffectOn`（harm／help／none）、`ZoneDraw.effect`；`drawZoneCell` 加 `neutral`（虛線、淡底色 0.1、不畫紋理）；快取鍵用 effect；圖例加「不影響我方的持續區域」（`HIGHLIGHT.zone_neutral`）；`fx-gallery` 加我方火牆。判斷：影響敵人且施放者是我方、影響友方且施放者是敵方 → none；影響友方且我方施放 → 看 `harmful`（通常有益）。 |
| `trpg content check` | 印出 `map_warnings`（「地圖外觀警告（N 項，不影響通過）」），不算失敗；加測試。 |
| 開發樣張頁 | `client/region-gallery.html`＋`src/dev/regionGallery.ts`：雲嶺 7 種地圖類型、霧天對無天氣、預設對照、兩種覆寫、水底色對照、致命地形與技能物件。 |

## 檢查清單（需求第 6 節）

- 雲嶺地板、牆、致命地形、9 種物件換皮，功能特徵可辨（牆有瓦頂、柱與老松高、竹籠與矮垣矮、可燃火苗、酒罈危險記號、崖線／紅色／深色水）：樣張頁與實機（雲海吊橋）確認。
- 不寫／寫錯 `region`、寫錯 `look`：單元測試（呼叫序列與預設完全相同）；樣張頁「沒標區域」對照畫預設。
- 表面、技能物件（冰牆、荊棘、土牆、倒塌物）、圖示與預設一樣：測試驗證（表面尾段呼叫序列相同、技能物件序列相同）；樣張頁最後一張目視。
- 峽谷棧道、雨中梯田覆寫生效：樣張頁目視＋測試；水底色綠對藍對照。
- 截圖：`docs/art/3-37b-*.jpg`（棧道、梯田、冰湖＋致命地形、山寺＋吊橋、實機雲海吊橋）；縮放較小（瀏覽器截圖 800 寬）。與 `realms.png` 色調一致（青石墨灰＋朱紅點綴）。
- 實機 1600×900：內建瀏覽器開正式 app（8011，自己的 worktree 啟動），地圖下拉顯示「雲海吊橋」「竹林」，開戰雲海吊橋畫面正常、無主控台錯誤；已還原視窗、關閉分頁與伺服器。竹林正式地圖用樣張頁同款外觀確認（未另開戰）。

## 檢查結果

ruff、format、mypy（相關檔）通過；pytest `tests/content`＋`cli`＋`api` 1297 全過；vitest 816、typecheck、`pnpm build` 過；`trpg battle --map bridge_chasm／dark_forest --seed 1` 重播一致（76／79 動作）。`LOG_FORMAT` 不變，OpenAPI／schema 沒動（fixtures 重產無差異）。

## `# noqa`

無新增。

## 待 PM 決定

1. 預設瀏覽器工具的 `launch.json` 在主 checkout，實作者的 worktree 版本不會被 `preview_start name` 讀到；本段改以背景指令啟動伺服器再開網址，已全數關閉。
2. 區域第三種樣式的「影響友方且施放者是我方，但 `harmful` 為真」判為有害（罕見）；是否要另處理待定。
3. 薄霧濃度（0.2／0.4）與雲海山谷深度是目測值，美術 PM 驗收時可直接改 `REGION_MIST` 或 `cloudChasm` 的漸層色。
4. 雲嶺色票中的燈火暖黃只用在 `CLOUD.lamp`（尚未使用，石燈籠不做）。
5. 截圖為縮小版；需要原尺寸可在 `region-gallery.html` 以 1600×900 重拍。
