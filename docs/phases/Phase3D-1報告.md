# Phase 3D-1 報告：連段條件 ＋ 資源互動

## 1. commit

| commit | 內容 |
|---|---|
| 3a643f0 | 5 個連段條件、狀態分類 `polarity`、`restore_resource`、`steal_buff`、事件 `resource_restored`、`status_removed` 新原因 `stolen`、預算、8 個示範技能與 build 裝備、`LOG_FORMAT` `/18`；`tests/engine/test_combo_resources.py`（43） |
| 4fcdc5f | AI：`restore_resource`、`steal_buff` 的評分與「對友方有沒有用」的便宜估計（`content/ai_profiles.yaml` 的 `rewrite`） |
| （本報告） | 報告 |

開發期間 main 上沒有其他 session 的 commit。

## 2. 交付項目

### 2.1 連段條件（規格 1.1）

`content/skill_conditions.yaml` 新增 5 條（共 10 條，`REQUIRED_CONDITIONS` 同步）：

| id | 判斷 | 參數 | harshness（初值） |
|---|---|---|---|
| `moved_this_turn` | 施放者本回合步行過（`arrive(mode="walk")` 設旗標；傳送、強制位移不算） | — | common |
| `adjacent_ally` | 施放者上下左右有存活友方（不含自己） | — | common |
| `target_isolated` | 對象單位上下左右沒有它的存活友方（對象的「友方」＝對象自己的陣營） | — | common |
| `first_round` | `state.round == 1` | — | harsh |
| `cast_tag_this_turn` | 本回合已施放過帶 `tag` 的主動技能（技能結算完才記錄，所以不含這次） | `tag` | common |

- **「本回合做過什麼」紀錄**：`UnitState.moved_this_turn: bool`、`UnitState.turn_cast_tags: tuple[str, ...]`；`start_turn` 清空、可序列化（`state_to_json` 往返測試）、`clone` 涵蓋（`test_state_clone` 通過）。
- 標籤用 `modifiers.effective_tags`（含修正規則 `add_tags`）；只記 `use_skill` 的主動施放（反應技、被動、複製技能、陷阱不記）。
- 技能層級的判斷：新增 `CASTER_CONDITIONS`（`self_hp_below` ＋ 前述四個施放者條件）——只看施放者，不要求影響範圍內有對象；`target_isolated` 與其他單位條件一樣要求範圍內至少一個符合的單位。
- 修正規則（3C-2）的 `condition` 可以用 5 個新條件（`test_a_modifier_rule_may_use_a_new_condition_but_not_for_pre_target_changes`）；「選目標前就決定」的改變（`SELF_ONLY_CHANGES`：`ap_delta` 等）**仍只能用 `self_hp_below`**，`SELF_CONDITIONS` 不變。
- `condition_text` 補上 5 條的中文（`本回合移動過`、`身旁有友方`、`目標身邊沒有友方`、`第一輪`、`本回合已施放過「tag」類技能`）。
- 預算折扣沿用 `harshness`（common 0.85／harsh 0.6，`skill_budget.yaml` 的 `condition_permille`），沒有另設係數。

### 2.2 狀態分類（規格 1.2）

`statuses.yaml` 原本只有布林 `beneficial`（淨化用）。新增 **必填** 欄位 `polarity: buff | debuff | neutral`，26 個狀態全部填值：

- buff（6）：`defending`、`guarded`、`empowered`、`hasted`、`regenerating`、`shielded`
- neutral（5）：`concealed`、`undying`、`soul_link`、`stance_fury`、`stance_bulwark`（姿態、隱蔽、不死、靈魂連結帶有來源或唯一性語意，不能被奪取）
- debuff（15）：其餘。

schema 驗證：`buff` 必須 `beneficial: true`、`debuff` 不可 `beneficial`（`test_a_status_without_polarity_is_rejected`）；`test_every_status_has_a_polarity_consistent_with_beneficial` 逐一檢查每個狀態（姿態、不死、靈魂連結必為 neutral，buff 集合固定）。

### 2.3 `restore_resource`（`src/trpg/engine/resources.py`）

- `resource: mana`：回復 `amount`（1–10），不超過上限；已滿時 `effect_fizzled`（`mana_full`）。
- `resource: cooldown`：`amount`（1–2，schema 檢查）縮短目標所有冷卻中的技能，下限 0（歸零就從 `cooldowns` 移除）；**不影響** `cost.source` 的技能，也**不影響施放中的這個技能本身**（它的冷卻才剛開始；規格沒寫，保守，見待決 #2）。每個變動技能發出 `skill_cooldown_changed`，另有一個彙總事件；沒有可縮短的技能時 `effect_fizzled`（`no_cooldown`）。
- 新事件 `ResourceRestored`（`unit_id`、`source_id`、`resource`、`amount`、`mana_after`、`skill_ids`）；紀錄文字：「回復了 N 點法力（現在 M）」「的「…」冷卻 −N」。
- 對象：`affects` 不可為 `enemies`／`all`（自己或友方）。結構型、稀有以上。
- 預算（初值，未經模擬，放 `content/skill_budget.yaml`）：法力每點 `restore_mana_point_permille: 700`‰ 點、冷卻每回合 `restore_cooldown_points: 3` 點（新 `budget_basis: restore_resource`）。

### 2.4 `steal_buff`

- 對象為敵方（`affects` 只能 `enemies`，需命中）。從目標的 `polarity: buff` 狀態中取「剩餘回合最長（永久視為最長）、同長依狀態 ID 排序」者，移除（`status_removed`，原因新增 `stolen`），並以 **相同剩餘回合與數值（`amount`，護盾量）** 對施放者 `apply_status`（施放者已有同狀態時沿用「取較長者」的既有規則）。目標沒有增益時 `effect_fizzled`（`no_buff`）。
- 結構型、稀有以上，固定 4 點（`budget_basis: fixed`）。
- 這個結果事件順序：因為效果依對象 ID 排序，紀錄中施放者的 `獲得狀態` 會出現在目標的 `被奪走了` 之前（見第 7 節節錄；純顯示順序，結算順序是先移除再施加）。

### 2.5 其他

- 兩個原語都加入 `_HAND_WRITTEN_PRIMITIVES`（隨機組合器不產生，3C-6 再處理）；`aura` 骨架核心加 `restore_resource`、`control` 骨架核心加 `steal_buff`。
- `trpg.narrative.skills` 補原語的技能描述文字。
- **`LOG_FORMAT` 升為 `trpg-battle-log/18`**（本段只升一次）：單位新欄位、5 個新條件、新事件 `resource_restored`、`status_removed` 新原因 `stolen`、狀態表必填 `polarity`。

### 2.6 示範技能（8 個，皆通過預算與結構驗證、皆已裝備）

| 技能 | 稀有度 | 使用的條件／原語 | 裝備 build |
|---|---|---|---|
| 衝勢劈砍 `skill_charging_strike` | rare | 效果層級 `moved_this_turn`（第二段傷害 ×0.8） | build_guardian |
| 並肩斬 `skill_shoulder_strike` | rare | `adjacent_ally` | build_guardian |
| 獵殺落單 `skill_pick_off` | rare | `target_isolated` | build_assassin |
| 先發制人 `skill_first_strike` | rare | `first_round`（harsh，第二段傷害 ×1.2 才進得了預算區間） | build_assassin |
| 連段雷光 `skill_arc_follow_up` | rare | `cast_tag_this_turn`（tag: lightning） | build_storm |
| 專注湧流 `skill_focus_surge` | rare | `restore_resource`（mana 10） | build_support |
| 疾時之潮 `skill_quicken_tide` | rare | `restore_resource`（cooldown 2） | build_healer |
| 竊取祝福 `skill_blessing_thief` | rare | `steal_buff` ＋ 1d4 暗影傷害 | build_warlock |

裝備位置的考量：`build_striker`、`build_trapper` 的既有測試固定了技能數與 AI 戰鬥（`tests/cli/test_striker_trapper_battle.py`），而 build_push／fire／tank／ranged 的主動欄位已滿（loader 限制主動 ≤ 6），所以示範技能放在還有空位的 build（武器類型相容）。我方預設陣容與敵方都不用這些技能，所以既有 CLI 戰鬥快照沒有變。

## 3. 驗收條件逐條（規格 1.3）

| # | 結果 | 證據 |
|---|---|---|
| 1 | 5 個條件各有成立／不成立測試 | `test_moved_this_turn_needs_a_walk`、`test_being_pushed_or_teleported_does_not_count_as_moving[forced／teleport]`、`test_the_turn_record_is_cleared_when_the_next_turn_starts_and_serializes`、`test_adjacent_ally_needs_a_living_friend_beside_the_caster`（斜角、倒下、敵人相鄰皆不成立）、`test_adjacent_ally_as_an_effect_condition`、`test_target_isolated_looks_at_the_targets_own_neighbours`、`test_target_isolated_as_a_skill_gate`、`test_target_isolated_ignores_the_dead`、`test_first_round_only_holds_in_round_one`、`test_cast_tag_this_turn_does_not_count_the_cast_itself`、`test_cast_tag_this_turn_counts_earlier_casts_with_the_tag`、`test_cast_tag_this_turn_needs_the_matching_tag`、`test_cast_tag_requires_the_tag_parameter` |
| 2 | `restore_resource` 兩種、上限、源力技能不受影響；`steal_buff` 有／無增益、選擇順序、分類完整 | `test_restore_mana_is_capped_by_max_mana`、`test_restore_mana_adds_the_full_amount_when_there_is_room`、`test_restore_mana_when_full_fizzles`、`test_restore_cooldown_skips_source_skills_and_the_casting_skill`（用傳說「鏡像施法」驗證源力技能不受影響）、`test_restore_cooldown_without_cooling_skills_fizzles`、`test_restore_resource_can_target_an_ally`、`test_restore_resource_schema_rejections`（5 個）、`test_steal_buff_moves_one_buff_with_its_remaining_rounds`、`test_steal_buff_picks_the_longest_remaining_then_status_id`、`test_steal_buff_prefers_a_permanent_buff`、`test_steal_buff_keeps_the_shield_amount`、`test_steal_buff_without_a_buff_fizzles_and_ignores_debuffs_and_neutral_statuses`、`test_steal_buff_cannot_target_allies_or_self`、`test_every_status_has_a_polarity_consistent_with_beneficial` |
| 3 | 每個條件與原語至少一個手寫技能；`check.py` 全過；重播一致 | `test_every_new_mechanic_has_an_equipped_hand_written_skill`、`tests/content/test_coverage.py`（允許清單維持為空）；`test_demo_battles_replay_exactly[4 個 build]`；`test_the_ai_uses_the_resource_skills_in_a_real_battle`；`uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest、client typecheck、vitest（92）全部通過；`trpg battle --map open_plain --ally-build build_warlock --seed 1 --log-json` → `battle replay`：「重播驗證通過：77 個動作、275 個事件」 |

AI 使用紀錄（`build_allies`＋`default_lineup`，4 張地圖 × 種子 0–4 ＝ 20 場，腳本在 scratchpad，不入庫）：

| build | 技能使用次數 |
|---|---|
| build_assassin | 獵殺落單 13、先發制人 4 |
| build_storm | 連段雷光 11 |
| build_support | 專注湧流 28（法力回復 28 次） |
| build_healer | 疾時之潮 20（冷卻縮短 20 次） |
| build_warlock | 竊取祝福 11（奪取成功 6、無增益而落空 5） |
| build_guardian | 並肩斬 1、衝勢劈砍 **0** |

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_statuses_content.py`、`tests/content/test_battle_content.py` | 直接建構 `StatusDef` 的測試補上必填的 `polarity` |
| `tests/content/test_skill_rules_content.py` | 骨架核心原語清單加入 `steal_buff`（control）、`restore_resource`（aura） |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/17` → `/18` |
| `tests/cli/test_budget_cli.py` | 技能總數 82 → 90 |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 兩筆重錄（新增 8 個技能）；戰鬥類快照沒有變 |

## 5. 新增的複雜度 noqa

無（`_base_points` 既有的 `PLR0911` 不變；為了不增加分支，原語的特殊預算算法改成 `_SPECIAL_BASES` 派發表；`condition_met`、`_rewrite_gains`、`_rewrite_supports` 也拆成小函式或表）。

## 6. 待 PM 決定

1. **狀態分類欄位**：新增必填 `polarity`（buff／debuff／neutral），沒有直接沿用 `beneficial`，因為姿態、隱蔽、不死、靈魂連結「有益」但不該被奪取或驅散。3D-8a 的 `dispel` 可直接用同一欄位。有意見再改。
2. **`restore_resource` 的冷卻不縮短「施放中的技能自己」**（規格沒寫；與 `reset_cooldown` 一致）。
3. **`cast_tag_this_turn` 只記主動施放**（不含反應技、被動、複製技能的內層施放、陷阱）；標籤含修正規則加上的標籤。
4. **`moved_this_turn` 只看 `walk`**：站起來（`unit_stood_up`）、傳送、被推都不算；衝鋒（3D-2 的 `dash`）要不要算「主動移動」留到 3D-2 決定（建議算）。
5. **`target_isolated` 的「友方」是目標自己的陣營**，所以目標身旁站著施放者的隊友（目標的敵人）仍算落單；倒下或撤離者不算。
6. **預算初值**：條件沿用 common／harsh 折扣；`restore_resource` 法力每點 0.7 點、冷卻每回合 3 點；`steal_buff` 4 點。`先發制人`（harsh 條件）要把加成傷害調到 ×1.2 才進入預算區間，顯示 `first_round` 的折扣（×0.6）偏重，平衡階段看。
7. **衝勢劈砍幾乎不被 AI 使用**（20 場 0 次）：AI 對 `moved_this_turn` 沒有「先走再打」的規劃（預覽只看當下狀態），守護者 AI 很少主動移動。屬 AI 規劃問題，3D-2 的 `dash` 之後再看是否需要「先走位再施放」的評分。
8. **`steal_buff` 事件順序**：紀錄中施放者的「獲得狀態」會顯示在目標的「被奪走了」之前（效果依對象 ID 排序執行，結算上是先移除再施加）。純顯示順序，要整理的話放 3C-6 紀錄文字。
9. **組合器不產生這兩個原語與新條件**（`restore_resource`、`steal_buff` 在 `_HAND_WRITTEN_PRIMITIVES`；`skill_composer.yaml` 的條件清單沒動），留到 3C-6 收尾。
10. **示範技能的裝備位置**是「有空位的 build」，不是主題最合適的 build（build_push／fire／tank／ranged 主動欄位已滿）；3C-6 整理 build 時再搬。

## 7. 代表性 CLI 輸出（`trpg battle --map open_plain --ally-build build_warlock --seed 1`，原樣擷取連續行 66–76）

```
— 術士英雄 的回合（AP 3，移動 5，法力 40/40）
  術士英雄 從 (0, 3) 移動到 (3, 3)（消耗 3 移動）
  術士英雄 施放「毒霧」（AP 2，法力 10，冷卻 3 回合）→ 影響 9 格
  術士英雄 以「毒霧」攻擊 盜賊頭目：d20=9 修正 -1 熟練 +2 = 10（目標 11）→ 失手
  術士英雄 以「毒霧」攻擊 盜賊1：d20=9 修正 -1 熟練 +2 = 10（目標 11）→ 失手
  術士英雄 以「毒霧」攻擊 盜賊弓手：d20=1 修正 +0 熟練 +2 = 3（目標 11）→ 自然 1，失手
  術士英雄 施放「竊取祝福」（AP 1，法力 5，冷卻 2 回合）→ 影響 1 格
  術士英雄 以「竊取祝福」攻擊 盜賊頭目：d20=20 修正 -1 熟練 +2 = 21（目標 11）→ 自然 20，暴擊！
  術士英雄 獲得狀態「防禦」
  盜賊頭目 的「防禦」被奪走了
    盜賊頭目 受到 13 點暗影傷害［骰 2+3］，HP 80 → 67
  術士英雄 結束回合
```
