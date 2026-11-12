# Phase OB-8 報告（#154 前端：隊友加入台詞與隊伍面板來歷）

> 實作者：OB-8 實作 agent（Opus 5.5）。
> 依據：09 9.6「預設隊友的出場」、18 18.7.1 第 1 步、決定 #154（使用者：「照建議」）；接口照 `docs/phases/PhaseOB-7報告.md` 第 4 節。
> 阿岳的部分：派工中途一度暫緩（玩法 PM 請使用者重新決定入隊時機），之後開發 PM 轉達使用者原話「剛開始 2打1 後面才加人」＝照 #154 渡口打完才加入，**恢復照做**。渡口改 1 隻敵人由另一段後端處理，這段沒動。
> 後端沒有改（接口夠用）；沒改數值與規則。

## 1. 交付與 commit

| commit | 內容 |
|---|---|
| 182de195 | 對話框 `PartyIntroDialog`、`WorldScreen` 接線、隊伍面板來歷行、型別別名 `WorldPartyIntro`、vitest `partyIntro.test.ts` |
| 72bf2c14 | 建角畫面的說明句改成只帶賽倫（見待決 1）；截圖 `docs/art/shots/ob8/` |
| （本報告） | 報告與上手筆記 |

## 2. 逐條

| 要做 | 做法 |
|---|---|
| 1 賽倫：確定出發後、傳送前用對話框出場，播完送 `hint_seen` | `WorldScreen` 的 `partyIntro`＝`view.party_intro`，在守印人那段話（`RangeDoneDialog`，按「出發」）關掉之後才出現；標題「{名字}加入隊伍」，台詞照伺服器順序「說話的人：台詞」，只有一個「好」。按「好」走既有的 `markSeen([seen_id])`（本機先記，送 `hint_seen {ids: ["intro:merc_tiebi"]}`）。之後玩家才去傳送陣／M 選霧渡鎮。 |
| 2 阿岳：渡口打完說一兩句 | 同一個對話框（通用，不分播誰）：回到地圖的那個回應帶 `party_intro`（`intro:companion_ayue`）就播。播著時升級畫面與教學先等，所以順序是「阿岳台詞 → 升到 2 級 → 配點教學」。 |
| 3 隊伍面板來歷 | `PartyPanel` 名字那一列下面一行 `.world-party-backstory`（`muted`），`backstory_zh` 是 null、沒給或空字串都不畫。隊伍面板在「影子（Y）」面板最上面、城鎮雇用面板也有。 |
| 4 共用元件、6.5.1 | 對話框用 `DialogFrame`（和開場、靶場那段話、教學同一個外框與 `.world-opening-line` 樣式）；沒有新的彈出層、沒有 `title=`（`floatCardRule.test.ts` 通過）。文字全部來自伺服器，`PartyIntroDialog.tsx` 去掉註解後不含任何成員名字或 ID（vitest 掃）。 |
| 5 vitest | `client/src/world/partyIntro.test.ts` 7 項：有 `party_intro` 才彈、沒有／沒台詞／已看過不彈；對話框照順序寫出台詞、標題、只有一個按鈕、用 `DialogFrame`；按「好」呼叫 `onClose`，`WorldScreen` 的 `onClose` 是 `markSeen([partyIntro.seen_id])` 而 `markSeen` 送 `hintSeenAction`；靶場那段話關掉後才播、升級與教學等它；來歷行有、無（null、沒給、空字串）。 |
| 6 實機 | 見第 3 節。 |

接線的條件（`WorldScreen`）：`rangeDone === null && !shouldShowAbsence(absence) && !shouldShowOpening(view.guide, seenIds) && partyIntroShown(view.party_intro, seenIds)`；升級畫面、配點教學、閃現教學三個條件各多 `partyIntro === null`。之後若改入隊時機，只要後端改觸發點。

## 3. 實機走一遍（自己的 `trpg serve --port 8743`，存檔在 scratchpad，無頭 Chrome `--mute-audio`＋`?dev=1&mute=1`，CDP 操作）

1. 建角（精靈、雲嶺）→ 醒來「站起來」→ 靶場選近戰 →「確定出發」→ 守印人那段話（按「出發」）→ **「賽倫加入隊伍」**：守印人一句、賽倫一句（和 09 9.6 原文一致）→ 按「好」。伺服器 `hints.seen` 多了 `intro:merc_tiebi`、`party_intro` 變 null。
2. 開「影子（Y）」面板：賽倫下面一行「守印人派來的護衛。正式選定後可以在城鎮換人。」
3. 傳送到霧渡鎮、接新手任務、走到渡口石階碰盜賊（這三步與戰鬥是用 API 腳本代走，和前端送的是同一組世界動作與 `/api/battles` 動作；3 輪贏）→ 重新整理頁面 → **「阿岳加入隊伍」**：阿岳那一句（和 18.7.1 原文一致）→ 按「好」→ 接著出「升到 2 級」→ 「知道了」。`hints.seen` 多了 `intro:companion_ayue`。
4. 隊伍面板：賽倫、阿岳各一行來歷（阿岳「在渡口一起打退盜賊後同行。任務結束後離隊。」）。

浮動卡實測（6.5.1；這段沒有新增浮動卡，抽查底部功能列「背包」鈕的說明卡）：1600×900 與 800×600 都是「滑過出現 → 滑進卡片不關 → 捲到底（卡片內容 114px，不需捲動，捲完仍開著）→ 點一下釘住（`pinned`）→ 滑鼠離開仍在 → Esc 關閉」。

截圖（6 張，jpg 80，最大 191 KB）：
- `docs/art/shots/ob8/ob8_saren_intro_1600.jpg`、`docs/art/shots/ob8/ob8_saren_intro_800.jpg`：主城，賽倫加入的對話框
- `docs/art/shots/ob8/ob8_ayue_intro_1600.jpg`、`docs/art/shots/ob8/ob8_ayue_intro_800.jpg`：渡口石階打完，阿岳加入的對話框（左上隊友已有阿岳）
- `docs/art/shots/ob8/ob8_party_saren_1600.jpg`：隊伍面板，賽倫的來歷
- `docs/art/shots/ob8/ob8_party_ayue_800.jpg`：隊伍面板，賽倫與阿岳的來歷

伺服器與無頭 Chrome 已用自己記下的 PID 關閉，8743、9333 沒有在聽。

## 4. 改到的既有測試

沒有。既有測試一項都沒改（新增 `client/src/world/partyIntro.test.ts`）。

## 5. 檢查結束碼

| 項目 | 結果 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（315 檔、4056 項） |
| `corepack pnpm -C client build` | 0 |

後端沒動，沒跑 ruff／mypy／pytest；沒跑 `scripts/check.py`、沒跑模擬、沒 push。

## 6. 待 PM 決定

1. 建角畫面的說明句原本寫死「一開始帶系統傭兵賽倫、回春」（#154 之後不對了），改成「隊友：守印人派系統傭兵賽倫同行；正式選定武器之後，可以在城鎮免費改成別的傭兵、借朋友的影子（最多 2 名）或獨行。」——暫定字，可改；這句仍是前端寫死（原本就是），沒有改成讀伺服器。
2. 對話框標題「{名字}加入隊伍」、按鈕「好」是前端自訂的字（台詞本身全部來自伺服器）；要換字只改 `PartyIntroDialog.tsx`。
3. 播放順序：隊友台詞排在升級畫面與教學前面（渡口打完＝阿岳 → 升 2 級 → 配點）。設計只寫「打完後說一句再入隊」，這是最保守的解讀；若要反過來改 `WorldScreen` 三個條件即可。
4. 「重新顯示提示」（`hints_reset`）清掉後兩段台詞會在條件成立時再播一次（OB-7 後端既有行為，沒改）。
