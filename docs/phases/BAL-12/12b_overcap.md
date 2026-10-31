## 1. 完整技能 +150‰ 上限下仍超過（B-3W-5）

內建技能 301 招；超過 +150‰ 的 **50** 招。
「超過的那一步」＝不限上限重爬時第一個讓分數超過上限的步子；「只走上限內」＝只走不超過
上限的步子時停在哪（即「+120‰ 以下最接近的一階」）。

### 原因（依超過那一步的旋鈕）

| 超過那一步的旋鈕 | 說明 | 招數 | 現狀 ‰ | 技能（前 8） |
|---|---|---|---|---|
| dice | 骰子一階就超過 | 21 | 151～300 | form_renewal、twin_strike、bloodlust、counterspell、ember_ward、holy_water、mark_detonation、reflex_ward… |
| duration | 持續回合 +1（整數，一格比例大） | 14 | 200～500 | dread_gaze、fleet_foot、ember_brand、fracture_mark、poison_mist、thorn_wall、vault_leap、vanish… |
| multiplier_permille | 武器倍率一階就超過 | 6 | 160～222 | riposte、rending_strike、ambush_stab、parting_slash、covering_fire、overdraft_strike |
| 修正 damage_permille | 修正幅度階梯 25‰（小幅度時一格比例大） | 5 | 166～500 | attack_mastery、searing_scar、war_avatar、rune_resonance、rune_sight |
| 減代價 cooldown |  | 4 | 152～170 | grief_rage、gale_kick、grapple_arrow、decoy_swap |

技能種類：active 28、modifier 5、passive 10、reaction 7。

自我檢查：現狀摘要與行為快照完整技能 301 筆不一致 0 筆。

### 覆寫結果

| 覆寫 | 說明 | > 150 | 最大 ‰ | < 120 | 120–150 | 151–200 | > 200 | 快照變 |
|---|---|---|---|---|---|---|---|---|
| `none` | 現狀 | 50 | 500 | 90 | 161 | 24 | 26 | 0 |
| `mod10` | 修正幅度每 10‰（只在完整技能） | 48 | 500 | 90 | 163 | 25 | 23 | 5 |
| `mod5` | 修正幅度每 5‰（只在完整技能） | 46 | 500 | 90 | 165 | 23 | 23 | 5 |
| `stop170` | 超過 +170‰ 就停在 +120‰ 以下 | 13 | 170 | 127 | 161 | 13 | 0 | 37 |
| `stop200` | 超過 +200‰ 就停在 +120‰ 以下 | 24 | 200 | 116 | 161 | 24 | 0 | 26 |
| `stop250` | 超過 +250‰ 就停在 +120‰ 以下 | 33 | 250 | 107 | 161 | 24 | 9 | 17 |
| `mod5_stop170` | 修正每 5‰＋超過 +170‰ 停 | 11 | 170 | 125 | 165 | 11 | 0 | 39 |
| `mod5_stop200` | 修正每 5‰＋超過 +200‰ 停 | 23 | 200 | 113 | 165 | 23 | 0 | 28 |

「快照變」＝行為快照完整技能那一組會變的筆數（升階重配、閃現出題不經過這裡，不變）。

### 每招前後（‰）

| 技能 | 種類 | 超過那一步 | 只走上限內 | `none` | `mod10` | `mod5` | `stop170` | `stop200` | `stop250` | `mod5_stop170` | `mod5_stop200` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| attack_mastery | modifier | 修正 damage_permille 50 → 75 | 0 | 500 | 200 | 200 | 0 | 0 | 0 | 100 | 200 |
| dread_gaze | active | duration 2 → 3 | 9 | 500 | 500 | 500 | 9 | 9 | 9 | 9 | 9 |
| fleet_foot | passive | duration 2 → 3 | 4 | 500 | 500 | 500 | 4 | 4 | 4 | 4 | 4 |
| ember_brand | passive | duration 3 → 4 | 4 | 333 | 333 | 333 | 4 | 4 | 4 | 4 | 4 |
| fracture_mark | passive | duration 3 → 4 | 4 | 333 | 333 | 333 | 4 | 4 | 4 | 4 | 4 |
| poison_mist | active | duration 3 → 4 | 61 | 333 | 333 | 333 | 61 | 61 | 61 | 61 | 61 |
| form_renewal | active | dice 1d10 → 1d12 | 119 | 300 | 300 | 300 | 119 | 119 | 119 | 119 | 119 |
| twin_strike | passive | dice 1d10 → 1d12 | 105 | 300 | 300 | 300 | 105 | 105 | 105 | 105 | 105 |
| bloodlust | passive | dice 1d6 → 1d8 | 4 | 285 | 285 | 285 | 4 | 4 | 4 | 4 | 4 |
| counterspell | reaction | dice 3d4 → 2d8 | 86 | 285 | 285 | 285 | 86 | 86 | 86 | 86 | 86 |
| ember_ward | passive | dice 1d6 → 1d8 | 4 | 285 | 285 | 285 | 4 | 4 | 4 | 4 | 4 |
| holy_water | active | dice 1d4 → 1d6 | 23 | 285 | 285 | 285 | 23 | 23 | 23 | 23 | 23 |
| mark_detonation | passive | dice 3d4 → 2d8 | 76 | 285 | 285 | 285 | 76 | 76 | 76 | 76 | 76 |
| reflex_ward | reaction | dice 3d4 → 2d8 | 81 | 285 | 285 | 285 | 81 | 81 | 81 | 81 | 81 |
| thorn_wall | active | duration 2 → 3 | 56 | 285 | 285 | 285 | 56 | 56 | 56 | 56 | 56 |
| vault_leap | active | duration 2 → 3 | 107 | 285 | 285 | 285 | 107 | 107 | 107 | 107 | 107 |
| wind_blade | active | dice 3d4 → 2d8 | 91 | 285 | 285 | 285 | 91 | 91 | 91 | 91 | 91 |
| searing_scar | modifier | 修正 damage_permille 100 → 125 | 0 | 250 | 200 | 150 | 0 | 0 | 250 | 150 | 150 |
| vanish | active | duration 4 → 5 | 59 | 250 | 250 | 250 | 59 | 59 | 250 | 59 | 59 |
| war_avatar | modifier | 修正 damage_permille 200 → 225 | 111 | 250 | 166 | 138 | 111 | 111 | 250 | 138 | 138 |
| creeping_blight | passive | dice 2d4 → 1d10 | 116 | 222 | 222 | 222 | 116 | 116 | 222 | 116 | 116 |
| riposte | reaction | multiplier_permille 1000 → 1100 | 111 | 222 | 222 | 222 | 111 | 111 | 222 | 111 | 111 |
| seething_rage | passive | dice 1d4 → 1d6 | 0 | 222 | 222 | 222 | 0 | 0 | 222 | 0 | 0 |
| blink | active | duration 2 → 3 | 113 | 214 | 214 | 214 | 113 | 113 | 214 | 113 | 113 |
| ice_wall | active | duration 3 → 4 | 61 | 208 | 208 | 208 | 61 | 61 | 208 | 61 | 61 |
| rending_strike | active | multiplier_permille 800 → 900 | 119 | 202 | 202 | 202 | 119 | 119 | 202 | 119 | 119 |
| ambush_stab | reaction | multiplier_permille 1100 → 1200 | 100 | 200 | 200 | 200 | 100 | 200 | 200 | 100 | 200 |
| ember_trail | active | duration 3 → 4 | 61 | 200 | 200 | 200 | 61 | 200 | 200 | 61 | 200 |
| holy_ground | active | duration 5 → 6 | 61 | 200 | 200 | 200 | 61 | 200 | 200 | 61 | 200 |
| parting_slash | reaction | multiplier_permille 1100 → 1200 | 100 | 200 | 200 | 200 | 100 | 200 | 200 | 100 | 200 |
| smoke_arrow | active | duration 5 → 6 | 112 | 200 | 200 | 200 | 112 | 200 | 200 | 112 | 200 |
| smoke_bomb | active | duration 5 → 6 | 112 | 200 | 200 | 200 | 112 | 200 | 200 | 112 | 200 |
| covering_fire | reaction | multiplier_permille 900 → 1000 | 98 | 197 | 197 | 197 | 98 | 197 | 197 | 98 | 197 |
| cluster_bolt | active | dice 2d10 → 5d4 | 117 | 190 | 190 | 190 | 117 | 190 | 190 | 117 | 190 |
| form_release_burst | active | dice 2d10 → 5d4 | 78 | 190 | 190 | 190 | 78 | 190 | 190 | 78 | 190 |
| second_wind | passive | dice 2d10 → 5d4 | 52 | 190 | 190 | 190 | 52 | 190 | 190 | 52 | 190 |
| life_drain | active | dice 1d10 → 1d12 | 71 | 181 | 181 | 181 | 71 | 181 | 181 | 71 | 181 |
| grief_rage | reaction | 減代價 cooldown 2 → 1 | 117 | 170 | 170 | 170 | 170 | 170 | 170 | 170 | 170 |
| fire_bolt | active | dice 2d4 → 1d10 | 110 | 166 | 166 | 166 | 166 | 166 | 166 | 166 | 166 |
| rune_resonance | modifier | 修正 damage_permille 150 → 175 | 0 | 166 | 133 | 133 | 166 | 166 | 166 | 133 | 133 |
| rune_sight | modifier | 修正 damage_permille 150 → 175 | 0 | 166 | 133 | 133 | 166 | 166 | 166 | 133 | 133 |
| overdraft_strike | active | multiplier_permille 3000 → 3250 | 82 | 160 | 160 | 160 | 160 | 160 | 160 | 160 | 160 |
| gale_kick | active | 減代價 cooldown 2 → 1 | 115 | 154 | 154 | 154 | 154 | 154 | 154 | 154 | 154 |
| grapple_arrow | active | 減代價 cooldown 2 → 1 | 115 | 154 | 154 | 154 | 154 | 154 | 154 | 154 | 154 |
| hex_bolt | active | dice 2d4 → 1d10 | 87 | 153 | 153 | 153 | 153 | 153 | 153 | 153 | 153 |
| radiant_mend | active | dice 2d4 → 1d10 | 98 | 153 | 153 | 153 | 153 | 153 | 153 | 153 | 153 |
| rime_touch | active | dice 2d4 → 1d10 | 87 | 153 | 153 | 153 | 153 | 153 | 153 | 153 | 153 |
| stoneskin_ward | active | dice 1d6 → 1d8 | 61 | 153 | 153 | 153 | 153 | 153 | 153 | 153 | 153 |
| decoy_swap | active | 減代價 cooldown 3 → 2 | 115 | 152 | 152 | 152 | 152 | 152 | 152 | 152 | 152 |
| soul_reap | active | dice 2d4 → 1d10 | 86 | 151 | 151 | 151 | 151 | 151 | 151 | 151 | 151 |

