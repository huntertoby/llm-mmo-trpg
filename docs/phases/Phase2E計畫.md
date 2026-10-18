# Phase 2E 計畫：補模板 B——事件觸發、反應、姿態、層數與陷阱

> 撰寫：PM｜2026-10-19｜對應 `docs/專案計畫.md` v0.2.1 第 14 節 Phase 2E
> 實作者請先讀：`CLAUDE.md`、本檔第 0–2 節與你負責的子階段一節、`docs/phases/Phase2D-2報告.md` 第 4、9 節。需要時再查 `docs/design/06-技能.md` 6.3、6.5、6.6、6.9、6.12 與 `docs/design/05-戰鬥.md` 5.2.1、5.9；資料欄位說明在 `content/statuses.yaml`、`content/reactions.yaml`、`content/skeletons/strike.yaml` 開頭的註解。

**目標：技能可以「在某件事發生時」自動生效，讓被動、反應技、姿態、蓄力／終結、陷阱這五種骨架做得出來，而且觸發不會失控。** 這不是平衡階段：所有數值都是初值，模擬只記錄、不調整。

| 子階段 | 內容 | 解鎖 |
|---|---|---|
| **2E-1｜觸發核心 ＋ 被動**（第 3 節） | 觸發時機資料檔、技能的 `trigger` 欄位、技能觸發的分派與 **觸發深度上限**、防無限迴圈；`passive` 骨架與預算；手寫被動；組合器產生被動 | 被動；補 Phase 2 驗收 ⚠️ #1、#11 |
| **2E-2｜反應技、擋攻擊、姿態**（第 4 節） | `reaction` 類技能接進反應規則；反擊；**替隊友擋攻擊**（`intercept`）；`stance` 姿態；AI 會開姿態；守護者 build | 反應、姿態、坦克擋刀 |
| **2E-3｜層數、陷阱與收尾**（第 5 節） | 層數（施放者自身與目標身上兩種）、`builder_finisher` 骨架；`trap` 陷阱；新 build；全量 fuzz、completion、build 矩陣；2E 驗收總表 | 蓄力流、陷阱流 |

子階段依序進行，前一段驗收後才開始下一段；PM 可能依前一段的報告修訂後面的章節。

---

## 0. PM 決定

### 0.1 2D-2 報告「待 PM 決定」

全部接受。平衡相關的已記入 `docs/PM交接.md` 3.3，本階段不處理。

| # | 項目 | 決定 |
|---|---|---|
| 1 | `skill_hex_bolt` 的 `marked` 持續 1 | 接受（平衡階段，交接 3.3） |
| 2 | `skill_dread_gaze`、`skill_hush` 法力 3、無冷卻，貼著預算下限 | 接受（平衡階段，交接 3.3） |
| 3 | `build_warlock` 用 `fire_staff`、`cunning` | 接受 |
| 4 | 致盲的距離上限也套用在友方單位目標的技能 | 接受 |
| 5 | 沉默的價值判斷只看「有法力足夠的法術技」 | 接受 |
| 6 | 恐懼只限制主動移動的每一步 | 接受 |
| 7 | `CONTROL_STATUSES` 未含 feared／silenced／blinded | 接受（平衡階段，交接 3.3） |
| 8 | 護盾吸收量歸施放者；`build_tank`、`build_healer` 不通過矩陣標準 2 | 接受（平衡階段，交接 3.3） |
| 9 | AI 對已標記目標重複施放咒印飛彈 | 接受（平衡階段，交接 3.3） |
| 10 | renderer 的 `source_lost` 改為「來源離場」 | 接受 |

### 0.2 本階段的設計決定（使用者已同意或 PM 決定）

| # | 決定 |
|---|---|
| A | **拆成三個子階段**（使用者同意）。 |
| B | **層數兩種都支援**（使用者決定）：層數類型以資料定義，每種指定累積在 **施放者自己**（`owner: self`，蓄能資源）或 **命中的目標**（`owner: target`，疊印記）。 |
| C | **姿態**（使用者同意）：花 1 AP 進入，持續到取消；同時只能有一個姿態，進入新姿態會取代舊的；取消免費（自己回合內）；倒下或戰鬥結束時解除。 |
| D | **陷阱對敵方隱藏**（使用者同意）：敵方 AI 不知道陷阱的位置、不會迴避；敵人踩到或延遲回合數到了就觸發；我方（放置者陣營）看得到。 |
| E | **只做「觸發型」被動**（觸發時機 ＋ 效果）。「修正型」被動（例如 6.9 的「燃燒中的敵人受到傷害 +10%」）需要另一套常駐修正系統，不在本階段。 |
| F | **觸發的效果不擲命中**（自動命中）；傷害照法術技公式（骰值 ＋ 縮放屬性 × `spell_attr_multiplier_permille`）；施加狀態照常擲抵抗。所以被動技能一律 `category: spell`、`weapon_req: any`。反應技不同：反應技是「立刻施放一次技能」，照一般技能擲命中（見 4.1）。 |
| G | **替隊友擋攻擊用新原語 `intercept`**（稀有、只能出現在反應技）。它和 6.3 的改寫規則型原語 `redirect_damage`（任意轉移傷害，傳說）是不同的東西；`redirect_damage` 仍延後。 |
| H | 6.12「史詩：觸發」：被動骨架的最低稀有度為 **epic**；反應技、姿態、蓄力／終結、陷阱骨架為 **rare**（它們不是 6.12 的「觸發」，是結構型）。 |
| I | 狀態的 `on_turn_start_damage`／`on_turn_start_heal` 與表面的 `on_turn_start` **維持原樣**，不改寫成觸發系統（能動但改動大，之後再說）。 |
| J | 所有新數值（點數、係數、持續回合、AI 權重）都是 **初值未經模擬**，在資料檔註解標明。 |

---

## 1. 範圍

**要做**：你負責的子階段一節中的交付項目。

**不要做**：
- 任何平衡：勝率、輪數、技能數值、AI 權重的「調好」。若初值造成例外或僵局，修的是程式或規則。
- 修正型被動（決定 E）、召喚、改寫規則型原語（含 `redirect_damage`）、偷取／驅散增益。
- 把狀態與表面的 `on_turn_start_*` 改寫成觸發（決定 I）。
- 新地圖、前端、LLM、roguelite。
- 修改 `docs/專案計畫.md`、`docs/design/`、`CLAUDE.md`、`docs/phases/` 下的計畫檔。

**引擎改動原則**（沿用 2D）：
- 狀態效果一律經過 `trpg.engine.rules.statuses` 的函式判斷 **欄位**，不直接判斷狀態 ID。
- 「來源離場即移除」一律用既有的 `is_removed_with_source`，不要另寫判斷（2D-2 報告 9 節）。
- `preview` 必須和實際結算一致（固定骰值時相同），**包含觸發的效果、反應技與擋攻擊**。
- 新的事件型別要能序列化、重播（`trpg battle replay` 通過）；`LOG_FORMAT` 有新事件時升版（目前 `/7`）。
- 確定性：觸發的順序一律排序（見 3.3），不依賴 `set` 或 `dict` 的插入順序以外的東西。
- CLI 的事件文字（`trpg.cli.render`）用繁體中文。

---

## 2. 工作環境

- 每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`，再 `uv sync`。
- 開發中只跑相關測試（`uv run pytest -q tests/<路徑> -x`）；`scripts/check.py` 只在每個 commit 前與子階段結束時跑。
- 大型模擬（completion、matrix）**只在 2E-3 最後各跑一次全量**，用 `--jobs 2`，在背景等待。
- 每完成一個交付項目就 commit。
- 既有測試因軌跡改變而需要更新期望值時，在報告逐一列出原因；不是軌跡的資料／數量變動另列。

---

## 3. Phase 2E-1｜觸發核心 ＋ 被動

### 3.1 觸發時機資料檔 `content/skill_triggers.yaml`（新）

每個觸發時機一筆，以 pydantic schema 驗證、載入到 `Ruleset`：

| 欄位 | 說明 |
|---|---|
| `id` | 觸發時機 ID |
| `name_zh`、`description_zh` | 顯示用 |
| `has_other` | 這個時機是否有「另一方」單位（見 3.2 的 `target: other`） |
| `budget_coefficient_permille` | 被動技能的預算係數（取代主動技能的 AP 係數，見 3.5） |
| `min_rarity` | 最低稀有度（決定 H：全部 `epic`） |

初始內容（係數全是初值）：

| id | 何時觸發（帶有此被動的單位稱為「持有者」） | 另一方 | 係數 ‰ |
|---|---|---|---|
| `on_hit` | 持有者的攻擊（普攻或技能）命中一個單位，在該次傷害結算之後 | 被命中的單位 | 400 |
| `on_crit` | 同上，且為暴擊 | 被命中的單位 | 250 |
| `on_natural_20` | 持有者的攻擊擲出自然 20（不論是否命中物件或單位，只計單位目標） | 攻擊目標 | 150 |
| `on_kill` | 持有者造成的傷害（任何來源歸給持有者的 `DamageDealt`）讓單位倒下 | 倒下的單位 | 300 |
| `on_damaged` | 持有者受到傷害（`amount > 0`，任何原因，含持續傷害與環境） | 傷害來源（沒有來源時為無） | 400 |
| `on_turn_start` | 持有者回合開始，在狀態與表面的回合開始效果之後（被跳過的回合不觸發） | 無 | 500 |
| `on_turn_end` | 持有者回合結束，在狀態倒數之前 | 無 | 500 |
| `on_move` | 持有者的一次 **主動移動動作** 完成後（不是每一步；強制位移不算） | 無 | 300 |
| `every_n_hits` | 持有者累計命中第 n、2n、3n…次時（計數方式同 `on_hit`；n 由技能指定，2 或 3） | 被命中的單位 | n=2：500、n=3：600 |

### 3.2 技能的 `trigger` 欄位

`SkillDef` 新增 `trigger: TriggerSpec | None`。`kind: passive` **必須** 有 `trigger`，其他 kind 不可有。

```yaml
trigger:
  event: on_hit          # skill_triggers.yaml 的 id
  n: 3                   # 只有 every_n_hits 使用（2 或 3）
  target: other          # self（持有者）或 other（另一方；只有 has_other 的時機可用）
  max_per_round: 1       # 每輪最多觸發幾次（1–3，預設 1；每輪開始時重設）
  max_distance: 1        # 可省略；target: other 時另一方與持有者的曼哈頓距離上限（例如荊棘只反彈近戰）
```

- 被動技能：`kind: passive`、`skeleton: passive`、`ap_cost: null`、`category: spell`、`weapon_req: any`（決定 F）、`shape: self`（形狀只表示「作用在 trigger.target 指定的單位」，不是範圍）。
- 技能既有的 `condition` 照常使用，判斷的「目標」是 `trigger.target` 指定的單位（例如 `on_hit` ＋ `target_has_status: marked`）。
- 被動技能可以有 `cost`（法力、冷卻）；付不起時不觸發。冷卻在觸發時開始計算。
- 效果的 `affects`：`target: self` 時只能 `self`；`target: other` 時照效果原語的預設（傷害對敵方、治療對友方……），不符合的對象不受影響。
- 被動技能要佔 `core.yaml` 的 `skill_slots.passive`（已存在，2 格）。

### 3.3 引擎：技能觸發的分派

新增 `trpg.engine.skill_triggers`（或擴充 `trpg.engine.triggers`，由你決定；不得匯入上層模組）：

1. **收集**：引擎在結算中產生的事件（包括不經過效果佇列、直接 `ctx.emit` 的 `AttackRolled`）要能被技能觸發看到。做法由你決定（例如在 `Ctx` 上掛一個觸發收集器）。
2. **延後結算**：一個效果佇列（`execute`）清空之後，才依序結算這段期間收集到的觸發。觸發的技能效果以 **新的** `execute` 結算（效果佇列的 `depth` 從 0 開始，環境連鎖上限照舊），並帶著 **觸發深度** `trigger_depth`（由產生它的觸發 +1；玩家或 AI 的動作本身為 0）。
3. **順序**：同一批觸發依「事件發生順序 → 持有者單位 ID → 技能 ID」排序。
4. **觸發深度上限**：`core.yaml` 新增 `max_trigger_depth: 3`。一個觸發若會讓 `trigger_depth` 超過上限，就不結算，改發出新事件 `TriggerLimitReached`（持有者、技能、深度）。這是 6.6「觸發連鎖深度 ≤ 3」的技能層級版本。
5. **次數限制**：每個（單位，技能）每輪最多觸發 `max_per_round` 次；計數存在 `UnitState`（新欄位，可序列化），在 `RoundStarted` 重設。`every_n_hits` 的命中計數整場戰鬥累計。
6. **持有者狀態**：持有者已倒下、已撤離、或處於 `skip_turn` 狀態時不觸發（`on_damaged` 造成持有者倒下的那一次也不觸發）。被沉默（`blocks_spells`）時 **不觸發**（被動都是法術技，決定 F）。
7. **另一方**：`target: other` 時，另一方必須還在場上（倒下的單位只有 `on_kill` 例外：效果仍可指向它，但傷害與狀態對倒下的單位無效，只有以它的位置為準的效果會生效——2E-1 的被動都不需要，保守處理並記錄）。
8. **事件**：觸發成功時發出新事件 `SkillTriggered`（持有者、技能、觸發時機、另一方、`trigger_depth`），接著是技能效果原本的事件。觸發的效果歸給持有者（`source_id` 是持有者），所以觸發造成的擊殺會再引起 `on_kill`（受深度與次數限制）。
9. **preview**：預覽動作時，觸發照實際規則結算（`preview` 與實際一致）；`trpg battle` 的預覽輸出要看得到觸發造成的傷害或狀態。

### 3.4 骨架 `passive`

`content/skeletons/passive.yaml` 改為 `enabled: true`：`kinds: [passive]`、`shapes: [self]`、核心原語 `damage`、`heal`、`shield`、`apply_status`（各自依 `trigger.target` 的對象檢查），`secondary.max_count: 1`。骨架 schema 新增 `min_rarity`（省略為 common；`passive` 為 `epic`，決定 H），由技能驗證檢查。

`trpg.skillgen.validate` 加上：
- `kind: passive` 必須有 `trigger`，且時機存在、`n` 只在 `every_n_hits` 出現且為 2 或 3、`target: other` 只用在 `has_other` 的時機、`max_per_round` 1–3。
- 技能稀有度 ≥ 觸發時機的 `min_rarity` 與骨架的 `min_rarity`。

### 3.5 預算

`trpg.skillgen.budget` 的可用預算：
- `kind: passive`：`tier_budget[tier] × 觸發時機的 budget_coefficient_permille`（`every_n_hits` 依 n 查表）。
- `max_per_round` 每多 1 次，可用預算 × 0.8（初值；寫在 `skill_budget.yaml` 的 `passive_extra_trigger_permille: 800`）。理由：次數越多，每次能分到的預算越少。
- 效果點數照既有算法；驗證區間照既有 70%–100%。
- `trpg skills budget --all` 要能計算被動技能，不再出現「尚無預算算法」。

### 3.6 手寫被動（`content/skills/`，數值為初值）

| ID | 名稱 | 觸發 | 效果 |
|---|---|---|---|
| `skill_ember_brand` | 餘燼烙印 | `on_hit`、`target: other` | 對被命中的單位施加 `burning` |
| `skill_second_wind` | 回氣 | `on_turn_start`、`target: self`、條件 `self_hp_below` 500‰ | 治療自己 |
| `skill_thorn_skin` | 荊棘之膚 | `on_damaged`、`target: other`、`max_distance: 1` | 對傷害來源造成小額物理傷害 |
| `skill_mark_detonation` | 標記引爆 | `on_hit`、`target: other`、條件 `target_has_status: marked` | 對被命中的單位造成暗影傷害 |

四個技能都要通過 `trpg skills budget --all`；若某個初值無法落在 70%–100%，調整骰值或法力到通過為止，並在報告記錄。本子階段 **不要** 把被動加進既有 build（會改動既有軌跡與矩陣）；build 在 2E-2、2E-3 新增。

### 3.7 組合器

`trpg.skillgen.random_composer` 能產生 `passive` 骨架的技能（`kind: passive`、隨機觸發時機與 `target`、`max_per_round` 1，稀有度 epic 以上）。骨架權重寫在 `content/skill_composer.yaml`（初值）。`scripts/skill_fuzz.py` 的執行驗收要涵蓋被動：把被動技能裝在測試單位身上打一場戰鬥，被動至少要有機會觸發（報告列出 1000 個中被動的數量與實際觸發過的數量）。

### 3.8 模擬報表

- 異常清單新增 `trigger_limit`（該場有 `TriggerLimitReached`），與既有 `chain_limit` 並列。
- `UnitMetrics` 新增 `triggers_fired`（觸發次數）；技能報表（`trpg sim skills`）對被動技能顯示觸發次數，不要求 DPR 有意義。

### 3.9 測試（情境測試，每項至少一個）

1. 每個觸發時機各一：`on_hit`、`on_crit`、`on_natural_20`、`on_kill`、`on_damaged`、`on_turn_start`、`on_turn_end`、`on_move`、`every_n_hits`（n=2 時第 2、4 次命中觸發，第 1、3 次不觸發）。
2. `max_per_round`：同一輪第二次命中不觸發，下一輪重設。
3. **觸發深度上限**：兩個單位都帶「`on_damaged` → 對來源造成傷害」且 `max_per_round: 3`（測試用技能資料）、相鄰互打：觸發最多到深度 3，之後發出 `TriggerLimitReached`，結算正常結束。
4. **不造成無限迴圈**（hypothesis）：隨機給雙方單位裝 0–2 個隨機被動（組合器產生），跑完整場戰鬥：無例外、每個 `SkillTriggered` 的深度 ≤ 3、戰鬥在 `max_actions` 內結束。
5. 沉默、暈眩、倒下的持有者不觸發；付不起法力時不觸發；冷卻中不觸發。
6. `condition` 照 `trigger.target` 判斷（`skill_mark_detonation` 對有標記與沒標記的目標）；`max_distance` 生效（`skill_thorn_skin` 對遠程攻擊者不觸發）。
7. preview：帶 `skill_ember_brand` 的單位攻擊時，預覽與實際結算（固定骰值）一致，且預覽中有燃燒。
8. 重播：帶被動的戰鬥 `--log-json` 後 `replay` 一致（測試裡做，不只手動）。
9. 驗證：缺 `trigger` 的被動、有 `trigger` 的主動、`target: other` 搭 `on_turn_start`、稀有度不足，都被拒絕。

### 3.10 驗收條件（2E-1）

1. `uv run python scripts/check.py` 五項全過。
2. 3.9 的測試全部存在且通過（報告列出測試名稱）。
3. `trpg skills budget --all` 全部通過（含 4 個被動）。
4. `uv run python scripts/skill_fuzz.py --count 1000` 無例外；報告列出被動數量與觸發過的數量。
5. 手動：`trpg battle` 用一個帶被動的單位跑一場（可以用 `--allies` 指定測試用範本，或在報告說明你用的方式）`--log-json` 再 `replay` 一致；報告附含 `SkillTriggered` 的紀錄節錄。
6. Phase 2 驗收 ⚠️ #1（觸發的資料檔）與 #11（觸發深度上限）在報告中逐條說明現在如何滿足。

---

## 4. Phase 2E-2｜反應技、擋攻擊、姿態

> PM 可能依 2E-1 報告修訂本節。

### 4.1 反應技（`kind: reaction`）

- `SkillDef` 新增 `reaction: ReactionSpec | None`（`kind: reaction` 必須有，其他不可有），欄位 `event`：
  - `hit_by_melee`：被近戰攻擊命中、傷害結算之後（持有者仍存活）
  - `hit_by_attack`：被任何攻擊命中、傷害結算之後
  - `ally_hit_adjacent`：與持有者相鄰（曼哈頓距離 1）的友方被攻擊命中、**傷害結算之前**（只給 `intercept` 用，見 4.2）
  - `enemy_leaves_adjacent`：同藉機攻擊
  - 「攻擊」包含普攻與技能的命中判定；範圍技能命中多個單位時，每個被命中的單位各自可以反應（仍受每輪次數限制）。
- 反應技接進既有的反應規則（`trpg.engine.reactions`）：`ReactionRule.reaction` 可以是內建反應（`reactions.yaml`）或持有者裝備的反應技 ID；`ReactionWhen.event` 擴充上述事件。單位裝備了反應技、而範本沒有為它寫規則時，自動加一條 `auto` 規則，**排在其他規則之前**。
- 反應技與內建反應 **共用** `reactions_per_round`（每輪 1 次）。
- 執行：反應技是「立刻施放一次技能」，不花 AP，照技能的 `cost` 付法力與冷卻；`shape: single` 時目標固定為觸發者（必須在技能射程內，並套用致盲的 `attack_range_cap`），`shape: self` 時目標為自己；照一般技能擲命中與抵抗。
- `mode: prompt` 的反應技照既有的 `pending`／`resume` 流程。
- 反應技的效果也帶 `trigger_depth`（反應本身 +1），所以「反擊 → 對方的被動 → ……」同樣受 `max_trigger_depth` 限制。
- 骨架 `reaction`：`enabled: true`、`min_rarity: rare`、形狀 `self`、`single`，核心原語 `damage`、`apply_status`、`push`、`pull`、`intercept`。預算係數用既有的 `reaction_coefficient_permille: 600`。

### 4.2 替隊友擋攻擊：原語 `intercept`

- 只能出現在 `reaction` 骨架、`event: ally_hit_adjacent` 的反應技；稀有度 rare；點數為初值。
- 效果：攻擊已經判定命中之後、傷害與其他效果結算之前，把這次攻擊對該友方的 **所有效果** 改為作用在守護者身上（不重擲命中；位移方向以攻擊者到守護者重新計算）。
- 只攔截 **單體** 攻擊（普攻與 `shape: single` 的技能）；範圍技能不攔截。
- 守護者的護盾、減傷、抗性照常結算；`shield_provided` 仍歸給該護盾最後一次的施加者（2D-2 規則不變）。
- 被攔截後，原目標的格擋不會觸發（它沒被打到）；守護者已經用掉本輪反應，所以也不會再格擋。
- 與嘲諷的關係：攔截不改變攻擊者的「攻擊目標」紀錄，也不施加或刷新任何嘲諷（2D-2 報告 9 節）。
- 多名守護者都可攔截時，依單位 ID 取第一個符合條件者；攔截後才輪到原目標的其他反應（此時已不適用）。
- preview：預覽攻擊時，攔截照實際規則分支（與格擋相同的作法）。

### 4.3 姿態（`kind: stance`）

- 姿態技能：`kind: stance`、`skeleton: stance`、`ap_cost: null`，進入時花 `core.yaml` 新增的 `stance_ap_cost: 1`；效果是對自己 `apply_status` 一個 **姿態狀態**。
- 狀態新欄位 `stance: true`：持續到取消（`expires: never`），帶有者同時最多一個 `stance` 狀態，施加新的會先移除舊的（`StatusRemoved` 原因 `replaced`）。倒下時移除。淨化（`cleanse`）不移除姿態。
- 新動作 `EndStance`：自己回合內免費取消目前姿態。
- 新增兩個姿態狀態與技能（初值，可用既有欄位組合，例如「狂怒：`attr_bonus` str +2、`damage_taken_permille` 1200」、「堅壁：`damage_reduction` 欄位、`move_permille` 500」；欄位名以 `statuses.yaml` 實際為準）。
- 骨架 `stance`：`enabled: true`、`min_rarity: rare`、形狀 `self`、核心 `apply_status`（必須是 `stance: true` 的狀態）。預算：可用預算 = `tier_budget × stance_coefficient_permille`（`skill_budget.yaml` 新增，初值 1000）；姿態狀態的點數寫在 `statuses.yaml` 的 `budget_points`。
- 效用 AI：沒有姿態時，把「進入姿態」當成一個合法動作，用 `ally_status_values`（或新權重）給分；已在同一姿態時不重複進入；不主動取消。

### 4.4 build

新增 `build_guardian`（守護者）：一個主動嘲諷或護盾技能、一個帶 `intercept` 的反應技（例如「挺身而出」）、一個防禦姿態、可以帶 2E-1 的 `skill_thorn_skin`。AI 行為模式沿用 `guard` 或 `support`（你決定並記錄）。另外新增一個手寫反擊反應技（例如「還擊」：`hit_by_melee` → 對觸發者武器傷害），放進 `build_guardian` 以外的一個新範本或測試用範本即可，**不改動既有 build**。

### 4.5 組合器、測試與驗收（2E-2）

- 組合器能產生 `reaction`（含 `intercept`）與 `stance` 技能；fuzz 涵蓋它們（報告列出數量）。
- 情境測試：反擊在近戰命中後觸發、遠程不觸發（`hit_by_melee`）；反應技與格擋共用每輪 1 次；致盲的守護者／反擊者受距離上限；`intercept` 改寫目標後守護者的護盾吸收、原目標毫髮無傷；範圍技能不被攔截；prompt 模式的反應技暫停與恢復；姿態進入花 1 AP、取代舊姿態、`EndStance`、倒下移除、淨化不移除；AI 會進入姿態；preview 含攔截與反擊；重播一致。
- 驗收：`check.py` 全過；上述測試存在且通過；`trpg skills budget --all` 全過；`skill_fuzz.py --count 1000` 無例外；`trpg battle --ally-build build_guardian` 跑一場 `--log-json`／`replay` 一致，報告附攔截的紀錄節錄。

---

## 5. Phase 2E-3｜層數、陷阱與收尾

> PM 可能依 2E-2 報告修訂本節。

### 5.1 層數

- 新資料檔 `content/stacks.yaml`：每種層數 `id`、`name_zh`、`owner`（`self`：累積在施放者身上；`target`：累積在被命中的目標身上，決定 B）、`max`（上限）、`expires_after_rounds`（可省略；`target` 型建議有，例如 3 輪沒有再累積就清空）。初始兩種：施放者型 `static_charge`（靜電，上限 5）與目標型 `sunder`（破甲印，上限 3、3 輪未刷新即清空）。
- `UnitState.stacks: dict[str, int]`（可序列化）；新事件 `StacksChanged`（單位、層數 ID、前後值、原因）。CLI 單位資訊顯示層數。
- 原語 `add_stack`（`stack`、`amount`）：依該層數的 `owner` 加在施放者或被命中的目標上，超過上限截斷。
- 原語 `consume_stack`（`stack`、`per_stack_permille`）：消耗 **全部** 該層數（施放者型從施放者扣、目標型從目標扣），同一技能中的傷害效果依消耗的層數 × `per_stack_permille` 加成（例如 200 → 每層 +20%）。沒有層數也可施放（加成 0）。
- 代價 `stacks`（`SkillCost` 新增，可省略）：施放前至少要有幾層（只對施放者型有意義），不足時不可施放、不在合法動作內。
- 預算：`add_stack`、`consume_stack` 的點數為初值；`consume_stack` 以「期望消耗 = 上限的一半」估算加成點數（寫在 `skill_budget.yaml` 並註明）。
- 骨架 `builder_finisher`：`enabled: true`、`min_rarity: rare`；技能必須含 `add_stack` 或 `consume_stack` 其中之一（核心仍是 `damage`）。
- 效用 AI：終結技的傷害評分要計入目前層數的加成；有層數時偏好終結技（用 `preview` 或同一公式，保持一致）。
- 手寫技能：靜電掌（＋靜電）、雷霆終結（消耗靜電）、破甲擊（＋破甲印）、碎甲重擊（消耗破甲印）。

### 5.2 陷阱

- 原語 `place_trap`：在目標格放一個陷阱；陷阱帶著 **同一技能其餘的效果**，觸發時以陷阱格為中心、照技能的 `trap.shape`（`single` 或 `cross`、`square3`）結算。技能新增欄位 `trap: {trigger: enter | delay, rounds: 2, shape: ...}`：`enter` 為敵人進入時觸發、`rounds` 輪後未觸發就消失；`delay` 為 `rounds` 輪後（放置者回合開始時）觸發。
- 戰鬥狀態新增陷阱清單（放置者、陣營、位置、技能、剩餘輪數；可序列化）。陷阱不是格子物件，不阻擋移動、不提供掩護；同一格只能有一個陷阱。
- **隱藏**（決定 D）：敵方的路徑規劃與 AI 評分不得讀取對方陣營的陷阱（實作上提供「依陣營過濾的可見陷阱」函式，AI 一律經過它）；CLI 文字網格顯示我方（玩家陣營）的陷阱。
- 觸發：敵方單位在主動或強制移動中 **進入** 陷阱格時立即觸發（與藉機攻擊同一個時點的機制）；觸發後陷阱移除。移動照常繼續，除非單位倒下或因效果無法再移動。陷阱的效果不擲命中（自動命中，同決定 F），狀態照常擲抵抗（施放者的屬性在 **放置時** 快照）。
- 陷阱觸發的效果帶 `trigger_depth`（+1）。新事件 `TrapPlaced`、`TrapTriggered`、`TrapExpired`。
- 骨架 `trap`：`enabled: true`、`min_rarity: rare`；形狀 `ground_tile`；核心 `damage`、`apply_status`、`create_surface`。預算：觸發不確定，可用預算 × `trap_coefficient_permille`（初值 800，寫在 `skill_budget.yaml`）。
- 效用 AI：會在敵人可能經過的格子放陷阱（評分可以簡單：距離最近敵人 1–3 步的格子），不要求聰明。
- 手寫技能：灰燼地雷（`delay` 2 輪、`cross` 火焰傷害＋火表面）、捕獸夾（`enter`、`single`、傷害＋`root`）。

### 5.3 build 與收尾（只在最後各跑一次全量）

1. 新增 `build_striker`（蓄力流：靜電掌、雷霆終結＋一個被動）與 `build_trapper`（陷阱流：兩個陷阱技能＋一個控場）。不改動既有 build。
2. 組合器開啟所有 2E 骨架；`skill_fuzz.py --count 1000`：無例外，報告列出各骨架數量（`passive`、`reaction`、`stance`、`builder_finisher`、`trap`）。
3. slow 測試全過。
4. `trpg sim completion --seeds 20 --jobs 2`：exception、max_actions、draw 皆為 0。
5. `trpg sim matrix --seeds 20 --jobs 2`：12 個 build 全量重跑，附報表；另附 `trigger_limit` 異常數。只記錄，不調平衡。

### 5.4 Phase 2E 驗收總表

報告最後附 `docs/專案計畫.md` 第 14 節 Phase 2E 驗收逐條（觸發深度上限〔技能層級〕、被動／反應／姿態／陷阱各有情境測試、觸發不造成無限迴圈、隨機 1,000 個技能〔含觸發類〕無例外、重播一致），以及 Phase 2 驗收 #1、#11 的最終狀態。

---

## 6. 報告格式（每個子階段一份：`docs/phases/Phase2E-N報告.md`）

1. 摘要（5 行內）
2. 交付項目與 commit 列表
3. 驗收結果（逐條，附測試名稱或指令輸出）
4. 設計與實作說明（只寫規格沒寫死、由你決定的部分）
5. 數據（fuzz、預算、模擬；有就寫）
6. 待 PM 決定（最多 10 點）
7. 附錄：代表性 CLI 輸出
8. 給下一個子階段的備註
