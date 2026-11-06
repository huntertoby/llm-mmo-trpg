# Phase 2H-1 報告：冰凍與自身狀態代價

## 1. Commit 列表

- `Add frozen status, data-driven thaw on fire damage and ice-freezes-unit-in-water interaction`（3.1、3.2：`frozen` 狀態、`removed_by_element`、`apply_status` 互動結果與 `unit_surface` 條件、`skill_deep_freeze`、`LOG_FORMAT` 升為 `/11`）
- `Add self_status skill cost with budget allowance, composer, AI cost and two demo skills`（3.3、3.4：`cost.self_status`、預算折抵、驗證、組合器、AI 成本、CLI 顯示、`skill_reckless_lunge`）
- 本報告 commit

## 2. 驗收逐條結果

1. 通過。測試名稱：
   - 3.1 `tests/engine/test_frozen.py`：`test_frozen_skips_the_turn_and_expires`（跳過回合）、`test_fire_damage_thaws_the_unit_with_an_event`（火傷解除，事件 `status_removed` 原因 `thawed`）、`test_non_fire_damage_does_not_thaw`（物理、冰、雷不解除）、`test_frozen_on_a_boss_becomes_slow`（Boss 轉緩速）、`test_frozen_shares_hard_control_diminishing_returns_with_stun`（與暈眩同組遞減）；內容側 `tests/content/test_statuses_content.py`（`frozen` 的欄位表、`boss_control_conversion`）。
   - 3.2 同檔：`test_ice_damage_freezes_a_unit_standing_in_water_and_the_water_freezes_too`、`test_ice_touch_on_a_tile_freezes_the_unit_in_water`、`test_ice_damage_does_not_freeze_a_unit_on_dry_ground`、`test_non_ice_damage_does_not_freeze_a_unit_in_water`、`test_ice_on_a_boss_in_water_becomes_slow`；schema 與跨檔案參照：`tests/content/test_environment_content.py::test_interaction_apply_status_outcome_and_unit_surface_validation`。
   - 3.3 見驗收 3。
   - `grep -rnw frozen src/`（排除 `frozen=True`、`frozen_lake`）只剩 `src/trpg/sim/metrics.py:82` 的 `CONTROL_STATUSES = ("stun", "frozen", "root", "slow")`（模擬報表的欄位清單；規格 3.1 明文要求把 `frozen` 納入 `CONTROL_STATUSES`）。引擎與內容載入沒有任何寫死 `frozen`；`turns.py` 的 `skip_turn_if_stunned` 本來就以 `skip_turn` 欄位判斷，不需要改。
2. 通過。`test_ice_damage_freezes_a_unit_standing_in_water_and_the_water_freezes_too`：同一次冰傷後該格變 `ice`，單位同時帶 `frozen`（事件 `status_applied` 持續 1、來源為施放者）；`test_unit_surface_positions_are_pre_touch` 證明水已變冰後再次冰傷不會再凍。實作方式：`matching_rules` 對 surface／object／unit 三類一次選好規則（此時表面還沒變），再產生後續效果。
3. 通過。`tests/engine/test_self_status.py`：結算 `test_casting_gives_the_caster_the_status_without_a_save`、`test_the_status_counts_down_at_the_end_of_the_casting_turn`、`test_the_status_is_applied_after_the_cast_so_weaken_does_not_hit_its_own_damage`、`test_a_skill_without_self_status_leaves_the_caster_clean`；預算折抵（含自身上限與總上限）`test_the_allowance_is_points_times_effective_turns_with_its_own_cap`（5 組）、`test_the_self_status_allowance_is_truncated_by_the_total_cap`、`test_budget_rules_come_from_skill_budget_yaml`；拒絕 `test_duration_must_be_two_or_three`（0、1、4）、`test_only_active_skills_may_use_self_status`（被動／反應／姿態）、`test_a_status_outside_the_allowed_list_is_rejected_by_the_validator`、`test_an_unknown_status_is_a_reference_error`；AI `test_the_ai_charges_the_self_status_as_a_cost`；組合器 `tests/skillgen/test_random_composer.py::test_the_composer_sometimes_adds_a_valid_self_status_cost_to_active_skills`。`uv run python scripts/skill_fuzz.py --count 1000`：組合成功 1000/1000、通過驗證 1000/1000、可施放 1000/1000、**例外 0 個**。
4. 通過。`skill_deep_freeze` 97.9%、`skill_reckless_lunge` 85.1%（`trpg skills budget`，驗證通過）；皆已裝備；`tests/content/test_coverage.py` 全數通過，新增 `test_self_status_cost_is_used_by_a_handwritten_skill`（`self_status` 至少一個手寫技能使用，且 `frozen` 被手寫技能施加）。
5. 通過。`trpg battle --map frozen_lake --seed 5 --ally-build build_storm,build_assassin --log-json f` → `trpg battle replay f`：「重播驗證通過：96 個動作、378 個事件，最終狀態一致」；`test_flat_6x6` 種子 4 亦通過。節錄見第 8 節。
6. 通過。`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（1463 passed）全部通過。複雜度類 noqa 前後皆為 14 個（`git grep` 計數），本階段沒有新增。

## 3. 新增的資料欄位與初值（皆為初值，未經模擬）

| 檔案 | 欄位 | 初值 |
|---|---|---|
| `statuses.yaml` | 新狀態 `frozen`（冰凍） | `duration: 1`、`expires: turn_end`、`skip_turn`、`control_group: hard`、`save_attr: con`、`min_rarity: rare`、`budget_points: 8` |
| `statuses.yaml`／`StatusDef` | `removed_by_element`（元素清單） | `frozen: [fire]`，其餘空 |
| `rules/core.yaml` | `boss_control_conversion` | `{stun: slow, frozen: slow}` |
| `ai_profiles.yaml` | `status_values.frozen` | 12（同 `stun`） |
| `interactions.yaml`／`InteractionOutcome` | 新 op `apply_status`，欄位 `status`、`duration` | `ice_freezes_unit_in_water`：`status: frozen`、`duration: 1` |
| `interactions.yaml`／`InteractionRule` | `unit_surface`（只能搭配 `target: unit`，用觸及前的表面） | `ice_freezes_unit_in_water`：`water` |
| `skill_budget.yaml` | `allowance.self_status` | `allowed: [vulnerable, weaken, slow, root]`、`per_point_permille: 40`、`cap: 250` |
| `SkillCost` | `self_status: {status, duration}`（`duration` 2–3） | 手寫：`vulnerable` 2 回合 |
| `skill_composer.yaml` | `cost.self_status_permille`、`cost.self_status_duration` | 60、`{min: 2, max: 3}` |
| `skill_exclusions.yaml` | `stun_single_long_cooldown` 的 `when.statuses` | `[stun, frozen]` |
| `runner.py` | `LOG_FORMAT` | `trpg-battle-log/11`（`status_removed` 新原因 `thawed`、規則包新欄位；`/10` 的紀錄無法由新版重播） |

## 4. 新技能

| ID | 中文名 | 預算比例 | 裝備於 | 說明 |
|---|---|---|---|---|
| `skill_deep_freeze` | 凍結 | 97.9% | build_storm（第 6 個主動） | 單體 5 格，2d6 冰傷＋冰凍 1 回合＋易傷 2 回合，AP 2、法力 8、冷卻 4（`control` 骨架要求傷害占比 ≤ 40%，所以多帶易傷） |
| `skill_reckless_lunge` | 捨身突刺 | 85.1% | build_assassin（第 6 個主動） | 近戰武器技，傷害 ×2.8，AP 2、法力 4、冷卻 2，`self_status: vulnerable` 2 回合 |

## 5. 修改過期望值的測試與原因

- `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py`：`LOG_FORMAT` 由 `/10` 改 `/11`。
- `tests/cli/test_budget_cli.py`：手寫技能數 59 → 61。
- `tests/content/test_statuses_content.py`：`boss_control_conversion` 期望值加 `frozen: slow`；欄位表新增 `frozen`。
- `tests/engine/test_status_ai.py`：`status_values` 鍵集合加 `frozen`。
- `tests/skillgen/test_budget.py`：狀態點數表加 `frozen: 8`。
- `tests/sim/test_batch.py`：控制欄位多一欄 `frozen`。
- `tests/content/test_skills_content.py`、`tests/content/test_environment_content.py`：這兩個測試原本拿 `frozen` 當「不存在的狀態」，現在 `frozen` 存在，改用 `petrified`。

## 6. 複雜度類 noqa

前後皆 14 個，本階段新增 0 個。

## 7. 待 PM 決定

1. **自身狀態的施加時機**：規格寫「支付代價時」，我改為「整個技能結算完之後」（`interpreter._apply_self_status`）。原因：技能傷害的 `cause` 是 `attack`，若在支付時施加，`weaken` 會削弱這次施放自己的傷害（有測試鎖定）；`vulnerable` 對這次施放期間的反擊也不會提前生效。倒下的施放者不會被施加。若要改回支付當下，只需移動一行呼叫。
2. **模擬報表的控制統計**：`CONTROL_STATUSES` 加入 `frozen`（規格要求），所以 `grep -rnw frozen src/` 有一行非註解結果；若要完全由資料推導，需要把規則集傳入 `metrics_from_events`／`BatchReport`，改動較大，沒有做。另外自己施加給自己的狀態（`source == 單位自己`）不計入控制回合，避免自身狀態代價灌水「己方控制」。
3. **冰凍解除的門檻**：「受到該元素傷害（數值 > 0）」用 `DamageDealt.amount > 0`（護盾吸收前的數值），所以被護盾完全吸收的火傷仍會解凍。
4. **單位類互動規則在傷害事件也生效**：`damage_dealt` 的互動觸發原本只看表面與物件，為了讓冰傷打中水上單位能凍住，改為三類都看。現有的 `wind_pushes_unit` 需要方向與距離，傷害事件沒有，不會誤觸發；日後新增 `target: unit` 的規則會在所有元素傷害命中時生效，撰寫時要留意。
5. **冰凍的組合器限制**：沿用暈眩的限制，改成以 `control_group: hard` 判斷（單體形狀、冷卻至少 4），`skill_exclusions.yaml` 的規則 `when.statuses` 同時列 `stun`、`frozen`。
6. **環境冰凍與 Boss**：環境互動施加的 `frozen` 走同一個 `apply_status`，Boss 照常轉成緩速（有測試）；環境狀態不擲抵抗，但也會觸發控制遞減（類別 hard），與技能路徑一致。
7. **凍結的易傷**：為了讓 `control` 骨架的傷害占比合格而加；若 PM 想讓冰凍技更純粹，可改成 `slow` 或降階級。
8. **組合器抽樣順序**：自身狀態代價的抽籤放在 `build_cost` 的最後，同一個隨機種子產生的技能內容可能與 2G 不同（只影響隨機組合器的輸出，不影響手寫技能與既有測試）。
9. **AI 成本**：自身狀態以 `damage 權重 × status_values[狀態] × (duration − 1)` 計入技能成本（`skill_cost` 多一個選用參數 `status_values`），沒列在 `status_values` 的狀態用 `status` 權重。數值未經模擬。
10. **預覽**：沒有額外標示自身狀態代價，但因為效果走正常結算，預覽的最小／最大狀態自然包含它；CLI 的技能說明（`trpg skills show`、`list`）已顯示「施放後自身易傷 2 回合」。

## 8. 代表性 CLI 輸出節錄

`uv run trpg battle --map frozen_lake --seed 5 --ally-build build_storm,build_assassin`：

```
— 雷電流英雄 的回合（AP 3，移動 5，法力 20/40）
  雷電流英雄 施放「凍結」（AP 2，法力 8，冷卻 4 回合）→ 影響 1 格
  雷電流英雄 以「凍結」攻擊 盜賊弓手：d20=10 修正 +0 熟練 +2 = 12（目標 11）→ 命中
    盜賊弓手 受到 11 點冰霜傷害［骰 1+2］，HP 26 → 15
  雷電流英雄 對 盜賊弓手 施加「冰凍」（智力 16 vs 體質 10）：d20=6 修正 +3 熟練 +2 = 11（目標 11）→ 施加成功
  盜賊弓手 獲得狀態「冰凍」（1 回合）
  雷電流英雄 對 盜賊弓手 施加「易傷」（智力 16 vs 意志 8）：d20=2 修正 +4 熟練 +2 = 8（目標 11）→ 被抵抗
— 盜賊弓手 的回合（AP 3，移動 5，法力 9/9）
  盜賊弓手 受到「冰凍」影響，跳過這個回合
  盜賊弓手 的「冰凍」結束了
...
  刺殺英雄 施放「捨身突刺」（AP 2，法力 4，冷卻 2 回合）→ 影響 1 格
  刺殺英雄 以「捨身突刺」攻擊 盜賊2：d20（優勢 2、8）=8 修正 +0 熟練 +2 = 10（目標 11）→ 失手
  刺殺英雄 獲得狀態「易傷」（2 回合）
```

`uv run trpg battle replay f`：`重播驗證通過：96 個動作、378 個事件，最終狀態一致（frozen_lake，種子 5）。`

`uv run trpg skills show skill_reckless_lunge`：`代價 AP 2，法力 4，施放後自身易傷 2 回合，冷卻 2 回合`。
