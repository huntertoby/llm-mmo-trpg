嘗試 33 次，錯誤 18 條，類別 7 種

| 名次 | 類別 | 次數 | 例子（第幾題／第幾次：路徑｜訊息｜pydantic 位置｜輸入） |
|---|---|---|---|
| 1 | `keyword.required` | 5 | Q2／2｜effects｜技能必須製造或利用題目的關鍵字 fury，但提議沒有帶到。可用寫法（fury：add_stack（stack＝fury）、consume_stack（stack＝fury）） |
| 2 | `skeleton.secondary` | 5 | Q1／1｜effects[1]｜骨架 strike：effects[1]（add_stack）不在允許的附帶原語內（允許：apply_status、push、pull、knock_prone、dash、gamble、shadowstep） |
| 3 | `exclusion.terrain_needs_earth` | 4 | Q4／1｜｜互斥規則「地形、石膚、震波限大地」：隆起地形（raise_terrain）、下陷地形（lower_terrain）、震波（shockwave）與石膚（stoneskin）只有大地元素的技能能用（技能元素要是 earth）（形狀 single（range 2），冷卻 無，效果 apply_status:stoneskin）。請在技能 JSON 的頂層填 element: "earth"（效果裡各自的 element 不算） |
| 4 | `passive.category` | 1 | Q12／2｜｜骨架 passive 要求 category: spell、weapon_req: any（收到 spell、focus） |
| 5 | `reference｜消耗層數 focus 的技能至少要有傷害其中一種` | 1 | Q17／1｜effects[0].stack｜消耗層數 focus 的技能至少要有傷害其中一種效果 |
| 6 | `skeleton.required_primitive` | 1 | Q9／1｜｜骨架 builder_finisher：效果至少要有 add_stack、consume_stack 其中之一 |
| 7 | `value_error｜被動技能（kind: passive）必須有 t` | 1 | Q12／1｜｜被動技能（kind: passive）必須有 trigger｜{"category": "spell", "condition": {"type": "height_advantage"}, "effects": [{"a |
