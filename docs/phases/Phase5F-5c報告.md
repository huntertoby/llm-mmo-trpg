# Phase 5F-5c 完成報告：季末重置收尾

規格：`docs/phases/Phase5計畫.md` 第 41 節（本段開工時補上；「之後各段規格」順延成 42）。依據：第 1 節 5F-5c 列（玩法 PM 2026-11-03 代決）、09 9.7「季末重置細節」、`Phase5F-5報告.md` 的待 PM 決定 1～4。開發 PM 另補兩項（玩法 PM 2026-11-03 代決）：熔核類狀態不外流、商店寫出加價原因。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | **唯讀封存**：季末重置把世界日誌 `log.jsonl`、循環賽 `league/`（賽程、每場戰鬥紀錄、規則改過的舊賽程）、賽季 Boss 首殺的戰鬥紀錄 `season_boss/` 從世界資料夾搬進 `<存檔資料夾>/archive/<舊季>/`（相對路徑不變，`FirstKill.battle_log` 在封存裡照同一路徑找），寫 `manifest.json`（`trpg-season-archive/1`，每個檔的 sha256 與大小），封存裡每個檔 `os.chmod` 成唯讀（Windows 唯讀屬性／macOS 0444）。只有重置會寫；重置報告多一個 `archive` 欄位。備份 `saves-backups/` 照舊。5F-5 的 `league_history/` 不再寫（舊資料夾仍認得、保留） | `server/season_archive.py`、`server/season_reset.py` |
| 2 | **重播查證**：`verify_first_kill`（世界日誌該序號是那個角色的動作；有戰鬥紀錄就確定性重播、比對最終狀態與事件、要是我方勝）、`verify_league_match`（重播後比對賽程紀錄的勝方、輪數、結束原因）。舊季讀封存、目前這一季讀世界資料夾；封存檔和清單的 sha256 不同要報出「封存後被改過」；紀錄被改到重播丟例外也回報成不一致。入口：`POST /api/world/season/verify`（管理者，`require_season_admin`；找不到 404、缺 `target`／`match_id` 422）、`scripts/season_verify.py`（結束碼 0 一致／1 不一致／2 找不到） | `server/season_archive.py`、`api/world.py`、`api/routes/world.py`、`api/chronicle_schemas.py`、`api/app.py`、`scripts/season_verify.py` |
| 3 | **編年史列事實**：模板搬進 `content/world/season.yaml` 的 `chronicle`（`ChronicleTemplates`／`ChronicleFact`，載入時檢查佔位字）。順序：等級、精英、Boss（區域 Boss＝`world/loot.yaml` 的 `bosses`，加賽季 Boss）、全服首殺、主線章節（完成的 `kind: main` 任務）、事件、首位發現的配方、循環賽名次。`ChronicleHero` 加 `level`、`bosses`、`first_kills`、`chapters`、`recipes`、`league_rank`（政策表紀念類；`elites` 不再含區域 Boss）；`CARRIED` 加角色的 `level`、`quests` 與世界的 `boss_clears`、`league_entries`。例：「第一季：到達 7 級；擊倒盜賊頭目；全服首殺盜賊頭目；完成主線「灰燼之心」；完成事件「渡婆婆：…」；首位發現配方「霧鐵盔」、「灰燼盔」；影子循環賽第 1 名」 | `content/world/season.yaml`、`content/world_season.py`、`server/season_reset.py`（`SeasonFacts`、`season_facts`、`chronicle_hero`）、`server/chronicle.py`、`server/season_policy.py` |
| 4 | **種族不算外觀**：沿用上季角色時名字＋紙娃娃照沿用；`race` 省略＝帶上季的、給了就照新選（免費）；種族改了時紙娃娃裡跟著種族的部件（`RACE_DOLL_FIELDS`＝膚色、髮型、髮色、眼睛、骷髏）改回新角色範本的預設，裝備、褲子、飾邊、主手材質不動。前端沿用選單本來就能改種族（原本被伺服器蓋回上季的），說明文字改成「種族預設帶上季的，可以免費改」 | `server/chronicle.py`（`legacy_doll`）、`api/world.py`、`api/world_schemas.py`、`client/src/world/WorldCharacterPicker.tsx` |
| 5 | **熔核類狀態只給敵人**：`StatusDef.enemy_only`（必須沒有 `budget_points`）；`molten_burst`（熔核爆裂）、`frost_ember_burst`（寒燼爆裂）與同類的 `heart_ember_burst`（殼縫熔核）標上。現況查核：三者本來就沒有 `budget_points`，生成器的施加清單已排除，但 `rarity_statuses`（LLM 版型的狀態清單）、提議的引用表、「目標有某狀態」條件與 `on_status_applied` 觸發的隨機參數、工坊的狀態選項會列出它們。改法：`skill_reference_problems` 把 `enemy_only` 當未知狀態並加一句「只給敵人」（內容載入與技能驗證器共用，所以生成器、候選、閃現、工坊、LLM 提議都擋），上述清單也排除 | `content/battle.py`、`content/statuses.yaml`、`content/library.py`、`skillgen/proposal.py`、`option_params.py`、`composer_parts.py`、`random_composer.py` |
| 6 | **商店寫出加價原因**：`ShopPriceEffect.reason_zh`（content；熔岩潰堤＝「熔岩潰堤失守」）；`ShopView.price_notes_zh`（已結束的世界事件、結果的價格加成指到這家店的每一筆：「熔岩潰堤失守：買價 +20%」）；前端商店標題下顯示（`world-shop-price-note`）。OpenAPI 已重產 | `content/world/season.yaml`、`content/world_season.py`、`world/economy.py`（`shop_price_notes`）、`api/world_economy_*`、`client/src/world/EconomyPanel.tsx` |
| 7 | 前端季末重置區塊多一行「唯讀封存：…」 | `client/src/world/SeasonResetPanel.tsx` |

## 測試

- `tests/server/test_season_archive.py`（4）：真的跑一場 2 人循環賽（2 場）＋一筆用其中一場當戰鬥紀錄的賽季 Boss 首殺；目前這一季從世界資料夾查證；重置後從封存查證每一場與首殺（日誌序號、重播一致、我方勝）、清單欄位；找不到拋錯；改過的封存檔 → sha256 不符＋重播失敗；腳本。
- `tests/server/test_season_reset.py`：封存的內容、清單、唯讀（`os.access(W_OK)` 為假）、世界資料夾裡不再有日誌／循環賽／首殺紀錄；編年史整行文字、區域 Boss 與賽季 Boss、名次、首殺、配方、主線章節。
- `tests/server/test_legacy_doll.py`（3）、`tests/api/test_season_reset_api.py`：沿用時改種族；查證端點 401／403／404／422。
- `tests/content/test_enemy_only_statuses.py`（5）：三個狀態是 `enemy_only`、不在任何稀有度的清單；引用它的技能被擋；內容技能不用；只出現在 `statuses.yaml` 與 `units/`，那些單位不在 build、傭兵、開發起始角色、種族、出身裡；循環賽開場狀態不含它們。
- `tests/content/test_world_season.py`：編年史模板在 content、佔位字檢查。`tests/world/test_ashen_waste.py`：加價原因（函式與 `ShopView`）。`client/src/world/economy.test.ts`：加價原因顯示。

## 交件檢查

- `ruff check`、`ruff format --check`、`mypy`（1218 檔）、`lint-imports`（13 契約）通過。
- `tests/world`、`api`、`server`、`bot`、`content`、`test_architecture.py`（`-n 8`）：3412 通過。因為動到技能池清單，另跑 `tests/skillgen`、`tests/llm`：4111 通過、14 略過。
- vitest 141 檔 1301 通過；`pnpm build` 通過。OpenAPI 已重產（`client/openapi.json`、`schema.d.ts`）。
- swamp 種子 7 重播通過（88 動作、313 事件）。已 `git merge main`（5F-3b、5F-3c 文件；衝突只在 import，帳號稱號照 main）。
- 沒有做瀏覽器實測（前端只多兩行文字，元件測試涵蓋）。

## 代決（照最保守的預設）

| # | 事項 | 代決 |
|---|---|---|
| 5F5c-1 | 封存的範圍 | 只搬規格列的三類（日誌、循環賽、賽季 Boss 首殺戰鬥紀錄）；首殺紀錄、評分榜、編年史照舊留在世界資料夾（紀念類、要繼續寫） |
| 5F5c-2 | 中斷後重跑 | 封存裡已有同名的就用 `<名字>-2` 起的空位，不覆蓋；清單重寫 |
| 5F5c-3 | 唯讀的範圍 | 只把檔案設唯讀，資料夾不動（macOS 資料夾唯讀會擋後續重跑與清理） |
| 5F5c-4 | 查證誰能用 | 管理者（同季末重置的預覽：`require_season_admin`）；腳本不用登入 |
| 5F5c-12 | 精英首殺的查證 | 精英首殺沒有戰鬥紀錄，只查世界日誌該序號是那個角色的動作（不做整個世界重播：日誌重播要初始角色快照） |
| 5F5c-5 | 「Boss」的定義 | 區域 Boss＝`world/loot.yaml` 的 `bosses`（灰燼之心、霧鎖真人），加賽季 Boss（`boss_clears` 有這個角色）；精英欄不再列區域 Boss |
| 5F5c-6 | 循環賽名次怎麼對到角色 | 編年史名次的 `account` 對 `world.league_entries` 的 `account` → 角色 ID |
| 5F5c-7 | 編年史沒有模板 | `season.yaml` 沒有 `chronicle` 時只寫季名（不在程式裡留備用文字）；等級每個角色都有，所以 `empty`（「走過這一季」）實際上用不到 |
| 5F5c-8 | 跟著種族的紙娃娃部件 | 膚色、髮型、髮色、眼睛、骷髏（前端畫圖時這些會被種族外觀蓋過）；改回「新角色範本」的值；範本沒有紙娃娃就整個用預設 |
| 5F5c-9 | 加價原因的寫法 | 「熔岩潰堤失守：買價 +20%」（用「買價」不是「價格」：賣價不受影響，代決 5F5b-3）；原因文字在 content，`reason_zh` 空時用世界事件名 |
| 5F5c-10 | `heart_ember_burst`（殼縫熔核） | 同類（承載灰燼之心戰蜥蜴的 ×1.5），一起標 `enemy_only` |
| 5F5c-11 | `enemy_only` 狀態在「目標有某狀態」條件 | 也擋（技能池不能提到它們） |

## 待 PM 決定

1. 重播查證要不要開放給一般玩家（例如編年史上的首殺、名次旁加「查證」按鈕）？目前只有管理者與腳本。
2. 精英首殺只查日誌序號；要不要之後替精英首殺也存那一場的戰鬥紀錄（像賽季 Boss 一樣）以便完整重播？
3. 編年史模板的措辭（`season.yaml` 的 `chronicle`）請玩法 PM 看一下；每個角色一行可能很長（全列事件與配方）。
4. 紙娃娃「跟著種族的部件」清單（5F5c-8）是否正確。
5. `enemy_only` 與 5F-3b 技能的 `enemy_only` 同名、分屬狀態與技能兩種資料；要不要統一說明在 06／19 號文件。
