# Phase PERF-4｜mypy 修正與 pytest 省時

> 來源：2026-11-10 Windows 全量檢查（mypy 13 個錯誤）與效能盤點，使用者同意（「go」）。**不得減少任何比對內容**；確定性、重播、平衡相關的測試一律保留。
> 參考數字：Windows `-n 12` 全量 pytest 668 秒，15350 項。`load_library` 重複 761 次，佔測試累計時間 30%。

## 範圍外

- 不把慢測試標 slow、不刪 `test_demo_balance`、不減統計測試取樣（已決定先不做）。
- 不改 `--dist` 策略與 `-n` 預設值。不動 Defender 設定。
- 不跑全量（PM 合併後跑）。

## 交付項目

1. **M1 mypy**：修掉 `tests/api/test_hidden_info.py` 的 13 個錯誤（第 26～28 行 index 型別、第 116～117 行 `StatusApplied` 的 `**dict` 引數）。不加 `type: ignore`，不改測試的斷言內容。
2. **R1 CLI 測試快取內容庫**：`tests/cli/conftest.py` 加 autouse fixture，快取 `trpg.cli.main.load_checked_library`。只在 `content_dir is None` 且未設 `TRPG_CONTENT_DIR` 時走快取，其他情況一律走原函式。不改正式 CLI。快取放在行程內，同一 worker 共用。
3. **R2 YAML 換 C 解析器**：`src/trpg/content/loader.py:62`、`src/trpg/content/yaml_sources.py:31`、`src/trpg/skillgen/skill_yaml.py:22` 改走同一個 helper，用 `CSafeLoader`，沒有時退回 `SafeLoader`。安全性維持 safe loader，不得用非 safe 的 loader。
4. **R3 記憶化 `build_subset_models`**：先確認產生的動態模型在呼叫端不會被修改，且快取鍵能完整表達輸入（不依賴 `set` 迭代順序或內建 `hash()` 的跨行程結果）。快取對應的內容庫要能被回收或有上限，不可無限增長。**若無法確認不會被修改，就不做這項並寫進報告。**
5. **R4 `test_demo_balance` 不重算**：4 個案例加同一 `xdist_group`，或讓 fixture 只算該案例的地圖。比對內容不變，`xfail` 標記不動。
6. **R5 `test_owner_guard` 降 scrypt 成本**：`env` fixture 只在這個檔案用較小的 `SCRYPT_N`。不改正式預設值；要有一個測試仍以正式參數跑過驗證流程，若既有測試已涵蓋就寫明是哪一個。

## 受影響的既有功能

| 項目 | 影響 | 處理 |
|---|---|---|
| 內容 digest、世界日誌重播 | R2 換解析器，若 digest 算自解析結果，理論上可能受影響 | 要確認 digest 前後相同 |
| YAML 錯誤訊息 | C 解析器的語法錯誤訊息可能略異 | 跑 content 相關測試，有比對訊息的測試不得放寬 |
| macOS | C 解析器的 wheel 未確認 | 有退回路徑，不用另外驗 |
| CLI 快照 | R1 共用內容庫物件 | 內容庫要確認是 frozen，有任何測試會改它就排除該測試 |
| `skillgen` 提議流程 | R3 | 同輸入的模型 schema 要與未記憶化時相同 |

## 行為一致測試

- 全部內容 YAML（`content/` 下約 645 檔）逐檔比對 C 解析器與純 Python 解析器的結果相等；沒有 C 解析器時 skip。
- `build_subset_models` 有快取與無快取產出的 JSON schema 逐一相等（表格測試，至少涵蓋現有測試用到的幾種子集）。
- R1 的快取測試：帶 `content_dir` 或設 `TRPG_CONTENT_DIR` 時確實走原函式。

## 驗收條件

- `uv run mypy` 0 錯誤；`ruff check`、`ruff format --check`、`lint-imports` 通過；沒有新增 `type: ignore` 或複雜度 noqa。
- 相關測試過：`tests/cli`、`tests/content`、`tests/skillgen`、`tests/api/test_hidden_info.py`、`tests/engine/test_demo_balance.py`、`tests/test_architecture.py`、`test_owner_guard` 所在檔案。
- 一場 `trpg battle --log-json` ＋ `trpg battle replay` 通過。
- 內容 digest 前後相同（附指令與值）。
- 附對照：`tests/cli/test_output_snapshots.py` 與 `tests/content` 改前改後的 wall 時間（同一批交替跑各 2 次）。

## 報告

`docs/phases/PhasePERF-4報告.md`：逐條驗收、對照時間、R3 的判斷依據、待 PM 決定。
