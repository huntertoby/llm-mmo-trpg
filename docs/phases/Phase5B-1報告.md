# Phase 5B-1 完成報告：事件骨架與線頭的資料層

> 實作者：implementer agent（2026-11-02）。規格：`docs/phases/Phase5計畫.md` 第 8 節（先寫入規格、commit 後再實作）。
> 只動 `content/world/events/`、`content/world/npcs/`、`content/world/event_rules.yaml`（新）、`src/trpg/content/world_events.py`（新）、`src/trpg/content/library.py`（一個欄位＋一行呼叫）、`src/trpg/world/`（新增 `events.py`、`threads.py`；`state.py`、`actions.py`、`rng.py`、`step.py`、`__init__.py` 小改）、`tests/content/test_world_events.py`、`tests/world/test_events.py`、`tests/world/test_threads.py`（新）、`tests/world/test_travel.py`（2 行）、`docs/phases/Phase5計畫.md`（第 8 節）。沒有動 `content/skills/`、`src/trpg/skillgen/`、引擎、roguelite、API、前端、5A-3 的敵人與遭遇表。

## 1. 交付

| # | 項目 | 檔案 |
|---|---|---|
| 1 | 5B-1 詳細規格（計畫第 8 節；和 5A-3 合併後「之後各段規格」改為第 9 節） | `docs/phases/Phase5計畫.md` |
| 2 | 事件骨架、線頭、NPC 人設卡、事件規則的 schema、跨檔案檢查與載入 | `src/trpg/content/world_events.py`、`library.py` |
| 3 | 雲嶺 18 個骨架（17 種線頭）、8 張 NPC 人設卡、事件規則初值 | `content/world/events/cloud_ridge.yaml`、`content/world/npcs/cloud_ridge.yaml`、`content/world/event_rules.yaml` |
| 4 | 移動時的事件擲骰（依步數＋種子）、`EventTrigger`、線頭狀態與純函式 | `src/trpg/world/events.py`、`threads.py`、`state.py`、`actions.py`、`rng.py`、`step.py` |
| 5 | 測試（新 72 個：content 43、world 事件 18、線頭 11） | `tests/content/test_world_events.py`、`tests/world/test_events.py`、`tests/world/test_threads.py` |
| 6 | 本報告 | `docs/phases/Phase5B-1報告.md` |

`uv run trpg content check` 新增三行：「`world/npcs/cloud_ridge.yaml`：cloud_ridge：8 張 NPC 人設卡」「`world/events/cloud_ridge.yaml`：cloud_ridge：18 個事件骨架、17 種線頭」「`world/event_rules.yaml`：事件每步 +150‰、上限 600‰；線頭上限 5（世界 5）、72 小時到期」。

## 2. Schema 摘要（`src/trpg/content/world_events.py`）

- `SolutionDef`：`kind`（`combat`、`situation`、`parley`、`abandon`、`opportunity`）、`attributes`（只有 `situation` 可填且必填 1～3 個、不重複；用 `Attribute` 列舉）、`note_zh`。
- `ThreadDef`：`id`、`text_zh`、`scope`（`personal`／`world`，預設 `personal`）、`npc`、`hints_location`（必須是 `reveal` 含 `quest_clue` 的隱藏地點）、`on_expire_zh`。
- `EventSkeletonDef`：`id`、`number`（18.4 編號）、`who_zh`／`want_zh`／`obstacle_zh`／`stakes_zh`、`locations`（≥ 1）、`day_phase`、`weather`、`npcs`、`solutions`（≥ 1）、`threads`、`follows`（能接的線頭；`follows` 不可接自己的線頭）。
- `EventSkeletonTable`（一區一檔、檔名＝`region`）：骨架 ID、編號、線頭 ID 不重複；`summary()`。
- `NpcCardDef`：`id`、`name_zh`、`role_zh`、`location`、`personality_zh`、`speech_zh`、`secret_zh`（只給說書人）、`hooks_zh`；`NpcCardTable`（一區一檔）。
- `EventRules`：`frequency`（`per_step_permille`、`max_permille`）、`threads`（`personal_limit`、`world_limit`、`expire_seconds`）。
- 跨檔案：`world_event_problems`（地點、天氣、NPC、線頭的 NPC 與 `hints_location`、`follows` 的線頭存在）、`npc_card_problems`（所在地點）；載入時骨架 ID＋線頭 ID、NPC ID **跨區也不可重複**。
- 載入：`ContentLibrary.world_event_content: WorldEventContent(events, npcs, rules)`；資料夾或檔案不存在＝空／`None`（舊測試的精簡 content 照常載入）。為了減少和 5A-3 的 `library.py` 衝突，載入函式 `load_world_event_content` 放在 `world_events.py`，`library.py` 只加一個欄位與一行呼叫（規格 8.2 已同步改寫）。

## 3. 出現頻率規則（`trpg.world.events.roll_event`，`world_step` 的移動用）

在遇敵擲骰之後、感知判定之前（`event_rules` 為 `None` 或該區沒有骨架檔時整段跳過、不耗亂數）：

1. 身上有 `pending_event` 時先清掉，發 `event_left`。
2. `steps = event_steps + 1`；機率 ‰ ＝ `min(600, 150 × steps)`（第 1 步 15%、第 4 步起 60%）。
3. `event` 串流（`fnv1a64("{season_seed}:{character_id}:event:{counter}")`）**一律** 擲 `randint(0, 999)`，亂數消耗固定。
4. 候選骨架＝本區骨架中地點、時段、天氣（`weather_at`，同區同半天所有人相同）都符合者，依 ID 排序。
5. 觸發＝`roll < 機率` 且這一步 **沒有遇敵** 且候選非空；觸發時優先挑 `follows` 接得上有效線頭（個人＋世界、`expires_at > now`）的骨架，用同一個 `Rng` 的 `choice`；寫入 `pending_event`（`EventTrigger`：骨架、候選、被接上的線頭、天氣、日夜、時間）、`event_steps` 歸零，發 `event_check`、`event_triggered`。沒觸發則 `event_steps = steps`。
6. 事件不擋移動與紮營；不呼叫 LLM、不產生線頭、不做任何結算。

**線頭**（`trpg.world.threads`，純函式；本段沒有任何動作會呼叫）：`active_threads`／`expired_threads`（`expires_at > now` 為有效）、`add_thread(threads, thread_id, skeleton, region, now, *, limit, expire_seconds) → (threads, pushed_out)`：同 ID 有效則不變、滿了擠掉最舊（`created_at`、ID 排序）、已到期未處理的保留但不佔上限。個人線頭存 `CharacterState.threads`、世界級存 `WorldState.threads`。

**狀態**：`CharacterState` 加 `event_steps`、`pending_event`、`threads`；`WorldState` 加 `threads`。新欄位都有預設值，舊存檔照讀（有測試），格式版本不變。

## 4. 確定性

- 只用 `trpg.world.rng.draw`（新串流 `STREAM_EVENT = "event"`）；候選、線頭一律排序；沒有 `hash()`、時間、`random`、`uuid4`（`tests/test_architecture.py` 掃描通過）。
- 5A-2 的重播測試（60 步雙角色、hypothesis 25 例）現在包含事件擲骰，快照逐字相同；`test_events.py` 另測同輸入同結果、不同賽季種子挑到不同骨架。
- 既有 `test_travel.py` 兩個斷言 `rng_counters` 的地方補上 `event` 串流（其餘既有測試不變）。

## 5. 用了 18 號文件的哪些內容

- **18.4 全部 18 個事件骨架**：誰／想要／阻礙／賭注照抄（#4 的 obstacle、#12、#15 的「（異象）」「（遺跡）」照原文；#16 阻礙「—」存空字串）；解法照括號拆成 `kind`＋`attributes`＋`note_zh`；線頭照「線頭」欄（#16「隨機傳聞（機遇或隱藏地點）」照原文存成一條 `tavern_rumor`）；表下兩個到期結局寫進 `scarface_grudge`、`temple_traitor`。
- **18.5 全部 8 張 NPC 人設卡**：個性、說話方式、祕密、關係照抄。
- 18.3：骨架地點的推定依據（「內容」欄的事件、敵人）、`foxfire_guide` → 鶴歸崖（`quest_clue`）。

ID 對照（開發 PM 取）見計畫 8.3、8.4。

## 6. 代決（照計畫 8.10，都是最保守做法）

1. **5B1-1** 骨架的出現地點、時段、天氣（18.4 沒寫）：照計畫 8.3 推定；改了只動 content。值得使用者確認的：燈籠隊（#17）只在夜晚、可出現在霧渡鎮；說書人（#16）出現在霧渡鎮（城鎮也會擲事件）；雷雨（#12）＝`rain`＋`night`。
2. **5B1-2** 頻率：依距離上次事件的步數線性加，150‰／步、上限 600‰；遇敵那一步不出事件（但照擲）。
3. **5B1-3** 引擎挑預設骨架＋列出候選，LLM（5B-3）只能在候選內換。
4. **5B1-4** 事件不擋移動；離開地點＝作罷（`event_left`）。
5. **5B1-5** 線頭全部 `personal`；世界級上限也 5；到期 3 天（現實 259200 秒）；滿了擠掉最舊。
6. **5B1-6** 解法種類加 `opportunity`（#12 機遇），條件（帶「帶電」技能）先寫在 `note_zh` 文字。
7. **5B1-7** 情境判定解法的屬性照 18.4 填 1～2 個。
8. **5B1-8** 新欄位有預設值、存檔格式版本不升。
9. **（實作補）** 小蓮（18.5「青霧觀」）放在 `mist_temple_gate`；霜音放在隱藏地點 `crane_cliff`。
10. **（實作補）** `ContentLibrary` 只加一個 `world_event_content` 欄位（不是三個），減少合併衝突。

## 7. 待 PM 決定

- **事件要不要擋移動**（5B1-4）：目前不擋、離開就作罷。若 5B-2 要「事件必須先處理（含選放棄）才能走」，改成和 `pending_encounter` 一樣擋，並在 5B-2 加處理動作。
- **9.6.4「模板允許 2～3 種屬性」vs 18.4 的單一屬性解法**：多數骨架的情境判定解法只列 1 個屬性（例：#3 意志威嚇）。5B-2 需要決定情境模板是「每個解法一個模板」還是「同骨架所有情境解法合成一個模板」，以及單屬性解法要不要補屬性（給玩法 PM）。
- **世界級線頭**：18.4 沒標哪些是世界級（9.6.7 #6 例：放走的頭目、鬆動的封印）。候選：「霧魅從裂痕湧出」「碎片被送往灰燼荒原」；目前全部個人。
- **`follows`（接線頭的骨架）**：18.4 沒寫哪個骨架接哪條線頭，雲嶺資料目前全空，「優先接線頭」的機制做好了但沒有資料會觸發（給玩法 PM 補）。
- **機遇條件**（#12「帶『帶電』技能」）與「斷崖幫寨的暗門（隱藏入口）」：前者要資料化成技能關鍵字條件、後者在地點圖上沒有對應的隱藏地點，留給 5B-4。
- **頻率數值**：150‰／步、上限 600‰ 是初值，之後用模擬定；趕路目前不影響事件機率。
- **每個非城鎮地點的骨架覆蓋**：獵戶小屋白天、丹爐洞、鶴歸崖、雲頂觀、往灰燼荒原的渡口沒有骨架（擲了也不會出事件）。

## 8. 檢查紀錄

交件前已 `git merge main`（含 5A-3）：`library.py`、`trpg/world/__init__.py`、計畫文件的衝突都保留兩邊（計畫第 7 節 5A-3、第 8 節 5B-1、第 9 節之後各段）。

- `uv run pytest -q tests/world tests/content/test_world_events.py tests/content/test_world_map.py tests/content/test_world_enemies.py tests/content/test_loader.py tests/test_architecture.py -n 8 --timeout=1800`：**263 passed**。
- `uv run pytest -q tests/cli -m "slow or not slow" -n 8 --timeout=3000`：**180 passed**（快照沒變，不需重產）。
- `ruff check .`：通過；`ruff format --check .`：全部已格式化；`mypy`（strict，985 檔）：Success；`lint-imports`：9 個契約全部 KEPT。
- `uv run trpg content check`：通過，列出三個新檔摘要。
- 沒動戰鬥，不需戰鬥重播；沒跑全量 `scripts/check.py`。
