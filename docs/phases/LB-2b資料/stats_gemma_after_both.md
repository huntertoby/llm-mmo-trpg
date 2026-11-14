嘗試 83 次，錯誤 96 條，類別 32 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `variant.v1.skeleton.secondary_count` | 11 | Q2／2｜variants[0]｜怒火迸發：骨架 builder_finisher：附帶效果最多 2 個，收到 3 個 |
| 2 | `value_error｜變奏「…」：range_delta 只能用在射程` | 9 | Q2／1｜variants[0].range_delta｜變奏「怒火迸發」：range_delta 只能用在射程是數字的形狀，收到 cone 的射程 None。請拿掉這個變奏的 range_delta（改用 shape、element 或 add_effect），或把技能形狀改成有數字射程的形狀（例：single 並填數字 range）｜{"ap_cost": 2, "category": "weapon", "condition": {"count": 1, "stack": "fury",  |
| 3 | `budget.over` | 6 | Q12／1｜｜超出預算：total 5.50 ÷ 可用預算 4.20 ＝ 131.0%（上限 100.0%，階級 1） |
| 4 | `keyword.required` | 6 | Q4／1｜effects｜技能必須製造或利用題目的關鍵字 summon，但提議沒有帶到。可用寫法（summon：apply_status（status＝commanding）） |
| 5 | `variant.v1.skeleton.secondary_share` | 6 | Q3／1｜variants[0]｜殘響：骨架 displace：damage 占 50.7%，超過上限 50.0% |
| 6 | `skeleton.secondary_count` | 5 | Q2／2｜｜骨架 builder_finisher：附帶效果最多 2 個，收到 3 個。請刪掉多出的附帶效果（核心效果以外的都算），或改用附帶效果上限較高的骨架 |
| 7 | `variant.v1.budget.weak` | 5 | Q3／1｜variants[0]｜殘響：過弱：total 6.21 ÷ 可用預算 14.03 ＝ 44.3%（下限 70.0%，階級 1） |
| 8 | `reference｜single 的 range 必須在 #–#，收` | 4 | Q15／1｜shape.range｜single 的 range 必須在 1–10，收到 0 |
| 9 | `reference｜層數 combo_point 只有符合條件的技能` | 4 | Q9／2｜effects[2].stack｜層數 combo_point 只有符合條件的技能可以消耗（見層數說明） |
| 10 | `variant.v1.skeleton.core` | 4 | Q17／1｜variants[0]｜靈光迸發：骨架 aura：沒有核心效果（需要 heal、shield、cleanse、apply_status、create_surface、grant_ap、reset_cooldown、cheat_death、redirect_damage、copy_skill、extra_reaction、restore_resource、zone、rule_change、revive、grant_skill） |

其餘：`skeleton.secondary_share` 3、`value_error｜變奏「…」：主傷害（第 # 個效果）不能被換掉。` 3、`variant.v1.budget.over` 3、`budget.weak` 2、`passive.category` 2、`value_error｜變奏「…」：效果原語必須有 # 到 # 個，收到` 2、`variant.detonation.skeleton.core` 2、`variant.detonation.skeleton.secondary_count` 2、`variant.detonation.skeleton.secondary_share` 2、`variant.fury_burst.budget.over` 2、`variant.v1.skeleton.forbidden_affects` 2、`passive.affects` 1、`shield.status` 1、`tier.terrain_area` 1、`variant.detonate_variant.budget.weak` 1、`variant.detonate_variant.skeleton.core` 1、`variant.detonate_variant.skeleton.secondary_count` 1、`variant.detonate_variant.skeleton.secondary_share` 1、`variant.detonation.budget.weak` 1、`variant.v1.exclusion.no_damage_with_ally_heal` 1、`variant.v1.skeleton.shape` 1、`variant.v1.tier.element` 1
