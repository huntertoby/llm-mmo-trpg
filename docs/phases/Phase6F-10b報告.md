# Phase 6F-10b 報告：6F-10 驗收的補修與補拍

實作者，2026-11-05。分支 `worktree-agent-a5241455b3469db6d`，從 main `7036ceef` 開始（含 6F-10 與 `docs/art/6F-10檢查.md`）。沒有 push，也沒有合併。

**範圍**：只改 `client/`，只改外觀與顯示。
- 沒碰：skillgen 與內容、人物繪製、高度標記。
- 沒有新增相依套件、原生 `title=`、`Math.random`。

**依據**：`docs/art/6F-10檢查.md` 第 2 節待決 3～5、第 3 節 1～5。

**截圖方式**
- 無頭 Chrome，用 `Emulation.setDeviceMetricsOverride` 把視窗真的設成檔名上的尺寸（device scale 1）。
- 加 `--mute-audio`，網址加 `?mute=1`。
- **全圖和放大圖是同一幀**：每一組只拍一次全畫面 PNG，`_zoom` 是在頁面裡用 canvas 從同一張圖裁出來、最近鄰放大的。
  - 6F-10 的放大圖是另外用 CDP 的 `clip.scale` 拍的。這種拍法不是同一幀，而且 Chrome 會用較高的解析度重畫。實測時，召喚物的狀態列因此換成另一種排法，所以這次不用。
  - 800 的放大圖因為是從 1 倍畫面放大，看起來比 6F-10 的模糊，但畫的就是玩家實際看到的像素。
- 畫面都是正式戰鬥畫面。召喚物的 3 個狀態和 6F-10 一樣，是攔下戰鬥 API 的回應補上去的（守護、強化、虛弱，畫成 2 個圖示＋「+1」）。

---

## 1. 推回畫面內的飄字也要錯開（待決 4）

**原因**（`render/floatStack.ts`、`BattleRenderer.playFeedback／makeEffect`）
- 「撞擊！」和「−3」其實是**同一格**的字：主角在 (0,3)，兩次撞擊的字都記在這一格。
- 同一格已經有字時，新的一組接在舊的上面。但 (0,3) 頭頂上方放不下四個字，舊做法（6F-6 `stackedY`）**只把新的一組往下推**，推到剛好在上限。結果新的「撞擊！」就壓在舊的「−3」上。
- 還有一個小錯：位移以「每一組第一個字的中心」為準，兩組的第一個字高度不同（「撞擊！」是放大字，比「−3」高）時，字距會被吃掉幾 px。

**做法**
- `FloatStack.placeGroup`：位置一律從**頭頂線**（第一個字的下緣）算，不同高度的字也對得齊。
- 每一格算出頭頂上方的空間（`floatRoom`）：停住時字的上緣最高到戰場上緣，再往下留飄的距離 `FLOAT_RISE_MAX` 和邊緣空隙 `FLOAT_EDGE_PAD`。這樣字飄到最高也不會被夾回來、壓到下面的字。
- 放不下時，**這一格整疊一起往下推**：
  - 新的一組直接放在推過的位置；
  - 還在畫面上的舊組在 160ms（`FLOAT_SLIDE_MS`，實際時間）內滑下來；
  - 新的一組等舊組滑完才出現（`waitMs`，最多佔整段時間的 40%），滑動途中不會先壓上去。
  - 同一格的字彼此距離不變。
- 左右照舊用 `clampFloatCenter` 每一幀往內推。同一格的字 y 都錯開了，所以推進來的字不會互相蓋住。

**截圖**（開闊平原、種子 1、開場輪到敵人；主角在左緣 (0,3) 撞到地圖邊緣兩次）
- `6f10_2_edge_1600`、`6f10_2_edge_1600_zoom`（覆蓋舊檔）：由下往上是「撞擊！」「−3」「撞擊！」「−7」，四個字都分開。全圖和放大圖都有「−7」。
- `6f10_2_edge_800`、`6f10_2_edge_800_zoom`（覆蓋舊檔）：同樣四個字分開，全圖和放大圖都有「−7」。

## 2. 補拍右緣、下緣

- **右緣**（開闊平原、種子 1，弓手隊友射右緣 (9,5) 的盜賊）：
  - `6f10b_edge_right_1600`、`_zoom`：「閃避」往內推，離右緣約 2px，沒被切掉。
  - `6f10b_edge_right_800`、`_zoom`：同上。
- **下緣**（沼澤、種子 9，第 2 輪盜賊背刺站在最下排 (1,9) 的戰士隊友）：
  - `6f10b_edge_bottom_1600`、`_zoom`：「背刺！」「−7」完整。
  - `6f10b_edge_bottom_800`、`_zoom`：同上。
  - 說明：浮動字從頭頂往上冒，所以最下排的字其實在格子上方，不會碰到戰場下緣，下緣的夾邊實際上不會觸發。這兩張證明最下排的字完整、沒被切掉。

## 3. 補拍選取「喚起骷髏」時的面板和技能列

- `6f10b_summon_pick_1600`（全圖）：
  - `_panel_zoom`：左側選取面板「點選格子上的目標（紅框 13 格）」；
  - `_bar_zoom`：技能列提示「點選紅框格子當目標格（13 格）」，「喚起骷髏」鈕為選取狀態。
- `6f10b_summon_pick_800`、`_panel_zoom`、`_bar_zoom`：同上（800×600）。

## 4. 800 寬的召喚物（待決 3）

做法（`render/unitSprite.ts`；只改召喚物，一般單位的「+N」沒動）：
- **「+N」縮成角標、往右移**：
  - 半徑 4.5 → 4（`SUMMON_MORE_R`），圓心放在第 2 個圖示右上角外側（`summonMoreAt`）。
  - 往右多少照空間決定（`SummonRowLayout.moreDx`）：放得下就往右到完全不重疊（`SUMMON_MORE_DX_MAX`）。
  - 擠的時候依序讓步：
    1. 先把間距縮到兩個圖示剛好相貼；
    2. 再讓角標往左縮；
    3. 最後才縮間距。
  - 結果：
    - 1600：角標蓋到第 2 個圖示約 2%（幾乎完全在外面）。
    - 800：約 17%，只蓋右上角（6F-10 約 36%）。兩個圖示相貼不重疊。
- **徽章靠格子右緣**：
  - 放不下、搬到狀態列上方時，圓心 x 改成 `SUMMON_BADGE_EDGE_X`（`T/2 + 3 − r`）。圓的右緣比格子右緣多出 3px，壓到隔壁格最左邊、沒有人站的那一條。
  - 左緣在格子中心右邊 12.5px，避開骷髏往右伸的手臂和武器（約到 12px，`HUMANOID_ARM_REACH`）。
  - 1600 寬照舊：徽章在原位（狀態列旁邊）。

**截圖**
- `6f10b_summon_800`、`6f10b_summon_800_zoom`。
- `6f10b_summon_1600`、`6f10b_summon_1600_zoom`（對照）。

## 5. 召喚物操控面板（待決 5）

- **原因**：名字和 HP 之間原本靠 JSX 一行開頭的全形空白隔開，但 JSX 會把每一行開頭的空白（含全形空白 U+3000）去掉，所以黏字。
- **做法**：新增 `SummonTitle` 元件，名字和「HP …・剩 N 輪」是兩個元素。`.summon-title` 改成 flex，`column-gap: 0.75em`。放不下時 HP 整段換到下一行。
- **截圖**：
  - `6f10b_summon_1600_panel_zoom`：一行，名字和 HP 中間有空隙。
  - `6f10b_summon_800_panel_zoom`：面板較窄，HP 整段在第二行。

---

## 驗證

**排版煙霧檢查**
- 網址 `/?dev=1&anim=0.1&mute=1`，先 `localStorage.clear()` 再重新載入，跑 `__layoutSmoke.runCase('6F-10b')`。伺服器帶 `TRPG_DEV_ROUTES=1`。
- 1600×900、1040×624、800×600 三個尺寸都是「全 PASS」，各 12 列。
- 主控台照舊有 React 的 `flushSync` 警告（`BattleScreen`，6F-10 就有，這次沒改）。

**6.5.1 浮動卡實測**（功能列「技能」鈕的說明卡）

| 步驟 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 卡片出現 | ✓（707～821） | ✓（436～550） |
| 滑進卡片後不關 | ✓ | ✓ |
| 卡內捲動後不關 | ✓（卡片 106px，沒有可捲的內容，只確認不關） | ✓ |
| 點一下釘住 → 滑出去不關 | ✓ | ✓ |
| Esc 關閉 | ✓ | ✓ |

截圖：`6f10b_float_1600_pinned`、`6f10b_float_800_pinned`。

**交件前的完整檢查**
- client 全部 vitest：**250 個檔、2833 項全過**，結束碼 0。
- `corepack pnpm -C client build`（含 `tsc --noEmit`）：結束碼 0。

**程序**
- 自己啟動的程序：
  - API 8359（`scratchpad/f10b/serve.py`，存檔在 `scratchpad/f10b/saves`）
  - vite 5359（暫時設定 `client/vite.f10b.config.mts`，已刪除，沒有 commit）
  - CDP 9591、9593 的無頭 Chrome
- 結束時只用這些程序的 PID 關掉。
- 沒碰 8000、8001、8010、`tmp_x`、`saves/`。暫存都在 `scratchpad/f10b/`，沒有 commit。

## 檔案清單

**新增**
- `client/src/ui/fix6f10b.test.ts`
- 截圖 `docs/art/6f10b_*`，共 22 張：
  - 右緣、下緣 8 張
  - 選取喚起骷髏 6 張
  - 召喚物與操控面板 6 張
  - 浮動卡 2 張
- 本報告

**覆蓋**
- `docs/art/6f10_2_edge_1600.jpg`、`_1600_zoom.jpg`、`_800.jpg`、`_800_zoom.jpg`

**修改**
- `client/src/render/floatStack.ts`：`placeGroup`、`PlacedGroup`、`FLOAT_SLIDE_MS`；位移改從頭頂線算
- `client/src/render/BattleRenderer.ts`：`floatRoom`；`FloatSpot` 多了 `firstH`、`shiftAt`、`waitMs`；`makeEffect` 不再用 `stackedY`
- `client/src/render/unitSprite.ts`：`SUMMON_MORE_R`、`SUMMON_MORE_AT`、`SUMMON_MORE_DX_MAX`、`SUMMON_MORE_SQUEEZE_DX`、`SUMMON_MORE_OUT_Y`、`SUMMON_BADGE_EDGE_X`、`HUMANOID_ARM_REACH`、`summonMoreAt`；`summonRowLayout` 多回傳 `moreDx`
- `client/src/ui/SummonPanel.tsx`：`SummonTitle`
- `client/src/styles/battle-panels.css`：`.summon-title`
- `client/src/ui/fix6f10.test.ts`：召喚物排法的期望值跟著改：角標寬度、徽章搬到上方時改看 `SUMMON_BADGE_EDGE_X`、徽章右緣上限 `T/2 + 3.5`

## 測試數

`fix6f10b.test.ts` 共 12 項：
- **第 1 項（5 項）**
  - 兩組第一個字高度不同時仍留空隙；
  - 放不下時整格一起推：舊組滑完和新組位置一致；四個字（舊組飄到最高）兩兩不重疊；新組上緣不超過 room；
  - 滑動平順、新組等 `FLOAT_SLIDE_MS`；
  - 放得下不推不等、別格不受影響；
  - 接線。
- **第 4 項（4 項）**
  - 「+N」蓋到圖示的面積：1600 寬 < 3%、800 寬 < 舊做法的一半、圓心在圖示外；兩個圖示不重疊；
  - 各種倍率 × 炸彈 × 圖示數：狀態列在格子內、和徽章不重疊；
  - 800 寬徽章靠右緣、左緣在手臂外，1600 寬照舊；
  - 接線。
- **第 5 項（2 項）**
  - `SummonTitle` 輸出兩個元素、CSS 的 `column-gap`；
  - 操控面板用 `SummonTitle`、`SummonPanel` 沒有行首全形空白。
- **原始碼掃描（1 項）**：不用 `Math.random`、不用原生 `title=`。

`fix6f10.test.ts` 19 項、`fix6f6.test.ts`、浮動卡規則 `floatCardRule.test.ts` 照舊全過。

## commit

- `ad74dc16`：推回畫面內的飄字照同一格堆疊，整格一起往下推
- `c10ef3cf`：召喚物「+N」角標、徽章靠右緣、操控面板名字和 HP 分開
- 最後是截圖與本報告

## 待 PM 決定

以下都照最保守的做法先做完了：

1. **整格往下推時，舊字會滑下來（160ms）**，新字晚 160ms 才出現。另一個做法是舊字直接跳下去（不滑），新字就不用等。
2. **800 寬的「+N」角標仍蓋到第 2 個圖示右上角約 17%**。800 寬時兩個圖示放大到 1.71 倍，加上完全不重疊的「+N」，寬度會超過格子。如果要完全不重疊，只能二選一：
   - 縮小圖示，但會違反 6F-9 定的 10px 下限；
   - 只顯示 1 個圖示＋「+2」。
3. **一般單位（非召喚物）的「+N」沒有改**，還是蓋在第 2 個圖示右上角（約 36%）。要不要統一改成角標？一般單位在 800 寬時沒有徽章，但同樣要算格子寬度。
4. **800 寬召喚物的徽章右緣壓出格子 3px**，進到隔壁格最左邊、沒有人站的那一條，這樣才避得開骷髏的手臂和武器。徽章本身在 800 寬時很小（半徑 7 世界 px，畫面上約 4.5px），「3」不太好讀。這次沒有放大，因為不在這次的範圍內。
5. **下緣的飄字**：浮動字從頭頂往上冒，最下排的字在格子上方，碰不到戰場下緣。下緣的夾邊程式有寫，但實際戰鬥中不會觸發。
6. **同一個 JSX 行首全形空白的問題還有 6 處**，都在世界畫面，不在這次的範圍內，沒有改：
   - `world/QuestLog.tsx` 28、56 行
   - `world/WorldGrowth.tsx` 49 行
   - `world/LeaguePanel.tsx` 76 行
   - `world/BoardPanel.tsx` 154 行
   - `run/FlashChooser.tsx` 86 行
   
   這些地方的空白都會被吃掉，造成黏字。
7. **800 寬時操控面板的 HP 換到第二行**（面板較窄），每隻召喚物多一行高。如果想維持一行，可以改成縮小字級或拿掉「・剩 N 輪」。
