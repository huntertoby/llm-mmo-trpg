# Phase 3C-6b 報告：收尾（內容與 build 整理、組合器、模擬）

## 1. commit

| commit | 內容 |
|---|---|
| 6bf8e4e | 6 個示範技能（`content/skills/`）、3 個新 build、`build_fire` 的念力投擲搬到念力流、`tests/content/test_sim_builds.py`、`test_budget_cli.py` 技能數 |
| b3301ea | 8.2C：守護者擋下近戰後轉身（`reactions.py`、`interpreter.py`）、`LOG_FORMAT` `/34`、2 個新測試 |
| e03ac43 | 念力投擲的測試改用 `build_telekinesis`、CLI 快照重錄 |
| 1a99fac | 組合器：傳說、修正技能、新觸發時機、新條件、新原語、賭博型（`composer_special.py` 等）；fuzz 驗收腳本擴充；組合器測試 |
| e8aa6a4 | 組合器：固定點數的傳說核心改用完整合格區間（0.70–1.00） |
| 5e006bb、172027d | 組合器測試跟著調整（預算區間、慢速分佈測試） |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 內容（8.1）

**協同管道對照（每條 ≥ 2 個示範技能）**

| 管道 | 示範技能（★ 本段新增） |
|---|---|
| 1 狀態當燃料（`consume_status`） | 引爆燃燒、★毒血迸發（引爆中毒）、★撕裂傷口（引爆流血，武器版）、標記引爆（被動） |
| 2 環境當中介 | 灰燼誓約、召潮、念力投擲、★燈油瓶（鋪油，等火）、★烈焰投擲（技能帶火，丟出去的油桶直接爆炸） |
| 3 監聽自己的動作 | 裂骨印記（`on_collision`）、蝕心追擊（`on_status_applied`）、烈焰護身（`on_cast_tag`）、潮汐絆腳（`on_enter_surface`）——四個時機各 1 個 |
| 4 標籤／元素改寫 | 雷之手（普攻帶雷）、重踏（推擊類 +1 格）、★灼熱推擊（`push`／`control` 標籤的技能帶火：推進油裡就著火） |

另外新增 ★念力傾倒（法術版推倒，射程 4）。新增技能共 **6 個**（上限 10）：毒血迸發、撕裂傷口、灼熱推擊、燈油瓶、烈焰投擲、念力傾倒；全部通過 `trpg skills budget`（預算 72–99%）。

**build 對應（8.1 要求 4 個 build ＋ 賭徒 ＋ 3D 整理）**

| 8.1 的要求 | 對應 |
|---|---|
| 協同主題 1「推牆焚燒」（推擊改造 ＋ `on_collision` ＋ 火表面） | ★新增 `build_wallburn`（燈油瓶、灼熱推擊、重踏、破城衝撞、裂骨印記、撕裂傷口：撞擊 → 流血 → 撕裂引爆） |
| 協同主題 2「狀態引爆」（施加狀態 ＋ `on_status_applied` ＋ `consume_status`） | ★新增 `build_detonator`（火焰箭、毒雲、咒印飛彈施加狀態；蝕心追擊；引爆燃燒、毒血迸發、標記引爆） |
| 物件主題 1「念力流」（投擲 ＋ 推倒） | ★新增 `build_telekinesis`（念力投擲、烈焰投擲、念力傾倒、碎裂衝擊、寒鎖、瞬移、烈焰護身）；念力投擲從 `build_fire` 搬過來（火焰流回到純火焰） |
| 物件主題 2「撞擊流」（推擊改造 ＋ 撞擊 ＋ `on_collision`） | **已被 `build_push` 涵蓋**（重踏、破城衝撞、裂骨印記、震地推倒、颶風踢）；`build_charger` 是自身位移（dash／leap／swap）主題，不是撞擊流。不另加 |
| 賭徒／狂戰士流 | 3D-7a 的 `build_gambler` 已涵蓋 |
| 3D 各段示範技能的整理 | 每個手寫技能都有 build 或單位裝備（`test_coverage.py` 允許清單維持空）；召喚師在 3D-4b、偵察破咒／炸彈／飛翼／賭徒在 3D-8、衝鋒／放逐在 3D-2 都已各有主題 build。逐一核對主動 ≤ 6、被動 ≤ 3、反應 ≤ 1，沒有需要搬動的技能（只搬了念力投擲） |

build 總數 **22**（超過 20 個）。**建議合併／淘汰**（不自行刪除，見第 7 節 #4）：

1. `build_wallburn` → 併入 `build_push`（撞擊流）：兩者都是推擊＋撞擊，wallburn 的特色技能（灼熱推擊、燈油瓶、撕裂傷口）可以替換 push 目前的 `arcane_blade`／`bloodlust`；wallburn 前段 1 次、`ruined_fort` 最後一名。
2. `build_detonator` → 併入 `build_warlock`：兩者共用咒印飛彈、毒雲、標記引爆、蝕心追擊，而 detonator 太強（見第 4 節）；合併後 warlock 取兩者的引爆技能。
3. `build_tank` 與 `build_guardian`：兩者都是劍＋盾＋嘲諷的坦克，前段次數 0／2，可併成一個。
4. 備選：`build_winged`、`build_gambler`（前段 0，勝率最低的兩個），等平衡階段決定要調數值還是淘汰。

### 2.2 隨機組合器（8.1、8.2A 最後一條）

新增 `src/trpg/skillgen/composer_special.py`；其餘改動在 `random_composer.py`、`composer_parts.py`、`content/skill_composer.yaml`（`condition.self_conditions`、`special.modifier_permille`）、`content/skill_triggers.yaml`（四個新時機的 `random_composer` 旗標）。所有新流程都用 `Rng(seed).fork(...)` 的獨立串流，沒有抽到新內容的種子結果不變。

| 項目 | 組合器現在能產生 |
|---|---|
| **傳說（含源力成本）** | 稀有度權重抽到 legendary 時（原本降為史詩）改走 `compose_legendary`：核心三擇一（修正規則／規則改變 `rule_change`／改寫規則型原語 `grant_ap`、`reset_cooldown`、`cheat_death`、`redirect_damage`、`extra_reaction`）＋ `cost.source` 1 或 2 點；修正與規則改變型有 `activation`（timed／battle），改寫規則型冷卻 2–6。以「列舉候選 → 預算合格 → 亂數挑一個」組合（這些結構點數是固定值，沒有可爬升的旋鈕） |
| **修正技能（史詩）** | `kind: modifier`：12 種改變（傷害‰、命中、冷卻、推擊距離、AP、射程、元素、標籤、穿透、範圍、形狀轉換、含自己）× 套用對象（所有攻擊／所有技能／基本動作／標籤）× 30% 目標狀態條件；獨立串流以 10% 機率對史詩以上的未指定骨架種子改組修正技能 |
| **新觸發時機** | `on_cast_tag`（一定帶元素 `tag`）、`on_status_applied`（一半機率指定狀態）、`on_collision`、`on_enter_surface`（一半機率指定表面）加進被動的候選 |
| **新條件** | 新增 `self_conditions`：`moved_this_turn`、`adjacent_ally`、`first_round`；目標條件加 `target_isolated`（fuzz 場面會布置成條件成立） |
| **新原語** | `restore_resource`（法力）、`dispel`、`reveal`、`steal_buff`、`delayed_damage`（只限法術技）；`dispel`、`reveal` 在骨架清單裡本來就有，但組合器沒有替它們填必填參數，現已補上 |
| **賭博型** | `gamble`：strike 的附帶效果，必須有傷害效果、一定排在最後，成功率（30%–95%）是強度旋鈕，成功時傷害 ×1.5–3、失敗時 70% 機率反噬 25–75% |

**組合器仍不產生（只給手寫者）**：`summon`、`zone`、`leap`、`swap`、`swap_any`、`teleport_target`、`charge_through`、`shadowstep`、`hurl_object`、`topple`、`revive`、`grant_skill`、`copy_skill`（原因：落點／交換對象／召喚物範本／場上物件／別人剛施放的技能等需要場面配合）；`rule_change` 與改寫規則型原語只出現在傳說；條件 `flanked`、`from_behind`、`cast_tag_this_turn`、`self_concealed`（需要特定站位或前一個動作，驗收場面無法穩定成立）；`consume_status` 骨架（`then` 巢狀效果，3C-3b 已規定）；`on_hit_effects` 型修正規則。

### 2.3 8.2C

守護者替隊友擋下近戰（普攻或單體近戰技）時，轉身的是守護者（原本被瞄準的人朝向不變）。`_attack_once` 多回傳承受攻擊的單位；技能路徑把 `melee_victims` 的最後一筆換成守護者。`LOG_FORMAT` `/33` → `/34`。測試：`test_the_guardian_who_takes_a_melee_attack_turns_not_the_original_target`、`test_the_guardian_turns_when_a_melee_skill_is_intercepted`。背刺次數不變（見 4.3）。

## 3. 驗收條件逐條（8.5）

| # | 條件 | 結果 |
|---|---|---|
| 1 | 每條管道 ≥ 2 個示範技能、4 個新 build（或說明由 3D 涵蓋）、`test_coverage.py` 通過、build 超過 20 個時建議合併 | 通過：見 2.1（新增 3 個 build、1 個由 `build_push` 涵蓋、賭徒由 `build_gambler` 涵蓋）；`tests/content/test_coverage.py`（允許清單維持空）、`tests/content/test_sim_builds.py`（22 個 build 逐一通過預算與驗證）；22 個 build，合併建議見 2.1 |
| 2 | fuzz 1000 個通過；組合器能產生傳說（含源力成本） | 通過：`uv run python scripts/skill_fuzz.py --count 1000` 結束代碼 0（摘要見 4.4）；`test_legendary_is_composed_with_one_core_and_a_source_cost`、`test_the_modifier_skeleton_composes_epic_modifiers_and_legendary_modifier_rules`、`tests/skillgen/test_composer_3c6b.py` |
| 3 | 前端顯示項目齊全 | 本段沒有改前端（3C-6a 已完成，PM 用瀏覽器驗收）；`client` typecheck 與 vitest 163 個通過 |
| 4 | matrix 與 completion 摘要、completion 異常 0 | 通過：見 4.1–4.2（matrix 2200 場異常 0、completion 450 場異常 0） |
| 5 | `check.py` 全過；重播一致 | 通過：`uv run python scripts/check.py`（ruff、format、mypy、lint-imports、pytest **2879**、client typecheck、vitest 163）；重播：`test_an_ai_battle_hurls_objects_and_replays`、`test_cli_output_matches_the_recorded_snapshot`、`test_ai_battle_with_backstabs_replays` |

## 4. 模擬

### 4.1 `trpg sim matrix --seeds 10`

22 個 build × 10 張地圖 × 10 種子 ＝ 2200 場，**異常 0、平手 0**，144 秒（`--jobs 16`，沒有超過 30 分鐘）。前段 ＝ 每張地圖（類型）前 7 名（22 ÷ 3）。

| build | 前段類型數（/8） | 平均勝率（8 類型） | 備註 |
|---|---:|---:|---|
| build_storm | 8 | 92.5% | 全前段 |
| build_detonator（新） | 8 | 89.4% | 全前段 |
| build_fire | 6 | 90.0% | |
| build_warlock | 7 | 80.6% | |
| build_summoner | 7 | 80.0% | |
| build_bomber | 4 | 71.2% | |
| build_banisher | 3 | 75.6% | |
| build_telekinesis（新） | 2 | 82.5% | oil_depot 第 2、corridor 第 4 |
| build_ranged | 2 | 75.0% | |
| build_guardian | 2 | 73.1% | |
| build_striker | 2 | 74.4% | |
| build_seer | 2 | 73.1% | |
| build_support | 1 | 73.1% | |
| build_trapper | 1 | 68.8% | |
| build_wallburn（新） | 1 | 69.4% | swamp 第 7；ruined_heights 最後一名（20%） |
| build_push | 0 | 72.5% | 撞擊流，corridor 第 17 |
| build_tank | 0 | 65.6% | |
| build_assassin | 0 | 56.9% | 最低 |
| build_healer | 0 | 78.8% | |
| build_charger | 0 | 70.0% | |
| build_gambler | 0 | 65.0% | |
| build_winged | 0 | 61.9% | |

**與 Phase 2H 驗收時比較**（2H 驗收當時 12 個 build，前 3 名為前段；結果記於 `docs/PM交接.md`）：標準 1 當時不通過（`build_storm` 8 類型全前段）→ 現在仍不通過（`build_storm`、`build_detonator`）；標準 2 當時不通過（`build_tank`、`build_assassin`、`build_healer`）→ 現在不通過者擴大為 7 個（`build_push`、`build_tank`、`build_assassin`、`build_healer`、`build_charger`、`build_gambler`、`build_winged`）。前段定義隨 build 數放寬（12 個 build 時前 4 名，現在 22 個前 7 名），所以絕對次數不能直接比；`build_tank`、`build_assassin`、`build_healer` 三個舊的弱勢 build 仍然是 0。2H 以前的逐格數字沒有留存，這裡只能比標準結果。

**新 build 的地圖偏好（8.1 的期待）**

- 念力流：oil_depot 第 2、corridor（narrow_halls）第 4，open_plain 第 11、ruined_fort 第 8；不是任何地圖的第 1 名 → 符合「物件多的地圖較強、不是全地圖最強」。
- 撞擊流（`build_push`）：**不符合期待**，狹窄走廊（narrow_halls）第 17、前段 0 次；沒有任何地圖的前段。wallburn 在 swamp 第 7，但 narrow_halls 第 11、ruined_fort 最後。撞擊流目前輸出不足（不調數值，見待決 #2）。
- 狀態引爆：**全地圖前段、平均勝率 89%**，偏強。

**勝率比其他高 15% 以上（列入待決 #1）**：`build_storm` 92.5%、`build_fire` 90.0%、`build_detonator` 89.4%（全 build 平均 74.5%；高出 15 個百分點以上的是前兩個，detonator 差 0.1）；8 類型全前段：`build_storm`、`build_detonator`。

### 4.2 `trpg sim completion --seeds 5`

9 種設定 × 10 張地圖 × 5 種子 ＝ 450 場，**異常合計：exception 0、max_actions 0、draw 0 —— 通過**，35 秒。

### 4.3 背刺次數（8.3）

`uv run python scripts/backstab_counts.py --seeds 5`（10 張地圖 × 5 種子）：預設陣容我方背刺 27、敵方背刺 27、我方偷襲 12；`build_assassin` 我方 89、敵方 58、偷襲 20。與 3C-6a 的「改後」完全相同（守護者轉身規則不影響這兩個陣容）。

### 4.4 `scripts/skill_fuzz.py --count 1000`

```
隨機技能驗收：種子 0–999，共 1000 個
  組合成功 1000/1000；通過驗證 1000/1000
  可施放 1000/1000（100.0%）；合法選取共執行 2337 次
  AI 對戰 213 場（我方勝 205、敵方勝 8、平手 0）
  被動 28 個（每個打一場戰鬥）；其中實際觸發過 11 個，共觸發 16 次
  傳說 93 個（修正規則 36、規則改變 31、改寫規則 26；源力 1 點 62 個、2 點 31 個）
  修正技能（史詩）12 個
  被動觸發時機：every_n_hits 1、on_cast_tag 2、on_collision 5、on_crit 2、on_enter_surface 2、on_hit 1、on_kill 2、on_move 4、on_natural_20 2、on_status_applied 4、on_turn_end 2、on_turn_start 1
  條件：adjacent_ally 15、first_round 17、height_advantage 16、moved_this_turn 14、self_hp_below 16、target_has_status 25、target_hp_below 19、target_isolated 15、target_on_surface 10
  例外 0 個
```

新增的原語出現次數（效果數）：`restore_resource` 29、`reveal` 16、`delayed_damage` 13、`dispel` 9、`gamble` 6、`steal_buff` 6、`rule_change` 31，改寫規則型 `cheat_death` 8、`extra_reaction` 8、`redirect_damage` 4、`grant_ap` 3、`reset_cooldown` 3。

## 5. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `test_builds_file_loads_with_nineteen_builds…` → `…twenty_two_builds…`、`BUILD_IDS` | 新增 3 個 build |
| `test_budget_cli.py` 兩處 135 → 141 | 新增 6 個手寫技能（共 141） |
| `test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/33` → `/34` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 兩個雜湊改變（技能增加）；9 場戰鬥的雜湊沒有變 |
| `test_hurl_object.py`（`test_an_ai_battle_hurls_objects_and_replays`）、`test_scene_ai.py`、`test_hurl_api.py` | 念力投擲從 `build_fire` 搬到 `build_telekinesis`；hurl 測試改用念力流（種子 2 → 5，因為念力流的烈焰投擲會讓油桶爆炸，種子 5 仍有「漏油」的投擲） |
| `test_collision_triggers_schema.py`、`test_surface_consume_schema.py` | 原本斷言「新觸發時機不被組合器抽到」；現在改為斷言組合器會抽到（on_cast_tag 必帶 tag） |
| `test_gamble_schema.py` | 原本斷言組合器從不產生賭博型；改為斷言會產生且結構合法 |
| `test_random_composer.py` | 傳說不再只能手寫（`test_legendary_is_hand_written_only` 改為 `test_legendary_is_composed_with_one_core_and_a_source_cost`）、稀有度清單加 legendary、`kind`／標籤／預算區間的斷言認得修正技能與傳說（固定點數結構用完整合格區間） |
| `tests/sim/test_skill_fuzz.py` | 無需啟動的修正技能和被動一樣不能施放，只打一場戰鬥 |

## 6. 新增的複雜度 noqa

無（C901、PLR0911／0912／0915 都沒有新增）。過程中 `compose_with_stats` 一度超過 PLR0912，已拆出 `_check_passive_args` 解決；`_prepare`（fuzz）拆出 `_prepare_self`、`_prepare_targets`。

## 7. 待 PM 決定

1. **偏強的 build**：`build_storm`（92.5%）、`build_fire`（90.0%）、`build_detonator`（89.4%）；`build_storm` 與 `build_detonator` 8 類型全前段。不調數值，留給平衡階段。
2. **撞擊流不符合期待**：`build_push` 在窄路與牆多的地圖沒有變強（narrow_halls 第 17），wallburn 也不穩。可能原因：撞擊傷害太低（每次 4–5 點）、AI 不會刻意把敵人推向牆。建議平衡階段先看 AI 推擊評估，再看撞擊傷害。
3. **偏弱的 build**：`build_assassin`（56.9%）、`build_winged`（61.9%）、`build_gambler`（65.0%）、`build_tank`（65.6%）；前段 0 次的共 7 個（標準 2）。
4. **build 數量 22 個**：建議合併 wallburn → push、detonator → warlock、tank ＋ guardian（見 2.1）。要不要在平衡階段前先做，請 PM 決定。
5. **傳說的「整場／限時」兩種啟動**：組合器各以 50% 抽；整場型的預算目前自動帶 60% 係數，所以同一個修正在整場型要選更強的值。沒有額外調整。
6. **組合器的傳說 / 修正技能用完整合格區間（0.70–1.00）**，不是組合器一般的 0.75–0.95（固定點數沒有旋鈕可調）。若希望一致，需要先為規則改變／改寫規則型加強度旋鈕（例如 `grant_ap` 的 `amount`、`redirect_damage` 的 `permille` 本來就是旋鈕，只是目前沒用爬升）。
7. **`reset_cooldown`、`grant_ap` 這類改寫規則型傳說很少被抽到**（各 3–8 個／1000）：tier 1 的預算剛好卡在合格區間邊緣（手寫的 `skill_rallying_cry` 也是 74.4%）。若想增加變化，需調 `base_points` 或下限（不是本段範圍）。
8. **`LOG_FORMAT` 升到 `/34`**（8.2C 改變 AI 走位）。`docs/design/05-戰鬥.md` 5.1 還只寫「被近戰攻擊後轉身」，沒寫守護者攔截時轉身的是守護者，我沒有修改設計文件，請 PM 補一句。
9. **8.4 打法差異檢查**由 PM 做；建議試玩 `build_wallburn`（`oil_depot` 種子 3：燈油瓶 → 撞擊 → 裂骨印記流血）與 `build_detonator`（`bridge_chasm`）。
10. **前端沒有改動**；3C-6a 的網頁顯示項目由 PM 用瀏覽器驗收。

## 8. 代表性的 CLI 輸出

`uv run trpg battle --map oil_depot --seed 3 --ally-build build_wallburn`（燈油瓶命中、撞擊後裂骨印記觸發流血）：

```
  推牆焚燒英雄 施放「燈油瓶」（AP 1，法力 4，冷卻 3 回合）→ 影響 5 格
  推牆焚燒英雄 以「燈油瓶」攻擊 盜賊2：d20=16 修正 -3 熟練 +2 半掩護 -2 = 13（目標 11）→ 命中［命中 −2：矮牆掩護］
  ...
  盜賊頭目 被推得太猛，受到衝擊（1 次撞擊）
    盜賊頭目 受到 4 點撞擊物理傷害［骰 1+4］（元素修正 ×0.85），HP 69 → 65
  ★ 推牆焚燒英雄 的被動「裂骨印記」觸發（造成撞擊後，深度 1），對象 盜賊頭目（法力 2）
  盜賊頭目 獲得狀態「流血」（3 回合）
```

`uv run trpg skills random --seed 11 --rarity legendary`（組合器產生的傳說修正：階級 2、花 1 點源力、帶 `activation`）。
