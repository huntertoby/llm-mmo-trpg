"""預覽（dry run，``docs/專案計畫.md`` 5.9）：``preview(state, action) -> Preview``。

做法：用 **同一套引擎** 在狀態複本上模擬兩次（:func:`trpg.engine.battle.resolve_with` 的預覽模式）：

- ``min``（最少後果）：動作本身的判定視為成功但不暴擊；所有傷害骰取最小值；次要判定（藉機攻擊、
  冰面滑倒）對守方有利；``prompt`` 反應不使用。→「若命中且傷害為最小值時 **確定** 會發生的連鎖」。
- ``max``（最多後果）：動作本身暴擊；傷害骰取最大值；次要判定對守方不利；``prompt`` 反應使用。
  → 與 ``min`` 的差集為「可能發生的連鎖」。

命中率、暴擊率以 :class:`fractions.Fraction` 窮舉 d20（優劣勢時窮舉 400 組）精確計算；
期望傷害窮舉傷害骰的分布，以與結算相同的整數公式計算。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import product
from typing import Literal

from trpg.content.skills import (
    CHARGE_THROUGH,
    DAMAGE_MULTIPLIER,
    GAMBLE,
    SWAP,
    SWAP_ANY,
    TELEPORT_TARGET,
    TIME_BOMB,
    EffectSpec,
    SkillDef,
)
from trpg.engine import modifiers
from trpg.engine.actions import (
    Action,
    Aim,
    Attack,
    Defend,
    Interact,
    Reload,
    Run,
    Shove,
    Swap,
    Trip,
    UseSkill,
    Vault,
)
from trpg.engine.battle import _actor, action_ap_cost, simulate_preview
from trpg.engine.bombs import blast_tiles, bomb_spec
from trpg.engine.control import plan_status, status_save_chance
from trpg.engine.events import (
    AttackIntercepted,
    AttackRolled,
    DamageDealt,
    EnteredDeadlyTerrain,
    EventBase,
    FollowupCharged,
    Healed,
    ObjectDamaged,
    ObjectDestroyed,
    ObjectExploded,
    ObjectHurled,
    ObjectIgnited,
    ObjectMoved,
    ObjectToppled,
    ReactionTriggered,
    ShieldGained,
    SkillFollowup,
    SkillGranted,
    StacksChanged,
    StatusApplied,
    SummonExpired,
    SurfaceChanged,
    TerrainChanged,
    TrapPlaced,
    TrapTriggered,
    UnitCharged,
    UnitDashed,
    UnitDowned,
    UnitEscaped,
    UnitFell,
    UnitMoved,
    UnitRevived,
    UnitSummoned,
)
from trpg.engine.ids import BOSS_TAG
from trpg.engine.maneuvers import contest_chance
from trpg.engine.pierce import pierce_trace
from trpg.engine.results import ResolveResult
from trpg.engine.rules.combat import (
    PERMILLE,
    PPM,
    Cover,
    advantage_state,
    attack_reach,
    half_cover,
    hit_modifier,
    is_hit,
    positional_bonus,
    situational_modifier,
    weapon_profile,
)
from trpg.engine.rules.geometry import manhattan
from trpg.engine.rules.movement import available_move_budget, is_deadly, path_map
from trpg.engine.rules.statuses import effective_attribute, shield_amount, weapon_attribute
from trpg.engine.rules.weapons import weapon_hit_bonus
from trpg.engine.skills.conditions import Subject, condition_met
from trpg.engine.skills.scaling import skill_scaling_value
from trpg.engine.skills.targeting import (
    compute_area,
    damage_parameters,
    followup_origin,
    followup_selection,
    pierce_active,
    resolve_effects,
    shape_reach,
    skill_ap_cost,
    skill_profile,
)
from trpg.engine.state import BattleState, UnitState
from trpg.engine.traps import strip_hidden_traps
from trpg.engine.weapon_traits import attack_dice
from trpg.shared.types import Attribute, ObjectId, UnitId

__all__ = [
    "BombInfo",
    "DamageRange",
    "DisplaceCheck",
    "GambleInfo",
    "GambleOutcome",
    "GrantInfo",
    "HurlInfo",
    "MoveInfo",
    "Outcome",
    "PierceInfo",
    "Preview",
    "ReviveInfo",
    "StatusChance",
    "SummonInfo",
    "TargetPreview",
    "ToppleInfo",
    "dice_distribution",
    "preview",
]

type XY = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Outcome:
    """連鎖結果的摘要（用於比較「確定」與「可能」）。

    ``kind``：``damaged``、``downed``、``moved``、``fell``、``deadly_terrain``、``escaped``、
    ``status``、``surface``、``terrain``、``object_damaged``、``object_destroyed``、
    ``object_exploded``、``object_ignited``、``object_moved``、``reaction``、``intercepted``
    （``unit_id`` 是守護者、``detail`` 是被保護的單位）、``stacks``（2E-3；``detail`` 是
    ``層數:原因``）、``trap_placed``、``trap_triggered``。
    """

    kind: str
    unit_id: UnitId | None = None
    object_id: ObjectId | None = None
    pos: XY | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class DamageRange:
    """對主要目標的傷害（``minimum``／``maximum`` 為命中時的範圍；``expected`` 已乘上命中率）。"""

    minimum: int
    maximum: int
    expected: Fraction
    expected_if_hit: Fraction


@dataclass(frozen=True, slots=True)
class StatusChance:
    """技能施加在某個目標身上的、需要抵抗判定的狀態（命中之後）。

    ``status_id`` 是 Boss 轉換之後實際施加的狀態（``original_id`` 為技能寫的狀態）；
    ``apply_chance`` 為施加成功率（攻方勝出），``resist_chance`` ＝ 1 − 施加成功率。
    已含控制遞減（``diminished``）。
    """

    status_id: str
    original_id: str
    apply_chance: Fraction
    diminished: bool = False

    @property
    def resist_chance(self) -> Fraction:
        return 1 - self.apply_chance


@dataclass(frozen=True, slots=True)
class TargetPreview:
    """技能對一個需要命中判定的單位的預覽（沒有傷害效果時 ``damage`` 為 ``None``）。"""

    unit_id: UnitId
    hit_chance: Fraction
    crit_chance: Fraction
    damage: DamageRange | None
    ally: bool = False
    knock_chance: Fraction | None = None
    """技能含 ``knock_prone`` 且會對這個單位生效時，擊倒的對抗成功率（命中之後；比照推擊、絆倒的
    :func:`_maneuver_chance`）；沒有擊倒效果時為 ``None``。"""
    status_chances: tuple[StatusChance, ...] = ()
    """技能會對這個敵方單位施加、且要擲抵抗判定的狀態（定身、暈眩……）的施加成功率；
    預覽的 ``min`` 視為全部被抵抗、``max`` 視為全部施加成功。"""


@dataclass(frozen=True, slots=True)
class PierceInfo:
    """穿透技能的射線（Phase 3C-5b）。

    ``route``：施放者與目標之間的格子（直線為影響範圍）；``objects``：穿過的 ``penetrable`` 物件
    ``(物件 ID, 位置)``；``behind``：位於它們後方的單位（只受 ``behind_permille``‰ 傷害）。"""

    route: tuple[XY, ...]
    objects: tuple[tuple[ObjectId, XY], ...]
    behind: tuple[UnitId, ...]
    behind_permille: int


@dataclass(frozen=True, slots=True)
class ToppleInfo:
    """預覽中發生的推倒（Phase 3C-5b；取自 ``object_toppled`` 事件）：物件、倒下的方向、壓住的
    格子、壓到的單位與倒塌物的位置。"""

    object_id: ObjectId
    pos: XY
    direction: XY
    tiles: tuple[XY, ...]
    units: tuple[UnitId, ...]
    rubble: XY | None


@dataclass(frozen=True, slots=True)
class SummonInfo:
    """預覽中會出現的召喚物（Phase 3D-4b；取自 ``unit_summoned`` 事件與模擬後的狀態）。

    ``expires_round``：在召喚者這一輪的回合結束時消失；``totem_radius``：圖騰的光環半徑（不是圖騰
    為 ``None``）；``replaces``：因超過上限而消失的舊召喚物（最舊的先）。"""

    unit_id: UnitId
    template_id: str
    name_zh: str
    pos: XY
    expires_round: int
    max_hp: int
    totem_radius: int | None
    replaces: tuple[UnitId, ...]


@dataclass(frozen=True, slots=True)
class BombInfo:
    """預覽中會綁上的定時炸彈（Phase 3D-8b；取自 ``status_applied`` 的 ``time_bomb``）：攜帶者、倒數
    的環境回合數、爆炸半徑，以及以攜帶者 **目前位置** 展開的波及格子（它會移動，所以只是參考）。"""

    unit_id: UnitId
    rounds: int
    radius: int
    tiles: tuple[XY, ...]


@dataclass(frozen=True, slots=True)
class ReviveInfo:
    """預覽中的復活（Phase 3D-8b；取自 ``unit_revived``）：站起來的單位、HP 與站的格子（原位置被
    占用時為最近的空格，``from_pos`` 是倒下的位置）。"""

    unit_id: UnitId
    hp: int
    pos: XY
    from_pos: XY


@dataclass(frozen=True, slots=True)
class GrantInfo:
    """預覽中暫時獲得的技能（Phase 3D-8c；取自 ``skill_granted``）：誰、獲得哪個技能、持續幾輪
    （``refreshed``：已經暫時擁有，只刷新輪數）。"""

    unit_id: UnitId
    skill_id: str
    name_zh: str
    duration: int
    refreshed: bool


@dataclass(frozen=True, slots=True)
class HurlInfo:
    """預覽中發生的物件投擲（Phase 3C-5b；取自 ``object_hurled`` 事件）。

    ``outcome`` 為 ``exploded``／``shattered``／``placed``／``lost``，``placed`` 時 ``placed_pos``
    是物件停下的格子。"""

    object_id: ObjectId
    kind: str
    from_pos: XY
    to_pos: XY
    outcome: str
    placed_pos: XY | None


@dataclass(frozen=True, slots=True)
class MoveInfo:
    """預覽中發生的自身位移（Phase 3D-2；取自 ``unit_dashed``、``unit_moved`` 的 ``leap``／
    ``swap``）。

    ``kind``：``dash``（``path`` 為衝鋒的路線，含起點與終點，``other_id`` 是衝鋒的目標）、
    ``charge``（Phase 3D-2c 直線衝撞：``path`` 是依序經過的格子，含起點、含有單位的格子與停下的
    格子；沿途的敵人在 ``Preview.targets``）、
    ``leap``（``path`` 是起點與落點）、``shadowstep``（Phase 3D-8d 瞬步：``path`` 是起點與落點）、
    ``swap``（``unit_id`` 與 ``other_id`` 交換，``path`` 是
    ``unit_id`` 的起點與終點）。"""

    kind: str
    unit_id: UnitId
    other_id: UnitId | None
    path: tuple[XY, ...]


@dataclass(frozen=True, slots=True)
class DisplaceCheck:
    """位移他人的抵抗判定預覽（Phase 3D-2b）：敵方單位 ``unit_id`` 被移動的成功率 ``chance``
    （攻方勝出；精確機率，窮舉 d20），``resist_bonus`` 是它的抵抗加成（傳送敵人、致命地形），
    ``lethal`` 為落點是致命地形。友方不檢定，不列入。"""

    unit_id: UnitId
    chance: Fraction
    resist_bonus: int
    lethal: bool


@dataclass(frozen=True, slots=True)
class GambleOutcome:
    """賭注的一個分支的預覽（Phase 3D-7a）：``kind`` 為 ``win``／``lose``，``chance`` 是這個分支發生
    的機率（命中之後）。``preview`` 是強制這個分支時的完整預覽（AI 以它評分；目標的傷害範圍已含
    ``damage_multiplier``）。其餘為顯示用的摘要：``multiplier_permille`` 本次傷害的倍率（沒有
    ``damage_multiplier`` 為 1000）、``self_damage`` 施放者自己受到的傷害（最少與最多，含失敗
    分支的反噬）、``self_statuses`` 施放者獲得的狀態、``self_healed`` 施放者回復的 HP。"""

    kind: Literal["win", "lose"]
    chance: Fraction
    multiplier_permille: int
    self_damage: tuple[int, int]
    self_statuses: tuple[str, ...]
    self_healed: tuple[int, int]
    preview: Preview


@dataclass(frozen=True, slots=True)
class GambleInfo:
    """賭注技能的預覽（Phase 3D-7a）：成功率與兩個分支（依序 ``win``、``lose``）。"""

    chance_permille: int
    branches: tuple[GambleOutcome, GambleOutcome]


@dataclass(frozen=True, slots=True)
class Preview:
    action: Action
    hit_chance: Fraction | None
    """命中率（攻擊）或成功率（推擊、絆倒）；攻擊物件為 1；其他動作為 ``None``。
    攻擊單位時已包含高度、半掩護與優劣勢（隱蔽、倒地、天氣）。"""
    crit_chance: Fraction | None
    damage: DamageRange | None
    affected_tiles: tuple[XY, ...]
    affected_units: tuple[UnitId, ...]
    certain: tuple[Outcome, ...]
    possible: tuple[Outcome, ...]
    min_events: tuple[EventBase, ...]
    max_events: tuple[EventBase, ...]
    min_state: BattleState
    max_state: BattleState
    cover: Cover | None = None
    """攻擊單位時目標受到的半掩護（來源物件與懲罰）；沒有時為 ``None``。"""
    notes: tuple[str, ...] = ()
    """命中修正的說明（繁體中文），例如 ``("半掩護 −2：木箱 (3, 4)",)``。"""
    targets: tuple[TargetPreview, ...] = ()
    """技能：每個需要命中判定的單位（依單位 ID）的命中率、暴擊率與傷害範圍。"""
    healed: tuple[tuple[UnitId, int, int], ...] = ()
    """技能：治療 ``(單位, 最少, 最多)``（含所有治療效果的總和）。"""
    ap_cost: int | None = None
    """這個動作花的 AP（含修正規則的 ``ap_delta``，Phase 3C-2）；不花 AP 的動作為 ``None``。"""
    reach: int | None = None
    """射程（普攻與有射程的技能，含修正規則的 ``range_delta``）；其他動作為 ``None``。"""
    collisions: tuple[tuple[UnitId, int, int], ...] = ()
    """撞擊傷害（Phase 3C-3a）：``(單位, 最少, 最多)``，含行動者造成的所有撞擊傷害（被推的單位與
    被撞到的單位；最少後果的模擬中推擊失敗時為 0）。"""
    pierce: PierceInfo | None = None
    """穿透的射線（Phase 3C-5b）：動作是穿透的技能（含 ``grant_pierce``）時才有。"""
    topples: tuple[ToppleInfo, ...] = ()
    """動作會造成的推倒（Phase 3C-5b；最多後果的模擬，依物件 ID）。"""
    hurls: tuple[HurlInfo, ...] = ()
    """動作會造成的物件投擲（Phase 3C-5b；最多後果的模擬）。"""
    moves: tuple[MoveInfo, ...] = ()
    """動作的自身位移（衝鋒的路線、跳躍的落點、交換位置的兩格；Phase 3D-2；最多後果的模擬）。
    位移他人（Phase 3D-2b）：``teleport``（``unit_id`` 被傳到 ``path`` 的終點）與 ``swap``。"""
    displace_checks: tuple[DisplaceCheck, ...] = ()
    """技能的位移抵抗判定（Phase 3D-2b：``swap``、``swap_any``、``teleport_target`` 的敵方）。"""
    displace_chance: Fraction | None = None
    """位移他人成功的總機率（所有敵方目標都沒抵抗成功）；沒有檢定（全是友方）為 ``None``。"""
    summons: tuple[SummonInfo, ...] = ()
    """動作會召喚的單位（Phase 3D-4b；召喚位置、持續與被擠掉的舊召喚物）。"""
    bombs: tuple[BombInfo, ...] = ()
    """動作會綁上的定時炸彈（Phase 3D-8b；最多後果的模擬）：倒數與爆炸範圍。"""
    revives: tuple[ReviveInfo, ...] = ()
    """動作會復活的單位（Phase 3D-8b）。"""
    grants: tuple[GrantInfo, ...] = ()
    """動作會讓誰暫時獲得哪個技能（Phase 3D-8c）。"""
    run_range: tuple[XY, ...] = ()
    """跑步（Phase 3-20）：跑完之後本回合能走到的格子（依 (y, x)；不含目前位置）；其他動作為空。"""
    gamble: GambleInfo | None = None
    """技能有賭注時（Phase 3D-7a）：成功率與兩個分支各自的預覽。本預覽的其他欄位（傷害範圍、
    確定與可能的連鎖）不含賭注的分支，只算賭注以外的效果。"""
    miss_notes: tuple[str, ...] = ()
    """技能有失手反噬 ``cost.on_miss`` 時（Phase 3D-7a）：反噬的說明（「失手時：你獲得倒地」）；
    預覽模擬只算命中的情形，所以反噬不在其他欄位裡。"""
    backstab: tuple[UnitId, ...] = ()
    """行動者會從背後攻擊的單位（Phase 3D-8d；最多後果的模擬中命中判定帶背刺加成的目標，依 ID）。
    命中率與暴擊率已包含背刺與潛行偷襲的加成；說明在 ``notes``。"""
    landing: XY | None = None
    """複合技能（Phase 3F-3a）：第二段的原點（「位移 → 動作」為位移段的落點；3F-4a 的其他種類為
    最多後果的模擬裡第二段的原點，第二段沒有結算時為 ``None``）；其他動作為 ``None``。"""
    followup_tiles: tuple[XY, ...] = ()
    """複合技能：第二段的影響格（``affected_tiles`` 已含兩段）。"""
    followup_when: str | None = None
    """複合技能第二段的種類（``followup.when``，Phase 3F-4b；網頁依此寫說明）；其他動作為 ``None``。
    延遲段的 ``landing``／``followup_tiles`` 是施放後以施放者位置推算的預計範圍。"""


# ---------------------------------------------------------------------------
# 機率
# ---------------------------------------------------------------------------


def _naturals(advantage: str) -> Counter[int]:
    """自然骰的分布（次數，總和 20 或 400）。"""
    if advantage == "none":
        return Counter(range(1, 21))
    pick = max if advantage == "advantage" else min
    return Counter(pick(a, b) for a, b in product(range(1, 21), repeat=2))


def _chances(
    naturals: Counter[int], bonus: int, target: int, crit_range: int
) -> tuple[Fraction, Fraction]:
    total = sum(naturals.values())
    hit = sum(n for nat, n in naturals.items() if is_hit(nat, nat + bonus, target))
    crit = sum(
        n for nat, n in naturals.items() if is_hit(nat, nat + bonus, target) and nat >= crit_range
    )
    return Fraction(hit, total), Fraction(crit, total)


def _exploding_die(sides: int, rerolls: int) -> Counter[int]:
    """一顆會爆骰的 ``sides`` 面骰的總和分布（次數）：擲到最大值再加擲一次，最多再擲 ``rerolls``
    次。分母為 ``sides ** (rerolls + 1)``。"""
    if rerolls <= 0 or sides <= 1:
        return Counter(range(1, sides + 1))
    again = _exploding_die(sides, rerolls - 1)
    total = sum(again.values())
    dist: Counter[int] = Counter({face: total for face in range(1, sides)})
    for value, n in again.items():
        dist[sides + value] += n
    return dist


def dice_distribution(count: int, sides: int, explode_max: int = 0) -> Counter[int]:
    """``count`` 顆 ``sides`` 面骰總和的分布（次數）。``count == 0`` 時為 ``{0: 1}``。

    ``explode_max > 0``：每顆骰會爆骰（Phase 3D-7b，每顆最多再擲 ``explode_max`` 次）。
    """
    die = _exploding_die(sides, explode_max)
    dist: Counter[int] = Counter({0: 1})
    for _ in range(count):
        nxt: Counter[int] = Counter()
        for value, n in dist.items():
            for face, weight in die.items():
                nxt[value + face] += n * weight
        dist = nxt
    return dist


def _expected(dist: Counter[int], amount: dict[int, int]) -> Fraction:
    total = sum(dist.values())
    return Fraction(sum(amount[s] * n for s, n in dist.items()), total)


# ---------------------------------------------------------------------------
# 連鎖摘要
# ---------------------------------------------------------------------------


def _xy(pos: object) -> XY | None:
    x, y = getattr(pos, "x", None), getattr(pos, "y", None)
    return None if x is None or y is None else (x, y)


def _outcome(e: EventBase) -> Outcome | None:  # noqa: C901, PLR0911, PLR0912
    if isinstance(e, DamageDealt):
        return Outcome("damaged", unit_id=e.target_id, detail=e.cause)
    if isinstance(e, ShieldGained):
        return Outcome("shield", unit_id=e.unit_id)
    if isinstance(e, UnitDowned):
        return Outcome("downed", unit_id=e.unit_id)
    if isinstance(e, UnitMoved) and e.mode not in ("walk", "dash"):  # 衝鋒每一步由 MoveInfo 顯示
        return Outcome("moved", unit_id=e.unit_id, pos=_xy(e.to_pos), detail=e.mode)
    if isinstance(e, UnitFell):
        return Outcome("fell", unit_id=e.unit_id)
    if isinstance(e, EnteredDeadlyTerrain):
        return Outcome("deadly_terrain", unit_id=e.unit_id, pos=_xy(e.pos))
    if isinstance(e, UnitEscaped):
        return Outcome("escaped", unit_id=e.unit_id)
    if isinstance(e, StatusApplied):
        return Outcome("status", unit_id=e.target_id, detail=e.status_id)
    if isinstance(e, SurfaceChanged):
        return Outcome("surface", pos=_xy(e.pos), detail=e.after.value)
    if isinstance(e, TerrainChanged):
        return Outcome("terrain", pos=_xy(e.pos), detail=f"{e.terrain_after}:{e.height_after}")
    if isinstance(e, ObjectDamaged):
        return Outcome("object_damaged", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectDestroyed):
        return Outcome("object_destroyed", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectExploded):
        return Outcome("object_exploded", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectIgnited):
        return Outcome("object_ignited", object_id=e.object_id, pos=_xy(e.pos))
    if isinstance(e, ObjectMoved):
        return Outcome("object_moved", object_id=e.object_id, pos=_xy(e.to_pos))
    if isinstance(e, ReactionTriggered):
        return Outcome("reaction", unit_id=e.unit_id, detail=e.reaction)
    if isinstance(e, AttackIntercepted):
        return Outcome("intercepted", unit_id=e.guardian_id, detail=e.target_id)
    if isinstance(e, StacksChanged):
        return Outcome("stacks", unit_id=e.unit_id, detail=f"{e.stack_id}:{e.reason}")
    if isinstance(e, TrapPlaced):
        return Outcome("trap_placed", unit_id=e.owner_id, pos=_xy(e.pos), detail=e.skill_id)
    if isinstance(e, TrapTriggered):
        return Outcome("trap_triggered", unit_id=e.unit_id, pos=_xy(e.pos), detail=e.skill_id)
    return None


def outcomes(events: list[EventBase]) -> list[Outcome]:
    """事件 → 連鎖結果（去除重複，保留第一次出現的順序）。"""
    seen: dict[Outcome, None] = {}
    for e in events:
        o = _outcome(e)
        if o is not None:
            seen.setdefault(o, None)
    return list(seen)


def _affected(
    state: BattleState, events: list[EventBase]
) -> tuple[tuple[XY, ...], tuple[UnitId, ...]]:
    tiles: set[XY] = set()
    units: set[UnitId] = set()
    for o in outcomes(events):
        if o.pos is not None:
            tiles.add(o.pos)
        if o.unit_id is not None:
            units.add(o.unit_id)
            unit = state.units.get(o.unit_id)
            if unit is not None:
                tiles.add(unit.xy)
        if o.object_id is not None and o.object_id in state.objects:
            tiles.add(state.objects[o.object_id].xy)
    return tuple(sorted(tiles, key=lambda p: (p[1], p[0]))), tuple(sorted(units))


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def _primary_damage(events: list[EventBase], actor: UnitId, target: str) -> EventBase | None:
    for e in events:
        if isinstance(e, DamageDealt | ObjectDamaged) and e.cause == "attack":
            key = e.target_id if isinstance(e, DamageDealt) else e.object_id
            if e.source_id == actor and key == target:
                return e
    return None


def _amount_table(
    state: BattleState,
    unit: UnitState,
    sums: list[int],
    *,
    mod_ppm: int,
    weather: int,
    mult: int,
    status_ppm: int,
    shield: int = 0,
) -> dict[int, int]:
    weapon = unit.weapon
    core = state.ruleset.core
    scaled = weapon_attribute(state.ruleset, unit) * core.basic_attack_attr_multiplier_permille
    table: dict[int, int] = {}
    for s in sums:
        raw = (s + weapon.flat) * PERMILLE + scaled
        amount = max(
            raw
            * mod_ppm
            * weather
            * mult
            * status_ppm
            // (PERMILLE * PPM * PERMILLE * PERMILLE * PPM),
            core.min_damage_on_hit,
        )
        table[s] = max(0, amount - shield)  # 護盾先吸收；表中是實際扣血
    return table


def _cover_notes(cover: Cover | None) -> tuple[str, ...]:
    if cover is None:
        return ()
    x, y = cover.pos
    return (f"半掩護 −{cover.penalty}：{cover.name_zh} ({x}, {y})",)


def _attack_numbers(
    state: BattleState,
    action: Attack,
    actor: UnitState,
    min_events: list[EventBase],
    max_events: list[EventBase],
) -> tuple[Fraction, Fraction, DamageRange | None]:
    core = state.ruleset.core
    if action.target_object_id is not None:
        hit, crit = Fraction(1), Fraction(0)
        crit_dist: Counter[int] = Counter()
        target_key: str = action.target_object_id
    else:
        assert action.target_id is not None
        target = state.units[action.target_id]
        cover = half_cover(state, actor, target)
        bonus = (
            hit_modifier(actor, target, state.ruleset)
            + core.proficiency
            + situational_modifier(state, actor, target)
            + weapon_hit_bonus(actor, manhattan(actor.xy, target.xy))
            - (0 if cover is None else cover.penalty)
            + modifiers.hit_bonus(state, actor, modifiers.ATTACK, Subject(target, target.xy))
        )
        positional = positional_bonus(state, actor, target, weapon_profile(state, actor))
        naturals = _naturals(advantage_state(state, actor, target))
        hit, crit = _chances(
            naturals, bonus + positional.hit, core.hit_target, positional.crit_range
        )
        dice = attack_dice(state, actor)
        crit_dist = dice_distribution(dice.count * 2, dice.sides)
        target_key = action.target_id
    low = _primary_damage(min_events, actor.id, target_key)
    high = _primary_damage(max_events, actor.id, target_key)
    if low is None or high is None:
        return hit, crit, None
    dice = attack_dice(state, actor)
    normal_dist = dice_distribution(dice.count, dice.sides)
    status_ppm = PPM
    shield = 0
    if isinstance(low, DamageDealt):
        mod, weather, mult = low.element_mod_ppm, low.weather_permille, low.multiplier_permille
        status_ppm = low.status_ppm
        shield = shield_amount(state.ruleset, state.units[low.target_id])
    else:
        assert action.target_object_id is not None
        obj = state.objects[action.target_object_id]
        use = modifiers.ATTACK
        mod, weather = PPM, _object_weather(state, actor)
        mult = modifiers.damage_permille(state, actor, use, Subject(None, obj.xy))
    sums = sorted(set(normal_dist) | set(crit_dist))
    table = _amount_table(
        state,
        actor,
        sums,
        mod_ppm=mod,
        weather=weather,
        mult=mult,
        status_ppm=status_ppm,
        shield=shield,
    )
    e_normal = _expected(normal_dist, table)
    e_crit = _expected(crit_dist, table) if crit_dist else Fraction(0)
    expected_if_hit = Fraction(0) if hit == 0 else ((hit - crit) * e_normal + crit * e_crit) / hit
    damage = DamageRange(
        minimum=_dealt(low),
        maximum=_dealt(high),
        expected=expected_if_hit * hit,
        expected_if_hit=expected_if_hit,
    )
    return hit, crit, damage


def _dealt(event: EventBase) -> int:
    """主要傷害事件的實際扣血（傷害 − 護盾吸收）；物件傷害為 ``amount``。"""
    if isinstance(event, DamageDealt):
        return event.amount - event.absorbed
    return int(getattr(event, "amount", 0))


def _object_weather(state: BattleState, actor: UnitState) -> int:
    weather = state.weather
    if weather is None:
        return PERMILLE
    element = modifiers.damage_element(state, actor, modifiers.ATTACK, actor.weapon.element)
    return PERMILLE + weather.element_damage_permille.get(element, 0)


def _maneuver_chance(state: BattleState, actor: UnitState, action: Shove | Trip) -> Fraction:
    target = state.units[action.target_id]
    attr = Attribute.STR if isinstance(action, Shove) else Attribute.DEX
    rules = state.ruleset
    modifier = rules.hit_table.modifier(
        effective_attribute(rules, actor, attr), max(1, effective_attribute(rules, target, attr))
    )
    hit, _ = _chances(
        _naturals("none"), modifier + rules.core.proficiency, rules.core.hit_target, 21
    )
    return hit


def _preview_skill(state: BattleState, actor: UnitState, skill_id: str) -> SkillDef:
    """命中與傷害估計用的技能：複合技能（Phase 3F-3a）把兩段的效果接在一起（位移段、動作段的命中
    判定都以同一個技能 ID 記錄）；其他技能就是施放時的技能。"""
    skill = modifiers.acting_skill(state, actor, skill_id)
    follow = skill.followup_skill()
    if follow is None:
        return skill
    return skill.model_copy(update={"effects": (*skill.effects, *follow.effects), "followup": None})


def _followup_when(state: BattleState, actor: UnitState, action: Action) -> str | None:
    if not isinstance(action, UseSkill):
        return None
    skill = modifiers.acting_skill(state, actor, action.skill_id)
    return None if skill.followup is None else skill.followup.when


def _simulated_second(
    max_events: list[EventBase],
) -> tuple[XY | None, tuple[XY, ...], tuple[UnitId, ...]]:
    """模擬裡的第二段：即時的第二段取 ``skill_followup``；延遲段（3F-4b）取 ``followup_charged``
    （蓄力時以施放者位置推算的預計範圍）。都沒有時為空。"""
    for e in max_events:
        if isinstance(e, SkillFollowup):
            return (e.origin.x, e.origin.y), tuple((p.x, p.y) for p in e.tiles), ()
        if isinstance(e, FollowupCharged):
            return (e.pos.x, e.pos.y), tuple((p.x, p.y) for p in e.tiles), ()
    return None, (), ()


def _followup_info(
    state: BattleState, actor: UnitState, action: Action, max_events: list[EventBase]
) -> tuple[XY | None, tuple[XY, ...], tuple[UnitId, ...]]:
    """複合技能的第二段：原點（「位移 → 動作」為落點）、影響格與單位；不是複合技能時為空。

    「位移 → 動作」以施放前的狀態推算（假設施放者已在落點）；其他種類（Phase 3F-4a）取最多後果的
    模擬裡第二段的 ``skill_followup`` 事件（第二段沒有結算——沒有觸發、或還沒選目標——時為空）。"""
    if not isinstance(action, UseSkill):
        return None, (), ()
    skill = modifiers.acting_skill(state, actor, action.skill_id)
    if skill.followup is None:
        return None, (), ()
    if skill.followup.when != "after_move":
        return _simulated_second(max_events)
    origin = followup_origin(state, actor, skill, action)
    if origin is None:
        return None, (), ()
    _, area = followup_selection(state, actor, skill, action, origin)
    return origin, area.tiles, area.units


def _damage_expectation(  # noqa: PLR0917
    state: BattleState,
    actor: UnitState,
    action: UseSkill,
    target_id: UnitId,
    hit: Fraction,
    crit: Fraction,
    min_events: list[EventBase],
    max_events: list[EventBase],
) -> DamageRange | None:
    """技能對 ``target_id`` 的傷害範圍：最少／最多取自模擬事件，期望值依效果的骰子分布精確計算
    （事件與效果數量對不上時退回最少與最多的平均）。"""
    skill = _preview_skill(state, actor, action.skill_id)

    def direct(events: list[EventBase]) -> list[DamageDealt]:
        return [
            e
            for e in events
            if isinstance(e, DamageDealt)
            and e.cause == "attack"
            and e.source_id == actor.id
            and e.target_id == target_id
        ]

    low, high = direct(min_events), direct(max_events)
    if not low or not high:
        return None
    minimum = sum(e.amount - e.absorbed for e in low)
    maximum = sum(e.amount - e.absorbed for e in high)
    target = state.units[target_id]
    specs = [
        skill.effects[r.spec_index]
        for r in resolve_effects(state, skill)
        if r.type == "damage"
        and condition_met(
            state, actor, skill.effects[r.spec_index].condition, Subject(target, target.xy)
        )
    ]
    if hit == 0:
        return DamageRange(minimum, maximum, Fraction(0), Fraction(0))
    if len(specs) != len(low):
        mid = Fraction(minimum + maximum, 2)
        return DamageRange(minimum, maximum, mid * hit, mid)
    core = state.ruleset.core
    total = Fraction(0)
    shield = shield_amount(
        state.ruleset, target
    )  # 依序被每個傷害效果吸收（以最少後果估計用掉的量）
    for spec, event in zip(specs, low, strict=True):
        params = damage_parameters(state, actor, skill, spec, modified=True)
        dice = params.dice
        count, sides = (0, 1) if dice is None else (dice.count, dice.sides)
        explode = core.explode_max if spec.explode else 0
        normal = dice_distribution(count, sides, explode)
        doubled = dice_distribution(count * 2, sides, explode)
        table: dict[int, int] = {}
        for value in sorted(set(normal) | set(doubled)):
            raw = (value + params.flat) * PERMILLE + params.scaled_permille
            nominal = max(
                raw
                * event.element_mod_ppm
                * event.weather_permille
                * event.multiplier_permille
                * event.status_ppm
                // (PERMILLE * PPM * PERMILLE * PERMILLE * PPM),
                core.min_damage_on_hit,
            )
            table[value] = max(0, nominal - shield)
        shield = max(0, shield - event.amount)
        total += ((hit - crit) * _expected(normal, table) + crit * _expected(doubled, table)) / hit
    return DamageRange(minimum, maximum, total * hit, total)


def _knock_chance(
    state: BattleState, actor: UnitState, skill: SkillDef, target: UnitState
) -> Fraction | None:
    """技能對 ``target`` 的擊倒對抗成功率（技能屬性對相同屬性）；不會擊倒時為 ``None``。"""
    enemy = target.team is not actor.team
    resolved = resolve_effects(state, skill)
    prone = any(
        r.type == "knock_prone" and (r.affects == "all" or (enemy and r.affects == "enemies"))
        for r in resolved
    )
    charge_prone = enemy and any(
        r.type == CHARGE_THROUGH and skill.effects[r.spec_index].on_hit == "knock_prone"
        for r in resolved
    )
    if not (prone or charge_prone):
        return None
    attr = skill.scaling_attr
    rules = state.ruleset
    modifier = rules.hit_table.modifier(
        skill_scaling_value(rules, actor, skill), max(1, effective_attribute(rules, target, attr))
    )
    hit, _ = _chances(
        _naturals("none"), modifier + rules.core.proficiency, rules.core.hit_target, 21
    )
    return hit


def _status_chances(
    state: BattleState, actor: UnitState, skill: SkillDef, target: UnitState
) -> tuple[StatusChance, ...]:
    """技能對敵方 ``target`` 施加、且要擲抵抗判定的狀態（含 Boss 轉換與控制遞減）。"""
    if target.team is actor.team:
        return ()
    chances: dict[str, StatusChance] = {}
    for resolved in resolve_effects(state, skill):
        spec = skill.effects[resolved.spec_index]
        if resolved.type != "apply_status" or resolved.affects not in ("enemies", "all"):
            continue
        assert spec.status is not None
        if not condition_met(state, actor, spec.condition, Subject(target, target.xy)):
            continue
        plan = plan_status(state, target, spec.status)
        if plan.save_attr is None:
            continue
        chance = status_save_chance(state, skill_scaling_value(state.ruleset, actor, skill), plan)
        chances[plan.status_id] = StatusChance(
            plan.status_id, plan.original_id, chance, plan.diminished
        )
    return tuple(chances[k] for k in sorted(chances))


def _positions_at_roll(
    actor: UnitState, events: list[EventBase], skill_id: str
) -> dict[UnitId, UnitState]:
    """每個被擲命中的單位 → 擲骰當下的施放者（只有施放者在技能中途移動時才有，例如直線衝撞從
    經過敵人前的格子出手；命中率要以那個位置計算）。"""
    here = actor.pos
    out: dict[UnitId, UnitState] = {}
    for e in events:
        if isinstance(e, UnitMoved) and e.unit_id == actor.id:
            here = e.to_pos
        elif (
            isinstance(e, AttackRolled)
            and e.skill_id == skill_id
            and e.attacker_id == actor.id
            and here != actor.pos
            and e.target_id not in out
        ):
            moved = actor.clone()
            moved.pos = here
            out[e.target_id] = moved
    return out


def _skill_targets(
    state: BattleState,
    actor: UnitState,
    action: UseSkill,
    min_events: list[EventBase],
    max_events: list[EventBase],
) -> tuple[TargetPreview, ...]:
    skill = _preview_skill(state, actor, action.skill_id)
    profile = skill_profile(state, actor, skill)
    use = modifiers.skill_use(skill)
    core = state.ruleset.core
    rolled = sorted(
        {e.target_id for e in max_events if isinstance(e, AttackRolled) and e.skill_id == skill.id}
    )
    result: list[TargetPreview] = []
    at_roll = _positions_at_roll(actor, max_events, skill.id)
    for uid in rolled:
        target = state.units[uid]
        shooter = at_roll.get(uid, actor)  # 直線衝撞：從經過時的位置出手
        cover = half_cover(state, shooter, target, profile)
        bonus = (
            hit_modifier(shooter, target, state.ruleset, profile)
            + core.proficiency
            + situational_modifier(state, shooter, target)
            + (
                weapon_hit_bonus(shooter, manhattan(shooter.xy, target.xy))
                if profile.weapon_attack
                else 0
            )
            - (0 if cover is None else cover.penalty)
            + modifiers.hit_bonus(state, actor, use, Subject(target, target.xy))
        )
        positional = positional_bonus(state, shooter, target, profile)  # 背刺：以出手的位置判斷
        naturals = _naturals(advantage_state(state, shooter, target, profile))
        hit, crit = _chances(
            naturals, bonus + positional.hit, core.hit_target, positional.crit_range
        )
        damage = _damage_expectation(state, actor, action, uid, hit, crit, min_events, max_events)
        knock = _knock_chance(state, actor, skill, target)
        result.append(
            TargetPreview(
                uid,
                hit,
                crit,
                damage,
                ally=target.team is actor.team,
                knock_chance=knock,
                status_chances=_status_chances(state, actor, skill, target),
            )
        )
    return tuple(result)


def _skill_heals(
    actor: UnitState, min_events: list[EventBase], max_events: list[EventBase]
) -> tuple[tuple[UnitId, int, int], ...]:
    def totals(events: list[EventBase]) -> dict[UnitId, int]:
        out: dict[UnitId, int] = {}
        for e in events:
            if isinstance(e, Healed) and e.source_id == actor.id:
                out[e.target_id] = out.get(e.target_id, 0) + e.amount
        return out

    low, high = totals(min_events), totals(max_events)
    return tuple((uid, low.get(uid, 0), high[uid]) for uid in sorted(high))


def _collision_damage(
    actor: UnitState, min_events: list[EventBase], max_events: list[EventBase]
) -> tuple[tuple[UnitId, int, int], ...]:
    def totals(events: list[EventBase]) -> dict[UnitId, int]:
        out: dict[UnitId, int] = {}
        for e in events:
            if isinstance(e, DamageDealt) and e.cause == "collision" and e.source_id == actor.id:
                out[e.target_id] = out.get(e.target_id, 0) + e.amount - e.absorbed
        return out

    low, high = totals(min_events), totals(max_events)
    return tuple((uid, low.get(uid, 0), high[uid]) for uid in sorted(high))


def _run_range(after: BattleState, actor: UnitState) -> tuple[XY, ...]:
    """跑步之後（``after`` 為模擬後的狀態）行動者本回合能停留的格子（不含目前位置）。"""
    unit = after.units[actor.id]
    budget = available_move_budget(after, unit)
    if budget is None:
        return ()
    pm = path_map(after, unit, budget)
    ends = (xy for xy in pm.cost if xy != unit.xy and pm.can_end_at(xy))
    return tuple(sorted(ends, key=lambda p: (p[1], p[0])))


def _cost_and_reach(
    state: BattleState, actor: UnitState, action: Action
) -> tuple[int | None, int | None]:
    """動作的 AP 與射程（含修正規則）；移動、防禦、結束回合等為 ``(None, None)``。"""
    if isinstance(action, Attack):
        return action_ap_cost(state, actor, modifiers.ATTACK), attack_reach(state, actor)
    if isinstance(action, Shove):
        return action_ap_cost(state, actor, modifiers.SHOVE), None
    if isinstance(action, Trip):
        return action_ap_cost(state, actor, modifiers.TRIP), None
    if isinstance(action, Interact):
        return action_ap_cost(state, actor, modifiers.INTERACT), None
    if isinstance(action, UseSkill):
        skill = modifiers.acting_skill(state, actor, action.skill_id)
        reach = shape_reach(state, skill, actor) if skill.shape.range is not None else None
        return skill_ap_cost(state, skill, actor), reach
    return None, None


def _pierce_info(state: BattleState, actor: UnitState, action: UseSkill) -> PierceInfo | None:
    """穿透技能的射線（只讀目前狀態）；不是穿透的技能為 ``None``。"""
    skill = modifiers.acting_skill(state, actor, action.skill_id)
    if not pierce_active(state, actor, skill):
        return None
    area = compute_area(state, actor, skill, action)
    trace = pierce_trace(state, actor, skill.shape.type, area)
    return PierceInfo(
        route=trace.route,
        objects=tuple(zip(trace.objects, trace.object_tiles, strict=True)),
        behind=trace.behind,
        behind_permille=state.ruleset.core.pierce_behind_permille,
    )


def _scene_infos(
    events: list[EventBase],
) -> tuple[tuple[ToppleInfo, ...], tuple[HurlInfo, ...]]:
    """模擬事件中的推倒與物件投擲（每個物件只取第一次）。"""
    topples: dict[ObjectId, ToppleInfo] = {}
    hurls: dict[ObjectId, HurlInfo] = {}
    for e in events:
        if isinstance(e, ObjectToppled) and e.object_id not in topples:
            topples[e.object_id] = ToppleInfo(
                object_id=e.object_id,
                pos=(e.pos.x, e.pos.y),
                direction=e.direction,
                tiles=tuple((p.x, p.y) for p in e.tiles),
                units=e.units,
                rubble=None if e.rubble_pos is None else (e.rubble_pos.x, e.rubble_pos.y),
            )
        elif isinstance(e, ObjectHurled) and e.object_id not in hurls:
            hurls[e.object_id] = HurlInfo(
                object_id=e.object_id,
                kind=e.kind,
                from_pos=(e.from_pos.x, e.from_pos.y),
                to_pos=(e.to_pos.x, e.to_pos.y),
                outcome=e.outcome,
                placed_pos=None if e.placed_pos is None else (e.placed_pos.x, e.placed_pos.y),
            )
    return tuple(topples.values()), tuple(hurls.values())


def _bomb_infos(state: BattleState, events: list[EventBase]) -> tuple[BombInfo, ...]:
    """模擬事件中綁上的定時炸彈（``state`` 為模擬後的狀態，用來查炸彈的技能與半徑）。"""
    infos: list[BombInfo] = []
    for e in events:
        if not (isinstance(e, StatusApplied) and e.status_id == TIME_BOMB):
            continue
        carrier = state.units.get(e.target_id)
        status = None if carrier is None else carrier.get_status(TIME_BOMB)
        if carrier is None or status is None or status.skill_id is None:
            continue
        radius = bomb_spec(state, status.skill_id).radius or 0
        infos.append(
            BombInfo(
                unit_id=carrier.id,
                rounds=status.remaining or 0,
                radius=radius,
                tiles=blast_tiles(state, carrier.pos, radius),
            )
        )
    return tuple(infos)


def _grant_infos(state: BattleState, events: list[EventBase]) -> tuple[GrantInfo, ...]:
    """模擬事件中暫時獲得的技能（``state`` 用來查技能名稱）。"""
    return tuple(
        GrantInfo(
            unit_id=e.unit_id,
            skill_id=e.skill_id,
            name_zh=state.ruleset.skill_def(e.skill_id).name_zh,
            duration=e.duration,
            refreshed=e.refreshed,
        )
        for e in events
        if isinstance(e, SkillGranted)
    )


def _revive_infos(events: list[EventBase]) -> tuple[ReviveInfo, ...]:
    """模擬事件中的復活。"""
    return tuple(
        ReviveInfo(
            unit_id=e.unit_id,
            hp=e.hp,
            pos=(e.pos.x, e.pos.y),
            from_pos=(e.from_pos.x, e.from_pos.y),
        )
        for e in events
        if isinstance(e, UnitRevived)
    )


def _summon_infos(state: BattleState, events: list[EventBase]) -> tuple[SummonInfo, ...]:
    """模擬事件中的召喚（``state`` 為動作前的狀態，用來查範本；``limit`` 消失的舊召喚物並入
    新召喚物的 ``replaces``）。"""
    infos: list[SummonInfo] = []
    replaced: list[UnitId] = []
    for e in events:
        if isinstance(e, SummonExpired) and e.reason == "limit":
            replaced.append(e.unit_id)
        elif isinstance(e, UnitSummoned):
            try:
                template = state.ruleset.summon_def(e.template_id).template
            except KeyError:
                continue
            infos.append(
                SummonInfo(
                    unit_id=e.unit_id,
                    template_id=e.template_id,
                    name_zh=template.name_zh,
                    pos=(e.pos.x, e.pos.y),
                    expires_round=e.expires_round,
                    max_hp=state.ruleset.core.template_max_hp(template),
                    totem_radius=None if template.totem is None else template.totem.radius,
                    replaces=tuple(replaced),
                )
            )
            replaced = []
    return tuple(infos)


def _displace_checks(
    state: BattleState, actor: UnitState, action: UseSkill
) -> tuple[DisplaceCheck, ...]:
    """位移類技能的抵抗判定：每個敵方被移動的單位（依單位 ID）的精確成功率。"""
    skill = modifiers.acting_skill(state, actor, action.skill_id)
    kinds = {e.type for e in skill.effects}
    if not kinds & {SWAP, SWAP_ANY, TELEPORT_TARGET}:
        return ()
    core = state.ruleset.core
    bonus, lethal = 0, False
    ids = [action.target_id, action.second_target_id]
    if TELEPORT_TARGET in kinds and action.target_pos is not None:
        lethal = is_deadly(state, (action.target_pos.x, action.target_pos.y))
        bonus = core.teleport_enemy_resist_bonus + (
            core.teleport_lethal_resist_bonus if lethal else 0
        )
        ids = [action.target_id]
    attack = skill_scaling_value(state.ruleset, actor, skill)
    checks = [
        DisplaceCheck(
            unit_id=unit.id,
            chance=contest_chance(state, unit, skill.scaling_attr, attack, bonus),
            resist_bonus=bonus,
            lethal=lethal,
        )
        for unit in sorted((state.units[i] for i in ids if i is not None), key=lambda u: u.id)
        if unit.team is not actor.team
    ]
    return tuple(checks)


def _displace_notes(
    state: BattleState, actor: UnitState, action: UseSkill, skill: SkillDef
) -> tuple[str, ...]:
    """傳送他人的說明：Boss 對傳送到致命地形免疫（致命地形不會出現在可選的落點）。"""
    if not any(e.type == TELEPORT_TARGET for e in skill.effects) or action.target_id is None:
        return ()
    target = state.units[action.target_id]
    if target.team is actor.team or not target.has_tag(BOSS_TAG):
        return ()
    return (f"{target.name_zh} 是 Boss：對傳送到致命地形免疫，致命地形不能選為落點",)


def _move_infos(events: list[EventBase]) -> tuple[MoveInfo, ...]:
    """模擬事件中的自身位移：衝鋒（路線）、跳躍（落點）、交換位置（兩個單位換格）。"""
    infos: list[MoveInfo] = []
    swapped: dict[UnitId, UnitMoved] = {}
    for e in events:
        if isinstance(e, UnitDashed):
            path = tuple((p.x, p.y) for p in e.path)
            infos.append(MoveInfo("dash", e.unit_id, e.target_id, path))
        elif isinstance(e, UnitCharged):
            infos.append(MoveInfo("charge", e.unit_id, None, tuple((p.x, p.y) for p in e.path)))
        elif isinstance(e, UnitMoved) and e.mode in ("leap", "shadowstep"):
            path = ((e.from_pos.x, e.from_pos.y), (e.to_pos.x, e.to_pos.y))
            infos.append(MoveInfo(e.mode, e.unit_id, None, path))
        elif isinstance(e, UnitMoved) and e.mode == "teleported":
            path = ((e.from_pos.x, e.from_pos.y), (e.to_pos.x, e.to_pos.y))
            infos.append(MoveInfo("teleport", e.unit_id, None, path))
        elif isinstance(e, UnitMoved) and e.mode == "swap":
            swapped[e.unit_id] = e
    ids = list(swapped)
    for first, second in zip(ids[::2], ids[1::2], strict=False):
        a = swapped[first]
        infos.append(
            MoveInfo(
                "swap",
                first,
                second,
                ((a.from_pos.x, a.from_pos.y), (a.to_pos.x, a.to_pos.y)),
            )
        )
    return tuple(infos)


def _gamble_spec(state: BattleState, actor: UnitState, action: Action) -> EffectSpec | None:
    """動作是帶賭注的技能時，它的 ``gamble`` 效果；否則 ``None``。"""
    if not isinstance(action, UseSkill):
        return None
    skill = modifiers.acting_skill(state, actor, action.skill_id)
    return next((e for e in skill.effects if e.type == GAMBLE), None)


def _self_totals(actor: UnitState, events: list[EventBase]) -> tuple[int, tuple[str, ...], int]:
    """模擬事件中施放者自己受到的傷害（扣掉護盾）、獲得的狀態與回復的 HP。"""
    damage, healed = 0, 0
    statuses: list[str] = []
    for e in events:
        if isinstance(e, DamageDealt) and e.target_id == actor.id and e.source_id == actor.id:
            damage += e.amount - e.absorbed
        elif isinstance(e, StatusApplied) and e.target_id == actor.id and e.source_id == actor.id:
            if e.status_id not in statuses:
                statuses.append(e.status_id)
        elif isinstance(e, Healed) and e.target_id == actor.id:
            healed += e.amount
    return damage, tuple(statuses), healed


def _gamble_outcome(
    state: BattleState,
    action: Action,
    stripped: BattleState,
    spec: EffectSpec,
    kind: Literal["win", "lose"],
) -> GambleOutcome:
    """強制賭注走 ``kind`` 分支的預覽（最少後果與最多後果各模擬一次）。"""
    assert spec.chance_permille is not None
    actor = _actor(state, action)
    low, high = simulate_preview(stripped, action, kind)
    branch = _build(state, action, actor, low, high)
    effects = (spec.win if kind == "win" else spec.lose) or ()
    multiplier = PERMILLE
    for sub in effects:
        if sub.type == DAMAGE_MULTIPLIER and sub.damage_multiplier_permille is not None:
            multiplier = multiplier * sub.damage_multiplier_permille // PERMILLE
    low_damage, _, low_heal = _self_totals(actor, list(low.events))
    high_damage, statuses, high_heal = _self_totals(actor, list(high.events))
    permille = spec.chance_permille if kind == "win" else PERMILLE - spec.chance_permille
    return GambleOutcome(
        kind=kind,
        chance=Fraction(permille, PERMILLE),
        multiplier_permille=multiplier,
        self_damage=(min(low_damage, high_damage), max(low_damage, high_damage)),
        self_statuses=statuses,
        self_healed=(min(low_heal, high_heal), max(low_heal, high_heal)),
        preview=branch,
    )


def _miss_notes(state: BattleState, actor: UnitState, action: Action) -> tuple[str, ...]:
    """失手反噬的說明（Phase 3D-7a）：每個反噬效果一行。"""
    if not isinstance(action, UseSkill):
        return ()
    skill = modifiers.acting_skill(state, actor, action.skill_id)
    lines: list[str] = []
    for sub in skill.cost.on_miss:
        if sub.type == "apply_status" and sub.status is not None:
            lines.append(f"失手時：你獲得「{state.ruleset.status_def(sub.status).name_zh}」")
        elif sub.type == "damage":
            lines.append("失手時：你受到反噬傷害（不會讓你的 HP 低於 1）")
    return tuple(lines)


def _backstab_targets(actor: UnitState, events: list[EventBase]) -> tuple[UnitId, ...]:
    """行動者的命中判定中帶背刺加成的目標（Phase 3D-8d，依 ID）。"""
    return tuple(
        sorted(
            {
                e.target_id
                for e in events
                if isinstance(e, AttackRolled) and e.attacker_id == actor.id and e.backstab
            }
        )
    )


def _positional_notes(
    state: BattleState, actor: UnitState, events: list[EventBase], backstab: tuple[UnitId, ...]
) -> tuple[str, ...]:
    """背刺與潛行偷襲的說明（Phase 3D-8d），例如「背刺 盜賊1：命中 +2、暴擊範圍 +1」。"""
    core = state.ruleset.core
    lines = [
        f"背刺 {state.units[uid].name_zh}：命中 +{core.backstab_hit_bonus}、"
        f"暴擊範圍 +{core.backstab_crit_range_bonus}（從背後近戰攻擊）"
        for uid in backstab
    ]
    if any(isinstance(e, AttackRolled) and e.attacker_id == actor.id and e.ambush for e in events):
        lines.append(f"潛行偷襲：隱蔽中出手，命中 +{core.ambush_hit_bonus}（攻擊結算完後脫離隱蔽）")
    return tuple(lines)


def preview(state: BattleState, action: Action) -> Preview:
    """預覽 ``action`` 的結果（不修改 ``state``、不消耗亂數）。

    不合法時拋出 ``IllegalActionError``。技能有賭注（Phase 3D-7a）時，``gamble`` 另外附上兩個
    分支各自的完整預覽；其餘欄位只算賭注以外的效果。
    """
    actor = _actor(state, action)
    stripped = strip_hidden_traps(state, actor.team)
    low, high = simulate_preview(stripped, action)
    base = _build(state, action, actor, low, high)
    spec = _gamble_spec(state, actor, action)
    if spec is None or spec.chance_permille is None:
        return base
    win = _gamble_outcome(state, action, stripped, spec, "win")
    lose = _gamble_outcome(state, action, stripped, spec, "lose")
    return replace(base, gamble=GambleInfo(spec.chance_permille, (win, lose)))


def _basic_ap_cost(state: BattleState, action: Action, default: int | None) -> int | None:
    """基本動作（跑步、守護、換位、瞄準、攀跳）與裝填的 AP 花費；其他動作沿用 ``default``。"""
    core = state.ruleset.core
    costs: dict[type, int] = {
        Run: core.run_ap_cost,
        Defend: core.defend_ap_cost,
        Swap: core.swap_ap_cost,
        Aim: core.aim_ap_cost,
        Vault: core.vault_ap_cost,
    }
    if isinstance(action, Reload):
        return state.units[action.unit_id].weapon.reload_ap
    return costs.get(type(action), default)


def _build(
    state: BattleState,
    action: Action,
    actor: UnitState,
    low: ResolveResult,
    high: ResolveResult,
) -> Preview:
    """由兩次模擬（最少與最多後果）整理成 :class:`Preview`（不含賭注的分支）。"""
    min_events, max_events = list(low.events), list(high.events)
    hit: Fraction | None = None
    crit: Fraction | None = None
    damage: DamageRange | None = None
    cover: Cover | None = None
    if isinstance(action, Attack):
        hit, crit, damage = _attack_numbers(state, action, actor, min_events, max_events)
        if action.target_id is not None:
            cover = half_cover(state, actor, state.units[action.target_id])
    elif isinstance(action, Shove | Trip):
        hit, crit = _maneuver_chance(state, actor, action), Fraction(0)
    targets: tuple[TargetPreview, ...] = ()
    healed: tuple[tuple[UnitId, int, int], ...] = ()
    if isinstance(action, UseSkill):
        targets = _skill_targets(state, actor, action, min_events, max_events)
        healed = _skill_heals(actor, min_events, max_events)
    certain = outcomes(min_events)
    certain_set = set(certain)
    possible = [o for o in outcomes(max_events) if o not in certain_set]
    tiles, units = _affected(high.state, max_events)
    landing, follow_tiles, follow_units = _followup_info(state, actor, action, max_events)
    if isinstance(action, UseSkill):
        area = compute_area(
            state, actor, modifiers.acting_skill(state, actor, action.skill_id), action
        )
        tiles = tuple(sorted({*tiles, *area.tiles, *follow_tiles}, key=lambda p: (p[1], p[0])))
        units = tuple(sorted({*units, *area.units, *follow_units}))
    ap_cost, reach = _cost_and_reach(state, actor, action)
    ap_cost = _basic_ap_cost(state, action, ap_cost)
    pierce = _pierce_info(state, actor, action) if isinstance(action, UseSkill) else None
    topples, hurls = _scene_infos(max_events)
    checks: tuple[DisplaceCheck, ...] = ()
    notes = _cover_notes(cover)
    if isinstance(action, Attack) and action.target_id is not None:  # 武器命中特性（3-24a1）
        notes += actor.weapon.trait_lines_zh(on_hit_only=True)
    backstab = _backstab_targets(actor, max_events)
    notes += _positional_notes(state, actor, max_events, backstab)
    if isinstance(action, UseSkill):
        checks = _displace_checks(state, actor, action)
        notes += _displace_notes(
            state, actor, action, modifiers.acting_skill(state, actor, action.skill_id)
        )
    chance: Fraction | None = None
    if checks:
        chance = Fraction(1)
        for check in checks:
            chance *= check.chance
    return Preview(
        action=action,
        hit_chance=hit,
        crit_chance=crit,
        damage=damage,
        affected_tiles=tiles,
        affected_units=units,
        certain=tuple(certain),
        possible=tuple(possible),
        min_events=tuple(min_events),
        max_events=tuple(max_events),
        min_state=low.state,
        max_state=high.state,
        cover=cover,
        notes=notes,
        targets=targets,
        healed=healed,
        ap_cost=ap_cost,
        reach=reach,
        collisions=_collision_damage(actor, min_events, max_events),
        pierce=pierce,
        topples=topples,
        hurls=hurls,
        moves=_move_infos(max_events),
        displace_checks=checks,
        displace_chance=chance,
        summons=_summon_infos(state, max_events),
        bombs=_bomb_infos(high.state, max_events),
        revives=_revive_infos(max_events),
        grants=_grant_infos(state, max_events),
        run_range=_run_range(high.state, actor) if isinstance(action, Run) else (),
        miss_notes=_miss_notes(state, actor, action),
        backstab=backstab,
        landing=landing,
        followup_tiles=follow_tiles,
        followup_when=_followup_when(state, actor, action),
    )
