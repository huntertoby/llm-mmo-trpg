# Phase PR-2c 報告｜靶場木樁與場景畫法

> 規格：`docs/phases/PhasePR-2計畫.md`「PR-2c」與開頭「第 1～10 點已定」（第 8 點木樁在 3F 一起換、第 9 點不改地圖）。
> 美術依據：`docs/art/靶場移植需求.md` 第 2 節、`docs/art/OB與PR樣張.md` 第 4 節（`docs/art/sample/obSamples.js` 的 `dummy()`、`rail()`、`pool()`／`poolRim()`）、`docs/art/OB與PR移植需求.md` 第 2 節 PR-2 第 2 點、第 4 節第 9 項。
> 實作者：Opus 5.5（2026-11-12）。worktree 從 origin/main 開，先 `git merge --ff-only main`（含 `9e136ae0`）。

## 1. Commit

| commit | 內容 |
|---|---|
| `0c79f2ce` | `feat(render)`：木樁外觀與閃白、測試模式的滑軌與方角水池、C 組測試 |
| `97b60948` | `feat(dev)`：開發頁 `practice-gallery` 與 5 張截圖 |
| （本報告那一筆） | `docs`：本報告、上手筆記 |

沒有 push。

## 2. 做了什麼（對應交付編號）

### 交付 1：木樁外觀＋閃白

- 新檔 `client/src/render/trainingDummy.ts`：`isTrainingDummy`（範本 `training_dummy`、`training_dummy_moving`）、`drawTrainingDummy`（`obSamples.js` 的 `dummy()` 逐行搬，用遊戲端同一套 `inkStyle.ink/stroke/ellPts`，0.86 倍）、白閃剪影 `drawTrainingDummyFlash`、`DUMMY_FLASH_MS = 100`、`dummyFlashAlpha`、`dummyFlashMs`。
- `render/unitSprite.ts`：`buildUnitSprite` 遇到木樁走 `buildDummySprite`——只畫木樁（貼圖含地上影子，`ArtTextures.dollFx` 紙娃娃大小的畫布），**沒有陣營圈、朝向三角形、血條、字母標記**；行動中的虛線圈、狀態列與徽章照一般單位；倒下（3F 打倒時）照倒地的透明度與去色。`bodyTexture`（走路、待機）回同一張木樁貼圖；`hasSkeleton`、`uprightTexture` 對木樁回 false／null；`overlayFlashKind` 多一種 `"dummy"`，`flashTexture` 回木樁的白色剪影。
- `battle/drawModel.ts`：木樁的 `UnitDraw` 帶 `noBar: true`（只在木樁時加這個鍵；其他單位的欄位和改前相同）。
- 閃白：`render/reactEffects.ts` 新 `dummyFlashEffect`——木樁受擊（hit／heavy／block／down）只在木樁上疊白色剪影，0.1 秒 × 播放速度倍率，整段同一個強度 0.85；閃避不閃。`render/battle/vfxLayer.ts`：沒有反應資料的舊路徑也走它；減少動態的「重擊加長白閃」（`steadyFlashAt`）跳過木樁。
- **減少動態**：效果標成身體片段（`motion: "body"`），`reduceEffects` 直接畫最後一格不再動——同一張白閃停一下、結束拿掉＝「一格」（規格允許「不閃或一格」，取一格）。
- 技能工坊（3F）不帶測試模式旗標，木樁一樣換（第 8 點）。

### 交付 2：滑軌

- 新檔 `client/src/render/practiceRange.ts`：`PRACTICE_SCENES`（鍵＝`map_id`）、`railGeometry`（樣張 `rail()` 等比例縮到一格 48：軌距 ±6、枕木寬 7 上下各 8.5、間距 22、軌道在那一排 0.62 高度）。
- training_range：會動的木樁站 (9, 3)（`newcomer.yaml`），滑軌照樣張「5 格、木樁在中間偏右」放在**第 3 排第 7～11 欄**（右端到地圖右緣內 6）。
- `render/battle/terrainLayer.ts` 新 `drawPracticeScene`：枕木＋兩條鐵軌畫在第 3 排的表面裝飾層（人站在上面）。只在 `DrawModel.practice` 存在（`view.practice`）時畫。

### 交付 3：水池

- `practiceRange.poolGeometry`：水池範圍＝地圖上的三格水面 (6, 8)、(7, 8)、(6, 9)（L 形）。
  - 水面：每格一塊**方角**的水（`Explore.C.water` #3f7aa8＋兩道波紋，`Explore.ground("w")` 的畫法），畫在地形層、蓋掉原本圓角羽化的水面；相鄰水面互蓋 1 像素，**格縫十字線不透出來**；水面的飄動反光（6N-9）照舊疊在上面。
  - 石條：外圈方角石條（寬 9×48/52，北邊受光 #d0c8b8、其餘 #b8b0a0、墨線描邊、接縫短線），在水面外（壓在隔壁格上，同樣張）；外角往外多伸一個石條寬；**L 形內角方角**（(7,8) 南邊石條與 (6,9) 東邊石條在 (7T, 9T) 方角相接，不磨圓）。石條放在它壓到的那一排的表面裝飾層（那一排的人站在它上面）。
  - 南緣貼地圖下緣（畫布下面沒有留邊）：那一邊的石條改畫在水面裡面，水面停在石條內緣。
  - 結冰、蒸發的格子不畫方角水面（照原本的地形貼圖），石條照舊圍著範圍。
- 實戰與技能工坊沒有 `DrawModel.practice`，`drawPracticeScene` 第一行就回去，水面照舊（圓角羽化）。
- `render/BattleRenderer.ts` 加一行呼叫 `drawPracticeScene`（地形格畫完、地表動畫之前）。

### 交付 4：地圖與內容不改

沒有改 `content/`、後端、地圖。樣張的效果用現行地圖做得出來，不必停下回報。

### 交付 5：測試（C 組）

新檔 `client/src/render/pr2cPractice.test.ts`（15 項；地圖讀實際的 `content/maps/training_range.yaml`、`content/world/newcomer.yaml`）：

| # | 測試（describe › it） |
|---|---|
| C1 | `PR-2c C1：木樁的畫法選擇` › 兩種木樁範本 → 木樁畫法、沒有血條；其他範本照舊／木樁的節點只有 BODY，沒有陣營圈、朝向三角形、血條／走路待機的貼圖也是木樁、白閃用不含影子的白色剪影／技能工坊（3F）的木樁也換 |
| C2 | `PR-2c C2：滑軌與方角水池只在測試模式` › practice=false 的 DrawModel 沒有 practice 鍵、其餘和測試模式逐欄相同（JSON 全文比對）／實戰非木樁單位沒有 noBar 鍵／表上沒有的地圖沒有滑軌水池／**表和 content 一致**（水池＝yaml 水面、滑軌在會動木樁那一排且包含它、5 格、在地圖內、不壓牆） |
| 幾何 | `PR-2c：水池幾何` › 每格方角水面、互蓋 1、貼下緣停在石條內緣／石條池外一圈、外角外伸、內角方角、地圖外不畫／水面每條外緣都貼著石條（沒有露出地磚）／結冰蒸發不畫水面、石條不變／滑軌位置與枕木 |
| C3 | `PR-2c C3：木樁閃白` › 受擊一個 0.1 秒白閃（照播放速度縮放）、整段 0.85、結束拿掉；heavy 也閃、dodge 不閃／減少動態：第一次更新就是最後一格、同一張白閃停住、結束拿掉 |

「實戰不變」由 C2 第 1、2 項鎖住（`view.practice=false` 時 DrawModel 沒有 `practice`，其餘欄位與測試模式那份逐字相同；非木樁單位沒有 `noBar`），繪製端 `drawPracticeScene` 沒有 `practice` 時不畫任何東西。

### 交付 6：截圖

見第 5 節。

## 3. 逐條驗收

| 驗收（2c） | 結果 | 證據 |
|---|---|---|
| `corepack pnpm -C client typecheck` | **0** | 交件前跑 |
| `corepack pnpm -C client test` | **0**（288 檔、3562 項全過） | 交件前跑 |
| `corepack pnpm -C client build`（`tsc --noEmit && vite build`） | **0**（只有既有的 chunk 大小警告） | 交件前跑 |
| 雜湊快照（`render/creaturePose.test.ts`、`render/inkDollSnapshot.test.ts`）照舊通過 | 通過；`render/__snapshots__/` 沒有變動 | 整包測試後 `git status` 乾淨 |
| C 組行為一致測試 | 全過 | 第 2 節交付 5 |
| 移植需求第 4 節第 9 項：三種木樁特寫一張、被打閃白一張 | 有 | `c-9-dummies-3x.jpg`、`c-9-hit-flash-3x.jpg` |
| 和 `practice-board-dummies-3x.png`、`practice-pool-4x.png` 並排對得上 | 對得上（見下） | `c-9-dummies-3x.jpg`、`c-9-pool-4x.jpg` |
| 實戰一場確認水面與單位畫法沒變 | 單位：有陣營圈、血條、朝向三角形，和改前相同；水面：該場地圖（雲海吊橋）沒有水，水面改看並排圖右半（不帶旗標＝3F／實戰畫法，圓角羽化照舊） | `c-real-battle-1280.jpg`、`c-compare-practice-vs-3f.jpg` |

和樣張並排看的結果（自己看過）：

- 木樁：圓布頭（兩撇眼）、麻布身三道繩、橫臂、細木樁、深色梯形底座、地上影子；沒有血條、沒有陣營圈。比例和樣張相同（樣張 0.86 倍）。
- 滑軌：兩條灰鐵軌、一排短枕木，枕木只比鐵軌多一點，不像柵欄；木樁站在軌上。
- 水池：水面方的、角都填到石條內緣、沒有露出地磚、中間沒有格縫十字線；四邊淺色石條有接縫；L 形內角方角。
- 閃白：被打的木樁整個變白色剪影（地上影子不變白、不畫白圓），旁邊的木樁照常。

另外：`/?dev=1` 單場戰鬥 1280×720 的 `__layoutSmoke.runCase("PR-2c")` 順手跑了一次：全 PASS（不是本段的驗收項）。

## 4. 和規格不同的地方與理由

1. **多改了 `render/BattleRenderer.ts` 一行**（呼叫 `drawPracticeScene`）。規格的「只改」沒列這個檔，但整場重畫 `draw()` 在這裡，石條要在地形格全部畫完後才放得進正確的排。只加一行。
2. **閃白用剪影，不用樣張 `dummy(hit)` 的放射光暈**：樣張寫「閃白的參數留著，樣張沒有用」；遊戲端 6C-8 起受擊一律「只閃剪影、不畫整片白圓」，照遊戲端（待 PM 決定第 1 點）。
3. 木樁腳底放在一般單位的腳底（格子中心下 0.23 格），不是樣張戰場的 0.86 格高度：和戰場上其他人同一條腳底線、狀態列位置不用另算（待 PM 決定第 6 點）。

## 5. 截圖（`docs/art/shots/pr2/`，本段 5 張，皆 jpg 品質 80、≤ 300 KB）

| 檔案（完整路徑） | 內容 | 大小 |
|---|---|---|
| `docs/art/shots/pr2/c-9-dummies-3x.jpg` | 第 9 項：三種木樁特寫合成一張（滑軌上、水池裡、平地），3 倍（`deviceScaleFactor: 3`） | 86 KB |
| `docs/art/shots/pr2/c-9-hit-flash-3x.jpg` | 第 9 項：平地木樁被打閃白（右邊滑軌木樁照常），3 倍 | 27 KB |
| `docs/art/shots/pr2/c-9-pool-4x.jpg` | 方角水池特寫（L 形、內角方角、下緣石條在內），4 倍 | 21 KB |
| `docs/art/shots/pr2/c-compare-practice-vs-3f.jpg` | 同一張 training_range：左測試模式、右不帶旗標（3F／實戰的水面畫法不變；木樁兩邊都換） | 91 KB |
| `docs/art/shots/pr2/c-real-battle-1280.jpg` | 實機：自己的 `trpg serve` ＋ `/?dev=1` 單場戰鬥（`__layoutSmoke.runCase` 開的那場），單位畫法不變 | 91 KB |

怎麼拍：前四張是 `client/dev/practice-gallery.html`（自己的 vite，埠 5235）＋無頭 Chrome（`--mute-audio`，CDP 埠 8115）；第 5 張是 `corepack pnpm -C client build` 後 `TRPG_SAVE_DIR=<暫存> TRPG_DEV_ROUTES=1 uv run trpg serve --port 8114`，開 `/?dev=1&anim=0.1&mute=1`、`localStorage.clear()`、`await window.__layoutSmoke.runCase("PR-2c")`。截完用自己記下的 PID 關掉 vite（35228）、伺服器（26556）、Chrome（12800 與其子程序），之後 5235、8114、8115 都沒有在聽。

## 6. 實機未看

- **測試模式戰鬥的實機畫面**（工坊師傅 → 靶場試玩、或選大類的「拿起試打」進去的那場）：入口與 HUD 是 PR-2b，本段用開發頁 `practice-gallery`（真的 `buildDrawModel`＋`BattleRenderer`，地圖照 yaml 抄）畫。2b 合併後要在實機看一次滑軌、水池、木樁。
- **技能工坊（3F）試玩的實機**：沒進去看；畫法由並排圖右半與 C1 第 4 項證明（同一個 `buildUnitSprite`）。
- **閃白在實際播放速度下**：截圖是開發頁把白閃拉長成 5 秒拍的；正常速度 0.1 秒沒有逐格截。
- **會動的木樁走路**：沒看實機；走路片段換貼圖時回同一張木樁貼圖（`bodyTexture`），整個平移。

## 7. 快照變動

無。`render/__snapshots__/` 兩個檔沒有變（木樁不在靜態異形、人形的快照裡）。

## 8. 新增的複雜度例外

無（前端沒有 C901 類的檢查；新函式都短）。

## 9. 待 PM 決定

1. **閃白畫法**：用遊戲端的白色剪影（6C-8），不用樣張 `dummy(hit)` 的放射光暈；強度 0.85、整段不淡出、0.1 秒 × 播放速度倍率；減少動態時同一張白閃停一格。要改成光暈請美術 PM 定。
2. **滑軌與水池的位置寫在前端的表**（`render/practiceRange.ts` 的 `PRACTICE_SCENES`，鍵＝`map_id`），不是伺服器給的；`pr2cPractice.test.ts` 讀 yaml 鎖住一致。之後若有別的靶場地圖，要不要改成內容檔（地圖 yaml 加 `decor`）由伺服器給。
3. **滑軌的長度與位置**：第 3 排第 7～11 欄（照樣張 5 格、木樁在中間偏右，右端到地圖右緣）。會動的木樁（`drift`）會往任何方向退開，可能離開滑軌；滑軌只是外觀（規格「不影響規則」）。
4. **水池貼地圖下緣**：畫布下面沒有留邊，那一邊的石條畫在水面裡面（水面少 9×48/52 像素）。要改成畫布下緣留邊、石條在外，要動 `STAGE_MARGIN`（影響實戰版面），沒做。
5. **水池格結冰或蒸發**：那一格不畫方角水面（看到原本的石地＋冰面畫法），石條照舊圍著。要不要讓結冰格也先鋪水色再疊冰，請美術 PM 看。
6. **木樁的腳底高度**：放在一般單位的腳底線（格子中心下 0.23 格），比樣張戰場（0.86 格高度）高約 6 像素。
7. **移動格（藍格）貼水池時內縮 9 不壓石條**：樣張有，本段沒做（高亮層不在 2c 的檔案範圍，樣張也註明藍格只是示意）；現在藍格、紅框會蓋到石條外緣。要做的話排進 2b 之後的小段。
8. **木樁以外的地方仍是舊外觀**：行動順序列（`TurnBar`，3F 會顯示；測試模式 2b 拿掉）、格子資訊卡等若有用範本畫小人頭像的，木樁仍是預設人形。本段只改戰場上的單位。
9. **石條與枕木用 Pixi 直線畫**（填色＋墨線描邊＋接縫），沒有樣張 `ink()` 的手繪抖動；木樁本身用遊戲端的 `ink()`（有抖動與暗面排線）。截圖上看不太出差別，美術 PM 若要抖動再改成貼圖。
10. **測試模式水色**：方角水面用樣張的城鎮河水色 #3f7aa8（比實戰水面 #3a86d8 暗一階），只在測試模式；實戰水色不變。

## 10. 上手筆記

`docs/dev/上手-前端戰鬥畫面與動畫.md` 更新了：

- 第一節檔案表：加 `render/trainingDummy.ts`、`render/practiceRange.ts` 兩列；
- 第二節「從點擊到畫面」：加第 7 點（測試模式的戰場畫法、`DrawModel.practice`、石條放在哪一排、木樁 `noBar`）；
- 第二節「開發入口」表：加 `client/dev/practice-gallery.html`；
- 第四節常踩的坑：加第 22 點（滑軌與水池範圍是前端的表、改地圖要一起改；貼地圖邊緣時石條在內；結冰時的畫法），原第 22 點順延為 23；
- 第五節測試表：加「靶場木樁、測試模式的滑軌與水池」一列。
