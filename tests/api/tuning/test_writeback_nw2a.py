"""NW-2a T-A4：預算例外的寫回閘門與附帶改動（全部在 ``tmp_path`` 的假 repo；不碰真的 content/）。

另含 T13 的 commit 訊息與招式組的寫回、還原。"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.api.tuning.conftest import git
from trpg.api.tuning.check import prepare
from trpg.api.tuning.drafts import Change, Draft
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.skills import add_budget_side_changes
from trpg.api.tuning.writeback import TUNED_BY, WritebackError
from trpg.api.tuning.yaml_patch import exception_comment
from trpg.content.library import load_library
from trpg.content.loader import parse_yaml
from trpg.skillgen.budget import skill_budget

FIRE = "skills/skill_fire_arrow.yaml"
BUDGET = "skill_budget.yaml"
DATE = "2026-11-12"


@pytest.fixture
def service(repo_service: TuningService) -> TuningService:
    repo_service.today = lambda: DATE
    return repo_service


def _draft(service: TuningService, *changes: Change) -> None:
    service.drafts.put(Draft(name="current", changes=changes))


def _bytes(service: TuningService, rel: str) -> bytes:
    return (service.content_dir / rel).read_bytes()


def _commits(repo: Path) -> int:
    return int(git(repo, "rev-list", "--count", "HEAD").strip())


def _exceptions(service: TuningService) -> list[str]:
    data = parse_yaml(_bytes(service, BUDGET).decode("utf-8"))
    return list(data["known_budget_exceptions"])


def _out_of_range(content: Path) -> set[str]:
    """``tests/skillgen/test_range_budget.py`` 的同一個判定。"""
    library = load_library(content)
    return {
        s.id
        for s in library.skills.values()
        if not s.id.startswith("skill_gear_") and not skill_budget(s, library).ok
    }


def test_over_budget_needs_confirmation_then_registers_and_unregisters(
    repo: Path, service: TuningService
) -> None:
    fire_before, budget_before = _bytes(service, FIRE), _bytes(service, BUDGET)
    _draft(service, Change(file=FIRE, path="effects[0].multiplier_permille", old=800, new=1300))
    check = service.check("current")
    assert check.ok and [f.skill_id for f in check.needs_confirm_budget] == ["skill_fire_arrow"]
    assert check.needs_confirm_budget[0].ratio_text == "128.1%"
    assert [s.action for s in check.side_changes] == ["exception_add"]
    diff = service.diff("current")
    assert "+known_budget_exceptions: [skill_fire_arrow, skill_summon_elite]" in diff.text
    with pytest.raises(WritebackError, match="我確定"):  # 不勾 → 409、檔案不變
        service.apply("current")
    with pytest.raises(WritebackError, match="不符"):  # 勾的和超出的不符 → 409
        service.apply("current", ["skill_pinpoint_shot"])
    assert _bytes(service, FIRE) == fire_before and _bytes(service, BUDGET) == budget_before
    assert _commits(repo) == 1
    done = service.apply("current", ["skill_fire_arrow"])
    assert done.files == [BUDGET, FIRE]
    text = _bytes(service, BUDGET).decode("utf-8")
    assert exception_comment("skill_fire_arrow", "128.1%", DATE) + "\n" in text
    assert _exceptions(service) == ["skill_fire_arrow", "skill_summon_elite"]
    shown = git(repo, "show", "--name-only", "--format=%B", "HEAD")
    assert (
        shown.splitlines()[0] == "tune(skill_fire_arrow): effects[0].multiplier_permille 800→1300"
    )
    assert "預算例外：skill_fire_arrow（比例 128.1%" in shown and TUNED_BY in shown
    assert sorted(shown.rstrip().splitlines()[-2:]) == [f"content/{BUDGET}", f"content/{FIRE}"]
    assert _out_of_range(service.content_dir) == set(_exceptions(service))  # test_range_budget 照過
    # 調回區間 → 自動移除（不必勾），兩個檔逐位元組回到原樣
    _draft(service, Change(file=FIRE, path="effects[0].multiplier_permille", old=1300, new=800))
    back = service.check("current")
    assert back.ok and not back.needs_confirm_budget
    assert [s.action for s in back.side_changes] == ["exception_remove"]
    service.apply("current")
    assert _bytes(service, FIRE) == fire_before and _bytes(service, BUDGET) == budget_before
    assert "預算例外移除（回到合格區間）：skill_fire_arrow" in git(repo, "log", "-1", "--format=%B")


def test_listed_skill_in_range_is_removed_even_if_hand_written(service: TuningService) -> None:
    """清單裡（不論誰寫的）而草稿讓它在合格區間 → 附帶移除；別的例外（``skill_summon_elite``，
    仍超出）不動（規格 5.3）。"""
    library = service._rules_library()
    assert not skill_budget(library.skills["skill_summon_elite"], library).ok
    prepared = prepare(service.content_dir, service.table, [])
    prepared.kinds["skills/skill_fire_arrow.yaml"] = "skill"
    prepared.texts["skills/skill_fire_arrow.yaml"] = _bytes(service, FIRE).decode("utf-8")
    text = (
        _bytes(service, BUDGET)
        .decode("utf-8")
        .replace(
            "known_budget_exceptions: [skill_summon_elite]",
            "known_budget_exceptions: [skill_fire_arrow, skill_summon_elite]",
        )
    )
    (service.content_dir / BUDGET).write_text(text, encoding="utf-8", newline="\n")
    add_budget_side_changes(prepared, service.content_dir, library, DATE)
    assert [(s.action, s.skill_id) for s in prepared.side] == [
        ("exception_remove", "skill_fire_arrow")
    ]
    assert "[skill_summon_elite]" in prepared.texts[BUDGET]


def test_multi_skill_commit_subject(repo: Path, service: TuningService) -> None:
    _draft(
        service,
        Change(file=FIRE, path="effects[0].multiplier_permille", old=800, new=850),
        Change(
            file="skills/skill_pinpoint_shot.yaml",
            path="effects[0].multiplier_permille",
            old=1000,
            new=950,
        ),
    )
    service.apply("current")
    subject = git(repo, "log", "-1", "--format=%s").strip()
    assert subject == "tune(skills×2): effects[0].multiplier_permille 800→850 等 2 項"


def test_unit_skill_list_writeback_and_revert(repo: Path, service: TuningService) -> None:
    heart = "units/ashen_heart.yaml"
    before = _bytes(service, heart)
    old = ["skill_heart_inhale", "skill_heart_exhale", "skill_fire_bolt"]
    _draft(
        service,
        Change(
            file=heart,
            path="phases[1].skills",
            old=tuple(old),
            new=("skill_heart_inhale", "skill_fire_bolt", "skill_heart_exhale"),
        ),
    )
    done = service.apply("current")
    assert "phases[1].skills: [skill_heart_inhale, skill_heart_exhale, skill_fire_bolt] →" in (
        done.message
    )
    service.revert("current", done.commit)
    service.apply("current")
    assert _bytes(service, heart) == before
