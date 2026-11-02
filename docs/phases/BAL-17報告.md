# BAL-17 報告：雙屬性武器的「跟主屬性」與候選偏離數

## 改了什麼

1. `trpg.skillgen.candidates.follows_attr`：武器有兩個不同的縮放屬性、且主角最高屬性是其中之一時，非武器技（法術）改看「技能的縮放屬性（含第二屬性）是否落在武器的兩個屬性內」。魔導劍力量最高時，力量與智力的法術都算同路線。並列最高照舊（`top_attribute` 不變）；最高屬性不在武器內、單屬性武器、武器技的判定都不變。`offers.py` 的 `off_route`、完整版與白板版候選產生器共用同一個函式，所以判定一致。
2. 找不到同路線技能時的放寬順序（`candidates.py` 與 `whiteboard_candidates.py`）：原本某個關鍵字有技能但屬性不合時，會直接拿它當備選，不再試其他關鍵字。改為「加深／橋接／新方向」各把所有要試的關鍵字合成一串，先找屬性合乎偏好的，整串都沒有才放寬屬性取第一個備選。`_Search.find` 改回傳「是否符合偏好」，技能是否登記進 `taken` 由 `_first` 決定。候選的 `fallback` 旗標語意不變。

## 量測（第一次與第二次升級三選一，白板模式，種子 0～49，共 100 組）

| 開局 | 前 平均／最多 | 後 平均／最多 |
|---|---|---|
| 魔導劍，力量 14，電爆＋暗影彈（charged＋concealed） | 1.35／3 | 1.00／1 |
| 魔導劍，預設配點 | 1.33／2 | 1.00／1 |
| 單手劍，預設配點 | 1.56／2 | 1.00／1 |
| 火焰法杖，預設配點 | 2.00／2 | 1.00／1 |

完整技能模式（`candidates.whiteboard: false`，一組要 3～40 秒）抽 8 個種子的魔導劍：前 2,2,1,2,2,1,1,1（平均 1.5），後 8 個全是 1。單屬性武器沒有變差，兩把都從 1.5～2 降到 1。

## 快照與種子測試

- `tests/skillgen/fixtures/refactor_3wr2.json`：測試通過，快照沒變，沒有重產。
- 候選取法改變後挑種子的測試重挑（斷言沒改）：`tests/roguelite/helpers.py` 的 `VICTORY` 由 `("build_fire", 2)` 改 `("build_fire", 1)`（種子 0～11 勝利的有 0、1、3、4、6、10），影響 test_progress、test_save、cli 的 run 測試；`tests/roguelite/test_flash_run.py` 的 `SEED` 由 2 改 3（0、1 抽不到可傳承的技能而跳過）。
- 新測試：`tests/skillgen/test_dual_weapon_follow_bal17.py`（4 個：雙屬性武器的法術同路線、其他屬性仍偏離、單屬性武器不變、魔導劍開局偏離 ≤ 2 且平均 ≤ 1.5）。

## 檢查

ruff check、ruff format --check、mypy（939 檔）、lint-imports（7 契約全過）通過；pytest：tests/skillgen 3325 passed 14 skipped、tests/roguelite 與 tests/api 550 passed、tests/cli 135 passed；`trpg battle --map swamp --seed 7` 重播一致（88 動作、313 事件）。

## 待 PM 決定

- 「雙屬性武器」只認武器的兩個縮放屬性（`secondary_scaling_attr`）；其他雙屬性武器（例如匕首敏捷／力量、拳套）也一併套用，沒有只限魔導劍。
- 法術判定改成「技能的第二縮放屬性也算」（雙屬性技能）；原本只看主縮放屬性。
- 新方向（偏離）的候選仍固定要求「不跟主屬性」；放寬屬性時偏離張數可能多於 1，但本次所有量測都是 1。
- 完整技能模式的候選產生很慢（每組 3～40 秒，改動前就是），不在本次範圍。
- 沒動開局配點。
