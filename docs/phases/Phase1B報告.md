# Phase 1B 完成報告

> 撰寫：實作者｜2026-10-17｜對應規格 `docs/phases/Phase1計畫.md` 第 1–4 節與第 6 節
>
> 本階段由兩位實作者接力完成：前一位完成 6.0 的三項修改與 6.1 的全部交付項目（`7b7ce39`～`337b9d5`，8 個 commit）後中途停止；後一位（本報告撰寫者）逐條驗收、補上缺少的測試、修正一個雷電擴散的錯誤，並撰寫本報告（`4b5344e` 之後）。

## 摘要

Phase 1B（環境與戰術）的 15 項交付全部完成：6.0 的三項 PM 決定（近戰高度差 ≤ 1、先攻平手先比敏捷再用戰鬥亂數、視線對稱）；物件與標籤、7 種表面、資料驅動的元素 × 標籤互動表（計畫 5.1 全部規則）、推擊／絆倒／互動、環境回合與 `telegraph` 預告、地圖事件、4 種天氣、反應規則與 `prompt` 暫停點（`resume`）、三種勝利條件（含失敗條件）、部署、`preview`（精確 `Fraction` 命中率與確定／可能連鎖）、4 種行為模式的效用 AI（CLI 預設改用它），以及 3 張示範地圖 `bridge_chasm`、`oil_depot`、`swamp`。驗收條件 1–7 全部通過：`uv run python scripts/check.py` 五項全過，共 451 個測試（前一位留下 436 個，本次新增 15 個）；1A 的 11 條驗收條件仍然成立。驗收時發現並修正一個錯誤：雷電沿水擴散時天氣加成被套用兩次（下雨時擴散傷害等於 +44%）。

## 驗收條件逐條結果

### 1B 驗收條件（6.2）

| # | 條件 | 結果 | 證據（測試名稱／指令與輸出摘要） |
|---|---|---|---|
| 1 | `check.py` 五項全過；1A 驗收條件仍成立 | ✅ 通過 | `uv run python scripts/check.py` → ruff check、ruff format --check、mypy、lint-imports、pytest 全部「通過」，`451 passed`，`全部檢查通過。`。1A 各條見下一張表 |
| 2a | 火焰攻擊油桶 → 摧毀並爆炸，3×3 傷害，周圍 oil 著火 | ✅ 通過 | `test_environment.py::test_fire_attack_on_oil_barrel_explodes`（爆炸半徑 1、`ObjectDestroyed(cause="explosion")`、3×3 內兩名盜賊受火焰傷害、範圍內 4 格油變成火、範圍外 (4, 4) 的油不變）；對照 `test_physical_attack_destroys_barrel_without_explosion` |
| 2b | 打斷木橋 → 橋上單位墜落；一般單位死亡，Boss 受 30% 並移到安全格 | ✅ 通過 | `test_breaking_bridge_drops_normal_unit`、`test_breaking_bridge_boss_takes_30_percent_and_moves_to_safe_tile`（80 → 56，移到 (2, 1)）、`test_attacking_bridge_until_it_breaks`、`test_burning_bridge_collapses_at_environment_turn`、`test_maneuvers.py::test_destroy_object_effect_on_bridge_drops_unit` |
| 2c | 雷電命中水中單位 → 沿相連 water 擴散 | ✅ 通過 | `test_lightning_conducts_through_connected_water`（同一片水的 (2, 1) 受傳導傷害，水外的 (2, 2) 沒有）；`test_lightning_conduct_applies_rain_bonus_only_once`（本次新增，見「補做與修正」） |
| 2d | 冰霜命中 water → ice；進入 ice 檢定，失敗倒地 | ✅ 通過 | `test_ice_freezes_water_then_slip_check`（只有被命中的格結冰；擲 3：3+2=5 < 12 → 倒地並停下；擲 10：12 通過）；`test_fire_melts_ice_and_water_extinguishes_fire` |
| 2e | 推擊 Boss 2 格 → 只移動 1 格（steadfast） | ✅ 通過 | `test_push_boss_two_tiles_moves_only_one`（`PushResisted(requested=2, distance=1)`；一般盜賊推 2 格就是 2 格） |
| 2f | 墜落傷害不超過 30% | ✅ 通過 | `test_fall_damage_from_push_is_capped`（每層 200‰、落差 3 → 40% → 上限 30）；1A 的 `test_fall_damage_capped_at_30_percent` |
| 2g | 火表面依規則蔓延，`telegraph` 與實際完全一致 | ✅ 通過 | `test_environment_turn.py::test_fire_spreads_round_by_round_and_telegraph_matches`（連續 3 輪，輪初與輪中預告都與實際環境回合事件除 `seq` 外逐筆相同）、`test_explosion_during_environment_is_telegraphed`、`test_rain_creates_puddles_and_telegraph_matches`；本次新增 hypothesis `test_property_telegraph_matches_every_environment_turn_on_demo_maps`（三張示範地圖整場對戰的每一次環境回合都與預告相同）。另以效用 AI 跑三張示範地圖種子 42（與 `trpg battle` 相同），9 次環境回合全部一致 |
| 2h | 風吹火蔓延、風吹散毒、神聖淨化毒、大地隆起與下陷 | ✅ 通過 | `test_wind_spreads_fire_along_direction_and_disperses_poison`、`test_wind_pushes_pushable_object`、`test_holy_purifies_poison_and_dispels_darkness`、`test_earth_raises_and_lowers_terrain`（上限 3、下限 0、單位隨之升降）、`test_earth_fills_chasm_under_bridge` |
| 2i | 連鎖深度超過 3 時停止並產生 `chain_limit_reached` | ✅ 通過 | `test_chain_reaction_stops_at_depth_limit`（一排 4 個油桶只爆 3 個，`ChainLimitReached(effect_kind="explode", depth=4)`）；1A 的 `test_chain_limit` |
| 3 | 反應自動觸發；prompt 暫停並由 `resume` 恢復，重播一致 | ✅ 通過 | `test_reactions.py`：`test_opportunity_attack_when_enemy_leaves`（在離開前結算）、`test_no_opportunity_attack_when_staying_adjacent_or_ranged`、`test_reaction_once_per_round`、`test_block_halves_melee_damage_and_costs_stamina`（×0.5、耐力 30 → 20）、`test_block_unless_stamina_below_threshold`、`test_prompt_reaction_pauses_and_resumes[True/False]`（`resolve`／`resume` 都不改原狀態、暫停中 `legal_actions == []`、事件 `seq` 連續）、`test_resume_without_pending_is_rejected`、`test_prompt_battle_replays_identically`（3 個種子，步驟列表含 `decision`，重播狀態與事件 JSON 相同） |
| 4 | 三種勝利條件正確判定，含失敗條件 | ✅ 通過 | `test_objectives.py`：`test_escape_victory_when_all_allies_reach_exit`、`test_escape_partial_survivors_still_win`、`test_escape_timeout_is_a_defeat`、`test_enemy_cannot_escape`、`test_defend_victory_after_rounds`、`test_defend_point_lost_at_round_end`、`test_eliminating_enemies_wins_in_any_mode`、`test_allies_wiped_out_is_a_defeat`、`test_setup_objective_overrides_map`；部署：`test_deploy_allies_in_start_zone`、`test_deploy_rejects_bad_positions` |
| 5 | 預覽一致性：最小傷害／確定連鎖與實際相符；命中率與窮舉相符 | ✅ 通過 | `test_preview.py`：`test_hit_chance_matches_exhaustive_enumeration`（含優勢）、`test_expected_damage_matches_brute_force`、`test_preview_is_pure`、`test_min_damage_and_certain_chain_match_actual_resolution`、`test_certain_explosion_chain_matches_actual`（以 `with_rolls` 固定骰值）、`test_possible_chain_includes_kill_on_max_damage`、`test_preview_move_shows_opportunity_attack`、`test_shove_preview_success_chance`；本次新增 `test_maneuvers.py::test_trip_uses_dex_contest_and_shove_uses_str` |
| 6 | 4 種行為模式在同一場景做出不同且符合定位的選擇 | ✅ 通過 | `test_ai_utility.py::test_four_profiles_choose_differently_in_the_same_scene`（同一場景：莽夫攻擊相鄰敵人、狡猾把敵人推進深淵、弓手退到高台且與敵人距離 > 2、守衛靠近受傷友方；4 個選擇互不相同）；另有 `test_cunning_detonates_barrel_near_enemies`、`test_guard_holds_defend_point`、`test_archer_shoots_from_range_instead_of_closing_in`、`test_end_turn_when_nothing_is_worth_doing`、`test_rank_follows_legal_action_order_and_is_deterministic`、`test_utility_battle_finishes_and_replays` |
| 7 | 3 張示範地圖 `--seed 42` 跑完並分出勝負，可見環境互動 | ✅ 通過 | 實際執行（rc 皆為 0，`trpg battle replay` 皆「重播驗證通過」）：`oil_depot` → 敵方勝利（4 輪、74 動作、262 事件；油桶爆炸、油著火、火勢蔓延、援軍）；`bridge_chasm` → 敵方勝利（3 輪、66 動作、187 事件；木橋著火、燒毀、盜賊掉進深淵）；`swamp` → 我方勝利（5 輪、82 動作、229 事件；雷電沿水傳導、下雨修正）。`tests/cli/test_demo_maps.py::test_demo_map_battle_has_winner_and_interactions[3 張]` 檢查勝方與互動字串，`test_demo_log_replays` 檢查紀錄重播 |

### 6.0 的三項修改

| 項目 | 結果 | 證據 |
|---|---|---|
| 近戰高度差 ≤ 1（射程 2 的長柄同樣適用；`legal_actions` 與 AI 同步） | ✅ 通過 | `test_combat.py::test_melee_height_difference_limit`（5 組：差 1 可以、差 2 不行、低打高同樣限制、匕首差 3 不行、弓不受限）、`test_reach_weapon_obeys_height_limit`；`legal_actions` 由同一個 `attack_problem` 判斷；藉機攻擊與推擊／絆倒也受同一限制（`reactions.opportunity_attacks` 用 `attack_problem`；本次新增 `test_maneuvers.py::test_maneuver_target_rules`） |
| 先攻平手：先比敏捷，仍相同用戰鬥亂數（開場一次、寫入事件） | ✅ 通過 | `test_turns.py::test_initiative_order_and_ties`（120 個種子：順序符合「總值 → 敏捷」、`InitiativeTieBroken` 事件與實際順序一致、兩名敏捷 10 的盜賊兩種先後都出現過，證明不是依 ID）、`test_initiative_tie_is_deterministic` |
| 視線對稱（加 property 測試） | ✅ 通過 | hypothesis `test_property_line_of_sight_is_symmetric`（隨機高度）、本次新增 `test_property_line_of_sight_is_symmetric_with_environment`（隨機高度 ＋ 石柱 ＋ 草叢 ＋ 黑暗表面 ＋ 濃霧距離限制）、`test_line_of_sight_asymmetric_case_is_now_blocked_both_ways` |

### 1A 驗收條件（5.3）仍成立

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `check.py` 五項全過 | ✅ | 同上，451 passed |
| 2 | 確定性、replay、hypothesis 隨機種子重播 | ✅ | `test_determinism.py`：`test_same_seed_same_battle`、`test_replay_matches`、`test_replay_from_serialized_log`、`test_property_random_seed_battle_replays`，以及 1B 新增的 `test_property_demo_maps_replay`（示範地圖：物件、表面、環境回合、反應、地圖事件）；CLI：五張地圖 `--seed 42 --log-json` 後 `trpg battle replay` 全部「重播驗證通過」；竄改偵測 `tests/cli/test_battle_cli.py` |
| 3 | 純函式 | ✅ | `test_resolve_does_not_modify_input_state`、`test_illegal_action_does_not_modify_state`、`test_run_effects_is_pure`、`test_preview_is_pure`、`test_property_demo_maps_legal_actions_resolve`（示範地圖上每個合法動作 `resolve` 後原狀態 JSON 不變）、`test_prompt_reaction_pauses_and_resumes`（`resume` 也不改原狀態） |
| 4 | 序列化往返 | ✅ | `test_state_json_round_trip_through_a_battle`、`test_actions_and_events_round_trip`、`test_battle_log_round_trip`、`test_property_demo_maps_replay`（最終狀態 `state_from_json(state_to_json(s)) == s`） |
| 5 | 判定 | ✅ | `tests/content/test_rules.py` 命中表 4 項、`test_combat.py` 的 `test_hit_rate_table_exhaustive`、優劣勢、自然 1／20、暴擊等（與 1A 報告相同） |
| 6 | 移動 | ✅ | `tests/engine/test_movement.py` 15 個測試全過 |
| 7 | 致命地形 | ✅ | `tests/engine/test_effects.py` 的 5 個致命地形測試 |
| 8 | 元素修正 | ✅ | `test_element_modifier`（10 組）、`test_damage_minimum_one_on_hit` |
| 9 | AP | ✅ | `test_ap_per_turn_and_carry`、`test_ap_shortage_is_rejected_with_reason`、`test_ap_values_come_from_rules` |
| 10 | CLI `trpg battle --map test_heights_8x8 --seed 42` | ✅ | rc=0，現在預設使用效用 AI：`我方勝利（第 4 輪結束，72 個動作，173 個事件）`；`--ai simple` 保留 1A 的簡易 AI（`test_simple_ai_weather_and_deploy_options`） |
| 11 | 不合法動作拋出 `IllegalActionError`；`legal_actions` 的每個動作都能 `resolve` | ✅ | `test_property_every_legal_action_resolves`、`test_property_arbitrary_actions_are_legal_or_rejected`、`test_property_demo_maps_legal_actions_resolve`；1B 動作的錯誤訊息另有單元測試（「目標已經倒地」「無法推動」「物件必須相鄰」「找不到物件」「高度差過大」「結算暫停中」「目前沒有等待中的決定」……） |

## 本次補做與修正

前一位實作者的 8 個 commit 內容完整、檢查全過，沒有重做。逐條核對時發現以下缺漏，依邏輯分成 3 個 commit：

1. **`4b5344e` 補上沒有測試的交付項目**（`tests/engine/test_maneuvers.py`，12 個測試）：`Trip`（敏捷對抗、成功倒地、失敗不倒地、已倒地不可再絆倒、消耗 1 AP）、`Shove` 對抗失敗不推動、Trip 比敏捷／Shove 比力量（以 `preview` 成功率與 `maneuver_rolled` 的修正值驗證）、推擊／絆倒的相鄰與高度差限制、`Interact`（推木箱 1 格、把油桶推進深淵 → 掉落摧毀、不可推動／不相鄰／不存在／AP 不足的拒絕），以及 `create_obstacle`、`spawn_unit`、`destroy_object` 三種效果直接放進佇列的測試。這些功能原本都已實作，但測試中完全沒有出現 `Trip`、`Interact`、`CreateObstacleEffect`、`SpawnUnitEffect`、`DestroyObjectEffect`。
2. **`380d033` 補上兩個屬性測試**：視線在 1B 的阻擋來源（石柱、黑暗、濃霧距離）下仍然對稱；示範地圖整場對戰中，每一次環境回合都與本輪最後一個 `EndTurn` 之前的 `telegraph` 完全相同。
3. **`4df521e` 修正雷電擴散的天氣重複計算**：擴散傷害以主要目標「實際受到的傷害」為基準（已含下雨 +20%），處理器卻又乘一次天氣，`swamp` 種子 42 中主要目標受 6／10 點時，水中其他單位受 7／12 點。`DamageEffect` 新增 `apply_weather`（預設 `True`），擴散效果設為 `False`；修正後擴散傷害等於主要目標的傷害（同抗性時）。新增回歸測試 `test_lightning_conduct_applies_rain_bonus_only_once`（修正前失敗：`assert 1200 == 1000`）。`swamp --seed 42` 的結果因此由「7 輪、87 動作」變為「5 輪、82 動作」，仍是我方勝利。

## 實際執行的驗證指令

```bash
cd /home/claude/LLM-MMO-TRPG
export NO_PROXY=localhost no_proxy=localhost   # 本工作區每個指令前都要設定

# 1) 安裝與一鍵檢查
uv sync
uv run python scripts/check.py                 # → 451 passed，全部檢查通過。

# 2) 1B 的情境測試群組
uv run pytest -q tests/engine/test_environment.py tests/engine/test_environment_turn.py \
  tests/engine/test_reactions.py tests/engine/test_objectives.py tests/engine/test_preview.py \
  tests/engine/test_ai_utility.py tests/engine/test_maneuvers.py tests/cli/test_demo_maps.py
uv run pytest -v tests/engine/test_combat.py tests/engine/test_turns.py \
  -k "melee or initiative or line_of_sight or reach"   # 6.0 的三項修改

# 3) 示範地圖與重播
for m in oil_depot bridge_chasm swamp test_heights_8x8 test_flat_6x6; do
  uv run trpg battle --map $m --seed 42 --log-json /tmp/$m.json | grep '^勝方'
  uv run trpg battle replay /tmp/$m.json
done
uv run trpg map show oil_depot

# 4) 效能基準
uv run python scripts/bench_battle.py --repeat 40
```

## 效能基準

`uv run python scripts/bench_battle.py --repeat 40`（本工作區，Python 3.12.3；簡易 AI 情境取 40 次中位數、效用 AI 情境取 3 次中位數；預設陣容、種子 42）。本工作區的計時有 ±30% 左右的波動（同一指令連跑兩次，10 輪情境的重播時間曾出現 33 ms 與 48 ms）。

| 情境 | 輪數 | 動作數 | 事件數 | 整場時間（含 AI） | 重播時間（只有 `resolve`） | 每個 `resolve` 平均 | 每個動作平均（含 AI） |
|---|---|---|---|---|---|---|---|
| 1A 示範戰鬥（簡易 AI，`test_heights_8x8`） | 5 | 89 | 209 | 26.2 ms | 14.9 ms | 168 µs | 294 µs |
| 1A 10 輪戰鬥（簡易 AI，HP ×5，`max_rounds=10`） | 10 | 223 | 459 | 58.5 ms | 28.8 ms | 129 µs | 262 µs |
| 效用 AI：`test_heights_8x8` | 4 | 72 | 173 | 1157.5 ms | 18.7 ms | 260 µs | 16.1 ms |
| 效用 AI：`bridge_chasm` | 3 | 66 | 187 | 1147.4 ms | 15.5 ms | 234 µs | 17.4 ms |
| 效用 AI：`oil_depot` | 4 | 74 | 262 | 2068.9 ms | 16.4 ms | 221 µs | 28.0 ms |
| 效用 AI：`swamp` | 5 | 82 | 229 | 1598.7 ms | 16.0 ms | 196 µs | 19.5 ms |

**與 1A 比較**（1A 報告：示範戰鬥 4 輪／77 動作、20.6 ms、每個 `resolve` 102 µs、每個動作 268 µs；10 輪戰鬥 224 動作、58.3 ms、每個 `resolve` 108 µs、每個動作 260 µs）：

- **同一情境的 `resolve` 變慢約 20–60%**（102 → 168 µs、108 → 129 µs）：每次 `resolve` 多了物件與表面的狀態複本、互動表觸發函式、反應檢查、勝利條件檢查；每輪多一次環境回合。整場簡易 AI 的時間大致持平（10 輪 58.3 → 58.5 ms）。
- **1A 示範戰鬥的內容改變了**（4 輪／77 動作 → 5 輪／89 動作）：先攻平手改用戰鬥亂數、近戰高度差限制都會改變亂數消耗與走位，種子 42 的戰局因此不同，不是效能退化。
- **效用 AI 是新的瓶頸**：每個動作 16–28 ms，比簡易 AI 慢 55–95 倍；一場 1–2 秒。原因是對每個合法動作（每個可達格一個 `Move`，常有 30–60 個）各跑兩次 `preview`（最少／最多後果的完整引擎模擬）再評估位置價值。純 `resolve` 的重播時間（15–19 ms／場）仍與 1A 同級。
- 換算：效用 AI 單核心約 0.5–1 場／秒，十萬場約 30–55 小時；簡易 AI 約 40 場／秒。Phase 2 的大量模擬需要先決定用哪一種 AI（見「待 PM 決定」第 1 點）。
- 效用 AI 的批次結果（本次另外量測，種子 0–19，`max_rounds=30`）：我方勝率 `bridge_chasm` 17/20、`oil_depot` 4/20、`swamp` 12/20、`test_heights_8x8` 17/20；平均輪數 4.6–5.2（最短 2、最長 8），落在 PM 給的「一般遭遇 4–6 輪」目標附近。

## 與規格的差異

（前一位實作者的決定，經本次核對後整理；本次修改的部分另外標示。）

1. **環境回合的亂數不取自 `rng_state`**，而是 `Rng(state.seed).fork(f"environment:{round}")`（由種子與輪數衍生）。如此雨天水窪等隨機結果不受玩家本輪動作消耗多少亂數影響，`telegraph` 才能在輪初就準確預告（`test_environment_rng_is_independent_of_player_actions`）。仍然完全由「初始狀態 ＋ 動作列表」決定，重播一致。
2. **效果類型比規格多 4 種**：`element_touch`（元素觸及一格，互動表的入口）、`explode`、`ignite_object`、`change_tile`（地圖事件的地形變化）。規格列的 1B 八種效果全部都有。
3. **攻擊物件一律命中**：不擲命中骰、不暴擊；物件必須帶 `breakable`。傷害 ＝ 武器骰 ＋ 固定值 ＋ 屬性 × 0.3（套天氣，不套元素修正）。
4. **新增內容**：物件 `earth_wall`（`create_obstacle` 的預設障礙物）；武器 `lightning_staff`、`frost_staff`；單位範本 `hero_stormcaller`（`swamp` 的我方法師）；`content/reactions.yaml`、`content/ai_profiles.yaml`。
5. **`core.yaml` 新增鍵**：`melee_height_limit`（1）、`melee_height_limit_max_range`（2）、`maneuver_ap_cost`（1）、`interact_ap_cost`（1）、`shove_distance`（1）、`steadfast_push_permille`（500）、`ability_mod_base`／`ability_mod_divisor`（10／2）、`reactions_per_round`（1）、`default_stamina`（30）、`base_sight_range`（24，曼哈頓距離；濃霧 ×50% → 12）、`concealed_ranged_max_distance`（2）、`burning_object_rounds`（1）。
6. **地圖檔新增選用欄位**：`objective`、`weather`、`encounter`（6.0 決定的預設陣容）、`events`。地圖原有的表面預設永久；由效果產生的表面使用 `surfaces.yaml` 的 `duration`（火 2、冰 3 → 到期變水、毒／聖光／黑暗 3；油與水永久）。
7. **數值由實作者擬定**：油桶 HP 8、爆炸 2d6 火焰（切比雪夫半徑 1）、木橋 HP 12、石柱 HP 60、木箱 HP 15；冰面檢定 `d20 + 敏捷修正 ≥ 12`；毒 1d4、聖光 1d4；下雨每輪 2 個水窪；夜晚使隱蔽目標超過 1 格就無法被遠程選為目標。
8. **戰鬥紀錄格式升為 `trpg-battle-log/2`**：`actions` 改為步驟列表（動作或 `decision`），1A 的 `/1` 紀錄無法以 1B 引擎重播。`BattleState.tiles` 由 tuple 改為 list。
9. **CLI**：`trpg battle` 預設改用效用 AI，`--ai simple` 保留 1A 的 AI；新增 `--weather`、`--deploy "x,y;x,y"`；預設陣容取地圖的 `encounter`；每輪印出環境預告。
10. **（本次）`DamageEffect` 新增 `apply_weather` 欄位**（預設 `True`），見「本次補做與修正」第 3 點。

## 待 PM 決定

依重要性排序。

1. **效用 AI 的速度與 Phase 2 模擬**：效用 AI 一場 1–2 秒（每個動作 16–28 ms），十萬場單核心約 30–55 小時。可選擇：Phase 2 模擬用簡易 AI（快 55–95 倍，但不會利用環境）、或先最佳化效用 AI（例如 `Move` 只評估少數候選格、只跑一次 `preview`、快取位置價值、多處理程序）。
2. **steadfast 讓 `Shove` 永遠推不動 Boss**：規格要求「推擊距離減半（無條件捨去）」，`Shove` 只推 1 格 → 0 格。目前 `Shove` 對 Boss 仍列在 `legal_actions` 中，會擲骰、消耗 1 AP，但只產生 `push_resisted`（AI 因預覽沒有收益而不會選）。若希望基本推擊對 Boss 有用，可改成「最少 1 格」或「減半後無條件進位」；若是刻意免疫，建議從 `legal_actions` 移除以免玩家浪費 AP。
3. **雷電擴散的基準傷害**：目前以主要目標「實際受到的傷害」為基準（含主要目標的元素修正與格擋），再對每個擴散目標套用各自的元素修正；擴散會打到水中 **所有** 單位（包括友方與站在水中的攻擊者自己，只排除主要目標）。本次只修正了天氣重複計算。是否改以「元素修正前的原始傷害」為基準、是否排除友方，請決定。
4. **示範地圖的平衡**：效用 AI 20 個種子的我方勝率 `oil_depot` 只有 4/20（4 名敵人 ＋ 第 3 輪援軍，我方法師開場常把油桶連環引爆但自己很快倒下），`bridge_chasm` 17/20、`swamp` 12/20。種子 42 的 `oil_depot` 與 `bridge_chasm` 都是敵方勝利。是否在 1B 調整，或留到 Phase 2 以模擬調整？
5. **易爆物的觸發條件**：油桶只要被任何火焰觸及就爆炸（即使 HP 還沒歸零，例如 `oil_depot` 中 HP 8 → 2 仍然爆炸）；被物理攻擊打爆 **不會** 爆炸（只摧毀）。這是照計畫 5.1「fire｜explosive → 爆炸」的字面實作。是否要「任何原因摧毀都爆炸」？
6. **表面出現在單位腳下時不觸發進入效果**：例如爆炸把油點成火、冰霜把水結成冰時，站在那一格的單位不會立即燃燒或滑倒，要等自己回合開始（火）或下次走進來（冰）才受影響。
7. **守衛（guard）行為模式沒有任何內容單位使用**：範本未指定 `ai_profile` 時，近戰武器預設 `brute`、遠程預設 `archer`；只有 `hero_mage`、`hero_stormcaller` 指定 `cunning`。Boss 也是 `brute`。是否要讓某些敵人（例如守點地圖的守衛、Boss）使用 `guard`？
8. **地圖上預先放置的聖光表面治療雙方**：`holy` 的 `allies_only` 以表面的擁有隊伍判斷；地圖上原有的表面沒有擁有者，因此治療所有非 `undead` 單位。
9. **夜晚的「感知判定重要性提高」未實作**：Phase 1 沒有感知判定；目前夜晚只讓隱蔽更強（超過 1 格就不能被遠程選為目標）。
10. **`Interact`／`Shove` 在推不動時仍是合法動作**：例如木箱後面是牆、Boss 的 steadfast；動作會消耗 AP 並產生 `effect_fizzled`／`push_resisted`。另外 `Interact` 推物件不檢查行動者與物件的高度差。
11. **產生的單位排在先攻順序最後**（不擲先攻），ID 依序為 `unit_000N`；地圖事件產生在被佔用或不可站立的格子時，改到最近的空格（同距依 `y`、`x`）。
12. **隱蔽的來源**：站在黑暗表面或草叢（`conceal` 標籤）中視為隱蔽；`concealed` 狀態已放入 `statuses.yaml`，但 1B 沒有效果會施加它（留給 Phase 2 技能）。
13. **反應的範圍**：藉機攻擊只在主動移動時觸發（推擊等強制位移不觸發）；格擋只對普攻（含藉機攻擊）有效，爆炸、擴散、表面等環境傷害不能格擋。
14. **CLI 統計**：結算表的「命中/攻擊」不計入攻擊物件（`oil_depot` 中連續引爆 3 個油桶的法師顯示 `0/0`）。

## 給下一階段的備註

（給 Phase 1C／Phase 2 實作者）

- **API**：`trpg.engine` 匯出 `begin_battle`／`start_battle`、`legal_actions`、`resolve`、`resume`、`preview`、`telegraph`、`deploy_allies`、`deployment_tiles`、`build_setup`，動作 `Move`／`Attack`（`target_id` 或 `target_object_id`）／`Defend`／`Shove`／`Trip`／`Interact`／`EndTurn`，以及 `Decision`。
- **模組**：`effects/world.py`（環境效果處理器）、`interactions.py`（讀 `interactions.yaml` 的觸發函式；`touch_outcomes` 是互動表的單一入口）、`reactions.py`（反應、`PauseForDecision`）、`environment.py`（環境回合、天氣、地圖事件、`telegraph`）、`objectives.py`、`preview.py`、`ai/utility.py`。
- **互動表**：新的元素 × 標籤規則只要加進 `content/interactions.yaml`（`trigger: element | surface_created`、`target: surface | object | unit`、`then` 的 `op`）。新的 `op` 需要在 `content/environment.py` 的 `InteractionOutcome` 與 `interactions._outcome_effects` 各加一個分支。
- **暫停點**：`prompt` 反應暫停時，`BattleState.pending` 存「暫停前的狀態 JSON ＋ 動作 ＋ 已做的決定」；`resume` 以全部決定從頭重新結算同一個動作，再只回傳暫停之後的事件。結算必須確定性，這個做法才成立；新增會暫停的東西時沿用 `ctx.decisions`。
- **預覽**：`preview` 在狀態複本上跑兩次（`ctx.preview = "min"`／`"max"`）；技能系統新增會擲骰的地方時，要依 `ctx.preview` 決定預覽時的骰值（參考 `reactions.perform_unit_attack`、`battle._contest`），否則預覽會消耗亂數而與實際不一致。
- **環境亂數**：環境回合用 `environment.environment_rng(state)`，不要改用 `ctx.rng`，否則 `telegraph` 會與實際不符（`test_property_telegraph_matches_every_environment_turn_on_demo_maps` 會抓到）。
- **掩護（半掩護、牆壁）屬於 Phase 1C**，本階段沒有實作。視線目前只有「看得到／看不到」；`has_line_of_sight` 兩個方向都畫線，掩護判定若也依賴線上的格子，請同樣保持對稱。
- **效能**：效用 AI 是目前最大的成本（見「效能基準」）；`resolve` 本身約 130–260 µs。
- **天氣傷害修正**：`DamageEffect.apply_weather=False` 用於「基準已含天氣」的衍生傷害（目前只有雷電擴散）。

## 附錄：`trpg battle --map oil_depot --seed 42` 輸出節錄

```text
戰鬥開始：油庫（10×10），種子 42
……
行動順序：法師 → 盜賊2 → 戰士 → 盜賊1 → 弓手 → 盜賊頭目 → 盜賊弓手

=== 第 1 輪 ===
    0  1  2  3  4  5  6  7  8  9
 ……
 3  0.  0C  0.  0.  0.  0&  0.o 0.o 0&  0.
 4  0A  0.  0.  0.  0.  0.o 0ao 0co 0.o 0.
 5  0B  0.  0.  0.  0.  0.o 0bo 0do 0.o 0.
 6  0.  0.  0.  0.  0.  0&  0.o 0.o 0&  0.
 ……
  圖例：[ 木箱、& 油桶、o 油（表面）
— 法師 的回合（AP 3，移動 5）
  法師 攻擊 油桶 (5, 3)
    油桶 受到 10 點火焰傷害［骰 6］，HP 8 → 0
  ＊ 油桶 (5, 3) 爆炸了！
  ＊ 油桶 (5, 3) 炸毀！
  (6, 3) 的油變成了火焰
  (5, 4) 的油變成了火焰
  (6, 4) 的油變成了火焰
    盜賊1 受到 7 點爆炸火焰傷害［骰 1+6］，HP 30 → 23
  法師 從 (1, 3) 移動到 (5, 2)（消耗 5 移動）
  法師 攻擊 油桶 (8, 3)
  ……
    盜賊弓手 受到 5 點爆炸火焰傷害［骰 3+1］（元素修正 ×1.25），HP 26 → 21
  ……
— 盜賊2 的回合（AP 3，移動 5）
  盜賊2 獲得狀態「燃燒」（2 回合）
……
～ 環境回合 ～
  (7, 5) 的油變成了火焰
  (8, 5) 的油變成了火焰
  (7, 6) 的油變成了火焰

=== 第 2 輪 ===
  ……
  環境預告：(6, 3) 火焰→無；(7, 3) 火焰→無；……；(8, 6) 油桶將會爆炸；下一輪結束時：援軍
……
～ 環境回合 ～
  (6, 3) 的火焰消失了
  ……
  ＊ 油桶 (8, 6) 爆炸了！
  ＊ 油桶 (8, 6) 炸毀！
……
～ 環境回合 ～
  (7, 5) 的火焰消失了
  (8, 5) 的火焰消失了
  (7, 6) 的火焰消失了
  地圖事件：援軍出現！
  盜賊3 出現在 (9, 0)
……
勝方：敵方勝利（第 4 輪結束，74 個動作，262 個事件）
```

`bridge_chasm` 的節錄（火焰點燃木橋 → 下一次環境回合燒毀 → 橋上的盜賊掉進深淵）：

```text
  法師 攻擊 盜賊1：d20=13 修正 +0 熟練 +2 = 15（目標 11）→ 命中
    盜賊1 受到 7 點火焰傷害［骰 3］，HP 19 → 12
  (5, 2) 出現了火焰
  木橋 (5, 2) 著火了（1 次環境回合後燒毀）
……
～ 環境回合 ～
  ＊ 木橋 (5, 2) 燒毀！
  (5, 2) 的火焰消失了
  盜賊1 掉進了深淵！
……
  ＊ 盜賊1 倒下了！
```
