# Phase OB-5 報告：#150 前端——選大類、葛蘭的正式選定、入門期提示

> 實作者：worktree 分支 `worktree-agent-ab36437058248df22`，基準 origin/main `e8105999`（開工 `31c981ae`，中途依開發 PM 指示合併一次，只多文件）。沒有 push、沒有合併進 main。
> 依據：`docs/phases/PhaseOB-5計畫.md`、`docs/art/OB與PR移植需求.md`（含第 3 節玩法 PM 補定）、`docs/art/OB與PR樣張.md` 第 1～4、6 節、`docs/design/21` 21.5、OB-1～OB-4 報告、共用筆記 `台詞-OB5與PR2定稿.md`（「補定」優先）與 `台詞-150與147.md`。
> 沒有動 `src/trpg/engine/`、`src/trpg/roguelite/`、`client/src/battle/`、`client/src/render/`；`WORLD_RULES_VERSION` 沒動（25）、`CHAR_FORMAT` 沒動。沒做 PR-2、OB-6。

## 1. 交付項目

| # | commit | 內容 |
|---|---|---|
| 1 | `e618f739` | 選大類畫面（`RangeClassPick.tsx`）＋後端畫面資料與定稿字串入檔 |
| 2 | `f9fbb352` | 葛蘭的正式選定（`RangeScreen.tsx` 的 `choose` 模式）、入口、推薦小牌、黏底列 |
| 3 | `d12f0cd6` | 延後的三選一依序出、等待提示；接著的配點教學 |
| 4 | `b2778778` | 入門期的限制提示（面板資料標成不可用）＋ pytest、vitest |
| 5 | `f71331a9` | `STARTER_STEPS` 收成一份；舊「一次選定」的說明 |
| 6、7 | 本報告的 commit | 暫定字串清單、測試收尾、報告 |

第 5 項的 commit 裡 `tests/api/test_ob5_screen_data.py` 有一個名稱衝突（那個 commit 單獨跑會有 1 個測試失敗），在本報告的 commit 修掉；`STARTER_STEPS` 的實際改動在第 1 個 commit 就做了。

### 1.1 畫面怎麼接

- `range.ts` 的 `rangeMode()`：`class`（`stage == pick_class`，整頁）／`choose`（`stage == starter` 且 `choice.available`）／`reselect`（`stage == chosen` 且可重選；**OB-6 的位置，這一段不畫**，`RangeScreen` 收到時回傳 `null`）。
- 選大類：按「確定出發」送 `opening_class`（不再送舊的一次選定）。去試打回來會接著上次選的（本機草稿）。
- 正式選定：伺服器給教學 `choose`（可以選定時）就自動打開整頁；「之後再選」回世界畫面，之後可按頂列的「正式選定武器與關鍵字」、或點葛蘭（霧渡鎮）／主城的靶場與工坊師傅再打開；離開能選定的地方後下次到了再自動開。第一次打開時手上是入門武器。
- 推薦：每換一把武器就查 OB-3 的帶武器端點；查不到時用畫面資料裡入門武器那一份；沒有推薦就不標、也不顯示推薦的說明句。
- 被拒（背包放不下等）：原因顯示在頁面上方的錯誤條、關鍵字那一塊按鈕上方、窄版黏底列的第一行。
- 入門招、示範招、關鍵字、地名、台詞、頭像全部讀伺服器；靶場的四個前端檔沒有技能 ID、沒有寫死「主城」（vitest 掃原始碼）。

### 1.2 後端補的畫面資料

| 位置 | 內容 |
|---|---|
| `RangeView` | `keeper`（守印人頭像：主城實地地圖的情境物件）、`loan`（選了才說的一句）、`capital_zh`（主城地名，目前「樞島」）、`choice` |
| `RangeView.choice`（`stage == starter` 才有） | `available`、`blocked_zh`、`in_capital`、`place_zh`（「霧渡鎮導師堂」或「{主城地名}工坊靶場」）、`speaker`（葛蘭或守印人的頭像）、`lines`、`done`、`npc`、`objects` |
| `RangeDemoView.blurbs_zh` | 六招各一句（`range.demo_blurbs`） |
| `LessonView.kind = "choose"` | 可以正式選定時（條件就是 `choice_problem`、沒有待選的三選一）；不記看過 |
| `GuideView` | 入門期打完新手前兩步＝「回霧渡鎮導師堂找葛蘭」 |
| `LevelUpView` | 入門期用定稿的兩句（2 級／打完前兩步） |
| 戰鬥短提示 | 入門期竹林兩句提示句尾加「（選關鍵字時可以自己試試）」 |
| `WorldView.limits` | 系統 → 原因（`world.opening.opening_limits`，唯讀，和閘門同一張表） |
| 既有欄位在入門期標成不可用 | 背包武器的 `can_equip`／`equip_problem_zh`、`free_race_change_zh`、`here.can_loadout`、`party.can_hire`／`hire_problem_zh`、影子打法、`oath.can_swear`／`swear_problem_zh`、每一招的 `can_flash`／`flash_problem_zh`、聯賽 `can_enter`／`enter_problem_zh`、賽季 Boss `can_challenge`／`problem_zh` |
| 內容 schema（`content/world_newcomer.py`） | `range.loan`、`demo_blurbs`、`keeper_object`、`choose`、`choose_capital`、`choose_done`、`choose_place_zh`、`choose_objects`；`allocate_respec_lesson`、`allocate_respec_done_zh`、`level_up_starter_zh`、`level_up_choose_zh`、`guide_choose_zh`、`starter_teach_note_zh`、`starter_teach_hints` |

`world/` 裡改到的：三句被擋原因換成定稿（換種族、閃現、其他戰鬥、重選到期）、新增唯讀函式 `opening_limits`、`starter_steps_done`、`STARTER_STEPS` 的匯入方向。沒有改任何判斷。

### 1.3 改到的既有測試斷言（都是字串或畫面行為跟著規格變，沒有放寬規則）

| 檔案 | 改了什麼 | 原因 |
|---|---|---|
| `tests/api/test_opening_flash.py` | `BLOCKED`「4 級前不能閃現」→「到 4 級才能閃現」；`match="不能閃現"` → `match=BLOCKED` | 定稿 |
| `tests/world/test_opening_end.py`、`test_opening_reselect.py` | 「4 級之後不能重選」→「已到 4 級，免費重選已結束」 | 定稿 |
| `tests/world/test_opening_stages.py` `GATE_REASONS` | 加兩句定稿（閃現、換種族） | 原本靠「入門期」三個字比對，定稿的句子沒有這三個字 |
| `tests/api/test_opening_class_api.py` | `"入門期" in text` → `"之前不能換種族" in text` | 同上 |
| `tests/api/test_opening_lessons.py::test_no_allocate_lesson_in_the_starter_stage` | 打完前兩步、人在霧渡鎮的兩個角色從「沒有教學」改成「教學是 `choose`」（剛進入門期的那個仍是沒有） | 規格要的「教學類別選定」；仍然不出配點教學 |
| `client/src/world/range.test.ts` | 整份改寫 | 舊畫面（一次選武器＋關鍵字）被新畫面取代 |

## 2. 驗收

| 條件 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 結束碼 0、0 |
| `uv run mypy` | Success: no issues found in 1439 source files |
| `lint-imports` | 14 kept, 0 broken |
| `pytest tests/world tests/api tests/content tests/narrative tests/test_architecture.py -n 8` | 5326 passed、1 skipped，結束碼 0（3 分 16 秒） |
| `corepack pnpm -C client typecheck` | 結束碼 0 |
| `corepack pnpm -C client test`（vitest 全部） | 283 檔、3443 個全過，結束碼 0 |
| `vite build`（`corepack pnpm -C client exec vite build`） | 結束碼 0 |
| openapi | `client/openapi.json`、`schema.d.ts` 已重產（快照測試在上面那批裡） |

沒有跑：`scripts/check.py`、`tests/skillgen`、`tests/roguelite`、`tests/cli`、戰鬥重播（沒動引擎）。pytest 那一批跑完之後只再改了前端一個屬性名（`RangeDoneDialog` 的 `title` → `heading`，浮動卡規則的掃描會把它當原生 tooltip），之後 vitest、typecheck、build 重跑過。

新測試：`tests/api/test_ob5_screen_data.py`（12 個）、`client/src/world/range.test.ts`（27 個）、`client/src/world/limits.test.ts`（7 個）。

## 3. 美術驗收 6 項的截圖（`docs/art/shots/ob5/`）

全部是實機：自己啟動的 `trpg serve`（8105，存檔指到暫存資料夾，LLM 位址指到不存在的埠）＋ vite（5195）＋自己啟動的無頭 Chrome（`--mute-audio`，網址都帶 `?mute=1`）。每張都自己打開看過，並和 `shots/ob/` 的樣張比對。

| # | 項目 | 檔名 | 狀態 |
|---|---|---|---|
| 1 | 選大類 1280：未選、滑過、已選、展開武器架 | `1-class-1280-none`、`-hover`、`-selected`、`-rack-open` | 有截圖 |
| 2 | 選大類 390：未選、已選（含黏底列）、展開武器架 | `2-class-390-none`、`-selected`、`-selected-viewport`、`-rack-open` | 有截圖 |
| 3 | 葛蘭 1280：四種狀態、選滿與 1/2、兩顆鈕的一般與停用 | `3-gran-1280-four-states`（2/2，四種都在）、`3-gran-1280-one`（1/2）、`3-gran-keyword-states-2x`、`3-gran-try-normal-2x`／`-disabled-2x`、`3-gran-demo-normal-3x`／`-disabled-3x` | 有截圖 |
| 4 | 葛蘭 390：整頁、黏底列 | `4-gran-390`、`4-gran-390-viewport`、`4-gran-390-bar-3x` | 有截圖 |
| 5 | 頭像特寫 | `5-keeper-portrait`、`5-gran-portrait` | 有截圖 |
| 6 | 實機全流程 | `6-live-1`～`6-live-14`（見下） | 有截圖 |
| — | 限制提示 | `7-limit-main-hand`（滑過顯示原因）、`7-limit-growth-flash-oath-race`、`7-limit-loadout`、`7-limit-hire` | 有截圖 |

第 6 項的順序：`1` 選大類頁按遠程卡的「拿起試打」進靶場戰鬥（弓＋兩招入門招）→ `2` 回到選大類（選擇還在）→ `3` 按「確定出發」後守印人的話 → `4` 主城 → `5` 霧渡鎮的升級畫面（指示找葛蘭；任務欄第一行是「回霧渡鎮導師堂找葛蘭」）→ `6` 按「之後再選」回鎮上（頂列有再打開的鈕）→ `7` 按「確定選這套」的等待提示 → `8` 葛蘭收回入門配備 → `9` 第 1 組三選一 → `10` 第 1 組選了一張 → `11` 第 2 組（選擇已清空）→ `12` 第 2 組送出的等待提示 → `13` 配點教學 → `14` 葛蘭收尾那句。

**怎麼到第 1、2 步之後的**：`4` 和 `5` 之間不是在瀏覽器裡走過去打的。我把伺服器停掉，用腳本對那份暫存存檔做「AI 代打」：照 `tests/world/test_opening_choice.py::_played` 的做法，真的送 `FightAction`（`auto_steps`）用弓與兩招入門招打贏渡口石階與竹林小徑的固定戰（兩場都是種子 0 就贏，升到 3 級、兩組三選一有延後），再把角色放回霧渡鎮、重開伺服器。所以這份存檔的世界日誌和角色對不上（只用來拍圖）。限制提示那組用的是另一個角色，背包裡的武器與頭盔也是停伺服器時用腳本放進去的。

和樣張的出入（都是照規則或資料，不是沒做到）：

- 標題牌：選大類的副標是「先挑一條路」（見待決 1）；沙盒說明用補定版「不耗任何資源」。
- 人物是玩家自己的外觀（灰上衣），樣張是示範角色。
- 火焰箭的代價是資料裡的「AP 1・法力 4」，樣張寫法力 5。
- 葛蘭畫面的推薦是照實際用招算的（這個角色是點燃、中毒），樣張標在倒地、撞擊是示意。四種狀態：點燃＝推薦且已選、撞擊＝已選非推薦、中毒＝推薦未選、其餘＝一般。
- 「拿起試打」「看示範」的停用圖是等伺服器回應時拍的（把網路延遲調高）。**目前的內容裡沒有「這把武器沒有某關鍵字的起始技能」的組合**（我點了拳套、鞭、霰彈槍、圖騰杖都沒有），所以那種停用樣子沒有實機圖；樣式沿用現行靶場沒有改。

## 4. 實機未看

- **在主城靶場開的正式選定**（守印人的話、標題牌「樞島工坊靶場・…」、點靶場或工坊師傅打開）：只有 pytest 與 vitest，沒有截圖。
- **點葛蘭本人重新打開**：實機走的是頂列那顆鈕；點 NPC 的那條路只有 vitest（`opensChoose`）。
- **事件卡裡被擋的戰鬥解法與機遇**、**聯賽面板**、**公告板的賽季 Boss**、**鐵匠面板上緣那一行**：畫面資料有 pytest，沒有實機圖。事件卡與鐵匠沒有改既有的顯示方式。
- **正式選定被拒（背包放不下）的畫面**：只有 vitest（原因會顯示）；拒絕本身是 OB-3 的 API 測試。
- **略過配點教學後的再提示**：只有 vitest。
- 390 與 1280 之間的寬度沒有看。
- 用新角色在瀏覽器裡實際走到渡口石階、竹林小徑開打（見第 3 節）。

## 5. 暫定字串清單

共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\暫定字串-OB5.md`：第 1 節是這一段已照定稿換掉的（核對用），第 2 節後端還沒定稿的 24 列，第 3 節前端自己寫的 9 列。

## 6. 待 PM 決定

1. **選大類的標題牌**：補定寫「工坊靶場・先挑一條路」。我做成標題「工坊靶場」＋副標「先挑一條路」；若副標要整句（會出現兩次「工坊靶場」）改一個常數即可。
2. **舊的一次選定仍可達**：`pick_class` 階段後端還收 `opening_confirm`（白名單，`test_pick_class_stage_keeps_old_one_shot_confirm` 鎖著）。前端已經不送，但直接打 API 仍能跳過入門期。拿掉要改規則與那個測試，沒有做。
3. **配點教學我多做了一點**：規格沒列，但正式選定、三選一選完後它一定會跳出來，原本的字（「開局的 0 點…共 8 點」）和按鈕（再送一次配點）對不上，所以照 OB-3 報告的約定補了：文字改寫、「維持推薦配法」不送動作、略過記 `lesson:allocate_skip`、再提示記 `lesson:allocate_again`、葛蘭收尾那句改成跳在畫面上（後面不接閃現教學）。
4. **定稿的 `allocate_lesson`／`allocate_done_zh` 只套在走新流程的角色**（另開 `allocate_respec_*`）；舊角色照舊句，因為「我先照你的兵器配好了」對舊角色不成立。
5. **在主城選定完成沒有台詞**（「借你的那套我收回了」是葛蘭的話），目前不出彈窗。
6. **可以選定時點葛蘭會直接開整頁**，選定前不能和葛蘭聊天（按「之後再選」後再點還是開整頁）。主城的靶場與工坊師傅同理（原本只是說明卡）。
7. **每次到霧渡鎮或主城都會自動打開**（直到選定）。路過主城也會跳。
8. **任務欄**：指引排第一行，但下面新手任務的第 3 步仍寫「往東邊的出口 → 雨中梯田」，而那場戰鬥選定前碰不到。
9. **限制的原因以入門期那句優先**：例如人不在主城時，換種族原本寫地點的原因，現在寫「正式選定…之前不能換種族」，和送出動作被拒的句子一致。
10. **溶掉、傳承的按鈕沒有逐顆停用**，只在成長面板上緣寫一行；送出會被同一句擋下。打造只限防具也是只寫一行。
11. **入門期的角色有預設傭兵**（賽倫、回春）在隊伍裡，而面板寫「入門期不能雇用傭兵」。是既有行為，沒有動。
12. **試打戰鬥的地名**一律「{主城地名}・工坊靶場」，從霧渡鎮葛蘭那頁進去也是。上方訊息條的格式是既有的「靶場試打：弓：淬毒箭、燧石飛刃」，和樣張的「弓＋…」不同（PR-2 的範圍，沒有動）。
13. `keeper_object`、`choose_objects` 指到的主城物件存不存在，只有測試在檢查，沒有接進內容載入的檢查。
14. 葛蘭「提醒 4 級前可重選」等四句重選台詞沒有入檔（畫面屬 OB-6）。

## 7. 沒驗證

- 第 4 節列的各項。
- 開發模式下 vite 熱更新時我看到一次草稿被清成空的（當時剛改完檔）；重新載入後重現不出來，判斷是熱更新造成，正式建置沒有另外確認。
- 觸控裝置上停用按鈕的原因顯示（沿用既有 `Hint` 的行為，沒有測）。
