# 啟動Tunnel（Phase 5E-3；Windows PowerShell）。機器相關的值在設定檔，見 docs/部署說明.md。
# 用法（專案資料夾）：powershell -ExecutionPolicy Bypass -File scripts\start_tunnel.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
uv run python scripts/deploy.py tunnel
exit $LASTEXITCODE
