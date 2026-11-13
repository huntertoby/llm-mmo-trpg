# Phase RG-5b 完成報告（掩護高度改回半掩護、連擊點一律「點」）

依據：`docs/玩法PM交接.md` 4.1.7（玩法 PM 定，不用問使用者）；背景 `docs/phases/PhaseRG-5報告.md` 第 4 節與「CLI 快照補充」。開工時 worktree 已快轉到 main `904f1f894`（含 187402527 與玩法 PM 的 4.1.7）。

## 1. 做了什麼

### 1.1 高度改回半掩護（4.1.7 第 1 條）
- `engine/rules/combat.guard_blocks`（盾兵、盾陣共用）：回到 RG-4 的判定。掩護算 1 層高，攻擊者比持盾者高 2 層以上才無視（`attacker_h > guard_h + 1`）；目標比持盾者高 2 層以上擋不到（沒變）。
- `combat._shield_cover`（塔盾本體）：從「攻擊者比你高 1 層就無視」改成「比你高 2 層以上才無視」（`attacker_h > target_h + 1`）。4.1.7 寫明塔盾本體也照半掩護。**這條不是撤回，是新改的**：3I-2 起一直是「高 1 層」。
- 塔盾卡片字（`content/battle.py` 的 `OffhandDef` 特性行）：「攻擊者站得高 1 層以上時無視」改成「攻擊者站得比你高 2 層以上時無視」。`content/offhands.yaml` 的註解一起改。
- 效用 AI 的盾兵站位估值（`ai/utility/position._screened_allies`）呼叫 `guard_blocks`，所以跟著回到 RG-4 的估值。
- 半掩護物件本來就是這條判定，沒有改。

### 1.2 物品名（4.1.7 第 2 條）
- 維持「塔盾」，沒有改。

### 1.3 連擊點一律「點」（4.1.7 第 3 條）
都改成照 `StackDef.unit_zh` 取單位。預設「層」的輸出逐字不變。
- `narrative/skills.py::_stack`：斷喉、連擊終結的「每層使本技能傷害 +20%」改成「每點」；`add_stack` 的「累積 1 層「連擊點」」改成「1 點」；`cost.stacks` 的「至少 N 層才能施放」也照單位。
- `narrative/skills.py::_overload_text` 與 `scale: stacks` 的「層數」：照單位（目前只有「層」的層數會走到，輸出不變）。
- `narrative/status_info.py`（名詞表的層數規則）：連擊點的「最多 5 層」「武器技命中時 +1 層」「技能每層提高傷害」改成「點」。自動消耗與超載的句子也照單位。
- `narrative/events.py` 的超載行：照單位（輸出不變）。
- `content/skills/skill_throat_cut.yaml`、`skill_combo_finisher.yaml` 檔頭註解的「每層」改成「每點」（只是註解，不進規則包）。
- 手寫技能沒有自己的說明欄。斷喉、連擊終結的卡片字都是 `narrative/skills.py` 組出來的，所以上面這處改完就全部涵蓋。

### 1.4 測試
- `test_shield_guard_rg1.py`：「高 1 層無視」改成「高 1 層仍擋」，另外新增一條「大家站 1 層、攻擊者 3 層無視、2 層仍擋」（比的是盾兵不是目標）。
- `test_tower_formation_rg4.py`：高 1 層改回擋得到。
- `test_offhands.py` 塔盾表：「攻擊者高 1 層」從 0 改成 −2，另外新增「高 2 層」為 0。
- `test_stack_expansion.py`：連擊終結要有「每點」、斷喉不能有「每層」。名詞表的「消耗：技能每{單位}提高」照各層數的單位檢查，而且連擊點的規則句不能出現「層」。

## 2. 預測與實際（預測都在跑之前寫下）

| 項目 | 預測 | 實際 |
|---|---|---|
| 不變比對（改前＝`904f1f894`，改後＝這段；8 張地圖 × 種子 1、2，加上 3 張頭目圖 `molten_heart_pit`、`rift_gate`、`cloud_summit` × 種子 3～12；效用 AI、`max_rounds=30`；比對整份事件、步驟、最終狀態，去掉內嵌的 `ruleset`） | 地圖預設陣容沒有盾兵、沒人帶塔盾或盾陣；事件本身不帶敘事文字 → `different=0`，事件數同 RG-5 的 20499 | `battles=46 events=20499 different=0` |
| 一場重播（open_plain 種子 7） | 通過 | 「重播驗證通過：91 個動作、383 個事件，最終狀態一致」 |
| CLI 快照（`tests/cli -m slow`） | 戰鬥 7 鍵不變（沒有盾兵、塔盾、連擊點技能）。技能類有 6 鍵會變：`skills_list`，以及 `skills_show_all/01`（連擊終結）、`/03`（連環快刺；連影斬只有條件行，條件行 RG-5 已經是「點」）、`/10`（掠影步）、`/12`（疾刺）、`/13`（斷喉）。分片是事前用快照測試的切法算出來的。 | 正好這 6 鍵失敗（966 passed）。`skills list` 逐行 diff 只有 5 行「層」→「點」。只重產這 6 鍵，重跑 `tests/cli -m slow` 44 passed，`tests/cli` 非 slow 148 passed |
| parity（`tests/skillgen/test_refactor_parity.py`，slow） | 0 變。parity 雜湊的是技能強度、升階、閃現的 JSON，不含卡片文字，也不含高度 | 全過（和 CLI slow 同一次執行） |
| `glossary.json` 測試替身 | 只有 `combo_point` 的 3 行規則句「層」→「點」 | 同預測（+3／−3）；`skillCards.json`、`unitDolls.json`、`raceLooks.json` 重產後不變 |
| `openapi.json`、`schema.d.ts` | 不變（`OffhandDef` 的 docstring 不在 API schema 裡） | 前端沒有這段文字；沒重產 |

## 3. 版號說明

- **`LOG_FORMAT` `/124` → `/125`**：盾兵、盾陣的高度改回半掩護，塔盾本體改成半掩護。同樣的規則包與步驟，攻擊者比目標高 1 層時結算會不同。事件、狀態的欄位沒有增減；連擊點的文字只是顯示，不影響重播。`/124` 的紀錄無法重播。
  - 同步了 9 處寫死字串：`tests/cli` 6 檔 7 處、`test_gear_g2.py`、`test_gear_g3a.py`。
  - 同步了 3 個 `endswith`：`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py`。
  - `docs/phases/戰鬥紀錄格式變更.md` 加了 `/125` 一條。
- **`WORLD_RULES_VERSION` 維持 33**：`trpg.world` 的程式沒改。世界日誌的規則鍵（`world/save.log_rules_key`）是「戰鬥紀錄版號|w世界規則版號|規則包雜湊|內容 digest」，本來就含 `LOG_FORMAT`，所以 `/124` 的舊日誌照樣會標成規則已變、不能重播。`world/save.py` 的版本說明加了 RG-5b 一段，寫明這個理由。
- 日誌、角色、世界的格式都沒變。

## 4. 檢查結束碼

- `ruff check .` 0、`ruff format --check .` 0、`mypy` 0（1598 檔）、`lint-imports` 0（14 kept）、`trpg content check` 0。
- 相關 pytest：
  - 引擎、技能產生、敘事、API、內容、世界等相關檔，共 663＋518＋178 passed。
  - `tests/cli` 與 `test_refactor_parity.py` 的 slow：第一次正好是預測的 6 鍵失敗；重產後 `tests/cli -m slow` 44 passed。
  - `tests/cli` 非 slow 148 passed。
- 沒有跑全量 `check.py`，也沒有跑前端（前端只有 `glossary.json` 測試替身改了 3 行，vitest 沒有斷言這些字）。

## 5. Commit

| commit | 內容 |
|---|---|
| `a2acc90ce` | 高度改回半掩護（盾兵、盾陣、塔盾本體）、連擊點單位、`LOG_FORMAT` `/125`、測試、`glossary.json` |
| `dd33701d6` | CLI 快照只重產預測的 6 鍵 |
| （本報告的 commit） | 報告、上手筆記（引擎 45 修正、新增 46） |

## 6. 待 PM 決定

1. **08 8.11 塔盾表那一列還寫「攻擊者高 1 層以上照樣無視」**（`docs/design/08-裝備.md` 第 199 行）。同一節的盾陣那點（第 208 行）已經更正成「高度照半掩護……敵方盾兵、塔盾本體都一樣」，程式照 4.1.7 與第 208 行做。第 199 行的字要不要由玩法 PM 一起改（設計文件不是開發改的）。
2. **前端充能字寫死「層」**（`client/src/battle/charges.ts`、`targeting.ts` 的「3 層＋1 AP」）：目前能當裝備充能的層數只有靜電、怒氣，連擊點還不行，所以這次沒有改。以後若有連擊點的充能詞條，要改成照單位。
3. **技能產生器、工坊的欄位名「每層加成」**（`skillgen/player_text.py`、`option_params.py`、`tuning_fields.yaml`）：這是不分層數的通用欄位名，沒有改。

## 7. 平衡疑慮

- 沒有。4.1.7 已說明「高 1 層就無視」的疑慮不成立。塔盾本體從「高 1 層無視」改成「高 2 層」，對持塔盾的玩家略有利，但這是 4.1.7 定的規則。

## 開發 PM 裁定

- 接受，已合併。高度條件改回半掩護判定，塔盾本體一起照 4.1.7 改。不變比對 46 場相同；CLI 快照只重產預測到的 6 鍵；LOG_FORMAT 升到 /125。
- 待 PM 決定 1：請玩法 PM 改 08 第 199 行。2、3 照現況維持。
