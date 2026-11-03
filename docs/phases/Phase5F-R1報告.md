# Phase 5F-R1 完成報告：5F 審查整理①（正確性與資料完整）

規格：`docs/phases/Phase5計畫.md` 第 1 節表格的 5F-R1 列（2026-11-03 reviewer）。開發 PM 中途補一項：玩法 PM 2026-11-03 代決的「敵人專用技能不能複製」（06 6.35，commit 43a10ba8）。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | **round_end 倒數寫回**：`_expire_round_end_statuses` 只要有遞減或到期就寫回 `unit.statuses`（原本只有到期時才寫回，duration ≥ 2 永遠不會到期）。表格測試 duration 1／2／3 實際跑引擎，各自在第 N 輪結束時、所有單位一起移除 | `engine/turns.py`、`tests/engine/test_truce.py` |
| 2 | **伺服器心跳檔**：`trpg serve` 啟動時在世界資料夾寫 `server.lock`（JSON：PID、啟動時間、最後心跳），每 30 秒更新心跳，正常關閉時移除（只移除自己 PID 寫的）。心跳超過 120 秒沒更新就視為伺服器不在（當掉也不會永遠卡住）。`scripts/season_reset.py` 偵測到心跳時拒絕 `--execute`（結束碼 2，訊息說明「先停伺服器／用管理者介面／確定不在就加 `--force`」）；加 `--force` 放行並印警告；dry-run 只印警告。`create_app(hold_presence=True)` 才寫（`trpg serve`、`scripts/play.py`、`scripts/deploy.py server` 都經過 `trpg serve`）；測試與其他呼叫端預設不寫，所以測試不會動到真正的 `saves/` | `server/server_presence.py`、`api/app.py`、`cli/serve.py`、`scripts/season_reset.py` |
| 3 | **enemy_only 補入口**：(a) `granted_skill_problems`：`grant_skill` 給 enemy_only 技能＝驗證錯誤（內容載入與 `skillgen/validate.py` 共用 `skill_reference_problems`，一起擋）。(b) 載入時檢查玩家這一邊：`sim/builds.yaml` 的英雄（主角、影子、傭兵、劇情夥伴的底稿都是 build）與 build 的隊友（`builds.companions`）不能裝 enemy_only 技能（技能欄與反應規則）、不能開場帶 enemy_only 狀態；`dev_starters.yaml` 的指定技能不能是 enemy_only；劇情技能（任務與經濟的 `story_skills`）不能標 enemy_only；循環賽的開場狀態不能是 enemy_only。(c) enemy_only 狀態的檢查改成驗證載入器：原本兩個比對 YAML 文字的測試換成「改一份內容複本再載入、要拋 `ContentError`」 | `content/skills/problems.py`、`content/library.py`（`player_template_enemy_only_problems`、`_dev_starter_problems`、`_story_skill_problems`、季節載入）、`content/world_season.py`、`tests/content/test_enemy_only_statuses.py`、`tests/content/test_enemy_only_skills.py` |
| 3b | **enemy_only 技能不能複製**（開發 PM 補，06 6.35）：`uncopyable_reason` 把 enemy_only 列為不可複製（「是敵人專用的技能，不能複製」）。引擎的複製是「本輪最後一個別人施放的技能」，所以這招被擋下時 `copy_selections` 為空、`legal_actions`（含 AI 展開）不列複製技能、`resolve` 拋 `IllegalActionError`。表格測試（一般／敵人專用各一）實際跑引擎：敵人施放後輪到我方複製 | `engine/copying.py`、`tests/engine/test_copy_enemy_only.py` |
| 4 | **世界資料夾版面模組** `trpg.world.layout`：存檔資料夾的 `world/`、`archive/` 與世界資料夾裡每一種檔名（`world.json`、`log.jsonl`、`chars/`、`notes.json`、`league/`（`league.json`、`matches/`、`archive/`）、`first_kills.json`、`season_boss_board.json`、`season_boss/`、`chronicle/`（`league.json`、`seasons.json`）、`league_history/`、`server.lock`）與 `WORLD_ENTRIES`。`api/world.py`、`api/app.py`、`server/announce.py`、`season_reset.py`、`season_archive.py`、`league.py`、`chronicle.py`、`first_kills.py`、`notes.py`、`season_boss_board.py` 與 `scripts/dev_account.py`、`location_notes.py`、`season_verify.py` 都從這裡取（各模組原本匯出的常數名照舊可用）。`WORLD_FILES` 的鍵也從這裡來，加了 `server.lock: keep`。測試：`WORLD_FILES` 與 `WORLD_ENTRIES` 一致，假世界放滿每一種檔案時重置沒有「不認得的檔案」 | `world/layout.py`、上列各檔、`tests/server/test_season_reset.py` |
| 5 | **封存與備份**：中斷後重跑時併入既有的 `archive/<季>/`（不再開 `log-2.jsonl`、`league-2/`）：先逐檔比對，同名檔 sha256 一致就略過（刪世界資料夾那份），不一致就拋 `SeasonArchiveError`（重置轉成 `SeasonResetError`、409）且什麼都不動；搬完刪掉搬空的資料夾，再重寫清單。備份排除存檔資料夾的 `archive/`（世界資料夾的 `league/archive/` 照樣備份） | `server/season_archive.py`、`server/season_reset.py`、`tests/server/test_season_archive_merge.py`、`tests/server/test_season_reset.py` |
| 6 | `season_policy.py` 的 `_NOTE` 說明改成「數值類，季末刪掉（5F-5 代決定案，`PROVISIONAL` 已清空）」 | `server/season_policy.py` |

## 第 2 項為什麼用心跳檔、不用共用檔案鎖

伺服器的 `WorldStore` 把世界、角色、日誌放在記憶體快取。就算寫入和重置拿同一把檔案鎖，鎖只保證兩邊不同時寫，擋不住伺服器在重置**之後**用舊快取把新一季蓋回去；要安全，伺服器開著時根本不該從外面重置，所以要的是「知道伺服器開著」。心跳檔最簡單：只用標準函式庫（JSON＋`os.replace` 的原子寫入），Windows 與 macOS 相同；當掉留下的檔案心跳過期就失效。不查 PID 存活：Windows 上 `os.kill(pid, 0)` 其實是送 CTRL_C_EVENT，標準函式庫沒有安全的查法，PID 也會被重用。檔名是 `.lock` 結尾，重置的備份照舊略過。

## LOG_FORMAT

`/110` → `/111`（`docs/phases/戰鬥紀錄格式變更.md` 已加一條）。紀錄結構沒變，但結算語意改了兩處：round_end 倒數（目前內容只有 duration 1 的 `league_truce`，結果不變），與 enemy_only 不能複製（`/110` 的紀錄若複製過敵人專用技能，新引擎會判為不合法）。照 1.1 的慣例遞增。測試裡的字面值（含 `LOG_FORMAT.endswith("/110")` 三處）一併更新。

## 測試與檢查

- 新增測試：`test_truce.py` duration 1／2／3（3）、`test_copy_enemy_only.py`（2）、`test_server_presence.py`（7）、`test_season_archive_merge.py`（2）、`test_season_reset.py`（版面一致、備份不含封存，2）、`test_enemy_only_skills.py`（6）、`test_enemy_only_statuses.py`（改寫成載入器測試，4 個新的取代 2 個文字比對）。
- `ruff check`、`ruff format --check`、`mypy`、`lint-imports`（13 契約）通過。
- 交件檢查結果見下方「交件檢查」。
- **重播前後比對**：用 5F-R1 之前的程式（`6af12836` 的 `src/`、`content/`）與現在的程式各跑一次：swamp 種子 7 一般戰鬥只差 `format` 字串（88 動作、313 事件完全相同），`trpg battle replay` 通過；三人影子循環賽（輔助、衝陣、雷水，帶第 1 輪休戰）36 場的動作與事件逐位元相同（2055 動作、12362 事件），每場重播一致。

## 代決（最保守的做法）

1. 心跳檔只由 `trpg serve` 寫（`create_app(hold_presence=True)`），測試與其他呼叫端不寫，避免測試在專案的 `saves/` 留下心跳檔或刪掉使用者伺服器的心跳檔。
2. `--force` 沿用既有旗標（規格寫「要加 `--force` 才放行」）：同一個旗標同時略過「賽季沒結束／循環賽沒跑完」與「偵測到伺服器心跳」。
3. 心跳間隔 30 秒、過期 120 秒；心跳時間比現在晚（時鐘調過）也算在跑。
4. 玩家這一邊的範本檢查範圍：build 英雄（含反應規則）、`builds.companions` 的隊友、開發起始包、劇情技能、循環賽開場狀態。種族技沒有施加狀態的效果、技能是內嵌的，不在範圍內。
5. 封存衝突時整批不動（先比對再搬），錯誤訊息列出衝突的相對路徑，請管理者人工比對。

## 待 PM 決定

1. **`--force` 是否要拆成兩個旗標**（例如 `--ignore-server`）：目前一個 `--force` 同時放行「賽季未結束」與「伺服器開著」，管理者為了前者加 `--force` 時也會略過後者（有印警告）。
2. 世界事件（`world/events`）引用狀態時沒有排除 enemy_only（事件可能對敵我都施加，規格沒寫）；要不要也限制，請玩法 PM 決定。
3. `LOG_FORMAT` 遞增會讓本季循環賽與首殺的舊紀錄標成「規則已變、不能重播」（與 5F-3 升 `/110` 時相同的既有行為）；如果線上已有要保留查證的紀錄，需要先重跑循環賽。
