# Phase SR-1 報告｜1 階法器法術 84 招比值補量（只出報表）

> 實作 agent（Opus 5.5），2026-11-13。依據：專案 PM「補量法器法術」、`docs/phases/PhaseBAL-21e報告.md`（比值定義、第 6 節後續量測）、`docs/phases/PhaseNW-2c報告.md`（核心搬家、參考線 D4）、`docs/phases/PhaseNW-2計畫.md` 第 71、170 行。
> **沒有改任何數值、沒有動 `content/`**；目標比值與數值由使用者在數值工坊決定，本報告只列現況與建議。

## 1. 交付

| commit | 內容 |
|---|---|
| `3b4bef66` | `src/trpg/sim/skill_ratio.py`：`CATEGORIES`、`is_measurable(skill, category="weapon")`、`tier1_skills(lib, category)`（`tier1_weapon_skills` 保留）；法器站位 `STAND["focus"]＝(6,7)`、`ALLY_BESIDE_CASTER["focus"]＝(7,7)`；法術才有的兩種條件可做成「成立」（`cast_tag_this_turn`：主角本回合加標籤；`on_own_rune`：目標格放一個主角自己的符文，剩 2 回合）。`scripts/t1_skill_ratio.py`：`run`／`report` 加 `--category weapon|spell`（預設 `weapon`）；spell 的 JSON 多 `category`、meta 多 `skeleton`／`element`，報表只印法器一節，另印「參考線外」與四種分組摘要。`tests/sim/test_skill_ratio.py` 加 5 項（共 18 項） |
| （本 commit） | 本報告、上手筆記 |

指令：`UV_NO_SYNC=1 uv run python scripts/t1_skill_ratio.py run --category spell --jobs 4 [--out 檔]`（84 招、420 組武器×招、每組 250 種子）；重印 `... report [檔] --category spell [--detail]`。JSON 預設寫到系統暫存區 `t1_skill_ratio_spell.json`，不進 repo。

## 2. 量法與法術的基準

- **範圍**：1 階、主動、`category: spell`、`weapon_req: focus`、非敵人專用，共 84 招；每招 × 5 把開局法器（`fire_staff`、`frost_staff`、`lightning_staff`、`scepter`、`totem_staff`）。`weapon_req: any` 的 1 階主動法術 68 招**不在本段**（見待決 2）。
- **基準**：BAL-21e 沒有另外定義法術的基準；但核心本來就把「法器」列為第三個大類（`CLASS_ORDER`、`CLASS_ZH`），比值定義是「技能每 AP ÷ **同一把武器**的普攻每 AP」。所以照最保守、可解釋的做法：**法術的基準＝同一把法器的普攻每 AP**（法杖 1d6＋INT、權杖 1d6＋WIS＋祝福 3、圖騰杖 1d6＋WIL）。主角站 (6,7)，同靶場試打 `tests/world/test_opening.py` 的 `TRIAL_STAND["focus"]`；配點照 `recommended_allocation`（只帶受測那一招）。
- 其餘照 BAL-21e：250 種子取平均（含失手）、「含持續」＝施放後 4 輪、條件類分「不成立／成立」、變奏各跑一次「成立」、施放前用引擎 `condition_met`／`variant_holds` 檢查——**情境與條件不符 0 組**。
- 參考線照 D4（同工坊）：無條件單體 ≥ 0.9、條件成立 ≥ 1.1、條件不成立 ≥ 0.6〔建議〕；比範圍最高值；召喚、非傷害、非單體不套。1 AP 箭類線只認遠程，法術不套。

## 3. weapon 類輸出逐字相同（改前 `72712d5a`、改後同 worktree）

| 指令 | 檔 | 改前 SHA-256 | 改後 |
|---|---|---|---|
| `run --skills skill_fire_arrow,skill_pinpoint_shot,skill_rng_venom_arrow --seeds 20 --jobs 4` | JSON | `291d99abd412896a3f27e6f0eed514af59c47b5b9f3497bca675f6c274b7728b` | 相同 |
| 同上 | stdout | `57f8622add435362ca630c58746461342097b76aa31f090e0c06bda98abd72e6` | 相同 |
| `report <上面的 JSON> --detail` | stdout | `2e0d7946c5f29a15dea2593be53f64a92b457f39231a72637e87ef3c1e664af5` | 相同 |
| `run --skills skill_shadow_backstab,skill_fire_arrow --seeds 5 --jobs 4 --detail` | JSON | `a4c2bf70529d984e21027ccebe7f95222316e5f32273141519bd89295d6bccf5` | 相同 |
| 同上 | stdout | `ab155c3345c3de527f99b7888729f340e7711889d28718563cf70bbad591a548` | 相同 |
| **預設指令全部招**：`run --seeds 5 --jobs 4`（122 招、1079 組） | JSON | `a0175b031dff43d38c18ba2c766bd71a703e52d557c1e006386566eb15251f8b` | 相同 |
| 同上 | stdout | `8f3d0bc87092fabf811f45e9bdf02d4e241e34ed21dcf075dd678216ad671e70` | 相同 |
| `report <全部招 JSON> --detail` | stdout | `63916215456ec72fd89d7319288b3607534c6f47df3ce74e984f31a447b34f57` | 相同 |

前五個改前值和 NW-2c 報告第 3 節記錄的完全一樣。全部招只跑 5 種子（涵蓋每招每把武器每個情境的程式路徑與整份報表）；250 種子的預設全量沒有前後各跑一次（約 10 分鐘 ×2，且 PM 要跑全量檢查），見待決 9。stderr 只有兩行（招數組數、寫入路徑），除了路徑外相同。

## 4. 數值工坊

- 工坊用 `is_measurable(skill)`（不帶類別＝`weapon`）、`ratio_jobs`、`ratio_task`、`measure`：行為不變，法術在工坊照舊顯示「不適用」（`tests/api/tuning/test_ratio_nw2c.py` 斷言 `skill_fire_bolt` 不適用，照過）。
- **工坊沒有自然支援法術**：要支援得讓 `plan_ratio`／`skill_view` 改用 `is_measurable(skill, "spell")` 或兩類都算，屬工坊段的事（見待決 3）。
- spell 的 JSON 能通過工坊基準匯入的格式檢查（實測 `_check_script_json` 通過、84 招 `summary_of` 都不會出錯），但**基準只有一份**：匯入 spell JSON 會蓋掉武器技的基準，而法術在工坊仍不適用——**目前請不要把 spell JSON 匯入工坊**。

## 5. 結果（250 種子；`report` 原樣輸出）

類別：1 階法器法術（category: spell、weapon_req: focus）；普攻＝同一把法器的普攻
種子 250／組；含持續＝施放後 4 輪；
比值＝技能每 AP ÷ 普攻每 AP；範圍是一般武器（不含雙匕首與綁定武器）
直接／含持續＝無條件或條件不成立；成立＝條件或變奏成立；綁定武器＝不成立情境下那把武器

### 法器（84 招）

| 招 | AP | 形狀 | 條件 | 直接 | 含持續 | 成立 直接 | 成立 含持續 | 雙匕首 | 綁定武器 |
|---|---|---|---|---|---|---|---|---|---|
| 氣爆 `skill_air_burst` | 2 | ring | 無 | 0.00 | — | — | — | — | — |
| 連段雷光 `skill_arc_follow_up` | 1 | single | cast_tag_this_turn:lightning | 1.52～1.91 | — | 2.90～3.63 | — | — | — |
| 灰燼收割 `skill_ash_harvest` | 2 | single | 無 | 1.16～1.44 | — | — | — | — | — |
| 放逐 `skill_banish` | 2 | unit_then_tile | 無 | 0.00 | — | — | — | — | — |
| 竊取祝福 `skill_blessing_thief` | 1 | single | 無 | 1.27～1.59 | — | — | — | — | — |
| 蔽目黑霧 `skill_blinding_dark` | 2 | square3 | 無 | 0.62～0.77 | 0.62～0.77 | — | — | — | — |
| 清風 `skill_clearing_breeze` | 1 | square3 | 無 | 0.00 | — | — | — | — | — |
| 導電連擊 `skill_conductive_strike` | 2 | single | target_on_surface:water | 0.76～0.95 | — | 1.82～2.28 | — | — | — |
| 破魔 `skill_dispel_magic` | 1 | single | 無 | 1.18～1.47 | — | — | — | — | — |
| 驟雨 `skill_downpour` | 1 | square3 | 無 | 0.00 | 0.00 | — | — | — | — |
| 恐懼凝視 `skill_dread_gaze` | 1 | single | 無 | 0.00 | 0.00 | — | — | — | — |
| 大地崩陷 `skill_earth_collapse` | 2 | square3 | 無 | 0.00 | — | — | — | — | — |
| 火痕 `skill_ember_trail` | 1 | line | 無 | 0.00 | — | — | — | — | — |
| 火焰箭 `skill_fire_bolt` | 1 | single | 無 | 1.52～1.91 | 1.97～2.46 | — | — | — | — |
| 照明彈 `skill_flare_sight` | 1 | square3 | 無 | 0.00 | — | — | — | — | — |
| 急凍 `skill_flash_freeze` | 2 | single | 無 | 0.78～0.98 | 0.78～0.98 | — | — | — | — |
| 專注湧流 `skill_focus_surge` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 寒鎖 `skill_frost_shackle` | 1 | single | 無 | 1.27～1.59 | 1.27～1.59 | — | — | — | — |
| 焰契火靈 `skill_fsum_cinder_pact` | 2 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 燼火喚靈 `skill_fsum_ember_herald` | 2 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 雷契喚靈 `skill_fsum_storm_pact` | 2 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 吹送 `skill_gust_blow` | 1 | cone | 無 | 0.00 | — | — | — | — | — |
| 咒印飛彈 `skill_hex_bolt` | 1 | single | 無 | 1.52～1.91 | 1.52～1.91 | — | — | — | — |
| 聖光印地 `skill_holy_ground` | 1 | ground_tile | 無 | 0.00 | 0.00 | — | — | — | — |
| 聖水 `skill_holy_water` | 1 | cross | 無 | 1.27～1.59 | 1.27～1.59 | — | — | — | — |
| 獵印 `skill_hunt_sigil` | 1 | ground_tile | 無 | 0.00 | — | — | — | — | — |
| 噤聲 `skill_hush` | 1 | single | 無 | 0.00 | 0.00 | — | — | — | — |
| 冰牆術 `skill_ice_wall` | 1 | line | 無 | 0.00 | 0.00 | — | — | — | — |
| 引火重擊 `skill_kindling_strike` | 2 | single | target_has_status:burning | 0.76～0.95 | — | 1.81～2.27 | — | — | — |
| 汲命術 `skill_life_drain` | 1 | single | 無 | 1.66～2.08 | — | — | — | — | — |
| 毒霧彈 `skill_poison_mist` | 1 | square3 | 無 | 0.00 | 1.51～1.89 | — | — | — | — |
| 破邪聖光 `skill_purging_light` | 2 | cross | 無 | 0.93～1.16 | — | — | — | — | — |
| 淨化之光 `skill_purify` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 疾時之潮 `skill_quicken_tide` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 聖光撫慰 `skill_radiant_mend` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 回春 `skill_renewal` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 返魂術 `skill_resurrection` | 1 | single | 無 | 不可放 | — | — | — | — | — |
| 霜寒之觸 `skill_rime_touch` | 1 | single | 無 | 1.52～1.91 | — | — | — | — | — |
| 咒雷 `skill_rune_thunderbolt` | 2 | single | on_own_rune:lightning | 1.06～1.32 | — | 2.12～2.65 | — | — | — |
| 聖能壁壘 `skill_sanctified_ward` | 2 | single | stack:holy_power | 0.00 | — | 0.00 | — | — | — |
| 碎障爆破 `skill_shatter_blast` | 2 | square3 | 無 | 0.79～0.98 | — | — | — | — | — |
| 碎霜爆裂 `skill_shatter_frost` | 2 | single | stack:hoarfrost | 1.06～1.32 | — | 1.06～1.32 | — | — | — |
| 碎冰擊 `skill_shatter_ice` | 2 | single | target_has_status:frozen | 0.76～0.95 | — | 1.81～2.27 | — | — | — |
| 陷地術 `skill_sinkhole` | 2 | cross | 無 | 0.00 | — | — | — | — | — |
| 收割靈魂 `skill_soul_reap` | 1 | single | 無 | 1.52～1.91 | — | — | — | — | — |
| 魂潮奔流 `skill_soul_torrent` | 2 | single | stack:soul_shard | 1.06～1.32 | — | 2.12～2.65 | — | — | — |
| 火花連鎖 `skill_spark_chain` | 1 | chain | 無 | 1.52～1.91 | — | — | — | — | — |
| 石牆術 `skill_stone_wall` | 1 | cross | 無 | 0.00 | — | — | — | — | — |
| 石膚術 `skill_stoneskin_ward` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 喚潮 `skill_summon_tide` | 1 | cross | 無 | 0.00 | 0.00 | — | — | — | — |
| 順風 `skill_tailwind` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 荊棘牆術 `skill_thorn_wall` | 1 | ring | 無 | 0.00 | 0.00 | — | — | — | — |
| 雷紋刻印 `skill_thunder_sigil` | 1 | cross | 無 | 0.00 | — | — | — | — | — |
| 潮汐之矛 `skill_tidal_spear` | 2 | single | target_on_surface:water、變奏 tide_pierce、變奏 high_tide | 0.93～1.16 | 0.93～1.16 | 0.93～1.16；tide_pierce 0.93～1.16；high_tide 1.03～1.28 | 0.93～1.16；tide_pierce 0.93～1.16；high_tide 1.03～1.28 | — | — |
| 虛空互換 `skill_void_swap` | 2 | unit_pair | 無 | 0.00 | — | — | — | — | — |
| 戰歌 `skill_war_hymn` | 2 | allies_in_radius | 無 | 0.00 | 0.00 | — | — | — | — |
| 寒懼 `skill_wil_chill_dread` | 1 | single | 無 | 1.24～1.55 | 1.24～1.55 | — | — | — | — |
| 燼咒 `skill_wil_cinder_hex` | 1 | single | 無 | 1.52～1.91 | 1.97～2.46 | — | — | — | — |
| 壓頂咒 `skill_wil_crushing_hex` | 1 | single | 無 | 1.27～1.59 | — | — | — | — | — |
| 懼伏 `skill_wil_dread_kneel` | 1 | single | 無 | 0.00 | 0.00 | — | — | — | — |
| 懼焰 `skill_wil_dread_pyre` | 1 | single | 無 | 0.00 | 0.87～1.09 | — | — | — | — |
| 驚退 `skill_wil_dread_recoil` | 1 | single | 無 | 0.00 | 0.00 | — | — | — | — |
| 霜咒 `skill_wil_frost_hex` | 2 | single | 無 | 0.76～0.95 | 0.76～0.95 | — | — | — | — |
| 墓霜 `skill_wil_grave_frost` | 2 | square3 | 無 | 0.75～0.94 | 0.75～0.94 | — | — | — | — |
| 腐語 `skill_wil_rotting_whisper` | 1 | single | 無 | 0.00 | 0.53～0.67 | — | — | — | — |
| 影推 `skill_wil_shadow_shove` | 1 | single | 無 | 1.39～1.74 | — | — | — | — | — |
| 影絆 `skill_wil_shadow_snare` | 2 | square3 | 無 | 0.69～0.86 | — | — | — | — | — |
| 靜電噤聲 `skill_wil_static_silence` | 1 | single | 無 | 1.24～1.55 | 1.24～1.55 | — | — | — | — |
| 雷咒 `skill_wil_storm_hex` | 1 | single | 無 | 2.62～3.28 | — | — | — | — | — |
| 毒咒 `skill_wil_venom_hex` | 1 | single | 無 | 1.39～1.74 | 1.92～2.40 | — | — | — | — |
| 虛空牽引 `skill_wil_void_pull` | 1 | single | 無 | 1.39～1.74 | — | — | — | — | — |
| 風刃 `skill_wind_blade` | 2 | line | 無 | 0.93～1.16 | — | — | — | — | — |
| 放逐烙印 `skill_wis_banishing_brand` | 1 | single | 無 | 0.00 | 0.00 | — | — | — | — |
| 霜華祝禱 `skill_wis_frost_bloom_prayer` | 2 | cross | 無 | 0.76～0.95 | 0.76～0.95 | — | — | — | — |
| 屈膝印記 `skill_wis_humbling_mark` | 1 | single | 無 | 0.00 | 0.00 | — | — | — | — |
| 瘴氣探路 `skill_wis_miasma_sight` | 2 | cross | 無 | 0.00 | 0.39～0.48 | — | — | — | — |
| 驅逐聖光 `skill_wis_repelling_light` | 1 | single | 無 | 1.39～1.74 | — | — | — | — | — |
| 救援牽引 `skill_wis_rescue_tether` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 霜痕標記 `skill_wis_rime_mark` | 1 | single | 無 | 1.24～1.55 | 1.24～1.55 | — | — | — | — |
| 灼痕印記 `skill_wis_searing_mark` | 1 | single | 無 | 0.00 | 0.87～1.09 | — | — | — | — |
| 聖光擊倒 `skill_wis_smite_down` | 1 | single | 無 | 1.24～1.55 | — | — | — | — | — |
| 雷殼守護 `skill_wis_storm_aegis` | 1 | single | 無 | 0.00 | — | — | — | — | — |
| 雷印 `skill_wis_thunder_brand` | 1 | single | 無 | 1.24～1.55 | 1.24～1.55 | — | — | — | — |
| 蛇印 `skill_wis_venom_mark` | 1 | single | 無 | 0.00 | 0.81～1.01 | — | — | — | — |

法器 × 武器（單體傷害招的直接比值；條件類取不成立）

| 武器 | 普攻每 AP | 單體傷害招 | ≥ 0.9 | 中位數 | 最高 |
|---|---|---|---|---|---|
| fire_staff | 5.31 | 31 | 27 | 1.55 | 3.28 |
| frost_staff | 5.31 | 31 | 27 | 1.55 | 3.28 |
| lightning_staff | 5.31 | 31 | 27 | 1.55 | 3.28 |
| scepter | 6.63 | 31 | 31 | 1.55 | 3.28 |
| totem_staff | 5.31 | 31 | 30 | 1.39 | 2.62 |

### 低於 0.9 的招（直接傷害，取所有武器與情境的最高值仍 < 0.9）

| 大類 | 招 | 最高比值 | 類別 | 含持續最高 |
|---|---|---|---|---|
| 法器 | 氣爆 `skill_air_burst` | 0.00 | 非單體 | — |
| 法器 | 蔽目黑霧 `skill_blinding_dark` | 0.77 | 非單體 | 0.77 |
| 法器 | 影絆 `skill_wil_shadow_snare` | 0.86 | 非單體 | — |
| 法器 | 焰契火靈 `skill_fsum_cinder_pact` | 0.00 | 召喚 | 0.00 |
| 法器 | 燼火喚靈 `skill_fsum_ember_herald` | 0.00 | 召喚 | 0.00 |
| 法器 | 雷契喚靈 `skill_fsum_storm_pact` | 0.00 | 召喚 | 0.00 |
| 法器 | 放逐 `skill_banish` | 0.00 | 非傷害招 | — |
| 法器 | 清風 `skill_clearing_breeze` | 0.00 | 非傷害招 | — |
| 法器 | 驟雨 `skill_downpour` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 恐懼凝視 `skill_dread_gaze` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 大地崩陷 `skill_earth_collapse` | 0.00 | 非傷害招 | — |
| 法器 | 火痕 `skill_ember_trail` | 0.00 | 非傷害招 | — |
| 法器 | 照明彈 `skill_flare_sight` | 0.00 | 非傷害招 | — |
| 法器 | 專注湧流 `skill_focus_surge` | 0.00 | 非傷害招 | — |
| 法器 | 吹送 `skill_gust_blow` | 0.00 | 非傷害招 | — |
| 法器 | 聖光印地 `skill_holy_ground` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 獵印 `skill_hunt_sigil` | 0.00 | 非傷害招 | — |
| 法器 | 噤聲 `skill_hush` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 冰牆術 `skill_ice_wall` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 毒霧彈 `skill_poison_mist` | 0.00 | 非傷害招 | 1.89 |
| 法器 | 淨化之光 `skill_purify` | 0.00 | 非傷害招 | — |
| 法器 | 疾時之潮 `skill_quicken_tide` | 0.00 | 非傷害招 | — |
| 法器 | 聖光撫慰 `skill_radiant_mend` | 0.00 | 非傷害招 | — |
| 法器 | 回春 `skill_renewal` | 0.00 | 非傷害招 | — |
| 法器 | 返魂術 `skill_resurrection` | 0.00 | 非傷害招 | — |
| 法器 | 聖能壁壘 `skill_sanctified_ward` | 0.00 | 非傷害招 | — |
| 法器 | 陷地術 `skill_sinkhole` | 0.00 | 非傷害招 | — |
| 法器 | 石牆術 `skill_stone_wall` | 0.00 | 非傷害招 | — |
| 法器 | 石膚術 `skill_stoneskin_ward` | 0.00 | 非傷害招 | — |
| 法器 | 喚潮 `skill_summon_tide` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 順風 `skill_tailwind` | 0.00 | 非傷害招 | — |
| 法器 | 荊棘牆術 `skill_thorn_wall` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 雷紋刻印 `skill_thunder_sigil` | 0.00 | 非傷害招 | — |
| 法器 | 虛空互換 `skill_void_swap` | 0.00 | 非傷害招 | — |
| 法器 | 戰歌 `skill_war_hymn` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 懼伏 `skill_wil_dread_kneel` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 懼焰 `skill_wil_dread_pyre` | 0.00 | 非傷害招 | 1.09 |
| 法器 | 驚退 `skill_wil_dread_recoil` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 腐語 `skill_wil_rotting_whisper` | 0.00 | 非傷害招 | 0.67 |
| 法器 | 放逐烙印 `skill_wis_banishing_brand` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 屈膝印記 `skill_wis_humbling_mark` | 0.00 | 非傷害招 | 0.00 |
| 法器 | 瘴氣探路 `skill_wis_miasma_sight` | 0.00 | 非傷害招 | 0.48 |
| 法器 | 救援牽引 `skill_wis_rescue_tether` | 0.00 | 非傷害招 | — |
| 法器 | 灼痕印記 `skill_wis_searing_mark` | 0.00 | 非傷害招 | 1.09 |
| 法器 | 雷殼守護 `skill_wis_storm_aegis` | 0.00 | 非傷害招 | — |
| 法器 | 蛇印 `skill_wis_venom_mark` | 0.00 | 非傷害招 | 1.01 |

共 46 招（法器非單體 3；法器召喚 3；法器非傷害招 40）

條件檢查：施放前條件和情境不符 0 組

### 參考線外（D4：無條件 ≥ 0.9、成立 ≥ 1.1、不成立 ≥ 0.6〔建議〕；比範圍最高值）

| 招 | AP | 類別 | 參考線 | 值 |
|---|---|---|---|---|

套參考線 39 條（招×線），低於或不可放 0 條

### 分組：AP（直接，條件類取不成立；每招取最高值）

| 組 | 招 | 可放 | ≥ 0.9 | ≥ 0.6 | 中位數 | 最高 |
|---|---|---|---|---|---|---|
| 1 | 56 | 55 | 23 | 23 | 0.00 | 3.28 |
| 2 | 28 | 28 | 15 | 17 | 0.95 | 1.44 |

### 分組：元素（直接，條件類取不成立；每招取最高值）

| 組 | 招 | 可放 | ≥ 0.9 | ≥ 0.6 | 中位數 | 最高 |
|---|---|---|---|---|---|---|
| earth | 2 | 2 | 0 | 0 | 0.00 | 0.00 |
| fire | 4 | 4 | 4 | 4 | 1.44 | 1.91 |
| holy | 5 | 5 | 5 | 5 | 1.55 | 1.74 |
| ice | 8 | 8 | 8 | 8 | 1.55 | 1.91 |
| lightning | 6 | 6 | 6 | 6 | 1.55 | 1.91 |
| shadow | 16 | 16 | 14 | 16 | 1.74 | 3.28 |
| wind | 2 | 2 | 1 | 1 | 1.16 | 1.16 |
| — | 41 | 40 | 0 | 0 | 0.00 | 0.00 |

### 分組：骨架（直接，條件類取不成立；每招取最高值）

| 組 | 招 | 可放 | ≥ 0.9 | ≥ 0.6 | 中位數 | 最高 |
|---|---|---|---|---|---|---|
| area | 9 | 9 | 7 | 8 | 0.98 | 1.91 |
| aura | 12 | 11 | 0 | 0 | 0.00 | 0.00 |
| builder_finisher | 4 | 4 | 4 | 4 | 1.91 | 1.91 |
| combo | 5 | 5 | 5 | 5 | 0.95 | 1.32 |
| control | 29 | 29 | 9 | 10 | 0.00 | 1.59 |
| displace | 11 | 11 | 5 | 5 | 0.00 | 1.74 |
| rune | 3 | 3 | 0 | 0 | 0.00 | 0.00 |
| strike | 8 | 8 | 8 | 8 | 1.91 | 3.28 |
| summon | 3 | 3 | 0 | 0 | 0.00 | 0.00 |

### 分組：類別（直接，條件類取不成立；每招取最高值）

| 組 | 招 | 可放 | ≥ 0.9 | ≥ 0.6 | 中位數 | 最高 |
|---|---|---|---|---|---|---|
| 召喚 | 3 | 3 | 0 | 0 | 0.00 | 0.00 |
| 條件類 | 8 | 8 | 8 | 8 | 1.32 | 1.91 |
| 無條件 | 23 | 23 | 23 | 23 | 1.59 | 3.28 |
| 非傷害招 | 40 | 39 | 0 | 0 | 0.00 | 0.00 |
| 非單體 | 10 | 10 | 7 | 9 | 0.98 | 1.91 |

## 6. 和武器技的對照

武器技數字取 BAL-21e 報告第 4 節（250 種子；查過 `git log`，BAL-21e 之後 `content/skills`、`weapons.yaml`、`skill_scaling.yaml` 只有頭目招、圖示道具與武器外觀的改動，1 階武器技的數值沒變）；每 AP 絕對傷害的武器技一欄是本段 5 種子全部招的跑法（第 3 節那份 JSON），只當量級參考。

| 項目 | 武器技（遠程／近戰） | 法器法術 |
|---|---|---|
| 招數 | 45／77 | 84 |
| 普攻每 AP（基準） | 遠程 4.62～7.73；近戰 5.59～10.19 | 法杖、圖騰杖 5.31；權杖 6.63 |
| 單體傷害招的直接比值中位數（依武器） | 遠程 0.56～0.59；近戰 0.58～0.62（雙匕首 0.29） | 1.39～1.55 |
| 單體傷害招 ≥ 0.9 的數量（依武器） | 遠程 0～3／28～30；近戰 4～9／53～54 | 27～31／31 |
| 單體傷害招每 AP 絕對傷害中位數（直接、不成立） | 2.6～6.9（5 種子） | 五把法器的中位數都是 8.22（250 種子） |
| 參考線外（招×線） | 低於 0.9 的招 72 招（含非單體、召喚、非傷害） | **0／39** |
| 低於 0.9 的招 | 72 | 46（非單體 3、召喚 3、非傷害招 40；無條件與條件類 0） |

## 7. 重點

1. **法器法術沒有一招落在參考線外**：套得到參考線的 31 招（無條件 23、條件類 8）共 39 條（招×線）全部達標；無條件單體最低是急凍 0.78～0.98、霜咒 0.76～0.95（範圍最高值仍 ≥ 0.9）。
2. **方向和武器技相反：法術偏高**。無條件單體中位數約 1.5，1 AP 單體多在 1.24～1.91；雷咒 `skill_wil_storm_hex` 2.62～3.28、汲命術 1.66～2.08。以每 AP 絕對傷害看，法術單體招（中位數 8.22）也比武器技（中位數 2.6～6.9，5 種子）高。原因有二：法器普攻本身弱（每 AP 5.31，低於多數武器），而法術傷害不吃武器骰、照招自己的骰子與屬性算。
3. **條件類成立時都 ≥ 1.81**（連段雷光 2.90～3.63、咒雷與魂潮奔流 2.12～2.65、引火重擊／碎冰擊 1.81～2.27、導電連擊 1.82～2.28），不成立時 0.76～1.91。只有潮汐之矛的 `high_tide` 變奏是 1.03～1.28（< 1.1 但主型態條件成立值 1.16 ≥ 1.1，所以不列）。
4. **條件成立和不成立數字相同的招**（條件只影響非傷害效果，或量法量不到）：碎霜爆裂 `stack:hoarfrost`（1.06～1.32 兩邊相同）、潮汐之矛 `target_on_surface:water` 與 `tide_pierce` 變奏、聖能壁壘（非傷害）。施放前條件檢查都成立，不是量法錯；要不要把它們當「條件類」看，見待決 6。
5. **非傷害招 40 招（48%）**：控制、位移、護盾、治療、牆、地面印記；其中 6 招靠狀態有後續傷害（含持續：毒霧彈 1.51～1.89、懼焰與灼痕印記 0.87～1.09、蛇印 0.81～1.01、腐語 0.53～0.67、瘴氣探路 0.39～0.48）。返魂術要倒地的隊友，木樁場景不可放。
6. **範圍的上下緣來自武器**：權杖普攻有祝福 ＋3（每 AP 6.63），所以多數招的範圍下緣是權杖（例 1.52～1.91 的 1.52）；圖騰杖單體中位數 1.39（其他 1.55），推測是推薦配點跟著武器主屬性（WIL）走、INT 法術在圖騰杖上傷害較低——沒有逐招查證。

## 8. 建議（只寫建議；不改 `content/`，數值由使用者在工坊定）

- 法器法術目前**不需要往上補**；若要調，是「往下收」或「把法器普攻拉上來」的問題，建議使用者先決定法術要拿哪一條線比（見待決 1）。
- 若決定往下收，建議分組看：1 AP 無條件單體（中位數約 1.5）、條件類成立（≥ 1.81）各為一組；雷咒 2.62～3.28 是單招離群值，可先單獨看。
- 法術與武器技的比值**不能直接並排比**（基準不同）；跨類比較請看第 6 節的每 AP 絕對傷害，或另定共用基準。

## 9. 沒量到的與限制

- 同 BAL-21e：範圍招只算受測木樁；「成立」是直接改狀態做出來的；召喚的含持續受站位與 AI 影響。
- 法術的法力消耗、冷卻沒有進比值（武器技的耐力也沒有）；法術能連放幾次受法力限制，實戰每回合輸出未必如表。
- 木樁的元素抗性照木樁範本（沒有另外量各元素的抗性差）。
- `weapon_req: any` 的 1 階法術 68 招、1 階非主動招（被動、修正、反應、架勢）不在範圍內。

## 10. 檢查與結束碼

| 指令 | 結束碼 | 摘要 |
|---|---|---|
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run mypy` | 0 | 1522 個原始檔 |
| `uv run lint-imports` | 0 | 14 kept, 0 broken |
| `pytest -q tests/sim/test_skill_ratio.py -x` | 0 | 18 passed |
| `pytest -q tests/api/tuning/test_ratio_nw2c.py tests/test_architecture.py tests/test_sim_scripts.py -n 4` | 0 | 21 passed |
| `t1_skill_ratio.py run --category spell --jobs 4`（250 種子） | 0 | 84 招、420 組；JSON SHA-256 `83e2d7b8138926d7c0eae11b8efa7ef36b70b312fb0c275c5f19820dbbbf452f`、stdout `c25244eee76ff3ed5292cd5130ac5120191243b2e70b53b5de8aa8d174b8e0de`（暫存區，不進 repo） |
| 第 3 節的 weapon 前後比對（4 組 run＋2 組 report） | 全 0 | 8 個 SHA-256 全部相同 |

沒有跑 `scripts/check.py`、CLI 快照、`trpg sim completion`／`matrix`；沒有重產任何雜湊或快照；沒有新增 `# noqa` 的複雜度例外（`_apply_tweaks` 超過 PLR0912 後把法術條件拆成 `_spell_tweak`；腳本一個 `# noqa: PLR2004` 是「不成立」建議線 0.6）。

## 11. 待 PM 決定

1. **法術的基準**：照最保守的做法用「同一把法器的普攻每 AP」（核心本來就有法器大類）。因為法器普攻弱，法術比值普遍 1.2～1.9；要不要改用跨類共用基準（例如每 AP 絕對傷害、或某把參考武器的普攻）再看一次。
2. **範圍只量 `weapon_req: focus` 的 84 招**（照派工的「84 招」）；`weapon_req: any` 的 1 階主動法術還有 68 招沒量，要不要另段補（任何武器都能放，基準要選哪把武器另議）。
3. **工坊不顯示法術比值**（`is_measurable` 預設仍是 weapon）；要支援需改 `api/tuning/ratios.py` 的 `plan_ratio`／`skill_view` 與「基準只有一份」的存法，另排工坊段。在那之前不要把 spell JSON 匯入工坊（會蓋掉武器技基準）。
4. **參考線套到法術是否合適**：D4 是為武器技「往上補」定的下限；法術全部達標，但偏高。是否另訂法術的上限參考（例如單體無條件 ≤ 1.5）由使用者決定。
5. **1 AP 法術沒有套 1 AP 箭類線**（`_is_arrow` 只認遠程），一律用 0.9；目前全部達標，不影響結論。
6. 碎霜爆裂、潮汐之矛的條件／變奏「成立」和「不成立」傷害相同（條件影響的是非傷害效果），報表照條件類處理、取不成立比 0.6、成立比 1.1。
7. `cast_tag_this_turn` 成立的做法：施放前直接把標籤加到主角「本回合已施放標籤」；`on_own_rune` 成立：目標格放一個主角自己的同元素符文（剩 2 回合，同「目標加狀態剩 2 回合」的保守預設）。
8. 「非傷害招」的分類照 BAL-21e（看有沒有 `damage`／`charge_through` 效果），靠狀態才有傷害的 6 招算非傷害、不套線；它們的含持續值寫在第 7 節。
9. weapon 逐字相同的證據用 5 種子全部招＋NW-2c 的兩組指令；250 種子的預設全量沒有前後各跑一次（每次約 10 分鐘），需要的話 PM 可排在全量檢查之外的時段補。
10. 腳本仍留在 `scripts/`（法術與武器技共用），不搬 `scripts/archive/`。
