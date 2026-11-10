# Phase CB-2c 報告｜異形動畫小修：蛋的拋物線、鳥的攻擊過場、減少動態補拍

基準 main 0cbc4ce0。不改 `content/`、`src/trpg/engine/`；不畫新片段；動畫雜湊快照未重產、未更新。

## 改了什麼

- **蛋（交付 1）**：`client/src/render/eggArc.ts`（新）：拋物線的路線與時間是純函式（`eggArcPlan`、`eggAt`），`eggArcEffect` 畫蛋與落地爆開（照 qCreatureAnim 的 egg、glow、burst）。`atk:summon` 片段的蛋、孵化爆開標 `lobbed`（新欄位）：戰場貼圖不畫，`fxAll`（樣張頁）照畫；不用 `ranged` 是因為 `creatureAttackHitU` 會把出手格提早到飛出那一格。起點＝片段原本的 `EGG_START`（身體後方，跟著實際朝向鏡像）、離手時刻＝片段的 u 0.42、終點＝孵化格的腳底、**落地時刻＝片段出手格 `hitMs`**（＝畫面更新出幼體的 `leadMs`，誤差 ≤ 1 ms）。孵化格取 `unit_summoned.pos`，沒有事件時退回技能目標格。只有片段真的是產卵（`info.type === "summon"`）才拋蛋；沒有產卵片段的身形照舊退回遠程。
- **鳥的攻擊過場（交付 2）**：`skillSequence.lay` 在鳥的出招列前後各加一列（`SkillRow.perch: "up" | "down"`，長度 `PERCH_MS`＝333 ms，4 格）。普攻、衝鋒、遠程都走同一條路。起飛接片段第一格、落地從片段最後一格往待機（`perchRowPose`），`qCreaturePartPose` 的內插從 `move` 擴到 `atk:*`（翅膀：收翅 → 半開 → 拍翅，拍翅借移動片段）。同一步連續幾段時只在最前起飛一次、最後落地一次。命中點跟著順延（`hitRel` 含起飛），特效與扣血仍對齊出手格。
- **減少動態**：`playbackPlan` 多一個參數 `reduced`（`usePlayback` 傳 `prefersReducedMotion()`），`strikeOf` 拿掉 `perch`：時間軸不留位置。繪製器另有一道保險（`this.reduced` 時過場列不畫）。
- **開發頁（交付 3）**：`client/dev/skill-gallery.html#cb2b` 新增 `lizardW`、`lizardN`、`lizardS`、`hawkRake`（普攻）、`hawkPalm`；減少動態跟 `trpg.reducedMotion`。

## 驗收條件

| 條件 | 結果 | 證據 |
|---|---|---|
| typecheck | PASS，exit 0 | `npx tsc --noEmit`（client 內） |
| 相關 vitest | PASS，exit 0 | `npx vitest run src/battle src/render src/dev src/audio src/test --reporter=dot`（169 檔、1944 項全 PASS） |
| `npx vite build` | PASS，exit 0 | 建置輸出 |
| 排版煙霧 1600×900 | **全 PASS（12 項）** | `window.__layoutSmoke.runCase("1600x900")`，`/?dev=1&anim=0.1`，localStorage 先清，無頭 Chrome `--mute-audio`，自己的 `uv run trpg serve --port 8097` |
| 動畫雜湊快照 | **未變、未更新** | `creaturePose.test.ts`、`inkDollSnapshot.test.ts` 原樣通過；快照只含靜態（沒給姿勢）與人形，攻擊過場與蛋不在其中 |
| 移動的起飛／落地過場 | 原樣通過 | `qCreatureDeath4b.test.ts`（`perchAt`、移動片段 perch 內插、非鳥不變） |
| 非鳥異形、人形 | 不變 | 表格測試：`CB-2c 鳥的攻擊過場 > 非鳥異形…沒有過場；人形也沒有`、`RECOVER 還是給其他異形`；既有 `creatureAction`、`creatureStrike`、`skillSequence` 測試原樣通過 |
| 引擎、內容、戰鬥結果 | 不變 | 沒有改 `content/`、`src/trpg/engine/`（`git diff --stat` 為證） |

## 行為一致測試（`client/src/battle/cb2cCreatureAnim.test.ts`，25 項）

- 鳥（表格 3 列：普攻／爪擊 melee、俯衝斬 charge、靜電掌 cast × 減少動態開／關）：開＝`CB-2c 鳥的攻擊過場 > %s > 減少動態關：前後各一列、各 4 格…`（過場格數 4＋4，起飛接出招、落地接片段結束）；關＝`減少動態開：沒有過場列…`（0＋0）。
- 非鳥（蝙蝠、獵犬、蜥蜴、人形）都沒有過場；連續兩段只起落一次（`同一步連續兩段…`）；過場姿勢與快取鍵（`過場列的姿勢…`）。
- 蛋（表格 4 方向：朝東、朝西、正北、正南）：`片段是產卵；蛋落點＝孵化格`、`落地時刻＝片段的出手格＝畫面更新出幼體的時刻（不提早）`、`起點在身後、終點＝格子中心腳底、途中最高點在直線上方`；`孵化格取 unit_summoned 的位置…`、`身形沒有產卵片段（退回遠程）不拋蛋`、`片段的蛋標 lobbed…`。

## 截圖對應

全部在 `docs/art/shots/cb2c/`（12 張，jpg 80，最大 220 KB；每張 10 個時間點，時間標籤是遊戲內毫秒）。來自開發頁 `client/dev/skill-gallery.html#cb2b`＋`?anim=0.1`，無頭 Chrome `--mute-audio`，**播放器與繪製是正式路徑，事件是手寫的，不是戰鬥實錄**。

| 驗收項 | 檔案 | 看到什麼 |
|---|---|---|
| 蜥蜴產卵朝東 | `docs/art/shots/cb2c/1a-lizard-east.jpg` | 約 593 ms 蛋離開身體高飛，991 ms 接近孵化格，1198 ms 幼蜥已在該格出現、爆開中；蛋與幼蜥同一格（落地時刻約 1045 ms 是由片段出手格算的，10 個取樣點沒有剛好落在那一刻） |
| 蜥蜴產卵正南 | `docs/art/shots/cb2c/1b-lizard-south.jpg` | 995 ms 蛋在南邊孵化格正上方，同格孵出 |
| 蜥蜴產卵正北 | `docs/art/shots/cb2c/1c-lizard-north.jpg` | 同上，往北 |
| 鷹俯衝（含結尾落地） | `docs/art/shots/cb2c/2a-hawk-dive.jpg` | 14 ms 落地、189 ms 起飛過場、367 ms 起全程片段、1490 ms 落地過場、1675 ms 收翅站好 |
| 鷹爪擊（含結尾落地） | `docs/art/shots/cb2c/2b-hawk-rake.jpg` | 5 ms 落地、165 ms 起飛過場、654～812 ms 爪擊、1303 ms 落地過場、1468 ms 收翅站好 |
| 減少動態 | `docs/art/shots/cb2c/3a-reduced-leopard.jpg`、`3b-reduced-beetle.jpg`、`3c-reduced-hawk-dive.jpg`、`3d-reduced-tortoise.jpg`、`3e-reduced-boar.jpg`、`3f-reduced-lizard.jpg`、`3g-reduced-wraith.jpg`（同資料夾） | 6 個片段（噴吐分龜、硫煙獸兩張）。鷹沒有過場；蛋照舊飛到孵化格 |

## 待 PM 決定

1. **節奏**：過場是加時間，不是壓在片段裡（壓在片段裡會蓋掉鷹 0.3 秒內的蓄力）。鳥每次攻擊多 333 ms 起飛（命中順延）與 333 ms 落地（在命中之後、和下一步重疊）。若嫌慢，可只在第一次起飛，或把過場縮短。
2. **走路後攻擊**：鳥走到定點落地後，下一步攻擊會再起飛一次（兩段都照規格）。若要連起來要讀上一步的狀態，本段不動。
3. **減少動態下的蛋**：蛋歸類成飛行物（`reducedMotion.ts`「沒標的（飛行物…）照舊」），減少動態時照舊拋物線飛行；若美術 PM 認為該瞬移到定點，只差一個 `motion` 標記。
4. **減少動態的鷹**：出招列照既有規則第一格就跳片段最後一格（飛行姿勢）、片段結束直接回落地待機，也就是「沒有過場」。這段中間的高度差就是規格說的「不用過場」，照收。
5. **落地時刻**：把「落地那一刻接孵化」解讀成落地＝片段出手格（u≈0.91，約 1045 ms）。蛋飛行時間因此比片段原本（0.42～0.68）長，搖晃、裂紋這兩格不再出現；若要保留搖晃，得把落地提早，孵化時間就會和落地分開。
6. **爪擊的表格列**：鷹的普攻武器是 talons，普攻片段就是「爪擊」；開發頁的普攻案例叫 `hawkRake`。靜電掌的遠程也有過場（規格寫「所有鳥的攻擊」），一併測了。
7. **連拍來源**：全部是開發頁（真實播放器＋手寫事件），戰鬥實錄未看（同 CB-2b）。
8. **正南、正北時的身體朝向**：片段仍是側面播（沿用現況），蛋從身體後方起飛、飛往上下方向；規則朝向不動。

## 其他

- `qCreatureAnim.ts` 的片段幾何（蛋的起點、離手格、大小）抽成 `EGG_FROM_U`、`EGG_START`、`EGG_SCALE`，樣張頁與拋物線共用。
- 伺服器與無頭 Chrome 都用自己的 PID 關掉（vite 37476、trpg serve 47068／30116、chrome 38840、14020、12596），5197／8097／9488／9489 埠確認沒有殘留。
