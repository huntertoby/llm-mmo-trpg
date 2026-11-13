# Phase RG 計畫：加深雲嶺與灰燼荒原（瞄準預告、盾兵、陷阱痕跡、精英單挑）

依據：`docs/玩法決定紀錄.md` #162、`docs/design/05-戰鬥.md` 5.7（遠程瞄準預告、敵人陷阱的痕跡）、
`docs/design/06-技能.md` 6.3.1（陷阱可見性那一句）、`docs/design/09-世界與敘事.md` 9.6.6（強招預告、盾兵、精英單挑）、
`docs/design/18-雲嶺內容.md` 18.2.1「加深內容」、`docs/design/19-灰燼荒原與賽季主線.md` 19.2.1「加深內容」；設計 commit 967363244。
使用者核可排段：「兩題都排」（專案 PM 轉達）。數值一律照工坊（使用者自己調），本計畫只給初值、不附模擬報表。

> 命名：既有的基本動作「瞄準」（`aim`，命中加值）已經佔用 `aim` 這個字，本計畫的「瞄準預告」在程式裡叫 **lock-on**
> （技能欄位 `lock_on`、狀態欄位 `lock_target`），畫面上的中文照設計叫「瞄準」「被瞄準」。

## 0. 分段

| 段 | 範圍 | 主要檔案 | 依賴 |
|---|---|---|---|
| **RG-1** | 引擎＋內容：瞄準預告（宣告、釋放、四種應對、打斷）、盾兵掩護（單位提供的掩護）、AI（敵人會瞄準、盾兵站到遠程同伴前面、遠程偏好站在盾兵後面）、三招瞄準招與兩種盾兵、遭遇表；API 的蓄力資料帶被瞄準的人 | `engine/delayed.py`、`engine/rules/combat.py`、`engine/skills/interpreter.py`、`engine/ai/`、`content/skills/`、`content/units/`、`content/world/encounters/` | 無 |
| **RG-2** | 引擎＋世界：敵方陷阱的「可疑痕跡」與「看那一格一眼」；精英單挑（提出、接受／拒絕、一對一組場、獎勵不變）；荒原狂戰士（怒氣） | `engine/traps.py`、`engine/view.py`、`event_filter.py`、`world/`、`content/world/` | 狂戰士要等 KW（#161 怒氣關鍵字）合併；KW 沒合併時狂戰士拆成 RG-2b |
| **RG-3** | 前端：被瞄準標記與瞄準線、盾兵擋住的提示、可疑痕跡、看一眼的演出、單挑對話框；換上美術 PM 的圖 | `client/src/` | RG-1、RG-2；美術需求（第 5 節） |

## 1. RG-1：瞄準預告與盾兵（引擎＋內容）

### 1.1 瞄準預告的規則（05 5.7）

技能欄位 `lock_on: true`（`SkillDef`，沒填不輸出）＝這招是「強力一擊」，施放分兩步：

1. **瞄準（宣告）**：照一般施放檢查合法性（射程、視線、隱蔽距離、目標）並**付全部代價**（AP、法力或耐力、冷卻）；
   不擲命中、不結算效果。施放者身上加 `charging`（`skill_id`＝這招、`lock_target`＝目標單位 ID、`remaining` 1），
   發 `followup_charged`（`lock_target_id` 帶目標；`pos`、`tiles` 是目標**當下**的格子）。施放後面向目標。
2. **射出（釋放）**：施放者**下一個自己的回合開始**時（同延遲段的釋放時機：狀態與表面的回合開始效果之後、被動
   `on_turn_start` 之前），依序檢查，第一個不成立的就落空（`effect_fizzled`，`effect_kind: followup`）：
   1. 目標還站著 → 否則 `lock_on_lost`。
   2. 目標沒有隱蔽（`is_concealed` 而且施放者沒有靈覺看穿；**不論距離**）→ 否則 `lock_on_concealed`。
   3. 照一般施放的選取仍然合法（射程、視線；被掩護物斷了視線就不合法）→ 否則 `lock_on_lost`。
   4. 施放者到目標的直線上（`bresenham` 兩個方向的格子，不含兩端）沒有**目標陣營**的存活單位（含召喚物）→ 否則
      `lock_on_blocked`（隊友擋在中間）。施放者自己陣營的單位（例如盾兵）不擋。
   全部成立：`skill_followup`（`when: delayed`）之後照一般施放結算這招（擲命中、傷害、狀態；半掩護、盾兵掩護照常算）。
3. **打斷**：瞄準中的施放者**被近戰攻擊命中**（普攻或技能，傷害結算後仍站著；`hit_reactions` 的 `melee` 判斷）時，
   瞄準取消（`followup_cancelled`，新原因 `interrupted`）。既有的取消照舊：倒下、暈眩或冰凍、法術型被沉默、改瞄另一個。
4. 「被瞄準的人」頭上的標記與弓手到目標的線，畫面讀蓄力資料的 `lock_target_id`（RG-3 畫）；不另加狀態到目標身上。
5. 一般敵人的意圖照舊不顯示；瞄準預告不受這條限制（設計原話）。

內容檢查（`skills/problems.py`）：`lock_on` 只能用在 `enemy_only`、`kind: active`、形狀 `single`、沒有 `followup`、
不是陷阱、不是常駐類的招；第一個效果要對敵人。

### 1.2 盾兵掩護（09 9.6.6）

帶標籤 `shield_guard` 的單位替**相鄰的遠程同伴**擋遠程攻擊：

- 同伴＝同陣營、存活、不是盾兵自己、武器不受高度限制（射程 > `melee_height_limit_max_range`，弓、法杖、槍；
  和「近戰」的既有定義相反）。
- 幾何照半掩護物件（`cover_object_between`）：盾兵在同伴四方向相鄰、而且在同伴朝向攻擊者的那一側（內積 > 0）；
  盾兵視為 1 層高（攻擊者高出盾兵所在格 1 層以上、或同伴站得比盾兵高 1 層以上時擋不到）。所以**繞到側面**、
  把盾兵**推開、撞開**都會讓掩護消失（設計原話的應對）。
- 只對遠程攻擊（近戰、穿透、無視掩護的武器照舊不吃）。命中 −`shield_guard_hit_penalty`（`rules/core.yaml`，
  初值 2，同半掩護；開放工坊）。
- 不疊加：場上掩護物優先，其次盾兵，最後自己的塔盾（照既有「兩者不疊加」）。同時有多名盾兵時取上、右、下、左順序的第一個。
- 紀錄：`attack_rolled.cover` 照舊、`cover_unit_id` 帶盾兵（沒有不輸出）；預覽 `cover` 說明寫「被 X 的盾擋住」。

### 1.3 AI

- **敵人會瞄準**：預覽瞄準招時另算一份「現在就射出」的預覽（`Preview.lock_fire`，`Ctx.fire_lock` 只在預覽模擬用），
  效用 AI 的預覽收益改用它 × `rewrite.lock_on_permille`（`ai_profiles.yaml`，初值 700：對手可能躲開）。
  （實作時發現：只用延遲段的「範圍內敵人數」估值，瞄準招的分數固定約 21，永遠輸給普攻，等於 AI 不會瞄準；改成這樣後
  和改之前的高處狙擊一樣，平地普攻、居高臨下時瞄準。）
- legal_actions 不列瞄準招的物件目標（瞄準只對單位）。
- **盾兵站到遠程同伴前面**：位置價值新權重 `screen`（`AiWeights`）：盾兵每替一名相鄰遠程同伴擋住至少一名打得到它的敵人
  （幾何同 1.2）加 `screen` 分。只對帶 `shield_guard` 的單位算，其他單位 0。`guard` 行為模式填 `screen: 12`（初值）。
- **遠程偏好站在盾兵後面**：既有位置價值 `cover`（`_covered_from`）也算盾兵提供的掩護。沒有盾兵的戰鬥不變。

### 1.4 內容（數值是初值，照工坊）

| 新招（`content/skills/`，都 `enemy_only`、`lock_on`） | 給誰 | 取代 | 初值 |
|---|---|---|---|
| `skill_crane_piercing_shot` 鶴唳穿雲 | 雲鶴使（冰鶴使變體跟著） | `skill_high_ground_shot`（主角弓手也在用，不改它） | 照高處狙擊：2 AP、耐力 10、冷卻 2、傷害 ×1000，居高再 ×800 |
| `skill_binding_talisman` 定身符 | 符籙師（雷符師變體跟著） | `skill_frost_shackle`（主角法師也在用） | 照寒鎖：1 AP、法力 5、冷卻 2、1d4 冰＋定身 1 回合 |
| `skill_lava_bomb` 熔岩彈 | 噴岩龜 | `skill_fire_wall`（19 的「熔岩彈」原本用火牆近似） | 2 AP、法力 10、冷卻 4；射程 5、3d8 火＋燃燒 2 回合（打擊骨架不能造火地，見待決 7） |

| 新敵人（`content/units/`） | 區域 | 初值 |
|---|---|---|
| `sect_shield_disciple` 持盾弟子 | 雲嶺 | 照盜賊盾衛：HP 24、速度 4、護甲 6、單手劍、`guard`、`[humanoid, sect, shield_guard]`、`skill_shield_bash`＋`skill_taunting_roar`（#149 一般敵人至少 2 招） |
| `molten_shell_trooper` 熔殼甲兵 | 荒原 | 照熔岩甲蟲體型：HP 30、速度 4、護甲 5、石拳、`guard`、`[beast, lava_beast, shield_guard]`、`skill_shield_bash`＋`skill_battering_ram`、火 −50%、冰 +50%、開場「熔殼迸裂」 |

遭遇表（不加新地點，**加新陣容**到現有地點，原有陣容不動）：

| 地點 | 新陣容 |
|---|---|
| 雲海吊橋 `cloud_sea_bridge`（遠程上限 1） | 吊橋盾陣：持盾弟子＋雲鶴使 |
| 古松祭壇 `old_pine_altar` | 祭壇盾陣：持盾弟子＋符籙師＋武僧 |
| 焦油坑 `tar_pits` | 熔殼與噴岩龜：熔殼甲兵＋噴岩龜＋餘燼蜥 |
| 熔岩洞窟 `lava_cave` | 洞窟熔殼陣：熔殼甲兵＋噴岩龜 |

### 1.5 API

`ChargeOut.lock_target_id: UnitId | None = None`（`TelegraphCharge`、`ChargeInfo` 同名欄位）；`text` 寫「瞄準 X：下回合射出」。
重產 `client/openapi.json`、`client/src/api/schema.d.ts`。前端不改畫法（RG-3）：在那之前目標格照既有「蓄」的預計範圍顯示。

### 1.6 要改的檔案

- 內容 schema：`src/trpg/content/skills/skill.py`（`lock_on`）、`skills/problems.py`（檢查）、`src/trpg/content/rules.py`
  （`shield_guard_hit_penalty`）、`src/trpg/content/environment.py`（`AiWeights.screen`）。
- 引擎：`engine/state.py`（`StatusInstance.lock_target`）、`engine/delayed.py`、`engine/charge_queries.py`、
  `engine/skills/interpreter.py`（宣告分支）、`engine/reactions.py`（`hit_reactions` 只新增一行呼叫打斷）、
  `engine/events/skills.py`（`lock_target_id`、`interrupted`）、`engine/events/combat.py`（`cover_unit_id`）、
  `engine/rules/combat.py`（盾兵掩護）、`engine/environment.py`、`engine/ids.py`、`engine/ai/utility/position.py`、
  `engine/ai/utility/scoring.py`、`engine/preview.py`（掩護說明、`lock_fire`）、`engine/context.py`、`engine/battle.py`
  （`fire_lock` 只在預覽模擬）、`engine/skills/targeting.py`（不列物件目標）、`engine/lock_on.py`（新檔，純查詢）、
  `engine/runner.py`（`LOG_FORMAT`）。
- 文字：`narrative/events.py`（落空與取消的句子、盾兵掩護）、`api/telegraph.py`、`api/schemas.py`。
- 內容：上表的 3 招、2 名敵人、2 個遭遇檔、`ai_profiles.yaml`（`screen`）、`rules/core.yaml`、`tuning_fields.yaml`、
  `skill_icon_art.yaml`（新招的圖示資料，借既有部件）。
- 測試：`tests/engine/test_lock_on_rg1.py`、`tests/engine/test_shield_guard_rg1.py`、`tests/content/test_rg1_content.py`。

### 1.7 驗收條件

1. 行為一致表格測試（實際跑引擎）：瞄準 → 下回合射出；四種應對各一列（斷視線、隱蔽、隊友擋、近戰打斷）＋目標倒下、
   出射程、自己陣營擋在中間不算、普通射擊不預告、遠程打中弓手不打斷。
2. 盾兵：正面擋、側面不擋、推開後不擋、近戰不吃、高處不吃、不和掩護物疊加、盾兵自己不被自己擋、近戰同伴不受保護。
3. AI：有瞄準招的敵人在合適場面會瞄準（固定種子）；盾兵會移到遠程同伴與敵人之間（固定種子）。
4. 性質測試（hypothesis）：瞄準的宣告與釋放可重播（同種子同步驟得到同事件）；沒有 `shield_guard` 的場面掩護結果與舊公式相同。
5. 一場重播通過；沒有這些敵人的既有戰鬥不變（地圖預設陣容都沒有雲鶴使、符籙師、噴岩龜：預測 CLI 快照只有規則包雜湊類的鍵會變）。
6. `ruff check`、`ruff format --check`、`mypy`、`lint-imports`、`trpg content check` 都過。

## 2. RG-2：陷阱痕跡與精英單挑（引擎＋世界）

### 2.1 敵方陷阱的痕跡（05 5.7，06 6.3.1）

- 玩家方（`Team.PLAYER` 與它的召喚物）單位**移動抵達或回合開始**時，曼哈頓 2 格內（`trap_trace_radius`，core，初值 2）
  還沒看見的敵方陷阱記成「可疑痕跡」：`TrapState.traced_by`（陣營清單，同 `revealed_to` 的寫法），發 `trap_traced`
  （只給該陣營看：格子，不帶技能與種類）。**一旦看到就留著**直到陷阱觸發、過期或被揭露（保守做法，見待決）。
- 檢查點和既有感知的 `detect_traps` 同一處；只對玩家方，敵方 AI 照舊看不見玩家的陷阱。
- 「揭露」照舊：看清種類、可以拆；揭露後不再是痕跡。
- 預覽與畫面：`view` 的 `trap_traces`（格子清單）；預覽不洩漏種類（`strip_hidden_traps` 不變）。我方 AI（隊友）**不**因痕跡繞路（保守）。
- **看那一格一眼**：敵方放陷阱時另發一個所有人可見的事件 `trap_glance`（放置者、格子）；畫面在 RG-3 演出。
  放陷阱的那一刻，那一格也直接成為玩家方的「可疑痕跡」嗎——**不**（保守：痕跡只看距離）；看一眼只是演出。
- 第一季沒有會放陷阱的敵人（18、19 已寫明），所以 RG-2 只用合成單位測；內容之後加敵人時再配。

### 2.2 精英單挑（09 9.6.6）

- 資料：遭遇表地點的固定精英 `elite: {unit, affix, duel: true}`、懸賞（`world/season.yaml`）與遭遇變化的精英同樣可帶
  `duel: true`。第一季 4 場：雲嶺 北坡狼王（`north_slope`）、斷崖幫寨「疤面」（`scarface` 懸賞與 `scarface_rises` 變化）；
  荒原 熔核領主（`molten_lord` 懸賞）、熔爐督工「鍛疤」（`overseer_camp` 固定精英與懸賞；開發從現有精英挑：硬殼的、
  不會補血）。
- 流程：遇敵結果 `EncounterResult.duel` ∈ `offered`／`accepted`／`declined`（沒有＝不提）；新世界動作
  `duel_choice {accept}` 只在 `offered` 時可送。**還沒選就開打＝拒絕**（照原本全隊打；前端 RG-3 之前也能照常打）。
- 接受：戰鬥只有主角對精英本人——隊友、傭兵、影子不上場，陣容的其他敵人不上場（三方的第三方也不上場）；
  戰鬥中召出的召喚物照常。獨狼照 `mark_lone_wolves` 自然成立（雙方都是）。
- 獎勵：**兩邊完全一樣**——經驗、掉落、精英必掉、懸賞完成都照「整個陣容」算，不因少了小怪而少（設計原話「補師QQ」）。
- 版號：`WORLD_RULES_VERSION` +1（新動作、組場改變）；`EncounterResult` 加欄位若在角色存檔裡就升 `CHAR_FORMAT`。

### 2.3 荒原狂戰士（19.2.1）

`ashen_berserker` 荒原狂戰士：用 #161 的怒氣（受傷累積、滿了打出強力一擊）。**等 KW 合併**後照它的怒氣關鍵字與資源機制做內容，
不在 RG-2 自己做資源機制；加進一般營地的遭遇表（新陣容）。KW 還沒合併時拆成 RG-2b。

### 2.4 驗收條件

痕跡：2 格內出現、3 格不出現、敵方看不到、敵方 AI 不繞開玩家陷阱、揭露後轉成看清、觸發後消失、事件過濾只給玩家方；
單挑：提出、接受後的陣容（只有兩人）、拒絕與沒選＝原陣容、兩邊獎勵逐欄相同、世界重播一致；版號測試同步。

## 3. RG-3：前端

- 戰場：被瞄準的人頭上「被瞄準」標記、弓手到目標的瞄準線（讀 `ChargeOut.lock_target_id`；目標移動後線跟著畫到新位置）；
  落空與打斷時的短字（落空、被擋下、被打斷）；盾兵擋住時命中預覽與目標身上的盾標記（讀 `cover_unit_id`／預覽說明）。
- 可疑痕跡的格子標記（讀 `trap_traces`）、敵人放陷阱時「看那一格一眼」（頭轉向那格＋小眼神符號，0.6 秒）。
- 單挑：遇敵面板多一個對話框「{精英}要求一對一」（接受／拒絕，兩個按鈕一樣大，文字寫明「獎勵一樣」）。
- 瀏覽器：電腦版 Chrome、Edge 為主；Firefox、Safari 可降級。

## 4. 版號（各段）

| 版號 | RG-1 | RG-2 | 原因 |
|---|---|---|---|
| `LOG_FORMAT` | `/119` → `/120` | 再 +1 | RG-1：`StatusInstance.lock_target`、`followup_charged.lock_target_id`、`followup_cancelled` 多 `interrupted`、`attack_rolled.cover_unit_id`、新的結算規則（瞄準招、盾兵掩護）。RG-2：`TrapState.traced_by`、新事件 |
| `WORLD_RULES_VERSION` | 不變 | +1 | RG-1 只改內容（遭遇表、單位、技能），世界規則程式不變；RG-2 加世界動作與組場 |
| `CHAR_FORMAT` | 不變 | 視 `EncounterResult` 位置 | |
| 地圖規則雜湊 | 不變 | 不變 | 兩段都不改實地地圖 |

## 5. 美術需求（給美術 PM）

風格一律照已定案的戰場 Q 版與「強招預告」（`client/src/battle/telegraph.ts` 的「蓄」標記，紫色 `0xb06bff`）同一套顯示語言（05 5.7）。
戰場的圖都是程式繪製（`client/src/render/`：標記與線在 `render/battle/` 的圖層，敵人外觀是紙娃娃部件，
`content/equipment/appearance.yaml`、`docs/art/敵人外觀.md`）；美術 PM 出樣張與規格（放 `docs/art/`，例如
`docs/art/RG樣張.md`），開發照樣張用程式畫。尺寸以戰場一格 48 px（`client/src/battle/geometry.ts` 的 `TILE_SIZE`）為基準。

| 項目 | 要畫什麼 | 放哪 | 大小 | 和既有圖的關係 |
|---|---|---|---|---|
| 被瞄準標記 | 目標頭上的準星（同心圓＋十字或箭頭朝下），閃爍 2 段；**一看就知道「下回合會被射」** | 單位頭頂，狀態圖示列上方 | 約 20×20（一格的 0.4） | 顏色沿用強招預告的紫，或另選警示紅並和「蓄」區分（美術 PM 定） |
| 瞄準線 | 弓手到目標的虛線（2px，帶流動動畫），終點在準星；被擋（隊友在線上）時線段在擋住的人那裡變色 | 戰場地面層之上、單位之下 | 程式畫線，美術給線型、顏色、粗細、虛線間距 | 同上配色；不可和移動路徑線、技能射程框混淆 |
| 落空、被擋、被打斷的短字 | 「落空」「被擋下」「被打斷」浮字樣式 | 沿用傷害浮字 | 同既有浮字 | 只是新字樣，沿用浮字元件 |
| 盾兵擋住的提示 | 被保護的遠程同伴身上的小盾圖示（只在玩家選目標、預覽有掩護時出現），盾兵與被保護者之間淡淡的連結 | 目標頭上狀態列旁 | 約 14×14（同狀態小圖示） | 和既有「半掩護」圖示同一族，但要看得出來源是單位不是物件 |
| 持盾弟子 | 觀內弟子（雲嶺修士袍、髮髻）**手持大盾**（比盜賊盾衛的鳶盾更大，接近塔盾、蓋到肩），盾面有門派紋樣 | 紙娃娃：`off_hand` 新形態或新部件 | 照既有紙娃娃尺寸 | 修士配色參考持劍弟子（`#5f8f8a`）；盾是新部件（現有只有鳶盾、塔盾） |
| 熔殼甲兵 | 熔岩獸（甲蟲體型）**背著熔殼大盾**（半圓殼片立在身前），殼縫透紅光 | 紙娃娃：`creature` 新變體或 trait | 照熔岩甲蟲 | 參考熔岩甲蟲（`crawler/beetle/magma`）；和噴岩龜（`shell/volcano`）並排時要分得出來 |
| 可疑痕跡（RG-2） | 地面上的「不明痕跡」：翻動的土、細線、問號小圖示——**不能**畫出陷阱種類 | 格子地面層（同陷阱圖示層） | 一格 48×48 內 | 和已揭露陷阱的圖示明顯不同（揭露後換成既有陷阱圖示） |
| 看那一格一眼（RG-2） | 放陷阱的敵人頭轉向那一格＋一個小「眼神」符號（例：「👀」風格的雙點，不用 emoji 字型） | 單位頭上，0.6 秒 | 約 14×14 | 和「發現」「驚訝」等既有表情符號同一族 |
| 精英單挑（RG-3） | 對話框插圖：精英剪影與主角剪影相對、中間交叉的武器；接受、拒絕兩顆按鈕 | 遇敵面板的對話框（`DialogFrame`） | 插圖 320×120 | 對話框框體沿用既有 `DialogFrame`；精英剪影可用紙娃娃剪影自動產生，美術只需定構圖 |

美術交件前戰場可以先用暫代：準星用文字「◎」、線用程式畫的紫色虛線、盾兵用盜賊盾衛的鳶盾與熔岩甲蟲外觀（RG-1 的內容就是這樣暫代）。

## 6. 待 PM 決定（設計沒寫到、照最保守先做）

1. **隊友擋在中間＝整發落空**（`lock_on_blocked`）。另一種讀法是「改打擋住的那個人」（坦克擋箭）。照保守：落空。
2. **隱蔽不論距離都讓瞄準落空**（一般規則是隱蔽目標 2 格內仍可攻擊）。設計原話「進入隱蔽」讓這一擊落空，照字面。
3. **目標走出射程也落空**（`lock_on_lost`；設計只列四種應對，照一般施放的合法性）。
4. **打斷只算近戰命中**（遠程、法術打中弓手不打斷；設計原話「近戰攻擊命中」）。推開、撞開不打斷。
5. **瞄準時付全部代價**、射出時不再付；落空不退。
6. **符籙師的「強力一擊」選定身符**：符籙師兩招都是控制（定身符、封符），沒有傷害招；選單體的定身符改成瞄準。也可以改成新的傷害招。
7. **噴岩龜的熔岩彈取代火牆**：19 的「拋射熔岩彈（造火地）」原本用火牆近似，這次改成單體瞄準；火牆從噴岩龜身上拿掉。
   「造火地」做不到：打擊骨架（`strike`）的附帶原語不能造表面、範圍骨架（`area`）不能單體，先用燃燒 2 回合代替。
   要真的造火地，得放寬骨架（技能規則，不是數值），請玩法 PM 決定。
8. **盾兵只保護遠程同伴**（武器不受高度限制）；近戰同伴不受保護。噴岩龜（法杖）算遠程。
9. **盾兵掩護的數值另開 `shield_guard_hit_penalty`**（初值 2，同半掩護），不和半掩護共用，讓使用者分開調。
10. **既有的盜賊盾衛（`shield` 標籤）不變成盾兵**：只有新加的兩種帶 `shield_guard`。
11. **新陣容加在現有地點、原陣容不動**：加了陣容，那些地點抽到原陣容的機率會變低。
12. **陷阱痕跡看到就留著**（RG-2）：不會因為走遠又消失。
13. **單挑還沒選就開打＝拒絕**（RG-2）：讓前端做好之前照常能打。
14. 熔殼甲兵當作熔岩獸（甲蟲體型）而不是人形：19 只寫「背著熔殼大盾」。

## 7. 平衡疑慮（不量，交使用者在工坊看；同 `docs/design/平衡待查.md` 第 21 條）

- 瞄準招的傷害照原招，但多了預告與四種應對，遠程敵人可能變弱；反過來瞄準在 AP 上是「這回合付、下回合打」，弓手下回合還能普通射擊，輸出節奏變成每 2 回合多一發。
- 盾兵護甲 6、帶盾擊，近戰 build 繞不過去時可能拖長；遠程上限沒有算盾兵。
- 噴岩龜少了火牆（移動的火地區域），火地壓制變少。

## 8. 不做

- 不改 `docs/design/`、不改 `skill_keywords`、資源機制、既有技能內容、skillgen（KW 在做）。
- 不做模擬報表與數值調整。
- 前端畫法全部在 RG-3。
