# Phase CB-1 完成報告｜命中門檻 #146 與靶場示範招 #148

基準 commit `e10d3946`。本段沒有跑平衡模擬（規格排在 #149 之後的 CB-2）。

## 交付

| 項目 | 內容 | commit |
|---|---|---|
| #148 | `content/world/newcomer.yaml` 的 `range.demos` 換成 6 招；6 招都對得到現有技能 ID，沒有造招或換招 | `f3cfc647` |
| #146 | `content/rules/core.yaml` 的 `hit_target` 11 → 8，註解更新 | `d23dbe44` |
| 寫死舊值 | 測試、`core.yaml`／`rules.py` 的註解、前端詞彙 fixture | `d23dbe44` |

示範招 ID：近戰 `skill_shadow_backstab`、`skill_tower_slam`；遠程 `skill_scatter_shot`、`skill_suppressing_fire`；法器 `skill_fire_bolt`、`skill_spark_chain`。

## 逐條驗收

| 驗收條件 | 結果 | 證據 |
|---|---|---|
| `ruff check` | 通過 | `All checks passed!` |
| `ruff format --check` | 通過 | `2243 files already formatted` |
| `uv run mypy` | 通過 | `no issues found in 1417 source files` |
| `lint-imports` | 通過 | `Contracts: 14 kept, 0 broken.` |
| `tests/engine`、`content`、`api`、`cli`、`world`、`test_architecture.py`（`TRPG_FULL=1 -m "not llm"`） | 通過 | 連同 `tests/narrative`、`roguelite`、`sim` 一起跑：`9978 passed, 1 skipped, 4 xfailed` |
| 至少 3 張地圖、不同種子 `--log-json` ＋ `replay` | 通過 | open_plain 7（88 動作）、oil_depot 13（63）、bridge_chasm 3（84）、swamp 21（61），都是「重播驗證通過」 |
| 前端 `typecheck`、相關 vitest、`npx vite build` | 通過，結束碼都是 0 | `range`、`logGroups`、`scenePreview` 共 39 個測試 |

### 行為一致測試

| 規格 | 測試 |
|---|---|
| 攻擊在總值 7、8 的邊界 | `tests/engine/test_hit_target_146.py::test_attack_boundary`、`test_skill_attack_boundary` |
| 控制對抗的邊界 | `test_control_boundary` |
| 戰技對抗的邊界（推擊、絆倒） | `test_maneuver_boundary` |
| 自然 1 仍失手 | `test_attack_natural_one_misses_even_above_the_target`、`test_control_natural_one_fails_even_above_the_target`、`test_maneuver_natural_one_fails_even_above_the_target` |
| 自然 20 仍命中 | `test_attack_natural_twenty_hits_at_the_lowest_modifier`、`test_control_natural_twenty_succeeds_at_the_lowest_modifier`、`test_maneuver_natural_twenty_succeeds_at_the_lowest_modifier` |
| 引擎命中率與預覽一致（窮舉 d20 跑引擎） | `test_preview_matches_engine_for_attack`、`_for_skill_attack`、`_for_control`、`_for_maneuver` |
| 6 招都能在靶場施放 | `tests/world/test_opening.py::test_all_demos_cast_in_the_range_with_every_weapon`（跑引擎，該大類每把武器）、`test_demos_are_the_148_skills`、`tests/api/test_range_api.py::test_trial_offers_the_148_demos` |

自然 20 的測試用的是最低修正 −8：20 − 8 + 2 ＝ 14，本來就超過門檻 8，所以這三條只確認結果，無法單獨證明「必中」規則生效。必中規則本身由 `tests/engine/test_combat.py::test_natural_one_and_twenty` 直接測 `is_hit`。

## 起手角色對一般敵人的命中率（引擎 `preview` 計算）

算法：23 把開局武器的起手角色（推薦配點）對 34 種一般敵人（排除頭目、精英、護衛、木樁、不動物、召喚物），取平均。

| 項目 | 門檻 11（舊） | 決定紀錄（舊） | 門檻 8（新） | 決定紀錄（目標） |
|---|---|---|---|---|
| 主角打一般敵人 | 61.3% | 61% | **76.2%** | 76% |
| 主角打第一關盜賊 | 55.2% | 55% | 70.2% | — |
| 敵人打主角 | 56.4% | 57% | **71.4%** | 72% |

舊值和決定紀錄對得上，代表算法一致。

## 受影響的既有功能盤點

| 項目 | 結果 |
|---|---|
| 引擎命中、控制、戰技 | `combat.py`、`control.py`、`maneuvers.py` 都讀 `core.hit_target`，沒有寫死 11 的程式 |
| 預覽 | `preview.py` 都讀 `core.hit_target`；一致性測試通過 |
| AI 評分 | 程式沒有寫死門檻，都走預覽的命中率。權重沒動，但行為會變，見「待 PM 決定」2、3 |
| 模擬 | 沒有寫死門檻 |
| LLM 提示詞 | `src/trpg/llm/prompts` 沒有引用門檻或命中率，不必升版 |
| 說明文字 | `narrative/action_info.py`、`events.py` 動態讀門檻，自動變成「≥ 8」；`client/src/battle/fixtures/glossary.json` 用 `scripts/export_client_fixtures.py` 重產（3 行） |
| 前端 | 沒有寫死門檻的顯示；`logGroups.test.ts` 的範例字串改成「目標 8」 |
| 世界日誌與存檔 | `content/` 改動由內容 digest 涵蓋，`WORLD_RULES_VERSION` 沒有加一 |
| TR-1 靶場 | 流程測試通過 |
| 錄製的前端 fixture | `client/src/battle/fixtures/vfx_random_skills.json` 內的 `target_number: 11` 是過去錄下的事件，只用來測特效，保留不動 |

## 重產的快照與改動的測試

**先確認變化只來自門檻**：把 `hit_target` 暫時改回 11（示範招維持新的）時，`tests/cli/test_output_snapshots.py` 25 個全過，改回 8 才有 7 個變動。所以示範招不影響快照，7 個雜湊的變化全部來自門檻。改動前的基準是 `9535 passed, 0 failed`。

| 類別 | 檔案 | 原因 |
|---|---|---|
| CLI 快照（7 個 `battle_*` 雜湊，其餘 18 個不變） | `tests/cli/snapshots/cli_output_hashes.json` | 命中結果改變，戰鬥紀錄不同 |
| 詞彙 fixture | `client/src/battle/fixtures/glossary.json` | 公式說明的「≥ 11」→「≥ 8」 |

**改寫死機率或骰值的測試（照新門檻算）**：`test_combat`、`test_cover`、`test_maneuvers`、`test_preview`、`test_charge_through`、`test_charge_through_api`、`test_displace_others`、`test_status_control`、`test_rules`、`test_battle_log_text`。

**換種子的測試**（AI 軌跡改變，指定事件不再出現；斷言與重播比對不動，符合專案既有的換種子慣例）：

| 測試 | 舊 → 新 |
|---|---|
| `test_boss_phases` | 3、4 → 0、5 |
| `test_combo_resources`（seer 兩條） | 5 → 2 |
| `test_displace_ai` 虛空互換 | 17 → 55 |
| `test_gamble` | 3、55 → 17、27 |
| `test_grant_skill` | 2 → 7 |
| `test_hurl_object` | 11 → 14 |
| `test_reaction_events` | 悲憤 1 → 5；掩護射擊 2 → 8 |
| `test_rule_changes` | 2 → 4 |
| `test_scene_ai` | 穿透 1 → 2；推倒 7 → 13 |
| `test_self_moves` | open_plain 1 → 0 |
| `test_summon_ai` | 4 → 5 |
| `test_totem` | swamp 0 → 2；swamp 3 → 4 |
| `test_basic_actions_cli` | ruined_fort 6 → 1 |
| `test_demo_maps` | bridge_chasm 26 → 3；ruined_fort 1 → 3 |
| `test_striker_trapper_battle` | 35 → 115 |
| `VICTORY`（`tests/roguelite/helpers.py`）、`test_attribute_text_api`、`test_attribute_respec` | 1 → 3（種子 1 的 build_fire 第 3 場就輸了） |

**不是單純換種子、請 PM 過目的兩處**：

1. `test_basic_actions_cli::test_open_plain_battle_uses_guard_swap_and_aim_and_replays` 拆成兩個測試（`..._uses_guard_and_replays` 種子 60、`..._uses_swap_and_aim_and_replays` 種子 419）。open_plain 前 1500 個種子沒有一場同時出現換位、瞄準、守護加攔截。斷言內容不變，兩場都照舊重播，只是不再要求發生在同一場。
2. `test_ai_utility` 的 `_crossroads` 場景與 `test_displace_ai::test_the_ai_swaps_a_nearly_dead_ally_out_of_the_enemies_reach` 把場景固定在 `hit_target: 11`。這兩個是分數校準過的單步 AI 場景，門檻 8 時弓手改選推擊、救援改選普攻。`_crossroads` 原本就用同樣做法固定敵方傷害倍率。這代表這兩個測試**不驗證門檻 8 下的 AI 選擇**。

確定性與重播比對都沒有放寬。

## 沒有跑的項目

`tests/skillgen`、`tests/llm`、`tests/server`、`tests/bot`、`tests/shared`、根目錄的 `test_sim_scripts.py` 等，依規定留給 PM 合併後的全量檢查。

## 待 PM 決定

1. **與設計文件衝突**：`docs/design/06-技能.md` 寫傳送到致命地形「同級成功率約 10–15%」，門檻 8 後實際是 **25%**（總抵抗 +10 時，自然 16 以上成功）。規格要求不改其他數值，所以我沒動。若要維持設計值，`teleport_lethal_resist_bonus` 8 → 10 是 15%，8 → 11 是 10%（一行 yaml 加相關測試）。需要玩法 PM 或使用者決定。一般傳送的同級成功率也從 50% 變成 65%。
2. **AI 很少瞄準**：`aim_hit_permille` 是 500，只有命中率低於 50% 才瞄準。open_plain 1500 個種子只有 85 場（5.7%）用到瞄準。要不要調排到 CB-2。
3. **AI 個性差異縮小**：`_crossroads` 場景在門檻 8 時弓手和狡猾都選推進深淵，受傷隊友的救援也輸給普攻。權重沒動，建議併入 CB-2。
4. **難度訊號（未量化）**：`test_demo_balance` 的 4 張示範地圖由 xpassed 變成 xfailed（目標勝率 35–65%、平均 4–6 輪，標記為延後處理）；build_fire 種子 1 也從全勝變成第 3 場落敗。敵我命中都上升，整體難度要等 CB-2 的模擬。
5. **示範招的附帶效果多半看不到**：塔盾猛擊的擊倒只有拿塔盾才觸發，散彈驅離的推人只有霰彈槍，壓制射擊的緩速只有雙槍。其他武器示範時只有傷害。這是技能資料本來的條件，#148 指定這 6 招，所以照做；是否要在靶場畫面說明，請玩法 PM 看。
6. 靶場示範招的稀有度混了 rare（原本 TR-1 註解寫「1 階普通」）。檢查規則只要求 1 階主動技且該大類每把武器都能用，已通過；舊註解已更新。
