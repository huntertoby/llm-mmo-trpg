"""LB-2b 待決 5（Q12）：被動題目的關鍵字寫法——uses 在前、放不進被動預算的 makes 不列。

規則與數值都不改，只改 prompt 列哪些寫法。全部離線。
"""

from __future__ import annotations

import json
from dataclasses import replace

from trpg.content.library import ContentLibrary
from trpg.llm.prompts.proposal import build_proposal_prompt
from trpg.skillgen.proposal_passive import rule_key, unfit_effect_rules
from trpg.skillgen.proposal_subset import ProposalRequest, available_payload

Q12 = ProposalRequest(1, "epic", skeleton="passive", keywords=("high_ground",))
"""LB-1／LB-2 的第 12 題：1 階史詩被動、關鍵字高處（所有模型都退回）。"""


def _ways(library: ContentLibrary, request: ProposalRequest) -> list[str]:
    prompt = build_proposal_prompt(library, request)
    user = prompt.messages[1]["content"]
    available = json.loads(user.split("<available>\n")[1].split("\n</available>")[0])
    ways: list[str] = available["keywords"][0]["ways"]
    return ways


# -- A：被動題目的 ways -----------------------------------------------------------


def test_q12_ways_drop_terrain_and_lead_with_conditions(library: ContentLibrary) -> None:
    """升降地形固定 7 點，做成 1 階史詩被動一定超預算：不列；條件寫法排前面。"""
    ways = _ways(library, Q12)
    assert "raise_terrain" not in ways and "lower_terrain" not in ways
    assert ways and ways[0].startswith("條件 ")
    assert "條件 height_advantage" in ways


def test_unfit_rules_are_computed_from_the_budget(library: ContentLibrary) -> None:
    """照預算實算（不寫死清單）：高處的升降地形放不進；沒有昂貴產生效果的關鍵字什麼都不拿掉。"""
    subset = build_proposal_prompt(library, Q12).subset
    keywords = library.keywords.by_id()

    def unfit(keyword: str) -> frozenset[str]:
        return unfit_effect_rules(
            library,
            keywords[keyword].makes,
            tier=1,
            rarity="epic",
            primitives=subset.primitives,
            triggers=subset.triggers,
            skeletons=subset.skeletons,
        )

    terrain = {rule_key(r) for r in keywords["high_ground"].makes if "terrain" in r.source_id}
    assert terrain and unfit("high_ground") == terrain
    assert unfit("wet") == frozenset()


def test_active_ways_keep_their_order(library: ContentLibrary) -> None:
    """主動題目不受影響：仍是「製造」在前、升降地形照列。"""
    ways = _ways(library, ProposalRequest(1, "rare", keywords=("high_ground",)))
    assert ways[0] == "raise_terrain"


def test_subset_without_tier_is_not_filtered(library: ContentLibrary) -> None:
    """手組或挑大小時的子集（``tier`` 是 ``None``）照列全部寫法（排序仍是 uses 在前）。"""
    subset = build_proposal_prompt(library, Q12).subset
    assert subset.tier == 1
    bare = available_payload(library, replace(subset, tier=None))["keywords"][0]["ways"]
    assert "raise_terrain" in bare and bare[0].startswith("條件 ")
    assert subset.tokens >= 0
