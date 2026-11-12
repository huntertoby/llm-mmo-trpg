# Phase 6H-1b 報告：停頓時間點跟著技能時間軸（`retime` 連 `impacts` 一起換算）＋開發頁 `#impact`

實作者，2026-11-04。

規格依據：
- 開發 PM 派工的 6H-1b 六點；
- `docs/archive/art/RT-2與RT-4與6H-1與AU-3檢查.md` 的 6H-1 段（「停頓沒有跟著技能時間軸移動（例：停在 270 ms、命中在 396 ms）」）；
- `docs/archive/phases/PhaseAU-3報告.md` 順手發現第 1 點。

開工時 worktree 先 `git merge --ff-only 501d4161`（main）。

改動範圍：
- 只改 `client/`，另外加了截圖和這份報告；
- 沒有改 Python、內容資料、數值、規則或 API；沒有新增相依；沒有用原生 `title=`；
- 不用 `Math.random`，不讀時鐘。

## 問題

`skillSequence.retime` 把特效對齊出招的命中點時，會移動 `casts`、`hits`、`blasts`、`reactions`，但沒有移動 6H-1 新增的 `impacts`（扣血與爆炸）。
`withImpact` 在 `skillTimeline` 之後用 `impacts.atMs` 推停頓分級與微震，所以停頓、微震落在「還沒對齊的命中點」：

- 近身劍：原本 `vfxFor` 的命中在 270 ms，起手播完後畫面命中在 396 ms，停頓卻停在 270；
- 蓄力遠射被等比壓縮時也一樣（原本 520 ms，畫面命中 1446 ms）。

AU-3 的聲音照 `cueRealMs(atMs, vfx)` 排：停頓在 270、命中聲在 396，所以命中聲的「實際 ms」多了 100 ms 的停頓，比效果時鐘晚；報告說的「實際 ms 比效果時鐘晚」就是這件事。

## 做了什麼

### 1. `retime` 連 `impacts` 一起換算（`client/src/battle/skillSequence.ts`）

- 抽出 `shiftAt(atMs)`：和哪一段的 `impactMs` 同一刻就用那一段的位移；都不是（放在最後的、別人打的）用最後一段的位移。`hits` 原本就是這個規則，現在 `impacts` 用同一個函式。
- `impacts` 其他欄位（比例、暴擊、seq、位置）不動；沒有 `impacts` 時不加這個鍵。
- 停頓的起點、微震、最後一擊放慢都是 `withImpact` 從 `impacts`／`reactions` 推的，所以修 `retime` 之後全部跟著命中點走；`withImpact`、`impact.ts`、`hitStop.ts`、繪製器都沒改。

### 2. 聲音與畫面對齊（AU-3，沒改程式）

- `cueRealMs` 的規則是「比 `atMs` 早的停頓加進實際時間」；停頓現在和命中同一刻，命中聲不再被自己的停頓往後推：`cueRealMs(hitAt) = hitAt`（沒有放慢時）。
- 用 `advanceClock` 每 1 ms 走效果時鐘模擬繪製器，命中聲的實際時間和繪製器走到命中那一刻的差 ≤ 2 ms（實際是 0～1 ms），寫進測試。

### 3. 開發頁 `skill-gallery.html#impact`（`client/src/dev/skillGallery.ts`）

- 三招並排，走正式的 `playbackPlan`（vfxFor → skillTimeline → withSpecials → withImpact，含音效）：
  1. 劍・近身重擊（扣 60%：停 100 ms、微震 2 px）；
  2. 法杖・蓄力遠射 9 格（`timing: delayed`，超過 1.8 秒，起手被壓縮；扣 30%：停 70 ms）；
  3. 劍・輕擊（扣 5%：不停頓、不震）。
- 每招下方一條時間軸（橫軸是實際 ms）＋表格：起手開始、出招開始、放出（遠程的 hitAt）、命中（受擊反應）、**修正前的停頓起點（6H-1，虛線）**、停頓起點與長度、微震、每個音效點；每列同時列效果時鐘 ms 與實際 ms（`cueRealMs`），備註寫「和命中差 N ms」。
- `window.__impactRows` 放同一份資料（自動化檢查用）；`?freeze=`、`?mute=1` 照舊。
- 6H-1 待決 6（需求第 5 節的 `#impact`）這次補上；沒有並排四級、三種震、最後一擊的專頁，見待決 2。

## 檔案

| 檔案 | 內容 |
|---|---|
| `client/src/battle/skillSequence.ts` | `retime`：`shiftAt`，`impacts` 跟著移 |
| `client/src/battle/impact6h1b.test.ts`（新，9 項） | 壓縮前後、兩段、停頓與微震的時間、聲音與畫面對齊 |
| `client/src/dev/skillGallery.ts` | `#impact`：`IMPACT_CASES`、`timelineRows`、`timelineBox`、`impactTimeline` |
| `docs/art/6h1b_impact_timeline.jpg`、`docs/art/6h1b_impact_heavy_far.jpg` | 截圖 |

## 測試

- 新增 9 項（`impact6h1b.test.ts`）：
  - **壓縮**：蓄力遠射 9 格，`impactMs ≤ 1800`、時間軸真的移動了；每個 `impact.atMs` ＝ 同一個受擊者的反應時間 ＝ `hits.atMs` ＝ `casts[0].impactMs`；
  - **不壓縮**：近身劍的 `impacts` 和 `hits` 一起照起手的位移移，其他欄位不變；串接器同輸入同輸出、不改原本的描述；
  - **兩段（followup）**：各自跟自己那一段的命中點，別人打的跟最後一段；
  - **停頓、微震**：壓縮與不壓縮兩招，`stops[0].atMs`、`shakes[0].atMs`、`leadMs` 都等於 `hits[0].atMs`；
  - **聲音與畫面**：三招走 `playbackPlan`，命中聲 `atMs` ＝ 受擊反應 ＝ 扣血 ＝ 停頓起點；`cueRealMs` 和 `advanceClock` 模擬走到命中的實際時間差 ≤ 2 ms；
  - **原本的 bug**：壓縮那招的停頓起點不等於 `vfxFor` 的命中時間、等於畫面的命中。
- 把 `retime` 換回修正前的版本跑這個檔案：**9 項裡 8 項失敗**（確認測試抓得到）。
- 既有的 `impact6h1.test.ts`（22）、`skillSequence.test.ts`、`au3.test.ts` 全過。
- 交件前跑過一次 client 全部 vitest：**227 個檔案、2,481 項全部通過**（6H-1 交件時是 218 個檔案、2,378 項）。
- `tsc --noEmit` 通過；`corepack pnpm -C client build` 成功（只有原本就有的 chunk 大小提示）。

## 截圖（`docs/art/`）

- 環境：自己的 vite 5327（埠 5322 已被別人用）、自己的無頭 Chrome（`--mute-audio`、`--use-angle=swiftshader`、自己的設定檔），網址 `skill-gallery.html?mute=1&freeze=560#impact`。
- 收尾：vite 已用 PID 結束（先確認命令列是 vite 才結束），5327 已關；沒碰 tmp_x、saves/、8000、8001、8010、8366、8399，也沒碰內建瀏覽器的分頁。
- 暫存腳本放 `scratchpad/h1b/`（`shot.mjs`、`stop.mjs`，session 的 scratchpad，不在 repo）。

| 檔案 | 內容 |
|---|---|
| `6h1b_impact_timeline.jpg` | **`#impact` 全頁**：上方三招的畫面（停格在 560 ms，重擊那招正在閃白），下方三條時間軸與表格 |
| `6h1b_impact_heavy_far.jpg` | 重擊與蓄力遠射兩段放大：**停頓起點 396 ＝ 命中 396**（修正前 270，虛線）；遠射 **停頓起點 1446 ＝ 命中 1446**（修正前 520）；微震、命中聲 `hit_blunt` 都在同一刻，表格備註「和命中差 0 ms」 |

時間軸上的數字（正常速度）：

| 招 | 起手 | 出招 | 放出 | 命中 | 修正前的停頓 | 停頓起點 | 微震 | 命中聲（效果／實際） |
|---|---|---|---|---|---|---|---|---|
| 劍・重擊 60% | 0 | 260 | — | 396 | 270 | 396（100 ms） | 396（2 px） | 396／396 |
| 法杖・蓄力遠射 9 格 | 0（壓縮到 780 ms） | 960 | 1086 | 1446 | 520 | 1446（70 ms） | 1446（2 px） | 1446／1446 |
| 劍・輕擊 5% | 0 | 260 | — | 396 | 270 | 無 | 無 | 396／396 |

## noqa

沒有新增 eslint、ruff 例外。

## 待 PM 決定（都已照最保守的做法做完）

1. **同一刻多段的歸屬**：`shiftAt` 用「和哪一段的 `impactMs` 相等」判斷（和 `hits` 原本的規則一樣）。兩段的原始命中點恰好同一刻時，兩者都會跟第一段；`vfxFor` 的段落時間是接續的，實務上不會相等，沒有另外處理。
2. **`#impact` 的範圍**：只做「一招的時間軸」三個例子（重擊、被壓縮的遠射、輕擊），沒有四級停頓並排、三種微震、最後一擊放慢的專頁；`#result` 仍可看分級停頓與最後一擊。要補的話可以在同一頁加 `IMPACT_CASES`。
3. **AU-3 報告的「實際 ms 比效果時鐘晚」**：修了 `retime` 之後，沒有放慢時命中聲的實際 ms ＝ 效果時鐘 ms；有最後一擊放慢時實際 ms 仍會比效果時鐘晚（放慢在命中前的 120 ms），這是設計上的（聲音和畫面一起慢），沒有改。
4. **壓縮時的起手長度**：遠射那招起手被壓到 780 ms、命中落在 1446 ms（≤ 1.8 秒）是 6N-1 既有的規則，這次沒動。

## Commit

- `85c00d4a` fix(client): retime impacts with the skill timeline so hit stops start on the visual hit (6H-1b)
- `38672aa8` feat(client): skill gallery #impact timeline page (windup, hit, stop, shake, sfx; effect vs real ms) with screenshots (6H-1b)
- 報告：最後一個 commit
