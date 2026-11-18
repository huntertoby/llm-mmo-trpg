"""PK-2：挑選模式接上升級三選一（白板）與完整技能三選一——開關兩邊、格子規則、LLM 不能打亂。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from functools import cache

import pytest

from tests.roguelite.helpers import library
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.llm.pick import make_offer_picker, mock_offer_picker, mock_pick_client
from trpg.roguelite import RunState, new_run
from trpg.roguelite.llm_hook import use_picker, use_proposer
from trpg.roguelite.offers import candidate_request, make_offer, offer_key, pick_player
from trpg.roguelite.state import OfferTag, SkillOffer
from trpg.shared.types import top_attribute
from trpg.skillgen.candidates import CandidateRules, LlmTrace, follows_attr, skill_has_keywords
from trpg.skillgen.pick_offer import (
    MAX_OFF_ROUTE,
    OfferPicker,
    PickedSlot,
    SlotChoice,
    SlotPick,
    pick_slots,
    same_structure,
)
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.skill_pick import PickCandidate, design_key, is_nondamage

CASES = (("build_push", 0), ("build_fire", 1), ("build_ranged", 0), ("build_healer", 1))
"""固定的 build 與種子（不用 hypothesis 跑候選池：完整技能每份要 1～6 秒）。"""


@cache
def _off() -> ContentLibrary:
    lib = library()
    return replace(lib, skill_pick=lib.skill_pick.model_copy(update={"enabled": False}))


def _run(build: str, seed: int) -> RunState:
    return new_run(library(), build, seed)


def _family(kind: str, whiteboard: bool) -> str:
    if kind in ("passive", "modifier"):
        return "passive"
    if kind == "reaction":
        return "reaction"
    return "active"


def _slot_keywords_ok(lib: ContentLibrary, skill: SkillDef, keywords: tuple[str, ...]) -> bool:
    """PK-3（06 6.7「候選怎麼篩」）：全部關鍵字；多關鍵字的格子可以放寬成只帶其中一部分。"""
    if skill_has_keywords(skill, keywords, lib):
        return True
    return len(keywords) >= 2 and any(skill_has_keywords(skill, (k,), lib) for k in keywords)


def _check_slots(lib: ContentLibrary, run: RunState, reason: str, offer: SkillOffer) -> None:
    """格子規則：每格的關鍵字（多關鍵字的格子可放寬成部分）、種類都和原本出題（開關關）的那一格
    相同；PK-3 起「跟主路線」改成扣分，偏離最多 2 張（#110）；至少 1 張非傷害（做得到時）；三張不
    重複、都不是手上的技能。"""
    plain = make_offer(_off(), run, reason, pick=True)
    whiteboard = reason == "level_up"
    assert [(t.kind, t.keywords, t.fallback) for t in offer.tags] == [
        (t.kind, t.keywords, t.fallback) for t in plain.tags
    ]
    assert len(offer.off_route) <= MAX_OFF_ROUTE
    for skill, base, tag in zip(offer.candidates, plain.candidates, offer.tags, strict=True):
        assert _family(skill.kind, whiteboard) == _family(base.kind, whiteboard)
        if tag.keywords:
            assert _slot_keywords_ok(lib, skill, tag.keywords)
        assert tag.pick in ("llm", "top")
    assert all(s.id not in run.hero.skills for s in offer.candidates)
    assert len({s.id for s in offer.candidates}) == len(offer.candidates)


@pytest.mark.parametrize(("build", "seed"), CASES)
def test_switch_off_is_the_old_flow(build: str, seed: int) -> None:
    """開關關掉時，``pick=True`` 的呼叫和 PK-2 前完全相同（逐字）。"""
    run = _run(build, seed)
    for reason in ("level_up", "complete"):
        before = make_offer(_off(), run, reason)
        assert make_offer(_off(), run, reason, pick=True) == before
        assert all(t.pick is None for t in before.tags)
        assert "pick" not in before.model_dump(mode="json")["tags"][0]


def test_switch_defaults_on_and_only_for_pick_callers() -> None:
    lib = library()
    assert lib.skill_pick.enabled is True
    run = _run("build_push", 0)
    assert all(t.pick is None for t in make_offer(lib, run, "level_up").tags)  # 任務、許願池照舊
    picked = make_offer(lib, run, "level_up", pick=True)
    assert all(t.pick == "top" for t in picked.tags)
    assert offer_key(lib, run, "level_up", pick=True) != offer_key(lib, run, "level_up")
    assert offer_key(_off(), run, "level_up", pick=True) == offer_key(_off(), run, "level_up")


@pytest.mark.parametrize(("build", "seed"), CASES)
@pytest.mark.parametrize("reason", ["level_up", "complete"])
def test_slot_rules_hold_without_llm(build: str, seed: int, reason: str) -> None:
    lib = library()
    run = _run(build, seed)
    offer = make_offer(lib, run, reason, pick=True)
    assert offer == make_offer(lib, run, reason, pick=True)  # 確定性
    _check_slots(lib, run, reason, offer)


@pytest.mark.parametrize("index", [0, 2, 4, 9])
@pytest.mark.parametrize("reason", ["level_up", "complete"])
def test_mock_always_picking_one_index_cannot_break_slots(index: int, reason: str) -> None:
    """Mock 永遠挑第 ``index`` 號（9＝超出範圍，退回第一名＋組合式名稱）：格子規則照舊。"""
    lib = library()
    run = _run("build_fire", 1).model_copy(update={"llm": True})
    with use_proposer(None), use_picker(mock_offer_picker(lib, index=index)):
        offer = make_offer(lib, run, reason, pick=True)
    _check_slots(lib, run, reason, offer)
    plain = make_offer(lib, run.model_copy(update={"llm": False}), reason, pick=True)
    for skill, base, tag in zip(offer.candidates, plain.candidates, offer.tags, strict=True):
        if tag.pick == "top":
            assert tag.llm is None or not tag.llm.ok
        else:
            assert tag.llm is not None and tag.llm.ok and tag.llm.pick_index == index
            assert tag.llm.prompt_version is not None
        if tag.llm is None:  # 這格不請 LLM（候選太少）：和沒有 LLM 時同一張
            assert skill == base


def test_slate_entries_satisfy_the_slot_and_nondamage_slot() -> None:
    """每格送給 LLM 的每一張候選都符合這一格的條件；非傷害保底格的每一張都是非傷害。"""
    lib = library()
    for build, seed in CASES:
        run = _run(build, seed)
        request = candidate_request(lib, run)
        settings = lib.roguelite.candidates
        slots = pick_slots(
            lib,
            request,
            CandidateRules(composer_tries=settings.composer_tries),
            player=pick_player(lib, run),
            whiteboard=True,
        )
        assert sum(s.nondamage for s in slots) <= 1
        top = top_attribute(run.hero.attributes)
        held = pick_player(lib, run).held_skills
        held_keys = {design_key(h) for h in held}
        for slot in slots:
            if slot.slate.pool_size > 1:  # 只有一張時是留原本那一張（做不出別的）
                for c in slot.slate.ranked:
                    assert c.key not in held_keys and c.skill.id not in {h.id for h in held}
            for c in slot.slate.ranked:
                base = slot.original.skill
                assert _family(c.skill.kind, True) == _family(base.kind, True)
                # PK-3：不符合這一格路線的候選一定帶 route_off 扣分（加深、橋接要跟主路線；
                # 新方向照原本那一張），而且排在符合的後面
                follows = follows_attr(c.skill, top, request.weapon_attrs)
                if slot.original.kind == "new":
                    fits = follows == follows_attr(base, top, request.weapon_attrs)
                else:
                    fits = follows
                parts = dict(c.parts)
                if not fits and c.skill.id != base.id:
                    assert parts.get("route_off", 0) < 0
                    assert all(dict(x.parts).get("route_off", 0) < 0 for x in after(slot, c))
                if slot.original.keywords:
                    assert _slot_keywords_ok(lib, c.skill, slot.original.keywords)
                    if not skill_has_keywords(c.skill, slot.original.keywords, lib):
                        assert parts.get("relaxed", 0) < 0
                if slot.nondamage:
                    assert is_nondamage(c.skill)
        if any(s.nondamage for s in slots):
            offer = make_offer(lib, run, "level_up", pick=True)
            assert any(is_nondamage(s) for s in offer.candidates)


def after(slot: PickedSlot, candidate: PickCandidate) -> list[PickCandidate]:
    """排在 ``candidate`` 後面的候選。"""
    ranked = list(slot.slate.ranked)
    return ranked[ranked.index(candidate) + 1 :]


def test_picker_cannot_change_structure() -> None:
    """挑選器回傳的技能結構和候選不同（例如偷改數值）時不收，照第一名。"""
    lib = library()
    run = _run("build_push", 0).model_copy(update={"llm": True})

    def cheat(slots: Sequence[SlotPick], player: PickPlayer) -> list[SlotChoice | None]:
        out: list[SlotChoice | None] = []
        for slot in slots:
            skill = slot.slate.ranked[0].skill
            changed = skill.model_copy(update={"ap_cost": (skill.ap_cost or 1) + 1})
            assert not same_structure(changed, skill)
            trace = _trace(slot)
            out.append(SlotChoice(position=0, skill=changed, trace=trace, llm=True))
        return out

    picker: OfferPicker = cheat
    with use_picker(picker):
        offer = make_offer(lib, run, "level_up", pick=True)
    plain = make_offer(lib, run.model_copy(update={"llm": False}), "level_up", pick=True)
    assert offer.candidates == plain.candidates
    assert all(t.pick == "top" for t in offer.tags)
    asked = [t for t in offer.tags if t.llm is not None]
    assert asked  # 候選夠多的格子才請 LLM
    assert all(t.llm is not None and t.llm.pick_reason == "pick.structure_changed" for t in asked)


def _trace(slot: SlotPick) -> LlmTrace:
    return LlmTrace(
        keywords=slot.keywords,
        rarity=slot.request.rarity,
        core_primitive=None,
        menu_seed=None,
        theme=None,
        attempts=1,
        ok=True,
    )


def test_picker_time_budget_skips_remaining_slots() -> None:
    """一份三選一用掉 10 秒後，剩下的格子不請 LLM（照第一名、保留原名）。"""
    lib = library()
    ticks = iter(range(0, 1000, 6))
    picker = make_offer_picker(
        lambda slate, seed: mock_pick_client(lib, slate, seed),
        lib,
        clock=lambda: float(next(ticks)),
    )
    run = _run("build_fire", 1).model_copy(update={"llm": True})
    with use_picker(picker):
        offer = make_offer(lib, run, "level_up", pick=True)
    asked = [t for t in offer.tags if t.llm is not None]
    # 第 1 格開始 t=0（之後每次讀時間 +6 秒）：第 1、2 格請過，第 3 格 t≥12 不請
    assert len(asked) <= 2
    assert offer.tags[-1].llm is None


def test_offer_tag_pick_field_round_trip() -> None:
    tag = OfferTag(kind="new", keywords=(), source="composer", pick="top")
    assert OfferTag.model_validate(tag.model_dump(mode="json")) == tag
    plain = OfferTag(kind="new", keywords=(), source="composer")
    assert "pick" not in plain.model_dump(mode="json")


def test_llm_max_calls_caps_the_slots_asked() -> None:
    """大世界機遇（``llm_max_calls``＝1）：候選夠多的格子裡只有第 1 格請 LLM。"""
    lib = library()
    run = _run("build_ranged", 0).model_copy(update={"llm": True})
    with use_picker(mock_offer_picker(lib)):
        free = make_offer(lib, run, "level_up", pick=True)
        capped = make_offer(lib, run, "level_up", pick=True, llm_max_calls=1)
    assert sum(t.pick == "llm" for t in free.tags) >= 2
    assert sum(t.pick == "llm" for t in capped.tags) == 1
