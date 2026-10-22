# Phase 4 前置｜LLM 技能提議 schema 設計（Phase 3E-2g）

> 狀態：設計＋最小原型（2026-10-23）。原型在 `src/trpg/skillgen/proposal.py`，測試在 `tests/skillgen/test_proposal.py`。
> **沒有改動**現有技能 schema（`SkillDef`／`EffectSpec`）與引擎行為；`LOG_FORMAT` 不變。
> 來源：`docs/phases/Phase3審查-Python.md` 第 4 點（R4 設計部分）、`docs/phases/Phase3E計畫.md` 3.1 的 3E-2g 列、`docs/design/06-技能.md` 6.7、6.9、6.27.4。

## 1. 目標與非目標

**目標**

- 給 LLM 一份 **小、可驗證、錯誤可定位** 的輸出格式（「提議」），取代直接寫 `SkillDef`。
- 提議模型 **由內容資料自動產生**（`skill_primitives.yaml` 的 `params`、`skill_shapes.yaml`、`skill_conditions.yaml`、`skill_triggers.yaml`、狀態／物件／層數／召喚物等 ID 表）；新增原語只改 YAML（加上 3E-2b 清單的引擎端各處），提議模型自動多一支。
- 提議 → `SkillDef` 之後一律走 **現有** 的 schema 檢查、跨檔案驗證（`skill_reference_problems`）與 `validate_skill`（骨架、上限、互斥、稀有度、預算、關鍵字）。LLM 的輸出不會繞過任何一道檢查（守則 3；3E-2a 驗收 #1「LLM 提議流程一定走驗證器」）。
- 每道檢查的失敗都轉成同一種 **結構化錯誤**，附給 LLM 重試。

**非目標（本段）**

- 不接真實模型、不寫 `LLMClient`／prompt、不改升級流程；不拆 `skills.py`（R4 拆檔在 3E-3）。
- 不讓 LLM 產生任何「規則」：數值範圍、預算、稀有度、ID 一律由內容資料與引擎決定。

## 2. LLM 在流程中的位置

```
候選產生器（6.27.4：加深／橋接／新方向的關鍵字題目）
  │  呼叫端決定：tier、rarity、origin、可用原語子集、題目關鍵字
  ▼
LLM（LLMClient；玩家文字在 <player_input>）──► 提議 JSON
  ▼
① proposal：pydantic 驗證提議模型（每原語一支的 discriminated union）
  ▼
② skill：提議 → SkillDef（補 id／tier／rarity／rank／provenance），SkillDef 自己的 model_validator
  ▼
③ rules：validate_skill（含 skill_reference_problems、骨架、上限、互斥、稀有度、預算比例、關鍵字）
  ▼          （Phase 4 後段：④ 模擬門檻，6.8）
通過 → 候選；不通過 → 結構化錯誤 → 回到 LLM 重試（上限見 5 節）→ 用盡則退回
```

- 原型的 `evaluate_proposal(raw, models, library, ctx)` 依序做 ①②③，**任一階段失敗就停**，回傳該階段的全部錯誤（同一階段的錯誤一次全給，讓 LLM 一次修完）。
- **確定性**：LLM 呼叫在引擎外（`skillgen`／`roguelite` 層）。生成結果（`SkillDef` 本身，不是 prompt）必須寫進存檔／run 紀錄，重播時直接讀取，不重新呼叫 LLM；ID 由內容雜湊（`skill_llm_` ＋ SHA-256 前 10 碼），同一份提議永遠得到同一個 ID。
- 候選產生器目前的來源順序是 `pool`／`composer`（`skillgen/candidates.py`）；Phase 4 加一個 `llm` 來源放在最前，失敗時落回原本兩者（見 5.3）。

## 3. 提議模型

### 3.1 形狀

頂層 `SkillProposal`（`extra="forbid"`）：

| 欄位 | 來源 |
|---|---|
| `name_zh`、`description_zh`、`concept`、`cast_flavor` | LLM（`concept`／`cast_flavor` 轉成 `narrative`） |
| `kind` | LLM；原型開放 `active`、`passive`、`stance` |
| `skeleton` | LLM；`content/skeletons/` 的 ID，去掉需要額外欄位的 `reaction`、`modifier`、`trap` |
| `category`、`weapon_req`、`scaling_attr` | LLM；型別沿用 `SkillDef` 的 `Literal` |
| `ap_cost`（1–3）、`cost.mana`、`cost.cooldown`（1–6） | LLM（見 3.3「旋鈕」） |
| `shape` | union，以 `type` 區分，每支只有該形狀的參數與 YAML 的 `min`／`max`（`allow_weapon` 的可寫 `"weapon"`） |
| `effects`（1–4） | union，以 `type` 區分，**每個原語一支** |
| `condition` | union，以 `type` 區分，參數來自 `skill_conditions.yaml` |
| `trigger` | union，以 `event` 區分；只有 `has_other` 的時機才有 `target`、`max_distance` |
| `tags` | LLM（ID 格式，最多 8 個） |
| `variants`（0–2） | 變奏；`add_effect`／`replace_effect` 用 **另一個** 效果 union（見 4.2） |

每個原語分支 `Effect_<id>` 的欄位 ＝ `type`（`Literal[id]`）＋ `affects`（依 `acts_on`／`forbid_affects` 縮小的 `Literal`）＋ `condition` ＋ 該原語 `params` 的每個參數：

| `params` 的 type | 提議中的型別 |
|---|---|
| `int` | `int`，`ge`／`le` 取 YAML 的 `min`／`max`（3E-2f 已是唯一來源） |
| `dice` | 字串，`pattern` 為 `NdM` |
| `status`／`object`／`stack`／`summon`／`rule_change`／`summon_trait`／`infusion` | `Literal[內容庫中現有的 ID]`（JSON Schema 的 `enum` ＝ 可用值） |
| `element`／`surface` | 引擎的 `StrEnum` |
| `effects`（`then`、`win`／`lose`、`on_kill`、zone 的 `effects`） | 巢狀效果 list（1–2 個），只開放該位置允許、且本身是原語的類型；巢狀位置的效果不能再巢狀 |
| 其他（`which`、`scale`、`scaling`、`anchor`、`landing`…） | 沿用 `EffectSpec` 欄位的型別（`Literal` 或子模型） |
| `required: true` | 必填；但 `damage.dice`、`inscribe.element` 依情況才必填（照抄 `_filled_by_category`），提議中可省略、缺了由 ③ 報錯 |

`description_zh`（參數）與 `player_description`（原語）進 JSON Schema 的 `description`，LLM 看得到。

### 3.2 為何比扁平 `EffectSpec` 適合 LLM

1. **欄位少**：`EffectSpec` 約 40 個選填欄位，每個效果都「看得到」全部；分支後一支平均 2–4 個參數，`heal` 只有 `dice`。LLM 不會在 `heal` 上填 `radius`，填了也會被 `extra="forbid"` 擋下。
2. **錯誤可定位**：discriminated union 依 `type` 只驗證那一支，錯誤路徑精確到 `effects[1].radius`，而不是 pydantic 對 40 欄位扁平模型的一長串「某欄位對某類型不合法」；未知類型直接回 `union_tag_invalid` 並列出可用類型。
3. **可用值就在 schema 裡**：狀態、物件、元素、骨架、形狀都是 `enum`，可以直接當 tool input schema／structured output 給模型，模型層面就不太會產生不存在的 ID（守則：LLM 只能使用存在的原語 ID，6.7 第 2 步）。
4. **禁止的組合在 schema 層就不存在**：例如變奏的效果 union 根本沒有 `zone`（4.2），比事後報錯便宜。
5. **同源**：模型由 YAML 產生，不會與引擎檢查的範圍漂移；新增原語不必改提議程式。

### 3.3 LLM 不填的欄位

| 欄位 | 由誰決定 |
|---|---|
| `id` | 引擎：內容雜湊（`skill_llm_…`） |
| `tier`、`rarity`、`rank` | 呼叫端（升級進度、候選產生器）：`ProposalContext` |
| `provenance` | 呼叫端（`origin`，例如 `level_up`）；`created_by: llm` |
| `schema_version` | 固定 1 |
| `mastery`、`secondary_scaling_attr`、`crit_range`、`damage_permille`、`pierce`、`include_caster`、`exclusive_group` | 原型不開放（多數是稀有度或特殊機制，Phase 4 視需要再開） |
| `reaction`、`trap`、`modifiers`、`activation`、`followup` | 原型不開放（各需要一組子模型；見 7 節拆段） |
| `cost.hp_percent`／`stacks`／`source`／`self_status`／`on_miss`／`uses_per_battle` | 原型不開放（代價類的預算折抵規則複雜，先由引擎決定） |

**數值（旋鈕）**：骰子、倍率、持續、距離、射程、法力、冷卻。原型允許 LLM 填（在 YAML 範圍內），以證明提議格式能完整表達現有技能。**Phase 4 建議**：prompt 要求 LLM 只給「強度意圖」或省略旋鈕，由預算器補數值——沿用隨機組合器的 `composer_tuning.tune`（從最弱開始往上調到目標預算比例），LLM 給的值只當起點。這樣 LLM 永遠不決定強度（6.26 誓約也採同樣原則：數值由引擎查表）。

### 3.4 規模

- 現有 48 個原語、13 種形狀、15 種條件；完整 JSON Schema 約 15.8 萬字元（約 102 個 `$defs`），其中效果分支約 11 萬。
- 太大，不適合每次整份送出。`build_proposal_models(library, primitives=[…])` 可以只開放子集；6 個原語的子集約 5.1 萬字元。**Phase 4 建議**：呼叫端依稀有度（`min_rarity`）、骨架（`content/skeletons/` 的核心／附帶效果）、題目關鍵字先篩原語，再產生 schema；參數說明改用給玩家／LLM 的短句（現在 `description_zh` 夾雜階段編號與欄位名，見 8 節問題 4）。

## 4. 轉換：提議 → `SkillDef`

### 4.1 對應規則（`to_skill_def`）

1. `proposal.model_dump(mode="json", exclude_none=True)`：提議的欄位名與 `SkillDef`／`EffectSpec` 相同，效果、形狀、條件、觸發、變奏直接搬過去（union 標籤就是原本的 `type`／`event`）。
2. `concept`、`cast_flavor` → `narrative`。
3. 補 `tier`、`rarity`、`rank`（`ProposalContext`）、`provenance = {origin, created_by: "llm"}`。
4. `id` ＝ `skill_llm_` ＋ 以上內容的 SHA-256 前 10 碼。
5. `SkillDef.model_validate(...)`：`SkillDef`／`EffectSpec` 自己的 19 個 `model_validator` 照常執行（②）。

反向的 `proposal_from_skill(skill)` 把手寫技能轉成提議 JSON，用途：往返測試、**few-shot 範例**（Phase 4 prompt 可以從內容庫挑同骨架的手寫技能當範例，格式保證和 schema 一致）。

**原型實測**（`test_every_expressible_builtin_skill_round_trips`）：217 個手寫技能中，163 個能以提議格式表達並轉回 **除 ID 與來源外完全相同** 的 `SkillDef`；44 個用到原型不開放的頂層欄位（修正規則 16、反應 8、複合技能 8、啟動 4、陷阱 2、專精 2、雙屬性 1…）；10 個用到原型不開放的巢狀內容（`on_kill` 的 `refund_ap`／`refund_cooldown`、賭注的 `damage_multiplier`／`self_damage_of_hit`、`cost.source` 等），在 ① 就得到可定位的錯誤。

### 4.2 無法表達或被禁止的組合

| 組合 | 處理 | 層級 |
|---|---|---|
| 變奏的 `add_effect`／`replace_effect` 用 `lookup_by_skill_id` 原語（`zone`、`delayed_damage`、`copy_skill`，3E-2a） | 變奏用的效果 union 不含這些原語，LLM 填了得到 `union_tag_invalid` 與可用清單 | ① |
| 帶變奏的技能，主效果含 `lookup_by_skill_id` 原語 | 現有 `_variant_lookup_problems` 報錯 | ③ |
| 巢狀效果用非原語類型（`refund_ap`、`refund_cooldown`、`damage_multiplier`、`self_damage_of_hit`） | 原型不開放；Phase 4 要開放時把它們登錄成「只能巢狀」的原語（YAML 加旗標），提議模型就會自動多一支 | ① |
| 巢狀位置再巢狀（例如 `then` 裡的 `damage` 帶 `on_kill`） | 巢狀位置用去掉巢狀參數的模型 | ① |
| `affects` 違反 `acts_on`／`forbid_affects`（例如淨化對敵人） | `affects` 的 `Literal` 已縮小 | ① |
| 呼叫端欄位（`rarity`、`id`…） | 提議模型沒有這些欄位，`extra_forbidden` | ① |
| 依骨架／稀有度／預算的規則 | `validate_skill` | ③ |
| 篩選子集後，必填的巢狀參數沒有可用原語（例如只開放 `zone`、`push`） | 該原語不開放，記在 `excluded_primitives` | 產生模型時 |

## 5. 錯誤回饋

### 5.1 格式

每條錯誤（`ProposalError`）：

```json
{"stage": "proposal", "path": "effects[2].status", "code": "literal_error",
 "message": "不是可用的值", "allowed": ["bleeding", "burning", "..."]}
```

- `stage`：`proposal`／`skill`／`rules`，讓 LLM 知道是格式錯、組合錯還是強度錯。
- `path`：LLM 送來的 JSON 的路徑（union 標籤已去掉）；`rules` 階段從訊息開頭的 `欄位：` 取出，沒有就空字串（技能層級）。
- `code`：**英文穩定代碼**（pydantic 錯誤型別或驗證器規則代碼，例如 `budget.over`、`skeleton.core`）——給程式統計通過率與重試原因用，Phase 4 驗收要的「重試次數報表」直接依它分類。
- `message`：**繁體中文**。
- `allowed`：可用值（列舉型錯誤才有）。

重試時附給 LLM 的是 `feedback_payload(errors, attempt, max_attempts)`（JSON），放在資料區、不是指令區。

### 5.2 為何訊息用中文

- 引擎的驗證器（`skill_problems`、`validate_skill`、`SkillDef` 的驗證器）訊息全部是中文且已經寫得很具體；改用英文要多一層翻譯並維護兩份，容易漂移。
- LLM 這次的輸出（名稱、敘事）本來就是繁體中文，prompt 主體也會是中文；中英混雜反而增加歧義。
- 機器要判斷的部分已經由英文 `code`、`path`、`allowed` 承擔；`message` 只是給模型理解原因。
- pydantic 內建的英文訊息在原型中翻成中文（常見的 11 種），其餘保留原文。

### 5.3 重試與退回

- **每個候選最多 3 次 LLM 呼叫**（1 次 ＋ 2 次重試；建議值，可設定）。每次重試帶上一份提議與錯誤；同一階段的錯誤一次全給。
- `rules` 階段只剩預算比例錯誤（`budget.*`）時 **不必回 LLM**：交給預算器（`tune`）調旋鈕，調得到就通過——省一次呼叫，也符合「數值由引擎決定」。
- 用盡後退回（依序）：① 隨機組合器帶同一組題目關鍵字（`compose_random_skill(..., keyword=…)`，即現有 `from_composer`）② 技能池（`from_pool`）③ 工坊選項推導（`skillgen/options.py` 依骨架列出合法選項、取第一組可行值；最後保底）。名稱與敘事可以再單獨請 LLM 寫（只寫文字，失敗就用組合式名稱）。
- 退回與重試次數寫進 run 紀錄，供 Phase 4 驗收的報表（通過率、重試次數）。

## 6. 安全

- 玩家的任何文字（自我介紹、誓言、build 命名、戰術指令）一律包在 `<player_input>…</player_input>`，放在資料區，**絕不拼接進指令區**（守則 7）。上一次的提議與錯誤回饋也放資料區。
- LLM **沒有任何工具**能改數值、產生物品或資源：它唯一的輸出是提議 JSON，而提議只能選內容資料中已存在的原語、形狀、狀態與 ID；數值受 YAML 範圍限制，最終強度由預算器與驗證器決定（守則 3）。
- 提議不含 `id`、`rarity`、`tier`、`provenance`：LLM 無法替自己升稀有度或偽造來源。
- 生成的技能仍要通過 Phase 4 的模擬門檻（6.8）才會出現在候選中。
- 呼叫一律經 `LLMClient`，測試用 `MockLLMClient`（守則 6）：Mock 回傳固定的提議 JSON（例如 `proposal_from_skill` 產生的），測試不需網路與金鑰。

## 7. 對 Phase 4 規格的建議拆段（每段約 30 分鐘、一套規則＋測試）

| 段 | 內容 | 測試 |
|---|---|---|
| 4-L1 | `trpg.llm`：`LLMClient` 介面、`MockLLMClient`（依序回傳預設回應、記錄收到的 prompt）、模型 ID 設定檔 | Mock 行為；測試不需網路 |
| 4-L2 | 版本化 prompt（`content/` 或 `src/trpg/llm/prompts/`）：系統指令、資料區、`<player_input>` 包裝與跳脫 | 玩家文字含 `</player_input>`、指令字樣時仍只在資料區 |
| 4-L3 | 把原型的提議模型正式化：`required_when` 搬進 YAML（取代 `CONDITIONALLY_REQUIRED`）、觸發參數搬進 `skill_triggers.yaml` 的 `params`、參數加給 LLM 的短說明 | 模型由 YAML 產生、與 `_filled_by_category`／`TriggerSpec` 一致的表格測試 |
| 4-L4 | schema 子集：依稀有度、骨架、題目關鍵字篩原語、形狀、條件 | schema 大小上限；篩掉的原語提議會得到 `union_tag_invalid` |
| 4-L5 | 重試迴圈＋退回：`propose_skill(client, request) -> (SkillDef, source, attempts)`，3 次上限，預算錯誤交給 `tune` | Mock 依序回傳「壞 → 壞 → 好」「壞 ×3 → 組合器」 |
| 4-L6 | 接進候選產生器：`llm` 來源、結果寫進 run 紀錄、重播不呼叫 LLM | 存檔重播一致；Mock 失敗時候選仍有 3 個 |
| 4-L7 | 名稱與敘事（只寫文字；長度、禁字、失敗時組合式名稱） | Mock 輸出過長／空字串 |
| 4-L8 | 開放更多結構：`followup`（複合技能）、`reaction`、非原語巢狀效果（登錄成只能巢狀的原語）、代價類欄位 | 往返覆蓋率從 163／217 提高 |
| 4-L9 | 真實模型評估腳本：50 組升級候選的通過率、各 `code` 的重試次數、主題一致性抽樣（Phase 4 驗收） | 只在 PM 指定時跑（需要金鑰） |

L1–L2 可與 L3–L4 平行；L5 需要 L1、L3；L6 需要 L5。

## 8. 待使用者決定的問題

1. **世界觀（待決定事項 #5）**：決定 prompt 的語氣、名詞與敘事風格；也決定元素／狀態的命名是否需要在 prompt 中重新包裝。Phase 4 開始前必須定。
2. **模型選擇與成本**：技能提議用哪個模型（品質 vs 延遲 vs 成本）；名稱與敘事是否用較小的模型分開呼叫。完整 schema 約 15.8 萬字元，子集化後仍有數萬字元，影響每次呼叫的成本。
3. **LLM 能不能決定數值**：建議「LLM 只選結構，數值一律由預算器補」（3.3）；若希望 LLM 能做「低傷高控」這類取捨，可以讓它給強度意圖（例如核心／附帶的占比），仍由預算器換算。
4. **原語說明的對象**：現在 `description_zh` 是給開發者看的（含階段編號、欄位名）；要不要在 YAML 加一個給 LLM 的短說明欄位（或沿用 `player_description` 加參數說明）。
5. **重試上限與退回順序**：建議每個候選 3 次、退回順序「組合器 → 技能池 → 工坊選項」；以及生成失敗率多高時要提醒 PM（例如單輪 >30% 退回）。

## 附錄：原型 API

| 名稱 | 說明 |
|---|---|
| `build_proposal_models(library, *, primitives=None)` | 由內容庫產生 `ProposalModels`（`skill` 模型、`json_schema()`、開放的原語、變奏可用的原語、被排除的原語與原因） |
| `evaluate_proposal(raw, models, library, ctx)` | 提議（JSON 字串或 dict）→ `ProposalResult(skill, errors)`，依 ①②③ 檢查 |
| `to_skill_def(proposal, ctx)` | 已驗證的提議 → `SkillDef` |
| `proposal_from_skill(skill)` | 手寫技能 → 提議 JSON（few-shot、測試） |
| `ProposalError`、`feedback_payload(errors, attempt, max_attempts)` | 結構化錯誤與重試用的 JSON |
| `ProposalContext(tier, rarity, rank=1, origin="level_up")` | 呼叫端決定的欄位 |
