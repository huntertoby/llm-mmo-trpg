# 階段 SK-3d 報告：推擊、絆倒的修正規則條件也算利用

> 2026-11-19，實作者。依據：玩法交接 4.1.33（SK-3c 待決 3）。分支 `worktree-agent-a9144c27c5b790848`（先 `git merge main`，是快轉）。不 push。

## 做了什麼（commit `878d7d37a`）

- `battle._do_shove`、`_do_trip`：對抗**之前**用 `rule_exploits` 判斷（`modifiers.SHOVE`／`TRIP`，對目標），對抗成功、效果結算後交給 `report_exploits`；對抗失敗不算。推得動與否照 SK-3c 的「作用在目標上」判斷（推不動的 `push_resisted`、`move_blocked` 不算；撞牆有撞擊傷害算）。「一筆」的單位照 SK-3c。
- 目前 `CHANGE_TARGETS` 裡條件看目標的改變，能套用在推擊上的只有 `push_distance_delta`；**絆倒、互動沒有任何一種**。絆倒照樣接了（接線測試用一條直接組出來的假想規則），**互動沒接**：沒有規則的條件會看互動的目標。
- `LOG_FORMAT` `/132 → /133`（`戰鬥紀錄格式變更.md` 加一條；測試字面值 8 檔＋4 個 `endswith`）；`上手-引擎戰鬥結算.md` 第 56 點補一行。

## 測試與檢查

| 指令 | 結束碼 |
|---|---|
| `ruff check src tests scripts` | 0 |
| `ruff format --check src tests` | 0 |
| `mypy`（1704 檔） | 0 |
| `lint-imports`（14 kept） | 0 |
| 新測試 `tests/engine/test_exploit_maneuvers_sk3d.py`（5：推擊對抗成功算、推擊對抗失敗不算、推擊的規則不套用在絆倒、絆倒成功算、絆倒失敗不算） | 0 |
| 引擎相關（exploit、modifier、determinism、clone、版號字面值、maneuver 等，543） | 0 |
| CLI 版號字面值 6 檔（43） | 0 |
| 戰鬥不變比對 60 場（同 SK-3c 腳本，比 `11065f916`） | `battles=60 events=23897 different=0` |

## 待 PM 決定

1. 絆倒目前沒有任何規則能讓它算利用（`CHANGE_TARGETS` 不允許條件看目標的改變套用在絆倒）；程式已接好，等之後有這種改變才會生效。
2. 若 WC-2 也升 `LOG_FORMAT`，合併時要再往上排一號（協調者已說由他處理）。

## 開發 PM 裁定（2026-11-19）

合併：main（--no-ff）。不變比對 different=0；`LOG_FORMAT` /133 接受。互動沒有條件看目標的改變，不用接，照 4.1.33。
待決：絆倒的接線已做好，但目前沒有任何內容能讓「條件看目標」的改變套用在絆倒上，所以實際上不會觸發。要不要讓 `modifier_changes.yaml` 的某種改變能套用在絆倒，屬於內容設計，沒有需求前不做；有新規則時再開。
