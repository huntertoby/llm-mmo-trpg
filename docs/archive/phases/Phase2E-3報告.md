# Phase 2E-3 報告：層數、陷阱與收尾

## 1. 摘要

- 新增層數系統：`content/stacks.yaml`（施放者型 `static_charge` 上限 5、目標型 `sunder` 上限 3、3 輪未刷新即清空）、原語 `add_stack`／`consume_stack`、代價 `cost.stacks`、事件 `StacksChanged`；`builder_finisher` 骨架啟用（rare 以上），終結技把消耗的層數換成同一技能的傷害加成。
- 新增陷阱系統：原語 `place_trap`、技能欄位 `trap`（`enter`／`delay`；`single`／`cross`／`square3`）、`BattleState.traps`、事件 `TrapPlaced`／`TrapTriggered`／`TrapExpired`；陷阱只有放置者陣營看得見（AI、preview 都經過 `visible_traps`）；`trap` 骨架啟用（`trap_coefficient_permille` 800）。
- 手寫技能 6 個（靜電掌、雷霆終結、破甲擊、碎甲重擊、灰燼地雷、捕獸夾）；新 build `build_striker`、`build_trapper`；組合器與 fuzz 開啟所有 2E 骨架。
- 收尾：`check.py` 1341 通過；fuzz 1000 無例外；completion 1800 場異常 0；matrix 2400 場（12 build × 10 地圖 × 20 種子）異常 0。既有 build 的戰鬥輸出與 2E-2 相同（僅傷害標籤文字合併，見第 4 節）。`LOG_FORMAT` 升為 `trpg-battle-log/10`。
- Phase 2 驗收 ⚠️ #1、#11 在 2E-1 已補，本階段的陷阱與終結技沿用同一深度上限（見 5.4）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `1895d11` feat: stacks, traps and the builder_finisher/trap skeletons | 層數與陷阱的 schema、引擎（`engine/stacks.py`、`engine/traps.py`、解譯器、目標檢查、回合推進、效果佇列）、預算、效用 AI、preview、CLI 渲染、兩個骨架、六個手寫技能、組合器與 fuzz、`content/README.md`、新測試與既有測試的更新 |
| `dc1d0f3` feat: add build_striker and build_trapper sim builds | `content/sim/builds.yaml`、`tests/content/test_sim_builds.py`、`tests/cli/test_striker_trapper_battle.py` |
| （本報告的 commit） | `docs/phases/Phase2E-3報告.md` |

> 引擎、內容與組合器互相依賴（骨架啟用後 fuzz／驗證器就會用到引擎），拆開會讓中間 commit 無法通過測試，所以合併為第一個 commit。

主要檔案：

- 內容：`content/stacks.yaml`、`content/skills/skill_{static_palm,thunder_finisher,sunder_strike,armor_breaker,cinder_mine,bear_trap}.yaml`、`content/skeletons/{builder_finisher,trap}.yaml`、`content/skill_primitives.yaml`、`content/skill_budget.yaml`、`content/skill_composer.yaml`、`content/ai_profiles.yaml`、`content/sim/builds.yaml`。
- 程式：`content/{stacks,skills,skill_rules,composer_rules,environment,library,registry}.py`、`engine/{stacks,traps,battle,preview,runner,state,events,turns,lifecycle,context,skill_triggers}.py`、`engine/skills/{interpreter,targeting}.py`、`engine/effects/{queue,handlers}.py`、`engine/ai/utility.py`、`skillgen/{budget,mechanics,validate,composer_parts,random_composer}.py`、`sim/skill_fuzz.py`、`cli/{render,skills}.py`。
- 測試：`tests/engine/test_stacks.py`（11）、`tests/engine/test_traps.py`（16）、`tests/skillgen/test_stacks_traps_rules.py`（10）、`tests/skillgen/test_composer_stacks_traps.py`（6）、`tests/cli/test_striker_trapper_battle.py`（4）。

## 3. 驗收結果（5.3 逐條）

| 驗收項目 | 結果與證據 |
|---|---|
| 5.1 層數資料檔、`UnitState.stacks`、`StacksChanged`、CLI 顯示 | ✅ `content/stacks.yaml`；`test_stacks_traps_rules.py::test_the_stack_table_has_the_two_initial_stacks`；單位表顯示「靜電×3」（`test_the_grid_shows_only_the_player_teams_traps_and_the_unit_table_shows_stacks`） |
| `add_stack`（依 owner 加在施放者或目標、超過上限截斷） | ✅ `test_the_builder_adds_a_charge_to_the_caster_only_when_it_hits`、`test_stacks_are_capped_at_the_maximum`、`test_stacks_on_the_target_are_added_and_consumed_from_the_target` |
| `consume_stack`（消耗全部、傷害加成、無層數也可施放） | ✅ `test_the_finisher_consumes_all_charges_and_boosts_its_damage`、`test_a_target_finisher_works_with_no_stacks` |
| `cost.stacks`（不足時不可施放、不在合法動作內） | ✅ `test_a_finisher_needs_the_required_stacks_to_be_cast` |
| 目標型層數到期清空 | ✅ `test_target_stacks_expire_three_rounds_after_the_last_refresh`、`test_a_refresh_extends_the_expiry` |
| 預算：`add_stack`／`consume_stack` 點數、期望消耗 | ✅ `test_consume_stack_adds_expected_bonus_points`；`trpg skills budget --all`：47 個技能、0 違規（六個新手寫技能 75.5%–91.5%） |
| `builder_finisher` 骨架（rare、必含 `add_stack` 或 `consume_stack`） | ✅ `test_the_enabled_skeletons_require_their_structural_primitive_and_rarity`、`test_builder_finisher_skills_have_exactly_one_stack_effect` |
| 效用 AI 偏好終結技（用 preview 的真實傷害） | ✅ `test_the_ai_prefers_the_finisher_when_it_has_charges`、`test_the_ai_builds_charges_when_it_cannot_finish` |
| 手寫層數技能 4 個 | ✅ 靜電掌、雷霆終結、破甲擊、碎甲重擊（`test_the_six_handwritten_skills_are_valid_and_in_the_budget_window`） |
| 5.2 陷阱放置、儲存、同格唯一、快照屬性 | ✅ `test_placing_a_trap_stores_it_and_snapshots_the_owner_attributes`、`test_a_tile_holds_only_one_trap_and_must_be_free` |
| 隱藏（AI、preview 不讀對方陷阱） | ✅ `test_traps_are_hidden_from_the_other_team`、`test_the_preview_does_not_reveal_hidden_traps_but_the_real_move_triggers_them`、`test_the_enemy_ai_decides_the_same_with_or_without_the_hidden_traps` |
| `enter`／`delay` 觸發、過期、友軍不觸發 | ✅ `test_an_enemy_stepping_on_an_enter_trap_triggers_it`、`test_a_delay_trap_explodes_on_the_owners_second_turn_start`、`test_an_enter_trap_expires_after_its_rounds`、`test_a_trap_does_not_trigger_for_the_owners_team` |
| 主動與強制移動觸發（傳送不觸發） | ✅ `test_forced_movement_triggers_a_trap_but_teleporting_does_not` |
| 觸發深度 +1，超過上限陷阱留在原地 | ✅ `test_a_trap_over_the_trigger_depth_limit_stays_in_place` |
| 放置者倒下時陷阱移除 | ✅ `test_the_traps_disappear_when_the_owner_goes_down` |
| `trap` 骨架與 `trap_coefficient_permille` 800 | ✅ `test_a_trap_uses_the_trap_shape_and_the_trap_coefficient`、`test_trap_skills_start_with_place_trap_and_have_a_trap_field` |
| 效用 AI 放陷阱（敵人附近 1–3 步、不放在己方上） | ✅ `test_the_ai_places_traps_near_enemies_but_not_on_its_own_side`、`test_the_ai_never_places_a_cross_trap_over_an_ally` |
| 手寫陷阱技能 2 個 | ✅ 灰燼地雷（`delay` 2、`cross`、火焰＋火表面）、捕獸夾（`enter`、`single`、傷害＋`root`） |
| 不改敵人範本 | ✅ `git diff 4ef7764 --stat -- content/units` 為空 |
| 重播一致、JSON 來回 | ✅ `test_traps_replay_identically`、`test_traps_and_stacks_survive_a_json_round_trip`、`test_striker_battle_accumulates_and_consumes_static_charge_and_replays`、`test_trapper_battle_places_and_triggers_traps_and_replays` |
| 5.3-1 `build_striker`、`build_trapper`，不改既有 build | ✅ `test_the_new_builds_have_the_specified_skills`；既有 build 輸出對照見第 5 節 |
| 5.3-2 組合器開啟 2E 骨架、`skill_fuzz --count 1000` 無例外 | ✅ 1000／1000 組成、合法、可施放，0 例外；各骨架數量見第 5 節 |
| 5.3-3 slow 測試全過 | ✅ slow 測試通過（見下方註記） |
| 5.3-4 `trpg sim completion --seeds 20 --jobs 2` | ✅ 1800 場，exception 0、max_actions 0、draw 0（838.3 秒） |
| 5.3-5 `trpg sim matrix --seeds 20 --jobs 2` | ✅ 2400 場，異常場次 0；報表見第 5 節；`trigger_limit` 見第 5 節 |
| `check.py` | ✅ ruff、format、mypy（strict）、import-linter、pytest：1341 passed，7 deselected |

slow 測試註記：既有 `test_skill_fuzz.py` 的 slow 測試有一行 `len(counts) == 6` 的過時斷言（骨架數是寫死的），改成 `set(counts) == enabled`。demo 平衡的 xfail／xpass 測試為先前就存在，未動。

### 被改動的既有測試（原因）

| 測試 | 改動 |
|---|---|
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `trpg-battle-log/9` → `/10` |
| `tests/cli/test_budget_cli.py` | 技能數 41 → 47 |
| `tests/sim/test_skill_report.py` | 技能數 42 → 48 |
| `tests/content/test_sim_builds.py` | build 增加 2 個 |
| `tests/content/test_skill_rules_content.py`、`tests/skillgen/test_random_composer.py` | `ENABLED` 骨架集合加入 `builder_finisher`、`trap` |
| `tests/skillgen/test_validate.py` | 兩個新骨架的範例；停用骨架的參數只剩 `summon` |
| `tests/engine/test_state_clone.py` | 加入 `traps`、`stacks`、`stack_expiry` |
| `tests/sim/test_skill_fuzz.py` | 陷阱戰鬥；slow 測試的骨架斷言（見上） |

### 5.4 Phase 2E 驗收總表（`docs/專案計畫.md` 第 14 節）

| 驗收項目 | 結果與證據 |
|---|---|
| 觸發深度上限生效（技能層級） | ✅ `max_trigger_depth: 3`（`content/rules/core.yaml`）。被動：`tests/engine/test_passive_triggers.py::test_trigger_chains_stop_at_depth_three_with_a_limit_event`；陷阱：`test_traps.py::test_a_trap_over_the_trigger_depth_limit_stays_in_place`；反應技：`tests/engine/test_reaction_skills.py` |
| 被動有情境測試 | ✅ `tests/engine/test_passive_triggers.py`（2E-1） |
| 反應有情境測試（含擋攻擊） | ✅ `tests/engine/test_reaction_skills.py`、`tests/engine/test_intercept.py`（2E-2） |
| 姿態有情境測試 | ✅ `tests/engine/test_stances.py`（2E-2） |
| 陷阱有情境測試 | ✅ `tests/engine/test_traps.py`（16，本階段） |
| 層數有情境測試 | ✅ `tests/engine/test_stacks.py`（11，本階段） |
| 觸發不造成無限迴圈 | ✅ 深度上限＋每個被動每輪 `max_per_round`；`tests/sim/test_passive_battles.py::test_random_passives_never_loop_and_replay_exactly`（hypothesis，整場戰鬥）；fuzz 1000 內陷阱戰鬥與 AI 戰鬥 229 場全部結束 |
| 隨機 1,000 個技能（含觸發類）無例外 | ✅ `scripts/skill_fuzz.py --count 1000`（見第 5 節） |
| 重播一致 | ✅ `test_traps_replay_identically`、兩個新 build 的 CLI 重播測試、`tests/engine/test_skill_determinism.py` |

### Phase 2 驗收 ⚠️ 的最終狀態

- **#1 觸發的資料檔**：✅（2E-1 起）。`content/skill_triggers.yaml` 定義 9 個時機；技能用 `trigger.event` 引用。本階段的層數（`stacks.yaml`）與陷阱觸發（`enter`／`delay`）同樣是資料，新增層數種類不需改引擎程式。
- **#11 觸發深度上限**：✅（2E-1 起）。本階段的陷阱觸發與終結技沿用 `ctx.trigger_depth`；陷阱超過上限時發出 `TriggerLimitReached` 並留在原地（不消耗、不結算）。

## 4. 設計與實作說明（規格沒寫死、由我決定的部分）

1. **終結技加成公式**：傷害倍率 ＝ `倍率 × 格擋 × (1000 + 施放者層數加成 + 目標層數加成) // 10^6`；兩種層數可疊加，與格擋相乘而不是相加。
2. **施放者型 `add_stack` 要命中才累積**：至少要有一個被命中的敵人（擊倒也算）；沒命中不加層。目標型每命中一個目標加一次。
3. **目標型層數的到期**：每次累積重設計時；回合開始時倒數，到 0 就清空（`StacksChanged` 原因 `expired`）。
4. **層數條件的驗證**：`cost.stacks` 必須搭配 `consume_stack`，且不得超過該層數的上限；施放者型層數只能用在 `self` 擁有者，目標型不能設 `cost.stacks`（驗證器規則見 `test_stacks_traps_rules.py`）。
5. **預算**：`consume_stack` 的加成點數 ＝ 傷害點數（含形狀倍率）× 期望層數（上限 × `consume_stack_expected_permille` 500）× `per_stack_permille` ／ 1000；陷阱技能的形狀倍率取自 `trap.shape`，係數 ＝ AP 係數 × `trap_coefficient_permille`（800），標籤為「AP 係數 × 陷阱係數」。
6. **`SkeletonDef.require_any_primitives`**：新增骨架欄位，驗證規則 `skeleton.required_primitive`，兩個新骨架用它要求結構性原語（`add_stack`／`consume_stack`，`place_trap`）。
7. **陷阱放置合法性**：目標格必須可站立、非致命、無單位、無既有陷阱。
8. **陷阱觸發時機**：單位進入陷阱格（移動途中每一格都檢查）；`delay` 陷阱在放置者回合開始時倒數，到期引爆；`enter` 陷阱每輪倒數，到期 `TrapExpired`。放置者倒下或逃離時其陷阱全部移除（原因 `source_lost`）。
9. **移動中觸發**：陷阱觸發後若單位被定身或暈眩，該次移動中止（掃描新事件找 `TrapTriggered`，因為陷阱觸發後已被移除）。
10. **傳送不觸發陷阱**；步行與強制位移（擊退、拉扯）會。
11. **效果佇列**：新增 `trap_entries`，與 `surface_entries` 同樣在佇列清空後排空（`flush_trap_entries`），確保觸發順序確定。
12. **AI**：層數收益 ＝ 傷害權重 × `ai_value` × 命中；陷阱收益 ＝ 效果價值 × 形狀係數 × `trap_likelihood_permille`（700）；最多同時 2 個自己的陷阱；十字／方形陷阱的範圍內不得有友軍；目標格需在最近敵人 1–3 步內。
13. **CLI**：格子圖以 `^` 標示我方（玩家陣營）的可見陷阱，圖例「我方陷阱」；對方陣營的陷阱不顯示；單位表顯示「靜電×3」。傷害標籤由「（格擋 ×x）」合併為「（格擋/加成 ×x）」，因為終結技的層數加成與格擋共用同一個倍率欄位。
14. **靜電掌是 `spell`、`weapon_req: any`**：避免法師拿不到焦點武器以外的限制；雷霆終結需要焦點武器。破甲擊與碎甲重擊是近戰武器技。

## 5. 數據

### 5.1 預算（`trpg skills budget --all`）

47 個技能全數通過、0 違規。本階段手寫技能的預算使用率：

| 技能 | 使用率 |
|---|---|
| 靜電掌 | 75.5% |
| 雷霆終結 | 89.1% |
| 破甲擊 | 90.5% |
| 碎甲重擊 | 91.5% |
| 灰燼地雷 | 87.3% |
| 捕獸夾 | 83.5% |

### 5.2 `scripts/skill_fuzz.py --count 1000`

- 1000／1000 組成、通過驗證、可施放；例外 0。
- `builder_finisher` 28 個（全部可施放）；`trap` 25 個（其中 7 個在戰鬥中觸發，共 9 次觸發）。
- 原語：`add_stack` 17、`consume_stack` 11、`place_trap` 25；AI 對戰 229 場，全部正常結束。

### 5.3 既有 build 不變

`trpg battle --map test_flat_6x6` 對 build_tank、support、warlock、guardian、fire、push、assassin，種子 1、2（共 14 場）與基準 commit `4ef7764` 的輸出，在把標籤「（格擋/加成 ×x）」還原為「（格擋 ×x）」之後逐位元組相同。

### 5.4 `trpg sim completion --seeds 20 --jobs 2`

9 種設定 × 10 張地圖 × 20 種子 ＝ 1800 場，max_rounds 30：**exception 0、max_actions 0、draw 0，通過**（838.3 秒）。各格勝率 15%–100%、平均輪數 2.5–9.6（`hold_start` 設定下輪數較長）。完整表格由指令重現。

### 5.5 `trpg sim matrix --seeds 20 --jobs 2`

12 build × 10 地圖 × 20 種子 ＝ 2400 場，異常場次全為 0（988.8 秒）。以下為 8 種地圖類型的勝率與排名摘要（完整報表由指令重現，只記錄、不調平衡）。

| build | bridge_chasm | oil_depot | swamp | ruined_heights | forest | corridor | open_plain | frozen_lake | 前段次數 |
|---|---|---|---|---|---|---|---|---|---|
| build_push | 62.5% | 25.0% | 70.0% | 70.0% | 80.0% | 95.0% | 70.0% | 90.0% | 3 |
| build_fire | 82.5% | 55.0% | 70.0% | 80.0% | 100.0% | 90.0% | 80.0% | 90.0% | 7 |
| build_storm | 95.0% | 40.0% | 80.0% | 77.5% | 100.0% | 90.0% | 70.0% | 80.0% | 6 |
| build_tank | 47.5% | 30.0% | 40.0% | 57.5% | 95.0% | 80.0% | 30.0% | 70.0% | 0 |
| build_ranged | 77.5% | 35.0% | 65.0% | 80.0% | 95.0% | 100.0% | 50.0% | 50.0% | 3 |
| build_assassin | 57.5% | 15.0% | 65.0% | 72.5% | 90.0% | 95.0% | 45.0% | 75.0% | 1 |
| build_support | 62.5% | 20.0% | 60.0% | 60.0% | 100.0% | 85.0% | 55.0% | 85.0% | 1 |
| build_healer | 55.0% | 25.0% | 70.0% | 70.0% | 95.0% | 95.0% | 55.0% | 75.0% | 1 |
| build_warlock | 77.5% | 45.0% | 60.0% | 72.5% | 95.0% | 85.0% | 75.0% | 90.0% | 5 |
| build_guardian | 67.5% | 40.0% | 90.0% | 42.5% | 100.0% | 70.0% | 75.0% | 90.0% | 4 |
| **build_striker** | 62.5% | 30.0% | 60.0% | 70.0% | 90.0% | 90.0% | 55.0% | 75.0% | 0 |
| **build_trapper** | 77.5% | 50.0% | 70.0% | 65.0% | 85.0% | 90.0% | 40.0% | 80.0% | 1 |

英雄 DPR（跨地圖範圍）：striker 10.6–24.7（沼澤最高）、trapper 7.6–12.2。

6.8 標準檢查：

1. 沒有任何 build 在所有地圖類型都排名前段：**通過**。
2. 每個 build 至少在一種地圖類型排名前段：**不通過**，缺 `build_tank` 與 `build_striker`（前段次數為 0）。`build_tank` 是既有 build，`build_striker` 是新增的 build。只記錄、不調整。

### 5.6 `trigger_limit` 異常數

`trpg sim matrix` 的報表本身不輸出異常種類計數（只有 exception／max_actions 的場次），所以全量 matrix 沒有 `trigger_limit` 欄位。為了仍能回答這個問題，我另外用同一個 `matrix_specs`／`run_batches` 以 3 個種子重跑 12 build × 10 地圖共 360 場：**`trigger_limit` 0 次、exception 0 次**（其他異常：`one_shot` 7、`long_battle` 8，皆為既有種類）。這是抽樣，不是 20 種子的全量；見待 PM 決定 #9。

## 6. 待 PM 決定（最多 10 點）

1. **陷阱放置合法性會洩漏隱藏陷阱的存在**：放置者想把陷阱放在已有「對方陣營」陷阱的格子時，會被「同格只能一個」拒絕，等於得知該格有陷阱。2E 敵人沒有陷阱技能，所以目前只有玩家能碰到（且是自己放的）。保守做法：維持現狀。若之後敵人也有陷阱，需決定改成「無聲覆蓋」或「放置成功但舊的被取代」。
2. **放置者倒下或逃離時，其陷阱全部移除**（`source_lost`）。若希望陷阱在放置者死後仍留在場上，需要改。
3. **傳送不觸發陷阱**，步行與強制位移會。若希望傳送也觸發，需改。
4. **施放者型 `add_stack` 要命中才累積**（擊倒仍算命中）；沒命中不加層。若希望「施放就加」，可改。
5. **目標型層數每次累積重設計時**，且到期是「到期那一輪回合開始時清空」；也可以改為「不重設」或「每輪衰減 1 層」。
6. **陷阱觸發超過深度上限時留在原地**（不消耗、不結算），而不是被移除。這會讓同一個陷阱在下一次踩上時再嘗試。
7. **陷阱觸發後若單位被定身或暈眩，移動中止**。這是合理推論，規格只寫「除非單位倒下或因效果無法再移動」。
8. **各項初始數值都沒有經過模擬調整**：`trap_coefficient_permille` 800、`consume_stack_expected_permille` 500、AI 的 `trap_likelihood_permille` 700、最多 2 個自己的陷阱、1–3 步；`build_trapper` 的 AI 常把陷阱放在地圖角落，灰燼地雷幾乎沒被使用。`build_striker` 的 6.8 標準仍不通過（前段次數 0）。平衡階段再處理。
9. **`trpg sim matrix` 沒有 `trigger_limit` 欄位**：5.3-5 要求「另附 `trigger_limit` 異常數」，但矩陣報表不輸出異常種類。我用 360 場抽樣補上（0 次），若要全量數字需要 PM 同意讓矩陣報表增加該欄位（或再跑一次）。
10. **既有斷言與標籤的改動**：slow 測試的 `len(counts) == 6` 是過時的寫死斷言，我改成 `set(counts) == enabled`；傷害標籤「（格擋 ×x）」合併為「（格擋/加成 ×x）」，這是唯一一處既有戰鬥輸出的文字差異。

## 7. 附錄：代表性 CLI 輸出

層數的累積與消耗（`build_striker`，種子 1，`test_flat_6x6`）：

```
蓄力流英雄 施放「雷霆終結」…
蓄力流英雄 的「靜電」消耗：3 → 0 層
盜賊 受到 36 點雷電傷害［骰 6+7］（格擋/加成 ×1.75）
```

陷阱的放置與觸發（`build_trapper`，種子 1，`test_flat_6x6`）：

```
陷阱流英雄 在 (1, 2) 設下陷阱「捕獸夾」（敵人踩上時觸發，3 輪後消失）
  …
！盜賊頭目 踩中了 (1, 2) 的陷阱「捕獸夾」（陷阱流英雄 設置）
盜賊頭目 受到 12 點物理傷害…
```

格子圖以 `^` 標示我方陷阱，圖例顯示「^ 我方陷阱」；單位表顯示「靜電×3」。

## 8. 給下一個子階段的備註

- Phase 2E 到此結束（2E-1 被動、2E-2 反應技與姿態、2E-3 層數與陷阱）。2E 的所有骨架（`passive`、`reaction`、`stance`、`builder_finisher`、`trap`）都已啟用，組合器與 fuzz 涵蓋。
- 平衡階段要看的：`build_striker`／`build_tank` 沒有任何前段地圖類型；`build_trapper` 在 open_plain 勝率只有 40%；陷阱與層數的預算係數都是初始值。
- 若之後給敵人陷阱技能：隱藏規則（`visible_traps`）已經對稱，但需先解決待決定 #1。
- Phase 3 的客戶端需要自己過濾陷阱：只顯示玩家陣營的陷阱，請沿用 `visible_traps` 或 `strip_hidden_traps`。
