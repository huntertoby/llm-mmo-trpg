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
| `rules/core.yaml` | 核心戰鬥規則數值（AP、命中、傷害、墜落、連鎖深度、半掩護懲罰……） | Phase 1A、1B、1C |
| `rules/hit_table.yaml` | 命中修正整數門檻表（由 `scripts/gen_hit_table.py` 產生，勿手改） | Phase 1A |
| `terrain.yaml` | 地形（可否行走、致命、阻擋視線、顯示字元；1C 加入牆壁 `wall`） | Phase 1A、1C |
| `weapons.yaml` | 武器 | Phase 1A |
| `statuses.yaml` | 狀態（防禦、倒地、燃燒、隱蔽） | Phase 1A、1B |
| `objects.yaml` | 格子物件與標籤（木橋、油桶、石柱、草叢、木箱、土牆；1C 加入 `half_cover` 標籤、矮牆、倒木、油桶漏油 `spill`） | Phase 1B、1C |
| `surfaces.yaml` | 表面（油、水、火、冰、毒、聖光、黑暗）：持續回合、進入與回合開始效果 | Phase 1B |
| `interactions.yaml` | 元素 × 標籤／表面互動表與元素能力 | Phase 1B |
| `weather.yaml` | 天氣（晴朗、下雨、濃霧、夜晚） | Phase 1B |
| `reactions.yaml` | 反應（格擋、藉機攻擊）與預設反應規則 | Phase 1B |
| `ai_profiles.yaml` | 效用 AI 的行為模式權重（莽夫、弓手、狡猾、守衛；1C 加入掩護權重與 `move_candidates`） | Phase 1B、1C |
| `units/` | 單位範本（一檔一個，檔名 = id；1C 加入盜賊盾衛 `bandit_shieldbearer`） | Phase 1A、1B、1C |
| `maps/` | 地圖（一檔一張，檔名 = id；格式見 `docs/phases/Phase1計畫.md` 5.2，1B 加入 `objects`、`surfaces`、`objective`、`weather`、`encounter`、`events`）；圖例 `#` 慣例對應牆壁；示範地圖 `bridge_chasm`、`oil_depot`、`swamp`、`ruined_fort` | Phase 1A、1B、1C |

## 未來的子資料夾規劃

| 子資料夾 | 內容 | 預計階段 | 計畫章節 |
|---|---|---|---|
| `primitives/` | 效果原語（傷害、控制、位移、地形、召喚……）與參數範圍 | Phase 2 | 第 6 節 |
| `shapes/` | 目標形狀（單體、直線、錐形、範圍……） | Phase 2 | 第 6 節 |
| `skeletons/` | 技能骨架：規定技能結構與預算分配 | Phase 2 | 第 6 節 |
| `maps/`（已建立） | 地圖類型與手工地圖模板 | Phase 1–2 | 第 5.1 節 |
| `marks/` | 印記的觸發條件（由事件日誌統計） | Phase 3–4 | 第 7 節 |
| `resonance/` | 裝備共鳴效果 | Phase 5 | 第 8 節 |
| `affixes/` | 裝備詞條（四類，含技能強化詞條） | Phase 5 | 第 8 節 |
| `loot/` | 掉落表 | Phase 5 | 第 8 節 |
| `budgets/` | 技能與物品的預算表 | Phase 2、5 | 第 6、8 節 |

（條件、代價、觸發等技能積木也屬於 Phase 2 的內容資料，屆時再決定是否各自獨立成子資料夾。）
