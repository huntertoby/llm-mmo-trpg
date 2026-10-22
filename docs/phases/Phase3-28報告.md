# Phase 3-28 完成報告：介面小修（累積清單＋單場戰鬥開局同步＋屬性配點版面）

> 實作者：implementer（sonnet）。規格：`docs/phases/Phase3計畫.md` 第 30 節，加上 PM 追加的第 7 項（屬性配點面板版面）。
> 分支：`worktree-agent-a21c6bb9de490f0e7`（從 main 的 `26e939c` 分出），未 push、未合併。

## 1. Commit 列表

| commit | 內容 |
|---|---|
| `a475302` | 後端：`POST /api/battles` 與 `/api/gear/check` 接受 `weapon`＋`keywords`／`dev_pack`（`hero_build` 改選填，三擇一）；`roguelite.progress.hero_spawn` 抽出共用；OpenAPI 重產；屬性配點版面修正（CSS＋元件）也在這個 commit |
| 下一個 | 前端：共用 `StartPicker`；首頁單場戰鬥、一輪開局、技能工坊試玩、裝備測試都改用它；`?dev=1` 才有起始包 |
| 下一個 | 符文引爆特效、圖例出口／守點、工坊換骨架頁內確認、技能列捲動 |
| 其後 | 存檔列表不再顯示 build 名（流派名）；測試 |
| 最後 | 截圖；技能列提示行不被壓縮；本報告 |

（以 `git log --oneline 26e939c..HEAD` 為準。）

## 2. 驗收逐條

| # | 項目 | 結果 | 證據 |
|---|---|---|---|
| 1 | 單場戰鬥開局同步成 #36 | 通過 | 首頁「單場戰鬥」改為「起始武器＋2 個關鍵字（各池給 1 招）」，元件是 3-24b2 的開局畫面抽出的 `client/src/run/StartPicker.tsx`（一輪開局也改用同一個，沒有另寫一套）。後端 `SessionStore._start_setup`：主角用 `new_keyword_run`／`new_dev_run` 的主角（名稱「冒險者」）、標準隊友補到 3 人。pytest `tests/api/test_battle_start_api.py`（9 個：主角與一輪開局一致、起始包、5 種不合法輸入 422、gear check、回應不含任何 build 名／起始包標籤）；vitest `startFlow.test.ts`（`startBody`、`isDevMode`）、`workshop.test.ts`（試玩請求送武器＋關鍵字、不送 `hero_build`）。截圖 `img/3-28-single-start.png` |
| 1b | `?dev=1` 才有起始包 | 通過 | `DevPackSelect` 在 `picker.dev` 為假時直接回傳 null；`isDevMode` 測試；截圖 `img/3-28-dev-mode.png`（網址帶 `?dev=1` 才出現「開發者起始包」面板）；一般網址的截圖沒有 |
| 1c | 舊 build 不出現在玩家介面 | 通過 | 見第 3 節；API／CLI 的 `--build`／`hero_build` 保留給回歸測試 |
| 2 | 全面檢查殘留流派名稱或舊選單 | 通過 | 見第 3 節 |
| 3 | 符文引爆特效 | 通過 | `vfx.ts` 新增 `StepVfx.blasts`（事件 `rune_removed` 且 `reason=detonated`，在符文格、元素色；標籤符文用預設色），`vfxEffects.blastEffect` 沿用既有爆發型，`BattleRenderer.playVfx` 播放。vitest `vfx318b.test.ts` 3 個新案例（引爆才產生、到期不產生、速度縮放、`isEmptyVfx`）。截圖 `img/3-28-rune-burst.png`（雷紋刻印後施放符文爆裂，符文格迸出電光；戰鬥紀錄顯示 4 個符文被引爆）。截圖用腳本把戰鬥請求換成刻印型回歸 build（只在截圖的頁面內，未進 repo） |
| 4 | 工坊換骨架改頁內確認 | 通過 | `StepView.tsx` 移除 `window.confirm`：改在頁內顯示「換骨架會清掉其他已填的欄位……確定要換嗎？」＋「確定換骨架／取消」（沿用既有 `ws-warning` 樣式）。無其他 `window.confirm`（`grep` 全 client 零筆）。未寫元件測試（專案沒有 DOM 測試環境），邏輯沿用 `changeSkeleton` 不變 |
| 5 | 圖例加出口格與守點格 | 通過 | `battle/legend.ts` 的 `BASE_LEGEND` 加「出口格『出』」「守點格『守』」，顏色與渲染器共用 `HIGHLIGHT.exit`／`HIGHLIGHT.point`；vitest `legend328.test.ts`；截圖 `img/3-28-legend.png` |
| 6 | 技能列招數多時可捲動 | 通過 | `.skill-bar` 改 flex 直向，`.skill-row` `overflow-y: auto`（技能卡浮層是 skill-bar 的直接子元素，不會被裁掉）；提示行 `flex: 0 0 auto`。1600×900 下複製 14 個技能鈕：`row.scrollHeight 204 > clientHeight 138`，頁面 `scrollHeight 900 = innerHeight`（無頁面捲軸）。截圖 `img/3-28-skillbar.png`（截圖的多出來的鈕是用腳本複製的，因為遊戲內開局只有 2 招） |
| 7 | 屬性配點面板版面（PM 追加） | 通過 | ①標籤 `white-space: nowrap`、固定欄寬；②屬性列改 grid（標籤｜−｜數值｜＋），「最大 HP ＋N HP」移到下一行（第 2 欄起），不再擠同列；③標題改 flex、與「剩餘 0／4 點」有間距。截圖 `img/3-28-attr-800.png`、`img/3-28-attr-1600.png`（體質點了 1 點，顯示 HP 提示且各列對齊）。CSS 無單元測試（`?raw` 匯入在 vitest 取不到內容，已放棄），以截圖為證 |
| 8 | `check.py` 全過、`pnpm build` 成功 | 大致通過 | `corepack pnpm -C client build` 成功；`check.py` 只有 client test 在那一次執行失敗 1 個（疑為負載造成），單獨重跑兩次全過，詳見第 6 節 |

## 3. 第 2 項：流派名稱／舊選單檢查結果

| 地方 | 發現 | 處理 |
|---|---|---|
| 首頁「單場戰鬥」的「主角 build」下拉（`StartScreen`） | 顯示 `builds.yaml` 的 16 個 build 名（位移流、火焰流…）與主題說明 | 改為武器＋關鍵字（共用 `StartPicker`）；起始包只在 `?dev=1` |
| 技能工坊「裝上試玩」（`TryoutPanel`） | 「主角 build」下拉（同上），並用 build 的技能清單當「要換掉哪一個技能」 | 改為 `StartPicker`；「要換掉的技能」改用開局給的 2 招；法力提醒改用所選武器的法力（`manaNote`）；`?dev=1` 可勾「改用起始包」（此時不列可替換技能，只能加在空格） |
| 裝備測試分頁（`GearScreen`） | 「主角 build（武器名）」下拉 | 改為 `StartPicker`；`gearCheck` 送武器＋關鍵字（後端 `GearCheckRequest` 新增欄位）；`?dev=1` 可改用起始包 |
| 靶場 | 靶場是工坊／裝備測試的地圖，沒有自己的選單 | 隨上兩項改完即無流派名 |
| 一輪各畫面（開局、升級、營火、結束、主角面板） | 開局已在 3-24b2 完成；其餘畫面沒有 build 名 | 無需處理 |
| 一輪「繼續一輪」存檔列表（`start_label`） | 舊的 build 開局存檔會顯示 build 名（流派名） | 改為「回歸測試開局・武器名」；測試 `test_save_list_has_build_name_and_victory` 更新為不含 build 名 |
| 戰鬥畫面的主角名 | 用 build 開局時主角名為「位移流英雄」等 | 只有 API `hero_build`（回歸／開發用）才會出現；新開局一律「冒險者」；測試斷言新開局回應不含任何 build 名與起始包標籤 |
| 圖例 | 沒有流派名 | 無需處理 |
| CLI `--help` | `--ally-build`、`--build`、`sim matrix --builds` 的說明寫「build 英雄」「回歸範本 build（開發用）」，沒有流派名稱 | 保留（開發用、說明已標明）；沒有改 |
| `GET /api/builds`、`api.builds()`（client 的函式） | API 仍回傳 build 名（開發用）；client 已沒有任何畫面呼叫 | API 保留；client 函式與型別留著未刪（待 PM 決定，見第 5 節） |
| 程式碼註解、`content/` 註解與 README | 出現「遊戲不定義流派」的說明文字 | 不是玩家看得到的畫面文字，保留 |
| `content/sim/builds.yaml`、`dev_starters.yaml` 的 `label_zh` | 流派名資料本身 | 保留（開發／回歸用）；只透過 `?dev=1` 的起始包選單顯示起始包標籤 |

## 4. 設計摘要

- **API**：`CreateBattleRequest`、`GearCheckRequest` 的 `hero_build` 改選填；新增 `weapon`、`keywords`、`dev_pack`；`hero_build`／`weapon`＋`keywords`／`dev_pack` 三擇一，其他組合 422。主角以 `hero_spawn(library, run)`（由 `battle_setup` 抽出，行為不變）建立，隊友是 `builds.yaml` 的標準隊友（共 3 人），規則包加入生成技能。
- **OpenAPI**：`client/openapi.json`、`client/src/api/schema.d.ts` 已重產。
- **前端**：`run/StartPicker.tsx`（`useStartPicker`、`StartPickerView`、`DevPackSelect`）；`startFlow.ts` 新增 `startBody`；`tryout.ts` 的 `TryoutChoice.buildId` 改為 `start`。`TryoutPrefs.build` 欄位保留（舊的瀏覽器暫存仍可讀，不再使用）。
- 沒有改存檔格式、`LOG_FORMAT`、引擎。

## 5. 新增的複雜度 noqa

無。

## 6. 驗證

- 相關測試：`tests/api/test_battle_start_api.py`、`test_run_autosave.py`、`test_run_start_api.py`、`test_runs_api.py`、`test_gear_api.py`、`test_routes.py`、`test_openapi_snapshot.py` 通過；vitest（run、workshop、battle、ui）通過。
- ruff、ruff format、mypy 通過。
- `corepack pnpm -C client build`：built。
- 完整 `uv run python scripts/check.py`（只跑一次）：ruff、format、mypy、lint-imports、pytest、client install、typecheck 全部通過；client test 有 1 個測試在與平行 pytest 同時執行時失敗一次（未記下測試名，疑為負載造成的逾時），隨後單獨重跑 `vitest run` 兩次皆為 63 檔 663 個全過。
- 截圖伺服器用 `trpg serve --port 8131`（沒有動 8000）；以 headless Chrome＋CDP 腳本截圖（腳本在暫存區，未進 repo）。

## 7. 待 PM 決定

1. **`api.builds()`／`BuildSummary`（client）與 `GET /api/builds`**：client 已沒有畫面使用，API 仍在（開發／回歸）。是否移除 client 端的函式與型別？我保守地留著。
2. **工坊試玩選了開發者起始包時**不列「要換掉哪一個技能」（起始技能由後端決定、前端看不到 ID），只能加在空格。需要時可讓起始包預覽回傳技能卡。
3. **工坊／裝備測試的 `gear/check` 用種子 0 建立主角**（裝備合法性不依種子）；若某武器＋關鍵字在種子 0 湊不到起始技能而實際種子可以（或相反），檢查結果可能不同。機率極低，未處理。
4. **開局選擇不再存進工坊的瀏覽器暫存**（原本記 build）；每次進工坊要重選武器與關鍵字。需要記住的話可加。
5. **技能列溢出**只在按鈕排捲動；遊戲內開局只有 2 招，目前要升級很多次才會出現捲動。截圖用複製按鈕模擬。
6. **屬性配點與技能列 CSS 沒有自動化測試**（`?raw` CSS 在 vitest 取不到內容）；以截圖驗證。
7. 符文引爆特效的爆發大小（強度 1.3、尺度 1.2）是初值，請 PM 看過截圖後決定要不要調。
