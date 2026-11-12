"""寫回 ``content/`` 並自動 commit（NW-1a A6，規格 5.3）；還原＝反向改動單（第 0 節第 8 點）。

寫回依序（任何一步失敗就停；已寫的檔從備份還原）：

1. 草稿驗證通過（呼叫端先跑完整驗證，見 :mod:`trpg.api.tuning.service`）。
2. git 前置檢查（:func:`writeback_problem`）：``content/`` 在 repo 裡、分支是 ``main``、沒有合併／
   rebase／cherry-pick 進行中、沒有 ``index.lock``、要改的檔沒有未 commit 的改動。
3. 改動單的 ``old`` 全部等於磁碟現值（:func:`~trpg.api.tuning.check.prepare` 已比對）。
4. 備份：要改的檔原樣複製到 ``<save_dir>/tuning/backups/<時間>/``（只留最近
   :data:`BACKUP_KEEP` 份）。
5. 寫檔 → 對**真的** ``content/`` 再跑一次 ``load_checked_library`` ＋ ``library_violations``。
6. ``git add`` ＋ ``git commit -- <這幾個檔>``（訊息 :func:`commit_message`；作者用使用者自己的 git
   設定，不加 Co-Authored-By）。
7. 回傳 commit 與「重開伺服器後生效」。
"""

from __future__ import annotations

import contextlib
import shutil
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Final

from trpg.api.primitive_coverage import load_checked_library
from trpg.api.tuning.check import Prepared
from trpg.api.tuning.drafts import Change, normalize
from trpg.api.tuning.git_guard import MAIN_BRANCH, Git, GitError
from trpg.api.tuning.objects import concrete_fields
from trpg.api.tuning.schemas import TuningApplyResult, TuningDiffRow
from trpg.api.tuning.yaml_patch import MISSING, lookup
from trpg.content.loader import parse_yaml
from trpg.content.tuning_fields import TuningFields, parse_path
from trpg.shared.errors import ContentError
from trpg.skillgen.library_check import library_violations

__all__ = [
    "BACKUP_KEEP",
    "BUSY_ZH",
    "RESTART_NOTE_ZH",
    "TUNED_BY",
    "WritebackError",
    "apply_prepared",
    "commit_message",
    "reverse_of_commit",
    "writeback_problem",
]

BACKUP_KEEP: Final = 50
TUNED_BY: Final = "Tuned-by: number-workshop"
RESTART_NOTE_ZH: Final = "已寫回並 commit；重開伺服器後遊戲才用新數值（進行中的一輪會從頭開始）。"
BUSY_ZH: Final = "開發 PM 正在合併（或別的程序正在動 git），稍後再寫回"
_SUBJECT_IDS: Final = 3


class WritebackError(Exception):
    """寫回失敗（訊息是給使用者看的中文；檔案已還原）。"""


def _content_prefix(git: Git, content_dir: Path) -> str | None:
    """``content/`` 相對 repo 根目錄的路徑（不在 repo 裡回 ``None``）。"""
    try:
        rel = content_dir.resolve().relative_to(git.root.resolve())
    except ValueError:
        return None
    return rel.as_posix()


def _repo_paths(prefix: str, files: Sequence[str]) -> list[str]:
    return [f"{prefix}/{f}" if prefix not in ("", ".") else f for f in files]


def writeback_problem(git: Git | None, content_dir: Path, files: Sequence[str] = ()) -> str | None:
    """不能寫回的原因（``None``＝可以）；``files`` 是要改的檔（相對 ``content/``）。"""
    prefix = None if git is None else _content_prefix(git, content_dir)
    if git is None or prefix is None:
        return "內容資料夾不在 git repo 裡（例如 TRPG_CONTENT_DIR 指到別處），只能模擬、不能寫回"
    try:
        branch = git.branch()
        if branch != MAIN_BRANCH:
            return f"目前分支是 {branch or '（沒有分支）'}，不是 {MAIN_BRANCH}，不能寫回"
        if git.busy() is not None:
            return BUSY_ZH
        dirty = git.dirty(_repo_paths(prefix, files)) if files else []
    except GitError as exc:
        return f"git 檢查失敗：{exc}"
    if dirty:
        return "這些檔有還沒 commit 的改動，先處理再寫回：" + "、".join(dirty)
    return None


def _value_zh(value: int | None) -> str:
    return "沒寫" if value is None else str(value)


def commit_message(rows: Sequence[TuningDiffRow]) -> str:
    """第一行 ``tune(<對象>): <欄位> <舊>→<新>…``，內文逐筆列改動，結尾 ``Tuned-by``。"""
    ids = list(dict.fromkeys(r.object_id for r in rows))
    who = ",".join(ids[:_SUBJECT_IDS]) + ("…" if len(ids) > _SUBJECT_IDS else "")
    first = rows[0]
    subject = f"tune({who}): {first.path} {_value_zh(first.old)}→{_value_zh(first.new)}"
    if len(rows) > 1:
        subject += f" 等 {len(rows)} 項"
    body = [
        f"- {r.file} {r.path}: {_value_zh(r.old)} → {_value_zh(r.new)}"
        f"（{r.object_name_zh} {r.label_zh}）"
        for r in rows
    ]
    return "\n".join([subject, "", *body, "", TUNED_BY, ""])


def _backup(root: Path, content_dir: Path, files: Sequence[str]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    folder = root / stamp
    for rel in files:
        target = folder / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(content_dir / rel, target)
    olds = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    for old in olds[:-BACKUP_KEEP]:
        shutil.rmtree(old, ignore_errors=True)
    return folder


def _restore(backup: Path, content_dir: Path, files: Sequence[str]) -> None:
    for rel in files:
        shutil.copyfile(backup / rel, content_dir / rel)


def _verify_live(content_dir: Path) -> str | None:
    try:
        library = load_checked_library(content_dir)
    except ContentError as exc:
        return str(exc)
    violations = library_violations(library)
    return "；".join(str(v) for v in violations) or None


def apply_prepared(
    *,
    content_dir: Path,
    git: Git | None,
    prepared: Prepared,
    rows: Sequence[TuningDiffRow],
    backups: Path,
    verify: Callable[[Path], str | None] = _verify_live,
) -> TuningApplyResult:
    """第 2～7 步（第 1 步由呼叫端做完）。失敗丟 :class:`WritebackError`，檔案與暫存已還原。"""
    if prepared.errors:
        raise WritebackError(
            "改動單有錯，沒有寫回：" + "；".join(e.message_zh for e in prepared.errors)
        )
    files = sorted(prepared.texts)
    if not files:
        raise WritebackError("草稿沒有改動，沒有東西可以寫回")
    problem = writeback_problem(git, content_dir, files)
    if problem is not None or git is None:
        raise WritebackError(problem or "不能寫回")
    prefix = _content_prefix(git, content_dir)
    assert prefix is not None
    for rel in files:  # 第 3 步：寫之前再確認磁碟沒被別人改過
        if (content_dir / rel).read_bytes().decode("utf-8") != prepared.originals[rel]:
            raise WritebackError(f"{rel} 在驗證之後被改過了，請重新載入再寫回")
    backup = _backup(backups, content_dir, files)
    try:
        for rel in files:
            (content_dir / rel).write_bytes(prepared.texts[rel].encode("utf-8"))
        failed = verify(content_dir)
        if failed is not None:
            raise WritebackError(f"寫進 content/ 後整包檢查沒過，已從備份還原：{failed}")
        message = commit_message(rows)
        paths = _repo_paths(prefix, files)
        try:
            commit = git.commit(paths, message)
        except GitError as exc:
            with contextlib.suppress(GitError):
                git.unstage(paths)
            raise WritebackError(f"git commit 失敗，已從備份還原：{exc}") from exc
    except BaseException:
        _restore(backup, content_dir, files)
        raise
    return TuningApplyResult(
        commit=commit,
        message=message,
        files=files,
        backup=backup.as_posix(),
        restart_note_zh=RESTART_NOTE_ZH,
    )


def reverse_of_commit(
    git: Git | None, content_dir: Path, table: TuningFields, commit: str
) -> tuple[Change, ...]:
    """一筆 ``tune:`` commit 的反向改動單（新 → 舊）：比對 commit 前後每個白名單欄位的值。

    ``old`` 是那筆 commit 寫進去的值；之後又被改過時，驗證會標「這個值已經被改過」。"""
    if git is None:
        raise WritebackError("內容資料夾不在 git repo 裡，不能從 commit 還原")
    prefix = _content_prefix(git, content_dir)
    try:
        full = git.resolve(commit)
        subject = git.subject(full)
        files = git.changed_files(full)
    except GitError as exc:
        raise WritebackError(f"找不到 commit {commit}") from exc
    if not subject.startswith("tune"):
        raise WritebackError("只能還原數值工坊寫回的 tune: commit")
    head = "" if prefix in (None, "", ".") else f"{prefix}/"
    changes: list[Change] = []
    for repo_path in files:
        if not repo_path.startswith(head):
            continue
        rel = repo_path[len(head) :]
        before_text, after_text = git.show(f"{full}^", repo_path), git.show(full, repo_path)
        if before_text is None or after_text is None:
            continue
        before, after = parse_yaml(before_text), parse_yaml(after_text)
        target = next((t for t in table.targets if Path(rel).match(t.glob)), None)
        if target is None:
            continue
        paths = {p for _f, p, _l in concrete_fields(after, target)}
        paths |= {p for _f, p, _l in concrete_fields(before, target)}
        for path in sorted(paths):
            old_v, new_v = lookup(after, parse_path(path)), lookup(before, parse_path(path))
            old_i = None if old_v is MISSING else old_v
            new_i = None if new_v is MISSING else new_v
            if old_i != new_i:
                changes.append(Change(file=rel, path=path, old=old_i, new=new_i))
    if not changes:
        raise WritebackError("這筆 commit 沒有數值工坊管的欄位改動")
    return normalize(changes)
