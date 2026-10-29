"""主角的技能照角色階級重配數值（Phase 3W-9，``docs/design/06-技能.md`` 6.34.9；玩法決定 #72）。

:func:`sync_skill_tier`：角色階級（:func:`~trpg.skillgen.skill_tier.character_tier`）和主角技能目前
用的階級（``RunState.skill_tier``）不同時，裝備與備用的每招技能照新階級的預算重配
（:func:`~trpg.skillgen.skill_tier.retier`：結構與變化保留、預算分數不低於升階前）。只在戰鬥之間
呼叫（升級節點、讀入舊存檔），戰鬥中不會變。手寫技能（內容庫裡的，例如手寫池退回的候選、開發者
起始包）重配後成為生成技能 ``<原 ID>_t<階級>``（:func:`~trpg.roguelite.offers.at_run_tier`），等級、
用法統計、備用清單跟著換 ID。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.roguelite.offers import at_run_tier, skill_defs
from trpg.roguelite.state import RunState
from trpg.skillgen.skill_tier import character_tier

__all__ = ["run_tier", "sync_skill_tier"]


def run_tier(library: ContentLibrary, run: RunState) -> int:
    """這一輪主角目前的角色階級。"""
    return character_tier(library, run.level)


def sync_skill_tier(library: ContentLibrary, run: RunState) -> RunState:
    """主角裝備與備用的技能都照角色目前的階級重配（見模組說明）；已經同步時原樣回傳。"""
    tier = run_tier(library, run)
    if run.skill_tier == tier:
        return run
    owned = (*run.hero.skills, *run.bench)
    rename: dict[str, str] = {}
    generated = {s.id: s for s in run.generated_skills}
    for skill in skill_defs(library, run, owned):
        new = at_run_tier(library, skill, tier)
        if new.id != skill.id:
            rename[skill.id] = new.id
            generated.pop(skill.id, None)
        if new.id not in library.skills:
            generated[new.id] = new
    skills = tuple(rename.get(s, s) for s in run.hero.skills)
    bench = tuple(sorted(rename.get(s, s) for s in run.bench))
    keep = {*skills, *bench}
    kept = {k: v for k, v in generated.items() if k in keep}
    levels = {rename.get(k, k): v for k, v in run.skill_levels.items()}
    usage = {rename.get(k, k): v for k, v in run.skill_usage.items()}
    return run.model_copy(
        update={
            "hero": run.hero.model_copy(update={"skills": skills}),
            "bench": bench,
            "generated_skills": tuple(kept[k] for k in sorted(kept)),
            "skill_levels": {k: levels[k] for k in sorted(levels)},
            "skill_usage": {k: usage[k] for k in sorted(usage)},
            "skill_tier": tier,
        }
    )
