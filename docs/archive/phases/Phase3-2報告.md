# Phase 3-2 報告：FastAPI 本機 API

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 801fb3b | 共用推進迴圈：`runner.advance`／`auto_step`／`apply_step`（`run_battle` 改用它）、`StepLimitExceeded`；`CommandedAI.issue`／`current_orders`；`default_lineup`／`build_allies` 搬到 `trpg.sim.lineup`；`uv add fastapi uvicorn`、`httpx`（dev）；import-linter 合約「api 不得匯入 cli」 |
| 505030e | `SkillCard` 加英文代碼欄位（0.6 #8）；`narrative.battle_started_text`（不含種子的開場描述）；`advance` 與 `CommandedAI.issue` 的測試 |
| 2f9dcc4 | `trpg.api`：`sessions`（`BattleSession`、`SessionStore`）、`presenter`（我方視角回應）、`schemas`、`routes/{content,battles}`、`app.create_app`；`tests/api/` |
| 722d288 | `trpg serve [--host 127.0.0.1] [--port 8000]` 與測試 |
| （本報告） | `docs/phases/Phase3-2報告.md` |

### 架構摘要

- `BattleSession` 只保存 `setup ＋ seed ＋ steps`（與 `BattleLog.actions` 同格式）、由它們推導出的目前狀態與 `Pending`、事件列表、`CommandedAI`（指令紀錄即 `order_log`）、`hero_id`。每一步結算後立刻寫回工作階段，所以 500 時已結算的部分仍保留、仍可重播。
- **自動推進與 `run_battle` 共用**：`run_battle` 的 while 迴圈抽成 `trpg.engine.runner.advance(state, pending, policy, *, decide, on_step, max_actions, controllers, stop)`；每一步的選擇是 `auto_step`（暫停中 → `decide`；`has_only_end_turn` → `EndTurn`；否則 policy），結算是 `apply_step`（`replay` 也改用它）。`run_battle` ＝ `begin_battle` ＋ `advance(stop=None)`；工作階段 ＝ `advance(stop=awaits_player)`，停止條件是「主角的 `Pending`」或「輪到主角且 `not has_only_end_turn`」。非主角的詢問用預設的 `accept_all`。沒有第二份迴圈。
- 回應一律經過 `trpg.api.presenter`：`project_for(state, Team.ALLY)`、`filter_events(events, 最新狀態, Team.ALLY)`、`describe_event` 的 `text`；開場事件移除 `seed`；他方陷阱技能的 `use_skill` 步驟清掉目標欄位。
- 錯誤對應集中在 `trpg.api.app.ERROR_STATUS`：`BattleNotFoundError` 404、`IllegalActionError` 400、`SessionConflictError` 409、`InvalidRequestError` 422、`AutoAdvanceLimitError` 500（回應另帶 `battle_id`）；pydantic 驗證錯誤為 FastAPI 預設的 422。
- 依賴方向：`trpg.api` → engine／content／narrative／sim；`trpg.cli.serve` 延後匯入 `trpg.api.app` 與 uvicorn（其他子指令不載入 FastAPI）。

## 2. 驗收條件逐條

1. **`trpg serve` 可啟動，`GET /api/maps` 回 10 張地圖**：通過。背景啟動 `uv run trpg serve --port 8765` 後以 curl 查詢，結束時已關閉程序（埠不再 LISTEN）：
   ```
   maps: 10 ['bridge_chasm', 'cliff_outpost', 'dark_forest', 'frozen_lake', 'lava_crossing', 'narrow_halls', 'oil_depot', 'open_plain', 'ruined_fort', 'swamp']
   POST status 201
   INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
   INFO:     127.0.0.1:54215 - "GET /api/maps HTTP/1.1" 200 OK
   ```
   另有 `tests/cli/test_serve_cli.py`（預設 `127.0.0.1:8000`、自訂 host／port、壞埠號結束碼 2；以 monkeypatch 取代 `uvicorn.run`）與 `tests/api/test_routes.py::test_maps_lists_the_ten_playable_maps`。
2. **端點都存在、錯誤碼符合**：通過。`tests/api/test_routes.py`：
   - 404：`test_unknown_battle_is_404`（6 個端點參數化）、`test_unknown_skill_is_404`
   - 400：`test_an_illegal_action_is_400_and_changes_nothing`、`test_an_action_for_another_unit_is_400`、`test_preview_errors`
   - 409：`test_actions_and_decisions_after_the_end_are_409`（動作、決定、預覽、指令）、`test_a_decision_while_waiting_for_an_action_is_409`、`test_waiting_for_a_decision_rejects_actions_with_409`
   - 422：`test_bad_create_requests_are_422`（9 種）、`test_a_malformed_action_is_422`（4 種）、`test_invalid_orders_are_422`（8 種）、`test_a_semantic_order_error_has_a_chinese_reason`
   - 500：`test_exceeding_the_auto_advance_limit_is_500_and_keeps_the_session`
   - 正常：`test_create_advances_to_the_hero_and_includes_the_opening`、`test_create_with_explicit_ally_builds`、`test_get_returns_the_current_state_without_steps`、`test_a_legal_action_advances_to_the_next_hero_turn`、`test_builds_lists_every_build`、`test_skill_card_has_text_and_codes`、`test_log_has_the_cli_format`
3. **透過 API 打完至少 2 張地圖，`replay` 與 `trpg battle replay` 一致**：通過。`tests/api/test_full_battle.py::test_a_full_battle_through_the_api_replays_identically`（open_plain／build_fire／主角用效用 AI、frozen_lake／build_guardian／固定選第一個非 `end_turn`、narrow_halls／build_trapper／效用 AI）：`/log` 以 `replay` 重播，最終狀態 JSON 與事件 JSON 完全一致、與工作階段目前狀態一致，並以 `cmd_replay` 驗證通過。反應詢問：`test_hero_reaction_prompts_alternate_and_still_replay`（主角反應改 `prompt` 的測試內容庫，4 場戰鬥，接受與拒絕交替且都出現，紀錄皆可重播）。
4. **確定性**：通過。`test_same_inputs_give_the_same_responses`：同 `map_id／seed／build` 建立第二個工作階段，重送第一場的全部動作與決定，每個回應（去掉 `battle_id`）完全相同，`/log` 逐字相同。
5. **不洩漏**：通過。`tests/api/test_leaks.py`：
   - `test_no_response_contains_random_or_paused_internals`：陷阱戰鬥與含暫停的戰鬥的所有回應不含 `rng_state`、`base_state_json`、`action_json`、`events_emitted`、`"seed"`。
   - `test_the_hero_trap_is_hidden_from_the_enemy_view`：build_trapper 主角放陷阱後，我方回應有 `trap_placed`；以敵方視角過濾工作階段事件沒有 `TrapPlaced`，`step_view` 清掉陷阱技能的 `target_pos`。
   - `test_an_enemy_trap_never_reaches_the_ally_responses`：測試專用狀態（敵方捕獸夾）下 `GET` 的 `view.traps` 為空、全文無技能 ID。
   - `test_preview_does_not_reveal_an_enemy_trap`：同一狀態實際結算會觸發陷阱，但預覽的 `certain`／`possible` 沒有 `trap_*`、全文無技能 ID（已確認未過濾的模擬會出現 `trap_triggered`，測試有效）。
6. **自動推進與 `run_battle` 共用；CLI 輸出不變**：通過。共用方式見第 1 節架構摘要；`tests/engine/test_runner_advance.py::test_advancing_in_pieces_equals_run_battle`（分段 `advance` 的步驟、狀態、事件與 `run_battle` 相同）。`tests/cli/test_output_snapshots.py` 全過；`trpg battle --map open_plain --seed 7 --log-json f` 與 `trpg battle replay f`：「重播驗證通過：94 個動作、320 個事件，最終狀態一致（open_plain，種子 7）。」（與 3-1 相同）
7. **import-linter 新合約**：通過。`uv run lint-imports`：`Contracts: 5 kept, 0 broken.`（新增「api 不得匯入 cli」）；`tests/test_architecture.py` 加 `API_FORBIDDEN` 與正反各 3 個掃描器自我測試。
8. **`scripts/check.py` 全過、複雜度 noqa 不增加**：通過（1577 passed；ruff、format、mypy、lint-imports、pytest 全部通過）。複雜度類 noqa（C901／PLR0911／PLR0912／PLR0915／PLR0917）在 src／scripts／tests 合計 20 → 20。
9. **API 端點表**：見第 7 節。

## 3. 複雜度 noqa

- 新增：無。移除：無。總數 20 → 20。
- 其他 noqa：`cli/serve.py` 兩個 `PLC0415`（延後匯入 uvicorn 與 `trpg.api.app`，讓其他子指令不載入 FastAPI）；`cli/main.py` `_port` 的 `PLR2004`（埠號上限 65536）。

## 4. 修改既有測試期望值

無。`tests/test_architecture.py` 只新增合約與案例。

## 5. 待 PM 決定

1. **目前的內容沒有任何 `prompt` 反應**（`reactions.yaml` 預設 `auto`），所以網頁上實際不會出現反應詢問；決定端點與 409 都以「主角反應改為 `prompt`」的測試內容庫驗證。要不要讓主角在網頁模式的反應改成 `prompt`（或讓玩家設定）？這是規則層面的選擇，本段未做。
2. **`/log` 是完整紀錄**：為了與 `--log-json` 同格式、能 `trpg battle replay`，內含 `seed`、`final_state.rng_state` 與未過濾事件（含敵方陷阱）。戰鬥中也可讀取，等於玩家可以看到內部狀態。是否改成只在戰鬥結束後開放，或另出一份過濾版？
3. **戰術指令不經指揮官介面**：`CommandedAI` 每輪只問一次指揮官，用「回傳玩家指令的指揮官」時，回合中途改的指令要等下一輪才生效。所以我方不註冊指揮官，改以新增的 `CommandedAI.issue` 直接下達（下一次我方 AI 決策即生效），`OrderRecord.round` 是下達時的輪數。指令以 `PUT` **取代** 目前的指令；`unit_orders` 指向主角、敵方或不存在的單位一律 422。
4. **`awaiting` 多一個值 `"stalled"`**：只在自動推進超過上限（500）後出現，之後動作與決定都回 409，仍可 `GET` 與 `/log`。建立戰鬥時就 500 的話，回應帶 `battle_id`。
5. **地圖與錯誤碼**：`/api/maps` 與建立戰鬥只接受有預設遭遇的地圖（排除兩張 `test_` 地圖，剛好 10 張）；未知的地圖或 build 回 422（不是 404，404 只用於戰鬥 ID）。
6. **建立參數**：`ally_builds` 省略時同 CLI 補標準隊友到 3 人；有給（含空串列）時不補，空串列代表主角單獨出戰。`max_rounds` 預設 30（同 CLI），上限 200。敵方固定用地圖的預設陣容；天氣與部署未開放。
7. **額外的隱藏**：開場 `battle_started` 事件移除 `seed`，`text` 不提種子（新增 `narrative.battle_started_text`，CLI 文字不變）；他方陷阱技能的 `use_skill` 步驟清掉 `target_pos`／`direction`／`target_id`（目前敵人沒有陷阱，屬預防）。
8. **預覽回應**：機率以整數千分比（`*_permille`，四捨五入）、期望傷害 ×1000（`expected_milli`）；不含引擎 `Preview` 的 `min_state`／`max_state`（含 `rng_state`）與 `min_events`／`max_events`。3-4 若要連鎖動畫，需再加過濾後的事件。
9. **回應大小**：`legal_actions` 在 4 場測試戰鬥中位數 28.5、最少 2、最多 113（大多是移動目的地）；回應 JSON 中位數約 21 KB、最大約 50 KB（每次都帶完整 `view`）。本段未最佳化。步行的 `unit_moved` 沒有 `text`（CLI 用彙總的一行），前端需自行彙總。
10. **工作階段沒有數量上限也不會過期**（只存在記憶體，重啟消失）。另：starlette 1.9 對 `httpx` 發出棄用提示（建議 `httpx2`），規格指定 `httpx`，所以只在 `pytest` 設定中略過這則提示；要換 `httpx2` 請指示。

## 6. 代表性輸出節錄

`POST /api/battles` `{"map_id":"ruined_fort","seed":5,"hero_build":"build_tank"}`（`awaiting: "action"`、`hero_id: "unit_0001"`、`steps` 6 步、`legal_actions` 38 個）的開場事件：

```json
[{"seq":0,"round":1,"type":"battle_started","map_id":"ruined_fort","text":"戰鬥開始：廢墟要塞（10×10）"},
 {"seq":1,"round":1,"type":"initiative_rolled","unit_id":"unit_0001","roll":20,"modifier":1,"total":21,
  "text":"先攻：坦克英雄 d20=20 +1 = 21"}]
```

主角結束回合後，回應 `steps[1]`（AI 單位的移動；步行事件沒有 `text`）：

```json
{"actor_id":"unit_0006",
 "step":{"unit_id":"unit_0006","type":"move","path":[{"x":7,"y":5},{"x":6,"y":5},{"x":5,"y":5},{"x":4,"y":5},{"x":3,"y":5},{"x":2,"y":5}]},
 "events":[{"seq":25,"round":1,"type":"unit_moved","unit_id":"unit_0006","from_pos":{"x":7,"y":5},"to_pos":{"x":6,"y":5},"mode":"walk","cost":1}, …]}
```

整場戰鬥（主角反應改 `prompt` 的測試內容庫、主角用效用 AI）：

```
open_plain   build_fire     requests 17 decisions 1 outcome {'winner': 'ally', 'end_reason': 'eliminate', 'round': 4}
ruined_fort  build_tank     requests 33 decisions 2 outcome {'winner': 'ally', 'end_reason': 'eliminate', 'round': 10}
narrow_halls build_trapper  requests 17 decisions 0 outcome {'winner': 'ally', 'end_reason': 'eliminate', 'round': 5}
frozen_lake  build_guardian requests 33 decisions 1 outcome {'winner': 'ally', 'end_reason': 'eliminate', 'round': 8}
```

## 7. API 端點表（給 3-3 前端）

所有回應為 JSON；錯誤一律 `{"detail": "<中文訊息>"}`（pydantic 驗證錯誤為 FastAPI 預設格式，`detail` 是錯誤列表）。

| 方法 | 路徑 | 請求 | 回應（主要欄位） | 錯誤 |
|---|---|---|---|---|
| GET | `/api/maps` | — | `[{id, name_zh, archetype, width, height}]`（有預設遭遇的地圖，依 ID） | — |
| GET | `/api/builds` | — | `[{id, name_zh, theme_zh, skills: [skill_id]}]` | — |
| GET | `/api/skills/{skill_id}` | — | `SkillCard`：`id, name_zh, skeleton, tier, rank, rarity, kind, category, weapon_req, scaling, ap_cost, cost[], shape, condition, effects[], mastery, tags[], concept, cast_flavor` ＋ 代碼 `rarity_id, kind_id, category_id, weapon_req_id, scaling_attrs[], mastery_id` | 404 |
| POST | `/api/battles` | `{map_id, seed (0..2^64−1), hero_build, ally_builds?: [build_id] \| null, max_rounds?: 1..200 = 30}` | 201，**戰鬥回應** | 422 |
| GET | `/api/battles/{id}` | — | 戰鬥回應（`steps` 為空） | 404 |
| POST | `/api/battles/{id}/actions` | `Action`（`{type, unit_id: 主角, …}`，與 `legal_actions` 的元素同格式） | 戰鬥回應 | 404、400（不合法／不是主角）、409、422、500 |
| POST | `/api/battles/{id}/decision` | `{accept: bool}` | 戰鬥回應（`steps[0].step` 為 `{type:"decision", unit_id, accept}`） | 404、409、422、500 |
| POST | `/api/battles/{id}/preview` | `Action` | `{action, hit_permille, crit_permille, damage: {minimum, maximum, expected_milli, expected_if_hit_milli} \| null, affected_tiles: [[x,y]], affected_units, certain: [Outcome], possible: [Outcome], cover: {penalty, object_id, kind, name_zh, pos} \| null, notes[], targets: [{unit_id, hit_permille, crit_permille, damage, ally, knock_permille, status_chances: [{status_id, original_id, apply_permille, diminished}]}], healed: [{unit_id, minimum, maximum}]}`；`Outcome = {kind, unit_id, object_id, pos, detail}` | 404、400、409、422 |
| PUT | `/api/battles/{id}/orders` | `OrderSet`：`{team_orders: [Order], unit_orders: {unit_id: [Order]}}`；`Order` 為 `{kind:"focus_target", target}`、`{kind:"hold_position", at:[x,y], radius:0..3}`、`{kind:"retreat_to", at}`、`{kind:"protect", ward}`、`{kind:"use_environment"}`；`{}` ＝ 取消 | 戰鬥回應（`steps` 為空，`orders` 為新指令；不推進戰鬥） | 404、409（已結束）、422 |
| GET | `/api/battles/{id}/log` | — | `BattleLog`（`trpg battle --log-json` 同格式：`format, seed, setup, actions, events, final_state, orders`） | 404 |

**戰鬥回應**（`BattleResponse`）：

| 欄位 | 內容 |
|---|---|
| `battle_id` | 工作階段 ID |
| `hero_id` | 主角單位 ID（我方第一個單位） |
| `awaiting` | `"action"`／`"decision"`／`"ended"`／`"stalled"`（只在 500 後） |
| `view` | `BattleView`（3-1 的 `project_for(state, ally)`：`tiles, objects, units, traps, turn_order, active_unit, round, max_rounds, weather_*, objective, ended, winner, end_reason, pending`） |
| `legal_actions` | `awaiting == "action"` 時主角的合法動作（含 `end_turn`），否則 `[]` |
| `pending` | 主角的反應詢問 `{kind:"reaction", unit_id, reaction, trigger_unit_id, skill_id, trigger_event_seq, stamina_cost, mana_cost, hp_cost_permille}` 或 `null` |
| `orders` | 我方隊友目前的 `OrderSet` |
| `steps` | 這次請求推進的每一步：`[{actor_id, step, events}]`；開場那一步 `actor_id`、`step` 為 `null`；`events` 是我方視角過濾後的事件 JSON，另加 `text`（中文，沒有描述時不含此鍵），`seq` 保留原值（會跳號） |
| `outcome` | 結束時 `{winner: "ally" \| "enemy" \| null, end_reason, round}`，否則 `null` |
