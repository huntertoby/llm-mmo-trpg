# BAL-19e 報告：反應與姿態（玩法決定 #110，缺口 3）

規格：`docs/phases/PhaseBAL計畫.md` 第 12 節 BAL-19e；設計 `docs/design/06-技能.md` 6.27.4（反應補 8、姿態感知／意志各 2、閃現反應／姿態模板各補到約 10 種）、6.34.4（小變化類別與預算）。數值都是初值，未經模擬。

## 1. 新增技能（12 招，一招一檔 `content/skills/`）

反應（`skill_rx_*`，全部 1 階、稀有、反應係數 600‰）：

| ID | 名稱 | 屬性 | 類別 | 觸發事件 | 效果 | 費用 | 預算比例 |
|---|---|---|---|---|---|---|---|
| skill_rx_spell_ward | 驅咒聖盾 | 感知 | 法術（法器） | hit_by_spell | 自身護盾 2d6 | 法力 3、冷卻 1 | 78.2% |
| skill_rx_warning_mark | 示警標記 | 感知 | 法術 | ally_targeted | 攻擊者標記 2 回合＋神聖 1d6（射程 5） | 法力 2、冷卻 1 | 88.4% |
| skill_rx_vigil_prayer | 守夜禱言 | 感知 | 法術 | ally_downed | 自身治療 2d6 | 法力 3、冷卻 2 | 74.7% |
| skill_rx_dread_glare | 威懾凝視 | 意志 | 法術 | enemy_enters_adjacent | 恐懼 2 回合＋暗影 1d6 | 法力 3、冷卻 2 | 77.1% |
| skill_rx_shadow_grasp | 影縛 | 意志 | 法術（法器） | enemy_leaves_adjacent | 暗影 2d4＋減速 2（射程 3） | 法力 3、冷卻 1 | 85.0% |
| skill_rx_frost_backlash | 霜甲反噬 | 智力 | 法術（法器） | hit_by_melee | 冰霜 2d4＋減速 2（射程 1） | 法力 3、冷卻 1 | 76.0% |
| skill_rx_point_blank | 抵近射擊 | 敏捷 | 武器（遠程） | enemy_enters_adjacent | 武器 900‰＋推 1 | 冷卻 1 | 80.0% |
| skill_rx_slip_away | 滑步脫身 | 敏捷 | 法術（身體類，不需武器） | hit_by_attack | 自身隱蔽 2＋加速 3 | 冷卻 1 | 85.0% |

- 8 種觸發事件用了 7 種（每種最多 2 招）；只有 3 招是對攻擊者出手的「還擊」型，其餘是護盾、治療、標記、恐懼、脫身。
- 感知 3、意志 2，都是法術反應。

姿態（`skill_st_*`，用現有的姿態狀態，沒有新增狀態；法術、不需武器、2 階，姿態本來就要角色 2 階）：

| ID | 名稱 | 屬性 | 姿態狀態 | 維持費 | 預算比例 |
|---|---|---|---|---|---|
| skill_st_dawn_vigil | 晨禱架勢 | 感知 | stance_holy_1（聖光架勢·壹） | 0 | 83.3% |
| skill_st_warden_watch | 守望姿態 | 感知 | stance_guard（堅守姿態） | 0 | 77.8% |
| skill_st_umbral_pact | 幽影架勢 | 意志 | stance_shadow_1（暗影架勢·壹） | 0 | 83.3% |
| skill_st_unbroken_will | 不屈心志 | 意志 | stance_ironwall（鐵壁姿態） | 1 | 83.3% |

- 現有姿態的來源：手寫 12 招（狂怒、堅壁＋10 個變身），白板配方 6 個（感知／意志 0）。本段補手寫姿態，白板配方沒動。
- 不屈心志是防守姿態，沒有主題訊號（照 6.10 會落在身體類），`content/skill_scaling.yaml` 加一條 override（意志，附理由）。
- 每招 `trpg skills budget` 合格；`trpg content check`：合併 19d 後 370 個技能通過預算與結構驗證。
- `tests/content/test_coverage.py`：`_BAL19_PREFIXES` 加 `skill_rx_`、`skill_st_`（與 19d 的 `skill_rng_` 合併）；`stance_guard`、`stance_ironwall`、`stance_holy_1`、`stance_shadow_1` 從「沒有手寫技能」清單拿掉。內建技能數 358 → 370。
- 新測試 `tests/content/test_bal19e_reactions_stances.py`：事件分散、感知／意志數量、驗證與預算；引擎裡實際觸發（驅咒聖盾在法術傷害前上盾、霜甲反噬打到近戰攻擊者、滑步脫身上隱蔽與加速）。

## 2. 閃現小變化模板（要改程式）

| 模板 | 種類 | 類別 | op | 內容 |
|---|---|---|---|---|
| stance_enter_heavy 沉勢 | 姿態 | 費用 | stance_enter_heavy（新） | 進入代價（法力或耐力）+1，本體提高一級；維持費不動、變身姿態不出（`stance_enter_light` 的反向） |
| stance_ward 護體 | 姿態 | 修正 | self_rider（新） | 進入時多一層護盾 |
| stance_mend 調息 | 姿態 | 修正 | self_rider | 進入時治療 |
| stance_refocus 凝神 | 姿態 | 修正 | self_rider | 進入時自己所有技能冷卻 −1 |
| stance_channel 蓄能 | 姿態 | 修正 | self_rider | 進入時回復法力 |
| stance_cleanse 澄心 | 姿態 | 修正 | self_rider | 進入時淨化自己的減益 |
| reaction_ward 護身 | 反應 | 觸發 | self_rider | 反應觸發時自己也得到護盾 |
| reaction_refocus 回氣 | 反應 | 觸發 | self_rider | 反應觸發時自己所有技能冷卻 −1 |

- `self_rider`（`src/trpg/skillgen/flash_ops.py`）：多一個作用於自己的效果（模板的 `rider` 欄位，`FlashTemplate.rider`，schema 檢查只能是 `affects: self`、只給 `self_rider` 用）。只給只有一個效果的姿態或反應（骨架附帶最多 1 個）；變身姿態（`enter_form` 必須唯一）與擋攻擊（intercept）的反應不出。姿態先試本體不變、由預算器重調附帶的骰子，放不進預算時本體降一級換附帶；反應的主要效果由預算器一起重調。強度下限照 6.34.3。
- 姿態技能只能施加姿態狀態，所以附帶不用狀態（加速、隱蔽試過，驗證器擋下）；反應的附帶治療碰到互斥規則「傷害與友方治療不並存」，所以反應改用回氣。
- 「觸發範圍 +1／+2」（`trigger_range`、`trigger_range_wide`）原本只看觸發距離與形狀大小，反應的單體形狀套不上；改成反應的單體固定射程 +1／+2（武器射程不適用）。這不是新模板，但讓這兩個本來「算在反應裡、實際 0 招套得上」的模板生效。
- 可套用模板數（`skill_balance_audit.py` 1d，不重複）：**反應 10 → 12、姿態 4 → 10**。實際套得上的（內建＋白板抽樣，至少一招合法）：反應 7 → 11 種（`focus_range` 對反應仍套不上）、姿態 4 → 10 種（變身姿態仍只有「強效」）。
- 新測試 `tests/skillgen/test_flash_bal19e.py`：兩種各 ≥ 10 個模板；姿態附帶（內建＋手寫新姿態）、沉勢、反應附帶、反應射程 +1 都過驗證、預算窗與強度下限；變身姿態、已有附帶的姿態、intercept 與已有兩個效果的反應不出。

## 3. 覆蓋與供給前後

`scripts/flash_minor_coverage.py --jobs 6`（同 BAL-10c 參數，其他預設）。「前」在 b6b0c868（344 招），「後」在合併 19d 後（370 招；19d 只加主動武器技，不影響反應／姿態列）。數字是「第 1 次／第 2 次選項數 < 2 的列數」。

| 列 | 前：列數、<2（第 1／第 2 次）、平均 | 後 |
|---|---|---|
| 姿態（變身以外，內建＋白板） | 9 列、1／3、2.00／1.87 | 17 列、**0／5**、**3.88／3.14** |
| 姿態（含 8 個變身形態） | 33 列、25／27、1.27／1.12 | 41 列、24／29、2.20／1.79 |
| 反應（內建＋白板） | 60 列、3／7、3.85／3.58 | 84 列、3／12、3.87／3.60 |
| 全部 | 1094 列、121／169 | 1167 列、120／176 |

- 姿態變身形態（24 列）沒有改善：照 BAL-2c／10c，變身只出修正類的「強效」，附帶與費用類都不適用。
- 後的姿態不足列：幽影架勢 3 階第 2 次 0、不屈心志 3 階、守望姿態 2 階第 2 次 1（階梯到頂或預算窗）。反應不足列：挺身而出（intercept，本來就少）、滑步脫身（兩個效果、沒有傷害，可加的少）、白板 rand_1／rand_4。

`scripts/skill_balance_audit.py --sections 1,2,3,4 --jobs 6` 1a（手寫）反應／姿態：

| 屬性 | 反應 前 → 後 | 姿態 前 → 後 |
|---|---|---|
| 力量 | 5 → 5 | 5 → 5 |
| 敏捷 | 1 → 3 | 2 → 2 |
| 智力 | 0 → 1 | 2 → 2 |
| 感知 | 1 → **4** | 2 → **4** |
| 意志 | 1 → **3** | 1 → **3** |
| 合計 | 8 → 16 | 12 → 16 |

組合器抽樣（1b）與白板可達（1c）沒變（本段沒動配方與組合器）；白板姿態的感知／意志仍是 0。

## 4. 快照與 fixture

- `tests/skillgen/fixtures/refactor_3wr2.json`：合併 19d 後重產。complete／retier 只新增 12 招、既有條目不變；flash 抽樣依技能排序取樣，換了一批（新增 114、移除 123），既有同 key 的值不變。
- `client/src/render/fixtures/skill_icons.json`：重產，只新增 12 條，既有條目、隨機與工坊不變。
- `tests/cli/snapshots/cli_output_hashes.json`：合併 19d 後重產（不加 -n）。

## 5. 檢查

- 合併 main（BAL-19d，f178a123）後：`uv run pytest -n 8 --timeout=1800 -m "slow or not slow" tests/content tests/skillgen tests/narrative tests/llm tests/roguelite tests/api/test_client_fixtures.py`：6884 passed、14 skipped、3 failed——
  - `tests/llm/test_client.py::test_real_model_ping`、`tests/llm/test_skill_eval.py::test_real_model_one_upgrade_item`：要連真模型（本段沒連），與本段無關。
  - `tests/skillgen/test_evolution.py::test_every_option_passes_the_validator_within_the_same_tier_budget`（slow）：**main 既有**，BAL-19c 的 `skill_sum_storm_arrow`（雷鳴箭靈，史詩）進化成「潮濕・雷鳴箭靈」後結構稀有度算成稀有、技能仍標史詩；本段沒動主動技與進化，未修，交 PM。
- CLI 快照：重產 25 passed（不加 -n）；`-n 14` 驗證 25 passed。
- `ruff check`、`ruff format --check`、`mypy`（943 檔沒有問題）、`lint-imports`（7 契約）通過。
- 重播：`trpg battle --map swamp --seed 7` → `battle replay`：88 個動作、313 個事件，一致。
- 複雜度：無新增 `noqa`。

## 6. 待 PM 決定

1. **模板數的解讀**：#110「反應、姿態變化模板各補到約 10 種」。反應在 BAL-18 計數已是 10，但其中 3 個（觸發範圍 +1／+2、專注・範圍）對反應實際套不上；本段補 2 個反應模板並讓觸發範圍 +1／+2 對反應生效（實際可用 7 → 11），姿態補 6 個（4 → 10）。
2. **附帶護身是 6.34.4 沒有逐字列的變化**：姿態歸「修正」類（進入時附帶）、反應歸「觸發」類（效果 +）。若玩法 PM 認為要另立類別或只開放部分附帶（例如只留護盾），改 `content/flash_templates.yaml` 即可。
3. **沉勢（進入代價 +1）**：BAL-10c 說姿態的進入冷卻不算代價，所以只列法力、耐力；它是 `stance_enter_light` 的反向，歸費用類。
4. **變身姿態仍只有「強效」**（BAL-10c 待決 1 未改）：附帶與費用類都不適用變身，想改善要另外決定。
5. **白板姿態配方仍沒有感知／意志**：本段照指示補手寫姿態；配方要不要補由 PM 定（6 個配方都是 `category: spell`、白板會改成主角最高屬性，但 BAL-18 1c 量到感知／意志 0）。
6. **滑步脫身原本設計成「向後滑兩格」**：反應的自身推擊（`push` 對自己、形狀 self）在引擎裡沒有方向，會直接失效，改成隱蔽＋加速。白板反應配方 `step_back`（撤步護體，`push` 對自己）可能有同樣的問題，未查證，建議另查。
7. **不屈心志（防守姿態）歸意志**：加了一條 scaling override；姿態的縮放屬性只是顯示提示。
8. 數值是初值；新反應、姿態沒有跑模擬。

## 合併後修正

BAL-19a～19e 合併後全量有 5 個測試失敗（各段只跑相關測試時漏掉）。修正如下，沒有放寬任何斷言。

| 測試 | 原因 | 修法 |
|---|---|---|
| `test_budget_all_lists_every_skill`、`test_content_check_passes_with_the_shipped_skills` | 寫死「301 個」，技能已 370 | 改讀 `len(library().skills)`，斷言意義不變 |
| `test_mock_n3_snapshot` | 技能池變動，Mock 洗牌後選到不同的手寫技能（例：「暗影・打擊」→「暗影・控場」）；`引擎修補` 多了 `budget.weak` | 以 `UPDATE_CLI_SNAPSHOTS=1` 重產。`budget.weak` 查過：第 1 題的原技能是 `skill_dispel_magic`（既有技能，非新技能），第 2 題的 `skill_sum_whistle_arrow` 最低角色階級 2，Mock 以 2 階出題時預算變大，引擎照常補強——是預期的修補行為，不是內容過弱 |
| `test_run_auto_reaches_a_major_flash_...[4]` | 技能池變了，種子 4 走不到第 3 次大變化 | 掃種子 1～15，改用 6（與 7 並列）；斷言不變 |
| `test_every_option_passes_the_validator_...` | `skill_sum_storm_arrow`（雷鳴箭靈）與 `skill_sum_vanguard_spirit`（號令先鋒）標史詩，但結構算出只有稀有；召喚進化（`summon_evolution`）沿用父技能的稀有度，進化後仍標史詩，與 `structural_rarity` 不符 | 內容標錯：稀有度只管複雜度（6.12），兩招改成 `rarity: rare`。預算比例不變（98.4%、93.7%）。進化程式沒改（一般進化會重算稀有度，召喚進化沿用；內容標對後兩者一致；若日後再有「標得比結構高」的召喚技，召喚進化會再踩到，列為待決） |

連帶重產：`tests/skillgen/fixtures/refactor_3wr2.json`（兩招的完整技能強度雜湊）、`tests/cli/snapshots/cli_output_hashes.json`（`skills_show_all`）。

待決：BAL-19c 報告把這兩招列為史詩（較強的兩招），結構上只有稀有，已照 6.12 改標稀有；若玩法 PM 想讓它們是史詩，需要在結構上加複雜度，而不是只改標記。
