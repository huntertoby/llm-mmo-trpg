# Phase PR-1｜#147 靶場測試模式：引擎

> 來源：`docs/玩法決定紀錄.md` #147、`docs/design/21-探索地圖與城鎮.md` 21.5 測試模式（共 6 點，第 6 點 commit 5bb8465b；**以 21.5 為準**）。使用者原話：「我說的那些是僅限靶場 讓測試更簡單」。
> 盤點：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\盤點-150與147.md` 第 3 節。#147 共 2 段，本段只做引擎；接線、API、前端、出發後回靶場在 PR-2（排在 OB-6 之後）。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 做法 | `BattleSetup.practice: PracticeRules | None = None`（內容 `target_tag: "training_dummy"`），`begin_battle` 抄進 `BattleState.practice`；**不放 `Ruleset`** |
| 自動過輪 | 只有放招和普攻才過輪；種族技算放招；**推撞、絆摔等基本動作不過輪** |
| 木樁被推進致命地形 | 回開場位置並補滿；其他被推走不歸位 |
| 必中 | 仍照常擲 d20（亂數取用次數不變），暴擊照 `natural >= crit_range` |
| 版號 | `LOG_FORMAT` → `/113`（照 `docs/phases/戰鬥紀錄格式變更.md` 1.1）；`WORLD_RULES_VERSION` 本段不動 |
| 源力、彈藥、種族技、戰技 | 依 21.5 測試模式第 6 點 |

## 範圍外

- 不改 API schema、`world/`、前端（PR-2）。不改 `content/world/newcomer.yaml`（OB-1 平行在改）。
- **實戰規則一個字都不能變**。

## 交付項目（對應盤點 3.2）

1. `practice` 旗標與 `clone`。
2. `engine/turns.py::finish_resolution`：清主角 `cooldowns`、`skill_uses`、`form_cooldowns`；補 `ap`、`move_points`、`stamina`、`mana`、`hp` 與其他 21.5 指定的資源；重設 `ran_this_turn`。
3. 自動過輪：`resolve_with` 依動作種類記到 `ctx`，`finish_resolution` 非預覽時 `end_turn`＋`advance_turn`；`PauseForDecision` 恢復後才做。**步驟列表不多出 `EndTurn`**。
4. 不倒下：全掃呼叫 `down_unit` 的路徑（`effects/handlers.py:209`、`:434`、`:532` 等），主角與木樁在 practice 時不倒。木樁 HP 歸 0 不倒、下一輪補滿（`turns.py::_end_round`）；致命地形依 PM 決定。
5. 必中與對抗必成：`rules/combat.py::roll_attack`、`reactions.py::_forced_outcome`、`skills/cast.py:279`、`control.py`、`maneuvers.py`、`preview.py::_chances`，預覽自動顯示 100%。
6. 每個分支都是 `if state.practice is not None`；只對 `training_dummy` 標籤的目標生效的部分要看標籤。

## 受影響的既有功能

| 項目 | 影響 | 處理 |
|---|---|---|
| 實戰 | 不變 | 逐筆事件比對（見驗收） |
| 技能工坊的 `training_dummy` | 沒帶旗標，不受影響 | 測試鎖住 |
| `tests/engine/test_state_clone.py`、`test_ruleset_hash.py`、12 個含 `/112` 的檔案 | 版號 | 照盤點 4.3 更新 |
| CLI 快照 | 只有 `LOG_FORMAT` 字串應該變 | 重產前逐類說明原因 |

## 行為一致測試

- 表格測試，**實際跑引擎**：沒 CD、次數不算、資源補滿、放招／普攻過輪、推撞／絆摔不過輪、種族技過輪、木樁必中、狀態與推撞必成、不倒下、木樁下一輪補滿、木樁進致命地形回開場位置。
- practice 模式一場 `--log-json` 重播一致，亂數取用次數與預期一致。
- **實戰不變**：`practice=None` 時，同種子至少 5 張地圖的事件列表與改前逐筆相同（`LOG_FORMAT` 字串除外）。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過；沒有新增複雜度 noqa，有的話逐一列理由。
- `tests/engine`、`tests/sim`、`tests/cli`、`tests/api`、`tests/test_architecture.py` 通過（CLI 快照帶 `TRPG_FULL=1 -m "not llm"`）。

## 報告

`docs/phases/PhasePR-1報告.md`：逐條驗收、`down_unit` 掃描清單、實戰不變的比對方法、給 PR-2 的介面說明、待 PM 決定。
