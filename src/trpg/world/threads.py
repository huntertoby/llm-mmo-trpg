"""線頭（Phase 5B-1；``docs/phases/Phase5計畫.md`` 8.6；09 9.6.7 #6）。

事件結束時依結果留下 0～2 條線頭；每人約 5 條上限、約 3 天到期（到期也是一種結局）。本模組只有
純函式：有效／到期的判定與加入（含上限）。**線頭只能由事件結果產生**（5B-2／5B-4 呼叫
:func:`add_thread`）；5B-1 沒有任何世界動作會產生線頭。到期結局也在 5B-4 處理（用
:func:`expired_threads` 找出來）。
"""

from __future__ import annotations

from trpg.world.state import ThreadState

__all__ = ["active_threads", "add_thread", "expired_threads"]


def active_threads(threads: tuple[ThreadState, ...], now: int) -> tuple[ThreadState, ...]:
    """``now`` 時還有效（``expires_at > now``）的線頭，保持原順序。"""
    return tuple(t for t in threads if t.expires_at > now)


def expired_threads(threads: tuple[ThreadState, ...], now: int) -> tuple[ThreadState, ...]:
    """``now`` 時已到期的線頭（給 5B-4 處理到期結局），保持原順序。"""
    return tuple(t for t in threads if t.expires_at <= now)


def add_thread(
    threads: tuple[ThreadState, ...],
    thread_id: str,
    skeleton: str,
    region: str,
    now: int,
    *,
    limit: int,
    expire_seconds: int,
) -> tuple[tuple[ThreadState, ...], tuple[ThreadState, ...]]:
    """加入一條線頭，回傳 ``(新的線頭清單, 被擠掉的線頭)``。

    - 同一線頭 ID 還有效 → 不變。
    - 有效線頭已達 ``limit`` → 最舊的（建立時間、ID 排序）提前結束，放進被擠掉的清單。
    - 已到期但還沒處理的線頭留在清單裡（到期結局由 5B-4 處理），不佔上限。
    - 新線頭 ``expires_at = now + expire_seconds``；結果依 ``(created_at, thread)`` 排序。
    """
    if limit < 1:
        raise ValueError("線頭上限至少 1")
    if any(t.thread == thread_id and t.expires_at > now for t in threads):
        return threads, ()
    # 同 ID 但已到期的舊線頭被新的取代（同一線頭不重複）。
    kept = [t for t in threads if t.thread != thread_id]
    active = sorted((t for t in kept if t.expires_at > now), key=ThreadState.key)
    overflow = len(active) - limit + 1
    pushed = tuple(active[:overflow]) if overflow > 0 else ()
    pushed_ids = {t.thread for t in pushed}
    kept = [t for t in kept if t.thread not in pushed_ids]
    kept.append(
        ThreadState(
            thread=thread_id,
            skeleton=skeleton,
            region=region,
            created_at=now,
            expires_at=now + expire_seconds,
        )
    )
    kept.sort(key=ThreadState.key)
    return tuple(kept), pushed
