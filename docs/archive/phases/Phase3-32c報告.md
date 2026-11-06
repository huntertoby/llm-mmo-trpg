# Phase 3-32c 報告｜普攻流對照修正

> 規格：`docs/phases/Phase3計畫.md` 35.3。數值皆為初值，未經平衡。

## 1. 交付內容

1. **技能流對照組改成實際配置**（`content/sim/builds.yaml` 的 `build_skill_archer`，`reference: true`）：2 招範圍技（穿透射擊〔直線〕、震雷掌〔錐形〕）、1 招控制（捕獸夾，施加 root 2 回合）、1 招單體爆發（遠距狙擊，至多 +40%）；同屬性、同弓、普通長弓；沒有精通。主動欄 4 招。
2. **旋鈕：已套用**（重跑後普攻流在範圍戰與 Boss 戰仍高於技能流，依規格套用，見第 2 節）：普攻精通 80‰ → 60‰（`skill_attack_mastery.yaml`）、連擊／分裂 `strike_permille` 500 → 400（`affixes.yaml`，詞條文字 50% → 40%）。
3. **`affix_trait_longgun_still_crit` 改為「站定時傷害 +10%」**：id 保留不變，類別由 `weapon_trait` 改為 `conditional`（`effect: damage`、條件 `moved_this_turn` 取反，與 `affix_cond_still_defense` 同一機制，不需要改引擎），`weapons: [longgun]`、固定值 100‰（`value: {min: 100, max: 100}`），文字「長槍站定（本回合沒有移動）時傷害 +{n}」，計入全身 +50% 上限（走既有條件傷害）。長槍基礎值（`steady`）不動。
4. **連帶調整**：精通下修後預算「過弱」（54%，下限 70%），把 `content/skill_budget.yaml` 的 `modifier.empty_slots_permille` 由 500 調到 700（精通預算約 75%）；`skill_icons.json` 重產。

引擎、`LOG_FORMAT`、CLI 快照皆未動（只改內容資料與測試）。

## 2. 三情境前後對照（效用 AI，種子 0～39，每格 40 場）

`uv run python scripts/sim_attack_flow.py --seeds 40 --jobs 4`。「3-32a」欄為舊的 6 招對照組（20 場，取自 3-32a 報告）。格式：傷害/場、勝率、DPR。

| 情境 | build | 3-32a | 新對照組（旋鈕前） | 旋鈕後 |
|---|---|---|---|---|
| 長戰單體 | 普攻流 | 73 | 74、90%、19.6 | 74、85%、18.2 |
| 長戰單體 | 技能流 | 75 | 76、92%、13.4 | 76、92%、13.4 |
| 範圍戰 | 普攻流 | 47 | 51、97%、17.2 | 47、97%、16.2 |
| 範圍戰 | 技能流 | 39 | 40、100%、12.1 | 40、100%、12.1 |
| Boss 戰 | 普攻流 | 79 | 82、55%、14.5 | 73、45%、13.0 |
| Boss 戰 | 技能流 | 50 | 55、35%、9.5 | 55、35%、9.5 |

觀察：

- 換成實際配置後技能流傷害只小幅上升（範圍戰 39 → 40、Boss 戰 50 → 55），仍低於普攻流。旋鈕前普攻流範圍戰 51 vs 40、Boss 戰 82 vs 55，符合規格「仍偏高」的套用條件，所以套用旋鈕。
- 旋鈕後：長戰單體仍約等於技能流（74 vs 76）；範圍戰 47 vs 40、Boss 戰 73 vs 55，**普攻流傷害仍高於技能流**，但 Boss 戰勝率降到 45%（技能流 35%）。規格只允許套用一次旋鈕，沒有再往下調。
- 技能流弓手 DPR 偏低（Boss 戰 9.5）：技能多為 2 AP、有冷卻與法力限制；震雷掌用 int 縮放而英雄 int 只有 10；捕獸夾（root）是控制，不貢獻傷害，傷害欄位量不到控制價值。

## 3. 驗收證據

- pytest：`tests/engine/test_attack_flow.py` — `test_longgun_still_damage_applies_only_when_standing_still_and_counts_to_the_cap`（站定 1100、移動後 1000、與玻璃／低血傷害合計截斷在 1500、長槍基礎 `steady` 不變）、`test_traits_only_appear_on_their_own_weapon`（新詞條只能掛長槍）、`test_reference_builds_are_valid_and_kept_out_of_the_matrix`（對照組：直線＋錐形範圍、root 控制、狙擊、無精通、弓手可用）、精通（60‰：1180／1120／1060／1000）、combo／cleave（倍率 400）、`test_mastery_passive_is_valid_and_within_budget`。
- `tests/content`、`tests/skillgen`、`tests/sim`、`tests/narrative`、`tests/api/test_gear_api.py` 全過；`ruff check`、`ruff format --check`、`mypy` 全過。

## 4. 待 PM 決定

1. **普攻流範圍戰／Boss 戰傷害旋鈕後仍高於技能流**（47 vs 40、73 vs 55）。候選：精通再降到 40～50‰、combo／cleave 降到 300‰，或接受以勝率與存活為準。建議 PM 背景跑 200 場以上確認；技能流的控制價值也沒有被量到。
2. **捕獸夾是 tier 2**：弓手能用的 tier 1 控制技只有需 focus 武器的 `frost_shackle`，所以對照組用 tier 2 的 `skill_bear_trap`。震雷掌（法術、int 縮放）用在 dex 弓手身上偏弱。
3. **長槍詞條 id 保留** `affix_trait_longgun_still_crit`，但類別已是 `conditional`、文字不含「暴擊」；若要改名需同步改測試與物品資料，我沒動。
4. **精通預算旋鈕** `empty_slots_permille` 500 → 700 是為了讓精通過預算下限；之後若再降精通，需一併調整或放寬。
