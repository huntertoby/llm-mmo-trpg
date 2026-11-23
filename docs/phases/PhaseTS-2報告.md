# 階段 TS-2 報告：試用 testmon

基準：main `44611fc9a`，中途合併 main 兩次（`0463be2b9` → `f3487fc54`、`89f5d5e02` → `8de977310`）。分支 `worktree-agent-a8c1ea6993771402c`，沒有 push。規格：`docs/phases/PhaseTS-2計畫.md`。

## 結果（一兩句）

`check.py --testmon` 做好了，也有測試。9 次有效對照裡有 **2 次漏抓，共 5 個測試**，所以達不到「沒漏才正式用」。一般 testmon 平均只省 0.6% 的時間。`--testmon-nocollect` 平均省約 60%，但資料要另外重建，重建一次比全跑慢約 2.5 倍，而且一樣會漏。**建議不要正式用**，第 11 條不用改（理由見第 5 節）。

## 交付項目
| 項目 | 狀態 | commit |
|---|---|---|
| 1 安裝 `pytest-testmon==2.3.0`、`coverage==7.17.1`（開發相依），`.testmondata*` 加進 `.gitignore` | 完成；`uv.lock` 只多這兩個套件 | `662e3b43f` |
| 2 `check.py --testmon` 試用模式，加上 `scripts/testmon_select.py` 和測試 | 完成 | `e96f2e9ad` |
| 3 試跑對照：9 次有效＋1 次無效；7 次故意弄壞、3 次真實改動，其中 8 次也量了 nocollect | 完成 | 不 commit |
| 4 `docs/dev/上手-測試.md` 一之三節 | 完成 | `4a1e281db` |
| 報告 | 本檔（期中版是 `74e540517`、`92073098b`） | 本次 |

## 1. 試用模式的做法

- **什麼時候用**：`--testmon` 只在分流結果是「只跑後端」、而且後端改動都是 `.py`（夾 `.md` 可以）時才用。
  - 前端、全跑（包括 `--all`、`--full`），或後端有非 `.py` 的改動時，不用 testmon。開頭那一行會寫原因，戳記照 TS-1。
  - 非 `.py` 那條是規格外的保守做法，開發 PM 已同意。
- **怎麼選測試**：pytest 步驟加 `--testmon-forceselect`。`addopts` 裡有 `-m 'not slow and not llm'`，testmon 2.3.0 看到 `-m` 會自動關掉選測試，只有 forceselect 會同時照 testmon 和 `-m` 篩。
- **開頭那一行的數字**：由 `scripts/testmon_select.py` 算。它在同一個行程裡跑一次 `pytest --collect-only -n 0 --testmon-forceselect --testmon-nocollect`，只收集、不寫資料，約 10 秒。
  - 選了＝這次會跑的測試數。
  - 略過＝testmon 有執行紀錄、這次沒選到的數量。開發 PM 已同意這個算法。
  - 收集失敗時，退回不用 testmon。
- **戳記**：用 testmon 的跑法通過時，兩個位置都不寫戳記。
- **和 xdist、看門狗、`loadgroup` 搭不搭得起來**：搭得起來。
  - testmon 2.3.0 支援 xdist：各 worker 把覆蓋資料送回主行程，由主行程寫進 DB。
  - `SafeLoadGroupScheduling` 和看門狗照常運作，所以沒有退成不平行，一律 `-n 12`。
- **實跑的開頭那一行**（第 1 次）：`分流：只跑後端（基準 e96f2e9ad2（HEAD 的 merge-base），改動 1 個檔）。…這次用 testmon（試用）：選了 1443 個測試、略過 17260 個；不寫通過戳記。`
- **測試**：`tests/infra/test_check_testmon.py`，共 17 個，涵蓋：
  - 只有後端範圍才啟用；前端、全跑、`--all`、`--full` 都不啟用；後端有非 `.py` 改動也不啟用。
  - 預先收集失敗時退回不用 testmon。
  - 通過和失敗都不寫戳記。
  - 開頭那一行的內容，以及預先收集輸出的解析。
- `main` 的分支數超過 PLR0912，所以拆出 `_plan_for`、`testmon_setup`，沒有加 noqa。

## 2. 試跑對照表

- 「全部」是全跑實際跑到的測試數（passed＋failed）。
- 「一般」＝`--testmon-forceselect`，邊跑邊記覆蓋、更新資料。
- 「nocollect」＝再加 `--testmon-nocollect`，只照資料選測試，不記覆蓋、不更新資料。
- 每次都從同一份基準資料開始，三種跑法跑完都把資料還原。
- 耗時是看門狗整個指令的時間（含收集）。開頭那一行還要再加約 10 秒的預先收集。

| # | 種類 | 改動 | 選到／全部 | 一般 | nocollect | 全跑 | 一般失敗 | nocollect 失敗 | 全跑失敗 | 漏抓（一般／nocollect） |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 弄壞：引擎結算 | `engine/crit_damage.py` 基礎暴擊倍率加 100 | 1443／18694（7.7%） | 655 秒 | 沒量 | 667 秒 | 38（另有 2 個 wish，見下） | — | 38 | 0／— |
| 2 | 弄壞：規則 | `engine/rules/movement.py` 起身花費改成無條件捨去 | 164／18706（0.9%） | 356 秒 | 115 秒 | 780 秒 | 1（另有 2 個 wish） | 1 | 1 | 0／0 |
| 3a | 弄壞：內容載入（**無效**） | `content/races.py` 預設髮型一律 `none`，整個內容載入失敗 | 514 | 889 秒 | 76 秒 | 7620 秒，卡住判失敗 | 492 | 499 | 無結果 | 無法比 |
| 3b | 弄壞：內容載入 | `content/loader.py` 驗證錯誤訊息開頭「驗證失敗」改成「驗證錯誤」 | 62／18715（0.3%） | 24 秒 | 25 秒 | 721 秒 | 0 | 0 | 0 | 0／0（沒有測試看這幾個字） |
| 3c | 弄壞：內容載入 | `content/loader.py` 「找不到檔案」改成「沒有檔案」 | 1080／18715（5.8%） | 533 秒 | 311 秒 | 696 秒 | 1 | 1 | 1 | 0／0 |
| 4 | 弄壞：skillgen | `skillgen/budget.py` 骰子平均少加 1 | 2827／18712（15.1%） | 1212 秒 | 474 秒 | 650 秒 | 252 | 252 | 255 | **3／3** |
| 5 | 弄壞：API | `api/player_text.py` 清理後的文字尾巴多一個空白 | 12／18715（0.06%） | 126 秒 | 30 秒 | 651 秒 | 4 | 4 | 4 | 0／0 |
| 6 | 真實改動 | `343b165da` 觸發篩選欄位（內容 schema，6 檔） | 11199／18423（60.8%） | 1781 秒 | 682 秒 | 855 秒 | 0（另有 2 個 wish） | 0 | 0 | 0／0 |
| 7 | 真實改動 | `4c4da4303` 引擎結算觸發篩選（6 檔） | 5898／18443（32.0%） | 700 秒 | 289 秒 | 600 秒 | 0（另有 2 個 wish） | 0 | 0 | 0／0 |
| 8 | 真實改動 | `ee6b45d51` 種族被動帶數字（4 檔） | 6506／18665（34.9%） | 797 秒 | 320 秒 | 603 秒 | 0 | 0 | 2 | **2／2** |

**合計**（有效 9 次，3a 不算）：

| | 一般 testmon | nocollect（8 次，不含 #1） |
|---|---|---|
| 漏抓 | 2 次，共 5 個測試 | 2 次，共 5 個測試 |
| 平均選到比例 | 17.5% | 同左（選法一樣） |
| 合計耗時對全跑 | 6184 秒對 6223 秒，平均每次省 4 秒（0.6%） | 2246 秒對 5556 秒，平均每次省 414 秒（60%） |
| 比全跑還慢的次數 | 4 次（#4、#6、#7、#8） | 0 次 |

### 漏抓的 5 個

- **#4（3 個）**：
  - 漏掉的是 `tests/skillgen/test_proposal_l8.py` 的三個參數化測試：
    - `test_followup_skills_round_trip[skill_armor_break_combo]`
    - `test_followup_skills_round_trip[skill_death_spiral]`
    - `test_reaction_skills_round_trip[skill_reflex_ward]`
  - 原因：這個測試檔的 `_passed()` 是 `@functools.cache`。在同一個 worker 裡，只有第一個呼叫它的測試真的執行了 `round_trip_inventory`，testmon 只把 `budget.py` 記在那一個測試名下。之後的測試直接拿快取，testmon 認為它們跟 `budget.py` 無關。
  - **凡是測試檔、輔助模組或 session fixture 有快取的，都會漏。**本專案很多測試都是這樣寫的，例如 `tests/engine/helpers.library()`。
- **#8（2 個）**：
  - 漏掉的是 `tests/test_x10_fields.py::test_fields_cover_every_numeric_content_field` 和 `tests/test_x10_rescale.py::test_real_content_dry_run`。
  - 這是歷史上真的漏過的回歸：`ee6b45d51` 讓種族被動多了暴擊數值欄位，但 x10 清單沒列。全跑抓到了，testmon 沒選到。
  - 原因：這兩個測試讀的是 pydantic 模型的欄位定義和 YAML，沒有執行 `races.py` 裡的函式。類別本體在收集階段匯入時就跑完了，不算進任何測試的覆蓋。
  - **只看 schema 或欄位的測試，改模型時會漏。**

### 其他發現

- **2 個 wish 測試**：在第一次合併 main 以前（#1、#2，以及 #6～#8 用的舊版程式），`test_text_wish_wait_then_act`、`test_text_wish_is_logged_and_replayed_without_llm` 在「一般」跑法底下每次都失敗，因為記覆蓋把背景執行緒拖慢，超過 10 秒的等待。
  - 照裁定，這 2 個當已知失敗，不算漏抓。
  - CR-1b 改了等法之後（合併 `89f5d5e02` 起的 #3b～#5），它們在 testmon 底下也會過。
  - nocollect 不記覆蓋，這 2 個一直都會過。
- **#3a 無效**：內容載入整個壞掉，幾千個測試同時失敗。xdist 的 worker 一直掛掉、補開，最後整組卡住，連 `test_check_split` 都卡 1829 秒，看門狗兩次都判卡住（124），全跑沒有失敗清單。所以改用 #3b、#3c 重做。這也表示：大量失敗時，全跑本身也可能卡死，那是 TS-1 查到一半的 xdist 收尾問題。
- **#6～#8 在舊版的上一版建資料時**，`test_summon_f2.py::test_deepen_raises_max_hp_and_adds_the_trait`、`test_summon_ai.py::test_summon_gains_are_dpr_times_rounds_minus_distance` 在一般跑法失敗。這不在比對範圍裡（是建資料那一次，不是對照），可能也是記覆蓋造成的，我沒有追。

## 3. 建資料的成本

| 跑法 | 測試數 | 耗時 |
|---|---|---|
| 新 worktree 第一次建資料（全部，記覆蓋） | 18677 | 1804 秒；舊版 rw 那次 1586 秒 |
| 合併 main 後同步（49 檔改動） | 選 6050 | 721 秒 |
| 合併 main 後同步（CR-1b，11 個後端檔） | 選 5778 | 835 秒 |
| 真實改動前，在上一版同步（舊版 rw，跨幾十個 commit） | 選 11193、5898 | 1842 秒、1468 秒 |
| 平常的全跑（不用 testmon） | 約 18700 | 600～855 秒 |

- 資料比對的是「上一次 testmon 記覆蓋時的程式」，不是 `origin/main`。
- 每個新的 agent worktree 都沒有資料，第一次要花約 1800 秒建，等於 2～3 次全跑。合併 main 後的同步也常選到 30%～60%，再加上記覆蓋的負擔，往往比全跑還久。

## 4. 哪種用法真的省時間、多久要重建資料

- **一般 testmon（記覆蓋）**：不省。
  - 記覆蓋讓選到的測試慢 2～3 倍。改到引擎、內容 schema 這類核心時會選到 15%～60%，都是長的整合測試，常常比全跑還慢。
  - 只有改動很局部時才省，例如 #2、#3b、#5（選到 1% 以下），一次省 400～700 秒。
- **nocollect（不記覆蓋）**：每次都比全跑快，平均省 60%。條件：
  - 要有一份夠新的資料。nocollect 不更新資料，同一個 worktree 每改一次，比對的基準都還是建資料那時的程式，改得越多選得越多，最後接近全跑。
  - 實務上，**每次合併 main 或開新 worktree 都要重建一次**（用一般跑法同步，700～1800 秒），之後同一段開發中可以一直用 nocollect。
  - 一段開發如果 nocollect 跑不到 3 次以上，重建的成本就吃掉省下的時間。本專案的 agent 每段幾乎都開新 worktree，正好落在不划算的那一邊。
- **兩種都有同樣的漏抓**（快取、只看 schema 的測試），選法完全一樣。所以 testmon 只能當開發中的快速回饋，不能取代交件前的 `--all`，也不能取代 push hook。

## 5. 建議：不要正式用；CLAUDE.md 第 11 條不用改

理由：

1. **會漏抓**：9 次裡有 2 次漏、共 5 個，其中 1 次是歷史上真的發生過的回歸。原因在本專案測試的寫法（`@cache` 的共用函式庫、只讀 schema 的檢查），不是偶發，改不了 testmon 這一邊。使用者的條件是「先試跑對照沒漏才正式用」，這個條件沒有達到。
2. **一般用法不省時間**（平均 0.6%，4 次比全跑慢）。
3. **nocollect 雖然快**，但每個新 worktree、每次合併後都要重建資料，重建一次比全跑慢 2～3 倍，本專案的工作方式抵銷了它的好處。
4. TS-1 的資料夾分流已經能把只動前端的情況縮到約 2.5 分鐘；後端全跑 600～850 秒，對交件前跑一次來說還可以接受。

**`--testmon` 留不留**（待 PM 決定 1）：
- 程式不影響預設行為，不加參數時跟以前完全一樣；交件前、push hook 也都不看它。
- 可以留給想在同一個 worktree 反覆改後端的人當「先看一眼」，並在 `docs/dev/上手-測試.md` 寫明會漏、要搭配 nocollect 才快。
- 也可以整個移除，連兩個套件一起拿掉。
- 我保守地先留著：文件寫明試用中、不能取代 `--all`。

**如果之後仍想用**，比較可行的方向（都在規格外，沒做）：
- 在 main 上定期建一份共用資料，用 `TESTMON_DATAFILE` 指過去，讓新 worktree 不用從零建。要處理 SQLite 多個行程同時寫的問題。
- 把 `@cache` 的測試輔助函式改成不快取，或標記為一定要跑。這要改很多測試，違反「不改其他測試」。

## 驗收條件
| 條件 | 結果 | 證據 |
|---|---|---|
| 試用模式的測試：後端才啟用、前端與全跑不啟用、不寫戳記、開頭那一行 | 通過（17 passed；連同 TS-1 的 42 個共 59 passed） | `tests/infra/test_check_testmon.py` |
| 對照表至少 8 列 | 通過：10 列（9 次有效＋1 次無效），其中故意弄壞 7 列、真實改動 3 列 | 第 2 節 |
| 結論與建議：漏抓、省多少、要不要用、第 11 條改寫全文 | 通過：建議不用，第 11 條不改，理由見第 5 節 | 第 4、5 節 |
| 靜態檢查 | 通過 | 下表 |
| 全部 commit 之後 `check.py --all` | 見下表 | 下表 |
| 每項一個 commit | 第 1、2、4 項各一個；第 3 項依規格不 commit | 交付項目 |

## 檢查指令結果
| 指令 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0 |
| `uv run mypy` | 0 |
| `uv run lint-imports` | 0 |
| `run_pytest.py -q tests/infra/test_check_testmon.py tests/infra/test_check_split.py -n 4` | 0（59 passed） |
| `TRPG_CHECK_BASE=HEAD check.py --testmon`（#1 的暫時改動） | 1（預期：暫時改動弄壞 38 個） |
| `uv run python scripts/check.py --all`（全部 commit 之後） | 交件前補上 |

## 待 PM 決定
1. `--testmon` 和兩個套件要留著當開發中的選用工具，還是移除（第 5 節；我先留著）。
2. 測試輔助函式的 `@cache`（例如 `tests/engine/helpers.library()`、`test_proposal_l8._passed()`）是 testmon 漏抓的主因。如果之後還要用 testmon，或想用其他「只跑受影響測試」的工具，要另開一段改寫這些測試。
3. #3a 顯示內容大量壞掉時，全跑也會卡死（xdist 收尾）。這跟 TS-1 待查的 crash_case 卡住可能是同一個原因，可以附進那條待辦。

（先前的 5 件已由開發 PM 裁定：非 `.py` 不用 testmon、略過數的算法、wish 測試由 CR-1b 修、續跑、加試 nocollect。）
