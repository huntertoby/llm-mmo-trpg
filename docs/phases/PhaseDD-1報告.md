# Phase DD-1 完成報告：雙匕首的武器技也打兩下（#153 引擎＋AI）

> 依據：`docs/design/08-裝備.md` 8.11「雙匕首的武器技也打兩下」（決定 #153，使用者：「改 A」；排程：「排」）、`docs/玩法決定紀錄.md` #153。前端另一段，本段沒動 API 與 `client/`。
> 起點：`53865c7c`（本機 main ff 合入後）。

## 1. 交付與 commit

| commit | 內容 |
|---|---|
| `98d2ffc9` | 引擎結算、預覽／AI 估值、版號、測試 |
| （本報告 commit） | 報告、上手筆記 |

改動的程式：

- `src/trpg/engine/skills/targeting.py`：新函式 `skill_strikes(caster, skill)`——`category: weapon`、形狀 `single` 時回手上武器（`held_weapon`）的 `strikes`，其他 1。
- `src/trpg/engine/skills/cast.py`：
  - `Cast.strikes`（只有 `modified` 的施放用 `skill_strikes`；被動、陷阱觸發一律 1）、`Cast.form_bonus`（形態進入獎勵暫存）。
  - `run()` 的效果迴圈抽成 `resolve_effect(effect, extra=False)`（行為不變），之後呼叫新的 `extra_strikes()`／`_strike_effects()`。
  - `roll_one(..., extra=False)`：多打的那一下在預覽時同普攻的後續幾下（最少後果失手、最多後果暴擊；測試模式木樁照樣命中），武器 `backstab_first_only` 時不算背刺，不重複記轉身。
  - `consume_stacks()` 的「從目標消耗」抽成 `_consume_from_targets()`（呼叫順序不變），另有 `consume_target_stacks()` 給「第一下沒中、第二下才中」用。
- `src/trpg/engine/preview.py::_damage_expectation`：期望傷害 × `skill_strikes`（AI 的傷害收益吃這個值，所以 `ai/` 不必改）。
- 版號：`runner.py` `LOG_FORMAT` `/115` → `/116`；`world/save.py` `WORLD_RULES_VERSION` 25 → 26（加說明條目）；`docs/phases/戰鬥紀錄格式變更.md` 加 `/116` 一條。

## 2. 規則逐條對照（08 8.11）

| 規則句 | 實作 | 測試（`tests/engine/test_dual_dagger_skills_dd1.py`） |
|---|---|---|
| 拿雙匕首施放 **單體** 武器技（`category: weapon`、`single`）時，每個傷害效果結算兩下 | `skill_strikes` 判斷；`extra_strikes` 重打每個 `damage`（`affects` enemies／all）效果 | `test_a_single_weapon_skill_strikes_twice_with_dual_daggers`、`test_every_damage_effect_strikes_twice`（兩個傷害效果 → 4 筆） |
| 每一下都套技能倍率、各用一次雙匕首的傷害骰與屬性加成 | 重打走同一個 `damage` 原語（`damage_parameters`＋`attack_damage`），每下各擲骰 | 同上（每筆 `multiplier_permille`、`rolls`、`scaled_permille` 相同） |
| 每一下各自擲命中與暴擊 | 每下 `roll_one`，各一筆 `attack_rolled`；傷害的暴擊讀那一下的結果 | 表格四列（中中／中失／失中／失失）、`test_each_strike_rolls_its_own_crit` |
| 背刺時兩下都吃加成（同普攻） | `roll_attack(backstab_allowed=...)`；照普攻也尊重 `backstab_first_only`（雙匕首為 false） | `test_backstab_applies_to_both_strikes`、`test_backstab_first_only_weapons_...` |
| 第一下打倒目標就不打第二下 | 每下之前檢查施放者與目標都還站著 | `test_the_second_strike_is_skipped_when_the_first_one_kills` |
| 「命中時」觸發每一下各觸發一次 | 詞條、被動、修正規則的命中觸發本來就掛在 `attack_rolled`／`damage_dealt` 事件上，每下各一筆事件 → 各觸發一次；吸血、擊殺時效果跟著每下的傷害 | `test_on_hit_effects_follow_every_strike`（吸血 2 次） |
| 附加效果只結算一次：第一下命中時結算；第一下沒中、第二下中就在第二下；兩下都沒中不結算 | 第一下照舊結算全部效果（沒中時對敵人的效果自然沒有對象）；後面那下只有「前面都沒中」時才結算對敵人的非傷害效果、目標層數消耗與賭注 | `test_a_status_rider_resolves_once_on_the_first_hit`（含結算在哪一下之後）、`test_a_push_rider_resolves_once` |
| 範圍、直線、多目標等非單體形狀只打一下；法術不受影響 | `skill_strikes` 回 1 | `test_other_shapes_and_spells_strike_once`（十字形、法術）、`test_other_weapons_strike_once`、`test_the_number_of_strikes_follows_the_weapon_data`（1／2／3） |
| 和 PB-1a 部位一致：選了部位兩下打同一部位（R5 宣告時判一次） | 第二下沿用 `Cast.part_id`；部位第一下就破，第二下打本體（同普攻的 `live_part` 檢查） | `test_both_strikes_hit_the_declared_part`（未破 2 次 `part_damaged`；第一下破 → 1 次＋1 次 `part_broken`，第二下打本體） |
| AI 估值要算兩下 | 預覽期望 × 下數 | `test_the_preview_counts_both_strikes`、`test_the_utility_ai_values_the_second_strike` |

## 3. 不變比對

腳本在 scratchpad（未 commit）：地圖預設陣容、效用 AI、`max_rounds=30`；改前 `53865c7c`、改後 `98d2ffc9`，每場比對完整事件 JSON、步驟、最終狀態 JSON（含 `rng_state`）。只因版號不同的鍵是紀錄的 `format`（不在比對範圍內，事件與狀態裡沒有版號）。

- 8 張地圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12：`battles=46 events=20491 different=0`。46 場的陣容都沒有雙匕首。
- **帶雙匕首的戰鬥**（另寫腳本：`open_plain`、`bandit_lair` × 種子 1～10，我方第一人換成拿雙匕首、帶雙牙／刃舞／交叉斬／`skill_ambush_stab`）：改前用 `git archive 53865c7c` 解出的舊 `src` 跑（`PYTHONPATH` 指過去），20 場全部不同（預期）。逐項：
  - 雙刀手技能的 `attack_rolled` 從 47 筆變 100 筆（每次施放多一下；少數幾場施放次數也不同）。
  - 施放次數（20 場合計）：刃舞 18 → 19、雙牙 13 → 15、`skill_ambush_stab` 16 → 16、交叉斬 0 → 1（AI 估值算兩下後稍微多用）。
  - 勝方：我方 8 勝 → 13 勝。
  - 事件型別沒有新增；結構不變，只是同樣的步驟多出命中與傷害事件、亂數取用次數增加。
- 一場帶雙匕首的 `battle`＋`replay`：`open_plain` 種子 8（雙牙施放 2 次，每次兩下）→「重播驗證通過：64 個動作、265 個事件，最終狀態一致」。

## 4. 版號與存檔影響

- `LOG_FORMAT` `trpg-battle-log/115` → `/116`：結算結果與亂數取用次數改變，`/115` 的戰鬥紀錄與戰鬥中存檔無法重播。
- `WORLD_RULES_VERSION` 25 → 26（照派工；世界的程式沒有改）：舊世界日誌標成「規則已變、不能重播」。
- 規則包雜湊、內容 digest 不變（沒有動 `content/`）。
- 使用者原話「存檔都可以刪除」：沒有刪任何存檔檔案。

## 5. 改到的測試（舊 → 新）

| 檔案 | 舊 | 新 | 理由 |
|---|---|---|---|
| `tests/engine/test_weapons_dual_dagger_firearm.py` | `test_dual_dagger_weapon_skill_hits_only_once`：傷害 1 筆、擲命中 1 次 | `test_dual_dagger_single_weapon_skill_strikes_twice`：骰值固定兩下都命中，傷害 2 筆、擲命中 2 次 | 規則改了（#153），舊測試寫的是被推翻的行為 |
| CLI 測試 6 檔＋`test_gear_g2.py`、`test_gear_g3a.py` | `trpg-battle-log/115` | `/116` | 版號 |
| `test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py` | `endswith("/115")` | `endswith("/116")` | 版號 |
| `tests/api/test_pr2a_range_practice.py`、`tests/world/test_opening_stages.py` | `WORLD_RULES_VERSION == 25` | `== 26` | 版號 |

- 固定種子測試：沒有因本段失效的（其他固定種子的戰鬥都不帶雙匕首）；沒有換種子、沒有放寬斷言。
- `test_weapon_skill_damage_matches_the_card_current_bonus[dual_dagger]` 沒改仍通過：它只固定第一顆 d20，第二下由種子決定，目前那個種子第二下失手（`(dealt,) =` 解包剛好 1 筆）。記在上手筆記第四節第 20 點。
- CLI 快照 `tests/cli/test_output_snapshots.py -m slow`：24 passed，**沒有重產任何鍵**（快照裡的戰鬥都沒有雙匕首）。

## 6. 模擬報表（只出表、不調數值）

`scripts/t1_skill_ratio.py run --weapons dual_dagger --seeds 250 --jobs 4`；改前用 `53865c7c` 的舊引擎、改後用本段引擎，各跑一次（開發 PM 同意：「可以跑…程序池用 4」）。比值＝技能每 AP ÷ 雙匕首普攻每 AP（普攻每 AP 10.19 兩次相同）。

**彙總（雙匕首，近戰單體傷害招 54 招）**：中位數 0.29 → **0.58**、最高 0.65 → **1.32**、達 0.9 參考線的招 0 → **6**。

**逐招（「直接」＝無條件或條件不成立；「成立」＝條件成立）**：

| 招 | 改前 直接 | 改後 直接 | 改前 成立 | 改後 成立 |
|---|---|---|---|---|
| 雙牙 `skill_twin_fang`（綁雙匕首） | 0.54 | 1.10 | — | — |
| 刃舞 `skill_blade_dance`（綁雙匕首；含持續 0.62 → 1.11） | 0.45 | 0.91 | — | — |
| 交叉斬 `skill_crossing_slash`（背後） | 0.25 | 0.50 | 0.57 | 1.18 |
| 瞬步背刺 `skill_shadow_backstab`（背後） | 0.26 | 0.52 | 0.65 | 1.34 |
| 先發制人 `skill_first_strike`（第 1 輪） | 0.32 | 0.64 | 0.72 | 1.48 |
| 血祭重擊 `skill_blood_sacrifice` | 0.65 | 1.32 | — | — |
| 孤注一擲 `skill_all_in` | 0.59 | 1.17 | — | — |
| 狂野之刃 `skill_wild_blade` | 0.57 | 1.15 | — | — |
| 狂戰士之怒 `skill_berserker_rage` | 0.51 | 1.00 | — | — |
| 碎骨重擊 `skill_bone_crusher` | 0.37 | 0.78 | — | — |
| 審判斬 `skill_rng_judgment_cleave` | 0.35 | 0.74 | — | — |
| 裂風斬 `skill_rng_gale_cleave` | 0.35 | 0.69 | — | — |
| 放血斬 `skill_rending_strike`（含持續 0.67 → 1.08） | 0.34 | 0.69 | — | — |
| 連環快刺 `skill_flurry_jab` | 0.34 | 0.67 | — | — |
| 震擊 `skill_palm_strike` | 0.34 | 0.67 | — | — |
| 毒刃 `skill_venom_blade`（含持續 0.81 → 1.21） | 0.31 | 0.63 | — | — |
| 破甲擊 `skill_sunder_strike` | 0.28 | 0.55 | — | — |
| 破城衝撞 `skill_battering_ram` | 0.18 | 0.36 | — | — |
| 衝鋒撞擊 `skill_tiger_charge` | 0.18 | 0.36 | — | — |
| 盾擊 `skill_shield_bash` | 0.17 | 0.34 | — | — |
| 換位重擊 `skill_decoy_swap` | 0.17 | 0.34 | — | — |
| 颶風踢 `skill_gale_kick` | 0.17 | 0.34 | — | — |
| 倒地補刀 `skill_ground_finish`（倒地） | 0.25 | 0.50 | 0.72 | 1.43 |
| 踩踏 `skill_trample`（倒地） | 0.25 | 0.50 | 0.72 | 1.43 |
| 獵殺一擊 `skill_hunters_strike`（標記） | 0.25 | 0.50 | 0.69 | 1.36 |
| 連擊終結 `skill_combo_finisher`（層數） | 0.32 | 0.64 | 0.66 | 1.31 |
| 俯衝斬 `skill_plunging_strike`（高處） | 0.25 | 0.50 | 0.64 | 1.32 |
| 破冰重擊 `skill_icebreaker`（冰凍） | 0.25 | 0.50 | 0.61 | 1.24 |
| 怒氣爆發 `skill_rage_unleashed`（層數） | 0.32 | 0.64 | 0.59 | 1.17 |
| 潮斬 `skill_tide_cleave`（水面） | 0.25 | 0.50 | 0.58 | 1.18 |
| 碎骨追擊 `skill_bone_pursuit`（撞擊） | 0.25 | 0.50 | 0.58 | 1.18 |
| 灼斬 `skill_scorching_slash`（燃燒） | 0.25 | 0.50 | 0.55 | 1.13 |
| 追印絆擊 `skill_prone_mark_strike`（標記） | 0.00 | 0.00 | 0.54 | 1.05 |
| 碎岩擊 `skill_rock_smash`（倒地） | 0.29 | 0.58 | 0.52 | 1.03 |
| 蝕骨刺 `skill_marrow_thorn`（中毒） | 0.25 | 0.50 | 0.51 | 1.04 |
| 處決 `skill_execute`（低血量） | 不可放 | 不可放 | 0.51 | 1.00 |
| 霜崖斬 `skill_frost_ledge_cleave`（變奏） | 0.41 | 0.81 | 0.46 | 0.94 |
| 並肩斬、前後夾擊、獵殺落單、衝勢劈砍 | 0.25～0.26 | 0.50～0.52 | 0.44～0.45 | 0.90 |
| 靠牆盾擊 `skill_wall_brace_bash`（變奏） | 0.37 | 0.72 | 0.37 | 0.72 |

（綁其他武器的招，例如鞭、拳套、盾、鐮刀、魔刃，表上的雙匕首欄也照比例翻倍，但實戰拿雙匕首放不出來，略。）非單體形狀、召喚、非傷害招的列改前改後相同。完整輸出：`ratio_before.txt`／`ratio_after.txt`（scratchpad，未 commit）。

觀察（只陳述，不建議數值）：無條件單體招大致剛好 × 2（第二下的失手率與第一下相同）；雙牙、刃舞原本「拿雙匕首多一段傷害」也跟著打兩下，兩招現在是雙匕首最高的兩招之一。數值由使用者在數值工坊調。

## 7. 檢查（結束碼）

| 指令 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0（1500 檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0 |
| 相關 pytest（新檔、雙匕首與火器、部位、AI、預覽、反應、決定性、clone、暫停點、版號所在檔等） | 0 |
| `tests/skillgen tests/narrative`（含 slow） | 0（5390 passed、14 skipped） |
| `tests/cli/test_output_snapshots.py -m slow` | 0（24 passed，沒有重產） |
| `trpg battle replay`：`open_plain` 種子 8（雙匕首） | 0 |
| `trpg battle`＋`replay`：`oil_depot` 種子 13 | 0、0 |

沒有動 API 與前端型別，不跑 `pnpm`。沒有新增 `# noqa`。

## 8. 待 PM 決定

規格沒寫到的地方都照最保守、最一致的做法做完，列在這裡：

1. **反應技、複製施放、複合技能的第二段**：只要是拿雙匕首施放的單體武器技都打兩下（判斷放在 `Cast` 上；被動與陷阱觸發不算「施放」，打一下）。目前 105 招單體武器技裡反應技 5 招、帶第二段的 0 招。
2. **瞄準與形態進入獎勵**：第二下也吃（沿用技能「這次施放每一次命中判定都吃到」的規則）；普攻的瞄準只給第一下，兩者不同。
3. **目標的「被命中」反應技**（`hit_by_*`）：一次施放仍只反應一次（看任一下命中）；普攻是每下各一次。「相鄰友方被瞄準」反應也只在施放前一次。
4. **守護者攔截**：每一下都可能被攔（同普攻）；第一下被攔下時第二下打守護者。
5. **武器特性**（破甲、震退、祝禱等 `apply_hit_traits`）本來就只有普攻有、武器技沒有；本段沒加（雙匕首也沒有命中特性）。「命中時」只涵蓋詞條、被動、修正規則（掛在事件上的觸發）。
6. **對自己、友方、格子的附加效果**（自我增益、造地形）照舊在第一下結算，沒命中也結算（原本單下的行為）；元素觸及格子、風的擴散只做一次。對自己的傷害（反噬）不重打。
7. **賭注的「依造成傷害反噬」**（`self_damage_of_hit`）只算賭注效果位置之前的傷害（第二下在後面，不算）；目前只有 1 招有賭注。→ 玩法 PM 定為「兩下的總和」（08 8.11 細節 6），DD-1b 已改（`PhaseDD-1b報告.md`）。
8. **預覽數字**：最少後果＝只有第一下命中（同普攻的後續幾下），最多後果＝兩下都暴擊；期望值＝每下期望 × 下數（沒扣「第一下打倒」）。前端顯示若要另標「打兩下」，在前端段處理。
9. **武器卡文字**「連擊：普攻一次打 2 下」沒有提到武器技也打兩下（`content/battle.py` 的 `trait_lines_zh`）；要不要改字、改在哪一段。
10. **雙牙、刃舞**的「拿雙匕首多一段傷害」現在也打兩下（比值 1.10、0.91）；#153 待辦寫玩法 PM 另出案。
11. `strikes` 是通用參數（雙匕首 2；資料可到 3），第三下照同樣規則；目前只有雙匕首 `strikes > 1`（形態的天生武器只給普攻）。
12. 形狀 `unit_then_tile` 不算單體（規格寫 `single`；`t1_skill_ratio.py` 把它當單體統計）。
