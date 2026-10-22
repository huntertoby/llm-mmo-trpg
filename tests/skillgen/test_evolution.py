"""Phase 3-26b：分歧進化的兩支推導（加深、橋接）、同階預算驗證、模板資料、確定性。"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest
from pydantic import ValidationError

from tests.engine.helpers import library
from trpg.content.keyword_derive import derive_keywords
from trpg.content.skill_evolution import EvolutionTable, EvolutionTemplate
from trpg.content.skills import SkillDef, rarity_rank
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.evolution import (
    Evolution,
    EvolutionRequest,
    _bridge_templates,
    evolution_options,
)
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

FIRE_BOLT = "skill_fire_bolt"
"""火焰箭（1 階普通：1d8 火焰 ＋ 燃燒 1 回合）：製造點燃。"""
BERSERK = "skill_berserker_rage"
"""狂戰士之怒（武器技、單體）：沒有專屬關鍵字。"""

SINGLE_TARGET = SkillUsage(uses=4, targets=4, distance=16)
"""單體、遠距離的用法（平均 1 個目標、4 格）。"""


def _usage(**fields: object) -> SkillUsage:
    return SkillUsage.model_validate({"uses": 4, "targets": 4, "distance": 8, **fields})


def _options(
    skill_id: str, usage: SkillUsage, held: dict[str, int] | None = None, seed: int = 7
) -> tuple[Evolution, ...]:
    lib = library()
    request = EvolutionRequest(lib.skills[skill_id], usage, held or {}, seed)
    return evolution_options(lib, request)


def _exclusive(skill: SkillDef) -> tuple[str, ...]:
    return derive_keywords(skill, library().keywords, exclusive_only=True).all()


def test_deepen_reinforces_the_skills_own_keyword_and_bridge_follows_the_partner() -> None:
    # 打到的目標常在燃燒、前後常搭配製造倒地的技能
    usage = _usage(target_keywords={"ignite": 3}, partner_makes={"prone": 3})
    deepen, bridge = _options(FIRE_BOLT, usage)
    assert (deepen.branch, bridge.branch) == ("deepen", "bridge")
    assert "ignite" in _exclusive(deepen.skill)  # 加深保留（並強化）自己的點燃
    assert deepen.template in {"intensify", "reshape", "extend", "delayed_burst"}
    # 橋接：搭配的技能「製造」倒地 → 先試「利用」倒地（目標倒地時加碼）
    assert bridge.keyword == "prone" and "prone" in _exclusive(bridge.skill)
    assert bridge.template == "bridge_exploit"
    assert any(
        e.condition is not None and e.condition.type == "target_has_status"
        for e in bridge.skill.effects
    )
    assert not deepen.fallback and not bridge.fallback


def test_bridge_prefers_partners_then_targets_then_held_keywords() -> None:
    by_target = _options(FIRE_BOLT, _usage(target_keywords={"marked": 2}), {"collision": 5})
    assert by_target[1].keyword == "marked"
    by_held = _options(FIRE_BOLT, _usage(), {"collision": 5})
    assert by_held[1].keyword == "collision"
    by_partner = _options(
        FIRE_BOLT, _usage(target_keywords={"marked": 9}, partner_uses={"collision": 1})
    )
    assert by_partner[1].keyword == "collision"
    # 搭配的技能「利用」撞擊 → 先試「製造」撞擊（推擊）；搭配的技能「製造」→ 先試「利用」
    bridge = library().evolution.branch("bridge")
    uses_first = _bridge_templates(bridge, "collision", _usage(partner_makes={"collision": 1}))
    makes_first = _bridge_templates(bridge, "collision", _usage(partner_uses={"collision": 1}))
    assert [t.op for t in uses_first] == ["graft_uses", "graft_makes"]
    assert [t.op for t in makes_first] == ["graft_makes", "graft_uses"]


def test_without_any_bridge_keyword_the_second_option_falls_back_to_deepen() -> None:
    options = _options(FIRE_BOLT, _usage())
    assert [o.branch for o in options] == ["deepen", "deepen"]
    assert options[1].fallback and options[0].template != options[1].template


def test_single_target_usage_prefers_reshaping() -> None:
    deepen = _options(BERSERK, SINGLE_TARGET, {"ignite": 1})[0]
    assert deepen.template == "reshape"
    assert deepen.skill.shape.type != library().skills[BERSERK].shape.type


@pytest.mark.slow
def test_every_option_passes_the_validator_within_the_same_tier_budget() -> None:
    lib = library()
    usages = [
        _usage(target_keywords={"ignite": 2}, partner_makes={"prone": 2}, kills=1),
        SINGLE_TARGET,
        _usage(targets=12, partner_uses={"marked": 1}),
    ]
    checked = 0
    for skill in sorted(lib.skills.values(), key=lambda s: s.id):
        if skill.kind != "active" or skill.tier != 1:
            continue
        for usage in usages:
            for option in evolution_options(lib, EvolutionRequest(skill, usage, {"wet": 1}, 3)):
                evolved = option.skill
                assert validate_skill(evolved, lib) == [], evolved.id
                report = skill_budget(evolved, lib)
                assert Fraction(7, 10) <= report.ratio <= 1, evolved.id
                assert evolved.tier == skill.tier and evolved.kind == skill.kind
                assert evolved.ap_cost == skill.ap_cost
                # 稀有度不加強度：只會因為新內容需要而提高，不會變成傳說
                assert rarity_rank(evolved.rarity) >= rarity_rank(skill.rarity)
                assert evolved.rarity != "legendary" or skill.rarity == "legendary"
                assert evolved.id != skill.id and evolved.provenance.parents == (skill.id,)
                assert evolved.name_zh.endswith(f"・{skill.name_zh}")
                checked += 1
    assert checked > 100


def test_templates_that_do_not_fit_never_appear() -> None:
    lib = library()
    # 延遲爆炸只能用在法術技：武器技不會出現延爆
    for skill in lib.skills.values():
        if skill.kind == "active" and skill.category == "weapon" and skill.tier == 1:
            for option in evolution_options(lib, EvolutionRequest(skill, SINGLE_TARGET, {}, 1)):
                assert option.template != "delayed_burst"
    # 沒有任何模板合格時沒有選項（例：只有 1 個不合格的模板）
    bad = EvolutionTable(
        templates=(
            EvolutionTemplate(
                id="kill_chain",
                branch="deepen",
                op="on_kill",
                prefix_zh="收割",
                summary_zh="x",
                on_kill=next(t for t in lib.evolution.templates if t.op == "on_kill").on_kill,
            ),
        )
    )
    no_damage = lib.skills["skill_war_hymn"]
    assert (
        evolution_options(
            dataclasses.replace(lib, evolution=bad), EvolutionRequest(no_damage, _usage(), {}, 1)
        )
        == ()
    )


def test_same_request_gives_the_same_options_and_names_are_composed() -> None:
    usage = _usage(target_keywords={"ignite": 1}, partner_makes={"prone": 1})
    a, b = _options(FIRE_BOLT, usage), _options(FIRE_BOLT, usage)
    assert a == b
    assert [o.skill.name_zh for o in a][1] == "崩倒・火焰箭"
    assert a[1].skill.id == "skill_fire_bolt_evo_bridge_exploit_prone"


def test_evolution_content_schema_rejects_bad_templates() -> None:
    with pytest.raises(ValidationError, match="只能用在"):
        EvolutionTemplate(id="x", branch="deepen", op="graft_uses", summary_zh="x")
    with pytest.raises(ValidationError, match="shapes"):
        EvolutionTemplate(id="x", branch="deepen", op="reshape", prefix_zh="x", summary_zh="x")
    with pytest.raises(ValidationError, match="重複"):
        template = EvolutionTemplate(id="x", branch="deepen", op="intensify", summary_zh="x")
        EvolutionTable(templates=(template, template))
    lib = library()
    assert {t.branch for t in lib.evolution.templates} == {"deepen", "bridge"}
    assert set(lib.evolution.grafts) <= set(lib.keywords.ids())
