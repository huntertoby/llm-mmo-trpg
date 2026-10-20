"""技能工坊端點（Phase 3F-1，開發工具）。

全部是 :mod:`trpg.skillgen` 的包裝：選項（:func:`~trpg.skillgen.options.draft_options`）、檢查
（:func:`~trpg.skillgen.draft_check.check_draft`）、隨機組合器
（:func:`~trpg.skillgen.random_composer.compose_random_skill`）、YAML（:func:`~trpg.skillgen.skill_yaml.
skill_to_yaml`）；技能卡片用 :func:`trpg.narrative.skills.skill_card`。「裝上試玩」是
``POST /api/battles`` 的 ``custom_skills``、``replace_skills``、``opponents``。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from trpg.api.player_text import player_options
from trpg.api.schemas import MapSummary
from trpg.api.sessions import playable_maps
from trpg.api.state import store_of
from trpg.api.workshop_schemas import (
    ArenaOpponents,
    WorkshopArena,
    WorkshopCheck,
    WorkshopExport,
    WorkshopRandom,
    WorkshopRandomRequest,
    WorkshopSkillRequest,
)
from trpg.content.library import ContentLibrary
from trpg.narrative.skills import skill_card
from trpg.skillgen.draft import build_skill
from trpg.skillgen.draft_check import check_draft
from trpg.skillgen.option_models import DraftOptions
from trpg.skillgen.options import draft_options
from trpg.skillgen.random_composer import compose_random_skill
from trpg.skillgen.skill_yaml import skill_to_yaml

__all__ = ["router"]

router = APIRouter(prefix="/api/workshop", tags=["workshop"])


def _check(library: ContentLibrary, skill: dict[str, Any]) -> WorkshopCheck:
    result = check_draft(skill, library)
    card = None
    if result.skill is not None:
        card = skill_card(library, build_skill(result.skill))
    return WorkshopCheck(**result.model_dump(), card=card)


@router.get("/arena")
def get_arena(request: Request) -> WorkshopArena:
    """裝上試玩的選單：靶場（預設）、其他地圖、靶場的對手。"""
    library = store_of(request).library
    rules = library.workshop
    boss = playable_maps(library, include_boss=True)  # Boss 地圖排在一般地圖之後（3-5c-2）
    general = playable_maps(library)
    ids = [rules.map, *general, *(m for m in boss if m not in general and m != rules.map)]
    maps = tuple(
        MapSummary(
            id=m.id, name_zh=m.name_zh, archetype=m.archetype, width=m.width, height=m.height
        )
        for m in (library.map(i) for i in ids)
    )
    opponents = tuple(
        ArenaOpponents(
            id=o.id,
            name_zh=o.name_zh,
            description_zh=o.description_zh,
            enemies=tuple(library.unit(e).name_zh for e in o.enemies),
        )
        for o in rules.opponents
    )
    return WorkshopArena(
        default_map=rules.map, max_rounds=rules.max_rounds, maps=maps, opponents=opponents
    )


@router.post("/options")
def post_options(body: WorkshopSkillRequest, request: Request) -> DraftOptions:
    """下一步的合法選項：前置步驟都完成的每一步的欄位與選項，以及第一個未完成的步驟。"""
    library = store_of(request).library
    return player_options(draft_options(body.skill, library), library)


@router.post("/check")
def post_check(body: WorkshopSkillRequest, request: Request) -> WorkshopCheck:
    """是否合法、違反的規則、預算明細、最低稀有度與技能卡片。"""
    return _check(store_of(request).library, body.skill)


@router.post("/random")
def post_random(body: WorkshopRandomRequest, request: Request) -> WorkshopRandom:
    """以隨機組合器產生一個技能（同種子同參數結果一致）；組不出來時 422。"""
    library = store_of(request).library
    skill = compose_random_skill(
        body.seed, tier=body.tier, rarity=body.rarity, skeleton=body.skeleton, library=library
    )
    data = skill.model_dump(mode="json", exclude_none=True)
    return WorkshopRandom(skill=data, check=_check(library, data))


@router.post("/export")
def post_export(body: WorkshopSkillRequest, request: Request) -> WorkshopExport:
    """匯出 YAML（``provenance.origin: workshop``）。技能必須能通過 schema（否則 422）；規則上不合法
    的技能也可以匯出，``legal`` 與 ``problems`` 標示問題。"""
    library = store_of(request).library
    skill = build_skill(body.skill)
    provenance = skill.provenance.model_copy(update={"origin": "workshop"})
    skill = skill.model_copy(update={"provenance": provenance})
    result = check_draft(skill.model_dump(mode="json", exclude_none=True), library)
    return WorkshopExport(
        yaml=skill_to_yaml(skill),
        filename=f"{skill.id}.yaml",
        legal=result.legal,
        problems=tuple(p.message_zh for p in result.problems),
    )
