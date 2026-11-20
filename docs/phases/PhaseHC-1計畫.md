# Phase HC-1 計畫：寫死數值掃描工具與歸類檔

> 來源：使用者「感覺以後這種變數類都要搞個CONFIG 之類的東西 才好改動」；排序由使用者決定「全部集中化先做完」（專案 PM 轉，2026-11-21）。
> 盤點初稿：`docs/phases/寫死數值-盤點初稿.md`。
> **這段不搬任何數字**，只做工具和清單。搬家是 HC-2 之後的事。

## 範圍
1. **後端掃描**：`scripts/hardcoded/scan_py.py` 用 AST 列出 `src/trpg/` 的下列內容，每筆附「檔:行、所在函式或類別、值、前後文一行」：
   - 數字字面值。不列 0、1、-1，也不列 `range()` 的參數，其他全部列。
   - 含數字的中文字串，包括 docstring。
2. **前端掃描**：`scripts/hardcoded/scan_ts.py`（或 node 腳本）列出 `client/src/` 非測試、非 fixtures 的 .ts／.tsx 裡：
   - 數字字面值；
   - 含數字的中文字串。
   - 排版用的 px、毫秒、顏色、z-index，要能用規則自動排除。排除規則寫在歸類檔裡，規則本身要看得懂。
3. **歸類檔**：`scripts/hardcoded/classes.yaml`。每一筆（或一組規則）歸成下列其中一類：
   - `config`：應該進 content 或工坊設定的玩法數值；
   - `scale`：量類，應該由 `quantity_scale` 推導；
   - `const`：真的是常數，例如格數、AP、d20、‰ 換算、程式邏輯；
   - `text`：說明文字裡的數字，應該從資料帶入；
   - `layout`：前端排版。
   - 要能用「檔案或函式加樣式」成批歸類，不要求逐筆手寫。
   - 每筆要有 `status`：`todo`（還沒搬）或 `done`。
   - 規則：`config`、`scale`、`text` 這三類一開始都是 `todo`。
4. **涵蓋測試**：`tests/test_hardcoded_scan.py`。掃描結果中只要有一筆沒被歸類檔涵蓋，測試就失敗，訊息要寫清楚怎麼歸類。這就是防止再犯的檢查。
5. **統計報告**：產出 `docs/phases/寫死數值-清單.md`，內容：
   - 各類、各子套件的筆數；
   - `config`、`scale`、`text` 的完整清單，依區塊分組；
   - 建議的搬家分段，每段 2～3 件、同一塊。

## 驗收
- 涵蓋測試 0（全部有歸類）。
- 歸類照最保守的做法：拿不準是 `config` 還是 `const` 的，歸 `config`。報告列出這類項目。
- ruff、format、mypy、lint-imports 都是 0。這段不改 src 的行為，相關測試照舊要過。
- 每項一個 commit。報告寫在 `docs/phases/PhaseHC-1報告.md`。
