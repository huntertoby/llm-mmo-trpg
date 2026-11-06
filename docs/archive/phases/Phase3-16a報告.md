# Phase 3-16a 報告｜地形、表面、物件改用程式繪製，移除 Kenney 素材

分支：`worktree-agent-a5c6537817af7ed2f`（從 main 的 `5aa897c` 開出，未 push）。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `a272d64` feat(client): procedural terrain, surface and object art; remove Kenney sprites | 新增 `render/artPalette.ts`、`artRandom.ts`、`artDraw.ts`、`terrainArt.ts`、`objectArt.ts`、`artSpecs.ts`、`artTextures.ts` 與 `art.test.ts`；`BattleRenderer.ts` 改用程式貼圖；刪除 `client/public/assets/kenney/`、`render/sprites.ts`、`sprites.test.ts`、3-14 的 `proceduralTerrain.ts` 與其測試 |
| docs: add Phase 3-16a report and screenshots | 本報告與截圖 |

做法：每個格子、每個物件依「規格」（地形、座標、高度、表面、四鄰遮罩、崖面高度、陰影…）畫成一張 2 倍解析度的離屏 canvas，再 `Texture.from(canvas)`；規格鍵相同就共用貼圖，每次重畫場景後銷毀本輪沒用到的貼圖（不洩漏）。色票全在 `artPalette.ts`（依 `docs/art/移植需求.md` 第 1 節），紋理變化用「格子座標 → 雜湊種子」，沒有 `Math.random`（測試有檢查）。

圖層順序（需求第 2 節）：地形 → 高度明暗 → 表面（四鄰連成一片）→ 北／西較高鄰格的陰影 → 南側崖面 → 極淡格線（以上都在地形貼圖內）→ 光環／持續區域／源泉 → 物件（含影子、可燃小火苗）→ 高度徽章「▲N」（只在高度 > 0）→ 高亮、預覽 → 陷阱 → 單位 → 特效。

**單位**：3-16b 才做紙娃娃，所以 Kenney 移除後單位退回 3-13 之前的色塊圓形（召喚物菱形）加代號、朝向箭頭、HP 條與既有徽章，行為與 3-13 之前相同。

## 2. 驗收條件逐條

| # | 條件 | 結果 |
|---|---|---|
| 1 | 1600×900 截圖，至少三張地圖（懸崖前哨高台、岩漿渡橋、油庫） | 達成：`img/3-16a-cliff-outpost.png`、`3-16a-lava-crossing-vfx.png`、`3-16a-oil-depot.png`，另有 `3-16a-skill-preview-hover.png`（技能預覽＋滑過資訊卡）。內建瀏覽器截圖是縮小成 800×450 的圖，細節請試玩時直接看 |
| 2 | 繪圖對照 vitest（含未知種類預設） | 達成：`render/art.test.ts`（每種地形 × 每種表面含未知、每種物件含未知／可燃／相連／直向都畫得出來；未知地形走石地畫法＋glossary 色調；未知物件退回灰色六角形；規格推導；確定性；快取鍵） |
| 3 | `client/public/assets/kenney/` 移除、沒有殘留引用 | 達成：整個 `client/public/` 已空而消失；`grep -i kenney`（程式與設定，不含 docs）無結果 |
| 4 | 與 3-14 高度表現整合 | 達成：崖面畫在高格自己的底部（高度差 × 5 px，上限 15），不再蓋住較低格頂部；深淵／岩漿／冰窟旁的高台也有崖面；北、西側較高鄰格投影；高度差 ≥ 2 的懸崖線沿用 `heightModel.heightDecor`；單位底座陰影保留。`clientToTile` 不變（`heightModel.test.ts`、`stageLayout` 測試全過） |
| 5 | 點格子、技能預覽、特效位置正確 | 達成（瀏覽器實測）：點格子移動單位、技能預覽範圍（紅／橘框）、滑過資訊卡位置正確；岩漿渡橋的弓箭投射物沿正確的行列飛行；主控台無錯誤 |
| 6 | `check.py` 全過、`pnpm build` 成功 | 達成：`uv run python scripts/check.py` 全部通過（含 client typecheck、vitest）；`corepack pnpm -C client build` 成功 |

## 3. noqa 與複雜度

本段只動前端，沒有新增或移除 Python `noqa`；noqa 總數不變。

## 4. 修改既有測試

- 刪除 `render/sprites.test.ts`（Kenney 對照表測試）與 `render/proceduralTerrain.test.ts`（3-14 的程式紋理，改由 `terrainArt.ts` 的樣張畫法取代）。沒有修改其他既有測試的期望值。

## 5. 地形／表面／物件 → 畫法 對照表

地形（`terrainArt.ts`）：

| 種類 | 畫法 | 鄰格相依 |
|---|---|---|
| `stone` | 2–4 塊石板、偶有裂紋 | — |
| `grass` | 深淺斑塊、6–9 叢草、偶有小花 | — |
| `dirt` | 卵石點＋淺溝 | — |
| `wall` | 交錯磚紋 | 南鄰不是牆 → 立面 |
| `chasm` | 深色漸層＋微光點 | 四鄰非深淵 → 鋸齒崖緣；北緣縱深漸層 |
| `lava` | 底色＋中心亮光＋岩殼 | — |
| `ice_hole` | 深水＋水紋 | 四鄰非冰窟 → 冰緣 |
| **未知地形（預設）** | 石地畫法＋glossary 地形色調（alpha 0.3） | — |

表面（連成一片：依四鄰遮罩決定內縮與圓角）：`water`、`ice`、`oil`、`fire`、`poison` 照樣張；**補畫**：`smoke`（灰色底＋白／灰雲團）、`holy`（淡金底＋十字星芒）、`darkness`（暗紫底＋漩渦弧線）；**未知表面**：灰色連成一片的底色。

物件（`objectArt.ts`）：`crate`、`oil_barrel`、`stone_pillar`、`low_wall`（左右相連）、`wooden_bridge`（依鄰橋決定橫／直）、`fallen_log`、`earth_wall`、`dead_tree` 照樣張；**補畫**：`ice_wall`（半透明冰塊＋高光）、`thorn_wall`（深綠底＋藤蔓＋尖刺）、`rubble`（散落碎石）、`thin_ice`（半透明薄冰＋裂紋，地板型）、`grass`（物件，半透明草叢，地板型）；**未知物件**：灰色六角形＋原本的字（glyph）。可燃物右上角小火苗（橋除外）；著火、剩餘回合徽章、耐久條沿用原有疊圖。

樣張沒涵蓋、本段**沒有另畫**的：陷阱、持續區域、圖騰、倒地、狀態圖示——陷阱與持續區域仍是原本的圖示與半透明色塊（需求文件把它們列為照舊）；圖騰與倒地屬單位，歸 3-16b。

## 6. 與 `docs/art/移植需求.md` 的差異

1. 需求第 2 節第 5 點「崖面畫在本格底部」：照做，所以 3-14 的獨立側面（`heightDecor.sides`、`shadows`）不再繪製；函式與其測試保留（未刪），但 `BattleRenderer` 只用其中的懸崖線。
2. 貼圖以 2 倍解析度、線性縮放（3-14 的最近鄰縮放不再適用，因為不是像素圖）。
3. 樣張格子是 52 px，正式格子 48 px：繪圖座標維持樣張的 52 單位，貼圖產生時整體縮放，畫法逐字對應。
4. 地圖邊緣外視為「同種」（不畫崖緣／冰緣），樣張在邊緣會畫。
5. 單位行為見第 1 節（退回色塊圓形）。

## 7. 待 PM 決定（最多 10 點）

1. **整片高台每格都標 ▲1**（岩漿渡橋整張都是高度 1）：照需求「高度 > 0 才標」，畫面有點滿；要不要改成「只標與鄰格不同高度」或把徽章再縮小／淡化。
2. 崖面畫在高格內，高格頂面可用面積少了 5–15 px（高度差大時明顯）；可改成畫到低格上方（舊做法，但會蓋住低格）。
3. 懸崖線（高度差 ≥ 2 的深色邊）與崖面並存，高處邊緣略重；要不要拿掉懸崖線。
4. 岩漿、深淵格仍疊「致命 ×」框（既有行為），與新紋理相疊略吵；要不要改成淡化。
5. 煙霧、聖光、黑暗表面與冰牆、荊棘牆、碎石、薄冰、草叢是依同一套規則補畫的，色彩與樣式請 PM／美術 PM 過目。
6. 內建瀏覽器截圖偏小（800×450），細節未能在圖上展示；請試玩時直接檢視。
7. 單位在 3-16b 之前是色塊圓形；若希望過渡期有更好看的單位，可提早做 3-16b 的簡化版。
8. 貼圖快取鍵含座標，因此每格一張貼圖（10×10 地圖約 100 張 96×96）；若之後地圖變很大再考慮改成「變體池」。
9. `heightModel.ts` 中不再被繪圖使用的 `sides`、`shadows`、`sideThickness` 等是否刪除（目前留著，測試仍在）。
10. 預設的未知地形色調使用 glossary 的洋紅偏色（`0xff00ff`，alpha 0.3），本意是讓新地形一眼可見；可改成中性灰。

## 8. 代表性輸出

- vitest：`src/render/art.test.ts` 全過；完整 `scripts/check.py` 全部通過。
- 截圖：`docs/phases/img/3-16a-cliff-outpost.png`、`3-16a-skill-preview-hover.png`、`3-16a-lava-crossing-vfx.png`、`3-16a-oil-depot.png`。
- 測試伺服器 8774 已關閉，瀏覽器視窗已重設為 desktop，只使用既有的 `seed` 分頁；沒有在主資料夾留下 log 檔。
