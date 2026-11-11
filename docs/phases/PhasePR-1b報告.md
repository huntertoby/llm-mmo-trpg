# Phase PR-1b 完成報告｜#147 測試模式引擎修正

> 規格：`docs/phases/PhasePR-1b計畫.md`；來源：`docs/design/21-探索地圖與城鎮.md` 21.5 測試模式第 6 點。前置：`docs/phases/PhasePR-1報告.md`。基準：本機 `main`（`26916cbb`，引擎與 `29252e19` 相同，只多文件）。

## 1. 半成品的處理

前一位實作者被中斷，留下未 commit、未驗證的改動（+271／−13）。處理方式：

- 先原樣 commit 成 `97a5744f`（WIP from interrupted agent），再 `git merge main`（`0f5f0739`，只多文件，無衝突）。
- 逐段對照規格 3 項後 **全部沿用，沒有重寫**：三項的實作與測試都已齊全，做法與 PR-1 既有結構一致，跑起來 54 個測試全過。
- 我補的只有兩處超過 100 字的行（`ruff E501`）：`triggers.py::_practice_home` 的說明字串拆成兩行（順便寫明「最近」的排序規則）、測試檔一行分隔註解縮短。沒有改任何行為。
- 既有測試只動了一行匯入（`from trpg.engine.actions import ...` 多匯入 3 個動作），PR-1 的 31 個測試斷言一個都沒改。

## 2. 做了什麼

| 項目 | 改動 |
|---|---|
| 1. 灌注、啟動充能、指揮算放招 | `practice.py::PASS_ROUND_ACTIONS` 加 `infuse_skill`、`activate_charge`、`command_summon`。過輪仍走 PR-1 的 `practice_pass_round`（`resolve_with` 的 `try` 內），預覽不過輪。推撞、絆摔、走路、跑步不在集合內。 |
| 2. 主角進致命地形 | `practice.py` 新增 `is_practice_protected`（主角或木樁）；`begin_battle` 的 `practice_homes` 改記主角與木樁；`triggers.py::_deadly_terrain` 對兩者都走 `_practice_home`（HP 補滿、`teleport` 回開場位置）。召喚物不算主角，照一般規則。 |
| 3. 裝備充能補滿 | `turns.py::_refill_practice_charges`，由 `_refill_practice_heroes` 在每次結算收尾呼叫：身上生效的充能詞條補到裝備版上限 `min(affix.max_stacks, 層數定義的 max)`，只補不減，會過期的層數同時刷新到期輪數。AP 補到 `ap_cap`（4）沒有動。 |

**「最近的空格」的確定性規則**：沿用既有的 `rules/landing.py::nearest_free`——曼哈頓距離最小，同距離依 `y` 再依 `x` 由小到大；不用亂數、不依賴 `set` 順序。開場位置自己變成不能站（例如橋燒掉）時也走同一條規則。整張地圖都沒有空格時留在原地（HP 仍補滿）。

`LOG_FORMAT`、`WORLD_RULES_VERSION`、API、`world/`、前端、`content/`、CLI 快照都沒有動。沒有新增 `# noqa`。

## 3. 逐條驗收

| 條件 | 結果 | 證據 |
|---|---|---|
| 灌注、啟動充能、指揮會過輪；沒旗標時不過輪 | 通過 | `test_infuse_command_and_charge_count_as_casts`（3 動作 × 有無旗標 6 格） |
| 灌注在召喚物下回合真的放出來 | 通過 | `test_infusion_is_released_on_the_summons_next_turn` |
| 灌注、指揮下一輪能再做 | 通過 | `test_infuse_can_be_repeated_every_round`、`test_command_can_be_repeated_every_round` |
| 這三個動作的預覽不過輪 | 通過 | `test_preview_of_infuse_command_and_charge_does_not_pass` |
| 推撞、絆摔、走路、跑步仍不過輪 | 通過 | PR-1 的 `test_basic_actions_do_not_pass_the_round[move/run/shove/trip]`（未改） |
| 主角、木樁進致命地形回開場位置並補滿；開場位置被占用回最近空格 | 通過 | `test_deadly_terrain_sends_home_and_refills`（主角／木樁 × 空著／被占 4 格；被占時落在 (1, 0)） |
| 開場位置只在有旗標時記；召喚物不受保護；沒旗標主角照死 | 通過 | `test_hero_home_is_recorded_only_with_the_flag`、`test_summon_is_not_protected`、`test_no_flag_hero_dies_in_deadly_terrain` |
| 裝備充能開場就滿、任何動作後補滿、啟動後仍滿可再啟動 | 通過 | `test_charges_are_full_from_the_opening`、`test_charges_are_full_after_any_action`、`test_activating_a_charge_leaves_it_full_and_repeatable` |
| 充能只補不減；沒旗標不補；沒有充能詞條不多出層數 | 通過 | `test_charge_refill_never_lowers_stacks_from_other_sources`、`test_no_flag_charges_are_not_refilled`、`test_hero_without_charge_affixes_gains_no_stacks` |
| AP 補到 4 維持 | 通過 | PR-1 的 `test_every_resource_is_full_after_an_action`（未改） |
| PR-1 既有測試不放寬 | 通過 | 斷言未改；`tests/engine/test_practice_mode.py` 54 passed（原 31 ＋ 新 23） |
| `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` | 通過 | All checks passed／2272 files already formatted／no issues in 1426 files／14 kept, 0 broken |
| `tests/engine`、`tests/test_architecture.py` | 通過 | `uv run pytest -q tests/engine tests/test_architecture.py -n 8 -x`：4378 passed |
| `tests/cli` 帶 `TRPG_FULL=1 -m "not llm"` | 通過 | 192 passed，退出碼 0 |

依守則 11，沒有跑 `scripts/check.py` 全量、`tests/sim`、`tests/api` 與大型模擬（**沒驗證**；本段沒有改這些目錄用到的介面）。

## 4. 實戰不變的比對

- **基準的取得**：`git archive main src content | tar -x -C <暫存資料夾>/base`，取得改前的原始碼與內容；以 `PYTHONPATH=<暫存資料夾>/base/src uv run python dump_events.py` 執行，腳本把 `trpg.__file__` 寫進輸出，確認基準那次載入的是暫存資料夾的 `trpg`、改後那次載入的是 worktree 的 `trpg`。腳本放在 worktree 外的暫存資料夾，未 commit。
- **跑法**：`trpg.sim.batch.map_spec`（地圖預設陣容、效用 AI）＋ `trpg.engine.runner.run_battle`，`practice=None`（腳本內有 `assert`）。
- **範圍**：12 張地圖（`open_plain`、`bandit_lair`、`bridge_chasm`、`frozen_lake`、`lava_crossing`、`swamp`、`ruined_fort`、`oil_depot`、`cliff_outpost`、`dark_forest`、`narrow_halls`、`molten_heart_pit`）× 2 個種子（7、20261111）＝ 24 場。
- **比對內容**：`BattleLog` 轉 JSON 後的事件列表（逐筆）、步驟列表、最終狀態（含 `rng_state`）；只排除 `format` 字串。
- **結果**：`battles=24 events=6992 different=0`，24 場每一場的事件數相同、逐筆相同、沒有第一個差異位置。
- **涵蓋的限制**：這 24 場有 `entered_deadly_terrain` 11 次、`unit_downed` 115 次，所以致命地形那條分支在實戰下有實際走到；但預設陣容沒有裝備充能、召喚、灌注（`charge_activated`、`summon_commanded`、`infused_skill_cast`、`stacks_changed` 都是 0 次）。這三類在沒旗標時不變，是靠單元測試確認（`test_infuse_command_and_charge_count_as_casts[no_flag]`、`test_no_flag_charges_are_not_refilled`），不是靠這份整場比對。

## 5. 待 PM 決定

1. **充能補滿不發事件、不算超載**：直接寫層數，不走 `add_stacks`，所以沒有 `stacks_changed`，也不會觸發超載反噬。和 PR-1「資源補滿不發事件」一致，畫面讀結算後的狀態。若靶場要看得到超載，需另外定。
2. **充能補到裝備版上限**（`max_stacks`），不是層數本身的上限；技能另外疊上去、超過裝備版上限的層數保留不動。
3. **只補身上生效中的充能詞條**用的層數；主角技能自己的層數（非裝備充能）不補，21.5 沒列。
4. **整張地圖沒有空格時**，進致命地形的主角或木樁留在原地、HP 補滿（不倒下）。實際的靶場地圖不會發生。
5. **主角回位用 `teleport`**，發的是一般的 `unit_moved`；不退還這次被推走前已花的移動點數（收尾會補滿，所以沒差）。
6. **每輪反應次數（`reactions_used`）仍不補**：PR-1 報告第 9 點留下的項目，規格這次只列裝備充能，維持一般規則（新一輪重設）。指揮與灌注的每輪計數靠過輪重設，不另外清。
