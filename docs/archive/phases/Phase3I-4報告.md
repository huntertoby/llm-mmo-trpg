# Phase 3I-4 完成報告｜第二批其他武器（雙匕首、霰彈槍、手槍、雙手槍）

規格：`docs/phases/Phase3I計畫.md` 第 0～3 節（3I-4 列）；設計：`docs/design/08-裝備.md` 8.11（武器表、「雙屬性武器與卡片顯示」、「火器」、「雙持」）。火槍（火器第一批）的彈匣、裝填、槍聲、武器技開火等實作全部沿用。

## 1. 做了什麼

| 項目 | 內容 | 檔案 |
|---|---|---|
| 武器資料 | 雙匕首 `dual_dagger`（近戰、射程 1、敏捷、1d4、`paired: true`、`strikes: 2`）、霰彈槍 `shotgun`（遠程、射程 4、敏捷、2d6、雙手、彈匣 1、槍聲、`range_mod` 2／3／4 格 ＝ 750／500／250‰）、手槍 `pistol`（遠程、射程 5、敏捷、1d8、單手、彈匣 2、槍聲）、雙手槍 `dual_pistol`（遠程、射程 5、敏捷、1d6、`paired: true`、彈匣 4、裝填 1 AP、槍聲）；`look` 用現有的造型（`dual_dagger`／`shotgun`／`pistol`／`dual_pistol`）。傷害骰是初值 | `content/weapons.yaml` |
| schema | `WeaponDef.paired`（成對武器：算一件、占雙手；**`two_handed` 仍為 false**，同時為真會被 schema 擋）、`WeaponDef.strikes`（普攻連打幾下，1～3，預設 1）；卡片：握法行多了「成對：算一件武器、占用雙手」、特性行多了「連擊：普攻一次打 N 下…」，霰彈槍距離衰減行由 `range_mod` 自動產生（「2 格：傷害 −25%」…） | `content/battle.py` |
| 引擎：連擊 | `perform_unit_attack` 在第一下之後，依 `strikes` 再對**同一個目標**各自完整結算一次（各自擲命中、傷害、暴擊、背刺判定）；目標或攻擊者倒下就停。背刺位置是擲骰當下的朝向，轉身在整個普攻結束後才發生，所以兩下都吃背刺（命中 +2、暴擊範圍 +1）。藉機攻擊、監視射擊、反擊都走同一條路，所以也是兩下。武器技不連擊（仍只打一次） | `engine/reactions.py` |
| 引擎：火器 | 沒有改引擎：霰彈槍的距離衰減、手槍與雙手槍的「無站定、無距離修正」都是既有 `range_mod`／`steady` 參數的資料；彈匣 4（2＋2）用既有的 `magazine`／`reload_ap`（空膛才能裝填、1 AP 一次裝滿）；武器技開火、槍聲、直射沿用 | `content/weapons.yaml` |
| 成對武器占雙手 | `loadout_problems`：`paired = weapon.paired or 主手物品.paired`，所以拿成對武器（即使物品沒勾成對）也不能再放副手；物品卡的 `paired` 同樣包含武器的 `paired` | `content/equipment.py`、`api/gear.py` |
| 物品 | 新增 `item_dual_dagger`、`item_dual_pistol`（`paired: true`，無詞條）；既有試煉物品 `item_test_twin_daggers` 改引用 `dual_dagger`（原本是「匕首＋paired」，會變成單擊的成對匕首） | `content/items.yaml` |
| 工坊勾選框 | `GearWeaponInfo.pairable`（3-48g，由「有 `paired` 物品的單手武器」推導）**自動出現在 `dual_dagger`、`dual_pistol`**，不必改程式；`dagger` 不再 pairable（原本只因為那件試煉雙匕首） | 測試 `test_the_workshop_pairable_flag_appears_for_the_paired_weapons` |
| 開局、AI、build | 開局武器池本來就是 `weapons.yaml` 全部（非 `summon_only`），四把自動出現；起始技能依大類相容；AI 沒改（普通 AI／效用 AI 都會在空膛時裝填，見待決 2）；白板 build `build_blank_dual_dagger`／`shotgun`／`pistol`／`dual_pistol` | `content/sim/builds.yaml` |
| 前端 | **紙娃娃**：只有武器 id（沒有裝備快照）時，成對武器的 kind（`dual_dagger`／`dual_pistol`）原本畫不出來（不認得的 kind 被略過），現在主手畫單把、副手複製一把（`appearance.ts`、`dollGear.pairedPart`）；**武器小圖示**同樣把成對 kind 換成單把造型（雙匕首斜放如匕首，`weaponIcon.ts`）；工坊勾選框沿用 3-48g 的元件，免改；裝備目錄 fixture `catalog.json` 補上四把武器、兩件物品 | `client/src/render/`、`client/src/gear/` |
| 紀錄格式 | `LOG_FORMAT` `/65` → **`/66`**（`runner.py` 文件字串保留歷史、測試的 `trpg-battle-log/66`、`test_24c`） | `engine/runner.py`、tests |
| 重產 | `glossary.json`（新武器外觀）、`skill_icons.json`、`openapi.json`（無差異）、CLI 快照（無差異，不需 `UPDATE_CLI_SNAPSHOTS`） | |

## 2. 規則對照（08 8.11）

| 規則句 | 實作 | 測試（`tests/engine/test_weapons_3i4.py`） |
|---|---|---|
| 雙匕首：近戰、射程 1、敏捷、成對占雙手 | 武器資料；`paired`，`two_handed` 為 false | `test_the_new_weapons_are_data_with_the_designed_parameters`、`test_paired_weapons_block_the_offhand_even_without_the_paired_item`（雙匕首、雙手槍各 3 個斷言） |
| 普攻打兩下 1d4 | `strikes: 2`：兩次 `AttackRolled`、兩次 `DamageDealt`，各自擲命中 | `STRIKE_TABLE` 4 列、`test_each_strike_rolls_its_own_attack_and_damage`（第一下中、第二下失手只有一筆傷害） |
| 背刺時兩下都吃加成 | 兩下的 `backstab` 都是 2；正面都是 0 | `STRIKE_TABLE`（背後命中、背後失手） |
| （保守）第一下打倒目標就不打第二下 | 迴圈檢查雙方存活 | `test_dual_dagger_stops_when_the_first_strike_kills` |
| 改資料（`strikes`）行為跟著變；其他武器不連擊 | `strikes` 1／2／3 | `test_changing_strikes_changes_the_number_of_strikes` |
| 武器技不連擊 | 武器技走技能效果，不經普攻迴圈 | `test_dual_dagger_weapon_skill_hits_only_once` |
| 霰彈槍單體、射程 4、彈匣 1 | 資料；5 格外 `attack_problem` | `test_shotgun_range_is_four_and_...`、`test_shotgun_fires_one_shell_gunshot_and_reload` |
| 傷害依距離 1／2／3／4 格 ＝ 100／75／50／25% | `range_mod` | `SHOTGUN_TABLE`（4 距離 × 站定／移動後 2 種，實際 `multiplier_permille`）、`test_shotgun_damage_really_drops_with_distance`（實際傷害遞減）、改資料案例 |
| 霰彈槍沒有站定與遠距加成，可以邊走邊打 | 無 `steady`；移動後與站定的命中修正相同（0） | `SHOTGUN_TABLE` 的 `moved` 參數 |
| 手槍：單手（可搭副手）、射程 5、彈匣 2 | 資料 | `test_pistol_holds_two_shots_before_it_needs_a_reload`、`test_pistol_is_one_handed_and_allows_an_offhand`、`test_pistol_range_is_five` |
| 手槍：移動後開火沒有懲罰，也沒有站定、遠距加成或距離修正 | 無 `steady`、無 `range_mod` | `test_pistol_has_no_steady_range_or_point_blank_modifiers`（距離 1～5 × 站定／移動後 10 列：命中修正 0、傷害 1000‰） |
| 雙手槍：成對占雙手；彈匣 4（2＋2）、1 AP 一次裝滿、用有子彈的那把 | `magazine: 4`、`reload_ap: 1`（用子彈總數表示兩把；開火扣 1 發；空膛才能裝填） | `test_dual_pistol_has_four_shots_and_one_ap_refills_them`、`test_dual_pistol_has_no_position_modifiers` |
| 共通：開火解除隱蔽（槍聲）、直射、裝填 1 AP | 三把槍都有 `gunshot: true`、沒有 `lob` | `test_dual_pistol_gunshot_reveals_the_shooter`（資料）；槍聲與直射的行為本體由 3-24a2 的測試涵蓋（機制共用） |
| 武器技也算開火（耗 1 發、空膛不能施放） | 沿用 `fires_gun`（3-24c） | `test_firearm_weapon_skills_spend_a_round_and_need_ammo`（3 把槍） |
| 雙持只做雙匕首、雙手槍，成對算一件占雙手 | `paired`；`loadout_problems` | 同上；`test_non_paired_single_handed_weapons_still_take_an_offhand`（單手劍、手槍、匕首仍可搭副手） |
| 工坊「成對武器」勾選框自動出現 | `pairable` 推導 | `test_the_workshop_pairable_flag_appears_for_the_paired_weapons`、API 目錄測試、前端 `canPair` |

**行為一致測試**（流程改善 B）：四把新武器 × 2 組屬性 × 普攻與武器技，共 16 例。普攻的每一筆 `damage_dealt.scaled_permille // 1000` 等於卡片「目前 +N」（雙匕首兩筆都檢查，且筆數＝`strikes`）；整數加成且倍率 1000‰ 時傷害＝骰值＋N。武器技（`category: weapon`）同樣比對卡片的「目前 +N」。屬性表包含「只吃敏捷、不吃力量／智力」的組合。

## 3. 測試與檢查

- `ruff check`、`ruff format --check`、`mypy`（669 檔）、`lint-imports`（7 kept）通過。
- pytest：`tests/engine tests/content tests/skillgen tests/roguelite tests/narrative tests/api tests/sim` 6210 passed；`-m "slow or not slow" tests/cli` 148 passed（CLI 快照無差異）。新增 `tests/engine/test_weapons_3i4.py`（68 例），改動既有測試：`LOG_FORMAT`、試煉物品與 `pairable` 的斷言、物品詞條數檢查放寬（成對武器本體可 0 詞條，同副手本體）。
- 前端：`vitest` 922 passed（新增 `weapons3i4.test.ts`、改 `gearDraft`／`gearPreview` 測試）、`tsc --noEmit`、`pnpm build` 通過。
- 重播：`trpg battle --map open_plain --seed 3 --ally-build build_blank_dual_dagger,build_blank_shotgun,build_blank_dual_pistol --log-json …` → `battle replay` 通過（102 動作、266 事件）；戰鬥文字中雙匕首連兩次「攻擊」、雙手槍有裝填紀錄。
- 排版煙霧檢查（埠 8016，每個情況先 `localStorage.clear()`）：1600×900、底部最矮、800×600 全 PASS。本段沒有新增版面元件，**未在畫面上親眼看**：紙娃娃手持雙匕首／雙手槍的樣子、武器小圖示（以 vitest 的資料斷言代替）。

## 4. 模擬（只量不調）

`trpg sim matrix --builds build_blank_warrior,…,build_blank_longgun --seeds 10`，白板（全屬性 10、無技能）× 8 種地圖類型 × 10 種子＝480 場；表中是 8 種地圖類型的平均。

| build | 勝率 | 英雄 DPR | 前段次數（/8） |
|---|---|---|---|
| 白板戰士（單手劍，對照） | 57.5% | 5.36 | 3 |
| **白板雙刀手**（雙匕首） | **67.5%** | **7.22** | 6 |
| **白板霰彈手**（霰彈槍） | **31.9%** | **1.15** | 0 |
| **白板手槍手**（手槍） | **53.8%** | **3.69** | 2 |
| **白板雙槍手**（雙手槍） | **53.8%** | **4.00** | 2 |
| 白板槍手（火槍，對照） | 56.9% | 7.21 | 3 |

觀察（不調數值）：
- 雙匕首明顯偏強（連擊 ×2 ＋ 近戰命中，DPR 比單手劍高約 35%，且 6.8 標準第 1 項「沒有任何 build 在所有地圖類型都排名前段」仍通過）。1d4 × 2 的期望低，但每一下都吃屬性加成（敏捷 × 0.3），白板時加成比骰值還大。
- **霰彈槍很弱（DPR 1.15）**：效用 AI 沒有「想貼近」的位置價值，通常在射程 4 的邊緣開火（25% 傷害）。詳見待決 2。
- 手槍、雙手槍 DPR 3.7～4.0，約為火槍的一半（沒有站定、遠距加成，單發 1d8／1d6），勝率與火槍相近。
- 第 6.8 標準第 2 項「每個 build 至少在一種地圖類型排名前段」：霰彈槍不通過（因為本批全是白板、AI 未針對霰彈槍調整）。樣本小（每格 10 場），只供參考。

## 5. noqa

無新增。

## 6. 待 PM 決定

1. **成對武器的資料模型**：用「獨立武器 `dual_dagger`／`dual_pistol` ＋ `WeaponDef.paired`（`two_handed` 為 false）＋ `strikes`」，物品 `paired: true` 保留給外觀與工坊勾選。3-48g 報告待決 3 的另一個選項（「匕首＋paired」）沒用，因為連擊與彈匣 4 必須是武器資料。`pairable` 推導規則不變。同時，**既有的 `item_test_twin_daggers` 改成引用 `dual_dagger`**，所以 `dagger` 不再能被工坊勾成對（原本勾了只是占雙手、沒有連擊）。
2. **霰彈槍的 AI**：效用 AI 沒有距離衰減的概念，白板霰彈手 DPR 只有 1.15。建議之後加一個「武器距離傷害偏好」的位置價值（讀 `range_mod` 的傷害千分比，鼓勵站在高倍率的距離；同時能讓火槍更願意拉開），這會影響所有火器的 AI，屬於數值／AI 調整，這段不做。
3. **傷害骰是初值**：雙匕首 1d4 × 2、霰彈槍 2d6、手槍 1d8、雙手槍 1d6（08 沒寫）。雙匕首偏強、霰彈槍偏弱（見第 4 節），請玩法 PM 在平衡階段定。
4. **雙匕首暴擊範圍**：沿用 20（08 只寫匕首「暴擊 19 起」，雙匕首沒寫特性之外的暴擊）。若要比照匕首 19，改 `weapons.yaml` 一個數字。
5. **連擊的細節（保守解讀）**：兩下都對**同一個目標**；第一下打倒目標就不打第二下；第二下不是「主要攻擊」，預覽（`preview`）的傷害範圍與期望只算**第一下**（最小情境第二下視為失手、最大情境視為暴擊，與穿透／藉機攻擊的處理一致）——卡片文字已寫明「連擊」，但預覽數字沒有乘 2。若要預覽顯示兩下合計，是預覽（`preview.py`）的另一段小改。藉機攻擊、監視射擊、拳套反擊若由雙匕首發動也是兩下。
6. **雙手槍的「開火用有子彈的那把」**：用子彈總數 4 表示兩把各 2 發，開火扣 1 發；裝填維持「空膛（0 發）才能裝填」，所以不會出現「一把空了就先補一把」。若要允許半空補滿，需要放寬 `reload_problem`（影響所有火器的規則，故未做）。
7. **成對武器的卡片「單手／雙手」欄**：前端裝備清單用 `two_handed` 顯示「雙手」，成對武器顯示「成對」（已有）；武器卡的握法行新增「成對：算一件武器、占用雙手」。
8. **沒有開局副手選擇**（同 3I-2）：手槍是單手，可以搭副手，但一般開局沒有副手選擇，只在測試模式／裝備測試介面可搭配。
9. **槍造型跟區域走**（美術 PM 說明的後續項目）：這批用通用造型（霰彈槍 `double`、手槍與雙手槍 `revolver`）。
