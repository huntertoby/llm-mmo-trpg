# Phase AP-2b 報告：預支技能 0 法力

> 規格：`docs/phases/PhaseAP-2b計畫.md`。基準 `7ede8c01f`（開工時 `git merge main`）。分支 `worktree-agent-a6c4388ff5cede0e5`，沒有 push。
> 沒有試數值、沒有跑平衡量測；沒有改 `docs/design/`、`config/`、`client/`。

## 1. 做了什麼

| 項目 | commit | 內容 |
|---|---|---|
| 1 規則放行 | `2ffb7cc7d` | `SkillBudget.min_cost_problem` 加關鍵字參數 `borrows`（預設 `False`），為真時不擋。呼叫端：驗證器 `validate_skill`（傳 `skill.borrows_ap`）、往返覆蓋 `proposal_coverage._known_rules_only`、LLM 提議補值 `proposal_numbers._fill_cost`（帶預支時不補 1 點法力／耐力）。工坊（`api/workshop.py`）、數值工坊預覽（`api/tuning/skills.py`）都走 `validate_skill`，跟著放行。新測試 `tests/skillgen/test_borrow_min_cost_ap2b.py`（6 條）。 |
| 2 搶拍 0 法力 | `64d85a1d3` | `skill_borrowed_beat.yaml` 的代價 `{mana: 1, cooldown: 2}` → `{cooldown: 2}`。卡片、`skills show` 由代價自動產生，現在是「代價 AP 0，冷卻 2 回合」。`test_borrow_skill_ap2` 加「0 法力、0 耐力」斷言。 |
| 3 其他預支技能 | `755eb3461` | 組合器的基本款預支（`random_composer._borrow_skill`，`composer.borrow_core` 串流）改成只有冷卻、不花法力。閃現大變化 `borrow_deep` 本來就不動代價，沒改。`test_borrow_offers_ap2` 加斷言；`test_workshop_feedback` 的「組合器一律付最低花費」改成照規則傳 `borrows`（種子 140 是預支）。 |

改到最低花費的地方（先列再改）：`content/skill_rules.py:min_cost_problem`（規則本體）、`skillgen/validate.py`、`skillgen/proposal_coverage.py`、`skillgen/proposal_numbers.py`、`skillgen/random_composer.py`（預支基本款）。`skillgen/composer_parts.py:1143`、`composer_special.py:263` 是一般技能的費用抽法，跟預支無關，沒改。

## 2. 檢查（結束碼）

每個 commit 前都跑 ruff、format、mypy、lint-imports、`trpg content check` 與 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`（`-n 8`）。

| 指令 | 第 1 項 | 第 2 項 | 第 3 項 |
|---|---|---|---|
| `ruff check .` | 0 | 0 | 0 |
| `ruff format --check .` | 0（第一次 1：新測試檔沒格式化，格式化後 0） | 0 | 0 |
| `mypy` | 0 | 0 | 0 |
| `lint-imports` | 0 | 0 | 0 |
| `trpg content check` | 0 | 0 | 0 |
| `-m slow` parity ＋ `tests/cli` | 0（982 passed） | 0（982） | 0（982） |
| 相關測試 | `tests/skillgen` ＋ `test_skill_rules_content`：0（4649 passed，7 skip） | borrow 相關 5 檔 ＋ `tests/content`、`tests/narrative`、`tests/api/tuning`：0（3855） | `tests/skillgen`：第一次 1（`test_workshop_feedback` 1 個，見第 5 節），改後該檔 0；`roguelite` 0（279）、`llm` 0（495）、`sim` 0（180）、`world` 0（1328）、`api` 0（1331，1 skip） |

重播：`trpg battle --map open_plain --seed 10 --log-json` ＋ `battle replay`：0、0（71 個動作、311 個事件，同 AP-2）。
前端沒動，沒跑 tsc／vitest。全量 `scripts/check.py` 沒跑（PM 跑）。

## 3. 戰鬥不變比對

腳本在 scratchpad（未 commit）：改前＝`git archive 7ede8c01f` 的 `src content config`，`PYTHONPATH` 指向舊 `src`（印出 `trpg.__file__` 確認兩邊路徑不同）；17 張地圖 × 種子 1、2 預設陣容 ＋ `open_plain` 種子 3 × 48 個 `--ally-build`；比整份 `--log-json`（去掉 `ruleset_hash`、`format` 與 `setup`／`final_state` 裡內嵌的 `ruleset`——搶拍的定義在 ruleset 裡，所以會變）。

| 時間點 | 結果 |
|---|---|
| 第 2 項 | `battles=82 events=20979`，80 場相同；`build_form_mastery`、`build_form_tester_2` 兩場改前改後都在開場報錯（`skill_form_breath_dragon`，既有問題），只有錯誤訊息裡的路徑不同 → 實質 different=0 |
| 第 3 項 | 同上 |

沒有任何陣容或 build 帶預支（AP-2 待決 4 沒給精英、頭目裝），所以這個結果是預期的。

## 4. 快照、夾具（先預測再逐鍵核對）

| 東西 | 預測 | 結果 |
|---|---|---|
| parity `refactor_3wr2.json` | 第 2 項：`complete`、`retier` 各 `skill_borrowed_beat` 一鍵；閃現取樣不含搶拍 | 對：只這 2 鍵失敗，用腳本只改這 2 鍵（`3b186bfb…→83f2541d…`、`76c1bcd4…/fac1af25…→be616cec…/b5c70c92…`） |
| CLI 快照 | 第 2 項：`skills_list`（列出代價）與 `skills_show_all/01`（搶拍排第 37、每片 28 招）；7 場戰鬥不變 | 對：`UPDATE_CLI_SNAPSHOTS=1 … -k "skills_list or skills_show_all/01"` 不加 `-n` 重產 2 鍵 |
| 前端 `skill_icons.json` | 不變：它的 `costs`／`cost_values` 不記法力（465 招都是空的） | 沒動 |
| 第 3 項（組合器） | 沒有夾具鎖組合器的預支技能（AP-2 第 4 項也沒有夾具變動） | 對：`skillgen`、`roguelite`、`llm`、`sim`、`world`、`api` 都沒有夾具失敗 |

## 5. 為新規則改的測試

- `test_workshop_feedback.test_random_composer_always_pays_the_minimum_cost`：直接呼叫 `min_cost_problem` 沒傳 `borrows`，種子 140 是組合器的預支 → 改成照規則傳 `borrows=skill.borrows_ap`。
- `test_borrow_skill_ap2`、`test_borrow_offers_ap2`：加「0 法力、0 耐力」斷言。
- 新檔 `test_borrow_min_cost_ap2b.py`：預支技能（法術、武器）0 法力 0 耐力通過；不帶預支的法術技、武器技去掉法力／耐力後照舊 `cap.min_cost`；提議補值不幫預支補費用、其他主動技照補 1。

## 6. 版號

- `PROMPT_VERSION`、提議 schema：沒動（提示詞與 schema 都沒有寫最低花費或預支費用）。
- `LOG_FORMAT`：沒動。

## 7. 待 PM 決定

1. **預支是「可以 0」不是「必須 0」（解讀）**：最低花費只是不擋；預支技能若花法力（例如 LLM 提議、工坊）照舊合法、照舊算代價折抵。設計寫「不花法力、耐力」，若要硬性規定 0，要另加一條驗證。
2. **工坊說明文字沒改**：費用欄位說明仍是「主動技能至少要花 1 點」。工坊的 AP 選單是 1～3（AP-2 待決 10），做不出預支技能，所以沒加例外說明。
3. **數值工坊批次改 `ap_cost` 的範圍是 1～3**（`api/tuning/skills.py` `_SCALAR_LIMITS`）：對搶拍批次改 AP 會被夾成 1、然後驗證失敗。AP-2 就有，不在本段範圍，記一下。
4. **`build_form_mastery`、`build_form_tester_2` 在 `trpg battle --ally-build` 開場報錯**（`skill_form_breath_dragon`），改前就有，與本段無關。

## 開發 PM 裁定（2026-11-20）

合併：`Merge AP-2b`（--no-ff）。合併後 ruff、format、mypy、lint-imports、`trpg content check` 都是 0；全量檢查合併後跑一次。

待決 4 件：
1. 接受：「可以 0」，不強制。設計寫的是不受最低花費限制，沒寫必須是 0。
2. 接受。工坊做不出預支技能，說明文字先不改。
3. 排進佇列：數值工坊批次改 `ap_cost` 時，遇到預支技能要放行 0。
4. 排進佇列：兩個 form build 用 `--ally-build` 開場就報錯（`skill_form_breath_dragon`），改前就有，要另外查原因。
