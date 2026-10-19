# Phase 2H 計畫：冰凍、自身狀態代價、雙屬性縮放與專精加成

> 來源：Phase 2 完整性檢查 #2–#4（`docs/PM交接.md` 3.0.2），使用者 2026-10-19 決定排在 Phase 3 之前，並同意下列設計。
> 設計依據：`docs/design/06-技能.md` 6.3、6.6、6.10。

## 0. PM 決定（使用者已同意）

| # | 項目 | 決定 |
|---|---|---|
| 1 | 拆段 | 2H-1：冰凍 ＋ 自身狀態代價（狀態與代價）；2H-2：雙屬性縮放 ＋ 專精加成（屬性連動） |
| 2 | 冰凍效果 | 新狀態 `frozen`（冰凍）：硬控，跳過 1 回合；`control_group: hard`（和暈眩同類，一起受控制遞減）；**受到火焰傷害立即解除** |
| 3 | 冰凍來源 | 技能用 `apply_status` 施加；另加一條環境互動：**冰元素觸及站在水表面上的單位 → 冰凍 1 回合**（環境狀態不擲抵抗） |
| 4 | Boss | `boss_control_conversion` 加 `frozen: slow`（和暈眩一樣） |
| 5 | 自身狀態代價 | 新代價 `self_status`：只限 `vulnerable`、`weaken`、`slow`、`root`；依狀態點數折抵，算進現有折抵總上限（`total_cap` 500‰） |
| 6 | 雙屬性縮放 | 史詩以上；比例固定 **各 50%**；技能讀取縮放屬性的地方一律用兩屬性的平均 |
| 7 | 專精加成 | 技能的縮放屬性 ≥ 自己所有屬性（並列也算）時生效；技能定義 `range`（施放距離 +1，不加範圍大小）或 `duration`（狀態持續 +1）；**雙屬性技能不享專精** |
| 8 | 數值 | 所有新數值是初值、未經模擬，在資料檔註解標明；平衡留給平衡階段 |
| 9 | 大型模擬 | completion、matrix 不跑，PM 驗收時自己跑 |

## 1. 範圍外

- 其他未做的模板（`summon`、改寫規則型、修正型被動等，見 `docs/PM交接.md` 3.1.1）。
- 平衡與 AI 權重的調整（只做「AI 能理解新東西」的最小改動）。
- 技能卡片描述移出 CLI（Phase 3-1）。

## 2. 工作環境

- 在使用者的 Windows 電腦上執行（Git Bash，Linux 寫法）。
- 開發中只跑相關測試檔（`uv run pytest -q tests/<路徑> -x`）；commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**完整的 `uv run python scripts/check.py` 只在子階段最後跑一次**。
- 每完成一個交付項目就 commit。不要 push。
- 修改既有測試的期望值時，報告逐一列出原因。
- `tests/content/test_coverage.py`（2G）要求每個可由技能施加的狀態都被手寫技能使用、每個手寫技能都被裝備；新增內容時一併滿足。裝備限制：主動（含姿態）≤ 6、被動 ≤ 2、反應 ≤ 1。
- 若事件 schema 必須改（例如 `StatusRemoved.reason` 加新值），可以升 `LOG_FORMAT`，報告說明。

---

## 3. Phase 2H-1｜冰凍 ＋ 自身狀態代價

### 3.1 冰凍狀態

- `content/statuses.yaml` 新增 `frozen`（`name_zh: 冰凍`）：比照 `stun`——`duration: 1`、`expires: turn_end`、`skip_turn: true`、`control_group: hard`、`save_attr: con`、`min_rarity: rare`、`budget_points: 8`（初值）。
- 新的資料欄位（例如 `removed_by_element: [fire]`，名稱可調，寫進檔頭註解）：帶有者受到該元素的傷害（數值 > 0）時立即移除此狀態，發出 `StatusRemoved`（原因例如 `thawed`）。由資料驅動，不在引擎寫死 `frozen`。
- `content/rules/core.yaml`：`boss_control_conversion` 加 `frozen: slow`。
- `content/ai_profiles.yaml`：`status_values` 加 `frozen`（初值同 `stun`）。檢查 AI 其他地方是否寫死 `stun`（例如預覽、控制統計 `CONTROL_STATUSES`），有的話一併納入 `frozen`。
- 測試：施加後跳過回合；受火傷解除（含事件）；受非火傷不解除；Boss 轉成緩速；控制遞減與暈眩同組。

### 3.2 冰元素凍住水中的單位

- `content/interactions.yaml` 新增規則（例如 `ice_freezes_unit_in_water`）：`trigger: element`、`element: ice`、`target: unit`，條件是該單位所在格的表面是 `water`，結果是施加 `frozen` 1 回合（不擲抵抗）。
- 需要新的 outcome op（例如 `apply_status`，帶 `status` 與 `duration`）以及「單位所在格表面」的條件欄位；放進 `content/environment.py` 的 schema，引擎依資料執行。
- **順序**：同一次冰元素觸及會同時讓水變冰（既有 `ice_freezes_water`）。判斷單位條件時要用**觸及前**的表面，確保站在水上的單位會被凍住；以測試證明。
- 測試：冰傷打中站在水上的單位 → 冰凍；站在一般地面 → 不冰凍；Boss 站在水上 → 依轉換規則變緩速（若環境狀態不走 Boss 轉換，報告說明並採保守做法：一樣轉換）。

### 3.3 自身狀態代價 `self_status`

- `SkillCost` 新增 `self_status`（例如 `{status: vulnerable, duration: 2}`）。
- 允許的狀態與折抵寫在 `content/skill_budget.yaml`（例如 `self_status: {allowed: [vulnerable, weaken, slow, root], per_point_permille: 40, cap: 250}`，初值）：折抵 ＝ 狀態的 `budget_points` × 有效回合 × `per_point_permille`，先套用自己的上限，再和其他折抵一起截斷在 `total_cap`。
- **持續時間的意義**：狀態在帶有者回合結束時倒數，所以施放當回合結束就會 −1。`duration` 限制為 2–3（1 等於沒有效果），「有效回合」＝ `duration − 1`。在 schema 驗證並寫進註解。
- 結算：技能支付代價時（和法力、扣血同一處，2F 已合併為共用函式）對施放者施加，不擲抵抗；姿態、被動、反應技不可使用此代價（載入時驗證）。
- 組合器：主動技能以一個小機率加入 `self_status`（權重放 `content/skill_composer.yaml`，初值）。`scripts/skill_fuzz.py --count 1000` 例外 0。
- AI：評分時把代價狀態的價值當負收益（用 `status_values` 的值，初值），避免 AI 免費使用；若改動牽涉太廣，採最小做法並在報告說明。
- CLI 的技能說明（`trpg skills show`、技能卡片描述）顯示此代價。
- 測試：施放後自己帶有該狀態；預算折抵正確（含上限）；不允許的狀態、duration 1、非主動技能都被拒。

### 3.4 示範技能

- 新增至少 2 個手寫技能並裝備：一個施加 `frozen` 的冰系控場技（例如裝在 `build_storm`），一個帶 `self_status` 代價的技能（例如捨身型近戰，裝在主題相符的 build）。預算合格（0.7–1.0）。
- 覆蓋率測試擴充：`self_status` 代價至少被一個手寫技能使用。

### 3.5 驗收條件（2H-1）

1. 3.1、3.2、3.3 的測試都通過（報告列出測試名稱）；冰凍的規則全由資料驅動（`grep -rn frozen src/` 除了註解之外沒有結果）。
2. 冰元素觸及水上單位的順序測試通過。
3. `self_status` 的預算折抵、驗證拒絕、結算各有測試；`skill_fuzz.py --count 1000` 例外 0。
4. 示範技能預算合格、已裝備、覆蓋率測試通過。
5. `trpg battle ... --log-json` → `replay` 通過，報告附看得到冰凍或自身狀態代價的節錄。
6. `scripts/check.py` 全部通過；複雜度類 noqa 不增加。

---

## 4. Phase 2H-2｜雙屬性縮放 ＋ 專精加成

### 4.1 雙屬性縮放

- `SkillDef` 新增選填欄位（例如 `secondary_scaling_attr`）。驗證：只有 `epic`、`legendary` 可用（最低稀有度寫在資料，例如 `skill_budget.yaml` 的稀有度區或 `core.yaml`）；不可和 `scaling_attr` 相同。
- 一個共用函式（例如 `skill_scaling_value(rules, unit, skill) -> int`）：有第二屬性時回傳兩個有效屬性的平均（整數，無條件捨去），否則回傳原屬性。**所有讀取技能縮放屬性值的地方都改用它**：法術傷害、治療、護盾的縮放、法術命中值、控制抵抗的攻方值、預覽（目前至少 `interpreter.py`、`targeting.py`、`control.py`、`preview.py`；用 grep `scaling_attr` 找全）。武器技的武器傷害與武器命中照舊（讀武器的屬性）。
- 預算不變（6.12：稀有度不增加強度）。
- 組合器：`epic` 以上以小機率加第二屬性（權重放 `skill_composer.yaml`，初值）。
- CLI 技能說明顯示「力量 50%＋智力 50%」之類的字樣。
- 測試：平均值計算（含奇數捨去）；非史詩被拒；與主屬性相同被拒；傷害、命中、抵抗都用平均值。

### 4.2 專精加成

- `SkillDef` 新增選填欄位（例如 `mastery: range | duration`）。驗證：`range` 只能用在有施放距離（`shape.range`）的技能；`duration` 只能用在有 `apply_status` 效果的技能；有第二屬性的技能不可設定。
- 生效條件：施放者的 `scaling_attr` **基礎屬性**值 ≥ 其他每一個基礎屬性（並列也算）。用基礎屬性（單位範本的屬性，不含狀態加值），讓配點決定專精，不受戰鬥中增益影響；寫進註解。
- 效果：`range` → 施放距離 +1（不改範圍形狀大小）；`duration` → 此技能施加的狀態持續 +1（不影響代價的 `self_status`、表面、陷阱）。合法目標、AI、預覽都要看到生效後的距離與持續。
- 預算不計（屬於 build 條件的小加成）；寫進 `skill_budget.yaml` 註解。
- 組合器：以一定機率給 `mastery`（權重放 `skill_composer.yaml`，初值），只在合法時給。
- CLI 技能說明顯示專精加成，且標示該單位目前是否生效（若單位資訊不可得，只顯示加成內容）。
- 測試：最高屬性（含並列）生效、非最高不生效；`range` 讓距離 +1 的目標變合法；`duration` 讓狀態 +1；不合法組合被拒。

### 4.3 示範技能

- 至少一個手寫的雙屬性技能（史詩，例如力量＋智力的魔劍技）與兩個帶 `mastery`（`range`、`duration` 各一）的手寫技能並裝備；可以替既有手寫技能加 `mastery`，不一定要新增。
- 覆蓋率測試擴充：雙屬性、`mastery: range`、`mastery: duration` 各至少一個手寫技能使用。

### 4.4 驗收條件（2H-2）

1. 4.1、4.2 的測試都通過（報告列出測試名稱）。
2. `grep -n scaling_attr src/trpg/engine` 中，讀取技能縮放屬性值的地方都經過共用函式（報告列出 grep 結果與說明）。
3. 示範技能已裝備、預算合格；覆蓋率測試通過。
4. `skill_fuzz.py --count 1000` 例外 0；`trpg battle` ＋ `replay` 通過並附節錄。
5. `scripts/check.py` 全部通過；複雜度類 noqa 不增加。

---

## 5. 報告格式（每段一份：`docs/phases/Phase2H-N報告.md`）

1. commit 列表。
2. 驗收逐條結果（測試名稱或指令輸出為證）。
3. 新增的資料欄位與初值一覽。
4. 新技能或修改的技能（ID、中文名、預算比例、裝備於哪裡）。
5. 修改過期望值的測試與原因。
6. 複雜度類 noqa 前後數量。
7. 待 PM 決定（最多 10 點）。
