# Phase PNL-4b 報告：PNL-4 美術驗收的必修 1＋可修 1

> 依據：`docs/art/PNL-4驗收.md`「必修 1」「可修 1」。分支 `worktree-agent-aad0858656ec7373c`（開工時 ff 到 main `1c1d0827`）。沒有 push。
> 只改事件卡選項格相關檔：`client/src/world/solutionGrid.ts`、`client/src/world/story.css`、`client/src/world/pnl4EventTiles.test.ts`；沒動引擎與技能內容。

## 1. 做了什麼

| 項目 | 改法 |
|---|---|
| **必修 1：「用〔…〕抵」小鈕壓到圖示、貼左框** | 走美術建議的第二條（小鈕不出字欄、左緣不越過字欄）。小鈕 `max-width: calc(100% - var(--sol-waive-inset) - 7px)`，`--sol-waive-inset: 36px`＝左內距 5＋框 1＋圖示 24＋間距 6；`margin: 0 7px 7px 0`（右緣、下緣對齊字欄＝內距 6＋框 1，原本 `0 8px 6px 0`）。小鈕與看不見的同字都改 `white-space: normal`（原 `nowrap`）、同字 `max-width: 100%`：兩者可用寬度一樣，放不下就在鈕裡換成兩行，同字讓出的高度也是兩行，實量兩者位置與大小完全重合。寬的格子（1600、262）照舊一行、靠右。圖示維持垂直置中（小鈕不會再進圖示那一欄）。 |
| **可修 1：收尾標點黏整個詞** | 兩處：①`wordBreaks`：Chrome（node 也一樣）把「亮出商隊」切成四個單字，舊規則「單字併進下一個詞」湊出「亮出商隊旗號，」一整段（比 137 格的一行長，被任意斷成「旗／號，」）。現在連續單字湊到兩字以上就自成一詞，結果「亮出商隊｜旗號，｜談條件」；只有一個單字（「談」）才併進下一個詞。②`glueTail`：收尾標點連同整個詞包成 `.world-sol-glue`（不算標點 ≤ `GLUE_WORD_MAX`＝5 字；800×600 最窄字欄 94 約放 6 字粗體，5 字＋標點一定放得下）；比這長的詞照舊只黏最後一字，詞比一行長時才讓 `overflow-wrap: anywhere` 任意斷。 |
| 上手筆記 | 第 114、115 點補註；新增第 126、127 點；第五節 PNL-4 那列加註。 |

## 2. 驗收截圖（開發頁）

開發頁 `/dev/story-gallery.html?mute=1&mode=event`（`vite --port 5318`），用 JS 把 `.world-sol-grid` 設成 `2×格寬＋6`，量「雇船夫繞路／交涉 −2 補給／用〔商人欠你人情〕抵」那一格。無頭 Chrome `--mute-audio`、CDP 9341、DPR 1；`Page.captureScreenshot` 取格子外加 6px，頁內 canvas 最近鄰 ×3 存 PNG。

| 檔（`docs/art/shots/pnl4b/`） | 格寬 | 格高 | 小鈕 | 離圖示 | 離左框 | 離右框 | 離下框 | 大小 |
|---|---|---|---|---|---|---|---|---|
| `pnl4b-waive-137-x3.png` | 137 | 85.1 | 94×35（兩行） | 6 | 35 | 6 | 6 | 17 KB |
| `pnl4b-waive-145-x3.png` | 145 | 85.1 | 102×35（兩行） | 6 | 35 | 6 | 6 | 17 KB |
| `pnl4b-waive-262-x3.png` | 262 | 52.1 | 129×19.5（一行） | 96 | 125 | 6 | 6 | 17 KB |

要求「離圖示 ≥ 2、離邊框 ≥ 4」都達到。「離圖示」是兩個矩形的最短距離（小鈕在圖示右邊，水平隔 6）。

可修 1 的斷行用 `Range` 逐字量（不截圖）：字欄 84～92 寬時「亮出商隊／旗號，談條件」，96～132 時「亮出商隊旗號，／談條件」，40 寬才會斷到「旗號，」之外的地方；沒有一個寬度會出現「旗／號」。

## 3. 測試

`client/src/world/pnl4EventTiles.test.ts`：

| 舊 | 新 |
|---|---|
| 「最後一個字＋收尾標點包成一段」：`glueTail("亮出商隊旗號，")`＝`{head:"亮出商隊旗", tail:"號，"}`、`glueTail("黑曜片）")`＝`{head:"黑曜", tail:"片）"}`、輸出含 `<span class="world-sol-glue">[^<]，</span><wbr/>` | 「收尾標點黏住整個詞」：`GLUE_WORD_MAX`＝5；`glueTail("旗號，")`＝`{head:"", tail:"旗號，"}`、`"黑曜片）"`、`"賭一把，"` 整個黏；`"亮出商隊旗號，"`（6 字，超過上限）仍只黏「號，」；`"談條件"`、`"，"` 不變；`.world-sol-glue` 仍是 nowrap |

新增：
- 「連續單字湊到兩字以上自成一詞」：用 Chrome 實際的切法（假 segmenter）與 node 的 `Intl.Segmenter` 都得到 `["亮出商隊", "旗號，", "談條件"]`；`衝過去撞開路障`→`["衝過去", "撞開", "路障"]`；輸出含 `亮出商隊<wbr/><span class="world-sol-glue">旗號，</span><wbr/>談條件`。
- 「『用〔…〕抵』不伸出字欄」（結構斷言）：從 `story.css` 讀 `.world-sol` 的內距與間距，算回 `--sol-waive-inset`（＝左內距＋框＋`TILE_ICON`＋間距＝36px）、小鈕 `max-width` 與 `margin`；小鈕與同字 `white-space: normal`、同字 `max-width: 100%` 與 `visibility: hidden`；間距 ≥ 2、右下內距 ≥ 4。舊的 CSS 這項會失敗。

其他既有測試沒改。沒有重產雜湊或快照。

## 4. 檢查結束碼

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm vitest run src/world/pnl4EventTiles.test.ts src/world/pnl4Followups.test.ts src/world/story.test.ts` | 0（50 項） |
| `corepack pnpm -C client test --run` | 0（330 檔、4287 項全過） |
| `corepack pnpm -C client build` | 0（只有既有的 chunk 大小警告） |

## 5. 待 PM 決定

1. 窄格子時小鈕在鈕裡換兩行（「用〔商人欠你／人情〕抵」，`overflow-wrap: anywhere` 照字寬斷，可能斷在名字中間）。沒有改用「…」截斷，因為截了玩家就看不到是哪條線頭（說明卡寫的是通用說明）。若美術想要別的斷法（例如在「〔」前斷），下一段再調。
2. 截圖用開發頁量，不是實機；格子結構與實機相同（同一個 `SolutionGrid`）。

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（無衝突）。合併後前端 typecheck 0、vitest 4287 passed、build 0。三張特寫間距達標（離圖示 ≥ 6、離框 ≥ 6），交美術 PM 複驗。待決（窄格小鈕在線頭名中間換行、不截斷）：交美術 PM 判斷。
