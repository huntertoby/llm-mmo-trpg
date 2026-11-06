# Phase 6M-3 報告：動畫③　走路、跑步、潛行片段＋高低差＋接上戰場與探索

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6M-3 列，含併入的 6M-2 驗收結論；
- `docs/archive/art/動畫移植需求.md` 第 2、3、7 節；
- `docs/archive/art/6M-2檢查.md`；
- 樣張 `docs/art/sample/anim.js` 的 `walkPose`、`heightRow`、`CLIP.leap`、`figure`（白閃）。

開工前先 `git merge main`，沒有衝突，已經含 6M-1、6M-2、6A-4d、6B-4。只改了 `client/`，另外加了截圖和這份報告。

## 交付

| 項目 | 檔案 |
|---|---|
| 移動片段（純函式） | `client/src/render/motionClips.ts`（新）：<br>• `gaitPose`、`gaitPoseAt`、`GAITS`：走路、跑步、潛行<br>• `legFrame`、`climbMode`：高低差<br>• `proneBody`、`PRONE_POSE`：倒地<br>• `quantizePhase`、`quantizePose`、`poseKey`：快取 |
| 戰場逐格走 | `render/BattleRenderer.ts`：<br>• `animateWalk` 每格播走路片段，衝刺過的人播跑步<br>• 新增 `stepLeg`、`poseBody`、`restBody`<br>• 滑倒只有小人倒下 |
| 跑步判定 | `battle/walkAnim.ts`：`Gait`、`WalkAnim.gait`、`trackRunning`<br>`battle/playback.ts`：`playbackPlan(..., running)`<br>`screens/battle/usePlayback.ts`：跨回應保留同一個集合 |
| 探索 | `render/BattleRenderer.ts` 的 `animate`：步行（`walk`）播走路、衝鋒（`dash`）播跑步，轉彎時轉身，左右腳交替<br>`world/peopleWalk.ts`（新）：NPC、敵群走一格<br>`world/WorldField.tsx`：只加了「套用新畫面前播 NPC、敵群走一格」這一段 |
| 倒地持續躺著 | `render/unitSprite.ts`：`isProne`、`bodyTexture`、`bodyNodes`、`BODY_LABEL`；重畫時倒地狀態照骨架躺著 |
| 弓的朝向 | `render/inkGear.ts`：側面的弓左右翻過來<br>`render/inkWeaponFrame.ts`：側面作用端改成 `(6, 0)` |
| 刃點 | `render/inkWeaponFrame.ts`：`weaponEdge`、`weaponStrikePoint`；`probe` 多回報 `edge` |
| 異形白閃只閃剪影 | `render/creaturePose.ts`：`whiteSilhouette`、`creaturePoseKey`、`quantizeCreaturePose`<br>`render/inkCreature.ts`：`renderCreatureCanvas(..., pose)` 疊白色剪影；`drawCreature(..., ground)`<br>`render/vfxEffects.ts`：`hitEffects(..., circle)`<br>`BattleRenderer.playVfx`：異形受擊播「受擊」片段，不畫白圓 |
| 快取鍵 | `render/artTextures.ts`：`figure(..., pose)`、`creature(..., pose)` 的鍵加上量化後的姿勢 |
| 落地揚塵 | `render/walkFx.ts`：`landingDust` |
| dev 頁 | `client/walk-gallery.html`、`src/dev/walkGallery.ts`（新）：`#walk`、`#jump`、`#run`、`#prone`、`#perf`，`?cell=` 調整格子大小<br>`src/dev/dollGallery.ts`：新增第 ⑯ 段（弓）；第 ⑮ 段的白閃改成只閃剪影 |
| 測試（新） | `render/motionClips.test.ts`（16 項）、`render/bodyAnim.test.ts`（10 項）、`battle/walkGait.test.ts`（5 項）、`world/peopleWalk.test.ts`（2 項）<br>`render/inkWeaponFrame.test.ts` 加 4 項 |
| 截圖 | `docs/art/6m3_walk.jpg`、`6m3_jump.jpg`、`6m3_prone.jpg`、`6m3_bow_before_after.jpg`<br>附加：`6m3_creature_flash.jpg` |

## 做法

### 1. 移動片段

公式照樣張 `walkPose`：
- **走路**：髖 ±0.5，膝在後擺時彎，手臂反向擺，起伏 1.2；正面、背面抬腳 3.2、手擺 1.6。
- **跑步**：擺幅 0.75，前傾 0.2，手肘彎，起伏 2.2。
- **潛行**：擺幅 0.35，蹲低 2.5，前傾 0.3，膝多彎 0.5。

時間：
- 走路一步 450 毫秒，跑步 450÷1.6，潛行 450÷0.6；一個循環兩步。
- 片段都是時間的純函式（`gaitPoseAt`）。

其他細節：
- 6M-1 新增的另一隻手 `armF` 和主手反向擺。
- 跑步的手肘彎照 dev 畫廊 ⑬ 的示範（`elbow -0.9`）。
- 潛行的半透明用隱匿的 0.55，只放在 `GAITS.sneak.alpha`。戰場與 HUD 還沒有地方用到潛行，照規格留給 6C-5。

**逐格走的相位**：一格一步（`tilePhase`，每格 π），每格的時間照 6A-4d（120 毫秒，敵方 2 倍速、停頓不變）。
- 這樣每格固定一步，腳步不會打滑。
- 如果照 0.45 秒一步走，一格 120 毫秒時腳幾乎不動。

### 2. 高低差（`legFrame`）

| 情況 | 做法 |
|---|---|
| 同高、差一級 | 走路 |
| 差一級（上） | 前半段髖 +0.4×sin、膝 +0.7×sin，身體從 u ＝ 0.4 起才升 6 |
| 差一級（下） | 同樣從後半段降 6；落地時起伏多 1 |
| 差兩級以上 | 跳躍：拋物線高度 14＋級差×6，往下跳 0.7 倍；姿勢用樣張的 leap；u ＞ 0.85 時落地揚塵 |

- 跳躍時只抬小人本身，底圈、血條跟著地面走。
- 規格是 `TILE_SIZE` 48、`RAISE` 6，有測試鎖住。

### 3. 倒地持續躺著

- 新增 `proneBody(t, facing)`：只轉小人本身（以腳底為軸、往前溜 6），底圈、血條、代號不轉。
  - 方向照 6A-4d：往東走往西倒，往西走往東倒，南北一律往東側倒。
  - 骨架姿勢從走路的最後一個姿勢內插到 `PRONE_POSE`（膝微彎、手攤開）。
- 滑倒的停頓播 t 0→1。
- 有倒地狀態（`prone`）的單位，重畫場景時 `unitSprite` 直接照 t ＝ 1 畫，所以停頓結束、下一步、重新整理之後都持續躺著。
- HP 歸零的倒下（`downed`）照舊用橫躺貼圖，不受影響。
- 異形、形態、召喚物沒有骨架，倒地狀態時只旋轉。

### 4. 併入的三點

- **弓**：側面左右翻過來，弓身朝前、弓弦朝自己；正面、背面不變。
  - 側面的作用端改成 `(6, 0)`，拉弦往自己的方向。
  - 「站好時側面作用端不朝後」的測試，弓不再是例外。
- **刃點**：
  - 斧取主刃刃口 (9.4, −20.6)，戟取斧刃刃口中點 (8.5, −42.4)，鐮取內彎刃口的中段 (11, −28)。座標和作用端相同，都是現有座標、握把在原點。
  - `weaponStrikePoint` 有刃點用刃點，否則用作用端。
  - 測試：刃點在輪廓上（1.5px 內）、在柄的側邊、出招瞬間在手的前方。
- **異形白閃**：另畫一次不含地上影子的身體，`whiteSilhouette` 把顏色變白、不透明度 × flash，再以像素對齊疊回貼圖，等於樣張的 `brightness(0) invert(1) opacity(f)`。
  - 戰場上異形受擊時不畫原本的白圓，改播 6M-2 的「受擊」片段（往後彈、仰、白閃）。人形照舊，見待決 4。
  - 瀏覽器實測（狼，2 倍解析度）：白閃前後有顏色的像素都是 3541 個，剪影外沒有任何像素變白；身體的平均 R 值從 100 變成 226。

## 快取策略（6M-1 待決 5）

**決定：姿勢量化後放進快取鍵。**
- 相位每循環量化成 16 級，數值量化到 0.02，鍵用 `poseKey`。
- 同樣的裝備、朝向、姿勢共用一張貼圖。
- 一格最多 8 到 9 張貼圖（有測試鎖住）。
- 動畫中產生的貼圖會在下一次重畫場景時自動回收（`ArtTextures.endFrame`）。

沒給姿勢時，鍵和畫法都和之前相同。

**為什麼不逐格直接畫**：逐格直接畫的話，每個走路的人每幀都要重畫一張紙娃娃，再上傳成貼圖；同一個循環的姿勢也無法重用。

**FPS 量測**（`walk-gallery.html#perf`）：
- 場地：12×12 戰場、8 個單位，含異形和倒地的人。
- 方式：正常速度（每格 120 毫秒），4 個人一直來回走（平地、上下一級、跳上跳下兩級、跑步、異形），和靜止時比較。
- 環境：無頭 Chrome，軟體繪圖（swiftshader），dpr 1。

| 格子大小 | 靜止 FPS | 4 人走 FPS | p95 幀時間 | 超過 50ms 的幀 |
|---|---|---|---|---|
| 52px | 60 | 56～56.5 | 16.8ms（兩者相同） | 6 秒內 2～5 幀，都是第一次產生姿勢貼圖時 |
| 88px | 52.8 | 43.4 | 33.4～33.5ms | — |

- 52px 時大致不掉；88px 在軟體繪圖下掉得比較多，實機 GPU 應該更好，但這次沒有量實機。
- 快取最多 281 張，下次重畫場景時回收。

## 快照變更

只有一項：`inkDollSnapshot.test.ts` 的 `main:bow`（朝東、朝西兩個雜湊）。

前後對照：`docs/art/6m3_bow_before_after.jpg`。

其餘沒設姿勢的快照全部不變，包括：
- 所有人形範本；
- 10 族；
- 其他 44 種武器形制、成對武器、副手；
- 異形的指令流快照。

## 截圖（`docs/art/`）

| 檔案 | 內容 |
|---|---|
| `6m3_walk.jpg` | 平地走路的中途；同一張圖也看得到持續躺著的倒地單位 D、b |
| `6m3_jump.jpg` | 從平地跳上兩級高台的最高點：腿收起來，底圈留在地上 |
| `6m3_prone.jpg` | 走兩格後在冰上滑倒，快倒平的時候；另外兩個倒地狀態的單位持續躺著 |
| `6m3_bow_before_after.jpg` | 弓修正前後的對照 |
| `6m3_creature_flash.jpg`（附加） | 畫廊 ⑮ 的異形受擊：0ms 時只有剪影變白，影子和格子不變白 |

截圖做法：
- vite 開在 5307 埠，用 dev 頁（不需要伺服器）。
- 用無頭 Chrome（暫存設定檔，DevTools 協定）截圖。
- 截圖用的走路放慢：每格 2.4 秒或 1.6 秒。
- vite 和 Chrome 都是自己開的，用完都已經停掉。

## 測試結果

- `vitest run src/render src/battle src/world src/dev`：126 個檔案、1335 項全部通過。
- `tsc --noEmit` 通過。
- `pnpm build` 成功，只有原本就有的 chunk 大小提示。
- 沒有跑全量。

## 待 PM 決定（都已照最保守的做法做完）

1. **逐格走的相位**：一格一步。每格的時間照 6A-4d 的 120 毫秒；跑步也沒有縮短每格時間，只換片段。
2. **衝刺的判定**：
   - 前端依事件記住「這個回合跑過」的單位：`unit_ran` 加入，同一人的 `turn_started`／`turn_ended` 移除。
   - 重新整理頁面後會忘記，之後的步行照走路播。
   - 衝鋒（`dash`）也播跑步。
   - 跳躍類位移（`leap`）、推拉、傳送照舊。
3. **潛行**：只提供片段和半透明數值，戰場和探索都還沒有用到，照規格等 6C-5。隱身中的移動也沒有換成潛行片段。
4. **受擊白閃**：
   - 只有異形改成只閃剪影，加上受擊片段；人形照舊畫原本的白圓。
   - 人形要不要也改成只閃剪影，需要美術 PM 決定。
5. **探索的水平速度**：步行照舊等速，不加緩入緩出，配合鏡頭的等速平移。戰場維持 6A-4d 的每格緩入緩出。
6. **NPC、敵群**：只有位置差一格（上下左右）才播走路，而且在主角走完那一段、套用新畫面之前播；差更多格時照舊直接換位置。
7. **倒地的畫法**：
   - `PRONE_POSE`、往前溜 6、轉 1.35 rad 是我定的原型數值。
   - 倒下的身體會蓋到代號小標。
   - `walkAnim.ts` 的 `slipPose`（整個單位一起轉）已經不用了；原本的測試還在，函式先保留。
8. **形態與召喚物沒有骨架**：走路時照舊整個平移，跳躍時一起抬高。
9. **刃點座標**：取刃口的中點，是我從現有輪廓挑的點。技能特效批如果想要刃面的中心，再調 `inkWeaponFrame.ts` 的 `EDGE` 即可。
10. **FPS**：這次只在無頭軟體繪圖量過，88px 格時從 52.8 掉到 43.4；實機 GPU 沒有量。

沒有新增 eslint 例外，也沒有新增相依套件。

## Commit

- `11c89dd2` fix(client): side bow faces belly forward; edge points for axe, halberd, scythe (6M-3)
- `5d107296` feat(client): walk, run, sneak clips with height steps and jumps; prone lies on skeleton; creature hit flashes silhouette (6M-3)
- `fac4d329` feat(client): field NPCs and enemies walk one tile with the walk clip (6M-3)
- `f51ee3c0` fix(client): composite creature flash in pixel space; walk gallery, FPS probe and 6M-3 screenshots
- `3b386a65` refactor(client): only sprite body nodes follow walk poses (6M-3)
- 報告：最後一個 commit
