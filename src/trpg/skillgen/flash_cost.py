"""閃現費用方向「蓄力」「輕巧」一定要真的變（FL-1a；``docs/design/06-技能.md`` 6.34「費用方向」
第 1～4 點，玩法 PM 2026-11-13 定；起因 ``docs/phases/閃現蓄力調查.md``）。

- **蓄力**：至少一項強度欄位 **嚴格變強**（打平不算）。預算重調（:func:`apply_cost`
  的第一段，和以前同一條路）沒有讓任何一項變強時，依序試「傷害 → 狀態強度（治療、護盾、數值型狀態的
  強度）→ 狀態回合」，一次只動一項；狀態回合每次最多 +1、累計最多比原招多 2 回合。全部調不上去時
  不出這個選項。
- **輕巧**：至少一項 **嚴格變弱**、沒有任何一項變強（打平或變強都不行）。預算重調（AP 2 → 1 那一支，
  和以前同一條路）的結果不合格時，依序「傷害 → 狀態強度 → 狀態回合（最少留 1）」一次只降一項，降到
  少付的代價照預算扣回（:func:`cost_power` 不高於閃現前）；再降會跌出合格區間時停在最後一個合格的。
  狀態回合每次最多 −1（FL-1e，跟蓄力每次最多 +1 對稱）：降 1 還沒扣回時改試下一項，後面都扣不回
  時取第一個降 1 合格的。AP 已經是 1（只減冷卻或資源）時直接走這條。沒有東西可以降時不出這個選項。

每一級調多少在 ``skill_budget.yaml`` 的 ``flash_cost``（數值工坊可改）；這裡只放規則。
純函式、確定性（不用亂數）。
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import dice_ladder
from trpg.skillgen.evolution import multiplier_ladder
from trpg.skillgen.flash_major import fixed_strength

__all__ = [
    "CHARGE_DURATION_CAP",
    "CHARGE_DURATION_STEP",
    "COST_OPS",
    "LIGHT_DURATION_STEP",
    "MIN_DURATION",
    "STRENGTH_FIELDS",
    "Accept",
    "accept_for",
    "charge_adjusted",
    "charge_ok",
    "cost_power",
    "light_adjusted",
    "light_ok",
    "origin_durations",
    "strength_moves",
    "strength_table",
]

COST_OPS = frozenset({"charge", "light"})
"""照這個模組的規則出題的小變化 ``op``（主動技的蓄力、輕巧；姿態的維持費 ±1 不在這裡）。"""
CHARGE_DURATION_STEP = 1
"""蓄力每次最多加幾回合（06 6.34 費用方向第 1 點）。"""
CHARGE_DURATION_CAP = 2
"""蓄力累計最多比原招多幾回合（同上）。"""
MIN_DURATION = 1
"""輕巧降回合時最少留幾回合（同上第 2 點）。"""
LIGHT_DURATION_STEP = 1
"""輕巧每次最多減幾回合（同上第 6 點，FL-1e：跟蓄力每次最多 +1 對稱）。"""
_NEUTRAL_MAGNITUDE = 1000

STRENGTH_FIELDS = (
    "dice",
    "flat_bonus",
    "multiplier_permille",
    "duration",
    "magnitude_permille",
    "distance",
    "amount",
    "radius",
    "power_permille",
    "max_hp_permille",
)
"""比「變強／變弱」時看的效果欄位（數字越大越強；骰子比平均）。"""
_HARM = frozenset({"damage", "delayed_damage"})
_HELP = frozenset({"heal", "shield"})
_MAGNITUDE_TYPES = frozenset({"apply_status", "create_surface"})
_BUFF_DURATION_TYPES = frozenset({"grant_skill", "shield", "cheat_death", "redirect_damage"})
"""回合算「狀態回合」的增益原語（06 6.34「費用方向」第 6 點）：FL-1c 的暫時給技能；FL-1d 補定的
護盾、不死、轉移傷害的回合。給 AP、額外反應的 **數量** 不算（一次 +1 跳太大，玩法 PM 定）。"""
_SHIELD_DEFAULT_DURATION = 2
"""護盾省略 ``duration`` 時的回合（``skill_primitives.yaml`` 的 shield：2–3，省略＝2）。"""
_ALLY_ZONE = "allies"
"""只對友方結算的持續區域（例：戰歌）：區域回合算增益的狀態回合（FL-1c），區域裡巢狀的狀態也照直接
施加的狀態算強度與回合（FL-1d）；對敵方或全體的區域不算。"""


# ---------------------------------------------------------------------------
# 強度欄位的比較
# ---------------------------------------------------------------------------


def _dice_mean(value: Any) -> Fraction:
    count, sides = str(value).split("d")
    return Fraction(int(count) * (int(sides) + 1), 2)


def _number(field: str, value: Any) -> Fraction:
    return _dice_mean(value) if field == "dice" else Fraction(int(value))


def _groups(skill: SkillDef) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    yield "effects", [e.model_dump(mode="json", exclude_none=True) for e in skill.effects]
    if skill.followup is not None:
        yield (
            "followup",
            [e.model_dump(mode="json", exclude_none=True) for e in skill.followup.effects],
        )


def _effect_key(group: str, index: int, effect: dict[str, Any], sub: int | None = None) -> str:
    what = effect.get("status") or effect.get("surface") or effect.get("stack") or ""
    where = f"{group}[{index}]" if sub is None else f"{group}[{index}].effects[{sub}]"
    return f"{where}:{effect['type']}:{what}"


def _nested(effect: dict[str, Any]) -> list[dict[str, Any]]:
    """只對友方的區域裡巢狀的效果（FL-1d；其他效果回傳空）。"""
    if effect["type"] != "zone" or effect.get("affects") != _ALLY_ZONE:
        return []
    return list(effect.get("effects") or [])


def _walk(
    effects: list[dict[str, Any]],
) -> Iterator[tuple[int, int | None, dict[str, Any]]]:
    """（第幾個效果, 巢狀第幾個或 ``None``, 效果）：頂層每個效果，以及只對友方的區域裡巢狀的狀態
    （FL-1d：跟直接施加的狀態一樣算強度與回合）。"""
    for index, effect in enumerate(effects):
        yield index, None, effect
        for sub, inner in enumerate(_nested(effect)):
            if inner["type"] == "apply_status":
                yield index, sub, inner


def strength_table(skill: SkillDef) -> dict[str, Fraction]:
    """技能各效果（含接續段、只對友方的區域裡巢狀的狀態）的強度欄位：
    ``<group>[i]:<原語>:<狀態>.<欄位>``（巢狀 ``<group>[i].effects[j]:…``）→ 數值。狀態與表面沒寫
    強度時算 1000（中性）；護盾沒寫回合時算 2。"""
    out: dict[str, Fraction] = {}
    for group, effects in _groups(skill):
        for index, sub, effect in _walk(effects):
            key = _effect_key(group, index, effect, sub)
            for field in STRENGTH_FIELDS:
                if effect.get(field) is not None:
                    out[f"{key}.{field}"] = _number(field, effect[field])
                elif field == "magnitude_permille" and effect["type"] in _MAGNITUDE_TYPES:
                    out[f"{key}.{field}"] = Fraction(_NEUTRAL_MAGNITUDE)
                elif field == "duration" and effect["type"] == "shield":
                    out[f"{key}.{field}"] = Fraction(_SHIELD_DEFAULT_DURATION)
    return out


def strength_moves(before: SkillDef, after: SkillDef) -> tuple[bool, bool]:
    """（有沒有任何一項嚴格變強，有沒有任何一項嚴格變弱）。只比兩邊都有的欄位（同一個位置、同一種
    原語與狀態）；結構改變的部分不算。"""
    old, new = strength_table(before), strength_table(after)
    common = sorted(set(old) & set(new))
    return (
        any(new[k] > old[k] for k in common),
        any(new[k] < old[k] for k in common),
    )


def cost_power(skill: SkillDef, library: ContentLibrary) -> Fraction:
    """「扣掉代價」的預算分數：預算總點數 ÷（AP 係數 ×（1000 ＋ 冷卻與資源的折抵）÷ 1000）。輕巧少付
    代價後這個分數不能高於閃現前（＝少付的代價照預算扣回）；閃現的預算上限加成不算在內。"""
    report = skill_budget(skill, library)
    return report.total / (report.ap_coefficient * Fraction(1000 + report.allowance_permille, 1000))


# ---------------------------------------------------------------------------
# 一次動一項的調整
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Step:
    """一個可以調的欄位：``group``（``effects``／``followup``）第 ``index`` 個效果的 ``field``，依序
    試 ``values``（蓄力由弱到強、輕巧由強到弱，都不含目前的值）。"""

    group: str
    index: int
    field: str
    values: tuple[Any, ...]
    repeat: bool = True
    """比例還不在窗內時同一項可以繼續往同一個方向調（回合只調一格，不重複）。"""
    sub: int | None = None
    """區域裡巢狀的第幾個效果（FL-1d）；``None`` ＝ 頂層效果本身。"""


def _targets(
    base: dict[str, Any], effects: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    followup = base.get("followup")
    return {"effects": effects, "followup": followup["effects"] if followup else []}


def _ladder_after(
    ladder: tuple[Any, ...], current: Any, field: str, *, up: bool
) -> tuple[Any, ...]:
    """``ladder`` 中比 ``current`` 強（``up``）或弱的值，依調整方向排序。"""
    now = _number(field, current)
    if up:
        return tuple(v for v in ladder if _number(field, v) > now)
    return tuple(v for v in reversed(ladder) if _number(field, v) < now)


def _status(library: ContentLibrary, effect: dict[str, Any]) -> Any:
    return library.ruleset.statuses.by_id().get(str(effect.get("status")))


def _has_rounds(effect: dict[str, Any]) -> bool:
    """這個效果的回合算不算「狀態回合」：狀態（減益與增益，FL-1a），以及第 6 點的增益——暫時給
    技能（展翼）、只對友方的持續區域（戰歌）（FL-1c）；護盾、不死、轉移傷害（FL-1d）。"""
    kind = effect["type"]
    if kind == "apply_status" or kind in _BUFF_DURATION_TYPES:
        return True
    return kind == "zone" and effect.get("affects") == _ALLY_ZONE


def _duration_now(library: ContentLibrary, effect: dict[str, Any]) -> int | None:
    """目前的回合。護盾沒寫＝2；不死、轉移傷害沒寫（用狀態預設）時不調（``None``）。"""
    if effect.get("duration") is not None:
        return int(effect["duration"])
    kind = effect["type"]
    if kind == "shield":
        return _SHIELD_DEFAULT_DURATION
    if kind != "apply_status":
        return None
    status = _status(library, effect)
    return None if status is None or status.duration is None else int(status.duration)


def _power_steps(
    library: ContentLibrary,
    category: str,
    group: str,
    index: int,
    effect: dict[str, Any],
    *,
    up: bool,
) -> list[_Step]:
    """傷害（``_HARM``）或治療、護盾（``_HELP``）的骰子或武器倍率。"""
    if effect.get("dice") is not None:
        values = _ladder_after(dice_ladder(library.composer.dice), effect["dice"], "dice", up=up)
        return [_Step(group, index, "dice", values)] if values else []
    if effect["type"] in _HARM and (
        effect.get("multiplier_permille") is not None or category == "weapon"
    ):
        current = effect.get("multiplier_permille") or 1000
        values = _ladder_after(multiplier_ladder(library), current, "multiplier_permille", up=up)
        return [_Step(group, index, "multiplier_permille", values)] if values else []
    return []


def _duration_cap(library: ContentLibrary, origin: int | None, now: int) -> int:
    """蓄力的回合上限：原招 +2，不超過組合器的持續上限（原招本來就超過的不再加）。"""
    start = now if origin is None else origin
    return min(start + CHARGE_DURATION_CAP, max(library.composer.duration.cap, start))


def _duration_step(
    library: ContentLibrary,
    group: str,
    index: int,
    effect: dict[str, Any],
    origin: dict[str, int],
    *,
    up: bool,
    sub: int | None = None,
) -> _Step | None:
    if not _has_rounds(effect):
        return None
    now = _duration_now(library, effect)
    if now is None:
        return None
    if not up:
        lower = now - LIGHT_DURATION_STEP
        return (
            _Step(group, index, "duration", (lower,), repeat=False, sub=sub)
            if lower >= MIN_DURATION
            else None
        )
    key = _effect_key(group, index, effect, sub)
    cap = _duration_cap(library, origin.get(key), now)
    return (
        _Step(group, index, "duration", (now + CHARGE_DURATION_STEP,), repeat=False, sub=sub)
        if now + CHARGE_DURATION_STEP <= cap
        else None
    )


def _magnitude_step(
    library: ContentLibrary,
    group: str,
    index: int,
    effect: dict[str, Any],
    *,
    up: bool,
    sub: int | None = None,
) -> _Step | None:
    if effect["type"] != "apply_status":
        return None
    status = _status(library, effect)
    if status is None or not status.scales_with_magnitude:
        return None
    step = library.budget.flash_cost.magnitude_step
    now = int(effect.get("magnitude_permille") or _NEUTRAL_MAGNITUDE)
    if up:
        top = library.budget.retier_growth.magnitude_max
        values = tuple(range(now + step, top + 1, step))
    else:
        values = tuple(range(now - step, _NEUTRAL_MAGNITUDE - 1, -step))
    return _Step(group, index, "magnitude_permille", values, sub=sub) if values else None


def _steps(
    library: ContentLibrary,
    base: dict[str, Any],
    effects: list[dict[str, Any]],
    origin: dict[str, int],
    *,
    up: bool,
) -> list[_Step]:
    """依「傷害 → 狀態強度 → 狀態回合」排好的可調欄位。蓄力時狀態強度只用在回合已經加不上去的
    狀態（同升階 BAL-12e：先加回合、到上限才加強度）。"""
    category = str(base["category"])
    damage: list[_Step] = []
    strength: list[_Step] = []
    durations: list[_Step] = []
    for group, items in _targets(base, effects).items():
        for index, sub, effect in _walk(items):
            kind = effect["type"]
            if sub is None and kind in _HARM:
                damage += _power_steps(library, category, group, index, effect, up=up)
            elif sub is None and kind in _HELP:
                strength += _power_steps(library, category, group, index, effect, up=up)
            duration = _duration_step(library, group, index, effect, origin, up=up, sub=sub)
            if duration is not None:
                durations.append(duration)
            if up and duration is not None:
                continue  # 回合還能加：先加回合，不加強度
            magnitude = _magnitude_step(library, group, index, effect, up=up, sub=sub)
            if magnitude is not None:
                strength.append(magnitude)
    return [*damage, *strength, *durations]


def _with_value(
    base: dict[str, Any], effects: list[dict[str, Any]], step: _Step, value: Any
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trial_base = copy.deepcopy(base)
    trial_effects = copy.deepcopy(effects)
    target = _targets(trial_base, trial_effects)[step.group][step.index]
    if step.sub is not None:
        target = target["effects"][step.sub]
    if step.field == "magnitude_permille" and value == _NEUTRAL_MAGNITUDE:
        target.pop("magnitude_permille", None)
    else:
        target[step.field] = value
    return trial_base, trial_effects


def _ratio(
    base: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary
) -> tuple[Fraction, SkillDef] | None:
    try:
        skill = SkillDef.model_validate({**base, "effects": effects})
        return skill_budget(skill, library).ratio, skill
    except (ValidationError, BudgetError):
        return None


def _window(library: ContentLibrary) -> tuple[Fraction, Fraction]:
    rules = library.budget
    return Fraction(rules.min_ratio_permille, 1000), Fraction(rules.max_ratio_permille, 1000)


def origin_durations(library: ContentLibrary, origin: SkillDef | None) -> dict[str, int]:
    """原招（閃現之前）每個狀態效果的持續回合，鍵同 :func:`strength_table` 的效果部分。"""
    if origin is None:
        return {}
    out: dict[str, int] = {}
    for group, effects in _groups(origin):
        for index, sub, effect in _walk(effects):
            now = _duration_now(library, effect) if _has_rounds(effect) else None
            if now is not None:
                out[_effect_key(group, index, effect, sub)] = now
    return out


def charge_adjusted(
    library: ContentLibrary,
    current: SkillDef,
    draft: tuple[dict[str, Any], list[dict[str, Any]]],
    *,
    floor: Fraction | None,
    origin: SkillDef | None,
) -> SkillDef | None:
    """蓄力的退路：一次只把一項往上調（順序見 :func:`_steps`），比例低於合格區間時同一項再往上；
    第一個通過驗證、不低於強度下限、而且真的有一項變強的版本。都不行時 ``None``（不出蓄力）。"""
    base, effects = draft
    low, high = _window(library)
    rungs = library.budget.flash_cost.damage_rungs
    origin_map = origin_durations(library, origin if origin is not None else current)
    for step in _steps(library, base, effects, origin_map, up=True):
        start = (
            min(rungs, len(step.values)) - 1 if step.field in ("dice", "multiplier_permille") else 0
        )
        values = step.values[start:] if step.repeat else step.values[:1]
        for value in values:
            trial = _with_value(base, effects, step, value)
            measured = _ratio(*trial, library)
            if measured is None or measured[0] > high:
                break
            if measured[0] < low:
                continue
            done = fixed_strength(*trial, library, floor=floor)
            if done is not None and strength_moves(current, done)[0]:
                return done
            break
    return None


def light_adjusted(
    library: ContentLibrary,
    current: SkillDef,
    draft: tuple[dict[str, Any], list[dict[str, Any]]],
    *,
    replaced: Fraction | None,
) -> SkillDef | None:
    """輕巧的退路：一次只把一項往下調（順序見 :func:`_steps`），每一格都檢查驗證與合格區間；
    一直降到「扣掉代價」的分數不高於閃現前（:func:`cost_power`，少付的代價照預算扣回）為止。再降
    就跌出合格區間時，取最後一個合格的（扣到合格區間允許的最多）。狀態回合只降 1（FL-1e）：降 1
    合格但還沒扣回時先記著、改試下一項，後面都沒有扣回的才用第一個記著的。重閃時另外不低於被
    換掉那一筆（``replaced``）。結果一定沒有任何一項變強、至少一項變弱；都不行時 ``None``
    （不出輕巧）。"""
    base, effects = draft
    try:
        ceiling = cost_power(current, library)
    except BudgetError:
        return None
    low, high = _window(library)
    pending: SkillDef | None = None
    for step in _steps(library, base, effects, {}, up=False):
        found: SkillDef | None = None
        paid_back = False
        for value in step.values:
            trial = _with_value(base, effects, step, value)
            measured = _ratio(*trial, library)
            if measured is None or measured[0] < low:
                break
            if measured[0] > high:
                continue
            done = fixed_strength(*trial, library, floor=replaced)
            if done is None or not light_ok(current, done):
                break
            found = done
            if cost_power(done, library) <= ceiling:
                paid_back = True
                break
        if found is None:
            continue
        if paid_back or step.field != "duration":
            return found
        if pending is None:
            pending = found  # 回合降 1 還沒扣回：先記著，改試下一項
    return pending


def light_ok(current: SkillDef, done: SkillDef) -> bool:
    """輕巧的結果合格：沒有任何一項變強、至少一項變弱（少付多少由預算器的合格區間與
    :func:`light_adjusted` 決定）。"""
    up, down = strength_moves(current, done)
    return down and not up


def charge_ok(current: SkillDef, done: SkillDef) -> bool:
    """蓄力的結果合格：至少一項嚴格變強（可以同時有別項變弱，例如重新分配到接續段）。"""
    return strength_moves(current, done)[0]


type Accept = Callable[[SkillDef], bool]
"""預算重調結果的額外檢查（:func:`trpg.skillgen.flash_derive.apply_variation` 用）。"""


def accept_for(op: str, current: SkillDef) -> Accept:
    """``op``（蓄力／輕巧）的預算重調結果要通過的檢查。"""
    if op == "charge":
        return lambda done: charge_ok(current, done)
    return lambda done: light_ok(current, done)
