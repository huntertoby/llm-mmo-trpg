# Phase LW-2b 報告：前端小修三件（LW-2 必修 1、LW-2 可修 3、PNL-4 複驗新可修）

> 依據：`LW-2驗收.md`（美術分支 `8347e471`）必修 1、可修 3（＝開發 PM 要美術判斷的第 4 件）；`PNL-4驗收.md`（`503e13be`）末節「複驗 PNL-4b」的新可修；共用規則 `資訊面板-移植需求.md` 3.7 第 2、3 條（`e9e68e1a`）。
> 分支 `worktree-agent-ac47bb687b470cc17`（開工時 ff 到 main `769a0fdc`）。沒有 push。只動前端：隊伍面板、說明卡上方那一行、事件卡選項格的斷詞；沒動引擎、技能內容、數值工坊，也沒改 Python。

## 1. 做了什麼

| 項目 | 改法 |
|---|---|
| **LW-2 必修 1：800×600 帶隊友時獨狼警告被切** | `world/PartyShadowPanel.tsx`：`LoneWolfCallout` 多一個 `tone` 篩選（`"warn"`／`"info"`，不給＝照舊）。`PartyPane` 在 `TabLine`「主角＋最多 2 名」下面放 `tone="warn"`、成員卡後面放 `tone="info"`：帶隊友的琥珀警告在頁首；獨行的青色資訊照舊在成員卡後面、「獨行」之前（驗收寫「資訊與鎖住留在成員卡下面，不用動」）。字、顏色都沒改。 |
| **LW-2 可修 3：「現在不能用：…」加底色** | `ui/ConditionOffNote.tsx` 新增 `NowOffNote`（`<div class="skill-card-reason now-off-note"><b>現在不能用</b>：原因</div>`）。技能鈕（`SkillBar` 的技能槽與種族技）、`SkillTile` 三處原本手寫的那行都改用它。`styles/skill-bar.css`：`.cond-off-note, .now-off-note` 共用深藍底（`--ui-navy`、內距 5/9、圓角 6、陰影、12px），`.now-off-note` 框改 `1px solid #e8b45a`、`> b` 琥珀 700。順序照舊「現在不能用」在上、「本場不成立」在下。 |
| **PNL-4 新可修：「用〔…〕抵」斷在詞中間** | `world/solutionGrid.ts` 新增 `WAIVE_GLUE_CHARS`＝2 與 `waiveRuns(label)`：前段＋尾巴（線頭名字最後兩個字＋「〕抵」；名字不到兩個字就整個名字；字不是「用〔…〕抵」的樣子就整句當前段）。`world/SolutionTile.tsx` 的 `WaiveText` 把尾巴包既有的 `.world-sol-glue`（nowrap）；小鈕和看不見的同字都畫 `WaiveText`，兩者換行仍一致。 |
| 上手筆記 | `docs/dev/上手-前端戰鬥畫面與動畫.md` 第四節新增第 128～132 點；第五節 LW-2 那列補上新測試檔。 |

## 2. 驗收截圖（`docs/art/shots/lw2b/`，5 張，最大 70 KB）

無頭 Chrome（`--mute-audio`、除錯埠 9262、DPR 1、800×600）、`trpg serve --port 8762`（正式 build，存檔在暫存區）、vite 5262（開發頁）；網址都帶 `?mute=1`。拍完已關掉三個程序，埠都沒在聽。

| 檔 | 內容 | 量到的 |
|---|---|---|
| `lw2b_party_off_800.jpg` | **實機版面＋注入資料**：首頁「繼續」進入（開發角色，隊伍本來是主角＋賽倫），包 `window.fetch` 在世界回應的 `party` 追加阿岳（劇情夥伴）、補 `lone_wolf`（`ok:false`，孤狼撲擊、獨行者、皮甲的「獨行的」）。按 Y 打開隊伍頁、不捲。 | 捲動區 148～518、`scrollTop` 0；警告 260～311（兩行都在）；成員卡從 317 起 |
| `lw2b_nowoff_800.jpg` | **實機戰鬥＋注入**：`?dev=1` 首頁「一鍵開局」（烈焰包），包 fetch 把 `/api/battles` 回應主角第二招設冷卻 2，滑到「點名」上。 | 計算後的樣式：框 `solid rgb(232,180,90)`、底 `rgb(30,34,54)`、粗體字 `rgb(232,180,90)`／700 |
| `lw2b_nowoff_800_card.png` | 上一張的說明卡特寫（最近鄰 ×2） | 同上 |
| `lw2b-waive-145-x3.png` | 開發頁 `/dev/story-gallery.html?mode=event`，把 `.world-sol-grid` 設成 `2×145＋6`，「雇船夫繞路」那格特寫（最近鄰 ×3） | 小鈕逐字量行：「用〔商人欠你」／「人情〕抵」 |
| `lw2b-waive-137-x3.png` | 同上，137 寬 | 「用〔商人欠你」／「人情〕抵」 |

隊伍頁沒有角色能真的學會並裝上獨狼技能出城（同 LW-2），所以獨狼資料是注入的。「本場不成立」和「現在不能用」同一張卡兩條都有的樣子沒有實機拍（要另外注入獨狼技能），順序由測試保證。

## 3. 測試

新增：
- `client/src/world/lw2LoneWolf.test.ts` 加兩項：帶隊友時「主角＋最多 2 名」→ 警告 → 成員卡的順序，警告只出現一次；獨行時成員卡 → 青色資訊 →「獨行」。
- `client/src/battle/lw2bNowOff.test.ts`（新檔）：`NowOffNote` 的輸出；三處都用 `NowOffNote`、沒有手寫的「現在不能用：{」、技能鈕裡排在 `ConditionOffNote` 前面；CSS 共用深藍底、內距、圓角，框琥珀實線、`> b` 琥珀 700。
- `client/src/world/lw2bWaiveGlue.test.ts`（新檔）：`waiveRuns` 一般、短名字、空名字、格式不符、前段＋尾巴＝原字（含擴充區漢字）；`SolutionTile` 兩處都畫 `WaiveText`、尾巴用 `.world-sol-glue`，CSS 仍是 nowrap。

既有測試改動（舊 → 新）：

| 檔 | 舊 | 新 | 理由 |
|---|---|---|---|
| `client/src/world/pnl4EventTiles.test.ts`「『用〔…〕抵』：同一格裡的小鈕…」 | 同字 `…aria-hidden="true">用〔商人欠你人情〕抵</span>` | `…aria-hidden="true">用〔商人欠你<span class="world-sol-glue">人情〕抵</span></span>` | 尾巴多包一層不斷行 |
| 同上 | 小鈕 `/…data-testid="world-solution-waive">用〔商人欠你人情〕抵/` | `/…data-testid="world-solution-waive">用〔商人欠你<span class="world-sol-glue">人情〕抵<\/span><\/button>/` | 同上（斷言反而變嚴：要對到 `</button>`） |

沒有放寬任何斷言；沒有重產雜湊或快照。

結束碼：`corepack pnpm -C client typecheck` 0；相關 vitest（`lw2LoneWolf`、`lw2bNowOff`、`lw2ConditionOff`、`src/ui` 全部、`lw2bWaiveGlue`、`pnl4EventTiles`、`story`）0；交件前 `corepack pnpm -C client test --run` 0（332 檔、4297 項）；`corepack pnpm -C client build` 0。沒改 Python，沒跑 ruff／mypy／pytest；依指示沒跑 `scripts/check.py`。

## 4. 待 PM 決定

1. **`SkillTile`（城鎮等處的技能小卡）也一起換成新樣式**：它和戰鬥技能鈕用同一行「現在不能用：…」、外層一樣是透明浮動卡，所以一起改成 `NowOffNote`（最保守地維持「同一句同一個樣子」）。種族技的卡（`float-panel race-card`，本身有底）裡那行也有了深藍底與琥珀框，看起來是卡中一個小框。若美術只要戰鬥技能鈕那一處，改回很簡單。
2. **線頭名字只有一個字時**，尾巴＝整個名字＋「〕抵」（例「用〔／債〕抵」）。目前沒有這種線頭，照保守做法處理。
3. 琥珀直接寫 `#e8b45a`（`--pnl-warn` 只定義在面板範圍內，戰鬥畫面拿不到）。若要做成全域變數，改 `theme.css` 是另一件事，這次沒做。

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（無衝突）。合併後前端 typecheck 0、vitest 4297 passed、build 0。

1. SkillTile 與種族技卡一起換新樣式：接受，交美術 PM 確認。
2. 單字線頭名：接受（目前無此情況）。
3. 琥珀色直接寫色碼：接受；之後若戰鬥 UI 需要全域變數再收。
4. 兩行同卡無實機截圖：接受，由測試保證順序。
