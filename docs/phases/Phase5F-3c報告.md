# Phase 5F-3c 完成報告：5F-3b 收尾（碎晶之主重測、稱號顯示、近似清單、改種族保留紙娃娃）

範圍：`docs/phases/Phase5計畫.md` 第 1 節 5F-3c 列；背景 `Phase5F-3b報告.md`、`docs/design/19-灰燼荒原與賽季主線.md` 19.7（5F-3b 代決）。開發 PM 中途追加一項（玩法 PM 2026-11-03 代決）：改種族時紙娃娃五項部件的保留規則。

## 交付

| # | 項目 | 位置 |
|---|---|---|
| 1 | 碎晶之主重測（灌注 ×0.75、界崩第 15 輪；main 50c939a6 的 content，沒有再改數值） | 見下節；工具 `scripts/season_boss_diagnose.py --seeds 80` |
| 2 | 稱號「碎晶的終結者」的 API：`AccountRecord.title_labels()`（`AccountView.titles` 改用它，文字不變）、`AccountStore.titles_of(account_id)`；`WorldStore.account_titles`（`create_app` 接上）、`titles_of_account`／`titles_of_character`（角色→帳號→稱號；沒有帳號＝空）。新欄位（都有預設空值）：`ShadowView.titles`（名片）、`BoardBossEntryView.titles`、`BoardSeasonBossView.first_kill_titles`（評分榜、首殺）、`ChronicleHeroView／ChronicleKillView／ChronicleRankView／ChronicleBoardView.titles`（編年史）。view 函式多一個 `titles` 參數（預設不顯示），路由傳 `store.titles_of_character`；編年史用 `ChronicleTitles`（角色 ID 或帳號 ID 查：上季角色有帳號就照帳號、循環賽排名照帳號）。`client/openapi.json`、`schema.d.ts` 重產 | `src/trpg/server/accounts.py`、`src/trpg/api/account_schemas.py`（`TitlesOf`、`no_titles`）、`world.py`、`app.py`、`auth.py`、`world_party_schemas.py`、`world_party_view.py`、`world_presenter.py`、`season_schemas.py`、`season_boss_view.py`、`season_view.py`、`chronicle_schemas.py`、`routes/world.py` |
| 3 | 前端：共用元件 `AccountTitles`（名字後接「「碎晶的終結者（s1）」」，沒有稱號不畫）用在三處——雇用清單的影子（城裡看朋友 build 的地方，現在沒有獨立名片畫面）、公告板的首殺與通關評分榜、編年史（上季角色、首殺、評分榜、循環賽排名）。編年史評分榜原本就印「這次通關的稱號」`title_zh`：帳號有稱號時改印帳號稱號，沒有時照舊（避免同一個稱號印兩次）。戰鬥畫面沒有動 | `client/src/ui/AccountTitles.tsx`、`ui/titleLabel.ts`（＋測試）、`world/PartyPanel.tsx`、`BoardPanel.tsx`、`ChroniclePanel.tsx`、`styles/world.css` |
| 4 | 近似清單寫清楚實際做法（碎界脈動的觸發與數值、晶傀儡的召喚次數與觸發）並附 160 場實測 | `docs/phases/Phase5F-3b報告.md`「近似清單的實際做法」 |
| 5 | 改種族時沿用上季紙娃娃（開發 PM 追加）：原本 5F-5c 是膚色、髮型、髮色、眼睛、骨架五項**一律**改回新角色範本的預設；改成每一項「目前的值新種族也有就保留，沒有才改回預設」 | `src/trpg/server/chronicle.py`（`legacy_doll` 多 `race_look`）、`src/trpg/api/world.py`（傳新種族的 `races.yaml` `look`）、`tests/server/test_legacy_doll.py` |
| 6 | 測試 | `tests/api/test_title_display.py`（新：帳號稱號查詢、真實 API 的影子名片在掛帳號＋稱號前後、評分榜與首殺、編年史四種列）、`tests/server/test_legacy_doll.py`（+2）、vitest `titleLabel.test.ts`，夾具 `boardBoss.test.ts`、`party.test.ts` 補新欄位 |

## 碎晶之主重測（8 個 build × 80 場＝640 場）

`uv run python scripts/season_boss_diagnose.py --seeds 80`（同 5F-3b 的方法：`prepare_battle` → 效用 AI 雙方）。合併 main 後 5A-ART 只加了外觀 `doll`（不進結算），沒有重跑。

| build | 勝率 | 平均輪數 | 柱子全倒輪 | 敗場停在 |
|---|---|---|---|---|
| striker | 51% | 17.0 | 8.7 | 碎界脈動 16、三柱 14、界崩 9 |
| fire | 57% | 15.7 | 5.3 | 碎界脈動 11、界崩 11、三柱 10、核心過載 2 |
| storm | 75% | 15.0 | 5.3 | 界崩 8、碎界脈動 6、三柱 5、核心過載 1 |
| ranged | 78% | 13.2 | 5.3 | 界崩 8、碎界脈動 6、核心過載 3 |
| tank | 80% | 11.8 | 5.1 | 核心過載 5、碎界脈動 5、界崩 4、三柱 2 |
| guardian | 90% | 11.8 | 5.3 | 碎界脈動 3、三柱 3、核心過載 1、界崩 1 |
| healer | 92% | 8.5 | 3.1 | 核心過載 6 |
| trapper | **41%** | 19.3 | 9.8 | 三柱 19、界崩 18、碎界脈動 9、核心過載 1 |
| **全部** | **70%** | **14.1** | 5.8 | 界崩 59、碎界脈動 56、三柱 53、核心過載 19 |

結論：**整體 70%、每個 build ≥ 40%（最低 trapper 41%）、平均 14.1 輪（10～15）全部達標**，和 5F-3b 候選表「灌注 ×0.75（界崩 15）」那一列（51%／41%／70%／14.1）逐項相同。敗場的主要傷害仍是本體「聚雷」（58%）。

注意：達標是「平均輪數」；個別 build 的平均輪數 trapper 19.3、striker 17.0、fire 15.7 超過 15，healer 8.5 低於 10。trapper 41% 離 40% 只有 1 個百分點（80 場的標準誤約 ±5.5%）。沒有改數值。

## 改種族時的紙娃娃（追加項）

- 查證：5F-5c 的 `legacy_doll` 在種族改了時，`RACE_DOLL_FIELDS`（膚色 `skin`、髮型 `hair`、髮色 `hair_color`、眼睛 `eyes`、骨架 `skull`）**五項一律**換成新角色範本的預設——和代決不同，已改。
- 現在：每一項，目前的值「新種族也有」就保留，否則換成新角色範本的預設。「新種族也有」＝等於新角色範本的預設值，或等於新種族外觀（`races.yaml` 的 `look`）同名欄位的值；`skull` 種族外觀沒有這個欄位，只比範本。種族沒改時整個原樣；範本沒有紙娃娃時整個用預設（同 5F-5c）。裝備、褲子、飾邊等不跟種族的部件不變。

## 檢查結果

（合併 main＝`e79a7e2f`〔含 5A-ART〕之後跑）

- `ruff check .`、`ruff format --check .`、`mypy`（strict，1220 檔）、`lint-imports`（13 kept）：通過。
- pytest `-n 8` tests/world、api、server、content、test_architecture：3401 通過、0 失敗。
- vitest：1335 通過（144 檔）；`pnpm build`（含 `tsc --noEmit`）通過。
- 重播：swamp 種子 7 通過（88 動作、313 事件，和之前相同）。
- OpenAPI：合併後重產，沒有差異。
- 瀏覽器（8270 埠、自己的分頁；用暫存資料夾真的打倒碎晶之主拿到稱號、存影子，另一個角色來看）：800×600 與 1600×900 下，雇用清單的影子「阿霧的影子「碎晶的終結者（s1）」」、公告板首殺與通關評分榜、編年史的首殺與評分榜都顯示稱號；兩種尺寸在角色列表＋編年史、公告板、雇用清單各跑一次 `__layoutSmoke.scan()`，都回 `[]`。戰鬥畫面沒有改動。預覽伺服器已關。
- 沒跑全量、matrix、completion。

## 待 PM 決定

1. **「新種族也有」的判斷**：種族目前每一項外觀只有一個值、沒有可選清單，所以照最保守的解讀：等於新角色範本的預設或新種族 `look` 的同名值才算「有」。之後若種族有可選的膚色／髮型清單，要改成比清單。
2. **編年史裡的稱號是「帳號目前的稱號」**：稱號是帳號層級、季末保留，所以舊季的列也會顯示之後拿到的稱號（例：第一季的列也顯示「碎晶的終結者（s2）」）。若要只顯示那一季拿到的，要依 `AccountTitle.season_id` 過濾。
3. **顯示範圍**：照 19.7 的三處做；另外把編年史的循環賽排名也帶上（同在編年史裡）。主城的影子循環賽排行榜（`LeagueView`）、首位發現的配方、上季角色列表（建角沿用）沒有加。
4. 名片目前是雇用清單裡影子那一列（城裡沒有獨立的玩家名片畫面）；之後做名片畫面時直接用 `ShadowView.titles` 與 `AccountTitles` 元件。
5. 個別 build 的平均輪數有 4 個在 10～15 之外（見上），整體平均達標；要不要以各 build 為準由 PM 決定。
