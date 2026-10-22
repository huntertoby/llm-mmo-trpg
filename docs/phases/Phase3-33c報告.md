# Phase 3-33c 報告｜召喚物操控

> 規格：`docs/phases/Phase3計畫.md` 36.3；設計：`docs/design/06-技能.md` 6.29.2、6.29.5。數值都是初值（`content/rules/core.yaml`、`content/ai_profiles.yaml`），沒有調任何既有數值。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| 模式 | `UnitState.summon_mode`（`focus`／`guard`／`follow`／`hold`）、`summon_target_id`、`commanded_round`；召喚時取範本的 `default_mode`（`UnitTemplate`，預設 `follow`；戰意圖騰 `hold`，對應 6.29.5「不動」） | `engine/state.py`、`content/battle.py`、`content/units/summons/summon_war_totem.yaml` |
| 0 AP 切換 | 新動作 `set_summon_mode`（集火必帶 `target_id`＝場上敵人，其他模式不可帶；與目前完全相同、不是自己的、圖騰、已消失都不合法）；歸在管理操作、不列入 `legal_actions`（同 `set_reaction_mode`）；事件 `summon_mode_set` | `engine/actions.py`、`engine/summon_control.py`、`engine/battle.py` |
| 集火退回跟隨 | 目標倒下、撤離或消失時，以牠為目標的召喚物改回跟隨，發 `summon_mode_set(reason=target_gone)` | `engine/lifecycle.py`（`retire_focus`） |
| 1 AP 指揮 | 新動作 `command_summon`（`path`＋`target_id`，至少一個）：花 `summon_command_ap_cost`（`core.yaml`，1），讓召喚物用牠完整的移動力走 `path`、再普攻；結算後還原牠的 AP／移動點數（不佔牠的回合）；每隻每輪 1 次；暈眩、圖騰、AP 不足、移動力不夠、攻擊打不到都不合法（拋錯、狀態不變）；移動照常觸發藉機攻擊與反應，被打倒就不攻擊；事件 `summon_commanded` | 同上 |
| 指揮選項 | `GET /api/battles/{id}/summons/{sid}/command-options`：可到達的終點（含原地）、路徑與各終點打得到的敵人 | `api/routes/battles.py`、`api/schemas.py`、`engine/summon_control.py`（`command_options`） |
| AI：四種模式 | 沿用效用 AI 的戰術指令（軟性）＋合法動作過濾（硬性）：待命＝不移動、只打相鄰；守護我＝保護施放者、只走到 `guard_radius`（2）格內（已在外面時只走更靠近的）、有「威脅施放者」的敵人可打時只打他們（敵人射程＋速度＋`guard_threat_range`≥與施放者距離）；集火＝集火目標打得到時只打牠，打不到但有路靠近時也不打別人；跟隨＝待在施放者 `follow_radius`（3）格內（軟性，仍主動攻擊） | `engine/ai/summon.py`、`engine/ai/utility.py` |
| AI：自動切換 | 我方（`Team.ALLY`）非召喚物單位由 AI 操作時：HP 低於 `auto_guard_hp_permille`（400‰）全部改守護我；否則場上有 Boss 且 `auto_focus_boss` 時全部改集火 Boss（最小單位 ID）；一次回傳一個 0 AP 動作，已符合就不再切換。敵方不自動切換 | `engine/ai/summon.py`（`auto_mode_action`）、`UtilityAI.__call__` |
| AI：估值 | `summon_dpr(…, flat, bonus_permille)`；`summon_gains` 用 `growth_of` 的固定傷害與加成，帶灌注的每輪加 `infusion_points`（1）；被擠掉的舊召喚物用牠實際的加成與灌注 | `content/summons.py`、`engine/ai/summon.py` |
| 視圖／API | `UnitView.summon_mode`／`summon_target_id`／`commanded`（圖騰與一般單位為 `None`）、`BattleView.summon_command_ap_cost`；OpenAPI 與 `schema.d.ts` 已重產 | `engine/view.py` |
| 紀錄文字 | 「X 切換為集火 → Y」「集火目標 Y 離場：X 退回跟隨」「A 指揮 X：移動到 (x, y)、攻擊 Y」 | `narrative/events.py` |
| 前端 | `SummonPanel`（浮在戰場右上，列出主角的召喚物：HP、剩餘輪數、目前模式；4 個 0 AP 模式按鈕標示目前模式，集火再選敵人；「指揮（1 AP）」）；指揮流程：取得選項後地圖標出藍格（可到達）、選終點後紅框標可打的敵人，用地圖或下拉清單選終點，再按「移動並攻擊」或「只移動」；滑過按鈕預覽該指揮；單位資訊卡多「模式」一列；紀錄與動作標籤支援新動作 | `client/src/battle/summonControl.ts`、`ui/SummonPanel.tsx`、`screens/BattleScreen.tsx`、`ui/UnitInfo.tsx`、`battle/actions.ts` |
| 格式 | `LOG_FORMAT` `/49 → /50`（PM 合併時定號） | `engine/runner.py` |

## 2. 驗收證據

| 驗收項 | 證據 |
|---|---|
| 四種模式的 AI 行為 | `tests/engine/test_summon_control.py`：`test_hold_*`（不動、只打相鄰）、`test_guard_never_wanders_*`、`test_guard_hits_the_enemy_threatening_the_owner_first`、`test_focus_attacks_only_the_chosen_target_*`、`test_focus_walks_toward_a_far_target_*`、`test_follow_has_a_soft_leash_*`、`test_summon_orders_ignore_team_orders` |
| 集火目標倒下退回跟隨 | `test_a_downed_focus_target_sends_the_summon_back_to_follow`、`test_a_focus_target_that_is_gone_is_treated_as_follow_by_the_ai` |
| 指揮的移動範圍與每輪 1 次 | `test_command_move_is_limited_by_the_summons_movement`、`test_command_attack_must_be_in_reach_after_the_move`、`test_a_summon_can_be_commanded_once_per_round`、`test_command_options_list_reachable_tiles_*`（每個選項的路徑都能被接受） |
| 0 AP／1 AP 扣點 | `test_switching_modes_costs_no_ap_*`、`test_command_moves_and_attacks_for_one_ap_without_using_the_summons_turn`（召喚物自己的 AP、移動點數不變）、`test_command_needs_enough_ap` |
| 不合法的請求 | 不是自己的／圖騰／已消失／暈眩／集火對象不是敵人／重複模式（`test_illegal_mode_changes`、`test_only_your_own_*`、`test_command_rejects_*`） |
| AI 自動切換與估值 | `test_ally_ai_focuses_the_boss_and_guards_when_hurt`、`test_no_boss_and_healthy_*`、`test_the_utility_ai_issues_the_switch_before_acting`、`test_summon_valuation_counts_growth_and_infusion` |
| 同種子確定、`--log-json` ＋ `replay` | `test_command_is_deterministic_and_replayable`、`test_a_boss_battle_with_mode_switches_replays_identically`（dev_summoner 打 Boss，AI 自動集火；重播終局與事件序列逐位元一致）；既有 CLI 的 `--log-json`／`replay` 測試全過（格式字串更新為 `/50`） |
| API | `tests/api/test_summon_control_api.py`（視圖欄位、切換 0 AP、集火驗證 422／400、指揮選項、預覽、指揮 1 AP、同輪重複 400） |
| 前端 | `summonControl.test.ts`（按鈕出現條件：圖騰／別人的召喚物／已消失不出現；目前模式標示；指揮鈕的限制；指揮動作與選項）；`tsc`、`vitest`（714）、`pnpm build` 通過 |
| 全量 | 見第 6 節 |

被迫改的既有測試：`LOG_FORMAT` 斷言（8 個檔）、`test_weapons_24a2.py`／`test_vault.py` 的動作分類（多了兩個動作）、`test_summon_ai.py`（估值納入成長；整場戰鬥的種子 0→6，因為召喚物預設「跟隨」待在施放者附近，原種子的骷髏沒有出手）。

### 2.1 瀏覽器實測（`dev_summoner`，吊橋深淵，伺服器 8766 埠；未動 8000 埠）

- 瀏覽器窗格的**滑鼠點擊不會觸發畫布與按鈕動作**（同 3-33b 報告）：改用 `javascript_tool` 對畫布送 pointer 事件、對按鈕呼叫 `click()`，其餘（畫面、截圖、浮動卡計時）都是真的畫面。
- 起手：召喚「元素之靈」→ 面板出現（模式：跟隨，`docs/phases/img/3-33c-summoned.jpg`）。
- **切換模式**：按「守護我」→ 模式標示改為守護我、不花 AP（AP 仍 2）（`3-33c-mode-guard.jpg`）。
- **指揮**：按「指揮（1 AP）」→ 地圖標出藍格與下拉清單 → 選 (6, 1) → 紅框標出可打的盜賊1、盜賊2（`3-33c-command-pick.jpg`）→「移動並攻擊 盜賊1」→ 召喚物走到 (6, 1) 並攻擊，主角 AP 2→1，面板顯示「本輪已指揮」、指揮鈕灰掉（`3-33c-command-done.jpg`）。
- **6.5.1 浮動卡**：面板標題「召喚物操控 ⓘ」與每個模式／指揮按鈕都用 `PartTip`（沒有原生 `title`）。標題卡實測：滑入觸發（150ms 後顯示）→ 移到卡片上離開觸發元素後仍開著 → 點一下釘住（`aria-expanded=true`，離開後仍開）→ Esc 關閉（`3-33c-float-card.jpg`）。卡片內容高度 197px，在 1024×768 窗格不會超出可見區域，所以「捲到底」沒有東西可捲（共用元件的最大高度規則沒動）；**未測 800×600**。
- 發現並修了：說明文字的換行被吃掉（`.part-tip-text` 加 `white-space: pre-line`，截圖是修前的）。
- 實測時有一張模式說明卡因為用 JS 觸發點擊、沒有對應的 pointerleave 而殘留（按 Esc 即關），屬測試手法的人為現象。
- 截圖皆為 jpg（瀏覽器工具只輸出 jpg）。

## 3. 規則與行為的取捨

1. 召喚物不再吃「隊友指令」（陣營的集火／保護／守位）：牠只依自己的模式；`UtilityAI.order_context` 對召喚物改用模式轉成的指令。
2. 「跟隨」預設比以前保守（待在施放者 3 格內，每超出 1 格扣 `orders.hold_weight` 分）：以前的召喚物會無限追敵人。這讓一般模擬的召喚物行為改變（`/50`）；是否過於被動請看 3-33g 的模擬。
3. 「待命」：Defend、Aim 等原地動作仍可做，只禁止移動／換位與非相鄰攻擊。
4. 指揮 `command_summon` 不列入 `legal_actions`，所以自動推進的「只剩結束回合」判斷不受影響；代價是 AI 不會主動指揮（規格只要 AI 切換模式）。

## 4. 待 PM 決定

1. **`LOG_FORMAT` 定為 `/50`**，合併時請依實際順序改。
2. **跟隨半徑 3、守護半徑 2、威脅寬限 1、自動守護門檻 HP 40%、`infusion_points` 1** 皆為初值，未經模擬；「跟隨」變得比以前被動（見 3.2），建議 3-33g 對照模擬時檢視。
3. **自動切換只對我方 AI 的施放者**（含自動代打）；敵方召喚者不切換。若要敵方也用請說。玩家操控的主角不會被自動切換。
4. **集火不能是召喚時的預設**（需要目標），預設只有 `guard`／`follow`／`hold`；目前只有戰意圖騰是 `hold`，其餘 `follow`（6.29.5 的「守衛」「不動」等欄位在 e1／e2 新增召喚物時用 `default_mode` 填）。
5. **AI 不主動使用「指揮」**（組合多、價值難估）；需要的話請另開項目。
6. **指揮的 AP 檢查與主角的 AP 共用**：主角 AP 用完時，自動推進會立刻結束回合，玩家就沒機會再切換模式——要在行動中途切換，請在最後一個耗 AP 的動作之前做。若要「AP 為 0 時仍保留回合讓玩家切換」需改自動推進規則。
7. **圖騰沒有模式**（視圖為 `None`、面板不顯示），範本的 `default_mode: hold` 只是資料上標明。
8. **瀏覽器實測缺口**：畫布與按鈕的滑鼠點擊在此窗格不會觸發，流程是靠 JS 事件驅動；800×600 的浮動卡未測、卡片內捲動未測（內容不夠高）。

## 5. noqa

新增一個 `# noqa: PLR0913`（`engine/ai/summon.py` 的 `_value`：價值估算需要的關鍵字參數 `flat`／`bonus_permille`／`infused` 加上原有的 6 個參數；拆成 dataclass 會讓只有兩個呼叫端的私有函式更難讀）。測試內有數處 `PLC0415`（函式內 import，沿用既有作法）。

## 6. 最終檢查

- 已過：`ruff check`、`ruff format --check`、`mypy`（533 檔）、`lint-imports`（6 契約）、client `tsc`／`vitest`（714）／`pnpm build`。
- pytest 分段：`tests/engine tests/api tests/narrative tests/cli tests/test_architecture.py` 2798 通過、14 個失敗全是 `LOG_FORMAT /49→/50` 與動作分類／種子的預期更新（已改並單檔重跑通過）；`tests/content`、`tests/sim/test_summon_report.py` 與 8 個改過的重播測試重跑通過（625 通過）。
- **未能完整跑完**：`tests/roguelite`（含整輪自動遊玩的重播測試）、其餘 `tests/sim`、`tests/skillgen`、`tests/shared`、`test_sim_scripts.py`、`test_play_script.py`。與另一個 agent 同時跑時機器嚴重過載（單一整輪測試單跑 14 秒，同時跑卡了 25 分鐘以上），`scripts/check.py` 全量沒有跑完；`test_evolution.py` 的前 5 個整輪測試與 `test_keyword_start.py` 前段已通過。**請 PM 在合併後自己跑一次完整 `check.py`**；召喚物 AI 行為改變（跟隨待在施放者附近）可能讓使用固定種子的整輪或模擬測試需要換種子（`test_summon_ai.py` 就換了一個）。
