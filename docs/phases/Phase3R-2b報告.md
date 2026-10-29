# Phase 3R-2b 報告｜狐火誘餌修正

規格：`docs/phases/Phase3R計畫.md` 4.4；設計：`docs/design/07-角色成長.md` 7.7 實作細節 6。

## 做了什麼

- `engine/reactions.py`：移除 `try_intercept` 裡「命中後」的 `_decoy_intercept`，改成 `take_decoy(ctx, attacker, target, skill_id=)`：敵方單體攻擊在**擲命中之前**，目標陣營有誘餌（依單位 ID 第一個）就發出 `attack_intercepted`（新欄位 `decoy=True`）並以 `decoy_hit` 讓誘餌消失，這次攻擊落空。不論原本會不會命中都算用掉。直接打誘餌本身不攔。
- 普攻（`_attack_once`，含穿透、連擊武器的每一下）與單體技能（`Cast.roll_one`，`shape.type == "single"`）都在擲命中前呼叫；技能路徑回傳一個不擲骰的落空 `AttackRoll`，所以不發 `attack_rolled`、不結算任何效果。
- 戰鬥紀錄：放出時「{施放者} 放出一團狐火誘餌」（`unit_summoned`，範本為誘餌）；攔下時「狐火誘餌引走了 {攻擊者} 的攻擊，隨即消散」；`summon_expired` 的 `decoy_hit` 不再另外印一行（避免重複）。
- `LOG_FORMAT` `/83` → `/84`（事件新增 `attack_intercepted.decoy`），字面值與 CLI 快照一併更新。
- 測試（`tests/engine/test_race_skills.py`）：40 個種子下普攻一律不擲命中、無傷害、誘餌消失；誘餌只用一次；敵人可直接打誘餌（正常擲命中）；單體技能同樣在擲命中前轉向；紀錄兩行文字。重播由既有 `test_race_battles`（狐族 AI 使用種族技後重播一致）涵蓋。

## 驗收

pytest：engine、narrative、api、content、roguelite 共 6004 通過；`-m "slow or not slow" tests/cli` 152 通過（快照已更新）；ruff、format、mypy、lint-imports 通過。skillgen 在第一輪（程式碼被意外還原前）全過，改動未碰其範圍，未重跑。vitest／build 未跑（前端未改，規格 4.4 也未要求）。

## 待 PM 決定

1. 預覽（`ctx.preview`）不套用誘餌：預覽仍顯示命中機率與傷害，不消耗誘餌（保守做法）。
2. 誘餌攔下的普攻若攻擊者在隱蔽中，仍算攻擊（移除隱蔽）；被攔下沒有「轉身」。
3. 穿透弩對後排每個目標、連擊武器的每一下各算一次單體攻擊，只有第一次被誘餌吃掉。
4. 範圍／錐形／線形技能不被誘餌攔（只攔 `shape.type == single`）；反應攻擊（藉機攻擊）走普攻路徑，會被攔。
5. 開發過程中發現工作樹的修改曾被不明原因還原一次（非我的指令），已重做並重跑全部測試。
