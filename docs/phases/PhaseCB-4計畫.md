# Phase CB-4 計畫｜戰鬥特效落點修正：頭目的正南／正北、斜向目標

> 開發 PM 規格助手 2026-11-12 起草（依據 main `17982c56` 之後）。依據：美術 PM CB-3c 驗收（`docs/art/CB-3檢查.md` 末節「CB-3c 驗收：通過」第 1、2 點）、`docs/phases/PhaseCB-3c報告.md`「待 PM 決定」第 1～3 點。
> 先讀 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第一～三節，第四節第 3、4、9、10、15、16、18 點；再讀 `PhaseCB-3c計畫.md`、`PhaseCB-3c報告.md`（上一段的修法）、`PhaseCB-3b報告.md`（開發頁與換陣容做法）。

## 0.0 開發 PM 定稿（開發 PM 第七任，2026-11-12）

- 第 0 節 Q1～Q7 **全部照「建議」**定案（剪切、原點在目標格中心；形狀不轉只搬位置；頭目相鄰目標點沿用 52；其餘不改、記追蹤）。Q2、Q7 的截圖在報告標出，給美術 PM 判斷。
- 一段做完、一個實作者。`cb3cFxTurn.test.ts` 的斜向列與「頭目不另畫」是本段有意改變的舊行為：逐條說明，並證明新斷言在舊程式下會失敗。

## 0. 待確認（開發 PM 派工前定案；沒回覆就照「建議」做）

| # | 問題 | 建議 |
|---|---|---|
| Q1 | 斜向的轉法：(a)「剪切」——橫向距離照舊、往前的距離另外加上往南／往北的分量，原點放在目標格中心；(b) 以施放者為圓心轉 45° | **(a)**。和 CB-3c 是同一條公式（目標同一欄時退化成 CB-3c、同一排時退化成東西向原樣），星爆、白弧的相對位置照原樣張比例，最好測；(b) 會讓斜向的特效比東西向遠 √2 倍 |
| Q2 | 頭目在東西向時，灰燼之心衝撞（`ram`）的星爆在施放者前方 78.3 px，超出目標格邊（72）約 6 px（根因 B 第 3 點）；要不要本段一起拉回目標格 | **本段不改東西向**（美術 PM 沒提、是 QK-4b 照樣張的比例），只在報告附一張東西向截圖請美術 PM 判斷，要改另排 |
| Q3 | 頭目的「相鄰目標點」取多少虛擬單位：沿用一般異形的 52（`CREATURE_FX_TARGET_X`），或依頭目片段另訂 | **沿用 52**。換算後灰燼之心星爆、碎晶之主白弧與塵土在正南北／斜向時，每個軸離目標格中心約 2～13 px（格半寬 24），都在格內；另訂會讓頭目和一般異形兩套數字 |
| Q4 | 斜向時白弧、星爆的形狀要不要轉 | **不轉，只搬位置**（同 CB-3c 美術 PM 裁定第 3 點） |
| Q5 | 頭目、一般異形出招時身體的前推（`ram`、`swing` 的 `dx`、一般異形 `root.dx`）在正南北／斜向仍往東西推 | **不改**（CB-3c 也沒改；只修特效落點）。記追蹤 |
| Q6 | 隔一格的第二種近戰（射程 2 的近戰武器，`cb3cMeleeRange` 有這種判定）時，錨點仍放「相鄰格」而不是目標格 | **不改**：原樣內容的異形都拿射程 1 的近戰武器，不會出現；寫進報告的追蹤 |
| Q7 | 精英＋大型東西向的錨點 73.1 px（比格邊多約 1 px，既有） | **不改**（東西向不動）；斜向會因 Q1 的原點放在目標格中心而自動落在格內 |

## PM 決定（已定，照做）

| # | 決定 | 出處 |
|---|---|---|
| D1 | 頭目（灰燼之心、碎晶之主）打正南／正北時特效要落在目標格：**要排** | 美術 PM，`CB-3檢查.md`「CB-3c 驗收」第 1 點 |
| D2 | 斜向特效不在目標格內：和 D1 同段一起看 | 同上第 2 點 |
| D3 | 轉向後白弧只搬位置、形狀不轉，不另畫 | 同上第 3 點 |
| D4 | 「異形向正南／正北出招不翻面」（`creatureFacingTo`）維持；右緣留邊 12、左緣 0 不改 | `PhaseCB-3c計畫.md` D3、D4 |
| D5 | 不排「同一單位連續出手的銜接」 | 開發 PM 派工；`CB-3檢查.md` 第 5 點 |
| D6 | 舊存檔不必相容 | 使用者原話「存檔都可以刪除」 |

## 1. 兩個問題的根因（規格助手只讀查證，行號以 `17982c56` 為準）

### A. 斜向特效不在目標格內

1. `client/src/render/creatureFxTurn.ts:19-22` 的 `creatureFxTurnOf` 只在 `to.x === from.x`（同一欄）時回 1／-1，斜向回 `null`。
2. `client/src/render/battle/skillLayer.ts:224` 因此不帶 `fxTurn`，片段特效照舊在 `client/src/render/inkCreature.ts:1271` 畫進**身體貼圖**；身體貼圖的原點是施放者腳底、只有東西兩面（`creatureSide` 鏡射），特效的「相鄰目標」點固定在 (±52, 0) 虛擬單位。
3. 換成像素就是 `creatureFxAnchorPx`（`creatureFxTurn.ts:66-71`）的非轉向分支：(±50.88, 0) px（精英＋大型 ±73.14）。斜向的目標格中心在 (±48, ±48)，**特效落在施放者那一排、目標那一欄（離目標格中心正好一格高）**——也就是目標旁邊東西向的那一格。CB-3c 的測試（`client/src/render/cb3cFxTurn.test.ts` 的「8 方向」表）對斜向斷言「和修改前相同」，把這個行為鎖住了。

重現（vitest 純函式，已跑過）：
```ts
creatureFxAnchorPx({ from: { x: 4, y: 4 }, to: { x: 5, y: 5 }, side: "east", size: 1, fieldScale: 1, dollScale: DOLL_SCALE, tile: TILE_SIZE })
// → { x: 50.88, y: 0 }；目標格中心 (48, 48) → 不在格內（|dy| = 48 > 24）
```

### B. 頭目打正南／正北，特效仍落在側邊

CB-3c 刻意把頭目排除，四個地方都擋著：

1. `skillLayer.ts:224`：`creatureOf(draw)?.boss === undefined && …` —— 頭目不算 `fxTurn`。
2. `inkCreature.ts:1199-1202`：`drawCreature` 遇到頭目直接 `drawBossFrame` 後 return，**不看 `pose.fxTurn`**；`client/src/render/qBoss.ts:741-746` 的 `drawBossFrame` → `bossAct`（`qBoss.ts:615-616`）把 `bossPlan` 的特效（`ranged` 以外）一律畫進頭目身體貼圖（`BOSS_BOX` 200×150，腳底下只留 20，放不下往南北一格）。
3. `inkCreature.ts:1285-1289` 的 `turnedCreatureFx`、`renderCreatureFxCanvas`，以及 `client/src/render/artTextures.ts:278-284` 的 `creatureFx`：頭目一律回空／`null`；而且 `creatureFx` 傳 `fxTurnScale(r.size, 1, DOLL_SCALE)`，`fieldScale` 寫死 1，頭目要用 `creatureFieldScale`（1.6）、`size` 用 1（頭目貼圖不含大小，`unitSprite.ts:613`）。
4. 頭目的片段特效座標（`qBoss.ts:662` 灰燼之心 `ram` 的星爆 x＝50、塵土 x＝44；`qBoss.ts:690` 碎晶之主 `swing` 的白弧 x＝44）。頭目戰場縮放 1.6 → 每單位 1.5655 px，東西向時星爆在 78.3 px、白弧與塵土 68.9 px。正南北時這些照舊往東西畫（同 CB-3c 以前的一般異形）。
5. 哪些頭目片段會碰到：灰燼之心**第 1 階段**普攻（`bossAttackClip`：`melee`／`charge` 且 phase 1 → `ram`）、碎晶之主普攻與非施法的招（`swing`）。灰燼之心第 2、3 階段普攻是 `firebolt`、碎晶之主施法是 `thunder`，出手特效是 `ranged`，戰場上由技能特效畫在目標格，不受影響。

重現（vitest 純函式，已跑過）：
```ts
const boss = creatureOf(drawOf("rift_shard_lord", true, "east"))!;          // drawOf 同 cb3cFxTurn.test.ts
turnedCreatureFx(boss, { clip: "atk:@melee", u: 0.5, fxTurn: 1 }, 1)     // → []（cb3cFxTurn.test.ts:164-169 已鎖住）
bossPlan("ah", "ram", 6 / 11, { phase: 1 }).fx                            // burst x=50、dust x=44（未轉向，照東西畫）
```

## 目標

- 異形（含頭目）片段自帶的特效（星爆、白弧、塵土、掃尾）在目標位於**正南、正北、四個斜向**時，「相鄰目標點」落在目標格中心（跟著目標格抬高），其餘特效照原樣張比例沿連線排。
- 頭目站邊欄打正南／正北時特效不被畫布裁掉（D4 不加留邊）。
- 東西向（同一排）的一般異形與頭目：特效位置、身體貼圖、快照**一律不變**。

## 範圍外

- 同一單位連續出手的銜接（D5）；錐形震波畫面；鳥第二次攻擊先落地。
- 身體的前推方向（Q5）、白弧形狀（D3）、隔一格的近戰（Q6）、東西向的頭目星爆距離（Q2）。
- 人形單位的特效（`vfxEffects.ts` 的 `slashEffect` 本來就以目標格為準）、技能特效層（`vfx.ts`／`vfxLayer.ts`）。
- 引擎、AI、`content/`、API 一律不改。

## 受影響的既有功能

| 位置 | 改不改 | 說明 |
|---|---|---|
| `render/creatureFxTurn.ts`（`creatureFxTurnOf`、`turnCreatureFx`、`fxTurnScale`、`creatureFxAnchorPx`） | 改 | 由「只有同一欄 ±1」擴成「方向 (dx, dy)」，dy＝0（同一排）回 `null`、照舊。公式見交付 1 |
| `render/creaturePose.ts`（`CreaturePose.fxTurn` 型別、`quantizeCreaturePose`、`creaturePoseKey`） | 改 | 型別擴成能表示斜向；**沒有轉向時鍵與畫法逐字不變**，同一欄的鍵可以變（只出現在轉向貼圖的快取鍵） |
| `render/battle/skillLayer.ts`（第 224 行、`placeTurnedFx`） | 改 | 拿掉頭目排除；錨點改放 `r.target` 方向的相鄰格（斜向＝斜對角那一格），抬高照那一格 |
| `render/inkCreature.ts`（`drawCreature`、`turnedCreatureFx`、`renderCreatureFxCanvas`、`CREATURE_FX_BOX`） | 改 | 頭目也走轉向貼圖；斜向要保留橫向 x，畫布寬度確認放得下（必要時另訂頭目的畫布） |
| `render/qBoss.ts`（`bossAct`、`drawBossFrame`，必要時抽出「這一格的特效」給轉向貼圖用） | 改 | 有 `fxTurn` 時身體貼圖不畫特效；`bossPlan`、`bossAttackHitU`（命中對齊）不得改 |
| `render/artTextures.ts`（`creatureFx`） | 改 | 頭目不再回 `null`；`fxTurnScale` 用 `creatureFieldScale` 與頭目 size 1 |
| `render/cb3cFxTurn.test.ts` | 改 | 「8 方向」表的斜向列與「頭目不另畫」那條是上一段鎖住的舊行為，本段**有意改變**；改成新期望值，報告逐條說明（不得刪除東西向、同一欄一般異形的斷言） |
| `render/creaturePose.test.ts`、`inkDollSnapshot.test.ts` 的雜湊快照 | 不應變 | 這兩個只含靜態與東西向；若變了要停下查，**不得整批重產**，每項變動要證明來自本段（暫時拿掉改動能回到舊值） |
| `dev/skillGallery.ts` | 加案例 | 頭目正南北、斜向（見交付 4）；灰燼之心要能指定第 1 階段（`bossOf` 沒有階段資料時：有熔殼＝1、沒有＝2，案例要給 `boss_phase` 或熔殼） |
| 東西向、第一種近戰的時間軸、`creatureActionOf`、人形 | 不改 | |

## 交付項目

1. **方向化的轉向**（`creatureFxTurn.ts`）：目標相對施放者的方向 (sx, sy)＝(sign(dx), sign(dy))；sy＝0 → 不轉（照舊畫進身體貼圖）。其他情況照 Q1 的剪切：
   以「相鄰目標點」為原點，u＝x − 52（虛擬單位）→ 新座標 (|sx| × u, y ＋ sy × u × c)，`c = fxTurnScale(…)`；sx＝0 時就是 CB-3c 的公式（寫測試證明同一欄的輸出與 CB-3c 逐筆相同）。錐形（`cone`）的角度照同一規則換算。貼圖照 `creatureSide` 鏡射，原點放在**目標方向的相鄰格中心**。
2. **頭目**：拿掉四處排除（根因 B 第 1～3 點）。有轉向時頭目身體貼圖不畫片段特效、另畫轉向貼圖；`fieldScale`＝1.6、size＝1。`ranged` 特效照舊不畫進任何貼圖。
3. **斜向的一般異形**：同交付 1，含精英＋大型。
4. **開發頁案例**（`skill-gallery.html#cb2b`）：灰燼之心第 1 階段普攻打正南、站最左欄朝西打正北；碎晶之主普攻打正南、站最右欄打正北；硫煙獸斜向（東南、西北）；熔爐母獸精英＋大型站最右欄打西南或東南的邊角。案例名寫進報告。
5. **測試**（下節）。
6. 報告 `docs/phases/PhaseCB-4報告.md`；**順手更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`** 第二節「特效落點」與第四節第 3 點（拿掉「頭目、斜向還沒涵蓋」）。

## 行為一致測試（vitest，新檔 `render/cb4FxAnchor.test.ts`）

1. **錨點表**：8 方向 × {一般（硫煙獸）、精英＋大型（熔爐母獸）、灰燼之心（第 1 階段）、碎晶之主} × 原本朝東／朝西：
   - 東、西：錨點與修改前相同（期望值＝修改前的 `creatureFxAnchorPx`，寫死 50.88／73.14 與頭目的值）。
   - 南、北、四個斜向：錨點＝目標格中心（容差 0.01 px）。
2. **實際片段**：硫煙獸挑獠牙、熔爐母獸甩尾、灰燼之心 `ram`、碎晶之主 `swing`，在南、北、四個斜向逐格（12 格）跑，斷言每一格的星爆／白弧中心落在目標格內（`|Δ| ≤ 24 px`），塵土留在施放者那一格或連線上。數值一律從片段函式（`qCreaturePartPose`、`bossPlan`）取，不手寫座標。
3. **退化一致**：同一欄的一般異形，`turnCreatureFx` 新舊輸出逐筆相同（CB-3c 的結果當期望值）；同一排時 `creatureFxTurnOf` 回 `null`、姿勢鍵與修改前相同。
4. **頭目身體貼圖不畫特效**：用假畫布（`test/fakeCanvas.ts`）比對 `drawBossFrame` 在有／沒有轉向時的呼叫紀錄——有轉向時少了特效那幾筆、身體那幾筆逐筆相同。
5. **命中對齊不變**：`bossAttackHitU` 與一般異形 `creatureAttackHitU` 的結果和修改前相同（表格測試）。
6. 每項新斷言都要在**舊程式下會失敗**（暫時換回 `17982c56` 的檔跑一次，報告寫失敗數，跑完還原）。

## 驗收與截圖分配

驗收條件：
1. 上節測試全過；`corepack pnpm -C client exec vitest run src/render/cb4FxAnchor.test.ts src/render/cb3cFxTurn.test.ts src/render/creaturePose.test.ts src/render/inkDollSnapshot.test.ts src/render/qCreatureAnim.test.ts src/battle/creatureAction.test.ts` 全過；雜湊快照不變（變了照「受影響的既有功能」處理）。
2. 交件前各跑一次、結束碼分開記：`corepack pnpm -C client test`、`corepack pnpm -C client build`、`corepack pnpm -C client typecheck`，全部 0。
3. `git diff --stat 17982c56 -- src/trpg content client/src/api` 為空（引擎、內容、API 沒動）。
4. 截圖齊全，邊欄那幾張的特效完整在畫布內。

截圖（`docs/art/shots/cb4/`，**≤ 10 張**、jpg 品質 80、單張 ≤ 300 KB；連拍用合圖；真 1 倍特寫可 PNG ≤ 300 KB；只拍本段改到的；開發頁 `?mute=1&sheet=1&rows=1`，正式 `playbackPlan → frameOps`）：

| # | 內容 | 給誰看什麼 |
|---|---|---|
| 1 | 灰燼之心第 1 階段普攻 `ram` 打正南（連拍） | D1：星爆在目標身上 |
| 2 | 灰燼之心站最左欄朝西打正北（`&margin=1`） | D1：不被裁 |
| 3 | 碎晶之主 `swing` 打正南（連拍） | D1 |
| 4 | 碎晶之主站最右欄打正北（`&margin=1`） | D1：不被裁 |
| 5 | 硫煙獸打東南（連拍） | D2 |
| 6 | 硫煙獸朝西打西北（連拍） | D2 |
| 7 | 熔爐母獸精英＋大型站最右欄打西南或東南的邊角 | D2：大型＋邊欄 |
| 8 | 灰燼之心 `ram` 東西向（修改後；修改前只在 scratchpad 逐像素比對） | Q2：東西向沒變、星爆 78 px 給美術判斷 |
| 9 | （選）硫煙獸正南（對照 `cb3c/1-boar-west-south.jpg`，證明同一欄沒退化） | 退化一致 |

## 開發中跑的測試

- 只跑直接相關的檔：`corepack pnpm -C client exec vitest run src/render/cb4FxAnchor.test.ts src/render/cb3cFxTurn.test.ts`；動到 `creaturePose.ts`／`inkCreature.ts`／`qBoss.ts` 時加 `creaturePose.test.ts`、`inkDollSnapshot.test.ts`、`qCreatureAnim.test.ts`（有頭目片段的測試檔用 `grep -l bossPlan src` 找）。
- 整包 `pnpm test`／`build`／`typecheck` 只在交件前各一次（驗收 2）。不跑 `scripts/check.py`、不跑模擬、不跑 pytest（沒動後端）。

## 工作環境與規矩

- Windows：前端 `corepack pnpm -C client …`；新 worktree 先 `corepack pnpm -C client install --frozen-lockfile --offline`（需要 Python 時 `uv sync --frozen`，之後加 `UV_NO_SYNC=1`）。
- 預覽埠：vite 5300～5304、`trpg serve`／CDP 8148～8150；**不用 8000、8001**。網址一律加 `?mute=1`，無頭 Chrome 加 `--mute-audio`；腳本、`--user-data-dir` 放 scratchpad 自己的子資料夾。
- 等待一律靠完成通知，不寫 until／while 輪詢迴圈；交件前用自己記下的 PID 關掉 vite 與無頭 Chrome，不結束不是自己啟動的程序。
- 子 agent 一律 Opus 5.5（`model: "opus"`），並往下傳同樣規矩。
- 不要 push；依交付分 commit，結尾帶 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 報告格式

做了什麼（交付表＋commit）、驗收逐條（測試名或指令輸出為證、三個結束碼分開記）、根因確認（對照本計畫第 1 節，有出入就寫）、轉法與頭目換算說明、快照與 `cb3cFxTurn.test.ts` 改動逐條說明（含舊程式下的失敗數）、截圖清單（完整路徑）、實機未看、自己啟動的程序與 PID、「待 PM 決定」最多 10 點。
