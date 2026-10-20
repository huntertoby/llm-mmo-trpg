"""內容端點：地圖列表、build 列表、技能卡片、名詞對照表。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from trpg.api.glossary import build_glossary
from trpg.api.schemas import BuildSummary, Glossary, MapSummary
from trpg.api.sessions import playable_maps
from trpg.api.state import runs_of, store_of
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
        BuildSummary(
            id=b.id,
            name_zh=b.name_zh,
            theme_zh=b.theme_zh,
            skills=tuple(b.hero.skills),
            max_mana=b.hero.max_mana,
            max_hp=b.hero.max_hp,
            weapon=b.hero.weapon,
            weapon_name_zh=library.weapons[b.hero.weapon].name_zh,
        )
        for b in library.builds.builds
    ]


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str, request: Request, battle_id: str | None = None) -> SkillCard:
    """技能卡片：內容庫的技能，或進行中各輪的生成技能與候選（Phase 3-5a）；帶 ``battle_id`` 時
    也查該場戰鬥規則包內的技能（工坊試玩的自訂技能、一輪生成技能，Phase 3-5c-2）。"""
    store = store_of(request)
    library = store.library
    skill = library.skills.get(skill_id)
    if skill is None and battle_id is not None:
        skill = store.get(battle_id).setup.ruleset.skills.by_id().get(skill_id)
    skill = skill or runs_of(request).find_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"找不到技能 {skill_id}")
    return skill_card(library, skill)


@router.get("/glossary")
def get_glossary(request: Request) -> Glossary:
    """地形、表面、物件、狀態、反應、元素、屬性的 ID → 中文名（由內容庫產生）。"""
    return build_glossary(store_of(request).library)
