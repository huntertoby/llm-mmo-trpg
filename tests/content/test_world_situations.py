"""情境模板、情境規則與提議 schema（Phase 5B-2；``docs/phases/Phase5計畫.md`` 9.7）。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from trpg.content.library import ContentLibrary, load_library
from trpg.content.world_events import EventSkeletonTable, SolutionDef, world_event_problems
from trpg.content.world_situations import (
    CareClaim,
    SituationProposal,
    SituationRules,
    SituationTemplateTable,
    default_proposal,
    proposal_problems,
    situation_problems,
)
from trpg.shared.errors import ContentError
from trpg.shared.types import Attribute


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


@pytest.fixture(scope="module")
def rules(library: ContentLibrary) -> SituationRules:
    found = library.world_event_content.situations.rules
    assert found is not None
    return found


@pytest.fixture(scope="module")
def table(library: ContentLibrary) -> SituationTemplateTable:
    return library.world_event_content.situations.templates["cloud_ridge"]


def _template(**updates: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": "test_tpl",
        "skeleton": "wounded_peddler",
        "solution": 1,
        "note_zh": "測試",
        "methods": ["tracking", "force"],
        "attributes": ["wis", "str"],
        "base_dc": 12,
        "danger": 2,
        "success": {"rewards": {"xp_permille": 1000, "threads": ["peddler_owes_you"]}},
        "partial": {},
        "failure": {"penalties": {"hurt_permille": 100}},
    }
    data.update(updates)
    return data


def _problems(library: ContentLibrary, rules: SituationRules, **updates: Any) -> list[str]:
    table = SituationTemplateTable.model_validate(
        {"region": "cloud_ridge", "templates": [_template(**updates)]}
    )
    content = library.world_event_content
    return situation_problems(
        table,
        rules=rules,
        events=content.events["cloud_ridge"],
        world_map=library.world_maps["cloud_ridge"],
        status_ids=library.ruleset.statuses.by_id(),
        thread_ids={t for e in content.events.values() for t in e.thread_ids()},
    )


# ---------------------------------------------------------------------------
# 雲嶺資料
# ---------------------------------------------------------------------------


def test_cloud_ridge_loads(library: ContentLibrary, table: SituationTemplateTable) -> None:
    assert len(table.templates) == 23
    events = library.world_event_content.events["cloud_ridge"]
    covered = {(t.skeleton, t.solution) for t in table.templates}
    wanted = {
        (s.id, i)
        for s in events.skeletons
        for i, sol in enumerate(s.solutions)
        if sol.kind == "situation"
    }
    assert covered == wanted  # 每個情境判定解法剛好一個模板
    assert all(2 <= len(t.attributes) <= 3 for t in table.templates)
    convoy = table.template_by_id()["convoy_steal"]
    assert convoy.advantage_threads == ("gang_fort_secret_door",)


def test_attribute_coverage_reported(table: SituationTemplateTable) -> None:
    """9.6.4 #45：每個屬性出現在約 1/3～1/2 的模板（報告列實際數字，這裡只擋極端）。"""
    total = len(table.templates)
    for attribute in Attribute:
        count = sum(attribute in t.attributes for t in table.templates)
        assert total // 5 <= count <= total * 3 // 5, (attribute, count)


def test_rules(rules: SituationRules) -> None:
    assert len(rules.methods) == 12
    assert rules.race_methods["fox"] == "parley"
    assert len(rules.race_methods) == 10
    assert (rules.check.dc_shift_max, rules.check.care_max, rules.check.race_bonus) == (2, 2, 1)


# ---------------------------------------------------------------------------
# 壞資料
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"attributes": ["wis"]}, "at least 2"),
        ({"attributes": ["wis", "str", "dex", "con"]}, "at most 3"),
        ({"attributes": ["wis", "wis"]}, "attributes 重複"),
        ({"methods": ["tracking", "tracking"]}, "methods 重複"),
        (
            {"weaknesses": [{"id": "w", "text_zh": "弱點", "methods": ["stealth"]}]},
            "不在模板方法裡",
        ),
        ({"base_dc": 31}, "less than or equal to 30"),
    ],
)
def test_bad_template_shape(updates: dict[str, Any], match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        SituationTemplateTable.model_validate(
            {"region": "cloud_ridge", "templates": [_template(**updates)]}
        )


@pytest.mark.parametrize(
    ("updates", "match"),
    [
        ({"methods": ["tracking", "teleport"]}, "未知的方法 teleport"),
        ({"methods": ["tracking"]}, "屬性 str 沒有模板方法能用"),
        ({"methods": ["tracking", "force", "stealth"]}, "方法 stealth 的常見屬性都不在模板屬性裡"),
        ({"skeleton": "nope"}, "沒有事件骨架 nope"),
        ({"solution": 0}, "不是情境判定"),
        ({"solution": 9}, "沒有第 9 個解法"),
        ({"attributes": ["str", "wis"]}, "開頭必須是骨架解法的屬性"),
        ({"success": {"rewards": {"threads": ["temple_pass"]}}}, "不是骨架 wounded_peddler 的線頭"),
        ({"success": {"rewards": {"reveal": ["bamboo_path"]}}}, "不是可由情境判定揭露的隱藏地點"),
        ({"success": {"rewards": {"reveal": ["crane_cliff"]}}}, "不是可由情境判定揭露的隱藏地點"),
        ({"success": {"rewards": {"buffs": ["no_status"]}}}, "未知的狀態 no_status"),
        ({"success": {"rewards": {"supplies": 3}}}, "補給 3 超過預算 2"),
        (
            {"success": {"rewards": {"threads": ["peddler_owes_you", "wolves_driven_down", "x"]}}},
            "線頭 3 超過預算 2",
        ),
        ({"success": {"rewards": {"buffs": ["empowered", "hasted"]}}}, "buff 2 超過預算 1"),
        ({"failure": {"penalties": {"reinforce": True}}}, "危險度 2 不允許懲罰 reinforce"),
        ({"danger": 1, "failure": {"penalties": {"hurt_permille": 10}}}, "不允許懲罰 hurt"),
        ({"failure": {"penalties": {"hurt_permille": 300}}}, "超過上限 250‰"),
        ({"advantage_threads": ["nope"]}, "advantage_threads 是未知的線頭 nope"),
    ],
)
def test_cross_file_problems(
    library: ContentLibrary, rules: SituationRules, updates: dict[str, Any], match: str
) -> None:
    problems = _problems(library, rules, **updates)
    assert any(match in p for p in problems), problems


def test_valid_template_has_no_problems(library: ContentLibrary, rules: SituationRules) -> None:
    assert _problems(library, rules) == []


@pytest.mark.parametrize(
    ("check", "match"),
    [
        ({"dc_shift_max": 3}, "less than or equal to 2"),
        ({"care_max": 3}, "less than or equal to 2"),
        ({"race_bonus": 2}, "less than or equal to 1"),
    ],
)
def test_rules_cannot_loosen_design(
    rules: SituationRules, check: dict[str, int], match: str
) -> None:
    data = rules.model_dump()
    data["check"] = {**data["check"], **check}
    with pytest.raises(ValidationError, match=match):
        SituationRules.model_validate(data)


def test_rules_internal_checks(rules: SituationRules) -> None:
    data = rules.model_dump()
    data["race_methods"] = {**data["race_methods"], "fox": "flying"}
    with pytest.raises(ValidationError, match="方法 flying 不存在"):
        SituationRules.model_validate(data)
    data = rules.model_dump()
    data["dangers"] = data["dangers"][:2]
    with pytest.raises(ValidationError, match="危險度必須 1～3 各一筆"):
        SituationRules.model_validate(data)


def _copy_content(tmp_path: Path, library: ContentLibrary) -> Path:
    content = tmp_path / "content"
    shutil.copytree(library.root, content)
    return content


def test_bad_file_raises(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "situations" / "cloud_ridge.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["templates"][0]["methods"] = ["tracking", "teleport"]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="未知的方法 teleport"):
        load_library(content)


def test_unknown_race_in_rules(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    path = content / "world" / "situation_rules.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["race_methods"]["merfolk"] = "endurance"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match="未知的種族 merfolk"):
        load_library(content)


def test_missing_situation_files_is_empty(tmp_path: Path, library: ContentLibrary) -> None:
    content = _copy_content(tmp_path, library)
    shutil.rmtree(content / "world" / "situations")
    (content / "world" / "situation_rules.yaml").unlink()
    loaded = load_library(content)
    assert loaded.world_event_content.situations.templates == {}
    assert loaded.world_event_content.situations.rules is None


# ---------------------------------------------------------------------------
# 機遇條件
# ---------------------------------------------------------------------------


def test_requires_keyword_only_for_opportunity() -> None:
    SolutionDef(kind="opportunity", requires_keyword="charged")
    with pytest.raises(ValidationError, match="只有 opportunity"):
        SolutionDef(kind="combat", requires_keyword="charged")


def test_unknown_keyword(library: ContentLibrary) -> None:
    content = library.world_event_content
    data = content.events["cloud_ridge"].model_dump()
    for skeleton in data["skeletons"]:
        for solution in skeleton["solutions"]:
            if solution["kind"] == "opportunity":
                solution["requires_keyword"] = "sparkly"
    problems = world_event_problems(
        EventSkeletonTable.model_validate(data),
        world_map=library.world_maps["cloud_ridge"],
        npcs=content.npcs["cloud_ridge"],
        weather_ids=library.weather,
        thread_ids=content.events["cloud_ridge"].thread_ids(),
        keyword_ids={k.id for k in library.keywords.keywords},
    )
    assert any("未知的關鍵字 sparkly" in p for p in problems)


# ---------------------------------------------------------------------------
# 提議
# ---------------------------------------------------------------------------


def test_proposal_problems(table: SituationTemplateTable, rules: SituationRules) -> None:
    template = table.template_by_id()["peddler_safe_path"]
    ok = SituationProposal(attribute=Attribute.WIS, method="tracking", dc_shift=2)
    assert proposal_problems(template, rules, ok) == []
    cases = [
        (SituationProposal(attribute=Attribute.DEX, method="tracking", dc_shift=0), "不在允許清單"),
        (SituationProposal(attribute=Attribute.WIS, method="stealth", dc_shift=0), "不在允許清單"),
        (SituationProposal(attribute=Attribute.STR, method="tracking", dc_shift=0), "不能用屬性"),
    ]
    for proposal, match in cases:
        assert any(match in p for p in proposal_problems(template, rules, proposal))
    strict = rules.model_copy(update={"check": rules.check.model_copy(update={"dc_shift_max": 1})})
    assert any("超過 ±1" in p for p in proposal_problems(template, strict, ok))


def test_proposal_schema_limits() -> None:
    with pytest.raises(ValidationError):
        SituationProposal(attribute=Attribute.WIS, method="tracking", dc_shift=-3)
    with pytest.raises(ValidationError):
        SituationProposal.model_validate(
            {"attribute": "wis", "method": "tracking", "dc_shift": 0, "xp": 999}
        )
    claims = tuple(CareClaim(item="clue", fact=f"thread:t{i}") for i in range(5))
    with pytest.raises(ValidationError):
        SituationProposal(attribute=Attribute.WIS, method="tracking", dc_shift=0, care=claims)


def test_default_proposal(table: SituationTemplateTable, rules: SituationRules) -> None:
    for template in table.templates:
        proposal = default_proposal(template, rules)
        assert proposal.attribute is template.attributes[0] and proposal.dc_shift == 0
        assert proposal_problems(template, rules, proposal) == []
