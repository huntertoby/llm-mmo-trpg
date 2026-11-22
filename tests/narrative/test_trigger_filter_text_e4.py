"""E4（#175）：新時機與觸發篩選的卡片句子、工坊文字、LLM 說明、預算係數。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import TriggerSpec
from trpg.narrative.skills import trigger_filter_text, trigger_timing_text
from trpg.shared.types import Element


def test_new_timings_have_names_hints_and_workshop_text() -> None:
    rules = library().ruleset
    ids = {e.id for e in library().workshop_text.texts}
    for trigger_id, name in (("on_block", "格擋時"), ("on_displace", "你讓別人位移時")):
        definition = rules.trigger_def(trigger_id)
        assert definition.name_zh == name
        assert definition.llm_hint and definition.has_other
        assert not definition.random_composer  # 一般抽選不抽：既有種子不變
        assert definition.coefficient_permille(None) == 250  # 保守的初值（工坊可調）
        assert f"觸發.{trigger_id}" in ids


def test_timing_text_without_filters_is_unchanged() -> None:
    lib = library()
    assert trigger_timing_text(lib, TriggerSpec(event="on_hit")) == "命中時"
    assert trigger_timing_text(lib, TriggerSpec(event="on_block")) == "格擋時"
    assert trigger_timing_text(lib, TriggerSpec(event="on_displace")) == "你讓別人位移時"


def test_filters_are_written_on_the_card() -> None:
    lib = library()
    spec = TriggerSpec(event="on_hit", element=Element.FIRE, attack_kind="melee")
    assert trigger_timing_text(lib, spec) == "命中時（只算火焰傷害、近戰）"
    oa = TriggerSpec(event="on_hit", source="reaction", reaction="opportunity_attack")
    assert trigger_timing_text(lib, oa) == "命中時（只算反應：藉機攻擊）"
    block = TriggerSpec(event="on_block", attack_kind="ranged")
    assert trigger_timing_text(lib, block) == "格擋時（只算遠程）"
    hurt = TriggerSpec(event="on_damaged", element=Element.POISON, source="skill")
    assert trigger_timing_text(lib, hurt) == "受傷時（只算毒素傷害、技能）"


def test_filter_text_is_empty_without_filters() -> None:
    assert trigger_filter_text(library(), TriggerSpec(event="on_damaged")) == ""
