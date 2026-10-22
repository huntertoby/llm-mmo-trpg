# Phase 3E 計畫｜3C／3D 審查後的整理

> 開發 PM 撰寫，2026-10-20。來源：審查 agent 對 `26c282d..HEAD`（Phase 3C、3D 全部）的結論（`開發PM交接.md` 6.5）。
> 共用的範圍外、工作環境、報告格式沿用 `docs/phases/Phase3C計畫.md` 第 1、2、9 節。

## 0. PM 決定

審查結論：確定性（沒有 `random`、`hash()`、時間、`uuid`；set 迭代有排序；AI 除法用 `Fraction`）、依賴方向、引擎沒有寫死特定技能或單位 ID 的特例，都沒問題。建議先排一個整理子階段。

| # | 審查項目 | 排在 |
|---|---|---|
| 1 | LLM／組合器產生的技能驗證比內容庫少兩項（`granted_skill_problems`、規則改變型傳說的 `ap_cost`），兩處各自呼叫 `skill_problems(...)` | **3E-1** |
| 4 | 投擲、直線衝撞自己組傷害，沒吃賭注倍率、`consume_stack` 加成、`add_element`（可能是 bug） | **3E-1** |
| 6 | `battle_result().source_of(template_id)` 以範本 ID 為鍵；生成技能沒有正式的「加進規則包」API | **3E-1**（3-5 需要） |
| 7 | `EffectSpec.param_values` 手動列欄位名 | **3E-1**（只做「從 `model_fields` 推導」；LLM 子 schema 屬 Phase 4） |
| 8 | 區域預算寫死形狀格數、未知形狀回傳 1 | **3E-1** |
| 9 | `PRONE` 等常數定義 7 次；`next_unit_id` 重複 | **3E-1** |
| 10 | AI 評分的魔法數字（衝撞 ×3、瞬步 3＋2） | **3E-1** |
| 2 | Python schema 寫死上下限、形狀、狀態 ID，與 `skill_primitives.yaml` 重複 | **3E-2**（Phase 4 之前） |
| 3 | 「能不能站在這格／最近空格」約 9 份實作 | **3E-2**（Phase 4 之前） |
| 5 | `_Cast` 上帝類別（2004 行）、5 個模組延遲匯入 interpreter | **3E-3**（Phase 4 之前的獨立重構，opus） |

順序：3E-1 → Phase 3-5（3-5a／b／c）→ 3-6 → 3E-2、3E-3 → Phase 4。

### 0.1 3E-1 驗收與「待 PM 決定」的處理（2026-10-20）

- 驗收：`check.py` 全過；`narrow_halls` 種子 4（`build_telekinesis,build_charger`）重播一致；CLI 戰鬥快照全部不變；實作者的 `skill_fuzz --count 1000` 全過。`LOG_FORMAT` 維持 `/34`。投擲與衝撞改用共用傷害後，現有內容只影響「戰神降臨」開啟時的蠻牛衝陣（＋18%）。

| # | 項目 | 決定 |
|---|---|---|
| 1 | `skill_problems` 可選引用表保留，正式路徑走 `skill_reference_problems` | 接受 |
| 2 | `AllyResult` 加 `mana`、`max_mana` | 接受；3-5a 需要再加 |
| 3 | 範本查詢改名 `*_of_template`，同範本兩個時報錯 | 接受 |
| 4 | `Ruleset.with_skills` 同 ID 不同內容報錯 | 接受（3-5 不需要覆蓋） |
| 5 | `chain` 沒有 `cell_count`，用在 `zone` 會報錯 | 接受（目前不會產生） |
| 6–8 | `ids.py` 範圍、AI 預設值、3E-2 一併檢查 `cell_count` | 接受 |

## 1. Phase 3E-1｜小整理（sonnet，約 40 分）

1. **技能驗證共用**（#1）：在 `trpg.content` 新增 `skill_reference_problems(skill, ruleset, skills)`，內容庫 `_check_skills` 與 `skillgen/validate.py` 都改呼叫它；正式路徑必須帶齊所有引用表（`_Refs` 欄位不可為 `None`，或改成必填）。補測試：`validate_skill` 拒絕 `grant_skill` 指向傳說／改寫規則型／不存在的技能、規則改變型傳說 `ap_cost` 不等於 `legendary_activation_ap`。
2. **攻擊傷害共用**（#4）：抽出共用的攻擊傷害組裝（例如 `_Cast._attack_damage(...)`），`damage`、`hurl_object`、`charge_through` 三處共用，吃到賭注倍率、層數加成、`add_element`、修正規則。若某項加成是刻意排除，在 schema 擋掉該組合並寫進報告。補「投擲／衝撞 ＋ 修正規則（`add_element`、傷害 ‰）」的測試。若結算結果改變，重錄快照並說明。
3. **3-5 需要的介面**（#6）：
   - `BattleResult` 以 `unit_id` 為鍵查源力、HP、法力（`source_of(unit_id)` 等；保留以範本查的便利函式時要在兩個同範本單位時報錯）。
   - `Ruleset.with_skills(skills)`：加入生成的技能、重新驗證（走第 1 點的共用驗證）並重建索引；`sim/skill_fuzz.py` 改用它，不再 `model_copy` ＋ 手動 `model_post_init`。
4. **`param_values` 推導**（#7）：欄位清單從 `EffectSpec.model_fields` 推導，排除 `type`、`affects`、`condition` 等非參數欄位；加測試確保每個欄位不是參數就是明列排除。
5. **區域預算格數**（#8）：`zone_cell_count` 改用引擎的形狀幾何在空地圖上計算，或在 `skill_shapes.yaml` 加 `cell_count`；未知形狀報錯。
6. **常數集中**（#9）：新增 `engine/ids.py`（或同等位置）集中 `PRONE`、`CONCEALED`、`TOPPLABLE`、`DEFENDING`、`ELITE_TAG` 等狀態與標籤常數，以及 `next_unit_id(state)`；所有重複定義改引用它。
7. **AI 魔法數字**（#10）：衝撞每敵 ×3、瞬步 3＋2 搬進 `AiWeights`／`content/ai_profiles.yaml`，預設值不變（戰鬥結果不應改變）。

### 1.1 驗收條件（3E-1）

1. 第 1–7 點各有測試或說明；`validate_skill` 與內容庫的檢查項目一致（加一個測試比對兩者對同一批壞技能的結果）。
2. 除第 2 點外，戰鬥結果不變（CLI 戰鬥快照不變；若第 2 點改變了結果，只重錄受影響的快照並說明）。
3. `check.py` 全過；重播一致；`scripts/skill_fuzz.py --count 1000` 全過。

## 2. Phase 3E-2、3E-3（Phase 4 之前，規格屆時再細化）

- **3E-2**（#2、#3）：數值上下限、允許形狀、狀態 ID 以 YAML 為唯一真相來源（pydantic 只留型別）；落點與最近空格集中成 `landing_problem(...)`、`nearest_free(...)`，`charge` 改用 `unit_push_block`。
- **3E-3**（#5）：interpreter 改成「原語 → handler」註冊表、拆到 `skills/primitives/*.py`，對外入口抽成 `casting.py`，解開延遲匯入；結算模型統一（都回傳效果批次）。

## 3. Phase 3 結束審查後的 3E-2／3E-3 排程（2026-10-23）

> 審查全文：`docs/phases/Phase3審查-Python.md`（R1～R12）、`docs/phases/Phase3審查-前端.md`（F1～F12）。審查結論：確定性與依賴方向良好；主要風險是「新增原語要改很多處、漏做不報錯」、變奏驗證漏洞（R1，已實測崩潰）、前端點擊式選單與 Esc 衝突。上方第 2 節的舊 3E-2／3E-3 項目併入下表。一次最多 2 個 agent；每段合併只跑快速檢查，全量每 2～3 段一次。

### 3.1 3E-2（Phase 4 之前必做）

| 段 | 內容 | 來源 | 模型 | 前置／平行 |
|---|---|---|---|---|
| 3E-2a | **技能資料安全**：① 變奏檢查走過 `add_effect`／`replace_effect`，禁用清單改 `skill_primitives.yaml` 旗標（例 `lookup_by_skill_id: true`），回歸測試（含 R1 的實測案例）；`copying`、`skill_triggers` 命中後修正、AI 召喚範本改用生效型態或明確擋下 ② 統一 `SkillDef.iter_effects(include_followup=, include_variants=)`，四份走訪改用它（`combo.py` 補 zone 子效果） | R1、R3 | sonnet | 現在派；與 3E-2c 平行 |
| 3E-2c | **測試基礎**：sim 平行池改 `ProcessPoolExecutor` 並抽 `sim/parallel.py`（`batch.py`、`attack_flow_report.py` 共用）；加 pytest-timeout（預設 300 秒，slow 例外）；jobs>1 的測試 `xdist_group` 或 slow；清 `tests/**/__pycache__/*.pyc.<pid>`；文件寫明 agent 在自己 worktree 跑、`UV_NO_SYNC=1` 或 `uv run --frozen` | R5、R12 前半 | sonnet | 現在派；與 3E-2a 平行 |
| 3E-2b | **原語登錄表**：interpreter 的 if 鏈改「原語 → handler」登錄表、拆到 `skills/primitives/*.py`、對外入口 `casting.py`（解開延遲匯入）；載入時檢查 `skill_primitives.yaml` 每個原語在解譯器、預算、AI 估值、敘事、預覽都有對應，缺了就報錯（含 `tile_effect` 沒有預設分支） | R2、R7、舊 3E-3 #5 | **opus** | 3E-2a 後 |
| 3E-2d | **前端點擊式選單與 Esc**：共用 `usePopupMenu`（Esc、點外面、同時一張、最大高度捲動），`.more-list`、`.top-popup` 改用；浮動卡處理過 Esc 就不讓 BattleScreen 再處理；`.decision-card` 最大高度可捲；規則測試補 `position: absolute`＋`z-index ≥ 20`、移除 `.modal-backdrop` 死碼與白名單、`role=tooltip` 規則收緊 | F1、F2、F8、F12 | sonnet | 3E-2a／c 之後任一空檔 |
| 3E-2e | **glossary API 與前端對照表**：效果／條件／觸發中文名與原語 `player_description` 進 glossary API，前端 `skillParts.ts` 的 `EFFECT_NAMES`／`CONDITION_NAMES`／`TRIGGER_NAMES` 改讀它；`FieldSpec` 旗標；英雄武器外觀改由後端外觀欄位提供（照 `SummonLookView`） | F4、舊 3E-2 | sonnet | 3E-2b 後 |
| 3E-2f | **YAML 唯一來源與落點函式**：數值上下限、允許形狀、狀態 ID 以 YAML 為唯一來源；`landing_problem(...)`、`nearest_free(...)`、`charge` 改用 `unit_push_block` | 舊 3E-2 #2、#3 | sonnet | 3E-2b 後 |
| 3E-2g | **LLM 技能提議 schema 設計**（只寫設計文件＋最小原型，不改現有 schema）：由 `skill_primitives.yaml` 的 `params` 產生每原語一支的 discriminated union，驗證後轉回 `EffectSpec`；錯誤回饋格式 | R4 設計部分 | **opus** | 3E-2b 後；Phase 4 規格的前置 |

### 3.2 3E-3（可延後，Phase 4 期間或之後穿插）

R4 拆 `skills.py`、R6 `LOG_FORMAT` 版本策略（Phase 4 大量新增原語時提前）、R8 寫死數值移 YAML、R9 `engine/summons/`、`engine/gear/` 子套件與改名、R10 `PLR0917` 改 keyword-only 與 `_outcome` 表驅動、R11 不再吞 `KeyError`、R12 後半 `_relabel` 結構化；F3 觸控開啟說明框、F5 配色唯一來源（Phase 4 開放新元素則提前）、F6 拆 `BattleScreen.tsx`（Phase 4 前至少把 `onTileClick` 抽成純函式）、F7 拆 `styles.css` 與 z-index 分層、F9 浮動卡監聽器依賴、F10 Pixi Text 物件池、F11 外觀 JSON 型別；3-34b 根本改善（無旋鈕核心在高階搭配有旋鈕效果）；藤蔓底影無外框（一行，併進碰到 `summonArt.ts` 的段落）。

### 3.3 3E-2a 規格

見 3.1 表的 3E-2a 列。驗收：pytest（R1 實測案例被擋下並給中文訊息；變奏加 `delayed_damage`／`copy_skill`／`zone` 都擋；`iter_effects` 涵蓋 followup、陷阱、反噬、變奏、zone 子效果的表格測試；既有技能全部仍合法）；相關測試全過；`ruff`、`mypy`。

### 3.4 3E-2c 規格

見 3.1 表的 3E-2c 列。驗收：`scripts/check.py` 快速版與 `--full` 各跑一次全過並記時間；模擬子行程故意失敗時丟 `BrokenProcessPool` 而不是卡住（測試）；`docs/開發PM交接.md` 由 PM 更新。

### 3.5 3E-2a、3E-2c 驗收（2026-10-23）

- PM 合併兩段（無衝突）；`check.py --full` 全過（4 分 33 秒，pytest 含 slow；唯一失敗是 PM 改 `runner.py` 文件字串的一行過長，修正後 ruff 通過）。
- **3E-2a**：`skill_primitives.yaml` 的 `zone`、`delayed_damage`、`copy_skill` 加 `lookup_by_skill_id: true`，跨檔案驗證檢查基礎型態與每個變奏型態（R1 實測案例回歸測試）；帶變奏的技能不能被 `copy_skill` 複製；命中後修正規則用實際施放型態；AI 召喚範本用生效型態；`SkillDef.iter_effects(...)`／`walk_effect` 取代四份走訪（`combo.py` 補 zone 子效果）。報告 `Phase3E-2a報告.md`。**PM 決定 `LOG_FORMAT` → `/57`**（複製與修正比對是引擎行為變更）。待 PM 決定：#1 旗標檢查只在跨檔案驗證（直接建 `SkillDef` 不擋）→ 接受，3E-2g 的 LLM 提議流程一定走驗證器；#2 帶變奏技能不能複製、#3 型態從最近的 `skill_used` 事件取得 → 接受；#5 `iter_effects` 預設不含反噬與修正命中後效果 → 接受（各呼叫端沿用原涵蓋範圍）。
- **3E-2c**：`sim/parallel.py`（`ProcessPoolExecutor`，子行程失敗丟 `BrokenProcessPool`，有測試）；pytest-timeout 300 秒、slow 1800 秒（`tests/conftest.py`）；jobs>1 的 8 支測試 `xdist_group("sim_pool")`＋`--dist loadgroup`；`check.py` 在 pytest 前清 `*.pyc.<pid>`。實作者量測：快速版約 113 秒、`--full` 約 336 秒（另一 agent 同時跑）。報告 `Phase3E-2c報告.md`。待 PM 決定：#1～#4 → 接受；#5 `_relabel`、#6 `test_demo_balance` 自己的池 → 3E-3。

### 3.6 3E-2d 驗收（2026-10-23）

- PM 合併（無衝突）；前端 typecheck、vitest 762、`pnpm build` 全過（只動 `client/`）。共用 `usePopupMenu`（Esc、點外面、同時一張），`.more-list`、`.top-popup` 改用；浮動卡與格子資訊卡處理 Esc 後 `stopPropagation`（第一次 Esc 只關卡片、第二次才取消瞄準）；`.decision-card` 最大高度可捲；刪除 `.modal-backdrop`、`.fallback-list` 死碼；藤蔓底影改無外框、透明度 0.35。**發現**：vitest 不處理 CSS，`styles.css?raw` 在測試裡是空字串，原本的 CSS 規則一直空過 → 改讀真檔並加長度守門；規則補 `absolute`＋`z-index ≥ 20` 白名單、`.decision-card` max-height、`role=tooltip` 只在共用元件、掃描擴到 `.ts`（PM 抽查其他 `?raw` 都是讀 YAML，正常）。報告 `Phase3E-2d報告.md`。
- 待 PM 決定：#1 截圖無法存檔、詢問視窗以注入假卡驗證、藤蔓底影未目視 → 接受（使用者試玩時順帶看）；#2 頂端面板開著時 Esc 只關面板、#3 點外面關面板的同一下仍送到棋盤、#4 選單與滑過的浮動卡可並存、#5 `.resize-handle` 列為版面例外 → 接受。

### 3.7 3E-2b 驗收（2026-10-23）

- PM 合併（無衝突）；`check.py --full` 全過（4 分 32 秒）；`oil_depot` 種子 58 `--log-json` ＋ `replay` 一致。**純重構、行為不變**：既有測試未改全過（含 CLI 快照）；實作者比對 875822c 與 HEAD 的 `sim maps`（4 種子）、`sim skills --demo`（434 場）JSON 逐位元組相同；`LOG_FORMAT` 維持 `/57`。`interpreter.py` 2464 → 約 620 行（只留施放入口）；施放流程 `skills/cast.py`（`Cast`、`TriggeredCast`、`GearCast`）；48 個原語 handler 在 `skills/primitives/*.py`（7 模組），未登錄的原語丟 `KeyError`；`trpg/primitive_coverage.py` 載入時檢查每個原語在解譯器、預算、AI 估值、敘事、預覽都有對應（CLI 與 API `create_app` 呼叫）；預算與敘事的預設分支改明確項目。`PLC0415` 24 → 14。報告 `Phase3E-2b報告.md`（含 **Phase 4 新增原語要改哪幾處** 清單）。
- 待 PM 決定：#1 AI 估值與預覽的對應項是宣告表（只確保有項目）、#2 直接呼叫 `load_library()` 不檢查（靠測試）、#4 只檢查缺項、#5 拆檔一個 commit、#6 `Cast` 輔助方法改公開 → 接受；#3 剩下 11 個引擎內延遲匯入 → 3E-3（R7 剩餘）。

