# Phase 3J-3 報告｜形態身分

> 規格：`docs/phases/Phase3J計畫.md` 第 4.8 節；設計 `docs/design/06-技能.md` 6.27.1、6.28、6.30。3J-2（定向蓄力）沒有碰；3J-4（正式技能與池補齊）、3J-5（外觀）沒有做。

## 做了什麼

1. **第 12 個關鍵字「形態」（`form`）**（`content/skill_keywords.yaml`）：製造＝`enter_form`；利用＝條件 `in_form`、化形專精的兩種改變。註：規格文字寫「第 11 個」，中毒加入後實際是第 12 個。
2. **新條件 `in_form`「在形態中」**（`content/skill_conditions.yaml`）：可選參數 `form_category`（`physical`／`mental`，省略＝任何形態）；只看施放者（`CASTER_CONDITIONS`），技能層級、效果層級、修正規則條件都能用。引擎 `skills/conditions.py`、`ConditionSpec`、卡片句（「你在形態中」「你在物理形態中」…）、驗證器、工坊選單（新參數型別 `form_category`）、LLM 提議 schema、工坊說明文字（`workshop_text.yaml` 兩筆）一致。harshness 設 `harsh`（要先花 1 AP、佔欄位、付維持費）。
3. **化形專精**（`content/skills/skill_form_mastery.yaml`，史詩修正型被動，`exclusive_group: mastery`）：
   - 維持費減半（新改變 `form_upkeep_permille: -500`；`amount * 500 // 1000`，8→4、3→1）；
   - 進入獎勵數值 ×1.5（新改變 `form_entry_permille: 500`；進入時快照成 `FormState.entry_permille`）：護盾、治療、下一次攻擊命中／暴擊、本回合移動、巨人撞擊加成（+50%→+75%）、範圍傷害、相鄰治療；各自無條件捨去；**隱蔽回合數不放大**（1 回合 ×1.5 捨去仍 1）；
   - 手上武器的武器技傷害 −20%：新套用對象 `applies_to.weapon_skills`（只限 `damage_permille`，不含普攻，形態中的天生武器普攻也不受影響）；
   - 互斥組文字改為「專精（普攻精通、群召、精英召喚、化形專精）」。
   - 預算：新增 `form_upkeep_per_100`／`form_entry_per_100`（各 200）與 `uses.weapon_skills: 10`，反推到 85.7%（合格區間 70–100%）；初值，未經模擬。縮放屬性覆寫為意志（`skill_scaling.yaml`）。
4. **開局**：`form` 設 `start_hidden: true`（形態池沒有 1 階主動起始技能，照 3-53b）；三選一、工坊、推導照常。
5. **橋接嫁接**（`skill_evolution.yaml`）：`form` 只有 `uses`（`damage` 帶 `in_form`），沒有 `makes`（進入形態是姿態唯一效果，不能嫁接）。
6. **10 招 `skill_form_*`**：新增資料層級表格測試確認法術類別、`weapon_req: any`、姿態、沉默看形態類別。
7. 其他：`LOG_FORMAT` `/79` → `/80`（`runner.py` 文件字串與 11 個測試字面值）；裝備外觀關鍵字清單加 `form`（`appearance.yaml`、`gearAppearance.json`）；前端 `artPalette.ts` 加關鍵字顏色；參考 build `build_form_mastery`；技能 297。

## 驗收對照

見下方「驗收指令」與測試名稱（`tests/engine/test_form_identity_3j3.py` 35 個測試）：

| 條件 | 證明 |
|---|---|
| 在形態中（任何／物理／心智）表格 | `test_in_form_condition_table`、`test_in_form_ends_with_the_form`、`test_skill_level_in_form_makes_the_skill_usable_only_in_a_form`、`test_effect_level_in_form_applies_the_effect_only_when_it_holds` |
| 驗證器／卡片句／關鍵字推導 | `test_in_form_validator_accepts_valid_and_rejects_bad_parameters`、`test_in_form_condition_text_has_no_english`、`test_in_form_is_a_form_keyword_exploiter_and_enter_form_a_maker`、`tests/skillgen/test_keywords.py`（形態正負範例） |
| 化形專精互斥 | `test_mastery_is_mutually_exclusive_with_the_other_masteries` |
| 維持費減半（實際跑引擎） | `test_mastery_halves_the_upkeep_rounding_down`、`test_mastery_upkeep_that_rounds_to_zero_is_not_paid` |
| 進入獎勵 ×1.5 | `test_mastery_scales_the_entry_shield_by_one_and_a_half`、`test_mastery_scales_numeric_entry_bonuses`、`test_mastery_scales_the_giant_collision_bonus_for_this_turn_only`、`test_mastery_scales_the_treant_adjacent_heal_and_the_elemental_burst` |
| 武器技 −20%、普攻與法術不受影響 | `test_mastery_cuts_weapon_skill_damage_by_twenty_percent_but_not_basic_attacks`、`test_mastery_does_not_touch_spells` |
| 重播一致 | `test_a_battle_with_the_mastery_and_form_rotation_replays_identically`；CLI：`trpg battle --map open_plain --ally-build build_form_mastery --seed 3` → `replay`：「重播驗證通過：122 個動作、332 個事件，最終狀態一致」 |
| 開局不顯示形態 | `test_table_has_the_twelve_keywords_in_order`（`start_ids() == KEYWORDS`） |
| 嫁接 | `test_bridge_can_graft_form_as_a_user_only`、`test_evolution_content_schema_rejects_bad_templates` |
| 池檢查（先標記） | `test_pools_24c.py`：`short == {"form": 0}`；`test_keywords.py`：`EXTRA_KEYWORDS`、`pools["form"] == ()` |

## 驗收指令

| 指令 | 結果 |
|---|---|
| `pytest -n 8 tests/engine tests/content tests/narrative` | 只有 `test_summons_e1`（十個關鍵字假設）失敗，已修；該檔重跑通過 |
| `pytest -n 6 tests/skillgen tests/llm tests/sim` | 2218 passed、1 skipped |
| `pytest -n 4 tests/roguelite tests/api` | 468 passed |
| `-m "slow or not slow" tests/cli --timeout=3000` | 快照／預算測試分批跑通過；`llm_propose_mock` 快照因關鍵字清單變 12 個而重產；`cli_output_hashes.json` 重產 |
| `corepack pnpm -C client test` / `build` | 111 files、1066 tests passed／建置通過 |
| `ruff check`、`ruff format --check`、`mypy` | 通過 |
| 重播 | `trpg battle replay`：122 個動作、332 個事件，最終狀態一致 |

**卡住的點**：第一次把 engine＋content＋skillgen＋roguelite＋api＋sim＋llm 合在一個 `pytest -n 8` 時，xdist 出現 `node down: Not properly terminated` 與 INTERNALERROR。原因有兩個：(1) 跑測試時我同時改檔造成 xdist 收集錯亂；(2) 真正的問題是隨機組合器被要求做關鍵字 `form` 時白試 300 次（候選產生器、開局測試會挑到所有關鍵字），耗時超過單測 300 秒被殺。解法：`KeywordDef.composable: false`（形態設 false），組合器立刻 `ComposeError`；之後分批重跑全過。沒有跑 `scripts/check.py` 與 `lint-imports`、`tests/sim` 的慢速全量。

## 待 PM 決定

1. 形態池現況：1 階起始技能 0、主動利用者 0；已用 `start_hidden` 與測試標記（`EXTRA_KEYWORDS`、`short == {"form": 0}`）保守處理，3J-4 補齊後需移除。
2. 隨機組合器不產生 `in_form`，所以指定關鍵字 `form` 的組合會 `ComposeError`（候選產生器已會略過）；3J-4 是否要支援。
3. 進入獎勵 ×1.5 不放大隱蔽回合數（捨去後不變）；`FormState` 多了 `entry_permille` 欄位。
4. 化形專精的預算點數（`form_upkeep_per_100`、`form_entry_per_100` 各 200、`uses.weapon_skills` 10）是反推初值，需平衡階段模擬。
5. `weapon_skills` 套用對象新增（只給 `damage_permille`）；武器技 −20% 不含普攻與藉機攻擊。
6. 前端除關鍵字顏色外，另加了裝備小圖樣（`gearIcon.ts` 的 `form` case，裝備外觀測試要求關鍵字清單一致）與條件圖示（`skillParts.ts` 的 `in_form` 爪痕）；沒碰紙娃娃、形態、召喚物畫法。
7. 與 3J-2 合併時：`LOG_FORMAT`（都用 `/80`）、技能數與快照、`skill_icons.json`／`glossary.json` 需重產。
8. 玩家端說明（glossary）的條件說明沿用 `description_zh`（含英文參數名），同既有條件做法。

## 複雜度類 noqa

沒有新增（`C901`、`PLR0911`、`PLR0912`、`PLR0915` 都沒有）；兩處 `PLR0911` 以拆分 helper 解決。
