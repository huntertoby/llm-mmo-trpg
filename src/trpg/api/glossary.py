"""名詞對照表（Phase 3-4a 6.2）：地形、表面、物件、狀態、層數、反應、元素、屬性的 ID → 中文名。

由內容庫產生，前端不再手寫中文名；只保留色塊等純顯示用的對照。``tags`` 是前端判斷外觀需要的
簡短旗標：地形為 ``blocked``／``deadly``／``blocks_sight``，表面為 ``flammable``／``beneficial``
等，物件為 ``objects.yaml`` 的標籤，層數為 ``self``／``target``（累積在誰身上）。
"""

from __future__ import annotations

from trpg.api.schemas import (
    GameRulesOut,
    Glossary,
    GlossaryEntry,
    SkillSlotsOut,
    StatusLook,
    WeaponLookEntry,
    WeaponRangeEntry,
)
from trpg.api.world_pregen import WAIT_SECONDS
from trpg.content.battle import StatusDef
from trpg.content.library import ContentLibrary
from trpg.narrative.action_info import action_texts, objective_texts
from trpg.narrative.status_info import stack_rules, status_rules
from trpg.narrative.tile_info import object_rules, surface_rules, terrain_rules
from trpg.roguelite.flashes import max_carry
from trpg.shared.types import Attribute
from trpg.world.growth import OPENING_END_LEVEL
from trpg.world.league import league_rules

__all__ = ["build_glossary"]


def _entry(
    id_: str,
    name_zh: str,
    description_zh: str | None = None,
    tags: tuple[str, ...] = (),
    rules_zh: tuple[str, ...] = (),
    *,
    status_look: StatusLook | None = None,
) -> GlossaryEntry:
    return GlossaryEntry(
        id=id_,
        name_zh=name_zh,
        description_zh=description_zh,
        tags=tags,
        rules_zh=rules_zh,
        status_look=status_look,
    )


def _status_look(s: StatusDef) -> StatusLook:
    dot = s.on_turn_start_damage
    return StatusLook(
        polarity=s.polarity,
        control_group=s.control_group,
        dot_element=None if dot is None else dot.element.value,
        skip_turn=s.skip_turn,
        removed_by_element=tuple(sorted(e.value for e in s.removed_by_element)),
        absorbs_damage=s.absorbs_damage,
        prevents_move=s.prevents_move,
    )


def _terrain_tags(walkable: bool, deadly: bool, blocks_sight: bool) -> tuple[str, ...]:
    tags = [
        tag
        for tag, on in (
            ("blocked", not walkable),
            ("deadly", deadly),
            ("blocks_sight", blocks_sight),
        )
        if on
    ]
    return tuple(tags)


def build_glossary(library: ContentLibrary) -> Glossary:
    rules = library.ruleset
    return Glossary(
        terrain=tuple(
            _entry(
                t.id,
                t.name_zh,
                None,
                _terrain_tags(t.walkable, t.deadly, t.blocks_sight),
                terrain_rules(t, rules),
            )
            for t in rules.terrain.terrain
        ),
        surfaces=tuple(
            _entry(
                s.id.value,
                s.name_zh,
                None,
                tuple(
                    tag
                    for tag, on in (
                        ("flammable", s.flammable),
                        ("beneficial", s.beneficial),
                        ("blocks_sight", s.blocks_sight),
                        ("conceal", s.conceal),
                    )
                    if on
                ),
                surface_rules(s, library),
            )
            for s in rules.surfaces.surfaces
        ),
        objects=tuple(
            _entry(o.id, o.name_zh, o.description_zh, o.tags, object_rules(o, library))
            for o in rules.objects.objects
        ),
        statuses=tuple(
            _entry(
                s.id,
                s.name_zh,
                s.description_zh,
                ("beneficial",) if s.beneficial else (),
                status_rules(s, library),
                status_look=_status_look(s),
            )
            for s in rules.statuses.statuses
        ),
        reactions=tuple(
            _entry(r.id, r.name_zh, r.description_zh) for r in rules.reactions.reactions
        ),
        stacks=tuple(
            _entry(
                k.id,
                k.name_zh,
                k.description_zh,
                (k.owner, *(("auto_consume",) if k.auto_consume is not None else ())),
                stack_rules(k, library),
            )
            for k in rules.stacks.stacks
        ),
        elements=tuple(
            _entry(e.id.value, e.name_zh, e.description_zh) for e in library.elements.elements
        ),
        attributes=tuple(_entry(a.value, a.display_name) for a in Attribute),
        effects=tuple(
            _entry(p.id, p.name_zh, p.player_description or p.description_zh, (p.category,))
            for p in rules.primitives.primitives
        ),
        conditions=tuple(
            _entry(c.id, c.name_zh, c.description_zh) for c in rules.conditions.conditions
        ),
        triggers=_triggers(library),
        actions=tuple(
            _entry(t.id, t.name_zh, t.summary_zh, (), t.lines_zh)
            for t in action_texts(rules.core, library.roguelite.refill_after_battle)
        ),
        objectives=tuple(
            _entry(t.id, t.name_zh, t.summary_zh, (), t.lines_zh) for t in objective_texts()
        ),
        weapon_looks=tuple(
            WeaponLookEntry(
                id=w.id, weapon_class=w.weapon_class, two_handed=w.two_handed, look=w.look
            )
            for w in sorted(library.weapons.values(), key=lambda w: w.id)
            if w.look is not None
        ),
        weapon_ranges=tuple(
            WeaponRangeEntry(id=w.id, weapon_class=w.weapon_class, range=w.range)
            for w in sorted(library.weapons.values(), key=lambda w: w.id)
        ),
        rules=_game_rules(library),
    )


def _game_rules(library: ContentLibrary) -> GameRulesOut:
    """畫面要用的全域規則數字（HC-3）。"""
    core = library.ruleset.core
    slots = core.skill_slots
    flash = library.flash
    run = library.roguelite
    rules = GameRulesOut(
        source_max=core.source_max,
        skill_slots=SkillSlotsOut(
            active=slots.active,
            passive=slots.passive,
            reaction=slots.reaction,
            stance=slots.stance,
        ),
        start_keywords=library.roguelite.start.keywords,
        complete_budget_permille=flash.rules.complete.budget_permille,
        # HC-6b：畫面說明文字要組字的規則數字
        roguelite_battles=run.battles,
        roguelite_companions=len(run.companions),
        campfire_source=run.source.campfire,
        budget_min_ratio_permille=library.budget.min_ratio_permille,
        budget_max_ratio_permille=library.budget.max_ratio_permille,
        contagion_radius=core.contagion_radius,
        major_flash=flash.rules.major_flash,
        complete_flashes=flash.rules.complete.flashes,
        flash_max_carry=max_carry(library),
        flash_open_cost=flash.pricing.open.cost,
        flash_open_options=flash.pricing.open.options,
        flash_open_min_categories=flash.pricing.open.min_categories,
        pregen_wait_seconds=round(WAIT_SECONDS),
        wish_cards=library.skill_pick.pool.wish_cards,
        opening_end_level=OPENING_END_LEVEL,
    )
    return rules.model_copy(update=_world_text_rules(library))


def _world_text_rules(library: ContentLibrary) -> dict[str, int]:
    """線頭、循環賽、#149 招數下限的規則數字（HC-6b）；沒有這些資料檔的精簡內容庫照欄位預設值。"""
    update: dict[str, int] = {}
    events = library.world_event_content.rules
    if events is not None:
        update["thread_limit"] = events.threads.personal_limit
        update["thread_expire_seconds"] = events.threads.expire_seconds
    league = league_rules(library)
    if league is not None:
        update["league_signup_close_day"] = league.signup_close_day
    if library.world_enemies is not None:
        floor = library.world_enemies.min_moves
        update["min_moves_mob"] = floor.mob
        update["min_moves_elite"] = floor.elite
        update["min_moves_boss_phase"] = floor.boss_phase
    return update


def _triggers(library: ContentLibrary) -> tuple[GlossaryEntry, ...]:
    """被動觸發時機（``skill_triggers.yaml``）加反應時機（``reactions.yaml`` 的 ``events``）。"""
    rules = library.ruleset
    passive = tuple(
        _entry(t.id, t.name_zh, t.description_zh) for t in rules.skill_triggers.triggers
    )
    seen = {e.id for e in passive}
    reaction = tuple(
        _entry(e.id, e.name_zh, e.description_zh)
        for e in rules.reactions.events
        if e.id not in seen
    )
    return (*passive, *reaction)
