# Phase GS-2 計畫：形態補 8 招手寫技能（#172）

> 來源：
> - 使用者原話「不用跑，8 招可以，寫進去」（專案 PM 轉，2026-11-21）。
> - `docs/玩法決定紀錄.md` #172。
> - `docs/design/06-技能.md` 6.30 最後一點（形態池名單，38f52a0ae）。
> - `docs/形態補招提案.md`。
>
> 排在 GS-1（#171、#172 出題）之後。

## 受影響的既有功能（開工先盤點，寫進報告）

- 形態池、三選一指定形態的出題、技能清單與 CLI 快照、前端技能卡夾具、434 招逐招預算（會變成 442 招）、技能圖示推導。

## 範圍

1. **新增 8 個手寫技能檔**到 `content/skills/`，寫法照現有的 `skill_form_*.yaml` 與 `skill_form_release_burst.yaml`。內容以 06 6.30 最後一點為準：
   - 高階化身（姿態、法術類別、不限武器）：
     - 熊王怒吼：3 階，史詩
     - 影貓潛襲：3 階，稀有
     - 巨人踐地：4 階，稀有
     - 龍威降臨：4 階，史詩
   - 高階利用者（主動技，條件是「在形態中」）：
     - 野性連擊：3 階，稀有
     - 化形震地：3 階，史詩
     - 原形歸一：4 階，史詩
     - 化形守護：4 階，史詩
2. **限制**：
   - 不加新形態，不加新原語，不改 `forms.yaml`，不用新美術（圖示照推導表）。
   - 有某招用現有原語做不出來，就先跳過，寫進報告。
3. **數值**：
   - 照預算 70～100% 取最保守的初值。只跑內容載入的靜態預算驗證（`trpg content check`），不跑模擬。
   - 有招裝不進預算區間的，寫進報告給使用者在工坊調，不改招式內容。
4. **每招都要寫 narrative**：`concept`、`cast_flavor` 用繁中，名字照上面寫。
5. **這 8 招不當起始技能**。

## 不做

- 不改 `docs/design/`。不改其他招式和數值。

## 驗收

- `trpg content check` 結束碼要是 0，8 招的預算都在 70～100%，報告附每招的比例。
- 8 招都在形態池裡，要有測試。
- 三選一指定形態時，3 階、4 階、史詩都有招可以出，要有測試；也可以用 `recipe_census.py --keywords form` 小樣本證明。
- 這 8 招都不在起始技能裡，要有測試。
- 原有 434 招逐招預算 different=0，只多出 8 招。
- **快照**：照常重產。重產前先預測，只會多出這 8 招，或是含技能清單的鍵會變。CLI 快照用 `-n 0` 重產，parity 用 `uv run python -m tests.skillgen.test_refactor_parity` 重產，前端夾具照 `scripts/export_client_fixtures.py` 重產。
- **靜態檢查**：ruff、format、mypy、lint-imports、`classify.py --check`，結束碼都要是 0。
- **測試**：
  - 開發中經看門狗只跑相關測試。
  - **交件前全部 commit 之後，先問開發 PM「能不能跑」**，PM 回覆後才跑 `uv run python scripts/check.py`，再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
  - 前端夾具有改的話，vitest 也要過。
- **commit 與報告**：每項一個 commit，報告寫在 `docs/phases/PhaseGS-2報告.md`。
