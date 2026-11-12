# 開發 PM 交接歷史（歸檔）

> 開發 PM 交接文件的歷任進度小節，2026-10-22～10-31；現況以 `docs/開發PM交接.md` 為準。
> 各節保留原標題與日期，由新到舊排（DOC-B M1 自 `docs/開發PM交接.md` 第 3 節搬出，原文未改；文中「本檔 3.3」「本檔 6.1」等指的是當時的交接文件節號）。

---

> 2026-11-12 整理：下面 3.000～3.3 自 `docs/開發PM交接.md` 逐字搬入（原文未改）；更早的 10-22～10-31 各節接在這批之後。

### 3.000 交接（2026-11-12，第五組開發 PM 換手；流水細節，3.0000 優先）

> 換手原因：省額度做法第 3 條（PM 對話約 40 萬 token 就交接）。下面是現況與待排；各項的細節、原話與 commit 在 3.00 第 5 點的各條（那一節是這兩天的流水，查細節用）。
> PM id（第五組）：專案 PM `local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa`、玩法 PM `local_da4b4c03-a86c-4afe-b898-68314e032524`、**美術 PM（第六任）`local_b4c63feb-4b58-4944-a343-0597bae0d5b6`**（分支 `claude/vibrant-vaughan-91f07e`，worktree `.claude/worktrees/art-pm-5ea9fb`；它的 worktree 常有畫圖 agent 在工作，**併它的東西用 commit hash，不要動那個 worktree**）。舊 id 都不要再傳。
> 共用筆記資料夾：`C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_c2d54362-e4f7-4f75-b1dd-07933f64c2aa\`（核對、調查、量測、`台詞-OB5與PR2定稿.md`、`暫定字串-OB5.md`）；第四組留下的 `...\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\`（`盤點-150與147.md`、`台詞-150與147.md`）。

**1. 這兩天上 main 的段**（報告都在 `docs/phases/Phase<段>報告.md`）：PR-1b（#147 測試模式引擎修正）、CB-2d、CB-2e（#149 頭目招式與施放率；模擬腳本 `scripts/cb2e_sim.py`）、OB-2、OB-3、OB-4＋4b（#150 後端全部）、CB-3＋CB-3b（#149 異形第二種近戰動畫、戰場畫布留邊上 26／右 12、實機巡檢）、OB-5＋5b（#150 前端：選大類、葛蘭正式選定整頁、入門期提示）、`test_dev_boss_rehearses_to_the_boss_charge` 修穩（固定世界種子與角色 ID）。版號：`WORLD_RULES_VERSION` **25**（OB-3＋OB-4），`CHAR_FORMAT` `trpg-char/13`、`LOG_FORMAT` 沒動。**main 的確切位置與最後一次全量結果見本節末「換手時的狀態」。**

**2. 使用者的工作規則（都要照做，原話在專案 PM 交接與共用備忘）**：
- 所有 agent 與子 agent 一律 Fable 5.2（`model: "fable"`），派工 prompt 要寫明往下傳。
- **push 前 pytest、vitest、build 每個結束碼都是 0 才推；「已知不穩定、單獨重跑確認」不算例外**，非 0 就回報專案 PM 由使用者決定（2026-11-11 我違反過一次）。`check.py --full` 不含 `vite build`，要另外跑。自上次全綠以來只有 `docs/` 變動時可以直接推。
- 省額度八項（2026-11-12「4個都改」「都做」）：不回報「還在跑」；名額固定開發 3、美術 1（美術常來借 1 個做唯讀審查，有空就借、不用回）；PM 約 40 萬 token 換手；審圖只看有改的；同一塊的後續交回原 agent（上限 2～3 段或約 30 萬 token）；每區域一份上手筆記；派工 prompt 寫明要讀的檔與段落；只有動同一批檔案的小修才併段。**實作一律派 agent，PM 不自己寫。**
- 已寫入設計文件的決定只有使用者能改；放寬既有規則或驗證一律先回報。全量期間不跑模擬。
- **（2026-11-12 專案 PM）每段合併前，與該段改動相關的 slow 測試要一併跑**（例：動到技能 schema／內容就跑 `tests/skillgen/` 含 slow、改 AI 估值就跑 `tests/cli/test_output_snapshots.py -m slow`），不能等全量才發現；派工 prompt 寫明。**雜湊／快照不能整批重產**：每一項先證明變動來自預期改動（拿掉該改動後回到舊值），對不上的不准更新、先回報。起因：IP-1＋BAL-20 合併後全量 93 項失敗（FIX-1）。

**3. 新開發 PM 的第一批（依序；前三項可平行，檔案不重疊）**：
1. **上手筆記四份**（使用者「都做」的 B 項）：派一個 agent 寫 `docs/dev/上手-<區域>.md`，每份 150～300 行：這一塊在哪些檔、資料怎麼流、必守的規矩與常踩的坑、相關測試檔、要跑的最小檢查。四份：引擎戰鬥結算；roguelite／世界開局與入門期（#150）；前端戰鬥畫面與動畫；內容資料與模擬。之後每段的交件條件加「改到的區域順手更新上手筆記」，派工 prompt 第一行指定讀哪一份。
2. **PR-2**（#147 接線：工坊師傅選單「靶場試玩」、測試模式戰鬥版面、出發後回靶場、葛蘭畫面也能試打）：規格還沒寫。依據 `docs/art/OB與PR移植需求.md` 第 2 節 PR-2、第 3 節、第 4 節驗收 7～11 項；`docs/design/21` 21.5 工坊靶場與測試模式；`docs/phases/PhasePR-1報告.md`、`PhasePR-1b報告.md`；文字照 `台詞-OB5與PR2定稿.md`（「補定」優先）。要寫進規格的：地名讀內容檔的主城地名；守印人「出發後回靶場」那句不用、改工坊師傅的一句；測試模式提示句「敵人」換「木樁」（實戰不變）；「新」小牌在該角色第一次點開「靶場試玩」後消失（記旗標，優先用 `hints_seen`）；手機寬戰鬥版面不做；回合操作靠底／靠上要改先問美術 PM。
3. **OB-6**（重選確認彈窗、任務欄「4 級前可重選一次」小牌、入門武器背包卡片文字、重選相關字串與台詞檔沒用到的 4 句、入門配備打第 1、2 步的小模擬**含雨中梯田每格至少 80 人**，超標先調 `terrace_patrol`）：規格還沒寫；樣張沒另畫，照 `DialogFrame` 與既有樣式，交件時美術檢查。**併進 OB-6 或 PR-2 的 OB-5 遺留**：玩法 PM 對 OB-5b 四點（靶場以外寫死「主城」的地方與區域名／地名怎麼分、隊伍面板句與雇用被拒句、「重新顯示提示」會再自動開一次、兩處變短的字）與成長面板「改外觀（主城隨時免費）」——**玩法 PM 尚未回覆，回了照做**；美術追蹤：三選一面板開啟時要停在最上面、鐵匠面板入門期部位下拉預設防具、選大類頁守印人金框與葛蘭頭像 3 倍特寫補拍；仍沒實機看的（點葛蘭本人／主城靶場物件重開選定、略過配點後的再提示、768／1024 與觸控）。
4. **戰鬥動畫小修段**（美術 PM 裁定，優先度高的是 a）：(a) 修「目標在正南／正北時特效落在側邊」的落點（含左緣），修好邊欄裁切一起消失；(b) 第二種近戰片段的挑法改成看技能本身的射程（玩法 PM：射程 1 或跟近戰武器射程才算近戰；射程大於 1 的法術貼身放播施法片段），附一張碎晶之主貼身放法術的連拍給美術；(c) 「同一單位連續出手的銜接」先查原樣內容有沒有同一隻同回合同一招放兩次，有再排。
5. **只讀調查：餘燼啃咬**（玩法 PM）：帶 `skill_ember_bite` 的 5 種單位（餘燼蜥、殼縫餘燼蜥、熔爐母獸、熔晶魅、幼蜥）的每回合施放率與不放的原因，提做法給玩法 PM 審（小怪也適用 < 10% 要處理）。做法照 CB-2e 前的幾次調查（共用筆記 `調查-*.md`、`scripts/cb2e_sim.py`）。

**4. 之後的待排**：Q 版小圖示移植 5 段（等美術每批的移植需求：①武器副手＋②防具飾品；③技能主圖＋④徽章部件，含後端 `narrative/skill_icon.py`＋API 帶武器條件；⑤狀態；⑦HUD＋⑧事件卡；⑥物品最後）；錐形震波畫面（等美術樣張）；**QI-2 前端段順手做**（美術 PM 2026-11-12，QI-1b 驗收）：身上裝備格圖示置中後左上角要對齊裝置像素（`Math.round(x * dpr) / dpr`），`icons()` 加位置檢查；**PR-2 結案前必做**（美術 PM 2026-11-12，PR-2c 驗收 `docs/art/PR-2檢查.md`）：靶場藍格貼水池時內縮、不壓石條（高亮層，PR-2b 之後排一小段 PR-2d）；HUD 木樁小頭像改新外觀（已追加給 PR-2b）；木樁可能退出滑軌記追蹤；**下一個 CB 段**（美術 PM 2026-11-12，CB-3c 驗收）：頭目（灰燼之心、碎晶之主）打正南／正北時特效仍落側邊，與「斜向特效不在目標格內」一起看；連續出手銜接不排；1 階技能平衡（遠程優先）；平衡段（碎晶之主 P3 瞬步與 trapper、灰燼之心 `lava_spout` 8% 與法力見底——要先做引擎能力「延遲招可落在選定格」、霧鎖真人 95%、雨中梯田 42%；**另加 2026-11-12 玩法 PM：「雨中梯田固定戰平均 2～2.5 輪，新流程下偏輕」，平衡段再看**（OB-6b 報告；盜賊 HP −10% 維持））；整理待辦（舊的「一次選定」後端路徑、`tests/skillgen/test_player_text.py` 那個單獨要約 295 秒的測試標 slow 或拆小、3.00 第 4 點的小項）；Mac 上刪測試角色「測試」。使用者可能要實機看一次異形動畫的節奏（美術 PM 請專案 PM 問），要看的話開發入口與換陣容的做法在 `docs/phases/PhaseCB-3b報告.md`。

**5. 環境**：見 3.00 第 6 點與 3.0 第 5 點（Windows、`uv run python`、worktree 從 `origin/main` 分出所以派工前先 push 規格、完成的 agent worktree 被鎖住不要硬拆）。agent 的預覽埠請分段指定（這兩天用過 5187～5223、8097～8110），結束時用 PID 關。**5195 埠有一個來源未確認的 vite（PID 9592，可能是 OB-5 agent 留下的），我沒有關，已告知使用者。**

**換手時的狀態（2026-11-12）**：OB-5＋5b、CB-3b 與美術檢查紀錄合併後（合併 commit `30326987`）跑 `check.py --full` 與 `npx vite build`，**全部結束碼 0：pytest 15827 passed（15 skipped、4 xfailed）、vitest 3460、ruff／format／mypy／lint-imports、build**；之後只加了本交接，已 push，main＝origin/main（以 `git log -1` 為準）。沒有執行中的開發 agent；工作樹只有一個未追蹤的 `tmp_x`（不是開發 PM 建的，沒動）。

### 3.00 交接（2026-11-11，對話中斷後換新 session；流水細節，3.000 優先）

> 使用者：「你們被中斷了 因為某些原因 然後我想要換session 請交接」。前一個 session 結束時，下面三段的 agent 都**沒有交件**，且已不在執行（換 session 後沒有完成通知）。PM id 換新後以專案 PM 的開場訊息為準。專案 PM 交接在 main `4e712b6c`。

1. **main**：`4e712b6c` 已 push。最後一次全量是 CB-1 合併後（pytest 15580、vitest 3386）；之後的 PR-1、OB-1 只跑了快速檢查，**接手後第一次合併要跑 `check.py --full`**。
2. **三段未完成的分支**（worktree 在 `.claude/worktrees/agent-<id>/`，被執行環境鎖住，不要 `-f -f` 硬拆）：

   | 段 | 分支 | 狀態 | 接手建議 |
   |---|---|---|---|
   | **CB-2d**（#149 收尾，規格 `PhaseCB-2d計畫.md`） | `worktree-agent-a3e10e808e675a882`，HEAD `03ab3c13` | 已 commit：換招（`shock_follow` → `skill_spark_chain`、`whirlwind` → `execute`）、`aim_hit_permille` 700、`magma_slug` 智力 8、種子與快照、**已 revert 減 1 人（`dd96a754`）並改梯田盜賊 HP −10%（`44f5575f`）**、已 merge main。**沒做**：revert 後的種子／快照重確認與測試重跑、trapper 補到 30 場、更新報告（`PhaseCB-2d報告.md` 還是減 1 人的舊結論，要改成 HP −10% 與倒下率，並註明 CB-2a 第 1 階段輪數更正：只算本體約第 5.4 輪、32 場 29 場進入） | 派收尾 agent 在這個分支做完上述三件，再合併、跑全量 |
   | **OB-2**（#150 三選一延後、正式選定、推薦、入門期不存影子，規格 `PhaseOB-2計畫.md`） | `worktree-agent-abbd5c1b1f5e033c9`，HEAD `29252e19` | **沒有任何 commit 或改動**，等於沒開始 | 依規格重派（基準用最新 main） |
   | **PR-1b**（#147 灌注／指揮算放招、主角進致命地形回位、裝備充能補滿，規格 `PhasePR-1b計畫.md`） | `worktree-agent-a131ac84f73fb7f0e`，HEAD `29252e19` | **沒有 commit，但有未 commit 的改動**：`engine/battle.py`、`practice.py`、`state.py`、`triggers.py`、`turns.py`、`tests/engine/test_practice_mode.py`（+271／−13），沒驗證過 | 派收尾 agent 在這個 worktree 檢查、補齊、commit、跑驗收（含「實戰不變」逐筆比對）；不確定就重派 |

3. **待排順序**：CB-2d 收尾 → OB-2、PR-1b → OB-3（重選、閃現 4 級限制、配點教學）、OB-4（戰鬥閘，可與 OB-2 平行）→ OB-5（前端；**順手**：鳥走路接攻擊略過落地／起飛、異形向正南／正北施放不翻面（人形不動），補拍 `1b`、`1c` 與鳥的連拍，見 `docs/art/CB-2b檢查.md`）→ OB-6（正式選定與重選畫面、台詞入檔、入門配備打第 1、2 步的小模擬，**含雨中梯田與竹林小徑重量**，超標先調 `terrace_patrol`）→ PR-2（#147 接線、出發後回靶場：工坊師傅加一項＋葛蘭畫面也能試打）→ 1 階技能平衡（遠程優先）。拆段與檔案清單：共用筆記 `盤點-150與147.md`（專案 PM 給的共用筆記資料夾）。
4. **小項**（不單獨開段，碰到時順手）：`badgeCapsule.test.ts` 拆檔（vitest wall 下限）；`damage_object` 是第 4 份傷害算式；預覽與結算的最低傷害來源分歧風險；建角與 roguelite 開局沒選出身時開始鈕只變灰、沒提示缺什麼；`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` 用隨機種子、基準就會機率性失敗（改固定種子）；`scripts/cb2a_sim.py` 把源晶柱 `surge` 算進第 1 階段；`environment.py` 的 `aim_hit_permille` schema 預設仍是 500。
5. **等別人**：
   - **2026-11-11 使用者四項決定**（專案 PM 轉達，累積到下一段順手處理）：① #148 示範招「按玩法pm決定」→ 玩法 PM 建議 B（換成不綁武器的招：近戰瞬步背刺＋先發制人、遠程淬毒箭＋燧石飛刃、法器不變）；玩法 PM 會來核對這 4 招是否真的不綁武器、不低於普攻，定案後排進 #150 入門招，**定案前入門招照舊從資料讀，不要寫死**。② 墨線小圖示改 Q 版「好」→ 等美術 PM 樣張過審再排段；美術開畫圖 agent 前會先對名額（合計最多 4 個）。③ 蓄力強招在隱蔽單位的預告「按玩法pm決定」→ 維持不遮，不用改。④ Mac 本機測試角色「測試」：「刪」→ **已決定刪除，下次在 Mac 上工作時執行**（只刪這一個角色；Windows 的 `saves/` 查過沒有這個角色）。
   - **美術 PM**：5 款異形第二種近戰片段在畫（之後一個審查 agent）；#150／#147 的 3 項樣張（選大類、出發後入口、測試模式版面）排在後面。
   - **#148 示範招定案（玩法 PM 2026-11-11，`docs/design/21` 21.5、決定紀錄 #148，main `4ec2ab3b`；使用者原話「按玩法pm決定」）— 待排，OB-2 合併後併進下一個 #150 段**：近戰 `skill_shadow_backstab`＋`skill_wild_blade`；遠程 `skill_rng_venom_arrow`＋`skill_oil_spark_throw`；法器不變。改 `content/world/newcomer.yaml` 的 demos 與註解、`tests/world/test_opening.py` 的 `DEMOS_148`；燧石飛刃示範卡片說明加「靶場的油桶打破會流出油」；加測試：示範招不得有 `weapon_only` 或綁武器、副手的條件。核對數字在共用筆記 `核對-148示範招B案.md`。PR-1b 報告第 5 節的 5 點，玩法 PM 同意照最保守做法。
   - **CB-2d、OB-2 審核結論（玩法 PM 2026-11-11，`docs/design/21` 21.5 第 9 點「OB-2 補充」、決定紀錄 #149、#150 審核條，main `5df89c26`）— 待排**：
     - OB-2 後續（併進下一個 #150 段）：① 兩組延後三選一不能讓玩家拿到同一招（第 1 組選走的招若也在第 2 組就換掉那張，或改成選完第 1 組才出第 2 組，做法開發 PM 選，補測試）；② 背包滿拒絕選定時要提示原因；③ 關鍵字推薦找不到第 2 個就只標 1 個；OB-5 加「帶武器」的推薦查詢端點（照玩家當下選的武器算）；④ #148 換招後回報玩法 PM 三大類各推薦得出哪些關鍵字。「打完前 2 步才可選」確認；入門招靠 `range.demos` 辨識接受。
     - **進度（2026-11-11 晚）**：PR-1b、CB-2d、OB-2 已 push（`729c47a0`）；OB-4、OB-4b、OB-3 已合併進本機 main（`beb5b7d0` 起，`WORLD_RULES_VERSION` 25＝OB-3＋OB-4），下面「OB-2 後續」「OB-4 後續」①② 與 #148 換示範招都已做完。玩法 PM 對 OB-3 報告第 7 節六點全部照實作確認（21.5「OB-3 補充」，main `fcd48458`）。**OB-5／6 開工時把暫定字串列一張清單放共用筆記給玩法 PM 定稿**（閃現被擋、重選各訊息、配點再提示、升級畫面與 `allocate_done_zh` 順序對不上的舊台詞、OB-4 的各種被擋原因）；開局結束不用事件與台詞。小項：`tests/skillgen/test_player_text.py::test_player_check_texts_have_no_english_identifiers` 單獨要約 295 秒，機器忙時會超過 300 秒逾時讓 xdist worker 掛掉，要標 slow 或拆小。
     - OB-4 後續（**OB-4b，①② 已做完；③④ 待排**，玩法 PM 2026-11-11，21.5 第 9 點「OB-4 補充」，main `94ad14e1`；OB-4 報告第 6 節其餘各點照做）：① 補內容檢查或測試：會給招的任務步驟，完成條件必須在正式選定後還能達成，不能只靠入門期當下發生一次的事件（現有任務要全過；「查出私通盜賊的人」有線頭條件算過）；② 入門期紮營不能因為被隱藏的敵人被擋——先查現況，會擋就改成入門期不看被隱藏的敵人，並回玩法 PM 一句現況；③ `STARTER_STEPS` 兩份收成一份（`opening_choice` 從 `opening_limits` 匯入）；④ 聯賽、Boss、傭兵、誓約、換技能的面板資料在入門期標不可用（目前只有送出動作才回原因），可併 OB-5。
     - CB 後續（**CB-2e，待排**，不急）：霧鎖真人第 3 階段 `execute` 換成 **A 收霧斬 `skill_mist_rend`**（玩法 PM 2026-11-11 定案，決定紀錄 #149，main `29495847`；放血斬的敵人版，1 AP 近戰 700‰＋流血 2 回合、冷卻 2；草稿與 diff 在共用筆記 `候選-霧鎖真人換execute.md` 指到的 scratchpad，換 session 後可能不在，照筆記重寫即可）。實作要補圖示 fixture、預算校準、`tests/skillgen`／`narrative`／`roguelite` 名單。**標準改成：進到該階段後，頭目每個行動回合的施放率 ≥ 20%**（施放次數 ÷ 頭目在該階段的行動回合數），不看每場次數；歸一門檻不動，第 3 階段太短併進「霧鎖真人 91%、目標 70%」平衡待辦。`spark_chain` 算符合，不換。
       - **標準三級（玩法 PM，決定紀錄 #149，main `5b1972d3`）**：每回合施放率 ≥ 20% 達標；10～20% 可接受、不動；< 10% 要處理。量測結果在共用筆記 `量測-頭目每回合施放率.md`。
       - **CB-2e 前要先做的只讀調查（待派，有名額就派）**：① `mist_shift` 第 2 階段 2%：先試在 `content/ai_profiles.yaml` 的 `ally_status_values` 補上 `concealed` 的分數；過關條件是第 2 階段 ≥ 20%，且雲嶺一般、懸賞精英與其他會隱蔽的敵人勝率變動不超過 3 個百分點（附前後對照）；不過就用 C2 `skill_mist_step_slash`（不選 C1、N1）。② 碎晶之主 P1 `cluster_bolt` 7%、P3 `skill_blink` 0%：查原因、提做法給玩法 PM 審（`skill_blink` 若是玩家招要說明要不要敵人版）。第 1 階段 `mist_shift` 18%、灰燼之心 3 筆、碎晶之主其餘 3 筆都可接受，不動。
     - 雨中梯田 42%（火焰）、41%（巨劍）：不放寬 ≤ 40%、現在不調；#150（含 #148 換招）做完再量，每格至少 80 人，仍超標先調 `terrace_patrol`。trapper 打碎晶之主 37%（11/30）不算通過，記平衡待辦，平衡段照 #87 調 Boss。
   - **OB-5 版面題已解鎖（2026-11-11，專案 PM 轉達，使用者原話「都照建議」）**：葛蘭「正式選定」做整頁；選大類時三張卡下方一列展開整個武器架；守印人、葛蘭台詞旁放 Q 版頭像；測試模式手機寬戰鬥版面這次不做，照桌機寬移植。**等美術 PM 第 3 版樣張過審後的移植需求再開工。** Q 版小圖示：方向通過，六類加防具飾品全量重畫（約 370 個，美術建議切 7 批）；樣張與盤點 `docs/art/Q版小圖示樣張.md`（美術切 8 批：①武器副手 ②防具飾品 ③技能主圖 ④徽章部件 ⑤狀態 ⑥物品 ⑦HUD ⑧事件卡）。**開發 PM 已回美術 PM（2026-11-11）**：移植累積成 5 段——(①＋②)、(③＋④，含後端段：`narrative/skill_icon.py`＋API 多帶武器條件與 `weapon_req`，排在第③批樣張過審後、前端移植前，會重產 API schema、不和其他改 API 的段平行)、(⑤，含 `statusIcon.ts` 的 `glyphColor`)、(⑦＋⑧)、(⑥物品，最後做，連帶背包／商店／掉落／郵寄顯示)；每段等美術給移植需求與驗收截圖清單；OB-5／6、PR-2 優先，小圖示穿插。
   - **OB-5、CB-3b 已派（2026-11-11，規格 `PhaseOB-5計畫.md`、`PhaseCB-3b計畫.md`，main `31c981ae`）**；美術移植需求 `docs/art/OB與PR移植需求.md`。**PR-2 規格要寫進去的（玩法 PM 定稿 `台詞-OB5與PR2定稿.md`，「補定」一節優先）**：地名讀內容檔的主城地名（目前「樞島」）不寫死；守印人「出發後回靶場」那句不用、改工坊師傅的一句；測試模式提示句把「敵人」換成「木樁」（實戰不變）；「新」小牌在該角色第一次點開「靶場試玩」後消失（要記一個旗標，可能動 `CHAR_FORMAT` 或用 `hints_seen`）；移植需求第 4 節 PR-2 的 5 項驗收；回合操作靠底／靠上若要改先問美術 PM。
   - **OB-5 已交件、未合併（2026-11-12）**：本機分支 `worktree-agent-ab36437058248df22`（`e35f2063`），報告 `docs/phases/PhaseOB-5報告.md`（在該分支），截圖 `docs/art/shots/ob5/`；美術 PM（第六任）審查中。**OB-5b 要改的（玩法 PM 2026-11-12，21.5 第 9 點「OB-5 補充」；等美術審查結論一起派，原 agent 已用約 62 萬 token，要開新的）**：① 字串照 `台詞-OB5與PR2定稿.md`「OB-5 暫定字串定稿」一節改 10 列，沒列到的照現在的字；寫死「主城」的改讀主城地名；招的代價讀資料。② 正式選定畫面只在第一次回到霧渡鎮或主城時自動開一次，按「之後再選」後不再自動開（靠頂列的鈕或點葛蘭；點葛蘭直接開選定畫面可以）。③ 主城靶場選完補守印人一句並出彈窗：「挑好了。借你的那套我收走，渡口和竹林欠你的，現在一起補上。」其餘各點照現在的做法。重選那幾句與台詞檔沒用到的 4 句留 OB-6。**整理待辦**：舊的「一次選定」後端路徑（新前端已不送）之後清理時拿掉。
   - **CB-3b 已交件、未合併（2026-11-12）**：本機分支 `worktree-agent-ac1524f5a484eeb22`（`9893b01c`），報告 `docs/phases/PhaseCB-3b報告.md`。美術 PM 驗收（美術分支 `docs/art/CB-3檢查.md` 末段，`ea4da384`）：留邊與補拍通過；**必補 M1 收霧斬開發頁連拍（已派，補完給美術檔名即結案、可合併）**。上緣 26、右緣 12 定案；`devTrace` 保留；`cb3b/` 截圖留到結案。**美術裁定的後續追蹤（待排）**：① **修「目標在正南／正北時特效落在側邊」的落點（含左緣；優先度高）**，修好後邊欄裁切一起消失；② 「同一單位連續出手的銜接」（結尾少兩格、同一招連放兩次格號交錯約 250 ms、鳥第二次攻擊先落地再起飛）：先查原樣內容有沒有同一隻同回合同一招放兩次，有再排；③ 錐形震波的畫面（現在和火花連鎖一樣）等美術出樣張（排在小圖示之後）；④ **玩法 PM 2026-11-12 定（併下一個 CB 或平衡段）**：(a) 第二種近戰片段的挑法改判斷——「近戰技能」看技能本身，不看施放當下的距離：技能射程是 1 或跟近戰武器射程的才算；射程大於 1 的法術貼身放仍是法術，不播第二種近戰片段（CB-3 目前判定是「非普攻＋形狀 single＋距離 1」，要改；碎晶之主貼身放晶蝕、火花連鎖播近戰揮擊就是這個）。(b) 餘燼蜥 3 場 38 次普攻、0 次餘燼啃咬：小怪也適用每回合施放率標準（< 10% 要處理，#149 小怪 2 招）。只讀調查：查原因（AI 評分或代價），量帶 `skill_ember_bite` 的 5 種單位（餘燼蜥、殼縫餘燼蜥、熔爐母獸、熔晶魅、幼蜥）的施放率，提做法給玩法 PM 審；⑤ 使用者可能要實機看一次節奏，屆時給開發入口與陣容（做法在 CB-3b 報告）；⑥ 下次巡檢截圖取景置中、挑沒飄字的回合、標題用中文。
   - **push 規則（2026-11-11 專案 PM 重申使用者要求）**：全量任一項非 0 不 push，「已知不穩定、單獨重跑確認」不算例外；非 0 時回報專案 PM 由使用者決定。`test_dev_boss_rehearses_to_the_boss_charge` 修穩後回專案 PM 根因與 commit。
   - **CB-3（#149 異形第二種近戰片段）已合併**（美術 PM 2026-11-11 通過，`docs/art/CB-3檢查.md`）。**下一個前端段要帶的**：① 補件：鳥「移動接攻擊」連拍重拍（現在那張鳥全程在同一格，要拍到走兩格）；一般外觀蜥蜴站最上排的 333 ms 一張。② 戰場畫布上緣留約半格、右緣約四分之一格（大型蜥蜴 `atk:tailover` 在最上排／最右欄被裁；不縮小動作）。③ **實機巡檢**追蹤：四款第二種片段（實機只看過熊）、山豹斑點、鳥連接、正常速度節奏（含蜥蜴 667 那格是否只是截圖時機），巡檢時記錄每次重畫的格號。截圖 `docs/art/shots/cb3/` 先全留，結案時整批刪。
   - **CB-2e 已合併**（main `9488eef7`，報告 `docs/phases/PhaseCB-2e報告.md`，模擬腳本 `scripts/cb2e_sim.py`；`concealed: 2` 採用）。**待排（優先度低，併下一個平衡段或 CB 段，玩法 PM 2026-11-11）**：灰燼之心 P1 `lava_spout` 8%（51/603）：調查完（共用筆記 `調查-灰燼之心lava_spout.md`），玩法 PM 選 **B 新寫熔岩濺落 `skill_lava_splash`，但必須做成帶提前一輪預告的延遲招**（19.2.3 已寫入）；過關條件：P1 施放率 ≥ 10%（20% 更好）、整體勝率 70～80%、各 build 30 場 fire ≥ 40%，都過就採用並走預算校準、補熔岩柱 `spout` 的動畫對應；有一項不過或延遲版 AI 不放、或要改引擎才做得出來，回玩法 PM。**結論（2026-11-11）：純內容做不出帶預告的遠處延遲招**（延遲招落點寫死在施放者腳下；延遲陷阱玩家看不到；固定區域在玩家回合開始就結算），玩法 PM 定案**延後**：`lava_spout` 8% 記平衡待辦，平衡段把引擎能力「延遲招可落在選定格」（估計動 `content/skills/specs.py` `FollowupSpec`、`engine/state.py` `StatusInstance.target_pos`、`engine/delayed.py`、`engine/ai/composite.py`、合法動作列舉與 `preview.py`，`LOG_FORMAT` 升版）和灰燼之心法力見底、碎晶之主瞬步一起做，做完再照三個條件量；在那之前不上不帶預告的 B，也不走「陷阱對敵方公開」。`ashen_oath` 10% 可接受、不動。平衡待辦加一條：灰燼之心法力 67 不回復、第 6～8 輪見底（P2、P3 的招 15～17% 主要因此）。收霧斬、震波的動畫沒實機看過，併進實機巡檢。
   - **CB-2e 規格**（`docs/phases/PhaseCB-2e計畫.md`；玩法 PM 2026-11-11 裁定，決定紀錄 #149，main `c2af7393`）：收霧斬換 `execute`、AI 增益表 `concealed: 2`（合併前補量叛徒戰、夜間霧魅增援、帶 `skill_blink` 的我方 build，變動超過 3 個百分點就不合、回玩法 PM）、碎晶之主 P1 聚雷換 `skill_thunder_clap`；P3 瞬步招不加。
   - **平衡待辦（玩法 PM 記的，現在不調）**：碎晶之主 P3 `skill_blink` 0%，19.7「每回合換邊」未達成，和 trapper 一起調（到時優先 `skill_rift_flicker`，草稿見共用筆記 `調查-AI隱蔽分數與碎晶之主兩招.md`）；碎晶之主換震波後整體勝率約 74%，略高於 19.4 的 60～70%；霧鎖真人補隱蔽分數後 91% → 95%、第 3 階段太短；雙匕首上 2 AP 單擊招只有普攻的 0.5～0.7；瞬步背刺在普通木樁第二次起背後格被石柱占住只剩約 0.48；1 階遠程武器技沒有一招無條件 ≥ 普攻（玩法 PM 接受，不為此調）；`ruined_fort` 25%、霧鎖真人 91～95%（目標 70%）、門檻 8 後「瞄準」價值下降、雨中梯田暫時接受最差約 48%、trapper 打碎晶之主若 < 40%。
6. **Windows 注意**：GitHub 帳號已是 huntertoby，可以 push（不要動憑證設定）。建置在 `client` 內 `npx vite build`；`corepack pnpm -C client typecheck`；worktree 內 `uv sync --frozen --offline`、`corepack pnpm -C client install --frozen-lockfile --offline`；**不下載 pnpm 10（使用者沒同意）**。預覽埠不要用 8000（使用者）、8001（本機 LLM），也避開 8092。Agent 的 worktree 從 `origin/main` 分出，**派工前先 push 規格**。派工 prompt 加「涉及放寬既有規則或驗證的一律先回報」（CB-2d 曾自行放寬陣容下限）。改到技能池或內容的段，驗收要列 `tests/skillgen`、`tests/narrative`、`tests/roguelite`（CB-2a 曾漏）。

### 3.0 現況（2026-11-10，Windows；優先於 3.1）

> 第四組 PM（Windows）：專案 PM `local_1dc515fa-6fa4-4841-956e-bdff26ae2844`、玩法 PM `local_0a6fbf09-b1f7-4040-b5b4-98537b4efa82`、美術 PM `local_88eb1048-c8a4-4601-b42a-2b2e2664de37`。

1. **恢復順序（使用者「go」）**：① mypy＋測試省時 ✅ ② 傷害公式合一、`unit_downed` 鎖定 ✅ ③ HID-1b（規格 `PhaseHID-1b計畫.md`）④ #146、#148、#149（模擬排在 #149 之後一起跑；開段前請玩法 PM 附使用者原話確認 `hit_target` 的適用範圍；#149 加招前問美術 PM 動畫）⑤ #150（以 `docs/design/21` 21.5 為準，台詞由玩法 PM 補；#148 要先做）、再 #147 ⑥ 1 階技能平衡。`docs/部署說明.md` Windows 段穿插，**不下載 pnpm 10（使用者沒同意）**。其餘待排見 3.1 第 3 點。
2. **批次 1（PERF-4、PERF-4b、ENG-1）合併後全量**：pytest 15421 passed、501 秒（參考值 668 秒，負載不同）；vitest 3315 passed，平均約 50.6 秒（同條件改前 62.2 秒，約快 19%，盤點的 27～32 秒沒有重現）；mypy 0 錯誤。
3. **盤點結論與待決**：共用筆記 `盤點-總結與排序.md`。使用者預設：R7 等省時做完再看、R8／R9 不做、R10 Defender 不動。結構債 S4～S8 不單獨開段，改到時順手。
4. **累積的小項**：`badgeCapsule.test.ts` 拆檔（vitest 全量的 wall 下限）；`damage_object`（`effects/world.py`）是第 4 份傷害算式；預覽用 `core.min_damage_on_hit`、結算用 `effect.min_damage`，目前一致，若技能自訂 `min_damage` 會分歧；建角與 roguelite 開局沒選出身時按鈕只變灰，要提示缺什麼；`test_demo_balance` 的 xfail 全部 XPASS，是否移除待定；R3 快取上限 64、R5 `SCRYPT_N` 2**4 是初值。
   - **批次 2 完成（main 74225ed1）**：HID-1b、HID-1c（美術結案）、CB-1（#146、#148）、CB-2a（#149 補招與模擬，報告 `PhaseCB-2a報告.md`，待玩法 PM 審數值）、CB-2b、CB-2c（美術結案）。全量 pytest 15580、vitest 3386。
   - **下一個碰前端的段要順手做**（美術 PM，`docs/art/CB-2b檢查.md`）：① 移動後緊接同一隻鳥的攻擊，略過移動結尾的落地與攻擊開頭的起飛，補拍一組連拍；② 確認 `cb2c` `1b`、`1c` 蜥蜴孵化後朝向翻轉只是開發頁手寫狀態、實戰不會，結果回美術 PM。
   - **等美術 PM**：5 款異形（hound、feline、bear、boar、lizard）第二種近戰片段，招單已定，要通知它有 agent 名額就派畫圖。**等使用者**：#148 示範招的附帶效果綁武器，要保留加說明還是換招（玩法 PM 在問）。
   - **教訓**：實作者只跑規格列的目錄時，`tests/skillgen`、`tests/narrative`、`tests/roguelite` 的固定名單與 fixture 會漏；改到技能池或內容的段，規格要把這幾個目錄列進去。
5. **環境坑**：Agent 工具的 worktree 會從 `origin/main` 分出，派工前要先 push，否則 agent 拿不到規格。完成的 agent worktree 會被執行環境鎖住（lock reason: claude agent），不要用 `-f -f` 硬拆。slow 測試要用 `-m "not llm"` 配 `TRPG_FULL=1` 才會跑到。Python 用 `uv run`；worktree 內 `uv sync --frozen --offline`、`corepack pnpm -C client install --frozen-lockfile --offline`；建置 `npx vite build`。

### 3.1 現況（2026-11-07 收尾）

> 3.1 最新；3.2、3.3 是前兩次交接，只為了查脈絡。2026-11-06～11-07 的進度流水（原 3.1）在 `docs/archive/交接歷史-開發PM.md` 末段；更早的歷任小節也在那裡。
> PM id（第三組）：專案 PM `local_e92f686b-c8bd-4b4d-9e22-f0b23d3dc696`、玩法 PM `local_156847a7-c020-45da-84a7-8ced1469e490`、美術 PM `local_42bc346b-cc13-48da-b901-bb0d0b235c64`。美術 PM 的分支 `claude/art-pm-90ce85`（worktree `.claude/worktrees/art-pm-90ce85`）由開發 PM 併進 main；它常只在本機 commit、沒 push，合併時用本機分支。

1. **main 現況**：全部 push，工作樹乾淨，沒有在跑的開發 agent。最後一次全量（TR-1 合併後）：pytest 15349 過（唯一失敗已修：`CharacterState.opening` 補進季末政策 `b9678d36`）、vitest 3301、build、重播全過。版號：`CHAR_FORMAT` **`trpg-char/12`**（TR-1 加 `opening`，舊存檔一律當已完成開局）、`WORLD_RULES_VERSION` **22**、`trpg-wlog/9`、提示詞 `skill-proposal/14`、`storyteller/5`、`situation-check/4`、`flash-variation/5`。import-linter 14 條、複雜度 `noqa` 7 處。
2. **這兩天完成的段**（報告都在 `docs/phases/`，美術檢查在 `docs/art/*檢查.md`）：
   - 環境與 LLM：MAC-1、MAC-2、LLM-1（1A／1B／1C，結案：提議 prompt 回到改前結構）。
   - 整理提案（`docs/phases/整理提案-程式.md`）：文件 DOC-A／DOC-B；程式 CODE-1～3（I1～I7）、I8、R1a～R1e（拆 events、library、ai/utility、skillgen/proposal、BattleRenderer）、R2（測試檔改名）、R3（engine 無循環匯入）、R4（長函式）。剩 R5、R6。
   - Phase 6：6T-1d、UI-E3b／E3c、6R-2（＋6R-2b）、6R-1c、6F-20、6F-21（＋21b）、6F-22（＋22b）、MAP-1、RT-6（＋6b）、HID-1（#144）、TR-1（#134 靶場開局）。
   - **Q 版 QK-1～9 全部結案**（使用者「先讓q板完成」；規格 `docs/art/QK移植需求.md` 第 2 版＋更正 `fcacaa70`）：人物、10 族、裝備、武器、頭像、NPC、召喚物、形態、異形 16 款、頭目 2 位、動畫（含正背面五類攻擊、武器待機、分部件異形動畫）、戰場 ×1.15。
3. **暫停中＝待排（恢復時照順序；使用者 11-07：「跑中都跑完後 不要開新的…我要在windows上測試」）**：
   1. **HID-1b**（`docs/art/HID-1檢查.md`）：「？」與所有 HUD 畫在霧上（人物留霧下）；HP 條與「？」畫在攻擊紅框上；**玩法 PM 條件**：預告（`TelegraphChangeOut` 的 `before/after/amount/text`）對隱蔽且未揭露的單位不得帶出 HP／護盾／狀態（目前可能洩漏狀態到期，要查）；戰鬥主角卡左下「四角飾件」`runCase` 舊 FAIL（依種子出現）；補拍 4 張（1600 選「移動」一般敵人、隱蔽敵人；四角飾件 800、1600）。
   2. **`docs/部署說明.md` Windows 段改寫**（使用者 11-07 Windows 實測）：pnpm 12 在 Windows 全域與 `npx` 都裝不起來（「`...\pnpm\pnpm` 不是內部或外部命令」），`npm install` 報 `EUNSUPPORTEDPROTOCOL workspace:`；可行做法 `cd client; npx vite build`（相依自 10-20 沒變）；git `unknown write failure on standard output` 用 `git config --global core.pager ""`。**建議同段評估把 `client/package.json` 的 `packageManager` 從 `pnpm@12.14.0` 降到 Windows 可用的穩定版（例 pnpm 10.x）**：`pnpm-lock.yaml` 是 `lockfileVersion: '9.0'`，pnpm 9／10 都讀得懂；驗證要先下載 pnpm 10（**下載前要使用者同意**），在 Mac 與 Windows 各跑 `pnpm install --frozen-lockfile`、build、vitest 確認；`scripts/check.py`、`pnpm_command()` 的版本讀取跟著改。
   3. **外觀選單選項改頭像小圖＋郵寄寄件人 Q 版頭像**（美術 PM 併一小段；樣張 `docs/art/外觀變化方案.md` 第 4 節；寄件人要 API 多帶外觀）。
   4. **propose 第 9 題 collision** 每次 `keyword.required` 退回（0.25 段，等玩法 PM 一起看 collision 的 ways）。
   5. **R5**（tests 同名 helper 收斂，含 R2 合併時加前綴的 `_6f4_ok`／`LIB_48F` 等；bal／L／E／G 系列 56 個測試檔改名一併）、**R6**（client 測試 `as unknown as` → 型別化 fixture）。
   6. 其他小項：TR-1 待決 10 點（示範招 6 招、守印人台詞、木樁外觀等交玩法／美術 PM，`docs/phases/PhaseTR-1報告.md` 第 4 節）；人形倒下實機補拍（有人加 AI 代打選項時順手）；`build_proposal_models` 92 行；R1e 各層 `protected` 介面收窄；I8 驗收時在本機存檔建了測試角色「測試」（使用者決定是否清）。
4. **平衡與 LLM 的長期待辦**：原 3.3 平衡待辦核對後剩的列在 `docs/phases/PhaseDOC-B報告.md` 第 2 節（規則類 B-3W、B-3W-2 要回使用者；其餘是未單獨量測的初值與 AI 行為）；LLM 效能（E4B 每題約 14～17 秒、12B 約 59 秒）與「多講一點接線」、12B 基準等專案 PM 指示再排。
5. **開發入口**（QK-9b，只在開發模式＋`TRPG_DEV_ROUTES=1`、前端 `?dev=1`）：開場朝向 `&bossface=`、開場召喚物／形態 `&bossopen=summon|form`、傳送 `&tp=<region>`（`dev-teleport` 直接改角色存檔、不寫世界日誌，該角色之後的世界日誌重播會對不上，專案 PM 已轉知使用者、接受）。畫廊在 `client/dev/*-gallery.html`（I8 搬過）。
6. **環境**：見 §6.1（Mac）。Windows 測試指令見部署說明（待第 3.2 條改寫）。名額：開發同時 ≤ 3、全專案 ≤ 4，平行的 agent 不改同一批檔案；agent 一律帶 `model: "opus"`。

### 3.2 開發 PM 收尾（2026-11-05，使用者重開電腦前）

> （當時的 PM id 已失效，現行 id 見 3.1。）美術 PM 的文件分支由開發 PM 併進 main。
> 待排段的完整清單在 Windows 的共用筆記 `開發PM-待排段-1104.md`（這台拿不到；共用筆記資料夾由專案 PM 的開場訊息給，Mac：`~/Library/Application Support/Claude/side-session-notes/<專案 PM id>/`）。

1. **main 現況**：`2457e3f2` 之後只多了文件合併，全部已 push。最後一次全量（6R-1 合併後）：pytest 15197、vitest 3028、build、重播全過；之後 6T-1c、UI-E3 合併只跑前端與相關測試（vitest 3045）。版號：`WORLD_RULES_VERSION` **20**、`trpg-wlog/9`、`trpg-char/10`、world/4、`LOG_FORMAT` /112。
2. **這幾天上 main 的段**（報告都在 `docs/phases/`，美術檢查在 `docs/art/*檢查.md`（已結案段的在 `docs/archive/art/`））：
   - 6F-4g、6F-4h（起始協同：追印絆擊）— 玩法 PM 確認，6F-4 系列完成。
   - 6F-14～6F-19（格子碰撞：三角形避讓、有人站不畫 ▲N、「+N」膠囊）— **6F-19 美術通過，系列結案**。
   - RT-5、RT-5b～RT-5d（主城開場四格）— **RT-5d 美術通過，系列結案**。
   - 6T-1a（交易前置、郵寄伺服器、#135 掉落）、6T-1b（郵寄前端、別大類主手可換、過期信自動退回）、6T-1c（郵寄驗收修正、寄件填數量、郵差分頁台詞）。
   - 6R-1（#138 獸耳族：獸躍、輕身、崖台、免費換種族；B 矩陣、C 捷徑檢查）— 美術過了崖台，**缺兩種補拍**（見第 4 點）。
   - UI-E3／UI-E4（背包格子、SkillTile、雇用圖示列、出口木牌）— 美術退回 3 必修＋8 小修（併進 UI-E3b）。
3. **未完成的段（都只在本機 worktree 分支，沒有 push、沒有合併）**：

   | 段 | 分支 | 最後 commit | 狀態 | 下一步 |
   |---|---|---|---|---|
   | 6T-1d 郵寄收尾＋soot＋全遊戲按鈕滑過 | `worktree-agent-aa505caec1aede557` | `15139179` | 7 項程式完成、相關 vitest 過；**截圖、全量 vitest、煙霧檢查未做** | 拍 `6t1d_*`（soot 頭像 5 位、郵寄修正、按鈕滑過／停用），交件檢查，合併後送美術 PM |
   | UI-E3b 遇敵卡頭像、傭兵 `skill_ids`＋UI-E3c（UI-E3 退回的 11 項） | `worktree-agent-af9447930647c770b` | `22a64706` | 伺服器欄位完成（相關 pytest、mypy、重播過）；UI-E3c 2、3、4、11 已改未驗；1、5 做一半；6～10 未做；前端遇敵卡縮圖、金環未做 | 照 `docs/phases/PhaseUI-E3b報告.md`（在 Windows 分支，尚未 push）的下一步做完，拍 `uie3b_*`、`uie3c_*` |
   | 6R-2 #137 外觀與中性稱謂＋6R-1 補拍 | `worktree-agent-aae0ccf14bc44eab2` | `4442d65e` | 只有盤點報告，程式未動 | 照 `docs/phases/Phase6R-2報告.md`（在 Windows 分支，尚未 push）第 3 節從 `LookChoice`／`look_options` 開始；範圍見玩法 PM 93beba59（先資料、稱謂、掃「他／她」、LLM 指令；外觀選單用現有部件） |

   - 接手時：分別對這三個分支派 agent 接著做（`git merge main` 後繼續，不要 rebase）；6T-1d 與 UI-E3b 都改 client，但檔案不重疊；6R-2 改 races.yaml、建角、模板與 LLM 指令，和另外兩段不重疊。
4. **待排（依優先）**：
   - **6F-20**（約 0.25，美術 6F-19檢查）：放不下兩圖示的 9 種改回「1 圖示＋+1」（控制＞減益＞增益）、膠囊「+」加長到約 6.5、預覽框最後一行被技能列切、浮動卡最下提示沒圓角、主城 800 任務鈕壓房子與技能卡蓋「WASD」。
   - **6R-1 補拍**（併進 6R-2）：獸躍弧線 GIF 或三連拍、獸耳族建角卡 1600／800。
   - dark_forest 改地圖（被倒木圍住的 2 格要走得進去）。
   - 朝南三角形移出 HP 條；戰鬥撤離「出」框內放小路牌圖示（美術另想）。
   - RT-5 結案後順手：1600 夾邊「！」上邊界確認、rt5d_3 說明列壓木橋。
   - 6F-5 #134 靶場開局（前置 RT-5 已完成；建角三步要等 UI-E1 create-v2 與 Q 版）。
   - QK-1～7 Q 版回歸（等使用者確認樣張；美術 PM 在畫第 17 版）。郵差 `mailbag`、場上 soot、beast_ears 畫法都等 QK。**soot 頭像落點併進 QK**（美術 PM 11-06）：QK 換 Q 版頭像時，頭像配件要先套 `buildScale` 畫在紙娃娃體型座標裡，soot、護目鏡等落點與裁切跟著體型走；QK 頭像驗收拍 tall、stout、一般各一張；之前不做暫時修正。
   - 6T-2 交易所（郵寄上線後）、AU-3、RT-2 補、UI-E1、多講一點接線、角色列表 last_played、12B／31B 基準（等使用者把 LM Studio context 調大）。
   - **Phase 6 收尾報告**：上面做完後再回專案 PM。
5. **這幾天學到的**：
   - `python` 在 Git Bash 是 Windows Store 空殼（結束碼 49、不執行）；腳本一律 `uv run python`，衝突手動用 Edit 解。
   - 6T-1a 合併後全量抓到兩個 agent 漏掉的：主手掉落改 50% 別大類後，舊 loot 測試要固定同大類；新的必填 API 欄位要補 client 測試 fixture，否則 `tsc` 不過（vitest 不查型別，一定要看 build 結束碼）。
   - 改主城或城鎮地圖都要更新 `tests/content/test_field_buildings.py` 的 `RULE_HASHES`；兩段同時改同一張圖會衝突，合併時用最後的內容重算。
   - 效能測試在全量並行下會超時：取 3 次最快（6F-16 起）。
   - agent 有時停在「等背景工作」但其實已經沒有背景程序：送訊息叫它直接重跑、確認跑完再結束。
   - 名額：開發最多 3 個，全專案 ≤ 4；美術 PM 開 2 個時開發降到 2 個。每次派段前先問美術 PM 現在幾個。

### 3.3 第六任開發 PM 進度（2026-11-02）

> 第六任開發 PM（2026-11-02；當時的 PM id 已失效，現行 id 見 3.1）。

1. **完成**（驗收紀錄都在 `docs/phases/PhaseBAL計畫.md` 第 2 節末與第 4～10 節）：BAL-10d／10e（收束、收回家族，`trpg.skillgen.flash_trade`）、BAL-11（預算旋鈕查修）、BAL-12a～12f（技能數值、#76 升階持續上限 6＋強度）、BAL-13a～13e（元素協同、弱 build、#77 連鎖衰減、#78 擴散每輪一次）、BAL-14a～14c（召喚、#79 刪 `boss_blocker_points`）、BAL-15a（法力量測）。`LOG_FORMAT` `/94`；最後全量 pytest 11067、vitest 1176。
2. **進行中**：BAL-15b（#80 敵我同一套資源公式＋模擬 build 資源基礎對齊主角）。
3. **玩法 PM 已接受、不再調**：storm 73%、fire 79%、summoner 74%、精英召喚 86%／群召 88%；「沒有價值的技能」名單原型不換（大世界再量）；頭目 HP 700‰（「頭目死、護衛撤退」待大世界問使用者）。
4. **下一步**：BAL-15b 驗收後，交接歷史 3.00000 第 4 點（`docs/archive/交接歷史-開發PM.md`）的清單已大致做完；剩「下次使用者開模型時 `scripts/eval_flash_diversity.py --real`」、4-L11 小待辦、vLLM oneOf 警告。問專案 PM 下一個大方向。
6. **加速方案（2026-11-02，使用者「好那都改 寫入」，已寫進 CLAUDE.md 第 11 條）**：全量每 2～3 段跑一次，合併時只跑 ruff、format、mypy、lint-imports、相關測試、一場重播；待決的原型數值／解讀類由 agent 照保守預設做完，確認累積到下一段，不另開收尾段（規則類照舊先問）；agent 開發中只跑直接相關的測試檔，CLI 快照與大範圍測試只在交件前跑一次；全量用 `-n 12`～`-n 14`、全量期間不跑模擬；CLI 輸出快照拆成可平行的小測試（排在 BAL-17 之後的一小段 PERF-1）。Windows Defender 排除由使用者自己決定，不要動。
5. **做法**：全量檢查不要和模擬同時跑（曾因資源不足讓 xdist worker 掛掉）；agent 暫存放各自 worktree 的 `.scratch_<段>/`，不用共用 scratchpad（曾誤跑別段的同名腳本）；兩段都改引擎時排先後，後段 merge main 再重產快照；agent 改 content 數值後常漏跑 `tests/api`、CLI 輸出快照，合併後全量會抓到。

---

### 3.00000 接手第一件事（2026-10-31 第五任交接，最新，優先於下面各節）

> 使用者：「但我覺得對話太長了 要你們交接」。第五任開發 PM `local_ab425b7d` 到此交接。專案 PM `local_69ff6dd8-1a56-4d3a-950d-054825e07625`、玩法 PM `local_9c79efb1-a93e-4b28-8a2f-7c97ec50b846`、美術 PM `local_cb74dfda-1832-4c4b-bf87-d4dcb9fbf335`（交接後 id 可能換，以專案 PM 通知為準）。

**1. 進度**
- **Phase 3W**（白板與閃現）完成，含審查整理 3W-R1／R2（`Phase3W計畫.md` 第 4、6 節）。
- **4-L9～4-L11b**：真模型評估（`Phase4-L9報告.md`）→ 4-L10 schema／提示修正（升級候選 28% → 62%）→ 4-L11 敘事對齊效果與世界觀詞上限、卡片重複行 → 4-L11b 詞表（燃燒、易傷、比喻跳過、missing_added 放寬）。樣本：`docs/phases/4-L9/AI生成樣本.md`、`AI生成樣本_4L11.md`；多樣性量測 `閃現提議多樣性.md`；查修 `閃現轉型與護盾模板查修報告.md`、`複合技轉型報告.md`。
- **平衡階段**（`docs/phases/PhaseBAL計畫.md`，驗收紀錄在第 2 節、新順序在第 3 節）：BAL-1～BAL-9c、BAL-10a／10b 完成並驗收（靈感每勝 2、三種閃現 AI、姿態／形態幅度、難度倍率、守點、第 3 場 3 名、Boss 援軍 1、盜賊隊長、AI 修正、武器數值、boss_approach 10、頭目 HP 700‰、弓手護衛 1d6、弩 pierce_permille 400、小變化模板補第一段）。
- **BAL-10c**（變身姿態只出修正類、進入代價 −1 可減法力／耐力、`mod_cost` 不讓代價消失、閃現目錄依種子打亂）：見本節第 2 點的狀態。

**2. 交接時的狀態**：BAL-10c 已交件、合併並 push（報告 `docs/phases/BAL-10c報告.md`；合併後 ruff、format、mypy、lint-imports、skillgen／llm／content／roguelite／narrative／cli pytest 6407 通過、swamp 種子 7 重播通過；最後一次**全量**是 BAL-9 合併後：pytest 10793、vitest 1176）。四位 PM 的交接 commit（專案 PM 2da95ec0、玩法 PM 6ef9bb2a／1dd74ae9／d343796d／8cd9a725／01ebc927、美術 PM c14a80fc）都已併入並 push，main ＝ origin/main。**沒有 agent 在跑**。工作區只有不明的 `tmp_x`（不是開發 PM 建的，不要動）。`LOG_FORMAT` `/90`、存檔 `trpg-run/13`。
- BAL-10c 待決（交玩法 PM）：8 個變身姿態各階第 1 次只剩 1 個選項（只能新增非費用的形態旋鈕或接受）；`mod_cost` 只對 2 格以上代價出，內建幾乎沒有；打亂是否降低位置偏好待下次真模型量測。
- 新開發 PM 建議先跑一次全量（`UV_NO_SYNC=1 uv run pytest -q tests -n 6 -m "not llm" --timeout=3000` 加 vitest、build），因為 BAL-9c～10c 之間只跑相關檢查。

**3. 平衡方向（使用者 2026-10-31）**：「反正到時候大世界又不會要求你要打5局就要打BOSS…本來打不過就要練等不是嗎」→ **不追一輪勝率**；重心放在會帶到大世界的東西（單場難度、武器、技能數值、召喚、AI、資源）。已定的原型數值不再調。原型數值玩法 PM 可直接定；會帶到大世界的規則回使用者；**已寫入設計文件的決定只有使用者能改**（玩法 PM 自己定的細節由玩法 PM 改）。

**4. 下一步（依序）**
1. **BAL-10d 收束**（#74，06 6.34.4，`1dd74ae9`）：照原規格；把「放棄一部分 → 換核心數值」做成共用機制；量收束火球閃滿倍數、AI 選中比例，以及兩種練法比較（第 1、2 次收束＋蓄力 vs 第 1、2 次擴範圍、第 4 次收束；確認預算守恆、不超過 3 倍上限）。範圍在 `PhaseBAL計畫.md`。
2. **BAL-10e 收回家族**（#75，`8cd9a725`）：精煉、合體、專注、陷阱／地面格收束；做完重掃 BAL-10a 不足名單（`scripts/flash_minor_coverage.py`）。
3. 下次使用者開模型時：`scripts/eval_flash_diversity.py --real` 重量位置偏好（打亂後「第一個提議取自前三分之一」應接近 33%）。
4. **預算旋鈕查修**：約 300 次 keyword_exploit／keyword_imbue 結構合法但重調不進預算窗；姿態冷卻折抵另訂（遠小於主動技）；舊 `mod_potency` 等階梯改細（接續段 100‰、形態 50‰、修正傷害 25‰ 都大於一次閃現 +40‰）。
5. **技能數值批**：5 個沒有前段的 build（assassin、support、charger、gambler、seer）、偏強 fire／summoner、火系法力費用（火焰流 Boss 戰短缺 29%）、修正型被動幅度階梯（B-3W-5）、完整技能 +150‰ 超標、層數待辦（B-3W-4）、小變化補第二段（被動與反應、工具技／召喚／常駐／地面格／陷阱；觸發冷卻守 6.6）。
6. **召喚**（B2～B4；順便看有召喚 Boss 戰 10.8 輪是否降到 ≤ 10，否則考慮頭目 650‰；Boss 戰灌注）。
7. **資源（法力）**（B9、B11、B14、B15；「法力回滿時機」屬規則）。
- 規則待辦（玩法 PM 記著，之後整理給使用者）：Boss 戰「頭目死、護衛撤退」；B-3W-2 輔助→被動轉型。
- 4-L11 後的小待辦：閃現 `name_offer` 遊戲內命名尚未接（之後接時傳 `before`）；形態／規則修正技能的效果比對未納入一致性檢查。
- 伺服器警告「oneOf … falling back to anyOf」（vLLM xgrammar）：4-L10a 拆分支造成，不影響正確性；可排小段給分支加互斥固定欄位。

**5. 這任學到的做法**
- **等待一律用完成通知**，派工 prompt 必寫「不准用 `until grep ...; sleep` 輪詢迴圈」（曾掛 2～4 小時，見記憶 no-until-poll-loops）。
- pytest 指令加 `--timeout=1800`、不要用管線接 pytest 輸出；`tests/cli` 加 `--timeout=3000`。
- 兩個 agent 都會重挑種子時（例如一個改 AI、一個改數值），合併易在測試檔衝突；改成後一段在前一段合併後重挑，或由後一段 `merge` 前一段分支再解衝突（BAL-4c 的做法）。
- 量測先、套用後：平衡段一律「只在模擬覆寫量測 → PM 定值 → 寫進 content → 複測」；寫死數值的測試改讀 content；靠種子的測試重挑種子、斷言不改。
- 真模型評估：本機 8001 由使用者開關，絕不結束它；開跑前先問專案 PM 模型是否開著；樣本用固定種子以便新舊對照。
- 系統 `python` 是 Windows Store 空殼，一律 `uv run python`；用 Python 寫檔要 `newline="
"`，避免 CRLF。

### 3.0000 接手第一件事（2026-10-29 第五次，最新，優先於下面各節）

> **2026-10-30：Phase 3W（白板與閃現）全部完成並 push，含整理子階段 3W-R1／R2；下一步待專案 PM 與使用者決定（4-L9 等使用者開本機模型）。**
> 第五任開發 PM 的 session：`local_ab425b7d`（由專案 PM `local_69ff6dd8-1a56-4d3a-950d-054825e07625` 啟動）。**下面 3.000 第 5 點的各 PM session id 已過期**：專案 PM `local_69ff6dd8-1a56-4d3a-950d-054825e07625`、玩法 PM `local_9c79efb1-a93e-4b28-8a2f-7c97ec50b846`、美術 PM `local_cb74dfda-1832-4c4b-bf87-d4dcb9fbf335`（美術分支 `claude/art-pm-fcab45`）。

1. **完成**（驗收紀錄）：3-54c／d／e（`Phase3計畫.md` 66～68 節）；3J-1a～3J-5、3J-4b／4c（`Phase3J計畫.md` 4.x）；C-1a～C-3（`PhaseC畫風計畫.md`，美術 PM 檢查在 `docs/art/*檢查.md`）；3R-1～3R-3c（`Phase3R計畫.md` 4.x）。技能 301；`LOG_FORMAT` `/85`；存檔 `trpg-run/7`；最後全量 pytest 8527、vitest 1103。
2. **2026-10-29 晚更新**：3T（1～8）、3R-4（鱗族 #68）、4-L6／6b／7／8／8b 全部完成並 push；技能 301、`LOG_FORMAT` `/87`、存檔 `trpg-run/10`；最後全量 pytest 8766、vitest 1145。**下一步：等專案 PM 通知使用者開本機模型後做 4-L9**（`Phase4計畫.md` 表格 4-L9 列與 3C 節 4～6）；不進平衡階段或 Phase 5。派工的 pytest 一律 `-m "(slow or not slow) and not llm"`。
2b. **（舊）進行中**：Phase 3T（`Phase3T計畫.md`，兩份後段審查的整理）：3T-1（change 種類與預算旋鈕進 YAML，opus）、3T-4（前端整理）；之後 3T-2 → 3T-3（可和 Phase 4 平行）→ **Phase 4 從 4-L6 起**（`Phase4計畫.md`）。
3. **待使用者決定**：鱗族「水與冰面移動不花額外點數」（引擎本來沒有額外花費，被動實際只有不滑倒；玩法 PM 已交專案 PM）。
4. **待辦（不擋 Phase 4）**：AI 不施放純地形技能（大地崩陷）；`Phase3T計畫.md` 第 1 節末的延後項；晶能義體人辨識樣張（美術 PM 之後出）；召喚物實戰外觀美術 PM 尚未看（等有可選的召喚角色）。
5. **經驗**：兩個 agent 同時遞增 `LOG_FORMAT` 幾乎每次都撞，合併時取較大＋1，用 `git grep "battle-log/NN"` 找齊字面值（含 `endswith("/NN")`），`runner.py` 文件字串要補齊每一版；agent 一次跑全部 tests 曾讓 xdist 卡住，派工 prompt 要寫「不要一次跑全部 tests、跑測試時不要同時改檔」；審查 agent 沒用 worktree 時會直接 commit 到 main，合併前看 `git status`。

### 3.000 接手第一件事（2026-10-28 第四次交接，最新，優先於下面各節）

> 上一任開發 PM：`local_e6fcf372`（2026-10-24 接手，做到 3-54b 暫停；使用者換對話）。**只讀本節就能開始**，細節再看本節指到的檔案。和使用者、各 PM 一律用繁體中文。

**1. 現況（交接時）**
- main ＝ origin/main ＝ `030fa5ef`（含本節更新後的 commit），工作區乾淨（只有不明的 `tmp_x`，不是開發 PM 建的，不要動）。**沒有任何 agent 在跑**。使用者在 3-54b 後暫停：「做到 3-54b 先停 token 要沒了」——**恢復前不要派新段**，等專案 PM 轉達。
- 最後一次全量（除 `llm`）：pytest 7873、vitest 994、mypy、lint-imports、重播全過。`LOG_FORMAT` `/77`；存檔 `trpg-run/6`；內建技能 268＋後續段落新增（以 `content/skills/` 為準）。
- worktree：`git worktree list` 還有 5 個舊的 locked 登記（`agent-a1403…`、`a423…`、`a57d…`、`a9173…`、`aa62…`，前任遺留，分支已合併或作廢）與 3 個美術 PM 的 worktree（`art-pm-20b75c`、`art-pm-5ea9fb`、`art-style-sample-404539`，**不要刪**）。`.claude/worktrees/` 底下約 38 個資料夾是已刪分支的殘留（檔案被鎖、`git worktree remove` 刪不乾淨），可在沒有 agent 時手動清，刪之前確認裡面的 `client/node_modules` **不是連結**。

**2. 恢復順序**
1. **3-54c 種子技能**（`Phase3計畫.md` 第 64 節）：風 6、毒 6、大地 4、神聖 2（06 6.33）；「清風」用清除表面效果（#63，不靠風元素、不觸發擴散）；**補完毒種子後刪 `content/skill_keywords.yaml` 中 `poisoned` 的 `start_hidden`，並拿掉 3-53 的保守測試標記**（`EXTRA_KEYWORDS`、`test_pools_24c.py` 的 `short == {"poisoned": 1}`、`test_keyword_start.py` 起始技能剛好 1 招）。
2. **3J 形態**（`Phase3J計畫.md`）。
3. **3R 種族與出身**（`Phase3R計畫.md`；**2026-10-29 使用者「外觀先等」：3R-3a／b 種族外觀（含成對武器錯開小修）與 3J-5 先不做，等 C 手繪墨線畫風定案〔美術 PM `claude/art-pm-fcab45`〕再用新畫風做**；3R-3a 含 3S-3 美術小修：成對武器遠側的手槍、斧、錘往前上方錯開約 3px；種族角可用 `paperdollSideGear.drawHornSide`、側面種族部件掛 `SideHooks.race`）。
4. **Phase C 紙娃娃 C 畫風**（`PhaseC畫風計畫.md`，2026-10-29 排入）：C-1a、C-1b、C-2 要在 3J-5 與 3R-3a／b 之前，C-3 召喚物（使用者 2026-10-29 決定做）排在 C-2 之後；可和 3J、3R 的規則段平行。
5. **Phase 4**（4-L6 起，`Phase4計畫.md`）。

**3. 待玩法 PM 決定（恢復時先問）**
- 3-54b：「大地元素」定義（現為標籤 `earth` 或效果元素 `earth`）；工坊不能選標籤，純地形技能做不出來；石膚、震波沒限大地；震波仍要命中；石膚、震波、擴散 2 格預算初值；`content/workshop_text.yaml` 新增的震波與擴散格數說明是初稿。
- 3-55：工坊沒有主角手上武器的來源（App 沒傳 `heroWeapon`，API `/api/workshop/options`、`/api/workshop/check` 已支援 `weapon`）；無持有者卡片「縮放：武器的屬性」仍泛稱；「手持指定武器」命名。
- 各段驗收紀錄（含已回覆的待決）：`Phase3計畫.md` 51～65 節（含 60b、60c、62b、63b、64.1）、`Phase3I計畫.md` 4.1～4.6、`Phase3K計畫.md` 5.1～5.4、`Phase3S計畫.md` 檔尾。

**4. 平衡待辦**：本檔 3.3 的 B1～B25（使用者：平衡延後，驗收時只判斷並記錄、不調）。

**5. 流程（照做）**
- **流程改善 A～F**（2026-10-24 使用者同意，細節在本檔 6.2 與 6.5.1）：A 決策影響盤點（寫規格前先盤點受影響的既有功能）；B 行為一致測試（規則句一律要實際跑引擎的表格測試）；C 已寫入設計文件的決定只有使用者能改（PM 之間不在對話裡放寬，玩法 PM 也不能自己改已寫入的規則，要問使用者）；D 排版煙霧檢查（`window.__layoutSmoke`，先 `localStorage.clear()`）；E 一次出事就全面掃描；F 禁止結束不是自己啟動的程序。
- **派工**：同時最多 2 個 agent；規格寫明 `tests/engine` 與 `-m "slow or not slow" tests/cli --timeout=3000`；agent 開工先 fast-forward 到 main；不准建 `client/node_modules` 連結（`corepack pnpm -C client install --offline --frozen-lockfile`）；agent 回報後若顯示「waiting on its own background work」用 `TaskStop`。
- **合併**：`git merge --no-ff` 後在 main 跑「除 llm 的全量」（`UV_NO_SYNC=1 uv run pytest -q tests -n 8 -m "not llm" --timeout=3000`，加 ruff、format、mypy、lint-imports、`corepack pnpm -C client build`、vitest、一場重播；約 8～20 分，背景執行），**全過才 push**；背景檢查跑時不要改工作區。兩個 agent 同時加技能或遞增 `LOG_FORMAT` 必撞：`skill_icons.json`（`uv run python -m tests.narrative.icon_fixture`）、CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`）取 `--theirs` 再重產；`LOG_FORMAT` 取較大＋1、`runner.py` 文件字串兩段都保留、測試字面值一起改；改了 API 型別要重產 OpenAPI（`uv run python scripts/export_openapi.py` → `corepack pnpm -C client gen:api`）並修 vitest 夾具。
- **已知地雷**：
  - 前端指令一律 `corepack pnpm -C client …`（在 `client` 資料夾內執行 build／vitest）；`node_modules` 壞了用 `corepack pnpm -C client install --offline --frozen-lockfile --force` 從本機快取還原，不要下載。
  - Windows 路徑：`Path.resolve()` 很慢（內容庫已快取 `bundled_content_dir`）；Git Bash 下用 `/f/...`，PowerShell 與工具參數用 `F:\...`；暫存腳本放 scratchpad 或 `$TEMP`，不要放專案資料夾（會被 ruff 掃到）。
  - 不要 `taskkill /IM python.exe`、`pkill` 之類；只停自己的 PID。預覽伺服器不要用 8000（使用者）、8001（本機 LLM）——`.claude/launch.json` 有 `trpg-serve-verify`（8011）。
  - **兩個開發 PM 同時動 main 的教訓**：2026-10-24 交接時前任其實還在執行、直接在主資料夾改檔，差點互相覆蓋。接手先 `git status`、`git worktree list`、`list_sessions` 確認前任是否 idle，有人在動就停手並問專案 PM 由誰做。其他 PM（專案、玩法）也會在 main 上 commit 並 push，可能把你尚未全量檢查的合併一起推出去——合併後盡快跑全量。
  - 測試偶發：召喚物 HP 斷言在多 agent 搶 CPU 時偶發失敗，單獨重跑會過；`tests/cli/test_output_snapshots.py` 單一測試接近 300 秒，一律加 `--timeout=3000`。
- **回報**：只在「驗收合併完成（附給使用者的檢查重點）」「卡住」「需要決定」時傳給專案 PM `local_46ffc72c-28dd-48aa-9eb7-f1724ef32432`；規則問題直接問玩法 PM `local_e3a02b51-b04a-41ac-a356-7aef049c8be2`；美術驗收找美術 PM `local_1501da38-7be4-4aad-8915-c16e592f04f3`（分支 `claude/art-pm-5ea9fb`，由開發 PM 併進 main）。

### 3.00 接手第一件事（2026-10-23 第二次交接，最新，優先於下面各節）

**目前停在哪（使用者暫停）**：使用者：「做完這些後就先停」（專案 PM 轉達）。**沒有任何 agent 在跑**；main 與 origin 一致、`check.py --full` 在 3-37b 後跑過（5178 pytest＋816 vitest，唯一失敗是雲嶺改名造成的 CLI 快照，已更新 `75b8a95`）。**恢復前不要派新段**，等專案 PM 轉達使用者恢復。

**這一輪完成的（2026-10-23）**：
| 段 | 內容 | 驗收紀錄 |
|---|---|---|
| — | `check --full` 28 分 → 6 分 38 秒（`bundled_content_dir` 快取） | 本節下方 |
| 4-L4 | schema 子集、`available` 格式、`build_proposal_prompt` | `Phase4計畫.md` 4.4 |
| 4-L5 | 重試迴圈、預算器補數值、引擎修補、三層退回、`trpg llm propose` | 4.5（第一次真模型小測試：退回 50%） |
| 4-L5b | 隱藏組合規則進 YAML／schema（`form`）、狀態依稀有度篩、先修可修再回報、骨架資訊進 `available` | 4.6（第二次小測試：種子 0 退回 10%） |
| 4-L5c | 開關只能 true、列舉去掉不能施加的狀態、估算不算 schema、專屬錯誤代碼、CLI 不出不可能題目 | 4.7 |
| 3-35 | 前端字型 Noto Sans TC（400／700 自帶） | `Phase3計畫.md` 39.1 |
| 3-36a／b | 狀態圖示、戰場效果（美術 PM 驗收通過） | 40.1.1、40.2.1 |
| 3-37a／b | 區域主題底層、雲嶺換皮（`bridge_chasm`→雲海吊橋、`dark_forest`→竹林） | 41.1.1、41.2.1 |
| 3-38 | 可燃標記平時淡化（使用者選 C） | 42.1 |
| 小修 | 嘲諷 `control_group: mental`＋`budget_points` 3（玩法 PM）；拖曳線位置（`358a43a`）；格子資訊卡換格 80ms（`f64bb3b`，規則見 6.5.1）；雲海山谷調暗 | 各自 commit |

**恢復後的下一段（依序）**：
1. **4-L6**：接進候選產生器（`llm` 來源、寫進 run 紀錄、重播不呼叫 LLM、Mock 失敗仍 3 個候選、設定可關 LLM）＋ **3C 節原語多樣性 1～3**（題目指定核心原語、輪替選單、run 內配額；使用者 2026-10-23 決定）＋ **LLM 技能強制帶題目關鍵字**（4-L5 待決 #1；小測試的 `keyword.required`）。規格要先寫進 `Phase4計畫.md`（照 3A～3E 格式）。可與 4-L7（名稱與敘事）平行。
2. 4-L8（開放更多結構；`budget.over`／無旋鈕結構 44／161、AP／冷卻旋鈕、`unit_then_tile` 等旗標）→ 4-L9（真模型評估＋3C 節強制／自由測試）。
3. ~~3-41a／b 說明文字整修~~ **已完成（2026-10-23，`Phase3計畫.md` 45.3～45.4）**。
3a. ~~3H 屬性系統~~ **已完成（2026-10-24）**：3H-1～3、3H-5（耐力每回合 +5、戰後回滿）、3-41c；驗收見 `Phase3H計畫.md` 第 5、6 節。`LOG_FORMAT` 現為 `/61`。
3b. ~~3-41c~~ 已完成（`Phase3計畫.md` 45.6）。
3c. **排程（2026-10-24，使用者定）**：3H-7＋3H-8 → 3-47 → **3I 第二批武器＋魔劍士**（`Phase3I計畫.md`，1～4）→ **3J 形態系統**（`Phase3J計畫.md`，約 4.4～5.2 段）→ Phase 4（4-L6 起；含「自然」主題）。待排：戰後裝備三選一（玩法 PM 備設計中）。三個小原語中的定向蓄力已提前到 3J，其他兩個排在平衡階段之後。
4. 介面／美術：**3-37c 雲嶺服裝部件**（`Phase3計畫.md` 41.3，後放）；五區其他區等美術 PM。
5. **3E-3**（`Phase3E計畫.md` 3.2）可穿插；平衡 B1～B9（本檔 3.3）延後。

**本機模型（真模型測試）**：`F:\WSL\settings.ini` PORT 已改 8001（使用者 2026-10-23）；`config/llm.toml` → `http://localhost:8001/v1`、`swift`、**`enable_thinking=false`**（Qwen3 預設思考會用光 2048 輸出、回空）。strict JSON schema（含 `$ref`／`oneOf`，根層 `oneOf` 也可）vLLM 接受；schema 不佔 prompt token（最大題目實際 2,525）。關思考約 4～13 秒／次。測試：`uv run trpg llm ping`、`uv run trpg llm propose -n 10 --seed 0`（小測試）、`uv run pytest -m llm`。開發與自動測試一律 Mock；模型由使用者用 `F:\WSL\start.bat` 啟動，連不上或顯存不足時回報專案 PM，不要請使用者改 settings.ini。**預覽伺服器不要用 8000（使用者）或 8001（模型）**：`.claude/launch.json` 有 `trpg-serve-verify`（8011）。

**`check.py --full` 變慢（已解決，2026-10-23，`dabb5a9`）**：原因是 3E-2f 起每次建構 `EffectSpec` 都經 `default_content_dir()` 做 `Path.resolve()`（Windows 很慢，`run auto` 一半時間在這）；`bundled_content_dir()` 加 `@cache`、`run auto` 十種子測試改參數化。`--full` 28 分 → **6 分 38 秒**。之後若再變慢，先用 `--durations=30` 加 cProfile 單跑 `trpg run auto --seed 1` 找熱點。

**待查（2026-10-23 發現）**：`tests/engine` 裡召喚物 HP 的兩個測試（石像 `summon_golem`、骷髏 `summon_skeleton_warrior` 的 max_hp 斷言）在 `tests/roguelite`～`tests/engine` 九個資料夾一起 `-n 8` 時偶發失敗、重跑通過；單獨或兩兩組合都過 → 疑似某測試改了共用狀態（3-41a 的 `content/summons.py` 或內容庫快取）沒還原。下次全量檢查若再出現就追。

**驗收動畫的方法（2026-10-23 起）**：網址加 `?anim=0.1`（再慢 10 倍，可配播放列「極慢」再 ×5），內建瀏覽器每張截圖約 1 秒也能抓到移動中途的畫面。

**這一輪學到的**：合併前「相關測試」範圍要含 `tests/skillgen`（嘲諷改動時漏跑 `test_budget` 寫死的點數）；`.claude/worktrees/` 舊資料夾會累積（2026-10-23 清過 42 個，約 3 GB），合併後記得 `git worktree remove` ＋ 刪分支；主資料夾有不明的 `tmp_x`（不是開發 PM 建立的，沒動）。

**其他待辦位置**：
- **3E-3**（可在 Phase 4 期間穿插，一次最多 2 個 agent）：`Phase3E計畫.md` 3.2。
- **平衡階段清單 B1～B9**：本檔 3.3（使用者：平衡延後，驗收時仍判斷並記錄數值、不調）。
- 審查全文：`docs/phases/Phase3審查-Python.md`、`Phase3審查-前端.md`。

**常駐規則（都在本檔，照做）**：
- 回報：PM 之間只在「某段驗收合併完成（附給使用者的檢查重點）」「卡住」「需要決定」時傳訊息；不傳告知類（6.2 開頭）。
- 檢查：每段合併只跑快速檢查（ruff、format、mypy、相關測試、一場重播、有改前端才 `pnpm build`）；全量 `check.py --full` 每 2～3 段一次（6.2 第 5 點；CLAUDE.md 守則 11）。同時最多 2 個 agent；agent 不跑全量；長指令加 timeout 或背景執行；agent 在自己的 worktree 跑並用 `UV_NO_SYNC=1`。
- git：共用資料夾只用 `git pull --ff-only`，不 rebase；push 前 `git log origin/main..HEAD` 確認沒有別人的 commit（6.6 第一條）。
- 直接打 `python` 可能是 Windows 商店空殼，一律 `uv run python`；臨時腳本放 scratchpad 或 `$TEMP`，不要放在專案資料夾（會被 ruff 掃到）。
- `LOG_FORMAT` 目前 `/57`；平行段落同時遞增時，合併者改成下一號、`runner.py` 文件字串都保留、測試的 `trpg-battle-log/N` 一起改。
- 前端彈出 UI 一律用共用浮動卡元件（6.5.1）。
- agent 回報後若顯示「waiting on its own background work」，用 `TaskStop` 停掉。

### 3.0 接手後要做的（2026-10-22）

> **最新狀態（2026-10-23）**：Phase 3、結束審查、3E-2a～g 全部完成；`LOG_FORMAT` `/57`。**Phase 4 開工**：使用者已決定 5 題（碎界、本機 vLLM 模型、LLM 只選結構、加給 LLM 的短說明、重試 3 次＋退回率 20% 警示），規格 `docs/phases/Phase4計畫.md`（4-L1～L9）。已派 4-L1（LLMClient＋本機 OpenAI 相容 client）與 4-L3（提議模型正式化＋`llm_hint`）。**待使用者**：把 `F:\WSL\settings.ini` 的 `PORT` 改成 8001（避開 `trpg serve` 的 8000）。3E-3 可穿插；平衡在平衡階段（3.3 B1～B9）。

> （2026-10-22 暫停後已恢復，「繼續」；3-33e2b 已驗收 push，3-33e2a 由合併 agent 處理衝突中。）

1. **確認環境**：`git status` 乾淨；`uv run python scripts/check.py` 全過。使用者常自己開 `uv run trpg serve` 佔用 8000 埠：**不要關使用者的程序**，`preview_start` 會自動改用 8001。程式改動後要 `corepack pnpm -C client build` 並請使用者 **重開伺服器** 才看得到。
2. **使用者的 🎮 戰鬥手感檢查**（`docs/專案計畫.md` 第 14 節；問題清單在 `docs/玩法PM交接.md`）：回饋中規則與玩法交給玩法 PM，介面問題排成下一個介面段（**編號從 3-18 起**）。
3. **下一步（2026-10-22 交接；使用者選 A）**：
   - **3-25 戰場變奏**（玩法 #25，`docs/design/06-技能.md` 6.24）：**由接手的開發 PM 撰寫規格並派工**。排程表在 `Phase3計畫.md` 第 21 節；6.24 的變奏可帶關鍵字（3-24b 已做關鍵字推導，推導分級見 26.3：開局與候選只用專屬規則）。新規格請寫在 `Phase3計畫.md` 第 33 節之後（第 30、31 節是 3-28、3-29，第 32 節是 3-30 試玩回饋小修）。
   - **第二次試玩回饋**：與 3-25 同時進行；回饋由專案 PM 轉來，排成新的介面小修段（編號接 3-30 起）。
     - 清單在 `Phase3計畫.md` 第 32 節：#1 浮動卡互動規則一致化（32.1，2026-10-22 已派工）。
   - 之後加排：3-31 普攻與符文（#39）、3-32 普攻流（#40）、3-33a～h 召喚物（#41，`Phase3計畫.md` 第 36 節）。**使用者同意召喚物全部做完再做結束審查**（「可以」，2026-10-22）。
   - **🎮 戰鬥手感檢查點：使用者確認通過（2026-10-22）**——使用者原話：「3 我就不用了 我覺得還行了 之後再修就好」（「3」＝收尾流程中的「使用者試玩確認」）。收尾順序：排定的段（3-33d～h、3-32b、3-32d 普攻流修正）做完 → 直接 Phase 3 結束審查 → 3E-2／3E-3；中間不等使用者試玩，之後有試玩回饋照常插隊小修。
   - **收尾順序（2026-10-23 更新，使用者：平衡延後）**：3-33f2 push → 3-33h2 → Phase 3 結束審查 → 3E-2／3E-3 → Phase 4。3-33g 移到平衡階段（3.3 B2）。
   - 3-33 全部完成後：**Phase 3 結束審查**（下一點）→ 3E-2／3E-3（第 5 點）→ Phase 4。
   - 3-28 已完成先前累積的介面小修（`Phase3計畫.md` 24.4 清單清空）；3-29 修好衝鋒類技能打不到貼牆／地圖邊的敵人（請使用者試玩時實機確認點敵人格的體驗）。
   - 待玩法 PM 回覆：3-26b #1 是否補輔助類進化模板（47 招主動技沒有合格進化）。
   - **已知問題**：多個 agent 同時跑全量 `check.py` 時，平行 pytest 會在 98% 停住（3-24c、3-27 都遇過，PM 單獨跑會過）→ 審查時查原因；一次最多平行 2～3 個 agent，PM 合併後自己跑一次全量（可能超過 10 分鐘，用背景執行）。
   - 合併慣例：平行段落常同時遞增 `LOG_FORMAT`（目前 `/46`），合併時改成下一號、`runner.py` 文件字串兩段都保留、測試的 `trpg-battle-log/N` 與 `endswith("/N")` 一起改；產生檔 `client/src/render/fixtures/skill_icons.json`（`uv run python -m tests.narrative.icon_fixture`）、CLI 快照（`UPDATE_CLI_SNAPSHOTS=1`）、OpenAPI 重產；`styles.css` 衝突多半在檔尾，兩邊保留並補回被切掉的 `}`。agent 回報後常不會自己結束，收到報告就 `TaskStop`；brief 結尾加「完成回覆後就結束，不要留下背景工作」。
   - 美術 PM 的成果在分支 `claude/art-pm-20b75c`，由開發 PM 併進 main（`git merge --no-ff`）。
4. **Phase 3 結束審查**（6.5）：範圍 `2c42268..HEAD`（上一次審查到 3C／3D 結束；之後是 3E-1、3-5～3-27、3F、3G）。範圍很大，建議拆成 2～3 個審查 agent（引擎與內容／前端 `client/src/render/`、`BattleScreen.tsx`／roguelite 與裝備）。另請查：多 agent 時全量 pytest 卡在 98%、各段新增的 `PLR0917`／`PLC0415` noqa。**必查：全站浮動卡一致性**——盤點所有彈出 UI（卡片、說明框、資訊卡、選單）是否都已改用共用元件並符合 6.5.1，列出未改的位置。另查 3-25a 合併後一次全量 pytest 平行收集時的 `ImportError`（`tests/engine/test_variant*.py`，重跑通過）。結論排進 3E-2／3E-3 或新的整理段。
5. **Phase 4（LLM 技能生成）之前**：3E-2（數值上下限以 YAML 為唯一來源、落點函式合併、`FieldSpec` 旗標、原語 `player_description`、效果／條件／觸發中文名進 glossary API）、3E-3（interpreter 拆成原語 handler 註冊表）；待決定 #5 的 **世界觀**（美術原型已決定：程式繪製）。隨機組合器目前不產生暫時障礙與煙霧（3-11 #8），Phase 4 生成時一併開放。工坊的選項推導（`trpg.skillgen` 的 `draft_options`）與 `icon_of`、`tile_info` 可直接給 LLM 流程用。

### 3.0.1 使用者已做的決定在哪裡

| 主題 | 位置 |
|---|---|
| 玩法決定 #1～#21 | 總表 `docs/玩法PM交接.md`；全文 `docs/玩法決定紀錄.md`；設計細節 `docs/design/` |
| 美術：原型採程式繪製（地形、紙娃娃、組裝式技能圖示） | `docs/專案計畫.md` 3.2 #5；`docs/美術PM交接.md`；需求 `docs/art/移植需求.md` |
| 畫面與手感提升（不做 3D／等角，2D 俯視角） | `Phase3計畫.md` 第 15 節開頭 |
| Phase 3 網頁與 roguelite（戰鬥間不回復只在營火回滿、隊友維持標準兩名、每場固定經驗、專屬 Boss 地圖） | `Phase3計畫.md` 0.2、0.11 |
| 3C、3D、3F | `Phase3C計畫.md` 0.1；`Phase3D計畫.md` 0.1、0.6；`Phase3F計畫.md` 0 節 |
| CI 只手動觸發 | 本檔 6.1 |

### 3.0.2 各段「待 PM 決定」的處理狀態

- 所有已完成段的「待 PM 決定」都已逐條處理，寫在各計畫檔的驗收小節（「接受」「平衡階段」「排進某段」）。
- **已排定但未落地**：上面 3.0 第 3 點（3-18 介面小修）與第 5 點（3E-2、3E-3）。
- **標「平衡階段」的**：見 3.3。

### 3.0.3 前一位 PM 的備註

- **平行開發**：前端段落常用 `isolation: "worktree"` 平行派兩個 agent，在 prompt 寫明「誰負責哪些檔案、API 型別只新增」；合併用 `git merge --no-ff`，衝突多半在 `styles.css` 檔尾或 `client.ts` import（兩邊都保留）；`openapi.json`／`schema.d.ts` 衝突時重跑 `uv run python scripts/export_openapi.py` 與 `corepack pnpm -C client gen:api`。合併後自己跑 `check.py` ＋ `pnpm build`。實作 agent 偶爾在主資料夾留 log 檔，合併前 `git status` 清掉。
- **瀏覽器驗收**：用 `javascript_tool` 設選單（原生 setter ＋ `change`）與點按鈕；格子用 `computer` 點前先 `screenshot`。內建瀏覽器模擬 1600×900 時 **截圖會縮成只佔左上角**，那是截圖工具的問題；版面以 DOM 量測為準（`innerWidth`、`getBoundingClientRect`）。播放速度存在瀏覽器，若停在「略過」會看不到動畫。
- 用 API 查合法動作或錯誤原因很快（`/api/battles/{id}`、`/preview`）；一輪可用腳本 `auto_play` ＋ `write_save` 推進到指定節點再從網頁「繼續一輪」讀取。
- 驗收時自己跑一場 `trpg battle ... --log-json` ＋ `replay` 確認。
- PM 對話很長時用量高；一個大階段結束就更新本檔並交接。

---

## 原 3.1、3.1.2、3.3（2026-10-18～10-30 累積；DOC-B M2 歸檔）

> 3.1 的方向已寫進 `docs/專案計畫.md` 第 14 節（v0.2.1）；3.1.2 的做法已寫進 `CLAUDE.md` 守則 11 與交接文件 §6.2；3.3 的清單在平衡階段（BAL-1～19g，`docs/phases/PhaseBAL計畫.md`）逐列核對後，未做的搬進 `docs/開發PM交接.md` 3.1 第 4 點「來自原 3.3」，處置表在 `docs/phases/PhaseDOC-B報告.md`。

### 3.1 使用者已同意的方向（2026-10-18，已寫入 `docs/專案計畫.md` v0.2.1 第 14 節）

**先確定遊戲能 work，平衡延後。** 順序：

| 階段 | 內容 | 檢查點 |
|---|---|---|
| ~~Phase 2D｜補模板 A~~ ✅ | `shield`、`damage_reduction`、`taunt`、`buff_attr`、`haste`、`heal_over_time`、`cleanse`；`fear`、`silence`、`blind`、`mark` 等狀態；技能可施加 `defending`。解鎖坦克、輔助、治療、術士 | — |
| ~~Phase 2E｜補模板 B~~ ✅ | 事件觸發系統（`on_hit`、`on_damaged`、`on_turn_start`……）→ 被動、反應、姿態、陷阱骨架；層數累積／消耗（`builder_finisher`）；替隊友擋攻擊的反應技。補上 Phase 2 驗收中標 ⚠️ 的兩條（技能層級觸發、觸發深度上限） | — |
| **Phase 3｜網頁 ＋ roguelite** | （原 Phase 4，**已與 Phase 3 調換**）FastAPI ＋ React／PixiJS、roguelite 循環；升級選項先用隨機組合器；隊友指示只做快捷按鈕；美術先用程式繪製（3-16） | 🎮 戰鬥手感檢查 |
| **Phase 4｜LLM 技能生成** | （原 Phase 3）LLM 技能生成、LLM 戰術指揮官、LLM 命名、文字隊友指令，接進網頁。開始前要定 #5 的世界觀 | 🎯 好玩檢查點 |
| 平衡 | 見 3.3 | — |

- 使用者選這個順序的理由：先有畫面才能判斷好不好玩；試玩時 build 種類要齊全（所以模板 A、B 在網頁之前）。
- 召喚物範圍最大，放在更後面。
- Phase 3 已完成到 3-17（見第 2 節），下一個檢查點是使用者的 🎮 戰鬥手感檢查。

### 3.1.2 加快階段速度（2E 的經驗，寫下一份規格時照做）

- 2E 三段實際：2E-1 48 分、2E-2 56 分、2E-3 100 分（規格估 30 分）。分析 agent 紀錄：約一半時間在 **等全量 pytest／`check.py`**（單次 6–10 分鐘，每段跑 2–3 次），另一半是模型思考與撰寫；2E-3 多出的約 30 分鐘是全量 completion（14 分）＋ matrix（約 15 分）。
- 規格的「工作環境」一節要寫明：**開發中只跑相關測試檔；全量 `check.py` 只在子階段最後跑一次**（commit 前只跑 ruff、mypy 與相關測試）。
- 大型模擬（completion、matrix）**不要放在實作子階段裡**：獨立成一個小收尾段，或由 PM 驗收時自己在背景跑。
- `pytest-xdist` 已引入（2026-10-19），全量測試平行跑；工作環境改到使用者電腦（見 6.1）。
- 一段的範圍以「一套規則 ＋ 其測試」為上限；像 2E-2 一次三套規則（反應、攔截、姿態）就會超時。

### 3.3 延後到平衡階段的累積待辦

- **B-3W（2026-10-29，玩法 PM #70）**：全指定類別的玩家一季約只能練滿 2～3 招（不指定約 5 招）；平衡階段模擬兩種玩家（全指定／全不指定）後，再決定靈感點總量。
- **B-3W-2（2026-10-29，玩法 PM）**：補「輔助 → 被動」轉型（例：回合開始時，1 格內的友方回復少量生命）；目前輔助技只能轉防守姿態與召喚。
- **B-3W-3（2026-10-29，3W-2b）**：姿態等級表（預算 15／17／19／22／28、傷害 +10～30%）、維持費換算（每點 2 耐力或 1 法力、折抵 200‰）、護盾反傷 2、結束回復 3、先機標記實測 2～3 回合，都是初值；轉型後的姿態一律扣法力（即使原招是武器技）待確認。
- **B-3W-4（2026-10-30，玩法 PM 6fc1e9b0）**：升階時狀態／表面持續回合上限 10，3 階淬毒、毒反擊到頂後偏弱；施加狀態沒有層數參數，平衡階段再決定是否加層數。
- **B-3W-5（2026-10-30，3W-5b 上限）**：完整技能 +150‰ 上限下仍有約 50 招超過（骰子一階就超、沒有更細旋鈕）：火球 +166‰；修正型被動幅度階梯粗，攻擊精通、懾人凝視、疾足到 +500‰。平衡階段考慮把幅度階梯加細。玩法 PM 方向（2026-10-30）：大幅超過的（如 +500‰）寧可停在 +120‰ 以下最接近的一階，不要超過；火球 +166‰ 這種小幅超過照現在接受。
- **B-3W-6（2026-10-30，3W-8 模擬；玩法 PM 標優先）**：**優先** ① 一輪約 4 點靈感、平均閃 2.9 次，很少看到第 3 次大變化（閃現主要爽點）；「每打贏一場 1 點」是已寫入數字，要改須使用者決定，玩法 PM 平衡階段整理選項。**優先** ② 「修正」「觸發」兩類在所有策略 0 次被選，查是 AI 偏好還是出現太少。其他：全指定 95% 集中範圍／連段／元素；一季尺度模擬未做；AI 不溶掉／傳承；勝率約 30% 多死在 Boss。

> **使用者決定（2026-10-23）**：「幫我在後面加個平衡phase 這些都先往後延吧 因為都會陸續改 感覺現在平衡沒意義」——平衡工作全部移到獨立的平衡階段（位置照舊：Phase 4 之後、Phase 5 之前，`docs/專案計畫.md` 第 14 節）。之後各段驗收**確認功能正確、重播一致、沒有明顯壞掉**（某招完全無效、某種召喚物必死）；**數值仍要判斷並記錄**（使用者補充：「數值可能還是要判斷 然後記錄起來可能會很強或很弱 但是在加新功能 新開發 還是給予建議 但是不做開發平痕」）——從報告、少量測試或玩法 PM 的判斷看出可能偏強或偏弱時，寫進下表並附**建議值與來源**；不派平衡段、不跑大型模擬、不為數值反覆調整，新功能照設計初值實作。

**平衡階段清單（Phase 3 後期新增，2026-10-23 整理）**

| # | 項目 | 來源 | 內容與門檻 |
|---|---|---|---|
| B1 | 普攻流對照 | 3-32a～d（`Phase3計畫.md` 35.4a） | AI 有 ≥ 2 敵可打時範圍技選用率 40% → ≥ 70%；改完背景跑 200 場：Boss 擊殺輪數比 ≥ 0.90、範圍清場輪數比 ≥ 1.15；仍不達標才動基礎普攻（不再動連擊、分裂、精通）。`scripts/sim_attack_flow.py --diagnose` |
| B2 | 召喚流對照（原 3-33g） | 36 節段表 | 長戰單體、範圍戰、Boss 戰三情境；長戰輸出不超過技能流與普攻流；含灌注（1 AP、AI 權重 700）、操控半徑與自動切換門檻、群召／精英反推的預算點數、精英 +50% 與全身上限、數量型進化與上限 1 的互動、召喚物倒下爆炸／治療 1d8 |
| B3 | 召喚物存活門檻 | 36.4b、36.8a（06 6.29.7） | 一般戰鬥被打倒 ≤ 50% 且 ≥ 10%（±10 個百分點）、Boss 戰被打倒 ≤ 50%；戰意圖騰、殘影係數未模擬 |
| B4 | 召喚持續輪數與預算 | 36.7b、玩法 PM | 特性計入預算後多數召喚縮成 2 輪，看是否放寬召喚預算；拉扯／高台計價初值各每輪 1000‰；召喚物特性係數；17 種召喚技只有 9 種三支進化齊全（骷髏、傀儡、雷靈貼上限） |
| B5 | 召喚物 AI | 3-33e2b #2 | **3H 後 AI 灌注頻率大降**（dev_summoner／bandit_lair 40 場只有 2 場灌注，3H 前前 8 場內就有）；AI 對護盾、拉扯、高台、纏住估值 0；高台圖騰包勝率 60% → 檢查 AI 是否把遠程角色帶上高台 |
| B6 | 刃刻降階 | 3-31（34.1） | 刃刻 2 階，看能否降回 1 階；`per_turn_limit_uses: 8`、`on_hit_rune_permille: 270` |
| B7 | Boss 公平性 | 06 6.29.7、8.25 | Boss 對召喚物 ×2、擋路加分 60；普攻流不能成為打 Boss 唯一解；Boss 戰勝率（無召喚對照包 0–12%）與輪數 6–10 |
| B8 | 戰場變奏 | 33.1a、33.2a | 變奏加價 10%、射程每格 5%、AI `variant_position_bonus` 3、組合器變奏機率、進化模板曝光 |
| B9 | 法力續航 | 3-32d #3 | 目前沒有法力自動回復；技能流 Boss 戰 19% 回合缺法力，要加時先定「對所有單位或只對玩家方」 |
| B10 | 普攻屬性倍率 | 玩法決定 #45（2026-10-23） | 普攻的屬性倍率偏弱（例：力量 × 0.3），3H-1 後重量 |
| B11 | 法力、耐力係數 | #45、`Phase3H計畫.md` 3H-2 | 07 7.2 的資源上限係數（武器大類基礎、×2）與法力換耐力的預算換算；「每場法力回滿」（待使用者決定）要連耐力一起考慮 |
| B12 | 心智三分後的流派 | #45、3H-1 | 約 31 招改看意志後，召喚流、暗影流重量（勝率、輸出、資源不足回合） |
| B13 | 屬性常駐數值係數 | #45、`Phase3H計畫.md` 3H-1 第 6 點 | 每 4 點一階的門檻與每階數值，特別是智力「表面與持續區域 +1 回合」 |
| B14 | 敵我同一套資源公式 | 3H-2 待決 #4、玩法 PM 2026-10-23 | 原則上要（公平，朋友的影子也同規則），但會動敵方平衡：敵人、隊友、召喚物的法力／耐力改用和主角相同的上限公式，平衡階段一起做 |
| B15 | 法力回復 | 3H-2 待決 #1、3H-5 | 耐力回復已做（每回合 +5、戰後回滿，使用者選 A）；之後耐力不足幾乎消失，**短缺都是法力**（近戰長戰與 Boss 約 24%、弓手 Boss 17%、召喚師 Boss 38%）；**使用者決定法力維持只在營火回滿**（2026-10-24 原話：「法力維持只在營火回滿」）→ 法力短缺留給平衡階段用技能費用、上限係數處理，不改回復規則 |
| B16 | 3I-1 新武器傷害骰 | `Phase3I計畫.md` 4.1 | 拳套 1d8（雙手＋反擊）、鐮刀 1d10（雙手＋收割）、鞭 1d6（單手、射程 2＋纏繞）為初值；白板 700 場：拳 61%／鐮 58%／鞭 66%（單手劍 58%），鞭 DPR 最低但生存最高。依真實配點 build 再看 |
| B17 | 圓盾格擋強化 | `Phase3I計畫.md` 4.2 | 縮放值 × 5‰、最多 +10%（格擋 50% → 最高 60%），初值未模擬 |
| B18 | 3I-4 雙匕首偏強 | `Phase3I-4報告.md`、玩法 PM 2026-10-24 | 勝率 67.5%、DPR 7.22（單手劍 +35%）。平衡時先試「背刺只加成第一下」，不夠再降 1d3×2 |
| B19 | 3I-4 霰彈槍偏弱 | 同上 | 勝率 31.9%，主因 AI 不貼近；平衡時先修 AI 站位（往 1～2 格靠，效用 AI 位置價值），再重量，修好前不調傷害 |
| B20 | 3-50 代價換強度的 AI 與組合器初值 | `Phase3-50報告.md`、玩法 PM 2026-10-24 | 自暈 AI 條件（HP 50%、6 格內）、透支條件（波及 ≥ 2）、組合器產生透支機率 40‰；未模擬 |
| B21 | 魔劍斬改武器技 | `Phase3I-3報告.md`、玩法 PM 2026-10-24 | 近戰武器技＋智力，耐力 10、倍率 2.4，剛過預算下限的初值，未模擬 |
| B22 | 3K-1 物品產生器初值 | `Phase3K-1報告.md`、玩法 PM 2026-10-24 | 小部位（副手、手、腳、戒指）詞條預算 4～9 點，稀有／史詩常只 1 條，手腳 build 詞條出現率 17%；「傷害 +2%＝3 點」；條件成立率 0.6／0.35／0.2；代價型單位價；充能與代價型詞條第一版不產生（裝備段再開）；等級 9、10 優良主手產生不出來（Phase 5 掉落前處理） |
| B23 | 3I-5 親和出現率 | `Phase3I-5報告.md`、玩法 PM 2026-10-24 | 組合器只替換既有常見條件，實際出現率低於 400‰；等 Phase 4 LLM 依主角武器加親和條件後一起看。裝填類招牌技（讀取／操作彈匣的新原語）待需求出現再評估 |
| B24 | 3K-2b 防具基礎防禦與基礎份額 | `Phase3K-2b報告.md`、玩法 PM 2026-10-24 | 布袍 1、外套 2、皮甲 3、鎖甲 5、板甲 7，頭手腳 1，每級 3 點；基礎份額照 8.22 比例換算（3K-2c）的係數 |
| B25 | 3-54a 風的初值 | `Phase3-54a報告.md`、玩法 PM 2026-10-24 | 吹送每格 1 點、風壓撞擊每顆撞擊骰 +0.5 點、擴散不計點、組合器吹送機率 80‰；未模擬 |

- **召喚物（玩法 PM 2026-10-23）**：特性計入預算後多數召喚縮成 2 輪，召喚專精補回，平衡階段看是否放寬召喚預算；高台圖騰包勝率 60% 偏低 → 檢查 AI 是否把遠程角色帶上高台（AI 問題）；AI 對護盾／拉扯／高台／纏住的估值（3-33g）。
- **普攻流（3-32d，玩法 PM 2026-10-22）**：AI 有 ≥ 2 敵可打時範圍技選用率 40% → 目標 ≥ 70%；改完背景跑 200 場（`scripts/sim_attack_flow.py --diagnose`），門檻 Boss 擊殺輪數比 ≥ 0.90、範圍清場輪數比 ≥ 1.15；仍不達標才動基礎普攻，不再動連擊、分裂、精通。
- 勝率：大多數地圖我方 70–95%（2C-4 後 `lava_crossing` 75%、`ruined_fort` 70%），`oil_depot` 偏難（保留）；目標 35–65%、一般遭遇 4–6 輪。
- build 矩陣（`Phase2C-3報告.md`）：`build_storm` 8 種類型中 7 種前段；`build_tank` 曾 0 種（原因是 **沒有保護型模板**，補模板 A 後重測）；2C-4 改 AI 後標準 2 不通過的變成 `build_assassin`。
- AI 很少用控場、位移、場地技能；控制回合每場接近 0。所有 AI 權重、狀態價值、指令加成（集火 ×1.5 的算法等）未經模擬。
- `skill_fire_bolt` 的 DPR 超過同階 P95 × 1.2。
- 結構型原語點數偏低（2B-3 #3）；技能報表在平地 1 對 3，控場、位移、光環骨架的 DPR 偏低，可能要另設情境。
- 冰面 DEX DC12 滑倒對 AI 的影響未評估；敵方集火時 `bridge_chasm` 我方勝率反而上升，原因未查。
- 代價折抵總上限已定為 +500‰；組合器權重已搬到 `content/skill_composer.yaml`。
- **2D 後新增**：`build_tank` 改版（嘲諷＋護盾、`guard` 行為模式）後前段類型 2 → 0、英雄 DPR 5–8 → 1–2.5（疑似 `guard` 的 damage 權重 3 讓坦克太被動）；`build_healer` 也 0 次前段。保護矩陣有數字但沒轉成勝率——要決定保護型 build 的評估指標（標準 2 是否改看保護矩陣）或調 AI／數值。
- **2E-2 後新增**：`build_guardian`（攔截＋姿態）小樣本 8 張地圖 4 張第 1，可能偏強；姿態狀態 11 點只合階級 1，高階由組合器加護盾湊預算；反應技在 fuzz 中很少觸發（7/70）。
- **2E-3 後新增**：build 矩陣（12 個 build、2400 場、異常 0）6.8 標準 1 通過、標準 2 不通過：`build_tank`、`build_striker` 沒有任何前段類型；`build_trapper` 的 AI 陷阱擺位差（常放角落）。
- **2H 後新增**：新數值（`frozen` 點數 8、`self_status` 折抵 40‰／點、AI 自身狀態成本、組合器雙屬性 250‰、專精 300‰）都未經模擬；`skill_arcane_blade` 裝在智力 10 的 build_push。2H 驗收時 matrix 標準結果與 2G 相同（標準 1 `build_storm`；標準 2 `build_tank`、`build_assassin`、`build_healer`）。
- **2G 驗收時（PM 本機跑）**：completion 全量 1800 場異常 0（90 秒）；build 矩陣 2400 場異常 0、平手 1（103 秒）。6.8 標準 1 不通過（`build_storm` 8 類型全前段）；標準 2 不通過：`build_tank`、`build_assassin`、`build_healer`。`build_tank` 英雄 DPR 約 1–2.5。
- **2G-2 後新增**：12 個示範技能的數值只為通過預算（致命破綻、天賜好運靠冷卻湊預算；天賜好運護盾 1d4 太小）；AI 把「築高台」當攻擊技、升高敵人腳下的格子；敵方單位沒有被動、反應、姿態。
- **2G-1 後新增**：`build_tank` 主動技能 6 個（加了破甲擊、碎甲重擊）但法力只有 20。
- 控制回合統計（`CONTROL_STATUSES`）只算 stun、root、slow，未含 feared、silenced、blinded、taunted。
- **3C／3D／3F 後新增（2026-10-20）**：
  - matrix（22 build × 10 地圖、2200 場、異常 0）：偏強 `build_storm`（92.5%）、`build_detonator`（89.4%）、`build_fire`（90.0%）；偏弱 `build_assassin`（56.9%）、`build_winged`、`build_gambler`、`build_tank`；前段 0 次的 7 個 build（`Phase3C-6b報告.md`）。撞擊流（push、wallburn）不如預期，先查 AI 推擊評估。建議合併 wallburn→push、detonator→warlock、tank→guardian（未決定）。
  - roguelite：`trpg run auto` 10 種子只贏 3 輪（戰鬥間不回復累積）；Boss 地圖標準陣容勝率 30%、平均 7.9 輪；開局屬性六項 10 ＋ 4 點比 build 英雄弱。等 3-6 試玩再決定（多營火、調 Boss、調開局）。
  - 所有 3C／3D／3F 新原語、觸發、條件、複合技能的預算係數與 AI 權重都是初值，未經模擬（各計畫檔 0 節標「平衡階段」的項目）。
  - 背刺：被近戰攻擊後轉身後，刺殺 build 每場約 1.8 次背刺；AI 權重 `backstab` 4、`back_exposed` 3。
  - 召喚物很快被打倒；AI 隊友會走進我方火牆留下的火；定時炸彈不分敵我會炸到隊友。
  - 純數值的修正型被動「打法差異」只有 0–1 分（`Phase3C計畫.md` 0.14），Phase 4 生成時要避免大量產生。
- `skill_dread_gaze`、`skill_hush` 貼著預算下限 70.4%；`skill_hex_bolt` 的 `marked` 只有 1 回合；AI 會對已被標記的目標重複施放咒印飛彈。

- **3-5～3-17 後新增（2026-10-22）**：
  - 一輪：AI 代打 10 種子 2 勝（3-7 後）；Boss 戰中主角不動時頭目與弓手守在原地 → 30 輪平手（AI 是否要主動進攻）；等級 HP 加成向下取整（基礎 40 每級 +2）；玩家配體質的強度未測（AI 不配體質）。
  - 3-7：流血／中毒可被體質抵抗後依賴它們的 build 變弱，matrix 未重跑。
  - 3-11：暫時障礙持續時間係數（`content/skill_budget.yaml` 的 `obstacle_duration_permille`）未經模擬；冰牆、荊棘牆為過預算下限附帶表面；煙霧彈 5 回合與煙霧箭相近。

---

## 原 3.1（2026-11-06～11-07 進度流水，11-07 收尾時從 `docs/開發PM交接.md` 搬來）

### 原 3.1 Mac mini 接手（2026-11-06）

> 3.1 最新；3.2、3.3 是前兩次交接，只為了查脈絡。更早的歷任小節（2026-10-22～10-31）在 `docs/archive/交接歷史-開發PM.md`。

> PM id（2026-11-06 第三組）：專案 PM `local_e92f686b-c8bd-4b4d-9e22-f0b23d3dc696`、玩法 PM `local_156847a7-c020-45da-84a7-8ced1469e490`、美術 PM `local_42bc346b-cc13-48da-b901-bb0d0b235c64`。共用筆記在 `~/Library/Application Support/Claude/side-session-notes/<專案 PM id>/`（Windows 的 `C:\...` 筆記這台拿不到）。

1. **環境換成 macOS（Mac mini arm64，16 GB，zsh）**：`uv` 在 `~/.local/bin`（每個 shell 先 `export PATH="$HOME/.local/bin:$PATH"`）；Node 26 沒有 corepack，前端一律 `pnpm -C client …`（`pnpm_command()` 在 `src/trpg/cli/frontend.py`）；不跑 brew、不跑 `pnpm install`（已裝好）。預覽埠不用 8000／8001。本機 LLM：LM Studio（MLX）＋ `gemma-4-12b-it` 在 `127.0.0.1:1234`，設定 `config/llm.local.toml`（gitignored，用 `TRPG_LLM_CONFIG=config/llm.local.toml`）；**模型載著時不要跑全量 pytest**（記憶體只剩約 30%）。
2. **三個 Windows worktree 分支（6T-1d、UI-E3b、6R-2）等使用者從 Windows push**（2026-11-06 使用者：「Windows我沒打開 我回家再推上去」；分支名見 3.2 第 3 點）。在那之前：不派 agent 做這三段、**不動會衝突的檔**（6T-1d：client 郵寄與按鈕滑過；UI-E3b：client 遇敵卡、傭兵 `skill_ids` 伺服器欄位；6R-2：`races.yaml`、建角、LLM 指令）。push 上來後各自 `git merge main`（MAC-1 改了 CLAUDE.md、tests/llm、vitest 快照，衝突由開發 PM 解），再接著做。`PhaseUI-E3b報告.md`、`Phase6R-2報告.md` 目前不在 main。
3. **使用者 2026-11-06 的指示**：「在 Mac 上測試」「我 llm 都沒搞」「專案太大太久 整理 以防變屎山代碼 .md 也是」。對應的事：
   - Mac 全量驗證（專案 PM 的唯讀 agent，main `4a1bd1e7`）：pytest 14212 過、mypy 38 錯、vitest 2 個雜湊快照失敗（arm64 浮點）、build 過、serve 無 LLM 正常降級。
   - **MAC-1 Mac 相容修正 ✅**（`ff0ac6b6`～`9964b434`，報告 `docs/phases/PhaseMAC-1報告.md`）：corepack 缺席改用 pnpm／npx、Windows 路徑全改中性、mypy 0 錯、兩個雜湊快照改成數字固定 6 位小數（Windows x64 已驗過，2026-11-06 使用者跑 2 files／11 tests passed）、CLAUDE.md 與部署說明補 Mac。
   - **MAC-2 LM Studio MLX 相容 ✅**（`c6b43e26`、`0898b086`，報告 `docs/phases/PhaseMAC-2報告.md`；原派工內容：）MLX 不支援 schema `oneOf`，`auto` 退到 `guided_json` 後 LM Studio 靜默忽略約束 → `propose` 100% 退回組合器。做法：`oneof_as_anyof` 設定（預設 true）遞迴改寫、退回時 warning、`llm ping` 印接受的寫法；驗收用真模型跑 `tests/llm -m llm` 與 `propose -n 10`。合併後 PM 自己把 LM Studio 設定範例貼進 `config/llm.toml` 與 `docs/部署說明.md`。
   - **整理提案**：`docs/phases/整理提案-程式.md`（第 1 節文件、第 2 節程式；使用者的 6 題在 1.8 與 2.6 節）、玩法 PM 的 `docs/整理提案-玩法.md`。**使用者決定前不刪、不搬、不大改。** 決定後第 1 批（文件 D1、D2、A1～A3、M7；程式 I1～I8）各派 agent。
4. **2026-11-07 使用者：「所有人先停下 先讓q板完成再開始工作 把所有需要q版的都完成 腳色 動畫 怪物 npc 等 全部」** → 開發名額（≤ 3）全給 Q 版，非 Q 版全部暫停。**暫停中**（恢復時照這個順序）：RT-6b（WIP 在 `origin/dev/rt6b` `3fdd8ec7`，剩項見 `docs/phases/PhaseRT-6報告.md`「RT-6b」節；先修 `rt6.test.ts` 寬視窗那條預期）、外觀選單選項改頭像小圖（美術 PM 11-07：QK-9 之後另開一小段，樣張 `外觀變化方案.md` 第 4 節）、#134 靶場開局（QK-2 的靶場 ②③ 恢復待它，專案 PM 11-07 排在 QK-9 之後）、HID-1（#144 隱蔽敵人只藏資訊，`docs/design/05-戰鬥.md` 5.1.2 末段 6 條）、R1d（拆 `skillgen/proposal.py`＋`preview._outcome` 查表）、I8（client `dev/` 移出正式 bundle）、R1e（拆 `BattleRenderer.ts`，QK 後）、R5／R6、propose 第 9 題 collision、戰鬥主角卡四角飾件舊 FAIL。**2026-11-07 使用者：「跑中都跑完後 不要開新的 然後確保都有 push 我要在windows上測試」** → TR-1、R1e 合併後全部暫停。**暫停中（恢復時先做）**：HID-1b（`docs/art/HID-1檢查.md`：「？」與 HUD 畫在霧上、HP 條與「？」畫在攻擊紅框上；玩法 PM：預告 `TelegraphChangeOut` 對隱蔽單位不得帶出 HP／護盾／狀態——目前 `before/after/amount/text` 可能洩漏狀態到期，要查；四角飾件舊 FAIL（`runCase`，主角卡左下）；補拍 4 張）→ 外觀選單小圖＋郵寄寄件人頭像 → collision 第 9 題 → R5／R6。**開發入口 `dev-teleport`**（QK-9b）：只在開發模式＋`TRPG_DEV_ROUTES=1`，直接改角色存檔、不寫世界日誌，該角色之後的世界日誌重播會對不上——專案 PM 11-07 已轉知使用者、接受。**QK 結案後恢復順序**（專案 PM 同意，開發同時 3 個、平行者不改同一批檔案）：RT-6b → HID-1 → #134 靶場 → R1d → I8 → 外觀選單小圖＋郵寄寄件人 Q 版頭像（美術 PM 11-07 併一小段）→ collision 第 9 題 → R1e、R5／R6。**Q 版**：規格 `docs/art/QK移植需求.md`（第 2 版＋更正版 `fcacaa70`，使用者：「不 照建議」）；**QK 小修待排**：併 QK-9 順手：拿弓／弩／火槍的自身與地面施放維持舊的上下位移、不借法杖組；火槍與弩朝南正面放大約 1.3 倍（不用拍圖）；徽章避臉頭部圓檢查；頭目命中對齊；畫廊弓手。QK-4b（**等美術修樣張**：熊、野豬、傀儡倒下、鳥待機、頭目改 huge 約 1.6 倍＝腳底在自己格中心、可蓋隔壁、HUD 跟著上移；另：異形普攻沒有技能特效時走普攻武器特效＋火塵蝠普攻截圖；碎晶之主待機首尾接上；頭目對照 gif 拆開各自色盤＋補錄待機 16 格與各階段；灰燼之心狀態列要在頭目輪廓上方；畫廊補人形敵人疊精英詞綴；見 `docs/art/QK-4檢查.md`）；QK-6 補拍（同範本 ×2 外觀不同、同種子重開外觀相同）併 QK-5；美術修樣張 4 處（兔尾、狐狼耳、鬍渣側面、方臉心形臉背面）對照圖到了排 QK-8 或下一段；QK-5 另含：DOLL_SCALE ×1.15、背面攻擊前傾、開場 reach、龍裔尾巴穿地、異形命中對齊出手格（skillSequence）、放大後再看龍巨人與詞綴位置。**QK-8 追加（玩法 #145，`docs/design/18-雲嶺內容.md` 18.5.1）**：① NPC 頭像 schema 加「手持物」「圍裙」欄位（郵差帽徽、郵袋同理，清單見 18.5.1 表）② 前端畫 douli（斷崖幫雲嶺盜賊配色、疤面頭像），原列「不實作」改實作 ③ 霧鎖真人統一用頭目版（美術 PM 補需求）；美術 PM 會補 QK-1～7 沒涵蓋的需求。
   **之前的待排**：**LLM-1 系列結案**（LLM-1／1A／1B／1C，報告 `docs/phases/PhaseLLM-1報告.md`；提議 prompt 已回到改前結構，E4B 改前基準 5 次平均 6.8、LLM-1C 5.5，差距在抽樣誤差內，專案 PM 11-06 同意不再追）；待排 0.25 段：propose 第 9 題（common／collision）每次因 `keyword.required` 退回，看 collision 的 ways 寫法，等玩法 PM 有空一起看。6F-20 ✅（格子碰撞 6F-15～20 結案）。**順手項**（下一個碰到的前端段做，不用拍圖）：全部英文「Boss」介面文字改「頭目」（佈告欄「賽季 Boss」、預覽文字、開發選單「5 場戰鬥加 Boss」、開發標題列「Boss 戰（開發）」；識別字不動）。**主城 HUD 下一段**：800 寬右側任務鈕壓房子、技能說明卡蓋「WASD 走一格」。其餘同 3.2 第 4 點，在 Mac 下：可直接做 dark_forest 改圖、朝南三角形、RT-5 順手兩項、6R-1 補拍、AU-3／RT-2 補／UI-E1／last_played；6T-1d ✅、UI-E3b ✅、6R-2 進行中（三個分支 11-06 已從 Windows push，在 Mac 上 merge main 後續做）；等 Q 版 6F-5、QK；等 LLM 效能決定（生成 10 token/s、提示 128 token/s）的多講一點接線與 12B 基準。
   - **來自原 3.3（平衡階段 BAL-1～19g 做完後仍沒做的，DOC-B 2026-11-06 逐列核對；處置表在 `docs/phases/PhaseDOC-B報告.md`）**：
     - 規則類（回使用者）：B-3W 靈感總量——原型每勝 2 點已定（BAL-1b），一季尺度「全指定／全不指定」兩種玩家的模擬未做，大世界再量；B-3W-2「輔助 → 被動」轉型未補。
     - 未單獨量測的初值：B-3W-3 姿態等級表與維持費換算、轉型後姿態是否一律扣法力；B6 刃刻降階；B8 戰場變奏加價與 AI 加分；B10 普攻屬性倍率；B13 屬性常駐係數（每 4 點一階）；B17 圓盾格擋強化；B21 魔劍斬改武器技；B22 物品產生器初值（Phase 5 掉落後未重量）；B23 親和出現率；B24 防具基礎防禦與基礎份額；B25 風（吹送、風壓）；3-11 暫時障礙持續係數；2H 數值（`frozen` 8、`self_status` 40‰、雙屬性 250‰、專精 300‰）；結構型原語點數（2B-3）。
     - AI：控場／位移／場地技使用率（控制回合接近 0）；trapper 陷阱擺位；AI 把「築高台」當攻擊技；AI 隊友走進己方火牆、定時炸彈炸到隊友；冰面滑倒對 AI 的影響；`bridge_chasm` 敵方集火時我方勝率反升的原因。
     - 小項：`CONTROL_STATUSES` 只算 stun／root／slow（未含 feared、silenced、blinded、taunted）；B18 雙匕首 123.9%（BAL-9 對照未改，未見玩法 PM 結案句）；模擬 build 合併建議（wallburn→push、detonator→warlock、tank→guardian）未決；修正型被動「打法差異」低、LLM 生成避免大量產生（4-L 未見處理）；玩家配體質的強度未測。
5. **流程不變**（§6）；Windows 專屬的 §6.1、`py` 空殼、Git Bash 說明已過時，整理提案 M3 決定後重寫。


