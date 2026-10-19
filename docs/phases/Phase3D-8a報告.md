# Phase 3D-8a 報告：吸血、聖光雙效、驅散、揭露

## 1. commit

| commit | 內容 |
|---|---|
| 51f9373 | 內容層：傷害效果的 `lifesteal_permille`、`split_heal`；原語 `dispel`、`reveal`；狀態 `revealed`（`prevents_concealment`）；預算（`dispel_*`、`reveal_*`、`lifesteal_value_permille`）；骨架與驗證（光環／範圍骨架接受聖光雙效、控場骨架核心加驅散與揭露）；4 個示範技能與新 build `build_seer`；schema／預算／覆蓋率測試 |
| 8e77c9b | 引擎：吸血、聖光雙效（骰一次、友方不擲命中）、驅散、揭露（含陷阱的 `revealed_to`）；事件 `trap_revealed`、`healed.cause`、`status_removed` 新原因；技能卡片與戰鬥紀錄文字；AI 評分；`tests/engine/test_lifesteal_dispel.py`（46 個測試） |
| b3c4b6f | `LOG_FORMAT` `/28` → `/29`；CLI 快照重錄 |
| e5a923d | API 測試（技能卡片、build 技能） |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 吸血（A）

```yaml
- {type: damage, dice: 1d10, element: shadow, lifesteal_permille: 400}   # ≤ 500
```

- 這個傷害效果對 **敵人** 實際造成的傷害（`amount − absorbed`，與 3D-7a 的自傷基準一致：含溢出、扣護盾）× n‰（無條件捨去）回復給施放者，不超過最大 HP；用一般的 `HealEffect`（`cause: lifesteal`），事件是 `healed`（新欄位 `cause`），紀錄文字加「（吸血）」。施放者已滿血、倒下、或回復量為 0 時沒有事件。
- 多目標的範圍技加總每個敵人的傷害後一次回復；`affects: all` 打到友方的傷害不算。
- 只有技能自己的傷害效果可用（不能放進賭注分支、失手反噬、`then`，與 `explode`／`scaling` 同一個限制）。
- 預算：傷害點數 × (1 ＋ n‰ × `lifesteal_value_permille`（800）÷ 10⁶)；預覽沿用 `healed`（施放者回復量的最少／最多）。

### 2.2 聖光雙效（B）

```yaml
- {type: damage, dice: 1d12, element: holy, affects: all, split_heal: true}
```

（選擇「等價寫法」：`split_heal: true` 搭配 `affects: all`，不另開 `split: {allies: heal, enemies: damage}` 的巢狀結構。）

- 敵方照一般命中判定受傷害；友方（含施放者站在範圍內時）**不擲命中**、治療同樣的骰值：技能先擲一次骰（`DamageEffect.preset_rolls`／`HealEffect.preset_rolls`），敵方暴擊時多出來的骰子另擲，所以友方治療量 ＝ 骰值 ＋ 縮放屬性 × 0.5（同傷害公式）× 受治療倍率（中毒 500‰）。沒有任何對象時不擲骰。
- 限制（schema，`SkillDef._check_split_heal`）：必須 `affects: all`、主動法術技、`aura` 或 `area` 骨架（`SPLIT_SKELETONS`）、不可與 `lifesteal`／`explode`／`scaling` 並用、只能填 `true`、只能用在技能自己的傷害效果。光環骨架把聖光雙效視為核心並略過「不得對敵方／所有單位」的檢查（`validate._is_core`、`_skeleton_violations`）。機制標籤同時加 `damage` 與 `heal`。
- 預算：傷害點數 ＋ 治療點數（同一個骰子平均），再乘形狀倍率與 `affects: all` 的對象係數 0.8（兩邊都計）。

### 2.3 互斥規則放寬（6.6）

`no_damage_with_ally_heal` 的判定條件**沒有改**：吸血與聖光雙效是傷害效果自己的欄位，不是 `heal` 效果，所以天然不受它限制；「對敵傷害 ＋ 對友治療（`heal` 效果）」的其他組合仍被拒（測試用 `holy_burst` 改成「傷害 ＋ 對友 `heal`」驗證）。規則的說明文字與註解補上「吸血與聖光雙效不在此限」。設計 6.6 要求的放寬因此以「新欄位」而不是「改規則」達成。

### 2.4 驅散（J）

```yaml
- {type: dispel, count: all, affects: enemies}    # count: 1 | all
```

- 對敵方（需命中；`affects` 不可是 `allies`／`self`／`all`）：依 3D-1 的狀態分類 `polarity: buff` 找增益，`count: 1` 取剩餘回合最長者（永久最長、同長依狀態 ID，與 `steal_buff` 同一套排序：`resources._buffs_in_order`），`all` 全部；`status_removed`（原因 `dispelled`）。減益與中性狀態（姿態、隱蔽、不死、靈魂連結）不是增益、不受影響；與奪取不同，施放者不會得到它們。沒有增益時 `effect_fizzled`（`no_buff`）。
- `EffectSpec.count` 型別擴成 `int | "all"`（原本只給 `summon`）；原語參數新增型別 `count`。
- 預算：1 個 3 點、全部 6 點（`dispel_one_points`／`dispel_all_points`）。

### 2.5 揭露（I）

```yaml
- {type: reveal, duration: 2}     # 1–3
```

- 範圍內的敵人 **自動命中（不擲命中）**：失去 `concealed` 狀態（`status_removed`，原因 `revealed`）並獲得狀態 `revealed` `duration` 回合（`prevents_concealment`）。有 `revealed` 時 `is_concealed` 一律為假（黑暗表面、草叢也不算），`apply_status` 要施加 `concealed` 時 `effect_fizzled`（`revealed`）。
- 範圍內施放者敵方陣營的陷阱對施放者陣營顯示：`TrapState.revealed_to`（新欄位，預設空）；`visible_traps` 回傳「自己的 ＋ 被揭露給自己的」，新增 `own_traps`（AI 的陷阱上限與「推到自己的陷阱上」只算自己放的）；事件 `trap_revealed` 只給揭露者的陣營（`event_filter`）；已被揭露的陷阱不重複發事件。預覽與環境預告沿用 `strip_hidden_traps`，所以 AI 不會因為揭露而知道看不見的陷阱。
- 範圍內沒有敵人也沒有敵方陷阱時 `effect_fizzled`（`nothing_hidden`）。
- 預算：`reveal_base_points`（2）＋ `reveal_round_points`（1）× `duration`。

### 2.6 示範技能與 build

| 技能 | 機制 | 預算 | 裝備 |
|---|---|---|---|
| 汲命術 `skill_life_drain`（稀有、打擊） | A：1d10 暗影，吸血 40% | 91.8% | build_support |
| 聖光爆發 `skill_holy_burst`（稀有、範圍） | B：方陣 1d12 神聖，敵傷友療 | 96.3% | build_healer |
| 破魔 `skill_dispel_magic`（稀有、控場） | J：驅散全部增益 ＋ 1d3 暗影 | 97.3% | build_seer |
| 照明彈 `skill_flare_sight`（稀有、控場、法術） | I：方陣揭露 2 回合 | 97.7% | build_seer |

build 調整（主動欄位上限 6，support／healer／warlock／ranged 都已滿）：

- `build_support` 以汲命術換下專注湧流；`build_healer` 以聖光爆發換下疾時之潮。
- **新增 `build_seer`（偵察破咒流，第 17 個 build）**：破魔、照明彈、竊取祝福、咒印，並接收被換下的專注湧流與疾時之潮（每個手寫技能都要有人裝備，`test_coverage.py` 允許清單仍為空）。

### 2.7 文字、AI 與其他

- 技能卡片（API 與 CLI 共用）：傷害效果列加「吸血：你回復造成傷害的 40%」「友方（含自己）改為治療同樣的骰值（不擲命中，只骰一次）」；新原語「驅散目標身上的全部增益」「揭露範圍內的敵人：…（不擲命中）」。戰鬥紀錄：「（吸血）」、「被驅散了」、「被揭露而消失了」、「X 揭露了 (x, y) 的敵方陷阱「…」」。
- AI（`content/ai_profiles.yaml` 的 `rewrite`，初值）：`dispel_points` 6（每驅散 1 個增益）、`reveal_points` 6（每讓 1 個敵人失去隱蔽或揭露 1 個陷阱）；沒有增益／沒有隱蔽的敵人時不會用（`test_the_ai_dispels_and_reveals_only_when_there_is_something_to_gain`）。吸血與聖光雙效由預覽的傷害、治療事件自然計分。
- 隨機組合器不產生 `dispel`、`reveal`（`_HAND_WRITTEN_PRIMITIVES`），也不會填 `lifesteal_permille`／`split_heal`。
- 網頁：沒有前端改動（OpenAPI 與 `schema.d.ts` 不變；`check.py` 的 client typecheck／vitest 通過）。

## 3. 驗收條件逐條（8.4，3D-8a）

### 驗收 1：吸血、分流效果、互斥規則放寬後其他組合仍被拒

全部在 `tests/engine/test_lifesteal_dispel.py`：

| 項目 | 測試 |
|---|---|
| 吸血：比例、事件、HP | `test_lifesteal_heals_the_caster_for_a_share_of_the_damage_dealt` |
| 護盾（扣掉吸收；全吸收則不回復） | `test_lifesteal_is_floored_and_ignores_the_shield_absorption`、`test_a_fully_absorbed_hit_steals_nothing` |
| 上限、滿血 | `test_lifesteal_never_heals_above_the_maximum_hp`、`test_lifesteal_at_full_health_does_nothing` |
| 失手、範圍加總、不算友方、受治療倍率 | `test_a_missed_attack_steals_nothing`、`test_an_area_lifesteal_sums_the_damage_of_every_target`、`test_lifesteal_does_not_count_damage_to_allies`、`test_lifesteal_is_reduced_by_the_healing_received_modifier` |
| 吸血 schema（≤ 500、只有傷害、不能在分支內） | `test_lifesteal_schema_limits` |
| 分流：敵傷友療、骰一次（腳本化骰值，骰值剛好用完） | `test_the_split_effect_damages_enemies_and_heals_allies_with_one_roll` |
| 友方不擲命中、施放者在範圍內也被治療、暴擊額外骰、沒有對象不擲 | `test_allies_do_not_roll_to_be_hit_by_the_split_effect`、`test_the_caster_standing_in_the_area_is_healed_too`、`test_a_critical_hit_adds_dice_for_the_enemy_only`、`test_a_split_effect_with_no_one_in_the_area_rolls_nothing` |
| 骨架限制與其他 schema 限制 | `test_split_heal_schema_restrictions`（strike 骨架、武器技、非 `all`、與吸血／爆骰並用都被拒）、`test_the_split_effect_is_accepted_by_the_aura_skeleton_and_priced_on_both_sides` |
| 預算兩邊都計 | 同上（`base == 13`、形狀 ×2、對象 ×0.8） |
| 其他「對敵傷害 ＋ 對友治療」仍被拒；吸血與分流不被互斥規則擋 | `test_other_damage_plus_ally_heal_combinations_are_still_rejected` |
| 預覽 | `test_the_preview_shows_the_lifesteal_as_a_heal_of_the_caster`、`test_the_preview_of_the_split_effect_lists_the_healed_allies` |

### 驗收 2：驅散、揭露

| 項目 | 測試 |
|---|---|
| 驅散全部（減益與中性保留、施放者不得到） | `test_dispel_all_removes_every_buff_and_keeps_the_rest` |
| 驅散 1 個（最長者、同長依 ID、永久優先） | `test_dispel_one_takes_the_longest_buff_first`、`test_dispel_one_prefers_a_permanent_buff` |
| 沒有增益不結算；失手不驅散 | `test_dispel_without_a_buff_fizzles`、`test_a_missed_dispel_removes_nothing` |
| 驅散 schema 與預算 | `test_dispel_schema`、`test_dispel_budget_counts_one_and_all_differently` |
| 揭露移除隱蔽、獲得 `revealed`、自動命中 | `test_reveal_removes_concealment_and_blocks_it_for_n_rounds` |
| 阻止再隱蔽（狀態與黑暗表面）、狀態消失後可再隱蔽 | `test_a_revealed_unit_cannot_hide_again`、`test_reveal_beats_darkness`、`test_a_unit_without_the_revealed_status_can_hide_again` |
| 揭露陷阱（範圍內才揭露、視角、事件只給揭露方、只揭露一次、自己的不揭露） | `test_reveal_shows_enemy_traps_in_the_area_to_the_caster_team`、`test_the_trap_reveal_event_is_only_for_the_revealing_team`、`test_own_traps_are_not_revealed_and_a_trap_is_revealed_only_once` |
| 沒有東西可揭露時不結算；schema 與預算 | `test_reveal_with_nothing_to_find_fizzles`、`test_reveal_schema_and_budget` |
| 狀態存讀（`revealed_to`） | `test_the_state_round_trips_with_a_revealed_trap` |
| AI 只在有收益時使用 | `test_the_ai_dispels_and_reveals_only_when_there_is_something_to_gain` |

### 驗收 3：手寫技能裝進 build、`check.py` 全過、重播一致

- 示範技能通過驗證與預算（91.8%–97.7%）且裝進指定 build：`test_the_demo_skills_are_valid_in_budget_and_equipped`（4 個參數）；API：`tests/api/test_lifesteal_api.py`（技能卡片、主角帶有該技能）。`tests/content/test_coverage.py` 的允許清單維持為空（只新增 `revealed` 由 `reveal` 間接產生的對應）。
- 重播：`test_a_battle_with_the_new_builds_replays_exactly`（`build_support`／`build_healer`／`build_seer`，open_plain 種子 4，狀態 JSON 與事件逐一相同）。
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（收集 2666 個；**全部通過**）、client typecheck／vitest（131）—「全部檢查通過」。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_sim_builds.py` | build 數 16 → 17（新增 `build_seer`），`BUILD_IDS` 加入、測試改名 |
| `tests/content/test_coverage.py` | `_STATUS_VIA_PRIMITIVE` 加入 `revealed`（由 `reveal` 原語間接產生，與 `shielded`／`undying` 同類） |
| `tests/content/test_skill_rules_content.py` | 控場骨架核心原語加入 `dispel`、`reveal` |
| `tests/skillgen/test_budget.py` | 狀態點數表加入 `revealed: None`（只能由 `reveal` 施加，無 `budget_points`） |
| `tests/cli/test_budget_cli.py` | 技能數 120 → 124 |
| `tests/engine/test_combo_resources.py`（AI 使用資源技能） | 專注湧流、疾時之潮從 build_support／build_healer 換到 build_seer，兩個參數改用 `build_seer`（種子 0，AI 仍會用到：法力回復與冷卻縮短） |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/28` → `/29` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 2 筆：`skills_list`、`skills_show_all`（新增 4 個技能）；戰鬥快照全部不變 |

## 5. 新增的複雜度 noqa

**沒有新增。** 開發中超標的函式都以拆函式解決（`handlers._damage_rolls`、`validate` 的小判斷、`skills._count_problem`、`interpreter` 的 `dispel`／`reveal`／`lifesteal`／`split_healed`／`split_rolls`）。測試裡延後匯入的 `PLC0415` 不屬於複雜度類。

## 6. `LOG_FORMAT`

`/28` → **`/29`**（本段升一次）：傷害效果的 `lifesteal_permille`／`split_heal`、`healed.cause`、原語 `dispel`／`reveal`、`status_removed` 新原因 `dispelled`／`revealed`、狀態 `revealed`（`prevents_concealment`）、`TrapState.revealed_to`、新事件 `trap_revealed`、預算規則；`/28` 的規則包沒有這些欄位與狀態，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **互斥規則沒有改資料，而是用新欄位繞開**：設計 6.6 說「放寬互斥規則」，但吸血（`lifesteal_permille`）與聖光雙效（`split_heal`）是傷害效果的欄位、不是 `heal` 效果，所以 `no_damage_with_ally_heal` 本來就不會擋；我只改了規則的說明文字。若希望「傷害 ＋ 吸血 ＋ 另一個對自己的 `heal`」之類的組合也放寬，需要另外決定。
2. **聖光雙效的寫法**：規格給了 `split: {allies: heal, enemies: damage}` 或等價寫法；我用 `split_heal: true` ＋ `affects: all`（只有一種分流，巢狀結構沒有額外資訊）。若之後要別的分流（例如敵方施加狀態、友方護盾），再改成巢狀。
3. **友方不擲命中、施放者站在範圍內也被治療**：規格沒寫施放者；我讓 `affects: all` 的分流把施放者（若在範圍內）算友方。暴擊只讓敵方多骰，友方治療不加倍。
4. **吸血的基準與受治療倍率**：沿用 3D-7a 的「實際傷害含溢出、扣掉護盾」；回復套用施放者的受治療倍率（中毒減半）、不套用傷害的其他倍率。若希望吸血不受中毒影響，改成直接設定 HP。
5. **揭露自動命中，並且對範圍內所有敵人施加 `revealed`（不只隱蔽中的）**：規格寫「移除範圍內敵人的隱蔽，並施加狀態」，我解讀為不擲命中；敵人沒有隱蔽時仍會獲得 `revealed`（之後 N 回合不能躲）。被揭露時 `concealed` 狀態的施加會 `effect_fizzled`。AI 只在能讓敵人失去隱蔽或揭露陷阱時才用（預覽看不到對方陷阱，AI 不會因此作弊）。
6. **被揭露的陷阱的可見範圍**：只有揭露者的陣營看得到（`revealed_to`），放置者陣營不變；已揭露的陷阱仍可被觸發（不會消失）；CLI 的 HUD 與網頁會把它當成「我方看得到的陷阱」顯示，沒有另外區分「敵方的」。要不要用不同標記，留給 3-5 的網頁決定（`PM交接.md` 第 5 節「察覺陷阱」仍是開放問題，這只解決了「用技能揭露」的一半）。
7. **新增 `build_seer`（第 17 個 build）**：support／healer／warlock／ranged 的主動欄位都已滿（6），一定要換掉一個才能裝新技能，而每個手寫技能都必須有人裝備；為了不把被換下的技能弄丟、也不破壞既有 build 的測試（例如蓄力流 build 的技能數），新增一個偵察破咒流，接收被換下的專注湧流與疾時之潮。`sim matrix` 的格數因此增加；3C-6 整理 build 時可以合併。
8. **驅散示範用 `count: all`**：預算上，`count: 1` 加上控場骨架的傷害占比上限（40%）與稀有度過弱，示範技能放不進合格區間，所以「破魔」用驅散全部（6 點）＋ 1d3 傷害；驅散 1 個只有單元測試與預算。
9. **預算初值全部未經模擬**：驅散 3／6 點、揭露 2 ＋ 1/回合、吸血價值 800‰、聖光雙效兩邊都計；AI 的 `dispel_points`／`reveal_points` 各 6。示範技能的數值是為了落在合格區間（92%–98%）而調的；請在 `sim matrix` 後的平衡階段檢查（聖光爆發在敵我都有人時雙邊都算，對只有敵人的情況可能偏弱）。
10. **沒做的**：`dispel`／`reveal`／吸血／聖光雙效沒有最低稀有度以外的限制（原語 `min_rarity: rare`，吸血欄位沒有）；`dispel` 不能對友方（沒有「清除友方減益」的需求，那是 `cleanse`）；組合器不產生這些；沒有前端改動（陷阱揭露後的網頁標記留給 3-5）。

## 8. 代表性的 CLI 輸出節錄

`uv run trpg battle --map open_plain --seed 0 --ally-build build_support`，輔助英雄的一個回合後半（連續的一段，未剪接；汲命術命中後回復傷害的 40%，12 × 0.4 → 4）：

```
  輔助英雄 施放「汲命術」（AP 1，法力 6，冷卻 2 回合）→ 影響 1 格
  輔助英雄 以「汲命術」攻擊 盜賊2：d20=12 修正 +1 熟練 +2 = 15（目標 11）→ 命中
    盜賊2 受到 12 點暗影傷害［骰 3］，HP 30 → 18
    輔助英雄 回復 4 HP（吸血），HP 33 → 37
  輔助英雄 從 (0, 3) 移動到 (2, 4)（消耗 3 移動）
  ◇ 標準隊友（戰士） 進入「戰歌」區域（深度 1）
  標準隊友（戰士） 刷新狀態「激昂」（1 回合）
  ◇ 標準隊友（弓手） 進入「戰歌」區域（深度 1）
  標準隊友（弓手） 獲得狀態「激昂」（1 回合）
  ★ 輔助英雄 的被動「調息」觸發（回合結束時，深度 1）（法力 2）
    輔助英雄 回復 3 HP，HP 37 → 40
  輔助英雄 的「激昂」結束了
  輔助英雄 結束回合
```
