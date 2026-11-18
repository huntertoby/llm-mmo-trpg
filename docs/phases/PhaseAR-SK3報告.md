# Phase AR-SK3 報告：SK-3 新機制與距離條件的美術移植（前端）

> 依據：`docs/art/SK-3-移植需求.md`（第 1 節 6 項、第 2 節定案字、第 4 節 AR-SK2 小修與裁定）、`docs/art/SK-3-美術.md`（第 5 節、第 8 節第 2 版＋N1）、`docs/art/AR-SK2驗收.md`、樣張 `docs/art/sample/sk3Mechanics.js`／`sk3-mechanics.html`。
> 分支 `worktree-agent-a7a017ebd2dddbd64`（起點 main `ad7260766`；worktree 原本停在 `ca9d0fa08`，先快轉到起點）。
> 只改前端：沒有改 `docs/design/`、`config/`、引擎規則、後端 Python，也沒碰 `llmFlow.ts`、組合器、驗證器、LLM、淨化、疾病擴散後端。

## 0. 結論

| 項目 | commit | 一句話 |
|---|---|---|
| 1 部件：重擲、三個觸發、貼身、遠距 | `437f287f8` | 照樣張第 2 版逐行搬進 `qIcon/parts.ts`；拿掉 `EFFECT_ALIAS.reroll`、`TRIG_ALIAS` 三筆、`COND_ALIAS` 兩筆 |
| 第 4 節：吸收表面照表面染色 | `27395ea37` | 技能指定的表面 → `QS.TINT` 的色（黑暗＝暗影色），沒有對應色用水色 |
| 第 4 節：「+2」膠囊被孢子蓋到、框邊 ≥14 px 換狀態卡排法 | `dac23ea37`（＋`6552a9ee4` 小修） | 第 2 個圖示有記號時角標膠囊往右讓到孢子外；畫面框邊 ≥14 px 時記號改畫狀態卡大小 |
| 2、4、6 重擲演出、畫面下限、頭目骰子位置 | `5bea4ea64` | 骰子層（時間軸純函式＋Canvas 畫法＋效果）；MK＝max(1, 9÷(11×縮放))、「採用」≥10 px；巨型、頭目照 `unitTopY` |
| 2、3 接到播放、浮字延到 1250 ms | `4c14a4491` | 骰子層排在出招前；「重擲！」從回饋搬到骰子比較完才出 |
| 5 戰前佈置的格子記號與定案字 | `6a3fc0a66` | 金色四角括號＋菱形、指著整圈金框＋預覽＋「放在這裡」、放下的一下；兩處提示字照定案 |
| 開發頁 | `39d11ab21`、`b84b713d7` | `sk3-gallery` 加四種情況、`&w=`、`&strip=`、`&upper=1`、`&boss=`、`&slow=`；新 `arsk3-gallery`；`arsk2-gallery` 加 `&scale=` |
| 截圖 | `fa5dc58c3` | `docs/art/shots/ar-sk3/` 12 張 |

## 1. 各項做法

### 1.1 部件（需求第 1 項）
- `sk3Mechanics.js` 的 `d20`、`rerollArt`、`hand`、`touchLines`、`target` 與 `EFFECT／TRIG／COND` 逐行搬；`DIE`（四組骰色）、`d20` export 給戰場的骰子層共用。第 1 版的 `cwArrow`、`bolt` 沒搬。
- 加在各表最後：`EFFECT` 的 `SK3_EFFECT.reroll`、`TRIG` 三個、`COND` 兩個。被利用的旗用 `banner(q, { ...o, tiny: true })`。新色照 5.1 第 2 點寫死在部件裡（同 `STEEL` 的做法）。
- 別名：`EFFECT_ALIAS` 剩 3 筆、`TRIG_ALIAS` 剩 7 筆、`COND_ALIAS` 變空表（保留 export，`skillParts.KNOWN_PARTS` 照舊讀它）。

### 1.2 重擲演出（需求第 2、4、6 項）
- **描述與時間軸**（`battle/rerollFx.ts`，純函式）：`rerollFxOf` 讀 `attack_rerolled`（擲骰者＝`attacker_id`、反應者＝`unit_id`、兩次自然骰、`kept`、`keep`）。`rerollFrame(t)` 照樣張 `rerollTop` 的時間軸算每一刻的骰子狀態（彈出、停、光圈、引線、敲、退、轉、落地、比較、金環、採用、紅斜槓、淡出）。比較箭頭一律米白（N1）。
- **畫法**（`render/rerollEffects.ts`）：`fieldDie`／`fieldKnock`／`fieldAdopt`／`fieldBeam`／`fieldPulse`／`fieldCmp` 逐行搬；一張離屏 canvas（沿用 AR-SK2 的 `canvasEffect`），畫在單位之上的效果層。
- **位置**：中心＝擲骰者單位節點＋`dieDy(MK, top)`。一般單位 `top`＝上一排血條下緣（1600 寬約 −8.1、800 寬約 +0.9，同樣張）；巨型單位、頭目（`isGiantDraw` 或 `creatureOf(u).boss`）用它自己的 `unitTopY`，整組上緣收在頭頂下 1（不往上長到 HUD）。
- **畫面下限**：`MK = max(1, 9 ÷ (11 × 地圖縮放))`；骰子、引線、短金線、比較箭頭都乘 MK；「採用」字級 max(12, 10 ÷ 縮放)。
- **接到播放**（`playback.ts`）：`Frame.reroll`，`frameOps` 在出招的 `vfx` 之前加 `reroll` 操作。`usePlayback` 播骰子層、等到 1250 ms 播浮字、再等到 1450 ms 才接現行的出招與命中／失手。一步有多次重擲時一個接一個。
- **浮字「重擲！」**：字、顏色、位置照現行（`feedbackFor` 的同一個項目），只是從這一步的回饋搬到骰子層的 1250 ms 才出。
- **減少動態**：不播骰子層，浮字照舊在回饋裡（同 SK-2 演出的做法）。

### 1.3 戰前佈置（需求第 5 項、第 2 節）
- `battle/prep.ts::prepMarksOf`：只畫這一招放得下的格子；指著放得下的格子才算 hover；表面的預覽讀技能卡第一個 `create_surface` 的表面。
- `useHighlights`：選目標模式的 key 是 `prep:` 時不畫紅框與施放範圍，改給 `Highlights.prep`；指著佈置格時不另畫白框。
- `render/prepMarks.ts`：`placeMark`、`placeBurst` 逐行搬，畫在畫面 px（貼圖照地圖縮放×DPR 出圖再貼回一格）。待放格括號 1.2 秒呼吸一次（`tickBobs`，每 50 ms 重畫；減少動態時不動）。
- 預覽：陷阱＝`fieldFx.drawTrapPad`（我方、踩到觸發、灰），刻印＝`drawRunes` 那段（我方藍框、灰），表面＝部件圖樣，透明度 68%。
- 滑過提示「放在這裡」：現行戰場沒有格子滑過提示框元件，照樣張的 `tipAt` 畫在格子右邊（深藍底、金色細框、米白 12 px），放在 Pixi 的 hover 層。
- 放下的一下：`prep_placed` → `Frame.placed`，畫面更新之後播 420 ms（`playPlaceBurst`）。
- 字：視窗「在框起來的起始區格子點一下」、技能列「再點框起來的我方起始區格子放下」、滑過「放在這裡」。

### 1.4 AR-SK2 小修（第 4 節）
- **「+2」膠囊**：1600 寬第 2 個圖示帶記號時，角標膠囊的 `moreDx` 至少讓到孢子（含小點、外框、對齊裝置像素）右緣之外（`spreadMark.headSporeRight`）。碰撞判斷的形狀也照讓開後的位置算。
- **吸收表面染色**：`QP.surfaceTint(surface)`。部件（`effectPart` 帶 `q.tint`、`drawChip`）、完整圖示效果列（`QPartItem.tint`）、組裝列快取鍵（有染色時加在 id 後）都接上。AR-SK2 的演出改用同一個函式。
- **框邊 ≥14 px 換排法**：畫面框邊＝9 × 地圖縮放 × 反向放大。≥14（約縮放 1.56 以上）時，戰場記號改畫狀態卡大小（孢子 2.2、小點 1.1 畫面 px）；小於 14 照 AR-SK2 原樣。
- **演出差異**：照裁定不補。

## 2. 逐項對照需求

| # | 需求 | 狀態 | 截圖 |
|---|---|---|---|
| 1 | 重擲、三個觸發、兩個條件；拿掉 `*_ALIAS` 暫借；新色 | 完成 | `1-icons.png` |
| 2 | 骰子在擲骰者那一格、第一次往左退、敲擊短金線、比較（米白箭頭）、採用＋金環、劃掉的紅斜槓；四種情況 | 完成 | `2-anim-reroll-worse.jpg`、`3-anim-reroll-better.jpg` |
| 3 | 浮字「重擲！」延到 1250 ms；字、位置、顏色不改；上一排有人 | 完成 | `4-float-upper-row-1600.png`、`5-float-upper-row-800.png` |
| 4 | 骰子半徑 ≥9 畫面 px、「採用」≥10 px | 完成 | `6-anim-800-true1x.png` |
| 5 | 金色四角括號＋菱形、只畫放得下的格子、指著整圈金框＋半透明預覽、放下的一下 | 完成（實機未看，見第 3 節） | `8-prep-1600.jpg`、`9-prep-800-true1x.png` |
| 6 | 巨型單位、頭目的骰子位置照 `unitTopY` | 完成 | `7-boss-roll.jpg` |
| 字 | 部件名、採用、框起來的起始區（兩處）、放在這裡 | 完成 | `1`、`2`、`8`、`9` |
| 4.1 | 1600 寬「+N」膠囊不被孢子蓋到 | 完成 | `11-status-field-1600.png` |
| 4.2 | 吸收表面照表面代表色染色，沒有對應色用水色 | 完成 | `10-absorb-tint.png` |
| 4.3 | 框邊 ≥14 px 時用狀態卡排法 | 完成 | `12-status-field-scale1.7.png` |
| 4.4 | SK-3b 輸出 `contagious` 後補拍 3 張 | 不在這段（等 SK-3b） | — |

## 3. 截圖（`docs/art/shots/ar-sk3/`，12 張）

- 無頭 Chrome 的參數：`--headless=new --mute-audio --remote-debugging-address=127.0.0.1 --force-device-scale-factor=1`，CDP `deviceScaleFactor 1`。量到 `devicePixelRatio = 1`，網址帶 `mute=1`。
- 用的埠：vite `127.0.0.1:5317`、除錯埠 9757，開之前兩個都沒人聽。結束時只停了自己起的 vite 與 Chrome，兩個埠都已沒在聽。
- 裁切與最近鄰放大用暫存區的腳本（Pillow），沒有 commit。

| 檔案 | 內容 | 重拍 |
|---|---|---|
| `1-icons.png` | 六個部件：30／26／18（條件加 16）、真 1 倍 ×6、18 的 2 倍 ×4 | `arsk3-gallery.html?part=icons` |
| `2-anim-reroll-worse.jpg` | 變壞、被逼重擲反而變好：120／360／520／760／1120／1350 ms，1600 真 1 倍 ×2 | `sk3-gallery.html?case=reroll_worse｜reroll_worseup&w=1600&strip=…&slow=4` |
| `3-anim-reroll-better.jpg` | 變好、沒比較好：同上 | `case=reroll_better｜reroll_keepfirst` |
| `4-float-upper-row-1600.png` | 上一排站人＋浮字：120／760／1120／1350，1600 ×2 | `&upper=1&w=1600` |
| `5-float-upper-row-800.png` | 同上，800 ×4 | `&upper=1&w=800` |
| `6-anim-800-true1x.png` | 四種情況 520、1120 ms，800 真 1 倍 ×3 | `&w=800&strip=520,1120` |
| `7-boss-roll.jpg` | 灰燼之心（3×3）、碎晶之主擲骰：120／520／1120／1350 | `&boss=giant｜lord` |
| `8-prep-1600.jpg` | 戰前佈置視窗（定案字）、技能列提示、待放三格、指著＋陷阱／刻印／表面（冰）預覽＋「放在這裡」、放下的一下 140 ms，下面 ×2 | `arsk3-gallery.html?part=prep&w=1600` |
| `9-prep-800-true1x.png` | 同上，800 寬，下面 ×4 | `&w=800` |
| `10-absorb-tint.png` | 吸收表面：沒指定、水、火、冰、毒、聖光、黑暗、油、煙霧 | `arsk3-gallery.html?part=tint` |
| `11-status-field-1600.png` | 1600 寬狀態列，下排 4 種的「+2」膠囊讓到孢子外 | `arsk2-gallery.html?part=field&w=1600` |
| `12-status-field-scale1.7.png` | 地圖縮放 1.7（框邊 15.3 px）：記號換狀態卡排法 | `&scale=1.7` |

### 實機未看
- **重擲**：真人戰鬥裡沒有招會重擲（接進出題是 SK-3b）。演出只在開發頁用真引擎事件看過。其中「被逼重擲反而變好」「沒比較好」兩種是改真引擎事件的點數與 `kept` 做出來的。
- **戰前佈置**：在開發頁用遊戲端的 `BattleRenderer`＋`PrepDialog` 畫的，沒有開 `trpg serve` 走實機。所以 `useHighlights` 的接線（選了一招後換成金色記號）只有單元測試，沒有實機截圖。放下的一下也是開發頁直接呼叫的。
- **巨型頭目**：「重擲！」浮字照現行的位置出，會疊在骰子上面（`7-boss-roll.jpg`）。碎晶之主的浮字在 HUD 上方。
- `prompt` 模式（真人選要不要用反應）沒拍，見待決 2。

## 4. 測試與檢查

| 檢查 | 結束碼 |
|---|---|
| `npx tsc --noEmit -p client` | 0 |
| `vitest run`（全部，380 檔、4732 個） | 0 |
| `corepack pnpm -C client build`（含 tsc） | 0 |

新增測試：
- `battle/arSk3Reroll.test.ts`（15）：描述、位置與畫面下限、時間軸、接到播放、減少動態。
- `battle/arSk3Prep.test.ts`（5）：只畫放得下的格子、hover、表面預覽、定案字、放下的一下。
- `render/arSk3SpreadMark.test.ts`（4）：排法門檻、狀態卡大小、膠囊讓開。
- `render/arSk3AbsorbTint.test.ts`（3）：表面色、部件、完整圖示效果列。

改到的既有測試：都是「新增部件就要更新」的清單，沒有放寬斷言。
- `qIconSkills.test.ts` 的數量：
  - 效果圖 54 → 55（效果碼仍是 58：圖 +1、暫代 −1）。
  - 條件 22 → 24。
  - 觸發 22 → 25。
  - 觸發暫代 10 → 7。
- `qIconQi2d.test.ts` 的 `ADDED_PARTS`：加 6 個部件。它們是基準錄好之後才加的，沒有開工前的雜湊；做法同 AR-SK2。

自查失誤：第一次跑全部 vitest 時，`ui/summonBadges.test.ts` 的原始碼掃描斷言（`moreCapBox(..., lay.moreDx, extra)` 這一行字面）失敗。改成在 `apply` 開頭先做讓開，那一行照原樣保留，沒有改斷言（`6552a9ee4`）。

沒有改 Python，所以沒跑 ruff、mypy、pytest。

## 5. 新增 `# noqa`
沒有（沒改 Python）。

## 6. 待 PM 決定

1. **重擲的時間點**（解讀，保守做法）：骰子層整段（1450 ms）排在這一步出招之前，播完才出招、出命中或失手。
   - 這樣每次重擲會讓那一步多 1.45 秒（照播放速度縮放）。
   - 樣張只有骰子層、沒有畫出招，所以「接現行的命中／失手」我解讀成骰子層之後才播整個攻擊。
2. **`prompt` 模式的停頓點**（5.2 第 6 點）：沒有接。
   - 真人選要不要用反應時，詢問出現在重擲之前，回應裡還沒有 `attack_rerolled`，前端不知道第一次的點數。
   - 選了之後的回應才照完整時間軸從 0 播；不用就沒有骰子。
   - 要做到「160–260 ms 停住等選擇」，需要伺服器在詢問裡帶第一次的點數，屬於後端，這次沒做。
3. **巨型頭目的「重擲！」浮字**：浮字照現行的位置出，在 3×3 頭目身上會和骰子疊在一起（`7-boss-roll.jpg`）。要不要改位置請美術 PM 看。
4. **戰前佈置的預覽色**：陷阱、刻印的預覽一律用沒有元素的灰（同樣張）。技能的元素色沒讀。
5. **滑過提示的元件**：「放在這裡」用 Pixi 畫在格子右邊（照樣張）。現行 HUD 沒有格子滑過提示框元件，沒有用 DOM 的 `Hint`。起始區在地圖最右欄時，提示可能超出地圖。
6. **黑暗表面的代表色**：`QS.TINT` 沒有 `darkness`，對照到暗影色（`shadow`）。油、煙霧沒有對應色，用水色。
7. **戰前佈置沒有實機截圖**：如果要實機，需要排一段用 `trpg serve` 帶工坊陷阱技能重拍（做法同 SK-3 報告第 5 節）。
8. **SK-3b 之後補拍**：`contagious` 的實機截圖 3 張（第 4 節第 4 點）。
