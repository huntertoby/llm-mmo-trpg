"""trpg.shared.rng 的單元測試。

測試向量由 scripts/rng_reference/rng_vectors.c（gcc 編譯後執行）產生，見該資料夾的 README.md。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from trpg.shared.rng import (
    MASK32,
    MASK64,
    ZERO_STATE_FALLBACK,
    Rng,
    fnv1a64,
    splitmix64,
    state_from_u64_pair,
)

# ---------------------------------------------------------------------------
# 測試向量（C 參考實作的實際輸出）
# ---------------------------------------------------------------------------

SPLITMIX64_SEED_1234567 = [
    6457827717110365317,
    3203168211198807973,
    9817491932198370423,
    4593380528125082431,
    16408922859458223821,
]

XOSHIRO128SS_STATE_1234 = [
    11520,
    0,
    5927040,
    70819200,
    2031721883,
    1637235492,
    1287239034,
    3734860849,
    3729100597,
    4258142804,
]

RNG_SEED_42 = [
    1776835114,
    4165204688,
    17111135,
    2317295270,
    2792088233,
    2554630222,
    2940343271,
    2244566231,
    3567603786,
    2928476417,
]

# 額外向量：Rng(seed=42).fork("戰鬥") 的前 5 個 next_u32()
RNG_SEED_42_FORK_BATTLE = [3671694414, 2783417885, 1903830994, 1583637568, 3087658115]


def test_reference_program_is_present() -> None:
    ref = Path(__file__).resolve().parents[2] / "scripts" / "rng_reference" / "rng_vectors.c"
    assert ref.is_file()


def test_vector_splitmix64() -> None:
    x = 1234567
    out = []
    for _ in range(5):
        x, z = splitmix64(x)
        out.append(z)
    assert out == SPLITMIX64_SEED_1234567


def test_vector_xoshiro128ss_from_state() -> None:
    rng = Rng.from_state((1, 2, 3, 4))
    assert [rng.next_u32() for _ in range(10)] == XOSHIRO128SS_STATE_1234


def test_vector_seed_42() -> None:
    rng = Rng(seed=42)
    assert [rng.next_u32() for _ in range(10)] == RNG_SEED_42


# ---------------------------------------------------------------------------
# 播種與狀態
# ---------------------------------------------------------------------------


def test_same_seed_same_sequence() -> None:
    a, b = Rng(2026), Rng(2026)
    assert [a.next_u32() for _ in range(100)] == [b.next_u32() for _ in range(100)]


def test_different_seed_different_sequence() -> None:
    a, b = Rng(1), Rng(2)
    assert [a.next_u32() for _ in range(10)] != [b.next_u32() for _ in range(10)]


def test_seed_bounds() -> None:
    Rng(0)
    Rng(MASK64)
    with pytest.raises(ValueError):
        Rng(-1)
    with pytest.raises(ValueError):
        Rng(MASK64 + 1)


def test_seed_type() -> None:
    with pytest.raises(TypeError):
        Rng(True)
    with pytest.raises(TypeError):
        Rng("42")  # type: ignore[arg-type]


def test_state_round_trip() -> None:
    rng = Rng(7)
    for _ in range(13):
        rng.next_u32()
    state = rng.get_state()
    expected = [rng.next_u32() for _ in range(50)]
    restored = Rng.from_state(state)
    assert restored.get_state() == state
    assert [restored.next_u32() for _ in range(50)] == expected


def test_state_is_plain_ints_within_32_bits() -> None:
    state = Rng(99).get_state()
    assert len(state) == 4
    assert all(type(w) is int and 0 <= w <= MASK32 for w in state)


def test_from_state_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        Rng.from_state((0, 0, 0, 0))
    with pytest.raises(ValueError):
        Rng.from_state((1, 2, 3, MASK32 + 1))
    with pytest.raises(ValueError):
        Rng.from_state((1, -2, 3, 4))
    with pytest.raises(ValueError):
        Rng.from_state((1, 2, 3))  # type: ignore[arg-type]


def test_zero_state_guard() -> None:
    assert state_from_u64_pair(0, 0) == ZERO_STATE_FALLBACK
    assert ZERO_STATE_FALLBACK != (0, 0, 0, 0)
    assert state_from_u64_pair(1, 0) == (1, 0, 0, 0)
    assert state_from_u64_pair(0x0000000200000001, 0x0000000400000003) == (1, 2, 3, 4)
    # 替代狀態可以正常運作
    rng = Rng.from_state(ZERO_STATE_FALLBACK)
    assert len({rng.next_u32() for _ in range(10)}) > 1


# ---------------------------------------------------------------------------
# randint
# ---------------------------------------------------------------------------


class ScriptedRng(Rng):
    """依指定順序吐出 u32 的 Rng，用來驗證拒絕取樣的細節。"""

    def __init__(self, values: list[int]) -> None:
        super().__init__(0)
        self._values = list(values)

    def next_u32(self) -> int:
        return self._values.pop(0)


def test_randint_lo_equals_hi_consumes_nothing() -> None:
    rng = Rng(5)
    before = rng.get_state()
    assert rng.randint(7, 7) == 7
    assert rng.get_state() == before


def test_randint_negative_range() -> None:
    rng = Rng(5)
    values = [rng.randint(-10, -5) for _ in range(500)]
    assert set(values) == set(range(-10, -4))


def test_randint_range_beyond_32_bits() -> None:
    rng = Rng(5)
    hi = 2**40
    values = [rng.randint(0, hi) for _ in range(500)]
    assert all(0 <= v <= hi for v in values)
    # 若只用一個 u32，值不會超過 2**32
    assert any(v > MASK32 for v in values)
    huge = [rng.randint(-(2**100), 2**100) for _ in range(50)]
    assert all(-(2**100) <= v <= 2**100 for v in huge)


def test_randint_full_u32_range_uses_one_word() -> None:
    rng = ScriptedRng([0xFFFFFFFF])
    assert rng.randint(0, MASK32) == MASK32


def test_randint_rejects_biased_tail() -> None:
    # n = 3：limit = (2**32 // 3) * 3 = 2**32 - 1，抽到 0xFFFFFFFF 必須重抽。
    rng = ScriptedRng([0xFFFFFFFF, 7])
    assert rng.randint(0, 2) == 7 % 3


def test_randint_multiword_composition() -> None:
    # n = 2**32 + 1 需要兩個字；先抽到的字為高位：r = (1 << 32) | 5
    rng = ScriptedRng([1, 5])
    n = 2**32 + 1
    assert rng.randint(0, 2**32) == ((1 << 32) | 5) % n


def test_randint_invalid_input() -> None:
    rng = Rng(1)
    with pytest.raises(ValueError):
        rng.randint(5, 4)
    with pytest.raises(TypeError):
        rng.randint(0, 1.5)  # type: ignore[arg-type]


def test_d20_uniformity_chi_square() -> None:
    rng = Rng(20261017)
    n = 20_000
    counts = Counter(rng.d20() for _ in range(n))
    assert set(counts) == set(range(1, 21))
    expected = n / 20
    chi2 = sum((counts[face] - expected) ** 2 / expected for face in range(1, 21))
    # 自由度 19、顯著水準 0.001 的臨界值約 43.82
    assert chi2 < 43.82, chi2


def test_roll_and_d20() -> None:
    a, b = Rng(3), Rng(3)
    assert [a.roll(20) for _ in range(20)] == [b.d20() for _ in range(20)]
    c, d = Rng(3), Rng(3)
    assert [c.roll(6) for _ in range(20)] == [d.randint(1, 6) for _ in range(20)]
    assert Rng(3).roll(1) == 1
    with pytest.raises(ValueError):
        Rng(3).roll(0)


# ---------------------------------------------------------------------------
# chance_permille
# ---------------------------------------------------------------------------


def test_chance_permille_extremes() -> None:
    rng = Rng(11)
    assert not any(rng.chance_permille(0) for _ in range(1000))
    assert all(rng.chance_permille(1000) for _ in range(1000))


def test_chance_permille_rate() -> None:
    rng = Rng(11)
    hits = sum(rng.chance_permille(250) for _ in range(20_000))
    assert 4_700 < hits < 5_300


def test_chance_permille_consumes_fixed_amount() -> None:
    a, b = Rng(12), Rng(12)
    a.chance_permille(0)
    b.chance_permille(1000)
    assert a.get_state() == b.get_state()


def test_chance_permille_invalid() -> None:
    rng = Rng(1)
    with pytest.raises(ValueError):
        rng.chance_permille(-1)
    with pytest.raises(ValueError):
        rng.chance_permille(1001)


# ---------------------------------------------------------------------------
# choice / shuffled
# ---------------------------------------------------------------------------


def test_choice() -> None:
    items = ("a", "b", "c", "d")
    rng = Rng(8)
    picks = [rng.choice(items) for _ in range(400)]
    assert set(picks) == set(items)
    assert [Rng(8).choice(items) for _ in range(3)] == [Rng(8).choice(items)] * 3
    with pytest.raises(ValueError):
        rng.choice([])


def test_shuffled_deterministic_and_pure() -> None:
    original = list(range(20))
    snapshot = list(original)
    a = Rng(9).shuffled(original)
    b = Rng(9).shuffled(original)
    assert a == b
    assert original == snapshot
    assert sorted(a) == original
    assert a != original
    assert Rng(9).shuffled([]) == []
    assert Rng(9).shuffled(("x",)) == ["x"]


# ---------------------------------------------------------------------------
# fork
# ---------------------------------------------------------------------------


def test_fork_does_not_advance_parent() -> None:
    rng = Rng(100)
    before = rng.get_state()
    rng.fork("enemy_ai")
    assert rng.get_state() == before


def test_fork_same_label_same_stream() -> None:
    rng = Rng(100)
    a = rng.fork("loot")
    b = rng.fork("loot")
    assert [a.next_u32() for _ in range(20)] == [b.next_u32() for _ in range(20)]


def test_fork_different_label_different_stream() -> None:
    rng = Rng(100)
    a = rng.fork("loot")
    b = rng.fork("map")
    assert [a.next_u32() for _ in range(10)] != [b.next_u32() for _ in range(10)]


def test_fork_depends_on_parent_state() -> None:
    rng = Rng(100)
    a = rng.fork("loot")
    rng.next_u32()
    b = rng.fork("loot")
    assert [a.next_u32() for _ in range(10)] != [b.next_u32() for _ in range(10)]


def test_fork_differs_from_parent() -> None:
    rng = Rng(100)
    child = rng.fork("")
    assert [child.next_u32() for _ in range(10)] != [rng.next_u32() for _ in range(10)]


def test_vector_fork_matches_reference() -> None:
    # 額外向量（C 參考程式第 4 組）：若 fork 的做法或雜湊被改動（例如誤用內建 hash()），這裡會失敗。
    child = Rng(42).fork("戰鬥")
    assert [child.next_u32() for _ in range(5)] == RNG_SEED_42_FORK_BATTLE


def test_fnv1a64_known_values() -> None:
    # FNV-1a 64 的公開測試值
    assert fnv1a64(b"") == 0xCBF29CE484222325
    assert fnv1a64(b"a") == 0xAF63DC4C8601EC8C
    assert fnv1a64(b"foobar") == 0x85944171F73967E8
