# Phase 3-29 完成報告｜`charge_through` 打不到貼牆／地圖邊的敵人

分支：`worktree-agent-a3a00ace7b8102530`（從 main 863a4d5 分出）。`LOG_FORMAT`：`trpg-battle-log/45` → `/46`。

## 做了什麼

- `src/trpg/engine/skills/mobility.py`：`charge_route` 改為目標格可選射程內直線上任何格（含敵人、牆、地圖邊）。
  - 路線 `cells` 含目標方向走得到的所有格（含有單位的格子）；`stop` 是最後一個空格，前面全是單位時為起點（原地攻擊）；新欄位 `bump`：路線最後一格站著單位、其前方是牆／地圖邊／擋路物件時的撞擊格；`walked` 為到停點為止的格子。
  - 只剩「第一格就過不去」會被拒絕（訊息仍含「停不下來」）。`charge_candidates` 改列所有地圖內的格子。
- `src/trpg/engine/skills/interpreter.py`：`_charge_hit` 在命中、敵人活著、`on_hit` 結算後仍站在原地時，對 `bump` 格的敵人再發一次 `PushEffect(distance=1)`，被擋下即走既有的 `collided`／撞擊傷害／`collided_round`（接 `target_collided` 與撞擊關鍵字）。`UnitCharged.path` 只到停點。隊友不被撞。
- 內容文字：`content/skill_primitives.yaml` 的 `charge_through` 說明、`narrative/skills.py` 的技能摘要。
- 前端預覽（`client/src/battle/scenePreview.ts`）：停點之後的敵人（目標格、貼牆）也標命中率；原地不動時只標命中；說明文字加上「背後被擋住，命中後另受一次撞擊（傷害範圍）」。預覽的 `moves`／`collisions` 由引擎既有預覽模擬自然得出，不需改 API。
- AI：候選動作來自 `charge_candidates`，估計沿用 `_charge_estimate`（區域內敵人數 × 權重 ＋ 停點位置價值），目標格上的敵人現在計入區域，故 AI 自然會選貼牆的敵人；未改 AI 程式碼。

## 驗收（逐條）

| 條件 | 證據 |
|---|---|
| 目標可選射程內任何格 | `test_any_tile_in_line_within_reach_can_be_chosen`、`test_only_straight_lines_within_the_reach_are_legal` |
| 使用者案例：敵人在第 3 格、背後地圖邊 | `test_an_enemy_on_the_third_tile_against_the_map_edge_is_hit_and_bumped`（停在前一格、各擲命中、`collided` obstacle=edge、一次 collision 傷害） |
| 牆前／擋路物件 | `test_an_enemy_against_a_wall_is_bumped`、`test_an_enemy_against_a_blocking_object_is_bumped` |
| 背後有路不撞、失手不撞、隊友不撞 | `test_an_enemy_with_room_behind_is_not_bumped`、`test_a_miss_does_not_bump`、`test_an_ally_against_the_edge_is_not_bumped` |
| 貼牆相鄰敵人（原地攻擊，無移動） | `test_an_adjacent_enemy_against_the_wall_is_hit_without_moving` |
| 前一格被擋不能施放 | `test_it_cannot_be_cast_when_the_first_tile_is_blocked` |
| 撞擊接 `target_collided` | `test_the_bump_feeds_target_collided`（`collided_round`） |
| 預覽停格與被撞敵人 | `test_the_preview_shows_the_stop_tile_and_the_bump`；前端 `scenePreview.test.ts` 新案例 |
| 內容技能 `skill_bull_rush`（蠻牛衝陣）使用者案例 | `test_bull_rush_hits_an_enemy_standing_at_the_map_edge` |
| `check.py`、`pnpm build` | `pnpm -C client build` 成功；`check.py` 結果見文末 |
| `--log-json` ＋ `replay` | 引擎與 CLI 測試中的重播一致性測試全過；未另手動跑 CLI |

## 影響既有測試

- 改寫 `test_the_end_tile_must_be_empty_and_standable`（舊規則「終點須空」不再成立）、`test_it_cannot_be_cast_when_it_cannot_stop_anywhere`（改為第一格被擋）、`test_it_never_stops_on_a_unit`（現在敵人會被攻擊）。
- `LOG_FORMAT` 斷言 `/45` → `/46`（`tests/cli/*`、`test_gear_g2.py`、`test_gear_g3a.py`）。
- 釘種子的測試軌跡沒有改變，不需換種子。

## 複雜度

沒有新增 `noqa`。

## 待 PM 決定

1. 只有「路線最後一格」的敵人會被撞；若後面堆著一排單位（敵 A 在前、敵 B 貼牆），只有貼牆的 B 受撞，A 不受撞擊（保守）。
2. 前面全是單位時施放者原地不動，仍消耗 AP；`push_aside` 把前方敵人推開後施放者會走進那一格。
3. `steadfast` 單位（推距離被縮成 0）不會受撞擊傷害。
4. AI 沒有為「撞擊」加額外分數，只靠命中的敵人數；若要鼓勵 AI 把敵人撞牆，需另訂權重。
5. 前端點擊流程用既有的 tile 選取（候選格來自引擎合法動作），未在瀏覽器實機驗證；敵人所在格現在也是合法目標格，請試玩確認點擊體驗。
6. 未跑 `sim matrix`（規格未要求）。

## 最終檢查結果

- 第一次完整 `check.py`：ruff（LOG_FORMAT 說明行過長，已修）、pytest 2 項（`test_24c` 的 `/45` 斷言、CLI 輸出快照因 `charge_through` 說明文字改變，已更新斷言與快照）、client test 1 項（`dollGear.test.ts` 在高負載下逾時 5 秒，單獨重跑 16 項全過，與本段無關）。
- 修正後相關測試重跑全過；其餘 ruff、format、mypy、lint-imports、client typecheck、`pnpm build` 通過。完整 `check.py` 只跑了一次（遵守守則 11），修正後未再整套重跑。
- 快照 `tests/cli/snapshots/cli_output_hashes.json` 的 `skills_list`／`skills_show_all` 雜湊更新，原因是 `charge_through` 的技能摘要文字。
