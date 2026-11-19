"""許願覆蓋表腳本（WC-1，WC-2 起格式 /2，``scripts/wish_coverage.py``）：標籤清單、成功率的加權、
衍生版本（換元素、第二元素）、召喚桶與手寫技能池、做不到的分類、單桶量測的確定性。"""

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
    # WC-2（#167）：兩個元素 2 階起可以；WC-2b：物理＋元素也可以（物理不佔元素名額）
    assert wc.rule_verdict(library, [("elements", "fire"), ("elements", "ice")]) is None
    assert wc.rule_verdict(library, [("elements", "physical"), ("elements", "ice")]) is None
    two_shapes = wc.classify(library, [("shapes", "line"), ("shapes", "cone")], singles)
    assert two_shapes.category == "b"
    passive_line = wc.classify(library, [("shapes", "line"), ("kinds", "passive")], singles)
    assert passive_line.category == "b" and "skeleton" in passive_line.reason
    assert wc._kind_shape_block(library, [("shapes", "around"), ("kinds", "passive")]) is None
    assert wc._kind_shape_block(library, [("shapes", "single"), ("kinds", "passive")]) is None
    ghost = wc.classify(library, [("keywords", "no_such_keyword")], singles)
    assert ghost.category == "c"


def test_derived_versions_count_only_for_element_wishes(wc: Any) -> None:
    """WC-2：換元素的版本只在願望有元素時算，加第二元素的版本只在有兩個元素時算；召喚桶取較高；
    手寫技能池有一招全帶到＝1。"""
    rows = {
        "-/active/2/rare": {
            "elements:fire|shapes:area#Relements:ice|shapes:area#Delements:fire|elements:ice": 1,
            "shapes:single": 1,
        },
        "-/active/2/rare/summon": {"effects:summon|kinds:active|shapes:single": 2},
    }
    payload = {
        "params": {"tiers": [2]},
        "buckets": [{"key": k, "seeds": 2, "signatures": v} for k, v in rows.items()],
    }
    pool = {("form", "active", 2): (frozenset({"keywords:form", "kinds:active"}),)}
    measured = wc.Measured.from_payload(payload, {"active": 1}, pool)
    area = [("shapes", "area")]
    assert measured.rate(area, 2, "rare") == Fraction(1, 2)
    ice_area = [("elements", "ice"), ("shapes", "area")]
    assert measured.rate(ice_area, 2, "rare") == Fraction(1, 2)
    fire_ice = [("elements", "fire"), ("elements", "ice")]
    assert measured.rate(fire_ice, 2, "rare") == Fraction(1, 2)
    assert measured.rate([("elements", "ice")], 2, "rare") == Fraction(1, 2)
    summon = [("effects", "summon"), ("kinds", "active")]
    assert measured.rate(summon, 2, "rare") == 1
    form = [("keywords", "form"), ("kinds", "active")]
    assert measured.rate(form, 2, "rare") == 1
    assert measured.rate([("keywords", "form"), ("kinds", "passive")], 2, "rare") == 0


def test_compare_lists_fixed_and_remaining(wc: Any) -> None:
    head = ["| 組合 | 最佳格 | 類別 | 理由 | 出處 |", "|---|---|---|---|---|"]
    none = "## 做不到清單（每一格都 0）"
    low = "## 極低清單（最好的一格不到 2%）"
    old = "NL".join([none, "", *head, "| A | 0% |", "| B | 0% |", "| C | 0% |"])
    new = "NL".join([none, "", *head, "| C | 0% |", "| D | 0% |", low, "", *head, "| B | 1% |"])
    found = wc.compare_lines(old.replace("NL", chr(10)), new.replace("NL", chr(10)))
    at = {line: i for i, line in enumerate(found)}
    assert found[at["### 做不到 → 做得到（最好的一格 ≥ 2%）（1）"] + 2] == "- A"
    assert found[at["### 做不到 → 極低（最好的一格 < 2%）（1）"] + 2] == "- B"
    assert found[at["### 還是做不到（1）"] + 2] == "- C"
    assert found[at["### 新出現的做不到（舊表沒有）（1）"] + 2] == "- D"


def test_bucket_measurement_is_deterministic(wc: Any) -> None:
    bucket = wc.Bucket(wc.NO_KEYWORD, "active", 1, "common")
    first = wc.run_bucket(bucket, 3)
    second = wc.run_bucket(bucket, 3)
    first.pop("seconds")
    second.pop("seconds")
    assert first == second
    assert sum(first["reasons"].values()) == 3
    assert sum(first["signatures"].values()) == first["legal"]


def test_report_without_data_asks_to_run_first(
    wc: Any, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SK-4：``buckets.json`` 不進版控；沒有資料時 ``report`` 不寫表，提示先跑 ``run``。"""
    out = tmp_path / "table.md"
    code = wc.main(["report", "--data", str(tmp_path / "missing.json"), "--out", str(out)])
    assert code == 2
    assert not out.exists()
    assert "wish_coverage.py run" in capsys.readouterr().err


def test_bucket_data_is_not_tracked() -> None:
    """SK-4：覆蓋表的大資料檔列在 ``.gitignore``。"""
    ignore = (SCRIPT.parents[1] / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "docs/phases/WC-1資料/buckets.json" in ignore
    assert "docs/phases/WC-2資料/buckets.json" in ignore
