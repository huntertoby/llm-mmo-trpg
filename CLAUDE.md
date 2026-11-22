# CLAUDE.md

> **與使用者的所有對話一律使用繁體中文（zh-TW）**，包括進度回報、驗收報告與提問；程式碼、指令與識別字維持英文。

LLM 說書人開放世界 MMO-TRPG。核心初衷：**LLM 為每位玩家長出獨一無二、有主題、有協同的 build；多樣的格子戰場讓每個 build 都有發光的時刻。** 第一里程碑是單人 roguelite 原型（Phase 0–4）。

## 文件索引

本專案照 pm-workflow plugin 的通用守則運作（每個 session 開始時自動注入；設定在 `.claude/pm-workflow.json`）。**文件位置以本節為準**，不用 plugin 預設的 `docs/handoff/`、`docs/stages/`、`docs/決定紀錄.md`：

- 交接文件：`docs/<角色>PM交接.md`（`專案PM交接.md`、`玩法PM交接.md`、`開發PM交接.md`、`美術PM交接.md`）。plugin 的「總 PM」＝專案 PM，「設計 PM」＝玩法 PM。
- 階段規格與報告：`docs/phases/`（`PhaseN計畫.md`、`PhaseN報告.md`）。
- 決定紀錄：`docs/玩法決定紀錄.md`（舊的在 `docs/archive/玩法決定紀錄_1-138.md`）。
- 上手筆記：`docs/dev/上手-<區域>.md`、`docs/art/上手-畫法.md`。

| 文件 | 用途 |
|---|---|
| `docs/專案計畫.md` | 總覽、守則、決定事項與開發階段（設計的真相來源，細節在 `docs/design/`） |
| `docs/專案PM交接.md` | 專案 PM 的角色、組織圖、各 PM 的分工與傳話規則、整體進度（專案 PM 接手時先讀） |
| `docs/開發PM交接.md` | 開發 PM 的工作流程與目前進度（開發 PM 接手時只讀這份即可） |
| `docs/玩法PM交接.md` | 玩法 PM 的工作方式、玩法決定總表與待辦（玩法 PM 接手時先讀） |
| `docs/玩法決定紀錄.md` | 決定索引（#1～#138）＋ #139 起的新決定＋代決附錄；#1～#138 的原話在 `docs/archive/玩法決定紀錄_1-138.md` |
| `docs/美術PM交接.md` | 美術 PM 的工作方式與美術提案、結論（美術 PM 接手時先讀；樣張在 `docs/art/`） |
| `docs/art/` | 美術樣張、風格比較、給開發 PM 的移植需求與檢查清單 |
| `docs/design/` | 依主題拆分的設計細節，實作時只讀階段規格指定的檔案 |
| `docs/phases/PhaseN計畫.md` | 第 N 階段的實作規格與驗收條件，實作時以此為準 |
| `docs/phases/PhaseN報告.md` | 進行中階段的完成報告（由實作者撰寫）；已結案的在 `docs/archive/phases/` |
| `docs/部署說明.md` | 開服、Tunnel、Discord Bot、備份與季末重置（macOS 與 Windows） |
| `docs/phases/整理提案-程式.md` | 文件與程式整理提案（第 1 節已做完；第 2 節 I1～I8、R1～R6 待排）；整理完後刪這列 |
| `docs/archive/` | 歸檔：`phases/`（已結案報告，索引 `phases/README.md`）、`art/`（已結案美術檢查）、`交接歷史-開發PM.md`、舊版計畫、玩法決定紀錄 1～138、搬出的設計原文；只供查脈絡 |

## 角色分工

通用的角色與決策規則見 plugin 守則；以下只列本專案特有的部分。

- **使用者**：最終決策者。已寫入 `docs/design/` 的決定也只有使用者能改；不在對話裡口頭放寬，要改就由玩法 PM 附使用者原話改設計文件（2026-10-24 使用者同意）。
- **專案 PM**（＝總 PM）：見 `docs/專案PM交接.md`。
- **玩法 PM**（＝設計 PM）：規則、技能、build、世界觀；使用者說「好 寫入」後才寫 `docs/design/`。
- **開發 PM**：階段規格寫在 `docs/phases/`；審查流程見 `docs/開發PM交接.md` 6.5。
- **美術 PM**：樣張在 `docs/art/`，在自己的分支工作，由開發 PM 併進 main。
- **實作者**：規格沒寫到、或與 `docs/專案計畫.md` 衝突的地方，記在完成報告的「待 PM 決定」區。

**與 plugin 守則不同的地方（以本節為準）**
- **模型**（2026-11-18 使用者選「維持 Opus」）：PM、實作（含 `pm-workflow:implementer`，派工時指定 `model: opus`）、修 bug、審查、設計、規格、驗收、裁判，一律用 Opus 5.5。可以用 Haiku 的只有固定步驟、可以核對結果的工作：
  - 找資料用 `pm-workflow:finder`；
  - 跑檢查，只回報結束碼和失敗摘要；
  - 照清單截圖存檔；
  - 跑量測腳本並收集輸出；
  - 重產夾具、快照；
  - 搬檔，搬完用 diff 核對。
- **不用 `local_scan`**（使用者原話「那就直接不要了」）：找程式碼派 `pm-workflow:finder`，或用 grep。

## 實作守則（精簡自 `docs/專案計畫.md` 第 0 節）

1. **規則引擎是純函式且確定性**：`resolve(state, action) → (state, events, pending)`，亂數狀態存放在戰鬥狀態內，「初始狀態 ＋ 動作列表」即可完整重播。相同種子與輸入必得相同結果。引擎內禁止呼叫 LLM、讀取時間、使用 `random` 模組全域函式、使用 `uuid4`。
2. **確定性的 Python 細節**：只用 `trpg.shared.rng.Rng`（由戰鬥狀態內的 `rng_state` 還原）；需要順序時一律排序，不依賴 `set` 迭代順序或內建 `hash()`（字串 hash 每次執行不同）；數值結算以整數為主，百分比用整數千分比（‰）或 `Fraction`。
3. **LLM 只能提議，不能裁決**：LLM 輸出先經 pydantic 驗證，再由引擎檢查合法性。LLM 沒有任何能直接修改數值、產生物品或資源的工具。
4. **內容即資料**：原語、形狀、骨架、物件、互動表、地圖、詞條、印記、共鳴等都放在頂層 `content/`（YAML／JSON），以 pydantic schema 驗證；新增內容不需改引擎程式。
5. **模組依賴方向**：`trpg.engine` 不得匯入 `trpg.llm`、`trpg.narrative`、`trpg.api`、`trpg.roguelite`、`trpg.sim`、`trpg.skillgen`、`trpg.cli`；`trpg.shared` 不得匯入任何其他 `trpg` 子套件。由 import-linter 與 `tests/test_architecture.py` 檢查。
6. **LLM 呼叫一律經過 `LLMClient` 介面**，並提供 `MockLLMClient`；所有測試不需網路與 API 金鑰。模型 ID 寫在設定檔。
7. **玩家輸入一律視為資料**，包在 `<player_input>` 標籤中，絕不拼接進指令區。
8. **每個階段都要有自動化測試**；與技能、數值、平衡相關的變更，不跑模擬、不量平衡，有疑慮記進 `docs/design/平衡待查.md`（2026-11-21 使用者選「改成記平衡待查」）。
9. 介面與敘事文字用 **繁體中文（zh-TW）**；程式碼、識別字、資料欄位、commit 訊息的第一行用英文。
10. 只做當前階段規格內的事；標示為「後期」的內容不要實作，但設計不可擋住它們。
11. **節省 token 與時間**（2026-11-02 更新，使用者：「好那都改 寫入」；2026-11-04 放寬 agent 數與全量頻率，使用者：「放寬、排」「同意，改第 11 條」）：開發中只跑**直接相關**的測試檔（`uv run pytest -q tests/<路徑> -x`，平行最多 `-n 8`），CLI 輸出快照與大範圍測試只在交件前跑一次；每次 commit 與每段合併只跑 `ruff check`、`ruff format --check`、`mypy`、`lint-imports`、相關測試與一場重播；**一般的完整檢查交給 push hook（每次推到程式、測試、資料時自動跑；只改 `.md` 文件的推送略過），PM 不另外手動跑全量；階段結束審查前跑一次 `scripts/check.py --full`（含 slow 測試）**（2026-11-21 使用者選「拿掉 PM 手動那次」「只改文件就不跑」）；實作 agent 交件前，**全部 commit 之後**在自己的 worktree 跑一次 `uv run python scripts/check.py`（內含看門狗、全部非 slow 測試；2026-11-21 使用者：「改成一次跑完」），通過會寫下這份內容的通過戳記；合併後內容沒變時 push hook 看到戳記就不再重跑完整檢查，只跑前端建置（2026-11-21 使用者：「拿掉第二次重複的測試」）。合併時若 main 已有別的改動，內容不同、hook 照常重跑；開發中仍只跑相關測試；待決事項中的原型數值與解讀類，agent 照最保守的預設直接做完並寫進報告，PM 的確認累積到下一段順手改、不另開收尾段（規則類照舊先問）；**同時進行的 agent 最多 4 個，平行的 agent 不可改同一批檔案**；**全部測試（`scripts/check.py`、hook 的 push 檢查）同一時間只跑一份**，平行的 agent 交件前要錯開，由開發 PM 排順序（2026-11-21 使用者：「好，請開發 PM 錯開跑」）。大型模擬（`trpg sim completion`／`matrix` 全量）除非規格要求，否則不跑。數值由使用者自己在數值工坊調：PM 與 agent 不試數值、不量平衡，有疑慮記進 `docs/design/平衡待查.md`（2026-11-21 使用者選「改成記平衡待查」）。
12. **複雜度**：ruff `C901` 上限 15（另有 `PLR0911／0912／0915`）。超標時先拆函式；真的無法拆（例如單一事件分派迴圈）才加 `# noqa`，並在完成報告中逐一列出理由。
13. **保留的埠**：預覽伺服器不要用 8000（使用者）或 8001（本機 LLM）埠（2026-10-24 使用者同意）。只結束自己啟動的程序（plugin 守則）。

## 技術選型

Python 3.12＋（`requires-python >= 3.12`）、uv、pydantic v2、pytest、hypothesis、ruff、mypy（strict）、import-linter；伺服器 FastAPI（Phase 3 起）；前端 React ＋ PixiJS（Phase 3 起）。

## 專案結構

```
src/trpg/   shared/ engine/ content/ skillgen/ sim/ llm/ narrative/ roguelite/ api/ cli/
content/    資料檔
tests/      對應 src/trpg/ 的測試
docs/       計畫、階段規格與報告（archive/ 是歸檔）
scripts/    check.py（本機完整檢查）等
client/     前端（Phase 3 起）
```

## 常用指令

```bash
uv sync                          # 安裝相依
uv run python scripts/check.py   # ruff、格式、mypy、import-linter、pytest 全部跑一次
uv run pytest -n auto            # 平行跑全部測試（單一檔案時不用 -n）
uv run trpg --help               # CLI
export PATH="$HOME/.local/bin:$PATH"   # macOS：uv 裝在 ~/.local/bin，每個 shell 先加進 PATH
pnpm -C client <cmd>             # 前端指令（Node 24 以下也可用 corepack pnpm；Node 25 起 npm install -g pnpm）
# 預覽伺服器不用 8000（使用者）／8001（本機 LLM）埠
```
