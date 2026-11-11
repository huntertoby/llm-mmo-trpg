# Phase OB-4 報告：#150 入門期的戰鬥閘與活動限制

> 實作者：worktree 基準 main `729c47a0`。沒有 push、沒有 merge。依據：`docs/phases/PhaseOB-4計畫.md`、`docs/design/21` 21.5（#150 第 7、9 點）、`PhaseOB-1報告.md`、`PhaseOB-2報告.md`、共用筆記 `盤點-150與147.md` 1.1、4.3、第 6 節 Q2、Q3。沒有動 `src/trpg/engine/`、`src/trpg/roguelite/`、`content/`、API schema、前端；沒有動 OB-3 的檔案（`opening_choice.py`、`growth.py`、`api/world_range*.py`、`api/world_pregen.py`、`newcomer.yaml`）。

「入門期」＝`char.opening is not None` 且 `stage != "chosen"`（`opening_limits.in_starter_period`；含還在選大類的 `pick_class`）。所有新判斷都以它為前提。

## 1. 21.5 第 7、9 點逐項對照（交付項目 1）

| 21.5 | 項目 | 開工前 | 本段 |
|---|---|---|---|
| 7 | 走動、對話、傳送、改外觀、買賣、換防具 | 已放行（OB-1） | 不動 |
| 7 | 接任務 | 已放行（沒測） | 補測試；給招的步驟見下 |
| 7 | 不能換主手、換種族、閃現 | 已擋（OB-1） | 不動 |
| 7 | 戰鬥只開放新手第 1、2 步 | **未處理** | 補：見第 2 節 |
| 9 | 巡邏不顯示、不接觸 | **未處理** | 補：`field_enemies._shown` |
| 9 | 節點遭遇不觸發 | **未處理** | 補：`step._travel_to` |
| 9 | 第 3 步固定戰正式選定後才開 | **未處理** | 補：同巡邏的過濾＋戰鬥閘＋步驟不結算 |
| 9 | 休息、紮營、用道具 | 已放行 | 不動（紮營「要先清空」的條件照舊） |
| 9 | 不開戰也不給招的情境判定 | 已放行 | 不動：情境判定（`situation`）本身不會開戰也不給招，全部放行 |
| 9 | 手動配點與重配不擋 | 已放行（OB-1、OB-2 有測） | 不動 |
| 9 | 打造、強化、重骰、指定詞條只限防具 | 已擋（OB-1） | 不動 |
| 9 | 入門期不存影子 | 已做（OB-2） | 不動 |
| 9 | 任務的戰鬥要等正式選定 | **未處理** | 補：任務的戰鬥都來自上面三條路，全部關掉 |
| 9 | 任務給招的獎勵要等正式選定 | 新手前兩步已延後（OB-2），其餘**未處理** | 補：`quests._advance_one` 先不結算 |
| 9 | 雇傭兵、聯賽、賽季 Boss、誓約、換技能不開放 | 已擋（OB-1） | 不動；補「選定後可用」的測試 |
| 9 | 會開戰或給招的事件解法、機遇 | **未處理** | 補：`solutions._check`、事件卡畫面 |
| 9 | 溶掉、傳承 4 級前不能用 | 已擋（OB-1） | 不動 |
| 9 | 試打、關鍵字推薦、重選、回滿、4 級前、靶場入口 | OB-2／OB-3／OB-5 | 範圍外 |

## 2. 做法

新模組 `src/trpg/world/opening_limits.py`：入門期的判斷與被擋的原因文字都在這裡；只依賴內容與狀態，不匯入其他世界邏輯。

| # | 項目 | 做法 |
|---|---|---|
| 2 | 巡邏與實地敵人 | `field_enemies._shown` 多一個過濾（`spawn_hidden`）：入門期只留 `until_quest` 指到新手任務（`kind: starter`）、`until_step` 是前 2 步的隊伍。畫面清單（`field_enemies` → `FieldView.enemies`）與接觸判定（`walk_watch`）都走 `_shown`，所以一定一致。這一趟的種子、巡邏步數照算（亂數消耗不變） |
| 3 | 節點遭遇 | `step._travel_to`：入門期遇敵機率歸 0，擲骰照擲（同「已清空」的寫法；跨區出口共用同一個函式） |
| 4 | 第 3 步固定戰、任務戰鬥 | ① 雨中梯田的固定戰被 #2 的過濾擋掉；② 開局閘門 `starter` 階段多一條 `_fight_rule`：`fight` 只收新手任務前 2 步的固定戰（`fight_problem`），其他遭遇回原因——正常流程碰不到，是最後一道；③ 給招的步驟（`reward.offer` 或 `story_skill`）入門期先不結算（`holds_step`，`quests._advance_one` 加 2 行），新手任務前 2 步除外（三選一照 OB-2 延後） |
| 5 | 會開戰或給招的事件 | `solutions._check`：戰鬥解法（`combat`）、機遇（`opportunity`）擋下並回原因；交涉、放棄、情境判定照常。`field_things.object_status`：`use: encounter` 的情境物件（Boss 門）帶 `problem_zh`，`use_field_object` 照它擋。事件卡畫面 `api/world_story_view._solution_problem` 用同一個函式填 `unavailable_zh`。另：入門期不出機遇保底、也不記「遇過機遇」（`events.py`），見待決 3 |
| 6 | 不開放的系統 | OB-1 的 `_STARTER_BLOCKED` 已經全擋（雇用與影子 AI、聯賽報名與退出、賽季 Boss、立誓與解除、換技能），本段沒有改程式，只補測試 |
| 7 | 版號 | `WORLD_RULES_VERSION` 24 → 25，見第 4 節 |

`opening.py` 的改動：匯入 2 行、`_fight_rule` 6 行、`_STAGE_RULES["starter"]` 多 1 列。`quests.py` 的改動：匯入 1 行、`_advance_one` 2 行（沒有碰三選一）。

戰鬥閘認固定戰的方式：遭遇要是實地地圖上的接觸，而且（地點, 陣容）對得上新手任務前 2 步的 `win_battle` 條件。看任務資料而不是地圖的 `spawns`，因為 `tests/world` 的 `library` 沒有實地地圖（OB-2 的測試用假的接觸資料打固定戰），看地圖會讓既有測試失敗。

## 3. 被擋時的原因文字

本段新增（都在 `opening_limits.py`）：

| 常數 | 何時 | 文字 |
|---|---|---|
| `FIGHT_ZH` | `fight`：不是新手前兩步的遭遇 | 入門期只能打新手任務前兩步的戰鬥，找葛蘭選定武器後就能打 |
| `SOLUTION_ZH["combat"]` | 事件的戰鬥解法 | 入門期不能用戰鬥解決事件，找葛蘭選定武器後就能打 |
| `SOLUTION_ZH["opportunity"]` | 事件的機遇 | 入門期還不能領機遇的技能，找葛蘭選定武器後再來 |
| `OBJECT_ZH` | `use: encounter` 的情境物件 | 入門期還不能挑戰這裡的對手，找葛蘭選定武器後再來 |

OB-1 已有、本段沒動（在 `opening.py`）：入門期不能換技能／不能雇用傭兵／不能參加聯賽／不能挑戰賽季 Boss／不能立誓／不能閃現／不能換種族／不能換主手／打造、強化、附魔只限防具；4 級前不能溶掉技能或傳承。

不顯示的敵人、不觸發的節點遭遇、先不結算的任務步驟都沒有訊息（玩家看不到，也沒有被拒絕的動作）。

## 4. 版號

| 項目 | 變動 | 理由 |
|---|---|---|
| `WORLD_RULES_VERSION` | **24 → 25（有動）** | 同一份 24 的日誌只要有入門期的角色，重播出的遭遇與任務進度就不同；`save.py` 有寫說明。OB-3 若也加，合併時由 PM 對齊 |
| `CHAR_FORMAT`、`trpg-wlog`、`LOG_FORMAT`、`RULE_HASHES` | 不變 | 沒有新欄位、新動作、新事件；沒動引擎 |
| openapi、`schema.d.ts` | 不變 | 只用既有欄位（`FieldView.enemies`、`EventSolutionView.available`／`unavailable_zh`、`FieldSituationObjectView.usable`／`problem_zh`） |

`tests/world/test_opening_stages.py::test_versions` 的字面值 24 跟著改成 25，這是本段唯一改到的既有測試。沒有放寬任何既有規則、驗證或斷言。

## 5. 驗收

| 條件 | 結果 |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 2283 files already formatted |
| `uv run mypy` | Success: no issues found in 1432 source files |
| `lint-imports` | 14 kept, 0 broken |
| `tests/world tests/api tests/content tests/narrative tests/server tests/test_architecture.py`（`-n 8`） | 5340 passed、1 skipped、0 failed（4 分 05 秒；`test_dev_boss_rehearses_to_the_boss_charge` 這次也過） |
| `trpg battle --map swamp --seed 7 --log-json` ＋ `battle replay` | 重播驗證通過：58 個動作、217 個事件，最終狀態一致 |

沒有跑：`scripts/check.py` 全量、`tests/skillgen`、`tests/roguelite`、`tests/cli`（輸出快照）、前端（沒改）。沒有新增複雜度類 noqa（測試檔有 1 個 `PLR0917`：表格測試的欄位）。

行為一致測試（`tests/world/test_opening_limits.py`，31 個；都跑真的世界動作，實地地圖用正式內容）：

| 規格 | 測試 |
|---|---|
| 表格：入門期在各地圖走動 | `test_field_enemies_table`（白天、夜晚 × 雲嶺每張有敵人的圖 × 每一隊）：走到每一隊旁邊——清單裡的開戰、不在清單裡的不開戰；同一個角色換成已選定後同一步開戰 |
| 第 1、2 步碰得到並開戰 | `test_starter_fixed_fights_open_in_starter_period`（2 組，真的走過去、真的打完）、`test_done_starter_step_is_gone_for_everyone` |
| 其他巡邏不在清單、走過去不開戰；選定後恢復 | `test_named_enemies_hidden_then_restored`（石階夜間巡邏、竹林巡邏、梯田固定戰、田埂巡邏） |
| 節點移動不觸發遭遇 | `test_node_travel_never_encounters_in_starter_period`（必遇敵的規則下連走 3 個地點；選定後與舊角色同一步遇敵，擲的骰相同） |
| 第 3 步固定戰開不了；選定後恢復 | `test_step_three_waits_for_formal_choice`（走完整流程、真的正式選定、真的開打）、`test_fight_gate_blocks_everything_but_starter_fights` |
| 每個不開放的系統各一筆 | `test_closed_systems`（8 個動作：入門期被擋且原因文字相符；走完整流程選定的角色不再被入門期擋，其中雇用、影子 AI、立誓、換技能直接做得成） |
| 畫面與實際一致 | `test_field_enemies_table`（`FieldView.enemies` ＝ `field_enemies`，每一隊逐一驗碰不碰得到）、`test_combat_solution_blocked_then_restored`、`test_opportunity_blocked_then_restored`、`test_boss_gate_object_blocked_then_restored`（畫面的不可用原因＝動作被拒的原因） |
| 舊角色事件列表與改前相同 | 測試內：`test_field_enemies_table`、節點移動測試都斷言舊角色與已選定的事件完全相同。另用腳本對照改前的程式（`git archive 729c47a0` 解到暫存資料夾、`PYTHONPATH` 指過去，確認 `trpg.__file__` 載入的是那份）：舊角色在雲嶺每張圖走到每一隊旁邊（白天、夜晚）＋必遇敵的節點移動＋事件戰鬥解法＋Boss 門，共 52 個動作、106 個事件連同動作後的角色狀態，SHA-256 改前改後相同（`0a49aaea…5d323`）。這個對照是一次性的，沒有放進測試 |
| 世界日誌重播 | `test_starter_period_log_replays_identically`：選大類 → 夜裡走到巡邏旁邊（不開戰）→ 走到第 1 步固定戰旁邊（開戰）→ 打；重播與存檔往返一致 |
| 其他 | 任務可以接（`test_quests_can_be_accepted`）、給招的步驟等選定（`test_skill_reward_step_waits_for_formal_choice`）、不給招的步驟照常（`test_steps_without_skill_rewards_still_complete`）、放棄與情境判定照常（`test_peaceful_solutions_still_work`）、機遇保底保留（`test_opportunity_guarantee_is_kept_for_later`）、常數一致（`test_starter_steps_match_formal_choice`） |

## 6. 待 PM 決定

規格沒列到的動作照「會開戰或給招就擋、其餘放行」：

1. **放行的**（不開戰也不給招）：潛行、傳送石、郵寄與領信、分解、酒館、聊天、戰後選掉落、選三選一、撤退、敘述、提示紀錄。情境判定全部放行（`situations.py` 的結算沒有開遭遇、給技能的路徑）。
2. **給招的任務步驟「先不結算」而不是「先完成、招延後」**。延後要動 `deferred_offers` 與三選一（OB-3 的範圍），所以選保守的做法。副作用：狀態型條件（到某地、持有線頭、好感度）選定後的下一個動作就會結算；**事件型條件**（當下那次情境判定的結果）入門期達成了不會補算。目前內容碰得到的：主線「進青霧觀山門」（給劇情技能，狀態型，沒有損失）、任務鏈「查出私通盜賊的人」（給三選一；情境判定成功那一下不算，但條件另有「持有線頭 `temple_traitor`」可補）。兩者都要先推主線，新手 1～3 級很難走到。
3. **入門期不出機遇保底、碰到機遇骨架不記「遇過」**（規格沒寫）。否則保底的那一次會出在領不了的時候、白白用掉。機遇骨架照機率仍可能出現，事件卡上機遇那一項顯示不可用與原因。
4. **事件本身沒有隱藏**：入門期事件照常觸發，戰鬥解法與機遇顯示成不可用（帶原因），放棄、交涉、情境判定可用。「不顯示」只用在敵人。
5. **「已清空」與紮營沒有跟著改**：被隱藏的個人隊伍（例：梯田的第 3 步固定戰）仍算「還在」，所以那張圖在入門期不會顯示已清空、要先清空才能紮營的地點也照舊不能紮營。
6. **不開放的系統的面板沒有改**：聯賽、賽季 Boss、傭兵、誓約、換技能的畫面資料仍照各自的條件顯示可不可用，送出動作才回「入門期不能…」。要讓面板直接顯示原因的話要改 `league_view`、`season_boss_view`、`world_party_view`、`world_growth_view`（後者 OB-3 可能也在改），建議合併後再補或併進 OB-5。
7. **`STARTER_STEPS` 有兩份**：`opening_limits.STARTER_STEPS` 與 `opening_choice.STARTER_STEPS`（同值，測試檢查）。`opening_choice` 匯入 `quests`、`quests` 要用 `opening_limits`，不能反過來匯入；本段不能改 `opening_choice.py`。合併後建議讓 `opening_choice` 改成從 `opening_limits` 匯入。
8. **`pick_class` 也算入門期**（敵人過濾、節點遭遇）；這個階段本來就只能做白名單的動作，沒有實際影響。
9. **開發用端點沒有擋**（`api/world_dev.py` 直接塞遭遇的那些）：塞進去的遭遇在入門期會被戰鬥閘擋住，要撤退。
10. **原因文字是暫定**，OB-5／6 定稿。
11. 驗收的全目錄測試結果見第 5 節。
