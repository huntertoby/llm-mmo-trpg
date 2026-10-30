# BAL-3 全面基線報表

規模：BaselineSizes(map_seeds=60, matrix_seeds=10, weapon_seeds=10, boss_seeds=60, summon_seeds=12, resource_seeds=40, run_seeds=40, seed_start=0, maps=(), builds=(), weapon_builds=(), packs=('dev_spirit', 'dev_summoner', 'dev_summoner_bone', 'dev_bulwark', 'dev_blaze', 'dev_hawkeye'), scenarios=(), resource_builds=('build_skill_archer', 'build_attack_archer', 'build_summoner', 'build_push', 'build_fire'), summon_maps=('open_plain', 'dark_forest', 'ruined_fort', 'swamp', 'narrow_halls'), run_policy='balanced', sections=())

共 144 項指標，有目標的 126 項，偏離（⚠）52 項。
偏離 ＝ 超出目標區間的距離 ÷ 指標尺度（勝率 30 個百分點、輪數為區間寬度），可跨單位排序。

## 偏離最大的前 10 項

| # | 區塊 | 項目 | 數值 | 目標 | 偏離 |
|---|---|---|---|---|---|
| 1 | weapons | shotgun（build_blank_shotgun）DPR／單手劍 | 24.9% | 75–125%（對單手劍） | 2.00 |
| 2 | resources | build_fire × boss 法力不足回合 | 59.4% | ≤ 20%（參考） | 1.97 |
| 3 | matrix | 標準2：沒有任何前段類型的 build 數 | 5個 | 0（6.8 標準） | 1.67 |
| 4 | resources | build_summoner × boss 法力不足回合 | 47.4% | ≤ 20%（參考） | 1.37 |
| 5 | maps | dark_forest 我方勝率 | 96.7% | 35–65% | 1.06 |
| 6 | maps | narrow_halls 我方勝率 | 93.3% | 35–65% | 0.94 |
| 7 | resources | build_fire × single 法力不足回合 | 38.3% | ≤ 20%（參考） | 0.92 |
| 8 | matrix | build_fire 勝率 | 89.0% | 35–65% | 0.80 |
| 9 | maps | frozen_lake 我方勝率 | 88.3% | 35–65% | 0.78 |
| 10 | matrix | build_summoner 勝率 | 87.0% | 35–65% | 0.73 |

## 一、示範地圖（一般遭遇）（11/20 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| bridge_chasm 我方勝率 | 71.7% | 60 | 35–65% | ⚠ | 0.22 | 平手 0 |
| bridge_chasm 平均輪數 | 4.1輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| cliff_outpost 我方勝率 | 80.0% | 60 | 35–65% | ⚠ | 0.50 | 平手 0 |
| cliff_outpost 平均輪數 | 4.4輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| dark_forest 我方勝率 | 96.7% | 60 | 35–65% | ⚠ | 1.06 | 平手 0 |
| dark_forest 平均輪數 | 4.0輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| frozen_lake 我方勝率 | 88.3% | 60 | 35–65% | ⚠ | 0.78 | 平手 0 |
| frozen_lake 平均輪數 | 4.8輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| lava_crossing 我方勝率 | 76.7% | 60 | 35–65% | ⚠ | 0.39 | 平手 0 |
| lava_crossing 平均輪數 | 4.8輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| narrow_halls 我方勝率 | 93.3% | 60 | 35–65% | ⚠ | 0.94 | 平手 0 |
| narrow_halls 平均輪數 | 3.9輪 | 60 | 4–6 輪 | ⚠ | 0.06 | 一般遭遇 |
| oil_depot 我方勝率 | 55.0% | 60 | 35–65% | ✓ | 0.00 | 平手 0 |
| oil_depot 平均輪數 | 4.8輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| open_plain 我方勝率 | 58.3% | 60 | 35–65% | ✓ | 0.00 | 平手 0 |
| open_plain 平均輪數 | 4.6輪 | 60 | 4–6 輪 | ✓ | 0.00 | 一般遭遇 |
| ruined_fort 我方勝率 | 76.7% | 60 | 35–65% | ⚠ | 0.39 | 平手 0 |
| ruined_fort 平均輪數 | 3.8輪 | 60 | 4–6 輪 | ⚠ | 0.12 | 一般遭遇 |
| swamp 我方勝率 | 83.3% | 60 | 35–65% | ⚠ | 0.61 | 平手 0 |
| swamp 平均輪數 | 3.9輪 | 60 | 4–6 輪 | ⚠ | 0.06 | 一般遭遇 |

## 二、Boss 戰（7/13 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| dev_spirit Boss 勝率 | 36.7% | 60 | 35–65% | ✓ | 0.00 | 召喚包 |
| dev_spirit Boss 輪數 | 9.2輪 | 60 | 6–10 輪 | ✓ | 0.00 | 召喚包 |
| dev_summoner Boss 勝率 | 50.0% | 60 | 35–65% | ✓ | 0.00 | 召喚包 |
| dev_summoner Boss 輪數 | 10.3輪 | 60 | 6–10 輪 | ⚠ | 0.08 | 召喚包 |
| dev_summoner_bone Boss 勝率 | 60.0% | 60 | 35–65% | ✓ | 0.00 | 召喚包 |
| dev_summoner_bone Boss 輪數 | 12.8輪 | 60 | 6–10 輪 | ⚠ | 0.70 | 召喚包 |
| dev_bulwark Boss 勝率 | 15.0% | 60 | 35–65% | ⚠ | 0.67 | 無召喚對照包（B7） |
| dev_bulwark Boss 輪數 | 10.5輪 | 60 | 6–10 輪 | ⚠ | 0.12 | 無召喚對照包（B7） |
| dev_blaze Boss 勝率 | 21.7% | 60 | 35–65% | ⚠ | 0.44 | 無召喚對照包（B7） |
| dev_blaze Boss 輪數 | 8.8輪 | 60 | 6–10 輪 | ✓ | 0.00 | 無召喚對照包（B7） |
| dev_hawkeye Boss 勝率 | 26.7% | 60 | 35–65% | ⚠ | 0.28 | 無召喚對照包（B7） |
| dev_hawkeye Boss 輪數 | 9.7輪 | 60 | 6–10 輪 | ✓ | 0.00 | 無召喚對照包（B7） |
| 無召喚對照包合計 Boss 勝率 | 21.1% | 180 | 35–65% | ⚠ | 0.46 | B7 |

## 三、build 矩陣（23/48 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| build_push 勝率 | 71.0% | 100 | 35–65% | ⚠ | 0.20 | 偏強；英雄 DPR 7.5 |
| build_push 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_fire 勝率 | 89.0% | 100 | 35–65% | ⚠ | 0.80 | 偏強；英雄 DPR 15.5 |
| build_fire 前段類型數 | 7種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_storm 勝率 | 86.0% | 100 | 35–65% | ⚠ | 0.70 | 偏強；英雄 DPR 27.8 |
| build_storm 前段類型數 | 7種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_tank 勝率 | 67.0% | 100 | 35–65% | ⚠ | 0.07 | 偏強；英雄 DPR 3.6 |
| build_tank 前段類型數 | 2種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_ranged 勝率 | 69.0% | 100 | 35–65% | ⚠ | 0.13 | 偏強；英雄 DPR 11.6 |
| build_ranged 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_assassin 勝率 | 59.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 6.8 |
| build_assassin 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_support 勝率 | 68.0% | 100 | 35–65% | ⚠ | 0.10 | 偏強；英雄 DPR 5.4 |
| build_support 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_healer 勝率 | 81.0% | 100 | 35–65% | ⚠ | 0.53 | 偏強；英雄 DPR 2.9 |
| build_healer 前段類型數 | 4種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_warlock 勝率 | 78.0% | 100 | 35–65% | ⚠ | 0.43 | 偏強；英雄 DPR 18.1 |
| build_warlock 前段類型數 | 4種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_guardian 勝率 | 66.0% | 100 | 35–65% | ⚠ | 0.03 | 偏強；英雄 DPR 3.8 |
| build_guardian 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_striker 勝率 | 73.0% | 100 | 35–65% | ⚠ | 0.27 | 偏強；英雄 DPR 12.8 |
| build_striker 前段類型數 | 3種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_trapper 勝率 | 75.0% | 100 | 35–65% | ⚠ | 0.33 | 偏強；英雄 DPR 6.7 |
| build_trapper 前段類型數 | 2種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_charger 勝率 | 57.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 7.3 |
| build_charger 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_banisher 勝率 | 78.0% | 100 | 35–65% | ⚠ | 0.43 | 偏強；英雄 DPR 15.2 |
| build_banisher 前段類型數 | 3種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_summoner 勝率 | 87.0% | 100 | 35–65% | ⚠ | 0.73 | 偏強；英雄 DPR 9.8 |
| build_summoner 前段類型數 | 6種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_gambler 勝率 | 62.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 6.8 |
| build_gambler 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_seer 勝率 | 54.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 7.6 |
| build_seer 前段類型數 | 0種 | 8 | 1–7 種（共 8） | ⚠ | 0.50 |  |
| build_bomber 勝率 | 72.0% | 100 | 35–65% | ⚠ | 0.23 | 偏強；英雄 DPR 13.4 |
| build_bomber 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_winged 勝率 | 60.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 6.5 |
| build_winged 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_telekinesis 勝率 | 83.0% | 100 | 35–65% | ⚠ | 0.60 | 偏強；英雄 DPR 12.4 |
| build_telekinesis 前段類型數 | 6種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_wallburn 勝率 | 68.0% | 100 | 35–65% | ⚠ | 0.10 | 偏強；英雄 DPR 8.8 |
| build_wallburn 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_detonator 勝率 | 82.0% | 100 | 35–65% | ⚠ | 0.57 | 偏強；英雄 DPR 19.9 |
| build_detonator 前段類型數 | 5種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| build_runeweaver 勝率 | 64.0% | 100 | 35–65% | ✓ | 0.00 | 正常；英雄 DPR 11.2 |
| build_runeweaver 前段類型數 | 1種 | 8 | 1–7 種（共 8） | ✓ | 0.00 |  |
| 標準1：所有類型都前段的 build 數 | 0個 | 23 | 0（6.8 標準） | ✓ | 0.00 |  |
| 標準2：沒有任何前段類型的 build 數 | 5個 | 23 | 0（6.8 標準） | ⚠ | 1.67 | build_assassin、build_support、build_charger、build_gambler、build_seer |

## 四、資源短缺（3/15 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| build_skill_archer × single 法力不足回合 | 0.0% | 230 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 90% |
| build_attack_archer × single 法力不足回合 | 0.0% | 173 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 82% |
| build_summoner × single 法力不足回合 | 3.0% | 165 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 100% |
| build_push × single 法力不足回合 | 0.0% | 260 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 22%；英雄勝率 75% |
| build_fire × single 法力不足回合 | 38.3% | 193 | ≤ 20%（參考） | ⚠ | 0.92 | 耐力不足 0%；英雄勝率 88% |
| build_skill_archer × area 法力不足回合 | 0.0% | 126 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 1%；英雄勝率 100% |
| build_attack_archer × area 法力不足回合 | 0.0% | 112 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 98% |
| build_summoner × area 法力不足回合 | 0.0% | 121 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 95% |
| build_push × area 法力不足回合 | 0.0% | 145 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 2%；英雄勝率 100% |
| build_fire × area 法力不足回合 | 1.8% | 112 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 100% |
| build_skill_archer × boss 法力不足回合 | 10.6% | 235 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 25% |
| build_attack_archer × boss 法力不足回合 | 0.0% | 215 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 0%；英雄勝率 42% |
| build_summoner × boss 法力不足回合 | 47.4% | 348 | ≤ 20%（參考） | ⚠ | 1.37 | 耐力不足 0%；英雄勝率 65% |
| build_push × boss 法力不足回合 | 0.0% | 320 | ≤ 20%（參考） | ✓ | 0.00 | 耐力不足 13%；英雄勝率 10% |
| build_fire × boss 法力不足回合 | 59.4% | 340 | ≤ 20%（參考） | ⚠ | 1.97 | 耐力不足 0%；英雄勝率 55% |

## 五、武器類型（5/33 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| arcane_blade（build_blank_arcane_blade）勝率 | 57.0% | 100 | 35–65% | ✓ | 0.00 | DPR 5.1 |
| axe（build_blank_axe）勝率 | 58.0% | 100 | 35–65% | ✓ | 0.00 | DPR 5.1 |
| crossbow（build_blank_crossbow）勝率 | 63.0% | 100 | 35–65% | ✓ | 0.00 | DPR 8.8 |
| dual_dagger（build_blank_dual_dagger）勝率 | 66.0% | 100 | 35–65% | ⚠ | 0.03 | DPR 6.9 |
| dual_pistol（build_blank_dual_pistol）勝率 | 52.0% | 100 | 35–65% | ✓ | 0.00 | DPR 4.0 |
| fist（build_blank_fist）勝率 | 60.0% | 100 | 35–65% | ✓ | 0.00 | DPR 6.2 |
| hammer（build_blank_hammer）勝率 | 65.0% | 100 | 35–65% | ✓ | 0.00 | DPR 6.6 |
| longgun（build_blank_longgun）勝率 | 57.0% | 100 | 35–65% | ✓ | 0.00 | DPR 7.2 |
| fire_staff（build_blank_mage）勝率 | 51.0% | 100 | 35–65% | ✓ | 0.00 | DPR 7.0 |
| pistol（build_blank_pistol）勝率 | 53.0% | 100 | 35–65% | ✓ | 0.00 | DPR 3.8 |
| scepter（build_blank_priest）勝率 | 49.0% | 100 | 35–65% | ✓ | 0.00 | DPR 5.3 |
| scythe（build_blank_scythe）勝率 | 59.0% | 100 | 35–65% | ✓ | 0.00 | DPR 5.7 |
| shotgun（build_blank_shotgun）勝率 | 32.0% | 100 | 35–65% | ⚠ | 0.10 | DPR 1.3 |
| spear（build_blank_spear）勝率 | 67.0% | 100 | 35–65% | ⚠ | 0.07 | DPR 6.7 |
| totem_staff（build_blank_totemist）勝率 | 48.0% | 100 | 35–65% | ✓ | 0.00 | DPR 4.9 |
| one_handed_sword（build_blank_warrior）勝率 | 57.0% | 100 | 35–65% | ✓ | 0.00 | DPR 5.1 |
| whip（build_blank_whip）勝率 | 64.0% | 100 | 35–65% | ✓ | 0.00 | DPR 4.7 |
| arcane_blade（build_blank_arcane_blade）DPR／單手劍 | 100.0% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| axe（build_blank_axe）DPR／單手劍 | 100.2% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| crossbow（build_blank_crossbow）DPR／單手劍 | 172.5% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| dual_dagger（build_blank_dual_dagger）DPR／單手劍 | 134.9% | 170 | 75–125%（對單手劍） | ⚠ | 0.39 | B16～B19 對照 |
| dual_pistol（build_blank_dual_pistol）DPR／單手劍 | 78.6% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| fist（build_blank_fist）DPR／單手劍 | 121.6% | 170 | 75–125%（對單手劍） | ✓ | 0.00 | B16～B19 對照 |
| hammer（build_blank_hammer）DPR／單手劍 | 128.4% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| longgun（build_blank_longgun）DPR／單手劍 | 140.9% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| fire_staff（build_blank_mage）DPR／單手劍 | 135.8% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| pistol（build_blank_pistol）DPR／單手劍 | 73.4% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| scepter（build_blank_priest）DPR／單手劍 | 103.2% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| scythe（build_blank_scythe）DPR／單手劍 | 111.2% | 170 | 75–125%（對單手劍） | ✓ | 0.00 | B16～B19 對照 |
| shotgun（build_blank_shotgun）DPR／單手劍 | 24.9% | 170 | 75–125%（對單手劍） | ⚠ | 2.00 | B16～B19 對照 |
| spear（build_blank_spear）DPR／單手劍 | 130.6% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| totem_staff（build_blank_totemist）DPR／單手劍 | 95.7% | 170 | — | — | — | 參考（非 B16～B19 對照） |
| whip（build_blank_whip）DPR／單手劍 | 91.5% | 170 | 75–125%（對單手劍） | ✓ | 0.00 | B16～B19 對照 |

## 六、召喚物（1/12 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| dev_spirit 一般戰召喚物被打倒 | 25.0% | 48 | 10–50%（B3） | ✓ | 0.00 | 45/60 場有召喚 |
| dev_spirit 一般戰灌注次數／有召喚場 | 0.3次 | 45 | — | — | — | 共 14 次（B5：3H 後頻率下降，無目標值） |
| dev_spirit Boss 戰召喚物被打倒 | 52.4% | 82 | ≤ 50%（B3） | ⚠ | 0.05 | 60/60 場有召喚 |
| dev_spirit Boss 戰灌注次數／有召喚場 | 0.2次 | 60 | — | — | — | 共 14 次（B5：3H 後頻率下降，無目標值） |
| dev_summoner 一般戰召喚物被打倒 | 36.4% | 44 | 10–50%（B3） | ✓ | 0.00 | 44/60 場有召喚 |
| dev_summoner 一般戰灌注次數／有召喚場 | 0.2次 | 44 | — | — | — | 共 10 次（B5：3H 後頻率下降，無目標值） |
| dev_summoner Boss 戰召喚物被打倒 | 50.0% | 60 | ≤ 50%（B3） | ✓ | 0.00 | 60/60 場有召喚 |
| dev_summoner Boss 戰灌注次數／有召喚場 | 0.1次 | 60 | — | — | — | 共 5 次（B5：3H 後頻率下降，無目標值） |
| dev_summoner_bone 一般戰召喚物被打倒 | 18.8% | 48 | 10–50%（B3） | ✓ | 0.00 | 39/60 場有召喚 |
| dev_summoner_bone 一般戰灌注次數／有召喚場 | 0.5次 | 39 | — | — | — | 共 19 次（B5：3H 後頻率下降，無目標值） |
| dev_summoner_bone Boss 戰召喚物被打倒 | 45.3% | 75 | ≤ 50%（B3） | ✓ | 0.00 | 60/60 場有召喚 |
| dev_summoner_bone Boss 戰灌注次數／有召喚場 | 0.2次 | 60 | — | — | — | 共 12 次（B5：3H 後頻率下降，無目標值） |

## 七、一輪（roguelite）（2/3 項偏離）

| 項目 | 數值 | 樣本 | 目標 | 狀態 | 偏離 | 備註 |
|---|---|---|---|---|---|---|
| 一輪勝率（balanced閃現） | 25.0% | 40 | 35–65% | ⚠ | 0.33 |  |
| Boss 勝率（打到 Boss 的輪） | 71.4% | 14 | 35–65% | ⚠ | 0.21 | 14/40 輪打到 Boss |
| 平均贏幾場 | 3.6場 | 40 | — | — | — | 現行靈感每勝 2 點；無目標值 |
