# Phase 3E-2b 報告｜原語登錄表（解譯器拆檔＋對外入口＋載入時對應檢查）

> 規格：`docs/phases/Phase3E計畫.md` 3.1 表的 3E-2b 列（審查 R2、R7、舊 3E-3 #5）。
> 這是重構：沒有改任何數值、事件或 `LOG_FORMAT`（仍是 `/57`）。

## 做了什麼

### ① 新的模組結構（`src/trpg/engine/skills/`）

| 模組 | 內容 |
|---|---|
| `casting.py`（新） | **對外入口**。`use_skill`、`use_triggered_skill`、`use_gear_effects`、`use_modifier_effects`、`use_rule_change_effects`、`use_trap_skill`、`use_zone_effects`、`use_reaction_skill`、`run_delayed`、`run_infused`。執行時不匯入任何引擎模組（只有型別註記），解譯器載入時以 `install(...)` 登錄實作（`CastingImpl` Protocol，mypy 檢查簽名）。引擎其他模組一律從這裡呼叫。 |
| `interpreter.py`（2464 → 約 620 行） | 施放的入口實作：檢查、付代價、複合技能與第二段、延遲段、灌注、被動／陷阱／區域／修正規則／規則改變／反應的施放；檔尾 `casting.install(_Interpreter())`。`battle.py` 照舊匯入它（`trpg.engine` 一載入就會匯入 `battle`，所以只要用到引擎就已經登錄；沒登錄時 `casting` 拋出 `RuntimeError`）。 |
| `cast.py`（新） | `Cast`（原 `_Cast`）：命中、對象選取、效果順序、施放前後的處理（衝鋒與瞬步先結算、消耗層數、賭注擲骰、吸血、擊殺時效果、失手反噬、命中後反應、冷卻修正），以及原語共用的數值輔助方法；`Cast.build` 只查登錄表。`TriggeredCast`、`GearCast`（原 `_TriggeredCast`、`_GearCast`）。 |
| `primitives/__init__.py`（新） | **登錄表** `PRIMITIVE_HANDLERS`（原語 ID → handler，唯讀、依 ID 排序；兩個模組登錄同一原語時載入就失敗）與 `primitive_handler(kind)`（沒登錄時 `KeyError`，**沒有預設分支**）。 |
| `primitives/base.py` | `Handler` 型別 `(Cast, ResolvedEffect, EffectSpec) → list[EffectBase]`、`TOUCHING_AFFECTS`、`no_effects`。 |
| `primitives/numeric.py` | damage、heal、shield、cleanse |
| `primitives/displacement.py` | push、pull、teleport、leap、swap、teleport_target、swap_any、charge_through、knock_prone、topple、hurl_object |
| `primitives/statuses.py` | apply_status、consume_status、steal_buff、dispel、reveal、delayed_damage、add_stack |
| `primitives/rule_rewrites.py` | grant_ap、reset_cooldown、cheat_death、redirect_damage、copy_skill、extra_reaction、restore_resource、grant_skill |
| `primitives/summoning.py` | summon、sacrifice_summon（`sacrifice_blast` 也給 `GearCast` 用）、zone、revive、detonate_runes |
| `primitives/terrain.py` | create_surface、destroy_object、create_obstacle、inscribe、raise_terrain、lower_terrain（原 `tile_effect` 的 if 鏈，**沒有 else**，`rule_change` 以前就是掉進這裡靜默不做事） |
| `primitives/deferred.py` | 在效果位置不展開的原語：dash、shadowstep、consume_stack、intercept、place_trap、rule_change（`no_effects`）、gamble（結算擲出的分支） |

48 個原語（`skill_primitives.yaml` 全部）各恰好一個 handler。`Cast` 原本的私有輔助方法改成公開名稱（`is_hit`、`roll_one`、`modifier`、`attack_damage`、`physical_element`、`gamble_for`、`spell_scaled`、`level_permille`、`heal_multiplier`、`knock_down`、`status_effects`、`dash_continues`、`update_cooldown_delta`），新增 `spawn(...)`（`copy_skill` 另起一般施放）；只有單一原語用到的輔助函式搬進該原語模組。`GearCast` 的兩個覆寫（`sacrifice_summon` 以倒下格為中心、`grant_ap` 受裝備上限）合併到 `GearCast.build`。

### ② 載入時的對應檢查（`src/trpg/primitive_coverage.py`，新）

`check_primitive_coverage(library)` 檢查 `skill_primitives.yaml` 的每個原語：

| 對應處 | 檢查的東西 |
|---|---|
| 解譯器 | `trpg.engine.skills.primitives.PRIMITIVE_HANDLERS` 有它 |
| 預算 | `budget_basis` 不是空的，且在 `trpg.skillgen.budget.BUDGET_BASES`（`_plain_base_points` 有實作的算法；原本最後一行是「其他一律當表面算」的預設分支，改成明確的 `surface`，其餘拋 `BudgetError`） |
| AI 估值 | `trpg.engine.ai.coverage.PRIMITIVE_VALUATION`（新的宣告表，見待 PM 決定 #1） |
| 敘事 | `trpg.narrative.skills.DESCRIBED_PRIMITIVES`（＝ `_EFFECT_TEXT` 的鍵；原本 shield、cleanse、intercept 靠「找不到就寫 `name_zh`」的預設分支，改成明確的 `_name_only`，輸出不變） |
| 預覽 | `trpg.engine.preview.PRIMITIVE_PREVIEW`（新的宣告表） |

缺了就丟 `ContentError("<content>/skill_primitives.yaml", "原語的對應項不完整：\n  - 原語 X 沒有解譯器的對應項（請補 …）…")`，一次列出全部缺項。呼叫處：CLI（`content check` 與經由 `_with_library` 載入內容的子指令，改用 `load_checked_library`）、API `create_app`（不論 `library` 是傳入或自己載入）。`trpg.content` 不能往上匯入 engine／skillgen／narrative，所以檢查放在套件頂層模組（見待 PM 決定 #2）。

### ③ 延後匯入（`PLC0415`）

原本 24 個，**刪掉 10 個、剩 14 個**。

刪掉：解譯器相關 8 個（`delayed`、`reactions`、`rule_changes`、`skill_infusion`、`skill_triggers` ×2、`traps`、`zones` → 一律改成頂端 `from trpg.engine.skills.casting import …`）；順便試出可以直接提到頂端的 2 個（`rewrites` → `gear.cap_ap_gain`、`zones` → `effects.models.CreateSurfaceEffect`）。另外 `gear_charge`、`gear_triggers` 本來就頂端匯入解譯器，也改成經由 `casting`。

剩下的 14 個（逐一試過提到頂端，都會循環匯入失敗）：

| 位置 | 匯入 | 循環 |
|---|---|---|
| `engine/effects/__init__.py:97` | `turns.finish_resolution` | `turns` 匯入 `effects.execute` |
| `engine/effects/queue.py:97` | `effects.handlers.enter_surface` | `handlers` 向 `queue` 登錄處理器 |
| `engine/lifecycle.py:133` | `summons.detonate_on_downed` | `summons` 匯入 `lifecycle` |
| `engine/lifecycle.py:138` | `rule_changes.spawn_on_downed` | `rule_changes` 匯入 `lifecycle` |
| `engine/skill_triggers.py:252` | `delayed.DELAYED_RELEASE`、`attacked_release` | `delayed` → `context` → `skill_triggers` |
| `engine/skill_triggers.py:541` | `reactions.ally_downed_reactions` | `reactions` 匯入 `skill_triggers` |
| `engine/skill_triggers.py:605` | `gear_triggers.resolve_gear_fired` | `gear_triggers` 匯入 `skill_triggers` |
| `engine/skill_triggers.py:616` | `delayed.resolve_attacked_release` | 同 252 |
| `engine/skills/targeting.py:356` | `stacks.required_stack` | `stacks` → `context` → `skill_triggers` → `targeting` |
| `engine/skills/targeting.py:403` | `copying.copy_problem` | `copying` 匯入 `targeting` |
| `engine/zones.py:215` | `effects.execute` | 效果佇列（經由處理器）匯入 `zones` |
| `cli/serve.py:25`、`:27` | `uvicorn`、`trpg.api.app` | 刻意：只有 `serve` 需要，CLI 啟動不載入伺服器 |
| `skillgen/evolution.py:499` | `summon_evolution` | `summon_evolution` 匯入 `evolution` |

引擎內剩下的都是「低層模組在觸發時要回呼高層模組」（觸發分派、倒下處理、效果佇列），解法同本段：低層開一個登錄點、高層載入時登錄（見待 PM 決定 #3）。

## 新增一個原語要改哪幾處（Phase 4 清單）

1. `content/skill_primitives.yaml`：`id`、`name_zh`、`description_zh`、`category`、`harmful`、`params`、`budget_basis`（＋`base_points`），需要時 `allowed_shapes`、`forbid_affects`、`lookup_by_skill_id`。
2. `src/trpg/content/skills.py`：原語常數；`EffectSpec` 的新欄位與驗證（R4 拆 schema 之前仍需要）。
3. **解譯器**：在 `engine/skills/primitives/` 對應的模組寫 handler `(cast, effect, spec) -> list[EffectBase]`，加進該模組的 `HANDLERS`。需要新的效果模型時另在 `engine/effects/` 加模型與處理器。在效果位置不展開的原語登錄 `no_effects` 並在 `deferred.py` 寫明在哪裡結算。命中判定的特例（自己擲抵抗）要加進 `cast.py` 的 `_OWN_CHECK`。
4. **預算**：`budget_basis` 用既有算法，或在 `skillgen/budget.py` 寫點數算法並加進 `_SPECIAL_BASES`（新算法名也要加進 `PrimitiveDef.budget_basis` 的 `Literal`）。
5. **AI 估值**：`engine/ai/coverage.py` 的 `PRIMITIVE_VALUATION` 寫明 AI 怎麼看見它；預覽事件不夠時，在 `ai/utility.py`（候選估計、`_rewrite_gains`、`_SUPPORT_CHECKS`）或 `ai/*.py` 補估計。
6. **敘事**：`narrative/skills.py` 的 `_EFFECT_TEXT` 加一句效果敘述（只寫名稱就用 `_name_only`）。
7. **預覽**：`engine/preview.py` 的 `PRIMITIVE_PREVIEW` 寫明哪個欄位呈現它；新事件要讓 `_outcome` 或專用欄位看得到。
8. 其他（不在載入檢查內）：`src/trpg/content/keyword_derive.py`／`skill_keywords.yaml` 的關鍵字、`skillgen/` 的組合器選項（`options.py`、`composer_parts.py`）、前端 `client/src/render/skillParts.ts` 的 `EFFECT_NAMES`（3E-2e 會改讀 glossary API）、`LOG_FORMAT` 版號、模擬報表。

第 3、4、5、6、7 項漏做時，`trpg content check`、經由 `_with_library` 載入內容的 CLI 指令與 API 啟動都會丟 `ContentError` 並指出要補的地方；`tests/test_primitive_coverage.py` 也會失敗。

## 測試與行為不變的證據

- 新增 `tests/test_primitive_coverage.py`（8 個）：真實內容完全對應（且五張表的鍵與 YAML 完全一致）；新原語缺項時一次列出四處；`budget_basis` 空的或沒實作；對應表多出的項不算錯；`load_checked_library` 在 YAML 加一個原語時丟 `ContentError`（路徑是 `skill_primitives.yaml`）；`primitive_handler` 沒有預設分支。
- 既有測試未改（只有 `tests/engine/test_movement.py` 一段註解裡的函式路徑）；`tests/engine`、`tests/cli`（含輸出快照）、`tests/api`、`tests/roguelite`、`tests/narrative`、`tests/skillgen` 全過。
- 重構前後對照（`875822c` 的 `src` 與 HEAD 各跑一次）：`trpg sim maps --seeds 4` 的 JSON 報表、`trpg sim skills --demo --seeds 2`（434 場）的 JSON 報表**逐位元組相同**；`trpg sim keywords --samples 40` 與兩者的文字輸出只差執行時間與輸出路徑。
- `scripts/check.py`（快速版）全過，約 105 秒。

## 待 PM 決定

1. **AI 估值與預覽的「對應項」是宣告表**（原語 → 說明字串），不是 handler：兩者都是「模擬結算後依事件評分／整理」，沒有逐原語分派可檢查。表能逼新增原語的人想過 AI 與預覽，但檢查的是鍵存在，不是說明正確。採用保守做法；若要更強（例如每個原語宣告會發出的事件，再檢查預覽的 `_outcome` 都認得），建議放 3E-3。
2. **檢查放在套件頂層 `trpg/primitive_coverage.py`**，由 CLI 與 `create_app` 呼叫，而不是 `load_library` 本身（`trpg.content` 不能匯入 engine／skillgen／narrative）。直接呼叫 `load_library()` 的地方（測試、`skillgen/random_composer.py` 的預設內容）不會檢查，靠 `tests/test_primitive_coverage.py` 把關。
3. **剩下 11 個引擎內的延後匯入**不屬於解譯器（見上表），沒有在本段處理；若要清掉，可比照 `casting.py` 在 `skill_triggers`、`lifecycle`、`effects` 開登錄點，建議併入 3E-3（R7 剩餘部分）。
4. **對應表多出 YAML 沒有的原語不報錯**（只檢查缺項），讓測試或模組用刪減過的內容資料夾仍能載入；真實內容的「完全一致」由測試檢查。
5. **「每搬一組原語就 commit」沒有照做**：搬移是用腳本一次產生、再手動整理，中間狀態無法通過 mypy，所以解譯器拆檔是一個 commit（另有 `casting.py`、對應檢查、報告各一個）；每一步都跑過 ruff、mypy 與 `tests/engine`、`tests/cli`。
6. `Cast` 的輔助方法改成公開名稱（去掉底線）並給原語模組使用；這是內部 API，若之後 R4／R10 要再整理（keyword-only、結算模型統一回傳效果批次），以 `Cast` 的類別說明列出的方法為準。
