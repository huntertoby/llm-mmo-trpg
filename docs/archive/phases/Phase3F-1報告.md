# Phase 3F-1 報告：技能工坊後端與靶場地圖

## 1. commit

| commit | 內容 |
|---|---|
| a850ce8 | `trpg.skillgen`：選項推導 `options.draft_options`、檢查 `draft_check.check_draft`、草稿 `draft`、選項結構 `option_models`、參數欄位 `option_params`、值與選項比對 `option_conform`、試組用的最小填法 `option_fill`；`validate.rarity_requirements`（驗證器與工坊共用）；`SkillDef.provenance.origin` 新增 `workshop`、公開 `MAX_MODIFIERS`；`tests/skillgen/test_workshop_options.py`、`test_workshop_check.py`、`workshop_walks.py` |
| 5b0dbea | 靶場 `content/maps/training_range.yaml`、木樁 `content/units/training_dummy.yaml`、行為模式 `idle`、`content/workshop.yaml`（schema `trpg.content.workshop`）、地圖類型 `training`；roguelite 地圖池拒絕靶場、`sim` 預設地圖排除靶場；`tests/content/test_training_range.py` |
| bac58fd | API：`/api/workshop/{arena,options,check,random,export}`；`POST /api/battles` 新增 `custom_skills`、`replace_skills`、`opponents`；重新產生 `client/openapi.json` 與 `client/src/api/schema.d.ts`，`client/src/api/types.ts` 的 `CreateBattleRequest` 讓新欄位可省略；`tests/api/test_workshop_api.py` |
| d67a43f | 全地圖類測試納入靶場（見第 5 節）；`idle` 不再改寫 3E-1 的衝撞／瞬步權重 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。只 commit 自己改的檔案。網頁（3F-2）沒有做。

## 2. 交付項目

### 2.1 選項推導（`trpg.skillgen.options.draft_options`，純函式）

輸入「組到一半的技能」＝技能定義 JSON 的任意部分欄位（`content/skills/*.yaml` 的同一份欄位）。輸出：

- `steps`：前置步驟都完成的每一步（依序 `skeleton → basics → shape → effects → condition → cost → rarity`），每步有中文名稱與說明、`complete`、`fields`（欄位與合法選項）、`notes_zh`（只取決於多欄位組合的限制，例如互斥規則、核心點數占比）。
- `next_step`：第一個未完成的步驟（全部完成為 `null`）。條件與代價都可省略，所以填完效果後 `next_step` 直接是 `rarity`，但兩步的選項仍在 `steps` 裡。
- `problems`：已填但不在選項內的值（中文，含路徑），例如 `effects[1].distance：距離（格）必須在 1–2，收到 5`。

欄位格式（`FieldSpec`）：`field`、`name_zh`、`description_zh`、`type`（`choice`／`multi_choice`／`int`／`count`／`dice`／`bool`／`text`／`tags`／`effects`／`object`／`modifiers`）、`required`、`min`／`max`、`allow_weapon`、`dice_sides`、`choices`、`fields`、`min_count`／`max_count`、`default`。每個 `Choice` 有 `value`、`name_zh`、`description_zh`、`params`（選了它之後要填的欄位：值是物件時相對於該物件，例如形狀、條件、效果；否則相對於同一層，例如 `kind: active` 帶 `ap_cost`、`category` 帶 `weapon_req`）、`info`（最低稀有度、核心／附帶、附帶上限……）。

選項的來源（不另寫規則）：

| 步驟 | 來源 |
|---|---|
| 骨架 | `content/skeletons/` 啟用的骨架（`info`：kinds、最低稀有度、形狀、核心原語、附帶上限、是否需要條件） |
| 基本設定 | 骨架的 `kinds`、`required_category`／`required_weapon_req`；AP 範圍＝`skill_budget.yaml` 的 `ap_coefficient_permille`；階級＝`core.yaml` 的 `tier_budget`；被動的觸發時機＝`skill_triggers.yaml`（`has_other` 才給 `target: other`）、`max_per_round` 範圍取自 `TriggerSpec`；反應時機＝`SKILL_REACTION_EVENTS` |
| 形狀 | 骨架的 `shapes`，且至少有一個核心原語能搭配（`allowed_shapes`）；參數範圍＝`skill_shapes.yaml` |
| 效果 | 骨架核心與附帶原語（`harmful_only`、`max_count`）、原語的 `allowed_shapes`、`acts_on`、`forbid_affects`、骨架的 `forbid_affects`、被動 `target: self` 只能對自己；參數＝`skill_primitives.yaml` 的 `params`（範圍、狀態／表面／物件／元素／層數……可選值來自內容庫）。最後以 **schema 試組** 濾掉這個種類、類別、形狀不能用的原語（例：反應技不能用衝鋒、姿態不能用賭注），見 2.2。修正技能改為「修正規則」欄位：套用對象、改變（範圍取自 `ModifierChange` 的欄位限制、可套用對象取自 `CHANGE_TARGETS`）、條件 |
| 條件 | `skill_conditions.yaml`（參數範圍）；骨架 `requires_condition` 時必填 |
| 代價 | `SkillCost` 的欄位範圍；自身狀態代價＝`skill_budget.yaml` 的 `allowance.self_status.allowed`（只有主動技）；源力與啟動方式只在技能恰好有 1 個傳說核心時列出（`legendary_cores`） |
| 稀有度 | 最低稀有度＝`rarity_requirements`（形狀、骨架、觸發、原語、狀態、條件、失手反噬）＋效果數量（`rarity.*.max_effects`）＋雙屬性縮放；列出最低稀有度以上、且 schema 接受的稀有度（填了源力時只有傳說）；原因寫在 `notes_zh` |

**不合法的選項：不列出**（規格的二擇一）。只取決於多個欄位組合的規則（互斥規則、預算、核心點數占比、`unit_then_tile` 需要位移他人效果……）寫在 `notes_zh`，由 `check` 檢查。

### 2.2 schema 試組（`option_fill`）

SkillDef 的 schema 有許多分散在驗證器裡的限制（「`gamble` 只能用在主動技能」等）。為了不在選項裡重寫這些規則，效果步驟對每個候選原語用「最小填法」（`choice` 取第一個、`int` 取 `min`……；第一個 `choice` 參數的每個值都試，例：瞬步的 `choose`／`behind`）組成技能，單獨、接在已填的效果或一個核心效果之前或之後，以一般（史詩）與傳說（源力 1、啟動 `timed`）各試一次，**有一種能通過 schema 就列出**。無法自動填的原語（`then`、`win`／`lose` 等巢狀效果）試不出來時仍列出。前面步驟本身就組不起來（例如武器需求錯）時不試組，只回報 `problems`。

### 2.3 檢查（`trpg.skillgen.draft_check.check_draft`）

`complete`、`missing_steps`、`legal`、`problems`（`rule`＋`message_zh`）、`budget`、`minimum_rarity`、`rarity_reasons`、`skill`（正規化後的定義）。

- 未完成：`missing_steps` 與 `problems`（`rule: draft`）。
- 完成但 schema 不接受：`rule: schema`，中文訊息（pydantic 的自訂檢查訊息，去掉 `Value error,`，加上欄位路徑）。
- 完成：`validate_skill` 的全部違規（規則代碼 `skeleton.*`、`exclusion.<id>`、`rarity.*`、`budget.*`……，訊息指出骨架或互斥規則的中文名）＋ `skill_budget` 的明細（每個效果的基礎點數 × 形狀 × 對象 × 條件、raw、條件與協同、total、可用預算、代價折抵、`ratio_text` 與 CLI 同格式，`verdict` ok／weak／over）。

技能 ID：草稿沒給 `id` 時用 `skill_ws_` ＋ 內容（不含 id）的 SHA-256 前 10 碼；名稱預設「工坊技能」。

### 2.4 靶場（1.1A）

- `content/maps/training_range.yaml`（「靶場」，12×10，地圖類型 `training`）：北側 1 格寬窄道（木樁在 (9, 1)，往東推會撞牆）、中央開闊區（木樁在 (6, 4)，旁邊可推倒的石柱）、西南物件區（木箱 ×2、油桶、枯樹）、東南地形區（木樁在岩漿邊 (8, 6)、水窪 ×3、草叢 ×3、高 2 的高台與高 1 台階）、源泉格 (1, 1)。我方起始區在西側。`scripts/map_push_check.py`：「通」。
- `content/units/training_dummy.yaml`（「木樁」）：HP 300、速度 0、`reactions: []`、護甲與抗性 0、行為模式 `idle`（所有權重 0，沒有正分的動作，每回合直接結束）。
- `content/workshop.yaml`：預設地圖 `training_range`、輪數上限 30、對手 `dummy`（木樁 ×3，預設）與 `fighting`（木樁 ×3 ＋ 盜賊 ×2）。載入時檢查地圖存在且類型為 `training`、單位存在、起始區放得下。
- 不進：roguelite 抽選（`roguelite.yaml` 的地圖池放了靶場時載入失敗）、`sim matrix`／`sim maps`／`sim completion` 的預設地圖（`default_sim_maps` 排除 `training`）、`GET /api/maps`。`POST /api/battles` 可以用靶場。

### 2.5 裝上試玩（`POST /api/battles` 新欄位）

- `custom_skills`：自訂技能定義列表。每個都要通過 schema 與 `validate_skill`，否則 422，訊息列出每個技能的中文原因。
- `replace_skills`：從主角身上拿掉的技能 ID；自訂技能依序放進被拿掉的位置，多出來的接在最後。主角沒有那個技能時 422。
- 以 `Ruleset.with_skills` 加入規則包；裝備上限用 `skill_slot_problems`（主動 ≤ 6、被動含修正 ≤ 3、反應 ≤ 1、姿態 ≤ 1、規則改變型傳說 ≤ 1），武器相容用 `weapon_problem`。
- `opponents`：只有靶場可以填（其他地圖 422），省略為第一個（木樁）。
- 自訂技能的定義在戰鬥設定的規則包裡，所以 `GET /api/battles/{id}/log` 下載的紀錄直接 `trpg battle replay`。

## 3. 最終 API

| 方法 | 路徑 | 請求 | 回應 |
|---|---|---|---|
| GET | `/api/workshop/arena` | — | `WorkshopArena`：`default_map`、`max_rounds`、`maps`（靶場在最前面，其後是一般地圖）、`opponents`（`id`、`name_zh`、`description_zh`、敵人中文名） |
| POST | `/api/workshop/options` | `{"skill": {...部分技能...}}` | `DraftOptions`（2.1） |
| POST | `/api/workshop/check` | `{"skill": {...}}` | `WorkshopCheck`＝`DraftCheck` ＋ `card`（技能卡片，完整且通過 schema 時才有） |
| POST | `/api/workshop/random` | `{"seed": 42, "tier": 2, "rarity": null, "skeleton": "strike"}` | `{"skill": {...完整定義...}, "check": WorkshopCheck}`；組不出來 422 |
| POST | `/api/workshop/export` | `{"skill": {...}}` | `{"yaml", "filename", "legal", "problems"}`；`provenance.origin: workshop`；schema 不接受時 422 |
| POST | `/api/battles` | 既有欄位 ＋ `custom_skills`、`replace_skills`、`opponents` | 既有 `BattleResponse` |

錯誤：`WorkshopRequestError`、`DraftError`、`ComposeError` → 422（`{"detail": "中文"}`）。

範例（`/api/workshop/options`，只選了骨架）：

```json
請求 {"skill": {"skeleton": "displace"}}
回應 {"next_step": "basics", "steps": [{"id": "skeleton", ...}, {"id": "basics", "name_zh": "基本設定",
  "fields": [{"field": "name_zh", ...},
             {"field": "kind", "type": "choice", "required": true, "choices": [
                {"value": "active", "name_zh": "主動技", "description_zh": "花 AP 施放",
                 "params": [{"field": "ap_cost", "name_zh": "AP", "type": "int", "required": true, "min": 1, "max": 3, ...}]}]},
             {"field": "category", ...}, {"field": "scaling_attr", ...}, {"field": "tier", "min": 1, "max": 5, ...}]}],
 "problems": []}
```

範例（`/api/workshop/check`，衝鋒＋傷害＋擊退）：

```json
請求 {"skill": {"skeleton": "displace", "kind": "active", "ap_cost": 2, "category": "weapon", "weapon_req": "melee",
  "scaling_attr": "str", "tier": 2, "name_zh": "衝鋒擊退", "shape": {"type": "single", "range": 4},
  "effects": [{"type": "dash"}, {"type": "damage", "multiplier_permille": 1000}, {"type": "push", "distance": 2}],
  "cost": {"cooldown": 2}, "rarity": "rare"}}
回應 {"complete": true, "legal": true, "problems": [], "minimum_rarity": "rare",
  "rarity_reasons": ["原語 dash：至少稀有", "原語 push：至少稀有", "3 個效果：至少稀有"],
  "budget": {"lines": [{"type": "dash", "points": 3.0, ...}, {"type": "damage", "points": 7.0, ...}, {"type": "push", "points": 4.0, ...}],
             "total": 14.0, "usable": 19.8, "allowance_parts": ["冷卻 2 回合 +100‰"], "ratio_text": "70.7%", "verdict": "ok", "verdict_zh": "合格", ...},
  "skill": {"id": "skill_ws_e9737f7780", ...},
  "card": {"name_zh": "衝鋒擊退", "effects": ["衝鋒到目標身旁（先結算，不消耗移動點數；途中會被藉機攻擊與陷阱攔下）（自己）", "武器傷害 ×1（敵方）", "推開 2 格（敵方）"], ...}}
```

範例（`/api/workshop/export`）：`{"filename": "skill_ws_e9737f7780.yaml", "legal": true, "problems": [], "yaml": "id: skill_ws_e9737f7780\nschema_version: 1\nname_zh: 衝鋒擊退\n...provenance:\n  origin: workshop\n..."}`

範例（裝上試玩）：

```json
POST /api/battles {"map_id": "training_range", "seed": 3, "hero_build": "build_charger", "ally_builds": [],
  "custom_skills": [<上面的技能>], "replace_skills": ["skill_gale_kick"], "opponents": "dummy"}
→ 201 BattleResponse
POST /api/battles {..., "custom_skills": [<上面的技能>]}          （沒有替換）
→ 422 {"detail": "主動技能超過欄位上限：7 個（上限 6）"}
```

## 4. 驗收條件（1.2）

1. **options：從空技能一步步走到完整技能（打擊、位移、修正），每一步的選項都能組出合法技能；參數範圍與 `skill_primitives.yaml` 一致** — 通過。`tests/skillgen/test_workshop_options.py::test_walking_the_options_step_by_step_builds_a_legal_skill[strike|displace|modifier]`（每一步填的值都在該步選項內、沒有 `problems`，最後 `check` 合法、預算合格）、`test_param_ranges_match_the_content_files`（原語、形狀、條件的整數參數範圍逐一對照三個 YAML）、`test_strike_options_offer_the_skeleton_shapes_and_primitives`、`test_reaction_options_follow_the_schema`、`test_every_shipped_skill_fits_the_options`（內容庫全部技能的每個欄位都在選項內＝選項不漏掉合法技能）、`test_random_skills_fit_the_options`（組合器 120 個種子）、`test_values_outside_the_options_are_reported_in_chinese`、`test_rarity_step_derives_the_minimum_rarity`、`test_legendary_source_is_offered_only_with_a_legendary_core`、`test_options_start_from_the_skeleton_and_are_deterministic`；API `tests/api/test_workshop_api.py::test_options_endpoint_walks_the_steps`。
2. **check：預算百分比與 `trpg skills budget` 一致；不合法技能回中文原因（骨架限制、互斥規則、最低稀有度各一例）** — 通過。`tests/skillgen/test_workshop_check.py::test_budget_percent_matches_trpg_skills_budget[...]`（比對 `print_skill_budget` 輸出的「比例 ＝ … ＝ X%」）、`test_shipped_skills_check_like_the_cli[...]`（4 個內容技能，含修正型傳說、被動）、`test_skeleton_violation_names_the_skeleton_rule`（「骨架 strike：形狀只能是 single、unit_then_tile…」）、`test_exclusion_violation_names_the_exclusion_rule`（「互斥規則「推拉不並存」：…」）、`test_minimum_rarity_violation_and_reasons`（「稀有度 common 不能使用原語 knock_prone（至少需要 rare）」）、`test_partial_skill_reports_the_missing_steps`、`test_schema_errors_are_reported_in_chinese`；API `test_check_endpoint_returns_budget_rarity_and_card`。
3. **random：同種子同參數結果一致；產生的技能 check 合法** — 通過。`test_workshop_check.py::test_random_is_deterministic_and_legal`、`test_workshop_api.py::test_random_endpoint_is_deterministic_and_legal`。
4. **export：匯出的 YAML 重新載入後與原技能相同** — 通過。`test_workshop_check.py::test_export_yaml_round_trips`、`test_workshop_api.py::test_export_yaml_reloads_as_the_same_skill`（`provenance.origin` 為 `workshop`，其餘逐欄相同）。
5. **裝上試玩：自訂技能開戰、施放一次、下載紀錄並 `trpg battle replay` 重播通過；不合法技能與超過裝備上限被拒** — 通過。`test_workshop_api.py::test_try_out_a_custom_skill_cast_it_and_replay_the_log`（走到木樁旁、施放自訂技能，事件有 `skill_used` 與 `unit_dashed`；紀錄的規則包含自訂技能；`cmd_replay` 回 0「重播驗證通過」）、`test_illegal_custom_skills_are_rejected_in_chinese`（過弱、schema 錯誤）、`test_equipment_limits_are_checked`（主動 7 個、替換不存在的技能、武器不相容）。
6. **靶場：地圖與木樁通過驗證、不出現在 roguelite 抽選與 `sim matrix`；木樁整場不移動、不攻擊；可選「木樁」或「會反擊」對手** — 通過。`tests/content/test_training_range.py::test_training_range_and_dummy_pass_content_validation`、`test_workshop_rules_offer_dummy_and_fighting_opponents`、`test_training_range_is_kept_out_of_roguelite_and_sims`、`test_dummies_never_move_or_attack[dummy-0|fighting-1]`（AI 打完整場：木樁的動作全是 `EndTurn`、沒有 `attack_rolled`、沒有主動步行；會反擊時盜賊有攻擊）；API `test_arena_lists_the_training_range_first`（`/api/maps` 不列靶場）、`test_training_range_opponents`；`uv run python scripts/map_push_check.py` 靶場一列為「通」。
7. **check.py 全過** — 通過（見第 8 節）。

## 5. 修改既有測試的原因

- `tests/content/test_map_archetypes.py`：地圖類型多了 `training`（`ARCHETYPES` 的期望集合加上它；「正式地圖」排除 `test` 與 `training` 兩種類型，仍是 10 張）。
- `tests/engine/test_source.py::test_shipped_maps_with_source_wells`：有源泉的地圖排除靶場後仍是 `dark_forest`、`ruined_fort`；另斷言靶場有 1 個源泉（規格要求）。
- `tests/sim/test_push_check.py::test_official_maps_are_all_connected_and_the_table_renders`：非 `test_` 地圖由 10 張變 11 張（靶場；規格要求 `map_push_check.py` 也檢查它）。

沒有重錄任何 CLI 快照。

## 6. 複雜度 noqa

無新增、無移除。

## 7. `LOG_FORMAT`

維持 `trpg-battle-log/34`。自訂技能的定義本來就在 `BattleLog.setup.ruleset.skills`（規則包整份存進紀錄），主角的技能清單在 `setup.units[0].template.skills`，所以不需要新欄位；事件 schema 沒變。新增的只是既有 Literal 的值（地圖類型 `training`、`provenance.origin: workshop`），舊紀錄照常讀取與重播。

## 8. 待 PM 決定

1. **不合法選項「不列出」**；只取決於多欄位組合的規則（互斥、預算、核心占比、`unit_then_tile` 需要位移他人效果……）只在 `notes_zh` 說明、由 `check` 擋。因此「每一步的選項都能組出合法技能」是指 **每個選項在該步單獨成立**（含 schema 試組），不保證任意組合都合法；測試以三條路徑走完、並以全部內容技能與 120 個隨機技能證明選項不漏。
2. **schema 試組**（2.2）：每次 `options` 對每個候選原語試組數次（本機一次約 3–10 毫秒）。帶巢狀效果的原語（賭注 `win`／`lose`、消耗狀態 `then`、區域 `effects`、擊殺時 `on_kill`）在選項裡是 `type: effects`，沒有展開下一層的選項樹（網頁可先以 JSON 編輯或不支援）；要不要在 3F-2 或 Phase 4 展開請決定。
3. **骰子範圍**：`skill_primitives.yaml` 沒有骰子的範圍，選項給的是組合器的骰子階梯（`skill_composer.yaml`：1–`max_count` 顆、`sides` 面）作為建議；`problems` 只檢查 `NdM` 格式，不擋階梯以外的骰子（schema 本身允許）。
4. **匯出不要求合法**：schema 接受就能匯出，`legal`／`problems` 標示問題（方便把半成品存起來）；裝上試玩則要求 `validate_skill` 完全通過（含預算 70–100%）。若想讓試玩也能試過強／過弱的技能，可改成只擋 schema 與引用錯誤。
5. **自訂技能 ID**：沒給 `id` 時用內容雜湊 `skill_ws_xxxxxxxxxx`（同內容同 ID，改了任何欄位 ID 就變），名稱預設「工坊技能」。
6. **「會反擊」的內容**：木樁 ×3 ＋ 盜賊 ×2（敵人依靶場起始區順序擺放：中央、窄道、岩漿邊、東側 ×2），寫在 `content/workshop.yaml`，要換成弓手或盾衛只改那裡。
7. **手動結束**：沒有新增結束戰鬥的端點；勝負照地圖目標（木樁全倒）或輪數上限 30（`/api/workshop/arena` 回傳 `max_rounds` 給網頁帶進 `POST /api/battles`）。網頁可以隨時離開戰鬥回工坊（工作階段留在伺服器記憶體）。如需「結束並結算」的按鈕，3F-2 再加端點。
8. **地圖類型**：新增 `training`（而不是沿用 `test`），一般地圖列表與模擬預設排除它；`trpg map list` 仍列出它，CLI `trpg battle --map training_range` 也能用（預設陣容 `hero_fighter` 對木樁 ×3）。
9. **替換規則**：自訂技能放進被替換技能的位置、多的接在最後；不調整主角的法力上限（武器流 build 法力少，裝法力代價高的技能可能放不出來）。
10. **陷阱觸發範圍** 只列 `single`、`cross`、`square3`（陷阱預算以這三種形狀的倍率計算）；修正規則的 `change` 是 `object`（13 種改變各一個子欄位，恰好填一個），可套用的對象寫在子欄位說明裡。

## 9. 代表性輸出（API：在靶場用自訂技能打木樁）

```
POST /api/battles {"map_id":"training_range","seed":3,"hero_build":"build_charger","ally_builds":[],
                   "custom_skills":[衝鋒擊退],"replace_skills":["skill_gale_kick"]}   → 201
POST /api/battles/{id}/actions  （先走到 (5, 3)）
POST /api/battles/{id}/actions {"type":"use_skill","unit_id":"unit_0001","skill_id":"skill_ws_e9737f7780","target_id":"unit_0002"}
   skill_used     衝鋒流英雄 施放「衝鋒擊退」（AP 2，冷卻 2 回合）→ 影響 1 格
   unit_dashed    ➤ 衝鋒流英雄 衝向 木樁1：(5, 3)→(6, 3)
   attack_rolled  衝鋒流英雄 以「衝鋒擊退」攻擊 木樁1：d20=18 修正 +3 熟練 +2 = 23（目標 11）→ 命中
   damage_dealt   木樁1 受到 8 點物理傷害［骰 4］，HP 300 → 292
   unit_moved     木樁1 被推到 (6, 5)
   unit_moved     木樁1 被推到 (6, 6)
GET /api/battles/{id}/log → trpg battle replay
重播驗證通過：5 個動作、27 個事件，最終狀態一致（training_range，種子 3）。

$ uv run python scripts/map_push_check.py
| training_range | crate(2, 6)、oil_barrel(4, 7)、crate(3, 8) | obj_0003(2, 6)、obj_0005(3, 8) | 通 | — | — | stone_pillar(5, 4)、dead_tree(3, 5) | — |

$ uv run python scripts/check.py
=== 檢查結果摘要 ===
  ruff check             通過
  ruff format --check    通過
  mypy                   通過
  lint-imports           通過
  pytest                 通過
  client install         通過
  client typecheck       通過
  client test            通過
全部檢查通過。
```
