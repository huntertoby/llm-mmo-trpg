"""HC-7 a.3：後端剩下的說明文字改從 content 組字；目前的值組出來和以前逐字相同。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.equipment import AttackAffix, weapon_element_problems
from trpg.content.skills.queries import skill_slot_problems
from trpg.content.world_oaths import cooldown_zh


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(86400, "1 天"), (172800, "2 天"), (3600, "1 小時"), (5400, "2 小時"), (5399, "1 小時")],
)
def test_oath_cooldown_text(seconds: int, text: str) -> None:
    assert cooldown_zh(seconds) == text


def test_current_oath_cooldown_reads_one_day() -> None:
    table = library().world_oaths
    assert table is not None
    assert f"解除誓約後 {cooldown_zh(table.cooldown_seconds)}內不能再立誓" == (
        "解除誓約後 1 天內不能再立誓"
    )


def test_tower_shield_line_follows_cover_height() -> None:
    lib = library()
    tower = lib.offhands["tower_shield"]
    assert "攻擊者站得比你高 2 層以上時無視" in "".join(tower.trait_lines_zh(lib.ruleset.core))
    core = lib.ruleset.core.model_copy(update={"tower_shield_cover_height": 2})
    assert "攻擊者站得比你高 3 層以上時無視" in "".join(tower.trait_lines_zh(core))


def test_weapon_element_limit_is_read_from_rules() -> None:
    lib = library()
    elements = [a for a in lib.affixes.values() if isinstance(a, AttackAffix) and a.weapon_element][
        :2
    ]
    assert len(elements) == 2
    limit = lib.ruleset.equipment.max_weapon_element_affixes
    assert weapon_element_problems("劍", elements, limit) == [
        "劍：武器元素詞條同一件最多 1 條（有 2 條）"
    ]
    assert weapon_element_problems("劍", elements, 2) == []


def test_rule_change_legend_limit_is_read_from_slots() -> None:
    lib = library()
    changes = [s for s in lib.skills.values() if s.rule_change_id is not None][:2]
    assert len(changes) == 2
    slots = lib.ruleset.core.skill_slots
    assert slots.rule_change == 1
    found = [p for p in skill_slot_problems(changes, slots) if "規則改變型傳說" in p]
    assert found and found[0].startswith("規則改變型傳說每人最多裝 1 個，收到 2 個")
    wider = slots.model_copy(update={"rule_change": 2})
    assert not [p for p in skill_slot_problems(changes, wider) if "規則改變型傳說" in p]
