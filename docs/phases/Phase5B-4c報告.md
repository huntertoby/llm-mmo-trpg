# Phase 5B-4c 完成報告：5B-4b 收尾

> 實作者：implementer agent（2026-11-03）。規格：`docs/phases/Phase5計畫.md` 第 21 節（先寫規格、commit `15fca3cd` 後實作；原「之後各段規格」改第 22 節）。
> 追加一項（玩法 PM 定，5B-M3 待決 5BM3-8）：冬湖石背熊、崖上石背熊、雷羽鷹巢改三方。已照做（第 1 節第 7 列）。

## 1. 各項做了什麼

| # | 項目 | 做法 | 主要檔案 |
|---|---|---|---|
| 1 | 任務步驟好感度 +15 → +10 | `affinity.yaml` `quest_step_delta: 10`；每天聊天 +3、主線第 ① 步的 `npcs`（渡婆婆）保留。新增重量測試 `test_affinity_pace.py`（結果見第 2 節） | `content/world/affinity.yaml`、`tests/world/test_affinity_pace.py` |
| 2 | 懸賞精英帶資料指定詞綴 | `EnemyCatalog.affix_problem(..., allow_elite=True)`：遭遇表 **資料指定** 的精英（巢穴 `elite`、遭遇變化 `elite`）可以套在本身已是精英的範本上；營地隨機混精英照舊不套精英。已是精英的範本套詞綴時 HP 不再乘（代決 5B4c-3）。疤面＝`scarface_risen` 變化 `elite: {bandit_captain, heart_linked}`（連心的盜賊隊長＋盜賊＋霧狼 ×2）；北坡狼王＝霧狼＋狂暴的（原本就是）；叛徒戰的青霧執事照 19.7 原文套霧隱的；霧中劍客的陣容在 5F-1（待辦） | `content/world_enemies.py`、`content/world_encounters.py`、`content/world/encounters/cloud_ridge.yaml` |
| 3 | 機遇解法結算 | `event_solve` 選 `opportunity`：條件（裝備技能帶 `requires_keyword`）不成立或這個機遇拿過（`CharacterState.opportunities`）→ 拒絕；否則給 **完整技能三選一**（`pending_offers`、`PendingOffer.source = "opportunity"`、`quest`＝骨架 ID），`event_solved`（`solution_kind: opportunity`、`tier_bonus`）→ `skill_offered`（`source`）→ `event_resolved`（`success`）。高一階：`Rng(fnv1a64("{技能種子}:opportunity:{骨架}"))` 擲 `< 150‰`、本角色次數 `< 1`（`opportunity_tier_ups`）、階級 +1 ≤ 5 → `make_offer(..., tier_bonus=1)`（新 keyword-only 參數，預設 0＝原行為）。數值在 `rules.yaml` 的 `opportunity`。首例古松祭壇（骨架 12，雷雨夜＋帶電）。前端：合併 5B-5b 後把事件卡的機遇打開（`_opportunity_problem`：條件不成立「要裝備帶「帶電」的技能」、拿過「這個機遇已經拿過了」；`story.ts` 的 `solutionClick` 對機遇送 `event_solve`、提示語），三選一沿用既有的待選三選一面板（`pending_offer_view` 的名稱改成骨架的「誰」＋「機遇」） | `world/solutions.py`、`world/quests.py`（`store_offer`）、`world/state.py`、`world/actions.py`、`roguelite/offers.py`、`content/world_rules.py`、`api/world_story_view.py`、`client/src/world/story.ts` |
| 4 | 戰鬥解法的勝利條件 | `SolutionDef.objective`（只有 combat）：骨架 2、14＝`escape`，7、8＝`defend`（8 先用守點，代決 5B4c-7）。戰鬥解法的遭遇記 `EncounterResult.objective`；挑地圖時優先挑支援該條件的（地點 `battle_maps` 或區域地圖池），開戰時 `battle_objective` 設 `BattleSetup.objective`；地圖沒資料 → 全滅（劍冢 `ruined_fort` 沒有撤離資料，代決 5B4c-8） | `content/world_events.py`、`world/solutions.py`、`world/battle.py`、`content/world/events/cloud_ridge.yaml` |
| 5 | 骨架 22 每角色解決一次後不再出現 | `EventSkeletonDef.once`；`CharacterState.finished_skeletons`；`world_step` 在動作後看 `event_resolved`（結果不是 `abandoned`；成功、部分成功、失敗都算，代決 5B4c-9）記下；`event_candidates` 多 `finished` 參數，擲骰前濾掉。聊天本來就只解鎖一次，所以也不會再觸發。`granny_past` `once: true` | `world/events.py`、`world/step.py`、`content/world_events.py` |
| 6 | 世界級線頭到期結局 | `ThreadDef.on_expire_seconds`（只限世界級、要有旗標）；`WorldState.timed_flags`（`TimedFlag`：`flag`、`until`，從線頭 `expires_at` 起算、全服一致；同旗標取較晚）；`thread_expired.until`。遭遇表 `surges`（`flag`、`unit`、`kinds`、`day_phase`）：遇敵時把有效世界旗標記進 `EncounterResult.world_flags`，一般抽陣容（混精英之後）符合時敵方最後 +1 名（滿 4 名不加、遭遇變化不加，代決 5B4c-10）。雲嶺：「霧魅從裂痕湧出」→ `wraiths_surge` 2 天、夜晚營地 +1 霧魅；「碎片被送往灰燼荒原」→ 永久世界旗標 `ashen_heart_hardened`（效果待荒原與灰燼之心，待辦） | `world/endings.py`、`world/encounters.py`、`world/solutions.py`（`make_encounter`）、`content/world_encounters.py`、`content/world/events/`、`encounters/` |
| 7 | 野獸改三方（追加，玩法 PM 定） | `lake_bears` 敵方 冰鶴使 ×2、第三方 石背熊＋霧狼；`crane_nest` 敵方 雲鶴使 ×2、第三方 雷羽鷹 ×3；`crane_cliff_bear` 敵方 雷羽鷹 ×2、第三方 石背熊（沒有修士，代決 5B4c-11）；冬湖獵手不變。陣容 schema 要求敵方至少 2 名，所以前兩者各補 1 名同地點已有的修士；強度之後再量；第三方掉落屬 5D-2 | `content/world/encounters/cloud_ridge.yaml` |

## 2. 好感度重量結果（`tests/world/test_affinity_pace.py`）

進度表（代決 5B4c-1，照 18.7）：新手鏈第 1、1、2 天；主線 ① ② 第 2 天、③ ④ 第 3 天；區域鏈第 3、4、5 天；導師鏈第 5、6、6 天；事件成功：道童第 2 天、兩名修士與阿岳第 3 天、狐族第 5 天；聊天從見面那天起每天一次（霧渡鎮第 1 天、山門第 2 天、獵戶小屋第 3 天）。隱藏任務與 Boss 不算。`python -m tests.world.test_affinity_pace` 可重印。

| NPC | +10（本段）到信賴 | 第 1～7 天結束時 | +15（5B-4b）到信賴 |
|---|---|---|---|
| 青崖道長 | **第 5 天** | 0、13、46、59、82、100、100 | 第 3 天 |
| 渡婆婆 | 第 7 天 | 23、46、49、52、55、58、61 | 第 2 天 |
| 小蓮 | 第 10 天內沒到 | 0、13、26、29、32、35、38 | — |
| 阿岳 | 第 10 天內沒到 | 0、0、23、26、29、32、35 | — |
| 柳掌櫃 | 第 10 天內沒到 | 3、6、9、12、15、18、21 | — |
| 霜音 | 第 10 天內沒到 | 0、0、0、0、10、10、10 | — |

結論：+10 時第 5 天 1 名（青崖）到信賴、第 7 天第 2 名（渡婆婆），符合「第 4～5 天 1～2 名」；測試鎖住「第一位在第 4～5 天、第 5 天前 1～2 名、第 3 天前沒有」。

## 3. 資料格式摘要（新欄位全有預設；`trpg-char/1`、`trpg-world/1`、`trpg-wlog/1` 不升版號）

- 內容：`SolutionDef.objective`；`EventSkeletonDef.once`；`ThreadDef.on_expire_seconds`；`EncounterTable.surges`（`EncounterSurge`）；`WorldRules.opportunity`（`tier_up_permille: 150`、`tier_up_per_season: 1`）；`affinity.yaml` `quest_step_delta: 10`。
- 狀態：角色 `opportunities`、`opportunity_tier_ups`、`finished_skeletons`；世界 `timed_flags`（`active_flags(now)`）；`EncounterResult.objective`、`world_flags`；`PendingOffer.source`。
- 事件：`event_solved.solution_kind` 多 `opportunity`、`tier_bonus`；`skill_offered.source`、`skill_offer_taken.source`；`thread_expired.until`。
- 函式：`make_offer(..., tier_bonus=0)`（roguelite 呼叫端不變）；`EnemyCatalog.affix_problem(..., allow_elite=False)`；`world.quests.store_offer`；`world.solutions.opportunity_tier_bonus`；`world.battle.battle_objective`；`world.events.mark_finished`。

## 4. API 與前端（沒動 `world_schemas.py`；OpenAPI 不變）

- 機遇＝世界動作 `{"kind": "event_solve", "solution": <索引>}`（5B-5b 已把 `event_solve` 接上 API）。條件不成立（`opportunity_available`）或已拿過（`char.opportunities`）時拒絕；事件卡用同樣的檢查停用並顯示原因（`world_story_view._opportunity_problem`）。`tests/api/test_world_events_api.py` 一處註解與期望改成新的停用原因。
- 成功後角色有 `pending_offers`（`source: opportunity`），沿用既有的 `pending_offer` 面板與 `offer_pick`；面板標題是骨架的「誰」（例：「雷雨中的古松祭壇」）、步驟「機遇」；事件句子「機遇給了技能三選一…」。
- 前端只改 `client/src/world/story.ts`（機遇送 `event_solve`、提示語）與 `story.test.ts`；沒做瀏覽器實測。
- 戰鬥解法的勝利條件在 `prepare_battle` 的 `setup.objective`；既有的戰鬥畫面照 `effective_objective` 顯示。

## 5. 可重播與原型不變

- 全部是世界動作，由「日誌＋內容庫＋賽季種子」決定：機遇的高一階用技能種子衍生的固定種子（不動角色亂數計數）；限時旗標從線頭到期時間起算；遭遇加人不耗亂數、地圖篩選不改亂數消耗次數。`tests/world/test_quest_replay.py::test_5b4c_log_replays_identically`：世界級到期 → 機遇 → 選技能 → 移動遇敵（記下 `wraiths_surge`）→ 戰鬥，重播兩次逐字相同（角色、世界、事件）。
- 原型 roguelite：`make_offer` 的 `tier_bonus` 預設 0；`affix_problem` 的 `allow_elite` 預設 False；roguelite 呼叫端沒改。

## 6. 代決（照規格 21.13；最保守預設）

| # | 事項 | 代決 |
|---|---|---|
| 5B4c-1 | 好感度重量的「認真玩」 | 照第 2 節的進度表；只算任務步驟、每天聊天、事件好感度 |
| 5B4c-2 | 資料指定詞綴的範圍 | 只有遭遇表的固定精英（巢穴、變化）；營地混精英照舊不套精英 |
| 5B4c-3 | 精英再套詞綴的 HP | 不再乘 `hp_permille`（避免 ×1.5 兩次）；精英首殺的種類照範本 ID |
| 5B4c-4 | 霧中劍客 | 懸賞陣容在 5F-1；本段只讓機制可用，叛徒戰的青霧執事照 19.7 套霧隱的 |
| 5B4c-5 | 機遇的次數 | 同一個機遇骨架每個角色只能拿一次技能（其他解法不受限） |
| 5B4c-6 | 機遇的組成 | 完整技能三選一；`region_keywords`＝觸發關鍵字（見待決 3）；完整技能產生器不支援 0／1／2 組成，照原本組成 |
| 5B4c-7 | 骨架 8「獵人倒下即失敗」 | 引擎沒有保護目標，先用守點 |
| 5B4c-8 | 地圖沒有該勝利條件 | 優先挑支援的地圖；都不支援時全滅 |
| 5B4c-9 | 「解決」 | 情境判定或解法有結果（成功、部分成功、失敗）；放棄、離開不算 |
| 5B4c-10 | 霧魅加人 | 一般抽陣容的敵方最後、混精英之後；滿 4 名不加；遭遇變化不加 |
| 5B4c-11 | 崖上石背熊沒有修士 | 鷹 ×2 為敵方、熊為第三方；冬湖石背熊、雷羽鷹巢各補 1 名同地點的修士（敵方至少 2 名） |
| 5B4c-12 | 高一階技能之後 | 角色下次升階時照角色階級重配（之後和其他技能同階；沿用既有的升階重配） |

## 7. 待 PM 決定

1. **機遇的高一階之後會被拉平**：升階重配把所有技能重配到角色階級，高一階的技能在角色下一次升階時就和其他技能同階（5B4c-12）。要保留「永遠高 1 階」需要改升階重配。
2. **機遇的「第 7 天前保底 1 次」**（07 7.6）與其他機遇來源（擊殺稀有精英、隱藏祭壇）沒做。
3. **機遇的關鍵字由觸發情境決定**：目前把觸發關鍵字（帶電）當新方向的偏向傳給候選產生器，但機遇的條件就是「已裝備帶電技能」，偏向只挑玩家 **沒有** 的關鍵字，所以實際上不起作用，候選照一般加深／橋接／新方向。要讓三張都偏帶電，需要 skillgen 加「指定關鍵字」的模式（另排）。
4. **完整技能三選一很慢**：測試角色（冰杖施法者）一次 `make_offer(..., "complete")` 約 14 秒（時間花在橋接候選的隨機組合器），大世界在玩家按下機遇時同步產生。roguelite 與主線的完整技能也是同一條路；是否要另排效能段。
5. **霧中劍客**的懸賞陣容（修士精英＋霧隱的、分身）在 5F-1；機制已可用。
6. **灰燼之心第 1 階段護甲 +1**：世界旗標 `ashen_heart_hardened` 已有；灰燼之心、荒原骨架 13 的個人攔截（「被攔下的碎片數」抵銷）等荒原內容做時接上。
7. **骨架 22 失敗也算解決**（5B4c-9）：判定失敗就永遠拿不到渡婆婆這條暗門（暗門另可由骨架 7 拿到）。是否改成只有成功／部分成功才算。
8. **好感度**：+10 時柳掌櫃靠每天聊天到第 7 天才友善（20），「丹爐之謎」（開始條件＝柳掌櫃友善）約第 7 天才開；小蓮、阿岳 10 天內到不了信賴。若要更多 NPC 有機會到信賴，可以給他們加相關任務步驟或事件好感度（只改 content）。
9. **野獸三方的強度**：三組陣容的總人數變成 4、5、3，未量；第三方掉落屬 5D-2。

## 8. 檢查

- 已 `git merge main` 兩次（5B-5b `1c2ea681`、玩法 PM 文件 `4fec52dd`；後者只改設計文件與交接，和本段一致）。計畫文件：本段第 21 節、之後各段第 22 節。
- 開發中：`uv run pytest -q tests/world tests/content tests/api tests/roguelite/test_offers.py -n 8 --timeout=1800`：2737 passed。
- 合併 5B-5b 後：`uv run pytest -q tests/cli tests/test_architecture.py tests/world tests/content tests/api tests/roguelite/test_offers.py -m "slow or not slow" -n 8 --timeout=3000`：**2934 passed**（CLI 快照不用重產）。
- 前端：`npx vitest run` 127 檔、1214 passed；`npm run build` 通過（只有既有的 chunk 大小警告）。依賴用 `corepack pnpm -C client install --frozen-lockfile` 裝在 worktree。
- `ruff check .`、`ruff format --check .`、`mypy`（1060 檔）、`lint-imports`（9 kept）通過。
- 新增的 `# noqa`：`solutions._opportunity` 的 `PLR0917`（同 5B-4b 的 `_parley`、`_combat`：一個解法的完整結算要的參數）。沒動引擎，不需戰鬥重播；沒跑全量 `scripts/check.py`。
