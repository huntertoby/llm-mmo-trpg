## 5. 傷害落差分解（英雄每場）

| build | 英雄回合/場 | 進攻決策/回合 | 無進攻回合比 | 第一次進攻的輪數(均) | 死前沒進攻過 | 防禦決策/回合 | 移動決策/回合 | 結束時剩 AP>=1 的回合比 | 剩 AP 時最近敵人(均) | 英雄傷害/場 | 傷害/進攻決策 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| build_seer | 3.0 | 2.86 | 2% | 1.0 | 3% | 0.00 | 0.72 | 2% | 7.4 | 36.5 | 4.3 |
| build_gambler | 3.3 | 1.36 | 15% | 1.0 | 0% | 0.28 | 0.99 | 26% | 3.4 | 34.6 | 7.8 |
| build_assassin | 3.4 | 1.03 | 32% | 1.3 | 6% | 0.40 | 0.87 | 25% | 3.1 | 23.3 | 6.6 |
| build_ranged | 3.5 | 1.81 | 0% | 1.0 | 0% | 0.00 | 0.65 | 0% | 7.3 | 51.8 | 8.1 |
| build_striker | 2.8 | 1.92 | 2% | 1.0 | 3% | 0.01 | 0.79 | 2% | 6.6 | 50.9 | 9.3 |
| build_tank | 6.5 | 1.57 | 3% | 1.0 | 0% | 0.72 | 0.76 | 30% | 3.9 | 30.4 | 3.0 |
| build_bomber | 2.7 | 1.92 | 0% | 1.0 | 3% | 0.01 | 0.70 | 0% | 5.0 | 56.0 | 10.7 |

### 普攻（1 AP）

- build_seer：0.33 次/場，命中 51%，每次 2.1 傷害
- build_gambler：1.09 次/場，命中 58%，每次 3.9 傷害
- build_assassin：0.79 次/場，命中 57%，每次 3.3 傷害
- build_ranged：2.39 次/場，命中 55%，每次 4.2 傷害
- build_striker：1.45 次/場，命中 47%，每次 3.3 傷害
- build_tank：1.97 次/場，命中 58%，每次 4.3 傷害
- build_bomber：0.70 次/場，命中 51%，每次 3.8 傷害

### 防禦決策發生時（HP 比、最近敵人、2 格內敵人）

- build_seer：0.01 次/場；HP 比中位 92%；最近敵人平均 4.8 格；2 格內敵人 0.0；同時有進攻候選分>0 的比例 0%
- build_gambler：0.92 次/場；HP 比中位 96%；最近敵人平均 3.1 格；2 格內敵人 0.6；同時有進攻候選分>0 的比例 3%
- build_assassin：1.37 次/場；HP 比中位 59%；最近敵人平均 3.2 格；2 格內敵人 0.0；同時有進攻候選分>0 的比例 1%
- build_ranged：0.01 次/場；HP 比中位 100%；最近敵人平均 4.5 格；2 格內敵人 0.0；同時有進攻候選分>0 的比例 0%
- build_striker：0.04 次/場；HP 比中位 45%；最近敵人平均 4.4 格；2 格內敵人 0.0；同時有進攻候選分>0 的比例 8%
- build_tank：4.68 次/場；HP 比中位 83%；最近敵人平均 2.6 格；2 格內敵人 0.8；同時有進攻候選分>0 的比例 55%
- build_bomber：0.02 次/場；HP 比中位 50%；最近敵人平均 3.0 格；2 格內敵人 0.2；同時有進攻候選分>0 的比例 0%

### 第一輪英雄決策的選擇

- build_seer：skill:skill_hex_bolt 47%，move 22%，end 11%，skill:skill_blessing_thief 6%，attack 4%，skill:skill_quicken_tide 4%
- build_gambler：move 27%，end 21%，skill:skill_fury_stance 17%，attack 9%，defend 8%，skill:skill_first_strike 7%
- build_assassin：move 24%，end 22%，skill:skill_fury_stance 18%，defend 9%，skill:skill_shadow_backstab 7%，skill:skill_blink 6%
- build_ranged：skill:skill_sniper_shot 23%，move 22%，skill:skill_overwatch 16%，skill:skill_time_surge 13%，end 12%，attack 7%
- build_striker：move 27%，skill:skill_bloodwake_stride 23%，skill:skill_cluster_bolt 15%，end 14%，attack 10%，skill:skill_armor_break_combo 5%
- build_tank：skill:skill_guardian_aegis 25%，move 23%，end 21%，defend 18%，skill:skill_taunting_roar 5%，attack 3%
- build_bomber：skill:skill_ash_harvest 30%，move 27%，skill:skill_frost_shackle 20%，end 13%，skill:skill_blink 4%，attack 3%

### seer：給友方的支援技（專注湧流、疾時之潮）使用時

- skill_focus_surge：391 次；目標：build_seer 391；施放時英雄法力平均 64（上限 40）；同時 hex_bolt 候選分>0 90%；本招平均分數 41.8，同決策 hex_bolt 最高候選分平均 25.7
- skill_quicken_tide：272 次；目標：build_seer 272；施放時英雄法力平均 69（上限 40）；同時 hex_bolt 候選分>0 85%；本招平均分數 55.6，同決策 hex_bolt 最高候選分平均 23.1
- hex_bolt 的目標範本：bandit 530，bandit_archer 528，bandit_captain 113，bandit_shieldbearer 98，bandit_boss 72
- hex_bolt 選用時最近敵人距離平均 2.9；選用時分數平均 33.9
