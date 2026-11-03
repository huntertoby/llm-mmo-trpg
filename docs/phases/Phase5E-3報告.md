# Phase 5E-3 完成報告：公告、地點留言與足跡、部署

> 規格：`docs/phases/Phase5計畫.md` 第 31 節（本段新增；寫的時候是第 30 節，合併 main 時 5D-3 先佔了 30，本段順延為 31、「之後各段規格」為 32）。分支 `worktree-agent-aa4aa55b3f4412bda`。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格 | `docs/phases/Phase5計畫.md` 31 |
| 真實 IP：`trusted_proxies`（預設空＝不信任轉發標頭）；來源可信任時 `CF-Connecting-IP` 優先、`X-Forwarded-For` 由右往左；登入限制改用它 | `src/trpg/api/client_ip.py`、`server_config.py`、`routes/auth.py`、`config/server.toml` `[network]` |
| 本機模型健康檢查：啟動時與每 60 秒 ping（大世界 LLM 開關開著才 ping）；不可用時說書人、情境、聊天全部走模板；log 警告／恢復；`WorldLlmView.model_available` | `src/trpg/api/llm_health.py`、`world_flow.py`、`world_story_schemas.py`、`app.py`、`config/server.toml` `[llm_health]` |
| 全服首殺紀錄（精英，每種一次；`trpg-firstkills/1`，衍生資料、不影響重播） | `src/trpg/api/first_kills.py`、`world.py` |
| 公告：今日公告數字（`daily_digest`，唯讀）、模板（`string.Template`，變數錯誤載入時報錯）、玩家文字中和提及；今日目標／世界事件進度留接口 | `src/trpg/api/announce.py`、`content/world/announcements.yaml` |
| Bot 排程：`Announcer.tick(now)`（6 點後貼一次、晚啟動補貼當天、首殺每筆一則、失敗重試、第一次不洗版）；`DiscordGateway.send_channel`；`[announce]` 時區設定（沒有 tzdata 時用固定時差） | `src/trpg/bot/announcer.py`、`gateway.py`、`fake.py`、`config.py`、`config/bot.example.toml` |
| `discord_bot.py preview`（不連網、不需要 token，印出公告文字） | `scripts/discord_bot.py` |
| 地點留言（50 字、不能換行、要站在那裡）與足跡（日誌的 travel＋首殺）；管理者刪除（API＋腳本） | `src/trpg/api/notes.py`、`notes_schemas.py`、`routes/world.py`、`auth.py`、`scripts/location_notes.py` |
| 前端：地點圖右欄「地點留言」（留言、足跡、輸入框與剩餘字數） | `client/src/world/NotesPanel.tsx`、`notes.ts`、`screens/WorldScreen.tsx`、`styles/world.css`、`api/*` |
| 部署：`deploy.py check／server／bot／tunnel`、`start_*.ps1`／`.sh`、`config/deploy.example.toml`、部署說明（Windows／macOS） | `scripts/deploy.py`、`scripts/start_*`、`docs/部署說明.md` |
| 測試 | `tests/api/test_client_ip.py`（10）、`test_llm_health.py`（3）、`test_announce.py`（8）、`test_notes.py`（9）、`test_deploy_script.py`（6）、`tests/bot/test_announcer.py`（9）、`test_world_events_api.py`（改 1）、`client/src/world/notes.test.ts`（4） |

## 慣例上的決定（寫明）

- **留言不進世界日誌**（代決 5E3-3）：照 5E1-2「帳號不進日誌」的慣例，留言是玩家文字、不影響規則、要能手動刪，放在 API 層的 `<世界資料夾>/notes.json`（`trpg-notes/1`）。`trpg-wlog/1`、`trpg-world/1`、`trpg-char/1` 都沒改，重播不受影響。
- **首殺紀錄**也放 API 層（`first_kills.json`），由日誌序號＋時間戳決定，可從日誌查證。
- 留言只當資料顯示，**不送進 LLM**；放進 Discord 公告的角色名先中和 `@`（零寬字元）、去換行、截 40 字。
- 健康檢查、公告排程都用伺服器／Bot 的時鐘，不進引擎與 `trpg.world`。

## 檢查結果

- `ruff check .`、`ruff format --check .`、`mypy`（1149 檔）、`lint-imports`（11 kept）全過。
- `tests/api tests/world tests/bot tests/test_architecture.py -n 8`：1035 passed。
- vitest 133 檔 1248 passed；`build` 通過。
- swamp 種子 7 重播通過（88 動作、313 事件）。
- OpenAPI 已重產（新增 `/notes` 端點、`LocationBoard` 等、`WorldLlmView.model_available`）；合併 main 後再產一次沒有差異。
- 瀏覽器（自己開的 8135 埠、暫存存檔）：進大世界 → 右欄看到「地點留言・霧渡鎮」→ 輸入一則按 Enter → 出現在最上面、輸入框清空。伺服器已關。
- 已 `git merge main`（含 5D-3；計畫書衝突照 main 為準：5D-3 留在 30，本段改成 31）。

## 代決（照規格 31.11）

| # | 代決 |
|---|---|
| 5E3-1 | 現有資料的「首殺」＝全服第一個打倒某種精英（每種一次）；賽季 Boss 首殺留到 5F（格式已留 `kind: season_boss`） |
| 5E3-2 | 今日目標、世界事件進度只留接口（`DailyGoalsSource`、`WorldEventSource`），模板寫「尚未開放」；現有資料貼：賽季第幾天、昨天有動作的角色數、世界線頭數、已清空地點數、首殺種數 |
| 5E3-3 | 留言不進日誌（見上） |
| 5E3-4 | 只有管理者能刪留言（API 或 `scripts/location_notes.py`）；作者自己不能刪；開發模式不帶 token 也能刪（同 LLM 開關，5E2-6） |
| 5E3-5 | 留言不限次數、不清舊的；畫面只顯示最新 20 則；足跡最多 10 筆 |
| 5E3-6 | 時區設定 `Asia/Taipei`；這台 Windows 沒有 `tzdata`（沒裝、也不能裝），所以實際用 `utc_offset_minutes = 480`；世界的刷新時間照 `trpg.world.clock` 常數（UTC+8、6 點，使用者已定）沒改 |
| 5E3-7 | Bot 晚啟動當天補貼一次，不補前幾天 |
| 5E3-8 | 健康檢查預設 60 秒，**只在大世界 LLM 開關開著時 ping**（關著本來就走模板；也讓測試不會去連 8001）；還沒 ping 過＝照開關 |
| 5E3-9 | 轉發標頭只在來源可信任時讀；`CF-Connecting-IP` 優先；`X-Forwarded-For` 由右往左跳過可信任的；標頭不合法就用連線來源 |
| 其他 | 足跡只算 `travel` 走到這個地點（傳送、開場不算）；首殺貼過與否以 `<kind>:<target>` 記（季末清世界後照樣能貼新的）；`deploy.py check` 有 ✗ 時 exit 1；`deploy.py bot` 目前會照 5E-2 印「adapter 還沒做」並 exit 3 |

## 待 PM 決定

1. **真實 Discord adapter**（5E2-1 照舊）：公告現在只到 `Announcer.tick` 與假 gateway；接上真的 Discord 才會真的貼。要加 `discord.py`（新相依、連網）。
2. **今日目標與世界事件全服進度的資料來源**（5F-1）：接口已留，5F-1 實作 `DailyGoalsSource.daily_goals(world, now)`、`WorldEventSource.world_events(world, now)` 傳給 `AnnouncementSource` 即可。#103「門檻依前一天上線人數調整」可用 `daily_digest` 已算的「昨天有動作的角色數」，但它算的是**角色**不是帳號，要不要改算帳號待定。
3. **「首殺公告」的範圍**：目前把「全服精英首殺」也公告（設計只明寫賽季 Boss 首殺，#101）。精英種類多時可能有點吵，要不要只留 Boss。
4. **留言作者能不能刪自己的留言**（#105 只寫使用者手動刪）。
5. **前端的管理者刪除按鈕**沒做（目前用腳本或 API）；`AuthStatus` 也還沒回 `admin`（5E-2 待決 5）。
6. **足跡與地點 ID**：日誌只記 travel 的目的地 ID，區域由「地點在不在這區的地點圖裡」判斷；之後若不同區有同名地點 ID 會混在一起（現在只有雲嶺，不會發生）。要根除需在日誌記區域或約定地點 ID 全服唯一。
7. **公告時區與世界刷新時間是兩個地方**：公告看 `config/bot.local.toml` `[announce]`，世界刷新是 `trpg.world.clock` 的常數；改其中一個不會連動另一個。
8. 健康檢查不可用時要不要也在前端的大世界畫面顯眼提示（目前只在 LLM 開關的提示與伺服器 log）。

## 使用者要做的事

1. **裝 Tunnel 工具並登入**（例 cloudflared；本專案不幫你裝）：照 `docs/部署說明.md` 第 4 節建好 tunnel。
2. **複製** `config/deploy.example.toml` 成 `config/deploy.local.toml`，填 `tunnel_command`。
3. **改** `config/server.toml`：`[accounts] dev_mode = false`；`[network] public_url = "https://<你的網址>"`、`trusted_proxies = ["127.0.0.1", "::1"]`。
4. **公告頻道與時間**：`config/bot.local.toml` 要有 `announce_channel_id`；要改時間就加 `[announce] hour = 6`（範本裡有）。
5. **建置前端**：`corepack pnpm -C client install`、`corepack pnpm -C client build`。
6. **檢查**：`uv run python scripts/deploy.py check`，處理所有 ✗。
7. **啟動**：Windows 用 `scripts\start_server.ps1`、`start_tunnel.ps1`（`start_bot.ps1` 要等真實 adapter）；macOS 用對應的 `.sh`。
8. **看公告文字**：`uv run python scripts/discord_bot.py preview`；想改文字就改 `content/world/announcements.yaml`。
9. **刪留言**：`uv run python scripts/location_notes.py list`，再 `delete <note_id>`。

## 複雜度例外

無（沒有新增 `# noqa: C901／PLR`；`scripts/discord_bot.py` 有一個延後匯入 `time` 的 `PLC0415`，可改成頂層匯入）。
