# Phase OB-4｜#150：入門期的戰鬥閘與活動限制

> 來源：`docs/design/21-探索地圖與城鎮.md` 21.5 #150 第 7 點與第 9 點「入門期的敵人」「入門期能做的事」（**以它為準**）、`docs/玩法決定紀錄.md` #150。前置：OB-1、OB-2（報告 `docs/phases/PhaseOB-1報告.md`、`PhaseOB-2報告.md`；`opening_gate` 的結構與 `STARTER_STEPS` 常數在裡面）。
> 盤點：共用筆記 `C:\Users\tobby\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_1dc515fa-6fa4-4841-956e-bdff26ae2844\盤點-150與147.md` 第 1.1（第 7 點兩列）、4.3、第 6 節 Q2、Q3。

「入門期」＝`char.opening is not None` 且尚未正式選定（`stage` 不是 `chosen`）。

## PM 決定（不要再問）

| 項目 | 決定 |
|---|---|
| 入門期的敵人 | 新手第 1、2 步以外的巡邏、節點遭遇**不顯示、不接觸**（不是「顯示但打不了」） |
| 第 3 步固定戰（雨中梯田） | 正式選定後才開 |
| 接任務 | 可以接；任務的戰鬥與給招的獎勵要等正式選定 |
| 可以做 | 走動、對話、傳送、改外觀、買賣、換防具、休息、紮營、用道具、不開戰也不給招的情境判定；手動配點與重配；防具（頭、身、手、腳）的打造、強化、重骰、指定詞條 |
| 不開放 | 雇傭兵、聯賽、賽季 Boss、誓約、換技能；會開戰或給招的情境判定、事件解法、機遇 |
| 被擋時 | 回應要帶玩家看得懂的原因（繁體中文，一句），文字集中在一處，OB-5／6 會再調 |
| 畫面資料 | 伺服器給前端的敵人、可互動項目清單要和實際能不能碰到一致（不顯示的就不要出現在畫面資料裡） |

## 範圍外

- OB-3（另一個 agent 平行在做）：免費重選、閃現限制、配點教學、溶掉與傳承、4 級清 `opening`、示範招、推薦端點——**不要改 `src/trpg/world/opening_choice.py`、`quests.py` 的三選一、`growth.py` 的閃現、`api/world_range*.py`、`api/world_pregen.py`、`content/world/newcomer.yaml`**。`src/trpg/world/opening.py` 只能動 `opening_gate` 相關的部分，改動越小越好。
- **不改 API schema**（不重產 `client/openapi.json`、`schema.d.ts`）；若非加欄位不可，停下來寫進報告回報。不改前端。
- 不動 `src/trpg/engine/`、`src/trpg/roguelite/`；不調敵人數值與地圖內容。

## 交付項目

1. **盤點現況**：先對照 OB-1、OB-2 已做的閘門（動作白名單／黑名單、防具限制等），在報告列出 21.5 第 7、9 點每一項目前「已擋／已放行／未處理」，只補未處理的。
2. **巡邏與實地敵人**：`world/field_enemies.py` 的接觸判定與給畫面的清單，入門期只留新手第 1、2 步的敵人。
3. **節點遭遇**：移動時的遭遇表在入門期不觸發（`world/step.py` 的移動路徑）。
4. **第 3 步固定戰與任務戰鬥**：入門期不開；任務可接，戰鬥步驟與給招獎勵要等正式選定。
5. **會開戰或給招的事件**：情境判定、事件解法、機遇中會開戰或給招的選項在入門期擋下（不開戰也不給招的照常）。
6. **不開放的系統**：雇傭兵、聯賽、賽季 Boss、誓約、換技能在入門期擋下並回原因。
7. 需要時把 `WORLD_RULES_VERSION` 加一（OB-3 也可能加，合併時由 PM 對齊；報告寫明你有沒有動）。

## 受影響的既有功能

見盤點 4.3：`tests/world/test_field_things.py`、`test_three_way.py`、`test_enemy_smoke.py`、`tests/content/test_cloud_fields.py`、`test_field_spawn_flags.py`、`tests/world/test_dispatch.py`。所有新判斷以入門期為前提；舊角色（`opening is None`）、已正式選定的角色、roguelite 行為不變。

## 行為一致測試

- 表格測試，**實際跑世界動作**：入門期角色在新手區各地圖走動——第 1、2 步的敵人碰得到並開戰；其他巡邏不在畫面清單裡、走過去不開戰；節點移動不觸發遭遇；第 3 步固定戰開不了。正式選定後同一路線全部恢復。
- 每個「不開放」的系統各一筆：入門期被擋且有原因、選定後可用。
- 畫面資料與實際一致：畫面清單裡的每個敵人都碰得到，不在清單裡的都碰不到。
- 舊角色同種子走同一路線，事件列表與改前相同。
- 世界日誌重播一條入門期流程。

## 驗收條件

- `ruff check`、`ruff format --check`、`uv run mypy`、`lint-imports` 通過。
- `tests/world`、`tests/api`、`tests/content`、`tests/narrative`、`tests/server`、`tests/test_architecture.py` 通過。`tests/api/test_world_dev_boss.py::test_dev_boss_rehearses_to_the_boss_charge` 是已知不穩定的測試，失敗時單獨重跑確認即可，不要改它。
- 一場戰鬥 `--log-json` ＋ `replay` 通過。

## 報告

`docs/phases/PhaseOB-4報告.md`：逐條驗收、21.5 第 7、9 點的逐項對照表、被擋時的原因文字清單、版號、待 PM 決定（規格沒列到的動作照「會開戰或給招就擋、其餘放行」處理並列出）。
