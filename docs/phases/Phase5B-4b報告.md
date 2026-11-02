# Phase 5B-4b 完成報告：5B-4 收尾

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 19 節（先寫規格、commit 後實作；和 main 合併後 5B-5 為第 18 節、本段第 19 節、之後各段第 20 節）。
> 玩法 PM 2026-11-03 追加兩項（19.14，**玩法 PM 定**）：(a) 任務入口不例外，說明指向已知的鄰近地點；(b) 城鎮是安全區，有戰鬥解法的骨架不在城鎮出現。已照做。

## 1. 七項各做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 好感度新取得方式（18.7.6） | 任務步驟加 `npcs`（有關的 NPC），完成時每位 +15（`affinity.yaml` 的 `quest_step_delta`；和 `reward.affinity` 合併成一筆）；`talk` 每天（6 點刷新）第一次 +3（`daily_talk_delta`，角色新欄位 `talk_days`），先加再決定能說什麼。原本 5B-4 的單筆好感度獎勵（小蓮 +10、青崖 +20、霜音 +10）改成這個規則 | `world/quests.py`、`world/social.py`、`content/world/quests/`、`affinity.yaml` |
| 2 | 信賴的祕密解鎖骨架 22（18.7.7） | 骨架 22 `granny_past`（霧渡鎮、`unlock_only`、`shared_threads: [gang_fort_secret_door]`）、兩個情境模板 `granny_parley`（意志）／`granny_notice`（感知），DC 8，成功才給「斷崖幫寨的暗門」。渡婆婆的祕密加 `unlocks_skeleton`，文字改成不提暗門。`talk` 說出祕密時解鎖（`skeleton_unlocked`），身上沒事件就立刻觸發（候選只有它）；沒解鎖的骨架在擲骰前濾掉（舊角色亂數不變）。線頭只由事件結果產生（#85） | `world/social.py`、`world/events.py`、`content/world/events/`、`situations/`、`social/` |
| 3 | skillgen 區域偏向 | `CandidateRequest.region_keywords`：新方向把玩家還沒有的區域關鍵字排前面（白板版與完整版都套用；通用池擲骰照舊）。雲嶺 `region_keywords: [wet, charged, concealed]` 寫在 `content/world/quests/cloud_ridge.yaml`，用在區域任務鏈（`chain`）的三選一（`bias_keywords` 有填時覆寫）。`make_offer` 加 keyword-only 參數，預設＝原行為 | `skillgen/candidates.py`、`whiteboard_candidates.py`、`roguelite/offers.py`、`world/quests.py` |
| 4 | 新手鏈保底 | `SkillOfferReward.mix`（加深／橋接／新方向張數）、`min_passive`；白板產生器照組成產生，第 2 張新方向用 `fork("new/1")`、避開用過的關鍵字；被動不足時從最後一張往前換成同種類的被動白板（`fork("passive/<i>")`）。新手鏈 3 步都是 1／0／2、至少 1 張被動 | `skillgen/whiteboard_candidates.py`、`content/world/quests/` |
| 5 | 放棄／交涉／戰鬥解法結算＋骨架 9 人情抵用 | 新世界動作 `event_solve`（`solution`、`use_thread`）。放棄：清事件、無獎懲（`abandoned`）。交涉：不擲骰，付 `cost_supplies` 或用 `waive_thread` 的個人線頭抵（用掉，`thread_spent`），留解法的 `threads`。戰鬥：在所在地點開一般遭遇（同遇敵函式，撤退留原地），打完或撤退的那個動作結算（勝＝成功留線頭、輸或撤退＝失敗）。骨架 9：補給 2 或用「商人欠你人情」抵。事件好感度改看 `event_resolved`，交涉、戰鬥結果也算 | `world/solutions.py`（新）、`world/step.py`、`content/world/events/` |
| 6 | 線頭到期結局 | `ThreadDef.on_expire_flag`；`world_step` 分派動作 **之前** 結算到期、有結局的線頭（個人→劇情旗標、世界級→世界旗標，`thread_expired`）。遭遇表 `variants`：有旗標時該地點改用變化陣容，打贏那一場移除旗標（`story_flag_cleared`）。「二當家記恨你」→ `scarface_rises`：斷崖幫寨「坐大的疤面」（盜賊隊長＋盜賊＋霧狼×2）；「觀內有人私通盜賊」→ `temple_traitor_strikes`：山門「叛徒戰」（青霧執事＋盜賊×2＋修士劍客），主線第 ③ 步多一條路（在山門打贏叛徒戰陣容） | `world/endings.py`（新）、`world/encounters.py`、`world/battle.py`、`content/world/encounters/` |
| 7 | 導師任務鏈 3 步（18.7.5） | 任務 `mentor_qingya_trial`（`chain`、giver 青崖、開始條件＝旗標 `mentor_qingya`）：① 閃現（新條件 `growth: [flash]`，`flash_picked` 加 `slot` 分辨閃現／重閃）② 霧天打贏且用過帶隱蔽或帶電的技能（`win_battle` 加 `weather`、`skill_keywords`；`battle_ended` 加 `skills_used`）③ 重閃／溶掉／傳承（`growth`）。每步靈感 +1、青崖 +15；第 ③ 步旗標 `title_qingya_disciple`（稱號「青崖門下」）。不給技能、不給經驗 | `content/world/quests/`、`world/quests.py`、`world/battle.py`、`world/growth.py` |

玩法 PM 追加（19.14）：
- (a) 「丹爐之謎」說明改「柳掌櫃說藥師谷的谷底似乎還有一處洞窟」、步驟「找到藥師谷谷底的那處洞窟」；柳掌櫃的入口文字同；「霜音的謎」說明改「狐火在北坡獵場的霧裡指向一座山崖」。測試：任務說明、步驟、入口文字都不含隱藏地點名。
- (b) `world_event_problems` 加載入檢查：有戰鬥解法的骨架 `locations` 含城鎮 → 載入失敗。燈籠隊（17）移到渡口石階、竹林小徑（夜晚）；霧渡鎮只剩骨架 16、22。戰鬥解法在不能遇敵的地點另有執行期拒絕。

## 2. 資料格式摘要（新欄位全有預設；`trpg-char/1`、`trpg-world/1`、`trpg-wlog/1` 不升版號）

- 事件骨架：`unlock_only`、`shared_threads`；解法 `threads`（combat／parley，≤ 2）、`cost_supplies`、`waive_thread`（parley）；線頭 `on_expire_flag`。
- 遭遇表：地點 `variants: [{flag, group, elite?}]`。
- 任務：`QuestTable.region_keywords`；步驟 `npcs`；`SkillOfferReward.mix`／`min_passive`；條件 `flag`（狀態）、`growth`（事件）、`win_battle` 的 `location` 可省略並加 `group`／`weather`／`skill_keywords`。
- 聊天：`TalkEntry.unlocks_skeleton`（只限 secret、本區 `unlock_only` 骨架）。
- 好感度規則：`quest_step_delta`、`daily_talk_delta`（schema 預設 0）。
- 狀態：角色 `talk_days`、`unlocked_skeletons`；`EventTrigger.combat_solution`；`EncounterLineup.variant`。
- 動作 `event_solve`；事件 `event_solved`、`thread_spent`、`thread_expired`、`story_flag_cleared`、`skeleton_unlocked`；`event_resolved.outcome` 多 `abandoned`；`flash_picked.slot`、`battle_ended.skills_used`。

## 3. API 接點（給下一段打開前端；本段沒動路由與前端）

- 解法結算是世界動作 `{"kind": "event_solve", "solution": <骨架 solutions 索引>, "use_thread": <線頭 ID 或 null>}`（`trpg.world.actions.EventSolveAction`），走一般的 `world_step`；需要加進 `POST /api/world/.../actions` 收的動作聯集（`src/trpg/api/world_schemas.py`）。
- 回傳事件：放棄／交涉＝`event_solved`（→ `thread_spent`）→ `thread_added`… → `event_resolved`；戰鬥＝`event_solved` → `encounter`（之後照遭遇面板 `fight`／`retreat`，打完那一次回 `event_resolved`）。
- 事件卡要改的顯示（`world_story_view._solutions`）：戰鬥（所在地點不能遇敵時停用，原因「這裡打不起來」）、交涉（顯示付出補給 `cost_supplies`，持有 `waive_thread` 時多一個「用〔線頭〕抵」按鈕）、放棄可用；機遇仍「之後開放」。戰鬥解法進行中（`pending_event.combat_solution` 不是 null）時事件卡顯示「戰鬥中」。
- 聊天：`talk` 現在會改角色（每天第一次 +3、解鎖骨架並可能觸發事件）；事件句子可加 `skeleton_unlocked`、`thread_expired`、`story_flag_cleared`。

## 4. 可重播與原型不變

- 全部是世界動作，寫進 `trpg-wlog/1`；到期結算、戰鬥解法結算都在 `world_step` 裡由「日誌＋內容庫＋賽季種子」決定，不讀時間、不呼叫 LLM。`tests/world/test_quest_replay.py::test_5b4b_log_replays_identically`：交涉（人情抵用）→ 移動 → 到期結局 → 聊天解鎖 → 祕密事件判定，重播兩次逐字相同、存檔往返相同。
- 原型 roguelite：`make_offer` 的新參數預設＝原行為，`CandidateRequest` 新欄位預設＝原行為；`tests/skillgen/test_region_bias.py::test_default_inputs_keep_the_original_candidates` 逐字比對；`tests/roguelite`、`tests/skillgen`（含 `test_refactor_3wr2` 行為快照）不需重產。

## 5. 代決（照規格 19.13；最保守預設）

| # | 事項 | 代決 | 誰定 |
|---|---|---|---|
| 5B4b-1 | 「和該 NPC 有關的任務步驟」 | 每步在資料寫 `npcs`，不自動算 giver；原本單筆好感度改成統一 +15 | 開發 PM |
| 5B4b-2 | 每天第一次聊天 | 6 點刷新的日子；先加 +3 再決定能說什麼 | 開發 PM |
| 5B4b-3 | 祕密解鎖的事件何時出現 | 說出祕密那次立刻觸發；之後在霧渡鎮照一般擲骰也會出現 | 開發 PM |
| 5B4b-4 | 骨架 22 模板 | DC 8、危險度 1；成功給暗門＋0.5 份經驗、部分成功只給一半經驗、失敗無 | 開發 PM |
| 5B4b-5 | 區域偏向用在哪 | 只用在區域任務鏈（含導師鏈，但它不給技能）的新方向；新手鏈、主線不偏向；通用池擲骰照舊 | 開發 PM |
| 5B4b-6 | 新手鏈「至少 1 招被動」 | 每一組三選一至少 1 張被動（不強迫選） | 開發 PM |
| 5B4b-7 | 交涉的付出 | 沒有金幣與道具：付錢、青竹節、換補給都用補給（1／2／1）；不擲骰、一定成功 | 開發 PM |
| 5B4b-8 | 人情抵用 | 玩家選擇時才用掉；只能用個人線頭 | 開發 PM |
| 5B4b-9 | 戰鬥解法 | 在所在地點開一般遭遇；勝＝成功留線頭，輸或撤退＝失敗；經驗只有戰鬥本身 | 開發 PM |
| 5B4b-10 | 解法留的線頭 | 照同骨架情境判定成功時的線頭；#3 付錢不留線頭 | 開發 PM |
| 5B4b-11 | 到期結局的表現 | 旗標 → 地點遭遇改成變化陣容，打贏那一場結束；叛徒戰也能完成主線第 ③ 步 | 開發 PM |
| 5B4b-12 | 導師任務鏈 | `chain`、只給靈感 +1 與好感度、不給經驗；稱號＝劇情旗標 | 開發 PM |
| 19.14 (a) | 任務說明不寫隱藏地點名 | 指向已知的鄰近地點 | **玩法 PM 定** |
| 19.14 (b) | 城鎮安全區 | 載入檢查擋有戰鬥解法的骨架；燈籠隊移到渡口石階、竹林小徑 | **玩法 PM 定** |

實作時另定：
- 「坐大的疤面」原本想用盜賊隊長＋詞綴「連心的」（18.7.4），但盜賊隊長、青霧執事本身已是精英、不能再套詞綴（遭遇表檢查擋下），所以變化陣容直接放精英單位、不加詞綴。
- 第 2 張新方向不擲通用池（只有第 1 張照 #55 擲）。
- 到期結局只處理有 `on_expire_flag` 的線頭；其他到期線頭照 5B-1 留著（無效、不佔上限）。

## 6. 待 PM 決定

1. **好感度速度**：照 18.7.6，渡婆婆在新手鏈 3 步＋主線第 1 步就到 60（信賴），約第 2 天；青崖約第 3～5 天。比「第 5 天 1～2 名」快一點，是否要把主線第 ① 步的 `npcs` 拿掉（只改 content）。
2. **疤面的「連心的」**：精英不能再套詞綴；要保留「連心」需要允許精英套詞綴或另做疤面範本。
3. **機遇解法的結算**（入口、技能，07 7.6「機遇」來源）還沒做；`event_solve` 對機遇拒絕。
4. **戰鬥解法的陣容**：目前就是該地點的一般遭遇表，不依骨架（例：護送戰、不殺獵人、撤離勝利條件都用一般勝利）。要依骨架指定陣容或勝利條件需要另排。
5. **祕密事件重複出現**：骨架 22 解鎖後在霧渡鎮可以重複擲到（同其他骨架）；是否改成解決後就不再出現。
6. **世界級線頭的到期結局**：資料沒填（「霧魅從裂痕湧出」「碎片被送往灰燼荒原」），世界旗標的效果也還沒有資料會用。
7. **導師任務鏈第 ② 步**只認「這場用過」的技能（`battle_ended.skills_used`，來自用法統計）；反應技觸發是否算「用過」照用法統計的定義。

## 7. 檢查

見交件訊息（最後一次檢查的數字）。
