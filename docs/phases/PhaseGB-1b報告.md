# Phase GB-1b 報告｜巨型頭目：距離、範圍、出招起點

> 實作者（Opus 5.5），2026-11-14，起點 main `d848bd309`（含 GB-1a 合併與裁定）。規格：`docs/phases/PhaseGB計畫.md` 第 0 節（R1、R2；T5、T7、T9）、第 4 節 GB-1b 列、5.2、5.4～5.6、第 11、12 節與末節「開發 PM 裁定」（R1～R7 照建議；#164：R1 打中的那一格就算落在部位格，防禦也照本體）。設計：`docs/design/05-戰鬥.md` 5.12.4 第 2、4 點。部位綁格與新機制（GB-1c）、`api/`、`client/`、`content/` 都沒動。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 引擎：距離、範圍、出招起點 | `rules/footprint.py` 加 `strike_tiles`、`touches`、`chebyshev_to`、`face_tile`；射程與視線（`targeting._reach_problem`、`combat.reach_problem`）、掩護（`combat.strike_xy`、`half_cover(at=)`）、範圍去重與打中的那一格（`SkillArea.hit_tiles`、`Cast.hit_tile`、`roll_attack(at=)`、`AttackRoll.hit_tile`、事件 `attack_rolled.hit_tile`）、連鎖、以佔格為中心的形狀（`shapes.around_tiles`、`caster_center_candidates`）、錐形與直線起點、拉人方向（T7）、衝鋒與瞬步的落點；其餘引擎的 `manhattan`／行內距離換成單位版；`LOG_FORMAT` `/126` → `/127` | `f2d48bbe2` |
| AI 的距離 | `ai/` 全部單位距離換成單位版；走路步數從全部佔格出發；藉機攻擊風險、恐懼、掩護估值以佔格算；**沒有新評分** | `0945bf1e0` |
| 測試 | 新檔 `tests/engine/test_giant_gb1b.py`（28 項）；版號字面值 11 處 | 同上兩個 |
| 文件 | `docs/phases/戰鬥紀錄格式變更.md` 加 `/127`；本報告；`docs/dev/上手-引擎戰鬥結算.md`（第一節 `footprint.py`、第二節「巨型單位」第 7 點改寫、第四節第 48 點更新、新增第 50 點、第五節測試列） | 第 3 個 commit |

## 2. 逐條驗收

| 驗收（5.6） | 結果 | 證據 |
|---|---|---|
| 1. 分 commit、報告、上手筆記、格式變更文件 | 過 | 上表 |
| 2. `ruff check`／`ruff format --check`／`mypy`／`lint-imports` | 各自結束碼 0 | `ruff check .` 0；`ruff format --check .` 0；`Success: no issues found in 1606 source files`；`Contracts: 14 kept, 0 broken.` |
| 3. 相關測試（不帶 `-m`、`-n 8`） | **5011 passed**，0 失敗 | 改動牽涉 AI 與大部分引擎模組，所以一次跑了整個 `tests/engine`（含 5.6 第 3 點列的全部檔、`test_giant_gb1a.py`、`test_footprint_gb1a.py`、版號三檔）＋`tests/test_architecture.py`＋`tests/world/test_enemy_ai_moves_149.py`、`test_shard_lord_first_phase.py`＋`tests/content/` 的 `test_loader`、`test_battle_content`、`test_giant_content_gb1a`、`test_map_archetypes`、`test_boss_parts_content`、`test_delayed_anchor_content`＋版號字面值的 6 個 CLI 測試檔 |
| 4. 一場紀錄＋重播 | 三場都「重播驗證通過」，`battle` 結束碼 0 | `molten_heart_pit` 2：113 動作 617 事件；`oil_depot` 13：102 動作 454 事件；`swamp` 21：54 動作 240 事件（與 GB-1a 報告相同） |
| 5. 不變比對 `different=0` 與三個雜湊 | 過 | 第 3 節 |
| 6. CLI 快照（slow）與 `tests/narrative/` | 過：24 passed、475 passed，結束碼都 0 | 第 4 節 |
| 7. 新增 `# noqa` | 沒有 | 第 6 節 |

5.5 行為一致測試對到的列（本段範圍內；`tests/engine/test_giant_gb1b.py`）：

| 5.5 列 | 測試 |
|---|---|
| 2 相鄰與距離（D4） | `test_d4_the_twelve_side_tiles_are_adjacent_and_the_corners_are_not`（12 格都能普攻、4 個斜角不行）、`test_d4_range_is_measured_to_the_nearest_tile`（射程 5 的單體從 (5, 9) 打中心 (5, 3)＝距離 5；射程 4 被拒「距離 5，射程 4」；影響格是打中的那一格 (5, 4)）、`test_d4_leaving_any_side_triggers_the_opportunity_attack`（從南排外側走開被巨人藉機攻擊；一格時那裡離中心 2 格不會觸發；走進相鄰不觸發） |
| 3 範圍（R1、T5、D6） | `test_r1_an_area_covering_four_tiles_hits_once_at_the_nearest_tile`（方陣蓋 4 格：一筆 `attack_rolled`、一筆 `damage_dealt`、HP 只扣一次、`hit_tile` (7, 7)、沒有 `part_damaged`）、`test_r1_ties_go_to_the_smaller_y_then_x`、`test_r1_cover_is_judged_at_the_hit_tile`（木箱擋在打中的那一格前面＝有掩護）、`test_t5_a_chain_jumps_through_the_giant_only_once`（從 (6, 9) 跳到南排 (6, 7)、再從東欄跳出，巨人一次）、`test_area_units_are_unique` |
| 4 自身為中心（R2） | `test_r2_self_centred_shapes_measure_from_the_whole_body`（環形 2、範圍光環 3、方陣、十字臂長 2、錐形 3、直線 3 逐格列表；佔格不在範圍內）、`test_r2_counts_from_the_plan`（24／24／16／72 格）、`test_r2_one_tile_casters_keep_the_old_shapes`、`test_r2_the_giant_lists_its_own_body_once_as_a_centre` |
| 5 出招起點（T9）、拉人（T7） | `test_t9_the_giant_strikes_from_the_tile_facing_the_target`（南邊從南排、東邊從東欄；射程 3 的單體打 (6, 10) 從南排算＝3）、`test_t7_the_giant_pulls_toward_its_nearest_tile`（(9, 9) 斜角取 x 軸拉到 (8, 9)）、`test_t7_already_adjacent_units_are_not_pulled` |
| 5.2 第 6、7 點 | `test_ai_walks_next_to_any_tile_and_attacks_the_giant`（效用 AI 從 (6, 11) 走到南排外側後出手）、`test_preview_of_an_attack_on_the_giant_has_no_side_effects` |
| 14 確定性 | `test_same_seed_same_battle_and_the_log_replays`（同種子兩次相同、`BattleLog` JSON 往返重播一致、巨人有被打到）、`test_a_pause_while_the_giant_attacks_resumes_like_a_round_trip`（巨人近戰打帶 `prompt` 格擋的英雄：直接 `resume` 與狀態 JSON 往返後 `resume` 結果相同；GB-1a 留下的那一列）、`clone()` 沿用 GB-1a 的測試（本段沒有新的狀態欄位） |
| T2 | `test_one_tile_helpers_match_the_old_ones`、`test_giant_strike_tiles_are_a_nearest_pair`、`test_one_tile_self_shapes_and_centres_are_unchanged`（hypothesis：一格時 `strike_tiles`、`chebyshev_to`、`face_tile`、`touches`、`around_tiles`、`caster_center_candidates` 都等於原本的算法） |

## 3. 不變比對（5.4）

腳本在 scratchpad（未 commit），比照 GB-1a：改前用 `git archive d848bd309 src content` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；每場比對完整事件 JSON、步驟、輪數、勝方、最終 `rng_state`、最終狀態 JSON（拿掉 `final_state.ruleset`）。**沒有剝掉任何其他鍵**：新欄位 `attack_rolled.hit_tile` 是 `None` 不輸出。

- 8 張地圖 × 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12：**`battles=46 events=20499 different=0`**（事件總數與 GB-1a、RG-5b 相同）。
- 三個雜湊改前＝改後：

| | 改前 `d848bd309` | 改後 |
|---|---|---|
| `hash_ruleset` | `ae4b48df32333cb93b62e7ce9a6eec7b277426cf46168c5633e9438abb54b050` | 同左 |
| `ruleset_hash`（一輪存檔） | `6e0f469df0d803ae1c4f21f054367fc503014d428c4fa58570c7b22eb410efbb` | 同左 |
| `content_digest`（世界日誌） | `50be396d464667cb2bb6fce086afda832b2f596f2a1fdd4c1c263a6da41c8883` | 同左 |

## 4. 快照與既有測試的變動

- **CLI 快照預測：24 鍵全部不變**（戰鬥鍵都是一般地圖、沒有巨型單位，一格單位的戰鬥逐字不變；技能卡、技能列表沒改；紀錄版號不進快照雜湊）。實跑結果見下方；**沒有重產任何鍵**。
- 既有測試只改版號字面值：`trpg-battle-log/126` → `/127`（`tests/cli/` 6 檔、`test_gear_g2.py`、`test_gear_g3a.py`），`LOG_FORMAT.endswith("/126")` → `"/127"`（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`，三個都是跑一場再重播，重播仍一致）。沒有換種子、沒有放寬斷言。

交件前結果：`tests/cli/test_output_snapshots.py -m slow -n 8` **24 passed**（結束碼 0，預測 0 鍵變動＝實際 0 鍵）；`tests/narrative -n 8` **475 passed**（結束碼 0）。

## 5. 改了哪些呼叫點（檔案 × 處數）

「處」＝拿掉的 `manhattan(`／行內曼哈頓距離（含因格式重排而算到的同一行）。一格的單位時新函式逐值等於原本的算法（第 2 節 T2 列）。

| 檔案 | 處 | 說明 |
|---|---|---|
| `rules/footprint.py` | 新函式 4 | `strike_tiles`、`touches`、`chebyshev_to`、`face_tile` |
| `skills/targeting.py` | 7 | 射程／高度／視線改由出招起點與打中的那一格算（`_reach_problem(..., target)`）；致盲上限；單體影響格＝打中的那一格；`_tiles_to_units` 去重；`_chain_tiles`；`_hit_tiles`；`_tile_area` 的中心格以最近佔格量、巨人選自己＝`around_tiles`；`_direction_area` 從 `face_tile`；`_self_area` 走 `around_tiles`；候選與投擲物件 |
| `skills/shapes.py` | 2 | `chain_units`（`unit_dist`、`strike_tiles` 的視線）；新 `around_tiles`、`_giant_cross`、`caster_center_candidates` |
| `skills/cast.py` | 2 | `hit_tile` → `roll_attack(at=)`、事件 `hit_tile`；轉身記離目標最近的佔格；衝鋒後相鄰；火器距離 |
| `skills/mobility.py` | 2 | `dash_route` 對巨人以 12 格外圍為終點；`shadowstep_spot_problem`；`_adjacent` 對巨人回 12 格 |
| `skills/primitives/displacement.py` | 新分支 | T7 |
| `skills/primitives/statuses.py`、`summoning.py`、`variance.py` | 1、1、2 | 濺射、獻祭爆炸、多敵人變化 |
| `rules/combat.py` | 7 | `strike_xy`；掩護（物件、盾兵、盾陣、塔盾）以兩格算；靈覺、濃霧、武器距離命中、背刺的攻擊者格、`reach_problem(..., target)`、致盲、隱蔽距離；`AttackRoll.hit_tile` |
| `rules/movement.py` | 2 | 恐懼的「靠近」量到最近佔格（`fear_origins` 改回傳單位） |
| `reactions.py` | 11 | 同門相護範圍、反擊相鄰、守護詞條範圍、攔截相鄰、被瞄準／受擊的相鄰友方、走進相鄰、藉機攻擊離開範圍、加傷距離；事件 `hit_tile` |
| `basics.py`、`battle.py` | 3、3 | 相鄰友方、守護；技巧動作相鄰、互動物件相鄰 |
| `effects/handlers.py`、`formation.py`、`forms.py`、`parts.py`、`pierce.py`、`preview.py` | 1、2、2、1、1、2 | 護盾反傷的近戰判定、陣法、形態爆發與相鄰治療、部位 `high_or_far` 的距離、穿透排序、預覽命中 |
| `race/skills.py`、`rule_changes.py`、`skill_infusion.py`、`skill_triggers.py`、`strikes.py`、`summons/core.py`、`weapon_traits.py` | 4、1、1、4、1、8、4 | 種族技、規則改寫的相鄰、灌注、被動觸發距離與最虛弱友方、連擊、召喚物（光環、圖騰、藤蔓、落點）、祝禱、雷電連鎖、弩穿透（從出招起點經過打中的那一格延伸、同一單位只算一次） |
| `traps.py`、`oath_tracking.py` | 2、1 | 行內 `abs()`：靈覺看陷阱、誓約「遠離敵人」（`oath_tracking` 在 `state.py` 的匯入鏈上，照 `footprint` 的算法行內寫，上手第 50 點） |
| `bombs.py`、`objectives.py`、`zone_triggers.py`、`race/skills.py` | `touches` 5 | 爆炸範圍、目標區域、區域進入／回合開始、錐形內的單位：巨人整個只算一次 |
| `ai/`（20 檔） | 64 | 全部單位距離；`utility/position._steps_to` 從全部佔格出發（走到任一佔格旁）；`moves.reactive_enemies` 回傳單位、`is_risky_move` 以佔格判斷離開相鄰；掩護與盾兵估值從離那一格最近的佔格看 |
| `runner.py` | — | `LOG_FORMAT` `/127` |

**刻意不改**：
- 格子對格子的 `manhattan`（`rules/geometry.py` 的視野、`rules/landing.py` 的最近空格、`skills/shapes.py` 的單格形狀、`battle._zone_of` 起始區、`skills/mobility.py` 的衝撞與跳躍、`race/skills.py` 的跳躍、`summoning._site_near`、`ai/utility/position.py` 的指令與護衛點）：起點是格子或施放者自己的位移，巨人不會移動。
- 行內 `abs()`：`summons/core._blast_tiles`（召喚物爆心，一格）、`basics.vault_plan`（自己攀跳）、`battle.py` 路徑連續性、`combat.guard_blocks`（格子幾何）。
- `api/skill_reasons.py:29`、`sim/skill_ratio.py:491`：`api/` 是 GB-4a、`sim/` 不在範圍。
- 其餘 `has_line_of_sight(a.xy, b.xy)`（倒下友方的反應、瞄準預告、AI 部分項）：佔著端點的巨人本來就不擋（GB-1a），量到中心格的差別只在極端的地形邊緣；`lock_on` 的射程與擋箭沿用 `targeting` 的選取，已是單位版。
- `parts.py` 的 `back_xy`（`need_behind`）：GB-1c。

## 6. 新增 `# noqa`

沒有。

## 7. 規格沒寫到、採保守做法的地方

1. **單體打巨人的「打中的那一格」**＝離出招起點最近的佔格（D4「距離量到最近的那一格」）；`attack_rolled.hit_tile` 單體、範圍都輸出（一格的目標不輸出），給 GB-4a／4b 的演出落點。
2. **掩護與高度用打中的那一格**（R1）：範圍技以 `hit_tile` 判掩護；單體以最近的一對格子。高度：佔格高度一致（GB-1a 內容檢查），所以「以那一格算」和以中心算相同。
3. **以自己為中心的判定**：巨人選自己的任一佔格當中心＝以整個佔格為中心（延遲段「以施放者當下的位置為中心」就是這個）；候選只列中心格一次。巨人以自己為中心時 `SkillArea.origin` 仍是中心格；推擊從最近佔格往外推、拉人往最近佔格拉（T7）。`ground_tile` 選自己不擴大（只有那一格）。
4. **錐形、直線的「朝向那一面」**取的是這次施放選的方向（`direction`），不是頭目固定的正面——頭目不轉身，若只取正面，背面與側面的錐形就放不出去。
5. **`include_caster`**：範圍型技能「施放者自己也算在內」對巨人照舊把中心格加進影響格（R2「佔格不在範圍內」只指形狀本身）。
6. **藉機攻擊的範圍與「走進相鄰」**都量到最近佔格（`dist_to(reactor, from_xy)`）；巨人自己不移動，所以只有「別人在它旁邊移動」會觸發。
7. **恐懼**：被巨人嚇到時「不能靠近」量到最近佔格。
8. **弩的穿透**：直線從出招起點經過打中的那一格延伸；後方的巨人只算一次、不會把原目標再算進去。
9. **衝鋒到巨人**：終點是 12 格外圍中成本最小、同成本 (y, x) 小的；瞬步落點照「北排（西→東）、東欄（北→南）、南排（東→西）、西欄（南→北）」的固定順序。

## 8. 影響

- `/126` 的戰鬥紀錄無法重播、戰鬥中存檔讀不回（使用者 2026-11-12「存檔都可以刪除」）；世界日誌的規則鍵含 `LOG_FORMAT`，舊世界日誌標成不能重播。`ruleset_hash`、`content_digest` 不變，一輪存檔不受影響。
- 目前內容沒有巨型單位，所有實戰結果逐字不變（第 3 節）。
- 介面變動（只在引擎內）：`moves.reactive_enemies`、`movement.fear_origins` 回傳單位而不是格子；`combat.half_cover`、`roll_attack` 多選填 `at`；`combat.reach_problem`、`targeting._reach_problem` 多選填 `target`。

## 9. 平衡疑慮

無新增數值。規格第 10 節第 1、2 條在本段生效（12 格可近戰；R2 讓巨人的自身範圍變大：環形 2 從 16 格變 24 格、十字臂長 2 從 9 格變 24 格），等 GB-2 把灰燼之心變成巨人時才會進實戰。另一條觀察：範圍光環（`allies_in_radius`）以佔格量時半徑 3 是 48 格、4 是 72 格（1 格時 25／41）。

## 10. 待 PM 決定

1. 錐形、直線用「這次選的方向」那一面的中間格起算，而不是固定正面（第 7 節第 4 點）；要限制巨人只朝正面放錐形的話要另定規則。
2. `include_caster` 的範圍技對巨人照舊把自己算進去（第 7 節第 5 點）；目前內容的巨人（灰燼之心）沒有這種招。
3. `api/skill_reasons.py`、`sim/skill_ratio.py` 的行內距離沒有換（不在本段範圍）；GB-4a 處理 API 時一起換。
4. `attack_rolled.hit_tile` 是新事件欄位（`/127`），前端事件窄化要在 GB-4a 加（`client/src/api/types.ts`）。
5. 恐懼、藉機攻擊、陣法、光環等「N 格內」全部量到最近佔格，巨人因此影響的範圍變大（平衡第 10 節第 1 條的延伸），若有某一項要量到中心請指出。
