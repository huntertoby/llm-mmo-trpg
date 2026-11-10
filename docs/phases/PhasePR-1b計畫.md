# Phase PR-1b｜#147 測試模式引擎修正

> 來源：玩法 PM 審 PR-1（`docs/design/21-探索地圖與城鎮.md` 21.5，commit 8190b7d3）。前置：`docs/phases/PhasePR-1報告.md`。**實戰規則一個字都不能變**。

## 交付項目

1. `infuse_skill`、`activate_charge`、`command_summon` 算放招，**會過輪**（灌注要到召喚物下回合才放，指揮每輪限 1 次，不過輪測不到）。推撞、絆摔等基本動作仍不過輪。
2. 主角被推進致命地形：回開場位置並補滿，和木樁一致。開場位置被占用時回最近的空格。
3. 裝備充能也要補滿（21.5：不耗任何資源）。AP 補到本回合上限 4，維持。

## 範圍外

- 不改 API、`world/`、前端、`content/`（PR-2）。`LOG_FORMAT`、`WORLD_RULES_VERSION` 不動。

## 行為一致測試

- 表格測試，**實際跑引擎**：上面三項；同時保留 PR-1 既有的測試不放寬。
- **實戰不變**：`practice=None` 時，同種子至少 5 張地圖的事件列表與改前逐筆相同。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/engine`、`tests/test_architecture.py` 通過；`tests/cli` 帶 `TRPG_FULL=1 -m "not llm"` 通過。

## 報告

`docs/phases/PhasePR-1b報告.md`：逐條驗收、實戰不變的比對結果、待 PM 決定。
