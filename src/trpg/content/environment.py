"""環境內容 schema：格子物件、表面、元素 × 標籤互動表、天氣、反應規則。

對應資料檔：``content/objects.yaml``、``content/surfaces.yaml``、``content/interactions.yaml``、
``content/weather.yaml``、``content/reactions.yaml``（``docs/專案計畫.md`` 5.1、5.2.1、5.7）。
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from fractions import Fraction
from typing import Any, Literal

from pydantic import Field, PrivateAttr, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, Dice, ReactionRule, ReactionUnless, ReactionWhen
from trpg.content.schemas import ContentModel
from trpg.content.skills import SkillDef
from trpg.shared.types import Attribute, Element, Surface

__all__ = [
    "ENV_REACTION_EVENTS",
    "OBJECT_TAGS",
    "AiProfile",
    "AiProfileTable",
    "AiWeights",
    "BasicActionAiRules",
    "ElementCapability",
    "ExplosionDef",
    "GambleAiRules",
    "InteractionOutcome",
    "InteractionRule",
    "InteractionTable",
    "ObjectDef",
    "ObjectTable",
    "OrderBonuses",
    "ReactionDef",
    "ReactionEventDef",
    "ReactionRule",
    "ReactionTable",
    "ReactionUnless",
    "ReactionWhen",
    "RunAiRules",
    "RuneAiRules",
    "SpillDef",
    "SurfaceCheck",
    "SurfaceDamage",
    "SurfaceDef",
    "SurfaceEnter",
    "SurfaceHeal",
    "SurfaceTable",
    "SurfaceTurnStart",
    "TrapAiRules",
    "WeatherDef",
    "WeatherTable",
    "ZoneAiRules",
]

OBJECT_TAGS: frozenset[str] = frozenset(
    {
        "blocks_move",  # 不可通行
        "blocks_sight",  # 阻擋視線
        "breakable",  # 可被攻擊，HP ≤ 0 時摧毀
        "conceal",  # 站在同一格的單位獲得隱蔽
        "conductive",  # 雷電可沿此擴散
        "explosive",  # 火焰觸發爆炸
        "extinguish",  # 可熄滅火焰（資料保留，Phase 1 無引擎規則使用）
        "flammable",  # 可被點燃；環境回合火勢會蔓延過來
        "freezable",  # 冰霜可使其結冰
        "meltable",  # 火焰觸及時融化（直接移除，Phase 3-11 的冰牆）
        "half_cover",  # 半掩護：遠程攻擊緊鄰其後的目標命中 −2（Phase 1C）
        "over_chasm",  # 架在致命地形上：此格變成可站立、非致命
        "pushable",  # 可被推動
        "penetrable",  # 可被穿透（木製物件；Phase 3C-5b 的 pierce 使用）
        "topplable",  # 可推倒：被推時不移動，往推的方向倒下（Phase 3C-5a）
    }
)
"""引擎認得的物件標籤。新物件只要組合這些標籤，就自動支援所有互動。"""

ENV_REACTION_EVENTS = ("targeted_by_melee", "targeted_by_attack", "enemy_leaves_adjacent")


def _unique(ids: list[str], what: str) -> None:
    dup = sorted(i for i, n in Counter(ids).items() if n > 1)
    if dup:
        raise ValueError(f"重複的{what}：{', '.join(dup)}")


def _check_glyph(value: str) -> str:
    if re.match(r"^[!-~]$", value) is None:
        raise ValueError(f"顯示字元必須是單一可見 ASCII 字元，收到 {value!r}")
    return value


# ---------------------------------------------------------------------------
# 物件
# ---------------------------------------------------------------------------


class ExplosionDef(ContentModel):
    """爆炸：以物件為中心、``radius`` 格內（切比雪夫距離，``1`` 即 3×3）的單位受到傷害，
    每一格也被 ``element`` 觸及（例如點燃 oil 表面、引爆其他油桶）。"""

    radius: int = Field(default=1, ge=0, le=5)
    dice: Dice
    flat: int = 0
    element: Element = Element.FIRE


class SpillDef(ContentModel):
    """物件被 **傷害** 打破（``destroy cause = damage``，例如物理攻擊打破油桶）時，在該格與四方向
    相鄰格產生 ``surface``（漏油）。被火焰引爆、燒毀、掉落等其他原因摧毀時不會漏出。"""

    surface: Surface

    @field_validator("surface")
    @classmethod
    def _not_none(cls, value: Surface) -> Surface:
        if value is Surface.NONE:
            raise ValueError("spill.surface 不可為 none")
        return value


class ObjectDef(ContentModel):
    """一種格子物件（``content/objects.yaml``）。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    glyph: str
    max_hp: int | None = Field(default=None, ge=1)
    tags: tuple[str, ...] = ()
    explosion: ExplosionDef | None = None
    spill: SpillDef | None = None

    @field_validator("glyph")
    @classmethod
    def _glyph(cls, value: str) -> str:
        return _check_glyph(value)

    @field_validator("tags")
    @classmethod
    def _tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        unknown = sorted(t for t in value if t not in OBJECT_TAGS)
        if unknown:
            raise ValueError(f"未知的物件標籤：{', '.join(unknown)}")
        if len(set(value)) != len(value):
            raise ValueError("標籤不可重複")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _check(self) -> ObjectDef:
        if "breakable" in self.tags and self.max_hp is None:
            raise ValueError(f"物件 {self.id}：breakable 必須設定 max_hp")
        if "explosive" in self.tags and self.explosion is None:
            raise ValueError(f"物件 {self.id}：explosive 必須設定 explosion")
        if self.spill is not None and "breakable" not in self.tags:
            raise ValueError(f"物件 {self.id}：spill 只能用於 breakable 物件")
        return self

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags


class ObjectTable(ContentModel):
    objects: tuple[ObjectDef, ...] = Field(min_length=1)

    _index: dict[str, ObjectDef] = PrivateAttr(default_factory=dict)

    def model_post_init(self, context: object, /) -> None:
        self._index = {o.id: o for o in self.objects}

    @model_validator(mode="after")
    def _check(self) -> ObjectTable:
        _unique([o.id for o in self.objects], "物件 ID")
        _unique([o.glyph for o in self.objects], "物件顯示字元")
        return self

    def by_id(self) -> dict[str, ObjectDef]:
        return dict(self._index)

    def get(self, object_id: str) -> ObjectDef:
        # 略過 BaseModel.__getattr__ 的私有屬性慢速路徑（見 Ruleset.terrain_def）
        index: dict[str, ObjectDef] = self.__pydantic_private__["_index"]  # type: ignore[index]
        return index[object_id]

    def summary(self) -> str:
        return f"{len(self.objects)} 種物件"


# ---------------------------------------------------------------------------
# 表面
# ---------------------------------------------------------------------------


class SurfaceCheck(ContentModel):
    """進入表面時的檢定：``d20 + 屬性修正 ≥ dc``，失敗時獲得 ``fail_status``。"""

    attr: Attribute
    dc: int
    fail_status: str = Field(pattern=ID_PATTERN)


class SurfaceEnter(ContentModel):
    check: SurfaceCheck | None = None
    apply_status: str | None = Field(default=None, pattern=ID_PATTERN)


class SurfaceDamage(ContentModel):
    """回合開始時的傷害。``only_tag`` 不為空時只影響帶該標籤的單位。"""

    dice: Dice
    element: Element
    only_tag: str | None = Field(default=None, pattern=ID_PATTERN)


class SurfaceHeal(ContentModel):
    """回合開始時的治療。``allies_only``：只治療與表面擁有者同陣營的單位（地圖上原有、沒有
    擁有者的表面治療所有單位）；``exclude_tag``：帶該標籤者不治療。"""

    dice: Dice
    allies_only: bool = True
    exclude_tag: str | None = Field(default=None, pattern=ID_PATTERN)


class SurfaceTurnStart(ContentModel):
    damage: SurfaceDamage | None = None
    heal: SurfaceHeal | None = None
    apply_status: str | None = Field(default=None, pattern=ID_PATTERN)


class SurfaceDef(ContentModel):
    """一種表面（``content/surfaces.yaml``）。

    - ``duration``：由效果產生時的持續輪數（環境回合 −1，歸零變成 ``expires_to``）；
      ``None`` 為永久。
      地圖上原有的表面預設永久（地圖檔可另行指定）。
    - ``element``：表面本身帶的元素（例如 fire 表面 = 火焰）；產生此表面時，格上物件會被該元素觸及。
    - ``flammable``：環境回合火表面會蔓延到這種表面（例如 oil）。
    - ``blocks_sight``：視線穿越時被阻擋（兩端除外）；``conceal``：站在上面的單位獲得隱蔽。
    - ``budget_points``：技能產生此表面（預設持續時間）的預算點數（2B-2）；
      ``None`` 表示不能由技能產生。
    - ``beneficial``（2B-3）：對站在上面的友方有益（聖光）。光環骨架的核心表面必須有益。
    """

    id: Surface
    name_zh: str = Field(min_length=1)
    glyph: str
    duration: int | None = Field(default=None, ge=1)
    expires_to: Surface = Surface.NONE
    element: Element | None = None
    flammable: bool = False
    blocks_sight: bool = False
    conceal: bool = False
    on_enter: SurfaceEnter | None = None
    on_turn_start: SurfaceTurnStart | None = None
    budget_points: int | None = Field(default=None, ge=0)
    beneficial: bool = False

    @field_validator("glyph")
    @classmethod
    def _glyph(cls, value: str) -> str:
        return _check_glyph(value)


class SurfaceTable(ContentModel):
    """每個非 ``none`` 的 :class:`~trpg.shared.types.Surface` 恰好一筆。"""

    surfaces: tuple[SurfaceDef, ...]

    _index: dict[Surface, SurfaceDef] = PrivateAttr(default_factory=dict)

    def model_post_init(self, context: object, /) -> None:
        self._index = {s.id: s for s in self.surfaces}

    @model_validator(mode="after")
    def _check(self) -> SurfaceTable:
        counts = Counter(s.id for s in self.surfaces)
        expected = [s for s in Surface if s is not Surface.NONE]
        problems = []
        missing = [s.value for s in expected if counts[s] == 0]
        if missing:
            problems.append(f"缺少表面：{', '.join(missing)}")
        dup = [s.value for s in Surface if counts[s] > 1]
        if dup:
            problems.append(f"重複的表面：{', '.join(dup)}")
        if counts[Surface.NONE]:
            problems.append("none 不需要定義")
        if problems:
            raise ValueError("；".join(problems))
        _unique([s.glyph for s in self.surfaces], "表面顯示字元")
        return self

    def get(self, surface: Surface) -> SurfaceDef:
        # 略過 BaseModel.__getattr__ 的私有屬性慢速路徑（見 Ruleset.terrain_def）
        index: dict[Surface, SurfaceDef] = self.__pydantic_private__["_index"]  # type: ignore[index]
        return index[surface]

    def status_refs(self) -> list[str]:
        refs: list[str] = []
        for s in self.surfaces:
            if s.on_enter is not None:
                if s.on_enter.check is not None:
                    refs.append(s.on_enter.check.fail_status)
                if s.on_enter.apply_status is not None:
                    refs.append(s.on_enter.apply_status)
            if s.on_turn_start is not None and s.on_turn_start.apply_status is not None:
                refs.append(s.on_turn_start.apply_status)
        return refs

    def summary(self) -> str:
        return f"{len(self.surfaces)} 種表面"


# ---------------------------------------------------------------------------
# 元素 × 標籤互動
# ---------------------------------------------------------------------------

type OutcomeOp = Literal[
    "set_surface",
    "ignite_object",
    "explode",
    "conduct",
    "push",
    "spread_surface",
    "fill_chasm",
    "destroy_object",
    "apply_status",
    "keep",
]


class InteractionOutcome(ContentModel):
    """互動結果。

    - ``set_surface``：把該格表面改成 ``surface``（``none`` 即移除）。
    - ``ignite_object``：物件著火（``burning_object_rounds`` 次環境回合後摧毀），並在該格產生
      fire 表面。
    - ``explode``：物件爆炸（參數見 ``objects.yaml`` 的 ``explosion``）。
    - ``conduct``：沿相連的 water 格（與帶 ``conductive`` 的物件）擴散，其上的其他單位（含友方與
      攻擊者自己，不含主要目標）受到「主要目標套用自身抗性與格擋之前的傷害」× ``damage_permille``
      的同元素傷害（最低 ``min_damage``），再各自套用自己的元素修正。
    - ``push``：推動該格的物件或單位（方向與距離由觸及的效果提供）。
    - ``spread_surface``：沿觸及的方向，在下一格產生 ``surface``。
    - ``fill_chasm``：移除物件，該格地形改為 ``terrain``。
    - ``destroy_object``：摧毀物件。
    - ``apply_status``：對該格的單位施加 ``status``（``duration`` 省略時用狀態的預設持續時間）；
      環境造成的狀態不擲抵抗，Boss 的硬控照常轉換（Phase 2H-1）。
    - ``keep``：什麼都不做（用於 ``surface_created``：阻止新表面取代原表面）。
    """

    op: OutcomeOp
    surface: Surface | None = None
    terrain: str | None = Field(default=None, pattern=ID_PATTERN)
    status: str | None = Field(default=None, pattern=ID_PATTERN)
    duration: int | None = Field(default=None, ge=1)
    damage_permille: int = Field(default=1000, ge=0)
    min_damage: int = Field(default=1, ge=0)

    @model_validator(mode="after")
    def _check(self) -> InteractionOutcome:
        if self.op in ("set_surface", "spread_surface") and self.surface is None:
            raise ValueError(f"{self.op} 需要 surface")
        if self.op == "fill_chasm" and self.terrain is None:
            raise ValueError("fill_chasm 需要 terrain")
        if self.op == "apply_status" and self.status is None:
            raise ValueError("apply_status 需要 status")
        if self.op != "apply_status" and (self.status is not None or self.duration is not None):
            raise ValueError("只有 apply_status 可以設定 status、duration")
        return self


class InteractionRule(ContentModel):
    """一條互動規則。

    觸發（``trigger``）：

    - ``element``：元素觸及一格（攻擊或效果造成的元素傷害、爆炸、技能直接指定格子……）。
    - ``surface_created``：效果要在一格產生 ``surface_created`` 表面。符合的規則 **取代** 預設行為
      （預設：新表面取代原表面）。

    對象（``target``）：``surface``（該格目前的表面 = ``surface``）、``object``（該格的物件帶
    ``object_tag``）、``unit``（該格有存活單位；``unit_tag`` 不為空時需帶該標籤；
    ``unit_surface`` 不為空時，該單位所在格的表面必須是它——判斷用的是 **觸及前** 的表面，
    所以冰霜同時把水變成冰也能凍住站在水上的單位，Phase 2H-1）。

    同一次觸及中，每一類對象只套用 **第一條** 符合的規則（依檔案順序）。
    """

    id: str = Field(pattern=ID_PATTERN)
    description_zh: str = Field(min_length=1)
    trigger: Literal["element", "surface_created"]
    element: Element | None = None
    surface_created: Surface | None = None
    target: Literal["surface", "object", "unit"]
    surface: Surface | None = None
    object_tag: str | None = None
    unit_tag: str | None = Field(default=None, pattern=ID_PATTERN)
    unit_surface: Surface | None = None
    then: tuple[InteractionOutcome, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> InteractionRule:
        problems = []
        if self.trigger == "element" and (self.element is None or self.surface_created):
            problems.append("trigger 為 element 時必須設定 element（且不設定 surface_created）")
        if self.trigger == "surface_created" and (
            self.surface_created is None or self.element is not None
        ):
            problems.append(
                "trigger 為 surface_created 時必須設定 surface_created（且不設定 element）"
            )
        if self.target == "surface" and (self.surface is None or self.object_tag):
            problems.append("target 為 surface 時必須設定 surface（且不設定 object_tag）")
        if self.target == "object" and (self.object_tag is None or self.surface is not None):
            problems.append("target 為 object 時必須設定 object_tag（且不設定 surface）")
        if self.object_tag is not None and self.object_tag not in OBJECT_TAGS:
            problems.append(f"未知的物件標籤：{self.object_tag}")
        if self.target == "unit" and (self.surface is not None or self.object_tag is not None):
            problems.append("target 為 unit 時不可設定 surface 或 object_tag")
        if self.unit_surface is not None and self.target != "unit":
            problems.append("unit_surface 只能用於 target: unit")
        if problems:
            raise ValueError(f"互動規則 {self.id}：" + "；".join(problems))
        return self


class ElementCapability(ContentModel):
    """元素能產生的效果（例如暗影可產生 darkness 表面、大地可隆起地形）。

    Phase 2 的技能驗證以此檢查「帶某元素的效果是否合理」；引擎提供
    ``trpg.engine.interactions.element_capable`` 查詢。
    """

    element: Element
    effect: Literal["create_surface", "raise_terrain", "lower_terrain", "create_obstacle", "push"]
    surface: Surface | None = None
    description_zh: str = Field(min_length=1)


class InteractionTable(ContentModel):
    """``content/interactions.yaml``。"""

    rules: tuple[InteractionRule, ...] = Field(min_length=1)
    capabilities: tuple[ElementCapability, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> InteractionTable:
        _unique([r.id for r in self.rules], "互動規則 ID")
        return self

    def summary(self) -> str:
        return f"{len(self.rules)} 條互動規則、{len(self.capabilities)} 項元素能力"


# ---------------------------------------------------------------------------
# 天氣
# ---------------------------------------------------------------------------


class WeatherDef(ContentModel):
    """天氣（``docs/專案計畫.md`` 5.7）。

    - ``element_damage_permille``：元素傷害的增減（例如下雨 fire −300、lightning +200）。
    - ``puddles_per_round``：每次環境回合隨機產生的 water 表面格數。
    - ``sight_range_permille``：視線距離倍率（濃霧 500 = 減半）。
    - ``ranged_disadvantage_beyond``：遠程攻擊超過此距離時有劣勢。
    - ``concealed_ranged_max_distance``：覆寫「隱蔽目標可被遠程攻擊的最遠距離」（夜晚強化隱蔽）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    element_damage_permille: dict[Element, int] = Field(default_factory=dict)
    puddles_per_round: int = Field(default=0, ge=0)
    sight_range_permille: int = Field(default=1000, ge=0, le=1000)
    ranged_disadvantage_beyond: int | None = Field(default=None, ge=1)
    concealed_ranged_max_distance: int | None = Field(default=None, ge=0)

    @field_validator("element_damage_permille")
    @classmethod
    def _mods(cls, value: dict[Element, int]) -> dict[Element, int]:
        bad = [f"{e.value}={v}" for e, v in value.items() if v < -1000]  # noqa: PLR2004
        if bad:
            raise ValueError(f"元素傷害修正不可低於 -1000‰：{', '.join(bad)}")
        return {e: value[e] for e in Element if e in value}


class WeatherTable(ContentModel):
    weather: tuple[WeatherDef, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> WeatherTable:
        _unique([w.id for w in self.weather], "天氣 ID")
        missing = [w for w in ("clear", "rain", "fog", "night") if w not in self.by_id()]
        if missing:
            raise ValueError(f"缺少天氣：{', '.join(missing)}")
        return self

    def by_id(self) -> dict[str, WeatherDef]:
        return {w.id: w for w in self.weather}

    def summary(self) -> str:
        return f"{len(self.weather)} 種天氣"


# ---------------------------------------------------------------------------
# 反應
# ---------------------------------------------------------------------------


class ReactionDef(ContentModel):
    """一種反應（引擎實作 ``effect`` 的語意，數值由資料給定）。

    - ``reduce_damage``：本次攻擊傷害 × (1 − ``damage_reduction_permille``)，無條件捨去，最低 1。
    - ``basic_attack``：以武器普攻觸發者（不花 AP；需能攻擊到觸發者原本的位置）。
    - ``redirect_damage``（Phase 3G-G3b，只由裝備詞條授予）：``ally_hit_in_range`` 時，範圍內的友方
      被單體攻擊命中，改由持有者承受這次攻擊（距離由詞條的 ``range`` 決定）。
    - ``basic_attack`` 配 ``hit_by_melee``（3I-1 反擊 ``counter_attack``）：相鄰敵人的近戰攻擊
      命中持有者、傷害之後，持有者還站著就對攻擊者普攻一次。

    ``requires_status``（Phase 3D-8c）：持有者必須帶有這個狀態才能反應，反應用掉之後移除該狀態
    （監視射擊 ``overwatch_shot`` 用 ``overwatch``）。
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    effect: Literal["reduce_damage", "basic_attack", "redirect_damage"]
    events: tuple[
        Literal[
            "targeted_by_melee",
            "targeted_by_attack",
            "enemy_leaves_adjacent",
            "enemy_moves_in_range",
            "ally_hit_in_range",
            "hit_by_melee",
        ],
        ...,
    ]
    stamina_cost: int = Field(default=0, ge=0)
    damage_reduction_permille: int = Field(default=0, ge=0, le=1000)
    requires_melee_weapon: bool = False
    requires_status: str | None = Field(default=None, pattern=ID_PATTERN)
    requires_counter_weapon: bool = False
    """Phase 3I-1：持有者手上的武器必須有 ``counter``（拳套的反擊）才能反應；持有這種武器的單位由
    引擎自動加上一條 ``auto`` 規則。"""


class ReactionEventDef(ContentModel):
    """反應事件的中文名與說明（Phase 3E-2e）：``ReactionWhen.event`` 的每個值都要有一列，
    技能卡的「反應時機」部件與 glossary API 用。"""

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)


class ReactionTable(ContentModel):
    """``content/reactions.yaml``：反應定義、反應事件名稱與預設規則。"""

    reactions: tuple[ReactionDef, ...] = Field(min_length=1)
    events: tuple[ReactionEventDef, ...] = ()
    default_rules: tuple[ReactionRule, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ReactionTable:
        _unique([r.id for r in self.reactions], "反應 ID")
        _unique([e.id for e in self.events], "反應事件 ID")
        index = self.by_id()
        for rule in self.default_rules:
            check_rule(rule, index)
        return self

    def by_id(self) -> dict[str, ReactionDef]:
        return {r.id: r for r in self.reactions}

    def summary(self) -> str:
        return f"{len(self.reactions)} 種反應、{len(self.default_rules)} 條預設規則"


def check_rule(
    rule: ReactionRule, index: dict[str, ReactionDef], skills: Mapping[str, SkillDef] | None = None
) -> None:
    """反應規則引用的反應存在，且事件是該反應支援的事件。

    ``reaction`` 可以是內建反應（``reactions.yaml``），或（給定 ``skills`` 時）``kind: reaction``
    的技能 ID——此時規則的事件必須等於技能的 ``reaction.event``（Phase 2E-2）。
    """
    definition = index.get(rule.reaction)
    if definition is None:
        skill = None if skills is None else skills.get(rule.reaction)
        if skill is None:
            raise ValueError(f"未知的反應：{rule.reaction}")
        if skill.kind != "reaction" or skill.reaction is None:
            raise ValueError(f"技能 {rule.reaction} 不是反應技，不能作為反應規則")
        if rule.when.event != skill.reaction.event:
            raise ValueError(
                f"反應技 {rule.reaction} 的事件是 {skill.reaction.event}，"
                f"規則卻寫 {rule.when.event}"
            )
        return
    if rule.when.event not in definition.events:
        raise ValueError(
            f"反應 {rule.reaction} 不支援事件 {rule.when.event}"
            f"（可用：{', '.join(definition.events)}）"
        )


# ---------------------------------------------------------------------------
# 效用 AI 的行為模式
# ---------------------------------------------------------------------------


class AiWeights(ContentModel):
    """效用 AI 的權重（意義見 ``content/ai_profiles.yaml``）。未列出的權重為 0。"""

    damage: int = 0
    env_damage: int = 0
    kill: int = 0
    env_kill: int = 0
    friendly_fire: int = 0
    push: int = 0
    status: int = 0
    surface: int = 0
    defend: int = 0
    approach: int = 0
    threat: int = 0
    keep_distance: int = 0
    height: int = 0
    protect: int = 0
    objective: int = 0
    hazard: int = 0
    cover: int = 0
    expose: int = 0
    cover_damage: int = 0
    heal: int = 0
    shield: int = 0
    support: int = 0
    exposed: int = 0
    mana: int = 0
    stamina_permille: int = 0
    """（Phase 3H-2）技能的耐力機會成本：每點耐力 × 這個值 ÷ 1000（扣在技能的分數上）。"""
    cooldown: int = 0
    flank: int = 0
    backstab: int = 0
    """（Phase 3D-8d）近戰單位站在敵人背後格的每個敵人（位置價值加分）。"""
    back_exposed: int = 0
    """（Phase 3D-8d）背對相鄰的近戰敵人（位置價值扣分；朝向以「面向最近的敵人」近似）。"""
    reach_spacing: int = 0
    """（Phase 3-24a1）長柄近戰武器（射程 > 1，矛）：站在 2 格到射程內且打得到的每個敵人加分、緊貼的
    每個敵人扣同樣的分數（位置價值；偏好在觸及距離出手）。"""
    knock_angle: int = 0
    close_range: int = 0
    """（BAL-5 B19）近距離武器（距離傷害修正的最佳距離 ≤ 2 格，霰彈槍）：站位能打到的敵人中，
    距離傷害千分比最高者 × 這個值 ÷ 1000（位置價值；越靠近最佳距離越高）；
    保持距離只計比最佳距離更近的敵人。表格層級的 ``weapon_ai`` 填入每個行為模式。"""
    multi_target: int = 0
    """（BAL-5 B1）範圍技每多打到一名敵人（預期，乘命中率）的加分（技能分數；敵人數 ≥ 2 才有）。表格
    層級的 ``skill_ai`` 填入每個行為模式。"""
    line_up: int = 0
    """（Phase 3-24a2）帶穿透的武器（弩）：能對準一條直線上有多名敵人的站位，每多穿透一名敵人加分
    （位置價值；低權重）。"""
    """（Phase 3-24a1）帶震退的武器（錘）：緊貼著、而且推開後會撞到東西（單位、障礙、牆、邊緣）
    或掉進致命地形的每個敵人加分（位置價值；低權重，偏好能撞擊的角度）。"""
    charge_per_enemy: int = 3
    """（Phase 3E-1）直線衝撞（``charge_through``）每個會被穿過的敵人的固定加分；預設 3，不是 0。"""
    shadowstep: int = 3
    """（Phase 3E-1）瞬步（``shadowstep``）的固定加分；預設 3，不是 0。"""
    shadowstep_behind: int = 2
    """（Phase 3E-1）瞬步落在目標背後時再加的分數；預設 2，不是 0。"""
    contest: int = 0
    """（Phase 3-22）守點戰中，**敵方** 與最近守點格的距離（位置價值每格扣分；搶點）。表格層級的
    ``objective_ai`` 填入每個行為模式。"""
    intercept: int = 0
    """（Phase 3-22）撤離戰中，**敵方** 與最近出口格的距離（位置價值每格扣分；攔截出口路線）。"""
    rush_exit: int = 0
    """（Phase 3-22）撤離戰中，**我方** 與最近出口格的距離（位置價值每格額外扣分；朝出口，疊加在
    ``objective`` 上）。"""
    hold_point: int = 0
    """（Phase 3-22）守點戰中，**我方** 離守點格超過 ``hold_radius`` 的每一格位置價值扣分（守在點
    附近）。"""
    hold_radius: int = Field(default=2, ge=0)
    """（Phase 3-22）``hold_point`` 與 ``hold_guard`` 的半徑（曼哈頓格數）。"""
    hold_guard: int = 0
    """（Phase 3-22）守點戰中，**我方** 單位在守點 ``hold_radius`` 格內且有敵人逼近（6 格內）時，
    守護（防禦）動作多加的分數。"""


class TrapAiRules(ContentModel):
    """AI 放置陷阱的數值（Phase 2F-2；``content/ai_profiles.yaml`` 的 ``trap:``）。

    - ``max_active``：同陣營同時最多放幾個陷阱（不要求聰明，避免一回合鋪滿整張地圖）。
    - ``near``：只在最近的敵人 1–``near`` 格（曼哈頓）內的格子放陷阱。
    - ``shape_factor_permille``：陷阱觸發時預期波及的敵人數（相對單體，‰），以形狀 ID 為鍵。
    - ``default_factor_permille``：沒有列出的形狀使用的係數（‰）。
    """

    max_active: int = Field(default=2, ge=1)
    near: int = Field(default=3, ge=1)
    shape_factor_permille: dict[str, int] = Field(
        default_factory=lambda: {"single": 1000, "cross": 1500, "square3": 2000}
    )
    default_factor_permille: int = Field(default=1000, ge=0)

    def shape_factor(self, shape: str) -> Fraction:
        """形狀的預期波及敵人數（相對單體）；沒有設定的形狀用預設係數。"""
        return Fraction(self.shape_factor_permille.get(shape, self.default_factor_permille), 1000)


class RewriteAiRules(ContentModel):
    """AI 使用改寫規則型原語與源力的數值（Phase 3C-4a；``content/ai_profiles.yaml`` 的
    ``rewrite:``）。單位都是「等值傷害點數」，收益 ＝ 行為模式的 ``damage`` 權重 × 點數。
    評分是最簡單的近似（合法地使用即可，不要求用得好），初值未經模擬。

    - ``ap_points``：獲得的每點 AP（≈ 多一次動作的價值）。
    - ``ally_ap_permille``：給友方的 AP 相對給自己的價值（‰）。
    - ``cooldown_points``：被重置的每一回合冷卻。
    - ``undying_points``：免死的價值 × 目標已損失 HP 的比例（滿血 0，HP 越低越值得）。
    - ``source_points``：每花一點源力的機會成本（扣分）。
    - ``redirect_points``：靈魂連結的價值 × 目標已損失 HP 的比例（施放者 HP 不到一半時為 0）
      （Phase 3C-4b）。
    - ``reaction_points``：每個額外反應次數（目標有反應規則時才有價值）。
    - ``mana_points``：友方每回復 1 點法力（``restore_resource``，Phase 3D-1）。
    - ``steal_points``：每奪取 1 個增益（``steal_buff``，Phase 3D-1）。
    - ``dispel_points``：每驅散敵人 1 個增益（``dispel``，Phase 3D-8a）。
    - ``reveal_points``：每讓 1 個敵人失去隱蔽、或每揭露 1 個敵方陷阱（``reveal``，Phase 3D-8a）。
    - ``revive_points``：每復活 1 個倒下的友方（``revive``，Phase 3D-8b）。
    - ``refund_ap_points``：擊殺時效果每返還 1 點 AP（``on_kill`` 的 ``refund_ap``，Phase 3D-8b）。
    - ``bomb_points_permille``：定時炸彈（``delayed_damage``）的預期傷害折合——炸彈骰子平均 ×
      （半徑內的敵人數 − 友方數，含施放者）× 這個千分比（炸彈可能被淨化或打斷）。
    - ``overwatch_points``：進入監視（``overwatch`` 狀態，Phase 3D-8c）的價值——一次監視射擊的預期
      收益；只有走得進武器射程的敵人才算，最多算 ``overwatch_max_enemies`` 個。
    - ``grant_skill_points`` ／ ``grant_skill_uses_permille``：暫時獲得技能（``grant_skill``，
      Phase 3D-8c）給自己或友方的價值 ＝ ``grant_skill_points`` × 每輪預期使用次數（‰）× 持續
      輪數；只是被給技能預估價值的近似。
    - ``activation_round_points``：啟動常駐類傳說（Phase 3D-6）每一輪效果的價值（限時型 × 持續
      輪數、整場型 × ``activation_battle_rounds``），再扣源力成本。
    - ``activation_battle_rounds``：整場型傳說估計還能生效的輪數。
    - ``delayed_enemy_points``：延遲段（Phase 3F-4b）預計範圍內（以施放者目前的位置推算）每個
      敵人的價值（範圍內的友方扣同樣的分數）；``delayed_attacked_permille``：被攻擊才釋放的延遲段
      再乘這個千分比（可能沒人來打）。
    """

    ap_points: int = Field(default=6, ge=0)
    ally_ap_permille: int = Field(default=600, ge=0, le=1000)
    cooldown_points: int = Field(default=4, ge=0)
    undying_points: int = Field(default=40, ge=0)
    source_points: int = Field(default=3, ge=0)
    redirect_points: int = Field(default=24, ge=0)
    reaction_points: int = Field(default=8, ge=0)
    mana_points: int = Field(default=1, ge=0)
    steal_points: int = Field(default=8, ge=0)
    dispel_points: int = Field(default=6, ge=0)
    reveal_points: int = Field(default=6, ge=0)
    revive_points: int = Field(default=30, ge=0)
    refund_ap_points: int = Field(default=6, ge=0)
    bomb_points_permille: int = Field(default=700, ge=0, le=2000)
    overwatch_points: int = Field(default=5, ge=0)
    overwatch_max_enemies: int = Field(default=2, ge=1)
    grant_skill_points: int = Field(default=8, ge=0)
    grant_skill_uses_permille: int = Field(default=800, ge=0, le=3000)
    activation_round_points: int = Field(default=4, ge=0)
    activation_battle_rounds: int = Field(default=4, ge=1)
    delayed_enemy_points: int = Field(default=5, ge=0)
    delayed_attacked_permille: int = Field(default=600, ge=0, le=1000)


class GambleAiRules(ContentModel):
    """賭博型技能的 AI 數值（Phase 3D-7a；``content/ai_profiles.yaml`` 的 ``gamble:``；初值未經
    模擬）。AI 以期望值評分（每個分支的分數 × 該分支的機率）。

    - ``hp_floor_permille``：施放者的 HP 低於最大 HP 的這個千分比時，反噬可能造成傷害的賭博技能
      （賭注失敗分支或失手反噬有自傷）不在快死時亂賭。
    - ``low_hp_permille``：上述情形下，技能的正分乘上這個千分比（大幅降低）；負分不變。
    """

    hp_floor_permille: int = Field(default=300, ge=0, le=1000)
    low_hp_permille: int = Field(default=100, ge=0, le=1000)


class SelfCostAiRules(ContentModel):
    """自己付的代價的 AI 使用條件（Phase 3-50，06 6.5；ai_profiles.yaml 的 ``self_cost:``；
    初值未經模擬）。

    - ``stun_hp_below_permille``、``stun_enemy_radius``：自暈（會跳過回合的自身狀態）只在施放者 HP
      低於最大 HP 的這個千分比、且這個格數內有敵人時使用。
    - ``overdraft_min_targets``：透支只在這一擊能擊殺敵人、或波及至少這麼多敵人時使用。
    """

    stun_hp_below_permille: int = Field(default=500, ge=0, le=1000)
    stun_enemy_radius: int = Field(default=6, ge=1)
    overdraft_min_targets: int = Field(default=2, ge=1)


class FormAiRules(ContentModel):
    """形態的 AI 數值（Phase 3J-1a，06 6.30；ai_profiles.yaml 的 ``form:``；初值未經模擬）。

    - ``enter_value``：進入形態的價值（等值傷害點數）：收益 ＝ 行為模式的 ``support`` 權重 × 這個值
      （進入獎勵的護盾、治療、傷害另外照一般事件計分）。AI 沒在姿態或形態中、AP 夠時才考慮進入；
      不主動取消（維持費不夠時由規則自動解除）。
    - ``rotate_value``（3J-1b）：已經在形態中、換成另一個形態（離開的形態冷卻、新形態的進入獎勵
      另外照一般事件計分）的價值，比 ``enter_value`` 低，所以只有進入獎勵夠好時才輪替。
    """

    enter_value: int = Field(default=8, ge=0)
    rotate_value: int = Field(default=4, ge=0)


class SummonAiRules(ContentModel):
    """召喚者 AI 的數值（Phase 3D-4a 寫在程式裡，3D-4b 搬進 ``content/ai_profiles.yaml`` 的
    ``summon:``；初值未經模擬）。

    - ``hit_permille``：召喚物預估傷害的命中與走位折合（‰）。
    - ``distance_cost_permille``：召喚位置與最近敵人每差一格扣的分數（‰；只用來在同一技能的位置之間
      排序）。
    - ``totem_ally_points``：圖騰光環的價值：每個範圍內友方 × 狀態在 ``ally_status_values`` 的價值
      （沒列出的用這個值）× 持續輪數 × ``support`` 權重 × 折合（沿用 ``hit_permille``）。
    - ``boss_blocker_points`` / ``boss_blocker_slack``（Phase 3-33b）：Boss 優先清擋路的召喚物——
      召喚物與 Boss 的距離加上它與某個非召喚物敵人的距離，不超過 Boss 到該敵人的距離再加
      ``boss_blocker_slack`` 時算「擋在路徑上」；Boss 的動作會打到這樣的召喚物時，每隻加
      ``boss_blocker_points`` 分（× 命中折合）。0 ＝ 不加分。
    - 模式（Phase 3-33c）：``follow_radius`` 跟隨時待在召喚者幾格內（軟性：超出每格扣
      ``orders.hold_weight`` 分，仍會主動攻擊）；``guard_radius`` 守護我時只走到召喚者幾格內；
      ``guard_threat_range`` 守護我時，敵人與召喚者的距離不超過（敵人武器射程 ＋ 速度 ＋ 此值）
      算「威脅施放者」，優先打他們。
    - 自動切換（我方 AI 隊友與自動代打的施放者，規則保守）：``auto_guard_hp_permille`` 施放者 HP
      低於最大 HP 的這個千分比時，召喚物改守護我（0 ＝ 不切換）；``auto_focus_boss`` 場上有 Boss
      時召喚物改集火 Boss。
    - ``infusion_points``：估值時，帶灌注的召喚物每輪多算這麼多點等值傷害（0 ＝ 不計）。
    - 特性（Phase 3-33e2a）：``detonate_targets_permille`` 自爆召喚物的估值（爆炸傷害骰平均 × 預期
      被炸到的敵人數，‰；只算一次、一般攻擊只算 1 輪）；``inert_round_points`` 不行動的召喚物
      （土牆）每輪擋路的等值傷害點數（沒有攻擊，其餘估值為 0）。
    - 灌注技能（Phase 3-33d）：施放者 AI 評估「把技能灌注給召喚物」＝ 召喚物從自己位置施放的完整
      預覽分數 × ``infuse_value_permille`` ‰ × 存活機率的保守估計（召喚物 HP ÷（HP ＋ 能打到牠的
      敵人數 × ``infuse_threat_damage``））；高於其他動作的最佳分數時灌注。``infuse_value_permille``
      為 0 時 AI 不灌注。
    """

    hit_permille: int = Field(default=500, ge=0, le=1000)
    distance_cost_permille: int = Field(default=100, ge=0)
    totem_ally_points: int = Field(default=3, ge=0)
    boss_blocker_points: int = Field(default=0, ge=0)
    boss_blocker_slack: int = Field(default=1, ge=0, le=4)
    follow_radius: int = Field(default=3, ge=0, le=3)
    guard_radius: int = Field(default=2, ge=0, le=3)
    guard_threat_range: int = Field(default=1, ge=0, le=4)
    auto_guard_hp_permille: int = Field(default=0, ge=0, le=1000)
    auto_focus_boss: bool = False
    infusion_points: int = Field(default=0, ge=0)
    detonate_targets_permille: int = Field(default=1000, ge=0, le=5000)
    inert_round_points: int = Field(default=2, ge=0)
    infuse_value_permille: int = Field(default=0, ge=0, le=2000)
    infuse_threat_damage: int = Field(default=4, ge=0)
    shield_round_permille: int = Field(default=0, ge=0, le=2000)
    """（BAL-5 B5）護盾脈動（守護靈）：每輪護盾量平均 × ``shield`` 權重 × 這個千分比 × 持續輪數。"""
    pull_round_points: int = Field(default=0, ge=0)
    """（BAL-5 B5）拉扯脈動（吸引圖騰）：每輪的等值傷害點數（× ``damage`` 權重 × 持續輪數）。"""
    snare_likelihood_permille: int = Field(default=0, ge=0, le=1000)
    """（BAL-5 B5）纏繞（藤蔓）：每輪觸發的機率；價值 ＝ 狀態在 ``status_values`` 的價值 × 機率
    × 持續輪數
    （× ``damage`` 權重）。"""
    platform_points: int = Field(default=0, ge=0)
    """（BAL-5 B5）高台（高台圖騰）：每名遠程友方（非召喚物）的一次性等值傷害點數（不乘輪數；
    模擬顯示乘輪數會讓 AI 反覆召喚圖騰、拖長戰鬥而不提高勝率）。"""


class ZoneAiRules(ContentModel):
    """持續區域的 AI 數值（Phase 3D-5；``content/ai_profiles.yaml`` 的 ``zone:``；初值未經模擬）。

    - ``likelihood_permille``：建立區域時，估計之後每輪真的會有對象觸發一次的比例（‰）。收益 ＝
      區域每次觸發的價值 × 區域格內與移動路徑上的對象數 × 持續輪數 × 這個比例（建立當下就在
      區域內的對象，預覽已經算過一次）。
    - ``path_permille``：移動型區域路徑上（還沒被覆蓋）的對象，相對於格內對象的權重（‰）。
    """

    likelihood_permille: int = Field(default=400, ge=0, le=1000)
    path_permille: int = Field(default=500, ge=0, le=1000)


class RuneAiRules(ContentModel):
    """刻印的 AI 數值（Phase 3-23；``content/ai_profiles.yaml`` 的 ``rune:``；初值未經模擬）。

    只在行動者有「讀取技能」（條件 ``on_own_rune`` 或原語 ``detonate_runes``）時才會主動刻印。

    - ``inscribe_points``：在敵人腳下刻一個符文的價值（等值傷害點數 × ``damage`` 權重）；
    - ``adjacent_permille``／``near_permille``：符文刻在距離最近的敵人 1 格、2 格時相對於腳下的
      比例（‰；更遠為 0，敵人「會停留」的格子才有價值）；
    - ``read_points``：讀取技能（有 ``on_own_rune`` 條件的效果，或引爆）打到站在自己符文上的敵人
      時的額外價值（每個目標；單位同上）。
    """

    inscribe_points: int = Field(default=6, ge=0)
    adjacent_permille: int = Field(default=600, ge=0, le=1000)
    near_permille: int = Field(default=300, ge=0, le=1000)
    read_points: int = Field(default=6, ge=0)


class TerrainAiRules(ContentModel):
    """純地形技能的 AI 數值（Phase 3T-5；ai_profiles.yaml 的 ``terrain:``；初值未經模擬）。

    收益的單位是等值傷害點數，乘上行為模式的 ``damage`` 權重：

    - ``height_points``：站在被改變的格子上的單位，高度每變一層的價值——敵人被降低或友方被抬高
      為收益，反過來為損失（施放者自己站的格子由位置價值的 ``height`` 權重處理，不重複計算）；
    - ``pit_points``：下陷造出的坑旁邊，每名高出墜落門檻的敵人（我方有推擊或拉扯技能時才算；
      把敵人推進坑才會墜落）。
    """

    height_points: int = Field(default=4, ge=0)
    pit_points: int = Field(default=6, ge=0)


class AiProfile(ContentModel):
    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    """開發者說明（可寫權重、階段代號）；不顯示給玩家。"""
    player_description_zh: str = Field(min_length=1)
    """玩家用短句（3-41c）：召喚物資訊小卡的「行為」用它，不含權重或開發代號。"""
    weights: AiWeights
    status_values: dict[str, int] = Field(default_factory=dict)
    """對敵人施加各狀態的價值（等值傷害點數）；由 :class:`AiProfileTable` 的 ``status_values``
    填入，行為模式自己也可以覆寫個別狀態。"""
    ally_status_values: dict[str, int] = Field(default_factory=dict)
    """對友方（含自己）施加各增益的價值（等值傷害點數，Phase 2D-1）；收益 ＝ ``support`` 權重 ×
    價值 × 新增的持續比例。由 :class:`AiProfileTable` 的 ``ally_status_values`` 填入。"""
    trap_likelihood_permille: int = Field(default=700, ge=0, le=1000)
    """放置陷阱時，估計陷阱真的會被踩中或波及敵人的機率（‰，Phase 2E-3）；由 :class:`AiProfileTable`
    的同名欄位填入。"""
    trap: TrapAiRules = Field(default_factory=TrapAiRules)
    """放置陷阱的 AI 數值（Phase 2F-2）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    rewrite: RewriteAiRules = Field(default_factory=RewriteAiRules)
    """改寫規則型原語與源力的 AI 數值（Phase 3C-4a）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    summon: SummonAiRules = Field(default_factory=SummonAiRules)
    """召喚的 AI 數值（Phase 3D-4b）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    zone: ZoneAiRules = Field(default_factory=ZoneAiRules)
    """持續區域的 AI 數值（Phase 3D-5）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    gamble: GambleAiRules = Field(default_factory=GambleAiRules)
    """賭博型技能的 AI 數值（Phase 3D-7a）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    rune: RuneAiRules = Field(default_factory=RuneAiRules)
    """刻印的 AI 數值（Phase 3-23）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    self_cost: SelfCostAiRules = Field(default_factory=SelfCostAiRules)
    terrain: TerrainAiRules = Field(default_factory=TerrainAiRules)
    """純地形技能的 AI 數值（Phase 3T-5）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    form: FormAiRules = Field(default_factory=FormAiRules)
    """形態的 AI 數值（Phase 3J-1a）；由 :class:`AiProfileTable` 的同名欄位填入。"""
    """自己付的代價的 AI 使用條件（Phase 3-50）；由 :class:`AiProfileTable` 的同名欄位填入。"""


class OrderBonuses(ContentModel):
    """戰術指令的評分加成（Phase 2C-2；``content/ai_profiles.yaml`` 的 ``orders:``）。

    - ``focus_permille``：集火——對目標的預覽收益（傷害、擊倒、狀態、推擊、表面、離開掩護）
      乘上這個倍率（‰；1500 ＝ 原收益再加 50%）；位置價值的 ``approach`` 改看與目標的距離；
    - ``hold_weight``：守位——每超出 ``radius`` 一格的位置價值扣分；
    - ``retreat_weight``：撤退——與目標格每一格距離的位置價值扣分（``approach``、``threat`` 視為
      0）；
    - ``protect_min``：保護——``protect`` 權重至少為這個值（對象固定為指令指定的友方）；
    - ``environment_permille``：利用環境——環境傷害、環境擊倒、推擊、表面、離開掩護的收益倍率（‰）。
    """

    focus_permille: int = Field(default=1500, ge=1000)
    hold_weight: int = Field(default=20, ge=0)
    retreat_weight: int = Field(default=15, ge=0)
    protect_min: int = Field(default=12, ge=0)
    environment_permille: int = Field(default=2000, ge=1000)


def _with_facing(weights: Any, facing: Any) -> Any:
    """把表格層級的朝向權重（Phase 3D-8d）填入行為模式的 ``weights``（行為模式自己列出的優先）。"""
    if not isinstance(weights, dict) or not isinstance(facing, dict):
        return weights
    return {**facing, **weights}


class RunAiRules(ContentModel):
    """AI 使用跑步的數值（Phase 3-20，玩法 #22；``content/ai_profiles.yaml`` 的 ``run:``）。

    AI 只在兩種情況考慮跑步，其餘一律 0 分（不會跑）：

    - 追擊：沒有任何敵人在「目前移動點數能走到的格子」的攻擊距離內，但跑步後能——``pursue_points``；
    - 撤離：HP 低於最大 HP 的 ``retreat_hp_permille``‰、最近的敵人在 ``retreat_enemy_radius`` 格
      （曼哈頓）內，且跑步後能走到離最近敵人更遠的格子——``retreat_points``。

    初值未經模擬（平衡階段調整）；兩者都比防禦的分數大，才會在這些情況下勝過防禦，但比大多數
    攻擊與走位的收益小。
    """

    pursue_points: int = Field(default=6, ge=0)
    retreat_points: int = Field(default=6, ge=0)
    retreat_hp_permille: int = Field(default=350, ge=0, le=1000)
    retreat_enemy_radius: int = Field(default=4, ge=1)


class BasicActionAiRules(ContentModel):
    """AI 使用守護隊友、換位、瞄準的數值（Phase 3-21a，玩法 #24；``content/ai_profiles.yaml`` 的
    ``basic:``）。條件不成立一律 0 分（不會用）；初值未經模擬（平衡階段調整）。

    - 守護隊友：相鄰隊友 HP 低於 ``guard_ally_hp_permille``‰、``guard_threat_radius`` 格內有敵人、
      自己 HP 不低於 ``guard_self_hp_permille``‰ → 在「守護自己」的分數上加
      ``guard_points``（所以只在這種情況勝過守護自己）；
    - 換位：隊友比自己更靠近最近的敵人（在前線），且隊友在 ``swap_threat_radius`` 格內有敵人，並且
      （隊友 HP 低於 ``swap_rescue_hp_permille``‰ ＜把低血量隊友換離前線＞，或自己的最大 HP 達隊友的
      ``swap_tank_ratio_permille``‰ ＜把坦克換上前＞），自己 HP 不低於 ``swap_self_hp_permille``‰
      → ``swap_points``；
    - 瞄準：AP 剛好夠「瞄準 ＋ 一個 AP 花費 ≥ ``aim_min_attack_ap`` 的攻擊」，而該攻擊的命中率低於
      ``aim_hit_permille``‰ 且有收益 → 該攻擊的分數 ＋ ``aim_points``（所以先瞄準再攻擊）；
    - 攀跳（3-21b）：攀爬或跳躍後，走到最近敵人的步數比現在少至少 ``vault_min_saving`` 步（現在走不
      到、攀跳後走得到也算）→ ``vault_points``（低權重：只在明顯縮短路徑時用）。
    """

    guard_points: int = Field(default=3, ge=0)
    guard_ally_hp_permille: int = Field(default=500, ge=0, le=1000)
    guard_self_hp_permille: int = Field(default=500, ge=0, le=1000)
    guard_threat_radius: int = Field(default=6, ge=1)
    swap_points: int = Field(default=6, ge=0)
    swap_rescue_hp_permille: int = Field(default=350, ge=0, le=1000)
    swap_tank_ratio_permille: int = Field(default=1500, ge=1000)
    swap_self_hp_permille: int = Field(default=500, ge=0, le=1000)
    swap_threat_radius: int = Field(default=3, ge=1)
    aim_points: int = Field(default=2, ge=0)
    aim_hit_permille: int = Field(default=500, ge=0, le=1000)
    aim_min_attack_ap: int = Field(default=2, ge=1)
    vault_points: int = Field(default=4, ge=0)
    vault_min_saving: int = Field(default=4, ge=1)
    variant_position_bonus: int = Field(default=3, ge=0)
    """戰場變奏（Phase 3-25a）：移動的目的地能讓某招現在可用的技能的變奏成立（現在的位置不成立）
    時，移動分數加這麼多（初值保守，未經模擬）。"""
    reload_points: int = Field(default=20, ge=0)
    """裝填（3-24a2，武器動作）：彈匣空時的固定分數（要大於一般走位，所以空膛就先裝填）。"""
    charge_permille: int = Field(default=400, ge=0, le=1000)
    """裝備充能的啟動（3G-G3a）：預覽收益（加上自我增益的價值）× 這個比例（低權重：AI 會啟動，
    但通常排在一般攻擊與技能之後）。"""


class AiProfileTable(ContentModel):
    """``content/ai_profiles.yaml``：至少包含 brute、archer、cunning、guard。

    ``move_candidates``：每次決策中，``Move`` 先以便宜的位置價值排序，只保留前 N 個候選；其中
    有風險的移動（可能被藉機攻擊、踩上有進入效果的表面、墜落、撤離、倒地站起）才跑完整
    ``preview``，其餘的分數直接由位置價值算出（與完整預覽的分數相同）。

    ``skill_candidates``：每種技能最多保留幾個選取跑完整 ``preview``（先以便宜的估計排序）。

    ``status_values``（Phase 2B-1）：對敵人施加各種狀態的價值，單位為「等值的傷害點數」，AI 的
    收益 ＝ 行為模式的 ``damage`` 權重 × 價值 × 命中率 × 施加成功率。沒有列出的狀態使用
    ``status`` 權重（每個狀態固定分數）。

    ``ally_status_values``（Phase 2D-1）：對友方施加各增益的價值（同單位）；淨化的收益用
    ``status_values``（沒列出的狀態用 3）。
    """

    profiles: tuple[AiProfile, ...] = Field(min_length=1)
    move_candidates: int = Field(default=8, ge=1)
    skill_candidates: int = Field(default=3, ge=1)
    status_values: dict[str, int] = Field(default_factory=dict)
    ally_status_values: dict[str, int] = Field(default_factory=dict)
    trap_likelihood_permille: int = Field(default=700, ge=0, le=1000)
    """AI 放置陷阱的收益 ＝ 陷阱效果的價值 × 範圍波及的預期敵人數 × 這個機率（‰；初值未經模擬）。"""
    trap: TrapAiRules = Field(default_factory=TrapAiRules)
    rewrite: RewriteAiRules = Field(default_factory=RewriteAiRules)
    summon: SummonAiRules = Field(default_factory=SummonAiRules)
    zone: ZoneAiRules = Field(default_factory=ZoneAiRules)
    gamble: GambleAiRules = Field(default_factory=GambleAiRules)
    rune: RuneAiRules = Field(default_factory=RuneAiRules)
    self_cost: SelfCostAiRules = Field(default_factory=SelfCostAiRules)
    form: FormAiRules = Field(default_factory=FormAiRules)
    terrain: TerrainAiRules = Field(default_factory=TerrainAiRules)
    orders: OrderBonuses = Field(default_factory=OrderBonuses)
    basic: BasicActionAiRules = Field(default_factory=BasicActionAiRules)
    """守護隊友、換位、瞄準的 AI 數值（Phase 3-21a；敵我同一套，不分行為模式）。"""
    run: RunAiRules = Field(default_factory=RunAiRules)
    """跑步的 AI 數值（Phase 3-20；敵我同一套，不分行為模式）。"""
    objective_ai: dict[str, int] = Field(default_factory=dict)
    """勝利條件的 AI 權重（Phase 3-22；``contest``、``intercept``、``rush_exit``、``hold_point``、
    ``hold_radius``、``hold_guard``）：敵我同一套，填入每個行為模式的 ``weights``（行為模式自己
    列出的優先）。只在撤離或守點戰中生效。"""
    skill_ai: dict[str, int] = Field(default_factory=dict)
    """技能選用的權重（BAL-5 B1；``multi_target``）：敵我同一套，填入每個行為模式的 ``weights``。"""
    weapon_ai: dict[str, int] = Field(default_factory=dict)
    """武器站位的位置權重（BAL-5 B19；``close_range``）：敵我同一套，填入每個行為模式的 ``weights``
    （行為模式自己列出的優先）。"""
    facing: dict[str, int] = Field(default_factory=dict)
    """朝向與背刺的位置權重（Phase 3D-8d；``backstab``、``back_exposed``）：敵我同一套，填入每個行為
    模式的 ``weights``（行為模式自己列出的優先）。"""

    @model_validator(mode="before")
    @classmethod
    def _share_status_values(cls, data: Any) -> Any:
        """把表格層級的 ``status_values`` 填入每個行為模式（行為模式自己列出的優先）。"""
        if not isinstance(data, dict):
            return data
        shared = data.get("status_values")
        ally_shared = data.get("ally_status_values")
        trap_shared = {
            key: data[key]
            for key in (
                "trap_likelihood_permille",
                "trap",
                "rewrite",
                "summon",
                "zone",
                "gamble",
                "rune",
                "self_cost",
                "form",
                "terrain",
            )
            if key in data
        }
        facing = data.get("facing")
        for extra_key in ("objective_ai", "weapon_ai", "skill_ai"):
            extra = data.get(extra_key)
            if isinstance(extra, dict):
                facing = {**(facing if isinstance(facing, dict) else {}), **extra}
        if (
            not isinstance(shared, dict)
            and not isinstance(ally_shared, dict)
            and not trap_shared
            and not isinstance(facing, dict)
        ):
            return data
        trap_default = trap_shared
        profiles = [
            {
                **trap_default,
                **p,
                "status_values": {**(shared or {}), **p.get("status_values", {})},
                "ally_status_values": {**(ally_shared or {}), **p.get("ally_status_values", {})},
                "weights": _with_facing(p.get("weights"), facing),
            }
            if isinstance(p, dict)
            else p
            for p in data.get("profiles", [])
        ]
        return {**data, "profiles": profiles}

    @model_validator(mode="after")
    def _check(self) -> AiProfileTable:
        _unique([p.id for p in self.profiles], "行為模式 ID")
        missing = [p for p in ("brute", "archer", "cunning", "guard") if p not in self.by_id()]
        if missing:
            raise ValueError(f"缺少行為模式：{', '.join(missing)}")
        return self

    def by_id(self) -> dict[str, AiProfile]:
        return {p.id: p for p in self.profiles}

    def summary(self) -> str:
        return f"{len(self.profiles)} 種行為模式"
