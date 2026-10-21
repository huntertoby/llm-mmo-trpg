# Phase 3-21b 報告｜攀跳 ＋ 常駐 5 鈕與「更多動作」選單（玩法 #24）

> 規格：`docs/phases/Phase3計畫.md` 22.2；設計：`docs/design/05-戰鬥.md` 5.2.2。分支 `worktree-agent-ae142e634d84bcc07`（從 main 9baf74b 分出），未 push、未合併。

## 1. 做了什麼

**引擎**（`engine/basics.py`、`engine/battle.py`；數值在 `content/rules/core.yaml`：`vault_ap_cost` 1、`vault_move_cost` 2、`vault_climb_height` 2、`vault_jump_width` 1）
- 新動作 `Vault(dest)`（`type: vault`）；落點能分辨攀爬或跳躍，所以不另帶 mode。事件 `unit_vaulted`（kind climb／jump）＋ 一個 `unit_moved`（mode walk，cost 2）。
- **攀爬**：落點相鄰、可站立、無單位、高度差大於一般 `max_climb_height` 且不超過 `vault_climb_height`。**跳躍**：正前方隔 1 格（`vault_jump_width`）深淵／岩漿類缺口（地形致命、無橋）；缺口不能有單位或 `blocks_move` 物件，牆壁不算缺口；落點須可站立、無單位、不比起點高超過 1 層、落差不到墜落門檻。
- 其他不合法：定身、倒地、速度 0、AP 或移動點數不足、恐懼來源方向。藉機攻擊沿用 `opportunity_attacks`（起點相鄰、落點不相鄰才觸發）；被打倒、被推開、暈眩或倒地則攀跳中止（AP 已付）。落點照常結算陷阱、表面、墜落、`on_move`。
- `legal_actions`、`has_only_end_turn`（只剩攀跳時不自動結束回合，同 3-21a 慣例）、預覽 `ap_cost`、敘事文字（「X 攀爬到／跳到 (x,y)」）。API 因動作聯集自動帶出，已重產 `openapi.json`、`schema.d.ts`。
- **AI**（`ai/utility.py` 的 `vault_score`；`content/ai_profiles.yaml` 的 `basic.vault_points` 4、`vault_min_saving` 4）：攀跳落點走到最近敵人的步數（走路規則）比現在少至少 4 步（現在走不到、落點走得到也算）才給分，其餘 0 分。

**前端**
- 常駐 5 鈕（移動、普攻、跑步、守護、結束回合）＋「更多動作」選單（`ui/TurnControls.tsx`）；選單只列當下合法的推擊、絆倒、互動（推動／撥開）、換位、瞄準、攀跳（`targeting.ts` 的 `moreModes`；灰色「推不動」模式不列）。「移動」＝回到移動模式（取消選取，點亮格即移動）。技能列只留結束姿態、起身。舊的「其他動作（備援）」改為選單尾端的 `extra`（正常為空）。
- 守護：按「守護」後點自己＝守護自己、點相鄰隊友＝守護他；相鄰沒有隊友時仍立即守護自己。
- 攀跳落點用紫色（`HIGHLIGHT.vault`）標示，攀爬寫「攀」、跳躍寫「跳」（`Highlights.vaults`，新增可選欄位）。
- 3-18b 遺留：工坊「清空重來」改頁內確認（`resetStep`）。
- 3b 美術小修：刪除 `pedestalScale` 與測試（`heightModel.ts` 整檔刪除）、`unitSprite` 不再畫底座；高度徽章改為「同高相連一片只標一個，放在最上排最左格」，單獨一格照標，整張圖同高不標（`artSpecs.heightBadges`）；地形資訊卡本來就顯示高度，未動。

## 2. 驗收

| 條件 | 證據 |
|---|---|
| 攀爬（高 2 層、花 1 AP＋2 移動點、一般移動走不上） | `tests/engine/test_vault.py`：`test_climb_moves_up_two_levels_and_costs_ap_and_move_points`、`test_a_normal_move_cannot_climb_two_levels_but_vault_can`、`test_climbing_one_level_is_a_plain_move_not_a_vault`、`test_climbing_three_levels_is_too_high` |
| 跳躍（越過 1 格缺口、2 格太遠、牆不算） | `test_jump_over_a_one_tile_chasm`、`test_jump_is_not_offered_when_the_middle_tile_is_walkable`、`test_jump_over_a_two_wide_chasm_is_too_far`、`test_jump_over_a_wall_is_illegal` |
| 遇單位或擋路物件不合法 | `test_climb_onto_an_occupied_tile_is_illegal`、`test_jump_over_a_unit_standing_on_the_gap_is_illegal`、`test_jump_over_a_blocking_object_is_illegal`、`test_jump_landing_occupied_or_unstandable_is_illegal`、`test_jump_landing_too_high_or_too_low_is_illegal` |
| 藉機攻擊 | `test_leaving_an_adjacent_enemy_provokes_an_opportunity_attack`、`test_staying_adjacent_to_the_enemy_does_not_provoke_an_opportunity_attack` |
| 狀態與資源（定身、倒地、速度 0、AP、移動點）、數值來自 core | `test_vault_needs_ap_and_move_points`、`test_vault_is_illegal_when_rooted_prone_or_speed_zero`、`test_vault_numbers_come_from_core_rules` |
| AI 會跳過深淵、小收益不用 | `test_ai_jumps_a_chasm_that_blocks_the_whole_path`、`test_ai_does_not_vault_for_a_small_saving` |
| 重播一致 | `test_vault_battle_replays_identically`（AI 對戰含 `vault`，`replay` 事件一致）；既有 CLI `--log-json` ＋ `replay` 測試（open_plain、ruined_fort、bridge_chasm）全過。真實地圖上 AI 在種子 0–7 的 bridge_chasm、cliff_outpost、lava_crossing、ruined_fort、open_plain、frozen_lake、oil_depot 都沒選攀跳（條件收得很緊），所以含攀跳的整場重播以自訂地圖測試為準 |
| 基本動作上限 10 | `test_basic_actions_stay_within_the_limit_of_ten`（Python）；`basicActions.test.ts`「keeps the number of basic actions within the limit of 10」 |
| vitest：選單只列合法動作 | `basicActions.test.ts`：`more-actions menu`（固定順序、換位只在相鄰隊友時、攀跳只在有落點時、灰色模式不列、常駐／選單／技能列不重疊）、`vault`（落點點選、攀爬／跳躍標示）、守護點自己或點隊友 |
| 3b 美術 | `art.test.ts`：高度徽章（一片一個、單格照標、兩片不相連各一個、台階各標各的、全圖同高不標）；`geometry.test.ts` 接手 TILE_SIZE 的測試 |
| 清空重來頁內確認 | `workshop.test.ts`「reset confirmation」 |
| 截圖 | `docs/phases/img/3-21b-resident-buttons.png`（常駐 5 鈕）、`3-21b-more-menu.png`（相鄰有隊友、面前有高台時選單：換位、瞄準、攀跳）、`3-21b-vault-landings.png`（攀爬與跳躍落點標示）、`3-21b-after-climb.png`（攀爬後 AP 3→2、移動 5→3，高台只有一個 ▲2）。DOM 量測：5 鈕在 220px 寬面板內，面板底 749 < 視窗 768，無溢出；瀏覽器無 console 錯誤（未見）。截圖用的暫時地圖已刪除、未提交 |
| `check.py` 全過、`pnpm build` 成功 | `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest、client typecheck／test（vitest 539）全部通過；`corepack pnpm -C client build` 成功 |

## 3. `LOG_FORMAT`
`trpg-battle-log/36` → `/37`（`runner.py`）。舊 `/36` 紀錄與戰鬥中存檔不能由新版讀取。四個 CLI 測試的格式字串與 `cli_output_hashes.json` 快照因此更新（唯一原因是格式字串）。

## 4. 換種子
無：AI 在既有測試軌跡中不會選攀跳，沒有釘種子的測試因此改變。

## 5. 新增的複雜度 noqa
無（`vault_plan`、`_build` 以抽出 `_vault_state_problem`、`_basic_ap_cost` 解決）。

## 6. 待 PM 決定
1. 攀跳的保守限制：倒地、速度 0、受恐懼來源方向限制時不可用；跳躍落點不能比起點高超過 1 層、落差達墜落門檻（2 層）不可跳（避免跳下去摔傷）。
2. 跳躍只有「缺口地形＝致命地形（深淵、岩漿、冰窟）」才算；牆壁不算，可站立的格子（含有橋）也不需要跳。
3. 藉機攻擊只看起點與落點的相鄰關係（不看跳過的中間格）。攀跳被藉機攻擊打斷時 AP 已付、移動點未扣。
4. 只剩攀跳可做時不自動結束回合（同 3-21a 換位、瞄準）。
5. AI 攀跳數值（4 分、至少縮短 4 步）與判斷是平衡階段初值；目前在既有地圖上 AI 幾乎不會用，需要時請於平衡階段放寬。
6. 「移動」鈕的語意為「回到移動模式」（取消選取），不是新動作；常駐鈕在不可用時灰掉（普攻無目標）。
7. 選單不列灰色的「推不動物件」，因此失去「為什麼推不動」的提示（物件模式的點選提示仍在）；若要保留可在選單尾端列灰色項目。
8. `ui/workshop/StepView.tsx` 換骨架仍用 `window.confirm`（規格只要求「清空重來」），未動。
9. 單位底座陰影移除後，`heightModel.ts` 整檔刪除（只剩 `pedestalScale`）。
