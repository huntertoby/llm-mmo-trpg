# Phase 3K-1 報告：物品產生器＋物品預算（玩法決定 #49、#52）

規格：`docs/phases/Phase3K計畫.md` 第 0、1、1.1 節、第 2 節 3K-1 列、第 3、4 節。設計：08 8.11、8.12、8.21、8.21.2.4、8.22、**8.22.1**、8.24；07 7.1。這一段 **沒有接一輪流程**（那是 3K-2）。

## 做了什麼

- **`content/item_gen.yaml`**（schema `trpg.content.item_budget.ItemGenRules`）：全部係數都放在這裡——稀有度權重 **40／25／20／13／2**（第 1.1 節第 8 點）、全身預算曲線（1→100、5→200、10→350，線性內插、無條件捨去）、部位比例與詞條比例、數值類單位價、條件成立率、各類別固定點數（技能強化 8、普攻附加 10、**武器元素 15**、武器特性 8、觸發 12×0.7、充能 12、動作 20、反應 15、改變規則 40）、代價型淨值至少 4、基礎加成（3 點＝2%）、稀有度的條數與類別、各部位的 build 詞條、武器屬性偏好 500‰。載入時和詞條白名單交叉檢查（`item_gen_problems`）。
- **物品預算驗證器** `trpg.content.item_budget`：`total_budget`／`slot_budget`／`affix_budget`（只看等級與部位，和稀有度無關）、`affix_points`（`Fraction`）、`item_points`、`item_budget`（摘要，含填滿千分比，給 3K-2 的「預算分數」）、`item_budget_problems`：詞條點數在預算的 70～100%、每條至少 2 點、條數不超過稀有度上限、類別在稀有度允許範圍、build 詞條（技能強化等）每件最多 1 條、觸發每件最多 1 條、基礎加成只在沒有詞條的普通物品上。傳說物品不檢查；沒有物品等級的物品回報問題。
- **物品產生器** `trpg.content.item_gen.generate_item(library, rng, slot, rarity, item_level, *, weapon_class=None)`（`weapon_class` 改成關鍵字參數，ruff `PLR0917` 的位置參數上限 5）與 `roll_rarity(library, rng)`：
  - 底材：主手從 `weapons.yaml`（排除 `summon_only`，可限定大類；成對武器自動 `paired`；外觀取武器的 `look`）；副手從 `offhands.yaml`（標籤與外觀沿用 `items.yaml` 的副手本體，所以盾有 `shield` 標籤）；其他部位從外觀清單的造型。
  - 詞條：每一步只考慮「放得進剩餘預算、且替後面每條預留最便宜一條點數」的詞條；同一族（六屬性、8 種普攻附加元素、8 種武器元素）算一個候選，抽中再選成員；武器上的屬性依縮放屬性偏好；數值取放得進的最大值。稀有起第 1 條是 build 詞條。不到 70% 時重抽（最多 30 次），再不行用「每步挑點數最高」的確定性後備；仍不行拋出 `ItemGenError`。
  - 輸出前自我檢查 `item_problems`＋`item_budget_problems`，所以輸出一律通過。只用傳入的 `Rng`（相同種子相同物品）。
  - 名稱：「稀有度＋底材名」（例：「稀有手槍」「普通外套」）；詞條文字照白名單模板。
  - 傳說：從現有傳說物品挑同部位（主手還要同大類）的，沒有就降為史詩。
- **#52 元素詞條**（`content/affixes.yaml`，51 → 66 條）：普攻附加元素補齊 7 種（`affix_attack_fire/ice/poison/earth/wind/holy/shadow`，原有雷電）；新增 8 條 **武器元素詞條** `affix_weapon_<元素>`（`AttackAffix.weapon_element`，類別仍是普攻附加；schema 規定只能 `slots: [weapon]`、不可是物理）。穿戴驗證：本身有元素的武器不能掛、同一件最多 1 條（`weapon_element_problems`）。
- **接上 3I-6 的元素優先順序**：`attack_element.weapon_affix_element(unit)` 改成讀主手生效中的 `weapon_element` 詞條；`resolve_attack_element` 沒有改。召喚物「繼承普攻附加」不繼承武器元素詞條。外觀關鍵字推導也認 `weapon_element`。
- **普通物品的基礎加成**：`ItemDef.base_bonus_permille`（武器＝傷害 ‰、其他部位＝防禦值 ‰）在 `build_gear` 變成 `GearBonus`（`affix_id` 為 `base:<物品 id>`），英雄面板的來源寫「物品名：基礎加成」。`ItemDef.item_level` 也是新欄位。
- `LOG_FORMAT` `/70` → **`/71`**（`ItemDef` 兩個新欄位、`AttackAffix.weapon_element`）。

## 規則對照表

| 規則 | 實作 | 測試 |
|---|---|---|
| 物品等級曲線（8.22.1 第 1 點） | `total_budget` | `test_total_budget_interpolates_and_floors` |
| 部位預算、詞條部分（第 2、3 點） | `slot_budget`／`affix_budget` | `test_slot_and_affix_budget_table`（13 列） |
| 同物品等級各稀有度預算相同（8.5） | 預算只看等級與部位 | `test_every_rarity_gets_the_same_budget`（6 等級 × 8 部位） |
| 詞條點數（第 4 點） | `affix_points` | `test_affix_points`（20 列） |
| 每條至少 2 點、取放得進的最大 N | `_best_value`、驗證器 | 抽樣測試、`test_budget_validator_rejects_bad_items` |
| 普通沒有詞條 → 基礎加成（第 5 點） | `_base_bonus`、`build_gear` | `test_common_items_without_affixes_convert_the_budget_to_base_bonus`、`test_common_base_bonus_adds_weapon_damage_and_armor_defense` |
| 70～100%（第 6 點） | `item_budget_problems` | 抽樣測試（每件）、驗證器測試 |
| 傳說從測試物品挑、沒有就史詩（第 7 點） | `_legendary` | `test_legendary_picks_an_existing_legendary_item_or_falls_back_to_epic` |
| 稀有度權重 40／25／20／13／2（第 8 點） | `roll_rarity` | `test_rarity_weights_match_content`（10000 次，±1.5%） |
| 主手只出同大類（07 7.1） | `_weapon_base` | `test_main_hand_weapons_all_match_the_requested_class` |
| 稀有度條數與種類（8.7、8.21.6） | `rarities`、`required_picks` | `test_affix_count_and_categories_follow_rarity`、`test_rare_and_epic_weapons_carry_one_keyword_affix_when_it_fits` |
| 武器屬性偏好 50%／25%＋25% | `_attribute_weight` | `test_single_attribute_weapons_prefer_their_scaling_attribute`、`test_dual_attribute_weapons_split_the_preference` |
| 普攻附加元素 8 種、10 點 | `affix_attack_*` | `test_affix_points`、`test_whitelist_has_all_66_affixes_in_11_categories` |
| 武器元素：主手、不上法杖、15 點、每件最多 1 條 | schema＋`_affix_slot_problems`＋`weapon_element_problems` | `test_weapon_element_affixes_appear_but_never_on_elemental_weapons`、`test_staffs_never_get_a_weapon_element_from_validation`、`test_two_weapon_element_affixes_on_one_item_are_rejected` |
| 元素優先順序（06 6.10 A′）與實戰一致 | `weapon_affix_element` | `test_attack_element.py`（不變，全過）＋`test_weapon_element_3k1.py`：6 種元素的普攻與武器技（卡片＝實戰）、普攻附加只贏普攻、附魔最優先、只看主手、**法杖不被覆寫** |
| 新武器、副手可當底材 | `_weapon_base`／`_offhand_base` | `test_new_weapons_and_offhands_are_used_as_bases` |
| 確定性 | 只用傳入的 `Rng` | `test_same_seed_same_item_and_different_seeds_differ`、`test_generator_only_uses_the_given_rng` |
| 每件通過物品預算與穿戴驗證 | 產生後自我檢查 | `test_every_sampled_item_passes_budget_item_and_wear_checks`（1152 件） |

## 抽樣統計（等級 1～6 × 8 部位 × 每格 200 種子；腳本在 scratchpad，不進 repo）

| 稀有度 | 件數 | 平均詞條數 | 平均填滿 | 最低填滿 | 條數低於下限（下修） | 含 build 詞條 | 只有基礎加成 |
|---|---|---|---|---|---|---|---|
| 普通 | 9600 | 0.47 | 91.5% | 75.0% | 0% | — | 53.1% |
| 優良 | 9600 | 1.49 | 93.8% | 70.0% | 0% | — | 0% |
| 稀有 | 9600 | 1.50 | 93.5% | 70.0% | 62.5% | 58.3% | 0% |
| 史詩 | 9600 | 1.60 | 94.0% | 70.0% | 77.1% | 58.3% | 0% |

| 部位 | 稀有下修 | 史詩下修 | 稀有含 build | 史詩含 build |
|---|---|---|---|---|
| 主手 | 0% | 17% | 100% | 100% |
| 副手 | 100% | 100% | 33% | 33% |
| 頭 | 33% | 83% | 83% | 83% |
| 身體 | 33% | 67% | 83% | 83% |
| 手 | 100% | 100% | 17% | 17% |
| 腳 | 100% | 100% | 17% | 17% |
| 項鍊 | 33% | 50% | 100% | 100% |
| 戒指 | 100% | 100% | 33% | 33% |

- 稀有度抽樣（100000 次）：普通 40.07%、優良 24.99%、稀有 20.01%、史詩 12.97%、傳說 1.96%。
- 武器屬性偏好（優良主手，抽到屬性詞條時）：敏捷系單屬性武器 敏捷 46.7%、其餘 9.6～11.7%；力量系 力量 45.5%；錘（體質／力量）20.8%／28.1%、其餘 11.8～13.5%；鞭（敏捷／感知）24.4%／26.3%。
- 等級 7～10：只有 **等級 9、10 的優良主手** 產生不出來（詞條預算 38、42；兩條數值類最多約 24 點，達不到 70%），其餘都可以。roguelite 一輪是 1～6 級，不受影響。

## 測試

- 新增：`tests/content/test_item_gen.py`（99 個）、`tests/engine/test_weapon_element_3k1.py`（14 個）。
- 修改：白名單條數 51 → 66（`test_equipment_content.py`、`test_gear_api.py`）、`LOG_FORMAT` `/71`（8 個檔案）。
- 執行：ruff check、ruff format --check、mypy（src＋tests）、lint-imports（7 kept）通過；pytest `tests/engine tests/content tests/roguelite tests/api tests/narrative tests/skillgen` 6726 passed、1 skipped；`-m "slow or not slow" tests/cli` 148 passed（含重播）；vitest 973 passed；build 通過。沒有跑 `scripts/check.py` 全量。

## 影響盤點（規格第 3 節）

| 項目 | 這段的影響 |
|---|---|
| 一輪節點流程、`RunState`、`run auto`、營火、模擬報表 | 沒動（3K-2） |
| 存檔格式 | `RunSave.engine` 跟著 `LOG_FORMAT` 變成 `/71`：`/70` 的 **戰鬥中** 存檔無法重播（和以往升版相同） |
| 開戰 `Loadout` | `ItemDef` 多兩個有預設值的欄位；舊資料照讀 |
| 穿戴驗證、全身上限 | 新增武器元素的兩條檢查；其餘不變 |
| 詞條遞減與硬上限 | 武器元素是非數值類（同 id 只生效 1 條）；基礎加成的傷害計入全身 +50% 上限 |
| 常駐數值、資源上限（3H） | 沒動；產生的屬性詞條照舊併進總屬性 |
| 測試模式、裝備卡片與比較（3-32b） | 測試模式的詞條選單多 15 條；**API 物品卡（`GearItemInfo`）還沒顯示基礎加成**，產生的物品要到 3K-2 才進卡片 |
| 3I 新武器與副手 | 全部可當底材（測試涵蓋） |

## 待 PM 決定

1. **防具沒有基礎數值資料**：8.12 的五種身體防具（防禦、敏捷加到防禦、特性）與頭／手／腳的小防禦都沒有引擎資料。產生器只分配詞條部分；身體的造型（布袍、皮甲、鎖甲、板甲、外套）只來自外觀清單，**不影響規則**。8.12「屬性詞條依防具類型偏好」也沒做（設計沒有機率數字，防具類型也還不是規則資料）；副手的屬性偏好規格沒寫，也沒做。
2. **設計沒給的單位價（實作者初值，放在 `item_gen.yaml`）**：傷害 +2%＝3 點（借第 5 點的換算）；條件成立率逐條分類（站在高處＝偶爾、本回合沒移動＝常見、HP 低於 50%＝少見、火槍站定＝常見）；代價型的「受到的傷害」「冷卻」「回合開始失去 HP」單位價。
3. **普通稀有度的基礎加成**：照字面只在「沒有詞條時」換算；有 1 條詞條的普通物品要自己達到 70%。項鍊、戒指沒有規定 → 當成「防具」換成防禦值 +%。基礎加成的傷害計入全身 +50% 上限。
4. **「含 1 條技能強化」當成恰好 1 條**（`categories` 不列 keyword，只從 build 詞條出現）。
5. **稀有度表沒列的類別**：充能、代價型不產生；動作、反應、改變規則照第一季不掉落。優良照 8.21.6（數值＋條件數值），沒有採用 8.7「開始出現觸發詞條」。
6. **「不出現在法杖上」的範圍**：實作成「本身有元素的武器都不能掛」（三種法杖＋權杖〔神聖〕）；圖騰杖（物理）可以掛。普攻附加元素沿用既有規則（有元素的武器不能掛）。
7. **召喚物不繼承武器元素詞條**（6.29.6 列的可繼承項目沒有它，採保守做法）。
8. **小部位稀有／史詩大量下修**（上表）：副手、手、腳、戒指在 1～6 級的詞條預算只有 4～9 點，而技能強化固定 8 點、「本回合沒移動：防禦」最低 9 點，所以通常只放得下 1 條；稀有起的 build 詞條也常放不下（手、腳只有 17%）。8.22 已預告會下修，但比例很高，是否調整部位比例、點數或白名單範圍請決定。
9. **等級 9、10 的優良主手產生不出來**：白名單數值範圍（屬性最多 +4、HP 最多 +16）撐不起 38～42 點的預算。roguelite 用不到，但 Phase 5 掉落會碰到。
10. **驗證器不檢查條數下限與 build 詞條是否存在**（因為允許下修）；傳說物品不檢查預算（現有傳說項鍊的改變規則 40 點遠大於項鍊預算）。
11. **名稱**：「稀有度＋底材名」；同名物品以 id 區分（3K-2 若要避免撞名，可比照技能名加「（二）」）。
12. 等級 10 以上沿用最後一段斜率外插（+30／級）。
13. 同一件可以同時有 1 條普攻附加元素與 1 條武器元素（普攻看前者、武器技看後者）；產生器限制兩族各最多 1 條。
