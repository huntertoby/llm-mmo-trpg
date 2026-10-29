"""技能系統的內容 schema（``docs/phases/Phase2A計畫.md`` 第 3 節、``docs/design/06-技能.md``）。

對應資料檔：

- ``content/skill_shapes.yaml``：目標形狀（``ShapeTable``）。
- ``content/skill_primitives.yaml``：效果原語（``PrimitiveTable``）。
- ``content/skills/<id>.yaml``：一個檔一個技能（``SkillDef``）。

載入時的驗證分兩層：

1. **schema 內** 的驗證（與其他資料表無關）：欄位範圍、``kind`` 與 ``ap_cost``、``category`` 與
   ``weapon_req``、效果數量、推擊距離等。違反時的訊息為繁體中文。
2. **跨檔案** 的驗證（:func:`skill_problems`）：形狀與原語存在、參數在資料檔定義的範圍內、
   引用的狀態／表面／物件存在。由 :func:`trpg.content.library.load_library` 呼叫。

技能是獨立實體（``docs/design/17-未來展望.md`` 17.5）：``provenance`` 記錄來源、擁有者、是否綁定
與可否交易。2A 只存不用。
"""

from __future__ import annotations

from trpg.content.skills.conditions import (
    ConditionSpec,
    ConditionTable,
    condition_text,
)
from trpg.content.skills.conditions import (
    _rune_condition_text as _rune_condition_text,
)
from trpg.content.skills.conditions import (
    _unknown_tag as _unknown_tag,
)
from trpg.content.skills.constants import (
    _CHANGES as _CHANGES,
)
from trpg.content.skills.constants import (
    _ELEMENT_VALUES as _ELEMENT_VALUES,
)
from trpg.content.skills.constants import (
    _GAMBLE_ONLY_FIELDS as _GAMBLE_ONLY_FIELDS,
)
from trpg.content.skills.constants import (
    _GROUP_NAMES as _GROUP_NAMES,
)
from trpg.content.skills.constants import (
    _MAX_AP_COST as _MAX_AP_COST,
)
from trpg.content.skills.constants import (
    _MAX_BRANCH_EFFECTS as _MAX_BRANCH_EFFECTS,
)
from trpg.content.skills.constants import (
    _MAX_CONSUME_THEN as _MAX_CONSUME_THEN,
)
from trpg.content.skills.constants import (
    _MAX_COOLDOWN as _MAX_COOLDOWN,
)
from trpg.content.skills.constants import (
    _MAX_COOLDOWN_RESTORE as _MAX_COOLDOWN_RESTORE,
)
from trpg.content.skills.constants import (
    _MAX_DISPLACE as _MAX_DISPLACE,
)
from trpg.content.skills.constants import (
    _MAX_MASTERY_MODIFIERS as _MAX_MASTERY_MODIFIERS,
)
from trpg.content.skills.constants import (
    _MAX_MODIFIERS as _MAX_MODIFIERS,
)
from trpg.content.skills.constants import (
    _MAX_MULTIPLIER_PERMILLE as _MAX_MULTIPLIER_PERMILLE,
)
from trpg.content.skills.constants import (
    _MAX_ON_HIT_EFFECTS as _MAX_ON_HIT_EFFECTS,
)
from trpg.content.skills.constants import (
    _MAX_VARIANT_REPLACEMENTS as _MAX_VARIANT_REPLACEMENTS,
)
from trpg.content.skills.constants import (
    _MAX_ZONE_EFFECTS as _MAX_ZONE_EFFECTS,
)
from trpg.content.skills.constants import (
    _PERMILLE as _PERMILLE,
)
from trpg.content.skills.constants import (
    _PLAIN_CONDITION_TEXT as _PLAIN_CONDITION_TEXT,
)
from trpg.content.skills.constants import (
    _REQ_NAMES as _REQ_NAMES,
)
from trpg.content.skills.constants import (
    _VARIANT_REPLACEMENTS as _VARIANT_REPLACEMENTS,
)
from trpg.content.skills.constants import (
    _ZONE_ONLY_FIELDS as _ZONE_ONLY_FIELDS,
)
from trpg.content.skills.constants import (
    ADD_STACK,
    AFFECTS_VALUES,
    BACKLASH_TYPES,
    BASIC_ACTIONS,
    BLOW_SURFACE,
    CASTER_CONDITIONS,
    CHANGE_TARGETS,
    CHARGE_THROUGH,
    CHARGING,
    CHEAT_DEATH,
    CHEAT_DEATH_STATUS,
    COMPOSITE_KIND_ZH,
    COMPOSITE_MOVES,
    CONSUME_STACK,
    CONSUME_STATUS,
    CONSUME_THEN_TYPES,
    COPY_SKILL,
    DAMAGE_MULTIPLIER,
    DASH,
    DELAYED_DAMAGE,
    DELAYED_RELEASE_VALUES,
    DELAYED_SHAPES,
    DETONATE_RUNES,
    DISPEL,
    EFFECT_NON_PARAM_FIELDS,
    ENTER_FORM,
    EXTRA_REACTION,
    FOLLOWUP_AUTO_WHENS,
    FOLLOWUP_CHOICE_WHENS,
    FOLLOWUP_FORBIDDEN,
    FOLLOWUP_SHAPES,
    FOLLOWUP_WHEN_VALUES,
    GAMBLE,
    GAMBLE_BRANCH_TYPES,
    GAMBLE_TAG,
    GATHER_SHAPES,
    GRANT_AP,
    GRANT_SKILL,
    HURL_OBJECT,
    INSCRIBE,
    INTERCEPT,
    LEAP,
    LEAVE_FORM,
    LEGACY_REACTION_EVENTS,
    MAX_EFFECTS,
    MAX_GRANT_DURATION,
    MAX_MODIFIERS,
    MAX_SUMMON_COUNT,
    MAX_VARIANTS,
    MIN_SKILL_CRIT_RANGE,
    MODIFIER_CHANGES,
    NONZERO_CHANGES,
    ON_HIT_PRIMITIVES,
    ON_KILL_TYPES,
    ON_MISS_MIN_RARITY,
    PAIR_MOVES,
    PAIR_SHAPES,
    PIERCE_SHAPES,
    PLACE_TRAP,
    RARITY_ORDER,
    REDIRECT_DAMAGE,
    REDIRECT_STATUS,
    REFUND_AP,
    REFUND_COOLDOWN,
    REQUIRED_CONDITIONS,
    REQUIRED_SHAPES,
    RESET_COOLDOWN,
    REVEAL,
    REVIVE,
    RULE_CHANGE,
    SACRIFICE_SUMMON,
    SCALE_BY_VALUES,
    SELF_CONDITIONS,
    SELF_DAMAGE_OF_HIT,
    SELF_ONLY_CHANGES,
    SHADOWSTEP,
    SHAPE_REQUIRED_PRIMITIVES,
    SKELETON_IDS,
    SKILL_ID_PATTERN,
    SKILL_REACTION_EVENTS,
    SPLIT_SKELETONS,
    SUMMON,
    SWAP,
    SWAP_ANY,
    TELEPORT_TARGET,
    TIME_BOMB,
    TOPPLE,
    TRUE_ONLY_CHANGES,
    VARIANT_CONDITIONS,
    VARIANT_TARGET_CONDITIONS,
    WEAPON_CLASSES,
    WIELDING_EFFECT_ONLY,
    WIELDING_WEAPON,
    ZONE,
    ZONE_CASTER_SHAPES,
    ZONE_EFFECT_TYPES,
    ZONE_MOVING_SHAPES,
    Activation,
    Affects,
    BasicAction,
    Mastery,
    rarity_rank,
)
from trpg.content.skills.constants import (
    FOLLOWUP_CENTERED as FOLLOWUP_CENTERED,
)
from trpg.content.skills.constants import (
    FORM_CATEGORY_TEXT as FORM_CATEGORY_TEXT,
)
from trpg.content.skills.constants import (
    MAX_ON_KILL_EFFECTS as MAX_ON_KILL_EFFECTS,
)
from trpg.content.skills.constants import (
    MAX_REFUND_AP as MAX_REFUND_AP,
)
from trpg.content.skills.constants import (
    ON_CAST_TAG as ON_CAST_TAG,
)
from trpg.content.skills.constants import (
    ON_COLLISION as ON_COLLISION,
)
from trpg.content.skills.constants import (
    ON_ENTER_SURFACE as ON_ENTER_SURFACE,
)
from trpg.content.skills.constants import (
    ON_KILL_SECOND_SHAPES as ON_KILL_SECOND_SHAPES,
)
from trpg.content.skills.constants import (
    ON_STATUS_APPLIED as ON_STATUS_APPLIED,
)
from trpg.content.skills.constants import (
    ON_SUMMON_DOWNED as ON_SUMMON_DOWNED,
)
from trpg.content.skills.constants import (
    PER_TURN_LIMIT_CHANGES as PER_TURN_LIMIT_CHANGES,
)
from trpg.content.skills.constants import (
    RESTORE_RESOURCE as RESTORE_RESOURCE,
)
from trpg.content.skills.constants import (
    RUNE_BOTH_MESSAGE as RUNE_BOTH_MESSAGE,
)
from trpg.content.skills.constants import (
    SELF_MOVES as SELF_MOVES,
)
from trpg.content.skills.constants import (
    SHADOWSTEP_SHAPES as SHADOWSTEP_SHAPES,
)
from trpg.content.skills.constants import (
    SHAPE_CHANGES as SHAPE_CHANGES,
)
from trpg.content.skills.constants import (
    SHAPE_ROLES as SHAPE_ROLES,
)
from trpg.content.skills.constants import (
    SHAPE_TO_VALUES as SHAPE_TO_VALUES,
)
from trpg.content.skills.constants import (
    STEAL_BUFF as STEAL_BUFF,
)
from trpg.content.skills.constants import (
    YAML_RANGED_FIELDS as YAML_RANGED_FIELDS,
)
from trpg.content.skills.constants import (
    DelayedRelease as DelayedRelease,
)
from trpg.content.skills.constants import (
    FollowupWhen as FollowupWhen,
)
from trpg.content.skills.constants import (
    KnobLadder as KnobLadder,
)
from trpg.content.skills.constants import (
    KnobWeight as KnobWeight,
)
from trpg.content.skills.constants import (
    Origin as Origin,
)
from trpg.content.skills.constants import (
    ReactionEvent as ReactionEvent,
)
from trpg.content.skills.constants import (
    ScaleBy as ScaleBy,
)
from trpg.content.skills.constants import (
    SkillCategory as SkillCategory,
)
from trpg.content.skills.constants import (
    SkillKind as SkillKind,
)
from trpg.content.skills.constants import (
    SkillRarity as SkillRarity,
)
from trpg.content.skills.constants import (
    Targeting as Targeting,
)
from trpg.content.skills.constants import (
    WeaponReq as WeaponReq,
)
from trpg.content.skills.constants import (
    _unique as _unique,
)
from trpg.content.skills.effects import (
    EFFECT_PARAM_FIELDS,
    CompositionRule,
    EffectSpec,
    ScaleSpec,
    ShapeSpec,
    SkillRuleError,
    composition_rules,
    composition_shapes,
    true_only_params,
)
from trpg.content.skills.effects import (
    _check_composition as _check_composition,
)
from trpg.content.skills.effects import (
    _check_rule as _check_rule,
)
from trpg.content.skills.effects import (
    _composition_of as _composition_of,
)
from trpg.content.skills.effects import (
    _ranged_params_of as _ranged_params_of,
)
from trpg.content.skills.effects import (
    _true_only_of as _true_only_of,
)
from trpg.content.skills.effects import (
    _yaml_ranged_params as _yaml_ranged_params,
)
from trpg.content.skills.followup import (
    _FOLLOWUP_CHECKS as _FOLLOWUP_CHECKS,
)
from trpg.content.skills.followup import (
    _check_after_action as _check_after_action,
)
from trpg.content.skills.followup import (
    _check_after_gather as _check_after_gather,
)
from trpg.content.skills.followup import (
    _check_after_move as _check_after_move,
)
from trpg.content.skills.followup import (
    _check_delayed as _check_delayed,
)
from trpg.content.skills.followup import (
    _check_on_hit as _check_on_hit,
)
from trpg.content.skills.followup import (
    _check_on_kill as _check_on_kill,
)
from trpg.content.skills.followup import (
    _lone_move as _lone_move,
)
from trpg.content.skills.followup import (
    _needs_damage as _needs_damage,
)
from trpg.content.skills.followup import (
    _no_forbidden as _no_forbidden,
)
from trpg.content.skills.followup import (
    _second_shape as _second_shape,
)
from trpg.content.skills.followup import (
    _types as _types,
)
from trpg.content.skills.modifiers import (
    ModifierChange,
    ModifierSpec,
    ModifierTarget,
)
from trpg.content.skills.primitives import (
    ConditionDef,
    PrimitiveDef,
    PrimitiveKnob,
    PrimitiveParam,
    PrimitiveTable,
    default_affects,
)
from trpg.content.skills.problems import (
    _branch_problems as _branch_problems,
)
from trpg.content.skills.problems import (
    _condition_problems as _condition_problems,
)
from trpg.content.skills.problems import (
    _consume_status_problems as _consume_status_problems,
)
from trpg.content.skills.problems import (
    _consumer_problems as _consumer_problems,
)
from trpg.content.skills.problems import (
    _cost_stack_problems as _cost_stack_problems,
)
from trpg.content.skills.problems import (
    _count_problem as _count_problem,
)
from trpg.content.skills.problems import (
    _default_affects_of as _default_affects_of,
)
from trpg.content.skills.problems import (
    _effect_problems as _effect_problems,
)
from trpg.content.skills.problems import (
    _forbidden_affects_message as _forbidden_affects_message,
)
from trpg.content.skills.problems import (
    _gamble_problems as _gamble_problems,
)
from trpg.content.skills.problems import (
    _legendary_problems as _legendary_problems,
)
from trpg.content.skills.problems import (
    _modifier_problems as _modifier_problems,
)
from trpg.content.skills.problems import (
    _on_kill_problems as _on_kill_problems,
)
from trpg.content.skills.problems import (
    _reference_problem as _reference_problem,
)
from trpg.content.skills.problems import (
    _Refs as _Refs,
)
from trpg.content.skills.problems import (
    _scaling_problems as _scaling_problems,
)
from trpg.content.skills.problems import (
    _stack_effect_problems as _stack_effect_problems,
)
from trpg.content.skills.problems import (
    _trigger_problems as _trigger_problems,
)
from trpg.content.skills.problems import (
    _value_problem as _value_problem,
)
from trpg.content.skills.problems import (
    _zone_problems as _zone_problems,
)
from trpg.content.skills.problems import (
    granted_skill_problems,
    legendary_cores,
    param_required_for,
    skill_problems,
)
from trpg.content.skills.queries import (
    held_gear,
    is_wind_skill,
    on_hit_carrier,
    skill_elements,
    skill_slot_problems,
    weapon_problem,
)
from trpg.content.skills.reactions import (
    ReactionSpec,
    TrapSpec,
)
from trpg.content.skills.shapes import (
    ParamDef,
    RequiredWhen,
    ShapeBudget,
    ShapeCells,
    ShapeDef,
    ShapeTable,
)
from trpg.content.skills.shapes import (
    ShapeConversion as ShapeConversion,
)
from trpg.content.skills.skill import (
    _FOLLOWUP_CACHE as _FOLLOWUP_CACHE,
)
from trpg.content.skills.skill import (
    _FOLLOWUP_CACHE_LIMIT as _FOLLOWUP_CACHE_LIMIT,
)
from trpg.content.skills.skill import (
    _VARIANT_CACHE as _VARIANT_CACHE,
)
from trpg.content.skills.skill import (
    SkillDef,
    SkillTable,
)
from trpg.content.skills.skill import (
    _int_param_problems as _int_param_problems,
)
from trpg.content.skills.specs import (
    FollowupSpec,
    NarrativeDef,
    Provenance,
    SkillCost,
    TriggerSpec,
)
from trpg.content.skills.specs import (
    SelfStatusCost as SelfStatusCost,
)
from trpg.content.skills.variants import (
    VariantEffectSwap,
    VariantSpec,
    VariantWhen,
    walk_effect,
)

__all__ = [
    "ADD_STACK",
    "AFFECTS_VALUES",
    "BACKLASH_TYPES",
    "BASIC_ACTIONS",
    "BLOW_SURFACE",
    "CASTER_CONDITIONS",
    "CHANGE_TARGETS",
    "CHARGE_THROUGH",
    "CHARGING",
    "CHEAT_DEATH",
    "CHEAT_DEATH_STATUS",
    "COMPOSITE_KIND_ZH",
    "COMPOSITE_MOVES",
    "CONSUME_STACK",
    "CONSUME_STATUS",
    "CONSUME_THEN_TYPES",
    "COPY_SKILL",
    "DAMAGE_MULTIPLIER",
    "DASH",
    "DELAYED_DAMAGE",
    "DELAYED_RELEASE_VALUES",
    "DELAYED_SHAPES",
    "DETONATE_RUNES",
    "DISPEL",
    "EFFECT_NON_PARAM_FIELDS",
    "EFFECT_PARAM_FIELDS",
    "ENTER_FORM",
    "EXTRA_REACTION",
    "FOLLOWUP_AUTO_WHENS",
    "FOLLOWUP_CHOICE_WHENS",
    "FOLLOWUP_FORBIDDEN",
    "FOLLOWUP_SHAPES",
    "FOLLOWUP_WHEN_VALUES",
    "GAMBLE",
    "GAMBLE_BRANCH_TYPES",
    "GAMBLE_TAG",
    "GATHER_SHAPES",
    "GRANT_AP",
    "GRANT_SKILL",
    "HURL_OBJECT",
    "INSCRIBE",
    "INTERCEPT",
    "LEAP",
    "LEAVE_FORM",
    "LEGACY_REACTION_EVENTS",
    "MAX_EFFECTS",
    "MAX_GRANT_DURATION",
    "MAX_MODIFIERS",
    "MAX_SUMMON_COUNT",
    "MAX_VARIANTS",
    "MIN_SKILL_CRIT_RANGE",
    "MODIFIER_CHANGES",
    "NONZERO_CHANGES",
    "ON_HIT_PRIMITIVES",
    "ON_KILL_TYPES",
    "ON_MISS_MIN_RARITY",
    "PAIR_MOVES",
    "PAIR_SHAPES",
    "PIERCE_SHAPES",
    "PLACE_TRAP",
    "RARITY_ORDER",
    "REDIRECT_DAMAGE",
    "REDIRECT_STATUS",
    "REFUND_AP",
    "REFUND_COOLDOWN",
    "REQUIRED_CONDITIONS",
    "REQUIRED_SHAPES",
    "RESET_COOLDOWN",
    "REVEAL",
    "REVIVE",
    "RULE_CHANGE",
    "SACRIFICE_SUMMON",
    "SCALE_BY_VALUES",
    "SELF_CONDITIONS",
    "SELF_DAMAGE_OF_HIT",
    "SELF_ONLY_CHANGES",
    "SHADOWSTEP",
    "SHAPE_REQUIRED_PRIMITIVES",
    "SKELETON_IDS",
    "SKILL_ID_PATTERN",
    "SKILL_REACTION_EVENTS",
    "SPLIT_SKELETONS",
    "SUMMON",
    "SWAP",
    "SWAP_ANY",
    "TELEPORT_TARGET",
    "TIME_BOMB",
    "TOPPLE",
    "TRUE_ONLY_CHANGES",
    "VARIANT_CONDITIONS",
    "VARIANT_TARGET_CONDITIONS",
    "WEAPON_CLASSES",
    "WIELDING_EFFECT_ONLY",
    "WIELDING_WEAPON",
    "ZONE",
    "ZONE_CASTER_SHAPES",
    "ZONE_EFFECT_TYPES",
    "ZONE_MOVING_SHAPES",
    "Activation",
    "Affects",
    "BasicAction",
    "CompositionRule",
    "ConditionDef",
    "ConditionSpec",
    "ConditionTable",
    "EffectSpec",
    "FollowupSpec",
    "Mastery",
    "ModifierChange",
    "ModifierSpec",
    "ModifierTarget",
    "NarrativeDef",
    "ParamDef",
    "PrimitiveDef",
    "PrimitiveKnob",
    "PrimitiveParam",
    "PrimitiveTable",
    "Provenance",
    "ReactionSpec",
    "RequiredWhen",
    "ScaleSpec",
    "ShapeBudget",
    "ShapeCells",
    "ShapeDef",
    "ShapeSpec",
    "ShapeTable",
    "SkillCost",
    "SkillDef",
    "SkillRuleError",
    "SkillTable",
    "TrapSpec",
    "TriggerSpec",
    "VariantEffectSwap",
    "VariantSpec",
    "VariantWhen",
    "composition_rules",
    "composition_shapes",
    "condition_text",
    "default_affects",
    "granted_skill_problems",
    "held_gear",
    "is_wind_skill",
    "legendary_cores",
    "on_hit_carrier",
    "param_required_for",
    "rarity_rank",
    "skill_elements",
    "skill_problems",
    "skill_slot_problems",
    "true_only_params",
    "walk_effect",
    "weapon_problem",
]
