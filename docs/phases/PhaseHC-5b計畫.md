# Phase HC-5b 計畫：組合器與候選常數搬進 content

> 來源：`docs/phases/寫死數值-清單.md` HC-5 節 b 項；HC-5a、QF-4b 報告最後的開發 PM 裁定。
> 原則：**結果不變**，只換數字放的地方，數值不變。做法照 HC-5a（skillgen 常數經 `ContentLibrary` 帶入）。

## 範圍

1. **組合器與候選常數搬家**：搬 `src/trpg/skillgen/` 底下剩下的 config todo，共約 135 筆。
   - **檔案**：
     - 組合器：`composer_special.py` 28、`composer_parts.py` 13、`composer_recipes.py` 8、`composer_rider.py`、`composer_dual.py`
     - 階級、提議與進化：`skill_tier.py` 9、`proposal_*`、`evolution.py` 7、`random_composer.py` 6
     - 選項：`option_*`、`options.py`
     - 其他：`candidates.py`、`pick_offer.py`、`budget.py`、`wish_pick.py`、`whiteboard_candidates.py`、`validate.py`、`self_penalty.py`、`complete.py`、`skill_pick.py`
   - 用 `classify.py --dump config` 列出確切清單。
   - 包含 `skill_pick.py` 的 `thin_reasons` 預設值（HC-4b2 裁定 5）、`NESTED_PARAMS`（HC-4b2 計畫「不做」）、`validate.POINT_BLANK_MIN_REACH`（HC-5a 裁定 4）。
   - 放哪裡：優先放 `content/skill_composer.yaml`、`skill_pick.yaml`、`skill_budget.yaml` 既有的區塊；都不合適才新開區塊，並寫理由。
   - 拿不準是 config 還是結構常數，照 `classes.yaml` 的分類規則判斷，附上理由。寫法見 `docs/dev/上手-引擎戰鬥結算.md` 第七節。
   - 量類數字照 `scripts/x10/fields.yaml` 登記。
2. **護主、伴生代價只留一份**（HC-5a 裁定 2）：`composer_recipes.py` 和 `flash_templates.yaml` 轉型模板裡的同值代價，改成共用一處；做不到共用，就加對照驗證。
3. **陷阱輪數在輸入層補值**（HC-5a 裁定 5，**要修**）：
   - HC-5a 之前，LLM 提議和工坊草稿沒寫陷阱輪數時，會自動補 2；HC-5a 之後被 schema 擋下，結果不一樣了。
   - 修法：內容檔的 `TrapSpec.rounds` 照舊必填。LLM 提議與草稿的輸入層，在驗證前沒寫輪數就補組合器的 `trap.enter_rounds.min`。
   - 加測試：沒寫輪數的提議和草稿，結果和 HC-5a 之前（基準 `5188031d0`）相同。
4. **伴生被動也加快取**（QF-4b 裁定 2）：照護主的 `memo` 做法加上，輸出不變。
5. **開進工坊**：
   - 搬進 content 的計價和規則數值，照現有分組放（組合器、預算表）。
   - 每格要有中文名稱，說明寫清楚調高、調低的效果。
   - 純搜尋參數照 HC-5a 的 `rules.search` 前例，不開。
6. **收尾**：變成 0 筆的規則直接刪掉。刪完沒歸類的要是 0。

## 不做

- text 類留給 HC-6。
- `world/*`、`engine/*`、`api/*`、`llm/*` 的模組常數留給 HC-7。
- 不動 `docs/design/`、`config/`、`llm.toml`。不改任何數值。

## 驗收

- **比對**（對照基準 commit）都要 different=0：
  - 434 招逐招預算。
  - 78 場戰鬥。
  - 閃現出題：沿用 HC-5a 的腳本，含兩種用法統計。
  - 組合器：recipe census、`wish_coverage.py` 小樣本、挑選模式三選一 48 格、升級補足。沿用 QF-4b 的腳本。
  - parity、CLI 快照不變。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check` 都要是 0。
- **測試**：
  - 開發中經看門狗只跑相關測試。
  - **交件前全部 commit 之後，先傳訊息問開發 PM「能不能跑」**，回了才跑 `uv run python scripts/check.py`，再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
  - 前端有改，tsc、vitest、build 也要跑。
- **快照、夾具**：先預測再逐鍵核對，不整批重產。
  - CLI 快照重產要用 `-n 0`：平行跑時各個 worker 寫回同一個檔，會互相蓋掉。
  - API 有改就重產 OpenAPI。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-5b報告.md`，要附：
  - config todo 剩幾筆（推送前的後端是 299，HC-5a 後）；
  - `skillgen/` 剩幾筆，目標是 0；
  - 新開的工坊欄位。
