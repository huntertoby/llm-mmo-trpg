## 1. 完整技能 +150‰ 上限下仍超過（B-3W-5）

內建技能 301 招；超過 +150‰ 的 **23** 招。
「超過的那一步」＝不限上限重爬時第一個讓分數超過上限的步子；「只走上限內」＝只走不超過
上限的步子時停在哪（即「+120‰ 以下最接近的一階」）。

### 原因（依超過那一步的旋鈕）

| 超過那一步的旋鈕 | 說明 | 招數 | 現狀 ‰ | 技能（前 8） |
|---|---|---|---|---|
| dice | 骰子一階就超過 | 10 | 151～190 | cluster_bolt、form_release_burst、second_wind、life_drain、fire_bolt、hex_bolt、radiant_mend、rime_touch… |
| duration | 持續回合 +1（整數，一格比例大） | 4 | 200～200 | ember_trail、holy_ground、smoke_arrow、smoke_bomb |
| multiplier_permille | 武器倍率一階就超過 | 4 | 160～200 | ambush_stab、parting_slash、covering_fire、overdraft_strike |
| 減代價 cooldown |  | 4 | 152～170 | grief_rage、gale_kick、grapple_arrow、decoy_swap |
| 修正 damage_permille | 修正幅度階梯 25‰（小幅度時一格比例大） | 1 | 200～200 | attack_mastery |

技能種類：active 17、modifier 1、passive 1、reaction 4。

自我檢查：現狀摘要與行為快照完整技能 301 筆不一致 0 筆。

### 覆寫結果

| 覆寫 | 說明 | > 150 | 最大 ‰ | < 120 | 120–150 | 151–200 | > 200 | 快照變 |
|---|---|---|---|---|---|---|---|---|
| `none` | 現狀 | 23 | 200 | 113 | 165 | 23 | 0 | 0 |

「快照變」＝行為快照完整技能那一組會變的筆數（升階重配、閃現出題不經過這裡，不變）。

### 每招前後（‰）

| 技能 | 種類 | 超過那一步 | 只走上限內 | `none` |
|---|---|---|---|---|
| ambush_stab | reaction | multiplier_permille 1100 → 1200 | 100 | 200 |
| attack_mastery | modifier | 修正 damage_permille 55 → 60 | 100 | 200 |
| ember_trail | active | duration 3 → 4 | 61 | 200 |
| holy_ground | active | duration 5 → 6 | 61 | 200 |
| parting_slash | reaction | multiplier_permille 1100 → 1200 | 100 | 200 |
| smoke_arrow | active | duration 5 → 6 | 112 | 200 |
| smoke_bomb | active | duration 5 → 6 | 112 | 200 |
| covering_fire | reaction | multiplier_permille 900 → 1000 | 98 | 197 |
| cluster_bolt | active | dice 2d10 → 5d4 | 117 | 190 |
| form_release_burst | active | dice 2d10 → 5d4 | 78 | 190 |
| second_wind | passive | dice 2d10 → 5d4 | 52 | 190 |
| life_drain | active | dice 1d10 → 1d12 | 71 | 181 |
| grief_rage | reaction | 減代價 cooldown 2 → 1 | 117 | 170 |
| fire_bolt | active | dice 2d4 → 1d10 | 110 | 166 |
| overdraft_strike | active | multiplier_permille 3000 → 3250 | 82 | 160 |
| gale_kick | active | 減代價 cooldown 2 → 1 | 115 | 154 |
| grapple_arrow | active | 減代價 cooldown 2 → 1 | 115 | 154 |
| hex_bolt | active | dice 2d4 → 1d10 | 87 | 153 |
| radiant_mend | active | dice 2d4 → 1d10 | 98 | 153 |
| rime_touch | active | dice 2d4 → 1d10 | 87 | 153 |
| stoneskin_ward | active | dice 1d6 → 1d8 | 61 | 153 |
| decoy_swap | active | 減代價 cooldown 3 → 2 | 115 | 152 |
| soul_reap | active | dice 2d4 → 1d10 | 86 | 151 |

