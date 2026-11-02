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
| Q10 | 用心清單、種族加值的「方法分類」清單（9.6.4 只給例子；各族清單「大世界開發時定」#89） | 規則 | 玩法 PM 代決 | 只用 9.6.4 表列出的方法；種族加值先只做狐族說服、欺騙（18 事件 18 用到） | 5B-1b | 5B-1 補資料（玩法 PM 2026-11-02，18 18.4 末段「補充」，`6f66287b`）：12 個骨架的 follows 對照表、世界級線頭（霧魅從裂痕湧出、碎片被送往灰燼荒原）、新骨架 19～21（阿岳的請託、失控的丹爐、霜音的謎）；19～21 的情境模板（19 感知／敏捷 DC 12、20 體質／智力 DC 13、21 意志／智力 DC 13）與既有模板加敏捷、體質（骨架 9、10、13、19 加敏捷；2、8、17 加體質；`5cbda759`） | 5B-1 | 0.5 h | 可與 5A-M1 平行 |
| 5B-2 |
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
| 5A-6 | 大世界成長接點（玩法 PM 2026-11-02）：主角技能階級照 07 7.6（1～3 級 1 階、4～7 級 2 階、8～10 級 3 階；原型 `offer_tier_by_level` 只留 roguelite）、配點、靈感與閃現、重閃、溶掉、傳承、立誓的引擎接點 | 5A-4 | 1.5 h | 可與 5A-5 平行 |
| 5A-6b | 5A-6 收尾（玩法 PM 代決 2026-11-03）：先手只影響第 1 輪（先手方單位第 1 輪全部排最前，第 2 輪起照正常先攻；敵人先手同）；開場 debuff 不擲抵抗、持續最多 2 回合（引擎，`LOG_FORMAT` 照慣例） | 5A-6 | 0.5 h | 可與 5A-SIM 平行 |
| 5A-7 | 新世界動作的 API 與前端：配點、重配、閃現（待選）、溶掉、傳承、立誓、`first_team`／`hero_statuses`／新事件的中文呈現；最近一次戰鬥結果留在角色上（5A-5 待決 1） | 5A-6 | 1.5 h | 可與 5A-SIM 平行 |
| 5A-SIM | 練等手感與經驗曲線模擬（代決初值）：同等級主角＋2 隊友打該地點遭遇勝率 ≥ 85%、結束剩 40～70% HP，高 2 級約一半；經驗來源比例 一般 1／精英 3／任務鏈一步 3／主線一步 5／情境成功 0.5（部分 0.25）／隱藏地點 2／懸賞 4；每天約 3 小時，第 3 天 5 級、第 6 天 8 級、第 7～8 天 10 級；精英首殺 +1 靈感。差太多再調敵人成長倍率 | 5A-4 | 1 h | 可與 5A-5 平行 |
| 5A-SIM2 | 5A-SIM 套用（玩法 PM 代決 2026-11-03）：隊友（標準隊友、傭兵、影子）照主角等級成長；敵人成長維持（HP +5%／級、屬性 +2）；經驗門檻方案 B（1 份＝100×(1＋10%×(地點建議等級−1))；2～10 級累計 950／3800／8600／14350／20200／26050／31950／37800／43650）；戰鬥依一般／精英給、情境判定 0.5／0.25 份；雲海吊橋陣容最多 1 名遠程、寒湖石背熊只出現在 4 級以上陣容（其他換霧狼），兩處同等級約 75% 以上；套用後重量 | 5A-SIM | 1 h | 可與 5A-M1 平行 |
| 5A-M1 | 引擎機制①（玩法 PM 2026-11-02，5A-3 待決）：蓄力強招預告、死亡時留下表面、開場隱蔽、同門相護；做好後把雲嶺替代品換成正式機制（只改 content） | 5A-4 | 1.5 h | 可與 5A-ART 平行 |
| 5A-M1b | 5A-M1 收尾（玩法 PM 代決 2026-11-03）：沉默可打斷法術型蓄力強招（武器技型照舊只吃倒下、暈眩、冰凍）；單位卡加「特性」欄（招牌被動、反應、精英詞綴，#82）。不做帶電表面、九轉回天維持 3×3 | 5A-M1 | 0.75 h | 可與 5B-3 平行 |
| 5A-M2 | 引擎機制②：陣法範圍加成（≤ 3 格）、把傷害分給相鄰同門 | 5A-M1 | 1 h | — |
| 5B-M3 | 引擎機制③：三方混戰（排在 5B 主線第 1 章之前） | 5A-M1 | 1 h | — |
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
| 5B-5 | 前端：事件卡、情境判定輸入（第一次送出即定案、列出持有線索可點選引用）、NPC 對話、任務日誌、線頭列表；路由接說書人（travel 觸發事件後送 `event_story`、聊天端點）；大世界自己的 LLM 開關（預設跟著伺服器設定，玩法 PM 2026-11-03）；隱藏地點揭露後名稱可公開，揭露前用提示語而非「某處」（玩法 PM 2026-11-03） | 5B-3、5B-4 | 1.5 h | 否 |

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

## 7. 5A-3 詳細規格：雲嶺敵人內容與遭遇表

> 給實作 agent。只動 `content/units/`（新增檔，不改既有）、`content/world/enemies.yaml`（新）、`content/world/encounters/`（新）、`src/trpg/content/world_enemies.py`（新）、`src/trpg/content/world_encounters.py`（新）、`src/trpg/content/library.py`（載入）、`src/trpg/world/encounters.py`（新）、`tests/content/`、`tests/world/`、CLI 快照（`trpg content check` 變了才重產）。**不做** 開戰接線（5A-4）、前端與外觀（5A-ART；新範本不寫 `doll`）、Boss 霧鎖真人與階段機制（5F-2）。不動 `content/skills/` 既有技能、`src/trpg/skillgen/`、引擎、roguelite、既有單位範本與地圖。
> 依據：18 18.2.1～18.2.2、18.3「內容」欄、18.7.4（懸賞「北坡狼王」）；09 9.6.6（家族、中立族群、變體與精英詞綴是 content 資料、混族、遠程上限、營地混精英：開戰前看得到、強度以建議等級為準、一場最多 1 名）；05 敵人範本與 AI 行為模式（`content/ai_profiles.yaml`）；本檔 0.2 Q5、2.4、6.4（`EncounterResult`）。

### 7.1 目標

雲嶺的敵人能被「查表 → 陣容 → 單位範本」產生：地點 → 遭遇表 → 陣容（含變體、營地混精英），陣容裡每個名字都解析得到合法的 `UnitTemplate`，能直接放進現有戰鬥引擎打完一場。全部用 **現有** 原語、技能、反應、標籤與 AI 行為模式；引擎沒有的招牌機制照最保守替代並列代決（7.6）。

### 7.2 交付項目

1. **敵人範本 `content/units/*.yaml`**（17 個新檔，格式同 `bandit*.yaml`；不寫 `doll`；屬性、HP、護甲是初值，不做平衡模擬）。對照表見 7.3。
2. **精英詞綴與元素變體 `content/world/enemies.yaml`** ＋ schema `src/trpg/content/world_enemies.py`（`EnemyVariantDef`、`EliteAffixDef`、`WorldEnemies`）：
   - **變體** `EnemyVariantDef`：`id`、`base`（單位範本 ID）、`name_zh`、`theme`（外觀用的元素標記：9 種元素＋`water`，5A-ART 用；純顯示）、`weapon: str | None`（換武器）、`skill_swaps: dict[str, str]`（舊技能 → 新技能，鍵必須在 base 的 `skills` 裡）。`apply_variant(base, variant) → UnitTemplate`：ID、名稱換掉，換武器與技能，其餘照 base。
   - **精英詞綴** `EliteAffixDef`：`id`、`name_zh`（「再生的」）、`add_skills`（既有技能 ID）、`add_reactions`（反應規則；範本沒寫 `reactions` 時先展開成 `reactions.yaml` 的 `default_rules` 再加）、`hp_permille`（HP 倍率，初值 1500）、`weapon_classes`（空＝不限；例：狂暴的只限近戰）。`apply_affix(template, affix, default_rules) → UnitTemplate`：ID＝`<範本>_<詞綴>`、名稱＝`<詞綴名><範本名>`、加 `elite` 標籤、HP × 倍率（捨去，至少 1）、加技能與反應規則。`affix_problem(...) → str | None`：武器大類不符、範本已是精英、技能已裝備、加上後超過欄位上限（`unit_skill_problems`）時不可套用。
   - 載入時：變體的 base、武器、技能存在；套用後的範本通過 `unit_skill_problems`；變體 ID 不可和單位範本 ID 撞；詞綴的技能與反應存在。
3. **遭遇表 `content/world/encounters/cloud_ridge.yaml`** ＋ schema `src/trpg/content/world_encounters.py`（`EncounterTable`；一區一檔，檔名＝`region`）：

   ```yaml
   region: cloud_ridge
   ranged_cap: 2              # 每場遠程敵人上限（18.2.1、9.6.6；Q5）
   camp_elite_permille: 100   # 一般營地混進 1 名精英的機率（9.6.6；Q5 初值）
   affixes: [regenerating, mist_veiled, heart_linked, berserk]   # 本區常見詞綴（18.2.1）
   groups:                    # 陣容：單位範本 ID 或變體 ID，2～4 名（3 人隊伍；地圖敵方起始區 4 格）
     - {id: sect_patrol, name_zh: 修士巡邏, units: [sect_acolyte, sect_acolyte, sect_swordsman, sect_alchemist]}
   locations:
     - location: rain_terraces
       groups: [{group: sect_patrol, weight: 1}]
     - location: north_slope
       groups: [...]
       elite: {unit: mist_wolf, affix: berserk}   # 精英巢穴固定的精英（懸賞「北坡狼王」）
   ```

   **單檔驗證**：`ranged_cap ≥ 0`、`0 ≤ camp_elite_permille ≤ 1000`；陣容 ID 不重複、2～4 名；地點不重複；每個地點至少 1 個陣容、權重 ≥ 1、陣容存在；有 `elite` 的地點，陣容＋固定精英 ≤ 4 名；`affixes` 不重複。
   **跨檔案檢查** `encounter_table_problems(...)`：
   - `region` 有地點圖；地點都在地點圖；**地點圖上遇敵機率 > 0 的地點（town、gate 以外）都要有表**（5A-2 對這些地點擲遇敵）。
   - 陣容裡的名字是單位範本（非召喚物）或變體；`affixes` 在 `enemies.yaml`。
   - **遠程上限**：每個陣容（含固定精英）的遠程數 ≤ `ranged_cap`。遠程＝武器大類 `ranged`，或範本帶 `ranged` 標籤（符籙師用法器，但 18.2.1 寫「都算遠程」）。
   - **精英**：每個陣容最多 1 名 `elite` 標籤的單位；`elite` 欄只有 `elite_lair` 可填、`elite_lair` 必填，且它的陣容不可再含精英；固定精英的詞綴必須可套用到該單位。
   - `camp` 地點的每個陣容至少有 1 名可以套用本區某個詞綴的成員，或陣容本身已有精英。
4. **載入**（`library.py`）：`ContentLibrary.world_enemies: WorldEnemies | None`（檔案不存在＝`None`）、`world_encounters: dict[str, EncounterTable]`（資料夾不存在＝空，鍵＝`region`）；有問題 → `ContentError`（指出檔案）。`trpg content check` 會列出兩個新檔的摘要。
5. **遭遇查詢 `src/trpg/world/encounters.py`**（純函式，可重播）：
   - `EncounterLineup`（`region`、`location`、`group`、`members: tuple[LineupMember, ...]`；`LineupMember(unit, affix: str | None)`）。
   - `roll_lineup(library, encounter: EncounterResult) -> EncounterLineup`：亂數 `Rng(fnv1a64(f"{battle_seed}:lineup"))`（`battle_seed` 已由世界 `battle` 串流衍生；不動角色計數）。① 依權重抽陣容；② `elite_lair`：固定精英放第一個；③ `camp` 且陣容沒有精英：擲 `randint(0, 999) < camp_elite_permille` → 從「可套用至少一個本區詞綴」的成員中均勻抽 1 名、再從可套用的詞綴中均勻抽 1 個（升級原成員，不增加人數、不加等級，9.6.6「強度以建議等級為準」）。其他地點種類不混精英。
   - `lineup_templates(library, lineup) -> tuple[UnitTemplate, ...]`：解析變體、套用詞綴，回傳可直接放進 `UnitSpawn` 的範本（依陣容順序）。
6. **測試**（7.5）與 **完成報告** `docs/phases/Phase5A-3報告.md`（交付、敵人精簡表、遭遇表摘要、smoke 結果、用了 18 的哪些內容、代決、待 PM 決定）。

### 7.3 雲嶺敵人對照（18.2 → 範本；開發 PM 取 ID）

標籤：修士一律 `[humanoid, sect]`、野獸 `[beast]`、源晶造物 `[construct]`；另列的標籤附加。技能都是 `content/skills/` 既有的。

| 18.2 | `id` | 武器 | AI | 技能（概念對照） | 其他 |
|---|---|---|---|---|---|
| 青霧道童 | `sect_acolyte` | `totem_staff` | `support` | `skill_radiant_mend`（清心） | |
| 持劍弟子 | `sect_swordsman` | `one_handed_sword` | `brute` | `skill_crossing_slash`（劍勢連斬）、`skill_stand_firm`（同門相護替代） | 反應：預設＋`stand_firm`（`ally_hit_adjacent`） |
| 符籙師 | `sect_talisman_caster` | `totem_staff` | `archer` | `skill_frost_shackle`（定身符）、`skill_static_palm`（雷符） | `ranged` 標籤 |
| 煉丹師 | `sect_alchemist` | `totem_staff` | `support` | `skill_sanctuary`（回春丹，群體治療）、`skill_poison_mist`（丹爆毒霧） | |
| 護法武僧 | `sect_warrior_monk` | `fist` | `guard` | `skill_parry_riposte`（金剛身）、`skill_rampart_jeer`（嘲諷）、`skill_stand_firm` | 反應同持劍弟子；`steadfast` |
| 劍陣弟子 | `sect_array_disciple` | `one_handed_sword` | `flanker` | `skill_shoulder_strike`（劍陣：相鄰同伴時加傷） | |
| 霧行者 | `sect_mist_walker` | `dagger` | `assassin` | `skill_shadow_backstab`（霧襲）、`skill_rx_slip_away`（受擊隱蔽） | 反應：預設＋`rx_slip_away`（`hit_by_attack`） |
| 雲鶴使 | `sect_crane_archer` | `bow` | `archer` | `skill_high_ground_shot`（高處射擊）、`skill_rng_hawkeye_mark`（鶴唳標記） | 遠程 |
| 傀儡師 | `sect_puppeteer` | `totem_staff` | `cunning` | `skill_summon_bomb_puppet`（木傀儡，會爆裂） | |
| 陣眼石靈 | `sect_array_stone` | `fist` | `idle` | — | 速度 0、`reactions: []`、`immovable` |
| 青霧執事（精英） | `sect_steward` | `totem_staff` | `support` | `skill_sanctuary`、`skill_renewal`、`skill_steady_breath`（每回合結束回血） | `elite` |
| 霧狼 | `mist_wolf` | `fangs` | `flanker` | `skill_twin_fang` | |
| 山豹 | `mountain_leopard` | `talons` | `assassin` | `skill_tiger_charge`（撲擊） | |
| 石背熊 | `stoneback_bear` | `talons` | `brute` | `skill_quake_topple`（震地擊倒） | `steadfast` |
| 雷羽鷹 | `thunder_hawk` | `talons` | `flanker` | `skill_plunging_strike`（俯衝）、`skill_static_palm`（帶電） | `flying` |
| 霧魅 | `mist_wraith` | `shade_blades` | `assassin` | `skill_blink`（隱蔽）、`skill_rx_dread_glare`（碰到就迷惑→恐懼） | 反應：預設＋`rx_dread_glare`（`enemy_enters_adjacent`） |
| 碎晶傀儡 | `shard_golem` | `stone_fist` | `brute` | `skill_rock_smash` | 雷抗 |

盜賊沿用既有 `bandit`、`bandit_archer`、`bandit_shieldbearer`、`bandit_captain`（雲嶺配色是 5A-ART）。實作時若某個技能與武器、欄位不相容（載入檢查），換成同概念的既有技能並在報告列出。

**變體**（18.2.1）：`thunder_talisman_caster` 雷符師（`lightning_staff`；`frost_shackle → spark_chain`）、`frost_crane_archer` 冰鶴使（`rng_hawkeye_mark → annotated_frost`，命中緩速）、`water_alchemist` 水煉丹師（`poison_mist → splash_flask`，造水）。
**詞綴**（18.2.1，`hp_permille: 1500`）：`regenerating` 再生的（＋`skill_steady_breath`）、`mist_veiled` 霧隱的（＋`skill_rx_slip_away` 與 `hit_by_attack` 反應）、`heart_linked` 連心的（＋`skill_soul_bond`）、`berserk` 狂暴的（＋`skill_berserker_rage`，限近戰）。

### 7.4 雲嶺遭遇表（初值；依 18.3「內容」欄與 18.2 陣容例）

| 地點 | 陣容 |
|---|---|
| 渡口石階（camp 1） | 盜賊 ×2＋盜賊弓手；盜賊 ×2＋盾衛 |
| 竹林小徑（camp 1～2） | 霧狼 ×3；盜賊＋霧狼 ×2（混族例） |
| 雨中梯田（camp 2） | 道童 ×2＋持劍弟子＋煉丹師（18 例）；盜賊 ×2＋持劍弟子＋道童（盜賊＋修士衝突，同一陣營） |
| 青霧觀山門（village 2） | 道童＋持劍弟子 ×2 |
| 獵戶小屋（village 2） | 霧狼 ×2＋山豹 |
| 斷崖幫寨（camp 3） | 盜賊＋盾衛＋盜賊弓手＋隊長；盜賊 ×2＋盜賊弓手＋霧狼 |
| 古松祭壇（altar 3） | 武僧＋符籙師＋霧行者（18 例） |
| 雲海吊橋（camp 3～4） | 劍陣弟子 ×3＋陣眼石靈（18 例）；持劍弟子＋雲鶴使＋道童＋煉丹師 |
| 藥師谷（ruin 4） | 煉丹師＋武僧＋傀儡師；山豹 ×2＋石背熊 |
| 丹爐洞（secret 5） | 青霧執事＋持劍弟子＋武僧＋道童；水煉丹師＋持劍弟子 ×2＋霧行者 |
| 北坡獵場（elite_lair 4～5） | 固定精英：狂暴的霧狼（北坡狼王）＋霧狼 ×3 |
| 冬湖（camp 4） | 冰鶴使＋石背熊＋霧狼；石背熊 ×2＋冰鶴使 |
| 劍冢（ruin 5） | 劍陣弟子 ×3＋霧行者；持劍弟子＋霧行者＋雷符師＋雲鶴使 |
| 源晶裂痕（anomaly 5） | 霧魅 ×2＋碎晶傀儡；盜賊＋盜賊弓手＋霧魅＋碎晶傀儡 |
| 鶴歸崖（secret 6） | 雷羽鷹 ×3＋雲鶴使；雷羽鷹 ×2＋石背熊 |
| 雲頂觀（boss 6） | 一般巡邏：劍陣弟子 ×2＋符籙師＋煉丹師（Boss 戰本身是 5F-2） |

權重一律 1（初值）；`camp_elite_permille: 100`。

### 7.5 測試

| 檔案 | 內容 |
|---|---|
| `tests/content/test_world_enemies.py` | 載入 17 個新範本、3 個變體、4 個詞綴；`apply_variant` 換武器與技能、ID 與名稱；`apply_affix` 的 ID、名稱、`elite` 標籤、HP 倍率、技能、反應（範本沒寫 `reactions` 時含 `default_rules`）；`affix_problem`（狂暴的不能套遠程、已是精英、已裝備）；壞資料（未知 base、swap 的鍵不在 base、未知技能、變體 ID 撞範本）→ 錯誤；沒有 `world/enemies.yaml` → `None` |
| `tests/content/test_world_encounters.py` | 載入雲嶺表；遇敵機率 > 0 的地點都有表；每個陣容遠程 ≤ 2、精英 ≤ 1、人數 2～4；各條驗證（未知單位、遠程超量、非 elite_lair 填 `elite`、elite_lair 沒填、陣容含 2 名精英、地點缺表、未知地點、詞綴不可套用）→ 錯誤；沒有 `world/encounters/` → 空 |
| `tests/world/test_encounters.py` | `roll_lineup` 確定性（同 `EncounterResult` 相同、不同種子會變）；陣容一定來自該地點的表；北坡獵場第一名是狂暴的霧狼；營地精英機率：`camp_elite_permille` 改 0 → 永不、1000 → 每場恰 1 名，且被升級的是原陣容成員、人數不變；非營地不混精英；`lineup_templates` 解析變體與詞綴、遠程 ≤ 2 |
| `tests/world/test_enemy_smoke.py` | **smoke**：每個陣容（含變體）＋每個詞綴（套在一個可套用的雲嶺單位上）用該地點的戰鬥地圖（沒有地圖的地點用 `dark_forest`）、3 名既有主角範本（`hero_fighter`、`hero_archer`、`hero_stormcaller`）、`max_rounds: 8`，`run_battle` 跑到 `state.ended`；並斷言 17 個新範本與 3 個變體都至少出場一次 |

### 7.6 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5A3-1 | 招牌反應「同門相護」（2 格內同門受擊時替他加護盾）：引擎沒有「替被攻擊的友方加護盾」的反應目標 | 前排（持劍弟子、護法武僧）帶既有反應技「挺身而出」（相鄰同門受擊時替他擋下＋自身護衛）；真正的同門相護待 PM 決定是否排引擎段 |
| 5A3-2 | 陣眼石靈「存在時同門護盾 +、打碎才解除陣法」、劍陣「≤ 3 格」、青霧執事「九轉回天」蓄力強招、碎晶傀儡「死後帶電碎片」、霧魅「迷惑」 | 沒有對應機制：石靈只做不動的高護甲物件；劍陣用「並肩斬」（相鄰同伴加傷）；執事用群體治療＋再生；碎晶傀儡只是近戰；迷惑以「恐懼」替代。全部列待 PM 決定 |
| 5A3-3 | 詞綴「霧隱的」（開場隱蔽 1 回合）、「連心的」（受傷分給相鄰同門）沒有對應機制 | 霧隱的＝受擊時隱蔽（`rx_slip_away`）；連心的＝「魂結」（方向相反：替同伴分擔）。列待 PM 決定 |
| 5A3-4 | 混族同陣營：三方混戰（9.6.6 D）需要第三陣營 | 本段所有敵人同一陣營；三方混戰待之後的引擎段 |
| 5A3-5 | 敵人強度不隨地點等級縮放（7.8「不縮放」），用陣容挑選區分強弱；精英＝原成員套詞綴（HP ×1.5），不加人數 | 數值是初值 |
| 5A3-6 | 遭遇陣容的亂數由 `battle_seed` 衍生（`"{battle_seed}:lineup"`），不另開角色串流 | 不改 5A-2 的角色計數；重播照 `EncounterResult` |
| 5A3-7 | 遠程的定義：武器大類 `ranged` 或範本帶 `ranged` 標籤 | 符籙師用法器，但 18 寫算遠程 |
| 5A3-8 | 營地混精英只限 `camp` 種類；`elite_lair` 固定精英；其他種類不混 | 9.6.6「一般營地」 |
| 5A3-9 | 一個陣容最多 4 名（地圖敵方起始區 4 格） | 3 人隊伍對 2～4 名 |

### 7.7 驗收

- `uv run pytest -q tests/content/test_world_enemies.py tests/content/test_world_encounters.py tests/world tests/content/test_loader.py tests/test_architecture.py -n 8 --timeout=1800` 通過。
- `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 通過；一場重播（`uv run trpg battle --map swamp --seed 7 --log-json …` ＋ `replay`）。
- 交件前跑 `tests/cli`（`-m "slow or not slow"`）；`trpg content check` 的快照變了照指示重產。

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

## 9. 5A-4 詳細規格：遇敵展開戰鬥與城鎮服務

> 給實作 agent。只動 `src/trpg/world/`、`src/trpg/content/world_rules.py`、`content/world/rules.yaml`（末尾加區塊，改動小）、`content/units/sect_talisman_caster.yaml` 與 `content/world/enemies.yaml` 的雷符師（追加 B）、`tests/world/`、受影響的 `tests/content/`。**不做** API、前端（5A-5）；不改 `trpg.engine`、`trpg.roguelite`（只匯入重用）、`trpg-run` 格式與戰鬥紀錄格式。
> 依據：09 9.6.2（遇敵展開的格子取自地點的地圖模板）、9.6.6（開戰前看得到陣容、可撤退、不扣任何東西；精英強度以建議等級為準）、9.6.7 #2（只有城鎮與營火完全回復、換技能）、#11（補給用完只能回城補）、#15（已清空、一段時間後重生）、9.6.2「城鎮之間用傳送點」、9.6.9 #98（野外全滅：回小鎮、HP 回滿、沒有戰利品、經驗不扣、下一場「疲憊」開場 HP 80%、打完一場就消失）、9.6.11 #113（耐力戰後回滿、法力只在營火與城鎮回滿、HP 不自動回）、#114（營火＝紮營，可換技能）；05 5.1「區域地圖池」（機制不動、只換 `region` 外觀）；07 7.6（換裝地點：主城、區域小鎮、營火；裝備欄上限；技能階級 1～3／4～7／8～10）、7.8（經驗、敵人不跟著玩家縮放、地點標建議等級）；本檔 2.1～2.4、6.4、7.2。
> **追加（開發 PM 轉玩法 PM 2026-11-02，#81 練等前提）**：A. 敵人範本照地點建議等級成長（和主角同樣的成長；範本＝1 級基準）；B. 符籙師改成純控制（定身符＋封符），雷符師保留雷符＋定身符。

### 9.1 目標

大世界一場遭遇從頭到尾可玩、可重播：**移動 → 遇敵 → 看陣容（可撤退）→ 戰鬥 → 勝負回寫**；城鎮可休息、換技能、傳送；營火（5A-2 的紮營）可換技能。戰鬥本身沿用原型引擎（`trpg.engine`）與 roguelite 的主角出場算法，戰鬥的步驟寫進世界動作日誌，重播時用同一份設定與種子重算勝負（第 2.4 節）。

### 9.2 交付項目

1. **世界動作**（`trpg.world.actions`，加進 `WorldAction` 判別聯集）：

   | 動作 | 欄位 | 條件（不合法拋 `WorldActionError`，狀態不變） |
   |---|---|---|
   | `retreat` | — | 有 `pending_encounter`；回到出發地點（`EncounterResult.from_location`；舊資料沒有時回本區小鎮），清掉遭遇；不扣補給、不擲骰（9.6.6「不扣任何東西」） |
   | `fight` | `steps: tuple[Step, ...]` | 有 `pending_encounter`；以 9.3 的設定與 `battle_seed` 開戰，依序套用 `steps`（引擎 `apply_step`），套用後戰鬥必須已結束；回寫見 9.4 |
   | `rest` | — | 在城鎮（`kind == "town"`）、沒有遭遇；HP、法力回滿、耐力滿、補給補到至少 `supplies.start`（9.6.7 #11「回城補」；代決 5A4-11）；免費 |
   | `loadout` | `skills: tuple[str, ...]` | 在城鎮或營火（`camped_at` 是目前地點）、沒有遭遇；只能裝擁有的技能（裝備＋`bench`）、不重複、欄位上限（roguelite `equip_problems`）；沒裝上的進 `bench`（排序） |
   | `teleport` | `region` | 沒有遭遇；在城鎮 → 目的區域的小鎮必須在 `visited_towns`；或在傳送點（`gate`）且 `gate_to == region`；目的區域要有地點圖；抵達目的區域的小鎮、記入 `visited_towns` |

2. **事件**：`retreated`（from、to）、`battle_started`（地圖、`region`、陣容、敵人等級、天氣、我方開場 HP、`fatigued`）、`battle_ended`（won、end_reason、rounds、hp、mana、xp_gained、level）、`leveled_up`（level、attribute_points）、`defeated`（回到的地點、HP）、`location_cleared`（location、respawn_at）、`rested`、`loadout_changed`、`teleported`（region、location）。

3. **狀態欄位**（全部有預設值，舊的 `trpg-char/1`／`trpg-world/1` 照樣讀得進來，格式字串不變）：
   - `EncounterResult.from_location: str | None = None`（5A-2 的移動填入出發地點）。
   - `CharacterState.bench: tuple[str, ...] = ()`（備用技能，同 `RunState.bench`，排序）、`fatigued: bool = False`、`attribute_points: int = 0`（升級給的未分配屬性點；分配介面在 5A-5 以後）、`visited_towns: tuple[str, ...] = ()`（到過的區域小鎮，記區域 ID，排序；`new_character` 記起始區）。

4. **開戰設定** `trpg.world.battle`（新）：
   - `encounter_setup(library, char) -> BattleSetup` 與 `encounter_lineup(library, char)`：5A-5 的 API 開戰與「看陣容」直接用；
   - `fight_battle(library, world, char, steps)`／`auto_steps(library, char)`（效用 AI 代打，測試與 smoke 用）。

5. **規則數值**（`content/world/rules.yaml` 末尾加，`WorldRules` 新欄位都有預設值）：

   ```yaml
   battle:                      # 5A-4（代決 5A4-*）
     max_rounds: 30             # 同原型
     xp_per_battle: 100         # Q8 初值；等級門檻沿用原型曲線（roguelite.yaml level_thresholds）
     fatigue_hp_permille: 800   # #98「開場 HP 80%」
     clear_kinds: [camp]        # 打贏後寫「已清空」的地點種類（9.6.7 #15「清掉的營地」）
     respawn_seconds: 1800      # 已清空到重生：遊戲內 1 天（現實 30 分鐘）
   enemy_growth:                # 追加 A
     attribute_points_per_level: 2
     skill_tier_by_level: [1, 1, 1, 2, 2, 2, 2, 3, 3, 3]   # 07 7.6
   ```

6. **追加 B（只改 content）**：`sect_talisman_caster` 技能改為 `skill_frost_shackle`（定身符）＋`skill_hush`（噤聲：沉默 1 回合，現成技能＝封符）；雷符師變體改 `skill_swaps: {skill_hush: skill_static_palm}`（＝定身符＋雷符；武器 `lightning_staff` 不變）。

7. **測試** `tests/world/`（9.6）與 **完成報告** `docs/phases/Phase5A-4報告.md`。

### 9.3 開戰（`encounter_setup`）

1. **地圖**：`EncounterResult.battle_map`；為 `None`（地點沒有戰鬥地圖：祭壇、遺跡、異象、Boss 據點）時，從該區 `map_pool` 的 archetype 裡的地圖（排除 `boss` archetype、依地圖 ID 排序）以 `Rng(fnv1a64(f"{battle_seed}:map"))` 均勻抽一張（代決 5A4-1）。
2. **換皮**：地圖的 `region` 不是遭遇的區域時，改成遭遇的區域，`look` 換成該區 `regions.yaml` 的預設外觀（機制不動，05 5.1；代決 5A4-2）。
3. **勝利條件**：地圖預設（全滅）；營地的勝利條件輪替之後再做（代決 5A4-3）。
4. **天氣**：`EncounterResult.weather`。
5. **我方**：主角（等級 HP 加成、`scaled_resources`、`level`，目前 HP／法力／耐力；疲憊時開場 HP ＝ min(目前, 最大 HP × 800‰)，至少 1）＋原型的 2 名標準隊友（`roguelite.yaml` 的 `companions`，滿狀態；5C-1 換成傭兵與影子；代決 5A4-4）。
6. **敵方**：`roll_lineup` → `lineup_templates` → **依等級成長**（追加 A）：
   - 等級 ＝ 地點的 `level_min`（代決 5A4-5）；1 級＝範本原樣。
   - 屬性：每級 +2，全部加在範本最高的屬性（同分取屬性順序 str、dex、con、int、wis、wil 的第一個；代決 5A4-6）。
   - HP：基礎 HP ＋ `level_hp_bonus`（同主角：每級 +5% 基礎 HP，`core.yaml` 的 `level_hp_permille`）。
   - 技能階級：`enemy_growth.skill_tier_by_level[等級]`；技能目前階級較低時用 roguelite 的 `at_run_tier` 重配成 `<原 ID>_t<階級>`（只升不降），反應規則引用的技能 ID 一併改名；重配的技能以 `Ruleset.with_skills` 加進本場規則包。
   - 範本的 `level` 欄位設為等級（召喚物依施放者等級成長）。
7. **種子**：`EncounterResult.battle_seed`。

### 9.4 勝負回寫（`fight`）

- **打贏**（`winner == ally`）：HP ＝ 主角戰後 HP（倒下但勝利以 1 HP 繼續，同原型）；法力照戰後（不回）；耐力回滿（#113）；經驗 ＋`xp_per_battle`，等級照原型門檻；升級時最大 HP／法力上限增加的量加到目前值（同 roguelite `with_hp_change`），每級 `attribute_points` ＋ `roguelite.attribute_points_per_level`；地點種類在 `clear_kinds` 時寫 `ClearedLocation(respawn_at = now + respawn_seconds)`（已有就更新）；清掉遭遇；疲憊消失。
- **沒打贏**（全滅或輪數上限，一律當全滅；代決 5A4-7）：回本區小鎮（代決 5A4-8：「最近的小鎮或營火」先只做小鎮）、HP 回滿、法力照戰後、耐力回滿；不給經驗、不扣經驗、背包裝備不掉；`fatigued = True`；清掉遭遇與 `camped_at`。
- 戰利品、精英獎勵、靈感點：5D／之後（待 PM 決定）。
- **已清空的營地**：移動到已清空且未重生的地點時遇敵機率為 0（擲骰照擲，亂數消耗不變；代決 5A4-9）。

### 9.5 重播與確定性

- `fight` 的 `steps` 寫在世界動作日誌（`trpg-wlog/1` 不變，多一種動作）；重播時由「角色快照＋遭遇＋內容庫」重建同一份設定、同一個種子、套用同樣的步驟，得到逐位元相同的戰鬥結果與回寫。戰鬥沒結束或步驟不合法 → `WorldActionError`。
- `trpg.world` 內不讀時間、不用 `random`、`uuid4`、`hash()`；亂數只來自 `battle_seed` 與世界串流。

### 9.6 測試（`tests/world/`）

| 檔案 | 內容 |
|---|---|
| `test_battle_setup.py` | 有地圖的地點用遭遇的地圖、沒有地圖的地點從區域地圖池抽（確定性、archetype 在池內）、換皮成 `cloud_ridge`；天氣；我方＝主角＋2 名隊友；疲憊開場 HP 80% |
| `test_enemy_growth.py` | 1 級不變；5 級：最高屬性 +8、HP ＋20%、技能升到 2 階（ID `_t2`、反應改名）、`level`；`level_min` 取值；規則包含重配技能 |
| `test_fight.py` | 打贏：經驗、升級、耐力滿、HP 不回、法力不回、清掉遭遇、營地已清空與重生、已清空不遇敵；輸：回小鎮、HP 滿、疲憊、下一場開場 80% 後消失；沒結束、沒遭遇、步驟不合法 → 錯誤 |
| `test_town.py` | 撤退回出發地點且不扣東西；休息（只在城鎮）；換技能（城鎮、營火可以，野外不行；不能裝沒有的、超過欄位）；傳送（城鎮到去過的小鎮、傳送點到 `gate_to`、沒地點圖或沒去過 → 錯誤） |
| `test_replay.py`（加） | 移動 → 遇敵 → 戰鬥 → 回寫 → 休息的日誌重播兩次逐字相同；寫出再讀回相同 |

### 9.7 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5A4-1 | 沒有戰鬥地圖的地點遇敵用哪張圖 | 區域地圖池（非 Boss）以 `{battle_seed}:map` 均勻抽 |
| 5A4-2 | 換皮時地圖原本的單張 `look` 覆寫 | 換成該區預設外觀（原覆寫是給原區的） |
| 5A4-3 | 營地的勝利條件輪替（9.6.2） | 先用地圖預設（全滅） |
| 5A4-4 | 3 人隊伍的隊友（#97） | 5C-1 前用原型的 2 名標準隊友 |
| 5A4-5 | 敵人等級取地點等級範圍的哪一點（追加 A） | `level_min` |
| 5A4-6 | 敵人每級 +2 屬性加在哪 | 全部加在範本最高的屬性 |
| 5A4-7 | 輪數上限沒打完 | 當全滅處理 |
| 5A4-8 | 全滅「回最近的小鎮或營火」 | 先只回本區小鎮 |
| 5A4-9 | 已清空的地點遇敵 | 機率 0（擲骰照擲） |
| 5A4-10 | 已清空寫入與重生（9.6.7 #15「一段時間」） | 只有 `camp` 種類；遊戲內 1 天（1800 秒）後重生；數值在 `rules.yaml` |
| 5A4-11 | 城鎮休息的費用與補給 | 免費；補給補到至少 `supplies.start` |
| 5A4-12 | 傳送點 | 城鎮到「去過的」其他區小鎮；傳送點（gate）到 `gate_to` 區的小鎮 |
| 5A4-13 | 經驗與等級 | 每場 100、沿用原型門檻（Q8）；升級屬性點先累積在 `attribute_points` |
| 5A4-14 | 符籙師的「封符」（追加 B） | 現成的 `skill_hush`（噤聲：沉默 1 回合） |

### 9.8 驗收

- `uv run pytest -q tests/world tests/content tests/test_architecture.py -n 8 --timeout=1800` 通過；交件前 `tests/cli`（`-m "slow or not slow"`）。
- `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 通過；一場原型重播（`trpg battle --map swamp --seed 7 --log-json` ＋ `replay`）；一段世界日誌重播測試。

### 9.9 不做的事

- API、前端、地點圖畫面（5A-5）；傭兵與影子（5C）；戰利品、材料、精英獎勵（5D）；屬性點分配、閃現、重閃、溶掉、傳承、立誓、主角升階重配（之後的段，見報告待 PM 決定）。
- 不改 `trpg-run`、戰鬥紀錄（`LOG_FORMAT`）格式；不改引擎與 roguelite。

## 10. 5B-2 詳細規格：情境判定引擎

> 給實作 agent。只動 `content/world/situations/`（新）、`content/world/situation_rules.yaml`（新）、`content/world/events/cloud_ridge.yaml`（#12 機遇條件一行）、`src/trpg/content/world_situations.py`（新）、`src/trpg/content/world_events.py`（`SolutionDef.requires_keyword`、載入時一併載入情境模板）、`src/trpg/content/library.py`（多傳狀態、關鍵字、種族 ID，一行）、`src/trpg/world/`（新增 `situations.py`；`state.py`、`actions.py`、`rng.py`、`step.py` 小改）、`src/trpg/llm/situation.py`（新：提議 prompt、schema、提議流程）、`tests/content/`、`tests/world/`、`tests/llm/`、CLI 快照（`trpg content check` 變了才重產）。**不做** 說書人敘述與骨架挑選（5B-3）、放棄／交涉／戰鬥解法與任務（5B-4）、機遇的獎勵、API、前端（5B-5）、戰鬥套用下一場 buff／debuff（5A-4 之後）。不動 `content/skills/`、`src/trpg/skillgen/`、引擎、roguelite。
> 依據：09 9.6.4（模板、`<player_input>`、第一次送出即定案、LLM 提議 ±2、劣勢、d20、三段結果、獎懲有預算上限、用心清單最多 +2、種族 +1、公平原則、寫入事件日誌）、9.6.7 #3～#6（線頭由事件結果產生、獎勵照地點建議等級的預算表）、9.6.11 #115（方法 12 類、10 族 +1）；10 第 10、11 節（結構化輸出、pydantic、prompt 版本、LLM 輸出寫進事件日誌、重播不呼叫 LLM、玩家輸入當資料）；18 18.4（解法屬性；表末「補充」：機遇「帶電技能」、「斷崖幫寨的暗門」給骨架 14 偷竊優勢、模板第 2 種屬性的補法）；本檔 2.1、2.3、2.4、第 8 節。

### 10.1 目標

骨架的「情境判定」解法變成可以結算的資料：**情境模板**（content）＋ **LLM 提議**（pydantic 驗證）＋ **引擎判定**（`trpg.world`，純函式、可重播）。

```
外層（之後的 trpg.api／narrative）        trpg.llm.situation                       trpg.world.situations
pending_event ＋ 模板 ───────────────▶  messages（資料區＋<player_input>）
situation_facts(...)（引擎算的事實）──▶  LLMClient.complete(json_schema)
                                        clean → JSON → SituationProposal（pydantic）
                                        proposal_problems（靜態）→ 有錯帶 <errors> 重試
                                        連不上／用盡 → default_proposal（降級）
SituationAction(模板, 玩家文字, 提議, 來源, prompt 版本) ─────────────────────▶ world_step
                                                                               合法性檢查（不合法拋錯、狀態不變）
                                                                               逐筆核對用心清單（核對不到不算）
                                                                               d20（優勢／劣勢）＋修正 vs DC
                                                                               三段結果 → 獎懲（預算內）、線頭
                                                                               清掉 pending_event、寫事件
```

`trpg.world` 不匯入 `trpg.llm`：提議 schema（`SituationProposal`）與靜態檢查放在 `trpg.content.world_situations`（純資料），`trpg.llm` 和 `trpg.world` 都從那裡匯入（2.3）。提議隨動作寫進世界動作日誌（`trpg-wlog/1`），**重播照紀錄、不再呼叫 LLM**（10 第 10 節、2.1）。

### 10.2 交付項目

1. **schema `src/trpg/content/world_situations.py`**（`__all__` 明列、`ContentModel`、ID 用 `ID_PATTERN`、錯誤訊息繁中）：

   ```python
   class MethodDef(ContentModel):  # 9.6.11 方法 12 類
       id: str; name_zh: str; attributes: tuple[Attribute, ...]  # 常見屬性（1～2）

   class CheckRules(ContentModel):
       dc_shift_max: int  # 9.6.4「±2」（只能 0～2，不可放寬）
       partial_margin: int  # 總值 ≥ DC − partial_margin＝部分成功
       care_max: int  # 9.6.4「最多 +2」（只能 0～2）
       race_bonus: int  # 9.6.4「+1」（只能 0～1）

   class SituationBudget(ContentModel):  # 獎勵預算（依地點建議等級）
       xp_battle_permille: int  # xp 預算 ＝ 打贏一場的經驗（battle.xp_per_battle）× ‰（07 7.8：0.5 份）
       supplies_max: int; threads_max: int  # 線頭 ≤ 2（9.6.7 #6「0～2 條」）
       buffs_max: int; reveals_max: int

   class DangerDef(ContentModel):  # 危險度 → 允許的懲罰（9.6.4「依情境危險度分級」）
       level: int  # 1～3
       penalties: tuple[PenaltyKind, ...]  # supplies／debuff／hurt／reinforce
       hurt_max_permille: int

   class SituationRules(ContentModel):  # content/world/situation_rules.yaml
       methods: tuple[MethodDef, ...]
       race_methods: dict[str, str]  # 種族 → 方法（9.6.11 #115）
       check: CheckRules
       budget: SituationBudget
       dangers: tuple[DangerDef, ...]
       exchange_supplies: int  # 用心清單「交換條件」拿補給出來時花掉的量

   class SituationRewards(ContentModel):
       xp_permille: int = 0  # 0～1000，乘地點的等級預算 xp
       supplies: int = 0
       threads: tuple[str, ...] = ()  # 必須是本骨架的線頭
       reveal: tuple[str, ...] = ()  # 本區的隱藏地點（reveal 含 situation）
       buffs: tuple[str, ...] = ()  # statuses.yaml；下一場戰鬥帶（短期 buff）

   class SituationPenalties(ContentModel):
       supplies: int = 0
       hurt_permille: int = 0  # 最大 HP 的 ‰，最少留 1 HP
       debuffs: tuple[str, ...] = ()  # statuses.yaml；下一場戰鬥帶
       reinforce: bool = False  # 下一場戰鬥敵人增援

   class SituationOutcomeDef(ContentModel):
       rewards: SituationRewards; penalties: SituationPenalties  # 都有預設（空）

   class WeaknessDef(ContentModel):  # 用心清單 ④「方法針對情境弱點」
       id: str; text_zh: str; methods: tuple[str, ...]

   class SituationTemplateDef(ContentModel):
       id: str
       skeleton: str  # 本區骨架
       solution: int  # 骨架 solutions 的索引（0 起），必須是 situation
       note_zh: str
       methods: tuple[str, ...]  # 允許的方法（1～3）
       attributes: tuple[Attribute, ...]  # 2～3 種，開頭＝骨架解法的屬性
       base_dc: int  # 5～30
       danger: int  # 1～3
       weaknesses: tuple[WeaknessDef, ...] = ()
       advantage_threads: tuple[str, ...] = ()  # 持有其一＝優勢（18.4 補充：暗門）
       success: SituationOutcomeDef; partial: SituationOutcomeDef; failure: SituationOutcomeDef

   class SituationTemplateTable(ContentModel):  # content/world/situations/<region>.yaml
       region: str; templates: tuple[SituationTemplateDef, ...]

   # LLM 提議（pydantic；trpg.llm 與 trpg.world 共用）
   CareItem = Literal["clue", "npc_bond", "exchange", "weakness"]  # 9.6.4 用心清單 ①～④
   class CareClaim(_Strict): item: CareItem; fact: str  # fact＝引擎給的事實編號
   class SituationProposal(_Strict):
       attribute: Attribute; method: str; dc_shift: int  # −2～+2
       disadvantage: bool = False; care: tuple[CareClaim, ...] = ()  # 最多 4 筆
   class SituationFact(_Strict): item: CareItem; fact: str; text_zh: str

   def proposal_problems(template, rules, proposal) -> list[str]  # 靜態合法性
   def default_proposal(template, rules) -> SituationProposal  # 降級提議
   ```

   **單檔驗證**：方法 ID、模板 ID、弱點 ID 不重複；`attributes` 2～3 個不重複；每個模板屬性都至少有一個模板方法能用、每個模板方法至少有一個常見屬性在模板屬性裡；弱點的方法在模板方法裡；危險度 1～3 各一筆；`check` 不可超過 9.6.4（±2、+2、+1）。
   **跨檔案** `situation_problems(...)`（排序）：骨架存在且同區；`solution` 指到 `situation` 解法，解法屬性＝模板屬性的開頭；方法在 `rules`；獎勵線頭是本骨架的線頭；`reveal` 是本區 `hidden` 且 `reveal` 含 `situation` 的地點；buff／debuff 在 `statuses.yaml`；`advantage_threads` 存在（任一區）；獎勵在預算內（補給、線頭、buff、揭露）；懲罰種類在該危險度允許的清單、`hurt_permille` ≤ 上限；`race_methods` 的種族在 `races.yaml`、方法在 `methods`。

2. **`SolutionDef.requires_keyword: str | None`**（只有 `opportunity` 可填；必須是 `skill_keywords.yaml` 的關鍵字）：18.4 補充「帶電技能＝裝備中的技能有任何一招帶『帶電』關鍵字」，雲嶺 #12 填 `charged`。引擎 `opportunity_available(library, char, solution)`：英雄裝備的技能中任何一招推導出的關鍵字（製造或利用）含該關鍵字。機遇的結算（入口、技能）不在本段。

3. **載入**：情境模板與規則在 `load_world_event_content` 裡一起載（`WorldEventContent` 加 `situations`、`situation_rules`），`library.py` 只改那一行呼叫。不存在＝空／`None`。模板 ID 跨區不重複。

4. **雲嶺內容**：`content/world/situation_rules.yaml`（10.4）、`content/world/situations/cloud_ridge.yaml`（10.3；18.4 每個情境判定解法一個模板，共 23 個）。

5. **`trpg.world`**：
   - `rng.py`：新串流 `STREAM_CHECK = "check"`。
   - `state.py`：`NextBattleMod`（`kind: buff|debuff|reinforce`、`status`、`source`＝模板 ID）；`CharacterState.next_battle: tuple[NextBattleMod, ...] = ()`（之後的戰鬥接線消耗；本段只寫入）。有預設值、不升格式版本。
   - `actions.py`：動作 `SituationAction`（`kind="situation"`、`template`、`player_text`（≤ 500 字）、`proposal`、`source: "llm"|"fallback"`、`prompt_version`）；事件 `situation_check`（模板、屬性、方法、基準 DC、調整、DC、兩顆骰、優勢／劣勢、採用的骰、屬性修正、用心清單逐筆明細、用心加值、種族加值、總值、結果）、`situation_result`（xp、補給增減、HP 損失、下一場戰鬥修正）、`thread_added`、`thread_pushed_out`、`event_resolved`；揭露地點沿用 `location_revealed`（method＝`situation`）。
   - `situations.py`：`situation_template`、`situation_facts`（給外層餵 LLM）、`resolve_situation`（10.5）、`opportunity_available`。
   - `step.py`：`world_step` 多一個分派。

6. **`trpg.llm.situation`**（新）：`SITUATION_PROMPT_VERSION`、`situation_schema(template, rules, facts)`（屬性、方法、事實編號都是列舉，`dc_shift` −2～2）、`build_situation_messages(...)`（系統指令＋資料區；玩家文字只出現在 `<player_input>`，其餘資料經 `escape_text`）、`propose_situation(client, ...) -> SituationProposalOutcome`。只用 `LLMClient` 介面；測試用 `MockLLMClient`。

7. **測試**（10.7）與 **完成報告** `docs/phases/Phase5B-2報告.md`：交付、判定流程、注入防護與合法性檢查、可重播證明、代決、待 PM 決定。

### 10.3 雲嶺情境模板（18.4 → 資料；第 2 種屬性照 18.4 補充：同一類方法的常見屬性，不夠再補主題不同的屬性）

| 骨架 | 模板 `id` | 解法 | 方法 | 屬性 | DC | 危險 |
|---|---|---|---|---|---|---|
| 1 | `peddler_safe_path` | 感知（找安全路） | 追蹤、力取 | wis、str | 12 | 2 |
| 2 | `acolyte_find_way` | 感知／智力（認路） | 追蹤、學識 | wis、int | 11 | 1 |
| 3 | `toll_intimidate` | 意志（威嚇） | 威嚇 | wil、str | 13 | 2 |
| 4 | `elder_go_game` | 智力（下棋） | 學識、察覺 | int、wis | 13 | 1 |
| 4 | `elder_patience` | 意志（耐心） | 交涉、學識 | wil、int | 12 | 1 |
| 5 | `lingzhi_climb` | 力量／敏捷（攀爬） | 攀爬跳躍 | str、dex | 14 | 2 |
| 6 | `monks_persuade` | 意志（說服一方） | 交涉、學識 | wil、int | 13 | 1 |
| 6 | `monks_see_lie` | 感知（看穿誰在說謊） | 察覺、學識 | wis、int | 13 | 1 |
| 7 | `deserter_hide` | 敏捷（帶他躲藏） | 潛行、耐力 | dex、con | 14 | 3 |
| 8 | `hunter_awaken` | 意志（喚醒） | 異象、學識 | wil、int | 14 | 2 |
| 9 | `ferry_repair` | 智力（修理） | 機關、力取 | int、str | 12 | 1 |
| 10 | `bear_slip_away` | 感知（悄悄退出） | 察覺、潛行 | wis、dex | 13 | 3 |
| 11 | `envoy_persuade` | 意志（說服） | 交涉、察覺 | wil、wis | 13 | 2 |
| 11 | `envoy_take_cover` | 敏捷（躲到掩體） | 攀爬跳躍 | dex、str | 13 | 2 |
| 12 | `altar_endure` | 體質（硬撐） | 耐力、異象 | con、wil | 15 | 2 |
| 13 | `sword_pull` | 力量（拔劍） | 力取、耐力 | str、con | 15 | 2 |
| 13 | `sword_array` | 智力（解陣） | 機關、靈巧 | int、dex | 15 | 2 |
| 14 | `convoy_steal` | 敏捷（偷走；持有「暗門」優勢） | 靈巧、察覺 | dex、wis | 15 | 3 |
| 15 | `spring_hold_breath` | 體質（憋氣） | 耐力、力取 | con、str | 14 | 2 |
| 15 | `spring_antidote` | 智力（配解藥） | 學識、耐力 | int、con | 14 | 2 |
| 16 | `storyteller_tale` | 意志（文字回答＋用心清單） | 交涉、學識 | wil、int | 12 | 1 |
| 17 | `patrol_track` | 感知（追蹤） | 追蹤、耐力 | wis、con | 13 | 2 |
| 18 | `fox_persuade` | 意志（說服；狐族交涉 +1） | 交涉、察覺 | wil、wis | 12 | 1 |

- DC 初值＝10＋骨架地點建議等級的一半上下（開發 PM 定）。獎懲：成功 xp 1000‰＋本骨架的線頭（≤ 2）、部分成功 xp 500‰＋輕懲罰、失敗依危險度懲罰；哪個結果留哪條線頭照骨架文字推定（開發 PM 定，之後模擬與玩法 PM 調）。
- 弱點（用心清單 ④）每個模板 1～2 個，照骨架的阻礙推定（例：霧狼怕火→ 不適用；行商說得出狼群走向 → 追蹤）。

### 10.4 規則數值初值（`content/world/situation_rules.yaml`；方法與種族照 9.6.11，其他開發 PM 定、之後模擬定）

```yaml
methods:  # 9.6.11 #115
  - {id: force, name_zh: 力取, attributes: [str]}
  - {id: climb, name_zh: 攀爬跳躍, attributes: [str, dex]}
  - {id: stealth, name_zh: 潛行, attributes: [dex]}
  - {id: finesse, name_zh: 靈巧, attributes: [dex]}
  - {id: endurance, name_zh: 耐力, attributes: [con]}
  - {id: lore, name_zh: 學識, attributes: [int]}
  - {id: mechanism, name_zh: 機關, attributes: [int]}
  - {id: notice, name_zh: 察覺, attributes: [wis]}
  - {id: tracking, name_zh: 追蹤, attributes: [wis]}
  - {id: parley, name_zh: 交涉, attributes: [wil]}
  - {id: intimidate, name_zh: 威嚇, attributes: [wil, str]}
  - {id: uncanny, name_zh: 異象, attributes: [wil]}
race_methods: {human: lore, elf: notice, fox: parley, dragonkin: intimidate, dwarf: mechanism,
               cyborg: finesse, orc: force, fiend: uncanny, scalefolk: stealth, seafolk: endurance}
check: {dc_shift_max: 2, partial_margin: 5, care_max: 2, race_bonus: 1}
budget: {xp_battle_permille: 500, supplies_max: 2, threads_max: 2, buffs_max: 1, reveals_max: 1}
dangers:
  - {level: 1, penalties: [supplies, debuff], hurt_max_permille: 0}
  - {level: 2, penalties: [supplies, debuff, hurt], hurt_max_permille: 250}
  - {level: 3, penalties: [supplies, debuff, hurt, reinforce], hurt_max_permille: 400}
exchange_supplies: 1
```

### 10.5 規則（`resolve_situation`，純函式）

**合法性檢查**（任一不過拋 `WorldActionError`、狀態不變；外層可以重新提議或用降級提議）：
1. 角色有 `pending_event`、沒有 `pending_encounter`；模板存在於角色所在區、`template.skeleton == pending_event.skeleton`。
2. `player_text` ≤ 500 字（只存紀錄，引擎不讀內容）。
3. `proposal_problems`：屬性在模板 `attributes`、方法在模板 `methods`、屬性是該方法的常見屬性、`|dc_shift| ≤ dc_shift_max`、用心清單 ≤ 4 筆。
4. **第一次送出即定案**：結算後 `pending_event` 清掉，同一個事件不能再判定（再送＝沒有事件可判定而被拒）。

**用心清單**（逐筆核對引擎狀態，不信 LLM 文字；核對不到「不算」、不是錯誤，寫進事件明細）：
- 事實集合＝`situation_facts`：① `clue` → `thread:<id>`：角色持有的有效個人線頭與世界線頭；② `npc_bond` → `npc:<id>`：骨架 `npcs` 中、角色持有以該 NPC 為 `npc` 的有效線頭（過去互動的紀錄；好感度在 5B-4 後再加）；③ `exchange` → `supplies`：補給 ≥ `exchange_supplies`；④ `weakness` → `weakness:<id>`：模板的弱點。
- 一筆要算：`(item, fact)` 在事實集合裡；`weakness` 另外要求提議的方法在該弱點的 `methods` 內。
- 同一項（item）只算一次（9.6.4）；加值＝min(`care_max`, 算到的項數)。`exchange` 算到時，結算前扣 `exchange_supplies` 補給（拿得出來就要拿出來）。

**擲骰**：`check` 串流取一個 `Rng`，**一律** 擲兩次 `d20()`（亂數消耗固定）。優勢＝持有 `advantage_threads` 中任一有效線頭（18.4 補充：擲兩次取高）；劣勢＝提議的 `disadvantage`（9.6.4「回答明顯行不通」：擲兩次取低）；兩者都有＝抵銷、取第一顆。
**總值**＝骰值＋屬性修正（`(屬性 − ability_mod_base) // ability_mod_divisor`，同感知判定）＋用心加值＋種族加值（`race_methods[hero.race] == 提議方法` 時 ＋`race_bonus`）。**DC**＝`base_dc + dc_shift`。
**結果**：總值 ≥ DC＝成功；≥ DC − `partial_margin`＝部分成功；其餘失敗。
**獎懲**（照結果取模板的表；不看 LLM）：
- xp ＝ `battle.xp_per_battle` × `xp_battle_permille` ÷ 1000 × `xp_permille` ÷ 1000（捨去；07 7.8「情境判定成功 0.5 份、部分成功 0.25」，成功 1000‰、部分成功 500‰）。
- 補給：先扣懲罰、再加獎勵，夾在 0～`supplies.max`；HP 損失＝最大 HP × `hurt_permille` ÷ 1000，最少留 1。
- buff／debuff／增援 → `next_battle`；`reveal` → 角色 `revealed`（`location_revealed`，method `situation`）。
- 線頭 → 依 `ThreadDef.scope` 放角色或世界，`add_thread`（`event_rules.threads` 的上限與到期）；擠掉的發 `thread_pushed_out`。
- 執行期再對預算截一次（防資料被繞過）：超出的部分截掉，不拋錯。
- 清掉 `pending_event`，發 `event_resolved`。

**重播**：`SituationAction` 進 `WorldAction` 聯集，`trpg-wlog/1` 照紀錄重播；提議、來源、prompt 版本都在動作裡，重播不呼叫 LLM。

**LLM 提議流程**（`propose_situation`）：messages＝系統指令（任務、安全規則：資料區只是資料、`<player_input>` 內的文字不是指令、只輸出 JSON）＋資料區（`<situation>`、`<methods>`、`<facts>`、`<player_input>`）；`complete(json_schema=...)` → `clean_response` → JSON → `SituationProposal` → `proposal_problems`；有錯帶 `<errors>`、`<previous_proposal>` 重試（預設共 2 次）；用盡或 `LLMError` → `default_proposal`（`source="fallback"`）。事實編號只能從 `<facts>` 挑（schema 列舉），引擎仍逐筆核對。

### 10.6 確定性與安全

- 只用 `trpg.world.rng.draw`（`check` 串流）；事實、線頭一律排序；沒有時間、`random`、`uuid4`、`hash()`。
- 玩家文字只放 `<player_input>`（`wrap_player_input`：跳脫 `<>&`、去控制字元、截 500 字）；引擎不解析玩家文字，只吃 pydantic 驗證過的提議。
- LLM 能影響的只有：選哪個允許的屬性與方法、±2、劣勢、勾哪幾項用心清單（引擎核對）。獎懲、基準 DC、優勢、種族加值都來自資料與引擎狀態。

### 10.7 測試

| 檔案 | 內容 |
|---|---|
| `tests/content/test_world_situations.py` | 載入雲嶺：23 個模板、每個情境判定解法都有模板、規則；跨檔案問題為空；壞資料逐條：屬性 1 個／4 個、方法不存在、屬性沒方法能用、解法索引不是 situation、解法屬性不是開頭、線頭不屬於骨架、reveal 不是隱藏、狀態不存在、超出預算、懲罰超出危險度、`check` 放寬；`proposal_problems` 各情況；`default_proposal`；`requires_keyword` 只有機遇可填、未知關鍵字 |
| `tests/world/test_situations.py` | 沒事件／骨架不符／屬性不在清單／方法不允許／±3 被拒且狀態不變；送出後不能再送；成功／部分／失敗三段；用心清單：持有線頭算、沒持有不算、重複項只算一次、上限 2、弱點方法不符不算、交換扣補給；優勢（暗門）取高、劣勢取低、抵銷；種族 +1 只對對應方法；獎懲：xp 照等級預算、補給夾上限、HP 最少 1、線頭加入與擠出、世界級線頭、下一場修正、揭露；重播：日誌（移動→觸發→判定）重播出逐字相同的快照；機遇條件 |
| `tests/llm/test_situation_propose.py` | schema 列舉；玩家文字只在 `<player_input>`、注入字串被跳脫；Mock 回合法 JSON → `llm` 來源；壞 JSON／越界（±3、屬性不在清單）→ 帶錯誤重試 → 成功或降級；`LLMUnavailable` → 降級；端到端（Mock 提議 → 動作 → 判定） |

### 10.8 驗收

- `uv run pytest -q tests/world tests/llm/test_situation_propose.py tests/content/test_world_situations.py tests/content/test_world_events.py tests/test_architecture.py -n 8 --timeout=1800` 通過；交件前加跑 `tests/cli`（`-m "slow or not slow"`）。
- `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 通過；`C901` ≤ 15。

### 10.9 不做的事

- 不做說書人挑骨架、情境敘述與結果敘述（5B-3）；不做放棄、交涉、戰鬥解法的結算、任務、好感度、線頭到期結局（5B-4）；不做機遇的獎勵；不做 API、前端。
- 不把下一場戰鬥修正接到戰鬥；不做任務幣（5D-1 才有貨幣）。
- 不補 18.4 補充的 follows 對照、新骨架 19～21、世界級線頭（另排 5B-1b）；「在斷崖幫寨的戰鬥我方先手」屬戰鬥接線，記在報告待辦。

### 10.10 代決

| # | 事項 | 代決 | 誰定 |
|---|---|---|---|
| 5B2-1 | 模板第 2 種屬性：解法屬性為主，從 9.6.11 方法表同一類補，不夠再補主題不同的屬性 | 10.3 表 | **玩法 PM 定**（18.4 補充） |
| 5B2-2 | 「帶電技能」＝裝備技能任何一招推導出 `charged` 關鍵字；「暗門」＝骨架 14 偷竊優勢（擲兩次取高） | `requires_keyword`、`advantage_threads` | **玩法 PM 定**（18.4 補充） |
| 5B2-3 | 一個情境判定解法一個模板；模板以骨架解法索引對應 | 10.2 | 開發 PM 定 |
| 5B2-4 | 部分成功＝總值 ≥ DC − 5；優勢與劣勢抵銷；亂數一律擲兩顆 | 10.5 | 開發 PM 定 |
| 5B2-5 | 預算：xp ＝ 一場戰鬥經驗的 500‰（照 07 7.8 經驗來源比例，不依地點等級；戰鬥經驗本身也不依等級）、補給 ≤ 2、線頭 ≤ 2、buff ≤ 1、揭露 ≤ 1；危險度 1～3 的懲罰種類與受傷上限 | 10.4 | 開發 PM 定（初值） |
| 5B2-6 | 用心清單的事實：① 有效線頭；② 骨架 NPC＋持有該 NPC 的線頭（好感度在 5B-4）；③ 補給（算到就扣）；④ 模板弱點＋方法相符；影子專長（9.6.4）等 5C-2 | 10.5 | 開發 PM 定 |
| 5B2-7 | 劣勢只由 LLM 提議；優勢只由資料（線頭）給，LLM 不能提議優勢 | 9.6.4 只寫劣勢 | 開發 PM 定 |
| 5B2-8 | 獎勵沒有任務幣（5D-1 才有貨幣）；buff／debuff／增援存在角色 `next_battle`，戰鬥接線之後做 | 10.2 | 開發 PM 定 |
| 5B2-9 | DC 初值、各模板的獎懲、弱點與哪個結果留哪條線頭 | 10.3 | 開發 PM 定（初值，之後模擬） |
| 5B2-10 | LLM 提議共試 2 次，用盡或連不上 → 降級提議（第一個屬性、±0、不勾清單） | 10.5、3.1 | 開發 PM 定 |

## 11. 5A-5 詳細規格：API 與前端地點圖畫面

> 給實作 agent。只動 `src/trpg/api/`（新增 `world.py`、`world_schemas.py`、`world_presenter.py`、`routes/world.py`；`app.py`、`state.py` 小改）、`src/trpg/world/` 的 **小改**（`state.py` 加 1 個欄位、`battle.py` 與 `town.py` 認得生成技能，見 11.4）、`tests/api/`、`tests/world/`（只加測試）、`client/`（新畫面、首頁入口、API 型別）、`client/openapi.json`。**不做** 帳號與登入（5E-1）、事件卡與情境判定（5B-5）、屬性點分配與閃現等成長服務（5A-6）、傭兵（5C-1）。不改 `trpg.engine`、`trpg.roguelite`、`trpg-run` 與戰鬥紀錄格式。
> 依據：09 9.6.2（點哪裡就走過去、路上可能遇敵、隱藏地點要探索才出現、建議等級、城鎮之間用傳送點）、9.6.6（開戰前看得到陣容、可撤退）、9.6.7 #2（城鎮與營火完全回復、換技能）、#9（點相鄰地點移動、趕路）、#11（補給）、#15（已清空）、#16（日夜與天氣）、9.6.9 #98（全滅回小鎮、疲憊）、9.6.11 #114（營火＝紮營）；07 7.6「創角：自選起始武器＋選 2 個關鍵字」、7.7（種族與出身）；本檔 2.1～2.5、6、9；`docs/開發PM交接.md` 6.5.1（浮動卡規則）。

### 11.1 目標

使用者能在瀏覽器玩大世界的第一個可試玩里程碑（第 3 節「試玩」）：**首頁「大世界（測試）」→ 建立角色 → 雲嶺地點圖點相鄰地點移動 → 遇敵看陣容（撤退或開戰）→ 用現有戰鬥畫面打完 → 回到地點圖（勝負已回寫）→ 回霧渡鎮休息、換技能、傳送；野外紮營**。所有世界規則照 `trpg.world`（5A-2～5A-4），API 只負責存取、時鐘與組裝顯示資料。

### 11.2 存檔與工作階段（`trpg.api.world`）

- **位置**：一輪存檔資料夾（`create_app(save_dir=…)`，預設 `saves/`）底下的 `world/`：`world.json`（`trpg-world/1`）、`chars/<character_id>.json`（`trpg-char/1`）、`log.jsonl`（`trpg-wlog/1`，一行一筆、append）。寫檔用 5A-2 的 `write_atomic`（日誌：讀全部＋新行原子重寫；5～10 人量足夠）。
- **世界**：第一次用到時建立（`season_id = "s1"`、`season_seed` 由伺服器 `secrets.randbits(64)`、`season_start = now`）；之後從 `world.json` 讀。
- **時間**：API 層讀 `int(time.time())` 傳給 `world_step`（2.1）；`WorldStore` 接受注入的時鐘（測試用固定時間）。
- **單一寫入佇列**（2.4）：一把全域鎖；每個成功的世界動作依序取 `seq`（日誌最後一筆 ＋1）寫進日誌，再寫角色與世界快照。動作不合法（`WorldActionError`）→ 422、什麼都不寫。
- **戰鬥**：`POST …/battle` 用 `prepare_battle(library, char)` 的 `setup`／`seed` 在現有戰鬥工作階段表開一場（`SessionStore.open`，和一輪相同），之後用既有 `/api/battles/{id}/…` 操作；戰鬥結束後，任何讀取該角色的請求先 **同步**：把這場的步驟送 `fight` 世界動作（`world_step`），寫日誌與快照，戰鬥工作階段脫鉤。戰鬥中途伺服器重啟：遭遇還在，重新開戰從頭打（同一個種子；代決 5A5-5）。戰鬥中不能做其他世界動作（409）。
- **角色**（帳號是 5E-1）：不做登入；角色以伺服器產生的簡單 ID（`c` ＋ 8 個十六進位字元）存取，可以有多個；前端記住最後使用的角色 ID（瀏覽器 `localStorage`），首頁入口列出既有角色（代決 5A5-1）。

### 11.3 API（`/api/world`，`trpg.api.routes.world`）

| 方法與路徑 | 內容 |
|---|---|
| `GET /api/world/characters` | 角色列表（ID、名稱、等級、區域、所在地點名） |
| `POST /api/world/characters` | 建立角色（201）：`name`（1～12 字）、`weapon`、`keywords`（2 個）、`race`、`origin`（選填）、`seed`（選填，起始技能；省略由伺服器亂數）；主角照 07 7.6 創角，用一輪開局的同一套函式（`new_keyword_run` ＋ `with_race`／`with_origin`，開局配點照預設），站在雲嶺霧渡鎮（`new_character`）。武器、關鍵字、種族、出身的選項沿用 `GET /api/runs/start-options`。|
| `GET /api/world/characters/{id}` | 地點圖畫面的整份資料（`WorldView`，見下）；先同步已結束的戰鬥 |
| `POST /api/world/characters/{id}/actions` | 一個世界動作：`travel`（`to`、`hasten`）、`camp`、`retreat`、`rest`、`loadout`（`skills`）、`teleport`（`region`）；`fight` 不從這裡送（戰鬥走下一列）。回傳 `WorldView`（含這個動作的事件文字） |
| `POST /api/world/characters/{id}/battle` | 有遭遇時開戰或接續進行中的戰鬥：`{world: WorldView, battle: BattleResponse}` |

錯誤：角色不存在 404；動作不合法、內容不合法 422；戰鬥中做其他動作、沒有遭遇卻開戰 409。

**`WorldView`**（全部由後端算好，前端不寫規則）：
- `character`：ID、名稱、等級、經驗（目前／下一級門檻；到頂為 `None`）、HP／最大 HP、法力／上限、補給／上限、疲憊、未分配屬性點、武器名、種族名、裝備的技能卡（`SkillCard`）、備用技能卡、技能欄位上限。
- `map`：區域 ID 與名稱、等級範圍、地點列表（ID、名稱、種類與中文種類、建議等級文字、說明、座標、`current`、`adjacent`（可以走過去）、`blocked`（相鄰但不能走的原因，例：還沒開放）、`cleared`、`camped`）、連線列表。**未發現的隱藏地點與連到它的連線不出現在回應裡**（不是只在前端藏起來）。
- `here`：目前地點的服務——`can_rest`、`can_camp`／`camp_problem`、`can_loadout`、`teleports`（可傳送的區域與名稱；沒有地點圖的區域不列）、`supplies_cost`（趕路、紮營）。
- `encounter`：沒有時 `None`；有時：地點名、敵人等級、戰鬥地圖名、天氣、日夜、陣容（每名敵人：名稱、是否精英、詞綴名）、撤退會回到哪裡、`in_battle`（已開戰未結束）。
- `clock`：遊戲內時刻（`HH:MM`）、日夜、這一區現在的天氣名稱。
- `events`：這次請求的世界事件轉成的中文句子（移動、遇敵、感知判定、發現地點、戰鬥結果、升級、全滅、清空、休息、紮營、換技能、傳送）；`GET` 時只帶剛同步的戰鬥結果。
- `battle_id`：進行中戰鬥的 ID（沒有＝`None`）。

### 11.4 `trpg.world` 的小改（生成技能）

07 7.6 的創角從關鍵字池給起始技能，可能是組合器生成的技能（不在內容庫）。`CharacterState` 加 `generated_skills: tuple[SkillDef, ...] = ()`（同 `RunState.generated_skills`，依 ID 排序；舊檔照讀、格式字串不變）；`prepare_battle` 把它併進該場規則包；`loadout` 認得它。不改其他規則。

### 11.5 前端（`client/src/world/`、`client/src/screens/World*.tsx`）

- **首頁入口**：開始畫面加「大世界（測試）」按鈕。
- **角色畫面**：列出既有角色（點了進入）；建立新角色：名稱、起始武器、2 個關鍵字（沿用一輪開局的選擇元件與 `start-options`）、種族與出身選填。
- **地點圖畫面**：
  - 左：程式繪製的地點圖（SVG；座標用內容的 `pos`）：地點圓點（依種類不同形狀或顏色）、名稱、建議等級；連線；目前位置醒目標示；可以走的相鄰地點可點（滑過有建議等級與說明的浮動卡，用共用浮動卡元件 6.5.1）；不相鄰的地點不可點；已清空標「已清空」；未發現的隱藏地點不畫。
  - 右：角色狀態（HP、法力、補給、等級與經驗、疲憊）、時刻與天氣、目前地點與服務按鈕（城鎮：休息、換技能、傳送；野外：紮營；營火中：換技能）、「趕路」切換（花補給降低遇敵機率）、最近事件紀錄。
  - **遇敵**：右側最上方出現陣容面板（敵人名單、等級、地圖、天氣；不是浮動卡）：「開戰」或「撤退」；有遭遇時地點圖不可點。
  - **換技能**：城鎮或營火才有；勾選裝備的技能（擁有＝裝備＋備用），送出前檢查欄位上限由後端回錯誤。
- **戰鬥**：沿用 `BattleScreen`（`exitLabel="回到地點圖"`）；結束或離開回到地點圖（重新讀 `WorldView`，勝負已回寫）。進行中的戰鬥離開後地點圖顯示「繼續戰鬥」。
- 美術：只用程式繪製的元件與現有樣式（不加新美術）。

### 11.6 測試

| 檔案 | 內容 |
|---|---|
| `tests/api/test_world_api.py` | 建立角色（站在霧渡鎮、技能卡、補給）；列表；名稱或關鍵字不合法 → 422；不存在 → 404；地點圖不含未發現的隱藏地點與它的連線、發現後出現；移動到相鄰地點、非相鄰 → 422；遇敵後看陣容、撤退回出發地點；開戰 → 戰鬥工作階段 → AI 代打到結束 → `GET` 同步（經驗或全滅回小鎮）、日誌有 `fight`；戰鬥中移動 → 409；城鎮休息、換技能、紮營（村落）、傳送選項；存檔：新的 app 讀同一資料夾得到相同角色；日誌重播（`replay`）得到與快照相同的角色 |
| `tests/world/test_generated_skills.py` | 角色帶生成技能：開戰規則包含它、換技能認得它；舊格式（沒有欄位）照讀 |
| `client/src/world/*.test.ts` | 地點圖顯示資料的純函式（地點樣式、可點與不可點、已清空文字、事件文字）、角色建立表單的驗證 |

### 11.7 驗收

- `uv run pytest -q tests/api tests/world -n 8 --timeout=3000`；`tests/cli -m "slow or not slow" --timeout=3000`；`npx vitest run`、`npm run build`（`client/`）；`ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`；OpenAPI 快照重產（`scripts/export_openapi.py` ＋ `gen:api`）。
- 瀏覽器實際走一遍（後端、前端用 8000／8001／8010 以外的埠）：建立角色 → 雲嶺移動 → 遇敵 → 看陣容 → 開戰打完 → 回地點圖 → 回小鎮休息；浮動卡 6.5.1 實測（1600×900、800×600）；截圖或 `read_page` 記錄寫進報告。

### 11.8 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5A5-1 | 帳號還沒做（5E-1） | 不登入；角色用伺服器產生的 ID，可多個；前端記最後一個；5E-1 改成依帳號存取 |
| 5A5-2 | 世界與賽季的建立 | 第一次用到時自動建立 `s1`，伺服器亂數種子、開始時間＝當下 |
| 5A5-3 | 創角的配點、名稱 | 配點照一輪開局的預設（全點主屬性）；名稱只顯示用（1～12 字），不影響規則 |
| 5A5-4 | 日誌寫法 | 讀全部＋新行原子重寫（不做 append 模式）；5～10 人量足夠 |
| 5A5-5 | 戰鬥中途的進度 | 不存檔；伺服器重啟後遭遇還在、從頭開戰（同種子） |
| 5A5-6 | 戰鬥畫面 | 沿用現有戰鬥畫面與 API；回到地點圖時才把步驟送 `fight` 回寫 |
| 5A5-7 | 地點圖畫法 | SVG＋內容的 `pos`；地點種類用不同顏色與形狀；不加新美術 |
| 5A5-8 | 生成技能 | `CharacterState.generated_skills`（同 `RunState`），11.4 |

### 11.9 不做的事

- 帳號、登入、一帳號 2～3 角色的上限（5E-1）；事件卡、情境判定、NPC 對話（5B-5）；屬性點分配、閃現、重閃（5A-6 之後）；傭兵與影子（5C）；商店與背包（5D）；朋友足跡、多人同時在線的顯示。

## 12. 5A-6 詳細規格：大世界成長接點

> 給實作 agent。只動 `src/trpg/world/`、`src/trpg/content/world_rules.py`、`src/trpg/content/world_encounters.py`（一個欄位）、`src/trpg/content/world_oaths.py`（新）、`src/trpg/content/library.py`（載入誓約，一行）、`content/world/rules.yaml`（末尾加 `hero_growth`）、`content/world/encounters/cloud_ridge.yaml`（斷崖幫寨一行）、`src/trpg/engine/setup.py`、`src/trpg/engine/battle.py`（開場狀態與先手，見 12.5）、`src/trpg/engine/runner.py`（`LOG_FORMAT` 遞增）、`docs/phases/戰鬥紀錄格式變更.md`、`tests/world/`、受影響的 `tests/content/`、`tests/engine/`、`tests/cli/`（只改版號字串）。**不做** API、前端（5A-5 另一個 agent 在做 `src/trpg/api/`、`client/`）；不做經驗曲線與遭遇強度（5A-SIM）；不改 `trpg.roguelite` 的函式簽名與原型行為（`offer_tier_by_level` 只留 roguelite）。
> 依據：07 7.2（配點、營火免費重配、HP 隨體質）、7.6（技能階級 1～3 級 1 階、4～7 級 2 階、8～10 級 3 階；換裝地點）、7.8（每級屬性 +2、HP +5%、2 點靈感、4、8 級升階；經驗來源；上限 10）；06 6.26（誓約）、6.34.2（大世界靈感：每升 1 級 2 點、任務鏈段落／世界事件／每種精英首殺各 1 點、一般戰鬥不給；花在主城、小鎮、營火）、6.34.3（閃現、重閃、溶掉）、6.34.9（階級屬於角色、升階重配、傳承）；09 9.6.7、9.6.10 #106（大世界立誓：主城、小鎮、營火，同時 1 個，解除後現實 1 天不能再立）、9.6.11 #114（營火可換技能、閃現、重閃、溶掉、傳承、立誓）；18 18.4「補充」（暗門：在斷崖幫寨的戰鬥我方先手；**危險度 3 的增援**：從同地點遭遇表用種子抽 1 名非精英敵人、照地點等級，陣容已滿 4 名改成敵人先手——玩法 PM 定，main `5cbda759`）、18.6（誓約模板，內容在 5C-3）；本檔 2.2（重用 roguelite，不搬家）、9、10。

### 12.1 目標

大世界角色有完整的成長接點，全部是 **世界動作**（寫進 `trpg-wlog/1`、可重播）或戰鬥／判定的回寫：

- 任何來源加經驗後立刻判定升級（戰鬥、情境判定，之後的任務也呼叫同一個函式）；升級給屬性點、靈感點，跨過 4、8 級時主角技能照 07 7.6 的角色階級重配。
- 配點、重配、閃現、重閃、溶掉、傳承、立誓、解除誓約。
- 5B-2 的 `next_battle` 在開戰時套用並消耗；增援照玩法 PM 定；斷崖幫寨持有暗門時我方先手。

### 12.2 交付項目

1. **規則 content**（`content/world/rules.yaml` 末尾、`WorldRules.hero_growth`，有預設值）：

   ```yaml
   hero_growth:                                          # 5A-6
     skill_tier_by_level: [1, 1, 1, 2, 2, 2, 2, 3, 3, 3]  # 07 7.6（玩法 PM 定）
     insight_per_level: 2                                # 06 6.34.2 大世界
     insight_per_elite_kind: 1                           # 06 6.34.2「每種精英的首殺各 1 點」
     level_cap: 10                                       # 7.8、09 9.7 第一季上限
   ```
   經驗門檻仍沿用原型 `roguelite.yaml` 的 `level_thresholds`（Q8，5A-SIM 再定）。

2. **`trpg.world.growth`**（新）：
   - `world_library(library)`：給 roguelite 成長函式用的內容庫視圖——只把 `roguelite.offer_tier_by_level` 換成 `hero_growth.skill_tier_by_level`（`dataclasses.replace`，同 `trpg.sim` 的做法），所以 roguelite 的閃現出題、傳承、升階重配在大世界用 07 7.6 的階級；原型不受影響。
   - `hero_tier(library, level)`、`as_run(library, world, char) -> RunState`／`from_run(char, run)`：把角色轉成 roguelite 的 `RunState`（`seed`＝角色技能種子 `fnv1a64("{season_seed}:{character_id}:skills")`、`plan=()`、`node=CampfireNode`、`source=0`、`llm=False`），呼叫 roguelite 的純函式後把成長欄位寫回角色。roguelite 的 `ChoiceError` 轉成 `WorldActionError`。
   - `gain_xp(library, char, xp) -> (char, events)`：**共用的加經驗＋升級**。等級 ＝ min(`level_for(xp)`, `level_cap`)；每升 1 級：`attribute_points` ＋`roguelite.attribute_points_per_level`、`insight` ＋`insight_per_level`、最大 HP／法力增加量加到目前值（同 5A-4）；全部升完後若角色階級變了，主角技能照新階級重配（roguelite `sync_skill_tier`）。每級發 `leveled_up`（新增 `insight`、`skill_tier` 欄位）。
   - `elite_first_kills(...)`：打贏時，陣容裡每種還沒擊殺過的精英 ＋`insight_per_elite_kind`（記進 `elite_kills`），發 `insight_gained`。
3. **狀態欄位**（`CharacterState`，全部有預設值，`trpg-char/1` 不升版號，同 5A-4／5B-2 的慣例）：`insight`、`flash`、`flash_bases`、`pending_flash`、`generated_skills`、`skill_usage`、`skill_tier`、`attribute_spent`、`elite_kills`、`oath`、`oath_cooldown_until`。型別與意義同 `RunState`（`trpg.roguelite.state`）。`new_character` 記 `skill_tier`＝1 級的階級（開局不重配，同 6.34.9「開局保持原樣，第一次升階才重配」）。
4. **世界動作**（加進 `WorldAction`）：

   | 動作 | 欄位 | 地點與條件（不合法拋 `WorldActionError`，狀態不變） | 重用 |
   |---|---|---|---|
   | `allocate` | `attributes` | 沒有遭遇；點數 ≤ `attribute_points` | roguelite `allocate_attributes`；HP／法力上限同步 |
   | `respec` | — | 城鎮或營火、沒有遭遇（7.2 營火免費重配；城鎮比照換裝地點） | `respec_attributes` |
   | `flash` | `skill`、`slot`、`category` | 城鎮或營火、沒有遭遇（6.34.2 大世界花點地點）；閃現要「先上場用過」 | `open_flash` |
   | `flash_pick` | `pick`、`unequip` | 有 `pending_flash` | `pick_flash` |
   | `dissolve` | `skill` | 城鎮或營火 | `dissolve` |
   | `inherit` | `skill`、`source`、`records` | 城鎮或營火 | `inherit` |
   | `swear_oath` | `template`、`params`、`player_text`、`source`、`prompt_version` | 城鎮或營火、沒有誓約、`now ≥ oath_cooldown_until`；模板存在、參數合法 | — |
   | `release_oath` | — | 有誓約；`oath_cooldown_until = now + cooldown_seconds`（#106 現實 1 天） | — |

   有 `pending_flash` 時，除了 `flash_pick` 以外的動作一律拒絕（6.34.3「出題就扣點、一定要選」）。
   換技能（5A-4 的 `loadout`）改用 roguelite `set_loadout`，生成技能（閃現後的技能）也能換。
5. **事件**：`attributes_allocated`、`attributes_respecced`、`flash_offered`（技能、重閃欄、類別、花費、選項數）、`flash_picked`（舊 ID → 新 ID）、`skill_dissolved`（退回點數）、`skill_inherited`、`insight_gained`（來源、點數）、`skill_tier_changed`（舊階、新階、改名）、`oath_sworn`、`oath_released`；`battle_started` 加 `reinforcements`、`first_team`、`hero_statuses`。
6. **戰鬥接線**（`trpg.world.battle`）：
   - 規則包加入主角的 `generated_skills`（閃現、重配後的技能）。
   - 打完（勝負都算）：主角裝備的技能照這場的用法統計記「先上場用過」與 `skill_usage`（roguelite `after_battle_flash`，**不給** 每勝靈感，6.34.2「一般戰鬥不給」）。
   - 打贏的經驗與升級改呼叫 `gain_xp`；精英首殺給靈感。
   - **`next_battle`**（12.4）：buff／debuff 開場掛在主角身上；增援；打完（勝負都算）清空，撤退不消耗。
   - **先手**（12.4）。
7. **情境判定**（`trpg.world.situations`）：給的 xp 改呼叫 `gain_xp`，當下升級。
8. **誓約接點**：schema `trpg.content.world_oaths`（`OathTable`：`cooldown_seconds`、`templates`；`OathTemplateDef`：`id`、`name_zh`、`difficulty: easy|medium|hard`、`params`；參數 `choice`（允許值）或 `int`（範圍））；`ContentLibrary.world_oaths`（`world/oaths.yaml` 不存在＝`None`）。18.6 的 15 種模板與戰鬥中的加成、違反判定在 **5C-3**；本段只有接點與測試裡的最小樣本（代決 5A6-9）。
9. **測試**（12.6）與 **完成報告** `docs/phases/Phase5A-6報告.md`：交付、各接點的世界動作、可重播證明、代決、待 PM 決定。

### 12.3 角色階級與重配（6.34.9、07 7.6）

- 主角的角色階級 ＝ `hero_growth.skill_tier_by_level[等級]`；閃現出題、傳承、升階重配一律用 `world_library` 的視圖呼叫 roguelite，原型的 `offer_tier_by_level`（[1,1,2,2,3,3]）只留給 roguelite。
- 升階的當下（`gain_xp` 結束時，戰鬥之間）呼叫 `sync_skill_tier`：手寫技能重配成 `<原 ID>_t<階級>`，閃過的技能照新階級重推歷程；裝備、備用、閃現狀態、用法統計跟著改 ID。

### 12.4 下一場修正、增援與先手

- **buff／debuff**：`next_battle` 裡的狀態（依產生順序、同一狀態只掛一次）在開戰時掛到主角身上，持續回合照 `statuses.yaml` 的預設（引擎 `UnitSpawn.opening_statuses`，在擲先攻前施加，不擲抵抗）。
- **增援**（玩法 PM 定，18.4 補充）：每一筆 `reinforce`，從 **同地點遭遇表** 各陣容出現過的單位中去掉精英（`elite` 標籤），依 ID 排序後用 `Rng(fnv1a64("{battle_seed}:reinforce"))` 均勻抽 1 名加入敵方（照地點等級成長，同 5A-4 追加 A）；敵方已有 4 名時改成「敵人先手」。增援併進 `PreparedBattle.lineup`，看陣容時就看得到。
- **先手**：`BattleSetup.first_team`（新，預設 `None`）：設定時該陣營的單位依先攻排在最前面、另一陣營依先攻排在後面（引擎的行動順序整場固定）。斷崖幫寨：遭遇地點的遭遇表列了 `ally_first_threads`（雲嶺：`cliff_gang_fort` → `gang_fort_secret_door`），且角色持有其中一條有效個人線頭（以遭遇時間 `at` 判定到期）→ 我方先手。我方先手與敵人先手同時成立時抵銷（照先攻）。
- 引擎新欄位會出現在戰鬥紀錄的 `setup` → `LOG_FORMAT` `/99` → `/100`（`docs/phases/戰鬥紀錄格式變更.md` 1.1；舊紀錄不能重播，照慣例）。沒設定時結算與 `/99` 完全相同。

### 12.5 可重播

- 所有新動作進 `WorldAction` 聯集、寫進 `trpg-wlog/1`；閃現選項由角色技能種子衍生（roguelite 標籤 `flash/<技能>/<第幾次>/<重閃次數>`），`pending_flash` 存在角色快照裡，選擇時不重抽。重播照紀錄，不呼叫 LLM（本段 LLM 閃現提議不接，`llm=False`）。
- 戰鬥設定只由「角色快照＋遭遇＋內容庫」決定（`next_battle`、線頭、生成技能都在角色快照裡），重播逐位元相同。

### 12.6 測試

| 檔案 | 內容 |
|---|---|
| `tests/world/test_growth.py` | 階級表 1～3／4～7／8～10；`world_library` 不改原型；`gain_xp`：升級屬性點、靈感 +2、HP／法力同步、上限 10、升到 4 級重配技能（`_t2`）；戰鬥與情境判定給的經驗當下升級；精英首殺靈感只給一次 |
| `tests/world/test_flash_world.py` | 打完一場記「先上場用過」、一般戰鬥不給靈感；閃現（城鎮、營火可以，野外不行；點數不足；沒用過）→ 選 → 技能換新 ID、裝備跟著換、規則包有新技能能開戰；有待選時其他動作被拒；重閃、溶掉退一半、傳承；配點與重配（地點） |
| `tests/world/test_next_battle.py` | buff／debuff 開場掛在主角身上並消耗；撤退不消耗；增援 +1 名非精英、照地點等級、確定性；已滿 4 名改敵人先手；暗門在斷崖幫寨我方先手、別處不先手、線頭到期不先手、抵銷 |
| `tests/world/test_oath.py` | 立誓（地點、參數、同時 1 個）、解除後 1 天冷卻、沒有模板的內容庫拒絕 |
| `tests/engine/test_first_team.py` | `first_team` 的行動順序；`opening_statuses` 掛上；預設值時和原本相同 |
| `tests/world/test_replay.py`（加） | 戰鬥升級 → 配點 → 閃現 → 選 → 溶掉 → 立誓的日誌重播兩次逐字相同、寫出讀回相同 |

### 12.7 驗收

- `uv run pytest -q tests/world tests/roguelite tests/content tests/engine/test_first_team.py tests/test_architecture.py -n 8 --timeout=1800`；交件前 `tests/cli`（`-m "slow or not slow"`、`--timeout=3000`）。
- `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`；一場原型重播（`trpg battle --map swamp --seed 7 --log-json` ＋ `replay`）；世界日誌重播測試。

### 12.8 不做的事

- API、前端（5A-5）；經驗曲線、各來源經驗量、遭遇強度（5A-SIM）；到頂後經驗換靈感或材料（7.8「換算比例待定」）。
- 任務鏈段落、世界事件的靈感（5B-4、5F）；完整技能三選一與白板三選一在大世界的來源（任務、劇情、機遇、許願池；5B-4 之後）；LLM 閃現提議接線（外層，之後）。
- 誓約的 15 種模板內容、戰鬥中的加成與違反判定、佔被動欄位（5C-3）。

### 12.9 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 | 誰定 |
|---|---|---|---|
| 5A6-1 | 主角階級表 | 07 7.6（寫在 `hero_growth`，和 `enemy_growth` 同表） | **玩法 PM 定** |
| 5A6-2 | 增援 | 18.4 補充（同地點遭遇表、種子、非精英、照地點等級；滿 4 名改敵人先手） | **玩法 PM 定** |
| 5A6-3 | 增援的抽法 | 同地點各陣容出現過的非精英單位（去重、依 ID 排序）均勻抽；多筆增援各抽 1 名，滿 4 名後每筆改成敵人先手（一次就成立） | 開發 PM 定 |
| 5A6-4 | 「先手」的引擎意思 | 該陣營依先攻排在最前、另一陣營接在後面（引擎行動順序整場固定）；我方與敵人先手同時成立時抵銷 | 開發 PM 定 |
| 5A6-5 | 等級上限與到頂 | 上限 10；超過的經驗照累積，不換算（7.8「換算比例待定」） | 開發 PM 定 |
| 5A6-6 | 花靈感的地點 | 閃現、重閃、溶掉、傳承都只在城鎮與營火（6.34.2 大世界表）；配點任何沒有遭遇的時候（同原型「戰前都可以」）；重配在城鎮與營火 | 開發 PM 定 |
| 5A6-7 | 精英「每種」 | 精英範本（`elite` 標籤）以單位 ID 算一種；一般單位套詞綴的精英以「單位＋詞綴」算一種 | 開發 PM 定 |
| 5A6-8 | `next_battle` 的消耗 | 下一場戰鬥（勝負都算）全部消耗；撤退不消耗；同一個狀態只掛一次、持續回合照狀態預設 | 開發 PM 定 |
| 5A6-9 | 誓約模板 | 內容（18.6 的 15 種）與戰鬥判定在 5C-3；本段只有 schema、動作與測試樣本；`world/oaths.yaml` 不存在時立誓被拒 | 開發 PM 定 |
| 5A6-10 | 誓約冷卻 | 解除後 86400 秒（現實 1 天，#106）；數值在 content | 開發 PM 定 |
| 5A6-11 | 角色技能種子 | `fnv1a64("{season_seed}:{character_id}:skills")`（閃現選項、傳承、重配的種子；不佔世界亂數串流） | 開發 PM 定 |
| 5A6-12 | 戰鬥紀錄版號 | `BattleSetup.first_team`、`UnitSpawn.opening_statuses` 進紀錄 → `/100` | 開發 PM 定 |

## 13. 5A-7 詳細規格：新世界動作的 API 與前端

> 給實作 agent。只動 `src/trpg/api/`（`world_schemas.py`、`world_presenter.py`、`routes/world.py`、`world.py`；`run_presenter.py` 把既有的主角與待選閃現組裝函式公開，不改輸出）、`src/trpg/world/` 的 **小改**（`state.py` 加 1 個欄位 `last_battle`、`battle.py` 打完時寫它，見 13.4）、`tests/api/`、`tests/world/`（只加測試）、`client/`（大世界畫面、重用 `client/src/run/` 的配點與閃現元件、`BattleScreen` 開場說明、API 型別）、`client/openapi.json`。**不做** 誓約模板內容與戰鬥中的加成、違反判定（5C-3）；經驗曲線（5A-SIM）；事件卡與情境判定畫面（5B-5）；LLM 閃現提議與 LLM 立誓轉換。不改 `trpg.engine`、`trpg.roguelite`、戰鬥紀錄格式（`LOG_FORMAT` 不變）。
> 依據：06 6.34.2（大世界靈感：花在主城、小鎮、營火，和換技能同地點；一般戰鬥不給）、6.34.3（閃現流程、出題就扣點一定要選、重閃、溶掉退一半）、6.34.9（階級屬於角色、升階重配、傳承）、6.26（誓約）；07 7.2（配點、營火免費重配）、7.6、7.8；09 9.6.10 #106（大世界立誓：主城、小鎮、營火，同時 1 個，解除後現實 1 天不能再立）、9.6.11 #114（營火可換技能、閃現、重閃、溶掉、傳承、立誓）；本檔 11（5A-5）、12（5A-6，含 5A-6b：先手只影響第 1 輪、開場狀態不擲抵抗且最多 2 回合）；`Phase5A-5報告.md` 待決 1；`docs/開發PM交接.md` 6.5.1。

### 13.1 目標

5A-6 的成長接點在瀏覽器玩得到：**建角 → 打贏一場（經驗、升級、靈感）→ 配點 → 回小鎮閃現（待選時只能選）→ 重閃、溶掉、傳承、重配 → 立誓／解除（沒有誓約內容時「尚未開放」）**；下一場的 buff／debuff、增援、先手與開場狀態在遇敵陣容與戰鬥開場用中文說清楚；重新整理頁面仍看得到最近一次戰鬥的輸贏。規則全部照 `trpg.world`（API 不寫規則，前端不寫規則）。

### 13.2 API

| 方法與路徑 | 內容 |
|---|---|
| `POST /api/world/characters/{id}/actions` | `WorldActionRequest` 加上 5A-6 的 `allocate`、`respec`、`flash`、`flash_pick`、`dissolve`、`inherit`、`swear_oath`、`release_oath`（欄位同 `trpg.world.actions`）。`swear_oath` 從 API 只收 `source: "menu"`（LLM 轉換之後才接；代決 5A7-4）。不合法 422（`WorldActionError` 的中文訊息），戰鬥中 409（同 5A-5）。 |
| `POST /api/world/characters/{id}/flash-preview` | 閃現或重閃之前的預覽（同一輪的 `flash-preview`，用大世界的內容庫視圖與角色技能種子）：`{skill, slot}` → `FlashPreviewOut`；不扣點、不寫日誌。 |
| `POST /api/world/characters/{id}/allocation-preview` | 配點後的最大 HP、法力、耐力（同一輪的 `allocation-preview`）：`{attributes}` → `AllocationPreviewOut`。 |

**`WorldView` 新增**（全部由後端算好）：
- `hero`：一輪的主角格式 `HeroOut`（由 `as_run(char)` 經 `world_library` 組裝；屬性、已分配點、屬性影響、靈感、閃現規則、每招的閃現狀態、備用技能）——前端直接重用一輪的配點與閃現元件。
- `pending_flash`：待選閃現（一輪的 `PendingFlashOut`；沒有＝`None`）。
- `growth`：`insight`、`skill_tier`、`at_service`（在城鎮或營火）、`service_zh`（地點限制說明，例「閃現、重閃、溶掉、傳承、重配屬性、立誓只在城鎮與營火」）、`can_allocate`、`can_spend`（城鎮或營火、沒有遭遇、不在戰鬥、沒有待選）、`blocked_zh`（不能花點的原因；可以時 `None`）。
- `oath`：`available`（內容庫有 `world/oaths.yaml`）、`unavailable_zh`（沒有時「尚未開放」）、`current`（模板名、難度中文、參數文字、立誓時間）、`cooldown_until`、`cooldown_zh`（剩多久能再立）、`can_swear`／`swear_problem_zh`、`can_release`、`templates`（ID、名稱、難度中文、參數：`choice` 的允許值或 `int` 的範圍）。
- `next_battle`：角色身上的下一場修正，每筆一句中文（「下一場開場：〔狀態名〕（狀態說明，最多 2 回合）」「下一場增援 1 名敵人」）。
- `encounter` 加：`reinforcements`、`first_team`（`ally`／`enemy`／`None`）、`hero_statuses`（狀態 ID、名稱、說明、回合）、`opening_zh`（開場說明句子，例「我方先手：第 1 輪我方全部先動，第 2 輪起照先攻」「開場狀態：主角帶〔中毒〕2 回合（不擲抵抗）」「增援 1 名」）。
- `last_battle_zh`：最近一次戰鬥結果的一句話（地點、輸贏、輪數、經驗、升到幾級；沒有打過＝`None`），由角色快照算，重新整理也看得到（5A-5 待決 1）。
- `events`：新事件的中文句子：開戰（增援、先手、開場狀態）、升級（含靈感、角色階級）、升階重配、得到靈感（精英首殺）、配點、重配、閃現出題、選閃現、溶掉、傳承、立誓、解除誓約。

### 13.3 前端

- **右側狀態**：等級、經驗、靈感點、未分配屬性點、角色階級；有下一場修正時列出；最近一次戰鬥結果（`last_battle_zh`）。
- **「成長與技能」**：右側按鈕切換左欄（地點圖 ↔ 成長畫面）；成長畫面重用 `client/src/run/` 的元件：配點（`AttributeRespecSection`，重配按鈕只在城鎮與營火）、閃現（`FlashSection`）、重閃與溶掉／傳承（`CampfireSkillCare`）；前端把一輪的選擇轉成世界動作（`respec_attributes` → `respec`，其他同名同欄位）。不在城鎮或營火時，閃現、重閃、溶掉、傳承、重配、立誓的按鈕停用，畫面上方顯示 `growth.service_zh` 與 `blocked_zh`；配點任何沒有遭遇的時候都可以。
- **閃現待選**：有 `pending_flash` 時左欄固定顯示選項畫面（重用一輪的選項畫面），地點圖、服務按鈕、遇敵按鈕全部停用，並顯示「先選完閃現的變化」。
- **誓約**：成長畫面裡的「誓約」區：沒有誓約內容時「立誓（尚未開放）」停用；有內容時：選模板、填參數（選單或數字）、誓言文字選填 → 立誓；已有誓約時顯示內容與「解除誓約」（解除前確認，說明 1 天冷卻）；冷卻中顯示剩多久。
- **戰鬥開場**：遇敵陣容面板顯示 `opening_zh`；戰鬥畫面開場橫幅下加同樣的句子（`BattleScreen` 新增選填的 `openingNotes`）。
- 浮動卡一律用共用元件（6.5.1）；不加新美術。

### 13.4 `trpg.world` 的小改（最近一次戰鬥結果）

`CharacterState` 加 `last_battle: LastBattle | None = None`（`location`、`won`、`end_reason`、`rounds`、`xp_gained`、`level_before`、`level`、`at`；有預設值，`trpg-char/1` 不升版號，舊檔照讀）。`fight` 結算時寫入（勝負都算），其他動作不清除。重播得到相同的值（由日誌決定）。

### 13.5 測試

| 檔案 | 內容 |
|---|---|
| `tests/api/test_world_growth_api.py` | 打贏一場（AI 代打）→ `GET` 有經驗、升級、靈感、`last_battle_zh`；再 `GET` 一次句子還在；配點（成功、點數不足 422）；野外閃現 422、小鎮閃現 → `pending_flash` → 其他動作 422 → `flash_pick` → 技能換新 ID；`flash-preview`、`allocation-preview`；溶掉退點；重配（野外 422、小鎮可以）；沒有誓約內容時立誓 422、`oath.available` 為假、「尚未開放」；有樣本內容時立誓、解除、冷卻；`source: "llm"` 被拒；遇敵陣容的 `opening_zh`（先手、開場狀態、增援）；新事件句子 |
| `tests/world/test_last_battle.py` | 打贏、打輸都寫 `last_battle`；舊格式（沒有欄位）照讀；日誌重播相同 |
| `client/src/world/*.test.ts` | 一輪選擇轉世界動作、成長畫面可用與停用的判斷、待選時擋其他動作 |

### 13.6 驗收

- `uv run pytest -q tests/api tests/world -n 8 --timeout=3000`；`tests/cli -m "slow or not slow" --timeout=3000`；`npx vitest run`、`npm run build`；`ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`；OpenAPI 快照重產（`scripts/export_openapi.py` ＋ `gen:api`）。
- 瀏覽器實際走一遍（後端、前端用 8000／8001／8010 以外的埠）：建角 → **在畫面上點完一場並打贏**（勝利回寫、經驗、升級）→ 配點 → 回小鎮閃現一次（待選時其他動作停用 → 選）；截圖或 `read_page` 記錄寫進報告；浮動卡 6.5.1 抽查。

### 13.7 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5A7-1 | 最近一次戰鬥結果放哪 | `CharacterState.last_battle`（由 `fight` 寫入，可重播）；畫面一句話，不另存事件 |
| 5A7-2 | 成長畫面的位置 | 左欄切換（地點圖 ↔ 成長），閃現待選時固定顯示選項；右側只放摘要與按鈕 |
| 5A7-3 | 重用一輪元件 | `WorldView.hero` 用一輪的 `HeroOut` 格式；元件加選填的預覽函式與地點文字參數，一輪的行為不變 |
| 5A7-4 | 立誓的來源 | API 只收 `menu`（玩家從模板選單選）；LLM 轉換（6.26 安全流程）之後的段再接 |
| 5A7-5 | 解除誓約的地點 | 照 5A-6：有誓約就能解除（不限地點）；畫面先確認 |
| 5A7-6 | 開場說明的文字 | 先手：「第 1 輪〔我方／敵方〕全部先動，第 2 輪起照先攻」（5A-6b）；開場狀態：狀態名＋說明＋「最多 2 回合、不擲抵抗」（5A-6b）；增援：「增援 N 名（已在陣容裡）」 |

### 13.8 不做的事

- 誓約模板內容（18.6）、戰鬥中的加成與違反判定、佔被動欄位（5C-3）；LLM 立誓轉換與 LLM 閃現提議。
- 事件卡、情境判定畫面（5B-5）；新的技能來源（任務、劇情、許願池）；經驗曲線（5A-SIM）；戰鬥中途存檔（5A-5 待決 2）。

## 14. 5A-M1 詳細規格：引擎機制①（蓄力強招預告、死亡時留下表面、開場隱蔽、同門相護）

> 給實作 agent。主要動 `src/trpg/engine/`（`battle.py` 開場狀態、`reactions.py`／`skills/cast.py` 受擊鉤子、新模組 `death_surfaces.py`、`kin_ward.py`、`ai/utility.py`）、`src/trpg/content/`（`battle.py` 單位範本與狀態欄位、`environment.py` 反應與 AI 欄位、`world_enemies.py` 詞綴欄位）、`src/trpg/narrative/`（戰鬥紀錄文字）、`content/`（`statuses.yaml`、`reactions.yaml`、`ai_profiles.yaml`、新技能、雲嶺範本與 `world/enemies.yaml`）、`src/trpg/engine/runner.py`（`LOG_FORMAT`）、`docs/phases/戰鬥紀錄格式變更.md`、受影響的測試與快照。共用檔（`trpg.world`、`trpg.api`、`client/`）只在必要時小改；另一個 agent 在做 5A-7（API、前端大世界）。
> 依據：18 18.2.1（招牌「同門相護」：2 格內的同門受到攻擊時替他加一層小護盾、每輪 1 次，沉默／擊殺補師／拉開距離破解；青霧執事蓄力強招「九轉回天」提前一輪預告；詞綴「霧隱的」開場隱蔽 1 回合）、18.2.2（碎晶傀儡死後爆出源晶碎片＝帶電表面）；19（熔岩獸「熔核爆裂」死亡時在原地留下 2 回合火焰表面、寒燼蜥死後留冰面；熔核領主、Boss 的蓄力強招預告）；05 5.7（環境預告、強招預告：只有精英與 Boss 的蓄力型強招提前一輪在地圖上標出範圍，沿用環境預告的顯示方式；一般敵人意圖不顯示）；06 6.23 #5（延遲段：施放後帶「蓄力」、下回合開始釋放，倒下、暈眩、冰凍取消）；玩法 PM 2026-11-02（5A-M1 四個機制，做好後雲嶺替代品只改 content）；本檔 7.6 代決 5A3-1～5A3-3、12.4（`opening_statuses` 最多 2 回合）。

### 14.1 目標

四個機制都是 **資料設定** 的引擎機制，雲嶺的替代品（Phase5A-3 報告 5A3-1～5A3-3）換成正式機制只改 content。每個機制：pydantic schema、引擎實作（純函式、確定性）、戰鬥紀錄中文、AI 不會無視、測試。

### 14.2 機制與資料格式

1. **蓄力強招預告**（沿用 6.23 #5 延遲段，不另做一套）：
   - 強招＝`followup.when: delayed`、`release: next_turn` 的技能；施放時施放者帶 `charging`、發 `followup_charged`（預計範圍）；下回合開始以當下位置結算第二段；倒下、暈眩、冰凍取消。網頁的蓄力預告（`telegraph` 的 `charges`）、戰鬥紀錄文字已經有，不新增前端畫法。
   - 引擎補：延遲段第二段是 **治療／友方** 效果時（九轉回天：全隊回大量 HP），AI 估值改看預計範圍內 **受傷的友方**（`rewrite.delayed_heal_points` × 受傷友方數，含自己），不再只數敵人。
   - 「花一回合蓄力」：強招的 `ap_cost` ＝ `ap_per_turn`（3），蓄力那回合不能再做別的（content）。
   - 新技能 `skill_nine_turns_revival`「九轉回天」（青霧執事）：第一段 `self` 小護盾、第二段自己為中心 3×3 的友方治療（數值初值，見 5AM1-9）。
2. **死亡時留下表面**（狀態資料）：`StatusDef.on_death_surface: DeathSurfaceSpec | None`（`surface`：既有表面、`radius`：0～2 曼哈頓、`duration`：省略＝表面預設）。帶這個狀態的單位倒下（`unit_downed`）時，在倒下的位置（＋半徑內可站的格子）產生表面（`create_surface`，`cause: death_surface`；依 (y, x) 排序）。狀態是 `polarity: neutral`、`expires: never`（不會被淨化、驅散或奪取）；由範本的 `opening_statuses` 開場掛上（見 3）。
3. **開場隱蔽**（範本資料）：`UnitTemplate.opening_statuses: tuple[OpeningStatus, ...]`（`status`、`duration: 1～2 | None`，`None`＝狀態預設）。開戰時和 `UnitSpawn.opening_statuses`（5A-6 下一場 buff）一起在擲先攻前施加、不擲抵抗；有限持續回合照 5A-6b 最多 2。精英詞綴加 `EliteAffixDef.add_opening_statuses`（同格式）。霧隱＝`{status: concealed, duration: 1}`。
4. **同門相護**（內建反應）：`reactions.yaml` 新反應 `kin_ward`（`effect: shield_ally`、新事件 `kin_hit_in_range`）；`ReactionDef` 加 `range`（曼哈頓格數）、`kin_tag`（同門標籤）、`shield_dice`／`shield_flat`、`blocked_by_silence`。持有者（範本 `reactions` 寫一條 `kin_ward` 規則）在 `range` 格內、帶 `kin_tag` 的友方（不含自己）被敵人的攻擊（普攻或技能）**命中、傷害之前**，給他一層護盾（`shield` 效果，已有護盾時照護盾規則取大值）。佔本輪反應（`reactions_per_round`＝1，即「每輪 1 次」）；被沉默（`blocks_spells`）、暈眩時不能用；`auto`／`prompt`／`off` 照一般反應規則。多名持有者時依單位 ID 第一個能用的出手（一次攻擊只觸發 1 層）。

### 14.3 AI（`trpg.engine.ai.utility`；數值在 `ai_profiles.yaml` 的 `rewrite:`，初值）

- 預覽本來就會結算反應、延遲段與倒下觸發：同門護盾讓預估傷害變小、殺死碎晶傀儡的預覽有表面事件（`surface` 權重）、隱蔽讓命中率變低。
- **優先處理**：擊倒帶 `kin_ward` 反應規則的敵人（同門的護盾來源）× `priority_kill_points`；擊倒或使其 `skip_turn`（暈眩、冰凍）正在蓄力的敵人 × `interrupt_points`（打斷強招）。只在目標有這些特性時才加分，其他戰鬥分數不變。

### 14.4 雲嶺換正式機制（只改 content）

| 敵人／詞綴 | 原替代品 | 正式機制 |
|---|---|---|
| 青霧道童、煉丹師、水煉丹師、青霧執事 | — | 反應 `kin_ward`（2 格、`sect`） |
| 持劍弟子 | 挺身而出（5A3-1） | 拿掉挺身而出（被相護的前排） |
| 青霧執事 | 聖域＋回春＋調息（5A3-2） | 加「九轉回天」（蓄力強招），保留聖域、調息 |
| 碎晶傀儡 | 沒有（5A3-2） | 開場狀態 `shard_burst`（倒下時留表面） |
| 詞綴 霧隱的 | 受擊隱蔽（5A3-3） | 開場隱蔽 1 回合 |

護法武僧的挺身而出是 18.2.1「嘲諷／守護」本身，不動。陣法（陣眼石靈）、劍陣 ≤ 3 格、連心的（傷害分給同門）是 5A-M2，不在本段。

### 14.5 戰鬥紀錄與版號

- 文字：同門相護走 `reaction_triggered`（反應名「同門相護」）＋`shield_gained`；死亡表面走 `surface_created`（`cause: death_surface` 的說明：「X 倒下，留下…」）；開場狀態走 `status_applied`；蓄力走既有 `followup_charged`。
- `UnitTemplate`、`StatusDef`、`ReactionDef` 加欄位、結算新增 → `LOG_FORMAT` `/101` → `/102`（`戰鬥紀錄格式變更.md`）。沒用到這些欄位的戰鬥結算與 `/101` 相同。

### 14.6 測試

| 檔案 | 內容 |
|---|---|
| `tests/engine/test_mechanics_5am1.py` | 開場隱蔽 1 回合（範本與詞綴）；死亡表面（半徑、持續、不能被驅散）；同門相護（2 格內加盾、超出範圍不加、每輪 1 次、沉默不能用、非同門不加、技能命中也觸發）；九轉回天蓄力 → 下回合治療、被暈眩取消；AI：受傷友方時會施放九轉回天、優先擊倒同門相護持有者 |
| `tests/content/`（受影響） | schema 驗證（半徑、持續上限、反應欄位必填）；雲嶺範本與詞綴載入 |
| `tests/world/test_enemy_smoke.py`（既有） | 換機制後雲嶺陣容照樣打完 |

### 14.7 驗收

`uv run pytest -q tests/engine/test_mechanics_5am1.py tests/content tests/world -n 8 --timeout=1800`；交件前 `tests/cli`（`-m "slow or not slow"`、`--timeout=3000`）、`npx vitest run`、`npm run build`；`ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`；一場原型重播。

### 14.8 不做的事

- 陣法範圍加成、陣眼石靈、劍陣、傷害分給同門（5A-M2）；三方混戰（5B-M3）；Boss 階段與「霧鎖千山」（5F-2）；新表面種類與新美術。
- 單位卡上的「特性」欄（要改 API 與前端；目前開場狀態與反應規則已經顯示在單位卡的狀態與反應欄）。

### 14.9 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5AM1-1 | 蓄力強招的引擎 | 沿用 6.23 #5 延遲段（同一套蓄力狀態、預告與取消）；「打斷」＝倒下、暈眩、冰凍（沉默不打斷，同既有延遲段） |
| 5AM1-2 | 「花一回合蓄力」 | 強招 `ap_cost` 3（整回合）；下回合開始釋放後仍可行動 |
| 5AM1-3 | 誰有同門相護 | 補師型修士（道童、煉丹師、水煉丹師、青霧執事）；持劍弟子是被相護的前排；武僧保留挺身而出 |
| 5AM1-4 | 同門相護的次數與時機 | 佔本輪反應（每輪 1 次，和格擋共用）；命中後、傷害前；普攻與技能都算；一次攻擊只一層 |
| 5AM1-5 | 同門相護護盾量 | `1d4+2`（初值，`reactions.yaml`）；同門＝`sect` 標籤；沉默、暈眩時不能用 |
| 5AM1-6 | 碎晶傀儡的「帶電表面」 | 引擎沒有帶電表面、新表面要新美術 → 留下 **水**（半徑 1，水會導電：雷電打上去沿水擴散）；要真正的帶電表面待 PM 決定 |
| 5AM1-7 | 死亡表面的實作方式 | 狀態 `on_death_surface`（同定時炸彈「倒下時」的做法），由範本 `opening_statuses` 掛上；狀態中性、不倒數 |
| 5AM1-8 | 開場隱蔽的回合數 | `duration: 1`（在自己第 1 回合結束時移除）；範本開場狀態也受 5A-6b 的 2 回合上限 |
| 5AM1-9 | 九轉回天數值 | 第二段自己為中心 3×3 的友方治療 `4d8`（延遲段第二段只能是十字／方陣／環形，`2d8` 低於預算下限；實作時改）、`wis` 加成；冷卻 4、法力 12（初值） |
| 5AM1-10 | 戰鬥紀錄版號 | `/102` |

## 15. 5B-3 詳細規格：說書人接線

> 給實作 agent。只動 `content/world/narration.yaml`（新）、`src/trpg/content/world_narration.py`（新）、`src/trpg/content/world_events.py`（載入時一併載入說書模板）、`src/trpg/world/`（新增 `narration.py`；`state.py`、`actions.py`、`step.py` 小改）、`src/trpg/llm/prompts/storyteller.py`（新：prompt 文字與版本）、`src/trpg/narrative/storyteller.py`（新：組 prompt、呼叫 `LLMClient`、驗證、重試、降級）、`src/trpg/api/world_story.py`（新：外層組裝，從世界狀態取資料 → 說書人 → 世界動作；**不接路由**）、`tests/content/`、`tests/world/`、`tests/narrative/`、`tests/llm/`、`tests/api/`（只加測試）、CLI 快照（`trpg content check` 變了才重產）。**不做** 前端與 API 路由（5B-5）、任務狀態機、好感度、酒館傳聞內容（5B-4）、真模型評估（不連 8001）。不動 `trpg.engine`、`trpg.roguelite`、`narrative/events.py` 等戰鬥紀錄文字、`content/units/`。
> 依據：09 9.1（說書人分層；NPC 代理只帶人設、記憶與當下情境）、9.5（context 依序：固定系統提示 → 世界資料 → 當前場景狀態（從引擎讀，不從聊天推斷）→ 相關記憶；輸出經 canon 驗證器，違反則重新生成）、9.6.4 第 1、6 點（LLM 只依模板與世界狀態寫情境敘述、只負責敘述結果）、9.6.7 #3（自由聊天只換資訊：線索、隱藏任務入口、傳聞；不換道具、經驗、戰力）、#6（LLM 依世界狀態挑骨架、填角色與動機；引擎驗證合法性：角色存在、地點對；LLM 不能自己多生事件；線頭只能由事件結果產生）、#7（旁白約 1～3 句，可點「多講一點」）、9.6.10 #107（旁白簡潔具體、短句少形容詞；雲嶺古風；NPC 依人設卡當場說）；10 第 10 節（結構化輸出、pydantic、prompt 版本化放 `src/trpg/llm/prompts/`、LLM 輸出寫進事件日誌、重播不呼叫 LLM）、第 11 節（`<player_input>`、物品經驗資源只能由引擎產生）；`docs/專案計畫.md` 3.1（模型不可用時遊戲要能降級）；18 18.4、18.5；本檔 2.1、2.3、8.6（5B1-3）、10。

### 15.1 目標

說書人接上 5B-1／5B-2：事件觸發後 **挑骨架（只能從候選挑）＋填角色與動機＋短旁白**；情境判定前寫 **情境敘述**、判定後寫 **結果敘述**；在 NPC 所在地點可以 **自由聊天（只換資訊）**。四種敘述都經 `LLMClient`（測試用 `MockLLMClient`），輸出先過 pydantic 與靜態檢查，不合法帶錯誤重試，用盡或連不上模型時用 **content 裡的模板文字** 降級；外層把結果包成世界動作 `narrate`，由 `trpg.world` 再核對一次引用（NPC、地點、線頭存在且角色看得到），通過才寫進世界動作日誌。**重播照紀錄、不呼叫 LLM。** 敘述不改任何數值、不產生物品、經驗、補給、線頭；唯一的狀態變化是事件敘述換骨架（候選內）。

```
trpg.api.world_story（外層）          trpg.narrative.storyteller              trpg.world.narration
世界＋角色＋內容庫 → 請求（純資料）──▶ messages（資料區＋<player_input>）
  允許的骨架／NPC／地點／線頭             complete(json_schema) → clean → JSON
                                        → StoryText（pydantic）→ story_problems（靜態＋請求內引用）
                                        有錯帶 <errors> 重試（共 2 次）；用盡／連不上 → 模板降級
NarrateAction(scene, story, 來源, prompt 版本) ── narration_problems 不過 → 改用降級 ──▶ world_step
                                                                         引用核對（不過拋錯、狀態不變）
                                                                         事件敘述：換骨架、標記已敘述
                                                                         發 narrated 事件
```

依賴（2.3）：`trpg.world` 不匯入 `narrative`／`llm`；`trpg.narrative` 不匯入 `world`（只吃 `trpg.content` 的定義與純資料）；敘述的 pydantic 模型與靜態檢查放 `trpg.content.world_narration`，三方共用；組裝在 `trpg.api`。

### 15.2 交付項目

1. **schema `src/trpg/content/world_narration.py`**（`__all__` 明列、`ContentModel`、錯誤訊息繁中）：

   ```python
   StoryScene = Literal["event", "situation", "outcome", "chat"]
   # event＝事件開場（挑骨架＋角色＋動機＋旁白）；situation＝情境判定前的情境敘述；
   # outcome＝情境判定的結果敘述；chat＝NPC 自由聊天的回話

   class StoryText(_Strict):  # LLM 輸出（也是降級輸出）；extra="forbid"
       skeleton: str | None = None  # 只有 event：從允許的候選挑
       actor_zh: str = ""  # 只有 event：填角色（≤ 24 字）
       motive_zh: str = ""  # 只有 event：動機（≤ 60 字）
       text_zh: str  # 短旁白／回話：1～3 句、≤ 150 字（9.6.7 #7）
       more_zh: str = ""  # 「多講一點」（≤ 400 字；可空）
       npcs: tuple[str, ...] = ()  # 提到的 NPC（人設卡 ID，≤ 4、不重複）
       locations: tuple[str, ...] = ()  # 提到的地點（≤ 4、不重複）
       threads: tuple[str, ...] = ()  # 提到的線頭（≤ 4、不重複）

   def sentence_count(text: str) -> int  # 以 。！？!? 結尾的句數（沒有句號＝1 句）
   def story_problems(scene, story) -> list[str]  # 靜態：event 必須有 skeleton／角色／動機，其他場景不可有

   class StoryTemplates(ContentModel):  # content/world/narration.yaml（降級文字，內容即資料）
       tones: dict[str, str]  # 區域 → 語氣（9.6.10 #107；雲嶺古風）
       event_text: str; event_more: str; event_more_no_obstacle: str
       situation_text: str; situation_more: str
       outcome_text: dict[Outcome, str]  # success／partial／failure
       chat_text: str
       # 佔位符只能用規定的名稱（{who}、{want}、{obstacle}、{stakes}、{location}、{approach}、{name}），
       # 載入時檢查；格式化後必須通過 StoryText 的長度與句數限制
   ```

2. **載入**：`load_world_event_content` 一併載入 `world/narration.yaml`（`WorldEventContent.story: StoryTemplates | None`）；不存在＝`None`（降級時用程式內建的最小句子）。`tones` 的區域要有地點圖。加進 `library.files`，`trpg content check` 多一行摘要。

3. **雲嶺內容** `content/world/narration.yaml`（15.4）。

4. **`trpg.world`**：
   - `state.py`：`EventTrigger.narrated: bool = False`（有預設值、不升格式版本）。
   - `actions.py`：動作 `NarrateAction`（`kind="narrate"`、`scene`、`template`（situation／outcome）、`outcome`（outcome）、`npc`（chat）、`player_text`（chat，≤ 500 字，只存紀錄）、`story: StoryText`、`source: "llm"|"fallback"`、`prompt_version`）；事件 `narrated`（場景、最後的骨架、模板、NPC、`story`、來源）。
   - `narration.py`：`story_choices(library, world, char, scene, ...) -> StoryChoices`（允許的骨架、NPC、地點、線頭、禁止出現的文字；給外層餵 LLM、給引擎核對，兩邊同一個函式）、`narration_problems(...)`、`apply_narration(...)`（15.5）。
   - `step.py`：`world_step` 多一個分派。

5. **`src/trpg/llm/prompts/storyteller.py`**：`STORY_PROMPT_VERSION = "storyteller/1"`、系統指令（任務、風格、安全規則）四種場景各一段。

6. **`src/trpg/narrative/storyteller.py`**：請求資料類別（`StoryRequest`：場景、區域名稱與語氣、地點、骨架（event 為允許的候選）、模板、結果摘要、NPC 卡、持有線頭、允許的 ID、禁止文字、玩家文字）、`story_schema(request)`（ID 欄位都是列舉）、`build_story_messages(...)`、`tell_story(client, request, *, attempts=2, templates) -> StoryOutcome`（`story`、`source`、`attempts`、`errors`、`prompt_version`）、`fallback_story(request, templates)`。

7. **`src/trpg/api/world_story.py`**（外層，不接路由）：`event_story`、`situation_story`、`outcome_story`、`chat_story`：從世界狀態組請求 → `tell_story` → `NarrateAction`；組好的動作先用 `narration_problems` 核對，不過就改用降級（降級只引用允許清單內的東西，一定通過）。`client=None`＝直接降級（模型關閉）。

8. **測試**（15.7）與 **完成報告** `docs/phases/Phase5B-3報告.md`：交付、提示結構與注入防護、降級做法、可重播、代決、待 PM 決定。

### 15.3 四種場景

| 場景 | 前提（引擎檢查） | LLM 可以做的 | 允許的引用 | 狀態變化 |
|---|---|---|---|---|
| `event` | 有 `pending_event`、還沒敘述過、沒有 `pending_encounter` | 從允許的骨架挑一個（9.6.7 #6）、寫角色（`actor_zh`）與動機（`motive_zh`）、1～3 句旁白＋多講一點 | 骨架：`pending_event.candidates`；若其中有接得上有效線頭的骨架，只能從那些挑（「優先接線頭」，同 5B-1 8.6 第 6 點）。NPC：挑的骨架的 `npcs` ＋ 所在地點的 NPC。地點、線頭見下 | `pending_event.skeleton` 換成挑的骨架、`follows_thread` 依新骨架重算、`narrated=True` |
| `situation` | 有 `pending_event`、模板在本區且屬於該骨架、沒有 `pending_encounter` | 依模板寫情境敘述（9.6.4 第 1 點） | NPC：骨架 `npcs` ＋ 所在地點的 NPC | 無 |
| `outcome` | 模板在本區、`outcome` 是三段之一 | 敘述結果（9.6.4 第 6 點；結果與獎懲由外層從判定事件帶入，LLM 不能改） | 同上 | 無 |
| `chat` | NPC 在本區、人設卡地點＝角色所在地點、沒有 `pending_encounter` | 依人設卡回話（9.6.7 #3：只換資訊） | NPC：本區所有人設卡 | 無（不給物品、經驗、補給、線頭、好感度） |

共同：
- **地點**＝本區地點中角色看得到的（不是隱藏，或已發現）；**線頭**＝角色持有的有效線頭（個人＋世界，`expires_at > now`）。說書人只能提到已經存在、角色看得到的東西（9.6.7 #6「引擎驗證合法性」）；新線頭、揭露地點只能由事件結果產生（5B-2／5B-4）。
- **禁止文字**（9.5 canon 驗證的規則部分）：所有文字欄位不可含本區 **未發現的隱藏地點名稱**、本區 NPC 的 **祕密原文**（`secret_zh` 只給說書人參考，18.5）。
- 長度與句數照 `StoryText`；所有 ID 欄位在 JSON schema 是列舉，pydantic 驗證後再由 `story_problems` 與請求內的允許清單檢查。

### 15.4 雲嶺降級模板（`content/world/narration.yaml`；開發 PM 定、之後可改）

```yaml
tones:
  cloud_ridge: 古風：短句、少形容詞，帶一點文言；修士稱人「施主」
event_text: 在{location}，{who}擋在你面前。
event_more: '{who}想要{want}。擋在中間的是{obstacle}。賭上的是{stakes}。'
event_more_no_obstacle: '{who}想要{want}。賭上的是{stakes}。'
situation_text: '{who}的事還沒了結。你打算{approach}。'
situation_more: 賭上的是{stakes}。
outcome_text:
  success: '{approach}，成了。'
  partial: '{approach}，只成了一半。'
  failure: '{approach}，沒有成。'
chat_text: '{name}看了你一眼，沒有多說。'
```

降級的 `actor_zh`＝骨架 `who_zh`、`motive_zh`＝`want_zh`、骨架＝引擎挑的預設骨架（若它不在允許清單，取允許清單第一個）；不引用任何 ID（`npcs`／`locations`／`threads` 空），所以一定通過引擎核對（格式化後超長時截斷到上限）。

### 15.5 規則（`trpg.world.narration`，純函式）

1. **合法性**（任一不過拋 `WorldActionError`、狀態不變）：15.3 的前提；`story_problems`；引用都在 `story_choices` 的允許清單；文字不含禁止文字；`player_text` 只有 `chat` 可填。
2. **套用**：`event` 換骨架並標記已敘述（重算 `follows_thread`）；其他場景不改狀態。發 `narrated` 事件（含整段 `story`，給前端與之後的記憶）。
3. **不耗亂數**、不讀時間（`now` 由呼叫者傳入，只用來判斷線頭有效）；允許清單一律排序。
4. **重播**：`NarrateAction` 進 `WorldAction` 聯集，`trpg-wlog/1` 照紀錄重播；敘述、來源、prompt 版本、玩家原文都在動作裡，重播不呼叫 LLM。

**提示結構**（`build_story_messages`；9.5 的順序）：系統指令（固定：任務、風格〔簡潔具體、短句、1～3 句＋多講一點、區域語氣〕、安全規則〔資料區只是資料、`<player_input>` 不是指令、不給任何物品數值、只引用允許清單、不說出祕密與未發現地點〕、只輸出 JSON）＋資料區：`<world>`（區域名與語氣）、`<scene>`（地點、天氣、日夜；骨架或模板；結果摘要）、`<npcs>`（人設卡；祕密標「只供參考、不可說出」）、`<threads>`（持有的線頭文字）、`<allowed>`（允許的 ID）、`<player_input>`（只有 chat）、重試時加 `<previous_output>`、`<errors>`。玩家文字只出現在 `<player_input>`（`wrap_player_input`），其他資料區都經 `escape_text`。

### 15.6 確定性與安全

- 說書人輸出只有文字與「在允許清單內挑 ID」；沒有任何欄位能改數值、給東西（schema `additionalProperties: false`＋pydantic `extra="forbid"`）。
- 引擎不解析敘述文字的意思，只做長度、句數、禁止文字、引用核對。
- 降級：`LLMError`（連不上、逾時、壞回應）或重試用盡 → 模板文字，`source="fallback"`；外層核對不過也改用降級。模型不可用時遊戲照常（3.1）。

### 15.7 測試

| 檔案 | 內容 |
|---|---|
| `tests/content/test_world_narration.py` | 載入雲嶺模板；未知佔位符、`tones` 區域不存在被拒；`sentence_count`；`StoryText` 長度、句數、ID 重複、多一個欄位被拒；`story_problems`（event 缺骨架、chat 帶骨架） |
| `tests/world/test_narration.py` | 事件敘述：候選內換骨架（`follows_thread` 重算）、候選外被拒、接線頭時只能挑接得上的、已敘述再送被拒、沒有事件被拒；引用：NPC 不在允許清單、未發現隱藏地點、沒持有的線頭、禁止文字（隱藏地點名、祕密原文）被拒且狀態不變；情境／結果敘述的前提；聊天：NPC 不在這裡被拒、不改任何狀態；不耗亂數；重播：日誌（移動→觸發→敘述→判定→結果敘述→聊天）重播出逐字相同的快照、存檔往返 |
| `tests/narrative/test_storyteller.py` | schema 列舉；玩家文字只在 `<player_input>`、注入字串被跳脫、系統訊息不含玩家文字；Mock 合法 JSON → `llm`；壞 JSON／候選外骨架／超過 3 句／提到禁止文字 → 帶錯誤重試 → 成功或降級；`LLMUnavailable` → 降級；降級文字照模板、沒有模板檔時用內建句子；prompt 版本、四個場景的系統指令都含安全規則 |
| `tests/api/test_world_story.py` | 外層組裝：事件、情境、結果、聊天四種動作都能 `world_step`；Mock 回候選外骨架 → 降級仍可套用；`client=None` → 降級 |

### 15.8 驗收

- `uv run pytest -q tests/world tests/narrative/test_storyteller.py tests/api/test_world_story.py tests/content/test_world_narration.py tests/content/test_world_events.py tests/llm tests/test_architecture.py -n 8 --timeout=1800 -m "not llm"` 通過；交件前加跑 `tests/cli`（`-m "slow or not slow"`、`--timeout=3000`）。
- `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports` 通過；`C901` ≤ 15。

### 15.9 不做的事

- 不接 API 路由、不做前端（事件卡、NPC 對話畫面在 5B-5）；不做好感度、任務、酒館傳聞、線頭到期結局（5B-4）；不做說書人記憶（9.6.7 #8：之後用 `narrated` 事件與日誌做）、canon 驗證的小模型部分（只做規則）。
- 不讓聊天產生線頭、揭露地點或任何狀態變化（「隱藏任務入口、傳聞」的發放在 5B-4 的任務與傳聞資料裡做）。
- 不做真模型評估（不連 8001）；不做串流。

### 15.10 代決（開發 PM 定，最保守預設；寫進完成報告）

| # | 事項 | 代決 |
|---|---|---|
| 5B3-1 | 敘述怎麼進日誌 | 新世界動作 `narrate`（外層送），引擎核對後發 `narrated` 事件；不另開敘事日誌 |
| 5B3-2 | 事件敘述可以換骨架幾次 | 每個事件 1 次（`narrated` 旗標）；有接得上線頭的候選時只能在那些裡挑 |
| 5B3-3 | 允許引用的範圍 | 地點＝角色看得到的本區地點；線頭＝持有的有效線頭；NPC：事件／情境／結果＝骨架 NPC＋所在地點的 NPC，聊天＝本區全部人設卡 |
| 5B3-4 | canon 檢查（9.5）先做哪些 | 規則：未發現隱藏地點名、NPC 祕密原文、引用 ID、長度、句數；小模型檢查之後 |
| 5B3-5 | 聊天的限制 | NPC 要在角色所在地點；不改任何狀態；玩家文字 ≤ 500 字，只放 `<player_input>` |
| 5B3-6 | 旁白長度 | `text_zh` 1～3 句、≤ 150 字；「多講一點」≤ 400 字；角色 ≤ 24 字、動機 ≤ 60 字 |
| 5B3-7 | 重試與降級 | 共試 2 次（同 5B2-10）；用盡、連不上、外層核對不過 → content 模板文字；沒有模板檔 → 程式內建的最小句子 |
| 5B3-8 | 結果敘述的核對 | 引擎只核對模板與引用（判定結果不存在狀態裡）；結果與獎懲由外層從判定事件帶進請求，LLM 不能改 |
| 5B3-9 | 組裝放哪 | `trpg.api.world_story`（world 與 narrative 互不匯入）；路由與畫面在 5B-5 |


## 16. 之後各段規格

（5A-M1、5B-3 驗收後補上之後各段。）
