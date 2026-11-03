"""``scripts/deploy.py`` 與啟動腳本（Phase 5E-3；計畫 31.8）。不啟動任何程序。"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("deploy_script", ROOT / "scripts" / "deploy.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["deploy_script"] = module
    spec.loader.exec_module(module)
    return module


def _configs(tmp_path: Path, *, tunnel: bool, ready: bool) -> dict[str, str]:
    deploy = tmp_path / "deploy.toml"
    command = '["mytunnel", "run"]' if tunnel else "[]"
    deploy.write_text(
        f'[deploy]\nhost = "127.0.0.1"\nport = 8135\ntunnel_command = {command}\n',
        encoding="utf-8",
    )
    server = tmp_path / "server.toml"
    server.write_text(
        f"[accounts]\ndev_mode = {'false' if ready else 'true'}\n"
        f'[network]\npublic_url = "{"https://trpg.example.com" if ready else ""}"\n'
        f"trusted_proxies = {'["127.0.0.1"]' if ready else '[]'}\n",
        encoding="utf-8",
    )
    return {
        "TRPG_DEPLOY_CONFIG": str(deploy),
        "TRPG_SERVER_CONFIG": str(server),
        "TRPG_SAVE_DIR": str(tmp_path / "saves"),
        "TRPG_BOT_CONFIG": "",
    }


def test_check_lists_problems(tmp_path: Path) -> None:
    out = io.StringIO()
    code = _script().main(
        ["check"], out, io.StringIO(), _configs(tmp_path, tunnel=True, ready=False)
    )
    text = out.getvalue()
    assert code == 1
    assert "開發模式還開著" in text and "public_url" in text and "trusted_proxies" in text
    assert "帳號資料夾" in text and str((tmp_path / "saves" / "accounts").resolve()) in text


def test_check_passes_server_items_when_ready(tmp_path: Path) -> None:
    out = io.StringIO()
    _script().main(["check"], out, io.StringIO(), _configs(tmp_path, tunnel=True, ready=True))
    text = out.getvalue()
    assert "開發模式還開著" not in text and "public_url 填" not in text
    assert "trusted_proxies 是空的" not in text and "https://trpg.example.com" in text


def test_tunnel_without_command_exits_2(tmp_path: Path) -> None:
    err = io.StringIO()
    code = _script().main(
        ["tunnel"], io.StringIO(), err, _configs(tmp_path, tunnel=False, ready=True)
    )
    assert code == 2 and "tunnel_command" in err.getvalue()


def test_commands_built_from_config(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    class Done:
        returncode = 0

    def runner(command: list[str], **kwargs: Any) -> Done:
        del kwargs
        calls.append(command)
        return Done()

    env = _configs(tmp_path, tunnel=True, ready=True)
    script = _script()
    for name in ("server", "bot", "tunnel"):
        assert script.main([name], io.StringIO(), io.StringIO(), env, runner) == 0
    server, bot, tunnel = calls
    assert server[1:] == ["-m", "trpg", "serve", "--host", "127.0.0.1", "--port", "8135"]
    assert bot[-1] == "run" and bot[-2].endswith("discord_bot.py")
    assert tunnel == ["mytunnel", "run"]


def test_start_scripts_wrap_deploy() -> None:
    for name in ("server", "bot", "tunnel"):
        for ext in ("ps1", "sh"):
            text = (ROOT / "scripts" / f"start_{name}.{ext}").read_text(encoding="utf-8-sig")
            assert f"scripts/deploy.py {name}" in text


def test_example_config_and_local_ignored() -> None:
    script = _script()
    settings = script.load_deploy(ROOT / "config" / "deploy.example.toml")
    assert settings.tunnel_command == () and settings.host == "127.0.0.1"
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.local.*" in gitignore
