# Phase 5F-4 完成報告：影子循環賽

> 規格：`docs/phases/Phase5計畫.md` 第 36 節（本段開工時補上；原「之後各段規格」順延為第 37 節）。

## 交付內容

| 項目 | 位置 |
|---|---|
| 規格（含決策影響盤點：影子快照、傭兵 AI、自動戰鬥、`trpg.sim`） | `docs/phases/Phase5計畫.md` 36 |
| 內容：`league:`（截止日 13、地圖 3 張、種子 2、輪數上限 30、每批 10 場）＋載入檢查（地圖存在、不能用 Boss／靶場／測試圖、不重複、種子 1～8、截止日在賽季內） | `content/world/season.yaml`、`src/trpg/content/world_season.py`（`LeagueRules`）、`library.py` |
| 報名／取消（世界動作，算帳號）、拉到等級上限、賽程、對戰設定與自動對戰 | `src/trpg/world/league.py`、`league_actions.py`；`state.py`（`LeagueEntry`、`WorldState.league_entries`）、`step.py`（`ACCOUNT_HANDLERS`：帶 `actor` 的分派表） |
| 賽果存檔（`trpg-league/1`＋每場 `BattleLog`）、背景分批執行、接續、單場出錯標 `error`、排行榜計分 | `src/trpg/server/league.py` |
| 季末欄位分類：`WorldState.league_entries` 數值類；`LeagueRecord` 賽程／勝負紀念類、凍結的報名數值類（暫標，列入 `PROVISIONAL`）；`LeagueMatch` 全部紀念類 | `src/trpg/server/season_policy.py` |
| API：`GET …/league`、`POST …/league/matches/{id}/replay`、`GET /api/world/league/matches/{id}/log`、`POST /api/world/league/run`（管理者）；`league_enter`／`league_withdraw` 走 `…/actions`；事件句子 | `src/trpg/api/league_schemas.py`、`league_view.py`、`routes/world.py`、`world.py`、`app.py`、`auth.py`、`world_presenter.py`、`world_schemas.py`、`world_party_view.py`（`ai_choice_views`、`shadow_role_zh` 公開給循環賽用） |
| 前端：城鎮「循環賽」面板（報名＋打法、排行榜、場次、重播鈕）；重播用既有 `BattleScreen` 從開場播到結束，開場說明顯示標題與「重播驗證一致」，離開鈕「回到循環賽」 | `client/src/world/LeaguePanel.tsx`、`league.ts`、`WorldPanel.tsx`、`screens/WorldScreen.tsx`、`growth.ts`、`api/*`、`styles/world.css` |
| OpenAPI 重產 | `client/openapi.json`、`client/src/api/schema.d.ts` |
| 測試 | `tests/world/test_league.py`（11）、`tests/server/test_league_runner.py`（5）、`tests/api/test_world_league.py`（4）、`tests/content/test_world_season.py`（加 8）、`tests/world/test_dispatch.py`（改）、`client/src/world/league.test.ts`（4） |

## 規則重點

- **拉到上限**：等級＝`level_cap`（10）；新增點數＝（上限 − 快照等級）× 每級點數＋未分配點，照開局自動配點（`primary_attribute`＋`default_allocation`）補；已分配的不動。技能全部 `at_run_tier` 到上限的角色階級（3），再走 `shadow_spawn(…, recruiter_level=10)`（裝備不會降級、生成技能改名 `<id>_<主人>`）。
- **賽程**：參賽者依帳號排序，`i<j` × 地圖 × 種子 × 先後手；編號 `m0001` 起；種子 `fnv1a64("{season_seed}:league:{a}:{b}:{map}:{k}")`，同種子交換先後手各一場。對戰：我方＝先手（`first_team = ally`），雙方都由 `CommandedAI(UtilityAI)` 操作。
- **確定性**：同一份報名＋賽季種子＋內容必得同一份結果（測試：兩個資料夾各跑一次結果相同；每場紀錄重播得到相同最終狀態）。

## 驗收

- `ruff check .`、`ruff format --check .`、`mypy`（1188 檔）、`lint-imports`（13 kept）：通過。
- `tests/world tests/api tests/server tests/content tests/test_architecture.py -n 8`：見下方「檢查結果」。
- `npx vitest run`：138 檔 1276 項通過；`pnpm build` 通過。
- swamp 種子 7 重播：通過（88 個動作、313 個事件）。
- 循環賽對戰重播：用目前程式產生一場（衝陣 vs 雷水，`open_plain`）→ `trpg battle replay` 通過（11 個動作、52 個事件）；API 測試的重播回應 `verified: true`。
- 瀏覽器（8180 埠、自己的分頁、自己的存檔資料夾）：兩個角色，一個用面板選「守衛」報名、一個經 API 報名 → 第 14 天管理者開跑（開發模式）→ 面板顯示「比賽已結束、已完成 12／12 場、冠軍：小美」、排行榜與 12 場場次 → 點 m0005「重播」→ 戰鬥畫面從第 1 輪播到結束，開場說明顯示標題與「重播驗證一致」→「回到循環賽」回到面板。

## 代決（照規格 36.9，最保守預設）

5F4-1 只有管理者觸發（截止後）；5F4-2 已分配點不動、新增點照自動配點；5F4-3 技能只重配階級、不補新技能；5F4-4 用報名當下的快照（截止後凍結）；5F4-5 1 對 1、只有本人；5F4-6 同種子交換先後手與站位；5F4-7 和局不算勝場；5F4-8 勝多 → 負少 → 報名早，同分同名次；5F4-9 `seeds: 2`、開闊平原／竹林／沼澤；5F4-10 賽果放 `trpg.server.league` 衍生檔；5F4-11 重播用先手那位的我方視角。

## 待 PM 決定

1. **對戰很短**：實測（兩個 1 級火焰法杖拉到 10 級；衝陣 vs 雷水）多半 2～3 輪就結束，10 級主角 HP 約 58、3 階技能爆發很高；後手方勝率偏高（瀏覽器那組 12 場中後手贏 11 場）。要不要循環賽另設開場 HP 倍率或改地圖／站位，待 PM（建議先用 `trpg.world.league.play_match` 寫腳本量勝率，再定）。
2. **引擎或規則資料一改，舊的循環賽紀錄就因 `ruleset_hash` 不符不能重播**（本段合併 main 的 5F-2b 後實測舊紀錄被擋下，目前程式產生的紀錄重播正常）。9.7「修正前的重播仍可重現」要靠保留舊版引擎或在賽季中凍結規則；建議循環賽開跑後避免改規則，或開跑後要改時重跑整個賽程（同報名、同種子）。
3. **「屬性點重新分配」**：目前只補新增的點，玩家沒辦法為循環賽重新配點。要不要做「報名時另配一套點數」的畫面。
4. **冠軍同分**時都列第 1；獎金怎麼分（#101）待定。有人首殺 → 對打賽改娛樂賽的判定與顯示是 5F-3／5F-5。
5. **凍結報名要不要跨季**（名字、build 快照）：暫標數值類（`PROVISIONAL`）；賽程與勝負已是紀念類，但季末清掉報名後排行榜就沒有名字可顯示。
6. **開跑方式**：目前只有 API `POST /api/world/league/run`（管理者），前端沒有按鈕、Bot 也沒有指令；要不要第 14 天換日自動開跑或加 Bot 指令。
7. **重播結束面板**從我方（先手那位）視角寫「勝利／敗北」；要不要改成「某某勝」的中性文字。
8. 場次列表一次只列 60 場（自己的在前，其餘捲動）；人數多時（10 人＝540 場）要不要分頁或篩選。
