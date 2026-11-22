# Phase E2 報告｜單位規則表（種族、裝備共用；AI 看免疫）

> 規格 `docs/phases/PhaseE2計畫.md`；規則以 `docs/design/08-裝備.md` 8.29「E2」（#175）為準，「同一條規則」的判法照開發 PM 轉述的玩法 PM 補定（2026-11-22，見第 5 節第 1 項）。基準 main `2904f2d1d`（含 E1）。

## 1. Commit

| 項目 | commit |
|---|---|
| 1 共用規則表（純搬移） | `8dd60815b` |
| 2 第 12 類詞條 `terrain` | `5a61592fa` |
| 3 引擎查詢看所有來源、移動上限、顯示（OpenAPI、前端型別、裝備卡） | `620fe3058` |
| 4 AI 看雙方的免疫（開關，預設開） | `bc26f6d86` |
| 5 收尾：`classify.py --check` | `dbc9c10ed` |
| 截圖 | `bb2587001` |
| 合併 main | `b7b7e2d96` |
| 報告 | 最後一個 commit |

## 2. 各項做法

1. **共用規則表**
   - 新模組 `src/trpg/content/unit_rules.py`：規則種類表 `UNIT_RULE_SPECS`、參數欄位 `UNIT_RULE_PARAM_FIELDS`、參數檢查 `unit_rule_param_problems`、permille 上限檢查 `unit_rule_permille_problems`、唯讀介面 `UnitRule`（Protocol）。
   - `races.py` 的 `PASSIVE_RULE_SPECS`、`PassiveRule` 改成共用表的別名，`RacePassive` 的檢查呼叫共用函式；欄位宣告不動、錯誤訊息逐字相同，YAML 格式不變。
   - 驗證：種族相關測試（`tests/content/test_races.py`、`tests/engine/test_race_passives.py`）全過；442 招預算與 78 場（開關關）見第 3 節。
2. **第 12 類 `terrain`（地形規則）**
   - `content/equipment.py`：`AffixCategory`／`AFFIX_CATEGORIES`／中文名「地形規則」／編號 12；`TerrainAffix` 欄位同種族被動（rule＋參數），參數檢查用共用表；屬於非數值類（同 id 只生效 1 條）。
   - `damage_taken_permille` 載入時擋掉，訊息「地形規則不能用 damage_taken_permille（元素減傷是數值抗性，請用數值類的元素抗性詞條）」（開發 PM 裁定）。
   - 跨檔檢查（`gear_checks._terrain_affix_problems`）：天氣、地形 ID 存在；permille 上限同 `races.yaml` 的 `limits`。
   - `affixes.yaml` 沒有加任何一條；`item_gen` 的 `category_points` 不要求 `terrain`（產生器不產，定價在 E6），`affix_points` 對沒定價的類別給 0 點而不是 KeyError。
   - 測試：`tests/content/test_terrain_affix_e2.py`（8 項）；`test_equipment_content` 的「每類都有詞條」改成排除 `terrain`。
3. **引擎查詢看所有來源**
   - 新模組 `src/trpg/engine/rules/unit_rules.py`：
     - `rule_sources`：種族被動先，再依欄位固定順序（同欄位依詞條 ID）看生效中的 `terrain` 詞條。
     - 每條規則有一組「鍵」（`rule_keys`：作用的表面、天氣、地形、地圖標籤；沒有這類參數的規則只有一個鍵）。**每個鍵由第一個給它的來源決定**，後面的來源在這個鍵上沒有效果、不疊加。
     - 判斷集中在 `classify_sources`：鍵全部被前面給過 → 完全重複（標灰）；部分被給過 → 仍生效，重疊的鍵只算一份，卡片註明；戰鬥中的查詢 `first_source` 用同一個規則。
     - `gear_move_room`：裝備的移動加成合計上限（`caps.move_bonus`＝2）扣掉數值詞條已給的移動（上限前合計，先截到上限；塔盾的 −N 不算）。
   - `engine/rules/race.py` 留作轉接層，各查詢函式介面不變，改用 `first_source`；`passive_of` 回傳型別由 `RacePassive` 放寬成 `UnitRule`（第一個該種類的來源）。`passive_active`、`race_element_mods` 照舊只看種族。
   - 移動：新函式 `rule_move_bonus`（`statuses.move_points_for_turn` 改呼叫它），天氣＋表面兩條移動加成裡裝備給的部分合起來受上限；種族給的不受影響。`weather_move_bonus`、`surface_move_bonus` 單獨呼叫時，裝備給的也截到剩餘額度。
   - 顯示：`AffixLineView` 新欄位 `overlap_zh`（預設 `None`）；地形規則完全重複時 `active=false`、`weight_permille=0`、`duplicate_of` 是重複的來源。前端 `TipLine` 加 `aside`（不標灰、後面加註），`PartTip` 顯示；OpenAPI 與 `schema.d.ts` 重產。
   - **卡片上的實際文字**（截圖裡的那三行）：
     - 完全重複（種族）：「走在冰面上不會滑倒（和種族被動「穩健步伐」重複，沒有效果）」
     - 完全重複（另一件裝備，沿用 3-32 的格式）：「火焰表面不會讓你燃燒（和身體的火焰表面不會讓你燃燒重複，沒有效果）」
     - 部分重疊：「走在冰面和水面上不會滑倒（冰的部分和種族重複）」；重疊來源是裝備時寫「和腳的「〇〇」重複」，多個來源用「；」隔開。
   - 測試：`tests/engine/test_unit_rules_e2.py`（12 項）：裝備地形規則生效（穿踏火靴走進火不燃燒、對照組會燃燒）、五種判法各一項（開關完全涵蓋、開關有新參數、開關部分重疊、數值同參數、數值不同參數）、兩件裝備同規則後面那件標灰、移動上限（數值詞條 +2 時靴子給 0、兩條裝備移動共用剩下的 1、種族不受影響）。
4. **AI 看雙方的免疫**
   - 開關：`content/ai_profiles.yaml` 的 `heuristics.scoring.harmful_sees_immunity: true`（`ScoringAiRules`，模型預設也是 `true`）。
   - `ai/utility/position.py` 的 `_harmful(state, xy, unit=None)`：開關開、有給單位時，表面施加的燃燒對 `burn_immune` 的單位不算有害（種族炎膚或裝備的同種規則）；回合開始的傷害照舊算有害；`unit=None` 或開關關時邏輯和改前相同。
   - 呼叫端都傳要評估的單位：`position_value`（自己）、`gains._surface_gains`（前後兩個狀態的敵人各自）、`_tile_value`（被移動的單位）、`_harmed_allies`；`ai/displace.py` 的 `Harmful` 型別多一個單位參數，`tile_harm` 加 `unit`（`skill_estimate` 照舊把 `_harmful` 當回呼傳入）。
   - 測試：`tests/engine/test_ai_immunity_e2.py`（9 項）：預設開；角魔在火上不算有害、毒照樣有害、開關關時照舊；裝備踏火也算；角魔自己的位置不扣 `hazard`；推角魔進火的分數比開關關時低、推一般人開關開關結果相同；傳送估計的 `tile_harm` 看免疫；同種子跑兩次與重播相同（角魔＋兩件地形規則裝備）。
5. **收尾**：`classify.py --check` 原本多 2 筆 text：TerrainAffix 的訊息改掉數字；`unit_rule_permille_problems` 的訊息是從 `races.py` 照搬，併進既有規則 `RacePassive.permille_problems` 那條（const，HC-6a）。

## 3. 驗收

基準 `2904f2d1d`（`git archive` 的 `src`、`content`）；腳本在暫存區，沒進 repo。

| 檢查 | 結果 |
|---|---|
| 逐招預算 442 招（`BudgetReport` repr＋`validate_skill` 違規） | 檔案逐位相同（`cmp` 0） |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看 timing） | `cells=204 same=204 different=0` |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（後端 config 28、text 0；沒歸類 0） |
| ruff、format、mypy、lint-imports | 0 |
| tsc、vitest（`affixStatus.test.ts`）、build | 0 |
| 合併 main（`b7b7e2d96`，main 只有文件改動）後 `uv run python scripts/check.py` | 0（pytest 18316 passed、8 skipped；vitest 4892；client typecheck、situation coverage 通過；已寫通過戳記） |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（995 passed）；CLI 快照、parity 都沒變，不用重產 |
| 前端 build（合併後） | 0 |
| 78 場（`compare78.py`，同 a 段那組；去掉 `ruleset_hash`、內嵌規則包、`format`），**開關關**（暫存複本把 `harmful_sees_immunity` 設 `false`） | `battles=78 events=26206 different=0`；內嵌規則包只多 `ai.scoring.harmful_sees_immunity`（missing → False） |
| 78 場，**開關開**（預設，就是目前的內容） | `battles=78 events=26206 different=0`；內嵌規則包只多 `ai.scoring.harmful_sees_immunity`（missing → True） |

**開關開時為什麼也沒有差異**：這 78 場的單位都沒有種族（`sim/builds.yaml` 的英雄、隊友與敵人範本都沒填 `race`），`affixes.yaml` 也沒有地形規則詞條，所以沒有任何單位 `burn_immune`，`_harmful` 的結果和改前逐格相同。預期會變的「角魔參與的場次」不在這組裡；行為差異由 `tests/engine/test_ai_immunity_e2.py` 驗證。

## 4. 截圖

實機（開發模式「一鍵開局」，坦克英雄在暫存的內容複本裡改成矮人；腳穿「踏霜靴」三條地形規則、身體穿「炎紋外衣」一條；測試詞條只在暫存複本）：

- `docs/art/shots/e2/e2_terrain_rules_1600x900.png`
- `docs/art/shots/e2/e2_terrain_rules_800x600.png`

兩張都是角色面板（單位卡的「詳細」）上方釘住的裝備卡，三種情況各一行：和種族重複標灰、和另一件裝備重複標灰、部分重疊不標灰只加註。交美術 PM 看（新視覺：部分重疊的註記用和標灰原因相同的金色，但不劃線）。

## 5. 待 PM 決定

1. **「同一條地形規則」的判法**（開發 PM 轉述玩法 PM 2026-11-22 補定，待寫進 8.29）：照鍵（表面、天氣、地形、標籤）判，開關型與數值型同一套。**數值同鍵不同數值**（例：種族水上 +1、靴子水上 +2）照「第一個來源決定」→ 靴子完全重複標灰、仍是 +1，沒有取較強的那條；若要「取最強」需再定。
2. **`damage_taken_permille` 不開放給裝備**（開發 PM 已裁定）。
3. **`passive_of` 的語意**：回傳「第一個該種類的來源」，不分鍵；目前只有 `reveal_radius`、`fall_immune`、`hazard_push_reduction`（只用來判斷有沒有）在用，鍵相關的查詢都改走 `first_source`。
4. **地形規則的定價**：`affix_points` 對 `terrain` 給 0 點（沒有 `category_points`）；E6 定價時要補。
5. **裝備比較預測（前端 `compareItem`）不預測「和種族重複」**：只照舊預測同 id 的非數值詞條（`terrain` 算非數值）；種族重複由伺服器在角色面板標灰。
6. **HUD 的「被動作用中」只看種族**（草案做法）；裝備的地形規則只在裝備卡、角色面板。
7. **AI 只看燃燒免疫**：目前只有「表面施加燃燒」有免疫規則；E3 的「表面傷害免疫」要接在 `_harmful` 的回合開始傷害那一段。
8. **`_harmful` 的標籤限定傷害**（聖光只傷不死族）照舊不看單位標籤，這段沒改。

## 開發 PM 裁定（2026-11-22）

合併為 8a4a62309 推上 main。截圖交給美術 PM 驗收。

1. 改成取較強的那條。8.21.5.3 寫明同 id 重複時「取效果最強的那條」，數值型的地形規則照同一原則：種族「水上 +1」配「水上 +2」的靴子時，靴子生效，結果是 +2；種族那條在角色面板註明被蓋過，仍受裝備移動合計 +2 的上限。E3 也會改同一張表，這項併進 E3 做。結果通知玩法 PM。
2. 接受。E6-a 定價時補上。
3. 接受。前端預測不了的情況，由伺服器在角色面板標灰。
4. 接受，寫進 E3 計畫。
5. 交美術 PM 驗收截圖。
6. 接受。
- 78 場比對在開關打開時仍是 different=0，是因為這組戰鬥沒有帶種族的單位。AI 會看免疫的行為差異，改由 `tests/engine/test_ai_immunity_e2.py` 驗證，接受。
