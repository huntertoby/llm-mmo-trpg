# Phase 4-L10b 報告：引擎補值與說明修正

依 `Phase4計畫.md` 4-L10 節的 4-L10b 與 `Phase4-L9報告.md` 第 7 節 B1～B5。不改遊戲規則：預算下限（70%）、稀有度可用內容都沒動；沒有連真模型，測試只用 Mock／純函式。

## 1. Commit

| commit | 內容 |
|---|---|
| `eeb736fd` | B1 無旋鈕結構的過弱補強（`lift_weak`、`llm_cost.weak_steps`） |
| `cd70dae6` | B2 `cap.revive_cost`、`cap.rule_rewrite_cost` 進可修清單（補冷卻） |
| `52ac0a9b` | B3 `skeleton.secondary_share`：附帶傷害降到最低值，仍超標就明確建議移除 |
| `3dba9239` | B4 `shockwave`／`raise_terrain`／`lower_terrain` 的 `llm_hint` 補大地元素 |
| `6b2d86b1` | B5 擊殺時效果（`damage.on_kill`）的 `llm_hint` 補「只能對自己有益」 |
| （本報告） | 報告 |

## 2. 每點做法

### B1 無旋鈕結構 `budget.weak`（使用者採 b）
- `src/trpg/skillgen/proposal_budget.py` 新增 `lift_weak`：只在修 `budget.weak` 時（`evaluate_with_repair` 的第二次評估）啟用，第一次評估的結果與以前完全相同。
  1. 先把巢狀效果的數值也當旋鈕重調（`NESTED_KNOB_KEYS = ("then", "on_kill")`；例如 `consume_status` 的 `then` 傷害骰）。失手反噬與賭注輸方不調。
  2. 還是過弱，而且是主動技能時，就依 `content/skill_composer.yaml` 新增的 `llm_cost.weak_steps` 由輕到重試：AP 降到 1（AP 係數 500‰），必要時再補冷卻 1～5、法力 3／6／10（AP 1 調過頭時用來拉回窗內）。每一階都重新調旋鈕，取第一個「比例落在驗證器窗 70～100%、骨架占比也合格」的結果。
  3. 全部都不行就原樣回傳，照舊回報 `budget.weak`。
- 資料驅動：階梯放在 YAML（`LlmCostRules.weak_steps`，schema 檢查冷卻不超過 `max_cooldown`），程式裡沒有寫死技能 ID 或原語。`ap` 取「原本」與「這一階」的較小者，冷卻和法力取較大者，所以不會低於互斥規則要求的冷卻。
- 實測（Mock 提議，種子 3）：teleport＋隱蔽、swap＋緩速、leap＋加速（2 階）、swap_any、teleport_target（3 階）、raise_terrain 單格、cleanse＋防禦、apply_status、consume_status、restore_resource、topple（1 階）都補得起來。補不到的是 2～3 階「只有一個固定點數核心、沒有任何附帶效果」的提議（例如 3 階單獨的 teleport，AP 1 也只有約 35%），這些照舊回報。

### B2 `cap.revive_cost`、`cap.rule_rewrite_cost`
- 兩個代碼加進 `REPAIRABLE_CODES`；新增 `cap_cooldown(library, code, data)`：門檻直接讀 `skill_budget.yaml`（`rule_rewrite_min_cooldown` 4；改寫規則型且花源力時用 `rule_rewrite_min_cooldown_with_source` 2），和驗證器用同一個來源。
- 補值器補冷卻，和 `exclusion.no_cooldown_*` 同一個做法；沒有選「每場一次」（理由見待決 #2）。
- `proposal_fallback`（保底工坊）也是用 `is_repairable` 判斷，所以保底技能遇到這兩條規則也會由引擎補冷卻。

### B3 `skeleton.secondary_share`
- 修補時原本最多重調 4 次，最後一次是「全部旋鈕」，可能把附帶傷害又調高。現在 4 次都失敗時，會把骨架 `secondary.max_share_permille` 列到的附帶效果（例如控制骨架的傷害）旋鈕降到第一階（最低骰或最低武器倍率），再只調核心。
- 修補後仍超標時，`evaluate_with_repair` 把這條錯誤改寫成明確建議：`path` 指到那個效果（例如 `effects[1]`），訊息在原文後面加「引擎已把這個傷害（damage）降到最低值仍超過上限：請移除 effects[1] 的 damage，只保留骨架的核心效果（或改用允許 damage 當主軸的骨架）」。改寫在 `proposal_budget.py`，**沒有動 `skillgen/validate.py`**（避免和 4-L10a 衝突）。
- 實測：控制骨架＋表面（有持續旋鈕）＋傷害可以直接修好；dispel、steal_buff、blow_surface、clear_surface、緩速等核心點數小的，傷害降到最低仍占 45% 以上，會回報上面的建議；照建議移除傷害後就不會再有占比錯誤。

### B4／B5 說明文字
- `shockwave`：「讓直線上的單位直接倒地，會飛的不受影響（須用大地元素 earth）。」
- `raise_terrain`／`lower_terrain`：「把格子的地形抬高／降低（改地形須用大地元素 earth）。」
- `damage.on_kill`：「這個傷害擊倒敵人時給施放者的效果，只能對自己有益。」`on_kill.beneficial` 只檢查技能內 `damage.on_kill`，被動觸發 `skill_triggers.yaml` 的 `on_kill`（擊倒時）不受這條規則限制，所以那裡沒改。
- 用字受兩個既有測試限制：`tests/content/test_llm_hint.py`（一句話、60 字內）和 `test_subset_fits_within_the_token_budget`（控制骨架在 2,700 token 預算內的核心結構，現在是 2,696）。所以句子寫得比較精簡，見待決 #4。
- **`PROMPT_VERSION` 不升**：`llm_hint` 只進 schema 的 description 和 `available`（資料），system 指令模板沒變，和 4-L8b 的判斷一樣；prompt 快照測試也通過。

## 3. 驗收

- 新測試 `tests/skillgen/test_proposal_l10b.py`（48 個）：
  - B1：11 個原語各一個典型提議，第一次評估只有 `budget.weak`，修補後 `repaired == ("budget.weak",)`，`validate_skill` 為空、比例在 70～100%、結果確定。卡片＝實戰：卡片 AP 等於技能 AP、法力和冷卻文字一致、`then` 補上的骰子寫在卡片上；放進戰鬥用 `legal_actions` 施放後，實際扣的 AP、法力（扣掉回復的量）與冷卻等於卡片。另外測了：補不到時照舊回報、不過弱的提議 AP 維持 2、`weak_steps` 資料形狀。
  - B2：`revive`、`grant_ap`、`reset_cooldown`、`cheat_death`、`redirect_damage`、`copy_skill`、`extra_reaction` 在 1 階和 3 階都確認規則代碼由引擎修掉、補的是冷卻不是每場一次。1 階整招通過；3 階單獨一個原語只剩 `budget.weak`（B1 範圍）。`cap_cooldown` 的門檻（含源力）、`followup.` 前綴、`cap.rule_rewrite`（個數）不可修。
  - B3：control（狀態）、dispel、steal_buff（武器）、blow_surface、clear_surface（武器）帶傷害時，錯誤路徑是 `effects[1]`、訊息有「請移除 effects[1] 的 damage」，修補後傷害停在最低階，移除傷害後沒有占比錯誤；表面骨架＋傷害直接修好。
- 既有測試只改 1 行：`test_proposal_budget.py::test_repairable_codes` 的清單加上兩個新代碼。
- 收尾檢查：`ruff check .`、`ruff format --check .`、`mypy`（844 檔）、`lint-imports`（7 kept）全過。
- pytest（都加 `-m "(slow or not slow) and not llm"`）：`tests/skillgen tests/llm` 3,860 passed／14 skipped（B3 後）；`tests/content tests/llm tests/skillgen` 相關子集 2,267 passed（B4／B5 後）；`tests/cli`（`--timeout=3000`）156 passed；`tests/api tests/roguelite -k "llm or proposal or workshop or flash"` 84 passed。
- CLI 快照、workshop／icon 夾具不受影響，沒有重產（沒用 `UPDATE_CLI_SNAPSHOTS`）。

## 4. 待 PM 決定

1. **B1 降 AP 再補冷卻／法力**：「降費用」我做成「AP 2 → 1，必要時補冷卻 1～5、法力最多 10」。AP 1 讓可用預算減半，固定點數的核心常常一下子超過 100%，所以需要冷卻和法力拉回來。等於拿較長的冷卻換較低的 AP，總費用是降的。法力上限 10 是照手寫技能最高約 12 定的；試過 15／20 能再多救幾個（例如 2 階的 teleport_target），但法力太貴，沒有採用。
2. **B2 補冷卻還是每場一次**：選了補冷卻（4 回合；花源力 2 回合），因為和互斥規則的修法一致，而且每場一次的折抵是 400‰，會讓預算一口氣變很多。如果要改成「每場一次」，只要改 `cap_cooldown` 一處。
3. **只有一個固定點數核心的提議（2～3 階）仍然補不到**：單獨的 teleport／swap／leap／cleanse／topple、或 3 階單獨的改寫規則型原語，AP 1 加滿旋鈕也只到 26～66%。照規格照舊回報 `budget.weak`。可以考慮讓這種情況的錯誤訊息多一句「加一個有數值的附帶效果」（4-L9 建議 B1 的 c，屬於說明／提示範圍，沒做）。
4. **B4／B5 的用字比較精簡**：受兩個既有限制影響——hint 只能一句話、60 字內，以及控制骨架 2,700 token 的子集測試（現在 2,696，離上限只剩 4）。之後只要再加控制骨架相關的說明就會超過，可能要放寬那個測試的 2,700。
5. **`PROMPT_VERSION`**：這段沒有升（只改了 schema 用的資料 hint）。合併時以 4-L10a 的版本為準。
6. **重跑 4-L9 評估**：要等 4-L10a 合併後由 PM 安排（需要真模型）。
