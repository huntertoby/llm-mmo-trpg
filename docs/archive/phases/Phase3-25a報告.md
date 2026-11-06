# Phase 3-25a 完成報告｜戰場變奏：變奏引擎、預算、示範技能、AI

分支：`worktree-agent-a026d7890e0680c2e`（從 main 0260192 分出）。`LOG_FORMAT`：`trpg-battle-log/46` → `/47`。
規格：`docs/phases/Phase3計畫.md` 第 33 節（PM 決定表 ＋ 33.1）；設計：`docs/design/06-技能.md` 6.24。只做 33.1；33.2（API 視圖、前端、工坊、組合器、進化模板）沒做。

## 做了什麼

### 1. Schema 與驗證（PM 決定 #1、#2、#7）

- `src/trpg/content/skills.py`：新增 `VariantWhen`（四種條件恰好填一種：`caster_surface`、`caster_high_ground: true`、`caster_adjacent_blocker: true`、`target_surface`）、`VariantEffectSwap`、`VariantSpec`（`id`、`name_zh`、`when`、替換 1～2 項：`shape`、`range_delta`、`element`、`add_effect`、`replace_effect`）。沒有 AP／冷卻／代價／kind／骨架欄位（`extra="forbid"`，寫了就被拒）。
- `SkillDef.variants`（0～2 個）與 `_check_variants`：最多 2 個、ID 不重複、只有主動技能（不是陷阱、不是複合技能、不是常駐類傳說）、`replace_effect` 不能換主傷害（第一個 `damage` 效果）或唯一效果、`element` 需要有傷害效果、`range_delta` 需要數字射程。
- `SkillDef.variant_form(id)`：展開成獨立的技能（沒有 `variants`；ID、名稱、代價、骨架不變），依序套用 換形狀 → 射程 ±（至少 1）→ 換附帶效果 → 加附帶效果 → 換所有頂層 `damage` 效果的元素；用同一套 schema 驗證（像 `followup_skill`），有快取。
- 稀有度上限：`content/rules/core.yaml` 的 `variant_max_by_rarity: {common: 0, rare: 1, epic: 2, legendary: 2}`（`CoreRules`）。跨檔案檢查在 `library.skill_reference_problems`：數量上限、條件引用的表面必須在 `surfaces.yaml`、每個型態本身再跑一次引用檢查（錯誤以 `variants.<id>.` 開頭）。

### 2. 引擎（PM 決定 #3、#4）

- 新模組 `src/trpg/engine/variants.py`（純函式、只讀）：`target_point`（單位目標所在格 → 指定格 → 目標物件所在格；方向型與自身型為 `None`）、`variant_holds`、`chosen_variant`（資料中第一個成立的）、`varied_skill(state, caster, skill, target) -> (SkillDef, variant_id | None)`、`possible_variants`。
  - 相鄰：八方向、地圖內，牆壁（`shapes.is_wall`）或 `blocks_move` 物件；地圖邊不算。
  - 居高：施放者所在格高度 − 目標點高度 ≥ 1；沒有目標點時不成立。
- 結算順序 基礎 → 變奏 → 等級 → 修正：`modifiers.acting_skill(state, unit, skill_id, action=None)` 給了 `action` 時先依目標點選型態，再走原本的 `shaped_skill`（內含 `leveled_skill`）。解譯器 `use_skill` 同樣先 `varied_skill` 再 `shaped_skill`，再用該型態的 `checked_area` 檢查選取，所以「某目標點合法 ⇔ 該點選出的型態接受它」。
- 合法動作：新模組 `src/trpg/engine/skills/forms.py` 的 `skill_selections`／`has_skill_selection`——沒有變奏的技能直接用原本的 `selections`（結果不變）；有變奏時列出各可能型態的選取，只保留「目標點選出的型態就是這個型態」的。`battle.py` 的 `_skill_actions`、`_has_attack_to_aim`、`_has_ap_action` 改用它。
- 預覽：`preview.py` 所有 `acting_skill` 呼叫都帶 `action`（命中、傷害、射程、穿透、複合資訊都以該目標點的型態計算）。

### 3. 事件、紀錄、CLI（PM 決定 #5）

- `SkillUsed.variant: str | None = None`；`_pay_costs` 帶入。
- 戰鬥紀錄：`施放「潮汐之矛」（水中貫穿）（AP 2，…）`（`narrative/events.py`）。
- `LOG_FORMAT` → `trpg-battle-log/47`（說明寫在 `runner.py`）；各測試的 `/46` 斷言改 `/47`。
- `trpg skills show` 列出每個變奏（條件與替換內容的中文說明，`narrative/skills.py` 新增 `variant_condition_text`、`variant_change_text`）。
- CLI 快照：`skills_list`、`skills_show_all` 兩個雜湊更新（新增 4 招示範技能與變奏說明）；7 場戰鬥快照 **不變**。

### 4. 預算（PM 決定 #6）

- `content/skill_budget.yaml`：`variant_surcharge_permille: 100`（`BudgetRules`）。
- `skill_budget`：有變奏時，基礎型態照一般技能計算，`total ×（1000 ＋ 100 × 變奏數）÷ 1000`；`BudgetReport.variant_surcharge_permille` 與 `variants: tuple[VariantBudget, ...]`（每個型態自己的預算，不含加價）。
- 驗證器 `validate_skill`：每個型態照一般技能完整檢查（骨架、互斥、稀有度、預算窗），規則代碼 `variant.<id>.<rule>`。
- `trpg skills budget <id>` 逐型態列出（條件 → 替換、total ÷ 可用、合格與否）；`--all` 總表在技能下方以 `└ <變奏 id>` 逐型態列出。

### 5. 關鍵字（PM 決定 #8）

- `derive_keywords`：有變奏時取所有型態的聯集；`SkillKeywords.variant` 列出只由變奏型態帶來的關鍵字（`variant: true`）。
- `exclusive_only=True`（開局技能池、候選產生器）**只看基礎型態**（見「待 PM 決定」1）。
- 技能卡的「（特定地形）」顯示屬於 API／前端，留給 3-25b（`KeywordRef` 在 OpenAPI 裡，本段不動 API）。

### 6. 示範技能 4 招（`content/skills/`）

| 技能 | 稀有度 | 類型 | 變奏（條件 → 替換） | 預算比例（基礎含加價／各型態） |
|---|---|---|---|---|
| 潮汐之矛 `skill_tidal_spear` | 史詩 | 法術（法器，combo） | 水中貫穿：站在水上 → 直線 3 格 ＋ 雷；居高投矛：居高 → 射程 +2 ＋ 擊倒 | 82.1%／95.8%、87.4% |
| 靠牆盾擊 `skill_wall_brace_bash` | 稀有 | 近戰（strike） | 借牆猛撞：相鄰牆壁／擋路物件 → 加推擊 1 格（撞擊 1d6） | 73.7%／86.1% |
| 燧石飛刃 `skill_oil_spark_throw` | 稀有 | 遠程（strike） | 油上火星：目標點在油上 → 火元素 | 83.5%／75.9% |
| 霜崖斬 `skill_frost_ledge_cleave` | 史詩 | 近戰（strike） | 寒霜刃：站在冰／水上 → 冰元素；崖頂下劈：居高 → 加擊倒 | 88.0%／73.3%、92.4% |

四種條件各至少一次；近戰、遠程、法術都有。`icon_of` 皆非 partial（`client/src/render/fixtures/skill_icons.json` 依規定重產）。
- 為了 `test_every_handwritten_skill_is_equipped_by_a_build_or_unit`，新增 3 個示範單位（不在任何地圖遭遇中、不影響既有戰鬥）：`content/units/variant_vanguard.yaml`（靠牆盾擊、霜崖斬）、`variant_tidecaller.yaml`（潮汐之矛）、`variant_slinger.yaml`（燧石飛刃）；`tests/content/test_con_hp.py` 補上三者的 HP。
- 潮汐之矛的居高型態原本只有「射程 +2」，射程不計預算，與直線型態（形狀 ×1.4）無法同時落在 70%–100% 的窗內（可行區間只有 2%）；所以居高型態另加「擊倒」（第 2 項替換）。

### 7. AI（PM 決定 #9）

- 新模組 `src/trpg/engine/ai/variant.py`：
  - `cast_form`：AI 評估（`effective_skill`、改寫型收益）用目標點選出的型態。合法動作已列出每個型態的選取、預覽以同一型態結算，所以每個可行型態都會被評估。
  - `variant_move_bonus`：移動目的地能讓某招「現在可用」的技能的變奏成立（現在的位置不成立）→ 加 `basic.variant_position_bonus`（`content/ai_profiles.yaml`，初值 3，保守）。只看施放者位置的條件：站的表面、相鄰牆壁／擋路物件、居高（目的地比某個存活敵人高）；目標格表面不加分。不做多回合規劃。
- `UtilityAI.rank`：移動的估計分數與（有風險時）完整分數都加上這個加分。

## 驗收（逐條）

| 條件 | 證據 |
|---|---|
| schema 拒絕：普通帶變奏 | `tests/content/test_variant_schema.py::test_common_skills_cannot_carry_variants`（稀有 1／史詩 2：`test_rare_skills_carry_one_and_epic_two`） |
| schema 拒絕：複合技帶變奏 | `test_composite_skills_cannot_carry_variants` |
| schema 拒絕：換主傷害（與唯一效果） | `test_the_main_damage_and_the_only_effect_cannot_be_replaced` |
| schema 拒絕：3 個變奏 | `test_three_variants_are_rejected` |
| 其他拒絕（非主動、條件格式、替換數、改代價／骨架、未知表面、weapon 射程） | `test_only_active_skills_may_carry_variants`、`test_bad_variant_shapes_are_rejected`（7 例）、`test_unknown_surfaces_are_cross_checked`、`test_range_delta_needs_a_numeric_range` |
| 四種條件的成立／不成立 | `tests/engine/test_variants.py::test_caster_surface_holds_only_when_standing_on_the_listed_surface`、`test_caster_high_ground_needs_at_least_one_level_above_the_target_point`、`test_adjacent_blocker_counts_walls_and_blocking_objects_in_eight_directions`、`test_target_surface_looks_at_the_target_point`、`test_variant_holds_checks_one_condition_at_a_time` |
| 多個成立取第一個 | `test_the_first_variant_in_data_order_wins_when_several_hold` |
| 目標依賴條件的合法性與射程 | `test_high_ground_range_bonus_only_reaches_lower_target_points`（低處目標 5 格合法、同高 5 格不在合法動作且 `resolve` 拒絕）、`test_standing_in_water_turns_the_spear_into_a_lightning_line` |
| 等級與修正疊在變奏之後 | `test_skill_level_applies_after_the_variant`（基礎單體 5 級＝冷卻 −1；水中直線 5 級＝範圍 +1）、`test_modifiers_apply_after_the_variant_and_the_level`（直線 3 → 修正 4 → 等級 5） |
| 施放事件 `variant`、紀錄文字 | `test_plain_cast_has_no_variant`、`test_the_battle_log_names_the_variant`、`tests/cli/test_variant_cli.py::test_a_variant_battle_logs_the_form_and_replays` |
| 預算逐型態 ＋ 加價 | `test_budget_adds_the_surcharge_per_variant_and_reports_each_form`、`test_a_form_outside_the_window_is_a_violation`、`tests/cli/test_variant_cli.py::test_budget_lists_every_form` |
| 關鍵字聯集 | `test_keywords_are_the_union_of_all_forms` |
| 示範技能（稀有 2、史詩 2、四種條件、近戰與法術、過預算、圖示） | `test_the_demo_skills_cover_every_condition_and_pass_validation` |
| AI 會移到水格再施放潮汐之矛 | `tests/engine/test_variant_ai.py::test_the_ai_steps_into_water_and_casts_the_tidal_spear_line`（先 Move 到水格，再施放 `tide_pierce`）；加分細節 `test_the_move_bonus_only_counts_tiles_that_newly_satisfy_a_variant`、`test_the_move_bonus_counts_high_ground_above_an_enemy` |
| 每招 AI 會用 | `test_the_ai_uses_every_demo_skill_in_its_variant_form`（4 例；三招在場景中施放的是變奏型態） |
| 同種子確定 | `test_same_seed_same_battle_and_replay_is_identical`（引擎）、`test_a_variant_battle_logs_the_form_and_replays`（CLI 兩次紀錄的事件與動作相同） |
| `--log-json` ＋ `replay` 一致 | `test_a_variant_battle_logs_the_form_and_replays`：`trpg battle --map swamp --allies variant_vanguard,variant_tidecaller,variant_slinger --seed 0 --log-json …` 後 `trpg battle replay …` →「重播驗證通過」，紀錄中有 `variant` 非 null 的 `skill_used` |
| `check.py` 全過 | 最後一次 `uv run python scripts/check.py`：ruff check／format、mypy、lint-imports、pytest（4236 passed）、client install／typecheck／test（664 passed）全部通過（「全部檢查通過。」） |

## 影響既有測試與內容

- `LOG_FORMAT` 斷言 `/46` → `/47`：`tests/cli/test_basic_actions_cli.py`、`test_battle_cli.py`、`test_run_battle_cli.py`、`test_skills_cli.py`、`test_weapons_24a2_cli.py`、`tests/engine/test_gear_g2.py`、`test_gear_g3a.py`、`test_24c.py`。
- 技能數 193 → 197：`tests/cli/test_budget_cli.py`。
- `tests/content/test_con_hp.py`：補 3 個示範單位的 HP。
- `tests/cli/snapshots/cli_output_hashes.json`：`skills_list`、`skills_show_all` 更新；戰鬥快照不變。
- `client/src/render/fixtures/skill_icons.json`：依 `test_client_fixture_is_current` 的指示以 `uv run python -m tests.narrative.icon_fixture` 重產（純資料、Python 產生；沒有動前端程式）。
- 釘種子的測試：一開始關鍵字推導對開局池也取聯集時，`trpg run auto --seed 4` 的開局抽到靠牆盾擊（撞擊只來自變奏），`test_run_auto_reaches_a_branching_evolution[4]` 失敗；改成開局池／候選只看基礎型態後軌跡回到原樣，**沒有換種子**。

## 複雜度

沒有新增任何 `noqa`（C901、PLR0911、PLR0912、PLR0915 皆無）。

## 待 PM 決定

1. **開局技能池與候選產生器是否計入變奏型態的關鍵字**：目前 `exclusive_only` 只看基礎型態（特定地形才有的關鍵字不讓技能進池；保守，且不改變既有種子軌跡）；一般推導（驗證「每招至少一個關鍵字」、技能卡）取聯集並以 `variant` 標記。
2. **技能卡「（特定地形）」**：`SkillKeywords.variant` 已提供，但卡片欄位在 OpenAPI 裡，留給 3-25b 一併做。
3. **「黑暗」與「草叢」**：`darkness` 是表面，可用；草叢是地形（`grass`）不是表面，條件不支援（`caster_surface: [grass]` 會被「未知的表面」拒絕）。
4. **相鄰擋路的範圍**：只算牆壁地形（`is_wall`：不可走、擋視線、非致命）與 `blocks_move` 物件；深淵、岩漿、地圖邊、單位都不算。
5. **目標點的定義**：單位目標 → 指定格 → 目標物件；方向型（直線、錐形）與自身型沒有目標點，居高與目標格表面一律不成立。若要讓方向型也能居高，需要定義方向型的「目標點」。
6. **`element` 替換的範圍**：只換頂層 `damage` 效果（含變奏加上的），巢狀（`then`、賭注分支、擊殺時效果）與其他帶元素的原語（`delayed_damage` 等）不換。
7. **`range_delta` 不能用在 `range: weapon` 的形狀**（保守，直接拒絕）；若要支援武器射程 ±，需另定義。
8. **後續查表仍用基礎技能**：區域（`zone`）、延遲效果、`copy_skill` 的複製對象等以 `skill_def(id)` 查到的是基礎型態（示範技能都沒有這些效果）。變奏目前不建議與這些原語搭配，或之後在 schema 加限制。
9. **潮汐之矛居高型態加了擊倒**（見示範技能說明）：射程 ± 不計預算，單純「射程 +2」的型態與直線型態無法同時落在預算窗內。是否要讓射程 ± 計價（例如每格 +x‰）請決定。
10. **AI 加分初值 3**：在測試場景中剛好能讓水格勝過一般接近的格子，但仍輸給有收益的普攻（AI 一次只看一步）；`variant_position_bonus` 待模擬調整。示範單位 `variant_*` 是否要併進某個 sim build 也請決定（目前只為覆蓋率與 CLI 試玩存在）。
