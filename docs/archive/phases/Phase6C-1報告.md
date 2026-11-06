# Phase 6C-1 完成報告：看得見的敵人、巡邏、碰到開打

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 0.4（Q4、Q5、Q8）、第 1 節 6C-1 列、第 3、4 節；`docs/design/21-探索地圖與城鎮.md` 21.4、21.9 第 6、7、12 條、21.10；`Phase6B-2報告.md`、`Phase6C-3報告.md`、`Phase6C-4報告.md`。
> 沒有改引擎（`src/trpg/engine/`），沒有改 `content/` 地圖。就地切 12×12 是 6C-2，這段開戰仍用地點原本的戰鬥地圖選法。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| 敵人、巡邏、視野、接觸 | 新檔 `world/field_enemies.py`：`visit_for`／`with_visit`（這一趟）、`spawn_route`／`spawn_place`（巡邏）、`sight_cells`（視野）、`contact_of`（接觸與先手）、`field_enemies`、`enemy_lineup`、走路鉤子 `walk_watch`／`arrive_watch`、戰後 `after_fight` |
| 狀態 | `world/state.py`：`FieldVisit`（這一趟：種子、步數、打贏的隊伍、進圖時站的格子）、`FieldContact`（接觸：哪一隊、陣容種子、接觸點、先手、撤退格）；`CharacterState.field_visit`、`EncounterResult.contact`；`CHAR_FORMAT` 升成 `trpg-char/3` |
| 亂數串流 | `world/rng.py`：`STREAM_FIELD = "field"`（每進一個有敵人的地點抽 1 次） |
| 走路接上 | `world/field.py`：`walk` 改收 `FieldHooks`（`travel`、`watch`、`arrive`；避免 `field` ↔ `field_enemies` 循環匯入）；`field_actions.py` 的 `StopReason` 加 `enemy` |
| 世界動作 | `world/step.py`：鉤子表 `_HOOKS`；每個動作之後 `with_visit`、`after_fight`；`_travel` 目的地有實地地圖時遇敵機率 0（擲骰照擲） |
| 陣容與先手 | `world/encounters.py`：`roll_lineup` 有 `contact` 時用那一隊的 `group` 與 `lineup_seed`；`world/battle.py`：`first_team` 把接觸的先手算進去 |
| 撤退 | `world/town.py`：`retreat` 對接觸的遭遇留在原地點、站回進圖時的格子 |
| 存檔與日誌 | `world/save.py`：`WLOG_FORMAT` 升成 `trpg-wlog/3`（`/2` 照讀、標成規則已變） |
| 季末重置政策 | `server/season_policy.py`：`field_visit` 歸為數值類（同 `field`） |
| API | `api/world_field_schemas.py`：`FieldEnemyView`、`FieldEnemyUnitView`，`FieldView.enemies`；`api/world_field_view.py`：`field_view(..., world=, now=)` 帶出敵人；`api/world_presenter.py` 傳入 |
| OpenAPI | `client/openapi.json`、`client/src/api/schema.d.ts` 重產 |
| 前端 | 只改 `client/src/world/fieldModel.ts`：敵群畫成敵方單位（紙娃娃，範本＝陣容第一名、朝向照伺服器）、視野格淡紅（`#e04a3a` 的環境預告框）、精英格多一個「精」、滑過敵群顯示陣容一行、滑過視野格顯示「敵人的視野」。`WorldScreen.tsx`、HUD 沒動 |
| 測試 | 新檔 `tests/world/test_field_enemies.py`（38 項）；`client/src/world/fieldModel.test.ts` 加 4 項；既有測試的版號與兩個 fixture 調整（第 4 節） |

## 2. 規則怎麼落實

**地圖上的敵人**
- 室外圖的每個 `spawns` 是一隊。陣容照 `group`；遭遇變化（線頭到期）、懸賞照現行 `roll_lineup` 優先。
- 陣容的亂數改用 `lineup_seed`（由這一趟的種子與隊伍索引衍生），所以地圖上顯示的陣容就是開戰的陣容（測試鎖住）。營地混精英、遭遇加人照舊在開戰時套用；情境判定的增援不顯示在地圖上。
- 駐守：站在 `at` 不動，朝向照種子（四方向之一）。
- 巡邏：路線從 `at` 起，沿 `patrol` 各點之間的直線（先走 x 再走 y）展開成格子，來回走；起點照種子，面向下一格。你走一格它走一格（`WalkAction` 每一步推進），不追擊。
- **這一趟**（`FieldVisit`）：進入一個有敵人的地點時，從 `field` 串流抽一次種子；換地點才重來，進出室內不重來。所在地點沒有敵人或沒有實地地圖時是 `None`（不抽亂數）。
- 清空：地點 `is_cleared` 時整張圖的敵人消失，`respawn_at` 到了就回來（同一趟的陣容與位置照舊）。

**視野**（21.10 第 3 條）
- 前方扇形：往前 ≥ 1 格、橫向偏移 ≤ 往前格數（90°）、曼哈頓距離 ≤ 4，空地上共 12 格。
- 遮擋同戰鬥的視線規則：牆（地形 `blocks_sight`）、`blocks_sight` 物件（石柱等）、`blocks_sight` 表面擋住；中間格子的高度 ≥ 兩端最高 ＋ 1 也擋；兩個方向都畫 Bresenham 線。草叢（`conceal`）不擋。
- 只算站得上去的格子（玩家只會站在這種格子上）。

**開打與先手**（21.10 第 3、4 條）
- 每一步：你走一格 → 檢查 → 敵人走一格 → 再檢查。碰到就停在那一格（`walked.stopped == "enemy"`，後面的路徑不走），產生 `pending_encounter`（`make_encounter`，`battle` 串流照舊）並記下 `contact`。
- 碰到的定義：站在某隊的視野格裡，或和它四方向相鄰（含同一格）。同時碰到好幾隊時取 `spawns` 順序的第一隊。
- 先手：被看到（在視野內或正前方相鄰）＝敵方先手；在視野外、站在敵人背後（往前 < 0）＝我方先手；站在側面相鄰＝照現行先攻。
- 踩上出口或門的那一格只檢查一次（人已經離開，敵人不再走）；被看到就不離開。
- 走出口或門換到另一張圖之後，一到就檢查一次（敵人還沒走）。

**走出口時的遇敵擲骰**（21.9 第 7 條）
- 目的地有實地地圖：遇敵機率改成 0，擲骰照擲（亂數消耗不變，`EncounterCheckEvent` 照出、機率 0）。事件、機遇提示、感知判定照舊。
- 目的地沒有實地地圖：照舊擲遇敵。

**戰後回到哪**（21.10 第 7 條）
- 打贏：站在接觸點（走路就停在那一格，戰鬥不改位置）。
- 撤退：留在這個地點，站回這一趟進地圖時站的格子（`FieldVisit.arrived`，舊存檔或傳送進來的就是當時的位置或 `entry`）。
- 全滅：照現行回本區小鎮。
- 非營地的地點（不寫「已清空」）打贏的那一隊記進 `defeated`，到離開這個地點前不再出現。

**確定性與重播**
- 種子：`Rng(derive_seed(season_seed, character_id, "field", counter)).next_u32()`；每隊的陣容與巡邏再用 `fnv1a64(f"{seed}:{index}:lineup"|":patrol")`。不用 `set` 迭代順序與內建 `hash()`。
- 畫面只算不寫（`visit_for` 讀計數但不加），之後的動作抽到的就是同一個種子。
- 重播測試：走進巡邏視野開戰再撤退、繞背我方先手開戰並打贏（營地寫「已清空」、敵人消失），各重播兩次，角色逐字相同、世界相同。

## 3. API

`WorldView.field.enemies[]`：`id`（`e<索引>`）、`x`、`y`、`facing`、`patrol`、`group`、`name_zh`（陣容名稱）、`elite`、`units[]`（`unit`、`name_zh`、`affix`、`elite`、`third`）、`sight[]`（視野格）。室內、已清空、打贏的不給。

## 4. 存檔格式與既有測試

- `trpg-char/2` → `trpg-char/3`：只多了選填欄位，舊檔照讀。
- `trpg-wlog/2` → `trpg-wlog/3`：有實地地圖的地點不再擲遇敵，舊紀錄重播結果會不同，所以 `/2` 比照 6B-2 處理 `/1` 的方式：照讀、標成「規則已變、不能重播」，寫回時標頭換成 `/3`。
- 既有測試的調整：
  - 版號字串（`test_save.py`、`test_field.py`、`test_world_field_api.py`、`test_opportunity_hints.py`）。
  - `tests/world/test_field.py`：`calm_field`、`ambush_field` 拿掉所有 `spawns`（測的是 6B-2 的走路，不讓巡邏擋路）；`ambush_field` 另外拿掉渡口石階的地圖，讓它照舊每步遇敵（原本靠「出口換圖擲遇敵」測撤退與重播，現在有地圖的地點不擲）。測試的意思不變。

## 5. 測試與檢查結果

- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content tests/server tests/test_architecture.py -n 8`：3828 通過、1 skip。
- `tests/world/test_field_enemies.py` 38 項：扇形邊界（12 格表格）、牆／石柱／高低差遮擋、草叢不擋、接觸與先手表格、走進視野開打、繞背先手、地圖陣容＝開戰陣容、撤退回入口、清空消失與重生、非營地打贏的那一隊消失、換地點重來、巡邏路線與來回、巡邏一步一步走、巡邏走過來看到你、有地圖的出口不擲遇敵、沒地圖的照舊擲、`travel` 進有地圖的地點不擲、兩個重播測試。
- 前端：`vitest run src/world` 15 檔 116 項通過；`tsc --noEmit` 通過。
- `ruff check .`、`ruff format --check .`、`mypy src`（501 檔）、`lint-imports`（13 kept）都通過。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。

**新增的 `# noqa`**（守則 12）：
- `world/field_enemies.py` 的 `_start`、`walk_watch` 各一個 `# noqa: PLR0917`：`walk_watch` 要和 `field.WatchFn` 同簽名（世界動作的 `library`、`world`、`char` 加地圖、走路事件、時間）；`_start` 要接觸的全部資料。複雜度（C901／PLR0912／0915）沒有新增 noqa。

## 6. 待 PM 決定（都已照最保守的做法做完）

**規則類**

1. **一進圖就被看到**：走出口或門到另一張圖時，抵達格已經在視野內或相鄰就馬上開打（敵方先手）。正式內容有幾張圖的抵達格離巡邏路線或駐守很近，視朝向可能一到就開打（第 8 節列表）。如果想給「進圖的第一步不算」的寬限，要改規則。
2. **側面相鄰**：Q5 寫「背後 180°」，我把「往前 < 0」算背後、「往前 = 0」（正側面）算「其他，照現行先攻」。
3. **先手和其他來源一起算**：接觸的先手和既有的「暗門線頭＝我方先手」「增援滿了＝敵方先手」用同一條「兩邊都有就抵銷」。例：持有暗門線頭卻被看到 → 抵銷、照現行先攻。
4. **非營地地點打贏的那一隊**：只有營地會寫「已清空」（`clear_kinds: [camp]`）。村落、遺跡、祭壇、精英巢穴、秘境、異象打贏的那一隊只在這一趟消失，離開再回來就又在。要不要比照營地寫「已清空」（或另訂重生時間）請決定。
5. **營地清空是整張圖**：「已清空」是地點層級，打贏一隊（例如駐守）同一張圖的巡邏也一起消失。
6. **懸賞與遭遇變化優先**：地點有懸賞或線頭到期變化時，那張圖上每一隊顯示並開打的都是懸賞／變化陣容（照現行 `roll_lineup` 的順序）。
7. **夜晚巡邏一律出現**：`spawns` 與遭遇表都沒有日夜欄位（`surges.day_phase` 只用來加人），所以渡口石階「夜晚多一隊」等草稿的日夜條件沒有接，巡邏日夜都在。要分日夜需要在 `spawns` 加欄位（內容 PM 改地圖）。
8. **只有走路會被看到**：`travel`（從沒有地圖的地點過來）、傳送石、`teleport`、撤退、全滅回城抵達時不檢查視野，下一步走路才檢查。
9. **新手任務的固定戰**（6C-3 待決 5）：「任務完成前不會被別人清掉」沒有做；「已清空」是世界共用的。
10. **踩上出口時先看敵人**：出口格在視野內時先開打、不離開；打完站在出口格上，要再走一步才換圖。

**數值／解讀類**

11. 扇形的形狀：曼哈頓距離 ≤ 4、90°（空地 12 格）；遮擋照戰鬥的視線規則（含高低差）。
12. 駐守的朝向、巡邏的起點照種子；巡邏面向下一格。
13. 同時碰到好幾隊取 `spawns` 順序的第一隊（其他隊不加入這一場）。
14. 地圖上顯示的陣容以畫面當下的時段、世界旗標算；開打的那一刻如果剛好換時段，開戰陣容的「遭遇加人」會照開打的時刻（開打時重算）。
15. 「這一趟」只在有 `spawns` 的室外圖建立，所以城鎮等沒有敵人的地點不抽 `field` 串流。

## 7. 測試結果（交件前）

- 相關 pytest（world、api、content、server、architecture）：3828 通過、1 skip（7 分 6 秒）。
- vitest `src/world` 116 項、`tsc --noEmit`、ruff、format、mypy、lint-imports、swamp 種子 7 重播：全部通過。
- 沒有跑全量（守則 11）。

## 8. 內容檢查（spawns，只報告、沒有改地圖）

用暫存腳本對正式內容的 25 個 spawns 檢查：陣容都在該地點的遭遇表、巡邏路線每格都站得上去而且連續，沒有錯。以下抵達格（出口內側一格或 `entry`）在某個朝向下會落在敵人視野裡或和巡邏路線相鄰，視種子可能一進圖就開打（待決 1）：

| 地圖 | 隊伍 | 可能一到就開打的抵達格 |
|---|---|---|
| 竹林小徑 | 巡邏 `bandit_wolf_handler` | (1, 4)、(1, 5)、(9, 10)、(10, 9)、(10, 10) |
| 斷崖幫寨 | 巡邏 `cliff_gang_hounds` | (20, 1)、(21, 1) |
| 雲海吊橋 | 駐守 `sword_array`（北橋頭） | (11, 1)、(12, 1) |
| 鶴歸崖 | 駐守 `crane_cliff_bear` | (7, 11)、(7, 12) |
| 渡口石階 | 巡邏 `bandit_shield_line` | (1, 8)、(1, 9)、(2, 8)（從霧渡鎮進來的位置） |
| 藥師谷 | 巡邏 `valley_beasts` | (3, 16)、(4, 16)、(7, 12) |
| 獵戶小屋 | 巡邏 `hunter_beasts` | (11, 1)、(12, 1) |
| 雨中梯田 | 巡邏 `sect_patrol` | (1, 9)、(1, 10) |
