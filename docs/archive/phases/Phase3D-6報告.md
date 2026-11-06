# Phase 3D-6 報告：改變規則型傳說（傳說核心三擇一、常駐類傳說的啟動）

## 1. commit

| commit | 內容 |
|---|---|
| ed52233 | 內容層：傳說核心三擇一（`legendary_cores`、恰好 1 個核心）、`SkillDef.activation`（`timed`／`battle`）、修正型傳說可花源力、`rule_change` 原語與 `EffectSpec.rule`、`content/rule_changes.yaml`（4 類、各 1 條）＋ `RuleChangeTable` 嵌入規則包、分身召喚物 `summon_afterimage`、`core.yaml` 的 `legendary_activation_ap`／`legendary_timed_rounds`、`skill_budget.yaml` 的 `legendary_battle_budget_permille`、預算（`rule_change` 點數、啟動係數）、每人最多裝 1 個規則改變、5 個示範傳說與 build 裝備、`ai_profiles.yaml` 的啟動評分；schema 測試 |
| d66f45f | 引擎：`UnitState.activations`、`trpg.engine.activations`（啟動、到期、查詢）、`UseSkill` 啟動、修正規則只在啟動後生效、四類規則改變（`trpg.engine.rule_changes` 與傷害／推動物件的判斷）、三個新事件、`UnitSummoned.orphan`、分身在環境回合到期；紀錄文字、技能說明、CLI 單位表、`UnitView.activations`、AI；引擎與 AI 測試 |
| 94ec49c | `LOG_FORMAT` `/25` → `/26`；CLI 快照重錄 |
| a18e6a6 | 網頁：OpenAPI 與 `schema.d.ts` 重產、HUD「傳說：」清單、技能卡片的啟動方式、已啟動的技能按鈕停用；API 測試 2 個、vitest 2 個 |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 傳說核心三擇一與 `activation`（0.1、6.14.4）

- `rarity: legendary` 必須有 `cost.source`，且 **恰好 1 個核心**（跨檔案檢查 `_legendary_problems`）：改寫規則型原語、修正規則（`kind: modifier` 的 `modifiers` 整組算一個）、規則改變（`rule_change`）。解決 3C-4a 待決 #2：修正型傳說現在寫得出來。
- 常駐類傳說（修正型、規則改變型）**必須**寫 `activation: timed | battle`；其他技能（含改寫規則型傳說、一般修正技能）**不可**寫。
- 修正型傳說：`kind: modifier`、裝在被動欄位，代價只能有 `source`（與可選的 `cooldown`）；`is_actionable` 為真，所以出現在技能列、可用 `UseSkill` 啟動。
- 規則改變型傳說：主動技能、形狀 `self`、`rule_change` 是唯一效果、`ap_cost` 必須等於 `legendary_activation_ap`（載入時檢查）。原語 `min_rarity: legendary`、`category: rule_change`；加進 `aura` 骨架的核心原語；隨機組合器不使用。
- 啟動 ＝ `UseSkill`：花 `legendary_activation_ap`（1）AP ＋ 源力（照常有 `skill_used`、`source_changed`），接著 `skill_activated`。啟動前修正規則／規則改變不生效；生效中的同一技能不能再啟動（「「戰神降臨」已經啟動（還剩 3 輪）」）；同一單位同時最多 1 個生效中的規則改變。
- `timed`：`expires_round` ＝ 啟動輪 ＋ `legendary_timed_rounds`（3）；持有者在那一輪的回合開始時結束（`activation_expired`），所以持有者連同啟動那一回合共 3 個回合，期間其他單位的回合也有效。`battle`：本場剩餘時間有效。狀態存在 `UnitState.activations`（可序列化）。
- 預算：常駐類傳說的係數改用「啟動 AP」的 AP 係數（1 AP → 500‰；不用修正係數 300‰，因為啟動是一次 1 AP 的動作），`battle` 再 × `legendary_battle_budget_permille`（600‰）。`trpg skills budget` 顯示「啟動 AP 1 係數 × 整場 600‰」。

### 2.2 規則改變（`content/rule_changes.yaml`、`trpg.engine.rule_changes`）

只影響持有者自己；點數（`kinds.<kind>.points`，初值）只給傳說，參數不影響點數。

| 類 | 實作 | 點數 |
|---|---|---|
| `element_heals_allies`（`element`、`permille` 100–1000） | 傷害處理器：來源單位生效中、元素相同、受傷者是同陣營且 **不是自己** → 改為治療 `傷害 × permille‰`（再乘受治療倍率，例如中毒），不扣護盾、不發 `damage_dealt`；`rule_change_triggered` ＋ `healed`。範圍：所有 `source_id` 是持有者的同元素傷害（技能、區域、燃燒等狀態） | 5 |
| `push_any_object` | 持有者推動（互動的推與撥開、技能的推擊效果）時，`blocks_move` 的物件也能推（土牆、矮牆、倒木、倒塌物）；`topplable`（石柱、枯樹）照樣倒下；`over_chasm`（木橋、薄冰）與地形不行；每次推動發 `rule_change_triggered` | 7 |
| `pass_through_apply`（`status`、`duration` 1–3） | 持有者 **步行**（`Move`）每踏進一格，相鄰（曼哈頓 1）的敵人依 ID 被施加狀態；同一次移動每個敵人一次、起點不算；比照被動觸發（自動命中、照常擲抵抗、深度 +1、受 `max_trigger_depth` 限制） | 7 |
| `on_downed_spawn`（`unit`、`duration` 1–3） | 持有者倒下（`down_unit`）時，在原地召喚 `unit`（`owner_id` 為持有者），排在持有者原本的先攻位置；`unit_summoned.orphan = true`；在第「倒下輪 ＋ duration − 1」輪的 **環境回合** 消失（召喚者已不在場）；原地不能站（深淵）時 `effect_fizzled(summon_blocked)` | 5 |

新召喚物範本「殘影分身」`summon_afterimage`（HP 14、匕首、brute）。

### 2.3 示範傳說（全部 T1）

| 技能 | 核心 | 啟動 | 源力 | 預算 | 裝備 |
|---|---|---|---|---|---|
| 戰神降臨 `skill_war_avatar` | 修正：所有攻擊傷害 +18% | 限時 | 1 | 86.4% | build_charger（被動欄位） |
| 慈焰誓約 `skill_kindred_flame` | 規則改變「慈焰」（火焰 100%） | 整場 | 1 | 95.2% | build_summoner（火牆不再燒隊友） |
| 移山之力 `skill_mountain_mover` | 規則改變「移山」 | 限時 | 1 | 80.0% | build_guardian |
| 血痕疾行 `skill_bloodwake_stride` | 規則改變「血痕」（流血 2 回合） | 限時 | 1 | 80.0% | build_striker |
| 殘影之誓 `skill_afterimage_vow` | 規則改變「殘影」（分身 2 輪） | 整場 | 1 | 95.2% | build_trapper |

### 2.4 AI

- 候選：常駐類傳說在場上有敵人時列為候選（`_placement_estimate`）。
- 評分：`_rewrite_gains` 對預覽中的 `skill_activated` 加 `activation_round_points`（4）× 生效輪數（限時為實際輪數、整場為 `activation_battle_rounds` 4），再扣源力成本（數值在 `ai_profiles.yaml` 的 `rewrite`）。
- 結果（一次性腳本，3 張地圖 × 種子 0–1）：五個 build 都會在第 1 輪啟動；血痕 9 次觸發；殘影 2 次；移山只在 open_plain 種子 1 推過一次牆（AI 不會為了推牆特別加分）；慈焰在 oil_depot 種子 0、2、3 有治療。

### 2.5 紀錄、CLI、API、網頁

- 紀錄：「✦ X 啟動了傳說「戰神降臨」（持續到第 4 輪 X 的回合開始）」「X 的傳說「戰神降臨」時間到了，不再生效」「✦ X 的「慈焰誓約」：10 點傷害改為治療 Y」「✦ X 的「移山之力」：推動了本來推不動的土牆」「✦ X 的「血痕疾行」：掠過 Y 身邊」「✦ X 的「殘影之誓」：倒下的地方留下了分身」「X 的原地留下了 殘影分身1（…，第 3 輪的環境回合消失）」。
- CLI：單位表「［傳說：殘影之誓 整場］／［傳說：戰神降臨 剩 2 輪］」；分身標「X留下，第 N 輪的環境回合消失」；`skills show` 多「啟動 限時：花 AP 1 ＋ 源力 1 啟動，持續 3 輪（啟動前不生效）」，規則改變的效果文字。
- API：`UnitView.activations`（`skill_id`、`name_zh`、`activation`、`expires_round`、`rule_name_zh`，雙方都看得到）；`SkillCard.activation`／`activation_id`，修正型傳說的 `ap_cost` 與代價顯示啟動 AP。
- 網頁：HUD「傳說：戰神降臨：剩 3 輪（第 4 輪你的回合開始時結束）」「慈焰誓約（規則改變「慈焰」）：整場」；技能卡片「啟動：…（啟動前不生效）」；已啟動的技能按鈕停用，滑過顯示「已啟動（到第 4 輪你的回合開始）」；修正型傳說的按鈕代價多一段「傳說啟動」。

## 3. 驗收條件逐條（6.1）

### 驗收 1：4 類規則改變各自的規則與邊界；每人最多 1 個

`tests/engine/test_rule_changes.py`：

| 項目 | 測試 |
|---|---|
| 慈焰：友方改為治療、啟動前照常受傷 | `test_kindred_flame_heals_allies_hit_by_the_holders_fire` |
| 慈焰：敵人、自己、其他元素照常受傷 | `test_kindred_flame_still_burns_enemies_the_holder_and_other_elements` |
| 慈焰：只算持有者的火 | `test_kindred_flame_only_applies_to_the_holders_fire` |
| 移山：啟動後才推得動土牆、事件 | `test_mountain_mover_pushes_an_earth_wall_only_after_activation` |
| 移山：矮牆、倒木、倒塌物 | `test_mountain_mover_pushes_other_blocking_objects`（參數化 3 個） |
| 移山：橋面不行、別人推不動 | `test_mountain_mover_does_not_move_floor_objects_or_other_units_walls` |
| 血痕：每次移動每個敵人一次、遠的與友方不算、啟動前沒有 | `test_bloodwake_marks_each_adjacent_enemy_once_per_move` |
| 血痕：起點不算、新的移動重新計 | `test_bloodwake_counts_again_on_a_new_move_and_ignores_the_start_tile` |
| 血痕：觸發深度上限 | `test_bloodwake_respects_the_trigger_depth_limit` |
| 殘影：原地、接替先攻位置、orphan、持續 2 輪；啟動前沒有 | `test_afterimage_leaves_a_double_in_the_holders_place_and_turn_slot` |
| 殘影：最後一輪的環境回合消失 | `test_the_double_disappears_at_the_environment_turn_of_its_last_round` |
| 殘影：掉進深淵時 fizzled | `test_the_double_fizzles_when_the_holder_falls_into_a_chasm` |
| **同時最多 1 個生效中** | `test_at_most_one_rule_change_is_active_per_unit`（修正型傳說不受限） |
| **每人最多裝 1 個** | `tests/content/test_lasting_legendary_schema.py::test_each_unit_equips_at_most_one_rule_change_legendary` |
| `rule_changes.yaml` schema 與引用 | `test_rule_change_params_are_checked_per_kind`（6 個）、`test_rule_change_references_and_kind_points_are_checked` |

### 驗收 2：三擇一與 `activation` 的 schema；啟動前不生效、`timed` 到期、`battle` 整場、600‰；修正型傳說能寫出來並啟動

- schema（`tests/content/test_lasting_legendary_schema.py`）：三種核心各自合法 `test_each_of_the_three_cores_makes_a_valid_legendary`（參數化 3 個）；兩個核心被拒 `test_a_legendary_with_two_cores_is_rejected`；`rule_change` 結構 `test_a_rule_change_must_be_the_only_effect_on_a_self_shaped_active_legendary`；未知規則 `test_an_unknown_rule_change_is_a_reference_problem`；必填 `test_lasting_legendaries_must_declare_an_activation`；禁填 `test_other_skills_cannot_declare_an_activation`；修正型傳說的代價 `test_a_modifier_legendary_can_only_cost_source_and_cooldown`；**修正型傳說寫得出來** `test_a_modifier_legendary_is_written_and_activated_from_the_skill_bar`；**600‰** `test_battle_activation_scales_the_usable_budget_by_600_permille`（規則改變與修正型都驗）。既有 `tests/content/test_legendary_schema.py` 的「沒有核心被拒」改為新訊息。
- 引擎（`tests/engine/test_rule_changes.py`）：1 AP ＋ 源力與事件順序 `test_activation_costs_one_ap_and_source_and_emits_events_in_order`；**啟動前不生效** `test_a_modifier_legendary_does_nothing_until_activated`（倍率 1000 → 1180）；技能列提供、不能重複 `test_the_passive_slot_legendary_is_offered_as_an_action_and_not_twice`；源力不足 `test_activation_needs_source`；**timed 到期** `test_timed_activation_lasts_three_rounds_and_expires_at_the_holders_turn_start`、`test_the_timed_rounds_come_from_core_rules`；**battle 整場** `test_battle_activation_lasts_the_whole_battle`；序列化 `test_activations_survive_serialization`。
- API：`tests/api/test_activation_api.py`（從技能列啟動修正型傳說、視圖 `activations`、生效中再啟動回 400「已經啟動」、技能卡片的啟動與規則改變文字）。vitest：`client/src/battle/activations.test.ts`（剩餘輪數、HUD 文字、按鈕停用）。

### 驗收 3：每類至少一個手寫傳說並裝進 build；`check.py` 全過；重播一致

- 2.3 的 5 個技能：`test_the_demo_lasting_legendaries_cover_both_activations_and_every_rule_kind`（驗證、預算、裝備、4 類都有、兩種啟動都有）；`tests/content/test_coverage.py` 允許清單維持為空。
- AI 會用：`test_the_ai_activates_a_modifier_legendary_on_its_first_turn`（charger swamp 0）、`test_the_ai_activates_kindred_flame_and_its_fire_heals_allies`（summoner oil_depot 2）。
- 重播：`test_an_afterimage_battle_spawns_the_double_and_replays_exactly`（trapper swamp 1：狀態 JSON 與事件逐字相同）；CLI：`trpg battle --map swamp --seed 1 --ally-build build_trapper --log-json …` → `battle replay`「重播驗證通過：97 個動作、273 個事件，最終狀態一致（swamp，種子 1）。」
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2457 passed**）、client install／typecheck／test（**vitest 126**）—「全部檢查通過」。（最後跑了兩次：第二次只為取得測試數。）

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_legendary_schema.py` | 「沒有核心」的訊息改為三擇一；「只有主動技能可以花源力」改為「主動技能與修正型傳說」；傳說清單加 5 個；「最多 1 個改寫規則型」改用史詩（傳說的兩個改寫規則型原語現在先被「恰好 1 個核心」擋在引用檢查） |
| `tests/skillgen/test_validate.py::test_at_most_one_rule_rewrite_primitive` | 同上，改用史詩 |
| `tests/content/test_skill_rules_content.py` | `aura` 核心原語多 `rule_change`；`rule_change` 的最低稀有度是 legendary |
| `tests/content/test_summon_content.py` | 召喚物範本多 `summon_afterimage` |
| `tests/engine/test_summon_ai.py` | trapper 加了殘影之誓後，swamp 種子 1 的 AI 不再召喚骷髏（第 1 輪改用 AP 啟動傳說），換成 dark_forest 種子 0；`UnitSummoned` 只看非 orphan |
| `tests/narrative/test_skills_text.py`、`tests/api/test_reactions_telegraph.py` | 修正型傳說的卡片代價有啟動 AP（「AP 1」），不再屬於「沒有 AP」的一群 |
| `tests/cli/test_budget_cli.py` | 技能數 108 → 113 |
| `tests/cli/test_striker_trapper_battle.py` | striker 技能 3 → 4、trapper 6 → 7 |
| `tests/cli/test_battle_cli.py`、`test_skills_cli.py` | `LOG_FORMAT` `/25` → `/26` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 5 筆：`skills_list`、`skills_show_all`（新技能）、`battle_bridge_guardian_11`、`battle_open_plain_trapper_7`、`battle_swamp_striker_5`（這三個 build 裝了新傳說，戰鬥內容改變）；其他戰鬥快照沒變 |
| `client/src/battle/testFixtures.ts` | `UnitView` 多 `activations` |

## 5. 新增的複雜度 noqa

**無**（沒有新增 C901／PLR0911／PLR0912／PLR0915）。開發中三處超標都以拆函式解決：`handlers._damage`（虛弱倍率抽成 `_dealt_permille`）、`targeting.skill_problem`（「姿態已在／傳說已啟動」抽成 `_already_problem`）、`cli.skills.cmd_skills_show`（效果列表抽成 `_print_body`）。其他非複雜度 noqa：`interpreter.use_rule_change_effects` 的 `PLR0917`、`lifecycle.down_unit` 與 `rule_changes.pass_through` 的延後匯入 `PLC0415`（避免循環匯入，同陷阱與區域）。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/26`**（本段只升一次）：狀態多 `UnitState.activations`；`SkillDef.activation`、`EffectSpec.rule`、規則包多 `rule_changes`、核心規則 `legendary_*`、預算 `legendary_battle_budget_permille`；三個新事件與 `unit_summoned.orphan`；`/25` 的規則包沒有這些欄位。

## 7. 待 PM 決定（最多 10 點）

1. **修正型傳說的預算係數用「啟動 AP 的 AP 係數」（500‰）而不是修正係數（300‰）**：使用次數仍用整場的估計（不因只持續 3 輪而縮小），所以限時的修正型傳說約為同階史詩修正技能的 2 倍強（戰神降臨 +18% vs 灼傷之痕 +10% 有條件）。若希望改成「依持續輪數縮小使用次數」需另訂。
2. **`timed` 的「3 輪」＝ 持有者連同啟動那一回合共 3 個回合**，在第 4 個回合開始時結束（中間別人的回合都有效）。啟動當回合只剩部分 AP，所以實際上約 2.x 個完整回合。
3. **規則改變點數不看參數**（規格：每類一個點數）：例如「慈焰」100% 與 30% 同價、「血痕」換成暈眩也同價。參數有範圍限制（permille 100–1000、duration 1–3）。
4. **慈焰不含自己**：持有者被自己的火打到仍受傷（避免對腳下放火球回血）；燃燒狀態、火焰表面、火牆區域只要傷害來源是持有者都算，所以火牆燒到的隊友也會被治療。火焰的其他後果（點燃、燃燒狀態）照常發生。
5. **移山只讓 `blocks_move` 的物件可推**；可推倒的石柱、枯樹仍是「推倒」而不是滑動；木橋、薄冰（`over_chasm`）視為地面不能推。規格寫「包括石柱與牆」，若希望石柱滑動要改成先判斷移山再判斷推倒。
6. **血痕只算步行（`Move`）**，衝鋒、跳躍、傳送、被推都不算；起點不算；同一次移動每個敵人一次。
7. **殘影的分身**：排在持有者原本的先攻位置（持有者在自己回合倒下時分身立刻接著行動）；在第「倒下輪 ＋ 2 − 1」輪的環境回合消失（持續 2 輪含倒下那輪）；不算勝負（召喚物規則），所以持有者是我方最後一人時照樣戰敗；分身的 HUD「剩 N 輪」沿用召喚物公式，對 orphan 會多算 1 輪（CLI 與紀錄文字正確）。
8. **生效中不能再啟動**（不刷新時間）；啟動後也不可取消。改寫規則型傳說不受「每人最多 1 個規則改變」限制，修正型傳說也不受。
9. **AI 評分是最簡單近似**：只要場上有敵人就把啟動列為候選，限時 4 點 × 輪數、整場 4 點 × 4 輪，所以五個 build 幾乎都在第 1 輪啟動；不會為了「移山」去推牆、不會為了「血痕」繞過敵人、不會等 HP 低才開「殘影」。trapper 加了殘影之誓後少召喚骷髏（swamp 種子 0–4 皆無），3C-6 整理 build 時請一起看。
10. **慈焰誓約改為源力 1**（原設計 2）：源力 2 時召喚師開場只有 1 點，AI 幾乎啟動不了；把 `element_heals_allies` 點數從 6 降為 5，整場、源力 1 的預算 95.2%。數值都是初值。

## 8. 代表性輸出

`uv run trpg battle --map swamp --seed 1 --ally-build build_trapper`（輸出第 63–72 行，陷阱流英雄第 1 輪啟動殘影之誓）：

```
— 陷阱流英雄 的回合（AP 3，移動 5，法力 40/40）
  陷阱流英雄 施放「殘影之誓」（AP 1，源力 1）→ 影響 1 格
    ✦ 陷阱流英雄 花費源力：源力 1 → 0
  ✦ 陷阱流英雄 啟動了傳說「殘影之誓」（本場剩餘時間有效）
  陷阱流英雄 施放「寒鎖」（AP 1，法力 5，冷卻 2 回合）→ 影響 1 格
  陷阱流英雄 以「寒鎖」攻擊 盜賊弓手：d20=5 修正 +0 熟練 +2 半掩護 -2 = 5（目標 11）→ 失手［命中 −2：倒木掩護］
  陷阱流英雄 攻擊 盜賊：d20=5 修正 -1 熟練 +2 = 6（目標 11）→ 失手
  陷阱流英雄 從 (0, 6) 移動到 (1, 6)（消耗 1 移動）
  ★ 陷阱流英雄 的被動「疾行」觸發（移動後，深度 1）（法力 2）
  陷阱流英雄 獲得狀態「加速」（2 回合）
```

同一場第 117–125 行（第 2 輪，倒下時留下分身；連續未刪節）：

```
— 盜賊弓手 的回合（AP 3，移動 5，法力 9/9）
  盜賊弓手 攻擊 陷阱流英雄：d20=9 修正 +0 熟練 +2 = 11（目標 11）→ 命中
    陷阱流英雄 受到 10 點物理傷害［骰 6］，HP 10 → 0
  ＊ 陷阱流英雄 倒下了！
  ✦ 陷阱流英雄 的「殘影之誓」：倒下的地方留下了分身
  陷阱流英雄 的原地留下了 殘影分身1（(1, 6)，接替 陷阱流英雄 的行動順序，第 3 輪的環境回合消失）
  盜賊弓手 攻擊 殘影分身1：d20=5 修正 +0 熟練 +2 = 7（目標 11）→ 失手
  盜賊弓手 攻擊 殘影分身1：d20=5 修正 +0 熟練 +2 = 7（目標 11）→ 失手
  盜賊弓手 從 (2, 4) 移動到 (3, 1)（消耗 4 移動）
```

以 `--log-json` 存檔後 `trpg battle replay`：「重播驗證通過：97 個動作、273 個事件，最終狀態一致（swamp，種子 1）。」

## 9. 網頁重現步驟（PM 驗收）

1. `corepack pnpm -C client build` 後 `uv run trpg serve`（或 `scripts/play.py`），開始畫面選地圖 `swamp`（沼澤）、build「衝鋒流」、種子 `0`，開始戰鬥。
2. 輪到主角時，技能列最後一個是「戰神降臨」（代價「AP 1・源力 1・傳說啟動」）；滑過顯示卡片「啟動：限時：花 AP 1 ＋ 源力 1 啟動，持續 3 輪（啟動前不生效）」與「修正：你的所有攻擊（普攻與攻擊技能）：傷害 +18%」。
3. 點「戰神降臨」→ 施放（只有「自身」，不需選目標）：紀錄「✦ 衝鋒流英雄 啟動了傳說「戰神降臨」（持續到第 4 輪 衝鋒流英雄 的回合開始）」；HUD 源力 1 → 0，多一行「傳說：戰神降臨：剩 3 輪（第 4 輪你的回合開始時結束）」；按鈕變灰，滑過顯示「已啟動（到第 4 輪你的回合開始）」。之後普攻的預覽傷害比啟動前高約 18%。
4. 結束回合到第 4 輪主角回合開始：紀錄「衝鋒流英雄 的傳說「戰神降臨」時間到了，不再生效」，HUD 的「傳說：」一行消失（源力已用完，按鈕仍停用並顯示源力不足）。
5. 規則改變型：改選 build「召喚師」、地圖 `oil_depot`、種子 2，技能列「慈焰誓約」啟動後 HUD「慈焰誓約（規則改變「慈焰」）：整場」；火牆或燃燒波及隊友時紀錄出現「✦ … 的「慈焰誓約」：n 點傷害改為治療 …」。
