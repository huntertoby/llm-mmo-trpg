"""內容端點：地圖列表、build 列表、技能卡片、名詞對照表。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from trpg.api.auth import check_owner, optional_account, settings_of
from trpg.api.glossary import build_glossary
from trpg.api.schemas import BuildSummary, Glossary, MapSummary
from trpg.api.sessions import BattleNotFoundError, playable_maps
from trpg.api.skill_cards import SkillCard, skill_card
from trpg.api.state import runs_of, store_of
from trpg.content.skills import SkillDef

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
            max_mana=library.ruleset.core.template_base_resource(
                "mana", b.hero, library.weapons[b.hero.weapon].weapon_class
            ),
            max_hp=library.ruleset.core.template_max_hp(b.hero),
            weapon=b.hero.weapon,
            weapon_name_zh=library.weapons[b.hero.weapon].name_zh,
            weapon_traits_zh=(
                *library.weapons[b.hero.weapon].trait_lines_zh(),
                *library.weapons[b.hero.weapon].rule_lines_zh(library.ruleset.core),
            ),
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
        battle = store.get(battle_id)  # 6S-1：開發模式關時只查自己的戰鬥（別人的 404）
        check_owner(request, battle.owner, BattleNotFoundError(f"找不到戰鬥 {battle_id}"))
        skill = battle.setup.ruleset.skills.by_id().get(skill_id)
    if skill is None:
        skill = _run_skill(request, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"找不到技能 {skill_id}")
    return skill_card(library, skill)


def _run_skill(request: Request, skill_id: str) -> SkillDef | None:
    """各輪的生成技能與候選；開發模式關時只查自己帳號的一輪（沒登入＝不查，6S-1）。"""
    runs = runs_of(request)
    if settings_of(request).dev_mode:
        return runs.find_skill(skill_id)
    account = optional_account(request)
    if account is None:
        return None
    return runs.find_skill(skill_id, owner=account.account_id)


@router.get("/glossary")
def get_glossary(request: Request) -> Glossary:
    """地形、表面、物件、狀態、反應、元素、屬性的 ID → 中文名（由內容庫產生）。"""
    return build_glossary(store_of(request).library)
