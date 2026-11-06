# Phase MAP-1 報告：dark_forest 被圍住的 2 格

## 1. 問題

用地圖檢查共用的移動規則（`trpg.content.maps.passable_grid` ＋ `reachable_from`：`blocks_move` 物件、牆壁、爬升上限）從雙方起始區做 BFS，全部 17 張地圖只有 `dark_forest` 有「可站立卻走不到」的格子，而且是**兩個互不相連的口袋**（斜對角），不是一塊 2 格：

| 格 | 北 | 東 | 南 | 西 |
|---|---|---|---|---|
| [4, 4]（有草叢） | 倒木 [4, 3] | 牆 [5, 4] | 牆 [4, 5] | 枯樹 [3, 4] |
| [5, 5]（有草叢） | 牆 [5, 4] | 枯樹 [6, 5] | 倒木 [5, 6] | 牆 [4, 5] |

（枯樹、倒木都可打壞／推倒，但沒打掉前誰都走不進去。）

## 2. 改動

因為是兩個獨立口袋，挪 1 根倒木只能開 1 格，所以**挪了 2 根**，各往旁邊移 1 格，保持原地圖的點對稱（以 (4.5, 4.5) 為中心）：

- 倒木 [4, 3] → [5, 3]
- 倒木 [5, 6] → [4, 6]

倒木數量（4 根）、半掩護數量、草叢、牆、枯樹都不變；倒木不擋視線，視線分佈不變。掩護位置各平移 1 格，仍貼著中央牆柱。

前（x 往右 0–9，y 往下 0–9；`#` 牆、`-` 倒木、`Y` 枯樹、`*` 被圍住的格、`.` 其他）：

```
   0123456789
3  ..#.-.....
4  ...Y*#....
5  ....#*Y...
6  .....-.#..
```

後：

```
   0123456789
3  ..#..-....
4  ...Y.#....
5  ....#.Y...
6  ....-..#..
```

## 3. 測試

- 新增 `tests/content/test_map_reachability.py`：對所有非 `test` 類型的地圖（16 張，含 boss、training）檢查沒有封閉的可站立格；`KNOWN_EXCEPTIONS` 目前為空（別張地圖沒有這個問題）。另一條專門確認 [4, 4]、[5, 5] 走得到。
- 改圖讓 AI 軌跡改變，三個「挑種子觸發特定事件」的測試照慣例換種子（腳本掃 0–29 挑第一個符合的）：
  - `test_reaction_events_3d3.py`：build_ranged／dark_forest 掩護射擊 4 → 2
  - `test_scene_ai.py`：穿甲箭穿過倒木 7 → 1
  - `test_summon_ai.py`：喚起骷髏並行動 1 → 4
- `RULE_HASHES`（只涵蓋實地地圖）與 CLI 快照不含 dark_forest，不需重算；兩檔在 main（含 6R-2）上照跑通過。

驗收：ruff check、ruff format --check、mypy、lint-imports 通過；`pytest tests/content tests/engine -n 4` 全過；`tests/cli/test_output_snapshots.py`、`test_field_buildings.py` 及其他引用 dark_forest 的 world／cli／sim 測試通過；`trpg battle --map dark_forest --seed 1` 跑完，`trpg battle replay` 重播驗證通過。

## 4. 待 PM 決定

1. 規格寫「挪 1 根倒木」，實際是兩個獨立口袋，挪 1 根只能開 1 格，所以挪了 2 根（點對稱）。若只想開一格或改用其他方式（例如換成移掉枯樹），請告知。
2. 平衡未跑模擬（只挪兩格掩護）；若要確認 dark_forest 勝率沒變，可排一次 `trpg sim maps --maps dark_forest`。
3. 跑 `tests/content tests/engine -n 4` 第一次時 `test_battle_content.py` 有 3 條載入錯誤訊息不符，單獨跑與重跑都通過，疑似當時 main 正在併入 6R-2 讀到半更新的檔案，非本段造成；若之後再出現可能是平行測試的偶發問題。
