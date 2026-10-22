# Phase 3-26a 完成報告：技能點與技能等級

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3計畫.md` 28.1、`docs/design/06-技能.md` 6.28。
> 分支：`worktree-agent-a5575a9d248e47bbf`（從 main 的 `61fd5b3` 分出），未 push、未合併。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `5d5547a` | `content/skill_growth.yaml` ＋ schema；引擎的技能等級（單位資料、+10%、5 級小特性）；一輪的技能點、等級、備用技能、花點／重配／換裝；存檔 `trpg-run/4`；`LOG_FORMAT` `/44`；測試 |
| `9188813` | API（技能卡 `growth`、`HeroOut.skill_points／skill_growth／bench`、`UnitView.skill_levels`、新選擇種類）、CLI 顯示、OpenAPI 重產、API／CLI 測試 |
| `99cc10f` | 前端：技能點分配、Lv 標籤、營火免費重配與換裝、技能列 Lv 標籤、vitest |
| `fd97fea` | 截圖 `docs/phases/img/3-26a-*.png` |
| （本報告） | `docs/phases/Phase3-26a報告.md` |

## 2. 驗收逐條

| # | 驗收項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 點數取得（每級 2 點，數值在 `content/`） | 通過 | `content/skill_growth.yaml`（`points_per_level: 2`）；`tests/roguelite/test_skill_growth.py::test_a_new_run_has_no_points_and_every_level_up_gives_two`；`tests/content/test_skill_growth_content.py` |
| 2 | 升級（每級花 1 點、1～5 級、不合法被拒、狀態不變） | 通過 | `test_spend_points_raises_levels_for_one_point_each`、`test_spend_points_rejects_bad_requests_and_leaves_the_run_unchanged`（點數不足、降級、超過 5 級、沒裝備、被動）、`test_spend_can_ride_along_with_the_level_up_choice` |
| 3 | 2 級、4 級 +10%（整數千分比、無條件捨去）；3 級只計等級 | 通過 | `tests/engine/test_skill_levels.py::test_damage_levels_two_and_four_add_ten_percent_each`（傷害倍率 1000→1100→1200，3 級同 2 級）、`test_heal_and_shield_scale_too`、`test_heal_multiplier_applies_to_a_wounded_ally`、`test_only_active_skills_get_the_effect_bonus` |
| 4 | 5 級小特性與 6.6 上限 | 通過 | `test_level_five_trait_picks_area_when_the_shape_can_grow`（範圍 +1，4 級還沒有）、`test_level_five_area_trait_is_capped_by_the_shape_maximum`（形狀最大值；範圍滿了改減冷卻；都做不到就沒有）、`test_level_five_trait_falls_back_to_cooldown_minus_one`、`test_the_reduced_cooldown_is_what_the_cast_sets` |
| 5 | 卸下保留等級 | 通過 | `test_unequipped_skills_keep_their_levels_and_can_be_equipped_again`、`test_replacing_a_skill_sends_it_to_the_bench_with_its_level` |
| 6 | 營火重配（免費、全部退回）與換裝 | 通過 | `test_respec_refunds_every_point_for_free`、`test_loadout_rejects_unknown_duplicate_and_overfull_equipment`、重配與換裝只能在營火（`test_spending_is_blocked_after_the_run_ends_and_respec_only_at_the_campfire`）；API：`tests/api/test_skill_growth_api.py::test_campfire_respec_and_loadout_over_the_api` |
| 7 | 每場三選一照舊保留 | 通過 | 升級與營火的候選流程未改；被換掉的技能改進備用（`tests/roguelite/test_offers.py::test_replaced_generated_skills_go_to_the_bench`）；`test_the_level_up_spend_is_checked_before_anything_changes` |
| 8 | 引擎：等級是單位技能資料的一部分，重播一致 | 通過 | `UnitTemplate.skill_levels` → `UnitState.skill_levels`（`battle_setup` 帶入）；`test_battle_levels_flow_into_the_battle_setup_and_the_engine_state`、`test_skill_levels_survive_a_json_round_trip_and_clone`、`test_replay_is_deterministic_with_levels_and_the_save_round_trips`、`test_a_mid_battle_save_with_levels_replays_to_the_same_state`（戰鬥中存檔重播的狀態與存檔當下逐位元相同） |
| 9 | 預覽與技能卡顯示等級與下一級效果 | 通過 | 預覽沿用 `damage_parameters`／`acting_skill`，所以已含等級（`preview` 不需另改）；技能卡 `growth`（`current_text`、`next_text`、`trait_text`）：`test_the_hero_reports_points_levels_and_growth_rules`；前端 `skillGrowth.test.ts::技能卡的等級說明` |
| 10 | 網頁：營火與戰鬥後可分配點數、技能卡顯示 Lv | 通過 | 截圖 `3-26a-levelup.png`（升級畫面，草稿 Lv.3）、`3-26a-campfire.png`（營火：分配、免費重配、換裝與備用）、`3-26a-battle.png`（戰鬥技能列「灰燼收割 Lv.5」）；戰前（還有未花的點數時）也有分配區塊 |
| 11 | `trpg run auto` 2 個種子跑完 | 通過 | `tests/cli/test_run_cli.py::test_run_auto_spends_skill_points_and_shows_levels[1,2]`（輸出含「技能點升級：…Lv.N」）；手動：`trpg run auto --seed 1`（潑水瓶升到 Lv.5，第 3 場失敗，一輪正常結束） |
| 12 | 存檔版本 | 通過 | `trpg-run/4`（`tests/roguelite/test_save.py`、`test_old_saves_are_refused_with_a_hint`：`/1`、`/2`、`/3` 拒絕並提示開新一輪） |
| 13 | vitest | 通過 | `client/src/run/skillGrowth.test.ts`（草稿、費用、上限、請求、技能卡說明、換裝，共 9 個）；全部 60 檔 650 個 |
| 14 | 截圖 | 完成 | `docs/phases/img/3-26a-levelup.png`、`3-26a-campfire.png`、`3-26a-battle.png`。伺服器用 `trpg serve --port 8137`（沒有動 8000）；截圖用 headless Chrome＋CDP（node 腳本，未進 repo） |
| 15 | `check.py` 全過、`pnpm build` 成功 | 見下方「全量檢查」 | |

## 3. 設計摘要

### 3.1 資料與規則（`content/skill_growth.yaml`）

- `max_level: 5`、`points_per_level: 2`、`upgrade_cost: 1`、`effect_permille: [0, 100, 100, 200, 200]`（索引 ＋ 1 ＝ 等級，累計加成：2 級 +10%、3 級沿用、4 級 +20%、5 級沿用）、`trait_level: 5`、`trait_area_delta: 1`、`trait_cooldown_delta: 1`、`trait_min_cooldown: 2`、`evolve_level: 3`（3-26b 用，先保留）。
- schema：`trpg.content.skill_growth.SkillGrowthRules`（個數、遞增、等級範圍檢查）；掛在 `Ruleset.skill_growth`（嵌入規則包，重播不依賴資料檔）。

### 3.2 引擎（`trpg.engine.skill_levels`）

- 資料流：`RunState.skill_levels`（技能 ID → 等級，只列 ≥ 2）→ `battle_setup` 只帶「裝備中」的等級進 `UnitTemplate.skill_levels` → `UnitState.skill_levels`（`make_unit`）。隊友與敵人沒有。
- 效果加成：`level_multiplier(rules, unit, skill)`（只有主動技能）。傷害在 `damage_parameters` 的倍率上乘（涵蓋一般傷害與 `then` 傷害，預覽共用）；治療在 `_Cast._heal_multiplier`（含聖光雙效、獻祭治療）；護盾新增 `ShieldEffect.multiplier_permille`，護盾量 ＝ 原式 × 倍率 ÷ 1000，無條件捨去。
- 5 級小特性：`leveled_skill` 在 `modifiers.shaped_skill` 的最前面套用（施放前複製出變形後的技能，所以合法動作、預覽、結算一致）：形狀有可加的 `size`／`radius` 且未達形狀最大值 → 範圍 +1；否則原冷卻 ≥ 2 → 冷卻 −1；都做不到 → 沒有小特性。複合技能（有第二段）與陷阱不加範圍（與修正規則的保守做法一致）。`modifiers._grow` 改成呼叫 `skill_levels.grow_shape`（同一份邏輯）。

### 3.3 一輪（`trpg.roguelite`）

- `RunState` 新增 `skill_points`、`skill_levels`、`bench`（備用技能 ID；定義在 `generated_skills` 或內容庫）。
- `growth.py`：`spend_points`、`respec`、`set_loadout`、`battle_levels`、`raise_problem`、`spent_points`。
- 新的選擇種類（`Choice` 多三種，都不推進節點）：`SpendChoice`（升級、營火、戰鬥前可花；`levels` ＝ 技能 ID → 目標等級）、`RespecChoice`（營火）、`LoadoutChoice`（營火；`skills` ＝ 新的裝備清單）。`LevelUpChoice` 多選填的 `levels`（選完候選之後順便花點數）。
- 被替換的技能進 `bench`（等級保留，營火可換回）；候選產生器的排除清單也含備用技能。
- `trpg run auto`：升級時用 `auto_levels` 把點數集中在第一個未滿級的主動技能（寫進 `LevelUpChoice.levels`，所以網頁 API 路徑與 CLI 路徑結果一致）。

### 3.4 API（只新增欄位）

- `SkillCard.growth: SkillLevelInfo | None`（`trpg.narrative.skill_levels`）：只有一輪中主角持有的主動技能卡片帶它（候選、技能庫、工坊的卡片為 `None`）。
- `HeroOut.skill_points`、`skill_growth`（規則數值，前端不寫死）、`bench`（備用技能卡片）。
- `UnitView.skill_levels`（自己陣營、≥ 2 級；技能列顯示「Lv.N」）。
- `POST /api/runs/{id}/choice` 的 `Choice` 多三種；戰鬥進行中送 `spend`／`respec`／`loadout` 回 409（改了主角會讓存檔重播不一致）。

## 4. 存檔與 `LOG_FORMAT`

- 存檔 `trpg-run/3` → **`trpg-run/4`**（`run.skill_points`、`run.skill_levels`、`run.bench`）。舊版明確拒絕並提示開新一輪。
- `LOG_FORMAT` `/43` → **`/44`**（`UnitState` 多 `skill_levels`、結算多了等級倍率與 5 級小特性）。與 3G-G3b 的合併衝突由 PM 處理（`runner.py` 的版本字串與說明、7 個測試檔的 `battle-log/43` 字串；兩邊都想用 `/44` 時請改成 `/45`）。`library.py`（`Ruleset` 新欄位）、`state.py`（`UnitState` 新欄位與 `clone`）、`lifecycle.py`（`make_unit`）、`modifiers.py`（`shaped_skill` 第一行）也可能與 G3b 在附近衝突。
- `styles.css` 只在檔尾新增；API 型別只新增欄位。

## 5. 3-26b（分歧進化）會用到的接點

- `trpg.roguelite.growth.raise_problem(library, run, skill, skill_id, level)`：「這招能不能升到這一級」的唯一檢查處——3 級的「用過 N 次」門檻放這裡（回傳不能升的原因，API 以 422 顯示）；`content/skill_growth.yaml` 的 `evolve_level` 已預留。
- `RunState.behavior` 只有動作類型次數；每招的用法統計（使用次數、目標關鍵字狀態……）要在 `finish_battle(..., actions)` 旁累加到新的 `RunState` 欄位（存檔再遞增 `/5`）。
- `RunState.skill_levels` 是「ID → 等級」；進化選擇可另存 `RunState.evolutions: dict[技能 ID, 進化結果]`，由 `battle_setup` 在帶入等級時把技能換成進化後的定義（`with_skills`，ID 必須不同——`with_skills` 遇到同 ID 不同內容會拒絕）。
- `growth.spent_points`／`respec`：進化後重配要一併處理（目前重配只退回點數、不動進化）。
- 引擎：`modifiers.shaped_skill` → `skill_levels.leveled_skill` 是「施放前變形」的位置，進化若只是換模板不需動引擎。
- 技能卡：`SkillLevelInfo.next_text` 已在 3 級顯示「分歧進化（之後開放）」，3-26b 把它換成兩支比較。
- 前端：`SkillGrowthPanel` 的 `Row` 是每個技能的分配列；進化二選一可放在升到 3 級的確認流程。

## 6. 新增的複雜度 noqa

無（`src` 沒有新增任何 `noqa`）。

## 7. 全量檢查

- 第一次全量 `uv run python scripts/check.py`：ruff、format、lint-imports、client install／typecheck／vitest（60 檔 650 個）通過；pytest 4031 個中 1 個失敗（`tests/engine/test_24c.py` 斷言 `LOG_FORMAT.endswith("/43")`，已改 `/44`）、mypy 報 `test_skill_levels.py` 的多餘 `type: ignore`（已拿掉）。
- 修正後：`uv run mypy`（497 個檔案）無問題、`ruff format --check` 通過、`test_24c.py` 與 `test_skill_levels.py` 31 個通過；其餘 4030 個 pytest 在第一次全量已通過（修正只動這兩個測試檔），所以沒有重跑第二次全量（節省時間）。
- `corepack pnpm -C client build`：成功（只有 chunk 大於 500 kB 的既有警告）。

## 8. 待 PM 決定

1. **只有主動技能能升級**：被動、反應、姿態、修正的等級先不做（它們沒有「傷害／治療／護盾」數值可加成，也沒有冷卻或範圍）；它們的卡片沒有等級資料、不能花點數。要不要之後讓被動／反應也有等級？
2. **效果加成怎麼算**：2 級 +10%、4 級再 +10%（累計 +20%，3、5 級沿用），套在傷害、治療、護盾的倍率上（乘法疊在其他倍率之後，不受裝備的 +50% 傷害加成上限限制）。其他數值（狀態持續回合、位移距離、召喚物數值、吸血比例、反噬、陷阱／區域的傷害）先不加成，傷害只涵蓋走 `damage_parameters` 的技能傷害（含 `then`）。要擴大嗎？
3. **5 級小特性的擇一規則**：有可加的範圍（形狀 `size`／`radius` 未達上限，且不是複合技能或陷阱）→ 範圍 +1；否則冷卻 ≥ 2 → 冷卻 −1；都沒有 → 沒有小特性（卡片顯示原因）。結果是單體、沒有冷卻的技能升到 5 級只有 +20%。要不要讓這種技能改給其他小特性（例如 AP −1 受限、射程 +1）？
4. **備用技能（`bench`）是新增的**：規格寫「卸下後等級保留」「營火可以換裝」，但現有一輪沒有技能庫，被替換的技能就消失了。我新增 `bench`：被替換或營火卸下的技能進備用（等級保留），營火可以換回；備用沒有數量上限、候選產生器不會再給已持有或備用的技能。大世界的技能庫來了之後要和它合併。
5. **何時可以分配**：升級畫面（跟著升級選擇一起送出）、營火、戰鬥前（戰鬥進行中不行）；重配與換裝只有營火（規格：營火）。重配不退任務幣（原型沒有）。
6. **AI 代打的花點策略**：把點數集中在裝備順序的第一個未滿級主動技能（不看用法）。只是讓 `trpg run auto` 走過這條路，不代表平衡；模擬看平衡時可能要換成「最常用的技能」。
7. **`LOG_FORMAT` `/44`、存檔 `/4`**：見第 4 節，合併時與 G3b 重疊的版本號由 PM 處理。
8. **平衡未模擬**：+10%／+20% 與每級 2 點是規格數值；沒有跑 `sim matrix`。`trpg run auto` 兩個種子仍是第 3 場失敗，與先前一致，未做平衡評估。
9. **技能卡等級說明只在完整卡片顯示**：緊湊版（技能列的浮動卡）只有標題的「Lv.N」，沒有加成與下一級的說明；戰鬥中技能列按鈕顯示 Lv 標籤。
10. **`styles.css` 在檔尾新增了一段**（`.growth-*`、`.loadout-*`、`.skill-lv`、`.skill-level-badge`）。
