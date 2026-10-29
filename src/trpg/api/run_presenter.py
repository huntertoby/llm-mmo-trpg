"""把一輪（``RunState``）轉成 API 回應（Phase 3-5a）。技能一律給卡片（含生成技能）。"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.api.attribute_text import attribute_affects
from trpg.api.gear import item_info
from trpg.api.run_schemas import (
    AllocationPreviewOut,
    AttributePerkOut,
    BattlePlanOut,
    EvolutionChoiceOut,
    EvolutionOptionOut,
    GearCandidateOut,
    GearOfferOut,
    HeroGearSlotOut,
    HeroOut,
    NodeOut,
    OfferOut,
    OfferTagOut,
    RunResponse,
    SaveSummary,
    SkillGrowthOut,
)
from trpg.api.runs import RunSession
from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.slots import SLOT_ZH, SLOTS
from trpg.narrative.skill_levels import skill_level_info
from trpg.narrative.skills import CardOwner, KeywordRef, SkillCard, skill_card
from trpg.roguelite import RunSave, RunState
from trpg.roguelite.gear import current_item, equip_notes, target_slot, weapon_swap_prompt
from trpg.roguelite.growth import (
    crosses_evolution,
    evolution_choices,
    level_of,
    raise_problem,
    uses_of,
)
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.progress import hero_effective_attributes, run_loadout
from trpg.roguelite.start import apply_allocation
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    EndedNode,
    GearOfferNode,
    LevelUpNode,
    SkillOffer,
)
from trpg.shared.types import Attribute

__all__ = ["keyword_refs", "run_response", "save_summary", "start_label"]

_TAG_LABELS = {"deepen": "加深", "bridge": "橋接", "count": "數量", "new": "新方向"}


def keyword_refs(library: ContentLibrary, ids: tuple[str, ...]) -> tuple[KeywordRef, ...]:
    defs = library.keywords.by_id()
    return tuple(
        KeywordRef(id=k, name_zh=defs[k].name_zh, description_zh=defs[k].description_zh)
        for k in ids
    )


def start_label(library: ContentLibrary, run: RunState) -> str:
    """一輪的開局說明（存檔列表用；不含任何流派名稱）：「單手劍・點燃＋倒地」。以 build 開局
    （回歸範本，開發用）的存檔不顯示 build 名稱（那是流派名），只寫武器。"""
    if run.start is None:
        weapon = library.weapons.get(run.hero.weapon)
        return f"回歸測試開局・{weapon.name_zh if weapon is not None else run.hero.weapon}"
    weapon = library.weapons.get(run.start.weapon)
    names = "＋".join(r.name_zh for r in keyword_refs(library, run.start.keywords))
    return f"{weapon.name_zh if weapon is not None else run.start.weapon}・{names}"


def _card(
    library: ContentLibrary, run: RunState, skill: SkillDef, *, owned: bool = False
) -> SkillCard:
    """技能卡；``owned``（主角持有的技能）才帶技能等級的顯示資料（Phase 3-26a）。"""
    attrs = run.hero.attributes
    weapon = library.weapons.get(run.hero.weapon)
    mastery = (  # 專精看縮放屬性是不是自己最高；武器技看手上武器（3H-6）
        None
        if skill.mastery is None
        else skill.mastery_value(attrs.__getitem__, weapon) >= max(attrs.values())
    )
    # 傷害算法的「目前」加成：主角的有效屬性（基礎＋裝備）與武器（3-41c）；戰鬥之間沒有戰鬥狀態，
    # 召喚物資訊維持 1 級基準值（標明「基準值」）
    effective = hero_effective_attributes(library, run)
    owner = CardOwner(weapon=weapon, attr_get=effective.__getitem__)
    card = skill_card(library, skill, mastery_active=mastery, owner=owner)
    if not owned:
        return card
    level = level_of(run, skill.id)
    record = run.evolutions.get(skill.id)
    blocked = None
    if skill.id in run.hero.skills and level < library.ruleset.skill_growth.max_level:
        blocked = raise_problem(library, run, skill, skill.id, level + 1)
    info = skill_level_info(
        library,
        skill,
        level,
        uses=uses_of(run, skill.id),
        evolved_from_zh=None if record is None else record.base_name_zh,
        blocked_text=blocked,
    )
    return card.model_copy(update={"growth": info})


def _evolutions(library: ContentLibrary, run: RunState) -> tuple[EvolutionChoiceOut, ...]:
    """升到分歧進化那一級時可選的兩支（Phase 3-26b）：已達門檻、還沒進化的裝備中主動技能。"""
    growth = library.ruleset.skill_growth
    out = []
    for skill in skill_defs(library, run, run.hero.skills):
        if skill.kind != "active" or not crosses_evolution(
            library, run, skill.id, growth.evolve_level
        ):
            continue
        if raise_problem(library, run, skill, skill.id, growth.evolve_level) is not None:
            continue
        options = tuple(
            EvolutionOptionOut(
                index=i,
                branch=e.branch,
                label_zh=_TAG_LABELS[e.branch],
                template=e.template,
                keyword=None if e.keyword is None else keyword_refs(library, (e.keyword,))[0],
                summary_zh=e.summary_zh,
                fallback=e.fallback,
                card=_card(library, run, e.skill),
            )
            for i, e in enumerate(evolution_choices(library, run, skill.id))
        )
        out.append(EvolutionChoiceOut(skill_id=skill.id, name_zh=skill.name_zh, options=options))
    return tuple(out)


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


def _candidate(library: ContentLibrary, run: RunState, item: ItemDef) -> GearCandidateOut:
    """戰後候選或背包裡的一件裝備：放進的欄位、該欄位目前的裝備與換上的連帶效果。"""
    slot = target_slot(library, run, item)
    current = current_item(library, run, slot)
    return GearCandidateOut(
        item=item_info(library, item),
        slot=slot,
        slot_zh=SLOT_ZH[slot],
        current=None if current is None else item_info(library, current),
        notes_zh=tuple(equip_notes(library, run, item, slot)),
        weapon_swap_zh=weapon_swap_prompt(
            library, run, item, slot, hero_effective_attributes(library, run)
        ),
    )


def _gear_offer(library: ContentLibrary, run: RunState, node: GearOfferNode) -> GearOfferOut:
    return GearOfferOut(
        after_battle=node.after_battle,
        candidates=tuple(_candidate(library, run, i) for i in node.candidates),
    )


def _node(library: ContentLibrary, run: RunState) -> NodeOut:
    node = run.node
    if isinstance(node, BattleNode):
        return NodeOut(kind="battle", battle_index=node.index, boss=run.plan_of(node.index).boss)
    if isinstance(node, GearOfferNode):
        return NodeOut(kind="gear_offer", gear=_gear_offer(library, run, node))
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


def _race_name(library: ContentLibrary, race: str | None) -> str:
    if race is None:
        return ""
    try:
        return library.ruleset.race_def(race).name_zh
    except KeyError:
        return race


def _origin_name(library: ContentLibrary, origin: str | None) -> str:
    if origin is None or library.origins is None:
        return ""
    return next((o.name_zh for o in library.origins.origins if o.id == origin), origin)


def _hero(library: ContentLibrary, run: RunState) -> HeroOut:
    thresholds = library.roguelite.level_thresholds
    growth = library.ruleset.skill_growth
    weapon = library.weapons.get(run.hero.weapon)
    off_item = run_loadout(library, run).item_in("off_hand")
    offhand = None if off_item is None else off_item.item.offhand_def
    effective = hero_effective_attributes(library, run)
    equipped = skill_defs(library, run, run.hero.skills)
    core = library.ruleset.core
    return HeroOut(
        build_id=run.build_id or "",
        race_id=run.hero.race,
        race_name_zh=_race_name(library, run.hero.race),
        origin_id=run.origin,
        origin_name_zh=_origin_name(library, run.origin),
        name_zh=run.hero.name_zh,
        level=run.level,
        xp=run.xp,
        xp_next=thresholds[run.level - 1] if run.level - 1 < len(thresholds) else None,
        attributes=dict(run.hero.attributes),
        effective_attributes=effective,
        attribute_points=run.attribute_points,
        attribute_spent=dict(run.attribute_spent),
        attribute_affects=attribute_affects(equipped, weapon),
        hp=run.hp,
        # 測試模式戰後回滿到含裝備的上限，可能高於一輪本身算的上限：顯示時不讓 HP／法力超過上限
        max_hp=max(run.max_hp_in(library.ruleset.core), run.hp if run.test_mode else 0),
        hp_per_con_point=library.ruleset.core.hp_per_con_point,
        hp_con_base=library.ruleset.core.hp_con_base,
        attribute_perks=tuple(
            AttributePerkOut(
                attr=p.attr,
                tier=p.tier,
                per_tier_zh=p.per_tier_zh,
                now_zh=p.now_zh,
                next_at=p.next_at,
            )
            for p in library.ruleset.core.attribute_perks.lines(effective)
        ),
        mana=run.mana,
        max_mana=max(run.max_mana_in(core), run.mana if run.test_mode else 0),
        stamina=run.stamina_in(core),
        max_stamina=max(run.max_stamina_in(core), run.stamina_in(core) if run.test_mode else 0),
        source=run.source,
        source_max=library.ruleset.core.source_max,
        weapon=run.hero.weapon,
        weapon_name_zh=weapon.name_zh if weapon is not None else "",
        weapon_class=weapon.weapon_class if weapon is not None else "",
        weapon_traits_zh=(
            (
                *weapon.trait_lines_zh(),
                *weapon.rule_lines_zh(library.ruleset.core, effective.__getitem__),
            )
            if weapon is not None
            else ()
        ),
        offhand_name_zh="" if offhand is None else offhand.name_zh,
        offhand_traits_zh=(
            ()
            if offhand is None
            else offhand.trait_lines_zh(library.ruleset.core, effective.__getitem__)
        ),
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
            evolve_uses=growth.evolve_uses,
        ),
        bench=tuple(
            _card(library, run, s, owned=True) for s in skill_defs(library, run, run.bench)
        ),
        evolutions=_evolutions(library, run),
        equipment=tuple(
            HeroGearSlotOut(
                slot=slot,
                slot_zh=SLOT_ZH[slot],
                item=None
                if (held := current_item(library, run, slot)) is None
                else item_info(library, held),
            )
            for slot in SLOTS
        ),
        backpack=tuple(_candidate(library, run, i) for i in run.backpack),
    )


def resource_rule_text(library: ContentLibrary, *, test_mode: bool) -> str:
    """戰鬥之間的資源規則（Phase 3-41b）：營火的場次取自 ``roguelite.yaml``，不寫死在前端。"""
    if test_mode:
        return "測試模式：每場戰鬥結束後 HP、法力、耐力自動回滿。"
    after = "、".join(f"第 {n} 場" for n in library.roguelite.campfire_after)
    names = {"mana": "法力", "stamina": "耐力"}
    refill = [names[k] for k in ("mana", "stamina") if k in library.roguelite.refill_after_battle]
    kept = "、".join(["HP", *(v for k, v in names.items() if v not in refill)])
    head = f"每場打贏後{'、'.join(refill)}回滿；" if refill else ""
    regen = library.ruleset.core.resources.stamina_regen
    regen_text = f"戰鬥中主角的耐力每回合開始回復 {regen} 點；" if regen else ""
    return f"{head}{regen_text}{kept}不會在戰鬥之間回復，只有營火會回滿（{after}之後）。"


def allocation_preview(
    library: ContentLibrary, run: RunState, allocation: Mapping[Attribute, int]
) -> AllocationPreviewOut:
    """配點後的最大 HP、法力、耐力（3H-5）：把 ``allocation`` 加到主角目前的屬性上，用
    ``RunState.max_*_in``（一輪面板、升級同步上限的同一組函式）算；負數的配點視為 0。"""
    core = library.ruleset.core
    added = {a: max(0, n) for a, n in allocation.items()}
    after = run.model_copy(update={"hero": apply_allocation(run.hero, added)})
    now = (run.max_hp_in(core), run.max_mana_in(core), run.max_stamina_in(core))
    new = (after.max_hp_in(core), after.max_mana_in(core), after.max_stamina_in(core))
    names = ("最大 HP", "法力", "耐力")
    parts = [
        f"{name} {'＋' if b > a else '−'}{abs(b - a)}"
        for name, a, b in zip(names, now, new, strict=True)
        if a != b
    ]
    return AllocationPreviewOut(hp=new[0], mana=new[1], stamina=new[2], summary_zh="、".join(parts))


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
        test_mode=run.test_mode,
        test_equipment=dict(run.test_equipment),
        resource_rule_zh=resource_rule_text(library, test_mode=run.test_mode),
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
        test_mode=run.test_mode,
    )
