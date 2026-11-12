# Phase QK-7 報告：武器專屬待機 15 種（Q 版）

> 實作者：worktree `dev/qk7`（從 main `f4a018fc` 開）。沒有 push、沒有 rebase。依據：`docs/art/武器待機移植需求.md` 全文、`docs/art/QK移植需求.md` 第 0 節與第 8 節；真相來源 `docs/art/sample/idleWeapons.js`、`docs/art/shots/idle/idle-weapons.gif`。只換畫法與待機動畫，規則、資料、存檔、重播都沒動；沒有 import 樣張程式。

## 1. 做了什麼

| 項目 | 做法 | 檔案 |
|---|---|---|
| 15 種待機定義 | 樣張 `IDLE` 表照搬數值（`ms`、`zh`、`mid`），呼吸 bob 拆開（`breath`），`weaponIdlePose(kind, u, breath)` 等於樣張 `pose(u)` | `client/src/render/idleWeapons.ts` |
| 相位 | `idHash(`${id}:weaponIdle`) % 1000 / 1000`（FNV-1a，共用 `idleClips.idHash`）；不用 `Math.random`、不讀時間，時鐘是 6M-4 ticker 累加的毫秒 | 同上 |
| 8 格量化 | `weaponIdleFrame(kind, id, ms, opt)`＝樣張 `frame()`：動作取 `floor(u×8)/8`，`glow`／`orbY` 即時；`view` 不是側面時只留 `bob、glow、orbY、shieldUp、pull`；`reduce` 回傳空姿勢 | 同上 |
| 選哪一種 | `weaponIdleKindOf(QUnit)`：主手的 Q 版武器種類；劍、刀、匕首、斧、鎚＋副手盾 → 劍盾；匕首、斧、鎚 → 劍；拳（fist）→ 拳套；長槍形制 → 火槍；Q 版不會畫的手持物（拂塵、符紙…）與空手 → 不晃（只照 6M-4 呼吸） | 同上 |
| `InkPose` 新鍵 | `shieldUp、glow、orbY、lash、dw、nock、idle、glowLayer` 加進 `InkPose` 與 `POSE_KEYS`（貼圖鍵 `poseKey` 會帶上；值為 0 的不寫，既有片段的鍵不變）。Q 版畫法本來就吃這些鍵（QK-1 已移植），C 畫法不吃 | `inkPose.ts`、`qCore.ts` |
| 接上戰場 | `IdleMotion.tick`：**Q 版、戰場（沒有實地場景）、沒輪到行動（`!draw.active`）、有骨架、6M-4 `idles()` 成立、沒在播小動作**時，換成武器待機這一格的貼圖（鍵 `wi:<poseKey>`，只在換格時換貼圖）；定身照 `lockLegs`；小動作（張望、伸懶腰）照舊，播時武器待機暫停；`hold` 時一起藏疊加層 | `idleMotion.ts`、`weaponIdleLayer.ts` |
| 疊加層（不量化、不換貼圖） | **法杖**：貼圖不畫杖頭光暈（`glowLayer: 1`），疊加層每幀畫光暈（墊外框色，同樣張「光暈也算剪影」）＋光點＋高光，四面都有。**魔導劍**：源晶槽外疊兩圈半透明光（代替 shadowBlur 增量）＋符文，背面不疊（劍被身體擋住）。錨點用 Q 版畫法的 `probe` 量武器矩陣，同裝備同朝向同一格只量一次。Pixi `Graphics` 放在小人節點正上方，位置、縮放（含 6M-4 呼吸）、透明度每幀跟著小人 | `weaponGlow.ts`、`weaponIdleLayer.ts`、`qWeapons.ts` |
| 減少動態 | `prefers-reduced-motion`（6N-10 的 `reduced`）或 `setIdle(false)`：一律站好（`setPose(null)`），疊加層藏起來，光不脈動 | `idleMotion.ts` |
| dev 畫廊 | `client/doll-gallery.html?skin=q&set=idle&t=<ms,…>[&mode=sample][&facing=east|west|south|north][&reduce=1][&dump=1]`：版面同樣張 `idle-weapons.html` 第 1 節（1240×600、15 格）。`mode=game`（預設）照遊戲畫法：8 格貼圖＋疊加層＋6M-4 呼吸縮放；`mode=sample` 照樣張算法 | `client/src/dev/qGallery.ts` |
| 樣張資料 | `qSample.SAMPLE_IDLE` 改從 `idleWeapons.ts` 取（不再複製一份表） | `qSample.ts` |

## 2. 截圖（`docs/art/shots/qk7/`，共 5.3 MB）

- `qk7_idle_compare.gif`：**左：樣張 `shots/idle/idle-weapons.gif`、右：遊戲畫法**，16 格 × 150ms（和樣張 gif 同時間點，t = 0～2250ms），縮 50%。
- `qk7_idle_compare_t0000.jpg`、`_t0900.jpg`、`_t1650.jpg`：同上的原尺寸單格。
- `qk7_idle_algo_vs_game_t*.jpg`：左＝畫廊 `mode=sample`（同底色，方便逐格比），右＝遊戲畫法。差異約 1.4～1.6% 像素，來源是呼吸（樣張 bob 位移 vs 遊戲 6M-4 垂直縮放）與 8 格量化。
- `qk7_idle_game.gif`：遊戲畫法單獨一張。
- `qk7_idle_south.jpg`、`qk7_idle_north.jpg`、`qk7_idle_west.jpg`：正面、背面、朝西各 4 個時間點（0、600、1200、1800ms）。
- `qk7_idle_reduce.jpg`：減少動態 t=0 與 t=700 並排，**標題列以下逐像素相同**（差異框 None）。
- `qk7_battle_1600.jpg`：實機 1600×900 戰場（開發模式、起始武器魔導劍、靜音）；`qk7_battle_1600_zoom.jpg` 地圖區 2 倍；`qk7_battle_1600_3moments.jpg` 同一場隔 0.7 秒三張（地圖區），非行動的單位有動（差異集中在單位上）。

出圖：Playwright＋系統 Chrome（非無頭），腳本放在 scratchpad 沒進 repo。

## 3. 驗收

| 項目 | 結果 |
|---|---|
| 新測試 `client/src/render/idleWeapons.test.ts`（10 項） | 15 種都有定義、循環長度照樣張；相位固定值、同 ID 同時鐘同一格、一個循環後回同一格、不呼叫 `Math.random`；9 個 ID 相位兩兩不同；減少動態姿勢＝站好；15 種 × 4 方向一個循環貼圖鍵 ≤ 8（法杖、魔導劍的光不進鍵、> 32 種值；其他光 ≤ 8）；**15 種 × 8 格 × 東／西／正／背：作用端在畫布內、手在握把上（像素，照 `qSelfTest` 的 gripTest，朝西只量作用端，同樣張）**；疊加層錨點每格都量得到、在畫布內、杖頭光在作用端；接上 `IdleMotion`：非行動者一循環 ≤ 8 種貼圖、兩次跑結果相同；行動者不播；減少動態／關待機時每人換回站好一次之後不動 |
| `qSelfTest.test.ts`、`inkWeaponFrame.test.ts` | 照跑、沒改，全過 |
| vitest 全量 | 252 檔、3162 項全過 |
| 快照 | 沒有重產（`inkDollSnapshot` 沒變） |
| `tsc --noEmit`、`vite build` | 過（只有原本的 chunk 大小提醒） |
| 排版煙霧檢查 1600×900、1040×624、800×600 | 三個都 12 PASS、1 FAIL：「戰鬥：四角飾件沒有壓到內容」（主角卡左下飾件 × 技能晶片），**main 既有的舊 FAIL**，本段沒動 HTML／CSS |
| Python | 沒動，沒跑 |
| 效能（12 人同時待機的 FPS） | **沒量**（6R-F 的量法要另開；實機戰場目測不卡）。貼圖每人最多 8 × 朝向張，走既有 LRU 與 `holdFor` 釘選 |

## 4. 待 PM 決定

1. **法球的光與浮沉放進 8 格貼圖（量化），不走疊加層**：需求寫「法球浮沉、光是疊加層，不量化」。試做疊加層時發現樣張裡**持球的手畫在法球上面**，疊加層畫在小人上方會把手蓋掉（見改動前的對照，已改掉）；所以法球改成跟著 8 格換貼圖（每格光暈透明度差約 0.12、上下差約 0.3 像素，實機看不出階梯）。法杖、魔導劍照需求走疊加層。要堅持法球不量化，就得把法球拆到手的下層另畫，工作量另估。補充：遊戲資料裡法球只在副手（`off_hand: orb`），主手沒有法球，**目前遊戲裡不會出現法球待機**；15 種裡刀（saber）同樣沒有資料會產生。
2. **呼吸不疊兩次**：樣張每種（拳套以外）都疊一個 bob 呼吸；遊戲的呼吸已是 6M-4 的垂直縮放（不換貼圖），所以遊戲版拿掉樣張的 bob（`breath: false`），拳套的跳躍照留。畫廊 `mode=sample` 仍是樣張算法。
3. **劍盾的判定範圍**：副手是盾、主手是劍／刀／匕首／斧／鎚 → 劍盾；長槍、鐮等雙手武器＋盾（Q 版改單手握）照該武器自己的待機。匕首、斧、鎚沒有專屬待機，照劍。
4. **只在戰場播**：實地地圖（主城、探索，有 `ambient` 場景）照 6M-4／6Q-1 的 NPC 小動作，不播武器待機（需求寫「戰鬥中沒輪到行動」）。
5. **魔導劍背面**不疊光（劍被身體擋住），背面的符文光跟著 8 格放進貼圖。
6. 疊加層的魔導劍光是「兩圈半透明的矩形」近似 shadowBlur，和樣張的模糊邊略有不同（遊戲裡約 1 像素寬，看不太出來）。
7. **效能沒量**（見第 3 節）；若要照 6R-F 量 12 人同時待機的 FPS，排到下一段順手做。

## 5. commit

- `55524e4a` feat(client): QK-7 weapon-specific idle (15 kinds, 8-frame quantize, glow overlay)
- `cc3f267f` test(client): QK-7 weapon idle determinism, quantize, reduced motion, per-frame selfTest
- `a425c455` fix(client): QK-7 orb idle baked in 8 frames, staff halo drawn by overlay
- `98b8ab98` docs(art): QK-7 idle gallery set and sample-vs-game gif
- 戰場截圖與本報告各一個 commit（見 `git log`）
