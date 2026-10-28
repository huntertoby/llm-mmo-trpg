"""可玩種族與出身（Phase 3R-1，``docs/design/07-角色成長.md`` 7.7；玩法決定 #61）。

對應資料檔：

- ``content/races.yaml``（:class:`RaceTable`）：10 個人形種族，各 1 招種族技、1 項環境被動、
  預設外觀。
- ``content/origins.yaml``（:class:`OriginTable`）：碎界五區出身（預設外觀、開場劇情鍵、NPC 態度）。

**防止種族變成最佳解**（7.7 的 5 條原則）寫成載入時的驗證規則，違反時以繁體中文說明原因：

1. 不給純數值：資料中不得出現傷害、命中、暴擊、最大 HP、AP、屬性的欄位
   （:func:`forbidden_key_problems`）。
2. 只給功能型效果：種族技的效果類型、環境被動的規則都是封閉清單（:data:`RACE_EFFECT_SPECS`、
   :data:`PASSIVE_RULE_SPECS`），每個類型只能填它自己的參數。
3. 強度小於半個技能欄：種族技固定 1 AP、每場 1～2 次、不佔技能欄、效果最多 3 個、不加傷害
   （推、拉不吃撞擊傷害；投擲不造成傷害）。
4. 不給元素專屬機制（6.33）：此條無法機器檢查，由玩法 PM 審資料（見 3R-1 報告）。
5. 主城重選種族是大世界功能，不在此處。

出身**不影響戰鬥**：:class:`OriginDef` 沒有任何數值欄位，``extra="forbid"`` 與同一套禁用鍵檢查擋掉。
本模組只有資料與驗證，不含引擎結算（3R-2）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel
from trpg.content.skills import ShapeSpec
from trpg.shared.types import Element, Surface

__all__ = [
    "MAX_RACE_EFFECTS",
    "MAX_RACE_USES",
    "PASSIVE_RULE_SPECS",
    "RACE_EFFECT_SPECS",
    "OriginDef",
    "OriginTable",
    "RaceDef",
    "RaceLook",
    "RacePassive",
    "RaceSkill",
    "RaceTable",
    "forbidden_key_problems",
    "race_reference_problems",
]

MAX_RACE_USES = 2
"""種族技每場次數上限（7.7：每場限用 1～2 次）。"""
MAX_RACE_EFFECTS = 3
"""種族技的效果個數上限（強度小於半個技能欄）。"""
RACE_SKILL_AP = 1
"""種族技固定花費的 AP。"""
MAX_SIGHT_REDUCTION_PERMILLE = 500
"""視線懲罰減免上限（‰；最多減半）。"""
MAX_RESIST_PERMILLE = 250
"""環境被動的元素傷害減免上限（‰；龍裔 −20% 為 200）。"""

# ---------------------------------------------------------------------------
# 原則 1：禁用欄位
# ---------------------------------------------------------------------------

_FORBIDDEN_KEYS: dict[str, str] = {
    **dict.fromkeys(
        (
            "damage",
            "dice",
            "collision_dice",
            "multiplier_permille",
            "damage_permille",
            "damage_multiplier_permille",
            "extra_damage",
            "bonus_damage",
            "lifesteal_permille",
        ),
        "傷害",
    ),
    **dict.fromkeys(("hit", "accuracy", "hit_bonus", "hit_permille", "attack_bonus"), "命中"),
    **dict.fromkeys(
        ("crit", "crit_range", "crit_bonus", "crit_permille", "next_attack_crit"), "暴擊"
    ),
    **dict.fromkeys(("hp", "max_hp", "max_hp_permille", "hp_bonus", "heal", "shield"), "最大 HP"),
    **dict.fromkeys(("ap", "ap_bonus", "grant_ap", "extra_ap", "ap_max"), "AP"),
    **dict.fromkeys(
        ("attrs", "attributes", "attr_bonus", "stats", "str", "dex", "con", "int", "wis", "cha"),
        "屬性",
    ),
}
"""禁用欄位名（小寫）→ 對應的「純數值」類別。"""

_FORBIDDEN_EFFECT_TYPES: dict[str, str] = {
    "damage": "傷害",
    "delayed_damage": "傷害",
    "detonate_runes": "傷害",
    "charge_through": "傷害",
    "grant_ap": "AP",
    "extra_reaction": "AP",
    "cheat_death": "最大 HP",
    "heal": "最大 HP",
    "shield": "最大 HP",
    "revive": "最大 HP",
}


def forbidden_key_problems(data: object, where: str) -> list[str]:
    """遞迴找出資料中的禁用欄位，回傳中文原因（依鍵排序，確定性）。"""
    problems: list[str] = []
    if isinstance(data, Mapping):
        for key in sorted(data, key=str):
            value = data[key]
            kind = _FORBIDDEN_KEYS.get(str(key).lower())
            if kind is not None:
                problems.append(
                    f"{where}.{key}：種族不得給{kind}（防最佳解原則 1：不給純數值，"
                    "不加傷害、命中、暴擊、最大 HP、AP、屬性）"
                )
            elif key == "type" and isinstance(value, str) and value in _FORBIDDEN_EFFECT_TYPES:
                problems.append(
                    f"{where}.type：效果「{value}」會給{_FORBIDDEN_EFFECT_TYPES[value]}，"
                    "種族技只能做功能型效果（位移、環境互動、感知、防守一次）"
                )
            problems += forbidden_key_problems(value, f"{where}.{key}")
    elif isinstance(data, list | tuple):
        for index, item in enumerate(data):
            problems += forbidden_key_problems(item, f"{where}[{index}]")
    return problems


class _GuardedModel(ContentModel):
    """載入前先跑禁用欄位檢查，讓錯誤原因是中文而不是「多餘欄位」。"""

    @model_validator(mode="before")
    @classmethod
    def _no_pure_numbers(cls, data: Any) -> Any:
        problems = forbidden_key_problems(data, cls.__name__) if isinstance(data, Mapping) else []
        if problems:
            raise ValueError("；".join(problems))
        return data


# ---------------------------------------------------------------------------
# 外觀
# ---------------------------------------------------------------------------

_COLOR = r"^#[0-9a-fA-F]{6}$"


class RaceLook(ContentModel):
    """預設外觀參數（顯示用，不進引擎結算）；欄位照 ``docs/art/sample/raceArt.js`` 的 ``look``
    （駝峰改底線）。

    ``hair``／``ears``／``horns``／``tail``／``pattern``／``build`` 的值由 3R-3 的前端決定畫法；
    這裡只擋非 ID 值。顏色為 ``#rrggbb``。省略＝部件不存在。
    """

    skin: str = Field(pattern=_COLOR)
    hair: str | None = Field(default=None, pattern=ID_PATTERN)
    hair_color: str | None = Field(default=None, pattern=_COLOR)
    ears: str | None = Field(default=None, pattern=ID_PATTERN)
    horns: str | None = Field(default=None, pattern=ID_PATTERN)
    horn_color: str | None = Field(default=None, pattern=_COLOR)
    tail: str | None = Field(default=None, pattern=ID_PATTERN)
    tail_color: str | None = Field(default=None, pattern=_COLOR)
    pattern: str | None = Field(default=None, pattern=ID_PATTERN)
    mark_color: str | None = Field(default=None, pattern=_COLOR)
    eyes: str | None = Field(default=None, pattern=_COLOR)
    build: str | None = Field(default=None, pattern=ID_PATTERN)
    beard: bool = False
    tusks: bool = False
    scale_color: str | None = Field(default=None, pattern=_COLOR)
    """龍裔鱗色（定案版：依元素或出身，紅 #c8402a／藍 #3a78c8／金 #d8a830）。"""
    slit_eyes: bool = False
    ridge: bool = False
    spines: bool = False


# ---------------------------------------------------------------------------
# 種族技
# ---------------------------------------------------------------------------

type RaceEffectType = Literal[
    "bonus_move",
    "ignore_opportunity_attack",
    "conceal_self",
    "decoy",
    "push",
    "pull",
    "immovable",
    "restore_choice",
    "hurl_object",
    "create_surface",
]


@dataclass(frozen=True)
class EffectSpecRule:
    """一種種族技效果類型的參數規則。"""

    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    """必須明寫為 ``true`` 的旗標（例如推擊不吃撞擊傷害）。"""


RACE_EFFECT_SPECS: dict[str, EffectSpecRule] = {
    "bonus_move": EffectSpecRule(required=("amount",)),
    "ignore_opportunity_attack": EffectSpecRule(optional=("duration",)),
    "conceal_self": EffectSpecRule(optional=("requires",)),
    "decoy": EffectSpecRule(required=("range",)),
    "push": EffectSpecRule(required=("distance",), flags=("no_collision_damage",)),
    "pull": EffectSpecRule(required=("distance",), flags=("no_collision_damage",)),
    "immovable": EffectSpecRule(required=("duration",)),
    "restore_choice": EffectSpecRule(required=("resources", "amount")),
    "hurl_object": EffectSpecRule(required=("range",), flags=("no_damage",)),
    "create_surface": EffectSpecRule(required=("surface", "duration")),
}
"""種族技允許的效果類型（封閉清單；3R-2 照此結算）。其中 ``push``／``pull``／``create_surface``／
``hurl_object`` 對應現有原語，其餘為種族技專用的功能型效果。"""

_EFFECT_PARAM_FIELDS = (
    "amount",
    "distance",
    "duration",
    "range",
    "surface",
    "resources",
    "requires",
    "no_collision_damage",
    "no_damage",
)


class RaceEffect(ContentModel):
    """種族技的一個效果。哪些參數合法由 :data:`RACE_EFFECT_SPECS` 決定。"""

    type: RaceEffectType
    amount: int | None = Field(default=None, ge=1, le=10)
    distance: int | None = Field(default=None, ge=1, le=2)
    duration: int | None = Field(default=None, ge=1, le=10)
    range: int | None = Field(default=None, ge=1, le=6)
    surface: Surface | None = None
    resources: tuple[Literal["stamina", "mana"], ...] | None = None
    """``restore_choice``：擇一回復的資源。"""
    requires: tuple[Literal["grass", "darkness"], ...] | None = None
    """``conceal_self``：站在這些地形／表面上才能用。"""
    no_collision_damage: bool | None = None
    no_damage: bool | None = None

    @model_validator(mode="after")
    def _check_params(self) -> RaceEffect:
        rule = RACE_EFFECT_SPECS[self.type]
        allowed = set(rule.required) | set(rule.optional) | set(rule.flags)
        problems: list[str] = []
        for name in _EFFECT_PARAM_FIELDS:
            value = getattr(self, name)
            if name in rule.required and value is None:
                problems.append(f"缺少必填參數 {name}")
            elif name in rule.flags and value is not True:
                problems.append(f"{name} 必須明寫為 true（種族技不加傷害）")
            elif value is not None and name not in allowed:
                problems.append(f"不可使用參數 {name}")
        if self.type == "create_surface" and self.surface in (None, Surface.NONE):
            problems.append("surface 必須是實際的表面")
        if self.resources is not None and (
            not self.resources or len(set(self.resources)) != len(self.resources)
        ):
            problems.append("resources 不可為空或重複")
        if problems:
            raise ValueError(f"效果 {self.type}：" + "；".join(problems))
        return self


class RaceSkill(_GuardedModel):
    """種族技：主動、1 AP、每場限用 1～2 次、不佔技能欄、不加傷害（7.7）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    ap_cost: int = RACE_SKILL_AP
    uses_per_battle: int
    occupies_skill_slot: bool = False
    shape: ShapeSpec
    effects: tuple[RaceEffect, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_rules(self) -> RaceSkill:
        problems: list[str] = []
        if self.ap_cost != RACE_SKILL_AP:
            problems.append(f"種族技必須固定花 {RACE_SKILL_AP} AP，收到 {self.ap_cost}")
        if not 1 <= self.uses_per_battle <= MAX_RACE_USES:
            problems.append(f"種族技每場限用 1～{MAX_RACE_USES} 次，收到 {self.uses_per_battle}")
        if self.occupies_skill_slot:
            problems.append("種族技不佔技能欄（occupies_skill_slot 必須為 false）")
        if len(self.effects) > MAX_RACE_EFFECTS:
            problems.append(f"種族技最多 {MAX_RACE_EFFECTS} 個效果（強度小於半個技能欄）")
        if problems:
            raise ValueError(f"種族技 {self.id}：" + "；".join(problems))
        return self


# ---------------------------------------------------------------------------
# 環境被動
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassiveRule:
    """一種環境被動規則的參數規則。"""

    required: tuple[str, ...]


PASSIVE_RULE_SPECS: dict[str, PassiveRule] = {
    "sight_penalty_reduction": PassiveRule(("weathers", "permille")),
    "sight_bonus_on_terrain": PassiveRule(("terrain", "amount")),
    "detect_hidden_nearby": PassiveRule(("radius",)),
    "damage_taken_permille": PassiveRule(("element", "permille")),
    "slip_immunity": PassiveRule(("surfaces",)),
    "conduction_immunity": PassiveRule(("surfaces",)),
    "knockback_reduction_at_hazard": PassiveRule(("terrain", "amount")),
    "burn_immunity_on": PassiveRule(("surfaces",)),
    "free_move_on": PassiveRule(("surfaces",)),
    "weather_move_bonus": PassiveRule(("weathers", "amount")),
}
"""環境被動允許的規則（封閉清單，只有環境互動的小規則；3R-2 照此結算）。"""

_PASSIVE_PARAM_FIELDS = (
    "weathers",
    "terrain",
    "surfaces",
    "element",
    "permille",
    "amount",
    "radius",
)


class RacePassive(_GuardedModel):
    """環境被動：一條環境互動的小規則；不給數值（7.7 原則 1、2）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    rule: str = Field(pattern=ID_PATTERN)
    weathers: tuple[str, ...] | None = None
    terrain: tuple[str, ...] | None = None
    surfaces: tuple[Surface, ...] | None = None
    element: Element | None = None
    permille: int | None = None
    amount: int | None = Field(default=None, ge=1, le=2)
    radius: int | None = Field(default=None, ge=1, le=3)

    @model_validator(mode="after")
    def _check_rule(self) -> RacePassive:
        rule = PASSIVE_RULE_SPECS.get(self.rule)
        if rule is None:
            known = "、".join(sorted(PASSIVE_RULE_SPECS))
            raise ValueError(
                f"環境被動 {self.id}：規則 {self.rule!r} 不在允許清單內"
                f"（只允許環境互動的小規則：{known}）"
            )
        problems: list[str] = []
        for name in _PASSIVE_PARAM_FIELDS:
            value = getattr(self, name)
            if name in rule.required and value is None:
                problems.append(f"缺少必填參數 {name}")
            elif value is not None and name not in rule.required:
                problems.append(f"不可使用參數 {name}")
        problems += self._permille_problems()
        if problems:
            raise ValueError(f"環境被動 {self.id}：" + "；".join(problems))
        return self

    def _permille_problems(self) -> list[str]:
        if self.permille is None:
            return []
        if (
            self.rule == "sight_penalty_reduction"
            and not 0 < self.permille <= MAX_SIGHT_REDUCTION_PERMILLE
        ):
            return ["permille 必須在 1～500（視線懲罰最多減半）"]
        if self.rule == "damage_taken_permille" and not -MAX_RESIST_PERMILLE <= self.permille < 0:
            return [f"permille 必須為 −{MAX_RESIST_PERMILLE}～−1（只能減傷，幅度有上限）"]
        return []


# ---------------------------------------------------------------------------
# 種族與出身
# ---------------------------------------------------------------------------


class RaceDef(_GuardedModel):
    """一個可玩種族。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    home_realm: str = Field(pattern=ID_PATTERN)
    """代表界域（``regions.yaml`` 的區域 ID）；只是預設，出身可另選。"""
    skill: RaceSkill
    passive: RacePassive
    look: RaceLook


class RaceTable(ContentModel):
    """``content/races.yaml``。"""

    races: tuple[RaceDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> RaceTable:
        problems: list[str] = []
        for label, ids in (
            ("種族", [r.id for r in self.races]),
            ("種族技", [r.skill.id for r in self.races]),
            ("環境被動", [r.passive.id for r in self.races]),
        ):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                problems.append(f"{label} ID 重複：{'、'.join(dup)}")
        if problems:
            raise ValueError("；".join(problems))
        return self

    def by_id(self) -> dict[str, RaceDef]:
        return {r.id: r for r in self.races}

    def summary(self) -> str:
        return f"{len(self.races)} 個種族（各 1 招種族技＋1 項環境被動）"


type NpcAttitude = Literal["friendly", "neutral", "wary"]


class OriginLook(ContentModel):
    """出身的預設外觀（疊在種族外觀上；顯示用）。"""

    outfit_tint: str = Field(pattern=_COLOR)
    hair_color: str | None = Field(default=None, pattern=_COLOR)
    accent: str | None = Field(default=None, pattern=_COLOR)


class OriginDef(_GuardedModel):
    """一個出身（碎界界域）：外觀、開場劇情鍵、NPC 態度；**不影響戰鬥**。"""

    id: str = Field(pattern=ID_PATTERN)
    realm: str = Field(pattern=ID_PATTERN)
    """``regions.yaml`` 的區域 ID。"""
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    default_look: OriginLook
    opening_key: str = Field(pattern=ID_PATTERN)
    """開場劇情鍵（由敘事層對應內容；LLM 只寫出身故事，7.7）。"""
    npc_attitude: dict[str, NpcAttitude] = Field(default_factory=dict)
    """各界域 NPC 對玩家的態度（鍵為區域 ID）。"""


class OriginTable(ContentModel):
    """``content/origins.yaml``。"""

    origins: tuple[OriginDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> OriginTable:
        ids = [o.id for o in self.origins]
        realms = [o.realm for o in self.origins]
        problems: list[str] = []
        if len(set(ids)) != len(ids):
            problems.append("出身 ID 重複")
        if len(set(realms)) != len(realms):
            problems.append("每個界域只能有一個出身")
        if problems:
            raise ValueError("；".join(problems))
        return self

    def by_id(self) -> dict[str, OriginDef]:
        return {o.id: o for o in self.origins}

    def summary(self) -> str:
        return f"{len(self.origins)} 個出身（不影響戰鬥）"


# ---------------------------------------------------------------------------
# 跨檔案檢查
# ---------------------------------------------------------------------------


def race_reference_problems(
    races: RaceTable,
    origins: OriginTable,
    *,
    region_ids: frozenset[str],
    shape_ids: frozenset[str],
    weather_ids: frozenset[str],
    terrain_ids: frozenset[str],
) -> list[str]:
    """種族與出身引用的界域、形狀、天氣、地形都要存在；每個界域恰有一個出身。"""
    problems: list[str] = []
    for race in races.races:
        if race.home_realm not in region_ids:
            problems.append(f"種族 {race.id}：未知的界域 {race.home_realm}")
        if race.skill.shape.type not in shape_ids:
            problems.append(f"種族技 {race.skill.id}：未知的形狀 {race.skill.shape.type}")
        passive = race.passive
        bad_weather = sorted(set(passive.weathers or ()) - weather_ids)
        if bad_weather:
            problems.append(f"環境被動 {passive.id}：未知的天氣 {'、'.join(bad_weather)}")
        bad_terrain = sorted(set(passive.terrain or ()) - terrain_ids)
        if bad_terrain:
            problems.append(f"環境被動 {passive.id}：未知的地形 {'、'.join(bad_terrain)}")
    for origin in origins.origins:
        if origin.realm not in region_ids:
            problems.append(f"出身 {origin.id}：未知的界域 {origin.realm}")
        bad = sorted(set(origin.npc_attitude) - region_ids)
        if bad:
            problems.append(f"出身 {origin.id}：npc_attitude 有未知的界域 {'、'.join(bad)}")
    missing = sorted(region_ids - {o.realm for o in origins.origins})
    if missing:
        problems.append(f"這些界域沒有出身：{'、'.join(missing)}")
    return problems
