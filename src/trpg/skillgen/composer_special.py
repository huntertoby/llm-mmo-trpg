"""隨機組合器：修正技能與傳說（Phase 3C-6b，``docs/phases/Phase3C計畫.md`` 8.1）。

修正技能（``kind: modifier``，史詩以上）與傳說（三擇一的核心：修正規則、規則改變、改寫規則型原語，
再加源力代價）的點數多半是固定值，沒有可以連續調整的旋鈕，所以不走 :mod:`composer_tuning` 的
旋鈕爬升，改成「列舉候選 → 預算比例落在調整區間（``tuning``）內 → 亂數挑一個」：

1. 先抽結構（核心種類、修正的種類與套用對象、規則改變或改寫規則型原語）；
2. 再列舉階級、源力、冷卻、法力、啟動方式與參數階梯的組合，保留通過 schema 與預算驗證的；
3. 從保留的候選中用 :class:`~trpg.shared.rng.Rng` 挑一個。

整個流程只用 ``Rng(seed).fork(...)`` 的獨立串流，不影響其他種子。確定性：候選的列舉順序固定。
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.shared.types import Element
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_tuning import tuning_bounds
from trpg.skillgen.validate import validate_skill

__all__ = ["compose_legendary", "compose_modifier"]

_ELEMENTS = tuple(e.value for e in sorted(Element, key=lambda e: e.value) if e.value != "physical")

_LADDERS: dict[str, tuple[Any, ...]] = {
    "damage_permille": tuple(range(100, 701, 50)),
    "hit_bonus": (1, 2, 3),
    "cooldown_delta": (-1, -2),
    "push_distance_delta": (1, 2),
    "ap_delta": (-1,),
    "range_delta": (1, 2),
    "area_delta": (1,),
    "grant_pierce": (True,),
    "allow_self_target": (True,),
    "shape_to": ("line", "chain", "cone"),
}
"""修正規則各種改變的值階梯（由弱到強）。``add_element``、``add_tags`` 另外處理。"""

_CHANGE_KINDS = (*sorted(_LADDERS), "add_element", "add_tags")
_ACTIONS = ("attack", "shove", "trip")
_CONDITION_STATUSES = ("burning", "bleed", "poison", "frozen", "prone")
_REWRITE = ("grant_ap", "reset_cooldown", "cheat_death", "redirect_damage", "extra_reaction")
"""傳說可用的改寫規則型原語（``copy_skill`` 需要場上有別人剛施放的技能，只給手寫者）。"""


def _attr(rng: Rng, library: ContentLibrary) -> str:
    weights = library.composer.spell_attr_weights
    roll = rng.randint(1, weights.int_ + weights.wis + weights.wil)
    if roll <= weights.int_:
        return "int"
    return "wis" if roll <= weights.int_ + weights.wis else "wil"


def _tags_for(theme: str, rarity: str, kind: str) -> list[str]:
    tags = [theme]
    if kind == "modifier":
        tags += ["passive", "modifier"]
    if rarity == "legendary":
        tags.append("legendary")
    return tags


def _data(seed: int, label: str, rarity: str, theme: str, extra: dict[str, Any]) -> dict[str, Any]:
    """技能資料的共同欄位（名稱、標籤、敘事文字都是暫定的）。"""
    return {
        "id": f"skill_rand_{seed}",
        "name_zh": f"{label} #{seed}",
        "rarity": rarity,
        "category": "spell",
        "weapon_req": "any",
        "tags": _tags_for(theme, rarity, extra["kind"]),
        "narrative": {
            "concept": f"隨機組合器產生的{label}技能（種子 {seed}，暫定）",
            "cast_flavor": "（暫定）力量依你的意志成形。",
        },
        "provenance": {"origin": "level_up"},
        **extra,
    }


def _pick(rng: Rng, library: ContentLibrary, candidates: list[dict[str, Any]]) -> SkillDef | None:
    """候選中預算比例落在調整區間、且通過驗證的，隨機挑一個。"""
    low, high = tuning_bounds(library)
    fits: list[SkillDef] = []
    for data in candidates:
        try:
            skill = SkillDef.model_validate(data)
            report = skill_budget(skill, library)
        except (ValidationError, BudgetError):
            continue
        if low <= report.ratio <= high:
            fits.append(skill)
    for skill in rng.shuffled(fits):
        if not validate_skill(skill, library):
            return skill
    return None


# ---------------------------------------------------------------------------
# 修正規則
# ---------------------------------------------------------------------------


def _tags(library: ContentLibrary) -> list[str]:
    """手寫技能用過的機制標籤（修正規則 ``skill_tags`` 的候選）。"""
    found = {t for s in library.skills.values() for t in s.tags}
    return sorted(found - {"legendary", "modifier", "passive", "spell", "melee"})


def _applies_to(rng: Rng, library: ContentLibrary) -> dict[str, Any]:
    kind = rng.choice(("all_attacks", "all_skills", "actions", "skill_tags", "skill_tags"))
    if kind == "actions":
        return {"actions": [rng.choice(_ACTIONS)]}
    if kind == "skill_tags":
        return {"skill_tags": [rng.choice(_tags(library))]}
    return {kind: True}


def _changes(rng: Rng, kind: str) -> list[dict[str, Any]]:
    """某種改變的候選值（由弱到強）。"""
    if kind == "add_element":
        return [{"add_element": rng.choice(_ELEMENTS)}]
    if kind == "add_tags":
        return [{"add_tags": [rng.choice(_ELEMENTS)]}]
    return [{kind: v} for v in _LADDERS[kind]]


def _rule(rng: Rng, library: ContentLibrary) -> list[dict[str, Any]]:
    """一條修正規則的候選（同一個套用對象與改變種類、不同的值；可能帶條件）。"""
    kind = rng.choice(_CHANGE_KINDS)
    applies = _applies_to(rng, library)
    condition: dict[str, Any] | None = None
    if rng.chance_permille(300):
        condition = {"type": "target_has_status", "status": rng.choice(_CONDITION_STATUSES)}
    return [
        {"applies_to": applies, "change": change, **({"condition": condition} if condition else {})}
        for change in _changes(rng, kind)
    ]


def _modifier_candidates(
    rng: Rng,
    library: ContentLibrary,
    seed: int,
    *,
    tiers: tuple[int, ...],
    legendary: bool,
) -> list[dict[str, Any]]:
    """修正技能的候選：修正規則的值 × 階級（傳說再 × 源力 × 啟動方式）。"""
    rules = _rule(rng, library)
    theme = rng.choice(_ELEMENTS)
    scaling = _attr(rng, library)
    out: list[dict[str, Any]] = []
    for tier in tiers:
        for rule in rules:
            base = {
                "tier": tier,
                "kind": "modifier",
                "skeleton": "modifier",
                "scaling_attr": scaling,
                "ap_cost": None,
                "shape": {"type": "self"},
                "effects": [],
                "modifiers": [rule],
                "condition": None,
            }
            if not legendary:
                out.append(_data(seed, "修正", "epic", theme, {**base, "cost": {}}))
                continue
            for source in (1, 2):
                for activation in ("timed", "battle"):
                    extra = {**base, "activation": activation, "cost": {"source": source}}
                    out.append(_data(seed, "傳說修正", "legendary", theme, extra))
    return out


# ---------------------------------------------------------------------------
# 規則改變與改寫規則型原語（傳說的另外兩種核心）
# ---------------------------------------------------------------------------


def _rewrite_effect(rng: Rng, primitive: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """改寫規則型原語的效果與形狀。"""
    if primitive == "grant_ap":
        return {"type": "grant_ap", "amount": rng.choice((1, 2)), "affects": "self"}, {
            "type": "self"
        }
    shape = {"type": "single", "range": rng.choice((3, 4))}
    if primitive == "reset_cooldown":
        return {"type": "reset_cooldown", "which": "all", "affects": "allies"}, shape
    if primitive == "cheat_death":
        return {"type": "cheat_death", "duration": rng.choice((1, 2)), "affects": "allies"}, shape
    if primitive == "redirect_damage":
        effect = {
            "type": "redirect_damage",
            "permille": rng.choice((200, 300, 400, 500)),
            "duration": rng.choice((2, 3)),
            "affects": "allies",
        }
        return effect, shape
    return {"type": "extra_reaction", "amount": 1, "affects": "allies"}, shape


def _lasting_candidates(
    rng: Rng, library: ContentLibrary, seed: int, tiers: tuple[int, ...], *, rule_change: bool
) -> list[dict[str, Any]]:
    """規則改變（``rule_change``，常駐類：花 1 AP 與源力啟動）或改寫規則型原語的傳說候選。"""
    theme = rng.choice(_ELEMENTS)
    scaling = _attr(rng, library)
    activation_ap = library.ruleset.core.legendary_activation_ap
    if rule_change:
        rules = sorted(r.id for r in library.ruleset.rule_changes.rule_changes)
        effect: dict[str, Any] = {
            "type": "rule_change",
            "rule": rng.choice(rules),
            "affects": "self",
        }
        shape: dict[str, Any] = {"type": "self"}
    else:
        effect, shape = _rewrite_effect(rng, rng.choice(_REWRITE))
    out: list[dict[str, Any]] = []
    for tier in tiers:
        for source in (1, 2):
            for mana in (0, 4, 8, 12):
                for cooldown in (None,) if rule_change else (2, 3, 4, 5, 6):
                    cost: dict[str, Any] = {"mana": mana, "source": source}
                    if cooldown is not None:
                        cost["cooldown"] = cooldown
                    base = {
                        "tier": tier,
                        "kind": "active",
                        "skeleton": "aura",
                        "scaling_attr": scaling,
                        "ap_cost": activation_ap,
                        "shape": shape,
                        "effects": [effect],
                        "condition": None,
                        "cost": cost,
                    }
                    for activation in ("timed", "battle") if rule_change else (None,):
                        extra = {**base, **({"activation": activation} if activation else {})}
                        out.append(_data(seed, "傳說", "legendary", theme, extra))
    return out


# ---------------------------------------------------------------------------
# 進入點
# ---------------------------------------------------------------------------

_ATTEMPTS = 20
_CORE_TRIES = 8


def compose_modifier(
    seed: int, library: ContentLibrary, *, tier: int | None = None
) -> SkillDef | None:
    """史詩的修正技能（``kind: modifier``）；做不出合格的回傳 ``None``。"""
    rng = Rng(seed).fork("composer.modifier.build")
    tiers = (tier,) if tier is not None else tuple(sorted(library.ruleset.core.tier_budget))
    for _ in range(_ATTEMPTS):
        candidates = _modifier_candidates(rng, library, seed, tiers=tiers, legendary=False)
        found = _pick(rng, library, candidates)
        if found is not None:
            return found
    return None


def compose_legendary(
    seed: int,
    library: ContentLibrary,
    *,
    tier: int | None = None,
    cores: tuple[str, ...] | None = None,
) -> SkillDef | None:
    """傳說技能：核心三擇一（修正規則、規則改變、改寫規則型原語）＋ 1–2 點源力；做不出合格的
    回傳 ``None``。``cores`` 限制可用的核心（``modifier``、``rule_change``、``rule_rewrite``）。"""
    rng = Rng(seed).fork("composer.legendary.build")
    tiers = (tier,) if tier is not None else tuple(sorted(library.ruleset.core.tier_budget))
    cores = cores or ("modifier", "rule_change", "rule_rewrite")
    start = rng.randint(0, len(cores) - 1)  # 抽到的核心連續失敗 _CORE_TRIES 次才換下一種
    for index in range(len(cores) * _CORE_TRIES):
        core = cores[(start + index // _CORE_TRIES) % len(cores)]
        if core == "modifier":
            candidates = _modifier_candidates(rng, library, seed, tiers=tiers, legendary=True)
        else:
            candidates = _lasting_candidates(
                rng, library, seed, tiers, rule_change=core == "rule_change"
            )
        found = _pick(rng, library, candidates)
        if found is not None:
            return found
    return None
