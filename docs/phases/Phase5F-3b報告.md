# Phase 5F-3b 完成報告：5F-3 收尾（敵人專用技能、碎晶之主平衡、解鎖對齊、帳號稱號）

範圍：`docs/phases/Phase5計畫.md` 第 1 節 5F-3b 列；背景 `Phase5F-3報告.md`（待 PM 決定 1、2、4、6）、`Phase5F-2b報告.md`、計畫第 37 節。依玩法 PM 2026-11-03 代決。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | 技能 schema 加選填 `enemy_only`（預設 `false`；`false` 時不輸出，既有技能的序列化、規則包雜湊、重產夾具的值都不變）。集中的玩家技能池 `player_skills(library)`／`is_player_skill(skill)`；關鍵字池（開局、候選）、候選產生器的關鍵字池與通用池、白板候選、LLM 提議的備援池與 `grant_skill` 可選清單、工坊的技能選單、修正規則的標籤候選、mock 提議、閃現評估、屬性建議的「前期拿得到的技能」全部改走它。敵人範本照常裝備、施放 | `src/trpg/content/skills/skill.py`、`src/trpg/content/player_pool.py`（新）、`skillgen/keywords.py`、`candidates.py`、`whiteboard_candidates.py`、`proposal.py`、`proposal_fallback.py`、`option_params.py`、`composer_special.py`、`llm/candidate_source.py`、`llm/flash_eval.py`、`api/attribute_text.py` |
| 2 | 標上 `enemy_only` 的技能（17 招）：霧鎖千山、霧遁、碎晶之主與源晶柱的 6 招（霧晶／雷晶／火晶脈衝、碎界脈動、晶蝕、界碎）、霧影分身（見待 PM 決定 1），以及合併 main 後 5F-5a 灰燼荒原的 8 招（熔岩噴發、熔心吸氣、熔心吐息、熔心爆、熔流潰堤、產下幼蜥、硫煙吐息、餘燼啃咬；開發 PM 通知） | `content/skills/` |
| 3 | 架構測試：`skillgen`、`llm`、`roguelite`、`world`、`api` 裡不准直接走訪 `library.skills`（`sorted(...)`、`.values()／.items()／.keys()`、`for`、推導式），只有列在白名單的函式例外（撞名檢查、ID→中文名對照、開發用的結構盤點，各附理由）；掃描器本身的正反例。另有行為測試：每個池子入口都不含這 9 招、敵人範本仍帶著它們 | `tests/test_architecture.py`、`tests/skillgen/test_enemy_only.py`（新） |
| 4 | 夾具與快照：`refactor_3wr2.json` 只對玩家技能池取樣（閃現的等距取樣點仍在全部內建技能上取，再去掉敵人專用，避免整排位移）並重產；`llm_propose_mock.txt`（`test_mock_n3_snapshot`）重產後回到 BAL-19f 的內容；`cli_output_hashes.json` 不變 | `tests/skillgen/test_refactor_3wr2.py`、`tests/skillgen/fixtures/refactor_3wr2.json` |
| 5 | 碎晶之主平衡（見下節） | `content/units/rift_shard_lord.yaml`、`content/statuses.yaml`、`scripts/season_boss_diagnose.py`（新） |
| 6 | 解鎖時間：`max(最早第 8 天, 集滿 + 24 小時)` 之後（含）的第一個刷新時刻（6 點），再和第 10 天強制解鎖取早；公告照舊是解鎖前 24 小時 | `src/trpg/world/season_boss.py` |
| 7 | 帳號紀念稱號「碎晶的終結者」：`AccountTitle`（`id`＝`season_boss:<Boss>`、名字、賽季、第一次拿到的角色、時間）、`AccountRecord.titles`（預設空，舊檔照讀、不升版）、`AccountStore.grant_title`（走 5D-R2 的帳號檔鎖：鎖內重讀再寫回；同一季同一個稱號只記一次）。每個打倒賽季 Boss 的帳號都拿到（19.7「所有打倒者得稱號」）；`WorldStore.grant_title` 由 `create_app` 接上，寫入失敗只記 log（同評分榜）。季末分類：`AccountRecord.titles` 與 `AccountTitle` 全部欄位都是紀念類。`AccountView.titles`（「碎晶的終結者（s1）」）；評分榜照舊顯示 | `src/trpg/server/accounts.py`、`season_policy.py`、`src/trpg/api/world.py`、`app.py`、`auth.py`、`account_schemas.py`、`client/openapi.json`、`client/src/api/schema.d.ts` |
| 8 | 新狀態 `rift_channel` 的圖示（菱形晶體＋往外三道線）、`test_budget` 狀態點數表與 `test_coverage` 允許清單、vitest 狀態數 116 → 117 | `client/src/render/statusIcon.ts`、`statusIcon.test.ts`、`tests/skillgen/test_budget.py`、`tests/content/test_coverage.py` |


## 碎晶之主：敗因、調整、前後勝率

工具：`uv run python scripts/season_boss_diagnose.py --seeds 80 [--set ...]`（同 `season_boss_sim.py` 的真實路徑：`prepare_battle` → 效用 AI 雙方；每組 8 個 build × 80 種子＝640 場；`--set` 不改 content 就能試候選：單位欄位、屬性、階段觸發、狀態欄位）。每場多記：停在哪個階段、敗因（主角與傭兵全倒／超過輪數；召喚物不算）、柱子全倒在第幾輪、我方對柱子與本體的傷害（主角／傭兵分開）、我方受到的傷害來源（敵方單位・技能）與倒下時的最後一擊。

### 5F-3 的 20%／40% 是 5 場的誤差

用 80 場重量（現值 380／60、沒有任何調整）：striker **50%**、trapper **28%**、整體 69%、平均 13.5 輪。所以要處理的主要是 trapper；striker 只是偏低。

### 原因（兩個 build 輸在同一個地方）

| | striker | trapper | 其他 6 個 build |
|---|---|---|---|
| 傭兵 | 預設鐵壁＋回春 | 預設鐵壁＋回春 | 守護／輔助主角帶赤焰（輸出） |
| 柱子全倒在第幾輪 | 7.8 | 9.5 | 3.1～6.5 |
| 對柱子的傷害 主角／傭兵 | 226／25 | 207／40 | 輸出主角也是主角打；守護、輔助主角由赤焰打 250 |
| 敗場停在 | 碎界脈動 14、界崩 13、三柱 13 | **三柱 25**、碎界脈動 17、界崩 14 | — |
| 敗場受到的傷害 | 碎晶之主「聚雷」約 70% | 「聚雷」約 74% | — |

1. **三柱階段打不動柱子**：鐵壁與回春幾乎不打柱子（傭兵合計 25～40），三根柱子只能靠主角一人打，比別人多花 3～6 輪；這段時間本體不受傷、卻每 2 回合一發「聚雷」，隊伍被慢慢磨死（trapper 有 25 場在柱子還沒打完前就全倒）。陷阱流的陷阱對不會移動的柱子與本體無效（`immovable`），主角實際只靠寒鎖與陷落打柱子。
2. **界崩來得太早**：柱子拖到第 9～10 輪才倒，第 2～3 階段還沒打完就到第 15 輪，傷害 ×2（trapper 平均 18.3 輪）。
3. 排除的假設：「聚雷」依目標身邊敵人數加傷，陷阱流的骷髏擠在一起會被多打——換成不加傷的版本後 trapper 30%，沒有差別（試完已刪掉試用的技能檔）。晶蝕（流血）在敗場只占受到傷害的 7～12%，不是主因。

### 調整（只改 Boss，#87）

| 項目 | 改前 | 改後 | 位置 |
|---|---|---|---|
| 三柱階段的本體 | 照常輸出 | 開場掛「灌注源晶」：造成的傷害 ×0.7；最後一根柱子碎掉進第 2 階段時移除（新狀態 `rift_channel`，中性、不能淨化） | `content/statuses.yaml`、`content/units/rift_shard_lord.yaml` |
| 界崩 | 第 15 輪起 | 第 18 輪起 | `content/units/rift_shard_lord.yaml` |
| 本體／柱子 HP | 380／60 | 380／60（不變） | — |

`LOG_FORMAT` 不變：沒有新的事件或欄位，狀態與階段都是既有機制（照 `戰鬥紀錄格式變更.md` 1.2）；規則包雜湊會變（Boss 內容改了），舊的首殺紀錄由 `ruleset_hash` 擋下。

### 前後勝率（每組 80 場／build）

| build | 改前勝率 | 改前輪數 | 改後勝率 | 改後輪數 | 改後敗場停在 |
|---|---|---|---|---|---|
| striker | 50% | 15.6 | **52%** | 17.4 | 碎界脈動 18、三柱 15、界崩 4 |
| fire | 66% | 14.9 | 60% | 15.2 | 碎界脈動 13、三柱 10、界崩 6 |
| storm | 65% | 14.4 | 72% | 14.6 | 碎界脈動 11、界崩 7 |
| ranged | 77% | 13.7 | 80% | 13.1 | 碎界脈動 9、核心過載 4 |
| tank | 86% | 11.2 | 86% | 11.8 | 碎界脈動 4、三柱 4 |
| guardian | 88% | 11.8 | 91% | 11.8 | 碎界脈動 3、界崩 2 |
| healer | 90% | 8.4 | 90% | 8.5 | 核心過載 6、碎界脈動 2 |
| trapper | 28% | 18.3 | **43%** | 19.6 | 三柱 17、界崩 15、碎界脈動 11 |
| **全部** | 69% | 13.5 | **72%** | **14.0** | — |

結果（合併 5F-5a 後重跑，逐場相同）：10～15 輪、每個 build ≥ 40% 達標；**整體 72%，比目標上限 70% 高 2 個百分點**（80 場的標準誤約 ±5%，trapper 43% 也在邊緣）。

### 其他候選（都是 80 場／build；HP 是 1 級基準）

| 候選 | striker | trapper | 整體 | 平均輪數 |
|---|---|---|---|---|
| 灌注 ×0.7（界崩 15） | 46% | 38% | 69% | 14.0 |
| 灌注 ×0.75（界崩 15） | 51% | 41% | 70% | 14.1 |
| 界崩 18（沒有灌注） | 55% | 32% | 70% | 13.6 |
| **灌注 ×0.7＋界崩 18（採用）** | 52% | 43% | 72% | 14.0 |
| 灌注 ×0.7＋界崩 18＋本體 420 | 48% | 38% | 69% | 14.5 |
| 灌注 ×0.6＋界崩 18＋本體 400 | 56% | 46% | 73% | 14.3 |
| 灌注 ×0.6＋界崩 18＋本體 420 | 55% | 45% | 72% | 14.6 |
| 灌注 ×0.5＋界崩 18＋本體 430 | 51% | 41% | 72% | 14.8 |
| 灌注 ×0.6＋界崩 18＋智力 17 | 60% | 43% | 75% | 14.1 |
| 本體智力 16 → 14（40 場） | 60% | 70% | 84% | 14.7 |
| 柱子 60 → 45（40 場） | 80% | 37% | 75% | 12.7 |

整體壓不到 70% 以下的原因：trapper 達到 40% 時，帶輸出傭兵的守護、輔助主角（tank／guardian／healer 86～91%，8～12 輪打完）也一起變容易；加本體 HP 會先拖垮最慢的 trapper。要同時達標，需要只對「打得快的隊伍」有效的機制（例如第 2～3 階段更早出強招、晶傀儡更多），見待 PM 決定 2。

## 檢查結果

（合併 main 後）

- `ruff check .`、`ruff format --check .`、`mypy`（strict，1205 檔）、`lint-imports`（13 kept）：通過。
- `pytest -n 8 -m "(slow or not slow) and not llm"` tests/engine、content、skillgen（含 slow 的 test_budget、test_refactor_3wr2）、llm、world、api、server、test_architecture：12396 通過、0 失敗（合併 5F-5a 後）。要連真實模型的 `llm` 標記測試沒跑。
- `tests/cli -m "slow or not slow" --timeout=3000`（不加 -n）：180 通過（`test_mock_n3_snapshot` 重產後；其餘快照不變）。`tests/sim/test_push_check.py`（slow）：5 通過。
- vitest：合併 5F-5a 前 1294 通過（140 檔）；合併後 `statusIcon.test.ts` 13 通過（狀態 117 個）；`pnpm build` 通過。
- 重播：swamp 種子 7 通過（88 動作、313 事件，和之前相同）；首殺重播通過（`trpg battle replay <世界>/season_boss/s1-first-kill.json`：209 動作、945 事件、rift_gate）。
- 產生檔：`client/openapi.json`、`schema.d.ts`（`AccountView.titles`）、`glossary.json`（新狀態）重產；`refactor_3wr2.json` 重產。
- 沒跑全量、matrix、completion。

### 夾具與快照的差異（以合併 5F-5a 後的 main 為準重產）

- `refactor_3wr2.json` 和 main 比：`complete`、`retier` 各少 17 筆（就是那 17 招敵人專用技能），`flash` 少 9 筆（餘燼啃咬、霧鎖千山、霧晶脈衝各 3 個種子，剛好在取樣點上），**其餘每一筆的值都相同、沒有新增**。
- 和 5F-3 之前（`28764907^`）比：`complete`、`retier` 只差霧鎖千山、霧遁（5F-2 加的，這次排除），其餘相同；`flash` 的鍵不同只是因為取樣點位移（技能總數變了），共同的鍵值全部相同。
- CLI `test_mock_n3_snapshot`：5F-3 之前 main 上失敗的原因其實是 5F-1b 的霧影分身進了技能池（第 2 題的召喚技從「雷電・召喚」變成「風・召喚」）。5F-5a 又把快照重產成含荒原敵人技能的版本（第 2 題「火焰・召喚」、第 3 題「暗影・打擊」）。排除敵人技能後重產：第 2、3 題回到「雷電・召喚」「暗影・控場（二）」，和 BAL-19f 的快照逐字相同。`cli_output_hashes.json` 不變。

## 代決（玩法 PM 2026-11-03；照做）

| # | 事項 | 實作 |
|---|---|---|
| 1 | `enemy_only` | schema 選填欄位；集中的 `player_skills`；架構測試；夾具與快照恢復 |
| 2 | 碎晶之主 | 380／60 不變；查出敗因後只調 Boss：三柱階段傷害 ×0.7、界崩延到第 18 輪 |
| 3 | 解鎖時間 | 最早第 8 天且滿 24 小時之後的第一個 6 點；第 10 天強制照舊 |
| 4 | 稱號 | 帳號層級紀念稱號，季末保留、評分榜照顯示、帳號檔欄位有預設值、走帳號檔鎖 |

實作時的保守做法：

- 霧影分身（`skill_summon_mist_shade`）不在指定的 8 招裡，但它的資料檔註解寫著「只給霧中劍客，不進技能池」，而且不排除它 CLI 快照就恢復不了，所以也標上（待 PM 決定 1）。
- 撞名檢查（LLM 命名、閃現評估）、技能 ID→中文名的對照、開發用的結構盤點與 `trpg skills` 清單照舊看全部技能（含敵人專用），不算玩家技能池。
- 稱號：每個打倒賽季 Boss 的帳號都拿（19.7「所有打倒者」），不只首殺；同一季只記第一次的角色；沒有帳號（開發模式）時不記。前端還沒有顯示帳號稱號的地方，只在 `AccountView.titles` 給出。
- 解鎖剛好落在 6 點時就是那個 6 點（「之後（含）」）。

## 待 PM 決定

1. **霧影分身也標 `enemy_only`**（見上）；不同意的話要把它拿掉並重產 CLI 快照（第 2 題會變成「風・召喚」）。另外荒原的「產下幼蜥」等技能若之後要給玩家，記得拿掉標記。
2. **整體勝率 72%**，比目標高 2 個百分點；每個 build ≥ 40% 與 10～15 輪都達標。要壓到 70% 以下又不讓 trapper 掉到 40% 以下，需要只對打得快的隊伍有效的 Boss 機制（候選：第 2 階段晶傀儡多 1 隻、或核心過載提早到 HP 60%），這兩個都會動到 19.7 的原文數字，所以沒有直接做。另一個選項是接受「灌注 ×0.75、界崩 15」（整體 70%、trapper 41%、striker 51%）——只改一處，但 trapper 更貼近 40% 的邊緣。
3. **19.7 原文的「第 15 輪起傷害加倍」改成第 18 輪**：設計文件只有使用者能改，我沒動 `docs/design/19-灰燼荒原與賽季主線.md`；若採用，請玩法 PM 附使用者原話更新 19.7。
4. 19.7 的 5F-3 代決段落寫了「全場傷害在回合結束、晶傀儡每 3 回合」，這兩項 5F-3 用現有機制近似（5F3-13），本段沒有做（需要新的引擎欄位）。
5. 帳號稱號要在哪裡顯示（大世界頂欄、角色列表、評分榜名字旁）由美術／開發 PM 排段。
