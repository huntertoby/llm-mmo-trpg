#!/usr/bin/env sh
# 啟動Tunnel（Phase 5E-3；macOS）。機器相關的值在設定檔，見 docs/部署說明.md。
# 用法（專案資料夾）：sh scripts/start_tunnel.sh
set -e
cd "$(dirname "$0")/.."
exec uv run python scripts/deploy.py tunnel
