# Phase R3 報告：解開 `trpg.engine` 子模組的循環匯入

依 `docs/phases/整理提案-程式.md` 2.2 節 R3。純結構重構，不改行為；舊匯入路徑都照舊可用（在原模組轉出），`src/trpg/engine` 以外的呼叫端沒有改。

## 結果

- 函式內延遲匯入（`# noqa: PLC0415`）：**18 → 3**。
- 模組頂端的匯入圖（不含 `TYPE_CHECKING`、不含函式內匯入）在 `trpg.engine` 內沒有任何環（以腳本跑 Tarjan SCC 確認）。
- 沒有新增其他 `noqa`；import-linter 契約沒有放寬。
- 效果處理器（`register_effect`）與事件觸發（`register_trigger`）的註冊順序與重構前完全相同（腳本比對 `_HANDLERS`、`_TRIGGERS` 的內容與順序）。

### 抽出的葉模組（只讀狀態或只放型別，不依賴效果佇列）

| 新模組 | 內容（自哪裡搬來） | 原模組轉出 |
|---|---|---|
| `engine/trigger_types.py` | `Fired`、`GEAR_PREFIX`、`GEAR_ATTACK_RUNE`、`MODIFIER_ON_HIT`（`skill_triggers`） | `skill_triggers` |
| `engine/charge_queries.py` | `DELAYED_RELEASE`、`attacked_release`、`charged_skill`、`release_of`（`delayed`，原 `_charged_skill`、`_release_of`） | `delayed` |
| `engine/oath_tracking.py` | `OathSetup`、`OathTracker`、`observe_oath`、`oath_warning`、違反判定、常數（`oaths`；`_breach` 改名 `breach_oath`） | `oaths` |
| `engine/stack_queries.py` | `required_stack`（`stacks`） | `stacks` |
| `engine/copy_rules.py` | `has_copy_effect`、`uncopyable_reason`、`copy_source`、`copy_free_problem`（`copying`） | `copying` |
| `engine/zone_triggers.py` | 區域查詢（`zone_spec`、`zone_cells`……）、`flush_zone_entries`、`zones_turn_start`（`zones`；私有輔助改為公開名 `sorted_cells`、`caster_cells`、`step_cells`、`zone_when`、`find_zone`） | `zones` |
| `engine/effects/surface_entry.py` | `enter_surface`、`ability_modifier`（`effects/handlers`） | `effects.handlers` |

另外兩處小搬動：
- `gear_attack_element` 與分組輔助（`_groups` → 公開名 `affix_groups`）由 `gear/enhance` 移到 `gear/core`（`enhance` 轉出），`attack_element` 改從 `gear/core` 匯入，`enhance` 就能在頂端匯入 `attack_element`。
- `copy_problem` 由 `copying` 移到 `skills/targeting`（要列舉同模組的 `selections`；`copying` 轉出）。

### 改用登錄（執行流程互相呼叫的 4 處）

被動觸發的結算（`skill_triggers.settle`）在效果佇列清空時被呼叫，又要回頭結算層數累積、裝備詞條、延遲段、友方倒下反應（這些都會再結算效果）。這是執行流程的遞迴，不只是型別。做法與既有的 `skills/casting.install` 相同：
- `skill_triggers.register_fired_resolver(kind)`：`stacks`（`stack_gain:`）、`gear/triggers`（`gear:`）、`delayed`（`delayed_release`）在載入時登錄。
- `skill_triggers.register_downed_handler`：`reactions.ally_downed_reactions` 登錄。
- `trpg.engine` 套件一載入就會匯入這些模組（已確認四個都在）；沒登錄時拋 `RuntimeError`（同 `casting`）。
- `stack_gain.resolve` 移到 `stacks.resolve_stack_gain`（它要用 `add_stacks`）。`stack_gain.resolve` 只有 `skill_triggers` 用到，引擎外沒有呼叫端，所以沒有留舊名稱（見待 PM 決定）。

### 保留的延遲匯入（3 處）與理由

| 位置 | 理由 |
|---|---|
| `lifecycle.py` `summons.core.detonate_on_downed` | 單位倒下的處理（`lifecycle`，被效果處理器呼叫）要引爆召喚物；`summons.core` 匯入 `lifecycle`（`make_unit`、`dismiss_summon`）並結算效果。這是執行流程的遞迴；拆開要讓倒下處理改成登錄式掛鉤，順序（先引爆、再生成）也要一併設計。 |
| `lifecycle.py` `rule_changes.spawn_on_downed` | 同上：`rule_changes` 匯入 `lifecycle` 與 `summons.core`。 |
| `effects/__init__.py` `turns.finish_resolution` | 只有測試用的 `run_effects` 用到；`turns` 匯入效果套件。改成頂端匯入要讓效果套件依賴回合流程（方向反了），搬走 `run_effects` 又會改變它的匯入路徑。 |

### 新的匯入方向（簡圖，箭頭＝「匯入」）

```
上層：turns / battle / reactions / summons / rule_changes / zones / delayed / stacks / gear.triggers / oaths
        │ （登錄 → skill_triggers；頂端匯入 ↓）
效果：effects(套件) → effects.queue → { triggers, skill_triggers, traps, zone_triggers, effects.surface_entry }
        │
觸發：skill_triggers → { trigger_types, charge_queries, stack_gain, modifiers, skills.targeting, skills.casting(登錄式) }
        │
核心：context → { oath_tracking, skill_triggers, state } ； state → { oath_tracking, gear.state }
        │
查詢：skills.targeting → { stack_queries, copy_rules, attack_element → gear.core, ... }
葉　：trigger_types、charge_queries、stack_queries、copy_rules、oath_tracking、events、rules.*
```

## 驗收

- `ruff check`、`ruff format --check`、`mypy`（1386 檔無錯誤）、`lint-imports`（14 kept）通過；`tests/test_architecture.py` 13 passed。
- `pytest -q tests/engine tests/cli/test_output_snapshots.py tests/world tests/sim tests/api/test_openapi_snapshot.py -x -n 4`：5455 passed（CLI 快照與 `frozen_replay` 未重產）。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay` 通過（88 個動作、313 個事件，與 R1a 相同）。
- `scripts/export_openapi.py` 後 `client/openapi.json` 無差異（byte 相同）。
- 每個 `trpg.engine` 子模組（159 個）各自在乾淨的直譯器中第一個匯入都成功。
- `grep -c "noqa: PLC0415"`（`src/trpg/engine`）：18 → 3。

## 待 PM 決定

1. `stack_gain.resolve` 改名搬到 `stacks.resolve_stack_gain`，沒有留舊名稱（引擎外沒有使用者；若要嚴格保留舊路徑，`stack_gain` 必須匯入 `stacks`，會重新形成環）。
2. 保留的 3 處延遲匯入：若要清零，`lifecycle` 的倒下處理可比照 `register_fired_resolver` 改成登錄式掛鉤（另開一段，需確認引爆與生成的先後順序不變）。
