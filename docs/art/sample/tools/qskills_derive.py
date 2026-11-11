"""Q-style skill icons (batch 3): derive (prop, motion, action, tint, element) for every skill.

Reads content/skills/*.yaml only. Prints a summary of how many distinct small-icon looks the
derivation rule gives (next to the current rule in docs/art/sample/assembled.js), and with
--export writes docs/art/sample/qSkillsData.js for the sample page q-icons-skills.html.

Usage (from the repo root):
    uv run python docs/art/sample/tools/qskills_derive.py            # summary tables
    uv run python docs/art/sample/tools/qskills_derive.py --export   # also write qSkillsData.js
    uv run python docs/art/sample/tools/qskills_derive.py --no-name  # rule without name keywords
    uv run python docs/art/sample/tools/qskills_derive.py --list     # one line per skill

The rule table is documented in docs/art/Q版小圖示-第3批技能主圖.md (section 4); this file is
the reference implementation the backend port (narrative/skill_icon.py) should follow.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
SKILLS = ROOT / "content" / "skills"
OUT = Path(__file__).resolve().parents[1] / "qSkillsData.js"

ELEMENTS = ("physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow")
STARTERS = (
    "skill_shadow_backstab",
    "skill_wild_blade",
    "skill_rng_venom_arrow",
    "skill_oil_spark_throw",
    "skill_fire_bolt",
    "skill_spark_chain",
)

# ---- prop tables -----------------------------------------------------------------------------
# wielding_weapon ids that are not a weapon "kind" themselves -> kind/form of the icon art.
WEAPON_LOOK = {
    "arcane_blade": "sword/arcane",
    "tower_shield": "kite_shield/tower",
    "round_shield": "round_shield/wood",
    "tome": "tome/book",
    "orb": "orb/ball",
    "one_handed_sword": "sword",
    "fire_staff": "staff",
    "lightning_staff": "staff",
    "frost_staff": "staff",
    "scepter": "staff/scepter",
    "totem_staff": "staff/totem",
    "bow_guard": "bow",
}
# name_zh keywords -> weapon kind, first hit wins (only for weapon_req melee / ranged).
# v2 (review): only words that NAME a weapon stay. Generic verbs (射擊、彈、重擊、碎、踏、撞、
# 刺、劈…) are gone: they drew bow skills as rifles and stomps as gauntlets. A skill whose name
# does not name its weapon falls back to the class default (sword / bow) until content can say
# so itself (optional field icon_prop, see the batch record).
MELEE_WORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("盾",), "kite_shield"),
    (("鞭",), "whip"),
    (("拳",), "fist"),
    (("匕",), "dagger"),
    (("矛", "槍"), "spear"),
    (("斧",), "axe"),
    (("鐮",), "scythe"),
    (("錘", "鎚"), "hammer"),
)
RANGED_WORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("弩",), "crossbow"),
    (("飛刃", "飛刀"), "kunai"),
    (("槍",), "longgun"),  # v3: "狙" dropped (sniping is not a rifle by name; falls back to bow)
)
# melee weapons whose single-target attack is a thrust, not a swing
THRUST_PROPS = ("w:spear", "w:dagger")
RANGED_KINDS = ("bow", "crossbow", "longgun", "shotgun", "pistol", "dual_pistol", "kunai")
SUMMON_GROUP = {
    "elemental_spirit": "spirit",
    "fire_spirit": "spirit",
    "ice_spirit": "spirit",
    "thunder_spirit": "spirit",
    "water_sprite": "spirit",
    "guardian_spirit": "guardian",
    "skeleton_warrior": "skeleton",
    "shade": "shade",
    "mist_shade": "shade",
    "golem": "golem",
    "bomb_puppet": "bomb",
    "earth_wall": "wall",
    "war_wolf": "wolf",
    "hawk": "hawk",
    "ember_whelp": "whelp",
    "vine": "vine",
    "war_totem": "totem",
    "pull_totem": "totem",
    "plateau_totem": "totem",
}
SUMMON_TINT = {
    "fire_spirit": "fire",
    "ice_spirit": "ice",
    "thunder_spirit": "lightning",
    "water_sprite": "water",
    "guardian_spirit": "holy",
    "mist_shade": "ice",
    "shade": "shadow",
    "ember_whelp": "fire",
    "bomb_puppet": "fire",
    "pull_totem": "shadow",
    "plateau_totem": "wind",
    "war_totem": "fire",
}
MOD_TAG_PROP = {"heal": "el:holy", "summon": "summon:spirit", "ranged": "w:bow"}
# modifier change key -> tint of the "modify" mark (add_element uses the element itself).
MOD_TINT = {
    "damage_permille": "blood",
    "on_hit_effects": "lightning",
    "cooldown_delta": "water",
    "area_delta": "wind",
    "shape_to": "wind",
    "grant_pierce": "wind",
    "push_distance_delta": "impact",
    "summon_hp_permille": "holy",
    "summon_limit_delta": "holy",
    "form_upkeep_permille": "poison",
    "allow_self_target": "holy",
}

# ---- action tables ---------------------------------------------------------------------------
DOT = {"burning": "fire", "poison": "poison", "bleed": "blood"}
# the lock: only for "cannot act / cannot move" (slow has its own mark, a pocket watch)
BIND = {
    "frozen": "ice",
    "root": "earth",
    "stun": "lightning",
    "silenced": "shadow",
}
# the down arrow never uses poison green (a green down arrow reads as "download")
CURSE = {
    "weaken": "steel",
    "vulnerable": "blood",
    "feared": "shadow",
    "blinded": "shadow",
    "taunted": "fire",
}
STATUS_TINT = {
    "hasted": "wind",
    "empowered": "fire",
    "infused_fire": "fire",
    "infused_holy": "holy",
    "guarded": "steel",
    "defending": "steel",
    "stoneskin": "earth",
    "concealed": "shadow",
    "regenerating": "poison",
    "shielded_charged": "lightning",
}
COND_TINT = {
    "burning": "fire",
    "frozen": "ice",
    "poison": "poison",
    "marked": "blood",
    "slow": "water",
    "prone": "impact",
    "target_collided": "impact",
    "target_on_surface": "water",
    "height_advantage": "wind",
    "from_behind": "shadow",
    "self_concealed": "shadow",
    "flanked": "shadow",
    "target_isolated": "shadow",
    "on_own_rune": "lightning",
}
SURFACE_TINT = {
    "fire": "fire",
    "water": "water",
    "ice": "ice",
    "poison": "poison",
    "oil": "earth",
    "smoke": "steel",
    "darkness": "shadow",
    "holy": "holy",
}
# effect type -> action; scanned in this order, first effect type present wins.
EFFECT_ACTION: tuple[tuple[tuple[str, ...], str], ...] = (
    (("enter_form",), "transform"),
    (("summon",), "summon"),
    (("sacrifice_summon", "consume_status", "detonate_runes"), "detonate"),
    (("place_trap", "delayed_damage", "inscribe"), "trap"),
    (("shadowstep", "teleport", "teleport_target", "swap", "swap_any"), "step"),
    (("dash", "leap", "charge_through"), "dash"),
    (("pull",), "pull"),
    (("push", "blow_surface", "shockwave", "hurl_object"), "push"),
    (("knock_prone", "topple"), "knockdown"),
    (("heal", "revive"), "heal"),
    (("shield", "cheat_death", "redirect_damage", "intercept"), "shield"),
)
LATE_ACTION: tuple[tuple[tuple[str, ...], str], ...] = (
    (("create_surface", "zone", "clear_surface"), "surface"),
    # v2: terrain / obstacles share the ground-effect mark, tinted stone grey
    (("create_obstacle", "raise_terrain", "lower_terrain", "destroy_object"), "terrain"),
    (("add_stack",), "builder"),
    (("consume_stack",), "finisher"),
    (("dispel", "steal_buff"), "curse"),
    (
        (
            "cleanse",
            "restore_resource",
            "reset_cooldown",
            "grant_ap",
            "grant_skill",
            "extra_reaction",
            "rule_change",
            "copy_skill",
            "leave_form",
            "reveal",
        ),
        "buff",
    ),
)
AREA_SHAPES = ("square3", "cross", "allies_in_radius")
# actions that are drawn on a prop (afterimages, tip flash...): they never stand alone.
NEEDS_PROP = ("hit", "combo", "finisher", "step", "dash", "transform", "summon")


def _effects(skill: dict[str, Any]) -> list[dict[str, Any]]:
    main = [e for e in skill.get("effects") or [] if isinstance(e, dict)]
    follow = [e for e in (skill.get("followup") or {}).get("effects") or [] if isinstance(e, dict)]
    return main + follow


def elements_of(skill: dict[str, Any]) -> list[str]:
    """Same rule as narrative/skill_icon.py: effect elements, else the first element tag."""
    found: list[str] = []
    for e in _effects(skill):
        el = e.get("element")
        if isinstance(el, str) and el not in found:
            found.append(el)
    if not found:
        found = [t for t in skill.get("tags") or [] if t in ELEMENTS][:1]
    return found


def _first_word(name: str, table: tuple[tuple[tuple[str, ...], str], ...]) -> str | None:
    for words, kind in table:
        if any(w in name for w in words):
            return kind
    return None


def _is_modifier(skill: dict[str, Any]) -> bool:
    return skill.get("kind") == "modifier" or (not _effects(skill) and bool(skill.get("modifiers")))


def _prop_special(skill: dict[str, Any]) -> str | None:
    """1. forms, 2. the weapon a wielding_weapon condition names."""
    effects = _effects(skill)
    for e in effects:
        if e.get("type") == "enter_form":
            return f"form:{e.get('form')}"
    for e in effects:
        cond = e.get("condition") or {}
        if cond.get("type") == "wielding_weapon" and cond.get("weapon"):
            weapon = str(cond["weapon"])
            return "w:" + WEAPON_LOOK.get(weapon, weapon)
    return None


def _prop_modifier(skill: dict[str, Any]) -> str | None:
    """3. modifiers: what they modify (attacks -> the weapon class, tagged skills, all skills)."""
    if not _is_modifier(skill):
        return None
    req = skill.get("weapon_req")
    applies = ((skill.get("modifiers") or [{}])[0]).get("applies_to") or {}
    for tag in applies.get("skill_tags") or []:
        if tag in MOD_TAG_PROP:
            return MOD_TAG_PROP[tag]
    if applies.get("all_attacks") or "attack" in (applies.get("actions") or []):
        return "w:bow" if req == "ranged" else "w:sword"
    if (applies.get("actions") or applies.get("skill_tags")) and req == "melee":
        return "w:fist"
    return "w:tome/book"


def _prop_weapon_class(skill: dict[str, Any], use_name: bool) -> str | None:
    """4. weapon_req melee / ranged: tags, then name keywords, then shape, then the default."""
    req = skill.get("weapon_req")
    name = skill.get("name_zh") or ""
    tags = skill.get("tags") or []
    if req == "ranged":
        return "w:" + ((_first_word(name, RANGED_WORDS) if use_name else None) or "bow")
    if req != "melee":
        return None
    if "stealth" in tags:
        return "w:dagger"
    if "martial" in tags:
        return "w:fist"
    hit = _first_word(name, MELEE_WORDS) if use_name else None
    if hit:
        return "w:" + hit
    shape = (skill.get("shape") or {}).get("type")
    return "w:greatsword" if shape in ("cone", "ring") else "w:sword"


def _prop_spell(skill: dict[str, Any], els: list[str]) -> str:
    """5. the summoned unit, 6. the element prop, 7. nothing (the action mark is the picture)."""
    effects = _effects(skill)
    tags = skill.get("tags") or []
    for e in effects:
        if e.get("type") == "summon":
            unit = str(e.get("unit") or "").removeprefix("summon_")
            return "summon:" + SUMMON_GROUP.get(unit, "spirit")
    el = els[0] if els else None
    if el not in (None, "physical"):
        return f"el:{el}"
    if "water" in tags or "water" in [e.get("surface") for e in effects]:
        return "el:water"
    return "el:arcane" if "arcane" in tags else "none"


def derive_prop(skill: dict[str, Any], els: list[str], use_name: bool) -> str:
    return (
        _prop_special(skill)
        or _prop_modifier(skill)
        or _prop_weapon_class(skill, use_name)
        or _prop_spell(skill, els)
    )


SHAPE_MOTION = {
    "chain": "chain",
    "line": "thrust",
    "cone": "sweep",
    "ring": "spin",
    "square3": "area",
    "cross": "area",
    "allies_in_radius": "area",
    "ground_tile": "place",
    "self": "aura",
    None: "aura",
}


def derive_motion(skill: dict[str, Any], prop: str) -> str:
    shape = skill.get("shape") or {}
    kind = shape.get("type")
    if kind in SHAPE_MOTION:
        return SHAPE_MOTION[kind]
    if prop.startswith("w:") and skill.get("weapon_req") == "melee":
        thrust = kind == "single" and prop.partition("/")[0] in THRUST_PROPS
        return "thrust" if thrust else "swing"
    # v2: a touch-range single target is not a projectile (no comet tail). Ranged weapons keep
    # "shot": the picture draws no line for them (the tip flash / mark is the shot).
    ranged_weapon = prop.startswith("w:") and prop[2:].partition("/")[0] in RANGED_KINDS
    if kind == "single" and shape.get("range") in (1, None) and not ranged_weapon:
        return "swing"
    return "shot"


Action = tuple[str, str | None]


def _status_action(status: str) -> Action:
    if status in DOT:
        return "dot", DOT[status]
    if status in BIND:
        return "bind", BIND[status]
    if status == "slow":
        return "slow", None
    if status == "marked":
        return "mark", None
    if status in CURSE:
        return "curse", CURSE[status]
    return "buff", STATUS_TINT.get(status)


def _action_setup(skill: dict[str, Any]) -> Action | None:
    """Modifiers, and charged skills (shield now, the second segment next turn)."""
    if _is_modifier(skill):
        change = ((skill.get("modifiers") or [{}])[0]).get("change") or {}
        el = change.get("add_element")
        if isinstance(el, str):
            return "modify", el
        return "modify", next((MOD_TINT[k] for k in change if k in MOD_TINT), None)
    follow = skill.get("followup") or {}
    main_types = {e.get("type") for e in skill.get("effects") or [] if isinstance(e, dict)}
    if follow.get("when") == "delayed" and main_types <= {"shield"}:
        els = [e.get("element") for e in follow.get("effects") or [] if e.get("element")]
        f_el = els[0] if els else None
        return "builder", f_el if f_el != "physical" else None
    return None


def _action_effect(
    skill: dict[str, Any], table: tuple[tuple[tuple[str, ...], str], ...]
) -> Action | None:
    """First group of the table that has an effect in the skill (table order = priority)."""
    effects = _effects(skill)
    for group, action in table:
        for e in effects:
            if e.get("type") not in group:
                continue
            if action == "summon":
                return action, SUMMON_TINT.get(str(e.get("unit") or "").removeprefix("summon_"))
            if action == "detonate":
                status = e.get("status") or ""
                return action, DOT.get(status) or BIND.get(status)
            if action == "surface":
                return action, SURFACE_TINT.get(e.get("surface") or "")
            if action == "terrain":
                return "surface", "stone"
            return action, None
    return None


def _action_status(skill: dict[str, Any]) -> Action | None:
    for e in _effects(skill):
        if e.get("type") == "apply_status" and e.get("status"):
            return _status_action(str(e["status"]))
    return None


def _action_damage(skill: dict[str, Any], els: list[str]) -> Action:
    effects = _effects(skill)
    if "finisher" in (skill.get("tags") or []):
        return "finisher", None
    damages = [e for e in effects if e.get("type") == "damage"]
    conds = [e.get("condition") for e in damages if e.get("condition")]
    if len(damages) > 1 or conds:
        keys = [str(cond.get("status") or cond.get("type")) for cond in conds]
        tint = next((COND_TINT[k] for k in keys if k in COND_TINT), None)
        return "combo", tint or (els[1] if len(els) > 1 else None)
    return ("hit", None) if damages else ("buff", None)


def derive_action(skill: dict[str, Any], els: list[str]) -> Action:
    """(action, tint). Priority: see the rule table in the batch 3 record, section 4.3."""
    return (
        _action_setup(skill)
        or _action_effect(skill, EFFECT_ACTION)
        or _action_status(skill)
        or _action_effect(skill, LATE_ACTION)
        or _action_damage(skill, els)
    )


def derive(skill: dict[str, Any], use_name: bool = True) -> dict[str, Any]:
    els = elements_of(skill)
    prop = derive_prop(skill, els, use_name)
    action, tint = derive_action(skill, els)
    if prop == "none" and action in NEEDS_PROP:
        prop = "el:arcane"
    motion = derive_motion(skill, prop)
    variants = [v for v in skill.get("variants") or [] if isinstance(v, dict) and v.get("element")]
    return {
        "prop": prop,
        "motion": motion,
        "act": action,
        "tint": tint,
        "el": els[0] if els else None,
        "el2": els[1] if len(els) > 1 else None,
        "spark": variants[0]["element"] if variants else None,
    }


# ---- the current rule (docs/art/sample/assembled.js partsOf + skillIcons.js motif) ------------
RANGED_FROM = 2  # skillIcons.js isRanged(): a numeric range of 2 or more draws a projectile


def _current_motif(seg: dict[str, Any], req: str | None, tags: list[str]) -> str:
    shape = (seg.get("shape") or {}).get("type")
    rng = (seg.get("shape") or {}).get("range")
    skeleton = seg.get("skeleton")
    if isinstance(rng, int):
        ranged = rng >= RANGED_FROM
    elif rng == "weapon" and req:
        ranged = req == "ranged"
    else:
        ranged = any(t in ("bow", "ranged", "arrow") for t in tags)
    if shape == "single":
        return "buff" if skeleton == "aura" else ("projectile" if ranged else "slash")
    if shape == "ground_tile":
        return f"ground:{skeleton if skeleton in ('summon', 'trap') else ''}"
    if shape in ("unit_pair", "unit_then_tile"):
        return "pair"
    if shape in ("line", "cone", "square3", "cross", "ring", "chain", "allies_in_radius"):
        return str(shape)
    if shape == "object_then_tile":
        return "hurl"
    return f"self:{'stance' if skeleton == 'stance' else ''}"


def _effect_key(e: dict[str, Any]) -> str:
    if e.get("type") == "apply_status" and e.get("status"):
        return f"status:{e['status']}"
    if e.get("type") == "create_surface" and e.get("surface"):
        return f"surface:{e['surface']}"
    return str(e.get("type"))


def current_look(skill: dict[str, Any]) -> tuple[Any, ...]:
    els = elements_of(skill)
    tags = skill.get("tags") or []
    req = skill.get("weapon_req")
    kind = skill.get("kind")
    follow = skill.get("followup")
    mods = skill.get("modifiers") or []
    keys: list[str] = []
    for e in _effects(skill):
        key = _effect_key(e)
        if key not in keys:
            keys.append(key)
    if mods:
        keys = [k for m in mods for k in (m.get("change") or {})]
    core = next((k for k in keys if k != "damage"), keys[0] if keys else None)
    if mods:
        applies = mods[0].get("applies_to") or {}
        main: Any = ("mod", json.dumps(applies, sort_keys=True, ensure_ascii=False))
    elif kind == "reaction":
        main = ("trigger", (skill.get("reaction") or {}).get("event"))
    elif kind == "passive":
        main = ("trigger", (skill.get("trigger") or {}).get("event"))
    elif follow:
        f_els = []
        for e in follow.get("effects") or []:
            if e.get("element") and e["element"] not in f_els:
                f_els.append(e["element"])
        main = (
            "two",
            _current_motif(skill, req, tags),
            _current_motif(follow, req, tags),
            tuple((f_els or els)[:1]),
            follow.get("when"),
        )
    else:
        main = _current_motif(skill, req, tags)
    return (els[0] if els else None, els[1] if len(els) > 1 else None, main, core)


def frame_of(skill: dict[str, Any]) -> tuple[Any, ...]:
    return (skill.get("kind"), skill.get("rarity"))


# ---- export for the sample page --------------------------------------------------------------
COST_KEYS = ("source", "on_miss", "self_status", "uses_per_battle", "stacks")


def _segment(d: dict[str, Any]) -> dict[str, Any]:
    shape = d.get("shape") or {}
    rows = []
    for e in d.get("effects") or []:
        row = {"type": e["type"]}
        for k in ("status", "surface", "affects"):
            if k in e:
                row[k] = e[k]
        if e.get("condition"):
            row["condition"] = e["condition"].get("type")
        rows.append(row)
    return {
        "skeleton": d.get("skeleton"),
        "shape": shape.get("type"),
        "range": shape.get("range"),
        "effects": rows,
    }


def export_row(skill: dict[str, Any], use_name: bool) -> dict[str, Any]:
    """Same fields as tools/export_skills.py (what AssembledIcon.draw reads) plus q = derive()."""
    els = elements_of(skill)
    cost = skill.get("cost") or {}
    follow = skill.get("followup")
    out: dict[str, Any] = {
        "id": skill["id"],
        "name": skill["name_zh"],
        "kind": skill["kind"],
        "rarity": skill["rarity"],
        "weapon_req": skill.get("weapon_req"),
        "elements": els,
        **_segment(skill),
        "condition": (skill.get("condition") or {}).get("type"),
        "cost": {k: cost[k] for k in COST_KEYS if k in cost},
        "activation": skill.get("activation"),
        "trigger": (skill.get("trigger") or {}).get("event"),
        "reaction": (skill.get("reaction") or {}).get("event"),
        "tags": skill.get("tags") or [],
        "q": derive(skill, use_name),
    }
    if skill.get("enemy_only"):
        out["enemy_only"] = True
    if follow:
        f_els = [e["element"] for e in follow.get("effects") or [] if e.get("element")]
        out["followup"] = {
            "when": follow.get("when"),
            "release": follow.get("release"),
            **_segment(follow),
            "elements": f_els[:1] or els,
        }
    if skill.get("modifiers"):
        out["modifiers"] = [
            {"applies_to": m.get("applies_to"), "change": m.get("change")}
            for m in skill["modifiers"]
        ]
    return out


TINTED_SUMMONS = ("summon:spirit", "summon:shade", "summon:totem")
UNTINTED_ACTS = (
    "hit",
    "finisher",
    "knockdown",
    "push",
    "pull",
    "dash",
    "heal",
    "trap",
    "step",
    "mark",
    "slow",
)


def look_key(q: dict[str, Any]) -> tuple[Any, ...]:
    """What the picture actually shows (qIconsSkills.js), so two skills with the same key are
    pixel-identical inside the frame. 24px is the same picture as 40px, only simplified."""
    prop, motion, act, tint = q["prop"], q["motion"], q["act"], q["tint"]
    if act == "dot" and prop == f"el:{tint}":
        act, tint = "hit", None  # fire prop + burning: the mark is not drawn twice
    if act == "step":
        motion = None  # afterimages replace the motion line
    if prop.startswith("summon:") and act == "summon" and prop not in TINTED_SUMMONS:
        tint = None  # only spirits, shades and totems are recoloured
    if act in UNTINTED_ACTS:
        tint = None
    spark = q["spark"] if act == "hit" and prop.startswith("w:") else None
    return (prop, motion, act, tint, q["el"], q["el2"], spark)


def _groups(skills: list[dict[str, Any]], key: Any) -> dict[Any, list[str]]:
    out: dict[Any, list[str]] = defaultdict(list)
    for s in skills:
        out[key(s)].append(s["name_zh"])
    return out


def summary(skills: list[dict[str, Any]], use_name: bool) -> None:
    qs = {s["id"]: derive(s, use_name) for s in skills}
    cur = _groups(skills, current_look)
    cur_f = _groups(skills, lambda s: (current_look(s), frame_of(s)))
    new40 = _groups(skills, lambda s: look_key(qs[s["id"]]))
    new40_f = _groups(skills, lambda s: (look_key(qs[s["id"]]), frame_of(s)))

    def biggest(groups: dict[Any, list[str]]) -> int:
        return max(map(len, groups.values()))

    print(f"技能數 {len(skills)}（名稱關鍵字{'有' if use_name else '沒有'}用）")
    print("| | 只看圖與底：種數／最大同圖群 | 加上外框（類型、稀有度）：種數／最大同圖群 |")
    print("|---|---|---|")
    print(f"| 現行小圖 | {len(cur)}／{biggest(cur)} | {len(cur_f)}／{biggest(cur_f)} |")
    print(f"| Q 版小圖 | {len(new40)}／{biggest(new40)} | {len(new40_f)}／{biggest(new40_f)} |")
    for label, field in (("道具", "prop"), ("出手", "motion"), ("效果", "act"), ("元素底", "el")):
        count = Counter(str(q[field]) for q in qs.values())
        print(
            f"\n{label} {len(count)} 種：" + "、".join(f"{k} {v}" for k, v in count.most_common())
        )
    combos = {(q["prop"], q["motion"], q["act"]) for q in qs.values()}
    print(f"\n道具 × 出手 × 效果 的組合 {len(combos)} 種；再乘元素底與染色共 {len(new40)} 種")
    print("\n最大的 10 個同圖群（Q 版 40px）：")
    for key, names in sorted(new40.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))[:10]:
        head = "｜".join(str(k) for k in key[:4])
        print(f"- {len(names)} 招 {head}｜底 {key[4]}：{'、'.join(names)}")
    print("\n現行最大的 5 個同圖群：")
    for key, names in sorted(cur.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))[:5]:
        print(f"- {len(names)} 招 {key}：{'、'.join(names)}")
    print("\n六招入門招：")
    for s in skills:
        if s["id"] in STARTERS:
            q = qs[s["id"]]
            head = "｜".join(str(q[k]) for k in ("prop", "motion", "act"))
            print(f"- {s['name_zh']}：{head}｜染 {q['tint']}｜底 {q['el']}")
    lost = [n for names in new40.values() if len(names) > 1 for n in names]
    lost_now = sum(len(v) for v in cur.values() if len(v) > 1)
    print(f"\n仍和別招同圖的招數：{len(lost)}（現行 {lost_now}）")
    # information that disappears: same Q picture and frame, but the current icons differ
    by_id = {s["id"]: s for s in skills}
    same_q: dict[Any, list[str]] = defaultdict(list)
    for s in skills:
        same_q[(look_key(qs[s["id"]]), frame_of(s))].append(s["id"])
    print("\n現行分得開、Q 版同一張的（同框同圖；括號裡是現行靠什麼分）：")
    count = 0
    for ids in same_q.values():
        looks = {i: current_look(by_id[i]) for i in ids}
        if len(set(looks.values())) == 1:
            continue
        count += len(ids)
        parts = [f"{by_id[i]['name_zh']}（{looks[i][2]}＋{looks[i][3]}）" for i in ids]
        print("- " + "、".join(parts))
    print(f"共 {count} 招")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true", help="write qSkillsData.js")
    parser.add_argument("--no-name", action="store_true", help="ignore the name keyword tables")
    parser.add_argument("--list", action="store_true", help="print one line per skill")
    parser.add_argument("--all", action="store_true", help="count enemy_only skills too")
    args = parser.parse_args()
    skills = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(SKILLS.glob("*.yaml"))]
    use_name = not args.no_name
    if args.list:
        for s in skills:
            q = derive(s, use_name)
            mark = "|enemy_only" if s.get("enemy_only") else ""
            head = f"{s['name_zh']}|{q['prop']}|{q['motion']}|{q['act']}|{q['tint']}|{q['el']}"
            print(head + mark)
        return
    # v2: the statistics are about icons the player sees; enemy_only skills are listed apart.
    enemy = [s for s in skills if s.get("enemy_only")]
    counted = skills if args.all else [s for s in skills if not s.get("enemy_only")]
    summary(counted, use_name)
    if enemy and not args.all:
        print(f"\n另列：enemy_only {len(enemy)} 招（不在上面的統計內）：")
        for s in enemy:
            q = derive(s, use_name)
            print(f"- {s['name_zh']}：{q['prop']}｜{q['motion']}｜{q['act']}｜染 {q['tint']}")
    if args.export:
        rows = [export_row(s, use_name) for s in skills]
        OUT.write_text(
            "// 由 tools/qskills_derive.py 從 content/skills/ 匯出"
            "（Q 版小圖示第 3 批樣張用；不要手改）\n"
            f"window.QSKILLS = {json.dumps(rows, ensure_ascii=False)};\n",
            encoding="utf-8",
        )
        print(f"\n{len(rows)} skills -> {OUT}")


if __name__ == "__main__":
    main()
