# Phase 3J-4c 報告｜解除形態原語＋解形爆發

規格：`docs/phases/Phase3J計畫.md` 4.14；設計：`docs/design/06-技能.md` 6.30「形態池名單」第 4 招。

## 做了什麼

1. **新原語 `leave_form`（解除形態）**：`content/skill_primitives.yaml`（`acts_on: caster`、`position: first`、`max_per_skill: 1`、`active_only`、`budget_basis: fixed`、`base_points: 0`）。
   - 引擎：handler（`engine/skills/primitives/statuses.py`）呼叫既有 `leave_form(ctx, unit, "released")`——照常換回武器與裝備、最大 HP 減回、該形態冷卻 2 回合、取消龍的蓄力。`FormLeaveReason` 多了 `released`；事件文字「解除了形態」。
   - 合法性：`skill_problem`（`_already_problem`）——不在形態中回 `只能在形態中使用：<技能名>`；AI、預覽、`resolve` 共用同一處，所以 AI 不在形態中不會選它。
   - 驗證器／LLM 提議／工坊：靠 `position`／`max_per_skill`／`active_only` 三個組合規則欄位同源（驗證器與提議模型都讀它們）；`area` 骨架的附帶原語加入 `leave_form`；工坊文字表多一筆 `原語.leave_form`（164 筆）。
   - 卡片：「只能在形態中施放：先解除你目前的形態（照常進入冷卻），再結算以下效果」；`narrative` 句子、`effect_summary` 的自身對象清單、預覽與 AI 覆蓋表（`ai/coverage.py`）都登記。
   - 關鍵字：`skill_keywords.yaml` 的 `form.uses` 加 `{effect: leave_form}`，使用它的技能是「形態」利用者。
   - 隨機組合器：`_HAND_WRITTEN_PRIMITIVES` 加 `leave_form`——**組合器不抽**。
2. **預算＝代價折抵**：`skill_budget.yaml` 新增 `allowance.leave_form_permille: 200`（初值，未經模擬）；`_allowance_parts` 在技能含 `leave_form` 時加一項「解除形態（先離開目前的形態）」，與其他代價加總、套整體上限。原語本身 0 點。
3. **解形爆發** `skill_form_release_burst`：2 階、epic、法術（體質）、2 AP、法力 8、ring 半徑 1、`leave_form` ＋ 3d6 物理傷害。預算比例約 85%（70～100% 內）。進形態池（非起始技能，因為 2 階）；放進 `build_form_user`（第 6 招）讓內容覆蓋測試通過。
4. `LOG_FORMAT` `/83` → `/84`（`runner.py` 文件字串與測試字面值一起改）；`skill_icons.json`、`glossary.json` 重產；CLI 快照更新；技能總數 300 → 301。

## 驗收對照

| 驗收 | 證據 |
|---|---|
| 不在形態中不能施放 | `tests/engine/test_form_release_3j4c.py::test_the_burst_cannot_be_cast_outside_a_form`（`skill_problem` 文字與 `IllegalActionError`） |
| 解除形態照常冷卻、之後傷害＝卡片 | `..._releases_the_form_with_the_usual_cooldown_then_hits_for_the_card_number`（`FormLeft(reason=released, cooldown=2)` 先於 `DamageDealt`；`form_cooldowns == {bear: 2}`；同形態冷卻中、別的形態可進入；傷害 ＝ (3d6 骰值 ×1000 ＋ 體質加成) ÷ 1000；只打周圍 1 格；之後不能再施放） |
| 算代價折抵 | `..._counts_as_a_cost_inside_the_budget`（折抵 200‰；拿掉 `leave_form` 後可用預算少 200‰；比例 70～100%） |
| 卡片 | `test_the_card_tells_the_requirement_and_the_cost` |
| 驗證器 | `test_the_validator_wants_leave_form_first_alone_and_on_active_skills`（必須第一個、最多一個、只限主動） |
| 關鍵字／池 | `test_the_burst_makes_a_form_exploiter_and_joins_the_form_pool` |
| AI | `test_the_ai_only_offers_the_burst_inside_a_form` |
| 重播 | `trpg battle --map open_plain --seed 9 --ally-build build_form_user` → `battle replay` 通過（98 動作、285 事件；解形爆發使用 3 次含 1 次實際解除） |
| ruff／format／mypy／lint-imports | 全過 |
| 測試 | `tests`（不含 cli）8334 全過（修完 4 項既有測試的字面值後）；`-m "slow or not slow" tests/cli` 全過（快照更新、預算數字 300→301） |

## 為了讓既有測試通過做的調整

`tests/content/test_skill_scaling.py`（301 招）、`test_skill_rules_content.py`（area 附帶原語）、`tests/skillgen/test_workshop_text_48f.py`（164 筆）、`tests/cli/test_budget_cli.py`（301）、LOG_FORMAT 字面值（`/84`，共 12 處）。

## 複雜度 noqa

沒有新增。

## 待 PM 決定

1. **`in_form` 允許清單沒有刪**：規格寫「解形爆發用 `in_form` 條件時刪掉」。我用 `leave_form` 原語自己擋「只能在形態中施放」（`skill_problem`），沒有用 `in_form` 條件，所以 `tests/content/test_coverage.py` 的 `in_form` 允許清單仍需要（只改了理由文字）。若要讓條件被手寫技能使用，需另案（例如技能層級的「施放條件」欄位）。
2. **「只能在形態中施放」是 `leave_form` 原語的內建行為**（含 `leave_form` 的技能一律如此），而不是獨立的施放條件欄位。
3. **折抵 200‰ 與傷害 3d6 為初值**（比例約 85%），未經模擬。「較高傷害」目前相對於野性怒吼（2d4 ＋30%）；請玩法 PM 看是否要調。
4. **解形爆發對自身冷卻**：只有被解除的那個形態冷卻 2 回合，技能本身沒有冷卻（可在形態間輪替再用）；要加技能冷卻需調傷害或折抵。
5. **預覽（preview）不列「解除形態」結果**（`FormLeft` 沒有對應的預覽結果型別；其餘傷害照常）。若前端預覽要顯示，需新增結果型別與前端文字。
6. **工坊／LLM 提議同源開放**：`leave_form` 可被放進 `area` 骨架的任何主動技能（第一個效果）；組合器不抽。工坊玩家文字是實作者初稿，待玩法 PM 改寫。
7. **解形爆發放進 `build_form_user`**（第 6 招），模擬回歸範本因此多一招；若不想改範本，可另開一個專用 build。
8. **`LOG_FORMAT` `/84`**：與同時進行的 3R-2b 可能撞號，合併時由 PM 決定最終編號與文字。
9. **工具提醒**：這個 worktree 的 `.venv` 是空的，需 `uv sync --offline` 才能跑；Bash 的 `python` 是 Windows Store 假指令，一律 `uv run python`。
