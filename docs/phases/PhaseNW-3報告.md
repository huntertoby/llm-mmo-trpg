# Phase NW-3 完成報告｜數值工坊白名單：巨型頭目 AI 權重＋物件欄位

起點：本機 `main` `1c896462e`（派工時寫 `a9632ae1c`，開工時 fast-forward 到較新的 `1c896462e`，只多一筆開發 PM 交接）。
段名：`docs/phases/` 沒有 NW-3 的報告或規格檔；`PhaseNW計畫.md` 第 3、4 節把「AI 表、裝備、遭遇」排為 NW-3，本段只做其中 AI 的三個權重，外加物件的 `max_hp`，沿用 NW-3 這個名字（開發 PM 交接 11-14 派工就叫 NW-3）。GB-3、CW-1 的報告確認這幾項沒人做過。

## 1. 做了什麼

| 項目 | 內容 | commit |
|---|---|---|
| AI 權重（GB-3 待決 3） | `content/tuning_fields.yaml` 的 `kind: ai` 加 `parts.guard_face_bonus`（巨型頭目護面的加分，建議 0～10）、`parts.giant_spot_bonus`（隊友找巨型部位的站位分，建議 0～20）、`profiles[*].weights.prefer_far_from_leader`（追離頭目遠的人，建議 0～10，`existing_only`：只展開已寫的模式，目前只有殼縫蟲群）。標籤「行為模式「殼縫蟲群」：追離頭目遠的人」；AI 表頂端說明改成列出現在開的欄位 | `52756df30` |
| 物件欄位（CW-1 待決 5） | 新表格對象 `kind: object`（`objects.yaml`，清單名「格子物件（全體共用）」、`category: object`）；只開 `objects[*].max_hp`，`existing_only`（13 種已寫 `max_hp` 的物件，含冷卻井；草叢沒寫＝打不破，不展開）；標籤「物件「冷卻井」最大 HP」；建議 1～99，擋 1 以上（schema `ge=1`） | `52756df30` |
| API／OpenAPI | `TuningCategory` 多 `object`；`TABLE_KINDS`、`TARGET_MODELS`、`TuningTarget.kind` 多 `object`；`objects._entry_label`、`_schema_limits`；重產 `client/openapi.json`、`client/src/api/schema.d.ts`（只差 `TuningCategory` 一行） | `52756df30` |
| 工坊前端 | `TuningScreen` 多讀 `tuningObjects("object")`；`FieldForm` 清單多「格子物件（全體共用）」一組與表單頂端的類別名；`api/client.ts` 的 `tuningObjects` 參數型別；vitest 1 項 | `cb516eb0c` |
| 截圖、報告、上手筆記 | `docs/art/shots/NW-3/` 5 張（DPR 1）；本報告；`docs/dev/上手-內容資料與模擬.md` 第 54 點與第七節 | 報告 commit |

**整類開放的做法（為什麼這樣選）**：物件全在一個檔（`objects.yaml`），照 AI 表、規則表的「一個檔一張全體共用的表」做成表格對象，白名單只加一行 `objects[*].max_hp`＋`existing_only`。影響最小：不碰 `ObjectDef`、不改任何物件的 YAML、不讓「沒寫 `max_hp`」的物件被插入（插入會把打不破的東西變成打得破，屬結構）。一致：13 種有 `max_hp` 的物件一起開，不特例冷卻井；爆炸（`explosion.*`）、漏出（`spill.radius`）、標籤都不開（列在待決 2）。

## 2. 逐條驗收

| 驗收 | 結果 |
|---|---|
| 工坊讀寫新欄位有測試（API 層） | **過**：`tests/api/tuning/test_nw3_whitelist.py` 15 項——白名單、只展開已寫的模式／物件、標籤、清單與表單（值、擋的範圍）、YAML 字面替換只動那個數字（4 欄位）、不合法值擋下（冷卻井 0、草叢插入、護面 −1、莽夫插入權重）、寫回暫存 repo（殼縫蟲群權重、冷卻井 HP）只差一行且 commit 只含那個檔 |
| 前端有改 → vitest | **過**：`tuning.test.ts` 加 1 項（物件表分組、`objectKind`→`object`、畫面讀 `object`、物件與 AI 新欄位的表單、改值記進改動單）；`src/tuning` ＋ `bs2SilentStrike.test.ts` 66 項全過；`tsc` 0 |
| 改了值，戰鬥吃到新值 | **過**：`test_changed_values_reach_the_battle`——草稿改護面 +1、站位 +1、殼縫蟲群 +1、冷卻井 HP +5，驗證通過後載入草稿內容庫：每個行為模式的 `guard_face_bonus`／`giant_spot_bonus` 都是新值、`ember_brood` 的 `prefer_far_from_leader` 是新值（莽夫仍 0）、熔心坑 `begin_battle` 開場 4 口井 `hp`／`max_hp` 都是新值（改前是舊值） |
| 沒改時所有戰鬥逐字不變 | **過**：`battles=46 events=19276 different=0`（第 3 節） |
| OpenAPI 重產與快照測試 | **過**：`export_openapi.py`、`gen:api` 已跑；`tests/api/test_openapi_snapshot.py` 過 |
| CLI 快照 | 預測 **0 鍵**；實際 `tests/cli/test_output_snapshots.py` 1 passed、`tests/cli -m slow` 44 passed，沒重產任何鍵 |
| `uv run trpg content check` | 結束碼 **0** |
| commit 前檢查 | `ruff check`、`ruff format --check`、`mypy`（668 檔）、`lint-imports`（14 kept）全過；相關 pytest `tests/api/tuning`＋`tests/content/test_tuning_fields*.py`＋OpenAPI 快照 203 passed |

## 3. 不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive 1c896462e src content` 解到暫存區，改後＝本段 HEAD 的工作樹；兩邊各用自己的 `src` 與 `content`。地圖預設陣容、效用 AI、`max_rounds=30`；每場比完整事件 JSON、步驟、勝方、輪數、最終狀態 JSON（拿掉 `final_state.ruleset`）。

- 8 張地圖（`bandit_lair`、`bridge_chasm`、`cliff_outpost`、`dark_forest`、`frozen_lake`、`lava_crossing`、`oil_depot`、`open_plain`）× 種子 1、2 ＋ 3 張頭目地圖（`cloud_summit`、`rift_gate`、`molten_heart_pit`）× 種子 3～12：**`battles=46 events=19276 different=0`**。
- 理由也成立：本段沒改 `content/` 裡任何會被載入的檔（`tuning_fields.yaml` 不進內容庫、不進 digest）、沒改引擎。

## 4. 截圖（`docs/art/shots/NW-3/`，DPR 1）

無頭 Chrome（`--headless=new --mute-audio`，除錯埠 9481 綁 127.0.0.1）＋CDP，`trpg serve --port 8012`（`TRPG_TUNING=1`），頁面 `/?dev=1&mute=1`。

1. `1_object_table_1600.png`：清單多「格子物件（全體共用）（1）」，表單 13 個物件的最大 HP。
2. `2_cooling_well_edited_1600.png`：冷卻井改成 20，「改過」＋草稿列出這筆。
3. `3_cooling_well_zero_refused_1600.png`：改成 0，欄位下紅字「不能小於 1」、模擬鈕擋住。
4. `4_ai_gb3_weights_1600.png`：AI 估值表的三個新欄位（巨型頭目護面、隊友找巨型部位、殼縫蟲群）。
5. `5_object_table_800.png`：800×600 的物件表單（標籤換行，沒有破版）。

截完把草稿的冷卻井改回 15（沒有留改動）；伺服器與 Chrome 用自己的 PID 結束。

## 5. 範圍外沒動

戰鬥結算、`content/` 的數值、頭目 HUD／延遲預告層／`usePlayback.ts`、設計文件與計畫檔都沒改。

## 6. 待 PM 決定

1. **建議範圍是占位**：護面 0～10、站位 0～20、追遠 0～10、物件 HP 1～99（只是畫面提示，不擋）。要改直接改 `tuning_fields.yaml` 的 `hint_min`／`hint_max`。
2. **物件其他欄位沒開**：`explosion.radius`／`dice`／`flat`（油桶）、`spill.radius`（冷卻井）。要開就在 `kind: object` 加路徑（`existing_only`），骰子用 `kind: dice`。
3. **`prefer_far_from_leader` 只開已寫的模式**（殼縫蟲群）。要讓使用者給別的模式加這個權重屬結構（新增鍵），目前會回「不開放」。
4. **物件 HP 不進技能預算**：土牆、冰牆、荊棘叢是 `create_obstacle` 造出來的，改它們的 HP 會讓造牆技能變強或變弱，但工坊的預算比例不會跟著變。是否要在表單加提示，或在預算裡算物件 HP，請決定。
5. **`prefer_far_from_leader` 的 schema 沒有下限**（`AiWeights` 其他權重也沒有），負值會變成「偏好追近的人」。目前照 schema 不擋（表單顯示沒有允許範圍）；要擋就在 `AiWeights` 加 `ge=0`（屬內容 schema，另開段）。
6. **AI 表的其他權重**（`status_values`、其他行為模式權重）、**遭遇 `armor_mods`、裝備、道具**仍照 `PhaseNW計畫.md` 的 NW-3 列待開；單位表單的唯讀提示「數值工坊 NW-3 才開」（`objects._armor_notes`）字面還在，等那段開了再改字。
