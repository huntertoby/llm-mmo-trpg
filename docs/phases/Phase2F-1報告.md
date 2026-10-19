# Phase 2F-1 報告：引擎重複邏輯

## 1. commit 列表

| commit | 說明 |
|---|---|
| `6c43476` | 3.1／3.2：`_usable` 改用 `targeting.resource_problem`；新增共用的 `pay_skill_cost`／`PaidCost`；`stack_problem` 改用 `stacks.required_stack`；陷阱形狀展開改用公開的 `center_tiles`；`TrapSpec.shape` 改為載入時驗證形狀 ID |
| `bd6f4d4` | 3.1／3.4：新增共用的 `check_trigger_depth`（`reactions.py`、`traps.py` 改用它）；`TrapTriggered` 新增 `tiles` 欄位；`remove_traps_of` 回傳事件，`down_unit`／`escape_unit` 併入回傳值 |
| `a4d1828` | 3.5：`TrapState.attributes` 改為不可變 tuple |
| `d48844d` | 3.3：`_do_move` 的中斷條件改為通用的 `_move_interrupted`（位置偏離預期格、定身、暈眩、倒地、死亡、逃離） |
| `9fa5c34` | 測試：`TrapSpec.shape` 未知 ID 載入時報錯；`down_unit` 的 `TrapExpired` 回傳值不重複 |

（另外 step 0 的 `4789414 Add Phase 2F spec` 已依你的指示由你自己 push；上面 5 筆實作 commit 未 push。）

## 2. 驗收逐條結果（`docs/phases/Phase2F計畫.md` 3.6）

1. **`_usable` 不再自行檢查沉默／法力／冷卻／每場次數／HP／層數** ✅
   `src/trpg/engine/skill_triggers.py` 的 `_usable` 現在只檢查被動專屬條件（存活、`skip_turn_status`、`max_per_round`），其餘全部交給 `targeting.resource_problem`。既有測試「被沉默的被動不觸發」等持續通過：`uv run pytest -q tests/engine/test_passive_triggers.py` → 全過。

2. **代價支付只有一個實作；觸發深度檢查只有一個實作** ✅
   - `grep -rn "cooldowns\[.*\] = " src/trpg/engine` 只在 `targeting.pay_skill_cost` 一處（`turns.py` 的是回合開始的冷卻倒數，不是支付代價，性質不同）。
   - `grep -rn "TriggerLimitReached" src/` 只在 `engine/events.py`（事件定義／型別聯集）、`skill_triggers.check_trigger_depth`（唯一的 `ctx.emit(TriggerLimitReached, ...)`）與讀取端（`cli/render.py`、`sim/metrics.py`）出現；`reactions._skill_usable`、`traps._trigger` 都改成呼叫 `check_trigger_depth`，不再各自 `ctx.emit`。

3. **陷阱形狀展開只有一個實作；`TrapSpec.shape` 使用不存在的 ID 會在載入時報錯** ✅
   `interpreter.use_trap_skill`、`ai/utility._trap_estimate`、`targeting.compute_area` 三處都改成呼叫 `targeting.center_tiles`。
   測試：`tests/content/test_skills_content.py::test_unknown_trap_shape_rejected_at_load`（新增）。

4. **陷阱推擊中斷移動的新測試通過** ✅（細節見下方「待 PM 決定」第 1 點）
   `tests/engine/test_movement.py` 新增 4 個測試，直接驗證 `_move_interrupted`（新的通用條件）：正常抵達不中斷、被推離預期格中斷、定身／暈眩中斷、死亡中斷。
   `uv run pytest -q tests/engine/test_movement.py` → 19 passed。

5. **`TrapTriggered.tiles` 有值；倒下時移除陷阱的 `TrapExpired` 出現在 `down_unit` 回傳值中且不重複** ✅
   `tests/engine/test_traps.py::test_down_unit_returns_the_trap_expired_event_without_duplicating_it`（新增）：直接呼叫 `down_unit`，確認回傳值裡有且只有一筆 `TrapExpired`，與 `ctx.events` 裡的是同一個物件（不是多發一次）。既有測試 `test_an_enemy_stepping_on_an_enter_trap_triggers_it` 等也確認 `TrapTriggered` 帶有 `tiles`。

6. **3 場對照戰鬥 JSON 與開工前相同（若因 3.4 新欄位而不同，只能差在新欄位）** ✅
   見第 3 節。

7. **`scripts/check.py` 全部通過；複雜度類 noqa 數量不增加** ✅
   見第 5 節（`uv run python scripts/check.py` 的 ruff／ruff format／mypy／import-linter 全過；pytest 因本機單次呼叫有 180 秒上限，分成幾批跑完同一份預設測試集，全部通過，見下）。

## 3. 對照戰鬥比對結果

開工前（HEAD＝`2400d3b`）與完成後各跑一次，存到暫存目錄比對：

```bash
uv run trpg battle --map ruined_fort  --seed 1 --ally-build build_trapper,build_guardian --log-json battle1.json
uv run trpg battle --map open_plain   --seed 2                                            --log-json battle2.json
uv run trpg battle --map dark_forest  --seed 3 --ally-build build_warlock,build_healer    --log-json battle3.json
```

比對結果（`diff <(python3 -m json.tool before.json) <(python3 -m json.tool after.json)`）：

- **battle2（open_plain，無陷阱 build）**：完全相同。
- **battle3（dark_forest，warlock/healer）**：完全相同。
- **battle1（ruined_fort，trapper/guardian，有陷阱）**：只有一處差異——第 87 個事件（`TrapTriggered`）多了 3.4 新增的 `tiles` 欄位（`[{"x": 4, "y": 4}]`），其餘全部相同。這正是規格允許的「新欄位有預設值、可向下相容讀取」情況，不須升版 `LOG_FORMAT`。

另外用 `trpg battle replay` 交叉驗證：`battle2_before.json`／`battle3_before.json` 重播後與重新跑的結果仍一致；`battle1_before.json`（開工前錄的舊紀錄，沒有 `tiles` 欄位）可以正常讀取（沒有因缺少新欄位而壞掉），只在新增 `tiles` 的那個事件上與用新程式碼重新結算的結果不同——這就是上面講的唯一差異，不是迴歸。

## 4. 修改過期望值的測試與原因

無。所有既有測試的期望值都沒有改動（如規格預期：2F-1 理論上應為 0 個）。

## 5. 複雜度類 noqa 數量

| | 數量 |
|---|---|
| Phase 2F 開始前（`2400d3b`） | 19 |
| 目前（本階段結束） | 17 |

減少的兩處：`skill_triggers._usable`（`PLR0911`）與 `reactions._skill_usable`（`PLR0911`）——拆掉重複檢查後分支變少，ruff 自動判定不再需要 `# noqa`，直接移除（不是新增，故不需逐一說明理由）。本階段沒有新增任何 noqa。

## 6. 待 PM 決定

1. **驗收 #4 的「陷阱推擊」測試改用直接測試 `_move_interrupted`，而非真的組一個會推開踩中它的單位的陷阱技能**：引擎的推擊效果（`push`／`pull`）方向是以範圍技能的原點（中心格型即中心格）往外算（`interpreter._displace_direction`）。`enter` 陷阱觸發時，踩中它的單位必定剛好站在陷阱格——也就是推擊的原點本身，位移向量恒為 `(0, 0)`，推擊原語不會對它產生任何效果（`_axis_direction` 對零向量回傳 `None`，直接跳過）。這是既有、刻意的設計（以中心為準的範圍技能不能把站在中心上的目標推開自己），不是這次要修的 bug。也確認過：合法的 `Move` 不可能走進致命地形（`plan_move`／`is_standable` 一開始就不允許規劃這種路徑步），所以也沒有別的合法途徑能讓一個陷阱推開「踩中它」的單位本身。目前的做法是直接測試 `_do_move` 抽出的 `_move_interrupted` 這段通用條件（覆蓋「被推離預期格」「定身」「暈眩」「死亡」四種中斷原因），細節與推理寫在 `tests/engine/test_movement.py` 新增測試的註解裡。是否要新增一個不以中心為原點的陷阱推擊效果（例如把目標往陷阱放置者的方向推），讓這個場景在未來真的能用合法技能組合測到，留給你決定；目前我認為不需要，`_move_interrupted` 本身已經測到了。
2. 其餘規格內的項目都沒有遇到需要自行決定、或與 `docs/專案計畫.md` 衝突的地方。

