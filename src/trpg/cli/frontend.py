"""前端工具鏈：找出可用的 ``pnpm`` 指令（MAC-1）。

Node 24 以下隨附 ``corepack``；Node 25 起沒有，改用全域安裝的 ``pnpm``
（``npm install -g pnpm``），再退而用 ``npx`` 依 ``client/package.json`` 的 ``packageManager``
版本執行。三者都找不到時回傳 ``None``，由呼叫端決定略過或報錯。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

__all__ = ["CLIENT_DIR", "PNPM_INSTALL_HINT", "pnpm_command", "pnpm_version"]

CLIENT_DIR = Path(__file__).resolve().parents[3] / "client"
PNPM_INSTALL_HINT = "找不到 pnpm，請安裝 Node.js 20.19 以上並 `npm install -g pnpm`"


def pnpm_version(package_json: Path = CLIENT_DIR / "package.json") -> str | None:
    """``package.json`` 的 ``packageManager``（``pnpm@<版本>``）裡的版本。

    讀不到、不是 JSON 或不是 pnpm 時 ``None``。
    """
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    manager = data.get("packageManager") if isinstance(data, dict) else None
    if isinstance(manager, str) and manager.startswith("pnpm@"):
        return manager.removeprefix("pnpm@")
    return None


def pnpm_command(package_json: Path = CLIENT_DIR / "package.json") -> list[str] | None:
    """執行 pnpm 的指令前綴（之後接 ``-C client <指令>``）。

    依序找 ``corepack``（``corepack pnpm``）→ ``pnpm`` → ``npx``（``npx -y pnpm@<版本>``）；
    都沒有時 ``None``。回傳的是 ``shutil.which`` 解析出的完整路徑（Windows 的 ``pnpm.cmd``
    不經 shell 時只有完整路徑才能執行）。
    """
    if corepack := shutil.which("corepack"):
        return [corepack, "pnpm"]
    if pnpm := shutil.which("pnpm"):
        return [pnpm]
    if npx := shutil.which("npx"):
        version = pnpm_version(package_json)
        return [npx, "-y", f"pnpm@{version}" if version else "pnpm"]
    return None
