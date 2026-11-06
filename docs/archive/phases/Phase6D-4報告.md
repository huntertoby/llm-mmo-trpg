# Phase 6D-4 報告：主城城鎮圖與室內（內容）

**依據**：
- `docs/phases/Phase6計畫.md` 第 1 節 6D-4 列、第 2 節
- `docs/archive/phases/Phase6D-3報告.md`、`Phase6C-3報告.md`（城鎮與室內的寫法）
- `docs/design/21-探索地圖與城鎮.md` 21.1、21.5、21.10；`docs/design/09` 9.6.1
- 玩法 PM 草稿 `玩法PM-Phase6主城草稿.md`（2026-11-04，未寫入設計文件）

**動了哪些檔案**：
- `content/world/fields/capital/capital.yaml`（新增）：主城 32×24
- `content/world/fields/capital/interiors/capital_mentor_hall.yaml`、`capital_tavern.yaml`、`capital_smithy.yaml`（新增）
- `src/trpg/content/fields.py`：最小擴充 `region: capital`（見第 1 節）
- `tests/content/test_capital_field.py`（新增）；`tests/content/test_fields.py` 的進度斷言加一列主城
- `tests/cli/test_cli.py`：`content check` 進度那一行的正規式加上「、主城 \d／1」（**不在原定可動範圍**，但進度行多了主城就一定要改，只改這一行）

沒有改 `world/`、`api/`、`client/`、`cli/main.py`。開工時 `git merge main` 已是最新。

## 1. schema 擴充：`region: capital`

主城不在任何區域的地點圖裡，現行驗證會因「未知的區域（沒有地點圖）」擋下。最小幅度擴充：

- 常數 `CAPITAL_REGION = "capital"`、`CAPITAL_LOCATION = "capital"`、`CAPITAL_NAME_ZH = "主城"`；`FieldMapDef.is_capital`。
- 寫法：室外圖 `region: capital`、`location: capital`；室內圖 `interior_of: capital`；放在 `world/fields/capital/`（載入器的「資料夾＝region、檔名＝location／id」規則不用改）。
- 主城專屬驗證（錯誤）：
  - `location`／`interior_of` 必須是 `capital`；
  - 沒有出口（`exits` 不可有）；
  - 門只能通往主城的室內圖，並沿用既有的門與室內出口配對檢查；
  - 傳送石恰好 1 個；
  - 室外與室內都不可有 `spawns`、`campfires`；
  - 不可有 `npcs`（主城沒有人設卡，功能型 NPC 用 `facilities`／`situation_objects`）。
- 區域地圖的出口寫 `region: capital` 原本就會報「區域 capital 沒有地點」，等於「不能走進主城」，有測試。
- 主城的傳送石不算進任何區的「每區 2～3 個」。尺寸用既有的 `capital`（28～36 × 20～28）範圍。
- `field_progress` 最後多一列主城（1 張）。`content check` 印出：`實地地圖：雲嶺 18／18、灰燼荒原 18／18、主城 1／1（另有室內圖 7 張）`。

## 2. 主城（`capital`，暫名「樞島」，32×24）

邊緣一圈是雲（深淵）。十字主路：直的 x=9～10、21～22，橫的 y=7～8、15～16。

| 位置 | 建築／設施 | 地圖上的寫法 |
|---|---|---|
| 中央廣場（11～20, 9～14） | 傳送石、公告板、四角源晶燈 | `teleport_stones: stone_capital [15,11]`；`entry [16,11]`（傳送石旁）；`notice_board`（石柱 [17,10]） |
| 北（13～17, 1～4） | 技能導師殿 5×4 | 門 `mentor_hall_door [15,4]` → `capital_mentor_hall` |
| 西（2～5, 9～12） | 酒館 4×4 | 東牆的門 `tavern_door [5,11]` → `capital_tavern` |
| 東（25～28, 10～12） | 鐵匠鋪 4×3（含附魔台） | 西牆的門 `smithy_door [25,11]` → `capital_smithy` |
| 東北（23～30, 1～6） | 封印廣場 | `seal_altar`（石柱 [26,3]）、`rift_projection` [27,5]、`boss_stele`（石柱 [29,2]）、`seal_keeper` [25,3] |
| 西北（1～8, 1～6） | 許願池 | 水表面 2×2；`wishing_pool` [4,3]、`pool_keeper` [6,4] |
| 東南（23～30, 17～22） | 技能工坊靶場 | 木人樁 4 個（crate）；`training_range` [25,19]、`workshop_master` [24,18] |
| 南（11～20, 17～22） | 傭兵營 | 兩頂帳篷（牆）；`hire`（傭兵管事站位 [14,18]）；`shadow_league_desk`（crate [18,17]） |
| 西南（1～8, 17～22） | 整備亭 | 四根石柱的亭子；`loadout_pavilion` [4,19] |

**五座浮橋**：橋面是深淵上的 `wooden_bridge`（2 格寬），伸到地圖邊緣，但不是出口。橋頭石碑是石柱。兩者都寫成 `situation_objects`：`bridge_<區域>`、`stele_<區域>`。

| 方向 | 區域 | 橋面 | 石碑 |
|---|---|---|---|
| 北 | 晶冠城邦 | [9,0]、[10,0] | [11,1] |
| 西 | 雲嶺 | [0,15]、[0,16] | [1,14] |
| 東 | 魔導樞市 | [31,7]、[31,8] | [30,6] |
| 南 | 灰燼荒原 | [15,23]、[16,23] | [17,22] |
| 東南 | 霜潮海境 | [29,23]、[30,23] | [28,22] |

**安全區**：沒有 `spawns`、`campfires`、`event_spots`。主城沒有自己的事件骨架，所以不放事件點。

## 3. 室內圖（各 10×8，南邊門口 [4,7]、[5,7] 回主城，`arrive` 指回那扇門）

| 室內圖 | 設施／站位 |
|---|---|
| `capital_mentor_hall` 技能導師殿 | `mentor`＝殿主站位 [6,2]（講壇前）；`scribe`＝書記站位 [2,2]、`grimoire_shelf` 書架 [2,1] |
| `capital_tavern` 樞島酒館 | `tavern`＝酒館老闆站位 [6,1]（櫃檯後） |
| `capital_smithy` 樞島鐵匠鋪 | `smithy`＝鐵匠站位 [4,2]（鐵砧旁）；`enchanter`＝附魔師站位 [7,3]（附魔台旁） |

## 4. 功能型 NPC 的處理（照草稿第 2 節、待確認 2）

主城的 NPC 都沒有人設卡。`npcs` 欄位要對到人設卡，而且 client 點 NPC 會走「這裡的人」卡片，不是直接開面板，所以**不放進 `npcs`**。每位 NPC 的站位改這樣寫：

- **有現成設施種類的**寫成 `facilities`，走到旁邊就直接開原本的面板，client 現在就能用：
  - 殿主 → `mentor`
  - 酒館老闆 → `tavern`
  - 鐵匠 → `smithy`
  - 附魔師 → `enchanter`
  - 傭兵管事 → `hire`
- **沒有現成種類的**寫成 `situation_objects`，面板接線留給 6D-5：
  - 書記 → `scribe`
  - 守印人 → `seal_keeper`
  - 守池人 → `pool_keeper`
  - 工坊師傅 → `workshop_master`

站位格都是走得到的空格（測試逐一檢查）。

## 5. 測試（`tests/content/test_capital_field.py`，40 項）

- 載入：主城加 3 張室內圖、尺寸、`layout`；主城不在任何地點圖、沒有地圖能走進主城。
- 沒有出口、傳送石 1 個且在廣場、抵達點在傳送石旁。
- 安全區：主城與室內都沒有 spawns、營火、事件點、npcs。
- 進度：雲嶺、荒原 18／18，主城 1／1，室內圖 7 張；`field_warnings`、`field_pending` 都是空的。
- 設施齊全：室外、室內的 facilities 與 situation_objects 各自完全等於草稿清單。
- NPC 可達：9 位功能型 NPC 的站位都在入口可達範圍內。另外每個設施和情境物件旁邊都走得到。
- 浮橋與石碑 5 組：
  - 橋面在邊緣、是深淵上的木橋、走得到；
  - 石碑是石柱、旁邊走得到、離橋頭不超過 2 格；
  - bridge 和 stele 各 5 個。
- 門配對：3 扇門↔室內出口互指；不是隱藏門；門外與出口格走得到。草稿的大致方位（殿在北、酒館在西、鐵匠鋪在東）。
- 驗證抓得到的錯：
  - 加走路出口、加 spawns、加營火（室內也算）；
  - 傳送石 0 或 2 個；
  - 加 npcs、`location` 不是 capital；
  - 門通往別處的室內圖；
  - 區域地圖的出口指向主城。

## 6. 檢查結果

- `UV_NO_SYNC=1 uv run pytest -q tests/content tests/cli -k "field or content" -n 8`：2531 通過
- `ruff check`、`ruff format --check`（src、tests/content、tests/cli）：通過
- `mypy src`：503 檔無問題。全專案 `mypy` 另有 1 個錯誤，在 `tests/world/test_field.py:92`（`Collection[object]` 的 dict key）。這是 main 上本來就有的，本段沒動那個檔。
- `lint-imports`：13 kept、0 broken
- `trpg content check`：通過，`實地地圖：雲嶺 18／18、灰燼荒原 18／18、主城 1／1（另有室內圖 7 張）`；沒有警告、沒有待補
- 重播：`trpg battle --map swamp --seed 7 --log-json` → `battle replay` 驗證通過（88 個動作、313 個事件）

## 7. 留給 6D-5 的規則（本段只畫地圖與最小 schema）

1. **怎麼抵達**：
   - 從各區的傳送石與城鎮傳送到主城；新角色也可以從霧渡鎮的傳送石去；
   - 大世界圖上主城一開始就解鎖；
   - `stone_capital` 要預設解鎖或另外處理。目前 `use_teleport_stone` 與 `_stone_targets` 只認 `char.teleport_stones`，角色不在任何區時 `char.region` 該怎麼表示也還沒定。
2. **安全區規則**：
   - 進城、在城裡走、進出室內都不算一步：不推進時間、不擲事件、不花補給；
   - 不能紮營，在整備亭或酒館直接休息。整備亭目前只是情境物件，休息要接線；
   - 可換技能組、配點、換裝；
   - 全滅不回主城（回最近的小鎮或營火）。
3. **情境物件的面板接線**：浮橋石碑開該區傳送選單，依「已開放／未解鎖＋條件／之後的賽季」顯示三種內容。下列各開自己的面板：
   - 封印台、裂界投影、擊殺石碑、守印人；
   - 許願池、守池人；
   - 靶場、工坊師傅；
   - 循環賽報名台；
   - 整備亭；
   - 書記與魔導書書架。
4. **動態站位**：朋友的角色（中央廣場與酒館附近）、9 名系統傭兵（傭兵營），草稿說每次進城更新，沒有寫進地圖。

## 8. 待 PM 決定

**照草稿預設做的待確認項目**（6 條全照預設）：
1. 名稱暫用「樞島」：`name_zh: 樞島`，進度列用「主城」，ID 用中性的 `capital`，改名不影響 ID。
2. 主城 NPC 沒有人設卡：只放功能型站位，不開自由聊天，做法見第 4 節。
3. 主城沒有商店：沒放 `shop`。
4. 五座浮橋的方向：西雲嶺、南荒原、北晶冠、東樞市、東南霜潮。要和大世界圖一致，6D-5 和美術定案時可能要搬。
5. 賽季 Boss 挑戰入口：`rift_projection` 放在封印廣場。小鎮現行的挑戰入口沒動。
6. 全滅不回主城：是規則，6D-5 做。

**草稿與規格沒寫到、我採保守做法的**：
1. 功能型 NPC 用 `facilities`／`situation_objects`，不新增設施種類，避免動到 API 的 `FacilityKind` 與 client。如果要讓守印人這幾位也直接開面板，6D-5 可以選：
   - 加新的設施種類（seal、wish、workshop、loadout）；
   - 或把 `situation_objects` 接到面板。
2. 情境物件 ID 是本段自訂的：`bridge_<區域>`、`stele_<區域>`、`seal_altar`、`rift_projection`、`boss_stele`、`seal_keeper`、`wishing_pool`、`pool_keeper`、`training_range`、`workshop_master`、`shadow_league_desk`、`loadout_pavilion`、`scribe`、`grimoire_shelf`。目前沒有 situation 內容表可以對，驗證也不檢查這些 ID。
3. 主城的公告板與酒館都沒放事件點，因為主城沒有自己的事件骨架。酒館的「本週傳聞」靠 `tavern` 面板。
4. 浮橋做成 2 格寬，伸到地圖邊緣就斷在雲上。走到橋尾沒有任何效果，只有石碑會開選單。
5. `tests/cli/test_cli.py` 的進度正規式改了一行，原因見檔案清單。
6. 擺設是原型，外觀等 6D-ART：
   - 書架、櫃檯、木人樁、報名台用 crate；
   - 石碑、源晶燈、封印台用 stone_pillar；
   - 帳篷用牆。
