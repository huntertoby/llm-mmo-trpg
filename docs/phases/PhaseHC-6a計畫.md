# Phase HC-6a 計畫：後端說明文字裡的寫死數字改從資料帶入

> 來源：
> - `docs/phases/寫死數值-清單.md` HC-6 節 a、b 項。
> - 使用者「全部集中化先做完」。
> - HC-5b 裁定 4：`wish_cards`「3 張」。
> - 專案 PM 轉玩法 PM 的順手項：`recipe_census` 的設計鍵要算進召喚物種類。
>
> 原則：**玩家看到的字不變**。這段只把字裡寫死的規則數字，改成從規則、資料組字；目前的值不變，組出來的字也就和現在逐字相同。

## 範圍

1. **後端的說明文字**（text 類，用 `classify.py --dump text` 列出確切清單）：
   - `src/trpg/narrative/` 33 筆；
   - `src/trpg/skillgen/` 35 筆（含 `option_*`、`budget.py` 的標籤）；
   - `src/trpg/content/` 69 筆，大多是驗證訊息裡的上下限；
   - `engine/`、`world/`、`llm/prompts`、`bot/` 的零星約 25 筆。

   做法：
   - 字裡的數字照對應的 content 規則或 schema 常數組字。
   - 驗證訊息裡的上下限，改用 schema 的 `Field` 界線或規則包的值。不要另外寫一份常數。
   - LLM 提示詞裡的規則數字也改成組字，例如 `wish_cards`「3 張」。
     - **提示詞的文字如果因此改變**（有任何一個字元不同），要照 `docs/dev/上手-LLM.md` 升 `PROMPT_VERSION`，並寫進報告。
     - 目標是組出來的字逐字相同，所以版號不必升。
   - `wish_cards` 改成組字後，把它開進工坊，放進挑選的分組（HC-5b 裁定 4）。
   - 真的是寫死的固定說法、不是規則數字的，照 `classes.yaml` 的分類規則改判成 const，附上理由。例如「第 1 段」、「兩條」的語法用字。
2. **順手項**：`scripts/recipe_census.py` 的設計鍵算進召喚物種類，召喚 2～3 階才不會被誤報成薄格。
   - 用 `--keywords summon --seeds 50` 的前後結果證明薄格減少。
   - 其他關鍵字格的結果不變：抽幾個非召喚的關鍵字，用 `--seeds 4` 比對，different=0。
3. **收尾**：搬完變成 0 筆的規則就刪掉，刪完後沒歸類的要是 0。

## 不做

- `api/`、`client/` 的文字，以及介面文字項目（工坊 15 筆、祝禱骰子字等），留給 HC-6b。
- 不改任何數值，也不改玩家看到的字。

## 驗收

- **字不變**：
  - CLI 快照、parity、前端夾具都不變。這段只換組字的方式，所以快照不能有任何變動；有變就是錯了。
  - 敘事與卡片文字：用固定的技能、狀態、召喚物各抽一批（例如全部 438 招的卡片文字、全部狀態的說明），前後逐字比對 different=0。
  - 驗證訊息：每一類錯誤各造一筆不合法的內容，比對改前、改後的訊息逐字相同。
  - 提示詞：mock LLM 收到的提示詞，前後逐字相同。
- 434→438 招的逐招預算，以及 78 場戰鬥，都要 different=0。
- **靜態檢查**：ruff、format、mypy、lint-imports、`trpg content check`、`classify.py --check`，結束碼都要是 0。
- **測試**：
  - 開發中經看門狗只跑相關的測試。
  - **交件前全部 commit 之後，先問開發 PM「能不能跑」**：
    - 回「可以跑」：照 PM 的指示做，例如先 `git merge --no-edit main`，再跑 `uv run python scripts/check.py` 和 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。有失敗就修好、commit、重跑，直到全部通過。
    - 回「不用跑」：直接交件。
- **commit 與報告**：每項一個 commit。報告寫在 `docs/phases/PhaseHC-6a報告.md`，附上 text 剩幾筆，以及改判成 const 的清單。
