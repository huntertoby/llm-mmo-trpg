"""``trpg.cli.frontend.pnpm_command``（MAC-1）：corepack → pnpm → npx → None。"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from trpg.cli.frontend import pnpm_command, pnpm_version


def _which(available: set[str]) -> object:
    def which(name: str) -> str | None:
        return f"/fake/bin/{name}" if name in available else None

    return which


@pytest.fixture
def package_json(tmp_path: Path) -> Path:
    path = tmp_path / "package.json"
    path.write_text('{"packageManager": "pnpm@12.14.0"}', encoding="utf-8")
    return path


def test_prefers_corepack(monkeypatch: pytest.MonkeyPatch, package_json: Path) -> None:
    monkeypatch.setattr(shutil, "which", _which({"corepack", "pnpm", "npx"}))
    assert pnpm_command(package_json) == ["/fake/bin/corepack", "pnpm"]


def test_falls_back_to_global_pnpm(monkeypatch: pytest.MonkeyPatch, package_json: Path) -> None:
    monkeypatch.setattr(shutil, "which", _which({"pnpm", "npx"}))
    assert pnpm_command(package_json) == ["/fake/bin/pnpm"]


def test_falls_back_to_npx_with_pinned_version(
    monkeypatch: pytest.MonkeyPatch, package_json: Path
) -> None:
    monkeypatch.setattr(shutil, "which", _which({"npx"}))
    assert pnpm_command(package_json) == ["/fake/bin/npx", "-y", "pnpm@12.14.0"]


def test_npx_without_package_json_uses_latest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(shutil, "which", _which({"npx"}))
    assert pnpm_command(tmp_path / "missing.json") == ["/fake/bin/npx", "-y", "pnpm"]


def test_none_when_nothing_installed(monkeypatch: pytest.MonkeyPatch, package_json: Path) -> None:
    monkeypatch.setattr(shutil, "which", _which(set()))
    assert pnpm_command(package_json) is None


def test_pnpm_version_reads_real_package_json() -> None:
    version = pnpm_version()
    assert version is not None and version[0].isdigit()


def test_pnpm_version_ignores_other_managers(tmp_path: Path) -> None:
    path = tmp_path / "package.json"
    path.write_text('{"packageManager": "yarn@4.0.0"}', encoding="utf-8")
    assert pnpm_version(path) is None
    path.write_text("not json", encoding="utf-8")
    assert pnpm_version(path) is None
