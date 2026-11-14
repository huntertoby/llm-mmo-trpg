嘗試 43 次，錯誤 58 條，類別 24 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `variant.v1.skeleton.secondary_count` | 8 | Q10／2｜variants[0]｜地脈共振：骨架 rune：附帶效果最多 1 個，收到 2 個 |
| 2 | `value_error｜變奏「…」：range_delta 只能用在射程` | 6 | Q2／1｜variants[0].range_delta｜變奏「怒火迸發」：range_delta 只能用在射程是數字的形狀，收到 line 的射程 None。請拿掉這個變奏的 range_delta（改用 shape、element 或 add_effect），或把技能形狀改成有數字射程的形狀（例：single 並填數字 range）｜{"ap_cost": 2, "category": "weapon", "cost": {"stamina": 1}, "effects": [{"affec |
| 3 | `reference｜層數 combo_point 只有符合條件的技能` | 4 | Q9／2｜effects[2].stack｜層數 combo_point 只有符合條件的技能可以消耗（見層數說明） |
| 4 | `variant.v1.budget.weak` | 4 | Q6／2｜variants[0]｜熾焰餘燼：過弱：total 6.50 ÷ 可用預算 14.07 ＝ 46.2%（下限 70.0%，階級 1） |
| 5 | `variant.v1.skeleton.core` | 4 | Q17／1｜variants[0]｜靈光迸發：骨架 aura：沒有核心效果（需要 heal、shield、cleanse、apply_status、create_surface、grant_ap、reset_cooldown、cheat_death、redirect_damage、copy_skill、extra_reaction、restore_resource、zone、rule_change、revive、grant_skill） |
| 6 | `variant.v1.skeleton.secondary_share` | 4 | Q10／2｜variants[0]｜地脈共振：骨架 rune：damage 占 54.3%，超過上限 40.0% |
| 7 | `budget.over` | 3 | Q12／1｜｜超出預算：total 8.50 ÷ 可用預算 4.20 ＝ 202.4%（上限 100.0%，階級 1） |
| 8 | `keyword.required` | 3 | Q4／1｜effects｜技能必須製造或利用題目的關鍵字 summon，但提議沒有帶到。可用寫法（summon：apply_status（status＝commanding）） |
| 9 | `reference｜single 的 range 必須在 #–#，收` | 2 | Q3／1｜shape.range｜single 的 range 必須在 1–10，收到 0 |
| 10 | `skeleton.secondary_count` | 2 | Q15／1｜｜骨架 strike：附帶效果最多 1 個，收到 2 個。請刪掉多出的附帶效果（核心效果以外的都算），或改用附帶效果上限較高的骨架 |

其餘：`value_error｜變奏「…」：主傷害（第 # 個效果）不能被換掉。` 2、`variant.fury_burst.budget.over` 2、`variant.v1.budget.over` 2、`variant.v1.skeleton.forbidden_affects` 2、`passive.affects` 1、`passive.category` 1、`shield.status` 1、`variant.detonate_variant.budget.weak` 1、`variant.detonate_variant.skeleton.core` 1、`variant.detonate_variant.skeleton.secondary_count` 1、`variant.detonate_variant.skeleton.secondary_share` 1、`variant.v1.exclusion.no_damage_with_ally_heal` 1、`variant.v1.skeleton.shape` 1、`variant.v1.tier.element` 1
