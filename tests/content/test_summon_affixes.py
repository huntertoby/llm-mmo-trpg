"""Phase 3-33f2：召喚專用詞條的內容（schema 規則、白名單、物品、新觸發時機與小特性表）。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from tests.engine.helpers import library
from trpg.content.equipment import AffixDef, AttackAffix, KeywordAffix, TriggerAffix, item_problems
from trpg.content.library import _affix_reference_problems

AFFIX: TypeAdapter[AffixDef] = TypeAdapter(AffixDef)

COOLDOWN = "affix_summon_cooldown"
DURATION = "affix_summon_duration"
SACRIFICE = "affix_summon_sacrifice"
BLAST = "affix_trig_summon_blast"
MEND = "affix_trig_summon_mend"
INHERIT = "affix_summon_inherit_attack"

SLOTS = {
    COOLDOWN: {"offhand", "neck"},
    DURATION: {"offhand", "neck"},
    SACRIFICE: {"ring", "neck"},
    BLAST: {"ring", "neck"},
    MEND: {"ring", "neck"},
    INHERIT: {"weapon", "offhand"},
}


def _data(affix_id: str, **changes: object) -> dict[str, Any]:
    base = library().affixes[affix_id].model_dump(mode="json")
    return {**base, **changes}


def test_the_six_summon_affixes_load_with_the_designed_slots() -> None:
    affixes = library().affixes
    for affix_id, slots in SLOTS.items():
        assert set(affixes[affix_id].slots) == slots, affix_id
    cooldown, duration, sacrifice = affixes[COOLDOWN], affixes[DURATION], affixes[SACRIFICE]
    blast, mend, inherit = affixes[BLAST], affixes[MEND], affixes[INHERIT]
    assert isinstance(cooldown, KeywordAffix) and cooldown.amount == -1
    assert isinstance(duration, KeywordAffix) and duration.amount == 1
    assert isinstance(sacrifice, KeywordAffix)
    assert sacrifice.value is not None and sacrifice.value.max == 200  # +20%
    assert isinstance(blast, TriggerAffix) and blast.trigger == "on_summon_downed"
    assert isinstance(mend, TriggerAffix) and mend.limit == "per_turn"
    assert isinstance(inherit, AttackAffix) and inherit.summon_inherit


def test_numeric_summon_affixes_diminish_and_trigger_ones_do_not_stack() -> None:
    affixes = library().affixes
    assert affixes[COOLDOWN].numeric and affixes[DURATION].numeric and affixes[SACRIFICE].numeric
    assert not affixes[BLAST].numeric and not affixes[MEND].numeric and not affixes[INHERIT].numeric


def test_duration_affix_on_an_off_hand_needs_an_orb() -> None:
    affix = library().affixes[DURATION]
    assert affix.item_tags == {"offhand": ("orb",)}


def test_summon_changes_only_work_with_the_summon_keyword_and_the_right_direction() -> None:
    AFFIX.validate_python(_data(COOLDOWN))
    with pytest.raises(ValidationError, match="keyword: summon"):
        AFFIX.validate_python(_data(COOLDOWN, keyword="ignite"))
    with pytest.raises(ValidationError, match="direction: create"):
        AFFIX.validate_python(_data(COOLDOWN, direction="exploit"))
    with pytest.raises(ValidationError, match="direction: exploit"):
        AFFIX.validate_python(_data(SACRIFICE, direction="create"))


def test_cooldown_must_be_negative_and_duration_positive() -> None:
    with pytest.raises(ValidationError, match="負數"):
        AFFIX.validate_python(_data(COOLDOWN, amount=1))
    with pytest.raises(ValidationError, match="正數"):
        AFFIX.validate_python(_data(DURATION, amount=-1))


def test_sacrifice_affix_needs_a_permille_value() -> None:
    with pytest.raises(ValidationError):
        AFFIX.validate_python(_data(SACRIFICE, value=None, amount=200))
    with pytest.raises(ValidationError, match="permille"):
        AFFIX.validate_python(_data(SACRIFICE, value_unit="flat"))


def test_summon_downed_trigger_needs_exactly_one_sacrifice_effect() -> None:
    AFFIX.validate_python(_data(BLAST))
    with pytest.raises(ValidationError, match="sacrifice_summon"):
        AFFIX.validate_python(_data(BLAST, effects=[{"type": "knock_prone"}]))
    with pytest.raises(ValidationError, match="effect_target: target"):
        AFFIX.validate_python(_data(BLAST, effect_target="self"))
    with pytest.raises(ValidationError, match="只能搭配"):
        AFFIX.validate_python(_data(BLAST, trigger="on_kill"))


def test_inherit_is_exactly_one_of_the_attack_affix_kinds() -> None:
    AFFIX.validate_python(_data(INHERIT))
    with pytest.raises(ValidationError, match="恰好填一個"):
        AFFIX.validate_python(_data(INHERIT, add_element="fire"))


def test_library_checks_references_of_the_new_affixes() -> None:
    lib = library()
    keyword_ids = frozenset(lib.ruleset.keywords.ids())
    for affix_id in SLOTS:
        affix = lib.affixes[affix_id]
        assert not _affix_reference_problems(affix, lib.ruleset, lib.weapons, keyword_ids)


def test_the_new_trigger_is_named_and_not_for_the_random_composer() -> None:
    trigger = library().ruleset.trigger_def("on_summon_downed")
    assert trigger.name_zh == "召喚物倒下時" and trigger.has_other
    assert not trigger.random_composer


def test_test_items_with_the_new_affixes_are_legal() -> None:
    lib = library()
    names = {
        "item_sim_summon_orb": {COOLDOWN, DURATION},
        "item_sim_summon_pendant": {SACRIFICE, BLAST},
        "item_sim_summon_ring": {MEND, SACRIFICE},
        "item_sim_summon_blade": {"affix_attack_mark", INHERIT},
    }
    for item_id, ids in names.items():
        item = lib.items[item_id]
        assert {a.affix for a in item.affixes} == ids
        assert item_problems(item, lib.affixes, lib.weapons, lib.ruleset.equipment) == [], item_id


def test_summon_traits_table() -> None:
    traits = library().ruleset.core.summon_traits
    assert set(traits) == {"sturdy", "swift", "keen"}
    assert traits["sturdy"].armor_bonus == 1 and traits["swift"].speed_bonus == 1
    assert traits["keen"].crit_range_delta == 1
