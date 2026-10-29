"""第 3 次閃現的大變化：轉型、輔助類與召喚類的加深／橋接、欄位卸下判定（Phase 3W-3，
``docs/design/06-技能.md`` 6.34.5；玩法決定 #70、#73）。

純函式、確定性。資料在 ``content/flash_templates.yaml`` 的 ``transforms``（轉型）與 ``extra_major``
（補充的大變化）兩個區段；:mod:`trpg.skillgen.flash` 負責把它們接進出題（``make_offer``）與套用
（``apply_variation``、``derive_skill``）。

**轉型**（:data:`TransformTemplate`）：主動技轉成別種技能，依 **角色階級** 開放（#73）：

- 1 階：被動（``to_passive_on_hit``）、反應（``to_reaction_melee``）；
- 2 階起：加開召喚（``to_summon``）、陷阱（``to_trap``）、姿態（``to_stance``）；
- 3 階起：加開修正型被動（``to_modifier``）。

每種轉型只描述「新技能的結構」（:func:`transform_drafts`）；強度由預算器依 **新種類** 的預算重算
（沿用進化的調整器 :func:`~trpg.skillgen.evolution.retune`，調整器做不出來的固定強度種類——召喚、
姿態、修正型被動——改以驗證器直接檢查預算窗，:func:`finish_transform`）。轉型的技能照原本的
「強度下限」不比較（預算類別換了，分數不可比）；只要預算窗與驗證器全過就算合法。

**保底**（#70）：第 3 次（或重閃第 3 次）有合法轉型就一定是選項之一。可轉的種類有好幾種時，由
種子挑一種：:func:`transform_variations` 把種類洗牌後輪流排列，出題時取第一個做得出來的。

**欄位**（:func:`transform_slot_plan`）：轉型後的技能佔用的欄位照 ``SkillDef.slot_kind``；和原招
不同欄且目標欄位已滿時，回傳「需要卸下」幾個、可以卸哪些（流程在 3W-5，這裡只判定）。

**補充的大變化**（:func:`extra_variations`、:func:`apply_extra`）：輔助技（治療、護盾、增益）多半沒有
進化模板可套，這裡補三個（範圍擴大、冷卻縮短、附帶場地）；召喚技能沿用 3-33f2 的三支
（加深、數量型、橋接）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from trpg.content.flash_templates import ExtraMajorTemplate, TransformTemplate
from trpg.content.library import ContentLibrary
from trpg.content.rules import SkillSlots
from trpg.content.skills import SkillDef, rarity_rank, skill_elements
from trpg.engine.skill_levels import grow_shape
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.evolution import EvolutionRequest, retune
from trpg.skillgen.evolution import rarity_of as _rarity_of
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.scaling import fit_scaling
from trpg.skillgen.summon_evolution import is_summon_skill, summon_evolution_options
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

__all__ = [
    "TRANSFORM_CATEGORY",
    "SlotPlan",
    "apply_extra",
    "extra_prefix",
    "extra_summary",
    "extra_variations",
    "finish_transform",
    "is_extra_template",
    "meets_floor",
    "transform_drafts",
    "transform_prefix",
    "transform_slot_plan",
    "transform_summary",
    "transform_variations",
]

TRANSFORM_CATEGORY = "transform"
"""轉型變化的類別 ID（不是可指定的類別；大變化時保底出現）。"""

type _Draft = tuple[dict[str, Any], list[dict[str, Any]]]

_LEGENDARY = rarity_rank("legendary")
_RESET: dict[str, Any] = {
    "followup": None,
    "variants": [],
    "trap": None,
    "trigger": None,
    "reaction": None,
    "condition": None,
    "modifiers": [],
    "mastery": None,
    "crit_range": None,
    "damage_permille": None,
    "pierce": False,
    "weapon_only": [],
    "activation": None,
    "exclusive_group": None,
    "include_caster": False,
    "secondary_scaling_attr": None,
}
"""轉型時從原招清掉的欄位（新種類各有自己的結構）。"""

_HOSTILE = (None, "enemies")
_CORE_TYPES = ("damage", "apply_status")
"""被動、反應、陷阱帶得走的敵對效果（其餘原語在轉型時省略）。"""
_MAX_CARRIED = 2
_MAX_TRAP_EFFECTS = 3


# ---------------------------------------------------------------------------
# 共用
# ---------------------------------------------------------------------------


def _base(skill: SkillDef) -> _Draft:
    base = skill.model_dump(mode="json")
    effects: list[dict[str, Any]] = [
        e.model_dump(mode="json", exclude_none=True) for e in skill.effects
    ]
    base.pop("effects")
    return base, effects


def skill_element_id(skill: SkillDef) -> str | None:
    """技能的主題元素 ID（傷害效果的非物理元素優先，其次技能元素）；沒有時 ``None``。"""
    for effect in skill.effects:
        if effect.type == "damage" and effect.element not in (None, Element.PHYSICAL):
            assert effect.element is not None
            return effect.element.value
    found = sorted(e.value for e in skill_elements(skill))
    return found[0] if found else None


def _hostile_core(skill: SkillDef) -> list[dict[str, Any]]:
    """敵對的核心效果（傷害優先、再來狀態），最多 :data:`_MAX_CARRIED` 個；去掉骰子與倍率（新種類
    由預算器重調）。"""
    out: list[dict[str, Any]] = []
    for effect in sorted(skill.effects, key=lambda e: e.type != "damage"):
        if effect.type not in _CORE_TYPES or effect.affects not in _HOSTILE:
            continue
        item: dict[str, Any] = {"type": effect.type, "affects": "enemies"}
        if effect.type == "damage":
            element = skill_element_id(skill) if effect.element is None else effect.element.value
            if element is not None and element != "physical":
                item["element"] = element
        else:
            if effect.status is None:
                continue
            item["status"] = effect.status
            if effect.duration is not None:
                item["duration"] = effect.duration
        if item not in out:
            out.append(item)
    return out[:_MAX_CARRIED]


def _retag(skill: SkillDef, *extra: str) -> list[str]:
    """轉型後的標籤：保留元素標籤，加上新種類的標籤。"""
    elements = {e.value for e in skill_elements(skill)}
    kept = [t for t in skill.tags if t in elements]
    return [*dict.fromkeys([*kept, "spell", *extra])]


def _new_base(skill: SkillDef, **changes: Any) -> dict[str, Any]:
    """原招的欄位去掉舊種類的結構，改成法術類（觸發的效果自動命中，不看武器）。"""
    base, _ = _base(skill)
    base.update(_RESET)
    base.update({"category": "spell", "weapon_req": "any"})
    base.update(changes)
    return base


def _concept(skill: SkillDef, template: TransformTemplate) -> dict[str, Any]:
    concept = f"{skill.narrative.concept}（轉型：{template.summary_zh}）".lstrip("（")
    return {"concept": concept, "cast_flavor": skill.narrative.cast_flavor}


# ---------------------------------------------------------------------------
# 轉型：新種類的結構
# ---------------------------------------------------------------------------


def _to_passive(skill: SkillDef, t: TransformTemplate, _lib: ContentLibrary) -> list[_Draft]:
    effects = _hostile_core(skill)
    if not effects or t.trigger is None:
        return []
    drafts: list[_Draft] = []
    for cost in ({"mana": 2}, {"mana": 2, "cooldown": 2}, {}):
        base = _new_base(
            skill,
            kind="passive",
            skeleton="passive",
            ap_cost=None,
            shape={"type": "self"},
            trigger=t.trigger.model_dump(mode="json", exclude_none=True),
            cost=cost,
            tags=_retag(skill, "passive"),
            narrative=_concept(skill, t),
        )
        drafts.append((base, [dict(e) for e in effects]))
    return drafts


def _to_reaction(skill: SkillDef, t: TransformTemplate, _lib: ContentLibrary) -> list[_Draft]:
    effects = _hostile_core(skill)
    if not effects or t.reaction is None:
        return []
    drafts: list[_Draft] = []
    for cost in ({"cooldown": 1}, {"mana": 2, "cooldown": 1}, {"cooldown": 2}):
        base = _new_base(
            skill,
            kind="reaction",
            skeleton="reaction",
            ap_cost=None,
            shape={"type": "single", "range": 2},
            reaction=t.reaction.model_dump(mode="json", exclude_none=True),
            cost=cost,
            tags=_retag(skill, "reaction"),
            narrative=_concept(skill, t),
        )
        drafts.append((base, [dict(e) for e in effects]))
    return drafts


_SUMMON_COSTS: tuple[dict[str, Any], ...] = (
    {"mana": 10, "cooldown": 4},
    {"mana": 8, "cooldown": 3},
    {"mana": 12, "cooldown": 5},
)


def _to_summon(skill: SkillDef, t: TransformTemplate, _lib: ContentLibrary) -> list[_Draft]:
    if is_summon_skill(skill):
        return []
    element = skill_element_id(skill)
    units = [*t.units.get(element or "", ()), *t.units.get("any", ())]
    drafts: list[_Draft] = []
    for unit in dict.fromkeys(units):
        for cost in _SUMMON_COSTS:
            base = _new_base(
                skill,
                kind="active",
                skeleton="summon",
                ap_cost=1,
                shape={"type": "ground_tile", "range": 4},
                cost=cost,
                tags=_retag(skill, "summon"),
                narrative=_concept(skill, t),
            )
            drafts.append((base, [{"type": "summon", "unit": unit, "duration": t.summon_duration}]))
    return drafts


def _to_trap(skill: SkillDef, t: TransformTemplate, _lib: ContentLibrary) -> list[_Draft]:
    effects = _hostile_core(skill)
    if not effects or t.trap is None or skill.trap is not None:
        return []
    drafts: list[_Draft] = []
    for cost in ({"mana": 6, "cooldown": 2}, {"mana": 6, "cooldown": 3}, {"mana": 4}):
        base = _new_base(
            skill,
            kind="active",
            skeleton="trap",
            ap_cost=2,
            shape={"type": "ground_tile", "range": 4},
            trap=t.trap.model_dump(mode="json", exclude_none=True),
            cost=cost,
            tags=_retag(skill, "trap"),
            narrative=_concept(skill, t),
        )
        placed = [{"type": "place_trap"}, *(dict(e) for e in effects)]
        drafts.append((base, placed[: _MAX_TRAP_EFFECTS + 1]))
    return drafts


def _to_stance(skill: SkillDef, t: TransformTemplate, lib: ContentLibrary) -> list[_Draft]:
    offense = any(e.type in ("damage", "delayed_damage") for e in skill.effects)
    status = t.stances.get("offense" if offense else "defense")
    if status is None or status not in lib.ruleset.statuses.by_id():
        return []
    base = _new_base(
        skill,
        kind="stance",
        skeleton="stance",
        ap_cost=None,
        shape={"type": "self"},
        cost={},
        tags=_retag(skill, "stance"),
        narrative=_concept(skill, t),
    )
    return [(base, [{"type": "apply_status", "status": status, "affects": "self"}])]


def _modifier_changes(skill: SkillDef, t: TransformTemplate) -> list[dict[str, Any]]:
    """修正規則的候選改變（依序試）：先帶上原招的敵對狀態，再來傷害提高（由大到小）。"""
    changes: list[dict[str, Any]] = []
    status = next((e for e in _hostile_core(skill) if e["type"] == "apply_status"), None)
    if status is not None:
        carried = {k: v for k, v in status.items() if k != "duration"}
        changes.append({"on_hit_effects": [{**carried, "duration": 1}]})
    changes += [{"damage_permille": n} for n in t.damage_permille_steps]
    return changes


def _to_modifier(skill: SkillDef, t: TransformTemplate, _lib: ContentLibrary) -> list[_Draft]:
    if not t.damage_permille_steps or skill.kind != "active" or is_summon_skill(skill):
        return []
    element = skill_element_id(skill)
    target = {"skill_tags": [element]} if element is not None else {"all_attacks": True}
    drafts: list[_Draft] = []
    for change in _modifier_changes(skill, t):
        base = _new_base(
            skill,
            kind="modifier",
            skeleton="modifier",
            ap_cost=None,
            shape={"type": "self"},
            cost={},
            modifiers=[{"applies_to": target, "change": change}],
            tags=_retag(skill, "passive", "modifier"),
            narrative=_concept(skill, t),
        )
        drafts.append((base, []))
    return drafts


_BUILDERS = {
    "passive": _to_passive,
    "reaction": _to_reaction,
    "summon": _to_summon,
    "trap": _to_trap,
    "stance": _to_stance,
    "modifier": _to_modifier,
}


def transform_drafts(
    skill: SkillDef, variation: Variation, library: ContentLibrary
) -> list[_Draft]:
    """轉型的草稿（技能欄位 dict、效果 dict 列表；依序試，第一個通過預算的就是結果）。只有主動技
    能轉型；做不出來（沒有可帶走的效果、已經是該種類）時為空。"""
    template = library.flash.transform_template(variation.template)
    if template is None or skill.kind != "active":
        return []
    return _BUILDERS[template.to](skill, template, library)


# ---------------------------------------------------------------------------
# 草稿 → 合格的技能
# ---------------------------------------------------------------------------


def _validated(
    base: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary
) -> SkillDef | None:
    """沒有旋鈕可調的結構（召喚、姿態、修正型被動）：直接檢查預算窗與驗證器。"""
    try:
        trial = SkillDef.model_validate({**base, "effects": effects})
    except ValidationError:
        return None
    rarity = _rarity_of(base, effects, library)
    if rarity_rank(rarity) >= _LEGENDARY > rarity_rank(str(base["rarity"])):
        return None
    try:
        fitted = fit_scaling(trial.model_copy(update={"rarity": rarity}), library)
    except (ValidationError, BudgetError, ValueError):
        return None
    return None if validate_skill(fitted, library) else fitted


def finish_transform(
    base: dict[str, Any], effects: list[dict[str, Any]], rng: Rng, library: ContentLibrary
) -> SkillDef | None:
    """轉型草稿 → 通過預算與驗證的技能：有旋鈕（骰子）的先交給調整器，沒有或調不進窗內的改用直接
    檢查。做不出來時 ``None``。"""
    done = retune(base, effects, rng, library)
    return done if done is not None else _validated(base, effects, library)


def meets_floor(old: SkillDef, new: SkillDef, library: ContentLibrary) -> bool:
    """強度下限（6.34.3，玩法 PM 定）：重調後的預算分數不低於閃現前。轉型不比較（換了預算類別，分數
    不可比）。算不出預算時視為不符。"""
    try:
        return skill_budget(new, library).total >= skill_budget(old, library).total
    except BudgetError:
        return False


# ---------------------------------------------------------------------------
# 轉型的候選（依角色階級、種子挑種類）
# ---------------------------------------------------------------------------


def transform_variations(
    library: ContentLibrary, skill: SkillDef, *, tier: int, rng: Rng
) -> list[Variation]:
    """這招在角色階級 ``tier`` 可以轉型成的變化（種類由種子洗牌後輪流排列：第一個做得出來的就是
    「隨機挑的一種」；同種類有多個模板時依資料順序）。只有主動技有轉型。"""
    if skill.kind != "active":
        return []
    groups: dict[str, list[TransformTemplate]] = {}
    for template in library.flash.transforms:
        if template.min_tier <= tier:
            groups.setdefault(template.to, []).append(template)
    order = rng.shuffled(sorted(groups))
    out: list[Variation] = []
    depth = 0
    while any(len(groups[k]) > depth for k in order):
        out += [
            Variation(source="transform", template=groups[k][depth].id, category=TRANSFORM_CATEGORY)
            for k in order
            if len(groups[k]) > depth
        ]
        depth += 1
    return out


def transform_prefix(library: ContentLibrary, variation: Variation) -> str | None:
    template = library.flash.transform_template(variation.template)
    return None if template is None else template.prefix_zh


def transform_summary(library: ContentLibrary, variation: Variation) -> str:
    template = library.flash.transform_template(variation.template)
    return "" if template is None else template.summary_zh


# ---------------------------------------------------------------------------
# 欄位（召喚、陷阱、姿態佔主動欄等由 SkillDef.slot_kind 決定；滿了先卸下，流程在 3W-5）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SlotPlan:
    """轉型後的欄位判定。``new_slot`` 與 ``old_slot`` 相同時原地換招，不需要卸下；不同欄且新欄位
    已滿時 ``must_unequip`` 為需要卸下的個數，``candidates`` 是新欄位裡目前裝備的技能 ID（玩家
    從中挑；卸下的技能回到技能庫）。"""

    old_slot: str
    new_slot: str
    limit: int
    occupied: int
    must_unequip: int
    candidates: tuple[str, ...]

    @property
    def changes_slot(self) -> bool:
        return self.old_slot != self.new_slot

    @property
    def needs_unequip(self) -> bool:
        return self.must_unequip > 0


def transform_slot_plan(
    equipped: Sequence[SkillDef], old_id: str, new: SkillDef, slots: SkillSlots
) -> SlotPlan:
    """``equipped``（目前裝備，含 ``old_id`` 這一招）換成 ``new`` 之後，目標欄位要不要卸下。"""
    old = next((s for s in equipped if s.id == old_id), None)
    old_slot = new.slot_kind if old is None else old.slot_kind
    limit = int(getattr(slots, new.slot_kind))
    others = tuple(s.id for s in equipped if s.id != old_id and s.slot_kind == new.slot_kind)
    must = max(0, len(others) + 1 - limit) if old_slot != new.slot_kind else 0
    return SlotPlan(
        old_slot=old_slot,
        new_slot=new.slot_kind,
        limit=limit,
        occupied=len(others),
        must_unequip=must,
        candidates=others if must else (),
    )


# ---------------------------------------------------------------------------
# 補充的大變化：輔助技與召喚技能
# ---------------------------------------------------------------------------

_GRAFT_SURFACES = ("create_surface",)


def _support_keywords(library: ContentLibrary, skill: SkillDef) -> list[str]:
    """輔助技橋接可帶的關鍵字：嫁接表中「製造」是場地的（不會傷到友方）、這招還沒有的。"""
    present = {e.surface.value for e in skill.effects if e.surface is not None}
    return [
        keyword
        for keyword, graft in library.evolution.grafts.items()
        if graft.makes is not None
        and graft.makes.type in _GRAFT_SURFACES
        and (graft.makes.surface is None or graft.makes.surface.value not in present)
    ]


def extra_variations(
    library: ContentLibrary, skill: SkillDef, category: str, *, support: bool
) -> list[Variation]:
    """進化模板之外、適用這招的大變化候選（資料順序）。``support``：這招是輔助技。"""
    out: list[Variation] = []
    summon = is_summon_skill(skill)
    for template in library.flash.extra_major:
        if template.category != category:
            continue
        if (template.only == "support" and not support) or (
            template.only == "summon" and not summon
        ):
            continue
        if template.op == "support_imbue":
            out += [
                Variation(source="major", template=template.id, category=category, keyword=k)
                for k in _support_keywords(library, skill)
            ]
        elif template.op == "summon_bridge":
            keywords = dict.fromkeys(
                o.keyword
                for o in summon_evolution_options(library, _request(skill))
                if o.branch == "bridge" and o.keyword is not None
            )
            out += [
                Variation(source="major", template=template.id, category=category, keyword=k)
                for k in keywords
            ]
        else:
            out.append(Variation(source="major", template=template.id, category=category))
    return out


def is_extra_template(library: ContentLibrary, template_id: str) -> bool:
    return library.flash.extra_template(template_id) is not None


def extra_prefix(library: ContentLibrary, variation: Variation) -> str | None:
    template = library.flash.extra_template(variation.template)
    if template is None:
        return None
    graft = library.evolution.grafts.get(variation.keyword or "")
    if template.op == "support_imbue" and graft is not None:
        return graft.prefix_zh
    return template.prefix_zh


def extra_summary(library: ContentLibrary, variation: Variation) -> str:
    template = library.flash.extra_template(variation.template)
    if template is None:
        return ""
    name = next(
        (k.name_zh for k in library.keywords.keywords if k.id == variation.keyword),
        variation.keyword or "",
    )
    return template.summary_zh.replace("{keyword}", name)


def _request(skill: SkillDef) -> EvolutionRequest:
    return EvolutionRequest(skill=skill, usage=SkillUsage(), held_keywords={}, seed=0)


def _support_wide(skill: SkillDef, _v: Variation, library: ContentLibrary) -> list[_Draft]:
    """影響範圍 +1；單體沒有大小可加時改成十字（同射程）。"""
    base, effects = _base(skill)
    shape = grow_shape(library.ruleset, skill.shape, 1)
    if shape != skill.shape:
        base["shape"] = shape.model_dump(mode="json", exclude_none=True)
    elif skill.shape.type == "single" and isinstance(skill.shape.range, int):
        base["shape"] = {"type": "cross", "range": skill.shape.range}
    else:
        return []
    return [(base, effects)]


def _support_ease(skill: SkillDef, _v: Variation, _library: ContentLibrary) -> list[_Draft]:
    """冷卻 −1（沒有冷卻的不適用）。"""
    cooldown = skill.cost.cooldown
    if cooldown is None or cooldown < 1:
        return []
    base, effects = _base(skill)
    base["cost"] = {**base["cost"], "cooldown": cooldown - 1 or None}
    return [(base, effects)]


def _support_imbue(skill: SkillDef, variation: Variation, library: ContentLibrary) -> list[_Draft]:
    """施放時在腳下留下關鍵字的場地（嫁接表的「製造」，只用場地類）。"""
    graft = library.evolution.grafts.get(variation.keyword or "")
    if graft is None or graft.makes is None:
        return []
    base, effects = _base(skill)
    return [(base, [*effects, graft.makes.model_dump(mode="json", exclude_none=True)])]


_SUPPORT_OPS = {
    "support_wide": _support_wide,
    "support_ease": _support_ease,
    "support_imbue": _support_imbue,
}


def _support_drafts(
    skill: SkillDef, template: ExtraMajorTemplate, variation: Variation, library: ContentLibrary
) -> list[_Draft]:
    op = _SUPPORT_OPS.get(template.op)
    return [] if op is None else op(skill, variation, library)


def apply_extra(
    library: ContentLibrary, skill: SkillDef, variation: Variation, rng: Rng
) -> SkillDef | None:
    """補充大變化的套用（``skill`` 已帶這一次的預算加成）；做不出來時 ``None``。"""
    template = library.flash.extra_template(variation.template)
    if template is None:
        return None
    if template.only == "summon":
        return _apply_summon(library, skill, template, variation)
    for index, (base, effects) in enumerate(_support_drafts(skill, template, variation, library)):
        done = finish_transform(base, effects, rng.fork(str(index)), library)
        if done is not None and meets_floor(skill, done, library):
            return done
    return None


def _apply_summon(
    library: ContentLibrary, skill: SkillDef, template: ExtraMajorTemplate, variation: Variation
) -> SkillDef | None:
    if not is_summon_skill(skill):
        return None
    wanted = {
        "summon_deepen": "summon_deepen",
        "summon_count": "summon_count",
        "summon_bridge": "summon_bridge",
    }[template.op]
    for option in summon_evolution_options(library, _request(skill)):
        if option.template != wanted:
            continue
        if wanted == "summon_bridge" and option.keyword != variation.keyword:
            continue
        return option.skill if meets_floor(skill, option.skill, library) else None
    return None
