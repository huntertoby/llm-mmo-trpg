"""#150 開局先玩再定的第 1 段（Phase OB-1；21 21.5、:mod:`trpg.world.opening`）。

表格測試，一律跑真的世界動作：選大類（``pick_class`` → ``starter``）、三種大類的入門配備、``/12``
舊存檔遷移、``starter`` 階段每個被擋與不被擋的動作、升級自動配點、入門武器不能賣寄分解、世界日誌
重播。
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from tests.world.test_crafting import ENCHANTER, SMITHY, _rich
from tests.world.test_gear import SHOP, _item
from tests.world.test_situations import at_event, peddler, sure
from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathProposal
from trpg.roguelite.start import recommended_allocation, recommended_level_up
from trpg.shared.types import Attribute
from trpg.world.actions import (
    AttributesAllocatedEvent,
    ChangeLookAction,
    ChangeRaceAction,
    DissolveAction,
    FlashAction,
    FlashPickAction,
    HintSeenAction,
    HireAction,
    InheritAction,
    LeveledUpEvent,
    LoadoutAction,
    NewsSeenAction,
    OpeningClassAction,
    OpeningClassChosenEvent,
    OpeningConfirmAction,
    ReleaseOathAction,
    RestAction,
    ShadowAiAction,
    SwearOathAction,
    TeleportAction,
    WorldAction,
)
from trpg.world.common import max_hp, max_mana
from trpg.world.crafting_actions import (
    CraftAction,
    EnhanceAction,
    ImbueAction,
    RerollAction,
    SalvageAction,
)
from trpg.world.economy_actions import EquipAction, SellAction
from trpg.world.errors import WorldActionError
from trpg.world.growth import gain_xp
from trpg.world.league_actions import LeagueEnterAction, LeagueWithdrawAction
from trpg.world.opening import new_opening, pending_hero, range_content
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import WORLD_RULES_VERSION, dumps_char, dumps_log, loads_char, loads_log
from trpg.world.season_events import SeasonBossAction
from trpg.world.state import CHAR_FORMAT, CharacterState, DeferredOffer, OpeningState
from trpg.world.step import world_step
from trpg.world.trade_actions import MailSendAction

type MakeChar = Callable[..., CharacterState]

CLASSES = {"melee": "one_handed_sword", "ranged": "bow", "focus": "fire_staff"}


def _pending(library: ContentLibrary, make_char: MakeChar, **updates: object) -> CharacterState:
    char = make_char(**updates)
    hero = pending_hero(library, char.hero.model_copy(update={"name_zh": "小靶", "race": "human"}))
    return char.model_copy(update={"hero": hero, "generated_skills": (), "opening": new_opening(7)})


def _starter(
    library: ContentLibrary, make_char: MakeChar, cls: str = "melee", **updates: object
) -> CharacterState:
    action = OpeningClassAction(weapon_class=cls)  # type: ignore[arg-type]
    return world_step(
        library, make_world(), _pending(library, make_char, **updates), action, NOON
    ).char


# ---------------------------------------------------------------------------
# 選大類
# ---------------------------------------------------------------------------


def test_versions() -> None:
    assert CHAR_FORMAT == "trpg-char/15"
    assert WORLD_RULES_VERSION == 32  # RG-4（31＝RG-2，30＝RR-2c，29＝RR-1，28＝WP-1，27＝OB-7）


@pytest.mark.parametrize(("cls", "weapon"), sorted(CLASSES.items()))
def test_pick_class_gives_starter_kit(
    library: ContentLibrary, make_char: MakeChar, cls: str, weapon: str
) -> None:
    pending = _pending(library, make_char)
    action = OpeningClassAction(weapon_class=cls)  # type: ignore[arg-type]
    result = world_step(library, make_world(), pending, action, NOON)
    char = result.char
    demos = range_content(library).demos[cls]  # type: ignore[index]
    assert char.opening is not None
    assert char.opening.stage == "starter" and char.opening.weapon_class == cls
    assert char.hero.weapon == weapon
    assert char.hero.skills == demos
    assert char.hero.name_zh == "小靶" and char.hero.race == "human"
    # 開局 4 點照推薦配法（同 ``recommended_allocation``，全部讀資料，不寫死招）
    points = library.roguelite.start_free_points
    assert points == 4
    skills = [library.skills[s] for s in demos]
    expected = recommended_allocation(skills, library.weapons[weapon], points)
    base = pending.hero.attributes
    spent = {
        a: char.hero.attributes[a] - base[a]
        for a in Attribute
        if char.hero.attributes[a] != base[a]
    }
    assert sum(spent.values()) == points
    assert spent == expected
    assert char.hp == max_hp(library, char) and char.mana == max_mana(library, char)
    event = next(e for e in result.events if isinstance(e, OpeningClassChosenEvent))
    assert (event.weapon_class, event.weapon, event.skills) == (cls, weapon, demos)
    assert len(event.skill_names) == 2
    # 只記大類；正式選定的欄位還沒有
    assert char.opening.weapon is None and char.opening.keywords == ()
    assert char.opening.deferred_offers == () and char.opening.granted_skills == ()


def test_pick_class_is_deterministic(library: ContentLibrary, make_char: MakeChar) -> None:
    assert dumps_char(_starter(library, make_char)) == dumps_char(_starter(library, make_char))


def test_starter_kit_reads_demos_from_data(library: ContentLibrary, make_char: MakeChar) -> None:
    """入門招未定案（#148）：換 ``range.demos`` 就換招，不動程式。"""
    arena = range_content(library)
    other = ("skill_spark_chain", "skill_fire_bolt")
    assert arena.demos["focus"] != other
    demos = {**arena.demos, "focus": other}
    newcomer = library.world_newcomer
    assert newcomer is not None
    changed = newcomer.model_copy(update={"range": arena.model_copy(update={"demos": demos})})
    lib = dataclasses.replace(library, world_newcomer=changed)
    assert _starter(lib, make_char, "focus").hero.skills == other


def test_class_cannot_be_rechosen(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _starter(library, make_char)
    with pytest.raises(WorldActionError, match="大類已經選好"):
        world_step(library, make_world(), char, OpeningClassAction(weapon_class="focus"), NOON)


def test_done_character_cannot_use_opening_actions(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    done = make_char()
    for action in (
        OpeningClassAction(weapon_class="melee"),
        OpeningConfirmAction(weapon="dagger", keywords=("frozen", "concealed")),
    ):
        with pytest.raises(WorldActionError, match="不能重選"):
            world_step(library, make_world(), done, action, NOON)


def test_pick_class_whitelist(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _pending(library, make_char)
    blocked: list[WorldAction] = [
        RestAction(),
        TeleportAction(region="cloud_ridge"),
        LoadoutAction(skills=()),
    ]
    for action in blocked:
        with pytest.raises(WorldActionError, match="確定出發"):
            world_step(library, make_world(), char, action, NOON)
    allowed: list[WorldAction] = [
        NewsSeenAction(until=NOON),
        HintSeenAction(ids=("x",)),
    ]
    for action in allowed:
        world_step(library, make_world(), char, action, NOON)
    # 改外觀過得了閘門（主城限定是它自己的規則，這裡角色在霧渡鎮）
    with pytest.raises(WorldActionError) as excinfo:
        world_step(library, make_world(), char, ChangeLookAction(), NOON)
    assert "確定出發" not in str(excinfo.value)


# ---------------------------------------------------------------------------
# 舊存檔
# ---------------------------------------------------------------------------


def _as_old(char: CharacterState, *, opening: object) -> str:
    data = json.loads(dumps_char(char))
    data["format"] = "trpg-char/12"
    if opening == "missing":
        data.pop("opening", None)
    else:
        data["opening"] = opening
    return json.dumps(data)


@pytest.mark.parametrize(
    ("label", "opening", "expected"),
    [
        ("done", None, None),
        ("missing", "missing", None),
        ("in_range", {"seed": 42}, OpeningState(seed=42)),
    ],
)
def test_format_12_upgrades(
    make_char: MakeChar, label: str, opening: object, expected: OpeningState | None
) -> None:
    del label
    loaded = loads_char(_as_old(make_char(), opening=opening))
    assert loaded.format == "trpg-char/15"
    assert loaded.opening == expected
    if expected is not None:
        assert loaded.opening is not None and loaded.opening.stage == "pick_class"


def test_old_in_range_character_uses_new_flow(library: ContentLibrary, make_char: MakeChar) -> None:
    char = loads_char(_as_old(_pending(library, make_char), opening={"seed": 7}))
    after = world_step(library, make_world(), char, OpeningClassAction(weapon_class="ranged"), NOON)
    assert after.char.opening is not None and after.char.opening.stage == "starter"
    assert after.char.hero.weapon == "bow"


def test_opening_state_round_trip(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _starter(library, make_char)
    assert char.opening is not None
    opening = char.opening.model_copy(
        update={"deferred_offers": (DeferredOffer(quest="starter_ferry", step=0),)}
    )
    full = char.model_copy(update={"opening": opening})
    assert loads_char(dumps_char(full)) == full


def test_stage_needs_class() -> None:
    with pytest.raises(ValueError, match="大類"):
        OpeningState(seed=1, stage="starter")
    with pytest.raises(ValueError, match="大類"):
        OpeningState(seed=1, weapon_class="melee")


def test_done_character_is_untouched_by_gate(library: ContentLibrary, make_char: MakeChar) -> None:
    """舊角色（``opening=None``）閃現、換技能、換種族都不經過入門期閘門。"""
    char = make_char()
    loadout = LoadoutAction(skills=tuple(char.hero.skills))
    assert world_step(library, make_world(), char, loadout, NOON).char.hero.skills


# ---------------------------------------------------------------------------
# 入門期閘門（21.5 第 7、9 點）
# ---------------------------------------------------------------------------

GATE_REASONS = (
    "入門期",
    "還不能正式選定",
    "大類已經選好",
    "4 級前不能",
    # OB-5：玩法 PM 定稿的字（台詞-150與147「限制：閃現」「限制：換種族」）
    "到 4 級才能閃現",
    "正式選定武器與關鍵字之前不能換種族",
)


BLOCKED: dict[str, WorldAction] = dict(
    [
        ("change_race", ChangeRaceAction(race="elf")),
        ("flash", FlashAction(skill="skill_fire_bolt")),
        ("flash_pick", FlashPickAction(pick=0)),
        ("loadout", LoadoutAction(skills=())),
        ("hire", HireAction(mercenaries=())),
        ("shadow_ai", ShadowAiAction(profile=None)),
        ("league_enter", LeagueEnterAction()),
        ("league_withdraw", LeagueWithdrawAction()),
        ("season_boss", SeasonBossAction()),
        ("swear", SwearOathAction(proposal=OathProposal(template="no_items"))),
        ("release", ReleaseOathAction()),
        ("dissolve", DissolveAction(skill="skill_fire_bolt")),
        ("inherit", InheritAction(skill="a", source="b", records=(0,))),
        ("confirm", OpeningConfirmAction(weapon="dagger", keywords=("frozen", "concealed"))),
    ]
)


@pytest.mark.parametrize("name", sorted(BLOCKED))
def test_starter_blocks(library: ContentLibrary, make_char: MakeChar, name: str) -> None:
    action = BLOCKED[name]
    char = _starter(library, make_char)
    with pytest.raises(WorldActionError) as excinfo:
        world_step(library, make_world(), char, action, NOON)
    assert any(r in str(excinfo.value) for r in GATE_REASONS), str(excinfo.value)


def test_starter_blocks_main_hand_with_or_without_slot(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    sword = _item(library, "weapon")
    char = _starter(library, make_char, gear=(sword,))
    for slot in (None, "main_hand"):
        with pytest.raises(WorldActionError, match="不能換主手"):
            world_step(library, make_world(), char, EquipAction(item=sword.id, slot=slot), NOON)


@pytest.mark.parametrize("slot", ["head", "body", "hands", "feet"])
def test_starter_can_change_armor(library: ContentLibrary, make_char: MakeChar, slot: str) -> None:
    piece = _item(library, slot)
    char = _starter(library, make_char, gear=(piece,))
    after = world_step(library, make_world(), char, EquipAction(item=piece.id), NOON).char
    assert after.equipment[slot] == piece and after.gear == ()
    assert after.hero.weapon == char.hero.weapon


def _smith_case(
    library: ContentLibrary, make_char: MakeChar, slot: str
) -> tuple[CharacterState, str]:
    piece = _item(library, slot)
    char = _starter(library, lambda **kw: _rich(make_char, **kw), gear=(piece,))
    return char, piece.id


def _gate_refused(library: ContentLibrary, char: CharacterState, action: WorldAction) -> bool:
    """真的跑動作：回傳是不是被開局閘門擋（動作自己的錯誤不算）。"""
    try:
        world_step(library, make_world(), char, action, NOON)
    except WorldActionError as exc:
        return "只限防具" in str(exc)
    return False


@pytest.mark.parametrize(
    ("slot", "refused"),
    [("body", False), ("head", False), ("weapon", True), ("ring", True), ("offhand", True)],
)
def test_starter_smithing_is_armor_only(
    library: ContentLibrary, make_char: MakeChar, slot: str, refused: bool
) -> None:
    char, item = _smith_case(library, make_char, slot)
    for action in (
        EnhanceAction(station=SMITHY, item=item),
        RerollAction(station=ENCHANTER, item=item, index=0),
        ImbueAction(station=ENCHANTER, item=item, index=0, affix="affix_x"),
    ):
        assert _gate_refused(library, char, action) is refused, action


def test_starter_craft_slot_type(library: ContentLibrary, make_char: MakeChar) -> None:
    char, _ = _smith_case(library, make_char, "body")
    kwargs = {"station": SMITHY, "rarity": "rare", "grade": "item_coarse_material"}
    armor = CraftAction(slot_type="body", **kwargs)  # type: ignore[arg-type]
    weapon = CraftAction(slot_type="weapon", **kwargs)  # type: ignore[arg-type]
    assert not _gate_refused(library, char, armor)
    assert _gate_refused(library, char, weapon)


def test_starter_allows_rest_and_teleport(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _starter(library, make_char).model_copy(update={"hp": 1})
    rested = world_step(library, make_world(), char, RestAction(), NOON).char
    assert rested.hp == max_hp(library, rested)
    assert rested.opening == char.opening
    # 第 7 點「能走動、對話、傳送」：閘門不擋（目的地合不合法是傳送自己的事）
    try:
        world_step(library, make_world(), char, TeleportAction(region="capital"), NOON)
    except WorldActionError as exc:
        assert not any(r in str(exc) for r in GATE_REASONS)


# ---------------------------------------------------------------------------
# 升級自動配點
# ---------------------------------------------------------------------------


def _thresholds(library: ContentLibrary) -> tuple[int, ...]:
    assert library.world_rules is not None
    return tuple(library.world_rules.hero_growth.level_thresholds)


@pytest.mark.parametrize("cls", sorted(CLASSES))
def test_level_up_auto_allocates(library: ContentLibrary, make_char: MakeChar, cls: str) -> None:
    char = _starter(library, make_char, cls)
    skills = [library.skills[s] for s in char.hero.skills]
    weapon = library.weapons[char.hero.weapon]
    points = library.roguelite.attribute_points_per_level
    expected = recommended_level_up(skills, weapon, char.hero.attributes, points)
    up, events = gain_xp(library, make_world(), char, _thresholds(library)[0])
    assert up.level == 2 and up.attribute_points == 0
    for attr in Attribute:
        assert up.hero.attributes[attr] == char.hero.attributes[attr] + expected.get(attr, 0)
    assert dict(up.attribute_spent) == expected
    allocated = [e for e in events if isinstance(e, AttributesAllocatedEvent)]
    assert len(allocated) == 1 and allocated[0].attributes == expected
    assert up.hp == char.hp + max_hp(library, up) - max_hp(library, char)
    assert up.insight == char.insight + 2  # 靈感照領


def test_level_up_through_world_action(library: ContentLibrary, make_char: MakeChar) -> None:
    """實際跑世界動作（情境判定給經驗）升級，點數當場配掉。"""
    lib = sure(library, "peddler_safe_path", "success")
    starter = _starter(library, make_char, "melee", xp=_thresholds(library)[0] - 1)
    char = at_event(starter, "wounded_peddler", strong=True)
    result = world_step(lib, make_world(), char, peddler(), NOON)
    assert [e.level for e in result.events if isinstance(e, LeveledUpEvent)] == [2]
    assert result.char.attribute_points == 0
    assert any(isinstance(e, AttributesAllocatedEvent) for e in result.events)


def test_non_starter_points_still_accumulate(library: ContentLibrary, make_char: MakeChar) -> None:
    up, events = gain_xp(library, make_world(), make_char(), _thresholds(library)[0])
    assert up.attribute_points == library.roguelite.attribute_points_per_level
    assert not any(isinstance(e, AttributesAllocatedEvent) for e in events)
    pending, _ = gain_xp(
        library, make_world(), _pending(library, make_char), _thresholds(library)[0]
    )
    assert pending.attribute_points == library.roguelite.attribute_points_per_level


# ---------------------------------------------------------------------------
# 入門武器不能賣、寄、分解（21.5 第 1 點；自然做不到，鎖住）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("cls", "weapon"), sorted(CLASSES.items()))
def test_starter_weapon_is_not_an_item(
    library: ContentLibrary, make_char: MakeChar, cls: str, weapon: str
) -> None:
    piece = _item(library, "body")
    char = _starter(library, make_char, cls, gear=(piece,))
    worn = world_step(library, make_world(), char, EquipAction(item=piece.id), NOON).char
    for state in (char, worn):
        assert all(g.weapon != weapon for g in state.gear)
        assert "main_hand" not in state.equipment
    plain = f"base_{weapon}"
    for action in (
        SellAction(shop=SHOP, item=f"item_{weapon}"),  # ``base_`` 開頭的 ID 連動作格式都不收
        SalvageAction(station=SMITHY, item=plain),
        MailSendAction(to="bob", gear=(plain,)),
        EnhanceAction(station=SMITHY, item=plain),
    ):
        before = worn
        with pytest.raises(WorldActionError):
            world_step(library, make_world(), worn, action, NOON)
        assert worn == before


def test_starter_skills_cannot_be_dissolved(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _starter(library, make_char)
    with pytest.raises(WorldActionError, match="4 級前"):
        world_step(library, make_world(), char, DissolveAction(skill=char.hero.skills[0]), NOON)


# ---------------------------------------------------------------------------
# 世界日誌重播
# ---------------------------------------------------------------------------


def test_new_flow_log_replays_identically(library: ContentLibrary, make_char: MakeChar) -> None:
    lib = sure(library, "peddler_safe_path", "success")
    piece = _item(library, "body")
    start = _pending(library, make_char, gear=(piece,), xp=_thresholds(library)[0] - 1)
    start = at_event(start, "wounded_peddler", "mist_ferry", strong=True)
    world = make_world()
    char = start
    entries: list[WorldLogEntry] = []
    actions: list[WorldAction] = [
        HintSeenAction(ids=("opening",)),
        OpeningClassAction(weapon_class="focus"),
        peddler(),
        RestAction(),
        EquipAction(item=piece.id),
    ]
    for seq, action in enumerate(actions, start=1):
        now = NOON + seq * 60
        result = world_step(lib, world, char, action, now)
        char, world = result.char, result.world
        entries.append(WorldLogEntry(seq=seq, now=now, character_id="alice", action=action))
    assert char.opening is not None and char.opening.stage == "starter" and char.level == 2
    restored = loads_log(dumps_log(entries))
    first = replay(lib, make_world(), {"alice": start}, entries)
    second = replay(lib, make_world(), {"alice": start}, restored)
    assert dumps_char(first.characters["alice"]) == dumps_char(char)
    assert dumps_char(second.characters["alice"]) == dumps_char(char)
    assert first.events == second.events
