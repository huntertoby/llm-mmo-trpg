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
| 5A-ART1 | 敵人外觀移植①：異形畫法（`docs/art/敵人外觀.md` 第 3 節；美術 PM 代決 9 項待使用者確認，見 `docs/美術PM交接.md` 第 6 節） | 5A-3 | 1 h | 可與 5A-4 平行（只動 `client/`） |
| 5A-ART2 | 敵人外觀移植（美術 PM 已改成 4 小段、約 2.5 段，見 `docs/art/敵人外觀.md` 第 3 節；做到時照該節重拆）②③：精英與頭目標記、修士與盜賊外觀資料（敵人名稱與數量以玩法 PM 筆記《玩法PM-敵人清單》為準） | 5A-3、5A-ART1 | 0.75 h | 可與 5A-5 平行 |

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

## 6. 之後各段規格

（5A-1 驗收後補上 5A-2。）
