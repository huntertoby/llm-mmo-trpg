# Phase PB-1f 完成報告｜頭目部位「破」字記號修正＋前端小項

> 規格：美術 PM 裁定 `docs/art/PB-1e驗收.md` 末節（待決 1、2、5、6，可修 2）；前一段 `docs/phases/PhasePB-1e報告.md`。併入：(e3p) 美術 FL-1j 待決 2 裁定 `docs/art/FL-1b驗收.md` 末節；(e3q) PB-1e 待決 4 的 portal 說明卡冒泡全面檢查。
> 基準：本機 main `b02b0aae9`（開工時 fast-forward 到這裡）。只改 `client/`、對應測試、本報告、上手筆記與截圖；沒有碰 Python、設計文件、計畫檔。

## 1. commit

| commit | 內容 |
|---|---|
| `24bdb44b4` | 部位破壞不出「{部位} 破！」浮字（拿掉 PB-1e 的 `early` 提前段）；「破」字記號字 ≥ 12 px 的等比放大；南邊有人時朝南三角形 800 寬不縮 |
| `38bb825ea` | (e3p)「」括起來 ≤ 6 字的名字不斷行、不可拆詞加「回合」「點燃」 |
| `f025707e7` | (e3q) 閃現選項卡、浮動卡觸發元素、釘選單位停靠區不再被 portal 說明卡的點擊冒泡觸發 |
| （本報告） | 報告、上手筆記第 170～174 點與測試對照表、截圖 8 張 |

## 2. 逐條驗收

| # | 項目 | 做法 | 驗證 | 結果 |
|---|---|---|---|---|
| 1 | 必修 1：部位破壞不出浮字，本體傷害浮字照舊 | `feedback.ts` 的 `part_broken` 回 `[]`；`FloatItem.early`、`partBrokenWord`、`frameOps` 的提前段一起刪掉（死碼） | `pb1cPartBreak.test.ts`（浮字沒有「破」、有「−5」）、`pb1eParts.test.ts`（回饋只有一段、在重畫之後；原始碼沒有 `early`）；實機連拍 1600／800 只有「−9」 | ✓ |
| 2 | 必修 2：「破」字畫面上 ≥ 12 px，整個記號等比放大，倍率 max(1, 12／(14 × 地圖縮放)) | `bossPartArt.popScale`（用 `minMarkScale`，常數 `MIN_BREAK_POP_FONT_PX = 12`）；`pop()` 的半徑、外圈、字乘倍率，圓心位置照模型 px；縮放由 `ResultHost.boardScale()`（`VfxLayer` 給 `this.scale`）取得，倍率進貼圖快取鍵 | `pb1eArt.test.ts`（0.53 → ×1.617、14 × k × 0.53 = 12、1.31 → 1；接線掃描）；實機 800（地圖 52%）連拍「破」字清楚（截圖 2） | ✓ |
| 3 | 朝南三角形：1600 縮 0.6、800 不縮 | `facingArrowPoly(u, boardScale?)`：縮完含描邊的畫面寬 ≥ 6 px 才縮（1600 實機 103% → 6.6 px 縮；800 的 52% → 3.3 px 不縮）；三角形在部位小格的縮放重排裡重畫 | `pb1eArt.test.ts`（1.31、1.03 縮 0.6；0.53 不縮；節點跟著縮放重畫來回）；實機特寫截圖 4（800 南邊有人＝和沒人一樣大、1600 縮小） | ✓ |
| 4 | 可修：800 有 3 狀態＋蓄力時滑過三部位差異小 | **沒做**（不強制）。原因是 800 狀態列蓋在下腹（美術 PM 另記追蹤「800 頭目狀態列移到 HP 條旁」），只動亮起解決不了；見待 PM 決定 3 | — | 未做 |
| 5 | 實機 1600、800 各：破壞連拍、南邊有人 hudTop、氣旋（歸一） | 見第 4 節；做法上手第 174 點 | 截圖 1、2、3、5、6 | ✓（資料是改寫的，見第 4 節說明） |
| 6 | (e3p)「」名字 ≤ 6 字連同括號不斷行；「回合」「點燃」不可拆 | `noBreakRuns` 改成三種範圍（`quotedSpans`、`wordSpans`、`numberUnitSpans`）的聯集，重疊才併段；數字的單位不切進詞中間（維持 FL-1j「第 3 格」＋「轉型」兩段） | 新檔 `run/pb1fQuoteWrap.test.ts`（含夾具每句）；舊測試兩處依新規則改期望（「水」「被標記」變成一段、詞表 6 個）；376 實測斷行見下 | ✓ |
| 7 | (e3q) 其他把說明卡放在可點元素裡的地方 | 查出 3 處並照 PartMenu 同法修（第 3 節）；新檔 `ui/pb1fPortalBubble.test.ts` | 瀏覽器實測（第 5 節）：舊碼點說明卡會把選項從 2 換成 0，新碼不換 | ✓ |

**e3p 376 實測**（`flash-choice.html?set=reflash_major&mode=run`，逐字 `Range` 量行，「／」是換行）：
- pick=2 條件括號：「（目標帶有狀／態「被標記」／時才有）」「（本回合已施／放過帶／「雷電」標籤／的技能時才／有）」——「被標記」「雷電」整段換行、不再拆開。下固定區：「…燃燒少 1 回合，／多了額外傷害：1d4 火焰傷害（本回合已／施放過帶「雷電」標籤的技能時才有）。」
- pick=3（轉型卡）：「這招變成／陷阱：先布在地上，敵人踩上去時才發／動。轉型後照新種類重算強度，不跟原／本比。」——沒有「」名字與新詞，和改前相同（「才發／動」「原／本比」是一般詞，裁定不追）。

## 3. (e3q) 檢查結果

React 事件照元件樹冒泡；`FloatCard` portal 到 body，它的 `onClick` 不擋冒泡，所以「說明卡的元件祖先」上的點擊／按鍵處理都會被觸發。

**有問題、已修（同 PartMenu：DOM target 在元素裡面才算）**：
1. `screens/RunFlashPending.tsx` 選項卡 `<div role="radio" onClick onKeyDown>`（一輪閃現與大世界「成長與技能」共用）：卡裡的類別標籤 `Term`、前 → 後列的 `Term`／`TermText`／改名列 `Hint`。點說明卡（釘住）＝選了那張；焦點在說明卡上按 Enter／空白也會選、方向鍵會換選項。**會改變選擇**。
2. `ui/useFloatCard.tsx` 觸發元素的 `onClick`（技能卡 `SkillTile`、技能列不可用的小格 `MiniSlot`，`pinOn: "always"`）：技能卡裡的說明卡被點，冒泡到觸發元素切換釘住，外層技能卡跟著關掉。不觸發遊戲動作。
3. `ui/PinnedUnitDock.tsx` 觸控 `onPointerUp`：點單位卡裡的說明卡會展開／收起停靠區。不觸發遊戲動作。

**查過、沒問題**（說明卡是可點元素的兄弟，不是它的子孫；或已經擋了）：FlashChooser 類別標籤、StartPicker 武器／關鍵字、LoadoutEditor、OfferPicker（技能卡和「選」鈕是兄弟）、RaceOriginPicker、SkillBar 各格與普攻鈕、WishPanel、SolutionTile／離開鈕、ActionPanel、SummonPanel（`PartTip pin={false}`）、TurnControls、BattleLog／BattleLogDock、FlashSection、WorldGrowth 的閃現鈕、NpcPanel、WorldHud 的 Chip／IconButton／設定；沒有任何 `<button>` 裡面包說明卡元件。ReactionPanel、`gear/SlotGrid`、BagScreen、EventCard、LootChoicePanel、Smithy／Party／Mail／Economy 面板、PanelTabs 的可點元素裡沒有說明卡。已擋：`RangeClassPick`（按鍵比 `target === currentTarget`）、`BattleCanvas` 格子點擊（`HoverFloat` 自己擋冒泡）、UnitInfo／SkillCardView 的圖釘鈕、PartMenu。背景點擊關閉：AtlasMap、RegionMap 內層 `stopPropagation`；WorldHud 背景與面板是兄弟；DialogFrame／PopupFrame／PanelKit 沒有背景點擊。`BattleScreen` 沒有 React 點擊處理。document 層的「點外面關」（`usePopupMenu`、`useTileCard`、`useFloatCard`）都已略過 `.float-card`。`<details>` 的原生展開只看 DOM，不受影響。

## 4. 截圖（`docs/art/shots/PB-1f/`，8 張；DPR 1、無頭 Chrome `--mute-audio`、網址 `?mute=1`）

| 檔案 | 內容 |
|---|---|
| `docs/art/shots/PB-1f/1-break-1600.jpg` | 實機 1600（地圖 103%）×3 最近鄰：長劍破壞連拍 8 格（命中前→白閃→裂開→飛出＋「破」→落地「破」淡出＋打叉→定格）；只有「−9」沒有「長劍 破！」 |
| `docs/art/shots/PB-1f/2-break-800.jpg` | 實機 800（地圖 52%）×4：同上；「破」記號放大 ×1.62 |
| `docs/art/shots/PB-1f/3-hudtop-1600-800.jpg` | 實機 1600 ×4、800 ×8：南邊站人、頭目朝南，HP 條＋部位條蓋在那人頭上；腹前氣旋 |
| `docs/art/shots/PB-1f/4-arrow-closeup.png` | 實機特寫（PNG 最近鄰）：朝南三角形 800 南邊有人／沒人一樣大（不縮），1600 南邊有人縮 0.6／沒人原大 |
| `docs/art/shots/PB-1f/5-qi-1600-800.jpg` | 實機 1600 ×4、800 ×8：歸一（三部位露出）腹前氣旋，朝南與朝東 |
| `docs/art/shots/PB-1f/6-scene-800-hudtop.jpg` | 實機 800 整個畫面（hudTop 那一場的版面） |
| `docs/art/shots/PB-1f/7-flash-376-pick2.jpg` | 開發頁 `flash-choice.html?set=reflash_major&mode=run&pick=2`，376 寬：「被標記」「雷電」不拆 |
| `docs/art/shots/PB-1f/8-flash-376-pick3.jpg` | 同上 `pick=3`（轉型卡） |

**實機資料的說明（重要）**：都是真的 `trpg serve`（`TRPG_DEV_ROUTES=1`、存檔在暫存區）＋正式 build 的前端＋真的戰鬥 API 回應，但用 CDP `Fetch` **改寫**過（上手第 174 點）：
- 開局：雲頂觀種子 1、`build_ranged`、工坊試玩（`skill_piercing_shot` 換 id），主角走一步的那一刻；改寫成頭目「歸一」的樣子（三個部位都露出、HP 28%），**拿掉護體泡泡**（會蓋住身體）；hudTop 那張另把隊友搬到頭目南邊、頭目改朝南。伺服器那一場實際還在劍陣。
- 破壞：主角真的對頭目放「遠距狙擊」（瞄拂塵），但這個種子開局 d20 一直是 3、打不中，所以回應裡把命中改成成功、補 `damage_dealt`＋`part_damaged`＋`part_broken`（長劍），之後的畫面長劍已破。
- 沒做：氣海的實機破壞（只拍長劍）；800 的選單滑過亮起（PB-1e 已拍）。

## 5. 瀏覽器實測（6.5.1）

閃現選擇開發頁（`reflash_major`、pick=2，選中第 3 張），在**沒選中的第 1 張**選項卡裡滑過術語「冷卻」：

| 檢查 | 1600×900 | 800×600 |
|---|---|---|
| 滑過 → 說明卡出現；經橋接區滑進卡片仍開著 | ✓ | ✓ |
| 卡內滾輪（內容一行，scrollHeight＝clientHeight 46）後仍開著 | ✓ | ✓ |
| 點卡片 → 釘住；**選中的仍是第 3 張** | ✓（舊碼：變成第 1 張，已用 `git show` 換回舊檔重現） | ✓ |
| Esc 關閉 | ✓ | ✓ |

## 6. 結束碼（交件前）

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（359 檔、4537 項） |
| `corepack pnpm -C client build` | 0 |

Python 沒改，沒跑 ruff／mypy／pytest／`scripts/check.py`、沒跑模擬、沒 push。自己開的 `trpg serve`（8823）、vite（8824）、無頭 Chrome（9373）都用 PID 關掉，三個埠沒有監聽。

## 7. 舊測試的改動

- `battle/pb1cPartBreak.test.ts`：「浮動字『拂塵 破！』」改成「不跳浮字、傷害數字照舊」。
- `battle/pb1eParts.test.ts`：「破字提前到命中」那組改成「回饋只有一段、在重畫之後；沒有 `early`」。
- `run/fl1hFlashWords.test.ts`：「（目標站在「水」表面上時才有）」原本整段不包，現在「「水」」一段（裁定的新規則）。
- `run/fl1jFlashWrap.test.ts`：詞表 4 → 6 個；「1d4 火焰傷害（…「被標記」…）」多一段「「被標記」」。

## 待 PM 決定

1. **800 寬「破」字和「−N」傷害浮字上下貼著**（截圖 2 第 4～7 格：浮字下緣碰到放大後的「破」外圈上緣，沒有互蓋字）。1600 有空隙。要不要再錯開請美術看。
2. **朝南三角形「不縮」的門檻**用「縮完含描邊畫面寬 ≥ 6 px」（照美術驗收可修 1 的建議），換算地圖縮放約 0.94；1600 寬但地圖很大、縮放 < 0.94 時也不縮。另外 800 不縮的三角形本身也只有約 3～5 px（截圖 4），本來就難看清。
3. 可修「800 有 3 狀態＋蓄力時滑過三部位差異小」沒做：根源是 800 狀態列蓋下腹，建議併美術 PM 已記的追蹤（800 頭目狀態列移到 HP 條旁）一起做。
4. 實機截圖的歸一外觀、命中、長劍破壞是改寫 API 回應做出來的（第 4 節說明）；渲染與播放接線（`partId`、`partHudUp`、`boardScale`）是真的。若要「伺服器真的打到歸一」需要另寫代打腳本（世界 Boss 的 `dev-boss ai_until` 是大世界角色才有）。
5. e3q 的修法是逐處加判斷；`FloatCard` 本身的 `onClick` 仍不擋冒泡（擋了可能影響外層卡片的釘住與 window 層監聽）。之後新寫「整塊可點、裡面有說明卡」的元件要照上手第 173 點自己判斷。
6. e3p 的聯集規則讓「強度 +1」這類詞後接數字時只保「強度」（數字前面不從詞的最後一字黏起），和 FL-1j 相同；「」名字裡有數字時整段併成一段（例「「第 3 式」」）。
