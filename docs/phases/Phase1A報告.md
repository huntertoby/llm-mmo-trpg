# Phase 1A 完成報告

> 撰寫：實作者｜2026-10-17｜對應規格 `docs/phases/Phase1計畫.md` 第 1–5 節

## 摘要

依規格完成 Phase 1A（戰鬥核心）的全部交付項目：9 種元素與 4 組抗性、`content/rules/core.yaml` 與整數門檻命中表（附 `scripts/gen_hit_table.py`）、地形／武器／狀態／單位範本／地圖的 schema 與資料、確定性規則引擎（`start_battle`／`legal_actions`／`resolve`、先攻、回合與 AP、移動與路徑、視線、判定與傷害、可註冊的效果佇列、墜落與致命地形、勝負），以及 CLI（`trpg map show`、`trpg battle`、`--log-json`、`trpg battle replay`）。驗收條件 1–11 在本工作區全部通過（`uv run python scripts/check.py` 五項全過，306 個測試，含 3 個 hypothesis 屬性測試）。沒有實作 1B 的內容（物件、表面、環境回合、反應、預覽、效用 AI）。主要的實作者自行決定集中在「待 PM 決定」第 1–8 點（防禦動作 AP、單位 HP 數值、CLI 預設陣容等）。

## 驗收條件逐條結果

| # | 條件 | 結果 | 證據（指令與輸出摘要） |
|---|---|---|---|
| 1 | `scripts/check.py` 五項全過 | ✅ 通過 | `uv run python scripts/check.py` → ruff check、ruff format --check、mypy、lint-imports、pytest 全部「通過」，`全部檢查通過。`；pytest `306 passed`；lint-imports `Contracts: 2 kept, 0 broken.` |
| 2 | 確定性：同 setup／seed／動作列表結果相同；replay 通過；hypothesis 隨機種子重播一致 | ✅ 通過 | `tests/engine/test_determinism.py`：`test_same_seed_same_battle`（兩張地圖，比對最終狀態 JSON 與事件 JSON 字串）、`test_replay_matches`、`test_replay_from_serialized_log`、`test_property_random_seed_battle_replays`（hypothesis，種子 0–2⁶⁴−1，兩張地圖，整場簡易 AI 對戰後重播一致）。CLI：`trpg battle --map test_heights_8x8 --seed 42 --log-json b42.json` 後 `trpg battle replay b42.json` → `重播驗證通過：77 個動作、171 個事件，最終狀態一致`；竄改 `final_state` 後 → `重播驗證失敗：最終狀態不一致`，rc=1 |
| 3 | 純函式：`resolve` 前後原狀態不變 | ✅ 通過 | `test_resolve_does_not_modify_input_state`（150 步隨機動作，每步比對 resolve 前後的 `state_to_json`）、`test_illegal_action_does_not_modify_state`、`test_run_effects_is_pure`，以及 hypothesis `test_property_arbitrary_actions_are_legal_or_rejected`（任意動作後原狀態 JSON 不變） |
| 4 | 序列化：`BattleState`、`Action`、`Event` JSON 往返相等 | ✅ 通過 | `test_state_json_round_trip_through_a_battle`（開場與結束狀態：`state_from_json(state_to_json(s)) == s` 且再序列化字串相同）、`test_actions_and_events_round_trip`、`test_battle_log_round_trip` |
| 5 | 判定：門檻表與高精度一致；命中率表窮舉成立；優劣勢抵消；自然 1／20；暴擊骰加倍 | ✅ 通過 | `tests/content/test_rules.py`：`test_hit_table_matches_high_precision_recomputation`、`test_thresholds_are_exact_ceilings`（以 `Fraction` 精確驗證每個門檻是正確的無條件進位，含 slope 1/3/4/5）、`test_modifier_matches_exact_formula_on_grid`（攻擊 1–60 × 防禦 1–60 共 3600 組與精確公式一致）、`test_generated_file_is_up_to_date`。`tests/engine/test_combat.py`：`test_hit_rate_table_exhaustive`（窮舉 d20：1 倍 60%、2 倍 80%、4 倍與以上 95%、一半 40%、1/4 與以下 20%）、`test_advantage_and_disadvantage_probabilities`（窮舉 400 組）、`test_combine_advantage`、`test_advantage_and_disadvantage_cancel_rolls_one_die`（抵消時只擲 1 顆）、`test_natural_one_misses_even_with_huge_bonus`（修正 +8 仍失手）、`test_crit_doubles_dice_not_flat`（1d8 暴擊擲 2 顆，固定值不加倍）、`test_crit_range_requires_hit` |
| 6 | 移動：爬升成本、兩層不可上、墜落 10%／層上限 30%、不可穿過敵人、路徑確定 | ✅ 通過 | `tests/engine/test_movement.py`：`test_climb_costs_extra`、`test_two_levels_up_is_impassable`、`test_fall_damage`（落差 1／2／3 → 0／10／20 HP）、`test_fall_damage_capped_at_30_percent`（每層改 200‰ 時 2 層 = 40% → 30）、`test_forced_move_down_cliff_also_falls`、`test_cannot_pass_enemy_can_pass_ally`、`test_find_path_is_deterministic_with_fixed_tie_break`（固定路徑且與 `legal_actions` 的代表路徑一致） |
| 7 | 致命地形：一般單位強制位移進深淵死亡；elite 受 30% 並移到最近安全格（同距依固定順序） | ✅ 通過 | `tests/engine/test_effects.py`：`test_normal_unit_forced_into_chasm_dies`、`test_normal_unit_into_lava_dies`、`test_elite_takes_30_percent_and_moves_to_nearest_safe_tile`（80 → 56，傳送到 (1, 0)）、`test_elite_safe_tile_tie_order_skips_occupied`（(1, 0) 有人 → (0, 1)）、`test_elite_killed_by_terrain_damage_is_not_relocated` |
| 8 | 元素修正：分組抗性 × 個別弱點、75% 減傷上限 | ✅ 通過 | `test_element_modifier`（10 組：分組、跨組、弱點、0.8×1.5、0.8×0.5、下限 0.25、負抗性、物理抗性不影響冰霜）、`test_element_modifier_applied_to_damage`、`test_damage_minimum_one_on_hit`（100% 抗性 → 修正 0.25 → 1 點） |
| 9 | AP：每回合 3、保留上限 1、不足時中文原因 | ✅ 通過 | `tests/engine/test_turns.py`：`test_ap_per_turn_and_carry`（用 2 留 1 → 4；不用 → 4；用光 → 3）、`test_ap_shortage_is_rejected_with_reason`（`AP 不足：需要 1，剩餘 0`）、`test_ap_values_come_from_rules`（改 core 數值即生效） |
| 10 | CLI：`trpg battle --map test_heights_8x8 --seed 42` 跑完並分出勝負，輸出可讀 | ✅ 通過 | 實際執行 rc=0，4 輪、77 個動作，`戰鬥結束：敵方勝利（全滅）`，每輪印出網格、單位狀態與中文紀錄（節錄見本報告附錄）。`tests/cli/test_battle_cli.py` 13 個測試（含同種子輸出逐字相同、`--rounds-max` 平手、log／replay、竄改偵測、參數錯誤） |
| 11 | 不合法動作拋出 `IllegalActionError`；`legal_actions` 的每個動作都能 `resolve` | ✅ 通過 | hypothesis `test_property_every_legal_action_resolves`（隨機策略走過的局面中，`legal_actions` 每一個動作都 `resolve` 成功、無重複、最後一個是 `EndTurn`、`has_only_end_turn` 與之一致）、`test_property_arbitrary_actions_are_legal_or_rejected`（任意行動者／路徑／目標只會成功或拋出帶訊息的 `IllegalActionError`）；各種錯誤訊息另有單元測試（射程、視線、友方、路徑不連續、高度差、深淵、移動點數不足、非本人回合、戰鬥已結束……） |

## 實際執行的驗證指令

```bash
cd /home/claude/LLM-MMO-TRPG
export NO_PROXY=localhost no_proxy=localhost   # 本工作區每個指令前都要設定

# 1) 安裝與一鍵檢查（使用者電腦同樣是這兩行，不需要 export）
uv sync
uv run python scripts/check.py

# 2) 個別測試群組
uv run pytest -q tests/engine                     # 引擎（104 個測試）
uv run pytest -q tests/content tests/cli          # 內容 schema 與 CLI
uv run lint-imports

# 3) 命中表
uv run python scripts/gen_hit_table.py --check    # → hit_table.yaml 為最新

# 4) CLI
uv run trpg content check
uv run trpg map show test_heights_8x8
uv run trpg battle --map test_heights_8x8 --seed 42
uv run trpg battle --map test_heights_8x8 --seed 42 --log-json /tmp/b42.json
uv run trpg battle replay /tmp/b42.json          # → 重播驗證通過
python3 -c "import json;d=json.load(open('/tmp/b42.json'));d['final_state']['units']['unit_0001']['hp']=99;json.dump(d,open('/tmp/bad.json','w'))"
uv run trpg battle replay /tmp/bad.json; echo rc=$?   # → 重播驗證失敗：最終狀態不一致，rc=1

# 5) 效能基準
uv run python scripts/bench_battle.py
```

## 效能基準

`uv run python scripts/bench_battle.py`（本工作區，Python 3.12.3，各重複 20 次取中位數；地圖 `test_heights_8x8`、預設陣容、種子 42）：

| 情境 | 輪數 | 動作數 | 事件數 | 整場時間（含簡易 AI） | 重播時間（只有 `resolve`） | 每個 `resolve` 平均 | 每個動作平均（含 AI） |
|---|---|---|---|---|---|---|---|
| 示範戰鬥（同 `trpg battle --seed 42`） | 4 | 77 | 171 | 20.6 ms | 7.9 ms | 102 µs | 268 µs |
| 10 輪戰鬥（HP ×5、`max_rounds=10`） | 10 | 224 | 434 | 58.3 ms | 24.2 ms | 108 µs | 260 µs |

- 200 個種子的批次（不含輸出）：`test_heights_8x8` 平均 20 ms／場、4.2 輪、77 個動作；`test_flat_6x6` 平均 16 ms／場。換算單核心約 50–60 場／秒，十萬場約 30 分鐘。
- 一個 `resolve` 的成本主要是：狀態複本（每個單位 `dataclasses.replace`）、`Rng.from_state`、pydantic 事件與效果 model 的建立。簡易 AI 的成本主要是不限成本的 Dijkstra 與每格的視線計算。
- 開發中做過的一次最佳化：驅動迴圈原本每步呼叫 `legal_actions`（為每個可達格建立 `Move` 與 `Pos`）只為判斷「是否只剩 EndTurn」，佔總時間約 60%；改成 `has_only_end_turn` 快速判斷，並把地形／狀態查詢改成索引後，每個動作從約 650 µs 降到約 260 µs（結果逐位元相同）。
- Phase 2 若需要更快，可考慮：事件與效果改用 `model_construct`（略過驗證）、`Pos` 在引擎內部改用整數座標、AI 共用一次 Dijkstra 結果、以多處理程序平行跑場次。

## 與規格的差異

1. **`content/rules/core.yaml` 多了幾個鍵**（規格寫「至少包含」）：`basic_attack_ap_cost`（1）、`defend_ap_cost`（1）、`initiative_attr_base`（10）／`initiative_attr_divisor`（2）、`min_damage_on_hit`（1）、`max_climb_height`（1）、`fall_damage_min_drop`（2）、`prone_stand_up_move_permille`（500）、`max_chain_depth`（3）。目的是讓計畫中出現的數字都不寫死在程式裡。
2. **新增 `begin_battle(setup, seed) -> ResolveResult`**：規格的 `start_battle` 只回傳狀態，但開場會產生事件（`battle_started`、`initiative_rolled`、`turn_order_set`、`round_started`、第一位的 `turn_started`），重播與紀錄需要它們。`start_battle` 照規格保留，等於 `begin_battle(...).state`。
3. **`shared.types` 新增 `Team`**（`ally`／`enemy`，含 `display_name`、`opponent`）：地圖起始區與引擎共用。
4. **`legal_actions` 的移動以「每個可達格一條代表路徑」列出**（Dijkstra 的確定性最短路徑）；`resolve` 仍接受任何合法路徑。完整列舉所有路徑是指數級。
5. **新增 `has_only_end_turn(state)`**：與「`legal_actions` 只剩 `EndTurn`」等價（有屬性測試），驅動迴圈用它避免每步建立整個動作列表。
6. **戰鬥狀態內嵌整份 `Ruleset`**（核心數值、命中表、地形、狀態定義），`BattleSetup` 內嵌地圖、單位範本與武器。如此「初始狀態 ＋ 動作列表」的重播不依賴當下的資料檔；代價是狀態 JSON 約 10 KB、戰鬥紀錄 JSON（`--log-json`）約 70 KB。
7. **地圖的 `objects`、`surfaces` 在 1A 載入時必須為空**（`ContentError`：「目前（Phase 1A）尚未支援」）。schema 已定義（`at`、`kind`／`surface`），1B 移除這項檢查即可。
8. **連通性檢查比規格嚴格**：要求「每一個起始格都能走到對方起始區的至少一格」，且依實際移動規則（往上一步最多 1 層）做有向判斷——因為往下可以走、往上不一定能爬，單向可達不夠。
9. 額外檔案：`scripts/bench_battle.py`（效能基準）、`src/trpg/cli/render.py`（中文渲染器）、`src/trpg/cli/battle.py`。README 的「目前進度」與 CLI 範例已更新，`content/README.md` 補上新資料檔。

## 待 PM 決定

1. **防禦動作的 AP 消耗**：規格沒寫。目前 `defend_ap_cost: 1`，已在防禦姿態中時不能再防禦（「已處於防禦姿態」）。也可以考慮「消耗剩餘全部 AP」或「結束回合」。
2. **單位數值**：每回合 3 AP 且普攻 1 AP，一回合可普攻 3 次，若用一般 TRPG 的 HP（20–40）戰鬥 2–3 輪就結束。目前 HP 為戰士 60、弓手 46、法師 40、盜賊 30、盜賊弓手 26、盜賊頭目 80，示範戰鬥約 4–5 輪。屬性、護甲、抗性都是實作者擬定，請 PM 調整（Phase 2 模擬後再定）。
3. **CLI 預設陣容**：地圖格式沒有遭遇欄位，`trpg battle` 預設我方 `hero_fighter, hero_archer, hero_mage`、敵方 `bandit, bandit_archer, bandit_boss`（可用 `--allies`／`--enemies` 覆寫）。200 個種子中我方勝率：`test_heights_8x8` 56%、`test_flat_6x6` 54%。種子 42 的示範戰鬥是敵方勝利。
4. **岩漿不可主動進入**：規格只說 `chasm` 不可主動進入；目前 `lava` 也設為 `walkable: false`（地形表的資料，可改）。若允許主動走進岩漿，需要決定後果（直接死亡？）。
5. **暴擊範圍需要命中**：匕首自然 19 若未命中則不暴擊（只有自然 20 必定命中）。預設數值下自然 17 以上必定命中，所以實際上幾乎沒有差別。
6. **墜落與致命地形的傷害**：以最大 HP 比例計算，**不套用元素修正與抗性**（否則 30% 上限的語意會被抗性改變），最低 1 點。事件中的元素記為物理。
7. **近戰與高度**：相鄰即可近戰，不論高度差多少；高度修正只看高低，不看差幾層（高打低 +2、低打高 −2）。遠程攻擊相鄰目標沒有懲罰；單位不阻擋視線。
8. **倒地站起**：沒有獨立的「站起」動作，而是倒地時的 `Move` 先自動站起（消耗 `ceil(速度 × 50%)` 移動點數，產生 `unit_stood_up`）；`path` 只有起點時表示「只站起來」。倒地時仍可攻擊。
9. **先攻平手**：依 Phase 1 規格以單位 ID 排序；`docs/專案計畫.md` 5.0 寫的是「同值以種子亂數決定」，兩者不同，目前照階段規格。
10. **輪數上限**：`BattleSetup.max_rounds` 到達時以平手結束（`battle_ended`，`winner: null`，`reason: round_limit`）；CLI `--rounds-max` 預設 30。是否應該算敵方勝利（我方未能擊敗敵人）？
11. **效果佇列的排序細節**：「來源單位 ID → 目標 ID → 格子座標」中，沒有來源的效果（環境、狀態）排在最前；座標以 `(y, x)` 比較；鍵完全相同時保留產生順序（穩定排序）。例如精英掉進深淵時，「30% 傷害」先於「傳送到安全格」結算；若傷害致死就不再傳送。
12. **最近的安全格**：以曼哈頓距離計，同距離依 `y` 再依 `x` 由小到大；安全格 ＝ 地形可站立且沒有其他存活單位（不要求可走到）。找不到安全格時精英只受傷害、留在原地（實務上不會發生）。傳送不觸發墜落。判斷精英只看 `elite` 標籤（`boss` 不自動視為精英）。
13. **`concealed` 狀態** 標示為 1B，未放入 `statuses.yaml`。`steadfast` 標籤已在資料中，但 1A 沒有推擊，尚未使用。
14. **狀態與死亡的細節**：倒下的單位保留在 `units` 中（`downed: true`、HP 0），不佔格子、不能被治療（沒有復活）；持續傷害的 `source_id` 記為施加者；行動者在自己回合中倒下（例如低 HP 走下懸崖）時立即換下一位。
15. **防禦值下限**：`敏捷 ＋ 護甲` 最低視為 1；攻擊值 ≤ 0 時命中修正為 −cap。
16. **命中表的進位方式**：門檻以無條件進位存成整數，整數判斷永遠不會給出比真實值更高的修正；只有比例落在門檻上方不到 10⁻⁶ 相對誤差時會低 1（測試中 3600 組整數比例皆與精確值相同）。`hit_slope` 必須是正整數（精確驗證依賴這點；若要非整數斜率需改用 `Fraction` 驗證）。
17. **視線不對稱**：Bresenham 從攻擊者畫向目標，A 看得到 B 不保證 B 看得到 A（少數斜線情況）。若要對稱，可改成「兩個方向任一條通過」或「兩條都要通過」。

## 給下一階段的備註

（給 Phase 1B 實作者）

- **API 與模組**：`trpg.engine` 匯出 `start_battle`、`begin_battle`、`legal_actions`、`resolve`、`BattleSetup`、`build_setup`、`state_to_json`／`state_from_json`。模組：`state`（dataclass 狀態）、`actions`／`events`（pydantic discriminated union）、`battle`（API 與動作處理器表 `ACTION_HANDLERS`）、`turns`（回合流程與勝負）、`rules/`（`geometry`、`movement`、`combat`）、`effects/`（`models`、`queue`、`handlers`）、`triggers`（事件 → 效果）、`ai/simple`、`runner`。
- **新增效果類型**：在 `effects/models.py` 新增 model（`kind` 為 Literal）並加入 `Effect` union，再以 `@register_effect("push")` 註冊處理器（簽名 `(ctx, effect) -> list[EventBase]`，事件以 `ctx.emit(EventCls, ...)` 建立）。處理器回傳的事件會自動經過觸發表，`depth` 由佇列管理。
- **元素 × 標籤互動、反應**：以 `@register_trigger("damage_dealt")` 這類觸發函式掛上（簽名 `(ctx, event, depth) -> list[EffectBase]`，新效果請帶入 `depth`）。互動表建議做成一個讀 `content/interactions.yaml` 的通用觸發函式。測試可用 `monkeypatch.setitem(triggers._TRIGGERS, ...)` 暫時掛上 fixture 觸發（見 `test_chain_limit`）。
- **暫停點（`resume`）**：目前 `effects.queue.execute` 的佇列是區域變數。要支援 `prompt` 反應暫停，需要把「剩餘佇列」與「暫停中的動作脈絡」移進 `BattleState`（效果已是可序列化的 pydantic model，`EFFECT_LIST_ADAPTER` 可直接用），`ResolveResult.pending` 已預留。
- **環境回合的掛點**：`turns.advance_turn` 中 `RoundEnded` 與 `RoundStarted` 之間（目前只檢查輪數上限）。`telegraph` 建議在 `state.clone()` 上執行同一段環境邏輯，確保預告與實際一致。
- **物件與表面的掛點**：`rules/movement.is_standable`／`is_deadly`（`blocks_move`、`over_chasm` 木橋）、`rules/geometry.has_line_of_sight`（`blocks_sight`、`darkness`、濃霧）、`rules/combat.advantage_sources`（`concealed`、天氣）。`Tile` 已有 `surface` 與 `object_id` 欄位；`Tile` 是不可變的，改變格子時替換 `state.tiles` 中的元素（`tiles` 是 tuple，需重建；若頻繁可改成 list 並在 `clone` 時複製）。
- **攻擊物件**：`Attack.target_id` 目前是 `UnitId`；1B 需要擴充（例如新增 `target_object_id` 或改成 `target: {kind, id}`，與計畫 5.3 的意圖 schema 一致）。
- **骰子控制**：測試用 `tests/engine/helpers.py` 的 `with_rolls(state, [(20, 20), (8, 5)])` 把 `rng_state` 設為接下來依序擲出指定點數的狀態（搜尋種子），可用於 1B 的預覽一致性測試。`make_map`／`spawn`／`template`／`make_setup(**core)` 可快速建構小地圖與修改規則數值。
- **AI**：簡易 AI 在 `engine/ai/simple.py`，決策函式型別 `Policy = Callable[[BattleState], Action]`；效用 AI 可放在同一個套件，CLI 與 `runner.run_battle` 只需換 `policy`。
- **重播格式**：`runner.BattleLog`（`format: "trpg-battle-log/1"`、`seed`、`setup`、`actions`、`events`、`final_state`）。新增事件或狀態欄位會改變 JSON，舊紀錄不一定能重播；若需要相容，記得遞增 `LOG_FORMAT`。
- **數值調整**：改 `content/units/*.yaml` 或 `rules/core.yaml` 後，可用 `scripts/bench_battle.py` 或自行跑 `runner.run_battle` 多個種子看勝率與輪數；改 `hit_slope`／`hit_mod_cap` 後執行 `uv run python scripts/gen_hit_table.py`。

## 附錄：`trpg battle --map test_heights_8x8 --seed 42` 輸出節錄

```text
戰鬥開始：測試高台（8×8），種子 42
先攻：戰士 d20=15 +1 = 16
先攻：弓手 d20=9 +3 = 12
先攻：法師 d20=16 +1 = 17
先攻：盜賊 d20=11 +2 = 13
先攻：盜賊弓手 d20=14 +2 = 16
先攻：盜賊頭目 d20=3 +0 = 3
行動順序：法師 → 戰士 → 盜賊弓手 → 盜賊 → 弓手 → 盜賊頭目

=== 第 1 輪 ===
    0  1  2  3  4  5  6  7
 0  0. 0. 0. 0. 0. 0. 0a 0b
 1  0. 0. 1. 1. 1. 1. 0c 0.
 2  0. 0. 1. 2# 2# 1. 0. 0.
 3  0. 0. 1. 2. 2. 1. 0. 0.
 4  0. 0. 1. 1. 1. 1. 0. 0.
 5  0. 0. 0. 0. 0. 0. 0. 0.
 6  0A 0B 0. 0. 0. 0. 0. 0.
 7  0C 0. 0. 0. 0. 0. 0. 0.
  A 我方 戰士：HP 60/60 位置 (0, 6) 武器 單手劍
  ……
— 法師 的回合（AP 3，移動 5）
  法師 從 (0, 7) 移動到 (4, 6)（消耗 5 移動）
  法師 獲得狀態「防禦」
  法師 結束回合，保留 1 AP
……
— 盜賊頭目 的回合（AP 3，移動 5）
  盜賊頭目 從 (6, 1) 移動到 (5, 5)（消耗 5 移動）
  盜賊頭目 攻擊 戰士：d20=17 修正 -1 熟練 +2 = 18（目標 11）→ 命中
    戰士 受到 9 點物理傷害［骰 4+2］（元素修正 ×0.9），HP 60 → 51
……
— 盜賊弓手 的回合（AP 3，移動 5）
  盜賊弓手 攻擊 弓手：d20=20 修正 -1 熟練 +2 = 21（目標 11）→ 自然 20，暴擊！
    弓手 受到 11 點物理傷害［骰 5+2］，HP 21 → 10
  盜賊弓手 攻擊 弓手：d20=15 修正 -1 熟練 +2 = 16（目標 11）→ 命中
    弓手 受到 12 點物理傷害［骰 8］，HP 10 → 0
  ＊ 弓手 倒下了！
戰鬥結束：敵方勝利（全滅）

=== 結算 ===
勝方：敵方勝利（第 4 輪結束，77 個動作，171 個事件）
  代號 單位          造成傷害 承受傷害 命中/攻擊 暴擊 擊倒 結果
  A    我方 戰士           42       67    6/7       0    0 倒下
  B    我方 弓手           33       48    4/9       0    1 倒下
  C    我方 法師           26       43    3/4       0    0 倒下
  a    敵方 盜賊           11       39    2/7       0    1 倒下
  b    敵方 盜賊弓手       78        0    8/11      1    2 HP 26/26
  c    敵方 盜賊頭目       69       62    7/9       0    0 HP 18/80
```
