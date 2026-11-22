# 階段 TS-2 報告：試用 testmon（期中，對照未做完）

基準：main `44611fc9a`。分支 `worktree-agent-a8c1ea6993771402c`，沒有 push。規格：`docs/phases/PhaseTS-2計畫.md`。

## 結果（一兩句）

testmon 已安裝，`check.py --testmon` 做好、有測試。試跑對照只做了 1 次（故意弄壞引擎結算）：沒有漏抓，但**沒有省時間**（選 1443 個跑 655 秒，全跑 18694 個 667 秒），而且有 2 個測試只在 testmon 底下固定失敗。對照依開發 PM 指示暫停在空檔，這份是期中報告，**還沒達到驗收的 8 次，也還沒跑交件前的 `--all`**。

## 交付項目
| 項目 | 狀態 | commit |
|---|---|---|
| 1 安裝 `pytest-testmon==2.3.0`、`coverage==7.17.1`（開發相依）、`.testmondata*` 進 `.gitignore` | 完成；`uv.lock` 只多這兩個套件 | `662e3b43f` |
| 2 `check.py --testmon` 試用模式＋`scripts/testmon_select.py`＋測試 | 完成 | `e96f2e9ad` |
| 3 試跑對照（至少 8 次，5 次故意弄壞、3 次真實改動） | **未完成：1／8**（暫停中） | 不 commit |
| 4 `docs/dev/上手-測試.md` 一之三節 | 完成 | `4a1e281db` |
| 報告 | 本檔（期中） | 本次 |

## 1. 試用模式的做法

- `--testmon` 只在分流結果是「只跑後端」、而且後端改動都是 `.py`（夾 `.md` 可以）時才用。前端、全跑（含 `--all`、`--full`）、或後端有非 `.py` 的改動（測試快照、JSON 等，testmon 追不到）時不用，開頭那一行寫原因，戳記照 TS-1。
- 用的時候 pytest 步驟加 `--testmon-forceselect`。原因：`addopts` 有 `-m 'not slow and not llm'`，testmon 2.3.0 看到 `-m` 會自動關掉「選測試」，只有 forceselect 會同時照 testmon 和 `-m` 篩。
- 開頭那一行的數字：`scripts/testmon_select.py` 在同一個行程裡跑 `pytest --collect-only -n 0 --testmon-forceselect --testmon-nocollect`，收集完時記下選到的測試數，以及 testmon 有執行紀錄（duration 不是空的）但沒選到的數量。約 10 秒。收集失敗就退回不用 testmon。
- 用 testmon 的跑法通過時不寫任何戳記（兩個位置都不寫）。
- 和 xdist、看門狗、`loadgroup` 搭得起來：testmon 2.3.0 支援 xdist（主行程收各 worker 的覆蓋資料寫 DB），我們的 `SafeLoadGroupScheduling` 和看門狗照常運作，`-n 12` 全程沒有 worker 掛掉。所以沒有退成不平行。
- 實跑開頭那一行（第 1 次對照，`TRPG_CHECK_BASE=HEAD`）：`分流：只跑後端（…改動 1 個檔）。…這次用 testmon（試用）：選了 1443 個測試、略過 17260 個；不寫通過戳記。`
- 測試：`tests/infra/test_check_testmon.py`，17 個：後端才啟用、前端／全跑／`--all`／`--full` 不啟用、非 `.py` 改動不啟用、預先收集失敗時退回、通過與失敗都不寫戳記、開頭那一行的內容、預先收集輸出的解析。`main` 因分支數超過 PLR0912，拆出 `_plan_for`、`testmon_setup`，沒有加 noqa。

## 2. 耗時與發現

| 跑法 | 測試數 | 耗時 |
|---|---|---|
| 第一次建 testmon 資料（全部、`-n 12`、記覆蓋） | 18677 | 1804 秒（平常全跑約 600～1000 秒） |
| 沒改動時預先收集 | 選 19 | 10.8 秒 |

- **記覆蓋很慢**：選到的測試在 testmon 底下約慢 2～3 倍（例如 `test_season_boss_api.py::test_first_kill_records_replayable_log` 145 秒）。
- **2 個測試在 testmon 底下固定失敗**，不用 testmon 單獨跑會過（2 passed，11 秒）：
  - `tests/api/test_wish_api_wp2.py::test_text_wish_wait_then_act`（回 `timeout` 不是 `ready`）
  - `tests/api/test_wish_pregen.py::test_text_wish_is_logged_and_replayed_without_llm`（`WorldActionError`：池子沒聽懂願望）
  - 判斷：背景執行緒（`ThreadPoolExecutor`）的 Mock 生成被覆蓋追蹤拖慢，超過 10 秒的等待。testmon 會一直重選失敗過的測試，所以只要有資料，這兩個每次都會被選到、每次都失敗，`--testmon` 的結束碼永遠是 1。

## 3. 試跑對照表（有效 2／8，暫停中）

| # | 種類 | 改動 | 選到／全部 | 選測試耗時 | 全跑耗時 | 選測試失敗 | 全跑失敗 | 漏抓 |
|---|---|---|---|---|---|---|---|---|
| 1 | 故意弄壞：引擎結算 | `src/trpg/engine/crit_damage.py` 基礎暴擊倍率加 100 | 1443／18694（7.7%） | 655 秒 | 667 秒 | 40（38＋上面 2 個 testmon 才有的） | 38 | 0 |
| 2 | 故意弄壞：規則 | `src/trpg/engine/rules/movement.py` 起身花費改成無條件捨去 | 164／18714（0.9%） | 一般 356 秒；nocollect 115 秒 | 780 秒 | 一般 3（1＋2 個 wish）；nocollect 1 | 1 | 一般 0；nocollect 0 |
| 3 | 故意弄壞：內容載入（無效，要重做） | `src/trpg/content/races.py` 預設髮型一律 `none`，整個內容載入失敗 | 514／18714（預先收集結束碼 2） | 一般 889 秒（看門狗卡住重跑一次）；nocollect 76 秒 | 7620 秒，卡住兩次判失敗（124），沒有失敗清單 | 一般 492；nocollect 499 | 無法比 | 無法比 |

- 第 2 次之前先合併 main `0463be2b9`（合併後是 `f3487fc54`），用 testmon 重建資料：選了 6050 個，跑 721 秒（只有 2 個 wish 失敗）。第 2 次起用這份資料當基準。
- 依開發 PM 裁定，2 個 wish 測試當已知失敗，不算漏抓，也不算進結束碼判斷。nocollect 不記覆蓋，這 2 個在 nocollect 底下會過。
- 第 3 次弄壞得太大：內容載入失敗，幾千個測試同時失敗，xdist 的 worker 一直掛掉、補開，最後整組卡住（stuck.txt 裡連 `test_check_split` 都卡 1829 秒），全跑沒有結果。這次對照無效，續跑時要改用影響小的寫法重做，預定改 `src/trpg/content/loader.py` 的驗證錯誤訊息開頭。

- 選到的 1443 個多半是長的整合測試（跑整場戰鬥、重播、模擬），加上覆蓋追蹤，CPU 總時數 6164 秒，和全跑的 6646 秒差不多。
- 還沒做：故意弄壞的規則（`engine/rules/movement.py`）、內容載入、skillgen（`skillgen/budget.py`）、API 四次；真實改動三次（已挑 `343b165da`、`4c4da4303`、`ee6b45d51`，暫時 worktree 已開在 scratchpad 的 `rw/`，建在 `343b165da` 的上一版，已裝好兩個套件）。
- 每次的 log 在 scratchpad `trials/<名稱>/`（`summary.txt`、`selected.log`、`full.log`、`missed.txt`）。

## 4. 目前的結論與建議（期中）

- 漏抓：1 次對照 0 件。次數不夠，不能下結論。
- 省時間：這 1 次沒有省（-2%）。改到引擎核心時幾乎一定選到長的整合測試，覆蓋追蹤的額外成本把選測試省下的抵掉。
- 目前建議：**先不要正式用**。至少要先處理上面 2 個固定失敗的測試，並把剩下 7 次對照做完，看改動在邊緣模組（API、skillgen、內容載入）時能不能省。CLAUDE.md 第 11 條的改寫全文等對照做完再提。
- 可再試的方向（規格外，沒做）：選測試時加 `--testmon-nocollect`（不記覆蓋，速度回到平常，但資料不會更新，要定期全跑重建）。

## 驗收條件
| 條件 | 結果 | 證據 |
|---|---|---|
| 試用模式的測試（後端才啟用、前端與全跑不啟用、不寫戳記、開頭那一行） | 通過，17 passed（與 TS-1 的 42 個一起 59 passed） | `tests/infra/test_check_testmon.py` |
| 對照表至少 8 列 | **未達成：1 列**（暫停中） | 第 3 節 |
| 結論與建議、第 11 條改寫全文 | 期中結論已寫；改寫全文未寫 | 第 4 節 |
| 靜態檢查 | 通過 | 下表 |
| 全量 `check.py --all` | **未跑**（暫停中） | — |
| 每項一個 commit | 第 1、2、4 項各一個；第 3 項不 commit | 交付項目 |

## 檢查指令結果
| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0 |
| `run_pytest.py -q tests/infra/test_check_testmon.py tests/infra/test_check_split.py -n 4` | 0（59 passed） |
| `TRPG_CHECK_BASE=HEAD check.py --testmon`（第 1 次對照的暫時改動） | 1（預期：暫時改動弄壞 38 個，加上 testmon 才有的 2 個） |
| `check.py --all` | 未跑 |

## 待 PM 決定
1. 後端改動有非 `.py` 檔時不用 testmon（規格沒寫，我採保守做法）。
2. 「略過幾個」的定義：testmon 有執行紀錄、這次沒選到的測試數（不含從沒執行過的 slow 佔位紀錄）。
3. 2 個測試在 testmon 底下固定失敗（第 2 節）。要改測試的等待時間、標記讓 testmon 排除，還是接受？規格不准改其他測試，所以我沒改。
4. 剩下 7 次對照和交件前的 `--all` 何時續跑；暫時 worktree `rw/` 還在 scratchpad，續跑時會用，結案時要用 `git worktree remove` 清掉。
5. 要不要加試 `--testmon-nocollect` 的跑法（第 4 節）。
