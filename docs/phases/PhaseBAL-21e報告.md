# Phase BAL-21e 報告｜1 階技能比值報表（只讀＋新腳本）

> 實作 agent，2026-11-12。規格：`docs/phases/PhaseBAL-21計畫.md` 第 0 節（Q8）、第 8 節。只讀量測，**沒有改任何內容與引擎**。
> 數值調整由使用者在數值工坊決定；本報告只列現況與建議，PM 與 agent 不試數值。

## 1. 交付

- 新腳本 `scripts/t1_skill_ratio.py`（子命令 `run`＝跑、`report`＝重印；結果 JSON 預設寫到系統暫存區 `t1_skill_ratio.json`，不進 repo；`--detail` 另印逐武器明細）。ruff check、ruff format --check、mypy 通過；沒有加測試。
- 指令：`UV_NO_SYNC=1 uv run python scripts/t1_skill_ratio.py run --jobs 4`（122 招、1079 組武器×招、每組 250 種子；程序池 4 約 10 分鐘），重印 `... report [檔] [--detail]`。

## 2. 量法（照 `核對-148示範招B案.md`）

- 靶場 `training_range`、`range_trial` 推薦配點（`recommended_allocation`，主角只帶受測那一招）、打普通木樁 (6,4)；近戰站 (6,5)、遠程站 (6,7)；每把開局武器（不含敵人專用與召喚物專用）250 個種子取平均，含失手。
- 比值＝（技能對木樁傷害 ÷ 花掉的 AP）÷（普攻對木樁傷害 ÷ AP）。只算受測木樁的損血；範圍招打到其他木樁不算。
- 「含持續」＝施放後主角再空過 4 輪的總損血（中毒、燃燒、表面、延遲段、召喚物的攻擊都算），只在技能有後續傷害時另跑。
- 條件類：「不成立」＝自然狀態（第 1 輪、背刺、落單這種自然成立的另做：等一輪、背後格放木樁、目標旁放敵方木樁）；「成立」＝施放前直接改狀態：目標加狀態（剩 2 回合）、表面、施放者格高度＋1、隱匿、疊層加滿、`moved_this_turn`、`collided_round`、目標血量降到門檻下、夾擊／並肩在對面格或身旁放一個我方木樁；`consume_status`（撕裂傷口）當成目標有該狀態。綁武器（`wielding_weapon`）不另跑，看那把武器的值。變奏每個另跑一次。腳本在施放前用引擎的 `condition_met`／`variant_holds` 檢查：**情境與條件不符 0 組**。
- 範圍：1 階、主動、武器技、非 `enemy_only` 共 122 招（遠程 45、近戰 77、法器 0）。

## 3. 先對 #148 的 4 招（250 種子，與 #148 逐字相同，含普攻每 AP）

| 招 | #148 記錄 | 本腳本 |
|---|---|---|
| 瞬步背刺 | 背後 1.26～1.34；背後被占 0.45～0.50；雙匕首 0.65／0.26 | 1.26～1.34；0.45～0.50；0.65／0.26 |
| 先發制人 | 第 1 輪 1.38～1.48；第 2 輪 0.63～0.67；雙匕首 0.72／0.32 | 1.38～1.48；0.63～0.67；0.72／0.32 |
| 淬毒箭 | 直接 0.58～0.61；含中毒 1.29～1.79 | 0.58～0.61；1.29～1.79 |
| 燧石飛刃 | 0.83～0.86；有油含燃燒 1.50～1.97 | 0.83～0.86；1.50～1.97 |

## 4. 摘要表（遠程在前；`report` 原樣輸出）

種子 250／組；含持續＝施放後 4 輪；
比值＝技能每 AP ÷ 普攻每 AP；範圍是一般武器（不含雙匕首與綁定武器）
直接／含持續＝無條件或條件不成立；成立＝條件或變奏成立；綁定武器＝不成立情境下那把武器

### 遠程（45 招）

| 招 | AP | 形狀 | 條件 | 直接 | 含持續 | 成立 直接 | 成立 含持續 | 雙匕首 | 綁定武器 |
|---|---|---|---|---|---|---|---|---|---|
| 雙槍連射 `skill_akimbo_burst` | 2 | single | 綁 dual_pistol | 0.56～0.57 | — | — | — | — | dual_pistol 1.04 |
| 穿甲箭 `skill_armor_piercing_arrow` | 2 | single | 無 | 0.68～0.70 | — | — | — | — | — |
| 燃燒彈 `skill_blazing_round` | 2 | single | 無 | 0.92～0.95 | 1.11～1.25 | — | — | — | — |
| 交叉火網 `skill_crossfire` | 2 | single | target_has_status:slow | 0.50 | — | 0.99 | — | — | — |
| 火焰箭矢 `skill_fire_arrow` | 1 | single | 無 | 0.75～0.77 | — | — | — | — | — |
| 照火追射 `skill_flare_shot` | 2 | single | target_has_status:burning | 0.50 | — | 1.07～1.09 | — | — | — |
| 專注一擊 `skill_focused_shot` | 2 | single | stack:focus | 0.73～0.76 | — | 1.09～1.12 | — | — | — |
| 碎霜射擊 `skill_frost_snap` | 2 | single | target_has_status:frozen | 0.50 | — | 1.17～1.19 | — | — | — |
| 鉤索箭 `skill_grapple_arrow` | 1 | single | 無 | 0.35～0.36 | — | — | — | — | — |
| 高處狙擊 `skill_high_ground_shot` | 2 | single | height_advantage | 0.50 | — | 0.87～0.97 | — | — | — |
| 燧石飛刃 `skill_oil_spark_throw` | 2 | single | 變奏 oil_spark | 0.83～0.86 | 0.83～0.86 | oil_spark 0.83～0.86 | oil_spark 1.50～1.97 | — | — |
| 監視射擊 `skill_overwatch` | 1 | self | 無 | 0.00 | — | — | — | — | — |
| 穿透射擊 `skill_piercing_shot` | 2 | line | 無 | 0.50 | — | — | — | — | — |
| 趁亂釘射 `skill_pinning_shot` | 2 | single | target_collided | 0.50 | — | 1.12～1.13 | — | — | — |
| 點射 `skill_pinpoint_shot` | 2 | single | target_has_status:marked | 0.50 | — | 1.24～1.36 | — | — | — |
| 近距轟擊 `skill_point_blank_blast` | 2 | single | 綁 shotgun | 0.53～0.54 | — | — | — | — | shotgun 1.03 |
| 快拔連射 `skill_quick_draw` | 2 | single | 綁 pistol | 0.59 | — | — | — | — | pistol 1.02 |
| 築高台 `skill_raise_perch` | 2 | cross | 無 | 0.00 | — | — | — | — | — |
| 漣射 `skill_ripple_shot` | 2 | single | target_on_surface:water | 0.50 | — | 1.12～1.13 | — | — | — |
| 聖別之箭 `skill_rng_consecrated_arrow` | 2 | single | target_has_status:marked | 0.50 | — | 1.02～1.12 | — | — | — |
| 下擊風箭 `skill_rng_downdraft_shot` | 1 | single | 無 | 0.64～0.67 | — | — | — | — | — |
| 疾風箭 `skill_rng_gale_arrow` | 1 | single | 無 | 0.35～0.36 | — | — | — | — | — |
| 斷腱射擊 `skill_rng_hamstring_shot` | 1 | single | 無 | 0.34～0.35 | — | — | — | — | — |
| 鷹眼標記 `skill_rng_hawkeye_mark` | 2 | single | height_advantage | 0.32～0.33 | 0.32～0.33 | 0.60～0.68 | 0.60～0.68 | — | — |
| 居高追獵 `skill_rng_high_mark_shot` | 2 | single | height_advantage、target_has_status:marked | 不可放 | — | 1.20～1.36 | — | — | — |
| 臨高點殺 `skill_rng_high_point_kill` | 2 | single | height_advantage、target_has_status:marked | 不可放 | — | 1.20～1.36 | — | — | — |
| 俯射箭雨 `skill_rng_plunging_volley` | 2 | cross | height_advantage | 0.27～0.28 | — | 0.50～0.57 | — | — | — |
| 聖光箭雨 `skill_rng_radiant_volley` | 2 | cross | 無 | 0.43～0.44 | — | — | — | — | — |
| 導雷弩矢 `skill_rng_static_bolt` | 2 | single | target_on_surface:water | 0.50 | — | 0.99～1.01 | — | — | — |
| 雷鳴箭 `skill_rng_thunder_arrow` | 1 | single | 無 | 0.75～0.77 | — | — | — | — | — |
| 毒霧箭 `skill_rng_toxic_volley` | 2 | cross | 無 | 0.27～0.28 | 0.60～0.81 | — | — | — | — |
| 淬毒箭 `skill_rng_venom_arrow` | 1 | single | 無 | 0.58～0.61 | 1.29～1.79 | — | — | — | — |
| 散彈驅離 `skill_scatter_shot` | 2 | single | 綁 shotgun | 0.89 | — | — | — | — | shotgun 0.91 |
| 煙幕箭 `skill_smoke_arrow` | 1 | square3 | 無 | 0.00 | 0.00 | — | — | — | — |
| 煙霧彈 `skill_smoke_bomb` | 1 | square3 | 無 | 0.00 | 0.00 | — | — | — | — |
| 遠距狙擊 `skill_sniper_shot` | 2 | single | 無 | 0.85～0.88 | — | — | — | — | — |
| 穩穩瞄準 `skill_steady_aim` | 1 | single | 無 | 0.64～0.67 | — | — | — | — | — |
| 火引箭靈 `skill_sum_ember_arrow` | 1 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 符箭喚靈 `skill_sum_spirit_arrow` | 1 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 雷鳴箭靈 `skill_sum_storm_arrow` | 1 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 鳴鏑喚鷹 `skill_sum_whistle_arrow` | 1 | ground_tile | 無 | 0.00 | 7.72～12.90 | — | — | — | — |
| 壓制射擊 `skill_suppressing_fire` | 2 | single | 綁 dual_pistol | 0.83～0.86 | 0.83～0.86 | — | — | — | dual_pistol 0.83 |
| 花式射擊 `skill_trick_shot` | 2 | single | 綁 pistol | 0.76～0.78 | 0.76～0.78 | — | — | — | pistol 0.76 |
| 隱匿 `skill_vanish` | 1 | self | 無 | 0.00 | — | — | — | — | — |
| 隱匿射擊 `skill_veiled_shot` | 2 | single | self_concealed | 0.50 | — | 1.12～1.25 | — | — | — |

遠程 × 武器（單體傷害招的直接比值；條件類取不成立）

| 武器 | 普攻每 AP | 單體傷害招 | ≥ 0.9 | 中位數 | 最高 |
|---|---|---|---|---|---|
| bow | 7.45 | 28 | 0 | 0.56 | 0.89 |
| crossbow | 6.14 | 28 | 0 | 0.56 | 0.89 |
| dual_pistol | 6.62 | 30 | 2 | 0.59 | 1.04 |
| longgun | 7.73 | 29 | 1 | 0.56 | 0.92 |
| pistol | 7.45 | 29 | 2 | 0.56 | 1.02 |
| shotgun | 4.62 | 29 | 3 | 0.58 | 1.03 |

### 近戰（77 招）

| 招 | AP | 形狀 | 條件 | 直接 | 含持續 | 成立 直接 | 成立 含持續 | 雙匕首 | 綁定武器 |
|---|---|---|---|---|---|---|---|---|---|
| 孤注一擲 `skill_all_in` | 2 | single | 無 | 1.17～1.24 | — | — | — | 0.59 | — |
| 堡壘突擊 `skill_bastion_strike` | 2 | single | 無 | 沒有可用武器 | | | | | |
| 破城衝撞 `skill_battering_ram` | 2 | single | 無 | 0.37～0.40 | — | — | — | 0.18 | — |
| 狂戰士之怒 `skill_berserker_rage` | 2 | single | 無 | 1.00～1.07 | — | — | — | 0.51 | — |
| 刃舞 `skill_blade_dance` | 2 | single | 綁 dual_dagger | 0.88～0.95 | 0.88～0.95 | — | — | 0.45 | dual_dagger 0.45 |
| 血祭重擊 `skill_blood_sacrifice` | 2 | single | 無 | 1.20～1.31 | — | — | — | 0.65 | — |
| 碎骨重擊 `skill_bone_crusher` | 2 | single | 無 | 0.73～0.77 | — | — | — | 0.37 | — |
| 碎骨追擊 `skill_bone_pursuit` | 2 | single | target_collided | 0.50 | — | 1.11～1.17 | — | 0.25 | — |
| 蠻牛衝陣 `skill_bull_rush` | 2 | ground_tile | 無 | 0.32～0.56 | — | — | — | 0.31 | — |
| 連環鞭 `skill_chain_lash` | 2 | single | 綁 whip | 0.56～0.59 | — | — | — | 0.28 | whip 1.07 |
| 蓄力斬 `skill_charged_cleave` | 2 | self | 無 | 0.00 | 0.46～0.51 | — | — | 0.00 | — |
| 衝勢劈砍 `skill_charging_strike` | 2 | single | moved_this_turn | 0.50 | — | 0.85～0.91 | — | 0.25 | — |
| 橫掃劈砍 `skill_cleave` | 2 | cone | 無 | 0.69～0.73 | — | — | — | 0.35 | — |
| 連擊終結 `skill_combo_finisher` | 2 | single | stack:combo_point | 0.63～0.67 | — | 1.30～1.37 | — | 0.32 | — |
| 交叉斬 `skill_crossing_slash` | 2 | single | from_behind | 0.25 | — | 0.57 | — | 0.25 | — |
| 換位重擊 `skill_decoy_swap` | 1 | single | 無 | 0.33～0.38 | — | — | — | 0.17 | — |
| 困獸旋斬 `skill_encircled_sweep` | 2 | ring | 無 | 0.48～0.51 | — | — | — | 0.26 | — |
| 處決 `skill_execute` | 2 | single | target_hp_below:400 | 不可放 | — | 1.00～1.07 | — | — | — |
| 先發制人 `skill_first_strike` | 2 | single | first_round | 0.63～0.67 | — | 1.38～1.48 | — | 0.32 | — |
| 連環快刺 `skill_flurry_jab` | 1 | single | 無 | 0.66～0.70 | — | — | — | 0.34 | — |
| 穿陣刺 `skill_formation_pierce` | 2 | line | 無 | 0.69～0.73 | — | — | — | 0.35 | — |
| 霜崖斬 `skill_frost_ledge_cleave` | 2 | single | 變奏 frost_edge、變奏 ledge_drop | 0.81～0.86 | 0.81～0.86 | frost_edge 0.81～0.86；ledge_drop 0.90～0.97 | frost_edge 0.81～0.86；ledge_drop 0.90～0.97 | 0.41 | — |
| 颶風踢 `skill_gale_kick` | 1 | single | 無 | 0.35～0.38 | — | — | — | 0.17 | — |
| 倒地補刀 `skill_ground_finish` | 2 | single | target_has_status:prone | 0.50 | — | 1.38～1.46 | — | 0.25 | — |
| 碎防拳 `skill_guard_breaker_fist` | 2 | single | 綁 fist | 0.63～0.67 | 0.63～0.67 | — | — | 0.32 | fist 0.63 |
| 護衛換位 `skill_guard_swap` | 1 | single | 無 | 不可放 | — | — | — | — | — |
| 絆腿鞭 `skill_hamstring_lash` | 2 | single | 綁 whip | 0.83～0.88 | 0.83～0.88 | — | — | 0.42 | whip 0.88 |
| 獵殺一擊 `skill_hunters_strike` | 2 | single | target_has_status:marked | 0.50 | — | 1.32～1.40 | — | 0.25 | — |
| 破冰重擊 `skill_icebreaker` | 2 | single | target_has_status:frozen | 0.50 | — | 1.17～1.23 | — | 0.25 | — |
| 鐵拳連打 `skill_ironclad_flurry` | 2 | single | 綁 fist | 0.53～0.57 | — | — | — | 0.25 | fist 1.03 |
| 蝕骨刺 `skill_marrow_thorn` | 2 | single | target_has_status:poison | 0.50 | — | 0.98～1.01 | — | 0.25 | — |
| 震擊 `skill_palm_strike` | 1 | single | 無 | 0.66～0.70 | — | — | — | 0.34 | — |
| 格擋反擊 `skill_parry_riposte` | 2 | self | 無 | 0.00 | 0.00 | — | — | 0.00 | — |
| 獵殺落單 `skill_pick_off` | 2 | single | target_isolated | 0.45～0.50 | — | 0.85～0.91 | — | 0.26 | — |
| 前後夾擊 `skill_pincer_strike` | 2 | single | flanked | 0.50 | — | 0.82～0.87 | — | 0.25 | — |
| 俯衝斬 `skill_plunging_strike` | 2 | single | height_advantage | 0.50 | — | 1.23～1.30 | — | 0.25 | — |
| 拖地摔 `skill_prone_drag` | 1 | single | target_has_status:prone | 0.00 | — | 2.91～4.87 | — | 0.00 | — |
| 踢翻 `skill_prone_kick` | 1 | single | target_has_status:prone | 0.00 | — | 0.00 | — | 0.00 | — |
| 追印絆擊 `skill_prone_mark_strike` | 2 | single | target_has_status:marked | 0.00 | — | 1.02～1.12 | — | 0.00 | — |
| 震地推倒 `skill_quake_topple` | 1 | single | 無 | 0.00 | — | — | — | 0.00 | — |
| 怒氣爆發 `skill_rage_unleashed` | 2 | single | stack:fury | 0.63～0.67 | — | 1.17～1.24 | — | 0.32 | — |
| 壁壘挑釁 `skill_rampart_jeer` | 2 | single | 綁 tower_shield | 0.83～0.88 | 0.83～0.88 | — | — | 0.42 | — |
| 收割弧 `skill_reaping_arc` | 2 | cone | 綁 scythe | 0.50 | — | — | — | 0.25 | scythe 0.85 |
| 放血斬 `skill_rending_strike` | 1 | single | 無 | 0.66～0.70 | 1.03～1.25 | — | — | 0.34 | — |
| 撤步斬 `skill_retreating_slash` | 2 | cone | 無 | 0.37～0.40 | 0.37～0.40 | — | — | 0.18 | — |
| 盾緣打擊 `skill_rim_strike` | 2 | single | 綁 round_shield | 0.58～0.62 | — | — | — | 0.29 | — |
| 裂風斬 `skill_rng_gale_cleave` | 2 | single | 無 | 0.69～0.73 | — | — | — | 0.35 | — |
| 審判斬 `skill_rng_judgment_cleave` | 2 | single | 無 | 0.69～0.73 | — | — | — | 0.35 | — |
| 碎岩擊 `skill_rock_smash` | 2 | single | target_has_status:prone | 0.58～0.62 | — | 0.99～1.08 | — | 0.29 | — |
| 符文斬 `skill_runic_cut` | 2 | single | 綁 arcane_blade | 0.58～0.62 | — | — | — | 0.29 | arcane_blade 1.05 |
| 撕裂傷口 `skill_rupture` | 2 | single | target_has_status:bleed | 0.00 | — | 0.55～0.60 | — | 0.00 | — |
| 灼斬 `skill_scorching_slash` | 2 | single | target_has_status:burning | 0.50 | — | 1.06～1.12 | — | 0.25 | — |
| 暗影突襲 `skill_shadow_ambush` | 2 | unit_then_tile | self_concealed | 0.37～0.40 | — | 0.79～0.89 | — | 0.18 | — |
| 瞬步背刺 `skill_shadow_backstab` | 2 | single | from_behind | 0.45～0.50 | — | 1.26～1.34 | — | 0.26 | — |
| 瞬影旋斬 `skill_shadow_whirl` | 2 | ground_tile | 無 | 0.41～0.46 | 0.41～0.46 | — | — | 0.21 | — |
| 盾擊 `skill_shield_bash` | 2 | single | 無 | 0.33～0.35 | 0.33～0.35 | — | — | 0.17 | — |
| 盾衝 `skill_shield_rush` | 2 | single | 綁 round_shield | 0.83～0.88 | — | — | — | 0.42 | — |
| 並肩斬 `skill_shoulder_strike` | 2 | single | adjacent_ally | 0.50 | — | 0.82～0.87 | — | 0.25 | — |
| 靈魂收割 `skill_soul_harvest` | 2 | single | 綁 scythe | 0.88～0.95 | 0.88～0.95 | — | — | 0.45 | scythe 0.94 |
| 魔刃湧動 `skill_spellblade_surge` | 2 | single | 綁 arcane_blade | 0.63～0.67 | 0.63～0.67 | — | — | 0.32 | arcane_blade 0.67 |
| 劍塚喚兵 `skill_sum_grave_blade` | 1 | ground_tile | 無 | 0.00 | 4.42～7.68 | — | — | 0.00 | — |
| 撼地立像 `skill_sum_quake_idol` | 1 | ground_tile | 無 | 0.00 | 3.18～5.59 | — | — | 0.00 | — |
| 影隨刃 `skill_sum_shadow_twin` | 1 | ground_tile | 無 | 0.00 | 3.80～6.61 | — | — | 0.00 | — |
| 號令先鋒 `skill_sum_vanguard_spirit` | 1 | ground_tile | 無 | 0.00 | 3.40～5.91 | — | — | 0.00 | — |
| 戰嚎喚狼 `skill_sum_war_howl` | 1 | ground_tile | 無 | 0.00 | 4.83～8.48 | — | — | 0.00 | — |
| 破甲擊 `skill_sunder_strike` | 1 | single | 無 | 0.54～0.58 | — | — | — | 0.28 | — |
| 潮斬 `skill_tide_cleave` | 2 | single | target_on_surface:water | 0.50 | — | 1.11～1.17 | — | 0.25 | — |
| 衝鋒撞擊 `skill_tiger_charge` | 2 | single | 無 | 0.37～0.40 | — | — | — | 0.18 | — |
| 塔盾猛擊 `skill_tower_slam` | 2 | single | 綁 tower_shield | 0.87～0.92 | — | — | — | 0.43 | — |
| 踩踏 `skill_trample` | 2 | single | target_has_status:prone | 0.50 | — | 1.38～1.46 | — | 0.25 | — |
| 雙牙 `skill_twin_fang` | 2 | single | 綁 dual_dagger | 0.56～0.59 | — | — | — | 0.54 | dual_dagger 0.54 |
| 騰躍 `skill_vault_leap` | 1 | ground_tile | 無 | 0.00 | — | — | — | 0.00 | — |
| 毒刃 `skill_venom_blade` | 1 | single | 無 | 0.60～0.62 | 1.16～1.48 | — | — | 0.31 | — |
| 靠牆盾擊 `skill_wall_brace_bash` | 2 | single | 變奏 braced | 0.73～0.77 | — | braced 0.73～0.77 | — | 0.37 | — |
| 鞭梢爆響 `skill_whip_crack` | 2 | single | 無 | 1.22 | — | — | — | — | — |
| 旋風斬 `skill_whirlwind` | 2 | ring | 無 | 0.48～0.51 | — | — | — | 0.26 | — |
| 狂野之刃 `skill_wild_blade` | 2 | single | 無 | 1.11～1.21 | — | — | — | 0.57 | — |

近戰 × 武器（單體傷害招的直接比值；條件類取不成立）

| 武器 | 普攻每 AP | 單體傷害招 | ≥ 0.9 | 中位數 | 最高 |
|---|---|---|---|---|---|
| arcane_blade | 6.49 | 53 | 8 | 0.61 | 1.27 |
| axe | 7.54 | 53 | 4 | 0.59 | 1.23 |
| dagger | 5.91 | 53 | 4 | 0.58 | 1.21 |
| dual_dagger | 10.19 | 54 | 0 | 0.29 | 0.65 |
| fist | 7.54 | 53 | 5 | 0.59 | 1.23 |
| greatsword | 9.74 | 53 | 4 | 0.59 | 1.23 |
| hammer | 9.63 | 53 | 4 | 0.59 | 1.20 |
| one_handed_sword | 7.54 | 53 | 4 | 0.59 | 1.23 |
| scythe | 7.32 | 53 | 7 | 0.61 | 1.31 |
| spear | 8.43 | 53 | 4 | 0.59 | 1.27 |
| whip | 5.59 | 54 | 9 | 0.62 | 1.28 |

### 法器（0 招）

| 招 | AP | 形狀 | 條件 | 直接 | 含持續 | 成立 直接 | 成立 含持續 | 雙匕首 | 綁定武器 |
|---|---|---|---|---|---|---|---|---|---|

### 低於 0.9 的招（直接傷害，取所有武器與情境的最高值仍 < 0.9）

| 大類 | 招 | 最高比值 | 類別 | 含持續最高 |
|---|---|---|---|---|
| 遠程 | 斷腱射擊 `skill_rng_hamstring_shot` | 0.35 | 無條件 | — |
| 遠程 | 鉤索箭 `skill_grapple_arrow` | 0.36 | 無條件 | — |
| 遠程 | 疾風箭 `skill_rng_gale_arrow` | 0.36 | 無條件 | — |
| 遠程 | 淬毒箭 `skill_rng_venom_arrow` | 0.61 | 無條件 | 1.79 |
| 遠程 | 下擊風箭 `skill_rng_downdraft_shot` | 0.67 | 無條件 | — |
| 遠程 | 穩穩瞄準 `skill_steady_aim` | 0.67 | 無條件 | — |
| 遠程 | 穿甲箭 `skill_armor_piercing_arrow` | 0.70 | 無條件 | — |
| 遠程 | 火焰箭矢 `skill_fire_arrow` | 0.77 | 無條件 | — |
| 遠程 | 雷鳴箭 `skill_rng_thunder_arrow` | 0.77 | 無條件 | — |
| 遠程 | 花式射擊 `skill_trick_shot` | 0.78 | 無條件 | 0.78 |
| 遠程 | 壓制射擊 `skill_suppressing_fire` | 0.86 | 無條件 | 0.86 |
| 遠程 | 遠距狙擊 `skill_sniper_shot` | 0.88 | 無條件 | — |
| 遠程 | 鷹眼標記 `skill_rng_hawkeye_mark` | 0.68 | 條件類 | 0.68 |
| 遠程 | 燧石飛刃 `skill_oil_spark_throw` | 0.86 | 條件類 | 1.97 |
| 遠程 | 毒霧箭 `skill_rng_toxic_volley` | 0.28 | 非單體 | 0.81 |
| 遠程 | 聖光箭雨 `skill_rng_radiant_volley` | 0.44 | 非單體 | — |
| 遠程 | 穿透射擊 `skill_piercing_shot` | 0.50 | 非單體 | — |
| 遠程 | 俯射箭雨 `skill_rng_plunging_volley` | 0.57 | 非單體 | — |
| 遠程 | 火引箭靈 `skill_sum_ember_arrow` | 0.00 | 召喚 | 0.00 |
| 遠程 | 符箭喚靈 `skill_sum_spirit_arrow` | 0.00 | 召喚 | 0.00 |
| 遠程 | 雷鳴箭靈 `skill_sum_storm_arrow` | 0.00 | 召喚 | 0.00 |
| 遠程 | 鳴鏑喚鷹 `skill_sum_whistle_arrow` | 0.00 | 召喚 | 12.90 |
| 遠程 | 監視射擊 `skill_overwatch` | 0.00 | 非傷害招 | — |
| 遠程 | 築高台 `skill_raise_perch` | 0.00 | 非傷害招 | — |
| 遠程 | 煙幕箭 `skill_smoke_arrow` | 0.00 | 非傷害招 | 0.00 |
| 遠程 | 煙霧彈 `skill_smoke_bomb` | 0.00 | 非傷害招 | 0.00 |
| 遠程 | 隱匿 `skill_vanish` | 0.00 | 非傷害招 | — |
| 近戰 | 盾擊 `skill_shield_bash` | 0.35 | 無條件 | 0.35 |
| 近戰 | 颶風踢 `skill_gale_kick` | 0.38 | 無條件 | — |
| 近戰 | 換位重擊 `skill_decoy_swap` | 0.38 | 無條件 | — |
| 近戰 | 破城衝撞 `skill_battering_ram` | 0.40 | 無條件 | — |
| 近戰 | 衝鋒撞擊 `skill_tiger_charge` | 0.40 | 無條件 | — |
| 近戰 | 破甲擊 `skill_sunder_strike` | 0.58 | 無條件 | — |
| 近戰 | 雙牙 `skill_twin_fang` | 0.59 | 無條件 | — |
| 近戰 | 盾緣打擊 `skill_rim_strike` | 0.62 | 無條件 | — |
| 近戰 | 毒刃 `skill_venom_blade` | 0.62 | 無條件 | 1.48 |
| 近戰 | 碎防拳 `skill_guard_breaker_fist` | 0.67 | 無條件 | 0.67 |
| 近戰 | 魔刃湧動 `skill_spellblade_surge` | 0.67 | 無條件 | 0.67 |
| 近戰 | 連環快刺 `skill_flurry_jab` | 0.70 | 無條件 | — |
| 近戰 | 震擊 `skill_palm_strike` | 0.70 | 無條件 | — |
| 近戰 | 放血斬 `skill_rending_strike` | 0.70 | 無條件 | 1.25 |
| 近戰 | 裂風斬 `skill_rng_gale_cleave` | 0.73 | 無條件 | — |
| 近戰 | 審判斬 `skill_rng_judgment_cleave` | 0.73 | 無條件 | — |
| 近戰 | 碎骨重擊 `skill_bone_crusher` | 0.77 | 無條件 | — |
| 近戰 | 絆腿鞭 `skill_hamstring_lash` | 0.88 | 無條件 | 0.88 |
| 近戰 | 壁壘挑釁 `skill_rampart_jeer` | 0.88 | 無條件 | 0.88 |
| 近戰 | 盾衝 `skill_shield_rush` | 0.88 | 無條件 | — |
| 近戰 | 交叉斬 `skill_crossing_slash` | 0.57 | 條件類 | — |
| 近戰 | 撕裂傷口 `skill_rupture` | 0.60 | 條件類 | — |
| 近戰 | 靠牆盾擊 `skill_wall_brace_bash` | 0.77 | 條件類 | — |
| 近戰 | 前後夾擊 `skill_pincer_strike` | 0.87 | 條件類 | — |
| 近戰 | 並肩斬 `skill_shoulder_strike` | 0.87 | 條件類 | — |
| 近戰 | 暗影突襲 `skill_shadow_ambush` | 0.89 | 條件類 | — |
| 近戰 | 蓄力斬 `skill_charged_cleave` | 0.00 | 非單體 | 0.51 |
| 近戰 | 格擋反擊 `skill_parry_riposte` | 0.00 | 非單體 | 0.00 |
| 近戰 | 撤步斬 `skill_retreating_slash` | 0.40 | 非單體 | 0.40 |
| 近戰 | 瞬影旋斬 `skill_shadow_whirl` | 0.46 | 非單體 | 0.46 |
| 近戰 | 困獸旋斬 `skill_encircled_sweep` | 0.51 | 非單體 | — |
| 近戰 | 旋風斬 `skill_whirlwind` | 0.51 | 非單體 | — |
| 近戰 | 蠻牛衝陣 `skill_bull_rush` | 0.56 | 非單體 | — |
| 近戰 | 橫掃劈砍 `skill_cleave` | 0.73 | 非單體 | — |
| 近戰 | 穿陣刺 `skill_formation_pierce` | 0.73 | 非單體 | — |
| 近戰 | 收割弧 `skill_reaping_arc` | 0.85 | 非單體 | — |
| 近戰 | 劍塚喚兵 `skill_sum_grave_blade` | 0.00 | 召喚 | 7.68 |
| 近戰 | 撼地立像 `skill_sum_quake_idol` | 0.00 | 召喚 | 5.59 |
| 近戰 | 影隨刃 `skill_sum_shadow_twin` | 0.00 | 召喚 | 6.61 |
| 近戰 | 號令先鋒 `skill_sum_vanguard_spirit` | 0.00 | 召喚 | 5.91 |
| 近戰 | 戰嚎喚狼 `skill_sum_war_howl` | 0.00 | 召喚 | 8.48 |
| 近戰 | 護衛換位 `skill_guard_swap` | 0.00 | 非傷害招 | — |
| 近戰 | 踢翻 `skill_prone_kick` | 0.00 | 非傷害招 | — |
| 近戰 | 震地推倒 `skill_quake_topple` | 0.00 | 非傷害招 | — |
| 近戰 | 騰躍 `skill_vault_leap` | 0.00 | 非傷害招 | — |

共 72 招（遠程無條件 12；遠程條件類 2；遠程非單體 4；遠程召喚 4；遠程非傷害招 5；近戰無條件 20；近戰條件類 6；近戰非單體 10；近戰召喚 5；近戰非傷害招 4）

條件檢查：施放前條件和情境不符 0 組

清單說明：「無條件」包含效果只綁武器加狀態的招（花式射擊、壓制射擊、碎防拳、魔刃湧動…），也包含綁副手、本表量不到加成的招（盾緣打擊、盾衝、壁壘挑釁）。「條件類」是條件或變奏成立時取最高值仍低於 0.9 的招。

## 5. 重點

1. **遠程沒有一招無條件的單體 1 階武器技 ≥ 0.9**：只有燃燒彈（限火器，0.92～0.95）和散彈驅離（霰彈槍 0.91，其他 0.89）勉強到線。1 AP 箭類 0.34～0.77；2 AP 無條件招 0.68～0.88。弓、弩沒有任何一招單體傷害招 ≥ 0.9（條件不成立時）。
2. **「基礎 1000‰＋條件 1300‰」這類 2 AP 招，不成立時一律是 0.50**（見表中「直接 0.50」的列）。成立時遠程 0.99～1.36、近戰 0.85～1.46。
3. **成立時仍 < 1.1 的條件類**（照 Q8 討論起點）：遠程有交叉火網 0.99、導雷弩矢 0.99～1.01、高處狙擊 0.87～0.97、鷹眼標記 0.60～0.68、照火追射 1.07～1.09；近戰有交叉斬 0.57、撕裂傷口 0.55～0.60、暗影突襲 0.79～0.89、前後夾擊與並肩斬 0.82～0.87、衝勢劈砍與獵殺落單 0.85～0.91、蝕骨刺 0.98～1.01、碎岩擊 0.99～1.08、處決 1.00～1.07、霜崖斬（崖頂）0.90～0.97。
4. **綁武器的加成在本命武器上只有 1.02～1.07**（雙槍連射、近距轟擊、快拔連射、連環鞭、鐵拳連打、符文斬），換別的武器是 0.53～0.62。
5. **雙匕首**：近戰單體傷害招中位數 0.29、最高 0.65（普攻一次打兩下，每 AP 10.19）。這是武器本身的問題，逐招調救不起來。
6. 近戰無條件的強招：孤注一擲 1.17～1.24、血祭重擊 1.20～1.31、狂野之刃 1.11～1.21、鞭梢爆響（限鞭）1.22、狂戰士之怒（滿血）1.00～1.07。

## 6. 建議（只寫建議；目標比值與數值由使用者在數值工坊定）

- **目標**：沿用 Q8 的討論起點：無條件單體招 ≥ 0.9；帶條件的招在條件成立時 ≥ 1.1。另建議「不成立時」設一條下限（例如 ≥ 0.6），避免 0.50 這種「條件沒中就虧一半」的設計。
- **調法**：
  - 不建議用 `skill_scaling.yaml` 的全域倍率：近戰幾招已經 1.1～1.3，全域拉高會一起放大。建議以「1 階遠程武器技」為一組（或逐招）調倍率，遠程先做。
  - 1 AP 箭類（0.34～0.77）與 2 AP 招分開看：1 AP 招多半帶控制（擊倒、推、拉、標記），可接受較低的直接傷害，建議目標另定。
  - 「1000＋1300 條件」這一型可以考慮把基礎段提高、條件段降低，總和不變。
  - 雙匕首另開題：調武器（例如技能對雙匕首的倍率），不逐招調。
- **後續量測（開發 PM 裁定，這次不做）**：1 階法器法術（`category: spell`、`weapon_req: focus`，84 招）沒量，建議下一段用同一支腳本加 `--category spell` 後量。

## 7. 沒量到的與限制

- **要副手的招**：堡壘突擊（`weapon_only` 只有圓盾、塔盾）沒有可用武器；盾緣打擊、盾衝、塔盾猛擊、壁壘挑釁綁盾牌的加成沒量到。原因：開局主角沒有副手，腳本只用開局武器。
- **護衛換位**要我方目標，木樁場景不可放（非傷害招）；**格擋反擊**要等木樁攻擊才會觸發，木樁不攻擊，所以是 0；**踢翻**只有撞上東西才有傷害，木樁旁沒有障礙，所以是 0。
- 召喚招的「含持續」是召喚物 4 輪內打這根木樁的總和，受站位和 AI 影響，只能當參考。
- 範圍招只算受測木樁；實戰打到多個目標時會更高。
- 「成立」是直接改狀態做出來的，不代表實戰的成立率。

## 8. 待 PM 決定

1. 「低於 0.9」的判法：取所有武器與情境的最高值；條件類只要成立時有一把武器 ≥ 0.9 就不列（開發 PM 已同意照這個做法）。
2. 成立情境的做法（目標狀態剩 2 回合、高度＋1、疊層加滿、夾擊與並肩改放我方木樁）是最保守的預設（開發 PM 已同意）。
3. 含持續一律算 4 輪、召喚物的攻擊也算進去（開發 PM 已同意）。
4. 是否另定「不成立時下限」與 1 AP 招的目標（第 6 節）。
5. 雙匕首要不要另開武器題。
6. 腳本留在 `scripts/`，結案時再決定要不要搬到 `scripts/archive/`（T6）。

## 使用者決定（2026-11-12，專案 PM 轉達）

使用者原話：「要改數值的都給我改就好 其他都按照建議」。專案 PM 的分配：目標比值（無條件單體 ≥ 0.9、條件成立 ≥ 1.1、條件不成立約 ≥ 0.6、1 AP 箭類約 ≥ 0.6）只當報表參考線，**不派 agent 調任何技能數值**；調法逐招或分組、不用全域倍率，數值工坊 NW-2（技能欄位）排最前；雙匕首另開武器題（轉玩法 PM）；1 階法器法術 84 招下一段補量（只出報表）。
