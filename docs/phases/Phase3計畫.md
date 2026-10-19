# Phase 3 計畫：網頁客戶端 ＋ roguelite 循環

> 範圍與驗收見 `docs/專案計畫.md` 第 14 節「Phase 3」（含 🎮 戰鬥手感檢查）。前端技術見 `docs/design/12-技術與結構.md`；roguelite 循環見 `docs/design/07-角色成長.md` 7.1。
> 本檔先寫總覽與 **Phase 3-1**；之後各段的規格在前一段驗收後補上（第 4 節起）。

---

## 0. PM 決定（使用者已同意，2026-10-19）

### 0.1 拆法（六段，每段約 30–45 分鐘）

| 段 | 內容 | 模型 |
|---|---|---|
| **3-1** | 整理：依陣營過濾的戰場視圖與事件、事件與技能卡片的中文描述搬出 CLI、`Pending` 補欄位與序列化往返 | sonnet |
| 3-2 | FastAPI 本機 API：建立戰鬥、送動作、預覽、回應反應詢問、讀紀錄 | opus |
| 3-3 | 前端骨架：Vite ＋ React ＋ PixiJS（TypeScript）；格子、高度、表面、物件、單位渲染；點選移動與攻擊 | opus |
| 3-4 | 戰鬥 UI：技能範圍與連鎖預覽、環境預告、反應詢問視窗、HUD、戰鬥紀錄、隊友快捷按鈕 | sonnet |
| 3-5 | roguelite 循環：一輪流程、地圖與遭遇抽選、升級三選一（隨機組合器）、本機存檔 | opus |
| 3-6 | 收尾：網頁與 CLI 同種子同輸入同結果；PM 在瀏覽器試玩（戰鬥手感檢查） | sonnet |

### 0.2 設計決定

| # | 問題 | 決定 |
|---|---|---|
| A | 玩家操控誰 | 玩家只操控 **1 名主角**；隊友由效用 AI 控制，玩家用快捷按鈕下戰術指令。隊友先從現有 12 個 build 隨機抽 2 個 |
| B | 一輪長度 | 試玩版 **5 場 ＋ Boss**；場數寫在資料檔，之後可調（設計文件 7.1 的 8–10 場是目標值） |
| C | 升級選項 | 3 選 1、可跳過；其中 1 個為「偏離路線」。沒有傾向向量前，「偏離路線」＝縮放屬性與主角目前最高屬性不同 |
| D | 敵人的陷阱／被動／反應 | 試玩版 **先不給**，試玩後再決定（`PM交接.md` 第 5 節） |
| E | 存檔格式 | **戰鬥中也可存**：存「戰鬥初始狀態 ＋ 動作與決定列表」，讀檔時重播；一輪進度（角色、技能、層數、種子）另存 |
| F | 技能進化／重骰候選（7.1） | 只做 **重骰候選**（一輪中段與 Boss 前各一次）；技能進化需要 LLM，移到 Phase 4 |

### 0.3 技術決定

- 後端 **FastAPI**（使用者確認，不用 Django）：引擎資料模型是 pydantic，可直接當 API 格式；Phase 6 的 WebSocket 內建。
- 前端 React ＋ PixiJS ＋ Vite ＋ TypeScript，套件管理用 pnpm（以 `corepack enable` 啟用；使用者電腦已有 Node 24）。
- 美術用色塊與簡單圖示；戰鬥敘事用 3-1 搬出的模板文字。

### 0.4 2E-3 報告「待 PM 決定」的處理（沿用 `PM交接.md` 3.2，已接受）

| # | 項目 | 決定 |
|---|---|---|
| 1 | 放置陷阱時同格被拒會洩漏隱藏陷阱的存在 | 接受；目前只有玩家放陷阱（決定 D） |
| 2 | 放置者倒下或逃離時其陷阱全部移除 | 接受 |
| 3 | 傳送不觸發陷阱，步行與強制位移會 | 接受 |
| 4 | 施放者型 `add_stack` 要命中才累積 | 接受 |
| 5 | 目標型層數到期那一輪回合開始時清空 | 接受 |
| 6 | 陷阱超過觸發深度上限時留在原地、不結算 | 接受 |
| 7 | 陷阱觸發後被定身或暈眩則移動中止 | 接受 |
| 8 | 陷阱、終結技、AI 陷阱機率等初值 | 平衡階段 |
| 9 | 矩陣報表沒有 `trigger_limit` 欄位 | 接受 |
| 10 | 傷害標籤改為「（格擋/加成 ×x）」 | 接受 |

### 0.5 Phase 3 要處理的既有約定

- 滑倒停在友軍格時退回最近空格，以 `teleport` 事件表示 → 客戶端動畫要支援（3-3／3-4）。
- 陷阱只對放置者陣營顯示（CLI 用 `^`）→ 3-1 的視圖與事件過濾。
- `pending`／`resume` 的反應詢問要有 UI → 3-1 補資料、3-4 做視窗。

### 0.6 3-1 報告「待 PM 決定」的處理（PM 決定，2026-10-19）

| # | 項目 | 決定 |
|---|---|---|
| 1 | 藉機攻擊詢問時 `trigger_event_seq` 為 `None`（移動事件尚未發出） | 接受；UI 用 `trigger_unit_id` 顯示即可，不改事件順序 |
| 2 | 他方單位在視圖中不列技能，冷卻不列陷阱技能 | 接受（保守、不洩漏陷阱）；試玩時若想看敵方技能，再改成只隱藏陷阱技能 |
| 3 | 敵方法力、耐力、狀態、層數完整給出 | 接受（TRPG 公開資訊） |
| 4 | `filter_events` 傳最新狀態 | 接受；3-2 API 依此呼叫 |
| 5 | `TriggerLimitReached` 以技能有 `trap` 欄位判斷 | 接受 |
| 6 | 不升 `LOG_FORMAT` | 接受 |
| 7 | 多加 `Pending.hp_cost_permille` | 接受，保留 |
| 8 | `SkillCard` 欄位為中文字串 | 3-2 視需要加英文代碼欄位（例如 `skeleton_id`、`rarity_id`） |
| 9 | `cli/skills.py` 不再 re-export | 接受 |
| 10 | CLI 快照以雜湊儲存，`UPDATE_CLI_SNAPSHOTS=1` 重錄 | 接受 |

### 0.7 3-2 報告「待 PM 決定」的處理（PM 決定，2026-10-19）

| # | 項目 | 決定 |
|---|---|---|
| 1 | 目前內容沒有 `prompt` 反應，網頁上不會出現反應詢問 | 3-4 做「反應規則設定」（第 14 節原本就列在 Phase 3 範圍）：主角的每個反應可設為自動／詢問／關閉，預設自動；需要的引擎欄位一併加（設定存在單位狀態或 setup，可重播） |
| 2 | `/log` 含完整內部狀態、戰鬥中可讀 | 接受；只綁本機，是除錯與重播工具。Phase 6 多人時再限制 |
| 3 | 戰術指令改用 `CommandedAI.issue` 直接下達，下一次我方決策即生效 | 接受（比規格寫法更好） |
| 4 | `awaiting` 多 `"stalled"` | 接受 |
| 5 | 只接受 10 張正式地圖；未知地圖或 build 回 422 | 接受 |
| 6 | `ally_builds` 給了就不補隊友；`max_rounds` 預設 30、上限 200；天氣與部署不開放 | 接受；部署階段在 3-4 或 3-5 視需要再開 |
| 7 | 開場事件移除 `seed`；他方陷阱技能動作清掉目標 | 接受 |
| 8 | 預覽只有數字，不含模擬事件 | 3-4 做連鎖預覽時加過濾後的事件 |
| 9 | `legal_actions` 最多約 113 個、回應最大約 50 KB；`unit_moved` 沒有中文描述 | 接受；前端自行彙總步行 |
| 10 | 工作階段無上限、不過期；保留 httpx（只略過棄用提示） | 接受 |

### 0.8 3-3 報告「待 PM 決定」的處理（PM 決定，2026-10-19）

PM 驗收：`check.py` 全過（1587 測試＋前端 30 測試）；在內建瀏覽器以油庫、火焰流打完一場（點敵人攻擊、灰燼誓約點燃木箱與火焰蔓延、結束回合到全滅），下載的紀錄以 `trpg battle replay` 重播通過（103 個動作）。

| # | 項目 | 決定 |
|---|---|---|
| 1 | 中文名稱對照寫在前端 `glossary.ts`，要手動同步 | 3-4 加 `/api/glossary`（由 content 產生），前端改用它 |
| 2 | 傳送類技能讓「其他動作」多達數十項 | 3-4 的技能 UI 解決 |
| 3 | `StepOut.events` 前端手寫窄化型別 | 接受 |
| 4 | 有預設值的欄位前端另宣告為可省略 | 接受 |
| 5 | 請求失敗時顯示 `detail` 並重新 GET | 接受 |
| 6 | 伺服器事件文字同名敵人分不出來 | 接受（敵人名稱已帶編號）；試玩時有問題再改 |
| 7 | 倒下單位淡化留在原格；援軍不播動畫 | 接受 |
| 8 | 種子輸入上限 2⁵³−1 | 接受 |
| 9 | `client/dist` 位置由原始碼路徑推出 | 接受；打包時再改 |
| 10 | pnpm 提示 pixi.js agent skills 待核准 | 不核准，忽略 |

---

## 1. 範圍外（整個 Phase 3）

- LLM（技能生成、指揮官、命名、文字指令）—— Phase 4。
- 平衡調整（勝率、數值、AI 權重）—— 平衡階段；只記錄觀察。
- 召喚、改寫規則型等未補模板（`PM交接.md` 3.1.1）。
- 帳號、多人、資料庫、部署到網路上；只做本機（`127.0.0.1`）。

## 2. 工作環境（每段共用）

- 在使用者的 Windows 電腦上執行（Git Bash，Linux 寫法）。
- 開發中只跑相關測試檔（`uv run pytest -q tests/<路徑> -x`）；commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**完整的 `uv run python scripts/check.py` 只在子階段最後跑一次**。
- 每完成一個交付項目就 commit。不要 push。
- 修改既有測試的期望值時，報告逐一列出原因。
- 不跑 `trpg sim completion`／`matrix` 全量（PM 驗收時自己跑）。
- 若事件 schema 必須改，可以升 `LOG_FORMAT`，報告說明；**能不改就不改**。

---

## 3. Phase 3-1｜視圖過濾、描述模組、Pending 序列化

目標：讓之後的 API 能安全地把戰場與事件交給某一方的玩家，並能用中文描述事件與技能，而且不依賴 `trpg.cli`。**不新增遊戲規則，CLI 輸出不變。**

### 3.1 依陣營過濾的戰場視圖 `project_for`

- 新模組（例如 `trpg/engine/view.py`）：純函式 `project_for(state: BattleState, team: Team) -> BattleView`。
- `BattleView` 是 pydantic 模型（frozen、`extra="forbid"`），之後直接當 API 回應。內容至少包含：地圖尺寸與每格（高度、地形、表面）、物件、單位（位置、陣營、HP／護盾／法力／耐力、AP 與移動、狀態與剩餘回合、層數、冷卻、反應是否可用）、先攻順序與目前行動者、輪數、天氣、勝利條件、戰鬥是否結束與勝方、**`team` 看得見的陷阱**、目前的反應詢問（只有 3.3 的公開欄位）。
- **不可包含**：`rng_state`、`seed`、`PendingResolution` 的內部欄位（`base_state_json`、`action_json`、`decisions`、`events_emitted`）、其他陣營的陷阱、`ruleset` 本體。
- 用既有的 `trpg.engine.traps.visible_traps`，不要重寫一份陷阱可見性邏輯。
- 確定性：相同狀態與陣營 → 相同 JSON（集合類欄位排序）。
- 測試：敵方放了陷阱的狀態，我方視圖的 JSON 裡找不到該陷阱位置與技能 ID；放置者那一方看得到；JSON 不含 `rng_state`、`base_state_json` 等字串；暫停中的狀態可以產生視圖。

### 3.2 依陣營過濾事件 `filter_events`

- 純函式 `event_visible_to(event, state_or_context, team)` 與 `filter_events(events, team, ...) -> list[EventBase]`（簽名可調，需要的話帶入戰鬥狀態以查技能類型）。**不在 `EventBase` 新增欄位**，避免改紀錄格式。
- 規則：
  - `TrapPlaced`、`TrapExpired`：只給放置者陣營。
  - 放陷阱技能的 `SkillUsed`：其他陣營看到的版本 `tiles` 為空（回傳替換後的複本），但「誰用了哪個技能」照樣看得到。
  - 由隱藏陷阱引起的 `TriggerLimitReached`（2E-3 #6：陷阱留在原地）：只給放置者陣營。
  - `TrapTriggered` 與之後的效果事件：所有人可見（陷阱已曝光）。
  - 其他事件：所有人可見。
- 規則用註冊表或小函式表示，不要寫長 isinstance 鏈。
- `seq` 保留原值（過濾後會跳號，這是預期的），在 docstring 說明。
- 測試：上述每條規則各一個情境；一場含陷阱的完整戰鬥，對非放置者陣營過濾後的事件 JSON 不含任何未觸發陷阱的位置。

### 3.3 `Pending` 補欄位

- `Pending.kind` 改為 `Literal["reaction"]`（目前只有這種；之後新增種類時擴充）。`PendingResolution.kind` 同步。
- `Pending` 新增：
  - `skill_id: str | None`：以反應技回應時為該技能 ID，一般反應規則為 `None`。
  - `trigger_event_seq: int | None`：引發這次詢問的事件 `seq`（找不到合適事件時為 `None`，報告說明）。
  - 代價摘要：例如 `stamina_cost: int`、`mana_cost: int`（依實際代價種類，至少要讓 UI 能顯示「接受要付出什麼」）。
- `PendingResolution` 一併存這些欄位，`resume` 後的新 `Pending` 也要帶。
- 若這會改變存檔的戰鬥狀態 JSON 結構，視需要升 `LOG_FORMAT` 並說明。
- 測試：**序列化 → 反序列化 → resume 往返**：在暫停狀態上 `state_to_json` → `state_from_json` → `resume`，結果（狀態 JSON 與事件）和直接 `resume` 完全相同；接受與拒絕各一次；連續兩次詢問的情境一次。

### 3.4 描述模組搬到 `trpg.narrative`

- 把 `cli/render.py` 的 `describe_event` 與它用到的輔助函式搬到 `trpg.narrative`（例如 `narrative/events.py`），改成 `dict[type[EventBase], Callable]` 註冊表；移除其 `# noqa: C901, PLR0911, PLR0912`。沒有對應的事件類型回傳 `None`（與現狀相同）。
- 把 `cli/skills.py` 的技能卡片描述（`shape_summary`、`scaling_label`、`scaling_detail`、`mastery_text`、`effect_summary` 及其 `_effect_core`／`_stack_core`／`_trap_core`、`_condition`、`_cost_summary`）搬到 `trpg.narrative`（例如 `narrative/skills.py`），改為公開函式；`_effect_core` 的 noqa 能拆就拆。另提供 `skill_card(library, skill, ...) -> SkillCard`（pydantic：名稱、骨架、AP／代價、範圍、效果列表、條件、縮放、專精），給網頁的技能卡片用。
- `trpg.cli` 改為從 `trpg.narrative` 匯入；**CLI 輸出逐字不變**（以既有 CLI 測試證明，並加一個 `trpg battle` 輸出前後一致的快照測試，若尚無）。
- `pyproject.toml` import-linter 新增合約：`trpg.narrative` 不得匯入 `trpg.cli`、`trpg.api`、`trpg.roguelite`、`trpg.sim`；`tests/test_architecture.py` 同步。
- 檢查是否有測試直接匯入被搬走的私有函式，一併改匯入路徑。
- `engine/preview.py` 的 `_outcome` 與 `sim/metrics.py` 的長 isinstance 鏈 **不在本段**（之後的整理再處理）。

### 3.5 驗收條件（3-1）

1. `project_for` 的輸出不含 3.1 列出的禁止欄位，且對各陣營的陷阱可見性正確（測試名稱為證）。
2. `filter_events` 的四條規則各有情境測試；完整含陷阱戰鬥的過濾結果不洩漏未觸發陷阱位置。
3. `Pending.kind` 為 Literal，新增的欄位在 `resolve` 與 `resume` 都正確；序列化往返測試通過。
4. `describe_event` 與技能卡片描述位於 `trpg.narrative`，`trpg.cli` 中不再定義；`describe_event` 不再有複雜度 noqa。
5. CLI 輸出不變（既有測試全過；新增或既有的快照測試為證）。
6. import-linter 新合約生效（`lint-imports` 與 `tests/test_architecture.py`）。
7. `uv run python scripts/check.py` 全過；複雜度類 noqa 總數不增加（報告列出前後數字）。
8. `trpg battle --map <任一張> --seed 7 --log-json f` 與 `trpg battle replay f` 一致。

---

## 4. Phase 3-2｜FastAPI 本機 API

目標：讓瀏覽器（3-3 起）能透過 HTTP 打完一場戰鬥：玩家操控 1 名主角，其餘單位由效用 AI 自動行動。**不新增遊戲規則，不做前端。** 架構與 API 格式之後不易改，請以清楚、可擴充為優先。

### 4.1 套件與啟動

- `uv add fastapi uvicorn`，測試用 `httpx`（dev 相依）。
- 程式放 `src/trpg/api/`（例如 `app.py` 建立 `FastAPI`、`sessions.py` 戰鬥工作階段、`schemas.py` 請求／回應模型、`routes/`）。
- CLI 新增 `trpg serve [--host 127.0.0.1] [--port 8000]`，以 uvicorn 啟動；預設只綁 `127.0.0.1`。
- import-linter 新增合約：`trpg.api` 不得匯入 `trpg.cli`；`tests/test_architecture.py` 同步。`trpg.cli` 可以匯入 `trpg.api`（只為了 `serve`）。
- 若 CLI 與 API 都需要的組裝邏輯（例如 `default_lineup`、`--ally-build` 補隊友的寫法、`build_commanded_ai`）目前在 `trpg.cli`，搬到 `trpg.api` 與 `trpg.cli` 都能匯入的地方（例如 `trpg.sim` 或新的小模組），CLI 行為不變（3-1 的 CLI 快照測試要過）。

### 4.2 戰鬥工作階段 `BattleSession`

- 記憶體內的工作階段表（`dict[str, BattleSession]`），ID 由伺服器產生（伺服器層可以用 `uuid4`／`secrets`；**引擎內仍禁止**）。重啟伺服器後工作階段消失（存檔是 3-5）。
- 工作階段保存：`setup`、`seed`、**步驟列表**（動作與決定，與 `BattleLog.actions` 同格式）、目前狀態、目前的 `Pending`、玩家下過的戰術指令紀錄、主角單位 ID。**目前狀態必須可由 `setup ＋ seed ＋ 步驟列表` 以 `trpg.engine.runner.replay` 重現**（3-5 的存檔就存這些）。
- 每個工作階段一把 `threading.Lock`：同一場戰鬥的請求依序處理。
- **主角**：我方第一個單位（`hero_build` 指定的那個）。其餘我方單位與敵方單位由效用 AI 控制。
- **自動推進**：玩家送出動作或決定後，伺服器持續結算，直到 (a) 輪到主角且主角有 `EndTurn` 以外的合法動作，(b) 出現主角的 `Pending`，或 (c) 戰鬥結束。與 `run_battle` 相同：只剩 `EndTurn` 時自動結束回合；非主角的 `Pending` 用 `accept_all`。建立戰鬥時也先推進到第一次輪到主角。
- 自動推進要有上限（例如沿用 `DEFAULT_MAX_ACTIONS`），超過時回 500 並保留工作階段。
- 推進迴圈請與 `run_battle` 共用邏輯或至少共用判斷函式，不要複製一份會漂移的版本。

### 4.3 隊友快捷指令

- 玩家可對我方 AI 隊友下達戰術指令（`trpg.engine.ai.orders` 的 `OrderSet`：集火、守位、撤退、保護、利用環境）。
- 做法：我方使用 `CommandedAI`，指揮官是一個「回傳玩家目前指令」的物件；玩家更新指令後下一次我方 AI 決策即生效。敵方指揮官設定沿用 CLI 預設（無）。
- 指令以 `validate_order` 驗證，無效回 422 並附中文原因。
- 指令紀錄存在工作階段（含下達時的輪數）；`BattleLog.orders` 匯出時帶上。
- 重播只重播動作（與現在相同），所以指令不影響重播一致性。

### 4.4 端點（JSON；路徑可微調，報告列出最終版本）

| 方法 | 路徑 | 內容 |
|---|---|---|
| GET | `/api/maps` | 地圖列表（ID、中文名、類型、尺寸） |
| GET | `/api/builds` | build 列表（ID、中文名） |
| GET | `/api/skills/{skill_id}` | 技能卡片（3-1 的 `SkillCard`；依 0.6 #8 加英文代碼欄位） |
| POST | `/api/battles` | 建立戰鬥：`map_id`、`seed`、`hero_build`、`ally_builds`（可省略，省略時同 CLI 預設補隊友）、`max_rounds`（可省略） |
| GET | `/api/battles/{id}` | 目前狀態（見下方「戰鬥回應」） |
| POST | `/api/battles/{id}/actions` | 送出主角的動作（`Action` JSON） |
| POST | `/api/battles/{id}/decision` | 回答主角的反應詢問：`accept: bool` |
| POST | `/api/battles/{id}/preview` | 預覽主角的動作（`trpg.engine.preview.preview` 的結果） |
| PUT | `/api/battles/{id}/orders` | 設定我方隊友的戰術指令（`OrderSet`；空集合＝取消） |
| GET | `/api/battles/{id}/log` | 匯出 `BattleLog`（與 `trpg battle --log-json` 同格式，可用 `trpg battle replay` 重播） |

**戰鬥回應**（建立、讀取、動作、決定共用）：
- `view`：`project_for(state, Team.ALLY)`。
- `hero_id`；`awaiting`：`"action"`／`"decision"`／`"ended"`。
- `legal_actions`：輪到主角時的合法動作（`legal_actions` 的結果，含 `EndTurn`）；其他時候為空。若數量很大，報告記下典型數量，不必在本段最佳化。
- `pending`：主角的反應詢問（3-1 的公開欄位）或 `null`。
- `steps`：本次請求推進的每一步，依序：`{actor_id, step, events}`；`events` 經 `filter_events(…, Team.ALLY)` 過濾，每個事件附 `text`（`describe_event` 的中文，`None` 時省略）。前端用來播放動畫與寫戰鬥紀錄。建立戰鬥時包含開場事件。
- 勝負與結束原因（戰鬥結束時）。

**錯誤**：不存在的戰鬥 404；不合法的動作 400（附引擎的中文訊息）；不是主角的回合、不是在等決定、戰鬥已結束 409；輸入格式錯誤 422。動作的 `unit_id` 必須是主角。

**不可洩漏**：任何回應都不得含 `rng_state`、`seed` 以外的隨機內部狀態（`seed` 只在 `/log` 匯出）、`PendingResolution` 內部欄位、敵方隱藏陷阱。預覽要用已過濾隱藏陷阱的狀態（`preview` 目前已用 `strip_hidden_traps`，確認並以測試固定）。

### 4.5 測試（`tests/api/`，用 FastAPI `TestClient`，不需網路）

- 每個端點的正常與錯誤情況（404／400／409／422）。
- **整場戰鬥**：以腳本客戶端透過 API 打完一場（主角每次用 `UtilityAI` 對回傳的狀態選動作，或固定選第一個非 `EndTurn` 的合法動作；遇到詢問時交替接受與拒絕），至少 2 張地圖；結束後 `/log` 匯出的紀錄以 `trpg.engine.runner.replay` 重播，最終狀態 JSON 完全一致。
- **網頁與 CLI 一致**：同一份匯出紀錄用 `trpg battle replay` 驗證通過（呼叫 CLI 函式即可）。
- **確定性**：相同 `map_id／seed／builds ＋ 相同動作序列` 建立兩個工作階段，每一步的回應（去掉戰鬥 ID）完全相同。
- **不洩漏**：放了陷阱（`build_trapper` 當主角放陷阱後，以敵方視角檢查工作階段內部的過濾函式；以及我方回應中不含敵方陷阱——可用測試專用的狀態讓敵人帶陷阱）；所有回應 JSON 不含 `rng_state`、`base_state_json`。
- 戰術指令：設定集火後，紀錄的 `orders` 含該指令；無效指令 422。
- 預覽：回傳結構正確，且不改變工作階段狀態。

### 4.6 驗收條件（3-2）

1. `trpg serve` 可啟動，`GET /api/maps` 回 10 張地圖（報告附 `curl` 或 `TestClient` 輸出節錄）。
2. 4.4 的端點都存在，錯誤碼符合規定（測試名稱為證）。
3. 透過 API 打完至少 2 張地圖的整場戰鬥；匯出紀錄以 `replay` 與 `trpg battle replay` 重播一致。
4. 確定性測試通過。
5. 不洩漏測試通過。
6. 自動推進與 `run_battle` 共用邏輯（報告說明共用方式）；CLI 輸出不變（3-1 快照測試通過）。
7. import-linter 新合約生效。
8. `uv run python scripts/check.py` 全過；複雜度類 noqa 不增加（報告列出前後數字）。
9. 報告附 API 端點表（最終路徑、請求與回應的主要欄位），供 3-3 的前端使用。

---

## 5. Phase 3-3｜前端骨架：格子渲染與基本操作

目標：在瀏覽器裡看得到戰場，並能用點選打完一場戰鬥（移動、攻擊、其他動作、結束回合）。技能範圍預覽、HUD、反應設定、快捷指令按鈕等是 3-4。**後端只做 4.3 列的小改動，不改遊戲規則。** 這是前端的骨架，之後 3-4、3-5 都在上面加功能，請以清楚的結構為優先。

### 5.1 工具與專案結構

- `client/`：Vite ＋ React 18 ＋ TypeScript（`strict: true`）＋ PixiJS v8。版本用撰寫時的穩定版並鎖定（`pnpm-lock.yaml` 進 git）。
- 套件管理用 pnpm，**一律以 `corepack pnpm …` 呼叫**（不需要 `corepack enable`，避免 Windows 權限問題）；`package.json` 的 `packageManager` 欄位鎖定 pnpm 版本。
- `package.json` scripts 至少有：`dev`、`build`、`typecheck`（`tsc --noEmit`）、`test`（vitest，非 watch 模式）、`gen:api`。
- 建議結構（可調，報告說明）：`src/api/`（型別與 fetch 包裝）、`src/battle/`（純邏輯：視圖 → 繪製模型、合法動作分類、紀錄彙總）、`src/render/`（PixiJS 繪製）、`src/ui/`（React 元件）、`src/screens/`（開始畫面、戰鬥畫面）。**純邏輯與 PixiJS／React 分開**，純邏輯才能用 vitest 測。
- `node_modules/`、`client/dist/` 不進 git（檢查 `.gitignore`）。

### 5.2 API 型別

- 以 FastAPI 的 OpenAPI 產生 TypeScript 型別（例如 `openapi-typescript`）：`scripts/export_openapi.py` 把 `create_app().openapi()` 寫到 `client/openapi.json`，`corepack pnpm -C client gen:api` 產生 `client/src/api/schema.d.ts`；兩個檔都進 git。
- pytest 新增一個測試：目前 app 的 OpenAPI 與 `client/openapi.json` 相同（API 改了而沒重新產生就失敗，訊息提示要跑哪兩個指令）。
- 若有欄位在 OpenAPI 中型別不夠精確（例如 `step`、`events` 是任意 JSON），可以在 API 端補上更精確的回應模型，或在前端手寫窄化型別；報告說明。

### 5.3 畫面與操作

**開始畫面**：選地圖（`/api/maps`）、主角 build（`/api/builds`）、種子（預設隨機，可輸入）→ `POST /api/battles`。

**戰鬥畫面**：
- **格子**：俯視角方格。顏色依表面／地形（色塊即可，對照表寫成一個資料物件，之後好換）；高度以明暗加角落數字表示；牆壁、深淵、致命地形要一眼看得出來。
- **物件**：簡單形狀或文字圖示（例如油桶、木箱），可燃／已點燃有區別。
- **單位**：圓形，我方與敵方不同顏色；顯示代號（同 CLI 的 A／a）與血條；目前行動者與主角要有外框；倒下的單位淡化或移除。
- **陷阱**：`view.traps` 中的陷阱（我方看得到的）以 `^` 或圖示顯示。
- **回合資訊**：輪數、目前行動者、先攻順序列。
- **單位資訊**：滑過或點選單位時顯示名稱、HP／護盾／法力／耐力、狀態與剩餘回合（文字即可）。
- **操作**（只在 `awaiting == "action"` 時可用）：
  - 可移動的格子以 `legal_actions` 中的 `move` 動作計算（目的地＝路徑最後一格；同一格多條路徑取第一條），點選即送出。
  - 點選敵人：若有對該單位的 `attack` 動作就送出（多個時取第一個，或讓玩家選）。
  - 「其他動作」清單：列出不屬於上兩類的所有合法動作（技能、推擊、絆倒、防禦、互動、結束姿態……），每個有可讀的中文標籤（類型 ＋ 技能名或目標名；技能名用 `/api/skills/{id}` 或建立戰鬥時一次取得），點選即送出。**這樣 3-3 就能打完整場**，3-4 再換成正式的技能 UI。
  - 「結束回合」按鈕。
  - 等待伺服器回應時鎖住操作。
- **事件播放**：收到回應後依 `steps` 順序播放：`unit_moved` 做逐格移動動畫（`teleport` 直接出現在新位置；`forced` 可用較快的動畫），其他事件先不做動畫，播放完再以 `view` 更新整個畫面（**以 `view` 為準**，動畫只是過場）。可以有「略過動畫」的開關。
- **戰鬥紀錄**：右側或下方列出事件 `text`，最新在下並自動捲動；同一單位連續的步行（`unit_moved` 沒有 `text`）彙總成一行「X 移動到 (x, y)」。
- **反應詢問**：`awaiting == "decision"` 時顯示簡單的確認框（接受／拒絕，顯示 `pending` 的反應名與代價），送 `/decision`。正式視窗在 3-4。
- **結束**：顯示勝負與「再來一場」（回開始畫面）、「下載戰鬥紀錄」（`/log`）。
- 錯誤（400／409／500）以畫面上的提示顯示 `detail`，不讓畫面卡死。

### 5.4 後端的小改動

- `trpg serve` 在 `client/dist/` 存在時，同時以靜態檔提供前端（`/` 為 `index.html`，`/api/*` 不受影響）；不存在時印出提示（要先 build）。
- 開發時 Vite 的 dev server 以 proxy 把 `/api` 轉到 `127.0.0.1:8000`。
- 新增 `scripts/play.py`（給使用者一鍵試玩）：若 `client/dist` 不存在或比 `client/src` 舊就先 `corepack pnpm -C client install` ＋ `build`，然後啟動 `trpg serve` 並開瀏覽器。用 `uv run python scripts/play.py` 執行。
- `scripts/check.py` 加入前端檢查：`corepack pnpm -C client install --frozen-lockfile`（已安裝時很快）、`typecheck`、`test`；找不到 `corepack` 時印出警告並略過（不算失敗）。

### 5.5 測試

- vitest（純邏輯）：視圖 → 繪製模型（格子顏色、高度、單位位置）、合法動作分類（可移動格、可攻擊目標、其他動作與標籤）、紀錄彙總（連續步行合併、`teleport` 不合併）、座標換算（點擊位置 → 格子）。
- pytest：OpenAPI 快照測試；`trpg serve` 有 `client/dist` 時 `/` 回 `index.html`、`/api/maps` 仍正常（測試可用暫存資料夾假裝 dist）。
- 不要求瀏覽器自動化測試；PM 驗收時會在瀏覽器試玩。實作者可以用 `corepack pnpm -C client build` 成功、`trpg serve` 後 `curl /` 拿到 HTML 作為證據。

### 5.6 驗收條件（3-3）

1. `corepack pnpm -C client build`、`typecheck`、`test` 全過。
2. OpenAPI 快照測試通過；`schema.d.ts` 由腳本產生、進 git。
3. `uv run python scripts/play.py` 能建置並啟動，瀏覽器開到開始畫面（PM 驗收時確認）。
4. 在瀏覽器能選地圖、build 開戰，看得到格子、高度、表面、物件、單位、血條，能移動、攻擊、使用「其他動作」、結束回合，並打到戰鬥結束（PM 驗收時確認）。
5. 移動有逐格動畫，播放完以 `view` 為準；戰鬥紀錄顯示中文並彙總步行。
6. 網頁打完的戰鬥，下載的紀錄以 `trpg battle replay` 重播通過（PM 驗收時確認）。
7. `uv run python scripts/check.py` 全過（含前端檢查）；複雜度類 noqa 不增加。
8. 報告附畫面結構說明（元件與模組列表）與已知限制，供 3-4 接手。

---

## 9. 報告格式（每段一份：`docs/phases/Phase3-N報告.md`）

1. 完成項目與 commit 列表。
2. 驗收條件逐條：結果 ＋ 證據（測試名稱或指令輸出）。
3. 新增或移除的複雜度 noqa 與理由；noqa 總數前後。
4. 修改既有測試期望值的清單與原因。
5. 待 PM 決定（最多 10 點）。
6. 代表性輸出節錄。
