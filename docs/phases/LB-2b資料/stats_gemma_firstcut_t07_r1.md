嘗試 50 次，錯誤 54 條，類別 14 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `value_error｜變奏「…」：range_delta 只能用在射程` | 26 | Q2／1｜variants[0].range_delta｜變奏「怒火衝擊」：range_delta 只能用在射程是數字的形狀，收到 line 的射程 None｜{"ap_cost": 2, "category": "weapon", "cost": {"stamina": 1}, "effects": [{"affec |
| 2 | `passive.affects` | 6 | Q12／1｜effects[0]｜effects[0]（apply_status）：trigger.target 為 self 時，效果的 affects 只能是 self，收到 enemies |
| 3 | `variant.v1.budget.weak` | 5 | Q3／1｜variants[0]｜影印：過弱：total 7.05 ÷ 可用預算 14.07 ＝ 50.1%（下限 70.0%，階級 1） |
| 4 | `skeleton.secondary_share` | 3 | Q16／1｜effects[1]｜骨架 control：damage 占 45.5%，超過上限 40.0%。引擎已把這個傷害（damage）降到最低值仍超過上限：請移除 effects[1] 的 damage，只保留骨架的核心效果（或改用允許 damage 當主軸的骨架） |
| 5 | `variant.v1.budget.over` | 3 | Q5／1｜variants[0]｜餘燼爆裂：超出預算：total 15.21 ÷ 可用預算 14.07 ＝ 108.1%（上限 100.0%，階級 1） |
| 6 | `keyword.required` | 2 | Q4／2｜effects｜技能必須製造或利用題目的關鍵字 summon，但提議沒有帶到。可用寫法（summon：apply_status（status＝commanding）） |
| 7 | `variant.v1.skeleton.secondary_count` | 2 | Q3／2｜variants[0]｜影印：骨架 displace：附帶效果最多 2 個，收到 3 個 |
| 8 | `budget.over` | 1 | Q12／1｜｜超出預算：total 8.05 ÷ 可用預算 7.00 ＝ 115.0%（上限 100.0%，階級 1） |
| 9 | `budget.weak` | 1 | Q3／1｜｜過弱：total 5.79 ÷ 可用預算 14.07 ＝ 41.2%（下限 70.0%，階級 1） |
| 10 | `passive.category` | 1 | Q12／1｜｜骨架 passive 要求 category: spell、weapon_req: any（收到 spell、focus） |

其餘：`shield.status` 1、`skeleton.forbidden_affects` 1、`skeleton.secondary_count` 1、`variant.v1.skeleton.secondary_share` 1
