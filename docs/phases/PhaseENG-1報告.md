# Phase ENG-1 報告｜傷害公式合一與 `unit_downed` 順序鎖定

## 結論

- S1 完成：實際結算與兩份預覽共用同一個純函式。預覽只有護陣 ×0 的情況改變，現在與實際結算一致（0，不套最低傷害）。
- S2 完成：只有 `unit_downed` 有 2 個以上觸發函式，22 個入口的順序完全一致，已用測試鎖定，沒有改順序。
- 實際結算沒有變：5 場戰鬥的紀錄與改動前逐位元相同。`LOG_FORMAT`、`WORLD_RULES_VERSION` 未動。
- **未全過的一項**：`uv run mypy` 結束碼不是 0，13 個錯誤全在 `tests/api/test_hidden_info.py`，改動前的 4d4948c8 就有同樣 13 個（見驗收第 1 條），本段沒有新增 mypy 錯誤。

## 改動內容

| 檔案 | 內容 |
|---|---|
| `src/trpg/engine/rules/combat.py` | 新增 `raw_damage_permille`、`rolled_damage_amount`（整數運算、先乘後除，護陣 ×0 的判斷在此，以 `ward` 判斷） |
| `src/trpg/engine/effects/handlers.py` | `_rolled_damage` 改呼叫上述函式 |
| `src/trpg/engine/preview.py` | `_amount_table`（普攻）與 `_damage_expectation`（技能）改呼叫上述函式，`ward` 取自模擬事件的 `ward_permille`；打物件時為 1000 |
| `tests/engine/test_damage_formula.py` | S1 的表格測試、手算固定值、hypothesis 舊寫法比對 |
| `tests/engine/test_trigger_order.py` | S2 順序鎖定 |

`effects/handlers.py` 的 `base_amount` 是另一條公式（紀錄用），不在規格範圍，未動。

## 逐條驗收

| # | 條件 | 結果 | 證據 |
|---|---|---|---|
| 1 | `ruff check` | 通過 | `All checks passed!` |
| 1 | `ruff format --check` | 通過 | 結束碼 0 |
| 1 | `uv run mypy` | **未通過（既有錯誤）** | 改動後：13 errors in 1 file（1411 個檔案）。4d4948c8 的乾淨副本（`git archive` 解開後跑同一個 mypy）：同樣 13 errors（1409 個檔案），全在 `tests/api/test_hidden_info.py`。本段新增的檔案沒有錯誤 |
| 1 | `lint-imports` | 通過 | `Contracts: 14 kept, 0 broken.` |
| 1 | 沒有新增複雜度 noqa | 通過 | diff 中沒有新增 `noqa`。測試有 1 個 `type: ignore[arg-type]`（`**row.core` 傳給 `make_state`），不是複雜度類 |
| 2 | `tests/engine`、`tests/test_architecture.py` | 通過 | 與 `tests/cli/test_output_snapshots.py` 合跑：`4271 passed`。之後只強化了 `test_damage_formula.py`，該檔與 `test_trigger_order.py` 重跑：`41 passed` |
| 2 | CLI 快照 | 未受影響 | 上述合跑包含快照測試，沒有重產 |
| 3 | 3 張以上地圖的 `battle --log-json` ＋ `replay`，且與改動前逐位元相同 | 通過 | 見下表 |

行為一致測試：

| 規格項目 | 測試 |
|---|---|
| 一般、爆擊、元素抗性、天氣、倍率、易傷、護盾、最低傷害、護陣 ×0、護陣 ×0 且有易傷，普攻與技能各一輪 | `test_preview_table_matches_engine[<row>-attack／skill]`，共 11 列 × 2。另有 `ward_half`（護陣 ×0.5）與 `status_zero_without_ward`（`status_ppm == 0` 但沒有護陣，仍套最低傷害）；爆擊在每一列都和未暴擊一起比對 |
| 公式對舊寫法逐一比對 | `test_formula_equals_legacy_engine`、`test_formula_equals_legacy_preview_when_not_warded_to_zero`、`test_raw_damage_equals_legacy`、`test_formula_hand_computed_values` |

表格測試的比對方式：對每個骰值總和實際 `resolve` 一次，用真正的 `damage_dealt`（`amount − absorbed`）算出精確期望值，與預覽的 `expected_if_hit` 以 `Fraction` 比對，並比對最小、最大值。每列的 `check` 會確認事件真的帶到該列要測的因子。

### 紀錄比對

方法：改動前先在 4d4948c8（尚未修改）跑兩次確認本身可重現，改動後再跑一次，以 `read_bytes()` 整檔比對，並各跑 `trpg battle replay`。腳本與紀錄在 `.scratch_eng1/`（未 commit）：`run_battles.py`、`compare.py`、`base/`、`after/`。

| 地圖 | 種子 | 大小（位元組） | SHA-256 前 16 碼 | 比對 | 重播 |
|---|---|---|---|---|---|
| open_plain | 101 | 5114400 | d7408cc11a8ac79c | 相同 | 通過（82 動作、299 事件） |
| frozen_lake | 202 | 5116256 | e0e804cbc598ffa0 | 相同 | 通過（72、288） |
| cliff_outpost | 303 | 5145014 | 55ea74ada8540948 | 相同 | 通過（119、398） |
| ruined_fort | 404 | 5087481 | 38efa33d521803e8 | 相同 | 通過（73、200） |
| lava_crossing | 505 | 5086634 | 3fd2d3440914d95e | 相同 | 通過（49、227） |

### 突變檢查

暫時改壞程式，確認測試會失敗（`.scratch_eng1/mutate.py`，改完還原原始位元組）：

| 突變 | 結果 |
|---|---|
| 普攻預覽忽略 ward | 抓到（`ward_zero`、`ward_zero_vulnerable` 的 attack） |
| 技能預覽忽略 ward | 抓到（同上的 skill） |
| 公式改用 `status_ppm` 判斷 ×0 | 抓到（`status_zero_without_ward` 與 hypothesis） |
| 基底提早捨成整數點 | 抓到（hypothesis 與手算值） |
| 元素修正提早捨去 | 抓到（hypothesis 與手算值） |

第一版的 hypothesis 範圍太寬，後兩個突變沒抓到：乘積多半落在最低傷害，而表格測試的預覽與引擎共用公式，本來就抓不到公式本身寫錯。因此改用實際可能的範圍，並加上手算固定值。另外試過「只把最後的 PPM 提早除」的突變，它的差異機率約 1e-8，實務上等價，未列入。

## S2：量到的順序

在全新直譯器中從以下 22 個入口匯入後比對（改動前後各量一次），結果只有一種：

`trpg.engine`、`.battle`、`.preview`、`.runner`、`.effects`、`.lifecycle`、`.bombs`、`.delayed`、`.death_surfaces`、`.triggers`、`.interactions`、`.shield_riders`、`.summons.core`（以上為 `trpg.engine` 底下）、`trpg.api`、`trpg.api.app`、`trpg.cli`、`trpg.cli.main`、`trpg.sim`、`trpg.sim.batch`、`trpg.roguelite`、`trpg.server`、`trpg.world`。

共 18 個事件、20 個觸發函式，有 2 個以上的只有：

| 事件 | 順序 |
|---|---|
| `unit_downed` | `trpg.engine.bombs._bomb_on_downed` → `trpg.engine.death_surfaces._surface_on_downed` → `trpg.engine.delayed._cancel_on_downed` |

只有 1 個觸發函式的事件：`bomb_exploded`、`check_rolled`、`collided`、`damage_dealt`、`element_touched`、`entered_deadly_terrain`、`object_damaged`、`object_destroyed`、`object_exploded`、`object_toppled`、`shield_absorbed`、`shield_ended`、`status_applied`、`surface_entered`、`unit_fell`、`unit_moved`、`wall_toppled`。

`test_trigger_order.py` 為節省時間只固定 8 個入口（`trpg.engine`、`trpg.api.app`、`trpg.cli.main`、`trpg.sim.batch`、3 個葉模組、`trpg.engine.triggers`）；日後某個事件變成 2 個以上觸發函式時，測試會失敗，要求把順序列進 `EXPECTED`。

## 複雜度 noqa

沒有新增。

## 過程備註

- worktree 建立時停在 9bc45ad3，比派工指定的 4d4948c8 落後 4 個 commit（規格就在其中），已在自己的分支 `git merge --ff-only 4d4948c8` 後才開始。
- 開發中一次突變腳本失敗時，連帶的 `git checkout` 把尚未 commit 的 `preview.py` 修改還原，已重做；上面的驗收都在重做之後跑，最終 diff 已逐行看過。

## 待 PM 決定

1. `tests/api/test_hidden_info.py` 有 13 個 mypy 錯誤（4d4948c8 就有，最後改動是 11-07 的 HID-1），不在本段可改範圍。需要另排修正，否則 `uv run mypy` 的閘門一直是紅的。
2. 引擎的 `damage_object`（`effects/world.py`）是第 4 份傷害算式。與預覽打物件時的算法換算後等價，規格只列 3 份，所以沒合併；要不要合併由 PM 決定。
3. 預覽的最低傷害用 `core.min_damage_on_hit`，實際結算用 `effect.min_damage`。目前 `cause: attack` 的來源都帶 core 的值，所以一致；照規格保留原樣。若日後有技能自訂 `min_damage`，預覽會再次不一致。
