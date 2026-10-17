"""trpg.shared.rng 的 hypothesis 屬性測試（未安裝 hypothesis 時整個檔案略過）。

mypy 設定說明：在沒有安裝 hypothesis 的環境（例如雲端工作區）中，hypothesis 會被視為 Any，
因此以檔案層級設定關閉 ``untyped-decorator``，並在匯入處加上可容許「未使用」的 ignore。
安裝了 hypothesis（使用者電腦與 CI）時這兩項都不會生效，型別檢查照常進行。
"""
# mypy: disable-error-code="untyped-decorator"

from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")

from hypothesis import given  # type: ignore[import-not-found,unused-ignore]
from hypothesis import strategies as st  # type: ignore[import-not-found,unused-ignore]

from trpg.shared.rng import MASK64, Rng

seeds = st.integers(min_value=0, max_value=MASK64)
bounds = st.integers(min_value=-(2**80), max_value=2**80)


@given(seed=seeds, a=bounds, b=bounds)
def test_randint_within_range(seed: int, a: int, b: int) -> None:
    lo, hi = min(a, b), max(a, b)
    rng = Rng(seed)
    for _ in range(5):
        assert lo <= rng.randint(lo, hi) <= hi


@given(seed=seeds, skip=st.integers(min_value=0, max_value=50))
def test_state_round_trip(seed: int, skip: int) -> None:
    rng = Rng(seed)
    for _ in range(skip):
        rng.next_u32()
    restored = Rng.from_state(rng.get_state())
    assert [restored.next_u32() for _ in range(10)] == [rng.next_u32() for _ in range(10)]


@given(seed=seeds, label=st.text())
def test_fork_deterministic_and_pure(seed: int, label: str) -> None:
    rng = Rng(seed)
    before = rng.get_state()
    a = rng.fork(label)
    b = rng.fork(label)
    assert rng.get_state() == before
    assert a.get_state() == b.get_state()
    assert [a.next_u32() for _ in range(5)] == [b.next_u32() for _ in range(5)]


@given(seed=seeds, items=st.lists(st.integers(), max_size=30))
def test_shuffled_is_permutation(seed: int, items: list[int]) -> None:
    snapshot = list(items)
    out = Rng(seed).shuffled(items)
    assert items == snapshot
    assert sorted(out) == sorted(items)
