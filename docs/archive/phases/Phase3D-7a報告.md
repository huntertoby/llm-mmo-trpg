# Phase 3D-7a 報告：賭博型技能（賭注 ＋ 失手反噬 ＋ 預覽顯示機率與兩種結果）

## 1. commit

| commit | 內容 |
|---|---|
| 1cb4de9 | 內容層：原語 `gamble`、分支專用的 `damage_multiplier`／`self_damage_of_hit`、`cost.on_miss`；schema 與跨檔案檢查（硬控、跳過回合、持續傷害狀態不能當反噬）；預算（期望值、自傷折合、變異加成）；自動加標籤 `gamble`；示範技能血祭重擊、孤注一擲；`build_gambler`；schema／預算測試 |
| 72f5cae | 引擎：賭注擲骰與分支結算、傷害倍率、自傷、失手反噬、反噬上限（`cause: backlash`）；事件 `GambleRolled`、`BacklashTriggered` 與紀錄文字；引擎測試 |
| 346e317 | 預覽：`Preview.gamble`（兩個分支各自的完整預覽）、`miss_notes`；AI：期望值評分、失手反噬成本、低血量保護；`ai_profiles.yaml` 的 `gamble:` |
| 3575d7c | 技能文字：卡片的賭注說明、代價的失手反噬說明；文字測試 |
| 625e628 | 修正：賭注的對象是施放者，不讓技能能選自己當單體目標（網頁預覽驗證時發現） |
| 0e2fad5 | 網頁：`PreviewOut.gamble`／`miss_notes`、OpenAPI 與 `schema.d.ts` 重產、`gamble.ts`、vitest、API 測試 |
| 074662b | `test_routes` 預覽回應的欄位集合加兩個欄位 |
| cfbc96b | AI 低血量決策測試與賭徒 build 的整場戰鬥重播測試 |
| f98e075 | `LOG_FORMAT` `/26` → `/27`；CLI 快照重錄 |
| a46356e | CLI 技能快照再錄一次（賭注文字更新後） |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push；只 commit 自己改的檔案。

## 2. 交付項目

### 2.1 賭注 `gamble`（A）

```yaml
- type: damage
  multiplier_permille: 1200
- type: gamble                # 必須是技能的最後一個效果，每個技能最多一個，只能用在主動技能
  chance_permille: 600        # 擲一次 d1000，≤ 600 成功
  win:  [{type: damage_multiplier, damage_multiplier_permille: 2000}]
  lose: [{type: self_damage_of_hit, self_damage_permille_of_hit: 500}]
```

- **時機**：命中判定之後、第一個效果之前擲（只用戰鬥狀態內的 `Rng.randint(1, 1000)`）；技能有對敵方的效果、卻沒有任何敵人命中時 **整個賭注不結算**（不擲骰、沒有事件）。成功分支的 `damage_multiplier` 在擲骰時決定，之後技能的傷害效果（含格擋、層數加成之後）乘上它；分支的其他效果在 `gamble` 效果自己的位置（最後）結算。事件 `GambleRolled(unit_id, skill_id, roll, chance_permille, success)`。
- **分支**：`win`、`lose` 各 0–2 個效果（至少一邊有效果），類型只能是 `damage`、`heal`、`shield`、`apply_status`、`damage_multiplier`、`self_damage_of_hit`；可寫 `affects: self`（對施放者）或對敵方。每個分支最多一個 `damage_multiplier`、一個 `self_damage_of_hit`；兩者都需要技能有傷害效果。對敵方的分支效果需要技能本身有對敵方的效果（有命中判定可以依據）。
- **自傷**：`self_damage_of_hit` ＝ 這次施放對敵人造成的傷害（扣掉護盾吸收）× n‰，無條件捨去、至少 1；對施放者自己的傷害（含 `affects: self` 的 `damage` 與失手反噬的傷害）一律 `cause: backlash`。
- **反噬上限**：引擎層 `backlash` 傷害最多讓目標剩 1 HP（護盾先吸收）；schema 層 `apply_status` 對施放者自己的狀態不能是硬控（`control_group: hard`）、會跳過回合（`skip_turn`）或有回合開始持續傷害（`on_turn_start_damage`；由 `Ruleset.unsafe_backlash_statuses()` 從狀態表推導，不寫死 ID）。
- **標籤**：帶賭注或失手反噬的技能自動加 `gamble`（`SkillDef` 驗證後附加，YAML 不必寫）。
- **隨機組合器不產生**：`gamble` 列入手寫專用原語。

### 2.2 失手反噬 `cost.on_miss`（C）

```yaml
cost:
  mana: 3
  cooldown: 1
  on_miss:
    - {type: apply_status, status: prone}
```

- 1–2 個效果，類型只能是 `damage`、`apply_status`，對象固定是施放者自己（省略 `affects` 或寫 `self`）；只有主動技能可以有。
- **規則**：這次施放沒有命中任何敵人（含自然 1）時，先發 `BacklashTriggered`，再對施放者結算反噬效果；有任何敵人被命中就不結算。被動、陷阱與複製技能（`copy_skill`，不付代價）不適用。

### 2.3 預算（`content/skill_budget.yaml`，初值，未經模擬）

- 期望值：`gamble` 的點數 ＝ 成功率 × `win` ＋ 失敗率 × `lose`。`damage_multiplier` ＝ 同技能傷害點數（含形狀倍率）×（倍率 − 1）；`self_damage_of_hit` ＝ 傷害點數 × n‰，並計為負點數；對施放者的有害效果（自傷、非增益狀態）折合 `gamble_self_harm_permille`（500‰）後計為負點數；對自己的治療、護盾、增益照正常算。
- `cost.on_miss` 是效果列表最後一列（負點數）：反噬點數 × 自傷折合 × `gamble_on_miss_rate_permille`（300‰，預估未命中的比例）。
- **變異加成**：`gamble_variance_bonus_permille`（1100‰）乘在可用預算（AP 係數）上，`trpg skills budget` 的係數名稱顯示「AP 係數 × 變異加成 1100‰」。
- 示範技能：血祭重擊 73.1%、孤注一擲 74.1%（合格區間 70–100%）。

### 2.4 預覽

- 引擎 `Preview.gamble: GambleInfo(chance_permille, branches=(win, lose))`；每個分支 `GambleOutcome` 含機率、`multiplier_permille`、施放者自傷（最少／最多）、獲得的狀態、回復的 HP，以及強制該分支的完整 `Preview`（傷害範圍已含倍率）。預覽 **強制** 分支（`Ctx.gamble`），不消耗亂數；`Preview` 其餘欄位只算賭注以外的效果。`Preview.miss_notes` 列失手反噬（預覽模擬一律命中，反噬不在其他欄位）。
- API：`PreviewOut.gamble`（`chance_permille`、兩個 `GambleBranchOut`：`permille`、`multiplier_permille`、`targets`、`self_damage_min/max`、`self_statuses`、`self_healed_min/max`）、`PreviewOut.miss_notes`。
- 網頁（`client/src/battle/gamble.ts`）：預覽面板多一行「賭注（命中後擲 d1000）：60%：傷害 ×2（目標 6–24）｜40%：你受 1–6 傷害」，其下每個分支各列每個目標的傷害範圍（「成功（60%）：盜賊2 傷害 6–24」）；失手反噬一行「失手時：你獲得「倒地」」。技能卡片：效果列「賭注（命中後擲 d1000）——60%：本次傷害 ×2｜40%：你受到本次傷害的 50%（不致命）」，代價多一段「失手（含自然 1）時：你獲得「倒地」」。

### 2.5 AI（`trpg.engine.ai.gamble`、`content/ai_profiles.yaml` 的 `gamble:`）

- 賭注：對兩個分支的預覽各自評分，依分支機率加權（自傷由既有的 `friendly_fire` 權重計入）。
- 失手反噬：另外扣「未命中任何敵人的機率 × 反噬的價值」（傷害用 `friendly_fire` 權重，狀態用 `status_values`、沒列出的用 `status` 權重）。
- 低血量：施放者 HP < 最大 HP × `hp_floor_permille`（初值 300‰）時，反噬可能對自己造成傷害的賭博技能（失敗分支或失手反噬有自傷、`self_damage_of_hit`）正分乘 `low_hp_permille`（100‰）；負分不變。只有狀態反噬（例如倒地）的技能不受影響。
- 結果（`trpg battle --ally-build build_gambler`，open_plain 種子 1–4、swamp 種子 1–3）：兩個技能都會被使用；血祭重擊用得較少（法力 4、冷卻 2、自傷由 `friendly_fire` 扣分）。

### 2.6 示範技能與 build

| 技能 | 機制 | 數值（初值） | 預算 |
|---|---|---|---|
| 血祭重擊 `skill_blood_sacrifice`（稀有、打擊） | 賭注 | 傷害 ×1.2；60%：本次傷害 ×2｜40%：你受到本次造成傷害的 50% | 73.1% |
| 孤注一擲 `skill_all_in`（稀有、打擊） | 失手反噬 | 傷害 ×1.8；失手（含自然 1）時你倒地 | 74.1% |

`build_gambler`（賭徒／狂戰士流，新增第 16 個 build）：血祭重擊、孤注一擲、捨身突刺、狂怒姿態、嗜血（被動）、悲憤（反應）；單手劍、STR 16、HP 56。3C-6 再整理。

## 3. 驗收條件逐條（7.3，3D-7a）

### 驗收 1：賭注成功／失敗、未命中不結算、`GambleRolled`；失手反噬：未命中結算、命中不結算、自然 1

`tests/engine/test_gamble.py`（以腳本化的 `Rng.randint` 固定每一顆骰子，可以精確造出兩種結果）：

| 項目 | 測試 |
|---|---|
| 成功分支（d1000 = 600）：本次傷害加倍；失敗（601）同樣的骰子不加倍；事件欄位 | `test_the_gamble_win_branch_multiplies_the_hit_damage` |
| 失敗分支：施放者受到本次傷害的 50%、`cause: backlash`、事件順序 命中 → 賭注 → 傷害 → 反噬 | `test_the_gamble_lose_branch_hurts_the_caster_for_half_the_damage_dealt` |
| 未命中不結算（之後再擲骰會讓測試失敗） | `test_a_missed_attack_does_not_resolve_the_gamble` |
| 分支對施放者與對敵方的效果（治療、自傷、反噬原因） | `test_the_gamble_branches_may_target_the_caster_or_the_enemy` |
| 成功率符合 60%（300 個種子） | `test_the_gamble_roll_follows_the_chance_over_many_seeds` |
| 失手反噬：d20 = 1／2／5 都結算、倒地 | `test_a_missed_attack_triggers_the_miss_backlash`（參數化 3 個） |
| 命中不結算 | `test_a_hit_does_not_trigger_the_miss_backlash` |
| 自然 1 | `test_a_natural_one_triggers_the_backlash_even_against_a_defenseless_target` |
| 賭注不讓施放者成為合法目標（修正） | `test_a_gamble_does_not_make_the_caster_a_legal_target` |

### 驗收 2：反噬上限（自傷不致死、硬控在 schema 被拒）

- 引擎：`test_backlash_damage_never_kills_the_caster`（HP 2、自傷 100% → 留 1 HP）、`test_miss_backlash_damage_leaves_one_hp_and_shields_absorb_first`（失手反噬 3d6 → 留 1 HP）、`test_other_damage_is_not_capped_by_the_backlash_rule`（一般傷害不受影響）。
- schema（`tests/content/test_gamble_schema.py`）：`test_hard_control_and_damage_over_time_cannot_be_a_backlash`（stun、frozen、burning、poison、bleed 在 `cost.on_miss` 與賭注失敗分支都被拒，參數化 5 個）、`test_soft_statuses_are_allowed_as_a_backlash`（prone、slow、vulnerable、weaken、root）、`test_a_hard_control_on_the_enemy_in_a_branch_is_fine`、`test_the_unsafe_status_set_is_derived_from_the_status_table`；結構：`test_the_gamble_must_be_the_last_effect_and_unique`、`test_chance_permille_*`、`test_the_gamble_needs_a_chance_and_at_least_one_branch`、`test_each_branch_has_at_most_two_effects_of_the_allowed_types`、`test_multiplier_and_self_damage_need_a_damage_effect_and_their_value`、`test_miss_backlash_is_limited_to_two_effects_on_the_caster`。

### 驗收 3：預覽列出兩個分支的機率與結果（API 與 vitest）；AI 低血量不選會自傷的賭博技能

- 引擎預覽：`tests/engine/test_gamble_preview_ai.py::test_the_preview_lists_both_branches_with_chance_and_results`（機率 3/5、2/5、倍率 2000／1000、自傷範圍、成功分支傷害較高）、`test_the_preview_does_not_consume_randomness_or_change_the_state`、`test_a_skill_without_a_gamble_has_no_gamble_preview`、`test_the_preview_describes_the_miss_backlash`。
- API：`tests/api/test_gamble_api.py::test_the_preview_lists_both_gamble_branches`（`open_plain`、種子 2、build_gambler：血祭重擊 60%／40%、倍率 2000／1000）、`test_the_preview_of_a_plain_skill_has_no_gamble_and_the_miss_backlash_is_noted`、`test_skill_cards_list_the_gamble_and_the_miss_backlash`、`test_casting_a_gamble_logs_the_roll`。
- vitest：`client/src/battle/gamble.test.ts`（5 個：摘要「60%：傷害 ×2（目標 16–32）｜40%：你受 4–8 傷害」、沒有賭注、各種結果文字、每個目標的傷害範圍、納入 `previewLines` 與失手反噬）。
- AI：`test_a_low_hp_caster_does_not_pick_a_gamble_that_can_hurt_it`（分數）、`test_the_ai_gambles_when_healthy_but_picks_the_safe_skill_when_nearly_dead`（決策：健康時選賭注、HP 20% 時改選穩定技能）、`test_the_low_hp_penalty_only_applies_to_gambles_that_can_hurt`、`test_the_ai_scores_a_gamble_with_the_expected_value_of_its_branches`、`test_the_miss_backlash_lowers_the_ai_score`。

### 驗收 4：示範技能裝進 build；`check.py` 全過；重播一致

- 示範技能：`test_the_demo_gamble_skills_are_valid_and_tagged`（通過驗證器、標籤自動加 `gamble`）；兩個技能裝在 `build_gambler`；`tests/content/test_coverage.py` 允許清單維持為空（原語 `gamble` 由血祭重擊使用）；AI 會用（見 2.5）。
- 重播：`test_an_ai_battle_with_the_gambler_build_bets_and_replays_exactly`（open_plain 種子 5：賭注失敗一次、失手反噬一次、反噬傷害一次；`replay` 的最終狀態 JSON 與事件逐一相同）、`test_a_gamble_roll_is_reproduced_by_the_replay_state`；CLI：`trpg battle --map open_plain --seed 5 --ally-build build_gambler --log-json … ` → `battle replay`「重播驗證通過：127 個動作、331 個事件，最終狀態一致（open_plain，種子 5）。」
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（**2525 passed**）、client install／typecheck／test（**vitest 131**）—「全部檢查通過」。（最後跑了兩次：第一次只有 CLI 快照在文字更新後需要重錄。）

### 網頁預覽的重現步驟（PM 驗收用）

1. 啟動網頁（`uv run trpg serve`），新戰鬥：地圖 `open_plain`、種子 `2`、build `build_gambler`（賭徒／狂戰士流）。
2. 第 1 輪：主角（賭徒英雄，起點 (0,3)）移動到 **(3, 3)**（敵人盜賊2 在 (4, 3)，相鄰）。
3. 點技能「血祭重擊」、目標 盜賊2（右側預覽）：應看到「賭注（命中後擲 d1000）：60%：傷害 ×2（目標 6–24）｜40%：你受 1–6 傷害」，其下兩行「成功（60%）：盜賊2 傷害 6–24」「失敗（40%）：盜賊2 傷害 3–12」。
4. 點技能「孤注一擲」、目標 盜賊2：預覽最後有「失手時：你獲得「倒地」」，傷害範圍 5–18（×1.8）。
5. 技能卡片（技能列滑過）：血祭重擊的效果列有「賭注…」；孤注一擲的代價列有「失手（含自然 1）時：你獲得「倒地」」。
6. 施放血祭重擊後（命中時）戰鬥紀錄有一行「✦ 賭徒英雄 賭上了「血祭重擊」：d1000=… → 成功／失敗」；失敗時另有「受到 N 點反噬物理傷害」。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_sim_builds.py` | build 數 15 → 16（`build_gambler`） |
| `tests/cli/test_budget_cli.py` | 技能數 113 → 115 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/26` → `/27` |
| `tests/api/test_routes.py` | 預覽回應的欄位集合加 `gamble`、`miss_notes` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 2 筆：`skills_list`、`skills_show_all`（新增兩個技能與賭注／失手反噬文字）；戰鬥快照沒有改變（既有 build 的行為不變） |

## 5. 新增的複雜度 noqa

**無**（沒有新增 C901／PLR0911／PLR0912／PLR0915）。開發中四處超標都以拆函式解決：`SkillDef._check`（賭博檢查拆成 `_check_gamble`／`_check_on_miss`／`_check_gamble_effect`／`_check_branch`／`_add_gamble_tag`）、`_damage` 處理器（反噬上限抽成 `_cap_backlash`）、`_Cast.build`（`gamble` 放進 `_SIMPLE` 對應表而不是多一個分支）、`skill_budget`（係數抽成 `_action_coefficient`）。測試裡兩處延後匯入的 `PLC0415` 是避免測試模組循環匯入，不屬於複雜度類。

## 6. `LOG_FORMAT`

`/26` → **`/27`**（本段升一次）：新原語 `gamble`、`EffectSpec` 新欄位、`cost.on_miss`、`damage_dealt.cause` 的新值 `backlash`、新事件 `gamble_rolled`／`backlash_triggered`、預算規則 `gamble_*`。`/26` 的規則包沒有這些欄位，舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **「變異加成」的套用位置**：規格寫「預算以期望值計，再乘變異加成」。我把 1100‰ 乘在 **可用預算** 上（等於同樣的點數可以換到高 10% 的平均強度），不是乘在技能的點數上；兩者的合格區間等價，但 `skills budget` 的畫面顯示在「可用預算」那一列。
2. **三個預算初值**：自傷折合 500‰（對自己的有害效果只算一半價值）、失手反噬預估觸發率 300‰、變異加成 1100‰，全部未經模擬。建議 3C-6 的 `sim matrix` 後再調。
3. **`damage_multiplier`／`self_damage_of_hit` 不是 `skill_primitives.yaml` 的原語**：規格稱「專用效果」，我讓它們只能出現在賭注的分支裡（`damage_multiplier_permille`、`self_damage_permille_of_hit` 欄位），所以不會被當成一般原語使用或進入隨機組合器。
4. **自傷的基準**：`self_damage_of_hit` 取「對敵人造成的傷害（扣掉護盾吸收）」，**不**截掉超過目標剩餘 HP 的溢出（紀錄範例：目標剩 7 HP、傷害 14，自傷 7）；若要以實際扣掉的 HP 為準請告知。多目標的範圍技能是所有被打到的敵人合計。
5. **「失手」的定義**：這次施放沒有命中任何敵人（範圍技能只要有一個敵人被命中就不反噬）。被動、陷阱與複製技能不適用；反應技與被動不能帶 `cost.on_miss`／`gamble`（保守：只開主動技能）。
6. **稀有度**：`gamble` 原語最低稀有度為 rare；`cost.on_miss` 目前 **沒有** 最低稀有度限制（設計 6.17 建議 A、C 為稀有以上）。若要限制，請指定規則（例如驗證器檢查 `cost.on_miss` 需 rare 以上）。
7. **AI 的低血量規則**：只對「反噬可能造成傷害」的賭博技能生效（只有倒地之類狀態反噬的孤注一擲不受影響）；正分乘 100‰ 而不是直接排除，所以沒有其他選擇時仍可能賭。設定名稱是 `ai_profiles.yaml` 的 `gamble: {hp_floor_permille, low_hp_permille}`（規格寫的 `ai_gamble_hp_floor_permille` 即 `hp_floor_permille`）。
8. **預覽的 `damage` 等欄位不含賭注分支**：賭注技能的 `Preview.damage`／連鎖是「沒有賭注」的結果，賭注的結果在 `gamble.branches[*]`；網頁因此另列「賭注」行。預覽強制分支不擲骰，所以沒有預覽「賭注失敗且對方暴擊」之類的交叉組合（每個分支內仍有最少／最多後果兩次模擬）。
9. **骨架**：`strike` 的附帶原語加入 `gamble`，`gamble` 原語標 `harmful: true`（只為通過「附帶效果必須是有害原語」的骨架規則，實際對象永遠是施放者）。其他骨架（combo、area 等）尚未開放賭注。
10. **既有的小怪事（非本段造成）**：單體武器技在 `legal_actions` 裡除了每個目標一筆之外，還有一筆 `target_id: null` 的動作（例如碎骨重擊也有），施放後只扣代價；賭注技能照樣出現，結算時沒有敵人被命中所以不擲骰。建議之後在 3-5 或前端整理時處理。

## 8. 代表性的 CLI 輸出節錄

`uv run trpg battle --map open_plain --seed 5 --ally-build build_gambler`，第 2 輪賭徒英雄的回合（連續的一段，未剪接；賭注失敗、反噬自傷）：

```
— 賭徒英雄 的回合（AP 4，移動 5，法力 24/24）
  賭徒英雄 的「防禦」結束了
  賭徒英雄 施放「孤注一擲」（AP 2，法力 3，冷卻 1 回合）→ 影響 1 格
  賭徒英雄 以「孤注一擲」攻擊 盜賊1：d20=11 修正 +1 熟練 +2 = 14（目標 11）→ 命中
  ⟳ 盜賊1 反應：格擋（耐力 −10）
    盜賊1 受到 9 點物理傷害［骰 5］（格擋/加成 ×0.9），HP 16 → 7
  賭徒英雄 施放「血祭重擊」（AP 2，法力 4，冷卻 2 回合）→ 影響 1 格
  賭徒英雄 以「血祭重擊」攻擊 盜賊1：d20=11 修正 +1 熟練 +2 = 14（目標 11）→ 命中
  ✦ 賭徒英雄 賭上了「血祭重擊」：d1000=974（成功率 60%，要 ≤ 600）→ 失敗
    盜賊1 受到 14 點物理傷害［骰 7］（格擋/加成 ×1.2），HP 7 → 0
  ＊ 盜賊1 倒下了！
    賭徒英雄 受到 8 點反噬物理傷害（狀態 ×1.2），HP 22 → 14
  ★ 賭徒英雄 的被動「嗜血」觸發（擊倒時，深度 1），對象 盜賊1（法力 2）
    賭徒英雄 回復 14 HP，HP 14 → 28
```

同一場戰鬥稍後的失手反噬（第 3 輪）：

```
  賭徒英雄 施放「孤注一擲」（AP 2，法力 3，冷卻 1 回合）→ 影響 1 格
  賭徒英雄 以「孤注一擲」攻擊 盜賊頭目：d20=3 修正 +1 熟練 +2 = 6（目標 11）→ 失手
  ✦ 賭徒英雄 的「孤注一擲」失手了，遭到反噬
  賭徒英雄 獲得狀態「倒地」
```
