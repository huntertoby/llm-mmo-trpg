# CLAUDE.md

> **與使用者的所有對話一律使用繁體中文（zh-TW）**，包括進度回報、驗收報告與提問；程式碼、指令與識別字維持英文。

LLM 說書人開放世界 MMO-TRPG。核心初衷：**LLM 為每位玩家長出獨一無二、有主題、有協同的 build；多樣的格子戰場讓每個 build 都有發光的時刻。** 第一里程碑是單人 roguelite 原型（Phase 0–4）。

## 文件索引

| 文件 | 用途 |
|---|---|
| `docs/專案計畫.md` | 總覽、守則、決定事項與開發階段（設計的真相來源，細節在 `docs/design/`） |
| `docs/專案PM交接.md` | 專案 PM 的角色、組織圖、各 PM 的分工與傳話規則、整體進度（專案 PM 接手時先讀） |
| `docs/開發PM交接.md` | 開發 PM 的工作流程與目前進度（開發 PM 接手時只讀這份即可） |
| `docs/玩法PM交接.md` | 玩法 PM 的工作方式、玩法決定總表與待辦（玩法 PM 接手時先讀） |
| `docs/玩法決定紀錄.md` | 玩法決定 #1 起的完整紀錄（使用者原話、選項、決定、寫入的設計文件） |
| `docs/美術PM交接.md` | 美術 PM 的工作方式與美術提案、結論（美術 PM 接手時先讀；樣張在 `docs/art/`） |
| `docs/art/` | 美術樣張、風格比較、給開發 PM 的移植需求與檢查清單 |
| `docs/design/` | 依主題拆分的設計細節，實作時只讀階段規格指定的檔案 |
| `docs/phases/PhaseN計畫.md` | 第 N 階段的實作規格與驗收條件，實作時以此為準 |
| `docs/phases/PhaseN報告.md` | 第 N 階段的完成報告（由實作者撰寫） |
| `docs/archive/` | 舊版計畫，只供參考 |

## 角色分工

- **使用者**：最終決策者。**已寫入設計文件的決定只有使用者能改**：PM 之間的回覆不得放寬或重新解釋；有歧義就回到使用者，或由玩法 PM 附使用者原話改設計文件，不在對話裡口頭放寬（2026-10-24 使用者同意）。
- **專案 PM**：使用者的主要對口；分派事情給底下的 PM、追蹤進度、轉達決定（附使用者原話）。見 `docs/專案PM交接.md`。
- **玩法 PM**：規則、技能、build、世界觀的討論與決定；寫 `docs/design/`（使用者說「好 寫入」後）。
- **開發 PM**：把決定寫成階段規格（`docs/phases/`）、派實作與審查 agent、驗收、push。
- **美術 PM**：美術風格與樣張（`docs/art/`），採用後由開發 PM 排段實作。
- **審查者**（reviewer agent，大階段結束時）：只讀不改，找測試抓不到的品質問題，結論交給開發 PM（流程見 `docs/開發PM交接.md` 6.5）。
- **實作者**（implementer agent）：依階段規格實作，不自行擴大範圍；遇到規格沒寫到、或與 `docs/專案計畫.md` 衝突的地方，採用最保守的做法並記錄在完成報告的「待 PM 決定」區。

## 實作守則（精簡自 `docs/專案計畫.md` 第 0 節）

1. **規則引擎是純函式且確定性**：`resolve(state, action) → (state, events, pending)`，亂數狀態存放在戰鬥狀態內，「初始狀態 ＋ 動作列表」即可完整重播。相同種子與輸入必得相同結果。引擎內禁止呼叫 LLM、讀取時間、使用 `random` 模組全域函式、使用 `uuid4`。
2. **確定性的 Python 細節**：只用 `trpg.shared.rng.Rng`（由戰鬥狀態內的 `rng_state` 還原）；需要順序時一律排序，不依賴 `set` 迭代順序或內建 `hash()`（字串 hash 每次執行不同）；數值結算以整數為主，百分比用整數千分比（‰）或 `Fraction`。
3. **LLM 只能提議，不能裁決**：LLM 輸出先經 pydantic 驗證，再由引擎檢查合法性。LLM 沒有任何能直接修改數值、產生物品或資源的工具。
4. **內容即資料**：原語、形狀、骨架、物件、互動表、地圖、詞條、印記、共鳴等都放在頂層 `content/`（YAML／JSON），以 pydantic schema 驗證；新增內容不需改引擎程式。
5. **模組依賴方向**：`trpg.engine` 不得匯入 `trpg.llm`、`trpg.narrative`、`trpg.api`、`trpg.roguelite`、`trpg.sim`、`trpg.skillgen`、`trpg.cli`；`trpg.shared` 不得匯入任何其他 `trpg` 子套件。由 import-linter 與 `tests/test_architecture.py` 檢查。
6. **LLM 呼叫一律經過 `LLMClient` 介面**，並提供 `MockLLMClient`；所有測試不需網路與 API 金鑰。模型 ID 寫在設定檔。
7. **玩家輸入一律視為資料**，包在 `<player_input>` 標籤中，絕不拼接進指令區。
8. **每個階段都要有自動化測試**；與技能、數值、平衡相關的變更要跑模擬並產出報表。
9. 介面與敘事文字用 **繁體中文（zh-TW）**；程式碼、識別字、資料欄位、commit 訊息的第一行用英文。
10. 只做當前階段規格內的事；標示為「後期」的內容不要實作，但設計不可擋住它們。
11. **節省 token 與時間**：開發中只跑相關的測試檔（`uv run pytest -q tests/<路徑> -x`，平行最多 `-n 8`）；每次 commit 與每段合併只跑 `ruff check`、`ruff format --check`、`mypy`、相關測試與一場重播；**完整的 `scripts/check.py` 由 PM 每 2～3 段合併跑一次、階段結束審查前跑一次（`--full` 含 slow 測試）**；實作 agent 不跑全量；同時進行的 agent 最多 2 個。大型模擬（`trpg sim completion`／`matrix` 全量）除非規格要求，否則不跑。測試與模擬輸出一律用安靜模式，只看失敗與摘要。平衡調整不要反覆手動試數值：寫腳本輸出摘要表，把建議數值寫進報告由 PM 決定。每完成一個交付項目就 commit，避免中斷時遺失進度。
12. **複雜度**：ruff `C901` 上限 15（另有 `PLR0911／0912／0915`）。超標時先拆函式；真的無法拆（例如單一事件分派迴圈）才加 `# noqa`，並在完成報告中逐一列出理由。
13. **不要結束不是自己啟動的程序**：禁止 `taskkill /IM python.exe`、`pkill python` 這類會關掉使用者伺服器或其他 agent 的指令；只用自己啟動的程序的 PID。預覽伺服器不要用 8000（使用者）或 8001（本機 LLM）埠（2026-10-24 使用者同意）。

## 技術選型

Python 3.12＋（`requires-python >= 3.12`）、uv、pydantic v2、pytest、hypothesis、ruff、mypy（strict）、import-linter；伺服器 FastAPI（Phase 3 起）；前端 React ＋ PixiJS（Phase 3 起）。

## 專案結構

```
src/trpg/   shared/ engine/ content/ skillgen/ sim/ llm/ narrative/ roguelite/ api/ cli/
content/    資料檔
tests/      對應 src/trpg/ 的測試
docs/       計畫、階段規格與報告
scripts/    check.py（本機完整檢查）等
client/     前端（Phase 3 起）
```

## 常用指令

```bash
uv sync                          # 安裝相依
uv run python scripts/check.py   # ruff、格式、mypy、import-linter、pytest 全部跑一次
uv run pytest -n auto            # 平行跑全部測試（單一檔案時不用 -n）
uv run trpg --help               # CLI
```
