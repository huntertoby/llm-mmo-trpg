"""部署用的啟動與檢查（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.8；``docs/部署說明.md``）。

    uv run python scripts/deploy.py check    # 開服前的檢查（只檢查，不改任何東西）
    uv run python scripts/deploy.py server   # 啟動遊戲伺服器（照 [deploy] host／port）
    uv run python scripts/deploy.py bot      # 啟動 Discord Bot（scripts/discord_bot.py run）
    uv run python scripts/deploy.py tunnel   # 啟動 Tunnel（照 [deploy] tunnel_command）

機器相關的值都在設定檔：``config/deploy.local.toml``（沒有就讀 ``config/deploy.example.toml``；
``TRPG_DEPLOY_CONFIG`` 可指定別的檔）、``config/server.toml``、``config/bot.local.toml``。
這個腳本不下載、不安裝任何東西；Tunnel 工具由使用者自己裝。路徑一律 ``pathlib``，Windows 與 macOS
同一條指令（``scripts/start_*.ps1``／``.sh`` 只是包裝）。
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import subprocess
import sys
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trpg.api.server_config import ServerConfigError, load_server_settings
from trpg.bot.config import BotConfigError, load_bot_settings
from trpg.roguelite.save import default_save_dir
from trpg.server.account_config import AccountConfigError, load_account_settings

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / "config" / "deploy.local.toml"
EXAMPLE_CONFIG = ROOT / "config" / "deploy.example.toml"
CONFIG_ENV = "TRPG_DEPLOY_CONFIG"
CLIENT_INDEX = ROOT / "client" / "dist" / "index.html"
EXIT_PROBLEMS = 1
EXIT_CONFIG = 2

NO_TUNNEL = (
    "沒有設定 Tunnel 指令：在 config/deploy.local.toml 的 [deploy] 填 tunnel_command，例如\n"
    '  tunnel_command = ["cloudflared", "tunnel", "run", "trpg"]\n'
    "Tunnel 工具要自己先裝好並登入（見 docs/部署說明.md）。"
)


class DeploySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    tunnel_command: tuple[str, ...] = ()


class DeployConfigError(Exception):
    pass


def config_path(env: Mapping[str, str]) -> Path:
    override = env.get(CONFIG_ENV)
    if override:
        return Path(override)
    return LOCAL_CONFIG if LOCAL_CONFIG.is_file() else EXAMPLE_CONFIG


def load_deploy(path: Path) -> DeploySettings:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise DeployConfigError(f"無法讀取部署設定 {path}：{exc}") from exc
    try:
        return DeploySettings.model_validate(raw.get("deploy", {}))
    except ValidationError as exc:
        raise DeployConfigError(f"部署設定 {path} 不合法：{exc}") from exc


def command_for(name: str, settings: DeploySettings) -> list[str]:
    """子指令實際要執行的指令（``tunnel`` 沒設定＝空串列）。"""
    if name == "server":
        return [
            sys.executable,
            "-m",
            "trpg",
            "serve",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
        ]
    if name == "bot":
        return [sys.executable, str(ROOT / "scripts" / "discord_bot.py"), "run"]
    return list(settings.tunnel_command)


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def problems(settings: DeploySettings, env: Mapping[str, str]) -> tuple[list[str], list[str]]:
    """開服前的檢查：``(問題, 資訊)``。"""
    found: list[str] = []
    info: list[str] = []
    try:
        accounts = load_account_settings(env=env)
        if accounts.dev_mode:
            found.append("開發模式還開著：config/server.toml 的 [accounts] dev_mode 改成 false")
        save_dir = Path(env["TRPG_SAVE_DIR"]) if env.get("TRPG_SAVE_DIR") else default_save_dir()
        info.append(f"帳號資料夾：{accounts.accounts_dir(save_dir).resolve()}")
        info.append(f"世界存檔資料夾：{(save_dir / 'world').resolve()}")
    except AccountConfigError as exc:
        found.append(str(exc))
    try:
        server = load_server_settings(env=env)
        if not server.public_url:
            found.append(
                "沒有外部網址：config/server.toml 的 [network] public_url 填 Tunnel 給的網址"
            )
        else:
            info.append(f"外部網址：{server.public_url}")
        if settings.tunnel_command and not server.trusted_proxies:
            found.append(
                "有 Tunnel 但 trusted_proxies 是空的：登入限制會把所有人算成同一個 IP；"
                'Tunnel 跑在同一台電腦時填 ["127.0.0.1", "::1"]'
            )
    except ServerConfigError as exc:
        found.append(str(exc))
    if settings.tunnel_command and not _is_loopback(settings.host):
        found.append(f"經 Tunnel 對外時 host 建議用 127.0.0.1（現在是 {settings.host}）")
    if not settings.tunnel_command:
        found.append("沒有設定 tunnel_command（config/deploy.local.toml）")
    if not CLIENT_INDEX.is_file():
        found.append("前端還沒建置：pnpm -C client install 後 pnpm -C client build")
    try:
        # 讀真的環境時（env 是 os.environ）也讀 repo 根目錄的 .env（5E-2b 32.3）
        load_bot_settings(env=None if env is os.environ else env)
    except BotConfigError as exc:
        found.append(f"Bot 設定不完整（不影響伺服器）：{exc}")
    return found, info


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="部署：啟動與檢查")
    parser.add_argument("command", choices=["check", "server", "bot", "tunnel"])
    return parser


def main(
    argv: Sequence[str] | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    env: Mapping[str, str] | None = None,
    runner: object = None,
) -> int:
    environ = os.environ if env is None else env
    args = _parser().parse_args(argv)
    path = config_path(environ)
    try:
        settings = load_deploy(path)
    except DeployConfigError as exc:
        print(f"錯誤：{exc}", file=err)
        return EXIT_CONFIG
    if args.command == "check":
        found, info = problems(settings, environ)
        print(f"部署設定：{path}", file=out)
        for line in info:
            print(f"  {line}", file=out)
        for line in found:
            print(f"  ✗ {line}", file=out)
        if not found:
            print("  ✓ 全部檢查通過", file=out)
        return EXIT_PROBLEMS if found else 0
    command = command_for(args.command, settings)
    if not command:
        print(NO_TUNNEL, file=err)
        return EXIT_CONFIG
    print("執行：" + " ".join(command), file=out)
    run = runner if callable(runner) else subprocess.run
    result = run(command, cwd=ROOT, check=False)
    return int(getattr(result, "returncode", 0))


if __name__ == "__main__":
    raise SystemExit(main())
