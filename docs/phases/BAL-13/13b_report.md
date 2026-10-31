## 1. 總覽（每 build 300 場）

| build | 勝率 | 輪數 | 英雄存活 | 英雄倒地輪(均) | 隊友倒地數/場 | 英雄回合數 | 每回合 AP | 結束回合時未用 AP | 技能 AP 占比 | 英雄對敵傷害/場 | 隊友對敵傷害/場 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| build_seer | 49.0% | 5.0 | 30% | 2.8 | 1.21 | 3.0 | 3.02 | 0.07 | 90% | 36.5 | 92.0 |
| build_gambler | 44.3% | 5.4 | 22% | 3.3 | 1.33 | 3.3 | 3.22 | 0.53 | 53% | 34.6 | 92.8 |
| build_assassin | 39.0% | 5.3 | 24% | 3.2 | 1.41 | 3.4 | 3.20 | 0.53 | 52% | 23.3 | 98.0 |
| build_ranged | 54.7% | 4.9 | 40% | 3.2 | 1.16 | 3.5 | 3.00 | 0.01 | 91% | 51.8 | 82.4 |
| build_striker | 56.3% | 4.8 | 33% | 2.7 | 1.07 | 2.9 | 3.02 | 0.07 | 70% | 50.9 | 85.3 |
| build_tank | 47.7% | 7.4 | 43% | 6.7 | 1.49 | 6.6 | 3.27 | 0.52 | 45% | 30.4 | 101.3 |
| build_bomber | 54.7% | 4.6 | 34% | 2.6 | 1.11 | 2.7 | 3.00 | 0.00 | 80% | 56.0 | 82.8 |

## 2. 技能使用率


### build_seer：技能使用率與每次期望效果（300 場，3877 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| skill_hex_bolt | 4.53 | 77% | 66% | 46% | 5.2 | 5.2 | 50% | 6% | 0.00 | 法2 |
| skill_focus_surge | 1.30 | 18% | 18% | 55% | 0.0 | 0.0 | - | - | 0.00 | 法2 |
| skill_blessing_thief | 0.91 | 58% | 41% | 12% | 4.4 | 4.4 | 36% | 5% | 0.00 | 法4 |
| skill_quicken_tide | 0.91 | 15% | 13% | 47% | 0.1 | 0.1 | - | - | 0.00 | 法3 |
| rx:block | 0.56 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_dispel_magic | 0.32 | 71% | 53% | 3% | 4.2 | 4.2 | 40% | 4% | 0.00 | 法4 |
| skill_flare_sight | 0.13 | 74% | 63% | 1% | 0.0 | 0.0 | - | - | 0.00 | 法3 |
| basic | 0.00 | 0% | 0% | - | 208.0 | 208.0 | 51% | 9% | 0.00 | - |
| non_skill | 0.00 | 0% | 0% | - | 311.0 | 311.0 | - | - | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 84.0 | 84.0 | - | - | 0.00 | - |

英雄決策分佈：skill:skill_hex_bolt 35%，move 16%，end 16%，skill:skill_focus_surge 10%，skill:skill_blessing_thief 7%，skill:skill_quicken_tide 7%，attack 4%，skill:skill_dispel_magic 2%，skill:skill_flare_sight 1%，shove 1%

### build_gambler：技能使用率與每次期望效果（300 場，3574 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| rx:block | 0.88 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_fury_stance | 0.86 | 25% | 25% | 29% | 0.4 | 0.4 | - | - | 0.00 | - |
| trig:skill_bloodlust | 0.81 | 0% | 0% | - | 0.4 | 0.4 | 55% | 2% | 0.01 | - |
| skill_berserker_rage | 0.80 | 32% | 21% | 21% | 12.3 | 6.1 | 65% | 6% | 0.09 | 耐8 |
| skill_all_in | 0.65 | 33% | 23% | 17% | 5.2 | 2.6 | 56% | 6% | 0.02 | 耐6 |
| skill_wild_blade | 0.45 | 33% | 21% | 12% | 9.2 | 4.6 | 68% | 26% | 0.03 | 耐8 |
| rx:skill_grief_rage | 0.33 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_grief_rage | 0.33 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_first_strike | 0.30 | 31% | 20% | 8% | 10.1 | 5.0 | 59% | 7% | 0.01 | 耐10 |
| skill_blood_sacrifice | 0.14 | 32% | 21% | 4% | 10.4 | 5.2 | 60% | 2% | 0.01 | 耐8 |
| rx:opportunity_attack | 0.12 | 0% | 0% | - | 3.4 | 3.4 | 72% | 3% | 0.00 | - |
| skill_reckless_lunge | 0.03 | 33% | 21% | 1% | 23.9 | 11.9 | 90% | 10% | 0.01 | 耐8 |
| basic | 0.00 | 0% | 0% | - | 1275.0 | 1275.0 | 58% | 7% | 0.00 | - |
| non_skill | 0.00 | 0% | 0% | - | 318.0 | 318.0 | - | - | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 72.0 | 72.0 | - | - | 0.00 | - |

英雄決策分佈：move 24%，end 21%，attack 10%，defend 8%，skill:skill_fury_stance 7%，skill:skill_berserker_rage 7%，skill:skill_all_in 5%，shove 5%，skill:skill_wild_blade 4%，run 4%

### build_assassin：技能使用率與每次期望效果（300 場，3698 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| rx:skill_ambush_stab | 1.11 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_ambush_stab | 1.11 | 0% | 0% | - | 2.5 | 2.5 | 60% | 11% | 0.00 | - |
| skill_shadow_backstab | 0.93 | 23% | 13% | 33% | 4.7 | 2.3 | 68% | 16% | 0.59 | 耐10 |
| skill_fury_stance | 0.90 | 19% | 19% | 39% | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_retreating_slash | 0.57 | 19% | 18% | 24% | 2.5 | 1.3 | 62% | 9% | 0.00 | 耐10 |
| skill_pick_off | 0.42 | 26% | 12% | 13% | 7.1 | 3.5 | 65% | 9% | 0.04 | 耐10 |
| trig:skill_crippling_crit | 0.39 | 0% | 0% | - | 1.3 | 1.3 | 71% | 20% | 0.00 | - |
| skill_blink | 0.37 | 64% | 31% | 5% | 0.4 | 0.4 | - | - | 0.00 | 法4 |
| rx:block | 0.30 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_shadow_ambush | 0.28 | 33% | 17% | 7% | 4.0 | 2.0 | 71% | 19% | 0.11 | 耐12 |
| rx:opportunity_attack | 0.03 | 0% | 0% | - | 1.9 | 1.9 | 60% | 10% | 0.00 | - |
| skill_pincer_strike | 0.02 | 28% | 13% | 1% | 10.0 | 5.0 | 71% | 29% | 0.01 | 耐10 |
| basic | 0.00 | 0% | 0% | - | 784.0 | 784.0 | 57% | 12% | 0.00 | - |
| non_skill | 0.00 | 0% | 0% | - | 773.0 | 773.0 | - | - | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 5.0 | 5.0 | - | - | 0.00 | - |

英雄決策分佈：move 22%，end 22%，defend 11%，skill:skill_shadow_backstab 8%，attack 7%，skill:skill_fury_stance 7%，shove 6%，skill:skill_retreating_slash 5%，skill:skill_pick_off 3%，skill:skill_blink 3%

### build_ranged：技能使用率與每次期望效果（300 場，3968 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| skill_sniper_shot | 1.92 | 25% | 18% | 58% | 9.5 | 4.7 | 56% | 7% | 0.00 | 耐8 |
| skill_armor_piercing_arrow | 1.27 | 34% | 27% | 28% | 7.4 | 3.7 | 64% | 5% | 0.00 | 耐10 |
| skill_time_surge | 0.98 | 21% | 21% | 35% | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_overwatch | 0.77 | 60% | 13% | 10% | 0.0 | 0.0 | - | - | 0.00 | 耐2 |
| rx:overwatch_shot | 0.69 | 0% | 0% | - | 4.6 | 4.6 | 56% | 9% | 0.00 | - |
| skill_high_ground_shot | 0.56 | 41% | 33% | 10% | 6.6 | 3.3 | 51% | 4% | 0.00 | 耐10 |
| trig:skill_lucky_break | 0.37 | 0% | 0% | - | 1.0 | 1.0 | 65% | 0% | 0.00 | - |
| rx:block | 0.24 | 0% | 0% | - | 0.1 | 0.1 | 33% | 0% | 0.00 | - |
| skill_piercing_shot | 0.20 | 32% | 15% | 5% | 11.9 | 6.0 | 67% | 5% | 0.00 | 耐12 |
| rx:skill_covering_fire | 0.08 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_covering_fire | 0.08 | 0% | 0% | - | 3.4 | 3.4 | 65% | 0% | 0.00 | - |
| basic | 0.00 | 0% | 0% | - | 2994.0 | 2994.0 | 55% | 7% | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 146.0 | 146.0 | - | - | 0.00 | - |
| non_skill | 0.00 | 0% | 0% | - | 11.0 | 11.0 | - | - | 0.00 | - |

英雄決策分佈：attack 19%，end 18%，move 18%，skill:skill_sniper_shot 14%，skill:skill_armor_piercing_arrow 10%，skill:skill_time_surge 7%，skill:skill_overwatch 6%，skill:skill_high_ground_shot 4%，aim 2%，skill:skill_piercing_shot 1%

### build_striker：技能使用率與每次期望效果（300 場，3217 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| trig:skill_ember_brand | 1.61 | 0% | 0% | - | 1.0 | 1.0 | 60% | 7% | 0.00 | - |
| skill_overcurrent | 1.56 | 65% | 36% | 23% | 6.6 | 6.6 | 52% | 6% | 0.00 | 法2 |
| skill_cluster_bolt | 1.10 | 37% | 21% | 27% | 12.1 | 6.1 | 53% | 7% | 0.00 | 法4 |
| skill_bloodwake_stride | 0.93 | 15% | 15% | 58% | 0.0 | 0.0 | - | - | 0.00 | - |
| rx:block | 0.50 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_armor_break_combo | 0.46 | 6% | 5% | 76% | 7.5 | 3.8 | 50% | 4% | 0.00 | 法4 |
| skill_static_palm | 0.40 | 56% | 21% | 7% | 7.1 | 7.1 | 61% | 8% | 0.00 | 法2 |
| skill_thunder_finisher | 0.01 | 0% | 0% | 50% | 12.3 | 6.2 | 50% | 0% | 0.00 | 法6 |
| non_skill | 0.00 | 0% | 0% | - | 1433.0 | 1433.0 | - | - | 0.00 | - |
| basic | 0.00 | 0% | 0% | - | 1451.0 | 1451.0 | 47% | 6% | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 182.0 | 182.0 | - | - | 0.00 | - |

英雄決策分佈：move 21%，attack 18%，end 17%，skill:skill_overcurrent 15%，skill:skill_cluster_bolt 10%，skill:skill_bloodwake_stride 9%，skill:skill_armor_break_combo 4%，skill:skill_static_palm 4%，aim 2%，run 0%

### build_tank：技能使用率與每次期望效果（300 場，8108 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| skill_guardian_aegis | 5.87 | 28% | 27% | 78% | 0.6 | 0.6 | - | - | 0.00 | 法3 |
| rx:block | 1.48 | 0% | 0% | - | 0.3 | 0.3 | 49% | 7% | 0.00 | - |
| rx:skill_grief_rage | 0.90 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_grief_rage | 0.90 | 0% | 0% | - | 0.0 | 0.0 | - | - | 0.00 | - |
| skill_taunting_roar | 0.81 | 59% | 26% | 5% | 0.0 | 0.0 | 41% | 6% | 0.00 | 法1 |
| skill_parry_riposte | 0.63 | 19% | 17% | 12% | 3.0 | 1.5 | 61% | 9% | 0.01 | 耐8 |
| skill_encircled_sweep | 0.48 | 47% | 10% | 4% | 5.7 | 2.8 | 56% | 5% | 0.00 | 耐12 |
| skill_armor_breaker | 0.38 | 32% | 20% | 4% | 8.4 | 4.2 | 63% | 3% | 0.04 | 耐8 |
| rx:opportunity_attack | 0.16 | 0% | 0% | - | 3.0 | 3.0 | 53% | 2% | 0.01 | - |
| skill_sunder_strike | 0.05 | 47% | 31% | 0% | 1.1 | 1.1 | 46% | 0% | 0.01 | 耐6 |
| basic | 0.00 | 0% | 0% | - | 2566.0 | 2566.0 | 58% | 5% | 0.10 | - |
| non_skill | 0.00 | 0% | 0% | - | 539.0 | 539.0 | - | - | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 8.0 | 8.0 | - | - | 0.00 | - |

英雄決策分佈：skill:skill_guardian_aegis 22%，end 20%，defend 17%，move 17%，attack 7%，shove 5%，skill:skill_taunting_roar 3%，skill:skill_parry_riposte 2%，skill:skill_encircled_sweep 2%，skill:skill_armor_breaker 1%

### build_bomber：技能使用率與每次期望效果（300 場，2844 個有候選的決策點）

| 招 | 每場施放 | 候選出現率 | 候選分>0 | 被選率(在出現時) | 每次傷害 | 每 AP 傷害 | 命中率 | 暴擊率 | 背刺命中 | 代價/次 |
|---|---|---|---|---|---|---|---|---|---|---|
| skill_ash_harvest | 1.77 | 32% | 23% | 58% | 10.7 | 5.4 | 54% | 5% | 0.00 | 法4 |
| trig:skill_ember_brand | 1.64 | 0% | 0% | - | 1.0 | 1.0 | 58% | 4% | 0.00 | - |
| skill_frost_shackle | 1.24 | 47% | 37% | 28% | 5.8 | 5.8 | 56% | 8% | 0.00 | 法4 |
| skill_time_bomb_rune | 0.63 | 33% | 29% | 20% | 0.7 | 0.3 | 57% | 4% | 0.00 | 法5 |
| rx:block | 0.57 | 0% | 0% | - | 0.0 | 0.0 | 100% | 0% | 0.00 | - |
| skill_blink | 0.18 | 65% | 25% | 3% | 0.3 | 0.3 | - | - | 0.00 | 法4 |
| skill_death_spiral | 0.14 | 13% | 12% | 12% | 7.9 | 3.9 | 64% | 9% | 0.00 | 法4 |
| skill_undying_oath | 0.05 | 1% | 1% | 88% | 0.0 | 0.0 | - | - | 0.00 | - |
| non_skill | 0.00 | 0% | 0% | - | 2930.0 | 2930.0 | - | - | 0.00 | - |
| basic | 0.00 | 0% | 0% | - | 794.0 | 794.0 | 51% | 5% | 0.00 | - |
| other | 0.00 | 0% | 0% | - | 72.0 | 72.0 | - | - | 0.00 | - |

英雄決策分佈：move 20%，skill:skill_ash_harvest 19%，end 19%，attack 13%，skill:skill_frost_shackle 13%，skill:skill_time_bomb_rune 7%，aim 4%，skill:skill_blink 2%，skill:skill_death_spiral 1%，shove 1%

## 3. 死因與死亡回合

| build | 英雄倒地場數 | 倒地輪數分布(1/2/3/4/5+) | 死前 2 輪主因（來源|cause） | 平均來源數 | 純自傷占比 |
|---|---|---|---|---|---|
| build_seer | 210/300 | 26/75/56/29/24 | bandit_archer|attack 70%；bandit|attack 12%；bandit|collision 5%；bandit_boss|attack 5% | 1.6 | 0% |
| build_gambler | 233/300 | 12/63/72/50/36 | bandit_archer|attack 56%；bandit|attack 20%；bandit_shieldbearer|attack 7%；bandit_boss|attack 5% | 2.0 | 0% |
| build_assassin | 228/300 | 19/77/46/54/32 | bandit_archer|attack 57%；bandit|attack 26%；bandit_boss|attack 6%；bandit_captain|attack 3% | 1.8 | 0% |
| build_ranged | 179/300 | 12/58/42/39/28 | bandit_archer|attack 59%；bandit|attack 19%；bandit_captain|attack 8%；bandit_boss|attack 6% | 1.7 | 0% |
| build_striker | 200/300 | 33/68/52/31/16 | bandit_archer|attack 70%；bandit|attack 13%；bandit|collision 5%；bandit_boss|attack 4% | 1.6 | 0% |
| build_tank | 170/300 | 0/3/15/16/136 | bandit_archer|attack 50%；bandit|attack 12%；bandit_archer|deadly_terrain 9%；bandit_boss|attack 8% | 1.7 | 1% |
| build_bomber | 197/300 | 33/73/50/28/13 | bandit_archer|attack 66%；bandit|attack 14%；bandit|collision 6%；bandit_boss|attack 4% | 1.7 | 1% |

### 敵方攻擊的目標分佈（每輪桶；比例＝打在英雄上 / 所有敵方攻擊）

| build | 第1輪 | 第2輪 | 第3輪+ | 每場英雄承傷 | 其中第1~2輪承傷占比 |
|---|---|---|---|---|---|
| build_seer | 45%（5.8） | 27%（7.1） | 14%（11.3） | 36.4 | 76% |
| build_gambler | 38%（6.0） | 50%（7.6） | 30%（14.3） | 58.6 | 60% |
| build_assassin | 59%（7.0） | 36%（8.1） | 19%（14.0） | 54.7 | 75% |
| build_ranged | 45%（6.1） | 25%（7.2） | 24%（10.6） | 37.8 | 66% |
| build_striker | 46%（5.8） | 27%（7.2） | 13%（9.5） | 35.6 | 81% |
| build_tank | 15%（5.9） | 20%（7.0） | 51%（21.2） | 46.2 | 20% |
| build_bomber | 46%（5.8） | 27%（6.6） | 12%（9.0） | 35.2 | 81% |

### 英雄承傷來源（每場，依來源範本與 cause，前 5）

- build_seer：bandit_archer|attack 26.7；bandit|attack 3.7；bandit|collision 2.5；bandit_boss|attack 1.3；bandit_captain|attack 0.5
- build_gambler：bandit_archer|attack 35.5；bandit|attack 10.6；bandit_shieldbearer|attack 3.5；bandit_boss|attack 3.2；bandit_captain|attack 2.3
- build_assassin：bandit_archer|attack 33.7；bandit|attack 13.0；bandit_boss|attack 2.6；bandit_shieldbearer|attack 1.7；bandit_captain|attack 1.4
- build_ranged：bandit_archer|attack 25.4；bandit|attack 5.7；bandit_captain|attack 2.1；bandit|collision 1.8；bandit_boss|attack 1.4
- build_striker：bandit_archer|attack 27.1；bandit|attack 3.5；bandit|collision 1.8；bandit_boss|attack 1.0；bandit_captain|attack 0.6
- build_tank：bandit_archer|attack 27.3；bandit|attack 5.5；bandit_boss|attack 3.3；bandit_shieldbearer|attack 2.5；bandit_captain|attack 1.6
- build_bomber：bandit_archer|attack 24.7；bandit|attack 4.0；bandit|collision 2.4；bandit_boss|attack 1.3；bandit_boss|collision 0.5

## 4a. seer：咒印、驅散、奪取、揭露、法力回復

- 咒印施加：271 次（每場 0.90）；刷新已有咒印 79 次
- 上咒印後窗口內（到咒印消失／目標倒地）：有接攻擊（隊友或英雄打同目標）的咒印 207/271（76%）；隊友對咒印目標的攻擊平均 1.17 次/咒印，窗口內隊友全部攻擊 1.63 次/咒印（同目標占 72%）；英雄自己打同目標 0.57 次/咒印；窗口平均 0.3 輪；目標在咒印中倒地 144 次
- 隊友攻擊命中率：對咒印目標 84%（316 次），對其他目標 58%（5324 次）
- hex_bolt 被選 1358 次；目標當下已有咒印 210 次（15%）
- 破魔／奪取／照明彈實際移除的狀態（總數）：skill_blessing_thief:stolen:defending 99；skill_dispel_magic:dispelled:defending 38
  - skill_dispel_magic：每場施放 0.32，移除狀態合計 38，每次 0.40；目標身上有任何狀態 90/96
  - skill_blessing_thief：每場施放 0.91，移除狀態合計 99，每次 0.36；目標身上有任何狀態 258/273
  - skill_flare_sight：每場施放 0.13，移除狀態合計 0，每次 0.00；目標身上有任何狀態 0/39
- 法力／冷卻回復（給隊友）：restored:cooldown:cd 1.81/場；restored:mana:mana 12.19/場；restored_n:cooldown 0.91/場；restored_n:mana 1.30/場

## 4b. gambler：賭注結果、反噬、使用時機

- skill_blood_sacrifice 賭注：25 次（每場 0.08），成功 68%
- 反噬（失手）：每場 0.25；因而倒地（prone）每場 0.54
- 英雄承傷：每場 58.6，其中自傷（血祭／反噬／狂戰士之怒）0.0（0%）
- 技能以 HP 付費：每場 0.0
  - skill_blood_sacrifice：選用 42 次；選用時 HP 比 中位 100%、低於 30% 0 次；平均分數 108.8；耐力中位 41
  - skill_all_in：選用 196 次；選用時 HP 比 中位 50%、低於 30% 62 次；平均分數 132.2；耐力中位 34
  - skill_wild_blade：選用 136 次；選用時 HP 比 中位 61%、低於 30% 25 次；平均分數 135.4；耐力中位 37
  - skill_reckless_lunge：選用 10 次；選用時 HP 比 中位 91%、低於 30% 0 次；平均分數 175.1；耐力中位 36
  - skill_berserker_rage：選用 241 次；選用時 HP 比 中位 30%、低於 30% 120 次；平均分數 171.8；耐力中位 31
- 回合開始耐力 < 6（最便宜的耐力技都付不起）：0%；耐力 < 10：0%；平均 36.4

## 4c. assassin：背刺、瞬步、撤退

- skill_shadow_backstab：選用 278 次（0.93/場）；用前離最近敵人 2.3 格、2 格內敵人 0.7；目標 HP 比平均 73%
- skill_shadow_ambush：選用 84 次（0.28/場）；用前離最近敵人 2.4 格、2 格內敵人 0.7；目標 HP 比平均 56%
- skill_blink：選用 112 次（0.37/場）；用前離最近敵人 5.1 格、2 格內敵人 0.2；目標 HP 比平均 0%
- skill_retreating_slash：選用 170 次（0.57/場）；用前離最近敵人 2.6 格、2 格內敵人 0.3；目標 HP 比平均 0%
- skill_pincer_strike：選用 7 次（0.02/場）；用前離最近敵人 1.0 格、2 格內敵人 1.3；目標 HP 比平均 63%
- skill_pick_off：選用 127 次（0.42/場）；用前離最近敵人 1.0 格、2 格內敵人 1.2；目標 HP 比平均 63%
- 英雄命中 2.8/場（命中率 63%），其中背刺 0.76/場（27%），潛行偷襲 0.25/場，暴擊 0.56/場
- 英雄回合（可觀測 982）：回合開始離最近敵人 3.6 格 -> 結束 2.6 格；結束時比開始更遠 23%；有攻擊 76%；攻擊後結束時 2 格內無敵人 70%
- HP < 35% 的決策點 1281 個（每場 4.27）；選：end 352，move 234，defend 148，attack 114，skill:skill_shadow_backstab 102，shove 102
