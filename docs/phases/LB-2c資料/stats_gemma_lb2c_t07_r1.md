嘗試 29 次，錯誤 19 條，類別 13 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `skeleton.secondary_count` | 3 | Q9／1｜｜骨架 builder_finisher：附帶效果最多 2 個，收到 3 個。請刪掉多出的附帶效果（核心效果以外的都算），或改用附帶效果上限較高的骨架 |
| 2 | `budget.weak` | 2 | Q14／1｜｜過弱：total 6.87 ÷ 可用預算 14.07 ＝ 48.8%（下限 70.0%，階級 1） |
| 3 | `keyword.required` | 2 | Q4／2｜effects｜技能必須製造或利用題目的關鍵字 summon，但提議沒有帶到。可用寫法（summon：apply_status（status＝commanding）） |
| 4 | `skeleton.core` | 2 | Q14／1｜｜骨架 combo：沒有核心效果（需要 damage） |
| 5 | `skeleton.core_share` | 2 | Q14／1｜｜骨架 combo：核心效果（damage）占 0.0%，低於下限 50.0% |
| 6 | `budget.over` | 1 | Q12／3｜｜超出預算：total 10.00 ÷ 可用預算 7.00 ＝ 142.9%（上限 100.0%，階級 1）。被動的可用預算看觸發的係數：請換係數高的觸發（這個稀有度最高的是 every_n_hits（n: 3）），或換便宜的狀態 |
| 7 | `exclusion.terrain_needs_earth` | 1 | Q12／3｜｜互斥規則「地形、石膚、震波限大地」：隆起地形（raise_terrain）、下陷地形（lower_terrain）、震波（shockwave）與石膚（stoneskin）只有大地元素的技能能用（技能元素要是 earth）（形狀 self，冷卻 無，效果 raise_terrain、apply_status:commanding）。請在技能 JSON 的頂層填 element: "earth"（效果裡各自的 element 不算） |
| 8 | `passive.affects` | 1 | Q12／1｜effects[0]｜effects[0]（apply_status）：trigger.target 為 self 時，效果的 affects 只能是 self，收到 allies。請在這個效果明寫 "affects": "self"（沒寫時預設是 enemies 或 allies） |
| 9 | `reference｜層數 soul_shard 只有符合條件的技能可` | 1 | Q9／2｜effects[1].stack｜層數 soul_shard 只有符合條件的技能可以消耗（見層數說明） |
| 10 | `reference｜消耗層數 soul_shard 的技能至少要有傷` | 1 | Q9／2｜effects[1].stack｜消耗層數 soul_shard 的技能至少要有傷害其中一種效果 |

其餘：`skeleton.core_beneficial` 1、`skeleton.forbidden_affects` 1、`skeleton.secondary_share` 1
