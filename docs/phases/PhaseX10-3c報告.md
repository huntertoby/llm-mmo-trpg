# Phase X10-3c 報告：×10 漏換（姿態進入代價）與註解

依據：`docs/phases/PhaseX10-3c計畫.md`、`PhaseX10-3a報告.md`（待決 3、6 與開發 PM 裁定）、`PhaseX10-2b報告.md`（parity 重產程序）。
基準：開工時 `git merge main`（`ca9429fac`）。分支 `worktree-agent-a03579e4d681be8cf`，沒 push。
沒改 `docs/design/`、`config/`；沒碰 X10-3b 的檔（`api/skill_cards.py`、`narrative/skills.py`、`client/`、CLI 快照）；CLI 快照沒有變，沒重產。沒跑全量、沒用 `-m ""`、沒試數值。

## 1. 交付與 commit

| # | 項目 | commit |
|---|---|---|
| 1 | 姿態進入代價的法力、耐力步距與下限 × `quantity_scale`；模板文字；parity 重產 | `8236d320c` |
| 2 | docstring、YAML 註解的舊單位說法（只改文字） | `85d05df93` |

## 2. 第 1 項：姿態進入代價

### 程式
`skillgen/flash_ops.py` `_entry_cost` 多收 `library`，一格用 `CoreRules.cost_floor(field)`（X10-2b 已有：法力、耐力 1 × `quantity_scale`，其他 1）：
- `step` −1：值 − 一格，低於一格（10）就不出；
- `step` +1：值 + 一格；
- 冷卻照舊一格 1、最少 1；AP 照舊不動（姿態進入 AP 固定）。

三個呼叫點都改了：`_form_cost_drafts`（變身姿態的輕巧／蓄力）、`_op_stance_enter_light`（俐落）、`_op_stance_enter_heavy`（沉勢）。

### 文字（`content/flash_templates.yaml`）
- `stance_enter_light`：「進入姿態的冷卻 −1，或法力、耐力 −10（冷卻最少留 1，法力、耐力最少留 10；維持費不變，效果不變）」（寫法比照 X10-3a 的 `cost_light`）。
- `stance_enter_heavy`：「進入姿態的法力或耐力 +10」。
- 兩條上方的註解同步。

### 同類掃描（`skillgen/flash_*.py` 全部 13 檔）
找法力、耐力相關的 `±1`、`max(1,…)`、寫死費用：
- `flash_major.py` 的寫死候選費用：全部已經走 `scaled_cost`（X10-2b）。
- `flash_ops._light_cost_drafts`、`flash_trade`：已經用 `cost_floor`（X10-2b）。
- `flash_ops` 以血支付：已經留 1 × scale（X10-2a）。
- 其他 `± 1` 都是冷卻、回合、格數、層數、AP、預支 AP、維持費、修正幅度：不變類。
- **沒有其他漏換**，只有 `_entry_cost` 這一處。

### 回歸測試
- `test_flash_bal10b.py::test_enter_light_cuts_mana_or_stamina_but_keeps_one`（mana、stamina 兩組）：先斷言 scale 是 10，再驗：
  - 30 → 20（一次減 10）；
  - 10 和 19 都不出（減一格會低於 10）；
  - 實際閃現後值是 20；卡片顯示的費用和資料一致（法力看實付 `mana_cost`）。
- 原本這個測試寫的是舊單位（3 → 2、1 不出），是規格裡的行為改變，所以改測試，不是放寬。
- `test_flash_bal19e.py::test_enter_heavy_raises_the_entry_cost_and_the_stance`：進入代價的增加量從 +1 改成 + scale（10）。
- `tests/test_x10_texts.py::test_flash_cost_texts`：加上兩條模板文字和倍率的比對。

### parity 夾具（`tests/skillgen/fixtures/refactor_3wr2.json`）
**預測（重產前寫下）**：
- complete、retier：不變。它們不走閃現模板。
- flash：只有取樣到的**姿態**、而且題目裡有 `stance_enter_*` 的鍵會變。取樣的 41 招裡姿態有 2 招（`skill_form_elemental`、`skill_st_unbroken_will`），共 6 鍵。用新程式列出每題的模板，只有 `skill_st_unbroken_will@5@2` 的第 1、3 題有沉勢（第 2 題沒有）。預測：只變這一鍵的第 1、3 段。

**意外發現：main 上本來就有 31 鍵不過**。
- 在 `ca9429fac`（沒有我的改動）跑 `-m slow test_refactor_parity.py -k flash`：31 failed。
- 原因：X10-3a（`5d885e618`）改了 `cost_light`、`cost_blood` 的 `summary_zh`，但沒重產 parity。題目 JSON 含模板說明，所以題目裡有輕巧或以血支付的鍵都會變。X10-3a 報告寫「parity 沒變」，但它交件時只跑了 `-m slow tests/cli`，沒跑 parity。
- 驗證：在 `ca9429fac` 把 `flash_templates.yaml` 換回 `5d885e618` 之前的版本，flash 125 個全過。所以這 31 鍵只是那兩句文字造成的。

**只看我的程式改動**：
- 用舊文字加我的 `flash_ops.py` 跑 parity：只有 `skill_st_unbroken_will@5@2` 失敗。
- complete 406、retier 406 全過。和預測一致。

**重產後逐鍵核對**（舊夾具 vs 新夾具，`uv run python -m tests.skillgen.test_refactor_parity`）：
- complete 0／406 變、retier 0／406 變；flash 鍵數 123 → 123（沒有增減）。
- flash 共 32 鍵變：
  - `skill_st_unbroken_will@5@2`：變的是第 1、3 段，**和預測完全一致**。抽查題目：基礎法力 0，沉勢候選的法力是 10。舊程式在這裡是 1。
  - 其他 31 鍵：和 main 上本來就失敗的 31 鍵逐一相同，都是 X10-3a 文字造成的。

重產順便修好了 main 上 parity 的 31 鍵。

## 3. 第 2 項：註解與 docstring（只改文字）

| 檔案 | 舊 | 新 |
|---|---|---|
| `engine/events/rules.py` `DeathCheated` | HP 留在 1；多擋下的部分 ＋ 1 | HP 留在 1 × `quantity_scale`（10）；＋ 留下的 HP（程式 `_hp_floor` ＝ scale） |
| `skillgen/complete.py` 模組說明 | 每項最少留 1 | 最少留一格（法力、耐力 1 × scale，其他 1；`cost_floor`） |
| `skillgen/flash_ops.py` 模組表、`_op_light`、`_entry_cost`、俐落、沉勢 | −1／+1、最少留 1 | 減一格／加一格（法力、耐力 1 × scale） |
| `skillgen/flash_trade.py` | 最少留 1 | 最少留一格（`cost_floor`） |
| `content/world_encounters.py` `ArmorMod` | 護甲 −1／+1 | −10／+10（設計文件 18、19 已是 10） |
| `content/environment.py` `mana_points` | 每回復 1 點法力 | 每回復 1 × scale（10）點（程式 `scoring.py` 已 ÷ scale） |
| `content/rules.py` 屬性常駐數值 | 每高於基準 4 點 | 40 點 |
| `roguelite/start.py` | 體質 10 | 體質 100 |
| `api/world_party_view.py`、`api/world_schemas.py`（欄位 docstring，不進 OpenAPI） | 開場 HP 30 | 開場 HP 300 |
| `rules/core.yaml` | 14＝1 階…；(敏捷 − 10) // 2；體質 10、(體質 − 10)；(屬性 − 10) // 2 | 140／180／220；(敏捷 − 100) // 20；體質 100；(屬性 − 100) // 20（和 divisor 20 一致） |
| `units/training_dummy_moving.yaml`、`world/newcomer.yaml` | HP 300 | HP 3000（`max_hp: 3000`） |
| `item_gen.yaml` 單位價 | 屬性 +1、最大 HP +4 | +10、+40（`per` 已是 10、40） |
| `roguelite.yaml` | 耐力 40／30／20、法力 20／20／40 | 400／300／200、200／200／400 |
| `world/resonance.yaml` | 最大 HP +8 | +80 |
| `stacks.yaml` 雷電反噬 | 最多留 1 HP | HP 最少留 10 |
| `ai_profiles.yaml` `mana_points` | 每回復 1 點法力 | 10 點 |
| `world/encounters/ashen_waste.yaml`、`world/events/ashen_waste.yaml` | +1、−1、合計 −3～+1 | +10、−10、−30～+10（`armor_mods` 已是 10） |
| `skills/skill_lava_splash.yaml` | 引用 BAL-21 建議「法力 6」 | 「法力 6〔舊單位，現為 60〕」（保留原引用） |

### 看過、不改的
- 冷卻、回合、AP、層數、點數的「最少 1」「保留 1 點」：不變類（`skill_rules.py` 293、`flash_cost.py` 9、`roguelite/auto.py` 15、`tuning_fields.yaml` 224 等）。
- `core.yaml`「最大 HP …（至少 1）」、`rules.py` 707 `max(1, …)`：和程式一致，是「活著」的下限（比照 X10-2b 3.4 的 revive）。
- `skill_budget.yaml`「耐力 20 點 ＝ 法力 10 點」：說的是比例，兩種單位都對；「基準傷害 7」是預算內部點數，沒動。
- 單位檔裡「HP 31 → 19」「90 → 120」這類歷史紀錄：保留原話。
- `narrative/events.py`、`skill_rules.py`、`options.py` 裡的「1」：是程式輸出的字串，不是註解，見待決 1、2。

## 4. 不變比對

- **做法**：
  - 基準：`git archive ca9429fac src content`，用 `PYTHONPATH` 指向基準的 `src`、`TRPG_CONTENT_DIR` 指向基準的 `content`。有確認每個 worker 載入的 `trpg` 來自基準那份程式。
  - 目前：`85d05df93`（兩項都做完）。
- **範圍**：同 X10-2a～3a 的 78 場：
  - 15 張正式地圖 × 種子 1、7；
  - `open_plain` 種子 3 × 8 個 build；
  - 4 張頭目圖 × 種子 3～12。
- **比對內容**：`--log-json` 整份，排除 `ruleset_hash`；文字輸出排除寫入路徑那行。
- 結果：**`battles=78 events=26446 different=0`**。事件總數和 X10-3a 相同。
- `ruleset_hash` 也沒變。閃現模板不進戰鬥規則包，改註解也不影響 `model_dump`。

## 5. 檢查（最後一個程式 commit `85d05df93`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy`（1735 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| 不變比對 78 場 | different=0 |
| 分目錄 `pytest -n 8`（預設標記） | 全部 0：api 1336（1 skipped）、bot 67、cli 148、content 3166、engine 5120、llm 495、narrative 475、roguelite 279、server 77、shared 72、sim 180、skillgen 4634（7 skipped）、world 1328、頂層 198 |
| `pytest -n 8 -m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（979 passed） |

第 1 項 commit 前另外跑過：skillgen 和 `test_x10_texts`（4642 passed），slow parity 加 cli（979），一般 cli（148），都是 0。第 2 項 commit 前跑過 ruff、format、mypy、lint-imports、content check，以及 OpenAPI 快照、`test_x10_caps`、`test_rewrites`、`test_events_text`、`test_x10_scale`、`test_ashen_waste`、`test_x10_texts`（98 passed）。

### 快照預測與實際
| 檔案 | 預測 | 實際 |
|---|---|---|
| parity `refactor_3wr2.json` | flash 只變 `skill_st_unbroken_will@5@2` 第 1、3 段 | 我的改動造成的就是這一鍵；另外重產帶進 main 本來就壞的 31 鍵（X10-3a 文字），見第 2 節 |
| CLI 輸出雜湊、`llm` 快照、OpenAPI | 不變（閃現模板文字不進 CLI 戰鬥／技能輸出；改的是欄位 docstring） | 不變，沒重產 |
| `client/` 夾具 | 不動（X10-3b 的範圍） | 沒動；`flashChoice.json` 裡沒有 `stance_enter_*` 的說明 |

## 6. 待 PM 決定
1. **免死的戰鬥敘事還寫「HP 留在 1」**（程式輸出，不是註解，這段沒改）：
   - `narrative/events.py` 1274：`DeathCheated` 的敘事句。實際 HP 留在 10。
   - 改了可能會動到 CLI 文字輸出快照（戰鬥裡出現免死的場次）。
   - `narrative/skills.py` 925 的卡片說明也一樣，那個檔在 X10-3b 範圍內。
   - 建議交給 X10-3b，或另開一段一起處理。
2. **最低花費驗證還是「≥ 1」**（規則類，發現的，沒改）：
   - `content/skill_rules.py` 664 `resource_minimum`：主動技法力或耐力 `>= 1` 就通過，訊息寫「至少要花 1 點」。
   - `skillgen/options.py` 1288 的欄位說明也寫「至少要花 1 點」。
   - `proposal_numbers.py` 266 補值時用的下限已經是 1 × scale，以血支付也留 1 × scale。驗證器的下限要不要也改成 scale，是規則問題。
   - 目前文字和驗證器一致，所以沒動。
3. **main 上 parity 本來就壞了 31 鍵**（X10-3a 改了模板文字、沒重產）：這段照標準程序重產時一起修好，已在第 2 節逐鍵說明。開發 PM 合併 X10-3a 之後的驗收，建議加跑 slow parity。

## 7. 平衡疑慮
- 有一個行為改變：閃現「俐落」「沉勢」「變身姿態的輕巧／蓄力」一次改 10 點法力或耐力（原本實際只改 1，等於舊單位的 0.1），最少留 10。這就是裁定要的修正。
- 預算器會照新費用重算強度，沒有另外調數值。
- 戰鬥不變比對 different=0，既有戰鬥沒有改變。
