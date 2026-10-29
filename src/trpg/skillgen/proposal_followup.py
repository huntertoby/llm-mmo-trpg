"""LLM 提議的複合技能第二段（``followup``；Phase 4-L8，``docs/design/06-技能.md`` 6.23）。

提議的 ``followup`` 與 :class:`~trpg.content.skills.FollowupSpec` 同形（``when``、``skeleton``、
``shape``、``effects``、``condition``、``release``），但只有結構：第二段效果的數值由補值器補
（預算器的旋鈕也調第二段，見 :mod:`trpg.skillgen.proposal_budget`）。這裡只決定 **schema 裡列哪些
值**（純函式、只看內容資料與引擎常數）：

- ``when``：六種時機（:data:`~trpg.content.skills.FOLLOWUP_WHEN_VALUES`），說明見
  :data:`FOLLOWUP_WHEN_HINTS`（時機本身是引擎的 ``Literal``，說明跟著放在程式）；
- ``shape``：任何一種時機的第二段可能用到的形狀（動作段、擊殺後第二段、延遲段，加上位移原語自己的
  形狀）；
- ``effects``：第二段不能用的原語（:data:`~trpg.content.skills.FOLLOWUP_FORBIDDEN`：位移、召喚、
  區域、陷阱等）不列——施放者自身位移（:data:`~trpg.content.skills.COMPOSITE_MOVES`）例外，
  「動作 → 位移」與「擊殺 → 接下一段」的第二段可以用。

各時機的細部規則（第一段只能是一個位移、聚集段只能是 pull、以原點為中心的形狀 ``range: 0``、兩段
合計最多 4 個效果、不帶變奏）由 ``SkillDef`` 的驗證器檢查，錯誤帶 ``followup`` 路徑回給 LLM。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from trpg.content.library import ContentLibrary
from trpg.content.skills import (
    COMPOSITE_KIND_ZH,
    COMPOSITE_MOVES,
    DELAYED_RELEASE_VALUES,
    DELAYED_SHAPES,
    FOLLOWUP_FORBIDDEN,
    FOLLOWUP_SHAPES,
    FOLLOWUP_WHEN_VALUES,
)
from trpg.content.skills.constants import ON_KILL_SECOND_SHAPES

__all__ = [
    "FOLLOWUP_DOC",
    "FOLLOWUP_WHEN_HINTS",
    "RELEASE_HINTS",
    "followup_effect_ids",
    "followup_shape_ids",
    "followup_when_entries",
    "release_entries",
]

FOLLOWUP_WHEN_HINTS: dict[str, str] = {
    "after_move": "第一段只有一個施放者自身位移；真的移動到落點後，以落點為原點施放第二段。",
    "after_action": "第一段是動作；結算完後施放者再做第二段的一個自身位移（打帶跑）。",
    "after_gather": "第一段只有一個把敵人拉向聚集點的 pull；第二段以聚集點為中心打擊。",
    "on_kill": "第一段是有傷害的動作；擊倒目標才施放第二段（動作或位移後再動作）。",
    "on_hit": "第一段是有傷害的動作；命中才對同一個目標施放第二段。",
    "delayed": "第一段施放後蓄力；release 成立時以施放者當下位置為中心施放第二段。",
}
"""``followup.when`` 的說明（給 LLM；中性描述，不含數值）。"""
RELEASE_HINTS: dict[str, str] = {
    "next_turn": "施放者下回合開始時釋放。",
    "attacked": "施放者下回合開始前被敵人攻擊時釋放（沒被攻擊就失效）。",
}
"""延遲段 ``release`` 的說明。"""
FOLLOWUP_DOC = (
    "可省略，只有主動技能可用。複合技能的第二段：自己的骨架、形狀與效果，when 決定何時施放；"
    "兩段合計最多 4 個效果，複合技能不帶變奏。第二段不能有召喚、區域、陷阱等效果，也不能再接第二段"
)


def followup_when_entries() -> list[dict[str, str]]:
    """``available`` 用的時機清單（``id``、中文名、說明；依 :data:`FOLLOWUP_WHEN_VALUES`
    的順序）。"""
    return [
        {"id": w, "name_zh": COMPOSITE_KIND_ZH[w], "hint": FOLLOWUP_WHEN_HINTS[w]}
        for w in FOLLOWUP_WHEN_VALUES
    ]


def release_entries() -> list[dict[str, str]]:
    return [{"id": r, "hint": RELEASE_HINTS[r]} for r in DELAYED_RELEASE_VALUES]


def followup_shape_ids(library: ContentLibrary, shapes: Iterable[str]) -> list[str]:
    """第二段可用的形狀（``shapes`` 內、依 YAML 順序）：動作段、擊殺後第二段、延遲段的形狀，加上
    施放者自身位移原語允許的形狀。"""
    primitives = library.ruleset.primitives.by_id()
    allowed = {*FOLLOWUP_SHAPES, *ON_KILL_SECOND_SHAPES, *DELAYED_SHAPES}
    for move in COMPOSITE_MOVES:
        primitive = primitives.get(move)
        if primitive is not None and primitive.allowed_shapes:
            allowed.update(primitive.allowed_shapes)
    wanted = set(shapes)
    return [s.id for s in library.ruleset.shapes.shapes if s.id in wanted and s.id in allowed]


def followup_effect_ids(primitives: Sequence[str]) -> list[str]:
    """第二段可用的原語（保持 ``primitives`` 的順序）：不在 :data:`FOLLOWUP_FORBIDDEN`，或是施放者
    自身位移（:data:`COMPOSITE_MOVES`）。"""
    return [p for p in primitives if p not in FOLLOWUP_FORBIDDEN or p in COMPOSITE_MOVES]
