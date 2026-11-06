# Phase 6H-1 報告：打擊感（停頓分級、三種微震、最後一擊放慢）＋遊戲內「減少動態」開關

實作者，2026-11-04。

規格依據：
- 開發 PM 派工的 6H-1 六點；
- `docs/archive/art/打擊感移植需求.md`（第 2～4 節）；
- `docs/archive/art/6R-F檢查.md` 待決 1（遊戲內減少動態開關）。

開工時 worktree 已含 `b6d7582f`（6R-F），不用合併。

改動範圍：
- 只改 `client/`，另外加了截圖和這份報告；
- 沒有改 Python、內容資料、數值、規則或 API；
- 沒有新增相依；沒有用原生 `title=`；
- 不用 `Math.random`，也不讀時鐘決定效果。

## 做了什麼

### 1. 停頓依扣血比例分級（`battle/impact.ts`）

- 比例 ＝ `damage_dealt` 的 `(hp_before − hp_after) × 1000 ÷ max_hp`（‰，取整數下限）；一下打多人時取最大的。
  - 最大 HP 取自這一步結束時的畫面。
  - 事件沒有 `hp_before`／`hp_after` 時當作 0。
- 分級：

  | 比例 | 停頓 |
  |---|---|
  | 未滿 10% | 0 |
  | 10%～未滿 25% | 40 ms |
  | 25%～未滿 50% | 70 ms |
  | 50% 以上，或暴擊 | 100 ms |

- 同一刻只停一次，取以下最長的，且每次不超過 100 ms：
  - 分級；
  - 6N-5 的特殊結果：擊殺 100、格擋 60；
  - 最後一擊：第 3 級。
- 一步加起來最多 200 ms；超過時後面的縮短，再後面的不停。
- 照舊跟著播放速度縮放（`scaleVfx`）；略過時播放計畫沒有特效，也就不停。
- 繪製器照舊用效果時鐘停住（`hitStop.ts`）。
- 播放端等命中的時間改用 `hitHoldMs`：
  - 內容是停頓，加上命中點以前放慢的部分；
  - 減少動態時是 0（6R-F 起繪製器在減少動態時不停頓，原本播放端還照樣多等）。
- 傷害數字改照實際時間走（`Effect.clock = "real"`）：停頓、放慢時照常速彈出，不凍結。

### 2. 鏡頭微震只在三種情況（`battle/impact.ts` 的 `shakesFor`、`render/vfxEffects.ts` 的 `impactShakeEffect`）

| 情況 | 判斷 | 幅度／長度（正常速度） |
|---|---|---|
| 重擊 | 停頓第 2、3 級的命中點（含暴擊、最後一擊） | 2 px／120 ms |
| 爆炸 | `object_exploded`、`bomb_exploded`、`rune_removed` 的 `reason: detonated` | 3 px／160 ms |
| Boss 大招 | 6N-5 的判斷（帶 `boss` 標籤、蓄力中、這一步放出技能），震在那一段的命中點 | 4 px／220 ms |

- 拿掉了以下幾種震動：
  - 原本每次命中都震（`vfx.shake` 1 級）；
  - 原本暴擊另外震（2 級）；
  - 原本擊殺另外震。
- `StepVfx.shake` 欄位留著給舊的呼叫端，繪製器不再讀它。
- 震法：
  - 衰減的正弦，左右 28 Hz、上下 22 Hz；
  - 前 70% 由 1 衰減到 0.5，最後 30% 線性收回 0；
  - 相位 ＝ `variantHash("戰鬥鍵:事件 seq")`；
  - 頻率照正常速度的長度算，慢放時震得一樣慢。
- 同時有好幾個時，每一刻取幅度最大的那個，不疊加。一步只有一個震動效果。
- 幅度是畫面像素：場景位移除以地圖縮放（`this.scale`），所以 139% 自動縮放時也是 2／3／4 px。
- 升地形的輕震保留，降到 1 px。
- 版面設定的「畫面震動」關掉時不震；減少動態時不震（效果標 `shake`，被 `reduceEffects` 拿掉）。

### 3. 最後一擊放慢（`battle/impact.ts` 的 `finalBlowOf`；`render/hitStop.ts` 的 `advanceClock(…, slows)`）

- 觸發條件：
  - 這一步擊倒 Boss（`before` 裡帶 `boss` 標籤、還沒倒下的人，這一步 `unit_downed` 或扣到 0）；
  - 或打倒最後一個敵人（這一步有我方勝利的 `battle_ended`，取這一步最後倒下的敵方單位）。
- 做法：
  - 以倒下那人的反應時間（那一段的命中點）為中心，前 120 ms、後 280 ms；
  - 效果時鐘以 0.4 倍走，前後各 60 ms 線性漸變；
  - 正常速度下整段多出約 **0.48 秒**（解析積分，測試鎖在 0.43～0.53 秒）；
  - 命中那一刻疊第 3 級停頓（100 ms）和重擊微震。
- **一場只一次、無狀態**：
  - `before` 裡已經有倒下的 Boss，就表示之前那一步已經放慢過，不再放慢；
  - 沒有 Boss 的戰鬥只有勝利那一步會放慢；
  - 不跨步驟記憶，所以重播、觀戰、重新整理、略過之後都一樣（測試鎖住）。
- 放慢範圍是全場（技能片段、特效、受擊、倒下都照效果時鐘），傷害數字照常速。
- 播放端：
  - 命中前多等放慢的部分；
  - 勝利片段等放慢的後半段（`slowTailMs`）播完才開始。
- 快速播放減半；略過時不做；減少動態時 `reduceVfx` 拿掉 `slow`。

### 4. 減少動態開啟時

- 微震、停頓、放慢全部關閉：
  - `reduceVfx` 拿掉 `stops`、`slow`；
  - 微震效果標 `shake`，不播；
  - `hitHoldMs` 為 0。
- 白閃加長：
  - 重擊、爆炸的目標改成「不換姿勢、不位移」的白閃，長 130 + 40 = 170 ms（跟著播放速度縮放）；
  - 人形、異形換成帶白閃的身體貼圖；形態、召喚物、倒地的人疊白色剪影；
  - 這個效果沒有動態標記，減少動態時照播；
  - 這一步倒下或復活的人不閃，因為白閃會把他們的結果姿勢換回站著。
- 原因：6R-F 起減少動態時，受擊片段直接跳到最後一格，人形、異形其實完全沒有白閃，所以另外加這一個。

### 5. 遊戲內「減少動態」開關

- `client/src/ui/motionPrefs.ts`（新）：
  - 三選一：`system`（跟系統，預設）、`on`、`off`；
  - 存 localStorage `trpg.reducedMotion`（跟系統時刪掉這個鍵），讀寫都包 try/catch；存不了時只在本次有效；
  - `reducedMotion()` ＝ 有效值；`subscribeMotion` 同時聽遊戲內設定和系統設定的改變。
- 所有呼叫點都讀有效值：
  - `world/frameLoop.ts` 的 `prefersReducedMotion`／`subscribeReducedMotion` 改成轉到這個模組；
  - 這樣繪製器、大世界的浮島、升級光柱、狀態與表面動畫、震動開關的預設值都不用改匯入；
  - 繪製器、`MotionAnims`、`MapStage` 本來就有訂閱，改設定時馬上跟著變。
- CSS：
  - `main.tsx` 開機時 `installMotionPrefs(document)`，在 `<html>` 寫 `data-reduced-motion="true|false"`，改設定時更新；
  - 三個 CSS 檔（`skill-bar.css`、`ui/uiMotion.css`、`world/fieldPeople.css`）都改成 `:root[data-reduced-motion="true"] …`；
  - 另外保留 `@media (prefers-reduced-motion: reduce) { :root:not([data-reduced-motion]) … }`，當作 JS 還沒寫屬性前的退路。
- `client/src/ui/MotionSettingsSection.tsx`（新）：
  - 「減少動態」三個單選：跟系統（預設）／開／關；
  - 選「跟系統」時顯示目前系統設定；
  - 放在戰鬥「版面」面板，排在聲音區下面。
- 大世界齒輪沒動，合併時由 PM 接：放一個 `<MotionSettingsSection />` 即可。

### 其他

- `dev/skillGallery.ts`：`#result` 改走 `withSpecials → withImpact`，等命中用 `hitHoldMs`。
- 需求文件第 5 節的開發頁 `#impact` 沒做，派工的六點沒有要求，見待決 6。

## 檔案

| 檔案 | 內容 |
|---|---|
| `client/src/battle/impact.ts`（新） | 分級、停頓、微震、包絡與位移、最後一擊、放慢的倍速與實際時間、`withImpact`、`hitHoldMs`、`slowTailMs` |
| `client/src/battle/vfx.ts` | `VfxImpact`（扣血比例與爆炸，跟著段落排命中點）、`VfxShake`、`VfxSlow`、`StepVfx.impacts／shakes／slow`；`scaleVfx` 一起縮放 |
| `client/src/battle/playback.ts` | `stepSkill` 多接 `heroId`，`withSpecials` 之後接 `withImpact` |
| `client/src/render/hitStop.ts` | `advanceClock` 多一個 `slows` 參數（一小步一小步照倍速走，碰到停頓照舊）、`rateAt` |
| `client/src/render/vfxEffects.ts` | `impactShakeEffect`；`shakeEffect` 改吃幅度 px；`Effect.clock` |
| `client/src/render/BattleRenderer.ts` | 拿掉每次命中都震；微震、放慢的登記；減少動態的白閃（`steadyFlashAt`）；實際時間的傷害數字；升地形 1 px；幅度除以縮放 |
| `client/src/render/resultEffects.ts` | 擊殺不再另外震 |
| `client/src/render/reducedMotion.ts` | `reduceVfx` 也拿掉 `slow`；`REDUCED_FLASH_MS` |
| `client/src/screens/battle/usePlayback.ts` | 等命中用 `hitHoldMs`（減少動態時 0）；勝利等放慢的後半段 |
| `client/src/ui/motionPrefs.ts`（新）、`client/src/ui/MotionSettingsSection.tsx`（新） | 減少動態開關 |
| `client/src/ui/LayoutPanel.tsx` | 聲音區下面放 `MotionSettingsSection` |
| `client/src/world/frameLoop.ts` | 轉到 `motionPrefs` 的有效值 |
| `client/src/main.tsx` | `installMotionPrefs(document)` |
| `client/src/styles/skill-bar.css`、`client/src/ui/uiMotion.css`、`client/src/world/fieldPeople.css` | 同時看 `data-reduced-motion` |
| `client/src/dev/skillGallery.ts` | `#result` 用 `withImpact` |
| 測試 | `battle/impact6h1.test.ts`（新，22 項）、`ui/motionPrefs6h1.test.ts`（新，9 項）、`render/reducedMotion6rf.test.ts`（擊殺不再有 shake） |

## 測試

- 新增 31 項：
  - **分級邊界**：9.9%（99‰）→ 0；10% → 40；24.9% → 40；25% → 70；49.9% → 70；50% → 100；暴擊 → 100。另外驗了用實際扣血、不是 amount；一下打兩人取大的；格擋 60 和分級取長的。
  - **一步上限**：四下都 ≥ 50%，總和 200、每次 ≤ 100；70＋100＋30 的縮短順序。速度縮放：快 ＝ 一半；略過沒有 `vfx` 操作。
  - **微震只在三種**：輕傷、第 1 級不震；第 2、3 級（含暴擊）2 px；小傷害的擊殺有停頓但不震；三種爆炸事件 3 px（不是引爆的符文移除不震）；Boss 大招 4 px 在命中點（沒蓄力的 Boss 不震）；同時兩個取大的、不疊加；包絡；同輸入同輸出；相位照 seq。
  - **最後一擊**：
    - 打倒最後一個敵人有放慢，範圍 −120／+280、漸變 60、0.4 倍，疊 100 ms 停頓與重擊微震；
    - 不是最後一個、我方輸、沒有人倒下的勝利都沒有；
    - 擊倒 Boss 有；之後打倒最後一個沒有；Boss 就是最後一個時只有一次；
    - **整場三步只放慢一次，且重播、只收到後兩步（重新整理、觀戰）、第一步略過都一樣**；
    - 多出約 0.48 秒、快速減半、倍速漸變；
    - 繪製器時鐘實際走的時間和積分相符；停頓和放慢一起時停頓照舊用掉。
  - **減少動態**：沒有停頓、沒有放慢，`hitHoldMs` 為 0；微震效果被拿掉；白閃目標留著。
  - **開關**：
    - 有效值的四種組合；
    - 三個值經由 `frameLoop.prefersReducedMotion` 都生效；
    - 存讀：跟系統不存、不認得的值退回跟系統；
    - 儲存壞掉不出錯；
    - 訂閱者收到改變；
    - 震動預設跟著有效值；
    - `<html>` 屬性；
    - 設定區塊有三個選項、預設勾跟系統、沒有 `title=`；
    - 三個 CSS 檔都同時看屬性。
- 交件前跑過一次 client 全部 vitest：**218 個檔案、2,378 項全部通過**（6R-F 交件時是 215 個檔案、2,326 項）。
- `tsc --noEmit` 通過；`corepack pnpm -C client build` 成功（只有原本就有的 chunk 大小提示）。

## 實機與截圖（`docs/art/`）

- 環境：
  - 自己的伺服器 8322（build 版，存檔與帳號放在 scratchpad）；
  - 自己的無頭 Chrome（CDP 9322，自己的設定檔）。內建瀏覽器的分頁已滿，所以沒用。
- 做法：
  - 開闊平原、雙手劍、點燃＋撞擊；
  - 攔下 API 回應，記錄每一下的扣血比例；
  - 每次結束回合後連拍（約每 105 ms 一張），事後挑。

| 檔案 | 內容 |
|---|---|
| `6h1_settings_panel.jpg` | 戰鬥「版面」面板：聲音區下面的「減少動態：跟系統（預設）／開／關」。實機切三個值：`<html data-reduced-motion>` 分別是 true／false／false，localStorage 分別是 on／off／（刪掉） |
| `6h1_final_blow_burst.jpg` | **最後一擊放慢連拍**（#073～#080）：我方戰士打倒最後一個盜賊弓手。弧光慢慢掃過（約 0.7 秒才收），命中白閃、停頓、微震，倒下，之後才浮出勝利 |
| `6h1_final_blow_hit.jpg` | 命中那一張全畫面（目標白閃、整張場景偏移） |
| `6h1_final_blow_victory.jpg` | 放慢結束、倒下播完後的「勝利」 |
| `6h1_heavy_shake.jpg` | **重擊微震**：地圖右上角放大 4 倍比較。沒在震的一張，地圖邊緣在紅線上；命中那一張，整個場景往左下偏移 |

- 截圖的時間點：
  - 微震與最後一擊兩組，是在「幅度除以地圖縮放」修正**之前**拍的；
  - 當時 139% 自動縮放，畫面上看到約 3 px；
  - 修正後是 2 px。拍到之後才發現縮放的問題，修正後沒再重拍。
- 一般戰鬥中的重擊：
  - 實戰紀錄裡有多次 ≥ 25% 的命中（257‰、263‰ 暴擊、304‰、342‰）；
  - 但連拍時常被浮動卡片遮住，或沒對上那一張，所以重擊微震只用最後一擊那一下示範。
- 實戰中 < 25% 的命中（66‰～216‰）都沒有微震。
- 收尾：
  - 伺服器、無頭 Chrome 都用 TaskStop 停了自己啟動的背景工作，8322、9322 已關；
  - 沒碰 tmp_x、saves/，沒用 8000、8001、8010；
  - 沒碰 8366、8377、8311 和內建瀏覽器的任何分頁。
- 另外：共用的 scratchpad 根目錄裡，`cdp.mjs` 被別的程序改寫過（9333 埠），所以我的腳本改放 `scratchpad/h1/`，沒有動別人的檔案。

## noqa

沒有新增 eslint、ruff 例外。

## 待 PM 決定（都已照最保守的做法做完）

1. **擊殺的停頓保留 6N-5 的 100 ms**：
   - 需求的分級表沒有提擊殺；
   - 所以小傷害的擊殺（例如剩 2 HP 被打到 0）照舊停 100 ms，但不再震；
   - 要改成也照比例分級，把 `impactStops` 裡 `STOP_MS.kill` 那一行拿掉即可。
2. **爆炸事件的名稱**：
   - 需求寫的 `bomb_blast`、`detonate_rune` 是效果種類，不是事件；
   - 改用對應的事件：`bomb_exploded`、`rune_removed` 的 `reason: detonated`，`object_exploded` 照舊；
   - 爆炸的時間排在這一步最後一段的命中點（和 3-28 的符文爆發同一刻）；
   - 只有爆炸、沒有任何傷害與技能的步驟沒有特效，也就不震。
3. **Boss 大招的震動時間**：
   - 6N-5 的變暗在出招開始；
   - 微震放在那一段的命中點（大招「打下去」那一刻）。
4. **減少動態時 Boss 大招**：
   - 需求寫「只保留四周變暗」，但 6R-F 已定減少動態時不變暗（美術 PM 6R-F 檢查通過）；
   - 這段照 6R-F：Boss 大招在減少動態時沒有變暗、沒有白閃。
5. **減少動態的白閃**：
   - 只給重擊、爆炸的目標，170 ms；一般命中仍然沒有白閃（6R-F 的樣子）；
   - 這一步倒下、復活的人不閃。
6. **開發頁 `skill-gallery.html#impact` 沒做**：
   - 需求檢查清單有這項，但派工六點沒列；
   - `#result` 已改走正式的 `withImpact`，可以看到分級停頓與微震，但沒有並排四級、三種震、最後一擊的專頁。
7. **「一場只放慢一次」的邊界**：
   - 判斷是「`before` 裡沒有已倒下的 Boss」；
   - Boss 被復活後再擊倒，會再放慢一次；
   - 兩個 Boss 時只有第一個會放慢。
8. **最後一擊的對象**：
   - 同一步同時擊倒 Boss 和最後一個敵人時，以 Boss 那一下為準；
   - 否則取這一步最後倒下的敵方。
9. **原型數值**：
   - 震動頻率 28／22 Hz；
   - 衰減到一半後線性收回；
   - 放慢實際多出約 0.48 秒；
   - 減少動態的白閃 170 ms（0.85 線性淡掉）。
10. **大世界齒輪**：
    - 照指示沒動。合併 AU-2 時，在大世界的設定面板（共用的 `AudioSettingsPanel` 下面）放 `<MotionSettingsSection />`；
    - 元件不吃參數時自己讀寫 `motionPrefs`。
11. **6R-F 待決 8 的副作用還在**：
    - `usePlayback` 掛載時會 `saveShake(目前值)`，所以第一次開戰鬥時，震動開關的預設值就被存下來了；
    - 之後再切「減少動態」，「畫面震動」勾選框不會跟著變；
    - 實際上減少動態時繪製器一律不震，不影響畫面，只是勾選框的狀態不同步。

## Commit

- `fff9fea7` feat(client): impact feel - tiered hit stops, three-case camera shake, final blow slow-down, in-game reduced motion switch (6H-1)
- `0f6623f3` fix(client): shake amplitude in screen pixels at any map zoom; skill gallery uses tiered stops (6H-1)
- 報告與截圖：最後一個 commit
