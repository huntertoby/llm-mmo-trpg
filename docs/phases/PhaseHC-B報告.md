# Phase HC-B 報告：技能預算的計價全部開進工坊

依據：`docs/phases/PhaseHC-B計畫.md`；參考做法 `PhaseSK-3b計畫.md` 第 10 項（鉤、擴散、吸收搬到 `skill_budget.yaml`）。
基準：main `4d53775e5`。分支 `worktree-agent-a4f8947fb543a7122`，沒 push。
數字一律照現值搬，沒試數值、沒跑平衡量測或模擬。沒動 `docs/design/`、`config/`、`llm.toml`。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 1 原語點數搬家 | `25d5e8d39` | 32 個 `base_points` → `skill_budget.yaml` 的 `primitive_points`；讀的地方改讀預算表；載入檢查；工坊白名單 32 欄 |
| 2 其他看不到的計價 | `4a0653b6c` | 狀態、表面點數與形狀倍率搬到預算表；預算表其餘計價全開；核心規則、條件、協同、被動 n 次係數開進工坊；路徑支援數字鍵與純數字清單 |
| 3 工坊預算表分組 | `664d3f426` | 白名單 `group_zh`；前端分組畫成可收合區塊；截圖 |
| 報告 | 本 commit | |

每個 commit 前跑過 ruff、format、mypy、lint-imports、`classify.py --check`、相關測試目錄；第 1、2 項另跑逐招預算比對，第 2 項跑 78 場戰鬥比對。

## 2. 計價搬家表

「現在在哪」都是 `content/skill_budget.yaml`（＝工坊「技能預算表」）除非另註明。

| 數值 | 原本在哪 | 現在在哪 | 工坊 |
|---|---|---|---|
| 原語基礎點數（32 個：`fixed`／`per_distance`／`per_amount`／`obstacle`／`inscribe` 的原語） | `skill_primitives.yaml` 的 `base_points`（禁止檔） | `primitive_points.<原語 id>` | 開（組「原語點數」） |
| 鉤、疾病擴散、吸收表面、預支的點數 | SK-3b／AP-2 已在預算表 | 不動（`hook_points` 等，**沒有併進 `primitive_points`**，見待決 1） | 已開，歸「原語點數」組 |
| 狀態點數（86 個） | `statuses.yaml` 的 `budget_points` | `status_points.<狀態 id>`；沒列＝技能不能施加 | 開（組「狀態」） |
| 表面點數（8 個） | `surfaces.yaml` 的 `budget_points` | `surface_points.<表面 id>` | 開（組「表面」） |
| 形狀倍率基礎值、每單位加成（13 種形狀） | `skill_shapes.yaml` 的 `budget.base_permille`／`per_unit_permille`（禁止檔） | `shape_budget.<形狀 id>.base_permille`／`per_unit_permille` | 開 9 種沒查表的形狀（組「形狀」） |
| 形狀倍率查表（錐形、十字、環形、連鎖的 `by_value_permille`、連鎖的 `non_power_by_value_permille`） | `skill_shapes.yaml` | **沒搬**：鍵是參數值，查表與 `param`、`power_primitives` 綁在一起；這四種的 `base_permille` 搬了但只在參數沒填時用，所以也不開 | 不開（待決 3） |
| 射程係數 `range_baseline`、`range_step_permille` | 預算表（未開） | 不動 | 開（組「形狀」） |
| 合格區間、AP 1/2/3、反應、姿態、形態、被動多次、陷阱、傳說整場、敵我不分、條件倍率 4 級 | 預算表（只開 `condition_permille.mild`） | 不動 | 開（組「係數」） |
| 召喚每輪價值、圖騰、`summon_trait_*`、自爆、推倒、HP 權重（20 個） | 預算表（未開） | 不動 | 開（組「召喚」） |
| 代價折抵 `allowance.*`（21 個） | 預算表（未開） | 不動 | 開（組「代價折抵」） |
| 重擲、回復、驅散、揭露、復活、定時炸彈、擊殺、給技能、無聲、撞擊骰、擲物、衝撞、消耗、引爆、獻祭、障礙／刻印／護盾持續、風擴散、吸血、穿透 | 預算表（部分已開） | 不動 | 開（組「特殊效果的算法」） |
| 持續區域 `zone_*`、複合 `composite_*`、變奏、賭博、高變異、超載 | 預算表（未開） | 不動 | 開（各自一組） |
| 修正技能 `modifier.*`（係數、命中率、使用次數、`points_milli` 17 項） | 預算表（只開 `silent_strike`） | 不動 | 開（組「修正技能」） |
| 預支、改寫規則的最短冷卻 | 預算表（只開鉤） | 不動 | 開（組「冷卻規則」） |
| 閃現蓄力、轉型 | 預算表（已開） | 不動 | 已開（組「閃現」） |
| 階級預算 `tier_budget.1～5`、武器基準傷害 `budget_reference_weapon_damage` | `rules/core.yaml`（未開） | 不動 | 開（「核心戰鬥規則」表） |
| 召喚物小特性點數 `summon_traits.*.budget_points` | `rules/core.yaml`（未開） | 不動 | 開（「核心戰鬥規則」表） |
| 條件的個別倍率覆寫 `budget_permille`（背刺 700、自身沒有狀態 1000） | `skill_conditions.yaml`（沒有 target） | 不動 | 開（新表「技能條件的預算倍率」，只展開已寫的） |
| 協同係數（3 條） | `skill_synergies.yaml`（沒有 target） | 不動 | 開（新表「技能協同係數」） |
| 被動「每命中 n 次」的係數 `budget_by_n_permille` | `skill_triggers.yaml`（SK-5 因鍵是數字沒開） | 不動 | 開（n＝2、3） |
| `modifier_changes.yaml` | 禁止檔 | **沒搬**：檔內沒有數值，只有每種改變對到 `modifier.points_milli` 的哪個鍵（值都在預算表，已開） | — |
| 預算表裡不是計價的：`rarity.*.max_effects`、`max_rule_rewrite`、`min_character_tier.*`、`terrain_area_rarity`、`retier_growth.*`、`allowance.self_status.fixed_duration.stun`、`known_budget_exceptions`、`cost_resource` | 預算表 | 不動 | **不開**：結構上限、階級門檻、稀有度標記、升階規則、暈眩代價固定 2 回合、例外清單（另有機制）、非數值（待決 4） |

程式面：
- `BudgetRules` 多 `primitive_points`、`status_points`、`surface_points`、`shape_budget`（`ShapePrice`），方法 `status_point`、`surface_point`、`shape_permille`；`PrimitiveDef.base_points`、`StatusDef.budget_points`、`SurfaceDef.budget_points`、`ShapeBudget.base_permille／per_unit_permille` 拿掉，讀的地方（`skillgen/budget.py`、`composer_parts`、`options`、`option_params`、`self_penalty`、`proposal/params`、`sim/skill_fuzz`）都改讀預算表。不留兩份。
- 載入檢查（`library/tables.py`）：`primitive_points_problems`（用固定點數的原語都要有、不能有未知或用不到的）、`price_table_problems`（未知狀態、表面；只給敵人、只由機制施加的狀態不能列，原本 `StatusDef` 的檢查）、`shape_budget_problems`（每種形狀一項、有每單位加成要有 `param`）。
- 工坊路徑（`tuning_fields.py`、`yaml_patch.py`）：對照表的鍵可以是數字（`ap_coefficient_permille.2`，YAML 讀成整數鍵；清單索引照舊是 `[2]`）；標籤裡的 `{n}` 換成清單第幾項（例「限時障礙：持續 3 回合」）。
- 新的表種類 `skill_conditions`、`skill_synergies`（後端 `TABLE_KINDS`、前端載入清單）。協同規則沒名字，標籤用機制標籤的中文（「協同「範圍＋控制」」）。
- `scripts/x10/fields.yaml` 補 `primitive_points.*`、`status_points.*`、`surface_points.*`、`shape_budget.*.*`，拿掉原本三個檔的舊欄位；`classify.py --check` 0。
- 白名單：預算表 291 欄（原本 16），全部有 `group_zh`；整份 11 類對象、688 欄。

## 3. 值不變的證明

### 3.1 逐招預算
- 腳本：搬家前（基準）把內建 434 招的 `skill_budget` 結果存成 JSON（總點數、raw、可用預算、比例、每個效果的基礎點數／形狀倍率／點數／說明、複合段、變奏），每一步後重算比對。
- 結果：第 1 項後、第 2 項狀態表面後、形狀後、第 2 項完成後，四次都是 **`skills=434 same=434 different=0`**（連說明文字都一樣）。

### 3.2 戰鬥不變比對
- 基準：`git archive 4d53775e5 src content`，worker 斷言載入的 `trpg` 來自基準那份。同 HC-4a 的 78 場（15 張正式地圖 × 種子 1、7；`open_plain` 種子 3 × 8 個 build；4 張頭目圖 × 種子 3～12）。
- 比對 `--log-json` 整份（排除 `ruleset_hash` 與內嵌規則包）＋文字輸出。
- 結果：**`battles=78 events=26446 different=0`**（事件數同 HC-4a）。
- 內嵌規則包的差異只有拿掉的欄位：`primitives[].base_points`、`shapes[].budget.base_permille／per_unit_permille`、`statuses[].budget_points`、`surfaces[].budget_points`（所以 `ruleset_hash` 會變）。

### 3.3 slow parity
`tests/skillgen/test_refactor_parity.py -m slow` 照舊通過（見第 5 節），夾具沒重產。

## 4. 工坊

- 測試 `tests/api/tuning/test_budget_table_hcb.py`：
  - 改 `primitive_points.raise_terrain` 的草稿（×3）：草稿內容庫裡所有隆起地形的招比例變高、可用預算不變、其他招不變；驗證列出被推出區間的隆起地形招。
  - 每個原語點數都開、帶原語中文名；預算表每個整數不是開了就是在「結構」清單；數字鍵、純數字清單各一列且值對；數字鍵的寫回只改那一行；條件、協同表開了；預算表每欄有分組、六組都在、同組相鄰。
- 前端 `client/src/tuning/groups.test.ts`：分組畫成 `<details>`、標題帶欄數；分組多（> 4）時預設收合、只展開有改動或錯誤的組；頭目部位（分組少）照舊全展開。
- 改了的既有測試：`test_rules_budget_bs1`（預算表欄位改成「至少包含」、核心規則多 9 欄、`TABLE_KINDS` 多兩個）、`test_triggers_composer_sk5`（n 次係數改成開了）、讀 `base_points`／`budget_points`／`permille_for` 的 15 個測試改讀預算表（斷言的值不變）。

### 截圖（`docs/art/shots/hc-b/`）
- `before-budget-table.jpg`：改之前（基準 `4d53775e5` 的後端＋改分組前的前端）：預算表 16 欄一長串。
- `after-budget-table.jpg`：改之後：14 組收合，標題帶欄數。
- `after-budget-table-shape-open.jpg`：展開「形狀」組。
- 伺服器 `trpg serve`（9171 基準、9172 本分支；`TRPG_TUNING=1`，存檔、帳號在暫存區），內建瀏覽器、網址帶 `?mute=1`。拍完已停掉兩個伺服器，埠沒在聽。

## 5. 檢查（最後一個程式 commit `664d3f426`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy src tests` | 0 |
| `lint-imports` | 0（14 kept） |
| `scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| `pytest tests/api -n 8` | 0（1355 passed, 1 skipped） |
| `pytest tests/bot -n 8` | 0（67） |
| `pytest tests/cli -n 8` | 0（148） |
| `pytest tests/content -n 8` | 0（3167） |
| `pytest tests/engine -n 8` | 0（5120） |
| `pytest tests/llm -n 8` | 0（495） |
| `pytest tests/narrative -n 8` | 0（479） |
| `pytest tests/roguelite -n 8` | 0（279） |
| `pytest tests/server -n 8` | 0（77） |
| `pytest tests/shared -n 8` | 0（76） |
| `pytest tests/sim -n 8` | 0（180） |
| `pytest tests/skillgen -n 8` | 0（4637 passed, 7 skipped） |
| `pytest tests/world -n 8` | 0（1328） |
| `pytest tests/*.py -n 8` | 0（256） |
| `pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | 0（979） |
| 逐招預算比對 | 0（different=0） |
| 78 場戰鬥比對 | 0（different=0） |
| `pnpm -C client typecheck` | 0 |
| `pnpm -C client test --run` | 0（4820） |
| `pnpm -C client build` | 0 |

測試目錄一次一組、各自 `-n 8`，`tests/llm` 與 `tests/skillgen` 沒同時跑。

API 沒改形狀：`scripts/export_openapi.py` 與 `gen:api` 重跑後 `client/openapi.json`、`schema.d.ts` 沒有差異。

## 6. 待 PM 決定

1. **鉤、擴散、吸收、預支沒併進 `primitive_points`**：規格說可以併。照最保守沒併（併了路徑會改、BS-1／SK-3b 的測試與工坊既有草稿的路徑都要跟著換），只是在工坊歸到同一組「原語點數」。要併的話是純改名。
2. **原語數量**：規格寫「44 個原語的 `base_points`」，實際有 `base_points` 的是 32 個（44 是 grep 連說明文字一起算到的）；其他原語的點數本來就由骰子、狀態、表面或預算表的係數算。
3. **形狀的查表倍率沒開**：錐形、十字、環形、連鎖依參數值查表（`by_value_permille`），表與 `param`、`power_primitives` 綁在形狀定義裡，搬起來很彆扭，照規格先不搬。這四種的基礎值搬到 `shape_budget` 但只在參數沒填時用，所以工坊也沒開（開了改了也幾乎沒效果，會誤導）。要開的話可以把查表也搬到 `shape_budget.<id>.by_value.<值>`（數字鍵現在寫得出路徑）。
4. **預算表裡沒開的非計價欄位**：稀有度效果數上限、改寫規則上限、角色階級門檻、升降地形的稀有度標記、升階放大規則、暈眩代價固定 2 回合。都是結構或規則，不是計價；要開告訴我。
5. **狀態、表面點數放進預算表而不是另開兩張表**：規格的分組要「狀態」「表面」在預算表裡，所以照第 1 項的做法搬家（沒列＝技能不能施加，語意同原本的 `budget_points` 省略）。代價是看狀態定義時點數不在同一個檔。
6. **原語、狀態的說明文字還寫 `base_points`／`budget_points`**：`skill_primitives.yaml` 有幾個原語的 `description_zh`（與 `workshop_text.yaml` 的對照原文）寫「預算：add_stack 的 base_points × amount」之類；YAML 註解已改，說明文字沒改（會動到工坊說明對照與規則包文字）。要不要順手改字。
7. **分組預設收合的門檻**：分組超過 4 組才預設收合（預算表 14 組全收合，只展開有改動或錯誤的組）；頭目部位通常 2～4 組，照舊全展開。
8. **新開的係數的建議範圍**：一律是現值的一半到兩倍（0 的給 0～2 或 0～500、負值給兩倍到 0），只是提示、不擋。

## 開發 PM 裁定（2026-11-21）

通過，已用 --no-ff 合併。逐招預算比對（434 招）和 78 場戰鬥比對都是 different=0。使用者問的「升起地形」（`primitive_points.raise_terrain`）已經可以在工坊調。

待決八件：
1. 鉤、擴散、吸收、預支不併進 `primitive_points`：同意，只放同一組就好。
2. 實際是 32 個原語：知道了。44 是我盤點時連說明文字一起算到的。
3. 錐形、十字、環形、連鎖的查表倍率：要開。使用者要的就是「能調的計價都看得到」。排進下一段「工坊開放 2」（和形態、裝備規則、物品生成一起），照建議搬到 `shape_budget.<id>.by_value.<值>`。
4. 非計價欄位不開：同意。
5. 狀態和表面的點數放進預算表：同意，這樣工坊的分組才找得到。
6. 說明文字還寫 `base_points`：要改，併進 HC-6（文字）。
7. 超過 4 組就預設收合：同意。
8. 建議範圍取現值的一半到兩倍，只提示不擋：同意。
