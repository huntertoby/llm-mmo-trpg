"""HC-5a（HC-4d 裁定 1）：``TrapSpec.rounds`` 改必填；skillgen 試組陷阱與工坊草稿表單明確帶值。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from tests.skillgen.test_trap_shape_plain import _DRAFT
from trpg.content.skills import TrapSpec
from trpg.skillgen.option_effect_rules import probe_trap
from trpg.skillgen.options import draft_options

LIB = library()


@pytest.mark.parametrize("trigger", ["enter", "delay"])
def test_rounds_has_no_program_default(trigger: str) -> None:
    with pytest.raises(ValidationError, match="rounds"):
        TrapSpec.model_validate({"trigger": trigger})
    assert TrapSpec.model_validate({"trigger": trigger, "rounds": 2}).rounds == 2


def test_every_content_trap_writes_its_rounds() -> None:
    traps = [s.trap for s in LIB.skills.values() if s.trap is not None]
    assert traps
    assert all(t.rounds >= 1 for t in traps)


def test_probe_trap_takes_the_shortest_enter_rounds() -> None:
    """試組時補的陷阱：踩到時觸發、組合器 enter 陷阱最短的輪數（現值 2，同原本的程式預設）。"""
    trap = probe_trap(LIB)
    assert trap == {"trigger": "enter", "rounds": LIB.composer.trap.enter_rounds.min}
    TrapSpec.model_validate(trap)


def test_workshop_form_default_rounds_come_from_content() -> None:
    opts = draft_options({**_DRAFT, "trap": {"trigger": "enter"}}, LIB)
    trap = next(f for s in opts.steps for f in s.fields if f.field == "trap")
    rounds = next(f for f in trap.fields if f.field == "rounds")
    assert rounds.default == probe_trap(LIB)["rounds"]
