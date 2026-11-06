# Phase 2E-2 報告：反應技、擋攻擊、姿態

## 1. 摘要

- 新增 `kind: reaction`（`SkillDef.reaction.event`：`hit_by_melee`、`hit_by_attack`、`ally_hit_adjacent`、`enemy_leaves_adjacent`）：不花 AP、付法力與冷卻、與格擋共用 `reactions_per_round`，支援 prompt／pending／resume，`trigger_depth` +1。
- 新增 `intercept` 原語（只能在 `ally_hit_adjacent` 反應技，rare）：命中後、傷害前把單體攻擊改由相鄰友方承受；範圍技不被攔截；新事件 `AttackIntercepted`。
- 新增 `kind: stance`（`stance_ap_cost: 1`）：同時只有一個姿態、取代舊的、`EndStance` 免費、倒下移除、淨化不移除；2 個姿態狀態與技能。
- 內容：`skill_stand_firm`（挺身而出）、`skill_riposte`（還擊）、`skill_fury_stance`、`skill_bulwark_stance`、`build_guardian`、`sim_duelist`；`reaction`／`stance` 骨架啟用；組合器能產生兩者，fuzz 1000 個無例外（反應技 70、姿態 45）。
- `LOG_FORMAT` 升為 `trpg-battle-log/9`；既有 build（tank、support、warlock，種子 1、2）的戰鬥輸出與 2E-1 完全相同。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `fb10daa` feat(engine): reaction skills, intercept primitive and stances | schema（`ReactionSpec`、`StatusDef.stance`、`stance_ap_cost`、`stance_coefficient_permille`）、引擎（反應分派、攔截、`EndStance`、姿態取代與移除、AI、preview、渲染）、`intercept` 原語、骨架啟用、姿態狀態、4 個技能、`build_guardian`、`sim_duelist`、既有測試的更新 |
| `6961c3f` feat(skillgen): compose reaction skills and stances; fuzz covers them | 組合器（`reaction`／`stance`）、`skill_composer.yaml` 新區段、fuzz 對反應技打整場並計觸發、摘要新增一行、`trpg skills budget` 的 AP 欄顯示 |
| `97140c1` test: reaction skills, intercept, stances and guardian battle | 新測試檔（見第 3 節）與型別修正 |
| （本報告的 commit） | `docs/phases/Phase2E-2報告.md` |

> 內容檔與 `build_guardian` 在實作過程中併入 `fb10daa`（引擎與內容互相依賴，拆開會讓中間 commit 無法載入）。

主要檔案：

- 內容：`content/skills/skill_{stand_firm,riposte,fury_stance,bulwark_stance}.yaml`、`content/units/sim_duelist.yaml`、`content/sim/builds.yaml`、`content/statuses.yaml`、`content/skill_primitives.yaml`、`content/skeletons/{reaction,stance}.yaml`、`content/rules/core.yaml`、`content/skill_budget.yaml`、`content/skill_composer.yaml`、`content/ai_profiles.yaml`。
- 程式：`content/{skills,battle,environment,library,rules,skill_rules,composer_rules}.py`、`engine/{reactions,lifecycle,battle,actions,events,preview,runner,skill_triggers}.py`、`engine/skills/{interpreter,targeting}.py`、`engine/effects/handlers.py`、`engine/rules/statuses.py`、`engine/ai/utility.py`、`skillgen/{budget,validate,composer_parts,random_composer}.py`、`sim/skill_fuzz.py`、`cli/{render,budget}.py`。

## 3. 驗收結果（4.5 逐條）

| 驗收項目 | 結果與證據 |
|---|---|
| `check.py` 全過 | ruff check／ruff format --check／mypy／lint-imports／pytest 全部通過：`1286 passed, 7 deselected in 403.61s` |
| 組合器產生 `reaction`（含 `intercept`）與 `stance`；fuzz 涵蓋 | `tests/skillgen/test_random_composer.py`：`test_explicit_reactions_are_valid_in_every_tier_and_cover_every_event`（階級 1–5 × 30 種子，四種事件都出現，含 `ally_hit_adjacent`＋`intercept`）、`test_explicit_stances_are_valid_in_every_tier_and_have_a_stance_status`、`test_random_reactions_and_stances_appear_without_changing_common_seeds`；`tests/sim/test_skill_fuzz.py::test_one_hundred_seeds_pass_validation_cast_and_run_without_exceptions`。fuzz 1000 個：反應技 70（觸發過 7 個、共 8 次）、姿態 45、`intercept` 效果 41 個，例外 0 |
| 反擊近戰命中後觸發、遠程不觸發 | `tests/engine/test_reaction_skills.py`：`test_content_riposte_hits_back_for_free_when_meleed`、`test_hit_by_melee_ignores_ranged_attacks`；`test_hit_by_attack_fires_on_ranged_hits_and_misses_do_not_trigger` |
| 反應技與格擋共用每輪 1 次 | `test_reaction_skills_share_reactions_per_round_and_reset_each_round`（`reactions_used`）；`test_the_intercept_does_not_refresh_taunts_and_ignores_the_targets_block`（攔截後原目標不格擋） |
| 法力、冷卻、不花 AP、昏迷不能反應 | `test_mana_and_cooldown_are_paid_and_gate_the_reaction`、`test_a_stunned_owner_cannot_react`、`test_content_riposte_hits_back_for_free_when_meleed`（AP 不變） |
| 致盲的守護者／反擊者受距離上限 | `test_blinded_owner_cannot_target_beyond_the_range_cap`、`test_shape_single_needs_the_trigger_in_range` |
| `intercept` 改寫目標；守護者護盾吸收；原目標毫髮無傷 | `tests/engine/test_intercept.py`：`test_a_melee_attack_is_taken_by_the_adjacent_guardian`（原目標 HP 不變、不重擲命中、守護者獲得護衛）、`test_a_skill_attack_with_a_single_shape_is_intercepted`（控制狀態改落在守護者）、`test_displacement_is_recomputed_from_the_attacker_to_the_guardian`、`test_the_first_guardian_by_unit_id_wins`、`test_an_unavailable_first_guardian_falls_through_to_the_next` |
| 範圍技能不被攔截 | `test_area_skills_are_not_intercepted`；相鄰才攔：`test_a_guardian_must_be_adjacent_to_the_target`；未命中不攔：`test_a_miss_is_not_intercepted` |
| prompt 模式的反應技暫停與恢復 | `test_a_reaction_skill_can_use_the_prompt_mode`（接受／拒絕兩條路） |
| 觸發深度 | `test_trigger_depth_limit_stops_the_reaction`（`max_trigger_depth=0` 發出 `TriggerLimitReached`） |
| 姿態：花 1 AP、取代、`EndStance`、倒下移除、淨化不移除 | `tests/engine/test_stances.py`：`test_entering_a_stance_costs_the_core_stance_ap_and_applies_the_status`、`test_a_new_stance_replaces_the_old_one`、`test_the_same_stance_cannot_be_entered_twice`、`test_end_stance_is_free_and_only_legal_with_a_stance`、`test_a_stance_is_removed_when_the_unit_goes_down`、`test_a_stance_is_not_removed_by_cleanse`、`test_a_stance_stays_across_rounds`、`test_stance_effects_change_damage_taken_and_attributes` |
| AI 會進入姿態 | `test_the_ai_values_entering_a_stance_when_it_has_nothing_better`、`test_the_ai_does_not_cancel_or_reenter_a_stance`；`tests/cli/test_guardian_battle.py::test_guardian_battle_logs_intercepts_stances_and_replays`（AI 戰鬥的動作列表含 `skill_bulwark_stance`） |
| preview 含攔截與反擊 | `test_intercept.py::test_preview_follows_the_real_branch_and_is_pure`（`Outcome("intercepted")`）、`test_reaction_skills.py::test_preview_includes_the_counter_reaction` |
| 重播一致 | `test_intercept.py::test_the_intercept_is_deterministic_and_replayable`；CLI 重播見下 |
| `trpg skills budget --all` 全過 | 「通過 41 個，違規 0 個。」新技能：挺身而出 90.7%、還擊 75.0%、狂怒姿態 78.6%、堅壁姿態 78.6% |
| `skill_fuzz.py --count 1000` 無例外 | 「組合成功 1000/1000；通過驗證 1000/1000；可施放 1000/1000；例外 0 個」（約 54 秒） |
| `trpg battle --ally-build build_guardian --log-json` 與 `replay` 一致 | 種子 1：「重播驗證通過：111 個動作、275 個事件，最終狀態一致」；種子 6：123 個動作、300 個事件，一致。測試：`tests/cli/test_guardian_battle.py`（含「還擊」的 `sim_duelist` 戰鬥，種子 3 重播一致） |
| 既有 build 不變 | 以 2E-1 的 commit `b63efab` 與本版跑 `build_tank`／`build_support`／`build_warlock` × 種子 1、2 的 `trpg battle` 輸出逐位元組相同 |

### 被改動的既有測試（原因）

| 測試 | 原因 |
|---|---|
| `tests/cli/test_battle_cli.py`（及其他含 `battle-log/8` 者） | `LOG_FORMAT` /8 → /9 |
| `tests/cli/test_budget_cli.py`（2 處）、`tests/sim/test_skill_report.py` | 技能數 37 → 41、示範報表 38 → 42 |
| `tests/content/test_sim_builds.py` | 多一個 `build_guardian`（9 → 10 個 build） |
| `tests/content/test_skill_rules_content.py` | `ENABLED` 骨架集合加入 `reaction`、`stance` |
| `tests/engine/test_support_ai.py` | support 的 `ally_status_values` 多了 `stance_fury`／`stance_bulwark`（8） |
| `tests/skillgen/test_budget.py` | 反應技需要 `reaction` 欄位；狀態預算點數表多兩個姿態狀態 |
| `tests/skillgen/test_validate.py` | `reaction`／`stance` 不再是停用骨架（改為各有一個合格範例）；`skeleton.kind` 測試的技能補 `reaction`；有益狀態清單多兩個姿態 |
| `tests/skillgen/test_random_composer.py` | `ENABLED` 加入兩個骨架；kind 對應；「rare 不產生被動」改為「common 一律主動、rare 不是被動」 |
| `tests/sim/test_skill_fuzz.py` | 反應技和被動一樣每個都打一場、計觸發 |

新增測試檔：`tests/engine/{test_reaction_skills,test_intercept,test_stances}.py`、`tests/cli/test_guardian_battle.py`、`tests/content/test_reaction_stance_content.py`，另在 `test_random_composer.py` 增加 5 個測試。

## 4. 設計與實作說明（規格沒寫死、由我決定的部分）

- **統一的反應分派**：`engine/reactions.py` 的 `_react` 同時處理內建反應（格擋、藉機攻擊）與反應技，共用 `reactions_used`、prompt／pending 流程與深度檢查；`make_unit` 為每個裝備的反應技自動加一條 `auto` 規則（置於其他規則之前，範本已自訂規則者不加）。`ReactionWhen.event` 的合法值多了 `hit_by_melee`、`hit_by_attack`、`ally_hit_adjacent`；範本規則可直接引用反應技 ID（`check_rule` 檢查事件與技能的 `reaction.event` 一致）。
- **「近戰」的判定**：普攻看武器是否近戰；技能看射程輪廓是否受高度限制（`profile.height_limited`，即武器射程的近戰技）。遠程單體技仍算 `hit_by_attack`。
- **攔截的時機**：在 `_attack_once`（普攻）與 `_Cast.roll_hits`（`single` 形狀技能）的命中之後、格擋與傷害之前。改寫目標時一併改寫命中紀錄、敵人清單、影響範圍與尚未結算的被動觸發（`redirect_fired`）；方向由攻擊者重新指向守護者。攔截不使用嘲諷、不重擲命中。守護者必須是原目標的相鄰友方（同陣營、非原目標、存活、可反應），依單位 ID 取第一個符合者；第一個因冷卻、法力、昏迷或次數用完而不可用者，會換下一個。
- **姿態**：姿態狀態以 `stance: true`（要求 `expires: never`、無 `duration`）標記；`apply_status` 先移除其他姿態並發出 `StatusRemoved(reason="replaced")`；`down_unit`／`escape_unit` 以 `downed` 原因移除；淨化略過姿態。`has_only_end_turn` 在有姿態時恆為假（保持 `has_only_end_turn == (len(legal_actions) == 1)`）。AI：已有姿態時不重進、不取消，且 `rank` 在只剩 `EndStance`／`EndTurn` 時直接回傳。
- **預算**：反應技用 `reaction_coefficient_permille`（600）；姿態用新的 `stance_coefficient_permille`（1000）。姿態狀態的 `budget_points` 為 11（階級 1 為 78.6%）。
- **組合器**：用獨立的 `Rng(seed).fork("composer.reaction"|"composer.stance")` 決定是否改組（rare 以上、未指定骨架時），建構另用 `fork("composer.<kind>.build")`，做不出來時退回原本的主動技能，所以沒被抽中的種子輸出不變。反應技分三類：擋攻擊（`intercept` ＋自身護盾旋鈕）、自身增益（形狀 self）、對觸發者（傷害、有害狀態、推、拉）。姿態是一個姿態狀態；階級 2 以上（或抽中）加一個帶旋鈕的自身護盾，否則高階預算湊不到。姿態狀態排除在其他骨架的狀態候選之外。實測階級 1–5 × rare／epic／legendary × 40 種子，兩種骨架全部成功（0 次退回）。
- **fuzz**：反應技和被動一樣沒有合法選取，改為各打一場並計 `ReactionTriggered`；姿態走一般的合法選取；摘要新增一行「反應技 N 個……姿態 M 個」。

## 5. 數據

- fuzz（`--count 1000 --seed-start 0`）：骨架分佈 area 156、aura 172、combo 79、control 175、displace 89、passive 49、reaction 70、stance 45、strike 165；被動 49 個（觸發過 38）；反應技 70 個（觸發過 7、共 8 次——fuzz 場景只有一名友方弓手，很少相鄰被打）；平均重抽 0.588；例外 0。
- 模擬（`trpg sim matrix --builds build_guardian,build_tank,build_support,build_assassin --seeds 8 --jobs 4`，異常場次全為 0）：`build_guardian` 在 8 張地圖中 4 張排第 1（僅 4 個 build、每格 8 場，樣本小，**未調整任何數值**）；英雄 DPR 1.4–6.4，承受傷害 6.6–46.0，隊友存活率 6.2%–50%。
- `scripts/check.py`：五項全過，`1286 passed, 7 deselected`。

## 6. 待 PM 決定（最多 10 點）

1. **姿態欄位上限仍是 1**（`core.yaml` `skill_slots.stance: 1`），所以一個單位同一時間只能裝備一個姿態技能，「取代舊姿態」只有靠外力（測試放寬欄位、將來的裝備或詞條）才會發生。是否要把姿態欄位提高到 2？現在 `build_guardian` 只帶一個姿態（堅壁）。
2. **姿態狀態的預算點數 11** 讓階級 1 剛好 78.6%，階級 2 以上單一姿態只有 61% 以下，組合器因此一律加自身護盾。是否接受？或要把姿態的預算係數改成隨階級變動？
3. **組合器機率初值**：`reaction.skeleton_permille: 100`、`stance.skeleton_permille: 60`（rare 以上）。fuzz 中反應技很少實際觸發（7/70），不影響正確性，但分佈是否合適請 PM 看。
4. **`build_guardian` 的平衡未調**：小樣本模擬中它常排第 1（4/8 張地圖）。請 PM 決定要不要跑完整矩陣（10 build × 8 地圖）後再調 `stand_firm` 的冷卻（現為 1）或姿態的減傷。
5. **AI profile 選 `guard`**（規格允許 guard 或 support）；姿態的 AI 價值掛在 `ally_status_values`（兩個姿態各 8），因此 support profile 的該表也多了兩項（對 support 自身無影響，只是共用同一張表）。
6. **反應技優先於內建反應**：自動規則放在規則清單最前面；單位同時有「還擊」與藉機攻擊時，同一事件由反應技先用掉當輪唯一的次數。若 PM 要相反的優先序，改規則順序即可。
7. **攔截只看「單體」**：任何 `single` 形狀的命中（含遠程單體技、普攻）只要守護者與原目標相鄰都可攔截，並不限近戰；連鎖（chain）與範圍不攔。
8. **反應技與格擋共用一次**：一輪只有一次反應，攔截後原目標的格擋不會觸發（規格寫了），但若守護者本身也有格擋規則，攔截後守護者仍會對這次命中檢查格擋（共用次數已被攔截用掉時就不會格擋）。
9. **`StatusRemoved.reason` 新增 `replaced`、`stance_ended`、`downed`**，舊紀錄不受影響；`LOG_FORMAT` 已升為 /9。
10. 規格 4.4 的「還擊」放在新範本 `sim_duelist`（屬性比照 `hero_fighter`，不屬於任何 build）；若想直接給既有 build 或單位使用，再另行指定。

## 7. 附錄：代表性 CLI 輸出

`uv run trpg battle --map test_flat_6x6 --ally-build build_guardian --seed 1 --log-json out.json`（節錄）：

```
  盜賊頭目 攻擊 標準隊友（戰士）：d20=13 修正 +0 熟練 +2 = 15（目標 11）→ 命中
  ⟳ 守護者英雄 反應：「挺身而出」
  守護者英雄 施放「挺身而出」（AP 0，冷卻 1 回合）→ 影響 1 格
  🛡 守護者英雄 攔截了 盜賊頭目 對 標準隊友（戰士） 的攻擊——改由 守護者英雄 承受
  守護者英雄 獲得狀態「護衛」（2 回合）
    守護者英雄 受到 9 點物理傷害［骰 6+5］（元素修正 ×0.9）（狀態 ×0.7），HP 60 → 51
  盜賊頭目 結束回合
— 守護者英雄 的回合（AP 3，移動 5，法力 20/20）
  守護者英雄 的「挺身而出」冷卻結束
  守護者英雄 施放「堅壁姿態」（AP 1）→ 影響 1 格
  守護者英雄 獲得狀態「堅壁姿態」
```

`uv run trpg battle replay out.json` → `重播驗證通過：111 個動作、275 個事件，最終狀態一致（test_flat_6x6，種子 1）。`

`--allies sim_duelist,hero_archer,hero_mage --seed 3`（節錄）：

```
  盜賊頭目 攻擊 反擊者：d20=14 修正 +0 熟練 +2 = 16（目標 11）→ 命中
    反擊者 受到 7 點物理傷害［骰 1+2］（元素修正 ×0.9），HP 31 → 24
  ⟳ 反擊者 反應：「還擊」
  反擊者 施放「還擊」（AP 0）→ 影響 1 格
  反擊者 以「還擊」攻擊 盜賊頭目：d20（劣勢 17、1）=1 修正 +1 熟練 +2 = 4（目標 11）→ 自然 1，失手
```

## 8. 給下一個子階段（2E-3）的備註

- 反應技入口是 `engine/skills/interpreter.use_reaction_skill`；它設定並還原 `ctx.trigger_depth`，陷阱或層數若也要「不花 AP 的技能施放」可沿用。
- `_react`（`engine/reactions.py`）是所有反應的單一入口，新增觸發事件只需在 `hit_reactions`／`opportunity_attacks` 旁加呼叫點，並擴充 `ReactionWhen.event` 與 `SKILL_REACTION_EVENTS`。
- 姿態狀態的辨識用 `StatusDef.stance`；如果 2E-3 的層數（stacks）要與姿態並存，注意 `apply_status` 的「先移除其他姿態」在 `engine/effects/handlers.py`。
- 組合器的特殊骨架分派在 `random_composer._wants_special` ＋ `_compose_special`，陷阱可仿照新增。
