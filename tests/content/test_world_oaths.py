"""誓約模板內容（Phase 5C-3；``content/world/oaths.yaml``，18 18.6、06 6.26）。"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_oaths import (
    AT_END_CHECKS,
    OathDifficulty,
    OathProposal,
    OathTemplateDef,
    oath_problems,
    resolve_check,
)
from trpg.shared.errors import ContentError

DESIGN = {
    "oath_no_heal": "medium",
    "oath_no_retreat": "medium",
    "oath_attack_each_turn": "easy",
    "oath_hold_high_ground": "hard",
    "oath_no_category": "medium",
    "oath_melee_kills": "easy",
    "oath_no_items": "easy",
    "oath_no_reactions": "medium",
    "oath_one_element": "hard",
    "oath_protect_allies": "hard",
    "oath_still_first_turn": "easy",
    "oath_apply_status": "medium",
    "oath_no_early_defense": "medium",
    "oath_no_surface": "medium",
    "oath_solo": "hard",
}
"""18.6 的 15 種模板與難度（模板 6 的「易／中」由 ``difficulty_by`` 決定）。"""

DIFFICULTIES: tuple[OathDifficulty, ...] = ("easy", "medium", "hard")


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_fifteen_templates_with_chinese_names(library: ContentLibrary) -> None:
    table = library.world_oaths
    assert table is not None
    assert {t.id: t.difficulty for t in table.templates} == DESIGN
    assert table.cooldown_seconds == 86400  # #106
    assert set(table.bonuses) == set(DIFFICULTIES)
    assert (table.penalty_status, table.penalty_rounds) == ("oath_broken", 2)  # #27
    for template in table.templates:
        assert template.check is not None and template.description_zh
        for param in template.params:
            assert param.name_zh
            assert set(param.choice_names_zh) == set(param.choices)
    at_end = sorted(t.id for t in table.templates if t.check and t.check.kind in AT_END_CHECKS)
    assert at_end == ["oath_apply_status", "oath_melee_kills"]


def test_bonuses_scale_with_difficulty(library: ContentLibrary) -> None:
    table = library.world_oaths
    assert table is not None
    rules = library.ruleset
    dealt = [rules.status_def(table.bonuses[d]).damage_dealt_permille for d in DIFFICULTIES]
    assert dealt == sorted(dealt) and dealt[0] > 1000
    penalty = rules.status_def("oath_broken")
    assert penalty.duration == 2 and penalty.polarity == "debuff"


def test_resolve_check_fills_params(library: ContentLibrary) -> None:
    table = library.world_oaths
    assert table is not None
    by_id = table.template_by_id()
    status = by_id["oath_apply_status"]
    check = resolve_check(status, {"status": "burning", "n": 3})
    assert check is not None and (check.status, check.count) == ("burning", 3)
    element = resolve_check(by_id["oath_one_element"], {"element": "ice"})
    assert element is not None and element.element == "ice"
    melee = by_id["oath_melee_kills"]
    assert melee.difficulty_for({"n": 1}) == "easy"
    assert melee.difficulty_for({"n": 2}) == "medium"
    assert status.params_zh({"status": "burning", "n": 3}) == "狀態：燃燒、次數：3"
    bad = OathProposal(template="oath_apply_status", params={"status": "x", "n": 3})
    assert oath_problems(table, bad)
    assert not oath_problems(table, OathProposal(template="oath_solo"))


def _template(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "t",
        "name_zh": "測試",
        "difficulty": "easy",
        "params": [{"id": "c", "name_zh": "類別", "kind": "choice", "choices": ["spell"]}],
        "check": {"kind": "forbid_skill_category"},
        "bind": {"c": "category"},
    }
    data.update(updates)
    return data


def test_schema_rejects_bad_templates() -> None:
    OathTemplateDef.model_validate(_template())
    with pytest.raises(ValidationError, match="缺少"):
        OathTemplateDef.model_validate(_template(bind={}))
    with pytest.raises(ValidationError, match="沒有欄位"):
        OathTemplateDef.model_validate(_template(bind={"c": "element"}))
    with pytest.raises(ValidationError, match="不存在"):
        OathTemplateDef.model_validate(_template(bind={"nope": "category"}))
    with pytest.raises(ValidationError, match="difficulty_by"):
        OathTemplateDef.model_validate(
            _template(difficulty_by={"param": "c", "levels": {"other": "hard"}})
        )


Mutate = Callable[[dict[str, Any]], object]


def _write_oaths(root: Path, mutate: Mutate) -> None:
    path = root / "world" / "oaths.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, allow_unicode=True)


CASES: list[tuple[Mutate, str]] = [
    (lambda d: d["bonuses"].update(easy="nope_status"), "nope_status"),
    (lambda d: d["bonuses"].pop("hard"), "hard"),
    (lambda d: d["templates"][0]["check"].update(tags=["nope_tag"]), "nope_tag"),
    (lambda d: d["templates"][4]["params"][0].update(name_zh=""), "中文名"),
    (lambda d: d["templates"][8]["params"][0]["choice_names_zh"].pop("fire"), "fire"),
    (lambda d: d["templates"][11]["params"][0]["choices"].append("nope_state"), "nope_state"),
]


def test_loader_cross_checks(tmp_path: Path, library: ContentLibrary) -> None:
    root = tmp_path / "content"
    shutil.copytree(library.root, root)
    path = root / "world" / "oaths.yaml"
    original = path.read_text(encoding="utf-8")
    for mutate, needle in CASES:
        path.write_text(original, encoding="utf-8", newline="\n")
        _write_oaths(root, mutate)
        with pytest.raises(ContentError, match=needle):
            load_library(root)
    path.unlink()
    assert load_library(root).world_oaths is None
