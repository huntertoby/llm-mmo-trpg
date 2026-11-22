# Phase E1 報告｜裝備授予技能一般化

> 規格 `docs/phases/PhaseE1計畫.md`；規則以 `docs/design/08-裝備.md` 8.28（#174）為準。基準 main `871ca53df`。

## 1. 盤點現況（改動前）

**裝備怎麼授予技能**

| 途徑 | 在哪 | 怎麼運作 |
|---|---|---|
| 第 9 類「授予動作」`ActionAffix` | `content/equipment.py`、`engine/gear/core.py::gear_skill_ids`／`granted_skills`／`geared_template` | 生效的詞條（`gear.active_affixes("action")`）給的技能 ID 依欄位固定順序**接在範本 `skills` 後面、已有的不重複**；`make_unit` 用加過的範本，所以戰鬥中它就在 `UnitState.skills` 裡，和自己學的分不出來 |
| 第 10 類「授予反應」`ReactionAffix` | `engine/gear/reactions.py`、`lifecycle.make_unit` 的 `gear_reaction_rules` | 不是技能：`extend_trigger`（既有反應多一個事件）、`grant`（只有 `redirect_damage`）、`extra_uses`（多幾次）。這段沒動 |
| 暫時授予 `grant_skill` | `engine/grants.py`、`UnitState.granted_skills` | 技能 ID＋剩餘輪數，不佔欄；已有的技能不重複給（只刷新輪數）；經 `UnitState.all_skills` 生效 |
| 裝備的規則改變、觸發詞條 | `engine/activations.py`、`engine/gear/triggers.py` | 臨時組一個 `skill_gear_<詞條>` 的 `SkillDef`，不進技能列 |

**`gear_checks` 擋了哪幾類**：`_action_problems` 只允許 `kind: active`（被動、反應、修正、姿態都擋），另擋會給「無聲」的技能（BS-1）。所以改前只有主動技能由裝備授予。

**`modifiers.py` 的疑點**：`empty_active_slots` 的 docstring 寫「裝備授予的常駐技能、暫時獲得的技能不算」，但它數的是 `unit.skills`，而裝備授予的主動技已經被併進 `unit.skills`（上表第 1 列），所以**裝備給的主動技會佔掉普攻精通的空格**，和 docstring 不符。暫時獲得的技能確實不算（它在 `granted_skills`）。

**欄位上限**：`battle._check_loadouts` 用的是加裝備之前的 `spawn.template.skills`，roguelite、世界、工坊的欄位檢查也都看玩家自己的招式組，所以裝備給的主動技本來就不算進欄位上限；不符的只有上面的普攻精通空格。

**引擎列舉「可以用的技能」是否都經過 `UnitState.all_skills`**：大多是（`battle._usable_skills`（`legal_actions` 用）、`skills/interpreter`、`modifiers.unit_rules`、AI 的 `gains`／`rune`／`terrain`／`variant`／`scene_objects`、`skill_infusion`）。直接讀 `unit.skills`、因此**看不到暫時獲得的技能**的地方：

- 反應：`reactions._candidate`、`_kin_ward_def`（反應技要在 `unit.skills`）、AI `ai/priority.py`；
- `modifiers.shaped_skill` 的快速路徑（`has_modifier(unit.skills)`）；
- `prep.py`（戰前佈置）、`infusion.py`（灌注）、`ai/self_costs.py`、`ai/utility/skill_estimate.py`、`ai/parts.py`、`grants.grant_skill` 的「已有就不給」；
- `boss_phases.py` 換技能組時整個換掉 `unit.skills`（裝備給的技能也會被換掉；目前沒有帶裝備的頭目）。

裝備授予的技能因為放在 `unit.skills`，上面這些地方都看得到；這段維持這個做法（見第 3 節第 2 項），沒有改這些繞過 `all_skills` 的地方。

## 2. Commit

| 項目 | commit |
|---|---|
| 1 盤點（本報告第 1 節） | `da1aad1c3` |
| 2 四類都能授予、不佔欄、普攻精通空格、LOG_FORMAT `/136` | `df46f2bed` |
| 3 同一招從兩處拿到（複本鍵）、檢視的來源鍵、技能卡路由 | `c84797a09` |
| 4 授予技能的預算窗（`gear_skill_tier`，開進工坊） | `a03397b49` |
| 5 修正技重複：數字遞減後再套上限，非數字各自發動 | `e010827e8` |
| 6 顯示（OpenAPI、前端型別、技能列小圖示、截圖） | `bb887158e` |
| 7 AI 與重播（測試；AI 不必改程式） | `290bb0b43` |
| 修正（docstring 行長、合併後全量檢查抓到的 `/135` 字面值、x10 欄位清單、技能池走訪規則） | `4dd961210`、`35a8809d8` |
| 報告 | `d20a7cb13`（草稿）、最後一個 commit |

## 3. 各項做法

1. **盤點**：見第 1 節。
2. **四類都能授予、不佔欄**
   - `gear_checks._action_problems` 改成允許 `active`／`reaction`／`modifier`／`passive`（`GEAR_GRANTABLE_KINDS`），姿態照舊擋（開發 PM 裁定）；無聲照舊擋。
   - 做法維持「裝備給的技能接在 `UnitState.skills` 後面」（第 1 節：反應、被動觸發、AI 都從 `skills` 找，維持就不必動那些地方），另外新增 `UnitState.gear_skills`（哪幾個鍵是裝備給的；空的不輸出，`clone` 也帶）。
   - **`empty_active_slots` 改前改後**：改前數 `unit.skills` 的主動技，裝備給的主動技會佔掉普攻精通的空格（docstring 說不算，實際算）；改後排除 `gear_skills`。現有內容沒有裝備授予常駐技能，所以結算不變。
   - 欄位上限：`_check_loadouts` 本來就用加裝備前的範本，不用改；測試驗證六個主動欄、三個被動欄、一個反應欄都滿時照樣拿得到裝備的技能。
   - 反應：裝備給的反應技走既有的自動規則（`_auto_reaction_rules`），和格擋、藉機攻擊共用 `reactions_used` 每輪 1 次，順序照反應設定。裝了反應技時格擋預設改成不自動（BAL-15c），裝備給的反應技也一樣——這是現行行為，照開發 PM 裁定維持。
   - `LOG_FORMAT` 升 `/136`（狀態多欄位、重複授予的結算不同），`docs/phases/戰鬥紀錄格式變更.md` 第 2 節加一條，測試裡的 `battle-log/135` 字面值一起改。CLI 快照沒有版號字面值，不用重產。
3. **同一招從兩處拿到**
   - 新模組 `trpg.content.skill_copies`：第二份起的鍵是 `<技能 ID>~2`、`~3`（技能 ID 格式沒有 `~`，不會撞名）。`Ruleset.skill_def` 遇到複本鍵回傳原技能、`id` 換成複本鍵，所以冷卻、`skill_uses`、反應規則、事件、修正規則的每回合次數都照鍵分開；`has_modifier` 看原技能。
   - `gear/core.gear_skill_grants`：每條生效的第 9 類詞條一個鍵（依詞條順序）；自己學過的、或前面已經給過的就配下一個複本鍵。
   - 同一條第 9 類詞條在兩件裝備上：8.21.5.3 的「非數值同 id 只生效 1 條」對它不適用（8.28 第 4 點），`diminish` 對 `category: action` 每條都給 1000‰。原本 G3b 的測試「兩件只給 1 次」改成「兩份」。
   - 反應規則的 `reaction` 欄位格式放寬成 `ID` 或 `ID~數字`（`REACTION_KEY_PATTERN`）。
   - 序列化：`gear_skills` 有預設值、空的不輸出；舊存檔讀得進來（欄位預設空）。舊戰鬥紀錄照 1.1 因為版號不同被拒。
   - 技能卡路由 `/api/skills/{id}` 遇到複本鍵回原技能的卡片（前端照鍵快取）。
4. **授予技能的預算窗**
   - `skill_budget.yaml` 加 `gear_skill_tier: 1`（`BudgetRules.gear_skill_tier`，預設 1；載入時檢查不大於 `skill_limits.tiers`）。開進數值工坊（`tuning_fields.yaml` 的 `kind: budget`，中文名「裝備授予技能的預算階級」，寫了調高、調低的影響）。
   - `skillgen.library_check.gear_grant_violations`：每個被第 9 類詞條引用的技能，把階級換成 `gear_skill_tier` 再跑現有的 `skill_budget`；超出就是 `budget.gear_tier` 違規（`trpg content check` 失敗）。過弱照 `validate_skill` 的既有規則（帶 `gear` 標籤的不算過弱）。技能本身就是那一階時結果和 `validate_skill` 相同，不重複列；已知例外不列。
   - 現有三招 `skill_gear_*` 都是 1 階，`content check` 結果不變。
5. **修正技重複**
   - 遞減比例沿用 `rules/equipment.yaml` 的 `diminishing_permille: [1000, 500, 250]`，沒有新設定。
   - `modifiers.ActiveRule` 多 `weight_permille`（第 n 份的權重）；`_sum_self`、`_sum_for`、`_split_for`、`_sum_unit`、`cooldown_delta`、形狀的 `area_delta` 都改成「數字 × 權重加總、無條件捨去」，然後才進 `damage_permille` 的 `cap_damage_bonus` 等上限。只有一份時權重 1000，算式結果和改前逐位相同。
   - 非數字的部分（加標籤、改元素、穿透、無聲、命中後效果）每份各自生效；命中後效果與每回合次數照複本鍵分開。
   - 觸發型被動（`kind: passive`）照開發 PM 裁定算非數值：兩份各自發動、全額，每輪次數與冷卻分開。
6. **顯示**
   - API：`GearSkillView.skill_id` 改成鍵（複本鍵）、新增 `copy_of`（預設 `None`）、`kind`（預設 `active`）；`ReactionRuleView.gear_source_zh` 對裝備給的反應技寫「欄位：物品名」。OpenAPI 與 `schema.d.ts` 重產。
   - 前端：主動技照舊用「來自裝備・欄位：物品名」標記（兩份各一顆按鈕、各自冷卻）；被動、反應、修正的小圖示加金框，說明卡上方多一條「來自裝備・…」（樣式同「現在不能用」那條，金色實線）；主動技的說明卡也加同一條（按鈕上的字會省略，卡片寫完整）。反應設定面板照舊顯示 `gear_source_zh`。
   - 截圖（實機，暫存的內容複本多兩條只給截圖用的測試詞條：身體給「斷後斬」、項鍊給「嗜血」；手與副手各給「鉤爪」）：
     - `docs/art/shots/e1/e1_gear_skills_1600x900.png`
     - `docs/art/shots/e1/e1_gear_skills_800x600.png`
     兩張都有：技能列兩顆「鉤爪」（手、副手）、反應設定的「斷後斬 來自裝備・身體：斷後皮甲」、滑到「嗜血」小圖示時的說明卡。交美術 PM 驗收。
7. **AI**：AI 從 `legal_actions` 挑，複本鍵也在裡面，照現有評分；反應走反應規則。沒有改 AI 程式，加了測試（兩份都在候選、第一份冷卻時第二份仍在）。

新機制的測試都在 `tests/engine/test_gear_skills_e1.py`（23 項，用測試內容）：四類授予與姿態被擋、欄位全滿仍拿得到、普攻精通空格、同一主動技兩份冷卻分開（含同 id 詞條在兩件裝備）、複本鍵 JSON 來回、反應兩條都列但每輪 1 次、檢視來源、預算窗、遞減 1300／1450／1500 與「先遞減再截上限」、治療修正三份 1262、命中後效果兩份各打一次、AI 候選、同種子跑兩次與重播相同。

## 4. 驗收

基準 `871ca53df`（`git archive` 的 `src`、`content`，執行時確認載入的 `trpg` 來自基準那份）；腳本放在暫存區，沒進 repo。

| 檢查 | 結果 |
|---|---|
| 逐招預算 442 招（`BudgetReport` repr＋`validate_skill` 違規） | 檔案逐位相同，`same=442 different=0` |
| 78 場戰鬥（`compare78.py`，同 a 段那組；去掉 `ruleset_hash`、內嵌規則包，**另外去掉 `format`**（`/135`→`/136`，開發 PM 同意），加文字輸出） | 合併前、合併 main 並修正後（`35a8809d8`）各跑一次，都是 `battles=78 events=26206 different=0`；內嵌規則包 0 差異 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看 `timing`） | `cells=204 different=0` |
| `trpg content check` | 0 |
| `scripts/hardcoded/classify.py --check` | 0（後端 config 28、text 0；前端 config 0；沒歸類 0） |
| ruff、format、mypy、lint-imports | 0 |
| tsc、vitest、build | 0 |
| `uv run python scripts/check.py`（合併 main `e6a5f93c1` 之後） | 第一次 1：7 個測試（4 個測試寫死 `"/135"`、`test_architecture` 不准直接走訪 `library.skills`、x10 欄位清單沒列 `gear_skill_tier` 兩項）→ 修正 `35a8809d8` 後重跑 0（pytest 18287 passed、vitest 4890） |
| `uv run pytest -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（995 passed）；CLI 快照沒變 |
| 前端 build（合併後） | 0 |

## 5. 待 PM 決定

1. **觸發型被動重複算非數值**（開發 PM 已裁定照預設，待轉玩法 PM 確認）：`kind: passive` 的觸發效果（例「擊倒時治療 1d6」）重複時兩份各自發動、全額，每輪次數與冷卻分開；遞減只套在修正技規則的數字上。依據：8.21.5.3 把「觸發」列為非數值。
2. **姿態不能由裝備授予**（開發 PM 已裁定）：8.28 只列四類，`gear_checks` 照舊擋 `kind: stance`（含形態技）。
3. **裝備給的反應技也讓格擋預設不自動**（開發 PM 已裁定，現行行為）：和自己裝反應技相同（BAL-15c）。
4. **同一條第 9 類詞條在兩件裝備上會給兩份**：8.28 第 4 點說「兩件裝備都給」會疊加，所以 `diminish` 對第 9 類不再「同 id 只生效 1 條」。裝備詳情的詞條列不會再把第二條標灰。原本 G3b 的測試「兩件只給 1 次」已改。
5. **複本鍵的順序**：誰拿到原鍵、誰是 `~2`，照詞條順序（詞條 ID，再依欄位固定順序），不照欄位順序。截圖裡副手的鉤爪是第一份、手的是 `~2`。只影響內部鍵，兩份效果相同。
6. **頭目換技能組會清掉裝備給的技能**（`boss_phases` 整個換掉 `skills`，`gear_skills` 留著但不在 `skills` 裡）：目前沒有帶裝備的頭目，沒有處理。
7. **繞過 `all_skills` 的地方沒有改**（第 1 節列表）：裝備技能放在 `skills` 所以不受影響；暫時獲得的反應技、修正技在那些地方仍看不到（改前就是這樣）。
8. **預算窗只擋超出**：照 1 階的窗過弱時，帶 `gear` 標籤的技能不算錯（同現有 `validate_skill`）；沒帶標籤的照一般規則算過弱。8.27 的 60% 名額屬 E6-a，沒做。
9. **按鈕上「來自裝備・欄位：物品名」會省略**（現有樣式）；這段在說明卡上方加了完整的一條（新視覺，交美術 PM 看截圖）。
