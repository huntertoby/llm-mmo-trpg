"""``trpg skills random``：隨機組合器的產物（Phase 2B-3 5.4）。"""

from __future__ import annotations

from typing import TextIO

from trpg.cli.budget import print_skill_budget
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillRarity
from trpg.shared.errors import TrpgError
from trpg.skillgen.random_composer import compose_with_stats
from trpg.skillgen.skill_yaml import skill_to_yaml

__all__ = ["cmd_skills_random"]


def cmd_skills_random(
    library: ContentLibrary,
    *,
    seed: int,
    count: int,
    tier: int | None,
    rarity: SkillRarity | None,
    skeleton: str | None,
    out: TextIO,
    err: TextIO,
) -> int:
    """從 ``seed`` 起連續 ``count`` 個種子各組一個技能，印出 YAML 與預算摘要。"""
    code = 0
    for current in range(seed, seed + count):
        try:
            result = compose_with_stats(
                current, tier=tier, rarity=rarity, skeleton=skeleton, library=library
            )
        except TrpgError as exc:
            print(f"錯誤：{exc}", file=err)
            return 1
        print(f"# 種子 {current}（重抽 {result.attempts - 1} 次）", file=out)
        print(skill_to_yaml(result.skill), file=out, end="")
        print("", file=out)
        code = max(code, print_skill_budget(library, result.skill, out))
        if current != seed + count - 1:
            print("", file=out)
    return code
