"""主角的技能照角色階級重配數值（Phase 3W-9，``docs/design/06-技能.md`` 6.34.9；玩法決定 #72）。

:func:`sync_skill_tier`：角色階級（:func:`~trpg.skillgen.skill_tier.character_tier`）和主角技能目前
用的階級（``RunState.skill_tier``）不同時，裝備與備用的每招技能照新階級的預算重配
（:func:`~trpg.skillgen.skill_tier.retier`：結構與變化保留、預算分數不低於升階前）。只在戰鬥之間
呼叫（升級節點、讀入舊存檔），戰鬥中不會變。手寫技能（內容庫裡的，例如手寫池退回的候選、開發者
起始包）重配後成為生成技能 ``<原 ID>_t<階級>``（:func:`~trpg.roguelite.offers.at_run_tier`），閃現
狀態、用法統計、備用清單跟著換 ID。

**同一招只有一個真相來源**（3W-R1）：閃過的技能（有變化歷程）不重配存著的定義，而是從原本的技能
照新階級重推整條歷程（:func:`~trpg.skillgen.flash_derive.derive_skill`，與閃現出題同一個函式），所以卡片
上的數字就是下一次閃現的「套用前」與重閃的強度下限；ID 由歷程決定，不變。:func:`retier` 只處理沒
閃過的技能。歷程在目前的內容重推不了時（:class:`~trpg.skillgen.flash_derive.FlashHistoryError`），退回
重配存著的定義（之後的閃現也以它為起點，見 ``FlashRequest.current``）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.roguelite.flashes import base_def, state_of
from trpg.roguelite.offers import at_run_tier, skill_defs
from trpg.roguelite.state import RunState
from trpg.skillgen.flash_derive import FlashError, derive_skill
from trpg.skillgen.skill_tier import character_tier, retier

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
        new = _at_tier(library, run, skill, tier)
        if new.id != skill.id:
            rename[skill.id] = new.id
            generated.pop(skill.id, None)
        if new.id not in library.skills:
            generated[new.id] = new
    skills = tuple(rename.get(s, s) for s in run.hero.skills)
    bench = tuple(sorted(rename.get(s, s) for s in run.bench))
    keep = {*skills, *bench}
    kept = {k: v for k, v in generated.items() if k in keep}
    usage = {rename.get(k, k): v for k, v in run.skill_usage.items()}
    flash = {rename.get(k, k): v for k, v in run.flash.items()}
    return run.model_copy(
        update={
            "hero": run.hero.model_copy(update={"skills": skills}),
            "bench": bench,
            "generated_skills": tuple(kept[k] for k in sorted(kept)),
            "skill_usage": {k: usage[k] for k in sorted(usage)},
            "flash": {k: flash[k] for k in sorted(flash)},
            "skill_tier": tier,
        }
    )


def _at_tier(library: ContentLibrary, run: RunState, skill: SkillDef, tier: int) -> SkillDef:
    """一招學會的技能換到角色階級 ``tier``：閃過的從原本的技能照新階級重推歷程（重推不了時重配存著
    的定義），沒閃過的照 :func:`~trpg.roguelite.offers.at_run_tier` 重配。"""
    state = state_of(run, skill.id)
    if not state.records and state.adjustment is None:
        return at_run_tier(library, skill, tier)
    try:
        return derive_skill(library, base_def(library, run, skill.id), state, run.seed, tier)
    except FlashError:
        return retier(library, skill, tier)
