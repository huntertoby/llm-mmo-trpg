# Phase 3-20 報告｜跑步（玩法 #22）

> 規格：`docs/phases/Phase3計畫.md` 第 20 節；設計：`docs/design/05-戰鬥.md` 5.2「跑步」。分支：`worktree-agent-a40199cadd292aeec`（從 `dc92095` 分出，未 push、未合併）。

## 1. 做了什麼

**引擎**
- 新動作 `Run`（`engine/actions.py`，`type: "run"`）：花 `run_ap_cost`（1）AP，本回合移動點數 `+run_move_bonus`（3）；跑步本身不移動。數值在 `content/rules/core.yaml` 的 `run_ap_cost`／`run_move_bonus`（`content/rules.py` 的 `CoreRules`），沒有寫死在程式。
- 單位新欄位 `ran_this_turn`（`state.py`；自己回合開始時在 `turns.start_turn` 清除，所以「回合結束失效」＝移動點數本來就在回合開始重設、旗標清除，可再跑）。
- `battle.run_problem`：不合法的原因依序為「已經跑過了」「被定身，不能跑」「AP 不足：需要 N，剩餘 M」。合法時 `legal_actions` 才列出 `Run`；`has_only_end_turn` 也把跑步算進去（見待決定 #3）。
- 事件 `UnitRan`（`unit_ran`：`unit_id`、`bonus`、`move_points`）；中文紀錄：「X 跑步（本回合移動 +3，剩餘 N）」（`narrative/events.py`）。
- 算「移動類」：跑步時 `moved_this_turn = True`（連段條件 `moved_this_turn`）。沒有觸發被動技的 `on_move`（待決定 #2）。
- 固定 +3，不受加速／緩速倍率影響：只在回合開始時 `move_points_for_turn` 乘倍率，跑步是之後直接 `+= bonus`。

**預覽與 API**
- `Preview.run_range`／`PreviewOut.run_range`：跑完之後本回合能停留的格子（依 (y, x)，不含目前位置）；`ap_cost` 也填入。
- `BattleResponse.run_option`（`RunOptionOut`：`legal`、`reason`、`ap_cost`、`move_bonus`；輪到主角時才有）：不合法時給前端顯示原因。
- 重產 `client/openapi.json`、`client/src/api/schema.d.ts`（只新增欄位與型別）。

**AI**（`engine/ai/utility.py` 的 `run_score`；數值在 `content/ai_profiles.yaml` 的 `run:`，標為平衡階段初值；`RunAiRules` 在 `content/environment.py`）
- 只在**移動點數用完**（先走再跑）時才考慮：先走的走位評分不會被跑步搶走（`test_archers_out_of_range_of_each_other_still_approach`），先跑或後跑的總移動量相同。
- 追擊：沒有任何敵人在「目前位置」的攻擊距離內、跑步後（+3 格）走得到 → `pursue_points`（6）。
- 撤離：HP 低於 `retreat_hp_permille`（350‰）、最近敵人在 `retreat_enemy_radius`（4）格內、跑步後能走到離最近敵人更遠的格子 → `retreat_points`（6）。低血量只考慮撤離，不追擊。
- 其餘一律 0 分（不會跑）；`speed == 0` 的單位（木樁、圖騰）永遠不跑。敵我同一套 AI，所以敵人也會跑；隊友指令沒有新增。
- 攻擊距離用 `attack_reach`（普攻），不看技能射程，所以純技能型單位的「追擊」偏保守。

**前端**
- 行動面板（`ui/TurnControls.tsx`）在「防禦」旁加「跑步」鈕：合法時可按（立即送出，同防禦）；滑過／聚焦時送預覽，格子高亮改成「跑步後的移動範圍」；不合法時灰掉，`title` 與按鈕下方一行小字顯示原因（`battle/runAction.ts` 的純函式 `runButton`、`runRangeTiles`）。跑步後移動範圍由新的 `legal_actions` 立即更新；戰鬥紀錄多一行。
- `ModeKind` 加 `run`、`BASIC_MODES` 加「跑步」（不進技能列、不進備援清單）；`actionLabel` 加「跑步」。`styles.css` 只在檔尾新增。沒有動 `render/`、`heightModel.ts`、`stageLayout.ts`、`BattleCanvas.tsx`、`vfx.ts`。

## 2. 驗收（20.2）

| # | 條件 | 結果與證據 |
|---|---|---|
| 1 | pytest：+3 格、每回合 1 次、定身不能跑、不受加速／緩速影響、回合結束失效、AP 扣除、同種子重播一致；AI 追擊與撤離會跑、平常不跑；敵方也能跑 | 通過。`tests/engine/test_run.py`（17 項）：`test_run_adds_three_move_points_and_costs_one_ap`、`test_run_value_comes_from_core_rules_not_hardcoded`、`test_run_extends_move_range`、`test_run_only_once_per_turn`、`test_rooted_unit_cannot_run`、`test_run_needs_ap`、`test_run_bonus_ignores_haste_and_slow_multiplier[hasted/slow]`、`test_run_expires_at_turn_end`、`test_same_seed_replays_identically`、`test_preview_shows_move_range_after_run`、`test_ai_runs_when_target_is_outside_move_range_but_within_run_range`、`test_ai_does_not_run_when_already_in_reach_or_far_away`、`test_ai_runs_to_retreat_when_low_on_hp`、`test_ai_does_not_retreat_with_healthy_hp_or_distant_enemy`、`test_enemy_can_run_too`、`test_ai_run_battle_logs_run_and_replays`。 |
| 2 | `trpg battle --map <任一> --seed <n> --log-json f` 再 `trpg battle replay f` 一致，紀錄至少一次跑步 | 通過。`tests/cli/test_run_battle_cli.py`（`open_plain` 種子 0、`dark_forest` 種子 2）：紀錄含 `run` 動作與 `unit_ran` 事件、輸出有「跑步（本回合移動 +3」、重播顯示「重播驗證通過」。 |
| 3 | vitest：跑步按鈕狀態與原因；截圖 `docs/phases/img/3-20-*.png` | 通過。`client/src/battle/runAction.test.ts`（按鈕狀態、三種原因、無資料時的通用原因、備援清單不含跑步、預覽範圍轉高亮格）；vitest 全部 472 項通過。截圖：`3-20-before-run.png`（跑步前，移動範圍 20 格）、`3-20-run-preview-range.png`（滑過跑步鈕，範圍擴大、預覽卡 AP 1）、`3-20-after-run-blocked.png`（跑步後移動 8、範圍 34 格、鈕灰掉並顯示「跑步：已經跑過了」，紀錄有跑步一行）。 |
| 4 | `check.py` 全過、`pnpm build` 成功 | 見第 5 節。 |

另：`tests/api/test_routes.py` 的預覽欄位集合加入 `run_range`；`tests/api/test_openapi_snapshot.py` 在重產後通過；`lint-imports`（6 個合約）通過。

## 3. `LOG_FORMAT` 與舊 log

- `LOG_FORMAT` 由 `trpg-battle-log/34` 遞增為 `/35`（`runner.py` 註解說明）。
- 舊 `/34` 紀錄：步驟本身（沒有 `run`）在新引擎的結算不變，但 `trpg battle replay` 與戰鬥中存檔（`roguelite/save.py`）一律先比對格式字串，不符就拒絕，與歷來遞增版本的慣例相同；所以 `/34` 紀錄**不能**由新版重播（會被拒絕，不是重播出不同結果）。更重要的是：同種子的 AI 對戰會因為 AI 會跑步而軌跡不同，這是遞增的真正原因。
- 新增的核心規則欄位（`run_ap_cost`、`run_move_bonus`）為必填，舊規則包不相容。

## 4. 既有測試的調整（AI 軌跡改變）

AI 現在會跑步，同種子的整場 AI 對戰軌跡改變，下列依特定種子的整場測試需換種子（斷言內容不變）：`test_summon_ai`（dark_forest 0→25）、`test_gamble`（3、4→5、24）、`test_combo_resources`（warlock 1→5）、`test_reaction_events_3d3`（ranged open_plain 6→1）、`test_scene_ai`（pierce 0→4）、`test_displace_ai`（void swap 0→3）、`test_event_filter`（trapper 整場 1→2）、`test_striker_trapper_battle`（striker 57→69、trapper 1→2）、`tests/roguelite/helpers.py` 的 `VICTORY`（`("build_banisher", 0)` → `("build_banisher", 2)`）；`test_battle_cli`、`test_skills_cli` 的格式字串 `/34` → `/35`；CLI 輸出雜湊快照以 `UPDATE_CLI_SNAPSHOTS=1` 重產（`tests/cli/snapshots/cli_output_hashes.json`，6 筆戰鬥輸出改變，原因即上述）。

粗略影響評估（非正式）：`build_banisher` 種子 0–9 各打一輪，AI 代打的平均通過場數「有跑步」4.2、「關掉跑步」4.2；`build_trapper` 在 dark_forest 種子 0–11 的 12 場中召喚 2 次（關掉跑步時 3 次）。正式平衡請在平衡階段以模擬決定（待決定 #6）。

## 5. 檢查

結果見 `check.py` 輸出（最後一次）：

- `uv run python scripts/check.py`：第一次執行時 pytest 有 2 項失敗（`test_ai_deadlock` 的弓手對峙、`test_event_filter` 的陷阱整場），原因是 AI 在移動點數還沒用完時就選擇跑步（`Run` 搶在 `Move` 前），已改成「移動點數用完才考慮跑步」並重新釘種子；修正後全部 pytest（`uv run pytest -q tests -n auto`）3315 項通過、ruff／format／mypy／lint-imports／client typecheck／vitest 通過（最後會再完整執行一次 `check.py`，結果記於 commit 後的驗收註記）。
- `corepack pnpm -C client build`：成功（僅有既有的 chunk 大於 500 kB 警告）。
- `uv run ruff check .`、`ruff format --check .`、`uv run mypy`（429 個檔案）、`lint-imports`：通過。

## 6. 新增的複雜度 noqa

無。`_has_ap_action` 的 `PLR0911`、`UtilityAI.rank` 的 `PLR0912`、`preview._cost_and_reach` 的 `PLR0911` 都以重構解決（合併條件、`Defend | Run` 同一分支、`ap_cost` 在 `_build` 補），沒有加 `# noqa`。

## 7. 待 PM 決定

1. **速度 0 的單位**：引擎層面仍允許 `Run`（規格只寫定身不能跑）；AI 對 `speed == 0`（木樁、圖騰）不跑，否則靶場木樁會「跑」。是否要讓引擎也禁止速度 0 的單位跑步？
2. **「移動類」的範圍**：目前只設 `moved_this_turn = True`（連段條件），沒有觸發被動技 `on_move`（避免花 1 AP 就能無位移觸發移動被動）。是否要讓跑步也觸發 `on_move`？若有「本回合移動格數」類統計（目前沒有），需另外決定跑步是否計入。
3. **`has_only_end_turn`**：跑步合法時不自動結束回合，所以只剩跑步可做（例如已防禦、AP 有剩、無其他動作）時，玩家回合不會被自動跳過；AI 則由評分決定（0 分就結束回合）。
4. **AI 攻擊距離**：追擊只看普攻射程，不看技能射程；主要靠技能輸出的單位追擊會偏保守。
5. **AI 數值**：`pursue_points`／`retreat_points` 6、`retreat_hp_permille` 350、`retreat_enemy_radius` 4 皆為初值，未經模擬。AI 只在移動點數用完後才跑（先走再跑）；追擊分數比防禦（1×附近敵人數）高。
6. **平衡影響**：跑步讓整體戰鬥節奏略快（召喚類種子 pinned 測試需換種子）。數值 3 與 AI 權重請在平衡階段以模擬調整；本階段未跑大型模擬。
7. **前端預覽**：滑過「跑步」鈕時高亮改為「跑步後的移動範圍」，沒有另外標出「新增的格子」；若要區分新增格需動 `render/`（本階段不碰）。
8. **舊存檔**：戰鬥中的 `/34` 存檔會被拒絕讀取（慣例）；戰鬥之間的存檔不受影響。
9. **`ai_profiles.yaml` 結尾**：新增的 `run:` 區塊接在檔尾（沿用既有「表格層級規則」的位置慣例，只有一個表格層級欄位，不分享到各行為模式）。
