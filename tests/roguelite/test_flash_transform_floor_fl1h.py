"""FL-1h（06 6.34.5「轉型不套強度下限」，玩法 PM 選 (b)）：重閃的整招篩選不套轉型。

RR-2 重現案例（第一個開發起始包、種子 2 打到營火）的「灼燃・燃燒爆」重閃第 3 格（大變化格）：
轉型保底的整招低於現在的卡（RR-2b 報告 c4：20.0 對 23.62），照 (b) 仍是選項之一、不標「比原本弱」；
其他選項照整招篩選，都不低於現在。
"""

from __future__ import annotations

import pytest

from trpg.api.run_presenter import pending_flash_out
from trpg.content.library import ContentLibrary
from trpg.roguelite import auto_play
from trpg.roguelite.flashes import open_flash
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.start import new_dev_run
from trpg.roguelite.state import FlashChoice, RunState
from trpg.skillgen.evolution import budget_power

SEED = 2
MAJOR_SLOT = 3


@pytest.fixture(scope="module")
def campfire(library: ContentLibrary) -> RunState:
    pack = library.dev_starters.packs[0].id
    run = new_dev_run(library, pack, SEED)
    run, _ = auto_play(library, run, stop=lambda r, _b: r.node.kind == "campfire")
    return run.model_copy(update={"insight": 8})


def _charged(run: RunState) -> str:
    return next(
        skill_id
        for skill_id, state in sorted(run.flash.items())
        if (r := state.record(1)) is not None and r.variation.template == "cost_charge"
    )


def test_transform_is_not_filtered_by_the_whole_skill_floor(
    library: ContentLibrary, campfire: RunState
) -> None:
    run = campfire
    skill_id = _charged(run)
    now = budget_power(skill_defs(library, run, [skill_id])[0], library)
    opened = open_flash(library, run, FlashChoice(skill=skill_id, slot=MAJOR_SLOT))
    assert opened.pending_flash is not None
    offer = opened.pending_flash.offer
    assert offer.major and not offer.weaker
    transforms = [o for o in offer.options if o.variation.source == "transform"]
    assert len(transforms) == 1
    # 轉型的整招低於現在，照樣出（不套整招篩選），也不標「比原本弱」
    assert budget_power(transforms[0].skill, library) < now
    assert not transforms[0].weaker
    # 其他選項照整招篩選
    for option in offer.options:
        if option.variation.source != "transform":
            assert budget_power(option.skill, library) >= now
    pending = pending_flash_out(library, opened)
    assert pending is not None and pending.weaker_foot_zh is None
    assert [o.weaker_tag_zh for o in pending.options] == [None] * len(pending.options)
    assert sum(o.transform for o in pending.options) == 1
