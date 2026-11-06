# Phase 4-L5b 報告｜小測試後修正：讓隱藏規則看得見

> 規格：`docs/phases/Phase4計畫.md` 3D 節第 1～6 點（第 7 點範圍外）。實作者撰寫。全部測試用 `MockLLMClient`，沒有呼叫真模型、沒有執行 `-m llm`。

## 1. 做了什麼

| 項目 | 內容 |
|---|---|
| 1 組合規則進 YAML | `PrimitiveDef` 新增 `position`（first／last）、`sole_effect`、`others_affect`（self）、`max_per_skill`、`active_only`，寫進 `content/skill_primitives.yaml`（19 個原語，見第 2 節）。`SkillDef` 驗證器改由新的 `_check_composition` 讀同一份資料（`composition_rules()`，與 `_yaml_ranged_params` 同樣從預設內容資料夾讀一次）；原本 8 個「schema 層級的形狀檢查」改讀 YAML 的 `allowed_shapes`（`_require_shape`）。訊息沿用原文字，現有 content／engine 測試 3444 個全過、`swamp` 種子 60 重播一致。 |
| 1 組合規則進 schema | 新模組 `skillgen/proposal_forms.py`：提議頂層改成以 **`form`（型態）** 區分的 discriminated union（`form` 是第一個欄位）。`standard`＝一般型態（只有沒有組合規則的原語、不含 `unit_then_tile`／`unit_pair`／`object_then_tile`，可帶變奏）；牽涉其他效果的原語各自一個型態（ID＝原語 ID，例：`charge_through` 型態的形狀只有 `ground_tile`、其他效果是「只作用在施放者」的版本，`affects` 只能是 `self`、預設 `self`）；只有形狀限制的原語依 `allowed_shapes` 合併（`on_single`、`on_ground_tile`…）。`active_only` 的型態 `kind` 只有 `active`。手寫技能 → 提議時由 `form_of_effects` 判斷型態。選擇 schema（而不是題目層）處理，因為 `core_primitive` 是 4-L6 的事，題目層做會讓自由提議用不到這些原語。 |
| 1 schema 大小 | 型態會重複頂層欄位，為了讓題目仍放得進 `token_budget`：一般原語、只作用在施放者的版本、條件、觸發、骨架列舉、一般型態的形狀做成具名型別（`$defs` 只出現一次）；型態的效果 union 用自訂標籤（`Discriminator`）引用共用的 `GeneralEffect`；輸出的 schema 去掉只影響說明的 `title`、`discriminator` 對照表、`default`（`ProposalModels.json_schema` 的 `_compact`；驗證一律用 pydantic 模型）。 |
| 2 稀有度篩列舉 | `build_proposal_models(..., rarity=)`、`ProposalSubset.rarity`：`apply_status` 的 `status` 只列該稀有度可用的狀態（`rarity_statuses`；與 `rarity.status` 驗證共用 `validate.RARITY_STATUS_PRIMITIVES`）。非主動技能的題目在 `select_subset` 就去掉 `active_only` 的原語。 |
| 3 錯誤 path | 驗證器的組合規則與形狀檢查改丟 `SkillRuleError(ValueError)`，帶 `path`（`kind`、`effects`、`effects[i]`、`effects[i].affects`、`shape.type`、`category`）；`stage: skill` 的錯誤依序取：例外帶的 path → 訊息中的 `effects[i]` → 訊息講形狀時 `shape` → 空白。頂層缺 `form` 時 path 為 `form`、`allowed` 列出可用型態。 |
| 4 先修可修的 | `evaluate_with_repair`：錯誤中只要有可修代碼就先修（一次），**回給 LLM 的是修補後剩下的錯誤**；`repaired`＝修補前有、修補後沒有的代碼。可修清單見第 3 節（`skeleton.secondary_share` 加入；`exclusion.*` 中「補冷卻即可」的由 `skill_exclusions.yaml` 推導）。 |
| 5 骨架資訊進 available | `available` 新增 `forms`（`[{id, hint}]`，型態說明：形狀、唯一／第一／最後、每技能最多一個、其他效果只作用在施放者、只能主動、不能帶變奏），每個骨架加 `core`（`primitives`＋`note`：至少一個核心、最低占比、對象限制、有益限制）、`secondary`（`primitives` 或「不限」＋`note`：最多幾個、只能有害、個別占比上限）、`shapes`；清單只列子集內的項目。系統指令加三行說明 `form` 與骨架結構，`PROMPT_VERSION` 升為 `skill-proposal/2`、快照更新。 |

## 2. 組合規則盤點

### 2.1 搬進 YAML（`skill_primitives.yaml`，驗證器與提議模型共用）

| 欄位 | 原語 |
|---|---|
| `active_only: true` | dash、charge_through、shadowstep、leap、swap、teleport_target、swap_any、copy_skill、hurl_object、revive、delayed_damage、summon、zone、rule_change、gamble、grant_skill、inscribe、detonate_runes、sacrifice_summon |
| `position: first` | dash、charge_through、shadowstep |
| `position: last` | gamble |
| `sole_effect: true` | teleport_target、swap_any、copy_skill、zone、rule_change |
| `others_affect: self` | charge_through、summon、revive |
| `max_per_skill: 1` | hurl_object、revive、delayed_damage、summon、gamble、grant_skill |
| `allowed_shapes`（原本就在 YAML） | 驗證器原本寫死的 charge_through、hurl_object、revive、sacrifice_summon、rule_change、copy_skill、teleport_target、swap_any 改讀 YAML；其餘原語照舊由跨檔案驗證（`skill_problems`）檢查。提議模型對全部原語套用。 |

### 2.2 留在程式（理由）

| 規則 | 理由 |
|---|---|
| 改變自身位置的原語最多一個（`SELF_MOVES`） | 跨原語的群組規則；已移到 `_check_composition` 統一處理，群組名單仍是常數。提議模型中這些原語各在不同型態，同一招本來就只會有一個。 |
| 形狀要求原語：`object_then_tile` 恰好一個 hurl_object、`unit_then_tile`／`unit_pair` 要有對應位移他人（或 `landing: choose` 的 shadowstep） | 形狀這一側的規則，而且依參數（`landing`）而定；整理成常數 `SHAPE_REQUIRED_PRIMITIVES` 供提議模型使用，並有測試確認與 YAML `allowed_shapes` 一致。 |
| shadowstep `landing` → 形狀、zone `anchor: moving/caster` → 形狀 | 依參數值決定形狀，不是原語層級的資料。 |
| delayed_damage 只能用在法術技 | 類別規則（`category`），不在 3D 第 1 點的三類內。 |
| rule_change 只能傳說 | 稀有度規則（YAML 的 `min_rarity` 已是 legendary，提議子集本來就篩掉）。 |
| summon 的 count／power、revive 的 hp_permille、grant_skill 的欄位、inscribe 的 element／tag 二擇一 | 參數層級的必填與互斥，不是組合規則。 |
| 陷阱、反應、姿態、修正、複合技能、pierce、賭注分支、on_kill、consume_status 的 then | 提議模型不開放或屬於巢狀內容。 |

## 3. 可由引擎修的錯誤代碼

| 代碼 | 來源 | 修法 |
|---|---|---|
| `budget.over`、`budget.weak` | `proposal_budget.REPAIRABLE_CODES` | 換亂數串流重調旋鈕（核心優先與全部旋鈕交替）。 |
| `skeleton.core_share`、`skeleton.secondary_share`（新增） | 同上 | 先只調核心旋鈕（附帶停在最小值），與全部旋鈕交替。 |
| `exclusion.no_cooldown_big_area` | `cooldown_repairs(library)`，由 `skill_exclusions.yaml` 推導（`when: {has_cooldown: false}`） | 補冷卻 1。 |
| `exclusion.stun_single_long_cooldown`（新增） | 同上（`require.min_cooldown: 4`） | 補冷卻到 4；形狀不是 single 的部分補不了，修補後照常回報。 |

之後在 `skill_exclusions.yaml` 新增「沒有冷卻時才適用」或「要求最低冷卻」的規則，會自動列入，不必改程式。

## 4. `trpg llm propose --mock -n 10`（seed 0）

```
  1. common／strike／prone｜llm｜嘗試 1｜通過｜0.00 秒｜火焰箭
  2. rare／不限骨架／collision｜llm｜嘗試 1｜通過｜0.00 秒｜汲命術
  3. epic／不限骨架／marked｜composer｜嘗試 3｜literal_error、extra_forbidden（×3）｜暗影・光環 #1430544302
  4. common／不限骨架／high_ground｜llm｜嘗試 1｜通過｜0.00 秒｜火焰箭
  5. rare／area／無關鍵字｜llm｜嘗試 1｜通過｜0.00 秒｜聖水
  6. epic／不限骨架／無關鍵字｜composer｜嘗試 3｜cap.rule_rewrite_cost、budget.weak（×3）｜暗影・控場 #3988197716
  7. common／strike／無關鍵字｜llm｜嘗試 1｜通過｜0.00 秒｜聚雷
  8. rare／不限骨架／collision｜composer｜嘗試 3｜union_tag_invalid（×3）｜風・打擊 #128837899
  9. epic／area／無關鍵字｜composer｜嘗試 3｜missing×9（×3，沒有對應手寫技能，Mock 回 {}）｜物理・範圍 #1880156148
 10. common／area／無關鍵字｜llm｜嘗試 1｜通過｜0.00 秒｜旋風斬
```

一次通過 60.0%（6）、平均嘗試 1.80、退回 40.0%（4，提醒）、來源 llm 6／composer 4、引擎修補無。與 4-L5 相同：Mock 每次回同一份手寫技能的提議（`proposal_from_skill` 已帶 `form`），失敗的題目是 Mock 挑到的手寫技能本身不合題目（骨架、稀有度或有提議不開放的欄位），不代表真模型的通過率。CLI 快照 `tests/cli/snapshots/llm_propose_mock.txt` 沒有變。#9 的 missing 由 8 變 9（多了必填的 `form`；該題子集只有一個型態，根就是一般型態的模型）。

**大小**（4-L4 的矩陣：4 稀有度 × 12 種骨架（含不指定）× 3 組關鍵字）：可行 138 組（與 4-L4 相同）、估算最大 25,044、平均 11,481（4-L4：最大 24,999、平均 16,540；平均下降是因為 schema 去掉註記關鍵字）；每題型態數最多 16、平均 4.7。不指定骨架的 rare／epic／legendary 題目，核心原語本身就要約 22k，補足只剩約 2 個條件（見待決 #6）。

## 5. 測試與檢查

`tests/skillgen`、`tests/llm`、`tests/content`、`tests/engine`、`tests/cli/test_llm_propose_cli.py`、`tests/cli/test_cli.py`、`tests/test_architecture.py` 共 4426 過；`ruff check`、`ruff format --check`、`mypy`（src＋tests/skillgen＋tests/llm）、`lint-imports`（7 契約）全過；`swamp` 種子 60 `--log-json` ＋ `replay` 一致。手寫技能結構往返 **163／173**（可表達的 173 個中，與 4-L5 相同；失敗的只有 `cost` 等提議不開放的欄位）。未跑 `scripts/check.py`、未執行 `-m llm`。新增／修改的測試：

- `tests/skillgen/test_proposal_forms.py`（新，52）：`charge_through` 型態只有 `ground_tile`；一般型態沒有 `charge_through`；`charge_through` 型態的其他效果 `affects` 只能 `self`（省略即 self、可通過）、不開放傷害；位置錯誤在 `stage: skill` 帶 `effects[1]`；唯一效果型態只有一個效果；每個特殊原語都有型態、一般型態不含它們與要求原語的形狀；`SHAPE_REQUIRED_PRIMITIVES` 與 YAML 一致；手寫技能的 `form` 都存在；缺 `form` 時列出型態；schema 沒有 `title`／`discriminator`／`default`；**YAML 的每一條組合規則都被驗證器擋下且帶 path**（表格測試，37 組）；普通稀有度的 `apply_status` 列舉不含高稀有度狀態、提議高稀有度狀態得 `literal_error`；非主動題目不含 `active_only` 原語；`available` 的型態與骨架結構。
- `tests/skillgen/test_proposal_budget.py`：硬控非單體時引擎先補冷卻到 4、形狀錯誤照常回報；單體硬控由引擎補冷卻；**混合錯誤（骨架不合＋沒有冷卻的大範圍）時引擎仍先修冷卻、只回報不可修的**；可修代碼表與 `cooldown_repairs`。
- `tests/llm/test_propose.py`（Mock）：混合錯誤 → 第 1 次紀錄的 `repaired` 有冷卻、回饋的 `<errors>` 不含它、第 2 次通過；`charge_through` 型態出現在 prompt 的 `forms`、schema 形狀只有 `ground_tile`、`skill_bull_rush` 的提議一次通過；普通題目的狀態列舉不含稀有以上的狀態。
- 調整既有測試以配合頂層型態：提議 JSON 加 `"form": "standard"`、讀一般型態用 `tests/skillgen/helpers.py` 的 `standard_form`／`union_tags`、`available` 快照加 `forms` 與骨架欄位、prompt 快照新增 `skill-proposal/2`。

## 6. `# noqa` 清單

沒有新增複雜度類（C901／PLR0911／0912／0915）。新增 5 個 `# noqa: UP007`（`proposal.py`：具名型別 `TypeAliasType` 與 `None`、自訂標籤的 union 必須用 `Union[...]` 寫法，與檔內既有的同類 noqa 相同）。

## 7. 待 PM 決定

1. **頂層 schema 變成 `oneOf`（沒有頂層 `properties`）**：pydantic 的 discriminated union 產生根層級 `oneOf`；4.5 實測過巢狀 `$ref`／`oneOf`，但沒測過「根就是 `oneOf`」。PM 跑真模型時請確認 vLLM strict `response_format` 接受（不接受時 client 會退回 `guided_json`）；若仍不行，可改成在外面包一層物件。
2. **schema 去掉 `title`、`discriminator`、`default`，型態的說明只放在 `available.forms`**（4.5：schema 不進 prompt，模型看不到 schema 的說明）；原語、形狀、條件、觸發的 `llm_hint` 說明仍留在 schema。若之後換成會把 schema 給模型看的服務，可再把型態說明放回 `form` 欄位。
3. **只有形狀限制的原語合併成 `on_<形狀>` 型態**（例：`on_single`＝swap、topple、delayed_damage、sacrifice_summon），以控制型態數；ID 依 YAML 的 `allowed_shapes` 決定，加新原語時可能新增或合併型態。
4. **「其他效果只作用在施放者」的型態只開放有益原語與 `apply_status`**（`SELF_STATUS_PRIMITIVES`）：對自己傷害、推拉、`add_stack` 等有害原語不開放（驗證器本身允許）。手寫技能沒有這類組合，往返數不受影響。
5. **位置（第一個／最後一個）與每技能數量上限仍由驗證器檢查**（錯誤帶 path、型態說明有寫），沒有放進 schema（需要 `prefixItems`，約束解碼的支援度未知）。也可以改成轉換時自動把 dash／charge_through／shadowstep 移到第一個、gamble 移到最後（它們本來就固定先／後結算）。
6. **token 預算**：型態讓 schema 變大，不指定骨架的 rare／epic／legendary 題目補足後只剩約 2 個條件（核心原語永不砍，4-L4 決定 #2）。4.5 實測 schema 不佔 prompt token；建議 4-L9 決定時一併考慮把 schema 移出估算（4-L4 待決 #3、#5）。
7. **只有一般型態可以帶變奏**：特殊型態的變奏可能加入違反組合規則的效果，先不開放；往返數不變（163）。
8. **非主動技能的題目去掉 `active_only` 原語**（例：被動、姿態不會看到 inscribe、detonate_runes）。
9. **型態填錯時只回報型態錯誤**：discriminated union 先依 `form` 選分支，其他欄位的錯誤要等型態改對後才看得到（`allowed` 會列出可用型態）。
10. **稀有度篩狀態只套用在 `apply_status`**（與 `rarity.status` 相同），但巢狀位置（then、on_kill、zone 的 effects）的 `apply_status` 也一起篩——比驗證器嚴格一點。
11. **`stage: skill` 的錯誤代碼仍是 `value_error`**（只補 path）；若要統計各組合規則，可再給 `SkillRuleError` 加代碼（例：`composition.position`），會改變 `ProposalStats` 的代碼分布。
12. **工坊退回（`proposal_fallback._finish`）仍是「錯誤全部可修才修」**：只把 `is_repairable` 改成讀 YAML 的版本，行為與 4-L5 相同。
13. **組合規則與 `_yaml_ranged_params` 一樣從預設內容資料夾讀**：用別的內容資料夾建 `SkillDef` 時，驗證器仍讀預設資料夾的 YAML（既有限制，沒有擴大）。
14. 本 worktree 原本沒有 `.venv`，執行了 `uv sync --frozen` 建立本 worktree 自己的環境（沒有動主資料夾的環境）。
