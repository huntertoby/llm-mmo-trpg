"""``content/skill_composer.yaml``（Phase 2C-1 3.1）：schema、載入與錯誤資料被拒絕。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.engine.helpers import PROJECT_ROOT, library
from trpg.content.composer_rules import ComposerRules
from trpg.content.library import load_library
from trpg.shared.errors import ContentError
from trpg.skillgen.composer_parts import dice_ladder


def _data() -> dict[str, Any]:
    loaded = yaml.safe_load((PROJECT_ROOT / "content/skill_composer.yaml").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_composer_rules_are_loaded_into_the_library() -> None:
    rules = library().composer
    assert isinstance(rules, ComposerRules)
    assert rules.rarity_weights == {"common": 35, "rare": 35, "epic": 20, "legendary": 10}
    assert rules.ap_weights == {1: 35, 2: 50, 3: 15}
    assert rules.spell_share_permille == {"default": 500, "aura": 850}
    assert (rules.tuning.low_permille, rules.tuning.high_permille) == (750, 950)


def test_ladders_are_derived_from_the_data() -> None:
    rules = library().composer
    ladder = dice_ladder(rules.dice)
    assert ladder[0] == "1d4" and ladder[-1] == "8d12" and len(ladder) == 40
    multipliers = rules.multiplier_ladder()
    assert multipliers[0] == 500 and multipliers[-1] == 10000
    assert list(multipliers) == sorted(multipliers) and len(multipliers) == 25 + 12 + 9


def _mutations() -> list[tuple[str, Any]]:
    def drop_rarity(d: dict[str, Any]) -> None:
        del d["rarity_weights"]["legendary"]

    def bad_ap(d: dict[str, Any]) -> None:
        d["ap_weights"] = {1: 1, 2: 1}

    def no_default(d: dict[str, Any]) -> None:
        del d["spell_share_permille"]["default"]

    def bad_range(d: dict[str, Any]) -> None:
        d["cost"]["uses_per_battle"] = {"min": 3, "max": 1}

    def over_permille(d: dict[str, Any]) -> None:
        d["infuse_permille"] = 1200

    def tuning(d: dict[str, Any]) -> None:
        d["tuning"]["target_margin_permille"] = 900

    def typo(d: dict[str, Any]) -> None:
        d["rarity_weight"] = d.pop("rarity_weights")

    return [
        ("rarity", drop_rarity),
        ("ap", bad_ap),
        ("default", no_default),
        ("range", bad_range),
        ("permille", over_permille),
        ("tuning", tuning),
        ("typo", typo),
    ]


@pytest.mark.parametrize(
    ("name", "change"), _mutations(), ids=lambda v: v if isinstance(v, str) else ""
)
def test_invalid_composer_data_is_rejected(name: str, change: Any) -> None:
    data = _data()
    change(data)
    with pytest.raises(ValidationError):
        ComposerRules.model_validate(data)


def test_missing_composer_file_is_a_content_error(tmp_path: Path) -> None:
    root = tmp_path / "content"
    shutil.copytree(PROJECT_ROOT / "content", root)
    (root / "skill_composer.yaml").unlink()
    with pytest.raises(ContentError):
        load_library(root)


def test_passive_rules_are_present_and_in_range() -> None:
    from tests.engine.helpers import library  # noqa: PLC0415

    rules = library().composer.passive
    assert 0 < rules.skeleton_permille < 1000
    assert rules.mana.min >= 0 and rules.cooldown.min >= 1
