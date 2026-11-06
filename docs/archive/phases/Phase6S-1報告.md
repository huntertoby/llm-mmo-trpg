# Phase 6S-1 完成報告：上線前安全修正

規格：`docs/phases/Phase6計畫.md` 第 1 節 6S-1 列。使用者原話（專案 PM 轉達，2026-11-04）：「要不要擋掉開發用的作弊欄位 當然擋」。

只動 `src/trpg/api/`、`tests/api/`。引擎、content、前端都沒改；OpenAPI 沒變（`export_openapi.py` 重跑無差異，所以不必重新產生前端型別）。

## 1. 開發用欄位清單（grep 全部 API schema 的結果）

開發模式關時，下表「擋」的欄位只要有填就回 **403**，訊息是「`<欄位名>` 是開發用欄位，開發模式才能用」（例：`build 是開發用欄位，開發模式才能用`；同時填多個時用「、」接起來）。未登入照 5D-R2 先回 401。開發模式開時行為不變。

| 入口 | 欄位 | 處理 | 說明 |
|---|---|---|---|
| `POST /api/runs`（`CreateRunRequest`） | `build` | 擋 | 回歸範本開局 |
| 同上 | `dev_pack` | 擋 | 開發者起始包 |
| 同上 | `test_mode`（為真） | 擋 | 測試模式（戰後回滿） |
| 同上 | `test_equipment`（非空） | 擋 | 測試模式裝備 |
| `POST /api/battles`（`CreateBattleRequest`） | `hero_build` | 擋 | 回歸範本主角 |
| 同上 | `dev_pack` | 擋 | 開發者起始包 |
| 同上 | `ally_builds`（非空） | 擋 | 用 build 當隊友；**空串列不擋**（工坊試玩、只有主角），見待決 1 |
| 同上 | `equipment`（非空） | 擋 | 裝備測試（可自訂物品與詞條），見待決 2 |
| 同上 | `custom_skills`、`replace_skills` | 不擋 | 技能工坊「裝上試玩」，玩家功能，技能照常驗證，見待決 3 |
| `POST /api/gear/check`（`GearCheckRequest`） | `hero_build`、`dev_pack` | 擋 | `equipment` 只是檢查、不改狀態，不擋 |
| `POST /api/workshop/export`（`WorkshopExportRequest`） | `allow_illegal`（為真） | 擋 | 開發者模式匯出不合法半成品，見待決 4 |
| `GET /api/runs/dev-packs`、`/saves`、`POST /load`、`/{run_id}/dev-advance` | 整個端點 | 原本就不掛（5D-R2） | 不變 |
| `/api/world/*` | — | 沒有開發用欄位 | `CreateWorldCharacterRequest.seed` 不擋，見待決 5 |

做法：每個請求 model 加 `dev_fields()` 方法（回傳有填的開發用欄位名，不影響 OpenAPI），路由一開頭呼叫 `trpg.api.auth.reject_dev_fields(request, body.dev_fields())`；新例外 `DevModeRequiredError` 在 `ERROR_STATUS` 對應 403。

## 2. 帶 ID 的端點清單與擁有者檢查

開發模式關時，別人的（或沒有主人的）一律回 **404**，訊息和真的不存在時一模一樣（`找不到戰鬥 <id>`、`找不到一輪 <id>`、`找不到角色 <id>`），不透露存在與否。未登入 401。開發模式開照舊不檢查。

| 端點 | 檢查 | 備註 |
|---|---|---|
| `GET /api/battles/{battle_id}` | 6S-1 新增 | |
| `GET …/history`、`…/log`、`…/skill-reasons`、`…/hero-cards` | 6S-1 新增 | |
| `POST …/actions`、`…/decision`、`…/preview` | 6S-1 新增 | |
| `GET …/summons/{summon_id}/command-options`、`…/infuse-options` | 6S-1 新增 | |
| `PUT …/orders` | 6S-1 新增 | |
| `GET /api/skills/{skill_id}?battle_id=` | 6S-1 新增 | 帶 `battle_id` 時查戰鬥規則包；開發模式關要登入且是自己的戰鬥 |
| `GET /api/skills/{skill_id}`（查各輪生成技能） | 6S-1 新增 | 開發模式關只查自己帳號的一輪；沒登入不查（404） |
| `GET /api/runs/{run_id}` | 6S-1 新增 | |
| `POST /api/runs/{run_id}/battle`、`…/choice`、`…/save` | 6S-1 新增 | |
| `POST /api/runs/{run_id}/flash-preview`（閃現預覽） | 6S-1 新增 | |
| `POST /api/runs/{run_id}/allocation-preview`（配點預覽） | 6S-1 新增 | |
| `POST /api/runs/{run_id}/dev-advance`、`POST /api/runs/load` | 開發模式關不掛 | 5D-R2 |
| `/api/world/characters/{character_id}/…`（含 `battle`、`flash-preview`、`allocation-preview`、`actions`、`situation`、`chat`、`board`、`absence`、`league`、`notes`） | 已有（5E-1 `require_world_access`） | 開發模式開時帶了 token 也依帳號（原行為不變） |
| `POST /api/world/characters/{id}/league/matches/{match_id}/replay` | 已有（角色檢查） | 6S-1 另外把重播開出的戰鬥工作階段主人記成看的人 |
| `DELETE /api/world/characters/{id}/notes/{note_id}` | 已有（角色＋作者） | |
| `GET /api/world/league/matches/{match_id}/log` | 不檢查 | 循環賽結果本來就公開，見待決 6 |
| `DELETE /api/world/notes/{note_id}`、`/league/run`、`/season/*`、`POST /llm` | 已有（管理者） | |

做法：
- `BattleSession.owner`、`RunSession.owner`（帳號 ID，`None`＝沒有主人）。
- 記主人的地方：`POST /api/battles`、`POST /api/runs`（`auth.owner_id`：開發模式關照 `viewer`；開發模式開用 `optional_account`，無效 token 也不 401，維持原行為）；一輪的戰鬥跟著一輪的主人（`RunStore.battle`）；大世界的戰鬥＝角色所屬帳號（`WorldStore.battle` 用 `actor_of`）；循環賽重播＝看的人。
- 檢查：`auth.check_owner(request, owner, missing_error)`；戰鬥路由用 `routes/battles.py` 的 `owned_battle`，一輪路由用 `routes/runs.py` 的 `_owned_run`。
- `RunStore.find_skill` 加 `owner` 參數。

## 3. 測試

新增：
- `tests/api/test_owner_guard.py`：每個帶 ID 的入口 ×（開發模式開／關）×（自己／別人／未登入）；戰鬥端點再乘上三種來源（自由戰鬥、一輪、大世界）。請求順序是別人 → 未登入 → 自己，擋不住時抓得到。另有「別人的與不存在的回應一樣」與「生成技能卡只查自己的一輪」。
- `tests/api/test_dev_fields_guard.py`：每個開發用欄位 ×（開發模式開／關）×（登入／未登入）；另外確認一般玩家請求（含 `ally_builds: []` 的工坊試玩）開發模式關照常。

既有測試都沒有改（預設是開發模式，主人檢查不生效）。

結果：
- `tests/api/test_owner_guard.py`、`tests/api/test_dev_fields_guard.py`：129 passed、1 skipped（開發模式開時「別人與不存在一樣」不適用）。
- 相關的既有測試（`test_dev_mode_guard`、`test_runs_api`、`test_battle_start_api`、`test_gear_api`、`test_workshop_api`、`test_world_league`、`test_run_test_mode_api`、`test_routes`、`test_auth_api`、`test_world_api`、`test_notes`、`test_season_reset_api`、`test_world_board`、`test_openapi_snapshot`、`test_full_battle`、`test_skill_reasons_api`、`test_run_autosave`、`test_season_boss_api`）：全部通過。
- `ruff check`、`ruff format --check`、`mypy src`（strict）、`lint-imports`（13 kept）通過；`trpg battle --map open_plain --seed 3` 重播驗證通過。
- 沒跑全量（照規定）。

## 4. 待 PM 決定（都照最保守的預設做完）

1. **`ally_builds: []` 不擋**：工坊試玩與裝備測試畫面都送空串列（只有主角）；只有真的給了 build 才 403。要連空串列也擋，工坊試玩在正式環境會壞。
2. **`equipment`（`POST /api/battles`）擋了**：裝備測試畫面（`GearScreen`，3G-G4 開發工具）在開發模式關時按「進戰鬥」會拿到 403；`/api/gear/catalog` 與 `/api/gear/check`（不帶開發欄位）照常。要是裝備測試要開放給玩家，就把這條拿掉。
3. **`custom_skills` 不擋**：技能工坊「裝上試玩」是玩家功能，技能照常驗證預算與合法性。
4. **`allow_illegal` 擋了**：只是匯出 YAML 文字、不影響遊戲，但屬於開發者模式欄位。
5. **大世界建角的 `seed` 不擋**：可以指定起始技能的種子（等於可以挑起始技能）。不確定算不算開發欄位，先不擋。
6. **`GET /api/world/league/matches/{match_id}/log` 不檢查**：循環賽的結果與編年史本來就所有人可看。
7. **開發模式下建立的戰鬥與一輪**（沒帶 token＝沒有主人），之後開發模式關時一律 404。工作階段只在記憶體，伺服器重開就沒了，實際上不會發生。
8. 前端沒改：`?dev=1` 的開發者選單在正式環境照樣顯示，但送出會拿到 403（訊息已是中文）。要不要依 `/api/auth/status` 的 `dev_mode` 把選單藏起來，另排前端段。
