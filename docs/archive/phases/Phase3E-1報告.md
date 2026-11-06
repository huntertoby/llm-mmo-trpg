# Phase 3E-1 報告：3C／3D 審查後的小整理

## 1. commit

| commit | 內容 |
|---|---|
| 0567dbc | #1 `skill_reference_problems(skill, ruleset, skills)`；內容庫與 `validate_skill` 共用；`tests/skillgen/test_validate_shared.py` |
| 12ef0be | #2 `_Cast._attack_damage`：`damage`、`hurl_object`、`charge_through` 共用；`tests/engine/test_attack_damage_shared.py` |
| 95a5a3d | #6 `BattleResult` 以單位 ID 查詢、`Ruleset.with_skills`、`skill_fuzz` 改用它 |
| 2e8f63f | #7 `EffectSpec.param_values` 欄位從 `model_fields` 推導 |
| e13fe2d | #8 區域預算格數改為 `skill_shapes.yaml` 的 `cell_count`，未知形狀報錯 |
| 8c7fb2f | #9 `engine/ids.py` 集中狀態與標籤常數、`next_unit_id(state)` |
| 8446a48 | #10 AI 魔法數字搬進 `AiWeights` |
| （本報告） | 報告 |

開發期間沒有 stash、reset、amend、切換分支，也沒有 push。`LOG_FORMAT` 維持 `/34`，沒有改事件 schema。

## 2. 交付項目與驗收（1.1）

驗收 1：第 1–7 點各有測試或說明。

1. 技能驗證共用：`trpg.content.library.skill_reference_problems(skill, ruleset, skills)` 一次帶齊所有引用表，另外做 `grant_skill` 跨技能檢查與規則改變型傳說 `ap_cost` 檢查；`_check_skills` 與 `skillgen/validate.py::_reference_violations` 都改呼叫它。測試（`tests/skillgen/test_validate_shared.py`）：
   - `test_validate_skill_rejects_bad_references`（`grant_skill` 指向傳說、改寫規則型、不存在、被動技能，以及規則改變型傳說 `ap_cost` 錯誤，各一例）。
   - `test_the_rule_change_legend_ap_cost_is_checked`。
   - `test_validator_and_content_library_agree_on_bad_skills`：同一批壞技能，驗證器的 `reference` 違規與內容庫載入拋出的 `ContentError` 訊息逐字一致。
   - `test_every_shipped_skill_passes_the_shared_check`。
2. 攻擊傷害共用：`_Cast._attack_damage(unit, spec, ...)`（暴擊、格擋倍率、`consume_stack` 的施放者與目標加成、超載、`scaling`、修正規則傷害‰、賭注倍率、穿透後方折扣）；元素由 `_physical_element()` 決定（套 `add_element`）。三處共用。`tests/engine/test_attack_damage_shared.py`：投擲與衝撞各一例 `add_element`、`damage_permille`；投擲 ＋ 賭注（`test_gamble_multiplier_applies_to_thrown_damage`）。
3. `BattleResult.ally/source_of/hp_of/mana_of(unit_id)`；範本便利函式改名 `ally_of_template`、`source_of_template`，同範本兩個我方單位時拋 `ValueError`。`AllyResult` 新增 `mana`、`max_mana`。`Ruleset.with_skills(skills)`：走共用驗證、重建索引、不改原規則包。測試：`tests/engine/test_source.py`（兩個）、`tests/content/test_ruleset_with_skills.py`（4 個）。`sim/skill_fuzz.py` 不再 `model_copy` ＋ 手動 `model_post_init`。
4. `EFFECT_NON_PARAM_FIELDS`、`EFFECT_PARAM_FIELDS`（從 `model_fields` 推導，依名稱排序，順序與原本手列清單相同）。測試：`tests/content/test_effect_param_fields.py`（每個欄位不是參數就是明列排除）。
5. `skill_shapes.yaml` 每個形狀加 `cell_count`（`ShapeCells`：`base`，或 `param` ＋ `by_value` 且必須涵蓋參數全範圍）；`zone_cell_count(skill, library)` 查表，未知形狀、沒有 `cell_count` 的形狀（連鎖）、參數不在表內都拋 `BudgetError`。測試：`tests/engine/test_shape_cell_counts.py`（YAML 數字逐一對照引擎形狀函式在空地圖上的格數）。
6. `engine/ids.py`：`CONCEALED`、`DEFENDING`、`PRONE`、`REVEALED`、`SHIELDED` 五個狀態 ID，`BOSS_TAG`、`ELITE_TAG`、`PENETRABLE`、`STEADFAST`、`TOPPLABLE` 五個標籤，`next_unit_id(state)`（取代 `summons.py`、`effects/world.py` 兩份重複）。14 個檔案的重複定義改引用，`sim/metrics.py` 的 `BOSS_TAG` 也一併改。測試：`tests/engine/test_ids.py`（狀態存在於 `statuses.yaml`；engine 內不得再有同值的常數定義）。
7. `AiWeights.charge_per_enemy`（3）、`shadowstep`（3）、`shadowstep_behind`（2），預設值不是 0。測試：`tests/engine/test_ai_weights_3e.py`（預設值、內容裡沒有行為模式改寫、衝撞估計隨權重變化）。

驗收 2：除第 2 點外戰鬥結果不變。全部既有的 CLI 快照與重播測試沒有改動期望值、全數通過（沒有重錄任何快照，沒有修改任何既有測試的期望值）。

驗收 3：`uv run python scripts/check.py` 全過（ruff、format、mypy、lint-imports、pytest、client 三項）；重播一致（含在 pytest 內）；`uv run python scripts/skill_fuzz.py --count 1000`：組合成功 1000/1000、通過驗證 1000/1000。

## 3. 第 2 點造成的結果變化

- 修正：投擲與直線衝撞的傷害現在會吃修正規則的 `add_element`、傷害‰（原本只吃傷害‰ 與格擋，且 `add_element` 完全不吃）、賭注倍率、`consume_stack` 加成、超載、`scaling`、穿透後方折扣。
- 現有內容中受影響的組合只有一個：`build_charger` 的 `skill_war_avatar`（傳說修正技能，所有攻擊 +18% 傷害）開啟期間，`skill_bull_rush` 衝撞的傷害變成 +18%（原本不吃）。這個 build 的 CLI 快照沒有開啟傳說的情境，所有快照不變。念力投擲、烈焰投擲沒有搭配修正技能的 build，所以不受影響。
- 直線衝撞的 `damage_multiplier`（賭注）在 schema 上無法組合：賭注的 `damage_multiplier` 要求技能有 `damage` 效果，而 `charge_through` 以外的效果只能是 `affects: self`，所以沒有刻意排除，只是沒有可達的組合；投擲有（已測）。

## 4. 修改既有測試的原因

只改了一個：`tests/engine/test_source.py::test_battle_result_reports_remaining_source_for_allies`，因為 `source_of` 的鍵從範本 ID 改為單位 ID（範本版改名 `source_of_template`，同一個測試保留範本查詢的斷言）。

## 5. 新增的複雜度 noqa

無。

## 6. 待 PM 決定

1. `skill_problems(...)` 的可選引用表參數（`triggers`、`stacks` 等預設 `None`）保留，因為約 15 個測試檔直接以最小參數呼叫它。規格要求的「正式路徑必須帶齊」由 `skill_reference_problems` 保證（內容庫與驗證器只走它）；若要把 `_Refs` 欄位全改必填，需要一併改這些測試。
2. 衝撞的 `damage_multiplier` 賭注在 schema 上本來就無法組合（見第 3 節），沒有另外加 schema 檢查。
3. `AllyResult` 加了 `mana`、`max_mana`（3-5 存檔寫回法力用）；沒有加 `status`、冷卻等其他欄位，3-5 需要時再加。
4. `Ruleset.with_skills` 對「同 ID 但內容不同」報錯，「同 ID 且內容相同」視為已加入（回傳原規則包）。若 3-5 想要「覆蓋」語意請告知。
5. 連鎖（`chain`）沒有 `cell_count`（格數取決於跳數與地圖），用在 `zone` 會被預算報錯；目前 `zone` 沒有人用連鎖（組合器與內容都沒有）。
6. `ids.py` 只收「重複定義」的常數；單一模組內自用的標籤字串（例如各原語的標籤）沒有搬。
7. 三個 AI 數值放在 `AiWeights`（預設非 0），而不是另開一個像 `RewriteAiRules` 的區塊；`ai_profiles.yaml` 的表頭註解已補說明。若之後想讓不同行為模式用不同值，直接在該模式的 `weights:` 底下寫即可。
8. 3E-2 會把形狀參數範圍等改以 YAML 為唯一來源，屆時 `cell_count` 的 `by_value` 可由 `params` 範圍驗證（現在已驗證涵蓋全範圍）。

## 7. 代表性輸出

```
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

$ uv run python scripts/skill_fuzz.py --count 1000
  組合成功 1000/1000；通過驗證 1000/1000
```
