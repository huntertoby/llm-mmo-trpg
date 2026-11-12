# Phase PB-1 計畫｜部位系統段 1：共用部位系統＋霧鎖真人

> 開發 PM 的規格助手起草（2026-11-12，依據 main `4e204cf9`；行號以它為準）。**範圍與定稿以第 0 節為準**；第 0.2 節的規則類待決要先問使用者，答覆前對應的段不派工。
> 設計依據（以設計文件為準，本檔不放寬、不重新解釋）：`docs/design/05-戰鬥.md` 5.12（尤其 5.12.1～5.12.3、5.12.8）、`docs/design/18-雲嶺內容.md` 18.2.3（霧鎖真人「部位」表）、`docs/玩法決定紀錄.md` #152、`docs/phases/頭目部位與巨型頭目-工作量估算.md` 附錄 A。
> 實作者先讀：PB-1a／1b 讀 `docs/dev/上手-引擎戰鬥結算.md`（全文）；PB-1c 讀 `docs/dev/上手-前端戰鬥畫面與動畫.md` 第一～三節與 `docs/開發PM交接.md` 6.5.1、6.5.2；PB-1n 讀 `docs/phases/PhaseNW計畫.md` 第 3、5 節與 `docs/dev/上手-內容資料與模擬.md` 第七節；PB-1d 讀 `docs/dev/上手-內容資料與模擬.md` 第二節。

## 0. 決定與待決

### 0.1 已定、不要再問（都附出處）

| # | 規則 | 出處 |
|---|---|---|
| D1 | 段 1＝共用部位系統＋霧鎖真人；不動巨型頭目（3×3）、灰燼之心、碎晶之主、龍、大型精英都**不在本段** | 05 5.12.8；#152 決定 1 |
| D2 | 部位是頭目身上的子目標：不是單位、不能被位移、不擋路；每隻頭目 2～4 個部位 | 05 5.12.2 第 1 點 |
| D3 | 打中部位：傷害照常算進頭目 HP，同時從部位小血條扣**同樣的數字** | 05 5.12.2 第 2 點；#152 決定 3 |
| D4 | 部位血量＝頭目最大 HP 的千分比；預設每個 200‰，同一隻加總 ≤ 600‰（數值工坊可調） | 05 5.12.2 第 3 點；#152「數值」 |
| D5 | 部位可帶自己的護甲或元素抗性修正，沒寫＝和本體相同 | 05 5.12.2 第 4 點 |
| D6 | 每個部位只破一次，破了持續到戰鬥結束；回血、換階段都不長回來；破掉時寫一條戰鬥紀錄並交給說書人，說書人只描述、不決定 | 05 5.12.2 第 5 點 |
| D7 | 階段門檻照舊只看頭目 HP；部位可標「哪些階段才露出」，沒露出打不到，已破的換階段後仍算破 | 05 5.12.2 第 6 點 |
| D8 | 破壞效果只用引擎已有的東西、每個部位最多 2 種：封一招（正在蓄力就一起打斷）、一項能力下降（移動、護甲、命中或某元素抗性）、一次控制（照頭目原本免疫）、停掉一個機制（回合開始自我治療、產卵、飛行） | 05 5.12.2 第 7 點 |
| D9 | 打得到的條件每個部位標一種：任何方向／從背後（沿用 5.1 背刺判定）／從高處（比頭目高 ≥ 1 層）或 3 格外／趁倒地、暈眩或冰凍／某階段才露出；巨型頭目的「那一格打得到」屬段 2 | 05 5.12.2 第 8 點 |
| D10 | 只有單體招能選部位；範圍技、連鎖、彈跳只打本體；持續傷害（燃燒、中毒、流血）、反應與表面的傷害只扣本體；命中、暴擊、背刺加成照現行 | 05 5.12.2 第 9 點；#152 決定 3 |
| D11 | 選哪個部位記在動作裡，人形頭目用 `target_part`；部位血量存在戰鬥狀態；AI 選部位只用確定性評分，同分照部位 ID 排序 | 05 5.12.2 第 10 點 |
| D12 | AI：隊友與影子照「破掉的效果價值」挑部位，能封頭目下一招或能打斷蓄力時優先打部位，否則打本體；部位價值寫進 AI 價值表（數值工坊可調）。頭目第一版不做護部位，只加：部位快破時人形頭目多給「把背轉離攻擊者」一點分數 | 05 5.12.2 第 11 點 |
| D13 | 介面：頭目血條下列部位小血條、破掉打叉；預覽多一行（例「拂塵還剩 12」）；打不到的灰掉並寫原因；每個部位寫「破掉會：……」；破掉有一次明顯演出 | 05 5.12.2 第 12 點 |
| D14 | 人形頭目 1 格、規則照一般單位；選了單體招點頭目時跳出小選單「本體／拂塵／氣海……」，直接點本體或按確認＝打本體 | 05 5.12.3 |
| D15 | 只用在頭目與指定的大型精英，一般小怪不做；本段只有霧鎖真人 | 05 5.12.2 第 13 點；5.12.8 |
| D16 | 霧鎖真人三個部位：拂塵（任何方向；破＝封住「霧中換位」）、氣海（從背後；鎖霧、歸一才露出；破＝停止歸一回合開始的自我治療）、長劍（歸一才露出；破＝近戰傷害降低，並打斷正在蓄力的強招） | 18 18.2.3「部位」表 |
| D17 | 數值只定規則與預設比例；PM 與 agent 不試數值，只出報表，數值由使用者在數值工坊調 | #152「數值」；`docs/phases/PhaseBAL-21計畫.md` 0.0 |
| D18 | 舊存檔、舊戰鬥紀錄不必相容（照實寫影響，不寫遷移、不刪檔） | `PhaseBAL-21計畫.md` 第 1 節（使用者 2026-11-12「存檔都可以刪除」） |
| D19 | 外框（OCL）照做，與本段無關；本段不改剪影外框 | 05 5.12.7 |

### 0.2 規則類待決（必須問使用者；附建議與理由）

| # | 問題（出處） | 建議 | 理由 |
|---|---|---|---|
| R1 | **普攻算不算「單體招」、能不能選部位**（5.12.2 第 9 點只寫「單體招」；5.12.3「選了單體招、點頭目時」） | **算**。普攻點頭目也跳選單 | 普攻本來就是單體；不算的話沒有單體技能的近戰（坦克、雙持）打不到部位，和 5.12.6「坦克先讓頭目轉身」「刺客繞背打氣海」的節奏不合 |
| R2 | **「同樣的數字」是哪個數字**（5.12.2 第 2 點）：頭目**實際扣掉的 HP**（護盾吸收、劍陣 −50%、格擋、傷害轉移之後），還是扣護盾前的傷害 | **實際扣掉的 HP**（`hp_before − hp_after`） | 「算進頭目 HP，同時扣同樣的數字」最直接的讀法；護盾或劍陣擋掉的傷害也不傷部位，劍陣階段打部位自然比較慢，不必另寫規則 |
| R3 | **部位自己的護甲／抗性怎麼和「傷害照常算進 HP」一起算**（5.12.2 第 2、4 點） | 打部位時命中用**部位的護甲**、傷害用**部位的元素修正**算一次，得到的數字同時扣本體與部位 | 只算一次才不會有「本體一個數、部位另一個數」；部位護甲高＝難打中，正是第 4 點的用意。霧鎖真人三個部位都沒寫修正，本段實戰不受影響 |
| R4 | **長劍「近戰傷害降低」不在 5.12.2 第 7 點的能力下降清單內**（清單只有移動、護甲、命中、元素抗性），而且「打斷正在蓄力的強招」沒有搭配封招（清單是「封住一招，正在蓄力的話一起打斷」）；**降低多少設計沒給**（18 18.2.3） | 照 18.2.3 原文做兩個效果：①能力下降加一項「造成的傷害」（千分比；歸一階段真人的招與普攻全是近戰，等同近戰傷害降低）；②單獨的「打斷蓄力」（不封招）。降低量先放占位 **750‰（−25%）**，標「占位、待使用者在數值工坊調」 | 18.2.3 是頭目的定稿，05 的清單是通則；照頭目原文最不需要另造規則。占位值只為讓效果可測，模擬報表照實列（D17 不試數值） |
| R5 | **選部位的判定時點**：可打條件在宣告動作時判一次，還是每一下判一次（例：連擊武器第一下從背後打中，頭目轉身，第二下還算不算打氣海） | **宣告時判一次**；同一個動作的每一下都打同一個部位，部位破了之後剩下的打本體 | 5.12.2 第 10 點「選哪個部位記在動作裡」；每一下重判會讓「從背後」的部位對多段攻擊幾乎打不到第二下，也要額外的中途失效規則 |
| R6 | **點頭目的操作**（5.12.3「直接點本體或按確認就是打本體，現有操作不變」）：點頭目先跳選單（比改前多一步），還是第一下直接打本體、另外用別的方式選部位 | 點**有部位的**頭目先跳選單，**本體是第一項且預設選中**；在選單點本體、按 Enter、或再點同一個頭目＝打本體。**沒有部位的單位操作完全不變** | 這樣「選部位」只在需要時出現；「再點一次＝本體」讓習慣點兩下的人不會誤打部位；「現有操作不變」讀成「對其他單位不變」 |
| R7 | **「3 格外」含不含 3**（5.12.2 第 8 點）；本段霧鎖真人用不到，但共用系統要實作（段 3 碎晶之主的核心會用） | 照濃霧先例：**曼哈頓距離 > 3**（4 格起） | 18.2.3「遠程 4 格外命中劣勢」實作是 `> 4`（`src/trpg/engine/rules/combat.py:387`，`content/weather.yaml:17` 說明「超過 4 格」）；同一套說法同一套算法 |
| R8 | **隊友打不破時要不要也「磨」部位**（5.12.2 第 11 點「能封下一招或能打斷蓄力時優先打部位；否則打本體」）：打部位的傷害一樣算進 HP，所以磨部位通常沒有代價 | 部位分＝破壞效果價值 ×「這一下預計傷害 ÷ 部位剩餘血量」（上限 1）；**這一下能破、而且破了能封頭目下一招或打斷蓄力**時再加優先分；部位分 0 或打不到時打本體；同分本體優先，再照部位 ID | 照字面「否則打本體」會讓隊友永遠不先磨部位，部位只有剛好一刀能破時才會破，模擬會看不到部位破壞；用比例分保留「優先」語意，數值放 AI 價值表給使用者調 |
| R9 | **召喚物能不能打部位**（5.12.2 第 11 點只寫「隊友與影子」） | **不能**，召喚物（含玩家下令集火）一律打本體；之後要再開 | 設計沒寫到的照最保守；召喚物的指令介面也沒有選部位的地方 |

### 0.3 技術類待決（開發 PM 可定；沒回覆就照建議）

| # | 技術點 | 建議 |
|---|---|---|
| T1 | 內容欄位 | `UnitTemplate.parts: tuple[BossPart, ...] = ()`（`exclude_if` 空不輸出）。`BossPart`：`id`、`name_zh`、`hp_permille`（預設 200）、`reach`（`any`／`behind`／`high_or_far`／`disabled`）、`exposed_in: tuple[str, ...] = ()`（階段 ID；空＝全程露出）、`armor_bonus: int | None`、`resist`、`element_mods`（沒寫＝同本體）、`on_break: tuple[PartBreakEffect, ...]`（1～2 項）、`break_text_zh`（選填，給紀錄與說書人）。「某階段才露出」放 `exposed_in`、和 `reach` 並存（氣海＝`reach: behind`＋`exposed_in: [mist_lock, return_to_one]`），因為 18.2.3 的氣海同時有兩個條件 |
| T2 | 破壞效果的型別 | `seal_skill {skill}`（封招；施放者正在蓄力**這一招**就打斷）、`stat_down {stat, amount}`（`stat`：`move`（格）、`armor`（點）、`hit`（點）、`resist.<組>`（‰）、`damage_dealt`（‰，R4））、`control {status, duration}`（走一般施加狀態，吃免疫與控制遞減）、`stop_mechanic {status}`（移除該狀態並阻擋之後再加上，含換階段的 `add_statuses`）、`interrupt_charge`（R4）。**數字寫在單位檔的部位裡**（不建新的狀態定義），數值工坊才改得到（PB-1n）；`stop_mechanic` 本段只做「狀態」類，產卵、飛行等段 2 以後有內容時再加 |
| T3 | 戰鬥狀態 | `UnitState` 加 `parts: tuple[BossPart, ...] = ()`（開場從範本複製，同 `phases`）、`part_hp: dict[str, int]`、`broken_parts: tuple[str, ...]`、`sealed_skills: tuple[str, ...]`、`part_mods: dict[str, int]`（`stat_down` 累計）、`suppressed_statuses: tuple[str, ...]`；全部有預設值，同步 `clone()`（手寫逐欄）與序列化。沒有部位的單位這些欄位都是預設值 |
| T4 | 序列化「逐字不變」 | 動作的 `target_part` 用 `exclude_if=None`（沒選不輸出）；狀態新欄位若 pydantic adapter 能做到「預設值不輸出」就做，做不到就在比對腳本剝掉「值等於預設」的新鍵並在報告寫明。**不改 `DamageDealt`**，部位傷害另發新事件（T5） |
| T5 | 新事件 | `PartDamaged(target_id, part_id, amount, hp_before, hp_after)`（緊接在該次 `DamageDealt` 之後）、`PartBroken(target_id, part_id, name_zh, effects)`；破壞效果各自發既有事件（`FollowupCancelled` 加 `reason: part_broken`、`StatusApplied`／`StatusRemoved` 等）＋新事件 `SkillSealed`（`unit_id`、`skill_id`）與 `PartStatDown`（如 `stat_down` 需要紀錄）。全部加進 `events/union.py`，對所有陣營可見（頭目資訊被隱藏時照 `event_filter.py` 現行規則） |
| T6 | 合法動作清單 | **`legal_actions` 不列舉部位變體**（否則效用 AI 的候選截斷會變、實戰結果跟著變）。新增純查詢 `part_targets(state, action) -> tuple[PartTarget, ...]`（`part_id`、`ok`、`reason`：`not_exposed`／`need_behind`／`need_high_or_far`／`need_disabled`／`broken`／`area_skill`…），`resolve` 驗 `target_part` 時呼叫同一個函式。API 與 AI 都用它 |
| T7 | 哪些動作能帶 `target_part` | `Attack`（R1 通過時）與 `UseSkill`（形狀 `single`、而且有對該目標的傷害效果）。種族技、充能詞條、複合技第二段（`followup_target`）、延遲段釋放、反應、召喚物（R9）一律本體；帶了就 `IllegalActionError`（附原因） |
| T8 | 破壞的那一下頭目也倒下 | 照發 `PartBroken`（紀錄與說書人有一句），**不施破壞效果** |
| T9 | 傷害分流的插入點 | `effects/handlers.py::_damage`（`:136`）在扣 HP 之後、`DamageDealt` 之後：`DamageEffect` 多一個選填 `part_id`（只有動作的主要目標、主要選取的傷害效果帶上；連鎖、濺射、反應、持續傷害、表面都不帶）。部位的護甲與元素修正（R3）在 `rules/combat.py::defense_value_permille`（`:168`）與 `element_modifier_ppm`（`:575`）多收一個選填覆寫值；沒有 `part_id` 時走原本的程式路徑 |
| T10 | 「霧中換位」對到哪一招 | `skill_mist_shift`（霧遁）。依據：`content/skills/skill_mist_shift.yaml` 檔頭「18.2.3 霧鎖真人第 2 階段『每回合隱蔽換位』」；真人只有這一招換位 |
| T11 | 「打斷正在蓄力的強招」與延遲段 | 見 4.7：走既有的 `CancelChargeEffect`，不分是否 `anchor`、`release: next_turn` 或 `attacked`、法術或武器技、定向蓄力 |
| T12 | `LOG_FORMAT` | `trpg-battle-log/114` → `/115`；若合併時已有別段先升，改成下一號並在 `docs/phases/戰鬥紀錄格式變更.md` 寫清楚 |
| T13 | AI 價值表的位置與預設 | `content/ai_profiles.yaml` 新增 `parts:` 一節（schema 在 `src/trpg/content/environment.py`）：`seal_skill`、`interrupt_charge`、`stat_down`、`control`、`stop_mechanic` 各一個價值（占位：8、10、4、6、8，量級對照 `status_values` 的 stun 12、root 6）、`priority_bonus`（R8 的優先分，占位 6）、頭目 `guard_back_bonus`（占位 3＝現有 `facing.back_exposed`）、`near_break_permille`（「快破」門檻，占位 500＝剩一半）。全部占位、報告標明；使用者在 NW-3（AI 估值表）開放後自己調 |
| T14 | 前端二擇一：美術移植需求到之前**用占位、接口先做**，或**等移植需求** | **占位、接口先做**（PB-1c），美術樣張到了另開小段 PB-1e 換畫法。理由：選單、預覽、紀錄、可打條件的灰階與原因都是介面邏輯，和美術無關，先做才能讓 PB-1d 模擬之外也有人實際點得到；占位集中在一個檔（`render/partMarks.ts` 與 CSS 的 `.part-*`），換美術只動那裡；等移植需求會讓整個部位系統在畫面上不可用、也驗不到 6.5.1 |
| T15 | 部位小血條放哪 | PB-1c 放**角色卡（`ui/UnitInfo.tsx`）**＋**選部位選單**；頭頂血條下的小格屬美術（會擠 800 寬，附錄 A 已點出），並且要動 `render/battle/unitLayer.ts`（OCL-1 正在改），排到 PB-1e、在 OCL-1b 合併之後 |
| T16 | 破壞演出（占位） | 沿用現有特效：該頭目一次重擊白閃＋微震（`battle/specials.ts`／`impact.ts` 的既有參數）＋浮動字「拂塵 破！」（`feedbackLayer`）；不新增貼圖 |
| T17 | 模擬規模 | 每組 8 build × 13 種子＝104 場（≥ 100 場才判），部位「關」「開」同種子配對；程序池 ≤ 6；只在 PB-1d 最後各跑一次完整版，前面只冒煙 |

## 1. 現況查證（只讀，`4e204cf9`）

- **動作**：`Attack`（`src/trpg/engine/actions.py:78`，`target_id`／`target_object_id`／`direction` 恰好一個）、`UseSkill`（`:216`，依形狀 `targeting` 給欄位）、`UseRaceSkill`（`:260`）。都沒有部位欄位。
- **傷害**：`effects/handlers.py::_damage`（`:136`）：擲骰 → 倍率 → `_absorb`（護盾，`:164`）→ `_transfers`（轉移、分擔）→ `unit.hp` 扣減（`:167`）→ 免死／測試模式 → `DamageDealt`。劍陣 −50% 走 `_formation_and_ward`（`:149`）。
- **防禦與元素**：`rules/combat.py::defense_value_permille`（`:168`，敏捷＋`armor_bonus`）、`element_modifier_ppm`（`:575`，`resist`＋`element_mods`）。
- **背刺**：`rules/facing.py::is_behind`（`:60`，只算相鄰背後格）；`combat.py::positional_bonus`（`:458`）只在近戰（`profile.melee`）時算背刺。5.1：被近戰攻擊後立刻轉向攻擊者（`docs/design/05-戰鬥.md:74`）。
- **距離先例**：濃霧 `manhattan(...) > ranged_disadvantage_beyond`（`combat.py:387`）。
- **頭目階段**：範本 `UnitTemplate.phases`（`src/trpg/content/battle.py:1708`），`BossPhase`（`:1544`）；狀態 `UnitState.phases`／`phase_index`（`src/trpg/engine/state.py:519-522`）。進入階段 `boss_phases._enter`（`:80`）換技能組時**直接覆寫 `unit.skills` 與冷卻**、依序加 `add_statuses`——封招與停機制必須存在另外的欄位才撐得過換階段。
- **單位不在規則包內**：`Ruleset`（`src/trpg/content/library/ruleset.py:96`）沒有單位範本，所以 `hash_ruleset` 不受霧鎖真人 YAML 影響；一輪存檔的 `ruleset_hash` 與世界日誌 `content_digest` 會（內容檔變了）。
- **蓄力取消**：`delayed.py::_drop`（`:190`，原因 `downed／controlled／silenced／expired／replaced／form_left`）、`CancelChargeEffect` 與 `_cancel_charge`（`:295`）、暈眩沉默的觸發 `_cancel_on_control`（`:315`）；`release: attacked` 在那次攻擊結算完才釋放（`resolve_attacked_release`）。`_drop` 不看 `StatusInstance.anchor`，BAL-21a 的落在選定格一樣能取消。
- **技能可用性**：`skills/targeting.py::skill_problem`（`:432`）是封招要接的位置。
- **霧鎖真人**：`content/units/sect_mist_lock_master.yaml`（HP 120；階段 `sword_array`→`mist_lock`（≤ 600‰）→`return_to_one`（≤ 300‰）；`skill_mist_shift` 在開場與鎖霧的技能組；歸一加 `mist_return`；歸一的強招 `skill_charged_cleave` 是延遲段）。`mist_return`（`content/statuses.yaml:226`）＝回合開始回 1d6、不能淨化驅散。預設比例下三個部位各 24 HP（120 × 200‰），加總 600‰。
- **AI**：`ai/utility/policy.py`（候選與截斷 `skill_candidates`）、`scoring.py::score_action`（`:97`）；朝向權重 `content/ai_profiles.yaml:195` `facing: {backstab: 4, back_exposed: 3}`。
- **數值工坊**：白名單 `content/tuning_fields.yaml`（只有 `kind: unit`，`src/trpg/content/tuning_fields.py:85`；`phases[*]` 的展開與中文標籤在 `src/trpg/api/tuning/objects.py:81-116`）。AI 估值表要到 NW-3 才開放（`PhaseNW計畫.md:74`）。
- **前端點擊**：`client/src/battle/tileClick.ts::decideTileClick`（`:97`）：沒有選取模式時點敵人＝普攻（`act`），有模式時 `modeClick`（`:80-93`）直接 `submit`。共用點擊選單 `ui/usePopupMenu.ts`（Esc 先關選單、不取消瞄準；同時只開一張）、外框 `ui/PopupFrame.tsx`；說明卡 `ui/Hint.tsx`；掃描測試 `ui/floatCardRule.test.ts`。戰鬥紀錄文字由伺服器 `src/trpg/narrative/events.py` 產生。
- **CLI 快照**：`tests/cli/test_output_snapshots.py` 的戰鬥鍵沒有頭目圖（`:26-44`），本段**預期 0 個鍵變動**。

## 2. 範圍

**做**：共用部位系統（資料、狀態、動作、合法性、五種條件、傷害分流、破壞事件與五種效果、和延遲段的打斷、紀錄格式）；霧鎖真人三個部位；content check；數值工坊白名單加部位欄位；隊友與頭目 AI；前端選單、角色卡部位血條、預覽、紀錄、占位演出；兩項模擬報表。

**範圍外**：多格單位、`footprint`、綁格部位（段 2）；碎晶之主、灰燼之心的部位（段 2、3）；定點飛行；大型精英部位；`stop_mechanic` 的產卵與飛行；頭頂血條下的部位小格與美術樣張（PB-1e）；任何數值調整；AI 估值表進數值工坊（NW-3）。

## 3. 分段與平行

| 段 | 內容 | 前置 | 會動的主要檔 | 平行 |
|---|---|---|---|---|
| **PB-1a** 引擎＋內容 | 第 4 節 | R1～R7 答覆；T1～T12 | `src/trpg/engine/`（`actions.py`、`state.py`、`battle.py`、`effects/`、`events/`、`rules/combat.py`、`delayed.py`、`boss_phases.py`、`skills/targeting.py`、`preview.py`、`runner.py`、新檔 `parts.py`）、`src/trpg/content/battle.py`（或新檔 `parts.py`）、`content/units/sect_mist_lock_master.yaml`、`src/trpg/narrative/events.py`、`docs/phases/戰鬥紀錄格式變更.md` | 不和任何會升 `LOG_FORMAT` 或改 `effects/handlers.py`、`state.py` 的段平行 |
| **PB-1b** AI | 第 5 節 | 1a 合併；R8、R9；T13 | `src/trpg/engine/ai/`、`content/ai_profiles.yaml`、`src/trpg/content/environment.py` | 可和 1c、1n 平行（檔案不重疊）；和 BAL-21c 都會動 AI 與固定種子測試時錯開合併 |
| **PB-1n** 數值工坊白名單 | 第 6 節 | 1a 合併；NW-1b 已合併 | `content/tuning_fields.yaml`、`src/trpg/content/tuning_fields.py`、`src/trpg/api/tuning/objects.py`（必要時 `client/src/tuning/`） | 可和 1b、1c 平行；**不可和 NW-2 同時**（同一批白名單檔） |
| **PB-1c** 前端（占位、接口先做） | 第 7 節 | 1a 合併；R1、R6；T14～T16 | `src/trpg/api/`（視圖、合法動作、OpenAPI）、`client/src/`（`battle/tileClick.ts`、新 `ui/PartMenu.tsx`、`ui/UnitInfo.tsx`、預覽、事件窄化、`battle/specials.ts`） | 可和 1b、1n 平行；**不動 `render/battle/unitLayer.ts`、`BattleRenderer.ts`**（OCL-1 在改） |
| **PB-1d** 模擬報表 | 第 8 節 | 1b 合併 | 新腳本 `scripts/pb1_parts_report.py`（不改內容） | 可和 1c、1n 平行；PM 跑全量期間不跑 |
| PB-1e（之後） | 美術移植：頭頂部位小格、破壞演出、部位標示 | 美術 PM 移植需求；OCL-1b 合併 | `render/` | 和 OCL 不可平行 |

同時進行的 agent 最多 3 個（開發名額）。建議順序：1a → (1b ∥ 1c ∥ 1n) → 1d →（美術到了）1e。

## 4. PB-1a｜引擎＋內容

### 4.1 內容 schema（T1、T2）

1. `BossPart`、`PartBreakEffect`（判別聯集，`type` 為鍵）放 `src/trpg/content/battle.py` 或新檔 `src/trpg/content/parts.py`（`battle.py` 已很長，建議新檔，從 `battle.py` re-export）。
2. `UnitTemplate.parts`（`exclude_if` 空不輸出）；`BossPart` 的選填欄位都 `exclude_if=None`。
3. 結構檢查（model validator＋`trpg content check` 的跨檔檢查）：
   - 只有帶 `boss` 標籤的單位能有 `parts`（「指定的大型精英」等段 2 以後再開，D15）；召喚物不行。
   - 2～4 個；`id` 不重複；`hp_permille` 1～1000；加總 ≤ 600‰（D4，數值工坊改到超過時寫回會被同一個檢查擋）。
   - `on_break` 1～2 項（D8）；`seal_skill.skill` 必須出現在該單位的 `skills` 或任一 `phases[*].skills`；`stop_mechanic.status`、`control.status` 是存在的狀態；`control` 的狀態要有 `control_group` 或 `skip_turn`；`exposed_in` 的每個 ID 是該單位的階段 ID；`stat_down.stat` 在允許清單。
   - 錯誤訊息用中文、指出單位與部位 ID。

### 4.2 戰鬥狀態（T3）

- 開場（`begin_battle`／建單位處，和 `phases` 同一處）把範本 `parts` 複製到 `UnitState.parts`，`part_hp[id] = max_hp × hp_permille ÷ 1000`（無條件捨去、最低 1）。用**開場當下**的 `max_hp`（等級成長、遭遇調整之後），之後 `max_hp` 改變不重算（寫進報告）。
- 「上手-引擎戰鬥結算」第三節第 4 點：dataclass 欄位、手寫 `clone()`、序列化三處同步；`tests/engine/test_state_clone.py` 要過。

### 4.3 動作與合法性（R1、R5、R7、T6、T7）

- `Attack.target_part`、`UseSkill.target_part`：`str | None = None`，`exclude_if=None`。只在 `target_id` 有給時可填。
- 新檔 `src/trpg/engine/parts.py`：`part_targets(state, action)`（純查詢，排序：部位 ID）與 `check_target_part(state, action) -> str | None`。`resolve` 在 `_do_attack`／`_do_use_skill` 的既有合法性檢查之後呼叫，不合法拋 `IllegalActionError`（訊息帶原因代碼的中文）。
- 條件（R5：宣告時判一次，以**宣告時**的位置、朝向、狀態、階段為準）：
  - `any`：一定可以。
  - `behind`：攻擊者站在 `back_xy(target)`（`rules/facing.py`）**而且這次攻擊是近戰**（同 `positional_bonus` 的 `profile.melee`；5.1「近戰攻擊者站在目標背後」）。
  - `high_or_far`：攻擊者所在格比頭目高 ≥ 1 層，或曼哈頓距離 > 3（R7 待答；答案不同只改一個常數）。
  - `disabled`：頭目身上有 `prone`、`stun` 或 `frozen`（`content/statuses.yaml:89`、`:266`、`:278`；判斷用狀態定義的 `skip_turn` 或 ID 清單，實作者擇一並寫報告）。
  - `exposed_in`：非空時，頭目目前階段的 ID 要在清單內。
  - 已破的部位不能選（`broken`）。
- `legal_actions` **不改**（T6）。
- 預覽：`preview(state, action)` 接受帶 `target_part` 的動作，最少／最多兩次模擬都要有部位傷害；不能有副作用（上手第三節第 7 點）。

### 4.4 傷害分流（D3、D10、R2、R3、T9）

1. 動作帶 `target_part` 時，**只有**「該動作主要選取、目標是那個頭目」的 `DamageEffect` 帶 `part_id`；同一招的多個傷害效果（例 `skill_first_strike` 兩段）都帶；連擊武器的每一下都帶（R5）。
2. 範圍技、連鎖、彈跳、濺射（`extra_targets`）、持續傷害（狀態的回合開始傷害）、反應（借機攻擊、反擊）、表面、地形、墜落一律不帶（D10）。
3. 帶 `part_id` 時：命中判定的防禦值用部位的 `armor_bonus`（有寫才換），傷害的元素修正用部位的 `resist`／`element_mods`（有寫才換）（R3）。
4. `_damage` 扣完 HP、發 `DamageDealt` 之後：`dealt = hp_before − hp_after`（R2）；部位沒破就 `part_hp −= dealt`（最低 0），發 `PartDamaged`；降到 0 發 `PartBroken` 並結算破壞效果（4.5）。部位已破（例如同一動作前一下打破）就不帶、照本體結算。
5. **沒有 `part_id` 的傷害走原本的程式路徑**，不多取亂數、不多發事件、事件順序不變。

### 4.5 破壞事件與效果（D6、D8、T2、T5、T8）

依 `on_break` 的順序結算，每項發自己的事件：
- `seal_skill`：加進 `sealed_skills`（換階段不清）；`skill_problem`（`skills/targeting.py:432`）對封住的招回「已被破壞部位封住」；頭目正在蓄力**這一招**就打斷（4.7）。發 `SkillSealed`。
- `interrupt_charge`：頭目身上有任何 `charging` 就打斷（4.7）；沒有就什麼都不發。
- `stat_down`：累加到 `part_mods`，在既有計算點讀（`move`→移動力、`armor`→`defense_value_permille`、`hit`→命中加值、`resist.<組>`→`element_modifier_ppm`、`damage_dealt`→造成的傷害倍率，和狀態的 `damage_dealt_permille` 同一處相乘）。沒有部位的單位 `part_mods` 為空，計算結果逐字不變。
- `control`：走一般「施加狀態」流程（免疫、控制遞減、抵抗照現行，D8「照頭目原本的免疫判定」）；施加失敗照現行發的事件。
- `stop_mechanic {status}`：頭目身上有該狀態就移除（`StatusRemoved`）；加進 `suppressed_statuses`，之後任何來源（含 `boss_phases._enter` 的 `add_statuses`）要加這個狀態時跳過、不發事件（報告寫「跳過不發事件」）。
- 破壞的那一下頭目倒下：只發 `PartBroken`，不結算效果（T8）。
- 敘事：`src/trpg/narrative/events.py` 給 `PartDamaged`（例「拂塵受損（24 → 12）」）、`PartBroken`（例「霧鎖真人的拂塵被打碎了！破掉：封住霧遁」；有 `break_text_zh` 時用它）、`SkillSealed` 中文；說書人的輸入要含 `PartBroken`（實作者查 `src/trpg/narrative/storyteller.py` 的事件挑選，用 `MockLLMClient` 測「輸入裡有這一行」），說書人沒有任何改部位狀態的工具（守則 3）。

### 4.6 換階段與回血（D6、D7）

- `boss_phases._enter`：換技能組時**不動** `sealed_skills`；`add_statuses` 先過 `suppressed_statuses`；部位血量與 `broken_parts` 不動。
- 任何治療只回本體 HP，不回部位（D6）。

### 4.7 和延遲段的打斷關係（T11）

- 打斷一律產生 `CancelChargeEffect(unit_id=頭目, reason="part_broken")`，由既有的 `_cancel_charge` → `_drop` 結算，`FollowupCancelled.reason` 的 Literal 加 `part_broken`；敘事文字「蓄力被打斷（部位破壞）」。
- 適用所有 `charging`：`release: next_turn`、`release: attacked`、法術型與武器技型、BAL-21a `anchor: cast_tile` 的落在選定格（狀態一移除，`charge_infos`／環境預告就不再列那幾格）、定向蓄力。
- `release: attacked` 的蓄力被同一次攻擊打破部位時：打斷先發生（部位破壞在傷害結算當下），攻擊結算完的 `resolve_attacked_release` 找不到蓄力就不釋放——要有測試鎖住這個順序。
- `seal_skill` 只打斷「正在蓄力的就是被封的那一招」；`interrupt_charge` 打斷任何蓄力（R4）。
- 霧鎖真人：長劍只在歸一露出，打斷對象實際上是 `skill_charged_cleave`，若鎖霧的 `skill_mist_lock_peaks` 蓄力跨進歸一還沒放，一樣打斷。

### 4.8 紀錄格式（T12）

`BattleState` 欄位、動作欄位、事件都變了 → `LOG_FORMAT` `/114` → `/115`；`docs/phases/戰鬥紀錄格式變更.md` 加一條；Grep `trpg-battle-log/` 更新測試裡寫死的版號（BAL-21a 時是 11 處）。

### 4.9 內容：霧鎖真人（D16、T10、R4）

`content/units/sect_mist_lock_master.yaml` 加 `parts`（只用預設比例；檔頭註解寫 #152、18 18.2.3、占位值）：

| id | name_zh | hp_permille | reach | exposed_in | on_break |
|---|---|---|---|---|---|
| `whisk` | 拂塵 | 200 | `any` | （全程） | `seal_skill: skill_mist_shift` |
| `dantian` | 氣海 | 200 | `behind` | `[mist_lock, return_to_one]` | `stop_mechanic: mist_return` |
| `sword` | 長劍 | 200 | `any` | `[return_to_one]` | `stat_down: damage_dealt 750‰`（R4 占位）＋`interrupt_charge` |

ID 用英文、中文名照 18.2.3；護甲與抗性都不寫（同本體）。

### 4.10 證明「沒有部位的單位結果逐字不變」（分兩個 commit）

比照 `docs/phases/PhaseBAL-21a報告.md` 第 3 節的比對法；腳本放 scratchpad、不 commit。每場比對：完整事件 JSON、步驟列表（動作 JSON）、輪數、勝方、最終 `rng_state`、最終狀態 JSON（剝掉 T4 的預設值新鍵，剝了哪些寫進報告）。地圖預設陣容、效用 AI、`max_rounds=30`。

1. **commit A（引擎＋schema，`content/` 一個字都不改）**：改前在 `4e204cf9`（或派工時的 main）產生 `before.json`。
   - 8 張地圖 × 種子 1、2（`molten_heart_pit`、`rift_gate`、`cloud_summit`、`open_plain`、`bandit_lair`、`oil_depot`、`lava_crossing`、`swamp`）＋3 張頭目圖 × 種子 3～12：**`different=0`**。
   - `hash_ruleset`、一輪存檔 `ruleset_hash`、世界日誌 `content_digest` 三個值改前＝改後（報告附值）。
2. **commit B（只加霧鎖真人 `parts`）**：同一批比對。
   - 除 `cloud_summit` 外 `different=0`。
   - `cloud_summit`：事件、步驟、輪數、勝方、`rng_state` 也應 `different=0`（1a 沒有任何 AI 會帶 `target_part`、頭目 AI 未改）；最終狀態只差真人的部位欄位。不是這樣就停下回報。
   - `hash_ruleset` 不變（單位不在規則包）；`ruleset_hash`、`content_digest` 變——把 YAML 還原後算回 commit A 的值，證明變動只來自這個檔。
3. 雜湊、快照、夾具**不得整批重產**；每一項變動都要「拿掉本段改動就回到舊值」的證明，對不上不更新、先回報。

### 4.11 行為一致測試（實際跑引擎）

新檔 `tests/engine/test_boss_parts_pb1.py`（合成頭目放測試內，不加進 `content/`）＋`tests/engine/test_mist_lock_parts_pb1.py`（正式內容）＋`tests/content/test_boss_parts_content.py`。表格測試、每列一條規則句：

1. 合法性：沒有部位的目標、未知 ID、已破、未露出、`behind` 不在背後格、`behind` 用遠程、`high_or_far` 兩種成立與不成立（含 R7 的邊界 3／4）、`disabled` 三種狀態、範圍技、連鎖、沒有傷害效果的單體招、種族技、複合技第二段 → `IllegalActionError`；`part_targets` 的原因代碼逐列對。
2. 分流：同一動作打本體與打部位，HP 扣的一樣、部位扣 `hp_before − hp_after`；有護盾吸收、劍陣 −50%、格擋時部位扣的是實際扣到的 HP（R2）。
3. 部位護甲／抗性覆寫生效（合成部位 `armor_bonus` 高 → 用 `FixedRng`／強制骰比較命中）；沒寫時和本體同。
4. 範圍技、持續傷害、反應、表面打頭目時部位不變。
5. 破壞：只發一次 `PartBroken`；治療、換階段後仍是破的；破的那一下頭目倒下時不施效果（T8）。
6. 封招：被封的招不在 `legal_actions`、`UseSkill` 不合法；換到技能組含這招的階段仍封住。
7. 打斷：`next_turn`、`attacked`、`anchor: cast_tile`、定向蓄力四種蓄力被打斷（`reason: part_broken`）、預告格消失；`attacked` 型不會在同一次攻擊後又釋放（4.7 順序）。
8. 停機制：歸一中破氣海 → `mist_return` 移除、下個回合開始不回血；鎖霧中先破 → 進歸一時不加 `mist_return`。
9. `stat_down`：`damage_dealt` 降低真人之後造成的傷害；`move`、`armor`、`hit`、`resist` 各一列（合成頭目）。
10. `control`：對免疫的合成頭目施加失敗，照現行事件。
11. 多段攻擊（R5）：第一下讓頭目轉身，後面幾下仍打同一部位；中途破了，剩下的打本體。
12. 預覽：帶 `target_part` 的最少／最多都有 `PartDamaged`；預覽後狀態沒變。
13. 暫停點：打部位途中觸發 `prompt` 反應，`resume` 結果與一次跑完相同（`test_pending_serialization.py` 同款）。
14. 重播：效用 AI 不會帶部位，所以用**手寫動作序列**打一場含 `target_part` 的戰鬥，`BattleLog` JSON 往返後 `replay` 最終狀態與 `rng_state` 一致。
15. `clone()`、JSON 往返保留全部部位欄位。
16. 霧鎖真人正式內容：三個部位各 24 HP（HP 120 時）；劍陣時氣海、長劍不能選；鎖霧時氣海只能從背後近戰選；長劍只在歸一。
17. 內容檢查：非頭目帶部位、1 個或 5 個部位、加總 601‰、`on_break` 0 或 3 項、未知招／狀態／階段 ID、封的招不在任何技能組 → 載入失敗（中文訊息）；沒填 `parts` 不輸出（掃全部單位）。

### 4.12 交付與驗收

1. commit A、commit B（4.10）＋測試；報告 `docs/phases/PhasePB-1a報告.md`；更新 `docs/dev/上手-引擎戰鬥結算.md`（第一節加 `parts.py`、第二節加「部位分流」一段、第四節加「`legal_actions` 不列部位變體」一條）、`docs/phases/戰鬥紀錄格式變更.md`。
2. `ruff check`、`ruff format --check`、`mypy`、`lint-imports` 結束碼 0。
3. 相關測試（不帶 `-m`；多檔 `-n 8`）：4.11 新檔、`test_determinism.py`、`test_skill_determinism.py`、`test_status_determinism.py`、`test_state_clone.py`、`test_pending_serialization.py`、`test_combat.py`、`test_damage_formula.py`、`test_damage_sources.py`、`test_effects.py`、`test_boss_phases.py`、`test_boss_triggers.py`、`test_boss_mana_restore_bal21.py`、`test_delayed_followup.py`、`test_delayed_anchor_bal21.py`、`test_directed_charge.py`、`test_preview.py`、`test_skill_preview.py`、`test_runner_advance.py`、`test_ruleset_hash.py`、`tests/world/test_boss_battle.py`、`tests/content/` 的單位與 schema 檔、`tests/narrative/` 的事件文字檔、`tests/test_architecture.py`、版號字面值所在的 CLI／API 測試。
4. 一場紀錄＋重播：`trpg battle --map cloud_summit --seed 2 --log-json …` ＋ `trpg battle replay …`「重播驗證通過」，紀錄格式 `/115`；另跑 `oil_depot` 13、`swamp` 21 各一場。
5. 4.10 兩階段 `different=0` 與三個雜湊。
6. 合併前跑相關 slow：`tests/cli/test_output_snapshots.py -m slow`（**預期 0 個鍵變動**；有變就停下查，不重產）、`tests/skillgen/`（含 slow；`test_refactor_parity.py` 夾具不得動）、`tests/narrative/`。
7. 複雜度：`resolve` 分流、條件判斷、破壞效果分派都要拆成小函式；新增 `# noqa` 逐一寫理由。

## 5. PB-1b｜AI（R8、R9、T13）

1. **價值表**：`content/ai_profiles.yaml` 加 `parts:`（T13 的鍵與占位值，註解寫「占位，NW-3 開放後由使用者調」）；schema 在 `src/trpg/content/environment.py`。
2. **隊友與影子挑部位**（玩家方由效用 AI 控制的單位；召喚物不算，R9）：`policy.py` 產生候選時，對「目標有部位、`Attack` 或單體 `UseSkill`」的候選，另產生每個 `part_targets(...).ok` 的部位變體（**只在目標有部位時產生**，沒有部位的戰鬥候選清單逐字不變）。變體跑 `preview`，分數＝本體分＋R8 的部位分：
   - 破壞效果價值＝`on_break` 各項的 `parts.<type>` 價值相加；`seal_skill` 的招已在冷卻外、法力夠、在目前技能組＝「下一招」，`interrupt_charge` 或 `seal_skill` 對到正在蓄力的招＝「能打斷」；這兩種情況且預覽最多後果能破時加 `priority_bonus`。
   - 進度比例＝預覽的部位傷害（最少後果）÷ 部位剩餘血量，上限 1，用 `Fraction`。
   - 同分：本體優先，再照部位 ID（D11）。
3. **頭目**：人形頭目有 `reach: behind` 的部位、剩餘血量 ≤ `near_break_permille` 時，位置價值裡「背對攻擊者」的扣分（`facing.back_exposed`）多加 `guard_back_bonus`（D12「多給一點分數」）。只看有部位的頭目。
4. **候選數**：部位變體不擠掉本體候選（另計，或在 `skill_candidates` 截斷**之後**才展開），報告寫用哪一種。
5. **測試**（新檔 `tests/engine/test_parts_ai_pb1.py`）：歸一中真人正在蓄力蓄力斬、長劍剩下的血一下打得破時，隊友選長劍（能打斷）；拂塵快破、霧遁可用時優先拂塵；打不到時打本體；同分本體優先；頭目在背後部位快破時移動後背對攻擊者的機率上升（固定場面比較分數，不比機率）；確定性（同種子兩次相同）；**沒有部位的場面 `rank` 輸出逐字不變**。
6. **不變比對**：4.10 的 8 圖 × 2 種子＋頭目圖種子 3～12 再跑一次：除 `cloud_summit` 外 `different=0`；`cloud_summit` 列出變了幾場、平均事件差，寫「預期：隊友開始打部位」。
7. **快照與固定種子**：`tests/cli/test_output_snapshots.py -m slow` 逐項說明（預期 0 個鍵）；`cloud_summit` 相關固定種子測試（`tests/world/test_boss_battle.py` 等）若不再成立，照上手第四節第 6 點掃種子換一個仍成立的，斷言不放寬，逐項列出。
8. 報告 `docs/phases/PhasePB-1b報告.md`；上手筆記第二節「AI 怎麼選招」加部位變體一點。

## 6. PB-1n｜數值工坊白名單加部位欄位

1. `content/tuning_fields.yaml` 的 `kind: unit` 加：`parts[*].hp_permille`（permille，建議 50～400，說明「頭目最大 HP 的千分比；同一隻加總不能超過 600‰」）、`parts[*].armor_bonus`（int，說明「沒寫＝和本體相同」）、`parts[*].resist.<四組>`、`parts[*].element_mods.<九元素>`（permille）、`parts[*].on_break[*].amount`（int；依 `stat` 是格、點或 ‰，說明寫清楚）。
2. `src/trpg/api/tuning/objects.py`：仿 `_phase_label`（`:81`）加 `_part_label`（「部位「拂塵」」、`on_break` 項再加「破掉效果 1」）；`on_break[*].amount` 只展開 `stat_down`（仿 `_phase_skipped`）。`src/trpg/content/tuning_fields.py` 的「對得到 schema 整數欄位」檢查要認得 `BossPart`／`PartBreakEffect`。
3. 測試：NW 計畫 T-A1（每個新路徑對得到 schema）、T-A2（YAML 字面替換：流式、沒寫的 `armor_bonus` 插入、註解保留）各加部位的列；草稿把 `hp_permille` 改成三個加總 601 → `check` 擋下、中文原因；改 `whisk` 200→150 → 只差那一個值。
4. 前端表單由 `fields` 產生，預期不必改；若標籤或分組需要改再動 `client/src/tuning/`，並跑 `tuning/tuning.test.ts`。
5. 報告 `docs/phases/PhasePB-1n報告.md`；最後一節「給使用者的使用說明」三句（在哪裡改部位、加總上限、長劍降傷是占位）。

## 7. PB-1c｜前端（占位、接口先做；T14～T16）

先讀 `docs/開發PM交接.md` 6.5.1。所有選單、說明卡用共用元件，`ui/floatCardRule.test.ts` 不得加白名單。

1. **API**：`UnitView` 加 `parts: list[PartView] | None = None`（`id`、`name_zh`、`hp`、`max_hp`、`broken`、`exposed`、`reach`、`break_lines_zh`：「破掉會：……」的中文，由後端從 `on_break` 產生）；合法動作的輸出對「目標有部位」的單體動作附 `part_options: list[PartOption] | None = None`（`part_id`、`ok`、`reason_zh`，來自 `part_targets`）；動作輸入接受 `target_part`。選填一律 `X | None = None`（上手-引擎第四節第 13 點）。`uv run python scripts/export_openapi.py` → `corepack pnpm -C client gen:api`。`api/types.ts` 手寫窄化 `part_damaged`、`part_broken`、`skill_sealed`。
2. **點擊**（R1、R6）：`battle/tileClick.ts` 新結果 `{ kind: "part_menu"; targetId; actionBase }`：只在被點的單位有 `part_options` 時（瞄準單體技能，或 R1 通過時的普攻）。沒有部位的單位所有既有分支輸出不變（`tileClick.test.ts` 原表格不改）。
3. **選部位小選單** `ui/PartMenu.tsx`：用 `usePopupMenu`＋`PopupFrame`（Esc 只關選單、不取消瞄準；點外面關；同時只開一張），位置貼齊被點的格子（用 `battle/stageLayout.ts` 的 `cardPlacement` 算的錨點交給共用的 `floatPlacement`，超出畫面翻轉或往內推）。第一項「本體」預設選中；之後照部位 ID。每列：名稱、小血條（`hp/max_hp`，破掉打叉）、打不到時灰掉並寫 `reason_zh`（例「要從背後才打得到」「歸一階段才露出」）、「破掉會：……」一行（太長時完整內容放 `<Hint>`）。Enter、點本體、再點同一個頭目＝本體（R6）；方向鍵移動選取；`aria-expanded` 標在觸發元素上。
4. **角色卡**：`ui/UnitInfo.tsx` 在 HP 下列部位小血條（占位樣式 `.part-bar`，破掉打叉），每列可滑過看「破掉會：……」（`<Hint>`）。
5. **預覽**：選了部位後的預覽多一行「拂塵還剩 12」（最少／最多不同時寫「還剩 6～12」；會破時寫「會打破拂塵」）；文字放 `battle/previewText.ts`，`ActionPanel` 照現有預覽列顯示。
6. **破壞演出（占位，T16）**：`battle/specials.ts` 看到 `part_broken` 加一次重擊白閃＋微震＋浮動字「{部位} 破！」；不新增貼圖、不動 `render/battle/unitLayer.ts`。
7. **紀錄**：伺服器文字已在 1a；前端只確認 `logGroups` 不把新事件吞掉、`part_broken` 的 `tone` 是醒目的一類。
8. **測試**（vitest）：`battle/pb1cPartClick.test.ts`（點擊表：有部位／沒部位 × 瞄準單體／範圍／普攻；Enter、再點＝本體；Esc 只關選單）、`ui/partMenu.test.ts`（排序、灰掉原因、破掉打叉、`aria-expanded`）、`battle/previewText.test.ts` 加部位列、`api` 事件窄化；`floatCardRule.test.ts`、`sharedPopup.test.ts` 照舊過。後端 `tests/api/` 加 `test_parts_api.py`（`UnitView.parts`、`part_options`、帶 `target_part` 的動作與預覽）與 `test_openapi_snapshot.py`。
9. **瀏覽器實測**（6.5.1）：`?dev=1` 直接進雲頂觀頭目戰（`WorldScreen` 的 `&boss=` 開發參數），1600×900 與 800×600 各一次：「點頭目跳選單 → 選單內滑過『破掉會』說明卡 → 在說明卡內捲到底 → 釘住 → 關閉」，以及 Esc 關選單後仍在瞄準。結果寫報告。網址加 `?mute=1`、無頭 Chrome 加 `--mute-audio`；埠避開 8000／8001。
10. **截圖**（`docs/art/shots/pb1c/`，≤ 10 張、jpg 80）：選單（1600、800 各一）、灰掉的部位與原因、角色卡部位血條（含打叉）、預覽行、破壞占位演出一張；報告列「占位，待美術移植」。
11. 交件前 `corepack pnpm -C client test`、`build`、`typecheck` 各一次，結束碼分開記，全部 0（記憶「push 前看每個結束碼」）。
12. 報告 `docs/phases/PhasePB-1c報告.md`；更新 `docs/dev/上手-前端戰鬥畫面與動畫.md`（第一節加 `PartMenu.tsx`，第二節加「點有部位的頭目」一點）。

## 8. PB-1d｜模擬報表（只出報表，不調數值）

新腳本 `scripts/pb1_parts_report.py`（用 `trpg.sim.boss_probe` 的建角與歸屬規則；子命令「跑」與「重印」；結果 JSON 存 scratchpad、不進 repo；部位「關」＝在記憶體裡把範本的 `parts` 拿掉）。規模照 T17：霧鎖真人 × 8 build × 13 種子，關／開兩組同種子配對。

1. **報表一：霧鎖真人部位關／開對照**——勝率、平均輪數、每個 build 的勝率、各階段每招每回合施放率（#149 算法：只認頭目本體、回合中途轉階段且還沒放招歸新階段）、歸一 `mist_return` 的回血總量。
2. **報表二：部位統計（開）**——每個部位：被選為目標的次數、破壞率（場）、破壞時的輪數（中位數、四分位）、由哪個 build／單位打破、破壞時頭目在哪個階段；破壞效果的實際作用：拂塵破後霧遁少放幾次（對照關組同輪之後）、氣海破後少回多少 HP、長劍打斷蓄力次數與降傷後歸一造成的傷害。
3. 報告 `docs/phases/PhasePB-1d報告.md` 只貼兩張摘要表與「觀察」（例：某部位幾乎沒破、隊友打不到背後），**不寫建議數值**；數值由使用者在數值工坊調（D17）。

## 9. 共通規矩（每段派工 prompt 都要寫）

- 實作者遇到規格沒寫到、或和設計文件衝突的地方，照最保守做法做並寫進報告「待 PM 決定」（最多 10 點）；**不自己定規則**，已寫入設計文件的決定不放寬。
- 快照、雜湊、夾具不得整批重產；每一項先證明變動來自本段（拿掉改動回到舊值），對不上就停下回報；CLI 快照用 `-k` 只重產受影響的鍵。
- 開發中只跑直接相關的測試（不帶 `-m`，多檔最多 `-n 8`）；不跑 `scripts/check.py`、`trpg sim completion`、不限縮的 `matrix`；PM 跑全量期間不跑模擬。
- Windows：`uv run python`；新 worktree 先 `uv sync --frozen`，之後 `UV_NO_SYNC=1`；前端 `corepack pnpm -C client …`，新 worktree 先 `install --frozen-lockfile --offline`。
- shell 指令的字串裡不放反引號（含反引號的文字用檔案工具或 `<<'EOF'`）。
- 等待用完成通知，不寫 until／while／sleep 輪詢；不結束不是自己啟動的程序，只用自己記下的 PID；預覽埠不用 8000、8001。
- 子 agent 一律 Opus 5.5（`model: "opus"`），並往下傳同樣規矩。
- 不要 push；依交付分 commit，第一行英文，結尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 10. 報告格式

做了什麼（交付表＋commit）、逐條驗收（測試名或指令輸出為證、結束碼分開記）、現況確認（對照第 1 節，有出入就寫）、不變比對（場數、事件數、`different`、三個雜湊前後值、剝掉的預設鍵）、快照與既有測試變動逐條說明（含換種子的清單）、新增 `# noqa` 與理由、規格沒寫到而採保守做法的地方、影響（舊紀錄 `/114` 不能重播、戰鬥中存檔讀不回）、「待 PM 決定」最多 10 點。
