"""把一輪（``RunState``）轉成 API 回應（Phase 3-5a）。技能一律給卡片（含生成技能）。"""

from __future__ import annotations

from trpg.api.run_schemas import (
    BattlePlanOut,
    HeroOut,
    NodeOut,
    OfferOut,
    RunResponse,
    SaveSummary,
)
from trpg.api.runs import RunSession
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.narrative.skills import SkillCard, skill_card
from trpg.roguelite import RunSave, RunState
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    EndedNode,
    LevelUpNode,
    SkillOffer,
)

__all__ = ["run_response", "save_summary"]


def _card(library: ContentLibrary, run: RunState, skill: SkillDef) -> SkillCard:
    attrs = run.hero.attributes
    mastery = (
        None
        if skill.mastery is None
        else all(attrs[skill.scaling_attr] >= v for v in attrs.values())
    )
    return skill_card(library, skill, mastery_active=mastery)


def _offer(library: ContentLibrary, run: RunState, offer: SkillOffer | None) -> OfferOut | None:
    if offer is None:
        return None
    return OfferOut(
        reason=offer.reason,
        tier=offer.tier,
        top_attribute=offer.top_attribute,
        candidates=tuple(_card(library, run, s) for s in offer.candidates),
        off_route=offer.off_route,
    )


def _node(library: ContentLibrary, run: RunState) -> NodeOut:
    node = run.node
    if isinstance(node, BattleNode):
        return NodeOut(kind="battle", battle_index=node.index, boss=run.plan_of(node.index).boss)
    if isinstance(node, LevelUpNode):
        return NodeOut(
            kind="level_up",
            level=node.level,
            points=node.points,
            offer=_offer(library, run, node.offer),
        )
    if isinstance(node, CampfireNode):
        return NodeOut(
            kind="campfire",
            after_battle=node.after_battle,
            rerolls_left=node.rerolls_left,
            offer=_offer(library, run, node.offer),
        )
    assert isinstance(node, EndedNode)
    return NodeOut(kind="ended", victory=node.victory)


def _hero(library: ContentLibrary, run: RunState) -> HeroOut:
    thresholds = library.roguelite.level_thresholds
    weapon = library.weapons.get(run.hero.weapon)
    return HeroOut(
        build_id=run.build_id,
        name_zh=run.hero.name_zh,
        level=run.level,
        xp=run.xp,
        xp_next=thresholds[run.level - 1] if run.level - 1 < len(thresholds) else None,
        attributes=dict(run.hero.attributes),
        hp=run.hp,
        max_hp=run.max_hp_in(library.ruleset.core),
        hp_per_con_point=library.ruleset.core.hp_per_con_point,
        hp_con_base=library.ruleset.core.hp_con_base,
        mana=run.mana,
        max_mana=run.max_mana,
        source=run.source,
        source_max=library.ruleset.core.source_max,
        weapon=run.hero.weapon,
        weapon_name_zh=weapon.name_zh if weapon is not None else "",
        weapon_class=weapon.weapon_class if weapon is not None else "",
        weapon_traits_zh=weapon.trait_lines_zh() if weapon is not None else (),
        skills=tuple(_card(library, run, s) for s in skill_defs(library, run, run.hero.skills)),
    )


def run_response(session: RunSession) -> RunResponse:
    library, run = session.library, session.run
    plan = tuple(
        BattlePlanOut(
            index=p.index,
            map_id=p.map_id,
            map_name_zh=library.map(p.map_id).name_zh,
            boss=p.boss,
            enemies=tuple(library.unit(t).name_zh for t in p.enemies),
            done=p.index <= run.battles_done,
            objective=library.map(p.map_id).objective_for(p.objective),
        )
        for p in run.plan
    )
    return RunResponse(
        run_id=session.run_id,
        seed=run.seed,
        node=_node(library, run),
        hero=_hero(library, run),
        battles_done=run.battles_done,
        plan=plan,
        history=run.history,
        battle_id=None if session.battle is None else session.battle.battle_id,
    )


def save_summary(library: ContentLibrary, save: RunSave) -> SaveSummary:
    run = save.run
    build_name = next((b.name_zh for b in library.builds.builds if b.id == run.build_id), None)
    return SaveSummary(
        run_id=save.run_id,
        build_id=run.build_id,
        build_name_zh=build_name or run.build_id,
        seed=run.seed,
        level=run.level,
        battles_done=run.battles_done,
        battles_total=len(run.plan),
        node=run.node.kind,
        in_battle=save.battle is not None,
        victory=run.node.victory if isinstance(run.node, EndedNode) else None,
    )
