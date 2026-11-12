# Phase 6R-F 報告：前端整理段（貼圖 hold、減少動態、純函式化）

實作者，2026-11-04。

規格依據：開發 PM 的 Phase 6 後段前端審查摘要「6R-F 範圍」第 1～9 點，加上第 11 點的 `IMMOBILE_STATUSES`。

開工前 worktree 落後 main，先 `git merge --ff-only 00afe7e4`（6N-8 合併）。

改動範圍：
- 只改 `client/`，另外加了截圖和這份報告；
- 沒有改 Python、內容資料、數值或規則；
- 沒有新增相依，沒有用原生 `title=`；
- 審查第 10、12 點（效能、拆 BattleRenderer、ESLint complexity）沒做。

## 逐項

| # | 做了什麼 | 主要檔案 |
|---|---|---|
| 1 | `endFrame` 先 `releaseExcept(這一輪呼叫過 holdFor 的 owner)`：死掉、離場、換地圖的小人，以及殘影（`ghost:`、`ghost2:`、`afterimage:`、`flash:`、`cshadow:`）都放開。`drawUnit` 每一輪對畫到的人 `holdFor(u.id, 身體貼圖)`。殘影改用 `art.uniqueOwner(prefix)`（`prefix#序號`），同一人一步內兩次閃避不互相頂掉 | `artTextures.ts`、`textureLru.ts`、`BattleRenderer.ts`、`reactEffects.ts`、`resultEffects.ts` |
| 2 | `turn()` 新建的小人馬上 `holdBody`；白閃疊層（`overlayHit`、`overlayEffect`）用 `flash:<id>#n` hold，結束時放開。安全網 `setLiveProbe(() => liveSpriteTextures(stage))`：`endFrame` 的 drop、`flushEvicted`（包括 `store` 裡的提前 flush）都會跳過「仍被活著的 Sprite 引用」的貼圖。6N-8 的路徑也查過：`skillVariantPoses` 的衍生片段走 `poseClip → poseBody → setBodyTexture`，本來就會 hold；`clipHitFrame` 只算作用端的位置，不產生貼圖；Z 字殘影改用 uniqueOwner | 同上 |
| 3 | `LevelPillar`：收掉光柱的計時器改成跟著「這一次光柱」（`shown.n`），不跟著 `[view]`。升級後馬上又來一次畫面更新時，不會被清掉而殘留 | `world/GainEffects.tsx` |
| 4 | 減少動態全面生效，見下面的對照表。`Effect.motion` 加上分類標記（`body`／`fx`／`flash`／`shake`／`dim`），`launch()` 一律先經過 `reduceEffects`；`playVfx` 先經過 `reduceVfx`（拿掉停頓和 6N-8 特效層的 `look`）；`clipMove` 在減少動態時回傳 `null`，照舊平移，所以沒有前傾、跳躍弧度、Z 字殘影、空翻。震動開關的預設值改成 `!prefersReducedMotion()`，存過 on／off 時照存的 | `render/reducedMotion.ts`（新）、`vfxEffects.ts`、`BattleRenderer.ts`、`battle/vfxPrefs.ts` |
| 5 | 新增 `battle/viewGrip.ts` 的 `weaponClassInView`、`attackFamilyInView`，從每一步的 `before` 畫面的裝備算（純函式，同一份 view 有快取）。`playbackPlan` 的參數改成 `(unitId, before) => …`，`usePlayback` 不再經過 rendererRef。另外把 `buildDrawModel` 裡「一個人 → UnitDraw」抽成 `unitDrawOf` | `viewGrip.ts`（新）、`playback.ts`、`usePlayback.ts`、`drawModel.ts` |
| 6 | 擊殺的強化改成無狀態：只看本步事件，每一輪取「這一輪第一個倒下的人」（命中點最早）強化一次；輪數用事件的 `round`，沒有時用 `before.round`。`SpecialMemo`、`newSpecialMemo` 都刪掉了 | `specials.ts`、`playback.ts`、`usePlayback.ts`、`dev/skillGallery.ts` |
| 7 | `npcFidgets.npcFidgetPick` 改用 `variantHash`。`reactClips` 的 `dodgeSide`、`victoryPose`、`reactVariant` 已經是 `variantHash`（確認過）。全 client 搜過一遍，另外把 `statusAnim.arcAt` 的 `arc${s % 3}` 也改成 `variantHash`（連號的 n 會規律輪替）。加了原始碼掃描測試，鎖住不能再有 `seedOf(…) % n` 拿來挑變體 | `npcFidgets.ts`、`statusAnim.ts` |
| 8 | `upgradeReact(old, r)` 讓 `addReact` 和 assemble 的 looseReacts 合併共用，`kind`、`seq`、`variant`、`side` 一起升級；升級後的事件沒有 variant 或 side 時就刪掉舊的 | `battle/vfx.ts` |
| 9 | LRU 改成位元組預算 `TEXTURE_BUDGET_BYTES = 256MB`：每張用 canvas 的 `w*h*4` 計算，`set(key, v, bytes)`。另外加了 `bytes`、`pendingBytes`、`peek`、`owners`。異形姿勢的 dx、dy 不再進貼圖鍵，見下方說明 | `textureLru.ts`、`artTextures.ts`、`creaturePose.ts`、`inkCreature.ts`、`unitSprite.ts` |
| 11 | `IMMOBILE_STATUSES` 改成 `isImmobileStatus(id)`：讀 glossary `status_look` 的 `skip_turn` 或 `prevents_move`，另外加上躺著的姿勢 `prone`（`IMMOBILE_POSTURES`，見待決 2）。用真實 glossary 測，結果還是 frozen、prone、root、stun | `battle/feedback.ts` |

### 第 9 點：異形姿勢的位移改成移動節點

- 動畫中的異形改用 `art.creatureBody(r, facing, pose)`：
  - 鍵是 `cb|res|外觀|p:去掉 dx、dy 的姿勢`；
  - 只畫身體（`CreatureLayer = "body"`），不畫影子；
  - 姿勢的伸縮、傾斜、透明度、白閃照舊。
- 位移由 `placeCreatureBody` 處理：
  - 身體節點移到「原位置 ＋ dx·k·r.size（朝西時鏡像）、dy·k·r.size」；
  - 影子用另一張 `art.creatureShadow`，在原位置留一個 `creature-shadow` 節點。這個節點不在 `bodyNodes` 裡，跟原本「影子不跟著姿勢動」一致。
- 站好、倒地圖示照舊用合在一起的原貼圖，影子節點藏起來。
- 為了讓位移不被蓋掉，有幾處身體位置的設定改成先於 `setBody`：`reactEffects.poseCreature`，以及 `resultEffects` 的 rise、recoil、victory（新的 `setCreatureBody`）。
- 和原本畫面的差別只有一處：頭目外光是「身體」和「影子」各自加的，兩者重疊的地方外光的疊法會略有不同（見待決 4）。

## 減少動態對照表

| 動畫 | 減少動態時現在的行為 |
|---|---|
| 暴擊：全畫面閃白 | 不播（`flash`） |
| 擊殺、技能命中、地形升起：震動 | 不播（`shake`）；震動開關的預設也是關 |
| 命中停頓（暴擊、擊殺、格擋） | 不停（`reduceVfx` 拿掉 `stops`） |
| Boss 大招：四周變暗 | 不播（`dim`） |
| 技能身體片段（起手、出招、收勢、被撞倒） | 第一次更新就畫最後一格，播到時間照舊回到站好 |
| 受擊、重擊、格擋、閃避、倒下（人形、異形） | 同上（倒下 ＝ 直接躺好） |
| 白閃疊層（形態、召喚物、倒地的人） | 同上（最後一格白閃為 0） |
| 格擋成功：攻擊者被彈開 | 同上 |
| 勝利：舉手、收刀 | 同上（直接是最後的姿勢）；「勝利」字樣照舊 |
| 復活：站起來 | 同上（直接站好）；綠光圈不畫 |
| 普攻、技能的弧光（slash） | 不畫（`fx`）；命中爆發照舊 |
| 閃避殘影、第二層殘影、Z 字衝刺殘影 | 不畫 |
| 格擋火花、大火花 | 不畫 |
| 片段的特效提示（武器發光、符陣、光點、連線） | 不畫 |
| 位移片段（衝刺前傾、跳躍弧度、空翻、Z 字路線） | 不播，照舊平移到目的地 |
| 6N-8 三層變體 | 起手、原語層跟著身體片段一起跳到結果；特效層（軌跡、爆發形狀、粒子分布）照基本樣子 |
| 飛行物、光束、爆發、受擊白圈 | 照舊（傳達「打到哪裡」） |
| 傷害數字、狀態字 | 照舊（6N-10 已經是減少動態時直接顯示） |
| 待機、環境動態、狀態動畫、表面動態 | 照 6N-9、6N-10 原本的做法（停下） |
| 升級光柱 | 照 6N-10 原本的做法（直接顯示再收掉）；這次修好了殘留 |

## 貼圖快取的數字（實機）

- 環境：自己的伺服器 8355 ＋ vite 5355（暫時設定，已刪除），借內建瀏覽器的 tab-22。
- 量法：dev-only 的 `window.__texStats()`，只在 `import.meta.env.DEV` 時才會掛上。

| 時點 | 張數 | 位元組 | 待銷毀 | 有 hold 的 owner |
|---|---|---|---|---|
| 霧渡鎮剛進來 | 911 | 35.1MB | 0 | 3 |
| 霧渡鎮待機 10 秒 → 100 秒（每 10 秒取一次） | 931 → 935 | 35.9 → 36.2MB | 0 | 3（全程不變） |
| 走到獵戶小屋 | 897 | 31.8MB | 0 | 3 |
| 在獵戶小屋遇敵進戰鬥（第 3 張地圖） | 304 | 11.0MB | 0 | 6 |

- 換地圖後張數和位元組都下降，owner 數沒有一路累加。
- 舊的做法下，換地圖之後上一張地圖的小人 hold 永遠不放，所以會一直累積。
- 預算 256MB，實際只用了約 14%。

**實機的其他結果**
- 城鎮待機約 100 秒，主控台 0 錯誤。
- 戰鬥中出現一條 React dev 警告：「flushSync was called from inside a lifecycle method」（位置在 BattleScreen）。`usePlayback` 的 flushSync 呼叫位置和順序這次沒有改，應該是原本就有的，build 版不會出現。見待決 6。
- 瀏覽器面板在量測時是隱藏的（背景分頁）。ticker 可能被降速，但待機姿勢的張數仍有增加，表示待機有在跑。

## 截圖（`docs/art/`）

- 減少動態的開法：內建瀏覽器沒有 emulateMedia，所以在頁面裡把 `window.matchMedia` 對 `prefers-reduced-motion` 的查詢改成回傳 `matches: true`，再進戰鬥。
- 這樣只影響 JS 端（繪製器、震動預設），CSS 的 `@media` 不受影響。

| 檔案 | 內容 |
|---|---|
| `6rf_reduced_battle_1_enemy_turn.jpg` | 獵戶小屋，敵方先手：山豹猛虎衝撞，鐵壁閃避。只有「閃避」字樣，沒有殘影 |
| `6rf_reduced_battle_2_crit_result.jpg` | 主角火焰爆暴擊 18 點：沒有全畫面閃白、沒有停頓，紀錄照舊 |
| `6rf_reduced_battle_3_kill_crawl.jpg` | 「極慢」速度普攻擊倒霧狼2：數字「擊倒 −6」照常浮出；狼直接躺好（沒有倒下片段），沒有震動 |

## 測試

- 新增 4 個檔案，共 23 項：
  - `render/texHold6rf.test.ts`（6 項）：
    - endFrame 放開沒畫到的 owner；
    - 活著的 Sprite 拿著的貼圖不被 drop、不被 flush，Sprite 拆掉後才銷毀；
    - 超過預算時正在顯示的不被銷毀；
    - 預算以位元組計；
    - uniqueOwner 不互相頂掉；
    - 異形姿勢的位移拆分。
  - `render/reducedMotion6rf.test.ts`（7 項）：
    - 14 類產生器各自標了正確的分類；
    - 減少動態時 flash、shake、dim、fx 一個都不留，節點已銷毀；
    - 身體片段只畫一次 t = 1，到時間照舊回到站好；
    - 不是減少動態時原樣通過；
    - `reduceVfx`；
    - 震動預設跟著系統、存過的值優先（2 項）。
  - `battle/viewGrip6rf.test.ts`（3 項）：
    - 純函式；
    - 看的是 before 不是 after：拿 after 的裝備會挑到不同的弧光；
    - 重播、重新整理、觀戰（只收到後兩步）挑到同一個變體。
  - `battle/cleanup6rf.test.ts`（7 項）：
    - `upgradeReact` 3 項；
    - NPC 挑法 ＝ variantHash；
    - 隔兩次挑到同一個的比例在 20%～47%；
    - 帶電閃光；
    - 原始碼掃描：沒有 `seedOf(…) % n` 拿來挑變體。
- 改了 3 個檔案：
  - `textureLru.test.ts`：600 張的測試換成位元組預算，另加 4 項；
  - `specials.test.ts`：memo 的測試換成「無狀態：每輪第一個倒下的人」，另加「略過、重新整理、觀戰一致」；
  - `missImmobile.test.ts`：改用資料判斷。
- 交件前跑過一次 client 全部 vitest：**215 個檔案、2,326 項全部通過**（6N-8 交件時是 211 個檔案、2,298 項）。
- `tsc --noEmit` 通過；`corepack pnpm -C client build` 成功（只有原本就有的 chunk 大小警告）。
- 第 3 點（GainEffects）沒有元件測試：vitest 跑在 node 環境，沒有 DOM 測試工具，也不能新增相依。

## noqa

沒有新增 eslint、ruff 例外。

## 待 PM 決定

1. **擊殺「同一輪只強化一次」的範圍**
   - 改成無狀態之後，判斷只能看本步事件和 before。
   - 結果是「同一步內每一輪只強化第一個倒下的人」。
   - 同一輪裡分在不同步驟的擊殺（例如我方先殺一個，隊友下一步又殺一個），現在各自都會強化。
   - 畫面資料沒有「這一輪已經有人倒下」的欄位。
   - 要完全照原本的需求「同一輪只強化一次」，需要後端在 view 加欄位（例如單位的 `downed_round`，或 battle 的本輪擊殺數）。這要改 Python，這段沒做。
2. **`prone` 的不能動判斷**
   - 狀態資料裡 `prone` 沒有 `skip_turn`，也沒有 `prevents_move`（它的規則是「移動前要先站起來」）。
   - 但小人畫成躺著，閃不開。
   - 目前前端用 `IMMOBILE_POSTURES = ["prone"]` 保留這一個 ID，理由和畫法的 `PRONE` 相同。
   - 要完全讀資料的話，需要在 statuses.yaml 加一個標記（例如 tags 加 `lying`）。
3. **遊戲內的「減少動態」開關**：照指示沒做；目前只跟著系統的 `prefers-reduced-motion`。
4. **頭目外光**
   - 異形動畫中，身體和影子分成兩張貼圖，外光各自加。
   - 身體的外光蓋在影子上的那一小塊，和原本「先算整張外光再疊上」略有不同。
   - 一般異形完全一樣，只有帶外光的頭目受影響。
   - 要完全一致的話，影子也得照姿勢分張，貼圖鍵又會變多。
5. **戰鬥鍵 ＝ `map_id`**：同一張地圖每一場的變體序列都一樣。後端沒有戰鬥 ID，照指示沒改。
6. **React dev 警告**
   - 實機戰鬥時出現「flushSync was called from inside a lifecycle method」（BattleScreen）。
   - 這次沒動 flushSync，應該是原本就有的，只在 dev 出現。
   - 要不要排查，請 PM 決定。
7. **seedOf 的其他用法沒有改**
   - 以下都是「值」不是「挑變體」，所以留著：
     - `ambientAnim`、`ambientModel`、`surfaceAnim`、`statusAnim.phaseOf` 的相位、位移、強度；
     - `idleClips` 的 `(idHash + n) % len` 是刻意的輪替。
   - 掃描測試只鎖「拿來當索引挑變體」的寫法。
8. **震動預設的寫入時機**
   - `usePlayback` 掛載時就會 `saveShake(目前值)`，所以第一次開戰鬥時，系統設定推出來的預設值就被存下來了。
   - 之後使用者再改系統的減少動態，震動開關不會跟著變（除非手動切）。
   - 這是原本存檔方式的副作用，沒有改。

## 收尾

- 伺服器（8355）、vite（5355）都已停掉：
  - 背景工作用 TaskStop 停；
  - vite 的子程序用自己的 PID 27900 結束。
- 暫時用的 `client/vite.config.6rf.ts` 已刪除，存檔放在 scratchpad。
- 借用的 tab-22 沒有改大小。
- 沒碰 tmp_x、saves/，沒用 8000、8001、8010 埠。
- 沒碰 8388、8399 的分頁或程序。
- 只 commit 在 worktree 分支，沒有 push，也沒有合併。
