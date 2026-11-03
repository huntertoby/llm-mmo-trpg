"""立誓與解除誓約（Phase 5A-6 接點、5C-3 內容；``docs/phases/Phase5計畫.md`` 12.2 第 8 項、24.7）。

前半用最小的測試樣本（代決 5A6-9）；後半用 ``content/world/oaths.yaml`` 的 18.6 模板：難度、
被動欄位、開戰帶加成、違反與守住的世界事件、重播。
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_encounter, make_world
from trpg.content.library import ContentLibrary
from trpg.content.world_oaths import OathProposal, OathTable, oath_problems
from trpg.world.actions import (
    BattleStartedEvent,
    FightAction,
    LoadoutAction,
    OathBrokenEvent,
    OathKeptEvent,
    OathReleasedEvent,
    OathSwornEvent,
    ReleaseOathAction,
    SwearOathAction,
    TravelAction,
)
from trpg.world.battle import auto_steps, prepare_battle
from trpg.world.errors import WorldActionError
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char
from trpg.world.state import CharacterState
from trpg.world.step import world_step

MakeChar = Callable[..., CharacterState]

SAMPLE = OathTable.model_validate(
    {
        "templates": [
            {"id": "no_items", "name_zh": "不使用道具", "difficulty": "easy"},
            {
                "id": "melee_kills",
                "name_zh": "每場至少用近戰擊殺 N 名敵人",
                "difficulty": "medium",
                "params": [{"id": "n", "kind": "int", "min": 1, "max": 2}],
            },
            {
                "id": "one_element",
                "name_zh": "只用某一種元素的技能造成傷害",
                "difficulty": "hard",
                "params": [{"id": "element", "kind": "choice", "choices": ["fire", "ice"]}],
            },
        ]
    }
)


@pytest.fixture(scope="module")
def sworn_lib(library: ContentLibrary) -> ContentLibrary:
    return dataclasses.replace(library, world_oaths=SAMPLE)


def _swear(template: str, **params: str | int) -> SwearOathAction:
    return SwearOathAction(
        proposal=OathProposal(template=template, params=params), player_text="我絕不後退"
    )


def test_static_problems() -> None:
    assert oath_problems(SAMPLE, OathProposal(template="no_items")) == []
    assert oath_problems(SAMPLE, OathProposal(template="nope"))
    assert oath_problems(SAMPLE, OathProposal(template="melee_kills"))  # 缺參數
    assert oath_problems(SAMPLE, OathProposal(template="melee_kills", params={"n": 3}))
    assert oath_problems(SAMPLE, OathProposal(template="one_element", params={"element": "dark"}))
    assert oath_problems(SAMPLE, OathProposal(template="no_items", params={"x": 1}))


def test_swear_and_release_with_cooldown(sworn_lib: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    sworn = world_step(sworn_lib, world, make_char(), _swear("melee_kills", n=2), NOON)
    oath = sworn.char.oath
    assert oath is not None
    assert (oath.template, oath.params, oath.difficulty, oath.sworn_at) == (
        "melee_kills",
        {"n": 2},
        "medium",
        NOON,
    )
    assert isinstance(sworn.events[0], OathSwornEvent)
    with pytest.raises(WorldActionError, match="同時只能有 1 個"):
        world_step(sworn_lib, world, sworn.char, _swear("no_items"), NOON)
    released = world_step(sworn_lib, world, sworn.char, ReleaseOathAction(), NOON + 10)
    assert released.char.oath is None
    assert released.char.oath_cooldown_until == NOON + 10 + 86400
    assert isinstance(released.events[0], OathReleasedEvent)
    with pytest.raises(WorldActionError, match="1 天"):
        world_step(sworn_lib, world, released.char, _swear("no_items"), NOON + 86000)
    again = world_step(sworn_lib, world, released.char, _swear("no_items"), NOON + 10 + 86400)
    assert again.char.oath is not None


def test_swear_rejections(
    library: ContentLibrary, sworn_lib: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    bare = dataclasses.replace(library, world_oaths=None)
    with pytest.raises(WorldActionError, match="誓約模板"):
        world_step(bare, world, make_char(), _swear("no_items"), NOON)  # 內容沒有模板
    with pytest.raises(WorldActionError, match="城鎮與營火"):
        world_step(sworn_lib, world, make_char(location="ferry_steps"), _swear("no_items"), NOON)
    with pytest.raises(WorldActionError, match="必須是"):
        world_step(sworn_lib, world, make_char(), _swear("one_element", element="dark"), NOON)
    with pytest.raises(WorldActionError, match="沒有誓約"):
        world_step(sworn_lib, world, make_char(), ReleaseOathAction(), NOON)


# ---------------------------------------------------------------------------
# 5C-3：18.6 的模板內容
# ---------------------------------------------------------------------------

PASSIVES = ("skill_bloodlust", "skill_fleet_foot", "skill_lucky_break")


def test_real_templates_difficulty(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    for n, level in ((1, "easy"), (2, "medium")):  # 18.6 模板 6：易／中（代決 5C3-7）
        char = world_step(library, world, make_char(), _swear("oath_melee_kills", n=n), NOON).char
        assert char.oath is not None and char.oath.difficulty == level
    hard = world_step(library, world, make_char(), _swear("oath_solo"), NOON).char
    assert hard.oath is not None and hard.oath.difficulty == "hard"


def test_oath_takes_a_passive_slot(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    base = make_char()
    full = base.model_copy(update={"hero": base.hero.model_copy(update={"skills": PASSIVES})})
    with pytest.raises(WorldActionError, match="被動欄位"):
        world_step(library, world, full, _swear("oath_no_heal"), NOON)
    two = full.model_copy(
        update={
            "hero": full.hero.model_copy(update={"skills": PASSIVES[:2]}),
            "bench": (PASSIVES[2],),
        }
    )
    sworn = world_step(library, world, two, _swear("oath_no_heal"), NOON).char
    with pytest.raises(WorldActionError):  # 有誓約時被動只能裝 2 招
        world_step(library, world, sworn, LoadoutAction(skills=PASSIVES), NOON)
    released = world_step(library, world, sworn, ReleaseOathAction(), NOON).char
    back = world_step(library, world, released, LoadoutAction(skills=PASSIVES), NOON).char
    assert back.hero.skills == PASSIVES


def _ready(char: CharacterState) -> CharacterState:
    encounter = make_encounter(
        "ferry_steps", seed=5, battle_map="cliff_outpost", from_location="mist_ferry"
    )
    return char.model_copy(update={"location": "ferry_steps", "pending_encounter": encounter})


def test_battle_carries_oath_bonus(library: ContentLibrary, make_char: MakeChar) -> None:
    sworn = world_step(
        library, make_world(), make_char(), _swear("oath_no_category", category="spell"), NOON
    ).char
    prepared = prepare_battle(library, _ready(sworn))
    oath = prepared.setup.oath
    assert oath is not None and oath.unit == 0
    assert (oath.check.kind, oath.check.category) == ("forbid_skill_category", "spell")
    assert oath.bonus_status == "oath_bonus_medium"
    assert (oath.penalty_status, oath.penalty_rounds) == ("oath_broken", 2)
    assert prepare_battle(library, _ready(make_char())).setup.oath is None


def test_solo_oath_broken_with_party_kept_alone(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    sworn = world_step(library, world, make_char(), _swear("oath_solo"), NOON).char
    ready = _ready(sworn)  # 預設帶鐵壁＋回春：開場就違反
    fought = world_step(library, world, ready, FightAction(steps=auto_steps(library, ready)), NOON)
    broken = [e for e in fought.events if isinstance(e, OathBrokenEvent)]
    assert broken == [OathBrokenEvent(template="oath_solo", check="solo", at_end=False)]
    last = fought.char.last_battle
    assert last is not None and last.oath == "oath_solo" and last.oath_broken
    assert fought.char.oath is not None  # 違反不解除（下一場恢復）
    alone = _ready(sworn.model_copy(update={"mercenaries": ()}))
    kept = world_step(library, world, alone, FightAction(steps=auto_steps(library, alone)), NOON)
    assert OathKeptEvent(template="oath_solo") in kept.events
    started = next(e for e in kept.events if isinstance(e, BattleStartedEvent))
    assert started.oath == "oath_solo"


def test_oath_battle_replays(calm: ContentLibrary, make_char: MakeChar) -> None:
    start = make_char()
    who = start.character_id
    entries = [
        WorldLogEntry(seq=1, now=NOON, character_id=who, action=_swear("oath_attack_each_turn")),
        WorldLogEntry(
            seq=2, now=NOON + 30, character_id=who, action=TravelAction(to="ferry_steps")
        ),
    ]
    first = replay(calm, make_world(), {who: start}, entries)
    second = replay(calm, make_world(), {who: start}, entries)
    assert dumps_char(first.characters[who]) == dumps_char(second.characters[who])
    oath = first.characters[who].oath
    assert oath is not None and oath.template == "oath_attack_each_turn"


def test_end_of_battle_breach_carries_penalty_to_next_battle(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    sworn = world_step(library, world, make_char(), _swear("oath_melee_kills", n=2), NOON).char
    ready = _ready(sworn)
    before = prepare_battle(library, ready).setup.oath
    assert before is not None and before.start_penalty_rounds == 0
    fought = world_step(library, world, ready, FightAction(steps=auto_steps(library, ready)), NOON)
    broken = [e for e in fought.events if isinstance(e, OathBrokenEvent)]
    assert broken and broken[0].at_end  # 近戰擊殺 2 名：戰鬥結束時才判出違反
    assert fought.char.oath_broken_next
    nxt = prepare_battle(library, _ready(fought.char)).setup.oath
    assert nxt is not None
    assert (nxt.start_penalty_rounds, nxt.bonus_status) == (2, "oath_bonus_medium")
    assert nxt.label_zh == "每場至少用近戰擊殺 N 名敵人"
    released = world_step(library, world, fought.char, ReleaseOathAction(), NOON).char
    assert not released.oath_broken_next  # 解除誓約就清掉


def test_carried_penalty_is_consumed_by_the_next_battle(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    sworn = world_step(library, world, make_char(), _swear("oath_attack_each_turn"), NOON).char
    ready = _ready(sworn.model_copy(update={"oath_broken_next": True}))
    carried = prepare_battle(library, ready).setup.oath
    assert carried is not None and carried.start_penalty_rounds == 2
    fought = world_step(library, world, ready, FightAction(steps=auto_steps(library, ready)), NOON)
    assert not fought.char.oath_broken_next  # 打完一場就重新判定（這場不是戰鬥結束才判的）
