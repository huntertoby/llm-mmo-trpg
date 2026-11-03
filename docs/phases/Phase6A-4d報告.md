# Phase 6A-4d 報告：戰鬥 D 版④——一格一格走的動畫、特殊地表停頓

實作者，2026-11-04。規格：`docs/phases/Phase6計畫.md` 第 1 節 6A-4d 列；`docs/design/05-戰鬥.md` 5.10（冰面是滑倒：在那一格倒地，只有倒在友軍格才滑回最近的空格，不滑行多格）；`docs/art/戰鬥D版樣張.md` 第 4、6 節（main 上已是新版）。

開工時 worktree 沒有 6A-4c，先 `git merge main`（沒有衝突）。只動 `client/`（另加截圖與本報告）；沒有改伺服器、引擎，也沒有新增相依。引擎事件夠用：走路每一格本來就是一個 `unit_moved`（`mode: walk`），兩格之間的 `surface_entered`、`check_rolled`、`trap_triggered`、傷害與狀態事件就是「在那一格發生的事」；倒在友軍格的滑回是緊接的 `teleport`。前端完全不算規則。

## 1. 交付內容

### 1.1 逐格時間軸（純函式 `client/src/battle/walkAnim.ts`）

- `stepMotions`：一步的事件 → 依序的移動。
  - 同一單位、首尾相接的 `walk` 合成一段走路；每格一段 `leg`，時間 `TILE_STEP_MS` 120ms × 播放速度倍率。
  - 每段記下面向（`facingOf`），轉彎時轉身。
  - 其他位移（推、拉、衝鋒、跳躍、傳送、交換）照舊用 `MoveAnim`。
- **停頓**（`beat`）插在那一格之後：
  - 冰面檢定通過：冰花，不停（0ms），照常走過去；
  - 滑倒（同一人的 `check_rolled` 失敗）：停 450ms；
  - 陷阱（`trap_triggered` 的 `unit_id` 是走路的人）：停 400ms；
  - 火：停 250ms；
  - 油：停 200ms。油沒有自己的事件，所以看這一步開始前的畫面，那一格原本是油就濺油。這只影響畫面。
  - 同一格有好幾種效果時，留最重要的那個：陷阱 ＞ 滑倒 ＞ 火 ＞ 油 ＞ 冰。
- **停頓的數字與狀態圖示**：
  - 停頓後面緊接的傷害、護盾吸收、狀態、抵抗、擊倒，算進那一格。
  - 遇到其他事件（藉機攻擊、反應…）就不再收。
  - 這些回饋改成跳在停頓的那一格，停頓結束才跳出來。
  - 一步結束時的回饋會排除這些事件，不會重複跳數字（`consumed`）。
- **滑回空格**：滑倒之後同一人的 `teleport`（引擎 `_slide_back_if_stacked`）改成 200ms 的短滑行（`slide`），身體保持倒著。沒有滑倒的傳送照舊淡出淡入。
- 其他函式：
  - `easeInOut`：二次緩入緩出；
  - `walkTimeline`、`walkDurationMs`：測試用；
  - `slipPose`：滑倒姿勢。前 35% 腳往前溜，再 35% 以腳底為軸倒下。往東走往西倒，往西走往東倒，南北走往東側倒，避免倒到地圖外；
  - `cameraNudge`：鏡頭偏移。

### 1.2 播放計畫（`battle/playback.ts`）

- `Frame.moves` 換成 `Frame.motions`：走路或其他位移，依事件順序。
- `PlayOp` 新增 `walk`。`motionMs` 算一個移動的總時間。
- **敵方 2 倍速**（`walkRateOf`）：行動者和主角不同陣營時，走路每格時間除以 `ENEMY_WALK_RATE` 2。停頓不縮短。主角與友軍照常。
- **播放速度**：極慢、慢、正常、快都乘在每格時間與停頓上（`SPEED_SCALE`）。略過時照舊只有一格畫面，沒有任何走路動畫，直接到終點。播放中按略過時，畫布立刻把人放到終點。

### 1.3 畫布（`render/BattleRenderer.ts`、`render/walkFx.ts`）

- `animateWalk(walk, skip)`：
  - 每格用 `tween` 走，新增緩動參數，跟著當下的排換圖層；
  - 轉彎時用新的朝向重建小人（`turn`），重畫場景時再以 `view` 為準；
  - 停頓時播腳下效果；滑倒時倒地；停頓結束跳數字與狀態圖示；
  - 人物照規格先用整個小人平移，骨架走路是 6M-3。
- `walkFx.ts`：四種腳下效果，各自一個 `Graphics`。
  - 冰花：六瓣冰晶；
  - 滑倒擦痕；
  - 陷阱夾子：兩排鋸齒合上後抖一下，再加紅圈；
  - 冒火：火舌；
  - 濺油：油滴與油漬。
- **鏡頭稍微跟著**：
  - 移動中把戰場圖層往走路的人那邊帶一點（`cameraNudge`：偏離中心的 8%，最多 ±10px），平滑追上；
  - 走完回到原位。
  - 暗角（`.battle-vignette`、畫布外圈陰影）是 DOM，不跟著動。
- `usePlayback` 接上 `walk` 這個動作。
- `unitSprite.ts` 只把既有的 `FEET` 改成 export，給腳下效果定位。
- `animate`（`MoveAnim`）不變，大世界的 `WorldField` 照舊用它。

## 2. 測試

- 新增 `client/src/battle/walkAnim.test.ts`（18 個）：
  - **逐格時間軸**：3 格 ＝ 3 × 120ms、時間軸首尾相接；緩動兩端慢、0／½／1、超出範圍時夾住；轉彎轉身（東→南→西）；不同單位分段；其他位移照舊。
  - **停頓插入**：
    - 陷阱停 400ms，數字與定身在那一格、停頓後跳；
    - 已經跳過的事件不在一步結束時重複；
    - 藉機攻擊不算進停頓；
    - 冰面通過不停、失敗滑倒並跳倒地；
    - 火（燃燒）與油（看前一個畫面）。
  - **滑倒回滑**：滑倒後的傳送變成 200ms 滑行；沒滑倒的傳送照舊淡出淡入。
  - **2 倍速保留停頓**：敵方每格 60ms、陷阱仍 400ms；慢速每格與停頓都 2 倍；`walkRateOf` 敵方 2、主角 1；整合到 `playbackPlan`。
  - **略過**：沒有 `walk` 動作、沒有移動。
  - **畫面小算式**：滑倒後腳底留在往前溜的位置、東西兩向倒的方向相反；鏡頭夾在上限內。
- `playback.test.ts` 改用 `motions`／`motionMs`，原本的斷言不變。
- 執行結果：
  - `vitest run src/battle src/render/unitSprite.test.ts src/screens`：61 個檔案、612 個全過；
  - `tsc --noEmit` 通過；
  - `corepack pnpm -C client build` 通過（只有原本的 chunk 大小警告）。
- 沒有跑全量，照規定。

## 3. 截圖（`docs/art/`，1024×768）

- `6a4d_trap_pause.jpg`：陷阱停頓中。主角走兩格後踩上陷阱，腳下鋸齒夾子合上、紅圈，人停在那一格；鏡頭往右偏了幾 px，暗角不動。
- `6a4d_ice_slip.jpg`：冰面倒地。主角走進冰格檢定失敗：腳下冰花，往東側倒地，停在那一格。
- `6a4d_trap_damage.jpg`（附加，800×600）：陷阱停頓結束後，在那一格跳出「−6」。

截圖做法：
- 用 scratch 腳本開本機伺服器（不進版控）：照常 `create_app`，每場開局後在主角東邊兩格放一個已揭露的敵方陷阱，南邊鋪冰。截滑倒那張另外把主角敏捷調成 1，提高失敗機率。
- 走路與檢定照樣由引擎結算。
- 伺服器開在 8299 埠，直接提供建置好的前端（沒開 vite）；存檔放在暫存資料夾；用完已停掉，沒有碰 `saves/`、`tmp_x`。
- 網址加 `?anim=0.02` 放慢 50 倍再截圖。
- 內建瀏覽器的面板被別的工作切走（隱藏時不出畫面），所以改用無頭 Chrome（暫存設定檔）經 DevTools 協定截圖，沒有動使用者的瀏覽器設定。
- 實測其中一場滑倒時剛好倒在隊友格，事件是 `teleport` 滑回 (0,3)，畫面播成短滑行。

## 4. 待 PM 決定（都已照最保守的做法做完）

1. **停頓時間**：滑倒 450ms、火 250ms、油 200ms，是我定的原型數值。規格只寫了陷阱約 0.4 秒。冰面通過不停，只有冰花。
2. **倒地姿勢不留到下一步**：停頓時小人轉倒在地。這一步播完、以 `view` 重畫後，小人又站著，頭上是既有的倒地狀態圖示。現在的小人沒有倒地的畫法，要躺著得等 6M-3 的骨架。
3. **倒的方向**：往東走往西倒，往西走往東倒，南北走一律往東側倒（避免倒到地圖外）。這是畫面選擇，不影響規則。
4. **油的判斷**：油沒有 `surface_entered`（沒有進入效果），所以看這一步開始前畫面上那一格的表面。只影響畫面。
5. **敵方 2 倍速是自動的**：沒有加開關。範圍是「和主角不同陣營的行動者」，包含第三方。只縮短走路；AI 動作後的停頓、推拉等其他位移不變。開關要放在播放速度那排的話，屬於 HUD，留給 6A-4e 或之後。
6. **鏡頭跟隨的幅度**：偏離中心的 8%，最多 ±10px。戰場圖層移動時，畫布邊緣會露出最多 10px 的底色，有暗角蓋著不明顯。現在整張圖就是戰場，沒有更大的場景可以捲。
7. **腳下效果畫在效果圖層**，也就是單位上面，半透明，冰花與夾子會稍微蓋到腳。要改成畫在單位底下，得另開一個地面效果圖層。
8. **轉身是重建整個小人**（換朝向的貼圖），只在轉彎那一格做一次。

## 5. Commit

- `91555c6a` feat(client): tile-by-tile walk playback with surface beats (6A-4d)
- `cd524aa8` feat(client): slip falls toward the map side; 6A-4d screenshots
- 報告：最後一個 commit

## 6. 範圍

- 新檔：
  - `battle/walkAnim.ts`、`battle/walkAnim.test.ts`；
  - `render/walkFx.ts`。
- 修改：
  - `battle/animation.ts`：抽出 `moveAnimOf`；
  - `battle/playback.ts`、`battle/playback.test.ts`；
  - `render/BattleRenderer.ts`：`animateWalk`、轉身、鏡頭、`tween` 加緩動；
  - `render/unitSprite.ts`：只 export `FEET`；
  - `screens/battle/usePlayback.ts`。
- 沒有動 `client/src/world/`、HUD、`inkDoll`／`inkWeapons`／`inkPose`／`inkCreature`。
