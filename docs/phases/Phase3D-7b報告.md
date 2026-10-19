# Phase 3D-7b 報告：賭博型技能（高變異 ＋ 超載 ＋ 以血換力 ＋ 依情況縮放）

## 1. commit

| commit | 內容 |
|---|---|
| 5d63b80 | 內容層：傷害效果的 `explode`、`scaling`；技能的 `crit_range`、`damage_permille`；層數的 `overload`；`core.yaml` 的 `explode_max`、`scale_cap_max_permille`；預算（期望值公式）；`cost.on_miss` 最低稀有度 rare（3D-7a 驗收決定）；五個示範技能與 build 配置；預覽用的爆骰分布；schema／預算測試 |
| 5c94f86 | 引擎：爆骰、暴擊範圍、基礎傷害折扣、縮放、超載（每層加成、門檻反噬並清空）；事件 `OverloadTriggered`、`damage_dealt.exploded`；紀錄文字與技能卡片文字；引擎／預覽／文字測試；3D-7a 的重播測試改成兩個種子 |
| f681455 | `LOG_FORMAT` `/27` → `/28`；CLI 測試與快照重錄 |
| 90f9dd9 | API 預覽與技能卡片的測試 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 高變異（B）

```yaml
effects:
  - {type: damage, multiplier_permille: 2000, explode: true}   # 爆骰
crit_range: 17            # 技能層級，15–19；取技能與武器（法術技為 20）中較寬的
damage_permille: 750      # 技能層級，100–999：技能的每個傷害效果再 × 它
```

- **爆骰**：每顆傷害骰擲到最大值就再擲一顆，每顆原本的骰子最多再擲 `core.explode_max`（2）次；暴擊時骰數加倍、每顆都可以爆。擲骰順序固定（先擲完一顆的連爆再擲下一顆），只用戰鬥內的 `Rng`。`damage_dealt.rolls` 包含所有擲出的值，新欄位 `exploded` 是多擲的顆數；紀錄寫成「［骰 6+6+3］（爆骰 ×2）」。
- **預算**：爆骰以公式 `E_k = (s+1)/2 + E_(k-1)/s`（s 面數、k 再擲上限）算期望值（不跑模擬）；法術技用自己的骰子面數，武器技用 `explode_weapon_sides`（8）；傷害點數 × `1 + (E_k/E_0 − 1) × 骰子占比`（武器技占比 `variance_dice_share_permille` ＝ 700‰，法術技 100%）。暴擊範圍：額外暴擊率 `(20 − crit_range)/20` × 骰子占比；`damage_permille` 直接乘。
- **預覽**：傷害範圍的最大值取全部爆滿（`FixedRng` 的 max），期望值依爆骰分布精確計算（`dice_distribution(count, sides, explode_max)`）；暴擊率用技能的 `crit_range`。

### 2.2 超載（D）

```yaml
# content/stacks.yaml
- id: overload_surge
  owner: self
  max: 5
  overload:
    tag: overcurrent               # 持有者帶此標籤的技能，每層傷害 +per_stack_damage_permille
    threshold: 5
    per_stack_damage_permille: 200
    backlash:                      # 1–2 個，只能是 damage（dice + element）或 apply_status
      - {type: damage, dice: 2d6, element: lightning}
```

- 加成：持有者的帶標籤技能，每層傷害 +200‰（與縮放、消耗層數的加成一起加在同一個傷害倍率上）。
- 門檻：`add_stacks` 累積到 `threshold` 時，發出 `OverloadTriggered`、清空層數（`StacksChanged`，原因 `overload`），再對持有者結算 `backlash`（傷害 `cause: backlash`，反噬上限沿用 3D-7a，最多留 1 HP；狀態不能是硬控、跳過回合或持續傷害，由 `Ruleset._check_overloads` 檢查）。
- 預算：帶標籤的技能傷害點數 × `1 + 平均層數 ((門檻−1)/2) × 每層‰ × overload_expected_permille`；累積超載層數的技能（沒有消耗層數的技能）以「反噬點數 × 自傷折合 × 層數 ÷ 門檻」計為負點數。

### 2.3 以血換力 ＋ 依情況縮放（E、#7 G）

```yaml
- type: damage
  multiplier_permille: 1600
  scaling: {by: missing_hp_10pct, per_step_permille: 80, cap_permille: 800}
```

- `by` 四種：`missing_hp_10pct`（施放者每少 10% 最大 HP，不足 10% 的零頭不算）、`distance`（與目標的曼哈頓距離）、`enemies_adjacent_target`（目標相鄰的、對施放者而言的敵人數）、`enemies_adjacent_self`（施放者相鄰的敵人數）。
- 加成 ＝ `min(步數 × per_step_permille, cap_permille)`，加進傷害倍率（與超載、消耗層數加成相加），最後傷害無條件捨去；`cap_permille` 必填且 ≤ `core.scale_cap_max_permille`（800，跨檔案檢查）。
- 預算：`scale_expected_steps_milli`（missing_hp 2、distance 3、兩種周圍敵人數各 1.5 步）× per_step，受 cap 限制。
- 實作在 `trpg/engine/skills/variance.py`（`scale_steps`、`scale_bonus`、`overload_bonus` 三個純函式）。

### 2.4 賭博標籤與變異加成

`SkillDef.is_gamble` 擴充：有 `gamble`、`cost.on_miss`、`explode`、`crit_range`，或縮放依據為 `missing_hp_10pct` 者算賭博型（自動加標籤 `gamble`、可用預算 × 1100‰）。依距離／周圍敵人數縮放不算賭博，不加標籤、不加變異加成。超載的技能（過載電流）在 YAML 手寫標籤 `gamble`，預算由超載規則自己反映。

### 2.5 示範技能與 build

| 技能 | 機制 | 數值（初值） | 預算 |
|---|---|---|---|
| 狂野之刃 `skill_wild_blade`（稀有、打擊） | B：爆骰 ＋ 暴擊 17–20 ＋ 基礎傷害 −25% | 倍率 ×2.0 × 0.75 ＝ ×1.5 | 77.3% |
| 過載電流 `skill_overcurrent`（稀有、蓄力） | D：超載 | 1d8 雷電；累積 1 層 `overload_surge` | 78.8% |
| 狂戰士之怒 `skill_berserker_rage`（稀有、打擊） | E：每少 10% HP +8%（上限 +80%） | ×1.6 | 78.8% |
| 遠距狙擊 `skill_sniper_shot`（普通、打擊、遠程） | G：每距 1 格 +8%（上限 +40%） | ×1.4 | 77.5% |
| 困獸旋斬 `skill_encircled_sweep`（普通、範圍） | G：身邊每 1 名敵人 +10%（上限 +30%） | ×0.9，ring 半徑 1 | 78.9% |

build 配置：`build_gambler` 加狂野之刃、狂戰士之怒；`build_striker` 加過載電流；`build_ranged` 以遠距狙擊換下煙霧箭、`build_tank` 以困獸旋斬換下碎骨重擊（兩者主動欄位已滿，上限 6）。

### 2.6 文字與 API

- 技能卡片（API 與 CLI 共用）：傷害效果列加「爆骰（擲到最大值再擲一次，每顆最多再擲 2 次）」「暴擊範圍 17–20」「你每少 10% 最大 HP，傷害 +8%（最多 +80%）」；有折扣的法術技加「（基礎傷害 ×0.75）」、武器技直接把倍率乘進「武器傷害 ×1.5」；累積超載層數的效果列加「超載：你帶「overcurrent」標籤的技能每層傷害 +20%；累積到 5 層時，你受到 2d6 雷電傷害（不致命）並清空層數」。
- 戰鬥紀錄：爆骰、`OverloadTriggered`（「累積到 5 層（門檻 5），超載了！」）、層數「超載清空」。
- 網頁：預覽原本就顯示傷害範圍與暴擊率，不需前端改動（API `PreviewOut` 欄位不變，`openapi.json`／`schema.d.ts` 沒有變）。

## 3. 驗收條件逐條（7.3，3D-7b）

### 驗收 1：爆骰（含次數上限）、暴擊範圍、超載、`scale` 四種依據（捨去與上限）

`tests/engine/test_variance.py`（腳本化 `Rng.randint` 固定每顆骰子）：

| 項目 | 測試 |
|---|---|
| 爆骰：6 → 6 → 3 | `test_an_exploding_die_rerolls_on_its_maximum` |
| 次數上限（第三顆是 6 也不再擲） | `test_the_explosion_stops_at_the_reroll_cap` |
| 沒擲到最大值不爆／沒有 `explode` 不爆 | `test_a_die_that_does_not_reach_its_maximum_does_not_explode`、`test_without_explode_the_maximum_roll_is_final` |
| 暴擊時每顆骰都可爆 | `test_every_die_of_a_critical_hit_can_explode` |
| 暴擊範圍（17 暴擊、16 不暴擊；法術技預設只有 20；武器技取較寬） | `test_the_skill_crit_range_widens_the_critical_hit`（2）、`test_without_a_skill_crit_range_a_spell_only_crits_on_twenty`、`test_a_weapon_skill_takes_the_wider_of_the_weapon_and_skill_crit_range` |
| 基礎傷害折扣、三者並用 | `test_the_base_damage_discount_multiplies_every_damage_effect`、`test_the_discount_explode_and_crit_range_can_be_combined` |
| 超載：每層加成、無標籤不加成 | `test_each_overload_stack_raises_the_damage_of_tagged_skills`、`test_overload_does_not_boost_skills_without_the_tag`、`test_overload_bonus_is_a_pure_function_of_stacks_and_tags` |
| 超載：未到門檻、到門檻反噬並清空（事件順序） | `test_below_the_threshold_a_hit_only_accumulates_a_stack`、`test_reaching_the_threshold_strikes_the_caster_and_clears_the_stacks` |
| 超載：反噬上限（HP 2 → 留 1） | `test_the_overload_backlash_never_kills_the_caster` |
| `scale` 四種依據 | `test_missing_hp_adds_a_step_for_every_ten_percent_of_max_hp_lost`、`test_missing_hp_is_zero_at_full_health_and_below_ten_percent`、`test_distance_adds_a_step_per_tile`、`test_enemies_adjacent_to_the_target_count_for_the_caster`、`test_enemies_adjacent_to_the_caster_count_for_every_target`、`test_allies_next_to_the_caster_are_not_counted` |
| 上限與捨去、與超載相加 | `test_the_scaling_bonus_is_limited_by_the_cap`、`test_scale_bonus_is_zero_without_scaling_and_capped_with_it`、`test_the_scaling_bonus_is_floored_in_the_final_damage`、`test_scaling_adds_to_the_overload_bonus` |

schema（`tests/content/test_variance_schema.py`）：`explode` 只能 true／只能用在 damage／不能在賭注分支與失手反噬、`crit_range` 15–19、`damage_permille` 100–999、四種 `by` 皆合法、`cap_permille` 必填且 > 800 被拒（`test_the_cap_is_required_and_limited_by_the_core_rule`）、超載層數必須是 `owner: self`、門檻不可超過 max、反噬 1–2 個、硬控／跳過回合／持續傷害（`stun`、`frozen`、`burning` 等全部不安全狀態）被拒、未知狀態被拒、`cost.on_miss` 最低 rare（`test_the_miss_backlash_needs_at_least_rare`）。

### 驗收 2：預覽顯示傷害範圍與暴擊率；預算以期望值計

- 預覽：`tests/engine/test_variance_preview.py`——`test_an_exploding_die_widens_the_damage_range_and_raises_the_expectation`、`test_the_exploding_expectation_follows_the_exact_distribution`、`test_a_wider_crit_range_raises_the_preview_crit_chance`、`test_the_preview_damage_includes_the_discount_and_the_scaling`、`test_the_demo_wild_blade_preview_has_a_higher_crit_chance_than_a_plain_weapon_skill`、`test_the_preview_does_not_change_the_state`；API：`tests/api/test_variance_api.py::test_the_preview_shows_the_damage_range_and_the_wider_crit_chance`（狂野之刃的 `crit_permille` 高於狂戰士之怒、最大值遠高於最小值）。
- 預算：`test_the_exploding_die_expectation_follows_the_formula`（`E_2 = 301/72`）、`test_the_distribution_of_an_exploding_die_matches_the_formula`（分布總數 6³、平均 301/72）、`test_the_explode_budget_is_the_expected_value_by_formula`、`test_the_crit_range_discount_and_scaling_budget_factors`、`test_the_scaling_budget_is_limited_by_the_cap`、`test_the_overload_skill_budget_counts_the_bonus_and_the_backlash_cost`（4.5 × 1.4 與 −0.7）、`test_a_gamble_skill_gets_the_variance_bonus_and_other_scaling_does_not`。

### 驗收 3：示範技能裝進 build；`check.py` 全過；重播一致

- 示範技能：`test_the_demo_skills_pass_validation_and_the_budget`（5 個，預算 77%–79%）、`test_the_demo_skills_are_tagged_and_equipped`、`test_the_demo_covers_each_primitive_field`；`tests/content/test_coverage.py` 的允許清單維持為空。
- 重播：`test_a_battle_with_the_variance_builds_replays_exactly`（build_gambler／build_striker／build_ranged，open_plain 種子 3，狀態 JSON 與事件逐一相同）。
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2609 passed**）、client typecheck／vitest（131）—「全部檢查通過」。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/engine/test_gamble.py`（賭徒 build 重播） | build_gambler 加了狂野之刃與狂戰士之怒後 AI 的選擇改變，原本的種子 5 不再有賭注；改成種子 4（賭注失敗＋反噬傷害）與種子 3（失手反噬）兩個參數化案例，仍驗證重播一致 |
| `tests/cli/test_budget_cli.py` | 技能數 115 → 120 |
| `tests/cli/test_striker_trapper_battle.py` | 蓄力流 build 技能數 4 → 5（加過載電流） |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/27` → `/28` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 3 筆：`skills_list`、`skills_show_all`（新增 5 個技能）、`battle_swamp_striker_5`（蓄力流 build 多了過載電流）；其他戰鬥快照不變 |

## 5. 新增的複雜度 noqa

**沒有新增。** 唯一的 diff 行是 `_plain_base_points  # noqa: PLR0911`——它是原本的 `_base_points`（同一個 noqa）改名而來，新的 `_base_points` 只是它的包裝（乘上高變異係數）。其餘開發中超標的函式都以拆函式解決（`_variance_factor`／`_overload_ratio`／`_overload_stack_cost`／`_roll_damage_dice`／`_overload`）。測試裡延後匯入的 `PLC0415` 不屬於複雜度類。

## 6. `LOG_FORMAT`

`/27` → **`/28`**（本段升一次）：`EffectSpec` 新欄位 `explode`／`scaling`、`SkillDef` 新欄位 `crit_range`／`damage_permille`、層數的 `overload`、`DamageEffect.explode_max`、`damage_dealt.exploded`、新事件 `overload_triggered`、`stacks_changed` 的新原因 `overload`、核心規則 `explode_max`／`scale_cap_max_permille`、預算規則；`/27` 的規則包沒有這些欄位，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **欄位名 `scaling` 而不是 `scale`**：規格寫 `scale: {by, per_step_permille, cap_permille}`，但 `EffectSpec.scale` 已被 `consume_status` 使用（值為 `remaining_rounds`／`stacks`，3C-3b），同一個欄位不能同時是字串與物件，所以新欄位叫 `scaling`（型別 `ScaleSpec`）。若要改名請告知（可把 `consume_status` 的欄位改名）。
2. **`distance` 以完整距離計步**：與目標每距 1 格 +n‰，相鄰（距離 1）也有一步，不是「距離 − 1」。遠程技貼身時仍有加成；若要「相鄰不加成」請告知（改成 `max(0, 距離 − 1)`）。
3. **哪些算「賭博型」**：除了賭注、失手反噬，我把 `explode`、`crit_range` 與 `missing_hp_10pct` 縮放也算賭博型（自動標籤 `gamble`、可用預算 × 變異加成 1100‰）；`distance` 與周圍敵人數縮放不算。超載不由 `is_gamble` 判定（它的規則在層數上），過載電流的 `gamble` 標籤是手寫的、也沒有變異加成。若認為超載的技能也要變異加成，需要決定怎麼從層數反推。
4. **`explode`／`scaling` 只能用在技能自己的傷害效果**：不能放進賭注分支、失手反噬、`consume_status` 的 `then`、區域、召喚物（保守，這些路徑沒有統一的傷害管線）。`crit_range`、`damage_permille` 只能用在主動技能。`damage_permille` 只影響技能的傷害效果（不影響賭注分支內的自傷或 `then`）。
5. **超載的細節**：標籤用 `overload.tag`（初值 `overcurrent`，新標籤）；加成以「施放前的層數」計（過載電流自己累積的那一層不加成自己這一擊）；門檻觸發後同一個技能的其餘效果照常結算；反噬傷害會套用施放者自己的元素抗性（示範：雷電修正 ×0.85）；清空的層數不會在同一次施放再累積。
6. **AI 不會避開超載**：`build_striker` 的 AI 會連續施放過載電流直到門檻（種子 3：HP 5 被反噬打到 1）。AI 只看到層數的 `ai_value`（2），沒有「接近門檻的風險」評估；平衡階段可以讓 AI 在剩 1 層到門檻時降低分數，或把 `ai_value` 設為 0。
7. **預算初值全部未經模擬**：`variance_dice_share_permille` 700、`explode_weapon_sides` 8、`scale_expected_steps_milli`（2／3／1.5／1.5 步）、`overload_expected_permille` 1000；五個示範技能的倍率是為了落在合格區間（77%–79%）而調的。建議 3C-6 的 `sim matrix` 後再調。尤其狂野之刃算上變異加成與暴擊後倍率是 ×2.0（折扣前），數值偏高是為了通過「不過弱」，請在平衡階段檢查。
8. **新增技能把 AI 的選擇改變**：`build_gambler` 加入狂野之刃與狂戰士之怒後，AI 比較常用沒有風險的新技能，血祭重擊與孤注一擲出現頻率下降（open_plain 種子 1–8 中，血祭重擊或孤注一擲只在 5 個種子出現過）；不是 bug，但賭徒流的「賭」味變淡，3C-6 整理 build 時可以斟酌。
9. **build 配置的調整**：`build_ranged` 的煙霧箭與 `build_tank` 的碎骨重擊被換掉（主動欄位上限 6，`build_ranged`、`build_tank` 已滿）；若要保留可改放別的 build，或新增一個專屬 build（會讓 build 數變 17）。
10. **沒做的**：`crit_range`、`damage_permille`、`explode` 沒有最低稀有度（規格沒有寫；示範都是 common／rare）；隨機組合器不產生這些（沿用 3D-7a 的決定，3C-6 再讓組合器產生賭博型）；`enemies_adjacent_target` 只有單元測試與預算，沒有示範技能。

## 8. 代表性的 CLI 輸出節錄

`uv run trpg battle --map open_plain --seed 3 --ally-build build_striker`，第 3 輪蓄力流英雄的回合後半（連續的一段，未剪接；層數累積到 5 層、超載、反噬不致命，HP 5 → 1）：

```
  蓄力流英雄 施放「過載電流」（AP 1，法力 3）→ 影響 1 格
  蓄力流英雄 以「過載電流」攻擊 盜賊頭目：d20=16 修正 +1 熟練 +2 = 19（目標 11）→ 命中
    盜賊頭目 受到 22 點雷電傷害［骰 6］（格擋/加成 ×1.6），HP 58 → 36
    蓄力流英雄 的「過載電流」累積：3 → 4 層
  蓄力流英雄 施放「過載電流」（AP 1，法力 3）→ 影響 1 格
  蓄力流英雄 以「過載電流」攻擊 盜賊頭目：d20=17 修正 +1 熟練 +2 = 20（目標 11）→ 命中
    盜賊頭目 受到 18 點雷電傷害［骰 2］（格擋/加成 ×1.8），HP 36 → 18
    蓄力流英雄 的「過載電流」累積：4 → 5 層
  ✦ 蓄力流英雄 的「過載電流」累積到 5 層（門檻 5），超載了！
    蓄力流英雄 的「過載電流」超載清空：5 → 0 層
    蓄力流英雄 受到 4 點反噬雷電傷害［骰 6+4］（元素修正 ×0.85），HP 5 → 1
  蓄力流英雄 結束回合
```
