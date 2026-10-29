"""3 級分歧進化：依用法統計從進化模板挑兩支（Phase 3-26b，``docs/design/06-技能.md`` 6.28；
沒有 LLM）。

純函式、確定性（同樣的技能、統計、持有關鍵字與種子必得同樣的兩支）。roguelite 與之後的大世界共用。

**挑選規則**（模板在 ``content/skill_evolution.yaml``）：

1. **加深**：這招自己的關鍵字（專屬規則；沒有時看全部規則）中，打到的目標身上最常出現的一個（並列取
   推導表順序）。加深模板依統計排序——下列「偏好」成立的模板排前面，其餘依資料檔順序：
   ``intensify``（目標身上已經常帶這個關鍵字）、``reshape``
   （平均目標數 < ``spread_targets_permille``）、
   ``delay``（平均距離 ≥ ``far_distance``）、``on_kill``（用這招擊倒過敵人）。依序套用，
   第一個合格的就是
   加深分支。
2. **橋接**：這招自己 **沒有** 的關鍵字，
依「前後搭配的技能的關鍵字次數 → 打到的目標身上的次數 → 主角其他
   技能持有的招數 → 推導表順序」排序，最多試 ``bridge_keyword_tries`` 個；每個關鍵字先試
   ``graft_uses``（搭配的技能製造它、或目標身上常有它時——利用別人製造的關鍵字）或 ``graft_makes``
   （其他情況），再試另一個。第一個合格、而且進化後的技能（專屬規則）真的帶那個關鍵字的就是橋接分支。
3. 橋接做不出來時，改用下一個合格的加深模板當第二支（``fallback=True``）。兩支都做不出來時回傳空的。

**合格**：套用模板後，骰子與倍率依 **同階預算** 重新調整（沿用隨機組合器的調整器
:func:`trpg.skillgen.composer_tuning.tune`，比例落在組合器的區間內），
再經 :func:`validate_skill` 全部
檢查（預算、骨架、上限、互斥、
稀有度……）沒有違規。原骨架不合格時依模板的 ``skeletons`` 改試。稀有度取
「原本」與「新內容需要」中較高的一個（稀有度不加強度，6.12；需要傳說時不合格）。

名稱用組合式「{前綴}・{原名}」；ID 是 ``<原 ID>_evo_<模板>[_<關鍵字>]``。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal

from pydantic import ValidationError

from trpg.content.keyword_derive import derive_keywords
from trpg.content.library import ContentLibrary
from trpg.content.skill_evolution import EvolutionTemplate
from trpg.content.skills import SkillDef, SkillRarity, rarity_rank
from trpg.shared.rng import Rng
from trpg.skillgen.budget import BudgetError, skill_budget
from trpg.skillgen.composer_parts import Knob, dice_ladder
from trpg.skillgen.composer_tuning import tune
from trpg.skillgen.scaling import fit_scaling
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import effect_count, rarity_requirements, validate_skill
from trpg.skillgen.variant_gen import variant_specs, with_variant

__all__ = [
    "Evolution",
    "EvolutionRequest",
    "bridge_keywords",
    "budget_power",
    "evolution_options",
    "evolution_template",
    "evolved_id",
    "finish_draft",
    "multiplier_ladder",
    "rarity_of",
    "retune",
    "template_drafts",
    "template_prefix",
]

type Branch = Literal["deepen", "bridge", "count"]
_RARITIES: tuple[SkillRarity, ...] = ("common", "rare", "epic", "legendary")
_LEGENDARY = rarity_rank("legendary")
type _Draft = tuple[dict[str, Any], list[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class EvolutionRequest:
    """產生兩支進化的輸入。``held_keywords`` 是主角 **其他** 技能的關鍵字分布（專屬規則，橋接的最後
    依據）；``seed`` 決定調整器的目標比例。"""

    skill: SkillDef
    usage: SkillUsage
    held_keywords: Mapping[str, int]
    seed: int


@dataclass(frozen=True, slots=True)
class Evolution:
    """一支進化：分支、模板、帶的關鍵字（換形狀等不看關鍵字的模板為 ``None``）、進化後的技能。
    ``count`` 是召喚技能獨有的數量型分支（3-33f2）。"""

    branch: Branch
    template: str
    keyword: str | None
    skill: SkillDef
    summary_zh: str
    fallback: bool = False


def evolved_id(skill_id: str, template: str, keyword: str | None) -> str:
    return f"{skill_id}_evo_{template}" + (f"_{keyword}" if keyword else "")


# ---------------------------------------------------------------------------
# 統計 → 關鍵字與模板順序
# ---------------------------------------------------------------------------


def _own_keywords(skill: SkillDef, library: ContentLibrary) -> tuple[str, ...]:
    found = derive_keywords(skill, library.keywords, exclusive_only=True).all()
    return found or derive_keywords(skill, library.keywords).all()


def _deepen_keyword(skill: SkillDef, usage: SkillUsage, library: ContentLibrary) -> str | None:
    own = _own_keywords(skill, library)
    if not own:
        return None
    return min(own, key=lambda k: (-usage.target_keywords.get(k, 0), own.index(k)))


def _deepen_preferred(
    template: EvolutionTemplate, usage: SkillUsage, keyword: str | None, library: ContentLibrary
) -> bool:
    table = library.evolution
    if template.op == "intensify":
        return keyword is not None and usage.target_keywords.get(keyword, 0) > 0
    if template.op == "reshape":
        return usage.avg_targets_permille < table.spread_targets_permille
    if template.op == "delay":
        return usage.avg_distance_permille >= table.far_distance * 1000
    return template.op == "on_kill" and usage.kills > 0


def _bridge_keywords(request: EvolutionRequest, library: ContentLibrary) -> list[str]:
    own = set(derive_keywords(request.skill, library.keywords).all())
    usage = request.usage
    partners = usage.partners()
    order = library.keywords.ids()
    scored = [
        k
        for k in order
        if k not in own
        and k in library.evolution.grafts
        and (partners.get(k, 0) or usage.target_keywords.get(k, 0) or request.held_keywords.get(k))
    ]
    scored.sort(
        key=lambda k: (
            -partners.get(k, 0),
            -usage.target_keywords.get(k, 0),
            -request.held_keywords.get(k, 0),
            order.index(k),
        )
    )
    return scored[: library.evolution.bridge_keyword_tries]


def _bridge_templates(
    templates: tuple[EvolutionTemplate, ...], keyword: str, usage: SkillUsage
) -> list[EvolutionTemplate]:
    exploit_first = bool(usage.partner_makes.get(keyword) or usage.target_keywords.get(keyword))
    first = "graft_uses" if exploit_first else "graft_makes"
    return sorted(templates, key=lambda t: t.op != first)


# ---------------------------------------------------------------------------
# 模板 → 草稿（技能欄位的 dict）
# ---------------------------------------------------------------------------


def _effect_dict(effect: Any) -> dict[str, Any]:
    out: dict[str, Any] = effect.model_dump(mode="json", exclude_none=True)
    return out


def _first_damage(effects: list[dict[str, Any]]) -> int | None:
    return next((i for i, e in enumerate(effects) if e["type"] == "damage"), None)


def _damage_element(skill: SkillDef) -> str | None:
    damage = next((e for e in skill.effects if e.type == "damage"), None)
    return None if damage is None or damage.element is None else damage.element.value


def _base(skill: SkillDef) -> _Draft:
    base = skill.model_dump(mode="json")
    effects = [_effect_dict(e) for e in skill.effects]
    base.pop("effects")
    return base, effects


def _status_default(library: ContentLibrary, effect: dict[str, Any]) -> int | None:
    if effect["type"] == "apply_status":
        status = library.ruleset.statuses.by_id().get(effect.get("status", ""))
        return None if status is None else status.duration
    if effect["type"] == "create_surface":
        surfaces = {s.id.value: s for s in library.ruleset.surfaces.surfaces}
        surface = surfaces.get(effect.get("surface", ""))
        return None if surface is None else surface.duration
    return None


def _same_maker(effect: dict[str, Any], graft: dict[str, Any]) -> bool:
    keys = ("type", "status", "surface")
    return all(effect.get(k) == graft.get(k) for k in keys)


def _intensify(skill: SkillDef, keyword: str | None, library: ContentLibrary) -> list[_Draft]:
    graft = library.evolution.grafts.get(keyword or "")
    if graft is None or graft.makes is None:
        return []
    base, effects = _base(skill)
    makes = _effect_dict(graft.makes)
    same = next((e for e in effects if _same_maker(e, makes)), None)
    if same is None:
        return [(base, [*effects, _with_element(makes, skill)])]
    duration = same.get("duration") or _status_default(library, same)
    if duration is None:
        return []
    same["duration"] = duration + 1
    return [(base, effects)]


def _extend(skill: SkillDef, library: ContentLibrary) -> list[_Draft]:
    """這招的狀態、表面與區域（有持續回合的）各多持續 1 回合；硬控狀態不延長。"""
    base, effects = _base(skill)
    statuses = library.ruleset.statuses.by_id()
    changed = False
    for effect in effects:
        if effect["type"] not in ("apply_status", "create_surface", "zone"):
            continue
        status = statuses.get(effect.get("status", ""))
        if status is not None and status.control_group == "hard":
            continue
        duration = effect.get("duration") or _status_default(library, effect)
        if duration is not None:
            effect["duration"] = duration + 1
            changed = True
    return [(base, effects)] if changed else []


def _reshape(
    skill: SkillDef, template: EvolutionTemplate, usage: SkillUsage, far: int
) -> list[_Draft]:
    if not any(e.type == "damage" for e in skill.effects):
        return []
    reach = "far" if usage.avg_distance_permille >= far * 1000 else "near"
    options = sorted(template.shapes, key=lambda o: o.reach not in (reach, "any"))
    drafts: list[_Draft] = []
    for option in options:
        if option.shape.type == skill.shape.type:
            continue
        base, effects = _base(skill)
        base["shape"] = option.shape.model_dump(mode="json", exclude_none=True)
        drafts.append((base, effects))
    return drafts


def _delay(skill: SkillDef, template: EvolutionTemplate) -> list[_Draft]:
    base, effects = _base(skill)
    index = _first_damage(effects)
    if index is None or skill.category != "spell":
        return []
    damage = effects[index]
    effects[index] = {
        "type": "delayed_damage",
        "dice": damage.get("dice", "1d6"),
        "element": damage.get("element") or _damage_element(skill) or "fire",
        "rounds": template.delay_rounds,
        "radius": template.delay_radius,
    }
    return [(base, effects)]


def _on_kill(skill: SkillDef, template: EvolutionTemplate) -> list[_Draft]:
    base, effects = _base(skill)
    index = _first_damage(effects)
    if index is None or "on_kill" in effects[index]:
        return []
    effects[index]["on_kill"] = [_effect_dict(e) for e in template.on_kill]
    return [(base, effects)]


def _with_element(effect: dict[str, Any], skill: SkillDef) -> dict[str, Any]:
    """嫁接的傷害效果：沒寫元素時沿用這招的傷害元素。"""
    if effect["type"] == "damage" and "element" not in effect:
        element = _damage_element(skill)
        if element is not None:
            return {**effect, "element": element}
    return effect


def _graft(
    skill: SkillDef, keyword: str | None, side: Literal["makes", "uses"], library: ContentLibrary
) -> list[_Draft]:
    graft = library.evolution.grafts.get(keyword or "")
    spec = None if graft is None else getattr(graft, side)
    if spec is None:
        return []
    base, effects = _base(skill)
    return [(base, [*effects, _with_element(_effect_dict(spec), skill)])]


MAX_VARIANT_DRAFTS = 8
"""戰場變奏模板最多試幾個候選（每個都要重新調整強度，太多會很慢）。"""


def _variant(skill: SkillDef, library: ContentLibrary) -> list[_Draft]:
    """戰場變奏（Phase 3-25b）：資料順序中前幾個 schema 合法的候選各是一份草稿。"""
    if skill.kind != "active" or skill.trap is not None or skill.followup is not None:
        return []
    drafts: list[_Draft] = []
    for spec in variant_specs(library, {v.id for v in skill.variants}):
        grown = with_variant(skill.model_copy(update={"rarity": "epic"}), spec)
        if grown is None:
            continue
        base, effects = _base(skill)
        base["variants"] = [*base.get("variants", []), spec]
        drafts.append((base, effects))
        if len(drafts) >= MAX_VARIANT_DRAFTS:
            break
    return drafts


def _drafts(
    template: EvolutionTemplate,
    skill: SkillDef,
    keyword: str | None,
    usage: SkillUsage,
    library: ContentLibrary,
) -> list[_Draft]:
    makers: dict[str, Callable[[], list[_Draft]]] = {
        "intensify": lambda: _intensify(skill, keyword, library),
        "extend": lambda: _extend(skill, library),
        "reshape": lambda: _reshape(skill, template, usage, library.evolution.far_distance),
        "delay": lambda: _delay(skill, template),
        "on_kill": lambda: _on_kill(skill, template),
        "variant": lambda: _variant(skill, library),
        "graft_uses": lambda: _graft(skill, keyword, "uses", library),
        "graft_makes": lambda: _graft(skill, keyword, "makes", library),
    }
    return makers[template.op]()


# ---------------------------------------------------------------------------
# 草稿 → 合格的技能（同階預算）
# ---------------------------------------------------------------------------


_LOW_MULTIPLIER_STEP = 100
_LOW_MULTIPLIER_FLOOR = 300
"""武器倍率階梯往下延伸的間距（‰）：讓原本倍率比組合器階梯低的技能也能調回原本的強度。"""


def _multipliers(library: ContentLibrary) -> tuple[int, ...]:
    ladder = [v for r in library.composer.multipliers for v in range(r.start, r.stop, r.step)]
    low = list(range(_LOW_MULTIPLIER_FLOOR, ladder[0], _LOW_MULTIPLIER_STEP))
    return tuple(sorted({*low, *ladder}))


def _knobs(category: str, effects: list[dict[str, Any]], library: ContentLibrary) -> list[Knob]:
    """強度旋鈕：每個傷害、延遲爆炸、治療、護盾效果的骰子（法術技與有骰子的效果）或武器倍率，以及
    推拉距離（1 到原本的距離）。"""
    dice = dice_ladder(library.composer.dice)
    multipliers = _multipliers(library)
    knobs: list[Knob] = []
    for index, effect in enumerate(effects):
        kind = effect["type"]
        weight = 2 if not knobs else 1
        if kind in ("delayed_damage", "heal", "shield") and "dice" in effect:
            knobs.append(Knob(index, "dice", dice, weight))
        elif kind == "damage":
            if "dice" in effect or (category == "spell" and "multiplier_permille" not in effect):
                knobs.append(Knob(index, "dice", dice, weight))
            else:
                knobs.append(Knob(index, "multiplier_permille", multipliers, weight))
        elif kind in ("push", "pull") and effect.get("distance", 1) > 1:
            knobs.append(Knob(index, "distance", tuple(range(1, effect["distance"] + 1)), 1))
    return knobs


def _rarity(draft: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary) -> str:
    """稀有度：原本與新內容需要的較高者——用到的原語、條件、形狀、骨架與效果個數（需要傳說時回傳
    傳說，呼叫者視為不合格）。"""
    try:
        skill = SkillDef.model_validate({**draft, "effects": effects})
    except ValidationError:
        return str(draft["rarity"])
    need = max((rarity_rank(n.minimum) for n in rarity_requirements(skill, library)), default=0)
    count = effect_count(skill)
    need = max(
        need,
        next(
            (i for i, r in enumerate(_RARITIES) if library.budget.rarity[r].max_effects >= count),
            _LEGENDARY,
        ),
    )
    caps = library.ruleset.core.variant_max_by_rarity
    count = len(draft.get("variants") or ())
    need = max(
        need, next((i for i, r in enumerate(_RARITIES) if caps.get(r, 0) >= count), _LEGENDARY)
    )
    return _RARITIES[max(rarity_rank(str(draft["rarity"])), need)]


def cost_attempts(skill: SkillDef) -> list[dict[str, Any]]:
    """代價的嘗試順序：原本的代價；超出預算時再試冷卻 +1、+2（沒有冷卻的從 2 回合起）——以代價折抵
    換取預算（6.5），不加強度。冷卻不超過 :data:`MAX_EVOLVED_COOLDOWN`。"""
    cost = skill.cost.model_dump(mode="json")
    start = 1 if skill.cost.cooldown is None else skill.cost.cooldown
    longer = [start + n for n in range(1, EXTRA_COOLDOWN_STEPS + 1)]
    return [cost] + [
        {**cost, "cooldown": c} for c in longer if MIN_COOLDOWN <= c <= MAX_EVOLVED_COOLDOWN
    ]


EXTRA_COOLDOWN_STEPS = 2
MIN_COOLDOWN = 2
MAX_EVOLVED_COOLDOWN = 5
"""進化時折抵用的冷卻上限（回合）。"""


def budget_power(skill: SkillDef, library: ContentLibrary) -> Fraction:
    """技能的「預算分數」（Phase 3W-2，閃現的強度下限用）：預算總點數 ÷ AP（被動為觸發）係數。
    不改費用的變化，係數不變，等於直接比總點數；蓄力、輕巧、每回合觸發次數這類改了係數的變化，
    比的是「換算回同一個係數」之後的分數，所以輕巧 AP −1 不會因為係數變小而永遠過不了。"""
    report = skill_budget(skill, library)
    power = report.total / report.ap_coefficient
    if (
        skill.kind == "stance"
    ):  # 姿態的維持費折抵也換算掉：維持費 ±1 搭配效果升降，分數不變（3W-2b）
        power /= Fraction(1000 + report.allowance_permille, 1000)
    return power


def _floor_ratio(
    attempt: dict[str, Any], trial: list[dict[str, Any]], floor: Fraction, library: ContentLibrary
) -> Fraction | None:
    """強度下限換算成預算比例（旋鈕在最弱時的係數與可用預算）；結構不合法時 ``None``。"""
    try:
        report = skill_budget(SkillDef.model_validate({**attempt, "effects": trial}), library)
    except (ValidationError, BudgetError):
        return None
    return floor * report.ap_coefficient / report.usable


def _tuned(
    attempt: dict[str, Any],
    effects: list[dict[str, Any]],
    rng: Rng,
    library: ContentLibrary,
    *,
    floor: Fraction | None = None,
    extra: Sequence[dict[str, Any]] = (),
    extra_knobs: Sequence[Knob] = (),
) -> SkillDef | None:
    """調整強度後通過全部驗證的技能；不合格時 ``None``。

    ``floor``（Phase 3W-2）：調整後的 :func:`budget_power` 至少要有這麼多（閃現的強度下限）。
    ``extra``／``extra_knobs``：``attempt`` 裡其他要調的字典（接續段的效果、修正規則的 change），
    旋鈕的 ``index`` 是它在 ``extra`` 裡的位置。"""
    trial = [dict(e) for e in effects]
    knobs = _knobs(attempt["category"], trial, library)
    knobs += [Knob(len(trial) + k.index, k.field, k.values, k.weight) for k in extra_knobs]
    targets = [*trial, *extra]
    for knob in knobs:
        targets[knob.index][knob.field] = knob.values[0]
    rarity = _rarity(attempt, trial, library)
    if rarity_rank(rarity) >= _LEGENDARY > rarity_rank(attempt["rarity"]):
        return None
    attempt = {**attempt, "rarity": rarity}
    min_ratio = None if floor is None else _floor_ratio(attempt, trial, floor, library)
    if floor is not None and min_ratio is None:
        return None
    try:
        if not tune(rng, library, attempt, trial, knobs, extra=extra, min_ratio=min_ratio):
            return None
        # 縮放屬性收進允許範圍（3H-7；效果變了主題可能跟著變）
        evolved = fit_scaling(SkillDef.model_validate({**attempt, "effects": trial}), library)
        ok = not validate_skill(evolved, library) and (
            floor is None or budget_power(evolved, library) >= floor
        )
    except (ValidationError, BudgetError, ValueError):
        return None
    return evolved if ok else None


def _finish(
    draft: _Draft,
    skill: SkillDef,
    template: EvolutionTemplate,
    rng: Rng,
    library: ContentLibrary,
    *,
    floor: Fraction | None = None,
) -> SkillDef | None:
    """依序試「原骨架 → 模板列出的骨架」×「原代價 → 冷卻 +1」，回傳第一個合格的版本。"""
    base, effects = draft
    for skeleton in dict.fromkeys((skill.skeleton, *template.skeletons)):
        for index, cost in enumerate(cost_attempts(skill)):
            attempt = {**base, "skeleton": skeleton, "cost": cost}
            evolved = _tuned(
                attempt, effects, rng.fork(f"{skeleton}/{index}"), library, floor=floor
            )
            if evolved is not None:
                return evolved
    return None


def _label(
    skill: SkillDef, template: EvolutionTemplate, keyword: str | None, library: ContentLibrary
) -> tuple[str, str]:
    """（組合式名稱，一句話說明）。"""
    graft = library.evolution.grafts.get(keyword or "")
    prefix = template.prefix_zh or (graft.prefix_zh if graft is not None else "進化")
    name = keyword_name(library, keyword)
    return f"{prefix}・{skill.name_zh}", template.summary_zh.replace("{keyword}", name)


def keyword_name(library: ContentLibrary, keyword: str | None) -> str:
    if keyword is None:
        return ""
    return next((k.name_zh for k in library.keywords.keywords if k.id == keyword), keyword)


def _build(
    request: EvolutionRequest,
    template: EvolutionTemplate,
    keyword: str | None,
    library: ContentLibrary,
    accept: Callable[[SkillDef], bool] = lambda _s: True,
) -> SkillDef | None:
    skill = request.skill
    rng = Rng(request.seed).fork(f"{template.id}/{keyword or '-'}")
    name, summary = _label(skill, template, keyword, library)
    for index, (base, effects) in enumerate(
        _drafts(template, skill, keyword, request.usage, library)
    ):
        new_id = evolved_id(skill.id, template.id, keyword)
        concept = f"{skill.narrative.concept}（進化：{summary}）".lstrip("（")
        draft = {
            **base,
            "id": new_id,
            "name_zh": name,
            "narrative": {"concept": concept, "cast_flavor": skill.narrative.cast_flavor},
            "provenance": {"origin": "level_up", "parents": [skill.id]},
        }
        evolved = _finish((draft, effects), skill, template, rng.fork(str(index)), library)
        if evolved is not None and accept(evolved):
            return evolved
    return None


def _deepen_options(
    request: EvolutionRequest, library: ContentLibrary
) -> list[tuple[EvolutionTemplate, str | None]]:
    keyword = _deepen_keyword(request.skill, request.usage, library)
    templates = list(library.evolution.branch("deepen"))
    templates.sort(key=lambda t: not _deepen_preferred(t, request.usage, keyword, library))
    return [(t, keyword if t.op == "intensify" else None) for t in templates]


def evolution_options(library: ContentLibrary, request: EvolutionRequest) -> tuple[Evolution, ...]:
    """兩支進化（加深、橋接；見模組說明）。做不出來的分支省略，所以可能只有 0～1 支。

    召喚技能（有 ``summon`` 效果）改走 :mod:`trpg.skillgen.summon_evolution`：加深、橋接、數量型三支
    （Phase 3-33f2）。"""
    from trpg.skillgen.summon_evolution import (  # noqa: PLC0415
        is_summon_skill,
        summon_evolution_options,
    )

    if is_summon_skill(request.skill):
        return summon_evolution_options(library, request)
    table = library.evolution
    found: list[Evolution] = []
    deepen = _deepen_options(request, library)
    for template, keyword in deepen:
        skill = _build(request, template, keyword, library)
        if skill is not None:
            found.append(_evolution("deepen", template, keyword, skill, library))
            break
    for keyword in _bridge_keywords(request, library):
        for template in _bridge_templates(table.branch("bridge"), keyword, request.usage):

            def carries(skill: SkillDef, k: str = keyword) -> bool:
                derived = derive_keywords(skill, library.keywords, exclusive_only=True)
                return k in derived.all()

            skill = _build(request, template, keyword, library, carries)
            if skill is not None:
                found.append(_evolution("bridge", template, keyword, skill, library))
                return tuple(found)
    used = {e.template for e in found}
    for template, keyword in deepen:
        if template.id in used:
            continue
        skill = _build(request, template, keyword, library)
        if skill is not None:
            found.append(_evolution("deepen", template, keyword, skill, library, fallback=True))
            break
    return tuple(found)


def _evolution(
    branch: Branch,
    template: EvolutionTemplate,
    keyword: str | None,
    skill: SkillDef,
    library: ContentLibrary,
    *,
    fallback: bool = False,
) -> Evolution:
    _name, summary = _label(skill, template, keyword, library)
    return Evolution(branch, template.id, keyword, skill, summary, fallback)


# ---------------------------------------------------------------------------
# 給閃現（Phase 3W-1，:mod:`trpg.skillgen.flash`）共用的入口
# ---------------------------------------------------------------------------


def template_drafts(
    template: EvolutionTemplate,
    skill: SkillDef,
    keyword: str | None,
    usage: SkillUsage,
    library: ContentLibrary,
) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """進化模板套在 ``skill`` 上的草稿（技能欄位、效果字典）；做不出來時為空。"""
    return _drafts(template, skill, keyword, usage, library)


def finish_draft(
    draft: tuple[dict[str, Any], list[dict[str, Any]]],
    skill: SkillDef,
    template: EvolutionTemplate,
    rng: Rng,
    library: ContentLibrary,
    *,
    floor: Fraction | None = None,
) -> SkillDef | None:
    """同 3-26b 的進化：依「原骨架 → 模板骨架」×「原代價 → 冷卻折抵」調整強度並驗證
    （``floor``：閃現的強度下限，見 :func:`budget_power`）。"""
    return _finish(draft, skill, template, rng, library, floor=floor)


def retune(
    attempt: dict[str, Any],
    effects: list[dict[str, Any]],
    rng: Rng,
    library: ContentLibrary,
    *,
    floor: Fraction | None = None,
    extra: Sequence[dict[str, Any]] = (),
    extra_knobs: Sequence[Knob] = (),
) -> SkillDef | None:
    """只用 ``attempt`` 的骨架與代價調整強度並驗證（不折抵）；不合格時 ``None``。``floor``、
    ``extra``、``extra_knobs`` 見 :func:`_tuned`。"""
    return _tuned(attempt, effects, rng, library, floor=floor, extra=extra, extra_knobs=extra_knobs)


def multiplier_ladder(library: ContentLibrary) -> tuple[int, ...]:
    """武器倍率的旋鈕階梯（含往下延伸的低倍率），給閃現新增的傷害效果與接續段用。"""
    return _multipliers(library)


def evolution_template(library: ContentLibrary, template_id: str) -> EvolutionTemplate | None:
    """``template_id`` 的進化模板（閃現的小變化共用它的草稿函式）。"""
    return next((t for t in library.evolution.templates if t.id == template_id), None)


def bridge_keywords(
    library: ContentLibrary,
    skill: SkillDef,
    usage: SkillUsage,
    held_keywords: Mapping[str, int],
) -> list[str]:
    """橋接用的關鍵字（這招沒有的；依前後搭配、目標身上、持有、推導表順序排序，最多
    ``bridge_keyword_tries`` 個）；給閃現的「第二個關鍵字」共用。"""
    return _bridge_keywords(EvolutionRequest(skill, usage, held_keywords, 0), library)


def template_prefix(
    template: EvolutionTemplate, keyword: str | None, library: ContentLibrary
) -> str:
    """組合式名稱的前綴（模板的 ``prefix_zh``，沒有時用關鍵字的前綴）。"""
    graft = library.evolution.grafts.get(keyword or "")
    return template.prefix_zh or (graft.prefix_zh if graft is not None else "進化")


def rarity_of(draft: dict[str, Any], effects: list[dict[str, Any]], library: ContentLibrary) -> str:
    """草稿需要的稀有度（原本與新內容需要的較高者；需要傳說時回傳傳說，呼叫者視為不合格）。"""
    return _rarity(draft, effects, library)
