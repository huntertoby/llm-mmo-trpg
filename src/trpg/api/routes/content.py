"""內容端點：地圖列表、build 列表、技能卡片。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from trpg.api.schemas import BuildSummary, MapSummary
from trpg.api.sessions import playable_maps
from trpg.api.state import store_of
from trpg.narrative.skills import SkillCard, skill_card

__all__ = ["router"]

router = APIRouter(prefix="/api", tags=["content"])


@router.get("/maps")
def list_maps(request: Request) -> list[MapSummary]:
    """可以開戰的地圖（有預設遭遇的地圖，依 ID 排序）。"""
    library = store_of(request).library
    return [
        MapSummary(
            id=m.id, name_zh=m.name_zh, archetype=m.archetype, width=m.width, height=m.height
        )
        for m in (library.map(map_id) for map_id in playable_maps(library))
    ]


@router.get("/builds")
def list_builds(request: Request) -> list[BuildSummary]:
    """主角可選的 build（內容檔順序）。"""
    library = store_of(request).library
    return [
        BuildSummary(id=b.id, name_zh=b.name_zh, theme_zh=b.theme_zh, skills=tuple(b.hero.skills))
        for b in library.builds.builds
    ]


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str, request: Request) -> SkillCard:
    library = store_of(request).library
    skill = library.skills.get(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"找不到技能 {skill_id}")
    return skill_card(library, skill)
