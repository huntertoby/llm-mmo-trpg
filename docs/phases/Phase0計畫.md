# Phase 0 計畫：基礎建設

> 撰寫：PM｜2026-10-17｜對應 `docs/專案計畫.md` 第 14 節 Phase 0
> 實作者請先讀：`CLAUDE.md`、`docs/專案計畫.md` 第 0、12、13 節。其餘章節只需略讀，了解之後要長出什麼即可。

---

## 1. 目標

建立之後所有階段共用的地基：

- 一個結構正確、可安裝的 Python 專案（`src/trpg` 套件）
- 程式品質工具（ruff、mypy strict、import-linter）與一鍵檢查腳本
- **可種子化、可序列化、跨平台結果一致的亂數產生器**（確定性引擎的根基）
- 最基本的共用型別與錯誤類別
- 內容資料（`content/`）的載入與驗證機制，並以一個範例資料檔證明可行
- 最小的 CLI
- CI 設定檔
- git repo 與第一批 commit

**不在範圍內**（不要做）：戰鬥規則、格子、單位、技能、LLM、FastAPI、前端。各子套件只建立空殼與職責說明。

---

## 2. 工作環境（重要）

- 在 **雲端工作區** 的 `/home/claude/LLM-MMO-TRPG` 內工作（已存在，內含 `CLAUDE.md` 與 `docs/`）。不要動使用者電腦上的資料夾，同步由 PM 負責。
- **這個工作階段無法連到 PyPI**，`uv sync`／`pip install` 會失敗，不要反覆重試。以下工具已預先安裝，請用它們驗證：

| 工具 | 用法 |
|---|---|
| Python 3.13 | `/usr/bin/python3`，系統 site-packages 已有 `pydantic` 2.x、`yaml`（PyYAML） |
| pytest 9 | `PYTHONPATH=src:/usr/local/lib/python3.13/dist-packages pytest`（pytest 在獨立的 uv tool 環境，需用 PYTHONPATH 讓它看到 pydantic 與專案原始碼） |
| mypy 2.x | `PYTHONPATH=/usr/local/lib/python3.13/dist-packages mypy`（同理，讓 pydantic mypy 外掛可以載入） |
| ruff 0.16 | 直接執行 `ruff` |
| gcc | 可用來編譯參考 C 程式，產生亂數測試向量 |
| git | 可用 |

- **沒有** hypothesis、import-linter、FastAPI。相關設定照常寫進 `pyproject.toml` 與 CI（使用者的電腦與 CI 能正常安裝），但在本工作區：
  - hypothesis 測試用 `pytest.importorskip("hypothesis")`，本機會被略過，這是預期行為。
  - import-linter 由 `tests/test_architecture.py`（AST 掃描）提供等效保障；`scripts/check.py` 偵測到未安裝時印出警告並略過。
- 建議在 `scripts/check.py` 之外，另寫一個只給本工作區用的小腳本或在報告中記錄你實際執行的指令，讓 PM 能重現驗證。

---

## 3. 交付項目

### 3.1 專案設定檔

**`pyproject.toml`**
- 專案名稱 `llm-mmo-trpg`，套件 `trpg`，src layout，`requires-python = ">=3.12"`，版本 `0.0.1`。
- build backend：hatchling。
- 執行相依：`pydantic>=2.7`、`pyyaml>=6`。
- 開發相依（`[dependency-groups] dev`）：`pytest`、`hypothesis`、`ruff`、`mypy`、`import-linter`、`types-PyYAML`。
- CLI 進入點：`trpg = "trpg.cli.main:main"`。
- **ruff**：`line-length = 100`、`target-version = "py312"`；規則至少包含 `E, F, W, I, B, UP, SIM, RUF, TID, PL`（可視需要排除少數過嚴的 PL 規則並在註解說明）。
  - 用 `flake8-tidy-imports.banned-api`（TID251）禁止：`random`（整個模組）、`time.time`、`time.monotonic`、`time.perf_counter`、`datetime.datetime.now`、`datetime.datetime.utcnow`、`datetime.date.today`、`uuid.uuid4`。訊息寫明原因（例如「引擎必須確定性，請使用 trpg.shared.rng.Rng」）。
  - 以 `per-file-ignores` 讓 `src/trpg/{api,cli,llm,narrative}/**` 與 `scripts/**` 可以使用時間相關函式（但仍禁止 `random`）。測試檔也禁止 `random`。
- **mypy**：`strict = true`、啟用 `pydantic.mypy` 外掛、`files = ["src", "tests", "scripts"]`。
- **pytest**：`testpaths = ["tests"]`、`addopts = "-ra"`、`pythonpath = ["src"]`。
- **import-linter**（`[tool.importlinter]`）：`root_package = "trpg"`，至少兩個 contract：
  1. `trpg.engine` 禁止匯入 `trpg.llm`、`trpg.narrative`、`trpg.api`、`trpg.roguelite`、`trpg.sim`、`trpg.skillgen`、`trpg.cli`。
  2. `trpg.shared` 禁止匯入任何其他 `trpg` 子套件。

**其他設定檔**：`.python-version`（`3.12`）、`.gitignore`（Python、uv、IDE、OS 常見項目，以及 `.venv/`、`*.local.*`）、`.editorconfig`（UTF-8、LF、縮排 4、markdown 不刪行尾空白）、`.gitattributes`（`* text=auto eol=lf`，讓 Windows 使用者 checkout 後行尾一致）。

### 3.2 套件骨架

建立下列子套件，每個都要有 `__init__.py`，內含 **繁體中文 docstring** 說明職責與「從第幾個 Phase 開始實作」（內容參照 `docs/專案計畫.md` 第 13 節）：

```
src/trpg/__init__.py      # __version__ = "0.0.1"
src/trpg/py.typed
src/trpg/shared/          # 本階段實作
src/trpg/engine/          # Phase 1
src/trpg/content/         # 本階段實作載入器；資料本體在頂層 content/
src/trpg/skillgen/        # Phase 2
src/trpg/sim/             # Phase 2
src/trpg/llm/             # Phase 3
src/trpg/narrative/       # Phase 5
src/trpg/roguelite/       # Phase 4
src/trpg/api/             # Phase 4
src/trpg/cli/             # 本階段實作最小 CLI
```

另建 `src/trpg/__main__.py`，讓 `python -m trpg` 等同 `trpg`。

### 3.3 亂數產生器 `src/trpg/shared/rng.py`

這是本階段最重要的交付物。

**演算法**
- 核心：**xoshiro128\*\***（32 位元輸出，狀態為 4 個 32 位元整數）。
- 播種：輸入一個 0 ≤ seed < 2⁶⁴ 的整數，用 **splitmix64** 產生兩個 64 位元數，拆成 4 個 32 位元字作為狀態（第一個 64 位元數的低 32 位元為 s0、高 32 位元為 s1，第二個同理為 s2、s3）。若狀態全為 0（理論上幾乎不可能），改用固定的非零常數，並寫測試涵蓋。
- 所有運算以 Python 整數搭配 `& 0xFFFFFFFF`／`& 0xFFFFFFFFFFFFFFFF` 遮罩實作，確保跨平台一致。

**API**（類別 `Rng`，可變物件）

| 方法 | 說明 |
|---|---|
| `Rng(seed: int)` | 以 splitmix64 播種；seed 超出範圍時拋出 `ValueError` |
| `Rng.from_state(state: tuple[int, int, int, int])` | 由序列化狀態還原 |
| `get_state() -> tuple[int, int, int, int]` | 取得狀態（供事件日誌與重播使用） |
| `next_u32() -> int` | 下一個 32 位元無號整數 |
| `randint(lo: int, hi: int) -> int` | 閉區間 `[lo, hi]` 的均勻整數；**必須無偏差**（用拒絕取樣，不可直接取餘數）；`lo > hi` 拋出 `ValueError`；區間大小可超過 2³² 時以多個 u32 組合 |
| `roll(sides: int) -> int` | 擲一顆 `sides` 面骰，等同 `randint(1, sides)` |
| `d20() -> int` | `roll(20)` |
| `chance_permille(p: int) -> bool` | 以千分比判定成功（0 ≤ p ≤ 1000），不使用浮點數 |
| `choice(seq: Sequence[T]) -> T` | 均勻選一個；空序列拋出 `ValueError` |
| `shuffled(seq: Sequence[T]) -> list[T]` | 回傳新的洗牌後串列（Fisher–Yates），不修改輸入 |
| `fork(label: str) -> Rng` | 依目前狀態與 `label` 衍生一個獨立子串流，**不推進** 父串流；`label` 的雜湊必須用穩定演算法（例如 FNV-1a 64 位元搭配 UTF-8 編碼），**不可用內建 `hash()`** |

- 不提供任何浮點數 API（例如 `random() -> float`）。若日後需要，另案討論。
- 型別標註完整，通過 mypy strict。

**測試向量**
- 用 gcc 編譯 Sebastiano Vigna 的參考 C 實作（xoshiro128\*\* 與 splitmix64，自行依公開演算法撰寫一個小 C 程式即可），產生以下向量並寫進測試：
  1. splitmix64，seed = 1234567，前 5 個輸出。
  2. xoshiro128\*\*，直接設定狀態 `(1, 2, 3, 4)`，前 10 個輸出。
  3. `Rng(seed=42)` 的前 10 個 `next_u32()`（由你的 C 程式模擬完整播種流程產生）。
- 把 C 程式原始碼放在 `scripts/rng_reference/`（附 README 說明如何編譯與產生向量），讓日後可重現。不要把編譯產物 commit 進去。

### 3.4 共用型別與錯誤

**`src/trpg/shared/types.py`**：只放最基礎、之後確定會用到的型別，不要預先設計戰鬥模型。

- ID 型別（`typing.NewType`，底層為 `str`）：`UnitId`、`ObjectId`、`SkillId`、`ItemId`、`BattleId`、`MapId`。
- `Pos`：格子座標，pydantic frozen model，欄位 `x: int`、`y: int`（皆 ≥ 0），提供 `neighbors4()` 回傳上下左右四格（依固定順序：上、右、下、左；不檢查地圖邊界）。
- 列舉（`StrEnum`，值為小寫英文）：
  - `Element`：`physical, fire, ice, lightning, poison, holy, shadow`
  - `Surface`：`none, oil, water, fire, ice, poison, holy`
  - `Attribute`：`str, dex, con, int, wis, wil`（成員名稱可用 `STR` 等避開關鍵字衝突，值維持小寫縮寫）
  - `Rarity`：`common, uncommon, rare, epic, legendary`
  - 每個列舉成員附上繁體中文顯示名稱（例如以 `display_name` 屬性或對照表提供）。

**`src/trpg/shared/errors.py`**：`TrpgError`（基底）、`ContentError`（內容資料錯誤，需帶檔案路徑與原因）、`IllegalActionError`（Phase 1 使用，本階段只定義）。

**`src/trpg/shared/ids.py`**：`IdAllocator`：以前綴與遞增計數產生確定性的 ID（例如 `IdAllocator("unit").next()` → `"unit_0001"`），狀態可序列化。

### 3.5 內容資料載入

**`src/trpg/content/loader.py`**
- `load_content_file(path, model)`：依副檔名讀取 `.yaml`／`.yml`／`.json`（YAML 用 `yaml.safe_load`），以指定的 pydantic model 驗證；任何讀取或驗證錯誤都轉成 `ContentError`，訊息包含檔案路徑與 pydantic 的錯誤摘要。
- 內容 model 一律 `model_config = ConfigDict(extra="forbid", frozen=True)`，拼錯欄位就會報錯。
- `default_content_dir()`：回傳專案頂層 `content/` 的路徑（以套件位置推算，並允許用環境變數 `TRPG_CONTENT_DIR` 覆寫）。

**範例資料 `content/elements.yaml`**：列出 7 種元素，每筆含 `id`（對應 `Element`）、`name_zh`、`description_zh`。對應的 model 放在 `src/trpg/content/schemas.py`，並驗證：
- 每個 `Element` 成員恰好出現一次（不多不少、不重複）。

**`content/README.md`**：說明這個資料夾的用途與未來的子資料夾規劃（primitives、shapes、skeletons、objects、interactions、maps、marks、resonance、affixes、loot、budgets），參照 `docs/專案計畫.md`。

### 3.6 CLI `src/trpg/cli/main.py`

使用標準庫 `argparse`，提供：
- `trpg --version`：印出版本。
- `trpg rng --seed 42 --count 5 [--sides 20]`：印出亂數序列（未給 `--sides` 時印 `next_u32()`，給了則印擲骰結果），每行一個數字。
- `trpg content check`：載入並驗證 `content/` 下目前所有已知資料檔，成功印出摘要，失敗以非零代碼結束並印出 `ContentError` 訊息。
- `main(argv: list[str] | None = None) -> int`，方便測試。

### 3.7 測試 `tests/`

| 檔案 | 內容 |
|---|---|
| `tests/shared/test_rng.py` | 三組測試向量；同種子同序列；不同種子不同序列；`get_state`／`from_state` 往返後序列一致；`randint` 邊界（`lo == hi`、負數區間、超過 2³² 的區間）與錯誤輸入；以固定種子做簡單的均勻性檢查（例如 d20 擲 20,000 次，每面次數落在合理範圍或卡方檢定通過）；`chance_permille` 的 0 與 1000；`shuffled` 確定性且不修改輸入；`fork` 不推進父串流、同 label 結果相同、不同 label 結果不同；全零狀態保護 |
| `tests/shared/test_rng_properties.py` | hypothesis 屬性測試（以 `importorskip` 包住）：任意種子與區間，`randint` 結果必在區間內；狀態往返；`fork` 的確定性 |
| `tests/shared/test_types.py` | `Pos` 驗證與 `neighbors4` 順序；列舉值與中文名稱齊全；`IdAllocator` 確定性與序列化 |
| `tests/content/test_loader.py` | `elements.yaml` 可載入且通過「每元素恰好一次」檢查；用 `tmp_path` 建立錯誤的 YAML／多餘欄位／缺少元素，皆拋出 `ContentError` 且訊息含路徑 |
| `tests/test_architecture.py` | 以 `ast` 掃描 `src/trpg/`：(1) `trpg.engine` 與 `trpg.shared` 的依賴方向符合 CLAUDE.md 守則 5；(2) `engine`、`shared`、`content`、`skillgen`、`sim`、`roguelite` 內沒有 `import random`／`from random import`／`uuid4`／`time.time` 等禁用呼叫。這個測試是 import-linter 的保底，必須在本工作區實際執行並通過 |
| `tests/cli/test_cli.py` | `--version`；`rng` 子命令輸出與 `Rng` 直接呼叫一致；`content check` 成功與失敗情境 |

### 3.8 檢查腳本與 CI

**`scripts/check.py`**（跨平台，使用者在 Windows 也能跑）：依序執行
1. `ruff check .`
2. `ruff format --check .`
3. `mypy`
4. `lint-imports`（未安裝時印出黃色警告並略過，不算失敗）
5. `pytest`

任一步失敗就以非零代碼結束，最後印出各步驟結果摘要（繁體中文）。腳本以 `sys.executable -m <tool>` 或 `shutil.which` 找工具，並在 docstring 說明通常用法是 `uv run python scripts/check.py`。

**`.github/workflows/ci.yml`**：在 `push` 與 `pull_request` 時，於 `ubuntu-latest` 與 `windows-latest` 上、Python 3.12 與 3.13 的矩陣中，用 `astral-sh/setup-uv` 安裝 uv、`uv sync`、執行 `uv run python scripts/check.py`。（本工作區無法實際跑 CI，寫好即可，PM 之後推上 GitHub 時驗證。）

### 3.9 文件

- **`README.md`**（繁體中文）：專案一句話介紹、目前進度（Phase 0）、在 **Windows** 上的安裝與執行步驟（安裝 uv 的官方指令、`uv sync`、`uv run python scripts/check.py`、`uv run trpg rng --seed 42 --count 5`）、文件索引（指向 `CLAUDE.md` 與 `docs/`）。
- **`docs/phases/Phase0報告.md`**：完成報告，格式見第 6 節。
- 不要修改 `docs/專案計畫.md` 與 `CLAUDE.md`；若認為需要修改，寫在報告的「待 PM 決定」。

### 3.10 Git

- 在 `/home/claude/LLM-MMO-TRPG` 執行 `git init -b main`（若尚未初始化）。
- 依邏輯分成數個 commit（例如：專案設定、亂數產生器、共用型別、內容載入、CLI、CI 與文件），每個 commit 都應該能通過當時已存在的測試。
- commit 訊息第一行用英文、祈使句（例如 `Add xoshiro128** RNG with splitmix64 seeding`），內文可用中文；每個 commit 訊息結尾必須加上這兩行：

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RbaPp5tHxS9WU3o79xe213
```

- 不要設定 remote、不要 push。

---

## 4. 驗收條件

PM 會逐條檢查：

1. `ruff check .` 與 `ruff format --check .` 無錯誤。
2. `mypy`（strict）無錯誤。
3. `pytest` 全部通過（hypothesis 測試在本工作區被略過屬預期）。
4. 三組亂數測試向量來自實際編譯執行的 C 參考程式，且 Python 實作與之一致。
5. 相同種子產生相同序列；狀態序列化往返後序列一致；`fork` 確定且不影響父串流。
6. `tests/test_architecture.py` 能抓到違規：在報告中說明你曾暫時加入一行 `import random` 到 `trpg/engine/__init__.py` 確認測試會失敗，然後移除。
7. `trpg content check` 成功；把 `content/elements.yaml` 改壞時以非零代碼結束且訊息含檔案路徑。
8. `scripts/check.py` 在本工作區可執行，結果與上述一致（lint-imports 顯示略過警告）。
9. git 歷史乾淨：工作樹無未提交變更、沒有編譯產物或快取被 commit、每個 commit 皆帶規定的結尾兩行。
10. 沒有實作範圍外的東西（戰鬥、技能、LLM、FastAPI、前端）。

---

## 5. 實作提示

- 先寫亂數產生器與它的 C 參考程式，確認向量一致後再做其他項目。
- 拒絕取樣的參考做法：區間大小 `n`，取 `limit = (2**32 // n) * n`，抽到 `≥ limit` 就重抽。區間超過 2³² 時，用多個 u32 組成更大的整數再套同樣邏輯。
- `fork` 的參考做法：以 FNV-1a 64 計算 `label` 的雜湊，與父串流目前狀態組合（例如把 4 個狀態字與雜湊一起餵進 splitmix64）得到新種子，再建立新的 `Rng`。只要確定、穩定、不推進父串流即可，做法寫進 docstring。
- 中文 docstring 與註解可以，但識別字一律英文。
- 遇到工具在本工作區無法執行的情況，不要花時間繞過網路限制；照規格寫好設定，並在報告中說明。

---

## 6. 完成報告格式（`docs/phases/Phase0報告.md`）

```markdown
# Phase 0 完成報告

## 摘要
（三到五句：做了什麼、驗收是否全部通過）

## 驗收條件逐條結果
| # | 條件 | 結果 | 證據（指令與輸出摘要） |

## 實際執行的驗證指令
（可直接複製貼上重現）

## 與規格的差異
（沒有就寫「無」）

## 待 PM 決定
（規格沒寫清楚、或你認為計畫需要調整的地方）

## 給下一階段的備註
（Phase 1 實作者需要知道的事）
```

完成後在最終回覆中提供：commit 列表（`git log --oneline`）、驗收結果摘要、以及「待 PM 決定」的項目。
