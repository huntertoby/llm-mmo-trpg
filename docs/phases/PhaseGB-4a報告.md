# Phase GB-4a 報告｜巨型頭目：API＋前端邏輯（不動 `render/`）

> 實作者：GB-4a implementer（Opus 5.5），2026-11-14。依據 main `cb83fc060`（含 GB-2、GB-2b）。
> 規格：`docs/phases/PhaseGB計畫.md` 8.1、第 4 節 GB-4a 列、0.3 T12、第 11、12 節、末節開發 PM 裁定；併入 GB-1a 待決 4、GB-1b 待決 3／4；美術 `docs/art/GB巨型頭目-移植需求.md` 第 7 節第 5 條、第 9 節（只讀邏輯部分）。
> 中途電腦關機一次，worktree 停在 `cb83fc060`、沒有未存改動，從頭重做。

## 1. 做了什麼

| 交付 | 內容 | commit |
|---|---|---|
| API | `UnitView.footprint`／`tiles`（只有巨型單位輸出，1 格為 null）、`PartView.tiles`（部位綁的地圖格，依 (y, x)；1 格頭目為 null）；核心未露出的原因字（巨型頭目：「{露出的階段名}階段才露出」，拿不到退回「這個階段還沒露出」）；`api/skill_reasons.py`（排序用 `unit_dist`、格子型技能試最近佔格）、`api/hidden_info.py`（相鄰改 `adjacent`）、`sim/skill_ratio.py`（`dist_to`）換單位版距離；重產 `client/openapi.json`、`client/src/api/schema.d.ts`；新測試 `tests/api/test_giant_api.py` | `218edf798` |
| 前端邏輯 | 新 `battle/footprint.ts`（佔格、點格找單位、部位、`hit_tile` 定位、部位格狀態）；點巨型頭目任一格不跳選單、由那一格推 `target_part`；打不到的部位格提示原因、不送出；滑過預覽帶部位、資訊卡多一行；目標高亮蓋 3×3；演出位置吃 `hit_tile`；`api/types.ts` 窄化 `attack_rolled.hit_tile`；新測試 `footprint.test.ts`、`gb4aGiantClick.test.ts` | `cdb4be937` |
| 文件與截圖 | 本報告、上手筆記（第一節加 `battle/footprint.ts` 一列、第四節第 175、176 點）、`docs/art/shots/gb4a/` 5 張 | 本報告的 commit |

## 2. 逐條驗收（8.1）

| # | 項目 | 證據 |
|---|---|---|
| 1 | API 欄位、原因中文、重產 | `tests/api/test_giant_api.py` 7 項全過（9 格依 (y, x)、1 格單位沒有欄位且 `exclude_none` 不輸出、三個部位的地圖格、霧鎖真人沒有 tiles、核心「呼吸階段才露出」、退回通用字、`skill_reasons` 冒煙）；`tests/api/` 全部（含 `test_openapi_snapshot.py`）＋`tests/test_architecture.py`＋`tests/sim/test_skill_ratio*.py`：**1312 passed, 1 skipped**（`-n 8`，結束碼 0）；`ruff check`、`ruff format --check`、`mypy`（648 檔）、`lint-imports`（14 kept）結束碼 0 |
| 2 | `footprint.ts`，5 份點擊找單位、4 份 ID → 位置換掉 | 見第 4 節呼叫點表；`footprint.test.ts`（佔格、occupies、找單位、nearestTile、partAtTile、giantPartStates、事件窄化、`hitLocator` 四種情況） |
| 3 | 點格選部位（不跳選單；前殼、已破、未露出＝本體；灰掉原因） | `gb4aGiantClick.test.ts`：9 格 × 普攻／瞄準單體的點擊表（18 列）、任何一格都不回 `part_menu`、範圍技不推部位、已破殼縫＝本體、第 2 階段核心可打、遠程射程原因、滑過預覽與資訊卡字、不在佔格／沒選項／不能行動時不作用。`pb1cPartClick.test.ts` 原表未改、全過 |
| 4 | 範圍與高亮 | 目標高亮：`targetTiles`（瞄準）、`useHighlights` 的普攻目標、隊友指令、召喚物指揮、灌注、滑過紀錄都改 `unitTiles`（測試：`targetTiles` 列出 9 格）。範圍預覽、延遲落點、熔心爆本來就照伺服器的 `affected_tiles`／`charges[].tiles`（`telegraph.ts` 不用 `unit.pos` 推格，查過不必改） |
| 5 | 卡片錨點 | 資訊卡本來就錨在滑過的那一格（`cardPlacement(cardTile)`）；巨型頭目不開 `PartMenu`，所以沒有部位卡錨點的問題 |
| 6 | 測試 | 見上；前端事件窄化 `isAttackRolled`／`hitTileOf` 在 `footprint.test.ts` |
| 7 | 瀏覽器實測（熔心坑，1600×900、800×600） | 見第 3 節 |
| 8 | 三個結束碼 | `corepack pnpm -C client typecheck` **0**；`build` **0**；`test`（全量）**1 failed / 4577 passed**——唯一失敗是 `render/qIcon/qIconQi2d.test.ts`「主圖 24、40 只有第 6 節 19 招……」多出 `skill_heart_inhale`，是 GB-2b 改了吸氣的形狀（範圍光環 4）讓圖示變了，**不是本段造成**（本段沒動 `render/` 與任何夾具）。本段相關的 `src/battle`、`src/screens`、`src/ui` 共 142 檔 1755 項全過 |

## 3. 瀏覽器實測（Claude 內建瀏覽器、`?mute=1`；自己開的 `trpg serve` 8765＋暫存 vite 設定 5199，用完以 PID 結束、刪掉暫存設定）

進場方式見上手筆記第 176 點（開發 Boss：熔心坑、灰燼之心中心 (5, 3)）。主角拿火槍（遠程）站 (3, 11)：

- 伺服器回應：灰燼之心 `footprint: 3`、9 格；部位 tiles 對（核心 (5, 3)、殼縫 (4, 3)／(6, 3)、噴口北排）；普攻的 `part_options`＝核心「呼吸階段才露出」、殼縫與噴口「那一格超出射程」。
- 目標紅框蓋住整個 3×3（`01`）。
- 滑過噴口格：資訊卡「部位：熔岩噴口・打不到：那一格超出射程」，不預覽（`01`）。
- 滑過核心格：「部位：核心・呼吸階段才露出（點這一格＝打本體）」，左上預覽是打本體（命中 95%）（`02`）。
- 點噴口格：不送出，上方提示「打不到熔岩噴口：那一格超出射程」（`03`）。
- 點前殼 (4, 4)：送出普攻（本體），事件 `attack_rolled.hit_tile` = (4, 4)（`04`）。
- 熔岩濺落：灰燼之心蓄力時事件 `anchor_target_id`＝賽倫 (8, 11)（離最近佔格 9，比主角的 8 遠），落點預告格畫在 (8, 11) 一帶（`04` 右下紫格）。
- 800×600：畫面自動縮到 53%，點格換算照常（`05`）。

**實機沒做到的（只靠 vitest）**：近戰站殼縫旁點殼縫（南邊入口 (3, 10) 被餘燼蜥堵住、一輪內走不到）；第 2 階段點核心。浮動卡「滑進→捲到底→釘住→關閉」：本段沒有新的浮動卡元件（只在既有格子資訊卡多一段），沒有重跑這套，格子資訊卡的點擊釘住在實測中照常。

截圖（`docs/art/shots/gb4a/`，5 張、jpg、最大 60 KB）：`01-vent-out-of-range-1600.jpg`、`02-core-hidden-body-preview-1600.jpg`、`03-vent-click-hint-1600.jpg`、`04-splash-farthest-after-attack-1600.jpg`、`05-overview-800.jpg`。內建瀏覽器的截圖是 1600×900 畫面縮成 800×450（不是 DPR 1 原尺寸）；巨型頭目仍畫成 1 格（繪製是 GB-4b）。

## 4. 改了哪些呼叫點

| 檔 | 處數 | 內容 |
|---|---|---|
| `src/trpg/engine/view.py` | 3 | 欄位宣告與投影（`UnitView`／`PartView` 就定義在這裡，API 直接用；見待決 1） |
| `api/presenter.py` | 1 | `part_options` 原因字（新 `_part_reason_zh`、`_exposed_phase_zh`） |
| `api/skill_reasons.py` | 2 | 排序 `unit_dist`；格子型技能試 `nearest_tile` |
| `api/hidden_info.py` | 1 | 「和觀看者相鄰」改 `adjacent` |
| `sim/skill_ratio.py` | 1 | 範圍到目標的距離 `dist_to` |
| `battle/tileClick.ts` | 3 | 巨型頭目點格（`giantClick`）、指揮召喚物找敵人 `occupies`；新匯出 `giantAimAt`、`hoverActionAt` |
| `battle/actions.ts`、`composite.ts`、`orders.ts`（3）、`summonControl.ts`（2）、`pathPreview.ts`、`targeting.ts`（2） | 10 | 點格找單位、合法目標格 → `footprint.ts` |
| `battle/vfx.ts`、`skillSequence.ts`、`feedback.ts` | 3 | ID → 位置改 `hitLocator` |
| `battle/scenePreview.ts` | 1 | 衝撞路徑命中率標在巨型單位每一格 |
| `battle/tileInfo.ts` | 1 | `TileSectionKind` 加 `"part"` |
| `screens/battle/useTileInteraction.ts` | 2 | `unitAt`、資訊卡的部位一行 |
| `screens/battle/useHighlights.ts` | 4 | 滑過動作（帶部位）、普攻目標格、滑過紀錄的單位格 |
| `api/types.ts` | 1 | `AttackRolledEvent`、`isAttackRolled` |

**刻意不換**（仍讀 `u.pos`＝中心格）：`drawModel.ts`、`specials.ts`（頭目演出、`part_break` 落點）、`impact.ts`、`rgMarks.ts`、`telegraph.changePos`（`unit_id` 的變化）、`playback.ts`、`facing.ts`、`zones.ts`、`previewText.ts:161`（高度：佔格同高）、`useBattleData.ts:153`、投擲／互換的單位格（巨型單位不能被舉、換位）——都是「畫在哪裡」，屬 GB-4b 的繪製與演出起點；`ui/PartMenu.tsx` 不用改（巨型頭目不開選單）。

## 5. 不變比對、快照

- 本段沒動引擎規則、沒升 `LOG_FORMAT`；視圖多兩個選填欄位（null 時照舊輸出 null）。沒有跑 46 場不變比對（規格 8.1 未要求）。
- OpenAPI 快照照重產（`UnitView`、`PartView` 各多欄位），`test_openapi_snapshot.py` 過。CLI 快照不涉及。前端夾具沒動。

## 6. 新增 `# noqa`

無。

## 7. 規格沒寫到、採保守做法

1. **點到「露出、沒破、但打不到」的部位格**（例：近戰點噴口、遠程射程不夠）：不送出、提示「打不到{部位}：{原因}」；規格只列前殼、已破、未露出＝本體，這種情況不自動改打本體（避免玩家以為打了部位）。
2. **滑過打不到的部位格不要預覽**（伺服器會拒絕那個 `target_part`）；原因寫在格子資訊卡新的一段（`kind: "part"`，收起資訊卡時也留著）。
3. **核心未露出的階段名**：取「目前階段之後、部位 `exposed_in` 裡第一個」的階段名；只對巨型頭目換字，霧鎖真人（1 格）照舊「這個階段還沒露出」（PB-1 測試不變）。
4. **演出落點**：有 `hit_tile` 的命中判定之後，同一步裡那個目標的位置一律是那一格；沒有命中判定的傷害打巨型單位用「離來源最近的佔格」；完全沒有來源（持續傷害）用中心格。
5. **`giantPartStates`**（部位格標示的資料）先做好、有測試，但沒有接到 `Highlights`（`Highlights` 型別在 `render/`，GB-4b 接）。

## 8. 影響

- 前端讀 `UnitView.footprint`／`tiles` 為選填，舊回應（沒有欄位）照 1 格處理。舊紀錄、存檔不受影響（沒改引擎）。
- 美術第 9 節的短字（「要遠程攻擊才打得到」「射程不夠」「看不到這一格」）**沒有套用**：8.1 寫「原因同 `reason_zh`」，目前提示與資訊卡照伺服器的引擎字（見待決 4）。

## 9. 平衡疑慮

無新增（本段不改規則與數值）。

## 10. 待 PM 決定

1. `UnitView`／`PartView` 定義在 `src/trpg/engine/view.py`，派工範圍只列 `src/trpg/api/`；為了加欄位動了 `engine/view.py`（欄位＋投影，不碰規則）。請確認可接受。
2. 核心「呼吸階段才露出」只套巨型頭目；霧鎖真人的長劍、氣海要不要也改成寫階段名（會改 PB-1 的字與 `test_parts_api.py`）？
3. 露出、沒破、但打不到的部位格：點了＝提示不送出（保守）；要不要改成「點了＝打本體」？
4. 美術第 9 節的短字和引擎 `PART_REASON_ZH`（「只有遠程才打得到」「那一格超出射程」「看不到那一格」）不同。要改引擎字（同時改到選單、`IllegalActionError`、1 格頭目）、還是只在 GB-4b 的格子標示用短字？
5. 殼縫「近戰打這裡算從背後」需要 `PartView` 帶 `counts_as_behind`（目前 API 沒有）；建議 GB-4b 開頭加一個選填 `behind: bool | None`。
6. 全量 vitest 唯一失敗 `qIconQi2d.test.ts`（`skill_heart_inhale` 主圖因 GB-2b 改形狀而變）是 main 既有的，需把它加進該測試的 `CONTENT_CHANGED`（`render/`，本段不能動）；誰收？
7. 實機沒走到近戰點殼縫、第 2 階段點核心（只靠 vitest）；要不要 GB-4b 用開發頁或固定場面補拍？
8. 截圖是內建瀏覽器縮圖（1600 畫面存成 800×450），不是 DPR 1 原尺寸；GB-4a 是邏輯段，是否可接受？
9. 實測時主控台有 React `flushSync was called from inside a lifecycle method`（`BattleScreen`）與幾個 404，未查是否本段之前就有。

## 開發 PM 裁定（2026-11-14）

- 接受。全量 vitest 唯一失敗 `qIconQi2d` 是 GB-2b 造成，交 GB-2d 修。
- 待決 1：接受動 `engine/view.py`（只加欄位與投影）。
- 待決 2：「呼吸階段才露出」只套巨型頭目，霧鎖真人不改。
- 待決 3：照目前（露出、沒破、打不到的部位格點了只提示不送出）。
- 待決 4：引擎 `PART_REASON_ZH` 不改；美術第 9 節的短字只用在 GB-4b 的格子標示。
- 待決 5：GB-4b 開頭在 `PartView` 加選填 `counts_as_behind`。
- 待決 7：近戰點殼縫、第 2 階段點核心的畫面在 GB-4b 用開發頁或固定場面補拍。
- 待決 8：GB-4a 是邏輯段，縮圖截圖可接受；GB-4b 起照 DPR 1。
- 待決 9：`flushSync` 警告與 404 在 GB-4b 開工前查是否既有。
- 待決 10：`giantPartStates` 由 GB-4b 接到 `render/` 的 `Highlights`。
