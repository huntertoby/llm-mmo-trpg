"""工坊的一層巢狀效果（Phase 3-48d，規格第 54 節）。

四種原語帶有子效果列表：消耗狀態的 ``then``、賭注的 ``win``／``lose``、持續區域的 ``effects``、
傷害的擊殺時效果 ``on_kill``。這裡替那些 ``effects`` 型參數補上 ``choices``：子效果可選的類型
與驗證器（``SkillDef`` 的 ``_check_*``）一致，而且**子效果不再帶巢狀欄位**（只開放一層）。

子效果的參數沿用 :func:`~trpg.skillgen.option_params.primitive_param_fields`，只拿掉只屬於技能
自己的傷害效果的欄位（爆骰、縮放、吸血、聖光雙效、擊殺時效果）與再往下巢狀的 ``effects`` 型欄位。
預算與命中規則完全交給引擎與預算器（子效果的點數與期望值倍率都已在 ``budget.py`` 計入）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    CONSUME_THEN_TYPES,
    DAMAGE_MULTIPLIER,
    GAMBLE_BRANCH_TYPES,
    MAX_REFUND_AP,
    ON_KILL_TYPES,
    REFUND_AP,
    REFUND_COOLDOWN,
    SELF_DAMAGE_OF_HIT,
    ZONE_EFFECT_TYPES,
    PrimitiveDef,
)
from trpg.skillgen.option_models import Choice, FieldSpec
from trpg.skillgen.option_params import (
    AFFECTS_TEXT,
    ParamContext,
    primitive_param_fields,
)

__all__ = ["NESTED_PARAMS", "nested_field"]

_TOP_ONLY_PARAMS = frozenset({"explode", "scaling", "lifesteal_permille", "split_heal", "on_kill"})
"""只有技能自己（最上層）的傷害效果可以用的欄位，不放進子效果。"""


@dataclass(frozen=True)
class _Rule:
    types: tuple[str, ...]
    min_count: int
    max_count: int
    own_affects: bool
    """子效果可以自選對象（賭注）；否則對象由外層決定（消耗狀態、區域）或一律是施放者（擊殺時）。"""
    beneficial_only: bool = False


NESTED_PARAMS: dict[tuple[str, str], _Rule] = {
    ("consume_status", "then"): _Rule(CONSUME_THEN_TYPES, 1, 2, own_affects=False),
    ("zone", "effects"): _Rule(ZONE_EFFECT_TYPES, 1, 2, own_affects=False),
    ("gamble", "win"): _Rule(GAMBLE_BRANCH_TYPES, 0, 2, own_affects=True),
    ("gamble", "lose"): _Rule(GAMBLE_BRANCH_TYPES, 0, 2, own_affects=True),
    ("damage", "on_kill"): _Rule(ON_KILL_TYPES, 1, 2, own_affects=False, beneficial_only=True),
}
"""(原語, 參數) 對應子效果規則；類型清單來自 skills.py 的各 *_TYPES 常數。"""

_SPECIAL: dict[str, tuple[str, str, str, str, int, int]] = {
    DAMAGE_MULTIPLIER: (
        "傷害倍率",
        "這一次施放的所有傷害乘上倍率（×2＝加倍）。",
        "damage_multiplier_permille",
        "倍率",
        100,
        10_000,
    ),
    SELF_DAMAGE_OF_HIT: (
        "反噬自傷",
        "你自己也受到這一次造成傷害的一部分（不會致命，HP 至少留 1）。",
        "self_damage_permille_of_hit",
        "反噬比例（%）",
        1,
        1000,
    ),
    REFUND_AP: (
        "返還 AP",
        f"讓你立刻拿回 1～{MAX_REFUND_AP} 點 AP。",
        "amount",
        "返還點數",
        1,
        MAX_REFUND_AP,
    ),
}
"""不是原語、只能出現在巢狀裡的專用效果：``(名稱, 說明, 欄位, 欄位名, 最小, 最大)``。"""


_DISPLAY: dict[str, Literal["multiplier", "percent"]] = {
    DAMAGE_MULTIPLIER: "multiplier",
    SELF_DAMAGE_OF_HIT: "percent",
}
"""玩家看到的數值格式（倍率 ×2、百分比），內部仍存千分比。"""


def _special_choice(effect_type: str) -> Choice:
    name, desc, field, field_zh, low, high = _SPECIAL[effect_type]
    return Choice(
        value=effect_type,
        name_zh=name,
        description_zh=desc,
        params=(
            FieldSpec(
                field=field,
                name_zh=field_zh,
                type="int",
                required=True,
                min=low,
                max=high,
                display=_DISPLAY.get(effect_type),
            ),
        ),
    )


def _affects(primitive: PrimitiveDef) -> FieldSpec:
    allowed = tuple(
        a
        for a in ("enemies", "allies", "all", "self")
        if a not in primitive.forbid_affects and (primitive.acts_on != "caster" or a == "self")
    )
    if primitive.acts_on == "caster":
        default = "self"
    else:
        default = "enemies" if primitive.harmful else "allies"
    return FieldSpec(
        field="affects",
        name_zh="對象",
        description_zh="省略時用原語的預設對象；失敗的反噬可以選「自己」",
        required=default not in allowed,
        type="choice",
        choices=tuple(
            Choice(value=a, name_zh=AFFECTS_TEXT[a][0], description_zh=AFFECTS_TEXT[a][1])
            for a in allowed
        ),
        default=default if default in allowed else None,
    )


def _sub_choice(primitive: PrimitiveDef, ctx: ParamContext, rule: _Rule) -> Choice:
    params = tuple(
        f
        for f in primitive_param_fields(primitive, ctx)
        if f.type != "effects" and f.field not in _TOP_ONLY_PARAMS
    )
    if rule.own_affects:
        params = (_affects(primitive), *params)
    return Choice(
        value=primitive.id,
        name_zh=primitive.name_zh,
        description_zh=primitive.description_zh,
        params=params,
    )


def _refund_cooldown() -> Choice:
    return Choice(
        value=REFUND_COOLDOWN,
        name_zh="重置本技能冷卻",
        description_zh="這個技能的冷卻立刻歸零（技能必須有冷卻）。",
    )


def nested_field(
    owner: PrimitiveDef, field: FieldSpec, ctx: ParamContext, library: ContentLibrary
) -> FieldSpec:
    """``owner`` 原語的 ``effects`` 型參數 ``field`` 補上子效果的選項；不是巢狀欄位時原樣回傳。"""
    rule = NESTED_PARAMS.get((owner.id, field.field))
    if rule is None:
        return field
    sub_ctx = ParamContext(
        library,
        category=ctx.category,
        beneficial_only=rule.beneficial_only or ctx.beneficial_only,
        stance=ctx.stance,
    )
    by_id = library.ruleset.primitives.by_id()
    choices: list[Choice] = []
    for effect_type in rule.types:
        if effect_type == REFUND_COOLDOWN:
            choices.append(_refund_cooldown())
        elif effect_type in _SPECIAL:
            choices.append(_special_choice(effect_type))
        elif effect_type in by_id:
            choices.append(_sub_choice(by_id[effect_type], sub_ctx, rule))
    return field.model_copy(
        update={"choices": tuple(choices), "min_count": rule.min_count, "max_count": rule.max_count}
    )
