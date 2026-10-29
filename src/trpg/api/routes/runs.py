"""roguelite 一輪的端點（Phase 3-5a；``docs/phases/Phase3計畫.md`` 7.1）。

- ``POST /api/runs``：開新一輪（起始武器 ＋ 關鍵字，或開發者起始包；種子、開局配點）。
- ``GET /api/runs/rules``：開局規則（配點數、基礎屬性）。
- ``GET /api/runs/start-options``：開局可選的武器與關鍵字（Phase 3-24b2）。
- ``POST /api/runs/start-preview``：開局預覽——每個關鍵字的池會給哪一招起始技能（Phase 3-24b2）。
- ``GET /api/runs/dev-packs``：開發者起始包（Phase 3-24b2；開發用，網頁只在 ``?dev=1`` 顯示）。
- ``GET /api/runs/saves``：存檔列表。
- ``POST /api/runs/load``：讀檔（``run_id``）；戰鬥中的存檔重播到存檔當下。
- ``GET /api/runs/{run_id}``：一輪的狀態（戰鬥已結束時先結算）。
- ``POST /api/runs/{run_id}/battle``：開始或接續本場戰鬥（回傳一輪與戰鬥；之後用
  ``/api/battles/{battle_id}/…`` 操作）。
- ``POST /api/runs/{run_id}/choice``：升級選擇、營火重骰／選擇／離開。
- ``POST /api/runs/{run_id}/save``：存檔（戰鬥中也可以）。

Phase 3-6：節點改變（戰後結算、升級、營火、結束）與每個戰鬥動作之後自動存檔（同一個檔案覆寫）。

錯誤：不存在 404、節點不符 409、內容不合法或存檔壞掉 422。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from trpg.api.attribute_text import attribute_affects, attribute_suggestion
from trpg.api.presenter import battle_response
from trpg.api.run_presenter import allocation_preview, keyword_refs, run_response, save_summary
from trpg.api.run_schemas import (
    AllocationPreviewOut,
    AllocationPreviewRequest,
    CreateRunRequest,
    DevPackOut,
    LoadRunRequest,
    OriginOption,
    RaceOption,
    RunBattleResponse,
    RunResponse,
    RunRules,
    SaveOut,
    SaveSummary,
    StartKeywordOption,
    StartOptions,
    StartPreview,
    StartPreviewRequest,
    StartResourcesOut,
    StartResourcesRequest,
    StartWeaponOption,
)
from trpg.api.runs import RunSession, RunStore
from trpg.api.state import runs_of
from trpg.content.library import ContentLibrary
from trpg.content.skills import SkillDef
from trpg.narrative.skills import skill_card
from trpg.roguelite.start import (
    start_resources,
    start_weapons,
    starter_pools,
    starting_skill,
)
from trpg.roguelite.state import Choice

__all__ = ["router"]

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _respond(store: RunStore, session: RunSession) -> RunResponse:
    store.sync(session)
    return run_response(session)


@router.post("", status_code=201)
def create_run(body: CreateRunRequest, request: Request) -> RunResponse:
    store = runs_of(request)
    session = store.create(
        body.seed,
        body.attributes,
        weapon=body.weapon,
        keywords=body.keywords,
        dev_pack=body.dev_pack,
        build=body.build,
        test_mode=body.test_mode,
        test_equipment=body.test_equipment,
        race=body.race,
        origin=body.origin,
    )
    with session.lock:
        return _respond(store, session)


@router.get("/start-options")
def get_start_options(request: Request) -> StartOptions:
    """開局可選的武器（``weapons.yaml`` 全部）與關鍵字（推導表順序）。"""
    library = runs_of(request).library
    rules = library.roguelite
    core = library.ruleset.core
    weapons = []
    for weapon_id in start_weapons(library):
        weapon = library.weapons[weapon_id]
        hero = rules.start.heroes[weapon.weapon_class]
        hp = core.run_max_hp(hero.max_hp, rules.base_attribute, 1)
        weapons.append(
            StartWeaponOption(
                id=weapon.id,
                name_zh=weapon.name_zh,
                weapon_class=weapon.weapon_class,
                traits_zh=(*weapon.trait_lines_zh(), *weapon.rule_lines_zh(core)),
                hp=hp,
                mana=hero.max_mana,
            )
        )
    return StartOptions(
        weapons=tuple(weapons),
        keywords=keyword_refs(library, library.keywords.start_ids()),
        keyword_count=rules.start.keywords,
        races=_race_options(library),
        origins=_origin_options(library),
    )


def _realm_names(library: ContentLibrary) -> dict[str, str]:
    regions = library.regions
    return {r.id: r.name_zh for r in regions.regions} if regions is not None else {}


def _race_options(library: ContentLibrary) -> tuple[RaceOption, ...]:
    table = library.ruleset.races
    if table is None:
        return ()
    realms = _realm_names(library)
    return tuple(
        RaceOption(
            id=r.id,
            name_zh=r.name_zh,
            home_realm=r.home_realm,
            home_realm_name_zh=realms.get(r.home_realm, r.home_realm),
            skill_name_zh=r.skill.name_zh,
            skill_description_zh=r.skill.description_zh,
            skill_ap=1,
            skill_uses=r.skill.uses_per_battle,
            passive_name_zh=r.passive.name_zh,
            passive_description_zh=r.passive.description_zh,
        )
        for r in table.races
    )


def _origin_options(library: ContentLibrary) -> tuple[OriginOption, ...]:
    table = library.origins
    if table is None:
        return ()
    realms = _realm_names(library)
    return tuple(
        OriginOption(
            id=o.id,
            name_zh=o.name_zh,
            realm=o.realm,
            realm_name_zh=realms.get(o.realm, o.realm),
            description_zh=o.description_zh,
        )
        for o in table.origins
    )


@router.post("/start-preview")
def post_start_preview(body: StartPreviewRequest, request: Request) -> StartPreview:
    """每個關鍵字的池會給哪一招（同種子確定）：已選的依選擇順序是實際會拿到的；沒選的是「下一個
    選它」時會拿到的。湊不到時 ``skill`` 為 ``None``（不可選）。"""
    library = runs_of(request).library
    pools = starter_pools(library)
    chosen: dict[str, SkillDef | None] = {}
    taken: list[str] = []
    for keyword in body.keywords:
        found = starting_skill(library, body.weapon, keyword, body.seed, taken=taken, pools=pools)
        chosen[keyword] = found
        if found is not None:
            taken.append(found.id)
    options = []
    for ref in keyword_refs(library, library.keywords.start_ids()):
        selected = ref.id in chosen
        skill = (
            chosen[ref.id]
            if selected
            else starting_skill(library, body.weapon, ref.id, body.seed, taken=taken, pools=pools)
        )
        options.append(
            StartKeywordOption(
                keyword=ref,
                selected=selected,
                skill=None if skill is None else skill_card(library, skill),
            )
        )
    picked = [c for c in chosen.values() if c is not None]
    weapon = library.weapons.get(body.weapon)
    return StartPreview(
        weapon=body.weapon,
        seed=body.seed,
        options=tuple(options),
        suggestion=attribute_suggestion(picked, weapon),
        attribute_affects=attribute_affects(picked, weapon),
    )


@router.post("/start-resources")
def post_start_resources(body: StartResourcesRequest, request: Request) -> StartResourcesOut:
    """開局畫面的資源預覽（3-41c）：選了武器、配了點之後主角的最大 HP、法力、耐力。和開新一輪建立
    出的主角用同一個函式（:func:`trpg.roguelite.start.hero_resources`），不寫死在前端。"""
    library = runs_of(request).library
    out = start_resources(library, body.weapon, body.attributes)
    return StartResourcesOut(hp=out.hp, mana=out.mana, stamina=out.stamina)


@router.get("/dev-packs")
def list_dev_packs(request: Request) -> list[DevPackOut]:
    """開發者起始包（``dev_starters.yaml``；開發用，玩家介面不顯示）。"""
    library = runs_of(request).library
    return [
        DevPackOut(
            id=p.id,
            label_zh=p.label_zh,
            weapon=p.weapon,
            weapon_name_zh=library.weapons[p.weapon].name_zh,
            keywords=keyword_refs(library, p.keywords),
        )
        for p in library.dev_starters.packs
    ]


@router.get("/rules")
def get_rules(request: Request) -> RunRules:
    """開局規則（來自 ``content/roguelite.yaml``）：前端不寫死配點數。"""
    library = runs_of(request).library
    rules = library.roguelite
    return RunRules(
        start_points=rules.start_free_points,
        base_attribute=rules.base_attribute,
        hp_per_con_point=library.ruleset.core.hp_per_con_point,
    )


@router.get("/saves")
def list_saves(request: Request) -> list[SaveSummary]:
    store = runs_of(request)
    return [save_summary(store.library, s) for s in store.saves()]


@router.post("/load")
def load_run(body: LoadRunRequest, request: Request) -> RunResponse:
    store = runs_of(request)
    session = store.load(body.run_id)
    with session.lock:
        return _respond(store, session)


@router.post("/{run_id}/allocation-preview")
def post_allocation_preview(
    run_id: str, body: AllocationPreviewRequest, request: Request
) -> AllocationPreviewOut:
    """升級配點與營火重配的資源預覽（3H-5）：把配點加到主角目前的屬性上，回傳新的最大 HP、法力、
    耐力與變化文字；算式與一輪面板、開新一輪相同（後端算，前端不寫公式）。"""
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        return allocation_preview(session.library, session.run, body.attributes)


@router.get("/{run_id}")
def get_run(run_id: str, request: Request) -> RunResponse:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        return _respond(store, session)


@router.post("/{run_id}/battle")
def run_battle(run_id: str, request: Request) -> RunBattleResponse:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        battle, records = store.battle(session)
        with battle.lock:
            battle_out = battle_response(battle, records)
        return RunBattleResponse(run=run_response(session), battle=battle_out)


@router.post("/{run_id}/choice")
def post_choice(run_id: str, choice: Choice, request: Request) -> RunResponse:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        store.choose(session, choice)
        return _respond(store, session)


@router.post("/{run_id}/save")
def save_run(run_id: str, request: Request) -> SaveOut:
    store = runs_of(request)
    session = store.get(run_id)
    with session.lock:
        path, save = store.save(session)
        return SaveOut(
            run_id=save.run_id,
            file=path.name,
            format=save.format,
            in_battle=save.battle is not None,
        )
