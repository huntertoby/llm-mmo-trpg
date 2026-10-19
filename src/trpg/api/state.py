"""應用層的共用狀態（工作階段表）存取。"""

from __future__ import annotations

from fastapi import Request

from trpg.api.sessions import SessionStore

__all__ = ["store_of"]


def store_of(request: Request) -> SessionStore:
    store = request.app.state.store
    assert isinstance(store, SessionStore)
    return store
