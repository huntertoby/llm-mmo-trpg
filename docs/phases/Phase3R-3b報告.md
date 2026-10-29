# Phase 3R-3b 報告｜種族外觀：耳、角、尾、膚色、衝突規則（C 畫風）

規格：`docs/phases/Phase3R計畫.md` 4.5 節的 3R-3b。畫法對照 `docs/art/sample/storyDoll.js` 的 `tail`、`ears`、`horns`；衝突規則以 `docs/art/可玩種族評估.md` 第 2 節為準（不照樣張的簡化）。體型、臉部紋路、鬍子、獠牙、龍鱗等屬 3R-3c，沒做。

## 1. 交付

| 項目 | 位置 |
|---|---|
| 種族部件與衝突規則（新） | `client/src/render/inkRace.ts`：`raceLookToLook`（後端 `RaceLook` 底線欄位 → `Look` 駝峰；不認得的值＝沒有）、`COVERS`／`coverOf`（每種頭部裝備 kind 一個遮蓋標記）、`hatAdjust`、`drawInkTail`、耳（`drawEarsUnder`／`drawSideEarBeforeHat`／`drawBeastEarsBeforeHat`／`drawEarsAfterHat`）、`drawInkHorns` |
| 骨架整合 | `inkDoll.ts`：尾巴在披風之後（背面在披風之上）；尖耳在頭之前；頭部裝備依 `hatAdjust` 調整；頭部裝備之後畫穿出的耳朵，最後畫角 |
| 外觀資料管線 | `Look` 新增 `ears／horns／tail／hornColor／tailColor／scaleColor`；`resolveDoll` 的 `raceLook` 疊在範本外觀上（膚色、髮型、眼色換成種族的，部件加上去；召喚物與骷髏不套用）；`UnitDraw.raceLook`、殘影複製召喚者也帶 |
| Python／API（範圍很小） | `engine/view.py`：`RaceView` 新增 `look: RaceLook`（取自 `races.yaml`）；重產 `client/openapi.json`、`schema.d.ts`；新夾具 `client/src/render/fixtures/raceLooks.json`（`api/fixtures.py`、`scripts/export_client_fixtures.py`、`tests/api/test_client_fixtures.py` 同步） |
| 開發頁 | `doll-gallery` 新增 ⑫：10 族四方向、各衝突組合 |
| 測試 | `client/src/render/inkRace.test.ts`（12 項）；`race.test.ts` 夾具補 `look` |

## 2. 衝突規則實作對照（可玩種族評估.md 第 2 節）

| 頭部裝備 | 角 | 尖耳／鰭耳 | 獸耳 |
|---|---|---|---|
| 頭盔、重盔 | 穿出（最上層） | 兩側伸出（正面畫在頭之前；側面畫在頭盔之後） | 藏起來 |
| 角盔 | 種族角取代裝飾角（改畫成一般頭盔） | 伸出 | 藏起來 |
| 兜帽 | 穿出 | 藏起來 | 兜帽頂端多兩個帽色凸起 |
| 皮帽、頭巾、皇冠 | 皮帽、頭巾、皇冠變窄（x×0.8），戴在兩角之間 | 伸出 | 皮帽、頭巾從帽子兩側穿出；皇冠不遮、照畫 |
| 寬帽、巫師帽 | 帽子抬高 5 | 伸出 | 藏起來 |
| 長袍（身體） | 尾巴畫在身體之前，下襬蓋住根部、尾巴從下襬後側露出 | | |
| 披風（背面） | 尾巴畫在披風之上 | | |

不認得的頭部裝備 kind：只蓋頭頂；不認得的耳、角、尾值：當作沒有。

## 3. 驗收

| 條件 | 結果 | 證據 |
|---|---|---|
| `look` 新欄位、駝峰／底線對照、不認得的值退回預設 | 通過 | `inkRace.test.ts`「欄位對照」；`raceLooks.json` 與 `races.yaml` 同步（pytest 夾具檢查） |
| `UnitView` 帶出主角種族外觀 | 通過 | `RaceView.look`；實戰 API 回傳 `race.look`（角魔 horns=curved、tail=demon） |
| 10 族四方向耳、角、尾、膚色 | 通過 | `img/3R-3b-doll-gallery-races-south-north-east.jpg`、`-races-west.jpg` |
| 衝突規則各一張 | 通過 | `img/3R-3b-conflict-horns-hats-south.jpg`（角＋寬帽／皮帽／角盔…）、`-conflict-fox-headgear-east.jpg`（獸耳＋兜帽、頭盔、皮帽，側面）、`-conflict-elf-headgear.jpg`（尖耳＋頭盔）、`-conflict-fox-robe-tail.jpg`（尾巴＋長袍）、`-conflict-fiend-cape-back.jpg`（角魔披風背面） |
| 全組合自測（10 族 × 全部頭部 kind＋沒戴＋未知 kind × 4 方向）不出錯、確定性、不用 `Math.random` | 通過 | `inkRace.test.ts` |
| 實戰看得到 | 通過 | `img/3R-3b-battle-fiend-hero.jpg`（種子 7 以 `race: fiend` 開一輪；主角長髮＋魔尾；小角與深色頭髮同色、縮圖下不顯眼） |
| tsc、vitest（`src/render`、`src/battle` 81 檔 811 項）、build | 通過 | |
| ruff、format、mypy（改到的檔）、pytest（`tests/api/test_openapi_snapshot.py`、`test_client_fixtures.py`、`tests/engine/test_race_skills.py`、`test_race_battles.py`） | 通過 | |
| 排版煙霧檢查（1600×900、800×600、1600×900 shortBottom） | 全 PASS | 注意：目前開始畫面下 `runCase` 內建的 `startBattle` 一直無法進入戰鬥（定時器節流），我改為手動選武器與關鍵字、按「開始戰鬥」後再呼叫 `runCase`；shortBottom 先手動寫入 `trpg.battleLayout` |

未跑完整 `scripts/check.py`（守則 11）。複雜度類 `noqa`：無新增。

## 4. 待 PM 決定

1. **龍角、龍尾提前畫了**：`horns: dragon`、`tail: dragon`（含背刺）與樣張同一函式，沒另外拆，所以龍裔目前已有大龍角與粗龍尾；龍鱗紋路、豎瞳、鱗脊、鱗色（`scale_color` 只當尾巴預設色，角色用 `horn_color`）屬 3R-3c 沒做。
2. **種族外觀覆蓋範本外觀**：有種族時膚色、髮型、髮色、眼色一律換成種族的（裝備不動）；範本自己的膚色髮型被蓋掉。若 3R-3a／出身要保留自訂膚色，需改成「範本優先」。
3. **`RaceView` 只有主角帶種族**：敵人與隊友目前沒有種族，所以只有主角會出現種族外觀；`UnitView` 別處沒新增欄位（動到 `engine/view.py`、OpenAPI、夾具檔，合併時若與 3R-3a 衝突請 PM 處理，重產 OpenAPI 即可）。
4. **背面長袍＋尾巴**：背面尾巴畫在身體與披風之上（含長袍），沒有裁掉「下襬以上」的部分。
5. **寬帽抬高量**：固定 5；角在帽子前面畫（帽子沒有真的「架在角上」遮住角根），縮圖下看起來是角從帽緣前探出。
6. **兜帽的獸耳凸起**用帽色、不畫內耳；側面尖耳戴頭盔時耳尖畫在頭盔之後（蓋在頭盔上）。
7. **尖耳戴兜帽、鰭耳戴兜帽**一律藏起來；皇冠不遮獸耳與尖耳。
8. **`build`（體型）**：`Look.build` 與骨架縮放原本就有，但這段沒有把種族資料的 `build` 帶進 `raceLookToLook`（留給 3R-3c「接上資料來源」），所以精靈、矮人、獸人目前仍是普通體型。
9. **`runCase` 在目前開始畫面失敗**：`layoutSmoke.ts` 的 `startBattle` 疑似在內建瀏覽器背景節流下點不到第二個關鍵字（與我的改動無關）；3R-3a 改開始畫面時可順便檢查。
10. **共用內建瀏覽器**：另一個 agent 的分頁（8013）會搶走前景，截圖常逾時，須用 `tabId`＋`tabs_select`。
