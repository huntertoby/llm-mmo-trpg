# Phase PNL-3 報告：任務與線頭面板＋兩件共用小修

依據：`docs/art/資訊面板-移植需求.md`（美術 PM 第九任，使用者「照建議」）表 6 的 PNL-3 列；驗收看第 7 節 #15。開發 PM 追加：PNL-1b 美術驗收可修 1（說明字的數字不和前面名詞分開，寫進 `PanelKit`）、PNL-2 美術驗收可修 1（重閃清單空的時候改虛線空狀態；原文在美術分支 `3fec2b77` 的 `docs/art/PNL-2驗收.md` 第 37～71 行）。
起點：worktree 開在 `404c56bd`，`git merge --ff-only main` 快轉到 `98f92a00`。沒改 `content/`、`EventCard.tsx`、QI-7 的物品圖示檔、`PanelTabs.tsx`、需求與計畫檔。

## 1. 做了什麼

| 項目 | 檔案 |
|---|---|
| 後端：`QuestStepView` 加 `place_zh`、`task_zh`（`split_step` 照第一個「：」拆；沒有「：」或一邊是空的＝地點 `None`、整句當要做的事）；`QuestLogView` 加 `giver_portrait`（人設卡 `portrait`）、`giver_region`（任務所在區域，頭像框色）；`ThreadView` 加 `left_zh`（「剩 2 天 23 小時」「剩 5 小時」「剩 2 天」「剩不到 1 小時」）。舊欄位（`text_zh`、`expires_zh`）照舊 | `src/trpg/api/world_story_schemas.py`、`src/trpg/api/world_story_view.py`、`client/openapi.json`、`client/src/api/schema.d.ts` |
| 「任務與線頭」改成 `PanelTabs`：固定區（標題＋回到地點圖；「×」是 WorldHud 正式關閉鈕）＋分頁 任務日誌｜任務｜HUD `bar_J`｜細框「進行中條數」（滑過「進行中 N」）→ 線頭｜線頭｜事件卡 `thread` 圖樣本身｜細框「條數」（滑過「線頭 N 條」）。0 條不掛記號 | `client/src/world/QuestLog.tsx`、`client/src/world/questPanel.ts` |
| 任務卡：名字（16 粗體）＋實心類別標籤＋委託人小頭像 22（`Portrait`，伺服器給的頭像與區域）與名字；完成的任務掛綠細框「已完成」、整卡淡 0.7；摘要 L2；建議 `advice_zh` 照現行色（`#c08a20`）在路線膠囊上一行；藍色路線膠囊（HUD `bar_M` 18）；頁內不再寫「進行中 N」 | `QuestLog.tsx` `QuestCard` |
| `StepTimeline`：縱向時間軸（綠勾＝完成、金圈＋亮金粗體＝目前、空圈數字＝未到；圈之間 2px 直線，完成段綠）；左欄地點（L2）、右欄要做的事；欄寬在 `ol`、每列 `subgrid`，同一張卡的地點欄上下對齊 | `QuestLog.tsx`、`client/src/styles/world-panel-quest.css` |
| 線頭列：線軸 18、粗體內容、範圍標籤、鐘＋「剩 …」、NPC 標籤、「指向○○」標籤；放不下時標籤整組換到下一行靠右；第一行「事件的結果會留下線頭」＋右邊 (i)（規則句原字）；兩個空狀態照原字改虛線空狀態 | `QuestLog.tsx` `ThreadsPane` |
| **共用小修（PNL-1b 可修 1）**：`PanelKit` 新增 `KeepNum`／`glueNumbers`／`wordBeforeNumber`：數字（可帶空白、正負號）和前面那個詞（`Intl.Segmenter` 切詞，一個字的詞併進前一個，最多 6 字）包成 `.pnl-nowrap`。套到公告板世界事件說明、任務摘要、步驟、線頭內容 | `client/src/ui/PanelKit.tsx`、`client/src/styles/world-hud.css`（一行）、`client/src/world/BoardPanes.tsx`（一處） |
| **共用小修（PNL-2 可修 1）**：重閃清單空的時候改 `EmptyNote`；成長面板（`bare`）只寫「要先閃現過，或有完整技能。」、一輪營火照原句（`reflashEmptyText`） | `client/src/run/CampfireSkillCare.tsx` |
| 開發頁：`#quest`（`?empty=1`）、`#growth`／`#campfire` 加 `noreflash=1`；公告板 fixture 的熔岩潰堤改用內容檔原句 | `client/src/dev/panelGallery.tsx`、`client/src/dev/questFixture.ts`（新）、`client/src/dev/boardFixture.ts` |
| 測試：前端 17 項、後端 14 項 | `client/src/world/pnl3Quest.test.ts`、`tests/api/test_quest_pnl3.py` |
| 上手筆記第四節第 100～104 點、第五節加一列 | `docs/dev/上手-前端戰鬥畫面與動畫.md` |

## 2. 第 5 節「要開發 PM 決定的事」本段怎麼做

| # | 做法 |
|---|---|
| 2 | 照美術建議後端分欄（`place_zh`／`task_zh`）；沒有「：」整句放右欄、左欄空著（時間軸仍對齊） |
| 9 | 照美術建議：線頭分頁只掛細框條數，快到期不掛琥珀三角 |
| 8 | 沿用 PanelTabs（開著不重量） |
| 其他 | 屬於 PNL-1b／2／4 |

## 3. 既有測試的改動（舊 → 新）

1. `client/src/ui/summonBadges.test.ts`「6 處都改成 lead-gap」：拿掉 `world/QuestLog.tsx` 的兩筆（`<span className="muted small lead-gap">…{q.kind_zh}`、`<span className="muted lead-gap">…{t.scope_zh}・{t.expires_zh}`），改成檢查 `<Tag tone="open">{quest.kind_zh}</Tag>` 與 `<Tag>{t.scope_zh}</Tag>`。理由：類別、範圍、到期改成標籤（flex gap），那兩段 JSX 不在了，黏字問題不存在（同 PNL-1b、PNL-2 的處理）。

沒有重產任何雜湊或快照；`openapi.json`／`schema.d.ts` 照規定重產並跑 `tests/api/test_openapi_snapshot.py`。`PanelTabs.tsx` 沒改。

## 4. 實測、量值、結束碼

**結束碼**（交件前各一次）：`corepack pnpm -C client typecheck` 0；`corepack pnpm -C client test --run` 0（324 檔、4210 passed）；`corepack pnpm -C client build` 0（只有既有的 chunk 大小警告）；`uv run ruff check .` 0；`uv run ruff format --check .` 0；`uv run mypy` 0；`uv run lint-imports` 0（14 kept）；`uv run pytest -q -n 4 tests/api/test_openapi_snapshot.py tests/api/test_client_fixtures.py tests/api/test_quest_pnl3.py tests/api/test_world_events_api.py` 40 passed。沒跑 `scripts/check.py`；沒改引擎，沒跑重播。

**實機做法**：`vite build` 後自己的 `trpg serve --port 8795`（`TRPG_SAVE_DIR` 在 `scratchpad/pnl3/saves`、`TRPG_DEV_ROUTES=1`）、`vite --port 5297`（開發頁）、無頭 Chrome `--headless=new --mute-audio`（除錯埠 9733、profile 在 `scratchpad/pnl3/chrome`），網址都帶 `?mute=1`。開發角色 `POST /api/world/characters`（單手劍、主城），localStorage 寫角色後由**首頁「繼續」**進入、按 J 開面板。開發角色沒有任務與線頭：用 `Page.addScriptToEvaluateOnNewDocument` 包 `window.fetch`，在世界資料補兩個任務（含渡婆婆的人設卡頭像）與三條線頭（資料同 `dev/questFixture.ts`，欄位照新 API）；程式與後端不動。結束後用 TaskStop 關掉 serve、Chrome、vite，vite 子程序（PID 53784，自己開的 5297）再用 PID 關；8795／5297／9733 都沒在聽。

**(a) 固定區與面板高**（實機，注入資料：兩個任務、三條線頭）

| 視窗 | 面板（寬×高） | 固定區 | 分頁區鎖高 | 撐高的那一頁 | 捲不捲 |
|---|---|---|---|---|---|
| 1600×900 | 720×508 | 74 | 382 | 任務日誌（382） | 都不用捲 |
| 800×600 | 493×414 | 74 | 288（`cappedLock` 上限） | 任務日誌（382） | 任務日誌要捲 126px（scrollHeight 496／可視 370）；線頭不用捲 |

線頭頁 134（1600、800 一樣：800 時三列的標籤都還放在同一行）。分頁列 1600、800 都是第 0 級（全名）；切分頁前後兩個分頁的左、上、寬完全相同（1600：[456,234.5,122.4] [580.4,234.5,95.4]；800：[169.4,188.5,122.4] [293.8,188.5,95.4]），外框不動。

**浮動卡（6.5.1）**：觸發元素＝線頭頁第一行右邊的 (i)（規則句）。1600×900 與 800×600 都是：滑過約 700 ms 卡片出現 → 分 8 步滑進卡片，卡片還在 → 卡內滾輪：內容短（scrollHeight 52＝clientHeight 52），已在底、沒被關 → 點一下釘住（`.float-card.pinned`）→ 滑鼠移到左上角仍在 → Esc 關掉卡片，面板仍開著。

**共用小修實測**：開發頁 `#board` 800×600 世界事件，熔岩潰堤說明（內容檔原句）斷成「…提早開放、封印／鑰匙 +5」，`.pnl-nowrap`＝「鑰匙 +5」只有一個 client rect（沒有拆行）。重閃空狀態：`#growth?case=starter&tab=care&fold=reflash&noreflash=1` 的 `reflash-empty`＝「要先閃現過，或有完整技能。」（`pnl-empty`）；`#campfire?noreflash=1`＝「還沒有可以重閃的技能（要先閃現過，或有完整技能）。」（`pnl-empty`，營火沒截圖，只量字）。

**截圖**（`docs/art/shots/pnl3/`，10 張，全部 ≤ 300 KB）

| # | 檔 | 對應 | 來源 |
|---|---|---|---|
| 1 | `docs/art/shots/pnl3/pnl3_01_quests_1600.jpg` | 15：任務日誌（預設） | 實機 1600×900（任務為注入資料） |
| 2 | `docs/art/shots/pnl3/pnl3_02_threads_1600.jpg` | 15：線頭（點一下切換；滑過分頁的「線頭 3 條」說明卡也在） | 實機 1600×900（注入） |
| 3 | `docs/art/shots/pnl3/pnl3_03_quests_800.jpg` | 15：任務日誌 | 實機 800×600（注入） |
| 4 | `docs/art/shots/pnl3/pnl3_04_threads_800.jpg` | 15：線頭 | 實機 800×600（注入） |
| 5 | `docs/art/shots/pnl3/pnl3_05_steps_1600_x2.png` | 15：任務卡與步驟時間軸，最近鄰 2 倍 | 實機 1600×900（注入） |
| 6 | `docs/art/shots/pnl3/pnl3_06_float_1600.jpg` | 浮動卡釘住 | 實機 1600×900 |
| 7 | `docs/art/shots/pnl3/pnl3_07_float_800.jpg` | 浮動卡釘住 | 實機 800×600 |
| 8 | `docs/art/shots/pnl3/pnl3_08_empty_800_dev.jpg` | 沒有任務的虛線空狀態（線頭空狀態只量字） | 開發頁（實機未看） |
| 9 | `docs/art/shots/pnl3/pnl3_09_board_keepnum_800_dev_x2.png` | 可修：「鑰匙 +5」不分開，最近鄰 2 倍 | 開發頁 `#board` 800（實機未看） |
| 10 | `docs/art/shots/pnl3/pnl3_10_reflash_empty_1600_dev.jpg` | 可修：成長整備重閃的虛線空狀態 | 開發頁 `#growth`（實機未看） |

**實機未看**：真的任務與線頭資料（開發角色沒有，注入）、空狀態、公告板世界事件斷行（實機的公告板要走到守印人；用開發頁＋內容檔原句）、成長與營火的重閃空狀態。

## 5. 和樣張不同的地方

1. 完成的任務（樣張沒畫）：綠細框「已完成」標籤、整卡淡 0.7（原本是 opacity 0.65＋「・已完成」）。
2. 所有任務類別（新手、主線、支線）都用實心標籤（樣張只畫「新手」）。
3. 線頭列多了樣張沒畫的 NPC 標籤、「指向○○」標籤（需求 3.3 有寫，字照原字「指向」）。
4. 步驟地點欄 `subgrid` 對齊（樣張是每列 flex＋`min-width: 64px`，地點字數不同時會錯開）。
5. 沒有「：」的步驟左欄空著（例「在霧渡鎮打聽霧的來處」），時間軸與右欄仍對齊。

## 6. 待 PM 決定

1. **線頭的「剩 …」做成新欄位 `left_zh`，`expires_zh` 不改**：HUD 右側追蹤列（`hud.ts`）也用 `expires_zh`（沒有鐘圖示，「後到期」比較清楚）。要不要追蹤列也改「剩 …」請決定。
2. **800×600 任務日誌要捲 126px**（兩個任務：新手＋主線各三步）。和成長、公告板一樣是「最高那一頁超過可視高」，鎖高照 `cappedLock`；需求 3.2 第 1 條「盡量一屏」做不到，交美術 PM 看圖（要省可以把完成的任務收進摺疊，本段沒做）。
3. **完成的任務的排法**：留在列表後面（照舊 `sortQuests`）、淡掉＋「已完成」標籤；數量多時要不要收進「已完成（N）」摺疊。
4. **1600 線頭頁下方留白**（面板高＝最高的任務日誌頁 382，線頭頁只用 134）：照規則，與 PNL-1b、2 同。
5. **舊左欄（非 HUD 模式）也換成分頁版**：同一個 `QuestLog`，外層不再是 `.panel`；那個版面已少用，沒另外調。
6. **`KeepNum` 的範圍**：只包「前一個詞＋數字」；數字後面的單位（例「3 天」的「天」）沒黏。公告板只套世界事件說明（需求指定），其他說明（階段說明、頭目說明、成長面板）要不要一起套請決定。
7. **重閃空狀態只做了「空的時候那一行」**：營火的重閃標題、其他排法沒動（照指示）。

## 7. Commit

- `08bfc94a` feat(api): quest step place/task split, giver portrait, thread left text (PNL-3)
- `2ae9044a` feat(ui): keep numbers with the preceding word in panel notes (KeepNum)
- `aa915b56` feat(ui): reflash empty state uses the dashed EmptyNote
- `b79790d2` feat(world): quest and thread panel with tabs and step timeline (PNL-3)
- `3ddf5862` fix(world): align quest step columns with subgrid, let thread tags wrap
- （本報告、截圖、上手筆記另一個 commit）

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main（上手筆記 §4 與 QI-7 撞號，PNL-3 改為 108～112）。合併後 ruff、mypy 0；openapi 快照＋quest＋world events 36 passed；前端 typecheck 0、vitest 4238 passed、build 0。

1. 線頭新增 left_zh、舊 expires_zh 與 HUD 追蹤列不改：接受，HUD 是否一起改交美術 PM。
2. 800×600 任務日誌捲 126px：交美術 PM。
3. 完成任務收摺疊：交美術 PM；目前淡掉＋「已完成」框。
4. 1600 下方留白：同 PNL-1b／2 規則，接受。
5. 舊左欄換成分頁版：接受。
6. KeepNum 其他說明字是否套用：交美術 PM，PNL-4 時順手。
7. 任務類別一律實心標籤：交美術 PM。

### 美術驗收結果（2026-11-13，docs/art/PNL-3驗收.md）

通過，沒有必修。800 任務日誌捲動接受；已完成任務收「已完成（N）」摺疊、KeepNum 套到公告板與成長所有 L2／L3 說明、任務類別改細框中性 → 交 PNL-4 順手做；HUD 追蹤列「剩 …」待玩法 PM 確認前照舊。
