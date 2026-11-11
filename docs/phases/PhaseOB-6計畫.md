# Phase OB-6｜#150 前端第二段（重選畫面、小牌、入門武器卡片、字串收尾）與入門配備小模擬

> 規則來源：`docs/design/21-探索地圖與城鎮.md` 21.5「開局先玩再定」第 1、5、7 點與第 9 點（重選的邊界、回滿、4 級前、OB-2／3／4／5 補充）；`docs/design/18-雲嶺內容.md` 18.7.1（新手第 1～3 步）；`docs/玩法決定紀錄.md` #150、#149「CB-2a 審核」「CB-2d 審核」①、附錄 6F-4b／6F-4c 列（#139 已確認）。
> 畫面來源：`docs/art/OB與PR移植需求.md` 第 2 節 OB-6（樣張沒畫：照 `DialogFrame` 與既有樣式，交件時美術檢查）、`docs/art/OB-5檢查.md` 第 2 次的「追蹤」。
> 文字來源：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\台詞-OB5與PR2定稿.md`（**「OB-5b 後補定」＞「美術驗收後補定」＞「OB-5 暫定字串定稿」＞「補定」＞其他表**）、`...\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\台詞-150與147.md`、`...\local_c2d54362-...\暫定字串-OB5.md`。
> 前置：`docs/phases/PhaseOB-5報告.md`（含第 8 節 OB-5b）、`PhaseOB-3報告.md` 第 4、5、7 節、`PhaseOB-4報告.md` 第 6、7 節、`PhaseCB-2d報告.md`「雨中梯田」。

## 待開發 PM 確認（派工前回答；沒回答就照「預設」做，並寫進報告）

| # | 問題 | 出處 | 預設（最保守） |
|---|---|---|---|
| Q1 | **重選畫面從哪裡打開**。21.5 只寫「到葛蘭或主城靶場重選」。OB-5 的正式選定是「點葛蘭直接開整頁」（入門期很短）；重選窗口一直開到 4 級，若照搬，選定後到 4 級前點葛蘭都進不了對話（配點教學、閃現引導都靠葛蘭）。 | 21.5 第 5 點、OB-5 報告待決 6、21.5「OB-5 補充」第 2 點只講正式選定 | 不自動開、不攔截點擊；葛蘭的 NPC 面板與主城靶場（`choice.objects` 同一批物件）的面板各加一顆鈕開重選頁；人在可重選的地方時頂列也留一顆鈕（比照 `CHOOSE_OPEN_LABEL`） |
| Q2 | 葛蘭「提醒 4 級前可重選」那句**什麼時候說**。台詞檔只有句子沒有時機。 | `台詞-150與147.md` 葛蘭表第 7 列 | 接在正式選定後的配點教學收尾彈窗（`allocate_respec_done_zh`）同一個彈窗的第二段；不另開彈窗、不記新旗標 |
| Q3 | **在主城重選完成沒有完成台詞**（守印人只有開場「主城重選」一句；葛蘭「重選完成」是在霧渡鎮說的）。 | `台詞-150與147.md`；OB-5 報告待決 5（正式選定同樣情況，後來補了 `choose_capital_done`） | 主城重選完成不出說話彈窗，只有事件句；三選一照常出。請玩法 PM 給一句後再補 |
| Q4 | **入門武器的背包卡片寫什麼**。定稿檔沒有這張卡的字；規則是「入門武器與入門招不能賣、寄、分解」。另：正式選定後的「起始武器」重選時也會被收回，卡片要不要寫。 | 21.5 第 1 點、第 9 點「重選的邊界」；定稿「選大類」表「借」的說明 | 入門武器卡加一行，前半照定稿「入門配備是借的，正式選定時會換成你自己的。」、後半暫寫「不能賣、寄、分解。」；起始武器卡不加。全部列進暫定字串請玩法 PM 定 |
| Q5 | **重選頁與確認彈窗的字**（標題牌、按鈕、彈窗標題、「會收回」「材料不退」「起始武器已不在」各行）定稿檔沒有。 | 定稿檔各表；`暫定字串-OB5.md` 第 2 節最後一列 | 實作者暫寫、數字讀資料（`before_level` 等），全部列進 `暫定字串-OB6.md` 給玩法 PM |
| Q6 | 任務欄小牌「4 級前可重選一次」**在不能重選的地方也顯示嗎**（例如人在野外）。 | 開發 PM 交接 3.000 第 3 點第 3 項（只有字）；盤點 5.1 | 只要還有資格（已正式選定、沒用過、等級 < `before_level`）就顯示，不管人在哪；說明卡寫去哪裡重選（用 `place_problem(…, "重選")` 那句的地點） |
| Q7 | **小模擬的「每格」怎麼分**。CB-2d 的 42% 是舊流程 4 種開局（火焰法杖點燃＋帶電、匕首冰凍＋隱蔽、巨劍倒地＋撞擊、弓標記＋高處）；新流程第 1、2 步只有 3 個大類，第 3 步才是正式配備。 | #149「CB-2d 審核」①「每格至少 80 人」；附錄 6F-4c 列「每種開局量 40 人」 | 第 3 步沿用 CB-2d 的 4 種正式配備當 4 格（可和 42% 對照），第 1、2 步用各自大類的入門配備（火焰法杖→法器、匕首與巨劍→近戰、弓→遠程）；每格 80 人。另一種讀法（3 大類 × 入門武器＋推薦關鍵字）不做 |
| Q8 | **調 `terrace_patrol` 可以動到哪裡**。「敵方至少 2 名、不減人」寫的是 `terrace_clash`；巡邏沒寫。`sect_acolyte` 同時是 `terrace_clash` 的第三方。 | #149「CB-2a 審核」；`content/world/encounters/cloud_ridge.yaml` 第 26、28 行 | 不減人、不換陣容結構；只把巡邏的兩名改成新的梯田專用變體單位 `sect_acolyte_terrace`（比照 CB-2d 的 `bandit_rookie_terrace`）調 HP；`sect_acolyte` 本體與 `terrace_clash` 不動 |
| Q9 | 雇傭兵句統一後，**改影子打法**（`ShadowAiAction`）被拒也變成「入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵」嗎（現在兩個動作共用同一列）。 | `src/trpg/world/opening.py` `_STARTER_BLOCKED`；定稿「OB-5b 後補定」第 2 列 | 照現況共用同一列，一起換成新句 |
| Q10 | 野外的隊伍面板（`FieldPanels.tsx` 第 68 行）前綴是「現在不能換隊友：」，和玩法 PM 說的「換隊友：」不同。 | 定稿「OB-5b 後補定」第 2 列 | 只改玩法 PM 點名的隊伍面板（`PartyPanel.tsx`，已是「換隊友：」）；野外那行不動，列進報告 |

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| (a) 區域名與地名（玩法 PM 回 OB-5b 待決 1） | **區域名＝主城、地名＝樞島**。`CAPITAL_NAME_ZH` 不改；大世界圖、傳送清單、角色列表「主城・樞島」照舊。只有**標示所在地點的牌子**讀地名（內容檔，`world.common.capital_name`）；靶場戰鬥那一處屬 PR-2，其餘在本段。建角、首頁、外觀與換種族的說明和被拒原因、成長面板「改外觀（主城隨時免費）」裡的「主城」是通稱，**不改**。 |
| (b) 雇傭兵（回 OB-5b 待決 2） | 統一成一句：被拒原因也用「入門期隊友固定，找葛蘭正式選定後才能雇用其他傭兵」；隊伍面板前面加「換隊友：」。 |
| (c) 「重新顯示提示」（回 OB-5b 待決 4、5） | 會再自動開一次、重新整理後不再自動開：**維持現狀，不改程式**。 |
| (d) 兩處變短的字（回 OB-5b 待決 6、7） | 選定後的配點教學（不列六顆屬性）補一句「每顆屬性管什麼，成長面板上都有寫。」；成長面板入門期第一行在**現有前半句**後補「入門期可以自己配點，正式選定時會照新武器重配一次。」原句以台詞檔「OB-5b 後補定」表為準；前半句照現在畫面上的字（`api/world_growth_view.py` 的服務說明），不要改成表上的寫法。 |
| 美術追蹤三項（`OB-5檢查.md` 第 2 次） | ① 三選一面板（`WorldOfferPending`）每次開啟時捲到最上面；② 鐵匠面板在入門期部位下拉預設防具；③ 補拍：選大類頁守印人金框、葛蘭頭像 3 倍特寫。 |
| OB-5 沒實機看的四類 | 列為本段實機巡檢：點葛蘭本人／主城靶場物件重開正式選定、略過配點後的再提示、768 與 1024 寬、觸控（停用原因怎麼看得到）。 |
| 重選規則 | 已在 OB-3 做完（`world/opening_reselect.py`），**本段不改判斷**；21.5 OB-3 補充：重選不標推薦、重選後三選一內容不同、入門期先到 4 級沒有重選。 |
| 小模擬門檻 | 新手第 3 步路上（含巡邏）**主角倒下 ≤ 40%，每格至少 80 人**；超標**先調 `terrace_patrol`**，不放寬門檻、不動 `terrace_clash`（#149 CB-2a、CB-2d 審核①；附錄 6F-4b 列）。調整屬原型數值：照最保守做法做完，建議值與前後對照表寫進報告由 PM 決定（守則 8、11）。 |
| 台詞檔還沒用到的 4 句 | 守印人「主城重選」、葛蘭「提醒 4 級前可重選」「重選開場」「重選完成」（`台詞-150與147.md`；`暫定字串-OB5.md` 第 2 節最後一列）。逐字入檔。 |
| 重選相關的後端字串 | `opening_reselect.py` 各拒絕句、地點句、重選事件句：定稿檔「沒列在下表的一律照現在的字定稿」，**不改**（地點句已讀主城地名）。 |

## 切段

前端與模擬改的檔不重疊，切兩段，**可平行派**（各一個實作 agent）：

| 段 | 內容 | 只改這些地方 |
|---|---|---|
| **OB-6a** | 前端＋字串：重選頁與確認彈窗、任務欄小牌、入門武器卡片、4 句台詞、(a)(b)(d)、美術追蹤、實機巡檢 | `client/src/`（不含 `battle/`、`render/`、`render/fixtures/`）、`src/trpg/api/`、`src/trpg/world/opening.py`、`opening_reselect.py`（只抽函式，不改判斷）、`src/trpg/content/world_newcomer.py`、`content/world/newcomer.yaml`、`client/openapi.json`、`docs/art/shots/ob6/` |
| **OB-6b** | 入門配備小模擬＋（超標時）`terrace_patrol` | `scripts/ob6_newbie_sim.py`（新）、`content/world/encounters/cloud_ridge.yaml`、`content/units/sect_acolyte_terrace.yaml`（新，需要時）、`client/src/render/fixtures/unitDolls.json`（只由 `export_client_fixtures.py` 重產） |

平行時的節制：OB-6b 的模擬 `--jobs` 不超過 6；PM 跑全量 `check.py` 期間不跑模擬。兩段都會讓內容 digest 變，合併時不衝突（不同檔）。**PR-2 不能和 OB-6a 平行**（共用 `RangeScreen.tsx`、`WorldScreen.tsx`、`world_range*.py`、`newcomer.yaml`、`schema.d.ts`）。

## 範圍外

- PR-2（工坊師傅選單、測試模式戰鬥版面、出發後回靶場、靶場戰鬥右上的地名）。主城靶場的重選入口只接在 OB-5 已有的靶場物件上，不碰工坊師傅的新選單。
- 重選規則本身（OB-3 已做）、`pick_class` 階段的舊一次選定（OB-5 待決 2，另排整理段）、可以重選時沒有推薦（OB-3 待決 1）。
- `client/src/battle/`、`client/src/render/`（除了 OB-6b 重產的 `unitDolls.json`）、`src/trpg/engine/`、`src/trpg/roguelite/`。
- 不升 `WORLD_RULES_VERSION`（25）、`CHAR_FORMAT`（`trpg-char/13`）：本段只改字、畫面資料與內容。若發現非改規則不可，停下來回報。
- 手機寬戰鬥版面、技能小圖示 Q 版。
- 雨中梯田以外的平衡（竹林、渡口只量不調）。

## 工作環境

- Windows。Python 一律 `uv run python`（直接打 `python` 是商店空殼）；前端 `corepack pnpm -C client …`。**新 worktree 第一次先 `uv sync --frozen`、`corepack pnpm -C client install --frozen-lockfile --offline`**，之後指令加 `UV_NO_SYNC=1`。
- 先讀：OB-6a 讀 `docs/dev/上手-roguelite開局與入門期.md`、`docs/dev/上手-前端戰鬥畫面與動畫.md`；OB-6b 讀 `docs/dev/上手-內容資料與模擬.md`、`docs/dev/上手-roguelite開局與入門期.md` 第二節。
- 預覽埠：OB-6a 用 `trpg serve` 8116、vite 5240～5241；OB-6b 不開伺服器（需要時用 8117）。**不用 8000、8001、5195**。vite 的 `/api` 寫死轉 8000：另寫暫存 vite 設定轉到自己的埠，用完刪，不改 `client/vite.config.ts`。存檔用 `TRPG_SAVE_DIR` 指到暫存區。
- 瀏覽器測試網址一律加 `?mute=1`；無頭 Chrome 加 `--mute-audio`。
- 結束前只用自己記下的 PID 關掉自己開的伺服器、vite、無頭 Chrome，確認沒有殘留；不用 `taskkill /IM`、`pkill`。
- 等背景程序用完成通知，**不寫 `until`／`while` 輪詢迴圈**。
- 開子 agent 一律指定 **Opus 5.5**（Agent 工具 `model: "opus"`），並在 prompt 寫明往下也一樣。
- 不跑 `scripts/check.py`、`trpg sim completion`、不限縮的 `trpg sim matrix`；pytest 平行最多 `-n 8`，`tests/world` 只挑相關檔，交件前整個目錄跑一次。不要 push。每個交付項目一個 commit。

## 受影響的既有功能（第 0 步盤點）

| 區域 | 位置 | 改／不改 | 理由 |
|---|---|---|---|
| 引擎、roguelite | `src/trpg/engine/`、`src/trpg/roguelite/` | 不改 | 重選與選定都在世界層；模擬只呼叫 |
| 世界規則：重選 | `world/opening_reselect.py` `reselect_problem` | 只抽函式 | 小牌要「還有沒有資格」（不含地點、遭遇、閃現），畫面不能自己判斷等級：把等級、已用、未選定三條抽成 `reselect_window_problem`，`reselect_problem` 改成先呼叫它再查地點等，**判斷與順序不變**（`tests/world/test_opening_reselect.py` 全過為證） |
| 世界規則：入門期閘門 | `world/opening.py` `_STARTER_BLOCKED`、`HIRE_PANEL_ZH` | 改字 | (b)：雇用（與改影子打法，Q9）被拒句換成 `HIRE_PANEL_ZH`，之後 `limits["hire"]` 又和面板同一句；只改字不改判斷，被拒的動作不寫日誌，不升版號 |
| 畫面資料：靶場 | `api/world_range.py`、`world_range_schemas.py` `RangeReselectView` | 加欄位 | 小牌與入口要：`window_open`（＝`reselect_window_problem is None`）、`place_zh`（去哪裡重選）、說話的人與台詞（`speaker`、`lines`、`done`，比照 `RangeView.choice`）、`npc`／`objects`（入口，比照 `choice`） |
| 畫面資料：裝備卡 | `api/gear.py`、`gear_schemas.py`（或背包的 view；實作者確認入門武器卡由哪個 view 出） | 加選填欄位 | Q4 的一行字由伺服器給（入門武器靠 `range.starters`／`opening.stage` 認，前端不寫死武器 ID） |
| 畫面資料：成長面板 | `api/world_growth_view.py` 入門期第一行 | 改字 | (d) 補後半句 |
| 畫面資料：隊伍 | `api/world_party_view.py` | 不改程式 | 已用 `HIRE_PANEL_ZH`；(b) 之後與 `limits` 一致 |
| 內容 | `content/world/newcomer.yaml`、`src/trpg/content/world_newcomer.py` | 加欄位 | 4 句：`range.reselect`（葛蘭開場）、`reselect_capital`（守印人）、`reselect_done`（葛蘭）、`reselect_reminder`（葛蘭提醒）；給預設值，舊檔照讀 |
| 內容 | `content/world/encounters/cloud_ridge.yaml`、`content/units/` | OB-6b 視結果 | 只在超標時改 `terrace_patrol`（Q8）；新單位會多一筆 `unitDolls.json` |
| 前端：靶場 | `client/src/world/range.ts`（`rangeMode`、`opensChoose`）、`RangeScreen.tsx`（`mode === "reselect"` 現在回 `null`）、`RangeParts.tsx` | 改 | 重選頁沿用正式選定整頁：不標推薦、預填 `weapon`／`keywords`、按確定先開確認彈窗；`rangeMode` 的 `reselect` **不可自動開**（現在 `WorldScreen` 只對 `choose` 自動開，保持） |
| 前端：世界畫面 | `client/src/screens/WorldScreen.tsx`（`interactHud`、頂列鈕、完成彈窗→三選一的順序 `holdOffer`） | 改 | Q1 的入口；重選完成先出葛蘭的話、按「好」才開三選一（同 OB-5b M5） |
| 前端：任務欄 | `client/src/world/hud.ts`（`trackHint`／`trackedQuests`）與任務追蹤元件 | 改 | 小牌 |
| 前端：背包卡片 | `client/src/world/BagScreen.tsx`、`bagView.ts`（實作者確認） | 改 | Q4 |
| 前端：配點教學 | `client/src/world/OpeningDialog.tsx`（`allocateTotalText` 那一區、收尾彈窗） | 改字 | (d)、Q2 |
| 前端：三選一、鐵匠 | `client/src/world/QuestLog.tsx` `WorldOfferPending`、`SmithyPanel.tsx`／`crafting.ts` | 改 | 美術追蹤 ①② |
| 前端：地名牌 | 盤點所有標示所在地點的牌子 | 視結果 | (a)：OB-5b 已改頁首（`WorldMapView.name_zh`）；逐一確認還有沒有寫死「主城」的地點牌，**同時確認區域名的地方（大世界圖、傳送清單、角色列表）沒被 OB-5b 改成「樞島」**；只改地點牌，通稱不改 |
| 前端：「重新顯示提示」 | `HintsSettingsSection.tsx`、`WorldScreen.tsx` `resetHints` | 不改 | (c) 維持現狀 |
| 存檔、季末重置 | `world/state.py`、`server/season_policy.py` | 不改 | 沒有新存檔欄位（Q2 不記新旗標；若實作者認為需要旗標，用 `hints_seen`，不加欄位） |
| API 型別 | `client/openapi.json`、`client/src/api/schema.d.ts` | 重產 | OB-6a 加欄位 |
| 舊流程與舊角色 | `opening is None` 的角色 | 不受影響 | 沒有重選、沒有小牌（`RangeView` 為 `None`） |
| 既有測試會變的斷言 | `tests/api/test_ob5_screen_data.py`（隊伍面板那句「不再等於 `limits["hire"]`」要改回相等）、`tests/world/test_opening_limits.py` `CLOSED`、`tests/world/test_opening_stages.py` `GATE_REASONS`、`client/src/world/limits.test.ts`、`range.test.ts`（`reselect` 回 `null` 的斷言）、`questTracker.test.ts`、`growth.test.ts` | 跟著改 | 都是字串或畫面行為照本規格變，不是放寬規則；報告逐項列出 |
| 模擬腳本 | `scripts/archive/f4_newbie_sim.py`、`f4c_terrace_sweep.py`、`f4d_terrace_sweep.py`（舊建角路徑，已過時）、`scripts/cb2e_sim.py`（結構範本） | 只參考 | 新腳本照 `cb2e_sim.py` 的結構寫 |

## OB-6a 交付項目（每項一個 commit）

1. **重選的畫面資料**：`reselect_window_problem` 抽出（不改判斷）；`RangeReselectView` 加 `window_open`、`place_zh`、`speaker`、`lines`、`done`、`npc`、`objects`；`newcomer.yaml` 與 schema 加 4 句（逐字照 `台詞-150與147.md`：「主城重選」「重選開場」「重選完成」「提醒 4 級前可重選」）；在霧渡鎮開＝葛蘭說「重選開場」、在主城開＝守印人說「主城重選」；`done` 在霧渡鎮是葛蘭「重選完成」，主城照 Q3。重產 `openapi.json`、`schema.d.ts`。
2. **重選頁＋確認彈窗**：`RangeScreen` 的 `reselect` 模式（沿用正式選定整頁的武器架與關鍵字；不顯示推薦與推薦說明句；預填目前的武器與關鍵字）；按確定先開 `DialogFrame` 確認彈窗，列出 `returned_zh`（會收回的招）、起始武器本體收不收回（`weapon_returned`）、`lost_zh`（材料不退）、「只有這一次」；確認才送 `opening_reselect`。被拒原因顯示在頁上（同 OB-5 被拒的三處）。等待時有等待提示。完成後先出 `done` 彈窗、按「好」才開三選一。入口照 Q1。**不可自動打開**。
3. **任務欄小牌**：「{before_level} 級前可重選一次」（數字讀 `before_level`），顯示條件照 Q6（讀 `window_open`，前端不自己比等級）；滑過用 `<Hint>` 說明去哪裡重選。重選用掉或到期後消失。
4. **入門武器背包卡片文字**：照 Q4，字由伺服器給。
5. **字串收尾**：(b) 雇用被拒句；(d) 配點教學補句、成長面板第一行補後半句；Q2 的提醒句；(a) 地名牌盤點與修正（盤點表寫進報告：位置、目前的字、屬於地點牌或通稱、改了沒）。新寫而定稿沒有的字，列成共用筆記 `...\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\暫定字串-OB6.md`（欄位：位置、現在的字、出現時機）。
6. **美術追蹤**：三選一面板開啟時捲到最上面；鐵匠面板入門期部位下拉預設防具（入門期的判斷讀伺服器既有的限制資料，不在前端另寫）；補拍兩張特寫。
7. **測試**：見「行為一致測試」；新元件與模式切換的 vitest（`rangeMode` 的 `reselect` 不自動開、入口判斷、小牌顯示條件、確認彈窗列的項目來自資料、前端靶場四個檔仍沒有技能 ID 與寫死的「主城」）。
8. **實機巡檢**（OB-5 沒看的四類）：點葛蘭本人／主城靶場物件重開正式選定、略過配點後的再提示、768 與 1024 寬、觸控（`resize_window` 的 mobile 預設會模擬觸控；看停用原因怎麼顯示）。到達狀態的方法照 OB-5 報告第 3 節（AI 代打真的打贏前兩步）並寫明。

## OB-6b 交付項目（每項一個 commit）

1. **`scripts/ob6_newbie_sim.py`**：照 `scripts/cb2e_sim.py` 的結構——子命令 `run`（跑、結果寫 JSON 到暫存區，不進 repo）與 `report`（重印摘要表，不重跑）；平行用 `sim/parallel.py::run_tasks` 或 `ProcessPoolExecutor`，`--jobs` 預設 4、上限 6；`--per-cell`（預設 80）、`--only`、`--candidates`；只印摘要表。
   - **走真實路徑**：`new_character` 建角 → `opening_class`（大類）→ 接新手任務 → 用入門配備打第 1、2 步（BFS 走格、效用 AI 代打；入門期其他敵人看不到，照 OB-4）→ 回霧渡鎮 `opening_confirm`（Q7 的正式配備）→ 兩組延後三選一一律選第 1 張（有待選三選一時不能做別的動作）→ 走到雨中梯田，**路上碰到的每一場都打**（巡邏＋`terrace_clash`）。不要手拼 `BattleSetup`。走法參考 `scripts/archive/f4_newbie_sim.py`，建角與開局改走新流程。
   - **種子固定**：世界種子、角色 ID、開局種子都由（格, 第 i 人）決定（例：`base + i`），**不用 `secrets`**；同一個人在現況與各候選之間**配對**（第 1、2 步只跑一次，到第 3 步才分支換內容）。
   - **格**：照 Q7。第 1、2 步的表以大類彙總；第 3 步的表以 4 種正式配備為格。
   - **輸出兩張表**：① 第 1、2 步（每大類）：渡口、竹林各自的勝率、主角倒下率（分子/分母）、平均輪數、兩招入門招每場使用次數；② 第 3 步路上（每格）：主角倒下率（分子/分母；分母＝走到第 3 步路上的人數，分子＝路上任何一場主角倒下過）、倒在巡邏／固定戰的人數、固定戰勝率、平均輪數，最後一欄「≤ 40%？」。表頭寫明樣本數、種子範圍、每格人數。
2. **跑兩次為上限**：先用 `--per-cell 2` 做一次冒煙（不算結果，用來估時間；預估全量超過 40 分鐘就先回報，不要跑）。全量第 1 次只跑**現況**。全部格 ≤ 40%：結束，不改內容。有格超標才跑第 2 次：**同一批種子**跑候選（含現況共最多 4 組，寫死在腳本常數裡；照 Q8 只動巡邏、不減人，例如巡邏兩名改 `sect_acolyte_terrace` 的 HP −10%、−20%），不在對話裡反覆手動試數值。
3. **（超標時）調 `terrace_patrol`**：採「全部格 ≤ 40% 的候選中改動最小的」寫進內容；沒有候選全過就**不改內容**，把表交 PM。改了內容要：`trpg content check`、`export_client_fixtures.py`（`unitDolls.json` 多一筆）、`tests/content`、`tests/world`（`-n 8`，含 `test_three_way.py`）、`tests/api/test_client_fixtures.py`；固定種子測試若因巡邏變弱而軌跡改變，照 `docs/dev/上手-內容資料與模擬.md` 第四節第 3 點換種子、斷言不動，逐項寫進報告。

## 行為一致測試（必做；實際打 API 或跑世界規則，不只測資料）

**T1 重選規則表**（`tests/api/test_ob6_reselect.py`，打 `POST /api/world/characters/{id}/actions`；角色照 `tests/world/test_opening_choice.py::_played` 的做法真的打完前兩步再正式選定；種子與角色 ID 固定）。每一列同時斷言 **畫面資料 `opening.reselect` 的 `available`／`window_open`／`blocked_zh` 和送出的結果一致**（可以時送得過、不可以時被拒的句子＝`blocked_zh`）：

| 情況 | 期待 |
|---|---|
| 已正式選定、3 級、沒用過、在霧渡鎮 | 成功；武器、關鍵字、起始 2 招換成新的；第 1、2 步三選一拿到的招收回、重新出第 1 組；HP、法力回滿；`reselect_used` 變真；小牌消失（`window_open` 假） |
| 同上，在主城 | 成功（主城也能重選）；說話的人是守印人 |
| 同上，在野外 | 被拒＝地點句；`window_open` 仍真（小牌照顯示） |
| 第二次重選 | 被拒「免費重選只有一次，已經用過了」 |
| 升到 `before_level` 級 | 被拒「已到 4 級，免費重選已結束」；`before_level` 與實際被拒的等級相同（小牌寫的數字＝規則的數字） |
| 入門期（還沒正式選定） | 沒有 `reselect`；送了被拒 |
| 有沒處理的遭遇 | 被拒「還有沒處理的遭遇，不能重選」 |
| 換過主手、背包滿 | 被拒（換下來的主手放不下）；角色完全不變、`reselect_used` 仍假 |
| 已完成開局的舊角色 | 沒有 `opening`；送了被拒（開局已經結束那句） |

**重選後什麼變、什麼不變**（同檔另一個表格測試，同一個角色重選前後逐欄比）：變＝主手武器、`opening.weapon`／`keywords`、起始 2 招、三選一給的招（收回）、屬性配點（照新武器推薦重配）、HP／法力（回滿）、`reselect_used`；不變＝等級、經驗、靈感、金幣、所在地點、玩家自己換上的裝備（在背包）、其他來源學到的招、任務進度。**確認彈窗列的 `returned_zh` 必須等於實際被收回的招名**，`weapon_returned` 必須等於起始武器本體是否真的被拿走。

**T2 雇用句**：入門期送雇用、改影子打法，被拒句＝`HIRE_PANEL_ZH`＝`limits["hire"]`＝隊伍面板 `hire_problem_zh`（三者相同）。

**T3 卡片寫的「不能」**：入門武器卡上寫到的每一個「不能」（Q4 預設：賣、寄、分解），都要有實際送動作被拒的測試；寫不出被拒路徑的（例：入門期主手不是物品，根本送不出）就不能寫在卡上，回報 PM。

**T4（OB-6b）**：模擬沒有測試檔；用冒煙那一次確認同一個種子跑兩次輸出逐字相同（寫進報告）。

## 驗收條件

**OB-6a**
- `ruff check .`、`ruff format --check .`、`uv run mypy`、`lint-imports` 結束碼 0。
- `pytest tests/world tests/api tests/content tests/narrative tests/test_architecture.py -n 8` 結束碼 0（分批跑，一次不要塞八個目錄）；T1～T3 都在裡面。
- `corepack pnpm -C client typecheck`、`corepack pnpm -C client test`、`corepack pnpm -C client build` 三個結束碼分開記，都是 0。
- `tests/api/test_openapi_snapshot.py` 過（型別已重產）。
- `WORLD_RULES_VERSION` 仍是 25、`CHAR_FORMAT` 仍是 `trpg-char/13`（`test_versions` 字面值沒動）。
- 浮動卡與彈窗（重選確認彈窗、小牌的說明卡）在 **1600×900 與 800×600** 實測「從觸發元素滑進卡片 → 卡內捲到底 → 釘住 → 關閉」，結果寫進報告。
- `window.__layoutSmoke.runCase` 在 **1600×900、1040×624、800×600** 三個情況全 PASS（步驟照 `docs/開發PM交接.md` 6.2 第 5 點：先 `localStorage.clear()`、網址 `/?dev=1&anim=0.1&mute=1`）。
- **截圖** `docs/art/shots/ob6/`：≤ 10 張、jpg 品質 80、單張 ≤ 300 KB（多格用合圖）；每張自己打開看過。至少涵蓋：重選頁（霧渡鎮、葛蘭台詞與頭像）、重選頁（主城、守印人）、確認彈窗 1600 與 800 各一、重選完成彈窗、任務欄小牌（含說明卡）、入門武器卡片、三選一開在最上面＋鐵匠預設防具（可合圖）、守印人金框＋葛蘭頭像 3 倍（可合圖）；巡檢四類各至少一格（可合圖）。實機到不了的用開發頁畫並在報告「實機未看」逐項列出。
- 新增或改的字逐字對照定稿（表在報告）；沒定稿的都在 `暫定字串-OB6.md`。
- 前端靶場四個檔仍沒有技能 ID、沒有寫死「主城」（`range.test.ts`）。

**OB-6b**
- 腳本受 `scripts/ruff.toml` 檢查：`ruff check scripts/ob6_newbie_sim.py`、`ruff format --check` 0。
- 報告有兩張摘要表、樣本數、種子範圍、每格人數、執行時間與 `--jobs`；梯田每格分母 ≥ 80（走不到第 3 步的人另列，不算在分母）。
- 超標時：候選對照表（同種子配對；每格現況 → 候選、淨變動、勝負翻轉人數）、採用的建議值與理由；改了內容就附 `trpg content check`、相關 pytest 的結束碼，與換過的固定種子清單。
- 沒超標時：明寫「不調 `terrace_patrol`」，內容零改動（`git diff --stat content/` 為空）。

## 報告格式

`docs/phases/PhaseOB-6a報告.md`、`docs/phases/PhaseOB-6b報告.md` 各一份，各含：

1. 交付項目與 commit 對照表。
2. 逐條驗收（指令與結束碼、測試名稱）；6a 附截圖檔名對照表與完整路徑 `docs/art/shots/ob6/<檔名>`。
3. 改到的既有測試斷言（檔案、改了什麼、為什麼不是放寬規則）。
4. 6a：地名牌盤點表、暫定字串的位置；6b：兩張摘要表與候選對照表。
5. 「待開發 PM 確認」Q1～Q10 實際照哪個做。
6. 實機未看、沒驗證。
7. **待 PM 決定**（最多 10 點）。
8. **改到的區域順手更新對應上手筆記**：6a 更新 `docs/dev/上手-roguelite開局與入門期.md`（重選畫面、小牌、新欄位）與 `docs/dev/上手-前端戰鬥畫面與動畫.md`（若動到共用元件）；6b 更新 `docs/dev/上手-內容資料與模擬.md`（新腳本、量測做法）。報告裡寫明更新了哪幾節。
9. 給使用者重開伺服器檢查的重點（內容檔有變時）。
