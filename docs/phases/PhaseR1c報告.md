# Phase R1c 報告：`engine/ai/utility.py` 按職責拆成子模組

依據：`docs/phases/整理提案-程式.md` 2.2 節 R1。分支 `dev/r1c`。做法照 R1a／R1b。

## 結果

`src/trpg/engine/ai/utility.py`（2,450 行）→ `src/trpg/engine/ai/utility/` 套件（共 2,770 行，多出的是各檔的 docstring 與 import）：

| 檔案 | 行數 | 內容 |
|---|---|---|
| `__init__.py` | 141 | 原模組 docstring＋子模組說明、re-export、原樣的 `__all__` |
| `position.py` | 532 | 位置價值常數、`OrdersSource`、`OrderContext`、`resolve_orders`、`ActionScore`、`_Walk`／`_Scene`／`_scene`、`position_value` 與各位置項（敵人、武器、朝向、掩護、輸出劣勢） |
| `gains.py` | 613 | 預覽收益：`_GainFrame`、傷害／擊倒／狀態／支援／表面／推擊／位移／防禦／層數／陷阱／掩護收益與 `_gains`；收益專用常數（`_DEFEND_RADIUS`、`_POSSIBLE_KILL_DIVISOR`、`_ATTACK_CAUSES`、`_SURFACE_HARM`）；`effective_skill`、`_rune_read_gains`（收益與技能估計共用，放這裡避免循環） |
| `scoring.py` | 515 | `score_action`、`_preview_score`、`extra_targets`、改寫類技能的事件分數、`_order_bonus`、`skill_cost`、`defend_score`、`run_score`、`vault_score` |
| `skill_estimate.py` | 421 | `skill_estimate` 與放置／特殊／衝鋒／影步／陷阱估計、`_supports` 系列、場地型技能價值 |
| `moves.py` | 164 | `worth_previewing`、`virtual_move_score`、`ice_slip_cost`、`reactive_enemies`、`is_risky_move` |
| `policy.py` | 384 | `UtilityAI` 本體與 `_hits_unit`、`_with_infusion` |

每檔 < 700 行。子模組依賴單向：`position` 為葉；`gains`、`moves` → `position`；`scoring`、`skill_estimate` → `position`＋`gains`；`policy` → `position`、`scoring`、`skill_estimate`、`moves`。沒有循環匯入、沒有延遲匯入、沒有新增 `noqa`。

## 做法

- 純搬移：腳本依原檔頂層敘述切段（含前置註解與屬性 docstring），逐字搬到所屬子模組，各檔複製原 import 區塊後以 `ruff --fix F401,I001` 清掉沒用到的。AST 比對：原檔 118 個頂層敘述（扣除模組 docstring、`__all__`、import）全部原樣出現在新檔，無缺、無多。
- 唯一的順序變動：`effective_skill`、`_rune_read_gains` 與 4 個收益常數移到 `gains.py`（內容未改）。
- re-export：全專案（src／tests／scripts／bot）從 `trpg.engine.ai.utility` 匯入的名稱 16 個（含私有 `_charge_estimate`、`_facing_terms`、`_harmful`、`_knock_collides`、`_scene`、`_supports`、`_unit_position_value`、`_weapon_terms`）；另加 `__all__` 其餘 7 個與不在 `__all__` 的公開名稱（`effective_skill`、`run_score`、`vault_score`、`skill_estimate`），共 **27 個**，一律以 `import X as X` 明確 re-export，`__all__`（13 個）不變。
- 呼叫端 import 一行都沒改；import-linter 契約沒動。沒有人以模組屬性 monkeypatch `utility`（已 grep）。
- `noqa` 照搬：7 個 `PLR0917`（`_cover_gains`、`skill_estimate`、`_special_estimate`、`_charge_estimate`、`_shadowstep_estimate`、`UtilityAI._score_other`、`UtilityAI._skill_candidates`）與 1 個 `PLR2004`。原檔沒有 `C901` 的 `noqa`（見待 PM 決定）。

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（1392 檔）、`lint-imports`（14 條契約 KEPT）：全過。
- `pytest -q tests/engine tests/sim tests/world -x -n 4`：5452 passed。
- CLI 快照（含 slow）`pytest -q -m "" tests/cli/test_output_snapshots.py -n 4`：25 passed（未重產）；`frozen_replay` 在 `tests/world` 內通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay` 通過（88 個動作、313 個事件）；拆前（`git archive HEAD` 的 src）與拆後的 `--log-json` byte 相同。
- 模擬：`trpg sim maps --seeds 5 --jobs 4` 拆前拆後的 `--json` 報表 byte 相同；文字輸出只差輸出路徑與執行時間兩行。
- 匯入圖：R3 的 Tarjan SCC 腳本（頂端匯入、不含 `TYPE_CHECKING`）在 `trpg.engine` 內無環；每個 engine 模組（165 個）在新直譯器中單獨匯入皆成功。

## 待 PM 決定

- 任務說明提到「6 個 C901 超標」，但原 `utility.py` 沒有任何 `C901` 的 `noqa`（ruff 也沒報超標），本段只有 7 個 `PLR0917` 照搬；6 個 C901 可能是指其他檔，R4 排段時請確認。
- `UtilityAI.__module__` 由 `trpg.engine.ai.utility` 變成 `trpg.engine.ai.utility.policy`。pickle 用於 `sim` 的多行程（同版本程式，不受影響）；若有任何持久化的 pickle 會失效，但目前沒找到。
- `ruff format` 保留了部分只剩 1～2 個名稱的多行括號 import（magic trailing comma），不影響檢查；之後若在意可一次收成單行。
