# Phase 3I-1 完成報告｜主武器補平六屬性（拳套、鐮刀、鞭＋特性；錘改取較高）

規格：`docs/phases/Phase3I計畫.md` 第 0～3 節（3I-1 列）；設計：`docs/design/08-裝備.md` 8.11（武器表、「雙屬性武器與卡片顯示」、「提前武器的特性細節」）、`06-技能.md` 6.10。

## 1. 做了什麼

| 項目 | 內容 | 檔案 |
|---|---|---|
| 新武器資料 | 拳套 `fist`（近戰、射程 1、雙手、1d8、體質／敏捷 **取較高**、`counter`）、鐮刀 `scythe`（近戰、射程 1、雙手、1d10、意志／力量 **取平均**、`reap {hp_permille: 300, damage_permille: 250}`）、鞭 `whip`（近戰、射程 2、單手、1d6、敏捷／感知 **取平均**、`entangle {move_penalty: 2}`；`reach` 仍為 1）。`look` 填 `fist/knuckle/iron`、`scythe/long/iron`、`whip/leather/leather` | `content/weapons.yaml` |
| 錘改取較高 | `hammer.attr_mode: max`（體質、力量同屬物理，#46） | `content/weapons.yaml` |
| schema | `WeaponDef` 加 `counter`、`reap`（`Reap`）、`entangle`（`Entangle`）；**新驗證**：雙屬性同類必須 `max`、一物理一心智必須 `mean`；`Attribute.is_physical` | `content/battle.py`、`shared/types.py` |
| 反擊（拳套） | 內建反應 `counter_attack`（`effect: basic_attack`、事件 `hit_by_melee`、`requires_counter_weapon`）。`hit_reactions` 在近戰攻擊命中、傷害之後，**攻擊者相鄰** 時找 `basic_attack` 規則，對攻擊者普攻一次（`reaction=True`）。佔本輪反應（共用 `reactions_used`），`stamina_cost: 0`、不花 AP。手上武器有 `counter` 的單位由 `make_unit` 自動在最前面加一條 `auto` 規則（`lifecycle.weapon_reaction_rules`） | `content/reactions.yaml`、`content/environment.py`、`engine/reactions.py`、`engine/lifecycle.py` |
| 收割（鐮刀） | `modifiers.reap_permille`：普攻或 `category: weapon` 的技能、目標 **當下** HP ≤ 30% 時 +250‰，和其他正向加成一起進 `cap_damage_bonus`（全身 +50% 上限）。普攻在傷害前算（`_attack_once`），技能在建傷害效果時算 | `engine/modifiers.py` |
| 纏繞（鞭） | 新狀態 `entangled`（debuff、`turn_end` 持續 1、refresh、**沒有** `save_attr`／`control_group`／`budget_points`）＋新狀態欄位 `move_reduction`：回合開始的移動點數再減 `amount`（多個取最大、最低 0）。普攻命中後 `apply_hit_traits` 施加（`amount` ＝ 武器的 `move_penalty`）；命中發生在目標自己的回合（反應攻擊）時持續 2，確保作用在「下一個」回合 | `content/statuses.yaml`、`engine/rules/statuses.py`、`engine/weapon_traits.py`、`engine/ids.py` |
| 卡片與說明 | 武器卡特性行（反擊、收割、纏繞，數值取自資料）；狀態卡「纏繞」規則句（依武器列出減少量、不擲抵抗）；雙屬性取法句自動跟資料 | `content/battle.py`、`narrative/status_info.py` |
| 前端 | `weaponIcon.ts` 的 `DIAGONAL` 加 `scythe`、`whip`；狀態圖示 `entangled`（繩圈＋下箭頭、移動控制藍 `#6ac8ff`）；新測試 `weapons3i1.test.ts`；狀態數 32→33 | `client/src/render/` |
| 開局、AI、模擬 | 開局武器池是 `weapons.yaml` 全部（非 `summon_only`），新武器自動出現，起始技能依大類 `melee` 相容；AI 不需改（近戰武器照普攻；鞭射程 2 走既有的 `reach_spacing`；反擊是自動反應）。`content/sim/builds.yaml` 加 `build_blank_fist`／`build_blank_scythe`／`build_blank_whip`（白板，比照白板戰士） | `content/sim/builds.yaml` |
| 紀錄格式 | `LOG_FORMAT` `/62` → **`/63`**（`runner.py` 文件字串、測試的 `trpg-battle-log/63`、`test_24c` 的 `/63`） | `engine/runner.py`、tests |
| 重產 | `glossary.json`、`skill_icons.json`（OpenAPI／`schema.d.ts` 重產後無差異，CLI 快照重產後無差異） | `client/src/...` |

## 2. 武器表 `attr_mode` 核對（#46：同類取較高、一物理一心智取平均）

| 武器 | 屬性 | 類別 | 應為 | 目前 | |
|---|---|---|---|---|---|
| 匕首 | 敏捷／力量 | 物理＋物理 | 取較高 | `max` | ✔ |
| 錘 | 體質／力量 | 物理＋物理 | 取較高 | `mean` → **`max`** | 3I-1 修正 |
| 拳套 | 體質／敏捷 | 物理＋物理 | 取較高 | `max` | 新增 |
| 鐮刀 | 意志／力量 | 心智＋物理 | 取平均 | `mean` | 新增 |
| 鞭 | 敏捷／感知 | 物理＋心智 | 取平均 | `mean` | 新增 |
| 其他（單手劍、雙手劍、斧、矛、弓、弩、火槍、三把法杖、權杖、圖騰杖、召喚專用武器） | 單屬性 | — | — | — | 不受影響 |

`WeaponDef` 的 schema 驗證現在強制這條規則（不符就載入失敗），之後的圓盾、法器珠、魔導劍也會被檢查。六屬性主武器：力量、敏捷、體質、感知、意志都有近戰主武器；智力目前只有法杖（魔導劍在 3I-3）。

## 3. 特性實作與規則對照（08 8.11「提前武器的特性細節」）

| 規則句 | 實作 | 測試 |
|---|---|---|
| 拳套反擊是 **反應** | 內建反應 `counter_attack`，走 `_react`（規則、模式 auto／prompt／off、每輪次數） | `test_weapons_3i1.py` 反擊表格 |
| 相鄰敵人的近戰攻擊 **命中** 你 | 只在 `hit_by_melee`、`manhattan == 1`；失手、矛／鞭隔 1 格、相鄰的遠程攻擊都不反擊 | `COUNTER_TABLE` 6 列 |
| 你 **沒倒下** 時 | `hit_reactions` 開頭 `target.alive` | 「被打倒」列 |
| 自動對攻擊者 **普攻一次** | `perform_unit_attack(target → attacker, reaction=True)`（感知的反應命中常駐照算，同藉機攻擊） | `test_counter_is_a_free_basic_attack_that_uses_the_reaction` |
| **佔本輪反應**，和格擋共用 | `spend_reaction`；同輪第二次被打不再反擊 | 同上 |
| 不花 AP、不花耐力 | `stamina_cost: 0`；反應方 AP 不變 | 同上 |
| 用反應設定選優先 | 規則照順序；`SetReactionMode` 可切換 | `test_the_player_can_switch_...` |
| 近戰武器技命中也算近戰攻擊 | 技能的 `react_to_hits` 也走 `hit_reactions`（`melee` 依技能） | `test_counter_also_answers_an_adjacent_melee_weapon_skill` |
| 鐮刀收割看 **當下** HP ≤ 30% | `target.hp * 1000 <= 300 * max_hp`（30% 剛好算） | `REAP_TABLE` |
| 該次傷害 +25% | +250‰（傷害倍率） | `test_reap_raises_the_basic_attack_damage_by_a_quarter` |
| 適用普攻與武器技 | `use.action == "attack"` 或 `use.skill.category == "weapon"`；法術技、物件目標不算 | `test_reap_applies_to_basic_attacks_and_weapon_skills_only` |
| 計入全身 +50% 上限 | 加進 `cap_damage_bonus` 的總和 | `test_reap_counts_toward_...` |
| 鞭纏繞：普攻命中後施加狀態 | `apply_hit_traits` → `ApplyStatusEffect(entangled, amount=2)`；失手不施加；不拉近 | `test_whip_hit_entangles_without_a_save`、`test_whip_miss_does_not_entangle` |
| 目標下一個回合開始時移動 −2（最低 0） | `move_points_for_turn` 先乘 `move_permille` 再減 `move_reduction`，`max(0, …)` | `ENTANGLE_TABLE`（含緩速、速度 1、資料改值） |
| 持續到該回合結束 | `turn_end` 持續 1；反應攻擊在目標自己的回合命中時持續 2 | `test_entangle_lasts_through_the_target_next_turn_only`、`..._waits_for_its_next_turn` |
| 重複施加只刷新、不疊加 | `stacking: refresh`，單一實例；多個取最大 | `test_entangle_refreshes_instead_of_stacking` |
| 不擲抵抗、不算控制類別 | 狀態沒有 `save_attr`、`control_group`；沒有 `budget_points`（技能不能施加） | 同上（沒有 `status_save_rolled`）、狀態卡測試 |

**行為一致測試**（流程改善 B）：拳套、鐮刀、鞭、錘各 2 組屬性 × 普攻與武器技，實際結算的 `damage_dealt.scaled_permille // 1000` 等於卡片「目前 +N」，整數加成時傷害＝骰值＋N（`test_basic_attack_damage_matches_the_card_current_bonus`、`test_weapon_skill_damage_matches_the_card_current_bonus`，共 16 例）；既有的 `test_rule_texts_41c.py` 全武器表格測試也自動包含新武器。錘取較高：`test_weapons_24a1.py`、`test_weapon_skill_scaling.py` 改寫。

## 4. 檢查

- `ruff check`、`ruff format --check`、`mypy`（659 檔）通過。
- pytest：`tests/engine tests/skillgen tests/content` 5287 passed；`tests/api tests/narrative tests/roguelite` 627 passed；`tests/cli tests/sim` 231 passed；CLI 快照（slow）重產無差異。
- 前端：`typecheck`、`test`（890 passed）、`build` 通過。
- 重播：`trpg battle --map open_plain --seed 3 --ally-build build_blank_fist,build_blank_scythe,build_blank_whip` → `battle replay` 通過（128 動作、321 事件）；紀錄中反擊 3 次、纏繞相關事件 11 筆。
- 實機（`trpg serve --port 8013`，1600×900）：開局選單出現拳套、鐮刀、鞭，拳套的說明卡顯示反擊行與「1d8＋體質／敏捷（取較高）× 0.3」；選鞭開戰正常進入戰鬥。**沒有做完的**：內建瀏覽器的 1600×900 模擬在操作中一直被重設，畫布上的點擊位置跟著偏掉，所以沒在畫面上親眼看到反擊、纏繞動畫與紙娃娃小圖示細節；這部分改用 CLI 戰鬥文字（「⟳ 白板拳師 反應：反擊」、「獲得狀態「纏繞」」）與前端單元測試（外觀表、紙娃娃主手、斜放圖示）確認。**建議 PM 驗收時再看一次畫面。**

## 5. 模擬（只量、不調）

`trpg sim matrix`，7 個白板 build（全屬性 10、沒有技能）× 10 張地圖 × 10 種子＝700 場。地圖類型平均：

| build | 勝率 | 英雄 DPR | 前段次數（8 類） |
|---|---|---|---|
| 白板戰士（單手劍 1d8） | 57.5% | 5.36 | 0 |
| 白板斧手 | 58.1% | 5.38 | 0 |
| 白板錘手 | 63.8% | 6.66 | 3 |
| 白板矛兵 | 68.1% | 6.89 | 4 |
| **白板拳師（拳套 1d8＋反擊）** | **61.3%** | **6.44** | 4 |
| **白板鐮刀手（鐮刀 1d10＋收割）** | **57.5%** | **5.96** | 2 |
| **白板鞭手（鞭 1d6、射程 2＋纏繞）** | **65.6%** | **4.89** | 3 |

觀察（不調數值）：
- 拳套 DPR 含反擊傷害，介於錘與單手劍之間；冰湖 100%、沼澤 40%，地圖差異大。
- 鐮刀勝率與單手劍相同、DPR 稍高；收割只在收尾時生效，白板對局效果有限。
- 鞭 DPR 最低（1d6），但勝率第二高：森林、長廊 100%，射程 2＋纏繞讓敵人難以接近，生存（隊友存活率）高。
- 全屬性 10 時錘改取較高不影響白板 build 的數字；真實的影響在有配點的主角（同時點體質與力量的人會比以前少拿）。
- 樣本小（每格 10 場），只供參考。

## 6. noqa

無新增（測試的區域匯入已改成檔頭匯入）。

## 7. 待 PM 決定

1. **拳套持有者的預設格擋改成 `off`**：格擋（`targeted_by_melee`）在傷害前就會用掉本輪唯一的反應，預設下反擊幾乎不會發生。我讓「用預設反應規則」的拳套持有者，預設格擋規則改為 `off`（玩家可在反應設定改回 auto）；範本自己寫了反應規則的單位不動。替代方案：維持格擋 auto（反擊只在耐力不足時才會發生）。
2. **新武器的傷害骰是初值**（08 沒寫）：拳套 1d8（雙手＋反擊）、鐮刀 1d10（雙手＋收割）、鞭 1d6（單手、射程 2＋纏繞）。是否要依模擬調，請玩法 PM 定。
3. **鞭的藉機攻擊範圍**維持 1（`reach: 1`；只有矛的特性是「2 格內藉機攻擊」）。
4. **纏繞在目標自己的回合施加時持續 2**（例如被鞭的藉機攻擊打中），讓它作用在下一個回合，而不是當回合結束就消失。設計只寫「下一個回合」，這是我的解讀。
5. **武器技的允許縮放範圍變大**：`weapon_attrs("melee")` 現在包含感知、意志（鞭、鐮刀），所以近戰武器技的提示屬性範圍（3H-7 範圍檢查）也包含它們；組合器仍固定用大類主屬性（力量）。`test_skill_scaling.py`、`test_scaling_follow.py` 已跟著改。3I-3 的魔導劍會再加入智力。
6. **開局自動配點只看武器主屬性**（`primary_attribute` 的 fallback 是 `scaling_attr`）：取平均的鐮刀、鞭沒有技能時，4 點全點在意志／敏捷，第二屬性不加。要不要改成平均分給兩個屬性？
7. **收割只在「受修正規則影響」的施放生效**：被動觸發的施放（`Cast.modified == False`）不吃修正規則的傷害‰，所以也不吃收割；照現有架構處理。
8. 反擊的普攻吃感知的「反應命中」常駐加值（和藉機攻擊、監視射擊同一套）。
