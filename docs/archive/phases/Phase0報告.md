# Phase 0 完成報告

> 撰寫：實作者｜2026-10-17｜對應規格 `docs/phases/Phase0計畫.md`

## 摘要

依規格完成 Phase 0 的全部交付項目：可安裝的 `src/trpg` 套件骨架（10 個子套件附繁體中文職責說明）、ruff／mypy strict／pytest／import-linter 設定、xoshiro128\*\* ＋ splitmix64 亂數產生器（測試向量來自實際以 gcc 編譯執行的 C 參考程式）、共用型別與錯誤、內容資料載入器與 `content/elements.yaml` 範例、最小 CLI、`scripts/check.py`、GitHub Actions CI、README 與 git 歷史。驗收條件 1–10 在本工作區全部通過（106 個測試通過；hypothesis 屬性測試 1 個檔案依規格略過；lint-imports 依規格顯示略過警告）。唯一較明顯的偏離是「時間函式放行」改用巢狀 `ruff.toml` 實作，原因見「與規格的差異」第 1 點。

## 驗收條件逐條結果

| # | 條件 | 結果 | 證據（指令與輸出摘要） |
|---|---|---|---|
| 1 | `ruff check .` 與 `ruff format --check .` 無錯誤 | ✅ 通過 | `ruff check .` → `All checks passed!`；`ruff format --check .` → `38 files already formatted` |
| 2 | `mypy`（strict）無錯誤 | ✅ 通過 | `mypy` → `Success: no issues found in 28 source files`（環境變數見下方指令；PyYAML 型別借用 pyright 內附的 typeshed stub） |
| 3 | `pytest` 全部通過 | ✅ 通過 | `106 passed, 1 skipped`；略過的是 `tests/shared/test_rng_properties.py`（`could not import 'hypothesis'`，屬預期） |
| 4 | 三組亂數向量來自實際編譯執行的 C 參考程式，且 Python 一致 | ✅ 通過 | `gcc -std=c99 -O2 -Wall -Wextra -o rng_vectors scripts/rng_reference/rng_vectors.c && ./rng_vectors`（無警告）；輸出貼入 `tests/shared/test_rng.py` 的 `SPLITMIX64_SEED_1234567`、`XOSHIRO128SS_STATE_1234`、`RNG_SEED_42`，三個向量測試第一次執行即通過。另加第 4 組額外向量 `Rng(42).fork("戰鬥")`，同樣由 C 程式產生並通過 |
| 5 | 同種子同序列；狀態往返一致；`fork` 確定且不影響父串流 | ✅ 通過 | `test_same_seed_same_sequence`、`test_state_round_trip`、`test_fork_does_not_advance_parent`、`test_fork_same_label_same_stream`、`test_fork_different_label_different_stream`、`test_vector_fork_matches_reference` 等皆通過 |
| 6 | `tests/test_architecture.py` 能抓到違規 | ✅ 通過 | 暫時在 `src/trpg/engine/__init__.py` 末尾加一行 `import random` → `1 failed, 6 passed`，訊息 `trpg/engine/__init__.py:10: 禁止匯入 random`（ruff 也同時報 `TID251`）；改加 `import trpg.llm` → `1 failed`，訊息 `trpg.engine 不得匯入 trpg.llm`；移除後 `7 passed`，`git status` 乾淨。測試檔內另有掃描器自我測試（15 種違規片段、7 種依賴違規） |
| 7 | `trpg content check` 成功；改壞時非零結束且訊息含路徑 | ✅ 通過 | 正常：`內容檢查通過（…/content）： elements.yaml：7 種元素`，rc=0。暫時把 `name_zh: 火焰` 改成 `nmae_zh: 火焰`：`內容檢查失敗： /home/claude/LLM-MMO-TRPG/content/elements.yaml: 驗證失敗（2 個錯誤）： - elements.1.name_zh: Field required - elements.1.nmae_zh: Extra inputs are not permitted`，rc=1；已還原。CLI 測試另涵蓋錯誤元素代碼與缺檔 |
| 8 | `scripts/check.py` 在本工作區可執行，lint-imports 顯示略過警告 | ✅ 通過 | `bash scripts/verify_sandbox.sh`（設定 PYTHONPATH 後執行 `scripts/check.py`）→ 摘要：ruff check 通過、ruff format --check 通過、mypy 通過、lint-imports 略過（黃字「警告：找不到 lint-imports，略過此步驟（不算失敗）。」）、pytest 通過；`全部檢查通過。` |
| 9 | git 歷史乾淨 | ✅ 通過 | `git status` 無未提交變更；`git status --ignored` 只有快取資料夾（皆被忽略）；C 編譯產物只產生在工作區外的暫存資料夾，且 `.gitignore` 已列入；每個 commit 皆帶規定的兩行結尾。另以 `git archive` 把每個 commit 解到暫存資料夾分別執行驗證，7 個歷史 commit 全部「全部檢查通過」 |
| 10 | 沒有實作範圍外的東西 | ✅ 通過 | `engine`、`skillgen`、`sim`、`llm`、`narrative`、`roguelite`、`api` 只有 `__init__.py`（docstring）；沒有戰鬥、技能、LLM、FastAPI、前端程式；`types.py` 只有規格列出的型別 |

## 實際執行的驗證指令

以下指令可在本工作區直接複製貼上重現（使用者電腦請改用 `uv sync` 後 `uv run python scripts/check.py`）：

```bash
cd /home/claude/LLM-MMO-TRPG

# 1) 一鍵驗證（設定環境變數後執行 scripts/check.py）
bash scripts/verify_sandbox.sh

# 2) 個別步驟
ruff check .
ruff format --check .
T=$(mktemp -d) && ln -s /root/.local/share/uv/tools/pyright/lib/python3.13/site-packages/pyright/dist/dist/typeshed-fallback/stubs/PyYAML/yaml "$T/yaml-stubs" \
  && PYTHONPATH=/usr/local/lib/python3.13/dist-packages:/root/.local/share/uv/tools/pytest/lib/python3.13/site-packages:$T mypy; rm -rf "$T"
PYTHONPATH=src:/usr/local/lib/python3.13/dist-packages pytest

# 3) C 參考程式與測試向量（產物放在工作區外）
cd "$(mktemp -d)" && gcc -std=c99 -O2 -Wall -Wextra -o rng_vectors /home/claude/LLM-MMO-TRPG/scripts/rng_reference/rng_vectors.c && ./rng_vectors
cd /home/claude/LLM-MMO-TRPG

# 4) CLI
export PYTHONPATH=src:/usr/local/lib/python3.13/dist-packages
python3 -m trpg --version
python3 -m trpg rng --seed 42 --count 5
python3 -m trpg rng --seed 42 --count 5 --sides 20
python3 -m trpg content check; echo "rc=$?"

# 5) 驗收 6：架構測試能抓到違規（做完務必還原）
cp src/trpg/engine/__init__.py /tmp/engine_init.bak
echo "import random" >> src/trpg/engine/__init__.py
pytest -q tests/test_architecture.py        # 預期 1 failed
cp /tmp/engine_init.bak src/trpg/engine/__init__.py
pytest -q tests/test_architecture.py        # 預期 7 passed

# 6) 驗收 7：改壞 elements.yaml（做完務必還原）
cp content/elements.yaml /tmp/elements.bak
sed -i 's/name_zh: 火焰/nmae_zh: 火焰/' content/elements.yaml
python3 -m trpg content check; echo "rc=$?"  # 預期 rc=1，訊息含檔案路徑
cp /tmp/elements.bak content/elements.yaml
git status --short                           # 預期無輸出
```

工作區環境說明：pytest 與 mypy 各在獨立的 uv tool 環境，因此用 `PYTHONPATH` 讓它們看到系統的 pydantic／PyYAML；mypy 另需 pytest 的 site-packages（測試檔的 `import pytest` 型別）與 PyYAML stub（工作區沒有 `types-PyYAML`，借用 pyright 內附的 typeshed stub，以 `yaml-stubs` 連結模擬「已安裝的 stub 套件」，這樣 stub 本身不會被當成專案程式碼檢查）。

## 與規格的差異

1. **時間函式的放行方式（3.1）**：規格寫「以 `per-file-ignores` 讓 `api/cli/llm/narrative` 與 `scripts` 可以使用時間相關函式（但仍禁止 `random`）」。ruff 的 `per-file-ignores` 只能整條關閉 `TID251`，關掉後 `random` 也會一起放行，無法同時滿足兩個要求。改為在 `src/trpg/{api,cli,llm,narrative}/ruff.toml` 與 `scripts/ruff.toml` 放巢狀設定（`extend` 根目錄的 `pyproject.toml`），把 `banned-api` 覆寫成「只禁 `random`」。已實測：`cli`、`scripts` 中 `time.time()` 不報錯、`import random` 報錯；`tests/` 與引擎中兩者都報錯。`per-file-ignores` 仍用於 `tests/**` 放行 `PLR2004`（魔術數字）。為了不讓每個子資料夾各自產生 `.ruff_cache`，`pyproject.toml` 加了 `cache-dir = ".ruff_cache"`；wheel 打包排除 `**/ruff.toml`。
2. **額外的測試向量**：除了規格的三組，C 程式多輸出第 4 組 `Rng(42).fork("戰鬥")`，讓 `fork` 的做法（FNV-1a 64 ＋ splitmix64）也有獨立的參考實作驗證。
3. **架構測試比 ruff 規則更嚴**：`tests/test_architecture.py` 在確定性子套件中額外禁止 `secrets`、`os.urandom`、`uuid.uuid1`、`time.*_ns`、`datetime.today`，以及 `__import__("random")`／`importlib.import_module("random")`。ruff 的 `banned-api` 只列了規格要求的項目。
4. **額外加入的設定與檔案**：ruff `flake8-tidy-imports.ban-relative-imports = "all"`（一律絕對匯入，讓依賴方向更容易檢查）；ruff 排除 `RUF001/RUF002/RUF003`（中文全形標點）與 `PLR0913`（參數過多），皆在註解說明；`src/trpg/content/registry.py`（已知資料檔清單，供 `content check` 使用）；`scripts/verify_sandbox.sh`（只給本工作區用）。
5. **`tests/shared/test_rng_properties.py` 的 mypy 處理**：hypothesis 未安裝時會被視為 `Any`，因此該檔加上檔案層級的 `# mypy: disable-error-code="untyped-decorator"` 與 `# type: ignore[import-not-found,unused-ignore]`；安裝 hypothesis 的環境中兩者都不生效。

## 待 PM 決定

1. **巢狀 `ruff.toml`**（差異第 1 點）是否可接受？替代方案是 `per-file-ignores` 整條關閉 `TID251`，`random` 改靠架構測試把關（但架構測試只掃確定性子套件，不涵蓋 `api/cli/llm/narrative/scripts`）。
2. **`Pos.neighbors4()` 的邊界**：`Pos` 要求 `x, y >= 0`，因此位於 `x == 0` 或 `y == 0` 時，超出左／上邊緣的那一格會被**省略**（其餘順序不變），而不是回傳負座標或拋錯。座標系採「`x` 向右、`y` 向下、原點左上」，「上」為 `y - 1`。請確認。
3. **`water` 元素**：`docs/專案計畫.md` 5.1 的互動表有「`water` 遇到 `fire` 表面 → 熄滅」一列，但規格的 `Element` 列舉沒有 `water`（`Surface` 有）。目前依規格不加；Phase 1 實作互動表前需決定水是元素、技能原語，還是只作為表面。
4. **中文顯示名稱**由實作者擬定：元素（物理、火焰、冰霜、雷電、毒素、神聖、暗影）、表面（無、油、水、火焰、冰、毒、聖光）。屬性與稀有度取自計畫第 7.2、8.7 節。請確認用字。
5. **亂數消耗量的約定**（影響之後的重播與預覽）：`chance_permille` 即使 `p` 為 0 或 1000 也固定消耗一次 `randint(0, 999)`；`randint(lo, lo)` 不消耗亂數；多字組合時先抽到的 u32 放在高位。`Rng.from_state((0, 0, 0, 0))` 拋出 `ValueError`（全零替代常數只用在播種流程）；`Rng(True)` 這類 bool 種子拋出 `TypeError`。
6. **`scripts/check.py` 的失敗行為**：規格寫「任一步失敗就以非零代碼結束，最後印出各步驟結果摘要」。目前做法是**每一步都會執行**，最後印摘要並以非零結束（方便一次看到全部問題），而不是遇錯即停。
7. **`uv.lock`**：本工作區無法連 PyPI，沒有產生鎖定檔。建議 PM 在本機執行 `uv lock`（或 `uv sync`）後 commit `uv.lock`，CI 再改成 `uv sync --locked`。
8. **CI 動作版本**：使用 `actions/checkout@v4`、`astral-sh/setup-uv@v6`，並設定 `PYTHONUTF8=1` 讓 Windows 上的子程序以 UTF-8 輸出中文。推上 GitHub 時請確認版本是否要更新；hypothesis 屬性測試與 import-linter 也是第一次在 CI 實際執行。
9. **CLI 細節**：`trpg rng` 的 `--seed` 為必填、`--count` 預設 10；`trpg --version` 輸出 `trpg 0.0.1`；不帶子命令時以代碼 2 結束並印出用法。
10. **`IdAllocator`**：前綴限小寫英文開頭的 snake_case；序號超過 9999 後會變成 5 位數（`unit_10000`），字典序排序會與數值順序不同。若之後需要用 ID 排序，請決定位數或改用數值排序。
11. **`default_content_dir()`** 以原始碼位置推算專案根目錄的 `content/`，適用於本機開發（editable install）。若日後要發佈 wheel，需決定是否把 `content/` 打包進套件。
12. **計畫文件的小落差**（未修改，供 PM 參考）：`docs/專案計畫.md` 第 0 節第 10 點提到 `trpg.server`，實際子套件名稱是 `trpg.api`；同節第 9 點「不得依賴 `set` 或 `dict` 以外的無序集合」的語意與 `CLAUDE.md` 守則 2「不依賴 `set` 迭代順序」略有不同。

## 給下一階段的備註

- **亂數**：引擎一律接收 `trpg.shared.rng.Rng`；用 `get_state()`／`from_state()` 寫入事件日誌與存檔。需要彼此獨立的子系統（例如敵人 AI、掉落、地圖事件）時用 `rng.fork("label")`，父串流不會被推進，所以加入新的子串流不會改變既有的主序列。沒有浮點數 API，機率用 `chance_permille`。
- **確定性守則已有兩層保護**：ruff `TID251` 與 `tests/test_architecture.py`。新增子模組時不需改設定；若在 `engine` 等子套件新增子資料夾，記得放 `__init__.py`。
- **內容資料**：新資料檔的 model 繼承 `trpg.content.schemas.ContentModel`（已設 `extra="forbid"`、`frozen=True`），在 `trpg.content.registry.KNOWN_CONTENT_FILES` 登記後，`trpg content check` 與測試就會自動涵蓋。內容 model 不要開 pydantic `strict`（YAML 載入的字串需轉成列舉）。
- **ID**：用 `trpg.shared.ids.IdAllocator`，其狀態 `IdAllocatorState` 可直接 `model_dump_json()`，應與戰鬥狀態一起序列化。
- **型別**：`Pos` 為 frozen、strict、可雜湊，可當 dict 鍵；`neighbors4()` 順序固定為上、右、下、左。
- **本工作區驗證**：`bash scripts/verify_sandbox.sh`；使用者電腦與 CI：`uv run python scripts/check.py`。
