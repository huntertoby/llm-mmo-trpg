# Phase OCL-1a 報告｜被遮擋剪影外框（靜態）

> 實作 agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhaseOCL-1計畫.md`（Q1～Q9 照建議、D1～D8 照做）、`docs/art/被遮擋剪影外框-移植需求.md`。只做 1a（靜態），1b（播放）未動。
> 基準：worktree 先 `git merge --ff-only main`，`e7edf1be` 是祖先（已確認）。後端、`content/`、API 沒動。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 1～4、6、7 | `render/occludeOutline.ts`（純函式）、`render/battle/outlineLayer.ts`（`planOcclusion`、`outlineTexture`）、`render/battle/occlusionLayer.ts`（繪製器層 `OcclusionLayer`，插在 `UnitLayer` 與 `FeedbackLayer` 之間）、`unitSprite.bareBodyOf`、`ArtTextures.alphaMask`／`outline`、`rendererBase` 的 `outlineOf`／`outlineWas`、`unitLayer` 舊剪影改成畫完全部單位後才決定、`BattleRenderer.draw` 呼叫 `drawOcclusion`、`setScale` 呼叫 `rebuildOutlines`；測試 `render/ocl1Outline.test.ts` | `58569241` |
| 5、1（修正） | 開發頁 `client/dev/ocl-gallery.html`＋`src/dev/oclGallery.ts`；模型像素遮罩改成規格寫的「1 畫布 px ＝ 1 模型 px」 | `066ce879` |
| 8（效能） | 模型像素遮罩跨 `draw` 快取（照小數位置）、裁切遮罩照各層相對位置快取、畫布不到 4000 的不畫遮罩；第 4 列撞圖改成格子上做得到的擺位 | `6581ca17` |
| 8（報告、筆記、截圖） | 本報告、`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節新檔、第二節「被遮擋外框」、開發入口、第五節測試）、`docs/art/shots/ocl1/` 10 張、開發頁 `bare` 排版 | 最後一個 commit |

## 2. 驗收逐條

1. **測試**：`render/ocl1Outline.test.ts` 37 項全過（第 1～10、13 項；第 11、12 項是 1b）。相關既有測試 `ui/occludedHud`、`ui/hid1bLayers`、`render/silhouetteFlash`、`render/creaturePose`、`render/inkDollSnapshot`、`test/importCycles`、`render/heightShapes`、`battle/elevation` 8 檔 72 項全過。
2. **三個結束碼**（交件前各跑一次）：`corepack pnpm -C client typecheck` → **0**；`corepack pnpm -C client test` → **0**（305 檔、3912 項全過）；`corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）。
3. `git diff --stat e7edf1be -- src/trpg content client/src/api client/src/render/__snapshots__ client/src/render/fixtures` 為空。註：規格寫的 `6f2a8aeb` 到 `e7edf1be` 之間 main 本來就改過 `client/src/api`、`content/`、`src/trpg`、`qi3bStatusBaseline.json`（BAL-21b 等），不是本段。
4. 截圖齊全（第 8 節），(a)(b)(c) 在第 5 節。
5. 效能在第 6 節。

## 3. 現況確認（對照計畫第 1 節）

- A～F 都和計畫描述一致。補充：`drawModel` 的 `units` 先排倒下的、再照 y 排；畫的順序我直接讀每一排 `units` 容器的子節點（頭目 `addChildAt(0)` 之後的真實順序），不另外重算。
- 倒地狀態（`prone`）的人身體節點有旋轉（`layDown`）：外框的擺位不含旋轉，所以這種人**不當被擋者**（`skip: "tilted"`，保守做法，見待決 4）。

## 4. Q1、Q2 的實作

- **Q1（距離轉換）**：`sqDistTo` 是 Felzenszwalb & Huttenlocher 兩趟一維的精確歐氏距離平方。帶號距離 s＝內部「到最近外部像素中心的距離 − 0.5」、外部取負；色線覆蓋率 clamp(w + 0.5 − s)、黑邊 clamp(w + ink + 0.5 − s)（外部 clamp(ink + 0.5 + s)），邊緣 1 px 線性過渡；畫布邊緣當作身體外。裁切 O 在被擋者貼圖上逐像素取各前排貼圖（最近鄰、alpha ≥ 128），大型前排設 1、之後的小兵設 0；黑邊另乘 dilate(O, ink)（O 的距離轉換）。色線畫白、黑邊 `#16121a`，先疊成一層非預乘 RGBA 再 `putImageData`→`Texture.from`。測試：圓盤沿法線量色線寬誤差 ≤ 0.5、黑邊兩側各 ≈ ink、外側透明、只畫被擋段、小兵挖掉、兩次 SHA-256 相同。
- **Q2（量化鍵）**：線寬（貼圖 px）＝ 1.5 × 貼圖 px／模型 px ÷ 地圖縮放，量化 0.25；襯邊 0.75 同法。鍵 `ol|<res>|<身體鍵>|w:<寬>|i:<襯邊>|c:<裁切雜湊>`（計畫的鍵另加裁切雜湊，因為裁切畫進貼圖；裁切沒變時沿用）。測試第 8 項：800／1600 寬 × DPR 1、2 × 人形／頭目，換回 CSS px 都在 1.5 ± 0.12，縮放 ±0.001 鍵不變。`setScale` → `rebuildOutlines` 只換貼圖。
- **和樣張真 1 倍的像素差**：沒有做逐像素比對（樣張用 `drawImage` 0.5 px 步距膨脹，本來就會差）；只做目視對照（`4-true1x-1600.png`、`5-true1x-800.png` vs 樣張 `closeup/occlude/6-true1x-*.png`）。見待決 3。

## 5. 需求第 5 節 (a)(b)(c)

**(a) 大型前排面積實測**（模型 px²，`ocl-gallery.html?measure=1`；800 與 1600 寬相同）

| 單位 | 實測 | 紀錄 10.2／樣張量測表 | 差 |
|---|---|---|---|
| 灰燼之心（第 1 階段，朝北／朝東兩種鏡射） | 8870／8866 | 8928 | −0.7% |
| 碎晶之主（第 2 階段） | 8404／8412 | 8220（紀錄）、6929（樣張現行量測表） | +2.2%／+21% |
| 主角 | 1099 | 1646（樣張 hero） | −33% |
| 持盾盜匪 | 1279 | 1702 | −25% |
| 法師 | 1459 | 1963 | −26% |
| 精英碎晶傀儡 | 1747～1755 | 1751 | ±0.2% |
| 餘燼蜥／熔岩蛞蝓／晶塔 | 658～665／502／549 | 小型異形 506～558 | 蜥 +19%，其他在範圍內 |

原因（超過 ±3% 的）：①人形差 25～33%：遊戲端 Q 版人物在 1 倍解析度畫時外框較細（同一個主角在 res＝k、2k、4k 量到 1118／957／911，外框寬隨解析度變），樣張的 `QDoll.stamp` 另有 `dpr` 參數、樣張用的人物外觀（`TP.*`）也和開發頁的範本不完全一樣；沒有再深究。②碎晶之主樣張量測表是第 2 階段 t＝900 的姿勢，遊戲端站好是第 0 格。③餘燼蜥：外觀來源不同（樣張 spec）。**判斷不受影響**：4000 的門檻兩邊仍各留 > 1.5 倍（頭目 ≥ 8404、一般 ≤ 1755）。

**(b) 比例實測（CB-4 情境，大型前排）**

| 情境 | 遊戲端 | 樣張 `?part=measure` |
|---|---|---|
| 主角在灰燼之心後 | 95.5% → 畫 | hero behind ah 94% |
| 餘燼蜥在灰燼之心後 | 100% → 畫 | 100% |
| 法師在碎晶之主後 | 97.2% → 畫 | 93% |
| 盜匪在灰燼之心後 | 92.2% → 畫 | 90% |
| 持盾盜匪在碎晶之主後 | 93.8% → 畫 | （無此列） |
| 熔心坑：主角 (5, 4) 在灰燼之心 (5, 5) 後 | 95.5% → 畫 | — |
| 熔心坑：餘燼蜥 (6, 4) 在灰燼之心後 | 54.0% → 不畫 | — |
| 一般單位互擋 8 對（`pairs`） | 前排不是大型，全部不算（大型前排 0%） | 第 3 版全部不畫 |

比例在 1600 與 800 寬逐筆相同（模型像素算，和縮放無關）。

**(c) 6F-22 舊剪影去留**：`drawUnit` 不再畫舊剪影；`drawOcclusion` 先建外框，最後對每個單位呼叫 `legacySilhouetteWanted(occluded || roofCovers, outlineOf.has(id))`——有新外框就不畫（也不記 `silhouetteOf`），沒有就照現行條件畫（倒下的人照舊也畫）。測試第 9 項四種組合＋繪製器層；換回 `6f2a8aeb` 的 `unitLayer.ts` 跑本測試檔：**3 項失敗**（繪製器層舊剪影規則、原始碼掃描、`ocl=0` 照畫舊剪影），跑完已還原。

## 6. 效能

量法：開發頁 `ocl-gallery.html?scene=field&perf=1`（12 個單位＋灰燼之心），`draw(model)` 暖機 5 次後取 50 次；外框計算＝`drawOcclusion` 整段；待機 10 秒 `requestAnimationFrame` 間隔；無頭 Chrome **`--disable-gpu`**（軟體繪製）、`--mute-audio`、DPR 1。

| | 1600 開 | 1600 關 | 800 開 | 800 關 |
|---|---|---|---|---|
| `draw` 中位數／p95（ms） | 2.7／3.8 | 2.5／4.3 | 2.7／3.7 | 1.7／2.7 |
| 外框計算中位數／p95（ms） | **0.3／0.4** | 0.1／0.2 | **0.3／0.4** | 0.0／0.1 |
| 第一次 `draw` 的外框計算（冷，ms） | 263.5 | 0.3 | 215.4 | 0.3 |
| 待機影格中位數／p95（ms） | 16.7／33.4 | 16.7／33.4 | 16.7／33.3 | 16.7／16.8 |
| `__texStats` 張數／位元組 | 246／26.5 MB | 245／26.4 MB | 247／22.7 MB | 249／22.8 MB |
| `getImageData` 次數＝遮罩鍵數 | 15＝15 | 0 | 15＝15 | 0 |

- 擺位不變時的外框計算中位數 0.3 ms（< 1 ms）；影格時間開關無差別（p95 33 ms 是軟體繪製的偶發掉格，開關都有）。
- **冷啟動慢**：第一次要畫 15 張身體畫布（模型像素用）＋2 張畫面解析度的，再讀 alpha，約 0.2～0.26 秒（軟體繪製）。之後換位置只要重算模型遮罩（照小數位置快取）。見待決 1。

## 7. 快照與既有測試

- 雜湊快照（`creaturePose`、`inkDollSnapshot`、`__snapshots__`、`qi3bStatusBaseline.json`、`qi2dBaseline.json`）**都沒變**；沒有用 `-u`。
- 「不應變」的測試（`occludedHud`、`hid1bLayers`、`silhouetteFlash`、`heightShapes`、`elevation`）照舊通過。
- 原有的身體貼圖鍵逐字不變；新增的鍵前綴只有 `ol|`（外框貼圖，`ArtTextures` 快取）、`om|`／`oa|`（alpha 遮罩，`ArtTextures.alphaMask` 另一份上限 256 的表，不進貼圖 LRU）。

## 8. 截圖（`docs/art/shots/ocl1/`，全是開發頁；jpg 80、PNG 最近鄰）

| # | 檔案 | 內容 | 對需求第 5 節 |
|---|---|---|---|
| 1 | `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/ocl1/1-boss.jpg` | `scene=boss`（DPR 2）：灰燼之心擋友方、擋敵方；碎晶之主擋友方、擋敵方 | 1 |
| 2 | `.../ocl1/2-field-1600.jpg` | `scene=field&w=1600` 整張（縮放 1.20） | 3 |
| 3 | `.../ocl1/3-field-800.jpg` | `scene=field&w=800` 整張（縮放 0.53） | 3 |
| 4 | `.../ocl1/4-true1x-1600.png` | 1600 寬真 1 倍、主角那一格最近鄰 ×3 | 3 |
| 5 | `.../ocl1/5-true1x-800.png` | 800 寬真 1 倍、最近鄰 ×6 | 3 |
| 6 | `.../ocl1/6-pairs.jpg` | `scene=pairs` 8 對全部不畫 | 4 |
| 7 | `.../ocl1/7-collide-row4.jpg` | 第 4 列：熔爐母蜥被灰燼之心＋高 3 精英傀儡擋，外框只在頭目身上（傀儡範圍挖掉 149 個貼圖像素，實測） | 5 |
| 8 | `.../ocl1/8-collide-legacy.jpg` | 左兩格：蛞蝓、晶塔在高 3 主角後＝只有舊剪影；右二：被頭目擋＋南邊高台＝只有新外框、沒有舊剪影；右一：第 4 列 | 4、6 |
| 9 | `.../ocl1/9-concealed.jpg` | 左：隱匿中的盜匪在頭目後不畫；右：沒隱匿的對照有外框 | 7 |
| 10 | `.../ocl1/10-team.jpg` | 友／敵／第三方／召喚物的外框色 | （陣營色） |
| — | 遲滯不拍 | 測試第 4 項：表格、0.50→0.56→0.50→0.46→0.44→0.50 序列、繪製器連續 draw | 8 |

（`...` ＝ `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots`；合併前在 worktree 的同一路徑下。）

## 9. 實機未看

全部截圖都是開發頁（真的 `BattleRenderer.draw`、手寫 `DrawModel`），沒有開 `trpg serve` 打正式對局：CB-4 頭目往北打、隱匿敵人在頭目後、第 4 列「頭目＋小兵」、被頭目擋又被高台擋，都只在開發頁看過。浮動卡實測（6.5.1）沒做：本段沒有改 HUD、卡片或 `ui/`。

## 10. 自己啟動的程序

vite（埠 5320，Windows PID 63880）、靜態伺服器（樣張量測表用，埠 5321，PID 48324）、無頭 Chrome（CDP 8163，`--user-data-dir` 在 scratchpad `ocl1a/chrome-ud`）。交件前 vite、靜態伺服器用 `taskkill /PID` 關掉，Chrome 用 CDP `Browser.close` 關掉；三個埠都已沒有監聽。

## 待 PM 決定

1. 冷啟動：第一次 `draw` 外框計算約 0.2～0.26 秒（軟體繪製，主要是畫模型像素用的身體畫布）；之後 0.3 ms。要不要改成只在附近有大型前排時才畫小兵的遮罩（現在異形畫布夠大就會畫），或接受。
2. 人形面積比樣張量測少 25～33%（第 5 節 (a)）：不影響 4000 門檻，但和紀錄對不上；要不要請美術 PM 確認樣張人形的量法。
3. 和樣張真 1 倍只做了目視對照，沒有逐像素比；要不要補。
4. 倒地狀態（`prone`，身體旋轉）的人不當被擋者（保守）；1b 處理旋轉時一併決定。
5. 外框貼圖鍵比計畫多一段裁切雜湊 `c:`（裁切畫進貼圖，必須進鍵）。
6. 計畫第 4 列樣張用位移（頭目往東 10、傀儡往東 6），格子上做不到；開發頁改成熔爐母蜥 (1,1)、灰燼之心 (1,2)、精英傀儡 (2,2) 高 3 階。要不要換別的擺位。
7. 1a 時走路、擊退、出招片段中外框停在原地（不藏、不跟）——1b 第 2、3 點處理；1a 單獨上線前要知道。
8. `ocl-gallery` 的小場面一律用「熔心坑 12×12 在該寬度」的縮放（1600＝1.20、800＝0.53），不是樣張的 1.31／0.53，是照計畫「照 fitScale 算」；要對樣張數字時用 `&scale=1.31`。

## 給美術 PM 的截圖清單

`F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/ocl1/` 下：`1-boss.jpg`（需求 1）、`2-field-1600.jpg`、`3-field-800.jpg`、`4-true1x-1600.png`、`5-true1x-800.png`（需求 3）、`6-pairs.jpg`（需求 4）、`7-collide-row4.jpg`（需求 5）、`8-collide-legacy.jpg`（需求 4、6）、`9-concealed.jpg`（需求 7）、`10-team.jpg`（陣營色）。全部是開發頁（實機未看）；受擊閃白（需求 2）是 1b。遲滯（需求 8）用測試鎖住，測法見第 8 節。
