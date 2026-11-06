# Phase 5B-4d 完成報告：5B-4c 收尾（小蓮好感度、骨架 22 失敗可再試、機遇保底、skillgen 指定關鍵字）

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 25 節（先寫規格、commit `25f021c9` 後實作；原「之後各段規格」改第 26 節）。
> 柳掌櫃的店內消費（5D）、阿岳的打贏加成（5C-3）不在本段。

## 1. 各項做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 小蓮：主線第 ②、③ 步各 +10 | 主線「霧中裂痕」第 ② 步 `enter_temple` 的 `npcs` 加 `acolyte_xiaolian`（第 ③ 步 `temple_split` 原本就有）→ 完成 ②、③ 各 +10（照 `quest_step_delta`，代決 5B4d-1）。重量見第 2 節 | `content/world/quests/cloud_ridge.yaml`、`tests/world/test_affinity_pace.py` |
| 2 | 骨架 22 只有成功／部分成功才算解決 | `mark_finished(..., now=)`：`once` 骨架結果 `success`／`partial` → `finished_skeletons`（並清掉失敗紀錄）；`failure` → `CharacterState.failed_skeletons[骨架] = refresh_day(now)`；`abandoned` 照舊不記。`event_candidates(..., failed=)`：失敗當天（`refresh_day(now) <= 失敗那天`）不進候選，隔天台北 6 點刷新後回到移動擲骰的候選。聊天只在第一次解鎖時立刻觸發，失敗後不再由聊天觸發（代決 5B4d-2） | `world/events.py`、`world/step.py`、`world/state.py` |
| 3 | 第 7 天前保底 1 次機遇 | `OpportunityRules.guarantee_from_day`（預設 0＝不保底；雲嶺 `rules.yaml` 設 6）。`CharacterState.met_opportunities`：觸發過的機遇骨架（`world_step` 動作後看 `event_triggered`，移動擲骰、聊天解鎖都算）。移動抵達的 `roll_event`：賽季第 6 天起、`met_opportunities` 與 `opportunities` 都空、這一步沒遇敵 → 所在地點的機遇骨架 **不看天氣、時段與機率** 直接觸發（候選只有它、`EventTrigger.guaranteed = true`；多個時取 ID 最小）。擲骰照舊消耗（亂數計數不變）。機遇解法的 `requires_keyword` 不放寬。雲嶺＝古松祭壇（骨架 12） | `world/events.py`（`guaranteed_opportunity`、`season_day`、`is_opportunity`、`mark_met_opportunities`）、`content/world_rules.py`、`content/world/rules.yaml` |
| 4 | skillgen「指定關鍵字」模式 | `CandidateRequest.pinned_keyword`（預設 `None`＝原行為）；完整版產生器指定模式：加深＝只帶它；橋接＝它＋另一個持有的關鍵字；新方向＝它＋一個還沒有的關鍵字（行為權重、區域偏向排序）；多關鍵字找不到退回只帶它（`fallback`）；不從通用池抽；未知關鍵字 `ValueError`。橋接與新方向的多關鍵字選項 **各自** 受 `BRIDGE_VARIANT_CAP`（400）管（新增 `_Search.pinned_new_used`；一般模式只有橋接受管，結果逐字不變）；組合器照舊 `skip_legendary=True`。`make_offer`／`offer_key` 加 keyword-only `pinned_keyword`（快取鍵取自 `CandidateRequest` 全欄位，自動含它）。機遇（`solutions._opportunity`）與背景預測（`api.offer_prefetch` 的 `OfferJob.pinned_keyword`）都傳 `pinned_keyword=requires_keyword`；一般三選一不傳 | `skillgen/candidates.py`、`roguelite/offers.py`、`world/solutions.py`、`api/offer_prefetch.py` |

## 2. 小蓮的重量（`uv run python -m tests.world.test_affinity_pace`）

進度表照 5B-4c（代決 5B4c-1）：主線 ① ② 第 2 天、③ ④ 第 3 天；迷路的道童第 2 天；小蓮從第 2 天起每天聊一次。

| NPC | 到信賴 | 第 1～10 天結束時 |
|---|---|---|
| 小蓮（本段） | **第 11 天**（10 天內沒到） | 0、23、36、39、42、45、48、51、54、57 |
| 小蓮（5B-4c） | 10 天內沒到 | 0、13、26、29、32、35、38、41、44、47 |
| 青崖道長 | 第 5 天 | 0、13、46、59、82、100… |
| 渡婆婆 | 第 7 天 | 23、46、49、52、55、58、61… |

- 結論：+10 只加在第 ② 步，小蓮第 3 天 36 之後只剩每天聊天 +3，**到不了第 4～6 天的目標**（見待決 1）。
- 若把 ②、③ 解讀成「在通用 +10 之外再各加 +10」（③ 變 +20）：0、23、46、49、52、55、58、61 → 第 8 天，仍到不了。
- 原有驗收（第 5 天前 1～2 名、第 3 天前沒有）照舊通過；新測試鎖住小蓮在 ②、③ 各 +10。

## 3. 機遇（指定「帶電」）三選一的組成

量測（`.scratch_5b4d/measure.py`，雲嶺新角色把第一招換成「連鎖閃電」，`build_support`、`build_charger` 各 4 個角色，同一份 `make_offer("complete")`，指定 vs 不指定；機器上沒有其他測試在跑）：

| | 加深 | 橋接 | 新方向 | 時間（秒） |
|---|---|---|---|---|
| 指定「帶電」 | 8／8 帶電 | 8／8 **退回只帶電**（找不到「帶電＋另一個持有的」） | 5／8 帶電＋新關鍵字（潮濕、印記），3／8 退回只帶電 | 3.0～8.8（平均約 5.2） |
| 不指定（原本） | 8／8 帶電（剛好是持有最多的之一） | 2／8 真的橋接 | 8／8 新關鍵字（不帶電） | 1.2～6.7（平均約 3.7） |

- 三張都帶「帶電」（測試鎖住）；但「指定＋另一個持有的關鍵字」幾乎組不出來（400 個變體內都沒有），所以實際上多半是「1 張加深＋1 張只帶電的退回＋1 張往外橋接」。
- 指定模式較慢：新方向也多了一段多關鍵字搜尋（另一份 400 變體上限）。PERF-3 的背景預先計算照樣命中（測試鎖住快取鍵一致），玩家按下機遇時通常已算好。見待決 6、7。

## 4. 新欄位、事件與函式（全部有預設值；`trpg-char/1`、`trpg-world/1`、`trpg-wlog/1` 不升版號）

- 內容：`OpportunityRules.guarantee_from_day`（雲嶺 6）；主線第 ② 步 `npcs`。
- 狀態：角色 `failed_skeletons`（骨架 → 失敗那天）、`met_opportunities`；`EventTrigger.guaranteed`。
- 函式：`CandidateRequest.pinned_keyword`；`make_offer`／`offer_key` 的 `pinned_keyword`；`OfferJob.pinned_keyword`；`world.events.mark_finished(..., now=)`（改成必填）、`mark_met_opportunities`、`guaranteed_opportunity`、`season_day`、`is_opportunity`；`event_candidates(..., failed=)`。
- API／前端沒改（`world_schemas.py` 沒動、OpenAPI 不變）。事件卡照舊顯示（保底的事件和一般事件一樣；`guaranteed` 在角色狀態裡）。

## 5. 可重播與原型不變

- 全部是世界動作：失敗紀錄用 `refresh_day(now)`（`now` 來自日誌）；保底只看賽季天數、角色狀態與地點，不多耗亂數（擲骰照舊，測試比對亂數計數相同）；指定模式的亂數只來自 `Rng(seed).fork(<種類>)`。
- `tests/world/test_quest_replay.py::test_5b4d_log_replays_identically`：骨架 22 失敗 → 走到古松祭壇（第 6 天保底，白天也出現）→ 機遇三選一（三張帶「帶電」）→ 選技能，重播兩次逐字相同。
- 原型 roguelite、一般三選一：`pinned_keyword` 預設 `None`，產生器走原路徑；`tests/skillgen/fixtures/refactor_3wr2.json` **沒有變**（`test_refactor_3wr2.py -m "slow or not slow"` 通過，不用重產）。

## 6. 代決（規格 25.10；最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5B4d-1 | 小蓮「主線第 ②、③ 步各 +10」 | 當成通用的任務步驟好感度：② 的 `npcs` 加小蓮，③ 原本就有；不另加第二份 +10 |
| 5B4d-2 | 骨架 22 失敗後怎麼再試 | 失敗當天不進候選，隔天 6 點刷新後回到移動擲骰的候選；聊天不再立刻觸發 |
| 5B4d-3 | 保底的觸發點 | 賽季第 6 天起、沒遇過機遇的角色，走到有機遇骨架的地點（雲嶺＝古松祭壇）就直接觸發，不看天氣、時段、機率；遇敵那步照舊不出事件；不在別的地點硬生機遇 |
| 5B4d-4 | 「觸發過機遇」與過了第 7 天 | 機遇骨架的事件出現過就算（拿不拿都算）；第 7 天後還沒遇過的照樣保底到遇過一次為止 |
| 5B4d-5 | 保底時的條件 | 機遇解法的 `requires_keyword` 不放寬：沒有帶電技能的角色遇到保底事件只能選其他解法 |
| 5B4d-6 | 指定關鍵字的範圍 | 只有完整版產生器（機遇用）；白板版忽略；一般三選一不傳 |
| 5B4d-7 | 指定模式的搜尋上限 | 橋接、新方向的多關鍵字選項各自 400 個變體；找不到退回只帶指定關鍵字 |
| 5B4d-8 | 07 7.6 的「0／1／2」 | 指定模式照「加深／橋接／新方向」各一張（三張都帶指定關鍵字），不另做 0／1／2 |

## 7. 待 PM 決定

1. **小蓮到不了第 4～6 天信賴**（第 2 節）：本段做法第 11 天、加倍解讀第 8 天。要達標需要再加來源（例：迷路的道童成功 +10 → +20、山門事件給小蓮好感度、或主線 ④ 也列小蓮）；只改 content。
2. **保底只能在機遇地點觸發**：沒走到古松祭壇的角色第 7 天前仍拿不到；也沒有提示玩家去那裡（酒館傳聞、事件卡說明是 5B-5 之後）。若要「一定拿到」，需要不綁地點的保底（例：第 7 天紮營時給一次、關鍵字取當下天氣），這要新設計。
3. **保底的事件文字**：古松祭壇的骨架寫「雷雨中」，保底在晴天白天也會出現；說書人拿到的天氣是實際天氣。是否要另一段保底專用的敘述。
4. **沒有帶電技能的角色**遇到保底事件拿不到機遇技能（5B4d-5），保底算用掉了（`met_opportunities`）。是否改成「拿到機遇技能才算」或保底時放寬條件。
5. **骨架 22 失敗後的再試入口** 只有霧渡鎮的移動擲骰（和酒館說書人同一個候選池）；是否要讓隔天和渡婆婆聊天就直接再觸發。
6. **指定模式的橋接幾乎都退回**（第 3 節）：「帶電＋另一個持有的關鍵字」在組合器 400 個變體內組不出來，8／8 退回只帶電。要真的橋接，可改成組合器以「另一個關鍵字」為主再檢查帶電、兩種順序都試，或提高上限（都會更慢）；要不要另排。
7. **指定模式較慢**：同步計算最長約 9 秒（一般完整三選一最長約 3～7 秒）；有背景預先計算時不影響玩家。是否要給指定模式另設較小的上限。

## 8. 檢查

- 開發中：`uv run pytest -q tests/skillgen tests/roguelite tests/world tests/api -n 8 --timeout=1800`：4784 passed、14 skipped。
- `tests/skillgen/test_refactor_3wr2.py tests/cli -m "slow or not slow" -n 8 --timeout=3000`：1057 passed（CLI 快照、行為快照都不用重產）。
- 交件前 `git merge main`（5C-3 `8af2a55a`、`ea063447`）：計畫文件衝突（兩邊都新增第 24 節）→ 5C-3 留第 24 節、本段改第 25 節、之後各段第 26 節；`state.py`、`step.py` 自動合併。合併後 `tests/world tests/api tests/cli tests/test_architecture.py` 與本段新測試（`-m "slow or not slow"`、`--timeout=3000`）：1044 passed；好感度重量不變。
- `ruff check .`、`ruff format --check .`、`mypy`（1084 檔）、`lint-imports`（9 kept）通過。沒有新增 `# noqa`；沒動引擎，不需戰鬥重播；沒跑全量 `scripts/check.py`。
