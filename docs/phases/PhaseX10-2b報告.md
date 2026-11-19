# X10-2b 報告：正式換算 ×10

依據：`docs/phases/PhaseX10-2b計畫.md`、`PhaseX10-2a報告.md`（含開發 PM 裁定）、`PhaseX10-1報告.md`、`docs/design/05-戰鬥.md` 5.4.1。
基準：開工前 `git merge main`（`f6d2bc957`）。分支 `worktree-agent-a0f237af28a1b7625`，沒 push。
沒改 `docs/design/`、`config/`。沒跑 `scripts/check.py` 全量、沒用 `-m ""`、沒試數值。
期間開發 PM 透過訊息即時裁定了數件事（漏換的補改、輕巧、場景調整等），裁定內容逐條寫在對應的節。

## 1. 交付與 commit

| # | 項目 | commit | 內容 |
|---|---|---|---|
| 1 | 換算 | `f3a405238` | `rescale.py` 的輸出，只有 `content/` |
| 2 | X10-2a 裁定補件 | `51a9bcd85` | `mana_cost` 打折下限、`minimal_filler` 回復法力下限 × scale；`skill_budget.yaml` 註解改新單位 |
| 2b | 清單漏列（開發 PM 裁定） | `3de88c45e` | 意志 `control_resist` 每階 1→10；圓盾格擋強化 ÷ scale；`DamageEffect`／`DamageObjectEffect` 預設 `min_damage` 1×scale |
| 3a | 測試改新數字 | `e96690898` | 170 個測試檔（見第 5 節） |
| 2c | 漏換補改（開發 PM 裁定 A1～A4、B5、B6） | `e98c85a57` | 砍費用、輕巧步距 × scale；練習木樁補滿門檻；fuzz 法力；三段文字 |
| 2d | Python 寫死的量類字面值（開發 PM 裁定） | `b9043a06d` | 大變化、配方候選費用 × scale；白板法力步距；三處「不致死」下限 |
| 3b | 重產快照、夾具 | `122060224` | CLI 雜湊、parity 夾具、前端 glossary／skillCards；`run auto` 種子 18→20 |
| 3c | 小修 | `0e3cf3861`、`3e149d07e` | 測試多餘的 `type: ignore`（mypy）；前端 vitest 的技能卡法力 4→40 |
| 4 | 報告 | （本檔） | |

規格的 4 個交付項目中，第 2 項因為途中陸續找到漏換，拆成 4 個 commit（2、2b、2c、2d）；第 3 項拆成「改測試」與「重產夾具」兩個 commit，重產只做一次（2d 之後）。

## 2. 換算（交付項目 1）

- `rescale.py --tuned-md` 重跑：工坊寫回的 commit 仍是 0 筆，`X10-工坊調過的欄位.md` 沒有變動（沒 commit）。
- `rescale.py --check` 結束碼 0；換算 **1,838 筆、515 個檔**，`quantity_scale` 1→10；再跑一次被拒絕（結束碼 1，「已經換算過」）。
  - 515 個檔中有 20 個只含 0→0 的值，文字沒變，所以 git 實際變動 495 個檔。
- **和預覽 CSV（`X10-換算預覽.csv`，1,839 筆）的差異只有 1 筆**：`ai_profiles.yaml` `summon.infuse_threat_damage` 2→20 不在這次換算裡——X10-1 裁定 2 把它改回 keep，由引擎乘回。其餘 1,838 筆的路徑、舊值、新值完全相同。
- 換算後 `trpg content check` 結束碼 0（696 檔、434 技能通過預算）。

## 3. 補件與漏換（交付項目 2）

### 3.1 X10-2a 裁定的補件（`51a9bcd85`）
- `CoreRules.mana_cost`：打折後下限 `min(原費用, quantity_scale)`。原費用比 10 還少時（目前內容沒有）以原費用為下限，打折不會變貴——規格沒寫這個情況，照最保守的做。
- `minimal_filler`：`restore_resource` 的 `resource: mana` 補的 `amount` 下限 1×scale；`cooldown` 照舊 1。
- `skill_budget.yaml` 註解：「法力每點」→「法力每 quantity_scale 點」、耐力折抵公式、召喚物固定傷害 ÷ scale、召喚物 HP 例子 14→140。
- 工坊 `tuning_fields.yaml` 的建議範圍：換算腳本已經做了（30 筆，含最大 HP 10～9990、屬性 10～300、法力／耐力上限與費用），不需要另改。

### 3.2 清單漏列（`3de88c45e`，開發 PM 裁定）

屬性常駐效果逐條判斷（`content/rules/core.yaml` 232～241）：

| 常駐效果 | 加在哪裡（依據） | 判斷 |
|---|---|---|
| 撞擊傷害 +n／−n（力量） | `engine/triggers.py` 138～147 `_collision_flats` 加減在撞擊傷害的固定值上 | 量類，X10-1 已 ×10 |
| 反應攻擊命中 +n（感知） | d20 命中修正 | 不放大 |
| 表面、持續區域 +n 回合（智力） | 回合數 | 不放大 |
| 看見隱蔽與陷阱 +n 格（感知） | 格數 | 不放大 |
| **控制抵抗 +n（意志）** | `engine/control.py` 74～81 加在有效屬性值上成為 `defense_value`；85 行 `hit_table.modifier(attack_value, defense_value)` 以「攻擊值 ÷ 防禦值」比例換算修正（`content/rules.py` 801） | **量類，1→10**（原清單列 keep，漏列） |

其他「加在屬性值或量類值上」的欄位掃描（`scripts/x10/fields.yaml` 全部 keep 項逐一看）：

| 欄位 | 判斷 |
|---|---|
| `offhands.yaml` 圓盾 `block_bonus.permille_per_point`（5‰） | **要改**：減傷 ‰ ＝ 縮放屬性值 × 每點‰（`content/battle.py` 655～660），屬性 ×10 後變 10 倍，直接頂到上限 100‰。0.5 放不進整數，改在程式裡 ÷ `quantity_scale`（`block_extra_permille(get, scale)`），內容不動；卡片文字「縮放屬性 × 0.05%」 |
| `DamageEffect`／`DamageObjectEffect` 預設 `min_damage` 1（`engine/effects/models.py`） | **要改**：撞擊、百分比 HP 等沒指定的傷害用它；`min_damage_on_hit` 已 ×10，改成預設 `None`＝1×scale（`min_damage_for(scale)`） |
| `statuses[].attack_bonus`、`attr_bonus` | 已在 scale |
| `teleport_*_resist_bonus`、`*_hit_bonus`、`*_hit_penalty`、`keen.crit_range_delta` | d20，不放大 |
| `swift.speed_bonus`、`spell_range_bonus`、`run_move_bonus`、`affixes[].amount／delta`（範圍、回合） | 格數／回合，不放大 |
| `item_gen.yaml` `base_bonus`、`statuses[].formation／ward／share_damage` | ‰，不放大 |

### 3.3 漏換補改（`e98c85a57`，開發 PM 裁定 A1～A4、B5、B6）
- A1 `engine/turns.py` 練習木樁補滿：`hp <= 1` → `hp <= quantity_scale`（免死下限已是 1×scale，原本木樁不會補滿）。
- A2 閃現完整技能的砍費用：`flash_templates.yaml` `cost_cuts` 法力、耐力 step 1→10；`skillgen/complete.py`、`flash_trade.py` 的「至少留一格」改用新的 `CoreRules.cost_floor(field)`（法力、耐力 1×scale，其他 1）。
- A3 `sim/skill_fuzz.py` `_MANA` 99→990。
- A4 文字：`races.yaml` 過充「回復 10 點」→100；`core.yaml` sturdy「護甲 +1」→+10；`skill_primitives.yaml` 免死的 `player_description`「剩下 1 點生命」→10、`description_zh`「改為 1」→「改為 10（1 × quantity_scale）」，`workshop_text.yaml` 兩筆對應的原文與玩家版同步。
- B5 閃現「輕巧」（`skillgen/flash_ops.py` `_light_cost_drafts`）：法力、耐力一格 1×scale。接受「這 7 招現在會出輕巧」：`skill_flight`、`skill_hex_bolt`、`skill_rime_touch`、`skill_soul_reap`、`skill_static_palm`、`skill_wil_cinder_hex`、`skill_wil_storm_hex`——法力 30→20、實付 24→16、強度只降不升（`strength_moves == (False, True)`）。霜寒之觸同樣會出（30→20、1d8→1d6）。7 組參數都保留，期望改成「會出」；「實付不變就停、不改試別項」改用 100‰ 的規則造情境（20→10 實付都是下限 10）。
- B6 `test_variant_ai`（走進水裡放潮槍）：原本的分數：普攻 5.84 < 走進水 6.0；換算後普攻 7.91（火焰下限 25% 的捨去變細，期望傷害 1.17→1.58）。改的輸入：敵人 `armor_bonus` 20→160（`_scene` 加 `armor_bonus` 參數，只這個測試用）。改後普攻 5.86 < 6.0，AI 照舊先走進水裡、再放水中貫穿；斷言沒動。

### 3.4 Python 寫死的量類字面值（`b9043a06d`，開發 PM 裁定）

重產 parity 夾具前抽樣時，大變化「轉召喚」出現「法力 8」（＝換算前 0.8），追到程式裡寫死的候選費用，之後對 `src/` 全面掃描（`mana`、`stamina`、`hp`、`heal`、`shield`、`flat`、`damage`、`amount`、`armor`、`attr` 後面接數字的 dict、關鍵字參數、預設值、`randint` 範圍、`± 常數`、`max(1, …)`、`hp - 1` 等）：

| 檔案:行號 | 原值 | 判斷 | 理由 |
|---|---|---|---|
| `skillgen/flash_major.py` 197、218、235～237、270、404、423～425、482、507（8 個 `cost=cost` 呼叫點） | 候選費用 `{"mana": 2}`、`{"mana": 8, "cooldown": 3}` 等 | **改** | 法力是量類；呼叫點改成 `lib.ruleset.core.scaled_cost(cost)`（法力、耐力 × scale，冷卻不變） |
| `skillgen/composer_recipes.py` 85～92 | 護主、伴生費用 `mana` 2、4 | **改** | 同上 |
| `skillgen/whiteboard.py` 333、373 | `rng.randint(passive_mana.min, max)`、`reaction_mana` | **改** | 範圍已 ×10，改用 `quantity_randint` 步距 10（X10-1 裁定 5） |
| `skillgen/whiteboard.py` 428 | 姿態法力 `randint(...) + (tier − 1)` | **改** | 同 composer 的姿態：`quantity_randint` ＋ 每階 × scale |
| `engine/gear/core.py` 462 | 裝備代價失 HP「最低剩 1」 | **改** | 「不會致死」的下限，同免死 1×scale |
| `world/situations.py` 455 | 狀況受傷「`char.hp - 1`」 | **改** | 同上 |
| `world/economy.py` 445～447 | 野外道具「至少回復 1」 | **改** | 量類下限，同 `min_damage` |
| `content/environment.py` 372 互動 `min_damage` 預設 1 | | 不改 | 只有導電用到，內容兩筆都寫了 `min_damage: 10`；pydantic 預設拿不到倍率（同 X10-2a 裁定 8） |
| `content/forms.py` 253～259、`content/rules.py` 116～141 預設值 | | 不改 | X10-2a 已擋：scale 10 時缺欄位會報錯 |
| `content/roguelite.py` 88～104 `_default_heroes` | HP 60、法力 20… | 不改 | 內容 `roguelite.yaml` 有寫 `heroes`，預設不會用到；記待決 |
| `world/situation_coverage.py` 76 `base_attribute=10` 等 | | 不改 | 279 行起全部用內容的值覆寫 |
| `content/environment.py` 971 `infuse_threat_damage` | | 不改 | X10-1 裁定 2：AI 單位 |
| `content/composer_rules.py` 317、`engine/effects/models.py` 465／472、`content/skill_rules.py` 295、`rules.py` 524／527 | | 不改 | 層數、地形高度、傷害格數、d20 懲罰 |
| `content/parts.py` 212、`rules.py` `max_hp_for`、`summons.py` 62、`world_enemies.py` 219、`engine/forms.py` 240、`engine/gear/core.py` 300、`skills/revive.py` 111、`world/battle.py` 313／1018、`roguelite/progress.py` 159 | `max(1, …)` | 不改 | 「活著」或最大 HP 的下限（同 X10-2a 裁定 3 的 `max_hp_for`；progress 159 為本段裁定 C） |
| `sim/skill_fuzz.py` 292、300 `hp = 1` | | 不改 | fuzz 造「HP 低於門檻」的條件，1 仍成立 |
| `sim/commanders.py` 88、`difficulty_sweep.py` 183 | | 不改 | 哨兵值、docstring |

## 4. 快照與夾具（交付項目 3）

### 4.1 預測（重產前寫下）
- 會變：`tests/cli/snapshots/cli_output_hashes.json`、`tests/skillgen/fixtures/refactor_3wr2.json`、`client/src/ui/fixtures/skillCards.json`、`client/src/battle/fixtures/glossary.json`（若有量類文字）、`tests/cli/snapshots/llm_propose_mock.txt`（可能）、`tests/roguelite/fixtures/flash_history_3wr1.json`（只在測試失敗時）。
- 不變：OpenAPI 快照、`unitDolls.json`、`raceLooks.json`、其他手做的前端夾具（沒有過期檢查）。

### 4.2 實際
| 檔案 | 結果 |
|---|---|
| `cli_output_hashes.json` | 24 鍵全變（重產） |
| `refactor_3wr2.json` | complete 346／406、retier 344／406 變；flash 見下 |
| `skillCards.json`、`glossary.json` | 變（`export_client_fixtures.py` 重產） |
| `llm_propose_mock.txt` | **沒變**（Mock 提議的輸出不含量類數字），預測「可能」 |
| `flash_history_3wr1.json` | 沒重產：`test_retier.py` 沒失敗 |
| OpenAPI、`unitDolls.json`、`raceLooks.json` | 沒變，同預測 |
| `tests/world/frozen_replay/{hero,world_rules,quests}.json` | 子 agent 照內容 ×10 改了凍結輸入，`BEFORE_6CR2` 雜湊 `d2aedac4…`→`837a1238…`（開發 PM 裁定 B7 接受）。逐欄比過，只差在量類 ×10（屬性、HP 400、護甲 10、每級屬性點 20、任務技能法力 60）與法力上限 17→168（×1400‰ 捨去） |

### 4.3 抽樣核對（每類 ≥ 3 筆）

做法：用換算前的內容（`git archive f6d2bc957 content`，以 `TRPG_CONTENT_DIR` 指過去）跑同一份程式，倍率 1 時輸出和換算前相同——**舊內容重跑出的 7 個 CLI 輸出雜湊和舊快照逐一相同**，證明對照組可信。再把新舊輸出逐行比數字：同一位置的數字分成「相同」「×10」「捨去（和 ×10 差不到 10）」「其他」，行的骨架（數字遮掉後）不同就算戰鬥分岔、停止比對。

| 類別 | 抽樣 | 結果 |
|---|---|---|
| CLI `skills list` | 1 份（870 行） | ×10 407、捨去 14（法力打 800‰ 後的實付）、相同 934（AP、射程…）、其他 0 |
| CLI `skills show` 分片 | 00、05、10 | ×10 24／24／27、捨去 0／1／0、其他 0 |
| CLI 戰鬥 | `open_plain_trapper_7`、`oil_depot_fire_7`、`default_flat_42` | 分岔前：×10 98／155／119、捨去 28／36／53、其他 5／5／8。「其他」全是 HP 的累計值（例：每下 6 點 vs 68 點〔6.8 捨去〕，HP 25→19 vs 242→174），即前面每次捨去的累加。分岔點分別在第 88、128、110 行，都在第一個捨去之後 |
| parity：complete＋retier | `skill_fire_bolt`、`skill_rime_touch`、`skill_war_hymn`、`skill_wind_blade` | 12 個數字全是 ×10 |
| parity：flash 出題 | `afterimage_vow@3@1`、`cleave@11@1`、`blood_rage_slash@5@2` | 24 個數字全是 ×10（修 3.4 之前 `blood_rage_slash` 的轉召喚出現「法力 8」，就是這樣抓到漏換） |
| 前端 `glossary.json` | 全檔 | 18 個數字全是 ×10 |
| 前端 `skillCards.json` | 全檔 | ×10 9、捨去 6（法力 3→32、5→48：800‰ 打折後的實付，舊單位四捨五入成 3、5） |

**不是 ×10、也不是捨去的變動**：
- parity flash 的鍵：舊夾具 126 鍵、新的 123 鍵，取樣的招不同。原因是取樣規則「依 ID 排序等距取約 40 招」在舊內容與新內容下算出的是同一組 41 招（已用舊內容驗證），舊夾具是在更早的技能表下產的，從沒重產過；這次照標準程序重產，取樣點跟著現在的技能表。和換算無關。

## 5. 改測試

依開發 PM 同意，開了 3 個 Opus 子 agent 分目錄改（同一個 worktree、檔案不重疊、不放寬斷言、可疑的不改先回報；commit 由我做）：

| 組 | 目錄 | 改的檔 | 改的測試函式（約） |
|---|---|---|---|
| A | `tests/engine` | 90 | 約 220（含共用情境函式） |
| B | `tests/api`、`tests/content`、`tests/world` | 21／11／16（含 3 個凍結 JSON） | 約 95 |
| C | `tests/roguelite`、`narrative`、`sim`、`skillgen`、`llm` | 8／3／2／15／0 | 約 60 |
| 我 | `tests/cli`、`tests/test_x10_*.py`、`tests/sim/test_difficulty.py`、補改後的幾個檔 | 2＋3＋若干 | 約 30 |

改法：輸入是舊單位的跟著 ×10（屬性、HP、法力、詞條值、自造技能費用），讓情境意思不變；期望值改成新值（×10 或捨去後的實際值，捨去都在註解寫明）；假設骰面不乘的計算改成 × `quantity_scale`。屬性上限是 999，原本的「極大值 500」改成 999。審過整份 diff：刪掉的 assert 252 行、加入的 253 行，新加的不等式斷言都是原本就是不等式、只是數字 ×10。

`tests/test_x10_scale.py` 改成「內容已是 10，換回 1 比對」，並加了圓盾、控制抵抗、預設 `min_damage`、`mana_cost`、`minimal_filler` 的測試。

### 換種子（15 處，都在測試旁註解，原因都是捨去讓戰鬥分岔、事件不再出現）
| 測試 | 舊 → 新 | 掃描範圍 |
|---|---|---|
| engine `test_collision::test_ai_battles_with_collisions…` | 1 → 2 | 0～29 |
| engine `test_combo_resources`（build_seer 法力） | 9 → 11 | 0～39 |
| engine `test_grant_skill::test_ai_battle_with_wings_replays` | 11 → 12 | 0～39 |
| engine `test_hurl_object::test_an_ai_battle_hurls_objects_and_replays` | 35 → 81 | 0～199 |
| engine `test_reaction_events`（build_tank swamp 悲憤） | 2 → 3 | 0～29 |
| engine `test_rewrite_primitives`（build_support SkillCopied） | 1 → 4 | 0～39 |
| engine `test_scene_ai::test_an_ai_battle_with_a_topple_replays` | 3 → 6 | 0～39 |
| engine `test_totem` 整場與重播 | swamp 2 → 4 | 0～29 |
| world `test_elite_duel_rg2` `WON_SEEDS` | (0, 11) → (28, 116) | 0～139 |
| api `test_reactions_telegraph`（兩份清單） | open_plain 7→8、ruined_fort 5→6 | 0～15 |
| api `test_routes::test_waiting_for_a_decision_rejects_actions_with_409` | 7 → 8 | 0～15 |
| api `test_run_autosave` 兩個測試 | 0 → 4 | 0～11 |
| sim `test_skill_fuzz::test_one_hundred_seeds…` | `seed_start` 0 → 100 | 0～399 |
| cli `test_run_cli::test_run_auto_reaches_a_major_flash…` | 18 → 20（17 照舊） | 11～30：17、20、21、23～27、29 |

子 agent 用舊內容對照確認過幾個：例如 api open_plain 種子 9 是盜賊弓手三箭 122＋146＋134＝402，剛好超過英雄 HP 400；舊單位 12＋14＋13＝39 < 40。

另外兩個不是換種子但不只是 ×10 的測試輸入調整（子 agent 回報、我看過）：
- `test_displace_ai`：場景原有的校準參數 `hit_target` 11→12（普攻捨去後分數 25.8 超過互換 25.0；12 時 23.7）。
- `test_skill_conditions::test_target_hp_below_is_strict_at_the_boundary`：原測試把 `max_hp=36` 設在沒用到的 state 上，靠範本 HP 35 碰巧過；改成每場都設 360。
- `test_support_statuses::…floor_once`：`flat` 110 時逐步捨去和一次捨去結果相同、測不出差別，改用 111（期望 97，逐步會是 96）。

## 6. 回歸（交付項目 4）

同 X10-2a 的 78 場（15 張正式地圖 × 種子 1、7；`open_plain` 種子 3 × 8 個 build；4 張頭目圖 × 種子 3～12），基準是換算前（`f6d2bc957` 內容，events 27,376，和 X10-2a 相同），新的是 `122060224`。

| 指標 | 換算前 | 換算後 |
|---|---|---|
| 我方勝 / 敵方勝 | 44 / 34 | 47 / 31 |
| 勝方相同 | — | 67 / 78 |
| 勝方與輪數都相同 | — | 45 / 78 |
| 平均輪數 | 4.49 | 4.29 |
| 輪數差（新 − 舊） | — | −3：1 場、−2：3、−1：15、0：50、+1：9 |
| 動作序列完全相同 | — | 5 / 78 |
| 每個單位 HP 比例完全相同 | — | 4 / 78 |
| 單位 HP 比例（‰）平均絕對差 | — | 91（604 個單位） |

**差異來源**（逐場找「第一個既不相同也不是剛好 ×10 的數字」與「事件流第一次分岔」）：
- 第一個捨去差異：**法力上限 ×1400‰ 61 場**（`turn_started.mana`）、**傷害倍率 ‰ 捨去 17 場**（`damage_dealt.amount` 9、`base_amount` 6、`object_damaged.amount` 2），正好是 X10-2a 的兩個捨去來源，數字和 X10-2a 試跑一致。
- 分岔都在第一個捨去之後（74 場），**沒有一場在狀態還是精確 ×10 時就做了不同決定**；4 場沒有分岔。
- 勝方改變的 11 場：`bandit_lair_s1`、頭目 `bandit_lair_s3`／`s5`、`cloud_summit_s5`／`s6`、`molten_heart_pit_s4`／`s7`、`bridge_chasm_s1`、`cliff_outpost_s7`、`molten_heart_pit_s7`、`oil_depot_s7`；都屬上述分岔，沒有別的原因。
- 和 X10-2a 試跑相比，勝方相同 63→67、事件總數 27,376→26,446：這段多改的漏換（控制抵抗、圓盾、預設最低傷害、木樁、費用字面值）讓結果更接近換算前。
- **沒有修任何數值。**

## 7. 檢查

（最後的 commit `3e149d07e`；之後只加這份報告）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（全專案，1733 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0 |
| `rescale.py --check` | 0 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（979 passed） |
| 分目錄 `pytest -n 8`（預設標記） | 全部 0：engine 5120、skillgen 4634（7 skipped）、content 3166、api 1336（1 skipped）、world 1328、roguelite 279、narrative 475、sim 180、llm 495、server 77、bot 67、shared 72、頂層 180 passed |
| `tests/api/test_openapi_snapshot.py`、`test_client_fixtures.py` | 0（OpenAPI 沒變） |
| 前端 `tsc --noEmit` | 0 |
| 前端 `vitest run` | 0（4788 passed；`panelIcons.test.ts` 的「法力 4」改 40） |
| 前端 `vite build`（含 tsc） | 0 |

每個程式 commit 都跑了相關目錄的測試；`-m slow` parity＋cli 在換算 commit（`f3a405238`）與補件 commit（`51a9bcd85`）時預期失敗（夾具還沒重產：parity 753、CLI 雜湊 24、`run auto` 種子 1），重產後（`122060224`）全過。重產只做一次，放在所有程式修改之後。

## 8. 版號
- `LOG_FORMAT`：不升（`trpg-battle-log/135`）。這段的引擎改動（預設最低傷害、圓盾、木樁門檻、不致死下限）在 `quantity_scale: 1` 時結果完全相同；舊紀錄內嵌的規則包是倍率 1，重播不變。內容改了由 `ruleset_hash` 區分（`戰鬥紀錄格式變更.md` 1.2）。
- `PROMPT_VERSION` 與其他 prompt 版號：不升。`tests/llm` 的 prompt 快照與雜湊都過；變的只有 `available` 裡的原語資料（4-L2 裁定：資料不升版）。
- 提議 schema：沒變。OpenAPI：沒變，不重產。

## 9. 待 PM 決定
1. **舊存檔與舊單位**：roguelite 存檔、大世界角色存檔裡的 HP、屬性、法力是換算前的單位，載入後套新規則會差 10 倍（例如 `test_field_ctx_replay` 的凍結英雄套新規則後 HP 只剩 1）。這段沒做存檔遷移（規格沒寫）。上線前要決定：季末重置、還是寫一次性的 ×10 遷移。
2. **`tests/skillgen/helpers.py` 的 `_data` 預設 cost 耐力 8**（舊單位，9 個檔共用、測試都過）：照裁定先不動，排進佇列。
3. **`content/roguelite.py` 的 `_default_heroes`** 與 `content/environment.py` 互動 `min_damage` 預設 1：內容都有寫，預設不會用到，所以沒改；若要讓 Python 預設也是新單位，可比照 X10-2a 在 scale 10 時缺欄位就報錯。
4. **說明文字的舊數字沒全面掃**：這段只改了被測試抓到或子 agent 回報的 4 段（過充、堅韌、免死兩處＋工坊文字）。技能、狀態、地圖等手寫的 `description_zh` 若寫了量類數字仍是舊單位；顯示方式 X10-3 決定，建議那時一起掃。
5. **parity 夾具 flash 取樣點換了一批**（第 4.3 節最後一點）：照標準程序重產的自然結果，和換算無關；若希望保留舊取樣點，要改測試的取樣方式。

## 10. 平衡疑慮
- 換算後我方勝率在這 78 場從 44 升到 47、平均輪數 4.49→4.29，方向同 X10-2a：傷害尾數變細普遍略高、法力上限略低。樣本小，已由玩法 PM 記進平衡待查（X10-2a 裁定 2），這段沒動數值。

## 開發 PM 裁定（2026-11-20）

合併：`Merge X10-2b`（--no-ff）。合併後 ruff、mypy、`trpg content check` 都是 0，`quantity_scale: 10`。途中裁定（control_resist、圓盾、min_damage 預設、A1～A4、B5～B7、Python 字面值掃描）都照做了。

回歸：勝方相同的場數 67／78，比 X10-2a 試跑的 63 多；分岔來源和 X10-2a 相同，只有兩個捨去來源。沒有漏換的跡象，不修數值，照平衡待查第 32 項交給使用者在工坊調。

待決 5 件：
1. 舊存檔是舊單位：轉專案 PM，請使用者決定季末重置還是寫遷移。決定之前先不開服。
2. 照之前的裁定，排進佇列。
3. 接受。
4. 接受，X10-3 一起掃手寫說明文字裡的量類數字。
5. 接受。

## 補件：非 slow 的 cli 測試（2026-11-20，合併後全量檢查擋下）

原因：交件前分目錄跑時漏了 `tests/cli`（只跑了 `-m slow` 的 parity＋cli），7 個一般 cli 測試沒跑到。在分支 merge main（`fa609647a`）後修正。

### 碎骨重擊的預算：不是 bug
- `test_budget_cli::test_budget_shows_when_the_allowance_is_capped` 在測試裡把碎骨重擊的代價改成 `{"stamina": 80, ...}`，寫的是**舊單位**的 80。換算後 80 耐力＝舊的 8，折抵只有 20‰（不是 200→上限 150），所以總折抵到不了 850、也就不會截斷，比例算成 64.3%。
- 預算程式照新單位算是對的：`耐力 × mana_per_point ÷ (stamina_per_mana × quantity_scale)`，800 → 200 → 上限 150，150＋300＋400＝850 → 上限 500，和換算前完全相同。測試輸入改成 800 後通過。
- 全內容掃描：換算前內容（`f6d2bc957`）與現在內容各算一次 434 招的預算（`total`、`usable`、比例、合格、每一筆折抵的 ‰）：**數值 0 筆不同**（373 招只有折抵的標籤文字變了，例如「法力 6」→「法力 60」）；換算前合格、換算後不合格的 **0 招**；不合格的招數前後都是 4 招（同一批既有例外）。所以沒有補「scale 1 對 scale 10」的新測試；既有的 `tests/test_x10_scale.py::test_budget_points_same_before_and_after_x10` 已逐招比總點數與每筆折抵（343 招，召喚技除外），這次的全內容掃描把召喚技也涵蓋了。

### 修正
| 測試 | 原因 | 改法 |
|---|---|---|
| `test_budget_cli::test_budget_shows_when_the_allowance_is_capped` | 測試輸入是舊單位 | 耐力 80→800 |
| `test_run_cli::test_run_new_rejects_bad_input` | 開局配點 4→40 | `str=10`、「必須分配 40 點」 |
| `test_run_cli::test_run_new_writes_a_save_and_show_reads_it` | 配點輸入是舊單位（`str=3,con=1` 配不滿 40 點） | `str=30,con=10`、「力量 130」「體質 110」 |
| `test_demo_maps::test_simple_ai_weather_and_deploy_options` | 戰士 HP 寫死 60 | 600 |
| `test_demo_maps::…[ruined_fort]` | 換種子 3 → 4：種子 3 換算後不再出現半掩護（捨去分岔） | 重掃 0～59 有 34 個可用 |
| `test_basic_actions_cli::test_open_plain_battle_uses_guard_and_replays` | 換種子 27 → 44：27 不再守護 | 重掃 0～59 只有 44 |
| `test_striker_trapper_battle::test_striker_battle…` | 換種子 20 → 64：20 不再放雷霆終結 | 重掃 0～299：64、67、76、79、92、96、111、124、167、218 |

換種子累計 18 處（第 5 節的 15 處＋這 3 處）。三個舊種子在換算前的內容下都照舊通過，原因同第 6 節：捨去讓戰鬥分岔。

commit：`bbeb5c532`（數字）、`6f4df4190`（換種子與戰士 HP）。

### 補件後的檢查（`6f4df4190`）
- 每個目錄的非 slow 測試各跑一輪，`-n 8`，結束碼全部 0：cli 148、engine 5120、skillgen 4634（7 skipped）、content 3166、api 1336（1 skipped）、world 1328、roguelite 279、narrative 475、sim 180、llm 495、server 77、bot 67、shared 72、頂層 180 passed。
- `ruff check`、`ruff format --check` 0。只改了測試，沒有動 `src/`、`content/`。
