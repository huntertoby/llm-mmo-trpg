"""PK-3（06 6.7「候選怎麼篩」，使用者題 1「B 放寬」、題 2「B 擠掉」）：三選一每格的候選。

- 「跟主路線」改成扣分：符合路線、全部關鍵字的候選不夠 ``pool.relax_until`` 個時，依序放寬（部分
  關鍵字 → 偏離路線），放寬的扣分；偏離最多 2 張。
- 單薄的候選不進給 LLM 的前幾名（全格都單薄時照分數給）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from tests.roguelite.helpers import library
from trpg.roguelite import new_run
from trpg.roguelite.llm_hook import use_picker, use_proposer
from trpg.roguelite.offers import candidate_request, make_offer, pick_player
from trpg.skillgen.candidates import CandidateRules, LlmTrace
from trpg.skillgen.pick_offer import (
    LEVEL_EXACT,
    MAX_OFF_ROUTE,
    OfferPicker,
    SlotChoice,
    SlotPick,
    pick_slots,
)
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.skill_pick import PickCandidate, drop_thin, thin_reasons

BUILDS = (
    "build_push",
    "build_fire",
    "build_ranged",
    "build_healer",
    "build_storm",
    "build_tank",
    "build_assassin",
    "build_seer",
)
"""固定的 build（種子 0、升級白板三選一；不用 hypothesis 跑候選池）。"""


def _sizes(lib: object) -> list[int]:
    sizes: list[int] = []
    for build in BUILDS:
        run = new_run(library(), build, 0)
        slots = pick_slots(
            lib,  # type: ignore[arg-type]
            candidate_request(library(), run),
            CandidateRules(composer_tries=library().roguelite.candidates.composer_tries),
            player=pick_player(library(), run),
            whiteboard=True,
        )
        sizes += [len(s.slate.ranked) for s in slots]
    return sizes


def test_relaxing_gives_most_slots_a_choice() -> None:
    """PK-2 實機約一半的格子只有 1 張候選；放寬後固定樣本裡多數格子湊得到 2 張以上。不放寬
    （``relax_until``＝1：只收全部關鍵字＋路線符合的）時單張的格子比較多。"""
    lib = library()
    sizes = _sizes(lib)
    strict = replace(
        lib,
        skill_pick=lib.skill_pick.model_copy(
            update={"pool": lib.skill_pick.pool.model_copy(update={"relax_until": 1})}
        ),
    )
    narrow = _sizes(strict)
    singles = sum(n == 1 for n in sizes)
    assert singles * 3 < len(sizes)  # 多數格子有得挑（單張不到三分之一）
    assert singles < sum(n == 1 for n in narrow)


def test_relaxed_candidates_rank_after_exact_ones() -> None:
    """放寬的候選帶扣分（route_off／relaxed），而且只有全部關鍵字＋路線符合的不夠 relax_until 個時
    才放進來。"""
    lib = library()
    for build in BUILDS:
        run = new_run(lib, build, 0)
        slots = pick_slots(
            lib,
            candidate_request(lib, run),
            CandidateRules(composer_tries=lib.roguelite.candidates.composer_tries),
            player=pick_player(lib, run),
            whiteboard=True,
        )
        for slot in slots:
            relaxed = [c for c in slot.slate.ranked if _penalised(c)]
            exact = len(slot.slate.ranked) - len(relaxed)
            if relaxed:
                assert exact < lib.skill_pick.pool.relax_until or slot.nondamage


def _penalised(candidate: PickCandidate) -> bool:
    parts = dict(candidate.parts)
    return parts.get("route_off", 0) < 0 or parts.get("relaxed", 0) < 0


def test_level_constant_is_the_pk2_condition() -> None:
    assert LEVEL_EXACT == 0


def _last(slots: Sequence[SlotPick], player: PickPlayer) -> list[SlotChoice | None]:
    """永遠挑最後一張（偏離的候選排在最後）的挑選器。"""
    out: list[SlotChoice | None] = []
    for slot in slots:
        position = len(slot.slate.ranked) - 1
        trace = LlmTrace(
            keywords=slot.keywords,
            rarity=slot.request.rarity,
            core_primitive=None,
            menu_seed=None,
            theme=None,
            attempts=1,
            ok=True,
        )
        skill = slot.slate.ranked[position].skill
        out.append(SlotChoice(position=position, skill=skill, trace=trace, llm=True))
    return out


def test_off_route_cap_holds_even_if_llm_picks_the_last() -> None:
    """LLM 永遠挑排最後（常是偏離）的候選：LLM 挑出來的偏離不會讓一份三選一超過 2 張（#110）。"""
    lib = library()
    picker: OfferPicker = _last
    for build in BUILDS:
        run = new_run(lib, build, 0).model_copy(update={"llm": True})
        with use_proposer(None), use_picker(picker):
            offer = make_offer(lib, run, "level_up", pick=True)
        top = make_offer(lib, run.model_copy(update={"llm": False}), "level_up", pick=True)
        # 分數第一名本身就偏離的格子（做不出跟路線的）不算 LLM 造成的
        assert len(offer.off_route) <= max(MAX_OFF_ROUTE, len(top.off_route))


def test_thin_candidates_stay_out_unless_all_thin() -> None:
    lib = library()
    weights = lib.skill_pick.weights
    hollow = next(
        s for s in lib.skills.values() if s.effects and all(e.type == "inscribe" for e in s.effects)
    )
    full = lib.skills["skill_fire_bolt"]
    assert thin_reasons(hollow) and not thin_reasons(full)
    a = PickCandidate(hollow, "composer", 1, ("a", "", "", (), ()))
    b = PickCandidate(full, "composer", 2, ("b", "", "", (), ()))
    assert drop_thin([a, b], weights) == [b]
    assert drop_thin([a], weights) == [a]  # 全格都單薄：照分數給，不留空


def test_ranked_slates_have_no_thin_when_full_ones_exist() -> None:
    lib = library()
    epic = lib.skill_pick.weights.thin_epic_min_effects
    for build in BUILDS[:4]:
        run = new_run(lib, build, 0)
        for slot in pick_slots(
            lib,
            candidate_request(lib, run),
            CandidateRules(composer_tries=lib.roguelite.candidates.composer_tries),
            player=pick_player(lib, run),
            whiteboard=True,
        ):
            thin = [bool(thin_reasons(c.skill, epic_min_effects=epic)) for c in slot.slate.ranked]
            assert all(thin) or not any(thin)
