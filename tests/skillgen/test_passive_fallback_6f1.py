"""6F-1：新手鏈的被動保底把「新方向」換成被動時，換上的關鍵字還沒有 → 仍是新方向，不標成退回
（實機：只有 2 個關鍵字，「潮濕」被動卻寫「所有關鍵字都有了」）。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.skillgen.candidates import CandidateRequest
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates


def test_new_direction_passives_are_not_marked_as_fallback() -> None:
    lib = library()
    held = {"ignite": 1, "charged": 1}
    checked = 0
    for seed in range(12):
        request = CandidateRequest(
            keyword_counts=held,
            weapon_class="focus",
            seed=seed,
            tier=1,
            mix=(1, 0, 2),
            min_passive=1,
        )
        for candidate in generate_whiteboard_candidates(lib, request):
            if candidate.kind != "new" or not candidate.keywords:
                continue
            checked += 1
            assert candidate.fallback == any(k in held for k in candidate.keywords), (
                seed,
                candidate.keywords,
                candidate.skill.kind,
            )
    assert checked >= 12
