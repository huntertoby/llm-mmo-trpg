# Phase 2B 計畫：預算與隨機組合器

> 撰寫：PM｜2026-10-18｜對應 `docs/專案計畫.md` 第 14 節 Phase 2 的第二段
> 實作者請先讀：`CLAUDE.md`、`docs/phases/Phase2A-2報告.md` 第 4、7 節、`docs/design/06-技能.md`（全部）、`docs/design/05-戰鬥.md` 第 5.4 節。

Phase 2B 拆成三個子階段，**各由一位實作者依序完成**（前一個經 PM 驗收後才開始下一個）：

| 子階段 | 內容 | 主要模組 |
|---|---|---|
| **2B-1｜新狀態與控制遞減** | 7 種新狀態、控制的抵抗判定、控制遞減、Boss 硬控轉換、AI 與預覽支援、示範技能 | `trpg.engine`、`content/statuses.yaml` |
| **2B-2｜預算與驗證器** | 預算計算、硬性上限與互斥表、骨架、稀有度限制；示範技能全部通過驗證 | `trpg.skillgen`、`content/` |
| **2B-3｜隨機組合器與 1,000 技能驗收** | 隨機組合器、執行驗收工具、分佈報表 | `trpg.skillgen`、`trpg.sim` |

**本文件第 0–2 節三個子階段共用；第 3 節是 2B-1，第 4 節是 2B-2，第 5 節是 2B-3。**

---

## 0. PM 決定（2A-2 報告「待 PM 決定」）

| # | 項目 | 決定 | 由誰實作 |
|---|---|---|---|
| 1 | 我方勝率偏高、敵人技能用得少 | 2C 統一調整（陣容、敵人技能、英雄法力）。2B 只列出勝率，不調整 | 2C |
| 2 | AI 效能餘裕小 | 接受。2B-1 的效能驗收維持中位數 ≤ 8 ms；若超過，先做 ①視線快取、②單體技能對同一目標的重複預覽合併，並在報告列出前後數據 | 2B-1（必要時） |
| 3 | 場地型技能少被使用 | 2C 的 build 矩陣再處理 | 2C |
| 4 | 條件語意 ①–⑤ | 全部接受（範圍技能的目標條件＝至少一個對象成立；效果層級看結算當下；只支援單一條件） | — |
| 5 | AI 權重未經模擬 | 2C 統一以模擬調整；2B 新增的權重同樣先給初值 | 2C |
| 6 | `exposed` 只算不對稱壓制 | 接受 | — |
| 7 | 友方站上有害表面的懲罰 | 接受 | — |
| 8 | 吊橋戰改用種子 6 | 接受 | — |
| 9 | `legal_actions_with_areas` | 接受為引擎對外 API | — |
| 10 | 示範內容數值 | 接受；2B-2 的預算驗證可能要求調整，見 4.8 | 2B-2 |

---

## 1. 範圍

**要做**：第 3–5 節列出的項目。

**不要做**：
- 被動、反應技、姿態的 **執行**（觸發時機系統）；`builder_finisher`、`trap`、`summon` 等需要新系統的骨架只定義資料、不啟用（4.5）。
- 新原語（`damage_over_time`、`delayed_damage`、`shield`、層數、召喚、改寫規則型、`buff_attr`……）。DoT 以狀態（bleed、poison）實現。
- 雙屬性縮放、專精加成、裝備連動、技能等級成長。
- 批次模擬器、DPR 報表、build × 地圖矩陣、地圖類型、平衡調整 → 2C。
- LLM、前端。

---

## 2. 工作環境

- 在雲端工作區的 repo 內工作（路徑由 PM 派工時告知）；不要使用任何 `mcp__remote-devices__` 工具。
- 每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`；`uv sync`；`uv run python scripts/check.py` 五項全過。
- 不新增執行相依。
- git：在 `main` 上依邏輯分 commit，每個 commit 結尾帶兩行：

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01TEkeBiT3th5ANVbeFLXNGb
```

- **不要 push**，由 PM 負責。遵守 `CLAUDE.md` 守則 11（節省 token）。
- 新增程式不要加 `noqa` 複雜度例外，改拆函式。

---

## 3. Phase 2B-1｜新狀態與控制遞減

### 3.1 新狀態（`content/statuses.yaml`）

| 狀態 | 預設持續 | 效果 | 抵抗屬性 `save_attr` | 控制類別 `control_group` |
|---|---|---|---|---|
| `slow` 緩速 | 2 | 移動點數 ×50%（無條件捨去） | `dex` | `movement` |
| `root` 定身 | 1 | 不能主動移動（強制位移照常） | `str` | `movement` |
| `stun` 暈眩 | 1 | 跳過整個回合：沒有 AP、移動點數與反應 | `con` | `hard` |
| `weaken` 虛弱 | 2 | 自己造成的攻擊傷害（`cause: attack`）×75% | `con` | — |
| `vulnerable` 易傷 | 2 | 受到的骰值傷害 ×125%（不含墜落、致命地形等百分比傷害） | `wil` | — |
| `bleed` 流血 | 3 | 回合開始受 1d4 `physical` 傷害 | — | — |
| `poison` 中毒 | 3 | 回合開始受 1d4 `poison` 傷害；受到的治療 ×50% | — | — |

- 全部 `expires: turn_end`、`stacking: refresh`（沿用現有語意）。
- 數值效果以資料欄位表示，不寫死在程式：`move_permille`、`skip_turn`、`damage_dealt_permille`、`damage_taken_permille`、`healing_received_permille`、`on_turn_start_damage`（已存在）。欄位名稱可調整，但要在 schema 驗證並寫進 `statuses.yaml` 開頭的註解。
- 暈眩：回合開始的處理（持續傷害、冷卻 −1、狀態倒數）照常，然後直接結束回合，發出新事件 `TurnSkipped`（單位、原因狀態）。暈眩中不能執行反應。
- 倍率可疊乘（虛弱的攻擊者打易傷的目標＝×75%×125%），以整數千分比計算、最後無條件捨去，最低傷害規則照舊。

### 3.2 抵抗判定（6.10）

- 帶 `save_attr` 的狀態由 **技能或動作** 施加時，對每個目標做一次對抗判定，沿用 `maneuvers.contest` 的比例公式：攻方用技能的 `scaling_attr`，守方用狀態的 `save_attr`。失敗則不施加，發出可辨識的事件（例如 `StatusResisted`）。
- 對敵方的效果仍要先命中（2A 規則）；命中後才擲抵抗。對友方或自己施加的狀態不擲抵抗。
- 表面、環境造成的狀態維持現有規則（不擲抵抗）。
- 沒有 `save_attr` 的狀態（bleed、poison、burning……）命中即施加。

### 3.3 控制遞減（6.6）

- 帶 `control_group` 的狀態成功施加後，在目標上記錄「該類別遞減到第 R＋2 輪結束」（R＝目前輪數；`core.yaml` 新增 `control_dr_rounds: 2`）。
- 遞減期間，同類別的抵抗判定中守方屬性值 ×150%（`control_dr_resist_permille: 1500`）。
- 記錄存在 `UnitState`，要能序列化、`clone` 要同步。

### 3.4 Boss 硬控轉換

- 帶 `boss` 標籤的單位被施加 `control_group: hard` 的狀態時，改為施加對照表中的狀態（`core.yaml`：`boss_control_conversion: {stun: slow}`），持續時間沿用原效果；事件要看得出發生了轉換。轉換後的狀態仍走抵抗判定與遞減。

### 3.5 引擎其他配合

- `legal_actions`：定身時不列出主動移動；暈眩的單位不會輪到行動（直接結束）。
- 移動點數、傷害、治療的計算點各只改一處（集中在 `rules/` 或 `effects/handlers.py`），不要散落多處判斷狀態 ID。
- `preview`：抵抗判定比照 `knock_prone`——是分歧點（`min` 視為抵抗成功、`max` 視為失敗），並顯示抵抗成功率。
- AI：`ai_profiles.yaml` 新增每種狀態的價值權重（初值由你定，2C 再調）；效用評分把「施加狀態的期望價值 × 成功率」算進去；被定身、緩速的單位能正常選動作。既有 AI 測試仍通過。

### 3.6 示範技能

新增 4 個（數值由你估，2B-2 會再驗預算）：

| 技能 | 結構 | 裝備者 |
|---|---|---|
| `skill_frost_shackle` 寒鎖 | 法術、單體、小量冰霜傷害 ＋ `root` | `hero_mage` |
| `skill_rending_strike` 放血斬 | 武器技、單體傷害 ＋ `bleed` | `hero_fighter` |
| `skill_shield_bash` 盾擊 | 武器技、近戰單體、小量傷害 ＋ `stun`，冷卻 ≥ 4 | `bandit_shieldbearer` |
| `skill_venom_cloud` 毒霧 | 法術、`square3`、`poison` ＋ `vulnerable` | 不裝備（測試用） |

欄位超過上限時，由你決定換下哪個技能並寫進報告。

### 3.7 2B-1 驗收條件

1. `uv run python scripts/check.py` 五項全過；2A 的驗收測試仍成立。
2. 每種新狀態至少一個測試驗證效果：緩速的移動點數、定身不能移動但可被推、暈眩跳過回合且不能反應、虛弱與易傷的倍率（含疊乘與最低傷害）、流血與中毒的回合開始傷害、中毒減半治療。
3. 抵抗判定：固定骰值時成功與失敗各一個測試；對友方施加不擲抵抗；表面造成的狀態不擲抵抗。
4. 控制遞減：同一目標在遞減期內第二次被定身時，守方屬性以 ×150% 計算（測試直接驗證修正值）；遞減期過後恢復；不同類別（`movement` 與 `hard`）互不影響。
5. Boss：對 `bandit_boss` 施加暈眩 → 變成緩速，事件標示轉換。
6. 固定骰值時，`preview` 對施加控制的技能預測與實際一致，且顯示抵抗成功率。
7. AI 情境測試：①敵方近戰單位被定身時不會嘗試移動，改用可用的遠程或技能動作（或防禦）；②英雄法師在敵方近戰逼近時對其使用寒鎖。
8. 確定性：重播與 hypothesis 隨機動作測試仍通過（含新狀態）。
9. 效能：四張示範地圖每動作中位數 ≤ 8 ms（報告附 2A-2 與 2B-1 對照）。
10. 報告附 `scripts/sim_demo_maps.py` 的勝率、平均輪數與技能使用表（只列出、不調整）。

---

## 4. Phase 2B-2｜預算與驗證器

> 實作者另外要讀：`docs/phases/Phase2B-1報告.md` 第 6、7 節。

### 4.0 2B-1 驗收後的 PM 決定（2B-2 一併實作）

| # | 項目 | 決定 |
|---|---|---|
| 1 | Boss 轉換只在技能路徑 | **改**：轉換搬進 `handlers.apply_status`，所有來源都轉換（抵抗判定仍只對技能與動作） |
| 2 | AI 狀態價值尺度 | 2C 以模擬調整 |
| 3 | 定身連站起也不行 | **改**：定身時仍可站起（站起不是移動格子），站起後不能移動；補一個測試 |
| 4 | 虛弱只算攻擊、易傷算所有骰值傷害 | 接受 |
| 5 | 轉換後持續沿用原效果 | 接受 |
| 6 | 遞減的記錄範圍 | 接受 |
| 7 | 同一技能兩個同類別控制時預覽不一致 | 以互斥規則排除：4.4 新增第 6 條 |
| 8 | 在自己回合內被暈眩 | 接受；反應技能與陷阱實作時再處理 |
| 9 | 示範技能數值 | 依 4.8 |
| 10 | 勝率變化 | 2C 處理 |

### 4.1 模組與依賴

- 預算計算與驗證放在 `trpg.skillgen`（例如 `skillgen/budget.py`、`skillgen/validate.py`），對外提供 `skill_budget(skill, library) -> BudgetReport` 與 `validate_skill(skill, library) -> list[Violation]`。
- `trpg.content` 不得匯入 `trpg.skillgen`（新增 import-linter 規則）。`trpg content check` 由 CLI 層呼叫驗證器，任何示範技能違規就失敗（中文訊息指出技能、規則與數值）。
- 計算用 `Fraction` 或整數千分比，不用浮點；報表顯示時再四捨五入。

### 4.2 預算公式（6.5）

```
效果點數    = base_points × 強度係數 × 形狀倍率 × 對象係數 × 效果條件倍率
raw         = Σ 效果點數
total       = raw × 技能條件倍率 × Π 協同係數
可用預算    = tier_budget[tier] × AP係數[ap_cost] × (1000 + 代價折抵‰) ÷ 1000
驗證        = 0.7 × 可用預算 ≤ total ≤ 1.0 × 可用預算
```

**基礎點數與強度係數**（`base_points` 加在 `skill_primitives.yaml`；狀態與表面的點數加在各自的資料檔，欄位名 `budget_points`）：

| 原語 | 點數 |
|---|---|
| `damage`（法術） | 骰子平均值（2d6 → 7） |
| `damage`（武器） | `multiplier_permille` ÷ 1000 × `budget_reference_weapon_damage`（`core.yaml`，初值 7） |
| `heal` | 骰子平均值 |
| `push`／`pull` | 2 × 距離 |
| `knock_prone` | 3 |
| `teleport` | 4 |
| `apply_status` | 狀態的 `budget_points` × 持續 ÷ 預設持續 |
| `create_surface` | 表面的 `budget_points` × 持續 ÷ 預設持續 |
| `destroy_object` | 2 |
| `create_obstacle` | 3 |
| `raise_terrain`／`lower_terrain` | 2 |

狀態 `budget_points` 初值：burning 3、concealed 3、prone 3、slow 3、root 4、stun 8、weaken 4、vulnerable 4、bleed 3、poison 3（`defending` 不可由技能施加，可省略）。表面初值：fire 3、poison 3、ice 3、oil 2、water 1、holy 4、darkness 2。

**形狀倍率**（`skill_shapes.yaml` 加欄位，可用「基礎值 ＋ 每單位參數加成」表示）：

| 形狀 | 倍率 |
|---|---|
| `self`、`single`、`ground_tile` | 1.0 |
| `line` | 0.8 ＋ 0.2 × size（line3 ＝ 1.4） |
| `cone` | size 2 ＝ 1.3、3 ＝ 1.6、4 ＝ 2.0 |
| `cross` | 1.8 |
| `square3` | 2.0 |
| `ring` | radius 1 ＝ 1.8、2 ＝ 2.2 |
| `chain` | 1.0 ＋ 0.25 × jumps（2 跳 ＝ 1.5） |
| `allies_in_radius` | 1.0 ＋ 0.4 × radius |

- 形狀倍率只套用在對象為 `enemies`／`allies`／`all`／`tiles` 的效果；`affects: self` 與 `teleport` 一律 1.0。
- **對象係數**：`affects: all`（敵我不分）＝ 0.8；其他 1.0。

**條件倍率**：無條件 1.0、`harshness: common` 0.85、`harsh` 0.6。技能層級的條件乘在 total，效果層級的條件只乘該效果。

**AP 係數**：1 AP 0.5、2 AP 1.0、3 AP 1.6；`reaction` 0.6（只計算，不生成）。

**代價折抵**（‰，加總後乘上去）：冷卻每回合 +50（上限 +300）；`uses_per_battle` 1 次 +400、2 次 +250、3 次以上 +100；法力每點 +5（上限 +150）；`hp_percent` 每 1‰ +1（上限 +200）。

**`tier_budget`**：放 `core.yaml`。初值由你用腳本校準——選一組隨階級遞增的整數，使現有示範技能 **不修改** 就落在合格區間的數量最多；報告列出校準過程的摘要表。

**協同係數**（`content/skill_synergies.yaml`）：依 **機制標籤** 查表。機制標籤由驗證器從技能內容推導，不由人填寫：

| 機制標籤 | 推導規則 |
|---|---|
| `damage` | 有 `damage` |
| `heal` | 有 `heal` |
| `area` | 形狀不是 `self`／`single`／`ground_tile` |
| `displace` | 有 `push`／`pull`／`teleport`／`knock_prone` |
| `control` | 施加帶 `control_group` 的狀態 |
| `debuff` | 施加 `weaken`／`vulnerable` |
| `dot` | 施加 `burning`／`bleed`／`poison` 或產生有持續傷害的表面 |
| `surface` | 有 `create_surface` |
| `terrain` | 有 `create_obstacle`／`destroy_object`／地形升降 |

初始協同表：`area + control` 1.2、`damage + debuff` 1.15、`area + displace` 1.1。一個技能同時符合多條時全部相乘。

### 4.3 硬性上限（6.6）

驗證器檢查並回報違規：

1. 效果 ≤ 4 個；推擊、拉扯 ≤ 2 格（2A 已在載入時檢查，驗證器重用即可）。
2. `category: rule_rewrite` 的原語 ≤ 1 個，且技能必須 `uses_per_battle: 1` 或冷卻 ≥ 4（目前沒有此類原語，用測試專用的假資料驗證規則）。
3. `weapon_req` 只能是大類（2A 已檢查）。

### 4.4 互斥規則表（`content/skill_exclusions.yaml`）

規則以資料表達（例如「如果符合 A，則不得符合 B」或「如果符合 A，則必須滿足 B」），驗證器通用處理，不為每條寫特例程式。初始規則：

| # | 規則 |
|---|---|
| 1 | 沒有冷卻的技能不得使用 `square3`、`allies_in_radius`、`ring` radius 2、`cone` size 4 |
| 2 | 施加 `stun` 的技能形狀只能是 `single`，且冷卻 ≥ 4 |
| 3 | 同一技能不得同時有 `push` 與 `pull` |
| 4 | `self` 形狀不得有對象為 `enemies` 的效果 |
| 5 | 同一技能不得同時有對敵方的 `damage` 與對友方的 `heal`（屬於不同骨架） |
| 6 | 同一技能不得施加兩個相同 `control_group` 的狀態 |

### 4.5 骨架（6.9，`content/skeletons/<id>.yaml`）

- 12 種骨架都要有資料檔：`id`、`name_zh`、`kinds`、`enabled`、允許的形狀、**核心效果**（允許的原語與最低點數占比 `min_core_share_permille`）、**附帶效果**（允許的原語與數量上限）、是否必須有條件。schema 用 pydantic 驗證。
- 2B 啟用 6 種：`strike`、`area`、`control`、`displace`、`aura`、`combo`。其餘 6 種（`builder_finisher`、`trap`、`summon`、`reaction`、`stance`、`passive`）`enabled: false`，驗證器拒絕使用它們的技能。
- 初始結構（可微調，但要寫進報告）：

| 骨架 | 形狀 | 核心 | 附帶 | 其他 |
|---|---|---|---|---|
| `strike` | `single` | `damage`，占比 ≥ 60% | ≤ 1 個任意有害原語 | — |
| `area` | `line`、`cone`、`cross`、`square3`、`ring`、`chain` | `damage`，占比 ≥ 50% | ≤ 2 個：`create_surface`、`apply_status`、`push`、`knock_prone`、`destroy_object` | — |
| `control` | 全部 | `apply_status`、`create_surface`、`create_obstacle`、地形升降（可多個） | `damage` 占比 ≤ 40% | — |
| `displace` | `single`、`ground_tile`、`line`、`cone` | `push`／`pull`／`teleport`／`knock_prone` | `damage` 占比 ≤ 50%；≤ 2 個附帶 | — |
| `aura` | `self`、`allies_in_radius`、`square3` | `heal`、有益狀態、有益表面（對象為友方或自己） | ≤ 1 個 | 不得有對敵方的效果 |
| `combo` | `single`、`line`、`cone`、`chain` | `damage`，占比 ≥ 50% | ≤ 1 個 | **必須有條件**（技能或效果層級） |

### 4.6 稀有度限制（6.12）

- `skill_primitives.yaml`（已有 `min_rarity`）、`skill_shapes.yaml`、`statuses.yaml`、`skill_conditions.yaml` 各加或沿用 `min_rarity`。技能的稀有度必須 ≥ 它用到的每一項的 `min_rarity`。
- 初值：

| 稀有度 | 可用 |
|---|---|
| `common` | 數值型原語（`damage`、`heal`、`apply_status`）；狀態限 burning、slow、weaken、vulnerable、bleed、poison；形狀 `self`、`single`、`line`、`cone`、`ring`、`allies_in_radius`；**沒有條件**；效果 ≤ 2 個 |
| `rare` | 以上 ＋ 結構型原語、全部形狀、全部狀態、條件；效果 ≤ 4 個 |
| `epic` | 同 rare（觸發與雙屬性縮放尚未實作） |
| `legendary` | 同 epic ＋ 最多 1 個改寫規則型原語（目前沒有） |

### 4.7 CLI

- `trpg skills budget <skill_id>`：印出預算明細（每個效果的點數與倍率、raw、條件、協同、total、可用預算與折抵、比例、是否合格）。
- `trpg skills budget --all`：一張表列出所有示範技能的 total ／ 可用 ／ 比例 ／ 違規。
- `trpg content check` 失敗時列出所有違規。

### 4.8 示範技能的調整

所有示範技能（含 2B-1 新增的 4 個）都必須通過驗證。校準 `tier_budget` 後仍不合格的，**只調整技能本身**（骰子、倍率、持續、代價、稀有度、骨架標記），不改公式與點數表；報告列出每個被調整的技能與前後數值。

### 4.9 2B-2 驗收條件

1. `uv run python scripts/check.py` 五項全過；`trpg content check` 通過；新的 import-linter 規則生效。
2. 預算計算的單元測試：至少 5 個手算案例（含武器技、法術技、`affects: all`、效果條件、技能條件、協同、代價折抵），與 `skill_budget` 的結果完全相等。
3. 超預算（> 1.0）與過弱（< 0.7）的技能被拒，訊息顯示比例。
4. 4.3 的每條上限、4.4 的每條互斥、4.5 的每種骨架結構違規、4.6 的每條稀有度限制，各至少一個「違規被拒」測試，以及一個「合格」測試。
5. 停用的骨架被拒。
6. 全部示範技能通過；`trpg skills budget --all` 的輸出附在報告。
7. 2B-1 的驗收測試仍通過（數值調整後若有情境測試失敗，修正測試的設定而不是放寬規則，並在報告說明）。
8. 4.0 #1：非技能來源（測試中直接排入 `ApplyStatusEffect`）對 Boss 施加暈眩 → 轉為緩速；#3：倒地＋定身的單位可以站起但不能移動。

---

## 5. Phase 2B-3｜隨機組合器與 1,000 技能驗收

> 實作者另外要讀：`docs/phases/Phase2B-2報告.md` 第 6、7 節。

### 5.1 隨機組合器（`trpg.skillgen.random_composer`）

`compose_random_skill(seed, *, tier=None, rarity=None, skeleton=None, category=None, ap_cost=None) -> SkillDef`

- 確定性：只用 `trpg.shared.rng.Rng(seed)`；相同參數必得相同技能（逐欄位相等）。
- 未指定的參數由 RNG 選取；只選 `enabled` 且 `kinds` 含 `active` 的骨架，且符合稀有度限制（例如 `combo` 需要條件 → 至少 `rare`）。
- 流程：骨架 → 形狀與參數 → 核心與附帶原語與參數（元素、狀態、表面從允許清單選）→ 條件（`rare` 以上 30% 機率；`combo` 必有）→ 代價（AP、法力、冷卻、每場次數）→ **調整強度**（骰子顆數與面數 {4,6,8,10,12}、武器倍率、狀態與表面持續）使比例落在 0.75–0.95 → 用 4.1 的 `validate_skill` 驗證。
- 失敗則用同一個 RNG 繼續重抽；每個種子最多 50 次，仍失敗則拋出例外（驗收要求 0 次）。
- 產出的技能：`id` 為 `skill_rand_<seed>`，`name_zh` 為暫定名稱（例如「火焰・範圍 #123」），`tags` ＝ 元素 ＋ 機制標籤，`provenance.origin: level_up`，`narrative` 填暫定文字。
- `category` 與 `weapon_req` 一致（武器技 `melee`／`ranged`，法術技 `focus`／`any`）。

### 5.2 執行驗收工具（`trpg.sim.skill_fuzz`，加腳本 `scripts/skill_fuzz.py`）

對每個隨機技能：

1. 在 `test_flat_6x6` 上建立戰鬥：施放者（依 `weapon_req` 給相容武器、法力充足）、1 名友方、2 名敵方；嘗試 3 種站位（相鄰、距離 3、距離 5），直到該技能出現在 `legal_actions`。
2. 對該技能的每個合法選取（最多 8 個）在 `clone` 上 `resolve`，不得拋出例外。
3. 每 10 個技能中挑 1 個，讓施放者裝備它，用 `UtilityAI` 跑完一場戰鬥（上限 20 輪），不得拋出例外。
4. 輸出摘要：可施放率、例外數、例外清單（種子、技能 YAML、traceback 第一行）、各骨架／稀有度／階級／形狀的數量分佈、預算比例的分佈（10 個區間）、平均重抽次數。

`skill_fuzz.py --count 1000 --seed-start 0` 跑完要在合理時間內（目標 ≤ 3 分鐘）。

### 5.3 測試

- 預設測試跑 100 個種子（快速）；1,000 個的版本標 `@pytest.mark.slow`。
- 組合器確定性測試；每種啟用的骨架、每種稀有度、每個階級至少能各產出一個技能（指定參數）。
- 組合器產出的技能存成 YAML 再載入，結果相同（可序列化）。

### 5.4 CLI

- `trpg skills random --seed N [--tier T] [--rarity R] [--skeleton S] [--count C]`：印出技能 YAML 與預算摘要。

### 5.5 2B-3 驗收條件

1. `uv run python scripts/check.py` 五項全過。
2. `scripts/skill_fuzz.py --count 1000`：**1,000 個全部通過驗證、全部可施放、0 個例外**；報告附摘要輸出。
3. 分佈：5 個階級、4 種稀有度、6 種啟用骨架都有出現；任何一種骨架不超過總數的 40%。
4. 確定性：同一種子重跑得到相同技能；`skill_fuzz` 兩次執行的摘要完全相同。
5. 抽 3 個隨機技能（不同骨架）在報告附 `trpg skills random` 的輸出與一小段戰鬥紀錄。
6. 2B-1、2B-2 的驗收測試仍通過。

---

## 6. 完成報告格式

`docs/phases/Phase2B-1報告.md`、`Phase2B-2報告.md`、`Phase2B-3報告.md`，格式同前：

1. 摘要（3–5 行）
2. 交付項目與 commit 列表
3. 驗收條件逐條結果（附測試名稱或指令輸出）
4. 設計與實作說明（模組結構、重要的取捨）
5. 數據表（依子階段：勝率與效能／預算表與校準／分佈摘要）
6. 待 PM 決定（依重要性排序，最多 10 點）
7. 給下一階段的備註
8. 附錄：代表性的 CLI 輸出節錄
