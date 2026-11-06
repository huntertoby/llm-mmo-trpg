# Phase 2C-2 報告：控制分派與戰術指令

> 實作：implementer｜依據 `docs/phases/Phase2C計畫.md` 第 4 節（另含 0.1 #9）｜分支 `worktree-agent-a47424ec13ebc0754`（基於 main 40ebb0b）

## 1. 摘要

- `run_battle(controllers=…)`：行動者的 policy 依「單位 ID → 陣營 → 預設」查找；重播不受影響。
- 戰術指令 schema（`trpg.engine.ai.orders`：`focus_target`／`hold_position`／`retreat_to`／`protect`／`use_environment`、`OrderSet`、`validate_order`）與效用 AI 的評分加成（數值在 `content/ai_profiles.yaml` 的 `orders:`）。
- `CommandedAI`（指揮官包裝器，含 `order_log`）、4 個腳本指揮官（`trpg.sim.commanders`）、可 pickle 的 `CommandedPolicyFactory`；指令寫入 `BattleLog.orders`（舊紀錄照常載入）。
- CLI：`trpg battle`／`trpg sim maps` 新增 `--ally-commander`／`--enemy-commander`；戰鬥紀錄在每輪印出新下達的指令。
- 沒有指令時，整場戰鬥每個決策的每個動作分數與 2C-1 逐位元相同（1 萬餘筆分數雜湊相同、`trpg sim maps --seeds 20` 標準輸出 `cmp` 相同）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `6cf3338` | 指令 schema、驗證、`ai_profiles.yaml` 的 `orders:`、效用 AI 的評分加成 |
| `d6bfa28` | 控制分派（`controllers`）、`CommandedAI`、腳本指揮官、`BattleLog.orders`、CLI 參數、測試 |
| `7647ec1` | `scripts/bench_battle.py` 的決策時間微基準；省略「全為 0 的環境權重」的多餘計算 |
| 本報告的 commit | `docs/phases/Phase2C-2報告.md` |

## 3. 驗收條件逐條結果

1. **`scripts/check.py` 五項全過、import-linter 通過**：ruff／format／mypy／lint-imports／pytest（1008 passed，6 個 slow 未跑）全部通過。`trpg.engine` 沒有匯入 `trpg.sim`：`CommandedAI` 與指令 schema 在 `trpg.engine.ai`，腳本指揮官在 `trpg.sim.commanders`（`lint-imports` 3 contracts kept）。
2. **控制分派**：`tests/engine/test_orders.py::test_controller_precedence_unit_then_team_then_default`（單位 ID 優先於陣營、陣營優先於預設；並證明不影響動作列表）。
3. **五種指令的情境測試**（同檔）：
   - `focus_target`：`test_focus_target_changes_the_attack_target`（預設打殘血的 A，指令集火 B 就打 B）、`test_focus_target_makes_approach_follow_the_target`（`approach` 改看目標）。
   - `hold_position`：`test_hold_position_keeps_the_unit_near_the_spot`（敵人遠時，radius 0／1／2 都不離開；沒有指令時前進）。
   - `retreat_to`：`test_retreat_to_moves_toward_the_spot_instead_of_the_enemy`。
   - `protect`：`test_protect_moves_toward_the_ward`、`test_protect_overrides_the_default_ward`（對象固定為 ward）。
   - `use_environment`：`test_use_environment_prefers_detonating_the_barrel`（直接攻擊 23.4 分 vs 引爆油桶 21.5 分；加上指令後桶 112.5 分，改選引爆；使用 `cunning`，原因見待決 #1）。
4. **無效指令被忽略並記入 `ignored`**：`test_invalid_orders_behave_exactly_like_no_orders`（已倒下、不是敵人、不是友方、保護自己、格子在地圖外，單獨或合併，`rank` 分數列表與無指令逐項相等）；`test_ignored_orders_are_recorded_with_reasons`（`OrderRecord.ignored` 含範圍與原因）；`test_validate_order`。
5. **沒有指令時分數與 2C-1 完全相同**：
   - 測試：`test_no_orders_scores_match_plain_utility_ai_per_action[4 張地圖]`（整場戰鬥每個決策的每個動作分數，`orders=None`、空指令來源、指揮官回傳空 `OrderSet` 三者相同）。
   - 與舊版（40ebb0b）逐動作比對（一次性腳本，4 張地圖 × 3 個種子，每個決策 `rank()` 的全部「動作｜分數」做 sha256）：舊版 `10430 2b3b5338820af2fab6412ca6d19ce10fb2476a9e182f55a1de1674adba907dc2`，新版 `10430 2b3b5338…07dc2`，完全相同。
   - `trpg sim maps --seeds 20 --jobs 4` 的標準輸出，舊版與新版 `cmp` 無差異。
6. **指令寫入 `BattleLog`；`--log-json` → `replay` 一致；舊格式載入**：`test_orders_are_written_to_the_log_and_replay_matches`、`test_old_log_without_orders_still_loads`、`tests/cli/test_commander_cli.py::test_log_json_contains_orders_and_replay_verifies`（含刪除 `orders` 欄位的舊格式仍可重播）。實跑：`trpg battle --map oil_depot --seed 2 --ally-commander hold_start --enemy-commander focus_lowest_hp --log-json b.json` → `trpg battle replay b.json` 印出「重播驗證通過：109 個動作、406 個事件，最終狀態一致」。
7. **勝率對照表**：見 5.1。
8. **效能數據**：見 5.2。

其他：`tests/sim/test_commanders.py`（四個指揮官的行為、registry、pickle、`--jobs` 無關）、`tests/cli/test_commander_cli.py`（CLI 輸出、參數錯誤）。

## 4. 設計與實作說明

### 4.1 控制分派

`run_battle(…, controllers: Mapping[UnitId | Team, Policy] | None = None)`：每次需要 policy 決策時，先查 `controllers[unit.id]`，再查 `controllers[unit.team]`，最後用 `policy` 參數。`legal_actions` 只剩 `EndTurn` 的自動結束回合、`prompt` 反應的 `decide` 不經過 policy，與以前相同。

### 4.2 指令 schema（`trpg.engine.ai.orders`）

pydantic（`frozen`、`extra="forbid"`），以 `kind` 區分：`FocusTarget(target)`、`HoldPosition(at, radius=1, 0–3)`、`RetreatTo(at)`、`Protect(ward)`、`UseEnvironment()`。沒有任何數值、骰子或結果欄位（測試證明多餘欄位被拒絕）。`OrderSet(team_orders, unit_orders)`：每種 `kind` 最多一個；`for_unit(uid)` 在單位有自己的條目時完全取代陣營指令（即使是空的）。`validate_order(state, team, order) → str | None`（無效原因）。`OrderRecord(round, team, orders, ignored)`、`IgnoredOrder(scope, order, reason)`。

### 4.3 評分加成（`UtilityAI`）

`UtilityAI(profiles, …, orders=None)`：`orders` 是 `(state, unit_id) → tuple[TacticalOrder, …]` 的來源（可設定屬性；`CommandedAI` 建構時把自己的來源裝上去）。每次決策開始時 `resolve_orders` 濾掉無效指令（再驗證一次，目標在回合中倒下就悄悄忽略；保護自己視為無效），得到 `OrderContext`；全部無效或沒有指令時為 `None`，走的程式路徑與 2C-1 完全相同。

| 指令 | 實作 |
|---|---|
| `focus_target` | 位置價值的 `approach` 改看與目標的距離；動作分數 ＋ （1500‰ − 1000‰）× 「只計對目標的預覽收益」。「對目標的收益」是同一個 `_gains` 加上 `only=目標`：主要傷害、技能傷害、其他傷害、擊倒、推擊、狀態、擊倒對抗、目標站上有害表面、目標離開掩護；不含治療、友方誤傷、防禦、掩護物傷害 |
| `hold_position` | 位置價值 −`hold_weight`（20）× max(0, 曼哈頓距離(at) − radius) |
| `retreat_to` | 位置價值 −`retreat_weight`（15）× 曼哈頓距離(at)；`approach`、`threat` 權重視為 0 |
| `protect` | `ward` 固定為指令對象；`protect` 權重取 max(行為模式, `protect_min`＝12) |
| `use_environment` | 動作分數 ＋ （2000‰ − 1000‰）× 「只計環境收益」（`env_damage`、`env_kill`、`push`、`surface`、`expose`；做法是把其他權重歸零後再算一次 `_gains`）。這五個權重全為 0 的行為模式略過這次計算（結果必為 0） |

加成的倍率寫成「（倍率 − 1）× 對應收益」加在原分數上，所以 1000‰ 即無加成。指令只改評分，不改合法動作。

### 4.4 `CommandedAI` 與指揮官

- `Commander = Callable[[BattleState, Team], OrderSet | None]`（`None`＝沿用上一個）。`CommandedAI(ai, commanders, *, on_order=None)`，可當 `Policy`；`order_log: list[OrderRecord]`。
- **呼叫時機**：某陣營在每一輪的第一次決策，以及（敵我存活單位數）與上次呼叫不同時。沒有指揮官的陣營不受影響。只有指揮官真正回傳 `OrderSet`（不是 `None`）時才記錄一筆 `OrderRecord`（含 `ignored`）。
- `run_battle` 結束時，把 `policy` 與 `controllers` 中符合 `OrderLogging`（有 `order_log`）的物件的紀錄收進 `BattleRun.orders`（同一物件只算一次，依輪數與陣營排序）；`BattleRun.to_log()` → `BattleLog.orders`（預設 `[]`）。`LOG_FORMAT` 維持 `/6`：新欄位有預設值，舊紀錄可載入，動作格式沒變。重播只重播動作。
- **腳本指揮官**（`trpg.sim.commanders`，`COMMANDER_FACTORIES`：ID → 每場新建的類別）：`focus_lowest_hp`（可見＝未隱蔽的敵人中 HP 最低，平手依 ID）、`protect_weakest`（HP 比例最低的友方；隊伍只剩一人時回傳空指令）、`hold_start`（`unit_orders`，起始格是第一次看到該單位時的位置；每場新建所以不會跨場）、`use_env`。`CommandedPolicyFactory(profiles, ally, enemy)` 是 frozen dataclass，只存 ID，可 pickle（2C-1 待決 #9）；`map_spec(…, ally_commander=, enemy_commander=)` 用它。

### 4.5 CLI

- `trpg battle … [--ally-commander id] [--enemy-commander id]`：指令在下達當下印出（位於該單位的回合標題之後、動作之前），例如 `敵方指令：集火 法師`、`我方指令：戰士：守住 (0, 4) 半徑 1；弓手：…`、被忽略的指令印 `  （忽略：…，原因）`。與同陣營上一次相同的指令不重印（紀錄仍保留每一次）。指揮官只能搭配 `--ai utility`，否則 exit 2。
- `trpg sim maps … [--ally-commander id] [--enemy-commander id]`：只有指定時才在第一行後多印 `敵方指揮官：focus_lowest_hp（集火 HP 最低的可見敵人）`；沒指定時標準輸出與 2C-1 逐字相同。

## 5. 數據表

### 5.1 勝率對照（`trpg sim maps --seeds 20`，種子 0–19，max_rounds=30）

| 地圖 | 無指揮官：我方勝率／平均輪數 | 敵方 `focus_lowest_hp`：我方勝率／平均輪數 |
|---|---|---|
| bridge_chasm | 75.0%（15/20）／4.20 | 90.0%（18/20）／4.30 |
| oil_depot | 45.0%（9/20）／4.75 | 35.0%（7/20）／5.35 |
| ruined_fort | 85.0%（17/20）／4.35 | 75.0%（15/20）／5.00 |
| swamp | 85.0%（17/20）／4.20 | 65.0%（13/20）／4.40 |

（只列出，未調整。bridge_chasm 反而對我方有利：敵人集火後被「追人」帶離了原本有利的位置，原因沒有分析。20 場的抽樣誤差約 ±10 個百分點，單一地圖的差異不要過度解讀。兩次都沒有 `exception`／`max_actions` 異常；執行時間 `--jobs 4`：無指揮官 60.9 秒、敵方集火 68.0 秒，舊版（2C-1）49.0 秒，機器上同時有別的行程，單緒 A/B 交錯量測差距約 2%。）

### 5.2 效能（`scripts/bench_battle.py --decision-repeat 15`）

同一批決策狀態（取自一場無指令的戰鬥），交錯計時，單次 `ai(state)` 的中位數，括號為相對無指令：

| 地圖（決策數） | 無指令 | 集火 | 守位 | 撤退 | 保護 | 利用環境 | 四種合併* |
|---|---|---|---|---|---|---|---|
| bridge_chasm（49） | 6777 µs | +4.9% | +1.0% | −4.0% | +5.7% | +0.1% | +8.8% |
| oil_depot（93） | 5600 µs | +0.1% | −9.4% | −2.5% | +3.9% | −4.6% | +4.4% |
| swamp（8） | 5587 µs | −0.6% | −3.5% | −4.3% | −2.6% | −2.1% | +7.1% |
| ruined_fort（69） | 7428 µs | +5.7% | −4.1% | −6.1% | +2.0% | −2.8% | +7.0% |

\* 集火＋守位＋保護＋利用環境同時下（刻意最重的組合）。負值是因為指令改變了選擇的動作；各項皆 ≤ 10%（驗收標準）。
無指令路徑的全場時間與 2C-1 相同（同一台機器交錯 A/B：13.7／13.3 秒 vs 14.1／13.6 秒，16 場）。

## 6. 待 PM 決定

1. **`use_environment` 只對有環境權重的行為模式有效**：加成是對 `env_damage`、`env_kill`、`push`、`surface`、`expose` 收益的 ×2000‰，而 `brute`／`archer`／`guard` 這五個權重全為 0（只有 `cunning` 有），所以對它們沒有任何效果（`sim maps` 的 `swamp` 對敵方下 `use_env`，結果與無指令完全相同）。照規格實作。是否要讓指令同時提高這些行為模式的環境權重（例如給下限）？留給 2C-4。
2. **集火加成的實作**：規格寫「對目標的預覽收益 ×1500‰」，我用「只計對目標的 `_gains`」再乘 0.5 加上去（見 4.3 的範圍）。治療、友軍誤傷、防禦不在內。若 PM 想把整個動作分數乘 1.5，是一行的改動。
3. **指揮官看到的單位數沒有視野過濾**：呼叫時機的「看到的存活單位數」目前是全場（視野過濾是 Phase 3/4）。同一輪內有單位倒下就會再呼叫（`swamp` 的連鎖閃電一輪內可能呼叫數次）；CLI 只印出與上次不同的指令，`BattleLog.orders` 保留每次下達。
4. **`hold_start` 的起始格**是「第一次看到該單位時的位置」（第 1 輪該陣營第一次決策前，位置就是出生點）；單位倒下後它的條目從 `OrderSet` 消失，所以 `hold_start` 在有人倒下時會印出新的指令列。
5. **`validate_order` 不知道「誰」在執行**，所以「保護自己」不算無效、也不會記入 `ignored`；到評分時才視為無效（等同沒有該指令）。`OrderSet.unit_orders` 指向不存在的單位會記入 `ignored`（原因「單位 … 不存在」）。
6. **`LOG_FORMAT` 沒有升版**（維持 `/6`）：新增的 `orders` 欄位有預設值，舊紀錄與新引擎相容。若 PM 希望格式字串標示有指令欄位，需要升版並處理舊紀錄。
7. **一個 `UtilityAI` 只能接一個 `CommandedAI`**：`CommandedAI` 建構時把 `ai.orders` 設成自己的來源（會覆寫原有的）。批次模擬每場新建，沒有問題；Phase 3 的 LLM 指揮官若要共用同一個 AI，要另外考慮。
8. **指令的初值效果**（5.1）：敵方集火對我方勝率的影響方向不一致，且不是單調的「更強」。初值未經模擬，2C-4 調整 `orders:` 與指揮官邏輯（例如 `focus_lowest_hp` 是否該排除打不到的目標）。
9. **報表沒有指令統計**：`BattleOutcome`／`BattleMetrics` 沒有帶 `order_log`（指令只在 `BattleRun.orders`／`BattleLog`）。2C-4 若要分析「指令下達次數／被忽略次數」需要擴充。
10. **效能的 10% 標準**以單一指令類型滿足；「四種合併」在個別地圖上為 +4%～+9%（本次量測），重跑可能略高於 10%（量測噪音約 ±5%）。

## 7. 給下一個子階段的備註

- 2C-3 與本階段的潛在合併衝突：`src/trpg/cli/main.py`（`build_parser`、`_sim_maps`，另有 `_add_commander_args`）、`src/trpg/cli/sim.py`（`cmd_sim_maps` 多兩個關鍵字參數、標頭多印指揮官行）、`src/trpg/sim/batch.py`（`map_spec` 多兩個關鍵字參數與一行 import）、`src/trpg/cli/battle.py`、`scripts/bench_battle.py`。`trpg sim matrix` 若要支援指揮官，可直接用 `CommandedPolicyFactory`。
- 矩陣的 `BatchSpec.policy_factory` 預設仍是 `UtilityPolicyFactory`；要加指揮官時換成 `CommandedPolicyFactory(profiles, ally, enemy)` 即可（可 pickle）。
- 2C-4 的 `orders:` 區塊在 `content/ai_profiles.yaml`（`OrderBonuses` schema，`content check` 已涵蓋）；調整任何值都不影響沒有指令時的分數。

## 8. 附錄：代表性的 CLI 輸出節錄

`trpg battle --map oil_depot --seed 2 --ally-commander hold_start --enemy-commander focus_lowest_hp`（節錄）：

```
— 盜賊弓手 的回合（AP 3，移動 5，法力 9/9）
敵方指令：集火 法師
  盜賊弓手 攻擊 法師：d20=13 修正 +0 熟練 +2 半掩護 -2 = 13（目標 11）→ 命中［命中 −2：矮牆掩護］
    法師 受到 11 點物理傷害［骰 7］，HP 40 → 29
  盜賊弓手 攻擊 法師：d20=18 修正 +0 熟練 +2 半掩護 -2 = 18（目標 11）→ 命中［命中 −2：矮牆掩護］
    法師 受到 10 點物理傷害［骰 6］，HP 29 → 19
  盜賊弓手 攻擊 法師：d20=8 修正 +0 熟練 +2 半掩護 -2 = 8（目標 11）→ 失手［命中 −2：矮牆掩護］
  盜賊弓手 從 (7, 4) 移動到 (4, 2)（消耗 5 移動）
  盜賊弓手 結束回合
— 戰士 的回合（AP 3，移動 5，法力 20/20）
我方指令：戰士：守住 (0, 4) 半徑 1；弓手：守住 (0, 5) 半徑 1；法師：守住 (1, 3) 半徑 1
  戰士 從 (0, 4) 移動到 (0, 3)（消耗 1 移動）
  戰士 獲得狀態「防禦」
  戰士 結束回合，保留 1 AP
```

全場的指令行（`grep 指令`）：

```
敵方指令：集火 法師            （第 1 輪）
我方指令：戰士：守住 (0, 4) 半徑 1；弓手：守住 (0, 5) 半徑 1；法師：守住 (1, 3) 半徑 1
敵方指令：集火 弓手            （第 2 輪）
我方指令：戰士：守住 (0, 4) 半徑 1；弓手：守住 (0, 5) 半徑 1
敵方指令：集火 戰士            （第 4 輪）
我方指令：戰士：守住 (0, 4) 半徑 1   （第 5 輪）
勝方：敵方勝利（第 6 輪結束，109 個動作，406 個事件）
```

`trpg battle replay b.json`：

```
重播驗證通過：109 個動作、406 個事件，最終狀態一致（oil_depot，種子 2）。
```

`trpg sim maps --maps oil_depot --seeds 3 --enemy-commander use_env` 的前兩行：

```
批次模擬：效用 AI，種子 0–2（3 場／地圖），max_rounds=30
敵方指揮官：use_env（全隊優先利用環境）
```
