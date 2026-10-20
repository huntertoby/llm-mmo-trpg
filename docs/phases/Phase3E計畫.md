# Phase 3E 計畫｜3C／3D 審查後的整理

> 開發 PM 撰寫，2026-10-20。來源：審查 agent 對 `26c282d..HEAD`（Phase 3C、3D 全部）的結論（`PM交接.md` 6.5）。
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
