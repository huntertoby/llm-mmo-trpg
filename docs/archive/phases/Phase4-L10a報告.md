# Phase 4-L10a 報告：schema、提示、閃現模板列舉修正

依 `Phase4計畫.md` 的 4-L10 節（4-L10a）與 `Phase4-L9報告.md` 第 7 節。只用 `MockLLMClient`，**沒有連真模型**（重跑 4-L9 評估由 PM 安排）。沒有改補值器、修補邏輯、`skill_primitives.yaml` 的 `llm_hint` 與 `skill_triggers.yaml`（4-L10b 的範圍）；驗證器（`SkillDef`、`validate.py`）只動錯誤路徑，規則沒改。

## 1. Commit

| Commit | 內容 |
|---|---|
| `74b51238` | A1 巢狀效果錯誤帶完整路徑 |
| `e4928336` | A2～A4 schema 收緊（三點改在同一組建構器函式裡，拆不開，合成一個 commit） |
| `d58f27b5` | A5 system 指令「選填欄位沒必要不要填」，`PROMPT_VERSION` → `skill-proposal/5` |
| `5fe5defa` | F1／F2 閃現目錄只列套得上的模板 |
| `6893f81f` | C2 `max_tokens` 2048 → 1024 |
| `f040a828` | C3 命名 prompt 避免重複詞頭、帶入本輪已用名稱，`NAMING_PROMPT_VERSION` → `skill-naming/2` |
| `6fe4eec6` | C4 `concept`／`cast_flavor` 簡體字檢查 |
| `1ec32140`、`3117a56c` | C5 自由題選單排除形態原語（第二個是受影響的既有測試） |

## 2. 每點做法

### A1 巢狀效果錯誤帶完整路徑
- `SkillDef._check_effect(at, effect)` 改收完整路徑（`effects[0]`、`cost.on_miss[1]`、`effects[0].then[0]`、`effects[2].win[0]`、`effects[0].on_kill[0]`、`effects[0].effects[1]`（區域）、`modifiers[i].change.on_hit_effects[j]`），訊息開頭就是該路徑，不再一律寫 `effects[0]`。`flag.true_only` 的 `SkillRuleError.path` 同步。修正規則原本「接字串」的寫法改成直接傳路徑（訊息文字不變）。
- 變奏：`_check_variant` 的錯誤改成帶路徑的 `SkillRuleError`（`variants[i].replace_effect.index`、`.element`、`.range_delta`）；變奏型態的錯誤經新方法 `SkillDef.variant_error_path` 對回 `variants[i].add_effect`／`variants[i].replace_effect.effect`／`variants[i].shape`／`variants[i].when`。
- 新增 `trpg.content.skills.error_path_of(message)`：從錯誤訊息找完整效果路徑（先去掉 `（damage）` 這類類型註記）。
- 提議端（`proposal.py`）：`_skill_path` 改用它；新增 `_proposal_path`，把 `cost.on_miss` 換成提議欄位 `cost_on_miss`、把跨檔案驗證的 `variants.<id>.…` 換成 `variants[i]…`；`_rule_error` 對變奏型態的違規（`variant.<id>.*`）指向該變奏，路徑空白的違規改從訊息找效果路徑。

### A2 巢狀位置用精簡的效果型別（照驗證器現有規則推導）
- `TOP_ONLY_DAMAGE_PARAMS`（`explode`、`scaling`、`lifesteal_permille`、`split_heal`、`spread`；驗證器 `_check_variable_damage`）：巢狀位置（`then`、`on_kill`、區域效果、賭注分支）與失手反噬的 `damage` 不提供。
- 失手反噬的 `apply_status` 列舉扣掉 `ruleset.unsafe_backlash_statuses()`（硬控、跳過回合、持續傷害；與跨檔案檢查同一份）。
- 反應技分支：有反應技的版型多一支 `kind: reaction`，`reaction` 必填；不提供 `ACTIVE_ONLY_FIELDS`（`cost_penalty`、`cost_overdraft`、`cost_on_miss`、`variants`、`trigger`、`followup`）。另一支（一般種類）沒有 `reaction`。spec 只列了 overdraft／on_miss，其餘四個是同一批驗證器規則（自身代價、變奏、複合技能只有主動技能可以有；trigger 只有被動可以有），一併推導（見待決 #2）。
- 武器技 `weapon_req`：見待決 #1。做了依類別分支（`split_category=True`：武器技只列 melee／ranged、法術技只列 focus／any），但**預設關閉**，改在 `weapon_req` 的說明寫清楚配對（`WEAPON_REQ_DOC`）。原因：類別分支讓頂層模型數加倍，寬題目（例：`ProposalRequest(2, "rare")`）的子集 schema 從 101,566 字元變成 136,609，超過 `SCHEMA_CHAR_LIMIT` 125,000，`build_proposal_prompt` 會丟 `SubsetError`，整題直接失敗。

### A3「恰好其一」「必填」進 schema
vLLM strict 對 `oneOf` 內「依欄位是否存在」的條件（`required` 組合、`if/then`、`dependentRequired`）沒有把握，所以一律用**拆分型別**：每支都是 `additionalProperties: false` 的普通物件，以 pydantic 的判別函式選支（JSON Schema 仍是 `oneOf` 列 `$ref`，和既有的版型 union 同一種構造，4-L9 實測 strict 全部接受）。分支標籤含 `~`，錯誤路徑會略過。
- 變奏 `when`：四種條件各一支（`When_caster_surface` 等），每支只有一個必填欄位。
- `inscribe`：`element` 一支、`tag` 一支（`EXACTLY_ONE_PARAMS`），各自必填。
- `split_heal`：`damage` 拆成 `_plain`（沒有 `split_heal`）與 `_split_heal`（`split_heal: true` 與 `affects: all` 都必填）。
- 持續區域：`affects` 必填且只列 `enemies`／`allies`／`all`；版型依 `anchor` 分三支（`tile` 不限形狀、`caster` 只列 `ZONE_CASTER_SHAPES`、`moving` 只列 `ZONE_MOVING_SHAPES`）。spec 只寫 caster，moving 是同一條驗證器規則（見待決 #5）。
- 瞬步：版型依 `landing` 分兩支（`choose` → `unit_then_tile`、`behind` → `single`，取自 `SHADOWSTEP_SHAPES`）。
- 頂層錯誤的可用值補完整：`kind` 錯誤列出該版型全部種類（含 reaction）、版型不存在時列出全部版型、`category` 列出全部類別。

### A4 表面列舉、`grant_skill.skill` 列舉
- 變奏條件的表面列舉只放 `surfaces.yaml` 的 8 種（`crystal` 之類直接 `literal_error`）。
- `grant_skill.skill` 改列舉 `grantable_skills(library)`（規則與 `granted_skill_problems` 相同：一般主動技能、不是傳說、不含改寫規則型／規則改變型原語、不是 `grant_skill` 技能），目前 235 個，約 5.6K 字元（只在子集含 `grant_skill` 時出現）。測試逐一確認列舉裡的技能都通過跨技能檢查。

### A5 system 指令
`SYSTEM_TEMPLATE` 加一行「代價（cost_*）、變奏（variants）、條件（condition）都是選填；題目沒要求就不要填，越簡單越容易通過。」；`PROMPT_VERSION` `skill-proposal/5`，快照新增一筆。沒有依稀有度收 schema。

### F1／F2 閃現模板列舉
`build_catalog(..., applicable=...)`：只收引擎套得上的變化（LLM 提議傳 `try_variation(...) is not None`，與 `flash.not_applicable` 同一個判斷）；模板的參數選單只留套得上的值，沒有套得上變化的模板與類別不列入。指定類別時目錄本來就只有該類，再經這個篩選就只剩該類可用的模板。不傳 `applicable` 時目錄與原本完全相同（測試確認）。prompt 文字沒變，`FLASH_PROMPT_VERSION` 不升（只是目錄內容變少）。

### C2
`config/llm.toml` `max_tokens = 1024`（附註說明）。`LLMConfig` 的程式預設值仍是 2048（設定檔會覆寫）。

### C3 命名
命名指令加：taken_names 含這一輪已取過的名稱；「name_zh 避免重複使用名詞表裡的世界觀名詞當開頭，也不要和 taken_names 的名稱用同樣的開頭；從技能的效果、元素與形狀取材」。正式流程（同一個提議器 ＝ 一輪）本來就把已取名稱放進 `taken_names`，新增測試確認第二次命名 prompt 帶到第一個名稱。4-L9 評估工具原本命名時沒帶 `taken`，改成同一次評估共用（執行緒安全），重跑評估時才看得到效果。

### C4 簡體字
新增 `trpg.llm.simplified`：約 680 個常見簡體字（只收繁體幾乎不單獨使用的；「后、里、干、斗、范、冲、烟、脉、着」等繁體也常用的不收）。`check_naming` 對 `concept`、`cast_flavor` 檢查，有就回報 `concept.simplified`／`cast_flavor.simplified`（訊息列出是哪些字），模型重試。用全部內容資料、技能敘事與設計文件掃過，沒有誤判（全專案只找到報告裡引用的「目标」與一處程式註解的「次数」，都是真的簡體）。提議本身的 `concept`／`cast_flavor` 不檢查：命名開著時會被命名結果取代，關著時用模板文字，都不會進遊戲。

### C5 形態原語
自由題（`core_primitive` 為空）的子集排除 `skill_composer.yaml` 的 `llm_topic.core_exclude`（`enter_form`、`leave_form`），`dropped` 記「形態只由手寫內容提供，自由題不收」。指定核心的題目不動（核心本來就排除形態）。

## 3. schema 變化（測試照既有方式更新）

專案沒有 JSON schema 的快照檔；檢查 schema 結構的既有測試照新結構更新：
- `tests/skillgen/helpers.py`：`standard_form` 說明更新；新增 `effect_branches`（拆分效果的各支）。
- `test_proposal.py`：每個原語的參數檢查改看各支的聯集（`Effect_zone` 改看 `Effect_zone_tile`）；`inscribe` 改驗兩支各自必填。
- `test_proposal_l5c.py`：`split_heal` 的資料補 `affects: all`；失手反噬的狀態列舉另外扣不安全狀態。
- `test_proposal_l8.py`：反應技缺 `reaction` 改在提議格式階段報 `reaction`／`missing`（原本在 `skill` 階段、沒有路徑）。
- `test_self_costs.py`：`cost_penalty` 改成具名型別 `CostPenalty`。
- `test_llm_source.py::test_menu_rotation_shrinks_and_shuffle_keeps_membership`：自由題不收 `leave_form` 後，3 階 epic 的附帶原語都已是某骨架的核心（不輪替），原語不一定變少；改成原語 `<=`、條件 `<`。

新的 `$defs` 名稱：`SkillProposal_reaction`、`SkillProposal_<版型>_reaction`、`SkillProposal_zone_{tile,caster,moving}`、`SkillProposal_shadowstep_{choose,behind}`、`Effect_damage`（→ `_plain`／`_split_heal`）、`Effect_inscribe`（→ `_element`／`_tag`）、`VariantWhen`（→ `When_*`）、`CostPenalty`／`CostOverdraft`／`CostOncePerBattle`／`CostHp`／`CostOnMiss`、`WeaponReq`。代價欄位改成具名型別後，說明在 `$defs` 只寫一次。

schema 大小（字元）：完整 schema（rare）118,055 → 124,753（多的主要是 `grant_skill` 列舉）；上面那個寬題目的子集 101,566；4-L9 的升級題 8 題抽樣 11K～26K。

## 4. 驗收

- `ruff check .`、`ruff format --check .`（1206 檔）、`mypy`（846 檔）、`lint-imports`（7 kept）全過。
- `pytest -n 8 --timeout=3000 -m "(slow or not slow) and not llm" tests/llm tests/skillgen tests/cli`：4018 passed、14 skipped（修正 `test_llm_source` 前 1 failed，原因見第 3 節）；修正後該檔 16 passed。另跑 `tests/content`（A1 動到 `SkillDef`）、`tests/api/test_run_llm_api.py`、`tests/roguelite/test_llm_run.py`、`tests/roguelite/test_flash_llm_run.py`、`tests/engine/test_negative_statuses.py` 全過。
- 重播：`trpg battle --map lava_crossing --seed 3` → `battle replay` 通過（97 個動作、355 個事件）。
- 新增測試：`tests/skillgen/test_proposal_l10a.py`（A1 錯誤路徑 8 個、A2～A4 schema 與提議錯誤 14 個、C5 4 個）、`tests/llm/test_flash_propose.py`（F1／F2 6 個）、`tests/llm/test_simplified.py`（C4）、`test_prompts.py`／`test_naming.py`（A5、C3 快照與文字）、`test_skill_eval.py`（評估共用已取名稱）、`test_client.py`（C2）。
- 複雜度：沒有新增 `# noqa: C901`／`PLR09xx`。
- 沒有連真模型，也沒有連 8001 埠。

## 5. 待 PM 決定

1. **武器技 `weapon_req` 只列 melee／ranged**：依類別分支的程式已寫好（`build_proposal_models(..., split_category=True)`，有測試），但預設關閉，因為寬題目的 schema 會超過 `SCHEMA_CHAR_LIMIT`（125,000）而整題失敗；目前改用 `weapon_req` 的說明寫明配對。可選：a. 維持說明（4-L9 這類錯誤 12／992）；b. 把 `SCHEMA_CHAR_LIMIT` 提高後打開分支（schema 變大可能拖慢解碼，要真模型量）；c. 提議不再填 `category`，由 `weapon_req` 推導（徹底消掉這類錯誤，schema 不變大，但提議格式要改，few-shot 與測試都要跟著改）。
2. **反應技分支多拿掉的欄位**：除了 spec 列的 `cost_overdraft`／`cost_on_miss`，也拿掉 `cost_penalty`、`variants`、`trigger`、`followup`（都是驗證器「只有主動／被動技能可以有」的規則推導）。請確認。
3. **沒做的同類規則**：賭注分支的 `apply_status` 對象可以是敵方，不能用同一份「不安全狀態」列舉，沒有收；被動技必須有 `trigger`、非被動不可有，沒有拆分支（不在 spec，拆了頂層再多一倍）。
4. **頂層分支的數量**：反應技、區域 anchor、瞬步 landing 的分支讓頂層模型數增加（完整 rare schema 21 → 29 支）。真模型重跑時請留意 strict 解碼時間與 `json_invalid`。
5. **區域 `anchor: moving` 也分支**：spec 只寫 caster；moving 的形狀限制是同一條驗證器規則，一起做了。
6. **`grant_skill` 列舉不篩階級／稀有度**：235 個全列，強度由預算決定；需要的話可以只列和題目同階、稀有度不高於題目的技能，縮小列舉。
7. **C5 只套用在自由題**：指定核心的正式題目，`area` 骨架的附帶原語仍可能出現 `leave_form`（YAML 註明「手寫專用」）。要不要所有 LLM 題目都排除？
8. **C4 只檢查命名步驟**：閃現的 `note_zh`、提議本身的敘事沒有檢查（後者不會進遊戲）。字表是小型常見字表，漏網的字之後擴充。
9. **程式預設 `max_tokens`**：`LLMConfig` 預設值仍是 2048（設定檔已改 1024）。要不要一起改？
10. 掃簡體字時發現 `src/trpg/skillgen/candidates.py` 註解有「次数」（簡體），不在範圍，沒改。
