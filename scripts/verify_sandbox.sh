#!/usr/bin/env bash
# 只給 Claude 雲端工作區用的驗證腳本（無法連 PyPI、無法 uv sync 的環境）。
# 一般開發請用：uv run python scripts/check.py
#
# 本腳本設定環境變數後執行同一個 scripts/check.py：
#   - pytest 與 mypy 各在獨立的 uv tool 環境，用 PYTHONPATH 讓它們看到系統的 pydantic／PyYAML，
#     並把 pytest 的 site-packages 給 mypy（讓測試檔的 `import pytest` 有型別）。
#   - 工作區沒有 types-PyYAML，借用 pyright 內附的 typeshed PyYAML stub 給 mypy（MYPYPATH）。
#   - 工作區沒有 import-linter，check.py 會印出略過警告（由 tests/test_architecture.py 保底）。
set -euo pipefail

cd "$(dirname "$0")/.."

DIST=/usr/local/lib/python3.13/dist-packages
PYTEST_SITE=$(ls -d /root/.local/share/uv/tools/pytest/lib/python3*/site-packages | head -n1)
YAML_STUBS=$(ls -d /root/.local/share/uv/tools/pyright/lib/python3*/site-packages/pyright/dist/dist/typeshed-fallback/stubs/PyYAML | head -n1)

export PYTHONPATH="src:$DIST:$PYTEST_SITE"
export MYPYPATH="$YAML_STUBS"
echo "PYTHONPATH=$PYTHONPATH"
echo "MYPYPATH=$MYPYPATH"

exec /usr/bin/python3 scripts/check.py
