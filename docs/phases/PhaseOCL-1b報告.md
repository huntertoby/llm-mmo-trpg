# Phase OCL-1b 報告｜被遮擋剪影外框（動態）

> 實作 agent（Opus 5.5），2026-11-12。依據 `docs/phases/PhaseOCL-1計畫.md`（Q1～Q9 照建議、D1～D8 照做）、`docs/art/被遮擋剪影外框-移植需求.md`、`docs/phases/PhaseOCL-1a報告.md`。
> 基準：OCL-1a 完成的 `32017a66`（同一個 worktree、同一個分支）。後端、`content/`、API 沒動。
> PM 對 1a 待決的裁定一併做：1（冷啟動：只有附近有大型前排時才建遮罩）做了；2、3、5、6、8 照裁定不動；4（`prone` 不當被擋者）照舊，見第 3 節。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| PM 裁定 1a 待決 1（冷啟動） | `BareBody.fill`（紙娃娃、人形召喚物 `DOLL_MAX_FILL` 0.45）：畫布 × fill 不到 4000 的不畫遮罩；`OclUnit.row`（片段後重算用畫面上的排） | `0f0deaa6` |
| 1b-1～4 | `occlusionLayer.ts`：`refreshOcclusion`（片段結束重算，用 `draw` 時記下的站好身體位置、擺位簽名沒變就沿用）、`beginMove`／`endMove`（Q5）、`tickOutlines`（Q4：每格跟著身體節點平移、旋轉時藏）、`flashOutline`（D4、Q6）、`hideOutline`（倒下片段）；接線：`motionLayer`（走路、位移、進出門）、`skillLayer`（出招前轉向、出招列結束、被撞倒的白閃）、`vfxLayer`（異形受擊、人形受擊、疊層、減少動態）、`reactEffects`（`ReactHost.outline`：受擊、重擊、格擋、倒下、疊層、木樁）、`BattleRenderer.init`（ticker `LOW + 1`）；峰值常數 `HUMAN_HIT_FLASH`、`CREATURE_HIT_FLASH`、`HEAVY_HIT_FLASH`、`BLOCK_FLASH`、`CREATURE_HEAVY_GAIN`、`REDUCED_FLASH_PEAK` 與 `reactFlashPeak`／`creatureReactFlashPeak`（只把原本的字面值換成同值常數）；`outlineFlashK`；測試 `render/ocl1Playback.test.ts` | `6aa46731` |
| 1b-5（開發頁） | `skill-gallery.html#cb2b` 加 `oclAhN`、`oclAhNEnemy`、`oclLordN`、`oclBoarHit`、`oclHumanHit`（`Cb2bCase` 加 `casterTeam`、`targetAs`、`extras`） | `562cd0d0` |
| PM 裁定 1a 待決 1（再收一步） | 大型前排有像素的範圍（`tightBox`）碰不到被擋者整張畫布時，不畫被擋者的遮罩 | `86aab1b5` |
| 1b-5（連拍） | `&afterHit=0,30,90,300`：命中後這幾個毫秒各拍一張 | `1381c68d` |
| 1b-6 | 本報告、上手筆記（第一節、第二節「被遮擋外框」補播放與白閃 k、開發入口、第四節第 58、59 點、第五節測試）、截圖 7 張 | 最後一個 commit |

## 2. 驗收逐條

1. **測試**：`render/ocl1Playback.test.ts` 45 項全過（第 11、12 項＋冷啟動）；`render/ocl1Outline.test.ts` 37 項照舊全過。動到白閃呼叫點的 `render/reactClips.test.ts`、`render/bodyAnim.test.ts`、`render/reducedMotion.test.ts`，動到 `artTextures`／身體的 `render/creaturePose.test.ts`、`render/inkDollSnapshot.test.ts`，以及 `ui/occludedHud.test.ts`、`ui/hid1bLayers.test.ts`、`render/silhouetteFlash.test.ts` 全過。
2. **三個結束碼**（交件前各跑一次）：見第 9 節。
3. `git diff --stat 32017a66 -- src/trpg content client/src/api client/src/render/__snapshots__ client/src/render/fixtures` 為空。
4. 截圖第 8 節。
5. 效能第 6 節。

## 3. 現況確認與實作說明

- **什麼時候算**（交付 1）：`draw(model)` 照舊算；片段中不算。`refreshOcclusion` 在三個地方呼叫：移動結束（`endMove`，沒有其他人在移動時）、`playSkill` 開頭施放者轉向之後、每一列出招片段的 `end`。重算的擺位：單位資料用繪製器目前的（`unitDrawOf`：轉向、走路滑倒後的）、排用畫面上所在的排、身體位置用 `draw` 時記下的**站好位置**（`restOf`），所以前推、後仰、擊退這種身體節點位移中途重算＝片段開始前的結果；擺位簽名和上一次相同就什麼都不做（不重建 Sprite、不重算遮罩，測試鎖住 `calls` 為空）。待機換貼圖不重算。
- **跟著身體**（Q4）：ticker 每格（優先度 `LOW + 1`：所有動畫、效果迴圈之後，算繪之前）照單位 ID 找目前的小人節點（轉身重建的新節點也跟得上），外框位置＝單位節點＋身體節點的位置；身體 `rotation ≠ 0`、小人節點不在畫面上、倒下片段中時 `visible = false`。不跟縮放、不換貼圖。
- **移動**（Q5）：`animate`（每一段位移）、`animateWalk`、`playLeave`、`playArrive` 開頭 `beginMove`、結束 `endMove`（含鳥走完留在空中的提早 `return`）。有人在移動時 `refreshOcclusion` 直接返回（別人沿用移動前的結果），最後一個人停下時重算一次。移動過的人的 6F-22 舊剪影（`model` 的格子還是舊的）等下次 `draw` 才回來；沒移動的人的舊剪影照重算結果加減（D5）。
- **受擊閃白**（D4、Q6）：每個白閃呼叫點傳（當下白閃, 峰值）：`creatureHit` → (`pose.flash`, `CREATURE_HIT_FLASH` 0.9)；`dollHit`、`overlayHit` → (`humanHit(t).flash`, 0.85)；`reactEffects` 人形 → (`reactFrame(clip).flash`, `reactFlashPeak(clip)`：受擊、倒下、陷阱 0.85，重擊 0.95，格擋 0.35，閃避 0)；異形 → (`creatureReact(clip).flash`, `creatureReactFlashPeak(clip)`：受擊、陷阱 0.9，重擊 0.99，閃避、格擋 0)；疊層 → (`× strength`, 0.85 × strength)；木樁 → (`DUMMY_FLASH_ALPHA`, 同值)；減少動態 → (0.85 × (1 − t), 0.85)；被撞倒（`knocked_down`）→ (`humanHit`, 0.85)。外框層 `k = clamp(flash / peak)`，`tint`＝`flashTint(陣營色, k)`、`alpha`＝0.8 + 0.2k，結束送 (0, 1)；閃白中重畫時新外框接著同一個 k。倒下（人形 `downEffect`、異形 `down`）呼叫 `hideOutline`，頭目倒下的 0.7 白閃不傳（Q6）。
- **和計畫第 1 節的出入**：計畫表的「異形重擊 0.99」照傳，但身體白閃經 `quantizeCreaturePose` 量化後實際是 **1.0**；k 夾在 1，所以到頂時外框一樣全白，只是 k 早 1% 到 1（測試第 11 項這一列容許 0.0101，見待決 3）。
- **1a 待決 4（`prone`）**：照 PM 裁定，倒地狀態（身體躺著）的人仍不當被擋者；片段後重算時，走路滑倒（`markProne`）的人也照這條不畫。
- **冷啟動（PM 裁定 1a 待決 1）**：兩步預篩，判定結果不變。①`BareBody.fill`：紙娃娃身體最多佔畫布 0.45（實測 `unitDolls.json` 31 個紙娃娃範本 × 4 朝向 × 精英與否，bare、res 1，最大 0.298＝`bandit_boss` 朝南，取 1.5 倍）；畫布 × fill 不到 4000 的不畫遮罩——基本大小 5637 → 2537、精英 7455 → 3355，外觀放大約 1.23 倍以上才要畫。異形、頭目、形態沒有 fill（畫布本來就 > 4000，照舊畫遮罩量面積；一張 1.5～2 ms，頭目 18 ms）。②被擋者的遮罩只在「大型前排有像素的外接矩形（`tightBox`）碰得到被擋者整張畫布」時才畫（遮罩一定在畫布裡，碰不到＝不會相交＝不畫，和算了一樣）。對照：`ocl-gallery` 的 6 個場面（boss、pairs、collide、concealed、team、field，1600 寬）畫外框的單位與比例，和 1a 的量測檔逐筆相同。

## 4. 行為一致測試（`render/ocl1Playback.test.ts`）

| 項目 | 測試 |
|---|---|
| 第 12 項：片段中沿用 | 頭目身體節點前推 30 後某一列結束重算：同一個 Sprite、同一張貼圖、比例 70% 不變、重算次數 0、沒有取任何遮罩 |
| 第 12 項：片段結束重算 | 前排走開：移動中重算被延後、外框與比例沿用；移動結束重算 1 次、外框拿掉。前排走過來：移動中不畫、結束才畫 |
| 第 12 項：移動者 | `beginMove` 後自己的外框 `visible = false`，每格對齊也不會打開；停下重算後回來 |
| Q4 | 身體節點位移 (4, −3) → 外框同一個位移、貼圖不換；轉身換成新節點也跟得上；`rotation` 0.3 藏、0 出現；`hideOutline` 藏到下次 `draw` |
| 第 11 項：k | 21 列（人形受擊；人形反應 hit／heavy／block／down／trapped × 3 個變體；異形受擊；異形反應 hit／heavy／trapped；減少動態；木樁；疊層格擋）各自「片段裡最大的白閃＝傳給外框的峰值」，白閃＝峰值時 k＝1、tint 白、alpha 1，白閃 0 時原色 0.8；峰值表 0.85、0.95、0.9、0.99、0.35、0.85；異形每一種反應的分母都不是 0.85（白閃 0.45 → k 0.5）；原始碼掃描：`vfxLayer`、`skillLayer`、`reactEffects` 的 16 個 `flashOutline`／`outline.flash` 呼叫都沒有寫死的小數，`creatureHit` 用 `CREATURE_HIT_FLASH` |
| 第 4 點 | 繪製器：k 1 → 白、1；k 0.5 → mix、0.9；結束 → 陣營色、0.8；貼圖一直是同一張；閃白中 `draw` 新外框接著同一個 k |
| reactEffects | 假 `ReactHost`：異形受擊 0.9、重擊 0.99，人形受擊 0.85、重擊 0.95、格擋 0.35；最大 k＝1；結束送 (0, 1)；倒下呼叫 `hide`，異形倒下不傳白閃 |
| 接線 | 原始碼：`animate`、`animateWalk`、`playLeave`、`playArrive` 都有 `beginMove`／`endMove`；`playSkill` 與 `rowEffect` 的 `end` 有 `refreshOcclusion`；ticker 優先度 `LOW + 1` |
| 冷啟動 | 紙娃娃 `fill` 0.45；基本、精英 `canBeBig` 假、外觀 1.5 倍精英真；只有紙娃娃、一排排緊貼的 5 個人：`alphaMask` 0 次、`getImageData` 0 次；大型前排像素碰不到被擋者畫布時不取被擋者遮罩、碰得到才取；合成的 4000 填滿身體照舊算大型前排 |

**舊程式下的失敗數**（第 13 項；暫時換回 `32017a66` 的檔案跑 `ocl1Playback.test.ts`，跑完已還原）：全部換回 → 整檔匯入失敗（`reactFlashPeak is not a function`）；只換 `occlusionLayer.ts` → 10 項失敗；`reactEffects.ts` → 4；`unitSprite.ts` → 2；`outlineLayer.ts` → 2（`86aab1b5` 前的版本 → 1）；`motionLayer.ts`、`skillLayer.ts`、`BattleRenderer.ts` → 各 1；`vfxLayer.ts` → 整檔匯入失敗（沒有 `REDUCED_FLASH_PEAK`）。

## 5. 快照與既有測試

- 雜湊快照（`creaturePose`、`inkDollSnapshot`、`__snapshots__`、`qi3bStatusBaseline.json`、`qi2dBaseline.json`）**都沒變**，沒有用 `-u`。白閃的字面值換成同值常數（`0.85`、`0.9`、`0.95`、`0.35`、`1.1`），算式不變。
- 既有測試沒有改任何期望值。

## 6. 效能

量法同 1a：無頭 Chrome **`--disable-gpu`**（軟體繪製）、`--mute-audio`、DPR 1。

**冷啟動**（`ocl-gallery.html?scene=field&perf=1`，第一次 `draw` 的外框計算）

| | 1600 開 | 800 開 |
|---|---|---|
| 1a | 263.5 ms（本機重量 201.7）、`getImageData` 15 | 215.4 ms（重量 190.7）、15 |
| 1b | **173.4 ms**、13 | **164.2 ms**、13 |

剩下的 13 張：頭目模型像素 19 ms＋畫面解析度 29 ms、主角（被擋者）15＋32 ms、主角兩側被頭目碰到畫布的 2 個紙娃娃約 13 與 40 ms（第一張紙娃娃特別慢）、異形 5 張各 1.5～3 ms。**仍 > 50 ms**（待決 1）。只有紙娃娃的場面是 0 次。

**擺位不變時**（同頁 50 次 `draw`）：外框計算中位數 0.2 ms／p95 0.3 ms（1600、800 都是）；`draw` 中位數 1.8／1.6 ms（關外框 1.5／1.6）；待機影格中位數 16.7 ms，開關無差別。

**播放中**（`skill-gallery.html?case=…#cb2b`，`window.__cb2bPlay()` 一次；`performance.now()` 包住各方法，解析度 0.1 ms）

| 案例 | 每格 `tickOutlines` 中位數／最大 | `flashOutline` 次數／最大 | `refreshOcclusion` 次數／最大 | 實際重算 |
|---|---|---|---|---|
| `oclAhN` | 0.0／0.2 ms（114 格） | 7／0.0 ms | 2／0.1 ms | 0 |
| `oclHumanHit` | 0.0／0.1（106） | 7／0.0 | 3／0.2 | 0 |
| `oclBoarHit` | 0.0／0.1（110） | 15／0.1 | 3／0.1 | 0 |
| `ahRamEdgeWN` | 0.0／0.1（112） | 7／0.1 | 2／0.1 | 0 |
| `lordSwingEdgeN` | 0.0／0.1（103） | 6／0.0 | 2／0.1 | 0 |

播放中每格只動位置、`visible`、`tint`、`alpha`；出招列結束的重算全部因為擺位簽名沒變而沿用（0 次重建）。

## 7. 開發頁案例（`client/dev/skill-gallery.html#cb2b`）

- `oclAhN`：灰燼之心第 1 階段站 (4, 3)、往北打 (4, 2) 的主角（友方）。
- `oclAhNEnemy`（Q7）：**第三方**的灰燼之心站在**敵方**盜匪正南往北打（Q7 的第二種做法）。第一種做法「頭目身後同一排另一側放敵方小兵」實測盜匪在 (5, 2) 只被擋 30.7%（< 55%，不畫），所以改用第二種。
- `oclLordN`：碎晶之主站 (4, 3)、往北打主角。
- `oclBoarHit`：第三方硫煙獸在 (4, 2)、灰燼之心在它正南不動、西邊 (3, 2) 的盜匪普攻打它（異形受擊閃白）。
- `oclHumanHit`：同上，被打的是主角（人形受擊閃白）。
- CB-4 的 `ahRamEdgeWN`、`lordSwingEdgeN` 沒改，現在也有外框。

## 8. 截圖（`docs/art/shots/ocl1/`，全是開發頁；jpg 80）

| # | 檔案 | 內容 | 對需求第 5 節 |
|---|---|---|---|
| 1 | `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/ocl1/1b-1-ah-north-play.jpg` | `oclAhN` 出招片段 t＝0（出招前）、250（前推）、500（命中）、583（命中後）、1000（收勢）：外框沿用片段開始前的形狀、跟著主角被打退平移、命中時閃白 | 1 |
| 2 | `.../ocl1/1b-2-human-hit-flash.jpg` | `oclHumanHit` 命中後 +0、+30、+90、+300 ms：外框白 → 淡藍 → 陣營色 | 2 |
| 3 | `.../ocl1/1b-3-boar-hit-flash.jpg` | `oclBoarHit` 同上（第三方紫色、異形峰值 0.9） | 2 |
| 4 | `.../ocl1/1b-4-ah-north-enemy.jpg` | `oclAhNEnemy`（Q7）：敵方被擋者（紅色外框），同 #1 的 5 個時間點 | 1 |
| 5 | `.../ocl1/1b-5-lord-north-play.jpg` | `oclLordN` t＝0、250、333、417、833：碎晶之主擋住主角 | 1 |
| 6 | `.../ocl1/1b-6-cb4-ah-ram-left-column-north.jpg` | （選）CB-4 `ahRamEdgeWN&margin=1` 重拍，對照 `shots/cb4/2-ah-ram-left-column-north.jpg` | 1 |
| 7 | `.../ocl1/1b-7-cb4-lord-swing-right-column-north.jpg` | （選）CB-4 `lordSwingEdgeN&margin=1` 重拍，對照 `shots/cb4/4-lord-swing-right-column-north.jpg` | 1 |

（`...` ＝ `F:/PythonProject/LLM-MMO-TRPG/docs/art/shots`；合併前在 worktree 的同一路徑下。連拍參數：`&sheet=1&cell=72&crop=2.5,2.4,4,3.6`（灰燼之心）／`2.5,3.3,4,4.2`（碎晶之主）、`&at=…` 或 `&afterHit=0,30,90,300`。）

## 9. 交件前的結束碼

在 `1381c68d`（程式最後一個 commit；之後只有文件與截圖）各跑一次：

- `corepack pnpm -C client typecheck` → **0**
- `corepack pnpm -C client test` → **0**（306 檔、3957 項全過）
- `corepack pnpm -C client build` → **0**（只有既有的 chunk 大小警告）

## 10. 實機未看

全部是開發頁（`skill-gallery.html#cb2b` 走正式的 `playbackPlan → frameOps`，但戰鬥資料是手寫的），沒有開 `trpg serve` 打正式對局：頭目往北打被擋的友方／敵方、被頭目擋著受擊、走路與擊退中藏外框、進出門。走路與擊退中藏外框、移動結束重算只用 vitest 鎖住，沒有截圖（需求第 5 節沒有這一項）。浮動卡實測（6.5.1）沒做：本段沒有改 HUD、卡片或 `ui/`。

## 11. 自己啟動的程序

vite（埠 5320，Windows PID 40616）、無頭 Chrome（CDP 8163，`--disable-gpu --mute-audio`，監聽 PID 46772，`--user-data-dir` 在 scratchpad `ocl1b/chrome-ud`）。交件前 vite 用 `taskkill /PID` 關掉、Chrome 用 CDP `Browser.close` 關掉，兩個埠都已沒有監聽。

## 待 PM 決定

1. 冷啟動做完兩步預篩後 1600／800 寬仍約 173／164 ms（> 50 ms；只有紙娃娃的場面 0 次）：剩下的是頭目與被擋者本身、碰到頭目的鄰居紙娃娃的遮罩。要再降得改成「模型像素遮罩從畫面解析度那張縮出來」（會讓比例差一點點、判定可能不同）或延後到閒置時才算，請決定要不要做。
2. 紙娃娃預篩的 `DOLL_MAX_FILL` 0.45 是實測最大 0.298 的 1.5 倍（假設）；以後若有特別寬大的紙娃娃（大披風、巨盾）佔畫布超過 45%，會被誤當成「不可能是大型前排」。要不要接受，或改成只信實測（每個範本第一次畫完就記面積）。
3. 異形重擊照需求表傳 0.99，但身體白閃量化後實際是 1.0（k 早 1% 到頂、夾在 1）；要不要改成照實際的 1.0。
4. Q4「旋轉時藏起來」照字面做了：**任何**身體旋轉都藏，包括人形受擊的「側彎」變體（最多約 10°，三種受擊變體之一），所以這種受擊外框會藏起來、看不到閃白。另一個做法是外框跟著身體節點一起轉（錨點相同），只在空翻、倒下藏。
5. 片段結束的重算用 `draw` 時記下的「站好」身體位置，所以異形待機或出招中的整隻位移（`creatureOffsetPx`）只會讓外框跟著平移、不會讓比例重算；要等下次 `draw`。
6. 移動過的人的 6F-22 舊剪影要等下次 `draw`（播放結束一定會重畫）才回來；移動結束到重畫之間那個人兩種都沒有。
7. 進出門（`playLeave`／`playArrive`）也當作移動，外框藏起來（計畫沒寫，保守做法）。
8. `oclAhNEnemy` 用 Q7 的第二種做法（第三方頭目打敵方），因為第一種擺位只擋 30.7%。

## 給美術 PM 的截圖清單

`F:/PythonProject/LLM-MMO-TRPG/docs/art/shots/ocl1/` 下：`1b-1-ah-north-play.jpg`（需求 1：出招中沿用、片段結束）、`1b-2-human-hit-flash.jpg`、`1b-3-boar-hit-flash.jpg`（需求 2：人形、異形受擊閃白 0／30／90／300 ms）、`1b-4-ah-north-enemy.jpg`（需求 1：敵方被擋者，Q7）、`1b-5-lord-north-play.jpg`（需求 1：碎晶之主）、`1b-6-cb4-ah-ram-left-column-north.jpg`、`1b-7-cb4-lord-swing-right-column-north.jpg`（選：CB-4 重拍）。全部是開發頁（實機未看）。請特別看待決 4（側彎受擊時外框藏起來）與 Q4「輪廓和後仰的身體差幾 px」（#2、#3 的 +0、+30 ms）。
