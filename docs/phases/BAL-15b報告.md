# BAL-15b 完成報告｜敵我同一套資源公式（玩法決定 #80）

規格：`docs/phases/PhaseBAL計畫.md` 第 10 節「BAL-15b」。設計：07 7.2「敵我同一套資源公式」（使用者「A 好 寫入」）、06 6.29（召喚物屬性由施放者推得）、#67（姿態／形態維持費不打折）。

## 1. 做了什麼

**引擎與規則（`src/trpg/content/rules.py`、`engine/lifecycle.py`、`engine/skills/targeting.py`）**

- 上限公式對 **所有單位** 生效：`CoreRules.template_max_resource(kind, template, weapon_class, attributes=None)` ＝ 基礎 ＋（屬性最高者 − 10）× 2，法力再 × `mana_cap_permille`（1400）。引擎不再看範本的 `scaled_resources`（欄位保留，讓舊存檔與舊資料照常載入）。
- 基礎：範本有寫 `max_mana`／`stamina` 就用它；沒寫時依武器大類取新欄位 `core.yaml` 的 `resources.class_base`（近戰 20／40、遠程 20／30、法器 40／20，和 `roguelite.yaml` 的 `start.heroes` 同值）。`UnitTemplate.max_mana` 改為 `int | None`（預設 None）。
- 耐力每回合回復 `stamina_regen`（5）對所有單位生效（原本只有主角）。戰後回滿：敵人、隊友每場都是新單位，本來就滿；法力只在營火回滿只對主角有意義（見待 PM 決定 2）。
- 召喚物（含種族的誘餌分身）：`make_unit` 新參數 `resource_attributes`，召喚時傳施放者的屬性（6.29）；基礎依召喚物自己武器的大類。
- 法力費用 ×0.8：`ally_mana_cost_permille` 改名 `mana_cost_permille`、`CoreRules.ally_mana` 改名 `mana_cost`，`skill_mana_cost` 不再看陣營（敵方也打折）。姿態維持費（`pay_stance_upkeep`）與形態維持費（`pay_upkeep`）本來就不經過它，照 #67 不打折（相關測試照舊通過）。
- 顯示：戰鬥中的卡片（`hero_cards`）敵方單位也顯示打折後費用；`/api/builds` 的 `max_mana` 改回報「基礎」（build 英雄沒寫時依武器大類）。
- 一輪：`new_run` 從 build 開局時把基礎寫進主角範本（和戰鬥中的單位同一個來源），所以 run 狀態與戰鬥中的上限一致。

**content**

- 敵人：`bandit_archer`、`bandit_archer_guard`（法力 9）、`bandit_boss`、`bandit_captain`、`bandit_warlord`（14）、`bandit_shieldbearer`、`bandit_shieldbearer_guard`（法力 8、耐力 30）刪掉固定值，改由公式算。隊友與召喚物本來就沒寫（照舊固定法力 0、耐力 30），現在由公式算。
- 模擬 build（`content/sim/builds.yaml`）：48 個英雄的 `max_mana` 全部刪掉（原本 20／24／30／40 不等、耐力一律 30），對齊一輪主角的武器大類基礎。
- `sim_duelist`（示範反擊者，不屬於敵人、隊友、召喚物）：拿掉預設格擋（見第 4 節與待 PM 決定 3）。
- 示範與測試單位（`hero_*`、`gear_tester*`、`variant_*`、`sim_duelist`、`training_dummy`）的明寫值保留當「基礎」，同樣再加屬性加成與 ×1.4（最保守：不在規格範圍內的單位不改資料）。

**數值前後對照（上限；新值依各範本屬性）**

| 單位 | 法力 | 耐力 |
|---|---|---|
| 盜賊、盜賊護衛、標準敵人 t1～t5 | 0 → 28 | 30 → 48 |
| 盜賊弓手（含護衛） | 9 → 34 | 30 → 38 |
| 盜賊頭目 | 14 → 34 | 30 → 52 |
| 盜賊隊長 | 14 → 28 | 30 → 48 |
| `bandit_warlord` | 14 → 39 | 30 → 56 |
| 盜賊盾衛（含護衛） | 8 → 28 | 30 → 48 |
| 標準隊友（戰士／弓手） | 0 → 28／34 | 30 → 52／42 |
| 召喚物（施放者屬性全 10 時；近戰／法器武器） | 0 → 28／56 | 30 → 40／20 |
| 木樁 | 0 → 28 | 0 → 0 |
| 以上全部 | — | 每回合 +0 → +5 |

（屬性加成依施放者，召喚物實際值隨施放者屬性升高；法器武器的召喚物耐力反而從 30 降到 20 起跳。）

## 2. `LOG_FORMAT` 與存檔

- `LOG_FORMAT` `/94` → **`/95`**（結算結果與規則包結構都改變）：`runner.py` 文件字串、`docs/phases/戰鬥紀錄格式變更.md` 加一條、所有測試字面值（含 `tests/roguelite/fixtures/flash_history_3wr1.json`）已更新。
- 存檔版本 **不變**（`trpg-run/13`）：存檔結構沒變；進行中的戰鬥照慣例在引擎版號不同時丟掉並提示。

## 3. 量測（`scripts/bal15a_resources.py measure --variants base --builds named --normal-seeds 6 --boss-seeds 30 --chain-seeds 0 --jobs 6`，286 秒）

產出：`docs/phases/BAL-15/15b_base_full.md`（27 build）、`15b_b14_builds.md`（BAL-15a B14 的 8 個 build）。

| 指標 | BAL-15a 現況 | BAL-15a 預測（b14=all） | BAL-15b 實作後 |
|---|---|---|---|
| 27 build 一般戰 勝率／輪數 | 62.1%／5.06 | — | 61.9%／5.14 |
| 27 build Boss 勝率／輪數 | 37.5%／8.02 | — | 35.7%／7.67 |
| 27 build 敵方技能次數／場（一般／Boss） | 1.30／3.24 | — | 1.49／4.20 |
| 8 build 一般戰 勝率／輪數 | 64.4%／5.09 | 66.7%／5.15 | 66.2%／5.14 |
| 8 build Boss 勝率／輪數 | 38.3%／8.25 | 37.1%／7.77 | 35.8%／7.81 |
| 8 build 敵方技能次數／場（一般／Boss） | 1.30／3.30 | 1.48／4.50 | 1.50／**4.51** |

- 和 BAL-15a 的預測一致：Boss 戰敵方技能次數 3.3 → 4.5（+37%），勝率變化在雜訊內（Boss n=240～810 約 ±4～6 點），Boss 輪數仍在 6～10。
- 27 build 合計的 Boss 法力短缺 9.2 → 7.6%（輪數變短、build 英雄基礎對齊；BAL-15a 的 `classbase` 量測顯示對齊本身影響很小）；tank 仍 20.3%、support 28.9%、healer 24.2%、guardian 22.8% 超過 20%（BAL-15a 已知，`mana_cap_permille` 玩法 PM 決定維持 1400）。
- 敵方目前沒有花法力的技能，所以「敵方法力也打折」在數字上沒有作用。

## 4. 快照與測試變動

- **CLI 輸出快照**：9 筆中 7 筆重產（`battle_bridge_guardian_11`、`battle_default_flat_42`、`battle_frozen_lake_push_3`、`battle_halls_storm_9`、`battle_oil_depot_fire_7`、`battle_open_plain_trapper_7`、`battle_swamp_striker_5`）；原因：敵我上限與回復改變，戰局改變。
- **行為快照 `refactor_3wr2.json`**、**client fixture**（`tests/api/test_client_fixtures.py`）：沒有變（測試照舊通過）。
- **重挑種子**（斷言不改）：`test_commander_cli` swamp 3 → 0；`test_striker_trapper_battle` striker 55 → 35。
- **`test_guardian_battle`（還擊）**：種子 0～599 都找不到「還擊」觸發——耐力上限 52 ＋每回合 5 後，預設格擋（耐力 20 以下才停）在傷害前就用掉本輪唯一的反應，還擊永遠輪不到。比照拳套反擊把預設格擋關掉的既有做法，示範單位 `sim_duelist` 改寫反應規則（只留藉機攻擊），種子 16 不變、斷言不變。
- **寫死數值改讀 content／公式**：`test_dual_resources`（新增「其他單位同公式」「沒寫基礎時依武器大類」，耐力回復改為所有單位）、`test_reactions`（格擋後耐力、門檻）、`test_skill_primitives`、`test_skill_scenarios`、`test_passive_triggers`、`test_skill_ai_scenarios`、`test_negative_statuses`（法力 99 改讀實際上限，情境要的「目前法力」直接設在單位上）、`test_demo_maps`（面板法力／耐力讀公式）、`tests/api` 的 builds `max_mana`、`tests/roguelite/test_start`。
- **規則改變的測試**：`test_ally_mana_cost_bal4c`（敵方原價 → 敵我都打折）、`test_ally_mana_display_bal4c`（敵方卡片也顯示打折後）——依 #80 改斷言。

## 5. 檢查

ruff check、ruff format --check、mypy、lint-imports 通過；相關 pytest：`tests/engine`、`tests/content`、`tests/roguelite`、`tests/sim`、`tests/api`、`tests/narrative`、`tests/skillgen`、`tests/test_architecture.py`、`tests/cli`（含 slow）全部通過；重播 `trpg battle --map swamp --seed 7` → `battle replay` 驗證通過。未跑完整 `scripts/check.py`（照守則由 PM 跑）。

## 6. 待 PM 決定

1. **規則（反應）**：耐力上限變大（主角、隊友、敵人約 48～56）且每回合 +5 後，預設格擋（每次 10、耐力 20 以下才停）幾乎永遠先用掉本輪唯一的反應，**反擊類反應技（`hit_by_melee`／`hit_by_attack`，例如「還擊」）幾乎不會觸發**。BAL-15b 只把示範單位 `sim_duelist` 的格擋拿掉讓測試能跑；玩家或 build 帶反應技時要不要比照拳套「帶反擊技就自動關預設格擋」，需玩法 PM 決定。
2. **規則**：隊友與敵人每場都是新單位，所以「法力只在營火回滿」實際上等於每場滿法力；若之後隊友跨場延續狀態再處理（目前沒有隊友跨場狀態，最保守不做）。
3. **原型數值**：示範與測試單位（`hero_*`、`variant_*`、`gear_tester*`、`sim_duelist`）的明寫法力保留當基礎（例如 `hero_archer` 24，和遠程大類 20 不同）；要不要也刪掉改依武器大類。
4. **原型數值**：召喚物的基礎依「召喚物自己武器」的大類（靈類是法器 → 耐力基礎 20，比原本固定 30 低）；要不要改依施放者的武器大類。召喚物目前沒有技能，只影響格擋。
5. **相容**：舊的 build 開局存檔（主角範本沒寫耐力）在一輪狀態裡仍以 `default_stamina` 30 當基礎，戰鬥中則依武器大類；只影響舊存檔，未做遷移（存檔版本不變）。
6. 欄位改名 `ally_mana_cost_permille` → `mana_cost_permille`（content 與 `CoreRules`）；`scripts/bal15a_resources.py` 的 `mcost`／`b14`／`classbase` 覆寫在新 content 下無作用或已是現況（腳本仍可跑）。

## BAL-15c｜BAL-15b 收尾（玩法決定 #83、#84）

規格：`docs/phases/PhaseBAL計畫.md` 第 10 節「BAL-15c」「BAL-15c 追加」。設計：05 5.2.1（#83）、07 7.2（#80、#84）。

### 做了什麼

1. **AI 單位帶反應技不放預設格擋**、4. **玩家角色也一樣（#83）**：`engine/lifecycle.py` 的 `make_unit`——範本沒寫反應規則（用預設規則）而裝了反應技（`kind: reaction`）時，預設格擋改成 `off`（新函式 `default_block_off`、`has_reaction_skill`；拳套反擊的既有做法改呼叫同一個函式）。敵人、隊友、召喚物、主角一律適用。範本有手寫反應規則的（盜賊盾衛等）不動。`sim_duelist` 拿掉 BAL-15b 手寫的反應規則，改回預設規則由引擎處理（結果相同）。
   - 玩家改回格擋優先：既有的反應設定面板（`client/src/ui/ReactionPanel.tsx`）每條規則已有「自動／詢問／關閉」，格擋規則仍列在面板上（模式為關閉），切回「自動」即可；格擋在傷害前結算，所以切回後就是格擋優先。**前端不需改動**（未改 client，未跑 vitest／build）。新增測試 `tests/engine/test_reaction_defaults_bal15c.py` 驗證切回後格擋先用掉反應、還擊不觸發。
2. **示範／測試單位法力依武器大類**：`hero_archer`、`hero_fighter`、`hero_mage`、`hero_stormcaller`、`variant_slinger`／`tidecaller`／`vanguard`、`gear_tester`、`_g2`、`_g3a`、`_g3b`、`_g3b_sentinel`、`sim_duelist` 刪掉 `max_mana`（耐力本來就沒寫）。實際數值只有弓類（`hero_archer`、`variant_slinger`、`gear_tester_g3b_sentinel`）基礎 24 → 20，其他和大類相同。需要特定法力的測試原本就在 fixture 寫 `max_mana=99` 等覆寫，不需新增。`training_dummy` 的耐力 0 是木樁特性，保留。
3. **一輪狀態的耐力基礎對齊**：新的一輪（build 開局、武器＋關鍵字開局）本來就把基礎寫進主角範本；只有 BAL-15b 以前的 build 開局存檔沒寫。`roguelite/save.py` 新增 `fill_resource_base`，`upgrade_save`（API 與 CLI 讀檔時都會呼叫）依武器大類補上法力／耐力基礎，一輪狀態的上限從此和戰鬥中一致。存檔結構沒變，**存檔版本不變**（`trpg-run/13`）；目前法力／耐力值不動（戰鬥開場本來就會降到戰鬥中的上限）。
5. **#84 確認**：程式與 07 7.2 一致——敵人、隊友、召喚物由 `make_unit` 建立時法力＝上限；只有主角的出場設定帶一輪的目前法力。加回歸測試（`tests/roguelite/test_resources_bal15c.py`：主角法力 0 開戰仍是 0，其他單位全滿；`test_reaction_defaults_bal15c.py`：召喚物開場滿）。行為未改。

另：`scripts/bal15a_resources.py` 每個樣本多記英雄的格擋、還擊類（`hit_by_melee`／`hit_by_attack`／`hit_by_spell` 的反應技與拳套反擊）、反應技次數；新覆寫 `blockon`（重現 #83 之前）與 `riposte`（近戰 build 英雄的反應技換成「還擊」）。

### 量測（`measure --builds named --chain-seeds 0 --jobs 6`）

**現況 vs. 改動前**（`--variants base,blockon --normal-seeds 6 --boss-seeds 30`，535 秒；27 build，一般 n=1620、Boss n=810）

| 指標 | 改動前（blockon） | BAL-15c |
|---|---|---|
| 27 build 一般戰勝率／輪數 | 61.9%／5.14 | 60.4%／5.12 |
| 27 build Boss 勝率／輪數 | 35.7%／7.67 | 35.8%／7.58 |
| 帶反應技的 8 build 一般戰勝率（n=480） | 52.1% | 47.7% |
| 帶反應技的 8 build Boss 勝率（n=240） | 15.8% | 16.2% |
| 8 build 英雄格擋／場（一般） | 1.06 | 0 |
| 8 build 反應技觸發／場（一般／Boss） | 0.69／0.69 | 0.84／0.84 |
| 還擊類觸發總數（一般／Boss；只有 `build_support` 的反射護幕） | 122／58 | 184／82 |

（改動前一欄與 BAL-15b 報告的 61.9%／35.7% 相同，量測可重現。）整體勝率在雜訊內（一般 ±2.4、Boss ±3.4 點）；帶反應技的 build 一般戰 −4.4 點，約 1.9 個標準誤，接近但未超出雜訊。

**還擊**（`--variants riposte,riposte+blockon --normal-seeds 3 --boss-seeds 10`，241 秒；7 個近戰 build 換上「還擊」）

| 指標 | 格擋優先（舊預設） | 反應技優先（BAL-15c） |
|---|---|---|
| 「還擊」觸發／場（一般，n≈235） | 0.46 | **1.51** |
| 「還擊」觸發／場（Boss，n=79） | 0.59 | **1.51** |
| 近戰 build 一般戰勝率 | 41.3% | 45.8% |
| 近戰 build Boss 勝率 | 20.3% | 12.7% |

還擊有觸發（每場約 1.5 次，是舊預設的 2.5～3 倍）。Boss 戰近戰 build 勝率下降 7.6 點（n=79，約 1.6 個標準誤）。

### 快照、版本與測試變動

- **`LOG_FORMAT` `/95` → `/96`**：`runner.py` 文件字串、`docs/phases/戰鬥紀錄格式變更.md` 加一條、所有測試字面值（含 `tests/roguelite/fixtures/flash_history_3wr1.json`、`endswith("/95")` 三處）。
- **存檔版本不變**（`trpg-run/13`）。
- **CLI 輸出快照**：9 筆中 3 筆重產（`battle_bridge_guardian_11`、`battle_default_flat_42`、`battle_frozen_lake_push_3`）。
- **行為快照 `refactor_3wr2.json`、client fixture**：沒有變。
- **重挑種子**（斷言不改）：`test_displace_ai` 虛空互換 18 → 17；`test_gamble` 30 → 20；`test_reaction_events_3d3` build_tank／swamp 0 → 1；`test_scene_ai` 推倒石柱 1 → 2；`test_skill_shaping` build_tank 0 → 1（參數化多加種子欄，build_healer 仍為 0）。

### 檢查

ruff check、ruff format --check、mypy、lint-imports 通過；相關 pytest：`tests/engine`、`tests/content`、`tests/roguelite`、`tests/test_architecture.py`、`tests/sim`、`tests/api`、`tests/narrative`、`tests/skillgen`、`tests/cli`（含 slow）全部通過；重播 `trpg battle --map swamp --seed 7` → `battle replay` 驗證通過。未跑完整 `scripts/check.py`。

### 待 PM 決定

1. **規則範圍（#83）**：目前「反應技」指所有 `kind: reaction` 的技能（包括不和格擋搶時機的斷後斬、迎頭痛擊、悲憤、掩護射擊、挺身而出等）；照字面做。若只想針對「被打時」的還擊類（`hit_by_*`），需玩法 PM 決定。
2. **手寫反應規則的單位**：範本有寫反應規則（如盜賊盾衛）時不套用 #83（最保守）；目前沒有這種單位帶反應技。
3. **平衡**：還擊在 Boss 戰的近戰 build 勝率 20.3% → 12.7%（樣本小，n=79）；帶反應技的 8 build 一般戰 52.1% → 47.7%。是否需要補償（例如格擋與反應技分開計次）待玩法 PM。
4. **反應設定不跨場保存**：玩家改回格擋優先只在當場有效（和拳套反擊既有行為相同），下一場又回到反應技優先；要不要存進一輪狀態待決（會改存檔結構）。
5. **舊存檔目前資源值**：`fill_resource_base` 只補基礎，不調整存檔裡的目前法力／耐力（戰鬥開場會降到上限；法器主角的耐力上限變低、近戰變高，營火回滿後一致）。
