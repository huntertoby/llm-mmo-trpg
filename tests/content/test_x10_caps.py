"""X10-1：擋住量類 ×10 的 schema 上限都放寬到 ×10（``docs/phases/X10-影響盤點.md`` 第 3 節）。

內容與戰鬥不變（現有內容都在舊上限內）；X10-2 換算後的數值要能通過驗證。
"""

from __future__ import annotations

import annotated_types
import pytest
from pydantic import BaseModel, ValidationError

from trpg.content.battle import StatusDef, SummonDetonate, SummonPulse
from trpg.content.environment import ReactionDef
from trpg.content.flash_templates import FlashRules
from trpg.content.forms import FormTable
from trpg.content.races import RaceEffect
from trpg.content.rules import SummonGrowth, SummonTrait
from trpg.content.skills.constants import _MAX_FLAT_BONUS
from trpg.content.world_encounters import ArmorMod, ArmorMods


def _bounds(model: type[BaseModel], name: str) -> tuple[int | None, int | None]:
    low: int | None = None
    high: int | None = None
    for item in model.model_fields[name].metadata:
        if isinstance(item, annotated_types.Ge):
            low = int(item.ge)  # type: ignore[call-overload]
        if isinstance(item, annotated_types.Le):
            high = int(item.le)  # type: ignore[call-overload]
    return low, high


@pytest.mark.parametrize(
    ("model", "name", "high"),
    [
        (StatusDef, "attack_bonus", 100),
        (StatusDef, "shield_reflect", 50),
        (StatusDef, "shield_end_heal", 100),
        (StatusDef, "shield_break_lightning", 100),
        (SummonDetonate, "flat", 200),
        (SummonPulse, "heal_flat", 100),
        (SummonPulse, "shield_flat", 100),
        (ReactionDef, "shield_flat", 200),
        (FlashRules, "trigger_flat_bonus", 100),
        (FormTable, "upkeep_stamina", 200),
        (FormTable, "upkeep_mana", 200),
        (FormTable, "stance_upkeep_stamina", 100),
        (FormTable, "stance_upkeep_mana", 100),
        (SummonGrowth, "hp_per_level", 200),
        (SummonGrowth, "hp_per_attr_mod", 200),
        (SummonGrowth, "flat_per_level_permille", 50000),
        (SummonGrowth, "flat_per_attr_mod_permille", 50000),
        (SummonTrait, "armor_bonus", 30),
        (ArmorMod, "amount", 50),
        (ArmorMods, "max_total", 100),
        (RaceEffect, "amount", 100),
    ],
)
def test_upper_bounds_allow_x10(model: type[BaseModel], name: str, high: int) -> None:
    assert _bounds(model, name)[1] == high


def test_lower_bounds_allow_x10() -> None:
    assert _bounds(ArmorMod, "amount")[0] == -50
    assert _bounds(ArmorMods, "min_total")[0] == -100


def test_flat_bonus_cap() -> None:
    assert _MAX_FLAT_BONUS == 100


def test_race_amount_only_widened_for_restore_choice() -> None:
    RaceEffect(type="restore_choice", resources=("mana",), amount=100)
    RaceEffect(type="bonus_move", amount=10)
    with pytest.raises(ValidationError, match="amount 不可超過 10"):
        RaceEffect(type="bonus_move", amount=11)
