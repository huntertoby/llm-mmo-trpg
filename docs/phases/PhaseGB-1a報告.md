# Phase GB-1a 報告｜巨型頭目：佔格與基礎

> 實作者（Opus 5.5），2026-11-14，起點 main `b15e46210`。規格：`docs/phases/PhaseGB計畫.md` 第 0 節（T1～T4、T6、T8、T10、T13、T19）、第 4 節 GB-1a 列、5.1、5.4～5.6。R1～R7 相關的行為（距離改量最近格、範圍去重、出招起點、部位綁格）**沒有碰**，留給 GB-1b、1c。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 內容 schema 與檢查（T13） | `UnitTemplate.footprint`（只收 1、3；>1 要 `boss` 標籤、不是召喚物；1 不輸出）、`MapDef.giant_facing`（範本 ID → 方向；空不輸出）、新檔 `content/library/giant_checks.py::giant_problems`（`load_library` 在大世界載入後呼叫 `_check_giants`） | `2093ed390` |
| 引擎（T1～T4、T6、T8、T10、T19） | 新檔 `engine/rules/footprint.py`；`UnitState.footprint`（三處同步：欄位、`clone()`、序列化 `exclude_if`）＋ `UnitState.covers`；佔格、視線、位移免疫、固定朝向、地形；開場放置；`LOG_FORMAT` `/125` → `/126` | `c3f32b14d` |
| 測試 | `tests/engine/test_giant_gb1a.py`（23 項）、`test_footprint_gb1a.py`（4 項，hypothesis）、`tests/content/test_giant_content_gb1a.py`（14 項）；合成巨人 `tests/engine/helpers.py::giant_template`／`spawn_giant` | 同上兩個 |
| 文件 | `docs/phases/戰鬥紀錄格式變更.md` 加 `/126`；本報告；`docs/dev/上手-引擎戰鬥結算.md`（第一節 `rules/footprint.py`、第二節「巨型單位」、第四節第 48、49 點、第五節測試列） | 第 3 個 commit |

`content/` 一個字都沒改。

## 2. 逐條驗收

| 驗收（5.6） | 結果 | 證據 |
|---|---|---|
| 1. 分 commit、報告、上手筆記、格式變更文件 | 過 | 上表 |
| 2. `ruff check`／`ruff format --check`／`mypy`／`lint-imports` | 各自結束碼 0 | `All checks passed!`；`2705 files already formatted`；`Success: no issues found in 1605 source files`；`Contracts: 14 kept, 0 broken.` |
| 3. 相關測試（不帶 `-m`、`-n 8`） | 1026 passed，結束碼 0 | 新三檔＋`test_determinism`、`test_skill_determinism`、`test_status_determinism`、`test_state_clone`、`test_pending_serialization`、`test_combat`、`test_effects`、`test_skill_shapes`、`test_skill_primitives`、`test_reactions`、`test_preview`、`test_boss_parts_pb1`、`test_parts_ai_pb1`、`test_delayed_anchor_bal21`、`test_lava_splash_bal21b`、`test_runner_advance`、`test_ruleset_hash`、版號三檔（`test_collided_sacrifice_firearm`、`test_self_costs`、`test_wind`）、`test_gear_g2`、`test_gear_g3a`、改到的路徑（`test_ice_slide`、`test_landing`、`test_facing_backstab`、`test_turn_on_melee_hit`、`test_displace_others`、`test_runes`、`test_traps`、`test_surface_triggers`、`test_practice_mode`）、`tests/content/` 的 `test_loader`、`test_battle_content`、`test_map_archetypes`、`test_map_reachability`、`test_boss_parts_content`、`tests/test_architecture.py`、版號字面值的 6 個 CLI 測試檔 |
| 4. 一場紀錄＋重播 | 三場都「重播驗證通過」，`battle`／`replay` 結束碼都 0 | `molten_heart_pit` 2：113 動作 617 事件；`oil_depot` 13：102 動作 454 事件；`swamp` 21：54 動作 240 事件 |
| 5. 不變比對 `different=0` 與三個雜湊 | 過 | 第 3 節 |
| 6. CLI 快照（slow）與 `tests/narrative/` | 過：24 passed、475 passed，結束碼都 0 | 第 4 節 |
| 7. 新增 `# noqa` | 沒有 | 第 6 節 |

5.5 行為一致測試對到的列（本段範圍內）：

| 5.5 列 | 測試（`tests/engine/test_giant_gb1a.py`） |
|---|---|
| 1 佔格 | `test_d3_all_nine_tiles_belong_to_the_giant`（`unit_at`、`occupancy`、`landing_problem`、`nearest_free`）、`test_d3_paths_go_around_the_giant_even_for_its_allies`（敵我兩種巨人都繞路）、`test_d3_nothing_can_be_put_on_the_giant_tiles`（障礙物、符文、表面跳過不發事件、召喚、陷阱、傳送落點）、`test_d3_giants_are_placed_first_and_others_skip_their_tiles`、`test_d3_explicit_positions_cannot_overlap_the_giant` |
| 6 視線 | `test_d7_the_body_blocks_sight_behind_it_but_not_to_itself`（含拋射、北排、`ignore_unit`）、`test_d7_one_tile_units_still_do_not_block_sight` |
| 7 位移 | `test_d8_the_giant_never_moves_or_falls_prone`（推、拉、換位、被傳送、自己傳送、倒地、滑行 7 列）、`test_d8_the_giant_has_no_move_budget`、`test_t6_one_tile_immovable_units_keep_todays_rules`（源晶柱照舊被換位、被擊倒） |
| 8 朝向 | `test_d9_facing_comes_from_the_map_and_never_turns`（`face_toward`、`after_attack` 的轉身）、`test_t8_behind_is_the_column_outside_the_back_face`、`test_t8_without_an_entry_the_giant_keeps_the_team_facing` |
| 9 地形 | `test_d10_deadly_terrain_under_the_giant_does_nothing`（佔格含岩漿開場、改地形、降高度）、`test_d10_surfaces_under_the_giant_are_cleared_and_never_entered` |
| 14 確定性 | `test_same_seed_same_battle_and_the_log_replays`（同種子兩次相同、`BattleLog` JSON 往返後重播一致）、`test_clone_and_json_keep_the_footprint_and_one_tile_json_is_unchanged` |
| T2 | `test_footprint_gb1a.py`：一格時 `tiles_of`、`nearest_tile`、`dist_to`、`unit_dist`、`adjacent`、`occupies` 與 `manhattan` 逐值相同（hypothesis）；3×3 時等於逐格取最小；12 個外圍相鄰格、4 個斜角不算 |
| T13 | `tests/content/test_giant_content_gb1a.py`：預設不輸出、只收 1／3、要 `boss`；`giant_facing` 往返；現有內容沒有問題；乾淨的頭目地圖通過；非頭目地圖、9 格有表面／物件／站不上去／高度不一致、一般遭遇、同伴、大世界非頭目地點都擋；`giant_facing` 寫不存在的範本擋 |

5.5 的 2（距離、相鄰、藉機攻擊）、3（範圍）、4（自身為中心）、5（出招起點）是 GB-1b；10～13 是 GB-1c；「暫停點中途 `resume`」的確定性列沒寫（巨人目前沒有任何會暫停的互動，GB-1b 有距離後再補）。

## 3. 不變比對（5.4）

腳本在 scratchpad（未 commit），比照 BS-1：改前用 `git archive b15e46210 src content` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；每場比對完整事件 JSON、步驟、輪數、勝方、最終 `rng_state`、最終狀態 JSON（拿掉 `final_state.ruleset`、`setup.ruleset`）。**沒有剝掉任何其他鍵**：新欄位 1／空值不輸出，改前改後的 JSON 直接相等。

- 8 張地圖 × 種子 1、2 ＋ 3 張頭目圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`）× 種子 3～12：**`battles=46 events=20499 different=0`**（事件總數與 RG-5b 報告相同）。
- 三個雜湊改前＝改後：

| | 改前 `b15e46210` | 改後 |
|---|---|---|
| `hash_ruleset` | `ae4b48df32333cb93b62e7ce9a6eec7b277426cf46168c5633e9438abb54b050` | 同左 |
| `ruleset_hash`（一輪存檔） | `6e0f469df0d803ae1c4f21f054367fc503014d428c4fa58570c7b22eb410efbb` | 同左 |
| `content_digest`（世界日誌） | `50be396d464667cb2bb6fce086afda832b2f596f2a1fdd4c1c263a6da41c8883` | 同左 |

## 4. 快照與既有測試的變動

- **CLI 快照預測：24 鍵全部不變**（戰鬥鍵都是一般地圖、沒有巨型單位；技能卡沒改；戰鬥紀錄的版號不進快照雜湊）。實跑 `tests/cli/test_output_snapshots.py -m slow`：見下方結果；**沒有重產任何鍵**。
- `tests/narrative/`：見下方結果。
- 改動的既有測試只有版號字面值：`trpg-battle-log/125` → `/126`（`tests/cli/` 6 檔、`test_gear_g2.py`、`test_gear_g3a.py`），`LOG_FORMAT.endswith("/125")` → `"/126"`（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`，三個都是「跑一場再重播、最終狀態相同」，重播仍一致後才改）。沒有換種子、沒有放寬斷言。

交件前結果：`tests/cli/test_output_snapshots.py -m slow -n 8` **24 passed**（結束碼 0，預測 0 鍵變動＝實際 0 鍵）；`tests/narrative -n 8` **475 passed**（結束碼 0）。

## 5. 改了哪些呼叫點（檔案 × 處數）

| 檔案 | 處 | 說明 |
|---|---|---|
| `engine/state.py` | 3 | `UnitState.footprint`＋`covers`；`unit_at`、`occupancy` 認佔格（一格的單位走原本的比較）；`clone()` |
| `engine/rules/footprint.py` | 新檔 | T2 全部函式＋`giant_at` |
| `engine/rules/geometry.py` | 1 | `has_line_of_sight(..., ignore_unit=)`；沒有巨人時多一次空集合判斷，結果不變 |
| `engine/rules/movement.py` | 2 | `path_map` 巨人格連友方也不能穿；`available_move_budget` 巨人回 `None` |
| `engine/rules/facing.py` | 2 | `face_toward` 巨人不轉；`is_behind` 巨人看背面外側一排 |
| `engine/battle.py` | 3 | `_place_units`（指定位置的巨人佔 9 格、沒指定的先放）、`_giant_cells`／`_giant_cell_ok`／`_place_giants`、`_settle_placement`（固定朝向、清表面，並把 `mark_lone_wolves` 收進來） |
| `engine/effects/handlers.py` | 3 | `_move_unit`（任何模式）、`_swap_units`、`_status_blocked`（倒地） |
| `engine/effects/world.py` | 5 | `_resist_reason`、`push_distance`、`set_surface`（跳過）、`_inscribe`（`occupied`）、`_change_tile`（跳過） |
| `engine/effects/surface_entry.py` | 1 | `enter_surface` 巨人回空（規格列表外，T10） |
| `engine/heights.py` | 1 | `change_height` 佔格跳過（規格列表外，D10「高度一致」） |
| `engine/ice_slide.py` | 1 | `slide_next_block` 撞到巨人任一格 |
| `engine/basics.py` | 1 | 攀爬、跳躍落點的 `_unit_on` 改用 `state.unit_at`（規格列表外；一格的單位逐值相同：同樣依 ID 排序、只看存活） |
| `engine/lifecycle.py` | 1 | `make_unit` 帶 `footprint`（規格列表外，必要） |
| `engine/runner.py` | 1 | `LOG_FORMAT` |
| `content/library/load.py`、`giant_checks.py` | 新增 | T13（規格列表外的「內容檢查」程式；只讀） |

**刻意不改**：`rules/landing.py`、`skills/targeting.py::summon_site_problem`／`_trap_site_problem`、`effects/world.py::_create_obstacle`、`hurl_landing`、`object_push_block`、`unit_push_block`、`_topple_*` 都透過 `unit_at`／`occupancy`／`nearest_free` 自動認佔格，不必動。所有 `manhattan(..., unit.xy)`、相鄰、範圍收人、`back_xy`（`parts.py:197`）是 GB-1b、1c。`boss_phases.py` 的召喚落點走 `nearest_free`，自動避開佔格；規格表列的 `content/battle.py` 以外的 `boss_phases.py` 沒改。

## 6. 新增 `# noqa`

沒有。`begin_battle` 加一行後撞到 `PLR0915`（51 > 50），改成把「巨人朝向、清表面」和原本的 `mark_lone_wolves` 收進同一個 `_settle_placement`，不加 noqa。

## 7. 規格沒寫到、採保守做法的地方

1. **巨人的位移一律擋**：規格只列推、拉、換位、傳送、擊退、倒地、滑冰；`_move_unit` 對巨人**任何模式**（含 `walk`、`dash`、`leap`、`slide`）都發 `move_blocked`（`immovable`），`available_move_budget` 回 `None`（第一版不做會移動的多格單位）。
2. **倒地免疫的事件**：照 `race_stonewall` 的寫法在 `_status_blocked` 擋，`effect_fizzled` 原因 `immovable`（對抗照常擲，所以亂數取用和被穩若磐石擋的一樣）。紀錄文字沒有這個原因的中文（`narrative/` 不在本段範圍，`_FIZZLE_TEXT` 查不到就不顯示）。
3. **換位**：任一方是巨人就不交換，對巨人發 `move_blocked`（`to_pos` 是另一方的格子），另一方也不動。
4. **佔格上的地形與高度變化整個跳過**（`_change_tile`、`change_height`），不發事件：照 D10「佔的格子高度一致」與 D3「不能放表面」；規格沒明寫地形變化。
5. **符文**：佔格上刻符文 `effect_fizzled`（`occupied`）——一格的單位腳下照舊可以刻。
6. **開場放置**：沒指定位置的巨人在其他單位之前、照 `setup.units` 順序放進陣營起始區第一個「9 格都在地圖內、不是牆、沒被佔」的格子（中心格要可站）。非中心格允許致命地形（D10），可站、同高、沒物件表面由內容檢查擋（引擎不重驗，避免和內容檢查兩套標準）。指定位置的巨人：中心格照舊驗、其他 8 格驗在地圖內、不是牆、不重疊。
7. **`is_behind`（T8）**：巨人朝向的背面那一排外側相鄰的 3 格才算背後（斜角不算）；`back_xy` 對巨人仍回中心往後一格（在自己身上，等於沒有），`parts.py` 的 `need_behind` 讀它，留 GB-1c。
8. **內容檢查的大世界部分**：有巨人的陣容只能用在 `battle_maps` 全是頭目地圖的地點（同時照那些地圖檢查放得下）；沒被任何地點用到的這種陣容也擋。固定精英、加人、等級替換不能是巨人。賽季檔、事件、委託只是「提到」範本（例如首殺來源），沒有掃。

## 8. 影響

- `/125` 的戰鬥紀錄無法重播、戰鬥中存檔讀不回（狀態多了欄位、版號不同；使用者 2026-11-12「存檔都可以刪除」）。世界日誌的規則鍵含 `LOG_FORMAT`，舊世界日誌標成不能重播；`ruleset_hash`、`content_digest` 不變，所以一輪存檔不受影響。
- 目前內容沒有巨型單位，所有實戰結果逐字不變（第 3 節）。

## 9. 平衡疑慮

無新增（本段沒有數值）。規格第 10 節已列的照舊。

## 10. 待 PM 決定

1. 巨人對**所有**位移模式免疫、沒有移動點數（第 7 節第 1 點）；之後要做會移動的多格單位時再開。
2. 倒地免疫的紀錄文字：`effect_fizzled` 原因 `immovable` 目前不顯示，要不要在 `narrative/events.py::_FIZZLE_TEXT` 加一句（例如「巨大的身軀不會倒下」）——建議併 GB-1c 的敘事。
3. 佔格上的地形與高度變化整個跳過（第 7 節第 4 點）：例如地形下陷技能打到佔格時什麼都不發生。
4. **API 視圖**：`UnitView` 沒有 `footprint`，前端仍把巨人畫成一格；留給 GB-4a（本段沒動 `src/trpg/api/` 與 `client/`）。
5. 規格表外動到的引擎檔：`basics.py`、`heights.py`、`effects/surface_entry.py`、`lifecycle.py`（第 5 節），請確認不和別段衝突。
6. 本段是過渡狀態：距離仍量到中心格，所以**近戰打不到 3×3 的巨人**（要和中心格相鄰），一般地圖不會出現巨人所以不影響實戰；GB-1b 之前不要把巨人放進內容。
