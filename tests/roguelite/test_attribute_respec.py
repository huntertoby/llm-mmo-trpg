"""營火的免費屬性重配（Phase 3H-3）：往返、HP 同步、節點限制、存檔與重播一致。"""

from __future__ import annotations

import pytest

from tests.roguelite.helpers import full_library as library
from trpg.roguelite import (
    ActiveBattle,
    ChoiceError,
    NodeConflictError,
    RunState,
    apply_choice,
    auto_play,
    dumps_save,
    loads_save,
    new_run,
)
from trpg.roguelite.attributes import allocate_attributes, respec_attributes, spent_total
from trpg.roguelite.save import RunSave
from trpg.roguelite.state import (
    AllocateChoice,
    BattleNode,
    CampfireNode,
    LeaveChoice,
    LevelUpChoice,
    LevelUpNode,
    RespecAttributesChoice,
)
from trpg.shared.types import Attribute

A = Attribute
BUILD = "build_fire"


def _stop_at(kind: type[object]) -> object:
    def stop(run: RunState, battle: ActiveBattle | None) -> bool:
        return isinstance(run.node, kind)

    return stop


def _campfire(seed: int = 0) -> RunState:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, BUILD, seed), stop=_stop_at(CampfireNode))  # type: ignore[arg-type]
    assert isinstance(run.node, CampfireNode)
    return run


def test_new_run_records_the_opening_allocation_as_refundable() -> None:
    lib = library()
    run = new_run(lib, BUILD, 0, {A.CON: 3, A.WIL: 1})
    assert run.attribute_spent == {A.CON: 3, A.WIL: 1}
    assert run.attribute_points == 0
    assert run.hero.attributes[A.CON] == lib.roguelite.base_attribute + 3


def test_level_up_allocation_is_recorded() -> None:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, BUILD, 0), stop=_stop_at(LevelUpNode))  # type: ignore[arg-type]
    assert isinstance(run.node, LevelUpNode)
    before = spent_total(run)
    after = apply_choice(lib, run, LevelUpChoice(attributes={A.INT: run.node.points}, pick=None))
    assert spent_total(after) == before + run.node.points


def test_respec_then_allocate_round_trip() -> None:
    """重配退回全部點數、屬性回到基礎；重新分配後總點數與 spent 一致。"""
    lib = library()
    run = _campfire()
    base = lib.roguelite.base_attribute
    total = spent_total(run)
    assert total > 0
    refunded = apply_choice(lib, run, RespecAttributesChoice())
    assert isinstance(refunded.node, CampfireNode)  # 不推進節點
    assert refunded.attribute_points == total and refunded.attribute_spent == {}
    assert all(v == base for v in refunded.hero.attributes.values())
    redone = apply_choice(lib, refunded, AllocateChoice(attributes={A.WIS: total}))
    assert redone.attribute_points == 0
    assert redone.hero.attributes[A.WIS] == base + total
    assert redone.attribute_spent == {A.WIS: total}
    again = apply_choice(lib, redone, RespecAttributesChoice())
    assert again.attribute_points == total  # 往返：可以一直重配
    assert again.hero.attributes == refunded.hero.attributes


def test_partial_allocation_keeps_the_remainder() -> None:
    lib = library()
    refunded = apply_choice(lib, _campfire(), RespecAttributesChoice())
    total = refunded.attribute_points
    part = apply_choice(lib, refunded, AllocateChoice(attributes={A.STR: 1}))
    assert part.attribute_points == total - 1
    rest = apply_choice(lib, part, AllocateChoice(attributes={A.DEX: total - 1}))
    assert rest.attribute_points == 0 and spent_total(rest) == total


def test_allocate_validations_leave_the_run_unchanged() -> None:
    lib = library()
    refunded = apply_choice(lib, _campfire(), RespecAttributesChoice())
    total = refunded.attribute_points
    with pytest.raises(ChoiceError, match="屬性點不足"):
        apply_choice(lib, refunded, AllocateChoice(attributes={A.STR: total + 1}))
    with pytest.raises(ChoiceError, match="不可為負"):
        apply_choice(lib, refunded, AllocateChoice(attributes={A.STR: -1, A.DEX: 2}))
    with pytest.raises(ChoiceError, match="沒有要分配"):
        apply_choice(lib, refunded, AllocateChoice())
    with pytest.raises(ChoiceError, match="屬性點不足"):
        allocate_attributes(respec_attributes(new_run(lib, BUILD, 1)), {A.STR: 99})


def test_respec_is_only_allowed_at_the_campfire() -> None:
    lib = library()
    run, _ = auto_play(lib, new_run(lib, BUILD, 0), stop=_stop_at(LevelUpNode))  # type: ignore[arg-type]
    with pytest.raises(NodeConflictError, match="營火"):
        apply_choice(lib, run, RespecAttributesChoice())
    fresh = new_run(lib, BUILD, 0)
    assert isinstance(fresh.node, BattleNode)
    with pytest.raises(NodeConflictError, match="營火"):
        apply_choice(lib, fresh, RespecAttributesChoice())


def test_constitution_respec_adjusts_hp_with_max_hp() -> None:
    lib = library()
    core = lib.ruleset.core
    run = new_run(lib, BUILD, 0, {A.CON: 4})
    camp = run.model_copy(update={"node": CampfireNode(after_battle=2)})
    camp = camp.model_copy(update={"hp": camp.max_hp_in(core)})
    refunded = apply_choice(lib, camp, RespecAttributesChoice())
    drop = camp.max_hp_in(core) - refunded.max_hp_in(core)
    assert drop > 0
    assert refunded.hp == camp.hp - drop  # 目前 HP 同步減少，仍是滿的
    back = apply_choice(lib, refunded, AllocateChoice(attributes={A.CON: 4}))
    assert back.hp == refunded.hp + drop


def test_save_round_trip_after_respec() -> None:
    lib = library()
    refunded = apply_choice(lib, _campfire(0), RespecAttributesChoice())
    state = apply_choice(lib, refunded, AllocateChoice(attributes={A.WIL: 2}))
    text = dumps_save(RunSave(run_id="r1", run=state))
    assert loads_save(text).run == state
    # 重配後的一輪從存檔繼續與直接繼續完全一致（確定性）
    left = apply_choice(lib, state, LeaveChoice())
    assert isinstance(left.node, BattleNode)
    a, _ = auto_play(lib, left)
    b, _ = auto_play(lib, loads_save(text).run)
    c, _ = auto_play(lib, apply_choice(lib, loads_save(text).run, LeaveChoice()))
    assert a == c
    assert b.seed == a.seed


def test_old_saves_without_the_fields_still_load() -> None:
    """舊存檔（沒有 attribute_points／attribute_spent）讀得進來，重配時只退之後分配的點數。"""
    lib = library()
    run = new_run(lib, BUILD, 0)
    data = run.model_dump(mode="json", exclude={"attribute_points", "attribute_spent"})
    old = RunState.model_validate(data)
    assert old.attribute_points == 0 and old.attribute_spent == {}
