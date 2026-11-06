# Phase 2G-2 報告：示範技能

## 1. Commit 列表

- `Add twelve demo skills covering remaining triggers, reactions and terrain primitives`（12 個技能 YAML、builds.yaml、覆蓋率允許清單清空、行為測試、受影響測試的數量更新）
- 本報告 commit

## 2. 驗收逐條結果

1. 通過。`tests/content/test_coverage.py` 的 `_UNCOVERED` 已全部清空（所有分類皆為空），`test_every_defined_mechanic_is_used_or_explicitly_allowed`、`test_uncovered_allowlist_is_not_stale` 通過。`summon` 因骨架停用不在檢查範圍。
2. 通過。`uv run trpg skills budget --all`：通過 59 個，違規 0 個；新技能的行見第 3 節。
3. 通過。每個新技能都已裝備（`test_every_handwritten_skill_is_equipped_by_a_build_or_unit`），行為測試在 `tests/engine/test_demo_skills.py`（12 個測試，一技能一個）。
4. 通過。`trpg battle --map dark_forest --seed 7 --ally-build build_storm,build_ranged,build_assassin --log-json f` → `battle replay f`：56 個動作、205 個事件；`bridge_chasm` 種子 3、`build_push,build_support,build_trapper`：119 個動作、424 個事件，重播皆通過。節錄見第 8 節。
5. 通過。`scripts/skill_fuzz.py --count 1000`：例外 0 個；`scripts/check.py`：ruff、format、mypy、lint-imports、pytest（1427 passed）全部通過；本階段沒有新增任何 noqa。

## 3. 新技能一覽與裝備

| ID | 中文名 | 覆蓋的 ID | 預算比例 | 裝備於 |
|---|---|---|---|---|
| `skill_crippling_crit` | 致命破綻 | `on_crit`、狀態 `weaken` | 98.5% | build_assassin |
| `skill_lucky_break` | 天賜好運 | `on_natural_20` | 98.4% | build_ranged |
| `skill_bloodlust` | 嗜血 | `on_kill` | 82.5% | build_push |
| `skill_steady_breath` | 調息 | `on_turn_end` | 99.0% | build_support |
| `skill_fleet_foot` | 疾行 | `on_move` | 70.7% | build_trapper |
| `skill_twin_strike` | 雙連電擊 | `every_n_hits`（n=2） | 70.7% | build_storm |
| `skill_conductive_strike` | 導電連擊 | 骨架 `combo`、條件 `target_on_surface` | 76.8% | build_storm |
| `skill_reflex_ward` | 反射護幕 | 反應事件 `hit_by_attack` | 78.2% | build_support |
| `skill_parting_slash` | 斷後斬 | 反應事件 `enemy_leaves_adjacent` | 83.3% | build_push |
| `skill_raise_perch` | 築高台 | 原語 `raise_terrain` | 96.4% | build_ranged |
| `skill_sinkhole` | 陷地術 | 原語 `lower_terrain` | 96.4% | build_trapper |
| `skill_shatter_blast` | 碎障爆破 | 原語 `destroy_object` | 88.5% | build_fire |

各 build 技能數：push 3 主動＋1 被動＋1 反應；fire 4 主動；storm 4 主動＋1 被動；ranged 4 主動＋1 被動；assassin 4 主動＋1 被動；support 3 主動＋1 被動＋1 反應；trapper 4 主動＋1 被動。皆在主動 ≤6、被動 ≤2、反應 ≤1 內。沒有新增 build（仍為 12 個）。

## 4. 覆蓋率測試允許清單（結束時）

空（`skeleton`、`trigger`、`reaction_event`、`condition`、`primitive`、`status`、`stack` 皆為 `{}`）。所有 `enabled: true` 的機制都有手寫技能示範。

## 5. 修改過期望值的測試

- `tests/cli/test_budget_cli.py`：技能總數 47 → 59（兩處）。
- `tests/sim/test_skill_report.py`：`--demo --random 1` 的技能數改為 `len(library().skills) + 1`，不再寫死 48。
- `tests/sim/test_matrix.py`：build_push 的英雄技能改比對前三個（`hero.skills[:3]`），因為尾端新增了兩個技能。
- `tests/cli/test_striker_trapper_battle.py`：build_trapper 技能數 3 → 5。
- `tests/content/test_sim_builds.py`：「不相容技能被拒絕」測試原本替換 `skill_blink]`，build_push 尾端改變後改替換 `skill_blink, skill_parting_slash`。
- `tests/content/test_coverage.py`：允許清單清空。

## 6. 複雜度類 noqa

未新增（本階段只加內容與測試）。

## 7. 待 PM 決定

1. 數值為保守初值，只為通過預算 0.7–1.0。`skill_crippling_crit`、`skill_lucky_break` 為了讓低係數時機的預算合格，加了冷卻（3 與 4 回合）；`skill_lucky_break` 護盾僅 1d4，實際意義小，留給平衡階段。
2. `skill_raise_perch`、`skill_sinkhole` 為了達到預算下限，各附帶 1 回合的 `slow`（敵人）；純地形技能預算太低（約 25–46%）。
3. `skill_raise_perch` 是十字形狀，AI 目前會把它當攻擊技瞄準敵人（升高敵人腳下的格子），並不會替自己架高台；要讓 AI 真的「築台」需要 AI 評分調整，屬平衡／AI 階段。
4. 敵方單位沒有裝備新技能（只裝在我方 build），故敵方 AI 仍不用被動、反應、姿態；規格允許「分配到既有 build 或敵方單位」，這次選了前者。
5. `docs/PM交接.md` 仍寫「47 個手寫技能」，現為 59 個；依指示未修改該文件，請 PM 更新。
6. `skill_lucky_break`（自然 20）、`skill_twin_strike` 等被動為 `epic`，且被動限定 `category: spell`，所以「致命破綻」等戰士風格被動的 `scaling_attr` 只能以法術技形式存在；這是被動骨架的既有限制。

## 8. CLI 輸出節錄

```
$ trpg battle --map dark_forest --seed 7 --ally-build build_storm,build_ranged,build_assassin --log-json b.json
  雷電流英雄 施放「導電連擊」（AP 2，法力 6，冷卻 2 回合）→ 影響 1 格
  遠程英雄 施放「築高台」（AP 1，法力 4，冷卻 2 回合）→ 影響 5 格
  ★ 遠程英雄 的被動「天賜好運」觸發（擲出自然 20 時，深度 1），對象 盜賊2（法力 2，冷卻 4 回合）
重播驗證通過：56 個動作、205 個事件，最終狀態一致（dark_forest，種子 7）。
$ trpg battle --map bridge_chasm --seed 3 --ally-build build_push,build_support,build_trapper --log-json c.json
  ★ 陷阱流英雄 的被動「疾行」觸發（移動後，深度 1）（法力 2）
  ★ 輔助英雄 的被動「調息」觸發（回合結束時，深度 1）（法力 2）
  ⟳ 輔助英雄 反應：「反射護幕」
  ★ 位移流英雄 的被動「嗜血」觸發（擊倒時，深度 1），對象 盜賊2（法力 2）
重播驗證通過：119 個動作、424 個事件，最終狀態一致（bridge_chasm，種子 3）。
```
