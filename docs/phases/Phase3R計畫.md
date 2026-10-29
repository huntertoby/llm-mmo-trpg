# Phase 3R｜可玩種族與出身（玩法決定 #61）

> 使用者原話：「純外觀不太好」「種族 A、美術乙，好 寫入，開始畫樣張」。設計以 `docs/design/07-角色成長.md` **7.7**（`8977de8`）為準；對不上的地方停下來問 PM（轉玩法 PM），不要自行解釋。
> **排程**：3J 之後、Phase 4 之前（使用者原排程 3I → 3K → 3J → Phase 4 不動；原規劃為 Phase 5 前的創角段，roguelite 提前開放）。美術（美術 PM 樣張「美術乙」）移植在 3R-3，等美術 PM 交樣張與移植需求。

## 1. 段落估計（開發 PM 初估）

| 段 | 內容 | 估計 | 模型 |
|---|---|---|---|
| 3R-1 種族資料與防最佳解驗證 | `content/races.yaml`（10 個人形種族：名稱、1 招種族技、1 項環境被動、預設外觀參數）＋`content/origins.yaml`（碎界五區出身：預設外觀、開場劇情鍵、NPC 態度，**不影響戰鬥**）；pydantic schema；**5 條防最佳解原則寫成驗證規則**：種族技與被動不得給傷害、命中、暴擊、HP、AP、屬性（驗證器擋，中文原因；`trpg content check` 檢查）；種族技 1 AP、每場 1～2 次、不佔技能欄、不加傷害 | 0.4 | sonnet |
| 3R-2 種族技與環境被動結算 | 種族技多數用現有原語；環境被動的小規則：走火不燃燒、站水不導電、看見陷阱、天氣懲罰減半、冰面不滑倒（照 7.7 的確切寫法）；引擎表格測試（每項被動 × 有／無該種族）；卡片與實戰一致；AI 會用種族技（使用條件） | 0.5～0.6 | sonnet |
| 3R-3 開局流程與外觀（外觀部分 **排在 3S 真側面之後**；照 `docs/art/種族與側面移植需求.md` 第 ① 節：`look` 新選填欄位、10 族資料照 `raceArt.js`、龍裔定案版、頭部裝備 `covers` 衝突規則；建議拆 3R-3a 耳／角／尾／膚色／衝突（**另含 3S-3 美術小修**：成對武器遠側的手槍、斧、錘往前上方錯開約 3px）、3R-3b 體型／紋路／鬍子／獠牙／龍裔；種族技特效 0.25 段等玩法定案） | 開局順序改為「種族與出身 → 武器 → 2 關鍵字」（API、前端 `StartPicker`、run 存檔記錄種族與出身，存檔版本相容）；紙娃娃依種族／出身的預設外觀（**美術 PM 樣張到了再做**，照 `docs/art/` 的移植需求）；主城重選種族是大世界功能，**不做**，設計不擋 | 0.3＋美術約 1 | sonnet |

**合計**：玩法約 1～1.2 段＋美術移植約 1 段。

## 2. 受影響的既有功能（初步盤點，流程改善 A）

`roguelite` 開局（`new_keyword_run`、`StartPicker`、`roguelite.yaml` start）、run 存檔格式、`UnitTemplate`（種族欄位、種族技不佔技能欄）、技能列 UI（種族技另列）、紙娃娃 `appearance.ts`／`paperdoll.ts`、地形與天氣規則（燃燒、導電、陷阱可見、天氣、冰面滑倒）、AI 使用條件、戰鬥紀錄（`LOG_FORMAT` 遞增）、模擬 build（預設種族）、CLI `trpg run new`。

## 3. 行為一致測試（必填，流程改善 B）

每個種族：種族技的卡片數值＝實戰結算；每項環境被動有／無種族的表格測試；防最佳解驗證：故意寫一個給傷害／命中／暴擊／HP／AP／屬性的種族資料，載入必須失敗並給中文原因。

## 4. 3R-1 驗收與 3R-2 規格（2026-10-29，開發 PM）

### 4.1 3R-1 驗收
- 報告 `Phase3R-1報告.md`。`content/races.yaml`（10 族）、`content/origins.yaml`（五區出身，無戰鬥欄位）、`trpg.content.races`（`RaceTable`、`OriginTable`、種族技封閉效果清單、被動規則封閉清單）、防最佳解驗證（原則 1、3 機器檢查，中文原因）、`trpg content check` 跨檔檢查；`tests/content/test_races.py` 53 項。合併後 content 1520、架構測試、mypy、相關 CLI 通過。
- 玩法 PM 回覆（07 7.7「實作細節」，`00dc9f33`）：拋錨不吃撞擊、被擋就停；森林＝地圖標籤 `forest`（先加 `dark_forest`，其他依草叢多寡判斷）；獸人＝所有「推」的路徑（含落點）有岩漿或深淵時距離 −1（最少 0），不含拉與傳送；龍裔火抗不衝突；`origins.yaml` 照現狀定案。

### 4.2 3R-2｜種族技與環境被動結算（sonnet；約 0.6 段）
**受影響的既有功能**：引擎（位移：推、拉、投擲物件；表面：燃燒、導電；視線與隱蔽；陷阱可見；天氣懲罰；冰面滑倒；移動花費）、`UnitTemplate`／`UnitState`（種族欄位、種族技次數）、合法動作（種族技不佔技能欄、每場次數）、AI（使用條件）、卡片與 HUD（種族技另列）、地圖資料（`forest` 標籤）、戰鬥紀錄、存檔、`LOG_FORMAT`、模擬 build（預設種族：沒填就是人類或無種族，採保守做法並寫進報告）。
1. 照 07 7.7 表與「實作細節」結算 10 招種族技與 10 項環境被動；3R-1 的封閉效果清單決定對映到現有原語或在引擎實作（照最少新程式的做法，寫進報告）。
2. 種族技：1 AP、每場 1～2 次、不佔技能欄；合法動作、卡片、HUD 另列；AI 依使用條件會用。
3. 地圖標籤 `forest`：`dark_forest` 加上，其他地圖依草叢多寡判斷，報告列出加了哪些。
4. 單位的種族來源：主角（一輪）與 reference build 可指定種族；開局選種族是 3R-3，本段先讓 `trpg battle` 等能指定（例如 build 欄位），沒指定時無種族。
5. 行為一致測試：每項環境被動 × 有／無該種族的引擎表格測試；每招種族技卡片＝實戰；獸人被推 × 路徑上有無岩漿／深淵 × 推的來源（技能、風、衝撞）；拋錨被擋就停、不吃撞擊；重播一致。
6. 驗收：pytest（engine、content、skillgen、narrative、roguelite、api、`-m "slow or not slow" tests/cli --timeout=3000`）、vitest、build、ruff、format、mypy、lint-imports、一場含種族技的重播。報告 `Phase3R-2報告.md`。

### 4.3 3R-2 驗收（2026-10-29，開發 PM）
- 報告 `Phase3R-2報告.md`。動作 `use_race_skill`（推、拉 `PushEffect`、投擲 `HurlObjectEffect`、表面 `CreateSurfaceEffect`；狀態 `race_adapt`、`race_stonewall`；狐火誘餌召喚物 `summon_foxfire_decoy`）；被動集中在 `engine/rules/race.py`；精靈被動改 `sight_bonus_on_map_tag`，`forest` 只加在 `dark_forest`；指定種族：`trpg battle --ally-race／--enemy-race`、`trpg run new|auto --race`、`POST /api/runs` 的 `race`、build `hero.race`；前端種族技按鈕列與 HUD。`LOG_FORMAT` `/83`（與 3J-4b 合併）。合併後全量通過（同 3J 4.15）。
- 玩法 PM 回覆（07 7.7 實作細節 6～10，`9e9876fd`）：#2、#3、#5 照實作；鱗族「水與冰面不花額外點數」→ 專案 PM 問使用者，結果前維持現狀；**#1、#6 → 3R-2b**。

### 4.4 3R-2b｜狐火誘餌修正（sonnet；約 0.15 段）
1. 狐火誘餌照 07 7.7 實作細節：下一次敵方單體攻擊（不論原本打我方誰）在**擲命中之前**轉向誘餌，攻擊落空、誘餌消失，不論會不會命中都算用掉；敵人可以直接打誘餌。表格測試。
2. 戰鬥紀錄：放出時「{施放者} 放出一團狐火誘餌」；攔下時「狐火誘餌引走了 {攻擊者} 的攻擊，隨即消散」。
3. 驗收：pytest（engine、narrative、api、`-m "slow or not slow" tests/cli --timeout=3000`）、ruff、format、mypy、一場含狐火誘餌的重播；改紀錄格式就遞增 `LOG_FORMAT`。報告 `Phase3R-2b報告.md`。

### 4.5 3R-3 拆段（2026-10-29 開發 PM；外觀直接用 C 畫風）
外觀依據：`docs/art/C畫風移植需求.md` 第 5 節（種族）、`docs/art/種族與側面移植需求.md` ①（欄位、10 族資料、龍裔定案版）、`docs/art/可玩種族評估.md` 第 2 節（**衝突規則以它為準**）；部件畫法照 `docs/art/sample/storyDoll.js` 的 `tail`、`ears`、`horns`、`face`。成對武器遠側錯開已在 C-2b 做完。

#### 3R-3a｜開局選種族與出身（sonnet；約 0.3 段）
開局順序改成「種族與出身 → 武器 → 2 關鍵字」：API（沿用 3R-2 的 `POST /api/runs` `race`，加 `origin`）、前端 `StartPicker`（種族卡顯示種族技與被動、出身卡顯示界域與簡介）、run 存檔記錄種族與出身（存檔版本相容：舊存檔沒有就是無種族）、`trpg run new` 選項；主角戰鬥時帶種族。彈出卡片用共用浮動卡（6.5.1）。驗收：pytest（roguelite、api、cli）、vitest、build、排版煙霧檢查、內建瀏覽器走一次開局。報告 `Phase3R-3a報告.md`。

#### 3R-3b｜種族外觀：耳、角、尾、膚色、衝突規則（sonnet；約 0.5 段；可和 3R-3a 平行）
`look` 新選填欄位（照 ① 與 3R-1 的 `races.yaml` 預設外觀，駝峰／底線對照）；`UnitView` 帶出主角的種族外觀；C 畫風四方向的耳、角、尾、膚色；衝突規則（尖耳＋頭盔、獸耳＋兜帽、角＋寬帽、尾巴＋長袍、角魔＋披風背面）；不認得的值退回預設。檢查清單「種族」前半。報告 `Phase3R-3b報告.md`。

#### 3R-3c｜種族外觀：體型、臉部紋路、鬍子、獠牙、龍裔（sonnet；約 0.5 段；3R-3b 後）
`stout`／`tall` 接上資料來源；臉部紋路（鱗片、刺青、晶路）、鬍子、獠牙、豎瞳；龍裔定案版（大龍角、龍鱗、粗龍尾＋背刺、鱗色）。檢查清單「種族」全部打勾。報告 `Phase3R-3c報告.md`。

### 4.6 3R-3a／3b／3c 驗收（2026-10-29，開發 PM）——3R 完成
- **3R-3a**（報告 `Phase3R-3a報告.md`）：`RunState.origin`、`POST /api/runs` 的 `origin`、`start-options` 的 `races`／`origins`、`trpg run new|auto --origin`；存檔 `trpg-run/7`（`/5`、`/6` 可讀）；開局「種族與出身 → 武器 → 2 關鍵字」（前端必選、API／CLI 選填）；`layoutSmoke.runCase(title, {viaRun: true})` 走新開局。待決（種族與出身獨立、出身只記錄、浮動卡 `pinOn: "touch"`）→ 接受。
- **3R-3b**（報告 `Phase3R-3b報告.md`，`inkRace.ts`、`RaceView.look`、`raceLooks.json`）：耳、角、尾、膚色、衝突規則；美術 PM 驗收通過（`docs/art/3R-3b檢查.md`），小修 2 點併入 3R-3c。只有主角帶種族外觀。
- **3R-3c**（報告 `Phase3R-3c報告.md`）：體型、臉部紋路、鬍子、獠牙、豎瞳、龍裔定案版；角魔 `horn_color` `#bfb0a4`、角抬帽時頭髮照不遮頭頂畫（美術 PM 小修）。待美術 PM 驗收。
- 合併後全量（除 llm，含 3R-3a）：pytest 8527、vitest 1097、mypy、lint-imports、build、重播（swamp 種子 12，矮人）全過；3R-3c 合併後 vitest 1103、build、api／content 1826 通過。
- **3R 可玩種族與出身完成**（美術 PM 驗收 3R-3c 後）。

### 4.7 3R-4｜鱗族被動改版（#68，07 7.7，`359c927c`；使用者：「鱗族 A」；sonnet；約 0.15 段）
新規則：自己回合開始時站在水或冰面（看那一格的表面）→ 這回合移動 +1（只加這回合；回合中離開水面不收回）；在冰面上不滑倒（維持）。刪掉原本「水與冰面移動不花額外點數」的半句（`content/races.yaml` 被動規則、卡片句）。表格測試：回合開始站水／冰／一般地面 × 鱗族／非鱗族；回合中離開不收回；冰面不滑倒照舊。驗收：pytest（engine、content、narrative，`-m "(slow or not slow) and not llm"`、`tests/cli --timeout=3000`）、ruff、format、mypy；改紀錄格式就遞增 `LOG_FORMAT`（目前 `/86`）。報告 `Phase3R-4報告.md`。
- **3R-4 驗收**（2026-10-29，開發 PM）：報告 `Phase3R-4報告.md`。規則 `free_move_on` → `surface_move_bonus`（`surfaces`、`amount`），`move_points_for_turn` 依回合開始腳下表面（水、冰；不含水地形，照 #68「看那一格的表面」）；`LOG_FORMAT` `/87`。合併後 ruff、mypy、engine／narrative／content 5573 通過。
