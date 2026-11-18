"""許願覆蓋表腳本（WC-1，``scripts/wish_coverage.py``）：標籤清單、成功率的加權、做不到的分類、
單桶量測的確定性。"""

from __future__ import annotations

import importlib.util
import sys
from fractions import Fraction
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from trpg.content.library import ContentLibrary

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "wish_coverage.py"


@pytest.fixture(scope="module")
def wc() -> ModuleType:
    spec = importlib.util.spec_from_file_location("wish_coverage", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["wish_coverage"] = module
    spec.loader.exec_module(module)
    return module


def test_all_tags_follow_the_wish_menu(wc: Any, library: ContentLibrary) -> None:
    tags = wc.all_tags(library)
    rules = library.skill_pick.wish_tags
    assert [v for g, v in tags if g == "keywords"] == [k.id for k in library.keywords.keywords]
    assert [v for g, v in tags if g == "elements"] == [i.id for i in rules.elements]
    assert len(tags) == len(set(tags))
    assert {g for g, _ in tags} == {"keywords", "elements", "effects", "shapes", "kinds"}


def _payload(rows: dict[str, dict[str, int]], seeds: int = 10) -> dict[str, Any]:
    return {
        "params": {"tiers": [1]},
        "buckets": [{"key": k, "seeds": seeds, "signatures": sigs} for k, sigs in rows.items()],
    }


def test_rate_weights_kinds_and_alternates_keywords(wc: Any) -> None:
    rows = {
        "-/active/1/common": {"effects:damage|kinds:active": 5},
        "-/passive/1/common": {"effects:damage|kinds:passive": 10},
        "-/reaction/1/common": {},
        "ignite/active/1/common": {"keywords:ignite|keywords:wet|kinds:active": 2},
        "wet/active/1/common": {"keywords:wet|kinds:active": 10},
    }
    measured = wc.Measured.from_payload(
        _payload(rows), {"active": 700, "passive": 200, "reaction": 100}
    )
    damage = measured.rate([("effects", "damage")], 1, "common")
    assert damage == Fraction(700 * 5 + 200 * 10, 1000 * 10)
    active = measured.rate([("effects", "damage"), ("kinds", "active")], 1, "common")
    assert active == Fraction(5, 10)
    pair = measured.rate(
        [("keywords", "ignite"), ("keywords", "wet"), ("kinds", "active")], 1, "common"
    )
    assert pair == Fraction(2, 10) / 2  # 兩個關鍵字各半；wet 桶沒有帶到 ignite
    assert measured.rate([("effects", "heal")], 1, "rare") == 0  # 沒量的桶算 0


def test_classify_rules(wc: Any, library: ContentLibrary) -> None:
    singles = {t: 100 for t in wc.all_tags(library)}
    two_elements = wc.classify(library, [("elements", "fire"), ("elements", "ice")], singles)
    assert two_elements.category == "b" and "07 7.6" in two_elements.source
    passive_line = wc.classify(library, [("shapes", "line"), ("kinds", "passive")], singles)
    assert passive_line.category == "b" and "skeleton" in passive_line.reason
    assert wc._kind_shape_block(library, [("shapes", "around"), ("kinds", "passive")]) is None
    ghost = wc.classify(library, [("keywords", "no_such_keyword")], singles)
    assert ghost.category == "c"


def test_bucket_measurement_is_deterministic(wc: Any) -> None:
    bucket = wc.Bucket(wc.NO_KEYWORD, "active", 1, "common")
    first = wc.run_bucket(bucket, 3)
    second = wc.run_bucket(bucket, 3)
    first.pop("seconds")
    second.pop("seconds")
    assert first == second
    assert sum(first["reasons"].values()) == 3
    assert sum(first["signatures"].values()) == first["legal"]
