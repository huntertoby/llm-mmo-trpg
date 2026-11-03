覆寫 `none`；受測 355 個技能或配方、每階 2 個種子。

逐變化套用 111830 次（合法 55799、結構不符 7726、重調失敗 48305）。**下面以「一次請求 × 一個模板」為一次**（同模板的各關鍵字、元素併成一次，有任一合法就算合法）：31532 次，合法 18026、結構不符 6746、**重調失敗 6760**。

### 大類 × 模板（重調失敗次數）

| 大類 | keyword_imbue | keyword_exploit | support_keyword | cost_charge | extend_duration | trigger_potency | trigger_cap | 合計 |
|---|---|---|---|---|---|---|---|---|
| 超過上限 | 703 | 239 | 32 | 9 | 613 | 0 | 141 | 1737 |
| 低於強度下限 | 13 | 27 | 0 | 11 | 0 | 0 | 0 | 51 |
| 階梯跳過窗 | 66 | 6 | 24 | 0 | 22 | 178 | 92 | 388 |
| 沒有可調旋鈕 | 22 | 0 | 4 | 524 | 2 | 177 | 2 | 731 |
| 骨架占比 | 171 | 317 | 0 | 109 | 76 | 0 | 0 | 673 |
| 調整後驗證不過 | 217 | 3 | 134 | 0 | 22 | 0 | 0 | 376 |
| 草稿 schema 不合法 | 598 | 2206 | 0 | 0 | 0 | 0 | 0 | 2804 |
| 合計 | 1790 | 2798 | 194 | 653 | 735 | 355 | 235 | 6760 |

### 細原因 × 模板（重調失敗次數）

| 原因 | keyword_imbue | keyword_exploit | support_keyword | cost_charge | extend_duration | trigger_potency | trigger_cap | 合計 |
|---|---|---|---|---|---|---|---|---|
| 階梯跳過窗 | 66 | 6 | 24 | 0 | 22 | 178 | 92 | 388 |
| 旋鈕到頂 | 13 | 27 | 0 | 10 | 0 | 0 | 0 | 50 |
| 占比限制擋住旋鈕 | 28 | 39 | 0 | 80 | 0 | 0 | 0 | 147 |
| 占比限制（違規未清） | 143 | 278 | 0 | 29 | 76 | 0 | 0 | 526 |
| 最弱仍超過上限 | 703 | 239 | 32 | 0 | 611 | 0 | 141 | 1726 |
| 沒有可調旋鈕 | 22 | 0 | 4 | 524 | 2 | 177 | 2 | 731 |
| 調整後分數低於下限 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| 調整後驗證不過（exclusion.no_damage_with_ally_heal） | 17 | 0 | 0 | 0 | 0 | 0 | 0 | 17 |
| 調整後驗證不過（exclusion.self_shape_no_enemy_effect） | 38 | 2 | 0 | 0 | 0 | 0 | 0 | 40 |
| 調整後驗證不過（reference） | 0 | 0 | 0 | 0 | 22 | 0 | 0 | 22 |
| 調整後驗證不過（scaling.range） | 39 | 0 | 6 | 0 | 0 | 0 | 0 | 45 |
| 調整後驗證不過（skeleton.secondary_count） | 110 | 1 | 128 | 0 | 0 | 0 | 0 | 239 |
| 調整後驗證不過（skeleton.secondary） | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| 調整後驗證不過（variant.frost_edge.budget.weak） | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| 調整後驗證不過（variant.ledge_drop.skeleton.secondary_count） | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| 調整後驗證不過（variant.tide_pierce.budget.over） | 0 | 0 | 0 | 9 | 2 | 0 | 0 | 11 |
| 草稿 schema 不合法（charge_through 以外的效果必須明寫 affects: self（只） | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 28 |
| 草稿 schema 不合法（copy_skill 必須是技能唯一的效果） | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 16 |
| 草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） | 0 | 1628 | 0 | 0 | 0 | 0 | 0 | 1628 |
| 草稿 schema 不合法（gamble 必須是技能的最後一個效果（一律最後結算）） | 28 | 28 | 0 | 0 | 0 | 0 | 0 | 56 |
| 草稿 schema 不合法（revive 以外的效果必須明寫 affects: self（只作用在施放者）） | 18 | 18 | 0 | 0 | 0 | 0 | 0 | 36 |
| 草稿 schema 不合法（rule_change 必須是技能唯一的效果） | 32 | 32 | 0 | 0 | 0 | 0 | 0 | 64 |
| 草稿 schema 不合法（summon 以外的效果必須明寫 affects: self（只作用在施放者）） | 334 | 334 | 0 | 0 | 0 | 0 | 0 | 668 |
| 草稿 schema 不合法（swap_any 必須是技能唯一的效果） | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 20 |
| 草稿 schema 不合法（teleport_target 必須是技能唯一的效果） | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 20 |
| 草稿 schema 不合法（zone 必須是技能唯一的效果） | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 32 |
| 草稿 schema 不合法（效果原語必須有 N 到 N 個，收到 N 個） | 39 | 39 | 0 | 0 | 0 | 0 | 0 | 78 |
| 草稿 schema 不合法（聚集段只能有一個拉扯原語（pull），收到 pull、create_surfac） | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| 草稿 schema 不合法（聚集段只能有一個拉扯原語（pull），收到 pull、damage） | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| 草稿 schema 不合法（複合技能兩段合計最多 N 個效果，收到 N 個） | 21 | 21 | 0 | 0 | 0 | 0 | 0 | 42 |
| 草稿 schema 不合法（複合技能的位移段只能有一個施放者自身位移原語（teleport、leap、das） | 48 | 48 | 0 | 0 | 0 | 0 | 0 | 96 |
| 合計 | 1790 | 2798 | 194 | 653 | 735 | 355 | 235 | 6760 |

### 原因 × 種類＃第幾次

| 原因 | active#1 | active#2 | passive#1 | passive#2 | reaction#1 | reaction#2 |
|---|---|---|---|---|---|---|
| 階梯跳過窗 | 8 | 98 | 22 | 215 | 0 | 45 |
| 旋鈕到頂 | 19 | 31 | 0 | 0 | 0 | 0 |
| 占比限制擋住旋鈕 | 56 | 91 | 0 | 0 | 0 | 0 |
| 占比限制（違規未清） | 96 | 430 | 0 | 0 | 0 | 0 |
| 最弱仍超過上限 | 210 | 1041 | 64 | 331 | 10 | 70 |
| 沒有可調旋鈕 | 280 | 270 | 44 | 103 | 6 | 28 |
| 調整後分數低於下限 | 0 | 1 | 0 | 0 | 0 | 0 |
| 調整後驗證不過（exclusion.no_damage_with_ally_heal） | 4 | 13 | 0 | 0 | 0 | 0 |
| 調整後驗證不過（exclusion.self_shape_no_enemy_effect） | 6 | 32 | 0 | 0 | 2 | 0 |
| 調整後驗證不過（reference） | 6 | 6 | 0 | 8 | 0 | 2 |
| 調整後驗證不過（scaling.range） | 10 | 33 | 0 | 2 | 0 | 0 |
| 調整後驗證不過（skeleton.secondary_count） | 23 | 216 | 0 | 0 | 0 | 0 |
| 調整後驗證不過（skeleton.secondary） | 0 | 10 | 0 | 0 | 0 | 0 |
| 調整後驗證不過（variant.frost_edge.budget.weak） | 0 | 1 | 0 | 0 | 0 | 0 |
| 調整後驗證不過（variant.ledge_drop.skeleton.secondary_count） | 0 | 2 | 0 | 0 | 0 | 0 |
| 調整後驗證不過（variant.tide_pierce.budget.over） | 3 | 8 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（charge_through 以外的效果必須明寫 affects: self（只） | 12 | 16 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（copy_skill 必須是技能唯一的效果） | 12 | 4 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） | 346 | 876 | 76 | 252 | 12 | 66 |
| 草稿 schema 不合法（gamble 必須是技能的最後一個效果（一律最後結算）） | 12 | 44 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（revive 以外的效果必須明寫 affects: self（只作用在施放者）） | 12 | 24 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（rule_change 必須是技能唯一的效果） | 48 | 16 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（summon 以外的效果必須明寫 affects: self（只作用在施放者）） | 204 | 464 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（swap_any 必須是技能唯一的效果） | 12 | 8 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（teleport_target 必須是技能唯一的效果） | 12 | 8 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（zone 必須是技能唯一的效果） | 20 | 12 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（效果原語必須有 N 到 N 個，收到 N 個） | 0 | 78 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（聚集段只能有一個拉扯原語（pull），收到 pull、create_surfac） | 0 | 4 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（聚集段只能有一個拉扯原語（pull），收到 pull、damage） | 4 | 12 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（複合技能兩段合計最多 N 個效果，收到 N 個） | 0 | 42 | 0 | 0 | 0 | 0 |
| 草稿 schema 不合法（複合技能的位移段只能有一個施放者自身位移原語（teleport、leap、das） | 20 | 76 | 0 | 0 | 0 | 0 |

### 階梯跳過窗：最小一格的比例增量與離下限的缺口

|  | 最小 | 中位 | 90% | 最大 |
|---|---|---|---|---|
| 一格增量 | 0.048 | 0.129 | 0.218 | 0.378 |
| 缺口 | 0.000 | 0.011 | 0.064 | 0.127 |

### 最常見的技能（前 12）

| 技能 | 次數 | 主要原因 |
|---|---|---|
| skill_rand_1 | 118 | 最弱仍超過上限 51、階梯跳過窗 22 |
| skill_fracture_mark | 104 | 最弱仍超過上限 48、草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 28 |
| skill_ember_brand | 102 | 最弱仍超過上限 54、草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 24 |
| skill_rand_3 | 97 | 草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 39、最弱仍超過上限 28 |
| skill_rand_2 | 94 | 最弱仍超過上限 46、草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 12 |
| skill_sanctified_ward | 90 | 調整後驗證不過（skeleton.secondary_count） 55、草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 30 |
| skill_holy_weapon | 84 | 最弱仍超過上限 36、草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 26 |
| skill_rand_6 | 81 | 最弱仍超過上限 46、沒有可調旋鈕 18 |
| skill_rand_4 | 79 | 草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 28、最弱仍超過上限 20 |
| skill_tailwind | 74 | 最弱仍超過上限 44、草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 26 |
| skill_qi_breath | 72 | 草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 24、調整後驗證不過（skeleton.secondary_count） 21 |
| skill_radiant_mend | 72 | 草稿 schema 不合法（effects[N]（damage）：法術技的傷害必須指定 dice 與 ele） 24、調整後驗證不過（skeleton.secondary_count） 17 |

### 骨架

| 骨架 | 重調失敗 | 結構合法的次數 | 失敗率 |
|---|---|---|---|
| control | 1497 | 2950 | 51% |
| aura | 1357 | 2582 | 53% |
| passive | 1117 | 2458 | 45% |
| summon | 774 | 970 | 80% |
| displace | 716 | 1664 | 43% |
| strike | 372 | 6483 | 6% |
| reaction | 241 | 1216 | 20% |
| consume_status | 221 | 320 | 69% |
| rune | 124 | 196 | 63% |
| area | 97 | 1958 | 5% |
| sacrifice | 96 | 120 | 80% |
| builder_finisher | 61 | 1305 | 5% |
| trap | 55 | 296 | 19% |
| combo | 32 | 2268 | 1% |

