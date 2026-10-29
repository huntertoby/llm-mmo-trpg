"""風元素補強（Phase 3-54a，06 6.33，#56）在工坊、預算、組合器、LLM 提議與卡片的接法。

引擎行為見 ``tests/engine/test_wind_54a.py``；這裡檢查「卡片＝實戰」與各入口都認得吹送。
"""

from __future__ import annotations

from typing import Any

from tests.engine.helpers import library, make_skill
from tests.engine.skill_helpers import SID, battle, cast, hit_with, of
from trpg.content.skills import SkillDef
from trpg.engine.events import Collided, SurfaceBlown
from trpg.narrative.skills import skill_card
from trpg.shared.types import Pos, UnitId
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_models import StepOptions
from trpg.skillgen.options import draft_options
from trpg.skillgen.proposal import build_proposal_models, proposal_from_skill
from trpg.skillgen.random_composer import compose_random_skill

LIB = library()


def _draft(skeleton: str, effects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "skeleton": skeleton,
        "kind": "active",
        "ap_cost": 2,
        "category": "spell",
        "weapon_req": "focus",
        "scaling_attr": "int",
        "tier": 1,
        "shape": {"type": "cone", "size": 3},
        "effects": effects,
        "cost": {"mana": 4, "cooldown": 2},
    }


def _step(draft: dict[str, Any], step_id: str) -> StepOptions:
    return next(s for s in draft_options(draft, LIB).steps if s.id == step_id)


def _blow_choice(draft: dict[str, Any]) -> Any:
    effects = next(f for f in _step(draft, "effects").fields if f.field == "effects")
    return next(c for c in effects.choices if c.value == "blow_surface")


WIND = {"type": "damage", "dice": "2d6", "element": "wind"}
BLOW = {"type": "blow_surface", "distance": 2}


def test_workshop_offers_blow_with_tiles_only_and_a_two_to_three_distance() -> None:
    for skeleton, effects in (("control", []), ("area", [WIND])):
        draft = {k: v for k, v in _draft(skeleton, effects).items() if k != "cost"}
        choice = _blow_choice(draft)
        params = {p.field: p for p in choice.params}
        assert [c.value for c in params["affects"].choices] == ["tiles"]
        assert (params["distance"].min, params["distance"].max) == (2, 3)
        assert "yaml" not in choice.description_zh  # 玩家模式顯示改寫後的說明


def test_validator_accepts_blow_on_tiles_and_rejects_units_and_common() -> None:
    ok = check_draft({**_draft("area", [WIND, BLOW]), "rarity": "rare"}, LIB)
    assert ok.legal, ok.problems
    units = _draft("area", [WIND, {**BLOW, "affects": "enemies"}])
    assert not check_draft({**units, "rarity": "rare"}, LIB).legal
    # 3W-9：稀有度只是標記，普通也合法（吹送是 1 階就有的內容）
    assert check_draft({**_draft("area", [WIND, BLOW]), "rarity": "common"}, LIB).legal


def test_budget_counts_blow_per_distance_and_wind_push_collisions() -> None:
    blow = make_skill(SID, {"type": "cone", "size": 3}, [WIND, BLOW])
    report = skill_budget(blow, LIB)
    (row,) = [e for e in report.effects if e.type == "blow_surface"]
    assert row.base == 2
    push = {"type": "push", "distance": 1, "collision_dice": "2d6"}
    wind_push = skill_budget(make_skill(SID, {"type": "single", "range": 1}, [WIND, push]), LIB)
    fire = {**WIND, "element": "fire"}
    fire_push = skill_budget(make_skill(SID, {"type": "single", "range": 1}, [fire, push]), LIB)
    (w,) = [e for e in wind_push.effects if e.type == "push"]
    (f,) = [e for e in fire_push.effects if e.type == "push"]
    assert w.base - f.base == 1  # 2 顆撞擊骰 × 1 點 × 0.5
    assert "風壓撞擊" in w.note


def test_composer_adds_blow_only_through_its_own_stream() -> None:
    skills = [compose_random_skill(seed, skeleton="area", library=LIB) for seed in range(300)]
    found = [s for s in skills if any(e.type == "blow_surface" for e in s.effects)]
    assert found
    for skill in found:
        assert skill.rarity != "common"
        assert all(e.distance in (2, 3) for e in skill.effects if e.type == "blow_surface")
    again = compose_random_skill(0, skeleton="control", library=LIB)
    assert not any(e.type == "blow_surface" for e in again.effects)  # 控場不當核心抽


def test_llm_proposal_schema_knows_blow() -> None:
    models = build_proposal_models(LIB)
    assert "blow_surface" in models.primitive_ids
    assert "blow_surface" in str(models.json_schema())
    skill = make_skill(SID, {"type": "cone", "size": 3}, [WIND, BLOW])
    proposal = proposal_from_skill(skill, LIB)
    assert any(e.get("type") == "blow_surface" for e in proposal["effects"])


def _card(skill: SkillDef) -> str:
    return "\n".join(skill_card(LIB, skill).effects)


def test_card_matches_battle_for_blow_spread_and_wind_push() -> None:
    blow = make_skill(SID, {"type": "line", "size": 1}, [BLOW])
    text = _card(blow)
    assert "往風向吹走 2 格" in text
    state = battle(blow, surfaces=((4, 3, "oil"),), foes=[(0, 0)])
    (blown,) = of(cast(state, direction="east"), SurfaceBlown)
    assert blown.to_pos == Pos(x=6, y=3)

    spread = make_skill(SID, {"type": "line", "size": 1}, [{**WIND, "affects": "tiles"}])
    assert "往風向擴大 1 格" in _card(spread)

    push = make_skill(SID, {"type": "single", "range": 1}, [WIND, {"type": "push", "distance": 1}])
    assert "風壓：撞擊傷害 +50%" in _card(push)
    state = battle(push, foes=[(4, 3)], allies=[])
    tile = state.tile(5, 3)
    from dataclasses import replace  # noqa: PLC0415

    state.set_tile(5, 3, replace(tile, terrain="wall"))
    (collided,) = of(cast(hit_with(state), target_id=UnitId("unit_0002")), Collided)
    assert collided.damage_permille == 1500
