# Phase HC-8 報告：寫死清單最後兩組（畫面 2 句、工坊工具 10 項設定）

依據：`docs/phases/PhaseHC-8計畫.md`。基準：main `f5693df81`。分支 `worktree-agent-a94a99c734391b5ec`，沒 push。
沒改任何數值、沒動 `docs/design/`、`content/`、引擎、`content/tuning_fields.yaml`、`api/tuning/objects.py`、`_damage_rolls`。
`config/` 只新增 `config/tuning.toml`，既有的設定檔沒動。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 屬性點的 2 句說明改從資料組字 | `c557e7bed` | `GameRulesOut` 多 4 欄（有預設值）；`attrPerLevelText()`、`allocateExampleText()`；vitest、pytest；開發頁 `client/dev/hc8-gallery.html`；截圖 2 張 |
| 2 工坊工具的 10 項設定搬到 `config/tuning.toml` | `740f78b29` | `api/tuning/tool_config.py`（pydantic、local 覆寫）；三個模組的常數改讀它；`上手-數值工坊.md` 加一節 |
| 3 收尾 | `54e44b685` | 刪 `ts-ui-text`、`py-api-tuning-tool-settings`；重產 `寫死數值-清單.md` |
| 報告 | `8f7c4359b` | |
| 1′ 屬性改照原值顯示（玩法 PM 定案 A） | 本 commit | 刪 `attributeShown`（÷ `quantity_scale`）與用不到的 `GameRulesOut.quantity_scale`；vitest 鎖新字；重拍截圖 1、2；改報告 |

## 2. 第 1 項：屬性點的 2 句

### 2.1 資料從哪來

- `GET /api/glossary` 的 `rules`（`GameRulesOut`）多 3 欄，伺服器一律由內容庫填（`api/glossary.py::_game_rules`）：
  - `attribute_points_per_level` ← `roguelite.yaml`（20）；
  - `base_attribute` ← `roguelite.yaml`（100）；
  - `start_free_points` ← `roguelite.yaml`（40）。
- 照規格給預設值，預設＝目前的內容（`tests/api/test_game_rules_hc8.py` 對照）。重產了 `client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/battle/fixtures/glossary.json`。
- 第一版另有 `quantity_scale` 一欄給前端 ÷10 用；定案 A 之後沒有地方用，一起拿掉（API 欄位是這段新加的，沒有別人用）。

### 2.2 顯示量尺（玩法 PM 定案 A：照 ×10 後的原值顯示）

- 第一版照規格的「×10 量尺換算」寫了 `attributeShown`（÷ `quantity_scale`），讓字和改前逐字相同。玩法 PM 依 05 5.4.1（例子寫「開局屬性 100、每級配點 20」）定案：屬性一律照原值顯示，拿掉 ÷10。這一版已刪掉 `attributeShown`，兩句直接用原值組字，和配點教學上一行（「開局的 40 點……共 60 點」）、升級畫面（「屬性點 +20」）、主角面板（「基礎 100」）同一個量尺。
- 配點範例的規則照現行組字，不改規則：
  - 開局點數兩招各半，奇數時多的給第 1 招（同 `roguelite/start.py::recommended_allocation`）；
  - 升級點數給比較低的，一樣高給第 1 招（同 `recommended_level_up`）。

### 2.3 改前、改後（目前的值，照資料實際算出來）

| 位置 | 改前（寫死） | 改後（組字，目前的值） |
|---|---|---|
| 成長面板屬性點分頁的標籤 | `升級時每級 +2` | `升級時每級 +20` |
| 配點教學的範例 | `例：兩招看智力和力量 → 開局 4 點各給 2 點（智力 12、力量 12）；升級的 2 點給比較低的那個，一樣高就給第 1 招的 → 智力 14、力量 12。` | `例：兩招看智力和力量 → 開局 40 點各給 20 點（智力 120、力量 120）；升級的 20 點給比較低的那個，一樣高就給第 1 招的 → 智力 140、力量 120。` |

算法：開局 40 → 智力 40 − 40 // 2 ＝ 20、力量 20；起始值 100 ＋ 20 ＝ 120、120；兩個一樣高，升級的 20 給第 1 招（智力）→ 140、120。和 PM 給的字相同。

改值的 vitest（`client/src/world/hc8AttrText.test.ts`，原值）：
- 每級 30 點、開局 60 點 → `升級時每級 +30`、`例：兩招看智力和力量 → 開局 60 點各給 30 點（智力 130、力量 130）；升級的 30 點給比較低的那個，一樣高就給第 1 招的 → 智力 160、力量 130。`
- 開局 45 點（奇數）、每級 20 → `開局 45 點給智力 23 點、力量 22 點（智力 123、力量 122）；……→ 智力 123、力量 142。`
- `pnl2Growth.test.ts` 的期望字同步改成「升級時每級 +20」；開發頁 `panelGallery.tsx` 的標籤樣張也改成 +20。

### 2.4 截圖（`docs/art/shots/hc-8/`，jpg 80，1600 寬）

| 檔案 | 內容 |
|---|---|
| `1-allocate-example-1600.jpg`（35 KB） | 開發頁 `hc8-gallery.html?mute=1`：正式的 `AllocateLessonDialog`，範例句在「推薦配法」下面（定案 A 後重拍：40、20、120、140） |
| `2-growth-attr-per-level-1600.jpg`（43 KB） | 開發頁 `panel-gallery.html?tab=attr&mute=1#growth`：正式的 `WorldGrowth` 屬性點分頁，右側標籤「升級時每級 +20」（定案 A 後重拍） |

做法：vite 開發頁（埠 5283）＋無頭 Chrome（`--mute-audio`，除錯埠 9817）用 CDP 拍 jpeg 80。拍完兩個程序都用 PID 結束。

## 3. 第 2 項：工坊工具的 10 項設定

### 3.1 讀法

- `src/trpg/api/tuning/tool_config.py`：`TuningToolSettings`（pydantic、`extra="forbid"`、每項 `ge=1`、三個預設種子不能大於 `ratio.max_seeds`），模組載入時讀一次成 `TUNING_TOOL`。
- 讀的順序：`config/tuning.toml`（環境變數 `TRPG_TUNING_CONFIG` 可換檔，同 `TRPG_LLM_CONFIG`）→ `config/tuning.local.toml` 有寫的鍵蓋過（`*.local.*` 已在 `.gitignore`，同 `bot.local.toml`）。
- 打錯表格或鍵名、值不合法、檔案壞掉 → `TuningToolConfigError`，伺服器啟動時就報錯。
- 原本的常數名都留著（`schemas.SMALL_SAMPLE` 等），改成讀 `TUNING_TOOL`，所以 `service`、`ratios`、`sim_jobs`、`routes` 不用改。
- 每項的中文說明寫在 `config/tuning.toml` 的註解，也寫進 `docs/dev/上手-數值工坊.md`「工坊工具的設定」一節（含表格）。

### 3.2 對照表（值一律不變）

| 原位置 | 新的鍵 | 值 |
|---|---|---|
| `api/tuning/schemas.py` `SIM_DEFAULT_SEEDS` | `[sim] default_seeds` | 3 |
| `api/tuning/schemas.py` `MAP_DEFAULT_SEEDS` | `[sim] map_default_seeds` | 24 |
| `api/tuning/schemas.py` `MAX_SIM_MAPS` | `[sim] max_maps` | 3 |
| `api/tuning/schemas.py` `MAX_SIM_BATTLES` | `[sim] max_battles` | 160 |
| `api/tuning/schemas.py` `SMALL_SAMPLE` | `[sim] small_sample` | 30 |
| `api/tuning/schemas.py` `RATIO_DEFAULT_SEEDS` | `[ratio] default_seeds` | 50 |
| `api/tuning/schemas.py` `MAX_RATIO_SEEDS` | `[ratio] max_seeds` | 250 |
| `api/tuning/schemas.py` `RATIO_MAX_WORK` | `[ratio] max_work` | 40000 |
| `api/tuning/drafts.py` `DRAFT_NAME_MAX` | `[drafts] name_max` | 40 |
| `api/tuning/skills.py` `MAX_GROUP` | `[skills] max_group` | 100 |

### 3.3 設定不變的驗證

- 固定請求比對（腳本在 scratchpad，改前在動程式前跑）：工坊 `status()` 的 `max_group`／`draft_name_max`、`sim_options()` 全部、地圖選 4 張的錯誤訊息、`TuningSimRequest`／`TuningRatioPlanIn`／`TuningDraftIn` 的 JSON schema、`client/openapi.json` 的 `Tuning*` 全部 schema、17 個模組常數（含 `DRAFT_NAME_PATTERN`、`ratios`／`sim_jobs`／`service` 的別名）。結果 **different=0**（這項沒有新欄位）。
- 重跑 `export_openapi.py` 後 `client/openapi.json` 沒有差異。
- `tests/api/tuning/test_tool_config_hc8.py`：檔案值與程式預設＝改前的 10 個值、常數接線、local 覆寫只蓋有寫的鍵、環境變數換檔、5 種壞檔被擋。

## 4. 第 3 項：收尾

- 刪掉搬完變 0 筆的 `ts-ui-text`、`py-api-tuning-tool-settings`，順手改兩處提到它們的區塊註解。
- 新增 3 條規則（都是這段新寫的數字或字）：
  - `py-api-tuning-tool-config-defaults`（config／done）：`tool_config.py` 的 10 個 schema 預設，比照 `py-llm-config-config-number`。
  - `py-api-game-rules-hc8-defaults`（config／done）：`GameRulesOut` 新 3 欄的預設。
  - `ts-hc8-ordinal-text`（const／done）：範例句的「一樣高就給第 1 招的」是序號（平手規則），同 HC-6b 的序號前例。
- `classify.py --check` 沒歸類 0；`--unused` 沒有輸出；重產 `docs/phases/寫死數值-清單.md`（text 前端 2 → 0；config 後端 28 → 31，見待 PM 決定 2）。

## 5. 檢查

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0 |
| `lint-imports` | 0 |
| `trpg content check` | 0 |
| `classify.py --check` | 0（`--unused` 無輸出） |
| `pnpm typecheck`（tsc） | 0 |
| `pnpm test`（vitest 全部） | 0 |
| 相關 pytest（`tests/api/tuning`、openapi 快照、client 夾具、寫死掃描、`test_game_rules_hc6c/hc8`） | 0 |
| 前端 build、`scripts/check.py`、slow（parity＋cli） | 等開發 PM 回覆後跑，結果補在第 7 節 |

定案 A 的修改（1′）後重跑：ruff、format、mypy、lint-imports、content check、classify --check（--unused 無輸出）、tsc、`vitest run src/world`（68 檔 837 項）、相關 pytest（hc8、openapi 快照、client 夾具、寫死掃描）全部 0。

## 6. 待 PM 決定

1. **已定 A：屬性照 ×10 後的原值顯示**（玩法 PM，依 05 5.4.1「開局屬性 100、每級配點 20」）。原本的問題：前端沒有屬性顯示換算、其他畫面都顯示原值，第一版為了字不變另寫了 `attributeShown`（÷10），同一個配點視窗上下兩行量尺不一致。已改：刪掉 `attributeShown` 和 `GameRulesOut.quantity_scale`，兩句用原值組字。
   - 成長面板：改前「升級時每級 +2」→ 改後「升級時每級 +20」。
   - 配點範例：改前「例：兩招看智力和力量 → 開局 4 點各給 2 點（智力 12、力量 12）；升級的 2 點給比較低的那個，一樣高就給第 1 招的 → 智力 14、力量 12。」→ 改後「例：兩招看智力和力量 → 開局 40 點各給 20 點（智力 120、力量 120）；升級的 20 點給比較低的那個，一樣高就給第 1 招的 → 智力 140、力量 120。」
2. **新欄位的預設值**：規格要求新欄位有預設值，所以 `GameRulesOut` 的 3 欄給了等於內容的預設值（HC-6c、HC-7 b 的前例是必填、不給預設）。這 3 個數字和 `tool_config.py` 的 10 個 schema 預設各新增一條 config／done 規則，所以清單的後端 config 從 28 變 31。若要照 HC-7 b 改成必填，刪預設、刪那條規則即可（夾具已重產，前端型別本來就是必填）。
3. **`config/tuning.toml` 的格式**：分成 `[sim]`、`[ratio]`、`[drafts]`、`[skills]` 四個表格；`MAX_RATIO_SEEDS` 放在 `[ratio] max_seeds`，但它其實也是頭目戰、地圖戰種子欄的上限（原本就這樣），註解有寫。另加了環境變數 `TRPG_TUNING_CONFIG`（比照 `TRPG_LLM_CONFIG`），規格沒要求。
4. **設定只在啟動時讀一次**：常數被 pydantic 的 `Field(le=…)`、`pattern` 在模組載入時用掉，所以改設定要重開伺服器（toml 註解與上手文件都有寫）。`[drafts] name_max` 改小時，比新上限長的舊草稿會讀不到（改回來就好）。
5. **開發頁 `panelGallery.tsx` 的元件樣張**原本寫「升級時每級 +2」，定案 A 後順手改成 +20（只是排版樣張）。
6. **已定：葛蘭的配點教學第一句不帶數字**（玩法 PM 定字；每級幾點在工坊改了也不用跟著改）。`content/world/newcomer.yaml` 的 `allocate_lesson` 第一句：
   - 改前：「升級了？身上多了兩點力氣。來，我示範怎麼分。」
   - 改後：「升級了？身上又多了些力氣。來，我示範怎麼分。」
   - 一起更新：`tests/world/test_newcomer.py`（鎖這句的斷言）、開發頁 `client/src/dev/hc8Gallery.tsx` 的教學內容。沒改：美術樣張 `docs/art/sample/mentor-attr.html` 與舊報告 `PhaseOB-3報告.md`（歷史文件）。截圖 1 拍的是改字前的開發頁，台詞那行還是舊字（範例句與本段無關，沒重拍）。

## 7. 全量檢查

開發 PM 回覆「可以跑」後，先 `git merge --no-edit main`（main `81f9cbb49`，含 KD-1），合併 commit `a2494e983`。

- 衝突只有產生檔 `docs/phases/寫死數值-清單.md`：合併後重產（`classify.py --md`）解決。
- `classes.yaml` 自動合併，兩邊的規則都在：`classify.py --check` 沒歸類 0，`--unused` 沒有輸出。
- 重產 `openapi.json`、前端型別、client 夾具，和合併結果相同，沒有差異。

| 檢查 | 結束碼 |
|---|---|
| `uv run python scripts/check.py` | 0（全部通過，寫下通過戳記） |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（995 passed） |
| `pnpm -C client build` | 0（只有 chunk 大小的既有警告） |

都一次通過，沒有要修的。
