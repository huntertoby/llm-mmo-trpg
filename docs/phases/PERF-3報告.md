# PERF-3 報告：完整技能三選一再加速（玩法 PM 2026-11-03）

分支 `worktree-agent-a37ccddc72f920357`（base main `d2ba0ae9`，含 PERF-2 與 content 路徑修正）。只動 `trpg.skillgen`、`trpg.roguelite.offers`、`trpg.api`（背景計算）；世界引擎沒改。

## 1. 三項改法

1. **指定關鍵字的組合不抽傳說**（`skillgen/random_composer.py`）：`compose_with_stats(..., skip_legendary=True)` 時，種子變體的稀有度擲到傳說就**跳過這個變體**（不組、算一次嘗試），換下一個變體。只有三選一的候選產生器（`candidates.from_composer`，涵蓋機遇、區域偏向、一般完整技能三選一的組合器來源）會傳 `skip_legendary=True`；沒指定關鍵字的一般組合、開局技能（`roguelite.start`）、LLM 退回（`proposal_fallback`）、工坊、CLI 照舊（預設 `False`，結果逐字不變）。傳說本來就不當候選（`_Search.usable`），所以這只是省掉「組完傳說再丟掉」的時間（PERF-2 熱點 42%）。
2. **橋接搜尋的變體數上限**（`skillgen/candidates.py`）：`BRIDGE_VARIANT_CAP = 400`（`CandidateRules.bridge_variant_cap`，0＝不設）。橋接的**多關鍵字選項**（兩個持有的關鍵字、往外一步）共用這 400 個組合器種子變體（組合器的 `keyword_tries` 只給剩下的額度，用掉的變體數由 `ComposeResult.variants`／`KeywordExhaustedError.variants` 回報）。用完還沒找到就跳過剩下的多關鍵字選項，照 6.27.4 ③ 放寬關鍵字（單一持有關鍵字，再照 ①② 找、④ 偏離），`fallback` 為真。單一關鍵字的搜尋不受上限管，所以三張不會少。亂數只來自 `Rng(seed).fork("bridge")`，計數是確定性的整數，可重播。
3. **背景預先算好三選一**（`api/offer_prefetch.py` 新、`api/world.py`、`api/app.py`、`roguelite/offers.py`）：
   - `roguelite.offers`：`OfferCache`（執行緒安全；鍵 →（內容庫物件, `Future`）；上限 64 筆）與 `using_offer_cache()`（ContextVar）。裝了快取時 `make_offer` 先算 `offer_key`＝**候選產生器的完整輸入**（`CandidateRequest` 全欄位：關鍵字分布、武器、種子、階級＋高 1 階、行為、屬性、手持、排除、區域偏向、mix…）＋三選一種類＋第幾組＋最高屬性 的 BLAKE2b；命中就回傳，另一條執行緒正在算同一把鍵時等它算完。`run.llm` 或裝了觀察者（模擬）時不用快取。沒裝快取時行為逐字相同。
   - `api.offer_prefetch.OfferPrefetcher`：一條背景執行緒（`ThreadPoolExecutor(1)`）。每個世界動作之後（`WorldStore._apply`）與角色第一次從存檔讀進來時，預測看得到的三選一並丟到背景：
     - 機遇：`pending_event` 的骨架有可用的機遇解法（條件成立、這季沒拿過）→ 參數照 `solutions._opportunity`（`requires_keyword`、`opportunity_tier_bonus`）。
     - 劇情步驟：進行中任務的下一步有 `reward.offer` → 參數照 `quests._offer`；另算一份「加上這一步經驗後」的角色（可能升級換階）。
   - `WorldStore._apply` 把 `world_step` 包在 `using_offer_cache(...)` 裡：命中直接拿；預測錯（例如中間換了裝備）只是沒命中，照舊同步算。伺服器關閉時取消排隊中的工作（`app.router.on_shutdown`）。

## 2. 上限數值與理由

量測（`.scratch` 腳本，`scripts/perf_complete_offer.py` 的 6 組角色 × 8 輪種子＝48 組，`--cold`）：

- 不設上限（只做第 1 項）：橋接時間 ≈ 變體數 × 2.7 ms；**有找到配對的橋接最多用 165 個變體**，用到 400 個以上的（最多 3,265）**全部最後都退回單一關鍵字**。所以上限 400 幾乎不改變「有沒有找到配對」，只砍掉注定找不到的長尾。
- 上限 400：橋接最多約 1.1～1.5 秒；48 組中 17 組碰到上限。上限 250：最壞總時間沒有再下降（最壞由非橋接部分決定，見第 5 節），反而多退回。
- 定 400：最壞總時間約 3 秒（PM 目標「最壞約 3 秒」）。寫成常數 `trpg.skillgen.candidates.BRIDGE_VARIANT_CAP`（沒放進 `content/roguelite.yaml`，因為要改 `trpg.content` schema，超出這次範圍；見待決）。

## 3. 前後時間（秒，`scripts/perf_complete_offer.py --cold --rounds 4`，24 組）

| | 平均 | 中位數 | 最長 |
|---|---|---|---|
| 之前（main d2ba0ae9） | 2.59 | 1.94 | 11.33（術士 3002） |
| 之後（本分支，同步計算） | 1.52 | 1.32 | 3.49（治療 1005） |
| 之後，48 組（8 輪） | 1.34 | 1.11 | 3.2～4.0（火 5001，見下） |
| 之後，背景已算好時選機遇 | 快取命中，≈ 0 | | |

各輪最長：之前 6.37／7.59／2.50／11.33，之後 2.57／3.49／2.80／1.87。機器上同時有其他 agent 在跑，單次波動約 30%（火 5001 同一份程式量到 3.17 與 3.98）。

## 4. 快照與結果變動

- `tests/skillgen/fixtures/refactor_3wr2.json`：**沒有變**（`-m "slow or not slow"` 877 passed；它不經過關鍵字組合）。
- 改變的是完整技能三選一的候選（第 1、2 項，PM 已同意）：`perf_complete_offer.py` 24 組的結果指紋有 8 組變、16 組不變（不變的例：火 1 `f9ec3d757788`、治療 5 `226e8ca1a08b`、刺客 1011 `e63a245ff247`）。
- 靠種子的測試：`tests/skillgen tests/roguelite tests/world tests/api` 全過，**不需要重挑種子**、沒改任何斷言。

## 5. 確定性證明

- 第 1、2 項：只多了整數計數與「擲到傳說就跳過」，亂數仍只來自種子的 `fork`；`tests/skillgen/test_perf3_candidates.py`：同一輸入兩次逐字相同、上限內三張不少、`bridge_used ≤ cap`、預設值與 `skip_legendary` 不影響其他呼叫者（一般組合與沒要求跳過的關鍵字組合照樣會出傳說）。
- 第 3 項：快取鍵是候選產生器的完整輸入，命中時回傳的就是同一份計算結果。`tests/roguelite/test_offer_cache.py`：命中與無快取逐字相同、鍵涵蓋各參數（經驗等不影響候選的欄位不進鍵）、LLM／觀察者不走快取、等候正在算的鍵、失敗後移除、上限與內容庫身分。`tests/api/test_offer_prefetch.py`：背景算好後把 `_compute_offer` 換成會拋錯的函式，`world_step` 與 `WorldStore.act` 的機遇結果仍與同步計算的角色狀態、事件逐字相同；劇情步驟的預測參數正確。
- 世界引擎沒改；背景執行緒只在 `trpg.api`；`lint-imports` 9 kept。

## 6. 檢查

- `tests/skillgen tests/roguelite tests/world tests/api`：4772 passed、14 skipped（-n 8）。
- `tests/skillgen/test_refactor_3wr2.py -m "slow or not slow"`：877 passed。
- `tests/cli -m "slow or not slow" --timeout=3000`：180 passed（-n 8）。
- `ruff check .`、`ruff format --check .`、`mypy`（1077 檔）、`lint-imports`（9 kept）全過。
- 交件前 `git merge main`：main 仍是 `d2ba0ae9`，沒有新東西。

## 7. 待 PM 決定

1. **上限 400 寫成常數**（`BRIDGE_VARIANT_CAP`），沒進 `content/roguelite.yaml`（要改 `trpg.content` 的 roguelite schema）。要不要搬進 content？
2. **「指定關鍵字不抽傳說」只套在三選一的候選產生器**：開局技能（`roguelite.start`）、LLM 退回（`proposal_fallback`）、工坊、CLI 的關鍵字組合照舊（保守做法：不改開局與其他結果）。要不要擴大？
3. **背景還在算時，同步呼叫等它算完**，而不是再算一次（規格寫「沒算完就照舊同步算」）。理由：Python 的 GIL 下兩邊同時算只會更慢，等它的結果與自己算逐字相同；背景算失敗時才自己算。要照字面改回自己算也只是一行。
4. **剩下的最壞情況不在橋接**：火 5001 這類約 3 秒裡橋接只佔 0.3～0.4 秒，其餘在加深／新方向的組合與 `complete_strength`；要再壓需另開段。
5. 劇情步驟的預測不含「同一步先給劇情技能再給三選一」與「打完戰鬥才拿到的經驗」，這兩種情況沒命中，照舊同步算（目前內容的劇情步驟三選一都是白板，本來就快）。
