# Phase 5F-1 完成報告：賽季時鐘與日程、今日目標、懸賞板、世界事件、共享地點狀態

範圍：`docs/phases/Phase5計畫.md` 第 1 節 5F-1 列；詳細規格是同檔第 35 節（本段開工時補上，佔位節順延為 36）。季末重置（5F-5）、荒原內容、封印鑰匙（5F-3）不在本段。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | 日曆：時區與刷新時刻進世界規則 `calendar`（預設 +480 分、6 點）；`clock.refresh_day`／`next_refresh_at` 加參數；新 `trpg.world.calendar`（`day_of`、`next_refresh`、`season_day`、`season_status`、`season_start_at`）；既有每天一次的判定（感知、聊天好感度、夥伴／店裡每日上限、骨架 22 失敗隔天、機遇提示、影子每天第一次、週次）全部改走 `day_of` | `content/world/rules.yaml`、`content/world_rules.py`、`world/clock.py`、`world/calendar.py` 等 |
| 2 | 開賽日：`config/server.toml` `[season] start_date`（`TRPG_SEASON_START` 覆寫）；空＝建立世界的當下（同現行） | `api/server_config.py`、`api/app.py`、`api/world.py` |
| 3 | 賽季內容 `content/world/season.yaml`（14 天日程、時間點、今日目標池、雲嶺 3 張懸賞、世界事件 #1 霧潮入侵）＋ schema 與跨檔案檢查；遭遇表補陣容 `mist_swordsman_band` | `content/world_season.py`、`library.py` |
| 4 | 換日、世界事件（門檻依前一天上線帳號數、成功立刻套旗標、失敗套建議等級 +1）、懸賞先搶先贏、今日目標、上線紀錄；全部在 `world_step` 裡依日誌序號決定 | `world/season_board.py`、`world/season_events.py`、`world/step.py` |
| 5 | 建議等級加成：遇敵記 `EncounterResult.level_bonus`，敵人等級與經驗照加成後；懸賞貼出時遇敵記 `EncounterResult.bounty`、陣容照懸賞 | `world/solutions.py`、`world/encounters.py`、`world/battle.py` |
| 6 | 日誌帶帳號：`WorldLogEntry.actor`（選填）、`world_step(..., actor=)`；`WorldStore.actor_of` 接帳號 `owner_of`；重播帶回 | `world/replay.py`、`api/world.py`、`api/app.py` |
| 7 | API：`GET /api/world/characters/{id}/board`（賽季、今日目標、懸賞、世界事件、已清空與等級加成；換日後的世界只算不寫）；事件句子；OpenAPI 重產 | `api/season_view.py`、`api/season_schemas.py`、`routes/world.py` |
| 8 | 公告接真資料：`SeasonAnnouncements`（今日目標、世界事件進度）、`AnnouncementSource` 有內容庫時預設接上；昨天上線人數改用世界狀態的帳號數（沒紀錄退回日誌角色數）；`scripts/discord_bot.py` 傳內容庫 | `server/announce.py` |
| 9 | 前端：城鎮「公告板」左欄畫面（沿用任務日誌樣式與一輪的進度條） | `client/src/world/BoardPanel.tsx`、`board.ts` |
| 10 | 季末重置政策表：新欄位全部標數值類 | `server/season_policy.py` |

存檔：新欄位全部有預設值，`trpg-world/1`、`trpg-char/1`、`trpg-wlog/1` 不升版；`LOG_FORMAT` 不變。

## 決策影響盤點的結果

- 既有每日刷新：預設日曆下逐位元相同（`tests/world` 全過）。
- 懸賞精英詞綴（5B-4c）：照用；角色自己的遭遇變化（疤面線頭）優先於懸賞陣容。
- 事件冷卻：線頭到期仍是現實秒數；失敗隔天照新日曆。
- 商店每週限購：週次照新日曆；開賽日由設定給時從開賽日起算。
- 世界快照：每個動作都會寫上線紀錄與換日，**世界每天至少變一次**；3 個舊測試原本斷言「移動不改世界」，改成比對時去掉賽季紀錄（`tests/world/helpers.without_season`）；重播測試改用最後的世界比對。

## 檢查

- `ruff check`、`ruff format --check`、`mypy`（1180 檔）、`lint-imports`（13 契約）通過。
- `tests/world tests/api tests/content tests/bot tests/test_architecture.py`（`-n 8`）：3198 通過。
- vitest 137 檔 1272 通過；`npm run build` 通過；OpenAPI 與 `schema.d.ts` 重產。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- 瀏覽器實測（8170 埠）：建角 → 霧渡鎮「公告板」顯示賽季第 1 天、新手目標 3 條、3 張懸賞、霧潮入侵 0／30（第 1 天原門檻）。修了一個 JSX 全形空白被吃掉的排版問題。
- 新測試：`tests/world/test_season_board.py`（15）、`tests/world/test_calendar.py`（4）、`tests/content/test_world_season.py`（14）、`tests/api/test_world_board.py`（5）、`tests/api/test_announce.py`（+1）、`client/src/world/board.test.ts`（2）。

## 代決（照規格 35.9，最保守）

5F1-1～5F1-13 全照規格。補充：

- 換日產生的事件（世界事件開始、門檻調整、失敗）**不放進觸發換日的那個角色的事件**，只寫進世界狀態（調整紀錄可查）；規格 35.6 已補一句。
- 今日目標沒有前進時不寫角色（跨日歸零等到第一次前進）。
- 懸賞在賽季天數之後不再貼出；遭遇跨過刷新時刻時以打贏當下的刷新日判定。
- 精簡內容資料夾（沒有遭遇表）時跳過懸賞陣容檢查。
- 公告板按鈕只在城鎮（`can_rest`）出現（9.6.9「主城公告板」）。

## 待 PM 決定

1. **門檻算法**：Q14 用整數除法捨去、最少 1；第 2 天起沒人上線＝當 1 人（30 → 3）。舊存檔升級後第一天沒有上線紀錄也會當 0 人。要不要改成「沒有紀錄時用原門檻」？
2. **懸賞經驗**：那場經驗補到懸賞 4 份（不和精英 3 份疊加）；任務幣每張 3、今日目標每條 1（初值）。
3. **霧中劍客「會分身」**沒有機制（召喚 1 個幻影），目前只有霧隱的詞綴。
4. **懸賞貼出期間該地點的遭遇全變懸賞陣容**（先搶先贏的直接解讀）；北坡獵場本來就是固定精英，影響小；斷崖幫寨、劍冢在懸賞被搶前每場都是懸賞陣容。
5. **世界事件 #2、#3 的資料**：荒原村落與封印鑰匙到位再加（schema 已能表達）；世界事件成功的全服任務幣等獎勵 19.9 沒寫。
6. **雲嶺懸賞第 1 天起**（9.7 表的「第 4～7 天 懸賞」解讀成荒原懸賞）。
7. 換日事件沒有推給玩家的提示（例「霧潮入侵失敗，荒原建議等級 +1」）；目前只在公告板與 Bot 公告看得到。
