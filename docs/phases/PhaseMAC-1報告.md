# Phase MAC-1 報告：Mac 相容修正

日期：2026-11-06。環境：Mac mini（arm64）、macOS、Node 26（無 corepack）、pnpm 12.14.0 全域安裝、無 LLM。

## 做了什麼

| 項目 | 內容 | 檔案 |
|---|---|---|
| 1. corepack 找不到時改用 pnpm | 新增 `pnpm_command()`：`corepack` → `pnpm` → `npx -y pnpm@<package.json 的 packageManager 版本>` → `None`；`check.py` 找不到時略過前端三步並印警告，`play.py` 找不到時才退出（提示改為「找不到 pnpm，請安裝 Node.js 20.19 以上並 `npm install -g pnpm`」）；所有提示文字改成 `pnpm -C client …` | `src/trpg/cli/frontend.py`（新）、`tests/cli/test_frontend.py`（新，7 個測試）、`scripts/check.py`、`scripts/play.py`、`tests/test_play_script.py`（＋2 個測試）、`src/trpg/cli/serve.py`、`scripts/deploy.py`、`scripts/export_openapi.py`、`client/vite.config.ts`、`docs/部署說明.md`、`tests/api/test_static_client.py`、`tests/api/test_openapi_snapshot.py` |
| 2. 寫死的 Windows 路徑改中性 | `LLM_START_HINT` 改為「請確認本機模型服務（LM Studio 或其他 OpenAI 相容伺服器）已啟動，且連接埠與設定檔（config/llm.toml）一致。」；測試改比對 `config/llm.toml`；docstring／pytest marker／`config/llm.toml` 註解改中性；`export_workshop_descriptions.py` 預設輸出改為專案根目錄的 `workshop_descriptions.csv`（加 `-h/--help` 印用法、加進 `.gitignore`） | `src/trpg/llm/errors.py`、`tests/llm/test_client.py`、`tests/llm/test_propose.py`、`pyproject.toml`、`config/llm.toml`、`scripts/export_workshop_descriptions.py`、`.gitignore` |
| 3. mypy 38 個錯誤 → 0 | 正確修型別（見下方「mypy 修法」） | 6 支 scripts、12 個測試檔（清單在 commit `49df77f1`） |
| 4. vitest 指令流雜湊跨平台 | 兩檔的 `fmt` 把非整數改成 `toFixed(6)`（`"-0.000000"` 正規化成 `"0.000000"`；整數維持原本含 `-0` 的處理）；在 Mac 重產兩個 `.snap`；`creaturePose.test.ts` 兩個字面比對改成 6 位小數格式 | `client/src/render/creaturePose.test.ts`、`client/src/render/inkDollSnapshot.test.ts`、`client/src/render/__snapshots__/*.snap` |
| 5. 文件補 Mac 說明 | `CLAUDE.md` 常用指令區補 3 行；`docs/部署說明.md` 第 3 節 macOS 加「前置安裝」（uv、`npm install -g pnpm`、建置前端） | `CLAUDE.md`、`docs/部署說明.md` |

未改 `docs/開發PM交接.md`、`docs/專案PM交接.md`（後者有別人的未暫存變更，未碰）。

### mypy 修法摘要

- `WalkAction` 改從 `trpg.world.field_actions` 匯入（`trpg.world.actions` 的 `__all__` 沒有它）；`write_atomic` 的「真函式」改從 `trpg.world.save` 取（`monkeypatch.setattr(world_module, "write_atomic", spy)` 照舊，spy 仍攔到 `trpg.api.world` 內的呼叫）。
- `f4c_terrace_sweep.py`／`f4d_terrace_sweep.py` 同目錄匯入：加 `# type: ignore[import-not-found]  # 一次性量測腳本，同目錄匯入（已 sys.path.insert）`，與既有的 `bal*` 腳本做法一致。試過 `mypy_path = ["src", "scripts"]`，會讓 11 支舊腳本冒出 17 個新錯誤（既有的 ignore 變成 unused、型別流進去後再報錯），所以不採用。
- `tests/world/test_trade.py`：`_send`／`_sent` 補 `-> StepResult`，`result.other` 的 Optional 用 `assert … is not None` 處理，刪掉 5 個因此多餘的 `type: ignore`。
- `scripts/race_matrix.py`：`_hero_base` 回傳型別改成 `tuple[UnitTemplate, tuple[SkillDef, ...]]`（從 `object` 快取取出後 `isinstance` 斷言），刪掉 3 個 `type: ignore`；`field.location is None` 先跳過。
- `scripts/sim_race_138.py`／`f4_newbie_sim.py`：`state.units[...]` 的鍵改用 `UnitId`。
- 其餘：補回傳型別、刪 unused ignore、`json.loads` 結果先放進有型別的變數、`dict[str, Any]` 標註、`assert … is not None`。

## 驗收指令與結果

| 指令 | 結果 |
|---|---|
| `uv run ruff check` | 通過 |
| `uv run ruff format --check` | 2242 檔已格式化 |
| `uv run mypy` | 0 錯誤（1378 檔） |
| `uv run lint-imports` | 13 kept, 0 broken |
| `uv run pytest -q -x -n 4 tests/llm tests/cli tests/test_play_script.py tests/test_architecture.py` ＋第 3 點改到的 12 個測試檔＋`tests/api/test_static_client.py`、`test_openapi_snapshot.py` | 710 passed |
| `pnpm -C client exec vitest run src/render/creaturePose.test.ts src/render/inkDollSnapshot.test.ts` | 11 passed（2 檔） |
| `pnpm -C client typecheck`（`tsc --noEmit`） | 通過 |
| `grep -rn 'F:\\WSL\|C:\\Users\|start\.bat' src tests scripts config pyproject.toml CLAUDE.md README.md` | 0 筆（`start.bat` 要用 `start\.bat`，否則會匹配到 `start_battle`） |

沒跑全量 pytest、全量 vitest、build（PM 合併後跑）。註：重產 `creaturePose` 快照時 `vitest -u <檔>` 把路徑吃成 `-u` 的值而跑了全量 vitest 一次（266 檔全過、只更新該檔快照），非刻意。

## Commit 清單

1. `ff0ac6b6` fix(scripts): use pnpm when corepack is missing (MAC-1)
2. `e6ca8a29` chore: replace hard-coded Windows paths with neutral hints (MAC-1)
3. `49df77f1` fix(types): clear 38 mypy errors in scripts and tests (MAC-1)
4. `36da409f` test(client): hash canvas numbers at 6 decimals for cross-platform snapshots (MAC-1)
5. `0a2dc4cd` docs: add macOS notes to CLAUDE.md and deployment guide (MAC-1)
6. （本報告）

## 待 PM 決定

1. **雜湊快照只在 Mac 重產**：改 `fmt` 後兩個 `.snap` 的每一個雜湊都變了（指令數全部不變，已用去雜湊的 diff 確認）。Windows x64 上要再跑一次 `pnpm -C client exec vitest run src/render/creaturePose.test.ts src/render/inkDollSnapshot.test.ts` 確認一致；若仍有差異，代表差在第 6 位小數以前（或指令數），要再查。
2. **`pnpm_command()` 回傳完整路徑而非 `["corepack", "pnpm"]`**：規格寫回 `["corepack", "pnpm"]`，實作回 `shutil.which` 解析出的完整路徑（例 `["/opt/homebrew/bin/corepack", "pnpm"]`），因為 Windows 的 `pnpm.cmd`／`corepack.cmd` 不經 shell 時只有完整路徑才能執行（`play.py` 原本也是傳 `which` 的結果）。測試用 monkeypatch 蓋 `shutil.which`，驗的是元素結構。
3. **`export_workshop_descriptions.py` 的預設輸出**：選了「專案相對的 `workshop_descriptions.csv`」（維持 CSV 副檔名，因為內容是 UTF-8 BOM 的兩欄 CSV；規格寫的 `.md` 應是筆誤），並把它加進 `.gitignore`。若要改成 `--out` 必填請說。
4. **`-0` 的處理**：整數分支仍把 `-0` 印成 `"-0"`（原行為），非整數分支把 `"-0.000000"` 正規化成 `"0.000000"`（規格原文）。兩者不一致但各照原文；若希望統一成 `"0"` 請說。
5. **`LLM_START_HINT` 改文**後，`tests/llm/test_client.py` 的 3 處比對改成 `config/llm.toml`；`config/llm.toml` 開頭說明改成「OpenAI 相容 API：LM Studio、vLLM 等」，埠號註解改為「預設 8001，避開 `trpg serve` 的 8000；LM Studio 預設 1234」。
6. **mypy 有疑慮處**：`race_matrix.py` 的 `_hero_base` 以 `isinstance` 斷言取代 `type: ignore`（行為不變，只是多兩個 assert）；`tests/world/test_newcomer_6f4.py:332` 保留原本的 `# type: ignore[union-attr]`（它仍是必要的），只加 `assert location is not None`。
7. 其他腳本（`bal*`、`f4*`）仍以 `# type: ignore[import-not-found]` 處理同目錄匯入；若日後想一次清掉，可把 `scripts` 加進 `mypy_path` 並修那 17 個連帶錯誤，這次沒做。
