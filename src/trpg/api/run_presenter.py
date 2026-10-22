"""把一輪（``RunState``）轉成 API 回應（Phase 3-5a）。技能一律給卡片（含生成技能）。"""

from __future__ import annotations

from trpg.api.run_schemas import (
    BattlePlanOut,
    HeroOut,
    NodeOut,
    OfferOut,
    OfferTagOut,
    RunResponse,
    SaveSummary,
    SkillGrowthOut,
)
from trpg.api.runs import RunSession
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.narrative.skill_levels import skill_level_info
from trpg.narrative.skills import KeywordRef, SkillCard, skill_card
from trpg.roguelite import RunSave, RunState
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    EndedNode,
    LevelUpNode,
    SkillOffer,
)

__all__ = ["keyword_refs", "run_response", "save_summary", "start_label"]

_TAG_LABELS = {"deepen": "加深", "bridge": "橋接", "new": "新方向"}


def keyword_refs(library: ContentLibrary, ids: tuple[str, ...]) -> tuple[KeywordRef, ...]:
    defs = library.keywords.by_id()
    return tuple(
        KeywordRef(id=k, name_zh=defs[k].name_zh, description_zh=defs[k].description_zh)
        for k in ids
    )


def start_label(library: ContentLibrary, run: RunState) -> str:
    """一輪的開局說明（存檔列表用；不含任何流派名稱）：「單手劍・點燃＋倒地」。以 build 開局時用
    build 的名稱（回歸範本，開發用）。"""
    if run.start is None:
        build = next((b for b in library.builds.builds if b.id == run.build_id), None)
        return build.name_zh if build is not None else (run.build_id or "")
    weapon = library.weapons.get(run.start.weapon)
    names = "＋".join(r.name_zh for r in keyword_refs(library, run.start.keywords))
    return f"{weapon.name_zh if weapon is not None else run.start.weapon}・{names}"


def _card(
    library: ContentLibrary, run: RunState, skill: SkillDef, *, owned: bool = False
) -> SkillCard:
    """技能卡；``owned``（主角持有的技能）才帶技能等級的顯示資料（Phase 3-26a）。"""
    attrs = run.hero.attributes
    mastery = (
        None
        if skill.mastery is None
        else all(attrs[skill.scaling_attr] >= v for v in attrs.values())
    )
    card = skill_card(library, skill, mastery_active=mastery)
    if not owned:
        return card
    return card.model_copy(
        update={"growth": skill_level_info(library, skill, run.skill_levels.get(skill.id, 1))}
    )


def _offer(library: ContentLibrary, run: RunState, offer: SkillOffer | None) -> OfferOut | None:
    if offer is None:
        return None
    return OfferOut(
        reason=offer.reason,
        tier=offer.tier,
        top_attribute=offer.top_attribute,
        candidates=tuple(_card(library, run, s) for s in offer.candidates),
        off_route=offer.off_route,
        tags=tuple(
            OfferTagOut(
                kind=t.kind,
                label_zh=_TAG_LABELS[t.kind],
                keywords=keyword_refs(library, t.keywords),
                fallback=t.fallback,
                source=t.source,
            )
            for t in offer.tags
        ),
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
    growth = library.ruleset.skill_growth
    weapon = library.weapons.get(run.hero.weapon)
    return HeroOut(
        build_id=run.build_id or "",
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
        skills=tuple(
            _card(library, run, s, owned=True) for s in skill_defs(library, run, run.hero.skills)
        ),
        start_keywords=() if run.start is None else keyword_refs(library, run.start.keywords),
        dev_pack=None if run.start is None else run.start.dev_pack,
        skill_points=run.skill_points,
        skill_growth=SkillGrowthOut(
            max_level=growth.max_level,
            upgrade_cost=growth.upgrade_cost,
            points_per_level=growth.points_per_level,
            trait_level=growth.trait_level,
            evolve_level=growth.evolve_level,
        ),
        bench=tuple(
            _card(library, run, s, owned=True) for s in skill_defs(library, run, run.bench)
        ),
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
    return SaveSummary(
        run_id=save.run_id,
        build_id=run.build_id or "",
        build_name_zh=start_label(library, run),
        seed=run.seed,
        level=run.level,
        battles_done=run.battles_done,
        battles_total=len(run.plan),
        node=run.node.kind,
        in_battle=save.battle is not None,
        victory=run.node.victory if isinstance(run.node, EndedNode) else None,
    )
