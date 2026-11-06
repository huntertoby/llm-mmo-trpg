# Phase 3T-2 報告｜種族技檢查全部效果＋LOG_FORMAT 策略＋小項

> 規格：`docs/phases/Phase3T計畫.md` 表的 3T-2 列與第 2 節驗收；依據 `docs/phases/Phase3後段審查-Python.md` 第 3、4、6、7、8 點（P3、P4、P6、P7、P8）。另加：`skill_primitives.yaml` 的 `extra_reaction` 旋鈕改明寫 `knob: none`。
> 純整理：戰鬥結算、卡片文字不變。CLI 快照沒有重產（`tests/cli` 153 項全過）。

## 1. 做了什麼（對應 commit）

### ① 種族技合法性檢查走過全部效果、coverage（`68004b95`、`8f3fbc7f`）
- `engine/race_skills.py`：`race_skill_problem` 依效果順序檢查 **每個** 效果（原本只看第一個）；各效果的檢查函式多收一個 `effect`（不再用 `_primary(skill)`）；`_required_fields`、`_candidates` 改看全部效果（任一效果是 `restore_choice` 就要 `choice`）；docstring 對齊。
- 公開登錄表：`RACE_EFFECT_EXECUTORS`、`RACE_EFFECT_PROBLEMS`、`UNCONDITIONAL_RACE_EFFECTS`（明確宣告不需額外條件：`bonus_move`、`ignore_opportunity_attack`、`immovable`）；`ai/race.py` 的 `RACE_EFFECT_SCORERS`、`RIDER_ONLY_EFFECTS`（`ignore_opportunity_attack`，只作附帶效果）。AI 取計分函式改直接 `[]`，漏寫會拋錯而不是靜默不用。
- 形態：`engine/forms.py` 新增 `FORM_EFFECT_CONSUMERS`（`FormEffects` 每個欄位由哪個函式生效）、`FORM_ENTRY_CONSUMERS`（`FormEntry` 每個欄位）。形態的 AI 估值是統一的（預覽的 `form_entered` 收益），沒有逐欄位的計分函式，所以形態的「AI scorer」檢查不適用，改檢查引擎處理與卡片文字。
- `primitive_coverage.py`：`race_coverage_problems`（結算／合法性檢查／AI 計分函式三處）、`race_lead_problems`（內建種族不得以附帶效果開頭）、`form_coverage_problems`；併入 `check_primitive_coverage`（CLI、API 啟動時檢查）。
- 測試：`tests/test_primitive_coverage.py` +7（真實內容完整、缺項一次列出、宣告可免、形態欄位、每個形態欄位都有卡片文字）；`tests/engine/test_race_skills.py` +2（第二個效果的條件也被檢查、`choice` 以全部效果計算）。
- `extra_reaction.amount`：`knob: none`（`tests/skillgen/test_proposal_budget.py` 對應項改為空旋鈕）。

### ② `LOG_FORMAT` 策略與 `ruleset_hash`（`b16cbff0`）
- 新文件 `docs/phases/戰鬥紀錄格式變更.md`：策略（第 1 節：只有紀錄結構或結算語意改變才遞增；內容改變靠 `ruleset_hash` 區分；改版流程；算法；重播檢查順序）＋ 原 `runner.py` docstring 全部變更歷程（348 行，一字未改，新增 `/86` 一條）。
- `runner.py`：`LOG_FORMAT = ".../86"`，docstring 只剩兩行；`BattleLog.ruleset_hash`（`str | None`，預設 `None`）；`BattleRun.to_log()` 填入；新函式 `log_replay_problem(log)`（依序：格式版本、缺 `ruleset_hash`、內嵌規則包雜湊不符，皆中文）。
- 新模組 `engine/ruleset_hash.py`：`hash_ruleset(ruleset)`（`model_dump(mode="json")` → 排序鍵 JSON → SHA-256）。注意與 `roguelite.save.ruleset_hash(library)`（內容資料夾檔案的雜湊）是不同東西，文件第 1.4 節說明。
- `cli/battle.py` `cmd_replay` 改用 `log_replay_problem`；舊格式（含 `/85`）的錯誤訊息：「不支援的紀錄格式 … 舊格式的紀錄無法重播，請用目前的版本重新跑一場（變更歷程見 docs/phases/戰鬥紀錄格式變更.md）」。
- 版號 `/85` → `/86`：`git grep "battle-log/85"` 的 8 個測試檔，另有 3 處 `LOG_FORMAT.endswith("/85")`（`test_24c`、`test_self_costs`、`test_wind_54a`，在 ④ 的 commit 補上）。
- 測試：`tests/engine/test_ruleset_hash.py`（5 項：雜湊穩定、新紀錄帶符合的雜湊、JSON 往返不變、舊格式、缺／錯雜湊）；`tests/cli/test_battle_cli.py` 加 3 個案例（`/85` 舊格式、缺 `ruleset_hash`、竄改規則包）。

### ③ `proposal_forms` → `proposal_layouts`、`MAX_EFFECTS` 合併（`cbec6d84`）
- 檔案 `skillgen/proposal_forms.py` → `proposal_layouts.py`（`git mv`）；`FormPlan`→`LayoutPlan`、`STANDARD_FORM`→`STANDARD_LAYOUT`、`SHAPE_FORM_PREFIX`、`form_hint`／`form_id`／`form_of_effects`／`plan_forms`／`skill_form` 對應改 `layout_*`、`plan_layouts`、`skill_layout`；提議的 JSON 欄位 `form` → `layout`、`available.forms` → `available.layouts`、`ProposalModels.forms` → `layouts`；文字「型態」→「版型」（只在提議／prompt 相關檔；戰場變奏與 3J 形態的用詞不動）。測試 `test_proposal_forms.py` → `test_proposal_layouts.py`。
- **LLM prompt 內容因此改變**：`PROMPT_VERSION` `skill-proposal/2` → `/3`，`tests/llm/test_prompts.py` 新增快照 `fa56b01d…`（原 `/2` 快照保留）。
- `MAX_EFFECTS = 4` 只留在 `content/skills.py`（公開、加入 `__all__`），`skillgen/proposal.py`、`proposal_layouts.py`、`validate.py` 改匯入。

### ④ 吞錯與縮放規則必填（`adda25b1`）
- `race_skills.race_skill_of`、`rules/race.py` 的 `passive_of`、`race_element_mods`：移除 `except KeyError`，種族 ID 不存在直接拋 `KeyError`（載入時已驗證）。
- `stack_gain.py`：**未能全部改成直接拋錯**——形態的蓄力吐息技能（`skill_form_breath_*`，`form_breath.BREATH_PREFIX`）由形態資料臨時組出、不登錄在規則包，攻擊事件會帶這種 ID（`test_directed_charge` 4 項因此失敗）。改為 `_event_skill`：只有 `BREATH_PREFIX` 開頭的明確回傳 `None`，其餘 ID 找不到直接拋 `KeyError`；`consumes` 走 `unit.skills`（都已登錄）直接拋錯。
- `ContentLibrary.skill_scaling` 改為必填欄位（移到必填欄位區，拿掉 `model_construct` 空預設），`skillgen/validate.py` 拿掉「沒有載入縮放規則就回傳空」的分支。唯一建構點是 `load_library`，沒有測試內容庫需要補（測試都用真實內容庫）。

### ⑤ 寫死數值與 ID 進 YAML（本段最後一個 commit）
- 誘餌：`races.yaml` 的 `decoy` 效果多 `summon: summon_foxfire_decoy`、`lifetime: 3`、`ai_trigger_range: 7`（`RaceEffect` 新欄位，`RACE_EFFECT_SPECS["decoy"]` 三者必填；`race_reference_problems` 檢查範本存在）。刪除 `DECOY_TEMPLATE`、`DECOY_LIFETIME_ROUNDS`；`spawn_decoy` 讀種族技的 decoy 效果；敘事改用新的 `decoy_template_ids(ruleset)` 認出誘餌召喚事件。
- 透支：刪除 `OVERDRAFT_DURATION`；`ApplyStatusEffect` 不給 `duration`，用 `statuses.yaml` 的 `overdrawn.duration: 2`（同值，單一來源；沒有放進 `core.yaml`，見待決 #2）。
- AI：刪除 `_DECOY_RANGE = 7`，改讀 decoy 效果的 `ai_trigger_range`（見待決 #1）。
- 測試：`tests/content/test_races.py` +5（YAML 值、三個必填參數、未知範本）。

## 2. 行為一致的證據與 `ruleset_hash` 造成的差異

| 項目 | 結果 |
|---|---|
| CLI 快照（戰鬥雜湊、`skills list/show`） | `-m "slow or not slow" tests/cli`：①②後與⑤後各跑一次，153 項全過，**未重產任何快照**。戰鬥紀錄新增的 `ruleset_hash` 與 `format` 不在快照內（快照看戰鬥結果雜湊） |
| 重播 | `battle replay` 往返測試、`test_full_battle`、`test_run_autosave`、`test_directed_charge` 等重播測試全過 |
| 卡片文字 | `tests/narrative`、`tests/api` 全過；種族技說明文字取自同一份資料 |
| 會改變的內容 | ① 戰鬥紀錄的 `format`（`/86`）與新欄位 `ruleset_hash`；② 內嵌規則包的 JSON 多了 decoy 三欄位、`extra_reaction` 的 `knob` 值不同；③ LLM prompt 內容與 JSON 欄位名（`layout`）；舊 `/85` 紀錄無法重播（中文錯誤）。戰鬥中的 roguelite 存檔（`RunSave.engine` ≠ `/86`）同樣無法讀取，戰鬥之間的存檔不受影響 |

測試範圍：`tests/cli`（`-m "slow or not slow"`，153）、`tests/engine`、`tests/content`、`tests/skillgen`、`tests/narrative`、`tests/api`、`tests/llm`、`tests/roguelite`、`tests/sim`、`tests/test_primitive_coverage.py`、`tests/test_architecture.py` 全過；`ruff check`、`ruff format --check`、`mypy`（759 檔）、`lint-imports`（7 kept）通過。依指示沒有跑完整 `scripts/check.py`、沒有跑 `tests/` 全量。

## 3. 複雜度 noqa

沒有新增任何 `# noqa`。

## 4. 待 PM 決定

1. **AI 誘餌觸發距離**：規格寫「`_DECOY_RANGE` 改讀 races.yaml 射程」，但射程（`range: 2`）是放置距離，AI 目前是「最近敵人 7 格內才放」。直接讀 2 會改變 AI 行為（違反行為不變）。保守做法：新增 `ai_trigger_range: 7` 欄位，行為不變。若要改成讀 `range`，是玩法／平衡決定。
2. **透支回合沒放進 `core.yaml`**：`statuses.yaml` 的 `overdrawn.duration: 2` 本來就存在且同值，直接用狀態預設，避免兩處寫同一個數字。
3. **`stack_gain` 仍有一處明確例外**（形態吐息技能不登錄）。若要完全不例外，需讓吐息技能登錄進規則包（或事件帶旗標），是較大改動。
4. **形態沒有逐欄位的 AI scorer**：形態由預覽收益統一估值。coverage 只檢查引擎處理與卡片文字。
5. **`ruleset_hash` 檢查的是「內嵌規則包重新序列化後的雜湊」**：日後 `Ruleset` 欄位增減（即使只加預設欄位）會讓舊紀錄雜湊不符而被拒絕（文件 1.2 節已寫）。若希望保留舊紀錄可重播，需要另做遷移。
6. **golden 紀錄重播測試未做**（審查 P4 建議）：紀錄內嵌整份規則包，檔案很大，不適合提交；目前用「現場產生→JSON 往返→重播」代替。
7. **版型用詞**：把「型態」改成「版型」（layout），只限提議／prompt 相關檔；若美術／文案希望用別的詞請告知。
8. **`PROMPT_VERSION` 升到 `skill-proposal/3`**：LLM 提議的 JSON 欄位名改變，之前存下的提議 JSON（`form`）不再相容。
9. **`RIDER_ONLY_EFFECTS`**：目前只有 `ignore_opportunity_attack`。AI 只看第一個效果決定是否使用，內建種族不得以附帶效果開頭（`race_lead_problems` 檢查）。
