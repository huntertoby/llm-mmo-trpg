# Phase 2H-2 報告：雙屬性縮放與專精加成

## 1. Commit 列表

- `Add dual-attribute scaling, mastery bonus, shared skill_scaling_value and demo skills`（4.1、4.2、4.3 全部：欄位與驗證、共用函式、組合器、CLI、示範技能、測試）
- 本報告 commit

## 2. 驗收逐條結果

1. 通過。測試都在 `tests/engine/test_dual_scaling_mastery.py`（另有 CLI、組合器、覆蓋率測試）：
   - 4.1：`test_scaling_value_is_the_floored_average_of_the_two_effective_attributes`（奇數捨去）、`test_scaling_value_uses_effective_attributes_including_status_bonuses`、`test_spell_damage_uses_the_average`、`test_spell_hit_uses_the_average`、`test_heal_scaling_uses_the_average`、`test_status_save_uses_the_average`（控制抵抗）、`test_knock_prone_contest_uses_the_average_for_the_attacker`、`test_preview_uses_the_average`、`test_a_dual_skill_must_not_repeat_the_primary_attribute`（與主屬性相同被拒）、`test_dual_scaling_needs_epic_or_better`、`test_the_validator_rejects_a_dual_skill_below_epic`（非史詩被拒）。
   - 4.2：`test_mastery_is_active_when_the_scaling_attribute_is_the_highest_including_ties`（最高含並列生效、非最高不生效）、`test_mastery_uses_base_attributes_not_status_bonuses`、`test_range_mastery_makes_a_target_one_tile_farther_legal`、`test_range_mastery_extends_the_cast_distance_but_not_the_area_size`、`test_duration_mastery_adds_one_turn_to_the_applied_status`（含力量較高時不生效）、`test_duration_mastery_does_not_change_the_self_status_cost`、`test_preview_shows_the_mastered_status_duration`、`test_invalid_mastery_combinations_are_rejected`（range 無距離、duration 無狀態、雙屬性併用皆被拒）。
   - 組合器：`tests/skillgen/test_random_composer.py::test_the_composer_sometimes_adds_a_valid_dual_attribute_or_mastery`；CLI：`tests/cli/test_skills_cli.py::test_skills_show_displays_dual_scaling_and_mastery`。
2. 通過。見第 7 節 grep 結果：所有技能縮放值的讀取都經過 `skill_scaling_value`（`src/trpg/engine/skills/scaling.py`）。
3. 通過。`skill_arcane_blade` 88.5%、`skill_shatter_blast`、`skill_dread_gaze` 預算不變（專精不計預算）；`trpg skills budget --all`：通過 62 個、違規 0 個；三者皆已裝備；`tests/content/test_coverage.py::test_dual_scaling_and_both_masteries_are_used_by_handwritten_skills` 與其他覆蓋率測試通過。
4. 通過。`uv run python scripts/skill_fuzz.py --count 1000`：組合成功 1000/1000、通過驗證 1000/1000、**例外 0 個**。`trpg battle --map open_plain --seed {3,4,5} --ally-build build_push,build_warlock,build_fire --log-json` → `trpg battle replay`：三場皆「重播驗證通過」（例如 69 個動作、234 個事件，最終狀態一致）。節錄見第 8 節。
5. 通過。`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（1486 passed）全部通過。複雜度類 noqa 前後皆為 14 個（`git grep` 計數），本階段沒有新增。

## 3. 新增的資料欄位與初值（皆為初值，未經模擬）

| 檔案 | 欄位 | 初值 |
|---|---|---|
| `skills/*.yaml`／`SkillDef` | `secondary_scaling_attr`（選填） | 手寫：`skill_arcane_blade` 為 `int`（主屬性 `str`） |
| `skills/*.yaml`／`SkillDef` | `mastery`（選填，`range`／`duration`） | `skill_shatter_blast: range`、`skill_dread_gaze: duration` |
| `rules/core.yaml`／`CoreRules` | `dual_scaling_min_rarity` | `epic` |
| `skill_composer.yaml`／`ScalingRules` | `scaling.dual_permille`、`scaling.dual_attrs`、`scaling.mastery_permille` | 250、`[str, dex, int, wis, wil]`、300 |
| `skill_budget.yaml` | 僅註解：雙屬性與專精不計預算 | — |

縮放值：兩個有效屬性（含狀態加值）的平均，整數、無條件捨去；專精生效條件用基礎屬性（`UnitState.attributes`，不含狀態加值）。`LOG_FORMAT` 沒有改動（事件欄位不變；`status_save_rolled.attack_value` 在雙屬性時是平均值，`attack_attr` 仍是主屬性）。

## 4. 新技能與修改的技能

| ID | 中文名 | 預算比例 | 裝備於 | 說明 |
|---|---|---|---|---|
| `skill_arcane_blade`（新增） | 魔劍斬 | 88.5% | build_push（第 4 個主動） | 史詩、T2、法術技（`weapon_req: any`），單體射程 2，4d8 雷電傷害，縮放力量 50%＋智力 50%，AP 2、法力 6、冷卻 2 |
| `skill_shatter_blast`（加 `mastery: range`） | 碎障爆破 | 不變 | build_fire | 縮放智力、build_fire 智力最高 → 射程 4 → 5，3×3 大小不變 |
| `skill_dread_gaze`（加 `mastery: duration`） | 恐懼凝視 | 不變（70.4%） | build_warlock | 縮放智力、build_warlock 智力最高 → 恐懼 2 → 3 回合 |

## 5. 修改過期望值的測試與原因

- `tests/cli/test_budget_cli.py`：手寫技能數 61 → 62（新增 `skill_arcane_blade`），三處字串。
- `tests/engine/test_effective_attribute.py`：`base_attribute` 的允許使用者除了先攻，加入 `skills/scaling.py` 的 `mastery_active`（專精用基礎屬性，規格 4.2）；說明文字同步更新。

## 6. 複雜度類 noqa

前後皆 14 個，本階段新增 0 個。

## 7. `scaling_attr` grep 結果說明

`grep -rn scaling_attr src/trpg/engine`（技能相關）：

- `engine/skills/scaling.py`：`skill_scaling_value`（唯一的技能縮放值讀取點）與 `mastery_active`。
- `engine/skills/interpreter.py:599`：擊倒對抗傳入主屬性（守方比較用）並同時傳 `attack_value=skill_scaling_value(...)`；`:648`：`status_effect(attack_attr=..., attack_value=skill_scaling_value(...))`，主屬性只用來寫進事件。
- `engine/skills/interpreter.py` 的 `_spell_scaled`（治療／護盾）、`targeting.py` 的 `skill_profile`（法術命中）與 `damage_parameters`（法術傷害）：已改呼叫 `skill_scaling_value`，不再出現 `scaling_attr`。
- `engine/preview.py:524`：擊倒預覽的 `attr` 只用來取**守方**同屬性；攻方值用 `skill_scaling_value`；狀態抵抗預覽 `status_save_chance(state, skill_scaling_value(...), plan)`。
- `engine/control.py`：只剩 docstring；`status_save_chance`、`status_effect` 改收攻方「值」而不是屬性。
- 其餘出現的 `weapon.scaling_attr`（`battle.py`、`reactions.py`、`rules/combat.py`、`preview.py:327`）是武器自己的縮放屬性（普攻與武器技的傷害、命中），規格要求照舊。

## 8. 代表性 CLI 輸出節錄

`uv run trpg skills show skill_arcane_blade`：

```
魔劍斬（skill_arcane_blade）
  階級 T2（等第 1）  稀有度 史詩  種類 主動  骨架 strike
  分類 法術技  武器需求 任何武器  縮放屬性 力量 50%＋智力 50%
  代價 AP 2，法力 6，冷卻 2 回合
  形狀 單體（射程 2）
  效果：
    1. 4d8＋力量／智力加成的雷電傷害（敵方）
```

`uv run trpg skills show skill_dread_gaze --unit build_warlock`（`--unit build_healer` 則顯示「智力不是最高屬性，未生效」；省略 `--unit` 只顯示加成內容）：

```
  縮放屬性 智力
  專精加成 施加的狀態持續 +1 回合（智力為最高屬性，生效中）
```

`uv run trpg battle --map open_plain --seed 4 --ally-build build_push,build_warlock,build_fire`（碎障爆破的節錄來自種子 3／5）：

```
  位移流英雄 施放「魔劍斬」（AP 2，法力 6，冷卻 2 回合）→ 影響 1 格
  位移流英雄 以「魔劍斬」攻擊 盜賊弓手：d20=1 修正 -1 熟練 +2 = 2（目標 11）→ 自然 1，失手
  火焰流英雄 施放「碎障爆破」（AP 2，法力 6，冷卻 2 回合）→ 影響 9 格
  火焰流英雄 以「碎障爆破」攻擊 盜賊2：d20=15 修正 +0 熟練 +2 = 17（目標 11）→ 命中
    盜賊2 受到 13 點火焰傷害［骰 3+2］，HP 21 → 8
```

`trpg battle replay`：`重播驗證通過：73 個動作、294 個事件，最終狀態一致（open_plain，種子 4）。`

## 9. 待 PM 決定

1. **擊倒對抗的守方值**：攻方用平均，守方仍用主屬性同屬性（規格只提攻方值）。若要對稱（守方也取同一組屬性的平均）需再改 `contest` 與預覽。
2. **事件顯示**：`status_save_rolled` 沒有新增第二屬性欄位，雙屬性時 CLI 顯示「力量 12 vs …」（主屬性名稱配平均值）。要精確顯示需升 `LOG_FORMAT` 加欄位，這次沒做。
3. **專精與雙屬性互斥**寫在 `SkillDef` 驗證；雙屬性的稀有度門檻在 `core.yaml`（`dual_scaling_min_rarity`），因 `content.skills` 不能匯入 `content.rules` 的循環，稀有度型別以字面值宣告。
4. **`mastery: duration` 的範圍**：加在該技能所有 `apply_status` 效果（含對自己的增益）；永久狀態（無持續回合）不變；Boss 轉換後的狀態沿用同一個加成後的持續。不影響 `self_status` 代價、表面與陷阱。
5. **`mastery: range` 套用 `range: weapon`**：武器射程 +1。中心格型的 `range` 也 +1（包含 `range: 0` 的技能）。反應技 `single` 形狀同樣吃加成。
6. **組合器順序**：雙屬性與專精在強度調整成功「之後」才抽（兩者不計預算），因此既有種子的技能結構不變，只多出欄位；第二屬性從 `dual_attrs`（不含體質）抽。專精只給主動技能，反應、被動、姿態不給。
7. **`skill_arcane_blade` 的數值**（4d8、冷卻 2、射程 2、掛在 build_push）是為了讓預算落在合格區間的初值；build_push 的智力只有 10，平均 13，之後可考慮改裝在力量／智力較均衡的新 build。
8. **加上專精的既有技能** 會讓 `build_fire`／`build_warlock` 的模擬數字微幅改變（射程 +1、恐懼 +1 回合），沒有跑 completion／matrix。
9. **CLI `--unit`**：`trpg skills show <id> --unit <單位範本或 build ID>` 是額外加的小選項（規格只要求「單位資訊不可得時只顯示加成內容」）；Phase 3 技能卡片 UI 可沿用 `mastery_active`。
