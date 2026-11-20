# Phase X10-3c 計畫：×10 漏換（姿態進入代價）與註解

> 來源：`docs/phases/PhaseX10-3a報告.md` 待決 3、6 與開發 PM 裁定。
> 小段。同時有 X10-3b 在改卡片文字（`src/trpg/api/skill_cards.py`、`src/trpg/narrative/skills.py`）和 `client/`，這段不要動那些檔。

## 範圍
1. `skillgen/flash_ops.py` 的 `_entry_cost`（姿態「進入代價 ±1」「沉勢」）：法力、耐力一次改的量和下限都改成 × `quantity_scale`，冷卻和 AP 照舊。`flash_templates.yaml` 這兩條的文字一起改。parity 夾具照標準程序重產，先預測會變哪些鍵，再逐鍵核對。
   - 另外再掃一遍 `skillgen/flash_*.py`，看還有沒有同類「法力、耐力 ±1」沒乘倍率的地方。有就一起改，列在報告。
2. 程式 docstring、YAML 註解裡的舊單位說法，例如 `engine/events/rules.py` 的「HP 留在 1」、`core.yaml` 註解裡的「14＝1 階」，改成新單位。只改文字，不改程式。

## 驗收
- 第 1 項要有回歸測試：scale 10 時，進入代價一次改 10、最少留 10。
- 戰鬥不變比對 different=0。這段只動閃現的生成，不該改到既有戰鬥。
- ruff、format、mypy、lint-imports、`trpg content check` 都要 0。
- 交件前，所有目錄的非 slow 測試各跑一輪；另外跑 `-m slow tests/skillgen/test_refactor_parity.py tests/cli`。
- 每項一個 commit。報告寫在 `docs/phases/PhaseX10-3c報告.md`。
