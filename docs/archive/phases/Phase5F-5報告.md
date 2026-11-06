# Phase 5F-5 完成報告：季末重置

規格：`docs/phases/Phase5計畫.md` 第 40 節（本段開工時補上；「之後各段規格」順延成 41）。依據：第 1 節 5F-5 列（玩法 PM 2026-11-03 代決）、09 9.7、#91。荒原內容已在 5F-5a 做完，本段沒有動。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | **分類定案**：`PROVISIONAL` 清空（5D-R2 的四項待決都定為數值類）；新增 `CARRIED`（數值類但季末先寫進紀念紀錄：`hero` 的名字與外觀、`elite_kills`、`finished_skeletons`、`WorldState.recipes` 的首位發現）與 `HERO_LEGACY_FIELDS`（`name_zh`、`race`、`doll`）；新的紀念類模型 `SeasonChronicle`、`SeasonChronicleEntry`、`ChronicleHero`、`RecipeDiscovery` 加進政策表 | `server/season_policy.py`、`server/chronicle.py` |
| 2 | **季末重置流程** `season_reset()`：檢查 → 備份整個存檔資料夾（`<備份根>/saves-<UTC 時間>-<舊季>/`，預設存檔資料夾旁的 `saves-backups/`，已加進 `.gitignore`；`*.lock` 不複製）→ 編年史 `chronicle/seasons.json`（同一季已有就不覆寫，中斷重跑不會用半套資料蓋掉）→ `league/` 搬到 `league_history/<舊季>/`（每份賽程的 `entries` 清空）→ 刪 `chars/`、`log.jsonl`、`notes.json` → 新的 `world.json`（新 `season_id`＝`s<N+1>` 或參數、種子＝舊種子＋新 ID 的 sha256 或參數、開賽時間＝參數）。dry-run 不寫任何檔。整段持有帳號資料夾鎖檔（`AccountStore.locked()`）。確定性（同存檔＋同參數＋同 `now` → 逐位元相同） | `server/season_reset.py`、`server/accounts.py` |
| 3 | 入口：`POST /api/world/season/reset`（管理者；預設 dry-run；執行要 `confirm_season`＝目前季 ID；循環賽背景執行中拒絕；執行後清 `WorldStore` 快取與循環賽快取）、`scripts/season_reset.py`（預設 dry-run，`--execute` 才寫；說明寫「先停伺服器」） | `api/world.py`、`api/routes/world.py`、`api/auth.py`、`scripts/season_reset.py` |
| 4 | 新賽季建角：`GET /api/world/legacy`（自己帳號上季的角色）、`POST /api/world/characters` 的 `legacy_character`（沿用名字、種族、紙娃娃；不是自己的 404；新角色 ID 避開上季角色 ID） | `api/world.py`、`api/chronicle_schemas.py`、`api/world_schemas.py` |
| 5 | 編年史 `GET /api/world/chronicle`（所有人可看：上季角色的紀錄文字、首位發現的配方、循環賽最終排名、首殺、評分榜前 5 名）；`AccountView.admin` | `api/chronicle_schemas.py`、`api/account_schemas.py` |
| 6 | 前端：角色畫面加「沿用上季角色」選單（帶入名字與種族、名稱鎖住）、編年史區塊、管理者（或開發模式沒登入）的「季末重置」區塊（填開賽日 → 預覽清／留清單與編年史文字 → 輸入目前季 ID → 執行；條件改了要重新預覽） | `client/src/world/WorldCharacterPicker.tsx`、`ChroniclePanel.tsx`、`SeasonResetPanel.tsx`、`season.ts` |
| 7 | Bot：貼過的首殺鍵加賽季（`s1` 照舊 `<kind>:<target>`，之後的季 `<季>:<kind>:<target>`），新一季同一種精英的首殺照樣會貼 | `bot/announcer.py` |
| 8 | 架構測試：政策表每個模型都有 `season_reset.HANDLERS`，處理和分類一致（整個數值類＝刪／換新、整個紀念類＝不動、混合＝分開且紀念欄位都在 `SPLIT_CARRIERS` 的模型裡）；`CARRIED` 每項都有處理函式 | `tests/test_architecture.py` |

## 測試

- `tests/server/test_season_reset.py`（14）：假賽季（2 帳號、2 角色有等級／金錢／精英擊殺／完成骨架／種族與紙娃娃；世界有旗標、鑰匙、配方 2 筆、報名 2 位、等級加成；留言、首殺、評分榜、首殺戰鬥紀錄、循環賽＋舊賽程、編年史、Bot 狀態、一輪存檔）重置後，`CHECKS` 對政策表**每個模型**逐欄位檢查（`set(CHECKS) == set(SEASON_POLICY)`）；dry-run 不寫檔；備份完整；備份放在存檔資料夾裡拒絕；確定性；未結束與循環賽沒跑完要 `force`；季 ID 規則；中斷後重跑；腳本 dry-run／執行。
- `tests/api/test_season_reset_api.py`（3）：dry-run → 確認不符 409 → 執行 → 角色清空、編年史、沿用上季角色建角；非管理者 403、沒 token 401、`admin` 欄位；沿用別人的上季角色 404、新季角色上限從 0 算。
- `tests/bot/test_announcer.py`：新一季同一種精英首殺照樣貼。`client/src/world/season.test.ts`。
- 瀏覽器實測（埠 8240、暫存存檔資料夾 `scratchpad/f5reset/saves`、自己的分頁）：預覽列出清／留與「霧中旅人：第一季：擊倒盜賊頭目；完成渡婆婆：有人替她了結斷崖幫的舊帳」→ 輸入 s1 執行 → 備份資料夾建立、角色清空、編年史顯示第一季、沿用選單帶入名字並鎖住。使用者的 `saves/` 沒動。

## 交件檢查

- `ruff check`、`ruff format --check`、`mypy`（1210 檔）、`lint-imports`（13 契約）通過。
- `tests/world`、`api`、`server`、`bot`、`content`、`test_architecture.py`（`-n 8`）：3384 通過。
- vitest 141 檔 1300 通過；`pnpm build` 通過。OpenAPI 已重產（`client/openapi.json`、`schema.d.ts`）。
- swamp 種子 7 重播通過（88 動作、313 事件）。已 `git merge main`。

## 代決（照最保守的預設；規格 40.9）

| # | 事項 | 代決 |
|---|---|---|
| 5F5-1 | 配方碼與發現時間 | 照 5D-R2 的分類留著（紀念類）；沒有配方內容，配方碼不能打造 |
| 5F5-2 | 「外觀」的範圍 | 名字、種族、紙娃娃；出身、武器、關鍵字照新角色重選 |
| 5F5-3 | 世界日誌 | 刪掉（只在備份裡）；舊季首殺的 `seq` 要到備份查證 |
| 5F5-4 | 賽季還沒結束 | 要 `force` |
| 5F5-5 | 進行中的大世界戰鬥 | 跟著角色清掉；循環賽背景執行中拒絕 |
| 5F5-6 | 管理者權限 | 同 `require_admin`（開發模式沒登入可用），執行另外要輸入目前季 ID |
| 5F5-7 | 同一個上季角色沿用幾次 | 不限 |
| 5F5-8 | 編年史文字 | 「第一季：擊倒〈精英中文名〉；完成〈骨架的誰：想要什麼〉」，兩者都沒有＝「走過這一季」；模板寫在程式（`season_reset.chronicle_hero`），沒有放進 `content/` |
| 5F5-9 | 不認得的世界資料夾檔案 | 保留並列在報告的「保留」 |
| 5F5-10 | 三選一預先計算的快取 | 不清（鍵含角色與世界狀態，不會被舊資料命中） |

## 待 PM 決定

1. 世界日誌要不要搬進存檔資料夾裡的歷史區（例如 `league_history` 旁的 `log_history/<季>/`），讓舊季首殺不用翻備份就能查證？目前只在備份裡。
2. 編年史文字的寫法（5F5-8）與要不要改成內容資料；精英用的是精英種類的中文名（含詞綴），骨架用「誰：想要什麼」，不一定好讀（例「渡婆婆：有人替她了結斷崖幫的舊帳」）。
3. 沿用種族：種族有種族技與環境被動（不加數值），目前當外觀一起沿用；要不要改成只沿用名字、種族照新選。
4. 舊季的循環賽重播：搬到 `league_history/` 後網頁上的重播看不到（檔案還在，`trpg battle replay` 可驗）；要不要做舊季的重播頁。
5. 5F-3b 的帳號稱號若加在 `AccountRecord`，要在政策表標紀念類（架構測試會擋沒分類的欄位；`HANDLERS` 對 `AccountRecord` 已是 `keep`）。
6. 管理者權限在開發模式沒登入也能重置（同 LLM 開關）；正式部署 `dev_mode=false` 時只有管理者帳號。要不要季末重置一律要求管理者帳號。
