# Phase 3-5a 報告：roguelite 一輪——核心、存檔、API

## 1. 完成項目與 commit

| commit | 內容 |
|---|---|
| 07bd28d | 引擎：`UnitSpawn.hp`／`mana`（開場 HP／法力，`None`＝滿，超過上限以上限計）；`CommandedAI.restore_orders`（讀檔還原隊友指令）；`tests/engine/test_spawn_resources.py` |
| 558b485 | 0.10 #1：`trpg skills list` 的被動、反應、姿態技能不再顯示「None」，改顯示種類；重錄 CLI 快照（只有 `skills_list` 的雜湊變了） |
| d23e4f1 | `content/roguelite.yaml` ＋ schema `trpg.content.roguelite.RunRules`；內容庫載入時做跨檔案檢查；`trpg content check` 列出；`tests/content/test_roguelite_content.py` |
| 2ba97d4 | `trpg.roguelite`：`state`、`start`、`offers`、`progress`、`battle`、`save`、`auto`；import-linter 與 `test_architecture.py` 新增 roguelite 的依賴規則；`tests/roguelite/`（4 檔） |
| d6c5a31 | CLI `trpg run new|auto|show`；`.gitignore` 加 `saves/`；`tests/cli/test_run_cli.py` |
| 273d534 | API `/api/runs`（建立、狀態、戰鬥、選擇、存檔、讀檔、存檔列表）；`/api/skills/{id}` 也查得到生成技能；重新產生 `client/openapi.json` 與 `schema.d.ts`；`tests/api/test_runs_api.py` |
| f12dd09 | 測試整理 |
| （本報告） | 報告 |

沒有 stash、reset、amend、切換分支，沒有 push。`LOG_FORMAT` 維持 `/34`：`UnitSpawn` 的兩個新欄位預設 `None`，舊紀錄照常讀取與重播，事件 schema 沒變。Boss 地圖與前端（7.2、7.3）沒有做。

### 1.1 一輪的流程（`trpg.roguelite.progress`）

開新一輪 → 第 1 場 →（打贏）寫回主角 HP、法力、源力（＋戰後獎勵 1）、經驗 ＋100 → 每升一級一個升級節點（＋2 屬性點、3 選 1 或跳過）→ 第 3、5 場後營火（進入時 HP、法力回滿，源力 ＋1，可重骰一次）→ 下一場；下一場是 Boss 時源力至少 2 → Boss 打贏＝一輪勝利；任何一場沒打贏（含輪數上限）＝一輪失敗。

- 開局：主角用 build 英雄的武器、HP、法力、行為模式與技能組（＝起始技能組）；六項屬性皆為 10，另 4 點自由分配（設計文件 7.2）。省略配點時全部點在技能最常用的縮放屬性。
- 每場：主角（第一個我方單位，帶一輪的 HP、法力、源力；源力 ＝ max(存檔值, 1)、上限 3，由既有的 `starting_source` 處理）＋ 2 名標準隊友（`sim_companion_fighter`、`sim_companion_archer`，滿狀態）＋ 本場敵人；規則包以 `Ruleset.with_skills` 加入主角的生成技能。
- 戰後以 `battle_result(state).ally(主角單位 ID)` 讀回（3E-1）。擊殺精英的 ＋1 源力在戰鬥中由引擎處理，所以會帶出戰鬥。
- 隨機：全部由一輪的種子以 `Rng(seed).fork(<標籤>)` 衍生——`plan/map_types`、`plan/map/<i>`、`plan/encounter/<i>`、`plan/battle/<i>`、`offer/<n>`（`n`＝第幾組候選）。`fork` 不推進父串流，所以各用途彼此獨立、與呼叫順序無關。
- 地圖：先洗牌地圖類型取 5 種（同一輪不重複），再在該類型內抽一張；池內 9 張、8 種類型。Boss 戰先用 `ruined_fort` ＋ `bandit_boss`、盜賊、弓手、盾兵（不在一般池內）。**3-5b 只要改 `roguelite.yaml` 的 `boss:`**。
- 敵人隨場數成長：2 → 3 → 4 → 4 → 4 人，種類逐漸偏向弓手與盾兵（每場兩個選項，以種子抽）。起始區每方 4 格，所以上限 4 人。

### 1.2 技能候選（`trpg.roguelite.offers`）

- 從 `offer/<n>` 串流取組合器種子，呼叫 `compose_random_skill(seed, tier=等級對應的階級)`；過濾組不出來、武器不相容、主角已有、同組重複的。
- 「順路」＝縮放屬性等於主角目前最高屬性（並列取六屬性順序第一個），組合器分類提示依最高屬性（力量、敏捷 → 武器技；其他 → 法術技）；「偏離路線」固定 1 個、放在最後（`off_route` 給索引）。200 個種子內湊不齊時以多出來的合格技能補（實測 5 個 build × 4 個種子都一次湊齊）。
- 候選連同 **完整技能定義** 存在節點裡；選了之後定義進 `RunState.generated_skills`（只保留目前裝備的）。
- 裝備限制用既有的 `skill_slot_problems`（主動 ≤ 6、被動含修正 ≤ 3、反應 ≤ 1、姿態 ≤ 1、規則改變型傳說 ≤ 1）；裝不下要指定 `replace`（新技能放在被替換技能的位置），否則 422。

### 1.3 存檔格式（`trpg-run/1`，設計理由）

```json
{
 "format": "trpg-run/1",
 "engine": "trpg-battle-log/34",
 "run_id": "…",
 "run": { RunState },
 "battle": null | { "index": 2, "seed": 1348717492, "steps": [ 動作或決定 … ], "orders": [ OrderRecord … ] }
}
```

`RunState`：`seed`、`build_id`、`hero`（目前的單位範本：屬性與技能隨升級改變）、`level`、`xp`、`hp`、`mana`、`source`、`generated_skills`（完整定義）、`plan`（每一場的地圖、敵人、戰鬥種子、是否 Boss）、`battles_done`、`levels_pending`、`campfires_done`、`offers_made`、`history`（每場結果，含戰鬥最終狀態 JSON 的 SHA-256）、`node`（`battle`／`level_up`／`campfire`／`ended`，升級與重骰的候選含完整定義）。實測戰鬥中的存檔約 21 KB。

設計理由：

1. **主角存完整範本、生成技能存完整定義、候選存在節點裡**：之後改了 build 檔、組合器或 `roguelite.yaml`，舊存檔的主角與「當時給的候選」都不變。
2. **`plan` 開局就排好並存檔**：之後改了地圖或遭遇的抽選方式，舊存檔的下一場不變；`plan` 也讓網頁可以顯示「下一場地圖」。
3. **不存亂數狀態，只存計數器**：一輪的亂數由種子 ＋ 標籤衍生，唯一會變的是 `offers_made`；戰鬥的亂數由「種子 ＋ 步驟」重播得到（0.2 E）。
4. **戰鬥不存 `setup`**：戰鬥中 `RunState` 不變（戰後才寫回），所以 `setup` ＝ `battle_setup(內容庫, RunState)` 可重建；規格要求的「讀檔時用 `Ruleset.with_skills` 加回生成技能」就在這裡。缺點是 **地圖、敵人範本、規則內容改了，戰鬥中的存檔會重播出不同結果**，所以：
5. **`engine` 欄位**：戰鬥中的存檔若 `engine` 與目前 `LOG_FORMAT` 不同就拒絕讀取（422／`SaveFormatError`）；戰鬥之間的存檔不需要重播，不檢查。重播時任何一步不合法也拒絕。
6. 步驟與指令沿用 `BattleLog.actions`／`BattleLog.orders` 的格式；讀檔後以 `CommandedAI.restore_orders` 還原目前指令（效用 AI 沒有其他跨決策狀態），之後的 AI 決策與沒有中斷時相同。
7. `run_id` 限 `[A-Za-z0-9_-]{1,64}`，檔名 `saves/run-<run_id>.json`（預設專案根目錄的 `saves/`，環境變數 `TRPG_SAVE_DIR` 可覆寫；已加進 `.gitignore`）。

### 1.4 API（最終路徑）

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/api/runs` | 開新一輪 `{build, seed, attributes?}` → `RunResponse`（201） |
| GET | `/api/runs/saves` | 存檔列表 |
| POST | `/api/runs/load` | 讀檔 `{run_id}`（戰鬥中的存檔重播到存檔當下，產生新的 `battle_id`） |
| GET | `/api/runs/{run_id}` | 一輪的狀態（戰鬥已結束時先結算） |
| POST | `/api/runs/{run_id}/battle` | 開始或接續本場戰鬥 → `{run, battle: BattleResponse}`；之後用既有的 `/api/battles/{battle_id}/…` 操作 |
| POST | `/api/runs/{run_id}/choice` | `{"kind":"level_up","attributes":{…},"pick":0,"replace":null}`、`{"kind":"reroll"}`、`{"kind":"pick","pick":…,"replace":…}`、`{"kind":"leave"}` |
| POST | `/api/runs/{run_id}/save` | 存檔（戰鬥中也可以） |

`RunResponse` 給主角（屬性、HP、法力、源力、下一級經驗、技能卡片）、目前節點（候選以技能卡片給，含 `off_route` 索引）、每一場的安排（中文地圖名與敵人名、是否已打完）、歷程、進行中的 `battle_id`。錯誤：不存在 404、節點不符 409、內容不合法或存檔壞掉 422。

### 1.5 CLI

- `trpg run new --seed N --build X [--attrs str=2,con=2] [--save-dir D]`：開新一輪並存檔。
- `trpg run auto --seed N [--build X] [--save] [--save-dir D]`、`trpg run auto --from <存檔>`（從存檔接續，含戰鬥中）。沒給 `--build` 時以 `Rng(seed).fork("build")` 抽一個。
- `trpg run show <存檔>`。

## 2. 驗收條件（7.4 的 3-5a）

1. **一輪種子衍生所有亂數；同種子兩次結果一致** — 通過。`tests/roguelite/test_save.py::test_same_seed_gives_the_same_run_twice`、`test_different_seeds_give_different_runs`；`tests/roguelite/test_start.py::test_plan_is_derived_from_the_seed`；`tests/roguelite/test_offers.py::test_offer_is_deterministic_and_depends_on_the_counter`；`tests/cli/test_run_cli.py::test_run_auto_is_deterministic_and_matches_the_library_run`（CLI 兩次輸出逐字相同）。`roguelite` 在確定性套件清單內（`test_no_nondeterministic_apis_in_deterministic_packages`）。
2. **存檔 → 讀檔 → 繼續（含戰鬥中）與一次打完逐位元相同；存檔 JSON 帶 `format`** — 通過。`test_save.py::test_save_load_continue_matches_one_go_bit_for_bit`（5 個中斷點：第 1 場開場、第 2 場第 37 步、Boss 戰第 15 步、升級節點、營火節點；最終 `RunState` JSON 逐字相同，含每場最終戰鬥狀態的 SHA-256）、`test_save_mid_battle_with_restored_orders_replays_exactly`（帶隊友指令）、`test_save_json_has_format_and_engine_version`、`test_wrong_format_and_engine_are_rejected`；CLI `test_run_auto_from_a_mid_battle_save_finishes_the_same`；API `tests/api/test_runs_api.py::test_save_mid_battle_load_and_continue_matches`（讀檔後戰場與合法動作與存檔時相同，打完的結果與原本相同）。
3. **HP、法力跨戰鬥保留；營火回滿；源力跨戰鬥保留、上限 3、開場至少 1、戰後獎勵與 Boss 前保底** — 通過。`test_progress.py::test_won_battle_writes_back_hp_mana_and_source_plus_reward`（寫回並以寫回值開下一場）、`test_battle_setup_puts_the_hero_first_with_run_resources`（開場 HP／法力帶入、源力 0 → 1、隊友滿狀態）、`test_source_at_start_keeps_the_saved_value_up_to_the_cap`、`test_source_reward_is_capped`、`test_campfire_mid_run_restores_hp_and_mana_and_adds_source`、`test_boss_floor_applies_before_the_boss_battle`、`test_hero_downed_in_a_won_battle_continues_with_one_hp`、`test_a_lost_battle_ends_the_run`；引擎 `tests/engine/test_spawn_resources.py`（`None` 時與舊行為逐位元相同）；API `test_battle_starts_once_and_resumes`。
4. **升級 ＋2 屬性點、3 候選含 1 個偏離路線、可跳過、裝備上限檢查；重骰在中段與 Boss 前各一次** — 通過。`test_progress.py::test_level_up_gives_two_points_and_a_skippable_offer`、`test_two_levels_at_once_give_two_level_up_nodes`、`test_campfire_reroll_once_then_pick_or_leave`、`test_no_campfire_outside_the_configured_points`、`test_a_full_victorious_run_visits_both_campfires_and_rerolls_twice`（`campfires_done == (3, 5)`、候選組數 ＝ 升級次數 ＋ 2）；`test_offers.py::test_offer_has_three_candidates_with_one_off_route`（5 個 build × 4 個種子）、`test_full_slots_require_a_replacement`、`test_equip_limits_are_six_three_one`、`test_skip_keeps_the_skills`。
5. **API 與 CLI 端點有測試；`run auto` 10 個種子無例外；`check.py` 全過** — 通過。`tests/api/test_runs_api.py`（10 個）、`tests/cli/test_run_cli.py`（8 個，含 `test_run_auto_ten_seeds_without_exceptions`）；另手動跑 `trpg run auto --seed 0…9` 一次（見第 6 節）。`uv run python scripts/check.py`：ruff、format、mypy、lint-imports（7 個合約全部 KEPT）、pytest、client install／typecheck／test 全部通過。

另：0.10 #1（`skills` 的「AP None」）——`skills show` 早在 3-4b 已不顯示；實際出現在 `trpg skills list` 的 AP 欄，改成顯示種類（反應／被動／姿態），重錄 CLI 快照。

## 3. 複雜度 noqa

沒有新增或移除。複雜度類 noqa（C901、PLR0911、PLR0912、PLR0915）總數前後都是 11。

## 4. 修改既有測試期望值

- `tests/cli/snapshots/cli_output_hashes.json` 的 `skills_list`：因為上面的「AP None」修正（被動、反應、姿態技能的 AP 欄改顯示種類）。其他 8 個雜湊（含 `skills_show_all` 與 7 場戰鬥）不變。
- `tests/test_architecture.py`：新增 roguelite 的禁止依賴（擴充，不是改期望值）。

## 5. 待 PM 決定

1. **開局屬性**：照設計文件 7.2，六項皆 10 ＋ 4 點，**不沿用** build 英雄的屬性（例如位移流原本力量 16）。HP、法力、武器、技能仍用 build 英雄。主角因此比 build 矩陣的英雄弱。若要改成「build 屬性 ＋ 4 點」，改 `new_run` 一行即可。
2. **「重骰」的意思**：做成「營火可重骰一次＝產生一組新的 3 個候選（同升級規則：1 個偏離路線、可放棄、欄位滿要替換）」，選完或放棄就離開營火。另一種解讀是「重抽本次升級的候選」，請確認。
3. **技能清單＝裝備**：沒有「擁有但沒裝備」的技能；被替換的技能直接捨棄（`generated_skills` 也只留裝備中的）。若要有技能背包，存檔要多一個欄位（升 `trpg-run/2`）。
4. **沒打贏就是失敗**：包含輪數上限（30 輪）結束的平手；主角在戰鬥中倒下但我方勝利 → 以 1 HP 繼續（規格的保守做法）。觀察：主角常在開場幾輪就被集火倒下，之後由隊友打完。
5. **主角倒下後網頁自動推進到戰鬥結束**（沿用 3-2 的 `awaits_player`：主角倒下就不再停下來）。3-5c 可能要讓玩家看完或至少顯示「主角倒下，隊友繼續作戰」。
6. **初值**（全部在 `roguelite.yaml`）：經驗每場 100、升級門檻 100／200／350／500／700（5 場 ＋ Boss 打完約 5 級）、候選階級 1／1／2／2／3、戰後源力 ＋1、營火 ＋1、Boss 前保底 2、敵人人數 2／3／4／4／4。觀察：`run auto` 10 個種子 3 勝 7 敗，敗在第 3–5 場（HP 不回復的累積）；不調，留給平衡階段。
7. **候選排列**：偏離路線固定在最後一個（`off_route` 給索引）。要不要隨機位置由 3-5c 的 UI 決定。
8. **AI 代打的選技能策略**（只用於測試與模擬）：第一個裝得下的候選；都裝不下時換掉同種欄位的最後一個技能，常常換掉上一級剛拿的生成技能。不影響玩家。
9. **戰鬥中存檔依賴內容檔不變**：存檔不含 `setup`，地圖、敵人範本或規則改了（但 `LOG_FORMAT` 沒升）時，戰鬥中的存檔可能重播失敗（會拒絕讀取）或結果不同。若要完全不受內容影響，可以在存檔加內容的雜湊，或改存完整 `setup`（每個存檔多數百 KB）。
10. **`/api/skills/{id}`** 會在進行中各輪的生成技能與候選中查找（網頁的技能卡片快取用）；伺服器重啟後要先讀檔才查得到。

## 6. 代表性輸出

```
$ uv run trpg run auto --seed 3
一輪：種子 3，build_banisher（放逐流），力量 10 敏捷 10 體質 10 智力 14 感知 10 意志 10
  第 1 場 冰湖：勝利，3 輪 44 步；HP 16 法力 11 源力 2；等級 2 經驗 100
    升級 Lv2：智力+2；選 傳說 #686161849（skill_rand_686161849），替換 閃現（skill_blink）
  第 2 場 開闊平原：勝利，4 輪 75 步；HP 1 法力 2 源力 3（主角曾倒下）；等級 3 經驗 200
    升級 Lv3：智力+2；選 冰霜・反應技 #2988714968（skill_rand_2988714968），替換 反咒（skill_counterspell）
  第 3 場 岩漿渡橋：勝利，5 輪 71 步；HP 1 法力 2 源力 3（主角曾倒下）；等級 3 經驗 300
    營火（第 3 場後）：HP、法力回滿，源力 3
    營火重骰：3 個候選
    離開營火：選 風・被動 #1534718768（skill_rand_1534718768）
  第 4 場 懸崖前哨：勝利，2 輪 47 步；HP 27 法力 10 源力 3；等級 4 經驗 400
    升級 Lv4：智力+2；選 大地・光環 #438955604（skill_rand_438955604），替換 傳說 #686161849（skill_rand_686161849）
  第 5 場 狹窄長廊：勝利，3 輪 75 步；HP 1 法力 1 源力 3；等級 5 經驗 500
    升級 Lv5：智力+2；選 風・姿態 #3005209823（skill_rand_3005209823）
    營火（第 5 場後）：HP、法力回滿，源力 3
    營火重骰：3 個候選
    離開營火：選 雷電・範圍 #213422523（skill_rand_213422523），替換 大地・光環 #438955604（skill_rand_438955604）
  Boss 戰 廢墟要塞：勝利，5 輪 86 步；HP 1 法力 28 源力 3（主角曾倒下）；等級 5 經驗 600
結果：勝利（6/6 場），HP 1/40 法力 28/40 源力 3 等級 5 經驗 600

$ for s in 0..9: uv run trpg run auto --seed $s | tail -1
seed 0: 結果：失敗（2/6 場），HP 0/60 法力 0/20 源力 3 等級 3 經驗 200
seed 1: 結果：失敗（2/6 場），HP 0/40 法力 1/40 源力 1 等級 3 經驗 200
seed 2: 結果：失敗（2/6 場），HP 0/60 法力 0/24 源力 3 等級 3 經驗 200
seed 3: 結果：勝利（6/6 場），HP 1/40 法力 28/40 源力 3 等級 5 經驗 600
seed 4: 結果：失敗（3/6 場），HP 0/60 法力 2/20 源力 3 等級 3 經驗 300
seed 5: 結果：失敗（4/6 場），HP 0/40 法力 0/40 源力 3 等級 4 經驗 400
seed 6: 結果：勝利（6/6 場），HP 1/40 法力 22/40 源力 2 等級 5 經驗 600
seed 7: 結果：失敗（4/6 場），HP 0/60 法力 0/24 源力 2 等級 4 經驗 400
seed 8: 結果：勝利（6/6 場），HP 18/60 法力 3/24 源力 3 等級 5 經驗 600
seed 9: 結果：失敗（2/6 場），HP 0/60 法力 2/24 源力 0 等級 3 經驗 200

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
```
