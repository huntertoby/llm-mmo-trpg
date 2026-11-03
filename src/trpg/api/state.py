"""應用層的共用狀態（戰鬥工作階段表、一輪工作階段表、大世界）存取。"""

from __future__ import annotations

from fastapi import Request

from trpg.api.runs import RunStore
from trpg.api.sessions import SessionStore
from trpg.api.world import WorldStore
from trpg.api.world_flow import WorldLlm

__all__ = ["runs_of", "store_of", "world_llm_of", "world_of"]


def store_of(request: Request) -> SessionStore:
    store = request.app.state.store
    assert isinstance(store, SessionStore)
    return store


def runs_of(request: Request) -> RunStore:
    runs = request.app.state.runs
    assert isinstance(runs, RunStore)
    return runs


def world_of(request: Request) -> WorldStore:
    world = request.app.state.world
    assert isinstance(world, WorldStore)
    return world


def world_llm_of(request: Request) -> WorldLlm:
    llm = request.app.state.world_llm
    assert isinstance(llm, WorldLlm)
    return llm
