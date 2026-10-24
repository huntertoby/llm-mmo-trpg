"""技能工坊的參數欄位（Phase 3F-1）：把資料檔的定義（``skill_primitives.yaml`` 的 ``params``、
``skill_shapes.yaml`` 的 ``params``、``skill_conditions.yaml`` 的 ``params``）與 schema 的範圍轉成
:class:`~trpg.skillgen.option_models.FieldSpec`。

規則一律來自資料檔與 schema，這裡只負責轉換格式與中文標示；可選值（狀態、表面、物件……）來自
內容庫。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic.fields import FieldInfo

from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    SCALE_BY_VALUES,
    WIELDING_EFFECT_ONLY,
    WIELDING_WEAPON,
    ConditionDef,
    PrimitiveDef,
    PrimitiveParam,
    ScaleSpec,
    ShapeDef,
)
from trpg.shared.types import Surface
from trpg.skillgen.option_gear import gear_choices
from trpg.skillgen.option_models import Choice, FieldSpec, FieldType

__all__ = [
    "AFFECTS_TEXT",
    "PARAM_TEXT",
    "ParamContext",
    "condition_choice",
    "condition_param_fields",
    "dice_field",
    "model_range",
    "primitive_param_fields",
    "shape_param_fields",
]

AFFECTS_TEXT: dict[str, tuple[str, str]] = {
    "enemies": ("敵方", "影響範圍內的敵方單位"),
    "allies": ("友方", "影響範圍內的友方單位（含自己，依形狀而定）"),
    "all": ("敵我不分", "影響範圍內的所有單位"),
    "self": ("自己", "只作用在施放者自己"),
    "tiles": ("格子", "作用在影響範圍內的格子"),
}

_SHAPE_PARAM_TEXT: dict[str, tuple[str, str]] = {
    "range": ("射程", "可以選多遠的目標（格；曼哈頓距離）"),
    "size": ("大小", "直線的長度或錐形的深度（格）"),
    "radius": ("半徑", "以中心算起的半徑（格）"),
    "jumps": ("跳躍次數", "連鎖再跳到幾個目標"),
    "jump_range": ("跳躍距離", "每一跳的最遠距離（格）"),
}

PARAM_TEXT: dict[str, str] = {
    "weapon": "武器",
    "amount": "數量",
    "anchor": "區域錨點",
    "chance_permille": "成功率（‰）",
    "collision_dice": "撞擊傷害骰",
    "count": "個數",
    "dice": "骰子",
    "distance": "距離（格）",
    "duration": "持續回合",
    "effects": "區域效果",
    "element": "元素",
    "explode": "爆骰",
    "hp_permille": "復活 HP（‰）",
    "infusion": "第二個灌注關鍵字",
    "knock_prone": "另外擊倒",
    "landing": "落點",
    "lifesteal_permille": "吸血（‰）",
    "lose": "失敗時的效果",
    "max_hp_permille": "召喚物最大 HP 加成（‰）",
    "multiplier_permille": "武器倍率（‰）",
    "object": "物件",
    "on_hit": "撞到時",
    "on_kill": "擊殺時效果",
    "per_stack_permille": "每層加成（‰）",
    "permille": "千分比（‰）",
    "power_permille": "每隻召喚物的強度（‰）",
    "radius": "半徑（格）",
    "range": "距離（格）",
    "resource": "資源",
    "rounds": "倒數輪數",
    "rule": "規則改變",
    "scale": "倍率依據",
    "scope": "引爆範圍",
    "scaling": "依情況縮放",
    "skill": "技能",
    "speed": "速度（格）",
    "splash": "濺射距離",
    "split_heal": "聖光雙效",
    "stack": "層數",
    "status": "狀態",
    "surface": "表面",
    "tag": "標籤",
    "then": "消耗後的效果",
    "trait": "召喚物小特性",
    "unit": "召喚物",
    "when": "結算時機",
    "which": "哪些技能",
    "win": "成功時的效果",
}
"""原語與條件參數的中文名稱（顯示用；參數的定義與範圍在資料檔）。"""

_LITERAL_CHOICES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "which": (
        ("all", "全部技能", "重置所有技能的冷卻"),
        ("tag", "指定標籤", "只重置帶某個標籤的技能（另填 tag）"),
    ),
    "resource": (
        ("mana", "法力", "回復 amount 點法力"),
        ("cooldown", "冷卻", "所有技能的冷卻 −amount 回合（最多 2）"),
    ),
    "on_hit": (
        ("knock_prone", "擊倒", "被撞到的敵人對抗判定失敗就倒地"),
        ("push_aside", "推到路旁", "被撞到的敵人被推到路徑旁一格"),
    ),
    "landing": (
        ("choose", "自選落點", "形狀 unit_then_tile：先選敵人，再選他相鄰的空格"),
        ("behind", "背後", "形狀 single：固定落在目標背後"),
    ),
    "scale": (
        ("remaining_rounds", "剩餘回合", "倍率＝被消耗狀態的剩餘回合"),
        ("stacks", "層數", "倍率＝同時消耗目標身上的層數（另填 stack）"),
    ),
    "scope": (("target_cell", "目標那 1 格", "只引爆被命中目標所在格上自己的符文"),),
    "anchor": (
        ("tile", "固定在格子", "區域固定在施放時的格子"),
        ("caster", "跟隨施放者", "區域跟著施放者移動"),
        ("moving", "移動", "每次環境回合沿施放方向前進 speed 格"),
    ),
    "zone_when": (
        ("enter", "進入時", "單位進入區域時結算"),
        ("turn_start", "回合開始時", "回合開始時站在區域內就結算"),
        ("both", "兩者", "進入時與回合開始時都結算"),
    ),
}

_SCALE_BY_TEXT: dict[str, str] = {
    "missing_hp_10pct": "施放者每少 10% 最大 HP",
    "distance": "與目標每距 1 格",
    "enemies_adjacent_target": "目標相鄰的每個敵人",
    "enemies_adjacent_self": "施放者相鄰的每個敵人",
}


def model_range(info: FieldInfo) -> tuple[int | None, int | None]:
    """pydantic 欄位的 ``ge``／``le`` 限制（沒有時為 ``None``）。"""
    low: int | None = None
    high: int | None = None
    for meta in info.metadata:
        ge = getattr(meta, "ge", None)
        le = getattr(meta, "le", None)
        if isinstance(ge, int):
            low = ge
        if isinstance(le, int):
            high = le
    return low, high


def dice_field(
    library: ContentLibrary, name: str, name_zh: str, description_zh: str, *, required: bool
) -> FieldSpec:
    """骰子欄位：顆數 1–組合器上限、面數為組合器的骰子階梯（``skill_composer.yaml`` 的
    ``dice``）。"""
    rules = library.composer.dice
    return FieldSpec(
        field=name,
        name_zh=name_zh,
        description_zh=description_zh,
        type="dice",
        required=required,
        min=1,
        max=rules.max_count,
        dice_sides=tuple(sorted(rules.sides)),
    )


def shape_param_fields(shape: ShapeDef, *, weapon_ok: bool = True) -> tuple[FieldSpec, ...]:
    """形狀的參數（``skill_shapes.yaml`` 的 ``params``：範圍與是否可填「用武器射程」）。
    ``weapon_ok`` 為假（法術技）時不提供「用武器射程」（只有武器技有手上的武器）。"""
    out: list[FieldSpec] = []
    for name, spec in shape.params.items():
        name_zh, desc = _SHAPE_PARAM_TEXT.get(name, (name, ""))
        allow_weapon = spec.allow_weapon and weapon_ok
        if allow_weapon:
            desc += "；也可以勾選「用武器射程」"
        out.append(
            FieldSpec(
                field=name,
                name_zh=name_zh,
                description_zh=desc,
                type="int",
                required=spec.required,
                min=spec.min,
                max=spec.max,
                allow_weapon=allow_weapon,
            )
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# 引用其他資料檔的可選值
# ---------------------------------------------------------------------------


def _status_choices(
    library: ContentLibrary, keep: Callable[[str], bool] | None = None
) -> tuple[Choice, ...]:
    return tuple(
        Choice(
            value=s.id,
            name_zh=s.name_zh,
            description_zh=s.description_zh,
            info={"beneficial": s.beneficial, "stance": s.stance, "min_rarity": s.min_rarity},
        )
        for s in library.ruleset.statuses.statuses
        if keep is None or keep(s.id)
    )


def _surface_choices(library: ContentLibrary, *, beneficial_only: bool) -> tuple[Choice, ...]:
    return tuple(
        Choice(value=s.id.value, name_zh=s.name_zh, info={"beneficial": s.beneficial})
        for s in library.ruleset.surfaces.surfaces
        if s.id is not Surface.NONE and (s.beneficial or not beneficial_only)
    )


def _keyword_name(library: ContentLibrary, keyword: str) -> str:
    return next((k.name_zh for k in library.keywords.keywords if k.id == keyword), keyword)


def _ref_choices(kind: str, library: ContentLibrary) -> tuple[Choice, ...]:
    if kind in _LITERAL_CHOICES:
        return tuple(
            Choice(value=v, name_zh=n, description_zh=d) for v, n, d in _LITERAL_CHOICES[kind]
        )
    rules = library.ruleset
    builders: dict[str, Callable[[], tuple[Choice, ...]]] = {
        "element": lambda: tuple(
            Choice(value=e.id.value, name_zh=e.name_zh, description_zh=e.description_zh)
            for e in library.elements.elements
        ),
        "object": lambda: tuple(
            Choice(value=o.id, name_zh=o.name_zh) for o in rules.objects.objects
        ),
        "stack": lambda: tuple(
            Choice(value=k.id, name_zh=k.name_zh, description_zh=k.description_zh)
            for k in rules.stacks.stacks
        ),
        "summon": lambda: tuple(
            Choice(value=s.id, name_zh=s.template.name_zh) for s in rules.summons.summons
        ),
        "rule_change": lambda: tuple(
            Choice(value=r.id, name_zh=r.name_zh) for r in rules.rule_changes.rule_changes
        ),
        "summon_trait": lambda: tuple(
            Choice(value=i, name_zh=t.name_zh, description_zh=t.description_zh)
            for i, t in sorted(rules.core.summon_traits.items())
        ),
        "infusion": lambda: tuple(
            Choice(value=k, name_zh=_keyword_name(library, k))
            for k in sorted(rules.core.summon_infusions)
        ),
        "skill": lambda: tuple(
            Choice(value=s.id, name_zh=s.name_zh)
            for s in sorted(library.skills.values(), key=lambda s: s.id)
            if s.kind == "active" and s.rarity != "legendary"
        ),
    }
    return builders[kind]()


def tag_choices(library: ContentLibrary, primitive_id: str) -> tuple[Choice, ...]:
    """標籤欄位的選單（中文名）。刻印（``inscribe``）只列有符文單字的標籤，顯示成「獵紋」；
    其他（重置冷卻）列全部技能標籤。"""
    tags = sorted(library.ruleset.skill_tags.tags, key=lambda t: t.id)
    if primitive_id == "inscribe":
        return tuple(
            Choice(value=t.id, name_zh=f"{t.rune_zh}紋") for t in tags if t.rune_zh is not None
        )
    return tuple(Choice(value=t.id, name_zh=t.name_zh) for t in tags)


def _scaling_field(library: ContentLibrary, spec: PrimitiveParam) -> FieldSpec:
    fields = ScaleSpec.model_fields
    step_low, step_high = model_range(fields["per_step_permille"])
    cap_low, _ = model_range(fields["cap_permille"])
    return FieldSpec(
        field="scaling",
        name_zh="依情況縮放",
        description_zh=spec.description_zh,
        type="object",
        fields=(
            FieldSpec(
                field="by",
                name_zh="依據",
                type="choice",
                required=True,
                choices=tuple(Choice(value=v, name_zh=_SCALE_BY_TEXT[v]) for v in SCALE_BY_VALUES),
            ),
            FieldSpec(
                field="per_step_permille",
                name_zh="每一步加成（‰）",
                type="int",
                required=True,
                min=step_low,
                max=step_high,
            ),
            FieldSpec(
                field="cap_permille",
                name_zh="加成上限（‰）",
                type="int",
                required=True,
                min=cap_low,
                max=library.ruleset.core.scale_cap_max_permille,
            ),
        ),
    )


# ---------------------------------------------------------------------------
# 原語參數
# ---------------------------------------------------------------------------


class ParamContext:
    """產生原語參數欄位時的情境：技能類別、核心是否只能有益、姿態技能、原語的參數表。"""

    def __init__(
        self,
        library: ContentLibrary,
        *,
        category: str | None,
        beneficial_only: bool = False,
        stance: bool = False,
    ) -> None:
        self.library = library
        self.category = category
        self.beneficial_only = beneficial_only
        self.stance = stance

    def keep_status(self, status_id: str) -> bool:
        status = self.library.ruleset.statuses.by_id()[status_id]
        if self.beneficial_only and not status.beneficial:
            return False
        if status.budget_points is None:  # 技能不能施加的狀態（沒有預算點數；3H-8）
            return False
        return status.stance == self.stance


def _skip_param(primitive: PrimitiveDef, name: str, category: str | None) -> bool:
    """依技能類別不填的參數：武器技的傷害骰（用武器骰）、法術技的倍率。"""
    if primitive.id != "damage":
        return False
    return (category == "weapon" and name == "dice") or (
        category == "spell" and name == "multiplier_permille"
    )


def _required(
    primitive: PrimitiveDef, name: str, spec: PrimitiveParam, category: str | None
) -> bool:
    if primitive.id == "damage" and name == "element":
        return category == "spell"  # 法術技必填，武器技省略時繼承武器元素
    return spec.required


def _param_field(
    primitive: PrimitiveDef, name: str, spec: PrimitiveParam, ctx: ParamContext
) -> FieldSpec:
    library = ctx.library
    required = _required(primitive, name, spec, ctx.category)
    base: dict[str, Any] = {
        "field": name,
        "name_zh": PARAM_TEXT.get(name, name),
        "description_zh": spec.description_zh,
        "required": required,
        "show_when": spec.show_when or {},
    }
    kind = spec.type
    if kind == "tag":  # 只能選已定義的標籤（3-48c；刻印只列符文標籤，新標籤由內容資料新增）
        return FieldSpec(**base, type="choice", choices=tag_choices(library, primitive.id))
    plain: dict[str, FieldType] = {"bool": "bool", "effects": "effects"}
    if kind in plain:
        return FieldSpec(**base, type=plain[kind])
    if kind in ("int", "count"):
        low = spec.min if kind == "int" else (spec.min or 1)
        return FieldSpec(**base, type="int" if kind == "int" else "count", min=low, max=spec.max)
    if kind == "dice":
        return dice_field(
            library, name, PARAM_TEXT.get(name, name), spec.description_zh, required=required
        )
    if kind == "scaling":
        return _scaling_field(library, spec)
    return FieldSpec(**base, type="choice", choices=_choices_for(kind, primitive, ctx))


def _choices_for(kind: str, primitive: PrimitiveDef, ctx: ParamContext) -> tuple[Choice, ...]:
    if kind == "status":
        keep = ctx.keep_status if primitive.id == "apply_status" else None
        return _status_choices(ctx.library, keep)
    if kind == "surface":
        return _surface_choices(ctx.library, beneficial_only=ctx.beneficial_only)
    return _ref_choices(kind, ctx.library)


def primitive_param_fields(primitive: PrimitiveDef, ctx: ParamContext) -> tuple[FieldSpec, ...]:
    """原語的參數欄位（``skill_primitives.yaml`` 的 ``params``，依資料檔順序）。

    依技能類別省略不適用的參數（武器技的傷害骰、法術技的倍率）；範圍一律取自資料檔。"""
    return tuple(
        _param_field(primitive, name, spec, ctx)
        for name, spec in primitive.params.items()
        if not _skip_param(primitive, name, ctx.category)
    )


# ---------------------------------------------------------------------------
# 條件
# ---------------------------------------------------------------------------


def condition_param_fields(
    condition: ConditionDef, library: ContentLibrary, weapon_req: object = None
) -> tuple[FieldSpec, ...]:
    """條件的參數（``skill_conditions.yaml`` 的 ``params``）。``weapon_req``：技能的武器需求，
    ``weapon`` 型參數用它事前停用大類不符的武器（3I-5）。"""
    out: list[FieldSpec] = []
    for name, spec in condition.params.items():
        base: dict[str, Any] = {
            "field": name,
            "name_zh": PARAM_TEXT.get(name, name),
            "description_zh": spec.description_zh,
            "required": spec.required,
        }
        if spec.type == "int":
            out.append(FieldSpec(**base, type="int", min=spec.min, max=spec.max))
        elif spec.type == "status":
            out.append(FieldSpec(**base, type="choice", choices=_status_choices(library)))
        elif spec.type == "surface":
            choices = _surface_choices(library, beneficial_only=False)
            out.append(FieldSpec(**base, type="choice", choices=choices))
        elif spec.type == "weapon":
            out.append(FieldSpec(**base, type="choice", choices=gear_choices(library, weapon_req)))
        else:
            out.append(FieldSpec(**base, type="text"))
    return tuple(out)


def condition_choice(
    condition: ConditionDef,
    library: ContentLibrary,
    *,
    weapon_req: object = None,
    effect_level: bool = False,
) -> Choice:
    """條件選項。``effect_level``：這個選單是效果（或修正規則）的條件；技能層級的條件選單不能選
    「手持武器」（只能寫在效果上，和 schema 同一個訊息）。"""
    info: dict[str, object] = {"min_rarity": condition.min_rarity, "harshness": condition.harshness}
    if condition.id == WIELDING_WEAPON and not effect_level:
        info["unavailable_zh"] = WIELDING_EFFECT_ONLY
    return Choice(
        value=condition.id,
        name_zh=condition.name_zh,
        description_zh=condition.description_zh,
        params=condition_param_fields(condition, library, weapon_req),
        info=info,
    )
