# 階段 TS-3 報告：移除 testmon 試用模式

基準：main `a93acf4cb`。分支 `worktree-agent-a9bad9d1a0f5b9144`，沒有 push。規格：`docs/phases/PhaseTS-3計畫.md`。

## 結果（一兩句）

試用模式、兩個檔、兩個套件、`.gitignore` 那行都拿掉了。`scripts/check.py`、`pyproject.toml`、`uv.lock`、`.gitignore` 和 TS-2 之前（`e96f2e9ad^`／`662e3b43f^`）逐字相同，所以不加參數、`--all` 和戳記規則都回到 TS-1 的樣子。

## 交付項目
| 項目 | 狀態 | commit |
|---|---|---|
| 1 拿掉 `check.py --testmon` | 完成：`check.py` 直接還原成 `e96f2e9ad^` 的版本（TS-2 之後只有 TS-2 改過它） | `6b878e476` |
| 2 刪 `scripts/testmon_select.py`、`tests/infra/test_check_testmon.py` | 完成 | `9e5105cdc` |
| 3 `uv remove --dev pytest-testmon coverage` | 完成；兩個都移除 | `381e8f152` |
| 4 `.gitignore` 拿掉 `.testmondata*` | 完成（連同上面的註解和空行） | `23494339f` |
| 5 `docs/dev/上手-測試.md` | 完成：一之三節換成一句「曾試過 testmon，不採用，原因見 TS-2 報告」；開頭的修改紀錄改成「TS-3 拿掉 TS-2 的試用模式」 | `53fc52798` |
| 6 TS-2 報告、計畫 | 沒改 | — |

## 細節

- **`coverage` 有沒有別人用**：`uv.lock` 裡只有專案自己的開發相依和 `pytest-testmon` 依賴它；`src/`、`tests/`、`scripts/`、`pyproject.toml` 沒有 `import coverage`、`pytest-cov`、`--cov`。所以兩個都移除。
- `uv remove` 之後，`pyproject.toml`、`uv.lock` 和 `662e3b43f^`（TS-2 裝套件前）比對沒有差異。

## 檢查

| 檢查 | 結束碼 |
|---|---|
| `ruff check .` | 0 |
| `ruff format --check .` | 0 |
| `mypy` | 0（1857 個檔） |
| `lint-imports` | 0 |
| `pytest tests/infra/test_check_split.py test_run_pytest.py test_xdist_loadgroup.py` | 0（51 passed） |
| `scripts/check.py --all` | 見下方「全量檢查」 |

### grep `testmon`（排除 `docs/archive/`、TS-2 報告與計畫）

還有這些檔有 `testmon`：

- `docs/dev/上手-測試.md`：規格第 5 項要我補的那一句本身就有這個字。
- `docs/phases/PhaseTS-3計畫.md`：本段規格。
- 歷史紀錄：`docs/phases/PhaseCR-1b計畫.md`、`PhaseCR-1c計畫.md`、`PhaseE3b報告.md`、`PhaseTS-1計畫.md`，只是提到 TS-2。
- `docs/開發PM交接.md`：開發 PM 的交接。

程式、測試、設定、相依（`src/`、`tests/`、`scripts/`、`pyproject.toml`、`uv.lock`、`.gitignore`）都已經沒有。上面那些文件不在規格範圍裡，「不改其他」的保守做法是不動，見待 PM 決定 1。

## 全量檢查

（跑完後補）

## 待 PM 決定

1. **grep 驗收和其他文件**：規格第 5 項要補的句子本身含 `testmon`，和「grep 找不到」的驗收互相衝突；另外 CR-1b／CR-1c 計畫、E3b 報告、TS-1 計畫、`開發PM交接.md` 也有這個字。我只改了規格點名的檔，其他歷史文件和交接沒動。要不要把這些也算進例外（我的建議：算進例外，這些是歷史紀錄），或要我改寫，請 PM 決定。
