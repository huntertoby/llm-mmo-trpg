# 階段 SK-3c 報告：SK-3b 待決 5、6、8 的答覆

> 2026-11-19，實作者（SK-3c）。規格 `docs/phases/PhaseSK-3c計畫.md`；答覆來源玩法交接 4.1.31 第 5、6、8 點。
> 分支 `worktree-agent-a9144c27c5b790848`（起點 main `11065f916`）。不 push。
> 沒有試數值、沒有跑平衡量測與模擬（戰鬥不變比對除外）。沒有改 `docs/design/`、`config/`。

## 結果（一兩句）

第 1～3 項都做完：修正規則的條件也算利用（`LOG_FORMAT` `/131 → /132`）、`skill_evolution` 的 `reshape` 前綴「擴散」→「易形」、限定狀態或表面的「被利用時」算進關鍵字推導（餘燼共鳴進點燃池、潮引進潮濕池）。戰鬥不變比對 60 場在第 1、2、3 項之後各跑一次，都是 **different=0**。

## 交付項目

| 項目 | 狀態 | commit |
|---|---|---|
| 1 修正規則的條件也算利用 | 完成 | `263278792` |
| 2 `skill_evolution.yaml` `reshape` 前綴「擴散」→「易形」 | 完成 | `289cb5e62` |
| 3 `on_keyword_exploited` 算進關鍵字推導 | 完成 | `42f297197` |

每個 commit 前都跑了 ruff、format、mypy、lint-imports、相關測試與戰鬥不變比對（見第 5 節）。

## 1. 各項做法

### 1.1 修正規則的條件也算利用（第 1 項）

- **哪些規則**：`modifiers.target_rules`——套用在這次動作上、有條件、而且條件看「這次動作的目標」的那幾種改變（`TARGET_CHANGES`：傷害 `damage_permille`、命中 `hit_bonus`、推擊距離 `push_distance_delta`、冷卻 `cooldown_delta`、命中後效果 `on_hit_effects`，照 `ModifierSpec` 的說明）；其他種類（AP、射程、加元素、加標籤、變形、治療、召喚、形態、無聲）的條件看持有者自己，不是「作用在那個目標上」，不算。本回合 `per_turn_limit` 已用完的規則不算（那次沒有生效）。
- **哪些利用**：規則條件（含 `any_of` 分支）因為目標身上有某人造的狀態（`target_has_status`）、站在某人造的表面上（`target_on_surface`）或目標格有自己的符文（`on_own_rune`）而成立——同 SK-3b 的 `EXPLOIT_CONDITIONS`，`exploits.rule_exploits`。
- **施放**（`Cast.run`）：命中判定之後、效果結算之前，對這次擲了命中的對象（`self.hits` 裡的單位）判斷；全部效果與連擊打完後，只交「最後仍判定命中」的對象，而且之後的事件裡要有作用在那個對象的事件（同 SK-3b 1.1）。被動、陷阱、命中後效果的施放（`TriggeredCast`）不受修正，沒有。
- **普攻**（`reactions._attack_once`，含藉機攻擊、普攻連擊的每一下）：擲命中之前對目標判斷（守護者攔下時再對守護者判斷一次），傷害結算之後看有沒有作用在對象上。
- **只算一筆**：同一次施放（`Cast.exploits_seen`）或一次普攻，同一個鍵（製造者、狀態、表面、對象）只交一次給 `collect_exploit`。技能條件、效果條件、修正規則條件同時成立時不重複算；SK-3b 的「同一招兩個效果都帶同一個條件」也一起變成一筆（每回合本來就最多觸發 1 次，所以不影響觸發結果，只是紀錄乾淨）。見待決 1。
- **擲骰不算生效**：`_NO_EFFECT` 多 `attack_rolled`、`status_save_rolled`、`maneuver_rolled`。原因：只施加狀態的技能被抵抗時，作用在目標上的只剩「狀態豁免擲骰」事件，SK-3b 的判定會把它當成生效；連擊武器多打的那一下落空也有 `attack_rolled`。這是照規格「抵抗不算」的修正，也影響 SK-3b 的條件型利用（以前抵抗也算），見待決 2。
- 變奏的 `when` 照舊不算；推擊、絆倒、互動不算（見待決 3）。
- `LOG_FORMAT` `/131 → /132`（`docs/phases/戰鬥紀錄格式變更.md` 加一條；測試字面值 8 檔＋4 個 `endswith`）。`docs/dev/上手-引擎戰鬥結算.md` 第 56 點補 SK-3c 一段。

### 1.2 `reshape` 前綴改「易形」（第 2 項）

- `content/skill_evolution.yaml` 的 `reshape`（閃現大變化「換個形狀」）`prefix_zh: 擴散 → 易形`。只有這一行。

### 1.3 「被利用時」算進關鍵字推導（第 3 項）

- 做成資料：`content/skill_keywords.yaml` 每個關鍵字的 `uses` 裡，每條 `{condition: target_has_status, status: X}`／`{condition: target_on_surface, surface: Y}` 下面加一條 `{trigger: on_keyword_exploited, status: X}`／`{…, surface: Y}`（共 10 條：點燃 燃燒、火、油；潮濕 水；冰凍 冰凍、冰；倒地 倒地；標記 標記；中毒 中毒、毒）。推導程式沒改（既有的 `trigger` 規則本來就比對 `status`、`surface`）；沒限定的觸發沒有參數可比，照舊不算任何關鍵字。
- 為什麼做成資料而不是改推導程式：推導表內嵌在戰鬥規則包裡（裝備詞條「技能強化」依關鍵字選技能），改表會由 `ruleset_hash` 區分新舊紀錄，不需要升 `LOG_FORMAT`；改程式的話同樣的規則包會算出不同結果。
- 檔頭補一段說明；新測試鎖「條件收了的狀態、表面」和「觸發」兩邊一一對應，之後加條件忘了加觸發會失敗。

## 2. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive 11065f916` 的 `src content config` 解開、`PYTHONPATH` 指向舊 `src`（腳本印出載入的 `trpg` 路徑確認）；地圖預設陣容、效用 AI、`max_rounds=30`；整份事件、步驟、最終狀態（去掉 `ruleset`、`ruleset_hash`、`format`）比 SHA-256。10 張一般圖（bridge_chasm、cliff_outpost、dark_forest、frozen_lake、lava_crossing、narrow_halls、oil_depot、open_plain、ruined_fort、swamp）× 種子 1、2 ＋ 4 張頭目圖（bandit_lair、rift_gate、cloud_summit、molten_heart_pit）× 種子 3～12，同 SK-3b。

| 時間點 | 結果 |
|---|---|
| 第 1 項做完 | `battles=60 events=23897 different=0` |
| 第 2 項做完 | `battles=60 events=23897 different=0` |
| 第 3 項做完 | `battles=60 events=23897 different=0` |

- 第 1 項預期 different=0 的理由成立：地圖預設陣容沒有單位帶 `on_keyword_exploited`（`collect_exploit` 沒有持有者就直接返回），修正規則多算的利用沒有人收。
- `trpg battle --map open_plain --seed 7 --log-json` ＋ `trpg battle replay`：「重播驗證通過：91 個動作、383 個事件，最終狀態一致」。

## 3. 快照、夾具（先預測再逐鍵核對）

| 東西 | 預測 | 結果 |
|---|---|---|
| parity `flash`（126 鍵） | 第 2 項：帶「擴散・」名稱的鍵的雜湊變，其他不變；名稱以外不能有差異 | 先把改前／改後每個鍵的完整提議 JSON（3 次挑選，不雜湊）倒出來：**44 鍵不同、82 鍵相同**；44 鍵的改後＝改前把「擴散・」換成「易形・」，逐鍵相等（其他差異 0）；改前的雜湊和夾具 126 鍵全部相符（確認倒出來的和夾具同一套算法）。只用腳本改這 44 個值（`refactor_3wr2.json` 44 行），沒有整份重產；`-m slow -k flash` 全過 |
| parity 數量 | 規格寫「約 87 處」 | 實際是 44 個名稱在 44 個鍵（每鍵一個）。87 可能是別的算法（例如連說明一起算）；這份樣本裡就是 44 |
| parity `complete`／`retier` | 不變（不走閃現） | 沒動，`tests/skillgen` 全過 |
| 關鍵字推導（全部 433 招） | 第 3 項：只有餘燼共鳴（利用＋點燃）、潮引（利用＋潮濕）變 | 腳本倒出每招的製造／利用（全部與只看專屬）、分級，改前改後比：**只有這 2 招**；兩招都是專屬規則（`exclusive`），分級多 `uses:ignite`、`uses:wet` |
| 技能池 | 非起始池：點燃＋餘燼共鳴、潮濕＋潮引；起始池不變（兩招是史詩被動，不能當起始技能） | `keyword_pools` 四種組合（starter × exclusive）：只有 `starter=False` 的兩種各多這 2 招，起始池不變 |
| 挑選模式 | 打分看專屬關鍵字；組合器做出的限定狀態／表面被動會多一個利用關鍵字，可能改到某些種子的排序 | `tests/skillgen` 全過（挑選模式沒有鎖到受影響的樣本） |
| CLI `skills_show_all`（預測 02、12 兩片） | 以為 `skills show` 會印關鍵字 | **預測錯**：`skills show` 不印推導的關鍵字，`-m slow tests/cli` 44 全過、沒重產 |
| `skill_icons.json` | 圖示不看關鍵字 → 不變 | `tests.narrative.icon_fixture.render()` 和檔案逐字相同 |
| `glossary.json`、`unitDolls.json`、`raceLooks.json`、`skillCards.json` | 不變 | `export_client_fixtures.py` 重產後無差異 |
| `flashChoice.json`（開發頁夾具） | 不變 | 重產後有差（47 行加、930 行刪），但**拿掉第 3 項重產也是同樣的差**，和第 2 項的改名也無關（差異裡沒有「擴散・」）：是本段之前就過期的夾具，沒有 commit，還原。見待決 4 |
| OpenAPI | 不變 | 沒有改 schema |

**版號**

| 版號 | 變動 |
|---|---|
| `LOG_FORMAT` | `trpg-battle-log/131` → **`/132`**（第 1 項：結算規則） |
| `PROMPT_VERSION`、`WLOG_FORMAT`、`CHAR_FORMAT`、`SAVE_FORMAT`、`WORLD_RULES_VERSION`、`flash-*` | 不升 |
| `ruleset_hash`、`content_digest` | 變（第 3 項推導表內嵌在規則包；第 2 項閃現模板在內容庫） |

**改到的既有測試**（斷言沒有放寬）：版號字面值 `trpg-battle-log/132` 8 檔、`LOG_FORMAT.endswith("/132")` 4 檔；`refactor_3wr2.json` 44 個值。

## 4. 新測試

- `tests/engine/test_exploit_rules_sk3c.py`（12）：修正條件成立且命中（施放、普攻）、沒有修正規則不算、落空（施放、普攻）、抵抗（餘燼循環＋只施加緩速的技能，命中但緩速被抵抗；對照組沒被抵抗時算一筆）、狀態是自己或沒有來源時不算、技能條件和兩條修正規則條件同時成立只算一筆、同一個製造者的不同關鍵字（水表面＋燃燒）各算一筆、只套用在技能的規則普攻不算。`collect_exploit` 用間諜包一層，數交出去的筆數（不只看觸發次數，因為每回合本來就最多 1 次）。
- `tests/content/test_keyword_exploited_derive_sk3c.py`（7）：推導表兩邊一一對應、觸發規則都是專屬且恰好限定一種、兩招示範進各自的池（全部與只看專屬）、拿掉限定後不算任何關鍵字、限定一個沒有關鍵字收的狀態（流血）不算。

## 5. 測試與檢查

分目錄、最多 `-n 8`（`tests/llm` 與 `tests/skillgen` 沒有同時跑）。

| 指令 | 時間點 | 結束碼 |
|---|---|---|
| `uv run ruff check src tests scripts` | 每個 commit 前 | 0 |
| `uv run ruff format --check src tests` | 每個 commit 前 | 0 |
| `uv run mypy`（1702 檔） | 每個 commit 前 | 0 |
| `uv run lint-imports`（14 kept） | 每個 commit 前 | 0 |
| `pytest` 引擎相關 29 檔（exploit、modifier、determinism、clone、版號字面值等，752） | 第 1 項 | 0 |
| `pytest` CLI 版號字面值 6 檔（43） | 第 1 項 | 0 |
| `pytest -m slow tests/skillgen/test_refactor_parity.py -k flash`（128） | 第 2 項 | 0 |
| `pytest tests/skillgen`（4555 passed、14 skipped） | 第 2 項 | 0 |
| `pytest tests/content`（3132） | 第 2 項 | 0 |
| `trpg content check`（695 檔、433 招） | 第 2、3 項 | 0 |
| `pytest tests/content tests/narrative`（3614） | 第 3 項 | 0 |
| `pytest tests/skillgen`（4555 passed、14 skipped） | 第 3 項 | 0 |
| `pytest tests/llm`（495；和 skillgen 分開跑） | 第 3 項 | 0 |
| `pytest tests/world tests/roguelite`（1607） | 第 3 項 | 0 |
| `pytest tests/api`（1324 passed、1 skipped） | 第 3 項 | 0 |
| `pytest tests/engine`（全部，5051；含第 1 項） | 第 3 項 | 0 |
| `pytest -m slow tests/cli`（44） | 第 3 項 | 0 |
| `pytest tests/test_architecture.py`（13） | 第 3 項 | 0 |
| 前端 `tsc --noEmit` | 第 3 項 | 0 |
| 前端 `vitest run qIcon flash skillCard`（24 檔、308） | 第 3 項 | 0 |
| 紀錄＋重播 `open_plain` 7 | 第 3 項 | 「重播驗證通過」 |
| 戰鬥不變比對 60 場 | 第 1、2、3 項 | different=0 |

沒跑：全量 `scripts/check.py`、`tests/sim`、前端全部 vitest、平衡量測與模擬（不變比對以外）。

## 6. 新增 `# noqa`

沒有。

## 待 PM 決定（規格沒寫到、我先採保守做法的地方）

| # | 事項 | 我的做法 | 其他選項 |
|---|---|---|---|
| 1 | 「同一個製造者、同一個目標只算一筆」的鍵 | 鍵是（製造者、**狀態或表面**、對象）：同一個製造者在同一個目標上的**不同**關鍵字（例：U3 造的燃燒＋U3 造的水）各算一筆。照字面「同一個製造者、同一個目標只算一筆」會把第二筆丟掉，而被動可能限定了狀態或表面（潮引只收水），丟掉就會讓本來該觸發的被動不觸發——和玩法 PM「算重複也沒有差別、只是紀錄乾淨」的前提不合。完全相同的鍵合併後觸發結果不變 | 照字面只算第一筆（要定哪一筆優先） |
| 2 | 擲骰事件不算「作用在目標上」 | `attack_rolled`、`status_save_rolled`、`maneuver_rolled` 不算生效。這也改了 SK-3b 的條件型利用：只施加狀態的技能被抵抗時，以前會算利用、現在不算（規格「抵抗不算」）。地圖預設陣容沒人收，不變比對不受影響 | 只對修正規則的利用這樣判斷，SK-3b 的照舊 |
| 3 | 推擊、絆倒、互動 | 只做施放與普攻（含藉機攻擊、普攻連擊）。推擊的 `push_distance_delta` 規則條件也看目標，但規格講的是「那次攻擊」，推擊、絆倒是對抗動作，沒做 | 推擊、絆倒的對抗成功也算 |
| 4 | `client/src/dev/fixtures/flashChoice.json` 過期 | 本段之前就和 `export_flash_choice_fixture.py` 的輸出不一致（47 行加、930 行刪；拿掉本段改動重產也一樣），不是本段造成的，沒 commit | 下一段順手重產並逐項核對 |
| 5 | 規格寫閃現夾具「約 87 處」 | 實際 44 處（126 鍵中 44 鍵、每鍵一個「擴散・」名稱）；照實際逐鍵核對 | — |

## 開發 PM 裁定（2026-11-19）

合併：main（--no-ff）。三次不變比對 different=0；`LOG_FORMAT` /132 接受。

1. 「只算一筆」以（製造者、狀態或表面、對象）為單位：接受。照字面只算一筆會讓只收某個元素的被動漏觸發，這樣做才合乎 4.1.31「不重複算」的用意。已告知玩法 PM。
2. 被豁免、對抗擋下的不算作用在目標上，SK-3b 的條件型利用也跟著改：接受，這正是 1.1 的「抵抗不算」。已告知玩法 PM。
3. 修正規則的利用目前只在施放與普攻：推擊、絆倒、互動要不要也算，轉玩法 PM。
4. `client/src/dev/fixtures/flashChoice.json` 早已過期：排進下一個前端段重產，逐項核對。
5. 閃現夾具實際 44 處（計畫寫約 87）：照實際。
