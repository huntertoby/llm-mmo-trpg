嘗試 45 次，錯誤 48 條，類別 22 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `passive.affects` | 6 | Q12／1｜effects[0]｜effects[0]（raise_terrain）：trigger.target 為 self 時，效果的 affects 只能是 self，收到 tiles |
| 2 | `value_error｜變奏 X 的替換內容必須填 #～# 項（shap` | 6 | Q1／1｜variants[0]｜變奏 finisher 的替換內容必須填 1～2 項（shape、range_delta、element、add_effect、replace_effect），收到 3 項｜variants.0｜{"add_effect": {"per_stack_permille": 50, "stack": "combo_point", "type": "consu |
| 3 | `skeleton.secondary_count` | 5 | Q5／2｜｜骨架 rune：附帶效果最多 1 個，收到 2 個 |
| 4 | `value_error｜變奏「…」：主傷害（第 # 個效果）不能被換掉` | 5 | Q2／1｜variants[0].replace_effect.index｜變奏「怒火迸發」：主傷害（第 1 個效果）不能被換掉｜{"ap_cost": 2, "category": "spell", "cost": {"mana": 1}, "effects": [{"affects": |
| 5 | `budget.over` | 3 | Q12／1｜｜超出預算：total 8.95 ÷ 可用預算 7.00 ＝ 127.9%（上限 100.0%，階級 1） |
| 6 | `exclusion.terrain_needs_earth` | 3 | Q12／1｜｜互斥規則「地形、石膚、震波限大地」：隆起地形（raise_terrain）、下陷地形（lower_terrain）、震波（shockwave）與石膚（stoneskin）只有大地元素的技能能用（技能元素要是 earth）（形狀 self，冷卻 無，效果 raise_terrain、apply_status:commanding） |
| 7 | `budget.weak` | 2 | Q5／1｜｜過弱：total 9.38 ÷ 可用預算 14.07 ＝ 66.7%（下限 70.0%，階級 1）。引擎已把數值調到最高、AP 降到 1 仍不夠：請再加一個骨架允許的附帶效果（依技能主題選，例如對友方的 heal 或 shield、對敵方的施加狀態或 damage），或改用有數值的核心效果 |
| 8 | `reference｜稀有度 common 最多帶 # 個變奏，收到 ` | 2 | Q4／2｜variants｜稀有度 common 最多帶 0 個變奏，收到 1 個 |
| 9 | `skeleton.secondary_share` | 2 | Q16／2｜effects[1]｜骨架 control：damage 占 45.5%，超過上限 40.0%。引擎已把這個傷害（damage）降到最低值仍超過上限：請移除 effects[1] 的 damage，只保留骨架的核心效果（或改用允許 damage 當主軸的骨架） |
| 10 | `value_error｜法術技（category: spell）的 we` | 2 | Q4／1｜｜法術技（category: spell）的 weapon_req 只能是 focus、any，收到 ranged｜{"ap_cost": 2, "category": "spell", "cost": {"mana": 1}, "effects": [{"affects": |

其餘：`exclusion.stun_single_long_cooldown` 1、`keyword.required` 1、`reference｜層數 focus（owner: self）的co` 1、`reference｜層數 fury（owner: self）的con` 1、`reference｜層數 ki（owner: self）的consu` 1、`reference｜稀有度 rare 最多帶 # 個變奏，收到 # ` 1、`skeleton.core_share` 1、`value_error｜武器技（category: weapon）的 w` 1、`variant.detonate.budget.weak` 1、`variant.detonate.skeleton.core` 1、`variant.detonate.skeleton.secondary_count` 1、`variant.detonate.skeleton.secondary_share` 1
