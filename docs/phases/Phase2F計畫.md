# Phase 2F 計畫：Phase 3 前的整理（重構，不加功能）

> 來源：Phase 3 前第一次審查（範圍 `efe8fa0..26cac0c`，Phase 2D–2E）。審查 10 點中，#1（依陣營過濾隱藏資訊）、#5（事件敘述移出 CLI）、#8（pending 資訊補強）排進 Phase 3-1；其餘在本階段處理。
> 目標：**行為不變**的重構。除非本規格明寫，戰鬥軌跡、技能資料、模擬數字都不應改變。

## 0. PM 決定

| # | 項目 | 決定 |
|---|---|---|
| 1 | 範圍 | 只做審查 #2、#3、#4、#6、#7、#9、#10；不新增原語、狀態、骨架、內容 |
| 2 | 拆段 | 2F-1 引擎重複邏輯（#2、#4、#7、#9、#10 引擎部分）；2F-2 組合器與 AI（#3、#6、#10 其餘） |
| 3 | 行為 | 引擎與 AI 軌跡不變（同種子同結果）；唯一允許改變的是 2F-2 #3 組合器的抽樣分布（隨機技能輸出可以不同） |
| 4 | AI 數值 | 寫死的 AI 數值搬進 `content/ai_profiles.yaml` 時**保留原值**，不改成從 shapes 倍率推導（那是平衡階段的事） |

## 1. 範圍外

- 審查 #1、#5、#8（Phase 3-1）。
- 任何平衡數值調整；`LOG_FORMAT` 不升版（若真的必要，寫進報告「待 PM 決定」）。
- 大型模擬（completion、matrix）：不跑，PM 驗收時自己跑。

## 2. 工作環境

- 在使用者的 Windows 電腦上執行（Git Bash，Linux 寫法）。
- 開發中只跑相關測試檔（`uv run pytest -q tests/<路徑> -x`）；commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**完整的 `uv run python scripts/check.py` 只在每個子階段最後跑一次**。
- 每完成一個交付項目就 commit。不要 push。
- 若既有測試的期望值需要改，報告中逐一列出原因（2F-1 理論上應為 0 個）。
- **軌跡不變的證據**：開工前先用目前的 HEAD 跑 3 場 `trpg battle --map <id> --seed <n> --log-json` 存到暫存目錄（建議地圖：一張有陷阱 build 的、`--ally-build build_trapper,build_guardian`；一張預設；一張 `--ally-build build_warlock,build_healer`），完成後再跑一次並比對 JSON 相同。報告列出指令與比對結果。

---

## 3. Phase 2F-1｜引擎重複邏輯

### 3.1 技能可用性與代價共用（審查 #2）

- `engine/skill_triggers.py` 的 `_usable` 改為呼叫 `engine/skills/targeting.py` 的 `_resource_problem(...)`（必要時改成公開名稱，例如 `resource_problem`），再加上被動專屬條件（`skip_turn`、每輪次數）。不再逐項複製沉默、法力、冷卻、每場次數、HP、層數的檢查。
- `_pay`（skill_triggers）與 interpreter 的 `_pay_costs` 合併為一個共用函式（例如 `pay_skill_cost(..., ap=...)`），放在合適的 engine 模組；被動、反應技、主動技能都呼叫它。
- 抽出 `check_trigger_depth(ctx, unit_id, skill_id, depth) -> bool`（超過上限時發 `TriggerLimitReached` 並回傳 False），取代 `engine/reactions.py`、`engine/skill_triggers.py` 的 `_resolve_one`、`engine/traps.py` 的 `_trigger` 三處重複。
- `stack_problem` 改用 `stacks.required_stack`，只保留一份「找第一個 `owner: self` 的 `consume_stack`」。

### 3.2 陷阱形狀（審查 #4，引擎部分）

- `interpreter.py`、`ai/utility.py`、`targeting.py` 三處 cross／square3 的 if/elif 改為共用同一個函式（例如 `targeting._center_tiles`，必要時改公開名稱）。
- `content/skills.py` 的 `TrapSpec.shape` 由 `Literal[...]` 改為驗證 shape ID 存在於 shapes 內容（載入時檢查，錯誤訊息要指出技能 ID）。
- AI 端改呼叫共用形狀函式這一步在本段做；`_TRAP_SHAPE_FACTOR` 等數值搬到內容檔留給 2F-2（4.2）。

### 3.3 移動中斷改用通用條件（審查 #7）

- `engine/battle.py` 的 `_do_move`：每走一步後，以通用條件判斷是否中斷——單位位置不等於該步的預期格、或單位被定身／暈眩／倒地／死亡／逃離。不再依賴「有陷阱且觸發了 `TrapTriggered`」這種事件類型判斷。
- 新增測試：用測試專用的技能資料（放在 `tests/` 的 fixture，不加進 `content/`）讓陷阱附帶推擊，確認移動在被推離路徑後中止、不會跳回原路徑。

### 3.4 陷阱事件（審查 #9）

- `TrapTriggered` 加 `tiles: tuple[Pos, ...]`（實際影響格，排序固定）。CLI 渲染不必改文字，但不能壞掉。
- `remove_traps_of` 改為回傳事件清單；`down_unit`／`escape_unit` 把這些 `TrapExpired` 併入自己的回傳值（同時仍寫入 `ctx.events`，不可重複發出）。
- 這兩項會改變事件內容。若因此需要讓 `LOG_FORMAT` 升版或舊紀錄無法重播，**先停下來寫進報告「待 PM 決定」**，不要自行升版；若新欄位有預設值、可向下相容讀取，則直接做。

### 3.5 引擎小項（審查 #10，引擎部分）

- `TrapState.attributes` 改為不可變（排序好的 tuple 或 frozen mapping），確保複製不共用參照。
- `skill_triggers.py` 的 `_NATURAL_MAX = 20` 改為從核心規則的骰面數取得（核心規則的資料或常數已有的話直接引用）。

### 3.6 驗收條件（2F-1）

1. `_usable` 不再自行檢查沉默／法力／冷卻／每場次數／HP／層數（以程式碼與一個「被沉默的被動不觸發」等既有測試為證）。
2. 代價支付只有一個實作；觸發深度檢查只有一個實作（`grep TriggerLimitReached src/` 只在該函式與事件定義出現）。
3. 陷阱形狀展開只有一個實作；`TrapSpec.shape` 使用不存在的 ID 會在載入時報錯（有測試）。
4. 陷阱推擊中斷移動的新測試通過。
5. `TrapTriggered.tiles` 有值；倒下時移除陷阱的 `TrapExpired` 出現在 `down_unit` 回傳值中且不重複（有測試）。
6. 3 場對照戰鬥 JSON 與開工前相同（若因 3.4 新欄位而不同，只能差在新欄位）。
7. `scripts/check.py` 全部通過；複雜度類 noqa 數量不增加。

---

## 4. Phase 2F-2｜組合器與 AI

### 4.1 組合器改讀骨架資料（審查 #3）

- **先量測**：寫一段腳本（`scripts/` 下，可保留）統計目前組合器每種骨架的「驗證失敗退回」次數與原因，輸出摘要表，結果寫進報告（改動前後各一次）。
- `skillgen/composer_parts.py` 的 `_passive_options`、`build_reaction_effects` 改為從骨架 YAML 的 `core.primitives` 與 `secondary.primitives` 篩選候選原語，不再寫死清單。若現有「自身增益」分支需要的原語（heal、shield）不在反應技骨架中：**不改骨架 YAML**，而是讓該分支只在骨架允許時出現，並在報告「待 PM 決定」說明是否要把 heal／shield 加進反應技骨架。
- 反應事件清單只留一個來源（`content/skills.py`），`content/battle.py`、`composer_parts.py` 的 `REACTION_EVENTS` 改為引用它；`content/environment.py` 中意義不同的同名常數改名（例如 `ENV_REACTION_EVENTS`）。
- 允許改變組合器輸出；`skill_fuzz.py --count 1000` 異常數必須仍為 0。依賴特定隨機技能輸出的測試若需更新，逐一列出。

### 4.2 AI 數值搬到內容（審查 #4，AI 部分）

- `ai/utility.py` 的 `_TRAP_SHAPE_FACTOR`、`_TRAP_MAX_ACTIVE`、`_TRAP_NEAR` 搬進 `content/ai_profiles.yaml`（含 pydantic schema），**原值不變**。形狀係數以 shape ID 為鍵；遇到沒有設定的形狀時用明確的預設值，不可 `KeyError`。

### 4.3 拆分過長函式（審查 #6）

- `ai/utility.py` 的 `_gains` 拆成 `_damage_gains`、`_kill_gains`、`_push_gains`、`_surface_gains`、`_cover_gains`、`_defend_gains` 等（名稱可調），各自回傳 `Fraction`，由 `_gains` 加總。移除其 C901／PLR0912／PLR0915 noqa。
- `skills/targeting.py` 的 `compute_area` 依 targeting 拆成 `_unit_area`、`_tile_area`、`_direction_area`、`_self_area`，移除 C901 noqa。
- `cli/main.py` 的 `main` 改用 argparse `set_defaults(func=...)` 分派，移除其複雜度 noqa。
- **不動**：`cli/render.py` 的 `describe_event`／`_describe_environment`、`engine/preview.py` 的 `_outcome`、`sim/metrics.py:314`（Phase 3-1 會一起處理事件敘述）。

### 4.4 其餘小項（審查 #10）

- `sim/batch.py` 的 `_template_rows` 由 9 元 tuple 改為小型 dataclass／NamedTuple，不再用 `i[7]`、`i[8]`。
- `skillgen/validate.py` 的 `_passive_violations` 中「被動必須是法術技且 `weapon_req: any`」改為讀 `content/skeletons/passive.yaml` 的欄位（需在骨架 schema 加欄位，原有其他骨架以預設值不受影響）。

### 4.5 驗收條件（2F-2）

1. 組合器被動與反應技的候選原語來自骨架 YAML（有測試：修改測試用骨架的 primitives 會改變候選）。
2. 改動前後的退回統計表在報告中；改動後反應技骨架的 `skeleton.core` 退回應明顯下降或為 0。
3. `REACTION_EVENTS` 只有一個定義；environment 的同名常數已改名。
4. AI 陷阱數值在 `content/ai_profiles.yaml`；未知形狀不會 `KeyError`（有測試）。
5. `_gains`、`compute_area`、`cli main` 的複雜度 noqa 已移除；`src/` 複雜度類 noqa 總數比 2F 開始前少至少 4 個（報告列出前後數字）。
6. 3 場對照戰鬥 JSON 與 2F-1 結束時相同（AI 行為不變）。
7. `skill_fuzz.py --count 1000` 異常 0；`scripts/check.py` 全部通過。

---

## 5. 報告格式（每段一份：`docs/phases/Phase2F-N報告.md`）

1. commit 列表。
2. 驗收逐條結果（測試名稱或指令輸出為證）。
3. 對照戰鬥比對結果（指令與結論）。
4. 修改過期望值的測試與原因。
5. 複雜度類 noqa 前後數量；新增的 noqa 逐一說明理由。
6. 待 PM 決定（最多 10 點）。
