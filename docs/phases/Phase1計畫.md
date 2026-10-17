# Phase 1 計畫：格子戰鬥核心

> 撰寫：PM｜2026-10-17｜對應 `docs/專案計畫.md` 第 14 節 Phase 1
> 實作者請先讀：`CLAUDE.md`、`docs/phases/Phase0報告.md`（尤其「給下一階段的備註」）、`docs/專案計畫.md` 第 5 節全部與第 7.2–7.3 節。

Phase 1 拆成兩個子階段，**各由一位實作者完成**：

- **Phase 1A｜戰鬥核心**：狀態模型、地圖、單位、先攻、AP、移動、攻擊、判定、傷害、事件、效果佇列、勝負（全滅）、CLI 跑完一場戰鬥。
- **Phase 1B｜環境與戰術**：表面、物件與標籤互動、環境回合與預告、地圖事件、天氣、反應規則與暫停點、撤離與守點、部署、預覽、效用評分 AI。

1A 完成並經 PM 驗收後，才開始 1B。**本文件第 1–4 節兩個子階段共用，第 5 節是 1A，第 6 節是 1B。**

---

## 1. 範圍

**要做**：`docs/專案計畫.md` 第 5 節描述的戰鬥規則中，不依賴技能系統的部分。

**不要做**：
- 技能系統（原語解譯器、技能 JSON、預算、生成）→ Phase 2。Phase 1 只實作 **引擎內部需要的少數效果類型**（第 3.4 節），並把效果佇列設計成 Phase 2 能直接擴充。
- 裝備詞條、共鳴、印記、配點、升級 → Phase 2 之後。Phase 1 的單位直接由資料檔給定屬性與武器。
- LLM、文字輸入、FastAPI、前端、roguelite 循環。
- 8 種地圖類型的完整內容 → Phase 2。Phase 1 只做測試用地圖與 3 張示範地圖。

---

## 2. 工作環境

- 在雲端工作區 `/home/claude/LLM-MMO-TRPG` 內工作；不要使用任何 `mcp__remote-devices__` 工具。
- **PyPI 已可使用，但必須讓連線經過代理**：每個 shell 指令前加上 `export NO_PROXY=localhost no_proxy=localhost`（預設設定會讓 pypi.org 直連而 DNS 失敗）。
- 安裝與檢查：`uv sync`，然後 `uv run python scripts/check.py`（五項都必須通過，包括 hypothesis 與 lint-imports）。
- 需要新套件時先想清楚是否必要；Phase 1 原則上 **不新增執行相依**。若確有必要，寫進報告。
- git：在 `main` 上依邏輯分 commit；每個 commit 結尾必須帶這兩行：

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RbaPp5tHxS9WU3o79xe213
```

- 可能已設定 `origin` remote；**不要 push**，由 PM 負責。

---

## 3. 共用架構決定（1A 與 1B 都要遵守）

### 3.1 引擎 API

```python
start_battle(setup: BattleSetup, seed: int) -> BattleState
legal_actions(state: BattleState) -> list[Action]      # 目前行動者的所有合法動作
resolve(state: BattleState, action: Action) -> ResolveResult
resume(state: BattleState, decision: Decision) -> ResolveResult   # 1B
preview(state: BattleState, action: Action) -> Preview             # 1B
telegraph(state: BattleState) -> Telegraph                         # 1B：環境下一輪預告

ResolveResult = (state: BattleState, events: list[Event], pending: Pending | None)
```

- **純函式**：`resolve` 不得修改傳入的 `state`（要有測試）。內部可以複製後就地修改，對外只回傳新狀態。
- **亂數狀態存放在 `BattleState.rng_state`**，`resolve` 內部以 `Rng.from_state` 還原、結束時寫回。不得在引擎外傳入 `Rng`。
- **重播**：`start_battle(setup, seed)` 加上動作列表依序 `resolve`，必須得到逐位元相同的最終狀態與事件。
- `BattleState`、`Action`、`Event` 全部可序列化為 JSON 並完整往返（要有測試）。
- 不合法的動作 `resolve` 時拋出 `IllegalActionError`，訊息為繁體中文並說明原因（例如「AP 不足：需要 2，剩餘 1」）。

### 3.2 狀態模型建議

- 內容資料（地圖、物件、武器、單位範本）用 pydantic frozen model（已有 `trpg.content` 的慣例）。
- `BattleState` 可用 pydantic model 或 `dataclass(slots=True)` 加 pydantic `TypeAdapter`，由實作者決定，但 **Phase 2 的模擬器會跑數十萬場戰鬥**，請在報告中記錄「一場 10 回合示範戰鬥」的執行時間，作為之後最佳化的基準。
- 單位、物件以 ID 為鍵的字典存放；**任何迭代都依 ID 排序**。

### 3.3 事件

- 事件為 pydantic model 的 discriminated union（以 `type` 欄位區分），每個事件帶 `seq`（整場戰鬥遞增）與 `round`。
- 事件只描述 **發生了什麼**（例如 `attack_rolled`、`damage_dealt`、`unit_moved`、`object_destroyed`、`surface_changed`、`unit_fell`、`status_applied`、`turn_started`、`battle_ended`），不含任何顯示文字。
- 繁體中文的戰鬥紀錄文字由 `trpg.cli` 的渲染器產生，不放在引擎內。

### 3.4 效果佇列

依 `docs/專案計畫.md` 第 5.9 節：動作展開為效果，放入佇列逐一結算，每個效果產生事件，事件可觸發新效果入列。

- 佇列先入先出；同一時刻產生的多個效果依「來源單位 ID → 目標 ID → 格子座標」排序後入列。
- **連鎖深度 ≤ 3**：每個效果帶 `depth`，由事件觸發的效果 `depth + 1`，超過 3 的不入列並產生 `chain_limit_reached` 事件。
- Phase 1 只需要以下效果類型（Phase 2 會以原語解譯器擴充，請把效果類型做成可註冊的處理器表，不要寫成一大串 if/else）：
  - 1A：`damage`、`heal`、`move_unit`（強制位移）、`apply_status`、`remove_status`
  - 1B：`push`、`create_surface`、`damage_object`、`destroy_object`、`raise_terrain`、`lower_terrain`、`create_obstacle`、`spawn_unit`
- 測試可直接把效果放進佇列執行（提供內部 API，例如 `engine.effects.run_effects(state, effects)`），用來測試互動規則而不需要技能系統。

### 3.5 規則數值全部放進資料檔

所有可調整的數值放在 `content/rules/core.yaml`（以 pydantic schema 驗證），程式中不得寫死。至少包含：

| 鍵 | 預設值 | 說明 |
|---|---|---|
| `ap_per_turn` | 3 | 每回合 AP |
| `ap_carry_max` | 1 | 可保留到下回合的 AP |
| `hit_target` | 11 | `d20 + 命中修正 + 熟練 + 情境 ≥ 11` |
| `hit_slope` | 4 | 命中修正斜率 |
| `hit_mod_cap` | 8 | 命中修正上下限 ±8 |
| `proficiency` | 2 | 熟練加值 |
| `height_hit_bonus` | 2 | 高打低 +2、低打高 −2 |
| `basic_attack_attr_multiplier_permille` | 300 | 普攻的屬性倍率（0.3） |
| `fall_damage_permille_per_level` | 100 | 每層 10% 最大 HP |
| `fall_damage_cap_permille` | 300 | 單次墜落上限 30% |
| `deadly_terrain_elite_permille` | 300 | 精英與 Boss 落入致命地形受 30% 最大 HP |
| `element_mod_floor_permille` | 250 | 元素修正下限（總減傷上限 75%） |
| `defend_defense_bonus_permille` | 250 | 防禦動作：防禦值 +25% |
| `move_climb_extra_cost` | 1 | 爬升一層額外消耗 1 格移動 |

（1B 會再加入表面、反應、環境等數值。）

---

## 4. 共用規則細節

這些是 PM 對 `docs/專案計畫.md` 第 5 節的補充決定，計畫沒寫到的以此為準。

### 4.1 格子與移動

- **四方向** 移動（上下左右），距離一律用曼哈頓距離。
- 每格有 `height`（0–3）、`terrain`、`surface`、最多一個 `object`。
- 單位每回合有 `move_points`（等於速度，預設 5），移動不花 AP，可拆段使用（移動 → 攻擊 → 再移動）。
- 移動到相鄰格的成本：同高度 1；往上一層 `1 + move_climb_extra_cost`；往上兩層以上 **不可通行**（之後由攀爬、跳躍技能處理）。往下任意層成本 1，但 **往下 2 層以上** 觸發墜落傷害（落差 − 1 層計算，例如落差 3 層算 2 層）。
- 不可穿過敵方單位，可穿過友方單位但不能停在同一格；帶 `blocks_move` 的物件不可通行；`chasm` 地形不可主動進入。
- `Move` 動作給定 **完整路徑**（格子序列），引擎驗證每一步；另提供工具函式 `reachable_tiles(state, unit_id)` 與 `find_path(state, unit_id, dest)`（Dijkstra，同成本時依固定方向順序打破平手，確保確定性）。

### 4.2 視線

- 用 Bresenham 直線取攻擊者到目標之間經過的格子（不含兩端）。
- 被阻擋的條件：該格物件帶 `blocks_sight`，或該格高度 ≥ `max(攻擊者高度, 目標高度) + 1`。
- 1B 加入：`darkness` 表面阻擋穿越的視線；濃霧限制視線距離。

### 4.3 判定

依 `docs/專案計畫.md` 第 5.4 節：

```
命中修正 = clamp(round(hit_slope × log2(攻擊值 ÷ 防禦值)), −cap, +cap)
命中：d20 + 命中修正 + 熟練 + 情境 ≥ hit_target；自然 1 必定失手、自然 20 必定命中
```

- **不得在執行期使用浮點數 log2**。以整數比較實作：預先算好每個修正值 k 的比例門檻 `t_k = 2^((k − 0.5) / slope)`，存成整數（×10⁶）的對照表，用 `攻擊值 × 10⁶ ≥ 防禦值 × t_k` 判斷。對照表由一支腳本以 `fractions`／`decimal` 高精度產生，寫進 `content/rules/hit_table.yaml`，並有測試重新計算後比對。（`hit_slope` 或 `hit_mod_cap` 改變時要重新產生，報告中說明做法。）
- **攻擊值** ＝ 縮放屬性值 ＋ 武器攻擊加值；**防禦值** ＝ 敏捷 ＋ 護甲加值（＋防禦姿態加成）。
- **優勢／劣勢**：擲 2 顆 d20 取高／低；優勢與劣勢同時存在時互相抵消，**不疊加**。
- **暴擊**：自然 20（或落在武器暴擊範圍內）時，傷害骰的顆數加倍，固定值不加倍。
- **傷害**：`(武器骰 ＋ 武器固定值 ＋ 縮放屬性值 × 倍率) × 元素修正`，結果無條件捨去，最低 1（命中時）。元素修正見計畫 5.1.1；計算全程用整數千分比。
- **先攻**：`d20 + (敏捷 − 10) // 2`；同值依單位 ID 排序。每場戰鬥開始時擲一次。

### 4.4 回合流程

依計畫 5.2.1。補充：
- 回合開始：AP 回復為 `ap_per_turn + min(保留的 AP, ap_carry_max)`；移動點數回滿；持續效果結算；狀態持續回合在 **回合結束** 時 −1。
- 行動者以 `EndTurn` 結束回合。驅動迴圈（CLI、模擬器）在 `legal_actions` 只剩 `EndTurn` 時自動結束。
- 全員行動完為一輪；1B 在此執行環境回合。
- 倒下的單位（HP ≤ 0）立即移出先攻順序，留下 `unit_downed` 事件。Phase 1 沒有復活。

### 4.5 狀態（Phase 1 需要的）

| 狀態 | 效果 |
|---|---|
| `defending` | 防禦值 +25%，到自己下回合開始 |
| `prone`（倒地） | 站起來消耗一半移動點數（無條件進位）；近戰攻擊倒地者有優勢，遠程攻擊有劣勢 |
| `burning`（燃燒） | 回合開始受 1d6 火焰傷害，持續 2 回合；重複施加時刷新持續時間，不疊加 |
| `concealed`（隱蔽，1B） | 對其攻擊有劣勢；超過 2 格的遠程攻擊無法選為目標 |

狀態定義放在 `content/statuses.yaml`。

---

## 5. Phase 1A｜戰鬥核心

### 5.1 交付項目

1. **共用型別更新**（`trpg.shared.types`）：`Element` 改為 9 種（`physical, fire, ice, lightning, poison, wind, earth, holy, shadow`），新增 `ResistGroup`（`physical, elemental, nature, spirit`）與元素到分組的對照（計畫 5.1.1）；`Surface` 新增 `darkness`；中文名稱補齊（風、大地、黑暗）。`content/elements.yaml` 同步更新並加入 `resist_group` 欄位與驗證。
2. **內容資料與 schema**：
   - `content/rules/core.yaml`、`content/rules/hit_table.yaml`（含產生腳本 `scripts/gen_hit_table.py`）
   - `content/terrain.yaml`：至少 `stone`、`grass`、`dirt`、`chasm`（致命）、`lava`（致命）
   - `content/weapons.yaml`：至少 單手劍（相鄰，力量，1d8）、雙手劍（相鄰，力量，2d6）、匕首（相鄰，敏捷，1d4，暴擊 19–20）、弓（8 格，敏捷，1d8）、火焰法杖（5 格，智力，1d6，火焰）。欄位：`id`、`name_zh`、`range`、`dice`、`flat`、`attack_bonus`、`scaling_attr`、`element`、`crit_range`、`two_handed`
   - `content/units/`：單位範本，至少 `hero_fighter`、`hero_archer`、`hero_mage`、`bandit`、`bandit_archer`、`bandit_boss`（帶 `steadfast`、`elite` 標籤）。欄位：屬性 6 項、`max_hp`、`speed`、`armor_bonus`、`weapon`、`resist`（4 組千分比）、`element_mods`（個別元素弱點／抗性）、`tags`
   - `content/maps/`：地圖格式（見 5.2）與 2 張測試地圖（`test_flat_6x6`、`test_heights_8x8`）
3. **引擎**（`src/trpg/engine/`，模組劃分參考計畫 5.9）：狀態、`start_battle`、先攻、回合流程、AP 與移動、路徑、視線、`Attack`／`Defend`／`Move`／`EndTurn` 動作、判定與傷害、效果佇列（1A 的效果類型）、狀態、墜落、致命地形、事件、勝負（全滅）。
4. **CLI**：
   - `trpg map show <map_id>`：以文字網格印出地圖（高度、地形、物件、單位）
   - `trpg battle --map <map_id> --seed <n> [--rounds-max 30]`：雙方都由一個 **簡易 AI**（走向最近敵人並攻擊；Phase 1B 會換成效用 AI）自動進行，每輪印出戰場網格與繁體中文戰鬥紀錄，結束時印出勝方與統計
   - `trpg battle ... --log-json <path>`：輸出動作列表與事件 JSON
   - `trpg battle replay <path>`：讀取上述 JSON，以重播驗證最終狀態一致
5. **測試**：見 5.3。
6. **報告**：`docs/phases/Phase1A報告.md`（格式同 Phase 0 報告），含「一場示範戰鬥的執行時間」。

### 5.2 地圖檔格式

以 YAML 撰寫，讓人能直接閱讀與手改：

```yaml
id: test_heights_8x8
name_zh: 測試高台
size: [8, 8]
heights: |        # 每個字元一格，0–3
  00000000
  00111100
  00122100
  00122100
  00111100
  00000000
  00000000
  00000000
terrain: |        # 圖例見 legend
  ........
  ........
  ...xx...
  ........
  ........
  ........
  ........
  ........
legend:
  ".": stone
  "x": chasm
objects: []        # 1B 使用：[{ at: [3, 4], kind: oil_barrel }]
surfaces: []       # 1B 使用
start_zones:
  ally: [[0, 6], [1, 6], [0, 7], [1, 7]]
  enemy: [[6, 0], [7, 0], [6, 1], [7, 1]]
```

- 座標 `(x, y)`，x 向右、y 向下；`heights` 與 `terrain` 第 y 行第 x 個字元即該格。
- 載入時驗證：行數、每行長度、圖例完整、起始區在地圖內且不在不可站立的格子上、雙方起始區之間存在可通行路徑（連通性）。違反時拋出 `ContentError`。

### 5.3 1A 驗收條件

1. `uv run python scripts/check.py` 五項全過。
2. **確定性**：同一 setup、同一 seed、同一動作列表，兩次執行的最終狀態 JSON 與事件 JSON 完全相同；`trpg battle replay` 驗證通過；hypothesis 測試：隨機種子跑完整場簡易 AI 對戰，重播一致。
3. **純函式**：`resolve` 前後原狀態不變（序列化比對）。
4. **序列化**：`BattleState`、`Action`、`Event` JSON 往返相等。
5. **判定**：命中修正對照表與高精度計算一致；計畫 5.4 的命中率表（同級 60%、2 倍 80%、4 倍以上 95%、一半 40%、1/4 以下 20%）以窮舉 d20 的方式驗證成立；優劣勢抵消；自然 1／20；暴擊骰加倍。
6. **移動**：爬升成本、兩層以上不可上、往下 2 層以上的墜落傷害（10%／層、上限 30%）、不可穿過敵人、路徑確定性。
7. **致命地形**：一般單位被強制位移進 `chasm` 會死亡；帶 `elite` 的單位改受 30% 最大 HP 並移到最近的安全格（距離相同時依固定順序）。
8. **元素修正**：分組抗性與個別弱點的組合、75% 減傷上限。
9. **AP**：每回合 3 AP、保留上限 1、AP 不足時拒絕並給出中文原因。
10. **CLI**：`trpg battle --map test_heights_8x8 --seed 42` 能跑完一場並分出勝負；輸出可讀。
11. 不合法動作皆拋出 `IllegalActionError`，且 `legal_actions` 回傳的每個動作都能被 `resolve` 接受（property 測試）。

---

## 6. Phase 1B｜環境與戰術

> 1B 實作者請先讀 `docs/phases/Phase1A報告.md`，了解 1A 的實際架構與資料格式。

### 6.0 1A 驗收後的 PM 決定（1B 一併實作）

1A 報告「待 PM 決定」的處理結果：

| 項目 | 決定 |
|---|---|
| 防禦動作 1 AP、防禦中不可再防禦 | 接受 |
| 單位 HP 與屬性數值 | 暫時接受；戰鬥節奏於 Phase 2 以模擬調整（目標見下） |
| CLI 預設陣容、`--allies`／`--enemies` | 接受；1B 在地圖檔加入選用的 `encounter` 欄位作為預設陣容 |
| 岩漿不可主動進入 | 接受 |
| 墜落與致命地形傷害不套抗性、最低 1 | 接受 |
| 近戰不論高度差 | **改**：近戰攻擊的高度差必須 ≤ 1 層（長柄等射程 2 的武器同樣適用此限制）；`legal_actions` 與 AI 同步調整 |
| 倒地時 Move 自動先站起 | 接受 |
| 先攻平手 | **改**：先比敏捷值高者，仍相同再以戰鬥亂數決定（於開場一次決定並寫入事件）；不再依 ID 排序 |
| 輪數上限算平手 | 接受（僅 CLI／模擬器使用；有勝利條件的戰鬥由條件判定） |
| elite 判定與安全格排序 | 接受 |
| 視線不對稱 | **改**：視線必須對稱——A 能看到 B 若且唯若 B 能看到 A（例如兩個方向都畫線，兩者皆通才算可見），並加 property 測試 |
| `core.yaml` 新增鍵、`begin_battle`、`has_only_end_turn`、`Team`、狀態內嵌規則資料 | 接受 |

**戰鬥節奏目標**（供 1B 示範地圖與 Phase 2 調整參考，1B 不需達成）：一般遭遇 4–6 輪、Boss 戰 6–10 輪。


### 6.1 交付項目

1. **物件與標籤**：`content/objects.yaml`，至少 `wooden_bridge`（breakable、flammable、over_chasm）、`oil_barrel`（breakable、flammable、explosive、pushable）、`stone_pillar`（blocks_sight、blocks_move、breakable、高 HP）、`grass`（flammable、conceal）、`crate`（breakable、pushable、blocks_move）。物件有 HP、可被攻擊（`Attack` 可以物件為目標）。
2. **表面**：`content/surfaces.yaml`：oil、water、fire、ice、poison、holy、darkness，含持續回合與進入／回合開始效果（例如 ice：進入時 `d20 + 敏捷修正 ≥ 12`，失敗倒地；poison：回合開始 1d4 毒素傷害；holy：友方回合開始治療 1d4、`undead` 受 1d4 神聖傷害；darkness：阻擋視線、站在裡面獲得 `concealed`）。
3. **元素 × 標籤互動表**：`content/interactions.yaml`，實作計畫 5.1 互動表的 **全部** 規則，由資料驅動。
4. **技巧動作**：`Shove`（1 AP，推 1 格，比例公式對抗：攻方力量 vs 守方力量）、`Trip`（1 AP，倒地，攻方敏捷 vs 守方敏捷）、`Interact`（1 AP：推動 pushable 物件 1 格）。`steadfast` 推擊距離減半（無條件捨去）。
5. **環境回合**：每輪結束時依資料表結算——火表面蔓延到相鄰帶 `flammable` 的格子、著火的 flammable 物件下一輪摧毀、表面持續回合 −1。
6. **環境預告**：`telegraph(state)` 回傳下一次環境回合將發生的所有變化；**預告必須與實際一致**（以相同邏輯在狀態複本上模擬）。
7. **地圖事件**：地圖檔 `events` 欄位，支援 `spawn_units`（第 N 輪結束時在指定格產生單位）與 `terrain_change`（第 N 輪結束時改變指定格的高度、地形或表面）；提前一輪出現在 `telegraph` 中。
8. **天氣**：`content/weather.yaml`：clear、rain、fog、night（計畫 5.7 表格）；`BattleSetup` 指定天氣。
9. **反應規則與暫停點**：計畫 5.2.1。反應 `opportunity_attack`（敵人離開相鄰格）與 `block`（被攻擊命中後傷害 −50%，消耗 10 耐力；單位新增 `stamina` 資源，預設 30）；每輪 1 次反應。規則格式與預設規則照計畫範例；`mode: prompt` 的反應會讓 `resolve` 回傳 `pending`，以 `resume(state, decision)` 繼續；測試用一個 fixture 反應驗證暫停與恢復。
10. **勝利條件**：`eliminate`、`escape`（我方存活單位在 N 輪內全部抵達出口格即勝；抵達者離開戰場）、`defend`（守住指定格 N 輪；某輪結束時敵方單位站在守點格上即敗）。
11. **部署階段**：`BattleSetup` 可給定我方單位的起始位置；未給定時依起始區自動排列（確定性）。
12. **預覽**：`preview(state, action)` 回傳命中率（以 `Fraction` 精確計算，含優劣勢）、傷害範圍（最小／最大／期望）、影響的格子與單位、以及「若命中且傷害為最小值時 **確定** 會發生的連鎖」與「可能發生的連鎖」。
13. **效用評分 AI**：`engine.ai`，對每個 `legal_action` 跑 `preview` 評分取最高；平手依動作排序決定。`content/ai_profiles.yaml` 定義 4 種行為模式（莽夫、弓手、狡猾、守衛）的權重。CLI 改用此 AI。
14. **示範地圖** 3 張：`bridge_chasm`（吊橋深淵）、`oil_depot`（油庫）、`swamp`（沼澤），各 10×10 左右，展現對應的互動。
15. **報告**：`docs/phases/Phase1B報告.md`。

### 6.2 1B 驗收條件

1. `uv run python scripts/check.py` 五項全過；1A 的所有驗收條件仍成立。
2. 情境測試（皆以資料驅動、可在測試中直接建構小地圖）：
   - 火焰攻擊油桶 → 油桶摧毀並爆炸，3×3 範圍傷害，周圍 oil 表面著火
   - 打斷木橋 → 橋上單位墜落；一般單位死亡，Boss 受 30% 最大 HP 並移到安全格
   - 雷電命中站在水中的單位 → 沿相連 water 格擴散到其他單位
   - 冰霜命中 water → 變成 ice；單位進入 ice 時檢定，失敗倒地
   - 推擊 Boss 2 格 → 只移動 1 格（steadfast）
   - 墜落傷害不超過 30%
   - 火表面依規則蔓延，且 `telegraph` 的預告與實際環境回合結果完全一致
   - 風吹火表面蔓延、風吹散毒表面、神聖淨化毒表面、大地隆起與下陷改變高度
   - 連鎖深度超過 3 時停止並產生 `chain_limit_reached`
3. 反應規則自動觸發（藉機攻擊、格擋）；prompt 反應正確暫停並由 `resume` 恢復，恢復後重播仍一致。
4. 三種勝利條件正確判定，包含失敗條件。
5. **預覽一致性**：用一個測試專用的固定骰 Rng 狀態（或在測試中把 `rng_state` 設為已知會產生特定骰值的狀態），預覽中「最小傷害／確定連鎖」的預測與實際結算一致；預覽的命中率與窮舉計算相符。
6. 效用 AI：4 種行為模式在同一場景下做出不同且符合定位的選擇（各至少一個情境測試）。
7. `trpg battle --map oil_depot --seed 42` 等 3 張示範地圖都能跑完並分出勝負，戰鬥紀錄中可見對應的環境互動。

---

## 7. 完成報告格式

同 `docs/phases/Phase0計畫.md` 第 6 節，另加一節「效能基準」（示範戰鬥的回合數、動作數、總執行時間、每個 `resolve` 平均時間）。
