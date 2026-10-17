# Phase 1C 完成報告

> 撰寫：實作者｜2026-10-17｜對應規格 `docs/phases/Phase1C計畫.md`（含第 2.5 節 10 項 1B 驗收後的 PM 決定）

## 摘要

Phase 1C（掩護系統與牆壁）全部完成：視線擴充為 **全掩護（牆壁、`blocks_sight`、高度）／半掩護（`half_cover` 物件，命中 −2）／隱蔽（劣勢）** 三層，半掩護依規格 3.2 的四個條件確定性判定，`preview` 與戰鬥紀錄都會顯示懲罰與來源物件；新增地形 `wall`、物件 `low_wall`、`fallen_log`，`crate` 與 `oil_barrel` 加上 `half_cover`；效用 AI 加入掩護考量（弓手偏好有掩護的射擊位置；狡猾模式把敵人推離掩護或打掉掩護物）；三張示範地圖加入牆壁與半掩護，新增示範地圖 `ruined_fort`。第 2.5 節 10 項決定全部實作並有測試，其中效用 AI 的每個動作（含 AI）中位數由 1B 的 11.9–28.4 ms 降到 **2.1–3.6 ms**（同一批 1B 地圖 2.1–3.5 ms，1C 新地圖 2.3–3.6 ms），四張示範地圖以效用 AI 跑種子 0–19 的我方勝率為 **40%–60%**、平均輪數 **4.80–5.75**。`uv run python scripts/check.py` 五項全過，共 **529 個測試**（1B 結束時 451 個）；1A、1B 的驗收條件仍然成立。

本階段 commit（`git log --oneline e24be78..HEAD`，不含本報告）：

```text
7230463 Report wall surfaces as solid_terrain fizzles
9004f8d Add ruined_fort, shieldbearer, and walls and cover on demo maps
790cc05 Cut utility AI cost further
aee57c3 Speed up the utility AI and add cover-aware scoring
ec1a9bb Apply Phase 1B review decisions to the engine
4f32fee Add half cover, wall terrain and cover objects
```

## 驗收條件逐條結果

### 1C 驗收條件（第 4 節）

| # | 條件 | 結果 | 證據（測試名稱／指令與輸出摘要） |
|---|---|---|---|
| 1 | `check.py` 五項全過；1A、1B 驗收條件仍成立 | ✅ 通過 | `uv run python scripts/check.py` → ruff check、ruff format --check、mypy、lint-imports、pytest 全部「通過」，`529 passed`，`全部檢查通過。`。1A、1B 各條見後面兩張表 |
| 2a | 遠程攻擊箱子後方的目標 → 命中 −2；從側面攻擊 → 無懲罰 | ✅ 通過 | `tests/engine/test_cover.py::test_ranged_attack_behind_crate_has_minus_two`（固定 d20=10：10+0+2−2=10 → 失手，`AttackRolled.cover == -2`、`cover_object_id == obj_0001`）；`test_cover_depends_on_direction`（7 組：正後方、兩種斜向有掩護；正上方、正下方（內積 0）、另一側（內積 < 0）沒有；命中率 50% 對 60%）；`test_side_attack_has_no_penalty_in_actual_roll`（同骰值 12 → 命中、`cover == 0`） |
| 2b | 攻擊者站在高 1 層以上 → 無視半掩護 | ✅ 通過 | `test_attacker_above_cover_ignores_it`（攻擊者高 1：與掩護物同高，仍有掩護，另有高打低 +2；高 2、3：無視）；`test_cover_height_uses_cover_tile_height`（木箱放在高 1 的格子：攻擊者高 2 仍有掩護，高 3 才無視） |
| 2c | 近戰攻擊 → 無視半掩護 | ✅ 通過 | `test_melee_ignores_half_cover`（射程 2 的長柄隔著木箱攻擊 → 無掩護，同位置換成弓 → 有；相鄰近戰在幾何上不可能有掩護） |
| 2d | 箱子被摧毀後 → 半掩護消失 | ✅ 通過 | `test_destroyed_crate_no_longer_covers`（`DamageObjectEffect` 打掉木箱後命中率回到 60%） |
| 2e | 半掩護 ＋ 隱蔽同時生效 | ✅ 通過 | `test_half_cover_and_concealment_stack`（目標站在草叢中、木箱在兩者之間：命中率 (10/20)² = 1/4；實際擲骰 `advantage == "disadvantage"` 且 `cover == -2`） |
| 2f | 牆壁阻擋移動與視線 | ✅ 通過 | `test_wall_blocks_movement`（「無法進入牆壁」、`legal_actions` 不含牆格）、`test_wall_blocks_sight_regardless_of_height`（兩個方向都看不到，站在高 3 的高台也看不過牆）、`test_wall_stops_pushed_units_and_objects`（推擊與推物件撞牆停下，`move_blocked: obstacle`）、`test_map_legend_hash_is_wall_and_connectivity_considers_walls`（圖例 `#` = wall；整排牆封死時連通性檢查失敗；牆上不能放物件或表面）；其他：`test_units_do_not_provide_cover`、`test_cover_objects_have_half_cover_tag[4 種]`、`test_new_object_tags`、`test_penalty_comes_from_core_rules`、`test_wall_terrain_definition` |
| 3 | `preview` 顯示半掩護懲罰與來源物件，命中率包含它 | ✅ 通過 | `test_ranged_attack_behind_crate_has_minus_two`：`Preview.cover`（`penalty=2`、`object_id`、`kind="crate"`、`pos=(2, 2)`）、`Preview.notes == ("半掩護 −2：木箱 (2, 2)",)`、`hit_chance == 1/2`；`test_penalty_comes_from_core_rules`（懲罰改 3 → 9/20）；`test_battle_log_shows_cover_source`（紀錄中出現「半掩護 -2」與「命中 −2：木箱掩護」） |
| 4 | AI：弓手選有掩護的等價位置；狡猾模式推擊掩護後的敵人或攻擊掩護物 | ✅ 通過 | `tests/engine/test_ai_utility.py::test_archer_prefers_covered_firing_position`（兩格距離、視線、高度相同，沒掩護的 (2, 4) 在合法動作順序中排前面；弓手選 (4, 4)；把 `cover` 權重設 0 時選 (2, 4)）；`test_cunning_shoves_enemy_out_of_cover`（狡猾選推擊、莽夫選攻擊，推擊分數較高）；`test_cunning_attacks_cover_object_when_it_can_break_it`（木箱 HP 2 → 狡猾弓手先打木箱；木箱 HP 15 打不掉 → 直接射盜賊） |
| 5 | `trpg battle --map ruined_fort --seed 42` 分出勝負，紀錄看得到半掩護 | ✅ 通過 | 實際執行 rc=0：`勝方：敵方勝利（第 5 輪結束，86 個動作，210 個事件）`，「命中 −2：」出現 12 次（節錄見附錄）；`trpg battle replay` → `重播驗證通過：86 個動作、210 個事件`。`tests/cli/test_demo_maps.py::test_demo_map_battle_has_winner_and_interactions[ruined_fort]` 檢查「半掩護 -2」「命中 −2：矮牆掩護」 |
| 6 | 重播與確定性測試仍通過 | ✅ 通過 | `test_determinism.py` 全部通過，`test_property_demo_maps_replay`、`test_property_demo_maps_legal_actions_resolve` 擴充為四張示範地圖；`test_environment_turn.py::test_property_telegraph_matches_every_environment_turn_on_demo_maps` 擴充為四張地圖；`tests/engine/test_demo_balance.py::test_utility_demo_battle_replays[4 張]`（效用 AI 種子 42 重播一致）；CLI 六張地圖 `--log-json` 後 `trpg battle replay` 全部「重播驗證通過」 |
| 7 | 第 2.5 節 10 項皆實作並有測試；AI 效能達標；四張地圖勝率與輪數符合範圍 | ✅ 通過 | 見下一張表、「效能基準」與「示範地圖平衡」 |

### 第 2.5 節的 10 項 PM 決定

| # | 決定 | 結果 | 實作與證據 |
|---|---|---|---|
| 1 | 效用 AI 最佳化：四張示範地圖「每個動作含 AI」中位數 ≤ 5 ms；N 放 `ai_profiles.yaml`；行為仍通過既有 AI 測試 | ✅ | 中位數 2.27–3.65 ms（`scripts/bench_battle.py`，見「效能基準」）。`ai_profiles.yaml` 的 `move_candidates: 6`。既有 9 個 AI 測試全部通過，另有 `test_fast_move_scores_match_full_preview[4 張]`（沒有風險的移動用虛擬分數，與完整 `preview` 分數完全相同；有風險者跑完整預覽）、`test_pruned_ai_matches_exhaustive_choice_on_demo_scene`（4 種模式的選擇與「完整評分所有動作」相同）、`test_state_clone.py`（快速複本涵蓋所有欄位） |
| 2 | steadfast 讓 Shove 距離為 0 → 不列入 `legal_actions`，resolve 拋出中文 `IllegalActionError`；技能推擊 0 格只是不移動 | ✅ | `battle.shove_problem`；`test_phase1c_decisions.py::test_shove_on_steadfast_boss_is_illegal`（「推不動：盜賊頭目 不為所動（推擊距離減半後為 0 格）」；推擊距離改 2 時合法）、`test_skill_push_of_zero_tiles_just_does_not_move`（`PushResisted(requested=1, distance=0)`、沒有移動事件） |
| 3 | 雷電擴散：範圍為水中所有單位（含友方與攻擊者）；基準為主要目標套用自身抗性與格擋之前的傷害，各自套用元素修正 | ✅ | `DamageDealt.base_amount`（暴擊骰與天氣之後、元素修正與格擋之前）；`test_conduct_base_is_damage_before_primary_resistance`（主要目標抗性 50% 受 5，擴散基準 10：一般盜賊 10、雷電弱點 15、友方戰士 10、施法者自己 8）、`test_conduct_base_ignores_block_multiplier_and_includes_weather`（主要目標格擋 ×0.5 受 5，擴散仍以 10 為基準；下雨 +20% 只算一次） |
| 4 | 示範地圖平衡：20 個種子我方勝率 35%–65%、平均 4–6 輪 | ✅ | 40%／60%／50%／55%，4.80–5.75 輪（見「示範地圖平衡」）；`tests/engine/test_demo_balance.py::test_demo_map_win_rate_and_length[4 張]`、`scripts/sim_demo_maps.py` |
| 5 | 油桶：火焰觸及即爆炸；非火焰傷害打破時漏油（該格與四方向相鄰格） | ✅ | `objects.yaml` 的 `spill: {surface: oil}` ＋ `object_destroyed` 觸發；`test_non_fire_damage_breaking_barrel_spills_oil`（5 格變油、漏到火上保持火焰、之後可被點燃）、`test_fire_touching_barrel_still_explodes`（爆炸不漏油）、`test_barrel_falling_into_chasm_does_not_spill`、`test_spill_and_surfaces_never_land_on_walls`；1B 的 `test_physical_attack_destroys_barrel_without_explosion` 依新規則更新 |
| 6 | 表面在單位腳下建立或改變時立即觸發進入效果，順序依單位 ID | ✅ | `Ctx.surface_entries` ＋ 效果佇列清空前依單位 ID 觸發；`test_explosion_ignites_oil_under_unit_and_burns_immediately`、`test_freezing_water_under_unit_triggers_slip_check`（擲 2 → 倒地；擲 15 → 通過）、`test_surface_entries_resolve_in_unit_id_order`（格子順序 (0,0)→(2,0)，檢定順序 unit_0002→unit_0003）、`test_fire_spreading_onto_unit_at_environment_turn_burns_and_is_telegraphed`（環境回合火勢蔓延到腳下立即燃燒，且與預告一致） |
| 7 | 新增 `bandit_shieldbearer`（持盾、高護甲、守衛），至少一張示範地圖使用 | ✅ | `content/units/bandit_shieldbearer.yaml`（護甲 6、格擋對遠程也有效、`ai_profile: guard`），用於 `swamp`；`tests/cli/test_demo_maps.py::test_shieldbearer_uses_guard_profile_and_appears_on_a_demo_map`；`swamp --seed 42` 紀錄中「盜賊盾衛」出現 21 次 |
| 8 | 預先放置的聖光治療雙方 | ✅（接受） | 不需修改；1B 的 `test_holy_surface_heals_living_and_hurts_undead` 仍通過 |
| 9 | 環境回合亂數由種子與輪數衍生 | ✅（接受） | 不需修改；`test_environment_rng_is_independent_of_player_actions` 仍通過 |
| 10 | 推不動（被擋、出界、距離 0）時 Interact／Shove 不列入 `legal_actions`；Interact 高度差 ≤ 1 | ✅ | `battle.shove_problem`、`interact_problem`（`core.yaml` 新增 `interact_height_limit: 1`）；`test_blocked_shove_is_illegal[5 組]`（木箱、牆、較高、有單位、出界）、`test_shove_into_chasm_is_still_legal`、`test_blocked_interact_is_illegal[5 組]`（含「高度差過大：相差 2 層」）、`test_interact_height_difference_of_one_is_allowed`；`resolve` 對同樣的動作拋出相同的中文原因，`legal_actions` 與 `resolve` 保持一致 |

### 1B 驗收條件（Phase1計畫 6.2）仍成立

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `check.py` 五項全過 | ✅ | 同上，529 passed |
| 2 | 環境互動情境（油桶爆炸、斷橋、雷電擴散、結冰滑倒、推 Boss、墜落上限、火勢與預告、風／神聖／大地、連鎖上限） | ✅ | `test_environment.py`、`test_environment_turn.py` 全部通過（物理打破油桶一條依決定 #5 更新為漏油；`test_push_boss_two_tiles_moves_only_one` 仍是推擊效果 2 格 → 1 格） |
| 3 | 反應與暫停點 | ✅ | `test_reactions.py` 全部通過 |
| 4 | 勝利條件 | ✅ | `test_objectives.py` 全部通過 |
| 5 | 預覽一致性 | ✅ | `test_preview.py` 全部通過（預覽改為「沒有分歧點時只模擬一次」後，`test_min_damage_and_certain_chain_match_actual_resolution` 等仍相同） |
| 6 | 4 種行為模式做出不同選擇 | ✅ | `test_four_profiles_choose_differently_in_the_same_scene` 等 9 個既有 AI 測試通過 |
| 7 | 示範地圖 `--seed 42` 分出勝負並可見環境互動 | ✅ | `bridge_chasm` 我方勝利（6 輪、99 動作；木橋燒毀、掉進深淵、矮牆掩護）、`oil_depot` 我方勝利（6 輪、89 動作；爆炸、油著火）、`swamp` 我方勝利（4 輪、69 動作；傳導雷電、下雨修正）；`test_demo_map_battle_has_winner_and_interactions[4 張]` |

### 1A 驗收條件（Phase1計畫 5.3）仍成立

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `check.py` | ✅ | 同上 |
| 2 | 確定性、replay、hypothesis | ✅ | `test_determinism.py` 全部通過；CLI 重播六張地圖全部通過；竄改偵測 `tests/cli/test_battle_cli.py` |
| 3 | 純函式 | ✅ | `test_resolve_does_not_modify_input_state`、`test_preview_is_pure`、`test_rank_follows_legal_action_order_and_is_deterministic`（AI 不修改狀態）、`test_property_demo_maps_legal_actions_resolve`（四張示範地圖） |
| 4 | 序列化往返 | ✅ | `test_state_json_round_trip_through_a_battle`、`test_property_demo_maps_replay`；新的 `test_state_clone.py::test_clone_is_independent_and_equal` |
| 5–9 | 判定、移動、致命地形、元素修正、AP | ✅ | `test_rules.py`、`test_combat.py`、`test_movement.py`、`test_effects.py`、`test_turns.py` 全部通過 |
| 10 | `trpg battle --map test_heights_8x8 --seed 42` | ✅ | rc=0，`我方勝利（第 4 輪結束，72 個動作，173 個事件）`；`--ai simple`：`敵方勝利（第 5 輪結束，89 個動作，209 個事件）`（與 1B 相同） |
| 11 | 不合法動作拋出錯誤；`legal_actions` 每個動作都能 `resolve` | ✅ | `test_property_every_legal_action_resolves`、`test_property_arbitrary_actions_are_legal_or_rejected`、`test_property_demo_maps_legal_actions_resolve` |

## 實際執行的驗證指令

```bash
cd /home/claude/LLM-MMO-TRPG
export NO_PROXY=localhost no_proxy=localhost   # 本工作區每個指令前都要設定

# 1) 安裝與一鍵檢查
uv sync
uv run python scripts/check.py                 # → 529 passed，全部檢查通過。

# 2) 1C 的測試群組
uv run pytest -q tests/engine/test_cover.py tests/engine/test_phase1c_decisions.py \
  tests/engine/test_ai_utility.py tests/engine/test_state_clone.py \
  tests/engine/test_demo_balance.py tests/cli/test_demo_maps.py

# 3) 示範地圖與重播
for m in ruined_fort bridge_chasm oil_depot swamp test_heights_8x8 test_flat_6x6; do
  uv run trpg battle --map $m --seed 42 --log-json /tmp/$m.json | grep '^勝方'
  uv run trpg battle replay /tmp/$m.json
done
uv run trpg map show ruined_fort

# 4) 效能基準與平衡
uv run python scripts/bench_battle.py --repeat 40 --utility-repeat 5
uv run python scripts/sim_demo_maps.py         # 四張示範地圖 × 種子 0–19
```

## 效能基準

`uv run python scripts/bench_battle.py --repeat 40 --utility-repeat 5`（本工作區，Python 3.12.3，2 核心；預設陣容、種子 42）。新增「每個動作中位數（含 AI）」欄位：以 `run_battle` 的 `on_step` 量測每一步（AI 決策 ＋ `resolve`；只剩結束回合時自動結束、不呼叫 AI 的步驟也算一步），5 次重複的所有步驟合併取中位數。本工作區的計時波動約 ±30%（同一指令連跑，`swamp` 的中位數曾出現 3.6 與 4.4 ms）。

| 情境 | 輪數 | 動作數 | 事件數 | 整場時間（含 AI） | 重播時間（只有 `resolve`） | 每個 `resolve` 平均 | 每個動作平均（含 AI） | 每個動作中位數（含 AI） |
|---|---|---|---|---|---|---|---|---|
| 1A 示範戰鬥（簡易 AI，`test_heights_8x8`） | 5 | 89 | 209 | 21.4 ms | 18.7 ms | 211 µs | 241 µs | 182 µs |
| 1A 10 輪戰鬥（簡易 AI，HP ×5） | 10 | 223 | 459 | 49.4 ms | 23.0 ms | 103 µs | 221 µs | 184 µs |
| 效用 AI：`test_heights_8x8` | 4 | 72 | 173 | 234.9 ms | 8.5 ms | 118 µs | 3.26 ms | **2.48 ms** |
| 效用 AI：`bridge_chasm` | 6 | 99 | 275 | 343.6 ms | 17.7 ms | 179 µs | 3.47 ms | **2.27 ms** |
| 效用 AI：`oil_depot` | 6 | 89 | 312 | 359.6 ms | 15.1 ms | 170 µs | 4.04 ms | **3.44 ms** |
| 效用 AI：`swamp` | 4 | 69 | 193 | 299.5 ms | 17.8 ms | 258 µs | 4.34 ms | **3.65 ms** |
| 效用 AI：`ruined_fort` | 5 | 86 | 210 | 217.1 ms | 11.4 ms | 133 µs | 2.53 ms | **2.47 ms** |

### AI 最佳化前後比較

同一套量測方法（每個動作含 AI，5 次重複合併取中位數；種子 42）。「1B」是 `e24be78` 的程式碼與地圖（以 `git archive` 取出在同一工作區執行）；「1C／1B 地圖」是本階段程式碼搭配 1B 版本的四張地圖檔（排除地圖改動的影響；物件定義用 1C 版，例如木箱已可燃並提供半掩護）；「1C／1C 地圖」是本階段的最終狀態。

| 地圖 | 1B 中位數 | 1B 平均 | 1C／1B 地圖 中位數 | 1C／1B 地圖 平均 | 1C／1C 地圖 中位數（bench） | 倍數（1B → 1C，同地圖中位數） |
|---|---|---|---|---|---|---|
| `test_heights_8x8` | 11.92 ms | 13.34 ms | 2.12 ms | 2.84 ms | 2.48 ms | 5.6× |
| `bridge_chasm` | 15.71 ms | 16.13 ms | 2.52 ms | 3.39 ms | 2.27 ms | 6.2× |
| `oil_depot` | 28.42 ms | 28.32 ms | 3.51 ms | 4.17 ms | 3.44 ms | 8.1× |
| `swamp` | 25.30 ms | 20.96 ms | 2.65 ms | 3.28 ms | 3.65 ms | 9.5× |
| `ruined_fort` | — | — | — | — | 2.47 ms | — |

整場效用 AI 戰鬥由 1–2 秒降到 0.2–0.4 秒；批次模擬每場 0.33–0.64 秒（1B 為 1.7–2.8 秒，見下節表格的「每場時間」）。單核心約 2–3 場／秒，十萬場約 10–14 小時（1B 估計 30–55 小時）。

最佳化的內容（依實作順序；括號內是當時單次量測的大致中位數，四張圖，本工作區有雜訊，僅供參考）：

1. **預覽只在需要時模擬兩次**（`battle.simulate_preview`）：`min` 模擬沒有經過任何分歧點（擲骰、檢定、反應決定、強制命中結果）時，`max` 必定相同，直接重用。（約 11–26 → 11–18 ms）
2. **每次決策只算一次「動作前」的位置價值**，並 **以虛擬位置價值篩選移動**：把行動者直接放到目的地算位置價值（不跑引擎），排序後只保留前 `move_candidates` 個；其中 **有風險** 的移動（可能被藉機攻擊、踩上有進入效果的表面、墜落、撤離、倒地站起）才跑完整 `preview`，其餘直接用虛擬分數——沒有風險的移動結果確定、只改變位置，分數與完整預覽完全相同（`test_fast_move_scores_match_full_preview`）。（→ 4–6 ms）
3. 藉機攻擊的風險判斷改為精確條件（離開「本輪還能反應、有藉機攻擊規則」的敵人的相鄰格，且下一步不再相鄰）；同一決策共用敵人清單與保護對象。（→ 3–4.5 ms）
4. `Ruleset.terrain_def` 等查表直接讀 `__pydantic_private__`，略過 pydantic `BaseModel.__getattr__` 的私有屬性慢速路徑。（→ 2.7–4.5 ms）
5. `BattleState`／`UnitState`／`ObjectState.clone` 明確列出欄位，取代 `dataclasses.replace`（單位複本 6.4 → 0.9 µs）；合法移動共用快取的 `Pos`。
6. 防禦直接計分（與完整預覽相同）；攻擊物件先以便宜條件篩選：只評估易爆、導電、阻擋視線的物件，或 2 格內有敵人的物件（其他物件攻擊不會帶來正分）。

試過但撤回：預覽時以 `model_construct` 建立事件與移動動作——實測 `model_construct`（約 3.4–4.4 µs）比完整驗證的建構（約 1.6–2.6 µs）還慢，已改回。

篩選不改變行為的證據：步驟 1–2 前後，三張 1B 地圖種子 42 的輪數與動作數完全相同；步驟 6 前後，四張示範地圖 × 20 個種子（80 場）的勝負統計、平均輪數與輪數範圍完全相同（兩次 `sim_demo_maps.py` 的表格一致）。

## 示範地圖平衡

`uv run python scripts/sim_demo_maps.py`（效用 AI、地圖預設陣容、`max_rounds=30`、種子 0–19；單獨執行，每場時間為本工作區單核心）。

| 地圖 | 我方勝 | 敵方勝 | 平手 | 我方勝率 | 平均輪數 | 輪數範圍 | 每場時間 | 預設陣容（敵方） |
|---|---|---|---|---|---|---|---|---|
| `bridge_chasm` | 12 | 8 | 0 | 60% | 5.75 | 4–8 | 383 ms | 盜賊 ×2、盜賊弓手、盜賊頭目 |
| `oil_depot` | 8 | 12 | 0 | 40% | 5.30 | 3–8 | 639 ms | 盜賊 ×2、盜賊弓手、盜賊頭目（第 3 輪援軍盜賊） |
| `swamp` | 10 | 10 | 0 | 50% | 4.80 | 3–10 | 345 ms | 盜賊、**盜賊盾衛**、盜賊弓手、盜賊頭目 |
| `ruined_fort` | 11 | 9 | 0 | 55% | 4.95 | 3–11 | 326 ms | 盜賊弓手 ×2、盜賊 ×2 |

我方陣容：`bridge_chasm`、`oil_depot`、`ruined_fort` 為戰士、弓手、法師；`swamp` 為戰士、弓手、雷術士。

對照：1B 版本（`e24be78` 的程式碼與地圖，同一腳本）：`bridge_chasm` 17/20（85%，5.15 輪）、`oil_depot` 4/20（20%，5.15 輪）、`swamp` 12/20（60%，4.65 輪）。

地圖的調整：

- **`bridge_chasm`**：深淵改為第 1–8 列（第 0、9 列可以繞行，避免雙方隔著深淵僵持）；兩岸角落各一段牆壁 (1, 1)–(1, 2)、(8, 7)–(8, 8) 擋住斜向視線；東岸橋頭兩座矮牆、西岸一根倒木。只加牆與掩護而不改深淵時，我方勝率 85–95%、平均 7–9 輪。
- **`oil_depot`**：倉庫東側四格牆壁；我方前方兩座矮牆（取代原本 (7, 1) 的木箱），讓我方在油桶與援軍下有掩護可用。
- **`swamp`**：兩段殘牆 (7, 1)–(7, 2)、(2, 7)–(2, 8)，兩根倒木與一個木箱；一名盜賊換成盜賊盾衛。
- **`ruined_fort`**（新）：要塞外牆（兩個缺口）、兩座高 2 的高台（經高 1 的台階爬上）、高台邊緣的矮牆、要塞外的木箱與倒木、要塞內一個油桶；兩名盜賊弓手占據高台。

## 與規格的差異

1. **牆壁的顯示字元是 `@`**：地圖檔的圖例照規格以 `#` 對應 `wall`（沒有地圖的圖例使用過 `#`），但地形表的顯示字元 `#` 已由深淵使用，因此 `trpg map show` 與戰場網格中牆壁顯示為 `@`。新物件的顯示字元：矮牆 `_`、倒木 `-`。
2. **「近戰」的定義**：無視半掩護的「近戰」與 1B 的近戰高度差限制相同——武器射程 ≤ `melee_height_limit_max_range`（2，含長柄）。遠程武器攻擊相鄰目標時，唯一「在兩者之間」的相鄰格就是攻擊者自己的格子，因此不會有掩護。
3. **事件與模型的新欄位**：`AttackRolled.cover`（0 或負值）與 `cover_object_id`；`DamageDealt.base_amount`（決定 #3 的擴散基準）；`Preview.cover`、`Preview.notes`；`TerrainDef.blocks_sight`；`ObjectDef.spill`；`AiWeights.cover`、`expose`、`cover_damage`；`AiProfileTable.move_candidates`。`core.yaml` 新增 `half_cover_hit_penalty`（2）與 `interact_height_limit`（1）。
4. **戰鬥紀錄格式升為 `trpg-battle-log/3`**：結算規則改變（表面立即生效、漏油、推不動的動作不合法），`/2` 的紀錄無法重播。
5. **新互動規則 `oil_on_fire_burns`**：油（漏油）產生在火焰上時保留火焰（「漏到火上繼續燒」）；沒有這條時，新的油會蓋掉火。
6. **表面不能產生在牆壁上**：`create_surface` 在牆壁上會失效（`effect_fizzled: solid_terrain`）；地圖檢查拒絕把物件或表面放在牆壁上。
7. **AI 介面**：`UtilityAI.rank()` 現在只回傳候選動作（被篩掉的移動與物件攻擊不在其中）；新增 `rank_all()` 以完整預覽評分所有合法動作（較慢，供測試與分析）。`score_action` 新增 `before` 參數。
8. **新腳本** `scripts/sim_demo_maps.py`（平衡表）；`scripts/bench_battle.py` 加入每個動作中位數與 `ruined_fort`。
9. **既有測試的調整**：`test_physical_attack_destroys_barrel_without_explosion` 依決定 #5 改為檢查漏油；示範地圖的預告屬性測試（`test_property_telegraph_matches_every_environment_turn_on_demo_maps`）在「預告取得之後、環境回合之前還有改變戰場的事件」時不比較（例如下一位單位回合開始時被燃燒燒死、接著直接進入環境回合——預告的前提「之後狀態不再改變」不成立；地圖改動後 hypothesis 找到了這種情況）。

## 待 PM 決定

依重要性排序。

1. **半掩護不看目標的高度**：規格 3.2 只比較「攻擊者高度」與「C 的地形高度 ＋ 1」。因此站在高 2 高台上的目標，旁邊地面（高 0）的木箱仍會替它擋住地面上攻擊者的箭；反過來，高台上的矮牆會替站在地面、緊鄰高台的單位擋住同樣在高台上的弓手（`ruined_fort --seed 42` 中出現：戰士在 (6, 2)，矮牆在高 2 的 (7, 2)，高台上的盜賊弓手攻擊時 −2）。目前照字面實作。是否改成「C 的地形高度 ＋ 1 ≥ 目標高度」才算掩護？
2. **示範地圖平衡的穩定度**：20 個種子的勝率標準差約 ±11%，`bridge_chasm` 目前 60% 偏上緣；`tests/engine/test_demo_balance.py` 把 35%–65%／4–6 輪鎖成測試（約 20 秒，2 個處理程序），之後任何 AI 權重或規則改動都可能需要重新調地圖。請決定這個測試要保留為常態檢查，或改為只在 `scripts/sim_demo_maps.py` 報表檢查。
3. **AI 候選篩選是近似**：`move_candidates: 6` 以「直接放到目的地」的位置價值排序後才評估；有風險的移動若虛擬分數不在前 6 名就不會被考慮（實測 80 場的結果與篩選前相同，但不保證所有情境都相同）。攻擊物件只評估易爆、導電、阻擋視線、或 2 格內有敵人的物件。Phase 2 若加入會在遠處產生效果的技能，篩選條件需要擴充（或改成依技能預覽範圍）。
4. **「立即生效」的時間點**：表面在單位腳下建立或改變時，進入效果在 **整個效果佇列清空前**（同一次結算內、連鎖之後）依單位 ID 觸發，而不是在連鎖中途插入。只觸發 `on_enter`（火 → 燃燒、冰 → 滑倒檢定）；`on_turn_start` 類（毒、聖光）仍在回合開始時生效。
5. **AI 掩護權重的語意**：位置價值的 `cover` 計算「看得到我、且從其位置看過來我受到半掩護」的敵人數，不分敵人的武器（近戰敵人也算，雖然近戰無視半掩護）；`expose` 以「四方向相鄰有半掩護物件」判斷敵人是否在掩護中（不看從誰的角度）。權重（弓手 cover 12；狡猾 cover 6、expose 35、cover_damage 1）是實作者擬定。
6. **漏油的範圍與條件**：只在「被傷害打破」（`destroy cause = damage`）時漏油；被大地效果摧毀、掉進深淵、燒毀都不漏。漏到水上時油取代水；漏到火上保持火焰（新規則 `oil_on_fire_burns`）。
7. **盜賊盾衛的數值**：HP 32、護甲 6、速度 4、物理抗性 10%、格擋對遠程攻擊也有效（耐力 < 10 時不格擋）。最初的 HP 38／護甲 7 讓戰鬥拖到 7 輪以上，因此調低；目前只用在 `swamp`。守衛模式在全滅勝利條件下傾向守在受傷同伴旁，戰鬥會稍長。
8. **推擊被友方擋住也不合法**：決定 #10 的「目標格被擋」包含目標後方有任何單位（敵我都算），因此「把敵人推向他的同伴」的 Shove 不合法；推進深淵或岩漿仍合法。
9. **`bridge_chasm` 的地形改動較大**：深淵兩端開了通道（第 0、9 列），與 1B 的「只能走木橋」不同；若希望保留純吊橋的定位，需要改用其他方式縮短戰鬥（例如起始位置更靠近橋頭）。
10. **測試時間**：`check.py` 的 pytest 由約 35 秒增加到約 45 秒（平衡測試約 20 秒）。

## 給下一階段的備註

（給 Phase 2 實作者）

- **掩護 API**：`rules.combat.half_cover(state, attacker, target) -> Cover | None`（含近戰判斷與懲罰）、`cover_object_between(state, attacker_xy, target_xy)`（純幾何）。遠程技能的命中判定請沿用 `roll_attack`（已含半掩護）；技能的命中預覽在 `preview._attack_numbers` 計算 `bonus` 時記得扣掉掩護。
- **推擊**：`effects.world.push_distance`（steadfast 減半）、`unit_push_block`／`object_push_block`（阻擋原因）。技能的推擊效果照決定 #2「0 格只是不移動」，不要套用 `battle.shove_problem`。
- **表面立即生效**：效果處理器改變表面時一律經過 `effects.world.set_surface(..., depth=effect.depth)`；它會把腳下有單位的格子記到 `ctx.surface_entries`，由 `effects.queue.execute` 在佇列清空前處理。直接呼叫 `set_surface` 而不在 `execute` 內時（例如環境回合的到期處理），之後要呼叫一次 `execute(ctx, [])`。
- **預覽的分歧點**：新增會擲骰或依預覽模式分歧的地方時，`Ctx.rng`（`FixedRng`）會自動記錄；若是以 `ctx.preview` 直接分歧（像 `reactions._decide`），要呼叫 `ctx.mark_branch()`，否則 `simulate_preview` 會誤以為 `min` 與 `max` 相同而只模擬一次。
- **AI 篩選**：`UtilityAI.rank` 的篩選規則在 `is_risky_move`、`worth_previewing`、`defend_score`；新動作類型（技能）預設會跑完整 `preview`。若新增會影響「位置價值」以外結果的移動（例如踩了會觸發的陷阱），要加進 `is_risky_move`，否則虛擬分數會與實際不符（`test_fast_move_scores_match_full_preview` 會抓到）。
- **複本**：`clone` 明確列出欄位；在 `BattleState`／`UnitState`／`ObjectState` 新增欄位時要同步修改 `clone`（`tests/engine/test_state_clone.py` 會抓到漏掉的欄位）。
- **pydantic 效能**：引擎內的 `model_construct` 比一般建構慢，不要用它來加速；私有屬性（`PrivateAttr`）的讀取很慢，熱路徑請比照 `Ruleset.terrain_def` 直接讀 `__pydantic_private__`。
- **平衡工具**：`scripts/sim_demo_maps.py --maps a,b --seeds N`；地圖或 AI 權重改動後請重跑並更新 `tests/engine/test_demo_balance.py` 的預期（或依待 PM 決定第 2 點調整）。

## 附錄：`trpg battle --map ruined_fort --seed 42` 輸出節錄

```text
戰鬥開始：廢墟要塞（10×10），種子 42
……
行動順序：法師 → 盜賊1 → 戰士 → 盜賊弓手2 → 盜賊弓手1 → 弓手 → 盜賊2

=== 第 1 輪 ===
    0  1  2  3  4  5  6  7  8  9
 0  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
 1  0.  0-  0.  0.  0.  0@  0@  0@  0@  0.
 2  0.  0.  0.  0.  0.  0@  0.  2_  2a  0.
 3  0.  0C  0.  0[  0.  0@  0.  1.  2.  0.
 4  0A  0.  0.  0.  0.  0.  0b  0.  0.  0.
 5  0B  0.  0.  0.  0.  0.  0.  0c  0.  0.
 6  0.  0.  0.  0[  0.  0@  0&  1.  2.  0.
 7  0.  0.  0.  0.  0.  0@  0.  2_  2d  0.
 8  0.  0.  0.  0.  0.  0@  0@  0@  0@  0.
 9  0.  0.  0.  0.  0.  0.  0.  0.  0.  0.
  圖例：[ 木箱、- 倒木、_ 矮牆、& 油桶
……
— 戰士 的回合（AP 3，移動 5）
  戰士 攻擊 盜賊2：d20=13 修正 +0 熟練 +2 = 15（目標 11）→ 命中
  ⟳ 盜賊2 反應：格擋（耐力 −10）
    盜賊2 受到 4 點物理傷害［骰 4］（格擋 ×0.5），HP 2 → 0
  ＊ 盜賊2 倒下了！
  戰士 從 (5, 4) 移動到 (6, 2)（消耗 3 移動）
  戰士 獲得狀態「防禦」
  戰士 結束回合
— 盜賊弓手2 的回合（AP 3，移動 5）
  盜賊弓手2 攻擊 戰士：d20=4 修正 -2 熟練 +2 高度 +2 半掩護 -2 = 4（目標 11）→ 失手［命中 −2：矮牆掩護］
  盜賊弓手2 攻擊 戰士：d20=7 修正 -2 熟練 +2 高度 +2 半掩護 -2 = 7（目標 11）→ 失手［命中 −2：矮牆掩護］
  盜賊弓手2 攻擊 戰士：d20=17 修正 -2 熟練 +2 高度 +2 半掩護 -2 = 17（目標 11）→ 命中［命中 −2：矮牆掩護］
    戰士 受到 4 點物理傷害［骰 1］（元素修正 ×0.9），HP 8 → 4
……
— 弓手 的回合（AP 3，移動 5）
  弓手 攻擊 盜賊弓手1：d20=19 修正 +0 熟練 +2 高度 -2 半掩護 -2 = 17（目標 11）→ 命中［命中 −2：矮牆掩護］
    盜賊弓手1 受到 8 點物理傷害［骰 4］，HP 26 → 18
  弓手 攻擊 盜賊弓手1：d20=15 修正 +0 熟練 +2 高度 -2 半掩護 -2 = 13（目標 11）→ 命中［命中 −2：矮牆掩護］
    盜賊弓手1 受到 7 點物理傷害［骰 3］，HP 18 → 11
  弓手 攻擊 盜賊弓手1：d20=9 修正 +0 熟練 +2 高度 -2 半掩護 -2 = 7（目標 11）→ 失手［命中 −2：矮牆掩護］
  弓手 從 (4, 5) 移動到 (3, 2)（消耗 4 移動）
……
勝方：敵方勝利（第 5 輪結束，86 個動作，210 個事件）
```

（弓手從地面射向高台上的盜賊弓手 1：低打高 −2，再加上矮牆的半掩護 −2；高台上的弓手射向地面時有高打低 +2，但戰士緊鄰高台上的矮牆，同樣 −2。開場時，我方 4 個起始格中有 2 格完全看不到兩座高台（牆壁擋住），另 2 格只能斜穿缺口看到對角的一座；守在缺口的盜賊則都看得到。）
