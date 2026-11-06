# Phase 3-22 報告｜勝利條件輪替（玩法 #23）

> 規格：`docs/phases/Phase3計畫.md` 第 24 節；設計：`docs/design/05-戰鬥.md` 5.8、`docs/玩法決定紀錄.md` #23。分支 `worktree-agent-ac50cab0f39315658`（從 main d4a1df0 分出），未 push、未合併。

## 1. 做了什麼

**地圖資料**（`content/maps/*.yaml`、`trpg/content/maps.py`）
- `MapDef.alt_objectives`（可選）：`escape`（出口格＋輪數）、`defend`（守點格＋輪數）。驗證：至少一個、格子在地圖內、不重複、**不與任何起始區重疊**、可站立（含物件規則）、我方每個起始格都走得到目標格（連通性，`check_map`）。`MapDef.supports_objective(kind)`、`objective_for(kind)` 組出引擎用的 `Objective`。
- 補資料的地圖（地圖池共 9 張）：**可撤離 7 張**（bridge_chasm、lava_crossing、frozen_lake、dark_forest、open_plain、swamp、narrow_halls；出口在敵方側的角落或對岸），**可守點 7 張**（cliff_outpost、oil_depot、narrow_halls、swamp、dark_forest、open_plain、bridge_chasm；守點是我方起始區附近的單一格，例如橋頭、階梯底、長廊口）。輪數：撤離 6～8（冰湖 8、長廊 7）、守點 6。

**roguelite**（`content/roguelite.yaml` 的 `objective_rotation: {min_escape: 1, min_defend: 1}`；`trpg/roguelite/start.py`）
- 抽一輪時一併決定每場勝利條件，存在 `BattlePlan.objective`（`eliminate`／`escape`／`defend`）；撤離與守點的格子、輪數在開戰時由 `map.objective_for(...)` 取得（`progress.battle_setup`）。Boss 戰固定全滅。同一輪地圖類型仍不重複。
- 抽法：沿用原本的地圖類型與地圖抽選（`plan/map_types`、`plan/map/<i>`），之後以 `plan/objective/<kind>/<n>` 挑場次；被選中的場次若地圖不支援就在**同類型**內以 `plan/map/<i>` 重抽支援的地圖。
- 跨檔案檢查（`roguelite_problems`）保證「不論抽到哪幾種地圖類型都排得出來」：支援某條件的地圖類型數 ≥ 未被抽中的類型數 ＋ 兩條件最少場數總和（目前 8 類型、抽 5：撤離 6 類、守點 7 類，需 ≥ 5）。

**AI**（`trpg/engine/ai/objective.py`、`content/ai_profiles.yaml` 的 `objective_ai:`，填入每個行為模式的 weights，沿用 `facing` 的機制；`AiWeights` 新增 `contest`、`intercept`、`rush_exit`、`hold_point`、`hold_radius`、`hold_guard`，初值未經模擬）
- 撤離戰：我方朝出口（`objective` ＋ `rush_exit`）；敵方攔截出口路線（`intercept`：離最近出口越近越好；原本敵方在撤離戰完全不看出口）。
- 守點戰：敵方搶點（`objective` ＋ `contest`）；我方守在點附近（離守點超過 `hold_radius` 格才扣 `hold_point`），且在守點半徑內、6 格內有敵人時「守護」動作多加 `hold_guard`。
- 非撤離／守點的戰鬥所有新權重都不生效（行為與先前完全相同；`_objective_distance` 併入新模組後移除）。

**CLI**：`trpg battle --objective escape|defend`（用地圖的 `alt_objectives`，沒有資料時錯誤結束碼 2）；新腳本 `scripts/sim_objectives.py`（見第 4 節）。

**API**：`BattlePlanOut.objective`（本場勝利條件；欄位只新增）。重產 `client/openapi.json`、`schema.d.ts`。

**網頁**（`client/src/battle/objective.ts` 為純函式集中處）
- 一輪畫面：下一場面板加一行「➜ 撤離：5 輪內全員抵達出口」，進度列每場帶圖示徽章（⚔ 全滅／➜ 撤離／◎ 守點）。
- 戰鬥開場橫幅「戰鬥開始」下加一行本場勝利條件（撤離與守點多停一倍時間）。
- HUD（頂端回合列）常駐一個徽章：「➜ 撤離・剩 4 輪」「◎ 守點・最後 1 輪」「⚔ 全滅」。
- 地圖畫出口格（綠色門形框＋「出」）與守點格（金色雙圈＋「守」），畫在 `deco` 層並用 `place`（`tileLift`）跟著格子抬高；格子資訊卡新增「objective」段落說明規則與剩餘輪數。
- 結算畫面加一行原因說明：撤離成功、守住了、守點失守、撤離超時（`endDetail`）。
- CSS 只在 `styles.css` 檔尾新增。

## 2. 存檔與 LOG_FORMAT

- **存檔格式 `trpg-run/1` → `trpg-run/2`**（`BattlePlan` 多了 `objective`）。**舊存檔明確拒絕**：`存檔格式必須是 trpg-run/2，收到 'trpg-run/1'（舊版存檔無法讀取，請開新一輪）`（`tests/roguelite/test_save.py::test_wrong_format_and_engine_are_rejected`）。
- **`LOG_FORMAT` 未遞增**（維持原值）：`BattleSetup` 的結構沒變（`objective` 欄位本來就有）；`MapDef` 只新增可省略的 `alt_objectives`，舊紀錄仍可重播。AI 權重只影響「產生」紀錄，不影響重播。因此沒有 `LOG_FORMAT` 合併衝突。

## 3. 驗收

| 條件 | 證據 |
|---|---|
| 24.2-1 地圖 `alt_objectives` 驗證 | `tests/content/test_alt_objectives.py`：`test_alt_objectives_build_the_matching_objective`、`test_missing_kind_is_unsupported`、`test_validation_rejects_bad_alt_objectives`（空、輪數 0、無格、重複、超出範圍、落在我方／敵方起始區）、`test_check_map_requires_standable_and_reachable_tiles`、`test_shipped_pool_maps_cover_enough_escape_and_defend`（≥4 撤離、≥4 守點、隨附資料通過 `check_map`） |
| 一輪至少 1 撤離、1 守點且確定；Boss 全滅 | `tests/roguelite/test_objective_rotation.py`：`test_every_run_has_at_least_one_escape_and_one_defend`（60 個種子）、`test_boss_battle_stays_eliminate`、`test_plan_is_deterministic_and_varies_with_the_seed`、`test_battle_setup_uses_the_map_objective_data`、`test_rotation_rules_are_content_and_validated`；`tests/api/test_runs_api.py::test_run_plan_carries_each_battles_objective` |
| 存檔版本 | `tests/roguelite/test_save.py::test_wrong_format_and_engine_are_rejected`、`tests/api/test_runs_api.py::test_corrupt_save_is_422`、`tests/cli/test_run_cli.py` |
| AI 搶點與朝出口 | `tests/engine/test_objective_ai.py`（7 項）：評分函式的撤離我方／敵方、守點敵方／我方、`hold_guard` 條件；`test_enemy_ai_moves_toward_the_exit_with_intercept_weight`、`test_ally_ai_moves_toward_the_exit`、`test_defend_enemy_ai_rushes_the_point`（用 `UtilityAI` 實際決策） |
| 撤離與守點各一場 `--log-json` ＋ `replay` 一致 | `tests/cli/test_battle_cli.py::test_objective_battle_log_and_replay[bridge_chasm-escape-…]`、`[swamp-defend-…]`、`test_objective_option_rejects_maps_without_the_data` |
| 24.2-2 模擬摘要表 | 第 4 節 |
| 24.2-3 vitest | `client/src/battle/objective.test.ts`：勝利條件文字、徽章、剩餘輪數、標記繪製資料（`buildDrawModel(...).markers`）、格子資訊卡段落、結算原因、下一場畫面（`runView`） |
| 24.2-3 截圖 | `docs/phases/img/3-22-opening.png`（開場）、`3-22-map-escape.png`／`3-22-map-defend.png`（地圖上的出口與守點；HUD）、`3-22-tile-card-exit.png`／`3-22-tile-card-point.png`（資訊卡）、`3-22-hud-last-round.png`（HUD「最後 1 輪」）、`3-22-run-plan.png`（選路／下一場畫面）、`3-22-end-defended.png`／`3-22-end-escape-failed.png`／`3-22-end-point-lost.png`（結算原因）。工具：Chrome DevTools Protocol 腳本在 8123 埠截圖（沒有動 8000 埠）。沒有「撤離成功」的結算截圖（見待決 9） |
| 24.2-4 `check.py` 全過、`pnpm build` 成功 | `uv run python scripts/check.py` 全部通過（ruff、format、mypy、lint-imports、pytest、client install／typecheck／test）；`corepack pnpm -C client build` 成功 |

## 4. 模擬摘要

`uv run python scripts/sim_objectives.py --seeds 20 --jobs 8`：每張補了資料的地圖用自己的標準陣容（`encounter`：戰士、弓手、法師 vs 盜賊組）＋效用 AI，各 20 場；全滅基準欄是同陣容、全滅條件的勝率（對照）。

**最終（現在的資料）**

| 地圖 | 條件 | 輪數 | 格子 | 我方勝率 | 平均輪數 | 全滅基準 |
|---|---|---|---|---|---|---|
| bridge_chasm | 撤離 | 6 | (9,0)(9,1)(9,8)(9,9) | 90% | 3.6 | 75% |
| bridge_chasm | 守點 | 6 | (3,2) | 55% | 3.9 | 75% |
| cliff_outpost | 守點 | 6 | (3,4) | 50% | 4.1 | 70% |
| dark_forest | 撤離 | 6 | (9,0)(9,1)(9,8)(9,9) | 95% | 3.9 | 100% |
| dark_forest | 守點 | 6 | (2,4) | 70% | 3.8 | 100% |
| frozen_lake | 撤離 | 8 | (11,0)(11,1)(11,8)(11,9) | 100% | 6.2 | 90% |
| lava_crossing | 撤離 | 6 | (9,0)(9,1)(9,8)(9,9) | 80% | 4.4 | 90% |
| narrow_halls | 撤離 | 7 | (11,0)(10,0)(11,8)(10,8) | 100% | 4.0 | 80% |
| narrow_halls | 守點 | 6 | (4,5) | 75% | 3.4 | 80% |
| oil_depot | 守點 | 6 | (1,4) | 35% | 3.0 | 80% |
| open_plain | 撤離 | 6 | (9,0)(9,1)(9,8)(9,9) | 95% | 3.8 | 55% |
| open_plain | 守點 | 6 | (2,4) | 25% | 3.3 | 55% |
| swamp | 撤離 | 6 | (9,0)(8,0)(9,1) | 95% | 4.0 | 60% |
| swamp | 守點 | 6 | (2,6) | 30% | 2.9 | 60% |

**沒有勝率 0% 的組合。** 第一輪初版資料（撤離 8～9 輪、守點是 2 格且離敵人很近）的結果：撤離 80～100%（太寬鬆），守點 0～70%，其中 open_plain 守點 **0%**、oil_depot 15%、cliff_outpost 25%、swamp 25%、dark_forest 45%。因為 0% 與過低的守點不合理，我**只調整了一次**資料（守點改單格、移近我方側；撤離輪數縮到 6～8），之後沒有再調；初版表格與調整原因記在這裡供 PM 決定數值。守點仍偏難（open_plain 25%、swamp 30%、oil_depot 35%），撤離仍偏易（多數 ≥ 90%）。

**另外觀察**（`scripts/` 之外的臨時掃描，未進 repo）：把主角換成「只會結束回合」時，撤離常常超時（撤離要求主角本人也抵達出口）；敵方在撤離戰會站上出口格（`intercept` 生效），出口被占著時我方單位進不去。

## 5. 新增的複雜度 noqa 與理由

**無**（沒有新增任何 `# noqa`）。

## 6. 待 PM 決定

1. **數值**：撤離偏易（多數 ≥ 90%）、守點偏難（25～75%）。輪數、守點格位置與 `objective_ai` 權重（`contest 4`、`intercept 8`、`rush_exit 6`、`hold_point 10`、`hold_radius 2`、`hold_guard 4`）都是初值，建議平衡階段用 `scripts/sim_objectives.py` 對 build 矩陣統一調整。
2. **敵人站在出口格上**會擋住我方撤離（單位不能共用一格）。目前接受這是「攔截」的一部分；若覺得不好玩，可以讓出口格不允許敵方進入，或允許與敵方換位。
3. **守點格只有一格**；敵方單位在輪末站上去即敗，所以我方也可以直接站在點上擋住（目前 AI 會）。是否要改成多格或「占領計時」留給 PM。
4. **主角倒下**時撤離戰一定失敗（引擎規則：倒下的單位不能移動，也不會離開戰場）。目前保守不動；若要「帶走倒下的隊友」要另開規格。
5. **勝利後獎勵與場次**沿用全滅（每場固定 100 經驗）；撤離／守點沒有額外獎勵。
6. 一輪的重新抽取：舊 seed 的地圖／敵人安排在這次改動後**沒有變**（沿用原本的抽選標籤），只是多了勝利條件；但同 seed 的場次若被選為撤離或守點且原本的地圖不支援，會換成同類型的另一張地圖（目前只有 bridge_chasm 類型有兩張：吊橋與岩漿渡橋）。
7. **存檔 `trpg-run/2`**：舊存檔直接拒絕並提示開新一輪（保守做法，規格建議）。若要保留舊存檔可讀，需要為 `BattlePlan.objective` 補預設並在讀檔時標記，但那樣舊存檔的下一場不會有撤離／守點。
8. `scripts/sim_objectives.py` 只用地圖的標準陣容（含法師），與 roguelite 的「主角＋2 名標準隊友」不同；若要接近一輪的實況，建議之後加 `--allies` 選項。
9. 截圖缺「撤離成功」的結算畫面：網頁是主角手動操作，AI 代打整場的撤離成功我只能用腳本跑（`tests/` 與 CLI replay 有驗證 `escaped`），UI 上要手動把主角走到出口，沒有做。撤離成功的文字由 `objective.test.ts` 的 `endDetail` 驗證。
10. 圖例（Legend）還沒有「出口格／守點格」的說明項；資訊卡與橫幅已說明，圖例留給之後的介面小修。
