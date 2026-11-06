# Phase 3W-R1 報告｜真相來源與失敗處理

依據：`docs/phases/Phase3W計畫.md` 第 6 節（3W 大段審查 ①、②、⑨、⑩ 與開發 PM 決定）。實作者：opus。不改遊戲規則；存檔結構與戰鬥紀錄結構都沒有改，`trpg-run/13`、`LOG_FORMAT` 不遞增。

## 1. Commit

| commit | 內容 |
|---|---|
| `0cd80177` | ⑨ 重配快取掛在 `ContentLibrary` 上 |
| `938e604f` | ① 升階後同一招只有一個真相來源；② 歷程重推失敗的錯誤型別與退路；回歸夾具 |
| `f35ba428` | ⑩ 舊引擎的戰鬥中存檔改成從該場開頭重來；拿掉靈感換算的「待 PM 決定」標記 |
| `26e8f7fe` | 前端：讀檔提示、閃現預覽的歷程原因（沿用既有提示區） |
| （本報告） | 報告；3W-5 報告待決 1 標註已確認 |

## 2. 做了什麼

### ① 升階後同一招只有一個真相來源
- `roguelite/retier.sync_skill_tier`：有變化歷程（`records` 或完整技能的 `adjustment`）的技能改用 `derive_skill(base_def, state, seed, 新階級)` 從原技能照新階級重推整條歷程；`retier` 只處理沒閃過的技能（`at_run_tier`，含手寫技能換 `_t<階級>`）。
- 結果：卡片上的定義 ＝ 下一次閃現的「套用前」（`skill_before`）＝ 重閃強度下限的來源（同一條 `derive_chain`）。
- **ID 不加階級**：`_fl_<雜湊>` 仍只由歷程決定。理由：一輪裡同一時間每個 ID 只有一個定義（升階時直接取代 `generated_skills` 裡那一筆），戰鬥的規則包內嵌當時的定義（`with_skills`），存檔也只存目前那一份；加階級要改存檔 ID 與 `flash` 鍵的轉換，收益不明。所以不需要存檔相容處理。
- 3W-9b「預算分數不低於升階前、維持升階前比例」：見第 4 節量測與待決 1。

### ② 歷程重推失敗與「變化不合法」分開
- `skillgen/flash.py` 新錯誤型別：`FlashStepError(FlashError)`（`derive_chain` 第 `nth` 筆套不上，帶 `nth`、`template`）、`FlashHistoryError(FlashError)`（**已存的**歷程在目前的內容重推不了，帶 `reason_zh`）。`history_error()`、`history_problem()` 檢查已存歷程。
- `FlashRequest.current`：存檔裡已推出的這招（`roguelite.flash_request` 帶入卡片定義）。
- 選項產生器 `_builder()` 先重推一次已存歷程：
  - 可以重推 → 照舊。
  - 重推不了 → 記下 `broken`；**閃現**改由 `_derive_on_current` 把新變化套在 `current` 上（強度下限照它；轉型照常從原技能起算、轉型前套不上的變化省略），ID／名稱照新歷程；**重閃下限**改用 `current` 的預算分數（`_fallback_floor`，不會變 0，且比被換掉那一筆更嚴）；`skill_before` 退回 `current`（不再退回原技能）。
- 升階：重推不了時退回 `retier(存著的定義)`，之後的閃現也以它為起點（同一個真相來源：卡片）。
- 傳承：舊技能被帶走的小變化若模板在目前的內容已不存在，`inherit_problem` 先回傳「舊技能第 N 次的變化（模板）在目前的內容版本已經沒有了，不能帶走」；其他套不上的情形 `ChoiceError` 寫明是哪一筆對哪一招不合法。都不改狀態。
- API：`FlashPreviewOut.history_note_zh`（重推不了的原因）；前端閃現出題畫面在既有的 `flash-problem` 提示樣式下顯示（不新增畫面）。
- 回歸夾具 `tests/roguelite/fixtures/flash_history_3wr1.json`：`build_fire` 種子 6 代打到第一個營火的存檔（`skill_fire_bolt` 閃過 3 次）；重產用 `uv run python -m tests.roguelite.test_truth_3wr1`。「內容改版」用拿掉 `range_plus` 小變化模板的內容庫模擬。

### ⑨ `skill_tier._CACHE`
- 拿掉模組全域快取；改成 `ContentLibrary.retier_cache`（`init=False`、`compare=False`、`repr=False`），隨內容庫回收；`dataclasses.replace` 換內容後是新的空快取。鍵 `"<技能 JSON 的 SHA-256>/<階級>"`（hashlib，不用 `id()` 或內建 `hash()`），上限 4096 筆、滿了清空。

### ⑩ 舊戰鬥中存檔
- `loads_save` 遇到戰鬥中存檔的 `engine` 與目前 `LOG_FORMAT` 不同：不再拒絕，清掉 `battle`、保留戰鬥節點（開戰不改 `RunState`，等於還沒開打），`engine` 改寫為目前版本。新函式 `loads_save_noted`／`load_save_noted` 回傳 `(存檔, 提示)`，提示為「這場戰鬥的紀錄格式已更新，從這場的開頭重新開始。」（`STALE_BATTLE_NOTICE`）。
- API `/api/runs/load` 回應多了 `load_notice`（只在讀檔回應帶一次）；前端沿用開局 LLM 提示的 `NoticeBanner` 顯示。CLI `trpg run auto --from` 印出提示。
- 「戰鬥中但節點不是戰鬥」的檢查照舊拒絕；`ruleset_hash` 不符的戰鬥中存檔照舊拒絕（範圍外）。
- `convert_raw_run` 靈感換算已由玩法 PM 確認（`1752ae6c`）：`save.py` 模組說明的「待 PM 決定」改成已確認；`Phase3W-5報告.md` 待決 1 標註已確認。

## 3. 驗收

- 新測試 `tests/roguelite/test_truth_3wr1.py`（10）：
  - 升階後 `generated_skills` 裡的定義 == `derive_skill` 結果、ID 不變、階級為新階級；所有技能升階後預算分數不低於升階前；沒閃過的仍 == `retier`。
  - 升階後馬上閃現：`skill_before` == 卡片；重閃最後一筆的下限 == 卡片的預算分數；重閃第 1 筆的下限 == 新階級歷程第 1 筆。
  - 內容改版（拿掉 `range_plus`）：`FlashHistoryError`（`nth=2`）與原因字串、API 預覽 `history_note_zh`；閃現有選項（不被當成「沒有合法變化」）、起點是存檔的定義、每個選項不低於卡片、確定性、選了之後歷程 4 筆；重閃第 1、3 筆下限 == 卡片分數 > 0；升階退回 `retier`；傳承回傳具體原因且不改狀態。
  - 重配快取在內容庫上、鍵為 SHA-256＋階級、`replace` 後為空。
- `tests/roguelite/test_save.py`：引擎版本不符改成捨棄戰鬥＋提示。`tests/api/test_runs_api.py::test_mid_battle_save_from_an_old_engine_restarts_that_battle`：讀檔 `battle_id` 為空、節點是戰鬥、`load_notice` 只帶一次、重新開戰從第 1 回合。
- 收尾檢查：`ruff check`、`ruff format --check`、`mypy`（835 檔）、`lint-imports`（7 kept）全過。pytest（`-m "(slow or not slow) and not llm"`）：`tests/roguelite`＋`tests/skillgen` 3126 passed／14 skipped；`tests/api`＋`tests/sim` 442 passed；`tests/cli`（`--timeout=3000`）156 passed。前端：`gen:api` 重產、client fixtures 重匯出（無差異），vitest 120 檔 1174 passed，`build`（含 `tsc --noEmit`）通過。未跑 `scripts/check.py` 與大型模擬；沒有開瀏覽器預覽（前端只多兩個條件顯示）。
- 複雜度：沒有新增 `noqa`。

## 4. 量測（升階：重推歷程 vs 舊 `retier`）

腳本（不進版控）：`build_fire／summoner／trapper／healer／wallburn／storm` × 種子 1～4、10～12 的 AI 代打，每次角色升階時比較閃過的技能。共 44 筆（1→2、2→3 階）：

| | 預算分數低於升階前 | 比例偏離升階前 > 50‰ | 平均偏離 | 比例 < 70% |
|---|---|---|---|---|
| 重推歷程（現在） | 0 | 8 | 35‰ | 0 |
| 舊 `retier`（存著的定義） | 0 | 5 | 33‰ | 1 |

偏離大的例子：某地雷 0.912 → 0.802（`retier` 0.895）、某閃電 0.890 → 0.973、某踢擊 0.875 → 0.956（`retier` 0.685，出窗）。原因：重推時每一筆變化重新調整（`retune` 的亂數與預算窗），不以升階前的比例為目標。

## 5. 待 PM 決定

1. **「維持升階前比例」對閃過的技能只是近似**：單一真相來源（重推歷程）下，第一步（原技能 `retier`）維持比例，但後面每一筆變化照閃現規則重調，最後比例可能偏離超過 `target_tolerance_permille`（50‰）；44 筆中 8 筆，最大約 110‰，分數都不低於升階前、都在窗內。採保守：真相來源優先（審查 ① 的問題就是兩條路不一致），不再加第二條路。若要嚴格維持比例，需要讓閃現的 `retune` 也接受目標比例（會改閃現本身的數值，屬規則變更）。
2. **歷程重推不了時的傳承**：模板已被拿掉的變化不能帶走（`inherit_problem` 先擋、說明原因），沒有「自動略過那一筆」的退路（略過會讓玩家少帶一筆而舊技能照樣消失）。
3. **歷程重推不了時的重閃**：選項仍照完整歷程重推，所以只有換掉壞掉那一筆（或之後的）才可能有選項；換其他欄時多半「沒有合法的變化（沒有扣點）」，預覽會先顯示原因。下限採存檔定義的分數（比被換掉的那一筆更嚴）。
4. **ID 不含階級**（見 2 ①）：若之後要讓同一個 ID 跨階級在某處並存（例如戰鬥紀錄回看要找回升階前的卡片），再考慮加階級並寫存檔轉換。
