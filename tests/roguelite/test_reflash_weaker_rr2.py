"""RR-2：被強度下限卡住的重閃格改出較弱的候選並提醒（#160，06 6.34.3「強度下限」例外）。

重現案例（RR-1 報告待決 2）：第一個開發起始包、種子 2 的一輪打到營火。「灼燃・燃燒爆」第 1 次是
蓄力，預算分數很高；重閃第 1 格時照原規則（不低於被換掉的那一筆）沒有任何候選達得到，以前只能
標灰。現在這一格改出不低於重閃前一筆、但低於被換掉那一筆的候選：入口與選類別面板掛提醒、出題後
固定區換句（RR-2b 撤掉「比原本弱」小標），選了寫進歷程的下限是 0（重推得出同一張卡）。其他格（達得到
下限）照原規則不變。RR-2b：所有重閃的「前 → 後」都用現在的卡當基準（06 6.34.3 #160 第 4 點）。
"""

from __future__ import annotations

import dataclasses
from unittest import mock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from trpg.api.flash_changes import base_stats, flash_changes
from trpg.api.run_presenter import _flash_out, pending_flash_out
from trpg.content.library import ContentLibrary
from trpg.roguelite import auto_play
from trpg.roguelite.flashes import flash_request, open_flash, pick_flash
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.start import new_dev_run
from trpg.roguelite.state import FlashChoice, FlashPickChoice, RunState
from trpg.skillgen import flash_offer
from trpg.skillgen.evolution import budget_power
from trpg.skillgen.flash_derive import derive_chain, derive_skill
from trpg.skillgen.flash_offer import (
    REFLASH_WEAKER_PICK_ZH,
    REFLASH_WEAKER_ZH,
    WEAKER_FOOT_ZH,
    FlashRequest,
    has_options,
    make_offer,
    reflash_weaker,
)
from trpg.skillgen.flash_state import with_reflash

SEED = 2
BLOCKED_SLOT = 1


@pytest.fixture(scope="module")
def campfire(library: ContentLibrary) -> RunState:
    pack = library.dev_starters.packs[0].id
    run = new_dev_run(library, pack, SEED)
    run, _ = auto_play(library, run, stop=lambda r, _b: r.node.kind == "campfire")
    return run.model_copy(update={"insight": 8})


def _charged(run: RunState) -> str:
    """歷程第 1 次是蓄力的那一招（重現案例的「灼燃・燃燒爆」）。"""
    found = [
        skill_id
        for skill_id, state in sorted(run.flash.items())
        if (r := state.record(BLOCKED_SLOT)) is not None and r.variation.template == "cost_charge"
    ]
    assert len(found) == 1
    return found[0]


def _strict_has_options(library: ContentLibrary, request: FlashRequest) -> bool:
    """照原規則（不放寬下限）有沒有選項。"""
    with mock.patch.object(flash_offer, "_weaker", return_value=False):
        return flash_offer._has_options(library, request)


def test_floor_blocked_slot_offers_weaker_options(
    library: ContentLibrary, campfire: RunState
) -> None:
    run = campfire
    skill_id = _charged(run)
    request = flash_request(library, run, skill_id, slot=BLOCKED_SLOT)
    # 照原規則出不了題（RR-1 時標灰的原因）；現在改成較弱的候選
    assert not _strict_has_options(library, request)
    assert reflash_weaker(library, request) and has_options(library, request)
    # 入口不標灰，掛提醒字；選類別面板的那句也由伺服器給（RR-2b：不另跳確認框）
    slots = {s.slot: s for s in _flash_out(library, run, skill_id).reflash_slots}
    blocked = slots[BLOCKED_SLOT]
    assert blocked.available and blocked.problem_zh is None
    assert blocked.weaker and blocked.weaker_zh == REFLASH_WEAKER_ZH
    assert blocked.weaker_pick_zh == REFLASH_WEAKER_PICK_ZH
    # 扣點出題：每個選項都標較弱、下限 0，第 1 格的分數低於被換掉的那一筆、不低於重閃前
    chain = derive_chain(library, request.base, request.state, request.seed, request.tier)
    replaced = budget_power(chain[BLOCKED_SLOT - 1], library)
    before = budget_power(
        derive_skill(
            library,
            request.base,
            request.state.model_copy(update={"records": ()}),
            request.seed,
            request.tier,
        ),
        library,
    )
    opened = open_flash(library, run, FlashChoice(skill=skill_id, slot=BLOCKED_SLOT))
    assert opened.insight < run.insight
    assert opened.pending_flash is not None
    offer = opened.pending_flash.offer
    assert offer.weaker and offer.options
    for option in offer.options:
        assert option.weaker and option.floor_permille == 0
        state = with_reflash(request.state, BLOCKED_SLOT, option.variation)
        slot_skill = derive_chain(library, request.base, state, request.seed, request.tier)[0]
        assert before <= budget_power(slot_skill, library) < replaced
    # 面板：固定區換句；「比原本弱」小標撤掉（RR-2b），JSON 裡沒有這個欄位
    pending = pending_flash_out(library, opened)
    assert pending is not None and pending.weaker_foot_zh == WEAKER_FOOT_ZH
    assert all("weaker_tag_zh" not in o for o in pending.model_dump(mode="json")["options"])
    # 「前」是現在的卡（RR-2b）：原技能列與「前 → 後」都和現在的卡比
    # （注意：引擎保證的是被換掉那一格不低於它的前一筆，不是整招不低於現在的卡；
    # 見 RR-2b 報告待決 1）
    current = skill_defs(library, run, [skill_id])[0]
    assert pending.base_stats == base_stats(library, current)
    for option, out_option in zip(offer.options, pending.options, strict=True):
        keyword = option.variation.keyword
        assert out_option.changes == flash_changes(library, current, option.skill, keyword=keyword)
    # 選了寫進歷程：下限 0，重推得出同一張卡
    picked = pick_flash(library, opened, FlashPickChoice(pick=0))
    assert picked.pending_flash is None
    new_id = next(k for k, v in picked.flash.items() if v.base_id == request.state.base_id)
    record = picked.flash[new_id].record(BLOCKED_SLOT)
    assert record is not None and record.floor_permille == 0
    assert record.variation == offer.options[0].variation
    rederived = derive_skill(
        library, request.base, picked.flash[new_id], request.seed, request.tier
    )
    assert rederived == offer.options[0].skill


def test_slots_that_reach_the_floor_are_unchanged(
    library: ContentLibrary, campfire: RunState
) -> None:
    """達得到下限的格子照原規則：不標提醒、選項不標較弱、下限照被換掉的那一筆。"""
    run = campfire
    skill_id = _charged(run)
    slots = {s.slot: s for s in _flash_out(library, run, skill_id).reflash_slots}
    for slot, out in slots.items():
        if slot == BLOCKED_SLOT:
            continue
        request = flash_request(library, run, skill_id, slot=slot)
        assert _strict_has_options(library, request)
        assert not reflash_weaker(library, request)
        assert out.available and not out.weaker
        assert out.weaker_zh is None and out.weaker_pick_zh is None
        opened = open_flash(library, run, FlashChoice(skill=skill_id, slot=slot))
        assert opened.pending_flash is not None
        offer = opened.pending_flash.offer
        assert not offer.weaker
        assert all(not o.weaker and o.floor_permille > 0 for o in offer.options)
        pending = pending_flash_out(library, opened)
        assert pending is not None and pending.weaker_foot_zh is None
        # RR-2b：一般重閃的「前 → 後」也用現在的卡當基準（同新的閃現）
        current = skill_defs(library, run, [skill_id])[0]
        assert pending.base_stats == base_stats(library, current)
        for option, out_option in zip(offer.options, pending.options, strict=True):
            keyword = option.variation.keyword
            assert out_option.changes == flash_changes(
                library, current, option.skill, keyword=keyword
            )
        # 存檔欄位：沒有較弱時不輸出
        assert "weaker" not in offer.model_dump(mode="json")
        assert all("weaker" not in o for o in offer.model_dump(mode="json")["options"])


def test_new_flash_never_uses_the_weaker_rule(library: ContentLibrary, campfire: RunState) -> None:
    run = campfire
    for skill_id in sorted(run.flash):
        assert not reflash_weaker(library, flash_request(library, run, skill_id))


# ---------------------------------------------------------------------------
# 性質測試：同種子同結果；達得到下限時與原規則一模一樣
# ---------------------------------------------------------------------------

_PROPERTY = settings(
    max_examples=6,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


def _request(library: ContentLibrary, run: RunState, seed: int, slot: int) -> FlashRequest:
    request = flash_request(library, run, _charged(run), slot=slot)
    return dataclasses.replace(request, seed=seed)


@_PROPERTY
@given(seed=st.integers(min_value=0, max_value=2**31 - 1), slot=st.sampled_from([1, 2, 3]))
def test_same_seed_same_offer(
    library: ContentLibrary, campfire: RunState, seed: int, slot: int
) -> None:
    request = _request(library, campfire, seed, slot)
    library.flash_option_cache.clear()
    first = (reflash_weaker(library, request), make_offer(library, request))
    library.flash_option_cache.clear()
    second = (reflash_weaker(library, request), make_offer(library, request))
    assert first == second
    weaker, offer = first
    assert offer.weaker == weaker
    assert all(o.weaker == weaker for o in offer.options)
    if weaker:
        assert all(o.floor_permille == 0 for o in offer.options)


@_PROPERTY
@given(seed=st.integers(min_value=0, max_value=2**31 - 1), slot=st.sampled_from([1, 2, 3]))
def test_reachable_floor_keeps_the_original_offer(
    library: ContentLibrary, campfire: RunState, seed: int, slot: int
) -> None:
    """只要照原規則有一個候選達得到下限，出題與原規則逐字相同（不混進較弱的）。"""
    request = _request(library, campfire, seed, slot)
    if not _strict_has_options(library, request):
        assert reflash_weaker(library, request)
        return
    assert not reflash_weaker(library, request)
    with mock.patch.object(flash_offer, "_weaker", return_value=False):
        strict = make_offer(library, request)
    assert make_offer(library, request) == strict
    assert not strict.weaker
