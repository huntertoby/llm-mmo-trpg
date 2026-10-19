# Phase 3D-2c 報告：直線衝撞 `charge_through`

## 1. commit

| commit | 內容 |
|---|---|
| f3e1a52 | 原語 `charge_through`（schema、選取、結算、預算、骨架）、事件 `unit_charged`、紀錄與技能文字、預覽 `charge`、AI 估計、示範技能「蠻牛衝陣」、`build_charger` 換入、`LOG_FORMAT` `/21`；`tests/engine/test_charge_through.py` 的引擎部分 |
| 61435bf | 預覽／API／紀錄文字／組合器測試；順手修正預覽事件文字的既有錯誤（見 3.5） |
| 8d2d28a | 網頁：直線路線、沿途敵人（標命中率）、終點的標記與預覽文字、vitest |
| 91fd88a | 測試：AI 會用蠻牛衝陣、含衝撞的 AI 戰鬥重播一致 |
| （本報告） | 報告 |

開發期間 main 上有玩法 PM 的 docs commit（de8a891）；我沒有 stash、reset、amend、切換分支，也沒有 push。

## 2. 交付項目

### 2.1 原語 `charge_through`

資料：`{type: charge_through, dice: 2d6, on_hit: knock_prone | push_aside}`；形狀 `ground_tile`（選終點格），**射程取形狀的 `range`**（規格寫在原語裡的 `range`，見待決 #1）。

| 項目 | 做法 |
|---|---|
| 選取 | 終點與施放者同一列或同一行、距離 ≤ 射程、地圖內、可站立（`is_standable`，致命地形、牆、`blocks_move` 物件都不行）、**沒有單位**；`legal_actions` 只列四方向直線上合法的格子（`mobility.charge_candidates`） |
| 路線 | 沿直線一格一格走，步行規則（`step_cost`：不可站立或爬升過高就擋住）。被擋住時停在擋住前；單位（敵我）不擋，但**不能停在有單位的格子**，所以停點往回退到最後一個空格；退到起點（停不下來）**整招不可施放**（保守選擇，待決 #2） |
| 沿途敵人 | 每個敵人被穿過時各擲一次命中（**依路徑順序**，不是單位 ID；事件 `attack_rolled` 照走到的順序出現）。命中：`dice` 物理傷害（不加屬性；暴擊、格擋、修正規則照常，同 `hurl_object`），還活著再依 `on_hit`：`knock_prone` 擊倒對抗（沿用 `contest`）、`push_aside` 推到路徑旁一格 |
| `push_aside` 方向 | 左手邊（行進方向的左，座標 y 向下：向東衝＝北）優先，左邊撞得到東西（牆、單位、更高的地形、地圖外）就換右邊；兩邊都不行就推左邊，照常觸發 3C-3a 撞擊（`skills/charge.py`） |
| 隊友 | 讓路：不擲命中、不受影響、不阻擋；`SkillArea.units` 只含沿途的敵人 |
| 移動 | 空格一格一格走（`MoveUnitEffect` `mode: dash`）：沿途與終點的陷阱、表面、墜落照常結算；被定身、倒地、暈眩或倒下就停下，之後的敵人不會被撞。有單位的格子跳過；敵人倒下或被推開後，那一格空了就走進去 |
| 反應 | **不觸發藉機攻擊**；算 `moved_this_turn`；觸發 `on_move` 被動（與 `dash` 一致）；定身、倒地不能施放（`skill_problem`，與 `dash`、`leap` 同） |
| schema | 只能搭配 `ground_tile`、必須是第一個效果、只能用在主動技能、與其他位移原語最多一個；其餘效果必須**明寫** `affects: self`（沿途的敵人與隊友由衝撞自己處理）；`dice`、`on_hit` 必填 |
| 事件 | 新增 `unit_charged`（`unit_id`、`target`＝選的終點、`path`＝依序經過的格子，含起點與有單位的格子，終點是實際停下的格子）；失敗時 `effect_fizzled` 原因 `charge_no_path`（只在選取後狀態改變的極端情況） |
| 預算 | 新 `budget_basis: charge_through`：（`dice` 平均 ＋ `on_hit` 點數）× `charge_through_expected_targets_permille`（初值 1500‰，即 1.5 個敵人）；`knock_prone` 點數取該原語的 `base_points`（3）、`push_aside` 取 `push` 的（2）。2d6 ＋ 擊倒 ＝ （7＋3）× 1.5 ＝ 15 點。結構型、稀有以上、放進 `displace` 骨架核心；組合器不使用（只給手寫技能） |
| 紀錄文字 | `➤ X 直線衝撞：(a)→(b)→…`（被擋住時加「（被擋住，停在 …）」）；沿途每個敵人的命中、傷害、擊倒照既有格式逐段出現 |

### 2.2 預覽、API、網頁

- `Preview.moves` 新增 `kind: charge`（`path` 為依序經過的格子，含起點、有單位的格子與停下的格子，`other_id` 為 `None`）；API 的 `MoveOut.kind` 本來就是字串，**不需要改 OpenAPI**。沿途敵人在 `Preview.targets`／`PreviewOut.targets`（命中率、暴擊率、傷害範圍、`knock_permille`）。
- **命中率以「經過那個敵人時」施放者所在的格子計算**（`preview._positions_at_roll`）：衝撞中途位置會變，高度差、掩護都以實際出手的格子為準（測試 `test_the_preview_hit_chance_uses_the_tile_the_caster_passes_from`：從起點算是 50%，實際 60%）。
- 網頁：路線畫點、會被撞到的敵人格畫框並標命中率（`charge_hit`）、終點標「衝」；預覽文字「衝撞：X 沿 (a)→(b)→… 直線衝過去；沿途會撞到 A（命中 60%）、B（命中 65%），命中者受傷並可能被撞倒／推到路徑旁（隊友讓路，不會被藉機攻擊，沿途陷阱與表面照常結算）」；終點被擋住時加「被擋住：選的終點是 (x, y)，實際停在 (x, y)」。
- AI：`utility._special_estimate` 對 `charge_through`：沿途敵人數 × 3 ＋ 終點的位置價值變化（沿途沒有敵人就不納入候選）；收益由預覽（每個敵人的命中率與傷害）加權。

### 2.3 示範技能與 build

「蠻牛衝陣」`skill_bull_rush`（稀有、武器技近戰、AP 2、射程 4、法力 5、冷卻 3）：`charge_through 2d6 knock_prone`，預算 **91.2%**（合格 70–100%）。名稱沒有用「破城衝撞」（3C-3a 的 `skill_battering_ram` 仍是「破城衝撞」，有測試確認）。

`build_charger` 的主動欄位已滿（6/6），**盾擊換成蠻牛衝陣**（盾擊仍在 `build_push`，覆蓋測試不受影響）。沒有新增 build。

## 3. 驗收條件逐條（2C.1）

| # | 結果 | 證據（`tests/engine/test_charge_through.py` 除非另註） |
|---|---|---|
| 1 | 直線限制 | `test_only_straight_lines_within_the_reach_are_legal`（斜向、不在線上、原地、地圖外、射程外都拒絕；列舉剛好是四方向）、`test_the_end_tile_must_be_empty_and_standable`（終點有單位、不可站立） |
| 1 | 被牆或物件擋住停下 | `test_a_wall_stops_the_charge_before_it`、`test_a_blocking_object_stops_it_too`、`test_a_too_high_step_stops_the_charge`、`test_it_cannot_be_cast_when_it_cannot_stop_anywhere`、`test_it_never_stops_on_a_unit` |
| 1 | 隊友讓路 | `test_allies_yield_and_are_not_affected` |
| 1 | 沿途每個敵人各擲命中（命中與未命中） | `test_every_enemy_on_the_way_rolls_once_in_path_order`（路徑順序、不依單位 ID）、`test_hits_and_misses_are_rolled_separately`、`test_a_hit_deals_the_dice_physical_damage` |
| 1 | 兩種 `on_hit` | `knock_prone`：`test_hits_and_misses_are_rolled_separately`（成功）、`test_knock_prone_rolls_a_contest_and_can_fail`（對抗失敗）；`push_aside`：`test_push_aside_moves_the_hit_enemy_to_the_left_side_first`、`…picks_the_right_side_when_the_left_is_blocked`、`…direction_follows_the_travel_direction` |
| 1 | 推到旁邊撞牆觸發撞擊 | `test_push_aside_into_a_wall_triggers_a_collision`（`Collided`、`DamageDealt cause=collision`、施放者照樣穿過） |
| 1 | 不觸發藉機攻擊 | `test_the_charge_does_not_provoke_opportunity_attacks`（同一起點用走的會觸發） |
| 1 | 落點互動、`moved_this_turn`、定身倒地不能施放 | `test_a_trap_on_the_way_triggers_and_a_rooting_trap_stops_the_charge`、`test_the_surface_on_the_end_tile_applies`、`test_charging_counts_as_moving_this_turn`、`test_it_cannot_be_cast_while_rooted_or_prone`、`test_an_enemy_who_falls_leaves_the_tile_open` |
| 1 | schema 與資料 | `test_charge_through_must_be_the_first_effect`、`test_the_other_effects_must_be_self_only`、`test_charge_through_needs_the_ground_tile_shape_and_the_parameters`、`test_it_is_an_active_only_self_move_and_at_most_one`、`test_the_demo_skill_is_valid_rare_and_equipped_in_build_charger`；`trpg skills budget skill_bull_rush`（91.2% 合格）、`trpg content check`（97 個技能通過） |
| 2 | 預覽顯示路徑與被撞敵人（API 與 vitest） | 引擎：`test_the_preview_lists_the_route_and_each_enemy_with_the_hit_chance_at_that_spot`；API：`tests/api/test_charge_through_api.py`（`legal_actions` 只有直線終點、預覽的 `moves`／`targets` 命中率 600‰、送出後依路徑順序擲命中且主角停在 (7, 4)、不在線上的終點被拒）；vitest：`scenePreview.test.ts` 的 "charge-through previews"（4 個）。**PM 瀏覽器驗收見第 7 節** |
| 3 | AI 使用紀錄 | `trpg sim maps --seeds 5 --ally-build build_charger`：**蠻牛衝陣 35 次**（10 張地圖 × 5 種子 ＝ 50 場；swamp 8、narrow_halls 5、oil_depot 5、open_plain 4、ruined_fort 4、bridge_chasm 3、lava_crossing 3、cliff_outpost 2、frozen_lake 1、dark_forest 0）；測試 `test_the_ai_charges_along_the_line_the_enemies_stand_on`、`test_the_ai_does_not_charge_when_nobody_is_on_the_line`、`test_the_ai_uses_the_charge_in_real_battles` |
| 3 | `check.py` 全過、重播一致 | `uv run python scripts/check.py`：ruff、format、mypy、lint-imports、pytest（2210 passed）、client typecheck、vitest（110 passed）全部通過；重播：`test_an_ai_battle_with_charges_replays`（bridge_chasm 種子 2，一次撞到兩個敵人）「重播驗證通過」 |

### 3.5 順手修正的既有錯誤（需要 PM 知道）

預覽的 `AttackRolled` 是強制結果、只有一顆骰（`rolls` 長度 1），但單位有優勢時（目標倒地、隱蔽等）`narrative.events._attack` 讀 `rolls[1]` 會 `IndexError`，API 預覽（`event_out` 描述 `min_events`）因此回 500。**普攻倒地的敵人時就會發生**（與本段無關，既有錯誤）；衝撞的擊倒流程讓它更容易遇到，所以我改成 `len(rolls) == 1` 時只顯示 `d20=自然骰`，測試 `test_previewing_a_prone_target_describes_the_single_forced_roll`。

## 4. 修改既有測試的原因

| 測試 | 原因 |
|---|---|
| `tests/content/test_skill_rules_content.py` | `displace` 骨架核心多了 `charge_through` |
| `tests/cli/test_budget_cli.py` | 技能總數 96 → 97 |
| `tests/cli/test_battle_cli.py`、`tests/cli/test_skills_cli.py` | `LOG_FORMAT` `/20` → `/21` |
| `tests/cli/snapshots/cli_output_hashes.json` | 只有 `skills_list`、`skills_show_all` 兩筆重錄（新增 1 個技能）；戰鬥類快照沒有變 |

## 5. 新增的複雜度 noqa

沒有 C901、PLR0911、PLR0912、PLR0915。`charge_route` 拆成 `_charge_line_problem`、`_charge_dest_problem` 與路線走訪；`roll_hits` 的迴圈本體抽成 `_roll_one`（原有的 `# noqa: PLW2901` 跟著搬過去，不屬複雜度類）、`_update_cooldown_delta`。

## 6. `LOG_FORMAT`

**升為 `trpg-battle-log/21`**（本段只升一次）：新原語 `charge_through`（新欄位 `on_hit`）、事件 `unit_charged`、`effect_fizzled` 的新原因 `charge_no_path`、新技能與 `build_charger` 內容；`/20` 的規則包沒有這個原語。

## 7. PM 瀏覽器驗收：「衝過兩個敵人」重現步驟

本機以 API 流程重現（同一個種子結果固定）；建立戰鬥：`hero_build: build_charger`，不指定 `ally_builds`。

**情境 A（最簡單，不用移動）— `oil_depot` 種子 1**

1. 第 1 輪，主角 (0, 4)；敵人：盜賊1 (1, 4)、盜賊2 (2, 4)、盜賊弓手 (5, 4)、盜賊頭目 (7, 5)；(3, 4)、(4, 4) 是空格。
2. 選技能「蠻牛衝陣」→ 點終點 **(4, 4)**。
3. 預覽應顯示：路線 (0, 4)→(1, 4)→(2, 4)→(3, 4)→(4, 4)；(1, 4)、(2, 4) 的敵人格標命中率 60%；終點標「衝」；傷害 盜賊1 2–24、盜賊2 1–12，擊倒成功率 70%。
4. 送出（API 實測）：先撞盜賊1：d20=9 命中（11），7 點傷害，HP 4 → 0 倒下；再撞盜賊2：d20=5 失手；主角停在 (4, 4)。

**情境 B（兩個都被撞中、擊倒的畫面）— `swamp` 種子 1**：主角初始在 (0, 6)，先移動到 **(1, 4)**（路徑 (0,6)→…，消耗 5 內可達）；敵人 盜賊弓手 (2, 4)、盜賊頭目 (4, 4)；蠻牛衝陣 → 終點 **(5, 4)**。預覽命中率 盜賊弓手 60%、盜賊頭目 65%。送出結果：盜賊弓手 d20=5 失手；盜賊頭目 d20=15 命中、1 點傷害、擊倒 d20=9 成功「倒地」。

**情境 C（另一個兩敵人例子）— `swamp` 種子 0**：第 1 輪移動到 (3, 4)，終點 (7, 4)：預覽路線 (3, 4)→(4, 4)→(5, 4)→(6, 4)→(7, 4)，命中率 盜賊盾衛 60%、盜賊頭目 65%；送出結果：盜賊頭目 d20=1 自然 1 失手、盜賊盾衛 d20=13 命中並被擊倒。「被擋住」的預覽文字與結算由 vitest 與引擎測試覆蓋（`test_a_wall_stops_the_charge_before_it`），沒有另外挑種子。

網頁格子點擊可用 JS 對 canvas 發 pointer 事件（52px 一格）。我沒有用瀏覽器實測畫面（由 PM 驗收），目前只有 vitest 與 API 測試覆蓋。

## 8. 待 PM 決定（最多 10 點）

1. **射程放在形狀 `range`，不是原語的 `range` 參數**：規格寫 `charge_through: {range: 4, …}`，但技能的射程本來就是形狀的 `range`（`mastery: range`、AI、預覽的 `reach` 都讀它），原語再放一個會有兩個來源；所以原語只有 `dice` 與 `on_hit`。
2. **停不下來時整招不可施放**：選的終點（空格）合法，但路上第一格就被擋住、或擋住前的格子都被單位占住時，沒有地方可停，`legal_actions` 不列、直接施放會被拒（規格的「實作者擇一」）。另一種做法是「原地不動、仍擲不到任何人」，沒有意義。
3. **預算初值**：預期被撞 1.5 個 × （骰子平均 ＋ 擊倒 3／推 2）；蠻牛衝陣 15 點、91.2%。沒有另外為「位移本身」計價（施放者的位移價值）、也沒有依命中率折價；全部是初值、未經模擬。
4. **`on_hit` 只有兩種、傷害固定是 `dice` 物理傷害（不加屬性）**：與 `hurl_object` 一致，所以衝撞傷害不吃力量，只吃命中、格擋、暴擊與修正規則。想讓它吃力量（像武器技）需要決定倍率。
5. **推到旁邊的方向**：先左後右、都不行就往左撞；規格寫「左右以固定順序選可站的一側」，我把「可站立」擴大成「推得動」（含沒有單位、不更高）。
6. **沿途的敵人倒下或被推開後，那一格就走進去**（路徑上的移動事件會變多），而不是跳過；被擊倒（倒地）但沒死的敵人仍擋在格子裡，繼續穿過。
7. **預覽的命中率從「經過時的格子」計算**（見 2.2），傷害期望值仍用最少／最多的平均估計（衝撞的傷害不是 `damage` 效果，`_damage_expectation` 的逐效果精確計算套不上）；最少／最多傷害範圍是精確的。
8. **AI**：沿途沒有敵人就不衝（只有位置價值不值得花 2 AP）；終點的選擇由預覽收益與位置價值決定，所以兩個敵人排成一列時（`test_charge_ai.py` 的情境），AI 可能只穿過第一個就停在第二個旁邊（終點在第二個敵人後面會失去貼身位置）。平衡階段再調。
9. **朝向（3D-8d）尚未實作**：規格寫「面向衝撞方向」，目前沒有朝向系統，所以沒做；3D-8d 實作時 `charge_through` 結束後要面向 `travel` 方向（`_charge_walk` 內已有行進方向）。
10. **順手修了預覽文字的既有錯誤**（見 3.5）：沒有改變遊戲規則，只讓倒地目標的預覽不再回 500；若 PM 不希望本段碰到 narrative，可單獨 revert 該 commit 中的一行（`narrative/events.py` `_attack`）。

## 9. 代表性輸出

`uv run trpg battle --map bridge_chasm --seed 2 --ally-build build_charger`（連續一段，輸出第 118–133 行）：颶風踢失手後，蠻牛衝陣一次直線穿過兩個敵人，兩人都命中、都被擊倒。

```
  衝鋒流英雄 施放「颶風踢」（AP 1，法力 3，冷卻 2 回合）→ 影響 1 格
  衝鋒流英雄 以「颶風踢」攻擊 盜賊1：d20=5 修正 +1 熟練 +2 = 8（目標 11）→ 失手
  衝鋒流英雄 施放「蠻牛衝陣」（AP 2，法力 5，冷卻 3 回合）→ 影響 3 格
  ➤ 衝鋒流英雄 直線衝撞：(6, 6)→(6, 5)→(6, 4)→(6, 3)
  衝鋒流英雄 以「蠻牛衝陣」攻擊 盜賊1：d20=18 修正 +1 熟練 +2 = 21（目標 11）→ 命中
  ⟳ 盜賊1 反應：格擋（耐力 −10）
    盜賊1 受到 6 點物理傷害［骰 6+6］（格擋/加成 ×0.5），HP 12 → 6
  衝鋒流英雄 對 盜賊1 使出擊倒：d20=19 修正 +2 熟練 +2 = 23（目標 11）→ 成功
  盜賊1 獲得狀態「倒地」
  衝鋒流英雄 以「蠻牛衝陣」攻擊 盜賊2：d20=18 修正 -1 熟練 +2 = 19（目標 11）→ 命中
  ⟳ 盜賊2 反應：格擋（耐力 −10）
    盜賊2 受到 6 點物理傷害［骰 6+6］（格擋/加成 ×0.5），HP 30 → 24
  衝鋒流英雄 對 盜賊2 使出擊倒：d20=8 修正 +2 熟練 +2 = 12（目標 11）→ 成功
  盜賊2 獲得狀態「倒地」
  衝鋒流英雄 的「激昂」結束了
  衝鋒流英雄 結束回合
```
