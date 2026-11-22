# Phase HC-4b 計畫：技能規則的預設值搬進 content

> 來源：`docs/phases/寫死數值-清單.md` HC-4 節；HC-4a、HC-W2、QF-3a 的開發 PM 裁定。
> 原則：**結果不變**。這段只換數字放的地方，數值不變。做法照 HC-4a（`docs/phases/PhaseHC-4a計畫.md`、報告）。

## 範圍

1. **技能規則搬家**：搬 `src/trpg/content/skill_rules.py`（config todo 約 103 筆）和 `src/trpg/content/skills/constants.py`（約 18 筆）。
   - config 類的預設值：內容檔（`content/skill_budget.yaml` 等）有寫的，拿掉程式預設值、改成必填；沒寫的，先把值寫進 content，再改成必填。
   - 「有某欄才用到」的欄位，照 HC-4a 的做法：可以省略，用到時必填。
   - 遊戲規則型的上下限搬到 content 規則檔，讀不到規則的地方改在 `Ruleset` 層驗證。
   - `CoreRules._check_tier_budget` 的 1～5（HC-4a 裁定 3）和 `SkillDef.tier` 一起搬。
   - 搬進 content、而且是計價或規則數值的，加進 `tuning_fields.yaml`，放進 HC-B 的對應分組。
   - 改完的那一區，`classes.yaml` 的 status 改成 done。
2. **前幾段留下的收尾**：
   - 刪掉 `scripts/hardcoded/classes.yaml` 裡戰鬥核心 6 條逐檔的 done 規則（HC-4a 裁定）。刪掉後，之後新寫的預設值會被掃描抓到。刪掉後如果有筆數變成沒歸類，就照 HC-4a 的分類補正確的規則。
   - **裝備總減傷上限和元素修正下限一起開進工坊**（HC-W2 裁定 2）：兩格一起驗證（減傷上限 ＝ 1000 − 元素修正下限）。說明裡寫清楚兩格要一起改。
   - **鎖 `pytest-xdist` 版本上限 `<3.9`**（QF-3a 裁定 2）：改 `pyproject.toml`，跑 `uv lock`。`uv.lock` 只能有 xdist 這一行的變動。

## 不做

- `skill_pick.py`、`composer_rules.py`、`flash_templates.py`、`skill_evolution.py`、`skills/modifiers.py` 留到下一段（HC-4b2）。
- 不動 `docs/design/`、`config/`、`llm.toml`。不改任何數值。

## 驗收

- **結果不變**：
  - 78 場戰鬥不變比對 different=0（`ruleset_hash` 除外）。
  - 逐招預算比對（434 招）different=0。比對腳本可以沿用 HC-B／HC-W2 的。
  - parity、CLI 快照都不變。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要 0。
- **測試一律經看門狗跑**：`uv run python scripts/run_pytest.py -q <路徑> -n 8`，見 `docs/dev/上手-測試.md`。交件前：
  - 所有目錄的非 slow 測試各跑一輪（分目錄、一次一組；`tests/llm` 和 `tests/skillgen` 不同時跑）。
  - 再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
  - 前端有改的話，tsc、vitest、build 也要 0。
- **快照與 API**：快照、夾具先預測再逐鍵核對，不整批重產。API 有改就重產 OpenAPI。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-4b報告.md`，要附：
  - config todo 剩幾筆；
  - 新開的工坊欄位。
