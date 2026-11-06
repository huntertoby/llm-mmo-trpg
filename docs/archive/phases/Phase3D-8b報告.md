# Phase 3D-8b 報告：復活、技能內的擊殺時效果、定時炸彈

## 1. commit

| commit | 內容 |
|---|---|
| f2bc797 | 內容層：原語 `revive`、`delayed_damage`；傷害效果的 `on_kill`（專用效果 `refund_ap`、`refund_cooldown`）；狀態 `time_bomb`；預算規則、驗證（復活每場一次或冷卻 ≥ 4）、骨架（aura 核心加 `revive`、control 核心加 `delayed_damage`）、AI 數值、核心規則 `revive_landing_radius`；3 個示範技能；`build_healer` 換入返魂術、新 `build_bomber`；相關測試 |
| 38972ba | 引擎：復活、擊殺時效果、定時炸彈（倒數、爆炸、倒下即爆）；事件、戰鬥紀錄文字、視圖欄位、環境預告的炸彈、AI 評分；`test_revive.py`（24）、`test_on_kill.py`（17）、`test_time_bomb.py`（25） |
| 44447fc | API：預覽的 `bombs`／`revives`、視圖的 `revivable`／`blast_radius`、環境預告的 `bombs`；`LOG_FORMAT` `/29` → `/30`；OpenAPI 與 `schema.d.ts`；CLI 快照；`test_revive_bomb_api.py` |
| 本次前端 commit | 網頁：倒地標記、炸彈倒數徽章、預覽的炸彈／復活說明與格子標記、環境預告標記；vitest |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 C 復活

```yaml
- {type: revive, hp_permille: 300}     # 100–1000；形狀 single、對象友方
```

- 目標必須是射程與視線內、**倒下**的友方（`shape: single`；候選與合法性：`engine/skills/revive.py`）。倒下的單位本來就留在 `units`、保留位置、不占格子（`unit_at` 只看存活者），沒有改動。
- 站回原位置；原格被占用、不能站立或是致命地形時，站到 `core.revive_landing_radius`（初值 2，曼哈頓）格內最近的空格，距離相同依 `(y, x)`；都沒有則技能不能施放（`revive_target_problem` 回傳原因，候選列舉也不列）。
- 每個單位每場最多一次（`UnitState.revived`）；召喚物（`is_summon`）不能被復活；撤離、已消失的不是目標。HP ＝ 最大 HP × n‰（至少 1）。
- 回到先攻順序原本的名次（先攻值，再比基礎敏捷，平手排在同值者之後），所以不一定馬上行動；倒下時移除的姿態、嘲諷、陷阱、區域、召喚物都不恢復。
- 事件 `unit_revived`（單位、施放者、技能、HP、站的格子與倒下的格子）。
- 驗證：技能必須 `uses_per_battle: 1` 或冷卻 ≥ `rule_rewrite_min_cooldown`（4；違規碼 `cap.revive_cost`）；schema：主動技能、形狀 `single`、每技能一個、其餘效果必須 `affects: self`；稀有度結構型（rare）。
- 預算：`revive_base_points`（6）＋ `hp_permille` × `revive_hp_point_permille`（10‰）。

### 2.2 F 擊殺時效果

```yaml
- type: damage
  dice: 3d6
  element: fire
  on_kill:
    - {type: refund_ap, amount: 1}
    - {type: refund_cooldown}
```

- `on_kill` 1–2 個，只有 **主動技能自己的傷害效果** 可以用（不能在賭注分支、失手反噬、`then`）。類型：`refund_ap`（`amount` 1–2）、`refund_cooldown`（本技能冷卻歸零，技能必須有 `cost.cooldown`）、`heal`、`shield`、`apply_status`（一般原語，對象一律是施放者）。`refund_ap`／`refund_cooldown` 是 **只能放在 `on_kill` 裡** 的專用效果，不是 `skill_primitives.yaml` 的原語、不是改寫規則型（不佔 `max_rule_rewrite`、不受「每輪被給一次 AP」限制，`engine/refunds.py`）。
- 結算：該傷害效果（含連鎖）讓施放者造成傷害的敵人倒下時，對施放者結算；一個效果讓多個敵人倒下也只結算一次；施放者自己倒下則不結算。AP 返還不超過 `ap_cap`，沒有實際增加時不發事件（`ap_refunded`）；冷卻歸零發 `skill_cooldown_changed`（`remaining: 0`）。
- 預算：on_kill 各效果的點數 × `on_kill_expected_permille`（300‰）；`refund_ap` 每點 AP 6 點（`refund_ap_points`）、`refund_cooldown` ＝ 冷卻回合 × `restore_cooldown_points`（3）。預算報表多一列 `on_kill`。

### 2.3 H 定時炸彈

```yaml
- {type: delayed_damage, dice: 3d6, element: fire, rounds: 2, radius: 1}
```

- 命中的敵方目標（自動套用，不擲抵抗）得到狀態 `time_bomb`（減益，`expires: never`）。`StatusInstance.remaining` 是倒數（環境回合）、`source_id` 是施放者、新欄位 `StatusInstance.skill_id` 指向技能（爆炸的骰子、元素與半徑取自技能的 `delayed_damage` 效果）。已有炸彈的目標不再附加（`effect_fizzled`：`already_bombed`）。
- **倒數**：每次環境回合（`run_environment` → `bombs.tick_bombs`，排在持續區域之後）−1，事件 `bomb_ticked`；歸零時在攜帶者 **當下位置** 爆炸（`bomb_blast` 效果 → `bomb_exploded` → 觸發函式結算）。`rounds: 2` ＝ 施放後第 2 次環境回合爆炸。
- **爆炸**：半徑（曼哈頓）內所有存活單位（敵我不分，含施放者與攜帶者）各受 `dice ＋ 縮放屬性 × 0.5` 的傷害（`cause: explosion`，自動命中、不暴擊、無格擋；縮放屬性取施放者基礎屬性），非物理元素讓每一格被元素觸及一次（點燃油、融冰……）。
- **倒下即爆**：`unit_downed` 的觸發函式——攜帶者倒下時拆下狀態（原因 `downed`）並在倒下位置立即爆炸（攜帶者已倒下，不算受傷者）。炸彈炸倒另一個攜帶者時，後者也立即爆炸（連鎖，測試涵蓋）。
- **淨化**移除（`time_bomb` 非有益）；**驅散不移除**（polarity 為 debuff，測試 `dispelled_buffs == []`）。
- **環境預告**：`Telegraph.bombs`（單位、位置、倒數、半徑、波及格子、`explodes`）；下一次環境回合會爆炸時 `changes` 多 `bomb_exploded`（帶格子）與波及者的 `unit_damaged`；預告事件與實際環境回合逐筆相同（測試）。CLI「環境預告」與 API 帶中文說明。
- 預算：骰子平均 ×（`delayed_damage_base_targets_permille` 1000 ＋ 半徑 × `delayed_damage_radius_targets_permille` 400）÷ 1000。

### 2.4 示範技能與 build

| 技能 | 機制 | 預算比例 | 裝備 |
|---|---|---|---|
| 返魂術 `skill_resurrection`（T1 rare、aura、AP 1、法力 8、每場 1 次） | C：射程 3，30% HP | 89.3% | build_healer（換下不死誓約） |
| 灰燼收割 `skill_ash_harvest`（T1 rare、strike、法術、AP 2、冷卻 2） | F：3d6 火焰，擊殺返還 1 AP ＋ 冷卻歸零 | 89.5% | build_bomber |
| 定時炸彈符 `skill_time_bomb_rune`（T2 rare、control、AP 2、冷卻 2） | H：3d6 火焰、2 輪、半徑 1 | 72.3% | build_bomber |

- `build_healer` 的主動欄位已滿（6）：返魂術換下不死誓約。新增 **`build_bomber`（第 18 個 build，定時炸彈流）**：定時炸彈符、灰燼收割、寒鎖、瞬移、不死誓約（接收被換下的）、餘燼烙印。原本想把炸彈放在 `build_striker`、斬首放在 `build_gambler`，但會改變它們既有測試鎖定的 AI 行為（雷霆終結循環、賭注），所以改成新 build；斬首因此改寫成法術版「灰燼收割」。
- 三個技能的 CLI 紀錄：AI 實際會用（`trpg battle --map swamp --seed 0 --ally-build build_healer` 有返魂術；`--map dark_forest --seed 5 --ally-build build_bomber` 有收割返還與炸彈爆炸）。

### 2.5 網頁（PM 用瀏覽器驗收）

- **倒地標記**：倒下的單位畫紅色叉叉加「倒」徽章（可復活者寫「倒·復」）；單位資訊標「倒下・可復活」。
- **復活目標選取**：復活技能的合法目標由伺服器列出倒下的友方，既有的 `unitIdsAt` 本來就把倒下的單位排在同格存活者之後，點格子或滑過即可選到（原格被敵人占用時仍可選，測試涵蓋）；預覽列出「復活 X：以 N HP 站在 (x, y)（原位置被占用）」，格子標「復」。
- **炸彈**：攜帶者右下角徽章「炸N」（N ＝ 還要幾次環境回合爆炸）；單位資訊與 HUD 狀態文字「定時炸彈（還要 2 次環境回合爆炸，半徑 1 格）」；預覽列出綁上的炸彈、倒數與波及格數，並把爆炸範圍畫成橘色底；環境預告側欄與格子標記：攜帶者標倒數數字、波及範圍標「炸」，下一次環境回合就會爆炸時範圍標紅色「炸」。
- vitest：143 個（新增炸彈／復活的純邏輯、繪製模型、預覽、環境預告、點選倒下的友方）。

**重現步驟（PM）**

1. `uv run python scripts/play.py`，開始畫面選 build「治療」（build_healer）、任一地圖（例如沼澤 swamp 種子 0、或黑暗森林），開戰。
2. 隊友（標準隊友）是 AI，被打倒後會留在格子上變淡並出現紅叉與「倒·復」徽章。輪到自己時，技能列的「返魂術」（法力 8、每場 1 次）會變成可選；點選後倒地的隊友格子被紅框標出，滑過它看預覽（以 30% 最大 HP 站起來），點下去就救回；救回後「倒」標記消失，該隊友之後再倒下就不再可復活（顯示「倒下」不帶「可復活」）。
3. 炸彈：build 選「定時炸彈流」（build_bomber），開局把敵人引到射程內（定時炸彈符射程 5）；滑過目標看預覽（倒數與橘色爆炸範圍），施放（命中才綁上）後攜帶者出現「炸2」徽章，環境預告側欄寫「還要 2 次環境回合爆炸」、格子上有「炸」標記；每輪結束倒數 −1，剩 1 時爆炸範圍變紅，爆炸時範圍內的敵我都會受傷。
4. 灰燼收割：同一個 build，對低血量敵人施放並擊殺，紀錄出現「返還了 1 AP（擊殺時效果）」且技能沒進冷卻。

（我沒有用瀏覽器實機操作；前端以 `tsc`、vitest、`vite build` 與 API 層測試驗證。）

## 3. 驗收條件逐條（8.4，3D-8b）

### 驗收 1：引擎行為

| 項目 | 測試 |
|---|---|
| 復活：基本、HP、事件、先攻名次 | `test_revive_brings_a_downed_ally_back_on_the_same_tile_with_a_share_of_the_hp`、`test_the_revived_unit_returns_to_its_place_in_the_initiative_order`、`test_the_hp_is_at_least_one` |
| 射程、對象 | `test_the_target_must_be_in_range`、`test_a_standing_ally_or_a_downed_enemy_is_not_a_target`、`test_the_selections_list_only_the_downed_allies` |
| 原格被占、沒有空格 | `test_when_the_original_tile_is_taken_the_unit_stands_on_the_nearest_free_tile`、`test_ties_between_free_tiles_follow_the_fixed_order`、`test_without_a_free_tile_in_the_landing_radius_the_skill_cannot_be_cast`、`test_a_deadly_or_blocked_original_tile_also_moves_the_unit` |
| 每場一次（單位、技能）、召喚物不能 | `test_each_unit_can_be_revived_only_once_per_battle`、`test_the_skill_itself_is_limited_to_one_use_per_battle`、`test_a_summon_cannot_be_revived` |
| 倒下時移除的狀態不恢復 | `test_revive_does_not_restore_what_was_removed_when_the_unit_went_down` |
| 驗證（每場一次或冷卻 ≥ 4）、schema | `test_revive_needs_once_per_battle_or_a_long_cooldown`、`test_schema_rejects_the_wrong_shape_and_other_targets` |
| 擊殺時效果：擊殺／未擊殺／失手 | `test_a_kill_refunds_ap_and_resets_the_cooldown`、`test_no_kill_means_no_refund`、`test_a_miss_means_no_refund`、`test_a_killing_blow_from_someone_else_does_not_count` |
| 一次結算、AP 上限、一般原語 | `test_the_effect_resolves_once_even_when_several_enemies_go_down`、`test_the_refund_never_goes_above_the_ap_cap`、`test_a_full_ap_pool_produces_no_event`、`test_ordinary_primitives_apply_to_the_caster` |
| schema | `test_schema_limits_on_kill`、`test_on_kill_is_only_for_the_skills_own_damage_effect`、`test_cross_file_checks_validate_the_primitives_inside_on_kill` |
| 炸彈：附加、已有炸彈、失手 | `test_the_skill_binds_a_time_bomb_to_the_hit_enemy`、`test_a_carrier_cannot_be_bombed_again`、`test_a_miss_binds_nothing` |
| 倒數、爆炸範圍與敵我不分 | `test_the_countdown_ticks_every_environment_turn_and_then_explodes`、`test_the_blast_hurts_everyone_in_range_friend_or_foe_and_nobody_outside`、`test_the_caster_is_hurt_too_when_standing_in_the_blast`、`test_the_damage_is_the_dice_plus_half_the_scaling_attribute` |
| 移動後在新位置爆炸 | `test_the_bomb_explodes_where_the_carrier_stands_after_it_moves` |
| 目標倒下仍爆炸（含連鎖） | `test_a_carrier_that_goes_down_explodes_at_once_where_it_fell`、`test_a_blast_that_downs_another_carrier_sets_off_its_bomb_too` |
| 淨化移除、驅散不移除 | `test_cleanse_removes_the_bomb_and_nothing_explodes`、`test_dispel_does_not_remove_the_bomb` |
| 環境預告（倒數、範圍、與實際一致） | `test_the_telegraph_lists_the_countdown_and_the_blast_area`、`test_the_telegraph_matches_the_real_environment_turn_when_the_bomb_goes_off`、`test_the_real_turn_flow_counts_down_once_per_round`、`tests/api/test_revive_bomb_api.py::test_the_time_bomb_shows_in_the_preview_the_view_and_the_telegraph` |
| 元素互動 | `test_a_fire_blast_ignites_oil_on_the_surrounding_tiles` |

### 驗收 2：網頁

vitest 143 個全過（`bombs.test.ts`、`drawModel.test.ts`、`scenePreview.test.ts`、`telegraph.test.ts`、`targeting.test.ts` 的新案例）；實機重現步驟見 2.5（PM 驗收）。

### 驗收 3：示範技能、`check.py`、重播

- 三個示範技能通過驗證與預算且裝進 build：`test_the_demo_skill_is_valid_in_budget_and_equipped`（三個測試檔各一）。
- 重播一致：`test_a_battle_with_a_reviver_replays_exactly`（build_healer）、`test_a_battle_with_a_bomber_replays_exactly`（build_bomber），狀態 JSON 與事件逐一相同；狀態存讀：`test_the_state_round_trips_with_a_revived_unit`、`test_the_state_round_trips_with_a_bomb`。
- `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest、client typecheck、vitest 全部通過（「全部檢查通過」）。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_coverage.py` | `_STATUS_VIA_PRIMITIVE` 加入 `time_bomb`（由 `delayed_damage` 間接產生） |
| `tests/content/test_skill_rules_content.py` | 控場骨架核心加 `delayed_damage`、光環骨架核心加 `revive` |
| `tests/content/test_sim_builds.py` | build 數 17 → 18（新增 `build_bomber`），測試改名 |
| `tests/skillgen/test_budget.py` | 狀態點數表加入 `time_bomb: None`（只能由 `delayed_damage` 施加） |
| `tests/cli/test_budget_cli.py` | 技能數 124 → 127 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/29` → `/30` |
| `tests/cli/snapshots/cli_output_hashes.json` | 重錄 2 筆：`skills_list`、`skills_show_all`（新增 3 個技能）；戰鬥快照全部不變 |
| `tests/api/test_reactions_telegraph.py`、`tests/api/test_routes.py` | 環境預告多 `bombs`、預覽多 `bombs`／`revives` 欄位 |
| `tests/engine/test_effective_attribute.py` | `base_attribute` 的允許清單加 `revive.py::_order_index`（復活的單位回到先攻順序，與開場同一種比較） |
| `client/src/battle/fixtures/glossary.json` | 以 `/api/glossary` 重存（多了 `time_bomb` 等名詞） |
| `client/src/battle/telegraph.test.ts`、`zones.test.ts`、`testFixtures.ts` | `TelegraphOut` 多 `bombs`、`UnitView` 多 `revivable` |

## 5. 新增的複雜度 noqa

**沒有新增複雜度類（C901、PLR0911／0912／0915）noqa。** 開發中超標的函式以拆函式處理（`_check_on_kill_sub`、`_unit_pick_problem`、`_action_budgets`、`_kill_points`、`_bomb_points`）。只新增 `PLR0917`（位置參數過多）一處：`targeting._unit_pick_problem`，與同檔其他函式一致；延後匯入的 `PLC0415` 不屬於複雜度類。

## 6. `LOG_FORMAT`

`/29` → **`/30`**（本段升一次）：`revive`／`delayed_damage`／`on_kill` 與其欄位、`UnitState.revived`、`StatusInstance.skill_id`、狀態 `time_bomb`、效果 `bomb_blast`、核心規則 `revive_landing_radius`、新事件 `unit_revived`／`ap_refunded`／`bomb_ticked`／`bomb_exploded`、預算規則；舊紀錄不能由新版程式重播。

## 7. 待 PM 決定（最多 10 點）

1. **復活後的行動時機**：回到先攻順序原本的名次，名次已過的話要等下一輪才會行動（規格沒寫）。若希望「救回來就能立刻動」，改成插在施放者之後即可（類似召喚物）。
2. **落點半徑**：「最近的空格」我限制在 `revive_landing_radius`＝2 格內（規格寫「都沒有則不能施放」，若無限制幾乎永遠找得到）。落點不觸發陷阱與表面進入效果（只在下一個回合開始吃表面效果）。
3. **倒下時沒移除的狀態會留著**：復活的單位保有倒下前的減益（中毒等）；只有倒下時被移除的（姿態、以來源為依據的狀態）不恢復。是否一併清除減益？
4. **擊殺時效果的 `refund_cooldown` 與 `refund_ap` 名稱／位置**：規格只舉例；我做成只能放在 `on_kill` 裡的專用效果，並允許 `heal`／`shield`／`apply_status`（對施放者）。一個傷害效果讓多個敵人倒下只結算一次（不是每殺一個一次），避免範圍技滾雪球。
5. **示範技能改成法術版「灰燼收割」並放進新 build**：原本想做近戰「斬首」放進 `build_gambler`，但會改變該 build 既有測試鎖定的 AI 行為；炸彈同理不放進 `build_striker`。因此新增 `build_bomber`（第 18 個），`build_healer` 以返魂術換下不死誓約（移到 bomber）。3C-6 整理 build 時可合併。
6. **炸彈敵我不分、含施放者**：規格寫「目標與半徑內單位受傷」，我解讀為包含友方與施放者（這也是 AI 要避開的風險：AI 估價為「半徑內敵人數 − 友方數」，友方圍繞時不會放，測試涵蓋）。倒數在環境回合（每輪 1 次），不是目標自己的回合；`rounds: 2` ＝ 施放後第 2 次環境回合爆炸。
7. **一個目標只能帶一個炸彈**：已有炸彈時再施放為 `effect_fizzled`（`already_bombed`），不刷新也不疊加。炸彈半徑用曼哈頓（半徑 1 ＝ 十字 5 格），與光環一致、與物件爆炸（切比雪夫）不同；炸彈傷害 `cause: explosion`。
8. **預算與 AI 初值皆未經模擬**：復活 6 ＋ 1‰ 係數、炸彈預期波及 1000‰ ＋ 400‰ × 半徑、擊殺率 300‰、`refund_ap` 每點 6 點；AI 的 `revive_points` 30、`refund_ap_points` 6、`bomb_points_permille` 700。定時炸彈符落在合格區間的下緣（72.3%）。請在 `sim matrix` 後的平衡階段檢查。
9. **3-5 的影響**：復活讓「戰鬥中倒下的隊友」可以被救回；戰後仍倒下的隊友（`downed`）與「整輪固定或每場換」仍待 3-5 規格決定（`UnitView.revivable` 與 `revived` 旗標已可序列化）。
10. **沒做／限制**：組合器不產生 `revive`、`delayed_damage`、`on_kill`；炸彈不會被「換位／傳送」特別處理（炸彈跟著單位走，在當下位置爆炸）；網頁沒有為「被淨化拆除」多加提示（狀態消失即拆除）；沒有用瀏覽器實機操作（見 2.5）。

## 8. 代表性的 CLI 輸出節錄

`uv run trpg battle --map dark_forest --seed 5 --ally-build build_bomber`，第 3 輪結束的環境回合（連續的一段，未剪接；炸彈倒數歸零，波及的戰士與攜帶者都受傷，攜帶者倒下，火焰點燃草叢）：

```
  盜賊1 攻擊 標準隊友（戰士）：d20（劣勢 9、2）=2 修正 -1 熟練 +2 = 3（目標 11）→ 失手
  盜賊1 結束回合
～ 環境回合 ～
  盜賊1 的「定時炸彈」結束了
  ＊ 定時炸彈在 (4, 1) 爆炸了！（倒數歸零，半徑 1 格，火焰）
  (5, 1) 出現了火焰
  (4, 2) 出現了火焰
  草叢 (5, 1) 著火了（1 次環境回合後燒毀）
  草叢 (4, 2) 著火了（1 次環境回合後燒毀）
    標準隊友（戰士） 受到 20 點爆炸火焰傷害［骰 4+2+6］，HP 40 → 20
    盜賊1 受到 21 點爆炸火焰傷害［骰 5+2+6］，HP 18 → 0
  ＊ 盜賊1 倒下了！
  標準隊友（戰士） 獲得狀態「燃燒」（2 回合）
```
