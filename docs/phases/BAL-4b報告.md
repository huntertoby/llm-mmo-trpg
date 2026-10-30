# BAL-4b 完成報告｜採用數值寫進 content、Boss 戰陣容獨立、複測

## 1. 做了什麼

| 項目 | 做法 |
|---|---|
| 數值進 content（原型專用，已加註解） | `content/rules/core.yaml`：`enemy_damage_permille: 1200`、`boss_damage_permille: 1000`、`boss_escort_damage_permille: 1200`、`ally_mana_cost_permille: 800`、`resources.mana_cap_permille: 1400`。欄位拿掉 `exclude=True`，進序列化與規則包雜湊。 |
| 敵人 HP ×1.2 | 直接改單位範本 `max_hp`（四捨五入）：bandit 24→29、bandit_archer 26→31、bandit_shieldbearer 20→24。Boss（bandit_warlord、bandit_boss）不動。體質加成不縮放。 |
| 法力費用 ×0.8 | `load_library` 載入並驗證完成後，`apply_ally_mana_cost` 把 **`Ruleset.skills`**（戰鬥結算用）的 `cost.mana` 乘倍率（四捨五入、有費用者至少 1、敵方陣容裝備的技能不縮放）；`Ruleset.with_skills` 加入的生成技能同樣乘。`ContentLibrary.skills`（內容檔原始值）不縮放，預算／閃現／組合器都以原始費用計算。 |
| 法力上限 ×1.4 | `ResourceRules.max_for` 乘 `mana_cap_permille`（只對依屬性算上限的主角與 build 英雄）。 |
| Boss 戰陣容獨立 | 新增護衛範本 `bandit_guard`／`bandit_archer_guard`／`bandit_shieldbearer_guard`（帶 `boss_escort` 標籤，數值預設同一般敵人），`roguelite.yaml` 的 `boss.enemies`、`bandit_lair` 的陣容與第 3 輪援軍改用它們。護衛 HP 改範本檔；護衛傷害用 `boss_escort_damage_permille`（傷害結算依 `boss`／`boss_escort`／其餘分三種）。調一般戰（改 `bandit*` 或 `enemy_damage_permille`）不再連動 Boss 戰。 |
| 模擬覆寫工具 | `sim.difficulty.Difficulty` 語意改成「在 content 值上再乘」（HP 再乘範本值；傷害與上限旋鈕 ＝ content 值 × 旋鈕；費用把已縮放的技能費用再乘一次，兩次四捨五入；`core.ally_mana_cost_permille` ＝ content × 旋鈕，供 `with_skills` 從原始費用縮放）。新增 `escort_hp`、`escort_damage` 旋鈕。NEUTRAL ＝ content 現況。 |

### 取捨說明
- **敵人 HP 為何改範本而不是倍率欄位**：只有三個一般敵人範本，改一處（範本檔）即可；Boss 與護衛分開（護衛有自己的範本）。代價是新增 3 個範本檔（複本）。
- **費用為何縮放在規則包而不在 `library.skills`**：若連 `library.skills` 一起縮放，所有以技能費用算預算的工具（閃現、組合器、`content check`）都會看到偏低的費用而判定超預算（實測 300 多個 skillgen 測試與 `trpg content check` 出錯）。現在的做法與 BAL-4 量測時「生成技能先照原始費用過預算、進規則包才縮放」一致。副作用：`/api/content` 這類直接讀 `library.skills` 的內容瀏覽端點顯示原始費用；戰鬥內的卡片與結算讀 `state.ruleset`，是縮放後的值。
- **未遞增 `LOG_FORMAT`（仍 /90）**：依格式變更文件 1.2，只是新增有預設值的規則包欄位、結算語意在預設值下不變；舊紀錄內嵌的規則包少了新欄位，重播時 `ruleset_hash` 不符會被拒絕並說明，行為與遞增版號一致。若 PM 要遞增，改 `runner.py` 與 `git grep "battle-log/90"` 的測試字面值（8 處）。
- 傷害預覽（`engine/preview.py`）沒有套用敵方傷害倍率（BAL-4 起即如此，倍率只在結算時乘）；影響敵方攻擊的預告數字會偏低約 20%，列入待決。

## 2. 複測

見 `docs/phases/BAL-4/retest.md`（原始 CSV 在 `docs/phases/BAL-4/retest/`）。摘要：一般戰 57.0%／4.5 輪 ✓；Boss 有召喚 33.3%／9.2 輪（勝率 ⚠ 差 1.7 點）；召喚師短缺 15.0% ✓；火焰流短缺 28.9%（記錄）；無召喚 Boss 18.3%（記錄）；一輪 8.3%（60 輪，記錄）。

## 3. 測試調整（沒有為了過測試改規則）

- 寫死數值的改讀 content：`test_con_hp`、`test_effects`、`test_dual_resources`、`test_reactions`、`test_skill_ai_scenarios`、`test_skill_conditions`（邊界測試改明確設偶數 HP）、`test_summon_growth`、`test_skills_content`、`test_start`、`test_stamina_run`；比對「規則包內技能 ＝ 輸入技能」的測試改比對縮放後版本（`test_flash*`、`test_skill_tier_3w9`）。
- AI 軌跡類測試（戰鬥事件出現與否取決於種子）：重新挑種子並在註解標明 BAL-4b——`test_displace_ai`(3→18)、`test_reaction_events_3d3`(3→24)、`test_summon_ai`(6→1)、`test_status_determinism`(10→17)、`test_scene_ai`(4→7、0→1)、`test_event_filter`(2→0)、`test_gamble`(77→20)、`test_self_moves`(2→1)、`test_skill_fuzz`(2→3)、`test_basic_actions_cli`(98→78)、`test_striker_trapper_battle`(49→55)、`test_run_cli`(1→3、6→7)、`test_flash_run`(SEED 6→2)、`test_attribute_respec`／`test_attribute_text_api`(種子 0→1，打得到營火)、`test_run_start_api`(1→5)、`test_run_autosave`(1→0)、`test_flash_economy`(種子增至 8 個)；`test_ai_utility` 場景維持敵方傷害 1000（得分是微調的）。
- CLI 快照：`UPDATE_CLI_SNAPSHOTS=1` 重產，只有 7 個戰鬥輸出雜湊改變（敵人 HP／傷害與法力改變了戰鬥過程）；`skills list`／`show` 雜湊不變。
- 前端夾具：`export_client_fixtures.py` 重產，只有 `unitDolls.json` 多了 3 個 `*_guard` 範本；vitest 1175 通過。

## 4. 驗收

ruff check、ruff format --check、mypy（864 檔）、lint-imports（7 契約）通過；pytest（engine、sim、content、skillgen、roguelite、api、cli，含 slow）全部通過，**唯一例外** `tests/sim/test_completion.py::test_every_map_and_config_completes_…`（見下）；vitest 通過；swamp 種子 7 重播一致。

## 5. 待 PM 決定

1. **完成度檢查有 1 場 draw**：敵方 protect_weakest、oil_depot、種子 0，第 6 輪雙方同歸於盡（新數值下傷害較高）。測試要求 draw ＝ 0 所以紅燈，我沒有改種子或測試。選項：視為合法結果、把 draw 的判定放寬為「雙方同歸於盡不算異常」，或換種子。
2. 傷害預覽是否要乘敵方傷害倍率（目前不乘）。
3. 費用縮放的敵我共用技能：敵方陣容裝備的技能（skill_cleave、skill_gale_kick、skill_fire_arrow、skill_shield_bash）不縮放，若我方 build 也用它們就沒有折扣（沿用 BAL-4 行為）。
4. Boss 有召喚包勝率 33.3%（差 1.7 點）、各圖有 4 張偏離 35–65%（dark_forest 70、frozen_lake 80、narrow_halls 70、open_plain 30）、無召喚 Boss 18.3%、火焰流短缺 28.9%：留給後續批次。
5. 是否要遞增 `LOG_FORMAT` 到 /91（見上）。
