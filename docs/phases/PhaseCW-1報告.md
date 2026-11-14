# Phase CW-1 報告｜熔心坑冷卻井

> 實作者（Opus 5.5），2026-11-14，起點 `d828e0d55`（含本機 main `6eb7a1f8c`＝GB-4b 合併）。規格：`docs/art/冷卻井-移植需求.md` 全文（第 5 節、第 6 節第 1 條為玩法 PM 定案，`docs/玩法PM交接.md` 4.1.12）、`docs/design/19-灰燼荒原與賽季主線.md` 19.2.3、`docs/design/20-第一季商店與裝備內容.md` 灰燼之心那一列。動手前 grep `docs/phases/`：沒有人做過冷卻井。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| 引擎：漏出範圍參數 | `SpillDef.radius`（選填，`ge=1, le=5`，意義同 `explosion.radius`，`1`＝3×3）。沒寫＝原本的十字 5 格（程式路徑一字不改）；寫了＝`interactions._spill_square`：切比雪夫方陣、`(y, x)` 排序、界外與**巨型單位佔格**（`rules.footprint.giant_at`）不放。`ObjectDef.description_zh`（選填）進名詞表。兩個欄位都 `exclude_if` 空值不輸出。`tile_info` 的漏出規則句在有 `radius` 時寫「範圍 3×3（不放在巨型頭目佔的格子上）」 | `86fe1f76f` |
| 內容：冷卻井 | `content/objects.yaml` 新增 `cooling_well`：名「冷卻井」、`glyph: u`、`max_hp: 15`（占位）、`tags: [blocks_move, breakable]`、`spill: {surface: water, radius: 1}`、說明「打破後井水漫出，周圍 3×3 變成水面。」（照玩法 PM 4.1.12：拿掉油桶的半掩護、可推、可燃、爆炸；不可燃）。熔心坑 4 格預放水表面換成 4 口井（同座標 (3, 4)、(7, 4)、(3, 8)、(8, 8)），檔頭代決 5F5a-7 的註解改掉。重產名詞表夾具 | `e0c5fe8b3` |
| 前端：外觀、演出、碎屑 | `render/coolingWellArt.ts` 照樣張 `coolingWell.js` 第 2 版搬（完好／受損 1／受損 2 自己畫裂縫、K0～K2 空中、碎屑、遮罩），加美術 PM 結案的兩條可修（受損小灘往格內收：中心 8／44、半徑 3.8；K1、K2 空中碎塊 ×1.3、外框 2）。`ASHEN_OBJECTS.cooling_well`，預設表 `OBJECT_DRAW` 也用同一個畫法；`drawObject` 不疊通用裂痕（同薄冰）。破壞演出接在 `SurfaceAnimator`（第 6 節第 7 條見待決 3）。格子資訊卡把物件說明放在規則前面。`glossary.ts` 字「井」 | `8de834bb9` |
| 開發頁與截圖 | `client/dev/cooling-well-gallery.html`、`src/dev/coolingWellGallery.ts`（熔心坑場景、受損、停格連拍、打破後）、`src/dev/fixtures/moltenHeartUnits.json`（灰燼之心、餘燼蜥的畫面資料，取自實機 API）；`docs/art/shots/CW-1/` 8 張 | `6775101d5` |
| 文件 | 本報告；上手筆記三份各補一點（內容第 54 點、引擎第 54 點、前端第 177～179 點） | 本報告的 commit |

## 2. 逐條驗收

| 驗收 | 結果 | 證據 |
|---|---|---|
| 熔心坑以外逐字不變（7 張圖 × 種子 1、2 ＋ `rift_gate`、`cloud_summit` × 種子 3～12） | **過**：`battles=34 events=14490 different=0` | 第 3 節 |
| 熔心坑改前改後的勝方與輪數；每場結束、重播一致 | **過**：12 場都在 30 輪內分出勝負，12 場重播最終狀態一致 | 第 3 節 |
| `LOG_FORMAT` | **沒升**（仍 `/128`）：結算規則沒有改到舊內容（見第 4 節、待決 1） | 第 4 節 |
| CLI 快照先預測 | 預測 0 鍵，實際 0 鍵（`tests/cli -m slow` 44 passed，沒有重產） | 第 5 節 |
| OpenAPI | 沒改到 API（`GlossaryEntry.description_zh` 本來就有）：跑 `scripts/export_openapi.py` 後 `client/openapi.json` 無差異，所以沒跑 `gen:api` | — |
| `uv run trpg content check` | 結束碼 **0**（690 個檔案、429 個技能） | — |
| 靜態檢查 | `ruff check` 0、`ruff format --check` 0、`mypy` 0（1614 檔）、`lint-imports` 0（14 kept） | — |
| 相關 pytest | 過（第 5 節列檔） | — |
| 一場重播 | `trpg battle --map molten_heart_pit --seed 7 --log-json` → `trpg battle replay`：「重播驗證通過：96 個動作、568 個事件，最終狀態一致」，兩個結束碼 0 | — |
| 前端 | `tsc` **0**；交件前全量 `vitest` **0**（362 檔、4587 項全過）；`build` **0** | — |
| 截圖（1600×900、800×600） | 移植需求第 7 節 6 項都有（3 項實機、其餘開發頁並標「實機未看」） | 第 6 節 |

## 3. 不變比對與熔心坑

腳本在 scratchpad（未 commit）：改前＝本段第一個 commit 之前的工作樹（起點 `d828e0d55`）先跑一次存 JSON，改後再跑一次；地圖預設陣容、效用 AI、`max_rounds=30`；每場比完整事件 JSON、步驟、勝方、輪數、最終狀態 JSON（拿掉 `final_state.ruleset`），沒剝其他鍵。

- 熔心坑以外 34 場：**`battles=34 events=14490 different=0`**；`ruleset_hash` 34 場全變（規則包內嵌物件表，多了 `cooling_well`；舊物件序列化逐字相同，`test_old_spill_without_radius_keeps_the_cross_and_its_serialization` 驗）。
- 熔心坑 12 場（只列不評）：

| 種子 | 改前 勝方／輪／事件 | 改後 勝方／輪／事件 | 改後打破的井（座標） | 漏出水的 `surface_changed` 格數 |
|---|---|---|---|---|
| 1 | 敵／4／485 | 敵／5／510 | (8, 8) | 4 |
| 2 | 敵／4／439 | 敵／6／571 | — | 0 |
| 3 | 敵／5／510 | 敵／5／439 | (3, 4) | 4 |
| 4 | 敵／5／440 | 敵／5／484 | — | 0 |
| 5 | 敵／5／404 | 敵／6／537 | (3, 4) | 1 |
| 6 | 敵／5／532 | 敵／5／499 | (3, 4) | 2 |
| 7 | 敵／4／407 | 敵／6／568 | (3, 4)、(7, 4) | 7 |
| 8 | 敵／5／394 | 敵／4／385 | (7, 4)、(3, 4) | 11 |
| 9 | 敵／5／448 | 敵／6／429 | — | 0 |
| 10 | 敵／6／559 | 敵／6／552 | (3, 4) | 4 |
| 11 | 敵／5／484 | 敵／5／449 | — | 0 |
| 12 | 敵／6／560 | **我**／6／545 | (8, 8) | 9 |

  12 場的井都是 `cause: damage` 打破的（範圍招或打錯目標，AI 沒有專門打井）。水格少於 9 的原因：(3, 4)、(7, 4) 的 3×3 有 2 格是灰燼之心的佔格（不放）、1 欄是岩漿（致命地形不放）、格上已有水或火時照互動表處理。12 場都在 30 輪內結束，scratchpad 的 `replay_pit.py` 逐場 `BattleLog` 來回序列化再 `replay`，最終狀態 JSON 全部一致。

## 4. 版號與規則

- `LOG_FORMAT` 沒升：紀錄格式文件 1.2「規則包的資料結構新增有預設值、不影響舊內容結算的欄位，不升版號」。舊規則包沒有 `radius`（`exclude_if`，序列化也沒有這個鍵），舊紀錄重播走原本的十字路徑、`ruleset_hash` 照舊對得上；新分支只有新內容（冷卻井）用得到。`docs/phases/戰鬥紀錄格式變更.md` 因此沒有新增一條（待決 1）。
- `WORLD_RULES_VERSION` 等其他版號沒動。

## 5. 快照預測與測試

- **CLI 快照預測**：0 鍵。理由：沒改技能（`skills_list`、`skills_show_all/*` 不變）；7 個戰鬥鍵都不是熔心坑、地圖上沒有冷卻井，前述不變比對證明結算一樣，戰鬥輸出不印規則包雜湊。實際：`uv run pytest -q tests/cli -m slow -n 8` **44 passed**，預測與實際相同，沒有重產任何鍵。
- **新測試**：`tests/engine/test_cooling_well_cw1.py`（6 項：定義照玩法 PM、3×3 依 (y, x) 排序與 `cause`、火打破也漏水不爆、巨人佔格跳過、油桶十字與序列化不變、熔心坑 4 口井＋一場重播）；`client/src/render/cw1CoolingWell.test.ts`（9 項：畫法登記與字、幾何上緣與耐久條、碎塊確定性與放大、時間表與遮罩半徑、打破推算、地表動畫接線（9 格照 520 ms、碎屑留著、新的一場清掉、略過、換地圖）、格子資訊卡）。
- **改到的既有測試**（拿掉本段改動就回到舊值）：`tests/content/test_ashen_fields.py::test_molten_heart_pit_antechamber`（「至少 4 格預放水」→「4 口井在原座標」，檔頭說明一起改）；`client/src/render/regionReskins.test.ts`（預設畫法雜湊只鎖舊物件：迴圈排除 `cooling_well`，雜湊值沒動）；`ui/floatCardRule.test.ts` 掃到開發頁的內聯 `position: absolute`，改開發頁（負邊距），規則沒放寬。
- **相關 pytest**（`-n 8`）：`tests/content`、`tests/narrative`、`tests/api/tuning`、`tests/api/test_giant_api.py`、`test_client_fixtures.py`、`test_views_glossary.py`、`test_glossary_names.py`、`tests/engine/` 的 `test_phase1c_decisions.py`、`test_hurl_object.py`、`test_giant_gb1a.py`、`test_giant_ai_gb3.py`、`test_cooling_well_cw1.py`、`tests/world/test_ashen_waste.py`、`tests/test_architecture.py`——全過：**3915 passed**（結束碼 0）。
- **相關 vitest**：`src/battle`、`src/render` 全跑過（203 檔），交件前全量一次（362 檔、4587 項，結束碼 0）。

## 6. 截圖（`docs/art/shots/CW-1/`，8 張、jpg 80、DPR 1、最大 114 KB）

| 檔 | 移植需求第 7 節 | 來源 |
|---|---|---|
| `docs/art/shots/CW-1/01-pit-open-1600.jpg` | 1：1600 熔心坑開場，4 口井完好 | **實機**（開發 Boss，1600×900） |
| `docs/art/shots/CW-1/02-pit-open-800.jpg` | 2：800 同上 | **實機**（800×600，自動 53%） |
| `docs/art/shots/CW-1/03-damaged-1600-dev.jpg` | 3：(3, 8) 受損 1（左一灘、左裂縫、有熱氣）、(8, 8) 受損 2（左右各一灘、缺角、沒熱氣），耐久條與水滴記號都看得到 | 開發頁，**實機未看** |
| `docs/art/shots/CW-1/04-break-k0-k3-1600-dev.jpg` | 4：K0（45 ms 白閃）、K1（145 ms 水柱、碎塊飛、遮罩半格＋水沫）、K2（270 ms 水花、遮罩十字）、K3（430 ms 漣漪、碎屑落定） | 開發頁停格，**實機未看** |
| `docs/art/shots/CW-1/05-after-1600-dev.jpg` | 5：1600 打破後 3×3 水＋碎屑，主角站在水裡 | 開發頁（演出播完），**實機未看** |
| `docs/art/shots/CW-1/06-after-800-dev.jpg` | 6：800 同上 | 開發頁，**實機未看** |
| `docs/art/shots/CW-1/07-after-zoom-1600-dev.jpg` | 5 的放大（碎屑泡在水裡、主角在水中） | 開發頁 |
| `docs/art/shots/CW-1/08-tile-card-1600.jpg` | 格子資訊卡：「冷卻井・HP 11/15」、說明、規則 | **實機**（主角打了一槍後滑過） |

實機的做法照前端上手第 176 點（大世界開發 Boss）。主角（火槍）從 (3, 11) 打 (3, 8) 的井一槍 4 點（HP 11/15，還沒到受損 1），第 2 輪前主角就倒了，所以受損、打破、打破後只能用開發頁（場景照地圖檔、灰燼之心與餘燼蜥用實機存下的畫面資料）。瀏覽器：自己開的 headless Chrome（`--mute-audio`、`--remote-debugging-address=127.0.0.1`、埠 9341）＋ vite 5281／5282 ＋ `trpg serve` 8781（`TRPG_DEV_ROUTES=1`、存檔在 scratchpad），用完都以 PID 結束，確認沒有殘留；暫存的 vite 設定已刪。

浮動卡：本段沒有新的彈出元件，只在既有的格子資訊卡多一行說明（08 是滑過時的樣子）；「滑進→捲到底→釘住→關閉」這套沒有重跑。

## 7. 待 PM 決定

1. **沒升 `LOG_FORMAT`**：新欄位有預設值、不影響舊內容，照紀錄格式文件 1.2 不升、也沒寫格式變更紀錄。若 PM 認為「新增一種漏出範圍」算結算語意改變，要升 `/129` 並改 3 個 endswith 測試與 9 處字面值。
2. **`ObjectDef.description_zh` 是新增的 schema 欄位**（說明字要有地方放）。格子資訊卡現在是「說明」＋「不可通行・可被破壞」＋「被傷害打破或摔破時漏出水，範圍 3×3（不放在巨型頭目佔的格子上）」，說明和最後一行意思重疊；要不要只留其中一個。
3. **演出接法（移植需求第 6 節第 7 條）**：沒有接 `object_destroyed` 事件，而是比較前後兩張畫面（前一張有井、這一張沒有），和地表轉場同一個時鐘；不擋後續動畫（照建議）。好處是重播、略過、觀戰都一樣；代價是「讀檔、重連後不留碎屑」（第 5 條允許）。
4. **其他區的預設畫法（第 6 條）**：預設表也用冷卻井的畫法（沒標區域時不會出灰色六角形）；目前只有熔心坑用到。
5. **物件不在數值工坊白名單**：`tuning_fields.yaml` 沒有 `objects.yaml` 的 target，「max_hp 交使用者在工坊調」現在做不到；要的話另開一段把物件的 `max_hp` 加進白名單。
6. **3×3 碰到的格子（第 6 條第 4 點）**：照引擎規則——頭目佔格不放（新判斷）、岩漿與牆不放（原規則）、矮牆格與高台格照放（表面可在有物件、高的格子上）。熔心坑 (3, 8)、(8, 8) 的 3×3 會把水鋪到高台 (2, 9)／(9, 9) 與矮牆 (4, 9)／(7, 9) 格上。
7. **空中層的位置**：碎塊、水柱、水珠放在井那一排的物件層（照第 5 節第 5 條）。K1～K2 的範圍量過都在那一排以內或往北，不會被南邊一排的地面蓋掉；往北伸的部分（水柱、K1 水珠）會畫在北邊一排之上。
8. **截圖資料夾名**：照派工寫的 `docs/art/shots/CW-1/`（6.5.2 寫段名小寫，例 `6f19`）；要改成 `cw-1` 的話 `git mv` 即可。
9. **別人的檔沒動**：`docs/art/四區移植需求.md` 第 2 節與第 7 節「熔心坑的冷卻井還是藍色的水」三行（移植需求第 9 節可修 4 說做完後改指向本文件）、`client/src/dev/regionGallery.ts` 熔心坑場景的標題「冷卻井是水表面」——交美術 PM／下一段順手改。

## 8. 平衡疑慮（只記，不量）

- 原本 4 格預放的水是**永久、開場就有**；現在要先打破井才有水，而且 AI 不會專門打井（12 場裡 8 場打破至少一口，都是順帶打到）。熔心坑的「怕水」時刻變得要玩家自己去開；對玩家可能是變難（開場沒水）也可能變簡單（一口井換 3×3、最多 7～9 格）。
- (3, 4)、(7, 4) 兩口井緊貼頭目、殼縫攻擊位與餘燼蜥開場格，打破後水直接鋪在蜥蜴腳下（餘燼蜥怕水／潮濕不能回血）；第 3 階段往南長的火地碰到水的互動也會更常發生。
- `max_hp` 15 是 `灰燼實地圖庫.md` 的占位，而且目前無法在工坊調（待決 5）。

## 9. 附註

- 上手筆記：內容第 54 點（`spill.radius`／`description_zh`、新物件要一起改的三處、物件不在工坊）、引擎第 54 點（漏出範圍兩條路徑、為何沒升版號）、前端第 177～179 點（演出接在地表動畫、開發頁停格做法、CDP 的視窗尺寸只在同一條連線有效）。
- 踩坑：Bash 的 `uv run python -c "..."` 字串裡寫了反引號，被 shell 當指令執行吃掉一段註解（已補回；記憶裡已有這條，沒有新增）；`Path.write_text` 在 Windows 寫成 CRLF（內容上手第 53 點已有），改用 `write_bytes`。
