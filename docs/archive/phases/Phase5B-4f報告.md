# Phase 5B-4f 完成報告：5B-4e 收尾（小蓮部分成功好感度、保底專用「誰」、機遇提示一天一次）

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 1 節 5B 表「5B-4f」列；背景 `Phase5B-4e報告.md` 第 7 節待決 1、2、4（玩法 PM 2026-11-03 代決）。
> 沒動引擎、`content/skills/`、戰鬥紀錄格式、前端、OpenAPI；`trpg-char/1`、`trpg-world/1`、`trpg-wlog/1` 不升版號（新欄位有預設值，照 5A-6 起的慣例）。保底文字前端標「（模板文字）」不在這段（排 5D-4）。

## 1. 各項做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 骨架 2 部分成功小蓮 +10、拿掉失敗 −5 | 事件好感度表：`lost_acolyte` 的 `failure −5` 換成 `partial +10`（成功 +20、骨架 6 成功 +10 照舊）。只動 content | `content/world/social/cloud_ridge.yaml` |
| 2 | 保底機遇的「誰」＝「焦痕未冷的古松」 | 骨架新欄位 `guarantee_who_zh`（≤ 24 字，同說書人角色上限）與 `EventSkeletonDef.who_for(guaranteed=)`；`storm_altar` 填「焦痕未冷的古松」。保底觸發（`trigger.guaranteed`）時：專用旁白的角色（`actor_zh`）、事件卡的「誰」（`who_zh`，沒有開場敘述時的 `actor_zh`）、動作紀錄「在古松祭壇遇到一件事：…」都用它；一般觸發照舊「雷雨中的古松祭壇」 | `content/world_events.py`、`content/world/events/cloud_ridge.yaml`、`api/world_story.py`、`api/world_story_view.py` |
| 3 | 「古松那邊最近不太平」每個角色一天一次 | 角色狀態新欄位 `opportunity_hint_day: int \| None`（最後一次聽到提示的 `refresh_day`，6 點刷新為界）。`opportunity_hint` 當天聽過就回 `None`；新函式 `hear_opportunity_hint` 給事件並記下日子。抵達霧渡鎮與酒館共用同一筆（同一天先抵達聽過，酒館就不提，反之亦然）。`tavern` 改成回傳 `(char, events)`（之前不改狀態） | `world/state.py`、`world/social.py`、`world/step.py` |

## 2. 小蓮到信賴的天數

同 5B-4e 的方法（進度表照 `tests/world/test_affinity_pace.py`：骨架 2 第 2 天、骨架 6 第 3 天，小蓮第 2 天起每天聊；骨架 2 DC 11、骨架 6 DC 13、部分成功差 5 內；d20＋修正精確列舉，腳本在 scratchpad，不進 repo）：

| 修正 | 骨架 2／6 成功率 | 平均到信賴（本段） | 5B-4e | 第 5 天到 | 第 8 天前到 |
|---|---|---|---|---|---|
| +0 | 50%／40% | **9.2 天** | 10.5 天 | 20% | 60% |
| +2 | 60%／50% | **8.2 天** | 9.3 天 | 30% | 72% |
| +4 | 70%／60% | **7.3 天** | 8.2 天 | 42% | 85% |
| +6 | 80%／70% | **6.5 天** | 7.2 天 | 56% | 94% |

- 天數分布（+0）：第 5 天 20%、第 8 天 40%、第 11 天 25%、第 15 天 15%（5B-4e 是 5／8／11／13／15／16 天）。
- 兩個事件都成功仍是第 5 天（進度表不變：0、33、56、59…）；骨架 2 部分成功＋骨架 6 成功變成第 8 天（之前 11 天）。
- **平均約第 6.5～9 天**，比 5B-4e 早約 1 天，但平均仍到不了第 6 天的目標（見待決 1）。
- 原有驗收（第 4～5 天第一位、第 5 天前 1～2 名、第 3 天前沒有）照舊通過。

## 3. 新欄位與函式（全部有預設值）

- 內容：`EventSkeletonDef.guarantee_who_zh`（`None`＝照 `who_zh`）、`EventSkeletonDef.who_for`。
- 角色：`CharacterState.opportunity_hint_day`（`None`＝沒聽過）。舊存檔沒有這個欄位照讀（測試鎖住），不升 `trpg-char/1`、不需要遷移。
- 函式：`world.social.hear_opportunity_hint`；`world.social.tavern` 回傳型別改成 `(CharacterState, events)`（只有 `world/step.py` 一個呼叫端）。
- API：schema 不變（事件卡 `who_zh`／`actor_zh` 只換值）；OpenAPI 不變，沒跑 vitest。

## 4. 可重播

- 提示的「當天聽過」只看角色狀態與 `refresh_day(now)`（`now` 來自日誌），不耗亂數；酒館動作現在會改角色狀態，但照舊是確定性的世界動作，重播照日誌重算。
- 保底的「誰」是 `NarrateAction` 內容（照舊進日誌）與顯示層的取值，不影響狀態。

## 5. 測試

| 檔案 | 內容 |
|---|---|
| `tests/world/test_affinity.py`（改） | 骨架 2 部分成功 → 小蓮 +10；失敗不扣、沒有好感度事件 |
| `tests/world/test_affinity_pace.py`（加） | 事件表：骨架 2 partial +10、沒有 failure 列 |
| `tests/api/test_world_story.py`（加） | 保底：旁白角色、事件卡「誰」與角色、動作紀錄句子都是「焦痕未冷的古松」；一般觸發照舊「雷雨中的古松祭壇」；敘述進日誌後事件卡照樣 |
| `tests/world/test_opportunity_hints.py`（加） | 抵達提一次後同一天酒館、再抵達、隔天凌晨 6 點前都不提；6 點後酒館再提一次並記下新的一天；舊存檔（拿掉欄位）照讀、照提 |

## 6. 代決（最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5B4f-1 | 「一天只提一次」的範圍 | 抵達霧渡鎮與酒館共用同一筆（一天整體一次，不是各一次）；多條提示（目前只有一條）也共用 |
| 5B4f-2 | 保底「誰」用在哪裡 | 只在保底觸發的那次事件：開場旁白角色、事件卡、觸發的動作紀錄。機遇三選一的標題（`pending_offer_view`，待選紀錄沒有「是不是保底」）與「離開…的事就此作罷」那句（事件沒帶保底旗標）照舊用「雷雨中的古松祭壇」 |
| 5B4f-3 | 存檔格式 | 新欄位有預設值，不升版號、不寫遷移（同 5A-6 起的慣例） |

## 7. 待 PM 決定

1. **小蓮平均仍到不了第 6 天**：平均第 6.5～9 天（修正 +6～+0）。要平均落在第 6 天，可再加（例：骨架 6 部分成功也給 +10，或骨架 2 成功 +20 → +25）；只動 content。
2. **三選一標題與「作罷」句子**：要不要也換成保底的「誰」（要在 `PendingOffer` 或 `EventLeftEvent` 記保底旗標，動狀態或事件格式）。

## 8. 檢查

- 開發中：好感度相關 5 檔 105 passed；`tests/api/test_world_story.py`、`test_opportunity_offer_view.py`、`tests/content` 1992 passed；`test_opportunity_hints.py` 6 passed。
- 交件前 `git merge main`（設計文件 2 行；自動合併，沒有衝突）後：`ruff check .`、`ruff format --check .`、`mypy`（1095 檔）、`lint-imports`（9 kept）通過；`tests/world tests/api -n 8`：885 passed；swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- 沒有新增 `# noqa`；沒動前端，沒跑 vitest；沒跑全量與大型模擬。
