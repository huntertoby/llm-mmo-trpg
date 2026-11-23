# Phase QF-6 報告：後端小修合併段（佇列 (u)、(p)、(i)、(r)）

基準：main `7e0c34917`。分支 `worktree-agent-a439db38b729ca34e`，沒 push；交件前合併過 main（`d4004276c`，只多了 `docs/開發PM交接.md` 一行）。規格：`docs/phases/PhaseQF-6計畫.md`。

**結論：四項都做完。** 442 招逐招預算、78 場都是 different=0。census 有 3 格不同，3 格都來自 (r)（只把 (r) 的檔換回基準再跑一次，different=0）。seed 238 那題 slow 測試恢復通過。

QF-5 的四個檔（`content/maps.py`、`api/schemas.py`、`api/routes/content.py`、`api/routes/workshop.py`）和 `client/` 都沒有碰。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| (u) 被動技 `reaction` 篩選 id 存在檢查 | `213348695` | `content/library/ruleset.py`；新測試 `tests/content/test_trigger_reaction_ref_qf6.py` |
| (p) AI 便宜估計補閘門降傷 | `15ea50e43` | `engine/ai/utility/skill_estimate.py`；新測試 `tests/engine/test_skill_estimate_gate_qf6.py` |
| (i) 副手、元素中文名改讀資料 | `33a5e66aa`、`c42c51d55`（補 format） | `content/equipment.py`、`api/tuning/objects.py`、`api/tuning/diff.py`，以及傳名字的呼叫端（見 2.3）；新測試 `tests/content/test_name_tables_from_data_qf6.py` |
| (r) 組合器不組出零預算單一效果的光環 | `fa613acc3` | `skillgen/random_composer.py`；改測試 `tests/skillgen/test_borrow_offers_ap2.py` |
| 合併 main | `d4004276c` | |
| 報告 | 本 commit | |

## 2. 做法

### 2.1 (u) 被動技 `trigger.reaction` 存在檢查

- 新增 `_trigger_reaction_problems`，接在 `skill_reference_problems` 裡。載入內容庫、`Ruleset.with_skills`、技能驗證器共用這份檢查，複合技第二段與變奏也會經過。
- 合法的 id 有兩種，照引擎實際傳進來的 `AttackInfo.reaction`：
  - `reactions.yaml` 的反應 id：內建反應攻擊用的是 `picked.id`；
  - 反應技（`kind: reaction`）的技能 id：`skills/cast.py` 傳的是 `skill.id`（E4 待決 2）。
- 找不到時的訊息是「技能 〈技能 id〉 的 trigger.reaction：找不到反應 '〈id〉'」，技能 id 和找不到的 id 都寫出來。`with_skills` 外層還會再加「〈技能 id〉：」前綴。
- 現有內容沒有被動技用這個篩選，所以 `content check` 照樣通過。LLM 與組合器的開放沒有做（等 E6）。
- 測試：找不到的 id 會報錯；`opportunity_attack` 和 `skill_riposte` 都接受；拿主動技的 id 會報錯。

### 2.2 (p) 便宜估計乘閘門‰

- 在 `skill_estimate` 的一般估計段，敵人分數（`enemy_points`）和可破壞物件分數（1）乘上 `reshape_damage_permille(state, unit, skill) / 1000`。
- 閘門資料只有一份：用的是結算時 `damage_permille` 呼叫的同一個函式，查的是規則包的 `reshape_gates`，沒有另外算一套。
- 沒有裝備授予變形時，這個值是 1000‰，乘 1 之後分數和改前逐位相同。現有內容的閘門表是空的，所以 78 場 different=0（見第 4 節）。
- 召喚、區域、衝撞、位移等特殊估計段沒有改。這些分數不是照命中人數算傷害；複合技也不會變形。
- 測試用 E5 的 `gear_library()`（`BOUNCE` 套在 `STRIKE`，閘門 841‰）：
  - 每個打敵人的選取，估計都比「同局面、閘門改成 1000‰」的低；
  - 沒裝備時兩邊相同。

### 2.3 (i) 去掉 `_OFFHAND_ZH`、`_ELEMENT_ZH`

- **副手**：`_affix_slot_problems` 多一個 `offhand_names` 參數（副手 id → `name_zh`，查不到時寫 id），名字由呼叫端傳進來：
  - `item_problems`：用已經有的 `offhands` 參數算。
  - `affix_slot_problems`：加選填參數。`item_gen` 的兩個呼叫端只看有沒有問題、不看文字，所以沒改。
  - `loadout_problems`：加選填參數 `offhand_names`。src 裡會把文字給人看的呼叫端都傳規則包的 `gear_names`（武器＋副手的 `name_zh`，載入時就有）：`engine/battle.py`、`api/gear.py`、`roguelite/gear.py`、`roguelite/start.py`、`world/opening_reselect.py`。
  - 載入檢查的 `_GearCatalog` 多一個 `offhand_names` 欄位，由 `load.py` 用 `offhands.yaml` 填。
  - `world/resonance.py` 只看有沒有問題，沒改。
- **元素**：`api/tuning/objects.py` 新增 `element_names(content_dir)`，讀 `elements.yaml` 的 `name_zh`，有快取，寫法和 `primitive_names` 一樣。
  - `concrete_fields` 多一個選填參數 `elements`。會顯示標籤的兩個呼叫端（`objects.py` 的物件詳情、`diff.py` 的改動標籤）傳進去。
  - 其他三個呼叫端（`check.py`、`skills.py`、`writeback.py`）只取路徑、丟掉標籤，沒改。
- `chosen`（進入形態時選的元素）不在 `elements.yaml`，留一個常數 `_CHOSEN_ZH = "所選元素"`，用 `forms.CHOSEN` 判斷。
- **文字不變**：
  - 新測試把拿掉的兩張表原封不動抄進測試，比對資料讀出來的名字一字不差；
  - 形態標籤 10 種元素（含 `chosen`）逐一驗過；
  - 限定副手的詞條掛錯副手時，訊息照舊寫「只能出現在塔盾上」這種中文名。
- CLI 快照：slow 的 `tests/cli` 全過，差異 0。

### 2.4 (r) 組合器重抽零預算單一效果的光環

- 新增 `_no_zero_budget_aura`：骨架是 `aura`、只有一個效果、`skill_budget(...).total == 0` 時拋 `Retry`，交給既有的重抽迴圈（`search.composer_attempts`）。檢查規則沒有放寬。
- 接在 `_attempt` 的兩個出口：預支基本款那條，以及一般流程。一般流程已經過了預算窗（比例至少 0.75），實際上不會碰到。
- **1000 個種子（`compose_random_skill(seed)`）和基準比，變了 6 個：238、336、435、606、873、998。** 6 個原本都是只有 `borrow_ap` 的光環（預算 0、比例 0）；其他 994 個逐位相同。
  - seed 238 現在是「淨化＋回復資源」的光環，比例 301/360（約 0.836）。
- 既有測試 `test_the_composer_makes_the_basic_borrow_skill`（AP-2 第 4 項：「組合器做得出基本款」）跟這項直接衝突。改成 `test_the_composer_no_longer_makes_the_zero_budget_borrow_aura`：rare 光環 400 個種子都不會是只有預支的技能，而且都合法。見待 PM 決定 1。

## 3. 檢查與結束碼

| 檢查 | 結束碼 |
|---|---|
| `uv run ruff check`（改到的檔） | 0 |
| `uv run ruff format --check .` | 0（3245 files；第 1 次 `check.py --all` 擋下 `api/gear.py` 沒排版，補 `c42c51d55`） |
| `uv run mypy`（改到的檔；`check.py` 內全量） | 0 |
| `uv run lint-imports` | 0（14 kept） |
| `uv run trpg content check` | 0 |
| `uv run python scripts/hardcoded/classify.py --check` | 0（沒歸類 0） |
| 開發中相關測試（各項的新測試，加上 E4 篩選、E5 閘門與直線、裝備、物品生成、工坊 tuning、組合器、預支） | 0 |
| `uv run python scripts/check.py --all` 第 1 次 | 1（只有 ruff format 失敗：`api/gear.py`） |
| `uv run python scripts/check.py --all` 第 2 次（`c42c51d55` 之後） | **0**：pytest 18720 passed、8 skipped；client 421 檔、4978 項；已寫通過戳記 |
| `run_pytest.py -q -m slow tests/skillgen/test_refactor_parity.py tests/cli -n 8` | **0**（995 passed） |
| `run_pytest.py -q -m slow tests/skillgen/test_random_composer.py -k one_thousand` | **0**（1 passed） |

## 4. 結果比對（基準 `7e0c34917`）

- 基準用 `git archive 7e0c34917 src content scripts config`，新版是全部程式 commit 之後的 worktree（`c42c51d55`）。
- 腳本沿用 CR-1c 的 `compare78.py`、`budget.py`、`census_cmp.py`，放在暫存區，沒進 repo。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`） | 442 招，`cmp` 0（逐位相同）→ **different=0** |
| 78 場（`compare78.py`；`format` 也比） | `battles=78 events=26741 different=0`；內嵌規則包差異 0 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時） | `cells=204 different=3`；兩邊結束碼 0 |

**census 的 3 格差異（全部來自 (r)）：**

1. `- / active / 1 階 / epic`：`top_designs` 裡原本的「光環・自身・只有 borrow_ap（physical）」，換成「光環・allies_in_radius・apply_status:shielded_charged（poison）」。格子狀態仍是 thin，計數不變。
2. `- / active / 3 階 / epic`：原本的「光環・自身・只有 borrow_ap（wind）」，換成「光環・square3・shield（physical）」。狀態仍是 thin。
3. `summon / active / 1 階 / epic`：`diag.keyword_hit` 5 → 6。重抽後的技能帶到召喚關鍵字；狀態、legal、designs 不變。

**來源確認**：把 HEAD 的 `src` 只換回基準的 `random_composer.py` 再跑 census，和基準比是 `cells=204 different=0 whole_equal=True`。所以 3 格都是 (r) 造成的，(u)、(p)、(i) 不影響 census。

(p) 在 78 場沒有差異：現有內容沒有裝備授予的變形修正技，閘門表是空的，估計的乘數一律是 1。

## 5. 待 PM 決定

1. **（規則類，請 PM 確認）(r) 等於讓組合器不再做預支基本款。** 只有預支一個效果的基本款（06 6.3：0 AP、冷卻 2、自身、預支 1）預算本來就是 0。照規格「組合器不組出只有零預算單一效果的光環」去做，組合器的預支基本款就做不出來了。
   - 和既有的 AP-2 第 4 項「組合器的獨立串流做得出來」直接衝突，所以原測試改成相反的斷言。
   - 內容裡的預支技能 `skill_borrowed_beat` 不受影響；LLM 題目照舊可以用預支當核心（`test_llm_topics_can_take_borrow_as_the_core` 照過）。
   - 抽中預支的那個獨立串流（`composer.borrow_core`，`skill_composer.yaml` 的 `borrow_core_permille: 50`、`borrow_cooldown: 2`）還在，但抽中後一定重抽，等於沒有作用。照規格不改 `config`／`content` 既有的值。
   - 如果玩法要保留組合器的預支，另一種做法是讓基本款多帶一個有預算的效果，或者改 slow 測試的預算窗（讓預支例外）。後者等於放寬檢查規則，規格不允許，所以沒做。
2. **(p) 只乘在一般估計段**：敵人分數與物件分數乘閘門‰；支援分數、扣友方分數、場地型分數不乘（閘門只降傷害）。特殊估計（召喚、區域、衝撞、投擲、位移、地形）沒有接，因為它們的分數不是照傷害算。現有內容閘門表是空的，實際上沒有影響。屬於解讀類，照最保守的做法，記在這裡。
3. **(i) 只看有沒有問題的呼叫端沒傳名字**：`item_gen` 的兩處 `affix_slot_problems`、`world/resonance.py` 的 `loadout_problems` 只用結果是不是空的，沒傳副手名。真的拿這些訊息顯示時會寫副手 id。目前沒有路徑會把這些文字顯示出來。
4. 沒有新增 `# noqa`。沒有改 `docs/design/`、`config/`、`content/`、`client/`、`CLAUDE.md`。
