"""技能預算用角色階級（Phase 3W-9，``docs/design/06-技能.md`` 6.34.9、6.12；玩法決定 #72）。

**階級屬於角色**：技能本身不再有固定的階級。``SkillDef.tier`` 是「這招目前用哪一階的預算」，玩家的
技能一律等於角色目前的階級（:func:`character_tier`，同一個函式給候選、白板、組合器、閃現出題、LLM
提議、卡片與工坊用）；手寫內容（敵人）的技能照舊用自己寫的階級。

**升階重算**（:func:`retier`）：角色升階的當下（戰鬥之間），每招照新階級的預算重新配數值：

- 結構與閃現的變化保留（骨架、效果種類、條件、觸發都不動；閃現的 +40‰／完整技能的 +120‰
  疊在上面，``budget_bonus_permille`` 原樣保留）。
- 預算分數（:func:`~trpg.skillgen.evolution.budget_power`）不低於升階前（6.34.3 強度下限）。
- **維持原本的比例**（3W-9b）：重配的目標是升階前的預算比例（夾在驗證器的 70～100% 窗內），不重新
  抽 75～95%；玩家看到的是「同一招，數字變大」。
- 有強度旋鈕的（傷害、治療、護盾、延遲爆炸的骰子或武器倍率、推拉距離、修正幅度、接續段傷害）交給
  預算器重調。
- **點數固定的狀態／表面與升降地形放大效果本身**（3W-9b，``skill_budget.yaml`` 的
  ``retier_growth``）：表面與升降地形先換成格數較多的形狀（照角色階級的形狀與地形格數表），狀態與
  表面的持續回合可以放大到 ``stretch`` 的上限（只增不減）；不補傷害。
- 沒有旋鈕的固定強度結構依序試：姿態換到元素姿態階梯上合適的一級、變身姿態的形態幅度（BAL-2c，
  上限 2000‰）、召喚物的最大 HP 加成、費用（冷卻、資源）減輕，取比例最接近目標的；升降地形放大
  到上限仍不到 70% 時才補「落石」（多一個大地傷害效果，強度照預算；與 3W-2b 地形變化模板、位移
  白板的小補強同一種例外）。
- 都做不出來時保留原本的數值（只換階級），由 :func:`retier_report` 標示「不在預算窗內」。

戰鬥中不會變：重算只發生在戰鬥之間（:mod:`trpg.roguelite.progress` 的升級流程）。全部確定性：
調整用的亂數由 ``retier/<技能 ID>/<階級>`` 衍生。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from pydantic import ValidationError

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.content.skills.constants import MAX_AP_COST, MAX_EFFECTS
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob
from trpg.skillgen.evolution import budget_power, effect_strength_knobs, retune
from trpg.skillgen.flash_major import fixed_strength
from trpg.skillgen.flash_ops import Draft, base_draft, tuning_extras
from trpg.skillgen.knobs import has_strength_knobs, param_knobs
from trpg.skillgen.validate import structural_rarity, tier_requirements, validate_skill

__all__ = [
    "RETIER_ATTEMPTS",
    "RetierReport",
    "character_tier",
    "retier",
    "retier_report",
]

RETIER_ATTEMPTS = 3
"""同一份草稿最多試幾次不同的調整亂數。"""
_SUMMON_HP_STEPS = (0, 100, 200, 300, 450, 600, 800, 1000)
_PERMILLE = 1000
_CACHE_LIMIT = 4096
"""內容庫上重配快取（``ContentLibrary.retier_cache``）的上限：滿了就清空。"""


def character_tier(library: ContentLibrary, level: int) -> int:
    """角色等級 ``level`` 的階級（06 6.34.9、07 7.6；原型照 ``roguelite.yaml`` 的
    ``offer_tier_by_level``）。技能預算、候選、白板、閃現出題、LLM 提議都用這一個函式。"""
    return library.roguelite.offer_tier(level)


def _rng(skill: SkillDef, tier: int) -> Rng:
    return Rng(0).fork(f"retier/{skill.id}/{tier}")


@dataclass(frozen=True, slots=True)
class _Job:
    """一次重算的共同參數：``moved`` 換好階級的技能、``tier`` 新階級、``floor`` 強度下限（升階前的
    預算分數；降階為 ``None``）、``target`` 目標比例（升階前的比例，夾在窗內）。"""

    moved: SkillDef
    tier: int
    library: ContentLibrary
    rng: Rng
    floor: Fraction | None
    target: Fraction | None

    @property
    def upgrade(self) -> bool:
        return self.floor is not None


def _stretch_knobs(
    effects: list[dict[str, Any]], category: str, library: ContentLibrary
) -> list[Knob]:
    """升階時的效果參數旋鈕（3W-9b）：``retier_growth.stretch`` 列出的參數（狀態、表面的持續回合）
    放大到上限，而且只增不減（從目前的值起跳）；其餘參數照組合器的階梯。"""
    stretch = library.budget.retier_growth.stretch
    statuses = library.ruleset.statuses.by_id()
    out: list[Knob] = []
    for knob in param_knobs(effects, category, library):
        effect = effects[knob.index]
        cap = stretch.get(str(effect["type"]), {}).get(knob.field)
        status = statuses.get(str(effect.get("status")))
        if cap is None or (status is not None and status.control_group is not None):
            out.append(knob)  # 控制類狀態（移動、心智、硬控）照組合器的上限，不放大
            continue
        current = effect.get(knob.field)
        start = min(knob.values) if current is None else int(current)
        values = tuple(range(start, max(cap, start) + 1))
        out.append(Knob(knob.index, knob.field, values, knob.weight))
    return out


def _knob_candidates(
    job: _Job, moved: SkillDef | None = None, draft: Draft | None = None
) -> Iterator[SkillDef | None]:
    """有強度旋鈕的技能：預算器依新階級重調。先只用預算器原本的旋鈕（傷害、治療、護盾、推拉距離、
    修正幅度、接續段）；離目標太遠時再加上效果參數的旋鈕（狀態、表面的持續回合等；升階時用
    :func:`_stretch_knobs`）。``draft`` 給了就用它（換過形狀或費用的草稿）。"""
    skill = job.moved if moved is None else moved
    base, effects = base_draft(skill) if draft is None else draft
    op = "followup" if skill.followup is not None else ""
    extra, knobs = tuning_extras(op, base, job.library)
    if job.upgrade:
        params = _stretch_knobs(effects, skill.category, job.library)
    else:
        params = param_knobs(effects, skill.category, job.library)
    for more in ((), params) if params else ((),):
        for attempt in range(RETIER_ATTEMPTS):
            done = retune(
                base,
                effects,
                job.rng.fork(f"{base['shape']['type']}/{len(more)}/{attempt}"),
                job.library,
                floor=job.floor,
                extra=extra,
                extra_knobs=knobs,
                effect_knobs=more,
                target_ratio=job.target,
            )
            yield done
            if done is not None:
                break  # 同一組旋鈕換亂數不會更接近目標


def _settle(job: _Job, candidates: Iterable[SkillDef | None]) -> SkillDef | None:
    """候選裡第一個與目標比例相差在 ``target_tolerance_permille`` 內的；都不在範圍內時取最接近的
    （同樣接近取先出現的）。沒有目標時取第一個。"""
    tolerance = Fraction(job.library.budget.retier_growth.target_tolerance_permille, 1000)
    best: SkillDef | None = None
    gap: Fraction | None = None
    for done in candidates:
        if done is None:
            continue
        if job.target is None:
            return done
        distance = abs(_ratio(done, job.library) - job.target)
        if distance <= tolerance:
            return done
        if gap is None or distance < gap:
            best, gap = done, distance
    return best


# ---------------------------------------------------------------------------
# 放大格數（3W-9b：表面與升降地形）
# ---------------------------------------------------------------------------


def _bigger_shapes(moved: SkillDef, library: ContentLibrary) -> list[str]:
    """表面與升降地形可以換的較大形狀（``retier_growth.area_shapes`` 裡排在目前形狀之後的；由大到
    小）。複合技能、陷阱與沒有表面或地形效果的技能不換。"""
    ladder = library.budget.retier_growth.area_shapes
    if (
        moved.shape.type not in ladder
        or moved.kind != "active"
        or moved.followup is not None
        or moved.trap is not None
        or not any(e.type in library.budget.retier_growth.area_effects for e in moved.effects)
    ):
        return []
    return list(reversed(ladder[ladder.index(moved.shape.type) + 1 :]))


def _reshaped(moved: SkillDef, shape_id: str, library: ContentLibrary) -> SkillDef | None:
    """``moved`` 換成形狀 ``shape_id``（射程夾在新形狀的範圍內）；角色階級還不能用時 ``None``。"""
    shape = library.ruleset.shapes.by_id()[shape_id]
    spec: dict[str, Any] = {"type": shape_id}
    reach = moved.shape.range
    limits = shape.params.get("range")
    if limits is not None and isinstance(reach, int):
        spec["range"] = min(max(reach, limits.min), limits.max)
    try:
        trial = moved.model_copy(update={"shape": moved.shape.model_validate(spec)})
    except ValidationError:
        return None
    needs = tier_requirements(trial, library)
    if max((n.minimum for n in needs), default=1) > moved.tier:
        return None
    return trial


def _growth_drafts(skill: SkillDef, library: ContentLibrary) -> Iterator[Draft]:
    """換成較大形狀時試的費用：原本的，再往上加冷卻（``max_extra_cooldown``），最後才加 AP
    （``max_extra_ap``，不超過 3）。"""
    rules = library.budget.retier_growth
    start = skill.cost.cooldown or 0
    ap_cost = skill.ap_cost or 0  # 只有主動技能會換形狀（_bigger_shapes），一定有 AP
    top = min(ap_cost + rules.max_extra_ap, MAX_AP_COST)
    for ap in range(ap_cost, max(top, ap_cost) + 1):
        last = max(start, min(start + rules.max_extra_cooldown, rules.max_cooldown))
        for cooldown in range(start, last + 1):
            base, effects = base_draft(skill)
            base["ap_cost"] = ap or None
            base["cost"] = {**base["cost"], "cooldown": cooldown or None}
            yield base, effects


def _grown_skills(job: _Job) -> Iterator[SkillDef]:
    for shape_id in _bigger_shapes(job.moved, job.library):
        grown = _reshaped(job.moved, shape_id, job.library)
        if grown is not None:
            yield grown


def _terrain(skill: SkillDef, library: ContentLibrary) -> bool:
    terrain = library.budget.retier_growth.terrain_effects
    return any(e.type in terrain for e in skill.effects)


def _area_candidates(job: _Job) -> Iterator[SkillDef | None]:
    """點數固定的表面與升降地形：先換成格數較多的形狀（由大到小試）。表面（或已帶落石的升降地形）
    再用旋鈕調到目標比例；只有地形的沒有旋鈕，在費用的組合裡取比例最接近目標的。"""
    for grown in _grown_skills(job):
        if not has_strength_knobs(grown, job.library) and _terrain(grown, job.library):
            drafts = [*_growth_drafts(grown, job.library), *_cost_drafts(grown)]
            yield _closest(drafts, job)
            continue
        for draft in _growth_drafts(grown, job.library):
            yield from _knob_candidates(job, grown, draft)


# ---------------------------------------------------------------------------
# 固定強度的結構（姿態、召喚、費用）與落石
# ---------------------------------------------------------------------------


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


def _form_variants(moved: SkillDef, library: ContentLibrary) -> list[dict[int, dict[str, Any]]]:
    """變身姿態（BAL-2c）：形態幅度（``enter_form.magnitude_permille``）的每一級，由目前的值由近到遠
    （級距同閃現的 ``rules.form_magnitudes``，上限 2000‰；1000 ＝ 拿掉）。維持費不動。"""
    if moved.form_id is None:
        return []
    current = moved.form_magnitude
    steps = library.flash.rules.form_magnitudes
    order = sorted(steps, key=lambda v: (abs(v - current), v))
    return [{0: {"magnitude_permille": None if v == _PERMILLE else v}} for v in order]


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


def _cost_drafts(moved: SkillDef) -> Iterator[Draft]:
    for cost in _cost_variants(moved):
        base, effects = base_draft(moved)
        base["cost"] = {**base["cost"], **cost}
        yield base, effects


def _strength_drafts(moved: SkillDef, library: ContentLibrary) -> Iterator[Draft]:
    """沒有旋鈕的固定強度結構：（姿態級別、形態幅度或召喚物 HP）×（費用減輕）的每個組合，依序試。"""
    structures = (
        _stance_variants(moved, library)
        or _form_variants(moved, library)
        or _summon_variants(moved)
        or [{}]
    )
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


def _rock_drafts(job: _Job, *, grown: bool) -> Iterator[Draft]:
    """升降地形：「地形＋落石」（多一個大地傷害效果，數值由預算器調；3W-2b 地形變化模板的做法）。
    ``grown``：用放大過格數的形狀（由大到小，費用照 :func:`_growth_drafts`）；否則用原本的形狀。"""
    moved = job.moved
    if not _terrain(moved, job.library) or len(moved.effects) >= MAX_EFFECTS:
        return
    if grown:
        drafts: Iterable[Draft] = (
            d for g in _grown_skills(job) for d in _growth_drafts(g, job.library)
        )
    else:
        drafts = [base_draft(moved)]
    for base, effects in drafts:
        rock: dict[str, Any] = {"type": "damage", "element": "earth"}
        if moved.category == "spell":
            rock["dice"] = "1d4"
        else:
            rock["multiplier_permille"] = 300
        effects.append(rock)
        yield base, effects


def _ratio(skill: SkillDef, library: ContentLibrary) -> Fraction:
    return skill_budget(skill, library).ratio


def _closest(drafts: Iterable[Draft], job: _Job) -> SkillDef | None:
    """草稿裡通過驗證（含預算窗）、分數不低於下限的，取比例最接近目標的（同樣接近取先出現的）；沒有
    目標時取第一個。"""
    best: SkillDef | None = None
    gap: Fraction | None = None
    for base, effects in drafts:
        done = fixed_strength(base, effects, job.library, floor=job.floor)
        if done is None:
            continue
        if job.target is None:
            return done
        distance = abs(_ratio(done, job.library) - job.target)
        if gap is None or distance < gap:
            best, gap = done, distance
    return best


def _best_effort(job: _Job) -> SkillDef | None:
    """調不進窗內時的最後一步：每個強度旋鈕都推到最大（費用不動）；除了「過弱」之外要通過驗證，
    預算分數不低於下限。新階級的預算太大、這個結構追不上時用它（:func:`retier_report` 會標出）。"""
    moved, library = job.moved, job.library
    base, effects = base_draft(moved)
    knobs = [*effect_strength_knobs(moved.category, effects, library)]
    if job.upgrade:
        knobs += _stretch_knobs(effects, moved.category, library)
    else:
        knobs += param_knobs(effects, moved.category, library)
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
    if problems or (job.floor is not None and budget_power(trial, library) < job.floor):
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


def _target(skill: SkillDef, library: ContentLibrary) -> Fraction | None:
    """重配的目標比例（3W-9b）：升階前的預算比例，夾在驗證器的窗內（70～100%）。"""
    try:
        ratio = _ratio(skill, library)
    except BudgetError:
        return None
    rules = library.budget
    low = Fraction(rules.min_ratio_permille, 1000)
    high = Fraction(rules.max_ratio_permille, 1000)
    return min(max(ratio, low), high)


def _rocks(job: _Job, *, grown: bool) -> SkillDef | None:
    for base, effects in _rock_drafts(job, grown=grown):
        done = retune(
            base, effects, job.rng.fork("rocks"), job.library, floor=job.floor,
            target_ratio=job.target,
        )  # fmt: skip
        if done is not None:
            return done
    return None


def _grow(job: _Job) -> SkillDef | None:
    """點數固定的表面與升降地形升階時先放大格數（取最接近目標比例的）；升降地形放大到上限仍不到
    70% 時補落石（放大過的形狀）。升降地形一律放大（已帶落石的也是，格數照角色階級表）；表面只有
    點數固定的才放大（帶傷害的表面技能照預算器調骰子）。"""
    if not job.upgrade:
        return None
    if not _terrain(job.moved, job.library) and has_strength_knobs(job.moved, job.library):
        return None
    done = _settle(job, _area_candidates(job))
    if done is None and _terrain(job.moved, job.library):
        done = _rocks(job, grown=True)
    return done


def _same_shape(job: _Job) -> Iterator[SkillDef | None]:
    """形狀不變的候選：預算器重調 → 固定強度的結構與費用。"""
    yield from _knob_candidates(job)
    yield _closest(_strength_drafts(job.moved, job.library), job)


def _solve(job: _Job) -> SkillDef | None:
    """放大格數 → 形狀不變的候選（取最接近目標比例的，:func:`_settle`）→ 原本的形狀補落石 → 旋鈕
    推到最大。"""
    done = _grow(job)
    if done is None:
        done = _settle(job, _same_shape(job))
    if done is None:
        done = _rocks(job, grown=False)
    return done if done is not None else _best_effort(job)


def _retier(skill: SkillDef, tier: int, library: ContentLibrary) -> SkillDef:
    floor = _floor(skill, tier, library)
    job = _Job(
        moved=skill.model_copy(update={"tier": tier}),
        tier=tier,
        library=library,
        rng=_rng(skill, tier),
        floor=floor,
        target=_target(skill, library),
    )
    done = _solve(job)
    if done is None:
        return job.moved
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
    cache = library.retier_cache
    key = _cache_key(skill, tier)
    cached = cache.get(key)
    if cached is not None:
        return cached
    done = _retier(skill, tier, library)
    if len(cache) >= _CACHE_LIMIT:
        cache.clear()
    cache[key] = done
    return done


def _cache_key(skill: SkillDef, tier: int) -> str:
    """重配快取的鍵（3W-R1）：技能 JSON 的 SHA-256 ＋ 階級（不用內建 ``hash()`` 與 ``id()``）。"""
    digest = hashlib.sha256(skill.model_dump_json().encode("utf-8")).hexdigest()
    return f"{digest}/{tier}"


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
