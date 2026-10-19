"""本機 HTTP API（Phase 3-2：FastAPI；多人 WebSocket 於 Phase 6）。

- ``app``：``create_app()``；``routes``：端點；``sessions``：戰鬥工作階段；``presenter``：我方視角
  的回應；``schemas``：請求與回應模型。
- 不得匯入 ``trpg.cli``（import-linter 合約）；``trpg serve`` 由 CLI 匯入本套件啟動。
"""
