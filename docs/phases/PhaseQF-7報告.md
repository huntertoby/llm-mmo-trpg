# Phase QF-7 報告｜小修合併段（佇列 (ak)、(al)）

實作者，2026-11-23，worktree `agent-a2f02f4fe94b35e9e`，基準 `c2371432f`。

> **狀態：全部完成。** `check.py --all` 0；slow parity／cli 0；build 0；三項比對都 different=0。

## 1. Commit

| commit | 內容 |
|---|---|
| `213301c40` | (ak) 事件卡的說書人框（占位與補上後）都留「多講一點」那一列；開發頁新模式；截圖 `docs/art/shots/qf-7/` |
| `5e6db06a7` | (al) `world_crafting_view` 的鐵匠裝備說明先拿掉每段結尾的「。」再用「；」接 |
| 最後一個 commit | 報告 |

## 2. 做法

### 2.1 (ak) 旁白卡片不長高

- 原因：E6-c2 已經把文字區留到 3 行，但「多講一點」按鈕只有補上後、播到最後一段、後端有補充時才出現。旁白只有一段又有補充時，補上那一刻按鈕就出現，卡片長高一列。
- 做法（照 E6-c2 先留位子的思路，最小改法）：`StoryParts.tsx` 的 `StoryDialog`、`StoryPendingDialog` 多一個 `reserveMore` 參數。開著時，沒有「多講一點」按鈕就放一顆**同 class、看不見、不能按**的留位按鈕（`world-more-slot`：`visibility: hidden`、`pointer-events: none`、`disabled`、`tabIndex=-1`、`aria-hidden`）。因為是同一種按鈕，高度和真的按鈕逐像素相同，不用寫死像素。
- 只有 `EventCard` 的事件旁白（`world-event-story`、`world-event-story-pending`）傳 `reserveMore`；情境判定、判定結果的說書人框照舊。
- 附帶效果：多段旁白翻到最後一段、按鈕才出現時，卡片也不會再長高。
- 開發頁 `storyGallery` 多 `?mode=story-filled-more`：只有一段（36 字）、又有「多講一點」的旁白。

### 2.2 (al) 去掉「。；」

- `src/trpg/api/world_crafting_view.py` 新增 `join_clauses(parts)`：每段 `rstrip("。")` 後用「；」接（同前端 `gear/clauses.ts` 的 `joinClauses`）。`CraftGearView.description_zh` 改用它。
- 現有內容裡沒有詞條文字以「。」結尾，所以實際輸出不變（三項比對、CLI 快照都沒有差異）；這次是先擋住以後的內容。

## 3. 驗收

### 3.1 測試

- `client/src/world/eventStory.test.ts` 新題「QF-7（ak）」：只有一段又有補充的旁白、沒有補充的旁白、占位三種情況。
  - 三者的說書人框結構相同（外框、頭像、名字、文字區、「多講一點」那一列；只差文字與狀態屬性）。
  - 補上後是真的按鈕；占位和沒有補充時是留位按鈕。
  - 框以外的卡片 HTML（框前、框後）逐字相同。
- `tests/api/test_world_crafting_join.py`：
  - `join_clauses` 單元測試：結尾的「。」拿掉、連續的也拿；沒有「。」時和 `join` 逐字相同；句中的「。」不動；空清單。
  - 整合測試：測試內容庫把所有詞條文字補上「。」，再透過 API 打造一把稀有主手（有兩條以上的詞條）。`description_zh` 有「；」、沒有「。；」、結尾也沒有「。」。

### 3.2 截圖與量測（headless Chrome，800×600，`--mute-audio`、網址帶 `mute=1`）

| 截圖 | 卡片高 | 說書人框高 | 文字區高 | 「多講一點」列（高／上緣） | 選項按鈕上緣 |
|---|---|---|---|---|---|
| `docs/art/shots/qf-7/story-1-pending.png`（占位） | 483.6 | 117.1 | 69.1 | 17／258（留位） | 288、360、403、449 |
| `docs/art/shots/qf-7/story-2-filled-more.png`（補上：一段＋多講一點） | 483.6 | 117.1 | 69.1 | 17／258（真的按鈕） | 288、360、403、449 |
| `docs/art/shots/qf-7/story-3-filled.png`（補上：多段，第一段時沒有按鈕） | 483.6 | 117.1 | 69.1 | 17／258（留位） | 288、360、403、449 |

三張的按鈕位置完全相同。卡片比 E6-c2 量到的 467 高了約 17px，就是留位的那一列。

自己開的 vite（5199 埠）與 Chrome 都用 PID 關掉了。

### 3.3 結果不變（基準 `c2371432f` 的 `git archive`：`src`、`content`、`config`、`scripts`）

腳本沿用 QF-6 的 `budget.py`、`compare78.py`、`census_cmp.py`（暫存區 `qf7/run_cmp.sh`）。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算 | 442 招，兩邊結束碼 0，`cmp` 0 |
| 78 場（`compare78.py`） | `battles=78 events=26741 different=0`；規則包差異 0；結束碼 0 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`） | `cells=204 different=0 whole_equal=True`（兩邊結束碼 0） |

CLI 快照沒有差異（slow cli 全過）。

### 3.4 檢查指令

| 指令 | 結束碼 |
|---|---|
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports`（(al) 改的檔，commit 前） | 0、0、0、0 |
| `corepack pnpm -C client exec tsc --noEmit`（(ak) commit 前） | 0 |
| vitest `src/world`（(ak) commit 前，71 檔 871 題） | 0 |
| pytest `tests/api/test_world_crafting_join.py`、`test_world_crafting_api.py` | 0 |
| `uv run python scripts/check.py --all`（全部 commit 之後） | **0**：pytest 18961 passed、8 skipped；vitest 427 檔 5037 題；client typecheck 通過；已寫通過戳記 |
| `uv run python scripts/run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | **0**（995 passed） |
| `corepack pnpm -C client build` | **0** |

沒有新增 `# noqa`。

## 4. 待 PM 決定

1. **留位的代價**：事件卡的說書人框現在一律多留一列（約 17px），包括占位、和補上後沒有「多講一點」的旁白（那時下面是一列空白）。換來的是三種情況卡片高度、按鈕位置完全相同。另一種做法是占位時不留、補上後才出現按鈕，但那樣一段＋補充的情況還是會跳。交美術看截圖。
2. **(al) 目前沒有實際效果**：現有詞條文字沒有「。」結尾，鐵匠的裝備說明輸出不變；改動是先擋住以後的內容。整合測試用補上「。」的測試內容庫來驗。

## 5. 平衡疑慮

無。
