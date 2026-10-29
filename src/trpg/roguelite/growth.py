"""技能庫與換裝（Phase 3-26a；Phase 3W-5 起技能點、技能等級與分歧進化取消，改由靈感點與閃現取代，
見 :mod:`trpg.roguelite.flashes`）。

- :func:`set_loadout`：營火的換裝——重排裝備與備用技能；閃現狀態跟著技能走，所以卸下的技能長出的
  變化保留。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.roguelite.errors import ChoiceError
from trpg.roguelite.offers import equip_problems, skill_defs
from trpg.roguelite.state import RunState

__all__ = ["set_loadout"]


def set_loadout(library: ContentLibrary, run: RunState, skills: tuple[str, ...]) -> RunState:
    """新的裝備清單 ``skills``（順序即技能列順序）；沒裝上的進備用。不合法時拋出
    :class:`ChoiceError`。"""
    owned = (*run.hero.skills, *run.bench)
    unknown = sorted(set(skills) - set(owned))
    if unknown:
        raise ChoiceError(f"不能裝備沒有的技能：{', '.join(unknown)}")
    if len(set(skills)) != len(skills):
        raise ChoiceError("技能不可重複裝備")
    problems = equip_problems(library, skill_defs(library, run, skills))
    if problems:
        raise ChoiceError("；".join(problems))
    bench = tuple(sorted(set(owned) - set(skills)))
    hero = run.hero.model_copy(update={"skills": tuple(skills)})
    return run.model_copy(update={"hero": hero, "bench": bench})
