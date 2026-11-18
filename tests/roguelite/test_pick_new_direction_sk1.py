"""SK-1（06 6.38 第 6 點，#166）：三選一「新方向」格，會製造該關鍵字的卡排在純利用的前面。

只改排序：每格的關鍵字、種類、路線段（符合路線在偏離前面）照舊；加深、橋接格的排序不變。
"""

from __future__ import annotations

from tests.roguelite.helpers import library
from tests.roguelite.test_pick_offer_pk3 import BUILDS
from trpg.roguelite import new_run
from trpg.roguelite.offers import candidate_request, pick_player
from trpg.skillgen.candidates import CandidateRules
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.pick_offer import LEVEL_OFF, PickedSlot, _maker_keywords, pick_slots
from trpg.skillgen.skill_pick import PickCandidate


def _slots(build: str, seed: int) -> list[PickedSlot]:
    lib = library()
    run = new_run(lib, build, seed)
    return pick_slots(
        lib,
        candidate_request(lib, run),
        CandidateRules(composer_tries=lib.roguelite.candidates.composer_tries),
        player=pick_player(lib, run),
        whiteboard=True,
    )


def _makes(candidate: PickCandidate, keywords: tuple[str, ...]) -> bool:
    found = derive_keywords(candidate.skill, library().keywords, exclusive_only=True).makes
    return any(k in found for k in keywords)


def _off(candidate: PickCandidate) -> bool:
    return dict(candidate.parts).get("route_off", 0) < 0


def test_new_direction_makers_come_before_pure_users() -> None:
    checked = 0
    for build in BUILDS:
        for seed in (0, 1, 2):
            for slot in _slots(build, seed):
                keywords = _maker_keywords(slot.original)
                if slot.original.kind != "new":
                    assert keywords == ()
                    continue
                checked += 1
                for off in (False, True):
                    section = [c for c in slot.slate.ranked if _off(c) is off]
                    flags = [_makes(c, keywords) for c in section]
                    # 會製造的全部在前面：一旦出現純利用的，後面不再有會製造的
                    assert flags == sorted(flags, reverse=True), (build, seed, flags)
    assert checked > 0


def test_route_section_still_comes_first() -> None:
    for build in BUILDS:
        for slot in _slots(build, 0):
            offs = [_off(c) for c in slot.slate.ranked]
            assert offs == sorted(offs)


def test_level_off_constant() -> None:
    assert LEVEL_OFF > 0
