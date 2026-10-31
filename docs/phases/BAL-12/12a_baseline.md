# BAL-3 全面基線報表

規模：BaselineSizes(map_seeds=30, matrix_seeds=10, weapon_seeds=5, boss_seeds=30, summon_seeds=8, resource_seeds=40, run_seeds=20, seed_start=0, maps=(), builds=(), weapon_builds=(), packs=('dev_spirit', 'dev_summoner', 'dev_summoner_bone', 'dev_bulwark', 'dev_blaze', 'dev_hawkeye'), scenarios=(), resource_builds=('build_skill_archer', 'build_attack_archer', 'build_summoner', 'build_push', 'build_fire'), summon_maps=('open_plain', 'dark_forest', 'ruined_fort', 'swamp', 'narrow_halls'), run_policy='balanced', sections=('maps', 'matrix', 'resources'))

共 83 項指標，有目標的 83 項，偏離（⚠）25 項。
偏離 ＝ 超出目標區間的距離 ÷ 指標尺度（勝率 30 個百分點、輪數為區間寬度），可跨單位排序。

## 偏離最大的前 10 項

| # | 區塊 | 項目 | 數值 | 目標 | 偏離 |
|---|---|---|---|---|---|
| 1 | matrix | 標準2：沒有任何前段類型的 build 數 | 8個 | 0（6.8 標準） | 2.67 |
| 2 | matrix | build_storm 勝率 | 85.0% | 35–65% | 0.67 |
| 3 | maps | dark_forest 我方勝率 | 83.3% | 35–65% | 0.61 |
| 4 | matrix | build_assassin 前段類型數 | 0種 | 1–7 種（共 8） | 0.50 |
| 5 | matrix | build_bomber 前段類型數 | 0種 | 1–7 種（共 8） | 0.50 |
| 6 | matrix | build_gambler 前段類型數 | 0種 | 1–7 種（共 8） | 0.50 |
| 7 | matrix | build_push 前段類型數 | 0種 | 1–7 種（共 8） | 0.50 |
| 8 | matrix | build_runeweaver 前段類型數 | 0種 | 1–7 種（共 8） | 0.50 |
| 9 | matrix | build_seer 前段類型數 | 0種 | 1–7 種（共 8） | 0.50 |
| 10 | matrix | build_storm 前段類型數 | 8種 | 1–7 種（共 8） | 0.50 |

## 一、示範地圖（一般遭遇）（6/20 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| bridge_chasm 我方勝率 | 60.0% | 30 | 35–65% | ✓ | 0.00 | 平手 0 |
| bridge_chasm 平均輪數 | 4.4輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| cliff_outpost 我方勝率 | 63.3% | 30 | 35–65% | ✓ | 0.00 | 平手 0 |
| cliff_outpost 平均輪數 | 4.3輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| dark_forest 我方勝率 | 83.3% | 30 | 35–65% | ⚠ | 0.61 | 平手 0 |
| dark_forest 平均輪數 | 4.6輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| frozen_lake 我方勝率 | 73.3% | 30 | 35–65% | ⚠ | 0.28 | 平手 0 |
| frozen_lake 平均輪數 | 4.7輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| lava_crossing 我方勝率 | 66.7% | 30 | 35–65% | ⚠ | 0.06 | 平手 0 |
| lava_crossing 平均輪數 | 4.7輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| narrow_halls 我方勝率 | 63.3% | 30 | 35–65% | ✓ | 0.00 | 平手 0 |
| narrow_halls 平均輪數 | 4.5輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| oil_depot 我方勝率 | 63.3% | 30 | 35–65% | ✓ | 0.00 | 平手 0 |
| oil_depot 平均輪數 | 4.4輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| open_plain 我方勝率 | 43.3% | 30 | 35–65% | ✓ | 0.00 | 平手 0 |
| open_plain 平均輪數 | 4.3輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| ruined_fort 我方勝率 | 33.3% | 30 | 35–65% | ⚠ | 0.06 | 平手 0 |
| ruined_fort 平均輪數 | 4.2輪 | 30 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| swamp 我方勝率 | 66.7% | 30 | 35–65% | ⚠ | 0.06 | 平手 0 |
| swamp 平均輪數 | 3.6輪 | 30 | 4–6 輪 | ⚠ | 0.18 | 一般遭遇 |

## 三、build 矩陣（18/48 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| build_push 勝率 | 56.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 7.9 |
| build_push 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_fire 勝率 | 79.0% | 100 | 35–65% | ⚠ | 0.47 | 偏強；英雄 DPR 14.6 |
| build_fire 前段類型數 | 7種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_storm 勝率 | 85.0% | 100 | 35–65% | ⚠ | 0.67 | 偏強；英雄 DPR 31.8 |
| build_storm 前段類型數 | 8種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_tank 勝率 | 50.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 3.3 |
| build_tank 前段類型數 | 2種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_ranged 勝率 | 55.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 12.1 |
| build_ranged 前段類型數 | 2種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_assassin 勝率 | 34.0% | 100 | 35–65% | ⚠ | 0.03 | 偏弱；英雄 DPR 7.5 |
| build_assassin 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_support 勝率 | 60.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 6.3 |
| build_support 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_healer 勝率 | 76.0% | 100 | 35–65% | ⚠ | 0.37 | 偏強；英雄 DPR 2.8 |
| build_healer 前段類型數 | 7種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_warlock 勝率 | 65.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 18.5 |
| build_warlock 前段類型數 | 5種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_guardian 勝率 | 45.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 3.7 |
| build_guardian 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_striker 勝率 | 54.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 12.7 |
| build_striker 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_trapper 勝率 | 54.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 6.9 |
| build_trapper 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_charger 勝率 | 47.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 7.4 |
| build_charger 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_banisher 勝率 | 53.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 14.8 |
| build_banisher 前段類型數 | 2種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_summoner 勝率 | 74.0% | 100 | 35–65% | ⚠ | 0.30 | 偏強；英雄 DPR 9.6 |
| build_summoner 前段類型數 | 6種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_gambler 勝率 | 44.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 7.0 |
| build_gambler 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_seer 勝率 | 47.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 8.9 |
| build_seer 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_bomber 勝率 | 50.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 12.6 |
| build_bomber 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_winged 勝率 | 39.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 7.2 |
| build_winged 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_telekinesis 勝率 | 73.0% | 100 | 35–65% | ⚠ | 0.27 | 偏強；英雄 DPR 11.1 |
| build_telekinesis 前段類型數 | 6種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_wallburn 勝率 | 52.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 8.8 |
| build_wallburn 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_detonator 勝率 | 70.0% | 100 | 35–65% | ⚠ | 0.17 | 偏強；英雄 DPR 21.2 |
| build_detonator 前段類型數 | 6種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_runeweaver 勝率 | 46.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 10.6 |
| build_runeweaver 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| 標準1：所有類型都前段的 build 數 | 1個 | 23 | 0（6.8 標準） | ⚠ | 0.33 | build_storm |
| 標準2：沒有任何前段類型的 build 數 | 8個 | 23 | 0（6.8 標準） | ⚠ | 2.67 | build_push、build_assassin、build_striker、build_gambler、build_seer、build_bomber、build_winged、build_runeweaver |

## 四、資源短缺（1/15 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| build_skill_archer × single 法力不足回合 | 0.0% | 232 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 88% |
| build_attack_archer × single 法力不足回合 | 0.0% | 169 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 78% |
| build_summoner × single 法力不足回合 | 0.0% | 179 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 90% |
| build_push × single 法力不足回合 | 0.0% | 242 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 18%；英雄勝率 62% |
| build_fire × single 法力不足回合 | 5.3% | 169 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 92% |
| build_skill_archer × area 法力不足回合 | 0.0% | 128 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 92% |
| build_attack_archer × area 法力不足回合 | 0.0% | 118 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 100% |
| build_summoner × area 法力不足回合 | 0.0% | 123 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 88% |
| build_push × area 法力不足回合 | 0.0% | 147 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 92% |
| build_fire × area 法力不足回合 | 0.0% | 126 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 100% |
| build_skill_archer × boss 法力不足回合 | 0.0% | 196 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 38% |
| build_attack_archer × boss 法力不足回合 | 0.0% | 176 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 32% |
| build_summoner × boss 法力不足回合 | 19.4% | 299 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 65% |
| build_push × boss 法力不足回合 | 0.0% | 281 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 16%；英雄勝率 2% |
| build_fire × boss 法力不足回合 | 25.1% | 287 | ≤ 20%（參考） | ⚠ | 0.25 | 耐力不足 0%；英雄勝率 62% |
