# Phase 5F-R2 完成報告：5F 審查整理②（結構）

規格：`docs/phases/Phase5計畫.md` 第 1 節表格的 5F-R2 列，以及開發 PM 派工時列的 6 項。建在 5F-R1 分支（`worktree-agent-a1dd1e9ab2898ab5b`）之上。開發 PM 中途補一項：玩法 PM 2026-11-03 代決「世界事件的效果不能引用 enemy_only 狀態」（06 6.35，commit 6e00b487，已 `git merge main` 拿到）。

## 交付

| # | 項目 | 檔案 |
|---|---|---|
| 0 | **世界事件不能引用 enemy_only 狀態**：大世界事件（`world/events` 的情境判定結果）的 buff／debuff 引用 enemy_only 狀態時，載入報資料錯誤「狀態 X 只給敵人（enemy_only）」。`season.yaml` 的世界事件效果沒有狀態欄位，不用另外擋。**現有內容沒有違反的**（enemy_only 狀態只有 `molten_burst`、`heart_ember_burst`、`frost_ember_burst`，`content/world/` 沒有引用） | `content/world_situations.py`、`content/world_events.py`、`content/library.py`；測試 `tests/content/test_world_situations.py` +2 |
| 1 | **`prepare_season_boss_battle`**：賽季 Boss 的戰鬥設定拆成獨立函式（固定陣容、遭遇等級、Boss 地圖不換皮、只帶主角＋傭兵、不帶下一場修正、不看先手）。`prepare_battle` 開頭遇到賽季 Boss 就轉過去；`encounter_map`、`enemy_level`、`armored` 拿掉 Boss 分支。兩者共用 `_enemy_spawns`、`_mercenary_spawns`、`_hero_with_items`（主角與傭兵的出場設定）、`_battle_setup`。`fight` 拆成 `_started_event`＋`_encounter_fight`（一般）／`_season_boss_fight`（Boss），打贏的回寫拆成 `_won_rewards` | `world/battle.py` |
| 2 | **`season.yaml` 依季 ID 覆寫**：最上層＝預設；`seasons.<季 ID>` 底下寫要改的頂層項目（`name_zh`、`days`、`schedule`、`milestones`、`daily_goals`、`bounties`、`world_events`、`seal_keys`、`season_boss`、`league`、`chronicle`），沒寫的沿用預設，寫了就整項取代；`season_boss`／`league` 寫 `null`＝那一季沒有。每一季套上覆寫後都跑和預設相同的 schema 與跨檔案檢查（錯誤前面標 `seasons.<季 ID>：`）。`ContentLibrary.for_season(季 ID)` 回傳那一季的內容庫（沒有覆寫＝回傳原本的物件，所以第一季完全不變；有快取）。接上的地方：`world_step`（含重播）、API 的 `WorldStore.library`（照世界存檔的季 ID）、`LeagueStore.library`、每日公告、季末重置（舊季的內容） | `content/world_season.py`、`content/library.py`、`content/world/season.yaml`、`world/step.py`、`api/world.py`、`server/league.py`、`server/announce.py`、`server/season_reset.py` |
| 3 | **季名模板**：`season.yaml` 的 `naming`（`template: "第{number}季"`、`fallback: "賽季 {id}"`、`digits`、`units`），中文數字支援到 9999（`s100`＝「第一百季」），某一季可在覆寫寫 `name_zh`。拿掉 `_zh_number`；`season_name_zh(季 ID, library=None)`，沒給內容庫時用 `SeasonNaming` 的預設（和 YAML 相同） | `content/world_season.py`、`server/season_reset.py`、`api/chronicle_schemas.py`、`api/routes/world.py` |
| 4 | **Bot 首殺鍵統一**：每一季（含第一季）都是 `<季>:<kind>:<target>`。舊狀態檔的第一季鍵 `<kind>:<target>` 讀入時換成 `s1:<kind>:<target>`，算貼過、不重貼，下次寫回時存新格式 | `bot/announcer.py` |
| 5 | **`load_library` 拆開**：`_load_base_tables`（第一批表，`_BaseTables`）→ `_load_races` → `_build_ruleset` → `_load_gear` → `_load_units` → `_load_maps` → `_load_world` → `_load_run_extras`；順序不變，PLR0915 noqa 拿掉（`library.py` 沒有任何 noqa） | `content/library.py` |
| 6 | **`--force` 拆開**：`scripts/season_reset.py` 改成 `--force-season`（賽季沒結束、循環賽沒跑完也重置）與 `--force-server`（偵測到伺服器心跳也執行），各自獨立。舊的 `--force` 隱藏保留，用了印說明並結束碼 2（不做任何事）。API 的 `force` 不改名，語意就是 `--force-season`。部署說明加 8.1「季末重置」、腳本說明更新 | `scripts/season_reset.py`、`server/season_reset.py`（錯誤訊息）、`docs/部署說明.md` |

## 行為不變的驗證

- **一般與 Boss 戰鬥**：寫腳本對 4 場一般遭遇（雨中梯田 swamp、老松祭壇、北坡、劍塚，帶傭兵）＋1 場碎晶之主，比對 `prepare_battle` 的整份設定、陣容／等級／HP／先手、AI 打完後的世界、角色、事件：重構前（5F-R1 基底）與 HEAD 30 項雜湊完全相同（Boss 406 步）。
- **季末重置**：用 `tests/server/test_season_reset.py` 的假賽季，dry-run 與執行各一次，比對報告與整個存檔資料夾：用 5F-R1 基底的 `src/`＋`content/`（`git archive` 到暫存資料夾）跑和 HEAD 跑，除了帳號檔都相同。帳號檔每次跑都不同（假帳號的密碼雜湊有隨機鹽，同一份程式跑兩次也不同），和這段無關。
- **內容庫**：`load_library` 拆開前後，`files` 的順序與內容雜湊、`ContentLibrary` 每個欄位的雜湊都相同。
- 重播：swamp 種子 7 通過（88 動作、313 事件）；碎晶之主首殺紀錄（`first_kill_log_json` 產生）`trpg battle replay` 通過（406 動作、1349 事件、rift_gate）。

## 改了既有測試的斷言（都是這段要改的行為）

- `tests/bot/test_announcer.py::test_same_elite_next_season_is_posted`：第一季的鍵從 `elite:wolf` 改成 `s1:elite:wolf`（第 4 項）。另加舊狀態檔照讀、不重貼的測試。
- `tests/server/test_season_reset.py::test_script_dry_run_then_execute`：`--force` → `--force-season`（第 6 項）。
- `tests/server/test_server_presence.py::test_script_refuses_execute_while_server_runs`：訊息改成提示 `--force-server`；`--force-season` 不再放行伺服器心跳；舊 `--force` 會被擋；兩個一起加才放行（第 6 項）。另加 `--force-server` 不略過賽季未結束的測試。

## 新增測試

- `tests/content/test_season_overrides.py`（29）：第一季＝預設（同一個物件）、覆寫只換列出的項目、`null` 拿掉循環賽、改天數、壞的覆寫報錯（天數不合日程、`days: null`、未知欄位、季 ID 格式）、內容庫 `for_season` 快取與切回、覆寫也跑跨檔案檢查、`WorldStore`／`LeagueStore` 照世界的季 ID、`world_step` 照季 ID 用覆寫的世界事件、中文數字 13 例、季名模板與驗證。
- `tests/content/test_world_situations.py`：enemy_only 狀態被擋（載入器測試）、現有情境判定沒有引用 enemy_only。
- `tests/bot/test_announcer.py`：舊鍵照讀。`tests/server/test_server_presence.py`：兩個旗標獨立。

## 測試與檢查

- `ruff check`、`ruff format --check`、`mypy`（1227 檔）、`lint-imports`（13 契約）通過。
- pytest `tests/engine`、`content`、`world`、`api`、`server`、`bot`、`test_architecture.py`（`-n 8`）：7617 通過。
- vitest 145 檔 1344 通過；`pnpm build` 通過（只有既有的 chunk 大小警告）。沒有改 API 型別，OpenAPI 不用重產。
- 重播：見上方「行為不變的驗證」。沒有跑全量與大型模擬。

## 代決（最保守的做法）

1. **覆寫是「頂層整項取代」**，不逐欄合併（例如只想改 Boss 的每日次數也要寫整個 `season_boss`）。逐欄合併在 tuple（世界事件、懸賞）上語意不清楚，先不做。
2. **覆寫的接法**：世界規則在 `world_step` 開頭照 `world.season_id` 換內容庫（重播同一條路，所以確定）；API 的 `WorldStore.library` 改成屬性，照已讀的世界存檔的季 ID（還沒有世界存檔時用原本的，不為此建立世界）；`LeagueStore` 透過 `library_of` 拿同一個；季末重置的 `forget()` 也清掉循環賽的規則鍵快取（新一季可能覆寫循環賽規則）。`OfferPrefetcher`、`FirstKillRegistry`、`SessionStore` 等和賽季無關的照舊用原本的內容庫。
3. **賽季 Boss 不再呼叫 `shadow_spawns`**：原本 Boss 戰會算影子再丟掉單位、只留技能進規則包；挑戰時已擋影子（`season_boss_problem`），實際上沒有影子，結果完全相同。只有「挑戰後才借影子」這種走不到的狀態會不同（規則包少了用不到的技能）。
4. 遭遇沒有 `battle_map` 的 Boss（走不到：挑戰一定帶 Boss 地圖）沿用原本的抽圖。
5. 中文數字：10～19 寫「十X」，其他照「二千零二十四」這種寫法（不寫「兩」）；超過 9999 用阿拉伯數字。
6. API 的 `SeasonResetRequest.force` 不改名（不動 OpenAPI 與前端），語意＝`--force-season`；錯誤訊息改成「確定要重置請加 force；腳本是 --force-season」。
7. Bot 狀態檔格式字串維持 `trpg-announce/1`（新舊鍵都讀得進來）；舊版 Bot 讀到新格式的鍵會把第一季首殺當作沒貼過——升級後不會再跑舊版，不另外處理。
8. `season.yaml` 目前 `seasons: {}`，沒有實際的第二季覆寫（只在註解放例子）。

## 待 PM 決定

1. `docs/phases/Phase5計畫.md` 第 31.6 節與 4412 行仍寫首殺鍵是 `<kind>:<target>`／「`s1` 以外的季加賽季」，要改成統一格式（實作者不改規格）。
2. 覆寫要不要支援逐欄合併（例如 `season_boss.daily_attempts` 單獨改）；目前整項取代。
3. API 的 `force` 要不要改名成 `force_season`（會動 OpenAPI 與前端型別）。
