# Phase 5E-2b 完成報告：真實 Discord adapter

規格：`docs/phases/Phase5計畫.md` 第 32 節（這一段先補的規格；原本的「之後各段規格」順延成第 33 節）。依據：第 1 節 5E-2b 列；使用者 2026-11-03 同意加 discord.py（原話「裝」）、token 的放法（原話「到時候我會放.env然後 放token」）。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格 32 節 | `docs/phases/Phase5計畫.md` |
| 相依 | `pyproject.toml`（`discord-py>=2.7.1`）、`uv.lock` |
| `.env` 解析器（自寫，不加 python-dotenv） | `src/trpg/bot/envfile.py` |
| 讀取順序 環境變數 → `.env` → `bot.local.toml`、新變數名 | `src/trpg/bot/config.py`、`.env.example`（新）、`.gitignore`（`!.env.example`）、`config/bot.example.toml`（註解） |
| 斜線指令註冊表與事件轉換（不匯入 discord.py） | `src/trpg/bot/commands.py` |
| 真實 adapter：`DiscordPyGateway`、`TrpgBotClient`、`run_bot` | `src/trpg/bot/discord_adapter.py`（discord.py 只在這裡匯入） |
| `CommandEvent.interaction_id`（有預設值） | `src/trpg/bot/gateway.py` |
| `discord_bot.py run` 真的啟動；`check`／`preview` 照舊 | `scripts/discord_bot.py` |
| `deploy.py check` 讀 Bot 設定時也讀 `.env` | `scripts/deploy.py`（一行） |
| 部署說明第 9 節（建 Bot、intents、邀請權限、`.env`、啟動、玩家用法；Windows／macOS） | `docs/部署說明.md` |
| 測試 | `tests/bot/test_envfile.py`（新）、`tests/bot/test_discord_adapter.py`（新）、`tests/bot/test_config.py`、`tests/bot/test_script.py`、`tests/test_architecture.py` |

### 加入的套件

- `uv add discord.py` → **discord-py 2.7.1**（PyPI）。
- uv 帶進來的傳遞相依（`uv.lock` 新增）：`aiohttp` 3.14.5、`aiohappyeyeballs` 2.7.1、`aiosignal` 1.4.0、`attrs` 26.1.0、`frozenlist` 1.8.0、`multidict` 7.2.1、`propcache` 0.5.4、`yarl` 1.25.1、`audioop-lts` 0.2.2（只在 Python ≥ 3.13 安裝；本機 3.12 沒裝）。沒有加 python-dotenv、PyNaCl 或其他套件。
- discord.py 自帶 `py.typed`，mypy strict **不需要 override**。
- pytest `filterwarnings` 加一條：略過 discord.py 語音模組在 3.12 匯入 `audioop` 的 DeprecationWarning（Bot 不用語音）。

### 做法摘要

- **讀取順序**：每個欄位各自取第一個有值的：程序環境變數 `TRPG_DISCORD_TOKEN`／`TRPG_DISCORD_GUILD_ID`／`TRPG_DISCORD_ROLE_ID`／`TRPG_DISCORD_ANNOUNCE_CHANNEL_ID` → repo 根目錄 `.env`（同名）→ 設定檔 `[discord]`。`.env` 只在 `env=None`（讀真的環境）時讀；測試給了 `env` 就不讀，使用者主資料夾的 `.env` 不會混進測試。
- **`.env` 解析器**：`KEY=VALUE`、`#` 註解行、空行、成對引號（不處理跳脫）、沒引號時「空白＋#」之後是註解、BOM、同名後蓋前。不合法的行只報行號、不印內容（可能含 token）。
- **adapter**：intents 只開 `guilds`、`members`。所有 `BotService`／`Announcer` 呼叫排進同一條工作執行緒；gateway 方法從工作執行緒用 `run_coroutine_threadsafe` 回事件迴圈。指令先 `defer(ephemeral=True)` 再處理，回覆用 followup（只有本人看得到）。`member_roles` 每次 `fetch_member`；`NotFound` → `None`（不在伺服器），**其他錯誤丟 `GatewayError`**，不會因斷線停用帳號（指令回「暫時無法處理」、`reconcile` 中止不停用）。私訊、頻道貼文失敗回 `False`；頻道貼文與私訊都關掉提及。`setup_hook` 同步 guild 指令；第一次 `on_ready` 跑 `reconcile()` 再開公告迴圈（每 60 秒 `tick`，時鐘由腳本注入，`trpg.bot` 不讀系統時間）。`LoginFailure`／`PrivilegedIntentsRequired`／註冊指令被拒 → `BotConfigError`，訊息說明怎麼修、不含 token。
- **測試不連網、不需要 token**：intents、指令註冊表（真的 `CommandTree`，不 sync）、`TrpgBotClient` 建構、事件轉換、`DiscordPyGateway` 對假 client（事件迴圈在背景執行緒）、`BotService` 經真實 gateway 領帳號；`run` 換成假的 `run_bot` 檢查組裝與 exit code。測試 token 一律 `secrets` 當場產生。
- `.env` 被忽略、`.env.example` 不被忽略：`git check-ignore` 測試（`tests/bot/test_config.py`）。
- 架構：`tests/test_architecture.py` 新增「`discord` 只能在 `trpg.bot` 匯入」（掃 `src/trpg` 與 `scripts`，含掃描器自我測試）。import-linter 契約不變（11 kept）。

## 檢查結果

- `ruff check .`：通過；`ruff format --check .`：通過（1736 檔）。
- `mypy`（strict）：通過（1155 檔），沒有 override。
- `lint-imports`：11 kept、0 broken。
- `pytest tests/bot tests/api tests/test_architecture.py -n 8`：562 passed。
- swamp 種子 7 重播：通過（88 個動作、313 個事件）。
- 已 `git merge main`（只有文件變動，沒有 uv.lock 衝突）。沒跑全量、沒跑大型模擬、沒有連線 Discord、沒有建立或使用任何 token。

## 代決（照規格 32.9）

| # | 事項 | 代決 |
|---|---|---|
| 5E2b-1 | 指令名稱 | 英文 `/register`、`/reset_password`，說明繁中（輸入法都打得出、不需要在地化設定） |
| 5E2b-2 | 指令範圍 | 只註冊在設定的伺服器；沒有全域指令 |
| 5E2b-3 | 身分組查詢 | 每次 `fetch_member`；網路錯誤不當作「不在伺服器」 |
| 5E2b-4 | 同時處理 | 單一工作執行緒依序處理所有事件與公告 |
| 5E2b-5 | 舊環境變數名 | `TRPG_BOT_*` 仍可用（排在同一來源的新名之後），文件只寫 `TRPG_DISCORD_*` |
| 5E2b-6 | `.env` 位置與格式 | 只讀 repo 根目錄的 `.env`；不支援 `export`、多行、變數展開 |

規格以外的小決定：指令同步放在 `setup_hook`（登入後、連 gateway 前，discord.py 建議的位置；規格 32.5 已同步改寫）；`TRPG_BOT_CONFIG` 只認程序環境變數、不從 `.env` 讀；`[announce]` 照舊只從設定檔讀；`EXIT_NO_ADAPTER`（3）移除。

## 待 PM 決定

1. 指令要不要加中文名稱（Discord 的 name localization，zh-TW 顯示「領帳號」「重設密碼」）：目前只有英文名＋繁中說明。
2. `reconcile` 在帳號多時每個帳號打一次 `fetch_member`（Discord 有速率限制，discord.py 會自動等）；朋友規模沒問題，人多再改成一次抓成員清單。
3. Bot 斷線重連期間的身分組變動：重連後**不會**再跑 `reconcile`（只在程序啟動時跑一次），要的話可以改成每次 `on_ready` 都跑。
4. 跨程序寫同一帳號資料夾的後寫蓋前寫（5E-2 待決）照舊。

## 使用者要做的事

1. Developer Portal 建 Application → Bot → **Reset Token** 複製 token；打開 **SERVER MEMBERS INTENT**；建議關 Public Bot（`docs/部署說明.md` 9.1）。
2. OAuth2 → URL Generator：Scopes 勾 `bot`、`applications.commands`；權限勾 View Channels、Send Messages；用產生的網址把 Bot 邀進伺服器。
3. 開 Discord 開發者模式，複製伺服器、身分組、公告頻道的 ID（9.2）。
4. 專案根目錄複製 `.env.example` 成 `.env`（Windows：`Copy-Item .env.example .env`；macOS：`cp .env.example .env`），填四個值（9.3）。
5. 主資料夾要先 `uv sync` 一次裝 discord.py（合併後）。
6. `uv run python scripts/discord_bot.py check` → `run`（或 `scripts\start_bot.ps1`／`sh scripts/start_bot.sh`）；在伺服器打 `/register` 試一次。
7. 提醒玩家打開「允許來自伺服器成員的私人訊息」，不然收不到密碼。

## 複雜度例外

沒有新增 `C901`／`PLR09xx` 的 noqa。新增一個 `PLC0415`（`scripts/discord_bot.py` 的 `_real_run_bot`：只有 `run` 才載入 discord.py，`check`／`preview` 不需要它）。
