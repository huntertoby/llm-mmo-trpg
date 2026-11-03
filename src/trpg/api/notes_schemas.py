"""地點留言板的 API 型別與組裝（Phase 5E-3；``docs/phases/Phase5計畫.md`` 30.7）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.announce import location_name
from trpg.api.notes import NOTE_MAX_LEN, LocationNote, footprints
from trpg.api.world import WorldStore
from trpg.world.state import CharacterState

__all__ = ["FootprintView", "LocationBoard", "NoteRequest", "NoteView", "location_board"]


class _ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class NoteRequest(_ApiModel):
    """在角色現在所在的地點留言（去頭尾空白後 1～50 字、不能換行）。只當資料顯示，不送進 LLM。"""

    text: str = Field(max_length=200)


class NoteView(_ApiModel):
    note_id: str
    name: str
    """留言當下的角色名。"""
    text: str
    at: int
    """UTC 秒。"""
    mine: bool
    """是不是這個角色留的。"""


class FootprintView(_ApiModel):
    kind: str
    """``visit``（來過這裡）或 ``first_kill``（在這裡首殺了精英）。"""
    name: str
    at: int
    text_zh: str


class LocationBoard(_ApiModel):
    region: str
    location: str
    location_name_zh: str
    notes: list[NoteView]
    """最新的 20 則，新的在前。"""
    footprints: list[FootprintView]
    """其他角色的足跡，新的在前（最多 10 筆）。"""
    max_len: int = NOTE_MAX_LEN


def _note_view(note: LocationNote, character_id: str) -> NoteView:
    return NoteView(
        note_id=note.note_id,
        name=note.name,
        text=note.text,
        at=note.at,
        mine=note.character_id == character_id,
    )


def location_board(store: WorldStore, char: CharacterState) -> LocationBoard:
    """角色現在所在地點的留言與足跡（呼叫者持有世界的寫入鎖）。"""
    region, location = char.region, char.location
    world_map = store.library.world_maps.get(region)
    places = world_map.location_by_id() if world_map is not None else {}
    names = {cid: store.character(cid).hero.name_zh for cid in store.character_ids()}
    steps = footprints(
        store.entries(),
        names,
        store.first_kills.all(),
        region=region,
        location=location,
        exclude=char.character_id,
        region_of=lambda loc: region if loc in places else None,
    )
    return LocationBoard(
        region=region,
        location=location,
        location_name_zh=location_name(store.library, region, location),
        notes=[_note_view(n, char.character_id) for n in store.notes.at(region, location)],
        footprints=[
            FootprintView(
                kind=f.kind,
                name=f.name,
                at=f.at,
                text_zh=(
                    f"{f.name} 在這裡首殺了精英「{f.target_name_zh}」"
                    if f.kind == "first_kill"
                    else f"{f.name} 來過這裡"
                ),
            )
            for f in steps
        ],
    )
