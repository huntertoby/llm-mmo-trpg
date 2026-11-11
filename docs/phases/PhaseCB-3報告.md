# Phase CB-3 報告｜#149 異形第二種近戰片段移植（前端）

基準 main `544d0ceb`，分支 `dev/cb3`（worktree `.claude/worktrees/cb3`）。只改 `client/src/`、`docs/`；沒有改 `src/trpg/`、`content/`、`client/openapi.json`、`client/src/api/schema.d.ts`。

## 改了什麼

| 交付 | 內容 | 主要檔案 |
|---|---|---|
| 1 | 5 個片段（`atk:maul`、`atk:upcut`、`atk:slam`、`atk:uptusk`、`atk:tailover`）與 `kfN`、`plant`、`ptOf`、特效 `sweep`、`TAILOVER`、`bendTail`（`pose.split` 切 5 段）照樣張移植；山豹斑點改到身體組（`mark("tr-spots")`）；熊的乳白三爪只在 `atk:slam`（`QPartPose.claws`，資料欄位，不放函式）；取格加 `EPS` | `client/src/render/qCreatureAnim.ts`、`inkCreature.ts`、`creaturePose.ts`、新檔 `creatureRig.ts` |
| 2 | 挑法：動作類型多一個 `melee2`。普攻一律 `melee`（第一種）；單體近戰技能 → `melee2`；沒有第二種的身形與頭目退回第一種。第二種片段在戰場照自己的格數播（12 格／秒），命中點＝表上的命中時間 | `client/src/battle/creatureAction.ts`、`skillSequence.ts`、`viewGrip.ts`、`render/battle/skillLayer.ts`、`render/qBoss.ts` |
| 3 | 開發頁：`creature-gallery.html?melee2=<身形>`（`&west=1`、`&look=1`、`&reduce=1`）逐格並排；`?cb3=first｜spots｜reduce｜frames`；`skill-gallery.html#cb2b` 新增 CB-3 案例與頁內連拍（`&sheet=1`） | `client/src/dev/creatureGallery.ts`、`skillGallery.ts` |
| 4① | 鳥走路後緊接同一隻的攻擊：走路結尾不落地、攻擊開頭不起飛（`playbackPlan` 標 `WalkAnim.aloft`、`CreatureStrike.airborne`；繪製器在兩步之間把鳥留在飛行姿勢，別的動畫開始或 4 秒內沒等到攻擊就落地） | `client/src/battle/playback.ts`、`walkAnim.ts`、`render/battle/motionLayer.ts`、`unitLayer.ts`、`BattleRenderer.ts` |
| 4② | 異形目標在正南、正北時出招不翻面（`creatureFacingTo`）；蛋的起點跟著實際畫出來的那一面 | `client/src/battle/walkAnim.ts`、`render/battle/skillLayer.ts` |
| 5 | 測試 | `client/src/battle/cb3Melee2.test.ts`（24 項）、`cb3BirdLink.test.ts`（5 項） |

`RIG`（部件組與支點）和固定的 Q 大頭支點從 `inkCreature.ts` 搬到 `creatureRig.ts`（純搬移，`inkCreature` 照舊匯出 `RIG`）：`plant`、`ptOf` 在 `qCreatureAnim.ts` 要讀支點，而 `inkCreature` 已經匯入 `qCreatureAnim`，直接互相匯入會變成循環。

## 驗收條件

| 條件 | 結果 |
|---|---|
| `corepack pnpm -C client typecheck` | 通過（結束碼 0） |
| `corepack pnpm -C client test`（vitest 全部） | 通過（結束碼 0；282 檔、3416 項） |
| `client` 內 `npx vite build` | 通過（結束碼 0） |
| 快照 | **沒有變動**，見「快照變動說明」 |
| 7 項截圖 | 見下表，全部在 `docs/art/shots/cb3/` |

### 片段長度、格數、命中時間（照移植需求第 1 節，沒有增減格）

| 身形 | 片段 | 毫秒／格數 | 命中格（時間） | 測試 |
|---|---|---|---|---|
| hound | `atk:maul` | 1100／13 | 第 4 格（333）；417、583、750 只是畫面 | `cb3Melee2.test.ts`「長度、格數、命中時間」「犬狼撲咬拉扯」 |
| feline | `atk:upcut` | 1000／12 | 第 6 格（500） | 同上 |
| bear | `atk:slam` | 1100／13 | 第 7 格（583） | 同上、「熊的乳白三爪」 |
| boar | `atk:uptusk` | 1000／12 | 第 5 格（417） | 同上 |
| lizard | `atk:tailover` | 1250／15 | 第 6 格（500） | 同上、「蜥蜴掄尾砸擊」 |

戰場上既有的攻擊片段一律量化成 12 格（`creaturePose.CLIP_FRAMES.atk`），13、15 格的片段照那樣播會少格。所以這 5 個片段另外帶「命中格」（`Attack.hitF`），戰場照片段自己的格數播：第 f 格從 f × 83.33 ms 起（同樣張 `frameOf`），命中點＝命中格開始的那一刻。**既有片段的播法沒有動。**

### 驗收 7 項的截圖

圖有兩種來源，下表分開寫：「畫廊」＝`creature-gallery.html`（直接畫片段，和樣張頁同一種排法）；「戰場」＝`skill-gallery.html#cb2b`（正式的 `playbackPlan → frameOps` 與繪製器，事件是照引擎事件格式手寫的，不是戰鬥實錄；`?anim=0.25` 慢動作下每格取一張）。

| # | 項目 | 結果 | 檔案 |
|---|---|---|---|
| 1 | 五款各一組連拍，朝東、朝西 | **有截圖**。格數 13／12／13／12／15；我拿犬狼、山豹、熊、蜥蜴朝東和 `docs/art/shots/anim/q-melee2-<身形>.png` 逐格對過姿勢與特效位置，對得上；野豬只看了朝西那張。沒有做像素比對 | 畫廊：`1-<身形>-east.png`、`1-<身形>-west.png`（10 張）；戰場：`1b-<身形>-battle-east.jpg`、`1b-<身形>-battle-west.jpg`（10 張） |
| 2 | 五款普攻仍是第一種 | **有截圖** | 畫廊：`2-first-melee-hit-frames.png`；戰場：`2b-<身形>-basic-battle.jpg`（5 張） |
| 3 | 山豹其他片段的斑點在身體輪廓內 | **有截圖**（idle、move、claw、pounce、hit、death、upcut 各一格）。**實機未看** | 畫廊：`3-feline-spots.png` |
| 4 | 蜥蜴尾根在臀部、尾巴有彎；精英與大型不被裁 | **有截圖**。地圖中間：大型、精英＋大型朝東朝西的 333 尾尖、500 星爆都完整。**地圖最上排＋最右欄時被戰場畫布的邊緣裁到**（333 尾尖、667 頭頂、500 星爆），見待 PM 決定 4 | 畫廊：`4-lizard-tail-frames-a／b／c.png`、`4-lizard-elite-large-frames-a／b／c.png`；戰場：`4b-matriarch-large-battle.jpg`、`4b-matriarch-elite-large-battle.jpg`、`4b-matriarch-elite-large-battle-west.jpg`、`4b-matriarch-elite-large-map-corner.jpg` |
| 5 | 目標在正南、正北不翻面，蜥蜴與熊 | **有截圖**。四組全程頭朝東，朝向三角形沒有變 | 戰場：`5-lizard-north.jpg`、`5-lizard-south.jpg`、`5-bear-north.jpg`、`5-bear-south.jpg`；產卵補拍 `5b-matriarch-spawn-north.jpg`、`5b-matriarch-spawn-south.jpg` |
| 6 | 減少動態五款 | **有截圖**。戰場上照既有規則，出招列第一格就跳片段最後一格，所以身體站著、片段自己的白弧與星爆不出現，只有戰場的命中特效（待 PM 決定 5） | 畫廊：`6-reduced-gallery.png`；戰場：`6b-<身形>-reduced-battle.jpg`（5 張） |
| 7 | 實戰看到一次第二種片段 | **有截圖，一款（熊）**。自己啟動的本機伺服器、真引擎與敵人 AI：石背熊對正南的隊友施放「碎骨重擊」，播 `atk:slam`，沒有翻面。**對手是用暫存的內容資料夾（`TRPG_CONTENT_DIR`，不在 repo）把靶場對手換成霧狼、石背熊、餘燼蜥，不是大世界遭遇**；另外四款實機未看 | `7-real-battle-bear-slam.jpg`（連拍）、`7-real-battle-full-frame.jpg`（整個畫面） |

順手項 ① 的連拍：`x-hawk-walk-then-rake.jpg`（戰場；鷹走兩格後緊接爪擊，走完停在飛行姿勢、直接接爪擊片段，打完才落地一次）。**實機未看。**

截圖共 52 張、約 11.6 MB，單張最大 530 KB。

## `frameOf` 確認結果

**遊戲端有同樣的問題，已修。** `qCreatureAnim.creatureFrameU` 用 `Math.floor(t / (1000/12))` 取格；在 Node 實測，t 剛好是第 7、第 14 格的邊界時商是 6.999…、13.999…，會取到前一格。現在和樣張一樣先加 `1e-6` 再取整（循環片段那一支也加）。

影響範圍很小：戰場的攻擊、受擊、倒下用的是 `creaturePose` 的四捨五入量化，不經過這個函式；遊戲裡只有待機取格和開發頁會用到。新加的 `ownFrameU`、`creatureStrikePose` 的自有格數那一支一開始就帶 `EPS`，測試逐格鎖住（`第 f 格從 f × 83.33 ms 起（格邊界不取到前一格）`）。

## 蜥蜴朝向確認結果（交付 4②）

**不是開發頁手寫狀態造成的，實戰也會翻。** 和開發 PM 11-10 在 `docs/art/CB-2b檢查.md` 寫的結論相同：`SkillLayer.playSkill` 開頭會把施放者轉向目標，目標在正南、正北時朝向變成 `south`／`north`，`creatureSide` 把敵方異形的南北向畫成朝西，所以原本朝東的敵方異形會翻成朝西，打完重畫才翻回來。這是讀程式確認的；改之前沒有另外拍一組翻面的圖。

規格第 4 項②寫「確認」，驗收第 5 項要求「不翻面」。我照驗收與 `CB-2b檢查.md` 末段的決定修了：異形出招時只看目標偏東或偏西（`creatureFacingTo`），同一欄就維持原本的朝向。人形不動。蛋的起點原本也用會轉向南北的朝向算，一起改成實際畫出來的那一面。改後的圖是驗收第 5 項那 6 張，實機那張（第 7 項）也是正南、沒有翻。

## 快照變動說明

**沒有快照變動。** `client/src/render/__snapshots__/` 的兩個檔（`creaturePose.test.ts.snap`、`inkDollSnapshot.test.ts.snap`）都沒有變：它們只含靜態異形（沒有姿勢）與人形。斑點改組只在有姿勢時才有差別，靜態畫面的指令流不變，所以預期中的「山豹斑點」差異沒有反映在快照上，只能看圖（驗收第 3 項）。

改了既有測試的斷言，都是跟著規格變的，沒有放寬：

| 檔案 | 改動 | 原因 |
|---|---|---|
| `qCreatureAnim.test.ts` | 攻擊片段數 35 → 40；動作類型清單加 `melee2` | 多了 5 個片段、1 個類型 |
| `creatureAction.test.ts` 表格 | `mist_wolf`＋`skill_twin_fang`、`ember_lizard`＋`skill_ember_bite`：`melee`／`atk:bite` → `melee2`／`atk:maul`、`atk:tailover`；加一列 `shard_golem`（沒有第二種，退回 `atk:smash`） | 這兩列原本鎖的就是「第二種上線前暫時共用同一片段」 |
| `creatureAction.test.ts` 兩個全表測試 | 「其餘照現行」多一個條件：相鄰＋形狀 `single` 時是 `melee2` | 同上；其他情況仍要求和改前完全一樣 |

## 實機未看

- 第 1～6 項全部是開發頁（畫廊或戰場開發頁），沒有在實際戰鬥裡看。
- 第 7 項只看到熊；犬狼、山豹、野豬、蜥蜴的第二種片段實機未看。同一場霧狼用了「鉗擊」，但我沒有從連拍裡找出那幾張。
- 鳥走路接攻擊實機未看。
- **沒有用肉眼看過正常速度的播放**，節奏有沒有頓感不知道。戰場連拍用 0.25 倍慢動作取格；正常速度那次連拍在命中之後少拍到一格（蜥蜴 667），0.25 倍時 15 格齊全。我沒有查明是取樣時機還是命中停頓造成的，沒有驗證正常速度下每一格都有畫出來。

## 待 PM 決定

1. **「單體近戰技能」的判定**：不是普攻、形狀 `single`、目標相鄰（距離 1）、而且照現行規則會落到普攻片段。副作用：石背熊的 `skill_quake_topple`（`single`、射程 3）貼身放時也會播人立重拍。相鄰但形狀不是 `single` 的招仍播第一種。規格沒寫到形狀，這是最保守的解讀。
2. **`melee2` 是新的動作類型**：樣張裡這 5 個片段的 `type` 是 `melee`，我改成 `melee2`，這樣「普攻挑第一種」不靠宣告順序。開發頁的類型標籤顯示「第二種近戰（單體近戰技能）」。
3. **只有這 5 個片段照自己的格數播**，既有片段仍是 12 格量化。13 格的 `bear atk:quake`、14 格的 `lizard atk:summon` 等既有片段原本就少格，沒有動。
4. **地圖邊緣會裁**：精英＋大型的蜥蜴站在地圖最上排時，333 的尾尖超出戰場畫布上緣；站在最右欄朝東時 500 的星爆超出右緣（`4b-matriarch-elite-large-map-corner.jpg`）。異形貼圖本身沒有裁到。要不要加畫布留白沒有動，那會影響整個戰場版面。
5. **減少動態在戰場上看不到片段特效**：既有規則是出招列直接跳最後一格，最後一格沒有特效。`qCreaturePartPose` 的減少動態姿勢（往前推 2 單位、特效照放）只有開發頁會畫到。兩者都是既有行為，沒有改。
6. **鳥留在空中時不拍翅**：走完到出招之間（敵人移動後的停頓 150 ms）停在移動片段第 0 格。保險期限 4000 ms（效果時鐘）是我定的原型數值。
7. **鳥的連結條件**：上一步是純走路（沒有技能特效）、同一隻、最後一段是走一格（不是滑倒、滑回），這一步它的出招前沒有別的位移。中間隔了別人的一步、減少動態時都照舊落地再起飛。
8. **截圖體積**：52 張 11.6 MB，比前幾段多。`1b`、`2b`、`6b` 三組戰場圖（20 張、約 5 MB）和畫廊圖重複度高，嫌大可以刪。
9. 戰場連拍裡 250～417 ms 身上那個半透明的圓是既有的技能片段提示特效（`docs/art/shots/cb2c/2a-hawk-dive.jpg` 746 ms 也有），不是這次加的。

## 其他

- 開發中只跑相關的 vitest 檔；沒有跑 `scripts/check.py`、沒有跑模擬。
- 沒有新增 `# noqa`／lint 例外（這段沒有 Python）。
- 自己啟動的程序都用自己的 PID 關掉：第二個 vite（5188，PID 48224）、`trpg serve`（8097，PID 48540、32700）、常駐的無頭 Chrome（PID 45212）、第一個 vite（5187，PID 41432）；截圖用的無頭 Chrome 由腳本各自結束。8000、8001、8092 沒有碰。瀏覽器全程 `--mute-audio`，網址帶 `?mute=1`。
- `uv sync --frozen --offline`、`pnpm install --frozen-lockfile --offline` 都是離線完成，沒有下載任何東西。

## 交件前檢查

在 commit `3f2bb6fd`（程式與這份報告之前的最後一個 commit）上各跑一次，三個結束碼分開記：

| 指令 | 結束碼 | 結果 |
|---|---|---|
| `corepack pnpm -C client typecheck` | 0 | 通過 |
| `corepack pnpm -C client test` | 0 | 282 檔、3416 項全部通過 |
| `client` 內 `npx vite build` | 0 | 通過（只有既有的 chunk 大於 500 kB 警告） |
