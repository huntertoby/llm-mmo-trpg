"""把一輪（``RunState``）轉成 API 回應（Phase 3-5a）。技能一律給卡片（含生成技能）。"""

from __future__ import annotations

from collections.abc import Mapping

from trpg.api.attribute_text import attribute_affects
from trpg.api.gear import item_info
from trpg.api.run_schemas import (
    AllocationPreviewOut,
    AttributePerkOut,
    BattlePlanOut,
    FlashCategoryOut,
    FlashOptionOut,
    FlashPreviewOut,
    FlashRecordOut,
    FlashRulesOut,
    GearCandidateOut,
    GearOfferOut,
    HeroGearSlotOut,
    HeroOut,
    LlmStatsOut,
    NodeOut,
    OfferOut,
    OfferTagOut,
    PendingFlashOut,
    RunResponse,
    SaveSummary,
    SkillFlashOut,
)
from trpg.api.runs import RunSession
from trpg.content.equipment import ItemDef
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.slots import SLOT_ZH, SLOTS
from trpg.narrative.skills import CardOwner, KeywordRef, SkillCard, skill_card
from trpg.roguelite import RunSave, RunState
from trpg.roguelite.flashes import (
    flash_categories,
    flash_request,
    owned_skills,
    problem_of,
    state_of,
)
from trpg.roguelite.gear import current_item, equip_notes, target_slot, weapon_swap_prompt
from trpg.roguelite.offers import skill_defs
from trpg.roguelite.progress import hero_effective_attributes, run_loadout
from trpg.roguelite.start import apply_allocation
from trpg.roguelite.state import (
    BattleNode,
    CampfireNode,
    CompleteOfferNode,
    EndedNode,
    GearOfferNode,
    LevelUpNode,
    SkillOffer,
)
from trpg.shared.types import Attribute
from trpg.skillgen.flash_major import transform_slot_plan
from trpg.skillgen.flash_state import (
    FlashRecord,
    SkillFlash,
    dissolve_refund,
    flash_count,
    slot_is_major,
)

__all__ = ["flash_preview", "keyword_refs", "run_response", "save_summary", "start_label"]

_TAG_LABELS = {"deepen": "加深", "bridge": "橋接", "new": "新方向"}


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


def _card(library: ContentLibrary, run: RunState, skill: SkillDef) -> SkillCard:
    """技能卡（帶主角目前的有效屬性與武器）。"""
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
    return skill_card(library, skill, mastery_active=mastery, owner=owner)


def _category_zh(library: ContentLibrary, category: str) -> str:
    if category == "transform":
        return "轉型"
    found = next((c for c in library.flash.categories if c.id == category), None)
    return category if found is None else found.name_zh


def _summary(library: ContentLibrary, record: FlashRecord) -> str:
    variation = record.variation
    template = library.flash.minor_template(variation.template)
    if template is not None:
        return template.summary_zh
    return _category_zh(library, variation.category)


def _record_out(library: ContentLibrary, record: FlashRecord) -> FlashRecordOut:
    variation = record.variation
    return FlashRecordOut(
        nth=record.nth,
        source=variation.source,
        category=variation.category,
        category_zh=_category_zh(library, variation.category),
        template=variation.template,
        summary_zh=_summary(library, record),
        reflashes=record.reflashes,
    )


def _flash_out(library: ContentLibrary, run: RunState, skill_id: str) -> SkillFlashOut:
    """一招學會的技能的閃現狀態（Phase 3W-5）。"""
    rules = library.flash.rules
    state: SkillFlash = state_of(run, skill_id)
    problem = problem_of(library, run, skill_id)
    records = [*state.records, *([state.adjustment] if state.adjustment else [])]
    major = state.record(rules.major_flash)
    return SkillFlashOut(
        skill_id=skill_id,
        base_id=state.base_id,
        flashes=flash_count(rules, state),
        complete=state.complete,
        used=state.used,
        can_flash=problem is None,
        flash_problem_zh=problem,
        next_major=not state.complete and len(state.records) + 1 == rules.major_flash,
        records=tuple(_record_out(library, r) for r in records),
        spent=state.spent,
        dissolve_refund=dissolve_refund(rules, state),
        reflash_transform_hint=(
            not state.complete and major is not None and major.variation.source != "transform"
        ),
    )


def _flash_rules(library: ContentLibrary) -> FlashRulesOut:
    table = library.flash
    open_rule, focused = table.pricing.rule(False), table.pricing.rule(True)
    return FlashRulesOut(
        open_cost=open_rule.cost,
        open_options=open_rule.options,
        focused_cost=focused.cost,
        focused_options=focused.options,
        allow_focus=table.pricing.allow_focus,
        max_flashes=table.rules.max_flashes,
        major_flash=table.rules.major_flash,
        insight_per_win=table.rules.insight_per_win,
    )


def _pending(library: ContentLibrary, run: RunState) -> PendingFlashOut | None:
    pending = run.pending_flash
    if pending is None:
        return None
    offer = pending.offer
    equipped = skill_defs(library, run, run.hero.skills)
    options = []
    for index, option in enumerate(offer.options):
        unequip: tuple[str, ...] = ()
        if pending.skill in run.hero.skills:
            plan = transform_slot_plan(
                equipped, pending.skill, option.skill, library.ruleset.core.skill_slots
            )
            unequip = plan.candidates if plan.needs_unequip else ()
        variation = option.variation
        options.append(
            FlashOptionOut(
                index=index,
                source=variation.source,
                category=variation.category,
                category_zh=_category_zh(library, variation.category),
                template=variation.template,
                summary_zh=option.summary_zh,
                transform=variation.source == "transform",
                card=_card(library, run, option.skill),
                unequip_candidates=unequip,
            )
        )
    return PendingFlashOut(
        skill_id=pending.skill,
        nth=offer.nth,
        slot=offer.slot,
        category=offer.category,
        major=offer.major,
        cost=offer.cost,
        options=tuple(options),
    )


def flash_preview(
    library: ContentLibrary, run: RunState, skill_id: str, slot: int | None
) -> FlashPreviewOut:
    """閃現或重閃之前的預覽：能不能閃、這一次是不是大變化、每個可指定類別的合法變化數量（3W-2c）。"""
    problem = problem_of(library, run, skill_id, slot)
    table = library.flash
    nth = 0
    major = False
    categories: tuple[FlashCategoryOut, ...] = ()
    if skill_id in owned_skills(run):
        request = flash_request(library, run, skill_id, slot=slot)
        nth = request.nth
        major = slot_is_major(table.rules, request.state, nth)
    if problem is None:
        counts = flash_categories(library, run, skill_id, slot)
        categories = tuple(
            FlashCategoryOut(id=c, name_zh=_category_zh(library, c), count=n)
            for c, n in counts.items()
        )
    return FlashPreviewOut(
        skill_id=skill_id,
        slot=slot,
        nth=nth,
        major=major,
        problem_zh=problem,
        open_cost=table.pricing.rule(False).cost,
        focused_cost=table.pricing.rule(True).cost,
        categories=categories,
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
            tier_up=node.tier_up,
            offer=_offer(library, run, node.offer),
        )
    if isinstance(node, CompleteOfferNode):
        return NodeOut(
            kind="complete_offer",
            after_battle=node.after_battle,
            offer=_offer(library, run, node.offer),
        )
    if isinstance(node, CampfireNode):
        return NodeOut(kind="campfire", after_battle=node.after_battle)
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
        skills=tuple(_card(library, run, s) for s in skill_defs(library, run, run.hero.skills)),
        start_keywords=() if run.start is None else keyword_refs(library, run.start.keywords),
        dev_pack=None if run.start is None else run.start.dev_pack,
        insight=run.insight,
        flash_rules=_flash_rules(library),
        flash=tuple(_flash_out(library, run, s) for s in owned_skills(run)),
        bench=tuple(_card(library, run, s) for s in skill_defs(library, run, run.bench)),
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


def llm_stats(run: RunState, alert_permille: int) -> LlmStatsOut | None:
    """LLM 統計（與 ``trpg.cli.run_llm.llm_lines`` 同算法）；沒開 LLM 且沒有題目為 ``None``。"""
    total = len(run.llm_log)
    if not run.llm and total == 0:
        return None
    failed = run.llm_fallbacks
    permille = failed * 1000 // total if total else 0
    named = [r for r in run.llm_log if r.name_source is not None]
    generated = sum(1 for r in named if r.name_source == "llm")
    return LlmStatsOut(
        total=total,
        succeeded=total - failed,
        failed=failed,
        fallback_permille=permille,
        attempts=sum(r.attempts for r in run.llm_log),
        alert_permille=alert_permille,
        alert=permille > alert_permille,
        named=len(named),
        name_generated=generated,
        name_fallback=len(named) - generated,
    )


def run_response(session: RunSession, *, with_notice: bool = False) -> RunResponse:
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
        llm=run.llm,
        llm_notice=session.llm_notice if with_notice else None,
        llm_stats=llm_stats(run, session.alert_permille),
        pending_flash=_pending(library, run),
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
