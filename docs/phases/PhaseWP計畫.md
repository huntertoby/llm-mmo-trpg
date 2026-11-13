# Phase WP 計畫｜許願池（主城花任務幣許願，LLM 提議完整技能）

> 開發 PM 派的規格＋實作 agent 起草（2026-11-13）。使用者核可（專案 PM 轉達）：「都按照建議」。
> 設計依據：`docs/design/07-角色成長.md` 7.6（新技能來源表「許願池」、各來源配額表、**許願池**小節）、`docs/玩法決定紀錄.md` #88（2a A：一句話描述、LLM 對到關鍵字出 3 招挑 1，也可用選單；2b A：可都不拿、次數照扣、任務幣退一半）、`docs/design/09-世界與敘事.md` 9.6 上限表（**每週 2 次**）與「算角色：任務幣、許願池次數」、`docs/design/08-裝備.md` 8.15（任務幣用途）、`docs/design/06-技能.md` 6.34.7（預先生成、10 秒退回、日誌只記最後給出的版本、重播不呼叫 LLM；#126 主城用中性奇幻）；`CLAUDE.md` 守則 1、3、6、7。
> 共用的 LLM 出招流程照 `docs/phases/PhaseLF計畫.md` 第 2 節（第 5 點寫明許願池怎麼接）。
> 實作者先讀 `docs/dev/上手-LLM.md`；主城與世界動作讀 `docs/dev/上手-roguelite開局與入門期.md`。
> **不改 `docs/design/`**；設計沒寫到的列在第 6 節（照最保守的做法先寫進規格），要使用者決定的列在第 7 節。

## 0. 現況（2026-11-13 main `b1a76452`）

| 項目 | 現況 | 出處 |
|---|---|---|
| 主城的許願池 | 地圖上已有物件 `wishing_pool` 與 NPC `pool_keeper`，說明卡寫「還沒開放」；沒有任何規則 | `content/world/fields/capital/capital.yaml` |
| 任務幣 | `CharacterState.quest_coins`；任務、懸賞、今日目標、影子被借用會加；鐵匠高階打造會扣 | `world/economy.py`、`world/crafting.py` |
| 每週 | `world/season.py::week_of`（早上 6 點刷新的日子、`rules.week_days` 天一週，賽季開始那天是第 0 週）；商店每週限量已用 | `world/economy.py::weekly_left` |
| 完整技能三選一 | 機遇已有：`world/solutions.py::_opportunity_offer` → `supply(OfferGenRequest)` → `checked_offer` → `quests.store_offer` → `offer_pick` | `world/solutions.py`、`world/story_gen.py` |
| 指定關鍵字的候選 | `make_offer(..., pinned_keyword=, region_keywords=)` 三張都帶指定的關鍵字 | `roguelite/offers.py`、`skillgen/candidates.py::_pinned` |
| 玩家文字進 prompt | `propose_skill(player_text=)` → `build_skill_proposal_messages` 包進 `<player_input>`（跳脫、截斷 500 字）；`make_proposer` 沒有開這個參數 | `llm/propose.py`、`llm/prompts/builder.py`、`llm/candidate_source.py` |
| LLM 出招流程 | 請求 → `world_pregen`（單一佇列、只放記憶體、等 ≤ 10 秒）→ `supply` → 日誌 `generated` → `recorded` 重播 | `world/generated.py`、`api/world_pregen.py`、`world/replay.py` |

## 1. 範圍總覽

| 段 | 內容 | 依賴 | 撞檔注意 |
|---|---|---|---|
| **WP-1** 後端核心 | 世界動作 `wish`（願望文字或選單關鍵字）；主城、入門期、遭遇、每週次數、任務幣的檢查；扣款與次數；LLM 對關鍵字＋提議完整技能（`<player_input>`）；引擎驗證；沒有 LLM／沒對上時的退路；三選一都不拿退一半；日誌與重播；存檔版號；Mock 測試 | 無 | 不動 `skillgen/` 的轉型與模板邏輯、`content/flash_templates.yaml`（TF-1 進行中）；不動 `client/`、`api/world_schemas.py` 的請求 union（WP-2） |
| **WP-2** API 與等待 | `WorldActionRequest` 加 `WishAction`；`WorldView.wish`（費用、本週剩幾次、退款、選單、LLM 開不開、不能許的原因）；`pregen/wait` 加 `kind: "wish"`（帶願望文字，等待提示同閃現）；三選一標題與故事行；`wishing_pool`／`pool_keeper` 的說明卡換成面板入口（`panel: wish`）；PM 重產 OpenAPI | WP-1 | `api/world_schemas.py`、`api/world_pregen.py`、`content/world/fields/capital/capital.yaml` |
| **WP-3** 前端 | 許願池面板（文字框＋送出、改用選單挑 1～2 個關鍵字、費用與本週次數、不能許的原因）；送出前等待提示（同閃現）；三選一畫面的標題「許願池」與「都不拿（退 N 任務幣）」；本機 LLM 實機截圖 | WP-2 | `client/` |

## 2. 規則（設計＋本規格的保守補定）

1. **在哪裡**：角色在主城區域（`region == "capital"`）。不要求站在池邊（待決 1）。
2. **誰能許**：不在入門期（`in_starter_period` 為假：開局已結束，或已正式選定）；沒有待處理的遭遇；沒有待選的閃現、三選一（`world_step` 本來就擋）。
3. **次數**：每個角色每週 `per_week`（2）次；週＝`week_of(now)`。紀錄 `CharacterState.wish_week = {week, used}`，換週視為 0。**按下許願就算一次**（#88「次數照扣」）；都不拿也算。
4. **費用**：每次 `cost_quest_coins` 任務幣（設計沒寫數字，初值 4，待決 2），許願時先扣。任務幣不足不能許。
5. **兩種許法**（#88 2a）：
   - **願望文字**（`text`，1～`text_max_chars` 字，初值 60，待決 3）：LLM 從選單對到 1～2 個關鍵字，再以這些關鍵字出完整技能三選一；**願望文字只進 prompt 的 `<player_input>`**（對關鍵字那一步、提議技能那一步都是），不進鍵以外的任何引擎輸入（守則 7）。
   - **選單**（`keywords`，1～2 個不重複的關鍵字）：不呼叫 LLM，照關鍵字用組合器與技能池出三選一。
   - 兩個欄位剛好給一個。
6. **選單**＝內容庫的關鍵字，扣掉開局隱藏的（`start_hidden`；待決 4）。「任何池」：出題不限區域技能池（`region=None`），名稱與描述用中性奇幻（#126）。
7. **出題**：完整技能三選一（`reason="complete"`），角色目前的階級，`pinned_keyword`＝第 1 個關鍵字（三張都帶它）、`region_keywords`＝全部關鍵字（第 2 個關鍵字優先進「橋接／新方向」那一格）（待決 5）。LLM 版一份最多請 `llm_cards`（初值 1）張（同機遇 6L-2b），其餘組合器與技能池補滿（設計「LLM 提議 1～3 招」的下限；待決 6）。
8. **引擎驗證**（守則 3）：LLM 對的關鍵字要在選單內、1～2 個、不重複；LLM 的三選一要是完整技能、階級相同、候選與標示一一對應（`checked_offer`），而且每張都帶第 1 個關鍵字。數值一律由預算器補（提議器內）；不合格的部分退回：
   - 關鍵字合格、三選一不合格（或 LLM 沒提出技能）→ 用同樣的關鍵字照常算組合器版（`made_by="composer"`）。
   - 關鍵字不合格或沒拿到（模型關閉、逾時、對不上）→ **整個動作被拒、不扣錢不算次數**，原因句請玩家改用選單（「退回選單版」）。
9. **不滿意**（#88 2b）：三選一可以都不拿（`offer_pick` 不帶 `pick`），次數照扣、退還 `refund_permille`（500‰，捨去）的任務幣。退款數存在待選的三選一上（`PendingOffer.refund`），內容改了也照許願當時的費用退。
10. **時間**：世界引擎不讀時間（`now` 由 `WorldStore` 傳入）、不呼叫 LLM；LLM 只在 API 層的生成函式裡。

## 3. WP-1 後端核心（本次實作）

### 3.1 要做的

1. **內容規則**：`content/world/rules.yaml` 加 `wish:`（`per_week: 2`、`cost_quest_coins: 4`、`refund_permille: 500`、`text_max_chars: 60`、`max_keywords: 2`、`llm_cards: 1`）；schema `content/world_rules.py::WishRules`。
2. **世界動作**（`world/actions.py`）：`WishAction{kind:"wish", text?: str, keywords: tuple[str, ...]}`（剛好給一個）；事件 `WishMadeEvent{via: "text"|"menu", keywords, made_by: "llm"|"composer", coins_spent, used, refund}`。`PendingOffer.source`、`SkillOfferedEvent.source`、`SkillOfferTakenEvent.source` 多 `"wish"`；`SkillOfferTakenEvent` 多 `refund`（都不拿時退的任務幣，0 不輸出）。
3. **規則**（新檔 `world/wish.py`）：`wish_menu`、`wish_problem`（主城、入門期、遭遇、次數、任務幣；畫面與送出共用）、`wishes_left`、`wish_request`、`apply_wish`；`step.py` 掛 `WishAction`；`quests._take_offer` 都不拿時依 `PendingOffer.refund` 退任務幣。
4. **生成請求與紀錄**（`world/generated.py`）：`WishGenRequest{character_id, key, text, menu, run, region}`、`WishGen{kind:"wish", key, source: "llm"|"partial"|"none", keywords, offer?, attempts, codes, prompt_version}`；`Generated` union 加 `WishGen`。鍵＝`input_key("wish/{角色}/{offers_made}", {文字, 選單, 技能種子, 階級, 技能列…})`。
5. **LLM 端**（新檔 `llm/wish.py`、`llm/prompts/wish.py`）：
   - `match_wish(client, library, text, menu)`：系統指令固定（安全規則同技能提議）；資料區 `<request>`（選單：ID、名稱、一句說明；最多幾個）＋`<player_input>`（`wrap_player_input`）；JSON schema `{"keywords": [enum]}`（1～2 個）；驗證（在選單內、不重複、數量）不過帶 `<errors>` 重試（≤ `max_retries`）。`WISH_PROMPT_VERSION = "wish-match/1"`。
   - `make_proposer(..., player_text=)`：把願望文字傳給 `propose_skill`（`<player_input>`）。
   - `WishSource{client, proposer(text), max_attempts}`；`mock_wish_client`（Mock：選單名稱出現在願望裡的關鍵字，依選單順序取前 2 個；都沒有＝回空清單）。
6. **API 層的生成函式**（`api/llm_source.py`、`api/world_pregen.py`）：`LlmProvider.wish_source(library)`（本機：同一個 client 對關鍵字、提議、命名；Mock：`mock_wish_client`＋`mock_proposer(naming=True)`）；`Generators.wish`：對關鍵字 → 有就 `use_proposer(source.proposer(text))` 裡 `make_offer(..., llm_max_calls=llm_cards)`；至少一張 LLM 卡＝`llm`，否則 `partial`（不帶三選一，引擎自己算）。`WorldPregen._run` 多一個分支；**不預測**（玩家當場打字），`supplier` 收到時排進單一佇列、等最多 10 秒（同閃現）。
7. **日誌與重播**：`supply` 照舊把最後給出的 `WishGen` 收進這一筆的 `generated`；`replay` 的 `recorded` 依（`wish`, 鍵）取，**不呼叫 LLM**。選單許願沒有 `generated`。
8. **版號**：`CHAR_FORMAT` → `trpg-char/14`（`wish_week`、`PendingOffer.refund`、`source` 多一個值；`/13` 照讀）；`WORLD_RULES_VERSION` → 28（新動作、都不拿的退款）；`WLOG_FORMAT` 不升（`generated` 多一種紀錄，同「動作 union 多一種不用加」的前例；待決 7）；`LOG_FORMAT` 不升（戰鬥紀錄沒變）。季末重置表登記 `wish_week`（每季清空）。
9. **最小顯示**：`api/world_story_view.py` 的待選三選一標題（`source == "wish"` →「許願池」）與故事行（「許願池給了技能三選一」「都不拿，退還 N 任務幣」），避免現有畫面把來源當任務 ID 顯示。其餘 API（面板、等待）在 WP-2。

### 3.2 要改的檔

`content/world/rules.yaml`、`src/trpg/content/world_rules.py`；`src/trpg/world/actions.py`、`state.py`、`wish.py`（新）、`step.py`、`quests.py`、`generated.py`、`save.py`；`src/trpg/server/season_policy.py`；`src/trpg/llm/wish.py`（新）、`llm/prompts/wish.py`（新）、`llm/candidate_source.py`；`src/trpg/api/llm_source.py`、`api/world_pregen.py`、`api/world_story_view.py`；測試 `tests/world/test_wish.py`（新）、`tests/llm/test_wish_match.py`（新）、`tests/api/test_wish_pregen.py`（新）與寫死 `trpg-char/13`、`WORLD_RULES_VERSION` 的既有測試。

### 3.3 驗收

1. 選單許願：主城、2 個關鍵字 → 扣 4 任務幣、本週 1 次、三選一三張都帶第 1 個關鍵字、`source="wish"`；同週第 3 次被拒；換週又能許；任務幣不足、不在主城、入門期、遭遇中、關鍵字不在選單或重複或超過 2 個都被拒且狀態不變。
2. 都不拿：退 2 任務幣、次數不退；選一招：照一般三選一學會（主城＝裝上或備用）。
3. 文字許願（Mock）：願望「想把敵人凍住再一錘敲碎」→ 對到 `frozen`（＋`collision` 若名稱出現）→ 三選一至少一張 `source="llm"`；日誌那一筆的 `generated` 有 `WishGen`；用 `loads_log` 讀回、`replay` 裝會報錯的供應者，角色狀態逐字相同（重播不呼叫 LLM）。
4. 願望文字只在 `<player_input>`：系統訊息不含願望；`</player_input>`、`<request>` 這類字樣被跳脫；`<request>` 區塊不含願望。
5. 退路：沒有供應者（模型關閉）、對不上、逾時 → 動作被拒、任務幣與次數不變；關鍵字合格但三選一不合格 → 組合器版、`made_by="composer"`。
6. 舊角色檔（`/13`）照讀；沒許過願的角色 JSON 只差標頭版號。
7. 依賴方向（`lint-imports`、`tests/test_architecture.py`）；所有測試用 Mock、不連網路。
8. 交件前：`ruff check`、`ruff format --check`、`mypy`、`lint-imports`、直接相關測試、一場 `trpg battle` 紀錄＋重播。
9. 本機 LLM（手動、唯讀、≤ 30 次呼叫）：量 LF-2 之後大世界大變化閃現的 pregen 延遲、許願一次的延遲，各跑幾次，寫進報告（不做平衡量測）。

### 3.4 不做

- API 請求、畫面資料、等待提示端點（WP-2）；前端（WP-3）。
- 許願的預先生成（玩家當場打字，無從預測）。
- 命名步驟參考願望文字（只有提議那一步看 `<player_input>`）。

## 4. WP-2 API 與等待

1. `api/world_schemas.py::WorldActionRequest` 加 `WishAction`；OpenAPI 與 `client/src/api/schema.d.ts` 由 PM 重產。
2. `WorldView.wish: WishView | None`（人在主城才有）：`cost`、`refund`、`left`（本週剩幾次）、`per_week`、`available`／`blocked_zh`（同 `wish_problem`）、`llm`（世界的 LLM 開關與健康檢查；關＝只顯示選單）、`menu`（ID、名稱、一句說明）、`text_max_chars`、守池人的台詞。
3. `PregenWaitRequest.kind` 加 `"wish"`、`text`、`keywords`：前端送出文字許願前先等（≤ 10 秒，從第一次等待算起），期間等待提示可取消（取消＝不送動作，不扣錢）；逾時回 `timeout`，前端改開選單。
4. `capital.yaml` 的 `wishing_pool`、`pool_keeper` 改成 `panel: wish`（說明卡換成定稿句，玩法 PM 給字）。
5. 驗收：API 測試（Mock）走一次文字許願與選單許願、都不拿退款、`WorldView.wish` 的次數與原因；`test_openapi_snapshot`。

## 5. WP-3 前端

1. 許願池面板：文字框（字數上限、送出）、「改用選單」切換（1～2 個關鍵字）、費用與「本週還能許 N 次」、不能許的原因；LLM 關閉時只有選單。
2. 送出文字前打 `pregen/wait`，顯示等待提示（沿用閃現的元件），逾時自動切到選單並說明。
3. 三選一畫面：標題「許願池」、跳過鈕寫「都不拿（退 N 任務幣）」。
4. vitest；本機 LLM 實機一次文字許願的截圖（美術驗收每項有截圖）。

## 6. 待 PM 決定（照最保守的做法先寫進規格）

1. **要不要站在池邊**：設計只寫「在主城」。先照 `change_look` 的做法只看區域；WP-2 的面板從池子與守池人打開。
2. **每次多少任務幣**：設計沒寫數字。初值 4（新手任務一條 2、主線一步 3、懸賞 3；退一半剛好 2），只改 `rules.yaml`。
3. **願望文字上限**：設計說「一句話」。初值 60 字（prompt 的玩家文字上限是 500，這裡更嚴）。
4. **選單範圍**：「任何池」照字面是全部關鍵字；先扣掉開局隱藏的（`start_hidden`，目前是中毒池還沒補齊的那一類），和開局選單一致。
5. **兩個關鍵字怎麼出題**：#88 的例子「冰凍＋重擊」。現有的指定關鍵字出題只能釘一個；先釘第 1 個、第 2 個當偏向（三張都帶第 1 個，橋接與新方向優先帶第 2 個）。要三張都帶兩個需要改候選產生器，另排。
6. **LLM 張數**：設計「LLM 提議 1～3 招」，#88「出 3 招挑 1」。完整技能提議一張就要數秒（第 3 節實測），玩家當場許願只等 10 秒，先每份最多 1 張 LLM、其餘組合器與技能池補滿（同機遇 6L-2b 的保守值）；改 `llm_cards` 即可。
7. **`WLOG_FORMAT` 不升**：日誌的 `generated` 多一種紀錄（`wish`）；照「動作 union 多一種不用加」的前例不升，新日誌在舊程式讀不了這一種紀錄（同新動作）。
8. **LLM 對不上關鍵字時**：設計「沒有 LLM 時從選單挑」；先做成「動作被拒、不扣錢、請改用選單」，不由引擎替玩家猜。
9. **許願算不算「取得地點的界域」**：選到的技能記主城（`skill_regions`），名稱與描述照 #126 用中性奇幻（提議的 `region=None`）。

## 7. 需要使用者決定

1. **任務幣價格**（第 6 節第 2 點）：數值由使用者調，初值 4 只是讓流程能跑。
2. **一次許願只請 LLM 出 1 招是否接受**（第 6 節第 6 點）：要真的 3 招都由 LLM 出，玩家得等約 3 倍時間（或改成先回組合器版、背景補 LLM 版，需改流程）。
