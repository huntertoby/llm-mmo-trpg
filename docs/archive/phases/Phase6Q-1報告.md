# Phase 6Q-1 報告：美術驗收打磨

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 第 1 節 6Q-1 列；
- `docs/archive/art/6D-ART2檢查.md` 待決 2、`docs/archive/art/6N-10檢查.md` 第 2 節與待決 3、4；
- 開發 PM 中途追加：`docs/archive/art/6C-ART3檢查.md` 待決 3（d20 點數描邊）。

開工前 `git merge main`、`git merge origin/claude/art-pm-8f4e6d`，都沒有衝突。中途依開發 PM 指示再 merge 一次 main（含 6C-ART3），也沒有衝突。

範圍：只改 `client/`，另外加截圖與這份報告。沒碰 6N-4 的受擊／閃避／格擋／倒下、`skillClips`、`skillSequence`、`textureLru`。`BattleRenderer.ts` 只改了 `idlePose` 一個函式（多一個選填的朝向參數）。

## 交付

| 項目 | 做法 | 檔案 |
|---|---|---|
| 1. 主城金色嵌線 | 主城改用自己的嵌線樣式：比例 1/7 → **1/12**（同一個格子雜湊，鹽值不變）；線色 `rgba(232,187,72,0.45)`、晶光點 `rgba(143,123,255,0.5)`。晶冠城邦照舊 1/7、不透明 | `render/crystalTerrain.ts`（`CAPITAL_INLAY`、`capitalInlayAt`；`crystalTerrain` 多一個選填的樣式參數）、`render/terrainArt.ts` |
| 2. NPC 職業動作轉側面 | 搥打、擦桌子進行中（強度 > 0）畫側面；強度回到 0 就換回原本朝向的貼圖。日常動作（張望、伸懶腰、搔頭、擦汗）不轉。不改 `inkDoll` | `render/npcFidgets.ts`（`WORK_FIDGETS`、`workFacing`、`NpcIdleFrame`）、`render/idleMotion.ts`、`render/ambientModel.ts`（`sides?`）、`world/fieldAmbient.ts`（`workSide`）、`render/BattleRenderer.ts`（`idlePose`） |
| 3. 裝備飛進背包 | 裝備用 `GearIcon` 畫實際外觀（深色圓底金邊）；外觀先找身上穿的 `equipment`、再找背包的 `gear_cards`，依物品 ID 比對；找不到時退回通用的劍。藥水、材料維持布袋 | `world/gainFx.ts`（`gainIconOf`）、`world/GainEffects.tsx`（`GainFlyIcon`）、`ui/uiMotion.css`、dev 頁 `dev/ambientGallery.tsx` 補一筆裝備卡 |
| 4. 燈籠光暈 | 見下方「霧渡鎮確認」 | `render/townArt.ts`（`lanternCenters`、`LANTERN_H`、`BUILDING_ART_T`）、`render/ambientLayer.ts`（`lanternLights`） |
| 追加：d20 描邊 | 64px d20 的點數先 `strokeText` 一圈 `#fff8e8`，再寫深色字。字外那一圈寬 = 字高 14 × 0.2 = 2.8（`lineWidth` 5.6，一半在字外），圓角接合。綠骰、紅骰、金骰、灰骰共用 `drawD20`，全部一起生效；28px 以下不寫字，也不描邊 | `render/storyIconArt.ts`（`D20_HALO`、`D20_HALO_W`、`D20_FONT_PX`）、dev 頁 `dev/storyGallery.tsx` 的 `#icons` 多綠、紅兩顆 |

### 2 的細節：轉向哪一邊

1. NPC 本來就是側面（東、西）：不轉，貼圖鍵和 6N-10 一樣。
2. 否則朝工作的設施：在 2 格內、身分對應的設施裡取最近的一個（排序：距離 → y → x → 種類），在東邊就朝東、在西邊就朝西。
3. 設施在同一欄（正上方或正下方）：照單位 ID 的雜湊定東或西，同一個人永遠同一側。

- 全部是純函式、確定性，沒有 `Math.random`，也不讀時鐘。
- 側面的貼圖鍵後面多 `|east`、`|west`，和正面的姿勢貼圖分開。
- 底圈的朝向箭頭照規則的朝向，不動（只換身體貼圖）。

### 4 的細節：霧渡鎮確認（合併後的 main）

6N-10 報告第 7 點的疑慮是：光暈照 `townArt` 的立面高度另外算一次，6D-ART2 改了屋頂列數之後可能對不上。

查過的結果：
- 6D-ART2 的屋頂讓位（`roof: 0`）讓畫布原點跟著往下移，立面還是貼在建築最下一列。
- 所以舊的公式其實沒有錯位。

為了以後不再分兩處算：
- 改成 `townArt.lanternCenters(spec)` 一個公式；
- `whiteHouse` 畫燈籠、`ambientLayer` 算光暈都用它；
- 光暈再照 `sceneryLayer` 放建築的方式（`(x, y − 屋頂列數)` 格、跟著最下一列的抬高）換成場景座標。
- 閃動的種子照舊，所以 6N-10 的光暈相位不變。

實機截圖（`6q1_mist_ferry.jpg`、`6q1_mist_lantern.jpg`），三件事都確認：
- [x] 建築的門沒有淡黃框（酒館、鐵匠鋪、民宅、南邊的屋子）。
- [x] 渡婆婆站在南邊那棟的屋後，屋頂收在自己的範圍內，人完整可見。
- [x] 酒館兩盞燈籠的光暈中心落在燈籠上（特寫圖）。

## 測試與檢查

**型別與建置**
- `tsc --noEmit` 通過；`vite build` 通過。

**相關前端測試：12 個檔、170 項全部通過**
- 範圍：`regionArt4`、`capitalArt`、`townArt`、`ambient6n10`、`idleClips`、`storyIconArt`、`fieldAmbient`、`gainFx`、`floatCardRule`、`story6c7`，以及兩個新檔。
- 沒跑全量，照規定。

**新測試鎖住的事**
- 嵌線（`regionArt4.test.ts`）：
  - 主城 36×36 格的比例在 1/18～1/9 之間，而且比晶冠少；
  - 沒有嵌線的格子和預設石板完全一樣；
  - 不再出現不透明的金色；
  - 兩種顏色的透明度都低於 0.6；
  - 確定性。
- 側面轉向（`render/npcWorkSide6q1.test.ts`，新）：
  - 120 秒的時間軸上，職業動作的每一刻都是側面，其他時刻沒有朝向；
  - 一般 NPC 從不轉；
  - 動作結束後轉回；
  - 不給朝向時照 6N-10；
  - 朝向的選擇規則；
  - 本來就是側面時貼圖鍵不變；
  - `fieldAmbient` 帶上 `sides`；
  - `IdleMotion` 驅動：側面時 `pose` 不是 null、換回站好時 `facing` 是 undefined。
- 裝備圖示（`gainFx.test.ts`）：
  - 從背包的裝備卡或身上穿的找到外觀；
  - 找不到外觀或沒有背包時退回通用圖示；
  - 裝備畫出 `gear-icon` 的 canvas、沒有 SVG；
  - 其他物品和舊的通用圖示一樣。
- 光暈位置（`render/lanternGlow6q1.test.ts`，新）：
  - 用記錄器抓 `paintBuilding` 實際畫出的燈籠框中心，和 `lanternCenters` 相等（4 種酒館：含屋頂讓位、多扇門、沒有招牌）；
  - 場景座標的公式；
  - 屋頂讓位前後光暈位置相同；
  - 抬高整組平移；
  - 其他 9 種建築沒有燈籠也沒有光暈。
- d20 描邊（`storyIconArt.test.ts`）：
  - 6 種顏色（平常、綠、紅、黃、金、灰）的 64px 骰都是先 `strokeText`、後 `fillText`；
  - 描邊色 `#fff8e8`、寬度是字高的 0.2 倍 × 2；
  - 小骰沒有描邊。

**實機看過一次**
- 自己開的伺服器在 8330 埠，存檔放在 scratchpad 的 `g6q1/saves`，用 build 版。
- 建了兩個測試角色（Tester6Q、Crown6Q），從霧渡鎮傳送到主城，再傳送回霧渡鎮。
- dev 頁用 vite dev。規格要的 5330 被我先前開的一個 vite 佔住（見待決 5），所以改用 5331，`/api` 轉到 8330。設定檔是暫用的，已刪掉。
- 截圖：
  - 用我自己開的無頭 Chrome（CDP，獨立的使用者資料夾在 scratchpad）；
  - 一開始借用了內建瀏覽器分頁 tab-8（6D-ART2 留下、伺服器已關的 8325 分頁），因為分頁已滿；沒有關任何分頁。
- 已關掉：伺服器 8330、無頭 Chrome。

**截圖**

| 檔案 | 內容 |
|---|---|
| `docs/art/6q1_capital_floor.jpg` | 主城廣場：嵌線變稀、變淡，不再像格子標記 |
| `docs/art/6q1_mist_ferry.jpg` | 合併後 main 的霧渡鎮全景：門沒有框、渡婆婆可見、酒館燈籠 |
| `docs/art/6q1_mist_lantern.jpg` | 酒館立面特寫：光暈對準兩盞燈籠 |
| `docs/art/6q1_d20.jpg` | dev 頁 `#icons` 的 d20 一排：一般 15、金 20、灰 1、綠 17、紅 8，64／24／18px |
| `docs/art/6q1_d20_roll.jpg` | dev 頁擲骰結果：成功的綠骰 14 有描邊 |

## 待 PM 決定

1. **實機繪製器會壞（main 既有問題，不是這段造成的）**：霧渡鎮與主城開著待機動畫時，幾秒內就會出現 `[BattleRenderer] 戰場繪製失敗，重建繪製器`。
   - 錯誤訊息是 `Cannot read properties of null (reading 'uid')`，有時是 `'alphaMode'`。
   - 我在除錯時查到：出事的是某個單位的 `body` 精靈，它的貼圖已經被銷毀。
   - 推測原因：6N-3 的 `textureLru` 在重畫場景之間淘汰了「還掛在畫面上、但沒被釘住」的待機姿勢貼圖。6N-10 讓街上 NPC 的姿勢貼圖變多，所以更容易遇到。
   - 6N-10 合併點 `1d9013a6` 的 build 也會重現，所以不是 6Q-1 的改動造成的。
   - 截圖時我用「減少動態」（`prefers-reduced-motion`）避開；這樣截出來的 NPC 都是站好的樣子，光暈停在第 0 毫秒。
   - `textureLru` 在 6N-4 的範圍內，我沒有動。建議交給 6N-4，或另開一段處理。
2. **側面轉向只在實機的待機時間軸測過，沒有截到圖**：因為第 1 點，截圖時待機是關的。時間軸與驅動都有單元測試。
3. **描邊寬度的解讀**：「寬度約字高 0.2 倍」我解讀成露在字外的那一圈，所以 `lineWidth` 是 5.6（48 格畫布座標）。如果要的是線寬本身 0.2 倍，改 `D20_HALO_W` 一行即可。
4. **嵌線的透明度**（線 0.45、晶光點 0.5）是原型數值。
5. **我留下兩個 vite 程序沒關掉**：PID 15512 在 5330 埠，PID 22204 在 5331 埠，都是我這段開的 vite。
   - `TaskStop` 只停掉了外層的 shell，子程序沒有一起結束；
   - 我用 PID 關閉時被權限擋下。
   - 請 PM 確認後關掉這兩個 PID。
