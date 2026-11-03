"""地點留言板的 API 型別與組裝（Phase 5E-3；``docs/phases/Phase5計畫.md`` 31.7）。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from trpg.api.world import WorldStore
from trpg.content.world_narration import mask_text
from trpg.server.announce import location_name
from trpg.server.notes import NOTE_MAX_LEN, LocationNote, footprints
from trpg.world.narration import story_masks
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
    """是不是這個角色留的（是＝作者可以刪，5E-3b）。"""
    can_delete: bool = False
    """畫面要不要給刪除鍵：自己的留言，或管理者登入時每一則（5E-3b，#105）。"""


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
    admin: bool = False
    """目前登入的是管理者（每則留言旁都有刪除鍵，走 ``DELETE /api/world/notes/{note_id}``）。"""


def _note_view(note: LocationNote, character_id: str, *, admin: bool) -> NoteView:
    mine = note.character_id == character_id
    return NoteView(
        note_id=note.note_id,
        name=note.name,
        text=note.text,
        at=note.at,
        mine=mine,
        can_delete=mine or admin,
    )


def location_board(
    store: WorldStore, char: CharacterState, *, admin: bool = False
) -> LocationBoard:
    """角色現在所在地點的留言與足跡（呼叫者持有世界的寫入鎖）。``admin``＝登入的是管理者。

    地點名與足跡文字先套 :func:`~trpg.world.narration.story_masks`：這個角色還沒發現的隱藏地點用
    提示語（5C-3e，同 5B-5）；留言是玩家文字，照原樣顯示。"""
    region, location = char.region, char.location
    world_map = store.library.world_maps.get(region)
    places = world_map.location_by_id() if world_map is not None else {}
    masks = story_masks(store.library, char)
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
        location_name_zh=mask_text(location_name(store.library, region, location), masks),
        notes=[
            _note_view(n, char.character_id, admin=admin) for n in store.notes.at(region, location)
        ],
        footprints=[
            FootprintView(
                kind=f.kind,
                name=f.name,
                at=f.at,
                text_zh=mask_text(
                    f"{f.name} 在這裡首殺了精英「{f.target_name_zh}」"
                    if f.kind == "first_kill"
                    else f"{f.name} 來過這裡",
                    masks,
                ),
            )
            for f in steps
        ],
        admin=admin,
    )
