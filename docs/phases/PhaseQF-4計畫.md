# Phase QF-4 計畫：三個慢測試加速

> 來源：專案 PM 轉使用者決定（2026-11-21）：「先放寬再加速（建議）」。
> 背景：HC-4d 推送時，有 3 個測試超過單一測試 300 秒的上限，worker 被收掉，推送被擋（`.claude/pm-logs/push-check-20261121-155813.log`）。現在先暫時放寬成 `@pytest.mark.timeout(600)`（6adbedef3）。這一段要把它們加速，再拿掉放寬。

## 範圍

只改這 3 個測試：

| 測試 | 單獨跑的秒數（2026-11-21） |
|---|---|
| `tests/skillgen/test_upgrade_topup.py::test_reaction_keywords_the_composer_cannot_carry[summon]` | 288 |
| `tests/roguelite/test_test_mode.py::test_run_with_equipment_plays_to_the_end_and_replays_the_same` | 222 |
| `tests/skillgen/test_player_text.py::test_player_check_texts_have_no_english_identifiers` | 220 |

1. **先找出慢在哪**：用 `cProfile` 或 `--durations` 加手動計時，報告寫出每個測試的熱點。
2. **加速**：目標是單獨跑時每個 **120 秒以下**。
   - 可以這樣做：
     - 共用 fixture（`scope="module"` 或 `"session"`，要確認沒有共享的可變狀態）；
     - 拿掉重複的組合：同一條分支只測一次；
     - 先篩掉一定不會命中的輸入，再跑昂貴的步驟。
   - **覆蓋的分支不能少**：改之前先列出測試檢查到的情況，改完後逐一對照，寫進報告。例如每個關鍵字、每種選項類型、每個階級、每個 assert 的對象。做法是在 `--cov` 或測試內部加計數，前後比對；計數只在 scratch 量，不進 repo。
   - 只改測試檔與測試 helper（`tests/`）。**不改 `src/`**。想動 `src/` 才能加速的，寫進報告「待 PM 決定」。
3. **拿掉放寬**：加速達標的測試，拿掉 `@pytest.mark.timeout(600)` 那一行。沒達標的就留著，在報告寫原因。

## 不做

- **不准改標 slow**，不准改 300 秒的預設上限、`pyproject.toml` 的 timeout，也不准改 `.claude/pm-workflow.json`。
- 不准改 `src/`、`content/`、`docs/design/`。

## 驗收

- 報告寫在 `docs/phases/PhaseQF-4報告.md`，要包含：
  - 每個測試改前、改後的秒數（單獨跑）；
  - 熱點分析；
  - 覆蓋對照表；
  - collected 的測試數改前、改後各是多少（只能多，不能少）。
- ruff、format、mypy 結束碼都是 0。
- 這 3 個測試檔整檔經看門狗跑，結束碼 0：`uv run python scripts/run_pytest.py -q <三個檔> -n 8`。
- 不用跑全量。這一段和 HC-5a 同時進行，兩段不改同一批檔案。
- 每項一個 commit。
