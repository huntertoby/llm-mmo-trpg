"""數值工坊測試共用：暫存的 git repo（**絕不**對真的主資料夾或 worktree 寫回、commit）。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from trpg.api.tuning.service import TuningService
from trpg.content.library import ContentLibrary
from trpg.content.loader import bundled_content_dir


def git(root: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=True, encoding="utf-8"
    )
    return done.stdout


@pytest.fixture(scope="session")
def repo_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """``content/`` 的複本＋``git init -b main``＋一筆初始 commit（session 共用，測試各自複製）。"""
    root = tmp_path_factory.mktemp("tuning_repo")
    shutil.copytree(bundled_content_dir(), root / "content")
    git(root, "init", "-q", "-b", "main")
    hooks = root / ".no-hooks"
    hooks.mkdir()
    for key, value in (
        ("user.name", "Tuning Test"),
        ("user.email", "tuning@example.invalid"),
        ("core.autocrlf", "false"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", hooks.as_posix()),
    ):
        git(root, "config", key, value)
    git(root, "add", "content")
    git(root, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def repo(repo_template: Path, tmp_path: Path) -> Path:
    """這個測試自己的 repo（從範本複製）。"""
    root = tmp_path / "repo"
    shutil.copytree(repo_template, root)
    git(root, "config", "core.hooksPath", (root / ".no-hooks").as_posix())
    return root


@pytest.fixture
def repo_service(repo: Path, tmp_path: Path, content_library: ContentLibrary) -> TuningService:
    """寫回對象是暫存 repo 的服務（存檔資料夾也在暫存區）。"""
    service = TuningService(repo / "content", tmp_path / "saves", content_library)
    assert service.git is not None and service.git.root.resolve() == repo.resolve()
    return service


@pytest.fixture
def read_service(tmp_path: Path, content_library: ContentLibrary) -> TuningService:
    """讀專案內建 ``content/`` 的服務：只用來列對象、驗證、模擬，**不寫回**（寫回測試用
    :func:`repo_service`）。"""
    service = TuningService(bundled_content_dir(), tmp_path / "saves", content_library)
    service.git = None  # 保險：PM 在主資料夾（main）跑測試時也不可能寫回真的 content/
    return service
