# Phase FIX-1 報告：本機 main 全量 93 項 pytest 失敗

> 起點：本機 main `9dacb41b`（worktree `git merge --ff-only main` 後含 `9dacb41b`）。上一次全量全綠 `88909dec`。
> 失敗來源：PM 全量 log `check_full_3.log`（93 項：parity 90、round-trip 2、CLI 1）。

## 1. 歸因總表

| 失敗類別 | 項數 | 歸因 | 證明方式 | 結果 |
|---|---|---|---|---|
| `tests/skillgen/test_refactor_parity.py`（complete 34、retier 34、flash 22） | 90 | **IP-1**（`6954b540`） | ① 失敗的技能＝`content/skills/` 填了 `icon_prop` 的 36 招扣掉 2 招敵人專用（`skill_ember_bite`、`skill_magma_breach` 不在玩家池），flash 22 項全是有 `icon_prop` 的招；② 雜湊前排除 `icon_prop`、**夾具 `fixtures/refactor_3wr2.json` 一個字都沒改**，90 項全部回到舊值（見第 2 節）；③ 另以原始測試檔＋拿掉 `icon_prop` 的內容目錄對照（第 2 節） | 全過 |
| `tests/skillgen/test_proposal_l8.py` 的 `skill_ambush_stab`、`skill_leap_slam` round-trip | 2 | **IP-1**（D3：提議管線丟掉 `icon_prop`） | 兩招都有 `icon_prop`；往返比對 `proposal_coverage.same_structure` 排除 `icon_prop` 後兩招回到 `_passed()`，其他欄位比對不變 | 全過 |
| `tests/cli/test_run_cli.py::test_run_auto_reaches_a_major_flash_a_complete_skill_and_a_reflash[2]` | 1 | **BAL-20**（`9fe34f8b`，`ai_profiles.yaml` 的 `burning: 3`） | 同一份測試在 4 種內容下跑：現行 ✗；只拿掉 `icon_prop` ✗；只拿掉 `burning: 3` ✓；兩者都拿掉 ✓ | 種子 2 → 5 |

## 2. 證明的指令與雜湊

**parity（90 項）**

- 例：`test_complete_strength_unchanged[skill_ambush_stab]` 舊值（夾具）`87be08bc32b5ac85`、全量 log 的新值 `3daef9fde4128aeb`；另一例舊 `ca669401ca9fab6c`、新 `fbfae1fe768a8f62`。排除 `icon_prop` 後算出的值等於舊值（測試以夾具舊值逐項斷言）。
- 指令：`UV_NO_SYNC=1 uv run pytest -q tests/skillgen/test_refactor_parity.py tests/skillgen/test_proposal_l8.py -m "slow or not slow" -n 8` → **928 passed**（夾具未改；git diff 中 `tests/skillgen/fixtures/` 無變動）。
- 獨立對照（不靠新的排除邏輯）：把改動前的測試檔原封不動複製成暫存測試，以 `TRPG_CONTENT_DIR=<拿掉 icon_prop 的內容副本>` 跑：90 項全回舊值（第 5 節）。
- 沒有任何一項在排除 `icon_prop` 後仍對不上舊值，所以沒有需要停下回報的項目，也**沒有重產夾具**。
- BAL-20 對 parity 無影響：parity 只跑技能強度、升階與出題，不跑 AI；現行內容（含 `burning: 3`）排除 `icon_prop` 後即全數等於舊值。

**round-trip（2 項）**：`skill_ambush_stab`（`icon_prop` 有填）、`skill_leap_slam`（有填）。`round_trip_inventory` 用 `same_structure` 比較往返結果與原技能，原技能帶 `icon_prop`、往返結果被 `drop_icon_prop` 丟掉 → 判「往返後內容不同」。排除後兩招通過；同一次執行 `test_proposal_l8.py` 全過。

**CLI（1 項）**：內容副本在暫存區 `fix1/{noburn,noicon,neither}`（`noburn` 只把 `status_values` 的 ` burning: 3,` 刪掉；`noicon` 刪掉 36 個技能檔的 `icon_prop:` 行），以 `TRPG_CONTENT_DIR` 指過去跑 `pytest tests/cli/test_run_cli.py -m slow -k reaches_a_major`：

| 內容 | 結果 |
|---|---|
| 現行 | 1 failed（種子 2：`major` 為空，沒到第 3 次閃現）、1 passed |
| 只拿掉 `icon_prop` | 1 failed、1 passed |
| 只拿掉 `burning: 3` | 2 passed |
| 兩者都拿掉 | 2 passed |

## 3. 修法與理由

1. **parity：雜湊前排除 `icon_prop`（`DISPLAY_ONLY`），不重產夾具。** 這份測試的目的寫在檔頭：「重構前後行為不變」，鎖的是規則（完整強度、升階、出題）。`icon_prop` 依 06 6.36／IP-1 D1 不進結算、預算、重播與出題，所以它出現在技能 JSON 裡不是規則改變；重產夾具會把 34 招的規則對照一起換掉，等於放寬。排除只作用在雜湊輸入，技能本身仍帶著 `icon_prop` 走完整條計算（所以若 `icon_prop` 有朝一日影響了規則，其他欄位的雜湊會變而被抓到）。flash 用巢狀排除 `{"options": {"__all__": {"skill": {"icon_prop"}}}}`。
2. **round-trip：`src/trpg/skillgen/proposal_coverage.py::same_structure` 的 skip 加 `icon_prop`**，與 IP-1 對 `tests/skillgen/test_proposal.py::_same` 的做法相同。這是比較函式（往返盤點報表 `round_trip_inventory` 也用它），不是規則程式；其他欄位一律照舊比對。這也修正了盤點報表會把 34 招誤判成「往返後內容不同」。
3. **CLI：種子 2 → 5**（照 BAL-20／第四節第 3 點的做法）。掃 1～20：同時滿足三項的是 5、7、11、16、18、19、20；選 5（原註解 MAP-1 後就列為可行的種子）。斷言不動，註解補上換種子紀錄。

## 4. 改動的檔

- `tests/skillgen/test_refactor_parity.py`：`DISPLAY_ONLY`、`OFFER_DISPLAY_ONLY`，三個 snapshot 的 `model_dump_json(exclude=…)`。
- `src/trpg/skillgen/proposal_coverage.py`：`same_structure` 排除 `icon_prop`。
- `tests/cli/test_run_cli.py`：`[2, 7]` → `[5, 7]`＋註解。
- `docs/dev/上手-內容資料與模擬.md`：第四節加第 16 點（改技能內容欄位要跑哪些 slow 測試）。

**斷言改寫**：無。沒有放寬、刪除任何斷言；夾具與 CLI 快照未重產；內容數值、規則程式未改。

## 5. 測試結果

**獨立對照（用改動前的原始測試檔與原始比較函式，不靠新排除邏輯）**

| 對照 | 現行內容 | 內容拿掉 `icon_prop`（`noicon`） | 兩者都拿掉（`neither`） |
|---|---|---|---|
| 原始 `test_refactor_parity.py`（暫存複本，跑完已刪）＋原始夾具 | 90 failed、797 passed | **887 passed** | 887 passed |
| 原始 `proposal_coverage.py`（暫時換回，跑完還原）＋`test_proposal_l8.py` | 2 failed、39 passed | **41 passed** | — |

→ 90＋2 項每一項在拿掉 `icon_prop` 後都回到舊值／通過，歸因 IP-1 成立。

**修好後**

- `tests/skillgen`＋`tests/cli`（非 slow，`-n 8`）：4146 passed、14 skipped。
- `tests/cli`（含 `test_output_snapshots.py`、`test_run_cli.py`）＋`test_refactor_parity.py`＋`test_proposal_l8.py`，`-m slow -n 8`：930 passed。
- `ruff check .`、`ruff format --check .`、`mypy`：全過。
- 沒跑完整 `scripts/check.py`（PM 跑）。

## 6. 待 PM 決定

- 無規則類待決。IP-1 與 BAL-20 的報告漏跑了這些 slow 測試；已寫進上手文件第四節第 16 點。
