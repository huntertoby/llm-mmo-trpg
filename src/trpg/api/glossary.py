"""名詞對照表（Phase 3-4a 6.2）：地形、表面、物件、狀態、層數、反應、元素、屬性的 ID → 中文名。

由內容庫產生，前端不再手寫中文名；只保留色塊等純顯示用的對照。``tags`` 是前端判斷外觀需要的
簡短旗標：地形為 ``blocked``／``deadly``／``blocks_sight``，表面為 ``flammable``／``beneficial``
等，物件為 ``objects.yaml`` 的標籤，層數為 ``self``／``target``（累積在誰身上）。
"""

from __future__ import annotations

from trpg.api.schemas import Glossary, GlossaryEntry, StatusLook, WeaponLookEntry
from trpg.content.battle import StatusDef
from trpg.content.library import ContentLibrary
from trpg.narrative.action_info import action_texts, objective_texts
from trpg.narrative.tile_info import object_rules, surface_rules, terrain_rules
from trpg.shared.types import Attribute

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
            _entry(o.id, o.name_zh, None, o.tags, object_rules(o, library))
            for o in rules.objects.objects
        ),
        statuses=tuple(
            _entry(
                s.id,
                s.name_zh,
                s.description_zh,
                ("beneficial",) if s.beneficial else (),
                (),
                status_look=_status_look(s),
            )
            for s in rules.statuses.statuses
        ),
        reactions=tuple(
            _entry(r.id, r.name_zh, r.description_zh) for r in rules.reactions.reactions
        ),
        stacks=tuple(
            _entry(k.id, k.name_zh, k.description_zh, (k.owner,)) for k in rules.stacks.stacks
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
            _entry(t.id, t.name_zh, t.summary_zh, (), t.lines_zh) for t in action_texts(rules.core)
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
    )


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
