# Phase PB-1a 完成報告｜部位系統段 1a：共用部位系統（引擎＋內容）＋霧鎖真人

> 規格：`docs/phases/PhasePB-1計畫.md` 第 0～4 節（R1～R9 使用者「照建議」、T1～T16 照建議）。設計依據 `docs/design/05-戰鬥.md` 5.12.2、5.12.3，`docs/design/18-雲嶺內容.md` 18.2.3。
> 基準 commit `944b7de7`（main）。本段只做 1a；AI（1b）、前端（1c）、數值工坊（1n）、模擬（1d）沒有動。

## 1. 做了什麼

| commit | 內容 |
|---|---|
| `9d91383b` **commit A**（引擎＋schema，`content/` 一個字都沒改） | 內容 schema `src/trpg/content/parts.py`（`BossPart`、`PartBreakEffect` 五種、`check_parts`、`max_part_hp`／`opening_part_hp`），`UnitTemplate.parts`（空不輸出）＋`template_part_problems`（`content/battle.py`）＋跨檔檢查 `unit_part_problems`（`library/unit_checks.py`，掛在 `unit_phase_problems` 裡）；`UnitState` 六個部位欄位（空值不輸出）；`Attack`／`UseSkill.target_part`（`None` 不輸出）；新檔 `engine/parts.py`（`part_targets`、`check_target_part`）、`engine/part_breaks.py`（分流、覆寫、破壞效果）；`_damage` 分流；普攻與技能帶部位；能力下降的五個讀點；`skill_problem` 封招；`apply_status` 停機制；新事件 `part_damaged`、`part_broken`、`skill_sealed`、`part_stat_down`；`followup_cancelled`／`cancel_charge` 加 `part_broken`；敘事文字（`narrative/events.py`、新檔 `narrative/parts.py`）；`world/battle.py::grow_enemy` 把封的招跟著升階改名；`LOG_FORMAT` `/114` → `/115`（＋`戰鬥紀錄格式變更.md`、11 處測試版號）；`client/openapi.json`、`client/src/api/schema.d.ts` 重產（只多 `target_part`） |
| `a584492b` **commit B**（只加霧鎖真人 `parts`） | `content/units/sect_mist_lock_master.yaml`：拂塵 `whisk`（`any`；`seal_skill: skill_mist_shift`）、氣海 `dantian`（`behind`；`exposed_in: [mist_lock, return_to_one]`；`stop_mechanic: mist_return`）、長劍 `sword`（`any`；`exposed_in: [return_to_one]`；`stat_down damage_dealt 750`（R4 占位）＋`interrupt_charge`）；各 200‰，護甲抗性同本體；檔頭註解寫 #152、18.2.3、占位值 |
| `7c24a827` 測試 | `tests/engine/test_boss_parts_pb1.py`（52 項，合成頭目）、`tests/engine/test_mist_lock_parts_pb1.py`（15 項，正式內容）、`tests/content/test_boss_parts_content.py`（17 項） |
| `5fae665e` 修正 | 部位的引用檢查（`exposed_in`、封招）從範本驗證移到載入內容庫（第 8 節第 10 點） |
| `91ea966f` 上手筆記 | `docs/dev/上手-引擎戰鬥結算.md`（第一節加 `parts.py`、`part_breaks.py`；第二節加「部位分流」；第四節加 15～17：`legal_actions` 不列部位變體、空值不輸出的寫法、升階改名；第五節加測試列）、`docs/dev/上手-內容資料與模擬.md`（「加一個單位」加 1a 部位） |
| （本報告） | `docs/phases/PhasePB-1a報告.md` |

**規則怎麼落地（對照規格第 4 節）**

- 4.2 開場：`lifecycle.make_unit` 複製 `parts`，`part_hp = max(1, max_hp × hp_permille ÷ 1000)`，用建單位當下的 `max_hp`（等級成長已在範本裡；之後 `max_hp` 改變不重算）。
- 4.3 合法性：`part_targets` 先判整個動作（召喚物 `summon`、蓄力武器普攻 `charge_attack`、技能不是單體 `area_skill`、單體但對目標沒有傷害 `no_damage`、`copy_cast` 帶部位 `copy_cast`），再逐個部位判（`broken` → `not_exposed` → `need_behind`／`need_high_or_far`／`need_disabled`）。技能用變奏與修正規則變形之後的技能判（同 `use_skill`）。`behind` 的近戰判定用 `weapon_profile`／`skill_profile` 的 `melee`（同背刺）。`high_or_far` 常數 `FAR_BEYOND = 3`（R7）。`legal_actions` 沒改。種族技（`UseRaceSkill`）與第二段（`FollowupTarget`）沒有這個欄位，帶了 pydantic 直接擋（`extra="forbid"`）。
- 4.4 分流：只在 `perform_unit_attack`（主要目標，連擊武器每一下、詞條連擊）與 `use_skill` 第一段的 `Cast`（`part_for` 只對 `action.target_id`）帶 `part_id`；守護者攔下、穿透後方、第二段、延遲段、反應、持續傷害、表面、墜落一律不帶。`_damage` 沒有 `part_id` 時完全走原路徑。
- 4.5 破壞：`part_broken` 事件 → 觸發表 → `BreakPartEffect`，依 `on_break` 順序呼叫既有處理函式；破的那一下頭目倒下時 `applied: false`、不觸發（T8）。
- 4.6 換階段：`boss_phases._enter` 沒改——封招存在 `sealed_skills`（換技能組不動），`add_statuses` 走 `apply_status`，入口就擋 `suppressed_statuses`。治療只動 `hp`。
- 4.7 打斷：一律 `CancelChargeEffect(reason="part_broken")` → 既有 `_cancel_charge` → `_drop`。`release: attacked` 的順序：部位破壞在傷害結算當下（效果佇列內），被攻擊釋放是被動觸發、攻擊整個結算完才處理，所以找不到蓄力就不釋放（測試鎖住）。

## 2. 逐條驗收（規格 4.11、4.12）

| 規則（4.11） | 測試 |
|---|---|
| 1 合法性與原因代碼 | `test_boss_parts_pb1.py::test_parts_are_listed_by_id_with_their_reasons`、`test_the_back_needs_a_melee_attacker_on_the_back_tile`（背後格、側面、遠程站背後）、`test_high_or_far_counts_beyond_three_tiles[3 格／4 格／相鄰]`、`test_high_or_far_counts_a_higher_tile`、`test_disabled_parts_open_when_the_boss_is_down_stunned_or_frozen[prone/stun/frozen]`、`test_broken_parts_cannot_be_picked`、`test_only_single_target_damage_skills_can_pick`、`test_area_skills_cannot_pick_and_cannot_carry_a_part`、`test_race_skills_and_second_stages_have_no_part_field`、`test_illegal_parts_raise_with_a_reason[未知／背後／未露出]`、`test_targets_without_parts_reject_a_part`、`test_skills_reject_illegal_parts_too`、`test_legal_actions_never_list_part_variants` |
| 2 分流＝實際扣掉的 HP（R2） | `test_a_part_takes_exactly_what_the_boss_lost`（緊接在 `damage_dealt` 後）、`test_shields_and_multipliers_only_pass_on_the_hp_actually_lost`（護盾、倍率 500‰、全被吸收不發） |
| 3 部位護甲／抗性覆寫（R3） | `test_part_armor_overrides_the_hit_defense`（沒寫時相同）、`test_part_resistance_overrides_the_element_modifier` |
| 4 持續傷害、表面等不傷部位 | `test_damage_without_a_part_never_touches_parts[status/surface/effect/explosion]`；範圍技見第 1 列 |
| 5 破壞只一次、回血換階段不長回來、倒下不施效果 | `test_a_part_breaks_once_and_stays_broken_through_heals_and_phases`、`test_breaking_hit_that_downs_the_boss_applies_nothing` |
| 6 封招 | `test_a_sealed_skill_leaves_legal_actions_and_stays_sealed_across_phases`（進到技能組含這招的階段仍封住）、`test_sealing_another_skill_keeps_the_charge` |
| 7 打斷（`next_turn`／`attacked`／`anchor`／定向） | `test_breaking_interrupts_the_charge[head/tail]`（預告格消失、敘事「部位破壞」）、`test_an_attacked_charge_broken_by_the_same_attack_never_releases`（對照組打本體會釋放）、`test_interrupt_covers_an_anchored_charge`、`test_interrupt_covers_a_directed_charge`（龍形吐息）、`test_no_charge_means_interrupt_does_nothing` |
| 8 停機制 | `test_stopping_a_mechanic_removes_it_and_blocks_it_from_coming_back`；正式內容 `test_breaking_the_dantian_in_return_to_one_stops_the_heal`（對照組照常回血）、`test_breaking_the_dantian_in_mist_lock_keeps_return_to_one_from_healing` |
| 9 `stat_down` 五種 | `test_stat_down_lowers_move_armor_hit_resist_and_damage`、`test_hit_down_lowers_the_boss_attack_total`、`test_damage_dealt_down_lowers_the_boss_damage` |
| 10 `control` | `test_control_goes_through_the_normal_status_path`（暈眩對頭目走 Boss 硬控轉換） |
| 11 多段攻擊（R5） | `test_every_strike_of_a_multi_hit_weapon_hits_the_same_part`（雙匕首從背後，第一下後頭目轉身，第二下仍打背；第一下打破後剩下打本體） |
| 12 預覽 | `test_the_preview_shows_part_damage_without_side_effects` |
| 13 暫停點 | `test_resume_after_a_prompt_matches_a_straight_run[True/False]`（頭目格擋 `prompt`；直接 resume、存檔讀回 resume、帶決定一次跑完三者狀態 JSON 相同） |
| 14 重播 | `test_a_battle_with_target_part_replays_exactly`（手寫政策打「頭」，`BattleLog` JSON 往返後重播狀態與 `rng_state` 一致） |
| 15 clone／JSON | `test_clone_and_json_keep_every_part_field`、`test_units_without_parts_serialize_no_part_keys`；`tests/engine/test_state_clone.py`（`_COPIED` 加 `part_hp`、`part_mods`） |
| 16 霧鎖真人 | `test_mist_lock_parts_pb1.py`：表格、HP 120 時各 24、各階段可選表（劍陣只能拂塵；鎖霧氣海要背後近戰、長劍未露出；歸一長劍露出）、拂塵封霧遁＋紀錄文字、長劍降傷 750‰＋打斷蓄力斬、鎖霧千山蓄力跨進歸一也打斷、升階改名 |
| 17 內容檢查 | `tests/content/test_boss_parts_content.py`：非頭目、1 個、5 個、加總 601、重複 ID、`on_break` 0／3 項、未知階段、封的招不在技能組、未知 `stat`、未知 `reach`、召喚物、跨檔（未知狀態、非控制狀態）、沒填不輸出（掃全部單位，只有霧鎖真人有） |

| 4.12 驗收 | 結果 |
|---|---|
| 一場紀錄＋重播 | 見第 4 節 |
| 4.10 兩階段比對與三個雜湊 | 見第 3 節 |
| CLI 快照、skillgen、narrative（含 slow） | 見第 4 節 |

## 3. 不變比對（規格 4.10）

腳本在 scratchpad（未 commit），比照 BAL-21a：地圖預設陣容、效用 AI、`max_rounds=30`；每場比對完整事件 JSON、步驟、輪數、勝方、最終 `rng_state`、最終狀態 JSON。**沒有剝掉任何鍵**（新欄位空值不輸出，改前改後的原始 JSON 直接相等）。

- **commit A（引擎＋schema）vs 改前 `944b7de7`**：
  - 8 張地圖 × 種子 1、2：`battles=16 events=5689 different=0`
  - 3 張頭目圖 × 種子 3～12：`battles=30 events=14804 different=0`
  - 原始 JSON（含最終狀態）整份相等：`True`
- **commit B（霧鎖真人 `parts`）vs commit A**：
  - 事件、步驟、輪數、勝方、`rng_state` 46 場全部相同；只有 `cloud_summit` 12 場的 `final` 不同
  - 逐單位比對：差異只有 `sect_mist_lock_master` 多出 `parts`、`part_hp` 兩個鍵（12 場都沒有部位被打到——1a 沒有 AI 會帶 `target_part`），其他單位與戰場欄位全同（`bad 0`）
- **三個雜湊**：

| | 改前 `944b7de7` | commit A | commit B | commit B 把 YAML 還原後 |
|---|---|---|---|---|
| `hash_ruleset` | `a2fb31c0d6d1…6f710ce0` | 同左 | 同左 | 同左 |
| `ruleset_hash`（一輪存檔） | `79b36f86a85e…acee5f47a4e` | 同左 | `549b3d4d35ee…dc525e9bf3717144502a247186f961d9b7` | `79b36f86a85e…acee5f47a4e` |
| `content_digest`（世界日誌） | `93bead55aab9…feff299a63bd7` | 同左 | `43f2388831fe…c4586d1e387d1dadb3710c36a31bb9ea` | `93bead55aab9…feff299a63bd7` |

完整值：`hash_ruleset` `a2fb31c0d6d1fd3f8a5740cdc77d73422056ec5a060f47515216d1db6f710ce0`；`ruleset_hash` 改前 `79b36f86a85e888a308492909abcf67111744c510e5a89485a780acee5f47a4e` → `549b3d4d35ee9886074b2da3e055fbdc525e9bf3717144502a247186f961d9b7`；`content_digest` 改前 `93bead55aab9787632a6cc758b012a741f3519a011f2f5c59ddfeff299a63bd7` → `43f2388831fe375f9e8dea807669bd8d4c586d1e387d1dadb3710c36a31bb9ea`。

**其他「拿掉就回到舊值」的證明**：`client/openapi.json` 只多 3 處 `target_part`（`Attack`、`UseSkill` 的輸入與輸出 schema），拿掉這兩個欄位就回到原檔；CLI 快照、parity 夾具都沒有重產（第 4 節）。

## 4. 測試與檢查（結束碼）

交件前在 `5fae665e` 跑，每個指令的結束碼分開記：

| 指令 | 結束碼與結果 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0（1497 個檔無問題） |
| `uv run lint-imports` | 0（14 kept、0 broken） |
| `uv run trpg content check` | 0（662 個檔、404 個技能） |
| 相關 pytest（`-n 8`）：規格 4.12 第 3 點全部、4.11 新檔、`tests/world`、`tests/content`、`tests/api`、版號字面值所在的 CLI 測試、`test_reactions`、`test_reaction_skills`、`test_view`、`test_event_filter`、`test_statuses`、`test_ai_utility`、`test_skill_ai`、`tests/test_architecture.py` | 0：6105 passed、1 skipped |
| `uv run pytest -n 8 -m "not llm" tests/skillgen tests/narrative`（含 slow，parity 夾具沒動） | 0：5390 passed、14 skipped |
| `uv run pytest -n 8 tests/cli/test_output_snapshots.py -m slow` | 0：24 passed，**0 個鍵變動、沒有重產** |
| `trpg battle --map cloud_summit --seed 2 --log-json` ＋ `trpg battle replay` | 0／0：格式 `trpg-battle-log/115`，「重播驗證通過：96 個動作、464 個事件，最終狀態一致」 |
| 同上 `oil_depot` 13 | 0／0：102 個動作、454 個事件 |
| 同上 `swamp` 21 | 0／0：54 個動作、240 個事件 |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0：308 檔、3976 項 |
| `corepack pnpm -C client build` | 0 |

過程中：第一次跑相關測試有 4 項失敗（`test_boss_phases.py::test_mist_lock_peaks_telegraphs_a_cross`、`tests/world/test_enemy_ai_moves_149.py` 3 項）——這些測試把霧鎖真人的 `phases` 換成空的再組範本，`exposed_in`／封招的引用檢查原本放在範本驗證裡就擋下。改成載入內容庫時檢查（`5fae665e`，見第 8 節第 10 點），測試本身沒改。

## 5. 現況確認（對照規格第 1 節）

- 第 1 節的行號與函式都對得上，只有兩點補充：
  1. 霧鎖真人範本 `max_hp: 120` 是基礎值，加體質後實戰最大 HP 是 132（`template_max_hp`），雲頂觀的大世界戰鬥還會依等級成長；所以實戰的部位血量不是 24（預設陣容的 `cloud_summit` 是 26）。「各 24」只在最大 HP 120 時成立（測試用 `max_hp=120` 覆寫驗）。
  2. 頭目升階後技能 ID 會變成 `<原 ID>_t<階>`（`world/battle.py::grow_enemy`），規格的檔案清單沒有這個檔；不跟著改的話封招與「正在蓄力的是不是這一招」在大世界都對不上，所以在那裡加了改名（`_renamed_part`）。
- `src/trpg/narrative/storyteller.py` 是大世界場景的說書人，**目前沒有任何吃戰鬥事件的路徑**（`world_story.py` 也只用世界事件）；戰鬥裡的敘事文字是 `narrative/events.py` 的戰鬥紀錄。本段給 `part_broken`（含破壞效果的中文）、`part_damaged`、`skill_sealed`、`part_stat_down` 與 `followup_cancelled` 的 `part_broken` 寫了紀錄文字；「說書人輸入含 PartBroken」沒有可接的地方，沒做 `MockLLMClient` 測試（待 PM 決定第 6 點）。說書人沒有任何改部位狀態的工具（守則 3）。

## 6. 快照與既有測試的變動

- 版號字面值 11 處（`trpg-battle-log/114` → `/115` 8 處＋`endswith("/114")` 3 處），與 BAL-21a 同一批檔。
- `tests/engine/test_state_clone.py`：`_COPIED[UnitState]` 加 `part_hp`、`part_mods`（`clone()` 裡 `dict(...)` 複製），獨立性檢查各加一行。
- CLI 快照 0 個鍵變動、parity 夾具沒動、沒有換任何固定種子。

## 7. 新增的複雜度 `# noqa`

無。（`_action_reason` 拆出 `_skill_reason`、`skill_problem` 的封招拆成 `_sealed_problem`、`apply_status` 的停機制併進原本的提早返回，都沒有超標。）

## 8. 規格沒寫到、採保守做法的地方

1. **`control` 不擲抵抗**：破壞效果沒有施放者的屬性可擲，走 `apply_status`（免疫 `_status_blocked`、Boss 硬控轉換、控制遞減照常），不擲 `status_save`。霧鎖真人沒有 `control`，實戰不受影響。
2. **`part_damaged` 只在部位真的扣到（≥ 1）時發**；全被護盾吸收、轉移掉時不發。
3. **部位的 `resist`／`element_mods` 逐鍵覆寫**：只換有寫的組／元素，其他照本體。
4. **`disabled` 用狀態 ID 清單**（`prone`、`stun`、`frozen`，照設計文字），不用 `skip_turn`（倒地沒有 `skip_turn`）。
5. **詞條連擊（`combo`）的追加一下也打同一部位**（同一目標、同一次普攻）；分裂（`cleave`）、穿透後方、守護者攔下的打本體。
6. **`stat_down` 的累計**：`move`／`armor`／`hit`／`resist.<組>` 相加（降低量），`damage_dealt` 相乘（‰）。`damage_dealt` 的 `amount` 要 < 1000。
7. **封招只擋主動使用**（`skill_problem`，`legal_actions` 跟著不列）；反應技的路徑（`reaction_problem`）沒擋——目前沒有部位封反應技。
8. **停機制只攔 `apply_status`**（含換階段的 `add_statuses`、技能、開場狀態都走這裡）；引擎少數直接寫 `StatusInstance` 的路徑（蓄力 `charging`、姿態維持）不攔。本段只用在 `mist_return`。
10. **`exposed_in` 的階段 ID、`seal_skill` 的招在技能組裡**這兩項引用檢查放在載入內容庫（`unit_part_problems` → `part_reference_problems`，`trpg content check` 與數值工坊寫回都會跑），不放在 `UnitTemplate` 本身的驗證：既有測試與工具常把頭目的 `phases`／`skills` 換掉再組範本（規格 4.1 寫「model validator＋跨檔檢查」，結構類——頭目標籤、召喚物、2～4 個、ID、加總——仍在範本驗證）。
9. `part_broken.source_id`（打破它的單位）是本段加的欄位，給紀錄與之後的模擬報表（PB-1d「由哪個 build／單位打破」）用。

## 9. 影響

- 舊戰鬥紀錄（`/114`）不能重播、戰鬥中的存檔讀不回（狀態與動作結構變了）。使用者 2026-11-12：「存檔都可以刪除」；本段沒有刪任何存檔檔案、沒寫遷移。
- 霧鎖真人 YAML 改了 → 一輪存檔的 `ruleset_hash`、世界日誌的 `content_digest` 都變：使用者重開伺服器後進行中的一輪從頭開始、舊世界日誌標成不能重播（世界日誌的規則鍵也含 `LOG_FORMAT`）。`hash_ruleset` 不變。
- 1a 沒有任何 AI 會帶 `target_part`，所以實戰（模擬、自動推進）結果和改前逐字相同；部位要到 1b（AI）、1c（介面）才會被打。
- **請使用者重開伺服器檢查的重點**：本段沒有介面，玩家還點不到部位；可以看的是戰鬥紀錄格式 `/115`、雲頂觀頭目戰照常打完。

## 10. 待 PM 決定

1. `control` 破壞效果要不要擲抵抗；要擲的話用哪個屬性當攻方（目前不擲，第 8 節第 1 點）。
2. `part_damaged` 扣 0 點時要不要也發（目前不發，介面「拂塵還剩 N」不受影響）。
3. 部位小血條、`part_damaged` 對「頭目資訊被隱藏」的觀看者要不要藏數字（目前紀錄文字照 `hidden` 規則不寫血量，但事件本身對所有陣營可見，`api/hidden_info.py` 沒登記；屬 PB-1c）。
4. 說書人目前沒有吃戰鬥事件的路徑，「部位破壞交給說書人敘事」要接在哪（戰後摘要？），還是戰鬥紀錄這一行就算（第 5 節）。
5. 封招要不要也擋反應技（第 8 節第 7 點；目前沒有內容用到）。
6. 長劍降傷 750‰ 是 R4 占位，等使用者在數值工坊（PB-1n 開白名單後）調。
7. 部位引用檢查放在載入時而不是範本驗證（第 8 節第 10 點）是否接受。
8. 霧鎖真人實戰部位血量是 26（HP 132 × 200‰），比設計表敘述的「120 HP、各 24」高；是否接受以實戰最大 HP 為準（目前如此）。

## 開發 PM 裁定（2026-11-12，第八任）

1. control 破壞效果不擲抵抗：接受。
2. 部位扣 0 點不發 part_damaged：接受。
3. 頭目資訊被隱藏時部位事件藏數字：要，併進 PB-1c（api/hidden_info.py 登記）。
4. 說書人輸入含 PartBroken：本段不接，列為後續（之後說書人改吃戰鬥事件時一起做）。
5. 封招只擋主動使用：接受，日後有反應技內容用到再補。
6. 長劍降傷 750‰：R4 占位，使用者在數值工坊調（PB-1n 開放部位欄位）。
7. 引用檢查改在載入內容庫時做：接受。
8. 部位 HP 以實戰最大 HP 為準：接受。
9. 停機制只攔一般施加狀態路徑：接受。
