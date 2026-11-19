# Phase AR-AP2 報告：預支美術移植（前端）

> 依據：`docs/phases/PhaseAR-AP2計畫.md`、`docs/art/AP-2-移植需求.md` 第 1 節 7 項、`docs/art/AP-2-美術.md` 第 5 節（逐行照做）、第 9 節裁定；樣張 `docs/art/sample/ap2Borrow.js`。
> 分支 `worktree-agent-a5164fa9e14bba167`（先 `git merge main`，基準 `7ede8c01f`）。
> 只改前端 `client/` 和部件暫代清單（vitest 的部件計數）。沒改 `src/`、`content/`、`tests/`（Python）、`docs/design/`。

## 0. 結論

| # | 項目 | commit | 一句話 |
|---|---|---|---|
| 1 | 狀態「預支」`borrowed_ap` | `088ec3560` | 換成 `parts.ts::borrowArt`（和效果同一個圖）；頭頂 11 是挖洞的菱形。`statusFit.json` 重量頭頂那一鍵（0.88 → 0.96），`qi3bStatusBaseline.json` 只重錄兩鍵 |
| 2 | 效果原語「預支」`borrow_ap` | `29b481a6a` | `EFFECT` 最後加 `AP2_EFFECT.borrow_ap`；`EFFECT_ALIAS` 拿掉暫借的 `grant_ap` |
| 3 | 觸發 `on_ap_spent_all` | `c9fb2f367` | `TRIG` 最後加灰閃電＋金火花（`spentBolt`／`spentAll`）；`TRIG_ALIAS` 拿掉暫借的 `on_turn_end` |
| 4 | 施放演出 `borrow_pull` | `c60edd4d8` | 新片段 320 ms ＋新 fx `borrowSlot`；照 SK-3 拆檔：時間軸 `battle/borrowFx.ts`、畫法 `render/borrowEffects.ts`；胸口用 `chest()`（腳底往上 16.8）、往面向 3 |
| 5 | AP 列在 215 ms 淡入 | `4adfdd702` | `frameOps` 在畫面更新那一步帶 `apFadeDelayMs`；播放器設 CSS 變數 `--ap-fresh-delay`，200 ms 淡入的起點對齊演出 215 ms |
| 6 | `statusIcon.ts` 註解 | `ae69c15aa` | 改成「Q 版已正式補畫；線稿不會出現，沿用透支」，圖沒動 |
| 7 | 部件暫代清單拿掉這三樣 | `3ec1ce192` | 補一組斷言：三樣都不在 `*_ALIAS`、施放動作不再共用拍肩、狀態不是暫用圖（計數的改動見下面說明） |
| — | 開發頁 | `bd97bdf62` | `client/dev/arap2-gallery.html`（`?part=icons｜status｜field｜anim｜aprow&w=1600｜800`） |
| — | 截圖 | `1e0bceace` | `docs/art/shots/ar-ap2/` 8 張 |

說明：部件計數（`qIconSkills.test.ts`：效果 55 → 56、觸發 25 → 26、觸發暫代 8 → 7；`qIconQi2d.test.ts` 的 `ADDED_PARTS` 加兩個）跟著第 2、3 項的 commit 一起改。拆到第 7 項的話，第 2、3 項的 commit 單獨跑會失敗。

## 1. 各項做法

### 1.1 部件與狀態（第 1、2、3 項）
- `ap2Borrow.js` 的 `gem`、`slot`、`borrowArt`、`spentBolt`、`spentAll` 逐行搬進 `qIcon/parts.ts`。`at`、`star4`、`halo`、`poly`、`ln`、`ci`、`el` 用遊戲端原有的。
- 三個混色用 `core.ts` 的 `mix` 算，測試確認算出來是 `#ffc793`、`#ffac5d`、`#b3a994`。新色寫在部件裡（`BORROW`、`SLOT_ICON`、`SPENT`），同 `STEEL` 的做法。`BORROW`、`SLOT_ICON`、`gem` 有 export，給戰場演出共用。
- 判斷頭頂 11 用 `36 / o.u < 8`，照搬樣張。遊戲端 `render()` 的 `u = 48 / px`，和樣張的算法一致。
- `statusFit.json`：開發頁 `status-gallery.html?set=fitgen`（無頭 Chrome、`--disable-gpu`）量到狀態卡 1、頭頂 0.96，和樣張相同。只改這兩鍵；狀態卡那鍵本來就是 1。

### 1.2 施放演出（第 4 項）
- `skillClips.ts`：新增 `borrow_pull`。
  - 長度 320 ms，錨點 `offhand`。
  - 關鍵影格照 5.3 第 2 點的建議值：0.34 前伸、0.75 拉回、1 回站姿。
  - fx 是 `borrowSlot`，從 0 播到 1。
  - `PRIMITIVE_PLAYS.borrow_ap` 改成 `borrow_pull`，不再帶 `icon: "ap"`。
- `battle/borrowFx.ts`（純函式）：
  - `borrowMK`＝max(1, 4.5 ÷ (5 × 縮放))。
  - `slotAt`：前推 17＋(MK−1)×8；y＝max(−9, 上一排血條下緣＋1＋(6.5+1.9)×MK)。
  - `chestAt`：腳底往上 T×0.35、往面向 3。
  - `borrowFrame(t)`：照第 4 節的時間表。
- `render/borrowEffects.ts`：`fieldGem`、`fieldSlot`、`fieldArrive` 逐行搬。用 AR-SK2 的 `canvasEffect` 畫一張離屏 canvas，放在效果層。
- `skillLayer.rowCues` 遇到 `borrowSlot` 改走 `borrowCue`：
  - 中心是施放者的單位節點；面向西為 −1，其他方向為 ＋1。
  - 速度倍率＝這一列的 ms ÷ 320。
  - 標成 `motion: "fx"`，減少動態時不畫。
- `sk2Effects.canvasEffect` 的 host 型別放寬成 `Pick<Sk2Host, "deco">`（只用到 `deco`），行為不變。

### 1.3 AP 列淡入（第 5 項）
- 實測：只有預支的那一步，畫面更新（AP 列換成預支後的樣子）在預支演出開始前 **182 ms** 就發生了（1600、一般速度）。照現行做法，AP 列會比動作早出現。
- `borrowFx.borrowApDelayMs(rows, viewAt)` 算延後幾毫秒：
  - 畫面更新在演出 215 ms 之前：延後到 215 ms。
  - 畫面更新在 215 ms 之後：等到 320 ms。
  - 這一步沒有預支演出：0。
  - 會照播放速度縮放。
- `frameOps` 算出 `viewAt`（`leadMs`＋命中停頓＋出招後的位移時間），在 `view` 操作帶 `apFadeDelayMs`。
- `usePlayback` 在 `view` 前呼叫 `ui/apFade.delayApFade(ms)`，設 `--ap-fresh-delay`。淡入播完（延後＋200＋50 ms）就清掉。略過、減少動態時不延後。
- CSS：`.stat-pip.ap.fresh { animation: ap-borrow-in 0.2s ease-out var(--ap-fresh-delay, 0ms) backwards; }`。淡入長度 200 ms 沒動；延後期間圓點先藏起來。
- 截圖 `7-aprow-1600.png`：100、214 ms 看不到菱形與紅斜線；216 ms 剛開始淡入；320 ms 約一半；420 ms 全亮。

## 2. 逐項對照與截圖（`docs/art/shots/ar-ap2/`）

| # | 檔案 | 內容 | 對照 |
|---|---|---|---|
| 2、3 | `1-icons-true1x.png` | 效果、觸發：30／26／18（每組左邊暫借、右邊新圖），真 1 倍 ×6 最近鄰，18 的 2 倍 ×4 | `ap2-borrow/1`、`2-icons-true1x` |
| 1 | `2-status-true1x.png` | 透支、預支：狀態卡 20、說明行 16、頭頂 11，各有真 1 倍 ×6 | `2-icons-true1x` 下排 |
| 1 | `3-field-1600-true1x.png` | 戰場狀態列 1600：法師＝透支＋預支、戰士＝預支、弓手＝透支；整張真 1 倍，下面 ×3；附狀態卡 20 | `5-status-row-true1x` |
| 1 | `4-field-800-true1x.png` | 同上，800 寬、×4（見待決 1） | 同上 |
| 4 | `5-anim-1600-true1x.png` | 50／110／170／220／270／310 ms，三種站位（a 頭頂兩個狀態、b 面前有人、c 面向西），上一排站人；真 1 倍 ×2 | `7`、`9-anim-cases-1600` |
| 4 | `6-anim-800-true1x.png` | 同上，800 寬、×4 | `8`、`10-anim-cases-800` |
| 5 | `7-aprow-1600.png` | 100／214／216／270／320／420 ms 的戰場＋主角 AP 列 | 裁定 4 |
| 5 | `8-aprow-800.png` | 同上，800 寬 | 裁定 4 |
| 6、7 | — | 不用截圖 | — |

截圖做法：
- 自己起 vite `127.0.0.1:5341`，開之前沒人在聽。
- 無頭 Chrome 的參數：`--headless=new --mute-audio --disable-gpu --force-device-scale-factor=1 --screenshot`，網址帶 `mute=1`。沒開除錯埠。
- 裁掉背景用 Pillow（`uv run --no-project --with pillow`），腳本在 scratchpad，沒有 commit。
- 真 1 倍是 Pixi `extract.canvas` 拿到的整張戰場；最近鄰放大是 canvas 畫的（`imageSmoothingEnabled=false`），全部存 PNG。
- 這次沒有向量放大的關鍵影格，所以沒有 jpg。
- 每一格演出各用一個 `BattleRenderer`：停掉 ticker，每次手動推 10 ms，停在預支演出開始後的指定毫秒。走的是正式的 `playbackPlan → frameOps → playSkill／playVfx`。
- 事件是真引擎跑的：`client/src/dev/fixtures/ap2Events.json`，U1 施放預支 +1；產生腳本在 scratchpad，借 `tests/engine` 的 helper。開發頁把 `skill_used.tiles` 換成施放者所在的格子，不然施放者會轉向產生事件時站的舊格子 (1,3)。

我看到：
- 部件、狀態和樣張 `2-icons-true1x` 同形。頭頂 11 是中間有洞的橘菱形；18 真 1 倍看得到灰圈和紅斜線。
- 演出各格和樣張 `9`、`10` 的位置、時間點一致。1600 寬那格在法師杖旁、胸口高度，上一排沒被蓋到。800 寬那格會蓋到自己的頭頂狀態列，面前有人時碰到他身體左緣，這是移植需求第 2 節說可接受的現象。西向對稱到左邊。
- 50、110 ms 法師身上那一大圈淡粉紅的圈，是現行 aura 骨架起手自帶的特效（片段 `circle`／`ring`），不是這次加的。樣張沒有畫起手。

收尾：只停了自己起的 vite（PID 44140），5341 已沒在聽。Chrome 每次截完自己結束。

## 3. 測試與檢查（交件前）

| 檢查 | 結束碼 |
|---|---|
| `npx tsc --noEmit -p client` | 0 |
| `vitest run`（全部，387 檔、4785 個） | 0 |
| `corepack pnpm build`（含 tsc） | 0 |

新增測試：
- `render/arAp2Borrow.test.ts`（6）：狀態＝`borrowArt`、頭頂 11 挖洞、效果與觸發的專屬圖與別名、暫代清單、混色。
- `battle/arAp2BorrowFx.test.ts`（13）：片段、播放計畫（真引擎事件）、MK、那格位置與上緣、胸口、時間軸、AP 列延後（含真播放計畫的 215 ms 對齊）、CSS、`delayApFade`。

改到的既有測試，都是「換圖就要改」的清單，沒有放寬斷言：
- `qIconSkills.test.ts`：數量照實改；另加一條 `TRIG_ALIAS` 長度為 7 的斷言。
- `qIconQi2d.test.ts`：`ADDED_PARTS` 加 `effect:borrow_ap`、`trigger:on_ap_spent_all`。這兩個以前走別名，沒有基準。
- `qi2cStatusUnchanged.test.ts`：照 5.2 第 3 點，只重錄 `head|borrowed_ap`、`card|borrowed_ap`。
- `skillClips.test.ts`：共用拍肩的那一組拿掉 `borrow_ap`。
- `qIconStatus.test.ts`：只改註解。

自查失誤：開發頁第一版用內聯樣式 `position: absolute` 把畫布藏到畫面外，`floatCardRule.test.ts` 抓到了。改用 html 裡的 class 之後，重做開發頁與截圖那兩個 commit（還沒 push）；重拍比對，像素完全相同。

沒有改 Python，所以沒跑 ruff、mypy、pytest。

## 4. 新增 `# noqa`
沒有。

## 5. 待 PM 決定

1. **800 寬時主角兩個狀態畫成「+2」**（`4-field-800-true1x.png`、`6-anim-800` 的 (a)）：
   - 主角法師（有標記 A、朝向三角形）頭頂有透支＋預支兩個狀態時，現行狀態列排不下兩個圖示，退成只畫「+2」。
   - 樣張 `5-status-row-true1x` 的 800 寬是兩個都畫。
   - 這是 `rowLayout` 的現行排法（6F-13／6F-19），不在這段範圍，沒改。要不要讓 `pairRow` 在這種情況也排兩個，請美術 PM 看。
2. **AP 列延後的解讀**：
   - 畫面更新晚於 215 ms、早於 320 ms 時，我照「做不到就在 320 ms 之後」等到 320 ms。
   - 略過、減少動態時不延後，照現行在畫面更新就淡入；減少動態時演出的特效本來就不畫。
3. **面向南、北時的「那格」放在東側（＋1）**：樣張只有東、西兩向。預支是自身技能不轉身，所以朝南、北的施放者照東向畫（同 `sk2Host.side` 的規則）。
4. **身體關鍵影格**照 5.3 第 2 點的建議值（`armF`／`elbowF`），沒有微調；1600 真 1 倍只看得出幾個像素的差別。
5. **aura 起手的粉紅圈**：預支施放時，現行起手的大圈和新演出的前 110 ms 疊在一起（`5-anim-1600` 的 50、110 ms）。這不在這段範圍，要不要讓預支不播起手特效，請美術 PM 看。
