# Phase KW 計畫：連擊、怒氣、專注、氣掛成關鍵字（#161）

依據：`docs/design/06-技能.md` 6.27.1（清單 12 → 16）、6.32.1（玩法 PM 51849cda4）、`docs/玩法決定紀錄.md` #161、
`docs/玩法PM交接.md` 第 4.1 節 #161 列。使用者核可：「兩題都排」（專案 PM 轉達）。
平衡疑慮已由玩法 PM 記在 `docs/design/平衡待查.md` 第 20 項，這裡不量。

## 0. 現況（開工前查過）

| 項目 | 現況 |
|---|---|
| 層數 | `content/stacks.yaml` 已有 `combo_point`（連擊點，上限 5，武器技命中 +1）、`fury`（怒氣，上限 4，受傷 +1）、`focus`（專注，上限 3，回合結束沒移動 +1，下一招自動消耗）、`ki`（氣，上限 3，普攻命中 +1，加成傷害與治療自己）；四者除怒氣外 `composer: false` |
| 自動累積 | `engine/stack_gain.py`：只有身上帶「消耗這種層數」的技能的單位才累積；`weapon_skill_hit` 是**每一筆命中判定 +1**，所以雙匕首（DD-1 打兩下）的單體武器技一次施放會 +2 |
| 消耗 | `consume_stack`（`Cast.consume_stacks`：命中判定之後、第一個效果之前消耗，換成加成）；`cost.stacks`＝層數不足不能施放 |
| 示範招 | 8 招（連環快刺、連擊終結、穩穩瞄準、專注一擊、震擊、沉息癒傷、怒火中燒、怒氣爆發），全是 1 階手寫；目前推導出的只有通用關鍵字（倒地、高處、潮濕），**沒有專屬關鍵字** |
| 「層數達 N」條件 | **沒有**。`cost.stacks` 只能擋整招，效果層級的「滿 5 層讓目標流血」做不到 |
| 「自己站在高處」條件 | **沒有**。`height_advantage` 是「比目標高」，被動對自己判斷永遠不成立 |
| 關鍵字開關 | `KeywordDef.start_hidden`（開局選單與許願池不顯示，三選一照常；3-53b 中毒池補齊前用過）、`composable`（隨機組合器能不能做） |
| 前端 | 關鍵字圓章 `client/src/render/qIcon/keywords.ts` 的 `LIST`（12 個）、顏色 `render/palette.ts` 的 `KEYWORD_COLOR`、創角圖示 `ui/CreateIcons.tsx` 的 `KEYWORD_ICON_IDS`；層數在 HUD 只有文字「層數 連擊點×3」（`ui/Hud.tsx`） |

## 1. 和既有資源機制的關係

- **不新增資源**：四個關鍵字直接掛在既有的四種層數上（關鍵字 ID ＝ 層數 ID：`combo_point`、`fury`、`focus`、`ki`），
  上限、自動累積、消耗、加成全部沿用 `stacks.yaml`。
- **製造**＝技能本身有 `add_stack` 這種層數；`stacks.yaml` 的 `gain`（自動累積）是背景規則，**不算製造**（6.32.1）。
- **利用**＝技能有 `consume_stack` 這種層數，或條件寫「這種層數達 N 層」（KW-1 新條件 `self_stack_at_least`）。
  `cost.stacks`（層數不足不能放）一定伴隨 `consume_stack`，已被前一條涵蓋。專注的「下一招自動消耗」（`auto_consume`）
  是背景規則，不算利用（否則每一招傷害技都成了專注技）。
- **裝備充能詞條**（`affix_charge_fury` 等）照舊；裝備的關鍵字推導另有一套（`gear_checks`），這次不動。
- 聖能、靈魂碎片、寒霜、靜電、破甲印、過載電流不掛（6.32.1），靜電與過載電流照舊歸「帶電」。

## 2. 分段

### KW-1：關鍵字推導、「層數達 N」條件、雙匕首每次出招 +1（後端，本段）

範圍：

1. **四個關鍵字**加進 `content/skill_keywords.yaml`（放在「形態」之後，順序＝顯示順序）：
   - `makes: [{effect: add_stack, stack: <id>}]`；
   - `uses: [{effect: consume_stack, stack: <id>}, {condition: self_stack_at_least, stack: <id>}]`；
   - `start_hidden: true`（池子在 KW-2 補齊前，開局選單與許願池不出現；三選一、閃現、工坊、推導照常）；
   - `composable: false`（`stacks.yaml` 這幾種層數還是 `composer: false`，組合器做不出來，KW-2 一起打開）。
2. **新條件 `self_stack_at_least`（施放者的某種層數達 N 層）**：
   - 參數 `stack`（層數 ID，必填，只能是 `owner: self` 的層數）、`count`（1～該層數的上限，必填）。
   - 只看施放者（`CASTER_CONDITIONS`）。技能層級：層數不足不能施放（和 `cost.stacks` 一樣擋，但不消耗）。
     效果層級：**以這次施放開始時的層數判斷**（`Cast` 在消耗之前記一份快照），所以終結技
     「花光每層加傷；滿 5 層讓目標流血」照寫就會成立，同一招自己累積或消耗的層數不影響判斷。
   - 文字：「自身『連擊點』達 3 層」。預算倍率：`harshness: common`（占位）。
   - **第一版 `handwritten_only: true`**：只給 `content/skills/` 手寫技能；LLM 提議、隨機組合器、白板、工坊的選項
     不開放（同 DD-3 `all_strikes_hit`）。KW-2 視技能池需要再決定要不要放寬（待 PM）。
   - 裝備條件數值不能用（不加進 `SELF_EVALUABLE_CONDITIONS`）。
3. **雙匕首每次出招 +1 連擊點**（6.32.1）：`weapon_skill_hit` 的自動累積，同一次施放對同一個目標最多 +1
   （連擊武器多打的那幾下不再加；第一下沒中、第二下中照樣 +1）。範圍型武器技打中幾個目標仍是每個目標 +1（現況，待 PM）。
4. 版號：`LOG_FORMAT` `/119` → `/120`（第 3 點改了結算；第 2 點新增條件與 `ConditionSpec` 欄位）。`WORLD_RULES_VERSION` 不升
   （世界的規則程式沒變，關鍵字變動由 `content_digest` 自然標成不能重播）。

要改的檔案：

- 內容：`content/skill_keywords.yaml`、`content/skill_conditions.yaml`。
- schema 與驗證：`src/trpg/content/skills/conditions.py`（`ConditionSpec.stack`／`count`，`exclude_if` 空值不輸出、
  `param_values`、`condition_text` 加 `stack_name`）、`content/skills/constants.py`（`REQUIRED_CONDITIONS`、
  `CASTER_CONDITIONS`）、`content/skills/problems.py`（`stack` 參數存在且是自身層數、`count` ≤ 上限）。
- 引擎：`engine/skills/conditions.py`（`_caster_condition_met`、條件句帶層數名）、`engine/skills/cast.py`（施放開始的層數快照，
  `holds` 讀快照；**不加實例欄位**，用類別屬性預設，見引擎筆記第 28 點）、`engine/stack_gain.py`（同一次施放同一目標去重）、
  `engine/runner.py`（`LOG_FORMAT`）。
- 文字：`narrative/skills.py`、`api/flash_changes.py`（條件句帶層數名）；`skillgen/budget.py`（如需，條件參數不影響倍率則不改）。
- 不動：`content/world/`、敵人內容、敵方 AI（RG 段在改）、`docs/design/`、前端。

驗收：

1. `trpg content check` 通過；四個示範累積招推導出「製造 <關鍵字>」、四個消耗招推導出「利用 <關鍵字>」
   （怒火中燒是被動 `add_stack fury`＝製造怒氣），通用關鍵字（倒地、高處、潮濕）照 #54 不再顯示。
2. 行為一致測試（實際跑引擎）：
   - 條件在技能層級：層數不足時不在 `legal_actions`、`skill_problem` 有中文原因；足夠時能放且不消耗。
   - 條件在效果層級：終結技先消耗、但「滿 N 層」的效果照施放開始的層數成立；N−1 層時不成立。
   - 不是 `owner: self` 的層數、`count` 超過上限、缺參數、非手寫技能用它 → 驗證擋下。
   - 雙匕首施放單體武器技兩下都中 → 連擊點 +1；第一下沒中第二下中 → +1；兩下都沒中 → 0；單手武器照舊 +1；
     範圍武器技打中兩個目標仍是 +2。
3. 確定性：hypothesis 性質測試（同種子同步驟兩次結算的事件與狀態相同；連擊點每次出招最多 +1）；一場重播通過。
4. 既有戰鬥不變：預設地圖陣容沒有人帶連擊點的消耗技，8 張地圖 × 2 種子＋3 張頭目圖的事件、步驟、最終狀態
   （去掉內嵌規則包）與改前相同；`ruleset_hash` 全變是因為內容（關鍵字表、條件表）。
5. slow 的 parity、CLI 快照：先列預測會變的鍵，再和實際失敗比對，只重產預測內的。
6. `ruff check`、`ruff format --check`、`mypy`、`lint-imports` 通過。

### KW-2：技能池補齊與周邊系統（內容為主）

範圍：

1. **示範招**（數值照工坊占位，`provenance.origin: builtin`）：
   - 連擊：疾刺（打中 +1，從背後打中再 +1：`add_stack` 兩條，第二條帶 `from_behind`）、掠影步（移動 2 格並 +1：
     `dash`／`leap`＋`add_stack`）、斷喉（終結技：`consume_stack` 每層加傷＋`apply_status: bleed` 帶
     `self_stack_at_least {stack: combo_point, count: 5}`）。
   - 怒氣：血怒（自傷＋`add_stack fury 2`）、怒吼（`apply_status: taunted` 身邊敵人＋`add_stack fury 1`）、
     狂暴劈砍（花光每層加傷）、咬牙撐住（花光每層一層護盾：`stacks.yaml` 的 `fury.consumer.boosts` 加 `shield`）。
   - 專注：凝神（+1、自己帶 `root` 1 回合）、鷹眼（被動 `on_turn_end`，條件「自己站在高處」+1）、
     貫心箭（花光每層加傷；`self_stack_at_least {stack: focus, count: 3}` 時標記目標）。
   - 氣：寸勁（打中 +1、推開 1 格）、調息（回一點血、+1）、氣功波（花光每層加傷）、內觀（花光每層治療自己）。
   - 既有 8 招算進池子（6.32.1「現有示範招算進去」），名字重複的（例：震擊／寸勁）由玩法 PM 決定留哪個。
2. **池子門檻**（6.27.2）：每個新關鍵字至少 3 招 1 階白板、3 招主動的專屬利用者；不足的開發補齊（白板配方或手寫）。
3. 拿掉這四種層數的 `composer: false`、關鍵字的 `composable: false` 與 `start_hidden: true`：隨機組合器、
   開局選單（創角照 6.27.3 選 2 個、兩招要能互相觸發）、許願池選單與 LLM 對照清單都出現。
4. 閃現「加第二個關鍵字」：`content/skill_evolution.yaml` 的 `grafts` 加四筆（製造方＝打中時多累積 1 層、
   利用方＝消耗層數這招多傷一截）；大標（`flash_templates.yaml` 的 `headlines`）**由玩法 PM 補**，先留空走既有退路。
5. 需要的引擎能力：
   - 新條件「自己站在高處」（鷹眼）：施放者所在格高度 ≥ 1（占位，待 PM；飛行算不算另問）。
   - 視池子需要，`self_stack_at_least` 是否開放給白板、LLM、工坊（KW-1 先關）。
6. 登記處（上手筆記第四節第 1、26 點）：技能圖示快照、`test_skill_scaling.py` 招數、`test_tuning_fields_nw2a.py`、
   `refactor_3wr2.json` 只加新招、CLI 快照、`qIconQi2d.test.ts` 的 `ADDED_AFTER_BASELINE`、`test_coverage.py`。

驗收：每個新關鍵字池達門檻（測試鎖住）；創角可選四個並顯示觸發關係；許願池出現；組合器能做出四種層數的累積與消耗；
閃現有第二關鍵字選項；parity／快照只重產預測內的鍵。

### KW-3：前端顯示與美術移植

範圍：關鍵字圓章四個新圖樣與顏色、創角圖示、層數 HUD 的圖示化顯示（依第 3 節美術需求，美術 PM 出樣張後才排）；
`client/src/render/qIcon/keywords.ts`、`render/palette.ts`、`ui/CreateIcons.tsx`、`ui/Hud.tsx`、開發頁 `dev/keywordGallery.ts`。
瀏覽器：電腦版 Chrome、Edge 為主，Firefox、Safari 可降級。驗收要每項都有截圖（實機到不了用開發頁畫）。

## 3. 美術需求（交美術 PM）

| 項目 | 要什麼 | 放哪 | 大小 |
|---|---|---|---|
| 關鍵字圓章圖樣 ×4 | 連擊（建議：兩道交叉的短刃殘影＋小數字點）、怒氣（紅色怒焰／青筋記號）、專注（瞄準的眼／靜止的同心圓）、氣（螺旋氣旋）；沿用第 5b 批規則：深色圓底混 28% 關鍵字色、外圈 1 裝置像素外框、≤14px 只留一個主體 | `client/src/render/qIcon/keywords.ts` 的 `LIST`（和既有 12 個同格式：`zh`、`topic`、`src`、`k`、`d`） | 圓章＝裝備格邊長 × 0.42（32→13.5、42→17.5、48→20、64→27 px），圖樣 ±10 單位座標 |
| 關鍵字色 ×4 | 和既有 12 色分得開（尤其怒氣 vs 點燃、氣 vs 召喚物） | `render/palette.ts` 的 `KEYWORD_COLOR`；`ui/CreateIcons.tsx` 同色 | — |
| 創角關鍵字圖示 ×4 | 創角畫面的關鍵字按鈕圖示，畫法同既有 12 個 | `ui/CreateIcons.tsx`（`KEYWORD_ICON_IDS` 與 `switch`） | 同既有（按鈕內約 28～32 px） |
| 層數計量（HUD） | 四種層數在角色面板／HUD 的「格子式」計量（連擊 5 格、怒氣 4 格、專注 3 格、氣 3 格），滿層有亮起效果；取代目前的文字「層數 連擊點×3」 | `ui/Hud.tsx`（新元件，建議 `ui/StackPips.tsx`） | 每格約 8～10 px，整條不超過 60 px 寬 |
| 技能圖示部件 | 新條件「層數達 N」在技能組裝列的條件部件（`render/qIcon/parts.ts` 的 `COND`），可先借用既有部件暫代 | `render/qIcon/parts.ts` | 同既有條件部件（18 px 圓片） |

## 4. 待 PM 決定

1. **設計寫「引擎：不新增機制」，但「層數達 N」與「自己站在高處」都沒有現成條件**：規格先照 6.32.1「利用＝消耗或
   『層數達 N 時』」新增條件 `self_stack_at_least`（KW-1），「站在高處」留 KW-2。
2. `self_stack_at_least` 的判斷時機：**施放開始時的層數**（同一招自己消耗或累積的不算）。預算倍率先用 `common`（0.85）。
3. `self_stack_at_least` 第一版只給手寫技能（`handwritten_only`）；要不要開放給 LLM、白板、工坊、閃現，KW-2 前問。
4. 雙匕首「每次出招 +1」解讀成「同一次施放對同一個目標最多 +1」；範圍武器技打中幾個目標仍每個 +1（現況）。
   雙匕首的**普攻**打兩下對「氣」（普攻命中 +1）仍是 +2，設計沒寫，照現況。
5. 關鍵字 ID 直接用層數 ID（`combo_point`、`fury`、`focus`、`ki`）；顯示名「連擊」「怒氣」「專注」「氣」。
6. 「自己站在高處」的定義（KW-2）：所在格高度 ≥ 1？比相鄰格高？飛行算不算？
7. 示範招和既有 8 招同概念的（震擊 vs 寸勁、怒氣爆發 vs 狂暴劈砍、專注一擊 vs 貫心箭）要合併還是並存（KW-2）。

## 5. 不做

- 平衡量測、模擬報表；不改 `docs/design/`、`content/world/`、敵人內容、敵方 AI。
- KW-1 不碰前端（新關鍵字前端不認得時不畫圓章，`chip` 本來就會略過）。
