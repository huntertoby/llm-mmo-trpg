# Phase 6C-1b 完成報告：看得見的敵人：規則收尾

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 1 節 6C-1b 列、0.4；`docs/design/21-探索地圖與城鎮.md` 21.10 第 8～12 條（03d10f5b）；`Phase6C-1報告.md` 第 6、8 節；`Phase6C-3報告.md` 待決 5。
> 沒有改引擎（`src/trpg/engine/`）。地圖檔只加了 `personal`、`day_phase` 欄位，沒有改座標；沒有碰餘燼集與荒原室內圖。

## 1. 交付內容

| 項目 | 檔案 |
|---|---|
| 進圖寬限 | `world/field_enemies.py` 的 `arrive_watch`：只開始這一趟，抵達格不檢查 |
| 每隊清空 | `world/field_enemies.py`：`SHARED_CLEAR_KINDS`、`shared_clear`、`with_defeated_spawn`、`after_fight`（改成回傳世界）、`_shown`（哪些隊伍出現）；`world/state.py`：`DefeatedSpawn`、`WorldState.defeated_spawns`、`spawn_defeated`；`world/battle.py`：`_won` 對地圖上的接觸不再整個地點寫「已清空」；`world/step.py`：接上新的 `after_fight` |
| `personal`、`day_phase` 欄位 | `content/fields.py` 的 `FieldSpawn`（選填，預設 `False`／`None`） |
| 內容 | `content/world/fields/cloud_ridge/ferry_steps.yaml`、`bamboo_path.yaml`、`rain_terraces.yaml`、`ashen_waste/ash_well_village.yaml`、`iron_forge_village.yaml`、`red_sand_village.yaml`：只加欄位 |
| 存檔格式 | `world/state.py`：`WORLD_FORMAT` `trpg-world/1` → `/2`（`LEGACY_WORLD_FORMATS`）；`world/save.py`：`WLOG_FORMAT` `/3` → `/4` |
| 季末重置政策 | `server/season_policy.py`：`defeated_spawns` 歸為數值類（同 `cleared`）。不在本段列的可動範圍，但 `WorldState` 每個欄位都要分類，只加一行 |
| 測試 | 新檔 `tests/world/test_field_enemies_6c1b.py`（24 項）、`tests/content/test_field_spawn_flags.py`（8 項）；`tests/world/test_save.py` 加 2 項；既有測試調整見第 4 節 |

## 2. 規則怎麼落實

**1. 進圖寬限**（21.10 第 8 條）
- 走出口或門抵達新地圖：抵達格不檢查視野與相鄰（6C-1 是一到就檢查）。
- 從玩家走的第一步開始照舊檢查（你走一格 → 檢查 → 敵人走一格 → 再檢查）。站著不動時巡邏也不會走過來（巡邏只在你走路時推進）。

**2. 每隊清空**（21.10 第 9 條）
- 適用的地點種類：營地、精英巢穴、遺跡、祭壇（`SHARED_CLEAR_KINDS`），加上規則 `battle.clear_kinds` 列的種類（目前只有 `camp`）。
- 打贏一隊：寫進世界的 `defeated_spawns`（區域、地點、`spawns` 索引、重生時間），所有人都看到那一隊消失；重生時間＝打贏的時刻 ＋ `battle.respawn_seconds`（同營地）。
- 這張圖**現在會出現的**共享隊伍都打完：地點寫「已清空」（`LocationClearedEvent`），重生時間＝最後一隊打贏的時刻 ＋ `respawn_seconds`；同一張圖已記錄的隊伍重生時間都改成和地點一樣，所以整張圖一起重生。
- 地點「已清空」時，共享的隊伍都不出現（`personal` 的照樣在，見下）。
- 其他種類（村落、秘境、異象、商隊、Boss）照 6C-1：打贏的那一隊只在這一趟消失（角色的 `field_visit.defeated`）。
- 不是從地圖上碰到的遭遇（沒有地圖的地點擲到的、事件開的戰）照舊：營地打贏就整個地點寫「已清空」。

**3. `personal`**（21.10 第 9 條）
- 打贏只記在角色這一趟的 `defeated`，世界不寫，不算進「所有隊都打完」。
- 地點「已清空」（別人清的）時照樣出現，所以新手任務的固定戰不會被別人清掉。
- 下一趟（離開這個地點再進來）重新出現；進出室內不算離開。
- 內容：新手任務 1～3 的固定戰（渡口石階 `bandit_raiders`、竹林小徑 `mist_wolf_pack`、雨中梯田 `terrace_clash`），三村落的守點戰（灰井村 `village_raid_mid`、鐵爐村 `village_raid_heavy`、赤沙村 `village_raid_light`）。

**4. `day_phase`**（21.10 第 11 條）
- 選填 `day` / `night`（寫法同事件骨架），沒寫全天；照 `clock.day_phase(now)` 判斷，畫面與碰撞都看當下的時段。
- 內容：渡口石階的石階巡邏 `bandit_shield_line`（6C-3 草稿標「夜晚」的那一隊）加 `day_phase: night`。

## 3. 抵達格離駐守點不到 3 格的地圖（只報告，沒有改座標）

用暫存腳本對正式內容算每個出口每一格、每扇門的抵達格（`field.arrival`），和每一隊的曼哈頓距離（巡邏取路線上最近的一格）。**駐守點**不到 3 格的只有 1 處；巡邏路線的一併列出供參考。

| 地圖 | 抵達格 | 從哪裡進來 | 隊伍 | 種類 | 距離 |
|---|---|---|---|---|---|
| 灰井村 | (12, 16) | 出口 `to_ash_mire` | `village_raid_mid`（駐守 (12, 15)，`personal`） | 駐守 | 1 |
| 灰井村 | (11, 16) | 出口 `to_ash_mire` | 同上 | 駐守 | 2 |
| 熔岩洞窟 | (22, 9) | 出口 `to_horned_altar` | `beetle_line` | 巡邏路線 | 2 |
| 舊鐵哨站 | (11, 16)、(12, 16) | 出口 `to_ember_market` | `scavenger_beasts` | 巡邏路線 | 1 |
| 焦土外圍 | (22, 15) | 出口 `to_red_sand_village` | `hound_pack` | 巡邏路線 | 2 |
| 焦油坑 | (4, 16) | 出口 `to_cooling_well` | `lizard_brood` | 巡邏路線 | 2 |
| 竹林小徑 | (1, 5)／(1, 4) | 出口 `to_hunter_hut` | `bandit_wolf_handler` | 巡邏路線 | 1／2 |
| 竹林小徑 | (9, 10)／(10, 10) | 出口 `to_ferry_steps` | `bandit_wolf_handler` | 巡邏路線 | 1／2 |
| 斷崖幫寨 | (20, 1) | 出口 `to_herb_valley` | `cliff_gang_hounds` | 巡邏路線 | 2 |
| 獵戶小屋 | (11, 1)、(12, 1) | 出口 `to_winter_lake` | `hunter_beasts` | 巡邏路線 | 2 |
| 雨中梯田 | (1, 9) | 出口 `to_bamboo_path` | `sect_patrol` | 巡邏路線 | 2 |

有進圖寬限後，這些位置不會「一到就開打」，但走第一步就可能被看到。灰井村的守點駐守就在村口出口內側。

## 4. 存檔格式與既有測試

- `trpg-world/1` → `/2`：只多了選填欄位 `defeated_spawns`，舊檔照讀、讀進來就是 `/2`（同 6B-2 處理 `trpg-char/1`）。
- `trpg-wlog/3` → `/4`：進圖寬限、每隊清空、`personal`、`day_phase` 讓舊紀錄重播結果不同，`/3` 照讀、標成「規則已變、不能重播」，寫回時標頭換成 `/4`（同 6C-1 處理 `/2`）。
- `trpg-char/3` 不變（`personal` 用既有的 `field_visit.defeated`）。
- 既有測試的調整：`test_save.py`、`test_field.py` 的版號字串；`test_bad_format_rejected` 的「不認得的世界格式」改用 `trpg-world/9`；`test_field_enemies.py` 的 `after_fight` 改新簽名（村落：世界不變、只記在這一趟）。`tests/bot/test_announcer.py` 用 `trpg-world/1` 的資料照樣讀得進來，沒有改。

## 5. 測試與檢查結果

（見第 7 節）

新的測試（表格測試涵蓋 1～4）：
- 進圖寬限：抵達格和駐守相鄰也不開打，走開再走回來才開打。
- 哪些地點種類共享清空（7 種地點的表格）：共享的寫世界、不共享的寫這一趟，都只消失打贏的那一隊。
- 全部打完寫「已清空」、每隊重生時間對齊地點、別的角色也看不到、到時間一起重生；打一隊時別人也看到它消失、到時間重生；打輸什麼都不變。
- `personal` 表格：打個人的只記自己、不算進共享；打完唯一的共享隊伍就已清空、個人的照樣在；別人照樣看得到個人的駐守；下一趟回來又出現。
- `day_phase` 表格（沒寫／夜晚／白天 × 白天／夜晚）；白天清空不等夜晚的隊伍；不認得的時段報錯。
- 重播：從霧渡鎮走出口進渡口石階（寬限）、走到駐守旁開打、打贏一隊（不寫已清空），重播兩次角色與世界一致。
- 內容：7 隊標記正確，其他隊伍都不標。
- 存檔：`trpg-world/1` 升版、`trpg-wlog/3` 不能重播、`defeated_spawns` 排序驗證。

## 6. 待 PM 決定（都已照最保守的做法做完）

**規則類**

1. **「所有隊都打完」算不算不在時段的隊伍**：我只算**現在會出現的**共享隊伍。白天打完白天的隊伍就寫「已清空」，夜晚才出現的那一隊不用打；清空期間夜晚那一隊也不出現。若要求日夜兩邊都打完才算，白天就永遠清不完有夜巡的營地（渡口石階）。
2. **已清空時 `personal` 照樣出現**：別人清了營地，個人的固定戰還在（讓新手任務不被別人清掉）。所以「已清空」的營地上可能還站著一隊（只對還沒打的人）。
3. **營地紮營**：`camp_problem` 照舊看地點「已清空」；`personal` 的隊伍還在也可以紮營（雨中梯田、渡口石階、竹林小徑）。
4. **只有 `personal` 的地圖**（三村落）：村落不是共享清空的種類，本來就不會寫「已清空」。
5. **共享清空的種類寫在程式**：`SHARED_CLEAR_KINDS`（營地、精英巢穴、遺跡、祭壇）加上 `battle.clear_kinds`。規則檔 `content/world/rules.yaml` 的 `clear_kinds` 仍是 `[camp]`（本段不能改）。建議之後把 `clear_kinds` 改成 `[camp, elite_lair, ruin, altar]`、拿掉程式裡的常數（行為不變）。現在的寫法下，沒有實地地圖時擲到的遭遇只有營地會寫「已清空」（同 6C-1 以前）。
6. **新手任務完成後**：`personal` 的固定戰在任務完成後下一趟回來仍會出現（21.10「下一趟回來會重新出現」照字面）。如果任務完成後就不該再出現，要加條件（例如任務旗標）。
7. **重生時間對齊**：先打贏的隊伍原本會比較早重生；地點寫「已清空」時，我把同一張圖所有隊的重生時間都改成和地點一樣（整張圖一起回來）。還沒全打完時，各隊照自己打贏的時刻 ＋ 1800 秒重生。

**數值／解讀類**

8. 夜晚巡邏只標了渡口石階的 `bandit_shield_line`。燈籠事件點 `lantern_patrol`（夜晚）是事件點，不是 `spawns`，沒有動。

## 7. 測試結果（交件前）

- `UV_NO_SYNC=1 uv run pytest -q tests/world tests/api tests/content -n 8 -x`：3909 通過、1 skip（4 分 12 秒）。
- `tests/server tests/bot tests/test_architecture.py`（因為改了 `season_policy.py` 與世界格式）：156 通過。
- `ruff check .`、`ruff format --check .`、`mypy src`（506 檔含新測試）、`lint-imports`（13 kept）：通過。
- `uv run trpg content check`：通過（雲嶺 18／18、灰燼荒原 18／18）。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。
- 沒有跑全量（守則 11）。沒有新增 `# noqa`；`after_fight` 的 `action`、`events`、`now` 改成只能用關鍵字傳，避開 PLR0917。
