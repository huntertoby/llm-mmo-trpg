"""技能預算用角色階級（Phase 3W-9，``docs/design/06-技能.md`` 6.34.9、6.12；玩法決定 #72）。

**階級屬於角色**：技能本身不再有固定的階級。``SkillDef.tier`` 是「這招目前用哪一階的預算」，玩家的
技能一律等於角色目前的階級（:func:`character_tier`，同一個函式給候選、白板、組合器、閃現出題、LLM
提議、卡片與工坊用）；手寫內容（敵人）的技能照舊用自己寫的階級。

**升階重算**（:func:`retier`）：角色升階的當下（戰鬥之間），每招照新階級的預算重新配數值：

- 結構與閃現的變化保留（骨架、形狀、效果種類、條件、觸發都不動；閃現的 +40‰／完整技能的 +120‰
  疊在上面，``budget_bonus_permille`` 原樣保留）。
- 預算分數（:func:`~trpg.skillgen.evolution.budget_power`）不低於升階前（6.34.3 強度下限）。
- 有強度旋鈕的（傷害、治療、護盾、延遲爆炸的骰子或武器倍率、推拉距離、狀態持續、修正幅度、接續段
  傷害）交給預算器重調（組合器的 75～95% 目標）。
- 沒有旋鈕的固定強度結構依序試：姿態換到元素姿態階梯上合適的一級、召喚物的最大 HP 加成、費用
  （冷卻、資源）減輕；升降地形最後再試「地形＋落石」（多一個大地傷害效果，強度照預算；與 3W-2b
  地形變化模板同一個做法）。
- 都做不出來時保留原本的數值（只換階級），由 :func:`retier_report` 標示「不在預算窗內」。

戰鬥中不會變：重算只發生在戰鬥之間（:mod:`trpg.roguelite.progress` 的升級流程）。全部確定性：
調整用的亂數由 ``retier/<技能 ID>/<階級>`` 衍生。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob, effect_knobs
from trpg.skillgen.evolution import budget_power, effect_strength_knobs, retune
from trpg.skillgen.flash_major import fixed_strength
from trpg.skillgen.flash_ops import Draft, base_draft, tuning_extras
from trpg.skillgen.validate import structural_rarity, validate_skill

__all__ = [
    "RETIER_ATTEMPTS",
    "RetierReport",
    "character_tier",
    "retier",
    "retier_report",
]

RETIER_ATTEMPTS = 3
"""同一份草稿最多試幾次不同的調整亂數。"""
_PUSH_PULL = frozenset({"push", "pull"})
_SUMMON_HP_STEPS = (0, 100, 200, 300, 450, 600, 800, 1000)
_TERRAIN = frozenset({"raise_terrain", "lower_terrain"})
_MAX_EFFECTS = 4
_CACHE: dict[tuple[int, str, int], SkillDef] = {}
_CACHE_LIMIT = 4096


def character_tier(library: ContentLibrary, level: int) -> int:
    """角色等級 ``level`` 的階級（06 6.34.9、07 7.6；原型照 ``roguelite.yaml`` 的
    ``offer_tier_by_level``）。技能預算、候選、白板、閃現出題、LLM 提議都用這一個函式。"""
    return library.roguelite.offer_tier(level)


def _rng(skill: SkillDef, tier: int) -> Rng:
    return Rng(0).fork(f"retier/{skill.id}/{tier}")


_TUNED_FIELDS = frozenset({"dice", "multiplier_permille"})
"""預算器本來就會調的效果欄位（:func:`~trpg.skillgen.evolution.retune` 的旋鈕）。"""


def _param_knobs(
    effects: list[dict[str, Any]], category: str, library: ContentLibrary
) -> list[Knob]:
    """效果參數上的其他強度旋鈕（``skill_primitives.yaml`` 的 ``knob``，組合器同源）：狀態與表面的
    持續回合、累積層數……；預算器本來就會調的骰子、倍率與推拉距離除外。"""
    knobs: list[Knob] = []
    for index, effect in enumerate(effects):
        for name, values, weight in effect_knobs(library, effect, category=category, weight=1):
            if name in _TUNED_FIELDS or (name == "distance" and effect["type"] in _PUSH_PULL):
                continue
            knobs.append(Knob(index, name, tuple(values), weight))
    return knobs


def _knob_retune(
    moved: SkillDef, library: ContentLibrary, rng: Rng, floor: Fraction | None
) -> SkillDef | None:
    """有強度旋鈕的技能：預算器依新階級重調。先只用預算器原本的旋鈕（傷害、治療、護盾、推拉距離、
    修正幅度、接續段）；調不進窗內時再加上效果參數的旋鈕（狀態、表面的持續回合等）。"""
    base, effects = base_draft(moved)
    op = "followup" if moved.followup is not None else ""
    extra, knobs = tuning_extras(op, base, library)
    params = _param_knobs(effects, moved.category, library)
    for more in ((), params) if params else ((),):
        for attempt in range(RETIER_ATTEMPTS):
            done = retune(
                base,
                effects,
                rng.fork(f"{len(more)}/{attempt}"),
                library,
                floor=floor,
                extra=extra,
                extra_knobs=knobs,
                effect_knobs=more,
            )
            if done is not None:
                return done
    return None


def _stance_variants(moved: SkillDef, library: ContentLibrary) -> list[dict[int, dict[str, Any]]]:
    """元素姿態：同一條階梯上的每一級（由近到遠；維持費不變）。"""
    if moved.kind != "stance" or moved.form_id is not None or len(moved.effects) != 1:
        return []
    status = moved.effects[0].status
    rung = None if status is None else library.flash.stance_rung(status)
    if rung is None:
        return []
    ladder, index = rung
    order = sorted(range(len(ladder)), key=lambda i: (abs(i - index), -i))
    return [{0: {"status": ladder[i]}} for i in order]


def _summon_variants(moved: SkillDef) -> list[dict[int, dict[str, Any]]]:
    """召喚：召喚物的最大 HP 加成（‰）由小到大（0 ＝ 拿掉加成）。"""
    index = next((i for i, e in enumerate(moved.effects) if e.type == "summon"), None)
    if index is None:
        return []
    return [{index: {"max_hp_permille": step or None}} for step in _SUMMON_HP_STEPS]


def _cost_variants(moved: SkillDef) -> list[dict[str, Any]]:
    """費用：原本的、再把冷卻與資源（法力、耐力）往下減輕（代價折抵變小，預算比例變高）。"""
    cost = moved.cost
    cooldowns: list[int | None] = [cost.cooldown]
    if cost.cooldown:
        cooldowns += [c or None for c in range(cost.cooldown - 1, -1, -1)]
    out: list[dict[str, Any]] = []
    for cooldown in cooldowns:
        for scale in (1000, 500, 0):
            changed: dict[str, Any] = {"cooldown": cooldown}
            for field in ("mana", "stamina"):
                value = getattr(cost, field)
                if value:
                    changed[field] = value * scale // 1000
            if changed not in out:
                out.append(changed)
    return out


def _strength_drafts(moved: SkillDef, library: ContentLibrary) -> Iterator[Draft]:
    """沒有旋鈕的固定強度結構：（姿態級別或召喚物 HP）×（費用減輕）的每個組合，依序試。"""
    structures = _stance_variants(moved, library) or _summon_variants(moved) or [{}]
    for structure in structures:
        for cost in _cost_variants(moved):
            base, effects = base_draft(moved)
            for index, fields in structure.items():
                for name, value in fields.items():
                    if value is None:
                        effects[index].pop(name, None)
                    else:
                        effects[index][name] = value
            base["cost"] = {**base["cost"], **cost}
            yield base, effects


def _rock_drafts(moved: SkillDef) -> Iterator[Draft]:
    """升降地形：「地形＋落石」（多一個大地傷害效果，數值由預算器調；3W-2b 地形變化模板的做法）。"""
    if not any(e.type in _TERRAIN for e in moved.effects) or len(moved.effects) >= _MAX_EFFECTS:
        return
    base, effects = base_draft(moved)
    rock: dict[str, Any] = {"type": "damage", "element": "earth"}
    if moved.category == "spell":
        rock["dice"] = "1d4"
    else:
        rock["multiplier_permille"] = 300
    effects.append(rock)
    yield base, effects


def _fixed(
    drafts: Iterator[Draft], library: ContentLibrary, floor: Fraction | None
) -> SkillDef | None:
    for base, effects in drafts:
        done = fixed_strength(base, effects, library, floor=floor)
        if done is not None:
            return done
    return None


def _best_effort(
    moved: SkillDef, library: ContentLibrary, floor: Fraction | None
) -> SkillDef | None:
    """調不進窗內時的最後一步：每個強度旋鈕都推到最大（費用不動）；除了「過弱」之外要通過驗證，
    預算分數不低於下限。新階級的預算太大、這個結構追不上時用它（:func:`retier_report` 會標出）。"""
    base, effects = base_draft(moved)
    knobs = [*effect_strength_knobs(moved.category, effects, library)]
    knobs += _param_knobs(effects, moved.category, library)
    if not knobs:
        return None
    for knob in knobs:
        effects[knob.index][knob.field] = knob.values[-1]
    try:
        trial = SkillDef.model_validate({**base, "effects": effects})
        trial = trial.model_copy(update={"rarity": structural_rarity(trial, library)})
    except (ValidationError, ValueError):
        return None
    problems = [v for v in validate_skill(trial, library) if not v.rule.endswith("budget.weak")]
    if problems or (floor is not None and budget_power(trial, library) < floor):
        return None
    return trial


def _floor(skill: SkillDef, tier: int, library: ContentLibrary) -> Fraction | None:
    """升階時的強度下限（升階前的預算分數）；降階（手寫池的高階技能給低階角色）沒有下限。"""
    if tier < skill.tier:
        return None
    try:
        return budget_power(skill, library)
    except BudgetError:
        return None


def _retier(skill: SkillDef, tier: int, library: ContentLibrary) -> SkillDef:
    moved = skill.model_copy(update={"tier": tier})
    floor = _floor(skill, tier, library)
    rng = _rng(skill, tier)
    done = _knob_retune(moved, library, rng, floor)
    if done is None:
        done = _fixed(_strength_drafts(moved, library), library, floor)
    if done is None:
        for base, effects in _rock_drafts(moved):
            done = retune(base, effects, rng.fork("rocks"), library, floor=floor)
    if done is None:
        done = _best_effort(moved, library, floor)
    if done is None:
        return moved
    # ID、名稱、來源、閃現加成都沿用原本的（重算只改數值）
    return done.model_copy(
        update={
            "id": skill.id,
            "name_zh": skill.name_zh,
            "provenance": skill.provenance,
            "budget_bonus_permille": skill.budget_bonus_permille,
            "narrative": skill.narrative,
        }
    )


def retier(library: ContentLibrary, skill: SkillDef, tier: int) -> SkillDef:
    """``skill`` 照角色階級 ``tier`` 的預算重新配數值（見模組說明）；階級相同時原樣回傳。"""
    if tier == skill.tier:
        return skill
    if tier not in library.ruleset.core.tier_budget:
        raise ValueError(f"沒有階級 {tier} 的預算（tier_budget）")
    key = (id(library), skill.model_dump_json(), tier)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    done = _retier(skill, tier, library)
    if len(_CACHE) >= _CACHE_LIMIT:
        _CACHE.clear()
    _CACHE[key] = done
    return done


@dataclass(frozen=True, slots=True)
class RetierReport:
    """一招重算的結果：``before``／``after`` 預算分數、``ratio`` 新階級的預算比例、``in_window``
    比例是否在驗證器的窗內（0.70～1.00）、``problems`` 驗證器的其他違規。"""

    skill_id: str
    before: Fraction
    after: Fraction
    ratio: Fraction
    in_window: bool
    problems: tuple[str, ...]


def retier_report(library: ContentLibrary, before: SkillDef, after: SkillDef) -> RetierReport:
    """重算前後的比較（測試與報表用）。"""
    report = skill_budget(after, library)
    rules = library.budget
    ratio = report.ratio
    low = Fraction(rules.min_ratio_permille, 1000)
    high = Fraction(rules.max_ratio_permille, 1000)
    return RetierReport(
        skill_id=after.id,
        before=budget_power(before, library),
        after=budget_power(after, library),
        ratio=ratio,
        in_window=low <= ratio <= high,
        problems=tuple(v.rule for v in validate_skill(after, library)),
    )
