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

---

## 補件（開發 PM 裁定待決 2 之後；基準 merge main `0d1716186`）

| # | 項目 | commit |
|---|---|---|
| 3 | 升階減費的法力、耐力取到一格的倍數（`skill_tier._cost_variants`） | `9b6e2e9e6` |
| 4 | 最低花費驗證改成 ≥ 一格；舊單位的測試輸入與存檔夾具 ×10 | `59c5eee40` |
| 5 | 常駐類傳說的候選法力 × scale（`composer_special._lasting_candidates`） | `53867b122` |

### 掃描（第 4 項之前，照 PM 要求）
- 掃描範圍：content 434 招，加上照 parity 跑法重跑出來的 2361 份產物（complete、升到 2、3 階的 retier、41 招 × 3 種子 × 3 次閃現題目）。
- content 裡沒有法力或耐力落在 1～9 的主動技。
- 產物裡有 1 招中了：`skill_taunting_roar` 升到 2、3 階後是法力 5。已回報，PM 選擇第 3、4 項兩個都做。
- 第 3、4、5 項做完後重跑掃描：1～9 的有 0 份，不是 10 倍數的也是 0 份。

### 第 3 項：升階減費
- 原因：`_cost_variants` 把法力、耐力乘 1000／500／0‰，換算後 10 × 50% 得到 5。換算前是 1 × 50% → 0，會被最低花費擋下。
- 修法：乘完 ‰ 往下取到 `cost_floor`（10）的倍數，取到 0 的版本交給驗證器去擋。
- 同類掃描（skillgen 的費用計算）：
  - 「費用 × ‰」只有這一處；
  - 閃現輕巧、`flash_trade`、`complete` 已經用 `cost_floor`；
  - 組合器、白板、LLM 補值的費用來自 content（都是 10 的倍數）或 `ctx.scale`；`stamina_for_mana` 是 ×2；
  - 寫死的候選費用走 `scaled_cost`，只有傳說候選是例外，見第 5 項。
- parity：
  - 預測：先用修正前的程式列出所有產物裡不是 10 倍數的，共 7 招，都在 retier：`blessing_thief`、`dispel_magic`、`frost_shackle`、`sum_shadow_twin`、`taunting_roar`、`void_swap`、`wis_repelling_light`。預測就是這 7 個 retier 鍵會變，complete、flash 不變。
  - 實際：slow parity 剛好這 7 鍵失敗。重產後逐鍵比對：retier 7／406、complete 0／406、flash 0／123，鍵數都沒增減。
- 和換算前（`f6d2bc957` 的 src 加 content）比：7 招的 2 階、3 階，差別只在費用，而且都正好 ×10：

| 技能 | 2 階 | 3 階 |
|---|---|---|
| blessing_thief | 法力 2 → 20 | 2 → 20 |
| dispel_magic | 5 → 50 | 2 → 20 |
| frost_shackle | 2 → 20 | 2 → 20 |
| sum_shadow_twin | 耐力 3 → 30 | 1 → 10 |
| taunting_roar | 法力 1 → 10 | 1 → 10 |
| void_swap | 2 → 20 | 2 → 20 |
| wis_repelling_light | 2 → 20 | 2 → 20 |

- 回歸測試 `tests/skillgen/test_skill_tier.py::test_retier_cost_cuts_stay_on_quantity_steps`：
  - 法力 10 的變體依序是 [10, 0]，法力 30 的是 [30, 10, 0]；
  - 嘲諷怒吼升到 2、3 階後法力都是 10。

### 第 4 項：最低花費
- `content/skill_rules.py` `min_cost_problem`：
  - 加上必填的 `scale` 參數，判斷改成 `>= scale`（和 `cost_floor` 相同）；
  - 提示文字「主動的法術技至少要花 {scale} 點法力」，數字由程式算，不寫死；
  - 呼叫端 `validate.py`、`proposal_coverage.py` 傳 `core.quantity_scale`。
- `skillgen/options.py` 的費用欄位說明：「主動技能至少要花 {scale} 點（空白或少於 {scale} 檢查會不通過）」。
- 回歸測試 `test_borrow_min_cost_ap2b.py::test_min_cost_is_one_quantity_step`（法術、武器各一組）：
  - 花 5 被擋，提示寫「至少要花 10 點」；
  - 花 10 通過；
  - 預支技能的 0 照舊放行。
- 驗證器變嚴後失敗的測試，都是輸入還寫著舊單位的費用，照 ×10 修正（斷言沒有放寬）：

| 檔案 | 舊 | 新 |
|---|---|---|
| `tests/skillgen/workshop_walks.py`（15 個測試檔共用的工坊走法） | stamina 2（兩處） | 20 |
| `tests/engine/test_composite_skills.py`、`test_composite_followups.py`、`test_delayed_followup.py` | stamina 1 | 10 |
| `tests/api/test_workshop_api.py` `test_equipment_limits_are_checked` | mana 4 | 40 |
| `tests/skillgen/test_keywords.py` | mana 6 | 60 |
| `tests/skillgen/test_wind.py` | mana 4 | 40 |
| `tests/skillgen/test_weapon_affinity.py`（兩處） | stamina 8 | 80 |
| `tests/skillgen/test_workshop_feedback.py` | 斷言「1 點耐力」「1 點法力」 | `{scale} 點` |

  沒有失敗的舊單位輸入沒有動，例如 `test_workshop_api` 的 rune 草稿 mana 4、`test_workshop_feedback` 的 `_rune_draft`，以及 X10-3a 待決 4 已經裁定不改的 `test_self_costs`、`test_stamina_cost`。
- 其他呼叫 `min_cost_problem` 的測試（`test_proposal.py`、`test_workshop_feedback.py`、`test_borrow_min_cost_ap2b.py`）補上 `scale=`。

#### 存檔夾具 `tests/roguelite/fixtures/flash_history_3wr1.json` ×10（PM 裁定 A，比照 X10-2b B7）
- 為什麼要改：整份是舊單位，fire_bolt 存的定義是法力 6。驗證器變嚴後，閃現候選全部不合法。照程序重產的話，新跑出的局裡第 2 次閃現不是 `range_plus`，有 6 個測試靠這個前提，所以不重產，閃現歷史保留。
- 做法：腳本 `C:\Users\tobby\AppData\Local\Temp\claude\9f1b79de9b6f77a5\9d8cd6cd-f0cd-4696-a663-73ef271d469e\scratchpad\x3c\scale_fh.py`。
  - 用 `scripts/x10/rescale.py` 的 `load_fields`、`_walk`、`_classify_leaf` 分類：
    - `run.hero` 照 `units/*.yaml`，沒列到的再照 `roguelite.yaml` 的 `start.heroes.*`；
    - `run.generated_skills[]` 照 `skills/*.yaml`。
  - 跑局才有的數字（目前 HP、法力、耐力，戰後資源，已分配的屬性點）沒有對應的內容欄位，比照對應的內容欄位判斷，逐條寫在腳本裡。
  - 有沒分類到的數字欄位就中止。
  - 用 `json.dumps(indent=1)` 寫回：先驗證沒改時和原檔逐字相同，寫回後再用 `loads_save` 讀一次。
- 改了 27 個值，diff 正好 27 行：

| 欄位 | 依據 | 舊 → 新 |
|---|---|---|
| `hero.attributes.str／dex／con／wis／wil` | units `attributes.*` | 10 → 100 |
| `hero.attributes.int` | 同上 | 18 → 180 |
| `hero.max_hp` | units `max_hp` | 40 → 400 |
| `hero.armor_bonus` | units `armor_bonus` | 1 → 10 |
| `hero.max_mana` | roguelite `start.heroes.*.max_mana` | 40 → 400 |
| `generated_skills` 的 `cost.mana`：cinder_mine_cp、ember_ward_t2、fire_bolt_fl_…、rand_1734607427、rand_2114948101、shatter_blast_t2 | skills `cost.mana` | 7→70、2→20、6→60、6→60、10→100、6→60 |
| `run.hp／mana／stamina` | 同 max_hp／max_mana／stamina 的單位 | 44→440、56→560、30→300 |
| `run.history[0..2].hp` | 戰後 HP | 40→400、30→300、11→110 |
| `run.history[0..1].mana` | 戰後法力 | 14→140、4→40（[2] 是 0） |
| `run.history[0..2].stamina` | 戰後耐力 | 30→300 |
| `run.attribute_spent.int` | 屬性點（`attribute_points_per_level` 是 scale） | 8 → 80 |

- 值是 0 的量類欄位（各技能的 `cost.stamina`、`attribute_points`、`history[2].mana`）乘了也是 0。
- 不改的：
  - hero 的 speed、level、resist‰；
  - 技能的 cooldown、tier、ap_cost、骰子、‰ 等（照 skills keep 清單）；
  - seed、level、xp、源力、skill_tier、各種計數；
  - flash 紀錄（nth、reflashes、floor‰、spent 靈感點）；
  - skill_usage（次數、格數）、plan（地圖、種子）；
  - history 的回合、步數、源力、`state_digest`。`state_digest` 是戰鬥最終狀態的雜湊，沒有程式驗證它；
  - 裝備的 `item_level`、`base_bonus_permille`（item_gen 的 base_bonus 是 keep；詞條是空的）。
- 結果：`test_retier.py` 17 個測試全過（含 `test_a_stale_history_flashes_from_the_saved_definition`）。只有這個測試檔用到這個夾具。

### 第 5 項：常駐類傳說的候選法力
- `_lasting_candidates` 的候選法力 `(1, 4, 8, 12)` 改成 × `quantity_scale`，現在是 10、40、80、120。
- 和換算前比：`compose_legendary` 只用 `rule_change`、`rule_rewrite` 兩種核心，種子 0～199（階級 1～3 輪流），兩邊都產出 267 招（有產出的種子相同）。逐欄比對：**只有 `cost.mana` 不同，267 處都正好 ×10，沒有其他差異**。修正前的 HEAD 和換算前比，有 68 處不是 ×10（法力 23＋30、源力 9、冷卻 6），也就是選到不同的候選。
- parity：預測不變（parity 不走隨機組合器）。實際 slow parity 979 passed，沒有重產。
- 回歸測試 `tests/test_x10_scale.py::test_lasting_legendary_mana_candidates_are_scaled`（rule_change、rule_rewrite 兩組）：候選法力都在 {10, 40, 80, 120} 裡。

### 補件檢查（最後一個程式 commit `53867b122`）

| 檢查 | 結束碼 |
|---|---|
| `ruff check .`、`ruff format --check .` | 0 |
| `mypy`（1735 檔） | 0 |
| `lint-imports` | 0（14 kept） |
| `trpg content check` | 0（696 檔、434 技能） |
| 分目錄 `pytest -n 8`（預設標記） | 全部 0：api 1336（1 skipped）、bot 67、cli 148、content 3166、engine 5120、llm 495、narrative 475、roguelite 279、server 77、shared 72、sim 180、skillgen 4637（7 skipped）、world 1328、頂層 200 |
| `-m slow tests/skillgen/test_refactor_parity.py tests/cli` | 0（979 passed） |
| 不變比對 78 場（基準 `ca9429fac`） | `battles=78 events=26446 different=0` |

- 第 3、4 項的 commit 在 commit 前各跑過一次上面整組測試，都是 0。
- 第 3 項另外跑過 skillgen（4635 passed）、slow parity 加 cli（parity 重產前 7 鍵失敗，就是預測的那 7 鍵）。
- CLI 快照三項都沒變，`client/` 沒動。

### 補件待決
- 沒有新的待決。
- X10-3a 待決 1 那兩處（narrative 的「HP 留在 1」）照 PM 裁定交給 X10-3b，這段沒動。

## 開發 PM 裁定（2026-11-20）

合併：`Merge X10-3c` 和 `Merge X10-3c follow-up`，都用 --no-ff。

- 待決 1（narrative 裡免死寫「HP 留在 1」）：交給 X10-3b，已經改成依 scale 算的值。
- 待決 2：判定是換算漏掉，不是規則改變。做法三件：
  - 最低花費改成至少 1 × scale；
  - 升階減費後取到步距的倍數；
  - 常駐類傳說的候選法力 ×10。
  每件都和換算前（f6d2bc957）比對過，結果只差在費用剛好 ×10。
- 待決 3：接受。之後只改文字的段，交件前也要跑 slow parity。
- 舊單位夾具 `flash_history_3wr1.json`：照 X10-2b B7 的做法，用 rescale 的分類函式把數值 ×10，閃現歷史保留不動。
