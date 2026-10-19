"""API 的請求與回應模型（Phase 3-2）。

引擎的 pydantic 模型（``Action``、``Pending``、``BattleView``、``OrderSet``……）直接當 API 格式；
這裡只定義 API 專屬的外層與 ``Preview``（引擎的 dataclass，含完整狀態，不能直接外流）的公開版本。

機率與期望值以 **整數千分比** 表示（``*_permille``、``*_milli``，四捨五入），與引擎的 ‰ 慣例一致。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from trpg.engine.actions import Action, Step
from trpg.engine.ai.orders import OrderSet
from trpg.engine.preview import DamageRange, Outcome, Preview, StatusChance, TargetPreview
from trpg.engine.results import Pending
from trpg.engine.view import BattleView
from trpg.shared.rng import MASK64
from trpg.shared.types import ObjectId, Team, UnitId

__all__ = [
    "Awaiting",
    "BattleOutcome",
    "BattleResponse",
    "BuildSummary",
    "CoverOut",
    "CreateBattleRequest",
    "DamageOut",
    "DecisionRequest",
    "HealOut",
    "MapSummary",
    "OutcomeOut",
    "PreviewOut",
    "StatusChanceOut",
    "StepOut",
    "TargetOut",
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


class StepOut(_ApiModel):
    """自動推進中結算的一步。``actor_id`` 與 ``step`` 在開場時為 ``None``。

    ``events`` 已依我方視角過濾（:func:`trpg.engine.event_filter.filter_events`），每個事件是
    事件的 JSON 再加上 ``text``（繁體中文描述；沒有描述的事件不含此鍵）。``seq`` 保留原值，
    過濾後可能跳號。
    """

    actor_id: UnitId | None
    step: Step | None
    events: tuple[dict[str, Any], ...]


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
    view: BattleView
    legal_actions: tuple[Action, ...]
    """輪到主角（``awaiting == "action"``）時的合法動作（含 ``end_turn``）；其他時候為空。"""
    pending: Pending | None
    """主角的反應詢問（只有公開欄位）。"""
    orders: OrderSet
    """我方隊友目前的戰術指令。"""
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


def preview_out(p: Preview) -> PreviewOut:
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
    )
