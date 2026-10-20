# Phase 3-7 報告｜體質與升級 HP

> 規格：`docs/phases/Phase3計畫.md` 第 10 節。分支 `worktree-agent-a3cce7eb159aa40b2`。`scripts/check.py` 全過（ruff、format、mypy、lint-imports、pytest、client typecheck／test），`corepack pnpm -C client build` 成功。

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| `feat: derive max HP from constitution and migrate unit templates` | 引擎公式、係數進 `core.yaml`、內容遷移（`scripts/migrate_con_hp.py`）、`bleed`／`poison` 加 `save_attr: con`、相關測試 |
| `feat: roguelite max HP grows with constitution and level` | `RunState.max_hp_in(core)`、升級／配點同步加目前 HP、戰鬥中主角的等級加成、新測試 |
| `style: wrap long line in run CLI` | ruff E501 |
| `feat: show constitution HP preview in run UI and expose coefficients in API` | API 欄位、前端預覽、OpenAPI／型別重新產生、vitest |
| 本報告 | `docs/phases/Phase3-7報告.md` |

設計重點：

- **公式**（`CoreRules.max_hp_for`）：`max(1, 基礎 + (體質 − hp_con_base) × hp_per_con_point)`。係數 `hp_con_base: 10`、`hp_per_con_point: 3`、`level_hp_permille: 50` 在 `content/rules/core.yaml`（必填欄位，沒有程式內預設）。敵我同一公式，在 `engine/lifecycle.make_unit` 一處計算；`UnitState.max_hp`、`hp`、視圖、`battle_result`、治療上限、百分比門檻都讀這個值（其餘讀 `max_hp` 的地方本來就讀 `UnitState.max_hp`，沒有再讀範本的）。召喚物預覽（`engine/preview.py`）、技能說明文字（`narrative/skills.py`）、`/api/builds` 的 `max_hp` 改用 `core.template_max_hp(template)`。
- **roguelite**：`RunState.hero.max_hp` 是「基礎 HP」，不隨升級與配點改變。`RunState.max_hp_in(core)` ＝ `max_hp_for(基礎 + 基礎 × 50‰ ×（等級−1），體質)`。戰鬥時 `battle_setup` 把等級加成併入主角範本的基礎 HP，再由引擎加體質，所以戰鬥中的最大 HP 與 `max_hp_in` 恆相等（測試 `test_the_battle_hero_has_the_runs_max_hp`）。升級進入升級節點時、升級配點送出時，用 `progress.with_hp_change` 讓目前 HP 增加相同的量（減少時不低於 1）。
- **開局 HP 不變**：`new_run` 把主角的基礎 HP 設為 build 英雄「以自己的體質算出的最終 HP」（即遷移前的數字），屬性仍是全 10 再加配點，所以不配體質時起始 HP 與遷移前相同（60／40／46…），配體質才增加。這是對規格 10.1 B「不改現有平衡」的解讀，見「待 PM 決定」1。
- **存檔格式不變**（仍 `trpg-run/1`）：最大 HP 由既有欄位（`hero.max_hp`、`hero.attributes`、`level`）算出，沒有新欄位。舊存檔可讀：舊檔的 `hero.max_hp` 恰好就是新語意的基礎 HP，讀檔後最大 HP 因舊的體質配點與等級而變大，目前 HP 不變（下次營火回滿）。戰鬥中的存檔本來就會因內容雜湊不符被拒絕。
- **API／前端**：`HeroOut` 加 `hp_per_con_point`、`hp_con_base`，`RunRules` 加 `hp_per_con_point`；`AttributeAllocator` 在體質列即時顯示「最大 HP ＋N HP」（開局與升級畫面都用，開局畫面的主角 HP 也隨配點變化），主角面板的體質旁顯示目前加成（例如「＋12 HP」）。

## 2. 驗收條件逐條

| # | 結果 | 證據 |
|---|---|---|
| 1 | 通過 | 係數在 `content/rules/core.yaml`（`test_coefficients_come_from_yaml`）；體質 8／10／14 的最大 HP：`tests/content/test_con_hp.py::test_max_hp_by_constitution`（基礎 60 → 54／60／72）與 `test_engine_unit_hp_uses_constitution`（引擎建立的單位，基礎 40 → 34／40／52）；下限 1：`test_max_hp_floor_is_one`；敵方同公式：`test_enemies_use_the_same_formula` |
| 2 | 通過（見下） | `test_migration_keeps_every_template_final_hp`：44 個範本（22 個單位與召喚物範本、22 個 build 英雄）的最終 HP 與遷移前寫死的對照表完全相同。`trpg battle`：把中毒／流血的 `save_attr` 暫時拿掉，6 張地圖（open_plain、bandit_lair、swamp、frozen_lake、training_range、dark_forest，種子 7）的 `--log-json` 動作列表與事件列表和遷移前逐項相同（只有 `setup` 內嵌的範本基礎 HP 與規則多了三個係數不同；`LOG_FORMAT` 未改）。CLI 輸出快照在這個狀態下也不需更新。 |
| 3 | 通過 | `tests/engine/test_status_control.py::test_bleed_and_poison_are_resisted_with_constitution`（兩種狀態：`StatusSaveRolled.save_attr` 是體質、防禦值等於守方體質、抵抗成功不施加／失敗施加）；`test_statuses_content.py` 的規格表 |
| 4 | 通過 | `tests/roguelite/test_hp_growth.py`：`test_level_up_raises_max_hp_and_current_hp_by_the_same_amount`、`test_level_up_allocation_to_constitution_raises_max_and_current_hp`、`test_level_up_without_constitution_keeps_current_hp`、`test_allocating_constitution_at_the_start_raises_the_starting_hp`、`test_a_decrease_never_drops_current_hp_below_one`、`test_the_battle_hero_has_the_runs_max_hp`、`test_save_and_load_keep_max_and_current_hp`（存檔 → 讀檔一致） |
| 5 | 通過 | `client/src/run/hpPreview.test.ts`（純函式、配點時渲染出「最大 HP ＋6 HP」、不配體質時不顯示、主角面板「＋12 HP」）；`tests/api/test_runs_api.py::test_rules_and_hero_expose_the_hp_per_constitution_point`；`corepack pnpm -C client build` 成功；`uv run python scripts/check.py` 全過 |
| 6 | 通過 | 下方對照表 |

「`trpg battle` 差異從哪一步開始」：加上中毒／流血的體質抵抗之後，各地圖在第一次施加流血時開始不同（事件從 `status_applied` 變成多一筆 `status_save_rolled`，之後的骰序與戰況跟著分岔）。種子 7 的各圖第一個差異事件序號：open_plain #156、bandit_lair #99、swamp #41、dark_forest #38（open_plain、swamp 是施加流血多了抵抗判定；bandit_lair、dark_forest 是 AI 因流血機率改變而選了不同動作）；frozen_lake、training_range 整場沒有用到流血，事件完全相同。

## 3. 前後對照表（`trpg run auto`，種子 1～10，AI 代打，不調數值）

「到達場數」＝最後的 `結果` 行 `N/6`（打贏的場數）。

| 種子 | 之前：結果 | 之前：場數 | 之後：結果 | 之後：場數 |
|---|---|---|---|---|
| 1 | 失敗 | 2/6 | 失敗 | 4/6 |
| 2 | 失敗 | 2/6 | 失敗 | 2/6 |
| 3 | 失敗 | 5/6 | **勝利** | 6/6 |
| 4 | 失敗 | 3/6 | 失敗 | 3/6 |
| 5 | 失敗 | 4/6 | 失敗 | 4/6 |
| 6 | 失敗 | 5/6 | **勝利** | 6/6 |
| 7 | 失敗 | 2/6 | 失敗 | 5/6 |
| 8 | 失敗 | 5/6 | 失敗 | 4/6 |
| 9 | 失敗 | 2/6 | 失敗 | 3/6 |
| 10 | 失敗 | 2/6 | 失敗 | 2/6 |
| 合計 | 勝 0／10 | 平均 3.0 | 勝 2／10 | 平均 3.9 |

差異來源只有兩個：升級帶來的最大 HP（每級 ＋基礎 HP 的 5%，例如 40 HP 的主角 Lv2 +2、Lv5 +8），以及中毒／流血可被抵抗（改變骰序，所以即使 HP 相同的種子也會分岔）。AI 代打的配點全部加在技能最常用屬性，不會加體質。樣本只有 10 局，只供參考。

## 4. 複雜度 noqa

沒有新增或移除。noqa 總數前後相同。

## 5. 修改既有測試期望值（逐一列出原因）

- `tests/engine/helpers.py::template(...)`：覆寫 `max_hp` 時，測試寫的數字視為「最終 HP」，helper 自動扣掉體質加成（基礎 HP 至少 1，扣不掉時改用中性體質 10）。原因：絕大多數引擎測試用 `template(..., max_hp=N)` 表示「這個單位有 N 點 HP」（墜落傷害、撞擊、擊倒觸發…共約 25 個測試），公式上線後這個語意會因敵人體質 12 而偏移。
- `tests/engine/test_passive_triggers.py::scene`：`enemy.model_copy(update={"max_hp": foe_hp})` 繞過 helper，改成傳給 `no_reactions(max_hp=...)`，原因同上。
- `tests/content/test_sim_builds.py::test_standard_enemies_follow_the_tier_budget_hp_formula`：比對 `core.template_max_hp(enemy)`（最終 HP）而不是範本基礎 HP，原因：範本基礎 HP 已扣掉體質加成，預算公式針對的是最終 HP。
- `tests/api/test_run_autosave.py::test_builds_give_hp_mana_and_weapon`：`/api/builds` 的 `max_hp` 是最終 HP（`template_max_hp`），原因同上。
- `tests/api/test_run_autosave.py::test_rules_endpoint_gives_start_points`：`/api/runs/rules` 多了 `hp_per_con_point`。
- `tests/content/test_statuses_content.py`：`bleed`、`poison` 的 `save_attr` 期望值由 `None` 改為 `Attribute.CON`（規格 10.2 第 3 點）。
- `tests/engine/test_status_control.py`：兩個「沒有 `save_attr` 的狀態命中即施加」測試原本用 `bleed`，改用仍沒有 `save_attr` 的 `burning`（`test_statuses_without_save_attr_apply_on_hit`、`test_preview_omits_statuses_without_a_save`）；另新增 bleed／poison 抵抗測試。
- `tests/engine/test_status_determinism.py::test_same_seed_same_battle_and_replay_with_the_new_statuses`：種子 `(3, 7)` 改為 `(7, 10)`。原因：流血被體質抵抗之後，種子 3 的戰鬥不再出現 `bleed` 被施加；新的種子 7、10 合起來涵蓋 stun／poison／vulnerable／bleed 與抵抗判定、跳過回合。
- `tests/cli/test_striker_trapper_battle.py::test_striker_battle_...`：種子 1 → 57。原因：該戰鬥在種子 1 不再施放「雷霆終結」（流血抵抗改變骰序）；57 是掃過 1～99 後第一個仍符合原本斷言的種子。
- `tests/cli/snapshots/cli_output_hashes.json`：`battle_default_flat_42`、`battle_frozen_lake_push_3` 兩個雜湊更新（原因：放血斬施加流血的抵抗判定；已用「暫時拿掉 `save_attr`」確認 HP 遷移本身不改變任何一個快照）。
- `tests/roguelite/test_progress.py`（3 處）、`tests/roguelite/test_start.py`、`tests/api/test_runs_api.py::test_finished_battle_writes_back_and_levels_up`：贏第一場後升到 2 級，目前 HP 比戰鬥結束時多一個等級加成；開局配體質 1 點，起始 HP 多 3；`run.max_hp` 屬性改為 `run.max_hp_in(core)`。

## 6. 新增檔案

- `scripts/migrate_con_hp.py`：一次性遷移（`--dry-run` 預覽；只能跑一次）。逐檔把 `max_hp` 減去（體質−10）×3，保留註解與換行。已執行，輸出的變更見 commit。
- `tests/content/test_con_hp.py`、`tests/roguelite/test_hp_growth.py`、`client/src/run/hpPreview.test.ts`。

## 7. 待 PM 決定

1. **roguelite 起始 HP 的解讀**：規格 10.1 B 說不改現有平衡，但 roguelite 的主角是「全部屬性 10 ＋ 配點」，若直接用遷移後的基礎 HP，體質 14 的 build（戰士型）起始 HP 會從 60 掉到 48。我讓 `new_run` 以「build 英雄用自己體質算出的最終 HP」當基礎（仍是 60），所以不配體質時起始 HP 與遷移前一致。若 PM 希望的是「體質 10 的戰士型就是 48」，只要改 `new_run` 一行。
2. **舊存檔不拒絕**：`trpg-run/1` 沿用，舊存檔讀得進來，最大 HP 會因舊的體質配點與等級而變大（目前 HP 不變）。若要嚴格，改成 `/2` 並拒絕舊檔。
3. **升級加 HP 的時機**：進入升級節點（等級 +1）時就加，配點時再加體質部分；兩者都同步增加目前 HP。
4. **等級加成取整**：基礎 × 50‰ ×（等級−1）整體向下取整（例如基礎 40，Lv2＝2、Lv3＝4）；基礎 46 的 Lv2＝2（不是 2.3 的進位）。基礎低的 build 升級 HP 偏少，是否要設下限（每級至少 +N）。
5. **只有體質數值（`attributes`）影響最大 HP**：戰鬥中的暫時屬性加成（例如「激昂」狀態 +2 全屬性）不改最大 HP，避免戰鬥中途最大 HP 浮動。
6. **召喚物也適用公式**：召喚物範本的體質為 10～12，已一併遷移，最終 HP 不變。
7. **中毒／流血抵抗對平衡的影響**：流血、中毒現在有被抵抗的機率（守方體質高的單位更難中），依賴這兩個狀態的 build（放血斬、毒雲等）會略弱；完整矩陣未重跑（規格要求不跑）。
8. **`trpg run auto` 兩場勝利**（種子 3、6）：主要來自升級加 HP。AI 代打不配體質，所以沒有反映「玩家配體質」的強度；建議試玩時留意體質是否太強或太弱（每點 +3 HP ≈ 戰士型 +7.5%）。
