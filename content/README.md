# content/：內容資料

依 `docs/專案計畫.md` 第 0 節「內容即資料」：效果原語、目標形狀、格子物件、詞條、掉落表、技能模板等全部以 YAML／JSON 定義在這個資料夾，**新增內容不需要修改引擎程式**。

- 每個資料檔都有對應的 pydantic schema（`src/trpg/content/schemas.py`），一律 `extra="forbid"`、`frozen=True`，拼錯欄位就會報錯。
- 讀取一律經過 `trpg.content.loader.load_content_file`（YAML 用 `yaml.safe_load`）；錯誤會轉成 `ContentError`，訊息含檔案路徑。
- 已知的資料檔登記在 `src/trpg/content/registry.py`；`uv run trpg content check` 會載入並驗證全部。
- 檔案使用 UTF-8、LF 行尾；識別字與欄位名稱用英文，顯示文字（`*_zh`）用繁體中文。
- 可用環境變數 `TRPG_CONTENT_DIR` 指定其他內容資料夾（例如測試或模組）。

## 目前的檔案

| 檔案 | 內容 | 階段 |
|---|---|---|
| `elements.yaml` | 9 種元素的中文名稱、說明與抗性分組（每個元素恰好一筆） | Phase 0、1A |

## 未來的子資料夾規劃

| 子資料夾 | 內容 | 預計階段 | 計畫章節 |
|---|---|---|---|
| `primitives/` | 效果原語（傷害、控制、位移、地形、召喚……）與參數範圍 | Phase 2 | 第 6 節 |
| `shapes/` | 目標形狀（單體、直線、錐形、範圍……） | Phase 2 | 第 6 節 |
| `skeletons/` | 技能骨架：規定技能結構與預算分配 | Phase 2 | 第 6 節 |
| `objects/` | 格子物件與標籤（木橋、油桶、石柱、水窪……） | Phase 1 | 第 5.1 節 |
| `interactions/` | 元素 × 標籤／表面互動表 | Phase 1 | 第 5.1 節 |
| `maps/` | 地圖類型與手工地圖模板 | Phase 1–2 | 第 5.1 節 |
| `marks/` | 印記的觸發條件（由事件日誌統計） | Phase 3–4 | 第 7 節 |
| `resonance/` | 裝備共鳴效果 | Phase 5 | 第 8 節 |
| `affixes/` | 裝備詞條（四類，含技能強化詞條） | Phase 5 | 第 8 節 |
| `loot/` | 掉落表 | Phase 5 | 第 8 節 |
| `budgets/` | 技能與物品的預算表 | Phase 2、5 | 第 6、8 節 |

（條件、代價、觸發等技能積木也屬於 Phase 2 的內容資料，屆時再決定是否各自獨立成子資料夾。）
