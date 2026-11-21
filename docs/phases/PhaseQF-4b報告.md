# Phase QF-4b 報告：護主配方加速（輸出不變）

基準：main `e8ad47911`。分支 `worktree-agent-a22784476adbf3211`，沒 push。規格：`docs/phases/PhaseQF-4b計畫.md`，加上開發 PM 的補充：先用 (b)；第 2 項要做；放寬兩個逾時。

**結論：兩個目標測試都降到 120 秒以下，600 秒的放寬已拿掉。** 只用了 (b)，也就是純快取，所以亂數和輸出都不變。所有比對都是 different=0。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| 補充 3：放寬兩個逾時 | `1e7ac203e` | `tests/infra/test_xdist_loadgroup.py`、`client/src/test/sourceScan.test.ts` |
| 1 加速護主配方 | `13b816f4a` | `composer_tuning.py`、`random_composer.py`、`composer_recipes.py` |
| 2 `check_draft` 接受 `draft_options` | `d0a87818d` | `draft_check.py`；`test_player_text.py` 改成傳進去 |
| 3 拿掉放寬 | `020cb1060` | `test_upgrade_topup.py`、`test_test_mode.py` 各刪一行 `@pytest.mark.timeout(600)` |
| 4 一起量 | 本報告第 3 節 | |
| 報告 | 本 commit | |

## 2. 做法

### 2.1 護主配方：用 (b)

- `tune()` 和 `_Evaluator` 多一個選填參數 `memo`（型別 `RatioMemo`）。
  - 有給 `memo` 時，`ratio()` 先用 `memo.draft_key` 算鍵。鍵是草稿去掉 `id`、`narrative` 後的 JSON 摘要，和 PERF-2 用的是同一套。
  - 鍵已經在表裡，就直接拿記下的（預算比例, 占比違規數），不再做 `model_validate`、`skill_budget`、`share_violations`。
  - 結構不合法時記成 `(None, None)`。命中時違規數照舊不更新，和沒有快取時一樣。
- 只有護主配方會用到這張快取表：`_compose_reaction_recipe` 在 `is_guardian(recipe)` 時，從 `library_memo(lib, "composer.guardian.ratio")` 拿表，經 `_tune_drafts(..., memo=)` 傳給 `tune`。
  - 其他配方不傳，行為和改前逐行相同。
  - 快取表掛在內容庫上。用 `dataclasses.replace` 換內容後是新的空表（例如測試的 `_without_recipes`）。上限照 `MEMO_LIMIT`。
- **為什麼亂數和結果都不變：**
  - 快取只取代「從草稿算出比例和違規數」這一步。這一步本來就是純函式，而且不碰亂數。
  - `tune` 照舊依比例決定要不要擲目標比例（`rng.randint`），也照舊依序調旋鈕。所以亂數取用的次數和順序都一樣。
  - 鍵不含 `id`、`narrative`。這兩個欄位不影響預算和占比，PERF-2 的 `memo.py` 已經這樣用。
- 沒做 (a)、(c)（開發 PM 指示：(b) 夠快就不做）。

### 2.2 `check_draft(draft, library, *, options=None)`

- 多一個關鍵字參數 `options`，給呼叫者傳已經算好的 `draft_options(draft, library)`（不帶 `weapon`）。不傳時照舊自己算。
- `tests/skillgen/test_player_text.py::_player_texts` 改成傳進去，每份草稿只算一次。
- src 裡兩個呼叫端（工坊的 `_check`、匯出）原本就沒有重複算，所以沒改。
- 等價檢查（scratch `item2_eq.py`）：player_text 的 911 份不同草稿，傳和不傳的 `DraftCheck` JSON `same=911 different=0`。

### 2.3 放寬兩個逾時（開發 PM 補充 3）

只改逾時，不改測試內容：

| 測試 | 改前 | 改後 |
|---|---|---|
| `test_xdist_loadgroup.py::test_loadgroup_survives_two_workers_crashing_together` | 內層 pytest 240 秒，外層 `timeout(290)` | 內層 540 秒（`TWO_CRASH_LIMIT_SECONDS`），外層 `timeout(600)`（`TWO_CRASH_TIMEOUT_SECONDS`） |
| `sourceScan.test.ts`「測試檔不用 `import.meta.glob`」 | 30 秒 | 120 秒 |

- `_run_case` 多一個 `limit` 參數，預設還是 `CASE_LIMIT_SECONDS`（240）。另外兩個 loadgroup 測試不變。

## 3. 秒數

都是單獨跑：`run_pytest.py -q -p no:randomly --durations`，不平行，每個測試一個行程。負載用 `tasklist` 數 `python.exe` 行程，只能當相對指標。

| 測試 | 改前 | 改後 |
|---|---|---|
| summon（`test_reaction_keywords_the_composer_cannot_carry[summon]`） | 219.7 秒（行程 18，另外同時跑著 4 個行程的 scratch 基準 dump） | **44.5 秒**（行程 18） |
| 裝備重播（`test_run_with_equipment_plays_to_the_end_and_replays_the_same`） | 155.2 秒（行程 24，同時有基準 dump） | **43.5 秒**（行程 18） |
| 第 4 項（`test_test_mode_refills_to_the_gear_inclusive_maximum`） | 79.4 秒（行程 20，同時有基準 dump） | **25.7 秒**（行程 20） |

- 改前的秒數比 QF-4 量的少（QF-4 是 271.7／210.0 秒），因為這次的負載比較輕。
- 改後兩個檔一起跑 `-n 8`：summon 58.0 秒、裝備重播 52.6 秒、第 4 項 27.3 秒，51 passed，共 73.6 秒。
- 附帶：player_text 的 8 份（第 2 項）在 `-n 8` 下每份 11.4～12.6 秒。QF-4 驗收時在較重的負載下是 26～42 秒，所以這兩個數字不能直接比。

## 4. 不變比對（基準 `git archive e8ad47911 src content config`）

- 腳本放在 scratch，沒進 repo。沿用 HC-5a 的 `budget434.py`、`compare78.py`、`flash_dump.py`／`flash_cmp.py`，和 HC-4b2 的 `pick_dump.py`／`census_cmp.py`。另外新寫一支 `topup_dump.py`。
- 改前用基準的 `src/`、`content/`（`PYTHONPATH`＋`TRPG_CONTENT_DIR`），並確認載入的 `trpg` 來自基準。改後用 worktree（第 3 項 commit 後）。

| 比對 | 結果 |
|---|---|
| 組合器出題：`recipe_census.py --seeds 4 --tiers 1,3 --rarities common,epic` | `cells=204 same=204 different=0`（排除計時欄位） |
| 許願出題：`wish_coverage.py run --seeds 3 --tiers 1,2` | `buckets=384 same=384 different=0` |
| 挑選模式三選一：4 個 build × 種子 0、1 × 升級白板／完整技能 | 16 份、48 格、148 個候選，JSON 逐位元組相同 |
| 升級補足：16 個關鍵字 × 反應／被動 × （1 稀有、2 稀有、2 史詩、3 史詩）× 完整組合器／RC-1 前組合器的 `fallback_skill(seed=0)`，加上 `KEYWORD_CASES` 的 `evaluate_with_repair` | 256 題（139 組合器、53 工坊、64 不合法題）＋全部 keyword case，JSON 逐位元組相同 |
| 逐招預算 434 招 | `skills=434 same=434 different=0`（檔案逐位元組相同） |
| 78 場戰鬥 | `battles=78 events=26446 different=0`；內嵌規則包 0 差異 |
| 閃現出題 | 規則、計價、加成、大變化、退回都相同；完整技能 `same=406 different=0`；出題 `items=522 rows=3966 same=522 different=0`；閃現表 dump 0 差異 |
| parity、CLI 快照 | 交件前的 slow 測試（見第 5 節） |

## 5. 檢查與結束碼

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check .` | 0 |
| `uv run ruff format --check .` | 0（3068 files） |
| `uv run mypy` | 0（1775 source files） |
| `uv run lint-imports` | 0（14 kept） |
| 相關測試：`run_pytest.py -n 8`（composer 6 檔、`test_upgrade_topup`、`test_recipe_census_rc0`、`test_test_mode`） | 0（193 passed） |
| `run_pytest.py tests/skillgen/test_player_text.py tests/skillgen/test_workshop_check.py -n 8` | 0（25 passed） |
| `run_pytest.py tests/api/test_workshop_*.py`（3 檔）`-n 8` | 0（22 passed） |
| `run_pytest.py tests/infra/test_xdist_loadgroup.py` | 0（3 passed） |
| `pnpm -C client typecheck` | 0 |
| `pnpm -C client test` | 0（393 檔、4822 項） |
| `pnpm -C client build` | 0 |
| `scripts/check.py`、`-m slow tests/skillgen/test_refactor_parity.py tests/cli` | 交件前在全部 commit 之後跑（照開發 PM 排的順序），結束碼寫在交件訊息；跑完沒有再改檔 |

- 沒有改 `content/`、`config/`、`docs/design/`、`pyproject.toml`、`.claude/`，也沒有改標 slow。
- 沒有新增 `# noqa`。

## 6. 待 PM 決定

1. **(a)、(c) 沒做**：(b) 已經達標。如果之後還想再快，可以在「每份草稿最弱強度就不合格」時提早放棄。不過這會改亂數或候選內容，要另外排。
2. **伴生（被動 `companion`）沒加快取**：它的草稿結構和護主一樣，沒有旋鈕，只差召喚物、屬性、強度、代價。規格只寫護主，所以沒動。要加的話是一行：`_compose_passive_recipe` 照護主的做法傳 `memo`，輸出一樣不變。
