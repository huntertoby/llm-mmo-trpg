# Phase 3-1 報告：視圖過濾、描述模組、Pending 序列化

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| a0c7e90 | 新增 CLI 輸出快照測試（搬家前先錄下 9 組輸出的 SHA-256） |
| 1763e7b | `describe_event` 搬到 `trpg.narrative.events`，改為 `dict[type, handler]` 註冊表 |
| 5c64b73 | 技能卡片描述搬到 `trpg.narrative.skills`、新增 `SkillCard`／`skill_card`；import-linter 與架構測試新增 narrative 合約 |
| 23e4d10 | `Pending`／`PendingResolution` 補欄位與往返測試 |
| 0b30d3f | `project_for`（`engine/view.py`）與 `filter_events`（`engine/event_filter.py`） |
| 781f782 | 本報告 |


## 2. 驗收條件逐條

1. **`project_for` 無禁止欄位、陷阱可見性正確**：通過。`tests/engine/test_view.py::test_the_view_has_no_hidden_fields`（含暫停中的狀態；檢查鍵不含 `rng_state`／`seed`／`ruleset`／`base_state_json`／`action_json`／`decisions`／`events_emitted`）、`test_an_enemy_trap_is_invisible_to_the_other_team`、`test_the_owner_team_sees_its_own_traps_only`、`test_a_trap_placed_by_the_enemy_is_visible_only_to_the_enemy`、`test_a_paused_state_has_a_view_with_only_the_public_pending_fields`、`test_the_view_is_deterministic_and_round_trips_through_json`。陷阱可見性使用 `traps.visible_traps`。
2. **`filter_events` 四條規則＋完整戰鬥**：通過。`tests/engine/test_event_filter.py`：`test_trap_placed_is_only_visible_to_the_owner_team`、`test_trap_expired_is_only_visible_to_the_owner_team`、`test_the_trap_skill_used_event_hides_the_tiles_from_the_other_team`、`test_trigger_limit_from_a_hidden_trap_is_only_visible_to_the_owner_team`、`test_trap_triggered_and_its_effects_are_visible_to_everyone`、`test_seq_values_are_preserved_so_the_filtered_list_has_gaps`、`test_a_full_battle_leaks_no_untriggered_trap_to_the_other_team`（build_trapper、open_plain、種子 7 的整場戰鬥）。
3. **`Pending.kind` 為 Literal、欄位在 `resolve`／`resume` 都正確、往返通過**：通過。`tests/engine/test_pending_serialization.py`（內建反應、格擋、反應技、連續兩次詢問；每個情境皆「直接 resume」對「`state_to_json`→`state_from_json`→`resume`」比對狀態 JSON、事件 JSON 與新 `Pending`，接受與拒絕各一次）。
4. **描述模組在 `trpg.narrative`、cli 不再定義、`describe_event` 無複雜度 noqa**：通過。`src/trpg/narrative/events.py`、`src/trpg/narrative/skills.py`；`grep -rn "def describe_event\|def effect_summary" src` 只在 narrative。`tests/narrative/test_events_text.py` 確認所有事件類型都有處理器或明列為靜默。
5. **CLI 輸出不變**：通過。`tests/cli/test_output_snapshots.py` 在搬家前以舊程式錄下 `skills list`、全部 62 個 `skills show`、7 場 `battle`（多張地圖、陷阱／火／推擊／守護／突擊／風暴 build）的 SHA-256，搬家後逐字比對一致；既有 CLI 測試全過。
6. **import-linter 新合約**：通過。`pyproject.toml` 新增「narrative 不得匯入 cli、api、roguelite、sim」，`uv run lint-imports` 為 4 kept、0 broken；`tests/test_architecture.py` 同步（`NARRATIVE_FORBIDDEN` 與正反各 3 個掃描器自我測試）。
7. **`scripts/check.py` 全過；複雜度 noqa 不增加**：通過（1516 passed；ruff、format、mypy、lint-imports、pytest 全部通過）。複雜度類 noqa（C901／PLR0911／PLR0912／PLR0915／PLR0917）在 src／scripts／tests 合計由 23 降為 20。
8. **`trpg battle --map open_plain --seed 7 --log-json f` 與 `trpg battle replay f`**：通過。輸出「重播驗證通過：94 個動作、320 個事件，最終狀態一致（open_plain，種子 7）。」

## 3. 複雜度 noqa

- 新增：無。
- 移除：`describe_event`（C901、PLR0911、PLR0912）、`_describe_environment`（C901、PLR0911、PLR0912）、`_effect_core`（PLR0911、PLR0912）。
- 總數：23 → 20。測試中的 `dependency_violations` 改用 `FORBIDDEN_BY_SOURCE` 表格以避免 PLR0912，未使用 noqa。

## 4. 修改既有測試期望值

無期望值修改。只改了匯入路徑：`tests/engine/test_cover.py`、`tests/engine/test_passive_triggers.py`、`tests/cli/test_striker_trapper_battle.py`、`scripts/skill_fuzz.py` 的 `describe_event` 改從 `trpg.narrative.events` 匯入。

## 5. 待 PM 決定

1. **`Pending.trigger_event_seq` 的判定**：依反應事件找本次結算中最近一個相符的事件（格擋類找對自己的 `attack_rolled`；`hit_by_*` 找對自己的 `damage_dealt`；`ally_hit_adjacent` 找攻擊者的 `attack_rolled`）。`enemy_leaves_adjacent`（藉機攻擊）的移動事件在詢問時還沒發出，所以為 `None`。若 3-4 的視窗需要，可再讓引擎在移動前先發事件，但會動到事件順序，本段未做。
2. **其他陣營單位的 `skills` 與陷阱技能冷卻**：視圖中他方單位的 `skills` 為空、`cooldowns` 不列陷阱技能。否則「放過陷阱的人，捕獸夾冷卻 2」會洩漏陷阱技能 ID（第一版測試就抓到）。代價是敵人的技能列表看不到；如要顯示敵方技能請 PM 指示。
3. **視圖對敵方單位的詳細程度**：目前敵方單位的法力、耐力、狀態、層數都完整給出（規格沒有要求隱藏）。若之後想做「看不見敵方資源」，在 `view.py` 的 `_unit_view` 調整即可。
4. **`filter_events` 簽名**：`filter_events(events, state, team)`，`state` 用來查單位陣營與技能是否為陷阱技能；必須是包含這些事件所涉單位的狀態（建議傳最新狀態，召喚／援軍後的單位不在較舊的狀態裡）。
5. **`TriggerLimitReached` 的判定**：以「技能有 `trap` 欄位」判斷是陷阱引起的，只給放置者陣營；被動與反應技的深度上限仍所有人可見。
6. **未調整 `LOG_FORMAT`**：`PendingResolution` 新增欄位都有預設值，狀態 JSON 在 `pending` 為 `null` 時不變，舊紀錄仍可讀取，`LOG_FORMAT` 維持 `trpg-battle-log/11`。
7. **`Pending.hp_cost_permille`**：除規格例舉的 `stamina_cost`、`mana_cost` 外，反應技也可能有 `hp_percent` 代價，所以多加了這一欄（千分比）；若不需要可移除。
8. **`SkillCard` 欄位為純文字**：`rarity`、`kind`、`category` 等已轉為中文字串（給網頁直接顯示），若 3-3／3-4 想要英文代碼對照，需再加欄位。
9. **`cli/skills.py` 不再 re-export `effect_summary`／`shape_summary`**：搜尋全專案沒有其他使用者，所以直接移除；`pad` 仍留在 cli。
10. **CLI 快照以雜湊儲存**（`tests/cli/snapshots/cli_output_hashes.json`），要刻意改輸出時用 `UPDATE_CLI_SNAPSHOTS=1` 重錄。

## 6. 代表性輸出節錄

技能卡片（`skill_card(lib, bear_trap)` 的 JSON，節錄）：

```json
{"id":"skill_bear_trap","name_zh":"捕獸夾","skeleton":"trap","scaling":"敏捷","ap_cost":2,
 "cost":["AP 2","法力 6","冷卻 2 回合"],"shape":"指定格（射程 4）",
 "effects":["放置隱藏陷阱：敵人踩上時觸發（3 輪後消失），以該格結算其餘效果（自己）",
            "1d8＋敏捷加成的物理傷害（敵方）","狀態「定身」 2 回合（敵方）"], ...}
```

陷阱視圖（我方放了捕獸夾於 (4, 3)）：

```
ally  traps= [('skill_bear_trap', 4, 3)]
enemy traps= []
```

反應詢問的公開資料（`resolve` 回傳的 `pending`，藉機攻擊）：

```json
{"kind":"reaction","unit_id":"unit_0001","reaction":"opportunity_attack","trigger_unit_id":"unit_0002",
 "skill_id":null,"trigger_event_seq":null,"stamina_cost":0,"mana_cost":0,"hp_cost_permille":0}
```
