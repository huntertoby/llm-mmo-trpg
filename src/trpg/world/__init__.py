"""大世界的確定性規則（Phase 5；``docs/phases/Phase5計畫.md`` 第 2 節）。

地點圖移動、遇敵擲骰、隱藏地點感知判定、紮營、世界時鐘與天氣（5A-2 起）。全部是純函式：
``world_step(library, world, char, action, now) → StepResult(world, char, events)``；時間由呼叫端
傳入，本套件內不讀時間、不用 ``random``／``uuid4``／內建 ``hash()``、不呼叫 LLM。

依賴方向（import-linter）：可以匯入 ``trpg.shared``、``trpg.content``、``trpg.engine``、
``trpg.roguelite``；不得匯入 ``trpg.api``、``trpg.cli``、``trpg.sim``、``trpg.llm``、
``trpg.narrative``；下層套件不得匯入本套件。

模組：

- :mod:`trpg.world.clock`：時鐘（一天 30 分鐘、半天換天氣、台北 6 點刷新）。
- :mod:`trpg.world.rng`：世界亂數衍生（賽季種子:角色:串流:計數）。
- :mod:`trpg.world.state`：``trpg-world/3``、``trpg-char/5`` 的模型。
- :mod:`trpg.world.actions`：世界動作與事件。
- :mod:`trpg.world.weather`：各區天氣。
- :mod:`trpg.world.encounters`：遭遇的敵方陣容（遭遇表、營地混精英，5A-3）。
- :mod:`trpg.world.step`：:func:`world_step`（移動＋遇敵、事件擲骰、感知判定、紮營）。
- :mod:`trpg.world.events`：事件出現擲骰（依步數與種子，5B-1）。
- :mod:`trpg.world.threads`：線頭的有效、到期與上限（5B-1）。
- :mod:`trpg.world.battle`：遇敵開戰設定（地圖換皮、敵人依等級成長）與勝負回寫（5A-4）。
- :mod:`trpg.world.town`：撤退、城鎮休息、換技能、傳送（5A-4）。
- :mod:`trpg.world.common`：共用的內容與角色數值小工具（5A-4）。
- :mod:`trpg.world.replay`：世界動作日誌與重播。
- :mod:`trpg.world.save`：存檔格式與原子寫檔。
"""
