嘗試 40 次，錯誤 38 條，類別 19 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `budget.over` | 3 | Q12／1｜｜超出預算：total 5.50 ÷ 可用預算 4.20 ＝ 131.0%（上限 100.0%，階級 1） |
| 2 | `keyword.required` | 3 | Q4／1｜effects｜技能必須製造或利用題目的關鍵字 summon，但提議沒有帶到。可用寫法（summon：apply_status（status＝commanding）） |
| 3 | `skeleton.secondary_count` | 3 | Q2／2｜｜骨架 builder_finisher：附帶效果最多 2 個，收到 3 個。請刪掉多出的附帶效果（核心效果以外的都算），或改用附帶效果上限較高的骨架 |
| 4 | `skeleton.secondary_share` | 3 | Q3／1｜effects[1]｜骨架 displace：damage 占 50.7%，超過上限 50.0%。引擎已把這個傷害（damage）降到最低值仍超過上限：請移除 effects[1] 的 damage，只保留骨架的核心效果（或改用允許 damage 當主軸的骨架） |
| 5 | `value_error｜變奏「…」：range_delta 只能用在射程` | 3 | Q2／1｜variants[0].range_delta｜變奏「怒火迸發」：range_delta 只能用在射程是數字的形狀，收到 cone 的射程 None。請拿掉這個變奏的 range_delta（改用 shape、element 或 add_effect），或把技能形狀改成有數字射程的形狀（例：single 並填數字 range）｜{"ap_cost": 2, "category": "weapon", "condition": {"count": 1, "stack": "fury",  |
| 6 | `variant.v1.skeleton.secondary_count` | 3 | Q2／2｜variants[0]｜怒火迸發：骨架 builder_finisher：附帶效果最多 2 個，收到 3 個 |
| 7 | `budget.weak` | 2 | Q3／1｜｜過弱：total 6.45 ÷ 可用預算 14.03 ＝ 46.0%（下限 70.0%，階級 1） |
| 8 | `reference｜single 的 range 必須在 #–#，收` | 2 | Q15／1｜shape.range｜single 的 range 必須在 1–10，收到 0 |
| 9 | `value_error｜變奏「…」：效果原語必須有 # 到 # 個，收到` | 2 | Q9／2｜variants[0]｜變奏「幽影裂隙」：效果原語必須有 1 到 4 個，收到 5 個｜{"ap_cost": 2, "category": "spell", "cost": {"mana": 1}, "effects": [{"affects": |
| 10 | `variant.detonation.skeleton.core` | 2 | Q5／1｜variants[0]｜地脈震盪：骨架 rune：沒有核心效果（需要 inscribe、detonate_runes） |

其餘：`variant.detonation.skeleton.secondary_count` 2、`variant.detonation.skeleton.secondary_share` 2、`variant.v1.skeleton.secondary_share` 2、`passive.category` 1、`tier.terrain_area` 1、`value_error｜變奏「…」：主傷害（第 # 個效果）不能被換掉。` 1、`variant.detonation.budget.weak` 1、`variant.v1.budget.over` 1、`variant.v1.budget.weak` 1
