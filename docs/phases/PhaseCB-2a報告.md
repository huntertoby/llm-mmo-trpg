# Phase CB-2a 完成報告｜敵人招式數 #149 與模擬

基準 commit `36cfff47`（`hit_target` 8）。依 `docs/phases/PhaseCB-2a計畫.md` 實作。**沒有調平衡數值**；建議值只寫在本報告。

## 交付

| 項目 | 內容 | commit |
|---|---|---|
| `teleport_lethal_resist_bonus` 8 → 10 | `core.yaml`、`rules.py` 預設值、測試比對 15%（總 +12，自然 18 以上） | `a37ba061` |
| 補招、新招、詞綴帶招、冰鶴使緩速、霧影同步 | `content/units/*`、`content/skills/`（4 招）、`content/world/enemies.yaml`；3 個新測試檔 | `c0c96d0f` |
| 快照與換種子 | 見下 | `843313c9`、`feb521c7` |
| 模擬腳本 | `scripts/cb2a_sim.py` | `040fe8f5`、`feb521c7` |

## 逐條驗收

| 條件 | 結果 | 證據 |
|---|---|---|
| `ruff check` | 通過 | `All checks passed!` |
| `ruff format --check` | 通過 | `2258 files already formatted` |
| `uv run mypy` | 通過 | `no issues found in 1422 source files` |
| `lint-imports` | 通過 | `Contracts: 14 kept, 0 broken.` |
| `tests/content`、`engine`、`world`、`api`、`cli`、`sim`、`test_architecture.py`（`TRPG_FULL=1 -m "not llm"`） | 通過 | `9461 passed, 1 skipped, 4 xfailed`，加 1 個 `test_run_auto_is_deterministic_and_matches_the_library_run`；該項換 `VICTORY` 種子後與 `test_progress`、`test_save` 同跑 `59 passed`。沒有 `tests/ai` 目錄 |
| 3 張地圖以上 `--log-json` ＋ `replay` | 通過 | open_plain 7（90 動作）、oil_depot 13（79）、bridge_chasm 3（59）、swamp 21（56），都是「重播驗證通過」 |

### 行為一致測試

| 規格 | 測試 |
|---|---|
| 3 招新招的傷害與緩速、點燃、中毒（實際跑引擎） | `tests/engine/test_enemy_skills_149.py::test_new_move_deals_damage_and_applies_its_status` |
| 黏液不留表面、射程 3 | `test_slime_leaves_no_surface`、`test_slime_has_range_three` |
| 冰鶴使命中確實緩速（拿弓） | 同上的 `frost_crane_archer` 列、`test_frost_crane_slows_with_a_bow` |
| 碎晶之主三柱階段可施放 3 招（另含灰燼之心、霧鎖真人第 1 階段） | `test_first_boss_phase_can_cast_three_moves` |
| 帶 A 詞綴的精英多 1 招且能施放 | `test_affix_adds_one_castable_move` |
| 招數達標（例外名單寫在測試內） | `tests/content/test_enemy_skill_count_149.py`（`test_every_first_season_enemy_has_enough_moves`、`test_random_elites_reach_three_moves`、`test_fixed_elites_reach_three_moves`、`test_rookies_stay_as_they_were`、`test_three_pillars_phase_has_three_moves`） |
| AI 實際選得到每招（跑 AI） | `tests/world/test_enemy_ai_moves_149.py`；選不到的見「補了卻很少放」 |
| 霧影同步 | `tests/world/test_mist_shade.py`、`test_the_mist_shade_copies_the_new_move` |
| 傳送 15% | `tests/engine/test_displace_others.py::test_the_success_chances_at_the_same_level_are_75_65_and_15_percent`、`test_a_deadly_landing_needs_a_high_roll` |

### 受影響的既有功能

| 項目 | 結果 |
|---|---|
| AI 評分、敵人技能驗證器、內容 digest | 不用改程式，`trpg content check` 與測試通過 |
| 模擬用 build | 不用改 |
| `WORLD_RULES_VERSION` | 沒有加一 |
| 動畫 | 沒動前端；新招走既有片段 |
| 異形 | `test_new_move_...`、`test_first_boss_phase_...` 在引擎層驗證異形（蛞蝓、蝠、硫煙獸、灰燼之心）可施放 |

## 最終招單

每筆「新增」是加在現有招式後面。

| 敵人 | 新增 | 來源／備註 |
|---|---|---|
| 青霧道童 sect_acolyte | guardian_aegis | 盤點 |
| 持劍弟子 sect_swordsman | rending_strike | 盤點 |
| 劍陣弟子 sect_array_disciple | pincer_strike | 盤點 |
| 傀儡師 sect_puppeteer | wil_void_pull | 盤點 |
| 霧中劍客 sect_mist_swordsman | shadow_ambush（霧影同步） | 盤點 |
| 霧狼 mist_wolf | pincer_strike | 盤點 |
| 山豹 mountain_leopard | rending_strike | 盤點 |
| 石背熊 stoneback_bear（焦石背繼承） | bone_crusher | 盤點 |
| 碎晶傀儡 shard_golem | quake_wave | 盤點 |
| 盜賊 bandit | rending_strike、venom_blade | 盤點 |
| 盜賊弓手 bandit_archer（火槍手繼承） | rng_venom_arrow | 盤點 |
| 盜賊盾衛 bandit_shieldbearer | taunting_roar | 盤點 |
| 盜賊隊長 bandit_captain（鍛疤繼承） | gale_kick、rending_strike | 盤點 |
| 餘燼蜥 ember_lizard | kindle_pop | 盤點 |
| 殼縫餘燼蜥 heart_ember_lizard | kindle_pop | 盤點 |
| 寒燼蜥 frost_ember_lizard | frost_touch | 盤點 |
| 火塵蝠 fire_dust_bat | **cinder_dive 俯衝灑火塵（新）** | 規格指定新招，取代盤點的 ashen_oath |
| 噴岩龜 lava_tortoise | fire_bolt | 盤點 |
| 熔核蛞蝓 magma_slug | **slime_glob 黏液（新）** | 規格指定 |
| 熔岩甲蟲 lava_beetle（雷殼繼承） | parry_riposte | 盤點 |
| 熔爐母獸 furnace_matriarch | ember_bite | 盤點 |
| 硫煙獸 sulfur_beast | **venom_gore 毒牙頂撞（新）** | 規格指定新招，取代盤點的 wild_roar |
| 焦岩巨像 scorched_colossus | bone_crusher | 盤點 |
| 熔核領主 molten_lord | lava_spout | 盤點 |
| 霧鎖真人 劍陣 | guardian_aegis | 盤點 |
| 霧鎖真人 歸一 | whirlwind | 盤點 |
| 灰燼之心 殼 | ashen_oath | 盤點 |
| 碎晶之主 三柱 | shard_erosion、shock_follow | 盤點 |
| 詞綴 霧隱／連心／硬殼 | mist_shift／guardian_aegis／parry_riposte | 規格 |
| 冰鶴使 frost_crane_archer | annotated_frost → **frost_feather 寒羽霜箭（新）** | 冰鶴使緩速修正，見下 |

**實際補招**：31 筆（沿用 28 ＋新招 3），加 3 個詞綴、1 招霧影同步、1 招冰鶴使換招。規格寫的「其餘 31 招」與「3 招新招」合起來會是 34，實際總數 34 扣掉新手盜賊 3 招後是 31，新招包含在內。

**與盤點不同的逐項理由**

1. `bandit_rookie`（2 招）、`bandit_archer_rookie`（1 招）不補：18.2 例外。
2. 火塵蝠、硫煙獸改用新招：規格「三招新招」。
3. 新增第 4 招 `skill_frost_feather`（`enemy_only`）：規格寫要修但沒寫方法。`annotated_frost` 的緩速綁法書，弓拿不到；沒有弓能用的無條件緩速招。傷害、射程、費用照舊，骨架由 `combo` 改 `strike`（`combo` 要有條件）。寒燼蜥照 PM 決定不動。
4. 其餘 28 招照盤點。盤點備選的 `skill_swaps`（鍛疤換 whip_crack）沒有做，鞭能用 rending_strike。

**新招預算**（`trpg skills budget`，都標 `enemy_only`、rare）

| 招 | 效果 | AP／費用 | 預算比 |
|---|---|---|---|
| slime_glob 黏液 | 單體射程 3、1d8 地、緩速 2 回合、不留表面 | 1／法力 3、冷卻 2 | 91.3% |
| cinder_dive 俯衝灑火塵 | 十字射程 3、1d6 火、燃燒 2 回合、無位移 | 2／法力 5、冷卻 2 | 70.6% |
| venom_gore 毒牙頂撞 | 近戰 ×1.1、中毒 3 回合 | 2／耐力 10、冷卻 1 | 71.1% |
| frost_feather 寒羽霜箭 | 單體射程 5、3d8 冰、緩速 1 回合 | 2／法力 6、冷卻 4 | 91.5% |

黏液的縮放屬性依 `skill_scaling.yaml` 只能是智力；蛞蝓智力 4，命中偏低，模擬每單位每場仍放 1.40 次。

## 快照與改動的測試

**CLI 快照（24 個雜湊，1 個不變）逐類確認**：
- 舊內容（B）＋舊快照：25 全過（基準沒問題）。
- 舊內容＋只加 4 招新技能檔：`skills_list`、`skills_show_all/*` 共 17 個變，7 個 `battle_*` 不變 → 技能清單的變動來自新招。
- 新內容但傳送加值改回 8：只有 `skills_list`、`skills_show_all/00` 變 → 傳送加值影響描述文字，不影響 7 場戰鬥。
- 7 個 `battle_*` 的變動因此只來自補招。

**內容或斷言直接相關的改動**

| 檔案 | 改動 |
|---|---|
| `tests/engine/helpers.py` `template()` | 基底是 `bandit` 時技能預設清空。盜賊在測試裡是沒技能的通用替身（換弓等），補招後 `放血斬` 過不了武器檢查 |
| `test_skill_ai_scenarios` | 斷言改成盜賊、盾衛有招，新手盜賊沒招 |
| `test_status_determinism` | `control_dr` 允許 `mental`（盾衛 taunting_roar 帶入，這類別本來就存在） |
| `test_coverage` | 變體 `skill_swaps` 算被裝備（`frost_feather` 只由變體裝備） |
| `test_skill_scaling` | 技能數 397 → 401 |
| `test_world_enemies`、`test_cloud_ridge_mechanics` | 霧隱多一招；冰鶴使改新招；弓手不再能套硬殼 |
| `test_displace_others` | 傳送 25% → 15%、門檻自然 16 → 18、總抵抗 10 → 12 |

**換種子**（AI 軌跡改變，斷言與重播比對都沒動；確定性沒放寬）

| 測試 | 舊 → 新 |
|---|---|
| `test_boss_phases` 雲頂觀 | 0、5 → 0、1 |
| `test_gamble` | 17、27 → 17、37 |
| `test_displace_ai` 虛空互換 | 55 → 90 |
| `test_oaths` 自動戰鬥 | 0、1 → 0、6 |
| `test_hurl_object` | 14 → 38 |
| `test_rule_changes` 殘影 | 1 → 0 |
| `test_rewrite_primitives` build_support | oil_depot 4 → 0 |
| `test_scene_ai` 穿透 | 2 → 3 |
| `test_reaction_events` 悲憤 | 5 → 2 |
| `test_self_moves` | ruined_fort 1 → 3 |
| `test_combo_resources` seer | 2、2 → mana 9、cooldown 0 |
| `test_basic_actions_cli` | open_plain 60 → 18、419 → 730；ruined_fort 1 → 11 |
| `test_demo_maps` | bridge_chasm 3 → 4 |
| `test_striker_trapper_battle` | 115 → 46 |
| `VICTORY`（`tests/roguelite/helpers.py`） | 3 → 1（種子 3 的 build_fire 打到第 5 場就輸） |

沒有新增複雜度類 noqa。`scripts/cb2a_sim.py` 有一個 `# noqa: PLW0603`（多行程初始化用的模組全域，不是複雜度類）。

## 模擬

**方法**：`scripts/cb2a_sim.py`，只跑一次。A、B 的內容從 git 取出放在 `.scratch_cb2a/`（未 commit）：B＝`36cfff47` 的 `content/`；A＝B 再把 `hit_target` 改回 11。C＝目前內容。一般遭遇（雲嶺、荒原）每地點 8 build × 4 種子；懸賞 6 張 × 8 build × 5 種子（「精英」取懸賞）；頭目 3 個 × 8 build × 10 種子；5 張示範地圖 × 20 種子。新手戰用 `scripts/archive/f4_newbie_sim.py 10`（每種開局 10 人，以 `TRPG_CONTENT_DIR` 切換）。

### 勝率／平均輪數

| 類別 | A | B | C | 場數 |
|---|---|---|---|---|
| 雲嶺一般 | 98%／4.8 | 97%／4.0 | 97%／4.1 | 320 |
| 荒原一般 | 80%／5.0 | 73%／4.2 | 70%／4.1 | 384 |
| 懸賞精英 | 92%／4.9 | 88%／4.6 | 83%／4.6 | 240 |
| 霧鎖真人（6 級） | 95%／9.1 | 99%／7.5 | 95%／9.6 | 80 |
| 灰燼之心（9 級） | 78%／10.8 | 61%／10.9 | 71%／11.0 | 80 |
| 碎晶之主（10 級） | 84%／12.9 | 71%／12.1 | 69%／13.1 | 80 |
| 碎晶之主第 1 階段（到第 2 階段比例／輪數） | 100%／2.3 | 100%／2.2 | 100%／2.3 | 80 |

**4 張示範地圖**（目標 35–65%、平均 4–6 輪）

| 地圖 | A | B | C |
|---|---|---|---|
| bridge_chasm | 60%／4.5 | 65%／3.8 | 55%／3.8 |
| oil_depot | 50%／5.0 | 65%／3.8 | 40%／3.9 |
| ruined_fort | 40%／4.1 | 20%／3.5 | 25%／3.5 |
| swamp | 40%／5.2 | 20%／3.6 | 35%／3.9 |
| （open_plain，參考） | 50%／4.2 | 60%／3.6 | 60%／3.8 |

C 組輪數全都低於 4；ruined_fort 勝率低於 35%。

### 控制與推擠（發動次數／成功率）

世界戰鬥合計（一般、懸賞、頭目）。

| 項目 | A | B | C |
|---|---|---|---|
| 控制對抗：敵打我 | 479／75% | 513／86% | 1849／86% |
| 控制對抗：我打敵 | 1380／73% | 1653／84% | 1623／83% |
| 推擊 shove：敵打我 | 1427／66% | 1122／78% | 831／80% |
| 推擊 shove：我打敵 | 695／75% | 501／84% | 448／86% |
| 絆倒 trip：敵打我 | 26／73% | 24／75% | 57／67% |
| 絆倒 trip：我打敵 | 69／61% | 58／72% | 62／74% |
| 擊倒 knock_prone：敵打我 | 0／— | 0／— | 56／75% |

門檻 11 → 8 讓控制與推擠成功率上升約 10～12 個百分點，補招不影響成功率。C 組「敵打我」的次數暴增是流血（bleed 985 次）與中毒（poison 462 次）：`rending_strike`、`venom_blade`、`rng_venom_arrow` 帶來的，都是持續傷害；定身、標記、嘲諷的次數在 B、C 之間幾乎不變。敵人推擊變少，是因為有招可放，brute 改放技能。

### 新手戰（6F-4 門檻：主角倒下 ≤ 40%、打贏 ≥ 8/10）

| 開局／步驟 | A | B | C |
|---|---|---|---|
| 火焰 渡口／竹林／梯田 倒下 | 10／20／20% | 30／40／22% | 30／40／30% |
| 匕首 倒下 | 0／0／10% | 0／10／10% | 0／10／40% |
| 巨劍 倒下 | 10／30／40% | 10／20／50% | 10／33／**66%** |
| 弓 倒下 | 0／10／20% | 10／11／11% | 0／0／10% |

C 組打贏全都 ≥ 9/10；**巨劍在雨中梯田倒下 66%，超過 40%**。B 組（只有門檻 8）已經 50%，補招再加重。

### 補了卻很少放

全部 35 列見模擬輸出；每單位每場 < 0.1 的只有兩項，空地圖的 AI 測試另有 kindle_pop 選不到。

| 招 | 每單位每場 | 說明 |
|---|---|---|
| 碎晶之主三柱 shock_follow | 0.00（0 次） | 同階段的招總是更划算；這一招是空欄位 |
| 霧鎖真人歸一 whirlwind | 0.04（3 次） | 只有第 3 階段用得到 |

偏低但會放：霧狼 pincer_strike 0.19、冰鶴使 frost_feather 0.23（冷卻 4）、餘燼蜥 kindle_pop 0.26～0.29（要目標帶燃燒，真實遭遇裡有放）、熔爐母獸 ember_bite 0.12（樣本 8 名）。碎晶傀儡 quake_wave 沒有樣本（這次取樣的遭遇沒抽到）。傀儡師樣本也只有 8 名（2.25）。

`tests/world/test_enemy_ai_moves_149.py` 的 `RARELY_CHOSEN` 列了 `ember_lizard`、`heart_ember_lizard` 的 kindle_pop 與 `rift_shard_lord` 的 shock_follow（空地圖對 2 名英雄、40 種子選不到）。

### AI 訊號（4 張示範地圖加 open_plain）

| 項目 | A | B | C |
|---|---|---|---|
| 瞄準：我方（次數／每回合） | 46／5% | 1／0% | 1／0% |
| 瞄準：敵方 | 14／1% | 8／1% | 3／0% |
| 推擊：archer（次數，占回合） | 24（3%）／致死 1 | 3（0%）／致死 3 | 4（1%）／致死 2 |
| 推擊：brute | 472（45%）／致死 44 | 246（29%）／致死 27 | 146（17%）／致死 29 |
| 推擊：cunning | 12（5%）／致死 0 | 5（3%）／致死 0 | 12（6%）／致死 1 |
| 推擊：guard | 19（23%）／致死 0 | 0／0 | 1（2%）／致死 1 |

門檻 8 後瞄準幾乎消失（`aim_hit_permille` 500，命中率很少低於 50%）。弓手只在能推進致命地形時才推（推了幾乎都死），brute 大量推，個性差異還在，但弓手的樣本很小。「致死」是推擊成功後 8 個事件內目標倒下的近似值。

### 與 BAL 既有目標的差距

| 目標 | C 組 | 差距 |
|---|---|---|
| 一般遭遇 4～6 輪 | 雲嶺 4.1、荒原 4.1 | 在下緣 |
| Boss 6～10 輪 | 霧鎖 9.6、灰燼之心 11.0、碎晶之主 13.1 | 後兩者偏長（A 組也一樣：10.8、12.9） |
| 霧鎖真人 70%（5F-2b） | 95% | 偏高，A、B 組也是 95～99%，不是補招造成 |
| 灰燼之心 70～80%（5F-5） | 71% | 達標（B 組 61% 反而被補招拉回，原因沒查，可能是樣本） |
| 碎晶之主 70%（5F-3） | 69% | 接近；「每個 build ≥ 40%」這次沒分 build 統計 |
| 同級約 80%（7.8） | 雲嶺 97%、荒原 70% | 雲嶺偏易、荒原略難 |
| 示範地圖 4–6 輪、35–65% | 見上 | 輪數全低於 4；ruined_fort 25% |

## 建議數值（未修改，由 PM 決定）

1. 雨中梯田（新手第 3 步 terrace_clash）：巨劍倒下 66%。建議敵方 HP −10% 或減 1 人，用 `scripts/archive/f4d_terrace_sweep.py` 掃。
2. `shock_follow` 換掉：三柱階段第 3 招改一招 AI 會選、傷害不高於 `shard_erosion` 的招；第 1 階段進度不受影響。
3. `whirlwind` 換成盤點備選 `execute`，或接受只在第 3 階段偶爾出現。
4. `aim_hit_permille` 500 → 700，讓瞄準回到 A 組的水準（需要重跑示範地圖）。
5. 荒原一般 70%、雲嶺 97%：先不動，等 CB-2c 之後一起看。

## 待 PM 決定

1. **硬殼的 `parry_riposte` 限近戰**：規格寫「過不了武器相容檢查就換不限武器的同主題招」，18.2 又明寫這招。固定指定（鍛疤、熔核領主）都過得了，隨機混入時遠程武器（火塵蝠、噴岩龜、火槍手）不能再套硬殼（各自仍有「再生的」，一樣到 3 招）。我保留 18.2 的 `parry_riposte`，和「狂暴的」「熾熱的」一致。若要換，候選是 `ember_ward` 或 `frost_armor_seal`（不限武器的護盾招），一行 yaml。
2. 招重複造成詞綴不可套用：甲蟲、雷殼甲蟲不能套硬殼（已有 parry_riposte），道童不能套連心，母獸不能套熾熱。這是規格的做法 A 本來就有的結果。
3. 冰鶴使的 `frost_feather` 是第 4 招新招，名字與數值請玩法 PM 過目；動畫走既有片段。
4. 規格的「其餘 31 招」數字：實際沿用 28 招＋新招 3 招＝31。
5. `rules.py` 的 `teleport_lethal_resist_bonus` 預設值同步改 10（規格只寫 yaml，避免兩處不一致）。
6. `tests/engine/helpers.py` 的 `template("bandit")` 預設清空技能：測試裡的「盜賊」不再反映正式範本。之後若要測正式盜賊要用 `library().unit("bandit")`。
7. 新手戰是否要在 CB-2 之後重設 6F-4 門檻（巨劍的梯田，見建議 1）。
8. 蛞蝓的黏液智力 4 命中偏低、依 `skill_scaling.yaml` 只能縮放智力；要不要給敵人專用招例外。
9. 碎晶之主的 build 分布沒量（`scripts/archive/season_boss_sim.py` 可量），補招後建議 PM 排一次。
