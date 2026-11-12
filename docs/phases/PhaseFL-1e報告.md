# Phase FL-1e 報告：輕巧的回合每次最多 −1（06 6.34「費用方向」第 6 點末尾）

> 規格：`docs/design/06-技能.md` 6.34「費用方向」第 6 點末尾「輕巧的回合每次最多 −1（跟蓄力每次最多 +1 對稱，最少留 1）」（玩法 PM 7b6fc3789）；背景 `docs/phases/PhaseFL-1d報告.md`。開工時 main 已是 `7b6fc3789`（`merge --ff-only` 無變化）。

## 1. 改法（`src/trpg/skillgen/flash_cost.py`）

- 新常數 `LIGHT_DURATION_STEP = 1`。`_duration_step` 往下（輕巧）只給一格 `now − 1`（`repeat=False`），低於 `MIN_DURATION`（1）就沒有這一步。適用於所有 `_has_rounds` 的回合：狀態（增減益）、護盾、不死、轉移傷害、暫時給技能、只對友方的區域、區域裡巢狀的狀態。
- `light_adjusted` 的回合步驟：
  - 降 1 後合格（驗證、比例在窗內、強度下限、`light_ok`）而且已扣回（`cost_power` 不高於閃現前）→ 用它。
  - 降 1 合格但還沒扣回 → 先記著（只記第一個），**照退路規則改試下一項**；後面有扣回的就用那一項，都沒有才用第一個記著的。
  - 降 1 後比例仍高於合格區間（少付太多、扣不回）或不合格 → 這一項沒結果，試下一項；全部沒結果 → `None`，不出輕巧。**不會一路往下降**。
- 傷害、狀態強度步驟沒動（仍可多格、照舊「合格就用、停在最後一個合格的」）。調整順序、一次一項、輕巧不准任何一項變強都沒變。
- 既有退路是「同一項逐格往下、停在最後一個合格的」；「每項回合最多 −1」就是把回合那一項的候選值縮成一格，所以不會出現同一項累降。

`api/flash_changes.py`、has_options、快取都沒改。

## 2. 魂結

**轉移傷害 3 → 2**（AP 1；第一份草稿（冷卻那一版）降 1 後比例 81.5% 但沒通過強度下限或合格檢查，第二份草稿（法力 6 → 5）降 1 比例 78.5% 合格）。預算器不替轉移傷害回合計價，降 1 沒扣回，後面沒有別的項目，用這個記著的結果。差異清單仍列「轉移傷害回合」`worse`。

## 3. 掃描統計（FL-1a／1c／1d 方法：1 階主動、內容檔＋白板配方 × 三種武器 × 種子 0～7 去重 672 筆，種子 12345）

| | FL-1e 前（＝FL-1d 後） | FL-1e 後 |
|---|---|---|
| 蓄力・內容檔：套得上 | 164 | 164 |
| 　**蓄力沒變** | 0 | **0** |
| 蓄力・白板：套得上 | 611 | 611 |
| 　**蓄力沒變** | 0 | **0** |
| 輕巧・內容檔：套得上 | 122 | **120** |
| 　**輕巧沒變弱** | 0 | **0** |
| 輕巧・白板：套得上 | 512 | **440** |
| 　**輕巧沒變弱** | 0 | **0** |
| 1 階主動技沒有任何閃現選項 | 7 | **8（+展翼）** |

逐筆變動（蓄力 0 筆）：

- 內容檔 3 筆：魂結 轉移傷害 3 → 1 改成 3 → 2；**展翼、賜予羽翼 輕巧 套得上 → 不出**（原本飛行 3 → 1；AP 2 → 1，飛行 2 回合比例 143.8%，高於 100%）。
- 白板 72 筆 **套得上 → 不出**，全部是 AP 2 → 1、只能靠降狀態回合扣回的配方：venom 20、kindle（點燃斬）15、venom_mist 15、mark_target 13、mark_sweep 9。例：點燃斬（種子 0）燃燒 5 → 4 比例 142.9%，原本降到 2 才進窗。
- 其他輕巧結果逐字不變。

**仍然沒有閃現選項的招（8 招）**：殘影之誓、血痕疾行、慈焰誓約、移山之力、鏡像施法、吹送、挑釁怒吼、**展翼**（蓄力本來就不出：飛行回合已達上限）。賜予羽翼還有別的選項。

## 4. 快照與夾具（先預測再比對）

預測方法：包一層 `flash_derive.light_adjusted`，同時算 FL-1e 版與 FL-1d 版（猴子補丁回到多格回合步驟、找到就回傳），**回傳 FL-1d 版**，記下兩版不同的條目／測試（暫存區 `fl1e/predict.py`、pytest 外掛 `fl1e/fl1e_probe.py`）。

- **parity 夾具**：FL-1d 模型下 126 條 flash 條目全部等於夾具（模型正確）；預測會變 **0 條**。實際（slow）：0 失敗，夾具沒動。
- **Mock 提議**（`test_proposal_l8.py`、`test_proposal.py`）與 **CLI**（`tests/cli` 全部，含輸出快照、`test_run_cli.py`、`test_llm_propose_cli.py`）：Mock 0 項分歧 → 預測不變。CLI 有 4 項走到分歧（`test_run_cli.py` 的 `test_run_auto_ten_seeds_without_exceptions[1]`、`[7]`，`test_run_auto_without_a_start_draws_weapon_and_keywords[1]`，`test_run_auto_reaches_a_major_flash_a_complete_skill_and_a_reflash[7]`），但這幾項只檢查不變量（結束碼 0、最後一行「結果：」、有大閃現／完整技能／重閃），沒有逐字快照，預測仍通過；`test_output_snapshots.py` 0 項分歧 → 預測不變。實際（slow，含 parity、Mock、FL-1a／1c／1d／1e 全掃、`tests/cli`）：**1218 passed、0 失敗**，與預測一致，沒有重產任何快照或夾具。
- **一般測試**：預測 6 項（點燃斬輕巧 2、展翼／賜予羽翼輕巧 2、展翼「有選項」1、差異清單用展翼的 1），實際 `tests/skillgen tests/api tests/roguelite tests/world tests/llm` 失敗的正好是這 6 項。改法：
  - `test_flash_cost_fl1a.py`：`test_kindle_light_lowers_the_burn` → `test_kindle_light_is_not_offered`（`FlashError`）；`test_light_keeps_at_least_one_round` 改用魂結。
  - `test_flash_cost_fl1c.py`：`test_wing_light_shortens_the_granted_flight` → `test_wing_light_is_not_offered`；`STILL_NO_OPTIONS` 加展翼；「有選項」的例子展翼換賜予羽翼。
  - `tests/api/test_flash_changes_fl1a.py`：`test_light_lists_cheaper_cost_and_a_weaker_effect` 展翼換聚雷（AP 2 → 1、骰子變小）。

**新增測試** `tests/skillgen/test_flash_cost_fl1e.py`：常數 1；回合步驟只有一個候選值、不重複；剩 1 回合不再降；魂結 3 → 2；降 1 仍太強就不出（展翼、賜予羽翼、點燃斬）；1 階主動內容檔輕巧每個回合欄位最多少 1。

## 5. 檢查（結束碼）

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .`、`mypy`、`lint-imports`、`trpg content check` | 全部 0 |
| `pytest tests/skillgen tests/api tests/roguelite tests/world tests/llm -n 8` | 0（7160 passed、15 skipped） |
| slow：`test_refactor_parity.py`、`test_proposal_l8.py`、`test_proposal.py`、FL-1a／1c／1d／1e 全掃、`tests/cli`（`-m "slow or not slow" -n 8`） | 0（1218 passed） |
| 一場重播（`open_plain` 種子 7） | 0（91 個動作一致） |

沒跑 `scripts/check.py`、沒跑平衡量測、前端沒改沒跑。

## 6. 待 PM 決定

1. **降 1 仍太強就不出輕巧，導致 74 筆輕巧消失**（白板 72：點燃斬、venom、venom_mist、mark_target、mark_sweep；內容檔：展翼、賜予羽翼），展翼變成沒有任何閃現選項。照規格「降不到合格就不出輕巧」做。原因是 AP 2 → 1 少付的量大，單降 1 回合扣不回（比例約 143%）。若要讓它們保留輕巧，屬數值（AP −1 的折抵、回合計價）或規則（例如允許回合 −1 再加另一項），交使用者／玩法 PM。點燃斬正是閃現蓄力調查的起點招，特別提出。
2. **「降 1 合格但沒扣回」時改試下一項、都沒扣回才用第一個**：規格說「接著試下一項」，沒說都試不到時怎麼辦；採保守做法沿用 FL-1a「停在最後一個合格的」精神，回傳第一個降 1 合格的（魂結就是這種）。另一種讀法是「不出輕巧」，那魂結會不出。
3. 傷害、狀態強度的退路沒限制每次幅度（規格只說回合），照舊。
