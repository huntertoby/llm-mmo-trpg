"""開局在主城工坊靶場（Phase TR-1，#134；:mod:`trpg.world.opening`）。

規則層：未完成開局的動作限制、確定出發（確定性、照 6.27.3 給起始技能、不能重選）、舊存檔遷移、
沙盒試打的設定（木樁 3 個、示範招、確定性種子；會動的木樁真的會退開、木樁不攻擊）。
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, make_world
from trpg.content.library import ContentLibrary
from trpg.engine.actions import EndTurn, UseSkill
from trpg.engine.ai.commanded import CommandedAI
from trpg.engine.ai.utility import UtilityAI
from trpg.engine.battle import begin_battle
from trpg.engine.events import AttackRolled
from trpg.engine.runner import advance, apply_step
from trpg.roguelite.start import start_weapons
from trpg.shared.types import Team
from trpg.world.actions import (
    HintSeenAction,
    OpeningConfirmAction,
    OpeningConfirmedEvent,
    RestAction,
)
from trpg.world.errors import WorldActionError
from trpg.world.opening import (
    apply_opening,
    new_opening,
    pending_hero,
    range_content,
    range_trial,
    trial_seed,
)
from trpg.world.save import dumps_char, loads_char
from trpg.world.state import CHAR_FORMAT, CharacterState
from trpg.world.step import world_step

type MakeChar = Callable[..., CharacterState]

PICK = OpeningConfirmAction(weapon="dagger", keywords=("frozen", "concealed"))


def _pending(library: ContentLibrary, make_char: MakeChar, seed: int = 7) -> CharacterState:
    char = make_char()
    hero = pending_hero(library, char.hero.model_copy(update={"name_zh": "小靶", "race": "human"}))
    return char.model_copy(
        update={"hero": hero, "generated_skills": (), "opening": new_opening(seed)}
    )


def test_pending_hero_has_placeholder_and_no_skills(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _pending(library, make_char)
    assert char.hero.weapon == range_content(library).placeholder_weapon
    assert char.hero.skills == ()
    assert char.hero.name_zh == "小靶" and char.hero.race == "human"


def test_pending_only_confirm_and_notes(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _pending(library, make_char)
    with pytest.raises(WorldActionError, match="確定出發"):
        world_step(library, make_world(), char, RestAction(), NOON)
    noted = world_step(library, make_world(), char, HintSeenAction(ids=("opening",)), NOON)
    assert noted.char.opening is not None


def test_confirm_deterministic_and_gives_starters(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _pending(library, make_char)
    first = world_step(library, make_world(), char, PICK, NOON)
    again = world_step(library, make_world(), char, PICK, NOON)
    assert first.char == again.char
    done = first.char
    assert done.opening is None and done.hero.weapon == "dagger"
    assert len(done.hero.skills) == 2
    assert done.hero.name_zh == "小靶" and done.hero.race == "human"
    event = next(e for e in first.events if isinstance(e, OpeningConfirmedEvent))
    assert event.skills == done.hero.skills and len(event.skill_names) == 2
    # 同一個種子，和 apply_opening 直接給的一樣（建角就選的舊流程也走這套）
    direct, given = apply_opening(library, char, "dagger", ("frozen", "concealed"))
    assert direct.hero == done.hero and tuple(s.id for s in given) == done.hero.skills
    # 不能重選
    with pytest.raises(WorldActionError, match="不能重選"):
        world_step(library, make_world(), done, PICK, NOON)


def test_confirm_rejects_bad_choice(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _pending(library, make_char)
    for bad in (
        OpeningConfirmAction(weapon="dagger", keywords=("frozen",)),
        OpeningConfirmAction(weapon="no_such_weapon", keywords=("frozen", "concealed")),
        OpeningConfirmAction(weapon="dagger", keywords=("frozen", "frozen")),
    ):
        with pytest.raises(WorldActionError):
            world_step(library, make_world(), char, bad, NOON)


def test_old_save_counts_as_done(library: ContentLibrary, make_char: MakeChar) -> None:
    old = json.loads(dumps_char(make_char()))
    assert old["format"] == CHAR_FORMAT == "trpg-char/14"
    old.pop("opening", None)
    old["format"] = "trpg-char/11"
    loaded = loads_char(json.dumps(old))
    assert loaded.format == "trpg-char/14" and loaded.opening is None
    pending = _pending(library, make_char)
    assert loads_char(dumps_char(pending)).opening == pending.opening


def test_trial_setup(library: ContentLibrary, make_char: MakeChar) -> None:
    char = _pending(library, make_char)
    arena = range_content(library)
    trial = range_trial(library, char, "bow")
    assert trial.demo and [s.id for s in trial.skills] == list(arena.demos["ranged"])
    units = trial.setup.units
    assert units[0].team is Team.ALLY and units[0].template.weapon == "bow"
    assert units[0].template.skills == arena.demos["ranged"]
    assert [u.template.id for u in units[1:]] == [d.unit for d in arena.dummies]
    assert trial.seed == trial_seed(7, "bow", ())
    shown = range_trial(library, char, "dagger", ("frozen",))
    assert not shown.demo and len(shown.skills) == 1
    # 看示範給的招＝確定出發第 1 個關鍵字會給的招
    done, given = apply_opening(library, char, "dagger", ("frozen", "concealed"))
    assert shown.skills[0].id == given[0].id
    assert done.hero.skills[0] == given[0].id


def test_trial_needs_pending(library: ContentLibrary, make_char: MakeChar) -> None:
    with pytest.raises(WorldActionError):
        range_trial(library, make_char(), "bow")


def test_dummies_never_attack_and_moving_one_backs_off(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    char = _pending(library, make_char)
    trial = range_trial(library, char, "dagger")
    arena = range_content(library)
    moving = arena.dummies[0].at
    hero_spawn = trial.setup.units[0].model_copy(update={"position": (moving[0] - 1, moving[1])})
    setup = trial.setup.model_copy(update={"units": (hero_spawn, *trial.setup.units[1:])})
    opened = begin_battle(setup, trial.seed)
    state = opened.state
    hero_id = state.active_unit
    assert hero_id is not None and state.units[hero_id].team is Team.ALLY
    hp = state.units[hero_id].hp
    starts = {u.id: u.xy for u in state.units.values() if u.team is Team.ENEMY}
    after = apply_step(state, EndTurn(unit_id=hero_id)).state
    policy = CommandedAI(UtilityAI(library.ai_profiles), {})
    after, _, _ = advance(
        after, None, policy, stop=lambda st, p: p is None and st.active_unit == hero_id
    )
    assert after.units[hero_id].hp == hp  # 木樁不攻擊
    ends = {u.id: u.xy for u in after.units.values() if u.team is Team.ENEMY}
    moved = [uid for uid in starts if starts[uid] != ends[uid]]
    assert len(moved) == 1  # 只有會動的木樁退開


DEMOS_148: dict[str, list[str]] = {
    "melee": ["skill_shadow_backstab", "skill_wild_blade"],
    "ranged": ["skill_rng_venom_arrow", "skill_oil_spark_throw"],
    "focus": ["skill_fire_bolt", "skill_spark_chain"],
}
"""#148（21 21.5）指定的示範招。"""

TRIAL_STAND: dict[str, tuple[int, int]] = {"melee": (6, 5), "ranged": (6, 7), "focus": (6, 7)}
"""試打時主角站的位置：普通木樁 (6, 4) 的南邊，避開旁邊的石柱 (5, 4)。"""


def test_demos_are_the_148_skills(library: ContentLibrary) -> None:
    assert dict(range_content(library).demos) == {k: tuple(v) for k, v in DEMOS_148.items()}


def _trial_cast(library: ContentLibrary, char: CharacterState, weapon: str, skill: str) -> None:
    """從靶場試打的設定開場，對普通木樁放一次 ``skill``，要真的走完引擎。"""
    trial = range_trial(library, char, weapon)
    stand = TRIAL_STAND[library.weapons[weapon].weapon_class]
    hero_spawn = trial.setup.units[0].model_copy(update={"position": stand})
    setup = trial.setup.model_copy(update={"units": (hero_spawn, *trial.setup.units[1:])})
    state = begin_battle(setup, trial.seed).state
    hero_id = next(u.id for u in state.units.values() if u.team is Team.ALLY)
    if state.active_unit != hero_id:
        policy = CommandedAI(UtilityAI(library.ai_profiles), {})
        state, _, _ = advance(
            state, None, policy, stop=lambda st, p: p is None and st.active_unit == hero_id
        )
    target = state.unit_at(*range_content(library).dummies[2].at)
    assert target is not None
    action = UseSkill(unit_id=hero_id, skill_id=skill, target_id=target.id)
    result = apply_step(state, action)
    rolls = [e for e in result.events if isinstance(e, AttackRolled) and e.skill_id == skill]
    assert rolls, f"{weapon} 放 {skill} 沒有命中判定"
    assert rolls[0].target_id == target.id


def test_all_demos_cast_in_the_range_with_every_weapon(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """6 招示範招用該大類的每把武器都能在靶場實際施放（跑引擎）。"""
    char = _pending(library, make_char)
    for weapon in start_weapons(library):
        for skill in DEMOS_148[library.weapons[weapon].weapon_class]:
            _trial_cast(library, char, weapon, skill)
