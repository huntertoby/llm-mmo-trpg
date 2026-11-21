# Phase QF-4b 計畫：護主配方加速（輸出不變）

> 來源：QF-4 報告最後的開發 PM 裁定 1、3、4；使用者決定「先放寬再加速（建議）」「好，三個都留，照加速段做」（專案 PM 轉，2026-11-21）。
> 原則：**只加速，輸出逐位元組不變。**

## 背景

QF-4 量到兩個測試仍然超過 120 秒，熱點都在 src 的組合器「護主」反應配方：

| 測試 | 單獨跑 |
|---|---|
| `test_upgrade_topup.py::test_reaction_keywords_the_composer_cannot_carry[summon]` | 約 272 秒 |
| `test_test_mode.py::test_run_with_equipment_plays_to_the_end_and_replays_the_same` | 約 210 秒 |

3 階起，每份草稿在最弱強度就已經不合格，組合器卻仍然試滿 8 × 100 次，每次約 40 份草稿。相關函式是 `_compose_reaction_recipe`、`_first_valid`、`_guardian_drafts`。QF-4 報告列了 a、b、c 三種修法。

## 範圍

1. **加速護主配方**（`src/trpg/skillgen/composer_*.py`）。從 QF-4 報告的 a／b／c 選一種或組合。
   - 不能改變亂數的取用次數與順序，也不能改變任何一份輸出。
   - 例如「最弱強度就不合格 → 整個配方提早放棄」這種改法，必須證明提早放棄前後，結果和亂數狀態都相同。否則就只能用不碰亂數的快取、預先篩選。
2. **`check_draft` 可以接受算好的 `draft_options`**（可做可不做）：做的話，不傳時行為照舊。
3. **拿掉放寬**：summon 和裝備重播單獨跑都在 120 秒以下時，拿掉它們的 `@pytest.mark.timeout(600)`。沒達標的就留著，在報告寫原因。
4. **一起量**：`tests/roguelite/test_test_mode.py::test_test_mode_refills_to_the_gear_inclusive_maximum`（`-n 8` 時 159 秒），記下改前、改後的秒數。

## 不做

- 不改標 slow，不改 300 秒的預設上限，不刪測試，也不縮小測試的覆蓋範圍。
- 不改 content 的值，不動 `docs/design/`。
- HC-5b 的常數搬家另外排一段。

## 驗收

- **輸出不變**，對照基準 commit，全部 different=0：
  - 組合器：recipe census 小樣本、`scripts/wish_coverage.py` 小樣本、挑選模式三選一的 48 格（照 HC-4b2 的比對法）。
  - 升級補足（topup）各關鍵字的輸出。
  - 434 招逐招預算。
  - 78 場戰鬥。
  - 閃現出題（照 HC-5a 的腳本）。
  - parity、CLI 快照不變。
- **秒數**：兩個目標測試和第 4 項的測試，各寫改前、改後的單獨秒數，並註明量的時候有沒有其他程序在跑。
- **靜態檢查**：ruff、format、mypy、lint-imports，結束碼都要是 0。
- **測試**：
  - 開發中經看門狗只跑相關測試。
  - **交件前全部 commit 之後**，在自己的 worktree 跑一次 `uv run python scripts/check.py`，再跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 每項一個 commit。報告寫在 `docs/phases/PhaseQF-4b報告.md`。
