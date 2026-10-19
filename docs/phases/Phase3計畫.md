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

## 5. 報告格式（每段一份：`docs/phases/Phase3-N報告.md`）

1. 完成項目與 commit 列表。
2. 驗收條件逐條：結果 ＋ 證據（測試名稱或指令輸出）。
3. 新增或移除的複雜度 noqa 與理由；noqa 總數前後。
4. 修改既有測試期望值的清單與原因。
5. 待 PM 決定（最多 10 點）。
6. 代表性輸出節錄。
