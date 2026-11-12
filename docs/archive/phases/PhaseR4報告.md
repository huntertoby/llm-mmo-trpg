# Phase R4 報告：拆最長的函式、消掉複雜度 `noqa`

依 `docs/phases/整理提案-程式.md` 2.2 節 R4。純結構重構，行為逐字相同；沒有改任何公開函式簽名（被拆的私有函式 `_outcome_effects`、`_attack_once`、`_damage` 等的簽名也沒變）。`content/library.py _load_world` 已在 R1b 拆掉，不在本段。

## 結果

- `src/` 中 > 100 行的函式：**10 → 0**（指定 6 個＋額外 4 個；另把 `build_parser` 拆出來後 97 行的 `_add_sim_report_parsers` 一併拆掉）。
- 複雜度 `noqa`（`C901`／`PLR0911`／`PLR0912`／`PLR0915`）：**12 → 8**。
- 沒有新增任何 `noqa`。

### 前後行數（AST 量，含簽名與 docstring）

| 函式 | 前 | 後 | 做法 |
|---|---|---|---|
| `sim/metrics.py metrics_from_events` | 240 | 60 | 累計狀態搬進 `_Tally`，每種事件一個方法，`_HANDLERS` 以 `type(event)` 查表（22 種事件型別彼此沒有繼承關係，已用腳本確認，與原本的 `isinstance` 鏈等價）；`_unit_metrics`、`_summon_record` 組輸出 |
| `narrative/action_info.py _basic_actions` | 172 | 7 | 依原順序切成 `_move_and_attack`、`_maneuvers`、`_utility_actions`、`_turn_actions` |
| `cli/main.py build_parser` | 153 | 14 | 每個子指令一個 `_add_*_parser`（rng、content、map、skills、sim、battle） |
| `cli/main.py _add_sim_report_parsers` | 97 | 9 | 再拆成 `_add_sim_{matrix,completion,flash,skills,keywords}_parser` |
| `sim/batch.py format_report` | 123 | 20 | 每節一個 `_*_lines`（摘要、陣營、範本、控制、技能、整批事件、異常） |
| `engine/interactions.py _outcome_effects` | 120 | 33 | 參數打包成 `_Hit`，`_OUTCOME_HANDLERS` 依 `op` 分派到 9 個小函式 |
| `engine/summons/core.py summon_unit` | 115 | 77 | 抽出 `_build_summon`（建立單位，呼叫順序不變）、`_summon_duration`、`_conceal_on_summon` |
| `sim/matrix.py format_matrix`（額外） | 113 | 21 | 每節一個函式 |
| `engine/effects/handlers.py _damage`（額外） | 109 | 78 | 擲骰模式的數值計算抽成 `_rolled_damage`（回傳 `_RolledDamage`），亂數消耗順序不變 |
| `engine/reactions.py _attack_once`（額外） | 108 | 64 | 抽出 `_forced_outcome`、`_attack_hit_bonus`、`_emit_attack_rolled`、`_hit_multiplier`（呼叫順序不變） |
| `sim/matrix.py assemble_matrix`（額外） | 103 | 52 | 抽出 `_map_cells`、`_archetype_row`（加總順序不變，浮點結果相同） |
| `cli/main.py _battle`（額外，為了 noqa） | 53 | 38 | 參數檢查搬進 `_battle_args_error`，訊息與結束碼不變 |

### 去掉的 `noqa`（4 行）

| 位置 | 原本 |
|---|---|
| `sim/metrics.py metrics_from_events` | `C901, PLR0912, PLR0915` |
| `cli/main.py build_parser` | `PLR0915` |
| `engine/interactions.py _outcome_effects` | `PLR0911` |
| `cli/main.py _battle` | `PLR0911` |

### 保留的 `noqa`（8 行）

都是「單一分派／條件鏈，每個分支一行 return」，不在本段範圍，拆開只會把一個 if 鏈換成一張表：

| 位置 | 規則 | 理由 |
|---|---|---|
| `skillgen/budget.py _plain_base_points` | PLR0911 | 每種原語一個 return |
| `world/quests.py _leaf_holds` | PLR0911 | 每種條件一個分支（原註解） |
| `engine/oath_tracking.py _judge` | PLR0911 | 依事件種類分派（原註解） |
| `engine/preview.py _outcome` | C901, PLR0911, PLR0912 | 事件 → 預覽結果的單一分派；可比照 `metrics_from_events` 改查表，留待下次 |
| `engine/environment.py convert`（巢狀） | PLR0911 | 事件 → 預告變化的分派 |
| `engine/battle.py plan_move` | PLR0912 | 移動規劃的合法性檢查鏈 |
| `engine/path_preview.py _convert_own` | PLR0911 | 單純的事件分派（原註解） |
| `engine/skills/targeting.py resource_problem` | PLR0911 | 每種資源一個 return |

### 剩下 80～100 行的函式（未處理）

`engine/preview.py _build` 99、`engine/view.py _unit_view` 96、`skillgen/proposal.py build_proposal_models` 92、`roguelite/progress.py finish_battle` 89、`engine/state.py clone` 89、`world/step.py world_step` 88、`engine/effects/handlers.py apply_status` 87、`engine/battle.py begin_battle` 87、`api/glossary.py build_glossary` 87、`llm/naming.py name_skill` 85、`api/app.py create_app` 84、`cli/battle.py cmd_battle` 83、`content/world_events.py load_world_event_content` 82、`api/schemas.py preview_out` 82、`engine/turns.py start_turn` 81。

## 逐字比對

拆前在 `dev/r4` 起點（main `6937574`）先存基準，拆完再跑一次比對：

| 項目 | 結果 |
|---|---|
| `trpg sim maps --seeds 5 --jobs 4 --json` | JSON 逐 byte 相同；文字報表扣掉「已寫入 …」路徑與「執行時間」行後逐 byte 相同 |
| `trpg sim matrix --maps swamp,<另一張> --seeds 2`（額外，守 `format_matrix`／`assemble_matrix`） | JSON 與文字（扣路徑、耗時）相同；另以舊版模組對同一份報表（含人工加上的異常場次）跑 `format_matrix`，輸出相同 |
| `trpg --help` 與 28 個子指令 `--help`（遞迴走訪全部子指令） | 29 頁逐字相同 |
| `trpg battle --map swamp --seed 7 --log-json` | JSON 逐 byte 相同；終端輸出只差「已寫入戰鬥紀錄：」的路徑；`battle replay` 驗證通過 |
| `_basic_actions`（三種 `refill`） | 以舊版模組比對 16 則說明，完全相同 |
| `trpg battle` 錯誤參數 5 種 | 訊息與結束碼 2 與原本相同 |

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（1392 檔）、`lint-imports`（14 契約）全過。
- `uv run pytest -q tests/sim tests/narrative tests/cli tests/engine tests/world -x -n 4`：5952 passed
- CLI 快照（含 slow）`uv run pytest -q -m "" tests/cli/test_output_snapshots.py -n 4`：25 passed（未重產）
- `tests/world/test_field_ctx_replay.py`（`frozen_replay`）：通過。

## 待 PM 決定

- `engine/preview.py _outcome`（`C901, PLR0911, PLR0912`）是剩下 8 個 `noqa` 中唯一同時超三條規則的，可比照本段 `metrics_from_events` 改成事件型別查表；要不要排進下一個整理段？
- 80～100 行的 15 個函式是否另排（提案只要求 > 110 行歸零）。
