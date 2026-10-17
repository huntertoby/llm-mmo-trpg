# CLAUDE.md

LLM 說書人開放世界 MMO-TRPG。核心初衷：**LLM 為每位玩家長出獨一無二、有主題、有協同的 build；多樣的格子戰場讓每個 build 都有發光的時刻。** 第一里程碑是單人 roguelite 原型（Phase 0–4）。

## 文件索引

| 文件 | 用途 |
|---|---|
| `docs/專案計畫.md` | 完整設計與開發階段（唯一的設計真相來源） |
| `docs/phases/PhaseN計畫.md` | 第 N 階段的實作規格與驗收條件，實作時以此為準 |
| `docs/phases/PhaseN報告.md` | 第 N 階段的完成報告（由實作者撰寫） |
| `docs/archive/` | 舊版計畫，只供參考 |

## 角色分工

- **PM**（使用者與 PM agent）：決定設計、撰寫階段規格、驗收。
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

## 技術選型

Python 3.12＋（`requires-python >= 3.12`）、uv、pydantic v2、pytest、hypothesis、ruff、mypy（strict）、import-linter；伺服器 FastAPI（Phase 4 起）；前端 React ＋ PixiJS（Phase 4 起）。

## 專案結構

```
src/trpg/   shared/ engine/ content/ skillgen/ sim/ llm/ narrative/ roguelite/ api/ cli/
content/    資料檔
tests/      對應 src/trpg/ 的測試
docs/       計畫、階段規格與報告
scripts/    check.py（本機完整檢查）等
client/     前端（Phase 4 起）
```

## 常用指令

```bash
uv sync                          # 安裝相依
uv run python scripts/check.py   # ruff、格式、mypy、import-linter、pytest 全部跑一次
uv run pytest                    # 只跑測試
uv run trpg --help               # CLI
```
