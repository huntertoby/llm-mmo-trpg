# Phase 3T-6 報告｜`engine/` 拆子套件

純搬移、行為不變（`git mv` 保留歷史；不留相容轉發模組）。

## 搬移對照表

| 舊路徑（`trpg.engine.`） | 新路徑 |
|---|---|
| `gear` | `gear.core` |
| `gear_charge` / `gear_enhance` / `gear_reactions` / `gear_state` / `gear_summon` / `gear_triggers` / `gear_view` | `gear.charge` / `.enhance` / `.reactions` / `.state` / `.summon` / `.triggers` / `.view` |
| `summons` | `summons.core` |
| `summon_control` / `summon_variants` | `summons.control` / `summons.variants` |
| `race_skills` | `race.skills` |

- `gear_summon` 只依賴 `gear` 與 `gear_state`，歸在 `gear/`（`summons.core` 單向匯入它，無循環）。
- 子套件的 `__init__.py` 只有 docstring，沒有重新匯出。
- `race_skills`（`engine/race/skills.py`，種族技的合法性與結算，`UseRaceSkill`）與 `engine/rules/race.py`（種族被動的規則查詢）、`engine/ai/race.py`（AI 選種族技）是三個不同層：後兩者匯入前者，沒有搬動。

## 呼叫端

共改 80 個檔案：gear 41、summons 28（含 `client/openapi.json`、`client/src/api/schema.d.ts` 內由 docstring 產生的文字）、race 11（部分檔案重疊），另手改 `tests/engine/test_race_skills.py`（`from trpg.engine.race import skills as race_skills`）、`primitive_coverage.py` 錯誤訊息、`summon_foxfire_decoy.yaml` 註解。pyproject 的 import-linter 設定只列 `trpg.engine` 整體，不需修改；`tests/test_architecture.py` 未改。因三組的呼叫端大量交疊，三組搬移合為一個 commit。

## 驗收

ruff、format、mypy、lint-imports 全過；`tests/engine`（含 architecture、primitive_coverage）3797 通過；content＋skillgen 3667 通過；narrative／api／roguelite／sim 894 通過；`tests/cli` 155 通過（快照未改）。
