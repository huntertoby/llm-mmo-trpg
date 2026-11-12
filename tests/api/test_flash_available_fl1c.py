"""FL-1c 第 7 點：沒有任何閃現選項的招，面板資料事先標好（``flash_available``），不給按。"""

from __future__ import annotations

from tests.roguelite.helpers import library
from trpg.api.run_presenter import _flash_out
from trpg.roguelite import RunState, new_run
from trpg.roguelite.flashes import flash_available
from trpg.skillgen.flash_offer import NO_OPTIONS_ZH
from trpg.skillgen.flash_state import acquire

BUILD = "build_fire"
SEED = 3


def _with(skill_id: str, *, used: bool = True) -> RunState:
    """一輪剛開始的主角，第一招換成 ``skill_id``（已在戰鬥中用過）。"""
    lib = library()
    run = new_run(lib, BUILD, SEED)
    skills = (skill_id, *run.hero.skills[1:])
    state = acquire(skill_id).model_copy(update={"used": used})
    return run.model_copy(
        update={
            "hero": run.hero.model_copy(update={"skills": skills}),
            "flash": {**run.flash, skill_id: state},
        }
    )


def test_a_skill_without_options_is_greyed_out() -> None:
    lib = library()
    run = _with("skill_afterimage_vow")
    assert not flash_available(lib, run, "skill_afterimage_vow")
    out = _flash_out(lib, run, "skill_afterimage_vow")
    assert out.flash_available is False
    assert out.can_flash is False
    assert out.flash_problem_zh == NO_OPTIONS_ZH == "這招目前沒有可以閃的變化"


def test_a_skill_with_options_stays_available() -> None:
    lib = library()
    run = _with("skill_war_hymn")
    out = _flash_out(lib, run, "skill_war_hymn")
    assert out.flash_available is True
    assert out.can_flash is True
    assert out.flash_problem_zh is None


def test_other_problems_skip_the_check() -> None:
    """還沒用過（或閃滿）時照原本的原因，不算選項（``flash_available`` 照 ``True``）。"""
    lib = library()
    run = _with("skill_afterimage_vow", used=False)
    out = _flash_out(lib, run, "skill_afterimage_vow")
    assert out.flash_available is True
    assert out.can_flash is False
    assert out.flash_problem_zh is not None and out.flash_problem_zh != NO_OPTIONS_ZH
