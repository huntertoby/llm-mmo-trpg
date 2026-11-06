# Phase 5D-R2 報告：5D 審查整理（伺服器端）

範圍：`docs/phases/Phase5計畫.md` 第 1 節表格的 5D-R2 列（審查者指出的 8 項）。除了第 3～7 項，行為不變；swamp 種子 7 重播一致。

## 交付項目

| # | 內容 | 位置 |
|---|---|---|
| 1 | **季末重置政策表**：`SEASON_POLICY`（模型 → 欄位 → `"numeric"` 數值類／`"memorial"` 紀念類），範圍 `CharacterState`、`WorldState`、`RecipeRecord`、`FirstKill`、`AccountRecord`、`LocationNote`；拿不準的欄位列在 `PROVISIONAL`，一律暫標數值類。架構測試 `test_every_saved_field_has_a_season_reset_kind`：表裡每個模型的欄位剛好都分類（新增欄位沒分類、刪掉的欄位還在表裡都失敗）、只有兩種分類、待決欄位都是數值類。只做分類，重置流程在 5F-5 | `server/season_policy.py`、`tests/test_architecture.py` |
| 2 | `FirstKill.season_id`（預設 `FIRST_SEASON_ID`＝`"s1"`：欄位加上之前沒有任何季末重置，舊檔＝第一季）；`FirstKillRegistry.record(..., season_id=)`，世界存檔傳 `world.season_id`；首殺按賽季算（下一季的第一個仍是首殺）。`RecipeRecord.season_id`（必填；打造時寫 `world.season_id`）；舊存檔沒有時 `WorldState` 的 `mode="before"` 驗證器補成世界當季。`FIRST_SEASON_ID` 放在 `world/season.py`，`api.world.SEASON_ID` 改用它 | `server/first_kills.py`、`world/state.py`、`world/crafting.py`、`world/season.py` |
| 3 | 帳號角色上限**按賽季算**（擇一，見代決 R2-1）：`AccountRecord.character_seasons`（角色 → 建立時的賽季；舊檔沒有的角色＝第一季），`characters_in(season)`；`AccountStore(season=…)` 注入目前賽季（伺服器接 `WorldStore.current_season`，還沒有世界存檔時不建立、回第一季）；`check_character_room`、`attach_character`、`/api/auth/status` 的角色數與 `can_create` 只算當季。`scripts/dev_account.py attach` 讀世界資料夾的 `world.json` 賽季 | `server/accounts.py`、`api/world.py`、`api/app.py`、`api/auth.py`、`scripts/dev_account.py` |
| 4 | **帳號檔跨程序寫入**：新 `server/file_lock.py`（`FileLock`：Windows `msvcrt.locking`、其他 `fcntl.flock`，只用標準函式庫）；帳號資料夾的鎖檔 `accounts.lock`。每個 `AccountStore` 操作持有執行緒鎖＋鎖檔（同執行緒可巢狀，只有最外層拿鎖檔）；改一個帳號一律走 `_update`：鎖內**重讀那個帳號檔** → 套用變更 → 寫回。建帳號、角色歸屬在鎖內整個資料夾重讀再檢查唯一。登入的 scrypt 在鎖外比對，發 session 時對最新內容再檢查停用與密碼。測試：伺服器比對密碼時 Bot 停用 → 拒絕且停用不被蓋回；快取沒察覺另一個程序寫入時仍合併；兩個寫入者交錯；鎖被持有時寫入會等 | `server/file_lock.py`、`server/accounts.py`、`tests/server/test_account_lock.py` |
| 5 | **`dev_mode=false` 端點保護**（保守代決，待使用者確認）：新依賴 `require_login`（開發模式關：沒 token 或無效 401、停用 403；開發模式開不檢查），`create_app` 掛在 battles／runs／workshop／gear router。`/api/runs/dev-packs`、`/{run_id}/dev-advance`、`/saves`、`/load` 移到 `runs.dev_router`，**只在開發模式開時掛載**（掛在 `runs.router` 之前，`/saves` 不會被 `/{run_id}` 吃掉）。前端：任何 401（登入端點本身除外，`needsLogin`）都清 token 並發 `AUTH_EXPIRED_EVENT`；App 在大世界以外的畫面聽到就顯示登入畫面（標題「登入」，登入後重新整理接回原畫面；不給「返回首頁」，因為開發模式關時首頁的開戰表單本身就要登入）；首頁的存檔列表是背景請求，401 不導頁（`quiet`）；讀回上次一輪遇到 401 時不忘掉那一輪 | `api/auth.py`、`api/app.py`、`api/routes/runs.py`、`client/src/App.tsx`、`client/src/api/client.ts`、`client/src/auth/auth.ts`、`client/src/screens/LoginScreen.tsx`、`tests/api/test_dev_mode_guard.py` |
| 6 | 登入時帳號不存在：對假雜湊 `_DUMMY_HASH`（同 scrypt 參數）跑一次 `verify_password` 再回「帳號或密碼錯誤」。測試：不存在與密碼錯各跑一次 scrypt、參數相同 | `server/accounts.py`、`tests/server/test_accounts.py` |
| 7 | 首殺紀錄寫入包 try（`WorldStore._record_first_kills`）：失敗只 `logging.exception`，世界動作照常回應（日誌、角色已寫好，之後可從日誌補算）。測試 `test_first_kill_write_failure_does_not_break_the_action` | `api/world.py`、`tests/api/test_announce.py` |
| 8 | 新套件 `trpg.server`：`accounts`、`account_config`、`first_kills`、`announce`、`notes`（`git mv`，內容不變）＋本段的 `file_lock`、`season_policy`；`ruff.toml` 同 api（可讀時間）。全部匯入改路徑（src、tests、scripts），`tests/api/test_accounts.py` 移到 `tests/server/`。import-linter：bot 禁止匯入 `trpg.api`；新增「server 不得匯入 api、cli、bot、sim、llm、narrative」與「engine、world、shared、content、roguelite、skillgen、narrative 不得匯入 server」；server 也不得匯入 bot。`tests/test_architecture.py` 的掃描表同步（含新的偵測／放行案例） | `src/trpg/server/`、`pyproject.toml`、`tests/test_architecture.py` |

## 季末重置政策表（欄位分類）

紀念類＝季末保留；數值類＝季末清掉。＊＝拿不準、暫標數值類（`PROVISIONAL`，見待 PM 決定）。

| 模型 | 紀念類（保留） | 數值類（清掉） |
|---|---|---|
| `CharacterState` | — | `format`、`character_id`、`hero`＊、`origin`、`level`、`xp`、`hp`、`mana`、`stamina`、`region`、`location`、`supplies`、`revealed`、`perception_marks`、`rng_counters`、`pending_encounter`、`camped_at`、`bench`、`fatigued`、`attribute_points`、`visited_towns`、`event_steps`、`pending_event`、`threads`、`next_battle`、`insight`、`flash`、`flash_bases`、`pending_flash`、`skill_usage`、`skill_tier`、`attribute_spent`、`elite_kills`＊、`oath`、`oath_broken_next`、`oath_cooldown_until`、`last_battle`、`quests`、`affinity`、`pending_offers`、`offers_made`、`story_flags`、`talk_days`、`unlocked_skeletons`、`opportunities`、`opportunity_tier_ups`、`finished_skeletons`＊、`failed_skeletons`、`met_opportunities`、`opportunity_hint_day`、`mercenaries`、`shadows`、`party_ai`、`shadow_ai`、`companions`、`companion_bench`、`companion_affinity`、`gold`、`quest_coins`、`bag`、`pouch`、`shop_week`、`shop_affinity`、`gear`、`equipment`、`pending_loot`、`gear_mods`、`crafts`、`generated_skills` |
| `WorldState` | — | `format`、`season_id`、`season_seed`、`season_start`、`flags`、`cleared`、`threads`、`timed_flags`、`shadows`、`recipes`＊ |
| `RecipeRecord` | `code`、`name_zh`、`discoverer`、`discoverer_name`、`discovered_at`、`season_id` | `recipe`＊、`hidden`＊、`base`＊、`steps`＊、`listed`＊ |
| `FirstKill` | `kind`、`target`、`target_name_zh`、`character_id`、`name`、`region`、`location`、`seq`、`at`、`season_id` | — |
| `AccountRecord` | `format`、`account_id`、`username`、`password`、`disabled`、`characters`、`character_seasons`、`discord_id`、`admin`、`created_at`、`sessions` | — |
| `LocationNote` | — | `note_id`＊、`region`＊、`location`＊、`character_id`＊、`name`＊、`text`＊、`at`＊ |

依據：#91「影響數值的全清（等級、技能、裝備、材料、任務幣、世界狀態）；紀念類保留（帳號、稱號、編年史、印記收藏、排行榜與 Boss 擊殺紀錄）」。角色整個是數值類（#91 列的數值都在角色身上）；世界整個是數值類（「世界狀態」）；首殺＝Boss 擊殺紀錄；帳號保留。`RecipeRecord` 的「首位發現者」那幾欄是紀念類（可在 5F-5 收進編年史），配方內容跟著 `WorldState.recipes` 暫標清掉。

## 代決（照最保守做法）

| 編號 | 項目 | 做法 |
|---|---|---|
| R2-1 | 角色上限：按賽季算或重置時修剪 | **按賽季算**：不刪歸屬紀錄（不轉移 #100 照舊看全部賽季），也不用依賴 5F-5 記得修剪；舊帳號的角色＝第一季 |
| R2-2 | 舊首殺紀錄沒有 `season_id` | 當成第一季 `s1`（欄位加上前沒有任何季末重置，「當季」就是 s1）；首殺紀錄檔不知道世界當季，所以用常數而不是讀世界 |
| R2-3 | 首殺是否按賽季分 | 是：`record` 只看同一季的紀錄判斷「還沒人打過」（新一季的第一個仍是首殺） |
| R2-4 | 鎖的範圍 | 整個帳號資料夾一把鎖檔（建帳號、角色歸屬要檢查全部帳號）；讀取也在鎖內（避免 Windows 換檔時讀到一半）；scrypt 在鎖外 |
| R2-5 | `require_login` 在開發模式開時帶了無效 token | 照舊不檢查（開發模式開時這些 router 原本完全不看 token） |
| R2-6 | 開發模式關時 `/api/runs/saves`、`/load` | 不掛載：`GET /saves` 落到 `GET /{run_id}` 回 404、`POST /load` 回 405；`POST /{run_id}/save` 照留（規格只列列表與讀檔） |
| R2-7 | 前端登入畫面的「返回首頁」 | App 層的登入畫面不給（首頁本身要登入，回去會立刻導回來）；大世界入口的登入畫面照舊 |
| R2-8 | bot 的 import-linter `allow_indirect_imports` | 保留：bot 只直接匯入 server／shared，但 server 自己用 `trpg.world.save` 等；拿掉會讓 bot → server → world 的間接匯入違約。bot 對 `trpg.api` 的直接匯入已禁止 |
| R2-9 | `RecipeRecord.season_id` 必填或有預設 | 必填；舊存檔經 `WorldState` 補值（獨立讀 `RecipeRecord` 的地方目前沒有） |

## 待 PM 決定

1. **第 5 項整體**（保守代決，待使用者確認）：開發模式關時 runs／battles／workshop／gear 要登入、dev 與存檔列表／讀檔不掛。
2. 分類拿不準的欄位（暫標數值類，季末清掉）：
   - `WorldState.recipes` 與 `RecipeRecord.recipe／hidden／base／steps／listed`：配方表要不要跨季（配方能直接打出裝備，偏數值類）。
   - `CharacterState.elite_kills`、`finished_skeletons`：算不算「編年史」（目前是角色進度；編年史可由世界日誌與首殺另算）。
   - `CharacterState.hero`（含角色名）：要不要留名字給編年史／排行榜（首殺已存當時的名字）。
   - `LocationNote` 全部：地點留言要不要跨季（#91 沒提到）。
3. 開發模式關時 `POST /api/runs`、`/api/gear/check` 的 `dev_pack`、`test_mode`、`test_equipment` 欄位仍可用（登入後）；要不要也擋。
4. `/api/battles/{id}` 只檢查登入、不檢查戰鬥屬於誰（battle_id 是隨機的；大世界戰鬥也走這裡）；要不要加歸屬檢查。
5. main 上 `tests/sim/test_push_check.py:76`（5F-2 的 commit 5c77692d）超過 100 字、`ruff format --check` 也不過；這段沒改那個檔，合併後請順手修。

## 改了既有斷言的地方

沒有。只改匯入路徑（`trpg.api.<模組>` → `trpg.server.<模組>`）、`tests/api/test_accounts.py` 移到 `tests/server/`、`tests/test_architecture.py` 的依賴表多了 server 規則與 bot 不得匯入 api。

## 檢查結果

- ruff check、ruff format --check：通過（`tests/sim/test_push_check.py` 是 main 帶來的既有問題，見待決 5）；mypy（1170 檔）、lint-imports（13 kept）：通過。
- pytest `tests/api tests/world tests/bot tests/server tests/test_architecture.py`（-n 8）：1172 通過。
- pytest `tests/cli -m "slow or not slow" --timeout=3000`（-n 8）：180 通過。
- vitest：136 檔、1270 測試通過；`pnpm build`：成功（只有既有的 chunk 大小警告）。
- swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- OpenAPI 重產：只有 `/api/runs` 路徑的排列順序變了（dev router 掛在前面），型別沒變；`schema.d.ts` 同步重產。
- 預覽（8160 埠，開發模式關、存檔在 worktree 的 `.scratch_5dr2/`）：首頁直接顯示登入畫面（沒有返回首頁），用本機測試帳號登入後回到首頁、開戰表單正常載入。伺服器已關。
