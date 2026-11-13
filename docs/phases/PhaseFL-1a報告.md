# Phase FL-1a 報告：閃現「蓄力／輕巧」規則修正＋選項差異清單（後端）

> 規格：`docs/design/06-技能.md` 6.34「費用方向」第 1～4 點（玩法 PM 575c8baa，2026-11-13）；調查 `docs/phases/閃現蓄力調查.md`。開工時 `git merge --ff-only main`（`960d86bd6`）。前端畫面（FL-1b）不在本段。

## 1. 規則怎麼改

程式：新模組 `src/trpg/skillgen/flash_cost.py`（規則與確定性退路），`flash_derive.apply_variation` 遇到 `op` 為 `charge`／`light` 時交給 `_apply_cost`。

**蓄力（`charge`）**

1. 草稿照舊：冷卻 +2（最多 5；已經 ≥ 5 照舊不出）。
2. 先走 **原本的預算重調**（同一組子亂數 `"0"`、`"0.r1"`…），結果必須「至少一項強度欄位嚴格變強」（`strength_moves`，比效果與接續段的骰子平均、倍率、回合、強度、距離、層數等）。本來就變強的結果因此 **逐字不變**（含 38 招一升一降）。
3. 不合格（打平）或重調失敗時，走確定性退路 `charge_adjusted`：依「傷害 → 狀態強度 → 狀態回合」一次只動一項：
   - 傷害（`damage`、`delayed_damage`，含接續段）：骰子或武器倍率往上 `flash_cost.damage_rungs` 格；比例 < 70% 時同一項再往上，> 100% 停。
   - 狀態強度：治療、護盾骰子；數值型狀態（`scales_with_magnitude`）的 `magnitude_permille` +`flash_cost.magnitude_step`（上限 `retier_growth.magnitude_max`）——**只用在回合已經加不上去的狀態**（同升階 BAL-12e「先加回合、到上限才加強度」；否則點燃斬會先拿到 +25‰ 強度而不是規格例子的 5 → 6）。
   - 狀態回合（`apply_status`）：每次 +1，上限 ＝ min(原招 + 2, max(組合器持續上限 6, 原招))。「原招」由 `apply_variation(..., origin=)` 傳入（`derive_chain`／`derive_on_current` 傳 `at_role_tier(base)`；轉型後重套的變化以轉型結果為原招）。
   - 第一個通過驗證、不低於強度下限、而且真的有一項變強的版本就用；全都不行 → 不出蓄力。
4. 說明字不改。

**輕巧（`light`）**

1. 草稿照舊（AP −1、冷卻壓到 ≤ 1；AP 已是 1 時依序冷卻／法力／耐力 −1，最少留 1）。
2. 合格條件：**沒有任何一項變強、至少一項嚴格變弱**（`light_ok`）。
3. AP 2 → 1：先走原本的預算重調（結果過 `light_ok` 就用——改前 86＋400 筆「變弱」逐字不變）；不合格再走退路。
4. AP 已是 1：不走重調（它的強度下限只換算 AP，重調只會打平或變強，調查第 4 節），直接走退路。
5. 退路 `light_adjusted`：依「傷害 → 狀態強度（治療護盾骰子、強度最低回 1000‰）→ 狀態回合（最少 1）」一次只降一項，每一格都檢查驗證與 70～100% 窗；一直降到「扣掉代價的分數」`cost_power`（總點數 ÷（AP 係數 ×（1000＋冷卻與資源折抵）÷1000））不高於閃現前為止（＝少付的代價照預算扣回）；再降就跌出 70% 時停在最後一個合格的。重閃時另外不低於被換掉那一筆。全都不行 → 不出輕巧。

**數值工坊**：`content/skill_budget.yaml` 新增 `flash_cost: {damage_rungs: 1, magnitude_step: 25}`（`BudgetRules.flash_cost`／`FlashCostRules`，保守占位：一格、同升階的 25‰），白名單 `content/tuning_fields.yaml` 的 `kind: budget` 加兩列（中文說明、建議範圍 1～3、10～100）。回合 +1／累計 +2／最少留 1 是規格定的規則，不開。

## 2. 掃描統計（調查的方法：1 階主動、內容檔＋白板配方 × 三種武器 × 種子 0～7，種子 12345）

腳本在暫存區 `fl1a/scan.py`（比較 `strength_moves` 同一套欄位）。內容檔現在 277 招（調查時 274）。

| | 改前 | 改後 |
|---|---|---|
| 蓄力・內容檔：套得上 | 236 | 163 |
| 　有一項變強（其中一升一降） | 137（38） | 163（40） |
| 　**沒變** | **99** | **0** |
| 蓄力・白板：套得上 | 611 | 611 |
| 　有一項變強（其中一升一降） | 418（0） | 611（2） |
| 　**沒變** | **193** | **0** |
| 輕巧・內容檔：套得上 | 211 | 126 |
| 　變弱且沒有變強 | 86 | 126 |
| 　**沒變弱**（不變／變強） | **125**（109／16） | **0** |
| 輕巧・白板：套得上 | 428 | 512 |
| 　變弱且沒有變強 | 400 | 512 |
| 　**沒變弱** | **28** | **0** |

逐筆對照（改前 → 改後）：

- 蓄力內容檔：79 筆「只多冷卻」→ 不出（大多是調查 3.1 沒有強度旋鈕的召喚、地形、位移、規則改變類）；18＋2 筆「剛好落回原值」→ 變強；6 筆改前套不上 → 退路做得出來；改前有變強的 137 筆結果不變。
- 蓄力白板：39 筆「只多冷卻」→ 不出（召喚、隆地、振奮等）；152＋2 筆 → 變強（點燃斬、烙印擊……走回合）；39 筆改前套不上 → 套得上。
- 輕巧內容檔：AP 1 的 25 筆不變＋7 筆變強 → 變弱；84＋9 筆 → 不出；AP 2 → 1 的 86 筆結果不變，另 8 筆改前套不上 → 退路做得出來。16 招「變強」的現在 7 招變弱、9 招不出。
- 輕巧白板：AP 1 的 28 筆（隆地、振奮、喚出骸骨僕從、喚出元素火花）→ 不出；112 筆 AP 2 改前套不上 → 套得上（例：點燃斬輕巧＝AP 1、冷卻 1、燃燒 5 → 2）。

## 3. 選項差異清單 `changes`

- `src/trpg/api/run_schemas.py`：`FlashOptionOut.changes: tuple[StatChangeOut, ...] = ()`。
- `StatChangeOut`：`field`（路徑）、`label_zh`、`effect_index`（效果列才有）、`before`、`after`（顯示用字串，新加的 `before`／拿掉的 `after` 為 `None`）、`direction`（`better`／`worse`／`cost`／`new`）。
- 組裝：`src/trpg/api/flash_changes.py::flash_changes(library, before, after)`；`run_presenter._pending` 對每個選項算（大世界經 `pending_flash_out` 共用）。「前」：閃現用玩家現有定義；重閃用 `skill_before`（被換掉那一筆之前）。
- 比的是 **卡片數字**（`card_stats`）：
  - `range`／`radius`／`size`：大 → `better`，小 → `worse`，從沒有到有 → `new`。
  - 代價 `cost.<kind>`（`ap`、`cooldown`、`mana`、`stamina`、`hp_percent`、`upkeep`、`uses_per_battle`…，同 `CostStat.kind`）：一律 `cost`，升降看前後值（法力是實付值，見待決 3）。
  - 效果 `effects[i].dice`（骰子平均＋固定值比）、`.multiplier_permille`（顯示「×1.15」）、`.amount`（回合／格數／層數）、`.magnitude_permille`（「1025‰」，狀態、表面、形態）；接續段 `followup[i]...`。
  - 同一位置換了原語或狀態：舊的記 `worse`（after `None`）、新的記 `new`。
  - 只列有變的，順序：形狀 → 代價 → 效果 → 接續段。
- 例：點燃斬蓄力 `[{cost.cooldown, 冷卻, 2→4, cost}, {effects[0].amount, 燃燒回合, 5→6, better}]`；霜寒之觸輕巧 `[{effects[0].dice, 傷害骰子, 1d8→1d6, worse}]`；雙槍連射蓄力同時有 `better`、`worse`、`cost`。
- OpenAPI 重產（`scripts/export_openapi.py`、`corepack pnpm -C client gen:api`）：`openapi.json` +74 行、`schema.d.ts` +26 行（新 schema `StatChangeOut`、`FlashOptionOut.changes`）。前端畫面沒改。

## 4. 快照與夾具

**`tests/skillgen/test_refactor_parity.py`（`refactor_3wr2.json`）**

- 預測：`complete`、`retier` 不變（`complete_strength`、`retier` 不走 `apply_variation`）；`flash` 只有「出題過程中試過蓄力／輕巧」而結果會被新規則改到的條目會變。
- 預測方法（暫存區 `fl1a/predict.py`）：把 `flash_derive.COST_OPS` 清空＝回到改前的通用路徑，重跑 126 條 flash 條目，**126 條雜湊全部等於夾具**（模擬正確）；同時記下每次蓄力／輕巧嘗試的類型：
  - 一定會變（54 條）：試過「蓄力打平」、「輕巧在 AP 1」或「輕巧 AP 2 但沒變弱」；
  - 可能會變（20 條）：只試過「套不上」的蓄力／輕巧（新退路可能做得出來）。
- 實際（`pytest -m slow`）：**55 條 flash 失敗，complete 0、retier 0**。54 條「一定會變」全部失敗；「可能」20 條中 1 條失敗（套不上 → 退路做出來）、19 條仍套不上而不變；沒有預測外的失敗。**一致**，只重產這 55 條（腳本逐條呼叫 `flash_snapshot`，`git diff` 55 行 +／−55 行，都在 `flash` 下）。

**其他改動的測試（行為改變，逐一說明）**

| 測試 | 原因 | 處理 |
|---|---|---|
| `tests/llm/test_flash_propose.py::test_evaluation_entry_runs_on_the_mock_and_reports` | `pick_skills` 排序第一的殘影之誓只剩「只多冷卻」的蓄力，現在一個閃現選項都沒有，兩題退回模板 → 退回率 25% 超過 20% | 只挑閃得出東西的前 3 招（`_flashable`） |
| `tests/world/test_flash_world.py`、`test_first_flash.py`、`test_generated_content.py`、`test_replay.py::test_replay_with_growth`；`tests/api/test_opening_flash.py`（`test_pr2a_range_practice` 借用它）、`test_world_pregen.py`、`test_world_pregen_schedule.py::test_press_uses_pregen_and_replay_reads_log` | 測試主角（`build_support`）的第一招戰歌同上，現在沒有合法變化 | 改閃同一個主角身上的寒鎖 `skill_frost_shackle`（斷言不動） |
| `tests/roguelite/test_retier.py::test_a_stale_history_flashes_from_the_saved_definition` | 斷言「每個選項的預算分數不低於存檔定義」，輕巧現在依規格一定變弱 | 輕巧選項跳過這條下限 |
| `tests/api/tuning/test_rules_budget_bs1.py` | 預算表多兩個工坊欄位 | `BUDGET_PATHS` 加兩項 |

**CLI 快照、Mock 提議快照、固定種子一輪**：見第 5 節結果。

## 5. 檢查（結束碼）

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`、`trpg content check` | 全部 0 |
| `pytest tests/skillgen tests/api tests/roguelite tests/world tests/llm -n 8` | 0（7119 passed、15 skipped） |
| slow：`test_refactor_parity.py`、`test_proposal_l8.py`、`test_proposal.py`、`test_flash_cost_fl1a.py`、`tests/cli`（含 CLI 輸出快照、`test_run_cli.py` 固定種子一輪、`test_llm_propose_cli.py`）`-m "slow or not slow"` | 0（1180 passed）。**CLI 快照、Mock 提議快照、固定種子一輪都沒變**（預測：技能清單與戰鬥不經過閃現；`run auto` 的固定種子剛好沒有選到受影響的蓄力／輕巧，斷言照過），不必重產 |
| `tests/api/test_openapi_snapshot.py` | 0 |
| 前端 `corepack pnpm -C client typecheck` | 0 |
| 前端 `corepack pnpm -C client test --run` | 0（334 檔、4319 項） |

沒跑 `scripts/check.py`、沒跑平衡量測。

## 6. 附帶發現

1. **9 招 1 階主動技現在一個閃現選項都沒有**（改前 0）：殘影之誓、血痕疾行、吹送、慈焰誓約、鏡像施法、移山之力、挑釁怒吼、戰歌、展翼——它們原本唯一的選項是「只多冷卻」的蓄力。`can_flash` 不檢查有沒有選項，所以面板顯示可以閃、按下去才得到「這招這一次沒有合法的變化（沒有扣點）」（大世界、一輪都一樣，不扣點）。
2. **輕巧只減法力時可能實付不變**：法力費用 ×0.8 四捨五入，3 → 2 實付都是 2。改後有 7 招（飛行、咒印飛彈、霜寒之觸、收割靈魂、靜電掌、燼咒、雷咒；改前 13 招）輕巧＝實付代價沒少、威力降低。`changes` 照卡片實付值，所以不列法力。
3. 蓄力後稀有度標記照舊會被 `_tuned` 重算（調查 3.4 的 22 筆），本段沒動。

## 7. 待 PM 決定

1. **輕巧「打平或變強都不行」的解讀**：本段採最嚴（沒有任何一項變強、至少一項變弱），所以輕巧不會出現一升一降；蓄力允許一升一降（規格只要求至少一項變強，調查的 38 招保留）。
2. **輕巧扣多少**：降到 `cost_power`（扣掉代價折抵的分數）不高於閃現前；原招比例已經很低時跌出 70% 前就停（扣不滿也照出）。閃現的 +40‰ 上限加成不算進輕巧。輕巧不受「閃現後不低於閃現前」的強度下限（重閃時仍不低於被換掉那一筆）。
3. **輕巧減法力但實付不變**（第 6 節第 2 點，7 招）：要不要讓 `_light_cost_drafts` 跳過實付不變的資源、改試下一項？
4. **沒有閃現選項的 9 招**（第 6 節第 1 點）：接受，或給它們別的模板；面板的 `can_flash` 要不要預先檢查有沒有選項？
5. **蓄力的狀態強度只在回合加不上去時才加**（為了符合點燃斬 5 → 6 的例子，照升階 BAL-12e 的順序）。
6. **回合上限**：原招 +2，且不超過組合器持續上限 6（原招本來就超過的不再加）；控制類狀態的回合也算「狀態回合」，由預算與驗證器擋。表面（`create_surface`）的回合、強度不在蓄力／輕巧的退路裡。
7. **退路一次只動一項**：傷害一格不夠進 70% 時同一項繼續往上；不會同時動兩項。
8. **數值工坊兩個占位**：`damage_rungs: 1`、`magnitude_step: 25`（同升階的 25‰）。
9. 數值是預算器換算的原型值，沒有跑平衡量測（規格寫不做）。

## 8. 請使用者重開伺服器檢查的重點

- `skill_budget.yaml` 改了 → 內容 digest 變，進行中的一輪會從頭開始、世界日誌標成不能重播（`hash_ruleset` 不變，舊戰鬥紀錄照樣重播）。
- 閃現點燃斬類的招：蓄力選項應該看到燃燒回合 +1；輕巧選項不會再出現「威力降低」卻什麼都沒降。
- `/api/runs/...` 的 `pending_flash.options[].changes` 有前後差異（畫面要等 FL-1b）。

## 開發 PM 裁定（2026-11-13，第八任開發 PM）

已驗收並以 --no-ff 合入 main。parity 55 條先預測（54 必變＋20 可能）再比對一致才重產，接受。全量於合併後跑。

1、2、5、6、7：照保守解讀接受，轉玩法 PM 知悉。
3（輕巧減法力 ×0.8 四捨五入後實付沒少、威力卻降的 7 招）、4（9 招一個閃現選項都沒有，面板仍顯示可閃）：轉玩法 PM 定；4 若定「面板先檢查」排前端小修。
8：數值工坊占位，交使用者調。
9：content digest 變動照 TXT-1 做法記錄。
