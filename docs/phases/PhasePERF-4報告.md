# Phase PERF-4 報告｜mypy 修正與 pytest 省時

環境：Windows 11、Git Bash、`uv sync --frozen --offline`。依規格沒有跑全量 `scripts/check.py`，也沒有 push 或 merge。

分支基底：worktree 實際從 `9bc45ad3` 分出，不是派工時說的 `4d4948c8`。兩者只差 4 個 docs commit，不影響程式；規格用 `git show 4d4948c8:docs/phases/PhasePERF-4計畫.md` 讀取。

## Commit

| Commit | 項目 |
|---|---|
| `36fe8846` | M1 mypy |
| `4babd3a4` | R2 YAML C 解析器 |
| `c7eea8f5` | R1 CLI 測試快取內容庫 |
| `6014fedc` | R3 記憶化 `build_subset_models` |
| `e6642f07` | R4 `test_demo_balance` 同一 xdist group |
| `b823d400` | R5 `test_owner_guard` 降 scrypt 成本 |

## 驗收條件

| 條件 | 結果 | 證據 |
|---|---|---|
| `uv run mypy` 0 錯誤 | 通過 | `Success: no issues found in 1413 source files`（改前 13 個錯誤） |
| `ruff check` | 通過 | `All checks passed!` |
| `ruff format --check` | 通過 | `2230 files already formatted` |
| `lint-imports` | 通過 | `Contracts: 14 kept, 0 broken.` |
| 沒有新增 `type: ignore`、複雜度 noqa | 通過 | `git diff 9bc45ad3 HEAD` 的新增行搜尋 `type: ignore`、`noqa`：0 筆 |
| 相關測試 | 通過 | `pytest -q -n 8 tests/cli tests/content tests/skillgen tests/llm tests/api/test_hidden_info.py tests/api/test_owner_guard.py tests/server/test_accounts.py tests/engine/test_demo_balance.py tests/test_architecture.py`：7424 passed, 15 skipped，exit 0（skip 都是既有的條件式 skip） |
| `test_demo_balance` 的 slow 案例 | 通過 | `pytest -n 8 -m slow -v tests/engine/test_demo_balance.py`：4 xpassed，exit 0 |
| `trpg battle --log-json` ＋ `trpg battle replay` | 通過 | `--map oil_depot --seed 42`：`重播驗證通過：58 個動作、287 個事件，最終狀態一致` |
| 內容 digest 前後相同 | 通過 | 見下表 |
| 改前改後 wall 時間對照 | 已附 | 見「對照時間」 |

### 內容 digest

指令：`load_library()` 後印出 `trpg.roguelite.save.ruleset_hash(lib)` 與 `trpg.engine.ruleset_hash.hash_ruleset(lib.ruleset)`。兩者都由解析結果計算，所以會反映解析器差異。

| 雜湊 | 改前（SafeLoader） | 改後（CSafeLoader） |
|---|---|---|
| `ruleset_hash(library)` | `4c608a38a4a13f9ff814375af712a98a33d22d80710dd0620fd780caffdbf9c6` | 相同 |
| `hash_ruleset(ruleset)` | `6c12472baf20bd735a8d895896d6128688695aa8c027c4e079575e2edd978d1c` | 相同 |

## 對照時間

做法：改前的程式用 `git archive 9bc45ad3` 匯出到暫存資料夾，兩邊用同一個 `.venv`、`pytest -q -n 8`，各先暖機一次（不計），再交替跑各 2 次。

| 對象 | 改前 #1 | 改後 #1 | 改前 #2 | 改後 #2 |
|---|---|---|---|---|
| `tests/cli/test_output_snapshots.py` | 7.4 秒 | 7.3 秒 | 7.0 秒 | 7.2 秒 |
| `tests/content`（改前 2752 項，改後 2759 項） | 52.6 秒 | 35.5 秒 | 53.5 秒 | 45.8 秒 |

- `tests/content`：平均 53.0 秒降到 40.6 秒，約快 23%；改後還多跑了 7 個新測試。兩次改後差 10 秒，同時有其他 agent 在跑，數字有噪音。
- `tests/cli/test_output_snapshots.py`：**沒有可量到的改善**（差距在噪音內）。
- 捨棄的兩批量測：第一批改前的樹少了 `client/src`、`scripts/`，`tests/content` 有 4 個因此失敗；第二批設了 `PYTHONDONTWRITEBYTECODE`，改前每次都重新編譯，對改後有利。兩批都不採用。
- 沒有量：`tests/cli` 整個目錄、R3、R4、R5 各自省下的時間（規格只要求上面兩項）。

## 各項做法

- **M1**：`_concealed` 的參數改標 `UnitId`；`**base` 改成具名引數的 helper `_status_on_u2`。斷言沒有改。
- **R1**：`tests/cli/conftest.py` 的 autouse fixture 換掉 `trpg.cli.main.load_checked_library`。只有 `content_dir is None` 且環境變數裡沒有 `TRPG_CONTENT_DIR` 才走快取。測試：`tests/cli/test_library_cache.py`（4 個案例，含帶 `content_dir`、環境變數有值與空字串）。
  - 內容庫是否被改：`ContentLibrary` 是 frozen dataclass，但裡面的 dict 可變，所以另外實測。用一次性 pytest plugin 在 `tests/cli` 跑完後，比對每個 worker 的共用內容庫與重新載入的 `repr`：8 個 worker 都 `cache_used=1 same_as_fresh=True`。不需要排除任何測試。
- **R2**：`trpg.content.loader.parse_yaml` 是唯一入口，三處都改走它。用 `CSafeLoader`，沒有時退回 `SafeLoader`。測試：`tests/content/test_yaml_parser.py`。
  - `test_every_content_file_parses_the_same_with_both_loaders`：全部 YAML 逐檔比對，用 `repr` 比（比 `==` 嚴格，連鍵順序、`1`／`1.0`／`True` 都算），本機 654 檔。
  - 另有用到 C 解析器、退回路徑、拒絕 `!!python/...`、語法錯誤仍是 `YAMLError` 的測試。既有比對訊息的測試沒有放寬。
- **R4**：4 個案例加 `xdist_group("demo_balance")`，`xfail` 標記不動。`-v` 輸出顯示 4 個案例都在 `gw0`。
- **R5**：`env` fixture 用 monkeypatch 把 `accounts.SCRYPT_N` 改成 `2**4`，只限這個檔案。正式參數由 `tests/server/test_accounts.py::test_login_and_authenticate` 涵蓋（該檔案沒有改 `SCRYPT_N`，走完註冊、登入、驗證；本次單獨重跑通過）。

## R3 有做，判斷依據

- **不會被修改**：`ProposalModels` 是 `frozen=True, slots=True`，除了 `skill` 之外都是 tuple。呼叫端全部只讀：`evaluate.py:223` 與 `models.py:167` 把 `skill` 傳給 `TypeAdapter`；`proposal_subset.py`、`proposal_witness.py`、`llm/prompts/proposal.py`、`llm/propose.py`、`llm/candidate_source.py`、`llm/skill_eval.py` 只讀欄位或往下傳。`json_schema()` 每次都產生新的 dict。`src/trpg/skillgen` 與 `src/trpg/llm` 搜尋 `model_rebuild`、`__pydantic`、`setattr(` 都沒有結果。
- **快取鍵完整**：鍵是 `build_proposal_models` 實際收到的 9 個子集欄位，都是 tuple、字串或 `None`，以相等比對；內容庫用物件身分區分。只影響呈現的 `menu_seed`、`tokens` 等不進鍵。測試 `test_every_model_input_is_part_of_the_key` 逐欄位確認。
- **有上限**：LRU 上限 64 項，超過丟最舊的。項目持有內容庫的強參照，所以 `id` 在項目存活期間不會被重用，擠出後內容庫可回收。有 lock，建構在鎖外進行。
- **schema 相同**：`tests/skillgen/test_subset_models_cache.py::test_memoized_models_match_a_fresh_build`，7 種子集比對有快取與無快取的 JSON schema 及其他欄位。

## 待 PM 決定

1. worktree 基底是 `9bc45ad3`，比派工說的 `4d4948c8` 舊 4 個 docs commit。我沒有移動分支；合併時應該不會衝突，請確認這樣可以。
2. R1 在 `test_output_snapshots.py` 量不到改善。它只有 1 個測試案例，R1 的效果要看 `tests/cli` 整體，這次沒有量。是否要在全量時順便對照，請 PM 決定。
3. R3 的上限 64 是我取的保守值，規格沒有指定。正式伺服器最多會留 64 份動態模型，實際記憶體用量沒有量。
4. R5 的 `2**4` 是我取的值，規格只說「較小」。
5. `TRPG_CONTENT_DIR` 設成空字串時，正式碼視同未設，但 R1 走原函式（照規格最保守的解讀，只是少用快取）。
6. `test_demo_map_win_rate_and_length` 4 個案例這次都是 XPASS。依規格沒有動 `xfail` 標記；是否移除由 PM 決定。
