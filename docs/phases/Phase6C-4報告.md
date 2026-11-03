# Phase 6C-4 完成報告：雲嶺實地地圖②（其餘 9 張）

> 實作者 agent，2026-11-04。依據：`docs/phases/Phase6計畫.md` 第 2 節（6B-1 格式）與第 4 節（本段規格）；`Phase6C-3報告.md`；玩法 PM 草稿 `玩法PM-Phase6雲嶺實地地圖草稿.md`（2026-11-04）第 9～17 張與第 2 節方向表；18.3、21.2、21.3、21.6。
> 只動了 `content/world/fields/cloud_ridge/`、`tests/content/test_cloud_fields.py` 與這份報告。沒有改程式（`src/`），也沒有改地點圖。

## 1. 交付內容

| 地圖 | 檔案 | 大小 | 出口／門 | 敵人（spawns） | 事件點 | 其他 |
|---|---|---|---|---|---|---|
| 雲海吊橋 | `cloud_sea_bridge.yaml` | 24×18 | 西 古松祭壇、南 山門、東南 藥師谷、北 劍冢 | 北橋頭駐守 `sword_array`、橋上巡邏 `bridge_patrol` | `crane_envoy` | 傳送石（南岸）；吊橋寬 2 格（木橋物件），東側另有崖邊石徑 |
| 藥師谷 | `herb_valley.yaml` | 24×18 | 西南 斷崖幫寨、西北 雲海吊橋；**門** `elixir_cave_mouth` → 丹爐洞（`hidden_until: reveal`） | 藥田駐守 `valley_keepers`、谷口巡邏 `valley_beasts` | `cliff_lingzhi`、`poison_spring`、`gang_deserter` | 營火（藥廬裡）；毒泉（毒霧表面） |
| 丹爐洞（隱藏） | `elixir_cave.yaml` | 16×14 | 西 洞口 → 藥師谷（arrive 指向門） | 丹爐前 `furnace_steward`、南水房 `furnace_tide` | `runaway_furnace` | 丹爐（油桶）、兩側水房（水表面）、通道寬 3～4 |
| 北坡獵場 | `north_slope.yaml` | 16×14 | 南 冬湖、東 源晶裂痕；**門** `crane_cliff_crack` → 鶴歸崖（`hidden_until: reveal`） | 狼窩駐守 `north_slope_pack` | `possessed_hunter`、`fox_traveler` | 深草叢（草叢物件）、岩堆高 1～2 |
| 冬湖 | `winter_lake.yaml` | 24×18 | 南 獵戶小屋、北 北坡獵場 | 東岸 `lake_hunters`、湖心偏北 `lake_bears` | `bear_den`、`fox_traveler` | 營火（帳篷旁）；冰面表面、冰洞 2 個 |
| 劍冢 | `sword_tomb.yaml` | 24×18 | 南 雲海吊橋、西 源晶裂痕 | 石台駐守 `tomb_array`、外圍巡邏 `tomb_swordsmen` | `tomb_sword`、`shard_convoy` | 劍陣石台高 1、殘劍叢（矮牆） |
| 源晶裂痕 | `crystal_rift.yaml` | 24×18 | 西 北坡獵場、東 劍冢、東北 雲頂觀 | 北側 `rift_wraiths`、南側 `rift_scavengers` | `possessed_hunter`、`shard_convoy` | 傳送石（西南角）；裂縫長 8、寬 2，2 座石橋；霧牆 `rift_mist_wall`（情境物件） |
| 鶴歸崖（隱藏） | `crane_cliff.yaml` | 16×14 | 南 崖縫 → 北坡獵場（arrive 指向門） | 崖頂 `crane_nest`、下層 `crane_cliff_bear` | `frost_chime_riddle` | 崖台 0～3、外緣深淵；NPC 霜音 |
| 雲頂觀前廳 | `cloud_summit.yaml` | 12×8 | 西南 源晶裂痕 | 無 | 無 | 觀門 `summit_gate`（情境物件）、兩座石燈；沒有傳送石、營火 |

補齊 6C-3 留下的待補配對：斷崖幫寨↔藥師谷、獵戶小屋↔冬湖、青霧觀山門與古松祭壇↔雲海吊橋。新地圖的出口 ID 都照慣例 `to_<對面地點>`，所以 6C-3 那幾張一個字都沒改。

測試（`tests/content/test_cloud_fields.py`，51 → 102 項）：
- 參數化的測試從 6C-3 的 9 張擴到 18 張（`ALL_MAPS`）：出口內側站得上、走得回入口；拿掉木橋、薄冰後照樣走得到；`spawns` 與巡邏；事件點；營火與傳送石數量。
- 新增：
  - `test_all_eighteen_maps_are_drawn_and_pass`：實地地圖剛好涵蓋雲嶺 18 個地點，雲嶺沒有任何警告。
  - `test_only_the_ashen_waste_crossing_is_pending`：雲嶺內沒有待補，只剩往 `ashen_waste/ash_ferry`。
  - `test_hidden_places_are_entered_through_a_hidden_door`（丹爐洞、鶴歸崖）：相鄰地圖沒有出口、只有一扇 `hidden_until: reveal` 的門；隱藏地點唯一的出口 arrive 指向那扇門；洞口站得上，與入口互相走得到。
  - `test_cloud_summit_hall_is_only_reached_from_the_rift`：前廳 12×8，只有往源晶裂痕的出口，全內容庫只有源晶裂痕通往雲頂觀；沒有敵人、營火、傳送石、事件點；觀門與霧牆是情境物件。
- 接觸點新增 20 個（每個 spawn 至少 1 個，巡邏的取路線上 2 點），切出的 12×12 都通過 `check_map`：敵方起始區 4 格、我方 3 格。
- 連線配對測試略過兩條隱藏連線（門配出口，由上面的隱藏入口測試負責）。

## 2. 檢查結果

- `UV_NO_SYNC=1 uv run pytest -q tests/content -x -n 8`：2344 passed（其中 `test_cloud_fields.py` 102 項）。
- `tests/cli/test_cli.py -k content_check`：4 passed。
- `ruff check .`、`ruff format --check .`、`mypy src`（496 檔）、`lint-imports`（13 kept、0 broken）都通過。
- `uv run trpg content check`：通過。
  - 實地地圖：雲嶺 18／18、灰燼荒原 0／18（另有室內圖 2 張）。
  - **沒有警告**（傳送石：野外 3 個，城鎮 1 個另算）。
  - 待補 1 項：`ashen_ferry` 的出口 `to_ash_ferry` → `ashen_waste/ash_ferry`（6D-1）。雲嶺內沒有待補。
- swamp 種子 7 重播：通過，88 個動作、313 個事件，最終狀態一致。

## 3. 用了草稿哪幾條待確認的預設

| 草稿第 3 節 | 這段怎麼做 |
|---|---|
| 1. 雲海吊橋的大小 | 照草稿用 24×18，4 個出口都在吊橋圖上 |
| 2. 北坡獵場的大小 | 照表用 16×14。3 個出入口（南、東、隱藏崖縫）加狼窩放得下，不覺得擠 |
| 3. 一張圖幾隊敵人 | 每張最多 3 隊、巡邏 0～1 隊（測試檢查）；這段每張 0～2 隊 |
| 6. 三方混戰的呈現 | `lake_bears`、`crane_nest`、`crane_cliff_bear`、`rift_wraiths`、`rift_scavengers` 陣容本身帶 `third`，所以各放一個駐守點，碰到就開三方戰 |
| 9. 雲頂觀的霧牆 | 記成源晶裂痕上的情境物件 `rift_mist_wall`（山門出口內側），不畫會擋路的格子；擋住與提示語由走路動作做（6C-1／6C-5） |
| 10. 事件點數量 | 每張 1～3 個，一個事件骨架一個點；雲頂觀 0 個（Boss 地點不設事件） |
| 11. 傳送石位置 | 照草稿：雲海吊橋（南岸）、源晶裂痕（西南角）；加上 6C-3 的雨中梯田，野外 3 個 |
| 12. 切 12×12 靠近出口 | 測試的切法沿用 6C-3：越過邊緣就往內推 |

沒用到的：4（重生時間，6C-1）、5、7、8（6C-3 的地圖）。

## 4. 待 PM 決定（都已照最保守的做法做完）

1. **吊橋與「致命地形不擋唯一通路」**：草稿要吊橋寬 2、兩側深淵、中段可斬斷繩索。吊橋整段畫成 `wooden_bridge` 物件（打得斷），為了不讓它成為往北岸（劍冢）的唯一通路，東側加了一條 2 格寬的崖邊石徑繞過深淵（草稿沒有）。如果要吊橋是唯一通路，得放寬 4.2 的安全規則。
2. **源晶裂痕的形狀**：草稿寫裂縫「寬 1～2、長 8 格，把地圖分成南北兩半，中間有 2 座天然石橋」。長 8 格分不開 24 格寬的地圖，所以裂縫（深淵）畫 x 8～15 長 8、寬 2，兩側接碎晶岩脊（牆）到地圖邊緣；石橋 2 座各寬 1（x 9、x 14），用石地畫，不會斷。西、東兩個出口都在南半，往雲頂觀的山門在北半（要過石橋、經過霧魅）。
3. **雲頂觀的觀門**：門只能通往室內圖或隱藏地點，所以觀門記成情境物件 `summit_gate`（北牆正中內側），「走進觀門＝Boss 戰」由 6C-1／6C-5 接；Boss 戰照舊用 `cloud_summit` Boss 地圖。霧鎖真人的人設卡在 `cloud_summit`，但他在 Boss 圖裡，前廳不放 NPC。
4. **隱藏入口的提示**：丹爐洞「洞口 3 格內做感知判定」、鶴歸崖「狐火在霧裡指路」都是 reveal 的條件或畫面，不在地圖欄位裡。地圖只畫門的位置，狐火沒有另放物件。
5. **物件替代**（沒有新增 ID，照 6C-3 第 5 節第 7 條）：
   - 丹爐：`oil_barrel`（打翻會燒、會炸；「造毒霧」要 6C-5 或情境接），旁邊放一小片毒霧表面。
   - 鷹巢：`crate`；殘劍叢：`low_wall`（擋路不擋視線）；碎晶堆：`rubble`。
   - 深草叢、藥田：`grass` 物件；冰面：石地加 `ice` 表面；冰洞：`ice_hole` 地形；毒泉：`poison` 表面。
   - 帳篷、藥廬殘牆、霜音的石台：`low_wall`；石燈、繩樁、源晶柱：`stone_pillar`。
6. **北坡狼王與懸賞陣容**、**冬湖石背熊的等級門檻**、**劍冢懸賞期間的陣容**、**霧魅夜晚多一隻**：都是遭遇表的事。地圖只放 `north_slope_pack`、`lake_bears`、`tomb_array`／`tomb_swordsmen`、`rift_wraiths`，換陣容由 6C-1 照遭遇表的 variants 接。
7. **強風**（鶴歸崖）：是天氣或畫面，地圖不另畫。
8. **營火與情境物件的 ID**：營火照 6C-3 叫 `campfire_<地點>`；新的情境物件 `rift_mist_wall`、`summit_gate`，6C-5 接的時候可以再改。

## 5. 和規格的差別

- 規格 4.1 寫「傳送石 3 個加城鎮 1 個」：照 commit 0c32e8d8 之後的計數（城鎮不算在區域內），`content check` 沒有任何警告。
- 6C-3 報告第 5 節第 10 條（傳送石 4 個的警告）已由 0c32e8d8 解決，這段不用處理。

## 6. 過程

- 9 張圖用暫存的產生腳本（矩形填地形與高度、列出物件與表面）畫成 YAML，再逐張看網格確認出口、駐守、巡邏、事件點、營火、傳送石的位置。腳本不在 repo 裡，以後改圖直接改 YAML。
- 第一次載入就通過 `content check`（雲嶺 18／18、沒有警告、雲嶺內沒有待補）。
- 測試第一次跑有 3 個失敗，都是測試本身的問題：室內圖的 `location` 是 `None`、連線配對測試沒有略過隱藏連線、冬湖一個我方接觸點選到倒木格。改掉後全部通過。
- 複雜度：沒有新增 `# noqa`。
