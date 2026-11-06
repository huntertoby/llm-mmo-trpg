# Phase 2E-1 報告：觸發核心 ＋ 被動

## 1. 摘要

- 新增 `content/skill_triggers.yaml`（9 個觸發時機）、`SkillDef.trigger`、`passive` 骨架（epic 以上）與 4 個手寫被動。
- 引擎新增「收集 → 延後結算」的觸發分派，依（事件順序、持有者 ID、技能 ID）排序，`max_trigger_depth: 3`，超過時發出 `TriggerLimitReached`。
- 預算用觸發係數（含 `max_per_round` 額外折扣），組合器能產生被動，fuzz 1000 個無例外（被動 49 個，38 個實際觸發）。
- `scripts/check.py` 五項全過（1230 測試）；重播一致；`LOG_FORMAT` 升為 `trpg-battle-log/8`。
- Phase 2 驗收 ⚠️ #1、#11 現在都滿足（見 3.6）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `71894bc` Add passive skill trigger core (Phase 2E-1) | 觸發資料檔與 schema、`SkillDef.trigger`、引擎觸發分派與深度上限、事件、預算、驗證、`passive` 骨架、4 個手寫被動、對應測試 |
| `02131fb` Add passive composer, fuzz coverage, sim metrics and renderer (Phase 2E-1) | 組合器產生被動、`skill_fuzz` 被動戰鬥與觸發計數、`UnitMetrics.triggers_fired`、`trigger_limit` 異常、`trpg sim skills` 欄位、繁中事件渲染、hypothesis 與重播測試 |
| （本報告的 commit） | `docs/phases/Phase2E-1報告.md` |

主要新增或修改的檔案：

- 內容：`content/skill_triggers.yaml`、`content/skeletons/passive.yaml`（啟用、`min_rarity: epic`）、`content/skills/skill_{ember_brand,second_wind,thorn_skin,mark_detonation}.yaml`、`content/rules/core.yaml`（`max_trigger_depth: 3`）、`content/skill_budget.yaml`（`passive_extra_trigger_permille: 800`）、`content/skill_composer.yaml`（`passive:` 區段）、`content/skill_exclusions.yaml`。
- 程式：`src/trpg/content/skill_triggers.py`、`src/trpg/engine/skill_triggers.py`（新）；`engine/{context,turns,battle,reactions,events,state,runner}.py`、`engine/effects/queue.py`、`engine/skills/interpreter.py`、`skillgen/{budget,validate,random_composer,composer_parts}.py`、`sim/{metrics,batch,skill_fuzz,skill_report}.py`、`cli/{render,budget}.py`。

## 3. 驗收結果（3.10 逐條）

### 3.1 `scripts/check.py` 五項全過

```
ruff check 通過 / ruff format --check 通過 / mypy 通過 / lint-imports 通過 / pytest 通過
1230 passed, 7 deselected in 348.43s
```

### 3.2 3.9 的測試全部存在且通過

| 3.9 項目 | 測試 |
|---|---|
| 1 每個時機各一 | `tests/engine/test_passive_triggers.py`：`test_on_hit_triggers_after_the_damage_and_targets_the_unit_that_was_hit`、`test_on_crit_only_triggers_on_a_critical_hit`、`test_on_natural_20_triggers_on_a_natural_20_but_not_on_a_19`、`test_on_kill_triggers_when_the_holders_damage_downs_a_unit`、`test_on_damaged_triggers_for_the_unit_that_was_hurt_and_targets_the_source`、`test_on_turn_start_triggers_after_the_turn_start_effects`、`test_on_turn_end_triggers_before_the_turn_ends`、`test_on_move_triggers_once_per_move_action_not_per_step_and_not_on_forced_moves`、`test_every_n_hits_triggers_on_the_second_and_fourth_hit_only` |
| 2 `max_per_round` | `test_max_per_round_limits_triggers_and_resets_each_round`、`test_max_per_round_two_allows_two_triggers` |
| 3 深度上限 | `test_trigger_chains_stop_at_depth_three_with_a_limit_event`（雙方 `on_damaged` 對來源傷害、`max_per_round: 3`、相鄰互打：深度 1、2、3 之後 `TriggerLimitReached`，結算正常結束）、`test_a_limited_trigger_does_not_spend_its_use` |
| 4 不無限迴圈（hypothesis） | `tests/sim/test_passive_battles.py::test_random_passives_never_loop_and_replay_exactly`（雙方各 1–2 個組合器產生的被動，整場戰鬥；每個 `SkillTriggered` 深度 1–3；在 `max_actions=2000` 內結束）、`test_mutual_thorn_skin_battle_ends_and_respects_the_depth_limit` |
| 5 狀態限制 | `test_a_silenced_stunned_or_dead_holder_does_not_trigger`、`test_a_holder_downed_by_the_same_attack_does_not_trigger`、`test_not_enough_mana_means_no_trigger_and_triggering_pays_the_mana`、`test_cooldown_blocks_the_next_trigger_until_it_expires` |
| 6 condition、`max_distance` | `test_mark_detonation_uses_the_condition_on_the_unit_that_was_hit`、`test_thorn_skin_only_answers_attackers_within_its_max_distance`、`test_second_wind_needs_the_holder_to_be_below_half_hp` |
| 7 preview | `test_preview_includes_the_triggered_status_and_matches_the_resolution`、`test_preview_does_not_change_the_state_or_consume_trigger_counts` |
| 8 重播 | `tests/sim/test_passive_battles.py::test_random_passives_never_loop_and_replay_exactly`（`replay` 的事件與最終狀態一致，`BattleLog` JSON 來回後仍一致） |
| 9 驗證 | `tests/skillgen/test_passive_validation.py`：`test_a_passive_without_trigger_and_an_active_with_one_are_schema_errors`、`test_target_other_needs_a_trigger_with_another_party`、`test_a_passive_below_epic_is_rejected`、`test_an_unknown_event_is_rejected`、`test_every_n_hits_needs_n_two_or_three`、`test_max_per_round_is_between_one_and_three`、`test_a_self_target_passive_cannot_hurt_enemies`、`test_an_over_budget_passive_is_rejected` |

其他新增：`tests/content/test_skill_triggers_content.py`（9 個時機與係數、四個手寫被動不在既有 build）、`tests/sim/test_metrics.py::test_triggered_passives_are_counted_and_attributed_like_a_skill_use`、`tests/sim/test_skill_fuzz.py::test_a_passive_is_fought_and_its_triggers_are_counted`、`tests/skillgen/test_random_composer.py` 的三個被動測試、`tests/engine/test_passive_triggers.py::test_events_render_in_traditional_chinese`。

### 3.3 `trpg skills budget --all`

```
skill_ember_brand      餘燼烙印  1  被動 4.50  5.66  +10  79.6%  —
skill_mark_detonation  標記引爆  2  被動 5.95  7.27  +10  81.8%  —
skill_second_wind      回氣      1  被動 6.30  7.07  +10  89.1%  —
skill_thorn_skin       荊棘之膚  1  被動 5.00  5.60  +0   89.3%  —
通過 37 個，違規 0 個。
```

四個手寫被動的數值都落在 70%–100% 內，未調整初值。

### 3.4 `skill_fuzz.py --count 1000`

```
隨機技能驗收：種子 0–999，共 1000 個
  組合成功 1000/1000；通過驗證 1000/1000
  可施放 1000/1000（100.0%）；合法選取共執行 2719 次
  AI 對戰 144 場（我方勝 138、敵方勝 6、平手 0）
  被動 49 個（每個打一場戰鬥）；其中實際觸發過 38 個，共觸發 56 次
  例外 0 個
```

被動 49 個（占 4.9%），其中 38 個在一場 AI 戰鬥中至少觸發一次（共 56 次）。沒觸發的 11 個多半是 `on_crit`、`on_natural_20`、`on_kill` 這類在單場戰鬥中不易發生的時機。

### 3.5 手動：`trpg battle` ＋ `--log-json` ＋ `replay`

方式：把 `content/` 複製到暫存目錄，加一個測試用範本 `hero_ember`（`hero_mage` 加上 `skill_ember_brand`、`skill_second_wind`），用 `TRPG_CONTENT_DIR` 指向它，`--allies hero_ember,hero_fighter,hero_archer`（repo 內的內容沒有被改動）。

```
$ TRPG_CONTENT_DIR=<copy> uv run trpg battle --map test_flat_6x6 --seed 3 \
    --allies hero_ember,hero_fighter,hero_archer --log-json battle.json
$ TRPG_CONTENT_DIR=<copy> uv run trpg battle replay battle.json
重播驗證通過：86 個動作、238 個事件，最終狀態一致（test_flat_6x6，種子 3）。
```

節錄見第 7 節。

### 3.6 Phase 2 驗收 ⚠️ #1 與 #11

- **#1 觸發的資料檔**：觸發時機現在是資料。`content/skill_triggers.yaml` 定義 9 個時機（ID、中文名、是否有另一方、預算係數、最低稀有度），以 `SkillTriggerTable` 驗證（必須剛好是引擎實作的 9 個）；技能用 `trigger.event` 引用，驗證器檢查引用存在、`target: other` 搭配有另一方的時機、`every_n_hits` 的 `n`。新增被動不需改引擎程式；新增時機種類則需要引擎收集點（`REQUIRED_TRIGGERS` 刻意與引擎同步）。
- **#11 觸發深度上限**：`content/rules/core.yaml` 的 `max_trigger_depth: 3`。動作直接引起的觸發深度為 1，觸發的效果再引起的觸發深度 +1；超過上限時發出 `TriggerLimitReached`，不付代價、不計次數。測試：`test_trigger_chains_stop_at_depth_three_with_a_limit_event`（確定性情境）與 `test_random_passives_never_loop_and_replay_exactly`（hypothesis，整場戰鬥）。此外每個被動每輪有 `max_per_round`（1–3）的次數限制。

## 4. 設計與實作說明

1. **收集與結算**：`Ctx.emit` 呼叫 `observe()`，只把命中判定（`attack_rolled`）與傷害（`damage_dealt`）轉成 `Fired` 記錄；回合開始、回合結束、移動由 `turns.py`、`battle.py` 直接收集。結算（`settle`）在三個點發生：效果佇列清空時、`use_skill` 與一次攻擊（`holding`）結束時、`finish_resolution`。這樣「整個技能的所有效果」都完成後才觸發（技能傷到多人時每個被命中者各自觸發）。結算不可重入；一批以（事件順序、持有者單位 ID、技能 ID）排序，BFS 逐批處理，批次間深度 +1。
2. **觸發的效果**：以 `_TriggeredCast` 結算（不擲命中、對非施放者視為命中，來源為持有者）；狀態仍會擲抗性；傷害 `cause` 維持 `attack`。
3. **檢查順序**：持有者在場、沒有 `skip_turn`、沒被沉默、每輪次數、另一方（`target: other` 時必須存活，`on_kill` 例外）、`max_distance`、技能條件、法力／HP／冷卻／使用次數，最後才檢查深度（超過就不付代價）。
4. **單位狀態**：`UnitState.trigger_counts`（每輪重設，在 `RoundStarted`）與 `hits_landed`（`every_n_hits` 累計，僅對帶有該類被動的單位計數，不重設）。
5. **預算**：被動的可用預算 ＝ tier_budget × 觸發係數 × `(passive_extra_trigger_permille / 1000)^(max_per_round − 1)` ×（1 ＋ 折抵）；`every_n_hits` 依 `n` 查表。`trpg skills budget` 顯示係數標籤與「被動」欄。
6. **驗證**：`passive.category`（法術技、`weapon_req: any`）、`passive.affects`（`target: self` 時效果只能 `affects: self`）；骨架與時機的 `min_rarity` 併入稀有度檢查。`skill_exclusions.yaml` 的 `self_shape_no_enemy_effect` 加上 `kinds: [active, reaction, stance]`（`SkillMatch` 新增 `kinds`），因為被動的 `self` 形狀代表「作用在觸發對象」。
7. **組合器**：未指定骨架且稀有度 ≥ epic 時，用 `Rng(seed).fork("composer.passive")` 的獨立串流以 150‰ 決定是否改組被動，所以沒抽到被動的種子與 2D 完全相同（已用 `git archive HEAD` 的舊版對 150 個種子逐一比對，差異的 8 個全是被動）。明確指定 `skeleton="passive"` 且稀有度 ≥ epic 時一定組被動。被動：法術技、`weapon_req: any`、`self` 形狀、時機隨機、`other_permille: 600` 作用在另一方、第二個效果 350‰；法力 0–3 ＋ 每階 1、冷卻 250‰（1–2）。
8. **模擬**：`SkillTriggered` 在指標中等同「技能使用」（`skills[id].uses`、`skill_users`，其後的傷害歸給該被動）；`UnitMetrics.triggers_fired`、`BattleMetrics.trigger_limit_count`、異常 `trigger_limit`；`trpg sim skills` 的「次／場」欄對被動即觸發次數（標題改為「次／場（被動＝觸發）」）。
9. **fuzz**：被動沒有合法選取，所以每個被動都打一場 UtilityAI 戰鬥，數 `SkillTriggered`；被動視為 `castable`。

### 修改既有測試（原因）

- `tests/cli/test_battle_cli.py`、`test_skills_cli.py`：`LOG_FORMAT` `/7` → `/8`。
- `tests/engine/test_state_clone.py`：`UnitState` 新欄位 `trigger_counts`。
- `tests/content/test_skill_rules_content.py`：啟用骨架集合加入 `passive`。
- `tests/skillgen/test_budget.py`：「被動沒有預算公式」改成「被動用觸發係數」。
- `tests/skillgen/test_validate.py`：`passive` 從「停用骨架」移到「有效範例」。
- `tests/cli/test_budget_cli.py`、`tests/sim/test_skill_report.py`：技能總數 33 → 37、34 → 38。
- `tests/skillgen/test_random_composer.py`：`ENABLED` 加入 `passive`；`kind` 檢查允許被動；`ComposeError` 測試改為稀有度 rare 的 passive 與被動指定武器技。
- `tests/sim/test_skill_fuzz.py`：被動不計「合法選取」，且每個被動都打一場戰鬥。

## 5. 數據

- 預算：4 個手寫被動 79.6%／81.8%／89.1%／89.3%（見 3.3）。
- fuzz 1000：被動 49 個（4.9%），觸發過 38 個（77.6%），共 56 次；其他分佈（骨架、稀有度、階級）與 2D 相近，`passive` 只占 epic/legendary 的約 17%。
- 完整 `pytest`：1230 passed，約 348 秒。

## 6. 待 PM 決定

1. **`on_kill` 搭 `target: other`**：另一方已倒下，效果對它無效（傷害、狀態不生效）；`on_hit` 搭 `target: other` 的那一擊若打死對方，也不觸發（另一方必須存活，僅 `on_kill` 例外）。保守做法；若要「擊殺時對附近敵人」需另設對象規則。
2. **觸發傷害的 `cause` 維持 `attack`**：會計入 DPR、可被 `on_damaged` 再觸發；預覽的傷害期望值對觸發傷害退回中間平均。若想與直接攻擊分開統計，需新增 `cause`（會改事件格式）。
3. **`on_damaged` 的判定是 `amount > 0`**：被護盾完全吸收（`absorbed`）的傷害也算「受傷」。
4. **觸發效果的預設 `target` 是 `self`**（`TriggerSpec.target` 省略時），`other` 必須明寫。
5. **`hits_landed` 只對帶 `every_n_hits` 被動的單位計數**（效能與狀態大小），中途才裝備該被動的單位從 0 開始。
6. **`SkillMatch.kinds` 與 `self_shape_no_enemy_effect`**：為了讓被動的 `self` 形狀能帶敵方效果新增 `kinds` 過濾欄位；若 2E-2 的反應技、姿態也需要，可沿用。
7. **組合器被動機率 150‰ 與數值（法力 0–3、冷卻 250‰）為初值**：1000 個種子中被動占 4.9%，是否要提高請看 2E-3 的全量報表再定。
8. **`LOG_FORMAT` 升為 `/8`**：規則包新增 `skill_triggers`、單位狀態新增欄位，舊紀錄無法重播。
9. **被動槽上限沿用既有的「被動技能超過欄位上限：2 個」**，沒有改動。
10. **手寫被動不加入既有 build**（照規格），所以目前 `trpg sim matrix` 等報表看不到被動；手動驗收是用暫存內容目錄加測試範本。

## 7. 附錄：代表性 CLI 輸出

`trpg battle --map test_flat_6x6 --seed 3 --allies hero_ember,hero_fighter,hero_archer`（節錄，第 1 輪）：

```
— 餘燼法師 的回合（AP 3，移動 5，法力 40/40）
  餘燼法師 施放「火焰箭」（AP 1，法力 6）→ 影響 1 格
  餘燼法師 以「火焰箭」攻擊 盜賊頭目：d20=10 修正 +1 熟練 +2 = 13（目標 11）→ 命中
    盜賊頭目 受到 12 點火焰傷害［骰 4］，HP 59 → 47
  盜賊頭目 獲得狀態「燃燒」（1 回合）
  ★ 餘燼法師 的被動「餘燼烙印」觸發（命中時，深度 1），對象 盜賊頭目（法力 2）
  盜賊頭目 刷新狀態「燃燒」（3 回合）
```

`--log-json` 中對應的事件：

```json
{"seq": 79, "round": 1, "type": "skill_triggered", "unit_id": "unit_0001", "skill_id": "skill_ember_brand", "name_zh": "餘燼烙印", "trigger": "on_hit", "other_id": "unit_0006", "trigger_depth": 1, "mana": 2, "mana_after": 26, "hp_spent": 0, "cooldown": null}
{"seq": 80, "round": 1, "type": "status_applied", "target_id": "unit_0006", "status_id": "burning", "duration": 3, "refreshed": true, "source_id": "unit_0001"}
```

`replay`：`重播驗證通過：86 個動作、238 個事件，最終狀態一致（test_flat_6x6，種子 3）。`

## 8. 給下一個子階段的備註

- 2E-2 的反應技可重用 `skill_triggers.py` 的 `holding` 與 `settle`、`_TriggeredCast`（自動命中的技能結算）、`UnitState.trigger_counts`（每輪次數）與 `SkillMatch.kinds`；`hit_by_*` 事件可在 `observe()` 增加分支。
- `ally_hit_adjacent` 要在傷害結算之前處理，與目前「延後結算」的分派不同，需要另開收集點。
- 組合器的被動走獨立的 `_attempt_passive`；反應技、姿態若也用獨立串流決定骨架，可維持舊種子對應不變。
- `_skeleton_feasible` 現在有 `explicit` 參數：非主動骨架只有明確指定時才可行，新增骨架請沿用，避免改變預設抽選。
- `trpg sim skills` 的「次／場」對被動是觸發次數；若 2E-3 要比較被動與主動的 DPR，注意觸發傷害 `cause` 為 `attack`（待 PM 決定 2）。
