"""原語參數 → 提議欄位型別：內容庫的可用 ID（:class:`_Refs`）、參數型別、效果模型的欄位分支，
以及稀有度／預算可用的狀態。

自 :mod:`trpg.skillgen.proposal` 拆出（Phase R1d），內容未改。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from typing import Annotated, Any, Literal, Union, get_args

from pydantic import (
    Discriminator,
    Field,
    Tag,
    create_model,
)

from trpg.content.battle import ID_PATTERN
from trpg.content.library import ContentLibrary
from trpg.content.player_pool import player_skills
from trpg.content.skills import (
    AFFECTS_VALUES,
    GRANT_SKILL,
    INSCRIBE,
    SKILL_ID_PATTERN,
    ConditionSpec,
    EffectSpec,
    PrimitiveDef,
    PrimitiveParam,
    ScaleBy,
    SkillDef,
    SkillRarity,
    is_silent_grant,
    rarity_rank,
)
from trpg.shared.types import Element, Surface
from trpg.skillgen.composer_parts import obstacle_candidates
from trpg.skillgen.option_gear import gear_pool
from trpg.skillgen.proposal.models import _alias, _get, _id_choice, _literal, _Proposal, _strip_none
from trpg.skillgen.proposal_numbers import (
    numeric_param_names,
)


@dataclass(frozen=True, slots=True)
class _Refs:
    """參數型別對應的可用 ID（來自內容庫）。"""

    statuses: tuple[str, ...]
    objects: tuple[str, ...]
    """``object`` 型參數（目前只有 ``create_obstacle`` 造牆的 ``object``）可選的物件：和組合器同一份
    :func:`~trpg.skillgen.composer_parts.obstacle_candidates`（NW-3d，玩法 PM 交接 4.1.16；冷卻井、
    油桶選不到）。投擲（``hurl_object``）丟的是場上已有的物件、不經這個列舉。"""
    stacks: tuple[str, ...]
    summons: tuple[str, ...]
    rule_changes: tuple[str, ...]
    summon_traits: tuple[str, ...]
    infusions: tuple[str, ...]
    weapons: tuple[str, ...]
    """玩家手上會出現的武器與副手 ID（``wielding_weapon`` 條件的 ``weapon``；3I-5）。"""
    skills: tuple[str, ...] = ()
    """``grant_skill`` 能給的技能 ID（:func:`grantable_skills`；Phase 4-L10a）。"""

    @classmethod
    def of(cls, library: ContentLibrary) -> _Refs:
        rules = library.ruleset
        return cls(
            statuses=tuple(sorted(s.id for s in rules.statuses.statuses if not s.enemy_only)),
            objects=obstacle_candidates(library),
            stacks=tuple(sorted(rules.stacks.by_id())),
            summons=tuple(sorted(rules.summons.by_id())),
            rule_changes=tuple(sorted(rules.rule_changes.by_id())),
            summon_traits=tuple(sorted(rules.core.summon_traits)),
            infusions=tuple(sorted(rules.core.summon_infusions)),
            weapons=tuple(sorted(gear_id for gear_id, _, _ in gear_pool(library))),
            skills=grantable_skills(library),
        )

    def ids_for(self, param_type: str) -> tuple[str, ...] | None:
        table = {
            "status": self.statuses,
            "object": self.objects,
            "stack": self.stacks,
            "summon": self.summons,
            "rule_change": self.rule_changes,
            "summon_trait": self.summon_traits,
            "infusion": self.infusions,
            "weapon": self.weapons,
            "skill": self.skills,
        }
        return table.get(param_type)


def grantable_skills(library: ContentLibrary) -> tuple[str, ...]:
    """``grant_skill`` 能給的技能 ID（排序；Phase 4-L10a A4）：規則與跨技能檢查
    :func:`~trpg.content.skills.granted_skill_problems` 相同——一般的主動技能、不是傳說、不含改寫
    規則型與規則改變型原語、不是 ``grant_skill`` 技能（「不能給出自己」：提議的 ID 是雜湊，不會撞到
    內容庫的技能）。BS-1 起另有「只含無聲」的修正技能（:func:`is_silent_grant`，例：無聲步）；給它的
    技能要是隱蔽關鍵字的技能，由 ``validate_skill`` 的 ``silent_strike.source`` 擋。"""
    primitives = library.ruleset.primitives.by_id()

    def ok(skill: SkillDef) -> bool:
        if is_silent_grant(skill):
            return True
        if skill.kind != "active" or skill.rarity == "legendary":
            return False
        for effect in skill.effects:
            primitive = primitives.get(effect.type)
            if effect.type == GRANT_SKILL:
                return False
            if primitive is not None and primitive.category in ("rule_rewrite", "rule_change"):
                return False
        return True

    return tuple(s.id for s in player_skills(library).values() if ok(s))


_FIXED_PARAM_TYPES: dict[str, tuple[Any, dict[str, Any]]] = {
    "bool": (bool, {}),
    "element": (Element, {}),
    "surface": (Surface, {}),
    "tag": (str, {"pattern": ID_PATTERN}),
}
"""與內容庫無關的參數型別（數值型別 ``int``、``dice`` 不開放，見 :func:`_is_numeric`）。``skill``
（``grant_skill`` 給的技能）列舉能給的技能（4-L10a；內容庫沒有時退回 ID 格式）。"""


_CONDITION_FIELDS = {**EffectSpec.model_fields, **ConditionSpec.model_fields}
"""條件參數退回欄位型別時查的欄位（條件自己的欄位優先，如 ``form_category``）。"""


COUNT_CHOICES: tuple[int | str, ...] = (1, "all")
"""``count`` 型參數（驅散的增益個數）：1 個或全部。"""


def _param_type(
    name: str, spec: PrimitiveParam, refs: _Refs, fallback: Mapping[str, Any]
) -> tuple[Any, dict[str, Any]]:
    """一個參數的型別與 ``Field`` 限制（格式、可用值）；呼叫端已排除數值型別（``_is_numeric``）。"""
    if spec.type == "scaling":
        return _scaling_model(), {}
    if spec.type == "count":
        return _literal(COUNT_CHOICES), {}
    if spec.type == "bool" and spec.true_only:
        return _literal((True,)), {}  # 只能填 true 的開關（Phase 4-L5c）
    fixed = _FIXED_PARAM_TYPES.get(spec.type)
    if fixed is not None:
        return fixed[0], dict(fixed[1])
    ids = refs.ids_for(spec.type)
    if ids is not None:
        return _id_choice(ids, SKILL_ID_PATTERN if spec.type == "skill" else ID_PATTERN)
    # 其餘型別（which、scale、resource、on_hit、landing、anchor、zone_when、scope、scaling、count）
    # 沿用 EffectSpec 欄位的型別：可用值寫在 schema 的 Literal 或子模型裡。
    return _strip_none(fallback[name].annotation), {}


def _is_numeric(spec: PrimitiveParam) -> bool:
    """數值參數（``int``、``dice``）：提議模型不開放，由預算器補。"""
    return bool(numeric_param_names({"x": spec}))


@cache
def _scaling_model() -> Any:
    """``scaling`` 只留「依什麼縮放」，步進與上限是數值。"""
    return create_model("Scaling", __base__=_Proposal, by=(ScaleBy, ...))


def _field(annotation: Any, limits: Mapping[str, Any], *, required: bool, doc: str) -> Any:
    clean = {k: v for k, v in limits.items() if v is not None}
    if required:
        return (annotation, Field(description=doc or None, **clean))
    return (annotation | None, Field(default=None, description=doc or None, **clean))


def _affects_type(primitive: PrimitiveDef) -> Any:
    if primitive.acts_on == "caster":
        return _literal(("self",))
    forbid = set(primitive.forbid_affects or ())
    return _literal(v for v in AFFECTS_VALUES if v not in forbid)


def _required(spec: PrimitiveParam) -> bool:
    """提議中必填：YAML 的 ``required``，但有 ``required_when`` 的依情況才必填，提議中可省略、
    缺了由 ``rules`` 階段的跨檔案驗證報錯。"""
    return spec.required and spec.required_when is None


def _has_nested(primitive: PrimitiveDef) -> bool:
    return any(p.type == "effects" for p in primitive.params.values())


TOP_ONLY_DAMAGE_PARAMS: tuple[str, ...] = (
    "explode",
    "scaling",
    "lifesteal_permille",
    "flat_bonus",
    "split_heal",
    "spread",
)
"""只能用在技能自己的傷害效果的參數（驗證器 ``_check_variable_damage``）：巢狀位置（``then``、
``on_kill``、區域效果、賭注分支）與失手反噬的模型不提供（Phase 4-L10a A2）。"""


ZONE_AFFECTS: tuple[str, ...] = ("enemies", "allies", "all")
"""持續區域必填的 ``affects``（驗證器 ``_check_zone_effect``）。"""


_ZONE_AFFECTS_DOC = "必填：區域對誰結算（enemies 敵方、allies 友方、all 全部）。"


EXACTLY_ONE_PARAMS: dict[str, tuple[str, ...]] = {INSCRIBE: ("element", "tag")}
"""必須恰好填其中一個的參數（驗證器 ``_check_runes``）：拆成以欄位區分的分支（4-L10a A3）。"""


_SPLIT_HEAL = "split_heal"


def _top_only_params(primitive: PrimitiveDef) -> frozenset[str]:
    return frozenset(n for n in TOP_ONLY_DAMAGE_PARAMS if n in primitive.params)


def _without_none(annotation: Any) -> Any:
    args = get_args(annotation)
    if type(None) not in args:
        return annotation
    return _strip_none(annotation)


def _require(entry: tuple[Any, Any]) -> tuple[Any, Any]:
    annotation, info = entry
    doc = getattr(info, "description", None)
    return (_without_none(annotation), Field(description=doc))


def _split_effect(
    name: str, primitive: PrimitiveDef, fields: dict[str, Any], *, fixed_affects: bool
) -> Any:
    """效果模型；有「恰好填一個」的參數（:data:`EXACTLY_ONE_PARAMS`）或 ``split_heal``（須
    ``affects: all``，驗證器 ``_check_split_heal``）時拆成以欄位區分的分支（具名 union，各支
    ``additionalProperties: false``；標籤含 ``~``，錯誤路徑會略過）。``fixed_affects``：對象已
    固定（只作用在施放者、失手反噬），不拆 ``split_heal``。"""
    one_of = EXACTLY_ONE_PARAMS.get(primitive.id, ())
    branches: list[tuple[str, str, dict[str, Any]]] = []
    if one_of and all(f in fields for f in one_of):
        for keep in one_of:
            sub = {k: v for k, v in fields.items() if k not in one_of}
            sub[keep] = _require(fields[keep])
            branches.append((f"{primitive.id}~{keep}", f"{name}_{keep}", sub))

        def pick(value: Any) -> str:
            found = next((f for f in one_of if _get(value, f) is not None), one_of[0])
            return f"{primitive.id}~{found}"

    elif _SPLIT_HEAL in fields and not fixed_affects and "affects" in fields:
        plain = {k: v for k, v in fields.items() if k != _SPLIT_HEAL}
        heal = {**fields, _SPLIT_HEAL: _require(fields[_SPLIT_HEAL])}
        heal["affects"] = (Literal["all"], Field(description="split_heal 必須搭配 affects: all"))
        branches = [
            (f"{primitive.id}~plain", f"{name}_plain", plain),
            (f"{primitive.id}~{_SPLIT_HEAL}", f"{name}_{_SPLIT_HEAL}", heal),
        ]

        def pick(value: Any) -> str:
            heals = _get(value, _SPLIT_HEAL) is not None
            return f"{primitive.id}~{_SPLIT_HEAL if heals else 'plain'}"

    else:
        return create_model(name, __base__=_Proposal, __doc__=primitive.llm_hint, **fields)
    models = [
        Annotated[
            create_model(model_name, __base__=_Proposal, __doc__=primitive.llm_hint, **sub),
            Tag(tag),
        ]
        for tag, model_name, sub in branches
    ]
    return _alias(name, Annotated[Union[tuple(models)], Discriminator(pick)])  # noqa: UP007


_SELF_AFFECTS_DOC = "這個版型的其他效果只作用在施放者。"


def rarity_statuses(library: ContentLibrary, rarity: SkillRarity) -> tuple[str, ...]:
    """這個稀有度能施加的狀態 ID（排序；規則與驗證器的 ``rarity.status`` 相同）。"""
    rank = rarity_rank(rarity)
    return tuple(
        sorted(
            s.id
            for s in library.ruleset.statuses.statuses
            if rarity_rank(s.min_rarity) <= rank and not s.enemy_only  # 5F-5c
        )
    )


def budget_statuses(library: ContentLibrary) -> tuple[str, ...]:
    """技能能施加的狀態 ID（有 ``budget_points``；規則與預算的 ``budget.unavailable`` 相同，
    Phase 4-L5c；排序）。"""
    return tuple(
        sorted(s.id for s in library.ruleset.statuses.statuses if s.budget_points is not None)
    )
