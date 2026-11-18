# Phase SK-3 報告：#166 第 3 組（新觸發與流程）

> 規格：`docs/phases/PhaseSK-3計畫.md`（main `9a914a8fe`）。分支 `worktree-agent-ae6b47ace25700297`（起點 main `0aa9b6c54`）。
> 數字一律是初值，接數值工坊；沒有試數值、沒有跑平衡量測與模擬（戰鬥不變比對除外）。沒有改 `docs/design/`、`config/`；沒有存檔遷移。

## 0. 結論

三項都做完，各一個 commit；另有測試小修、開發頁與截圖、報告各一個 commit：

| 項目 | commit | 一句話 |
|---|---|---|
| 1 你造的關鍵字被利用時（6.38-10） | `99e115755` | 新觸發 `on_keyword_exploited`：你施加的狀態被消耗、你造的表面被元素觸發互動時，你的被動或詞條觸發 |
| 3 重擲（6.38-12） | `ccbba67fd` | 新原語 `reroll`（只限反應）：隊友擲失手時讓他重擲取較好、敵人擲中你時逼他重擲取較差；預覽列出 |
| （小修） | `fb1bf168e` | 第 3 項測試檔的 ruff／mypy（交件前全庫檢查才發現，見第 4 節） |
| 2 戰前佈置（6.38-11） | `b3f6dbc2a` | 開戰前在我方起始區免費放 1 個陷阱、刻印或表面；引擎＋API＋前端，可跳過 |
| 截圖 | `b959177af` | 開發頁 `sk3-gallery.html`（真引擎事件）＋實機戰前佈置 3 張 |

- `LOG_FORMAT` `/129 → /130`（一次升，三項共用；`docs/phases/戰鬥紀錄格式變更.md` 加一條）。`WORLD_RULES_VERSION`、`CHAR_FORMAT`、`SAVE_FORMAT`、提示詞版號都沒動。OpenAPI 有變（`PreviewOut.rerolls`、`BattleResponse.prep`、`awaiting` 多 `prep`、`Prepare` 動作、`POST /api/battles/{id}/prep`），已重產 `client/openapi.json`、`client/src/api/schema.d.ts`。
- 新觸發、新原語**都沒有放進任何骨架**，組合器、挑選打分、閃現檔都沒碰（SK-1 的範圍）；接進出題是待 PM 決定 1。
- 開發 PM 通知的 `tests/engine/test_trigger_order.py`：本段**沒有新增 `register_trigger` 的觸發函式**（新觸發是在 `consume_status` 與 `interactions.touch_outcomes` 直接呼叫 `skill_triggers.collect_exploit`，不走事件觸發表），順序清單不受影響。

## 1. 各項做法

### 1.1 你造的關鍵字被利用時（項目 1）

- 資料：`content/skill_triggers.yaml` 新時機 `on_keyword_exploited`（`has_other: false`、係數 300、epic、`random_composer: false`）；參數 `status`／`surface` 擇一（都省略＝任何一種）。`TriggerSpec`：這個時機的 `max_per_round` 只能是 1。裝備詞條 `TriggerAffix`：只能 `effect_target: self`、狀態與表面擇一，次數照詞條的 `limit`（預設每回合）。
- 「利用」目前兩種（`skill_triggers.collect_exploit`）：
  1. **狀態被消耗**：`consume_status` 移除狀態前，製造者＝`StatusInstance.source_id`（例：你的燃燒被引爆）。
  2. **表面被元素觸發互動**：`interactions.touch_outcomes` 符合表面類規則，或「站在某表面上的單位」類規則（例：雷電打到站在水上的人）時，製造者＝`Tile.surface_creator`；每次觸及最多記一次。
- 誰利用都算（含自己、隊友、敵人）；沒有製造者（地圖原有、天氣、蔓延）不算。走既有的被動／詞條延後結算（`skill_triggered`／`gear_triggered`，`trigger` 是時機 ID），深度照 `max_trigger_depth`；沒有新事件型別。
- 卡片文字「你造的「燃燒」被利用時」「你造的「水」表面被利用時」；工坊觸發欄位多狀態／表面兩個選填；工坊玩家文字 1 筆（實作者初稿）。

### 1.2 重擲（項目 3）

- 原語 `reroll`（`content/skill_primitives.yaml`，`sole_effect`、`allowed_shapes: [self]`、固定 5 點、rare）：只能是反應技唯一的效果；反應事件只能是新的 `ally_missed_roll`（隊友擲失手時）或 `enemy_hit_roll`（敵人擲中你時），這兩個事件也只能配重擲（`skill.py::_check_reroll`）。
- 結算（`reactions.reroll_attack`；純查詢在 `engine/rerolls.py`）：普攻 `_attack_once` 與技能 `Cast.roll_one` 擲完命中骰、發 `attack_rolled` **之前**：
  - 命中了 → 目標的「敵人擲中你時」反應技 → 付代價（照一般反應技：每輪反應次數、法力、冷卻）→ 同參數再擲一次 → 取**較差**。
  - 失手了 → 攻擊者 `core.reroll_ally_range`（初值 1，單位距離）格內的隊友依 ID 找第一個願意的 → 取**較好**。
  - 比較順序：暴擊 > 命中 > 總值；相同留第一次。新事件 `attack_rerolled`（兩次的自然骰、總值、命中與採用哪次），緊接著照採用結果發 `attack_rolled`（所以「命中時」等觀察 `attack_rolled` 的被動看的是最後結果）。`prompt` 模式照一般反應暫停（`resume` 從原狀態重跑，亂數一致）。
- 預覽：不真的重擲（強制結果不變）；`Preview.rerolls` 列出可能的重擲與重擲後的命中率（取較好＝1 −（1 − p）²、取較差＝p²）、`auto`，說明寫進 `notes`（前端預覽本來就顯示 notes）；API `PreviewOut.rerolls`（沒有時 `null`）。`hit_chance` 本身不含重擲。
- 工坊：反應時機選單加這兩個（`options._reaction_field`），重擲只在選了這兩個時機時出現；LLM 的反應事件清單（`SKILL_REACTION_EVENTS`）沒加，另列 `REROLL_EVENTS`。
- 前端：浮字「重擲！」（在擲骰的人頭上）、`skillSequence` 事件 → 原語、`skillClips` 暫借替隊友擋攻擊的側擋動作、Q 版部件暫借 `intercept`；觸發圖樣 `TRIG_ALIAS` 加三個暫代（新觸發借「施加狀態後」、兩個反應時機借既有的）。紀錄文字「↻ X 的「Y」逼 Z 重擲命中骰（取較差的）：d20=19，總值 20（命中）→ d20=2，總值 3（未命中），採用第二次」。

### 1.3 戰前佈置（項目 2）

- 引擎（`engine/prep.py`）：
  - 開窗：`BattleSetup.prep_placement`（false 不輸出）只有網頁工作階段會設；`begin_battle` 的 `_settle_placement` 呼叫 `open_prep`：主角＝我方第一個非召喚單位（同 API 的主角），裝備的**主動**技能裡第一個放置類效果是 `place_trap`／`inscribe`／`create_surface`，而且冷卻好了、還有每場次數、沒被封、武器相容，起始區內有放得下的格子 → `BattleState.prep = PrepWindow(主角, 起始區)`。沒有可放的技能就不開（「直接跳過」）。CLI、模擬、AI 代打不設旗標，所以永遠不開。
  - 動作 `Prepare(unit_id, skill_id, target_pos)`：不看行動順序（敵人先手時也能在第一個行動前放），不列入 `legal_actions`（AI 不用）；`skill_id` 與 `target_pos` 都省略＝跳過（`prep_skipped`）。放：`prep_placed` → 陷阱照 `traps.place_trap`、符文照技能第一個 `inscribe` 的參數、表面照第一個 `create_surface` 的參數（智力的表面持續加成照算）**只放 1 格**；不花 AP、法力、耐力；照常進冷卻（裝備的冷卻修正照算）、每場次數 +1。
  - 關窗：佈置、跳過，或任何其他動作在 `resolve_with` 一開始就關（「雙方都還沒行動」）。陷阱的 `prep_placed` 對方看不到（`event_filter`，同 `trap_placed`）。
- API：`awaiting` 多 `prep`（主角的窗開著時優先於其他狀態；自動推進在這裡停）；`BattleResponse.prep`（`unit_id`、`zone`、每招 `kind` 與放得下的格子）；`POST /api/battles/{id}/prep`（`{skill_id, target_pos}`，空物件＝跳過）。`SessionStore`／`create_app` 有 `prep_placement` 開關（預設開）；**API 測試的 client 預設關**（`tests/api/conftest.py`，既有 50 個測試的主角帶表面或陷阱技能，開著會全部停在佈置；佈置自己的測試 `test_prep_api_sk3.py` 開著）。
- 前端：`ui/PrepDialog.tsx`（列出可放的招、「不佈置，直接開戰」）；選了一招後起始區放得下的格子走第二段選目標同一套選取模式（`battle/prep.ts::prepMode`，`useBattleData` 的 `copying`），點格子送 `/prep`，Esc 換一招；技能列上方提示改成佈置的說明；滑過格子不打預覽。

## 2. 快照與相容性（先預測再核對）

| 東西 | 預測 | 實際 |
|---|---|---|
| `glossary.json` | 第 1 項 +1 觸發；第 3 項 +1 原語、+2 反應時機 | 一致（+8、+26 行，只有這些筆） |
| `unitDolls.json`、`raceLooks.json`、`skillCards.json` | 不變 | 不變 |
| OpenAPI | 第 1 項不變；第 3 項 `PreviewOut.rerolls`、`RerollOut`；第 2 項 `Prepare`、`PrepOut`、`awaiting`、`/prep` | 一致 |
| 狀態 JSON | 不帶新東西時逐字不變（`prep` None 不輸出） | 不變比對 60 場逐字相同 |
| 規則包雜湊 | 全變（觸發表、原語表、反應時機、核心規則） | 不變比對已把 `ruleset` 拿掉比 |
| CLI 快照（slow） | 0 鍵會變 | `tests/cli -m slow` 44 passed，沒有重產 |

改到的既有測試（沒有放寬斷言）：`LOG_FORMAT` 字面值 13 處（12 檔）；`tests/content/test_coverage.py`（新觸發、新原語列為還沒有技能用）、`test_skill_triggers_content.py`（沒有另一方的時機多一個）、`test_skills_content.py`（未使用原語多 `reroll`）；`tests/skillgen/test_workshop_feedback.py` 條數 183 → 185、`test_proposal_layouts.py`（`sole_effect` 多 `reroll`）；`tests/api/test_routes.py`（預覽欄位多 `rerolls`；推進上限那個測試的 `create_app` 關佈置）、`test_run_autosave.py`（兩處 `create_app` 關佈置）、`conftest.py`（client 預設關佈置）；前端 `qIconSkills.test.ts`（效果碼 57 → 58、觸發暫代 7 → 10）、`skillClips.test.ts`（共用片段 `intercept`／`redirect_damage`／`reroll`）。

## 3. 戰鬥不變比對

腳本在 scratchpad（未 commit），做法同 SK-2：改前＝`git archive 0aa9b6c54 src content` 解開、`PYTHONPATH` 指向舊 `src`；地圖預設陣容、效用 AI、`max_rounds=30`；每場比整份事件、步驟、最終狀態（拿掉 `setup.ruleset`、`final_state.ruleset`、`format`、`ruleset_hash`）。10 張一般圖 × 種子 1、2 ＋ 4 張頭目圖 × 種子 3～12。

- 第 1、3 項做完（`ccbba67fd` 時的工作目錄）：`battles=60 events=23897 different=0`。
- 三項都做完：`battles=60 events=23897 different=0`。
- 戰前佈置對既有戰鬥：`run_battle`／CLI／模擬／AI 代打（含 `world_dev` 的 `ai_until`、`opening`，它們直接用引擎的 `advance`）都不設 `prep_placement`，窗永遠不開；網頁工作階段只有主角有可放的技能時才停在佈置。網頁的存檔重播：舊存檔的步驟在新工作階段重播時，第一個動作就關窗，結果與事件相同。

## 4. 測試與檢查

分目錄、`-n 8`，不帶 `-m`（CLI 快照另跑 slow）。最後一輪全部結束碼 0。

| 檢查 | 結果 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0、0 |
| `mypy`（1688 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（691 檔、429 技能） |
| 新增引擎測試 `test_keyword_exploited_sk3.py`（20）、`test_reroll_sk3.py`（30，含 12 個種子的確定性）、`test_prep_sk3.py`（18） | 全過；每個都有「同輸入同結果」、預覽／序列化／重播 |
| API `test_prep_api_sk3.py`（4：停在佈置、放陷阱並重播、跳過、不合法格子 400、沒有可放的技能不停） | 0 |
| 相關引擎檔（確定性、clone、暫停點序列化、runner、事件過濾、視圖、回合、先手、陷阱、符文、反應、反應技、預覽、技能預覽、碰撞、gear g2／g3a、風、self costs…）＋`tests/content`＋`tests/narrative`＋`tests/cli`＋`test_architecture`＋`test_primitive_coverage` | 0（3986 passed） |
| `tests/skillgen` | 0（4442；第 3 項時跑，之後只改了 1 個測試檔的預期並單檔重跑） |
| `tests/llm` | 0（495；第 1 項時跑） |
| `tests/api` | 0（1324 passed、1 skipped） |
| `tests/world`、`tests/roguelite` | 0（1606 passed；佈置預設開的時候跑的） |
| `tests/cli -m slow` | 0（44 passed） |
| 前端 `tsc`、`vitest run`（全部） | 0、0（373 檔 4691 passed） |
| 前端 `build` | 0 |
| 紀錄＋重播 `open_plain` 7 | 「重播驗證通過」 |

- 自查失誤：第 3 項的 commit（`ccbba67fd`）提交前只對 `src` 跑了 ruff、mypy，測試檔 `test_reroll_sk3.py` 有 1 個 ruff（多餘的 `noqa`）與 1 個 mypy（`describe_event` 可能回 `None`），在 `fb1bf168e` 修掉。中間那個 commit 單獨看 `ruff check .`／`mypy` 不會過。
- `lint-imports`：最後一輪跑過，結束碼 0（新模組 `engine/prep.py`、`engine/rerolls.py`、`engine/events/prep.py` 只匯入 `trpg.engine`、`trpg.content`、`trpg.shared`）。
- 沒跑 `scripts/check.py` 全量、`tests/sim`、平衡量測與模擬（不變比對以外）。

## 5. 實機（截圖）

存在 `docs/art/shots/sk-3/`（jpg、DPR 1，量到 `devicePixelRatio = 1`；無頭 Chrome `--headless=new --mute-audio --remote-debugging-address=127.0.0.1`、除錯埠 9735；`trpg serve` 埠 8765、vite 埠 5293；開之前三個埠都沒人聽，結束時只停了自己起的三個程序，埠都已關閉）。

- **戰前佈置（真畫面）**：`?dev=1&mute=1` 首頁「一鍵開局」，頁面包 `window.fetch` 把建立戰鬥的請求改成衝鋒流英雄＋工坊版捕獸夾（`open_plain` 種子 3，敵方先手）。
  - `prep_1_dialog.jpg`：開場停在佈置視窗（行動順序最前面是盜賊弓手，敵人還沒動）。
  - `prep_2_pick.jpg`：選了捕獸夾，起始區 3 格可放（紅框），技能列上方是佈置的提示。
  - `prep_3_placed.jpg`：點格子放下（陷阱圖示在 (1, 5)），之後敵人照常行動、輪到主角；捕獸夾冷卻 1。紀錄裡有「◆ 戰前佈置：衝鋒流英雄 用「捕獸夾」在 (1, 5) 放了陷阱」（面板捲到後面，那一行在截圖範圍外；文字由頁面 `innerText` 確認）。
- **新觸發、重擲（開發頁）**：`client/dev/sk3-gallery.html?case=…&scale=0.8`；事件是真引擎跑的（產生腳本：`tests/engine` 的場景 → `resolve` → `model_dump`＋`describe_event`，寫進 `client/src/dev/fixtures/sk3Events.json`；腳本在 scratchpad），走正式 `playbackPlan → frameOps → BattleRenderer`。每張三格（動作前、演出中停格、結算後），上方是紀錄文字。
  - `exploit.jpg`：法師2 造的水，法師1 的雷擊打到站在水裡的盜賊 → 法師2 的「潮汐共鳴」觸發回血。
  - `reroll_worse.jpg`：盜賊擲 19 命中戰士，戰士的「厄運之眼」逼他重擲，取較差的 2 → 失手。
  - `reroll_better.jpg`：戰士擲 1 失手，身旁法師的「鼓舞」讓他重擲，取較好的 18 → 命中。

實機未看：重擲的浮字「重擲！」與觸發的「★」字是戰鬥畫面的 DOM 層，開發頁沒有畫；重擲 `prompt` 的詢問視窗（走既有 `DecisionDialog`）沒拍；新觸發、重擲在真人戰鬥裡用不到（沒有內建技能、沒有骨架）。

## 6. 新增 `# noqa`

- `engine/reactions.py::_rerolled`：`# noqa: PLR0913, PLR0917`（8 個參數：反應者、反應技、攻擊者、目標、第一次擲骰、再擲函式、取較好／較差，加 `ctx`；都是一次結算的現場資料，打包成物件只為了過規則）。
- `engine/preview.py::_build` 原本就在 `PLR0915` 上限：把位移判定的機率連乘拆成 `_all_checks_chance`，沒有加 noqa。

## 7. 待 PM 決定

1. **接進出題**（規格要求寫進報告）：`on_keyword_exploited`（`random_composer: false`，LLM 的觸發清單會列出它——提議模型照 `skill_triggers.yaml` 全部列）、`reroll` 與兩個反應時機（不在 `SKILL_REACTION_EVENTS`，LLM、組合器看不到）都沒進任何骨架；要放進哪些骨架、組合器排除表、閃現模板，由後面的小段接。也還沒有任何內建示範技能（被動、詞條、重擲反應）。
2. **「利用」的範圍**（解讀，照最保守的做）：只有「消耗狀態」與「元素觸發表面互動」兩種。條件型的利用（例：「目標燃燒中時加傷」的效果條件成立）、層數消耗、符文引爆都**不算**；條件判定是 SK-1 的檔，沒碰。敵人利用你造的東西也算你被利用（「被任何人利用」照字面），例如敵人的火點燃你的油。
3. **每回合 vs 每輪**：設計寫「每回合最多 1 次」；被動技能的計數只有每輪（`max_per_round`），所以被動是**每輪 1 次**（比每回合嚴），詞條照 `limit`（預設每回合）。要改成被動也每回合要另加計數。
4. **重擲的範圍**（解讀）：只重擲**攻擊的命中骰**（普攻與技能），不含抵抗、對抗、檢定；隊友版只在**失手**時問、敵人版只在**命中**時問（自動模式下不會在「已經命中」時再求暴擊）；隊友範圍 `core.reroll_ally_range` 初值 1（同其他「身旁隊友」反應）。重擲的反應形狀只能 `self`。
5. **戰前佈置的細節**（解讀，照最保守的做）：只有主角（玩家操控的那一個）能放，AI 隊友不放；一律只放 **1 格**（範圍技也只放 1 格表面）；技能的其他效果（傷害、狀態）不結算；不檢查沉默與 AP、法力（免費）；陷阱的位置對敵方隱藏。冷卻從放的那一刻算，所以主角先手時第 1 回合結束就倒數一次（同自己回合施放）。
6. **API 測試預設關佈置**：`tests/api/conftest.py` 的 client 與兩處直接 `create_app` 關掉佈置，既有測試照原流程；正式伺服器預設開。若要 API 測試預設開，要逐一改約 50 個測試先跳過佈置。
7. **AI**：AI 不會用戰前佈置（設計就是 AI 直接跳過）；重擲反應技是反應，AI 單位帶了會自動用，但效用 AI 估攻擊時不考慮對方的重擲（`hit_chance` 不含重擲）。新觸發的被動沒有估值。
8. **美術**：重擲的 Q 版部件、演出暫借（側擋、`intercept` 圖）；三個觸發圖樣暫借；戰前佈置視窗沿用 `DialogFrame`，起始區格子用選目標的紅框。
9. **和 SK-1 的合併點**：`engine/skills/cast.py`（`roll_one` 多一個 `reroll_attack` 呼叫）、`content/skills/constants.py`、`skill.py`、`skillgen/options.py`、`content/workshop_text.yaml` 尾端與 `test_workshop_feedback.py` 的條數、`qIconSkills.test.ts` 的數量那一行、`LOG_FORMAT`（SK-1 也升的話改成 `/131`）。
10. **工坊白名單**：`core.reroll_ally_range`、`reroll` 的 5 點、新觸發係數 300 都是初值；`tuning_fields.yaml` 沒加（沒有對應的技能可調）。
