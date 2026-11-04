# Phase 6N-9 報告：動畫第二批⑨　狀態動作與地表

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6N-9 列；
- `docs/art/動畫移植需求第二批.md` 第 0 節（共同原則）、第 8 節；
- `docs/art/動畫方案.md` 2.5、2.6（冰面滑倒、陷阱夾住屬於 6N-4，這段沒做）。

開工前 `git merge main` 沒有衝突，已含 `docs/art/動畫移植需求第二批.md`。

只改了 `client/`，另外加了截圖和這份報告。
- 沒碰串接器、技能播放（`client/src/battle`）、`render` 的技能片段；
- 沒碰 `terrainArt`、`objectArt`、建築畫法、事件卡插圖；
- 沒新增伺服器欄位，也沒新增相依套件。

## 交付

| 項目 | 檔案 |
|---|---|
| 狀態動作（純函式） | `render/statusAnim.ts`（新）：<br>• `statusAnimKinds`：判斷 8 種狀態<br>• `statusFrame`：時間 → 粒子與身體動作<br>• `arcAt`、`lockLegs`、`isFrozenLook`、`isRootedLook`<br>• `staticRemainder`：靜態特效裡改成動畫的部分拿掉之後的樣子 |
| 地表動畫（純函式） | `render/surfaceAnim.ts`（新）：<br>• `surfaceChanges`、`sameBoard`：比較前後畫面的表面<br>• `spreadSteps`：火蔓延的順序<br>• `revealAt`、`changeTotalMs`：出現、消失的時間軸<br>• `surfaceShimmer`：水、油、火面的持續動態 |
| 小貼圖 | `render/statusAnimArt.ts`（新）：狀態 14 張、地表 3 張，全場共用 |
| 驅動 | `render/statusAnimLayer.ts`（新）：`StatusAnimator`<br>`render/surfaceAnimLayer.ts`（新）：`SurfaceAnimator`<br>`render/motionAnims.ts`（新）：把兩者包成一個，處理 reduced-motion 與播放速度 |
| 接線 | `render/BattleRenderer.ts` 加 8 行：<br>• import 2 行；<br>• 欄位 `motion`；<br>• ticker 一行、`start`／`stop`；<br>• `draw` 裡的 `drawSurfaces`、`drawUnits`；<br>• `surfaceHost`（一個小物件）<br>`render/unitSprite.ts`：身上特效（`over`）精靈加標籤 `FX_OVER_LABEL`；`effectTexture` 改名匯出成 `effectTextureOf`<br>`render/idleMotion.ts`：冰凍判定改用 `isFrozenLook`；定身時小動作用 `idleFrameFor`（鎖腳） |
| dev 頁 | `client/status-anim-gallery.html`、`src/dev/statusAnimGallery.ts`（新）：`#status`、`#spread`（`?still` 給截圖用）、`#stack`、`#perf`，另有 `?cell=`、`?anim=0.1` |
| 測試（新） | `render/statusAnim.test.ts`（27 項）、`render/surfaceAnim.test.ts`（17 項） |
| 截圖 | `docs/art/6n9_status.jpg`、`docs/art/6n9_spread.jpg`、`docs/art/6n9_stack.jpg` |

WorldField 沒改：探索也是用 `BattleRenderer` 畫，所以自動套用。

## 做法

### 1. 狀態動作（疊在現有的圖示與身上特效上）

觸發只看畫面資料：狀態 ID、狀態外觀旗標（和 3-18b 的 `bodyEffects` 同一套判定）、站的格子的表面。

| 狀態 | 觸發 | 動作 |
|---|---|---|
| 燃燒 | 持續傷害的元素是火 | 身上 3 個火苗，形狀 4 張、90ms 輪播，加上縮放與搖擺；每 1.6 秒從頭頂冒一次煙（0.9 秒） |
| 冰凍 | `bodyEffects.frozen` | 一道斜的反光每 2.4 秒掃過冰塊；**不呼吸、不做小動作**，身體完全不動 |
| 中毒 | 持續傷害是毒 | 頭上 3 顆綠泡泡往上冒（1.2 秒）；身體染淡綠 `0xc9f2c0` |
| 暈眩 | `bodyEffects.stunned` | 頭上的圈加 3 顆星，1.25 秒轉一圈，轉到後面時變淡；身體以腳底為軸左右搖 ±0.07 rad（0.9 秒） |
| 定身 | `bodyEffects.noMove` | 腳邊兩條藤輕輕擺（靜態的藤和冰圈照舊）；小動作拿掉腿與起伏的欄位（`bob`、`hip*`、`knee*`、`lift*`），**只有上半身動** |
| 隱身 | `concealed` | 照舊 0.55 半透明，再乘 0.64～1 倍閃爍，加輕微扭曲（skew ±0.05） |
| 潮濕 | 站在水面上 | 兩側輪流滴水 |
| 帶電 | 持續傷害是雷，或帶電護盾 `shielded_charged` | 每人 0.9～1.6 秒一個週期，週期開頭閃一道小電弧 140ms；形狀、位置照「ID:第幾次」雜湊 |

**和靜態特效的關係**
- 暈眩的星星與圈、火與毒的腳邊粒子本來畫在靜態貼圖裡。動畫開著時，那張貼圖換成拿掉這幾樣的版本（`staticRemainder`），改由動畫畫會動的版本，所以不會畫兩份。
- 其他的照舊畫在靜態貼圖：冰塊、護盾泡泡、藤、流血的血滴等。
- reduced-motion 時換回原本的靜態貼圖，畫面和 6N-9 之前完全一樣。

**確定性**
- 相位用 `inkStyle.seedOf`（FNV-1a）算，鍵是「單位 ID:種類」。
- 不用 `Math.random`、不讀時鐘，有測試監看。
- 時鐘是 ticker 累加的毫秒。

**和其他動畫的分工**
- 正在走、受擊、進出門的人（待機的 `hold`）不動身體，粒子照畫。
- 倒地的人不搖。
- 走路轉彎時小人會重建，下一幀自動重新掛上。

### 2. 地表

**出現與消失**
- 重畫場景時比較前後兩次的格子表面。
- 只有同一張地圖才播：大小、主題、每格地形都要一樣，換地圖、換戰鬥時不播。
- 有變的格子，在新的貼圖上面疊一張「舊的樣子」（同一套 `ArtTextures.tile`，照舊的畫面資料），用圓形遮罩做轉場：
  - 出現（含換成另一種表面）：中間挖一個洞，越來越大，新的表面從中心擴散開；
  - 消失：舊的樣子往中心縮成一個點；
  - 各 260ms，緩出。
- 轉場中又重畫：表面一樣的接著播，又變了就以新畫面為準。

**火蔓延**
- 同一次重畫新出現的火，沿上下左右從起點擴散，每格延遲 80ms。
- 起點：
  - 和原本就在燒的格子相鄰的新火格；
  - 整塊都不和舊火相鄰時（點燃一整片油），取那塊最中間的格子（到其他格最遠步數最小，同分取 (y, x) 最小）。
- 延遲最多排 12 格。
- 還沒燒到的格子，火面光暈跟著擴散的程度淡入。

**持續動態**
- 水面：兩條反光線，5.2 秒飄過一格，兩端淡出。
- 油面：一塊虹彩光斑，色相 6 秒轉一圈，位置慢慢漂。
- 火面：光暈閃動（420ms）。
- 放在那一排的表面裝飾層，跟著格子抬高。
- 相位照格子座標雜湊（`seedOf`）。

**時間**
- 轉場長度乘上 `playback.SPEED_SCALE`（含 `?anim=`）。
- 「略過」不播轉場，直接顯示結果。
- 狀態動作的時鐘也照 `?anim=0.1` 放慢（正式環境倍率是 1）。

### 3. reduced-motion

`motionAnims.ts` 訂閱 `prefers-reduced-motion`（沿用 `world/frameLoop`），設定改變時馬上跟著變。開著時：
- 不畫粒子，身體回原位，身上特效換回靜態貼圖；
- 表面不動，不播轉場。

待機（6M-4）照舊，這段沒改它的行為。

### 4. 貼圖數（照 6M-3 的快取量化）

- 粒子與表面動態只改位置、縮放、透明度、旋轉、染色。
- 唯一會換的是火苗形狀，量化成 4 張。
- 動畫小貼圖固定 **17 張**，全場共用，不放進 `ArtTextures`。
- 會多產生 `ArtTextures` 貼圖的情況：
  - 轉場時「舊的樣子」的地形貼圖，下一次重畫就回收；
  - 「拿掉會動部分」的身上特效貼圖，每種組合一張。

## 效能量測

方式：
- 和 `walk-gallery #idle` 同一種量法，在 `status-anim-gallery.html#perf`；
- 12×12、8 個人都有狀態（5 個人疊兩種）、25 格水油火面，待機照開；
- 動畫關 4 秒 vs. 開 20 秒；
- 無頭 Chrome，dpr 1。

| 項目 | 6M-4 `#idle`（同一台、同一次） | 6N-9 `#perf` |
|---|---|---|
| 52px 格 FPS（關→開） | 60 → 60，p95 16.8ms | 60 → 60，p95 16.8ms |
| 88px 格 FPS（關→開） | 60 → 60，p95 16.8ms | 60 → 60，p95 16.8ms |
| `ArtTextures` 貼圖數（開始 → 20 秒後 → 重畫後） | 150 → 174 → 150 | 154 → 170 → 146 |
| 動畫小貼圖 | — | 17（固定） |
| 粒子精靈 | — | 8 人共 31 個 |

FPS 沒有下降。這次的無頭 Chrome 在 88px 也跑滿 60，6M-3 報告當時 88px 是 52.8，可能是繪圖環境不同，沒有實機另外量。

## 檢查清單

需求第 8 節：
- [x] 8 種狀態都看得出來：測試「8 種都有看得出來的東西」；截圖 `6n9_status.jpg`。
- [x] 冰凍不呼吸，定身時腳不動：
  - 測試「冰凍不待機」「定身時小動作拿掉腿與起伏」「冰凍身體完全不動」；
  - 截圖 `6n9_stack.jpg` 是定身的人小動作最大的時刻。
- [x] 火蔓延的順序照相鄰格：
  - 測試「從舊火那端一格一格」「整片從中間往外」「L 形、兩塊分開時每格都有相鄰格早一步」「最多 12 格」「輸入順序不影響」；
  - 截圖 `6n9_spread.jpg` 是點燃後 300ms。
- [x] FPS 不比 6M-4 的待機量測差太多：同條件下兩者都是 60，見上表。

prompt 要求的其他項目：
- [x] 觸發條件：8 種各一個測試，加上表面的出現、消失、換種類，以及換地圖不播。
- [x] 時間軸：火苗輪播、冒煙、星星週期、搖擺幅度、冰面反光、水滴、帶電閃的比例、轉場的延遲與長度、慢速倍率。
- [x] 確定性：同輸入同輸出，有監看 `Math.random`、`Date.now`、`performance.now`；不同人相位錯開；表面相位照座標。
- [x] reduced-motion：`StatusAnimator` 關掉後身體回原位、不再動；`SurfaceAnimator` 關掉後清掉轉場、之後也不登記。
- [x] 略過：`timeScale = null` 時不播轉場。
- [x] 效能量測：見上。
- [x] 截圖 3 張。

## 截圖（`docs/art/`）

| 檔案 | 內容 |
|---|---|
| `6n9_status.jpg` | 88px 格。上排：燃燒（冒煙中）、冰凍（反光掃過）、中毒（泡泡、偏綠）、暈眩（星星轉）。中排：定身、隱身、潮濕（站在水上滴水）、帶電（電弧閃）。下排：油面虹彩、火面光暈、水面反光線 |
| `6n9_spread.jpg` | 左端的火沿著一排油燒到第 4～5 格（洞正在擴大）；下面一整塊同時點燃，從中間往外燒（角落還是油）；水面消失、冰變水已經播完 |
| `6n9_stack.jpg` | 疊兩種狀態（`#perf` 的場景）：燃燒＋暈眩（身體在搖）、中毒＋定身、定身＋帶電、帶電＋燃燒、中毒＋潮濕 |

截圖做法：
- vite 開在 5323；
- 用無頭 Chrome（暫存設定檔，DevTools 協定）截圖，腳本在 scratchpad `g6n9/`；
- 截圖時停掉 ticker、把時鐘固定在選好的時刻再算繪，只在截圖的分頁裡做，沒改程式。

vite 和 Chrome 都是我自己開的，用完都停了。vite 留下的子程序，用它自己監聽 5323 的 PID 結束，最後確認 5323 沒有在聽。

## 測試結果

- `vitest run src/render src/world src/battle src/dev`：144 個檔案、1586 項全部通過。
- `tsc --noEmit` 通過。
- `vite build` 成功，只有原本就有的 chunk 大小提示。
- 沒有跑全量。

## 待 PM 決定（都已照最保守的做法做完）

1. **「潮濕」「帶電」沒有獨立的狀態**：
   - 潮濕：站在水面上（規則的「站在水上」）；
   - 帶電：持續傷害是雷，或帶電護盾 `shielded_charged`。
   - 不新增欄位。如果要改成別的判定（例如雷屬性的姿態），再告訴我。
2. **火蔓延的起點**：畫面資料裡沒有「從哪一格點燃」。和舊火相鄰的新火格當起點；整塊都沒有時，從那塊最中間的格子往外。
   - 要完全照引擎事件的順序（`surface_changed` 的先後），得改播放流程（6N-1 的檔），所以這段沒做。
3. **讀播放速度**：`motionAnims.ts` 直接讀 `ui/SpeedControl.loadSpeed()`（localStorage）。
   - 沒改 `usePlayback`，因為那是 6N-1 正在改的檔。
   - 之後串接器可以改成由播放流程傳入。
4. **原型數值**：週期、幅度、顏色、轉場 260ms、蔓延最多 12 格都是我定的，列在 `statusAnim.ANIM`、`surfaceAnim.SHIMMER` 等常數。
5. **冰面反光、毒霧等表面動態沒做**：需求只列火、水、油與出現、消失。冰、毒、聖光、黑暗、煙沒有持續動態，只有出現、消失的轉場。
6. **轉場時相鄰格的併塊邊緣直接跳到新形狀**：只有變的那一格有擴散，鄰格的圓角外緣在重畫時直接換。
7. **隱身「我方看得到輪廓」**：照舊是所有人都看到 0.55 半透明，只加閃爍和扭曲；沒有分我方、敵方的畫法。
8. **形態、召喚物、異形**：粒子照人形的身高（34）擺，大體型的異形頭上的星星、泡泡會偏低。
9. **dev 頁另開新檔**：`status-anim-gallery.html`，沒放進 `walkGallery`，避免和 6N-1 的 `#skills` 衝突。

沒有新增 eslint 例外、`noqa`，也沒有新增相依套件。

## Commit

- `58776289` feat(client): status motion and surface animation (fire spread, water, oil, appear/vanish) (6N-9)
- `fb940980` feat(client): status-anim gallery, perf probe and 6N-9 screenshots; shimmer fades in with spread
- 報告：最後一個 commit
