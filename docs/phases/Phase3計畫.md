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

### 0.9 3-4a 報告「待 PM 決定」的處理（PM 決定，2026-10-19）

PM 驗收：`check.py` 全過；在內建瀏覽器確認開場先顯示戰場再逐步播放（吊橋深淵：B → b → … → A），以真實滑鼠選「閃現」、紅框標出目標、滑過顯示預覽、點擊施放成功。

| # | 項目 | 決定 |
|---|---|---|
| 1 | HUD 沒有「保留 AP」 | 3-4b 檢查：紀錄有「結束回合，保留 1 AP」，若狀態有此值就加進視圖與 HUD |
| 2 | 每步帶完整視圖，開場回應約 600 KB | 接受（本機）；之後需要再改差異 |
| 3 | 播放停頓：移動 150 ms、其他 500 ms、結束回合 0 | 接受，試玩後調 |
| 4 | `SkillCard.cost` 對被動／反應技輸出「AP None」 | 3-4b 修後端，前端移除暫時處理 |
| 5 | glossary 加「層數」 | 接受 |
| 6 | 基本動作的選取方式 | 接受 |
| 7 | 預覽：滑過敵人預覽普攻、防抖 120 ms、快取 | 接受 |
| 8 | 跨步驟的步行不合併 | 接受 |
| 9 | 指標座標偏移 | PM 已用真實滑鼠確認可用 |

### 0.10 3-4b 報告「待 PM 決定」的處理（PM 決定，2026-10-19）

PM 驗收：`check.py` 全過；在內建瀏覽器把坦克的格擋與藉機攻擊設為「詢問」，結束回合後出現反應詢問視窗（觸發者洋紅框、代價耐力 10），按「拒絕」後紀錄為「放棄反應：格擋」；該場紀錄（含 2 個 `set_reaction_mode`）以 `trpg battle replay` 重播通過。

| # | 項目 | 決定 |
|---|---|---|
| 1 | CLI 的 `skills show` 仍顯示被動技「AP None」 | 3-5 順手修，重錄 CLI 快照並在報告說明 |
| 2 | `set_reaction_mode` 走 `POST /actions` | 接受 |
| 3 | 同一反應的多條規則一起改 | 接受 |
| 4 | 「之後都自動」記在前端佇列，重新整理會遺失 | 接受 |
| 5 | 詢問視窗固定左下 | 接受 |
| 6 | 環境預告以我方可見狀態模擬 | 接受（敵人目前沒有陷阱） |
| 7 | 預告標記樣式 | 接受，試玩後調 |
| 8 | 連鎖預覽只列幾類事件 | 接受 |
| 9 | 隊友指令只做全隊、守位半徑 1；被忽略原因即時計算 | 接受 |
| 10 | 指標座標偏移 | PM 以真實點擊確認可用 |

### 0.11 3-5 的設計決定（使用者，2026-10-20）

| # | 問題 | 決定 |
|---|---|---|
| G | 戰鬥之間 HP、法力 | **不回復，只在營火回滿**（使用者選「不回，只在營火回」）。營火放在一輪中段與 Boss 前（與 0.2 F 的重骰同一時點） |
| H | 隊友 | **維持現狀**（使用者：「還沒想好 現在是怎樣就先怎樣」）：每場 2 名標準隊友（目前網頁的戰士、弓手），滿狀態、不跟著升級、不跨戰鬥保留。取代 0.2 A 的「從 build 隨機抽 2 個」 |
| I | 經驗 | **每場固定**（打贏一場給固定經驗，數值放 `content/roguelite.yaml`） |
| J | Boss 戰 | **做一張專屬 Boss 地圖**（盜賊頭目加強版與手下；場地要有特色，例如源泉、可推倒的柱、致命地形） |
| K | 源力（Phase 3C 決定） | 一輪內保留、上限 3、每場開場至少 1；戰鬥之間取得（戰後獎勵、營火）、擊殺精英 ＋1、Boss 戰前保底（`Phase3C計畫.md` 0.4） |
| L | 裝備限制（Phase 3C 決定） | 主動 ≤ 6、被動（含修正）≤ 3、反應 ≤ 1 |

### 0.12 3-5a 驗收與「待 PM 決定」的處理（2026-10-20）

- 驗收：`check.py` 全過；`trpg run auto --seed 7` 兩次輸出逐字相同（雜湊一致）；實作者的「存檔 → 讀檔 → 繼續」5 個中斷點（含戰鬥中、升級、營火）與一次打完逐位元相同。存檔格式 `trpg-run/1`（報告第 3 節）。`LOG_FORMAT` 維持 `/34`。

| # | 項目 | 決定 |
|---|---|---|
| 1 | 開局屬性六項皆 10 ＋ 4 點自由分配（照設計），比 build 矩陣的英雄弱 | 接受（照設計）；試玩後再看 |
| 2 | 營火「重骰」＝營火時產生一組新的 3 個候選 | 接受 |
| 3 | 技能清單就是裝備，被替換的技能捨棄 | 接受 |
| 4 | 沒打贏（含平手）就算失敗；主角倒下但我方勝利時以 1 HP 繼續 | 接受 |
| 5 | 主角倒下後戰鬥自動推進到結束 | 3-5c 顯示「主角倒下，隊友繼續作戰」提示 |
| 6 | `run auto` 10 種子 3 勝 7 敗（HP 不回復累積） | 平衡階段；3-6 試玩時請使用者感受難度 |
| 7 | 偏離路線候選固定排最後 | 3-5c 網頁不要固定位置（或明確標示「偏離路線」），由前端處理 |
| 8 | 戰鬥中存檔依賴內容檔不變 | **3-5c 順手加內容雜湊**：存檔記錄規則包雜湊，不符時拒絕讀戰鬥中存檔並說明原因 |
| 9 | `/api/skills/{id}` 需先讀檔才查得到生成技能 | 接受 |

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

## 6. Phase 3-4｜戰鬥 UI（拆兩段）

使用者試玩 3-3 的回饋（2026-10-19）：**一進戰鬥，速度比主角快的單位已經行動完，畫面直接是結果**，看起來像遊戲已經玩了一部分。原因是建立戰鬥的回應只有最後的 `view`，前端沒有開場前的畫面可以播放。3-4a 第一項修正它。

- **3-4a**（sonnet）：逐步播放、`/api/glossary`、HUD、技能列與目標選取、預覽。
- **3-4b**（sonnet）：反應規則設定（含引擎小改）、反應詢問視窗、環境預告、隊友快捷指令按鈕、連鎖預覽事件。3-4a 驗收後補規格。

### 6.1 3-4a：逐步播放（修正開場）

- **API**：
  - `BattleResponse` 新增 `initial_view`：本次請求開始推進 **之前** 的視圖（建立戰鬥時為開場事件之後、第一個動作之前）。
  - 每個 `steps[i]` 新增 `view`：該步結算後的 `project_for(state, Team.ALLY)`。本機使用，回應變大可以接受；報告記下典型大小。
  - 重新產生 `client/openapi.json` 與 `schema.d.ts`。
- **前端播放**：
  - 收到回應：先畫 `initial_view`，再 **一步一步** 播放：標示行動中的單位 → 該步的移動動畫 → 畫該步的 `view` → 把該步的紀錄文字加進戰鬥紀錄 → 短暫停頓。最後以 `res.view` 為準。
  - 建立戰鬥時顯示「戰鬥開始」橫幅（約 1 秒），再播放開場到主角回合之間的 AI 行動。
  - 播放速度三段：正常（每個 AI 動作約 0.5 秒）／快（約 0.15 秒）／略過（直接畫最後的 `view`，紀錄一次加入）；取代原本的「略過動畫」勾選，記在 `localStorage`。
  - 播放中可以按「略過」直接跳到結尾。播放中鎖住操作。
- **測試**：vitest 測播放計畫（每步的順序：標示 → 移動 → 視圖 → 紀錄）；pytest 測 `initial_view` 與建立前狀態一致、`steps[i].view` 與重播到該步的狀態視圖一致。

### 6.2 3-4a：`/api/glossary`

- `GET /api/glossary`：地形、表面、物件、狀態、反應、元素、屬性的 ID → 中文名（與需要的簡短說明），由 content 產生。
- 前端 `glossary.ts` 改為啟動時讀 API（保留色塊等純顯示用的對照）；不再手寫中文名。
- 測試：pytest 檢查每個 content 定義的 ID 都在 glossary 中。

### 6.3 3-4a：HUD（設計文件 7.3「戰鬥 HUD」）

- 畫面固定位置顯示主角：HP／護盾、法力、耐力、剩餘 AP（含保留）、剩餘移動、反應是否可用、層數、身上的狀態（名稱＋剩餘回合）、腳下的表面。
- 回合列：先攻順序中的每個單位顯示代號、HP 小條；目前行動者強調。

### 6.4 3-4a：技能列與目標選取

- 技能列：主角的技能按鈕（名稱、AP、法力、冷卻中顯示剩餘回合並停用、沒有合法目標時停用）。滑過顯示技能卡片（`/api/skills/{id}`）。
- 選取技能後：在格子上標示所有合法的目標（依 `legal_actions` 中該技能的 `UseSkill`：目標單位、目標格、方向）。方向型用四個方向的箭頭按鈕或點選相鄰方向格。按 Esc 或右鍵取消。
- 推擊、絆倒、互動、防禦、結束姿態也改為按鈕或在目標上選取；「其他動作」清單保留為備援（收合）。
- **預覽**：滑過合法目標時呼叫 `/preview`（防抖，避免每次滑動都送），在格子上標示 `affected_tiles`，旁邊顯示命中率、暴擊率、傷害範圍與期望值、各目標的狀態機率、`certain`／`possible` 的結果摘要（中文）。普通攻擊滑過敵人時同樣顯示預覽。點擊才送出。
- 測試：vitest 測「技能 → 合法目標」分類（含方向型、自身型）、技能按鈕停用條件；預覽結果轉成顯示文字。

### 6.5 驗收條件（3-4a）

1. 建立戰鬥後先看到開場前的戰場與「戰鬥開始」，再一步步看到比主角快的單位行動（PM 在瀏覽器確認）。
2. `initial_view`、`steps[i].view` 的 pytest 通過；OpenAPI 快照已更新。
3. 播放速度三段可切換並記住；播放中可略過。
4. `/api/glossary` 涵蓋所有 content ID（測試為證）；前端不再手寫中文名。
5. HUD 顯示 6.3 列出的項目。
6. 能從技能列選技能、在格子上選目標並看到預覽後施放；傳送類技能不再塞滿「其他動作」（PM 確認）。
7. 網頁打完一場的紀錄以 `trpg battle replay` 重播通過（實作者以 API 腳本或瀏覽器打一場為證）。
8. `uv run python scripts/check.py` 全過（含前端）；複雜度類 noqa 不增加。
9. 報告附畫面截圖或文字描述，以及 3-4b 要注意的事。

---

### 6.6 3-4b：反應規則設定（含引擎小改）

- `ReactionRule.mode` 新增 `"off"`（不觸發）。
- 新動作 `set_reaction_mode`（`unit_id`、`reaction`、`mode`）：0 AP、不結束回合，只能在自己的回合使用，只能改自己身上已有的規則；記進步驟列表，所以重播一致。**不列入 `legal_actions`**（AI 不使用），另以驗證函式判斷合法。若需要，升 `LOG_FORMAT` 並說明。
- `BattleView` 的主角單位帶反應規則列表（反應 ID、中文名、觸發條件摘要、模式、代價）。
- API：沿用 `POST /actions` 送這個動作即可（不推進戰鬥，回應 `steps` 只有這一步）；或另設端點，報告說明。
- UI：HUD 旁「反應設定」面板，每條規則一個三段切換（自動／詢問／關閉），預設維持 content 的設定。
- 測試：設為 `off` 後不觸發；設為 `prompt` 後出現詢問、`resume` 正確；重播一致；非自己回合或不存在的規則被拒。

### 6.7 3-4b：反應詢問視窗

- 取代 3-3 的簡單確認框：顯示觸發者（在格子上標示）、反應名稱與說明、代價（耐力／法力／HP）、接受與拒絕按鈕；可勾選「之後都自動」（等於送 `set_reaction_mode`，下一次自己回合才能送的話，改為只在本地記住並在下個回合開始時送出，報告說明做法）。

### 6.8 3-4b：環境預告

- 回應新增 `telegraph`：`trpg.engine.environment.telegraph(state)` 的結果（下一次環境回合會發生的變化：火焰蔓延、表面變化、物件點燃／爆炸、援軍、地形變化）。確認不洩漏隱藏資訊（陷阱、亂數狀態）。
- UI：格子上以半透明圖示或外框標示預告的變化，滑過顯示說明；側欄列出文字摘要。

### 6.9 3-4b：隊友快捷指令

- 側欄按鈕：集火（再點一個敵人）、守位（再點一格）、撤退（再點一格）、保護（再點一個隊友，預設主角）、利用環境、取消指令。對全隊下達（`team_orders`）。
- 目前的指令顯示在側欄，被忽略的指令（`OrderRecord.ignored`）顯示原因。
- 送 `PUT /orders`；不推進戰鬥。

### 6.10 3-4b：連鎖預覽與小修

- `/preview` 回應新增過濾後的模擬事件（`min`／`max` 兩種，各附中文 `text`），前端在預覽框列出「可能發生的連鎖」（例如油桶爆炸、火焰蔓延、墜落）。
- 修 `SkillCard.cost` 被動／反應技的「AP None」（0.9 #4）。
- 保留 AP：0.9 #1。

### 6.11 驗收條件（3-4b）

1. 反應設定三段可切換，`off`／`prompt` 的行為與重播一致有測試為證。
2. 設為詢問後在瀏覽器遇到反應詢問視窗，接受與拒絕都正確（PM 確認）。
3. 環境預告顯示在格子上，與下一次環境回合的實際結果一致（以既有 `telegraph` 測試加一個 API 層測試為證）。
4. 快捷指令可下達、取消，隊友行為依指令改變（以 API 測試確認紀錄的 `orders`；行為由 PM 試玩觀察）。
5. 預覽列出連鎖事件；`SkillCard` 不再出現「AP None」。
6. 網頁打完一場的紀錄以 `trpg battle replay` 重播通過（含 `set_reaction_mode` 步驟）。
7. `uv run python scripts/check.py` 全過；複雜度類 noqa 不增加。

---


## 7. Phase 3-5｜roguelite 一輪（拆三段）

> 前置：Phase 3C、3D、**3E-1**（`Phase3E計畫.md`）已完成（`Phase3C計畫.md`、`Phase3D計畫.md`）。設計：`docs/design/07-角色成長.md`（只讀 7.1 一輪流程相關）、`docs/design/06-技能.md` 6.14.4（源力）。

| 段 | 內容 | 模型 |
|---|---|---|
| 3-5a | `trpg.roguelite` 核心、存檔、API | opus |
| 3-5b | 專屬 Boss 地圖與 Boss 遭遇 | sonnet |
| 3-5c | 前端：開新一輪、進度、戰後獎勵與升級、營火、讀檔、結束摘要 | sonnet |

### 7.1 3-5a：核心、存檔、API（opus）

- 新套件 `trpg.roguelite`：純函式、確定性；所有亂數由「一輪的種子」以固定方式衍生（每場戰鬥的種子、地圖與遭遇抽選、升級候選、重骰），只用 `trpg.shared.rng.Rng`。依賴方向：`roguelite` 可匯入 `engine`、`content`、`skillgen`，`engine` 不可匯入 `roguelite`（import-linter 已有規則，確認仍成立）。
- 參數放 `content/roguelite.yaml`（pydantic 驗證）：場數 5 ＋ Boss、地圖類型抽選不重複（Boss 地圖固定）、遭遇與敵人隨場數成長（敵人數量或等級；先用現有盜賊系列）、每場固定經驗與升級門檻、每級 ＋2 屬性點、開局 4 點自由分配、重骰次數與時點、營火時點（中段與 Boss 前）、源力的戰後獎勵量與 Boss 前保底。
- **主角的一輪狀態**（`RunState`，可序列化）：屬性、等級與經驗、技能清單與裝備（主動 ≤ 6、被動 ≤ 3、反應 ≤ 1）、**目前 HP、法力**（戰鬥之間不回復，0.11 G）、**源力**（0.11 K）、歷程（每場結果）。
- **戰鬥銜接**：
  - 開戰時以 `RunState` 建立主角（屬性、技能、HP、法力、源力 ＝ max(存檔值, 1)）。`UnitSpawn` 若沒有「開場 HP／法力」欄位，加上（預設 `None`＝滿），引擎測試確認舊行為不變。
  - 隊友：每場 2 名標準隊友，滿狀態（0.11 H）。
  - 戰後：用 `trpg.engine.battle_result(state)` 寫回主角 HP、法力、源力；HP 為 0（主角倒下）→ 一輪失敗。戰鬥中倒下但我方勝利時，主角以 1 HP 繼續（保守，報告說明）。
- **升級**：每場固定經驗；升級時給 ＋2 屬性點，並提供 3 個技能候選（隨機組合器，依主角目前的階級），其中 1 個「偏離路線」（0.2 C），可跳過；技能欄滿時要選擇替換或放棄。
- **營火**（中段與 Boss 前）：HP、法力回滿；源力依 `roguelite.yaml` ＋1（不超過上限）；同時提供重骰（0.2 F）。
- **存檔格式**（0.2 E）：JSON，帶 `format` 版本（例如 `trpg-run/1`）。內容：一輪的種子、`RunState`、目前節點（戰鬥／升級／營火／結束）、進行中戰鬥的 `setup ＋ seed ＋ steps ＋ orders`（讀檔以重播還原），以及 **升級得到的生成技能定義**（讀檔時用 `Ruleset.with_skills` 加回規則包，Phase 3E-1）。戰後讀回 HP、法力、源力用 `BattleResult` 以 `unit_id` 為鍵的查詢（3E-1）。存在本機資料夾（例如 `saves/`，加進 `.gitignore`），檔名含 run id。
- **API**：`/api/runs`（建立：選 build 作為起始技能組、分配開局 4 點）、`/api/runs/{id}`（狀態）、`/api/runs/{id}/battle`（開始或接續本場戰鬥，沿用既有戰鬥 API）、`/api/runs/{id}/choice`（升級選擇、營火、重骰）、`/api/runs/{id}/save`、`/api/runs/load`。路徑可微調，報告列出最終版本。
- **CLI**：`trpg run new --seed N --build X`、`trpg run auto --seed N`（AI 代打整輪，用於測試與模擬）、`trpg run show <存檔>`。
- 順手修 0.10 #1：`skills show` 被動技「AP None」，重錄 CLI 快照。
- 測試：同種子整輪（AI 代打）結果一致；「存檔 → 讀檔 → 繼續」與一次打完的結果逐位元相同（含戰鬥中存檔）；HP、法力、源力跨戰鬥正確；營火回滿；升級候選確定性；`run auto` 跑 10 個種子無例外。

### 7.2 3-5b：專屬 Boss 地圖（sonnet）

- 新地圖 `content/maps/bandit_lair.yaml`（名稱可改）：Boss 戰專用，不進一般抽選。場地要讓 3C／3D 的機制有發揮空間：至少 1 個源泉格、可推倒的石柱、可投擲的物件、一處致命地形（深淵或岩漿）、高低差。
- Boss 遭遇：盜賊頭目加強版（新範本，例如 `bandit_warlord`：HP、攻擊提高、`elite`），帶 3–4 名手下；可以有援軍地圖事件。數值為初值。
- `scripts/map_push_check.py` 通過；`trpg sim maps --maps <boss 地圖> --seeds 10` 一次，報告列勝率與平均輪數（目標 Boss 戰 6–10 輪，只記錄不調）。

### 7.3 3-5c：前端（sonnet）

- 畫面：開新一輪（選 build、分配 4 點、種子）→ 進度畫面（第幾場、下一場地圖、主角 HP／法力／源力、技能）→ 戰鬥（沿用現有戰鬥畫面，從一輪進入時帶入主角狀態）→ 戰後獎勵與升級三選一（用技能卡片，可跳過、欄位滿時選擇替換）→ 營火（回滿、重骰）→ 讀檔續玩 → 一輪結束摘要（勝敗、各場結果）。
- 存檔與讀檔按鈕；重新整理頁面後可從存檔繼續。
- 3F 規格 0.2：灰掉的技能按鈕顯示原因；工坊說明文字去掉開發術語；`/api/builds` 回傳法力上限；`/api/skills/{id}` 查得到戰鬥內的自訂技能。
- 0.12 #5：主角倒下後顯示「主角倒下，隊友繼續作戰」；#7：偏離路線候選明確標示；#8：存檔加規則包雜湊（後端小改），不符時拒絕讀取戰鬥中存檔並說明原因。
- vitest 涵蓋流程狀態；PM 用瀏覽器打完一輪驗收（3-6）。

### 7.4 驗收條件

3-5a：
1. 一輪種子衍生所有亂數；同種子 `trpg run auto` 兩次結果一致。
2. 存檔 → 讀檔 → 繼續（含戰鬥中）與一次打完逐位元相同；存檔 JSON 帶 `format`。
3. HP、法力跨戰鬥保留；營火回滿；源力跨戰鬥保留、上限 3、開場至少 1、戰後獎勵與 Boss 前保底。
4. 升級：＋2 屬性點、3 候選含 1 個偏離路線、可跳過、裝備上限檢查；重骰在中段與 Boss 前各一次。
5. API 與 CLI 端點有測試；`run auto` 10 個種子無例外；`check.py` 全過。

3-5b：Boss 地圖通過內容驗證與卡路檢查；Boss 遭遇 sim 10 場無異常，報告列勝率與輪數。

3-5c：網頁可以從開新一輪打到結束（PM 用瀏覽器驗收）；vitest；`check.py` 全過。

---

## 9. 報告格式（每段一份：`docs/phases/Phase3-N報告.md`）

1. 完成項目與 commit 列表。
2. 驗收條件逐條：結果 ＋ 證據（測試名稱或指令輸出）。
3. 新增或移除的複雜度 noqa 與理由；noqa 總數前後。
4. 修改既有測試期望值的清單與原因。
5. 待 PM 決定（最多 10 點）。
6. 代表性輸出節錄。
