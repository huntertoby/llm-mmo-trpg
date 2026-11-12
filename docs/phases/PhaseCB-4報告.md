# Phase CB-4 報告｜戰鬥特效落點修正：頭目的正南／正北、斜向目標

> 實作者 2026-11-12。依據 `docs/phases/PhaseCB-4計畫.md`（第 0.0 節定稿：Q1～Q7 全照「建議」），起點 main `47b8bc58`（含規格定稿）。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 1 方向化的轉向 | `creatureFxTurn.ts`：`creatureFxTurnOf` 回 `FxTurn` ＝ {x: sign(dx), y: sign(dy)}（同一排、自己、沒目標 → `null`）；`turnCreatureFx` 改成剪切（原點＝「相鄰目標」點，u ＝ x − 52 → (|x| × u, y ＋ y方向 × u × c)；x 方向 0 時沿用 CB-3c 原式，含吐息）；`creatureFxAnchorPx` 轉向時回 (方向 x × 一格, 方向 y × 一格)。`creaturePose.ts`：`fxTurn?: FxTurn`、鍵 `fxturn<x>:<y>`（沒有轉向時鍵與量化逐字不變） | `f7d48995` |
| 2 頭目 | `skillLayer.ts` 拿掉頭目排除；`qBoss.ts` 加 `BossActOpt.noFx`（`drawBossFrame` 有 `fxTurn` 時傳）與 `bossPoseFx(boss, pose)`（同 `bossAct` 畫進貼圖的特效，不含 `ranged`）；`inkCreature.ts` 的 `turnedCreatureFx`、`renderCreatureFxCanvas` 頭目走 `bossPoseFx`，大小用 `fxSizeOf`（頭目 1）；`artTextures.creatureFx` 頭目不再回 null，`fxTurnScale(fxSizeOf(r), 頭目 ? HUGE_FIELD_SCALE : 1, DOLL_SCALE)`。`bossPlan`、`bossAttackHitU` 沒改 | `f7d48995` |
| 3 斜向一般異形 | 同交付 1；`placeTurnedFx` 錨點放 `draw ＋ 方向`（斜對角那一格），抬高照那一格。`CREATURE_FX_BOX` 寬 176 → 240（見第 4 節） | `f7d48995` |
| 4 開發頁案例 | `skill-gallery.html#cb2b?case=`：`ahRamS`（灰燼之心第 1 階段普攻打正南）、`ahRamEdgeWN`（站最左欄朝西打正北）、`ahRamE`（東西向對照）、`lordSwingS`（碎晶之主普攻打正南）、`lordSwingEdgeN`（站最右欄打正北）、`boarSE`（硫煙獸挑獠牙打東南）、`boarWNW`（朝西打西北）、`matriarchEdgeSW`（熔爐母獸精英＋大型站最右欄打右下角的西南）。案例多一個 `bossPhase`（→ `UnitView.boss_phase.index`） | `d1c83d6a` |
| 5 測試 | 新檔 `render/cb4FxAnchor.test.ts`（97 項）；改 `render/cb3cFxTurn.test.ts`（第 5 節） | `f7d48995`、`fae1202a`、`54c99345` |
| 截圖 | `docs/art/shots/cb4/` 10 張 | `f753c0b7` |
| 6 報告、上手筆記 | 本檔；`docs/dev/上手-前端戰鬥畫面與動畫.md` 第二節「特效落點」、第四節第 3 點、開發入口、第五節測試表 | 本檔的 commit |

## 2. 驗收逐條

1. **測試全過、雜湊快照不變**：`corepack pnpm -C client exec vitest run src/render/cb4FxAnchor.test.ts src/render/cb3cFxTurn.test.ts src/render/creaturePose.test.ts src/render/inkDollSnapshot.test.ts src/render/qCreatureAnim.test.ts src/battle/creatureAction.test.ts` → `Test Files 6 passed (6)`、`Tests 180 passed (180)`。另跑 `qBoss4b.test.ts`、`test/importCycles.test.ts` → 21 passed。`creaturePose.test.ts`、`inkDollSnapshot.test.ts` 的雜湊快照**沒有變**（`__snapshots__` 沒有改動）。
2. **交件前三個結束碼**（分開記）：`corepack pnpm -C client typecheck` → **0**；`corepack pnpm -C client test` → **0**（`Test Files 299 passed (299)`、`Tests 3810 passed (3810)`）；`corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）。
3. `git diff --stat 17982c56 -- src/trpg content client/src/api` → **空**。
4. 截圖齊全（第 7 節）；邊欄三張（2、4、7）特效完整在畫布內。
5. `__layoutSmoke.runCase` 三尺寸（正式 build＋自己的 `trpg serve --port 8149`、`?dev=1&anim=0.1&mute=1`、每次先 `localStorage.clear()`）：1600×900、1040×624、800×600 皆「全 PASS」。

### 行為一致測試（規格 1～6）對應

| 規格 | 測試（`cb4FxAnchor.test.ts`） |
|---|---|
| 1 錨點表 | `CB-4 錨點表：8 方向 × 一般／精英＋大型／兩個頭目 × 原本朝東／朝西`（64 項）：東西向＝修改前（`creatureOffsetPx` 算的值，另寫死 50.88／73.14／81.41）；其他＝目標格中心（容差 0.01 px） |
| 2 實際片段 | `CB-4 實際片段：…`（4 片段 × 6 方向＝24 項，逐格 12 格／自己的格數）＋「片段特效的數值取自片段函式」＋「轉向貼圖放得下」 |
| 3 退化一致 | `CB-4 退化一致：…`：全部身形全部攻擊片段逐格 × 正南北 × 兩種大小，`turnCreatureFx` 和抄來的 CB-3c 原式 `toEqual`（> 100 組，含斜噴的吐息）；同一排 `null`、沒有轉向時鍵與量化逐字同修改前 |
| 4 頭目身體貼圖 | `CB-4 頭目身體貼圖：…`：灰燼之心 `ram`、碎晶之主 `swing` 每一格，假畫布紀錄「沒轉向＝有轉向的身體那幾筆＋`drawCreatureFx` 那幾筆＋最後的 restore」；沒有特效的格兩者逐筆相同 |
| 5 命中對齊不變 | `CB-4 命中對齊不變`：40 個一般片段的 `creatureAttackHitU`、兩個頭目 9 個片段 × 第 1～3 階段的 `bossAttackHitU`，和修改前（17982c56，同一段程式在改動前跑出來的值）逐筆相同 |
| 6 舊程式下會失敗 | 第 5.3 節 |

## 3. 根因確認（對照計畫第 1 節）

A、B 兩段都和計畫一致，行號相同。補充兩點：
- 舊的 `creatureFxAnchorPx` 本身沒有排除頭目（同一欄時本來就回 (0, ±一格)），頭目被擋在 `skillLayer` 第 224 行與 `turnedCreatureFx`／`creatureFx`／`drawBossFrame`；所以錨點表裡「頭目正南北」那幾列在舊程式下也會過，頭目沒接上的證據在「實際片段」與「頭目身體貼圖」兩組（第 5.3 節）。
- `skillLayer` 轉身（`turn`）會更新 `unitDrawOf` 的朝向，所以 `placeTurnedFx` 讀到的 `creatureSide(draw)` 是轉身後那一面；斜向時鏡射方向正確，不必另外傳。

## 4. 轉法與頭目換算

- **剪切**：「相鄰目標」點（x ＝ 52）放在目標方向的相鄰格中心；u ＝ x − 52；新座標 (|方向 x| × u, y ＋ 方向 y × u × c)，c ＝ `fxTurnScale(size, field, DOLL_SCALE)` ＝ 1 ／（size × field × 1.06），讓 u ＝ −52（異形自己）剛好往回一格（48 px）。斜向時橫向保留 u（照原樣張比例，所以精英＋大型的橫向是 1.406 px／單位、縱向是 0.923 px／單位，Q1 (a) 的預期）。吐息方向向量 (cos, sin) → (|x| × cos, y × c × cos ＋ sin)，`atan2`＋長度照比例；x ＝ 0 時用 CB-3c 原式（退化測試逐筆相同）。
- **頭目**：貼圖不含大小（size 1）、戰場縮放 1.6 → 每單位 1.5655 px；東西向錨點 52 × 1.5655 ＝ 81.41 px。正南北／斜向時（相對目標格中心、地面落點）：灰燼之心 `ram` 星爆 (斜向 ∓3.1, ∓1.8)、正南北 (0, −1.8)，塵土 (∓12.5, ∓7.4)；碎晶之主白弧 (∓12.5, ∓7.4)。都在格內（Q3 的 2～13 px 相符）。
- **畫布**：`CREATURE_FX_BOX` 由 176 加寬到 240（半寬 120）。量全部身形全部攻擊片段 × 精英＋大型（1.4375）× 6 方向：特效（含半徑）橫向最遠 112.9（甲蟲 `burst` 第 11 格的光點），身後的塵土 −94.9（`boar gore`），176 會裁到；縱向 −136～69，在 −200～100 內。原點仍在中線，同一欄的畫面不變（只是透明邊變寬）；`cb4FxAnchor.test.ts`「轉向貼圖放得下」鎖住。

## 5. 快照與既有測試的改動

### 5.1 雜湊快照

`creaturePose.test.ts`、`inkDollSnapshot.test.ts` 不變（沒有重產任何快照）。

### 5.2 `cb3cFxTurn.test.ts` 逐條（舊斷言 → 新斷言）

| # | 位置 | 舊 | 新 | 理由／舊程式下 |
|---|---|---|---|---|
| 1 | 「8 方向」表，斜向 16 列 | 斜向錨點＝修改前（`creatureOffsetPx` 的 ±50.88／73.14, 0） | 斜向錨點＝目標格中心 (dx × 48, dy × 48)，且在格內 | 本段有意改變（D2）。舊程式下這 16 列**失敗**（實測 16 fail） |
| 1' | 同表，同一欄 8 列 | `{x: 0, y: dy × 48}` | 同一條 `{x: dx × 48, y: dy × 48}`（dx ＝ 0 時就是原值） | 同一欄期望值逐字相同，只是和斜向合成一個分支；東西向 16 列原封不動 |
| 2 | 「只有同一欄算轉向」 | 正南 `toBe(1)`、正北 `toBe(-1)`；(2, 4)（西南）`toBeNull()` | 正南 `toEqual({x:0,y:1})`、正北 `{x:0,y:-1}`；西南 `toEqual({x:-1,y:1})`；同一排改用 (4, 3)、(0, 3)、自己 → null | 型別改成方向（規格「型別擴成能表示斜向」）；西南由 null 改成方向是本段有意改變。舊程式下失敗（回 1／null） |
| 3 | 「相鄰目標點到原點」「線段兩端、吐息」 | `turnCreatureFx(…, turn, c)`（turn ＝ 1／-1） | `turnCreatureFx(…, {x: 0, y: turn}, c)`；期望值一字不改 | 只換參數型別；期望值不變。舊程式下失敗（物件當數字 → NaN） |
| 4 | 姿勢鍵 | `fxTurn: 1` → 鍵 `…,fxturn1`；`quantize(…fxTurn: -1).fxTurn` `toBe(-1)` | `fxTurn: {x:0,y:1}` → `…,fxturn0:1`；量化後 `toEqual({x:0,y:-1})`；沒有轉向的鍵 `atk:@melee2@0.5000` 不變 | 同一欄的鍵可以變（規格「受影響的既有功能」）。舊程式下失敗（鍵是 `fxturn[object Object]`） |
| 5 | 實際片段（硫煙獸、熔爐母獸 × 南北） | `fxTurn: turn` | `fxTurn: {x: 0, y: turn}`；斷言一字不改 | 只換型別。舊程式下失敗（NaN） |
| 6 | 「頭目、沒有轉向時不另畫」 | 頭目 `fxTurn: 1` → `[]` | 沒有轉向（一般、頭目）→ `[]`（保留）；**頭目轉向** → `toEqual(turnCreatureFx(bossPlan("sl","swing",0.5).fx, {x:0,y:1}, 1))`、種類 `["slash"]` | 本段有意改變（D1）。舊程式下失敗（回 `[]`） |

沒有刪除東西向、同一欄一般異形的斷言；沒有放寬容差。

### 5.3 新斷言在舊程式下會失敗（換回 `17982c56` 的 6 個原始碼檔跑，跑完 `git checkout HEAD` 還原）

換回 `artTextures.ts`、`battle/skillLayer.ts`、`creatureFxTurn.ts`、`creaturePose.ts`、`inkCreature.ts`、`qBoss.ts`，跑 `cb4FxAnchor.test.ts`＋`cb3cFxTurn.test.ts`（JSON 報表）：**88 失敗、51 通過**。

| 組 | 舊程式下 | 說明 |
|---|---|---|
| cb4 錨點表（64） | 32 fail／32 pass | fail ＝ 4 種 × 4 斜向 × 2 朝向，全部斜向列。pass ＝ 東西向 16 列（「不變」斷言，本來就該過）＋正南北 16 列（舊的錨點函式同一欄已是格中心，頭目也一樣——頭目沒接上是在別處，見下兩列） |
| cb4 實際片段（26） | 26 fail | 斜向、頭目片段回空（`seen` 為 0）；一般異形正南北這 4 列是因為型別改成物件（舊式 NaN），同一欄的行為等價由「退化一致」證明 |
| cb4 退化一致（4） | 3 fail／1 pass | pass ＝「同一排回 null、沒有轉向時鍵與修改前相同」（不變斷言）；fail ＝ CB-3c 比對（型別）、斜向方向與鍵、剪切 |
| cb4 頭目身體貼圖（2） | 2 fail | 舊 `drawBossFrame` 有轉向時照畫特效 |
| cb4 命中對齊（1） | 1 pass | 「不變」斷言，本來就該過 |
| cb3c（42） | 25 fail／17 pass | 第 5.2 節的 #1、#2～#6 全部失敗；pass ＝ 東西向、同一欄的錨點列與「修改前的東西向錨點」 |

## 6. 東西向沒變的證明（截圖 8 以外）

- 純函式：錨點表東西向 32 列＝修改前；沒有轉向時 `drawCreature`／`drawBossFrame` 路徑與鍵沒改（`creaturePoseKey`、雜湊快照不變）。
- 畫面（只在 scratchpad 比，不入庫）：同一個無頭 Chrome、`skill-gallery.html#cb2b&sheet=1` 連拍存 PNG，舊程式（換回 6 檔、vite 熱更新）與新程式逐像素比：`ahRamE`（頭目東西向）差 158 px、`m2matriarchElite`（精英＋大型東西向）637 px、`m2boarSW`（同一欄）124 px；同一份新程式拍兩次的雜訊是 97／656／41 px（連拍照畫布時鐘取樣，格與格間有抖動），差異在雜訊範圍內，最大色差 15～41 也同級。

## 7. 截圖（`docs/art/shots/cb4/`，10 張、最大 140 KB）

開發頁 `http://127.0.0.1:5300/dev/skill-gallery.html?mute=1&sheet=1&rows=1&case=<案例>#cb2b`（正式 `playbackPlan → frameOps`），t＝出招片段開始後的毫秒。

| 檔 | 內容 | 給誰看 |
|---|---|---|
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\1-ah-ram-south.jpg` | 灰燼之心第 1 階段普攻衝撞打正南（`ahRamS`，333～667）：星爆在目標頭上、塵土在目標格 | D1 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\2-ah-ram-left-column-north.jpg` | 灰燼之心站最左欄、朝西打正北（`ahRamEdgeWN&margin=1`）：星爆在最左欄目標格、沒被裁（目標在頭目後一排，被身體擋住大半） | D1 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\3-lord-swing-south.jpg` | 碎晶之主普攻揮擊打正南（`lordSwingS`）：白弧落在目標格上方（高度照片段 −59.5 px，同東西向） | D1 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\4-lord-swing-right-column-north.jpg` | 碎晶之主站最右欄打正北（`lordSwingEdgeN&margin=1`）：白弧在目標那一欄、沒被裁 | D1 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\5-boar-southeast.jpg` | 硫煙獸挑獠牙打東南（`boarSE`，連拍） | D2 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\6-boar-west-northwest.jpg` | 硫煙獸朝西打西北（`boarWNW`，連拍） | D2 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\7-matriarch-elite-right-column-southwest.jpg` | 熔爐母獸精英＋大型站最右欄、打右下角的西南（`matriarchEdgeSW&margin=1`）：500 ms 星爆在目標身上 | D2、Q7 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\8-ah-ram-east.jpg` | 灰燼之心衝撞東西向（`ahRamE`，修改後）：星爆在施放者前 78.3 px，超出目標格邊約 6 px | Q2（給美術 PM 判斷） |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\9-boar-west-south.jpg` | 硫煙獸朝西打正南（`m2boarSW`），對照 `docs/art/shots/cb3c/1-boar-west-south.jpg`：同一欄沒退化 | 退化一致 |
| `F:\PythonProject\LLM-MMO-TRPG\docs\art\shots\cb4\10-boar-southeast-closeup.jpg` | 硫煙獸打東南特寫（`&cell=104`，333／417／500）：星爆在獠牙尖、兩格交界的角上 | 待決 1 |

## 8. 實機未看

- 實戰沒有直接拍：灰燼之心第 1 階段、碎晶之主貼身打正南北或斜向的場面要特定站位，改用開發頁（同正式播放路徑 `playbackPlan → frameOps → BattleRenderer`）畫出來。
- 減少動態（`&reduce=1`）沒拍；轉向特效貼圖在減少動態時照片段的最後一格（同 CB-3c，沒改這條路徑）。

## 9. 自己啟動的程序

| 程序 | PID | 結束 |
|---|---|---|
| vite（埠 5300） | sh 32448 → node 43956 | `taskkill /PID 32448 /T /F` |
| 無頭 Chrome（CDP 8148，`--mute-audio`，`--user-data-dir` 在 scratchpad `cb4\chrome-prof`） | 44392（含子程序 8 個） | `taskkill /PID 44392 /T /F` |
| `trpg serve --port 8149`（`TRPG_SAVE_DIR` 在 scratchpad） | bash 37332 → uv 16720 → trpg 22192 → python 17220／22124 | `taskkill /PID 37332 /T /F` |

結束後 `netstat` 查 5300、8148、8149 都沒有在聽，上列 PID 都不存在。沒有新增複雜度 noqa／eslint-disable。

## 10. 待 PM 決定

1. **硫煙獸挑獠牙的星爆在斜向時落在兩格交界的角上**：圓心相對目標格中心 (−26.2, −24.7) px（地面落點），比格邊多約 2 px，加上離地 31 px，畫面上在獠牙尖、目標頭的左上方（截圖 10）。原因是 Q1 (a) 照原樣張比例：這一招東西向時星爆就在兩格交界（離目標格中心 23.3 px）、正南北時 24.7 px（CB-3c 同樣用「圓碰得到格子」判定）。規格測試 2 寫「星爆中心 |Δ| ≤ 24」，這一招照 CB-3c 的「圓心 − 半徑 ≤ 24」判定（其餘三招照 ≤ 24）；要不要讓斜向的星爆再往目標推，請美術 PM 看截圖 5、6、10 判斷。
2. **碎晶之主的白弧高度**：轉向後高度照片段（−59.5 px，東西向同），正南北時看起來在目標頭上方、碎晶之主的下半身前（截圖 3、4）。照 Q4／D3 沒動；請美術 PM 判斷。
3. **Q2 灰燼之心東西向星爆 78.3 px**（截圖 8）：本段沒改，等美術 PM 判斷。
4. **`CREATURE_FX_BOX` 加寬到 240**：只影響轉向貼圖的透明邊（同一欄的畫面不變）；最遠的情況（精英＋大型的甲蟲、野豬）實際內容裡沒有，是保守做法。
5. **頭目站在目標的南邊打正北時，目標被頭目身體擋住**（截圖 2、4）：特效畫在效果圖層、蓋在目標之上，但頭目本體在前一排、比目標高大；這是既有的前後排順序，沒改。
6. Q5（身體的前推仍往東西）、Q6（隔一格的近戰錨點仍放相鄰格）照定稿不改，列追蹤。
