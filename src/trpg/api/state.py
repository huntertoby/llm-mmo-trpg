"""應用層的共用狀態（戰鬥工作階段表、一輪工作階段表）存取。"""

from __future__ import annotations

from fastapi import Request

from trpg.api.runs import RunStore
from trpg.api.sessions import SessionStore

__all__ = ["runs_of", "store_of"]


def store_of(request: Request) -> SessionStore:
    store = request.app.state.store
    assert isinstance(store, SessionStore)
    return store


def runs_of(request: Request) -> RunStore:
    runs = request.app.state.runs
    assert isinstance(runs, RunStore)
    return runs
