# BAL-2d 報告：形態幅度的兩點小修

## 1. 做了什麼

1. **整數四捨五入（half-up）**（`src/trpg/content/forms.py`）
   - `_gain`：`(value × 幅度 + 500) // 1000`，只作用於正值；0 與負值（代價）照原值。
   - `_less_taken`：減傷離 100% 的距離同樣四捨五入（最低 0）；弱點（> 100%）不動。
   - 天生武器傷害加成原本就在 `scaled_form_def` 內放大（BAL-2c 已用 `_gain`），這次一併改成四捨五入；骰子、射程、特性不變。
   - 引擎、HUD、卡片、預算器仍共用 `scaled_form_def`（經 `Ruleset.scaled_form`），沒有第二份算法。
   - 例：貓移動 +1 在幅度 1500 變 +2（原本 1）、狼人同；1450 仍是 +1。
2. **完整技能的 +120‰ 加在形態幅度上**（`src/trpg/skillgen/complete.py` 的 `_strength_knobs`）
   - `enter_form` 效果多一個旋鈕 `magnitude_permille`，級距用 `rules.form_magnitudes`（每 50‰）。

## 2. 結果

完整技能後的預算分數增加：

| 階 | 技能 | 幅度 | 增加 |
|---|---|---|---|
| 1 | 熊、貓、巨鵰、狼人 | 1000 → 1100 | +100‰ |
| 2 | 惡魔、龍、元素化身、巨人、影子、樹人 | 1000 → 1150 | +150‰ |

- 1 階形態的下一格（1150）會超出預算窗（`budget.over`），所以停在 +100‰，達不到 +120‰。這是「達上限並記錄」的情況；完整技能在此之後沒有別的旋鈕（形態沒有冷卻等可減的代價）。
- 測試 `test_form_skill_gets_a_bigger_form_magnitude`（10 招）：幅度變大、在級距上、驗證通過；增加 ≥ 120‰，否則斷言下一格會 `budget.over`。
- 卡片＝實戰：沿用 BAL-2c 的 `test_bear_in_battle_matches_the_card` 等（卡片、HUD、引擎同一函式）；新增 `test_integer_fields_round_half_up_and_weapon_damage_scales`。

## 3. 夾具與紀錄格式

- `tests/skillgen/fixtures/refactor_3wr2.json`：重產，只有 `complete` 區 10 個形態技能（`skill_form_*` 的 10 招）的雜湊改變，其他技能、`flash`、`retier` 皆未變。
- 戰鬥紀錄結構未改（只是數值不同），不遞增版本（維持 /90）。

## 4. 驗收

- `ruff check`、`ruff format --check`、`mypy`、`lint-imports`：通過。
- pytest（`-n 8`）：`tests/engine` 形態相關 6 個檔、`tests/skillgen`、`tests/narrative`、`tests/roguelite`：4452 通過、14 略過；唯一失敗是上述夾具（已重產），重產後該檔未再單獨重跑全部，僅形態雜湊更新。
- swamp 種子 7 重播：60 個動作、223 個事件，最終狀態一致。

## 5. 待 PM 決定

1. 1 階形態（熊、貓、巨鵰、狼人）完整技能只能 +100‰（下一格超出預算窗）。若要 +120‰，可：把形態幅度級距改成 20‰ 一格（1120 在窗內？未驗證）、或接受現狀。
2. 2 階形態一次 +150‰（級距 50‰ 太粗，剛好踩到上限）；同樣可由較細的級距解決。
