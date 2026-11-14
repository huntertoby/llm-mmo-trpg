嘗試 45 次，錯誤 44 條，類別 16 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `skeleton.secondary_count` | 7 | Q3／1｜｜骨架 strike：附帶效果最多 1 個，收到 2 個 |
| 2 | `exclusion.terrain_needs_earth` | 6 | Q8／1｜｜互斥規則「地形、石膚、震波限大地」：隆起地形（raise_terrain）、下陷地形（lower_terrain）、震波（shockwave）與石膚（stoneskin）只有大地元素的技能能用（技能元素要是 earth）（形狀 single（range 3），冷卻 無，效果 raise_terrain、damage） |
| 3 | `passive.affects` | 6 | Q12／1｜effects[0]｜effects[0]（raise_terrain）：trigger.target 為 self 時，效果的 affects 只能是 self，收到 tiles |
| 4 | `value_error｜變奏 X 的替換內容必須填 #～# 項（shap` | 5 | Q1／1｜variants[0]｜變奏 finisher 的替換內容必須填 1～2 項（shape、range_delta、element、add_effect、replace_effect），收到 3 項｜variants.0｜{"add_effect": {"per_stack_permille": 50, "stack": "combo_point", "type": "consu |
| 5 | `budget.over` | 3 | Q12／1｜｜超出預算：total 8.50 ÷ 可用預算 4.20 ＝ 202.4%（上限 100.0%，階級 1） |
| 6 | `value_error｜法術技（category: spell）的 we` | 3 | Q2／1｜｜法術技（category: spell）的 weapon_req 只能是 focus、any，收到 melee｜{"ap_cost": 2, "category": "spell", "cost": {"mana": 1, "on_miss": [{"dice": "1d |
| 7 | `value_error｜變奏「…」：主傷害（第 # 個效果）不能被換掉` | 3 | Q13／3｜variants[0].replace_effect.index｜變奏「帶電」：主傷害（第 0 個效果）不能被換掉｜{"ap_cost": 2, "category": "weapon", "cost": {"stamina": 1}, "effects": [{"eleme |
| 8 | `budget.weak` | 2 | Q10／1｜｜過弱：total 9.38 ÷ 可用預算 14.07 ＝ 66.7%（下限 70.0%，階級 1）。引擎已把數值調到最高、AP 降到 1 仍不夠：請再加一個骨架允許的附帶效果（依技能主題選，例如對友方的 heal 或 shield、對敵方的施加狀態或 damage），或改用有數值的核心效果 |
| 9 | `value_error｜武器技（category: weapon）的 w` | 2 | Q18／1｜｜武器技（category: weapon）的 weapon_req 只能是 melee、ranged，收到 any｜{"ap_cost": 2, "category": "weapon", "condition": {"count": 1, "stack": "combo_p |
| 10 | `reference｜層數 combo_point 只有符合條件的技能` | 1 | Q18／3｜variants[0].replace_effect.effect.stack｜層數 combo_point 只有符合條件的技能可以消耗（見層數說明） |

其餘：`reference｜層數 combo_point（owner: se` 1、`reference｜層數 ki（owner: self）的consu` 1、`reference｜稀有度 common 最多帶 # 個變奏，收到 ` 1、`reference｜稀有度 rare 最多帶 # 個變奏，收到 # ` 1、`skeleton.secondary_share` 1、`variant.detonate.budget.weak` 1
