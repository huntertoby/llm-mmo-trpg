# Phase GB-1c 報告｜巨型頭目：部位綁格與新機制

> 實作者（Opus 5.5），2026-11-14，起點 main `5f381e9fd`（含 GB-1b 合併與裁定）。規格：`docs/phases/PhaseGB計畫.md` 第 0 節（R3～R6；T11、T12、T14～T16）、第 4 節 GB-1c 列、5.3、5.4～5.6、第 11、12 節與末節「開發 PM 裁定」（R1～R7 照建議、R6 選 A；#164：R1 打中的那一格就算落在部位格，防禦也照本體）。設計：`docs/design/05-戰鬥.md` 5.12.2 第 8 點、5.12.4 第 3 點；`docs/design/19-灰燼荒原與賽季主線.md` 19.2.3「巨型頭目段 GB 補定的細節」。`content/` 資料檔、`api/`、`client/`、AI 評分都沒動。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 內容 schema（T11、T14、T15、T16） | `BossPart.tiles`／`melee_from`／`counts_as_behind`、`reach: ranged`、`check_part_tiles`（範本驗證時檢查）；`SealSkillBreak.rounds`；`DelayedAnchor` 加 `farthest_enemy`、`FARTHEST_FIRST_SHAPES = ("self",)` 與延遲段檢查；`BossPhase.grow_surface`（`PhaseGrowSurface`）。全部有預設、預設不輸出 | `1c67e19e2` |
| 引擎（R3～R6、T12、T14～T16） | 部位的可打條件（`parts._tile_reason`、`ranged`）；打綁格部位時打中的那一格（`part_breaks.part_hit_tile`）與從背後（`part_hit_tile`／`part_behind` → `roll_attack(at=, from_behind=)`、`Cast.holds` 的 `Subject.behind`、預覽）；限時封招（`UnitState.sealed_until`、`skill_problem`）；`farthest_enemy` 落點（`targeting.farthest_enemy`、`_anchor_problem`、`delayed._anchor`、事件 `anchor_target_id`）；生長表面（`environment._grow_surfaces`）；敘事（新原因的中文、限時封招、落點、倒地免疫）；`LOG_FORMAT` `/127` → `/128` | `844eeed80` |
| 測試 | 新檔 `tests/engine/test_giant_parts_gb1c.py`（30 項）；`test_state_clone.py` 的 `_COPIED` 加 `sealed_until`；版號字面值 11 處 | `844eeed80`、`bb33aef94` |
| 文件 | `docs/phases/戰鬥紀錄格式變更.md` 加 `/128`；本報告；`docs/dev/上手-引擎戰鬥結算.md`（版號、第一節 `boss_phases`／`delayed`／`parts`／`part_breaks` 列、第二節「巨型單位」第 8 點、第四節第 51、52 點、第五節測試列） | 第 4 個 commit |

## 2. 逐條驗收

| 驗收（5.6） | 結果 | 證據 |
|---|---|---|
| 1. 分 commit、報告、上手筆記、格式變更文件 | 過 | 上表 |
| 2. `ruff check`／`ruff format --check`／`mypy`／`lint-imports` | 各自結束碼 0 | `All checks passed!`；`2711 files already formatted`；`Success: no issues found in 1607 source files`；`Contracts: 14 kept, 0 broken.` |
| 3. 相關測試（不帶 `-m`、`-n 8`） | **4897 passed**＋**7614 passed／14 skipped**，0 失敗 | 改動牽涉命中判定、條件、技能選取與環境回合，所以跑了整個 `tests/engine`（含 5.6 第 3 點列的全部檔、新檔與 GB-1a／1b 兩檔、版號三檔）＋`tests/world/test_enemy_ai_moves_149.py`、`test_shard_lord_first_phase.py`＋`tests/api/test_delayed_api.py`＋版號字面值的 6 個 CLI 測試檔（4897 passed）；另跑 `tests/content`＋`tests/api/tuning`＋`tests/skillgen`＋`tests/test_architecture.py`（7614 passed、14 skipped；第一次有 1 個失敗：`test_pronoun_scan.py` 抓到新敘事句用了「他」，改寫成「落在最遠的 X 現在站的地方」後重跑通過） |
| 4. 一場紀錄＋重播 | 三場都「重播驗證通過」，`battle`／`replay` 結束碼都 0 | `molten_heart_pit` 2：113 動作 617 事件；`oil_depot` 13：102 動作 454 事件；`swamp` 21：54 動作 240 事件（與 GB-1a、1b 報告相同） |
| 5. 不變比對 `different=0` 與三個雜湊 | 過 | 第 3 節 |
| 6. CLI 快照（slow）與 `tests/narrative/` | 過：`tests/cli -m slow` 44 passed（其中 `test_output_snapshots.py` 24 鍵）、`tests/narrative` 475 passed，結束碼都 0 | 第 4 節 |
| 7. 新增 `# noqa` | 沒有 | 第 6 節 |

5.5 行為一致測試對到的列（`tests/engine/test_giant_parts_gb1c.py`）：

| 5.5 列 | 測試 |
|---|---|
| 10 部位（T11、D12、R3、T12） | `test_t11_giant_parts_need_tiles_inside_the_body_without_overlap`（沒綁格、出界、重疊、一格頭目帶綁格欄位、tiles 重複都擋）、`test_t11_new_fields_are_not_serialised_when_unused`、`test_d12_r3_part_reach_table`（5 列：劍貼西側殼縫、劍貼南排、劍站噴口旁地板、矛站噴口旁地板、弓從南邊 → 三個部位的原因代碼）、`test_d18_the_core_shows_from_phase_two_and_melee_reaches_it_from_any_face`（5 個位置＋遠程）、`test_d12_ranged_needs_the_part_tile_in_range`（射程 3 打得到本體、部位格超出；`IllegalActionError` 文字）、`test_d12_ranged_needs_sight_to_the_part_tile`、`test_t12_broken_parts_and_the_front_shell_are_the_body`、`test_reason_texts` |
| 10 從背後（R4）、打中的那一格、#164 | `test_r4_melee_on_the_seam_counts_as_behind`（殼縫有背刺、本體沒有；`hit_tile` (5, 6)；只扣殼縫）、`test_r4_ranged_on_the_seam_is_not_a_backstab`（遠程沒有背刺；同距離取 (y, x) 小；噴口打中 (6, 5)）、`test_r4_the_from_behind_condition_holds_on_the_seam`（帶「目標背後」條件的第二段傷害只在打殼縫時結算）、`test_164_an_area_hit_tile_on_a_part_still_uses_the_body_defence`（方陣打中的那一格是噴口格時防禦值＝打前殼時、不扣部位） |
| 11 限時封招（T14） | `test_t14_a_timed_seal_lasts_two_rounds_and_survives_phase_changes`（第 5 輪破：5、6 輪擋，7、8 輪可以；換階段不清；`skill_sealed.rounds`＝2、紀錄「被封住 2 回合」）、`test_t14_breaking_the_core_interrupts_the_charge`、`test_t14_a_permanent_seal_wins_over_a_timed_one` |
| 12 `farthest_enemy`（R5、T15） | `test_r5_the_farthest_enemy_is_chosen_ties_by_y_then_x`（同距離 5 取 y 小；`followup_charged` 的 `pos`、`anchor_target_id`、紀錄「最遠的」）、`test_r5_unseen_concealed_enemies_do_not_count_and_range_does_not_matter`（遠處隱蔽不算、2 格內照得到、沒人時 `skill_problem` 擋且 `legal_actions` 不列）、`test_t15_one_action_without_a_tile_and_target_pos_is_refused`、`test_t15_farthest_needs_a_first_segment_without_a_tile`、`test_r5_the_landing_stays_when_the_enemy_walks_away`（預告不動、釋放以原格為中心、走開的人不受傷） |
| 13 火地生長（R6 A、T16） | `test_r6_fire_grows_one_row_south_each_round_and_stops_at_obstacles`（5 輪逐輪列出：矮牆停、有人停、最多 4 排、不會到期）、`test_r6_water_and_lava_stop_the_growth_and_telegraph_shows_it`（水停、環境預告看得到）、`test_r6_no_growth_outside_the_phase` |
| 14 確定性 | `test_same_seed_same_battle_and_the_log_replays`（合成巨人帶部位、生長表面與 `farthest_enemy` 招的效用 AI 對戰：同種子兩次相同、`BattleLog` JSON 往返重播一致、有放到那招）、`test_clone_and_json_keep_the_timed_seal`（`clone`、JSON 往返、沒用時不輸出）；`test_state_clone.py` 的 `_COPIED` |
| GB-1a 待決 2 | `test_prone_immunity_has_a_log_line`（「巨大的身軀紋風不動：擊不倒」） |

## 3. 不變比對（5.4）

腳本在 scratchpad（未 commit），比照 GB-1a／1b：改前用 `git archive 5f381e9fd src content` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；每場比對完整事件 JSON、步驟、輪數、勝方、最終 `rng_state`、最終狀態 JSON（拿掉 `final_state.ruleset`、`setup.ruleset` 與版號）。**沒有剝掉任何其他鍵**：新欄位（`sealed_until`、`skill_sealed.rounds`、`followup_charged.anchor_target_id`）沒用到時不輸出，改前改後的 JSON 直接相等。

- 8 張地圖 × 種子 1、2 ＋ 3 張頭目圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`，含霧鎖真人的部位）× 種子 3～12：**`battles=46 events=20499 different=0`**（事件總數與 GB-1a、1b 相同）。
- 三個雜湊改前＝改後：

| | 改前 `5f381e9fd` | 改後 |
|---|---|---|
| `hash_ruleset` | `ae4b48df32333cb93b62e7ce9a6eec7b277426cf46168c5633e9438abb54b050` | 同左 |
| `ruleset_hash`（一輪存檔） | `6e0f469df0d803ae1c4f21f054367fc503014d428c4fa58570c7b22eb410efbb` | 同左 |
| `content_digest`（世界日誌） | `50be396d464667cb2bb6fce086afda832b2f596f2a1fdd4c1c263a6da41c8883` | 同左 |

## 4. 快照與既有測試的變動

- **CLI 快照預測：24 鍵全部不變**（戰鬥鍵都是一般地圖、沒有巨型單位也沒有新欄位；技能卡、技能列表沒改——新欄位都是預設不輸出、內容沒用到；紀錄版號不進快照雜湊）。**沒有重產任何鍵**。
- 既有測試只改版號字面值：`trpg-battle-log/127` → `/128`（`tests/cli/` 6 檔、`test_gear_g2.py`、`test_gear_g3a.py`），`LOG_FORMAT.endswith("/127")` → `"/128"`（`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`，三個都是跑一場再重播、重播仍一致）；`test_state_clone.py` 的 `_COPIED` 加 `sealed_until`（字典，`clone()` 要複製）。沒有換種子、沒有放寬斷言。

交件前結果：`tests/cli -m slow` **44 passed**（`test_output_snapshots.py` 24 鍵全過，預測 0 鍵變動＝實際 0 鍵）；`tests/narrative -n 4` **475 passed**（結束碼 0）。

## 5. 改了哪些呼叫點（檔案 × 處數）

| 檔案 | 處 | 說明 |
|---|---|---|
| `content/parts.py` | 5 | `PartReach` 加 `ranged`、`MeleeFrom`、`BossPart.tiles`／`melee_from`／`counts_as_behind`（tiles 不重複）、`SealSkillBreak.rounds`、`check_part_tiles` |
| `content/battle.py` | 3 | `PhaseGrowSurface`、`BossPhase.grow_surface`（含 `changes_anything`）、`template_part_problems` 呼叫 `check_part_tiles` |
| `content/skills/constants.py`、`followup.py`、`specs.py`、`__init__.py` | 2、1、1、1 | `DelayedAnchor`／`DELAYED_ANCHOR_VALUES` 加 `farthest_enemy`、`FARTHEST_FIRST_SHAPES`；延遲段檢查分 `cast_tile`／`farthest_enemy`；說明；匯出 |
| `engine/state.py` | 2 | `UnitState.sealed_until`（三處同步：欄位 `exclude_if` 空、`clone()` 複製字典、序列化） |
| `engine/parts.py` | 4 | `_Swing`（近戰、射程、拋射）、`_reach_reason`（`behind` 改用 `is_behind`，一格時逐值相同；`ranged`）、`_tile_reason`、原因代碼與中文 4 個 |
| `engine/part_breaks.py` | 4 | `part_tiles`、`part_hit_tile`、`part_behind`、`_seal` 的限時封招 |
| `engine/rules/combat.py` | 2 | `positional_bonus(..., from_behind=)`、`roll_attack(..., from_behind=)` |
| `engine/reactions.py` | 1 | `_attack_once` 的 `roll_attack` 帶 `at`、`from_behind` |
| `engine/skills/cast.py` | 3 | `roll_one` 帶 `from_behind`；`hit_tile` 先看部位格；`holds` 設 `Subject.behind` |
| `engine/skills/conditions.py` | 3 | `Subject.behind`、`_unit_condition_met(..., behind=)` |
| `engine/skills/targeting.py` | 3 | `_sealed_problem` 看 `sealed_until`；`farthest_enemy`；`_anchor_problem` |
| `engine/delayed.py` | 2 | `anchor_of(state, caster, skill, action)`／`_anchor`；`charge` 發 `anchor_target_id` |
| `engine/environment.py` | 3 | `_grow_surfaces`、`_grow_front`、`_can_grow`（環境回合最後一步） |
| `engine/events/parts.py`、`events/skills.py` | 1、1 | `skill_sealed.rounds`、`followup_charged.anchor_target_id`（都 `exclude_if` None） |
| `engine/preview.py` | 2 | 普攻與技能預覽的背刺吃 `from_behind` |
| `engine/ai/composite.py` | 1 | `anchor_of` 的新簽名（只改呼叫，不改評分） |
| `engine/runner.py` | 1 | `LOG_FORMAT` `/128` |
| `narrative/events.py` | 3 | `immovable` 的倒地免疫、`followup_charged` 的最遠敵人、`skill_sealed` 的回合數 |
| `narrative/parts.py` | 1 | 「破掉會：封住「X」2 回合」 |

**規格表外動到的檔**：`engine/skills/targeting.py`（T14「`skill_problem` 一併擋」與 R5「找不到敵人就不能施放」都在 `skill_problem`）、`engine/skills/cast.py`／`conditions.py`／`reactions.py`／`rules/combat.py`／`preview.py`（R4 的「從背後」與部位格要接到命中判定）、`engine/state.py`（T14 的新欄位）、`engine/events/`（新事件欄位）、`engine/ai/composite.py`（只改一行呼叫）、`content/skills/specs.py`／`__init__.py`（說明與匯出）。

**刻意不改**：
- `boss_phases.py`：生長表面照 T16「在 `_end_round` 結算」放在環境回合（`_end_round` → `run_environment`），環境預告（`telegraph`）因此也看得到；階段進入時不做事（第 1 排由階段的 `tiles` 放，GB-2 照 6.1 寫）。
- 技能層級的 `from_behind` 條件（`skill_condition_met`，施放前判斷）不看部位：目前內容的「目標背後」都是效果層級（瞬步背刺、交叉斬、快刺）。
- `quiet_strikes.py`：沒有「背後」判斷（巨人本來就不轉身）。
- AI：`ai/parts.py` 的 `silent_behind_extra`、`circle_back_extra` 等背後估值不看 `counts_as_behind`（評分在 GB-3）。
- `engine/view.py`、`api/`：`PartView.tiles`、`UnitView.footprint` 是 GB-4a；API 的部位原因已經吃 `PART_REASON_ZH`，新代碼自動有中文。

## 6. 新增 `# noqa`

沒有。

## 7. 規格沒寫到、採保守做法的地方

1. **近戰「貼著那一格」一律要上下左右相鄰**（D12 字面）：拿矛（近戰、射程 2）隔一格也不算；`melee_from: any_face` 是貼著任一佔格。
2. **遠程射程量到部位格**：普攻用 `attack_reach(..., 那一格)`（含弓的高處射程），技能用 `shape_reach`；視線用一般規則（拋射照武器），巨人自己的身體不擋（GB-1a）。只要部位有一格「射程內而且看得到」就能選；原因代碼先報射程（沒有一格在射程內）、再報視線。
3. **打綁格部位時打中的那一格**＝部位格裡離攻擊者（最近佔格）最近的那格，同距離 (y, x) 小；不另驗那一格的視線（宣告時 `part_targets` 已驗過「至少一格打得到」）。掩護、事件 `attack_rolled.hit_tile` 以它算。
4. **R4 的「從背後」只在近戰**（`profile.melee`）：背刺加成（命中、暴擊範圍、背刺骰）、效果層級條件「目標背後」；連擊武器的後幾下照 `backstab_first_only`。
5. **限時封招**：第 N 輪破、封 r 輪 → `sealed_until = N + r`，`round < N + r` 時擋（N、N＋1 輪不能放，N＋2 輪起可以）；已被永久封住的招不再記限時；同一招被限時封兩次取較晚的解封輪。解封不發事件、`sealed_until` 的舊項目不清（只是不再擋）。
6. **`farthest_enemy` 的敵人**＝不同陣營的存活單位（含召喚物）；距離用 `unit_dist`（離巨人最近佔格）；隱蔽照 `concealment_problem`（2 格內照得到、被標記照得到、狐族靈覺）。第一段的形狀只收 `self`（不需選格）；找不到敵人時 `skill_problem` 擋（`legal_actions` 不列）。
7. **生長表面的「停」**：每一欄只從北邊相鄰那格**已經有這種表面**的地方往南長一格；所以那一欄遇到矮牆、水、岩漿、牆、單位就停在那裡——擋住的是單位時，單位走開後下一輪會繼續長（北邊那格還是火）。北邊那格的火被別的東西弄掉（例如水）時，那一欄從那裡重新長。已經有同種表面的格子（例如熔岩濺落留下的火地）直接當作長到了、再往南看，所以那一輪那一欄可能多長一格。用 `ChangeTileEffect`（同階段的 `tiles`、地圖事件）：表面不會到期、事件是既有的 `surface_changed`。
8. **生長的時機**：環境回合的最後一步（地圖事件之後）；頭目倒下或不在那個階段就不長；進階段那一輪的環境回合就長第 2 排。

## 8. 影響

- `/127` 的戰鬥紀錄無法重播、戰鬥中存檔讀不回（狀態多 `sealed_until`、事件多欄位；使用者 2026-11-12「存檔都可以刪除」）；世界日誌的規則鍵含 `LOG_FORMAT`，舊世界日誌標成不能重播。`ruleset_hash`、`content_digest` 不變，一輪存檔不受影響。
- 目前內容沒有巨型單位、沒有用到新欄位，所有實戰結果逐字不變（第 3 節）。
- 介面變動（引擎內）：`delayed.anchor_of` 多收 `state`、`caster`；`positional_bonus`、`roll_attack` 多選填 `from_behind`；`Subject` 多 `behind`（預設 `False`）。

## 9. 平衡疑慮

無新增數值（`grow_surface.max_rows` 預設 4、`seal_skill.rounds` 都是內容要填的占位，GB-2 才填）。規格第 10 節第 4～6 條在 GB-2 填內容後生效。另一條觀察：殼縫的背刺加成只看「近戰打殼縫」，所以站在殼縫旁的近戰每一下都是背刺（包含背刺骰），比 1 格頭目要繞背容易得多。

## 10. 待 PM 決定

1. 生長表面「停」的解讀（第 7 節第 7 點）：擋住的是**單位**時，單位走開後那一欄會繼續長；要不要改成「被單位擋過一次就永久停」？
2. 生長表面不在進階段時放第 1 排（第 1 排照 6.1 由階段的 `tiles` 放），GB-2 寫內容時 `tiles` 南緣外一排與 `grow_surface` 要一起寫。
3. 近戰拿矛也要「貼著」部位格（第 7 節第 1 點）：矛隔一格打殼縫不行。
4. 技能層級的「目標背後」條件不吃殼縫（第 5 節「刻意不改」）；之後有這種招再補。
5. `farthest_enemy` 把敵方召喚物也算進「最遠的敵人」（第 7 節第 6 點）。
6. AI 的背後估值（`silent_behind_extra`、繞背）不看殼縫；GB-3 做巨型頭目的站位時一起處理。
7. 規格表外動到的引擎檔（第 5 節）請確認不和別段衝突。

## 開發 PM 裁定（2026-11-14）

- 接受。46／0、三個雜湊不變、CLI 快照 0 鍵；規格表外的檔都是接命中判定與 `skill_problem` 所需，和目前在跑的段（PB-1f 只動 client）不衝突（待決 7）。
- 待決 2：GB-2 寫內容時第 1 排火地（階段 `tiles`）與 `grow_surface` 一起寫，記進 GB-2 派工。
- 待決 4：同意，等有技能層級「目標背後」的招再補。待決 6：留給 GB-3。
- 待決 1（火地被單位擋住後是否永久停；現況：單位走開會繼續長）、3（「貼著那一格」照字面上下左右相鄰，拿矛隔一格打不到殼縫）、5（`farthest_enemy` 把敵方召喚物也算）：屬設計細節解讀，照現況先做，轉玩法 PM 確認；要改再併進後面的段。
- 待決 8 平衡觀察轉玩法 PM 記平衡待查。
- 2026-11-14 玩法 PM（4.1.11，commit a2a011ba9）：GB-1c 待決 1、3、5 三條解讀照現況，不改；平衡觀察記平衡待查第 28 條第 10 點。
