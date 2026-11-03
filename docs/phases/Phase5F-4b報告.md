# Phase 5F-4b 完成報告：影子循環賽收尾

範圍：`docs/phases/Phase5計畫.md` 第 1 節 5F-4b 列（規格摘要補在第 37 節）；背景 `Phase5F-4報告.md` 待 PM 決定 1～8。依玩法 PM 2026-11-03 代決與開發 PM 的保守代決。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | 平衡：循環賽開場最大 HP ×2、第 1 輪雙方都不能造成傷害。資料化的引擎旗標：`StatusDef.truce`（帶有者不受、也不造成任何傷害，含召喚物、墜落、致命地形；只能 `polarity: neutral`）＋新的到期方式 `expires: round_end`（每一輪結束、環境回合之後 −1）。新狀態 `league_truce`；`LeagueRules` 加 `hp_permille`、`opening_statuses`、`first_opening_statuses`（載入時檢查狀態存在）。只在 `trpg.world.league.league_unit` 套用，一般戰鬥不受影響（swamp 種子 7 重播結果和之前相同） | `content/statuses.yaml`、`content/world/season.yaml`、`content/battle.py`、`engine/turns.py`、`engine/effects/handlers.py`、`engine/rules/statuses.py`、`content/world_season.py`、`content/library.py`、`world/league.py` |
| 2 | 平衡候選腳本：候選規則 × 預設 build 組合 × 地圖輪替 × 交換先後手，輸出摘要表 | `scripts/league_balance.py` |
| 3 | 同分排名（6.8 BAL-12a）：勝場 → 所有場次己方剩餘 HP 比例（‰）合計 → 總輪數（少的勝）→ 同名次（`tied`，冠軍行註明「同分，平分獎金」）。每場記 `ally_hp_permille`、`enemy_hp_permille`（主角，不含召喚物） | `server/league.py`、`api/league_view.py` |
| 4 | 編年史：全部場次跑完時寫 `<世界>/chronicle/league.json`（`trpg-chronicle-league/1`：名次、帳號、名字、build 名〔武器・種族〕、勝負和、HP 合計、總輪數、同分），同一季重跑時取代；季末政策表標紀念類；`LeagueRecord.entries` 定為數值類（移出 `PROVISIONAL`） | `server/chronicle.py`、`server/season_policy.py`、`world/shadows.py`（`shadow_role_zh` 從 api 搬來共用） |
| 5 | 自動開跑：第 14 天刷新後（`season_day > signup_close_day`）、至少 2 人、這一季沒有 `season_boss` 首殺紀錄（讀 `first_kills.json`；讀不了＝還沒首殺）→ 自動凍結報名開跑。換日是被動的：每個世界動作之後與 `GET …/league` 時檢查；已開跑還有 `pending` 時也順便接續。管理者 `POST /api/world/league/run` 保留 | `api/world.py`（`auto_start_league`、`season_boss_killed`）、`api/routes/world.py` |
| 6 | 報名時免費重新配點（#32）：`league_enter.allocation`（拉到上限後全部可配的點＝已分配＋未分配＋升到上限多出的，總和必須剛好；`None`＝照自動配點，結果和 5F-4 相同）。存在 `LeagueEntry.allocation`，不改角色本身。`LeagueView.allocation`（基礎屬性、點數、自動配點）；前端報名區重用 `AttributeAllocator`，「照自動配點」鈕，點沒用完不能送出 | `world/league.py`、`world/league_actions.py`、`world/state.py`、`api/league_schemas.py`、`client/src/world/LeaguePanel.tsx`、`league.ts` |
| 7 | 重播結束面板中性文字：`LeagueReplayResponse.outcome_zh`（「某某 勝」／「和局」），`EndPanel` 的 `heading` 取代「勝利！／敗北……」；場次結果文字也改成「某某 勝（N 輪）」 | `api/league_view.py`、`client/src/ui/EndPanel.tsx`、`screens/BattleScreen.tsx`、`battle/BattleBottomBar.tsx`、`WorldScreen.tsx` |
| 8 | 規則改了就整個重跑：賽程記規則鍵（`LOG_FORMAT`＋規則包雜湊＋循環賽規則雜湊，`LeagueRecord.rules_key`）。不同時：畫面標「規則已變、不能重播」（`stale_zh`、每場 `replay_problem_zh`）、重播 409、背景不接續；管理者再開跑 → 舊賽程與戰鬥紀錄搬到 `league/archive/`（標 `stale_zh`）、用同一份凍結報名重排、全部重跑（`reruns`+1）。5F-4 的舊賽程沒有規則鍵＝視為已變 | `server/league.py`、`api/routes/world.py` |
| 9 | 場次列表分頁：`GET …/league?page=&page_size=`（預設 20、最多 100；超過範圍夾到最後一頁；自己的場次在前）；前端上一頁／下一頁 | `api/routes/world.py`、`api/league_view.py`、`client/src/api/client.ts`、`LeaguePanel.tsx` |
| 10 | OpenAPI 與 `schema.d.ts` 重產 | `client/openapi.json`、`client/src/api/schema.d.ts` |

存檔：新欄位都有預設值，`trpg-world/1`、`trpg-wlog/1`、`trpg-league/1` 不升版。`LOG_FORMAT` 不變：新的 `StatusDef` 欄位與 `expires` 值都有預設、舊內容的結算完全相同，照 `戰鬥紀錄格式變更.md` 1.2 不升版號（規則包雜湊會變，舊紀錄由 `ruleset_hash` 擋下，循環賽另由規則鍵標示）。

## 平衡摘要表

`uv run python scripts/league_balance.py --pairs 100 --jobs 8`：29 個預設 build（排除形態測試用的 2 個與 17 個空白 build）取 100 對組合 × 交換先後手＝每組 200 場，地圖照 `open_plain`／`dark_forest`／`swamp` 輪替。勝率＝勝場 ÷ 全部場次。

| 候選 | 場數 | 平均輪數 | 先手勝 | 後手勝 | 和局 | 達標 |
|---|---|---|---|---|---|---|
| 目前（5F-4） | 200 | 3.5 | 42% | 58% | 0% | 否 |
| 第 1 輪休戰 | 200 | 4.0 | 45% | 55% | 0% | 否 |
| HP ×2 | 200 | 5.9 | 42% | 58% | 1% | 否 |
| **HP ×2＋第 1 輪休戰** | 200 | **6.4** | **44%** | **54%** | 1% | **是** |
| HP ×3＋第 1 輪休戰 | 200 | 8.2 | 44% | 54% | 1% | 是 |

結論：第一順位「HP ×2＋第 1 輪休戰」就達標（平均 6.4 輪、先手 44%／後手 54%），已寫進 content；「拉開站位」與「先手少 1 AP」沒有用到、沒有實作（`first_opening_statuses` 已留好，先手少 1 AP 只要加一個 `ap_penalty: 1` 的狀態）。HP ×3 輪數更長但先後手比例沒有改善。後手仍略佔優（54%），貼近上限。

## 檢查

- `ruff check`、`ruff format --check`、`mypy`（1194 檔）、`lint-imports`（13 契約）通過。
- `tests/engine tests/world tests/api tests/server tests/content tests/test_architecture.py`（`-n 8`）：7296 通過（合併 main 後；`glossary.json` 加了 `league_truce` 的說明，照慣例用 `scripts/export_client_fixtures.py` 重產）。
- vitest 139 檔 1283 通過（新狀態加了圖示 `league_truce`：圓裡的暫停符號）；`pnpm build` 通過。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致（和 5F-1b 相同，一般戰鬥不受影響）。
- 循環賽重播：瀏覽器那次的 `m0003.json` → `trpg battle replay` 通過（24 個動作、99 個事件，open_plain）。
- 瀏覽器（8210 埠、自己的分頁與暫存存檔）：兩個角色，一個經 API 報名、一個在面板把智力的 3 點改配體質後報名（顯示「自己配點」，點沒用完時按鈕停用並提示）→ 存檔的開賽日往前調一天到第 14 天 → 打開循環賽面板自動開跑，12 場跑完：排行榜顯示同分比較數字（「剩餘 HP 合計 244%・共 61 輪」）、冠軍、場次結果「A-Wu 勝（4 輪）」→ 重播 m0003：開場兩人都有「開場休戰」、HP 134（加倍），結束面板顯示「Mei 勝（全滅）・第 4 輪」；`chronicle/league.json` 寫入最終排名。
- 新測試：`tests/engine/test_truce.py`（8）、`tests/world/test_league.py`（+8：平衡規則只套循環賽、6 場第 1 輪沒有傷害事件且休戰在第 1 輪結束移除、重新配點）、`tests/server/test_league_runner.py`（同分改寫＋3：編年史、規則改了整個重跑、舊賽程沒有規則鍵）、`tests/api/test_world_league.py`（改＋1：首殺擋自動開跑、自動開跑、配點經 API、分頁、規則已變 409 與重跑）、`tests/content/test_world_season.py`（+3）、`client/src/world/league.test.ts`（+4）；`test_coverage.py` 允許清單加 `league_truce`。
- CLI 快照：`tests/cli` 跑過一次，`test_output_snapshots` 沒有變動；`test_llm_propose_cli.py::test_mock_n3_snapshot` 失敗，但把 `src`、`content`、`tests/cli` 換回本段開工的 commit（`db6487d7`）一樣失敗，是既有問題、不是本段造成的，所以沒有重產（待 PM）。

## 代決（最保守）

| # | 事項 | 代決 |
|---|---|---|
| 5F4b-1 | 「第 1 輪不能造成傷害」的做法 | 資料化的狀態旗標 `truce`＋`expires: round_end`，不改戰鬥紀錄格式。原本想用既有的 `damage_taken_permille: 0`，但骰值傷害有 `min_damage` 1 點，召喚物也會在主人的狀態到期後出手，所以另加旗標。傷害直接略過、不發事件；debuff、表面、推擊照常（只擋傷害） |
| 5F4b-2 | 休戰擋到哪 | 目標、來源、來源的召喚者任一帶休戰就不結算；沒有來源的環境傷害打在沒有休戰的召喚物身上照常（極少見） |
| 5F4b-3 | HP ×2 怎麼算 | 裝備與體質算完的最大 HP × 倍率（無條件捨去），在範本的 `max_hp` 加上差額；每場 HP 滿 |
| 5F4b-4 | 「同分」 | 勝場數完全相同才比 HP 比例（BAL-12a 原文的「勝場差 ≤ 1 視為同分」是矩陣量測用、排名上不可遞移，沒有採用）；不再比負場、報名時間（報名時間只決定同名次的列出順序） |
| 5F4b-5 | 剩餘 HP 比例 | 主角結束時 HP ÷ 最大 HP（‰，倒下＝0），不含召喚物；和局也算 |
| 5F4b-6 | 編年史放哪 | 獨立檔 `chronicle/league.json`（循環賽的 `league.json` 下一季會換掉），只在全部場次跑完時寫；名字與 build 名照凍結報名當時；build 名＝影子的定位（武器・種族） |
| 5F4b-7 | 自動開跑的時機 | 沒有排程器：每個世界動作之後與看循環賽畫面時檢查（被動換日）。伺服器重啟後有 `pending` 的賽程也在這時接續；規則已變的賽程不自動重跑，等管理者開跑 |
| 5F4b-8 | 「已首殺」的判定 | `first_kills.json` 裡有這一季 `kind: season_boss` 的紀錄；檔案讀不了就當作還沒首殺 |
| 5F4b-9 | 重新配點的範圍 | 全部可配的點（已分配＋未分配＋升到上限多出的）免費重配；基礎屬性（開局的）不動；總和必須剛好；和自動配點一樣時不送（存 `None`）；每次重新報名都可以改 |
| 5F4b-10 | 規則鍵 | `LOG_FORMAT`＋基礎規則包雜湊＋循環賽規則雜湊。只改引擎程式、沒有升 `LOG_FORMAT` 時偵測不到（照版號政策這種改動本來就不改結果） |
| 5F4b-11 | 規則改了且賽程已經跑完 | 也標「規則已變、不能重播」；管理者再開跑才重跑（重跑完編年史那一季被取代） |
| 5F4b-12 | 分頁 | 每頁 20、最多 100；排行榜不分頁 |

## 待 PM 決定

1. **後手仍略佔優**（54%／44%）：在 40～60% 內但接近上限。要不要再加「先手少 1 AP」把比例拉近（`first_opening_statuses` 已可用，只差一個狀態），或維持現狀。
2. **BAL-12a 的「勝場差 ≤ 1 視為同分」**要不要用在循環賽排名（目前只有勝場完全相同才比 HP）。
3. **規則改了但賽程已跑完**：要不要自動重跑（目前只標示、等管理者），以及重跑後編年史被取代是否可以。
4. **自動開跑沒有排程器**：伺服器沒人動的話要等到第一個請求才開跑；要不要加一條換日排程（或 Bot 指令）。
5. `tests/cli/test_llm_propose_cli.py::test_mock_n3_snapshot` 在 main 上就失敗（Mock 提議第 2 題的元素從「雷電」變「風」），要不要由開發 PM 另外重產。
6. 編年史目前只有循環賽排名；其他編年史內容（首殺、配方發現）要不要收進同一個資料夾，留 5F-5。
