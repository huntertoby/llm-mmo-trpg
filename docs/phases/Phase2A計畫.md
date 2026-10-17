# Phase 2A 計畫：技能格式與執行

> 撰寫：PM｜2026-10-18｜對應 `docs/專案計畫.md` 第 14 節 Phase 2 的第一段
> 實作者請先讀：`CLAUDE.md`、`docs/phases/Phase1C報告.md` 的「給下一階段的備註」、`docs/design/06-技能.md`（全部）、`docs/design/17-未來展望.md` 第 17.5 節、`docs/design/05-戰鬥.md` 第 5.2 與 5.4 節。

Phase 2A 拆成兩個子階段，**各由一位實作者完成**：

- **Phase 2A-1｜技能資料與解譯器**：技能 schema、形狀與原語資料檔、技能解譯器、`UseSkill` 動作、法力與冷卻、事件、`preview`、CLI、示範技能、最低限度的 AI 支援。
- **Phase 2A-2｜條件與 AI**：技能條件、敵人技能、AI 候選篩選與評分、效能、技能使用報表。

2A-1 完成並經 PM 驗收後，才開始 2A-2。**本文件第 1–4 節兩個子階段共用，第 5 節是 2A-1，第 6 節是 2A-2。**

---

## 0. PM 決定（1C 報告「待 PM 決定」）

| # | 項目 | 決定 | 由誰實作 |
|---|---|---|---|
| 1 | 半掩護不看目標高度 | **改**：1C 規格 3.2 的四個條件之外，再加第 5 條「C 的地形高度 ＋ 1 ≥ 目標所在格的高度」。站在高台上的目標不再被旁邊地面的木箱掩護 | 2A-1 |
| 2 | 平衡測試 | `tests/engine/test_demo_balance.py` 加上 `@pytest.mark.slow`，預設不跑（`pyproject.toml` 設定 `-m "not slow"`，註冊 marker）。勝率改由 `scripts/sim_demo_maps.py` 報表檢查；2A 不要求勝率落在範圍內，平衡在 2C 統一調整 | 2A-1 |
| 3 | AI 候選篩選 | 技能動作納入候選與評分，見 5.7（最低限度）與 6.3（完整） | 2A-1／2A-2 |
| 4 | 立即生效的時間點 | 接受（佇列清空前依單位 ID 觸發） | — |
| 5 | AI 掩護權重語意 | 接受；2C 再依模擬調整 | — |
| 6 | 漏油範圍與條件 | 接受 | — |
| 7 | 盜賊盾衛數值 | 接受 | — |
| 8 | 推擊被友方擋住不合法 | 接受（Shove 動作）；**技能的推擊／拉扯被擋住時只是停在被擋住前的格子**，不使動作不合法 | 2A-1 |
| 9 | `bridge_chasm` 繞行通道 | 接受，做地圖類型時（2C）再檢討 | — |
| 10 | 測試時間 | 由決定 #2 處理 | — |

---

## 1. 範圍

**要做**：技能的資料格式（含未來欄位）、形狀與原語的資料檔、把技能 JSON 轉成引擎效果佇列的解譯器、單位裝備技能並在戰鬥中使用、`preview` 與效用 AI 支援技能。

**不要做**：
- 預算計算、硬性上限中的「改寫規則型限制」與互斥表、骨架結構驗證、稀有度限制、隨機組合器 → 2B。資料格式要留好欄位，但不實作規則。
- 被動、反應技、姿態的 **執行**（觸發時機系統）→ 之後的子階段。schema 必須能表示它們，戰鬥中只執行 `kind: active`。
- 新狀態（`slow`、`root`、`stun`、`weaken`、`vulnerable`、`bleed`、`poison`……）與控制遞減 → 2B。2A 只用現有 4 種狀態。
- 召喚、改寫規則型原語、`damage_over_time`、`delayed_damage`、`shield`、層數類原語 → 2B 以後。
- 雙屬性縮放、專精加成（6.10）、裝備連動與技能卡片（6.11）、技能等級成長（`rank` 只存不用）。
- 批次模擬器、地圖類型 → 2C。LLM、前端 → Phase 3、4。

---

## 2. 工作環境

- 在雲端工作區的 repo 內工作（路徑由 PM 在派工時告知）；不要使用任何 `mcp__remote-devices__` 工具。
- 每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`；`uv sync`；`uv run python scripts/check.py` 五項全過（ruff、格式、mypy strict、import-linter、pytest）。
- 原則上不新增執行相依。
- git：在 `main` 上依邏輯分 commit，每個 commit 結尾帶兩行：

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QsCrKjNMH4hmP3gs4Y78Cu
```

- **不要 push**，由 PM 負責。
- 遵守 `CLAUDE.md` 守則 11（節省 token）。

---

## 3. 資料格式（2A-1 與 2A-2 共用）

### 3.1 檔案位置

| 檔案 | 內容 |
|---|---|
| `content/skill_shapes.yaml` | 10 種目標形狀的定義：`id`、`name_zh`、`targeting`（`self`／`unit`／`tile`／`direction`／`none`）、參數及其範圍 |
| `content/skill_primitives.yaml` | 2A 支援的效果原語：`id`、`name_zh`、`category`（`numeric`／`structural`／`rule_rewrite`）、`min_rarity`、`harmful`（決定 `affects` 預設值）、參數說明。**不放預算點數**（2B 才加，但 schema 要允許之後新增欄位） |
| `content/skills/<id>.yaml` | 一個檔一個技能 |

`trpg content check` 要驗證以上所有檔案，並檢查技能引用的形狀、原語、狀態、表面、物件都存在。

### 3.2 技能 schema（`SkillDef`，pydantic，`extra="forbid"`）

```yaml
id: skill_ashen_oath          # 必填，^skill_[a-z0-9_]+$
schema_version: 1
name_zh: 灰燼誓約
description_zh: null          # 可省略；CLI 顯示時由形狀與效果自動產生摘要
tier: 2                       # 1–5
rank: 1                       # 1–5，2A 只存不用
rarity: rare                  # common / rare / epic / legendary
kind: active                  # active / reaction / passive / stance
skeleton: area                # 6.9 的 12 種骨架 ID 之一（2B 才驗證結構）
category: spell               # weapon / spell
weapon_req: focus             # melee / ranged / focus / any
ap_cost: 2                    # active 必填 1–3；其他 kind 必須為 null
scaling_attr: int             # str / dex / con / int / wis / wil
shape: {type: cone, size: 3}
effects:                      # 1–4 個
  - {type: damage, dice: 2d6, element: fire}
  - {type: create_surface, surface: fire, duration: 2}
condition: null               # 2A-2 才實作，2A-1 必須為 null
cost: {mana: 12, cooldown: 2} # 見 3.5
tags: [fire, ash, area]
narrative:
  concept: 在燒毀村莊中覺醒的灰燼之力
  cast_flavor: 灰燼從你掌心捲起，化作燎原之火
provenance:                   # 17.5：技能是獨立實體
  origin: builtin             # builtin / level_up / drop / crafted / taught / tome
  owner_id: null              # 擁有者（角色 ID）；內建技能為 null
  created_by: null            # 合成者或傳授者
  parents: []                 # 合成來源技能 ID
  bound: true                 # 學會後綁定
  tradeable: false
```

**載入時的驗證**（違反時錯誤訊息用中文、指出檔案與欄位）：
- `category: weapon` 只能搭配 `weapon_req: melee|ranged`；`category: spell` 只能搭配 `focus|any`（6.11）。
- 效果原語 ≤ 4 個；推擊、拉扯距離 1–2（6.6）。
- 形狀與效果的參數在資料檔定義的範圍內；引用的 ID 都存在。

### 3.3 形狀（全部 10 種都要實作）

方向只有東南西北 4 個。「射程」一律為曼哈頓距離。除非另外說明，被選中的格子或單位必須在施放者的視線內（沿用 `has_line_of_sight`），隱蔽規則與普攻相同。

| 形狀 | 參數 | 選取 | 影響的格子 |
|---|---|---|---|
| `self` | — | 無 | 施放者所在格 |
| `single` | `range`（整數或 `"weapon"`＝武器射程） | 一個單位或一個可被攻擊的物件 | 目標所在格 |
| `line` | `size` 2–6 | 方向 | 正前方第 1…`size` 格；遇到 `wall` 停在它之前；遇到阻擋視線的物件時包含該格後停止 |
| `cone` | `size` 2–4 | 方向 | 第 k 排（k＝1…`size`）為正前方第 k 格及其左右各 k−1 格；只含施放者看得到的格子 |
| `cross` | `range` 0–6 | 中心格（0＝施放者自己） | 中心 ＋ 四方向相鄰格 |
| `square3` | `range` 0–6 | 中心格 | 以中心為準的 3×3 |
| `ring` | `radius` 1–2 | 無 | 與施放者切比雪夫距離恰為 `radius` 的格子 |
| `ground_tile` | `range` 1–6 | 一格 | 該格 |
| `chain` | `range` 1–6、`jumps` 1–3、`jump_range` 1–3 | 第一個目標單位 | 第一個目標，之後每跳選「距上一個目標 ≤ `jump_range`、看得到、尚未被擊中」的最近敵方單位，同距離依單位 ID；沒有可跳的就停止 |
| `allies_in_radius` | `radius` 1–3 | 無 | 與施放者曼哈頓距離 ≤ `radius` 的格子（含自己） |

- 中心格型（`cross`、`square3`、`ground_tile`）只要求中心格在射程與視線內；其餘格子不需要視線。
- 影響範圍不含地圖外的格子與 `wall` 格。
- 影響格子的計算放在獨立的純函式模組（例如 `trpg.engine.skills.shapes`），以便 `preview`、AI 與之後的前端共用。

### 3.4 效果原語（2A 支援的 11 種）

| 原語 | 參數 | 說明 |
|---|---|---|
| `damage` | `dice`（法術技必填）、`multiplier_permille`（武器技用，預設 1000）、`element`（可省略） | 見 4.2 |
| `heal` | `dice` | 治療量 ＝ 骰值 ＋ 縮放屬性 × `spell_attr_multiplier_permille` ÷ 1000 |
| `push` | `distance` 1–2 | 以施放者為原點往外推；中心格型以中心為原點；被擋住時停在擋住前的格子（決定 #8），撞擊與墜落沿用既有規則；steadfast 減半，0 格只是不移動 |
| `pull` | `distance` 1–2 | 往施放者方向拉，規則同上 |
| `knock_prone` | — | 對抗判定（沿用 `_contest`，攻方用技能的縮放屬性，守方用相同屬性）成功才倒地 |
| `teleport` | — | 只能搭配 `ground_tile`：施放者移動到目標格（目標格必須可站立、無單位）；觸發抵達與表面進入效果，不觸發藉機攻擊 |
| `apply_status` | `status`、`duration`（可省略） | 只能用 `statuses.yaml` 中的狀態 |
| `create_surface` | `surface`、`duration`（可省略） | 經 `effects.world.set_surface`；`team` 設為施放者陣營（見 4.4） |
| `destroy_object` | — | 摧毀影響格中的可破壞物件 |
| `create_obstacle` | `object` | 在影響格中的空格產生物件（例如 `crate`、`low_wall`） |
| `raise_terrain`／`lower_terrain` | `amount` 1 | 沿用現有效果，高度維持 0–3 |

每個效果另有 `affects`：`enemies`／`allies`／`all`／`self`／`tiles`。省略時依原語的 `harmful` 欄位：有害者 `enemies`、有益者 `allies`、地形類 `tiles`。

- **技能的直接效果預設不誤傷友方**（PM 決定）。`affects: all` 是「敵我不分」的可選標記：範圍內的友方也會被擲命中骰並吃到效果（施放者自己除外，除非形狀包含自己且 `affects` 為 `all`）。2B 做預算時會給這類技能折扣，2A 只需正確執行。
- 由技能引發的 **連鎖反應**（爆炸、雷電沿水擴散、表面的持續效果）維持現有規則，敵我不分。
- 至少一個示範技能或測試技能使用 `affects: all`。

### 3.5 代價

| 欄位 | 說明 |
|---|---|
| `ap_cost`（頂層） | 1–3 |
| `cost.mana` | 消耗法力；不足時不可使用 |
| `cost.cooldown` | 1–6。使用後設定冷卻 N；自己回合開始時 −1（5.2.1）；為 0 才可使用。因此冷卻 1 ＝ 每回合限一次，冷卻 2 ＝ 隔一回合 |
| `cost.uses_per_battle` | 每場限用次數 |
| `cost.hp_percent` | 消耗最大 HP 的 ‰（無條件進位）；目前 HP 不大於消耗量時不可使用 |

---

## 4. 規則（2A-1 與 2A-2 共用）

### 4.1 命中

- 技能對 **每個受影響的敵方單位** 各擲一次命中（依單位 ID 排序擲骰），公式同普攻（5.4），含高度、半掩護、隱蔽、優劣勢。命中 → 該目標吃到所有以敵方為對象的效果；失手 → 該目標不受影響。自然 20 暴擊時傷害骰顆數加倍。
- 以友方、自己或格子為對象的效果 **不擲骰**、必定生效；地面效果（表面、地形、障礙）即使所有敵人都失手也照樣生效。
- 攻擊值：**武器技** 沿用 `attack_value(unit)`（武器的屬性 ＋ 武器加值）；**法術技** 用「技能縮放屬性值 ＋ 武器加值（只有法器類武器才加）」。
- 半掩護判定用施放者的位置，近戰武器技（射程 ≤ 2）無視半掩護，與普攻相同。
- 物件：影響格中的可破壞物件受到 `damage` 效果時，比照普攻打物件的規則（不擲骰）；帶元素的傷害照現有規則觸及格子（點燃油桶、電到水面等），**每格只觸及一次**。

### 4.2 傷害

- **法術技**：`dice` ＋ 縮放屬性 × `spell_attr_multiplier_permille`（`core.yaml` 新增，初始 500）÷ 1000，再套元素修正與天氣。
- **武器技**：（武器骰 ＋ 武器固定值 ＋ 縮放屬性 × `basic_attack_attr_multiplier_permille` ÷ 1000）× `multiplier_permille` ÷ 1000，再套元素修正與天氣。縮放屬性用技能的 `scaling_attr`。
- **元素灌注**：武器技的 `damage` 沒有寫 `element` 時，繼承武器的元素（6.11）。法術技必須寫 `element`。
- 格擋等反應照常觸發（技能命中視同攻擊命中；範圍技能的反應規則照現有的 `targeted_by_melee` 等事件判斷）。

### 4.3 武器分類

- `content/weapons.yaml` 每把武器新增 `weapon_class`：`melee`／`ranged`／`focus`。
- 技能的 `weapon_req` 與單位武器不相容時：載入單位範本時報錯；`any` 永遠相容。

### 4.4 表面擁有者

留在場上的表面視為環境（PM 決定）：

- 技能產生的表面記錄施放者陣營（`team`）。
- **有害的表面**（火、毒、冰……）敵我都受影響，與地圖上的同種表面相同。
- **有益的表面**（`holy` 這類 `allies_only` 的表面）只對施放者陣營生效（1B 決定 #8 的延續）。
- 地圖預先放置的表面沒有陣營，維持中立（雙方都可受益）。

### 4.5 單位與狀態

- 單位範本新增 `skills`（技能 ID 列表）與 `max_mana`（預設 0）。依 `kind` 檢查欄位上限（`core.yaml` 新增 `skill_slots: {active: 6, passive: 2, reaction: 1, stance: 1}`）。
- `UnitState` 新增 `mana`、`max_mana`、技能列表、冷卻、每場已用次數。**記得同步修改 `clone`**。法力 2A 不回復（之後由模擬決定）。
- 回合開始時冷卻 −1。

### 4.6 動作與事件

- 新動作 `UseSkill(unit_id, skill_id, target_id?, target_object_id?, target_pos?, direction?)`，依形狀的 `targeting` 只允許對應欄位；不合法時 `IllegalActionError`（中文原因）。
- `legal_actions` 列出所有可用技能 × 所有合法選取（中心格型列出射程內每一個合法格；方向型列出 4 個方向，影響範圍為空的不列）。
- 新事件 `SkillUsed`（施放者、技能 ID、`name_zh`、AP、法力、影響格子列表），以及冷卻／法力變化。命中擲骰事件要能看出來自哪個技能。
- 解譯器把一次 `UseSkill` 轉成效果佇列中的效果，**不得繞過效果佇列**；連鎖深度沿用現有上限。
- 重播：`--log-json` 的動作列表能序列化／還原 `UseSkill`。

---

## 5. Phase 2A-1｜技能資料與解譯器

### 5.1 交付項目

1. 第 0 節決定 #1、#2、#8 的實作與測試。
2. 第 3 節的資料檔與 pydantic schema、`trpg content check` 驗證。
3. 形狀模組（3.3）與解譯器（3.4、4.1、4.2）。
4. `weapon_class`、法力、冷卻、技能欄位、表面擁有者（4.3–4.5）。
5. `UseSkill` 動作、`legal_actions`、事件、重播（4.6）。
6. `preview` 支援 `UseSkill`：每個受影響單位的命中率、傷害範圍與期望值、影響格子、連鎖結果（沿用 `simulate_preview` 與 `mark_branch` 的機制）。
7. 示範技能與英雄裝備（5.2）。
8. 最低限度的 AI 支援（5.3）。
9. CLI（5.4）。

### 5.2 示範技能

至少 12 個，覆蓋全部 10 種形狀、11 種原語、兩種 `category`、四種 `weapon_req` 中的三種以上。建議如下（名稱與數值可調整，報告中列出最終表）：

| 英雄 | 技能 |
|---|---|
| 戰士 | 碎骨重擊（`single` weapon，傷害 ×1500 ＋ 擊倒，2 AP）、旋風斬（`ring` 1，傷害 ×1000，2 AP，冷卻 3）、颶風踢（`single`，傷害 ×800 ＋ 推 2，1 AP，冷卻 2） |
| 弓手 | 穿透射擊（`line` 5，傷害 ×1000，2 AP）、鉤索箭（`single`，傷害 ×600 ＋ 拉 2，1 AP）、煙幕箭（`square3` 射程 5，產生 darkness 表面，1 AP） |
| 法師 | 火焰箭（`single` 5，2d8 火 ＋ 燃燒，1 AP）、灰燼誓約（3.2 的範例）、閃現（`ground_tile` 3 ＋ `teleport`，1 AP，冷卻 3） |
| 風暴使 | 連鎖閃電（`chain`，1d10 雷電，2 AP）、喚潮（`cross` 射程 4，產生 water 表面，1 AP）、石牆術（`ground_tile` 3，`raise_terrain` 或 `create_obstacle`）、聖域（`allies_in_radius` 2，`heal` ＋ 在腳下產生 holy 表面） |

剩下的原語（例如 `destroy_object`、`lower_terrain`、`apply_status: concealed`）可用測試專用技能覆蓋（放 `tests/` 內的 fixture，不放 `content/`）。英雄範本設定合理的 `max_mana`。

### 5.3 最低限度的 AI 支援

- 效用 AI 把 `UseSkill` 納入候選，用完整 `preview` 評分（友方受到的傷害算負分）。
- 簡單篩選：只考慮影響範圍內至少有一個敵方單位、可破壞物件，或（有益技能）至少有一個受傷友方的選取。
- 2A-1 不要求效能目標，但在報告中列出四張示範地圖「每個動作含 AI」的中位數，與 1C 比較。

### 5.4 CLI

- 戰鬥紀錄顯示技能使用，例如：`法師 施放「灰燼誓約」（AP 2，法力 12）→ 影響 6 格`，之後是各目標的命中與效果。
- 回合標頭顯示法力（例如 `AP 3，移動 5，法力 28/40`）。
- `trpg skills list`（表格：ID、名稱、骨架、AP、代價）與 `trpg skills show <id>`（完整內容與自動產生的效果摘要）。

### 5.5 2A-1 驗收條件

1. `uv run python scripts/check.py` 五項全過（平衡測試已改為 slow）；Phase 1 的情境測試仍成立。
2. 決定 #1：站在高 2 高台上的目標，旁邊地面的木箱 **不** 提供半掩護；地面目標旁的木箱仍提供。
3. 每種形狀至少一個測試，驗證影響格子（含邊界、牆壁、視線、`line` 被物件截斷、`chain` 的跳躍與同距離排序）。
4. 每種原語至少一個測試；`push` 被擋住時停在前一格、steadfast 減半為 0 時不移動且動作仍合法。
5. 情境測試：
   - 灰燼誓約的錐形範圍內有油桶 → 油桶爆炸，連鎖照既有規則結算
   - 喚潮產生水面 → 連鎖閃電打中站在水面的目標 → 雷電沿水面擴散
   - 旋風斬使用火焰武器的單位 → 傷害為火焰（元素灌注）
   - 範圍技能對 3 個敵人各擲一次骰，失手的目標不受傷，但表面照樣產生
   - 技能產生的 holy 表面只治療施放者陣營；技能產生的 fire 表面會燒到施放者的友方
   - 預設的範圍傷害技能不傷友方；`affects: all` 的技能會對範圍內的友方擲骰並造成傷害
   - 法力不足、冷卻中、用完次數、HP 不夠支付時，該技能不在 `legal_actions`，直接 resolve 拋出 `IllegalActionError`
   - 冷卻 2 的技能：第 1 輪用，第 2 輪不可用，第 3 輪可用
6. `weapon_req` 不相容、超過欄位上限、效果超過 4 個、推擊 3 格、引用不存在的原語，在載入時被拒並有中文訊息。
7. 固定骰值時，`preview` 對技能的預測與實際結算一致（至少涵蓋單體、範圍、連鎖、會引爆物件的技能）。
8. 確定性：相同種子與動作列表重播結果一致（含技能）；hypothesis 測試隨機選 `legal_actions` 跑完多場戰鬥不拋例外。
9. `trpg battle --map oil_depot --seed 42` 跑完，紀錄中至少出現 3 個不同的技能；`--log-json` 後 `trpg battle replay` 結果一致。
10. 報告附四張示範地圖各 20 個種子的勝率與平均輪數（`scripts/sim_demo_maps.py`），只列出、不調整。

---

## 6. Phase 2A-2｜條件與 AI

> 2A-1 驗收後，PM 會在本節開頭補上「2A-1 驗收後的 PM 決定」。

### 6.1 條件

技能層級的 `condition` 決定技能能否使用（不成立時不在 `legal_actions`）；效果層級的 `condition` 決定該效果是否對某個目標生效。2A-2 實作：

| 條件 | 參數 | 判斷對象 |
|---|---|---|
| `target_hp_below` | `permille` | 目標 HP ÷ 最大 HP |
| `self_hp_below` | `permille` | 施放者 |
| `height_advantage` | — | 施放者所在高度 > 目標所在高度 |
| `target_on_surface` | `surface` | 目標腳下的表面 |
| `target_has_status` | `status` | 目標身上的狀態 |

條件放進 `content/skill_conditions.yaml`（`id`、`name_zh`、`harshness`：`common`／`harsh`，供 2B 的條件倍率使用）。新增 2–3 個示範技能使用條件，例如「對燃燒中的目標額外傷害」「站在高處時射程與傷害提升」。

### 6.2 敵人技能

- `bandit_boss` 與 `bandit_archer` 各裝備 1–2 個技能（例如 Boss 的錐形劈砍、弓手的火焰箭會點燃油桶）。
- 其他敵人維持只有普攻，保留對照組。

### 6.3 AI

- 篩選：依技能影響格子判斷是否值得完整預覽（擴充 `worth_previewing`），每種技能最多保留前 N 個選取（N 放 `ai_profiles.yaml` 的 `skill_candidates`）。
- 評分：法力與冷卻的機會成本（權重放 `ai_profiles.yaml`）、友軍誤傷、治療只算實際補到的量、表面與地形效果的價值（例如在敵人腳下產生火面）。
- 既有 AI 測試仍通過；`test_fast_move_scores_match_full_preview` 仍通過。

### 6.4 2A-2 驗收條件

1. `uv run python scripts/check.py` 五項全過；2A-1 驗收條件仍成立。
2. 每種條件的成立／不成立各一個測試（技能層級與效果層級都要）。
3. AI 情境測試：
   - 三個敵人排成一列時，弓手選擇穿透射擊而不是普攻
   - 範圍技能會打到友方時，AI 選擇不會誤傷的方向或改用其他動作
   - 友方受重傷時，風暴使使用聖域
   - 法力只夠用一次強技能時，AI 不會在沒有目標價值時浪費
4. 效能：四張示範地圖「每個動作含 AI」的中位數 ≤ 8 ms（報告附 1C、2A-1、2A-2 三欄比較）。
5. `scripts/sim_demo_maps.py` 新增技能使用統計：每個技能被使用的次數、平均傷害、命中率；報告附表（不調整數值）。
6. 重播與確定性測試仍通過。

---

## 7. 完成報告格式

`docs/phases/Phase2A-1報告.md`、`docs/phases/Phase2A-2報告.md`，格式同前：

1. 摘要（3–5 行）
2. 交付項目與 commit 列表
3. 驗收條件逐條結果（附測試名稱或指令輸出）
4. 設計與實作說明（模組結構、重要的取捨）
5. 數據表（示範技能表、勝率與輪數、效能）
6. 待 PM 決定（依重要性排序，最多 10 點）
7. 給下一階段的備註
8. 附錄：代表性的 CLI 輸出節錄
