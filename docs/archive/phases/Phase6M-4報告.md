# Phase 6M-4 報告：動畫④　進出門、換地圖、待機（併入美術 PM 檢查兩項）

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6M-4 列；
- `docs/archive/art/動畫移植需求.md` 第 4、5、7 節，`docs/art/動畫方案.md` 2.7；
- 樣張 `docs/art/sample/anim.js` 的 `CLIP.idle`、`CLIP.hit`；
- 開發 PM 中途補的兩項（依據美術 PM 驗收紀錄 `docs/archive/art/6A-4d至6M-3六段檢查.md`，在美術分支 `origin/claude/art-pm-8f4e6d`，只讀、沒有合併）。

開工前 `git merge main`，沒有衝突，已含 6M-3、6B-4。只改了 `client/`，另外加了截圖和這份報告。WorldField 只動了換地圖那一段（`walkPath` 裡套用新畫面前後），沒碰標記、互動、HUD、戰鬥 UI。

## 交付

| 項目 | 檔案 |
|---|---|
| 進出門、換地圖片段（純函式） | `client/src/render/doorClips.ts`（新）：`leaveFrame`、`arriveFrame`、`transitTotalMs` 與時間常數 |
| 換地圖播哪一段、和淡出淡入銜接 | `client/src/world/mapTransit.ts`（新）：`mapTransit`、`arriveKind`、`arriveFacing`、`leaveMap`、`arriveMap`<br>`world/WorldField.tsx`：換地圖時改呼叫 `leaveMap`／`arriveMap`（傳送石等其他情況照舊只淡出 0.22 秒） |
| 待機片段（純函式） | `client/src/render/idleClips.ts`（新）：呼吸 `breathAt`／`breathScale`，小動作 `fidgetAt`，`idleFrame`，FNV-1a `idHash` |
| 待機驅動 | `client/src/render/idleMotion.ts`（新）：`IdleMotion`（`hold`／`release` 成對、`tick`） |
| 繪製器 | `render/BattleRenderer.ts`：<br>• 待機 ticker、`setIdle`、`setIdleClock`、`textureCount`、`nextDraw`<br>• `playLeave`、`playArrive`（進出門、邊緣出口）<br>• `animate` 拆出 `moveOne`，移動、走路、受擊、進出門期間 `hold` 待機<br>• 滑倒後到下次重畫前標記成倒地（`markProne`），待機與受擊不會把人扶起來<br>• 人形受擊 `dollHit`（見「併入兩項」） |
| 併入①　人形受擊只閃剪影 | `render/paperdoll.ts`：`renderFigureCanvas(..., flash)`<br>`render/artTextures.ts`：`figure(..., flash)`，鍵加 `|w:<量化值>`<br>`render/unitSprite.ts`：`BodyFrame.flash`、`hasSkeleton`<br>`render/motionClips.ts`：`humanHit`、`knockOffset`、`quantizeFlash` |
| 併入②　沒字的黑色小圓 | `render/unitSprite.ts`：`marker !== ""` 才畫黑圓與字 |
| dev 頁 | `src/dev/walkGallery.ts`：新增 `#idle`（8 人待機 20 秒的 FPS 與貼圖數）；其他 6M-3 模式關掉待機，量測條件照舊 |
| 測試（新） | `render/idleClips.test.ts`（11 項）、`world/mapTransit.test.ts`（8 項）、`render/dollHit.test.ts`（5 項） |
| 截圖 | `docs/art/6m4_door_enter.jpg`、`docs/art/6m4_town_idle.jpg` |

## 做法

### 1. 進出門、換地圖

時間軸（原型值，`doorClips.ts`）：

| 階段 | 時間 |
|---|---|
| 小人離開片段 `LEAVE_MS` | 200 ms（片段一開始就播） |
| 畫面淡出（6B-3 的 0.22 秒，`STAGE_FADE_MS`） | 片段開始後 80 ms（`FADE_LEAD_MS`）才開始，和片段重疊 |
| 換地圖（commit） | 第 300 ms（max(200, 80＋220)） |
| 畫面淡入＋小人抵達片段 `ARRIVE_MS` | 220 ms，兩者同時 |
| **總長** | **520 ms（≤ 600）**，比 6B-3 原本的 440 ms 多 80 ms |

- **進門**（最後一格是門）：轉身朝走進門的方向，縮小 1 → 0.6、往上移 6、淡出（緩入）。
- **出門**：進到室內時，或從室內出口走出來、站在外面的門上時，播「從門裡出來」：0.6 → 1、往下回 6、淡入（緩出）；朝向照伺服器給的，不轉身。
- **邊緣出口**（最後一格是出口格）：照走的方向再走半格，播走路姿勢並淡出。
- **新地圖從邊緣入口進來**：從入口外一格走進來一步，前半段淡入，走路姿勢接續相位。
- 鏡頭：換地圖時照 6B-6 直接跳（`focus.ms = 0`，沒改）。
- 新地圖要畫好才播抵達片段：繪製器的 `nextDraw` 等下一次 `draw`，最多等 220 ms。
- 小人在畫面外的那一格（從邊緣走進來）會被畫布切掉，看起來就是從邊上走進來。

### 2. 待機

**呼吸**
- 起伏 0.5 虛擬像素、週期 1.6 秒（照需求第 5 節與樣張 `CLIP.idle`）。
- 做法是小人貼圖以腳底為軸的垂直縮放，倍率 1＋起伏÷53（頭頂高度）。**不換貼圖**、腳不離地、地上的影子幾乎不動。
- 樣張用 `bob` 整個人上下平移，那樣腳和影子會跟著浮起來，所以改用縮放，見待決 3。

**小動作**
- 每人 7～11 秒一次，每次 1.2 秒，兩種輪流：
  - 左右張望：重心換腳、手輕擺；
  - 伸懶腰：雙手往上抬、身體往上拉。
- 強度 sin 曲線量化成 4 級，同裝備、同朝向的人共用貼圖。

**相位錯開**
- 相位、間隔、偏移、哪一種，全部用單位 ID 的 FNV-1a 雜湊算。
- 確定性：不用 `Math.random`、不用內建 hash。
- 時鐘是 ticker 累加的毫秒，只影響畫面。

**套用範圍**
- 探索的主角、NPC、朋友影子，以及戰場單位，都經過同一個 `BattleRenderer`，所以全部套用。
- 不套用：正在移動、受擊、進出門的人（`hold`），以及倒地、冰凍（動畫方案 2.7「冰凍不呼吸」）。
- 小動作只有紙娃娃人形才有；異形、形態、召喚物只呼吸。

**快照不受影響**
- 站好的貼圖照舊是 `art.figure(..., null)`，「沒設姿勢」的路徑沒有改。
- 小動作走的是另外的有姿勢路徑。
- 呼吸是 Pixi 節點的縮放，不進畫布指令流。
- `inkDollSnapshot`、`creaturePose` 的快照全部沒變。

### 3. 效能（照 6M-3 的量化快取）

量測方式：
- `walk-gallery.html#idle`：12×12 戰場、8 個單位（含異形、倒地）；
- 先關掉待機量 4 秒，再打開量 20 秒；
- 無頭 Chrome，dpr 1。

| 格子 | 待機關 FPS／p95 | 待機開 20 秒 FPS／p95 | 貼圖數：開始 → 20 秒後 → 重畫一次後 |
|---|---|---|---|
| 52px | 60／16.8ms | 60／16.8ms | 150 → 174 → 150 |
| 88px | 60／16.8ms | 60／16.8ms | 150 → 174 → 150 |

- 20 秒只多 24 張貼圖（小動作的量化姿勢）。
- 呼吸不產生貼圖。
- 下次重畫場景時，`ArtTextures.endFrame` 會全部回收。
- 實際遊戲裡（霧渡鎮 3 人）15 秒換了 40 次貼圖，每幀最多換一次，都是快取命中或第一次產生。

## 併入美術 PM 檢查的兩項

### ① 人形受擊改成剪影白閃（和 6M-3 異形一致）

**片段**：照樣張 `CLIP.hit`，360 ms。
- 仰一下（lean −0.3）、主手往後甩（arm −0.5）；
- 往後彈 7（往面向的反方向；南北向有透視，只走一半）；
- 白閃開頭 0.85，播到 1/4 時消失。

**白閃做法**：
- `renderFigureCanvas` 在 flash ＞ 0 時，另畫一次不含地上影子的身體（`ground = false`）；
- 用 `whiteSilhouette` 變成白色剪影（不透明度 × flash）；
- 重設變換後以像素對齊疊回去；
- 外光（史詩、傳說）不閃。
- 白閃量化到 0.05，貼圖鍵加 `|w:`。**沒有白閃時鍵和畫法都不變**。

**套用範圍**：
- 戰場上有紙娃娃骨架、沒有倒地的人形受擊時，不畫原本的白圓，改播這個片段。
- 形態、召喚物、倒地的人照舊畫白圓（沒有骨架可以閃，見待決 6）。

**像素測試**（`dollHit.test.ts`）：
- 疊回去的剪影只在身體的像素上變白，剪影外完全透明，不透明度 ＝ 原本 × 0.85；
- 白閃的身體少畫地上的影子、沒有整格的 `fillRect`，疊回前先重設變換；
- 沒有白閃時只產生一張畫布。

### ② 拿掉戰場單位腳邊沒字的黑色小圓

- `unitSprite.ts`：`marker !== ""` 時才畫黑圓和字。
- 戰場本來就用 `BATTLE_DRAW`（`markers: false`），代號是空字串，所以戰場上的黑色小圓全部消失。
- 字母照舊只在滑過單位與行動順序列出現。
- 探索畫面照舊顯示 A／B／C（那邊有字）。
- 測試：沒有代號時比有代號少兩個節點。

### 快照變更

沒有。`inkDollSnapshot.test.ts`、`creaturePose.test.ts` 的快照檔都沒變：
- 白閃只在 flash ＞ 0 時才多畫；
- 黑圓是 Pixi 節點，不在快照範圍。

## 截圖（`docs/art/`）

| 檔案 | 內容 |
|---|---|
| `6m4_door_enter.jpg` | 霧渡鎮，主角走上酒館的門：轉身朝門、縮小、半透明，畫面剛開始淡出 |
| `6m4_town_idle.jpg` | 霧渡鎮街上三個人待機（2.5 倍放大）：主角 A 正在伸懶腰（雙手抬起），柳掌櫃 C 在張望，渡婆婆 B 站著呼吸 |

**做法**
- API 開在 8307、vite 開在 5310，用暫存設定檔（已刪）；存檔放 scratchpad 的暫存資料夾。
- 開發模式建了一個測試角色「阿測」。
- 用無頭 Chrome（暫存設定檔，DevTools 協定）截圖。
- 進門截圖：把那個分頁的計時器、rAF、`performance.now` 與淡出 CSS 放慢 12 倍才抓得到。
- 待機截圖：在分頁裡把待機時鐘固定在 1300 ms（主角伸懶腰、C 張望的時刻）。這兩個做法都只在截圖的分頁裡，沒有改程式。
- 鎮上目前只有 2 個 NPC，所以「多人」只有三個人。
- vite、API、Chrome 都是我自己開的，用完都停了：
  - vite 留下的子程序，用它自己監聽 5310 的 PID 結束；
  - 最後確認 5310、8307 都沒有在聽。

## 測試結果

- `vitest run src/render src/world src/battle src/dev`：131 個檔案、1373 項全部通過。
- `tsc --noEmit` 通過。
- `pnpm build` 成功，只有原本就有的 chunk 大小提示。
- 沒有跑全量。

## 待 PM 決定（都已照最保守的做法做完）

1. **時間軸原型值**：
   - 離開 200 ms，畫面淡出提早 80 ms 重疊，抵達 220 ms，總長 520 ms；
   - 進門縮到 0.6、往上 6；邊緣出口走半格。
2. **門打開的動畫（需求第 4 節「門打開 0.2 秒」）沒做**：門是地圖物件，6M-4 的工作清單沒列。要的話另排一小段。
3. **呼吸用縮放，不用 `bob`**：樣張的 `bob` 會讓腳和影子一起浮起來，改成以腳底為軸的縮放，頭頂起伏同樣 0.5。
4. **小動作的姿勢與頻率是我定的原型值**：
   - 每人 7～11 秒一次、1.2 秒、4 級；
   - 正面伸懶腰雙手抬 3.5、張望手擺 1.2／1。
   - 在正常大小下很輕微，放大才看得清楚。
5. **「跳過」**：探索沒有播放速度設定（需求第 6 節：探索走路不受戰鬥速度影響），所以進出門沒有「跳過」開關。元件卸載時照舊直接結束。
6. **人形受擊的範圍**：
   - 只有紙娃娃骨架、沒有倒地的人形改成剪影白閃；
   - 形態、召喚物、倒地狀態的人照舊畫白圓。
7. **戰鬥重播的確定性**：
   - 待機時鐘是 ticker 累加的毫秒（只影響畫面），同一場戰鬥播兩次時待機相位不保證逐幀相同。
   - 戰鬥結果與事件播放完全不受影響。
   - 截圖或比對可以用 `setIdle(false)`／`setIdleClock`。
8. **出門的判定**：
   - 進門之後到室內，一律播「從門裡出來」；
   - 從室內出口走出來、落在外面的門格上，也播「從門裡出來」；
   - 其他落點播「從對面入口走進來一步」。

沒有新增 eslint 例外、`noqa`，也沒有新增相依套件。

## Commit

- `72997cfa` feat(client): humanoid hit flashes silhouette only; no empty marker tag (6M-4)
- `08cec38f` feat(client): idle breathing and fidgets, door and edge map transitions (6M-4)
- `eac0ada9` feat(client): arrive-from-door clip, idle perf probe and 6M-4 screenshots
- 報告：最後一個 commit
