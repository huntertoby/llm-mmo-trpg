# Phase 3-33e1 報告｜17 種召喚物（一）＋灌注關鍵字補齊

> 規格：`docs/phases/Phase3計畫.md` 36.6；設計：`docs/design/06-技能.md` 6.29.1（灌注關鍵字）、6.29.5（清單）；外觀：`docs/art/召喚物外觀.md`、`content/summon_looks.yaml`。數值都是初值（放 `content/`），**沒有調任何既有數值**。名稱與數值請玩法 PM 審（第 2、3 節）。

## 1. 交付

| 項目 | 內容 | 位置 |
|---|---|---|
| 灌注關鍵字補齊到 10 個 | 對照表多 6 項：潮濕＝命中在目標格造水、帶電＝普攻另加 1d4 雷電、倒地＝命中絆倒（敏捷對抗，每隻每輪 1 次）、高處＝站得比目標高時普攻傷害 +25%、隱蔽＝召喚時隱蔽 2 回合、召喚物＝自身最大 HP +20% | `content/rules/core.yaml`（`summon_infusions`）、`content/rules.py`（`SummonInfusion`）、`engine/weapon_traits.py`、`engine/summons.py` |
| 範本的固有關鍵字與特性 | `UnitTemplate` 多 `innate`（固有灌注，與施放時選的並存、相同只算一次）、`hit_rules`（命中後條件特性：目標／自己站在水面時施加狀態或雷電連鎖）、`pulse`（自己的回合開始：腳下造表面、治療附近受傷友方） | `content/battle.py`、`engine/infusion.py`（`active_keywords`）、`engine/summons.py`（`pulse_summon`）、`engine/turns.py` |
| 召喚物 6 種新增、2 種改版、1 種確認 | 見第 2 節 | `content/units/summons/` |
| 召喚技能 6 招 | 見第 3 節 | `content/skills/` |
| 關鍵字推導 | 規則多了參數 `unit`（效果的 `unit` 欄位），每種召喚物的固有關鍵字由「召喚該範本」推導，不由人填 | `content/skill_keywords.yaml`、`content/skill_keywords.py` |
| 戰意（戰意圖騰改版） | 新狀態 `rallied`（`attack_bonus: 1`，攻擊值 +1），戰意圖騰的光環改成它；`StatusDef.attack_bonus` 加進 `attack_value` | `content/statuses.yaml`、`engine/rules/statuses.py`、`engine/rules/combat.py` |
| 召喚物專用武器 | 4 把（`spark_staff`、`water_jet`、`shade_blades`、`talons`），`WeaponDef.summon_only: true` → 不列入開局可選的武器（`start_weapons`），一般開局的亂數序列不變 | `content/weapons.yaml`、`roguelite/start.py` |
| 起始包 | `dev_summoner` 系列新增 6 個對照包（每包一招新召喚技能＋火焰箭），開發者起始包 14 → 20 | `content/dev_starters.yaml` |
| 外觀顏色 | 有固有關鍵字的召喚物固定用自己的元素色（`UnitView.summon_look.element`），通用的元素之靈仍依灌注上色 | `engine/view.py` |
| 格式 | `LOG_FORMAT` `/50 → /51`（PM 合併時定號）；單位狀態多 `trip_round`；CLI 快照與技能圖示 fixture 已重產 | `engine/runner.py`、`tests/cli/snapshots/`、`client/src/render/fixtures/skill_icons.json` |

灌注關鍵字的現成效果沿用 3-33b：點燃→燃燒、冰凍→緩速、標記→被標記、撞擊→震退 1 格。

## 2. 每種召喚物的特性（9 種）

> 欄位：HP＝範本 `max_hp` 經體質公式後的最終值；武器射程；速度；AI 預設模式（`default_mode`）。外觀照 `summon_looks.yaml`，範本的 `look` 與表一致（`tests/content/test_summon_looks.py`）。

| 召喚物 | 定位 | HP／速度／武器 | 固有關鍵字 | 特性（怎麼實作） | 預設模式 | 對應召喚技能 |
|---|---|---|---|---|---|---|
| 火靈 `summon_fire_spirit` | 遠程輸出 | 14／5／火焰法杖 1d6（射程 5） | 點燃 | 普攻命中燃燒（固有灌注） | 跟隨 | 召喚火靈 |
| 冰靈 `summon_ice_spirit` | 遠程控場 | 14／5／冰霜法杖 1d6 | 冰凍 | 普攻緩速；`hit_rules`：目標站在水面上時直接冰凍 1 回合（「潮濕」＝水表面） | 跟隨 | 召喚冰靈 |
| 雷靈 `summon_thunder_spirit` | 遠程輸出 | 14／5／電火法杖 1d4（射程 5，雷電） | 帶電 | 普攻另加 1d4 雷電；`hit_rules`：自己站在水面時，雷電連鎖到目標 2 格內最多 2 名其他敵人（武器骰 ×50%） | 跟隨 | 召喚雷靈 |
| 水精 `summon_water_sprite` | 治療、輔助 | 12／4／水流 1d4（射程 3） | 潮濕 | 普攻在目標格造水；`pulse`：自己的回合開始時腳下造水、治療 1 格內受傷友方 1d4 | 守護我（`guard`） | 召喚水精 |
| 骷髏戰士（強化）`summon_skeleton_warrior` | 近戰擋路 | 20／4／單手劍 1d8 | 倒地 | 盾擊：普攻命中時絆倒（敏捷對抗，每輪 1 次）；HP、武器不變 | 跟隨 | 喚起骷髏（既有；現在也製造「倒地」） |
| 影魅 `summon_shade` | 刺殺、斥候 | 10／5／影刃 1d4（暗影，暴擊 19） | 隱蔽 | 召喚時隱蔽 2 回合；影刃的 `backstab_dice: 2`（背刺多 2 顆骰，沿用 3-32a 參數） | 跟隨 | 喚出影魅 |
| 鷹隼 `summon_hawk` | 斥候 | 8／7／利爪 1d4 | 標記（技能另製造「高處」） | 普攻命中標記；`hit_rules`：命中同時揭露目標（`revealed`，解除隱蔽） | 跟隨 | 喚出鷹隼 |
| 戰意圖騰（改版）`summon_war_totem` | 光環 | 18／0／— | （召喚物，技能製造 `summon`） | 光環狀態激昂 → **戰意**（攻擊值 +1）；範圍 2 格內友方含其他召喚物（既有圖騰規則本來就含召喚物） | 待命 | 立起圖騰（既有） |
| 殘影分身 `summon_afterimage` | 誘餌 | 14／4／匕首 | （規則改變產生） | **確認**：外觀 `humanoid／afterimage／translucent／concealed` 與 `summon_looks.yaml` 一致，欄位齊全（`default_mode` 沿用預設跟隨；本段沒有改它） | 跟隨 | 殘影之誓（既有，傳說） |

元素之靈（`summon_elemental_spirit`）：**保留不動**（通用的靈，現有起始包、技能與測試都用它），火靈是新增的獨立範本（見「待 PM 決定」#1）。

## 3. 新召喚技能（6 招，玩法 PM 審）

共通：階 1、稀有度 rare、形狀 `ground_tile` 射程 4、1 AP、法力 8～10、冷卻 4、`category: spell`、`skeleton: summon`；關鍵字由推導得出（下表「製造」欄）；技能圖示由 `icon_of` 自動產生，fixture 已重產；AI 對所有 `summon` 技能一視同仁（`tests/engine/test_summons_e1.py::test_ai_casts_the_new_summon_skills`）；都在 `_POOL_ONLY`（由技能池給出），`dev_summon_*` 起始包可帶。

| 技能 | 召喚 | 持續 | 法力／冷卻 | 縮放屬性 | 標籤 | 製造的關鍵字 |
|---|---|---|---|---|---|---|
| 召喚火靈 | 火靈 | 3 輪 | 10／4 | 智力 | fire | 點燃、召喚物 |
| 召喚冰靈 | 冰靈 | 4 輪 | 10／4 | 智力 | ice | 冰凍、召喚物 |
| 召喚雷靈 | 雷靈 | 4 輪 | 10／4 | 智力 | lightning | 帶電、召喚物 |
| 召喚水精 | 水精 | 4 輪 | 8／4 | 智慧 | water、support | 潮濕、召喚物 |
| 喚出影魅 | 影魅 | 4 輪 | 8／4 | 敏捷 | shadow | 隱蔽、召喚物 |
| 喚出鷹隼 | 鷹隼 | 4 輪 | 8／4 | 智慧 | wind | 標記、高處、召喚物 |

預算：召喚技的點數＝武器骰平均 × 持續 × 800‰，1d4 武器 × 3 輪 = 6.0 低於階 1 的下限（70% × 8.68 = 6.08），所以水精、雷靈、影魅、鷹隼用 4 輪（8.0）過預算；火靈、冰靈 1d6 × 3 輪 = 8.4。雷靈的額外 1d4 雷電、水精的治療、影魅的背刺骰、鷹隼的標記與揭露，**預算公式不計**（見「待 PM 決定」#4）。

## 4. 驗收證據

| 驗收項 | 證據 |
|---|---|
| 10 個灌注關鍵字各自生效 | `tests/engine/test_summons_e1.py`：`test_the_infusion_table_covers_all_ten_keywords`、`test_wet_creates_water_on_the_target_tile`、`test_charged_adds_lightning_damage`、`test_prone_trips_once_per_round`（含每輪 1 次、下一輪恢復）、`test_high_ground_adds_damage_only_when_higher_than_the_target`、`test_concealed_infusion_conceals_the_summon_for_two_rounds`、`test_summon_infusion_adds_twenty_percent_hp`；點燃／冰凍／標記／撞擊沿用 `test_summon_growth.py` |
| 固有與選擇的灌注並存 | `test_a_chosen_infusion_that_equals_the_innate_one_counts_once` |
| 每種召喚物的特性情境 | `test_fire_spirit_burns_its_target`、`test_ice_spirit_slows_and_freezes_targets_standing_in_water`、`test_thunder_spirit_chains_through_water_only_when_standing_in_it`、`test_water_sprite_*`（造水、只治療相鄰受傷友方、回合開始觸發）、`test_skeleton_warrior_trips_with_its_shield_bash`、`test_shade_starts_concealed_and_stabs_harder_from_behind`、`test_hawk_marks_and_reveals_its_target_and_is_fast`、`test_war_totem_gives_rallied_to_allies_and_other_summons_within_two`、`test_rallied_raises_the_attack_value_by_one`、`test_afterimage_keeps_its_look_fields` |
| 新技能過預算與關鍵字、圖示、AI 會用 | `test_new_summon_skills_have_their_keyword_and_pass_the_budget`、`test_ai_casts_the_new_summon_skills`；`tests/skillgen/test_validate.py`／`test_keywords.py`（每個池 ≥ 3 招階 1 起始技能）；圖示 fixture 的測試（`tests/narrative/test_skill_icon.py`）；`tests/content/test_coverage.py` |
| 同種子確定、重播一致 | `test_same_seed_and_inputs_give_the_same_battle`；`tests/sim/test_summon_report.py::test_the_new_summon_packs_summon_and_replay_identically`（6 個新對照包在 Boss 地圖上 `run_battle` ＋ `replay` 終局逐位元一致） |
| 召喚專用武器不進開局 | `test_summon_only_weapons_are_not_start_weapons` |
| 外觀欄位 | `tests/content/test_summon_looks.py`（範本 `look` 與 `summon_looks.yaml` 一致）、`test_innate_summons_keep_their_own_element_colour_in_the_view` |
| 組合器種子 0–49 | `tests/skillgen` 全綠（含組合器種子 0–49 的驗證；「戰意」有預算點數，會進組合器的友方增益候選） |
| 全量 | 見第 7 節 |

被迫改的既有測試（原因都是新增內容，非行為回歸）：`test_con_hp.py`（新範本的最終 HP）、`test_summon_content.py`（範本清單）、`test_coverage.py`（新技能進 `_POOL_ONLY`、`rallied` 允許清單）、`test_combo_resources.py`／`test_validate.py`／`test_budget.py`（新增狀態 `rallied`）、`test_summon_growth.py`（灌注可選項：10 個關鍵字都有對照後，召喚技能自己製造的「倒地」「召喚物」也能灌注，預設取第一個）、`test_summon_ai.py`（估值多了灌注點數）、`test_summon_text.py`（光環文字「戰意」）、`test_run_start_api.py`／`test_keyword_start.py`（起始包 14 → 20、開局武器不含召喚專用）、8 個 `LOG_FORMAT` 斷言、CLI 快照雜湊。

## 5. `sim_summons.py` 小量表

`uv run python scripts/sim_summons.py --packs dev_summoner,dev_summon_fire,dev_summon_ice,dev_summon_thunder,dev_summon_water,dev_summon_shade,dev_summon_hawk --seeds 2 --jobs 3`（5 張正式地圖 × 2 種子，每包 10 場；主角 Lv1；樣本很小，只看有沒有跑通與大致量級）：

| 起始包 | 場數 | 勝率 | 平均輪數 | 主角 DPR | 我方傷害/場 | 召喚物傷害/場 | 召喚物占比 | 召喚次數/場 | 平均存活輪數 | 被打倒（隻／總數） |
|---|---|---|---|---|---|---|---|---|---|---|
| 喚靈（保證召喚，元素之靈）| 10 | 80% | 4.0 | 6.2 | 119 | 21 | 17.5% | 0.70 | 2.0 | 1／7 |
| 召喚火靈 | 10 | 90% | 4.0 | 10.7 | 130 | 27 | 20.7% | 0.80 | 1.8 | 1／8 |
| 召喚冰靈 | 10 | 70% | 4.8 | 10.4 | 124 | 14 | 11.4% | 0.90 | 1.4 | 3／9 |
| 召喚雷靈 | 10 | 70% | 4.4 | 7.0 | 114 | 17 | 15.1% | 0.80 | 1.8 | 1／8 |
| 召喚水精 | 10 | 60% | 4.7 | 6.4 | 114 | 3 | 2.4% | 1.10 | 1.2 | 5／11 |
| 喚出影魅 | 10 | 80% | 4.9 | 10.3 | 133 | 9 | 7.0% | 0.90 | 1.1 | 8／9 |
| 喚出鷹隼 | 10 | 90% | 4.1 | 9.3 | 130 | 15 | 11.3% | 1.10 | 1.4 | 7／11 |

觀察：火靈／雷靈／冰靈的貢獻在 11%～21%；影魅（HP 10、近戰）與鷹隼（HP 8、近戰）9 隻中倒 8 隻、11 隻中倒 7 隻，是最脆的；水精的主要價值是治療與造水，傷害統計看不出來（治療量未列入該表）。**不調數值**，建議看第 6 節。

## 6. 待 PM 決定

1. **元素之靈 vs 火靈**：規格寫「原元素之靈」。本段保留 `summon_elemental_spirit`（現有技能「召喚元素之靈」、起始包、build、測試都在用）不動，火靈另建範本。若要把元素之靈改名為火靈並合併，需改 build／起始包／存檔相容（舊存檔的範本 ID）。3-33h1 #1（沒灌注的元素之靈是灰白）因此只在「通用靈依灌注上色」處理：召喚技能一定製造「召喚物」關鍵字，所以現在幾乎一定有灌注（預設取第一個持有的）。
2. **「潮濕」＝站在水面上**：冰靈「命中潮濕目標時冰凍」、雷靈「站在水裡時連鎖」都以水表面判定（遊戲沒有潮濕狀態）。若玩法 PM 想要潮濕狀態，需新增狀態。
3. **鷹隼「會飛」只近似**：速度 7、標籤 `flying`，沒有新增飛行移動規則（不穿越地形與單位）；規格寫「沿用現有原語，不新增引擎行為」。需要真飛行請排進 3-33e2。
4. **預算公式不計特性**：召喚技的預算只算武器 dpr × 持續；雷靈額外雷電、水精治療、影魅背刺骰、鷹隼標記揭露都不計，所以 1d4 召喚物靠 4 輪才過下限。是否要把這些計入預算請玩法 PM 決定。
5. **灌注選項變多**：10 個關鍵字都有對照後，召喚技自己製造的「召喚物」「倒地」等也算持有 → 玩家施放召喚技幾乎總是 ≥ 2 個可選，灌注視窗會常跳出；預設取持有順序第一個（AI 依近戰／遠程偏好，`summon`（HP +20%）沒有偏好定位，是 AI 的最後選擇）。是否要「預設取最後一次選的」或「只有 1 個才不問」請決定。
6. **絆倒的對抗判定**：用施放者（召喚物）的敏捷對抗目標敏捷（沿用 `trip` 動作的公式），每隻每輪 1 次（`UnitState.trip_round`，狀態格式多一欄）。成功率沒有顯示在預覽（預覽視為成功）。
7. **高處 +25%**：只套用在召喚物的普攻（不含連鎖／額外傷害）；比較的是格子高度（`tile.height`），與 `height_hit_bonus` 命中修正是兩回事。
8. **戰意 +1**：做成攻擊值（命中比例的分子）+1，不是傷害 +1；只套用在普攻與武器技的攻擊值（`attack_value`），不影響法術技的命中。狀態有預算點數 4（為了圖騰預算公式），因此組合器也可能把它當友方增益選用。
9. **模擬**：樣本很小（每包 10 場）、主角 Lv1，不能下平衡結論；影魅／鷹隼被打倒比例高，建議 3-33g 的對照模擬一併看，並考慮提高 HP 成長係數（3-33f 已列）。

## 7. noqa 與最終檢查

沒有新增複雜度類（`C901`／`PLR*`）的 `noqa`。測試內有數處 `PLC0415`（函式內 import，沿用既有測試的作法）。

最終檢查見下一節（`scripts/check.py` 結果於完成時填寫）。
