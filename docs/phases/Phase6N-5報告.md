# Phase 6N-5 報告：動畫第二批⑤　特殊結果（特效加停頓）＋復活、勝利

實作者，2026-11-04。

規格依據：
- `docs/phases/Phase6計畫.md` 6N-5 列（選項 B：特效加停頓，不做慢動作與鏡頭）；
- `docs/art/動畫移植需求第二批.md` 第 0 節（原則）、第 5 節（觸發、做法、檢查清單），第 4 節的復活、勝利兩列（6N-4 待決 4，開發 PM 排進這段）。

開工時 worktree 落後 main，先 `git merge --ff-only 03d51abb`（含 6N-4）。只改了 `client/`，另外加了截圖和這份報告。沒有改數值、規則、Python 引擎或 API；沒有新增相依；沒有新增伺服器欄位。

## 交付

| 項目 | 檔案 |
|---|---|
| 特殊結果的推導（純函式，只讀事件） | `client/src/battle/specials.ts`（新）：`specialsFor`、`stopsOf`、`withSpecials`、`stopHoldMs`、`victoryOf`、`SpecialMemo` |
| 型別 | `client/src/battle/vfx.ts`：`StepVfx.specials`／`stops`、`SpecialKind`、`VfxSpecial`、`VfxStop`；`ReactKind` 加 `rise`（`unit_revived`）；`scaleVfx` 一起縮放 |
| 播放計畫 | `client/src/battle/playback.ts`：特殊結果照排好的命中點算、跟著速度縮放；`Frame.victory`、`PlayOp` 的 `victory`；`playbackPlan` 多一個 `memo` 參數（預設新的） |
| 播放 | `client/src/screens/battle/usePlayback.ts`：等命中時多等停頓（`stopHoldMs`）；`victory` 操作（略過時不播）；擊殺的輪跨回應記住 |
| 停頓（效果時鐘） | `client/src/render/hitStop.ts`（新）：`advanceClock`、`addFreeze`；`BattleRenderer.ts`：效果時鐘走到命中點停住 |
| 片段（純函式） | `client/src/render/reactClips.ts`：`recoil`（被彈開半步）、`rise`（復活）、`victory`（舉手／收刀）、`riseRing`、`victoryPose`、`creatureResult`（異形） |
| 效果 | `client/src/render/resultEffects.ts`（新）：畫面閃白、四周變暗、大火花、彈開、第二層殘影、復活（身體＋綠光）、勝利（全隊＋字樣）；`BattleRenderer.playVictory` |
| 暴擊弧光 | `client/src/render/vfxEffects.ts`：近戰弧光暴擊時加粗、變金色（`CRIT_GOLD`） |
| 字樣 | `client/src/battle/feedback.ts`：「暴擊 −N」（放大）、傷害的 `block_permille < 1000` 跳「格擋」（同一格一步只跳一次）、沒打中改寫「閃避」 |
| dev 頁 | `client/src/dev/skillGallery.ts`：`skill-gallery.html#result` |
| 測試 | `battle/specials.test.ts`（新，15）、`render/hitStop.test.ts`（新，5）、`render/resultClips.test.ts`（新，9）、`battle/feedback.test.ts`（＋1、改 2） |

## 1. 觸發（只讀事件）

`withSpecials` 在播放計畫裡、串接器排好命中點之後算（未縮放），再跟著播放速度一起縮放。

| 結果 | 觸發 | 時間 | 停頓（正常速度） | 做法 |
|---|---|---|---|---|
| 暴擊 | `damage_dealt.crit` | 那一段的命中點 | 100 ms | 停頓那一刻整張地圖閃白（0.32 → 0，140 ms）；原本的暴擊震動（6M 起就有，`shake 2`）；近戰弧光加粗、變金色；數字放大寫「暴擊 −N」 |
| 擊殺 | `unit_downed`，或 `hp_after == 0` 且有扣血 | 倒下的人那一段的命中點 | 100 ms | 停頓＋多一次震動（版面設定關震動時不震）。**同一輪只強化一次**：取這一步最早的一個，輪數記在 `SpecialMemo`（跨步驟、跨回應，`usePlayback` 用 ref 保留） |
| 格擋成功 | `damage_dealt.block_permille < 1000` | 6N-4 格擋反應的時間 | 60 ms | 大火花（11 道、半徑大七成，疊在 6N-4 的火花上）；「格擋」字樣；攻擊者（`source_id`）被彈開半步（`recoil`，退 8、仰身，300 ms） |
| 閃避成功 | `attack_rolled.hit == false` | 6N-4 閃避反應的時間 | 不停 | 殘影多一層（在原地和跳到的位置中間、更淡）；字樣「閃避」（原本寫「失手」） |
| Boss 大招 | 這一步開始前帶 `boss` 標籤、身上有 `charging` 的單位放出技能（`skill_followup` 或 `skill_used`） | 出招開始 | 不停 | 畫面四周一圈一圈變暗 0.3 秒（中間不暗） |

- **停頓的上限**：同一刻只停一次（暴擊＋擊殺在同一下＝100 ms，不是 200）；每次不超過 100 ms；一步加起來不超過 200 ms（多段技能每段都暴擊時，第 3 段起不停）。都乘播放速度：快 ＝ 一半、慢 ＝ 2 倍、`?anim=0.1` ＝ 10 倍。
- **略過不停頓**：「略過」的播放計畫沒有特效，`frameOps` 沒有 `vfx`／`victory` 操作；播放中途按略過時 `vfx` 操作直接跳過，也就不登記停頓。
- **不做慢動作、不做鏡頭拉近**。

## 2. 停頓怎麼做（`hitStop.ts`）

繪製器的效果時鐘（技能片段、特效、受擊、浮動數字都照它）走到停頓那一刻就停住，用掉停頓的時間再往下走（`advanceClock`：純函式，吃 ticker 每幀的時間；跨過停頓的長幀照樣扣掉停頓）。`playVfx` 登記這一步的停頓（`addFreeze`，同一刻取長的）。播放端等命中時多等 `stopHoldMs`（命中點以前的停頓總和），所以畫面在停頓結束後才以結果重畫、跳數字。按住空白鍵 2 倍速時 ticker 的每幀時間變長，停頓一起變短；等待也照 6N-1 的方式重算。效果都播完時清掉剩下的停頓。

## 3. 復活、勝利（6N-4 需求表的兩列）

- **復活**：`unit_revived` → 反應 `rise`（施放者那一段的命中點；同一段同一人：復活 ＞ 倒下 ＞ …）。人形：倒下片段倒過來——第一格＝倒下片段最後一格（轉 90°、平移 (-27, -11)、透明度＝可復活倒地的 0.6、不帶姿勢；測試鎖住和 `reactFrame("down", 1)` 相同），0～0.5 翻回跪姿、0.5～0.95 站直；腳下一圈綠光＋淡淡光柱（`riseRing`）。重畫前後都照單位 ID 找目前的小人（倒地圖示的小人或重畫後站著的小人）。異形：6M-2 的 `fall` 倒著播（第一格＝`downedCreaturePose`）。形態、召喚物：只有綠光。520 ms。
- **勝利**：這一步有 `battle_ended` 而且 `winner` ＝主角那一隊 → 站著的我方每人播勝利片段（520 ms），地圖上方浮出「勝利」（1 秒），播完才顯示結束面板（`victory` 操作在紀錄之後、停頓之前）。人形兩種照雜湊「戰鬥鍵:battle_ended 的 seq:單位:victory」挑：**舉手**（主手連武器朝天、另一手也舉起、小跳一下）、**收刀**（刀尖朝下、點頭）。異形：撲的小跳版（往前只走三成）。敗、平手沒有。
- 戰鬥鍵沿用 6N-4 的 `view.map_id`。

## 4. 測試結果

- `tsc --noEmit` 通過；`corepack pnpm -C client build` 成功（只有原本就有的 chunk 大小提示）。
- client 全部 vitest：**207 個檔案、2225 項全部通過**（交件前跑一次）。
- 新增、改動的測試（共新增 30 項）：
  - **觸發**（`specials.test.ts`）：暴擊在命中點；擊殺（`unit_downed`、扣到 0、扣不到 0 沒有）；**同一輪只強化一次**（memo 跨步驟，下一輪又有；同一步兩人倒下只一個）；格擋帶被彈開的攻擊者、`block_permille == 1000` 沒有；閃避（技能、普攻）；Boss 大招（Boss＋蓄力才有，非 Boss、沒蓄力都沒有）；
  - **停頓上限**：暴擊、擊殺 100、格擋 60、閃避與 Boss 不停；同一刻暴擊＋擊殺＋格擋只停 100；四次暴擊每次 ≤ 100、一步總和 ≤ 200；一場 6 次暴擊每步停頓 ≤ 100；
  - **跳過不停頓**：快速＝50、略過的計畫沒有 `vfx`／`victory` 操作；等待只算命中點以前的停頓；
  - **確定性**：同輸入同 specials／stops；片段同 t 同畫面；`advanceClock` 同幀時間同結果；勝利姿勢照雜湊、兩種都會出現；
  - **復活**：`unit_revived` → `rise` 在命中點；第一格＝倒下片段最後一格、最後一格站好、單調站起；綠光兩端為 0；異形復活第一格＝倒地的樣子；
  - **勝利**：我方勝才有、敗與平手沒有、倒下的人不算；`victory` 操作在重畫之後；
  - **停頓時鐘**（`hitStop.test.ts`）：停在命中點、用完再走、長幀跨過、同一刻取長的；
  - **字樣**（`feedback.test.ts`）：「暴擊 −N」、「格擋」同一格一步一次、「閃避」。

## 5. noqa

沒有新增 eslint／ruff 例外。

## 6. dev 頁

`client/skill-gallery.html#result`（`?anim=0.1` 慢動作、`?cell=88` 放大、`?freeze=毫秒` 停格）：暴擊、擊殺、格擋成功、閃避成功、暴擊＋擊殺（第 2 輪，只停一次）、Boss 大招、復活、異形復活、異形格擋（彈開＝輕版受擊），最後一排全隊勝利（舉手、收刀、弓手、異形）。全部走正式的 `vfxFor → skillTimeline → withSpecials → playSkill／playVfx`；這頁照效果時鐘等命中（加停頓）再重畫，背景分頁節流時 `?freeze=` 的停格仍對得上。

## 7. 截圖（`docs/art/`）

| 檔案 | 內容 |
|---|---|
| `6n5_gallery_hit.jpg` | dev 頁 `#result`，88px，`?anim=0.25&freeze=1586`（停在暴擊的停頓裡）：整張地圖閃白、兩個暴擊的金色粗弧光、格擋的大火花、目標白閃 |
| `6n5_gallery_after.jpg` | 停頓結束、以結果重畫：「暴擊 −9」「暴擊 −20」放大、「格擋」「閃避」「擊倒」「復活」字樣 |
| `6n5_gallery_boss.jpg` | Boss 大招：地圖四周一圈圈變暗（Boss 身上蓄力圖示） |
| `6n5_gallery_rise.jpg` | 復活：人形從倒地翻起中、腳下綠光圈；異形復活一樣有綠光 |
| `6n5_gallery_victory.jpg` | 勝利：最後一排舉劍朝天、弓手、異形小跳，地圖上方「勝利」 |
| `6n5_battle_crit_flash.jpg` | **實戰**（竹林，種子 7）：盜賊 3 對主角暴擊那一刻——畫面閃白、金色弧光，主角同時格擋（「格擋」字樣） |
| `6n5_battle_crit_block.jpg` | 同一下，停頓結束：「暴擊 −4」放大＋「格擋」 |
| `6n5_battle_dodge.jpg` | **實戰**（竹林）：隊友閃避，「閃避」字樣 |
| `6n5_battle_kill.jpg` | **實戰**（竹林）：敵人被擊倒（「擊倒」、倒下片段） |
| `6n5_battle_block.jpg` | **實戰**（開闊平原，種子 11）：盜賊隊長格擋隊友的攻擊，「−6」「格擋」、大火花、攻擊者被彈開 |
| `6n5_battle_victory.jpg` | **實戰**（開闊平原）：最後一個敵人倒下、我方勝利，「勝利」浮出（全隊播勝利片段） |

實戰的方法：自己啟動的伺服器（8335，存檔在 scratchpad）、build 版、無頭 Chrome（自己的設定檔與 9335／9336 埠，CDP），開始畫面選 2 個關鍵字開戰，`?anim=0.5`，主角一直按「結束回合」讓 AI 隊友和敵人打，回應裡有新的結果時連拍、事後挑。**Boss 大招與復活在實戰沒拍到**：Boss 要 Boss 地圖而且要剛好放蓄力招；復活要有人身上有返魂術（目前只有主角能裝，要手動瞄準），這兩種只在 dev 頁看（同 6N-4 的倒下、陷阱）。
伺服器、vite、無頭 Chrome 都只用 PID 停了自己啟動的程序。內建瀏覽器借用了 6N-4 留下、伺服器已關的分頁（tab-22）看 dev 頁，沒關任何分頁，大小已還原。

## 8. 檢查清單（需求第二批第 5 節）

- [x] 五種強化都觸發得到：觸發條件照第 1 節，測試鎖住；實戰看到暴擊、擊殺、格擋、閃避（Boss 大招在 dev 頁）。
- [x] 多次暴擊每次停頓不超過 0.1 秒，總時間不明顯拖長：同一刻只停一次、每次 ≤ 100 ms、一步 ≤ 200 ms；測試「一場 6 次暴擊」每步 ≤ 100 ms。
- [x] 「跳過」時不停頓；不做慢動作與鏡頭拉近。
- [x] 復活接上倒地圖示沒有跳一下（第一格＝倒下片段最後一格）；勝利只在我方勝。

## 9. 待 PM 決定（都已照最保守的做法做完）

1. **「失手」改成「閃避」**：需求要「閃避」字樣，所以地圖上沒打中的浮動字從「失手」改成「閃避」（戰鬥紀錄文字不變）。若要保留「失手」（攻擊者角度），改回 `feedback.ts` 的 `WORD_DODGE` 即可。
2. **Boss 大招的判斷**：畫面資料沒有「預告技能」的欄位，用「這一步開始前帶 `boss` 標籤、身上有 `charging` 的單位這一步放出技能」。精英的蓄力招不算（需求只寫 Boss）；Boss 開始蓄力（`followup_charged`）那一下不變暗，放出來才暗。
3. **停頓跟著播放速度縮放**：「每次 ≤ 0.1 秒」以正常速度算；慢、極慢、`?anim=` 會等比變長，快變一半。
4. **擊殺「同一輪只強化一次」**：輪數取事件的 `round`；略過播放的步驟不記（下次正常播放時同一輪還會強化一次）。同一步多人倒下只強化最早的一個。
5. **一步停頓總和上限 200 ms**（自訂的原型數值）：多段技能第 3 段起的暴擊不停。
6. **原型數值**：閃白 0.32／140 ms、Boss 變暗 0.6、大火花 11 道、彈開退 8／300 ms、復活與勝利 520 ms、「勝利」字樣 1 秒、金色 `#ffc93a`。
7. **暴擊的「畫面震動」沿用原本的**（3-12 起暴擊就是 2 級震動）；擊殺另外加一次 2 級震動。版面設定關掉震動時兩者都不震，停頓照停。
8. **勝利片段只給人形和異形**：形態、召喚物沒有骨架，只有字樣。勝利時倒下的人不播。
9. **浮動字樣偏大**：「暴擊 −N」沿用 3-9a 放大的字（30px＋6N-10 的彈跳），在 52px 格上會蓋到旁邊；要縮小請美術 PM 定。

## Commit

- `4e3e6aaf` feat(client): special results with hit stops (crit, kill, block, dodge, boss), revive and victory clips (6N-5)
- `e874b180` feat(client): skill gallery #result page for 6N-5; clearer victory poses (sword up, point down)
- 報告與實戰截圖：最後一個 commit
