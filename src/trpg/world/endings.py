"""線頭到期的結局（Phase 5B-4b；``docs/phases/Phase5計畫.md`` 19.7；09 9.6.7 #6）。

事件骨架的線頭定義了 ``on_expire_flag`` 時，到期就結算：個人線頭從角色移除、給角色劇情旗標；
世界級線頭從世界移除、給世界旗標；發 ``thread_expired``。旗標的效果寫在資料（遭遇表的 ``variants``：
例「二當家坐大」「叛徒戰」），打贏變化陣容那一場就移除（:mod:`trpg.world.battle`）。

沒有 ``on_expire_flag`` 的線頭照舊（留著、無效、不佔上限）。``world_step`` 在分派動作之前呼叫，
所以到期後的第一個動作就看得到結局。純函式：不讀時間、不耗亂數。

**限時的世界旗標**（Phase 5B-4c，18.4 補充「霧魅從裂痕湧出 → 之後 2 天…」）：世界級線頭定義了
``on_expire_seconds`` 時，旗標寫進 ``timed_flags``（到 ``線頭到期時間 ＋ on_expire_seconds`` 失效，
不看哪個角色的動作觸發，全服一致），不寫進永久的 ``flags``。效果寫在資料（遭遇表的 ``surges``）。
"""

from __future__ import annotations

from trpg.content.library import ContentLibrary
from trpg.content.world_events import ThreadDef
from trpg.world.actions import ThreadExpiredEvent, WorldEvent
from trpg.world.state import CharacterState, ThreadState, TimedFlag, WorldState

__all__ = ["expire_threads"]


def _defs(library: ContentLibrary) -> dict[str, ThreadDef]:
    out: dict[str, ThreadDef] = {}
    for table in library.world_event_content.events.values():
        out.update(table.thread_by_id())
    return out


def _split(
    threads: tuple[ThreadState, ...], defs: dict[str, ThreadDef], now: int
) -> tuple[tuple[ThreadState, ...], list[tuple[ThreadState, str]]]:
    """（留下的線頭, [(到期結算的線頭, 旗標)]）。"""
    kept: list[ThreadState] = []
    ended: list[tuple[ThreadState, str]] = []
    for thread in threads:
        defn = defs.get(thread.thread)
        flag = None if defn is None else defn.on_expire_flag
        if flag is not None and thread.expires_at <= now:
            ended.append((thread, flag))
        else:
            kept.append(thread)
    return tuple(kept), ended


def expire_threads(
    library: ContentLibrary, world: WorldState, char: CharacterState, now: int
) -> tuple[WorldState, CharacterState, list[WorldEvent]]:
    """結算已到期、有結局的線頭（見模組說明）；沒有時原樣回傳、不發事件。"""
    defs = _defs(library)
    if not any(d.on_expire_flag for d in defs.values()):
        return world, char, []
    events: list[WorldEvent] = []
    kept, ended = _split(char.threads, defs, now)
    if ended:
        flags = tuple(sorted({*char.story_flags, *(f for _, f in ended)}))
        char = char.model_copy(update={"threads": kept, "story_flags": flags})
        events += [ThreadExpiredEvent(thread=t.thread, scope="personal", flag=f) for t, f in ended]
    kept, ended = _split(world.threads, defs, now)
    if ended:
        timed = {f.flag: f.until for f in world.timed_flags}
        permanent = set(world.flags)
        for thread, flag in ended:
            seconds = defs[thread.thread].on_expire_seconds
            if seconds is None:
                permanent.add(flag)
                until = None
            else:
                until = max(timed.get(flag, 0), thread.expires_at + seconds)
                timed[flag] = until
            events.append(
                ThreadExpiredEvent(thread=thread.thread, scope="world", flag=flag, until=until)
            )
        world = world.model_copy(
            update={
                "threads": kept,
                "flags": tuple(sorted(permanent)),
                "timed_flags": tuple(TimedFlag(flag=f, until=timed[f]) for f in sorted(timed)),
            }
        )
    return world, char, events
