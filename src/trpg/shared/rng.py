"""可種子化、可序列化、跨平台結果一致的亂數產生器。

演算法
------
- 核心：**xoshiro128\\*\\***（David Blackman 與 Sebastiano Vigna），32 位元輸出，
  狀態為 4 個 32 位元整數。
- 播種：**splitmix64**。輸入 ``0 <= seed < 2**64``，以 splitmix64 產生兩個 64 位元數
  ``a``、``b``；``a`` 的低／高 32 位元為 ``s0``／``s1``，``b`` 的低／高 32 位元為 ``s2``／``s3``。
  若結果全為 0（xoshiro 的唯一非法狀態，理論上幾乎不可能），改用固定的非零常數
  :data:`ZERO_STATE_FALLBACK`。
- 所有運算皆以 Python 整數搭配 32／64 位元遮罩實作，不依賴平台的整數寬度或浮點數，
  因此在任何平台、任何 Python 版本上結果都一致。測試向量由
  ``scripts/rng_reference/rng_vectors.c`` 的 C 參考實作產生。

使用原則
--------
- 引擎內所有亂數一律來自傳入的 :class:`Rng`；禁止使用 ``random`` 模組。
- 不提供浮點數 API。機率以整數千分比（‰）表示，見 :meth:`Rng.chance_permille`。
- :meth:`Rng.get_state` 與 :meth:`Rng.from_state` 用於事件日誌、存檔與重播。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

__all__ = [
    "MASK32",
    "MASK64",
    "PERMILLE",
    "ZERO_STATE_FALLBACK",
    "Rng",
    "RngState",
    "fnv1a64",
    "splitmix64",
    "state_from_u64_pair",
]

MASK32: Final = 0xFFFFFFFF
MASK64: Final = 0xFFFFFFFFFFFFFFFF

type RngState = tuple[int, int, int, int]

# 全零狀態的替代值（取自黃金比例、π、e、√2 小數部分的前 32 位元，常見的「無特殊意義」常數）。
ZERO_STATE_FALLBACK: Final[RngState] = (0x9E3779B9, 0x243F6A88, 0xB7E15162, 0x6A09E667)

PERMILLE: Final = 1000
"""千分比的分母。"""

_STATE_WORDS: Final = 4

_FNV64_OFFSET: Final = 0xCBF29CE484222325
_FNV64_PRIME: Final = 0x00000100000001B3


def splitmix64(x: int) -> tuple[int, int]:
    """splitmix64 的一步：輸入目前狀態 ``x``，回傳 ``(新狀態, 輸出)``，皆為 64 位元無號整數。"""
    x = (x + 0x9E3779B97F4A7C15) & MASK64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return x, z ^ (z >> 31)


def fnv1a64(data: bytes) -> int:
    """FNV-1a 64 位元雜湊（穩定，不受 ``PYTHONHASHSEED`` 影響）。"""
    h = _FNV64_OFFSET
    for byte in data:
        h ^= byte
        h = (h * _FNV64_PRIME) & MASK64
    return h


def state_from_u64_pair(a: int, b: int) -> RngState:
    """把兩個 64 位元數拆成 xoshiro128** 狀態；全零時改用 :data:`ZERO_STATE_FALLBACK`。"""
    state = (a & MASK32, (a >> 32) & MASK32, b & MASK32, (b >> 32) & MASK32)
    if state == (0, 0, 0, 0):
        return ZERO_STATE_FALLBACK
    return state


def _rotl32(x: int, k: int) -> int:
    return ((x << k) | (x >> (32 - k))) & MASK32


def _check_int(name: str, value: object) -> int:
    # bool 是 int 的子類別；明確拒絕，避免 Rng(True) 這種意外用法。
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} 必須是 int，收到 {type(value).__name__}")
    return value


class Rng:
    """xoshiro128** 亂數產生器（可變物件）。

    相同種子必得相同序列；``get_state()``／``from_state()`` 往返後序列一致。
    """

    __slots__ = ("_s0", "_s1", "_s2", "_s3")

    def __init__(self, seed: int) -> None:
        seed = _check_int("seed", seed)
        if not 0 <= seed <= MASK64:
            raise ValueError(f"seed 必須滿足 0 <= seed < 2**64，收到 {seed}")
        x, a = splitmix64(seed)
        _, b = splitmix64(x)
        self._s0, self._s1, self._s2, self._s3 = state_from_u64_pair(a, b)

    # ------------------------------------------------------------------
    # 狀態
    # ------------------------------------------------------------------

    @classmethod
    def from_state(cls, state: tuple[int, int, int, int]) -> Rng:
        """由 :meth:`get_state` 的結果還原。

        每個字必須是 32 位元無號整數；全零狀態是 xoshiro 的非法狀態（不會由正常流程產生），
        拋出 ``ValueError``。
        """
        if len(state) != _STATE_WORDS:
            raise ValueError(f"state 必須是 {_STATE_WORDS} 個整數，收到 {len(state)} 個")
        words = tuple(_check_int("state 的元素", w) for w in state)
        for w in words:
            if not 0 <= w <= MASK32:
                raise ValueError(f"state 的每個元素必須在 [0, 2**32) 內，收到 {w}")
        if words == (0, 0, 0, 0):
            raise ValueError("state 不可全為 0（xoshiro128** 的非法狀態）")
        rng = cls.__new__(cls)
        rng._s0, rng._s1, rng._s2, rng._s3 = words
        return rng

    def get_state(self) -> RngState:
        """取得目前狀態（供事件日誌、存檔與重播使用）。"""
        return (self._s0, self._s1, self._s2, self._s3)

    def __repr__(self) -> str:
        return f"Rng.from_state({self.get_state()!r})"

    # ------------------------------------------------------------------
    # 核心
    # ------------------------------------------------------------------

    def next_u32(self) -> int:
        """下一個 32 位元無號整數（xoshiro128**）。"""
        s0, s1, s2, s3 = self._s0, self._s1, self._s2, self._s3
        result = (_rotl32((s1 * 5) & MASK32, 7) * 9) & MASK32
        t = (s1 << 9) & MASK32

        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = _rotl32(s3, 11)

        self._s0, self._s1, self._s2, self._s3 = s0, s1, s2, s3
        return result

    # ------------------------------------------------------------------
    # 整數
    # ------------------------------------------------------------------

    def randint(self, lo: int, hi: int) -> int:
        """閉區間 ``[lo, hi]`` 的均勻整數（無偏差）。

        以拒絕取樣避免取餘數造成的偏差：區間大小 ``n``，用 ``k`` 個 u32 組成
        ``32k`` 位元的整數 ``r``（``k`` 為能涵蓋 ``n - 1`` 的最少字數，先抽到的字放在高位），
        ``limit = (2**(32k) // n) * n``，``r >= limit`` 時重抽，否則回傳 ``lo + r % n``。
        ``lo == hi`` 時不消耗亂數。
        """
        lo = _check_int("lo", lo)
        hi = _check_int("hi", hi)
        if lo > hi:
            raise ValueError(f"randint 需要 lo <= hi，收到 lo={lo}, hi={hi}")
        n = hi - lo + 1
        if n == 1:
            return lo
        words = max(1, ((n - 1).bit_length() + 31) // 32)
        total = 1 << (32 * words)
        limit = (total // n) * n
        while True:
            r = 0
            for _ in range(words):
                r = (r << 32) | self.next_u32()
            if r < limit:
                return lo + r % n

    def roll(self, sides: int) -> int:
        """擲一顆 ``sides`` 面骰（``sides >= 1``），等同 ``randint(1, sides)``。"""
        sides = _check_int("sides", sides)
        if sides < 1:
            raise ValueError(f"骰子面數必須 >= 1，收到 {sides}")
        return self.randint(1, sides)

    def d20(self) -> int:
        """擲一顆 d20。"""
        return self.roll(20)

    def chance_permille(self, p: int) -> bool:
        """以千分比判定成功：成功機率 ``p / 1000``（``0 <= p <= 1000``），不使用浮點數。

        為了讓亂數消耗量與 ``p`` 無關（重播與預覽較單純），即使 ``p`` 為 0 或 1000
        也固定消耗一次 ``randint(0, 999)``。
        """
        p = _check_int("p", p)
        if not 0 <= p <= PERMILLE:
            raise ValueError(f"千分比必須在 [0, {PERMILLE}] 內，收到 {p}")
        return self.randint(0, PERMILLE - 1) < p

    # ------------------------------------------------------------------
    # 序列
    # ------------------------------------------------------------------

    def choice[T](self, seq: Sequence[T]) -> T:
        """從序列中均勻選一個；空序列拋出 ``ValueError``。"""
        if len(seq) == 0:
            raise ValueError("無法從空序列中選擇")
        return seq[self.randint(0, len(seq) - 1)]

    def shuffled[T](self, seq: Sequence[T]) -> list[T]:
        """回傳洗牌後的新串列（Fisher–Yates，從尾端往前），不修改輸入。"""
        items = list(seq)
        for i in range(len(items) - 1, 0, -1):
            j = self.randint(0, i)
            items[i], items[j] = items[j], items[i]
        return items

    # ------------------------------------------------------------------
    # 子串流
    # ------------------------------------------------------------------

    def fork(self, label: str) -> Rng:
        """依目前狀態與 ``label`` 衍生一個獨立的子串流，**不推進** 父串流。

        做法（確定且穩定，不使用內建 ``hash()``）：

        1. ``x = fnv1a64(label.encode("utf-8"))``
        2. 依序對父狀態的 4 個字 ``w``：``x = splitmix64(x ^ w)[1]``（取該步的輸出）。
        3. 以 ``x`` 作為種子建立新的 :class:`Rng`（再經一次 splitmix64 播種）。

        同一父狀態與同一 ``label`` 必得相同子串流；不同 ``label`` 得到不同子串流。
        """
        if not isinstance(label, str):
            raise TypeError(f"label 必須是 str，收到 {type(label).__name__}")
        x = fnv1a64(label.encode("utf-8"))
        for w in self.get_state():
            _, x = splitmix64(x ^ w)
        return Rng(x)
