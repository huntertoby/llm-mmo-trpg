# Phase 3-21a 報告｜守護、換位、瞄準（玩法 #24）

> 規格：`docs/phases/Phase3計畫.md` 22.1；設計：`docs/design/05-戰鬥.md` 5.2.2。直接在 main 上實作，未 push。

## 1. 做了什麼

**引擎**（新模組 `engine/basics.py`；數值在 `content/rules/core.yaml`：`swap_ap_cost`、`aim_ap_cost`、`aim_hit_bonus`（2）、`guard_transfers_per_round`（1），防禦 +25% 沿用 `defend_defense_bonus_permille`）
- **守護**取代防禦：`Defend` 加可選 `target_id`（內部 ID 仍為 `defend`、狀態仍為 `defending`，狀態中文名改「守護」）。`target_id` 為空＝守護自己；給相鄰隊友時記錄 `guarding_id`，並發 `guard_set` 事件。到守護者下回合開始解除（`start_turn` 清除）。
- **轉移**：沿用 2E-2 的攔截呼叫點——`reactions.try_intercept` 先檢查「守護中的相鄰隊友」（`_guard_transfer`），成功發 `attack_intercepted`（新欄位 `guard=true`）並呼叫 `redirect_fired`，其後走既有「傷害改作用在守護者」路徑（普攻與單體技能共用，範圍技能不經此處）。不花反應、每輪上限由 `guard_transfers`（每輪開始歸零）控制。條件：守護者存活、仍有 defending 狀態、仍相鄰、未被暈眩。先於 `intercept` 反應技檢查。
- **換位**（`Swap`）：沿用 `SwapUnitsEffect`（事件 `unit_moved` mode `swap`）；朝向不變、不觸發藉機攻擊。不合法：不相鄰、非隊友、任一方被定身或速度 0、高低差達墜落門檻、AP 不足。
- **瞄準**（`Aim`）：`aimed` 旗標；下一次擲命中（普攻 `_attack_once`、技能 `_Cast._roll_one`，整次施放的每個目標共用加值）用掉旗標；`end_turn` 清除。不疊加（「已經瞄準了」）。
- **跑步遺留**：速度 0 不能跑（「速度為 0，不能跑」）。
- `legal_actions`：列出守護自己與每個相鄰隊友的 `Defend`、每個合法 `Swap`、合法時的 `Aim`（需 AP ≥ 瞄準＋1 且有普攻目標或可用技能）。`has_only_end_turn` 隨之把這些算進去（保持與 `len(legal_actions)==1` 一致）。預覽 `ap_cost` 補上守護、換位、瞄準。API 因動作聯集自動帶出新動作（`legal_actions` 即「可用動作與合法目標」），已重產 `openapi.json`、`schema.d.ts`。
- 事件與中文紀錄：`guard_set`（「X 守護 Y」）、`unit_aimed`、守護轉移（「X 守護 Y：Z 的攻擊改由 X 承受」）。

**AI**（`engine/ai/basics.py`；`content/ai_profiles.yaml` 的 `basic:`，標平衡階段初值）：守護隊友（隊友 HP<50%、6 格內有敵人、自己 HP≥50%、非速度 0 → 在守護自己的分數上 +3）、換位（隊友比自己更近敵人且 3 格內有敵人，且隊友 HP<35% 或自己最大 HP≥隊友 1.5 倍 → 6 分）、瞄準（AP 剛好夠「瞄準＋AP≥2 的攻擊」且該攻擊命中率<50% 有收益 → 該攻擊分數 +2）。條件不成立 0 分。

**前端最小接線**：「防禦」鈕改「守護」（守護自己，立即送出）；守護隊友、換位、瞄準進「其他動作（備援）」清單，標籤「守護：X」「換位：X」「瞄準」（3-21b 改成選單）。

## 2. 驗收

| 條件 | 證據 |
|---|---|
| 守護：自己／隊友、每輪 1 次、範圍技能不轉移、不相鄰不轉移、單體技能轉移、解除時機、數值來自 core | `tests/engine/test_basic_actions.py`：`test_guard_*`、`test_a_single_target_attack_on_the_guarded_ally_is_taken_by_the_guardian`、`test_a_single_target_skill_is_also_taken_by_the_guardian`、`test_area_skills_are_not_transferred`、`test_only_one_transfer_per_round`、`test_the_transfer_count_resets_every_round`、`test_transfer_count_comes_from_core_rules`、`test_no_transfer_when_the_guardian_is_no_longer_adjacent`、`test_guarding_yourself_never_transfers`、`test_the_guard_ends_when_the_guardians_next_turn_starts`、`test_illegal_guards_have_chinese_reasons` |
| 換位：互換、朝向不變、無藉機攻擊、召喚物、定身（任一方）、速度 0、非隊友、不相鄰 | `test_swap_*`（含 `test_swap_is_illegal_when_either_side_is_rooted[U1/U2]`） |
| 瞄準：+2 只用一次、不疊加、回合結束失效、技能也吃、AP/目標條件、數值來自 core | `test_aim_*` |
| 速度 0 不能跑 | `test_speed_zero_unit_cannot_run` |
| AI 三種情境會用、平常不用 | `test_ai_guards_a_weak_adjacent_ally_under_threat`、`test_ai_guards_itself_when_the_ally_is_healthy_or_out_of_threat`、`test_ai_swaps_a_weak_front_ally_to_the_back`、`test_ai_swaps_a_tank_to_the_front`、`test_ai_does_not_swap_without_a_reason`、`test_aim_bonus_scoring_conditions`、`test_ai_aims_before_a_costly_low_chance_attack` |
| 任一地圖 `--log-json` ＋ `replay` 一致 | `tests/cli/test_basic_actions_cli.py`（open_plain 種子 3 含換位、瞄準、守護隊友與一次轉移；ruined_fort 6、bridge_chasm 0）；`test_ai_basic_actions_replay_in_battle` |
| vitest | `client/src/battle/basicActions.test.ts`；vitest 527 項通過 |
| `check.py` 全過、`pnpm build` 成功 | `uv run python scripts/check.py`：全部通過（ruff、format、mypy、lint-imports、pytest、client typecheck／test）；`corepack pnpm -C client build` 成功（僅既有 chunk 大小警告） |

## 3. `LOG_FORMAT`
`trpg-battle-log/35` → `/36`（`runner.py` 註解）。舊 `/35` 紀錄與戰鬥中存檔不能由新版讀取（格式字串不符即拒絕，慣例同前）；動作 `defend` 的 `target_id` 預設為空，舊步驟本身仍可解析。

## 4. 換種子／快照（AI 軌跡改變）
- `test_summon_ai`（dark_forest：25→10，含重播）、`test_gamble`（build_gambler 反噬：5→12）、`test_displace_ai`（void swap：3→4）、`test_totem`（swamp：4→0，含重播）。
- `tests/cli/snapshots/cli_output_hashes.json` 以 `UPDATE_CLI_SNAPSHOTS=1` 重產（9 筆戰鬥輸出雜湊改變）。
- 格式字串 `/35`→`/36`：`test_battle_cli`、`test_skills_cli`、`test_run_battle_cli`；`test_combat` 的錯誤訊息「已處於防禦姿態」→「已處於守護姿態」。
- 過程中發現：瞄準的 AI 條件初設命中率<70% 會改變約 30 項整場測試軌跡，收緊為 50% 後只剩上述 4 項。`test_training_range` 的木樁曾因守護加分而出手，已加「速度 0 不守護隊友」。

## 5. 新增的複雜度 noqa
無（`rank`、`_has_ap_action` 以抽出 `_score_aim`、`_cheap_score`、`_has_basic_action` 解決）。

## 6. 待 PM 決定
1. 「防禦」改名「守護」只改玩家看到的文字；內部 ID `defend`／`defending` 與 `defend_ap_cost` 等保留。
2. 守護隊友在前端先放「其他動作（備援）」，常駐按鈕只守護自己（3-21b 做選單）。
3. 守護轉移的順位：先於 `intercept` 反應技，多名守護者時依單位 ID 第一個；轉移不花反應、不要求守護者有反應次數。
4. 守護者被暈眩時不轉移（保守）；未限制守護者倒地以外的狀態。
5. 換位保守加了「高低差達墜落門檻不能換」「速度 0（含圖騰）不能換」；換位抵達格仍會結算陷阱、表面、持續區域（沿用 `swap_units`）。
6. 瞄準只在有 AP 再打一次且有普攻目標或可用技能時列出；`has_only_end_turn` 因此不再於「只剩換位／瞄準」時自動結束回合。反應技（被動施放）也可能用掉瞄準旗標。
7. AI 瞄準規則偏窄（只在「瞄準＋AP≥2 的低命中攻擊」且 AP 剛好時）；2 AP 時先瞄準再普攻通常不如打兩下，故未納入。所有 AI 數值未經模擬，請平衡階段調整。
8. 敵人與速度 0 的單位：AI 不會用守護隊友（維持木樁不動）；換位對方若是速度 0 的隊友一律不合法。
9. 規格 22.1 第 1 項「回合逾時自動守護自己」：後端沒有逾時機制，前端也未見逾時行為，本段未實作；若日後加逾時，直接送 `Defend`（無目標）即可。
