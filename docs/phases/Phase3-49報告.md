# Phase 3-49 報告｜射程計入預算（玩法決定 #53）

規格：`docs/phases/Phase3計畫.md` 第 58 節；設計：`docs/design/06-技能.md` 6.5（`28d8df5`）。

## 做了什麼

- **射程係數進預算器**（`src/trpg/skillgen/budget.py`）：固定射程 N（整數 ≥ 1）的技能，作用在單位的效果（shaped）點數再乘 `1 ＋ (N − 4) × 5%`（射程 1＝0.85、4＝1.00、10＝1.30）。武器射程、射程 0（以施放者／落點為中心的十字、方陣）、陷阱技能、自身／光環等沒有射程的形狀，係數 1.0。複合技能兩段各自依自己的形狀計算；`consume_stack`、傷害倍率等引用「傷害效果點數」的地方都含係數。
- **資料**：`content/skill_budget.yaml` 新增 `range_baseline: 4`、`range_step_permille: 50`（整數千分比，不寫死在程式）。
- **戰場變奏**：型態的射程 ±N 直接反映在型態本身的形狀上，所以**移除**舊的 `variant_range_step_permille`（基礎點數 ×5% 另外加價，會重複計算）。射程 −1 現在會少算（以前「不折抵」）。變奏步驟的說明文字同步更新。
- **工坊即時顯示**：`BudgetSummary` 多 `range_text`（例「射程 6：×1.1」，沒有固定射程為空字串）與 `range_coefficient`；明細表多「射程×」欄；複合技能每段也有一行；變奏型態列出自己的射程係數。玩家文字全中文。OpenAPI 與 `schema.d.ts` 已重產。
- **`trpg skills budget`**：每個技能多一行「射程 N：×係數」（有固定射程時）。
- **隨機組合器／LLM 補數值**：都經 `skill_budget`，自動照新預算；`tests/skillgen`、`tests/llm`、`tests/roguelite` 全過。
- **內建技能預算已知例外**：資料化為 `content/skill_budget.yaml` 的 `known_budget_exceptions`（5 個技能）。`trpg content check` 不把它們的 `budget.over`／`budget.weak` 算錯誤；`trpg skills budget --all` 另計「已知例外 5 個」並在列上標註。**未改任何技能數值**。
- 重算腳本：`scripts/range_budget_report.py`（安靜模式，只列射程係數 ≠ 1 的技能）。

## 內建技能重算報表（改前 → 改後 total ÷ 可用預算）

射程係數 ≠ 1 的技能共 52 個，其中改後超出 70～100% 的 7 個（含 2 個裝備授予技能，本來就在範圍外，不計）：

| 技能 | 射程 | 係數 | 改前 | 改後 | 狀態 |
|---|---|---|---|---|---|
| skill_arc_follow_up | 5 | ×1.05 | 98.9% | 103.8% | 超出上限 |
| skill_deep_freeze | 5 | ×1.05 | 97.9% | 102.8% | 超出上限 |
| skill_flare_sight | 6 | ×1.1 | 97.7% | 107.4% | 超出上限 |
| skill_armor_break_combo | 1 | ×0.85 | 74.5% | 66.3% | 過弱 |
| skill_quake_topple | 2 | ×0.9 | 76.9% | 69.2% | 過弱 |
| skill_gear_shield_wall（裝備，不計） | 1 | ×0.85 | 18.6% | 15.8% | 本來就過弱 |
| skill_gear_smoke_bomb（裝備，不計） | 3 | ×0.95 | 31.7% | 30.2% | 本來就過弱 |

改後仍在範圍內但已貼近下限（< 75%）的：death_spiral 71.3%、frost_touch 71.1%、splash_flask 71.8%、stone_wall 71.5%、undying_oath 72.4%、banish 73.2%、plant_totem／summon_plateau_totem／summon_pull_totem 73.7%、overcurrent 74.4%。貼近上限（> 95%）的：hex_bolt 96.1%、rune_thunderbolt 95.6%、raise_skeleton 98.8%（係數 ×0.95 但改前就 98.8%，沒變）。

完整 52 列用 `uv run python scripts/range_budget_report.py` 重現（全部技能超出範圍：改前 3 個＝裝備技等、改後 8 個）。

## 測試

- 新增 `tests/skillgen/test_range_budget.py`：射程 1、4、10、武器射程、自身各一組，驗證預算器係數＝工坊顯示（`range_text`／`range_coefficient`／每行 `range`）＝CLI 輸出；總點數 ＝ 射程 4 的同一招 × 係數；射程 0 與變奏射程；已知例外清單 ＝ 實際超出範圍的內建技能（調整技能後清單要同步，否則測試失敗）。
- 修改既有測試：`test_budget` 類寫死的點數（`consume_stack` 加成、超載技能）乘上射程係數；變奏測試改為「型態直接用射程係數」；工坊走查草稿（`workshop_walks.STRIKE`，射程 1）傷害倍率 1000 → 1400 以維持在合格區間（只是測試草稿，不是內建技能）；`tests/known_budget_exceptions.py` 讓逐技能的驗證測試略過 5 個已知例外的預算範圍違規（其他違規照查）。
- CLI 快照：`tests/cli/test_llm_propose_cli.py` mock n=3 快照因組合器結果改變而重產（`UPDATE_CLI_SNAPSHOTS=1`）；`skill_icons.json` 重產。
- 驗收結果：pytest skillgen／content／llm／api／roguelite／narrative／`-m "slow or not slow" tests/cli` 全過；vitest 936 全過；build 過；ruff、format、mypy、import-linter 過。未跑 `scripts/check.py` 全量。

## 待 PM 決定

1. **5 個內建技能超出 70～100%**（表中前 5 列）：怎麼調交玩法 PM（例如 arc_follow_up、deep_freeze、flare_sight 降傷害或加代價；armor_break_combo、quake_topple 加強或延長射程）。調整後從 `known_budget_exceptions` 移除。
2. **舊的變奏射程加價已移除**（避免與射程係數重複）：變奏射程 +1 現在是型態射程係數 +5%（相對該型態自己的總點數），不再是「基礎型態點數的 5%」；射程 −1 會少算。請玩法 PM 確認這樣符合 #53「戰場變奏的射程 +1 照算在變奏型態上」。
3. **射程 0 視為沒有射程（係數 1.0）**：十字／方陣以自身為中心時不打折（若要按公式 1 ＋ (0−4)×5% ＝ 0.8 計，需另行決定）。
4. 工作樹裡 `docs/phases/Phase4計畫.md` 與 `docs/開發PM交接.md` 有不是我修改的未提交變更（開工時 git status 是乾淨的），我沒有提交它們。
