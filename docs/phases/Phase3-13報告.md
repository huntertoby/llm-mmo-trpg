# Phase 3-13 報告｜原型美術

> 規格：`docs/phases/Phase3計畫.md` 15.3。只動前端繪圖與靜態素材；引擎、API、事件 schema、內容都沒改。
> 分支：`worktree-agent-a60d11ed1d2a3633c`（從 main `a40ef90` 開出）。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `65b3816` feat(client): add Kenney CC0 sprite assets and sprite mapping table | `client/public/assets/kenney/`（用到的圖與各包 `License.txt`）、`render/sprites.ts`（對照表）、`render/sprites.test.ts` |
| `f99c260` feat(client): render terrain, objects and units with sprites, fall back to color blocks | `BattleRenderer` 以圖繪製地形、物件、單位；`DrawModel` 加入 `surface`、`kind`、`template` 三個欄位供對照 |
| （本報告與截圖） | `docs/phases/Phase3-13報告.md`、`docs/phases/img/3-13-*.png` |

### 做法摘要

- **對照表（`render/sprites.ts`）**：`TERRAIN_SPRITES`（地形）、`OBJECT_SPRITES`（物件種類）、`UNIT_SPRITES`（單位範本 ID）三張表，值為 `{ pack, tile, tint? }`。`tint` 是乘上的顏色，用來把同一張圖變成冰牆、土牆、岩漿等變體。查詢函式 `terrainSprite`／`objectSprite` 找不到回傳 `null`；`unitSprite` 找不到時用陣營預設圖。
- **退回色塊**：`BattleRenderer` 啟動時預先載入所有圖（`Assets.load`，逐張 `try/catch`），載入失敗的圖不放進貼圖庫。繪圖時「沒有對照」或「圖沒載入」都走原本的色塊與文字圖示路徑，不會出錯。
- **地形**：圖塊乘上高度明暗（深淵類不乘，與原本一致）；表面（火、油、冰、煙霧……）仍以半透明色疊在圖塊上；致命地形的紅框叉叉、高度數字、格線都保留。
- **物件**：圖畫在地形之上；地板型（橋、薄冰、草叢）填滿整格；有圖時不再畫文字圖示（燃燒時仍標「火」並保留橘框）；可燃小點、耐久條、暫時障礙的剩餘回合徽章保留。
- **單位**：陣營色半透明圓底加外框（召喚物為菱形加青綠外框），圖放在上面；英雄外圈、行動中外圈、朝向箭頭、HP 條與護盾條、各種徽章、倒地叉叉都保留；代號字母縮小移到左上角並加深色外框。
- **新內容**：新地形／物件沒有對照時用原色塊；新單位範本沒有對照時用陣營預設圖（我方、敵方各一張）。
- 特效（3-12）、高亮、預覽、環境預告等圖層疊在最上面，沒有改動。

## 2. 驗收條件逐條

1. **1600×900 截圖，至少三張不同地圖** — ✅（見第 4 節；附註解析度限制）：`3-13-bandit-lair.png`（Boss 地圖）、`3-13-training-range.png`（靶場）、`3-13-dark-forest.png`（幽暗森林）。
2. **缺圖退回色塊的 vitest** — ✅ `render/sprites.test.ts`：沒有對照的地形／物件回傳 `null`；沒有對照的單位範本用陣營預設圖；貼圖庫查不到的圖與 `null` 參考回傳 `undefined`；用到的每一張圖與每個包的 `License.txt` 都存在於 `client/public`（用 Vite 的 `import.meta.glob`，不需 Node 型別）。
3. **陣營顏色、HP 條、狀態圖示保留、可讀性不變差** — ✅ 見截圖；單位仍有陣營色底圈、HP 條、代號。
4. **重拍技能特效** — ✅ `3-13-vfx-melee-slash.png`（靶場，隊友近戰揮砍加「背刺！」字樣，新美術之上）。附註：沒有再重拍火遠程等其他特效（解析度限制，見第 4 節）。
5. **`check.py` 全過、`pnpm build` 成功** — ✅（`check.py` 全部通過，vitest 387 項；`corepack pnpm -C client build` 成功）。
6. **字體** — 未更換（見「待 PM 決定」#1）。

## 3. 素材清單

兩個包都只從 Kenney 官方網站（kenney.nl）下載，授權 **Creative Commons Zero (CC0 1.0)**，使用者已同意（2026-10-22）。壓縮檔下載到專案外的暫存資料夾，只複製實際用到的 PNG 與原始 `License.txt`，沒有執行包內任何檔案。放在 `client/public/assets/kenney/<包名>/`。

| 包 | 網址 | 版本 | 授權 |
|---|---|---|---|
| Tiny Dungeon | https://kenney.nl/assets/tiny-dungeon | 1.0 | CC0 1.0（`tiny-dungeon/License.txt`） |
| Tiny Town | https://kenney.nl/assets/tiny-town | 1.1 | CC0 1.0（`tiny-town/License.txt`） |

用到的檔案（`tile_NNNN.png`，16×16；以 `render/sprites.ts` 為準）：

- **Tiny Dungeon**：`0018`（石柱）、`0042`（碎石）、`0057`（土牆，乘色）、`0058`（牆地形）、`0066`（戰意圖騰）、`0067`（冰牆，乘色）、`0077`（矮牆）、`0080`（木橋）、`0084`（法師）、`0085`（盜賊）、`0086`（我方預設）、`0087`（首領）、`0089`（木箱）、`0096`（戰士）、`0097`（盾衛）、`0098`（骷髏戰士）、`0099`（弓手）、`0100`（反擊者）、`0107`（元素之靈）、`0108`、`0110`（頭目）、`0111`（雷術士）、`0112`（盜賊弓手與隊友弓手）、`0120`、`0121`（敵方預設、殘影分身）、`0122`、`0123`、`0124`。
- **Tiny Town**：`0000`（草地）、`0003`（枯樹）、`0006`（草叢）、`0007`（荊棘）、`0025`（泥土）、`0095`（木樁靶）、`0106`（倒木）、`0109`（石地；也乘色當冰窟、深淵、岩漿、薄冰）、`0130`（油桶）。

對照概要：

| 類別 | 對照 |
|---|---|
| 地形 | stone、grass、dirt、wall 各一張；lava、chasm、ice_hole 用石地圖塊乘上橘／暗／藍色（素材包沒有對應圖） |
| 物件 | 13 種全有圖（橋、油桶、薄冰、石柱、草叢、箱、土牆、矮牆、倒木、枯樹、碎石、冰牆、荊棘） |
| 單位 | 22 個範本（英雄 4、盜賊系 5、標準敵人 5 階、隊友與反擊者 3、木樁、召喚物 4）；其餘用陣營預設圖 |

**字型**：沿用原本的系統字型（`system-ui`、微軟正黑體、蘋方），沒有新增字型檔，也沒有新的字型授權。

## 4. 瀏覽器實測與截圖

伺服器用 `uv run trpg serve --port 8771`（之後為了讓 Boss 地圖能從網頁列表選到，另開 8772，見 #6），內建瀏覽器視窗設為 1600×900。

- `3-13-bandit-lair.png`：盜賊巢穴（Boss 地圖）——岩漿、高低差、木箱、油桶、石柱、冰與水的表面、源泉格。
- `3-13-training-range.png`：靶場——牆、木樁靶、火焰、荊棘、水與冰表面、石柱、箱與油桶。
- `3-13-dark-forest.png`：幽暗森林——草地、荊棘、石柱、倒木，並抓到一個遠程飛行物。
- `3-13-vfx-melee-slash.png`：近戰揮砍特效與「背刺！」字樣（靶場）。
- **解析度附註**：內建瀏覽器截圖工具的輸出尺寸依面板大小為 715×402～800×450，不是 1600×900 的原始像素（頁面本身確實以 1600×900 版面排版）。截圖仍看得出圖塊與單位，但細節不如原尺寸。
- **Boss 地圖的取得方式**：`bandit_lair` 是 `boss` 類型，單場戰鬥列表不列、要打完一輪的前幾場才進得去。為了拍截圖，在 worktree 暫時把地圖檔的 `archetype` 改成 `ruined_heights` 並以 8772 起一個伺服器，拍完已 `git checkout` 還原（沒有 commit）。因此這張的敵人是一般標準敵人，不是 Boss 本人；Boss 單位的圖（`bandit_warlord`、`bandit_boss`）只由對照表保證，沒有實機截圖。
- **靶場**：同樣不在網頁地圖列表，是在頁面載入後以注入的 `fetch` 包裝把 `map_id` 換成 `training_range` 後開戰（沒有改程式）。

## 5. 驗證

- `corepack pnpm -C client exec tsc --noEmit` 通過；相關 vitest（`src/render`、`src/battle/drawModel.test.ts`）通過。
- `uv run python scripts/check.py`：ruff、格式、mypy、import-linter、pytest、client typecheck、client vitest（387 項）全部通過。
- `corepack pnpm -C client build` 成功（`client/public` 的素材由 Vite 複製進 `client/dist/assets/kenney/`，伺服器靜態提供）。
- 複雜度：沒有新增 `# noqa`。

## 6. 待 PM 決定

1. **字體**：未更換。規格寫「可換成」免費字型（例如 Noto Sans TC），但使用者的下載同意只涵蓋 Kenney CC0 包，且 Noto Sans TC 檔案約數 MB（自行託管）或需連外部字型服務（Google Fonts，離線不可用）。要換的話請另行同意，授權為 SIL OFL 1.1，可自行託管。
2. **素材風格與解析度**：兩個包都是 16×16 像素風，放大到每格 52 像素（約 3.25 倍，非整數倍，採最近鄰縮放，邊緣略不均）。若要更銳利，可把 `TILE_SIZE` 改為 48 或 64（影響整個版面，3-14 前再決定），或改選更高解析度的 Kenney 包。
3. **深淵、岩漿、冰窟沒有專屬圖**：目前是石地圖塊乘色，岩漿看起來是橘色方格而非熔岩。若要更像，需再下載其他 Kenney 包（例如含水／岩漿圖塊的包），需另行同意。
4. **角色對照是依外觀挑的**：包內沒有骷髏、法師以外的明確職業圖，例如 `summon_skeleton_warrior` 用了一張人形圖，標準敵人 1～5 階用了蝙蝠、蜘蛛等怪物圖。需要時可只改 `sprites.ts` 的表。
5. **Boss 本人沒有實機截圖**（見第 4 節）；使用者試玩一輪打到 Boss 時請順便看一眼 `bandit_warlord` 與 `bandit_boss` 的圖。
6. **Boss 地圖與靶場的截圖需要暫時改內容或注入請求**；若之後想要網頁上也能直接選（供美術驗收），要另開需求（不在 3-13 範圍）。
7. **物件有圖時不再顯示中文單字圖示**（箱、油、柱……），改靠圖與滑鼠提示認物件；若玩家覺得難辨，可以改為圖加小字。
8. **單位代號字母縮小到左上角**，不遮角色；召喚物的菱形外框保留。陣營色改為半透明圓底，對色盲玩家的區分依賴圓底顏色與代號大小寫，與原本相同。
9. **測試伺服器**：8771、8772 兩個伺服器已關閉（只關自己啟動的）；瀏覽器分頁只關了自己開的一個，另有一個內建瀏覽器分頁（`tab-3`）在操作途中被導向 8772（不確定是否為使用者的分頁），伺服器關閉後會顯示連線失敗，請使用者自行處理。
10. **DrawModel 新增三個欄位**（`TileDraw.surface`、`ObjectDraw.kind`、`UnitDraw.template`）：只供美術對照用，不影響既有測試。
