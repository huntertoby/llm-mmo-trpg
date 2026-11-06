# Phase 3D-8c 報告：監視射擊、夾擊條件、暫時獲得技能 `grant_skill`

## 1. commit

| commit | 內容 |
|---|---|
| 1e516ca | 引擎與內容層：狀態 `overwatch`、內建反應 `overwatch_shot`（事件 `enemy_moves_in_range`、`requires_status`）；條件 `flanked`；原語 `grant_skill`（`UnitState.granted_skills`、事件 `skill_granted`／`skill_grant_expired`、跨技能 schema 檢查、預算算法）；AI 評分（進入監視、暫時技能、夾擊位置權重） |
| 1166d5f | 五個新技能（監視射擊、前後夾擊、飛行、展翼、賜予羽翼）、`build_ranged`／`build_assassin` 換入新技能、新 `build_winged`；新測試 `test_overwatch_flank.py`（25）、`test_grant_skill.py`（27）；內容測試更新 |
| 62b55ec | 視圖 `UnitView.granted_skills`、預覽 `grants`、CLI 暫時技能標註、反應詢問文字；`LOG_FORMAT` `/30` → `/31`；OpenAPI、`schema.d.ts`、CLI 快照 |
| e4db825 | 網頁：技能列的暫時技能（藍青邊框＋「暫時・剩 N 輪」）、HUD 一行、預覽說明；vitest 4 個 |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 D 監視射擊

- 狀態 `overwatch`（`statuses.yaml`；buff、`expires: own_turn_start`、`budget_points: 6`、最低稀有 rare）：持續到持有者下回合開始。
- 內建反應 `overwatch_shot`（`reactions.yaml`；`effect: basic_attack`、`events: [enemy_moves_in_range]`、新欄位 `requires_status: overwatch`）。持有者帶有該狀態時，敵人 **主動移動（步行、衝鋒 `dash`、直線衝撞 `charge_through`）的一步結束後**，若持有者能以武器普攻到敵人現在的位置（射程、視線、隱蔽、致盲全照一般普攻規則，用 `attack_problem`），就普攻一次、不花 AP；佔本輪反應次數（`reactions_per_round`），普攻結算後移除 `overwatch`（`status_removed`，新原因 `fired`）。強制位移、傳送、跳躍、互換不觸發（與 `enemy_enters_adjacent` 同一批呼叫點）。
- 規則：沒有放進 `default_rules`。單位裝備的技能（或它暫時給出的技能）會施加 `overwatch` 時，`make_unit` 自動加一條 `auto` 規則（同反應技的自動規則做法），所以沒有監視技能的單位反應列表不變；玩家可用 `SetReactionMode` 改成 `prompt`／`off`。
- 詢問模式：與其他反應共用 `_react`／`_decide`／`PauseForDecision`；拒絕時狀態保留（下一步在射程內會再問）。`Pending.trigger_event_seq` 指向引發的 `unit_moved`。
- 示範技能：`skill_overwatch`「監視射擊」（rare、aura、AP 1、冷卻 1、武器技 ranged；預算 81.6%），裝進 `build_ranged`。
- AI：`utility._overwatch_points`——敵人數（距離在「武器射程 ＜ d ≤ 武器射程 ＋ 其速度」，已在射程內的不算，最多 `overwatch_max_enemies`＝2）× `overwatch_points`（5）× `damage` 權重；已有監視時為 0。數值放 `content/ai_profiles.yaml` 的 `rewrite:`。

### 2.2 E 夾擊 `flanked`

- 條件 `flanked`（`skill_conditions.yaml`；common 嚴苛度、最低 rare）：以目標為中心，施放者所在那一側的 **對面格** 站著施放者的存活友方（不含施放者）。「所在那一側」取施放者相對目標位移較大的軸（左右與上下相等時取左右；同格無）：相鄰攻擊就是正對面的格子，遠程攻擊也看目標背對自己的那一格（`conditions.flank_xy`、`is_flanked`）。
- 可用於：技能條件、效果條件（`condition_met` 的單位類條件）與修正規則的 `hit_bonus`、`damage_permille` 等（選目標之前就決定的 `SELF_ONLY_CHANGES` 仍只允許 `self_hp_below`，schema 拒絕 `flanked`）。
- 示範技能：`skill_pincer_strike`「前後夾擊」（rare、strike、AP 2、冷卻 2；傷害 100% ＋ 夾擊時再 80%；預算 74.7%），裝進 `build_assassin`（換下魯莽突刺，魯莽突刺仍在 `build_gambler`）。
- AI：新權重 `flank`（位置價值：緊貼敵人且敵人對面站著友方的敵人數 × 3）；只給新增的 AI 模式 `flanker`（其餘權重同 `brute`），`build_assassin` 的英雄使用（見待決 #6）。

### 2.3 `grant_skill`（暫時獲得技能）

```yaml
- {type: grant_skill, skill: skill_flight, duration: 3, affects: self}     # 展翼
- {type: grant_skill, skill: skill_flight, duration: 3, affects: allies}   # 賜予羽翼（形狀 single）
```

- 狀態在 `UnitState.granted_skills: tuple[GrantedSkill(skill_id, remaining)]`（可序列化、可重播、`clone` 涵蓋）。`UnitState.all_skills`（裝備 ＋ 暫時，依獲得順序）是引擎列舉「可用技能」的依據：`legal_actions`、`use_skill`、AI。**不佔技能欄位**（`unit.skills` 不變）。
- 倒數在 **目標自己的回合結束時** −1（`grants.expire_granted_skills`，`end_turn` 內）；歸零時消失、事件 `skill_grant_expired`，**該技能的冷卻與使用次數紀錄一併移除**。施放當回合的結束也算一次（給 3 輪＝含施放回合共 3 個持有者回合可用）；給友方時從友方自己的回合結束開始算。
- 同一個被給的技能不疊加：重新施放把剩餘輪數刷新成這次的 `duration`（事件 `skill_granted.refreshed: true`）；目標原本就裝備了該技能時不結算（`effect_fizzled`：`already_equipped`）。
- 被給的技能照它自己的規則（AP、法力、冷卻、武器需求）。
- schema（`SkillDef._check_grant_skill` ＋ 跨技能 `granted_skill_problems`，載入內容時檢查）：只能用在主動技能、每技能最多一個、`skill` 與 `duration`（1–4）必填、不能給出自己；被給的技能必須存在、是主動技能（排除反應／被動／姿態／修正）、不是傳說、不含改寫規則型或規則改變型原語、不是 `grant_skill` 技能（不連鎖）。
- 預算：被給技能的總點數 × `grant_skill_expected_uses_per_round_permille`（800）÷ 1000 × 持續輪數（`skill_budget.yaml`；`skillgen/budget._grant_skill_points` 遞迴呼叫 `skill_budget`）。
- 視圖／API：`UnitView.granted_skills`（技能 ID、中文名、剩餘輪數；只給自己陣營）；預覽 `grants`（單位、技能、名稱、輪數、是否只是刷新）。CLI 單位列加「 ［暫時技能：飛行 剩 3 輪］」；戰鬥紀錄「暫時獲得技能「飛行」（3 輪，在 … 的回合結束時倒數）」「… 期滿消失了」。
- AI：被給的技能是一般技能，照一般評分（AI 實際會用，見 CLI 節錄之外的 `build_winged` 戰鬥）；施放 `grant_skill` 的收益 ＝ `grant_skill_points`（8）× 每輪預期使用次數（800‰）× 持續輪數 × `damage` 權重，只給自己陣營、只刷新輪數時不加分；候選估計（`_grant_supports`）要求對象沒裝備、武器相容、尚未暫時擁有（或只剩最後一輪）。
- 示範：`skill_flight`「飛行」（rare、displace、AP 1、傳送自己射程 4 ＋ 短暫隱蔽 2 回合，法力 3；預算 98.5%）、`skill_wing_spread`「展翼」（aura、self、AP 2、法力 4、冷卻 4）、`skill_wing_gift`「賜予羽翼」（aura、single 射程 4、同上）；裝進新的 `build_winged`。`skill_flight` 沒有被任何 build 直接裝備（`test_coverage` 的「被裝備」檢查改為也認得「被裝備的 grant_skill 給出的技能」）。

### 2.4 build 變動

| build | 變動 |
|---|---|
| `build_ranged` | 監視射擊換下升高平台（主動欄位已滿） |
| `build_assassin` | 前後夾擊換下魯莽突刺；`ai_profile: flanker` |
| `build_winged`（新，第 19 個） | 展翼、賜予羽翼、升高平台（接收被換下的）、穿透射擊、居高射擊、遠距狙擊；弓 |

### 2.5 網頁（PM 用瀏覽器驗收）

- 技能列：暫時技能按鈕接在裝備技能之後，藍青色邊框、按鈕上「暫時・剩 N 輪」；HUD「暫時技能：飛行 剩 3 輪」；預覽說明「X 暫時獲得技能「飛行」3 輪（在他的回合結束時倒數，不佔技能欄位）」。技能卡片的名稱也會取得。

**「展翼」重現步驟（PM）**

1. `uv run python scripts/play.py`（`client/dist` 已建置），開始畫面選 build「飛翼流」（`build_winged`）、地圖「開闊平原」（`open_plain`）、種子 **2**，開戰。
2. 第 1 輪就是主角先攻（先攻 22）。點技能列的「展翼」（AP 2、法力 4、冷卻 4）；自我技能，預覽寫「暫時獲得技能「飛行」3 輪」，確認施放。
3. 施放後技能列最後多出「飛行」按鈕（藍青邊框，「暫時・剩 3 輪」，法力 3、AP 1，主角還剩 1 AP 可立刻點它並選 4 格內的落點）；HUD 多一行「暫時技能：飛行 剩 3 輪」，紀錄有「暫時獲得技能「飛行」」。
4. 結束回合：下一個自己的回合「飛行」剩 2 輪，再下一次剩 1 輪，第 3 個回合結束時紀錄出現「暫時獲得的技能「飛行」期滿消失了」，按鈕消失。「賜予羽翼」可選射程 4 內的友方（隊友的暫時技能在隊友自己的回合結束時倒數；網頁只列主角自己的技能列）。
5. 我用 API 層驗證過同一個序列（`POST /api/battles` → 預覽 `grants` → 施放後 `granted_skills == [{skill_flight, 飛行, 3}]`、合法動作多出 `skill_flight`、主角剩 1 AP）；沒有用瀏覽器實機操作。

**監視射擊重現**：build 選「遠程」（`build_ranged`）、地圖 `narrow_halls`、種子 1，第 1 輪主角施放「監視射擊」（AP 1）後，敵方弓手在第 1 輪走進射程時紀錄出現「⟳ 遠程英雄 反應：監視射擊」與一次攻擊、「「監視」射擊後結束了」。

## 3. 驗收條件逐條（8.4，3D-8c）

### 驗收 1：監視與夾擊

| 項目 | 測試（`tests/engine/test_overwatch_flank.py`） |
|---|---|
| 射程與視線 | `test_an_enemy_moving_in_range_and_sight_is_shot_once_and_overwatch_ends`、`test_the_shot_comes_from_the_first_step_that_ends_in_range`、`test_a_move_that_stays_out_of_range_does_not_trigger`、`test_no_line_of_sight_means_no_shot` |
| 每輪 1 次、佔反應 | 同上第一個（只一次射擊、`reactions_used == 1`）、`test_a_used_up_reaction_blocks_the_shot` |
| 移除時機 | 射擊後移除（`StatusRemoved.reason == "fired"`）；`test_overwatch_expires_when_the_holders_next_turn_starts`；沒有狀態不射擊 `test_without_the_overwatch_status_there_is_no_shot`；`test_a_killed_mover_stops_walking_and_the_shot_still_ends_overwatch` |
| 詢問模式／關閉 | `test_prompt_mode_asks_and_declining_keeps_overwatch`、`test_prompt_mode_accepting_fires_the_shot`、`test_off_mode_never_shoots`；預覽 `test_the_preview_of_a_move_includes_the_overwatch_shot` |
| 資料與自動規則 | `test_the_overwatch_status_reaction_and_skill_are_defined`、`test_a_unit_gets_the_overwatch_rule_only_when_it_has_an_overwatch_skill` |
| 夾擊成立／不成立 | `test_flank_xy_is_the_tile_opposite_the_caster`、`test_flanked_needs_a_living_friend_on_the_opposite_side`（友方在旁邊、無人、對面是敵人、對面倒下皆不成立）、`test_the_flanked_condition_in_condition_met` |
| 技能條件、效果條件、修正規則 | `test_the_pincer_skill_adds_a_hit_only_when_flanked`、`test_flanked_works_as_a_modifier_condition`（命中與傷害）、`test_flanked_is_rejected_for_changes_decided_before_targeting` |

### 驗收 2：示範技能與 AI

- 裝備：`test_the_overwatch_status_reaction_and_skill_are_defined`（`build_ranged`）、`test_the_pincer_demo_is_in_build_assassin`；全部技能通過預算與結構驗證（`tests/content/test_sim_builds.py`）。
- AI 有進入監視的紀錄：`test_ai_battle_with_overwatch_replays`（`narrow_halls` 種子 1、`build_ranged`：紀錄有「施放「監視射擊」」「反應：監視射擊」，重播一致）；`trpg sim maps --maps narrow_halls,open_plain --seeds 5 --ally-build build_ranged` 的技能使用表 `skill_overwatch  我方  1.20 次／場`。（預設陣容的 `sim maps --seeds 5` 沒有英雄 build，不會有監視技能，必須帶 `--ally-build build_ranged`。）
- 夾擊 AI：`build_assassin` 的 `flanker` 模式；sim 30 場（swamp）用到前後夾擊 0.07 次／場——本來就少見（要隊友剛好在目標對面），不是缺陷。

### 驗收 3：`grant_skill`（`tests/engine/test_grant_skill.py`）

| 項目 | 測試 |
|---|---|
| 獲得、不佔欄位 | `test_casting_grants_the_skill_without_using_a_slot`、`test_the_granted_skill_shows_up_in_legal_actions_and_works`、`test_without_the_grant_the_unit_cannot_use_the_skill` |
| 期滿消失（含冷卻紀錄） | `test_the_duration_counts_down_at_the_holders_turn_end_and_expires`、`test_expiry_clears_the_cooldown_and_use_records` |
| 重新施放只刷新 | `test_recasting_only_refreshes_the_remaining_rounds` |
| 給友方、倒數在友方回合 | `test_granting_a_friend_counts_down_on_the_friends_turn_not_the_casters` |
| 被給技能照自己的冷卻 | `test_a_granted_skill_follows_its_own_cooldown_rules` |
| 原本就裝備 | `test_granting_a_skill_the_target_already_equips_fizzles` |
| schema 拒絕傳說／改寫規則型／自己／連鎖／非主動 | `test_the_schema_rejects_bad_granted_skills`（傳說、`cheat_death`、反應、被動、姿態、另一個 grant_skill、未知技能）、`test_a_skill_cannot_grant_itself`、`test_grant_skill_needs_skill_and_duration_and_an_active_skill`、`test_loading_content_rejects_a_grant_of_a_legendary_skill`（載入內容） |
| 預算 | `test_the_budget_of_a_grant_is_the_granted_points_times_the_expected_uses` |
| 存讀與重播 | `test_the_state_round_trips_through_json_with_granted_skills`、`test_clone_copies_granted_skills`、`test_ai_battle_with_wings_replays`（`open_plain` 種子 2、`build_winged`，重播一致） |
| 視圖與預覽 | `test_the_view_lists_granted_skills_for_the_own_team_only`、`test_the_preview_lists_the_grant`；前端 `client/src/battle/granted.test.ts`（4 個） |
| 網頁 | PM 用瀏覽器驗收（步驟見 2.5） |

### 驗收 4：`check.py`、重播

- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2800** 個）、client typecheck、vitest（**147** 個）全部通過。
- 重播一致：`trpg battle --map narrow_halls --seed 1 --ally-build build_ranged` 與 `--map open_plain --seed 2 --ally-build build_winged` 皆 `重播驗證通過`（85 個動作／255 個事件；137 個動作／381 個事件）。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_coverage.py` | `_equipped()` 也算「被裝備的 grant_skill 技能給出的技能」（`skill_flight` 不佔欄位、沒有 build 直接裝備） |
| `tests/content/test_sim_builds.py` | build 數 18 → 19（新增 `build_winged`），測試改名 |
| `tests/content/test_skill_rules_content.py` | 光環骨架核心加 `grant_skill` |
| `tests/skillgen/test_budget.py`、`tests/skillgen/test_validate.py` | 新狀態 `overwatch`（點數 6、有益） |
| `tests/engine/test_combo_resources.py` | buff 狀態集合加入 `overwatch`（監視可被驅散或奪取） |
| `tests/cli/test_budget_cli.py` | 技能數 127 → 132 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/30` → `/31` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 2 筆：`skills_list`、`skills_show_all`（新增 5 個技能）；七場戰鬥快照全部不變 |
| `tests/api/test_routes.py` | 預覽多 `grants` 欄位 |
| `tests/engine/test_reaction_events_3d3.py` | `build_ranged` 的「掩護射擊」整場戰鬥測試由 `narrow_halls` 種子 0 改為 `open_plain` 種子 6：`build_ranged` 換下升高平台、加了監視射擊後，種子 0 的戰鬥走向改變，掩護射擊不再觸發（`open_plain` 種子 6 觸發 2 次，重播一致） |
| `client/src/battle/testFixtures.ts` | `UnitView` 多 `granted_skills` |

## 5. 新增的複雜度 noqa

**沒有新增任何 noqa。** 開發中超標的函式以拆函式處理（`_enemy_terms` 從 `_unit_position_value` 拆出、`_skill_event_points` 從 `_rewrite_event_points` 拆出、`_usable` 的狀態檢查併入既有條件）。

## 6. `LOG_FORMAT`

`/30` → **`/31`**（本段升一次）：狀態 `overwatch`、內建反應 `overwatch_shot`（`requires_status`、事件 `enemy_moves_in_range`）、`status_removed` 的新原因 `fired`、有監視技能的單位多一條自動反應規則、條件 `flanked`、原語 `grant_skill`（`EffectSpec.skill`）、`UnitState.granted_skills`、新事件 `skill_granted`／`skill_grant_expired`、預算與 AI 規則欄位；`/30` 的規則包沒有這些，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **展翼與賜予羽翼用 AP 2、不是 1**：「飛行」（傳送 4 點 ＋ 隱蔽 3 點）是 7 點，依規格公式 7 × 800‰ × 3 輪 ＝ 16.8 點；AP 1 的技能可用預算只有約 8.5（197%，驗證器拒絕），AP 2 剛好 98.4%。若要 AP 1，要降低給出的技能價值、縮短持續輪數、或提高預期使用係數；初值皆未經模擬。
2. **`overwatch` 狀態 `budget_points: 6`**：AP 1 的光環技能下限約 5.1 點（70% × 7.35），3 點會被判過弱；6 點約等於「一次普攻 × 命中機會」。平衡階段檢查。
3. **監視觸發條件**：敵人主動移動的一步結束後在射程與視線內就射擊（不要求「剛進入」射程，已經在射程內的移動也算）；近戰持有者（射程 1）等同守備。沒有做 `kind: reaction` 的反應技版 `enemy_moves_in_range`（反應技事件表不含它；只有內建反應 `overwatch_shot`）。`prompt` 模式拒絕時狀態保留，下一步再問。
4. **夾擊的「對面格」推廣到遠程**（規格只寫相鄰）：依施放者相對目標位移較大的軸決定哪一側，斜角取左右，遠程攻擊也看目標背對自己的那格。修正規則只能用在 `hit_bonus`／`damage_permille` 等（現有 `change` 沒有「暴擊範圍」這種修正，規格寫的暴擊範圍用不到）。組合器不產生 `flanked`、`grant_skill`、`overwatch` 類技能。
5. **暫時技能的限制**：被給的技能一律只能是 **主動技能**（我把反應／被動／姿態／修正一併排除，規格只寫排除傳說與改寫規則型）；武器需求與法力照被給技能自己的規則，所以把法器技給弓手會「給了但按鈕停用」（AI 的 `_grant_supports` 會避開）。單位倒下後暫時技能保留（復活後仍在）；撤離不特別處理。
6. **夾擊位置加分只給新 AI 模式 `flanker`（`build_assassin` 英雄）**：直接加在 `brute`（敵方盜賊也用）會改變 3 個既有種子測試（totem、charger 的 swap、stun 的種子）與 `swamp` 種子 5 的 CLI 快照；若要全部近戰單位都會夾擊，把 `flank` 權重加到 `brute` 並重錄那幾個種子即可，建議在平衡階段一起決定。
7. **預設反應規則的做法**：監視射擊的反應規則是「裝備了會施加 `overwatch` 的技能（含它暫時給出的技能）才自動加上」，不是 `default_rules`，所以其他單位的反應列表不變；`requires_status` 是通用欄位，之後別的「需要狀態的反應」可沿用。
8. **`build_ranged` 換下升高平台、`build_assassin` 換下魯莽突刺、新增第 19 個 build `build_winged`**（接收升高平台）：與前幾段一樣的「主動欄位已滿」做法，3C-6 整理 build 時再看。`build_ranged` 的 AI 行為因此改變（掩護射擊觸發頻率下降，見第 4 節）。
9. **AI 係數都是初值**：`overwatch_points` 5（最多算 2 個敵人）、`grant_skill_points` 8 × 800‰ × 輪數、`flank` 3；暫時技能的 AI 價值只是近似（不看被給技能實際能做什麼）。夾擊技能在 sim 中很少用到（30 場約 2 次）。
10. **被給技能的預算遞迴**：`grant_skill` 的點數直接取被給技能的 `skill_budget().total`（含它自己的條件與協同），所以被給技能改數值時，給它的技能預算會跟著變；若被給技能本身超出預算，只有它自己被驗證器指出。

## 8. 代表性的 CLI 輸出節錄

`uv run trpg battle --map narrow_halls --seed 1 --ally-build build_ranged`，第 1 輪（連續的一段，未剪接）：主角施放「監視射擊」後離開，敵方弓手走回射程內，觸發監視射擊（這一箭自然 1 失手），監視結束：

```
— 遠程英雄 的回合（AP 3，移動 5，法力 24/24）
  遠程英雄 施放「監視射擊」（AP 1，冷卻 1 回合）→ 影響 1 格
  遠程英雄 獲得狀態「監視」
  遠程英雄 施放「時隙湧流」（AP 1，冷卻 2 回合，源力 1）→ 影響 1 格
    ✦ 遠程英雄 花費源力：源力 1 → 0
    遠程英雄 獲得 2 AP（現在 3 AP）
  遠程英雄 從 (0, 3) 移動到 (4, 2)（消耗 5 移動）
  遠程英雄 獲得狀態「防禦」
  遠程英雄 結束回合，保留 1 AP
— 盜賊 的回合（AP 3，移動 5）
  盜賊 從 (10, 4) 移動到 (6, 5)（消耗 5 移動）
  盜賊 攻擊 標準隊友（戰士）：d20=5 修正 -1 熟練 +2 = 6（目標 11）→ 失手
  盜賊 攻擊 標準隊友（戰士）：d20=5 修正 -1 熟練 +2 = 6（目標 11）→ 失手
  盜賊 攻擊 標準隊友（戰士）：d20=15 修正 -1 熟練 +2 = 16（目標 11）→ 命中
  ⟳ 標準隊友（戰士） 反應：格擋（耐力 −10）
    標準隊友（戰士） 受到 2 點物理傷害［骰 1］（元素修正 ×0.9）（格擋/加成 ×0.5），HP 60 → 58
  盜賊 結束回合
— 盜賊弓手2 的回合（AP 3，移動 5，法力 9/9）
  盜賊弓手2 攻擊 標準隊友（弓手）：d20=13 修正 -1 熟練 +2 = 14（目標 11）→ 命中
    標準隊友（弓手） 受到 9 點物理傷害［骰 5］，HP 16 → 7
  盜賊弓手2 攻擊 標準隊友（弓手）：d20=19 修正 -1 熟練 +2 = 20（目標 11）→ 命中
    標準隊友（弓手） 受到 11 點物理傷害［骰 7］，HP 7 → 0
  ＊ 標準隊友（弓手） 倒下了！
  盜賊弓手2 攻擊 標準隊友（戰士）：d20=10 修正 -1 熟練 +2 = 11（目標 11）→ 命中
    標準隊友（戰士） 受到 7 點物理傷害［骰 4］，HP 58 → 51
  盜賊弓手2 從 (10, 6) 移動到 (11, 2)（消耗 5 移動）
  ⟳ 遠程英雄 反應：監視射擊
  遠程英雄 攻擊 盜賊弓手2：d20=1 修正 +0 熟練 +2 = 3（目標 11）→ 自然 1，失手
  遠程英雄 的「監視」射擊後結束了
  盜賊弓手2 結束回合
```
