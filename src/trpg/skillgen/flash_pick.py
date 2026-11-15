"""閃現與重閃接上「挑選模式」（Phase PK-3；06 6.7、6.34.7 #165，提案第 2、3 節、7.7 第 2 段）。

``skill_pick.yaml`` 的 ``flash_enabled`` 為真、而且選項來源會挑選（:class:`PickingSource`，例：
``trpg.llm.flash_propose.LlmFlashSource``、重播的紀錄）時，:func:`trpg.skillgen.flash_offer.make_offer`
改走這裡：

1. **出題（程式）**：照原本的出題（沒有 LLM 時的那一份）決定每一格——每格的類別、不指定時的類別
   混合（至少 2 類）、指定類別只出該類、大變化的加深／橋接、補位的小變化、轉型保底（#70）佔的那
   一格與它的位置、強度下限（6.34.3、#160；例外格照舊標「比原本弱」）。這些都由程式決定，LLM 動
   不了。
2. **候選（程式）**：每格的第一個候選就是原本出題的那一個；其餘依同一類的用法統計排序
   （``FlashOptionSource.ranked``）往下取合格的變化（套得上、過強度下限），同一類的幾格輪流分，
   格與格之間不重複，每格最多 ``pool.flash_top_k`` 個。轉型保底那一格固定（只有那一個）。
3. **挑選（LLM）**：來源的 :meth:`PickingSource.pick` 為每格挑一個位置、給文字（描述；大變化與轉型
   另有名稱）。位置超出範圍、固定格挑了別的，一律當第一個。
4. 選中的變化掛上文字（:func:`~trpg.skillgen.flash_text.clean_text`）後重新套用一次（文字影響
   名稱與技能 ID），格子順序照原本。

沒有挑選器時第一個候選就是原本那一個，所以結果和原本出題逐字相同。純函式、確定性：LLM 的回答由外層
記錄（重播用紀錄裡的位置，不呼叫 LLM）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_state import Variation
from trpg.skillgen.flash_text import VariationText

__all__ = [
    "FlashPicks",
    "FlashSlot",
    "PickingSource",
    "SlotOption",
    "flash_pick_on",
    "picks_by_key",
]


class SlotOption(Protocol):
    """候選（``trpg.skillgen.flash_offer.FlashOption`` 的介面；避免循環匯入）。"""

    @property
    def variation(self) -> Variation: ...

    @property
    def skill(self) -> SkillDef: ...

    @property
    def summary_zh(self) -> str: ...

    @property
    def weaker(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class FlashSlot:
    """閃現題目的一格：在選項裡的位置、類別、候選（第一個是原本出題的那一個）、是不是固定格
    （轉型保底：LLM 只取名，不挑）。"""

    index: int
    category: str
    candidates: tuple[SlotOption, ...]
    fixed: bool = False

    @property
    def named(self) -> bool:
        """這一格的變化會改名（大變化、轉型；06 6.34.3「小變化不改名」）。"""
        return self.candidates[0].variation.source != "minor"


@dataclass(frozen=True, slots=True)
class FlashPicks:
    """挑選的結果：每格選第幾個候選（依格子順序）、文字（鍵＝變化的穩定鍵）。"""

    positions: tuple[int, ...]
    texts: Mapping[str, VariationText] = field(default_factory=dict)


@runtime_checkable
class PickingSource(Protocol):
    """會挑選的閃現選項來源（PK-3）：LLM 挑選器或重播的紀錄。"""

    def pick(
        self,
        library: ContentLibrary,
        request: object,
        slots: Sequence[FlashSlot],
        before: SkillDef,
    ) -> FlashPicks:
        """為每格挑一個候選（``request`` 是 ``FlashRequest``；``before`` 是套用前的技能）。"""
        ...


def flash_pick_on(library: ContentLibrary, source: object) -> bool:
    """這一次出題走挑選模式：開關（``skill_pick.yaml`` 的 ``flash_enabled``）打開而且來源會挑選。"""
    return library.skill_pick.flash_enabled and isinstance(source, PickingSource)


def picks_by_key(slots: Sequence[FlashSlot], accepted: Sequence[Variation]) -> tuple[int, ...]:
    """重播：紀錄裡收下的變化（依格子順序）換回每格的位置；找不到的格子用第一個。"""
    keys = {v.key() for v in accepted}
    return tuple(
        next((i for i, c in enumerate(slot.candidates) if c.variation.key() in keys), 0)
        for slot in slots
    )
