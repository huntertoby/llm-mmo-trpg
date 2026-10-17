"""LLM 整合：``LLMClient`` 介面、``MockLLMClient``、版本化 prompt、輸出 schema、評估集。

- 實作階段：Phase 3 起。
- 守則：LLM 只能提議，不能裁決；輸出先經 pydantic 驗證，再由引擎檢查合法性。
  模型 ID 寫在設定檔；所有測試不需網路與 API 金鑰。
"""
