# Phase QF-6 報告：後端小修合併段（佇列 (u)、(p)、(i)、(r)）

基準：main `7e0c34917`。分支 `worktree-agent-a439db38b729ca34e`，沒 push；交件前合併過 main 兩次：`d4004276c` 只多了 `docs/開發PM交接.md` 一行；`72aae4737` 帶進玩法 PM 補的 06 6.3「預算」例外（`46d25550b`）。規格：`docs/phases/PhaseQF-6計畫.md`。

**結論：四項都做完，442 招、78 場、census 都是 different=0。** seed 238 那題 slow 測試恢復通過。

(r) 換過一次做法。第一版改組合器（`fa613acc3`），和 06 6.3、AP-2 第 4 項的預支基本款衝突，已經 revert（`06ed6a0af`）。之後玩法 PM 選 A：改檢查，組合器照舊；現在的做法是 `6ddc15eca`（見 2.4）。

QF-5 的四個檔（`content/maps.py`、`api/schemas.py`、`api/routes/content.py`、`api/routes/workshop.py`）和 `client/` 都沒有碰。

## 1. 交付與 commit

| 項目 | commit | 內容 |
|---|---|---|
| (u) 被動技 `reaction` 篩選 id 存在檢查 | `213348695` | `content/library/ruleset.py`；新測試 `tests/content/test_trigger_reaction_ref_qf6.py` |
| (p) AI 便宜估計補閘門降傷 | `15ea50e43` | `engine/ai/utility/skill_estimate.py`；新測試 `tests/engine/test_skill_estimate_gate_qf6.py` |
| (i) 副手、元素中文名改讀資料 | `33a5e66aa`、`c42c51d55`（補 format） | `content/equipment.py`、`api/tuning/objects.py`、`api/tuning/diff.py`，以及傳名字的呼叫端（見 2.3）；新測試 `tests/content/test_name_tables_from_data_qf6.py` |
| (r) 第一版：組合器重抽（已撤） | `fa613acc3` → revert `06ed6a0af` | 和預支基本款衝突，轉玩法 |
| 合併 main | `d4004276c`、`72aae4737` | 第二次帶進 06 6.3「預算」例外 |
| (r) 預支基本款例外（玩法 PM 選 A） | `6ddc15eca` | `skillgen/budget.py`；`tests/skillgen/test_random_composer.py` 的預算窗；新測試 `tests/skillgen/test_borrow_basic_exempt_qf6.py` |
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

### 2.4 (r) 預支基本款例外（06 6.3「預算」，玩法 PM 選 A）

- 規則：「只有一個效果、預算 0 的技能不合法」，只有預支基本款例外。四項都符合才合法：唯一效果是 `borrow_ap`、主動技、0 AP、形狀自身。組合器照舊。
- `skillgen/budget.py` 新增 `borrow_basic(skill)`，判斷上面四項。
  - `BudgetReport.min_ratio`（過弱下限）原本對所有帶預支的技能都是 0，現在只有 `borrow_basic` 為真時才是 0。
  - 其他預算 0 的單效果技能照舊算過弱（`budget.weak`）。
- schema 原本就擋掉三種情形，所以「四項各缺一項」裡有三項本來就過不了：
  - 預支加其他效果：「borrow_ap 必須是技能唯一的效果」；
  - 不是主動技：「borrow_ap 只能用在主動技能」；
  - 不是 0 AP：「ap_cost 必須是 0」。
  - 所以實際上被收窄的只有一種：只有預支、但形狀不是自身。這種原本豁免過弱下限，現在會被擋下（目前內容和組合器都沒有這種技能）。
- slow 測試 `test_one_thousand_seeds_are_all_valid_and_spread_out` 的預算窗（0.75～0.95），同樣只對 `borrow_basic` 例外。
- **6 個種子都符合四項**（238、336、435、606、873、998）：都是只有 `borrow_ap`、active、0 AP、self，`min_ratio` 0，`validate_skill` 通過。新測試逐一驗證。
- 新測試 `test_borrow_basic_exempt_qf6.py`：
  - 四項都符合時通過；
  - 形狀不是自身時擋下（過弱）；
  - 唯一效果不是預支、預算 0（`leave_form`）時擋下（`budget.weak`）；
  - 不是主動技（被動、反應）擋下；不是 0 AP 擋下；預支加其他效果擋下（後三種是 schema 擋的）；
  - 6 個種子都是基本款。
- 原本的 `test_the_composer_makes_the_basic_borrow_skill` 照原樣通過（revert 之後就是原檔）。

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
| `run_pytest.py -q -m slow tests/skillgen/test_random_composer.py -k one_thousand` | **0**（1 passed；第一版與新版各跑過一次） |
| 新版 (r) 之後：ruff、format、lint-imports、`content check`、`classify.py --check` | 都是 0 |
| 新版 (r) 之後的相關測試（預支 4 檔、`test_budget`、閃現、提議、工坊、組合器、引擎預支等 15 檔，`-n 8`） | 0（295 passed） |
| 新版 (r) 之後的 `check.py --all`、slow parity＋cli | 開發 PM 排時段後再跑（QF-5 正在用全量的時段） |

## 4. 結果比對（基準 `7e0c34917`）

- 基準用 `git archive 7e0c34917 src content scripts config`。
- 腳本沿用 CR-1c 的 `compare78.py`、`budget.py`、`census_cmp.py`，放在暫存區，沒進 repo。

| 比對 | 結果 |
|---|---|
| 442 招逐招預算（`BudgetReport` repr＋`validate_skill`；新版 (r) `6ddc15eca` 之後） | 442 招，`cmp` 0（逐位相同）→ **different=0**。內容裡的 `skill_borrowed_beat` 是基本款，`min_ratio` 照舊是 0 |
| census 小樣本（`--seeds 4 --tiers 1,3 --rarities common,epic`，不看計時；新版 (r) 之後） | `cells=204 different=0 whole_equal=True` |
| 78 場（`compare78.py`；`format` 也比；在 `c42c51d55` 跑） | `battles=78 events=26741 different=0`；內嵌規則包差異 0。新版 (r) 只改 `skillgen/budget.py`，引擎不匯入 skillgen，所以沒有重跑 |

- 第一版 (r) 時 census 有 3 格不同，3 格都來自組合器改了那 6 個種子。revert 後與新版都回到 0。
- (p) 在 78 場沒有差異：現有內容沒有裝備授予的變形修正技，閘門表是空的，估計的乘數一律是 1。

## 5. 待 PM 決定

1. **(r) 已由玩法 PM 定 A，照做**：只有基本款豁免過弱下限。實際收窄的只有一種：只有預支、形狀不是自身的技能。這種原本豁免，現在擋下；目前內容和組合器都沒有。LLM 或工坊如果做出這種技能，會被判過弱。
2. **(p) 只乘在一般估計段**：敵人分數與物件分數乘閘門‰；支援分數、扣友方分數、場地型分數不乘（閘門只降傷害）。特殊估計（召喚、區域、衝撞、投擲、位移、地形）沒有接，因為它們的分數不是照傷害算。現有內容閘門表是空的，實際上沒有影響。屬於解讀類，照最保守的做法，記在這裡。
3. **(i) 只看有沒有問題的呼叫端沒傳名字**：`item_gen` 的兩處 `affix_slot_problems`、`world/resonance.py` 的 `loadout_problems` 只用結果是不是空的，沒傳副手名。真的拿這些訊息顯示時會寫副手 id。目前沒有路徑會把這些文字顯示出來。
4. 沒有新增 `# noqa`。沒有改 `docs/design/`、`config/`、`content/`、`client/`、`CLAUDE.md`。
