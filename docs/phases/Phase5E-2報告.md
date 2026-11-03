# Phase 5E-2 完成報告：Discord Bot（假介面、不連網）

> 規格：`docs/phases/Phase5計畫.md` 第 29 節（本段新增；原「之後各段規格」順延為 30）。分支 `worktree-agent-abeb5c7186c59e106`。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格 | `docs/phases/Phase5計畫.md` 29 |
| Bot 介面：`DiscordGateway` protocol、三種事件資料類別 | `src/trpg/bot/gateway.py` |
| 測試用假 Discord（成員與身分組表、私訊與回覆紀錄、可關閉私訊） | `src/trpg/bot/fake.py` |
| Bot 行為：領帳號、重設密碼、身分組被拔／離開時停用、啟動時 `reconcile()` | `src/trpg/bot/service.py` |
| Bot 設定（token 用 `SecretStr`；缺值一次列出全部欄位與環境變數） | `src/trpg/bot/config.py`、`config/bot.example.toml` |
| 啟動腳本（`check`／`run`；缺值 exit 2、沒有 adapter exit 3） | `scripts/discord_bot.py` |
| 登入嘗試次數限制（帳號、IP 各自計數，429） | `src/trpg/api/login_limit.py`、`routes/auth.py`、`app.py`、`config/server.toml` |
| LLM 開關只給管理者改（`AccountRecord.admin`、`require_admin`） | `src/trpg/api/accounts.py`、`auth.py`、`routes/world.py` |
| `dev_account.py`：`create --admin`、`admin <名稱> on|off`、`attach` 檢查角色檔（`--world-dir`） | `scripts/dev_account.py` |
| 帳號存檔跨程序重讀（資料夾內檔案變了就重讀快取）；`open_account_store()` | `src/trpg/api/accounts.py` |
| import-linter：`trpg.bot` 只直接匯入 api 服務層與 shared；engine、world、api、shared、content、roguelite 不得匯入 bot | `pyproject.toml`、`tests/test_architecture.py` |
| 測試 | `tests/bot/test_service.py`（12）、`test_config.py`（7）、`test_script.py`（3）、`tests/api/test_login_limit.py`（5）、`test_accounts.py`（+4）、`test_auth_api.py`（+1） |

## 安全

- 密碼由 Bot 用 `secrets.token_urlsafe(12)` 產生，**只出現在私訊文字一次**；回覆、log、錯誤訊息都不帶（測試檢查回覆與存檔都不含密碼）。伺服器只存 scrypt 雜湊（5E-1）。
- token 不進版控：範本 `config/bot.example.toml` 全是空字串；真的值放 `config/bot.local.toml`（`.gitignore` 的 `*.local.*` 已排除，有測試檢查）或環境變數。`check` 只印最後 4 字。
- 身分組每次指令都向 Discord 重查（`member_roles`），不信任事件附帶的資料。
- 遊戲伺服器不讀 Bot 設定：Bot 設定缺值或錯誤不影響伺服器啟動（有測試）。

## 檢查結果

- `ruff check .`、`ruff format --check .`、`mypy`（1123 檔）、`lint-imports`（11 kept）全過。
- `tests/api tests/world tests/bot tests/test_architecture.py -n 8`：971 passed（OpenAPI 快照第一次因 LLM 端點 docstring 改了而失敗，已把說明改成註解，OpenAPI 與前端型別不變，快照通過）。
- swamp 種子 7 重播通過（88 動作、313 事件）。
- 沒動前端，沒跑 vitest／build；API 型別沒變，不需重產 OpenAPI。
- 已 `git merge main`（併入 `1bc8fca7`）。

## 代決（照規格 29.13）

| # | 代決 |
|---|---|
| 5E2-1 | 真實 Discord adapter **不做**；只留 `DiscordGateway` 與 `scripts/discord_bot.py run` 的說明；沒加 discord 函式庫相依 |
| 5E2-2 | 身分組加回 **不自動恢復**；管理者用 `dev_account.py enable`。停用中的人再「領帳號」只會被告知找管理者，不會領到第二個 |
| 5E2-3 | 私訊失敗：帳號照建立／密碼照換，但密碼沒送出（只在記憶體、丟掉），提示開私訊後重設 |
| 5E2-4 | 停用中的帳號不能用 Bot 重設密碼（不能繞過停用） |
| 5E2-5 | 嘗試次數限制只算失敗；帳號 5 次、IP 5 次／15 分（`config/server.toml`）；帳號不存在也照算；超過時連正確密碼也先擋；成功只清帳號的計數；記憶體計數，伺服器重啟歸零 |
| 5E2-6 | 開發模式開、沒帶 token 照舊可改 LLM 開關；帶了非管理者 token → 403 |
| 5E2-7 | 前端不改（非管理者按 LLM 開關會看到 403 訊息「只有管理者能改 LLM 開關」） |
| 其他 | `admin` 是有預設值的新欄位，舊檔照讀、格式仍 `trpg-account/1`；Bot 走服務層（不是 HTTP），兩個程序共用帳號資料夾，靠檔案簽章重讀；Discord 名稱轉帳號名稱（小寫、`.`／`-`／空白→`_`、去掉其他字元、截 20 字、不足 3 字補 `player`、撞名加 `_xxxx`）；`reconcile()` 只停用有 `discord_id` 的帳號，開發腳本建的不動；`trpg.api` 也不得匯入 `trpg.bot`（比規格多一條，方向一致） |

## 待 PM 決定

1. **真實 Discord adapter**（5E2-1）：要不要做？要加 `discord.py`（新相依）並連網；slash 指令名稱（例如 `/領帳號`、`/重設密碼`）也待定。
2. **身分組加回要不要自動恢復**（5E2-2）：目前不恢復。若要自動恢復，需在帳號加「停用原因」欄位，區分 Bot 停用與管理者停用。
3. **跨程序同時寫同一帳號**：Bot 停用與伺服器登入剛好同時改同一帳號時，可能後寫蓋前寫（機率低，5～10 人可接受）。若要根除：Bot 改走本機 HTTP 管理端點，或換 SQLite。
4. **Tunnel 之後的 IP**（5E-3）：經 Tunnel 時 `request.client.host` 都是 Tunnel 的位址，IP 限制會變成全體共用；5E-3 要改讀 Tunnel 的真實 IP 標頭（只信任 Tunnel 來的），或把 IP 上限調高。
5. 前端是否顯示「管理者」並在非管理者時停用 LLM 開關（目前只靠 403 訊息）。
6. 管理者的 Bot 指令（恢復帳號、查帳號）沒做，目前只有 `dev_account.py`。

## 使用者要做的事

1. **建 Bot**：到 Discord Developer Portal（https://discord.com/developers/applications）→ New Application → 左邊 Bot → 開啟 **Server Members Intent**（要收身分組變動）。
2. **拿 token**：Bot 頁 → Reset Token → 複製。**只放進環境變數 `TRPG_BOT_TOKEN` 或 `config/bot.local.toml`**，不要貼到聊天或版控。
3. **邀請 Bot 進伺服器**：OAuth2 → URL Generator，勾 `bot`、`applications.commands`，權限至少「Send Messages」；用產生的網址邀請。
4. **建身分組與頻道**：在伺服器新建一個身分組（能領帳號的人）與一個公告頻道（5E-3 用）。Bot 的身分組要排在它之上不是必要的（Bot 只讀身分組，不改）。
5. **拿 ID**：Discord「使用者設定 → 進階 → 開發者模式」打開，右鍵伺服器、身分組、頻道 →「複製 ID」。
6. **填設定**：複製 `config/bot.example.toml` 成 `config/bot.local.toml`，填 `guild_id`、`role_id`、`announce_channel_id`（token 建議用環境變數）。
7. **檢查**：`uv run python scripts/discord_bot.py check`，看到「設定齊全」即可。真實連線等待決 1 決定後再做。
8. **設管理者**：`uv run python scripts/dev_account.py admin <你的帳號> on`（之後才能改大世界的 LLM 開關）。

## 複雜度例外

無（沒有新增 `# noqa`）。
