# Phase 6Q-B 報告：覆蓋表口徑與種族方法補齊

> 來源：玩法 PM「種族讓任務過易」盤點第 7 節，以及開發 PM 轉達的三項口徑。這段只改內容與工具，不改規則和數值。實作者：implementer agent，2026-11-04。基底：main b8207d6e。

## 1. 做了什麼

### 1.1 覆蓋表口徑（`src/trpg/world/situation_coverage.py`）

1. **城鎮地點的等級**：地點沒有建議等級（town、gate）時，改用該區地點圖的 `level_min`，不再照 1 級算。骨架沒有地點時也用區域下限。
   - 受影響的模板：荒原 `veteran_listen`（灰燼市集），從 1 級改成區域下限。荒原人類、狐族的最好情況下限因此從 60% 升到 75%、80%。
   - 雲嶺的區域下限是 1，霧渡鎮、渡口的 6 個模板數字不變。
2. **DC − 2 另列資訊**：新增 `CoverageReport.shifted_low_dc`。收錄條件是基準 DC > 10、`基準 DC − dc_shift_max ≤ 10`，而且沒有前置門檻。
   - 摘要行加「資訊 N 個 DC − 2 ≤ 10」。
   - 完整輸出另列「資訊（不警告）」清單；quiet 輸出（`check.py` 用）不列。
   - 不算進 `--warn-exit`。
   - 「DC ≤ 10」警告照舊比基準 DC。
3. **門檻判斷**：新增 `skeleton_gated(skeleton)`，`unlock_only` 或 `follows` 非空就算門檻；`day_phase`、`weather`、`once` 不算。警告文字改成「（unlock_only／follows）」。

### 1.2 補種族方法（`content/world/situations/*.yaml`）

| 區 | 模板 | 加的方法 | 補的屬性 | 說明 |
|---|---|---|---|---|
| 雲嶺 | `peddler_safe_path` | `intimidate` | — | 原有 str，威嚇能用 |
| 雲嶺 | `bear_slip_away` | `intimidate` | `wil` | 原屬性 wis、dex 都不是威嚇的常見屬性 |
| 雲嶺 | `furnace_shut_down` | `mechanism` | — | 原有 int |
| 荒原 | `caravan_shortcut` | `intimidate` | `wil` | 原屬性 wis、int |
| 荒原 | `laotie_disarm` | `intimidate` | `wil` | 原屬性 int、dex |
| 荒原 | `stele_find_half` | `mechanism` | `int` | 原屬性 wis、str |
| 荒原 | `well_mechanism` | `finesse` | `dex` | 原屬性 int、str |

- 盤點第 7 節只寫「必要時一併補屬性」，沒有指定要補哪一個。這裡採最保守的做法：只補一個屬性，用該方法在 `situation_rules.yaml` 裡列的第一個常見屬性（威嚇補 `wil`、機關補 `int`、靈巧補 `dex`）。
- 新屬性一律接在最後，不動「開頭＝骨架解法屬性」的規定。補上後每個模板都是 3 個方法；有補屬性的模板是 3 個屬性，都在 schema 上限內。
- 弱點（`weaknesses[].methods`）沒有加新方法。
- 兩個檔頭各加了兩行註解，說明 6Q-B 改了什麼。
- 攀爬跳躍那 5 列沒做（等 #138）。

### 1.3 對 LLM 提議的影響

情境判定的 LLM 輸入是由模板產生的，所以這 7 個模板的 LLM 輸入都變了：

- JSON schema 的 `method` enum 多一個值；有補屬性的模板，`attribute` enum 也多一個值（`src/trpg/llm/situation.py` 的 `situation_schema`）。
- 提示詞的 `<methods>` 區塊多一列方法及可用屬性（`_methods_payload`）。例如 `peddler_safe_path` 新增的威嚇只列 `str`，因為模板沒有 `wil`。
- 系統提示詞的文字沒有改。
- 降級提議（`default_proposal`）照第一個屬性和能用它的第一個方法挑，新方法都排在最後，所以降級結果不變。
- 前端事件卡的「方法」文字（`world_story_view` 的 `methods_zh`）也會多列一個方法。

`tests/llm/test_situation_propose.py::test_schema_enums` 原本寫死 `peddler_safe_path` 的方法 enum，已改成含 `intimidate`。

## 2. 覆蓋表：改前與改後

### 2.1 改前（main b8207d6e，舊口徑）

情境覆蓋表：ashen_waste 16 個、cloud_ridge 30 個模板；20 列（區域 × 種族）；標出 6 列模板少於 3 個、0 個 DC ≤ 10 沒有前置門檻

| 區域 | 種族 | 方法 | 模板數 | DC 分布 | 最好情況（±0） | 最好情況（−2） |
|---|---|---|---:|---|---|---|
| ashen_waste | 人類（human） | lore | 7 | 12×1 13×3 14×2 15×1 | 60%～85% | 70%～95% |
| ashen_waste | 精靈（elf） | notice | 4 | 14×2 15×2 | 70%～80% | 80%～90% |
| ashen_waste | 狐族（fox） | parley | 2 | 12×1 13×1 | 60%～85% | 70%～95% |
| ashen_waste | 龍裔（dragonkin） | intimidate | 1 | 13×1 | 85% | 95% |
| ashen_waste | 矮人（dwarf） | mechanism | 2 | 13×1 14×1 | 75% | 85% |
| ashen_waste | 晶能義體人（cyborg） | finesse | 2 | 13×1 15×1 | 70%～75% | 80%～85% |
| ashen_waste | 獸人（orc） | force | 3 | 13×1 14×1 15×1 | 75%～85% | 85%～95% |
| ashen_waste | 角魔（fiend） | uncanny | 3 | 14×1 15×2 | 75%～80% | 85%～90% |
| ashen_waste | 鱗族（scalefolk） | stealth | 3 | 14×2 15×1 | 70%～80% | 80%～90% |
| ashen_waste | 海民（seafolk） | endurance | 3 | 13×1 14×1 15×1 | 75%～85% | 85%～95% |
| cloud_ridge | 人類（human） | lore | 12 | 8×2 11×1 12×2 13×5 14×2 | 60%～80% | 70%～90% |
| cloud_ridge | 精靈（elf） | notice | 9 | 8×1 12×1 13×6 15×1 | 60%～87% | 70%～93% |
| cloud_ridge | 狐族（fox） | parley | 7 | 8×1 12×3 13×3 | 60%～80% | 70%～90% |
| cloud_ridge | 龍裔（dragonkin） | intimidate | 1 | 13×1 | 65% | 75% |
| cloud_ridge | 矮人（dwarf） | mechanism | 2 | 12×1 15×1 | 60%～65% | 70%～75% |
| cloud_ridge | 晶能義體人（cyborg） | finesse | 3 | 12×1 15×2 | 60%～87% | 70%～93% |
| cloud_ridge | 獸人（orc） | force | 5 | 12×2 13×1 14×1 15×1 | 60%～87% | 70%～93% |
| cloud_ridge | 角魔（fiend） | uncanny | 3 | 13×1 14×1 15×1 | 55%～80% | 65%～90% |
| cloud_ridge | 鱗族（scalefolk） | stealth | 3 | 12×1 13×1 14×1 | 65%～70% | 75%～80% |
| cloud_ridge | 海民（seafolk） | endurance | 9 | 11×1 13×2 14×4 15×2 | 55%～87% | 65%～93% |

警告（6 列）：荒原狐族 2、荒原龍裔 1、荒原矮人 2、荒原晶能義體人 2、雲嶺龍裔 1、雲嶺矮人 2。

### 2.2 改後（新口徑＋補方法）

情境覆蓋表：ashen_waste 16 個、cloud_ridge 30 個模板；20 列（區域 × 種族）；標出 1 列模板少於 3 個、0 個 DC ≤ 10 沒有前置門檻；資訊 6 個 DC − 2 ≤ 10

| 區域 | 種族 | 方法 | 模板數 | DC 分布 | 最好情況（±0） | 最好情況（−2） |
|---|---|---|---:|---|---|---|
| ashen_waste | 人類（human） | lore | 7 | 12×1 13×3 14×2 15×1 | 75%～85% | 85%～95% |
| ashen_waste | 精靈（elf） | notice | 4 | 14×2 15×2 | 70%～80% | 80%～90% |
| ashen_waste | 狐族（fox） | parley | 2 | 12×1 13×1 | 80%～85% | 90%～95% |
| ashen_waste | 龍裔（dragonkin） | intimidate | 3 | 13×3 | 75%～85% | 85%～95% |
| ashen_waste | 矮人（dwarf） | mechanism | 3 | 13×1 14×1 15×1 | 75%～80% | 85%～90% |
| ashen_waste | 晶能義體人（cyborg） | finesse | 3 | 13×1 14×1 15×1 | 70%～75% | 80%～85% |
| ashen_waste | 獸人（orc） | force | 3 | 13×1 14×1 15×1 | 75%～85% | 85%～95% |
| ashen_waste | 角魔（fiend） | uncanny | 3 | 14×1 15×2 | 75%～80% | 85%～90% |
| ashen_waste | 鱗族（scalefolk） | stealth | 3 | 14×2 15×1 | 70%～80% | 80%～90% |
| ashen_waste | 海民（seafolk） | endurance | 3 | 13×1 14×1 15×1 | 75%～85% | 85%～95% |
| cloud_ridge | 人類（human） | lore | 12 | 8×2 11×1 12×2 13×5 14×2 | 60%～80% | 70%～90% |
| cloud_ridge | 精靈（elf） | notice | 9 | 8×1 12×1 13×6 15×1 | 60%～87% | 70%～93% |
| cloud_ridge | 狐族（fox） | parley | 7 | 8×1 12×3 13×3 | 60%～80% | 70%～90% |
| cloud_ridge | 龍裔（dragonkin） | intimidate | 3 | 12×1 13×2 | 60%～70% | 70%～80% |
| cloud_ridge | 矮人（dwarf） | mechanism | 3 | 12×1 13×1 15×1 | 60%～75% | 70%～85% |
| cloud_ridge | 晶能義體人（cyborg） | finesse | 3 | 12×1 15×2 | 60%～87% | 70%～93% |
| cloud_ridge | 獸人（orc） | force | 5 | 12×2 13×1 14×1 15×1 | 60%～87% | 70%～93% |
| cloud_ridge | 角魔（fiend） | uncanny | 3 | 13×1 14×1 15×1 | 55%～80% | 65%～90% |
| cloud_ridge | 鱗族（scalefolk） | stealth | 3 | 12×1 13×1 14×1 | 65%～70% | 75%～80% |
| cloud_ridge | 海民（seafolk） | endurance | 9 | 11×1 13×2 14×4 15×2 | 55%～87% | 65%～93% |

警告（1 列）：荒原狐族交涉 2 個，是預期內的結果（盤點第 7 節：#138 寫入後交涉沒有對應種族）。

資訊（不警告）：DC − 2 ≤ 10，而且骨架沒有前置門檻：

- 荒原 `veteran_listen`（骨架 `tavern_veteran`）：DC 12→10
- 雲嶺 `peddler_safe_path`（骨架 `wounded_peddler`）：DC 12→10
- 雲嶺 `acolyte_find_way`（骨架 `lost_acolyte`）：DC 11→9
- 雲嶺 `elder_patience`（骨架 `pine_elder_go`）：DC 12→10
- 雲嶺 `storyteller_tale`（骨架 `tavern_storyteller`）：DC 12→10
- 雲嶺 `fox_persuade`（骨架 `fox_traveler`）：DC 12→10

驗收：龍裔、矮人、晶能義體人在兩區都是 3 個，達標。

## 3. 檔案清單

- 修改：
  - `src/trpg/world/situation_coverage.py`
  - `tests/world/test_situation_coverage.py`
  - `content/world/situations/cloud_ridge.yaml`
  - `content/world/situations/ashen_waste.yaml`
  - `tests/llm/test_situation_propose.py`：方法 enum 加 `intimidate`
- 新增：`docs/archive/phases/Phase6Q-B報告.md`
- 規則檔（`situation_rules.yaml`）、引擎、`scripts/` 都沒改。

## 4. 測試

- `tests/world/test_situation_coverage.py`：13 個，比原本多 3 個，每項口徑各一個：
  - `test_town_location_uses_region_level_min`
  - `test_shifted_low_dc_is_info_only`
  - `test_gate_counts_unlock_only_and_follows`
- 相關測試一起跑（`-n 8`），178 個全過：
  - `tests/content/test_world_situations.py`
  - `tests/llm/test_situation_propose.py`
  - `tests/world/test_situations.py`
  - `tests/world/test_situation_coverage.py`
  - `tests/world/test_situation_aliases.py`
  - `tests/world/test_affinity.py`
  - `tests/world/test_growth.py`
  - `tests/test_architecture.py`
- 事件卡 API：`tests/api/test_world_story.py`、`test_opportunity_offer_view.py`、`test_newcomer_api_6f2.py`，23 個全過。
- `trpg content check`：通過。
- 靜態檢查：ruff check、ruff format --check、`mypy src`、lint-imports（13 kept）都通過。
- 沒跑全量，沒跑前端 vitest。`client/src/world/story.test.ts` 只把 `peddler_safe_path` 當字串 fixture，跟內容無關。

## 5. 待 PM 決定

1. **補的屬性**：盤點沒有指定要補哪個屬性。目前一律補該方法的第一個常見屬性，威嚇補 `wil` 而不是 `str`。
   - `bear_slip_away`、`caravan_shortcut`、`laotie_disarm` 因此多了 wil。
   - 若玩法 PM 想讓威嚇走 str（「嚇住熊」偏力量），改一個字就行，覆蓋表結果不變。
2. **弱點沒加新方法**：用心清單 ④ 的弱點方法維持原樣，所以新方法吃不到「針對弱點」。這是保守做法；要不要讓新方法也能針對弱點，請玩法 PM 決定。
3. **`follows` 算門檻的實際效果**：引擎裡 `follows` 只決定「優先接線頭」，沒有線頭時骨架照樣能出現（6Q-A 報告 2.3）。照玩法 PM 的口徑，覆蓋表把它當門檻，所以這類骨架的低 DC 模板不會被標出。
   - 目前兩區 DC ≤ 10 的模板只有渡婆婆那兩個，不受影響。
   - 若之後要讓 `follows` 真的擋住骨架，那是規則改動，要另外決定。
4. **新的資訊項**：雲嶺 `peddler_safe_path` 補威嚇後，龍裔在雲嶺有一個 DC 12→10 的無門檻模板。這只是資訊，沒有警告。
