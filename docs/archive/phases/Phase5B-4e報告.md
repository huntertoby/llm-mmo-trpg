# Phase 5B-4e 完成報告：5B-4d 收尾（小蓮事件好感度、祭壇傳聞與提示、保底專用文字、渡婆婆每天再觸發）

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 1 節 5B 表「5B-4e」列；背景第 25 節、`Phase5B-4d報告.md` 第 7 節；設計 `docs/design/18-雲嶺內容.md` 18.7.6「5B-4d 代決」。
> 數值與文字全部放在 `content/`（代決，之後被改只動資料）。沒動引擎、`content/skills/`、戰鬥紀錄格式、前端；`trpg-char/1`、`trpg-world/1`、`trpg-wlog/1` 不升版號（新欄位都有預設值，新事件只出現在動作結果，不進日誌）。

## 1. 各項做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 骨架 2 成功小蓮 +20、骨架 6 成功 +10 | 事件好感度表：`lost_acolyte` success 小蓮 10 → **20**（取代，不是疊加；代決 5B4e-1）；新增 `monks_dispute` success 小蓮 +10（青崖 +10 照舊） | `content/world/social/cloud_ridge.yaml` |
| 2 | 第 4 天起酒館傳聞必有祭壇 | `SocialTable.pinned_rumors`（`{rumor, from_day}`，傳聞要在池內）；雲嶺 `rumor_storm_altar` 從第 4 天。`week_rumors` 照舊洗牌抽 3 條，賽季第 4 天起沒抽到就換掉最後抽到的非必出那條（代決 5B4e-2） | `content/world_quests.py`、`world/social.py` |
| 3 | 第 6 天起霧渡鎮說書人提示 | `SocialTable.opportunity_hints`（`{location, from_day, text_zh}`）；雲嶺：霧渡鎮、第 6 天、「酒館的說書人順口提了一句：「古松那邊最近不太平。」」。條件同保底（`met_opportunities` 與 `opportunities` 都空）。**抵達**霧渡鎮（沒遇敵）與在霧渡鎮**聽酒館傳聞**時，多一個 `OpportunityHintEvent`（不改狀態），動作紀錄顯示那一句（代決 5B4e-3） | `world/social.py`、`world/step.py`、`world/actions.py`、`api/world_story_view.py` |
| 4 | 保底專用文字、不檢查帶電 | 骨架新欄位 `guarantee_text_zh`（古松祭壇填使用者給的那句）；`event_story` 遇到 `trigger.guaranteed` 且有專用文字 → 不經說書人，用模板的角色／動機＋專用旁白（`source=fallback`）。`OpportunityRules.guarantee_waives_keyword`（雲嶺 `true`）：保底觸發的事件 `opportunity_available` 直接成立（解法檢查、事件卡、背景預測同一個函式）；三選一照舊 `pinned_keyword=charged`，三張都帶電（測試鎖住）。一般觸發照舊要帶電技能 | `content/world_events.py`、`content/world_rules.py`、`content/world/rules.yaml`、`content/world/events/cloud_ridge.yaml`、`world/situations.py`、`api/world_story.py` |
| 5 | 渡婆婆信賴時聊天每天再觸發 | `TalkEntry.retrigger_daily`（只能配 `unlocks_skeleton`；`granny_du_secret` 設 `true`）。已解鎖的骨架：當天（6 點刷新）**第一次**聊天、說得出祕密（信賴）、還沒解決、當天沒失敗過、身上沒事件、骨架地點含所在地點 → 觸發（候選只有它）。取代 5B4d-2 的「失敗後不再由聊天觸發」 | `content/world_quests.py`、`world/social.py`、`content/world/social/cloud_ridge.yaml` |

## 2. 小蓮到信賴的天數

進度表同 5B-4c／4d（`uv run python -m tests.world.test_affinity_pace`；骨架 2 第 2 天、骨架 6 第 3 天成功，小蓮第 2 天起每天聊）：

| NPC | 到信賴 | 第 1～10 天結束時 |
|---|---|---|
| 小蓮（本段，兩個事件都成功） | **第 5 天** | 0、33、56、59、62、65、68… |
| 小蓮（5B-4d） | 第 11 天 | 0、23、36、39、42、45… |
| 青崖道長 | 第 5 天（不變） | 0、13、46、59、82、100… |
| 渡婆婆 | 第 7 天（不變） | 23、46、49、52、55、58、61… |

依成功率的平均（d20＋修正對 DC 11／13、部分成功差 5 內；部分成功沒好感度、骨架 2 失敗 −5；精確列舉，腳本在 scratchpad，不進 repo）：

| 修正 | 骨架 2／6 成功率 | 平均到信賴 | 第 5 天到的機率 |
|---|---|---|---|
| +0 | 50%／40% | 10.5 天 | 20% |
| +2 | 60%／50% | 9.3 天 | 30% |
| +4 | 70%／60% | 8.2 天 | 42% |
| +6 | 80%／70% | 7.2 天 | 56% |

- 兩個都成功：第 5 天（比目標第 6 天早 1 天）；只要有一個沒成功：第 8 天以後。**平均約第 8～10 天**，到不了第 6 天的目標（見待決 1）。
- 原有驗收（第 4～5 天第一位、第 5 天前 1～2 名、第 3 天前沒有）照舊通過（青崖、小蓮都第 5 天＝2 名）。

## 3. 新欄位、事件（全部有預設值）

- 內容：`SocialTable.pinned_rumors`、`SocialTable.opportunity_hints`（`OpportunityHint`；跨檔檢查地點存在）、`TalkEntry.retrigger_daily`、`EventSkeletonDef.guarantee_text_zh`（≤ 150 字，同旁白上限）、`OpportunityRules.guarantee_waives_keyword`。
- 事件：`OpportunityHintEvent`（`opportunity_hint`；`location`、`text_zh`）。
- 函式：`world.social.opportunity_hint`。
- API／前端：沒改 schema（提示走既有的動作紀錄句子 `events`）；OpenAPI 不變，不用跑 vitest。

## 4. 可重播

- 全部是世界動作的確定性結果：必出傳聞只看賽季天數（`now` 來自日誌）、提示只看角色狀態與天數、再觸發看 `talk_days`／`failed_skeletons`；都不耗亂數。
- 保底專用文字是 `NarrateAction` 的內容，照舊進日誌、重播照紀錄。

## 5. 測試

| 檔案 | 內容 |
|---|---|
| `tests/world/test_affinity_pace.py`（改、加） | 第 2 天 +33；骨架 2 ＝ +20、骨架 6 ＝ +10；小蓮 ≤ 第 6 天 |
| `tests/world/test_event_solutions.py`、`test_quests.py`（改） | 數值跟著改（+20；主線 ③ 步驟 +10 ＋骨架 6 +10） |
| `tests/world/test_opportunity_hints.py`（新） | 40 個種子 × 21 天：第 4 天起必有祭壇、第 1～3 天照舊隨機、同週只換一條；抵達霧渡鎮第 5 天沒提示、第 6 天有；遇過／拿過不提；酒館第 6 天多一句；別的地點沒有；必出傳聞要在池內 |
| `tests/world/test_opportunity.py`（加） | 保底時沒帶電技能也能拿機遇，三張都帶電；資料關掉照 5B-4d；一般觸發照舊要帶電 |
| `tests/world/test_affinity_gain.py`（加） | 失敗當天聊天不觸發；隔天第一次聊觸發、同天第二次不觸發；放棄後隔天照樣；解決後、不是信賴不觸發 |
| `tests/api/test_world_story.py`（加） | 保底事件用專用文字、不呼叫 LLM、寫得進日誌；一般觸發不用；提示句子顯示 |

## 6. 代決（最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5B4e-1 | 「骨架 2 成功給小蓮 +20」 | 取代原本的 +10（不是另加 +20 變 +30）；骨架 6 另加一列 +10 |
| 5B4e-2 | 必出傳聞怎麼塞進本週 3 條 | 照舊洗牌，沒抽到就換掉最後抽到的那條；第 1～3 天不變，第 4 天起同一週只差那一條（同一天所有人相同） |
| 5B4e-3 | 「說書人順口提」的形式與時機 | 固定一句（內容庫），不經 LLM；抵達霧渡鎮（沒遇敵）與在霧渡鎮聽酒館傳聞時出現在動作紀錄；每次都提，不限一天一次；條件同保底（遇過或拿過機遇就不提） |
| 5B4e-4 | 保底專用文字的呈現 | 只換旁白（`text_zh`，清掉「多講一點」）；事件卡的「誰」照骨架「雷雨中的古松祭壇」；來源標成模板文字 |
| 5B4e-5 | 不檢查帶電的範圍 | 只有保底觸發的那次事件（`guaranteed`）；雷雨夜一般觸發照舊要帶電技能 |
| 5B4e-6 | 渡婆婆「每天可再觸發一次」 | 每天第一次和她聊天時；當天失敗過的不觸發、解決後不觸發；身上有別的事件時不觸發也不補 |

## 7. 待 PM 決定

1. **小蓮平均到不了第 6 天**：兩個事件都成功是第 5 天，任一個沒成功就第 8 天以後；平均第 8～10 天（第 2 節）。要穩定在第 6 天，可把部分成功也給好感度（例：骨架 2 partial +10），或把骨架 2 失敗 −5 拿掉；只動 content。
2. **事件卡的「誰」**：保底在晴天白天仍顯示「雷雨中的古松祭壇」（5B4e-4）；要不要再給一個保底用的 `who`（例：「古松祭壇」）。
3. **保底文字標成「（模板文字）」**：前端對 `source=fallback` 會加這個標註；要不要對專用文字隱藏（要加來源種類，動 API 與前端）。
4. **提示的頻率**：目前每次抵達霧渡鎮與每次聽傳聞都提（5B4e-3）；要不要一天一次（要記在角色狀態）。

## 8. 檢查

- 開發中：`tests/world tests/content -n 8`：2423 passed；`tests/api/test_world_story.py`：11 passed。
- 交件前 `git merge main`（5D-1 經濟、藥水價格；自動合併，沒有衝突）後：`ruff check .`、`ruff format --check .`、`mypy`（1095 檔）、`lint-imports`（9 kept）通過；`tests/world tests/api -n 8`：882 passed；swamp 種子 7 重播：88 個動作、313 個事件，最終狀態一致。
- 沒有新增 `# noqa`；沒動前端，沒跑 vitest；沒跑全量與大型模擬。
