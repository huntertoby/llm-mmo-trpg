# Phase 3-54b 報告｜大地補強＋3-54a 小修

> 規格：`docs/phases/Phase3計畫.md` 第 62～64 節的 3-54b；設計：`docs/design/06-技能.md` 6.33（含 #63 修正）。**沒有新增種子技能**（3-54c 才做）；驗證用的技能都寫在測試裡。

## 做了什麼

### 3-54a 小修

| 項目 | 實作 |
|---|---|
| (a) 吹進深淵或岩漿的表面直接消失 | 吹送時致命地形（`is_deadly`：深淵、岩漿、冰窟；有木橋／薄冰架著時不致命）不再擋風：表面一格一格前進，**走進致命地形那一格就消失**，不再放下，也不再繼續走。牆壁、地圖外、`blocks_move` 物件、較高的地形照舊擋風（停在前一格）。事件 `surface_blown` 多了 `lost`（`to_pos` 是消失的那一格）。元素擴散（不是吹送）遇到致命地形仍是「擋住、不擴進去」（結果同樣是致命地形上沒有表面）。表格測試：`tests/engine/test_blow_deadly_54b.py`（3 種致命地形 × 6 種表面 × 距離／致命格位置、只丟失進去的那片、牆照擋、木橋不致命）。 |
| (b) 元素擴散格數做成技能參數 | 傷害效果新參數 `spread`（1 或 2；省略＝`core.wind.spread_distance`，預設 1）。只有 `element: wind` 的技能自己的傷害效果可以填（`SkillDef` 驗證）。預算：傷害效果點數 × `content/skill_budget.yaml` 的 `wind_spread_permille: [1000, 1150]`（擴散 1 格／2 格；初值，未經模擬）。工坊：`show_when: {element: wind}`，只在選風元素時顯示；卡片寫「往風向擴大 N 格」。LLM 提議模型由 `skill_primitives.yaml` 產生，自動有 `spread`。組合器**不抽 2 格**（保持既有種子不變）。測試：`tests/engine/test_wind_spread_54b.py`。 |
| (c) 吹送的工坊說明 | `content/workshop_text.yaml` 的 `原語.blow_surface` 玩家版換成規格句子；開發者語氣原文與卡片句同步加上「推進深淵或岩漿的部分會消失」。 |

### 大地（06 6.33）

| 6.33 | 實作 | 數值（都在 `content/`） |
|---|---|---|
| 只有大地能升降地形 | 互斥規則 `terrain_needs_earth`（`content/skill_exclusions.yaml`）：帶 `raise_terrain`／`lower_terrain` 的技能，「元素」必須有大地。技能的元素 ＝ `skill_elements()`：標籤裡的元素名稱（組合器的主題元素、手寫技能的主題標籤）＋所有層級效果自己寫的元素（物理不算）。`SkillMatch` 新增 `elements_any`。工坊：與驗證器同源（`exclusion.terrain_needs_earth` 列入成對規則，3-48h 機制），草稿裡還沒有大地元素的效果時，升降地形整個原語事前停用並說明「先加入一個大地元素的效果」。組合器：只在主題是大地時抽升降地形（`_theme_allows`，讀同一條規則）。 | — |
| 石膚（狀態：物理傷害 −30%、移動 −1，2 回合） | 狀態 `stoneskin`：`physical_taken_permille: 700`（只乘物理元素骰值傷害，與易傷等相乘）、`move_delta: -1`（回合開始的移動點數 −1，最低 0）、`duration: 2`、增益（可被奪取）、`min_rarity: rare`、`budget_points: 3`。新狀態欄位 `physical_taken_permille`、`move_delta`。已進：預算器（`budget_points`）、工坊（apply_status 的狀態選項）、組合器（狀態池）、LLM 提議（狀態列舉）、卡片（`status_info` 的數值句）、AI（`ally_status_values: stoneskin 3`）、前端狀態圖示。 | `content/statuses.yaml` |
| 震波（直線上的單位倒地，飛行不受影響） | 新原語 `shockwave`：只能搭配 `line` 形狀（`allowed_shapes`）、主動技能、最低稀有；影響格上的對象單位直接倒地（**不擲對抗**，已倒地的略過）；帶 `flying` 標籤的單位不受影響（`effect_fizzled`，原因 `shockwave_flying`，紀錄會寫）。預算 `fixed`、`base_points: 4`（形狀倍率另算）。已進：預算器、驗證器、工坊（原語選項與玩家說明）、組合器（`_shockwave_secondary`：大地主題＋直線＋範圍骨架、稀有以上，`structure.shockwave_permille: 250`，獨立亂數串流）、LLM 提議、卡片（「震波：直線上的單位直接倒地（不擲對抗；會飛的單位不受影響）」）、AI 估值、預覽、關鍵字「倒地」、前端技能部件。 | `content/skill_primitives.yaml`、`content/skill_composer.yaml` |
| 升降地形影響 4～6 格最低稀有、7 格以上最低史詩 | `rarity_requirements` 新增 `terrain_area`：用形狀的 `cell_count`（`content/skill_shapes.yaml`）算影響格數，查 `content/skill_budget.yaml` 的 `terrain_area_rarity: [{min_cells: 4, rarity: rare}, {min_cells: 7, rarity: epic}]`。驗證器（`rarity.terrain_area`）與工坊的「最低稀有度」共用。沒有固定格數的形狀（連鎖）略過（形狀本身有稀有度要求）。預算照 6.5 形狀倍率（沿用既有算法，沒有另外加係數）。 | `content/skill_budget.yaml` |

### 影響盤點

- `LOG_FORMAT` `/76` → **`/77`**。**3-55 也可能遞增，合併時請 PM 處理。**
- 組合器：升降地形只在大地主題抽、石膚進了狀態池、震波有獨立串流 → **既有種子的組合器技能會改變**（`skill_icons.json`、`client/src/battle/fixtures/glossary.json` 已重新匯出；CLI 快照與 run auto 種子見測試結果）。
- OpenAPI：重新匯出，沒有差異。
- `content/workshop_text.yaml`：154 條（吹送改寫、新增震波與擴散格數兩條「實作者初稿，待玩法 PM 改寫」）。

## 測試

- 新增：`tests/engine/test_blow_deadly_54b.py`、`tests/engine/test_wind_spread_54b.py`、`tests/engine/test_earth_54b.py`（石膚 × 9 種元素、移動點數、震波 × 對象／飛行／已倒地／驗證、升降地形 × 元素來源、形狀格數 × 稀有度、預算、工坊事前停用、含大地測試技能的整場戰鬥重播一致）。
- 修改既有測試的期待：`LOG_FORMAT` 斷言 `/77`、骨架／互斥規則清單、狀態清單（增益、預算點數、AI 的 `ally_status_values`）、工坊說明條數、`test_coverage` 允許清單（震波、石膚種子技能在 3-54c 才寫）。

## 待 PM 決定

1. **「大地元素」的判定**：6.33 只寫「隆起、下陷只能搭配大地元素」。現在是「技能標籤有 `earth`，或任何效果自己寫的元素是 `earth`」。這表示工坊**不能做出純地形（沒有任何大地元素效果）的升降地形技能**——工坊不讓玩家選標籤，必須先加一個大地元素的效果（例如大地傷害）。若要允許純地形，需要決定工坊怎麼表達技能的元素（例如新增「技能主題元素」欄位）。
2. **石膚與震波沒有限制大地**：規格只要求升降地形限大地（驗證器）；石膚（狀態）與震波（原語）其他元素也能用。若要限大地請說一聲（同一條互斥規則多加幾個原語即可）。
3. **震波會被命中判定影響**：對敵方的效果與其他範圍效果一樣先擲命中，未命中的單位不倒地。6.33 寫「直線上的單位倒地」，若要「必定倒地」需要決定。
4. **石膚數值**：預算 3 點、最低稀有、增益（可被奪取、驅散）；震波 4 點；擴散 2 格 ×1.15。都是初值，未經模擬，平衡階段（B25）再調。
5. **擴散 2 格組合器不抽**（保持種子穩定）；若要讓隨機技能也出現 2 格，需要另開獨立串流。
6. **吹送進致命地形與元素擴散**：吹送「走進去就消失」；元素擴散「不擴進致命地形」（結果相同：致命地形上沒有表面）。
7. 升降地形 4 格門檻與原語本身最低稀有重複（原語本來就是稀有）；實際生效的是 7 格以上要史詩。

## 驗收結果

- ruff check、ruff format --check、mypy（723 檔）、lint-imports（7 kept）通過。
- pytest：engine 3335 通過；content、skillgen、llm、narrative、api、roguelite、sim 合計 4246 通過（1 skipped）；`-m "slow or not slow" tests/cli --timeout=3000` 148 通過（**沒有更新任何 CLI 快照**，run auto 種子測試也沒有差異）。
- vitest 104 檔 994 通過；`pnpm build` 成功。
- 含測試用大地技能（`skill_t_quake`＝大地傷害＋震波、`skill_t_skin`＝石膚）的整場戰鬥重播一致（`tests/engine/test_earth_54b.py`）。
