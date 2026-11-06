# Phase 3K-2c 報告：物品基礎份額照 08 8.22 換算

## 做了什麼

- `content/item_gen.yaml` 的 `base_strength` 改成基礎份額換算（原本的單位價 `weapon_damage`／`armor_defense`／`small_defense` 移除）：`weapon_reference_permille: 4500`（1d8 平均）、`body_defense`（布袍 1、外套 2、皮甲 3、鎖甲 5、板甲 7）、`body_reference: 3`（皮甲）、`fallback_level: 1`。
- `trpg.content.item_budget`：新增 `base_pool(rules, level, slot)` ＝ 部位預算 − 詞條預算；`item_base_points` ＝ 池 × 底材比例。底材比例：武器 ＝ （骰平均＋固定傷害）× 打擊數 ÷ 1d8 平均；身體 ＝ 基礎防禦 ÷ 3；副手、頭、手、腳 ＝ 1（整個池）；項鍊、戒指池為 0。
- `item_strength`／`item_score`／比較行／`auto_gear_pick` 自動跟著變；`item_points`（物品預算檢查，只算詞條）未動。沒有物品等級的物品（初始裝備、`base_<武器>`）用 `fallback_level`（1）。

## 基礎份額池（部位預算 − 詞條預算）

| 部位 | 等級 1 | 等級 5 | 等級 10 |
|---|---|---|---|
| 主手（60：40） | 18 | 36 | 63 |
| 身體（60：40） | 12 | 24 | 42 |
| 副手（60：40） | 6 | 12 | 21 |
| 頭、手、腳（50：50） | 4 | 8 | 14 |
| 項鍊、戒指（0：100） | 0 | 0 | 0 |

底材範例（等級 1 主手）：單手劍 18、匕首 18×2.5/4.5＝10、大劍 18×7/4.5＝28、雙匕首（2 打）20。身體等級 1：布袍 4、皮甲 12、板甲 28。

## 測試

`tests/content/test_item_base_share.py`（部位 × 等級 1／5／10 的池表、各底材比例、骰×打擊數、缺等級退回）；`tests/roguelite/test_gear_offer.py` 的基礎武器／板甲分數改成新值（18、42）。pytest content／roguelite／api／narrative 2101 passed，`-m "slow or not slow" tests/cli` 148 passed；vitest、build 通過；ruff、format、mypy、lint-imports 通過。

## 待 PM 決定

1. 「參考底材」我選 1d8 平均（單手劍）與皮甲，使典型底材拿整池；若要改成「同部位底材平均」或「最強底材拿整池」只需改 yaml 的兩個參考值。
2. 副手沒有基礎數值差異，所有副手一律拿整個池（等級 1 為 6 點）；若要讓盾牌類依防禦區分需先有副手基礎數值。
3. 大武器（如 2d6）基礎份額會超過池（28 > 18），與 8.22 的「部位預算」總量不嚴格守恆；這是「照基礎數值比例分配」的直接結果。
4. 無等級物品固定用等級 1 換算；`run auto` 的種子勝率未重跑（規格未要求）。
