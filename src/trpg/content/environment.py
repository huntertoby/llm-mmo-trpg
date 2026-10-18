"""環境內容 schema：格子物件、表面、元素 × 標籤互動表、天氣、反應規則。

對應資料檔：``content/objects.yaml``、``content/surfaces.yaml``、``content/interactions.yaml``、
``content/weather.yaml``、``content/reactions.yaml``（``docs/專案計畫.md`` 5.1、5.2.1、5.7）。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Literal

from pydantic import Field, PrivateAttr, field_validator, model_validator

from trpg.content.battle import ID_PATTERN, Dice, ReactionRule, ReactionUnless, ReactionWhen
from trpg.content.schemas import ContentModel
from trpg.shared.types import Attribute, Element, Surface

__all__ = [
    "OBJECT_TAGS",
    "REACTION_EVENTS",
    "AiProfile",
    "AiProfileTable",
    "AiWeights",
    "ElementCapability",
    "ExplosionDef",
    "InteractionOutcome",
    "InteractionRule",
    "InteractionTable",
    "ObjectDef",
    "ObjectTable",
    "OrderBonuses",
    "ReactionDef",
    "ReactionRule",
    "ReactionTable",
    "ReactionUnless",
    "ReactionWhen",
    "SpillDef",
    "SurfaceCheck",
    "SurfaceDamage",
    "SurfaceDef",
    "SurfaceEnter",
    "SurfaceHeal",
    "SurfaceTable",
    "SurfaceTurnStart",
    "WeatherDef",
    "WeatherTable",
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
        "half_cover",  # 半掩護：遠程攻擊緊鄰其後的目標命中 −2（Phase 1C）
        "over_chasm",  # 架在致命地形上：此格變成可站立、非致命
        "pushable",  # 可被推動
    }
)
"""引擎認得的物件標籤。新物件只要組合這些標籤，就自動支援所有互動。"""

REACTION_EVENTS = ("targeted_by_melee", "targeted_by_attack", "enemy_leaves_adjacent")


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
    - ``keep``：什麼都不做（用於 ``surface_created``：阻止新表面取代原表面）。
    """

    op: OutcomeOp
    surface: Surface | None = None
    terrain: str | None = Field(default=None, pattern=ID_PATTERN)
    damage_permille: int = Field(default=1000, ge=0)
    min_damage: int = Field(default=1, ge=0)

    @model_validator(mode="after")
    def _check(self) -> InteractionOutcome:
        if self.op in ("set_surface", "spread_surface") and self.surface is None:
            raise ValueError(f"{self.op} 需要 surface")
        if self.op == "fill_chasm" and self.terrain is None:
            raise ValueError("fill_chasm 需要 terrain")
        return self


class InteractionRule(ContentModel):
    """一條互動規則。

    觸發（``trigger``）：

    - ``element``：元素觸及一格（攻擊或效果造成的元素傷害、爆炸、技能直接指定格子……）。
    - ``surface_created``：效果要在一格產生 ``surface_created`` 表面。符合的規則 **取代** 預設行為
      （預設：新表面取代原表面）。

    對象（``target``）：``surface``（該格目前的表面 = ``surface``）、``object``（該格的物件帶
    ``object_tag``）、``unit``（該格有存活單位；``unit_tag`` 不為空時需帶該標籤）。

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
    """

    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    effect: Literal["reduce_damage", "basic_attack"]
    events: tuple[Literal["targeted_by_melee", "targeted_by_attack", "enemy_leaves_adjacent"], ...]
    stamina_cost: int = Field(default=0, ge=0)
    damage_reduction_permille: int = Field(default=0, ge=0, le=1000)
    requires_melee_weapon: bool = False


class ReactionTable(ContentModel):
    """``content/reactions.yaml``：反應定義與預設規則。"""

    reactions: tuple[ReactionDef, ...] = Field(min_length=1)
    default_rules: tuple[ReactionRule, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> ReactionTable:
        _unique([r.id for r in self.reactions], "反應 ID")
        index = self.by_id()
        for rule in self.default_rules:
            check_rule(rule, index)
        return self

    def by_id(self) -> dict[str, ReactionDef]:
        return {r.id: r for r in self.reactions}

    def summary(self) -> str:
        return f"{len(self.reactions)} 種反應、{len(self.default_rules)} 條預設規則"


def check_rule(rule: ReactionRule, index: dict[str, ReactionDef]) -> None:
    """反應規則引用的反應存在，且事件是該反應支援的事件。"""
    definition = index.get(rule.reaction)
    if definition is None:
        raise ValueError(f"未知的反應：{rule.reaction}")
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
    exposed: int = 0
    mana: int = 0
    cooldown: int = 0


class AiProfile(ContentModel):
    id: str = Field(pattern=ID_PATTERN)
    name_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    weights: AiWeights
    status_values: dict[str, int] = Field(default_factory=dict)
    """對敵人施加各狀態的價值（等值傷害點數）；由 :class:`AiProfileTable` 的 ``status_values``
    填入，行為模式自己也可以覆寫個別狀態。"""


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


class AiProfileTable(ContentModel):
    """``content/ai_profiles.yaml``：至少包含 brute、archer、cunning、guard。

    ``move_candidates``：每次決策中，``Move`` 先以便宜的位置價值排序，只保留前 N 個候選；其中
    有風險的移動（可能被藉機攻擊、踩上有進入效果的表面、墜落、撤離、倒地站起）才跑完整
    ``preview``，其餘的分數直接由位置價值算出（與完整預覽的分數相同）。

    ``skill_candidates``：每種技能最多保留幾個選取跑完整 ``preview``（先以便宜的估計排序）。

    ``status_values``（Phase 2B-1）：對敵人施加各種狀態的價值，單位為「等值的傷害點數」，AI 的
    收益 ＝ 行為模式的 ``damage`` 權重 × 價值 × 命中率 × 施加成功率。沒有列出的狀態使用
    ``status`` 權重（每個狀態固定分數）。
    """

    profiles: tuple[AiProfile, ...] = Field(min_length=1)
    move_candidates: int = Field(default=8, ge=1)
    skill_candidates: int = Field(default=3, ge=1)
    status_values: dict[str, int] = Field(default_factory=dict)
    orders: OrderBonuses = Field(default_factory=OrderBonuses)

    @model_validator(mode="before")
    @classmethod
    def _share_status_values(cls, data: Any) -> Any:
        """把表格層級的 ``status_values`` 填入每個行為模式（行為模式自己列出的優先）。"""
        if not isinstance(data, dict) or not isinstance(data.get("status_values"), dict):
            return data
        shared = data["status_values"]
        profiles = [
            {**p, "status_values": {**shared, **p.get("status_values", {})}}
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
