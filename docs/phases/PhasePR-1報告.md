# Phase PR-1 完成報告｜#147 靶場測試模式：引擎

> 規格：`docs/phases/PhasePR-1計畫.md`；來源：`docs/design/21-探索地圖與城鎮.md` 21.5 測試模式 6 點。基準 commit `4b7d44f8`。

## 1. 做了什麼

- 新模組 `src/trpg/engine/practice.py`：`PracticeRules`（`target_tag`，預設 `training_dummy`）、`PASS_ROUND_ACTIONS`（`attack`、`use_skill`、`use_race_skill`）、`is_practice_target`、`is_practice_hero`、`hold_standing`。
- `BattleSetup.practice`，`begin_battle` 抄進 `BattleState.practice`；`BattleState.practice_homes` 記木樁開場位置，`clone` 都列了。**不放 `Ruleset`，規則包雜湊不變。**
- `turns.py`：`finish_resolution` 非預覽時清冷卻與次數、補資源（`_refill_practice_heroes`）；`practice_pass_round` 自動過輪；`_end_round` 補滿打到底的木樁。
- 必中與對抗必成：`rules/combat.py::roll_attack`、`reactions.py`（預覽強制值）、`control.py`、`maneuvers.py`、`preview.py`（`_chances(always=)`、`status_save_chance`、`contest_chance`）。
- 不倒下：`effects/handlers.py` 三處；致命地形：`triggers.py::_deadly_terrain`。
- `LOG_FORMAT` → `trpg-battle-log/113`，`docs/phases/戰鬥紀錄格式變更.md` 加一條，測試字面值 12 處更新。

## 2. 與規格不同的一點

規格第 3 項寫「`finish_resolution` 非預覽時 `end_turn`＋`advance_turn`」。實際放在 `resolve_with` 的 `try` 內、handler 之後（`practice_pass_round`）。原因：換手時的 `start_turn` 可能結算灌注技能、反應等而 `PauseForDecision`，`finish_resolution` 在 `try` 外，暫停會變成未處理的例外。放在 `try` 內，恢復時整個動作重跑，符合「`PauseForDecision` 恢復後才做」。資源補滿仍在 `finish_resolution`。

## 3. 逐條驗收

| 條件 | 證據 |
|---|---|
| 沒 CD | `test_cooldown_is_cleared_after_cast` |
| 次數不算（技能、種族技） | `test_uses_per_battle_are_not_counted`、`test_race_skill_uses_are_not_counted` |
| 資源補滿（AP、移動、耐力、法力、HP、源力、形態冷卻、彈藥） | `test_every_resource_is_full_after_an_action`、`test_ammo_is_refilled`、`test_run_can_be_repeated_and_keeps_its_bonus` |
| 放招、普攻、種族技過輪 | `test_casts_and_attacks_pass_the_round[attack/skill/race_skill]`、`test_attacking_only_air_still_counts_by_action_kind` |
| 走路、跑步、推撞、絆摔不過輪 | `test_basic_actions_do_not_pass_the_round[move/run/shove/trip]` |
| 暫停恢復後才過輪 | `test_auto_pass_waits_for_the_paused_decision` |
| 預覽不過輪、不補資源 | `test_preview_does_not_pass_or_refill` |
| 木樁必中、仍擲 d20、暴擊照規則 | `test_natural_one_still_hits_the_dummy_and_cannot_crit`、`test_natural_twenty_on_the_dummy_is_a_crit` |
| 亂數取用次數不變 | `test_practice_keeps_rng_consumption_of_a_landed_attack` |
| 只對木樁標籤生效 | `test_only_tagged_targets_are_always_hit_in_practice` |
| 狀態與推撞、絆摔必成 | `test_status_save_on_the_dummy_always_succeeds`、`test_shove_and_trip_contests_always_succeed` |
| 預覽 100% | `test_preview_shows_full_chance_against_the_dummy` |
| 主角、木樁不倒下；一般敵人照倒 | `test_hero_never_goes_down`、`test_dummy_stays_at_one_then_refills_next_round`、`test_ordinary_enemy_still_goes_down_in_practice` |
| 木樁下一輪補滿 | `test_dummy_stays_at_one_then_refills_next_round` |
| 木樁進致命地形回開場位置並補滿；其他被推走不歸位 | `test_dummy_pushed_into_deadly_terrain_returns_home_full`、`test_shove_and_trip_contests_always_succeed` |
| 技能工坊（沒旗標）不受影響 | `test_no_flag_means_no_practice_rules`、`test_workshop_dummy_without_flag_can_go_down`、`test_no_flag_cooldown_is_kept` |
| `--log-json` 重播一致 | `test_practice_battle_log_replays_identically`（`BattleLog` JSON 來回、`replay`、`trpg battle replay` 的 `cmd_replay` 回傳 0） |
| `clone`、版號 | `tests/engine/test_state_clone.py`、`tests/engine/test_ruleset_hash.py` |
| 實戰不變 | 見第 5 節 |
| `ruff check`、`ruff format --check`、`mypy`、`lint-imports` | 全過（14 contracts kept）；**沒有新增複雜度 noqa** |
| 指定目錄測試、CLI 快照 | 見第 6 節 |

## 4. `down_unit` 掃描

全 `src/trpg` 只有 3 個呼叫點，全部在 `effects/handlers.py`。三處都在判斷 `hp <= 0` 前先呼叫 `hold_standing`（免死之後），所以事件的 `hp_after` 是 1：

| 呼叫點 | 路徑 | 處理 |
|---|---|---|
| `_damage`（`register_effect("damage")`） | 一般傷害（含 `lethal`、墜落、致命地形） | `hold_standing(unit)`，也因此不會給精英擊殺獎勵 |
| `_share` | 分傷給同門 | `hold_standing(kin)` |
| `_redirect` | 靈魂連結轉移 | `hold_standing(linked)` |

其他會改 HP 的路徑都不會倒下：`gear/core.py`（最低剩 1）、`skills/targeting.py::pay_skill_cost`（代價，下次收尾補滿，不呼叫 `down_unit`）、`forms.py`（只夾上限）、`_mend_ally` 與 `heal`（加血）。`unit.downed = True` 全專案只在 `down_unit` 內；`revive` 不相關。

## 5. 實戰不變的比對

- 腳本：`.scratch_pr1/dump_events.py`（未 commit）。在改動前的 `4b7d44f8` 產生 `before.json`，改完產生 `after.json`，`.scratch_pr1/compare.py` 整份比對。
- 範圍：8 張地圖（`open_plain`、`bandit_lair`、`bridge_chasm`、`frozen_lake`、`lava_crossing`、`swamp`、`ruined_fort`、`oil_depot`）× 2 個種子 ＝ 16 場，3 對 3 的預設陣容。
- 比對內容：完整事件 JSON、步驟列表、輪數、勝方、最終 `rng_state`。
- 結果：`maps/seeds=16 events=2684 different=0`。`LOG_FORMAT` 字串不在事件內，所以不必排除。

## 6. 測試

- `uv run pytest -q tests/engine tests/sim tests/api tests/test_architecture.py tests/cli -n 8 -m "not llm"`：**5593 passed、1 skipped、4 xfailed**，退出碼 0。skipped 與 xfailed 是既有項目（`test_owner_guard` 開發模式、`test_demo_balance` 平衡延後）。
- `TRPG_FULL=1 uv run pytest -q tests/cli -n 8 -m "not llm"`：**192 passed**，退出碼 0。`-m "not llm"` 蓋過 `addopts` 的 slow 排除，所以含 slow 測試。
- `tests/cli/test_output_snapshots.py` 單獨再跑一次：**25 passed**。快照檔沒有重產、`git diff` 無變動：這些快照比對的輸出不受 `/113` 影響，規格「只有 `LOG_FORMAT` 字串應該變」這條實際上連字串都沒變。
- `tests/engine/test_practice_mode.py`：31 個測試全過。
- 依守則 11，沒有跑 `scripts/check.py` 與大型模擬。

## 7. 給 PR-2 的介面

- 開場：`BattleSetup(..., practice=PracticeRules(), max_rounds=None)`，`trpg.engine.practice.PracticeRules`。標籤可不給（預設 `training_dummy`）；PR-2 若要由 `newcomer.yaml` 帶值，傳 `PracticeRules(target_tag=...)`。
- 畫面判斷：`state.practice is not None`（`BattleView.practice` 由 PR-2 加）。
- 引擎會自己過輪，**步驟列表不多出 `EndTurn`**：放招或普攻的結果事件裡已有 `turn_ended` 與下一位的 `turn_started`，`BattleSession` 既有的 `advance` 接著跑木樁 AI 即可。`EndTurn` 動作仍合法（給木樁 AI 用），隱藏按鈕是前端的事。
- 資源補滿**不發事件**（只有冷卻歸零發 `skill_cooldown_changed`），畫面要讀結算後的狀態。木樁下一輪補滿、致命地形回位補滿的 HP 也不發事件（回位本身有 `unit_moved`）。
- 長時間沙盒的記憶體問題（`SessionStore`、`history()` 重播）見盤點第 3 節，PR-2 處理。
- `PendingResolution` 與 `state_to_json` 都帶 `practice`、`practice_homes`，暫停與重播不需額外處理。

## 8. 待 PM 決定

1. **AP 補到本回合上限 4（`ap_per_turn + ap_carry_max`）而不是 3**。補到 3 的話，要靠保留 AP 才放得出來的 4 AP 招在靶場永遠放不出來。
2. **其他會花 AP 的動作不過輪**：`infuse_skill`（灌注）、`activate_charge`（裝備充能）、`command_summon`（指揮召喚物）。21.5 與 PM 表只列放招、普攻、種族技，照最保守做。灌注算不算放招請定。
3. **主角被推進致命地形**：21.5 只定木樁，主角照「不倒下」留 1 HP、收尾補滿，**留在原地**不回位（可以自己走出來）。
4. **木樁下一輪補滿的判定是 `hp <= 1`**：剛好被打到 1 的也算，差一輪，不多存狀態。
5. **補血不發事件**（上面第 7 節）：若美術要「補滿」的飄字，PR-2 再加；用 `Healed` 會進戰鬥紀錄文字，所以先不發。
6. **跑步的移動點數只補不減**：連續跑步會累加（每次 +`run_move_bonus`），否則跑步等於沒效果。
7. **免死狀態先於不倒下**：主角或木樁身上有免死時照常消耗，方便試這類技能。
8. **木樁的開場位置被占用**時，回最近的空格（`nearest_free`：曼哈頓距離，同距離依 y、x）。
9. **未補的資源**：裝備充能、每輪反應次數（`reactions_used`）、每輪一次的指揮與灌注計數。21.5 未列，維持一般規則（反應與每輪計數在新一輪重設，裝備充能不補）。
