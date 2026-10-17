"""純確定性規則引擎：格子、單位、行動、判定、效果佇列與事件。

- 實作階段：Phase 1 起（Phase 0 只建立空殼）。
- 介面：``resolve(state, action, rng) -> (state, events, pending)``，相同種子與輸入必得相同結果。
- 依賴限制：不得匯入 ``trpg.llm``、``trpg.narrative``、``trpg.api``、``trpg.roguelite``、
  ``trpg.sim``、``trpg.skillgen``、``trpg.cli``。
- 確定性：禁止呼叫 LLM、讀取時間、使用 ``random`` 模組與 ``uuid4``；亂數只用傳入的
  ``trpg.shared.rng.Rng``。
"""
