# Phase 2G 計畫：Phase 2 完整性檢查的補強

> 來源：2026-10-19 Phase 2 完整性檢查（設計 vs 實作比對）。11 點新發現中，使用者決定：C 類（文件）與 #1–#4 的記錄由 PM 直接處理；**#5 重複施加狀態取較長、#6 已定義但沒有技能使用的內容、#7 沒被裝備的手寫技能**在本階段實作。
> 目標：讓 Phase 3 試玩時，`content/` 裡定義的機制都真的出現在戰鬥中，並修正一條與設計文件不一致的規則。

## 0. PM 決定

| # | 項目 | 決定 |
|---|---|---|
| 1 | 拆段 | 2G-1：狀態重複施加規則（#5）＋ 裝備未使用技能（#7）＋ 覆蓋率測試；2G-2：示範技能（#6） |
| 2 | 重複施加狀態 | 依設計文件 6.6「不疊加，取最高值」：剩餘回合取**較長者**（`None`＝永久視為最長）；不疊加數值 |
| 3 | 軌跡 | 2G 會改變戰鬥軌跡（規則改變、build 技能改變），**不要求**對照戰鬥相同；但 `trpg battle --log-json` → `replay` 必須通過 |
| 4 | `LOG_FORMAT` | 事件 schema 若不變則不升版；若必須改事件欄位，升版並寫進報告 |
| 5 | 平衡 | 不調任何數值。新技能只要通過預算驗證（0.7–1.0）即可；DPR、勝率留給平衡階段 |
| 6 | 大型模擬 | completion、matrix 不跑，PM 驗收時自己跑 |

## 1. 範圍外

- 新原語、新狀態、新骨架、新觸發時機、新條件（只能用 `content/` 已有的 ID）。
- `summon` 骨架（維持停用）、`freeze` 狀態、`self_status` 代價、雙屬性縮放、專精加成（已記入 `docs/PM交接.md` 3.1.1，屬補模板 C）。
- 技能卡片描述移出 CLI（Phase 3-1）。
- 平衡數值、AI 權重。

## 2. 工作環境

- 在使用者的 Windows 電腦上執行（Git Bash，Linux 寫法）。
- 開發中只跑相關測試檔（`uv run pytest -q tests/<路徑> -x`）；commit 前只跑 `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy` 與相關測試；**完整的 `uv run python scripts/check.py` 只在子階段最後跑一次**（本機約 1 分鐘）。
- 每完成一個交付項目就 commit。不要 push。
- 修改既有測試的期望值時，報告逐一列出原因。

---

## 3. Phase 2G-1｜狀態重複施加 ＋ 技能覆蓋

### 3.1 重複施加狀態取較長（#5）

- 位置：`src/trpg/engine/effects/handlers.py` 套用狀態處（目前註解「只有 refresh：重複施加時以新的持續時間取代」）。
- 新規則：單位已有同 ID 狀態時，新的剩餘回合 ＝ max(舊剩餘, 新持續時間)；`None`（永久）視為最長。
  - 新持續時間 ≥ 舊剩餘時，`source_id` 改為新來源；否則保留舊來源。
  - 控制遞減（`control_dr`）的記錄與 Boss 硬控轉換維持原邏輯不變。
  - 姿態互斥（先移除其他姿態）不變。
  - `StatusApplied` 事件的 `duration` 填**生效後**的剩餘回合，`refreshed` 意義不變。
- 護盾已是取較大值，不動。
- 更新該處註解，指向設計文件 6.6。
- 測試（`tests/engine/` 合適的檔案）：
  - 已有 4 回合 `concealed`，再施加 2 回合 → 仍為 4（以 `skill_vanish` → `skill_blink` 或直接構造狀態皆可）。
  - 已有 1 回合，再施加 3 回合 → 變為 3，`source_id` 為新來源。
  - 永久狀態再施加有限回合 → 仍為永久。
  - 既有 `test_apply_refresh_and_remove_status` 若需改期望值，報告說明。

### 3.2 裝備未使用的手寫技能（#7）

以下 6 個手寫技能沒有任何單位或 build 裝備，所以從沒進過 AI 對戰（目標型層數 `sunder` 也因此沒進過模擬）：
`skill_armor_breaker`、`skill_sunder_strike`、`skill_fury_stance`、`skill_mark_detonation`、`skill_second_wind`、`skill_venom_cloud`。

- 把每個技能裝到至少一個 `content/sim/builds.yaml` 的 build 英雄或 `content/units/` 的單位上，依主題與武器相容性選擇（例如 `sunder` 系近戰、`mark_detonation` 搭術士的 `marked`）。
- 限制：每名英雄或單位的技能依設計 6.13 暫定欄位，**主動（含姿態）≤ 6、被動 ≤ 2、反應 ≤ 1**；技能的 `weapon_req` 必須和武器相容（載入時已檢查）。
- 可以改既有 build 的技能組，或新增 build；**新增 build 時要同步更新相關測試與文件中 build 數量（12）**，並在報告說明。優先改既有 build，盡量不新增。
- `content/sim/builds.yaml` 開頭註解若描述 build 數量或規則，同步更新。

### 3.3 內容覆蓋率測試（防止再發生）

新增 `tests/content/test_coverage.py`（名稱可調），以手寫技能（`content/skills/`）與裝備清單（builds ＋ units）為準，檢查：

1. 每個手寫技能至少被一個 build 英雄或單位裝備。
2. 每個 `enabled: true` 的骨架、每個觸發時機（`skill_triggers.yaml`）、每個反應事件（`SKILL_REACTION_EVENTS`）、每個條件（`skill_conditions.yaml`）、每個原語（`skill_primitives.yaml`）、每個可由技能施加的狀態、每個層數（`stacks.yaml`）至少被一個手寫技能使用。
3. 第 2 條用一份**明確的允許清單**（測試檔內的常數，附中文註解說明原因）列出目前尚未覆蓋的 ID；測試同時檢查允許清單裡的 ID 確實未被使用（避免清單過時）。
   - 狀態的範圍：只算「技能可施加」的狀態，排除引擎或環境專用的（例如 `defending`、`prone`、`burning` 若由其他途徑產生，依實際情況判斷，並在註解說明）。
   - 2G-1 結束時允許清單會包含 2G-2 要補的 ID；2G-2 結束時只應剩 `summon` 與確實無法以手寫技能示範的項目（逐項註解理由）。
- 報告列出 2G-1 結束時的允許清單。

### 3.4 驗收條件（2G-1）

1. 重複施加狀態取較長的 3 個新測試通過；`StatusApplied.duration` 為生效後的值（有斷言）。
2. 6 個技能都被裝備；覆蓋率測試第 1 條通過，且沒有任何允許清單繞過第 1 條。
3. 覆蓋率測試第 2、3 條通過，允許清單列在報告中。
4. 隨機挑一張地圖、一個種子，用含新裝備技能的 build 跑 `trpg battle --map <id> --seed <n> --ally-build <build> --log-json f`，再 `trpg battle replay f` 通過；報告附節錄（最好看得到新裝備技能被使用）。
5. `scripts/check.py` 全部通過；複雜度類 noqa 數量不增加。

---

## 4. Phase 2G-2｜示範技能（#6）

### 4.1 要補的內容

以 2G-1 的允許清單為準，目前已知沒有任何手寫技能使用：

| 類別 | ID |
|---|---|
| 骨架 | `combo` |
| 觸發時機 | `on_crit`、`on_natural_20`、`on_kill`、`on_turn_end`、`on_move`、`every_n_hits` |
| 反應事件 | `hit_by_attack`、`enemy_leaves_adjacent` |
| 條件 | `target_on_surface` |
| 狀態 | `weaken` |
| 原語 | `destroy_object`、`raise_terrain`、`lower_terrain` |

### 4.2 做法

- 新增手寫技能 YAML（`content/skills/`），一個技能可以同時覆蓋多個 ID（例如一個 `combo` 技能用 `target_on_surface` 條件）。預估約 8–11 個技能；**每個觸發時機至少一個被動**。
- 每個技能：有 `name_zh`、`narrative`（繁中）、合適的 `tags`；通過預算驗證（`trpg skills budget --all` 全部在 0.7–1.0）；遵守稀有度規則（被動 epic 等，依現有 schema）。
- 每個新技能都要被裝備（覆蓋率測試第 1 條），裝備限制同 3.2；可以把新技能分配到主題相符的既有 build 或敵方單位（敵方單位使用可讓 AI 對戰覆蓋到它們）。
- 縮減覆蓋率測試的允許清單：結束時只應剩 `summon` 與確實無法示範的項目（逐項註解理由；若有，寫進報告「待 PM 決定」）。
- 每個新技能至少一個行為測試（在 `tests/engine/` 或 `tests/content/`），證明它在戰鬥中會產生預期事件（例如 `on_kill` 被動在擊倒後觸發；`raise_terrain` 改變格子高度；`enemy_leaves_adjacent` 反應在敵人離開時觸發）。可以參數化。
- `scripts/skill_fuzz.py --count 1000` 異常仍為 0（組合器不應受影響）。

### 4.3 驗收條件（2G-2）

1. 4.1 表中每個 ID 都被至少一個手寫技能使用，覆蓋率測試允許清單只剩有註解理由的項目。
2. 所有新技能預算合格（附 `trpg skills budget --all` 中新技能的行）。
3. 每個新技能都被裝備，且有行為測試。
4. `trpg battle` ＋ `replay` 用含新技能的 build 跑一場通過，報告附節錄。
5. `skill_fuzz.py --count 1000` 異常 0；`scripts/check.py` 全部通過；複雜度類 noqa 不增加。

---

## 5. 報告格式（每段一份：`docs/phases/Phase2G-N報告.md`）

1. commit 列表。
2. 驗收逐條結果（測試名稱或指令輸出為證）。
3. 技能裝備變更表（技能 → build／單位）；2G-2 另附新技能一覽（ID、中文名、覆蓋的 ID、預算比例）。
4. 覆蓋率測試的允許清單（結束時）。
5. 修改過期望值的測試與原因。
6. 複雜度類 noqa 前後數量。
7. 待 PM 決定（最多 10 點）。
