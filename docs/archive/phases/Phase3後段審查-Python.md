# Phase 3 後段審查｜Python 端（ebaebb32..HEAD，`src/trpg`、`content`、`tests`）

> 審查者：opus 審查 agent（只讀），2026-10-29。範圍：3-47～3-55、3H、3I、3K、3S、3J 形態、3R 種族。
> 抽樣：`engine`（skills/primitives 登錄表、forms、race_skills、stack_gain、self_costs、wind）、`skillgen`（proposal*、composer_parts、budget、validate、option_effect_rules）、`content`（skills.py、races.py、forms.py）、`llm`（propose、prompts）。
> 只跑了 `tests/test_architecture.py`、`tests/test_primitive_coverage.py`（15 passed）與 `lint-imports`（7 kept）。

## 上次審查（R1～R12）對照

| 項目 | 狀態 |
|---|---|
| R1 變奏偷帶禁用原語 | **已解決**（`skill_primitives.yaml` 的 `lookup_by_skill_id` 旗標） |
| R2 原語分派無預設分支 | **已解決**（`engine/skills/primitives/__init__.py` 登錄表＋`trpg/primitive_coverage.py` 載入時檢查解譯器／預算／AI／敘事／預覽） |
| R3 效果樹走訪四份 | **已解決**（`SkillDef.iter_effects`，`content/skills.py:2572`） |
| R4 schema 不適合 LLM | **LLM 端已解決**（`skillgen/proposal.py:401-610` 由 YAML 產生 discriminated union）；`skills.py` 拆檔未做且更大（見第 5 點） |
| R5／R12 平行池 | **已解決**（`sim/parallel.py`，`ProcessPoolExecutor`） |
| R6 `LOG_FORMAT` 策略 | **惡化**（見第 4 點） |
| R7 延遲 import | 改善（`PLC0415` noqa 24 → 17） |
| R8 引擎寫死數值 | 未處理且新增（見第 7 點） |
| R9 `engine/` 太扁平 | 未處理（頂層 65 個模組） |
| R10 `PLR0917` | 21 → 22（新增 `engine/stack_gain.py:79` `_collect`）；`C901` noqa 維持 2 |
| R11 吞 `KeyError` | 擴散（見第 8 點） |

確定性：引擎內無 `random`／時間／`hash()`／`uuid`；`float` 只出現在 skillgen 的顯示字串。依賴方向 7 條契約全部維持。`<player_input>` 包裝正確（`llm/prompts/builder.py`）。

## 發現（依嚴重度）

1. **【Phase 4 阻礙】修正規則的 change 種類是「第二套原語」，散在 Python、沒有對應檢查**
   位置：`content/skills.py:1864`（`MODIFIER_CHANGES`）、`:1896`（`CHANGE_TARGETS`）、`:1922`（`SELF_ONLY_CHANGES`）、`:2047`（`ModifierChange` 欄位）；`skillgen/budget.py:1365-1398`（無數值旗標 tuple、每 100‰ tuple、`per = {...}[kind]` 漏寫即執行時 `KeyError`、三行逐種類的 `sign` 特例）；`skillgen/player_text.py:40`、`:277`；`engine/modifiers.py`。
   本範圍新增 7 種（召喚 5、化形 2），每種約改 8 處，漏寫不報錯。`proposal.py:111` 的 `CLOSED_SKELETONS` 含 `modifier`：Phase 4 要開放修正型技能時，沒有 YAML 可以產生 schema。
   修：新增 `content/modifier_changes.yaml`（或 `skill_primitives.yaml` 的 changes 區段）宣告 kind、可套用對象、self_only、預算單位與點數鍵、正負號、玩家文字；`primitive_coverage` 加 change 表。**中**。

2. **【Phase 4 阻礙】預算旋鈕表寫死在 Python、預設回傳空**
   位置：`skillgen/composer_parts.py:189-232`（`fixed.get(kind, ())`）。`proposal_budget.budget_filler` 靠它補 LLM 提議的數值。實測下列原語有數值參數、`budget_basis` 不是 `fixed`，卻沒有旋鈕：`grant_ap`、`extra_reaction`、`summon`、`zone`、`revive`、`restore_resource`（耐力）。LLM 選這些原語時數值只能停在最小值，容易「過弱」或退回；新原語漏寫旋鈕不報錯（不在 `primitive_coverage` 內）。
   修：在 `skill_primitives.yaml` 的 params 加 `knob`（階梯來源＋權重），或明寫 `knob: none`；coverage 檢查「非 fixed 的原語必須宣告」。**中**。

3. **種族技與形態是另外兩套效果語言；種族技只檢查第一個效果**
   位置：`content/races.py:210`（`RACE_EFFECT_SPECS`）＋`RaceEffect`；`engine/race_skills.py:68`（`_SHAPE_FIELDS` 重寫形狀選取欄位知識）、`:481`（`_EXECUTORS`）、`_PROBLEMS`；`engine/ai/race.py:151`（`_SCORERS.get` 漏寫時 AI 靜默不用）；`content/forms.py:153-212`（`FormEffects`／`FormEntry` 每種加成一個欄位）＋`engine/rules/forms.py:75-140`（每欄位一個查詢函式）。push／pull／create_surface／hurl_object 已有原語，卻另寫一套；兩者都沒有 coverage 檢查。
   潛在 bug：`race_skill_problem`（`race_skills.py:135`）與 `_required_fields`（`:106`）只看 `effects[0]`，但 `MAX_RACE_EFFECTS = 3`，`do_race_skill`（`:516`）執行全部效果。docstring 寫「各效果自己的條件」，與實作不符。目前只有一招是兩個效果，所以還沒出事。
   修：短期改成檢查全部效果，或在內容驗證限制第 2 個以後只能是不需選取的類型；加測試確認每個 race effect 都有 executor、problem、scorer、敘事。長期（LLM 生成種族或形態之前）把形態加成改寫成既有的修正規則或狀態。**中**。

4. **`LOG_FORMAT` 版本策略惡化（R6）**
   位置：`engine/runner.py:41`。本範圍從 `/56` 升到 `/85`（29 次）；docstring 變更紀錄佔 `:42-389` 約 350 行；`BattleLog`（`:453`）仍然沒有 `ruleset_hash`。Phase 4 LLM 生成技能之後，規則包會每局不同，「升版號」無法表達可否重播。
   修：照 R6——結構版本與可重播性分開；`BattleLog` 記 `ruleset_hash`（`roguelite/save.py:93` 已有函式）；版本歷程移到 `docs/`；加 golden 紀錄重播測試。**中**。

5. **`content/skills.py` 繼續膨脹**
   3564 → 4225 行；`EffectSpec` 欄位 52 → 56、`SkillDef` 34 → 36、`model_validator` 18 → 22。LLM 端已有提議模型隔開，但驗證規則、change 表、變奏、組合規則全擠在一檔，第 1 點的整理也會碰這裡。
   修：純搬移拆成 `content/skills/`（effects、modifiers、variants、composition、validators）。**中**（機械性）。

6. **「form」一詞撞名**
   `skillgen/proposal_forms.py`（提議的「型態」：standard／on_*、`FormPlan`、`skill_form()`）對上 3J 的「形態」（`content/forms.py`、`engine/forms.py`、`engine/skills/forms.py`、`engine/rules/forms.py`、`FormDef`、`enter_form`）；測試 `test_proposal_forms.py` 和 `test_form_start_3j4b.py` 一樣混。Phase 4 兩邊都要動。另外 `_MAX_EFFECTS = 4` 在 `proposal.py:120` 和 `proposal_forms.py:51` 重複定義。
   修：提議那邊改名為 layout（`proposal_layouts.py`、`LayoutPlan`、JSON 欄位 `layout`），常數合併成一個。**小**。

7. **引擎寫死數值與內容 ID（R8 未處理且新增）**
   舊的還在：`gear_triggers.py:46`、`summon_variants.py:26`、`ai/charge.py:19`。新增：`race_skills.py:63` `DECOY_TEMPLATE = "summon_foxfire_decoy"`、`:65` `DECOY_LIFETIME_ROUNDS = 3`、`self_costs.py:19` `OVERDRAFT_DURATION = 2`、`ai/race.py:39` `_DECOY_RANGE = 7`（和 races.yaml 的 `range: 2` 沒有關聯）。另外 `_PERMILLE = 1000` 重複定義 10 處以上。
   修：誘餌範本與壽命放進 races.yaml 的 decoy 參數；透支回合放進 `core.yaml`；`PERMILLE` 放進 `trpg.shared`。**小**。

8. **吞錯擴散（R11）與為測試略過驗證**
   引擎 `except KeyError` 19 → 25：新增 `stack_gain.py:45-49`、`rules/race.py:52-56`、`race_skills.py:84-88`（種族在載入時已由 `library.py:822` 驗證，這裡是死路徑，卻會掩蓋存檔裡打錯的 race）；`summons.py:113-117` 還在。`skillgen/validate.py:182`「沒有載入縮放規則（測試用的內容庫）」直接回傳空 → 正式內容少了檔案時會靜默不驗證。
   修：引擎直接拋錯，測試改用真實 ID；縮放規則改為內容庫必填，或由 library 明確標示「測試庫」。**小**。

9. **組合器用骨架 ID 寫死分支（沒有改善，21 → 22 處）；跨模組匯入私有函式**
   `skillgen/composer_parts.py:248-270`、`:330`、`:531`、`:581`、`:632-639`（`control`／`aura`／`displace`／`combo`／`trap`／`builder_finisher`），`random_composer.py` 另有 3 處。Phase 4 開放更多骨架時要改程式，違反「內容即資料」。私有匯入：`race_skills.py:50` 匯入 `summons._insert_in_order`、`_order_index`；`preview.py:54` 匯入 `battle._actor`。
   修：核心數量、結構效果、只限有益等設定放進 `skill_skeletons.yaml`；私有函式改成公開 API。**中**（骨架）／**小**（私有匯入）。

10. **`engine/` 依然扁平（R9）**
    頂層 65 個模組，本範圍又加了 `race_skills.py`、`forms.py`、`wind.py`、`stack_gain.py`、`self_costs.py`、`attack_element.py`，`gear_*.py` 還是 7 個。
    修：拆出 `engine/gear/`、`engine/summons/`、`engine/race/`（race_skills＋rules/race＋ai/race 的介面）。**小～中**。

## 整體評價

上次最大的風險（原語分派沒有預設分支、漏做不報錯、變奏漏洞、效果走訪不一致）都已解決；LLM 提議 schema 已經由 YAML 產生，確定性與依賴方向維持良好。不過「新增一個東西要改很多處、漏做不報錯」的問題轉移到了沒有 coverage 檢查的地方：修正規則的 change 種類、預算旋鈕、種族效果、形態加成、骨架分支。其中第 1、2 點會直接卡住 Phase 4 的「開放修正型」和「預算器補數值」。

**建議先排一個整理子階段**：必做 1、2、3（短期修法）、4；5、6、8 可以一起做（多為機械性改動）；7、9、10 可延到 Phase 4 期間。
