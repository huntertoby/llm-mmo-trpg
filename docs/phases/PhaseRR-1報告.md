# Phase RR-1 報告｜升階後重閃退回存檔裡的閃現歷程

> 實作 agent，2026-11-13（Opus 5.5）。依據 main `917e4989e`（含 FL-1g、玩法 PM 定案 `b7eedf2ee`：06 6.34.9「重推套不上的那一筆」）。
>
> commit：`26c6dbb7a`（後端與測試）、`983a7ed1f`（前端重閃格標灰）、本報告與上手筆記另一個 commit。

## 1. 做法

### 規則（b7eedf2ee 原文）

> 照新階級重推時，某一筆變化套不上……這一筆**照存檔裡的定義保留**，不丟掉、也不改用當初的階級重推。新的閃現與重閃都用同一個退路……真的出不了題的格子才照 6.34「費用方向」第 7 點標灰。

### 存檔裡要有「那一筆」的定義

以前存檔只有整招最後的定義（`generated_skills` 裡那一張），沒有每一筆套完的樣子；套不上的那一筆在歷程中間時（重現案例就是：第 2 筆套不上、第 3 筆在它之後），沒有東西可以「照存檔保留」。所以：

- `FlashRecord` 多一個選填欄位 `kept: SkillDef | None`：**升階前這一筆套完的定義**。沒有時不輸出（舊存檔、沒出事的歷程逐字不變），也**不進技能 ID 的雜湊**（`FlashRecord.identity()`，`flashed_identity` 改用它），所以技能 ID、parity 夾具都不變。
- **只在升階時寫入**：`roguelite/retier.sync_skill_tier` 先呼叫 `flash_derive.keep_failed(old_tier=run.skill_tier, tier=新階)`：
  1. 照升階前的階級推一次歷程（這就是存檔裡那張定義的每一格；不是「照當初選的階級」逐筆推）；
  2. 照新階級逐筆推，套不上、又還沒有 `kept` 的那一筆，記下第 1 步那一格；
  3. 第 1 步也推不了（內容改版，3W-R1）就不記，照舊重配存著的定義。
- **讀取在 `derive_chain`**：某一筆照目前階級套不上、而且有 `kept` 時，改用 `at_role_tier(kept, 目前階級)`（照新階級重配那張存著的定義），然後照常往下推。閃現（`_builder`）、重閃、`skill_before`、`has_options`、再升階全部走 `derive_chain`，所以「新的閃現與重閃都用同一個退路」。
- **重閃換掉第 N 筆時**，N 之後各筆的 `kept` 清掉（`with_reflash`）：那些定義裡含被換掉的舊第 N 筆，不能再用；那幾筆改照目前階級重推，推不上就是那個候選不合法。N 之前的照留。
- 大世界城鎮：`world/growth.sync_tier` 本來就呼叫 `sync_skill_tier`（`as_run`／`from_run` 帶著 `flash`），不用另外改。`WORLD_RULES_VERSION` 28 → 29（同一份日誌，升階時中間那一筆套不上的角色重播結果會不同）。

### 重閃格標灰（FL-1g 待決 4）

b7eedf2ee 有寫「真的出不了題的格子才照 6.34『費用方向』第 7 點標灰」，照做：

- `ReflashSlotOut` 多 `available`（預設 `True`）、`problem_zh`。`run_presenter._flash_out` 對每一格用 `has_options(flash_request(..., slot=s))` 實際算（同 FL-1c，有快取）；轉型提示改用同一個結果。
- 灰字 `flash_offer.NO_REFLASH_OPTIONS_ZH`＝「這一格目前沒有可以重閃的變化」（前端同一句 `NO_REFLASH_OPTIONS_TEXT`）。**字待定**，見第 5 節。
- 前端只改重閃入口：`run/flash.ts` 的 `reflashSlots()` 多 `none`／`problem`；`run/CampfireSkillCare.tsx` 的重閃鈕 `disabled`、`title`、`data-reflash-none`，鈕裡多一段 `flash-none-note` 灰字（沿用 FL-1c 的樣式）。一輪營火與大世界成長面板共用 `ReflashSection`，兩邊一起生效。
- 按下去的伺服器端照舊：沒有選項時 `open_flash` 拋「這招這一次沒有合法的變化（沒有扣點）」，不扣點。
- OpenAPI 重產、`gen:api` 重跑（`schema.d.ts` 多兩個欄位）。

## 2. 重現案例的結果

`new_dev_run(第一個開發起始包, 種子 2)`，`auto_play` 到營火；「灼燃・燃燒爆」＝第 1 次蓄力、第 2 次 `keyword_imbue`（潮濕，1 階時選）、第 3 次 `major_intensify`（升到 2 階後選）。

| | 修之前 | 修之後 |
|---|---|---|
| 2 階 `derive_chain` | 第 2 筆失敗 | 推得過（第 2 筆照 `kept`） |
| 重閃第 3 格 | 17 個候選全失敗，入口沒有提示 | 出得了題；「可以重閃第 3 格轉型」回來了；`open_flash`＋選第 0 個都成功 |
| 重閃第 2 格 | 出得了題 | 出得了題（換掉的就是那一筆） |
| 重閃第 1 格 | 出不了題 | **仍出不了題 → 標灰** |
| 技能 ID | `…_fl_3b9bc3dd28` | 不變 |

重閃第 1 格的原因不是升階：逐一試候選，幾乎全部卡在第 1 筆自己——被換掉的「蓄力」預算分數很高（強度下限 22680‰），換成任何小變化都低於它（3W-2「重閃不低於換掉之前」）；只有 1 個候選是因為後面的第 2 筆照 2 階重推套不上。這屬於「真的出不了題」，照第 7 點標灰。

## 3. 測試

- 新增 `tests/roguelite/test_reflash_tierup_rr1.py`（7 個）：
  - 升階時第 2 筆記下的 `kept` 正好是升階前歷程的那一格，其他筆沒有；技能 ID 不變；卡片照新階級。
  - 重現案例：重閃第 3 格 `has_options`、`transform_hint`、`available` 都是真，`open_flash` 扣點出題、選第 0 個成功。
  - 每一招每一格的 `available` 和實際 `open_flash` 成不成功一致，`problem_zh` 是固定句。
  - `with_reflash` 換第 1 格清掉第 2 筆的 `kept`、換第 3 格不動。
  - 全部套得上（3、4 階）時 `keep_failed` 不動。
  - `sync_skill_tier` 從升階前一刻重跑得到同樣的 `flash`；已同步時原樣回傳。
  - 大世界：同一份升階前的成長欄位放進角色（`skill_seed` 打成種子 2、等級換成世界的 2 階），`sync_tier` 得到同樣的 `flash`，下一次閃現出得了題。
- 改了的既有斷言（都在預測內）：`tests/api/test_flash_api.py` 的 `reflash_slots` 多兩個欄位；`tests/api/test_pr2a_range_practice.py`、`tests/world/test_opening_stages.py` 的 `WORLD_RULES_VERSION == 29`。
- 前端：新增 `client/src/run/rr1ReflashNone.test.ts`（2 個：`reflashSlots` 的 `none`／`problem`、按鈕停用與灰字）；`run/flash.test.ts` 完整技能那一條的 `toEqual` 多 `none: false, problem: null`。
- **預測與實際**：`kept` 沒有時不輸出、不進雜湊，`derive_chain` 只在套不上時才看它，所以預測 parity 夾具、存檔快照、技能 ID 都不變；只有升階時中間那一筆套不上的一輪（模擬報表）可能變。實際：見第 4 節，slow 的 parity 與 flash 測試全過，沒有重產任何夾具或快照。

## 4. 檢查（交件前）

| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run pytest -q -n 8`（rr1、fl1g 提示、flash_api、retier、world flash、flash_state） | 0（77 passed） |
| `uv run pytest -q -n 8 -m "not llm"`（含 slow：`test_refactor_parity`、`test_flash_run`、`test_flash_llm_run`、`test_flash_cost_fl1a`／`fl1c`、`sim/test_flash_report`、`sim/test_flash_balanced_policy`，加上版號相關的 `test_pr2a_range_practice`、`test_opening_stages`、`test_world_store_cache`、`test_runs_api`、`cli/test_run_cli`） | 0（1128 passed） |
| 開發中另跑：flash 相關 11 檔（含 `skillgen/test_flash.py`、`test_flash_major.py`、`world/test_first_flash.py`、`api/test_newcomer_api.py`） | 0（164 passed） |
| `uv run trpg battle --map bandit_lair --seed 7 --log-json …` ＋ `uv run trpg battle replay …` | 0（重播驗證通過：73 個動作、254 個事件） |
| `corepack pnpm -C client exec vitest run src/run/ src/world/fl1cFlashNone.test.ts src/world/pnl3Quest.test.ts` | 0（175 passed） |
| `corepack pnpm -C client build` | 0 |

沒有重產任何夾具或快照（預測不會變，實際也沒有失敗）。沒有跑全量 `check.py`，也沒有做數值量測。

## 5. 待 PM 決定

1. **灰字的字**：「這一格目前沒有可以重閃的變化」。06 第 7 點只定了閃現面板的「這招目前沒有可以閃的變化」，重閃格沒有字，先比照寫，常數 `flash_offer.NO_REFLASH_OPTIONS_ZH`（前端 `NO_REFLASH_OPTIONS_TEXT`），定了只換這兩行。
2. **重現案例的重閃第 1 格仍標灰**：原因是 3W-2 的強度下限（被換掉的蓄力太強），不是升階。照 b7eedf2ee「真的出不了題的格子才標灰」處理；要不要讓這類格子有題，是另一條規則（玩法 PM）。
3. **重閃前面一格時，後面保留的定義作廢**：例如換掉第 1 筆後，第 2 筆的 `kept` 含舊的第 1 筆，不能用；第 2 筆改照目前階級重推，推不上那個候選就不出。這是「保留存檔裡那一筆」與「換掉前面一筆」同時成立時，最保守的解讀（不丟掉第 2 筆、也不讓新的第 1 筆被舊定義蓋掉）。
4. **「存檔裡的定義」怎麼取**：存檔本來只有整招最後的定義，沒有每一筆的；這次在**升階當下**照升階前的階級推一次歷程，取那一格存起來（等於當時存檔那張定義的中間狀態），之後不再用舊階級推。若玩法 PM 的意思是「只能用整張存著的定義」，那歷程中間那一筆就沒有東西可保留，重現案例的重閃第 3 格會繼續出不了題。
5. **舊存檔不補**：已經升過階的存檔不會補記 `kept`（沒寫遷移），那些格子照實標灰；開新一輪、新角色升階後才有。
6. **存檔格式版號沒升**：`kept` 是選填、沒有時不輸出，舊存檔逐字不變、照讀，所以 `trpg-run/13`、`trpg-char/14` 都沒升（WP-3 正在改 `test_wish.py` 等 15 個寫死 `trpg-char/14` 的測試，升了會撞）。只升 `WORLD_RULES_VERSION` 29（重播結果會變）。若要照 WP-1 的前例「多了選填欄位也升 CHAR_FORMAT」，合併時再升。**WP-3 若也升 `WORLD_RULES_VERSION`，合併時要再加一。**

## 6. 沒驗證

- 沒有實機截圖（瀏覽器）：只用 vitest 的靜態渲染驗了按鈕停用與灰字。
- 沒有跑全量 `check.py`、沒有做數值量測。
