"""技能工坊：推導「下一步的合法選項」（Phase 3F-1；Phase 4 的 LLM 技能生成也用它約束輸出）。

:func:`draft_options` 是純函式：輸入組到一半的技能（:data:`~trpg.skillgen.draft.Draft`）與內容庫，
依序回傳每個前置步驟都完成的步驟（:data:`~trpg.skillgen.option_models.STEP_IDS`）的欄位與合法選項。

合法選項的來源（不在這裡另寫規則）：

- 骨架：``content/skeletons/``（啟用的骨架、允許的 ``kinds``、``shapes``、核心與附帶原語、附帶效果
  上限、``required_category``、``forbid_affects``、``requires_condition``、``min_rarity``）。
- 形狀與參數範圍：``skill_shapes.yaml``；原語、參數範圍與可搭配的形狀與對象：
  ``skill_primitives.yaml``；條件：``skill_conditions.yaml``；觸發時機：``skill_triggers.yaml``。
- 代價：:class:`~trpg.content.skills.SkillCost` 的欄位範圍、``skill_budget.yaml`` 的自身狀態代價。
- 稀有度：:func:`~trpg.skillgen.validate.rarity_requirements`（與驗證器共用）、``skill_budget.yaml``
  的效果數量上限、雙屬性縮放的最低稀有度、傳說的核心（:func:`~trpg.content.skills.legendary_cores`）。

不合法的選項 **不列出**；只取決於多個欄位組合的規則（互斥規則、預算、骨架的點數占比）列在該步驟的
``notes_zh``，由 :func:`trpg.skillgen.draft_check.check_draft` 檢查。
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from trpg.content.library import ContentLibrary
from trpg.content.skill_rules import SkeletonDef
from trpg.content.skill_scaling import ScalingFacts
from trpg.content.skills import (
    AFFECTS_VALUES,
    BASIC_ACTIONS,
    CHANGE_TARGETS,
    GATHER_SHAPES,
    INTERCEPT,
    MAX_MODIFIERS,
    MODIFIER_CHANGES,
    ON_HIT_PRIMITIVES,
    PLACE_TRAP,
    RARITY_ORDER,
    SELF_CONDITIONS,
    SELF_ONLY_CHANGES,
    SKELETON_IDS,
    SKILL_REACTION_EVENTS,
    ModifierChange,
    PrimitiveDef,
    SkillCost,
    SkillDef,
    TrapSpec,
    TriggerSpec,
    legendary_cores,
    rarity_rank,
)
from trpg.shared.types import Attribute
from trpg.skillgen.draft import Draft, DraftError, build_skill, draft_skeleton, step_complete
from trpg.skillgen.option_conform import field_problems
from trpg.skillgen.option_effect_rules import cooldown_requirement, effect_fixes, with_param_blocks
from trpg.skillgen.option_fill import variants
from trpg.skillgen.option_followup import (
    FOLLOWUP_SKELETON,
    followup_fields,
    followup_notes,
    followup_visible,
)
from trpg.skillgen.option_models import (
    STEP_IDS,
    Choice,
    DraftOptions,
    EffectFix,
    FieldSpec,
    StepId,
    StepOptions,
)
from trpg.skillgen.option_nested import nested_field
from trpg.skillgen.option_params import (
    AFFECTS_TEXT,
    ParamContext,
    condition_choice,
    model_range,
    primitive_param_fields,
    shape_param_fields,
)
from trpg.skillgen.option_player import playerize
from trpg.skillgen.option_rules import (
    composition_block,
    composition_info,
    cost_step_text,
    resource_cost_text,
)
from trpg.skillgen.option_scaling import scaling_extra_fields
from trpg.skillgen.option_variant import variant_fields, variant_notes, variants_visible
from trpg.skillgen.player_text import CHANGE_TEXT, plainify
from trpg.skillgen.scaling import attr_names_zh, scaling_basis_zh
from trpg.skillgen.validate import rarity_requirements

__all__ = ["RarityFloor", "draft_options", "minimum_rarity"]

KIND_TEXT: dict[str, tuple[str, str]] = {
    "active": ("主動技", "花 AP 施放"),
    "passive": ("被動", "觸發時機到了自動生效，不花 AP"),
    "reaction": ("反應技", "被攻擊等時機不花 AP 立刻施放一次"),
    "stance": ("姿態", "花 AP 進入，持續到取消"),
    "modifier": ("修正", "持續改變自己的其他技能或基本動作（裝在被動欄位）"),
}
CATEGORY_TEXT: dict[str, tuple[str, str]] = {
    "weapon": ("武器技", "傷害用武器骰 × 倍率，靠武器出招"),
    "spell": ("法術技", "傷害用技能自己的骰子與元素"),
}
WEAPON_REQ_TEXT: dict[str, str] = {
    "melee": "近戰武器",
    "ranged": "遠程武器",
    "focus": "法器",
    "any": "任何武器",
}
_WEAPON_REQS: dict[str, tuple[str, ...]] = {
    "weapon": ("melee", "ranged"),
    "spell": ("focus", "any"),
}
RARITY_TEXT: dict[str, str] = {
    "common": "普通",
    "rare": "稀有",
    "epic": "史詩",
    "legendary": "傳說",
}
STEP_TEXT: dict[StepId, tuple[str, str]] = {
    "skeleton": ("骨架", "技能的大類：決定能用哪些種類、形狀、核心效果與附帶效果"),
    "basics": (
        "基本設定",
        "種類、武器技或法術技、縮放屬性、階級與 AP（被動選觸發時機、反應技選反應時機）",
    ),
    "shape": ("形狀", "技能打到哪些格子：單體、直線、錐形……與射程、大小"),
    "effects": ("效果", "核心效果與附帶效果（修正技能則是修正規則）"),
    "followup": (
        "第二段",
        "複合技能：接一個有自己骨架與形狀的第二段——位移 → 動作、動作 → 位移、聚集 → 打擊、"
        "擊殺 → 接續、命中 → 加碼、延遲段（可省略）",
    ),
    "condition": ("條件", "技能要在什麼情況下才生效（可省略）"),
    "cost": ("代價", "法力、冷卻、每場次數、生命、自身狀態、源力；代價越重，可用預算越多"),
    "rarity": ("稀有度", "由用到的形狀、原語、狀態、條件推導出最低稀有度"),
    "variants": (
        "戰場變奏",
        "同一招在不同地形有不同型態：站在某種表面、居高、靠牆或目標在某種表面時自動換型態"
        "（稀有以上，可省略）",
    ),
}
_ACTION_TEXT = {"attack": "普攻", "shove": "推擊", "trip": "絆倒", "interact": "互動"}
_TRAP_SHAPES = ("single", "cross", "square3")
"""陷阱觸發範圍可用的形狀（``skill_budget.yaml`` 的陷阱預算以這三種形狀的倍率計算）。"""


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _step(
    step: StepId,
    draft: Draft,
    library: ContentLibrary,
    fields: tuple[FieldSpec, ...],
    notes: tuple[str, ...] = (),
    *,
    description: str | None = None,
) -> StepOptions:
    name, desc = STEP_TEXT[step]
    return StepOptions(
        id=step,
        name_zh=name,
        description_zh=desc if description is None else description,
        complete=step_complete(step, draft, library),
        fields=fields,
        notes_zh=notes,
    )


# ---------------------------------------------------------------------------
# 1. 骨架
# ---------------------------------------------------------------------------


def _skeleton_choice(skeleton: SkeletonDef) -> Choice:
    return Choice(
        value=skeleton.id,
        name_zh=skeleton.name_zh,
        description_zh=skeleton.description_zh,
        info={
            "kinds": list(skeleton.kinds),
            "min_rarity": skeleton.min_rarity,
            "shapes": list(skeleton.shapes),
            "core_primitives": list(skeleton.core.primitives),
            "secondary_max_count": skeleton.secondary.max_count,
            "requires_condition": skeleton.requires_condition,
        },
    )


def _skeleton_step(draft: Draft, library: ContentLibrary) -> StepOptions:
    skeletons = [library.skeletons[s] for s in SKELETON_IDS if s in library.skeletons]
    choices = tuple(_skeleton_choice(s) for s in skeletons if s.enabled)
    field = FieldSpec(
        field="skeleton",
        name_zh="骨架",
        description_zh="技能的大類",
        type="choice",
        required=True,
        choices=choices,
    )
    return _step("skeleton", draft, library, (field,))


# ---------------------------------------------------------------------------
# 2. 基本設定
# ---------------------------------------------------------------------------


def _trigger_field(library: ContentLibrary) -> FieldSpec:
    fields = TriggerSpec.model_fields
    low, high = model_range(fields["max_per_round"])
    events: list[Choice] = []
    for timing in library.ruleset.skill_triggers.triggers:
        params: list[FieldSpec] = []
        if timing.id == "every_n_hits":
            params.append(
                FieldSpec(field="n", name_zh="每幾次", type="int", required=True, min=2, max=3)
            )
        if timing.id == "on_cast_tag":
            params.append(FieldSpec(field="tag", name_zh="技能標籤", type="text", required=True))
        if timing.id == "on_status_applied":
            params.append(FieldSpec(field="status", name_zh="狀態（省略＝任何）", type="text"))
        if timing.id == "on_enter_surface":
            params.append(FieldSpec(field="surface", name_zh="表面（省略＝任何）", type="text"))
        targets = [Choice(value="self", name_zh="持有者自己")]
        if timing.has_other:
            targets.append(
                Choice(
                    value="other",
                    name_zh="另一方",
                    description_zh="該時機的另一方單位（例：被命中的敵人）",
                    params=(
                        FieldSpec(field="max_distance", name_zh="最遠距離", type="int", min=1),
                    ),
                )
            )
        params.append(
            FieldSpec(
                field="target",
                name_zh="作用對象",
                type="choice",
                choices=tuple(targets),
                default="self",
            )
        )
        events.append(
            Choice(
                value=timing.id,
                name_zh=timing.name_zh,
                description_zh=timing.description_zh,
                params=tuple(params),
                info={"min_rarity": timing.min_rarity},
            )
        )
    return FieldSpec(
        field="trigger",
        name_zh="觸發時機",
        type="object",
        required=True,
        fields=(
            FieldSpec(
                field="event", name_zh="時機", type="choice", required=True, choices=tuple(events)
            ),
            FieldSpec(
                field="max_per_round",
                name_zh="每輪最多觸發",
                type="int",
                min=low,
                max=high,
                default=1,
            ),
        ),
    )


def _reaction_field() -> FieldSpec:
    texts = {
        "hit_by_melee": "被近戰攻擊命中後",
        "hit_by_attack": "被任何攻擊命中後",
        "ally_hit_adjacent": "相鄰友方被攻擊命中、傷害之前（只能用「替隊友擋攻擊」）",
        "enemy_leaves_adjacent": "敵人離開相鄰格時",
        "hit_by_spell": "被法術技命中、傷害之前",
        "ally_downed": "視野內的友方倒下之後（形狀必須是自身）",
        "enemy_enters_adjacent": "敵人主動走進相鄰格之後",
        "ally_targeted": "相鄰友方被敵人選為目標、命中判定之前",
    }
    return FieldSpec(
        field="reaction",
        name_zh="反應時機",
        type="object",
        required=True,
        fields=(
            FieldSpec(
                field="event",
                name_zh="時機",
                type="choice",
                required=True,
                choices=tuple(Choice(value=e, name_zh=texts[e]) for e in SKILL_REACTION_EVENTS),
            ),
        ),
    )


def _kind_choice(kind: str, library: ContentLibrary) -> Choice:
    name, desc = KIND_TEXT[kind]
    params: tuple[FieldSpec, ...] = ()
    if kind == "active":
        aps = sorted(library.budget.ap_coefficient_permille)
        params = (
            FieldSpec(
                field="ap_cost",
                name_zh="AP",
                description_zh="施放花的 AP（AP 越多，可用預算越多）",
                type="int",
                required=True,
                min=aps[0],
                max=aps[-1],
            ),
        )
    elif kind == "passive":
        params = (_trigger_field(library),)
    elif kind == "reaction":
        params = (_reaction_field(),)
    return Choice(value=kind, name_zh=name, description_zh=desc, params=params)


def _category_field(skeleton: SkeletonDef) -> FieldSpec:
    categories = (
        (skeleton.required_category,) if skeleton.required_category else ("weapon", "spell")
    )
    choices: list[Choice] = []
    for category in categories:
        reqs = _WEAPON_REQS[category]
        if skeleton.required_weapon_req is not None:
            reqs = tuple(r for r in reqs if r == skeleton.required_weapon_req)
        weapon = FieldSpec(
            field="weapon_req",
            name_zh="武器需求",
            type="choice",
            required=True,
            choices=tuple(Choice(value=r, name_zh=WEAPON_REQ_TEXT[r]) for r in reqs),
        )
        name, desc = CATEGORY_TEXT[category]
        choices.append(Choice(value=category, name_zh=name, description_zh=desc, params=(weapon,)))
    return FieldSpec(
        field="category", name_zh="類別", type="choice", required=True, choices=tuple(choices)
    )


def _scaling_field(draft: Draft, library: ContentLibrary) -> FieldSpec:
    """縮放屬性欄位。武器技（Phase 3H-6）命中與傷害看手上武器的屬性，欄位鎖成「看武器」：
    選項只有所需武器大類（近戰、遠程）的主屬性；還沒選武器需求時沒有選項。"""
    if draft.get("category") != "weapon":
        return _spell_scaling_field(draft, library)
    req = draft.get("weapon_req")
    attr = library.skill_scaling.weapon_class_attr(str(req)) if req in _WEAPON_CLASSES else None
    return FieldSpec(
        field="scaling_attr",
        name_zh="縮放屬性",
        description_zh=(
            "武器技的命中與傷害看手上武器的屬性（雙屬性武器取較高或取平均），不能另外選。"
            "武器技一定要拿近戰或遠程武器；不限武器的是法術技"
            if attr is not None
            else "武器技看手上武器的屬性；先選武器需求"
        ),
        type="choice",
        required=True,
        locked=True,
        default=None if attr is None else attr.value,
        choices=()
        if attr is None
        else (Choice(value=attr.value, name_zh=_weapon_scaling_name(str(req), library)),),
    )


def _weapon_scaling_name(weapon_req: str, library: ContentLibrary) -> str:
    """武器技縮放屬性的顯示：實際看的是手上武器的屬性，例子從武器資料產生（每種屬性組合取一把，
    優先取玩家能裝備的武器，依 ID 排序，最多 3 種），不寫死。"""
    equipped = {i.weapon for i in library.items.values() if i.weapon is not None}
    pool = sorted(w for w in library.weapons if w in equipped) or sorted(library.weapons)
    examples: dict[str, str] = {}
    for weapon_id in pool:
        weapon = library.weapons[weapon_id]
        if weapon.weapon_class == weapon_req:
            examples.setdefault(weapon.scaling_names_zh(), weapon.name_zh)
    shown = "、".join(f"{name}＝{attrs}" for attrs, name in list(examples.items())[:3])
    return f"依手上武器而定（例：{shown}）" if shown else "依手上武器而定"


_WEAPON_CLASSES = ("melee", "ranged")


def _spell_scaling_field(draft: Draft, library: ContentLibrary) -> FieldSpec:
    """法術技（與還沒選類別）的縮放屬性（Phase 3H-7，06 6.10）：只列允許範圍（主題由主要效果推導，
    ``skill_scaling.yaml``），預設範圍裡第一個；說明寫出範圍的由來。還沒選效果時主題未定，列出
    六個屬性並提醒之後會依效果限縮（選錯時檢查列出中文原因）。"""
    facts = ScalingFacts.of_draft(draft)
    if not facts.effects and draft.get("kind") != "modifier":
        return FieldSpec(
            field="scaling_attr",
            name_zh="縮放屬性",
            description_zh=(
                "技能的數值隨這個屬性成長。法術看主要效果的主題（智力＝元素傷害與互動；感知＝治療、"
                "護盾、輔助、偵測與標記；意志＝召喚、獻祭、詛咒、心智控制、暗影），選好效果後只列"
                "允許的屬性"
            ),
            type="choice",
            required=True,
            # 法術不看力量、敏捷、體質（身體類的法術要先選好物理效果才會列出），也不預設任何一個
            choices=tuple(
                Choice(value=a.value, name_zh=a.display_name)
                for a in Attribute
                if draft.get("category") != "spell" or a not in library.skill_scaling.body_attrs
            ),
        )
    allowed = library.scaling_range(facts) or tuple(Attribute)
    return FieldSpec(
        field="scaling_attr",
        name_zh="縮放屬性",
        description_zh=(
            f"技能的數值隨這個屬性成長。{scaling_basis_zh(facts, library)}，"
            f"只能看 {attr_names_zh(allowed)}"
        ),
        type="choice",
        required=True,
        default=allowed[0].value,
        choices=tuple(Choice(value=a.value, name_zh=a.display_name) for a in allowed),
    )


def _basics_step(draft: Draft, library: ContentLibrary, skeleton: SkeletonDef) -> StepOptions:
    tiers = sorted(library.ruleset.core.tier_budget)
    fields = (
        FieldSpec(field="name_zh", name_zh="技能名稱", type="text", default="工坊技能"),
        FieldSpec(
            field="kind",
            name_zh="種類",
            type="choice",
            required=True,
            choices=tuple(_kind_choice(k, library) for k in skeleton.kinds),
        ),
        _category_field(skeleton),
        _scaling_field(draft, library),
        FieldSpec(
            field="tier",
            name_zh="階級",
            description_zh="階級越高，可用預算越多",
            type="int",
            required=True,
            min=tiers[0],
            max=tiers[-1],
        ),
    )
    notes: list[str] = []
    if skeleton.required_category is not None:
        notes.append(
            f"骨架「{skeleton.name_zh}」只能是 {CATEGORY_TEXT[skeleton.required_category][0]}"
        )
    if (
        draft.get("category") != "weapon"
        and draft.get("kind") != "modifier"
        and not ScalingFacts.of_draft(draft).effects
    ):
        # 縮放屬性的允許範圍看主要效果的主題（3H-7）：效果還沒選時先提示，別等到檢查才被打槍（3-47）
        notes.append("縮放屬性的允許範圍要看主要效果的主題；選好「效果」後再回來確認這一欄")
    return _step("basics", draft, library, fields, tuple(notes))


# ---------------------------------------------------------------------------
# 3. 形狀
# ---------------------------------------------------------------------------


def _core_primitives(skeleton: SkeletonDef, library: ContentLibrary) -> list[PrimitiveDef]:
    primitives = library.ruleset.primitives.by_id()
    return [primitives[p] for p in skeleton.core.primitives if p in primitives]


def _fits_shape(primitive: PrimitiveDef, shape: str) -> bool:
    return primitive.allowed_shapes is None or shape in primitive.allowed_shapes


def _shape_step(draft: Draft, library: ContentLibrary, skeleton: SkeletonDef) -> StepOptions:
    shapes = library.ruleset.shapes.by_id()
    cores = _core_primitives(skeleton, library)
    weapon_ok = draft.get("category") != "spell"  # 「用武器射程」只有武器技有
    choices: list[Choice] = []
    gather = [g for g in GATHER_SHAPES if g not in skeleton.shapes]
    if skeleton.id != FOLLOWUP_SKELETON:
        gather = []
    for shape_id in (*skeleton.shapes, *gather):
        shape = shapes.get(shape_id)
        if shape is None:
            continue
        if shape_id in gather:  # 聚集段（3F-4b）：環形拉向自己，只能接「聚集 → 範圍打擊」
            choices.append(
                Choice(
                    value=shape_id,
                    name_zh=shape.name_zh,
                    description_zh=f"{shape.description_zh}（只能當聚集段：效果只有一個拉扯，"
                    "並在第二段選「聚集 → 範圍打擊」）",
                    params=shape_param_fields(shape, weapon_ok=weapon_ok),
                    info={"min_rarity": shape.min_rarity, "targeting": shape.targeting},
                )
            )
            continue
        if skeleton.kinds != ("modifier",) and not any(_fits_shape(p, shape_id) for p in cores):
            continue  # 沒有任何核心原語能搭配這個形狀
        choices.append(
            Choice(
                value=shape_id,
                name_zh=shape.name_zh,
                description_zh=shape.description_zh,
                params=shape_param_fields(shape, weapon_ok=weapon_ok),
                info={"min_rarity": shape.min_rarity, "targeting": shape.targeting},
            )
        )
    field = FieldSpec(
        field="shape", name_zh="形狀", type="choice", required=True, choices=tuple(choices)
    )
    notes = tuple(
        f"互斥規則「{r.name_zh}」：{r.message_zh}"
        for r in library.exclusions.rules
        if r.when is not None and r.when.has_cooldown is False
    )
    return _step("shape", draft, library, (field,), notes)


# ---------------------------------------------------------------------------
# 4. 效果
# ---------------------------------------------------------------------------


def _allowed_affects(
    primitive: PrimitiveDef, skeleton: SkeletonDef, draft: Draft
) -> tuple[str, ...]:
    if primitive.acts_on == "caster":
        values: tuple[str, ...] = ("self",)
    elif primitive.acts_on == "tile":
        values = AFFECTS_VALUES
    else:
        values = tuple(a for a in AFFECTS_VALUES if a != "tiles")
    trigger = _mapping(draft.get("trigger"))
    if draft.get("kind") == "passive" and trigger.get("target", "self") == "self":
        values = tuple(a for a in values if a == "self")
    banned = {*primitive.forbid_affects, *skeleton.forbid_affects}
    return tuple(a for a in values if a not in banned)


def _affects_field(primitive: PrimitiveDef, allowed: tuple[str, ...]) -> FieldSpec:
    if primitive.id == PLACE_TRAP:  # 3-48h：陷阱只作用在格子（刻印的做法）；唯一的選項寫成「格子」
        return FieldSpec(
            field="affects",
            name_zh="對象",
            description_zh="陷阱放在你選的那一格；敵人踩到時結算的是同一招的其他效果",
            type="choice",
            choices=(
                Choice(
                    value="self",
                    name_zh="格子",
                    description_zh="陷阱放在你選的那一格",
                ),
            ),
            default="self",
        )
    default = "tiles" if primitive.acts_on == "tile" else None
    if primitive.acts_on == "caster":
        default = "self"
    elif default is None:
        default = "enemies" if primitive.harmful else "allies"
    return FieldSpec(
        field="affects",
        name_zh="對象",
        description_zh="省略時用原語的預設對象",
        required=default not in allowed,
        type="choice",
        choices=tuple(
            Choice(value=a, name_zh=AFFECTS_TEXT[a][0], description_zh=AFFECTS_TEXT[a][1])
            for a in allowed
        ),
        default=default if default in allowed else None,
    )


def _roles(primitive: PrimitiveDef, skeleton: SkeletonDef) -> tuple[bool, bool]:
    """``(可以當核心, 可以當附帶)``。"""
    core = primitive.id in skeleton.core.primitives
    rules = skeleton.secondary
    secondary = (
        rules.max_count > 0
        and (rules.primitives is None or primitive.id in rules.primitives)
        and (primitive.harmful or not rules.harmful_only)
    )
    return core, secondary


def _primitive_usable(primitive: PrimitiveDef, draft: Draft, shape: str) -> bool:
    if primitive.budget_basis is None or not _fits_shape(primitive, shape):
        return False
    if primitive.id == INTERCEPT:  # 只能出現在 ally_hit_adjacent 的反應技
        return _mapping(draft.get("reaction")).get("event") == "ally_hit_adjacent"
    return True


def _primitive_choice(
    primitive: PrimitiveDef,
    skeleton: SkeletonDef,
    draft: Draft,
    library: ContentLibrary,
    roles: tuple[bool, bool],
) -> Choice | None:
    allowed = _allowed_affects(primitive, skeleton, draft)
    if not allowed:
        return None
    core, secondary = roles
    ctx = ParamContext(
        library,
        category=draft.get("category"),
        beneficial_only=core and not secondary and skeleton.core.beneficial_only,
        stance=draft.get("kind") == "stance",
    )
    params = (
        _affects_field(primitive, allowed),
        *(
            nested_field(primitive, f, ctx, library) if f.type == "effects" else f
            for f in primitive_param_fields(primitive, ctx)
        ),
    )
    return Choice(
        value=primitive.id,
        name_zh=primitive.name_zh,
        description_zh=primitive.description_zh,
        params=params,
        info={
            "core": core,
            "secondary": secondary,
            "min_rarity": primitive.min_rarity,
            "category": primitive.category,
            "harmful": primitive.harmful,
            **composition_info(primitive),
        },
    )


_PROBE_KEYS = ("skeleton", "kind", "category", "weapon_req", "scaling_attr", "tier", "ap_cost")
_PROBE_RARITIES: tuple[dict[str, Any], ...] = (
    {"rarity": "epic"},
    {"rarity": "legendary", "cost": {"source": 1}, "activation": "timed"},
)
"""試組時的稀有度：一般（史詩）與傳說（花源力、常駐類傳說的啟動方式）。"""


def _probe_base(draft: Draft) -> dict[str, Any]:
    base = {k: draft[k] for k in _PROBE_KEYS if draft.get(k) is not None}
    for key in ("trigger", "reaction", "shape"):
        if draft.get(key) is not None:
            base[key] = draft[key]
    return base


def _arrangements(
    candidate: dict[str, Any], contexts: list[list[dict[str, Any]]]
) -> list[list[dict[str, Any]]]:
    """候選效果單獨、接在每組既有效果之後或之前。"""
    out = [[candidate]]
    for context in contexts:
        out += [[*context, candidate], [candidate, *context]]
    return out


def _probe_builds(
    base: dict[str, Any], choice: Choice, contexts: list[list[dict[str, Any]]]
) -> bool | None:
    """以最小填法試組（單獨、接在已填的效果或一個核心效果之後或之前，一般或傳說），有一種能通過
    schema 就是 ``True``；無法自動填時為 ``None``。"""
    fills = variants(choice)
    if not fills:
        return None
    for fill in fills:
        for effects in _arrangements(fill, contexts):
            extra: dict[str, Any] = {"effects": effects}
            if any(e["type"] == "place_trap" for e in effects):
                extra["trap"] = {"trigger": "enter"}
            for rarity in _PROBE_RARITIES:
                if _probe(base, {**extra, **rarity}) is not None:
                    return True
    return False


def _schema_accepts(
    base: dict[str, Any], choice: Choice, contexts: list[list[dict[str, Any]]]
) -> bool:
    """試組通過，或試不出來：無法自動填、帶巢狀效果參數（``then``、``win``／``lose``……）的原語
    最小填法不準，仍列出（由檢查負責）。"""
    built = _probe_builds(base, choice, contexts)
    return built is not False or any(p.type == "effects" for p in choice.params)


def _base_accepts_something(base: dict[str, Any], candidates: list[Choice]) -> bool:
    """前面步驟的內容至少能和一個候選效果組成技能（否則試組沒有意義）。"""
    return any(_probe_builds(base, c, []) for c in candidates)


def _core_example(choices: list[Choice]) -> dict[str, Any] | None:
    for choice in choices:
        if choice.info.get("core"):
            fills = variants(choice)
            if fills:
                return fills[0]
    return None


def _effect_choices(draft: Draft, library: ContentLibrary, skeleton: SkeletonDef) -> list[Choice]:
    """骨架與形狀允許的原語，再以 schema 試組濾掉這個種類、類別與形狀不能用的原語（例：反應技
    不能用衝鋒、姿態不能用賭注）。"""
    shape = str(_mapping(draft.get("shape")).get("type"))
    candidates: list[Choice] = []
    for primitive in library.ruleset.primitives.primitives:
        roles = _roles(primitive, skeleton)
        if not any(roles) or not _primitive_usable(primitive, draft, shape):
            continue
        choice = _primitive_choice(primitive, skeleton, draft, library, roles)
        if choice is not None:
            candidates.append(choice)
    base = _probe_base(draft)
    if not _base_accepts_something(base, candidates):
        return candidates  # 前面的步驟本身就組不起來（見檢查結果的問題清單），不再試組
    existing = [dict(_mapping(e)) for e in draft.get("effects") or ()]
    out: list[Choice] = []
    for choice in candidates:
        contexts = [existing] if existing else []
        core = _core_example([c for c in candidates if c is not choice])
        if core is not None:
            contexts.append([core])
        if _schema_accepts(base, choice, contexts):
            out.append(choice)
    return out


def trap_effects_text(draft: Draft, library: ContentLibrary) -> str:
    """陷阱設定區的說明（3-48h）：踩到後會結算的是同一招的其他效果——列出目前會結算的效果，
    還沒有時提示要新增一個。"""
    by_id = library.ruleset.primitives.by_id()
    names = [
        by_id[t].name_zh if (t := str(_mapping(e).get("type"))) in by_id else t
        for e in draft.get("effects") or ()
        if _mapping(e).get("type") != PLACE_TRAP
    ]
    if not names:
        return "請新增一個效果（例如傷害），它就是踩到後的效果"
    return "踩到後會結算：下方其他效果（目前：" + "、".join(names) + "）"


def _trap_field(draft: Draft, library: ContentLibrary) -> FieldSpec:
    fields = TrapSpec.model_fields
    low, high = model_range(fields["rounds"])
    return FieldSpec(
        field="trap",
        name_zh="陷阱設定",
        description_zh="效果有「放置陷阱」時必填。" + trap_effects_text(draft, library),
        type="object",
        fields=(
            FieldSpec(
                field="trigger",
                name_zh="觸發方式",
                type="choice",
                required=True,
                choices=(
                    Choice(value="enter", name_zh="踩到時", description_zh="敵人進入陷阱格時觸發"),
                    Choice(value="delay", name_zh="延遲", description_zh="rounds 輪後觸發"),
                ),
            ),
            FieldSpec(field="rounds", name_zh="輪數", type="int", min=low, max=high, default=2),
            FieldSpec(
                field="shape",
                name_zh="觸發範圍",
                type="choice",
                choices=tuple(
                    Choice(value=s, name_zh=library.ruleset.shapes.by_id()[s].name_zh)
                    for s in _TRAP_SHAPES
                ),
                default="single",
                plain_value=True,  # 形狀 ID 字串（TrapSpec.shape），不是 {"type": ...}
            ),
        ),
    )


def _max_effects(library: ContentLibrary) -> int:
    return max(r.max_effects for r in library.budget.rarity.values())


def _effects_notes(skeleton: SkeletonDef, library: ContentLibrary) -> tuple[str, ...]:
    core = "、".join(skeleton.core.primitives) or "（無）"
    notes = [
        f"至少 1 個核心效果（{core}）；附帶效果最多 {skeleton.secondary.max_count} 個",
        f"效果總數最多 {_max_effects(library)} 個；普通稀有度最多 "
        f"{library.budget.rarity['common'].max_effects} 個",
    ]
    if skeleton.core.min_share_permille:
        notes.append(f"核心效果的點數至少占 {skeleton.core.min_share_permille / 10:g}%")
    for primitive, limit in sorted(skeleton.secondary.max_share_permille.items()):
        notes.append(f"{primitive} 的點數最多占 {limit / 10:g}%")
    if skeleton.require_any_primitives:
        notes.append(f"至少要有 {'、'.join(skeleton.require_any_primitives)} 其中之一")
    notes += [f"互斥規則「{r.name_zh}」：{r.message_zh}" for r in library.exclusions.rules]
    return tuple(notes)


def _with_availability(
    choices: list[Choice], draft: Draft, library: ContentLibrary
) -> list[Choice]:
    """依已填的效果與種類標示組合規則下現在不能加的效果（3H-8）：``info.unavailable_zh`` 是原因；
    已有「其他效果限自己」的效果時，新加的效果 ``info.forced_affects`` 是必須用的對象。"""
    by_id = library.ruleset.primitives.by_id()
    existing = [_mapping(e) for e in draft.get("effects") or ()]
    out: list[Choice] = []
    for choice in choices:
        primitive = by_id.get(str(choice.value))
        if primitive is None:
            out.append(choice)
            continue
        affects = next((p for p in choice.params if p.field == "affects"), None)
        allowed = tuple(str(c.value) for c in affects.choices) if affects is not None else ()
        reason, forced = composition_block(
            primitive, existing, library, kind=draft.get("kind"), allowed_affects=allowed
        )
        extra: dict[str, Any] = {}
        if reason is not None:
            extra["unavailable_zh"] = reason
        if forced is not None:
            extra["forced_affects"] = forced
        out.append(
            choice.model_copy(update={"info": {**choice.info, **extra}}) if extra else choice
        )
    return out


def _effects_step(draft: Draft, library: ContentLibrary, skeleton: SkeletonDef) -> StepOptions:
    if draft.get("kind") == "modifier":
        return _modifier_step(draft, library)
    choices = _with_availability(_effect_choices(draft, library, skeleton), draft, library)
    choices = with_param_blocks(
        choices, draft, library, skeleton
    )  # 3-48h：違規的對象與狀態事前停用
    fields = [
        FieldSpec(
            field="effects",
            name_zh="效果",
            description_zh="依序結算；衝鋒、直線衝撞、瞬步必須是第一個效果",
            type="effects",
            required=True,
            choices=tuple(choices),
            min_count=1,
            max_count=_max_effects(library),
        )
    ]
    if any(c.value == "place_trap" for c in choices):
        fields.append(_trap_field(draft, library))
    notes = (*_effects_notes(skeleton, library), *_rune_hint(draft, library))
    return _step("effects", draft, library, tuple(fields), notes)


RUNE_HINT_ZH = (
    "符文本身沒有效果。想要站上去就有效果，請用持續區域；"
    "或加一招讀取符文（目標站在自己的符文上）的技能。"
)
"""草稿有刻印、又給友方增益，卻沒有任何讀取符文的條件時的提示（3-48f，玩法決定 #51）。"""


def _rune_hint(draft: Draft, library: ContentLibrary) -> tuple[str, ...]:
    effects = [e for e in draft.get("effects") or () if isinstance(e, Mapping)]
    if not any(e.get("type") == "inscribe" for e in effects):
        return ()
    statuses = library.ruleset.statuses.by_id()

    def buff_for_allies(effect: Mapping[str, Any]) -> bool:
        if effect.get("affects") not in ("allies", "all") or effect.get("type") == "inscribe":
            return False
        if effect.get("type") == "apply_status":
            status = statuses.get(str(effect.get("status")))
            return status is not None and status.beneficial
        return effect.get("type") in ("shield", "heal", "grant_ap", "cheat_death", "cleanse")

    def reads_runes(effect: Mapping[str, Any]) -> bool:
        return effect.get("type") == "detonate_runes" or (
            _mapping(effect.get("condition")).get("type") == "on_own_rune"
        )

    top = _mapping(draft.get("condition")).get("type") == "on_own_rune"
    if top or any(reads_runes(e) for e in effects):
        return ()
    return (RUNE_HINT_ZH,) if any(buff_for_allies(e) for e in effects) else ()


def _change_field(name: str, library: ContentLibrary, category: str | None) -> FieldSpec:
    info = ModifierChange.model_fields[name]
    low, high = model_range(info)
    targets = "、".join(sorted(CHANGE_TARGETS[name]))
    when = "；選目標之前就決定，條件只能是自身血量" if name in SELF_ONLY_CHANGES else ""
    base: dict[str, Any] = {
        "field": name,
        "name_zh": CHANGE_TEXT[name],
        "description_zh": f"可套用：{targets}{when}",
    }
    if name == "add_element":
        elements = tuple(
            Choice(value=e.id.value, name_zh=e.name_zh)
            for e in library.elements.elements
            if e.id.value != "physical"
        )
        value = FieldSpec(**base, type="choice", choices=elements)
    elif name == "shape_to":
        value = FieldSpec(
            **base,
            type="choice",
            choices=tuple(
                Choice(value=s, name_zh=library.ruleset.shapes.by_id()[s].name_zh)
                for s in ("line", "chain", "cone")
            ),
        )
    elif name == "add_tags":
        value = FieldSpec(**base, type="tags", min_count=1, max_count=3)
    elif name == "on_hit_effects":
        primitives = library.ruleset.primitives.by_id()
        ctx = ParamContext(library, category=category)
        value = FieldSpec(
            **base,
            type="effects",
            min_count=1,
            max_count=2,
            choices=tuple(
                Choice(
                    value=p,
                    name_zh=primitives[p].name_zh,
                    params=primitive_param_fields(primitives[p], ctx),
                )
                for p in ON_HIT_PRIMITIVES
            ),
        )
    elif name in ("grant_pierce", "allow_self_target"):
        value = FieldSpec(**base, type="bool")
    else:
        value = FieldSpec(**base, type="int", min=low, max=high)
    return value


def _modifier_step(draft: Draft, library: ContentLibrary) -> StepOptions:
    category = draft.get("category")
    conditions = library.ruleset.conditions.conditions
    rule = FieldSpec(
        field="modifiers",
        name_zh="修正規則",
        description_zh="每條規則：套用對象、（可省略的）條件、恰好一種改變",
        type="modifiers",
        required=True,
        min_count=1,
        max_count=MAX_MODIFIERS,
        fields=(
            FieldSpec(
                field="applies_to",
                name_zh="套用對象",
                description_zh="至少一項（多項為「或」）",
                type="object",
                required=True,
                fields=(
                    FieldSpec(
                        field="actions",
                        name_zh="基本動作",
                        type="multi_choice",
                        choices=tuple(
                            Choice(value=a, name_zh=_ACTION_TEXT[a]) for a in BASIC_ACTIONS
                        ),
                    ),
                    FieldSpec(field="skill_tags", name_zh="帶這些標籤的技能", type="tags"),
                    FieldSpec(field="all_attacks", name_zh="所有攻擊", type="bool"),
                    FieldSpec(field="all_skills", name_zh="所有技能", type="bool"),
                ),
            ),
            FieldSpec(
                field="change",
                name_zh="改變",
                description_zh="恰好填一種（數值不可為 0）",
                type="object",
                required=True,
                fields=tuple(_change_field(n, library, category) for n in MODIFIER_CHANGES),
            ),
            FieldSpec(
                field="condition",
                name_zh="條件",
                type="choice",
                choices=tuple(condition_choice(c, library) for c in conditions),
            ),
        ),
    )
    notes = (
        "每種改變只能套用在它說明中列出的對象",
        "選目標之前就決定的改變條件只能是 " + "、".join(SELF_CONDITIONS),
    )
    return _step("effects", draft, library, (rule,), notes)


def _followup_step(draft: Draft, library: ContentLibrary) -> StepOptions:
    fields = followup_fields(draft, library, _effect_choices, condition_choice)
    return _step("followup", draft, library, fields, followup_notes(library))


# ---------------------------------------------------------------------------
# 5. 條件
# ---------------------------------------------------------------------------


def _condition_step(draft: Draft, library: ContentLibrary, skeleton: SkeletonDef) -> StepOptions:
    if draft.get("kind") == "modifier":
        return _step("condition", draft, library, (), ("修正技能的條件寫在每條修正規則裡",))
    field = FieldSpec(
        field="condition",
        name_zh="技能條件",
        description_zh="不成立時整個技能不生效；也可以寫在個別效果的 condition（只影響該效果）",
        type="choice",
        required=skeleton.requires_condition,
        choices=tuple(condition_choice(c, library) for c in library.ruleset.conditions.conditions),
    )
    notes = ["條件會讓效果點數打折（常見 × 0.85、嚴苛 × 0.6）"]
    if skeleton.requires_condition:
        notes.append(f"骨架「{skeleton.name_zh}」的技能或效果必須有條件")
    return _step("condition", draft, library, (field,), tuple(notes))


# ---------------------------------------------------------------------------
# 6. 代價
# ---------------------------------------------------------------------------


def _probe(draft: Draft, overrides: Mapping[str, Any] | None = None) -> SkillDef | None:
    try:
        return build_skill(draft, overrides)
    except DraftError:
        return None


def _non_legendary_probe(draft: Draft) -> SkillDef | None:
    """以非傳說的稀有度試組（看效果、修正規則能不能成立）。"""
    cost = {k: v for k, v in _mapping(draft.get("cost")).items() if k != "source"}
    return _probe(draft, {"rarity": "epic", "cost": cost, "activation": None})


def _can_be_legendary(draft: Draft, library: ContentLibrary) -> bool:
    probe = _non_legendary_probe(draft)
    if probe is None:
        return False
    return len(legendary_cores(probe, library.ruleset.primitives.by_id())) == 1


def _cost_int(
    name: str, name_zh: str, description_zh: str, *, min_: int | None = None
) -> FieldSpec:
    low, high = model_range(SkillCost.model_fields[name])
    return FieldSpec(
        field=f"cost.{name}",
        name_zh=name_zh,
        description_zh=description_zh,
        type="int",
        min=low if min_ is None else min_,
        max=high,
    )


def _self_status_choice(status_id: str, draft: Draft, library: ContentLibrary) -> Choice:
    """一個自身狀態選項（3-50）：附上這個狀態專屬的持續回合範圍（暈眩固定 2）、折抵（‰）；不能放的
    （沉默只能放法術技）標 ``unavailable_zh``——與驗證器同源（``allowance.self_status``）。"""
    rule = library.budget.allowance.self_status
    status = library.ruleset.statuses.by_id()[status_id]
    fixed = rule.fixed_duration.get(status_id)
    low, high = (fixed, fixed) if fixed is not None else (2, 3)
    info: dict[str, Any] = {"cap_permille": rule.cap_of(status_id)}
    if status_id in rule.spell_only and draft.get("category") not in (None, "spell"):
        info["unavailable_zh"] = (
            f"{status.name_zh}只能放在法術技：沒有法術的人不能白拿折扣。"
            "回到「基本設定」把類別改成法術，或改選別的狀態"
        )
    points = status.budget_points or 0
    description = f"每個有效回合折抵 {points * rule.per_point_permille / 10:g}%"
    if fixed is not None:
        description += (
            f"；固定 {fixed} 回合（跳過自己下一個回合），折抵上限 {rule.cap_of(status_id) / 10:g}%"
        )
    return Choice(
        value=status_id,
        name_zh=status.name_zh,
        description_zh=description,
        info=info,
        params=(
            FieldSpec(
                field="duration",
                name_zh="持續回合",
                type="int",
                required=True,
                min=low,
                max=high,
                default=low,
            ),
        ),
    )


def _self_status_field(draft: Draft, library: ContentLibrary) -> FieldSpec:
    statuses = library.ruleset.statuses.by_id()
    allowed = library.budget.allowance.self_status.allowed
    return FieldSpec(
        field="cost.self_status",
        name_zh="自身狀態代價",
        description_zh="施放後自己獲得這個負面狀態（只有主動技能；一招最多 1 個，與透支擇一）",
        type="object",
        fields=(
            FieldSpec(
                field="status",
                name_zh="狀態",
                type="choice",
                required=True,
                choices=tuple(
                    _self_status_choice(s, draft, library) for s in allowed if s in statuses
                ),
            ),
        ),
    )


def _overdraft_field(library: ContentLibrary) -> FieldSpec:
    low, high = model_range(SkillCost.model_fields["overdraft"])
    percent = library.budget.allowance.overdraft_permille / 10
    return FieldSpec(
        field="cost.overdraft",
        name_zh="透支",
        description_zh=(
            f"施放後自己下一個回合少 {high} AP（換 {percent:g}% 預算；與自身狀態擇一）"
        ),
        type="int",
        min=low,
        max=high,
    )


def _legendary_fields(draft: Draft, library: ContentLibrary) -> list[FieldSpec]:
    if not _can_be_legendary(draft, library):
        return []
    out = [
        FieldSpec(
            field="cost.source",
            name_zh="源力",
            description_zh="花源力的技能就是傳說技能（必須恰好一個傳說核心）",
            type="int",
            min=model_range(SkillCost.model_fields["source"])[0],
            max=model_range(SkillCost.model_fields["source"])[1],
        )
    ]
    effects = draft.get("effects") or ()
    if draft.get("kind") == "modifier" or any(
        _mapping(e).get("type") == "rule_change" for e in effects
    ):
        out.append(
            FieldSpec(
                field="activation",
                name_zh="啟動方式",
                description_zh="常駐類傳說花源力時必填",
                type="choice",
                choices=(
                    Choice(value="timed", name_zh="限時", description_zh="持續數輪"),
                    Choice(value="battle", name_zh="整場", description_zh="本場剩餘時間有效"),
                ),
            )
        )
    return out


def _resource_field(draft: Draft, library: ContentLibrary) -> FieldSpec:
    """費用欄位依類別（3H-2，06 6.10）：武器技花耐力、法術技花法力。"""
    category = draft.get("category")
    if category in ("weapon", "spell") and library.budget.resource_of(category) == "stamina":
        field = _cost_int("stamina", "耐力", resource_cost_text(library, "stamina"))
    else:
        field = _cost_int("mana", "法力", resource_cost_text(library, "mana"))
    if draft.get("kind") != "active":
        return field
    # 最低花費（3-48c）：欄位範圍不收緊（內建技能有 0 的），由檢查回報違規
    desc = f"{field.description_zh}。主動技能至少要花 1 點（空白或 0 檢查會不通過）"
    return field.model_copy(update={"description_zh": desc})


def _cost_step(draft: Draft, library: ContentLibrary) -> StepOptions:
    required = cooldown_requirement(draft, library)  # 硬控（暈眩、冰凍）要求冷卻下限（3-48h）
    fields: list[FieldSpec] = [
        _resource_field(draft, library),
        _cost_int(
            "cooldown",
            "冷卻",
            "施放後幾回合不能再用" + ("" if required is None else f"（{required[1]}）"),
            min_=None if required is None else required[0],
        ),
        _cost_int("uses_per_battle", "每場次數", "每場最多施放幾次"),
        _cost_int("hp_percent", "生命代價（‰）", "施放花最大 HP 的千分比"),
    ]
    if draft.get("kind") == "active":
        cost = _mapping(draft.get("cost"))
        if cost.get("overdraft") is None or cost.get("self_status") is not None:
            fields.append(_self_status_field(draft, library))
        if cost.get("self_status") is None or cost.get("overdraft") is not None:
            fields.append(_overdraft_field(library))
    fields += _legendary_fields(draft, library)
    allowance = library.budget.allowance
    notes = (
        f"代價越重可用預算越多：冷卻每回合 +{allowance.cooldown_per_turn}‰、法力每點 "
        f"+{allowance.mana_per_point}‰（耐力 {allowance.stamina_per_mana} 點折合法力 1 點）；"
        f"合計最多 +{allowance.total_cap}‰",
        "沒有冷卻的技能不能用大範圍形狀（互斥規則）",
    )
    return _step(
        "cost",
        draft,
        library,
        tuple(fields),
        notes,
        description=cost_step_text(draft.get("category")),
    )


# ---------------------------------------------------------------------------
# 7. 稀有度
# ---------------------------------------------------------------------------


class RarityFloor:
    """最低稀有度與原因（中文）。"""

    def __init__(self, minimum: str, reasons: tuple[str, ...]) -> None:
        self.minimum = minimum
        self.reasons = reasons


def minimum_rarity(skill: SkillDef, library: ContentLibrary) -> RarityFloor:
    """技能的最低稀有度：:func:`rarity_requirements`（形狀、骨架、觸發、原語、狀態、條件、失手反噬）、
    效果數量（``skill_budget.yaml`` 的 ``rarity.*.max_effects``）、雙屬性縮放
    （``core.dual_scaling_min_rarity``）中最高的；傳說另外要有源力代價與傳說核心。"""
    needs: list[tuple[str, str]] = [
        (n.minimum, f"{n.what}：至少{RARITY_TEXT[n.minimum]}")
        for n in rarity_requirements(skill, library)
    ]
    count = len(skill.effects)
    limits = {str(r): v.max_effects for r, v in library.budget.rarity.items()}
    fits = [r for r in RARITY_ORDER if limits.get(r, 0) >= count]
    if fits and fits[0] != "common":
        needs.append((fits[0], f"{count} 個效果：至少{RARITY_TEXT[fits[0]]}"))
    if skill.secondary_scaling_attr is not None:
        dual = library.ruleset.core.dual_scaling_min_rarity
        needs.append((dual, f"雙屬性縮放：至少{RARITY_TEXT[dual]}"))
    if skill.cost.source is not None:
        needs.append(("legendary", "花源力：傳說"))
    minimum = max((n[0] for n in needs), key=rarity_rank, default="common")
    reasons = tuple(dict.fromkeys(text for rarity, text in needs if rarity == minimum))
    return RarityFloor(minimum, reasons if minimum != "common" else ())


def _rarity_max_effects(library: ContentLibrary, rarity: str) -> int:
    return {str(r): v.max_effects for r, v in library.budget.rarity.items()}[rarity]


_STEP_NO_MARK = "\0"
"""``_definition_errors`` 留在備註後面的欄位名記號，由 ``_with_step_links`` 換成步驟編號。"""


_FIELD_ALIAS = {"secondary_scaling_attr": "scaling_attr", "mastery": "scaling_attr"}
"""第二屬性與專精出錯多半是前面的縮放屬性或類別改了：指回基本設定。"""


def _definition_errors(draft: Draft, rarity: str, library: ContentLibrary) -> list[str]:
    """試組失敗的原因（每條一行，尾端帶 ``_STEP_NO_MARK`` ＋ 欄位名）。"""
    try:
        build_skill(draft, {"rarity": rarity})
    except DraftError as exc:
        return [f"．{plainify(m, library)}{_STEP_NO_MARK}{m}" for m in exc.messages]
    return []


_NAME = re.compile(r"[a-z_]{3,}")


def _owner_step(raw: str, owner: dict[str, int]) -> int | None:
    """試組錯誤（原始訊息）屬於哪一步：先看訊息開頭的欄位路徑（``trap.shape``、``effects[0].dice``、
    ``variants[1].shape`` 都算它的第一段），沒有的話找訊息裡第一個出現的欄位名（3-48h）。"""
    head = raw.split("：", maxsplit=1)[0].split(" ", maxsplit=1)[0]
    candidates = [head.split(".")[0].split("[")[0], *_NAME.findall(raw)]
    for name in candidates:
        step = owner.get(_FIELD_ALIAS.get(name, name))
        if step is not None:
            return step
    return None


def _rarity_step(draft: Draft, library: ContentLibrary) -> StepOptions:
    paid = _mapping(draft.get("cost")).get("source") is not None
    candidates = ("legendary",) if paid else tuple(r for r in RARITY_ORDER if r != "legendary")
    floor_skill = _probe(draft, {"rarity": candidates[0]})
    floor = minimum_rarity(floor_skill, library) if floor_skill is not None else None
    choices: list[Choice] = []
    for rarity in candidates:
        if floor is not None and rarity_rank(rarity) < rarity_rank(floor.minimum):
            continue
        if _probe(draft, {"rarity": rarity}) is None:
            continue
        choices.append(
            Choice(
                value=rarity,
                name_zh=RARITY_TEXT[rarity],
                info={"max_effects": _rarity_max_effects(library, rarity)},
            )
        )
    field = FieldSpec(
        field="rarity",
        name_zh="稀有度",
        description_zh="稀有度不增加強度，只決定能用哪些機制",
        type="choice",
        required=True,
        choices=tuple(choices),
    )
    notes: list[str] = []
    if floor is not None:
        notes.append(f"最低稀有度：{RARITY_TEXT[floor.minimum]}")
        notes += floor.reasons
    else:
        notes.append("技能定義還有錯誤，無法推導稀有度：")
        notes += _definition_errors(draft, candidates[0], library)
    if not paid:
        notes.append("傳說技能要在代價步驟填源力")
    dual = library.ruleset.core.dual_scaling_min_rarity
    notes.append(f"第二縮放屬性（法術技）至少{RARITY_TEXT[dual]}；專精與第二屬性只能擇一")
    extras = scaling_extra_fields(draft, library)
    return _step("rarity", draft, library, (field, *extras), tuple(notes))


# ---------------------------------------------------------------------------
# 組合
# ---------------------------------------------------------------------------


def _variants_step(draft: Draft, library: ContentLibrary, skeleton: SkeletonDef) -> StepOptions:
    def shapes(d: Draft, lib: ContentLibrary, sk: SkeletonDef) -> tuple[Choice, ...]:
        return _shape_step(d, lib, sk).fields[0].choices

    fields = variant_fields(draft, library, skeleton, _effect_choices, shapes)
    return _step("variants", draft, library, fields, variant_notes(draft, library))


def _build_step(
    step: StepId, draft: Draft, library: ContentLibrary, skeleton: SkeletonDef | None
) -> StepOptions:
    if step == "skeleton" or skeleton is None:
        return _skeleton_step(draft, library)
    builders = {
        "basics": lambda: _basics_step(draft, library, skeleton),
        "shape": lambda: _shape_step(draft, library, skeleton),
        "effects": lambda: _effects_step(draft, library, skeleton),
        "followup": lambda: _followup_step(draft, library),
        "condition": lambda: _condition_step(draft, library, skeleton),
        "cost": lambda: _cost_step(draft, library),
        "rarity": lambda: _rarity_step(draft, library),
        "variants": lambda: _variants_step(draft, library, skeleton),
    }
    return builders[step]()


def _held_weapon_name(weapon_id: str, weapon_req: object, library: ContentLibrary) -> str | None:
    """有主角時的縮放屬性顯示（Phase 3-48b）：「看手上武器（目前：長劍＝力量）」，雙屬性照武器的
    ``attr_mode`` 寫（取較高／取平均）。武器不存在、或武器大類與技能的武器需求不合時回 ``None``
    （退回沒有主角的寫法）。"""
    weapon = library.weapons.get(weapon_id)
    if weapon is None or weapon.weapon_class != weapon_req:
        return None
    return f"看手上武器（目前：{weapon.name_zh}＝{weapon.scaling_names_zh()}）"


def _with_held_weapon(
    steps: list[StepOptions], draft: Draft, weapon_id: str, library: ContentLibrary
) -> list[StepOptions]:
    name = _held_weapon_name(weapon_id, draft.get("weapon_req"), library)
    if name is None or draft.get("category") != "weapon":
        return steps

    def fix(field: FieldSpec) -> FieldSpec:
        if field.field != "scaling_attr" or not field.choices:
            return field
        choice = field.choices[0].model_copy(update={"name_zh": name})
        return field.model_copy(update={"choices": (choice,)})

    return [s.model_copy(update={"fields": tuple(fix(f) for f in s.fields)}) for s in steps]


def _field_names(fields: tuple[FieldSpec, ...]) -> Iterator[str]:
    """步驟欄位的第一段欄位名，含選項專屬的參數（例：``weapon_req`` 是類別的參數）。"""
    for spec in fields:
        yield spec.field.split(".")[0]
        yield from _field_names(spec.fields)
        for choice in spec.choices:
            if choice.params and spec.type != "effects":
                yield from _field_names(choice.params)


def _with_step_links(steps: list[StepOptions], library: ContentLibrary) -> list[StepOptions]:
    """備註換成中文，並把試組錯誤附上「回到第 N 步修改」（編號同步驟列）。"""
    owner: dict[str, int] = {}
    for number, step in enumerate(steps, 1):
        for name in _field_names(step.fields):
            owner.setdefault(name, number)
    out: list[StepOptions] = []
    broken: set[int] = set()  # 有試組錯誤的所屬步驟（不打勾）
    for number, step in enumerate(steps, 1):
        notes: list[str] = []
        for note in step.notes_zh:
            text, mark, raw = note.partition(_STEP_NO_MARK)
            text = plainify(text, library)
            step_no = _owner_step(raw, owner) if mark else None
            if step_no is not None:
                text += f"（回到第 {step_no} 步修改）"
                if step_no != number:
                    broken.add(step_no)
            notes.append(text)
        fields = playerize(step.fields, library)  # 說明換成玩家版（原文在 dev_description_zh）
        out.append(step.model_copy(update={"notes_zh": tuple(notes), "fields": fields}))
    return [
        s.model_copy(update={"complete": False}) if n in broken else s for n, s in enumerate(out, 1)
    ]


def _effect_fixes(
    steps: list[StepOptions], draft: Draft, library: ContentLibrary
) -> tuple[EffectFix, ...]:
    """已加入的效果對象不合法時的修正建議（3-48h）；效果步驟還沒出現時沒有。"""
    for step in steps:
        for spec in step.fields:
            if spec.field == "effects" and spec.type == "effects":
                return effect_fixes(draft, library, spec.choices)
    return ()


def draft_options(
    draft: Draft, library: ContentLibrary, *, weapon: str | None = None
) -> DraftOptions:
    """組到一半的技能 → 每個前置步驟都完成的步驟與其合法選項（純函式；相同輸入必得相同結果）。
    ``weapon``（選填，Phase 3-48b）：主角目前手上武器的 ID；有值時武器技的縮放屬性顯示手上武器。"""
    skeleton = draft_skeleton(draft, library)
    steps: list[StepOptions] = []
    problems: list[str] = []
    next_step: StepId | None = None
    for step_id in STEP_IDS:
        if step_id == "followup" and not followup_visible(draft):
            continue  # 只有位移技能能接動作段
        if step_id == "variants" and not variants_visible(draft, library):
            continue  # 只有稀有以上的主動技能能帶變奏
        step = _build_step(step_id, draft, library, skeleton)
        found = field_problems(step.fields, draft)
        steps.append(step)
        problems += found
        if not step.complete:
            next_step = step_id
            break
        if found:  # 已填的值不在選項內：步驟列不打勾（流程照舊，錯誤列在「已填的內容和選項不符」）
            steps[-1] = step.model_copy(update={"complete": False})
    if weapon is not None:
        steps = _with_held_weapon(steps, draft, weapon, library)
    fixes = _effect_fixes(steps, draft, library)
    steps = _with_step_links(steps, library)
    return DraftOptions(
        steps=tuple(steps), next_step=next_step, problems=tuple(problems), effect_fixes=fixes
    )
