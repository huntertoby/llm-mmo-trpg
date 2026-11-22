嘗試 31 次，錯誤 20 條，類別 10 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `exclusion.terrain_needs_earth` | 5 | Q8／1｜｜互斥規則「地形、石膚、震波限大地」：隆起地形（raise_terrain）、下陷地形（lower_terrain）、震波（shockwave）與石膚（stoneskin）只有大地元素的技能能用（技能元素要是 earth）（形狀 single（range 2），冷卻 3 回合，效果 raise_terrain、damage）。請在技能 JSON 的頂層填 element: "earth"（效果裡各自的 element 不算） |
| 2 | `value_error｜effects[#]（damage）：法術技的傷` | 4 | Q3／2｜effects[0]｜effects[0]（damage）：法術技的傷害必須指定 dice 與 element｜{"ap_cost": 2, "category": "spell", "cost": {"mana": 10}, "effects": [{"affects" |
| 3 | `keyword.required` | 2 | Q12／1｜effects｜技能必須製造或利用題目的關鍵字 high_ground，但提議沒有帶到。可用寫法（high_ground：raise_terrain、lower_terrain） |
| 4 | `skeleton.core` | 2 | Q3／1｜｜骨架 area：沒有核心效果（需要 damage） |
| 5 | `skeleton.secondary` | 2 | Q18／1｜effects[1]｜骨架 strike：effects[1]（add_stack）不在允許的附帶原語內（允許：apply_status、push、pull、knock_prone、dash、gamble、shadowstep、absorb_surface、contagion） |
| 6 | `budget.over` | 1 | Q12／2｜｜超出預算：total 8.45 ÷ 可用預算 7.00 ＝ 120.7%（上限 100.0%，階級 1）。被動的可用預算看觸發的係數：請換係數高的觸發（這個稀有度最高的是 every_n_hits（n: 3）），或換便宜的狀態 |
| 7 | `budget.weak` | 1 | Q3／1｜｜過弱：total 9.50 ÷ 可用預算 16.87 ＝ 56.3%（下限 70.0%，階級 1） |
| 8 | `cap.distance_condition` | 1 | Q14／1｜｜遠距條件要最大射程至少 5 格（目前：3），否則條件一定不成立 |
| 9 | `skeleton.core_share` | 1 | Q3／1｜｜骨架 area：核心效果（damage）占 0.0%，低於下限 50.0% |
| 10 | `skeleton.shape` | 1 | Q3／1｜｜骨架 area：形狀只能是 line、cone、cross、square3、ring、chain，收到 single |
