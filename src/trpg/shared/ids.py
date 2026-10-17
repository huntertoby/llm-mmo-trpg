"""確定性的 ID 配發（取代 ``uuid4``）。"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["IdAllocator", "IdAllocatorState"]

_PREFIX_PATTERN = r"^[a-z][a-z0-9_]*$"


class IdAllocatorState(BaseModel):
    """:class:`IdAllocator` 的序列化狀態（可直接 ``model_dump()``／``model_dump_json()``）。"""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    prefix: str = Field(pattern=_PREFIX_PATTERN)
    issued: int = Field(ge=0, description="已配發的 ID 數量；下一個 ID 的序號為 issued + 1")


class IdAllocator:
    """以前綴與遞增計數產生確定性的 ID。

    >>> alloc = IdAllocator("unit")
    >>> alloc.next(), alloc.next()
    ('unit_0001', 'unit_0002')

    序號至少 4 位數、左側補零；超過 9999 後自然變成 5 位數以上（``unit_10000``）。
    前綴限小寫英文字母開頭，只含小寫英文、數字與底線。
    """

    __slots__ = ("_state",)

    def __init__(self, prefix: str) -> None:
        self._state = IdAllocatorState(prefix=prefix, issued=0)

    @property
    def prefix(self) -> str:
        return self._state.prefix

    def next(self) -> str:
        """配發下一個 ID。"""
        issued = self._state.issued + 1
        self._state = IdAllocatorState(prefix=self._state.prefix, issued=issued)
        return f"{self._state.prefix}_{issued:04d}"

    def get_state(self) -> IdAllocatorState:
        return self._state

    @classmethod
    def from_state(cls, state: IdAllocatorState) -> Self:
        alloc = cls(state.prefix)
        alloc._state = state
        return alloc

    def __repr__(self) -> str:
        return f"IdAllocator.from_state({self._state!r})"
