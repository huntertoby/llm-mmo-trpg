# Phase PNL-1b 報告：公告板分頁版＋PNL-1a 美術驗收必修

依據：`docs/art/資訊面板-移植需求.md`（美術 PM 第九任，使用者「照建議」）表 6 的 PNL-1b 列；開發 PM 追加的 `docs/art/PNL-1a驗收.md` 必修 1、可修 1。起點 main `0d0f9c7f`，中途 `git merge main`（`15099a7d`，只多了 PNL-1a 驗收文件與截圖）。PNL-2／3／4 沒做；沒改 `content/`、成長／技能／整備面板、數值工坊、需求與計畫檔。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 後端：`SeasonInfoView` 加 `phase`（今天那段，名稱與說明分開）、`phases`（全部日程，`start_day`／`end_day`）、`milestones`（全部時間點，含已過的）、`refresh_time_zh`（「06:00」）；`BoardMilestoneView` 加 `id`、`kind`、`kinds`；`BoardWorldEventView` 加 `start_day`、`end_day`、`region`；`BoardBountyView` 的括號說明拆到 `status_note_zh`（`status_zh` 只剩「已被 ○○ 搶下」）。舊欄位（`phase_zh`、`upcoming`、`days_zh`、`next_refresh_zh`）都照舊 | `src/trpg/api/season_schemas.py`、`src/trpg/api/season_view.py`、`client/openapi.json`、`client/src/api/schema.d.ts`、`client/src/api/types.ts` |
| 公告板改成分頁：讀資料只在 `BoardPanel`（`useBoard`，在 `PanelTabs` 外面）；`BoardView` 是純畫面 | `client/src/world/BoardPanel.tsx` |
| 固定區（標題＋回到地點圖；守印人 1600 頭像 36＋對話泡、面板 < 560 標題旁 28＋一行台詞，滑過「守印人：全文」；「第 N 天」大字佔兩行＋日程標籤「第 a～b 天」＋「下一個 ［第 N 天］ 名稱（明天）」）、五個分頁（今日目標｜懸賞板｜賽季時程｜世界事件｜賽季頭目；記號：細框「完成／總條數」、金底「還能搶的條數」、進行中綠點、封印中金鎖）、懸賞五欄＋欄名列、世界事件塊＋世界變化清單、頭目「挑戰規則與評分榜」摺疊（挑戰鈕在摺疊外） | `client/src/world/BoardPanes.tsx` |
| `SeasonTimeline`（14 格 × 5 列：釘、天、階段、世界事件兩列）；「完整日程」摺疊 | `client/src/world/SeasonTimeline.tsx` |
| 純函式：新字、記號、下一個、（明天）／（N 天後）、`timelineLayout`（世界事件依開始天排，重疊的放下一列） | `client/src/world/boardTabs.ts` |
| 樣式（`ip-*` → `pnl-*`；另開一檔免得和 PNL-2 互改 `world-hud.css`） | `client/src/styles/world-panel-board.css`、`client/src/styles/index.css`（多一行 `@import`） |
| **PNL-1a 必修 1**：切分頁時捲動歸零（`resetScrollOnSwitch`） | `client/src/ui/PanelTabs.tsx` |
| **PNL-1a 可修 1**：固定區下緣漸隱 10 → 18px、上半實色 | `client/src/styles/world-hud.css` |
| `PanelTabs` 鎖高不超過捲動區（`cappedLock`）、寬度改變後等一格再量（見第 5 節第 1 點） | `client/src/ui/PanelTabs.tsx` |
| 測試：前端 22 項、後端 5 項 | `client/src/world/pnl1bBoard.test.ts`、`tests/api/test_board_pnl1b.py` |
| 上手筆記：第一節加一列、第四節第 89～93 點、第五節加一列 | `docs/dev/上手-前端戰鬥畫面與動畫.md` |

共用元件（PNL-1a 那批）的改動，全部向後相容：`PanelTabs.tsx` 新增匯出 `resetScrollOnSwitch`、`cappedLock`，`TabBar` 的 `onPick` 由 `PanelTabs` 包一層（先歸零再切頁）；量高度的結果在「最高那一頁放得下」時和以前完全一樣，放不下時才變矮（短的頁不再多一段空白）；`world-hud.css` 只改漸隱兩個值。`PanelKit.tsx`、`panelTabRules.ts` 沒動。公告板標題列沒有用 `PanelHead`（要在標題和按鈕之間插守印人一行），改在 `BoardPanes.tsx` 用同樣的 `pnl-head` class 自己排，免得改共用元件。

## 2. 第 5 節「要開發 PM 決定的事」本段怎麼做（照美術建議）

| # | 做法 |
|---|---|
| 1 | 後端分欄：`BoardBountyView.status_note_zh`（括號裡那句），前端放在狀態標籤的說明卡 |
| 7 | 劇情技能＝說書人（圖樣本身 17px，放大一號）、頭目解鎖＝金鎖、循環賽＝影子 `bar_Y`、沒對照＝沙漏 `t_telegraph`。`season.yaml` 的時間點沒有種類欄位（`content/` 不在本段），後端依 ID 前綴判斷：`story_skill*`／`boss*`／`league*`；名稱另寫到「劇情技能」的再加一個劇情技能（第 10 天＝金鎖＋說書人，和樣張一樣） |
| 8 | 沿用 PNL-1a：開著不重量；超過 `maxHeight` 在頁內捲（本段加了鎖高上限，第 5 節第 1 點） |
| 2、3、9、10、11 | 屬於 PNL-3／4／2，本段沒碰。4、5、6 沿用 PNL-1a |

世界事件紋章：有區域＝該區 HUD 紋章（`crestId`：霧潮入侵雲嶺、熔岩潰堤荒原），沒有區域（封印共鳴）＝源晶 `r_source`，和樣張一致。

## 3. 既有測試的改動（舊 → 新）

| 檔 | 舊 | 新 | 理由 |
|---|---|---|---|
| `client/src/world/board.test.ts` | `BoardWorldEventView` 測試物件沒有 `start_day`、`end_day` | 補 `start_day: 1, end_day: 3` | 新欄位有預設值，openapi-typescript 在回應型別標成必填（上手筆記第 81 點），不補 typecheck 不過 |
| `client/src/ui/summonBadges.test.ts`（6F-11「6 處都改成 lead-gap」） | 要求 `world/BoardPanel.tsx` 含舊的 `<span className={\`lead-gap ${board.season_boss.status …}\`}>` | 拿掉這一筆（留一行註解），其他 5 處照舊 | 公告板改分頁，頭目狀態改用 `Tag`（`TabLine` 的 end），那段 JSX 不在了；黏字的問題本來就不存在（標籤之間用 flex gap） |

後端既有測試沒改（`status_zh == "懸賞中"`、`phase_zh` 開頭等照舊通過）。沒有重產任何雜湊或快照；`openapi.json` 是照規定重產並跑 `tests/api/test_openapi_snapshot.py` 通過。沒改戰鬥紀錄格式。

## 4. 實測、量值、結束碼

**結束碼**（交件前各一次）：`corepack pnpm -C client typecheck` 0；`corepack pnpm -C client test --run` 0（321 檔、4171 passed）；`corepack pnpm -C client build` 0（只有既有的 chunk 大小警告）；`uv run ruff check .` 0；`uv run ruff format --check .` 0；`uv run mypy` 0；`uv run lint-imports` 0（14 kept）；`uv run pytest -q -n 4 tests/api/test_board_pnl1b.py tests/api/test_world_board.py tests/api/test_world_absence.py tests/api/test_season_boss_api.py tests/api/test_title_display.py tests/api/test_openapi_snapshot.py tests/world/test_season_board.py` 45 passed。沒跑 `scripts/check.py`。沒改引擎，沒跑重播。

**實機做法**：`vite build` 後自己的 `trpg serve --port 8766`（`TRPG_SAVE_DIR` 在暫存區、`TRPG_DEV_ROUTES=1`），無頭 Chrome `--mute-audio`、CDP 9347、裝置像素比 1，網址 `?mute=1`；Node 24 內建 WebSocket。`POST /api/world/characters`（單手劍）建角，localStorage 寫角色後由**首頁「繼續」**進入（PNL-1a 驗收建議的玩家入口；800×600 面板 493×414）→「站起來」→ 點守印人正下方一格 → 按 E 開公告板。資料全是伺服器的真資料（第 1 天、三張懸賞、三個世界事件、封印中的碎晶之主），沒有包 fetch。結束後用自己的 PID 關掉 serve（66540 及子程序）與 Chrome（55628 及子程序，`--user-data-dir` 在暫存區），8766、9347 都沒在聽。

**(a) 量到的固定區與面板高**（公告板；固定區＝標題列＋守印人＋第 N 天兩行＋分頁列）

| 視窗 | 面板（寬×高） | maxHeight | 固定區 | 分頁區鎖高 | 最高那一頁 | 捲不捲 |
|---|---|---|---|---|---|---|
| 1600×900 | 720×559.8 | 632 | 173.8 | 334 | 賽季時程（完整日程打開）332 | 都不用捲 |
| 800×600 | 493.3×413.8 | 413.8 | 121（≤ 165） | 241（上限） | 同左 332 | 世界事件（315）要捲 74px、時程打開完整日程（332）要捲；目標 134、懸賞 212、時程 191、頭目 112（打開規則 182）不用捲 |

各頁自己的高（800／1600）：今日目標 134／134、懸賞 212／212、時程 191／191（打開 332／332）、世界事件 315／295、頭目 112／112（打開 182／182）。

**分頁列**：1600 內寬 692＝第 0 級全名；800 內寬 465＝第 1 級全部短名（和需求 3.2 第 7 條「490 第 ①」一致）。切分頁前後五個分頁的左、上、寬、高在兩個尺寸都完全相同（1600：[456,334.3,140.3,34] [598.3,…,108.5] [708.8,…,98] [808.8,…,112] [922.8,…,119]；800：[169.4,235.5,105.3,34] [276.6,…,87] [365.6,…,65] [432.6,…,77] [511.6,…,84]），外框 [440,172.5,720,559.8]／[153.4,126.5,493.3,413.8] 不動；打開「完整日程」後 1600 外框也不動。

**必修 1（捲動歸零）**：800×600 世界事件頁捲到底（scrollTop 74／444）→ 點「懸賞」→ scrollTop 0、第一行「先搶先贏」在固定區下方完整可見（截圖 10）。用公告板拍：這個角色只有主角＋賽倫，隊伍頁不用捲，重現不了驗收裡的 22px；同一段程式（`PanelTabs`），單元測試另外鎖。

**浮動卡（6.5.1）**：1600×900 與 800×600 都測了「滑過 → 分 8 步滑進卡片 → 卡內滾輪 → 點一下釘住（`.float-card.pinned`）→ 滑到角落仍在 → Esc 關掉、面板仍開著」，全部通過。觸發元素：懸賞頁的 (i)（「先打倒的人拿走當天的懸賞（每天 06:00 刷新）。」，兩個尺寸）、時程頁的下一個釘（「第 2 天　主線第 1 章的劇情技能」）、800 的守印人一行（「守印人：封印和懸賞的消息，都貼在板上了。」）。卡片都開在觸發元素上方；內容短（scrollHeight＝clientHeight），本來就在底部，滾輪不關卡。

**截圖**（`docs/art/shots/pnl1b/`，10 張，全部 ≤ 300 KB；PNG 只用在最近鄰特寫）

| # | 檔 | 對應驗收 | 來源 |
|---|---|---|---|
| 1 | `docs/art/shots/pnl1b/pnl1b_01_goals_1600.jpg` | 6：今日目標（預設分頁） | 實機 1600×900 |
| 2 | `docs/art/shots/pnl1b/pnl1b_02_bounty_1600.jpg` | 6：懸賞分頁（切換後；五欄＋欄名列） | 實機 1600×900 |
| 3 | `docs/art/shots/pnl1b/pnl1b_03_goals_800.jpg` | 6：800 今日目標 | 實機 800×600 |
| 4 | `docs/art/shots/pnl1b/pnl1b_04_bounty_800.jpg` | 6、10：800 懸賞、面板 < 560 收掉獎勵欄 | 實機 800×600 |
| 5 | `docs/art/shots/pnl1b/pnl1b_05_fixed_800_x2.png` | 7：800 固定區（守印人 28＋一行、大字與兩行對齊、分頁列短名），最近鄰 2 倍 | 實機 800×600 |
| 6 | `docs/art/shots/pnl1b/pnl1b_06_sched_fold_1600.jpg` | 8：賽季時程＋完整日程打開 | 實機 1600×900 |
| 7 | `docs/art/shots/pnl1b/pnl1b_07_sched_800.jpg` | 8：800 賽季時程（每天約 29px） | 實機 800×600 |
| 8 | `docs/art/shots/pnl1b/pnl1b_08_pins_800_x2.png` | 8：釘（下一個亮金圈、第 10 天金鎖＋說書人）、今天、階段、世界事件兩列，最近鄰 2 倍 | 實機 800×600 |
| 9 | `docs/art/shots/pnl1b/pnl1b_09_events_boss_800.jpg` | 9：左＝世界事件（捲到底，第三個事件在下面）、右＝賽季頭目（挑戰規則與評分榜打開，不用捲） | 實機 800×600 |
| 10 | `docs/art/shots/pnl1b/pnl1b_10_scroll_reset_800.jpg` | PNL-1a 必修 1：左＝世界事件捲到底、右＝切到懸賞後回到頂端；左圖也看得到 18px 漸隱 | 實機 800×600 |

**實機未看**：懸賞「已被 ○○ 搶下」與說明卡（要另一個角色先搶）、「你搶下了」、世界變化清單（要世界事件失敗）、頭目開放與評分榜有人、開賽前／季末的固定區、分頁列第 2、3 級（公告板在 1600／800 都到不了）——前四項由 `pnl1bBoard.test.ts` 的靜態輸出鎖住，第 2、3 級沿用 PNL-1a 開發頁的量測（公告板五頁在 `#switch` 已測過）。這次沒有另做開發頁。

## 5. 和樣張不同的地方

1. **分頁區鎖高有上限**：樣張只在「放得下」的情況量；800×600 實機（493×414）公告板最高那一頁 332 放不下（可視約 241）。PNL-1a 的做法會把每一頁都鎖成 332，連 134 高的今日目標也要捲 125px 空白。改成只鎖到放得下的高度，高的頁在頁內捲（外框仍固定在 maxHeight、切頁不跳）。隊伍與影子面板同樣受益（影子頁不再多捲一段）。
2. 守印人：1600 與 800 兩種樣子都畫出來，用容器查詢（面板 < 560）切換，不看視窗寬。
3. 懸賞狀態欄比樣張寬（70 → 96，窄版 88）：「已被 ○○ 搶下」比「懸賞中」長，標籤可換行。
4. 完整日程只列時間點（同樣張）；階段的說明放在時間軸階段格的說明卡（滑過「第 a～b 天　名稱：說明」）。今天所在那段的說明照樣張寫在時程頁第一行。
5. 世界事件的「成功」用綠細框標籤、「失敗」用淡灰（樣張沒畫這兩種）；頭目非封印狀態：開放＝實心金、其他＝淡灰。
6. 世界變化（樣張沒畫）照需求放在世界事件頁最後：區塊標頭（`town` 圖示＋「世界變化」）、建議等級／商店加價一行一列、已清空地點＋「已清空」＋鐘＋重生時刻。

## 6. 待 PM 決定

1. **800×600 世界事件頁要捲 74px**：三個世界事件（樣張只畫兩個）＋說明兩行，在 493×414 的面板放不下；需求第 7 節第 9 項寫「不用捲」指的是頭目（打開規則 182，放得下）。要一屏放下得砍內容（例：尚未開始的事件不畫進度條、說明收進說明卡），交美術 PM 看圖決定。
2. **時間點種類由 ID 前綴判斷**：建議之後在 `content/world/season.yaml` 的 `milestones` 加 `kind`（或 `kinds`），後端改成讀內容檔；本段不能改 `content/`。
3. **`PanelTabs` 鎖高上限**（第 5 節第 1 點）是共用元件的行為改變（向後相容，放得下時不變）；PNL-2 的成長面板如果最高那一頁超過 maxHeight，也會變成「只有高的頁要捲」。
4. **公告板標題列沒用 `PanelHead`**：要在標題和按鈕之間插守印人一行；若要共用，可在 `PanelHead` 加一個中間插槽（向後相容），本段為了不和 PNL-2 互改共用元件先不做。
5. **公告板樣式另開 `styles/world-panel-board.css`**：為了和 PNL-2 平行時不改同一檔；PNL 系列做完後要不要併回 `world-hud.css` 由開發 PM 定。檔名不能叫 `world-board.css`（排在 `world-hud.css` 前面會讓 PNL-1a 的 CSS 測試讀錯區塊，上手筆記第 93 點）。
6. **固定區下緣漸隱 18px、上半實色**：800 捲到底時分頁列下仍隱約看得到半行字的頂端（比 10px 時淡很多，截圖 10 左），要不要再加長交美術 PM 看。
7. **必修 1 的截圖用公告板拍**：測試角色的隊伍頁不用捲，重現不了驗收的隊伍 → 影子情境；程式是同一個 `PanelTabs`。
8. 舊的 `.world-board-event`、`.world-board-fill`、`.world-board-open`（`world.css`）公告板已不用，但 `LeaguePanel` 還掛 `world-board` class，沒刪。
