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
| 報告 | 本 commit | |

## 2. 第 1 項：屬性點的 2 句

### 2.1 資料從哪來

- `GET /api/glossary` 的 `rules`（`GameRulesOut`）多 4 欄，伺服器一律由內容庫填（`api/glossary.py::_game_rules`）：
  - `quantity_scale` ← `rules/core.yaml` 的 `quantity_scale`（10）；
  - `attribute_points_per_level` ← `roguelite.yaml`（20）；
  - `base_attribute` ← `roguelite.yaml`（100）；
  - `start_free_points` ← `roguelite.yaml`（40）。
- 照規格給預設值，預設＝目前的內容（`tests/api/test_game_rules_hc8.py` 對照）。重產了 `client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/battle/fixtures/glossary.json`。

### 2.2 顯示換算

- 規格要「沿用前端現有的屬性顯示換算」。查過前端**沒有**屬性的顯示換算：其他畫面（未分配屬性點的籌碼、主角面板的「基礎 100」、配點教學「開局的 40 點……共 60 點」、升級畫面「屬性點 +20」）都直接顯示原值。所以新寫了**一份** `attributeShown(raw, scale)`（`client/src/world/growthPanel.ts`，＝原值 ÷ `quantity_scale`），兩句都用它。見待 PM 決定 1。
- 配點範例的規則照現行組字，不改規則：
  - 開局點數兩招各半，奇數時多的給第 1 招（同 `roguelite/start.py::recommended_allocation`）；
  - 升級點數給比較低的，一樣高給第 1 招（同 `recommended_level_up`）。
  - 算的時候用原值（量類），顯示時才 ÷ scale。

### 2.3 改前、改後（目前的值，逐字相同）

| 位置 | 改前（寫死） | 改後（組字，目前的值） |
|---|---|---|
| 成長面板屬性點分頁的標籤 | `升級時每級 +2` | `升級時每級 +2` |
| 配點教學的範例 | `例：兩招看智力和力量 → 開局 4 點各給 2 點（智力 12、力量 12）；升級的 2 點給比較低的那個，一樣高就給第 1 招的 → 智力 14、力量 12。` | 同左，逐字相同 |

改值的 vitest（`client/src/world/hc8AttrText.test.ts`）：
- 每級 3 點、開局 6 點 → `升級時每級 +3`、`例：兩招看智力和力量 → 開局 6 點各給 3 點（智力 13、力量 13）；升級的 3 點給比較低的那個，一樣高就給第 1 招的 → 智力 16、力量 13。`
- 開局 5 點（奇數）→ `開局 5 點給智力 3 點、力量 2 點（智力 13、力量 12）；……→ 智力 13、力量 14。`

### 2.4 截圖（`docs/art/shots/hc-8/`，jpg 80，1600 寬）

| 檔案 | 內容 |
|---|---|
| `1-allocate-example-1600.jpg`（35 KB） | 開發頁 `hc8-gallery.html?mute=1`：正式的 `AllocateLessonDialog`，範例句在「推薦配法」下面 |
| `2-growth-attr-per-level-1600.jpg`（43 KB） | 開發頁 `panel-gallery.html?tab=attr&mute=1#growth`：正式的 `WorldGrowth` 屬性點分頁，右側標籤「升級時每級 +2」 |

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
  - `py-api-game-rules-hc8-defaults`（config／done）：`GameRulesOut` 新 4 欄的預設。
  - `ts-hc8-ordinal-text`（const／done）：範例句的「一樣高就給第 1 招的」是序號（平手規則），同 HC-6b 的序號前例。
- `classify.py --check` 沒歸類 0；`--unused` 沒有輸出；重產 `docs/phases/寫死數值-清單.md`（text 前端 2 → 0；config 後端 28 → 32，見待 PM 決定 2）。

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

## 6. 待 PM 決定

1. **前端沒有屬性的顯示換算，其他畫面顯示原值**（第 1 項）：規格要「沿用前端現有的屬性顯示換算」，但查過沒有。我新寫了一份 `attributeShown`（÷ `quantity_scale`），只用在這兩句。結果同一個配點教學視窗裡，上一行是伺服器的「開局的 40 點……加上這次升級的 20 點，共 60 點。推薦配法：智力 +20」，下一行範例是「開局 4 點……智力 12」（截圖 1）；升級畫面（`newcomer.yaml` 的 `level_up_zh`）也寫「屬性點 +20」、主角面板寫「基礎 100」。這是改前就有的不一致，這段照規格保持兩句字不變、沒動其他畫面。要不要全面統一量尺，請 PM 決定。
2. **新欄位的預設值**：規格要求新欄位有預設值，所以 `GameRulesOut` 的 4 欄給了等於內容的預設值（HC-6c、HC-7 b 的前例是必填、不給預設）。這 4 個數字和 `tool_config.py` 的 10 個 schema 預設各新增一條 config／done 規則，所以清單的後端 config 從 28 變 32。若要照 HC-7 b 改成必填，刪預設、刪那條規則即可（夾具已重產，前端型別本來就是必填）。
3. **`config/tuning.toml` 的格式**：分成 `[sim]`、`[ratio]`、`[drafts]`、`[skills]` 四個表格；`MAX_RATIO_SEEDS` 放在 `[ratio] max_seeds`，但它其實也是頭目戰、地圖戰種子欄的上限（原本就這樣），註解有寫。另加了環境變數 `TRPG_TUNING_CONFIG`（比照 `TRPG_LLM_CONFIG`），規格沒要求。
4. **設定只在啟動時讀一次**：常數被 pydantic 的 `Field(le=…)`、`pattern` 在模組載入時用掉，所以改設定要重開伺服器（toml 註解與上手文件都有寫）。`[drafts] name_max` 改小時，比新上限長的舊草稿會讀不到（改回來就好）。
5. **開發頁 `panelGallery.tsx` 的元件樣張**還寫著「升級時每級 +2」（只是排版樣張，不是正式元件，被 const 規則涵蓋），沒改。
6. `newcomer.yaml` 的「身上多了兩點力氣」（中文數字，掃描不會抓）也是寫死的點數，和第 1 點同一件事，沒動（`content/` 的字不在範圍內）。

## 7. 全量檢查

（待開發 PM 回覆「準備跑 check.py」後補上）
