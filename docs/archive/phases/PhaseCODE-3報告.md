# Phase CODE-3 報告：同名小工具去重（整理提案 I3）＋ CODE-1 小尾巴

依據 `docs/phases/整理提案-程式.md` 2.1 I3 與 `docs/archive/phases/PhaseCODE-1報告.md`「留給下一段」。只動 `src/**`（不含 `src/trpg/llm/**`），未動 tests。

## 交付

| 項目 | 內容 | 合併份數 | commit |
|---|---|---|---|
| 1 | 新模組 `trpg.shared.fmt`：`ratio_pct`、`percent_of`、`exact_pct`、`permille_pct`、`signed`、`signed_zh`、`mean` | 17 份 → 7 個函式（見下表） | `156af0ef` |
| 2 | 新模組 `trpg.sim.report_table.markdown_table` | `_table` 4 份 → 1 | `7de94fed` |
| 3 | 新模組 `trpg.server.clock.unix_now`，作為 `clock` 參數預設 | `_now` 4 份 → 1 | `ae55ee59` |
| 4 | `trpg.content.schemas.duplicates` | `_duplicates`／`_dups` 5 份 → 1 | `4df2a46b` |
| 5 | 刪 skillgen 3 個死定義（`summon_spec`、`keyword_def`、`_penalty_type`；再 grep 含字串／`getattr` 皆 0 引用）＋ 3 處 docstring 改成 `trpg.api.primitive_coverage` | — | `b5fd2c8e` |

`src/` 合計：+278／−345，淨減 67 行（含 4 個新模組的檔頭與 docstring；被刪的重複函式本體約 −150 行）。

### 1 的對照

| 新函式 | 取代 | 備註 |
|---|---|---|
| `ratio_pct` | `sim/batch`、`sim/matrix`、`sim/skill_report`、`cli/budget` 的 `_pct`，`skillgen/validate` 的 `_percent` | 全是 `f"{x*100:.1f}%"`；Fraction 版本原本就先 `float()` |
| `percent_of` | `sim/attrition`、`sim/baseline`、`sim/difficulty_sweep` 的 `_pct` | 回傳數值，分母 0 → 0.0 |
| `exact_pct` | `sim/flash_economy`、`sim/flash_report` 的 `_pct` | Fraction 取到 0.1%，分母 0 → 「—」 |
| `permille_pct` | `narrative/action_info` 的 `_pct`、`skillgen/proposal_subset` 的 `_percent` | `f"{‰/10:g}%"` |
| `signed` | `narrative/events` 的 `_signed` | ASCII 負號 |
| `signed_zh` | `content/form_text`、`content/battle` 的 `_signed` | 全形「−」。`battle` 原本 0 會印「−0」，但三個呼叫端都先 `if x` 擋掉 0，輸出不變 |
| `mean` | `sim/attack_flow_report`、`sim/skill_report` 的 `_mean` | 空序列 → 0.0 |

### 刻意沒合併（行為不同，保留原函式）

- `sim/resource_report._pct`（`None` → 「—」、取整數 `.0f`）、`sim/resource_report._mean`（略過 None、再 ÷1000）、`sim/summon_report._mean`（Fraction 加總、空 → None）。
- `world/situation_coverage._pct`（固定分母 `DICE_PAIRS`、整數除法）。
- `content/form_text._percent`（帶正負號的千分比）、`narrative/skills._percent`（千分比 → 不帶 % 的數字字串）。
- `api/world_story_view._signed`（全形「＋」）、`engine/gear/view._signed`（有 `permille` 參數、`{:+g}%`）。
- `api/login_limit._now`（`time.monotonic()`，不是牆上時間）。
- `api/world.WorldStore._now`（方法，轉呼 `self.clock()`，給 LeagueStore 晚綁定用）。

## 位置的選擇

- `unix_now` 放 `trpg.server`：`trpg.shared` 禁讀時間（banned-api），`server` 不得匯入 `api`，而 `api` 本來就匯入 `server`，所以只有 `server` 兩邊都能用。
- `duplicates` 放 `trpg.content.schemas`：五個使用者都已匯入 `ContentModel`，不新增任何邊。

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（1382 檔）、`lint-imports`（14 kept）全過。
- `tests/cli/test_output_snapshots.py tests/sim tests/test_architecture.py`：165 passed。
- 分項：項 1 `tests/sim tests/narrative tests/cli tests/content` 等 3389 passed；項 3 `tests/server` 與 api 的 llm_health／login_limit／world／league 118 passed；項 4 `tests/content` 等 2835 passed；項 5 skillgen／narrative 相關 551 passed。
- 重播 `swamp` 種子 7：88 個動作、313 個事件，最終狀態一致。
- 沒有測試 import 或 monkeypatch 被改名的私有函式（`_now` 也沒有），不需保留別名。

## 留給下一段

- `src/trpg/llm/skill_eval.py` 的 `_pct(part, total)`（一位小數、分母 0 → 「—」，浮點版），本段不動；下一段可改用 `fmt` 或保留（與 `exact_pct` 的捨入方式不同，浮點 vs Fraction）。

## 待 PM 決定

1. 項 4 超出指定的兩份：`world_events._duplicates`（AST 相同）、`world_economy._duplicates`（Counter 寫法，結果相同）、`fields._dups`（相同）一起併入；若只要兩份可回退這部分。
2. 是否要把「沒合併」清單裡的變體也統一格式（例如全形／半形負號、`.0f` vs `.1f`）——這會改輸出文字，屬玩法／UI 決定，本段不做。
