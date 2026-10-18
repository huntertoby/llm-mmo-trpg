# Phase 2C 計畫：模擬、戰術指令、地圖類型與平衡

> 撰寫：PM｜2026-10-18｜對應 `docs/專案計畫.md` 第 14 節 Phase 2 的最後一段（Phase 2 驗收的「模擬報表」「build × 地圖類型矩陣」「8 種地圖類型、10–15 張地圖」「戰術指令接口」都在這裡完成）
> 實作者請先讀：`CLAUDE.md`、`docs/phases/Phase2B-3報告.md` 第 6、7 節、`docs/design/06-技能.md` 6.8、`docs/design/05-戰鬥.md` 5.1（地圖類型表）與 5.9、5.9.1。

Phase 2C 拆成四個子階段，**各由一位實作者完成**，前一個經 PM 驗收後才開始依賴它的下一個：

| 子階段 | 內容 | 依賴 | 主要模組 |
|---|---|---|---|
| **2C-1｜批次模擬器與報表** | 兩項規則小改、批次模擬器、戰鬥指標、異常偵測、`trpg sim maps` | — | `trpg.sim`、`trpg.cli`、`content/` |
| **2C-2｜控制分派與戰術指令** | 每個單位／陣營不同的 policy、戰術指令 schema 與評分加成、腳本指揮官 | 2C-1 | `trpg.engine.ai`、`trpg.engine.runner`、`trpg.sim` |
| **2C-3｜地圖類型與 build 矩陣** | 地圖類型欄位、補齊 8 種地圖類型（共 10 張）、代表性 build、矩陣報表、分階標準敵人與技能報表 | 2C-1 | `content/maps`、`content/sim`、`trpg.sim` |
| **2C-4｜Phase 2 收尾** | （已改範圍）確保戰鬥都打得完、AI 環境權重、已知失敗測試、Phase 2 總驗收；平衡延後 | 2C-2、2C-3 | 見第 6 節 |

2C-2 與 2C-3 互不依賴，PM 可以用兩個 worktree 平行派工。**2C-4 已改為收尾（見第 6 節），下表標為「2C-4」的平衡項目一律延後到效果模板補齊之後。**

---

## 0. PM 決定（2B-3 報告「待 PM 決定」與累積待辦）

| # | 項目 | 決定 | 由誰實作 |
|---|---|---|---|
| 2B-3 #1 | 高階隨機技能強度未經戰鬥驗證 | 2C-3 建立分階標準敵人與技能報表（5.5），2C-4 依報表調整 | 2C-3、2C-4 |
| 2B-3 #2 | 代價折抵沒有總上限 | **加總上限 +500‰**（3.1） | 2C-1 |
| 2B-3 #3 | 結構型原語點數偏低 | 2C-3 的技能報表列出各骨架的強度分佈，2C-4 決定 | 2C-4 |
| 2B-3 #4 | 組合器抽選權重寫在程式碼 | **搬到 `content/skill_composer.yaml`**（3.1），數值不變 | 2C-1 |
| 2B-3 #5 | 預算比例偏上半段 | 接受 | — |
| 2B-3 #6 | 主題、協同、名稱暫定 | 接受，Phase 3 處理 | — |
| 2B-3 #7 | AI 很少用控場與位移技能 | 2C-1 報表列出使用率，2C-4 調權重 | 2C-4 |
| 2B-3 #8 | fuzz 先布置條件 | 接受 | — |
| 2B-3 #9 | 連鎖閃電維持原樣 | 接受 | — |
| 2B-3 #10 | `beneficial` 預設 `false` | 接受 | — |
| 累積 | 示範地圖勝率偏高、3 個 slow 平衡測試失敗 | 2C-4 | 2C-4 |
| 累積 | AI 權重全部未經模擬（狀態價值、mana、cooldown、exposed、heal） | 2C-4 | 2C-4 |
| 累積 | 示範技能數值（盾擊、處決、橫掃劈砍、火焰箭） | 2C-4 以報表評估 | 2C-4 |
| 累積 | 戰術指令接口（5.9.1） | 2C-2 | 2C-2 |

### 0.1 PM 決定（2C-1 報告「待 PM 決定」）

| # | 項目 | 決定 | 由誰實作 |
|---|---|---|---|
| 1 | 傷害只算實際扣掉的 HP、只算對敵人 | 接受 | — |
| 2 | 墜落、致命地形的傷害在指標層追溯來源，追溯不到算環境 | **引擎補上來源**：墜落、致命地形、爆炸、燃燒中物件造成的 `DamageDealt`（或對應事件）帶上能確定的 `source_id`（推擊者、打斷橋的人、點燃者），指標層改用事件上的來源；追溯不到才算環境。屬於第 1 節允許的最小引擎改動，既有測試與重播必須照常通過 | 2C-3 |
| 3 | `boss_burst` 門檻 50% 太敏感 | **改為 ≥ 60%** | 2C-3 |
| 4 | 控制回合接近 0 | 2C-4 | 2C-4 |
| 5 | 友軍誤傷另列、不計入 DPR | 接受 | — |
| 6 | 勝率分母只算完成的場次 | 接受 | — |
| 7 | 「從未使用」只涵蓋地圖單位的技能 | 接受 | — |
| 8 | 報表改為每張地圖一節 | 接受 | — |
| 9 | `--jobs > 1` 時 policy factory 必須可 pickle | 2C-2 的指揮官與 policy factory 用模組層級的類別，不用 lambda | 2C-2 |
| 10 | `MAX_ATTEMPTS` 等留在程式碼 | 接受 | — |

---

## 1. 範圍

**要做**：第 3–5 節（2C-1～2C-3）；第 6 節於 2C-4 開始前由 PM 補成正式規格。

**不要做**：
- LLM 指揮官、戰場描述的視野過濾、自然語言隊友指示（Phase 3／4）。2C-2 的指揮官只有確定性的 Python 腳本。
- 新原語、新形狀、新骨架的啟用（被動、反應、召喚……）。
- roguelite 流程、角色升級、屬性成長、裝備。
- 引擎規則的改動（除了 3.1 的預算上限屬於 `trpg.skillgen`）；若 2C-3 的地圖需要引擎支援才能表現某個特徵，採最小改動並寫進報告「待 PM 決定」。
- 前端。

---

## 2. 工作環境

- 在雲端工作區的 repo 內工作（路徑由 PM 派工時告知）；不要使用任何 `mcp__remote-devices__` 工具。
- 每個 shell 指令前 `export NO_PROXY=localhost no_proxy=localhost`；`uv sync`；`uv run python scripts/check.py` 五項全過。
- 不新增執行相依（`multiprocessing`、`concurrent.futures` 是標準函式庫，可以用）。
- git：在 `main`（或 PM 指定的 worktree 分支）上依邏輯分 commit，每個 commit 結尾帶兩行：

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NdQCBhJQhD7yNJCL9fewD4
```

- **不要 push**，由 PM 負責。遵守 `CLAUDE.md` 守則 11（節省 token）：批次模擬一律先用少量種子確認能跑，最後再跑規格要求的數量；不要為了「讓數字好看」反覆調數值——平衡是 2C-4 的事，2C-1～2C-3 只產出報表。
- 模擬器屬於 `trpg.sim`，引擎不得匯入它（守則 5）。批次模擬可以用多行程平行，但 **報表內容必須與 `--jobs` 數無關**（結果依種子排序後再彙總）。

---

## 3. Phase 2C-1｜批次模擬器與報表

### 3.1 兩項規則小改（先 commit）

1. **代價折抵總上限**：`content/skill_budget.yaml` 的 `allowance` 新增 `total_cap: 500`（‰）。冷卻、每場次數、法力、HP 的折抵各自先套用原本的上限，加總後再以 `total_cap` 截斷。`trpg skills budget` 的輸出要顯示截斷（例如「代價折抵 +650‰ → 上限 +500‰」）。
   - 示範技能若因此超出預算或比例跌出合格區間，列在報告中（附前後比例），**不要調整**技能數值，除非驗證器因此拒絕該技能——那種情況下以最小幅度調整（優先縮短冷卻、減少法力）並列出。
   - `skill_fuzz.py --count 1000` 仍須 1,000 個全部通過。
2. **組合器權重搬到 `content/skill_composer.yaml`**：`random_composer.py` 與 `composer_parts.py` 裡的抽選常數（稀有度權重、AP 權重、法術占比、武器技帶元素的比例、骰面、倍率表、後備次要原語、目標條件清單等，以實作者判斷「屬於調參而不是演算法」者為準）改由資料檔載入，以 pydantic schema 驗證，加入 `ContentLibrary`。**數值完全不變**：`skill_fuzz.py --count 1000` 的摘要必須與搬移前逐字相同（附 `cmp` 結果）。

### 3.2 批次模擬器 `trpg.sim.batch`

```python
@dataclass(frozen=True)
class BatchSpec:
    name: str  # 報表標題，例如 "swamp"
    setup: BattleSetup  # 沿用 build_setup；max_rounds 預設 30
    seeds: tuple[int, ...]
    policy_factory: Callable[[], Policy]  # 每場戰鬥新建一個 policy（避免跨場狀態）


def run_batch(spec: BatchSpec, *, jobs: int = 1) -> BatchReport: ...
def battle_metrics(run: BattleRun) -> BattleMetrics: ...  # 純函式，只讀 setup、事件與最終狀態
```

- 每場戰鬥的例外要被捕捉並記為異常（3.4），不中斷整批。
- `BatchReport` 可序列化成 JSON（pydantic），也能格式化成文字表格。
- `scripts/sim_demo_maps.py` 改為呼叫 `trpg.sim.batch` 的薄包裝（或刪除並更新 `tests/test_sim_scripts.py`），技能使用統計的收集邏輯搬進 `trpg.sim`。

### 3.3 指標定義

每場戰鬥（`BattleMetrics`）：

| 指標 | 定義 |
|---|---|
| 結果 | `ally`／`enemy`／`draw`（達到 `max_rounds`） |
| 輪數 | 戰鬥結束時的輪數 |
| 傷害 | 每個單位造成的傷害，分「直接」（`cause == "attack"`，含技能）與「間接」（爆炸、表面、墜落、致命地形、DoT 等其他 cause）；能追溯來源的間接傷害歸給來源單位，追溯不到的歸「環境」 |
| DPR | 單位造成的總傷害 ÷ 該單位存活的輪數（該輪開始時仍在場）。陣營 DPR＝陣營全體傷害 ÷ 輪數 |
| 承受傷害、治療量、擊倒數 | 每個單位 |
| 控制回合 | 單位在 **自己回合開始時** 帶有 stun／root／slow 的次數，分三欄；依 `StatusApplied.source_id` 歸給施加者（最後一次施加者），追溯不到歸「環境」 |
| 技能使用 | 每個技能：使用次數、擲骰次數、命中次數、直接傷害、治療量（沿用 `sim_demo_maps.py` 的歸屬規則） |
| 動作數 | 總動作數；每個單位平均每回合花掉的 AP（若能從事件或狀態取得；取不到就省略並寫進報告） |

整批彙總（`BatchReport`）：我方勝率、敵方勝率、平手率；輪數的平均、中位數、最小、最大；每個 **單位範本** 的平均 DPR、平均承受傷害、存活率；陣營平均 DPR；控制回合（每場平均，分陣營與狀態）；技能使用表（每場平均使用次數、命中率、平均直接傷害）；**從未被使用的技能**清單；異常清單。

### 3.4 異常偵測

每項都要列出種子，方便 `trpg battle --map … --seed …` 重現：

| 異常 | 判定 |
|---|---|
| `exception` | 戰鬥中拋出例外（記錄例外類型與最後一行訊息） |
| `max_actions` | 超過 `run_battle` 的 `max_actions` |
| `draw` | 達到 `max_rounds` 仍未分勝負 |
| `long_battle` | 輪數 > 10 |
| `chain_limit` | 出現 `ChainLimitReached` 事件（列出次數） |
| `boss_burst` | 帶 `boss` 標籤的單位在第 1 輪被擊倒，或單一動作對它造成 ≥ 50% 最大 HP 的傷害 |
| `one_shot` | 單一動作對非 boss 單位造成 ≥ 其最大 HP 的傷害（只計數，列出前 5 個種子） |

門檻寫成模組常數，報告中說明。

### 3.5 CLI

```
trpg sim maps [--maps a,b] [--seeds 20] [--seed-start 0] [--jobs N] [--json out.json]
```

- 預設跑全部帶 `encounter` 的地圖（測試地圖 `test_*` 除外）。
- 標準輸出只印摘要（每張地圖一節：勝率、輪數、陣營 DPR、單位範本表、控制回合、技能使用表、從未使用的技能、異常）；執行時間印在標準錯誤。兩次執行的標準輸出必須逐字相同；`--jobs 1` 與 `--jobs 4` 的輸出也必須相同。

### 3.6 驗收（2C-1）

1. `scripts/check.py` 五項全過。
2. 3.1-1：測試證明折抵加總被截斷在 +500‰；`trpg skills budget --all` 顯示截斷；報告列出受影響的示範技能（前後比例）。`skill_fuzz.py --count 1000` 1,000 個全部通過。
3. 3.1-2：`content/skill_composer.yaml` 有 schema 與載入測試；搬移前後 `skill_fuzz.py --count 1000` 的摘要 `cmp` 相同。
4. `battle_metrics` 有單元測試：用一場固定種子的小戰鬥（或手工事件序列），逐項核對傷害歸屬、DPR、控制回合、擊倒數。
5. 異常偵測有測試：每種異常至少一個能觸發它的情境（可以用手工事件序列或極端設定，例如 `max_rounds=1` 觸發 `draw`）。
6. 確定性：同一個 `BatchSpec` 跑兩次的 `BatchReport` 相等；`--jobs 1` 與 `--jobs 2` 相等（測試用 ≤ 4 個種子）。
7. 附上 `trpg sim maps --seeds 20` 的完整標準輸出（4 張示範地圖）與執行時間（`--jobs 1` 與 `--jobs 4` 各一次）。數字 **只列出、不調整**。

---

## 4. Phase 2C-2｜控制分派與戰術指令

> 對應 `docs/design/05-戰鬥.md` 5.9.1。本階段只做「效用 AI 接受指令」與「腳本指揮官」，LLM 指揮官在 Phase 3 接上同一個介面。

### 4.1 控制分派

`run_battle` 新增關鍵字參數：

```python
controllers: Mapping[UnitId | Team, Policy] | None = None
```

行動者的 policy 依序查：單位 ID → 陣營 → `policy` 參數。`replay` 不受影響（重播的是動作）。CLI `trpg battle` 不需要新參數以外的改動（見 4.5）。

### 4.2 戰術指令 schema（`trpg.engine.ai.orders`）

pydantic 模型，以 `kind` 區分：

| kind | 欄位 | 意義 |
|---|---|---|
| `focus_target` | `target: UnitId` | 集火指定敵人 |
| `hold_position` | `at: XY`、`radius: int`（0–3，預設 1） | 守在指定格子附近 |
| `retreat_to` | `at: XY` | 撤往指定格子 |
| `protect` | `ward: UnitId` | 保護指定友方 |
| `use_environment` | （無） | 優先利用環境（爆炸、推落、表面） |

- `OrderSet`：`team_orders: tuple[TacticalOrder, ...]`、`unit_orders: dict[UnitId, tuple[TacticalOrder, ...]]`（單位有自己的指令時 **完全取代** 陣營指令）；每種 `kind` 最多一個。
- `validate_order(state, team, order) -> str | None`：回傳無效原因（目標不存在或已倒下、目標不是敵人／友方、格子超出地圖或無法站立）。**無效指令直接忽略**，該單位的行為與沒有那條指令時完全相同。
- 指令 schema 不得包含任何數值、骰子或結果欄位（守則 3：LLM 只能提議）。

### 4.3 評分加成

加成數值放在 `content/ai_profiles.yaml` 新的 `orders:` 區塊（‰ 與權重，初值如下，未經模擬，2C-4 調整）：

| 指令 | 加成 |
|---|---|
| `focus_target` | 對目標的預覽收益（damage、kill、status、push、surface、expose）×1500‰；位置價值的 `approach` 改以「與目標的距離」計算 |
| `hold_position` | 位置價值加一項：`hold` 權重 20 ×（與 `at` 的距離 − `radius`，最小 0）扣分 |
| `retreat_to` | 位置價值加一項：`retreat` 權重 15 × 與 `at` 的距離扣分；`approach` 與 `threat` 權重視為 0 |
| `protect` | `protect` 的保護對象固定為 `ward`；`protect` 權重取 max(行為模式的值, 12) |
| `use_environment` | env_damage、env_kill、push、surface、expose 收益 ×2000‰ |

- 指令只改評分，不改合法動作；指令不可行時（例如目標打不到）AI 照常選其他正分動作。
- `UtilityAI` 新增 `orders` 來源（例如建構參數 `orders: Callable[[BattleState, UnitId], tuple[TacticalOrder, ...]]`，或 4.4 的包裝器直接注入；介面由實作者決定，寫進報告）。沒有指令時，分數與 2C-1 的結果 **完全相同**（以既有測試與一個「無指令 vs 舊版」逐動作比對的測試證明）。
- 效能：有指令時，每動作決策時間中位數增加不超過 10%（附 `scripts/bench_battle.py` 前後數據）。

### 4.4 指揮官與紀錄

```python
type Commander = Callable[[BattleState, Team], OrderSet | None]  # None ＝ 沿用上一個指令


class CommandedAI:  # 可當作 Policy
    def __init__(self, ai: UtilityAI, commanders: Mapping[Team, Commander]) -> None: ...

    order_log: list[OrderRecord]  # round、team、orders、ignored（無效指令與原因）
```

- **呼叫時機**：某陣營在每一輪的第一次決策時，以及該陣營看到的存活單位數（敵我任一方）自上次呼叫後有變化時。
- 腳本指揮官放在 `trpg.sim.commanders`（確定性、只讀狀態）：
  - `focus_lowest_hp`：集火 HP 最低的可見敵人。
  - `protect_weakest`：全隊保護 HP 比例最低的友方。
  - `hold_start`：每個單位守在自己的起始格（radius 1）。
  - `use_env`：全隊 `use_environment`。
- 戰鬥紀錄：`BattleLog` 新增 `orders: list[OrderRecord]`（預設空，舊紀錄仍可載入）。`trpg battle replay` 照常重播動作，不重新呼叫指揮官；重播結果與原戰鬥一致。

### 4.5 CLI

- `trpg battle --map X --seed N [--ally-commander id] [--enemy-commander id]`：文字戰鬥紀錄在每輪開頭印出新下達的指令（繁中，例如「敵方指令：集火 戰士」）。
- `trpg sim maps … [--ally-commander id] [--enemy-commander id]`。

### 4.6 驗收（2C-2）

1. `scripts/check.py` 五項全過；import-linter 仍通過（`trpg.engine` 不匯入 `trpg.sim`）。
2. 控制分派：測試證明單位 ID 優先於陣營、陣營優先於預設 policy。
3. 五種指令各有情境測試（固定狀態、固定種子），證明行為改變：
   - `focus_target`：沒有指令時攻擊 A，指令集火 B 時攻擊 B（B 可攻擊）。
   - `hold_position`：敵人很遠時，有指令的單位不離開 radius；沒有指令時會前進。
   - `retreat_to`：單位往指定格子移動而不是接近敵人。
   - `protect`：單位往 `ward` 靠近。
   - `use_environment`：在「直接攻擊與引爆油桶分數接近」的情境下改選引爆。
4. 無效指令（目標已倒下、格子在地圖外）被忽略並記入 `ignored`，行為與無指令完全相同。
5. 沒有指令時的分數與 2C-1 完全相同（逐動作比對測試）。
6. 指令寫入 `BattleLog`；`--log-json` → `replay` 一致；舊格式紀錄仍可載入。
7. 附上 `trpg sim maps --seeds 20` 在「無指揮官」與「敵方 `focus_lowest_hp`」兩種設定的勝率對照表（只列出）。
8. 效能數據（4.3）。

---

## 5. Phase 2C-3｜地圖類型與 build 矩陣

### 5.1 地圖類型欄位

- `MapDef` 新增 `archetype`：`bridge_chasm`、`oil_depot`、`swamp`、`ruined_heights`、`forest`、`corridor`、`open_plain`、`frozen_lake`、`test`（對應 `docs/design/05-戰鬥.md` 5.1 的 8 種類型）。必填；既有 6 張地圖補上（兩張 `test_*` 為 `test`）。
- 既有列出或顯示地圖的 CLI（例如 `trpg battle show`）顯示類型；沒有列表指令就新增 `trpg maps list`。

### 5.2 補齊地圖（共 10 張非測試地圖）

新增 4 張，每種缺少的類型各 1 張，依 5.1 地圖類型表的特徵設計；再新增 2 張任選類型的變體（不同類型），合計 10 張：

| 類型 | 必要特徵（至少） |
|---|---|
| `forest` 森林 | 大量草叢（`conceal`、`flammable`），視線破碎；適合潛行、火焰、伏擊 |
| `corridor` 狹窄走廊 | 牆壁形成 1–2 格寬的瓶頸，至少兩條通道；適合直線、範圍、坦克 |
| `open_plain` 開闊平原 | 物件 ≤ 4 個、高度變化小；適合單體爆發與機動 |
| `frozen_lake` 冰湖 | 大片 `ice` 表面，加上冰窟（致命地形或可破壞的薄冰）；適合位移與冰凍 |

- 冰窟優先用既有內容表現：`chasm` 類地形（可在 `terrain.yaml` 新增 `ice_hole`，屬性比照 `chasm`，顯示名稱不同）＋可破壞的 `thin_ice` 物件（比照木橋的 `over_chasm`、`breakable`，HP 低）。若既有引擎無法支援，依第 1 節「最小改動」處理。
- 每張地圖：`check_map` 通過（連通、公平、致命地形限量）、有 `encounter`（沿用既有敵人範本即可，敵人組成可以不同）、有繁中註解說明設計意圖（有利／不利的 build）。
- 地圖大小在 8×8～12×12 之間。
- 每張新地圖附 `trpg battle --map <id> --seed 0` 的開場網格與前兩輪紀錄節錄（報告附錄）。
- 勝率與輪數 **只列出**（`trpg sim maps --seeds 20`）。

### 5.3 代表性 build（`content/sim/builds.yaml`）

一個 build ＝ 一名英雄（屬性、HP、武器、行為模式、技能清單）。矩陣中的我方隊伍＝ **build 英雄 ＋ 2 名標準隊友**（`sim_companion_fighter`、`sim_companion_archer`：只有普通攻擊、沒有技能），敵方使用地圖的 `encounter.enemies`。

初始 6 個 build（技能從既有 23 個示範技能挑選，實作者可在同主題內調整，並在報告列出最終清單）：

| id | 主題 | 建議技能 |
|---|---|---|
| `build_push` | 位移流 | `skill_gale_kick`、`skill_grapple_arrow`、`skill_shield_bash`、`skill_blink` |
| `build_fire` | 火焰流 | `skill_fire_bolt`、`skill_cinder_burst`、`skill_ashen_oath`、`skill_fire_arrow` |
| `build_storm` | 雷電／水 | `skill_chain_lightning`、`skill_summon_tide`、`skill_frost_shackle` |
| `build_tank` | 坦克 | `skill_bone_crusher`、`skill_shield_bash`、`skill_stone_wall`、`skill_sanctuary` |
| `build_ranged` | 遠程 | `skill_piercing_shot`、`skill_high_ground_shot`、`skill_smoke_arrow` |
| `build_assassin` | 潛行刺殺 | `skill_vanish`、`skill_rending_strike`、`skill_execute`、`skill_smoke_arrow` |

- 英雄屬性與 HP 以既有英雄範本為基準（近戰比照戰士、法系比照法師、遠程比照弓手），讓 build 之間的差異主要來自技能。
- 若某個 build 的技能有屬性或武器需求，實作者選擇合理的範本並寫進報告。

### 5.4 build × 地圖類型矩陣

```
trpg sim matrix [--builds a,b] [--maps a,b] [--seeds 20] [--jobs N] [--json out.json]
```

- 每格（build, 地圖）：我方勝率、build 英雄的 DPR、build 英雄存活率、平均輪數。
- 每張地圖內依「勝率，平手比 build 英雄 DPR」排名；**前段＝前 2 名**（6 個 build 時）。地圖類型有 2 張地圖時，該類型的值取兩張的平均。
- 報表輸出：勝率矩陣、DPR 矩陣、排名矩陣，以及 6.8 兩條標準的檢查結果：
  1. 沒有任何 build 在所有地圖類型都排名前段；
  2. 每個 build 至少在一種地圖類型排名前段。
- 2C-3 **只產出並列出**，標準不通過不算 2C-3 失敗（由 2C-4 處理）。

### 5.5 分階標準敵人與技能報表

- 新增 5 個標準敵人範本 `std_enemy_t1`～`t5`（`content/units/`，標籤 `sim`）：屬性與防禦比照盜賊，沒有技能，行為模式 `brute`；HP ＝ 30 × `tier_budget[t]` ÷ `tier_budget[1]`，四捨五入（目前為 30、39、49、62、77）。
- `trpg sim skills [--demo] [--random N] [--seeds 10] [--jobs N]`：每個技能以 `skill_fuzz.battle_setup` 的施放者陣容，對上 3 名同階標準敵人跑 `--seeds` 場；輸出每個技能的施放者 DPR、勝率、平均輪數、技能使用率。
- 依階級彙總 DPR 的分佈（P5、P50、P95），標出 **DPR > 同階 P95 × 1.2** 的技能（6.8 的退回條件；這裡只標出、不退回），並依骨架彙總平均 DPR 與使用率（給 2B-3 #3 的結構型點數判斷用）。
- 附 `trpg sim skills --demo` 與 `--random 200` 的輸出。

### 5.6 驗收（2C-3）

1. `scripts/check.py` 五項全過。
2. `archetype` 必填、8 種類型都至少有 1 張地圖；非測試地圖共 10 張，全部通過 `check_map` 並有 `encounter`（測試列出所有地圖的類型與檢查結果）。
3. 每張地圖跑 `trpg sim maps --seeds 20` 沒有 `exception`、`max_actions` 異常。
4. `content/sim/builds.yaml` 有 schema 與載入測試；6 個 build 的技能都存在且通過預算驗證。
5. `trpg sim matrix` 確定性（兩次輸出相同、`--jobs` 無關）；附 `--seeds 20` 的完整輸出與執行時間。若單執行緒超過 15 分鐘，用 `--jobs` 並寫明使用的數量。
6. 矩陣的排名與兩條標準的檢查有單元測試（用手工的小矩陣）。
7. 標準敵人範本 HP 符合公式（測試直接從 `tier_budget` 計算比對）；附技能報表輸出。

---

## 6. Phase 2C-4｜Phase 2 收尾

> **本節原本的「平衡」大綱已作廢**（2026-10-18 使用者決定：先確定遊戲能 work，平衡等效果模板補齊後再做）。正式規格見 `docs/phases/Phase2C-4計畫.md`。

---

## 7. 報告格式

每個子階段完成後撰寫 `docs/phases/Phase2C-N報告.md`（N＝1～4）：

1. 摘要（5 行內）
2. 交付項目與 commit 列表
3. 驗收條件逐條結果（測試名稱或指令輸出為證）
4. 設計與實作說明（介面、資料格式、門檻常數）
5. 數據表（本子階段要求附上的模擬輸出；長輸出放附錄）
6. 待 PM 決定（最多 10 點）
7. 給下一個子階段的備註
8. 附錄：代表性的 CLI 輸出節錄
