"""白板定義的驗證（Phase 3W-4／3W-4b，``docs/design/06-技能.md`` 6.34.1、6.34.9）。

白板 ＝ 角色目前階級的預算（70～100%）、一個核心效果、一個關鍵字、簡單形狀、沒有附帶效果；
主動技用預設費用。3W-4b 之後的例外（玩法 PM 定，6.34.1）：

- **潮濕、倒地、撞擊**：利用者可以用「條件傷害」（條件傷害本身算一個核心效果）；製造者允許
  「弱傷害＋製造該關鍵字」；
- **召喚**：1 隻基本召喚物（自帶「召喚物」關鍵字，不算第二個關鍵字）；AP 1、冷卻較長
  （召喚物的點數是固定的，AP 2 湊不到預算）；
- **陷阱**：``place_trap`` 是放置的手段，不算核心效果；
- **姿態**（``kind: stance``）、**修正型被動**（``kind: modifier``，一條修正規則）；
- **位移類**（傳送、互換、推拉）：單一位移的點數追不上預算下限，允許一個小補強；
- **雙屬性縮放**：3 階起。
"""

from __future__ import annotations

from fractions import Fraction

from trpg.content.composer_rules import WhiteboardRules
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.keywords import derive_keywords

__all__ = [
    "SKILL_KINDS",
    "is_whiteboard",
    "whiteboard_keywords_of",
    "whiteboard_problems",
]

SKILL_KINDS = frozenset({"active", "passive", "reaction", "stance", "modifier"})
"""白板技能的 ``kind``：姿態佔主動欄、修正型被動佔被動欄（3W-3 同）。"""
SELF_MOVES = frozenset({"teleport", "swap", "leap"})
"""自身位移或互換（6.34.9 的「位移類」，不含推拉別人）。"""
DISPLACE = frozenset({"teleport", "swap", "leap", "push", "pull"})
"""位移類核心效果；可以帶一個小補強。"""

_MIN_RATIO = Fraction(7, 10)
_MAX_RATIO = Fraction(1)
_SIMPLE_SHAPES = frozenset({"self", "single", "ground_tile", "cross", "square3"})
"""白板允許的形狀：自身、單體、單格、十字與 3×3（小範圍）。"""
_SUMMON = "summon"
_PAIR = 2


def whiteboard_keywords_of(skill: SkillDef, library: ContentLibrary) -> tuple[str, ...]:
    """白板計算的關鍵字：專屬規則推導；召喚技自帶「召喚物」，有召喚物自己的關鍵字時只算後者。"""
    found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    if any(e.type == _SUMMON for e in skill.effects) and len(found) > 1:
        return tuple(k for k in found if k != _SUMMON)
    return found


def whiteboard_problems(
    skill: SkillDef, library: ContentLibrary, tier: int | None = None
) -> list[str]:
    """白板定義的檢查（06 6.34.1）；空串列 ＝ 是白板。逐條列出不符合的地方（繁體中文）。

    - 階級等於 ``tier``（角色目前階級，6.34.9；省略 ＝ 不檢查）；種類是主動、被動、反應、姿態
      或修正型被動；
    - 一個核心效果：沒有附帶效果、條件、變奏、第二段、專精（例外見模組說明）；
    - 最多一個關鍵字（專屬規則推導；沒有關鍵字的是通用池的基礎白板）；
    - 形狀簡單（自身、單體、單格、十字、3×3）；
    - 主動技用預設費用：AP ＝ ``ap_cost``、冷卻不超過範圍上限，沒有每場次數、自身狀態、透支；
    - 預算比例在 70～100%（同階規則）。
    """
    rules = library.composer.whiteboard
    problems: list[str] = []
    if tier is not None and skill.tier != tier:
        problems.append(f"白板必須是 {tier} 階，收到 {skill.tier} 階")
    if skill.kind not in SKILL_KINDS:
        problems.append(f"白板只能是主動、被動、反應、姿態或修正型被動，收到 {skill.kind}")
    keywords = whiteboard_keywords_of(skill, library)
    if len(keywords) > 1:
        problems.append(f"白板最多一個關鍵字，收到 {len(keywords)} 個（{'、'.join(keywords)}）")
    problems += _structure_problems(skill, rules, keywords)
    if skill.shape.type not in _SIMPLE_SHAPES:
        problems.append(f"白板的形狀必須簡單（單體或小範圍），收到 {skill.shape.type}")
    if skill.kind == "active":
        problems += _cost_problems(skill, rules)
    try:
        ratio = skill_budget(skill, library).ratio
    except BudgetError as exc:
        problems.append(f"預算算不出來：{exc}")
    else:
        if not _MIN_RATIO <= ratio <= _MAX_RATIO:
            problems.append(f"預算比例必須在 70%～100%，收到 {float(ratio) * 100:.0f}%")
    return problems


def _core_types(skill: SkillDef) -> list[str]:
    """核心效果的種類（陷阱的 ``place_trap`` 是放置的手段，不算核心）。"""
    return [e.type for e in skill.effects if e.type != "place_trap"]


def _rider_ok(types: list[str], keywords: tuple[str, ...], rules: WhiteboardRules) -> bool:
    """兩個效果的例外：位移類加小補強，或例外關鍵字的「弱核心效果＋製造該關鍵字」（核心是傷害，
    或 3W-2b 的小護盾：潮濕被動「被攻擊後得小護盾並在腳下造水」）。"""
    if len(types) != _PAIR:
        return False
    if types[0] in DISPLACE and types[1] not in DISPLACE:
        return True
    maker = bool(set(keywords) & set(rules.exception_keywords))
    return maker and types[0] in ("damage", "shield") and types[1] != types[0]


def _structure_problems(
    skill: SkillDef, rules: WhiteboardRules, keywords: tuple[str, ...]
) -> list[str]:
    problems: list[str] = []
    nested = len(list(skill.iter_effects(include_followup=True, include_variants=True)))
    types = _core_types(skill)
    if skill.kind == "modifier":
        if len(skill.modifiers) != 1 or skill.effects:
            problems.append("修正型白板只能有 1 條修正規則、沒有效果")
    elif len(skill.effects) != nested or not (len(types) == 1 or _rider_ok(types, keywords, rules)):
        problems.append(f"白板只能有 1 個核心效果（沒有附帶效果），收到 {nested} 個")
    exploit = bool(set(keywords) & set(rules.exception_keywords))
    if skill.condition is not None or (
        not exploit and any(e.condition is not None for e in skill.effects)
    ):
        problems.append("白板不能有條件")
    extras = (
        ("修正規則", bool(skill.modifiers) and skill.kind != "modifier"),
        ("變奏", bool(skill.variants)),
        ("第二段", skill.followup is not None),
        ("陷阱", skill.trap is not None and "place_trap" not in {e.type for e in skill.effects}),
        ("專精", skill.mastery is not None),
    )
    problems += [f"白板不能有{label}" for label, present in extras if present]
    if skill.secondary_scaling_attr is not None and skill.tier < rules.dual_min_tier:
        problems.append(f"雙屬性縮放白板要 {rules.dual_min_tier} 階起，收到 {skill.tier} 階")
    return problems


def _cost_problems(skill: SkillDef, rules: WhiteboardRules) -> list[str]:
    problems: list[str] = []
    cost = skill.cost
    first = skill.effects[0].type if skill.effects else ""
    expected_ap = rules.ap_cost
    max_cooldown = rules.cooldown.max
    if first == _SUMMON:  # 召喚物的點數固定，AP 1、冷卻較長才落在預算內
        expected_ap, max_cooldown = rules.summon_ap_cost, rules.summon_cooldown_max
    elif first in SELF_MOVES or (skill.shape.type == "self" and first == "apply_status"):
        expected_ap = rules.self_ap_cost
    if skill.ap_cost != expected_ap:
        problems.append(f"主動白板的 AP 必須是 {expected_ap}，收到 {skill.ap_cost}")
    if (cost.cooldown or 0) > max_cooldown:
        problems.append(f"主動白板的冷卻最多 {max_cooldown}，收到 {cost.cooldown}")
    for label, present in (
        ("每場次數", cost.uses_per_battle is not None),
        ("自身狀態代價", cost.self_status is not None),
        ("透支", cost.overdraft is not None),
        ("層數需求", cost.stacks is not None),
        ("生命代價", cost.hp_percent is not None),
        ("失手反噬", bool(cost.on_miss)),
    ):
        if present:
            problems.append(f"主動白板用預設費用，不能有{label}")
    return problems


def is_whiteboard(skill: SkillDef, library: ContentLibrary, tier: int | None = None) -> bool:
    """技能符合白板定義（:func:`whiteboard_problems` 為空）。"""
    return not whiteboard_problems(skill, library, tier)
