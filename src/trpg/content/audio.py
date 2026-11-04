"""音效參數表（``content/audio/sfx.yaml``，Phase AU-2；``docs/art/音效與音樂方案.md`` 第 4 節）。

純前端資料：前端 ``client/src/audio/synth.ts`` 用這些積木參數合成聲音，Python 端只驗證 schema
（``trpg content check``），不進引擎結算。每一層積木只能有一個種類鍵（``noise``、``tone``、``fm``、
``chord``、``pulses``、``crackle``），由鍵名分派到對應的 model。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Discriminator, Field, StrictBool, Tag, model_validator

from trpg.content.battle import ID_PATTERN
from trpg.content.schemas import ContentModel

__all__ = [
    "LAYER_KINDS",
    "ChordLayer",
    "CrackleLayer",
    "FmLayer",
    "NoiseLayer",
    "PulseLayer",
    "SfxDef",
    "SfxTable",
    "ToneLayer",
]

LAYER_KINDS: tuple[str, ...] = ("noise", "tone", "fm", "chord", "pulses", "crackle")
"""積木的種類鍵（與前端 ``LAYER_KINDS`` 相同）。"""

_MIN_HZ = 20.0
_MAX_HZ = 20000.0
_MAX_SECONDS = 6.0

Hz = Annotated[float, Field(ge=_MIN_HZ, le=_MAX_HZ)]
Seconds = Annotated[float, Field(gt=0, le=_MAX_SECONDS)]
Db = Annotated[float, Field(ge=-60, le=12)]
HzRange = Hz | tuple[Hz, Hz]
"""頻率，或 ``[起, 迄]`` 掃頻。"""
Env = (
    tuple[Annotated[float, Field(ge=0)], Annotated[float, Field(gt=0)]]
    | tuple[
        Annotated[float, Field(ge=0)], Annotated[float, Field(gt=0)], Annotated[float, Field(ge=0)]
    ]
)
"""包絡 ``[起音, 衰減到 −40 dB, 保持]``（秒）。"""


class _Layer(ContentModel):
    env: Env | None = None
    gain: Db = 0
    delay: Annotated[float, Field(ge=0, le=_MAX_SECONDS)] = 0


class NoiseLayer(_Layer):
    """濾波雜訊。"""

    noise: Literal["white", "band", "low", "high"]
    color: Literal["white", "pink", "brown"] = "white"
    freq: HzRange | None = None
    q: Annotated[float, Field(gt=0, le=40)] | None = None
    dur: Seconds

    @model_validator(mode="after")
    def _needs_freq(self) -> NoiseLayer:
        if self.noise != "white" and self.freq is None:
            raise ValueError(f"{self.noise} 雜訊需要 freq")
        return self


class ToneLayer(_Layer):
    """振盪器（可掃頻、顫音、低通）。"""

    tone: Literal["sine", "triangle", "square", "saw"]
    freq: HzRange
    vibrato: (
        tuple[Annotated[float, Field(gt=0, le=100)], Annotated[float, Field(ge=0, le=1200)]] | None
    ) = None
    lp: Hz | None = None
    dur: Seconds


class FmLayer(_Layer):
    """FM 鐘（bell）與金屬（metal）。"""

    fm: Literal["bell", "metal"]
    freq: HzRange
    ratio: Annotated[float, Field(gt=0, le=16)]
    index: (
        Annotated[float, Field(ge=0, le=30)]
        | tuple[Annotated[float, Field(ge=0, le=30)], Annotated[float, Field(ge=0, le=30)]]
    )
    dur: Seconds


class ChordLayer(_Layer):
    """和弦鐘（stagger＞0 是琶音）。"""

    chord: tuple[Hz, ...] = Field(min_length=1, max_length=8)
    stagger: Annotated[float, Field(ge=0, le=1)] = 0
    bright: Annotated[float, Field(ge=0, le=1)] = 0.5
    dur: Seconds


class PulseLayer(_Layer):
    """短脈衝序列（雜訊喀聲，或 ``pitch`` 的正弦啵聲）。"""

    pulses: Annotated[int, Field(ge=1, le=64)]
    every: Annotated[float, Field(gt=0, le=1)]
    jitter: Annotated[float, Field(ge=0, le=1)] = 0
    click: Annotated[float, Field(gt=0, le=0.5)]
    freq: HzRange | None = None
    q: Annotated[float, Field(gt=0, le=40)] | None = None
    pitch: HzRange | None = None
    fade: Annotated[float, Field(gt=0, le=1)] = 1
    dur: Seconds | None = None


class CrackleLayer(_Layer):
    """劈啪（時間由前端的種子決定）。"""

    crackle: Annotated[float, Field(gt=0, le=400)]
    click: Annotated[float, Field(gt=0, le=0.1)] | None = None
    freq: Hz
    q: Annotated[float, Field(gt=0, le=40)] | None = None
    dur: Seconds


def _layer_kind(value: Any) -> str | None:  # pydantic 的 callable discriminator 收原始值
    """依種類鍵分派；沒有或超過一個時回傳 ``None``（由 :class:`SfxDef` 給中文錯誤）。"""
    if isinstance(value, dict):
        found = [k for k in LAYER_KINDS if k in value]
    else:
        found = [k for k in LAYER_KINDS if getattr(value, k, None) is not None]
    return found[0] if len(found) == 1 else None


Layer = Annotated[
    Annotated[NoiseLayer, Tag("noise")]
    | Annotated[ToneLayer, Tag("tone")]
    | Annotated[FmLayer, Tag("fm")]
    | Annotated[ChordLayer, Tag("chord")]
    | Annotated[PulseLayer, Tag("pulses")]
    | Annotated[CrackleLayer, Tag("crackle")],
    Discriminator(
        _layer_kind,
        custom_error_type="layer_kind",
        custom_error_message="一層必須剛好有一個種類鍵（noise、tone、fm、chord、pulses、crackle）",
    ),
]

SfxCategory = Literal[
    "ui",
    "windup",
    "swing",
    "hit",
    "element",
    "result",
    "primitive",
    "status",
    "surface",
    "explosion",
    "step",
    "system",
    "ambient",
]


class SfxDef(ContentModel):
    """一個音效：中文名、分類、軌、積木清單。"""

    zh: str = Field(min_length=1)
    cat: SfxCategory
    use: str | None = None
    track: Literal["sfx", "ambient"] = "sfx"
    synth: Literal["full", "temp"] = "full"
    """full＝第一階段合成（○）；temp＝合成暫代、之後換取樣（△）。"""
    harsh: StrictBool = False
    """衝擊點綴（雷、爆炸）：減少刺耳音效開啟時，放在環境軌就不出聲。"""
    gain: Db = 0
    vary: Annotated[float, Field(ge=0, le=600)] = 0
    layers: tuple[Layer, ...] = Field(min_length=1, max_length=8)


class SfxTable(ContentModel):
    """``content/audio/sfx.yaml``：音效 ID → 參數表。"""

    sfx: dict[Annotated[str, Field(pattern=ID_PATTERN)], SfxDef] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> SfxTable:
        ui = sum(1 for d in self.sfx.values() if d.cat == "ui")
        if ui == 0:
            raise ValueError("至少要有一個介面音（cat: ui）")
        for sfx_id, d in self.sfx.items():
            if d.cat == "ambient" and d.track != "ambient":
                raise ValueError(f"{sfx_id}：cat 是 ambient 的音效必須放在 ambient 軌")
        return self

    def summary(self) -> str:
        ui = sum(1 for d in self.sfx.values() if d.cat == "ui")
        temp = sum(1 for d in self.sfx.values() if d.synth == "temp")
        return f"{len(self.sfx)} 個音效（介面音 {ui} 個、合成暫代 {temp} 個）"
