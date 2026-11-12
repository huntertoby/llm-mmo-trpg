# CODE-1 報告：程式整理第一批（I1、I4、I5、I6、I7）

依據 `docs/phases/整理提案-程式.md` 2.1（使用者：「瘦身都照建議」）。I2、I3、I8 不在本批。

## 做了什麼

| # | 內容 | 數字 | commit |
|---|---|---|---|
| I1 | 一次性量測腳本 `git mv` 到 `scripts/archive/`，加 `README.md`（一行一支：檔名｜用途｜對應段）與巢狀 `ruff.toml` | **57 支、12,306 行**；`scripts/` 腳本從 95 支降到 38 支 | `712c0dee` |
| I4 | import-linter 新契約「content 不得匯入 engine」；`tests/test_architecture.py` 的 `CONTENT_FORBIDDEN` 與說明同步 | 契約 13 → 14 條 | `3cc54321` |
| I5 | 刪 client 無效的 `eslint-disable-next-line` 註解（App、WaitScene、MailPanel、RunScreen、startResources、allocationPreview） | 6 行，只刪該行 | `9d734e0b` |
| I6 | `src/trpg/primitive_coverage.py` → **`src/trpg/api/primitive_coverage.py`**（不是 content，理由見下）；更新 `api/app.py`、`cli/main.py`、`tests/test_primitive_coverage.py` 的 import 與 engine／content 的 docstring 引用 | 9 檔 | `020504f9` |
| I7 | 刪 `api/world.py WorldService.battle_of`、`engine/ai/priority.py _formation_total`（全專案 grep 0 引用，含字串與 client） | −13 行 | `1f82511c` |

### I1 細節
- 清單重算：對每支腳本 `grep -rlF <檔名>` 與 `scripts\.<stem>`／`from <stem> import`，範圍為守則指定的程式、測試、交接、部署與設計文件。結果 **59 支只在 `docs/phases/`、`docs/archive/` 出現**（提案寫 49，差別在提案把「被其他一次性腳本匯入」的 10 支算成有引用；這次照「互相匯入的一組一起搬」整組搬）。
- **留在 `scripts/` 的 2 支**：`bal12b_measure.py`、`budget_knob_audit.py`——它們匯入 `flash_minor_coverage.py`（被 `tests/sim` 引用，必須留），依「一組一起留」不搬。
- 搬後修正：`Path(__file__).resolve().parents[1]` → `parents[2]`（11 支，找專案根目錄／`src`／`content`）；`bal13d_backstab.py` 載入 `weak_build_audit.py` 的路徑；`verify_sandbox.sh` 的 `cd` 改到上兩層；各腳本用法說明的 `scripts/<檔名>` 改成 `scripts/archive/<檔名>`。抽查 7 支 `--help`＋匯入同目錄模組都正常。
- `scripts/archive/ruff.toml`：`extend = "../ruff.toml"`，`src` 加入本目錄（同目錄互相匯入的排序不變），只放寬 E501（用法路徑變長）；因此 `ruff --fix` 移除 15 個已無作用的 `# noqa: E501`。mypy／ruff 範圍仍含 `scripts/archive/`，未排除。

### I4：narrative → skillgen 的 3 筆（未加契約、未改程式）
| 檔案 | 匯入 | 用途 |
|---|---|---|
| `src/trpg/narrative/skills.py:57` | `trpg.skillgen.budget.self_status_allowance_permille` | 技能卡代價文字「施放後自己○○（換 N% 預算）」算出代價狀態換到的預算比例 |
| `src/trpg/narrative/skills.py:58` | `trpg.skillgen.keywords.SkillKeywords`、`derive_draft_keywords` | 技能工坊草稿卡片的製造／利用關鍵字（`draft_card_keywords`）與型別 |
| `src/trpg/narrative/keyword_hints.py:20` | `trpg.skillgen.keywords.derive_draft_keywords` | 技能工坊的關鍵字提示（由推導表產生建議句） |

三筆都是「卡片文字要顯示 skillgen 算出的值」，方向是 narrative 讀 skillgen 的純函式；skillgen 不匯入 narrative，沒有環。

### N7：`src/trpg/bot/` 的時間匯入
bot 只用 `datetime`（`fromtimestamp` 轉當地時間），現況 `ruff check src/trpg/bot` 通過，不需要巢狀 `ruff.toml`，未動。

## 驗收
- `ruff check`、`ruff format --check`、`mypy`（1,380 檔）、`lint-imports`（14 kept, 0 broken）全過。
- `pytest tests/test_architecture.py tests/api tests/content -n 4`：3,500 passed、1 skipped。
- 分項：`tests/test_play_script.py`、`tests/world/test_situation_coverage.py`（18 passed）、`tests/test_sim_scripts.py`＋`tests/sim/test_flash_minor_coverage.py`（2 passed）、`tests/test_primitive_coverage.py`（26 passed）、`tests/api`（778 passed, 1 skipped）、ai.priority 相關 `tests/engine/test_mechanics_5am*`＋`tests/api/test_world_api.py`（55 passed）、`pnpm -C client typecheck` 通過。
- 重播：`trpg battle --map swamp --seed 7` → replay 通過（88 動作、313 事件）。

## 留給下一批
- I2（library 固件合併）、I3（同名小工具合併）、I8（client dev 入口與 gallery 搬家）。
- skillgen 的疑似死定義（本批不能動 skillgen）：`skillgen/summon_evolution.py:222 summon_spec`、`skillgen/keywords.py:176 keyword_def`、`skillgen/proposal.py:292 _penalty_type`——再 grep 一次皆 0 引用，可刪。
- I6 搬家後，以下 docstring 仍寫舊路徑 `trpg.primitive_coverage`（在 LLM-1 agent 的範圍內，本批不改）：`src/trpg/skillgen/budget.py:1116`、`src/trpg/narrative/skills.py:1021`、`src/trpg/narrative/skills.py:1211`。

## 待 PM 決定
1. **I6 放 `trpg.api` 而非 `trpg.content`**：模組匯入 engine、skillgen、narrative，放 content 會違反「content 不得匯入 skillgen／engine」；`trpg.api` 本來就依賴這三層，搬過去不新增任何套件間的邊（cli → api 原本就有）。若希望另開中性子套件（例如 `trpg.checks`），下一批再搬。
2. **I1 搬 57 支而非提案的 49 支**（見 I1 細節），`bal12b_measure.py`、`budget_knob_audit.py` 因相依留在 `scripts/`。
3. `docs/archive/phases/README.md` 的 BAL 重產表（別人的檔，未改）仍寫 `scripts/<檔名>`，其中指到已搬腳本的：BAL-4、6、7、8、8b、9、9b、9c、10（`flash_converge_measure`、`flash_reclaim_measure`）、12（`bal13c_matrix`、`bal13d_matrix`、`matrix_ranks`、`skill_diagnosis`、`synergy_audit`）、13、14、15、16、18、19g。`scripts/archive/README.md` 已註明「舊報告的 `scripts/<檔名>` 即本目錄同名檔」；是否要改表由文件 PM 決定。
4. narrative → skillgen 3 筆是否加契約（例如只允許 `skillgen.budget`／`skillgen.keywords`）或維持現狀。
