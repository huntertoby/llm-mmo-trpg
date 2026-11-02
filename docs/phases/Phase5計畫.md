# Phase 5 計畫：賽季大世界（第一季）

> 2026-11-02 開發 PM 規劃（規劃助手起草）。使用者授權：「我要去睡覺了 試玩可以到時候再玩 你們做完就直接開始Phase 5吧 有需要我決定得先幫我決定 記得做了那些決定就好了」。
> 順序照玩法 PM 建議：**① 地點地圖與城鎮 ② 事件與故事線 ③ 組隊、影子與傭兵 ④ 經濟 ⑤ Discord 機器人與帳號 ⑥ 賽季與 Boss**。
> `docs/專案計畫.md` 第 14 節原本的「Phase 5｜文字創意動作與裝備」是舊排法，已在該節標為「移到之後的階段」並保留原文；本檔的 Phase 5 指大世界。
> 本檔先寫總覽與 **5A-1** 的詳細規格（第 5 節）；之後各段的規格在前一段驗收後補上（第 6 節起）。

---

## 0. 範圍與來源

### 0.1 只根據已寫入 `docs/design/` 的決定

| 主題 | 設計文件 | 決定編號 |
|---|---|---|
| 大世界總體（主城、小鎮、精簡魔獸世界式運作） | 09 9.6、9.6.1 | #29、#94、#95 |
| 地點圖（每區 15～25 點、點了就走、路上遇敵、隱藏地點、建議等級、地點種類） | 09 9.6.2 | #29 |
| 任務結構（主線、區域任務鏈、隱藏任務、懸賞、世界事件、Boss 封印）、人少時世界不空 | 09 9.6.3 | #29、#87 |
| 情境判定（模板、`<player_input>`、LLM 提議 ±2、d20、三段結果、用心清單 +2、種族 +1） | 09 9.6.4 | #31、#45、#85、#89 |
| 碎界五區、第一個做雲嶺 | 09 9.6.5 | #42 |
| 敵人家族、中立族群、變體與精英詞綴、混族、遠程上限、營地混精英 | 09 9.6.6 | #82 |
| 城鎮與大世界體驗 16 條（酒館、休息、聊天只換資訊、好感度、事件骨架＋線頭、旁白、記憶、移動／補給／探索、朋友足跡與影子、共享變化、日夜天氣） | 09 9.6.7 | #85、#97 |
| Boss 戰（階段、解謎、只准傭兵、影子上限、通關評分榜） | 09 9.6.8 | #86、#87 |
| 隊伍 3 人、死亡與失敗、新手引導、一帳號 2～3 角色、早上 6 點刷新、一天 30 分鐘 | 09 9.6.9 | #97～#100 |
| 賽季獎金、影子 AI、世界事件進度、天氣、留言、誓約、說書風格、種族重選 | 09 9.6.10 | #101～#108 |
| 第一季 14 天節奏、雲嶺＋灰燼荒原、主線 3 章、上限、影子循環賽、bug 處理、季末重置 | 09 9.7 | #32、#90、#91 |
| 區域地圖池（每區 7 種）、各區天氣傾向 | 05 5.1「區域地圖池」 | #43 |
| 技能取得（創角、任務、劇情、機遇、許願池）、配額、技能庫與換裝 | 07 7.6 | #30、#38、#69、#88 |
| 種族與出身、主城重選 | 07 7.7 | #61、#108 |
| 練等（經驗來源、等級範圍、不縮放、退路、到頂換算） | 07 7.8 | #81 |
| 裝備取得、材料、貨幣、交易、道具 | 08 8.13～8.17、8.20 | #33、#37、#70 |
| 大世界經濟、物品等級、材料多樣性 M1～M7 | 08 8.26 | #94、#96 |
| 誓約 | 06 6.26 | #27、#106 |
| 大世界帳號與主機（Discord Bot 發帳密、一 Discord ID 一帳號、使用者電腦、Tunnel、模型降級、6 點刷新、一天 30 分鐘） | `docs/專案計畫.md` 3.1 | 使用者 2026-11-02 |
| 近期營運目標（Discord 5～10 人、賽季、首殺現金） | `docs/專案計畫.md` 1.2 | 使用者 2026-10-22 |
| **雲嶺內容**（山中修士 10 種＋精英＋Boss 霧鎖真人、中立族群、材料 8 種、地點圖 18 點、事件骨架 18 個、NPC 人設卡 8 張、誓約模板 15 種、新手鏈／主線第 1 章／區域任務鏈／懸賞） | 18 全部 | **#111（玩法 PM 代決、待使用者確認）** |

> **18 號文件的地位**：`docs/design/18-雲嶺內容.md` 是玩法 PM 依使用者授權寫的 **內容草稿（代決、待使用者確認）**，數值都是初值。本計畫照它排內容，但：① 規則以 05～09 為準，18 只填內容；② 使用者若改了 18 的內容，只需改 `content/` 資料，不改程式（守則 4）；③ 每段完成報告要列出「用了 18 的哪些內容」，方便使用者確認時對照。

### 0.2 設計文件沒寫、需要代決的事

規則類交玩法 PM 代決（使用者已授權，標「代決」）；純實作或原型數值由開發 PM 照最保守的預設定（標「開發 PM 定」），寫進該段規格與完成報告。代決 **不得推翻或放寬** 已寫入的決定。

| # | 問題 | 類別 | 誰定 | 最保守的暫用做法（代決前） | 影響段 |
|---|---|---|---|---|---|
| Q1 | 地點之間的 **連線**（哪些地點相鄰）——18.3 只列地點、沒有連線 | 內容／規則 | 玩法 PM 代決 | 5A-1 用第 5.4 節的連線初稿（依建議等級由低到高、小鎮為起點、隱藏地點不當唯一通路） | 5A-1 |
| Q2 | 每一步的 **遇敵機率**、「趕路」花多少補給降多少（9.6.7 #9）、補給上限與紮營用量（#11） | 數值 | 開發 PM 定初值 → 模擬定（9.6.10「數值類」） | 依地點建議等級查表；初值寫在 content，不寫死 | 5A-2 |
| Q3 | 隱藏地點「靠近時感知判定」的 DC 與「靠近」的定義（相鄰？） | 規則 | 玩法 PM 代決 | 相鄰地點才判定；DC 先放在 content，初值 12 | 5A-2、5B-2 |
| Q4 | 移動與遇敵的 **亂數衍生**（種子、角色、步數） | 實作 | 開發 PM 定 | 見第 2.4 節 | 5A-2 |
| Q5 | 遭遇表：地點 → 敵人陣容（家族、數量依 3 人隊伍）、營地混精英機率（9.6.6）、每場遠程上限（9.6.6；18.2.1 寫雲嶺 2 名） | 數值 | 開發 PM 定初值 → 模擬定 | 遠程上限照 18 的 2；精英機率初值 0‰～100‰ 放 content | 5A-3 |
| Q6 | 大世界戰鬥之間 **HP／法力／耐力** 怎麼回：9.6.7 #2 只說城鎮與營火完全回復；野外戰鬥之間回多少？ | 規則 | 玩法 PM 代決 | 照原型現行規則（法力、耐力戰鬥之間不回，HP 照現行）；城鎮與營火回滿 | 5A-4 |
| Q7 | 「營火」在地點圖上是什麼：固定地點，還是任何地點花補給紮營（9.6.7 #11「野外紮營要用」）？ | 規則 | 玩法 PM 代決 | 任何非戰鬥中的地點都能花補給紮營＝營火 | 5A-4 |
| Q8 | 經驗曲線、各來源給多少經驗（7.8 約第 7～8 天到 10 級） | 數值 | 開發 PM 定初值 → 模擬定 | 寫在 content；先沿用原型曲線 | 5A-4 |
| Q9 | 第 2 區 **灰燼荒原** 的內容（敵人家族、地點圖、事件、主線第 2 章）與 **主線第 3 章／賽季 Boss「碎晶之主」**（9.7 只有大綱） | 內容 | 玩法 PM 寫（同 18 的方式） | 程式先做通用，內容等玩法 PM；不擋 5A～5E | 5F 之前 |
| Q10 | 用心清單、種族加值的「方法分類」清單（9.6.4 只給例子；各族清單「大世界開發時定」#89） | 規則 | 玩法 PM 代決 | 只用 9.6.4 表列出的方法；種族加值先只做狐族說服、欺騙（18 事件 18 用到） | 5B-2 |
| Q11 | 線頭上限與到期（9.6.7 #6「每人約 5 條、約 3 天」「數值待大世界開發定」） | 數值 | 開發 PM 定初值 | 5 條、遊戲外 3 天（現實時間），寫 content | 5B-1 |
| Q12 | 系統傭兵的 **固定 build 名單**（9.6.8：輸出、守護、輔助、控制各至少 2 種） | 內容 | 玩法 PM 寫 | 暫用 `content/sim/builds.yaml` 的模擬範本挑 8 個 | 5C-1 |
| Q13 | 好感度的級距與名稱（8.26.1 例「友善」） | 規則 | 玩法 PM 代決 | 5 級：敵視／冷淡／中立／友善／信賴，數值 −100～100 | 5B-4 |
| Q14 | 世界事件門檻依前一天上線人數的比例（#103「比例數值開發時定」） | 數值 | 開發 PM 定初值 | 門檻 × max(上線人數, 1) ÷ 8，最少 1 | 5F-1 |
| Q15 | 「上線人數」「線上的朋友」怎麼算（登入過？當天有動作？） | 實作 | 開發 PM 定 | 當天（6 點到 6 點）有任何世界動作的帳號 | 5F-1 |
| Q16 | 18.3「Boss」「傳送」兩種地點種類不在 9.6.2 的種類表裡 | 內容 | 開發 PM 定（資料分類，不改規則） | schema 加 `boss`、`gate` 兩種；`gate` 只做傳送 | 5A-1 |

### 0.3 不在本階段

- 舊 Phase 5 的 **文字創意動作**（意圖解析器、`improvise`、戰鬥敘事串流、評估集）：移到之後的階段（`docs/專案計畫.md` 第 14 節）。
- 多人 **同場戰鬥**（9.6.7 #13：第一季先只做帶朋友的影子）；即時 PvP（3.2 #4）。
- 交易（8.16 第一季不做）；正式季的卷軸交易、4 件共鳴、傳說、品質。
- LLM 提議新事件骨架（9.6.7 #6「之後」）；LLM 地圖組裝；完整自由移動（9.6.2，之後升級）。
- 大型伺服器架構（PostgreSQL、Redis、分片；12 節標「後期」）。

---

## 1. 六大段的拆分

工時照 BAL 段的大小（每小段約 1～1.5 小時 agent 工時）。「平行」＝不碰同一批檔案，可以和列出的段同時跑（同時進行的 agent 最多 2 個，守則 11）。

### 5A｜地點地圖與城鎮（5 段）

| 段 | 範圍 | 依賴 | 預估 | 可平行 |
|---|---|---|---|---|
| **5A-1** | 地點圖資料與 schema：`content/world/` 地點圖格式、驗證、載入；**雲嶺 18 點** 當第一份內容；`regions.yaml` 加各區地圖池 | — | 1 h | 可與 5A-3 平行 |
| 5A-2 | `trpg.world` 套件骨架：角色在大世界的狀態、世界狀態、時鐘（一天 30 分鐘、6 點刷新、半天換天氣）、移動與遇敵擲骰、隱藏地點感知判定（純函式、可重播） | 5A-1 | 1.5 h | 可與 5A-3 平行 |
| 5A-3 | 雲嶺敵人內容：山中修士 10 種、中立野獸 4 種、源晶失控造物 2 種（18.2）；精英詞綴與元素變體的 schema（9.6.6）；地點 → 遭遇表（含遠程上限、營地混精英） | 5A-1 | 1.5 h | 可與 5A-2 平行（只碰 `content/units/`、`content/world/encounters/`、詞綴 schema） |
| 5A-4 | 遇敵展開戰鬥與城鎮服務：用地點的地圖模板開戰（沿用原型戰鬥、`region` 換皮）、戰前看陣容可撤退（9.6.6）、勝負回寫（經驗、全滅回小鎮＋疲憊 #98）、小鎮休息與換技能（9.6.7 #2、7.6）、傳送點、紮營 | 5A-2、5A-3 | 1.5 h | 否 |
| 5A-5 | API 與前端地點圖畫面：地點圖（點相鄰地點移動、建議等級、隱藏地點、已清空）、小鎮選單、從地點進戰鬥再回來；本機單一開發帳號 | 5A-4 | 1.5 h | 否 |
| 5A-ART1 | 敵人外觀移植①：異形畫法（`docs/art/敵人外觀.md` 第 3 節；美術代決待使用者確認，未確認時照代決先做，改名與配色只動資料） | 5A-3 | 1 h | 可與 5A-4 平行（只動 `client/`） |
| 5A-ART2 | 敵人外觀移植②：精英與頭目記號 | 5A-ART1 | 0.5 h | 可與 5A-5 平行 |
| 5A-ART3 | 敵人外觀移植③：修士新部件（紙娃娃補 11 個小部件） | 5A-ART1 | 0.75 h | 可與 5A-ART2 平行（不同檔案時） |
| 5A-ART4 | 敵人外觀移植④：內容資料（敵人外觀欄位，名稱與數量照玩法 PM 敵人清單） | 5A-3、5A-ART3 | 0.25 h | — |

### 5B｜事件與故事線（5 段）

| 段 | 範圍 | 依賴 | 預估 | 可平行 |
|---|---|---|---|---|
| 5B-1 | 事件骨架與線頭的 schema、**雲嶺 18 個骨架**（18.4）、NPC 人設卡 8 張（18.5）的資料；事件出現頻率由引擎依步數與種子決定（9.6.7 #6） | 5A-2 | 1.5 h | 可與 5C-1 平行 |
| 5B-2 | 情境判定引擎（9.6.4）：模板、LLM 提議的 pydantic schema 與合法性檢查（屬性在允許清單、難度 ±2、劣勢）、d20＋修正、三段結果、用心清單逐筆核對事實、種族 +1、獎懲照預算表；寫入事件日誌、可重播 | 5B-1 | 1.5 h | 否 |
| 5B-3 | 說書人接線（`trpg.narrative`）：挑骨架、填角色與動機、短旁白（1～3 句＋多講一點）、情境敘述、NPC 自由聊天只換資訊；全部經 `LLMClient`、有 Mock、玩家輸入包 `<player_input>`；模型不可用時用模板文字降級（3.1） | 5B-2 | 1.5 h | 否 |
| 5B-4 | 任務狀態機：新手任務鏈、主線第 1 章、區域任務鏈「青霧觀的分裂」（18.7）、隱藏任務、劇情技能與三選一接到現有候選產生器（7.6）；NPC 好感度（9.6.7 #5）；酒館傳聞 | 5B-2 | 1.5 h | 可與 5B-3 平行（不碰 `narrative`） |
| 5B-5 | 前端：事件卡、情境判定輸入（第一次送出即定案、列出持有線索可點選引用）、NPC 對話、任務日誌、線頭列表 | 5B-3、5B-4 | 1.5 h | 否 |

### 5C｜組隊、影子與傭兵（3 段）

| 段 | 範圍 | 依賴 | 預估 | 可平行 |
|---|---|---|---|---|
| 5C-1 | 隊伍 3 人（主角＋最多 2，#97）、系統傭兵名單（content，Q12）與免費雇用（出城前選、野外不能換）、AI 行為設定沿用隊友 | 5A-4 | 1 h | 可與 5B-1 平行 |
| 5C-2 | 朋友的影子：城鎮整備時自動存成影子（#102）、借用時強度上限照招募者（等級、技能階級、物品等級，#87）、不獨佔、每天第一次被借給任務幣與戰報、自己的其他角色可當影子（#100）；賽季 Boss 禁用（留給 5F-3 檢查） | 5C-1 | 1.5 h | 否 |
| 5C-3 | 劇情夥伴（獵戶阿岳，只在對應任務佔隊友位）與 **誓約**（06 6.26、9.6.10 #106、18.6 的 15 種模板；城鎮／營火立誓、同時 1 個、解除後 1 天冷卻、違反判定靠事件日誌） | 5C-1、5B-4 | 1.5 h | 否 |

### 5D｜經濟（4 段）

| 段 | 範圍 | 依賴 | 預估 | 可平行 |
|---|---|---|---|---|
| 5D-1 | 貨幣（金幣、任務幣，8.15）、背包 30 格與腰包 3 個（8.17）、商店（只賣消耗品、粗料、染料；區域特產每週限量；好感度門檻，8.26.1）、霧渡鎮柳掌櫃 | 5A-4 | 1.5 h | 可與 5B 各段平行（不碰事件與 narrative） |
| 5D-2 | 材料：雲嶺 8 種（18.2.4）＋通用粗／精／上料、敵人家族掉材料（M1）、掉落物品等級＝地點建議等級（8.26.2）、精英掉史詩；沿用 3G／3K 物品產生器 | 5D-1、5A-3 | 1.5 h | 否 |
| 5D-3 | 鐵匠與附魔台：打造（指定部位＋1 條關鍵字詞條、其餘傾向由材料決定 M2、物品等級規則）、強化、重骰、精華指定詞條、配方碼與首位發現者（8.20、M6）、隱藏配方（M7，18 的「驚雷霧袍」）；2 件共鳴（M3） | 5D-2 | 1.5 h | 否 |
| 5D-4 | 前端：背包、商店、鐵匠、附魔台畫面 | 5D-3 | 1.5 h | 否 |

### 5E｜Discord 機器人與帳號（3 段）

| 段 | 範圍 | 依賴 | 預估 | 可平行 |
|---|---|---|---|---|
| 5E-1 | 帳號與角色：密碼雜湊（只存雜湊）、一帳號 2～3 角色、停用旗標、登入與 session、角色之間不共用不轉移（#100）；API 改成依帳號／角色存取（取代 5A-5 的開發帳號） | 5A-5 | 1.5 h | 可與 5D 平行 |
| 5E-2 | Discord Bot：有指定身分組才能領帳號、一個 Discord 使用者 ID 一個帳號、重設密碼、身分組被拔時停用（3.1）；Bot 金鑰放設定檔／環境變數，測試用假 Discord 介面不連網 | 5E-1 | 1.5 h | 否 |
| 5E-3 | 公告與部署：每天 6 點貼今日目標與世界事件進度、首殺公告（#103、3.1）；Tunnel 部署說明、本機模型不可用時降級檢查；地點留言與足跡（#105，50 字、使用者可手動刪） | 5E-2 | 1 h | 否 |

### 5F｜賽季與 Boss（5 段）

| 段 | 範圍 | 依賴 | 預估 | 可平行 |
|---|---|---|---|---|
| 5F-1 | 賽季時鐘與日程（9.7 14 天、每日 6 點刷新）、今日目標 3 條（#99）、懸賞板每日刷新先搶先贏（18.7.4 三個懸賞）、世界事件全服進度與門檻自動調整（#103，Q14／Q15）、共享地點狀態（清空與重生、失敗建議等級 +1，9.6.7 #15） | 5E-1、5B-4 | 1.5 h | 否 |
| 5F-2 | 區域 Boss 階段機制：HP 門檻換招式或改地形（9.6.8，引擎資料化）；**霧鎖真人 3 階段**（18.2.3）與青霧執事蓄力強招預告；Boss 專屬地圖 | 5A-3 | 1.5 h | 可與 5F-1 平行（只碰 engine／content） |
| 5F-3 | 賽季 Boss 規則：封印鑰匙與解鎖（第 8 天起、第 10 天強制、24 小時前公告）、只准傭兵（#87）、每日 3 次算帳號、伺服器給種子、首殺日誌與重播驗證（#101）、通關評分榜；解謎機制（源晶柱）的通用資料化 | 5F-1、5F-2、5C-2 | 1.5 h | 否 |
| 5F-4 | 影子循環賽（9.7）：報名（每帳號 1 角色、第 13 天截止）、拉到等級上限、3 張地圖 × 交換先後手 × 多種子、勝場統計、每場可重播 | 5C-2 | 1.5 h | 可與 5F-3 平行 |
| 5F-5 | 季末重置（9.7、#91：數值類全清、紀念類保留）與灰燼荒原內容接入（Q9，內容到位後） | 5F-3 | 1 h | 否 |

> 合計 25 段，約 33 小時 agent 工時。

---

## 2. 架構決定（開發 PM 定）

### 2.1 新套件 `trpg.world`

- **職責**：大世界的確定性規則——地點圖移動、遇敵與事件出現的擲骰、隱藏地點、世界時鐘、補給、任務狀態機、情境判定的引擎半、經濟結算、影子快照、賽季日程。全部是 **純函式**：`world_step(world, char, action, now) → (world, char, events)`。
- **時間由呼叫者傳入**（`now` 是 UTC 秒數整數，API 層讀時鐘後傳進來）；`trpg.world` 內禁止讀取系統時間、禁止 `random` 全域函式與 `uuid4`（守則 1、2）。時鐘換算（遊戲內一天＝30 分鐘、Asia/Taipei 6 點刷新、半天換天氣）寫成純函式，時區用固定 +8 小時位移，不依賴系統時區資料。
- **戰鬥** 仍由 `trpg.engine` 負責；`trpg.world` 只產生「遭遇規格」（地圖 ID、敵方陣容、天氣、種子），戰鬥結果以 **事件摘要** 回寫世界（勝負、擊殺、經驗、掉落），不讀戰鬥中間狀態。
- **LLM**：`trpg.world` 不呼叫 LLM。需要 LLM 的地方（骨架填角色、情境判定提議、旁白、NPC 聊天）放 `trpg.narrative`，輸出先經 pydantic，再交給 `trpg.world` 的合法性檢查（守則 3）；提議寫進事件日誌，重播照紀錄、不再呼叫 LLM。

### 2.2 和 roguelite 的關係

- roguelite 一輪（`trpg.roguelite`、`RunState`、存檔 `trpg-run/13`）**保留不動**，繼續當戰鬥與技能的測試台（9.6「一輪 5 場只是測試」）。Phase 5 不改 `trpg-run` 格式。
- 角色成長的機制（升級、屬性點、靈感與閃現、技能庫與換裝、物品、階級重配）目前寫在 `trpg.roguelite`。Phase 5 **先由 `trpg.world` 匯入並重用** 這些函式與模型，不搬家；`trpg.roguelite` 不得匯入 `trpg.world`。若重用時發現需要改 roguelite 的函式簽名，該段先停下回報 PM（避免兩邊同時改）。之後若要抽出共用的 `trpg.character`，另排一段整修。
- 大世界角色另存（見 2.5），不是 `RunState`；但角色欄位（hero、level、xp、insight、flash、gear…）盡量沿用同名同型別，讓 roguelite 的函式可以直接吃。

### 2.3 依賴方向（import-linter 新增契約）

```
trpg.shared ← trpg.content ← trpg.engine ← trpg.roguelite ← trpg.world ← trpg.narrative? ✗
                                                              ↑
                                                trpg.api（組裝 world＋narrative＋llm）
```

| 契約 | 內容 |
|---|---|
| world 不得匯入上層 | `trpg.world` 不得匯入 `trpg.api`、`trpg.cli`、`trpg.sim`、`trpg.llm`、`trpg.narrative` |
| 下層不得匯入 world | `trpg.engine`、`trpg.content`、`trpg.shared`、`trpg.roguelite`、`trpg.skillgen` 不得匯入 `trpg.world` |
| narrative 不得匯入 world | 維持現行 narrative 契約，另加 `trpg.world`；narrative 只吃純資料（pydantic 模型在 `trpg.content` 或 narrative 自己的 schema），組裝在 `trpg.api` |
| engine 契約 | 現行清單加上 `trpg.world` |

- `tests/test_architecture.py` 同步加上檢查。5A-1 不建立 `trpg.world`（只動 content），契約在 5A-2 加。
- Discord Bot 放 `trpg.bot`（5E-2）：只能匯入 `trpg.api` 的服務層函式或透過 HTTP 呼叫本機 API；`trpg.world`、`trpg.engine` 不得匯入 `trpg.bot`。

### 2.4 確定性

- 世界種子：每季一個 `season_seed`（伺服器建立賽季時產生，存進世界狀態）。
- 衍生亂數：`Rng(fnv1a64(f"{season_seed}:{character_id}:{stream}:{counter}"))` 的形式（沿用 `trpg.shared.rng` 的 `fnv1a64`／`fork`），`stream` 例：`travel`、`reveal`、`event`、`check`、`loot`；`counter` 是該角色該串流的步數，存在角色狀態裡。**不用內建 `hash()`**。
- 戰鬥種子由世界衍生（`stream="battle"`），賽季 Boss 由伺服器給種子（9.7）。戰鬥照現有格式存「初始狀態＋動作列表」。
- 世界與角色的變化一律由 **世界動作日誌**（append-only）重播得到；快照只是快取。測試要能「從空世界＋動作日誌重播出相同的快照」。
- 共享世界的併發：所有世界動作經 API 層的 **單一寫入佇列** 依序套用（5～10 人，不需要分散式）；每筆動作帶伺服器序號，重播照序號。

### 2.5 存檔與版本

| 資料 | 格式 | 位置 |
|---|---|---|
| 大世界狀態快照 | `trpg-world/1` | 伺服器資料夾 |
| 角色 | `trpg-char/1` | 同上（一角色一筆） |
| 世界動作日誌 | `trpg-wlog/1`（一行一筆 JSON） | 同上 |
| 帳號 | `trpg-account/1`（5E-1） | 同上 |
| roguelite 一輪 | `trpg-run/13`（不變） | 現行位置 |

- 儲存層：Phase 5 先用 **本機 JSON／JSON Lines 檔**（12 節「原型以本機 JSON 存檔」）；寫入走暫存檔＋原子改名。5～10 人用量足夠；若 5E 之後發現效能問題再評估 SQLite（標準函式庫，不加相依），屆時另提。
- 每種格式都有 `format` 欄位；讀檔不認得的格式就拒絕（同 `trpg-run` 的做法）。格式升版時寫相容讀取與測試。

### 2.6 內容即資料

- 地點圖、遭遇表、事件骨架、情境判定模板、NPC 人設卡、任務鏈、傭兵名單、誓約模板、商店、材料、賽季日程全部放 `content/`（新子資料夾 `content/world/`），pydantic 驗證，新增內容不改程式（守則 4）。
- **ID 由開發 PM 取**（18 的說明）：每段規格附 18 的中文名 → ID 對照表。

---

## 3. 驗收與檢查方式

照 CLAUDE.md 第 11 條：

- **每段**：實作 agent 只跑相關測試檔（`uv run pytest -q tests/<路徑> -x`，平行最多 `-n 8`）；commit 前跑 `ruff check`、`ruff format --check`、`mypy`、相關測試；動到戰鬥的段加跑一場重播。每完成一個交付項目就 commit。
- **合併**：開發 PM 每段合併只跑上述四項＋相關測試＋一場重播；**每 2～3 段合併跑一次完整 `scripts/check.py`**；每大段（5A…5F）結束、審查前跑一次 `scripts/check.py --full`。
- **大段結束審查**：5A、5B、5D、5F 結束各派一次 reviewer（只讀不改，`docs/開發PM交接.md` 6.5）；5C、5E 段數少，併入下一次審查。
- **確定性驗收**（每個動到 `trpg.world` 的段）：同季種子＋同動作日誌重播出相同快照；`trpg.world` 內沒有時間、`random`、`uuid4`、`hash()`（`tests/test_architecture.py` 已有的禁止清單延伸到 world）。
- **LLM**：所有測試用 `MockLLMClient`、不需網路；玩家輸入包 `<player_input>` 的測試；LLM 提議越界（屬性不在清單、難度超過 ±2、表外獎勵）一律被引擎拒絕的測試。
- **數值**：遇敵率、經驗曲線、補給、遭遇強度等初值寫在 content；需要定數值時寫腳本輸出摘要表、建議值寫進報告由 PM 決定，不反覆手動試；大型模擬除非規格要求不跑。
- **試玩**：使用者醒來後可試玩的里程碑是 **5A-5**（在瀏覽器走雲嶺地點圖、遇敵開戰、回小鎮休息）；之後每大段結束更新試玩說明。

---

## 4. 待決清單

| # | 事項 | 標記 | 備註 |
|---|---|---|---|
| D1 | 18 號文件（雲嶺內容 #111）整份 | **待使用者** | 玩法 PM 代決；本計畫照它做，使用者改了只動 content |
| D2 | Q1 地點連線 | **代決**（玩法 PM） | 5A-1 先用 5.4 初稿；玩法 PM 改了只動 `content/world/cloud_ridge.yaml` |
| D3 | Q3 隱藏地點感知判定的範圍與 DC | **代決**（玩法 PM） | 5A-2 前 |
| D4 | Q6 野外戰鬥之間的回復 | **代決**（玩法 PM） | 5A-4 前；暫用原型現行規則 |
| D5 | Q7 營火＝任何地點花補給紮營？ | **代決**（玩法 PM） | 5A-4 前 |
| D6 | Q10 方法分類清單與各族種族加值 | **代決**（玩法 PM） | 5B-2 前 |
| D7 | Q13 好感度級距 | **代決**（玩法 PM） | 5B-4 前 |
| D8 | Q12 系統傭兵名單（輸出／守護／輔助／控制各 ≥ 2） | **代決**（玩法 PM） | 5C-1 前 |
| D9 | Q9 灰燼荒原內容、主線第 2～3 章、賽季 Boss「碎晶之主」細節 | **代決**（玩法 PM 寫內容） | 5F-2 前 |
| D10 | Q2、Q5、Q8、Q11、Q14 的初值 | **代決**（開發 PM，初值） | 各段規格寫明；之後用模擬定（9.6.10） |
| D11 | Q4、Q15、Q16 | **代決**（開發 PM，實作） | 見 0.2、2.4 |
| D12 | 18 號文件的 ID 命名 | **代決**（開發 PM） | 18 說明「ID 由開發 PM 取」；對照表見 5.3 |
| D13 | Discord 身分組與頻道 | **待使用者** | 3.1「到時新創一個」；5E-2 前要使用者建好並給 Bot 權杖（金鑰由使用者自己放進設定檔，agent 不經手） |
| D14 | Tunnel 服務與對外網址 | **待使用者** | 5E-3 前；使用者電腦上安裝與登入由使用者自己做 |
| D15 | 正式開服日期（第 1 天＝哪天） | **待使用者** | 5F-1 的日程以「賽季開始時間」參數化，不寫死 |
| D16 | `docs/專案計畫.md` 第 14 節：Phase 5 改為「賽季大世界（第一季）」，原「文字創意動作與裝備」標「移到之後的階段」、內容保留 | **代決**（開發 PM，2026-11-02） | 依使用者原話「你們做完就直接開始Phase 5吧 有需要我決定得先幫我決定 記得做了那些決定就好了」；專案 PM 同意由開發 PM 改 |

**代決結果（玩法 PM 2026-11-02，#112～#117，`c16f86f9`；09 9.6.11、18 18.3）**：D2 連線照 5.4 的 21 條；D3 隱藏地點：走到相鄰地點自動擲 d20＋感知，DC＝10＋建議等級÷2，同角色同地點每天 1 次、失敗無懲罰；D4 野外：耐力戰後回滿、法力只在營火與城鎮回滿、HP 不自動回；D5 營火＝非戰鬥地點花 1 補給紮營（敵人還在的營地、精英巢穴、Boss 地點不行）；D6 方法 12 類與 10 族 +1 見 9.6.11；D7 好感度 5 級（≤−50 敵視、−49～−10 冷淡、−9～19 中立、20～59 友善、≥60 信賴）；D8 傭兵 9 名（striker、ranged、fire、tank、guardian、healer、support、storm、trapper）。D9 玩法 PM 5F 前交。

---

## 5. 5A-1 詳細規格：地點圖資料與 schema

> 給實作 agent。只動 `content/`、`src/trpg/content/`、`tests/content/`；**不建立 `trpg.world`、不動引擎、API、前端、roguelite**。

### 5.1 目標

用資料定義「每個區域一張地點圖」（09 9.6.2），並寫入第一份內容：**雲嶺 18 個地點**（18.3）。載入時驗證結構與跨檔案引用（地圖模板、區域、地圖池），讓 5A-2 之後的移動與遇敵直接讀它。

### 5.2 交付項目

1. **`regions.yaml` 加各區戰場地圖池**（05 5.1「區域地圖池」，#43）
   - `RegionDef` 新增選填欄位 `map_pool: tuple[Archetype, ...] = ()`（`Archetype` 用 `trpg.content.maps` 現有的型別）；空＝不檢查。驗證：不可重複、不可含 `test`、`training`、`boss`。
   - 五區資料照 05 表（只寫 archetype ID）：

     | 區 | `map_pool` |
     |---|---|
     | `crystal_crown` | `open_plain, corridor, ruined_heights, bridge_chasm, forest, swamp, oil_depot` |
     | `cloud_ridge` | `open_plain, corridor, ruined_heights, bridge_chasm, forest, swamp, frozen_lake` |
     | `arcane_hub` | `open_plain, corridor, ruined_heights, bridge_chasm, swamp, frozen_lake, oil_depot` |
     | `ashen_waste` | `open_plain, corridor, ruined_heights, bridge_chasm, forest, swamp, oil_depot` |
     | `frost_tide` | `open_plain, corridor, ruined_heights, bridge_chasm, forest, swamp, frozen_lake` |

   - 檔頭註解說明欄位來源（05 5.1、#43）。`RegionTable.summary()` 不必改。

2. **新 schema `src/trpg/content/world_map.py`**（`__all__` 明列；繼承 `ContentModel`；ID 用 `trpg.content.battle.ID_PATTERN`）

   ```python
   LocationKind = Literal[
       "town",  # 區域小鎮（9.6.1）
       "camp",  # 營地（9.6.2）
       "ruin",  # 遺跡
       "altar",  # 祭壇
       "anomaly",  # 異象
       "caravan",  # 商隊
       "village",  # 村落
       "secret",  # 秘境（隱藏）
       "elite_lair",  # 精英巢穴
       "boss",  # 區域 Boss 據點（18.3；Q16）
       "gate",  # 通往其他區域的傳送點（18.3；Q16）
   ]
   RevealMethod = Literal[
       "perception_nearby",  # 靠近時感知判定（9.6.7 #10）
       "situation",  # 情境判定成功
       "quest_clue",  # 任務線索
       "friend_footprint",  # 朋友的足跡
   ]


   class MapPos(ContentModel):
       x: int = Field(ge=0, le=100)  # 前端畫地點圖用的相對座標（純顯示）
       y: int = Field(ge=0, le=100)


   class LocationDef(ContentModel):
       id: str  # ID_PATTERN
       name_zh: str  # min_length=1
       kind: LocationKind
       level_min: int | None = None  # 建議等級（9.6.2）；town、gate 必須是 None，其餘必填
       level_max: int | None = None  # 省略＝同 level_min；必須 >= level_min
       battle_maps: tuple[str, ...] = ()  # content/maps 的地圖 ID（遇敵展開格子用，9.6.2）
       hidden: bool = False  # 要探索才會出現（9.6.2）
       reveal: tuple[RevealMethod, ...] = ()  # hidden=True 時必填、不可重複
       gate_to: str | None = None  # 只有 gate 可填：通往的區域 ID
       unlock_flag: str | None = (
           None  # 世界旗標 ID（ID_PATTERN）；有值＝旗標成立前不能進入（只存資料，5A-2 才判定）
       )
       description_zh: str = ""  # 地點說明（18.3「內容」欄；純顯示）
       pos: MapPos


   class LocationMapDef(ContentModel):
       region: str  # regions.yaml 的區域 ID；一區一檔
       name_zh: str
       level_min: int = Field(ge=1)  # 區域等級範圍（7.8）
       level_max: int
       town: str  # 本區小鎮的地點 ID
       locations: tuple[LocationDef, ...]
       edges: tuple[tuple[str, str], ...]  # 無向連線
   ```

   **單檔驗證（`model_validator`，錯誤訊息用繁體中文，指出地點 ID）**：
   1. 地點數 15～25（9.6.2）。
   2. 地點 ID 不重複。
   3. `kind == "town"` 恰好 1 個，且等於 `town` 欄位（9.6.1「每區 1 座」）。
   4. `town`、`gate`：`level_min`／`level_max` 必須是 `None`；其餘種類 `level_min` 必填；`level_max` 省略時視為 `level_min`；`level_min <= level_max`；兩者都在區域 `[level_min, level_max]` 內。
   5. `battle_maps`：`town`、`gate`、`village`、`caravan` 必須為空；`camp`、`elite_lair`、`secret` 至少 1 張；其餘（`ruin`、`altar`、`anomaly`、`boss`）可空。不可重複。
   6. `kind == "secret"` ⇒ `hidden` 必須是 `True`；`hidden` ⇒ `reveal` 至少 1 項；`town`、`gate` 不可 `hidden`。
   7. `gate_to` 只有 `gate` 可填，且 `gate` 必填；不可等於本區。
   8. `edges`：兩端都是本檔的地點 ID；不可自連；無向去重後不可重複（`(a,b)` 與 `(b,a)` 算重複）。
   9. 連通：從 `town` 出發，所有地點都走得到；而且 **把所有 `hidden` 地點拿掉後**，所有非隱藏地點仍從 `town` 走得到（隱藏地點不能是唯一通路）。用 BFS，鄰接表依 ID 排序（守則 2，不依賴 set 順序）。
   10. `level_min <= level_max`（區域）。

   **方法**：`location_by_id() -> dict[str, LocationDef]`、`neighbors(location_id) -> tuple[str, ...]`（排序後回傳）、`summary() -> str`（例：「雲嶺：18 個地點（隱藏 2）、21 條連線、等級 1～6」）。

   **跨檔案檢查** 函式（同檔）：
   ```python
   def world_map_problems(
       world_map: LocationMapDef,
       *,
       regions: RegionTable | None,
       maps: Mapping[str, MapDef],
   ) -> list[str]
   ```
   - `region`、`gate_to` 必須在 `regions.yaml`。
   - `battle_maps` 的每個 ID 必須在 `maps`。
   - 非 `boss` 地點的地圖，其 `archetype` 必須在該區 `map_pool` 內（`map_pool` 為空則跳過）；`archetype` 為 `boss` 的地圖只能放在 `kind == "boss"` 的地點。
   - 回傳排序過的問題清單；空＝通過。

3. **載入**（`src/trpg/content/library.py`）
   - `ContentLibrary` 新增 `world_maps: dict[str, LocationMapDef]`（鍵＝`region`），預設空 dict。
   - `content/world/maps/` 資料夾存在時，用現有 `_load_dir` 載入（資料夾不存在＝空，讓舊測試複製的精簡 content 照常載入）；同一 `region` 出現兩檔 → `ContentError`。
   - 載入後呼叫 `world_map_problems`，有問題 → `ContentError`（指出檔案）。
   - 若 `_load_dir` 以檔內 `id` 當鍵：本 schema 用 `region` 當鍵，必要時寫一個小的專用載入函式，不改 `_load_dir` 的行為。
   - `trpg content check` 透過 `library.files` 會自動列出新檔摘要；確認它有出現。

4. **雲嶺內容 `content/world/maps/cloud_ridge.yaml`**：照 18.3 的 18 個地點、5.3 的 ID 對照、5.4 的連線。檔頭註解：來源 `docs/design/18-雲嶺內容.md` 18.3（#111，玩法 PM 代決、待使用者確認）；連線是開發 PM 初稿（Q1，待玩法 PM 代決）；`pos` 是開發 PM 排的顯示座標。

5. **測試 `tests/content/test_world_map.py`**（見 5.5）。

6. **完成報告 `docs/phases/Phase5A-1報告.md`**：交付、測試結果、用了 18 的哪些內容、所有開發 PM 自定的東西（ID、連線、座標、種類對照）、待 PM 決定。

### 5.3 雲嶺地點對照（18.3 → 資料）

區域：`region: cloud_ridge`、`name_zh: 雲嶺`、`level_min: 1`、`level_max: 6`（18.1）、`town: mist_ferry`。

| 地點（18.3） | `id` | `kind` | 等級 | `battle_maps` | `hidden`／`reveal` | 其他 | `pos` |
|---|---|---|---|---|---|---|---|
| 霧渡鎮 | `mist_ferry` | town | — | — | | | 10,80 |
| 渡口石階 | `ferry_steps` | camp | 1 | `cliff_outpost` | | | 25,85 |
| 竹林小徑 | `bamboo_path` | camp | 1～2 | `dark_forest` | | | 30,65 |
| 雨中梯田 | `rain_terraces` | camp | 2 | `swamp` | | | 45,70 |
| 青霧觀山門 | `mist_temple_gate` | village | 2 | — | | | 50,55 |
| 獵戶小屋 | `hunter_hut` | village | 2 | — | | | 15,55 |
| 斷崖幫寨 | `cliff_gang_fort` | camp | 3 | `narrow_halls` | | | 60,80 |
| 古松祭壇 | `old_pine_altar` | altar | 3 | — | | | 35,45 |
| 雲海吊橋 | `cloud_sea_bridge` | camp | 3～4 | `bridge_chasm` | | | 60,45 |
| 藥師谷 | `herb_valley` | ruin | 4 | — | | | 75,65 |
| 丹爐洞（隱藏） | `elixir_cave` | secret | 5 | `narrow_halls` | 是／`situation` | | 90,70 |
| 北坡獵場 | `north_slope` | elite_lair | 4～5 | `open_plain` | | | 25,25 |
| 冬湖 | `winter_lake` | camp | 4 | `frozen_lake` | | | 15,40 |
| 劍冢 | `sword_tomb` | ruin | 5 | `ruined_fort` | | | 70,30 |
| 源晶裂痕 | `crystal_rift` | anomaly | 5 | `open_plain` | | | 50,20 |
| 鶴歸崖（隱藏） | `crane_cliff` | secret | 6 | `cliff_outpost` | 是／`perception_nearby, quest_clue, friend_footprint` | | 30,8 |
| 雲頂觀 | `cloud_summit` | boss | 6 | —（5F-2 補 Boss 專屬地圖） | | | 75,10 |
| 往灰燼荒原的渡口 | `ashen_ferry` | gate | — | — | | `gate_to: ashen_waste`、`unlock_flag: mist_tide_success` | 5,95 |

- **地圖模板對照**（18.3 的戰場名 → 現有地圖檔；機制不動，只看 archetype）：山寺石階、高台廢墟 → `ruined_heights`（`cliff_outpost`、`ruined_fort`）；竹林 → `dark_forest`；雨中梯田 → `swamp`；峽谷棧道、狹窄長廊 → `narrow_halls`；雲海吊橋 → `bridge_chasm`；高原草甸、開闊平原 → `open_plain`；冬湖 → `frozen_lake`。雲嶺換皮（`region: cloud_ridge`）目前只有 `dark_forest`、`bridge_chasm`；其他地圖在大世界戰鬥時用地點的區域換皮，是 5A-4 的事，本段不改地圖檔。
- `description_zh` 照 18.3「內容」欄抄（例：渡口石階「新手任務 1：盜賊搶渡船」）。
- `reveal` 的依據：丹爐洞「藥師谷 … 通往隱藏地點」→ `situation`；鶴歸崖「感知判定或朋友足跡才會出現」＋事件 18 的線頭「狐火在霧裡指路（鶴歸崖的提示）」→ `perception_nearby, quest_clue, friend_footprint`。
- `unlock_flag: mist_tide_success`：世界事件 #1「霧潮入侵」成功（9.7、18.3）；旗標只存資料，判定在 5A-2／5F-1。

### 5.4 雲嶺連線初稿（Q1，待玩法 PM 代決）

原則：小鎮為起點、建議等級由低往高延伸、隱藏地點掛在提示它的地點旁、不是唯一通路。共 21 條：

```
mist_ferry – ferry_steps          mist_ferry – hunter_hut          mist_ferry – ashen_ferry
ferry_steps – bamboo_path         bamboo_path – hunter_hut         bamboo_path – rain_terraces
rain_terraces – mist_temple_gate  rain_terraces – cliff_gang_fort  rain_terraces – old_pine_altar
hunter_hut – winter_lake          old_pine_altar – cloud_sea_bridge mist_temple_gate – cloud_sea_bridge
cliff_gang_fort – herb_valley     cloud_sea_bridge – herb_valley   cloud_sea_bridge – sword_tomb
herb_valley – elixir_cave         winter_lake – north_slope        north_slope – crane_cliff
north_slope – crystal_rift        sword_tomb – crystal_rift        crystal_rift – cloud_summit
```

（鶴歸崖只連北坡獵場；雲頂觀只從源晶裂痕進入，對應主線第 1 章「源晶裂痕 → 雲頂觀」。）

### 5.5 測試（`tests/content/test_world_map.py`）

用 `load_library()`（module scope fixture）測實際內容；用最小合法的 `LocationMapDef` 字典（測試內建一個 15 點的小圖產生函式）測各條驗證規則。

| 測試 | 內容 |
|---|---|
| 載入雲嶺 | `library.world_maps["cloud_ridge"]` 存在；18 個地點、21 條連線、2 個隱藏、town＝`mist_ferry`；`summary()` 含「18 個地點」 |
| 雲嶺跨檔案 | `world_map_problems(...) == []`；所有 `battle_maps` 的 archetype 都在雲嶺 `map_pool`；沒有 `oil_depot` |
| 地圖池 | 五區都有 7 種 `map_pool`；4 種通用類型五區都有；每區含 `forest／swamp／frozen_lake／oil_depot` 中恰好 3 種（05 5.1） |
| 地點數 | 14 點、26 點 → `ValidationError` |
| ID 重複 | → 錯誤 |
| 小鎮 | 0 個或 2 個 town、`town` 欄位指向非 town → 錯誤 |
| 等級 | town 帶等級、camp 沒等級、`level_max < level_min`、超出區域範圍 → 錯誤；`level_max` 省略＝`level_min` |
| 戰鬥地圖 | camp 沒地圖、town 有地圖 → 錯誤；ruin 沒地圖 → 通過 |
| 隱藏 | secret 非 hidden、hidden 沒 reveal、town hidden → 錯誤 |
| gate | gate 沒 `gate_to`、camp 有 `gate_to`、`gate_to` 等於本區 → 錯誤 |
| 連線 | 未知端點、自連、`(a,b)`＋`(b,a)` 重複 → 錯誤 |
| 連通 | 有孤立地點 → 錯誤；某非隱藏地點只能經過隱藏地點到達 → 錯誤 |
| `neighbors` | 回傳排序過的 tuple；`neighbors("mist_ferry") == ("ashen_ferry", "ferry_steps", "hunter_hut")` |
| 跨檔案錯誤 | 未知地圖 ID、未知 `region`、地圖 archetype 不在地圖池、`boss` 地圖放在 camp → `world_map_problems` 回傳對應訊息；`load_library` 對壞檔丟 `ContentError` |
| 沒有 world 資料夾 | 複製一份不含 `world/` 的 content（照 `test_regions.py` 的 `tmp_path` 做法）→ `world_maps == {}`，載入照常 |
| 確定性 | 同一檔載兩次，`model_dump()` 相同；BFS 結果與 dict／set 順序無關（把 `edges` 反序後驗證結果相同） |

### 5.6 驗收

- `uv run pytest -q tests/content/test_world_map.py tests/content/test_regions.py tests/content/test_loader.py -x` 通過。
- `ruff check`、`ruff format --check`、`mypy`（strict）通過；`C901` 不超過 15（BFS、驗證拆成小函式）。
- `uv run trpg content check` 通過，並列出 `world/maps/cloud_ridge.yaml` 的摘要。
- 不需要重播（沒動戰鬥）；不跑全量 `scripts/check.py`（PM 合併時跑）。

### 5.7 不做的事

- 不建立 `trpg.world`、不做移動、遇敵、時鐘、存檔（5A-2）。
- 不寫遭遇表與敵人（5A-3）；不改任何地圖檔、不新增雲嶺換皮或 Boss 地圖（5A-4、5F-2）。
- 不做 API、前端、CLI 新指令。
- 不改 roguelite、引擎、`trpg-run` 格式。
- 不自己補 18 號文件沒有的地點、不改 18 的名稱與等級；連線與座標以外的不確定處，照最保守做法並寫進報告「待 PM 決定」。

---

## 6. 5A-2 詳細規格：`trpg.world` 套件骨架

> 給實作 agent。只動 `src/trpg/world/`（新）、`src/trpg/content/`（新增世界規則 schema 與載入）、`content/world/rules.yaml`（新）、`tests/world/`（新）、`tests/content/`、`tests/test_architecture.py`、`pyproject.toml`（import-linter 契約）。**不做** API、前端、敵人與遭遇表（5A-3）、開戰與戰後回寫（5A-4）。不動 `content/skills/`、`src/trpg/skillgen/`、`trpg.roguelite`、`trpg.engine`。
> 依據：09 9.6.2、9.6.7 #9～#11、#15、#16、9.6.9「時間」、9.6.10 #104、9.6.11 #112（隱藏地點感知）、#113（回復）、#114（營火＝紮營）；`docs/專案計畫.md` 3.1（一天＝現實 30 分鐘、Asia/Taipei 6 點刷新）；05 5.1「各區天氣傾向」、5.7 天氣 4 種；本檔第 2 節。

### 6.1 目標

大世界的確定性規則核心：角色在地點圖上走動、每一步擲遇敵、走到隱藏地點旁自動感知判定、非戰鬥地點紮營；世界時鐘與各區天氣。全部是純函式：`world_step(library, world, char, action, now) → StepResult(world, char, events)`，時間 `now`（UTC 秒數整數）由呼叫端傳入；「初始快照＋世界動作日誌」可重播出相同快照。遇敵只產生 **遭遇結果** 資料（不開戰）。

### 6.2 交付項目

1. **世界規則 content**：`content/world/rules.yaml` ＋ schema `src/trpg/content/world_rules.py`（`WorldRules`），`ContentLibrary.world_rules: WorldRules | None`（檔案不存在＝`None`，讓舊測試的精簡 content 照常載入）。跨檔案檢查：天氣 ID 必須在 `weather.yaml`、區域 ID 必須在 `regions.yaml`。
2. **`trpg.world` 套件**（新）：
   - `clock.py`：時鐘純函式。
   - `rng.py`：世界亂數衍生。
   - `state.py`：`WorldState`（`trpg-world/1`）、`CharacterState`（`trpg-char/1`）與子模型。
   - `actions.py`：世界動作（pydantic 判別聯集）、事件、`EncounterResult`。
   - `step.py`：`world_step`（移動＋遇敵、感知判定、紮營）與 `WorldActionError`。
   - `replay.py`：世界動作日誌（`trpg-wlog/1`）與重播。
   - `save.py`：三種格式的序列化／讀取（拒絕未知 `format`）與原子寫檔。
3. **import-linter 契約**（第 2.3 節）與 `tests/test_architecture.py` 對應更新；確定性掃描延伸到 `world`，並新增禁止內建 `hash()` 呼叫（第 3 節「確定性驗收」）。
4. **測試** `tests/world/`（見 6.6）。
5. **完成報告** `docs/phases/Phase5A-2報告.md`：交付、模組結構、確定性與重播測試、代決清單、待 PM 決定。

### 6.3 時鐘（`trpg.world.clock`，數值是使用者已定的事，寫成常數）

| 常數 | 值 | 依據 |
|---|---|---|
| `GAME_DAY_SECONDS` | 1800（現實 30 分鐘＝遊戲 1 天） | 3.1、9.6.9 |
| `WEATHER_PERIOD_SECONDS` | 900（半天換一次天氣） | 9.6.10 #104 |
| `UTC_OFFSET_SECONDS` | 8 × 3600（Asia/Taipei 固定位移，不讀系統時區） | 2.1 |
| `REFRESH_HOUR` | 6（現實早上 6 點刷新） | 3.1、9.6.9 |

函式（全部只吃 `now: int`，負數拋 `ValueError`）：

- `game_day_index(now) = now // 1800`；`half_day_index(now) = now // 900`。遊戲日以 Unix 紀元對齊：台北 06:00（UTC 22:00）是 1800 的倍數，所以每天的刷新點一定是遊戲日的開頭。
- `day_phase(now) -> "day" | "night"`：遊戲日前半（前 15 分鐘）＝白天、後半＝夜晚。
- `game_clock(now) -> (hour, minute)`：遊戲內時刻，遊戲日從 06:00 開始（白天 06:00～18:00、夜晚 18:00～06:00）。
- `refresh_day(now) = (now + 8h − 6h) // 86400`：「哪一天」（以台北早上 6 點為界）；每日一次的判定用它。
- `next_refresh_at(now)`：下一次 6 點刷新的 UTC 秒數。

### 6.4 資料結構

**`content/world/rules.yaml`（`WorldRules`；初值，開發 PM 定、之後模擬定，9.6.10「數值類」）**

```yaml
supplies:
  max: 10  # 補給上限（9.6.7 #11）
  start: 5  # 新角色帶的補給
camp_cost: 1  # 紮營花的補給（#114）
hasten:
  cost: 1  # 趕路花的補給（9.6.7 #9）
  encounter_permille: 500  # 趕路時遇敵機率 × 500‰
encounter:  # 遇敵機率（‰）＝ min(max, base + per_level ×（建議等級 − 1））；town、gate 為 0
  base_permille: 150
  per_level_permille: 30
  max_permille: 500
perception:  # #112：DC ＝ dc_base ＋ 建議等級 ÷ level_divisor（捨去）
  dc_base: 10
  level_divisor: 2
weather:  # 各區天氣權重（05 5.1 傾向、5.7 的 4 種）；day／night 對應 day_phase
  - {region: cloud_ridge, day: {clear: 1, rain: 3, fog: 3}, night: {night: 1, rain: 3, fog: 3}}
  # 五區都照 05 5.1 表的傾向（傾向權重 3、其他 1；「夜」傾向只加在 night）
```

驗證：數值非負、`start <= max`、權重 ≥ 0 且每組總和 > 0、區域不重複；跨檔案：天氣 ID 在 `weather.yaml`、區域在 `regions.yaml`。沒有列的區域用 `default_weather`（`day: {clear: 1}`、`night: {night: 1}`）。

**`WorldState`（`trpg-world/1`）**

| 欄位 | 型別 | 說明 |
|---|---|---|
| `format` | `Literal["trpg-world/1"]` | |
| `season_id` | `str`（ID_PATTERN） | |
| `season_seed` | `int`（0～2⁶⁴−1） | 第 2.4 節 |
| `season_start` | `int`（UTC 秒） | 5F-1 用；本段只存 |
| `flags` | `tuple[str, ...]`（排序、不重複） | 世界旗標；地點的 `unlock_flag` 判定用 |
| `cleared` | `tuple[ClearedLocation, ...]`（`region`、`location`、`respawn_at`；依區域與地點排序） | 共享「已清空」（9.6.7 #15）；本段只讀（紮營判定），寫入在 5A-4／5F-1 |

**`CharacterState`（`trpg-char/1`）**——欄位盡量和 `RunState` 同名同型別（2.2）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `format` | `Literal["trpg-char/1"]` | |
| `character_id` | `str`（ID_PATTERN） | 亂數衍生的「角色」段 |
| `hero` | `UnitTemplate` | 感知修正、HP／法力上限從這裡算 |
| `origin` | `str \| None` | |
| `level`、`xp` | `int` | 同 `RunState` |
| `hp`、`mana` | `int`（≥ 0） | 目前值 |
| `stamina` | `int \| None` | `None`＝滿（同 `RunState`） |
| `region`、`location` | `str` | 目前位置 |
| `supplies` | `int`（≥ 0） | |
| `revealed` | `tuple[LocationRef, ...]`（排序、不重複） | 這個角色發現的隱藏地點 |
| `perception_marks` | `tuple[PerceptionMark, ...]` | 每個隱藏地點最後一次感知判定的 `refresh_day`（#112 每天 1 次） |
| `rng_counters` | `dict[str, int]`（依鍵排序） | 每個亂數串流已用的次數 |
| `pending_encounter` | `EncounterResult \| None` | 還沒處理的遭遇（5A-4 開戰後清掉） |
| `camped_at` | `LocationRef \| None` | 目前紮營中的地點（離開就清掉；5A-4 換技能等服務用） |

建立：`new_character(library, character_id, hero, *, region, origin=None) -> CharacterState`（等級 1、HP／法力滿、補給 `start`、站在該區小鎮）。

**動作（`WorldAction`，`kind` 判別）**：`TravelAction(kind="travel", to, hasten=False)`、`CampAction(kind="camp")`。

**事件（`WorldEvent`，`kind` 判別）**：`traveled`（from、to、hasten、supplies_spent）、`encounter_check`（location、chance_permille、roll、encountered）、`encounter`（`EncounterResult`）、`perception_check`（location、roll、modifier、dc、success）、`location_revealed`（location、method）、`camped`（location、supplies_left、hp、mana）。

**`EncounterResult`**：`region`、`location`、`level`（建議等級，`level_max`）、`battle_map: str | None`（從目的地 `battle_maps` 抽一張；空＝`None`，由 5A-4 從區域地圖池挑）、`battle_seed: int`（32 位元）、`weather`、`day_phase`、`at`（`now`）。不含敵人陣容（5A-3／5A-4）。

**世界動作日誌（`trpg-wlog/1`）**：第一行 `{"format": "trpg-wlog/1"}`，之後每行一筆 `WorldLogEntry(seq, now, character_id, action)`。`replay(library, world, characters, entries)` 依序套用；`seq` 必須嚴格遞增、`now` 不可倒退，否則拋 `WorldReplayError`。

### 6.5 規則

**亂數衍生（2.4）**：`Rng(fnv1a64(f"{season_seed}:{character_id}:{stream}:{counter}".encode()))`；每用一次該串流 `counter` +1（存在 `rng_counters`）。串流：`travel`（遇敵擲骰）、`battle`（遭遇的地圖與戰鬥種子）、`reveal`（感知判定）。**天氣** 是全區共用（#104「同一區所有人看到相同的天氣」），角色段改成 `@<region>`、計數用 `half_day_index(now)`：`f"{season_seed}:@{region}:weather:{half_day_index}"`，依 `rules` 權重抽（純函式 `weather_at(library, world, region, now)`，不存狀態）。不用內建 `hash()`。

**移動（`travel`）**——不合法一律拋 `WorldActionError`（中文訊息），狀態不變：
1. 有 `pending_encounter` 時不能移動。
2. `to` 必須是目前地點的鄰居（`LocationMapDef.neighbors`）；隱藏地點必須已在 `revealed`；有 `unlock_flag` 的地點旗標要在 `world.flags`。
3. `hasten=True` 時補給必須 ≥ `hasten.cost`，扣掉。
4. 遇敵：目的地建議等級（`level_max`）查 `encounter` 公式得機率（town、gate＝0；趕路再 × `hasten.encounter_permille`‰，整數捨去），`travel` 串流 `randint(0, 999) < 機率` 即遇敵（機率 0 也照擲，讓亂數消耗固定）。
5. 角色移到目的地、清掉 `camped_at`。遇敵時用 `battle` 串流抽地圖與種子，寫入 `pending_encounter` 並發 `encounter` 事件。
6. **感知判定**（#112）：對目的地的每個鄰居（ID 排序），若是隱藏地點、`reveal` 含 `perception_nearby`、這個角色還沒發現、今天（`refresh_day(now)`）還沒判定過：`reveal` 串流擲 d20＋感知修正（`(wis − ability_mod_base) // ability_mod_divisor`，同引擎的 `ability_modifier`）≥ DC（`dc_base`＋隱藏地點 `level_min` ÷ `level_divisor`）即發現；記錄 `perception_marks`。失敗沒有懲罰。

**紮營（`camp`）**（#114）：
1. 有 `pending_encounter` 時不能紮營。
2. 不能紮營的地點：`town`（城鎮直接休息，5A-4）、`elite_lair`、`boss`；`camp` 種類要 `world.cleared` 裡有這個地點且 `now < respawn_at`（敵人還在＝不能）。其他種類（村落、祭壇、遺跡、異象、商隊、秘境、傳送點）可以。
3. 補給 ≥ `camp_cost`，扣掉；HP 回到 `run_max_hp`、法力回到上限、耐力設為 `None`（滿）；`camped_at` 設為目前地點。

### 6.6 測試（`tests/world/`）

| 檔案 | 內容 |
|---|---|
| `test_clock.py` | 一天 1800 秒、半天 900 秒；台北 06:00 是遊戲日開頭；`day_phase` 前半白天後半夜晚；`game_clock` 從 06:00 起；`refresh_day` 在台北 05:59:59 與 06:00:00 之間切換；`next_refresh_at`；負數拒絕 |
| `test_rules_content.py` | 載入 `world_rules`；未知天氣、未知區域、權重總和 0、`start > max` → 錯誤；沒有 `world/rules.yaml` → `None` |
| `test_travel.py` | 走到鄰居；非鄰居、未發現的隱藏地點、未解鎖的旗標地點、補給不足的趕路、有未處理遭遇 → `WorldActionError` 且狀態不變；回小鎮遇敵機率 0；趕路扣補給、機率減半；遇敵產生 `EncounterResult`（地圖在目的地 `battle_maps` 內，沒有地圖的目的地為 `None`）；計數器遞增 |
| `test_perception.py` | 走到鶴歸崖的鄰居（北坡獵場）時判定、DC＝13；成功後可走進鶴歸崖；同一天不重判、隔天（6 點後）再判；丹爐洞（只有 `situation`）不判；感知高（必成功）／低（必失敗）的角色 |
| `test_camp.py` | 村落可紮營、HP 法力回滿、扣補給、`camped_at`；town、`elite_lair`、`boss`、未清空的營地、補給 0 → 錯誤；已清空且未重生的營地可紮營、過了 `respawn_at` 不行；移動後 `camped_at` 清掉 |
| `test_rng.py` | 衍生字串格式固定（測試向量）；不同角色、串流、計數得到不同結果；天氣同區同半天所有角色相同、權重 0 的天氣抽不到 |
| `test_replay.py` | 同初始快照＋同日誌重播兩次，快照（JSON）完全相同；日誌寫出再讀回重播結果相同；`seq` 不遞增、`now` 倒退 → `WorldReplayError`；hypothesis：隨機合法動作序列重播一致 |
| `test_save.py` | `trpg-world/1`、`trpg-char/1`、`trpg-wlog/1` 序列化往返相等；未知 `format` 拒絕；原子寫檔 |

`tests/test_architecture.py`：`trpg.world` 在原始碼樹內；world 不得匯入 api、cli、sim、llm、narrative；engine、content、shared、roguelite、skillgen、narrative 不得匯入 world；`world` 列入確定性套件；掃描器偵測 `hash(...)`。

### 6.7 驗收

- `uv run pytest -q tests/world tests/content tests/test_architecture.py -n 8 --timeout=1800` 通過。
- `ruff check .`、`ruff format --check .`、`mypy`（strict）、`lint-imports` 通過；`C901` ≤ 15。
- `uv run trpg content check` 列出 `world/rules.yaml` 的摘要。
- 不跑全量 `scripts/check.py`（PM 合併時跑）；沒動戰鬥，不需戰鬥重播。

### 6.8 不做的事

- 不開戰、不寫戰後回寫（經驗、全滅回小鎮、疲憊、清空與重生的寫入）、不做城鎮休息、換技能、傳送點跨區（5A-4）。
- 不做敵人、遭遇表、日夜與天氣對敵人的影響（5A-3）；遭遇結果只帶天氣與日夜資料。
- 不做事件出現擲骰、線頭（5B-1）、情境判定（5B-2）、朋友足跡與任務線索揭露（5B／5C）。
- 不做 API、前端、CLI、帳號、角色建立流程（5A-5、5E-1）；角色建立不進日誌（重播從初始快照開始）。
- 不改 `trpg-run` 格式、roguelite、引擎。

### 6.9 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5A2-1 | 時鐘常數寫在程式（使用者已定的值），不放 content | 改值要回使用者 |
| 5A2-2 | 遊戲日對齊 Unix 紀元（因此對齊台北 6 點），遊戲日 06:00 開始、前半白天後半夜晚 | 9.6.9／#104 沒寫起點 |
| 5A2-3 | 遇敵率、趕路、補給上限與初值、各區天氣權重 | 6.4 初值，content 可改；之後模擬定 |
| 5A2-4 | 遇敵用目的地的建議等級上限；town、gate 為 0；遇敵後仍抵達目的地，遭遇擱在角色上、處理前不能移動或紮營 | 9.6.2「路上可能遇敵」沒寫細節 |
| 5A2-5 | 感知 DC 的「建議等級」用隱藏地點的 `level_min` | 雲嶺兩個隱藏地點都只有單一等級，不影響 |
| 5A2-6 | 傳送點可以紮營；紮營不含城鎮（城鎮休息是 5A-4 的服務） | #114 列舉「城鎮以外…等」 |
| 5A2-7 | 天氣衍生的角色段用 `@<region>`、計數用半天序號 | 2.4 只寫角色串流，天氣全區共用 |
| 5A2-8 | 重播從「初始世界快照＋初始角色快照」開始，角色建立不進日誌 | 帳號與角色建立在 5E-1 |

## 7. 之後各段規格

（5A-2 驗收後補上 5A-3 起。）

## 8. 5B-1 詳細規格：事件骨架與線頭的資料層

> 給實作 agent。只動 `content/world/events/`（新）、`content/world/npcs/`（新）、`content/world/event_rules.yaml`（新）、`src/trpg/content/world_events.py`（新）、`src/trpg/content/library.py`（載入，改動要小）、`src/trpg/world/`（新增 `threads.py`、`events.py`；`state.py`、`actions.py`、`rng.py`、`step.py` 小改）、`tests/content/`、`tests/world/`、CLI 快照（`trpg content check` 變了才重產）。**不做** 情境判定（5B-2）、LLM 與旁白（5B-3）、任務狀態機與好感度（5B-4）、前端（5B-5）。不動 `content/skills/`、`src/trpg/skillgen/`、引擎、roguelite、5A-3 的遭遇表與敵人檔。
> 依據：09 9.2（storylet：任務是需求的產物、結構與獎勵由系統模板決定、LLM 只包裝）、9.6.7 #3、#5、#6（骨架＋線頭、事件結束留 0～2 條線頭、每人約 5 條上限、約 3 天到期、世界級／個人線頭、**事件出現頻率由引擎依移動步數與種子決定，LLM 不能自己多生事件；線頭只能由事件結果產生**）、#16（日夜與天氣改變機遇）、9.6.4（情境判定是骨架的一種解法、允許的屬性）；18 18.3、18.4（18 個骨架）、18.5（8 張 NPC 人設卡）；10 第 10、11 節（LLM 只提議、玩家輸入當資料）；本檔 0.2 Q11、2.4、2.5、6.4。

### 8.1 目標

雲嶺的 18 個事件骨架、骨架可能留下的線頭、8 張 NPC 人設卡成為 content 資料（pydantic 驗證、跨檔案引用檢查）；移動時由 `trpg.world` 依「距離上次事件的步數＋種子」擲骰決定是否觸發事件，觸發時只產生 **「觸發了哪個骨架」的資料**（`EventTrigger`），存在角色上，給 5B-2～5B-4 接手。線頭的狀態模型（個人／世界、上限、到期）與純函式一起做好，但本段沒有任何動作會產生線頭（線頭只能由事件結果產生，5B-2／5B-4）。全部可重播、確定性；`trpg.world` 不呼叫 LLM。

### 8.2 交付項目

1. **schema `src/trpg/content/world_events.py`**（`__all__` 明列、繼承 `ContentModel`、ID 用 `ID_PATTERN`、錯誤訊息繁中並指出 ID）：

   ```python
   SolutionKind = Literal[
       "combat",  # 戰鬥（護送、撤離、不殺目標等寫在 note_zh）
       "situation",  # 情境判定（9.6.4）；attributes 是允許的屬性
       "parley",  # 交涉（付錢、給材料、換物）
       "abandon",  # 放棄
       "opportunity",  # 機遇（18.4 #12：帶特定技能靠近；條件先寫在 note_zh）
   ]
   ThreadScope = Literal["personal", "world"]  # 9.6.7 #6


   class SolutionDef(ContentModel):
       kind: SolutionKind
       attributes: tuple[Attribute, ...] = ()  # 只有 situation 可填，且必填 1～3 個、不重複
       note_zh: str = ""  # 18.4 括號裡的說明（「找安全路」「護送戰」「付錢」）


   class ThreadDef(ContentModel):
       id: str
       text_zh: str  # 18.4「線頭」欄
       scope: ThreadScope = "personal"
       npc: str | None = None  # 相關 NPC 人設卡
       hints_location: str | None = None  # 指向的隱藏地點（必須 hidden 且 reveal 含 quest_clue）
       on_expire_zh: str = ""  # 到期結局（18.4 表下兩例；空＝淡出）


   class EventSkeletonDef(ContentModel):
       id: str
       number: int  # 18.4 編號（對照用；≥ 1，同區不重複）
       who_zh: str
       want_zh: str
       obstacle_zh: str  # 18.4 寫「—」的存空字串
       stakes_zh: str
       locations: tuple[str, ...]  # 可能出現的地點（至少 1、不重複）
       day_phase: Literal["day", "night"] | None = None  # None＝不限
       weather: tuple[str, ...] = ()  # 空＝不限；不重複
       npcs: tuple[str, ...] = ()  # 相關 NPC 人設卡（18.5）
       solutions: tuple[SolutionDef, ...]  # 至少 1
       threads: tuple[ThreadDef, ...] = ()  # 事件結果可能留下的線頭
       follows: tuple[str, ...] = ()  # 能接的線頭 ID（9.6.7 #6「優先接線頭」；雲嶺先空）


   class EventSkeletonTable(ContentModel):  # content/world/events/<region>.yaml
       region: str
       skeletons: tuple[EventSkeletonDef, ...]


   class NpcCardDef(ContentModel):
       id: str
       name_zh: str
       role_zh: str
       location: str  # 所在地點 ID
       personality_zh: str
       speech_zh: str
       secret_zh: str  # 只給說書人用，不直接顯示給玩家
       hooks_zh: str  # 18.5「和線頭／任務的關係」


   class NpcCardTable(ContentModel):  # content/world/npcs/<region>.yaml
       region: str
       npcs: tuple[NpcCardDef, ...]


   class EventRules(ContentModel):  # content/world/event_rules.yaml
       frequency: EventFrequency  # per_step_permille、max_permille（0～1000）
       threads: ThreadRules  # personal_limit、world_limit（≥ 1）、expire_seconds（≥ 1）
   ```

   **單檔驗證**：骨架 ID、編號不重複；線頭 ID 檔內不重複；`follows` 不可含自己的線頭；NPC ID 不重複。
   **跨檔案** `world_event_problems(events, *, world_map, npcs, weather_ids, thread_ids) -> list[str]`、`npc_card_problems(npcs, *, world_map)`（排序）：`region` 要有地點圖；`locations`、NPC 的 `location`、`hints_location` 在該區地點圖；`hints_location` 是 `hidden` 且 `reveal` 含 `quest_clue`；`weather` 在 `weather.yaml`；`npcs`、線頭的 `npc` 在同區人設卡；`follows` 的線頭存在（任一區）。

2. **載入**（載入函式放 `world_events.py`，`library.py` 只加一個欄位與一行呼叫，減少和 5A-3 的衝突）：`ContentLibrary.world_event_content: WorldEventContent`，內含 `events: dict[str, EventSkeletonTable]`、`npcs: dict[str, NpcCardTable]`（鍵＝區域、檔名必須等於 `region`）、`rules: EventRules | None`。資料夾或檔案不存在＝空／`None`（舊測試的精簡 content 照常載入）。骨架 ID、線頭 ID、NPC ID **跨區也不可重複**。檔案加進 `library.files`。
3. **雲嶺內容**：`content/world/events/cloud_ridge.yaml`（8.3）、`content/world/npcs/cloud_ridge.yaml`（8.4）、`content/world/event_rules.yaml`（8.5）。檔頭註解來源（18.4、18.5，#111 待使用者確認）與開發 PM 自定的部分（ID、地點、時段、線頭範圍）。
4. **`trpg.world`**：
   - `state.py`：`EventTrigger`（`region`、`location`、`skeleton`、`candidates`（排序）、`follows_thread: str | None`、`weather`、`day_phase`、`at`）、`ThreadState`（`thread`、`skeleton`、`region`、`created_at`、`expires_at`）；`CharacterState` 加 `event_steps: int = 0`、`pending_event: EventTrigger | None = None`、`threads: tuple[ThreadState, ...] = ()`；`WorldState` 加 `threads: tuple[ThreadState, ...] = ()`。新欄位都有預設值，舊存檔照讀、格式版本不變。線頭依 `(created_at, thread)` 排序、同一線頭不重複。
   - `rng.py`：新串流 `STREAM_EVENT = "event"`。
   - `events.py`：`event_chance`、`event_candidates`、`roll_event`（8.6）。
   - `threads.py`：`active_threads`、`expired_threads`、`add_thread`（8.6）。
   - `actions.py`：事件 `event_check`（location、steps、chance_permille、roll、triggered）、`event_triggered`（`EventTrigger`）、`event_left`（skeleton、location）。
   - `step.py`：`_travel` 在遇敵擲骰之後、感知判定之前接事件擲骰。
5. **測試** `tests/content/test_world_events.py`、`tests/world/test_events.py`、`tests/world/test_threads.py`（8.7）；既有 `tests/world` 斷言 `rng_counters` 的地方補上 `event` 串流。
6. **完成報告** `docs/phases/Phase5B-1報告.md`：交付、schema 摘要、出現頻率規則、用了 18 的哪些內容、代決、待 PM 決定。

### 8.3 雲嶺事件骨架對照（18.4 → 資料；地點、時段、天氣是開發 PM 代決）

| # | `id` | `locations` | 時段／天氣 | `npcs` | 解法（kind〔屬性〕說明） | 線頭 `id` |
|---|---|---|---|---|---|---|
| 1 | `wounded_peddler` | `ferry_steps, bamboo_path` | — | | combat；situation〔wis〕找安全路；abandon | `peddler_owes_you`、`wolves_driven_down` |
| 2 | `lost_acolyte` | `rain_terraces, old_pine_altar` | — | `acolyte_xiaolian` | situation〔wis, int〕認路；combat 帶他走（護送戰） | `temple_quarrel` |
| 3 | `gang_toll` | `rain_terraces, cliff_gang_fort` | — | | combat；situation〔wil〕威嚇；parley 付錢 | `scarface_grudge`（npc `scarface`） |
| 4 | `pine_elder_go` | `old_pine_altar` | — | | situation〔int〕下棋；situation〔wil〕耐心 | `storm_night_fog` |
| 5 | `cliff_lingzhi` | `herb_valley` | — | | situation〔str, dex〕攀爬；abandon | `alchemist_owes_you` |
| 6 | `monks_dispute` | `mist_temple_gate` | — | `acolyte_xiaolian` | situation〔wil〕說服一方；situation〔wis〕看穿誰在說謊 | `temple_traitor` |
| 7 | `gang_deserter` | `cliff_gang_fort, herb_valley` | — | | combat 擋追兵；situation〔dex〕帶他躲藏 | `gang_fort_secret_door` |
| 8 | `possessed_hunter` | `crystal_rift, north_slope` | — | | combat 不殺獵人；situation〔wil〕喚醒 | `wraiths_from_rift` |
| 9 | `broken_ferry` | `ferry_steps` | — | | parley 給青竹節；situation〔int〕修理 | `ferryman_daughter` |
| 10 | `bear_den` | `winter_lake` | — | | combat；situation〔wis〕悄悄退出；abandon | `shards_under_den` |
| 11 | `crane_envoy` | `cloud_sea_bridge` | — | | situation〔wil〕說服；situation〔dex〕躲到掩體 | `temple_pass` |
| 12 | `storm_altar` | `old_pine_altar` | night／`rain` | | opportunity 帶「帶電」技能靠近；situation〔con〕硬撐 | — |
| 13 | `tomb_sword` | `sword_tomb` | — | | situation〔str〕拔劍；situation〔int〕解陣 | `swordsman_seeks_blade` |
| 14 | `shard_convoy` | `crystal_rift, sword_tomb` | — | | combat 撤離勝利條件；situation〔dex〕偷走 | `shards_to_ashen` |
| 15 | `poison_spring` | `herb_valley` | — | | situation〔con〕憋氣；situation〔int〕配解藥 | — |
| 16 | `tavern_storyteller` | `mist_ferry` | — | | situation〔wil〕文字回答＋用心清單 | `tavern_rumor` |
| 17 | `lantern_patrol` | `mist_ferry, ferry_steps, hunter_hut` | night | | combat；situation〔wis〕追蹤 | `missing_went_to_rift` |
| 18 | `fox_traveler` | `north_slope, winter_lake` | — | | parley；situation〔wil〕說服（狐族主角 +1） | `foxfire_guide`（`hints_location: crane_cliff`） |

- 線頭 `scope` 全部 `personal`（代決：18.4 沒標世界級；世界級影響所有人，先當個人較保守）。`scarface_grudge`、`temple_traitor` 帶 18.4 表下的到期結局。
- 雷雨＝天氣 `rain`＋`night`（`weather.yaml` 沒有雷雨；18.3「雷雨夜」）。
- 屬性：力量 `str`、敏捷 `dex`、體質 `con`、智力 `int`、感知 `wis`、意志 `wil`。

### 8.4 雲嶺 NPC 人設卡對照（18.5 → 資料）

| NPC | `id` | `location` |
|---|---|---|
| 渡婆婆（鎮長） | `granny_du` | `mist_ferry` |
| 柳掌櫃（商人） | `shopkeeper_liu` | `mist_ferry` |
| 青崖道長（技能導師） | `daoist_qingya` | `mist_temple_gate` |
| 阿岳（獵戶，劇情夥伴） | `hunter_ayue` | `hunter_hut` |
| 小蓮（道童） | `acolyte_xiaolian` | `mist_temple_gate`（18.5「青霧觀」＝地點圖的青霧觀山門） |
| 霧鎖真人（觀主、Boss） | `mistlock_master` | `cloud_summit` |
| 斷崖幫二當家「疤面」 | `scarface` | `cliff_gang_fort` |
| 白狐「霜音」 | `frost_chime` | `crane_cliff` |

### 8.5 數值初值（`content/world/event_rules.yaml`；開發 PM 定、之後模擬定）

```yaml
frequency:
  per_step_permille: 150  # 距離上次事件每多走一步 +150‰
  max_permille: 600
threads:
  personal_limit: 5  # 9.6.7 #6「每人約 5 條」；Q11
  world_limit: 5  # 代決
  expire_seconds: 259200  # 現實 3 天（Q11）
```

### 8.6 規則

**事件擲骰**（`travel` 抵達後，在遇敵擲骰之後、感知判定之前；`event_rules` 為 `None` 或該區沒有骨架檔時整段跳過、不耗亂數）：
1. 角色身上有 `pending_event` 時先清掉，發 `event_left`（走開＝作罷；代決 5B1-4）。
2. `steps = event_steps + 1`；`chance = min(max_permille, per_step_permille × steps)`。
3. `event` 串流取一個 `Rng`，**一律** 擲 `roll = randint(0, 999)`（亂數消耗固定）。
4. 候選＝目前區域的骨架中 `location ∈ locations`、`day_phase` 符合（`None` 不限）、`weather` 含當下 `weather_at`（空不限）者，依 ID 排序。
5. 觸發＝`roll < chance` 且 **這一步沒有遇敵**（戰鬥優先）且候選非空。
6. 觸發時：優先候選＝`follows` 含任一有效線頭（角色個人線頭＋世界線頭中 `expires_at > now` 者）的骨架；有就從優先候選挑，否則從全部候選挑（同一個 `Rng` 的 `choice`，序列依 ID 排序）。`follows_thread`＝被接上的線頭（多個時取 ID 排序第一個）。寫入 `pending_event`、`event_steps = 0`，發 `event_triggered`。
7. 沒觸發：`event_steps = steps`。
8. 事件 **不擋** 移動與紮營（解法在 5B-2／5B-4）。LLM（5B-3）只能從 `candidates` 換骨架，沒有 LLM 時用引擎挑的 `skeleton`（3.1 降級）。

**線頭**（純函式；本段沒有動作會呼叫 `add_thread`）：
- 有效＝`expires_at > now`；`expired_threads` 回傳已到期者（給 5B-4 處理到期結局）。
- `add_thread(threads, thread_id, skeleton, region, now, *, limit, expire_seconds) -> (threads, pushed_out)`：先丟掉已到期者以外不動；同 ID 已有效 → 不變；有效數已達上限 → 最舊的（`created_at`、ID 排序）提前結束，放進 `pushed_out`；新線頭 `expires_at = now + expire_seconds`。
- 個人線頭存 `CharacterState.threads`、世界級存 `WorldState.threads`（依 `ThreadDef.scope`），上限分別是 `personal_limit`、`world_limit`。

### 8.7 測試

| 檔案 | 內容 |
|---|---|
| `tests/content/test_world_events.py` | 載入雲嶺：18 個骨架（編號 1～18 各一）、8 張人設卡、`event_rules`；跨檔案問題為空；`foxfire_guide` 指向 `crane_cliff`；壞資料逐條錯誤：骨架 ID 重複、編號重複、線頭 ID 重複、situation 沒屬性、combat 有屬性、屬性重複、未知地點、未知天氣、未知 NPC、`hints_location` 不是隱藏或不含 `quest_clue`、`follows` 未知、檔名不等於 region、跨區 ID 重複；沒有 world 資料夾＝空、`event_rules=None` |
| `tests/world/test_events.py` | 機率公式與上限；`event_rules=None` 不耗亂數；必觸發時產生 `EventTrigger`、骨架在候選內、候選依地點／時段／天氣篩；夜晚才有 `lantern_patrol`；遇敵那一步不觸發但照擲；沒觸發時 `event_steps` 累加、觸發後歸零；有 `pending_event` 時移動發 `event_left`；`follows` 優先；同輸入同結果 |
| `tests/world/test_threads.py` | 有效／到期；上限擠掉最舊；同 ID 不重複；排序；存檔往返（新欄位）；舊存檔（沒有新欄位）照讀 |

### 8.8 驗收

- `uv run pytest -q tests/world tests/content/test_world_events.py tests/content/test_world_map.py tests/test_architecture.py -n 8 --timeout=1800` 通過；交件前加跑 `tests/cli`（`-m "slow or not slow"`）。
- `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 通過；`C901` ≤ 15。
- `uv run trpg content check` 列出三個新檔的摘要。

### 8.9 不做的事

- 不做情境判定、解法結算、獎懲、事件結果、線頭的產生與到期結局（5B-2、5B-4）；不做 LLM 挑骨架、填角色、旁白（5B-3）；不做好感度、任務、酒館傳聞內容（5B-4）。
- 不改 5A-3 的敵人與遭遇表、不改地點圖；不做 API、前端。
- 不自己補 18 號文件沒有的骨架、NPC、線頭；地點與時段以外的不確定處照最保守做法並列「待 PM 決定」。

### 8.10 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5B1-1 | 骨架出現的地點、時段、天氣（18.4 沒寫） | 8.3 表，依 18.3「內容」欄與骨架文字推定；改了只動 content |
| 5B1-2 | 出現頻率依「距離上次事件的步數」線性增加，150‰／步、上限 600‰；遇敵那一步不出事件；城鎮也會出（說書人、燈籠隊） | 9.6.7 #6 只寫「依移動步數與種子」 |
| 5B1-3 | 引擎挑一個預設骨架＋列出候選；LLM（5B-3）只能在候選中換 | 9.6.7 #6「LLM 依世界狀態挑骨架」＋「LLM 不能自己多生事件」 |
| 5B1-4 | 事件不擋移動；離開地點＝事件作罷（`event_left`） | 解法在 5B-2；不擋才不會在 5B-2 前卡住 5A-5 試玩 |
| 5B1-5 | 線頭全部 `personal`；世界級上限也 5 條；到期 3 天（現實秒數）；滿了擠掉最舊 | Q11、9.6.7 #6「約」 |
| 5B1-6 | 解法種類加 `opportunity`（機遇），條件先寫文字 | 18.4 #12 |
| 5B1-7 | 情境判定解法的屬性照 18.4 填 1～2 個（9.6.4 模板「2～3 種」是 5B-2 情境模板的事） | 5B-2 再定骨架解法和情境模板的對應 |
| 5B1-8 | 新欄位有預設值、存檔格式版本不升 | 2.5；加欄位不破壞舊檔 |
