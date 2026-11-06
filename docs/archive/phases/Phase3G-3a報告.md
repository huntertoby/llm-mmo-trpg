# Phase 3G-3a 報告：裝備詞條——觸發（第 6 類）與充能（第 7 類）（G3a）

規格：`docs/phases/Phase3G計畫.md` 第 0、3 節（第 1、2 項）、第 6、8 節；設計：`docs/design/08-裝備.md` 8.21.2.6、8.21.2.7、8.21.5.2～8.21.5.3、8.24（第 6、7 類共 5 條）。
分支 `worktree-agent-adb3fb4fa0762e211`（從 main 的 331de3a 分出），未 push、未合併。第 9、10、11 類（授予動作、授予反應、改變規則）留給 G3b，**沒有做**。

## 新增與修改的檔案

| 檔案 | 內容 |
|---|---|
| `src/trpg/engine/gear_triggers.py`（新） | 裝備觸發與充能累積的結算（`resolve_gear_fired`）；詞條效果包成被動技能（`gear_carrier`，不經 schema 驗證） |
| `src/trpg/engine/gear_charge.py`（新） | 充能啟動：`ActivateCharge` 動作的合法性（`charge_problem`）、合法動作列舉（`charge_actions`）、結算（`do_activate_charge`） |
| `src/trpg/engine/ai/charge.py`（新） | 充能啟動的 AI 評分（`charge_score`）：預覽分數 ＋ 自我增益估值，再乘低權重 |
| `src/trpg/engine/skill_triggers.py` | `PassiveIndex` 多一份「裝備詞條」索引（`by_gear_event`）；所有收集點（命中、暴擊、自然 20、每第 N 次命中、受傷、擊殺、施加狀態、撞擊、進入表面、施放標籤、回合開始／結束、移動）各加一行 `_fire_gear`；`settle` 多一個分派；`reset_round_counts` 一併清每輪次數 |
| `src/trpg/engine/skills/interpreter.py` | `use_gear_effects` 與 `_GearCast`（被動式施放；`grant_ap` 改走受上限約束的 `gear_grant_ap`） |
| `src/trpg/engine/rewrites.py`、`refunds.py` | `gear_grant_ap`（每回合 AP 回復 +1 上限）；`grant_ap`／`refund_ap` 把回復的 AP 記進 `ap_gain_turn` |
| `src/trpg/engine/stacks.py` | `add_stacks(limit=)`（裝備版層數上限）、`spend_stacks`（只花 N 層，與「消耗全部」的 `consume_stacks` 並存） |
| `src/trpg/engine/actions.py`、`battle.py`、`__init__.py` | 新動作 `ActivateCharge`（`activate_charge`）、`CHARGE_ACTION_TYPES`；`legal_actions` 列出可啟動的充能 |
| `src/trpg/engine/state.py`、`turns.py` | `UnitState.gear_turn_counts`／`gear_round_counts`／`ap_gain_turn`；自己回合開始時清除每回合次數並重設 AP 回復計數 |
| `src/trpg/engine/events.py`、`narrative/events.py` | 新事件 `gear_triggered`、`charge_activated` 與敘事文字 |
| `src/trpg/engine/preview.py` | `ActivateCharge` 的 AP 花費與對目標的傷害範圍（自動命中） |
| `src/trpg/engine/view.py` | `UnitView.charges`（`ChargeView`：層數、上限、花費、是否需要目標、是否層數足夠） |
| `src/trpg/engine/ai/utility.py` | AI 評分流程接上充能（`_score_other`） |
| `src/trpg/content/equipment.py`、`library.py` | `TriggerAffix` 新增 `tag`／`status`／`surface`（帶參數的時機）與參數規則；`ChargeAffix` 新增 `effect_target`、充能不能用需要參數的時機累積；載入時檢查：觸發時機、對象需要時機有「另一方」、效果原語、充能的層數（存在、`owner: self`、`max_stacks` 不超過層數上限） |
| `content/stacks.yaml` | 新充能 `fury`（怒氣，上限 4） |
| `content/affixes.yaml` | `affix_charge_fury` 加 `effect_target: self` |
| `content/ai_profiles.yaml`、`content/environment.py` | `basic.charge_permille`（預設 400）：充能啟動的 AI 權重 |
| `content/items.yaml`、`content/units/gear_tester_g3a.yaml` | 測試物品 `item_g3a_blade`／`item_g3a_armor`／`item_g3a_ring` 與測試單位 `gear_tester_g3a`（`--log-json` 驗收用） |
| `src/trpg/content/library.py` | 另外修一個 G2 留下的不穩定測試：`Ruleset` 的關鍵字快取（私有屬性）改用「永遠相等」的字典，規則包的相等比較不再因快取填過與否而不同（見「不穩定測試」） |
| `src/trpg/engine/runner.py` | `LOG_FORMAT` → `trpg-battle-log/42` |
| `client/openapi.json`、`client/src/api/schema.d.ts` | 重產（只新增欄位、動作與型別） |
| `client/src/battle/charges.ts`、`ui/ChargeChips.tsx`、`battle/targeting.ts`、`battle/actions.ts`、`ui/Hud.tsx`、`ui/UnitInfo.tsx`、`screens/BattleScreen.tsx`、`styles.css`（檔尾新增） | 層數顯示（HUD 與單位資訊）、「更多動作」選單的啟動按鈕、動作標籤 |
| `tests/engine/test_gear_g3a.py`（36）、`client/src/battle/charges.test.ts`（7）、既有測試的對應更新 | 見下方逐條驗收 |

## 設計重點

- **沿用被動技能的觸發機制，不另開一套**：收集 → 等效果佇列清空 → 依「事件順序 → 持有者 ID → 詞條 ID」排序結算；深度 ＋1、`max_trigger_depth`（超過發出 `trigger_limit_reached`，不計次數）、持有者被暈眩（`skip_turn`）不觸發、倒下的另一方只對 `on_kill` 保留（對倒下的單位效果無效，同被動技能）。
- **每條每回合最多 1 次**：`limit: per_turn`（預設）以詞條 id 為鍵存在 `UnitState.gear_turn_counts`，**持有者自己回合開始時清除**；`limit: per_round`（`affix_trig_thorns_burn`）存在 `gear_round_counts`，每輪開始清除。兩件同 id 只算 1 條由 G1 的遞減規則保證（非數值類同 id 只生效第一條，`GearState.active_affixes` 只回傳生效的）。
- **`every_n_hits`**：與被動技能共用 `hits_landed`（只有裝備了每第 N 次命中的被動或詞條才累計）；第 N、2N 次命中是觸發時機，但同一回合只結算 1 次。
- **近戰（`melee_only`）**：傷害原因是 `attack`，且來源與目標的距離不超過 `core.melee_height_limit_max_range`（收集時的位置）。
- **效果包成被動技能**：`gear_carrier` 把詞條的 `effects` 包成一個 `skill_gear_*` 被動（形狀 `self`，縮放屬性取持有者最高的有效屬性）；沒寫 `affects` 的效果依 `effect_target` 補（`self` → 自己，其餘 → 敵方）。效果自動命中、狀態照常擲抵抗、不受修正規則影響（同被動技能）。
- **AP 回復上限（+1，所有來源合計）**：`UnitState.ap_gain_turn` 記本回合已由 `grant_ap`、`refund_ap` 與裝備回復的 AP（回合外存進 `ap_pending` 的也算在下個回合）；`affix_trig_kill_ap` 走 `gear_grant_ap`，剩餘額度 ＝ 上限 − 已回復，額度不足時發出 `effect_fizzled`（`ap_gain_cap`）。裝備回復不吃「每輪最多被給一次 AP」的限制，只受這個上限約束。
- **充能累積**：`gain_trigger` 時 ＋1 層（`add_stacks(limit=max_stacks)`，沒有每回合限制）；裝備版上限 3（靜電）小於層數本身上限 5；已超過上限的層數不會被減少。與同 id 的技能層數共用（`static_charge`）。
- **充能啟動**：`ActivateCharge(affix_id, target_id?)`，只在自己的回合、層數 ≥ `cost_stacks` 且 AP ≥ `cost_ap` 時列入 `legal_actions`；`effect_target: target` 要選一個「普攻合法」的敵人（武器射程與視線），`self` 不能指定目標。結算：付 AP、發出 `charge_activated`、花掉 `cost_stacks` 層（只花那麼多，不是全部）、結算效果；期間引起的觸發在整個動作結束後結算（`holding`）。
- **AI**：`ActivateCharge` 走一般的預覽評分（傷害、擊倒都在預覽事件裡），作用在自己的增益依 `ally_status_values × support 權重` 估值，最後乘 `basic.charge_permille`（400‰，只調整正分）。實測：敵人很健康時分數低於一般技能與普攻；能直接擊倒殘血敵人時 AI 會啟動。
- **預覽**：`preview(ActivateCharge)` 給 AP 花費與對目標的傷害範圍（自動命中，沒有命中率）。
- **前端**：HUD 與單位資訊顯示每條充能的層數格（格數＝裝備版上限）與「可啟動」；「更多動作」選單最後列出每條可啟動的充能（`啟動靜電（3 層＋1 AP）`），需要目標的選模式後點敵人，作用在自己的直接啟動。沒有碰 roguelite、裝備分頁，`styles.css` 只在檔尾新增。

## LOG_FORMAT

`trpg-battle-log/41` → **`trpg-battle-log/42`**：新動作 `activate_charge`、新事件 `gear_triggered`／`charge_activated`、`UnitState.gear_turn_counts`／`gear_round_counts`／`ap_gain_turn`、詞條欄位（`TriggerAffix.tag`／`status`／`surface`、`ChargeAffix.effect_target`）、規則包的層數 `fury`。`/41` 的紀錄無法重播（規格已接受）。合併時若 3-24b2 或 G4 也遞增，由 PM 處理版號。

## 逐條驗收

證據都在 `tests/engine/test_gear_g3a.py`（36 個），除非另註。

| 規格 | 證據 |
|---|---|
| 5 條詞條載入、新充能 `fury` | `test_whitelist_trigger_and_charge_affixes_load`；`tests/content`（含 `test_equipment_content.py`、`test_coverage.py` 的 `fury` 允許清單） |
| schema 與載入時檢查 | `test_trigger_affix_parameter_rules`、`test_charge_affix_rejects_parameterised_gain_triggers`、`test_library_checks_trigger_charge_references`（對象沒有另一方、未知層數、`max_stacks` 超過層數上限、未知原語） |
| `affix_trig_every3_prone` | `test_every3_prone_fires_on_every_third_hit`（第 3、6 次命中是時機）、`test_every3_prone_applies_knock_prone_to_the_target`（`gear_triggered` ＋ 擊倒對抗判定） |
| `affix_trig_kill_ap` | `test_kill_ap_grants_one_ap_after_the_attack_cost`（回 1 AP） |
| `affix_trig_thorns_burn` | `test_thorns_burns_a_melee_attacker_once_per_round`（燃燒給攻擊者、每輪 1 次）、`test_thorns_ignores_ranged_attackers`（遠程不觸發） |
| `affix_charge_static` | `test_static_charge_gains_one_stack_per_hit_up_to_the_gear_cap`（1、2、3、3、3）、`test_static_charge_activation_spends_stacks_and_ap_and_deals_lightning`（花 3 層與 1 AP、3d6 雷電） |
| `affix_charge_fury` | `test_fury_gains_a_stack_when_damaged`（上限 4）、`test_fury_activation_buffs_the_owner_for_free`（0 AP、`empowered`、不能指定目標） |
| **每回合最多 1 次** | `test_trigger_is_limited_to_once_per_turn`（兩次擊殺只回一次 AP）、`test_every3_prone_second_trigger_in_the_same_turn_is_suppressed`、`test_trigger_count_resets_on_the_next_turn`、`test_round_counts_reset_at_round_start` |
| **同 id 兩件只算 1 條** | `test_same_affix_on_two_items_counts_once`（主手與戒指都有 `affix_trig_kill_ap`，只生效主手那條、只觸發一次） |
| **連鎖深度** | `test_trigger_chain_respects_max_trigger_depth`（深度 0：不觸發、`trigger_limit_reached`、不計次數）、`test_trigger_depth_increases_with_each_link`（深度從 1 起算） |
| **`kill_ap` 計入每回合 AP 回復 +1 上限（所有來源）** | `test_kill_ap_is_capped_by_the_per_turn_ap_gain_limit`（已回復 1 → 不回、`ap_gain_cap`）、`test_other_ap_sources_count_toward_the_gear_cap`（`grant_ap`／`refund_ap` 也計入）；上限函式本身是 G1 的 `test_cap_helpers_for_later_segments` |
| 持有者被暈眩不觸發 | `test_stunned_owner_does_not_trigger` |
| 充能合法性（層數、AP、目標） | `test_charge_cannot_activate_without_enough_stacks`、`test_charge_needs_ap_and_a_valid_target` |
| 啟動後的連鎖在動作結束後結算 | `test_activation_triggers_follow_up_after_the_action`（啟動擊倒敵人 → 戒指的擊殺觸發） |
| 確定性、序列化 | `test_charge_activation_is_deterministic_and_round_trips`（同狀態同動作事件相同、狀態與動作 JSON 來回） |
| 預覽反映 | `test_preview_shows_ap_cost_and_damage_of_a_charge`（AP 花費、傷害範圍、波及單位；怒氣 0 AP） |
| 檢視（層數顯示的資料） | `test_unit_view_lists_charges`（層數、上限、花費、`needs_target`、`ready`；敵人無裝備為空） |
| **AI 會啟動充能（低權重）** | `test_ai_scores_a_ready_charge_but_below_the_best_normal_action`、`test_ai_activates_a_charge_that_kills`（殘血敵人 → 選擇啟動靜電）、`test_ai_does_not_activate_without_stacks`、`test_ai_charge_score_is_discounted` |
| `legal_actions` 仍含結束回合 | `test_end_turn_remains_legal_with_charges` |
| 舊資料與其他測試不受影響 | 既有 engine／content／api／narrative／cli 測試全部通過；**沒有換任何種子**；只更新分類與格式字串（`test_vault`、`test_weapons_24a2` 的動作分類、`test_state_clone` 的新欄位、`test_coverage` 的 `fury`、`/42`） |
| 前端 | `client/src/battle/charges.test.ts`：層數格、文字、啟動按鈕只在伺服器列出時出現、排在「更多動作」最後、標籤含花費、不佔常駐／選單／技能列的按鈕分配 |
| 一場 `--log-json` ＋ `replay` | `test_g3a_gear_battle_log_json_and_replay`；手動見下 |

手動 `--log-json` ＋ `replay`（種子 3：觸發、啟動、擊殺回 AP 都出現）：

```
uv run trpg battle --map test_flat_6x6 --allies gear_tester_g3a --enemies bandit,bandit --seed 3 --log-json g3a.json
uv run trpg battle replay g3a.json
重播驗證通過：48 個動作、185 個事件，最終狀態一致（test_flat_6x6，種子 3）。
（種子 1～15 的紀錄內 gear_triggered 4～8 次、charge_activated 1～3 次：AI 會啟動充能）
```

截圖（`docs/phases/img/`；用本機 8123 埠的伺服器，主角為 `build_tank` 穿上 `gear_tester_g3a` 的物品、開場給 3 層靜電與 4 層怒氣；沒有碰使用者佔用的 8000 埠）：

- `3G-3a-hud-overview.png`：HUD 的層數格與「可啟動」標示（靜電 ●●●、怒氣 ●●●●）。
- `3G-3a-more-menu.png`：「更多動作」選單最後列出「啟動怒氣（4 層）」與「啟動靜電（3 層＋1 AP）」。
- `3G-3a-pick-target.png`：選了「啟動靜電」後的提示與可點的目標（紅框）。
- `3G-3a-after-activate.png`：啟動後戰鬥紀錄（花 3 層靜電、1 AP，對盜賊造成雷電傷害），HUD 靜電變成 ○○○、AP 3 → 2、怒氣仍可啟動。

## 新增的複雜度 noqa

- `skill_triggers._fire_gear`：`# noqa: PLR0917`（位置參數 6 個：上下文、索引、時機、事件序號、持有者、另一方；另有近戰、狀態、標籤、表面、命中次數 5 個關鍵字參數，是收集時各種時機需要的篩選條件，無法再合併而不降低可讀性）。
- `ai/utility.UtilityAI._score_other`：`# noqa: PLR0917`（位置參數 6 個，與既有的 `_skill_candidates` 同型；為了不讓 `rank` 的分支數超過 `PLR0912` 而拆出）。
- `# noqa: PLC0415`（函式內匯入）：`rewrites.gear_grant_ap`（`trpg.engine.gear` 匯入 `skills.conditions`，頂層匯入會循環）、`skill_triggers._resolve_gear`（同既有的 `_resolve_one`、`_resolve_delayed` 的延後匯入慣例）。
- 沒有 C901 或 PLR0911／0912／0915 的 noqa（`_on_attack` 超標時把每第 N 次命中拆成 `_count_hits`）。

## 待 PM 決定

1. **每回合 AP 回復 +1 上限只約束「裝備來源」**：`grant_ap`、`refund_ap`（技能）的 AP 會計入 `ap_gain_turn`（所以技能先回復過，裝備就不再回），但技能本身的回復不受這個上限約束（否則會改變既有技能的行為與平衡）。設計文字是「所有來源合計」，若要連技能一起限制請決定。
2. **「每回合」＝持有者自己回合開始時清除**：回合外觸發（例如敵方回合被擊殺或被打）計入「下一次自己回合開始前」的次數，所以 `per_turn` 的詞條在「持有者回合外」與「回合內」之間不會各算一次；`per_round`（荊棘）每輪開始清除。回合外 `affix_trig_kill_ap` 回的 AP 存進 `ap_pending`（同 `grant_ap`），並計入下個回合的 AP 回復上限。
3. **近戰的判定**：傷害原因 `attack` 且來源與目標距離 ≤ `core.melee_height_limit_max_range`（不看武器類別，所以技能的近戰傷害也算；貼臉的遠程攻擊也算）。
4. **充能啟動的目標條件**：以「普攻合法」（武器射程、視線、隱蔽）為準，不是技能形狀；效果歸給持有者、自動命中。傷害縮放屬性（詞條沒有技能可依據）取持有者最高的有效屬性（法術式：骰值 ＋ 屬性 × 0.5）。
5. **充能層數與技能層數共用同一個 id**：`static_charge` 同時被既有技能（雷霆終結，消耗全部）使用；裝備累積的上限是 3（裝備版），技能累積的上限仍是 5；裝備啟動只花 `cost_stacks` 層，不是全部。
6. **充能累積沒有每回合限制**（每次觸發時機 ＋1 層，直到裝備版上限）；觸發類才有每回合 1 次。
7. **schema 新增欄位**：`TriggerAffix.tag`／`status`／`surface`（支援帶參數的時機，與被動技能的 `trigger` 同規則）、`ChargeAffix.effect_target`（`target`／`self`，`fury` 填 `self`）；充能的累積時機不能用需要參數的 4 種（`every_n_hits`、`on_cast_tag`、`on_status_applied`、`on_enter_surface`）。
8. **AI 權重 `basic.charge_permille: 400`** 為初值，未經模擬；自我增益的估值用 `ally_status_values`（沒列出用 3）。`simple.py` 的簡單 AI 不使用充能（與裝填之外的動作一致）。
9. **`ActivateCharge` 是新的動作類別**（`CHARGE_ACTION_TYPES`），不算進基本動作的 10 個上限，也不是管理操作；啟動的敘事文字用詞條的完整名稱（例如「命中時累積 1 層靜電（上限 3）；花 3 層＋1 AP：…」），之後若詞條加短名稱欄位可改善紀錄與按鈕文字（目前按鈕用層數名稱與花費組成）。
10. **`fury` 沒有手寫技能使用**：`tests/content/test_coverage.py` 的允許清單加了 `fury`（只由裝備詞條使用）。

## 不穩定測試（Phase 3G 計畫第 8 節：`test_traps_and_stacks_survive_a_json_round_trip`）

原因找到並修掉：`Ruleset._keyword_cache`（G2 加的關鍵字推導快取）是 pydantic 私有屬性，pydantic 的 `__eq__` 會比較私有屬性；測試用的 `library()` 是行程內共用的，**同一個行程裡先跑過會推導關鍵字的測試**（例如 G2／G3a 的裝備測試）之後，狀態的規則包快取有內容、JSON 來回後的新規則包快取是空的，兩者就不相等——所以只在特定測試順序（平行時每個 worker 的順序不同）才失敗。穩定重現：`pytest tests/engine/test_gear_g2.py tests/engine/test_gear_g3a.py tests/engine/test_traps.py`（修之前失敗）。修法：快取字典（`_CacheDict`）的 `__eq__` 一律回傳「相等」（快取只是推導結果，不是規則資料）；`test_ruleset_equality_ignores_the_keyword_cache` 防止再發生。第一次全量時就是這個測試失敗（3849 通過、1 失敗），修好後重跑。

## 最終檢查

`uv run python scripts/check.py`：

- **第一次全量**（所有 G3a 變更都在）：ruff check／format、mypy（474 個檔）、lint-imports 通過；pytest **3849 通過、1 失敗**（就是上面的不穩定測試，與 G3a 無關）；client typecheck 通過、client test 56 個檔 600 個測試通過。
- 修掉不穩定測試之後 **第二次全量因電腦同時跑三個 agent 太慢（約 3 小時才跑了 44%），在 44% 時中止**（中止前沒有任何失敗；ruff、format、mypy、lint-imports 在那次都已通過）。修正只動 `library.py` 的快取字典與新增 1 個測試，所以改以針對性重跑代替：`tests/engine/test_traps.py` ＋ `test_state_clone.py` ＋ `test_gear*.py` ＋ `tests/content/test_coverage.py` ＋ `tests/api`（331 個通過）、修正前會失敗的組合（`test_gear_g2` ＋ `test_gear_g3a` ＋ `test_traps` 同一行程）修正後通過；`tests/engine`、`tests/content`、`tests/api`、`tests/narrative`、`tests/cli`、`tests/skillgen`、`tests/roguelite` 在修正前各自完整通過。**建議 PM 合併後在負載較低時再跑一次完整 `check.py`。**

`corepack pnpm -C client build`：成功（只有既有的 chunk 大於 500 kB 警告）。

沒有跑大型模擬（規格沒有要求，數值都是初值）。
