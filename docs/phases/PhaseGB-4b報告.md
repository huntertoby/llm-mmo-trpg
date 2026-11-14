# Phase GB-4b 報告｜巨型頭目：繪製（正式美術，併 GB-4c）

> 實作者：GB-4b implementer（Opus 5.5；子 agent 兩個：A3 圖示、戰場整合），2026-11-14。依據本機 main `a7dc58ca0`（含 GB-2d、GB-4a），中途兩次 merge 本機 main（美術 6.1 裁定、A5 過審）。
> 規格：`docs/phases/PhaseGB計畫.md` 8.2、第 4 節 GB-4b 列、第 11、12 節、末節開發 PM 裁定；美術 `docs/art/GB巨型頭目-移植需求.md`（A1～A4、A6、6.1、第 8 節）；`PhaseGB-4a報告.md` 末節裁定 4、5、7、9、10；交接 (e3r)。
> 美術已交，所以**直接做正式美術**（規格原本的 4b 占位＋4c 移植併成一段），沒有任何幾何占位。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| API | `PartView.counts_as_behind`（只有殼縫 true，其他 null 不輸出）；重產 `openapi.json`、`schema.d.ts`；`tests/api/test_giant_api.py` 加一項 | `c95f09980` |
| 畫法模組 | 新 `render/qBossGiant.ts`：照 `qBossGiant.js` 逐行搬 A1 立繪（三階段 × 熔殼在／不在、熔殼脫落）、3×3 陣營環、第 3 階段坑底紅光、A2 部位格標示（九種狀態、800 反向放大、背刺記號兩種）、A4 破壞演出（5 格、黑煙、火星、「破」字）、本體填色層；部位遮罩由畫法直接給。`qBoss.ts` 只加 export（`ASH` 色票、`osc`、`cyc`、`bossClipOf`） | `439718a61` |
| A3 圖示 | 新 `render/qIcon/giantParts.ts`（噴口、殼縫、核心、本體縮圖）；`bossParts.ts` 分派、四態合成 `bossPartStateIcon`（霧鎖真人輸出不變）；`ui/PartBar.tsx` 改用它；測試 `qIconGiantParts.test.ts`；開發頁 `client/dev/gb4b-icons.html` | `7aec797d2`、`bf87f1b6c`、`1ca698c5a` |
| 美術 6.1 | 技能主圖出手：「延遲段錨點不是自身（`followup.anchor`）→ 用落下的形狀推導」（`narrative/skill_icon_art.py::_derive_motion`），熔岩濺落維持 `area` | `259253683` |
| 戰場整合 | `UnitDraw.footprint`／`tiles`、`PartDraw.behind`；巨型立繪走 `ResolvedCreature.boss.giant`；南排 z 列；3×3 陣營環、坑底紅光切排掛地面層；HUD＋頭頂部位條三條；3×3 目標紅框與行動框；新 `render/battle/partTileMarks.ts`（`giantPartStates` 接到 `Highlights`）；破壞演出巨型分支；render 端找單位看佔格；新 `render/giantSprite.ts` | `be61825f6`、`28b42542f` |
| 測試、開發頁 | `render/qBossGiant.test.ts`（16）、`render/gb4bGiant.test.ts`（21）；開發頁 `client/dev/gb4b-giant.html`（`set=sprites｜marks｜break｜after｜shed｜field`）；`oclGallery.ts?scene=boss` 加 3×3 場面 | `1d478024a`、`e7ff31511` |
| 文件、截圖 | 上手筆記第一節三列、第四節第 177～181 點；`docs/art/shots/GB-4b/` 截圖；本報告 | `a399d2395`、本報告的 commit |

## 2. 逐條驗收

### 2.1 規格 8.2 與 4a 裁定

| # | 項目 | 結果 |
|---|---|---|
| 8.2-1 | 錨點與大小 | 錨點＝中心格中心往南 72（南排南緣中點），本體寬 3 格；用正式立繪（不是放大的 1 格造型）。`gb4bGiant.test.ts` 鎖錨點 |
| 8.2-2 | z 順序 | 整個節點掛 `rows.row(中心 y + 1)`（南排）、同列 index 0；南邊一排的人後畫蓋在前殼上（截圖 `03`、`03b`） |
| 8.2-3 | OCL | `outlineLayer.rowOf` 對巨型回南排、`canBeBig` 不改；`oclGallery.ts?scene=boss` 加 3×3 場面。實測 3×3 在平地上擋人最多 15%（門檻 55%），不會讓人出外框（待決 4） |
| 8.2-4 | HP 條、蓄力徽章、選取 | HUD 在外接框頂上（錨點往上約 3.5 格，含部位條）；行動虛線與目標紅框改框 3×3 |
| 8.2-5 | 部位格標示 | `render/battle/partTileMarks.ts`＋`qBossGiant.drawGiantMarks`（正式畫法，非占位） |
| 8.2-6 | 演出起點 | `vfxLayer` 的 `creatureAt`／`dollAt`／`overlayFlashAt`、`feedbackLayer.floatTopY` 改看佔格（原本打中非中心格時受擊片段、白閃不播）；浮動字落在打中的那一格 |
| 4a-4 | 短字只用在格子標示 | `markReasonZh` 只給標示；引擎 `PART_REASON_ZH` 沒改 |
| 4a-5 | `counts_as_behind` | API 小改＋重產；`tests/api/test_giant_api.py`、`test_openapi_snapshot.py`、`test_parts_api.py`、`test_client_fixtures.py` 24 passed |
| 4a-7 | 近戰點殼縫、第 2 階段點核心 | 實機（CDP 改寫回應擺情境）`11-real-melee-seam-1600-t1.png`、`12-real-core-p2-1600-t1.png` |
| 4a-9 | `flushSync` 警告與 404 | 見第 4 節：都是 main 既有，本段沒有造成新的 |
| 4a-10 | `giantPartStates` 接 `Highlights` | `Highlights.giantMarks`，和點擊同一份 `PartView.tiles` |
| e3r | 800 寬頭目狀態列移到 HP 條旁 | **沒做**（一般 HUD 版面，不在本段同一批檔；待決 3） |

### 2.2 移植需求逐條（第 2～6 節）

| 節 | 重點 | 結果 |
|---|---|---|
| 2.3 | 定案數字、`G`、外框 1.3G、金外光 2.2G | `GG = (48/52)×1.06×1.6`；外框、外光、細縫線照模型 px，不隨倍率放大 |
| 2.3 | 陣營環 A 案 | `giantGroundRing`（北排 35%、中南 80%、內線、金圈、南緣金菱形、影子），陣營色；掛南排 `under`；不畫 1 格扁圓環與 `bossRingFront` |
| 2.4-1 | 坑底紅光是地面層 | 一排一張畫布掛 4 排各自的 `deco`（地面之上、所有單位之前）；北、側的人沒被染（`04`、`04b`） |
| 2.4-2 | z 順序 | 同 8.2-2 |
| 2.4-3 | 核心只在中排 | 開發頁 `set=sprites&grid=1` 疊 3×3 格線（`01`、`02`） |
| 2.4-4 | 不用 `Math.random` | `qBossGiant.test.ts` 掃原始碼；殼片、黑煙、火星照名稱雜湊 |
| 2.4-5 | 不鏡像 | `renderCreatureCanvas` 對巨型不鏡像 |
| 2.5 | 動作 | 沿用 `bossPlan` 參數（`inhale`、`spout`、`flare`→`charge`、受擊白閃、`dieT`、待機 `loop`），不位移、不用 `ram`；片段自帶的地上特效不畫（待決 5） |
| 3.2 | 九種狀態 | `05`、`05b`（1600）、`06`（800） |
| 3.3 | 800 反向放大 | `drawGiantMarks` 的 `W()`；`marksCompact`（一格 < 40 px） |
| 3.4 | 背刺記號 1600／800 | 只給近戰、`counts_as_behind`；800 U 形箭頭佔內側下角（`06b`） |
| 3.5 | 同一份 tiles、不加小圖、⑤、遮罩 | 見第 3 節 |
| 4 | A3 | 指紋與樣張第 10 節**全部相同**（三部位各 6、本體 2）；自查數字 107／12％、106／8％、151／61％、120／14％ 一致（`07`、`07b`） |
| 5.2 | 5 格時間、白閃、微震、不出浮字、特效最上層 | `giantBreakEffect`（`BREAK_FRAMES_MS`）；第 1 格 `giantFlashCanvas`；`impact.ts` 本來整個畫面震；特效層在單位與標示之上；`part_broken` 不出浮字（PB-1f） |
| 5.3 | 破壞後定稿 | `broken` 旗標畫同一張（`10`、`10b`） |
| 5.4 | 「破」字與 800 放大 | `giantPopScale`＝`minMarkScale(14, 12, 縮放)`；殼縫照 `hit_tile` 那一側（`09b` 字 ≥12 px） |
| 5.5-2 | 離開佔格的殼片不帶金外光 | `freePlates` 自己包黑外框（`10c`） |
| 5.5-5 | 部位條第 4 格換「×」 | `stripBars` 看 `PartFx.frame` |
| 6 | A6 不畫連線 | 沒做事（沿用 BAL-21b） |
| 6.1 | 主圖出手 | 熔岩濺落維持 `area`（預測 1 筆、實際 1 筆：夾具 `skill_icons.json` 只有 `skills.skill_lava_splash.art.motion` aura→area；熔心吸氣 area 照舊） |
| 8 | A5：部位條三條、不被上緣切掉 | 見 2.4 |

### 2.3 第 7 節 8 條（開發 PM 裁定全部照美術建議）

1. 動作：沿用 `qBoss` 時間軸，3×3 不位移、受擊整隻白閃、熔岩柱從中間噴口往上。逐格攻擊連拍**沒拍**（只拍靜態與破壞），待美術要時再補。
2. HUD 與頭頂部位條：加了三條（噴口｜殼縫｜核心，`PART_ORDER` 加 `vent, shell_seam, core`），排法與 800 最小尺寸照 PB-1e 同一套（`partStrip.ts`／`bossPartArt.partStripNode`）。「北邊是岩漿、上方空間夠」：`03`、`03b`、`04`、`04b`、`04c`。
3. 目標紅框：照建議先改成框 3×3、放南排 `frames`（單位之下）實拍，**被前殼幾乎整片蓋掉看不出**，照同條後半改到標示層（`attackTop`，單位與標示之上）；⑤ 不另畫。
4. 遮罩：見第 3 節。
5. 原因字：「呼吸階段才露出」照伺服器的字（GB-4a 已做）。
6. 火星：不收。
7. 第 2、3 階段熔殼在：畫法自然支援，不另寫測試；`01` 順帶有。
8. 檔案位置：`render/qBossGiant.ts`、`render/battle/partTileMarks.ts`、`render/qIcon/giantParts.ts`。

### 2.4 頭頂部位條與畫面上緣（第 8 節第 3 點）

熔心坑的頭目中心在 (5, 3)，HUD 落在北邊岩漿那一排（y 1）上方；地圖北緣外還有一排岩壁與畫布留邊。

| 截圖 | 寬 | 部位條三條 | 上緣 |
|---|---|---|---|
| `03-field-1600.jpg`、`03b-field-boss-1600-nn2.png` | 1600（實機 94%） | 看得到三條 | 沒被切掉（HP 條上緣在畫面 y 234，離畫布上緣約 166 px） |
| `04b-p3-800-t1.png`、`04c-hud-800-nn4.png` | 800（實機 53%） | `04c`（第 2 階段、噴口已破）最近鄰 ×4 看得出「×」＋兩條米白；真 1 倍每條約 6 px 寬，只分得出破沒破、看不出血量細節（尺寸照 PB-1e 800 下限：條高 ≥2 px、× ≥4 px） | 沒被切掉（HP 條上緣在畫面 y 170，離畫布上緣約 94 px） |
| `04-p3-1600-t1.png` | 1600 | 看得到三條 | 沒被切掉 |

### 2.5 結束碼（交件前一次）

- `corepack pnpm -C client typecheck`：**0**
- `corepack pnpm -C client test`（全量）：**0**（364 檔、4631 項；`qIconQi2d` 也過）
- `corepack pnpm -C client build`：**0**
- Python：`ruff check`、`ruff format --check`、`mypy`（改到的檔）0；`tests/api/test_giant_api.py` 等 24 passed；`tests/narrative/ -k icon` 133 passed。

## 3. 部位遮罩怎麼取得（移植需求第 11 節 (b)）

不用樣張的換色相減。`qBossGiant.giantPartMask(st, part, res)` 照常畫整個本體，但每個零件前切換合成模式：那個部位的零件（噴口＝三支 `vent()`、殼縫＝兩條 `seam()`、核心＝`cavity()`＋`core()`）`source-over` 上色，其他零件 `destination-out` 擦掉，所以被後畫的零件（背殼、殼蓋、甲蟲、殼片）蓋住的地方自然不算；最後 `source-in` 填白成不透明遮罩。滑過亮起 `giantGlowCanvas`＝遮罩圓盤膨脹兩次（外框色襯邊、亮青白描邊，畫面線 ≥1.5／≥1 px）＋部位上 35%；第 1 格白閃 `giantFlashCanvas`＝遮罩白 0.9。同 PB-1e `partLayer` 的做法。

## 4. 開工前查：`flushSync` 警告與 404（GB-4a 待決 9）

用改 render 之前的程式查：
- `flushSync was called from inside a lifecycle method`：只在 vite 開發模式出現、正式 build 沒有；來源是 `screens/battle/usePlayback.ts` 的 `flushSync`，main 既有，不是本段造成，沒修。
- 404：`/api/tuning/status`（數值工坊沒開時的正常回應）、`favicon.ico`（dev server 才有），都是既有。另一個 `characters/undefined` 是實測腳本把 localStorage 寫錯造成的，不是遊戲問題。

## 5. 截圖（`docs/art/shots/GB-4b/`，DPR 1、`?mute=1`）

張數超過 10：每張要壓在 300 KB 內，九種狀態、破壞連拍各拆兩張；另加 GB-4a 待決 7 的兩張實機與第 8 節的 800 HUD 特寫。

| 項 | 檔 | 大小 | 來源 |
|---|---|---|---|
| 1 | `01-sprites-1600-t1.png` | 230K | 開發頁・實機未看 |
| 2 | `02-sprites-800-t1.png`、`02b-sprites-800-nn4.png` | 68K、95K | 開發頁・實機未看 |
| 3 | `03-field-1600.jpg`、`03b-field-boss-1600-nn2.png` | 118K、154K | 實機 |
| 4 | `04-p3-1600-t1.png`、`04b-p3-800-t1.png`、`04c-hud-800-nn4.png` | 189K、174K、31K | 實機 |
| 5 | `05-marks-1600-t1-a.png`、`05b-marks-1600-t1-b.png` | 189K、210K | 開發頁・實機未看 |
| 6 | `06-marks-800-t1.png`、`06b-seam-800-nn4.png` | 103K、66K | 開發頁・實機未看 |
| 7 | `07-icons-t1.png`、`07b-menu.png` | 124K、92K | 開發頁・實機未看（選單情境用真 `PartMenu`／`UnitParts`） |
| 8 | `08-break-1600-t1-a.png`、`08b-break-1600-t1-b.png` | 276K、238K | 開發頁・實機未看 |
| 9 | `09-break-800-t1.png`、`09b-pop-800-nn4.png` | 169K、108K | 開發頁・實機未看 |
| 10 | `10-after-1600-t1.png`、`10b-after-800-t1.png`、`10c-shed-1600-nn2.png` | 264K、68K、190K | 開發頁・實機未看 |
| 4a-7 | `11-real-melee-seam-1600-t1.png`、`12-real-core-p2-1600-t1.png` | 183K、177K | 實機 |

- 「實機」都是熔心坑開發 Boss（上手筆記第 176 點），用 CDP `Fetch` 改寫回應擺情境（南邊兩側站人、第 3 階段、近戰站殼縫旁、第 2 階段核心露出），所以畫面是真的遊戲、部分站位與浮字是改寫造成的。實機自動縮放 1600＝94%、800＝53%；開發頁照移植需求用 1.308／0.531。
- 浮動卡流程（1600×900、800×600）：格子資訊卡滑過出卡 → 點釘住 → Esc 關閉正常；技能卡滑進不關 → 釘住 → 離開仍在 → 關閉正常；兩種卡內容沒超出，沒有可捲的內容。

## 6. 和樣張不同的地方

- 目標紅框與 ⑤ 畫在標示層（2.3 第 3 條）；選目標時紅框一直在，① 的截圖也看得到紅框。
- 坑底紅光切成一排一張畫布（不用同一張貼圖的子矩形：`ArtTextures` 淘汰子貼圖時會連來源一起銷毀）。
- 片段自帶的地上特效（噴發環、衝撞星爆，位置是照 1 格算的）巨型不畫。
- 熔殼殼片飛走的約 0.16 秒內會短暫疊到頭頂 HUD（`10c`）。
- 待機一圈首尾接上：`loop` 有值時振盪取整數次（樣張沒有這個參數；沒給時逐式相同）。
- A3 本體圖示狀態多帶 `t: 300`（樣張的呼吸那一刻），指紋因此和樣張相同。

## 7. 規格沒寫到、採保守做法

1. 沒有選取模式（點敵人＝普攻）時，部位格標示只在滑到頭目身上才畫（一直畫太雜）；有選取模式時一直畫。
2. 近戰判斷（畫不畫背刺記號）：伺服器回了近戰才有的原因字，或普攻時武器大類是 melee。
3. 原因 → 小圖：「只有遠程才打得到」→ 遠程；「那一格超出射程」「要貼著那一格才打得到」→ 射程；「看不到那一格」→ 視線；其他 → 射程。
4. A3：巨型頭目的判斷只看範本 `ashen_heart`（`BossDoll` 沒有 footprint；目前只有灰燼之心一種巨型立繪）。
5. A3 選單「本體」列字照舊「本體」（`partMenuRows` 寫死；巨型頭目不開選單，角色卡沒有本體列）。
6. 美術 6.1：開發 PM 指的是 `skill_icon.py` 的 `icon_of`，實際推導在同目錄 `skill_icon_art.py::_derive_motion`（`icon_of` 經 `derive_art` 呼叫），改在那裡。參考實作（美術的 `docs/art/sample/tools/qskills_derive.py`）不動，`tests/narrative/test_skill_icon_art_qi2a.py` 加 `REFERENCE_OVERRIDES` 列出刻意不同的這一筆。

## 8. 影響

- 前端讀 `UnitView.footprint`／`tiles`、`PartView.counts_as_behind` 為選填；1 格單位（含霧鎖真人、1 格灰燼之心、碎晶之主）的畫法鍵與輸出不變（既有 vitest、指紋、快照全過）。
- 技能主圖夾具只動熔岩濺落一筆。舊紀錄、存檔不受影響（沒改引擎規則）。

## 9. 平衡疑慮

無新增（本段不改規則與數值）。

## 10. 待 PM 決定

1. 目標紅框從單位之下改到標示層（前殼蓋掉看不出；第 7 節第 3 條後半）——請美術 PM 看 `03`、`05` 確認。
2. 沒有選取模式時，部位格標示只在滑到頭目身上才出現（第 7 節第 1 點，本段自加的限制）。
3. (e3r) 800 寬頭目狀態列移到 HP 條旁沒做（一般 HUD 版面），請另排。
4. 3×3 在平地上不會讓任何人出外框（擋到 ≤15%、門檻 55%）；要不要對巨型頭目另降門檻？
5. 熔岩噴發、吸氣時 1 格版的地上特效環不畫在 3×3 上；要不要請美術出 3×3 版？
6. 攻擊片段（噴發、火焰箭、受擊、倒下）的逐格連拍沒拍（第 7 節第 1 條「做完拍一組」），要不要補一段給美術看？
7. 「要貼著那一格才打得到」的格子小圖用「射程」圖樣，是否要美術另出「要貼近」圖樣？
8. A3 選單本體列要不要改字「前殼（本體）」（目前巨型頭目不開選單，影響只在霧鎖真人以外的未來巨型頭目）。
9. 開發模式的 `flushSync` 警告是 main 既有（`usePlayback.ts`），要不要排一段處理？

## 開發 PM 裁定（2026-11-14）

- 接受。4b、4c 併一段（美術已全交）。
- 子 agent 補拍的 `04c-hud-800-nn4.png` 留在 worktree 沒 commit；開發 PM 看過，裁切位置錯了（拍到地圖左上角，不是頭目 HUD），不收。800 以 `04b` 為準。
- 待決 2：同意（沒選取模式時只在滑過頭目時畫部位格標示）。
- 待決 3：(e3r) 照原待排另做。
- 待決 9：`flushSync` 警告是 main 既有、只在開發模式，記待排低優先。
- 待決 1（紅框改到標示層）、4（巨型頭目要不要另降外框門檻）、5（熔岩噴發、吸氣的 3×3 地上特效環）、6（攻擊片段逐格連拍要不要補）、7（「要貼著那一格」借用射程圖樣）、8（選單「本體」列改「前殼（本體）」）轉美術 PM。
- 請美術驗收 `docs/art/shots/GB-4b/`。
