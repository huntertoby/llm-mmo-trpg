# Phase IP-1 計畫｜技能圖示道具 `icon_prop`（#151）

> 開發 PM（第六任）2026-11-12。先讀 `docs/dev/上手-內容資料與模擬.md`（全文）與 `docs/dev/上手-引擎戰鬥結算.md` 第一、三節。

## 依據（規則以這兩處為準，不得放寬或重新解釋）

- `docs/design/06-技能.md` **6.36**（第 1375 行起；含 2026-11-12 補的大類對應規則）、`docs/玩法決定紀錄.md` #151。
- 美術清單 `docs/art/技能圖示道具清單.md`：**第 1 節 57 個值＝允許清單**；**第 2 節 36 招的建議值全部採用**（玩法 PM 已審）；第 3 節清單外的（煙霧彈、瓶、吼聲）不填。

## PM 決定（不要再問）

| # | 決定 |
|---|---|
| D1 | `icon_prop` 是技能內容的**選填**欄位，**只影響圖示**：不進引擎結算、預算、重播、出題；`trpg.engine` 不得讀它 |
| D2 | 值只能是允許清單內的值；**要和技能的武器大類對得上**：副手盾算近戰；法書與法器珠算法器；元素、召喚、化身類道具不屬於任何大類；技能本身沒有武器大類的（法術、裝備技）可用任何道具。違反者由內容資料檢查擋下（`trpg content check` 與 pytest） |
| D3 | 只有 `content/skills/` 手寫技能可填；LLM 生成與白板配方**不帶**：輸出裡有就丟掉、不算錯（不讓驗證失敗） |
| D4 | 允許清單放成內容資料（`content/` 下一個 YAML，從美術第 1 節轉入，含每個值所屬大類），schema 驗證；不要寫死在程式裡 |
| D5 | 後端 `narrative/skill_icon.py` 的 `icon_of()` 帶出 `icon_prop`（有填就帶、沒填照現行推導），API 跟著帶；`gen:api` 並 commit 產物。前端本段**不改畫法**（技能主圖是之後的 Q 版段），只要型別跟上、既有測試過 |

## 交付

1. 技能 schema 加 `icon_prop: str | None`；允許清單內容檔＋schema；資料檢查規則（D2）。
2. `content/skills/` 36 招填值（照美術第 2 節，逐字）。
3. LLM 技能提議／白板配方的輸入清洗：遇到 `icon_prop` 丟掉（D3），寫測試。
4. `icon_of()` 與 API 帶出（D5）。
5. **行為一致測試**：
   - 「拿掉後戰鬥結果相同」：取有填 `icon_prop` 的技能，各跑同種子戰鬥兩次（原內容 vs 移除所有 `icon_prop` 的內容），事件序列與結果逐筆相同。
   - 內容 digest 是否因 `icon_prop` 改變：若 digest 涵蓋技能全文，接受改變但在報告寫明；不得讓重播驗證因 `icon_prop` 失敗。
   - 資料檢查表格測試：合法值、清單外值、大類不符（例：弓技能填劍類道具）、無大類技能填任何值、元素類道具配任一大類技能——各一列，期望值由 6.36 推得。
   - 36 招每一招的值都在允許清單內且通過大類檢查（從內容檔讀，不手寫清單）。
6. 報告 `docs/phases/PhaseIP-1報告.md`，含「待 PM 決定」最多 10 點；順手更新 `docs/dev/上手-內容資料與模擬.md`（新欄位與檢查）。

## 驗收條件

1. 交付 5 的測試全過；`tests/content`、`tests/skillgen`、`tests/narrative`、`tests/api` 中相關檔與 `tests/test_architecture.py` 過（列出跑了哪些）。
2. `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy`、`uv run lint-imports`、`trpg content check` 結束碼 0；一場 `trpg battle … --log-json` 加 `replay` 通過；`corepack pnpm -C client typecheck` 0。
3. `src/trpg/engine/` 沒有任何改動（`git diff --stat` 為證）。
4. 版號：只改內容與顯示，`WORLD_RULES_VERSION`／`CHAR_FORMAT`／`LOG_FORMAT` 不加；若你判斷需要，寫理由。

## 工作環境與規矩

- Windows：`uv run python`；新 worktree 先 `uv sync --frozen` 與 `corepack pnpm -C client install --frozen-lockfile --offline`，之後加 `UV_NO_SYNC=1`；pytest 平行最多 `-n 8`；不跑完整 `scripts/check.py`、不跑模擬；不啟動伺服器。
- 不結束不是自己啟動的程序；等待用完成通知，不寫 until／while 輪詢迴圈。
- 子 agent 一律 Opus 5.5（`model: "opus"`）並往下傳。
- 不要 push；commit 結尾帶 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
