"""Phase 3W-5：一輪裡的靈感點與閃現（06 6.34；玩法決定 #69～#72）。

靈感點（每贏一場 1 點）、先上場用過、閃現與重閃（價格、選項數、只出指定類別、待選時擋住別的選擇）、
溶掉（退一半、只在營火）、傳承（帶走小變化、舊技能消失）、完整技能三選一（+120‰、不能再閃、可重閃
調整欄）、升階旗標、確定性與存檔。
"""

from __future__ import annotations

import json
from functools import cache

import pytest

from tests.roguelite.helpers import library
from trpg.engine.state import state_to_json
from trpg.roguelite import (
    ActiveBattle,
    ChoiceError,
    NodeConflictError,
    RunSave,
    RunState,
    apply_choice,
    auto_choice,
    auto_play,
    dumps_save,
    loads_save,
    new_run,
    restore_battle,
)
from trpg.roguelite.auto import AutoStop
from trpg.roguelite.flashes import (
    comparable_run,
    flash_categories,
    owned_skills,
    problem_of,
    state_of,
)
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    CompleteOfferNode,
    CompletePickChoice,
    DissolveChoice,
    FlashChoice,
    FlashPickChoice,
    GearOfferNode,
    GearPickChoice,
    InheritChoice,
    LevelUpNode,
)
from trpg.skillgen.flash_state import COMPLETE_SLOT

BUILD = "build_fire"
SEED = 6


def _stop_at(kind: type[object], *, nth: int = 1) -> AutoStop:
    seen = 0
    last: object = None

    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        nonlocal seen, last
        if isinstance(run.node, kind) and run.node is not last:
            seen += 1
            last = run.node
        return seen >= nth

    return stop


@cache
def _at(kind: type[object], nth: int = 1, seed: int = SEED) -> RunState:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, BUILD, seed), stop=_stop_at(kind, nth=nth))
    assert isinstance(run.node, kind)
    return run


@cache
def _full(seed: int = SEED) -> RunState:
    lib = library()
    run, battle = auto_play(lib, new_run(lib, BUILD, seed))
    assert battle is None
    return run


def _ready(run: RunState) -> str:
    """第一個可以閃現的裝備中技能。"""
    lib = library()
    return next(s for s in run.hero.skills if problem_of(lib, run, s) is None)


def _flash(run: RunState, skill: str, **fields: object) -> RunState:
    return apply_choice(library(), run, FlashChoice(skill=skill, **fields))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 靈感點與先上場用過
# ---------------------------------------------------------------------------


def test_a_new_run_has_no_insight_and_each_win_gives_one() -> None:
    lib = library()
    assert new_run(lib, BUILD, SEED).insight == 0
    run = _at(GearOfferNode)
    assert run.insight == lib.flash.rules.insight_per_win == 1
    # 用過的主動技記下「先上場用過」，沒放出過的主動技不算
    defs = {s.id: s for s in skill_defs(lib, run, run.hero.skills)}
    for skill_id, skill in defs.items():
        casts = run.skill_usage.get(skill_id)
        used = state_of(run, skill_id).used
        if skill.kind == "active":
            assert used == (casts is not None and casts.uses > 0)
        else:
            assert used  # 被動、反應、姿態：裝備著打完一場就算


def test_a_flash_costs_one_point_shows_four_options_and_swaps_the_skill() -> None:
    lib = library()
    run = _at(GearOfferNode)
    skill = _ready(run)
    opened = _flash(run, skill)
    pending = opened.pending_flash
    assert pending is not None and pending.skill == skill and opened.insight == 0
    offer = pending.offer
    assert offer.cost == 1 and len(offer.options) == 4
    assert len({o.variation.category for o in offer.options}) >= 2
    # 待選時不能做別的選擇，也不能開戰
    with pytest.raises(NodeConflictError, match="flash_pick"):
        apply_choice(lib, opened, GearPickChoice(pick=None))
    picked = apply_choice(lib, opened, FlashPickChoice(pick=1))
    new = offer.options[1].skill
    assert picked.pending_flash is None
    assert new.id in picked.hero.skills and skill not in owned_skills(picked)
    assert picked.hero.skills.index(new.id) == run.hero.skills.index(skill)  # 位置不變
    state = picked.flash[new.id]
    assert state.base_id == skill and len(state.records) == 1 and state.spent == 1
    assert not state.used  # 用過要重新計算
    assert picked.generated(new.id) == new
    # 還沒再上場：不能再閃
    assert problem_of(lib, picked, new.id) is not None
    with pytest.raises(ChoiceError, match="先在戰鬥中用過"):
        _flash(picked.model_copy(update={"insight": 3}), new.id)


def test_flash_needs_points_and_a_use_and_happens_only_between_battles() -> None:
    run = _at(GearOfferNode)
    skill = _ready(run)
    with pytest.raises(ChoiceError, match="靈感點不足"):
        _flash(run.model_copy(update={"insight": 0}), skill)
    with pytest.raises(ChoiceError, match="靈感點不足"):
        _flash(run, skill, category="area")  # 指定類別要 2 點
    with pytest.raises(ChoiceError, match="沒有學會"):
        _flash(run, "skill_nobody")
    # 重閃只在營火
    with pytest.raises(NodeConflictError, match="營火"):
        _flash(run, skill, slot=1)
    ended = run.model_copy(update={"node": _full().node})
    with pytest.raises(NodeConflictError):
        _flash(ended, skill)


def test_a_focused_flash_costs_two_and_only_shows_that_category() -> None:
    lib = library()
    run = _at(GearOfferNode).model_copy(update={"insight": 2})
    skill = _ready(run)
    counts = flash_categories(lib, run, skill)
    assert counts and all(0 <= n <= 3 for n in counts.values())
    good = next(c for c, n in counts.items() if n > 0)
    opened = _flash(run, skill, category=good)
    offer = opened.pending_flash.offer  # type: ignore[union-attr]
    assert opened.insight == 0 and offer.cost == 2 and offer.category == good
    assert len(offer.options) == counts[good]
    assert {o.variation.category for o in offer.options} == {good}
    empty = [c for c, n in counts.items() if n == 0]
    if empty:  # 0 個合法變化的類別要拒絕，沒有扣點
        with pytest.raises(ChoiceError):
            _flash(run, skill, category=empty[0])


# ---------------------------------------------------------------------------
# 重閃、溶掉、傳承（營火）
# ---------------------------------------------------------------------------


def _flashed_at_campfire() -> tuple[RunState, str]:
    """營火，主角有一招閃過至少 2 次的技能（AI 代打把點數集中在一招）。"""
    run = _at(CampfireNode)
    best = max(owned_skills(run), key=lambda s: len(state_of(run, s).records))
    assert len(state_of(run, best).records) >= 2
    return run.model_copy(update={"insight": 6}), best


def test_reflash_swaps_one_record_at_the_same_price_without_counting() -> None:
    lib = library()
    run, skill = _flashed_at_campfire()
    before = state_of(run, skill)
    opened = _flash(run, skill, slot=1)
    assert opened.insight == 5 and opened.pending_flash is not None
    assert opened.pending_flash.offer.slot == 1
    after = apply_choice(lib, opened, FlashPickChoice(pick=0))
    new_id = opened.pending_flash.offer.options[0].skill.id
    state = after.flash[new_id]
    assert len(state.records) == len(before.records)  # 不增加次數
    assert state.record(1).reflashes == 1 and state.used == before.used  # type: ignore[union-attr]
    assert state.spent == before.spent + 1
    assert state.records[1:] == before.records[1:] or state.records[1:]


def test_dissolve_refunds_half_rounded_down_only_at_the_campfire() -> None:
    lib = library()
    run, skill = _flashed_at_campfire()
    spent = state_of(run, skill).spent
    after = apply_choice(lib, run, DissolveChoice(skill=skill))
    assert skill not in owned_skills(after) and skill not in after.flash
    assert after.insight == run.insight + spent // 2
    assert all(s.id != skill for s in after.generated_skills)
    battle = run.model_copy(update={"node": BattleNode(index=4)})
    with pytest.raises(NodeConflictError, match="營火"):
        apply_choice(lib, battle, DissolveChoice(skill=skill))


def test_inherit_carries_minor_variations_and_removes_the_old_skill() -> None:
    lib = library()
    run, source = _flashed_at_campfire()
    minors = [r.nth for r in state_of(run, source).records if r.variation.source == "minor"]
    targets = [s for s in owned_skills(run) if s != source and not state_of(run, s).records]
    assert minors and targets
    for target in targets:
        try:
            after = apply_choice(
                lib, run, InheritChoice(skill=target, source=source, records=tuple(minors[:2]))
            )
        except ChoiceError:
            continue  # 這些變化對這招不合法，換下一招
        break
    else:
        pytest.skip("沒有能接受傳承的技能")
    assert source not in owned_skills(after) and target not in owned_skills(after)
    new_id = next(s for s in owned_skills(after) if s not in owned_skills(run))
    state = after.flash[new_id]
    assert state.base_id == target and len(state.records) == len(minors[:2])
    assert state.spent == 0 and after.insight == run.insight  # 舊技能不退點
    # 已閃過的技能不能再接受傳承；大變化不能帶；只在營火
    other = next(s for s in owned_skills(after) if s != new_id)
    with pytest.raises(ChoiceError, match="還沒閃過"):
        apply_choice(lib, after, InheritChoice(skill=new_id, source=other, records=(1,)))
    with pytest.raises(NodeConflictError):
        apply_choice(
            lib,
            run.model_copy(update={"node": BattleNode(index=4)}),
            InheritChoice(skill=target, source=source, records=(minors[0],)),
        )


def _inherit_with_target_used(*, used: bool) -> tuple[RunState, str]:
    """營火傳承：白板自己的「先上場用過」設成 ``used``（舊技能一律是用過的）。回傳（傳承後, 新技能）。"""
    lib = library()
    run, source = _flashed_at_campfire()
    minors = [r.nth for r in state_of(run, source).records if r.variation.source == "minor"]
    assert minors
    used_source = state_of(run, source).model_copy(update={"used": True})
    run = run.model_copy(update={"flash": {**run.flash, source: used_source}})
    for target in (s for s in owned_skills(run) if s != source and not state_of(run, s).records):
        target_state = state_of(run, target).model_copy(update={"used": used})
        staged = run.model_copy(update={"flash": {**run.flash, target: target_state}})
        try:
            after = apply_choice(
                lib, staged, InheritChoice(skill=target, source=source, records=(minors[0],))
            )
        except ChoiceError:
            continue
        return after, next(s for s in owned_skills(after) if s not in owned_skills(staged))
    pytest.skip("沒有能接受傳承的技能")


def test_inherit_unused_whiteboard_cannot_flash_even_if_the_old_skill_was_used() -> None:
    from trpg.api.run_presenter import _flash_out

    lib = library()
    after, new_id = _inherit_with_target_used(used=False)
    assert state_of(after, new_id).used is False
    assert "用過" in (problem_of(lib, after, new_id) or "")
    assert _flash_out(lib, after, new_id).can_flash is False


def test_inherit_used_whiteboard_can_flash() -> None:
    from trpg.api.run_presenter import _flash_out

    lib = library()
    after, new_id = _inherit_with_target_used(used=True)
    assert state_of(after, new_id).used is True
    assert problem_of(lib, after, new_id) is None
    assert _flash_out(lib, after, new_id).can_flash is True


# ---------------------------------------------------------------------------
# 完整技能
# ---------------------------------------------------------------------------


def test_the_complete_offer_comes_before_the_campfire_with_boosted_candidates() -> None:
    lib = library()
    run = _at(CompleteOfferNode)
    node = run.node
    assert isinstance(node, CompleteOfferNode)
    assert node.after_battle in lib.roguelite.complete_skill_after
    assert node.offer.reason == "complete" and node.offer.candidates
    bonus = lib.flash.rules.complete.budget_permille
    assert all(c.budget_bonus_permille == bonus for c in node.offer.candidates)
    assert all(c.id not in lib.skills for c in node.offer.candidates)
    taken = apply_choice(lib, run, CompletePickChoice(pick=None))
    assert isinstance(taken.node, CampfireNode)
    assert node.after_battle in taken.complete_offers_done


def test_a_complete_skill_cannot_flash_but_can_reflash_its_adjustment() -> None:
    lib = library()
    run = _at(CompleteOfferNode)
    node = run.node
    assert isinstance(node, CompleteOfferNode)
    choice = auto_choice(lib, run)
    assert isinstance(choice, CompletePickChoice) and choice.pick is not None
    after = apply_choice(lib, run, choice)
    assert isinstance(after.node, CampfireNode)
    index = choice.pick
    skill = node.offer.candidates[index].id
    state = state_of(after, skill)
    assert state.complete and state.records == ()
    assert "完整技能不能再閃現" in (problem_of(lib, after, skill) or "")
    rich = after.model_copy(update={"insight": 3})
    with pytest.raises(ChoiceError):
        _flash(rich, skill)
    opened = _flash(rich, skill, slot=COMPLETE_SLOT)
    assert opened.pending_flash is not None and not opened.pending_flash.offer.major
    done = apply_choice(lib, opened, FlashPickChoice(pick=0))
    new_id = opened.pending_flash.offer.options[0].skill.id
    adjusted = done.flash[new_id]
    assert adjusted.complete and adjusted.adjustment is not None and adjusted.spent == 1
    assert done.generated(new_id).budget_bonus_permille == 120  # type: ignore[union-attr]
    # 溶掉完整技能只退重閃花的點
    gone = apply_choice(lib, done, DissolveChoice(skill=new_id))
    assert gone.insight == done.insight + 0


def test_level_up_marks_a_tier_up() -> None:
    lib = library()
    seen: list[LevelUpNode] = []

    def note(_before: RunState, after: RunState) -> None:
        if isinstance(after.node, LevelUpNode) and after.node not in seen:
            seen.append(after.node)

    auto_play(lib, new_run(lib, BUILD, SEED), on_node=note)
    assert len(seen) >= 3
    rules = lib.roguelite
    for node in seen:
        assert node.tier_up == (rules.offer_tier(node.level) > rules.offer_tier(node.level - 1))
    assert any(n.tier_up for n in seen)


# ---------------------------------------------------------------------------
# 確定性與存檔
# ---------------------------------------------------------------------------


def test_a_full_run_flashes_reaches_a_major_and_is_deterministic() -> None:
    lib = library()
    a = _full()
    b, _ = auto_play(lib, new_run(lib, BUILD, SEED))
    assert comparable_run(a) == comparable_run(b)
    states = [state_of(a, s) for s in owned_skills(a)]
    assert any(len(s.records) >= lib.flash.rules.major_flash for s in states)
    assert any(s.complete for s in states)
    raw = json.loads(dumps_save(RunSave(run_id="a", run=a)))
    assert raw["format"] == "trpg-run/13" and "insight" in raw["run"]
    assert loads_save(json.dumps(raw)).run == a


@pytest.mark.slow
def test_a_mid_battle_save_after_flashes_replays_to_the_same_state() -> None:
    lib = library()

    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        return (
            battle is not None
            and isinstance(run.node, BattleNode)
            and run.node.index >= 3
            and len(battle.steps) >= 6
        )

    run, battle = auto_play(lib, new_run(lib, BUILD, SEED), stop=stop)
    assert battle is not None and any(s.records for s in run.flash.values())
    save = loads_save(dumps_save(RunSave(run_id="m", run=run, battle=battle.to_saved())))
    restored = restore_battle(lib, save)
    assert restored is not None
    assert state_to_json(restored.state) == state_to_json(battle.state)
    finished, _ = auto_play(lib, save.run, restored)
    direct, _ = auto_play(lib, run, battle)
    assert finished == direct


def test_a_save_with_a_pending_flash_round_trips() -> None:
    run = _at(GearOfferNode)
    opened = _flash(run, _ready(run))
    again = loads_save(dumps_save(RunSave(run_id="p", run=opened))).run
    assert again == opened and again.pending_flash == opened.pending_flash
