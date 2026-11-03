"""路徑預覽的請求與回應（Phase 6A-4b；``POST /api/battles/{id}/path-preview``）。

:class:`trpg.engine.path_preview.PathPreview` 的公開版本：機率改成整數千分比，座標用 ``[x, y]``。
畫面依這份資料畫路徑提示（``docs/art/戰鬥D版樣張.md`` 第 3 節），不自己算規則。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from trpg.api.schemas import permille
from trpg.engine.path_preview import PathEvent, PathEventKind, PathPreview, PathStep, StepReach
from trpg.shared.types import Pos, Surface, UnitId

__all__ = [
    "PathEventOut",
    "PathPreviewOut",
    "PathPreviewRequest",
    "PathStepOut",
    "path_preview_out",
]

type XY = tuple[int, int]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PathPreviewRequest(_ApiModel):
    """恰好給 ``path``（格子序列，``path[0]`` 為目前位置、之後每一步相鄰）或 ``dest``（終點：取
    本回合的最短路徑）其中一個。``unit_id`` 省略時為主角（目前只能預覽主角）。"""

    unit_id: UnitId | None = None
    path: tuple[Pos, ...] | None = None
    dest: Pos | None = None

    @model_validator(mode="after")
    def _one_of(self) -> PathPreviewRequest:
        if (self.path is None) == (self.dest is None):
            raise ValueError("要給 path 或 dest 其中一個")
        if self.path is not None and not self.path:
            raise ValueError("path 不可為空")
        return self


class PathEventOut(_ApiModel):
    kind: PathEventKind
    """``stood_up``、``surface``、``slip_check``、``trap``、``damage``、``status``、``reaction``、
    ``displaced``、``surface_changed``、``fell``、``deadly``、``downed``、``escaped``、``stopped``
    （各欄位的意思見 ``trpg.engine.path_preview.PathEventKind``）。"""
    certain: bool
    """確定會發生；``false`` 為「可能」（看骰子或反應的決定）。"""
    other_id: UnitId | None
    status_id: str | None
    surface: Surface | None
    pos: XY | None
    amount_min: int | None
    """傷害的最小值；只有骰子不利時才會受傷（例如藉機攻擊命中）時為 ``null``。"""
    amount_max: int | None
    chance_permille: int | None
    """``slip_check`` 的失敗機率（‰，四捨五入）。"""
    detail: str | None


class PathStepOut(_ApiModel):
    pos: XY
    index: int
    surface: Surface
    """這一格目前的表面（畫路徑分段顏色：冰藍、火紅……；``water`` 為潮濕）。"""
    trap: bool
    """看得見的敵方陷阱。"""
    reach: StepReach
    """``certain`` 一定走到、``possible`` 看骰子、``interrupted`` 會在之前被打斷、``unreachable``
    到不了。"""
    events: tuple[PathEventOut, ...]


class PathPreviewOut(_ApiModel):
    unit_id: UnitId
    path: tuple[XY, ...]
    legal_length: int
    """合法前段的格數（含起點）；0 表示一步都不能走。"""
    reachable: bool
    reason: str | None
    """路徑不合法的原因（繁體中文；合法時為 ``null``）。"""
    steps: tuple[PathStepOut, ...]
    stop: XY
    """骰子都有利時的停點。"""
    worst_stop: XY
    """骰子都不利時的停點（與 ``stop`` 相同時停點確定）。"""
    stop_certain: bool
    certain: bool
    """整個預覽都確定：與實際移動完全一致。"""
    move_cost: int


def _event_out(event: PathEvent) -> PathEventOut:
    return PathEventOut(
        kind=event.kind,
        certain=event.certain,
        other_id=event.other_id,
        status_id=event.status_id,
        surface=event.surface,
        pos=event.pos,
        amount_min=event.amount_min,
        amount_max=event.amount_max,
        chance_permille=permille(event.chance),
        detail=event.detail,
    )


def _step_out(step: PathStep) -> PathStepOut:
    return PathStepOut(
        pos=step.pos,
        index=step.index,
        surface=step.surface,
        trap=step.trap,
        reach=step.reach,
        events=tuple(_event_out(e) for e in step.events),
    )


def path_preview_out(p: PathPreview) -> PathPreviewOut:
    return PathPreviewOut(
        unit_id=p.unit_id,
        path=p.path,
        legal_length=p.legal_length,
        reachable=p.reachable,
        reason=p.reason,
        steps=tuple(_step_out(s) for s in p.steps),
        stop=p.stop,
        worst_stop=p.worst_stop,
        stop_certain=p.stop_certain,
        certain=p.certain,
        move_cost=p.move_cost,
    )
