"""數值工坊用的 git（NW-1a A6，規格 5.3）：一律用參數陣列呼叫 ``git``（不經 shell），使用者打的值
只出現在 commit 訊息（經 stdin 傳入，不拼進指令）。

只做寫回需要的事：前置檢查（分支、合併／rebase／cherry-pick 進行中、``index.lock``、檔案有沒有
未 commit 的改動）、只 commit 指定的檔、讀 ``tune:`` commit 的紀錄與檔案內容。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = ["MAIN_BRANCH", "Git", "GitError", "TuneCommit"]

MAIN_BRANCH: Final = "main"
_BUSY_MARKERS: Final = (
    "MERGE_HEAD",
    "REBASE_HEAD",
    "rebase-merge",
    "rebase-apply",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "index.lock",
)
_TIMEOUT_S: Final = 60
_LOG_FIELDS: Final = 3


class GitError(RuntimeError):
    """``git`` 回傳非 0（訊息帶 stderr）。"""


@dataclass(frozen=True)
class TuneCommit:
    commit: str
    summary: str
    date: str


class Git:
    """``root`` 這個 repo（或 worktree）的 git。"""

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def _exec(cwd: Path, args: Sequence[str], stdin: str | None = None) -> str:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            done = subprocess.run(  # 參數陣列、不經 shell
                ["git", *args],
                cwd=cwd,
                input=None if stdin is None else stdin.encode("utf-8"),
                capture_output=True,
                timeout=_TIMEOUT_S,
                env=env,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitError(f"git {args[0]} 執行失敗：{exc}") from exc
        if done.returncode != 0:
            err = done.stderr.decode("utf-8", "replace").strip()
            raise GitError(f"git {args[0]} 失敗：{err}")
        return done.stdout.decode("utf-8", "replace")

    @classmethod
    def find(cls, folder: Path) -> Git | None:
        """``folder`` 所在的 repo；不在任何 repo 裡（或沒有 git）回 ``None``。"""
        if not folder.is_dir():
            return None
        try:
            top = cls._exec(folder, ["rev-parse", "--show-toplevel"]).strip()
        except GitError:
            return None
        return cls(Path(top))

    def run(self, *args: str, stdin: str | None = None) -> str:
        return self._exec(self.root, args, stdin)

    def git_dir(self) -> Path:
        return Path(self.run("rev-parse", "--absolute-git-dir").strip())

    def branch(self) -> str | None:
        """目前分支（detached HEAD 時 ``None``）。"""
        try:
            return self.run("symbolic-ref", "--short", "-q", "HEAD").strip() or None
        except GitError:
            return None

    def busy(self) -> str | None:
        """合併、rebase、cherry-pick 進行中或 ``index.lock`` 在時，回那個標記檔名。"""
        folder = self.git_dir()
        common = Path(self.run("rev-parse", "--git-common-dir").strip())
        if not common.is_absolute():
            common = self.root / common
        for marker in _BUSY_MARKERS:
            if (folder / marker).exists() or (
                marker == "index.lock" and (common / marker).exists()
            ):
                return marker
        return None

    def dirty(self, paths: Sequence[str]) -> list[str]:
        """``paths`` 中有未 commit 改動（含已暫存、未追蹤）的檔。"""
        out = self.run("status", "--porcelain", "--untracked-files=all", "--", *paths)
        return sorted(line[3:].strip() for line in out.splitlines() if line.strip())

    def commit(self, paths: Sequence[str], message: str) -> str:
        """只 commit ``paths``（``git add`` 後 ``git commit -- <檔>``，不帶到別的暫存）。"""
        self.run("add", "--", *paths)
        self.run("commit", "-q", "-F", "-", "--", *paths, stdin=message)
        return self.run("rev-parse", "HEAD").strip()

    def unstage(self, paths: Sequence[str]) -> None:
        self.run("reset", "-q", "--", *paths)

    def tune_log(self, limit: int = 20) -> list[TuneCommit]:
        out = self.run("log", f"-n{limit}", "--grep=^tune", "--format=%H%x1f%s%x1f%cI")
        rows = [line.split("\x1f") for line in out.splitlines() if line.strip()]
        return [
            TuneCommit(commit=r[0], summary=r[1], date=r[2]) for r in rows if len(r) == _LOG_FIELDS
        ]

    def subject(self, commit: str) -> str:
        return self.run("log", "-n1", "--format=%s", commit, "--").strip()

    def resolve(self, commit: str) -> str:
        return self.run("rev-parse", "--verify", "-q", f"{commit}^{{commit}}").strip()

    def changed_files(self, commit: str) -> list[str]:
        out = self.run("diff-tree", "--no-commit-id", "--name-only", "-r", commit)
        return sorted(line.strip() for line in out.splitlines() if line.strip())

    def show(self, commit: str, path: str) -> str | None:
        """``commit`` 時 ``path``（repo 相對）的內容；那時沒有這個檔回 ``None``。"""
        try:
            return self.run("show", f"{commit}:{path}")
        except GitError:
            return None
