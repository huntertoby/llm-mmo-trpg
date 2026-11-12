# Phase OCL-1 計畫｜被遮擋剪影外框（大型前排擋住的單位畫陣營色輪廓）

> 開發 PM 規格助手 2026-11-12 起草（依據 main `6f2a8aeb`，含美術移植需求 `705958e0`）。
> 依據：美術 PM 移植需求 `docs/art/被遮擋剪影外框-移植需求.md`（全文，**和紀錄有出入時以需求為準**）；使用者看過樣張後原話「外框照做」（專案 PM 轉達）；需要時查紀錄 `docs/art/被遮擋剪影外框.md` 第 2.1、2.2、6、10.4 節。
> 樣張：第 3 版 `6cf02b57` 之後的 `docs/art/sample/occludeOutline.js`、`occlude-outline.html`（`?part=boss|pair|flash|team|true1x|field&w=1600|800|collide|fragment|measure&mute=1`）。
> 先讀 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第一～三節，第四節第 4、9、10、15、16、18、23、45 點。

## 0. 待確認（開發 PM 派工前定案；沒回覆就照「建議」做）

| # | 問題 | 建議 |
|---|---|---|
| Q1 | **外框貼圖的做法**（需求 4 第 1 點）：(a) 離屏 canvas；(b) Pixi 濾鏡（自寫 GLSL 膨脹／侵蝕，或加 `pixi-filters` 的 `OutlineFilter`） | **(a) 離屏 canvas，但膨脹／侵蝕改成對 alpha 陣列的純函式**（二值遮罩 alpha ≥ 128 → 精確歐氏距離轉換（Felzenszwalb 兩趟一維）→ 距離落在 (0, w] 的是色線、落在襯邊範圍的是黑邊，邊緣用 1 px 線性過渡做反鋸齒），結果用 `putImageData` 寫回畫布再 `Texture.from`。理由：①**確定性**：純整數／浮點陣列運算，不吃 GPU、驅動、瀏覽器合成的差異；樣張的 `dilate()` 是 0.5 px 步距反覆 `drawImage`，結果隨瀏覽器的次像素合成變（上手筆記第四節第 23 點的 ±1 雜訊就是這類），濾鏡更是每台 GPU 不同；②**測試性**：vitest 沒有 WebGL、也沒有真畫布，純函式能直接拿合成遮罩斷言線寬、只畫被擋段、位元組雜湊；濾鏡只能截圖驗；③**效能**：只在擺位改變時算一次、結果照鍵快取，每格只動 `tint`／`alpha`；濾鏡每一格都在 GPU 重跑（除非再 `cacheAsTexture`），而且濾鏡區域會讓整個 `silhouettes` 容器多一次離屏繪製；④**和現有程式一致**：白閃剪影就是畫布像素運算（`render/silhouetteFlash.ts:13-22` 的 `whiteCanvas` → `creaturePose.ts:206` `whiteSilhouette`），所有身體貼圖也是畫布畫好再進 `ArtTextures` 快取；專案目前只有一個 `ColorMatrixFilter`（`unitSprite.ts:498`，灰階），沒有 `pixi-filters` 相依。距離轉換在 200×200 的貼圖約 4 萬像素，遠低於 1 ms 等級。和樣張的一致性用截圖驗收第 3 項的真 1 倍特寫對照 |
| Q2 | **縮放級距與快取鍵**（需求 4 第 2 點） | **不另切縮放級距，直接以「貼圖上的線寬」量化**：外框在被擋者身體貼圖的同一個解析度上算（身體貼圖本來就照 `figureResolution` 以 0.5 為級距跟著螢幕縮放，`artTextures.ts:35-38`、`111-122`，鍵含 `res`）。線寬（貼圖 px）＝ 1.5 × 貼圖 px／模型 px ÷ 地圖縮放 `scale`（CSS px／模型 px，`BattleRenderer.ts:155-159`），量化到 **0.25 貼圖 px**；襯邊同理（0.75 → 量化 0.25）。快取鍵＝`ol|<身體貼圖鍵>|w:<量化線寬>|i:<量化襯邊>`（身體貼圖鍵已含 `res`，所以等於「身體鍵 × 縮放級距」）。誤差上限：量化半格 0.125 貼圖 px，800 寬（縮放約 0.53，貼圖 1.5 res）約 0.04 CSS px、1600 寬（約 1.31）約 0.11 CSS px，都在 1.5 的 8% 內。**重算時機**：①`setScale`／`applySize`（縮放或裝置像素比改變）只重建外框貼圖、**不重算比例與遲滯**（比例在模型像素算，和縮放無關）；②擺位改變（需求 3 第 1 點）重算比例、遲滯與裁切。舊鍵照 `ArtTextures` 現行的 `beginFrame`／`endFrame` 回收 |
| Q3 | 「隱匿中（`concealed`）或資訊被隱藏的敵人」：**友方**隱匿中要不要畫 | **都不畫**（隱匿狀態一律不畫，不分陣營）：和身體半透明的判斷同一條（`unitSprite.ts:506`：`hiddenInfo === true` 或 `statusIds` 含 `concealed`），一條規則好測；友方隱匿少見，報告列出、要改另議 |
| Q4 | 被擋者**自己的片段**（受擊後仰、擊退、出招前推）中，外框用片段開始前的貼圖（需求 3 第 1 點），但身體會位移 | **外框 Sprite 每格跟著身體節點的平移**（`bodyNodes` 的 `position` 差值，含 `knockOffset`、`creatureOffsetPx`），**不跟姿勢換貼圖**；輪廓和後仰的身體會差幾 px，受擊閃白（截圖 2）照這樣拍給美術 PM 判斷。旋轉（空翻 `spinBody`、倒下片段）時外框藏起來 |
| Q5 | 走路、擊退位移（整個單位換格）時外框怎麼辦 | **移動的那個人自己的外框藏起來**，比照舊剪影（`motionLayer.ts:50-51`、`326-327`），停下重畫時再算；**別人**（例如頭目走開後，原本被擋的人）的外框沿用移動前的結果直到移動結束 |
| Q6 | 需求的峰值表沒有列到的白閃：格擋 0.35（`reactClips.ts:180` `block`）、減少動態的白閃一律 0.85（`vfxLayer.ts:272`，異形也用 0.85）、沒有骨架單位的疊層白閃 `× strength`（`reactEffects.ts:257`）、頭目倒下 0.7（`qBoss.ts:656`） | **k ＝ 當下白閃 ÷ 那個效果自己的峰值**，峰值由各白閃的呼叫點直接傳給外框（不是在外框層查表猜）：格擋 0.35、減少動態 0.85、疊層 `0.85 × strength`、頭目倒下不畫（倒下的人不畫外框）。需求表內的四個數字照表，測試鎖住「k 不寫死 0.85」 |
| Q7 | 驗收第 1 項「目標友方一張、敵方一張」：敵方頭目往正北打的目標是友方；**敵方被擋者**的情境怎麼做 | 開發頁加一個案例：頭目往正北打友方，**同一排另一側**（頭目身後）再放一個敵方小兵也被擋（或第三方頭目打敵方）。報告寫明是哪一種；正式對局到不了的標「實機未看」 |
| Q8 | 隱匿中或倒下的**大型前排**本身算不算前排 | **倒下不算**（倒地圖示面積本來就 < 4000，順手在過濾時排除），**隱匿中照算**（遮罩用貼圖 alpha，不乘 Sprite 的半透明；和樣張相同） |
| Q9 | 切段 | **切兩段、依序做、各一個實作者**（同一批檔案不能平行）：OCL-1a 靜態（算法、貼圖、圖層、6F-22 舊剪影規則、過濾、遲滯、縮放重建、開發頁、效能量測）；OCL-1b 動態（片段中沿用與片段結束重算、跟著身體平移、受擊閃白 k、走路藏外框）。1a 交件時戰場已能看到靜態外框，1b 只動播放 |

## PM 決定（已定，照做）

| # | 決定 | 出處 |
|---|---|---|
| D1 | 做，現在排 | 使用者 2026-11-12「做，現在排」（需求定案依據） |
| D2 | 只在前排是**大型單位**時算遮擋；**用面積判斷**（身體 alpha ≥ 0.5、模型 px² ≥ 4000），不用「頭目或 huge」，兩種不混用 | 使用者「可以」；需求第 2 節 |
| D3 | 外框照樣張第 3 版做：55% 開始畫、< 45% 拿掉；色線 1.5 CSS px（往內一圈）、兩側各 0.75 px `#16121a`；只畫被擋段；整層 × 0.8；`RING[team].stroke`（召喚物 `RING.summon.stroke`），不新增色票 | 使用者「外框照做」；需求第 2 節 |
| D4 | 受擊閃白：色線 mix(陣營色, 白, k)、整層透明度 0.8 + 0.2k，k ＝ 當下白閃 ÷ 片段峰值 | 需求第 2 節、3 第 4 點 |
| D5 | 6F-22 舊剪影：同一單位這一格有新外框時不畫；沒有新外框時照畫，**不能先拿掉**；地形算進遮擋是之後另一段 | 需求 3 第 5 點 |
| D6 | 倒下、隱匿中、資訊被隱藏的不畫，而且**在算比例之前**過濾 | 需求 3 第 6 點 |
| D7 | 被擋者的 HP 條、狀態列、輪到行動的黃虛線圈被頭目蓋住：**不在範圍** | 需求 1.2；使用者還沒表態 |
| D8 | 後端、`content/`、API 不動；不需要玩法 PM 決定 | 需求第 4 節末 |

## 1. 現況查證（規格助手只讀，行號以 `6f2a8aeb` 為準）

### A. 6F-22 舊剪影

1. 判斷：`client/src/render/battle/unitLayer.ts:98` —— `occluded(model, u)`（`battle/elevation.ts:145`：南鄰格比自己高）或 `roofCovers(model.scenery, u)`（`render/sceneryModel.ts:98`）才畫；只看地形，不看單位。
2. 畫法：`unitLayer.ts:99-103` 取 `RING.summon`／`RING[u.team]` 的 `stroke`，呼叫 `render/heightArt.ts:51-58` 的 `silhouette()`（固定人形橢圓＋頭圓 `heightShapes.ts:71` `silhouetteLoops`、2px 虛線 3/2、透明度 0.9），加進 `silhouettes`、記在 `silhouetteOf`。**倒下的人也會畫**（`drawUnit` 沒有過濾 `downed`），本段不改這個舊行為。
3. 移動時藏起來：`render/battle/motionLayer.ts:50-51`（`moveOne`）、`326-327`（`animateWalk`）把 `silhouetteOf` 的剪影 `visible = false`，重畫時重判斷。
4. 被擋時 HUD 改畫在 `hudTop`：`unitLayer.ts:68-70`、`88`（`RowStack.attachHud`，`render/rowLayers.ts:146`）；**本段不動**（D7）。

### B. `silhouettes` 容器與圖層順序

1. 宣告：`render/battle/rendererBase.ts:44-45`（`silhouettes`、`silhouetteOf`），`hudTop` 在 `:47`。
2. 順序：`render/BattleRenderer.ts:78`：`rows.root → marks → attackTop → arrowTop → ambient.root → silhouettes → hudTop → hover → groundMask → 特效層（EFFECT_LAYER_ORDER）`。外框放 `silhouettes`＝在所有排（含單位與排內 HUD）之上、`hudTop`／`hover`／特效之下，和需求一致。
3. 每次 `draw(model)` 清空：`BattleRenderer.ts:186-187`（`clearLayer(this.silhouettes)`、`silhouetteOf.clear()`）。**遲滯的「上一次有畫」不能放在這裡清**（見交付 3）。

### C. 單位排序與前後排

1. 由北到南一排一個 `RowLayer`（`render/rowLayers.ts:83-97` `RowStack.row(y)`），南邊的排後畫。
2. 同一排內照 `model.units` 的順序 `addChild`；**頭目（`ringScale(u) > 1`）一律 `addChildAt(sprite, 0)` 排在同一排最前面先畫**（`unitLayer.ts:85`，QK-9）。樣張的 `order()`（排、頭目先、欄）就是照這個。所以「前排」＝**畫的順序在被擋者之後**的單位：南邊 1～3 排的全部，加上同一排排在它後面的（同一排的頭目一定在最前面，不會是前排）。
3. 移動途中單位會換排（`motionLayer.ts` 的 `rowDuringMove`），停下重畫回到終點那一排。

### D. 身體貼圖、模型像素與縮放

1. 身體貼圖：`render/unitSprite.ts:584` `bodyTexture`（紙娃娃 `art.figure`、異形 `art.creature`／`creatureBody`、形態與召喚物回 `null` 用 `dollNode` 的整張圖）。**預設貼圖含地上影子**（`renderFigureCanvas(…, ground = true)`，`paperdoll.ts:111`），遮罩一律用不含影子的版本：人形 `figureBare`（`artTextures.ts:242`）、異形 `creatureBody`（`:267`）、召喚物與形態 `ground = false`（白閃用的 `formFlash`、`summonFlash`，`artTextures.ts:320-329`）。
2. 貼圖解析度：`artTextures.ts:111-122` `setScreenScale`／`figureRes`／`creatureRes`，`figureResolution`（`:35-38`）＝ ceil 到 0.5、夾在 1.5～6；鍵開頭都帶 `res`（`:237`、`:259`、`:270`）。頭目另乘 `HUGE_FIELD_SCALE`（1.6），異形戰場縮放 `creatureFieldScale`（`unitSprite.ts:329`）。紙娃娃 1 虛擬 px ＝ `dollPx(u)` 模型 px（`unitSprite.ts:672`，含精英與外觀大小）。
3. 地圖縮放：`BattleRenderer.ts:155-159` `setScale(scale)`（`fitScale`，`battle/stageLayout.ts:27`，夾在 `MIN_SCALE` 0.5～`MAX_SCALE` 2）→ `applySize`（`:162-180`）：畫布解析度＝`devicePixelRatio × scale`、`art.setScreenScale(該值)`、`scaleMarks()`。
4. `minMark`（`render/minMark.ts:48` `minMarkScale`）是 HUD 標記「縮小時反向放大到下限」的機制，**外框不套用**：線寬固定 1.5 CSS px，由 Q2 的線寬換算處理。

### E. 受擊白閃

| 呼叫點 | 對象 | 白閃 | 峰值 |
|---|---|---|---|
| `render/battle/vfxLayer.ts:80` `creatureHit` → `creaturePose.ts:99` | 異形（含頭目走 `qBoss.ts:656` `bossPlan`） | 前 20% 固定 0.9 | 0.9 |
| `vfxLayer.ts:121` `dollHit` → `motionClips.ts:291` `humanHit` | 有骨架的人形 | 0.85 → 0 | 0.85 |
| `vfxLayer.ts:168` `overlayHit`（`humanHit(t).flash`）、`reactEffects.ts:242-257` `overlayEffect`（`× strength`） | 形態、召喚物、倒地的人（`overlayFlashKind`，`unitSprite.ts:680`） | 疊白色剪影（`silhouetteFlash.ts:29` `overlayFlash`） | 0.85（× strength） |
| `reactEffects.ts:45` `reactEffects` → `reactClips.ts:124` `hit(heavy)` | 人形重擊 | 0.95 → 0 | 0.95 |
| `reactClips.ts` `creatureReact`（重擊 × 1.1） | 異形重擊 | 0.99 | 0.99 |
| `reactClips.ts:180` `block` | 格擋 | 0.35 → 0 | 0.35（需求表沒有，Q6） |
| `vfxLayer.ts:255-272` `steadyFlashAt` | 減少動態時所有種類 | 0.85 × (1 − t) | 0.85（需求表沒有，Q6） |

白閃是「換一張帶白閃的身體貼圖」（人形 `|w:`、異形 `creature.flash`）或「疊一張白色剪影」，**外框不能靠換貼圖做閃白**（需求 3 第 4 點：tint／alpha）。

### F. 隱匿與倒下

- `UnitDraw.downed`；`hiddenInfo`（`battle/drawModel.ts:105-108`、`:293`）；`statusIds` 含 `CONCEALED`（`render/statusIcon.ts:869`）。現行身體半透明的判斷：`unitSprite.ts:506`（`CONCEALED_ALPHA` 0.55，`statusIcon.ts:867`）。

## 目標

- 戰場上，被**大型前排**（身體面積 ≥ 4000 模型 px²）擋住 ≥ 55% 的單位，在被擋住的那一段畫一條陣營色輪廓（降到 < 45% 才拿掉）；受擊時照片段峰值閃白。
- 結果和樣張第 3 版一致：線寬 1.5 CSS px（800 寬與 1600 寬都是）、兩側 0.75 px 黑邊、只畫被擋段、整層 × 0.8。
- 同一單位有新外框時不畫 6F-22 舊剪影；其餘情況舊剪影照舊。

## 範圍外

- 地形（崖面、屋頂）算進遮擋、拿掉舊剪影（需求 3 第 5 點：之後另一段）。
- 被擋者的 HP 條、狀態列、輪到行動的黃虛線圈（D7）。
- 舊剪影本身的畫法、倒下的人也畫舊剪影的既有行為（第 1 節 A 第 2 點）。
- 單位、環、HUD、特效的畫法與排序；大世界（`client/src/world/`）；後端、`content/`、API。

## 受影響的既有功能

| 位置 | 改不改 | 說明 |
|---|---|---|
| 新檔 `render/occludeOutline.ts` | 新增（1a） | 純函式：alpha 遮罩（≥ 128）、面積、`coverRatio`、遲滯 `outlineWanted(ratio, was)`、距離轉換與色帶 `outlineBand`、裁切合成、`flashTint(color, k)`、線寬量化 `outlineWidthTex`。不 import Pixi 以外的繪製器狀態 |
| 新檔 `render/battle/outlineLayer.ts`（或併進 `unitLayer.ts`，看行數） | 新增（1a，1b 加播放） | 擺位改變時算前排、比例、遲滯、裁切；建外框 Sprite 放 `silhouettes`；記 `outlineOf`、`outlineWas` |
| `render/battle/unitLayer.ts`（`drawUnit:78-104`） | 改（1a） | 舊剪影改成「畫完全部單位、算完外框之後」才決定畫不畫（現在是每畫一個單位就決定，那時還不知道有沒有新外框）；判斷式抽成可測的函式 |
| `render/battle/rendererBase.ts` | 改（1a） | 加 `outlineOf`、`outlineWas`（遲滯狀態，**不在 `draw` 清**；單位消失時刪） |
| `render/BattleRenderer.ts`（`draw`、`applySize`） | 改（1a） | `draw` 畫完單位後呼叫外框計算；`applySize` 縮放改變時只重建外框貼圖（Q2） |
| `render/artTextures.ts` | 改（1a） | 加外框貼圖與遮罩的快取入口（`ol|…`、模型像素遮罩 `om|…`），沿用現行 `canvas()`／`get()` 與 `holdFor`；**既有鍵逐字不變** |
| `render/battle/motionLayer.ts`、`skillLayer.ts`、`vfxLayer.ts`、`reactEffects.ts` | 改（1b） | 片段開始前凍結、結束後重算；移動者外框藏起來（Q5）；白閃呼叫點把 (flash, peak) 傳給外框（Q6） |
| `render/heightArt.ts`、`heightShapes.ts`、`elevation.ts`、`sceneryModel.ts` | 不改 | 舊剪影畫法與地形判斷 |
| `render/silhouetteFlash.ts`、身體貼圖的畫法 | 不改 | 只讀它們的畫布 |
| 雜湊快照 `render/creaturePose.test.ts`、`render/inkDollSnapshot.test.ts`、`render/__snapshots__/`、`fixtures/qi3bStatusBaseline.json`、`qi2dBaseline.json` | **不應變** | 本段不碰身體與圖示畫法；變了就停下查，**不得整批重產** |
| `ui/occludedHud.test.ts`、`ui/hid1bLayers.test.ts`、`render/silhouetteFlash.test.ts`、`render/heightShapes.test.ts`、`battle/elevation.test.ts` | 不應變 | 舊剪影與 HUD 規則照舊 |
| 新開發頁 `client/dev/ocl-gallery.html`＋`dev/oclGallery.ts`；`dev/skillGallery.ts` | 加（1a 開發頁；1b 加案例） | 見交付 5 |

## 交付項目

### OCL-1a（靜態）

1. **遮罩與面積**（`occludeOutline.ts`＋`artTextures.ts`）：每個單位在**模型像素**（1 格 48、原點對齊整數模型像素，`floor`）另畫一份不含影子、環、HUD、特效的身體遮罩（第 1 節 D 第 1 點的 bare 版本，解析度設成 1 畫布 px ＝ 1 模型 px），alpha ≥ 128 才算。遮罩與面積**照貼圖的鍵快取，同一個鍵只取一次 `getImageData`**。大型前排＝面積 ≥ 4000（D2）。
2. **前排與比例**：被擋者先過濾（倒下、`hiddenInfo`、`concealed`，D6、Q3），再找前排：畫的順序在它之後（第 1 節 C）、在它南邊 0～3 排、模型像素外接矩形相交、面積 ≥ 4000、沒有倒下（Q8）。比例＝|M ∩ O| ÷ |M|，O＝大型前排遮罩聯集（模型像素）。待機一律用第 0 格的姿勢算（`creatureRestPose`、`PERCH_REST` 等站好的貼圖）。
3. **遲滯**：`outlineWanted(ratio, was)`：`was` 為假時 ≥ 0.55 才畫；`was` 為真時 < 0.45 才拿掉。`was` 存在繪製器（`outlineWas: Map<unitId, boolean>`），跨 `draw(model)` 保留，單位不在 `model.units` 時刪。
4. **外框貼圖**（Q1、Q2）：在被擋者身體貼圖（bare，畫面解析度）上算色帶：色線＝輪廓往內寬 w（貼圖 px）、黑邊＝色線兩側各 0.75 CSS px（換算成貼圖 px）；色線畫**白色**、黑邊畫 `#16121a`，先疊成一層不透明的。**裁切**：畫面解析度的前排遮罩照畫的順序疊——大型前排 `source-over`、畫在它之後的小兵 `destination-out`（需求 3 第 3 點），色線 ∩ O、黑邊 ∩ dilate(O, 襯邊)（同樣張）。Sprite 放 `silhouettes`，位置、錨點、鏡射對齊身體節點；`tint`＝`RING[team].stroke`（召喚物 `RING.summon.stroke`）、`alpha`＝0.8。
5. **開發頁** `client/dev/ocl-gallery.html`（`dev/oclGallery.ts`，用真的 `BattleRenderer.draw`、手寫 `DrawModel`，比照 `practiceGallery.ts`／`scaleGallery.ts`）：`?scene=boss|pairs|collide|concealed|team|field`、`&w=1600|800`（照 `fitScale` 算縮放）、`&ocl=0|1`（關／開外框，效能對照用；**只在開發頁**）、`&measure=1`（把每個單位的面積、比例、畫不畫寫進 `body.dataset.measure` 與頁上表格，對照樣張 `?part=measure`）、`&bare=1`（截圖用）。情境照樣張：`boss`＝灰燼之心／碎晶之主在目標南邊（友、敵各一）、`pairs`＝一般單位互擋 8 對、`collide`＝第 2 列矮異形在高台的人後面＋第 4 列頭目＋小兵、`concealed`＝隱匿敵人在頭目後面、`team`＝友／敵／第三方／召喚物。畫好後 `body.dataset.ready="1"`。
6. **6F-22 舊剪影規則**：單位這一格有新外框 → 不畫舊剪影（也不記 `silhouetteOf`）；否則照現行條件畫。判斷抽成 `legacySilhouetteWanted(terrainOccluded, hasOutline)`。
7. **縮放重建**：`applySize` 時若量化線寬改變，只重建外框貼圖（比例、遲滯不重算）。
8. **效能量測**（見「驗收」第 5 點）與報告 `docs/phases/PhaseOCL-1a報告.md`；順手更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節加兩個新檔、第二節加「被遮擋外框」一小段：什麼時候算、快取鍵、舊剪影規則）。

### OCL-1b（動態）

1. **什麼時候重算**（需求 3 第 1 點）：`draw(model)`、移動結束、換姿勢、轉向時算；走路、擊退、出招、受擊片段播放中**沿用片段開始前的結果**，片段結束再算一次。待機換貼圖不重算。
2. **跟著身體**（Q4）：外框 Sprite 每格同步身體節點的平移；旋轉中藏起來。
3. **移動**（Q5）：移動的人自己的外框藏起來（和舊剪影同一處，`motionLayer.ts:50`、`326`），停下重算；別人的沿用。
4. **受擊閃白**（D4、Q6）：每個白閃呼叫點（第 1 節 E 表）把 `(unitId, flash, peak)` 交給外框層；外框層 `k = clamp(flash / peak)`，`tint = mix(陣營色, 白, k)`、`alpha = 0.8 + 0.2k`，**不換外框貼圖**、白閃結束回 k＝0。黑邊因為 tint 相乘不受影響。
5. **開發頁案例**（`skill-gallery.html#cb2b`）：沿用 CB-4 的 `ahRamEdgeWN`、`lordSwingEdgeN`，再加 `oclAhN`（灰燼之心第 1 階段在目標正南往北打，目標友方）、`oclAhNEnemy`（Q7）、`oclLordN`、`oclBoarHit`（異形被頭目擋著受擊）、`oclHumanHit`（人形被擋著受擊），案例名寫進報告。
6. 報告 `docs/phases/PhaseOCL-1b報告.md`；更新上手筆記（第二節補「片段中沿用、白閃 k」與第四節一條「外框不能靠換貼圖閃白」）。

## 行為一致測試（vitest）

新檔 `render/ocl1Outline.test.ts`（1a）、`render/ocl1Playback.test.ts`（1b）。遮罩一律用合成的 `Uint8ClampedArray`／假畫布（`test/fakeCanvas.ts`），不靠真畫布。

1. **遮罩與面積**：alpha 127／128 邊界；同一個鍵取兩次只呼叫一次 `getImageData`（假畫布計數）。
2. **大型前排**：面積 3999 不算、4000 算；倒下的大型前排不算（Q8）。
3. **比例**：合成方塊遮罩已知交集（例 60×60 被擋 55% 的位置）→ 比例逐筆相等；原點小數位置時照 `floor` 對齊，平移整數格比例不變。
4. **遲滯**（驗收第 8 項）：表格測試 `outlineWanted`：(0.549, 假)→假、(0.55, 假)→真、(0.45, 真)→真、(0.449, 真)→假；序列 0.50→0.56→0.50→0.46→0.44→0.50 ＝ 假、真、真、真、假、假（**45～55% 之間進出不閃爍**）；`was` 跨 `draw(model)` 保留（呼叫兩次 `draw`）。
5. **過濾在算比例之前**：倒下、`hiddenInfo`、`concealed` 的被擋者，遮罩與比例函式**都沒被呼叫**（spy），而且沒有外框 Sprite。
6. **色帶**：合成圓盤遮罩 → 色線寬（沿法線量）＝ 指定的貼圖 px ± 0.5；黑邊在色線兩側各 ≈ 襯邊寬；外側 1 px 以外全透明；**只畫被擋段**：O 只蓋右半時左半色線像素 0；大型前排之後的小兵挖掉後，小兵範圍內沒有色線。
7. **確定性**：同一輸入算兩次，外框位元組的 SHA-256 相同。
8. **線寬換算**（Q2）：`outlineWidthTex` 在 800 寬、1600 寬（各給實際縮放、DPR 1 與 2、貼圖 res）換回 CSS px 都在 1.5 ± 0.12；縮放微調（± 0.001）時鍵不變。
9. **舊剪影規則**：`legacySilhouetteWanted` 四種組合；繪製器層：同一單位有外框時 `silhouetteOf` 沒有它、沒有外框時照舊有。
10. **陣營色**：友／敵／第三方／召喚物的 `tint` 分別是 `RING.*.stroke`。
11. （1b）**閃白 k**：每一列峰值（0.85、0.95、0.9、0.99、0.35、減少動態 0.85）在白閃＝峰值時 k＝1、tint＝白、alpha＝1；白閃 0 時回原色 0.8；**沒有任何一處用 0.85 當異形或頭目的分母**。
12. （1b）**片段中沿用**：片段開始後改變前排位置（模擬頭目前推），外框比例與貼圖不變；片段結束後重算一次。移動者外框 `visible = false`。
13. 每項新斷言盡量證明在**舊程式下會失敗**（第 9 項必做：暫時換回 `6f2a8aeb` 的 `unitLayer.ts` 跑一次，報告寫失敗數，跑完還原）。

## 驗收與截圖分配

驗收條件（每段各自）：
1. 上節測試全過；開發中指令（下節）全過；雜湊快照與第「受影響」表列為「不應變」的測試照舊通過。
2. 交件前各跑一次、結束碼分開記：`corepack pnpm -C client test`、`corepack pnpm -C client build`、`corepack pnpm -C client typecheck`，全部 0。
3. `git diff --stat 6f2a8aeb -- src/trpg content client/src/api` 為空。
4. 截圖齊全（下表），報告附需求第 5 節的 (a)(b)(c)：(a) 大型前排面積實測（兩位頭目＋至少 4 個一般單位，對照紀錄 10.2：灰燼之心 8928、碎晶之主 8220、一般 506～1963；差超過 ±3% 要寫原因）；(b) CB-4 情境的比例實測，對照樣張 `?part=measure`；(c) 舊剪影去留規則怎麼實作。
5. **效能**（1a 量、1b 再量一次播放中）：開發頁 `ocl-gallery.html?scene=field&w=1600`（12 單位＋頭目）與 `&w=800`，同一場景 `&ocl=0` 與 `&ocl=1` 各量：①`draw(model)` 耗時（`performance.now()` 包住，暖機 5 次後取 50 次的中位數與 p95）；②其中外框計算本身的耗時（目標中位數 < 1 ms，需求 3 第 8 點）；③待機 10 秒的影格時間（`requestAnimationFrame` 間隔的中位數與 p95，開關外框差距應在量測雜訊內）；④`window.__texStats()` 的張數與位元組開關對照；⑤`getImageData` 呼叫次數＝不同遮罩鍵數。1b 另量 CB-4 案例播放中每格外框層的耗時（只動 tint／alpha）。無頭 Chrome 要開 GPU 或固定 `--disable-gpu` 二擇一並寫明。

截圖（`docs/art/shots/ocl1/`，**每段 ≤ 10 張**、jpg 品質 80、單張 ≤ 300 KB；連拍用合圖；真 1 倍與最近鄰特寫用 PNG ≤ 300 KB；開發頁一律 `?mute=1`、無頭 Chrome `--mute-audio`；開發頁畫的標「開發頁」，正式對局到不了的在報告「實機未看」逐項列出）：

| 段 | # | 內容 | 對到需求第 5 節 | 對照 |
|---|---|---|---|---|
| 1a | 1 | `scene=boss`：灰燼之心擋友方、擋敵方、碎晶之主擋人（合圖一張） | 1 | `shots/occlude/1-boss.jpg` |
| 1a | 2 | `scene=field&w=1600` 整張 | 3 | `shots/occlude/7-field-1600.jpg` |
| 1a | 3 | `scene=field&w=800` 整張 | 3 | `shots/occlude/8-field-800.jpg` |
| 1a | 4 | 1600 寬一格最近鄰放大特寫（PNG） | 3 | `closeup/occlude/6-true1x-1600.png` |
| 1a | 5 | 800 寬一格最近鄰放大特寫（PNG） | 3 | `closeup/occlude/6-true1x-800.png` |
| 1a | 6 | `scene=pairs`（一般單位互擋全部不畫）＋`collide` 第 2 列（矮異形在高台的人後面：只有舊剪影） | 4、6（沒外框時舊剪影照畫） | `2-pairs.jpg`、`9-collide.jpg` 第 2 列 |
| 1a | 7 | `scene=collide` 第 4 列：頭目＋小兵一起擋，外框只在頭目身上 | 5 | `9-collide.jpg` 第 4 列 |
| 1a | 8 | 被頭目擋住、腳下又是高台（6F-22 也成立）的單位：只有新外框、沒有舊剪影 | 6 | `9-collide.jpg` 第 2 列 |
| 1a | 9 | `scene=concealed`：隱匿敵人在頭目後面不畫外框（旁邊放一個沒隱匿的對照） | 7 | 無樣張 |
| 1a | — | 遲滯：不拍，用測試第 4 項鎖住，報告寫測法 | 8 | — |
| 1b | 1 | `oclAhN` 播放中（出招前、命中、收勢連拍合圖）：外框沿用、片段結束重算 | 1 | `1-boss.jpg` |
| 1b | 2 | `oclHumanHit` 受擊閃白連拍 0、30、90、300 ms（合圖） | 2 | `shots/occlude/3-flash.jpg` |
| 1b | 3 | `oclBoarHit` 受擊閃白連拍 0、30、90、300 ms（合圖） | 2 | 同上 |
| 1b | 4 | `oclAhNEnemy`（Q7）敵方被擋者 | 1 | `1-boss.jpg` |
| 1b | 5 | （選）CB-4 的 `ahRamEdgeWN`、`lordSwingEdgeN` 重拍，對照 `shots/cb4/2`、`4` 的同一刻 | 1 | `shots/cb4/2-…`、`4-…` |

## 開發中跑的測試

- 只跑直接相關的檔：`corepack pnpm -C client exec vitest run src/render/ocl1Outline.test.ts`（1b 加 `src/render/ocl1Playback.test.ts`）；動到 `unitLayer.ts`／`BattleRenderer.ts` 加 `src/ui/occludedHud.test.ts src/ui/hid1bLayers.test.ts src/render/silhouetteFlash.test.ts`；動到 `artTextures.ts` 加 `src/render/creaturePose.test.ts src/render/inkDollSnapshot.test.ts`；動到白閃呼叫點（1b）加 `src/render/reactClips.test.ts src/render/bodyAnim.test.ts`。
- 整包 `pnpm test`／`build`／`typecheck` 只在交件前各一次（驗收 2）。不跑 `scripts/check.py`、不跑模擬、不跑 pytest（沒動後端）。
- 快照不得整批重產（`-u` 禁用）；變了照「受影響」表處理。

## 工作環境與規矩

- Windows：前端 `corepack pnpm -C client …`；新 worktree 先 `corepack pnpm -C client install --frozen-lockfile --offline`。
- 預覽埠：vite **5320～5324**、CDP **8163～8165**；**不用 8000、8001**。本段不需要 `trpg serve`（開發頁不打 API）。網址一律加 `?mute=1`，無頭 Chrome 加 `--mute-audio`；腳本、`--user-data-dir` 放 scratchpad 自己的子資料夾。
- 等待一律靠完成通知，不寫 until／while 輪詢迴圈；交件前用自己記下的 PID 關掉 vite 與無頭 Chrome，不結束不是自己啟動的程序。
- 子 agent 一律 Opus 5.5（`model: "opus"`），並往下傳同樣規矩。
- 不要 push；依交付分 commit，結尾帶 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 報告格式

做了什麼（交付表＋commit）、驗收逐條（測試名或指令輸出為證、三個結束碼分開記）、現況確認（對照本計畫第 1 節，有出入就寫）、Q1 Q2 的實作說明（距離轉換、量化鍵、和樣張真 1 倍的像素差）、需求第 5 節 (a)(b)(c)、效能量測表（開／關外框對照、量法、GPU 設定）、快照與既有測試變動逐條說明（含舊程式下的失敗數）、截圖清單（完整路徑）、實機未看、自己啟動的程序與 PID、「待 PM 決定」最多 10 點。
