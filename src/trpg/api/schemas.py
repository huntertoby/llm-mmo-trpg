"""API 的請求與回應模型（Phase 3-2）。

引擎的 pydantic 模型（``Action``、``Pending``、``BattleView``、``OrderSet``……）直接當 API 格式；
這裡只定義 API 專屬的外層與 ``Preview``（引擎的 dataclass，含完整狀態，不能直接外流）的公開版本。

機率與期望值以 **整數千分比** 表示（``*_permille``、``*_milli``，四捨五入），與引擎的 ‰ 慣例一致。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.engine.actions import Action, Step, UseSkill
from trpg.engine.ai.orders import IgnoredOrder, OrderSet
from trpg.engine.preview import (
    DamageRange,
    HurlInfo,
    Outcome,
    PierceInfo,
    Preview,
    StatusChance,
    TargetPreview,
    ToppleInfo,
)
from trpg.engine.results import Pending
from trpg.engine.view import BattleView
from trpg.shared.rng import MASK64
from trpg.shared.types import ObjectId, Pos, Team, UnitId

__all__ = [
    "Awaiting",
    "BattleOutcome",
    "BattleResponse",
    "BuildSummary",
    "CoverOut",
    "CreateBattleRequest",
    "DamageOut",
    "DecisionRequest",
    "Glossary",
    "GlossaryEntry",
    "HealOut",
    "HurlOut",
    "InteractOptionOut",
    "MapSummary",
    "OutcomeOut",
    "PierceObjectOut",
    "PierceOut",
    "PreviewOut",
    "StatusChanceOut",
    "StepOut",
    "TargetOut",
    "TelegraphChangeOut",
    "TelegraphOut",
    "ToppleOut",
    "UpcomingEventOut",
    "permille",
    "preview_out",
]

type XY = tuple[int, int]

Awaiting = Literal["action", "decision", "ended", "stalled"]
"""伺服器在等什麼：主角的動作、主角的反應決定、戰鬥已結束；``stalled`` 只在自動推進超過步數
上限（500）之後出現。"""


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# 內容
# ---------------------------------------------------------------------------


class MapSummary(_ApiModel):
    id: str
    name_zh: str
    archetype: str
    width: int
    height: int


class BuildSummary(_ApiModel):
    id: str
    name_zh: str
    theme_zh: str
    skills: tuple[str, ...]


class GlossaryEntry(_ApiModel):
    id: str
    name_zh: str
    description_zh: str | None = None
    tags: tuple[str, ...] = ()


class Glossary(_ApiModel):
    """名詞對照表（由內容庫產生）：ID → 中文名與簡短說明。"""

    terrain: tuple[GlossaryEntry, ...]
    surfaces: tuple[GlossaryEntry, ...]
    objects: tuple[GlossaryEntry, ...]
    statuses: tuple[GlossaryEntry, ...]
    stacks: tuple[GlossaryEntry, ...]
    reactions: tuple[GlossaryEntry, ...]
    elements: tuple[GlossaryEntry, ...]
    attributes: tuple[GlossaryEntry, ...]


# ---------------------------------------------------------------------------
# 戰鬥
# ---------------------------------------------------------------------------


class CreateBattleRequest(_ApiModel):
    """建立戰鬥。``ally_builds`` 省略時與 ``trpg battle --ally-build <hero_build>`` 相同，以標準
    隊友補齊到 3 人；給了（可以是空串列）就只用 ``hero_build`` ＋ 這些 build。"""

    map_id: str
    seed: int = Field(ge=0, le=MASK64)
    hero_build: str
    ally_builds: tuple[str, ...] | None = None
    max_rounds: int = Field(default=30, ge=1, le=200)


class DecisionRequest(_ApiModel):
    accept: bool
    """反應詢問：是否使用反應；``copy_skill`` 選目標：``false`` 為放棄施放（不付代價）。"""
    copy_cast: UseSkill | None = None
    """``copy_skill`` 選目標（``pending.kind == "copy_skill"``）時，複製技能的選取（從回應的
    ``copy_options`` 挑一個）；反應詢問不使用。"""


class StepOut(_ApiModel):
    """自動推進中結算的一步。``actor_id`` 與 ``step`` 在開場時為 ``None``。

    ``events`` 已依我方視角過濾（:func:`trpg.engine.event_filter.filter_events`），每個事件是
    事件的 JSON 再加上 ``text``（繁體中文描述；沒有描述的事件不含此鍵）。``seq`` 保留原值，
    過濾後可能跳號。
    """

    actor_id: UnitId | None
    step: Step | None
    events: tuple[dict[str, Any], ...]
    view: BattleView
    """這一步結算後的戰場（我方視角）；前端逐步播放時用。"""


class TelegraphChangeOut(_ApiModel):
    """預告的一項變化（:class:`trpg.engine.environment.TelegraphChange` ＋ 中文 ``text``）。"""

    kind: str
    pos: Pos | None
    before: str | None
    after: str | None
    object_id: ObjectId | None
    unit_id: UnitId | None
    amount: int | None
    text: str


class BurningOut(_ApiModel):
    object_id: ObjectId
    pos: Pos
    remaining: int
    """還能撐幾次環境回合。"""
    text: str


class UpcomingEventOut(_ApiModel):
    round: int
    kind: str
    tiles: tuple[XY, ...]
    text: str


class TelegraphOut(_ApiModel):
    """下一次環境回合（本輪結束時）將發生的變化（Phase 3-4b）。以我方看得見的狀態模擬，
    不含隱藏陷阱與亂數狀態。"""

    round: int
    changes: tuple[TelegraphChangeOut, ...]
    burning: tuple[BurningOut, ...]
    upcoming: tuple[UpcomingEventOut, ...]
    """再下一輪結束時的地圖事件（提前一輪預告）。"""


class InteractOptionOut(_ApiModel):
    """主角相鄰的可推動物件的一種互動（推、往左撥、往右撥）及其是否合法（Phase 3C-1）。
    ``legal_actions`` 只列合法的；這裡連不合法的也列出，讓介面灰掉並顯示原因。"""

    object_id: ObjectId
    mode: Literal["push", "shove_aside"]
    side: Literal["left", "right"] | None
    legal: bool
    reason: str | None
    """不合法的原因（繁體中文）；合法時 ``None``。"""
    to_pos: Pos
    """物件會移到的格子（即使不合法也給出；可能在地圖外）。"""


class BattleOutcome(_ApiModel):
    winner: Team | None
    """``None`` 為平手。"""
    end_reason: str | None
    round: int


class BattleResponse(_ApiModel):
    """建立、讀取、動作、決定、戰術指令共用的回應。"""

    battle_id: str
    hero_id: UnitId
    awaiting: Awaiting
    initial_view: BattleView
    """本次請求開始推進 **之前** 的戰場（建立戰鬥時為開場事件之後、第一個動作之前）；沒有推進時
    與 ``view`` 相同。"""
    view: BattleView
    legal_actions: tuple[Action, ...]
    """輪到主角（``awaiting == "action"``）時的合法動作（含 ``end_turn``）；其他時候為空。"""
    interact_options: tuple[InteractOptionOut, ...]
    """輪到主角時，相鄰可推動物件的互動選項（含不合法與原因）；其他時候為空。"""
    pending: Pending | None
    copy_options: tuple[UseSkill, ...]
    """``pending.kind == "copy_skill"`` 時，複製技能（``pending.copy_skill_id``）目前所有合法的
    選取（``DecisionRequest.copy_cast`` 從中挑一個）；其他時候為空。"""
    """主角的反應詢問（只有公開欄位）。"""
    orders: OrderSet
    """我方隊友目前的戰術指令。"""
    orders_ignored: tuple[IgnoredOrder, ...]
    """目前指令中已經無法執行的（例如集火的目標已倒下）與原因；AI 會略過它們。"""
    telegraph: TelegraphOut
    """下一次環境回合的預告。"""
    steps: tuple[StepOut, ...]
    """這次請求推進的每一步（依序）。"""
    outcome: BattleOutcome | None
    """戰鬥結束時的勝負與原因。"""


# ---------------------------------------------------------------------------
# 預覽
# ---------------------------------------------------------------------------


def permille(value: Fraction | None) -> int | None:
    """``Fraction`` → 四捨五入的整數千分比（``None`` 照舊）。"""
    if value is None:
        return None
    scaled = value * 1000
    return (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)


def _milli(value: Fraction) -> int:
    result = permille(value)
    assert result is not None
    return result


class DamageOut(_ApiModel):
    minimum: int
    maximum: int
    expected_milli: int
    """期望傷害 ×1000（已乘上命中率）。"""
    expected_if_hit_milli: int


class OutcomeOut(_ApiModel):
    kind: str
    unit_id: UnitId | None
    object_id: ObjectId | None
    pos: XY | None
    detail: str | None


class StatusChanceOut(_ApiModel):
    status_id: str
    original_id: str
    apply_permille: int
    diminished: bool


class TargetOut(_ApiModel):
    unit_id: UnitId
    hit_permille: int
    crit_permille: int
    damage: DamageOut | None
    ally: bool
    knock_permille: int | None
    status_chances: tuple[StatusChanceOut, ...]


class CoverOut(_ApiModel):
    penalty: int
    object_id: ObjectId
    kind: str
    name_zh: str
    pos: XY


class HealOut(_ApiModel):
    unit_id: UnitId
    minimum: int
    maximum: int


class CollisionOut(_ApiModel):
    """撞擊傷害預覽（Phase 3C-3a）：某單位受到的撞擊傷害總和（最少、最多後果）。"""

    unit_id: UnitId
    minimum: int
    maximum: int


class PierceObjectOut(_ApiModel):
    object_id: ObjectId
    pos: XY


class PierceOut(_ApiModel):
    """穿透技能的射線預覽（Phase 3C-5b）：路線、穿過的物件與後方受打折傷害的單位。"""

    route: tuple[XY, ...]
    """施放者與目標之間的格子（不含兩端；直線為影響範圍）。"""
    objects: tuple[PierceObjectOut, ...]
    """穿過的 ``penetrable`` 物件（受全額傷害）。"""
    behind: tuple[UnitId, ...]
    """位於這些物件後方的單位。"""
    behind_permille: int
    """後方單位受到的傷害（‰）。"""


class ToppleOut(_ApiModel):
    """預覽中的推倒（Phase 3C-5b）：物件、倒下的方向、壓住的格子與單位、倒塌物的位置。"""

    object_id: ObjectId
    pos: XY
    direction: XY
    tiles: tuple[XY, ...]
    units: tuple[UnitId, ...]
    rubble: XY | None


class HurlOut(_ApiModel):
    """預覽中的物件投擲（Phase 3C-5b）：``outcome`` 為 exploded／shattered／placed／lost。"""

    object_id: ObjectId
    kind: str
    from_pos: XY
    to_pos: XY
    outcome: str
    placed_pos: XY | None


class PreviewOut(_ApiModel):
    """:class:`trpg.engine.preview.Preview` 的公開版本：不含模擬後的完整狀態與原始事件。"""

    action: Action
    hit_permille: int | None
    crit_permille: int | None
    damage: DamageOut | None
    affected_tiles: tuple[XY, ...]
    affected_units: tuple[UnitId, ...]
    certain: tuple[OutcomeOut, ...]
    """確定會發生的連鎖（最少後果的模擬）。"""
    possible: tuple[OutcomeOut, ...]
    """可能發生的連鎖（最多後果的模擬減去確定的部分）。"""
    cover: CoverOut | None
    notes: tuple[str, ...]
    targets: tuple[TargetOut, ...]
    healed: tuple[HealOut, ...]
    min_events: tuple[dict[str, Any], ...]
    """最少後果的模擬事件（我方視角過濾，附中文 ``text``）；連鎖預覽用。"""
    max_events: tuple[dict[str, Any], ...]
    """最多後果的模擬事件。"""
    ap_cost: int | None = None
    """這個動作花的 AP（含修正規則，Phase 3C-2）；不花 AP 的動作為 ``None``。"""
    reach: int | None = None
    """射程（普攻與有射程的技能，含修正規則）；其他動作為 ``None``。"""
    collisions: tuple[CollisionOut, ...] = ()
    """撞擊傷害（Phase 3C-3a）：每個單位的最少與最多。"""
    pierce: PierceOut | None = None
    """穿透技能的射線（Phase 3C-5b）；不是穿透的動作為 ``None``。"""
    topples: tuple[ToppleOut, ...] = ()
    """動作會造成的推倒（Phase 3C-5b）。"""
    hurls: tuple[HurlOut, ...] = ()
    """動作會造成的物件投擲（Phase 3C-5b）。"""


def _damage(d: DamageRange | None) -> DamageOut | None:
    if d is None:
        return None
    return DamageOut(
        minimum=d.minimum,
        maximum=d.maximum,
        expected_milli=_milli(d.expected),
        expected_if_hit_milli=_milli(d.expected_if_hit),
    )


def _outcome(o: Outcome) -> OutcomeOut:
    return OutcomeOut(
        kind=o.kind, unit_id=o.unit_id, object_id=o.object_id, pos=o.pos, detail=o.detail
    )


def _status_chance(c: StatusChance) -> StatusChanceOut:
    return StatusChanceOut(
        status_id=c.status_id,
        original_id=c.original_id,
        apply_permille=_milli(c.apply_chance),
        diminished=c.diminished,
    )


def _target(t: TargetPreview) -> TargetOut:
    return TargetOut(
        unit_id=t.unit_id,
        hit_permille=_milli(t.hit_chance),
        crit_permille=_milli(t.crit_chance),
        damage=_damage(t.damage),
        ally=t.ally,
        knock_permille=permille(t.knock_chance),
        status_chances=tuple(_status_chance(c) for c in t.status_chances),
    )


def _pierce(p: PierceInfo | None) -> PierceOut | None:
    if p is None:
        return None
    return PierceOut(
        route=p.route,
        objects=tuple(PierceObjectOut(object_id=o, pos=xy) for o, xy in p.objects),
        behind=p.behind,
        behind_permille=p.behind_permille,
    )


def _topple(t: ToppleInfo) -> ToppleOut:
    return ToppleOut(
        object_id=t.object_id,
        pos=t.pos,
        direction=t.direction,
        tiles=t.tiles,
        units=t.units,
        rubble=t.rubble,
    )


def _hurl(h: HurlInfo) -> HurlOut:
    return HurlOut(
        object_id=h.object_id,
        kind=h.kind,
        from_pos=h.from_pos,
        to_pos=h.to_pos,
        outcome=h.outcome,
        placed_pos=h.placed_pos,
    )


def preview_out(
    p: Preview,
    min_events: tuple[dict[str, Any], ...],
    max_events: tuple[dict[str, Any], ...],
) -> PreviewOut:
    cover = p.cover
    return PreviewOut(
        action=p.action,
        hit_permille=permille(p.hit_chance),
        crit_permille=permille(p.crit_chance),
        damage=_damage(p.damage),
        affected_tiles=p.affected_tiles,
        affected_units=p.affected_units,
        certain=tuple(_outcome(o) for o in p.certain),
        possible=tuple(_outcome(o) for o in p.possible),
        cover=(
            None
            if cover is None
            else CoverOut(
                penalty=cover.penalty,
                object_id=cover.object_id,
                kind=cover.kind,
                name_zh=cover.name_zh,
                pos=cover.pos,
            )
        ),
        notes=p.notes,
        targets=tuple(_target(t) for t in p.targets),
        healed=tuple(HealOut(unit_id=u, minimum=lo, maximum=hi) for u, lo, hi in p.healed),
        min_events=min_events,
        max_events=max_events,
        ap_cost=p.ap_cost,
        reach=p.reach,
        collisions=tuple(
            CollisionOut(unit_id=u, minimum=lo, maximum=hi) for u, lo, hi in p.collisions
        ),
        pierce=_pierce(p.pierce),
        topples=tuple(_topple(t) for t in p.topples),
        hurls=tuple(_hurl(h) for h in p.hurls),
    )
