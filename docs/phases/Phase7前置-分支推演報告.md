# Phase 7 前置：檢定覆寫泛化與任意動作的分支推演——完成報告

來源：開發 PM 的 Phase 6 後段 Python 審查「Phase 7 開工前的前置工作」（6R-P 列為 Phase 7 前置的兩項）。純引擎重構：不改規則與數值，`LOG_FORMAT`、`WORLD_RULES_VERSION` 都沒升。

## 1. 做了什麼

### 1.1 `SlideOverride` → `CheckOverride`（`engine/context.py`）

- 新的檢定種類 `CheckKind`（都是守方的檢定，好壞以守方的角度說）：
  - `slide`：自己走進冰面第一格的滑行檢定（`ice_slide.slide_check`）；
  - `surface`：其他表面的進入檢定，例如被推、拉進冰面（`effects.handlers.enter_surface`）；
  - `status_save`：狀態抵抗，例如陷阱定身、技能暈眩（`control.status_effect`）；
  - `contest`：次要對抗，例如技能附帶的擊倒（`maneuvers.contest`，`primary=False`）。
- `CheckOutcome = "best" | "worst"`，語意與預覽模式相同：`min` 一律 `best`、`max` 一律 `worst`。
- `CheckRule(kinds, reason, outcomes, rest)`：符合種類（`None` 為全部）與 reason（`None` 為不限）的檢定，依「符合這條規則的第幾次」指定結果；超出 `outcomes` 的照 `rest`（`None` 照預覽模式）。
- `CheckOverride(rules)`：每次檢定依序比對，**第一條**符合的規則決定，也只有那條計數。捷徑：`CheckOverride.of(...)`（單一規則）、`CheckOverride.worst_at(i, kinds, rest=...)`（第 i 次最差、之前最好）。
- `Ctx`：
  - `slide_override`／`slide_checks` 改成 `check_override`／`check_counts`；
  - **正式結算傳入任何 `check_override`（包括空的）都拋 `ValueError`**，已加測試鎖住；
  - 新增 `check_log`：預覽時依序記下每次檢定的 `CheckPoint(kind, reason, unit_id, outcome, forced)`，正式結算不記。
- d20 的入口統一成兩個：
  - `check_d20(kind, reason, unit_id)`：守方自己擲，例如冰面。`best`／`min` 回傳 20，`worst`／`max` 回傳 1。
  - `opposed_d20(kind, reason, unit_id)`：攻方擲、守方抵抗，例如狀態抵抗、次要對抗。`best` 回傳 1，`worst` 回傳 20。
  - 正式結算時兩者都只呼叫一次 `rng.d20()`，與原本完全相同。
  - `control.py`、`maneuvers.py` 原本各自寫的「預覽時 `mark_branch`＋20／1」改成呼叫 `opposed_d20`，邏輯不變。
  - `primary` 的推擊、絆倒照舊：預覽一律視為成功（natural 20），不是分歧點。
- reason 的格式：`surface:<表面>`、`status:<狀態>`、`contest:<種類>`。
- `ice_slide._roll` 刪除，改成直接呼叫 `ctx.check_d20("slide", ...)`。

### 1.2 分支推演 `preview_action`（新模組 `engine/branching.py`）

- `battle.simulate_slide_branch` 換成 `battle.simulate_branch(base, action, preview="min", *, override=None, gamble=None) -> (ResolveResult, tuple[CheckPoint, ...], branched)`，可以吃任意 `Action`。
- `preview_action(state, action, *, kinds=CHECK_KINDS, limit=MAX_BRANCHES, gamble=None) -> ActionPreview`，流程：
  1. `min` 沒有經過分歧點時直接回傳 `certain`，`branches == (low, low)`。
  2. 否則跑 `max`，再從「全部最好」開始樹狀展開：每個分支跑完後，把它擲過、但還沒指定（在最後一個最差之後）的 `kinds` 檢定逐一改成最差，當成新分支。
     - 失敗讓後面的檢定消失時（例如冰面滑倒後不再走），分支會自然變少。
     - 新分支從 `min` 與 `max` 兩個模式的模擬都會發現。
  3. 順序用 heap 排：先比最差的次數（少的先），再比位置（前面的先）。同一組結果先 `min` 再 `max`。「全部最好 × `min`」就是最少後果，不重複跑。
- 這個順序剛好等於 6E-2b／6P-1 的舊分支順序：全部通過 × max、第 0 次失敗 × min／max、第 1 次……
- `preview_path` 改成呼叫 `preview_action(seen, move, kinds=("slide",))`，自己只負責 `_trace`、合併與小牌。
  - `_SlideFailures`（小牌的失敗停點）直接拿推演裡 `worst=(k,)`、`min` 的分支。
  - 推演裡沒有的分支（理論上只有只在最多後果出現的冰面）才另外跑一次。
- 隱藏陷阱照舊由呼叫端先 `strip_hidden_traps`，模組說明已寫明。

### 1.3 給 Phase 7 確認卡用的 API 形狀

```python
from trpg.engine.branching import preview_action, ActionPreview, PreviewBranch, MAX_BRANCHES
from trpg.engine.context import CheckOverride, CheckRule, CheckPoint, CheckKind, CHECK_KINDS

p: ActionPreview = preview_action(stripped_state, action)  # kinds 預設為全部四種
p.certain  # bool：min 沒經過分歧點，預覽＝實走
p.truncated  # bool：超過上限被截斷
p.low, p.high  # PreviewBranch：最少／最多後果（certain 時是同一個物件）
p.branches  # tuple[PreviewBranch, ...]：[low, high, *依序的組合分支]
p.results  # tuple[ResolveResult, ...]

b: PreviewBranch
b.mode  # "min" | "max"：檢定以外的骰子（傷害、命中、prompt 反應）
b.worst  # tuple[int, ...] | None：kinds 檢定中第幾次最差（其餘最好）；None 為兩個極端
b.checks  # tuple[CheckPoint, ...]：這個分支實際擲過的所有檢定與結果
b.result  # ResolveResult：狀態＋事件

c: CheckPoint  # kind, reason, unit_id（守方）, outcome（"best"/"worst"）, forced（由覆寫指定）
```

- 確認卡可以把 `b.result.events` 交給和 `_trace` 同類的轉換器，依目標分組，例如誰倒地、誰被推到哪、誰抵抗成功。
- 也可以用 `b.checks` 列出「這個結果需要哪些檢定成功或失敗」。
- 預覽前不檢查是否輪到這個單位，照現有路徑預覽的作法由呼叫端用 `acting_unit` 檢查。動作不合法時拋 `IllegalActionError`。

## 2. 分支上限與截斷規則

- `MAX_BRANCHES = 64`：兩個極端（最少／最多後果）之外最多推演 64 個分支。
- 超過時照推演順序截斷：保留最差次數少的組合，位置前面的先。`truncated=True`。
- **兩個極端一定在**：最多後果（全部最差）永遠涵蓋，最壞情況不會被截掉，這是最保守的截法。`limit=0` 時只剩兩個極端。
- 路徑預覽只分冰面，一條路徑最多 1＋2N 個分支（N 段冰），遠低於上限。`PathPreview` 沒有加 `truncated` 欄位，輸出形狀完全不變（見待 PM 決定 2）。
- 每個分支依它擲出的檢定數展開，最壞是 2^N，由上限擋住。

## 3. 新舊比對

- **固定種子的隨機情境，舊實作與新實作的 `repr(PathPreview)` 逐筆相同**：
  - 腳本：`scratchpad/p7/compare_paths.py`，不 commit；
  - 1500 組（7×4 地圖、隨機冰／油／水／毒、1～2 個盜賊、0～2 個捕獸夾／毒坑，含隱藏的、隨機終點或隨機路徑）；
  - 其中 153 組有冰面分支或超過 2 個停點；
  - 改動前先跑一次存下雜湊，改動後再跑，`diff` 沒有差異。
- **commit 的測試** `test_path_preview_branches_match_the_legacy_branches`：
  - 在測試內重寫 6E-2b／6P-1 的舊分支清單（`_legacy_branches`）；
  - 用 `Rng` 產生的隨機情境比對至少 120 組（其中至少 20 組有冰面分支）；
  - 逐個分支比對事件與最終狀態，結果相同。
- 既有測試全過：`tests/engine`、`tests/api/test_path_preview_api.py`、`tests/test_architecture.py`，`-n 8`，改動後含新測試共 4209 個。
- 重播一致：`trpg battle --map swamp --seed 7` → `trpg battle replay`：「重播驗證通過：88 個動作、313 個事件，最終狀態一致」。

## 4. 測試

- 新檔 `tests/engine/test_branching.py`，11 個：
  - `CheckOverride` 在正式結算被擋，3 種覆寫：空的、全部最好、只限 `status_save`；
  - 覆寫的 d20 語意：`check_d20`／`opposed_d20`、種類與 reason 篩選、計數、`check_log`；
  - 確定性：預覽前後狀態與 `rng_state` 不變；同一輸入兩次預覽相同；預覽前後正式結算相同；
  - 非移動動作：**推人進冰面**，分支在被推者的 `surface` 檢定，倒地／不倒地都有；推擊本身視為成功；
  - **移動經過冰面與陷阱**：`slide` × `status_save` 的組合都在（過冰＋定身、過冰＋抵抗、滑倒）。舊的路徑預覽只分冰面；
  - **行為一致**：每個分支的單位位置與狀態、檢定結果序列，都有某個種子（0～199）的實際結算走得到。推人與冰面加陷阱兩個情境都測；
  - 分支上限：`limit=3` 截斷且與完整推演的前段相同、順序依最差次數，`limit=0` 只剩兩個極端；
  - 沒有分歧點的動作：`certain`、`low is high`；
  - 新舊路徑預覽一致（第 3 節）。
- `tests/engine/test_path_preview.py`：
  - `SlideOverride` 的兩個測試改用新 API，改名為 `test_check_rule_outcomes`、`test_check_override_is_preview_only`，斷言內容對應不變；
  - `test_slide_override_only_forces_slide_checks` 改用 `simulate_branch`，其餘不動。

## 5. 檔案清單

- `src/trpg/engine/context.py`：`CheckKind`／`CHECK_KINDS`／`CheckOutcome`／`CheckPoint`／`CheckRule`／`CheckOverride`；`Ctx.check_override`／`check_counts`／`check_log`；`check_d20(kind, reason, unit_id)`、`opposed_d20`。
- `src/trpg/engine/branching.py`（新）：`preview_action`、`ActionPreview`、`PreviewBranch`、`MAX_BRANCHES`。
- `src/trpg/engine/battle.py`：`simulate_slide_branch` → `simulate_branch`。
- `src/trpg/engine/path_preview.py`：建立在 `preview_action` 上；刪掉 `_slide_branches`、`_ALL_PASS`；`_SlideFailures` 改從推演取分支；模組說明更新。
- `src/trpg/engine/ice_slide.py`、`effects/handlers.py`、`control.py`、`maneuvers.py`：呼叫 `check_d20`／`opposed_d20`，帶種類與 reason。
- `tests/engine/test_branching.py`（新）、`tests/engine/test_path_preview.py`。

## 6. 檢查

- `ruff check`、`ruff format --check`、`mypy src`、`lint-imports`（13 kept）全過。
- 相關測試（`tests/engine`、`tests/api/test_path_preview_api.py`、`tests/test_architecture.py`，`-n 8`）：4209 passed（改動前 4198＋新增 11）。
- 沒跑全量。
- `tests/engine/test_path_preview.py:645` 有一個原本就存在的 mypy 錯誤（`PathEvent(other_id="e1")`，str 不是 `UnitId`）。這段沒有動到它，`mypy src` 不涵蓋 tests。

## 7. noqa

沒有新增 noqa。

## 8. 待 PM 決定

1. **`primary` 的推擊、絆倒不是覆寫點**：預覽照舊一律視為成功，成功率由 `preview.py` 另外算，所以 `preview_action` 不會有「推擊失敗」的分支。Phase 7 的確認卡如果要畫「推不動」的分支，要另外加 `CheckKind`（例如 `maneuver`）。這會改變一般預覽的分支數，這次先不做。
2. **`PathPreview` 沒有 `truncated` 欄位**：路徑預覽只分冰面，不會碰到上限；為了輸出完全不變，沒有加欄位。如果要讓前端知道，可以加 `truncated: bool = False`，API schema 也要跟著加。
3. **`MAX_BRANCHES = 64` 是原型數值**：每個分支一次完整模擬。Phase 7 確認卡的延遲預算確定後再調；也可以讓 API 傳較小的 `limit`。
4. **攻擊命中、傷害骰、`prompt` 反應、賭注仍只有 `min`／`max` 兩極**，沒有逐次展開。這些不是 `check_d20` 類的守方檢定，照規格不在這段範圍。
5. **計數範圍**：`kinds=("slide",)` 的計數包含所有單位的滑行檢定，與舊 `SlideOverride` 相同；舊的 N 只數移動者。移動中只有移動者會自己走進冰面，所以實際上一樣，隨機比對也沒有差異。`CheckRule` 目前不能依單位篩選，Phase 7 需要時可以加 `unit_id` 欄位。
