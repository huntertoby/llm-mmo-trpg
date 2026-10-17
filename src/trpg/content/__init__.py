"""內容資料的 pydantic schema 與載入器。

- 實作階段：Phase 0 起（本階段提供載入器與 ``elements.yaml`` 範例 schema）。
- 資料本體放在專案頂層的 ``content/`` 資料夾（YAML／JSON），新增內容不需修改引擎程式。
- 內容 model 一律 ``extra="forbid"``、``frozen=True``，拼錯欄位就報錯。
"""
