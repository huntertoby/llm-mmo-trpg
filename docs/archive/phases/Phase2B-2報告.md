# Phase 2B-2 完成報告：預算與驗證器

## 1. 摘要

技能預算（`skill_budget`）與驗證器（`validate_skill`）完成：預算公式、硬性上限、6 條互斥規則、12 種骨架（啟用 6 種）、稀有度限制全部以資料檔表達，`trpg skills budget <id>｜--all` 與 `trpg content check` 可用，`trpg.content` 不得匯入 `trpg.skillgen` 的 import-linter 規則生效。2B-1 驗收後的 PM 決定 #1（Boss 轉換搬進 `apply_status`）與 #3（定身仍可站起）已實作。`tier_budget` 以腳本校準為 **T1 ＝ 14、T2 ＝ 15**（T3–T5 外推為 19／24／30）；23 個示範技能「不修改」只有 8 個完全合格，其餘 15 個依 4.8 只調整技能本身，現在全部通過。`uv run python scripts/check.py` 五項全過，**883 個測試**（2B-1 結束時 764 個）。

## 2. 交付項目與 commit 列表

| commit | 內容 |
|---|---|
| `0fca8d4` | 4.0 #1、#3：`rules/statuses.boss_converted_status`，`handlers.apply_status` 對所有來源做 Boss 硬控轉換（發 `StatusConverted`，持續時間沿用原狀態）；`movement.can_only_stand_up`，定身的倒地單位只能原地站起；測試 `test_a_non_skill_source_also_converts_stun_on_a_boss`、`test_a_prone_rooted_unit_can_stand_up_but_not_move` |
| `50715f4` | 預算資料與 schema：`content/skill_budget.yaml`、`skill_synergies.yaml`、`skill_exclusions.yaml`、`skeletons/`（12 檔）、`skill_primitives.yaml` 的 `budget_basis`／`base_points`、`skill_shapes.yaml` 的 `budget`／`min_rarity`、`statuses.yaml`／`surfaces.yaml` 的 `budget_points`、`skill_conditions.yaml` 的 `min_rarity`、`core.yaml` 的 `tier_budget`／`budget_reference_weapon_damage`；`content/skill_rules.py`（schema）、`library.py`（載入與交叉檢查）、`registry.py`；`LOG_FORMAT` → `/6` |
| `eb52399` | `skillgen/mechanics.py`（機制標籤）、`skillgen/budget.py`（`skill_budget`、`BudgetReport`）、`skillgen/validate.py`（`validate_skill`、`Violation`）、`cli/budget.py` 與 `trpg skills budget`、`trpg content check` 呼叫驗證器、import-linter 規則與 `test_architecture.py`、`scripts/calibrate_tier_budget.py` |
| `f174f77` | 示範技能調整（見 5.3）、`tier_budget` 數值、受影響的兩個測試（見驗收 7） |
| `7b1fa50` | 測試：`tests/skillgen/`（預算 20、驗證 73、校準 3）、`tests/content/test_skill_rules_content.py`（15）、`tests/cli/test_budget_cli.py`（6） |
| `bc95c83` | 骨架核心占比與角色分類一致（`_is_core`）、`content/README.md` 檔案清單 |
| （本報告的 commit） | `docs/phases/Phase2B-2報告.md` |

## 3. 驗收條件逐條結果

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `check.py` 五項全過；`trpg content check` 通過；新 import-linter 規則生效 | ✅ | `check.py`：ruff check／ruff format／mypy／lint-imports／pytest 全部通過（883 passed, 4 deselected）。`uv run trpg content check` → 「共 67 個檔案；…；23 個技能通過預算與結構驗證。」import-linter：`content 不得匯入 skillgen KEPT`；在 `content/schemas.py` 暫時加入 `from trpg.skillgen import budget` 後該契約變 `BROKEN`（已還原）。`tests/test_architecture.py` 也加入同一規則與掃描器自我測試 |
| 2 | 至少 5 個手算案例，與 `skill_budget` 完全相等 | ✅ | `tests/skillgen/test_budget.py`（`Fraction` 精確相等，註解列出手算過程）：`test_hand_case_1_weapon_skill`（武器技 12.6、可用 15.68、比例 45/56）、`_2_spell_skill_with_dice_average`（3d6、T2、比例 7/11）、`_3_affects_all_target_coefficient`（錐形 × 對象 0.8 ＝ 7.28）、`_4_effect_and_skill_conditions`（0.85 與 0.6 ＝ 7.77）、`_5_synergy_area_and_control`（×1.2 ＝ 24）、`_6_cost_allowance_caps`（折抵上限 ＝ 900‰）、`_7_synergy_stack_and_debuff`（×1.2×1.1、×1.15）；另有 `test_uses_per_battle_allowance`、`test_duration_scales_status_and_surface_points`、`test_structural_primitive_points`、`test_shape_multiplier_table`、`test_status_and_surface_points_match_the_spec`、`test_ap_coefficients_and_reaction` |
| 3 | 超預算（> 1.0）與過弱（< 0.7）被拒，訊息顯示比例 | ✅ | `test_over_budget_is_rejected_with_the_ratio`（「超出預算…133.9%」）、`test_too_weak_is_rejected_with_the_ratio`（「過弱…44.6%」）、`test_budget_boundaries_are_inclusive`（剛好 100%、剛好 70% 合格，差 0.001 就被拒）。CLI 端：`test_content_check_fails_on_a_skill_that_breaks_the_rules` |
| 4 | 4.3 每條上限、4.4 每條互斥、4.5 每種骨架結構、4.6 每條稀有度，各一個「被拒」與一個「合格」 | ✅ | 上限（`test_validate.py`）：`test_more_than_four_effects_are_rejected`（5 個拒、4 個過）、`test_push_and_pull_are_capped_at_two_tiles`（距離 3 被引用檢查擋下，1、2 通過）、`test_weapon_req_must_be_a_broad_class`、`test_at_most_one_rule_rewrite_primitive` ＋ `test_rule_rewrite_needs_once_per_battle_or_a_long_cooldown`（5 種代價）＋ `test_a_fake_rule_rewrite_primitive_needs_legendary`（以測試專用的假原語 `grant_ap`）。互斥：`test_exclusion_1_…`（square3／allies_in_radius／ring 2／cone 4 四種各拒一次，加冷卻後過）至 `test_exclusion_6_…`，`test_exclusion_messages_name_the_rule_and_the_facts`。骨架：`test_strike_structure`、`test_area_structure`、`test_control_structure`、`test_displace_structure`、`test_aura_structure`、`test_combo_structure_requires_a_condition`（形狀、核心缺少、核心占比、附帶數量、附帶原語、占比上限、對象、條件，各骨架適用的都有）＋ `test_each_enabled_skeleton_has_a_valid_example`（6 種各一個合格技能）、`test_a_skill_kind_must_match_its_skeleton`。稀有度：`test_common_skills_cannot_use_rarer_content`（結構型原語、root、cross、ground_tile、技能條件、效果條件、3 個效果各拒一次，且 rare 同樣內容不被這條拒）、`test_common_skills_can_use_numeric_primitives_and_simple_shapes`、`test_epic_and_legendary_are_at_least_as_permissive_as_rare` |
| 5 | 停用的骨架被拒 | ✅ | `test_disabled_skeletons_are_rejected`（`builder_finisher`、`trap`、`summon`、`reaction`、`stance`、`passive` 各一，規則 `skeleton.disabled`）；`test_the_initial_skeleton_structure_matches_the_spec` |
| 6 | 全部示範技能通過；`skills budget --all` 輸出附報告 | ✅ | `test_every_demo_skill_passes_validation`（23 個參數化）、`test_budget_all_lists_every_skill`；輸出見 5.2 |
| 7 | 2B-1 驗收測試仍通過 | ✅ | 全部 883 個測試通過。數值調整後有兩個測試依規定「修正設定而非放寬規則」：`tests/cli/test_demo_maps.py` 沼澤戰的種子 42 → 1（種子 42 的戰鬥在第一個環境回合前結束，不再有「環境預告」的畫面；該測試要驗證的互動片段與規則斷言都沒變）；`tests/engine/test_skill_preview.py::test_preview_expected_damage_matches_exhaustive_enumeration` 原本寫死火焰箭是 2d8，改為從技能資料讀骰子（斷言本身不變）。`LOG_FORMAT` 的 `/5` → `/6` 也同步更新兩個 CLI 測試。2B-1 的 AI 情境、確定性、狀態、抵抗、遞減、Boss 測試全部未修改 |
| 8 | 4.0 #1：非技能來源對 Boss 施加暈眩 → 緩速；#3：倒地＋定身可站起但不能移動 | ✅ | `test_status_control.py::test_a_non_skill_source_also_converts_stun_on_a_boss`（直接排入 `ApplyStatusEffect`：`StatusConverted(stun → slow)`、沒有 `StatusSaveRolled`、持續 1 回合、一般單位不轉換）；`test_statuses.py::test_a_prone_rooted_unit_can_stand_up_but_not_move`（`legal_actions` 只有「原地站起」的 `Move`、走格子的 `Move` 被拒「被定身」、站起後倒地消失、座標不變、之後沒有任何 `Move`） |

## 4. 設計與實作說明

**模組與依賴**

- `trpg.content` 只放 **資料 schema**（`content/skill_rules.py`：`BudgetRules`、`SynergyTable`、`ExclusionTable`、`SkeletonDef`），計算與驗證在 `trpg.skillgen`。`ContentLibrary` 多了 `budget`／`synergies`／`exclusions`／`skeletons` 四個欄位（不放進 `Ruleset`，所以不進戰鬥狀態）。
- `skillgen/mechanics.py`：效果的實際對象（`resolved_affects`）與機制標籤。標籤只看資料欄位：`control` ＝ 狀態有 `control_group`；`debuff` ＝ 狀態的 `damage_dealt_permille < 1000` 或 `damage_taken_permille > 1000`；`dot` ＝ 狀態有 `on_turn_start_damage`，或表面在回合開始造成傷害（直接傷害，或施加有持續傷害的狀態如燃燒）。不寫死狀態 ID。
- `skillgen/budget.py`：`skill_budget(skill, library) -> BudgetReport`。全部 `Fraction`；`BudgetReport` 帶每個效果的 `base／shape／target／condition／points`、`raw`、技能條件、機制標籤與協同、`total`、`tier_budget`、AP 係數、折抵明細、`usable`、`ratio`、`ok／too_weak／over_budget`。缺少點數資料（例如 `defending` 沒有 `budget_points`、passive／stance 沒有 AP 係數）拋 `BudgetError`，驗證器轉成 `budget.unavailable`。
- `skillgen/validate.py`：`validate_skill(skill, library) -> list[Violation]`（`skill_id`、`rule`、中文 `message`）。順序：`reference`（沿用 2A 的 `skill_problems`，有問題就不再往下）→ `cap.*` → `exclusion.<id>` → `skeleton.*` → `rarity.*` → `budget.*`，回報 **全部** 違規。
- 互斥規則是通用 DSL：`when`（可省略）＋ `forbid`／`require`，比對欄位 `shapes`（可帶參數，例如 ring 半徑 2）、`has_cooldown`、`min_cooldown`、`statuses`、`primitives_any／all`、`effects_any／all`（`type` ＋ `affects`，`all` 同時算敵方與友方）、`repeated_control_group`。六條初始規則都是資料，驗證器沒有針對單條規則的程式。
- 骨架：`core`（原語、對象限制、最低占比‰）、`secondary`（允許原語或不限、`harmful_only`、`max_count`、個別原語占比上限）、`forbid_affects`、`requires_condition`。占比以 **效果點數**（含形狀、對象、效果條件倍率；不含技能層級的條件與協同）計。停用的骨架可以引用尚未實作的原語（`summon` 的 `summon`）。
- 稀有度：各資料檔的 `min_rarity`（原語、形狀、狀態、條件）＋ `skill_budget.yaml` 的 `rarity.<r>.max_effects`。所有條件的 `min_rarity` 都是 `rare`，所以普通技能沒有條件；`rule_rewrite` 原語沒有，用測試假資料驗證。
- 4.3 的「推擊、拉扯 ≤ 2 格」依規格「重用 2A 的檢查」，由 `reference` 的參數範圍（1–2）擋下，沒有另寫一份。
- `trpg content check`：載入後呼叫 `library_violations`，任何違規就以 `內容檢查失敗：N 項技能違規` 列出全部（技能 ID、規則代碼、中文訊息與數值）並回傳 1。

**重要取捨**

- 預算公式裡的「強度係數」併入各原語的點數算法（`budget_basis`：`fixed`／`per_distance`／`dice_average`／`damage`／`status`／`surface`），沒有另外的欄位。
- 狀態與表面的持續倍率 ＝ 持續 ÷ 預設持續；預設持續為 `null` 的（水、油表面，倒地）或技能沒寫持續的一律 ×1。因此 **水表面的點數永遠是 1，加長持續也不會增加**。
- `affects: self` 與 `teleport`（`acts_on: caster`）形狀倍率 1.0；`affects: tiles` 的效果（表面、地形）套用形狀倍率。
- 光環（`aura`）的「有益」以 **對象** 判斷（核心原語 ＋ 對象為 `allies`／`self`），不判斷狀態或表面本身是否有益。
- 記錄的 `StatusConverted` 在技能路徑仍由 `control.status_effect` 先發出（抵抗判定要用轉換後的狀態），轉換後的狀態不再是 `hard`，所以 `apply_status` 不會重複轉換；非技能來源只在 `apply_status` 轉換且不擲抵抗。
- 定身站起：`Move(path=(unit.pos,))`（只含自己的格子）＝ 原地站起，`plan_move` 對 `path` 長度 > 1 才擋定身；`can_only_stand_up` 同時供 `legal_actions` 與 `has_only_end_turn` 使用。
- `LOG_FORMAT` 升為 `trpg-battle-log/6`：`Ruleset` 會嵌入戰鬥狀態，`CoreRules`、`StatusDef`、`SurfaceDef`、`ShapeDef`、`PrimitiveDef`、`ConditionDef` 都新增了欄位，舊紀錄無法載入。

**骨架初始結構的微調（4.5 允許，這裡記錄）**

規格表沒寫到的細節，我採用：`control` 附帶只能是 `damage`、最多 1 個、占比 ≤ 40%；`displace` 附帶可為 `damage`／`apply_status`／`create_surface`（≤ 2 個，`damage` ≤ 50%）；`aura` 附帶不限原語（≤ 1 個）但不得有對敵方（`enemies`、`all`）的效果；`area` 的核心占比 ≥ 50%、附帶原語照規格；`control` 允許全部 10 種形狀。停用的 6 種骨架的形狀與核心是我依 6.9 的描述填的占位資料，啟用時再確定。

## 5. 數據表

### 5.1 `tier_budget` 校準

方法（`scripts/calibrate_tier_budget.py`）：對每個示範技能，只看預算比例，算出「不修改就落在 70%–100%」的 `tier_budget` 區間 ＝ `[total ÷ (AP係數 × 折抵), 該值 ÷ 0.7]`；對每個候選整數統計各階級合格的技能數；在「階級間嚴格遞增」的條件下挑 ① 合格總數最多 ② 階級差距總和最大 ③ 較小的值。以下是 **調整技能之前**（`906b07d` 的 23 個技能）的結果。

各示範技能不修改就合格的區間（階級 1，18 個）：

| 技能 | 區間 | 技能 | 區間 |
|---|---|---|---|
| summon_tide | 3.19 – 4.55 | stone_wall | 5.33 – 7.62 |
| vanish | 4.94 – 7.05 | blink | 6.81 – 9.73 |
| smoke_arrow | 6.84 – 9.77 | cleave | 8.12 – 11.61 |
| high_ground_shot | 10.45 – 14.93 | whirlwind | 10.68 – 15.25 |
| fire_arrow | 11.03 – 15.76 | piercing_shot | 11.15 – 15.93 |
| bone_crusher | 12.05 – 17.22 | frost_shackle | 13.33 – 19.05 |
| grapple_arrow | 14.71 – 21.01 | rending_strike | 15.36 – 21.94 |
| gale_kick | 17.22 – 24.60 | shield_bash | 18.85 – 26.93 |
| execute | 21.16 – 30.22 | fire_bolt | 23.30 – 33.29 |

階級 2（5 個）：chain_lightning 7.86 – 11.22、cinder_burst 10.90 – 15.57、sanctuary 11.25 – 16.07、venom_cloud 11.67 – 16.67、ashen_oath 13.79 – 19.70。

候選值 → 不修改就合格的技能數（節錄；完整 4–34 見腳本輸出）：

| tier_budget | 階級 1（共 18） | 階級 2（共 5） |
|---|---|---|
| 7 | 4 | 0 |
| 11 | 3 | 2 |
| 12 | 4 | 3 |
| 13 | 5 | 3 |
| **14** | **6** | **4** |
| 15 | 6 | **4** |
| 16 | 4 | 3 |
| 17 | 4 | 1 |
| 19 | 5 | 1 |
| 24 | 4 | 0 |

最佳（嚴格遞增）：**T1 ＝ 14（6／18）、T2 ＝ 15（4／5）**，合計 10／23 個的預算比例合格（再加上結構與稀有度規則，完全合格的只有 8 個）。階級 3–5 沒有示範技能，無法校準，**外推為 19／24／30**（約每階 +25%，與 T2 的實際強度無關；2B-3 的隨機組合器若發現某階級湊不出合格技能，再回頭調）。最終 `core.yaml`：`tier_budget: {1: 14, 2: 15, 3: 19, 4: 24, 5: 30}`、`budget_reference_weapon_damage: 7`。

### 5.2 `trpg skills budget --all`（調整後）

```
技能預算總表（共 23 個；合格區間以 total ÷ 可用預算計）：
  ID                        名稱        T  AP  total   可用    比例    違規
  skill_ashen_oath          灰燼誓約    2  2   16.00   17.40   92.0%   —
  skill_blink               閃現        1  1   7.00    8.22    85.1%   —
  skill_bone_crusher        碎骨重擊    1  2   13.50   15.68   86.1%   —
  skill_chain_lightning     連鎖閃電    2  2   13.50   15.75   85.7%   —
  skill_cinder_burst        餘燼爆發    2  2   12.43   17.10   72.7%   —
  skill_cleave              橫掃劈砍    1  2   12.74   15.68   81.2%   —
  skill_execute             處決        1  2   11.90   15.75   75.6%   —
  skill_fire_arrow          火焰箭矢    1  1   5.60    7.11    78.8%   —
  skill_fire_bolt           火焰箭      1  1   6.00    7.21    83.2%   —
  skill_frost_shackle       寒鎖        1  1   6.50    7.88    82.5%   —
  skill_gale_kick           颶風踢      1  1   6.80    7.80    87.1%   —
  skill_grapple_arrow       鉤索箭      1  1   6.80    7.80    87.1%   —
  skill_high_ground_shot    高處狙擊    1  2   11.76   15.75   74.7%   —
  skill_piercing_shot       穿透射擊    1  2   12.60   15.82   79.6%   —
  skill_rending_strike      放血斬      1  1   6.90    7.84    88.0%   —
  skill_sanctuary           聖域        2  2   13.50   18.00   75.0%   —
  skill_shield_bash         盾擊        1  2   12.90   17.08   75.5%   —
  skill_smoke_arrow         煙幕箭      1  1   6.67    8.19    81.4%   —
  skill_stone_wall          石牆術      1  1   5.40    7.17    75.3%   —
  skill_summon_tide         喚潮        1  1   5.40    7.21    74.9%   —
  skill_vanish              隱匿        1  1   6.00    7.80    76.9%   —
  skill_venom_cloud         毒霧        2  2   14.00   18.00   77.8%   —
  skill_whirlwind           旋風斬      1  2   12.60   16.52   76.3%   —
通過 23 個，違規 0 個。
```

### 5.3 被調整的示範技能（4.8）：前後對照

「前」＝ 套用最終 `tier_budget`（14／15）但技能未調整時的結果。8 個技能沒有改動：灰燼誓約、碎骨重擊、餘燼爆發、火焰箭矢、穿透射擊、聖域、毒霧、旋風斬（比例 72.7%–92.0%）。以下 15 個有改動：

| 技能 | 前（total／比例／違規） | 調整 | 後（total／比例） |
|---|---|---|---|
| 火焰箭 `fire_bolt` | 12.00／166.4%／超預算 | 2d8 ＋ 燃燒 2 回合 → **1d8 ＋ 燃燒 1 回合**（骨架 strike 要求傷害占比 ≥ 60%，1d6 ＋ 燃燒 2 回合只有 54%） | 6.00／83.2% |
| 處決 `execute` | 11.90／151.1%／超預算 | AP 1 → **2**（倍率 ×2.0 不動） | 11.90／75.6% |
| 寒鎖 `frost_shackle` | 7.50／95.2%／骨架（傷害占 46.7% > 40%）、稀有度（定身要 rare） | 稀有度 common → **rare**；傷害 1d6 → **1d4** | 6.50／82.5% |
| 颶風踢 `gale_kick` | 9.60／123.0%／超預算、骨架（傷害占 58% > 50%） | 傷害倍率 ×0.8 → **×0.4**（推 2 格不動） | 6.80／87.1% |
| 鉤索箭 `grapple_arrow` | 8.20／105.1%／超預算、骨架（傷害占 51% > 50%） | 傷害倍率 ×0.6 → **×0.4**（拉 2 格不動） | 6.80／87.1% |
| 放血斬 `rending_strike` | 8.60／109.7%／超預算 | 傷害 ×0.8 → **×0.7**；流血持續 3 → **2 回合** | 6.90／88.0% |
| 盾擊 `shield_bash` | 11.50／134.7%／超預算 | AP 1 → **2**；傷害 ×0.5 → **×0.7**（控場骨架傷害占比 ≤ 40%：4.9 ÷ 12.9 ＝ 38%）；冷卻 4、法力 4 不動 | 12.90／75.5% |
| 橫掃劈砍 `cleave` | 9.10／58.0%／過弱 | 傷害 ×1.0 → **×1.4** | 12.74／81.2% |
| 連鎖閃電 `chain_lightning` | 8.25／52.4%／過弱 | 傷害 1d10 → **2d8** | 13.50／85.7% |
| 高處狙擊 `high_ground_shot` | 11.76／74.7%／稀有度（效果條件要 rare） | 稀有度 common → **rare** | 11.76／74.7% |
| 閃現 `blink` | 4.00／48.6%／過弱 | **加一個效果**：自身隱蔽 2 回合（傳送本身只有 4 點，AP 1 的合格下限是 4.9） | 7.00／85.1% |
| 煙幕箭 `smoke_arrow` | 4.00／48.8%／過弱 | 黑暗表面持續 3（預設）→ **5 回合** | 6.67／81.4% |
| 石牆術 `stone_wall` | 3.00／38.1%／過弱 | 形狀 `ground_tile` → **`cross`**（射程 3，倍率 ×1.8）；**取消冷卻**（原冷卻 2）；法力 5 不動 | 5.40／75.3% |
| 喚潮 `summon_tide` | 1.80／22.8%／過弱 | **加一個效果**：緩速 1 回合；**取消冷卻**（原冷卻 2） | 5.40／74.9% |
| 隱匿 `vanish` | 3.00／35.3%／過弱 | 隱蔽 2 → **4 回合**；冷卻 4 → **2** | 6.00／76.9% |

調整原則：①優先改數值（骰子、倍率、持續、冷卻）；②數值要砍超過約 40% 才合格的 AP 1 傷害技能不砍，改成 AP 2（處決、盾擊）；③AP 1 的純結構技能（單一效果最多 4 點，遠低於下限 4.9）無法靠數值達標，才加第二個效果或擴大形狀（閃現、喚潮、石牆術），詳見待 PM 決定 #2。

## 6. 待 PM 決定

1. **階級曲線幾乎是平的**：依規格「示範技能不修改就合格的數量最多」校準，得到 T1 ＝ 14、T2 ＝ 15，因為 2A 的 T2 示範技能（灰燼誓約、聖域、毒霧……）本來就跟 T1 的 2 AP 技能同強度。T3–T5 的 19／24／30 純屬外推。要不要改成明確的曲線（例如 14／21／30／41／54），並把 T2 技能重新定強度？這會影響 2B-3 隨機組合器能產出的強度範圍；建議在 2B-3 開工前決定。
2. **AP 1 的結構／輔助技能太弱，我加了效果**：結構型原語點數很低（obstacle 3、teleport 4、水表面 1），單獨一個效果的 AP 1 技能最多 4 點，合格下限是 4.9。調整規則（4.8）沒有列出「新增效果」，但閃現（＋隱蔽）、喚潮（＋緩速）只能這樣才合格；石牆術改成 `cross`（5 格牆）、煙幕箭黑暗延長到 5 回合。若 PM 覺得這些改變太大，替代方案是調整 `skill_primitives.yaml` 的結構型點數（我沒有動，因為 4.8 禁止改點數表）。水表面沒有預設持續，所以延長持續不增加點數（永遠 1 點）——是否要給水一個預設持續？
3. **戰鬥平衡因預算調整而改變（2C 處理）**：火焰箭（我方主力）傷害與燃燒大幅下修、放血斬下修、橫掃劈砍（Boss）與連鎖閃電上修、處決與盾擊改成 2 AP。`sim_demo_maps.py`（種子 0–19）勝率：bridge_chasm 70%（2B-1：85%）、oil_depot 35%（50%）、swamp 85%（60%）、ruined_fort 85%（100%）；平均輪數 4.2–4.8。四個 `@pytest.mark.slow` 的平衡測試現在有 3 個失敗（bridge_chasm、swamp、ruined_fort 勝率 > 65%；2B-1 結束時 bridge_chasm、ruined_fort 就已超出）。照 2B 決定 #1，只列出、不調整。
4. **盾衛與 Boss 的招式強度**：盾擊現在是 2 AP（盾衛每回合只能打一次盾擊 ＋ 一次普攻）；橫掃劈砍 ×1.4 讓 Boss 更痛。這是為了通過預算，未經模擬評估。
5. **「有益」以對象判斷**：光環骨架只檢查對象（友方／自己）與不得有敵方效果，並不知道某個表面或狀態本身是否對友方有益（例如對友方產生火焰表面也會被視為合格的光環核心）。若要嚴格，需要在狀態與表面加 `beneficial` 欄位。
6. **骨架規格沒寫到的細節**：見第 4 節末段（`control` 附帶只允許 `damage` 且 ≤ 1 個、`displace` 附帶的允許清單、`aura` 附帶不限原語等），以及停用骨架的占位資料。請確認或指示調整；2B-3 的組合器會直接依這些資料生成。
7. **機制標籤 `dot`／`debuff` 的推導**：由資料欄位推導（有回合開始傷害 → `dot`；虛弱／易傷 ＝ 降低攻擊傷害或提高受傷）。結果：聖域（神聖表面對不死族造成傷害）帶有 `dot` 標籤；中毒的「治療減半」不算 `debuff`（符合規格列舉的 weaken／vulnerable）。目前沒有任何協同用到 `dot`，影響為零，但之後加協同時要注意。
8. **稀有度**：`concealed`、`prone`、`root`、`stun` 為 rare 以上（規格 common 只列了 6 種狀態）；`ground_tile`、`cross`、`square3`、`chain` 為 rare 以上；所有條件為 rare 以上。`epic` 與 `legendary` 的效果數上限都是 4（規格寫「同 rare」）。
9. **日誌格式升為 `trpg-battle-log/6`**：`Ruleset` 嵌入戰鬥狀態，新增欄位使舊紀錄無法載入（2B-1 的 `/5` 同理）。
10. **兩條已知但維持原樣的規則**：①控制遞減與抵抗判定仍只在技能路徑擲骰，非技能來源（表面、環境）只做 Boss 轉換與記錄遞減；②passive／stance 技能沒有預算算法（`budget.unavailable`），反應技只算預算（AP 係數 0.6）而被停用的骨架擋下，等觸發系統實作時再補。

## 7. 給下一階段的備註（2B-3）

- 組合器要用的資料全在 `ContentLibrary`：`skeletons`（形狀、核心與附帶原語清單、占比、條件需求）、`ruleset.primitives／shapes／statuses／surfaces`（`min_rarity`、`budget_points`、形狀倍率）、`budget.rarity`、`budget.allowance`、`ruleset.core.tier_budget`。`validate_skill` 回傳的 `Violation.rule` 是穩定的代碼，可用於重抽統計。
- 強度調整最簡單的做法：用 `skill_budget(...)` 的 `ratio`（`Fraction`）迴圈調骰子或倍率；效果點數的明細在 `report.effects`。AP 1 的技能可用預算只有 `7 × (1 + 折抵)`（T1），隨機組合時要避免只有單一結構型效果（見待 PM 決定 #2）。
- 目前會同時成立的形狀／骨架限制：`strike` 只能 `single`、`combo` 不含 `ring`、`aura` 只有 `self`／`allies_in_radius`／`square3`；`stun` 只能單體且冷卻 ≥ 4；沒有冷卻的技能不能用 `square3`、`allies_in_radius`、`ring` 半徑 2、`cone` 大小 4。
- `scripts/calibrate_tier_budget.py` 在技能調整後只會顯示「全部在區間內」；要重新校準（例如加入 T3–T5 的示範技能後）直接重跑即可，排序規則見腳本說明。
- 測試輔助：`tests/skillgen/helpers.py` 的 `skill(**overrides)`（合格基準技能）、`skill_raw`（`model_copy` 繞過 schema）、`rules_of`、`lib_with_rewrite_primitive`（假的改寫規則型原語）。

## 8. 附錄：代表性的 CLI 輸出節錄

`uv run trpg skills budget skill_ashen_oath`：

```
灰燼誓約（skill_ashen_oath）  階級 T2  稀有度 稀有  骨架 area  AP 2
  效果點數 ＝ 基礎點數 × 形狀 × 對象 × 效果條件：
    1. damage          2d6 平均            形狀 ×1.6   對象 ×1    條件 ×1     ＝ 11.20（基礎 7.00）
    2. create_surface  fire 3×1            形狀 ×1.6   對象 ×1    條件 ×1     ＝ 4.80（基礎 3.00）
  raw ＝ 16.00
  技能條件倍率 無
  機制標籤 damage、area、dot、surface
  協同係數 無
  total ＝ raw × 條件 × 協同 ＝ 16.00
  可用預算 ＝ tier_budget 15 × AP 係數 1.00 × (1000 + 折抵 160‰) ÷ 1000 ＝ 17.40
  代價折抵 冷卻 2 回合 +100‰、法力 12 +60‰
  比例 ＝ total ÷ 可用預算 ＝ 92.0%（合格區間 70.0%–100.0%）→ 合格
  驗證：通過
```

`trpg skills budget skill_shield_bash`（調整後；含 Boss 轉換相關的暈眩）：

```
盾擊（skill_shield_bash）  階級 T1  稀有度 稀有  骨架 control  AP 2
    1. damage          武器 ×0.7           形狀 ×1     對象 ×1    條件 ×1     ＝ 4.90（基礎 4.90）
    2. apply_status    stun 8×1            形狀 ×1     對象 ×1    條件 ×1     ＝ 8.00（基礎 8.00）
  raw ＝ 12.90
  可用預算 ＝ tier_budget 14 × AP 係數 1.00 × (1000 + 折抵 220‰) ÷ 1000 ＝ 17.08
  比例 ＝ total ÷ 可用預算 ＝ 75.5%（合格區間 70.0%–100.0%）→ 合格
```

`trpg content check` 遇到違規時（把橫掃劈砍改成 ×4.0、`cone` 大小 4 且沒有冷卻；`test_content_check_fails_on_a_skill_that_breaks_the_rules` 用同樣的資料）會列出全部違規並回傳 1：

```
內容檢查失敗：2 項技能違規：
  - skill_cleave［exclusion.no_cooldown_big_area］互斥規則「無冷卻的大範圍」：沒有冷卻的技能不得使用 square3、allies_in_radius、ring 半徑 2、cone 大小 4（形狀 cone（size 4），冷卻 無，效果 damage）
  - skill_cleave［budget.over］超出預算：total 56.00 ÷ 可用預算 14.28 ＝ 392.2%（上限 100.0%，階級 1）
```
