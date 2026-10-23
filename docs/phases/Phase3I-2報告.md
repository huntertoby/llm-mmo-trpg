# Phase 3I-2 完成報告｜副手（圓盾、塔盾、法書、法器珠）

規格：`docs/phases/Phase3I計畫.md` 第 0～3 節（3I-2 列）；設計：`docs/design/08-裝備.md` 8.11 副手表與「提前武器的特性細節」。

## 1. 做了什麼

| 項目 | 內容 | 檔案 |
|---|---|---|
| 副手資料 | 新資料檔 `offhands.yaml`（`OffhandDef`／`OffhandTable`）：縮放屬性（雙屬性規則同武器，schema 強制同類 `max`、混搭 `mean`）與常駐特性參數 `block_bonus`、`ranged_cover`、`move_penalty`、`spell_damage_permille`、`spell_range_bonus` | `content/offhands.yaml`、`content/battle.py`、`content/registry.py` |
| 物品 | `ItemDef.offhand`（id）＋`offhand_def`（載入時嵌入定義，快照自成一體）；新增 4 件副手本體物品（`item_offhand_*`，無詞條）；舊副手物品（`item_test_shield` 等）沒有 `offhand`，行為不變 | `content/equipment.py`、`content/library.py`、`content/items.yaml` |
| 引擎 | `GearState.offhand`；塔盾半掩護（`combat._shield_cover`，`Cover.object_id` 可為 None）；塔盾移動 −1（`build_gear` 在移動上限之後扣）；法書（`modifiers.offhand_spell_permille` 併入全身 +50% 上限）；法器珠（`shape_reach` 對 `category: spell` 且射程不為 0 者 +1）；圓盾（`block_multiplier` 只強化 `block` 反應） | `engine/gear*.py`、`rules/combat.py`、`modifiers.py`、`skills/targeting.py`、`reactions.py` |
| 卡片 | `OffhandDef.trait_lines_zh`（縮放屬性行＋每個特性一行，數值取自資料與 `core.half_cover_hit_penalty`；圓盾附「目前 +N%」）；`UnitView.offhand_name_zh／offhand_traits_zh`、裝備目錄 `offhand*`／`offhands`、一輪英雄面板 | `engine/view.py`、`api/gear*.py`、`api/run_*.py` |
| 前端 | 單位資訊、一輪英雄面板顯示副手與特性行；裝備物品清單顯示副手特性；手動組副手可選種類（`CustomDraft.offhand`） | `client/src/ui/`、`run/`、`gear/` |
| 格式 | `LOG_FORMAT` `/63` → `/64`（runner 文件字串、測試 `trpg-battle-log/64`、`test_24c`） | `engine/runner.py` |
| 重產 | `skill_icons.json`、`glossary.json`、`unitDolls.json`（無差異）、`openapi.json`、`schema.d.ts`；CLI 快照重產無差異 | |

## 2. 規則對照

| 規則句 | 實作 | 測試 |
|---|---|---|
| 圓盾 力量／體質取較高 | `attr_mode: max`，`scaling_value` | `BLOCK_TABLE`、schema 測試 |
| 圓盾格擋反應強化，依縮放 | 格擋多減傷 ＝ 縮放值 × 5‰，最多 100‰（**初值，見待決 1**） | `test_round_shield_strengthens_block...`（卡片 %＝實際 `block_permille`） |
| 塔盾 遠程打你命中 −2（同半掩護） | 數值用 `half_cover_hit_penalty`；近戰／長柄、穿透（長槍）不吃；與場上掩護物不疊加 | `COVER_TABLE` 10 列 |
| 攻擊者高 1 層以上無視 | 攻擊者地形高度 > 持有者即無視 | 表中「攻擊者高 1 層」「低 1 層」 |
| 塔盾 移動 −1 | `merged["move"]` 扣在上限之後；速度與回合移動點數都少 1 | `test_tower_shield_slows_the_holder_by_one` |
| 法書 法術技傷害 +10%，計入 +50% 上限 | `offhand_spell_permille` 與其他正向加成合計後 `cap_damage_bonus` | `TOME_TABLE`、上限測試、實際 `multiplier_permille` 1100 |
| 法器珠 法術技施放距離 +1，不加範圍，自身不受影響 | `shape_reach`；武器技、射程 0／`self` 不加；範圍格數不變 | `REACH_TABLE`、實際施放距離 4 |
| 雙手武器不能拿副手 | 既有 `loadout_problems`；對四種新副手各測 | 參數化 24 例、API |

## 3. 測試

- ruff check／format、mypy（src、tests）、`lint-imports`（7 kept）通過。
- pytest：engine／content／skillgen／roguelite／narrative／api／sim 6092 passed；`-m "slow or not slow" tests/cli` 148 passed（CLI 快照無差異）。新增 `tests/engine/test_offhands_3i2.py`（66 例）、`tests/api/test_gear_api.py` 2 例、前端 1 例。
- 重播：`trpg battle --map open_plain --seed 3 ... --log-json` → `battle replay` 通過；含裝備快照的 API 戰鬥重播（`test_gear_api`）通過。
- 前端：`tsc`、`build` 通過；vitest 910 通過、**1 失敗：`floatCardRule.test.ts` 的 `role=tooltip` 規則被 `client/src/dev/layoutSmoke.ts`（查詢 `[role="tooltip"]`）觸發，檔案與測試皆不是本段修改，應為既有問題**（未在乾淨基底重跑確認）。
- 排版煙霧檢查（埠 8013，先 `localStorage.clear()`）：1600×900、底部最矮、800×600 全 PASS。**未在畫面上親眼看**：副手特性行的實際版面（以型別檢查與單元測試代替）。
- 模擬：未跑（規格未要求；副手尚未進任何 sim build）。

## 4. noqa

無新增。

## 5. 待 PM 決定

1. **圓盾「格擋反應強化」數值**：設計未寫，採最保守：多減傷 ＝ 縮放屬性值 × 5‰、最多 +10%（格擋 50% → 最高 60%），資料在 `offhands.yaml` 的 `block_bonus`。
2. 塔盾、法書、法器珠的縮放屬性目前只在卡片顯示，**對效果沒有數值影響**（設計只有圓盾的效果「依縮放」）；是否要讓它們也隨屬性成長？
3. **開局**：一般開局只選武器，目前沒有選副手的流程，副手只能由測試模式／裝備測試介面挑（目錄多了 4 件副手本體）。是否要在開局或營火加入副手選擇？
4. 副手本體物品沒有詞條（測試 `1..3 條詞條` 放寬為「副手本體可為 0」）。
5. 塔盾移動 −1 的速度為 0 以下時下限 0；與其他移動加成的上限（+2）互相獨立，沒有「移動下限」規則。
6. 戰鬥文字紀錄對塔盾掩護只顯示「半掩護 −2」，沒有來源名稱（無物件）。
7. 既有 `item_g3b_bulwark_shield`（kite_shield）仍是無特性的舊物品，未改。
