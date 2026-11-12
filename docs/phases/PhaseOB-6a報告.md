# Phase OB-6a 報告：#150 前端第二段——重選畫面、小牌、入門武器卡、字串收尾

> 實作者：worktree 分支 `worktree-agent-a176df9c858f80815`，基準 origin/main `6ef834fb`。沒有 push、沒有合併。
> 依據：`docs/phases/PhaseOB-6計畫.md`（OB-6a；開頭「Q1～Q10 已定」）、`docs/design/21-探索地圖與城鎮.md` 21.5 第 9 點「OB-6 補充」、共用筆記 `台詞-OB5與PR2定稿.md`（「OB-6 字串」「OB-5b 後補定」）與 `台詞-150與147.md`、`docs/開發PM交接.md` 6.5.1／6.5.2。
> 沒有動 `src/trpg/engine/`、`src/trpg/roguelite/`、`client/src/battle/`、`client/src/render/`、`scripts/ob6_newbie_sim.py`、`content/` 的單位與遭遇。**`WORLD_RULES_VERSION` 仍是 25、`CHAR_FORMAT` 仍是 `trpg-char/13`**（`test_versions` 字面值沒動）：只抽函式、改被拒的字、加畫面資料與內容，沒有存檔欄位、沒有改判斷。被拒的動作不寫日誌，所以換字不影響重播。

## 1. 交付項目與 commit

| # | 交付項目 | commit |
|---|---|---|
| 1 | 重選的畫面資料（`reselect_window_problem` 抽出、`RangeReselectView` 新欄位、4＋1 句台詞入檔）＋ 4 卡片字的伺服器端、5 字串收尾的後端（雇用與影子句、成長面板、配點提醒）＋ T1～T3 測試＋重產 `openapi.json`／`schema.d.ts` | `7bb6cfd3` |
| 2、3、4、5、6、7 | 重選頁＋確認彈窗、入口（葛蘭面板／主城靶場面板／頂列）、完成彈窗→三選一、任務欄小牌、卡片一行、配點補句、成長面板後半句、美術追蹤①②、vitest | `d4080963` |
| 8 | 截圖 `docs/art/shots/ob6/`（10 張） | `632aeb60` |
| — | 本報告、上手筆記 | 本報告的 commit |

後端與前端各自是一個 commit（後端欄位、測試、型別互相依賴，拆開會有中間狀態測試不過）；項目對照見上表。

### 1.1 改了什麼

**後端**
- `world/opening_reselect.py`：抽出 `reselect_window_problem(char)`（未選定／開局已結束／等級／已用過，**同一句、同一個順序**），`reselect_problem` 先呼叫它再查地點、遭遇、閃現；`starter_item_id` 抽出 `weapon_item_id`。`tests/world/test_opening_reselect.py` 全過。
- `world/opening.py`：`_STARTER_BLOCKED` 雇用一列改用 `HIRE_PANEL_ZH`（「入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵」），影子打法分開一列 `SHADOW_AI_ZH`（定稿句）。只換字、不改判斷。之後 `limits["hire"]`＝隊伍面板＝被拒句。
- `api/world_range*.py`：`RangeReselectView` 加 `window_open`、`place_zh`（`place_problem(…, "重選")`）、`in_capital`、`here_zh`（標題牌的地方）、`speaker`、`lines`、`done`、`npc`、`objects`。
- `content/world/newcomer.yaml`＋`content/world_newcomer.py`：`range.reselect`（葛蘭「重選開場」）、`reselect_capital`（守印人「主城重選」）、`reselect_done`（葛蘭「重選完成」）、`reselect_capital_done`（Q3 定稿）、`reselect_reminder`（葛蘭「提醒 4 級前可重選」）；預設空，舊檔照讀。
- `api/opening_gear_note.py`（新）：入門期入門武器卡「入門配備是借的，正式選定時會換成你自己的。不能賣、寄、分解。」；正式選定後、還有重選資格時起始武器本體卡「{4} 級前重選的話，這把會被收回。」（數字讀 `OPENING_END_LEVEL`）。接在 `HeroGearSlotOut.opening_note_zh`（穿戴中）與 `BagItemView.opening_note_zh`（背包）。
- `api/world_growth_view.py`：`GrowthView.starter_note_zh`（入門期）＝「入門期可以自己配點，正式選定時會照新武器重配一次。」；前半句照現在的 `SERVICE_ZH` 不動。
- `api/world_newcomer_view.py`：`LessonView.reselect_reminder`（`respec` 的配點教學、還有重選資格時才有）。

**前端**
- `RangeScreen.tsx` 的 `reselect` 模式：沿用正式選定整頁；標題牌「重選／{地方}・換一次武器與 2 個關鍵字」；說話的人與台詞讀 `reselect.speaker/lines`（主城＝守印人金框）；不查也不顯示推薦與推薦說明句；第一次打開預填目前的武器與關鍵字；「確定重選」先開 `ReselectConfirmDialog`（`DialogFrame`），列 `reselectConfirmLines`（會收回的招、起始武器收不收、`lost_zh` 原句、只有一次），確認才送 `opening_reselect`；被拒原因照 OB-5 的三處顯示；等待提示。
- `WorldScreen.tsx`：`reselectOpen` 狀態，**只由按鈕打開**（頂列「重選武器與關鍵字」、葛蘭面板與主城靶場面板的「重選」鈕，`ReselectEntry.tsx`）；離開能重選的地方、用掉、換角色就收起來；完成後先出 `done` 彈窗、按「好」才開三選一（沿用 `holdOffer`）；配點教學（`respec`）收尾彈窗加第二段提醒（`allocateClosingLines`）。
- `WorldHud.tsx`：任務欄小牌「{before_level} 級前可重選一次」（`window_open` 才顯示，前端不比等級），`<Hint>` 說明卡寫伺服器的地點句。
- `BagScreen.tsx`：穿戴中那一格的說明卡第一行、背包裡的起始武器卡多一行（伺服器的字）。
- `OpeningDialog.tsx`：選定後配點教學補「每顆屬性管什麼，成長面板上都有寫。」；`WorldGrowth.tsx` 接 `starter_note_zh`。
- 美術追蹤：①`QuestLog.tsx` 的三選一每次開啟（含換下一組）把自己與外面捲動的容器捲回最上面（`scrollToTop`）；②`SmithyPanel.tsx`／`crafting.ts` 入門期（伺服器 `limits.smith` 有值）部位下拉預設第一個防具；③補拍見第 2.3 節。
- `api/types.ts`：`WorldAction` 加 `OpeningReselectAction`。

## 2. 逐條驗收

| 條件 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0、0 |
| `uv run mypy` | 0（Success: no issues found in 1441 source files） |
| `lint-imports` | 0（14 kept, 0 broken） |
| `pytest tests/world -n 8` | 0（1254 passed） |
| `pytest tests/api -n 8` | 0（925 passed、1 skipped） |
| `pytest tests/content tests/narrative tests/test_architecture.py -n 8` | 0（3161 passed） |
| T1～T3 | 在 `tests/api/test_ob6_reselect.py`（14 個，含在上面 `tests/api` 那批） |
| `corepack pnpm -C client typecheck` | 0 |
| `corepack pnpm -C client test` | 0（284 檔、3472 個） |
| `corepack pnpm -C client build` | 0 |
| `tests/api/test_openapi_snapshot.py` | 過（型別已重產，在 `tests/api` 那批） |
| `WORLD_RULES_VERSION` 25、`CHAR_FORMAT` `trpg-char/13` | 沒動；`tests/world/test_opening_stages.py::test_versions` 過 |
| 浮動卡實測 1600×900、800×600 | 見 2.1，全過 |
| `__layoutSmoke.runCase` 1600×900、1040×624、800×600 | 三個都「全 PASS」（各 12 項；`localStorage.clear()` 後開 `/?dev=1&anim=0.1&mute=1`） |
| 截圖 ≤ 10 張、jpg 80、單張 ≤ 300 KB | 10 張，最大 263 KB（見 2.3） |
| 新增或改的字逐字對照定稿 | 見第 4 節 |
| 前端靶場四個檔沒有技能 ID、沒有寫死「主城」 | `range.test.ts` 的兩個掃描過（`RangeScreen.tsx` 新增的字沒有「主城」） |

沒有跑：`scripts/check.py`、戰鬥重播（沒動引擎）、模擬。

**T1（`tests/api/test_ob6_reselect.py`，打 `POST …/actions`；角色照 `test_opening_choice.py::_played` 真的 AI 代打第 1、2 步，經 API 正式選定、選完兩組三選一）**

| 情況 | 測試 |
|---|---|
| 霧渡鎮、3 級、沒用過 → 成功；`window_open` 變假、`used` 真、重出第 1 組三選一 | `test_reselect_in_mentor_town` |
| 主城 → 成功；說話的是守印人、`done` 是 Q3 定稿 | `test_reselect_in_capital_speaker_is_keeper`（用 `field_library`，守印人頭像在主城實地地圖） |
| 野外 → 被拒＝地點句＝`blocked_zh`；`window_open` 仍真 | `test_reselect_in_the_wild_is_refused_but_badge_stays` |
| 第二次 → 「免費重選只有一次，已經用過了」 | `test_second_reselect_is_refused` |
| 到 `before_level` → 「已到 4 級，免費重選已結束」；`before_level`＝被拒的等級 | `test_reselect_ends_at_before_level` |
| 入門期 → 沒有 `reselect`；送了被拒 | `test_no_reselect_in_starter_period` |
| 有沒處理的遭遇 → 被拒＝`blocked_zh` | `test_pending_encounter_blocks_reselect` |
| 換過主手、起始武器賣掉、背包滿 → 被拒、角色完全不變、`reselect_used` 仍假 | `test_full_bag_after_swapping_main_hand_is_refused` |
| 開局已結束 → 沒有 `opening`；送了被拒 | `test_finished_opening_has_no_reselect` |
| 變／不變逐欄比、`returned_zh`＝實際收回的招、`weapon_returned`＝真的被拿走 | `test_what_changes_and_what_stays` |

**T2**：`test_hire_and_shadow_reasons_in_starter_period`（被拒句＝`HIRE_PANEL_ZH`＝`limits["hire"]`＝畫面 `limits`＝隊伍面板 `hire_problem_zh`；影子打法＝`SHADOW_AI_ZH`）。
**T3**：`test_starter_weapon_card_and_every_cannot_is_refused`（卡上「賣」「寄」「分解」各送一次，都被拒、角色不變；見待決 1）、`test_chosen_weapon_card_note_only_while_reselect_is_open`、`test_full_bag_after_swapping_main_hand_is_refused`（背包裡的起始武器卡）。另 `test_allocate_lesson_carries_reselect_reminder`（Q2）。

**vitest**：`range.test.ts` 新 describe「OB-6 重選頁、確認彈窗、入口、小牌」7 個（模式切換、`reselect` 不自動開——`setReselectOpen(true)` 只出現在三顆鈕、入口判斷、小牌顯示條件、確認彈窗列的項目全部來自資料、台詞定稿逐字）；`limits.test.ts` 新 5 個（三選一捲回最上面、鐵匠預設防具、穿戴中卡片那一行、配點補句、成長面板）。

### 2.1 浮動卡實測（自己啟動的無頭 Chrome，`--mute-audio`，網址帶 `?mute=1`；真的滑鼠事件）

| 位置 | 尺寸 | 滑過開卡 | 滑進卡片仍開 | 卡內捲到底 | 點一下釘住 | 移開仍開 | Esc 關閉 |
|---|---|---|---|---|---|---|---|
| 任務欄小牌的說明卡 | 1600×900 | 是（卡在視窗內） | 是 | 是（內容一屏，捲動高度 0，卡片不關） | 是（`pinned`） | 是 | 是 |
| 同上 | 800×600 | 是（任務欄窄版預設收合，先按捲軸圖示展開） | 是 | 是（同上） | 是 | 是 | 是 |
| 重選確認彈窗 | 1600×900、800×600 | 共用 `DialogFrame`（不是浮動卡，沒有滑過開／釘住）：兩個尺寸都整個在視窗內（800×600：480×181，不用捲動），按鈕可按，「再想想」關閉；截圖 `3-confirm-1600-800.jpg` | | | | | |

### 2.2 怎麼到那些狀態

自己啟動的 `trpg serve`（8116，`TRPG_SAVE_DIR` 指到暫存區，`TRPG_LLM_BASE_URL` 指到不存在的 8119，`TRPG_DEV_ROUTES=1`）＋正式 build。角色是**伺服器停著時用暫存區的腳本做的**（同 OB-5 第 3 節的做法）：API 建角四個，再換成 `_played` 真的 AI 代打打完渡口石階、竹林小徑的狀態（遠程入門期、3 級、在霧渡鎮），其中兩個再經 API 正式選定（雙手劍＋倒地、點燃）並選完兩組三選一，一個放到主城。所以這幾份存檔的世界日誌和角色對不上，只用來拍圖。之後的操作（重選、確認、三選一、配點教學、點葛蘭、走到主城靶場按 E、傳送到主城、鐵匠、背包）都是在瀏覽器裡實際按的。選大類頁那張是在瀏覽器新建的角色。

### 2.3 截圖（`docs/art/shots/ob6/`，每張都打開看過）

| 檔名 | 內容 |
|---|---|
| `docs/art/shots/ob6/1-reselect-gran-1600.jpg` | 重選頁（霧渡鎮，葛蘭台詞與頭像，預填雙手劍＋點燃、倒地，沒有推薦） |
| `docs/art/shots/ob6/2-reselect-keeper-1600.jpg` | 重選頁（主城，守印人金框，標題牌「樞島工坊靶場」） |
| `docs/art/shots/ob6/3-confirm-1600-800.jpg` | 確認彈窗 1600×900 與 800×600（合圖） |
| `docs/art/shots/ob6/4-done-dialogs.jpg` | 霧渡鎮重選完成（葛蘭）、主城重選完成（守印人）、配點收尾彈窗＋重選提醒（推薦配法與略過兩種）（合圖） |
| `docs/art/shots/ob6/5-tracker-badge.jpg` | 任務欄小牌＋說明卡 1600 與 800（合圖） |
| `docs/art/shots/ob6/6-weapon-cards.jpg` | 入門武器卡（入門期）、起始武器卡（還能重選）（合圖） |
| `docs/art/shots/ob6/7-offer-top-smithy.jpg` | 三選一開在最上面、第 1 組捲到下面選完後第 2 組回到最上面、入門期鐵匠預設「頭」（合圖） |
| `docs/art/shots/ob6/8-portraits-3x.jpg` | 選大類頁守印人金框、葛蘭頭像，3 倍（`deviceScaleFactor` 3）（合圖） |
| `docs/art/shots/ob6/9-patrol.jpg` | 巡檢四類：①點葛蘭本人重開正式選定、主城靶場物件按 E 重開；②略過配點、換地點後到主城再提示；③1024×768、768×1024；④觸控 390×844（合圖） |
| `docs/art/shots/ob6/10-gran-panel-entry-1600.jpg` | 葛蘭面板上方的「重選」鈕（Q1 入口） |

### 2.4 巡檢四類（OB-5 沒看的）

| 類 | 結果 |
|---|---|
| ① 點葛蘭本人／主城靶場物件重開正式選定 | 霧渡鎮：點葛蘭的格子→走過去→開整頁。主城：走到靶場旁按 E→開整頁（守印人）。都正常。 |
| ② 略過配點後的再提示 | 按「之後再說」→（收尾彈窗：「隨時回來找我。」＋重選提醒）→傳送到主城→出再提示（「上次沒動的屬性點還照推薦配著…」）。正常。 |
| ③ 768 與 1024 寬 | 兩個尺寸都沒有橫向捲動、HUD 都在；768 寬頁首按鈕換兩行（既有）。 |
| ④ 觸控（停用原因怎麼看得到） | 390×844 觸控模擬：點停用的「換種族」不會開說明卡（停用鈕不收事件），但原因寫在鈕旁的括號裡，成長面板上緣也列了入門期的三條限制，所以看得到。 |

## 3. 改到的既有測試斷言（都不是放寬規則）

| 檔案 | 改了什麼 | 為什麼 |
|---|---|---|
| `tests/world/test_opening_limits.py` `CLOSED` | `hire` 期待句改 `HIRE_PANEL_ZH`、`shadow_ai` 改 `SHADOW_AI_ZH` | (b)、Q9 換字；仍斷言被擋 |
| `tests/api/test_ob5_screen_data.py` | 隊伍面板那句改回「＝`limits["hire"]`」 | (b) 統一成一句 |
| `client/src/world/range.test.ts` | `reselect` 模式從「渲染成空字串」改成「畫出重選頁、沒有推薦」 | OB-6 本來就要畫；`rangeMode` 判斷沒改 |
| `client/src/world/limits.test.ts` | 三選一 effect 的原始碼比對多一行 `scrollToTop(top.current)` | 美術追蹤① |

`tests/world/test_opening_stages.py` `GATE_REASONS`、`questTracker.test.ts`、`growth.test.ts` 不用改（沒有斷言到換掉的字）。

## 4. 字串

**逐字照定稿入檔／入程式的**：葛蘭「重選開場」「重選完成」「提醒 4 級前可重選」、守印人「主城重選」（`台詞-150與147.md`）；守印人主城重選完成、入門武器卡片、起始武器卡片、改影子打法被拒、野外隊伍面板（OB-6 字串表）；雇傭兵統一句、配點教學補句、成長面板後半句（OB-5b 後補定）。`range.test.ts`「內容檔的重選台詞（定稿逐字）」與 `test_ob6_reselect.py` 比對。

**暫寫**（重選頁、確認彈窗、入口、小牌說明卡）：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\暫定字串-OB6.md`（欄位：位置、現在的字、出現時機）。

**(a) 地名牌盤點**

| 位置 | 目前的字 | 地點牌／區域名／通稱 | 改了沒 |
|---|---|---|---|
| 世界畫面左上頁首（`WorldMapView.name_zh`） | 主城時「樞島」 | 地點牌 | 已是地名（OB-5b），不改；實機截圖可見 |
| HUD 地名牌（`field.name_zh`） | 「樞島」 | 地點牌 | 已是地名，不改 |
| 正式選定／重選標題牌 | 「樞島工坊靶場」 | 地點牌 | 重選頁本段新加，讀 `capital_name` |
| 小牌說明卡、重選被拒地點句 | 「…或到樞島的工坊靶場」 | 地點句 | 讀地名（OB-5b 的 `place_problem`），不改 |
| 試打戰鬥右上 `rangePlaceName` | 「樞島・工坊靶場」 | 地點牌 | 屬 PR-2，不動 |
| 角色列表 | 「主城・樞島」 | 區域名＋地名 | 不改（實機確認沒被改成「樞島・樞島」） |
| 地點面板「傳送到主城」、大世界圖、傳送清單 | 「主城」 | 區域名 | 不改（實機確認仍是「主城」） |
| 建角「建立並在主城醒來」、說明「主城工坊靶場」「主城樞島醒來」 | 「主城」 | 通稱 | 不改 |
| 首頁「在主城樞島醒來」 | 「主城」 | 通稱 | 不改 |
| 外觀「之後在主城可以隨時免費改」「（主城隨時免費）」、被拒「只有在主城能改外觀／換種族」 | 「主城」 | 通稱 | 不改 |
| `api/world.py` 舊建角錯誤「到主城工坊靶場再選」 | 「主城」 | 通稱 | 不改 |
| 開發頁（`client/src/dev/*`） | 「主城樞島」等 | 開發用 | 不改 |

沒有找到還寫死「主城」的地點牌。

## 5. Q1～Q10 實際照哪個做

| # | 做法 |
|---|---|
| Q1 | 照預設：不自動開、不攔截點葛蘭；葛蘭面板、主城靶場面板（`choose_objects`：靶場、工坊師傅）上方各一顆「重選」，人在能重選的地方時頂列一顆「重選武器與關鍵字」 |
| Q2 | 照預設：接在配點教學收尾彈窗第二段，不記新旗標；伺服器只在還有重選資格時給（略過與照推薦兩種收尾都接） |
| Q3 | 改：主城重選完成出說話彈窗（守印人定稿句） |
| Q4 | 改：入門武器卡用定稿句；起始武器卡加定稿句，只在還能重選時 |
| Q5 | 照預設：重選頁與確認彈窗的字暫寫，列進 `暫定字串-OB6.md` |
| Q6 | 照預設：照 `window_open`，不管人在哪；說明卡寫 `place_problem(…, "重選")` |
| Q7、Q8 | OB-6b 的事，本段沒碰 |
| Q9 | 改：影子打法分開一列，用定稿句 |
| Q10 | 改一半：野外前綴「現在不能換隊友：」不動，入門期原因接在後面（伺服器的 `hire_problem_zh` 已是新句，前端沒改） |

## 6. 實機未看、沒驗證

- **主城靶場面板上的「重選」鈕**：只有 vitest（`opensReselect`、`ReselectEntry` 渲染）；實機拍的是葛蘭面板那顆與頂列。
- **重選被拒（背包放不下）的畫面**：只有 pytest（API）與沿用 OB-5 的錯誤顯示，沒有截圖。
- **人在野外時的小牌**：只有 pytest（`window_open` 仍真）與 vitest；實機拍的是主城與霧渡鎮。
- **重選的等待提示**：本機回應不到 0.4 秒，沒拍到；有 vitest。
- 隊伍面板、野外隊伍面板的新句：pytest（T2），沒有截圖。
- 「這把武器沒有某關鍵字的起始技能」的停用樣子：內容裡仍沒有這種組合（同 OB-5）。
- 觸控只看了成長面板的停用鈕。

## 7. 待 PM 決定

1. **T3「不能賣、寄、分解」靠「送不出去」成立**：入門期主手不能換，入門武器永遠不是背包物品，所以賣（`item` 格式不合，422）、寄、分解（背包找不到）都被拒，但不是專門的入門期原因句。規格 T3 的例子說這種情況「不能寫在卡上」，但 Q4 定稿要寫；我照定稿寫並補了被拒測試。要改成專門的擋法或拿掉卡上那半句請定。
2. **窄版（< 1040）任務欄預設收合時看不到小牌**（要按捲軸圖示展開）。要不要在收合的圖示上加標記？
3. **面板上的「重選」鈕只在能重選時出現**；不能重選（例如有遭遇）時不顯示鈕、也不寫原因（頂列鈕同）。小牌仍在。
4. **鐵匠預設防具**用前端常數 `ARMOR_SLOT_TYPES`（頭、身體、手、腳，同 8.12）挑第一個；只是預設值，送出仍由伺服器擋。若要完全由伺服器給，要在打造資料加欄位。
5. **重選提醒也接在「之後再說」的收尾彈窗**（「隨時回來找我。」＋提醒）。若只要接在配完的那一種，改一處。
6. **影子打法被拒句只在送出時看得到**：影子面板只停用設定（`can_set_ai`），沒有原因欄位（OB-5 起如此）。要顯示的話需加欄位。
7. **確認彈窗的武器名**：起始武器還在手上時寫「會收回起始武器「雙手劍」」；換過主手（起始武器在背包）時不寫名字。
8. **重選完成彈窗的標題用「重選」**、按鈕「好」（同正式選定）。
9. 入門期若背包裡有一件和入門武器同 ID 的基礎武器（別人寄來），它的卡也會寫入門武器那句（同上手筆記第四節第 10 點的已知限制）。

## 8. 上手筆記

- `docs/dev/上手-roguelite開局與入門期.md`：第一節（檔案表：`opening_reselect` 的新函式、`opening_gear_note.py`、`ReselectEntry.tsx`、前端靶場檔的說明）、第二節「畫面資料」（重選的新欄位與入口、`LessonView.reselect_reminder`、`GrowthView.starter_note_zh`）、第四節第 16、17 點、第五節測試表兩列。
- `docs/dev/上手-前端戰鬥畫面與動畫.md`：第四節第 18 點（沒有 Playwright 時用 CDP 驅動無頭 Chrome、3 倍特寫、換角色）。沒有動到共用元件。

## 9. 給使用者重開伺服器檢查的重點

`content/world/newcomer.yaml` 有新台詞，要重開伺服器。用一個已正式選定、4 級前的角色：霧渡鎮點葛蘭（面板上方有「重選」）或頂列「重選武器與關鍵字」→ 換武器與關鍵字 →「確定重選」看確認彈窗 → 確定後葛蘭的話 → 按「好」才出三選一；任務欄的「4 級前可重選一次」小牌滑過看說明。入門期角色：背包（I）滑過主手看「借的」那一行、鐵匠打造部位預設「頭」。

## OB-6c 補件

> 依據：美術 PM 的 OB-6a 驗收（`0cb9e4ce:docs/art/OB-5檢查.md` 末節：必修 M1～M3、可修 1、「窄版小牌：建議收合時露一個點」）。只動前端兩個檔＋測試；沒有後端、內容、存檔欄位的改動。

### 交付

| # | 內容 | commit |
|---|---|---|
| 1 | 窄版任務欄收合時的提醒點：`range.ts` 新增 `trackerFoldDot(reselect, collapsed)`（收合且 `reselectBadge` 不是 `null`＝伺服器的 `window_open` 為真時，回小牌的字；前端不比等級）；`WorldHud.tsx` 收合鈕（`IconButton` 捲軸圖示）傳 `badge={ tone: "red" }`，**沿用功能列現成的通知點**（`IconButton` 內的 `Dot` → `.world-hud-dot.red`，同成長鈕 G 的紅點），沒有新樣式；滑過的字改成「4 級前可重選一次。任務追蹤（N 條）：點了展開」，走 `IconButton` 原本的 `<Hint>`（共用浮動卡），沒有 `title=` | `bb42fd9b` |
| 2 | 補截圖 5 張（見下表） | 本節的 commit |
| 3 | 本節 | 本節的 commit |

說明：點只看「收合」與資格，不看寬度——寬版玩家手動收合時也會出現（寬版預設展開，所以平常看不到）。若要只限窄版，在 `trackerFoldDot` 多傳 `layout.narrow` 即可。

### 測試

- `client/src/world/hud.test.ts` 新 describe「OB-6c 窄版任務欄收合時的重選提醒點」2 個：`有資格且收合：收合鈕右上有通知點…`（渲染 `WorldHud`，收合鈕裡有 `world-hud-dot red`、`aria-label` 以「4 級前可重選一次。」開頭）、`沒資格或展開：沒有點`（`window_open` 假、沒有 `opening`、展開三種都沒有點；展開時小牌仍在）。
- `corepack pnpm -C client exec vitest run src/world/hud.test.ts src/world/range.test.ts src/ui/floatCardRule.test.ts`：3 檔 122 個全過。
- `corepack pnpm -C client typecheck`：0。`corepack pnpm -C client build`：0。
- 沒有跑：整包 vitest、`scripts/check.py`、pytest（沒動後端）。

### 浮動卡實測（自己啟動的無頭 Chrome，`--mute-audio`，網址帶 `?mute=1`，CDP 真的滑鼠事件）

| 位置 | 尺寸 | 滑過開卡 | 滑進卡片仍開 | 卡內捲到底 | 點一下釘住 | 移開仍開 | Esc 關閉 |
|---|---|---|---|---|---|---|---|
| 收合鈕（捲軸圖示＋紅點）的說明卡 | 800×600 | 是（卡在鈕上方、視窗內：556,162，240×52） | 是 | 內容一屏（捲動高度 0），卡片不關 | 是（`pinned`） | 是 | 是 |

`window.__layoutSmoke.runCase` 800×600（`localStorage.clear()` 後開 `/?dev=1&anim=0.1&mute=1`）：「全 PASS」（12 項）。

### 截圖（`docs/art/shots/ob6/`，每張都打開看過；最大 137 KB）

| 檔名 | 對應 | 內容 |
|---|---|---|
| `docs/art/shots/ob6/c-1-capital-range-reselect-1280.jpg` | M1 | 1280×800，主城（樞島）走到工坊師傅旁按 E：面板上方「重選」鈕＋「4 級前可以免費換一次武器與關鍵字」 |
| `docs/art/shots/ob6/c-2a-reselect-390-full.jpg` | M2 | 390 寬重選頁整頁（視窗拉到整頁高 390×2056，黏底列在最下面） |
| `docs/art/shots/ob6/c-2b-reselect-390-sticky.jpg` | M2 | 390×844 捲到中段：黏底列「拿起試打／先不換／確定重選」三顆在畫面內（量到右緣 364 ＜ 390，三顆 `scrollWidth`＝`clientWidth`，不溢出） |
| `docs/art/shots/ob6/c-3-tracker-dot-800.jpg` | M3 | 800×600 霧渡鎮，任務欄收合：捲軸圖示右上紅點＋滑過的說明卡「4 級前可重選一次。…」 |
| `docs/art/shots/ob6/c-4-smithy-head-2x.jpg` | 可修 1 | 入門期鐵匠打造，2 倍（`deviceScaleFactor` 2）局部：部位預設「頭（通用料 ×1）」、上方「入門期的…只限防具」 |

### 怎麼到那些狀態

自己啟動的 `trpg serve`（8116，`TRPG_SAVE_DIR` 在暫存區，`TRPG_LLM_BASE_URL` 指到不存在的 8119，`TRPG_DEV_ROUTES=1`）＋正式 build、無頭 Chrome（除錯埠 8117）。角色在伺服器啟動前用暫存區的腳本做（照 `tests/api/test_ob6_reselect.py` 的 `_starter_played`／`_chosen`：API 建角 → `_played` 真的 AI 代打 → 經 API 正式選定、選完兩組三選一；主城那個再把 `region`／`location` 改成主城），三個：霧渡鎮已選定、主城已選定、霧渡鎮入門期。之後的操作（關「你不在的時候」、配點教學、走到工坊師傅按 E、開頂列重選、按「之後再選」、開鐵匠）都在瀏覽器裡按。沒有碰使用者的存檔。

### 實機未看

- 寬版手動收合時的點：只有 vitest（同一條判斷）。
- 人在野外、收合時的點：只有 vitest（`window_open` 照伺服器，不看地點）。
