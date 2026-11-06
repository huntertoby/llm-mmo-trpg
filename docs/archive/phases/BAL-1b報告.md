# BAL-1b 報告：套用靈感數值（每勝 2 點）

依玩法 PM 決定（204014e9，06 6.34.2）：`content/flash_templates.yaml` 的 `insight_per_win: 1 → 2`（註解註明 BAL-1、原型專用）；`insight_start`、`insight_preboss` 維持 0。未改規則、引擎、其他 content 區塊。

## 改了哪些測試
- `tests/sim/test_flash_economy.py`：`test_defaults_equal_current_behavior`、`test_with_economy_does_not_touch_original`、`test_parse_economy_product_and_defaults`——意圖是「預設等於 content」，改成讀 `lib.flash.rules` 的值，不寫死。
- `tests/api/test_flash_api.py`：模組常數 `INSIGHT_PER_WIN` 取自 content；`hero_reports_insight_rules`、`preview...`、`flash_then_pick` 的期望改用它（開啟後剩 `INSIGHT_PER_WIN - 1`）；`flash_then_pick` 末段「沒點了應 422」改為明確把 session 的 insight 設成 0，不依賴每勝點數。
- `tests/roguelite/test_flash_run.py`：`..._each_win_gives_one` 改名 `..._gives_the_configured_points`，只比對 content 值；`a_flash_costs_one_point...` 與 `flash_needs_points...` 開頭明確把 insight 設為 1（測「點數不夠」情境，不依賴每勝點數）。
- `tests/sim/test_flash_balanced_policy.py`：`_final` 新增 `win` 參數（用 `with_economy` 明確指定每勝點數）；spread 測試與決定性測試固定用 `win=1`。

## 值得 PM 注意
每勝 2 點時，`balanced` 與 `none` 兩種閃現策略在 seed 1–8 結果完全相同（閃過的技能數、次數皆同），原本「balanced 比 none 閃更多種技能」的差異只在點數吃緊時出現。測試因此固定在 `win=1` 驗證策略本身；平衡上若要比較策略差異，需在點數較緊的設定下做。

## 驗收
- CLI 快照：未受影響（tests/cli 156 passed，未用 UPDATE_CLI_SNAPSHOTS）。
- 前端夾具：`export_client_fixtures.py` 重產後無差異；vitest 1175 passed。
- `trpg run auto --seed 3 --flash-policy balanced`：正常結束（第 5 場失敗，屬正常結局）；4 場勝利取得 8 點靈感，用掉 7 點（含重閃/退還），剩 1，共閃現 6 次。
- ruff check、ruff format --check、mypy、lint-imports 皆通過；pytest：roguelite、sim、api、content、skillgen 5928 passed／14 skipped，cli 156 passed。
