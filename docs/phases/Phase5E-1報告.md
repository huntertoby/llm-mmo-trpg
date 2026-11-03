# Phase 5E-1 完成報告：帳號與角色

> 規格：`docs/phases/Phase5計畫.md` 第 28 節（本段新增；原「之後各段規格」順延為 29）。分支 `worktree-agent-ae94e77e5cb38e9a2`。

## 交付

| 項目 | 檔案 |
|---|---|
| 規格（含 5E-4 設計預留 28.12） | `docs/phases/Phase5計畫.md` 28 |
| 帳號服務層（建立、登入、驗證、登出、重設密碼、停用、角色歸屬；`trpg-account/1`） | `src/trpg/api/accounts.py` |
| 設定（`[accounts]`：開發模式、角色上限 3、session 168 小時、帳號資料夾；環境變數覆寫） | `config/server.toml`、`src/trpg/api/account_config.py` |
| 登入依賴與端點（`GET /api/auth/status`、`POST /api/auth/login`、`POST /api/auth/logout`） | `src/trpg/api/auth.py`、`account_schemas.py`、`routes/auth.py` |
| 大世界依帳號存取（router 層依賴，之後加的 `/api/world` 端點自動套用） | `src/trpg/api/routes/world.py`、`app.py` |
| 開發用腳本（create／list／disable／enable／reset-password／attach） | `scripts/dev_account.py` |
| 前端：登入畫面、大世界入口判斷、帳號一行與登出、401 自動回登入 | `client/src/auth/auth.ts`、`screens/LoginScreen.tsx`、`screens/WorldEntry.tsx`、`world/WorldCharacterPicker.tsx`、`api/client.ts` |
| 測試 | `tests/api/test_accounts.py`（21）、`tests/api/test_auth_api.py`（7）、`client/src/auth/auth.test.ts`（6） |

## 安全

- 密碼：`hashlib.scrypt`（n=2^14、r=8、p=1、32 位元組）＋16 位元組隨機鹽；只存雜湊；`hmac.compare_digest` 比對；不寫 log、不進錯誤訊息。帳號不存在與密碼錯回同一句。
- token：`secrets.token_urlsafe(32)`；檔裡只存 SHA-256；每帳號最多 5 個；重設密碼、停用時全部失效。
- 測試密碼都用 `secrets` 當場產生；沒有金鑰進版控。

## 檢查結果

- `ruff check`、`ruff format --check`、`mypy`（1110 檔）、`lint-imports`（9 kept）全過。
- `tests/api tests/world tests/test_architecture.py -n 8`：939 passed。
- vitest 131 檔 1239 passed；`tsc --noEmit`、`vite build` 成功。
- swamp 種子 7 重播通過（88 動作、313 事件）。
- OpenAPI 已重產（`client/openapi.json`、`schema.d.ts`），快照測試通過。
- 瀏覽器（8120 埠、開發模式關、暫存資料夾）：首頁「進入大世界」→ 登入畫面 → 錯誤密碼顯示「帳號或密碼錯誤」→ 正確登入 → 「帳號 tester・角色 0／3」→ 建角色（1／3）→ 進入、移動到渡口石階 → 換角色 → 登出回登入畫面、token 已清；未帶 token 的 `/api/world/characters` 回 401。開發模式開的情況由 API 測試涵蓋。

## 代決（照規格 28.11）

| # | 代決 |
|---|---|
| 5E1-1 | 開發模式旗標預設開（照舊不用登入）；開著時帶了有效 token 仍依帳號存取，方便本機測登入 |
| 5E1-2 | 角色建立 **不進** 世界日誌：帳號屬於 API／服務層；`trpg-wlog/1`、重播不變；歸屬記在帳號檔 |
| 5E1-3 | 開發模式建的舊角色不自動歸屬；用 `dev_account.py attach` 歸到帳號 |
| 5E1-4 | 「朋友」名單照現狀（同伺服器所有其他角色都能借） |
| 5E1-5 | session 存 token 雜湊在帳號檔（重啟仍有效），7 天、每帳號 5 個 |
| 5E1-6 | `/api/world/llm` 開發模式關時要登入 |
| 5E1-7 | 一輪、工坊、戰鬥端點不加登入（戰鬥 ID 是 `token_urlsafe(12)`） |
| 5E1-8 | 帳號名稱 3～20 字英數底線、不分大小寫；密碼 8～128 字 |
| 其他 | 帳號存在 `<存檔資料夾>/accounts/`（不在 `world/` 下，季末重置不清）；別人的角色回 404 不回 403 |

## 待 PM 決定

1. **朋友名單**（5C2-1／5E1-4）：要不要限制成「朋友＋自己的角色」？朋友怎麼來（Discord 好友、手動加、同伺服器全部）設計沒寫。
2. 開發模式何時改成關（開服前）；開著時任何人不登入都能動所有角色。
3. `/api/world/llm` 是伺服器全域開關：是否只給管理者改。
4. 登入嘗試次數限制（防暴力猜密碼）沒做；5E-3 對外開放前要不要加。
5. `dev_account.py attach` 不檢查角色檔是否存在（開發用）。

## 複雜度例外

無（沒有新增 `# noqa`）。
