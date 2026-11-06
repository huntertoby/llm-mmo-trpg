# Phase 3-33b 報告｜召喚物基本規則＋Boss 對策

> 規格：`docs/phases/Phase3計畫.md` 36.2；設計：`docs/design/06-技能.md` 6.29.1、6.29.7。基線：`Phase3-33a報告.md`。數值都是初值（放 `content/rules/core.yaml`、`content/ai_profiles.yaml`），**沒有調任何既有數值**。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| 數值成長 | 召喚當下依施放者等級 `L` 與召喚技能的縮放屬性修正 `M`（`(有效屬性−10)÷2`，下限 0）快照：最大 HP ＋ `2(L−1)+1·M`、普攻固定傷害 ＋ `(250(L−1)+250·M)÷1000`、傷害加成 `10‰(L−1)+10‰·M`；之後不隨施放者變化。係數在 `core.yaml` 的 `summon_growth` | `engine/summons.py`（`growth_of`）、`content/rules.py`（`SummonGrowth`） |
| 角色等級 | 引擎原本沒有等級：`UnitTemplate.level`（預設 1）→ `UnitState.level`；一輪的主角由 `hero_spawn` 帶入 `run.level` | `content/battle.py`、`engine/state.py`、`roguelite/progress.py` |
| 灌注關鍵字 | `UseSkill.infusion`（選填）；可選＝施放者裝備技能製造或利用的關鍵字 ∩ `core.yaml` 的 `summon_infusions` 對照表（目前 `ignite→burning`、`frozen→slow`、`marked→marked`、`collision→震退 1 格`）；省略取第一個；不合法（沒持有、沒對應、非召喚技能）拋 `IllegalActionError`；召喚物記下 `infusion`，普攻命中後附加（`weapon_traits.apply_hit_traits`）；`unit_summoned` 事件多了 `max_hp`、`infusion` | `engine/infusion.py`（新）、`engine/skills/targeting.py`（`compute_area` 檢查） |
| 上限 | `summon_limit_per_owner: 2`（照舊，最舊的先消失）、`summon_hard_cap: 3`（載入時驗證 limit ≤ 硬上限，執行時 `summon_limit()` 再取 `min`）、`summon_max_duration: 4`（技能 `duration` 超過以此為準；現有技能 2～3，目前無影響） | `engine/summons.py`、`content/rules.py`、`core.yaml` |
| 加成上限 | `modifiers.summon_damage_bonus`：施放者自己的正向傷害加成（修正規則、裝備、技能強化、關鍵字強化）先占用全身 +50%，召喚物成長加成只能用掉剩下的空間；已頂到上限時召喚物加成為 0 | `engine/modifiers.py` |
| Boss ×2 | `core.boss_summon_damage_permille: 2000`：`boss` 標籤單位對敵方召喚物造成的所有帶 `source_id` 的傷害（普攻、技能、範圍、區域）×2；`damage_dealt` 的 `multiplier_permille` 含此倍率 | `engine/effects/handlers.py` |
| Boss AI | 擋在 Boss 與敵方非召喚物單位之間的召喚物（距離和 ≤ 直線距離 ＋ `boss_blocker_slack`＝1）：預覽事件會打到它時每隻加 `boss_blocker_points`＝60 × 命中折合（範圍技能順帶打到也算）；不是 Boss 不加分 | `engine/ai/summon.py`、`ai/utility.py`、`ai_profiles.yaml` |
| AI 挑灌注 | 召喚技能的最終動作補 `infusion`：近戰召喚物偏好 `roles: [melee]` 的（碰撞）、遠程偏好 `ranged`（點燃…），沒有符合取第一個 | `engine/ai/utility.py`（`_with_infusion`） |
| 介面 | 召喚技能目標選好後，施放者有 2 個以上可選關鍵字時多一步 `InfusionDialog`（沿用 `DialogFrame`，Esc／取消＝不施放）；只有 1 個時直接用預設；`UnitView` 多 `infusion_options`（自己陣營的施放者）與 `infusion`；單位資訊顯示召喚物灌注 | `client/src/battle/infusion.ts`、`ui/InfusionDialog.tsx`、`screens/BattleScreen.tsx` |
| 模擬 | `dev_starters.yaml` 加 `dev_summoner`（圖騰杖＋元素之靈＋火焰箭）、`dev_summoner_bone`（骷髏戰士＋火焰箭），保證起始帶召喚技；`sim_summons.py` 預設納入、新增 `--maps boss`（一輪的 Boss 戰） | `content/dev_starters.yaml`、`sim/summon_report.py` |
| 格式 | `LOG_FORMAT` `/47 → /48`（PM 合併時定號）；一輪存檔格式不變（等級由 `run.level` 在戰鬥設定時帶入） | `engine/runner.py` |

## 2. 驗收證據

| 驗收項 | 證據 |
|---|---|
| 成長公式依等級／屬性 | `tests/engine/test_summon_growth.py`：`test_growth_follows_the_owner_level`、`test_growth_follows_the_scaling_attribute`（其他屬性不影響）、`test_growth_values_are_integers_from_core_rules` |
| 快照不隨施放者之後變化 | `test_growth_is_a_snapshot_taken_when_summoned`（施放者升級、屬性變動後，已召喚的不變；再召喚才用新值） |
| 灌注效果與不可選 | `test_infusion_options_are_held_keywords_with_a_mapping`、`..._defaults_to_the_first_option`、`test_an_unavailable_infusion_is_illegal`（沒持有／沒對應／不存在）、`test_only_summon_skills_take_an_infusion`、`test_infused_attack_applies_the_mapped_status`（燃燒）、`test_collision_infusion_knocks_the_target_back`、`test_ai_picks_the_infusion_by_the_summon_role`、`test_every_infusion_mapping_names_a_real_status` |
| 2 隻／4 輪／3 隻硬上限 | `test_default_limits_...`、`test_two_at_once_and_the_oldest_disappears`、`test_the_limit_never_exceeds_the_hard_cap`（含 4 > 硬上限被驗證擋下）、`test_three_summons_fit_when_the_limit_is_raised_to_the_hard_cap`、`test_duration_is_capped_at_four_rounds` |
| +50% 上限含召喚物 | `test_summon_bonus_counts_toward_the_owners_cap`（無其他來源／施放者占 300／施放者已頂到上限三種）、`test_summon_bonus_never_pushes_total_damage_past_the_cap`（Lv99 成長也不超過 +50%） |
| Boss ×2 | `test_boss_deals_double_damage_to_summons`、`test_boss_double_damage_only_applies_to_summons`（打施放者不加倍）、`test_area_skills_also_hurt_summons_in_the_area` |
| Boss AI 先打擋路召喚物 | `test_blocking_summons_lie_between_the_boss_and_the_hero`、`test_boss_ai_scores_hits_on_a_blocking_summon_higher`（開／關加分比較）、`test_non_boss_units_get_no_blocker_bonus`、`test_boss_ai_actually_attacks_the_blocking_summon` |
| 同種子確定、重播一致 | `test_same_seed_and_inputs_give_the_same_summon`；`tests/sim/test_summon_report.py::test_a_summoner_battle_with_growth_and_infusion_replays_identically`（Boss 戰，`replay` 終局與原跑逐位元一致）；既有 `test_24c` 重播、`tests/cli` 的 `--log-json` ＋ `replay` 測試全過（`LOG_FORMAT` 斷言與 CLI 快照已更新） |
| 前端 | `infusion.test.ts` 6 個測試；`vitest` 全部 701 個通過；`tsc --noEmit`、`pnpm build` 成功；OpenAPI 與 `schema.d.ts` 已重產 |
| 全量 | `uv run python scripts/check.py`：見第 7 節 |

被迫改的既有測試：`test_heal_summon_modifiers.py`、`test_summons.py` 的召喚物 HP 期望值（施放者智力 16 的成長 ＋3：20→23）、`test_keyword_start.py`（起始包 12→14，指定技能的對照包不比對「同一般開局的主角」）、8 個 `LOG_FORMAT` 斷言、CLI 快照雜湊（只有 `battle_open_plain_trapper_7` 變；因 `/48`）。

### 2.1 浮動卡規則（6.5.1）與瀏覽器實測

`InfusionDialog` 用既有的 `DialogFrame`（戰鬥詢問視窗外框，與複製技能、第二段選目標同一類），不是滑過觸發的浮動卡，選項說明直接寫在按鈕旁，**沒有新增彈出層**，所以 6.5.1 的「滑進卡片、捲到底、釘住、關閉」不適用。**未能在瀏覽器實測整條流程**：瀏覽器窗格的畫布點擊沒有觸發動作（試了 `left_click`、先 `hover`、JS 派送 pointer 事件都沒反應，預覽請求也沒送出；窗格內固定的預覽伺服器是另一份程式碼，已改用自己的伺服器在 8765 埠確認新起始包出現）。流程靠單元測試與型別檢查把關，建議 PM 驗收時用開發者起始包「喚靈（保證召喚）」手動試一次（該包只有 1 個可選關鍵字不會跳視窗；要看到視窗需帶 2 個以上有對應的關鍵字，例如帶「死亡迴旋」的施放者）。

## 3. 「3-33a 基線 vs 3-33b」對照

### 3.1 同一組態（4 包 × 5 圖 × 4 種子，與 3-33a 完全相同的指令）

| 起始包 | 勝率 | 主角 DPR | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 平均存活輪數 | 平均行動回合 |
|---|---|---|---|---|---|---|---|
| 喚靈：3-33a | 60% | 7.9 | 2 | 1.4% | 0.60 | 0.8 | 1.1 |
| 喚靈：3-33b | 60% | 7.1 | 2 | 1.8% | 0.60 | 0.9 | 1.2 |
| 鐵壁／烈焰／鷹眼 | 與 3-33a 完全相同（50%／55%／60%；DPR 5.7／8.5／10.2） | | 0 | 0% | 0 | — | — |

主角 Lv1、智力 16 的成長只有 HP ＋3、固定傷害 ＋0（250×3÷1000），所以對舊喚靈包幾乎沒差；0.60 次／場與 9/20 場有召喚不變（仍有種子抽不到召喚技）。

### 3.2 放大樣本（6 包 × 5 圖 × 8 種子，每包 40 場）

| 起始包 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 有召喚場數 | 平均存活輪數 | 平均行動回合 |
|---|---|---|---|---|---|---|---|---|---|---|
| 喚靈 dev_spirit（抽技能） | 57% | 4.9 | 7.7 | 118 | 5 | 4.5% | 0.60 | 19 | 0.9 | 1.4 |
| **喚靈（保證召喚）dev_summoner** | 65% | 4.5 | 8.8 | 118 | 14 | **12.1%** | 0.62 | 24 | 1.4 | 1.8 |
| **喚靈（骷髏）dev_summoner_bone** | 75% | 4.5 | 7.7 | 118 | 5 | 4.6% | 0.80 | 24 | 0.7 | 1.3 |
| 鐵壁 dev_bulwark | 60% | 5.4 | 5.9 | 120 | 0 | 0% | 0 | 0 | — | — |
| 烈焰 dev_blaze | 65% | 4.5 | 8.7 | 114 | 0 | 0% | 0 | 0 | — | — |
| 鷹眼 dev_hawkeye | 62% | 4.8 | 9.5 | 120 | 0 | 0% | 0 | 0 | — | — |

召喚物結束原因：dev_summoner 共 25 隻（被打倒 7、到期 2、召喚者離場 2、戰鬥結束仍在 14）；dev_summoner_bone 共 32 隻（被打倒 17、到期 4、仍在 11）。

### 3.3 Boss 戰（`--maps boss`，一輪的 Boss 地圖與加強版頭目，6 包 × 8 種子；主角 Lv1）

| 起始包 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 平均存活輪數 |
|---|---|---|---|---|---|---|---|---|
| dev_spirit | 50% | 10.4 | 5.8 | 192 | 10 | 5.0% | 0.88 | 1.1 |
| dev_summoner | 75% | 10.4 | 6.4 | 229 | 34 | 14.8% | 1.38 | 1.6 |
| dev_summoner_bone | 37% | 17.9 | 5.7 | 179 | 17 | 9.3% | 3.00 | 0.6 |
| dev_bulwark | 0% | 6.0 | 5.2 | 100 | 0 | 0% | 0 | — |
| dev_blaze | 12% | 6.9 | 8.9 | 147 | 0 | 0% | 0 | — |
| dev_hawkeye | 12% | 9.2 | 12.4 | 174 | 0 | 0% | 0 | — |

骷髏戰士在 Boss 戰 24 隻中 21 隻被打倒、平均只活 0.6 輪（Boss ×2 ＋ 優先清擋路）；但召喚流在 Boss 戰的勝率反而高於無召喚的對照包（每包只有 8 場，主角 Lv1，結論有限）。

### 3.4 check.py

見第 7 節。

## 4. 觀察

1. 保證帶召喚技的包（元素之靈）召喚物貢獻升到 12%（一般地圖）與 15%（Boss），仍遠低於「約等於普攻流」的目標（普攻為主的鐵壁主角 DPR 5.9）；但此時主角還是 Lv1、召喚物平均只活 1.4 輪。成長的效果要等主角升級後才顯現（模擬沒有跑多場一輪）。
2. 骷髏戰士（近戰、HP 較低）一般地圖存活 0.7 輪、Boss 戰 0.6 輪：短命是近戰召喚物的現況，不是 Boss ×2 單獨造成（一般地圖也一樣）。
3. Boss 戰中召喚流勝率較高，推測是召喚物吸收了 Boss 與隊友的攻擊；「優先清擋路召喚物」讓 Boss 把行動花在召喚物上。未做 Boss ×1 對照，無法分離各規則的貢獻。
4. 同時 2 隻的上限在實戰仍很少用到（每場 0.6～0.8 次召喚，冷卻 4 回合）。

## 5. 待 PM 決定

1. **數值初值**：成長（HP ＋2／級 ＋1／屬性修正；固定傷害 ＋0.25／級與修正；傷害加成 10‰／級與修正）、Boss 加分 60 點與距離寬限 1 都沒經過模擬調整。Lv1、智力 16 的主角現在就拿到 ＋3 HP（既有測試的期望值因此改了）；若希望 Lv1 完全不變，把 `hp_per_attr_mod` 設 0 即可。
2. **等級進引擎**：新增 `UnitTemplate.level`／`UnitState.level`（預設 1，非主角都是 1），主角由 `hero_spawn` 帶入 `run.level`；一輪存檔不變。`LOG_FORMAT` 我定 `/48`，合併時請依實際順序改。
3. **+50% 上限的算法**：召喚物成長加成只用施放者「剩下」的空間（施放者自己的裝備／修正／關鍵字強化先占），而且不繼承施放者的加成。若 PM 想讓召喚物同時吃施放者的加成請說（那樣會讓裝備傷害詞條對召喚流過強）。
4. **灌注對照表只有 4 個**（點燃、冰凍→緩速、標記、撞擊→震退）：潮濕、帶電、倒地、高處、隱蔽、召喚物沒有合適的現成狀態，沒有對應所以不可選。可選關鍵字＝施放者裝備技能「製造或利用」的關鍵字（含利用）；介面只在可選 ≥ 2 個時才問，1 個時自動用預設，要不要「只有 1 個也問／可選不灌注」請決定。`on_downed_spawn` 分身一律取預設。
5. **AI 估值未納入成長與灌注**：`summon_dpr` 仍用範本武器；Boss 的擋路判定是曼哈頓距離近似（不跑尋路），也沒有改 Boss 的移動目標。
6. **`summon_max_duration: 4` 目前不影響任何技能**（現有召喚技 2～3 輪）；硬上限 3 目前只在把 `summon_limit_per_owner` 設高時才有作用（3-33f 專精會用）。
7. **模擬限制**：主角固定 Lv1，未驗證成長；沒有 Boss ×1 對照；`dev_summoner*` 兩個包指定了起始技能，所以不再滿足「起始包 ＝ 一般開局同樣的主角」（測試已對有 `skills` 的包放寬）。dev 起始包現在 14 個，開發者選單會多兩項。
8. **瀏覽器實測缺口**：灌注選擇視窗沒有在瀏覽器完整走過（見 2.1），請 PM 驗收時手動抽查一次。

## 6. noqa

沒有新增複雜度類（`C901`／`PLR*`）的 `noqa`。測試內有數處 `PLC0415`（函式內 import，沿用 `test_24c.py` 的作法）。

## 7. 最終檢查

`uv run python scripts/check.py` 跑了一次：ruff、format、mypy、lint-imports、client typecheck、client test（701）全過；pytest 4320 通過、1 個失敗——`tests/api/test_run_start_api.py::test_dev_packs_endpoint_and_start` 仍寫死起始包 12 個（新增 2 個對照包後為 14）。已改成 14，單檔重跑通過（沒有再重跑全量）。另外 `pnpm build` 成功、`--log-json`／`replay` 一致由重播測試與既有 CLI 測試涵蓋。
