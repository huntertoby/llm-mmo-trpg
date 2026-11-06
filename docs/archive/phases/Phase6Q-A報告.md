# Phase 6Q-A 報告：情境覆蓋表

> 來源：玩法 PM 的「種族讓任務過易」盤點第 5 節 A（內容檢查工具，不碰規則）。實作者：implementer agent，2026-11-04。

## 1. 做了什麼

- `src/trpg/world/situation_coverage.py`：計算核心。只讀內容，不跑戰鬥、不呼叫 LLM、不改狀態。
  - `inputs_from_library`：從內容庫取資料，包括情境規則、各區模板、`unlock_only` 骨架、地點建議等級、種族表、開局屬性與每級屬性點、屬性修正公式。
  - `build_coverage`：產生覆蓋表，含每區 × 每族的模板清單和兩種標記。
  - `best_case`：算最好情況的成功率。
  - `format_report`：輸出 Markdown 表格；`quiet=True` 時只印摘要和被標出的項目。
- `scripts/situation_coverage.py`：CLI，參數有 `--quiet`、`--warn-exit`、`--content DIR`。
  - 預設結束碼 0。
  - 加 `--warn-exit` 時，有被標出的項目回傳 3。
  - 內容載入失敗回傳 1。
- `scripts/check.py`：最後加一步 `situation coverage`，執行 `--quiet --warn-exit`。
  - `Step` 新增兩個欄位：`script`（用 `sys.executable` 執行專案內的腳本）和 `warn_only`。
  - `warn_only` 的步驟結束碼非 0 時，摘要標黃色「警告」，不算失敗，也不影響總結束碼。
  - `_full_step` 改用 `dataclasses.replace`，避免新欄位被丟掉；行為不變。
- 實際內容跑一次約 25 秒，大部分是載入內容庫的時間。

## 2. 計算方式

### 2.1 能吃到種族加值的模板

模板同時符合下面兩條才算：

1. 模板的 `methods` 含該族的 `race_methods`。
2. 模板的 `attributes` 和該方法的常見屬性有交集。不符合時提議不合法（`proposal_problems`），種族加值吃不到。

計的是**模板數**，不是方法出現的次數。

- 玩法 PM 盤點的數字（雲嶺人類 17、龍裔 2 等）比這裡多，推測是把弱點（`weaknesses[].methods`）的方法也算進去了。
- 例：雲嶺模板層級含 `lore` 的有 12 個，整份檔案出現 `lore` 18 次。

### 2.2 最好情況成功率

和 `trpg.world.situations.resolve_situation` 的結算一致：

- **總值**＝採用的骰值＋屬性修正＋用心加值＋種族加值；總值 ≥ DC 就成功。
- 沒有自然 1／20 的特例，`_outcome` 只比總值。
- **骰子**：引擎一律擲兩顆 d20。沒有優勢時採第一顆，有優勢時取高。計算時列舉全部 400 種組合，算出成功比例（`success_hits`）。
- **屬性**：
  - 開局屬性 `base_attribute`（10）。
  - 每升一級得 `attribute_points_per_level`（2）點，全部加在這一項，算到「骨架地點建議等級的最高值」為止（`location_level`，即 `level_min`），不超過 `level_cap`。
  - 修正＝`(屬性 − 10) // 2`，同 `attribute_modifier`。
  - 判定只看主角的基礎屬性（`char.hero.attributes`），裝備詞條不算。
- **用心清單**：`care_max`（+2）。拿補給交換，再加上任一條線頭或弱點，就湊得到。
- **種族**：`race_bonus`（+1）。
- **優勢（道具）**：情境判定沒有物品欄位，唯一類似道具的是 `advantage_threads`。模板有這個欄位時，就當作持有。
- **DC**：算兩欄。
  - 「±0」用 `base_dc`。
  - 「−2」用 `base_dc − dc_shift_max`，也就是 LLM 能給的最低難度。

**和引擎的對照**（測試 `test_best_case_matches_engine`）：

- 用兩個實際模板，各跑 30 個種子 × 2 種難度，經 `world_step` 實際結算：
  - `granny_parley`：人類、學識。
  - `convoy_steal`：晶能義體人、靈巧，有優勢線頭。
- 逐場核對：
  - 用心 +2、種族 +1；
  - 優勢模式；
  - `total == roll + bonus`；
  - 成功與否和 `roll ≥ DC − bonus` 一致。

### 2.3 兩種標記

1. **模板少於 3 個**：某區某族能吃加值的模板少於 3 個（`MIN_TEMPLATES = 3`）。
2. **DC ≤ 10 但沒有前置門檻**：`base_dc ≤ 10`（`LOW_DC = 10`），而且模板所屬骨架的 `unlock_only` 不是 `true`。

**「前置門檻」的判斷方式**：只看事件骨架的 `unlock_only: true`。這種骨架只有角色解鎖後才會出現（`events.py` 的候選篩選；18.7.7 信賴的 NPC 說出祕密），目前只有 `granny_past`。

下面這些欄位都**不算**門檻：

- `follows`：只決定優先接線頭，不是門檻（`_followed`）。
- `day_phase`、`weather`：只是出現條件。
- `advantage_threads`：只給優勢，沒有線頭也能判定。
- `once`：只限制次數。

## 3. 實際內容的輸出表（2026-11-04，main 4804c297）

情境覆蓋表：ashen_waste 16 個、cloud_ridge 30 個模板；20 列（區域 × 種族）；標出 6 列模板少於 3 個、0 個 DC ≤ 10 沒有前置門檻。

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

計算用的等級（模板數）：

- 雲嶺：1 級 6、2 級 3、3 級 7、4 級 6、5 級 6、6 級 2。
- 荒原：1 級 1、5 級 1、6 級 5、7 級 7、8 級 2。

## 4. 被標出的項目

**能吃種族加值的模板少於 3 個（6 列）**：

| 區域 | 種族 | 方法 | 模板數 |
|---|---|---|---:|
| 荒原 | 狐族 | 交涉 | 2 |
| 荒原 | 龍裔 | 威嚇 | 1 |
| 荒原 | 矮人 | 機關 | 2 |
| 荒原 | 晶能義體人 | 靈巧 | 2 |
| 雲嶺 | 龍裔 | 威嚇 | 1 |
| 雲嶺 | 矮人 | 機關 | 2 |

**DC ≤ 10 但沒有前置門檻：0 個。**

- 雲嶺的 `granny_parley`、`granny_notice`（DC 8）屬於 `unlock_only` 的 `granny_past`，不標出。
- 補充：這兩個模板的地點 `mist_ferry` 沒有建議等級，照 1 級算。人類用學識的最好情況是 80%（±0），盤點文件以屬性 14 估的是 90%。

**其他觀察（沒有標出，給玩法 PM 參考）**：

- `climb`（攀爬跳躍）目前沒有對應的種族。#138 把狐族改成獸耳族（攀爬跳躍）後，`race_methods` 改了就會自動算進表裡。
  - 照現在的內容：雲嶺含 `climb` 的模板有 2 個（`lingzhi_climb`、`envoy_take_cover`），荒原 0 個。
  - 屆時獸耳族兩區都會被標出。
- 基準 DC 11～12 的模板共 8 個：DC 11 一個（雲嶺 `acolyte_find_way`），其餘是 DC 12。LLM 給 −2 後是 DC 9～10，而且都沒有門檻（見待 PM 決定 2）。

## 5. 檔案清單

- 新增：
  - `src/trpg/world/situation_coverage.py`
  - `scripts/situation_coverage.py`
  - `tests/world/test_situation_coverage.py`
  - `docs/archive/phases/Phase6Q-A報告.md`
- 修改：`scripts/check.py`
- 沒有改內容與規則。

## 6. 測試

`tests/world/test_situation_coverage.py` 共 10 個測試：

- 假內容：計數、DC 分布、屬性不合法時不算、沒有方法的種族、兩種標記。
- 數值：最好情況的數值；`success_hits` 的邊界，含優勢。
- 輸出：quiet 輸出只有摘要和標記。
- 和引擎的對照：2 個實際模板。
- 實際內容：渡婆婆模板沒有被標出。
- `check.py`：這一步結束碼 0／3／1 時，分別標為通過、警告、警告。

`tests/world/test_situations.py` 一起跑：共 43 個通過。

靜態檢查：

- ruff check、ruff format --check：全部通過。
- `mypy src` 和本段的檔案：通過。
- lint-imports：13 個 kept。
- 全量 `mypy`（含 tests、scripts）有 12 個**既有**錯誤，都在本段沒碰的檔案：`f4_newbie_sim.py`、`sim_race_138.py`、`test_world_store_r3.py` 等。

## 7. 待 PM 決定

1. **等級用哪一個？** 目前用骨架地點的 `level_min`（引擎給 xp 用的 `location_level`）。城鎮類地點沒有等級，照 1 級算。
   - 例：荒原 `veteran_listen`（`ember_market`）、雲嶺霧渡鎮與渡口的 6 個模板。
   - 這些模板的最好情況會偏低。
   - 要不要改成「沒有等級時用區域的 `level_min`」，或乾脆用等級上限？保守預設：維持 `level_min`／1 級。
2. **「DC ≤ 10」比哪一個 DC？** 目前比 `base_dc`。若要把 LLM −2 也算進去（`base_dc − 2 ≤ 10`），雲嶺會多標出 DC 11～12 的模板。保守預設：只比 `base_dc`，照規格原文。
3. **門檻的範圍**：目前只認 `unlock_only`。之後若有任務旗標、好感度直接鎖模板的欄位，要再加進判斷。
4. **跟盤點文件數字不同**：本表計模板數，盤點文件推測計方法出現次數（含弱點）。原則 4「每區每族至少 3 個模板」照模板數算，請玩法 PM 確認。
5. **輸出的位置**：目前只在 `check.py` 最後印警告，沒有寫入檔案。需要時可加 `--out` 存成報表。
