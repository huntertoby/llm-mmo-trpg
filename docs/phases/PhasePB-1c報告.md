# Phase PB-1c 完成報告｜部位系統段 1c：前端（占位、接口先做）＋需要的 API 欄位

> 規格：`docs/phases/PhasePB-1計畫.md` 第 7 節（R1～R9 使用者「照建議」、T14～T16 照建議）；美術 `docs/art/頭目部位-移植需求.md` 屬 PB-1c 的部分（1.1、1.4、2.1、2.2、3.1～3.3）；PB-1a 報告末節開發 PM 裁定第 3 點。
> 基準：本機 main（含 QI-5，`9e8963a1` 是祖先）。不做 PB-1e（頭頂部位小格、亮起、正式破壞演出）；`render/battle/unitLayer.ts`、`BattleRenderer.ts` 沒有動。

## 1. 做了什麼

| commit | 內容 |
|---|---|
| `48c565d8` API | 引擎投影 `UnitView.parts: tuple[PartView, ...] \| None = None`（`id`、`name_zh`、`hp`、`max_hp`、`broken`、`exposed`、`reach`、`break_lines_zh`；依部位 ID）；API 層 `traits_view` 用 `narrative.parts.break_lines_zh` 填「破掉會」；`BattleResponse.part_options: tuple[PartActionOut, ...] \| None = None`（`type`＋`skill_id`＋`target_id`＋`options[part_id, name_zh, ok, reason_zh]`，來自 `engine.parts.part_targets`）；`api/hidden_info.py` 登記：看不到資訊時部位 `hp`／`max_hp` 為 null、`part_damaged` 的 `hp_before`／`hp_after` 為 null（傷害量照常）。`tests/api/test_parts_api.py` 10 項。`client/openapi.json`、`schema.d.ts` 重產 |
| `54979711` 圖示 | `render/qIcon/bossParts.ts`：拂塵、氣海（第 2 版，照 `bossParts.js` 逐行搬）、長劍＝`COND.wielding_weapon`、從背後＝`COND.from_behind`、本體＝霧鎖真人小頭像（需求 1.4 全部 6 步）、`grayIcon`；`qIconBossParts.test.ts` |
| `bcb67ef1` 選單與接線 | `ui/PartMenu.tsx`、`ui/PartBar.tsx`、`battle/partMenu.ts`；`battle/tileClick.ts` 的 `part_menu`；`useTileInteraction`／`BattleScreen`／`BattleCanvas`（`aria-expanded`）接線；`floatPlacement` 加 `{ kind: "sides" }`、`sidePlacement`；`stageLayout.tileBox`；`UnitInfo.UnitParts`；`previewText.partPreviewLines`；`api/types.ts` 窄化 `part_damaged`／`part_broken`／`skill_sealed`；CSS `.part-menu*`、`.part-bar*`；測試 `pb1cPartClick.test.ts`、`ui/partMenu.test.ts`、`previewText.test.ts` 加部位列、`floatCardLayout.test.ts` 加 sides |
| `23142d37` 破壞演出與紀錄 | `specials.ts` 的 `part_break`（那一下頭目受擊升級成重擊片段＝重擊白閃、停頓 70）、`impact.ts` 一次重擊微震、`feedback.ts` 浮動字「{部位} 破！」；紀錄 `part_damaged` tone `damage`、`part_broken` 新 tone `break`（紅叉＋粗體）；`pb1cPartBreak.test.ts` |
| `de2b4be6` 小修＋開發頁＋截圖 | 選單開著時不顯示格子資訊卡（會蓋住選單）、選單寬 240、內距讓開四角飾件；開發頁 `client/dev/bossparts-gallery.html`（`src/dev/bossPartsGallery.ts`）；截圖 8 張 |
| （本報告與上手筆記） | `docs/phases/PhasePB-1c報告.md`、`docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節加兩列、第二節加第 8 點、開發入口加開發頁、第四節 66～68、第五節測試列） |

派工另加的五點：
1. `floatPlacement(anchor, size, vp, align, margin, "above", { kind: "sides", gap })`：上方放得下＝置中、下緣離格子 8；放不下退回右邊、再不行左邊（不翻到下方）。只有 `PartMenu` 在 < 1000 寬時傳；≥ 1000 用 `sidePlacement`（右邊、放不下左邊）。不傳第 7 參數的呼叫者：測試用改前的函式逐字抄一份，對 8×6×3×2×3 組輸入逐一比對相同。
2. 每列名稱左邊 20px 部位圖示；本體列是小頭像（取代米白人形；沒有外觀時才退回人形）。
3. `.part-bar` 米白 `#f2e6c8`、空槽 `#4a4252`、已破壞 `#5a1a1a`＋紅「×」`#ff5a4a`（外框色襯邊）、未露出 `#0e0e14`；選單圖示上的紅叉照樣張 `drawMenu` 用 `#ff6a5a`。
4. 頭目資訊被隱藏：見上表 API 列；後端測試 `test_hidden_master_hides_part_numbers_in_view`、`..._in_events_but_keeps_the_amount`、`test_visible_master_keeps_part_numbers`。
5. 破壞演出照占位，`unitLayer.ts` 沒動（`pb1cPartBreak.test.ts` 也掃原始碼擋）。

## 2. 逐條驗收（規格第 7 節）

| # | 項目 | 證據 |
|---|---|---|
| 1 | API 欄位、OpenAPI | `tests/api/test_parts_api.py`（`UnitView.parts`、排序、露出、破掉、`break_lines_zh`；`part_options` 只對真人、原因中文、去重；帶 `target_part` 的動作打中那個部位；預覽的 min／max 都有 `part_damaged`）；`test_openapi_snapshot.py` 過 |
| 2 | 點擊（R1、R6） | `battle/pb1cPartClick.test.ts`：沒有 `part_options` 時普攻／瞄準照舊；普攻、瞄準單體點有部位頭目 → `part_menu`；範圍技照舊送出；沒部位的單位照舊；選單開著再點同一個頭目＝本體、點別處只關選單；Shift 照舊釘卡。`tileClick.test.ts` 原表格沒改、照過 |
| 3 | 選單 | `ui/partMenu.test.ts`（本體第一且預設選中、照部位 ID、灰掉寫原因、從背後加背刺小圖、已破壞打叉、看不到資訊不寫數字、方向鍵循環、`role=menu`）；實機見第 4 節 |
| 4 | 角色卡 | `UnitParts`（`partMenu.test.ts`）；截圖 4 |
| 5 | 預覽 | `previewText.test.ts`「PB-1c」4 項（還剩 12、6～12、會打破、可能打破、隱藏時不寫）；實機 1600 預覽框出現「會打破拂塵」 |
| 6 | 破壞演出 | `pb1cPartBreak.test.ts`；截圖 5 |
| 7 | 紀錄 | `pb1cPartBreak.test.ts`「紀錄」：`logLines`／`groupLog` 不吞 `part_damaged`、`part_broken`，tone `break` |
| 8 | 測試 | 上列；`floatCardRule.test.ts`、`sharedPopup.test.ts` 照過、白名單沒加 |
| 9 | 瀏覽器實測 | 第 4 節 |
| 10 | 截圖 | 第 5 節（8 張） |
| 11 | 結束碼 | 第 6 節 |

## 3. 舊測試、快照、雜湊

- **沒有改任何既有測試的斷言**：`floatCardLayout.test.ts` 只改 import（多 `sidePlacement`）＋新增一個 describe；`previewText.test.ts` 只改 import（多 `partPreviewLines`）＋新增一個 describe。為了不改 `specials.test.ts` 鎖住的 `STOP_MS`（5 個鍵逐字比對），部位破壞的停頓另放 `PART_BREAK_STOP_MS`、經 `specialStopMs()` 取。
- 沒有重產任何雜湊、快照、夾具（`render/__snapshots__`、`qi2dBaseline`、`qi3bStatusBaseline`、client fixtures 都沒動）。
- OpenAPI／`schema.d.ts`：只多 `PartView`、`PartReach`、`PartOptionOut`、`PartActionOut`、`UnitView.parts`、`BattleResponse.part_options`；拿掉這幾個欄位就回到原檔。

## 4. 瀏覽器實測（6.5.1；1600×900 與 800×600）

**怎麼進場**：自己的 `trpg serve --port 8793`（`TRPG_DEV_ROUTES=1`、存檔在 scratchpad）＋無頭 Chrome（`--mute-audio`，網址 `?dev=1&mute=1&anim=0.1`，CDP 9341）。雲頂觀只能經工坊試玩開（規格寫的 `WorldScreen` `&boss=` 開發參數**不存在**），所以照 OCL-1c 的做法：`POST /api/battles {map_id: cloud_summit, seed: 1, hero_build: build_ranged, custom_skills: [skill_piercing_shot 換 id], replace_skills: [skill_piercing_shot]}`，照固定的 12 個動作推到第 4 輪（主角 (9,2)、真人 (9,1) 鎖霧、拂塵剩 3）；頁面從開發選單「一鍵開局」進，CDP `Fetch` 把那一次 `POST /api/battles` 的回應換成這場的 `GET`。之後點頭目、選部位、攻擊都是頁面自己送到真伺服器。

| 檢查 | 1600×900 | 800×600 |
|---|---|---|
| 點頭目跳選單、`aria-expanded="true"`、格子資訊卡不疊 | ✓（右邊，`data-side=right`） | ✓（**左邊**：頭目在第 2 排，上方放不下 → 退回左右；不蓋左 HUD 欄） |
| 選單內滑過「破掉會」→ 說明卡出現 → 經橋接區滑進卡片仍開著 | ✓ | ✓ |
| 卡內捲到底 | 內容只有一行（scrollHeight 28＝clientHeight），沒有可捲的，捲動後仍開著 | 同左 |
| 點卡片 → 釘住（`.float-card.pinned`），選單仍開著 | ✓ | ✓（截圖 8） |
| Esc 關閉 | ✓ 說明卡關了；**選單也一起關**（待決 4） | 同左 |
| 選單內滑過拂塵列 → 預覽多「會打破拂塵」 | ✓ | ✓ |
| 方向鍵 | ✓（↓ 從拂塵循環回本體） | ✓ |
| 選「高處狙擊」瞄準 → 點頭目開選單 → Esc：選單關、仍在瞄準（「高處狙擊 點選格子上的目標」還在）；再 Esc 才取消瞄準 | ✓ | ✓ |
| 選單點拂塵 → 送 `target_part: "whisk"`、拂塵破、紀錄與浮動字 | ✓（截圖 5） | ✓ |
| 破後選單：拂塵灰＋紅叉、「已破壞」 | ✓ | ✓ |
| 選單開著時再點同一個頭目 → 選單關、送出不帶 `target_part` 的普攻（網路紀錄） | ✓ | ✓ |
| 看不到資訊（造資料：包 `window.fetch` 把真人換成伺服器隱藏時的欄位）：角色卡、選單不寫部位數字 | ✓（截圖 6） | 未拍 |

開發頁量測（`bossparts-gallery.html`，`body.dataset.check`）：本體小頭像各大小**不帶外框**的半透明像素 0（16／20／24／32 × res 1、2 全部）；方眼實心 `#1d1a22` 20px 真 1 倍 8 px、24px 12 px（2×3×2）、20px res 2 24 px（3×4×2），左右鏡像；外接框水平置中（偏移 0）；20px 真 1 倍外接框 12×15（寬 12 < 14，見待決 1）。

## 5. 截圖（`docs/art/shots/pb1c/`；占位，待美術移植 PB-1e）

| 檔案 | 實機／開發頁 | 看到的 |
|---|---|---|
| `docs/art/shots/pb1c/1-menu-1600.jpg` | 實機 1600 | 選單在頭目右邊、四列（本體頭像、氣海灰＋背刺小圖＋原因、長劍未露出、拂塵 3/26）；左上預覽「會打破拂塵」 |
| `docs/art/shots/pb1c/2-menu-800.jpg` | 實機 800 | 頭目在最上面兩排 → 選單退回左邊、不蓋 HUD 欄 |
| `docs/art/shots/pb1c/3-menu-rows-1x.png` | 實機 1600 | 破壞前／後的選單真 1 倍＋圖示欄最近鄰 ×3（可打、從背後、未露出、已破壞紅叉） |
| `docs/art/shots/pb1c/4-card-bars.png` | 實機 1600 | 角色卡部位條：完好米白、破壞中（3/26 灰紫空槽）、未露出（黑）→ 破後暗紅＋紅「×」 |
| `docs/art/shots/pb1c/5-break-1600.jpg` | 實機 1600（`anim=0.1` 連拍） | 出手前、重擊白閃、「拂塵 破！」、字往上飄 |
| `docs/art/shots/pb1c/6-hidden-no-numbers.png` | 實機 1600（造資料） | 看不到資訊時角色卡與選單都沒有部位數字 |
| `docs/art/shots/pb1c/7-icons-gallery.png` | 開發頁 | 五種圖示 16／20／24／32 × res 1、2（真 1 倍＋最近鄰 ×4、灰掉、已破壞） |
| `docs/art/shots/pb1c/8-hint-pinned-800.jpg` | 實機 800 | 選單內「破掉會」說明卡釘住 |

**實機未看**：800 寬「選單放頭目上方」（雲頂觀頭目只站最上面兩排，實機到不了；由 `floatCardLayout.test.ts` 鎖）；800 的看不到資訊。

## 6. 結束碼（交件前）

| 指令 | 結束碼 |
|---|---|
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（313 檔、4044 項） |
| `corepack pnpm -C client build` | 0 |
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0 |
| `pytest tests/api`（全部，`-n 8`）＋`test_view`、兩個部位引擎測試、`test_architecture` | 0（1149 passed、1 skipped；在 `48c565d8`） |
| `pytest tests/api/test_openapi_snapshot.py test_parts_api.py test_hidden_info.py test_client_fixtures.py`（最後） | 0（25 passed） |

自己啟動的程序：`trpg serve`（8793）、vite（8794，只為開發頁）、無頭 Chrome（CDP 9341，`--user-data-dir` 在 scratchpad `pb1c/chrome-ud`，每個腳本結束用 `Browser.close`）。都已關，三個埠沒有監聽。沒跑 `scripts/check.py`、沒跑模擬、沒 push。

## 7. 規格沒寫到、採保守做法的地方

1. `part_options` 不掛在 `legal_actions` 的動作物件上（動作是引擎模型、`extra=forbid`，送回去會壞），改成 `BattleResponse` 旁邊一份清單，用 `type`＋`skill_id`＋`target_id` 對。
2. 選單開著時點別的格子：只關選單、不行動（避免誤走、誤打）。
3. 選單開著時格子資訊卡不顯示（800 寬時會整張蓋住選單）。
4. 部位最大血量：開場時算一次沒存，投影時用目前最大 HP 重算、和目前血量取大的。
5. 浮動字的時間：照既有回饋在這一步畫完結果後浮出，比重擊白閃晚約 0.2 秒（占位）。
6. 本體列在看不到資訊時畫黑條、不寫數字；「未露出」字樣在看不到資訊時仍寫（露出與否只跟階段有關，階段本來就顯示）。

## 待 PM 決定

1. 小頭像 20px 真 1 倍不透明外接框 12×15：需求寫「≥14px」，高 15 符合、寬 12 不到（遊戲端紙娃娃頭髮比樣張窄）；要不要請美術看是否接受或調裁切。
2. 規格第 9 點的 `WorldScreen` `&boss=` 開發參數不存在，這次用工坊試玩＋CDP 換開戰回應；要不要排一個正式的開發入口。
3. 800 寬「放頭目上方」實機到不了（雲頂觀真人只站最上兩排）；目前只有單元測試證明。
4. 選單裡釘住的說明卡按 Esc 會連選單一起關（`Hint` 與 `usePopupMenu` 都聽 document 的 Esc）；要不要改成第一次只關說明卡（動共用元件）。
5. 看不到資訊的截圖是造資料（伺服器遮罩由 pytest 證）；要不要另排實機擺位。
6. 破壞浮動字比白閃晚約 0.2 秒；PB-1e 正式演出時一併對齊。
