# Phase KW-1 完成報告｜連擊、怒氣、專注、氣掛成關鍵字（#161）第 1 段

> 規格：`docs/phases/PhaseKW計畫.md`（本段先寫，commit `781cf0811`）。依據 `docs/design/06-技能.md` 6.27.1、6.32.1（玩法 PM `51849cda4`）、`docs/玩法決定紀錄.md` #161。
> 基準：main `4ddce1e90`（worktree 開工時落後 main 16 個 commit，先 fast-forward 才拿到 #161 的設計）。`LOG_FORMAT` `/119` → `/120`；`WORLD_RULES_VERSION` 30 不變。
> 依使用者 11-13 指示沒有跑任何平衡模擬或量測；疑慮寫在第 7 節。沒有動 `content/world/`、敵人內容、敵方 AI（RG 段）、`docs/design/`。

## 1. 做了什麼

**內容**

- `content/skill_keywords.yaml`：四個新關鍵字接在「形態」之後（12 → 16），關鍵字 ID ＝層數 ID：`combo_point` 連擊、`fury` 怒氣、`focus` 專注、`ki` 氣。
  製造＝`add_stack` 這種層數；利用＝`consume_stack` 這種層數，或條件 `self_stack_at_least` 這種層數。`stacks.yaml` 的自動累積與專注的「下一招自動消耗」是背景規則，不算。
  四個都 `start_hidden: true`、`composable: false`（第 2 節）。
- `content/skill_conditions.yaml`：新條件 `self_stack_at_least`（自身層數達到；參數 `stack`、`count`；`harshness: common` 占位；`handwritten_only: true`）。
- 既有 8 招示範招（連環快刺、連擊終結、怒火中燒、怒氣爆發、穩穩瞄準、專注一擊、震擊、沉息癒傷）現在推導出專屬關鍵字（原本只有通用的倒地、高處、潮濕，照 #54 不再顯示）。內容檔沒改。

**引擎**

- `engine/skills/conditions.py`：`self_stack_at_least` 是施放者條件，施放外看 `unit.stacks`；條件不成立的中文原因「技能條件不成立：… 需要「自身「連擊點」達 3 層」」。
- `engine/skills/cast.py`：`Cast.run` 第一行記 `stacks_at_cast`（施放開始時的層數快照，類別屬性預設 `None`，不加進 `__init__`）；`holds` 遇到這個條件（含 `any_of` 分支）讀快照。所以終結技先花光層數，「滿 N 層」的效果照樣成立；同一招自己加的層數也不算。
- `engine/stack_gain.py`：武器技命中的連擊點（`weapon_skill_hit`）同一次施放對同一個目標最多 +1（`_collect(..., once=True)` 看還沒結算的 `ctx.fired`）。雙匕首兩下都中 +1、一中一不中 +1、都沒中 0；範圍武器技打中幾個目標仍各 +1。
- `engine/runner.py`：`LOG_FORMAT` `/120`（第 4 節）。

**schema、驗證、文字**

- `ConditionSpec` 新欄位 `stack`、`count`（`exclude_if` 空值不輸出：既有技能 JSON、規則包、parity 夾具不變）；`param_values` 加這兩個名稱。
- `content/skills/problems.py::_stack_condition_problems`：層數要存在、`owner: self`、`count` ≤ 上限；缺參數照既有規則擋。
- `condition_text(..., stack_name=)`：「自身「怒氣」達 3 層」；呼叫端（技能卡 `condition_summary`、閃現差異 `_condition`、引擎的不成立原因）都傳層數中文名，沒傳退回「層數」不露英文。
- `skillgen/validate.py` 的 `handwritten_only` 訊息改成「條件「<中文名>」目前只給內建技能用」、`option_params.HANDWRITTEN_ONLY_CONDITION` 拿掉「（雙牙）」（現在不只雙牙一個）。

**候選產生器**

- `start_hidden` 的意思擴大成「池子補齊前不主動提供」：開局選單、`run auto` 抽樣、許願池選單、**三選一的新方向**都不出現；已持有這種關鍵字的技能時，加深、橋接照常。實作是 `skillgen.candidates.new_direction_keywords`（`generate_candidates`、`generate_whiteboard_candidates` 共用）。目前內容只有這四個用 `start_hidden`。
  - 為什麼：第一版沒擋新方向時，`_weighted_order` 對每個「還沒有的關鍵字」擲一次骰，多 4 個關鍵字就改掉所有三選一的亂數，LLM 來源比例掉到 19/30（組合器做不出這四種層數），8 個固定種子測試翻掉（開局第二組、靶場 API、許願雙關鍵字、白板順序…）。擋住後這些全部回到原樣，池子在 KW-2 補齊時一次打開。

**前端（只為了名詞表多一個條件）**

- `client/src/battle/fixtures/glossary.json` 重產（多 `self_stack_at_least` 一筆；`skillCards.json`、`skill_icons.json` 重產後不變）。
- `render/qIcon/parts.ts` 的 `COND` 加 `self_stack_at_least`，**暫代**借「第一輪」的金色數字（畫的時候才查表）；`qIconSkills.test.ts` 條件數 20 → 21、`qIconQi2d.test.ts` 的 `ADDED_PARTS` 加一筆。
- `ui/entryScreen.test.ts`「每個關鍵字都有專屬小圖示」只對開局會出現的關鍵字（沒有 `start_hidden`）檢查，KW-3 拿掉時自動要求。

## 2. 測試

新增：

| 檔案 | 內容 |
|---|---|
| `tests/engine/test_stack_condition_kw1.py`（15） | 技能層級 0／2／3／5 層（不在 `legal_actions`、施放被擋的中文原因、足夠時不消耗）；效果層級 2／3／5 層（終結技先花光、「滿 3 層」護盾照開場層數）；同一招 +2 不算；`any_of` 分支也讀快照；雙匕首四種命中組合 → 1／1／1／0；匕首 +1；直線武器技打中兩人 +2 |
| `tests/engine/test_stack_keyword_properties_kw1.py`（3，hypothesis） | 同種子同狀態結算兩次，事件 JSON 與狀態 JSON 逐字相同；雙匕首每次出招連擊點最多 +1 且等於 `gained` 事件數；「滿 3 層」護盾 ⇔ 開場層數 ≥ 3（不論命中） |
| `tests/skillgen/test_stack_keywords_kw1.py`（22） | 表 12 → 16、名稱、順序；開局／許願池／新方向都沒有、組合器不做、持有時不出錯；8 招示範的製造／利用；條件推導成「利用」；一般武器技不帶這四個；五種壞條件（疊在敵人身上、超過上限、未知層數、缺 `count`、缺 `stack`）擋下；內建技能通過；工坊來源擋（`handwritten_only`）、不在 LLM schema、工坊選項標不可選；中文條件句；沒填不序列化 |

改到的既有測試（斷言不放寬，只把「池子門檻」類的規則限定在開局會出現的關鍵字，拿掉 `start_hidden` 時自動恢復）：

- `tests/skillgen/test_keywords.py`：`KEYWORDS`／`NAMES` 16 個、`PENDING`、`POSITIVE` 補四個關鍵字的製造／利用／條件例子；`start_ids` ＝前 12 個；每池 3 招的參數化測試對 `PENDING` 改斷言 `start_hidden`；`COMPOSABLE` 排除 `PENDING`。
- `tests/skillgen/test_keyword_pools.py`（3 招主動利用者）、`tests/skillgen/test_whiteboard.py`（每個關鍵字有 1 階白板）、`tests/roguelite/test_keyword_start.py`（開局池 3 招）、`tests/skillgen/test_evolution.py`（每個關鍵字有嫁接）、`tests/content/test_appearance.py`（裝備外觀關鍵字）：改看 `start_ids()`。
- `tests/content/test_coverage.py`：`_UNCOVERED["condition"]` 登記 `self_stack_at_least`（KW-2 的斷喉、貫心箭會用）。
- 版號：`/119` → `/120` 的 11 個檔（第 4 節）。

## 3. 檢查與結束碼

| 檢查 | 結束碼 / 結果 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0（1583 個檔） |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（667 個檔、409 個技能） |
| 直接相關的 pytest（68 個檔，`-n 8`） | 0：2098 passed、13 skipped |
| `trpg battle --map open_plain --seed 7` ＋ `replay` | 0、0：「重播驗證通過：91 個動作、383 個事件」 |
| 前端 `pnpm -C client typecheck` | 0 |
| 前端 `pnpm -C client test`（全部） | 0：344 檔、4386 項全過 |
| slow：parity、proposal、`tests/cli -m slow`（`-n 8`） | 0：940 passed（第 5 節） |

## 4. 版號

- **`LOG_FORMAT` `/119` → `/120`**：結算改了一處——武器技命中的連擊點自動累積，同一次施放同一個目標最多 +1（雙匕首原本 +2）；另外新增條件 `self_stack_at_least`、`ConditionSpec` 多兩個欄位（沒填不輸出）。身上帶連擊點消耗技、拿雙匕首施放單體武器技的 `/119` 紀錄重播會不同，所以照慣例遞增。`docs/phases/戰鬥紀錄格式變更.md` 加了 `/120` 一條。
  同步：`test_collided_sacrifice_firearm.py`、`test_self_costs.py`、`test_wind.py` 三個 `endswith("/120")`（三個重播測試照跑通過），另外 9 處寫死 `trpg-battle-log/120`（`tests/cli/` 6 個檔 7 處、`test_gear_g2.py`、`test_gear_g3a.py`）。
- **`WORLD_RULES_VERSION` 30 不變**：世界的規則程式沒改；關鍵字表與條件表是內容，`content_digest` 自然變，舊世界日誌照慣例標成「規則已變」。

**不變比對**（改前 `git archive 781cf0811 src content`、`PYTHONPATH` 指過去；地圖預設陣容、效用 AI、`max_rounds=30`；整份紀錄去掉 `format`、`ruleset_hash`、`setup.ruleset`、`final_state.ruleset`）：8 張地圖（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）× 種子 1、2 ＋ 3 張頭目圖 × 種子 3～12：**`battles=46 events=20499 actions=4227 different=0`**。預設陣容沒有人帶連擊點的消耗技，所以雙匕首的改動在這些場次不出現；`ruleset_hash` 全變是因為規則包內嵌的關鍵字表與條件表。

## 5. slow 測試：預測與實際

預測（跑之前寫下）：

| 測試 | 預測會變的鍵 | 理由 |
|---|---|---|
| CLI 快照 `skills_list`、`skills_show_all/00～15` | 無 | `skills list`／`show` 不印關鍵字（實測連環快刺的 `show` 沒有關鍵字行）；沒有內容技能用新條件 |
| CLI 快照 7 場戰鬥 | 無 | 不變比對 46 場 `different=0`；戰鬥文字不印版號 |
| parity `complete`、`retier` | 無 | 技能 JSON 沒變（新欄位空值不輸出） |
| parity `flash` | 至多 `skill_combo_finisher@11@1`、`@3@1`、`@5@2` | 126 條裡只有連擊終結的專屬關鍵字變了（多「利用連擊」）；嫁接表沒有新關鍵字 |
| `test_proposal_l8.py`、`test_proposal.py` | 無 | LLM schema 不含新條件 |
| `tests/cli/test_run_cli.py` slow（`run auto` 固定種子） | 無 | 新方向擋掉四個新關鍵字，三選一亂數取用不變 |

實際：`UV_NO_SYNC=1 uv run pytest -q tests/skillgen/test_refactor_parity.py tests/skillgen/test_proposal_l8.py tests/skillgen/test_proposal.py tests/cli -m slow -n 8` → **940 passed、0 failed**。和預測一致；連擊終結的 3 條閃現也沒變（預測是「至多」：連擊終結的閃現選項不看專屬關鍵字的那一部分）。**沒有重產任何夾具或快照。**

## 6. 美術需求

在 `docs/phases/PhaseKW計畫.md` **第 3 節**：四個關鍵字圓章圖樣與顏色、創角圖示、層數 HUD 格子計量、「層數達 N」條件部件（KW-1 先借「第一輪」暫代）。

## 7. 平衡疑慮（沒量，轉玩法 PM 記進 `平衡待查.md`）

1. `self_stack_at_least` 的預算倍率用 `common`（0.85）占位：「滿 5 層」實際很難達成，可能偏貴；反過來 1～2 層幾乎隨時成立，可能偏便宜。倍率不隨 `count` 變。
2. 雙匕首每次出招只 +1 後，雙匕首在連擊這條路線上沒有額外優勢（平衡待查第 20 項第 3 點已記，KW-1 照 #161 做）。
3. 範圍武器技打中幾個目標各 +1 連擊點（現況），範圍技集連擊點比單體快很多。

## 8. 待 PM 決定

1. **設計寫「引擎：不新增機制」，但「層數達 N」沒有現成條件**：照 6.32.1「利用＝消耗或『層數達 N 時』」新增條件 `self_stack_at_least`。KW-2 的鷹眼「站在高處時」也需要新條件（規格 KW-2 第 5 點）。
2. 條件判斷時機：**施放開始時的層數**（同一招消耗或累積的不算）。
3. 條件第一版 `handwritten_only`：LLM、工坊、白板、閃現不能用；KW-2 補池子時要不要開放（白板「利用者」可能需要）。
4. 「雙匕首每次出招 +1」解讀成「同一次施放同一個目標最多 +1」；範圍武器技仍每個目標 +1。雙匕首**普攻**打兩下對「氣」（普攻命中 +1）仍 +2，設計沒寫，照現況。
5. `start_hidden` 擴大成也擋三選一的「新方向」（原本只擋開局）。這樣 KW-1 不改任何既有的三選一結果；代價是 KW-2 前玩家不會在三選一「新方向」看到這四個關鍵字（持有示範招時加深、橋接照常）。
6. 關鍵字 ID 直接用層數 ID（`combo_point` 等）；顯示名「連擊」「怒氣」「專注」「氣」與說明文字是我擬的，玩法 PM 可改（`skill_keywords.yaml` 的 `name_zh`、`description_zh`）。

## 9. 需要使用者決定的事

- 沒有新的規則類問題需要直接問使用者；第 8 節第 3、4 點屬規則解讀，建議由玩法 PM 帶原話確認後在 KW-2 一起改。
- 請使用者重開伺服器時注意：內容（關鍵字表、條件表）變了，進行中的一輪會從頭開始、世界日誌標成不能重播；`/119` 的戰鬥紀錄不能重播。畫面上目前看不到新關鍵字（開局、許願池、三選一新方向都先隱藏）；持有那 8 招示範招時，技能卡的關鍵字依推導改成連擊、怒氣、專注、氣（取代原本標灰的倒地、高處、潮濕；前端不認得的關鍵字沒有圓章圖示）。

## 10. 其他

- `# noqa`：沒有新增。
- 交件後要接的段：KW-2（示範招 14 招、池子門檻、拿掉 `start_hidden`／`composable: false`／`composer: false`、許願池、閃現嫁接、鷹眼的條件）、KW-3（美術移植）。

## 開發 PM 裁定

- 接受，已合併。`LOG_FORMAT` 的 `/120` 和 RG-1 合為同一版，戰鬥紀錄格式變更.md 已合併成一條。
- 池子門檻測試暫時縮小檢查範圍：專案 PM 同意，附兩個條件。
  1. 測試要有註解或會失敗的提醒：已符合。PENDING 斷言在 start_hidden 拿掉時會失敗。
  2. KW-2 交件時，要列出恢復前後檢查的關鍵字數。
- 待 PM 決定 1～7 與平衡疑慮轉交玩法 PM，見 `docs/開發PM交接.md` 的「待轉玩法 PM」節。第 3、4 點建議帶使用者原話確認。
