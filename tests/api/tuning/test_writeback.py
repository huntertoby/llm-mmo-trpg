"""NW-1a T-A5／T-A6：寫回＋備份＋git（全部在 ``tmp_path`` 的假 repo；不碰真的 content/）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.api.tuning.conftest import git
from trpg.api.tuning import writeback
from trpg.api.tuning.check import prepare
from trpg.api.tuning.diff import diff_rows
from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.git_guard import Git, GitError
from trpg.api.tuning.schemas import TuningDiffRow
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.writeback import (
    BUSY_ZH,
    TUNED_BY,
    WritebackError,
    apply_prepared,
    writeback_problem,
)

HEART = "units/ashen_heart.yaml"
HEART_REPO = f"content/{HEART}"


def _draft(service: TuningService, *changes: Change) -> None:
    service.drafts.put(Draft(name="current", changes=changes))


def _heart(service: TuningService) -> bytes:
    return (service.content_dir / HEART).read_bytes()


def _commits(repo: Path) -> int:
    return int(git(repo, "rev-list", "--count", "HEAD").strip())


def test_apply_commits_only_the_changed_file(repo: Path, repo_service: TuningService) -> None:
    before = _heart(repo_service)
    _draft(
        repo_service,
        Change(file=HEART, path="max_hp", old=160, new=150),
        Change(file=HEART, path="phases[1].trigger.permille", old=600, new=550),
    )
    (repo / "content" / "README.md").write_text("沒 commit 的別的改動\n", encoding="utf-8")
    git(repo, "add", "content/README.md")  # 別的暫存不能被帶進這筆 commit
    done = repo_service.apply("current")
    assert _commits(repo) == 2
    assert done.files == [HEART] and done.commit == git(repo, "rev-parse", "HEAD").strip()
    shown = git(repo, "show", "--name-only", "--format=%B", "HEAD")
    subject = shown.splitlines()[0]
    assert subject == "tune(ashen_heart): max_hp 160→150 等 2 項"
    assert "- units/ashen_heart.yaml phases[1].trigger.permille: 600 → 550" in shown
    assert TUNED_BY in shown and "Co-Authored-By" not in shown
    assert shown.rstrip().splitlines()[-1] == HEART_REPO  # 只有這個檔
    assert git(repo, "diff", "--cached", "--name-only").strip() == "content/README.md"
    after = _heart(repo_service)
    changed = [
        (a, b) for a, b in zip(before.splitlines(), after.splitlines(), strict=True) if a != b
    ]
    assert changed == [
        (b"max_hp: 160", b"max_hp: 150"),
        (
            b"    trigger: {kind: hp_below, permille: 600}",
            b"    trigger: {kind: hp_below, permille: 550}",
        ),
    ]
    assert b"\r\n" not in after  # LF 照舊
    assert (Path(done.backup) / HEART).read_bytes() == before
    assert repo_service.writes == [done.commit] and repo_service.status().restart_needed
    assert repo_service.drafts.get("current").changes == ()  # 寫回後草稿清掉
    assert [h.commit for h in repo_service.history()] == [done.commit]


@pytest.mark.parametrize("marker", ["MERGE_HEAD", "index.lock", "CHERRY_PICK_HEAD", "rebase-merge"])
def test_busy_repo_refuses_and_leaves_files(
    repo: Path, repo_service: TuningService, marker: str
) -> None:
    (repo / ".git" / marker).touch()
    before = _heart(repo_service)
    _draft(repo_service, Change(file=HEART, path="max_hp", old=160, new=150))
    with pytest.raises(WritebackError, match=BUSY_ZH):
        repo_service.apply("current")
    assert _heart(repo_service) == before and _commits(repo) == 1
    assert repo_service.status().reason_zh == BUSY_ZH and not repo_service.status().can_write


def test_not_on_main_refuses(repo: Path, repo_service: TuningService) -> None:
    git(repo, "checkout", "-q", "-b", "feature")
    _draft(repo_service, Change(file=HEART, path="max_hp", old=160, new=150))
    with pytest.raises(WritebackError, match="目前分支是 feature"):
        repo_service.apply("current")
    assert _commits(repo) == 1


def test_uncommitted_change_in_the_file_refuses(repo: Path, repo_service: TuningService) -> None:
    path = repo / HEART_REPO
    path.write_bytes(path.read_bytes() + b"# local note\n")
    before = _heart(repo_service)
    _draft(repo_service, Change(file=HEART, path="max_hp", old=160, new=150))
    with pytest.raises(WritebackError, match="還沒 commit 的改動"):
        repo_service.apply("current")
    assert _heart(repo_service) == before and _commits(repo) == 1


def test_stale_old_value_refuses(repo: Path, repo_service: TuningService) -> None:
    before = _heart(repo_service)
    _draft(repo_service, Change(file=HEART, path="max_hp", old=170, new=150))
    with pytest.raises(WritebackError, match="已經被改過（現在是 160）"):
        repo_service.apply("current")
    assert _heart(repo_service) == before and _commits(repo) == 1


def test_invalid_value_refuses(repo: Path, repo_service: TuningService) -> None:
    _draft(repo_service, Change(file=HEART, path="max_hp", old=160, new=0))
    with pytest.raises(WritebackError, match="不能小於 1"):
        repo_service.apply("current")
    assert _commits(repo) == 1


def test_commit_failure_restores_from_backup(
    repo: Path, repo_service: TuningService, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = _heart(repo_service)
    real = Git.run

    def failing(self: Git, *args: str, stdin: str | None = None) -> str:
        if args[0] == "commit":
            raise GitError("git commit 失敗：模擬")
        return real(self, *args, stdin=stdin)

    monkeypatch.setattr(Git, "run", failing)
    _draft(repo_service, Change(file=HEART, path="max_hp", old=160, new=150))
    with pytest.raises(WritebackError, match="已從備份還原"):
        repo_service.apply("current")
    assert _heart(repo_service) == before and _commits(repo) == 1
    monkeypatch.setattr(Git, "run", real)
    assert git(repo, "status", "--porcelain").strip() == ""  # 暫存也還原了


def test_failed_live_check_restores_from_backup(repo: Path, repo_service: TuningService) -> None:
    before = _heart(repo_service)
    prepared = prepare(
        repo_service.content_dir,
        repo_service.table,
        [Change(file=HEART, path="max_hp", old=160, new=150)],
    )
    rows = diff_rows(repo_service.content_dir, repo_service.table, prepared.changes)
    with pytest.raises(WritebackError, match="整包檢查沒過"):
        apply_prepared(
            content_dir=repo_service.content_dir,
            git=repo_service.git,
            prepared=prepared,
            rows=rows,
            backups=repo_service.root / "backups",
            verify=lambda _root: "模擬的跨檔錯誤",
        )
    assert _heart(repo_service) == before and _commits(repo) == 1


def test_apply_then_revert_is_byte_identical(repo: Path, repo_service: TuningService) -> None:
    """T-A6：寫回 → 還原（反向改動單）→ 再寫回，檔案逐位元組回到原樣。"""
    before = _heart(repo_service)
    _draft(
        repo_service,
        Change(file=HEART, path="max_hp", old=160, new=150),
        Change(file=HEART, path="element_mods.wind", old=None, new=250),  # 原本沒寫：插入
    )
    first = repo_service.apply("current")
    assert _heart(repo_service) != before
    view = repo_service.revert("current", first.commit)
    assert {(c.path, c.old, c.new) for c in view.changes} == {
        ("max_hp", 150, 160),
        ("element_mods.wind", 250, None),
    }
    second = repo_service.apply("current")
    assert _heart(repo_service) == before
    assert _commits(repo) == 3
    assert git(repo, "diff", first.commit + "^", second.commit, "--stat").strip() == ""
    assert [h.commit for h in repo_service.history()] == [second.commit, first.commit]


def test_revert_refuses_non_tune_commits(repo: Path, repo_service: TuningService) -> None:
    head = git(repo, "rev-parse", "HEAD").strip()
    with pytest.raises(WritebackError, match="tune: commit"):
        repo_service.revert("current", head)


def test_content_outside_a_repo_disables_writeback(tmp_path: Path) -> None:
    assert writeback_problem(None, tmp_path) is not None
    assert "只能模擬" in (writeback_problem(Git.find(tmp_path), tmp_path) or "")


def test_commit_message_format() -> None:
    rows = [
        TuningDiffRow(
            object_id=f"u{i}",
            object_name_zh=f"單位{i}",
            file=f"units/u{i}.yaml",
            path="speed",
            label_zh="速度",
            old=None if i == 0 else i,
            new=i + 1,
        )
        for i in range(5)
    ]
    message = writeback.commit_message(rows)
    lines = message.splitlines()
    assert lines[0] == "tune(u0,u1,u2…): speed 沒寫→1 等 5 項"
    assert lines[2] == "- units/u0.yaml speed: 沒寫 → 1（單位0 速度）"
    assert lines[-1] == TUNED_BY
