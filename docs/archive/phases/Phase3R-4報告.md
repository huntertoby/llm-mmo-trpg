# Phase 3R-4 報告｜鱗族被動改版（#68）

## 做了什麼
- 規則 `free_move_on`（引擎裡本來沒有效果）改名為 `surface_move_bonus`（參數 `surfaces`、`amount`）；`content/races.yaml` 鱗族「流線身形」改為「回合開始時站在水或冰面上，這回合移動 +1；在冰面上不滑倒。」（`surfaces: [water, ice]`、`amount: 1`），刪掉「不花額外點數」半句。
- `engine/rules/race.py` 新增 `surface_move_bonus()`；`slip_immune` 改讀 `surface_move_bonus`（冰面不滑倒維持）。
- `move_points_for_turn` 多一個選填的 `surface` 參數；`turns.py` 新增 `_turn_move_points`，回合開始（含維持費不足後的重算）以腳下那一格的表面計算。+1 只進這回合的 `move_points`，回合中離開水面不收回、下回合重新判定。召喚物沿用不傳表面（無種族）。
- `LOG_FORMAT` `/86` → `/87`（`TurnStarted.move_points` 語意改變）；`docs/phases/戰鬥紀錄格式變更.md` 加 `/87` 條目；所有測試字面值（8 個檔案、3 個 `endswith("/86")`）已更新。
- 測試：`tests/engine/test_race_passives.py` 新增表格測試（站水／冰／無表面／油 × 鱗族／無種族／矮人）、回合中離開不收回、下回合不重複給；冰面不滑倒測試原樣保留；封閉清單覆蓋測試改名。

## 驗收
- ruff check／format、mypy、lint-imports：全過。
- pytest（`-m "(slow or not slow) and not llm"`）：tests/engine＋narrative 4044 過（3 個 LOG_FORMAT 字面值失敗已修）；修正後 engine 三檔、api、content、roguelite 共 2170 過；tests/cli 155 過。CLI 快照無需更新。
- 前端夾具重新匯出：無差異（未動 client）。
- 未跑完整 `scripts/check.py`、重播以外的全量模擬。

## 待 PM 決定
1. 規則 ID 由 `free_move_on` 改名 `surface_move_bonus`（舊名已無作用，內容檔無其他引用）；若希望保留舊名請告知。
2. 站在「水」判定只看腳下格的表面 `Surface.WATER`／`ICE`，不含水地形（terrain）；規格寫「看那一格的表面」，照此。
3. 紀錄格式遞增到 `/87`，舊 `/86` 紀錄不可重播（依 3T-2 策略）。
