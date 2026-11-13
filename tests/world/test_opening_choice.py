"""#150 開局先玩再定的第 2 段（Phase OB-2；21 21.5、:mod:`trpg.world.opening_choice`）。

一律跑真的世界動作：入門期打新手第 1、2 步（三選一延後）→ 回霧渡鎮正式選定（換武器與招、收回入門
招、屬性重配、延後的三選一依序出題）→ 選三選一；關鍵字推薦；入門期不存影子；世界日誌重播。
入門招一律從 ``range.demos`` 讀，不寫死技能 ID。
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable

import pytest

from tests.world.helpers import NOON, PARTY, make_encounter, make_world
from tests.world.test_gear import _item
from tests.world.test_opening_stages import _pending, _starter
from tests.world.test_quests import STARTER_FIXED, _with_quest, _won
from trpg.content.library import ContentLibrary
from trpg.roguelite.start import (
    apply_allocation,
    links_between,
    new_keyword_run,
    pick_starters,
    recommended_level_up,
    start_hero,
    start_weapons,
)
from trpg.shared.types import Attribute
from trpg.skillgen.keywords import derive_keywords
from trpg.skillgen.usage import SkillUsage
from trpg.world.actions import (
    AcceptQuestAction,
    AllocateAction,
    BattleEndedEvent,
    FightAction,
    InsightGainedEvent,
    LoadoutAction,
    OfferPickAction,
    OpeningClassAction,
    OpeningConfirmAction,
    OpeningConfirmedEvent,
    QuestStepDoneEvent,
    RespecAction,
    RestAction,
    ShadowSavedEvent,
    SkillOfferedEvent,
    SkillOfferTakenEvent,
    TravelAction,
    WorldAction,
)
from trpg.world.battle import auto_steps
from trpg.world.common import max_hp, max_mana
from trpg.world.economy_actions import EquipAction
from trpg.world.errors import WorldActionError
from trpg.world.opening import (
    mentor_town,
    range_content,
    recommended_keywords,
    starter_skill_ids,
)
from trpg.world.opening_choice import STARTER_STEPS, choice_problem, full_allocation
from trpg.world.quests import advance_quests, issue_deferred_offers, quest_home
from trpg.world.replay import WorldLogEntry, replay
from trpg.world.save import dumps_char, dumps_log, dumps_world, loads_log
from trpg.world.state import (
    CharacterState,
    DeferredOffer,
    FieldContact,
    FieldPos,
    WorldState,
)
from trpg.world.step import StepResult, world_step

type MakeChar = Callable[..., CharacterState]

QUEST = "starter_ferry"
STEP_PLACES = ("ferry_steps", "bamboo_path")
"""新手第 1、2 步固定戰的地點（任務資料 ``quests/cloud_ridge.yaml``）。"""
CHOICES = {
    # 入門大類 → 正式選的武器與關鍵字（都換到別的大類：基礎值要照新大類重建）
    "melee": ("fire_staff", ("ignite", "charged")),
    "ranged": ("greatsword", ("prone", "ignite")),
    "focus": ("bow", ("ignite", "frozen")),
}
MAX_FIGHT_SEEDS = 24


def _step(
    library: ContentLibrary, char: CharacterState, action: WorldAction, world: WorldState
) -> StepResult:
    return world_step(library, world, char, action, NOON)


def _fixed_fight(char: CharacterState, location: str, seed: int) -> CharacterState:
    """站到 ``location``、碰上那裡的新手固定戰（同 ``test_real_fight_advances_starter``）。"""
    encounter = make_encounter(location, seed=seed, battle_map="cliff_outpost")
    contact = FieldContact(
        map=location,
        spawn=0,
        group=STARTER_FIXED[location],
        lineup_seed=seed,
        x=0,
        y=0,
        retreat_to=FieldPos(map=location, x=0, y=0),
    )
    pending = encounter.model_copy(update={"contact": contact})
    return char.model_copy(update={"location": location, "pending_encounter": pending})


def _win(
    library: ContentLibrary, world: WorldState, char: CharacterState, location: str
) -> tuple[StepResult, CharacterState]:
    """真的打贏 ``location`` 的固定戰（AI 代打，換種子到贏為止）；回傳結果與開打前的角色。"""
    for seed in range(MAX_FIGHT_SEEDS):
        start = _fixed_fight(char, location, seed)
        result = _step(library, start, FightAction(steps=auto_steps(library, start)), world)
        if any(isinstance(e, BattleEndedEvent) and e.won for e in result.events):
            return result, start
    pytest.fail(f"{location} 找不到會贏的種子")


def _played(
    library: ContentLibrary, make_char: MakeChar, cls: str, **updates: object
) -> CharacterState:
    """選大類 → 接新手任務 → 真的打完第 1、2 步 → 回霧渡鎮（入門期，還沒正式選定）。"""
    world = make_world()
    char = _starter(library, make_char, cls, mercenaries=PARTY, **updates)
    char = _step(library, char, AcceptQuestAction(quest=QUEST), world).char
    for index, location in enumerate(STEP_PLACES):
        before = char
        result, _start = _win(library, world, char, location)
        char = result.char
        # 第 2 點：經驗、靈感照領，升級點數自動配掉；三選一先保留、不出題
        assert [e.index for e in result.events if isinstance(e, QuestStepDoneEvent)] == [index + 1]
        assert not any(isinstance(e, SkillOfferedEvent) for e in result.events)
        assert any(isinstance(e, InsightGainedEvent) for e in result.events)
        assert char.pending_offers == () and char.offers_made == before.offers_made
        assert char.level == index + 2 and char.attribute_points == 0
        assert char.insight > before.insight
        assert char.opening is not None
        assert char.opening.deferred_offers == tuple(
            DeferredOffer(quest=QUEST, step=i) for i in range(index + 1)
        )
    return char.model_copy(update={"location": "mist_ferry"})


def _fast_played(
    library: ContentLibrary, make_char: MakeChar, cls: str = "melee", **updates: object
) -> CharacterState:
    """不打真的戰鬥的版本（任務推進用打贏的事件）：入門期、打完第 1、2 步、人在霧渡鎮。"""
    world = make_world()
    char = _with_quest(_starter(library, make_char, cls, **updates), QUEST)
    for location in STEP_PLACES:
        char, _ = advance_quests(library, world, char, _won(location), NOON)
    return char


def _confirm(cls: str) -> OpeningConfirmAction:
    weapon, keywords = CHOICES[cls]
    return OpeningConfirmAction(weapon=weapon, keywords=keywords)


# ---------------------------------------------------------------------------
# 表格：三大類 × 入門期打完第 1、2 步 → 正式選定
# ---------------------------------------------------------------------------


def _check_kit(
    library: ContentLibrary, played: CharacterState, result: StepResult, cls: str
) -> tuple[str, ...]:
    """武器與招（和靶場預覽同一個種子）、入門招與使用紀錄收回、階段；回傳起始 2 招。"""
    assert played.opening is not None
    char = result.char
    weapon, keywords = CHOICES[cls]
    demos = range_content(library).demos[cls]  # type: ignore[index]
    run = new_keyword_run(library, weapon, keywords, played.opening.seed, "recommended")
    given = run.hero.skills
    assert char.hero.weapon == weapon
    assert char.hero.skills[:2] == given and len(given) == 2
    assert {s.id for s in run.generated_skills} <= {s.id for s in char.generated_skills}
    event = next(e for e in result.events if isinstance(e, OpeningConfirmedEvent))
    assert (event.weapon, event.keywords, event.skills) == (weapon, keywords, given)
    assert len(event.skill_names) == 2 and all(event.skill_names)
    # 入門招與使用紀錄收回（剛好和新的起始技能同一招時，那一招是新給的、紀錄是空的）
    for gone in set(demos) - set(given):
        assert gone not in char.hero.skills and gone not in char.bench
    for demo in demos:
        assert demo not in char.skill_usage and demo not in char.flash
        assert demo not in char.skill_regions
    assert not starter_skill_ids(library, char)
    assert char.opening is not None
    assert char.opening.stage == "chosen"
    assert char.opening.weapon == weapon and char.opening.keywords == keywords
    assert char.opening.weapon_class == library.weapons[weapon].weapon_class
    assert char.opening.granted_skills == given
    return given


def _check_numbers(
    library: ContentLibrary, played: CharacterState, char: CharacterState, cls: str
) -> None:
    """基礎值照新大類重建、點數全部重配並記在 ``attribute_spent``、HP 與法力回滿。"""
    assert played.opening is not None
    weapon, keywords = CHOICES[cls]
    rules = library.roguelite
    picked = pick_starters(library, weapon, keywords, played.opening.seed)
    points = rules.start_free_points + 2 * rules.attribute_points_per_level
    assert points == 8
    weapon_def = library.weapons[weapon]
    allocation = full_allocation(library, picked, weapon_def, points)
    expected = apply_allocation(start_hero(library, weapon, char.hero.skills), allocation)
    expected = expected.model_copy(
        update={
            "name_zh": played.hero.name_zh,
            "race": played.hero.race,
            "doll": played.hero.doll,
        }
    )
    assert char.hero == expected  # 名字、種族、外觀照舊，其餘是新大類的基礎值
    assert char.attribute_points == 0
    assert sum(char.attribute_spent.values()) == points
    assert dict(char.attribute_spent) == allocation
    # 和「一開始就拿這套、每級照推薦配」的結果相同
    run = new_keyword_run(library, weapon, keywords, played.opening.seed, "recommended")
    walked = dict(run.hero.attributes)
    for _level in range(2):
        per = rules.attribute_points_per_level
        for attr, n in recommended_level_up(picked, weapon_def, walked, per).items():
            walked[attr] += n
    assert dict(char.hero.attributes) == walked
    assert (char.level, char.xp, char.insight) == (3, played.xp, played.insight)
    assert char.hp == max_hp(library, char) and char.mana == max_mana(library, char)


def _check_offer(
    library: ContentLibrary, char: CharacterState, events: tuple[object, ...], index: int
) -> None:
    """延後的三選一一次出一組（OB-3）：第 ``index`` 組，內容照任務資料（``mix``、``min_passive``、
    任務所在的區域）。"""
    home = quest_home(library, QUEST)
    assert home is not None
    region, quest = home
    step = quest.steps[index]
    offered = [e for e in events if isinstance(e, SkillOfferedEvent)]
    assert [(e.quest, e.step) for e in offered] == [(QUEST, step.id)]
    assert [(p.quest, p.step) for p in char.pending_offers] == [(QUEST, step.id)]
    pending = char.pending_offers[0]
    reward = step.reward.offer
    assert reward is not None and reward.mix is not None
    assert pending.region == region and pending.source == "quest"
    assert len(pending.offer.candidates) == 3
    deepen, bridge, new = reward.mix.as_tuple()
    wanted = {"deepen": deepen, "bridge": bridge, "new": new}
    assert Counter(t.kind for t in pending.offer.tags) == {k: v for k, v in wanted.items() if v}
    assert any(s.kind == "passive" for s in pending.offer.candidates) or not reward.min_passive


@pytest.mark.parametrize("cls", sorted(CHOICES))
def test_formal_choice_after_two_steps(
    library: ContentLibrary, make_char: MakeChar, cls: str
) -> None:
    world = make_world()
    played = _played(library, make_char, cls)
    demos = range_content(library).demos[cls]  # type: ignore[index]
    assert starter_skill_ids(library, played) == demos and played.hero.skills[:2] == demos
    # 入門期真的用過入門招，留下用法與閃現的紀錄
    assert set(played.skill_usage) & set(demos)
    assert set(played.flash) & set(demos)
    result = _step(library, played, _confirm(cls), world)
    char = result.char
    given = _check_kit(library, played, result, cls)
    _check_numbers(library, played, char, cls)
    # 選三選一：選完一組才出下一組（OB-3）；選到的招記進 granted_skills（重選時要收回）
    taken: list[str] = []
    events: tuple[object, ...] = result.events
    for index in range(2):
        _check_offer(library, char, events, index)
        assert char.offers_made == played.offers_made + index + 1
        owned = {*char.hero.skills, *char.bench}
        assert not owned & {s.id for s in char.pending_offers[0].offer.candidates}
        picked_result = _step(library, char, OfferPickAction(pick=0), world)
        char, events = picked_result.char, picked_result.events
        took = next(e for e in picked_result.events if isinstance(e, SkillOfferTakenEvent))
        assert took.skill is not None
        taken.append(took.skill)
    assert char.pending_offers == () and len(set(taken)) == 2
    assert not any(isinstance(e, SkillOfferedEvent) for e in events)
    assert char.opening is not None and char.opening.granted_skills == (*given, *taken)
    # 入門期的限制解除（換技能），正式選定不能再送
    assert _step(library, char, LoadoutAction(skills=char.hero.skills), world).char.hero.skills
    with pytest.raises(WorldActionError, match="已經正式選定"):
        _step(library, char, _confirm(cls), world)


# ---------------------------------------------------------------------------
# 三選一的出題規則與「不延後」時相同
# ---------------------------------------------------------------------------


def test_deferred_offers_match_undeferred_rule(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """延後的三選一＝同一個角色（正式的武器與招）在任務所在的區域當場完成那一步會拿到的三選一：
    同一個技能種子、同一個計數；選完第 1 組才出第 2 組（和不延後時「打完一步出一組」相同）。"""
    world = make_world()
    played = _fast_played(library, make_char, "melee")
    chosen = _step(library, played, _confirm("melee"), world).char
    # 對照組：一樣的角色，但不延後（已完成開局）、任務退回第 0 步，照舊流程一步一步完成
    plain = chosen.model_copy(
        update={
            "opening": None,
            "pending_offers": (),
            "offers_made": played.offers_made,
            "quests": _with_quest(make_char(), QUEST).quests,
        }
    )
    for location in STEP_PLACES:
        plain, events = advance_quests(library, world, plain, _won(location), NOON)
        assert any(isinstance(e, SkillOfferedEvent) for e in events)
        assert len(chosen.pending_offers) == 1
        assert plain.pending_offers == chosen.pending_offers
        assert plain.offers_made == chosen.offers_made
        plain = _step(library, plain, OfferPickAction(pick=0), world).char
        chosen = _step(library, chosen, OfferPickAction(pick=0), world).char
        assert (plain.hero.skills, plain.bench) == (chosen.hero.skills, chosen.bench)
    assert plain.pending_offers == chosen.pending_offers == ()


def test_second_group_never_repeats_the_skill_taken_from_the_first(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """21.5「OB-2 補充」：不能從兩組拿到同一招。兩組候選有交集的情況：先照舊規則（選定當下兩組
    一起出）算出第 2 組，把其中一招內容庫的技能放進第 1 組讓玩家選走——選完才出的第 2 組不會再有
    它（出題時已經擁有的招不會當候選）。候選大多是生成技能（ID 不重複），自然出現交集的種子很少，
    所以交集用舊規則的第 2 組來造。"""
    world = make_world()
    chosen = _step(library, _fast_played(library, make_char), _confirm("melee"), world).char
    assert len(chosen.pending_offers) == 1
    old_rule, _ = issue_deferred_offers(library, world, chosen, after=0)  # 舊：不等第 1 組選完
    old_second = old_rule.pending_offers[1].offer.candidates
    # KW-2：新方向多 4 個關鍵字後這個種子的舊第 2 組全是生成技能；沒有內容庫的技能時拿第一張
    # （生成技能拿走後一樣算已擁有，不會再當候選）
    shared = next((s for s in old_second if s.id in library.skills), old_second[0])
    first = chosen.pending_offers[0]
    candidates = (shared, *first.offer.candidates[1:])
    offer = first.offer.model_copy(update={"candidates": candidates})
    both_have = chosen.model_copy(
        update={"pending_offers": (first.model_copy(update={"offer": offer}),)}
    )
    result = _step(library, both_have, OfferPickAction(pick=0), world)
    took = next(e for e in result.events if isinstance(e, SkillOfferTakenEvent))
    assert took.skill == shared.id
    char = result.char
    assert len(char.pending_offers) == 1 and char.pending_offers[0].step != first.step
    second = [s.id for s in char.pending_offers[0].offer.candidates]
    assert shared.id not in second
    assert [s.id for s in old_second] != second
    # 跳過第 1 組也會接著出第 2 組；兩組選完就沒有了
    skipped = _step(library, chosen, OfferPickAction(), world)
    assert [e.step for e in skipped.events if isinstance(e, SkillOfferedEvent)] == [
        char.pending_offers[0].step
    ]
    done = _step(library, skipped.char, OfferPickAction(pick=0), world)
    assert done.char.pending_offers == ()
    assert not any(isinstance(e, SkillOfferedEvent) for e in done.events)


def test_formal_choice_is_deterministic(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    first = _step(library, _fast_played(library, make_char), _confirm("melee"), world)
    second = _step(library, _fast_played(library, make_char), _confirm("melee"), world)
    assert dumps_char(first.char) == dumps_char(second.char)
    assert first.events == second.events


def test_offers_use_quest_region_when_chosen_in_capital(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """在主城靶場選定：三選一的取得地點、偏向還是任務所在的區域，內容和在霧渡鎮選的一樣。"""
    world = make_world()
    played = _fast_played(library, make_char)
    in_town = _step(library, played, _confirm("melee"), world).char
    capital = played.model_copy(update={"region": "capital", "location": "capital"})
    in_capital = _step(library, capital, _confirm("melee"), world).char
    assert in_capital.pending_offers == in_town.pending_offers
    assert all(p.region == "cloud_ridge" for p in in_capital.pending_offers)


def test_other_quests_and_done_characters_still_offer_at_once(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """只有入門期的新手任務延後：舊角色照舊當場出題（``opening is None``）。"""
    char = _with_quest(make_char(location="ferry_steps"), QUEST)
    char, events = advance_quests(library, make_world(), char, _won("ferry_steps"), NOON)
    assert any(isinstance(e, SkillOfferedEvent) for e in events)
    assert len(char.pending_offers) == 1 and char.offers_made == 1


# ---------------------------------------------------------------------------
# 正式選定的條件
# ---------------------------------------------------------------------------


def test_choice_needs_two_steps(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    assert STARTER_STEPS == 2
    fresh = _starter(library, make_char)
    one = _with_quest(fresh, QUEST)
    one, _ = advance_quests(library, world, one, _won(STEP_PLACES[0]), NOON)
    for char in (fresh, one):
        assert choice_problem(library, char) is not None
        with pytest.raises(WorldActionError, match="還不能正式選定"):
            _step(library, char, _confirm("melee"), world)


def test_choice_needs_mentor_town_or_capital(library: ContentLibrary, make_char: MakeChar) -> None:
    world = make_world()
    played = _fast_played(library, make_char)
    assert mentor_town(library) == ("cloud_ridge", "mist_ferry")
    assert choice_problem(library, played) is None
    away = played.model_copy(update={"location": "bamboo_path"})
    with pytest.raises(WorldActionError, match="霧渡鎮找葛蘭"):
        _step(library, away, _confirm("melee"), world)
    capital = played.model_copy(update={"region": "capital", "location": "capital"})
    assert _step(library, capital, _confirm("melee"), world).char.opening is not None
    blocked = played.model_copy(update={"pending_encounter": make_encounter("mist_ferry")})
    with pytest.raises(WorldActionError, match="遭遇"):
        _step(library, blocked, _confirm("melee"), world)


def test_choice_rejects_bad_weapon_or_keywords(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    played = _fast_played(library, make_char)
    bad: list[WorldAction] = [
        OpeningConfirmAction(weapon="no_such_weapon", keywords=("ignite", "charged")),
        OpeningConfirmAction(weapon="fire_staff", keywords=("ignite",)),
        OpeningConfirmAction(weapon="fire_staff", keywords=("ignite", "ignite")),
        OpeningConfirmAction(weapon="fire_staff", keywords=("ignite", "no_such_keyword")),
    ]
    for action in bad:
        before = dumps_char(played)
        with pytest.raises(WorldActionError):
            _step(library, played, action, world)
        assert dumps_char(played) == before


def test_pick_class_stage_keeps_old_one_shot_confirm(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """選大類之前送 ``opening_confirm``＝舊的一次選定（OB-5 換前端之前照收），直接完成開局。"""
    pending = _pending(library, make_char)
    done = _step(library, pending, _confirm("melee"), make_world()).char
    assert done.opening is None and done.hero.weapon == CHOICES["melee"][0]


# ---------------------------------------------------------------------------
# 入門期手動配點、重配不擋：正式選定時全部重配
# ---------------------------------------------------------------------------


def test_manual_respec_before_choice_does_not_change_result(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    played = _fast_played(library, make_char)
    plain = _step(library, played, _confirm("melee"), world).char
    respecced = _step(library, played, RespecAction(), world).char
    assert respecced.attribute_points == 4  # 升級的 4 點退回；開局的 4 點不在 attribute_spent
    partly = _step(library, respecced, AllocateAction(attributes={Attribute.CON: 1}), world).char
    assert partly.attribute_points == 3
    for char in (respecced, partly):
        chosen = _step(library, char, _confirm("melee"), world).char
        assert chosen.hero == plain.hero
        assert chosen.attribute_spent == plain.attribute_spent and chosen.attribute_points == 0
        assert chosen.hp == plain.hp and chosen.mana == plain.mana


def test_two_handed_choice_stows_off_hand(library: ContentLibrary, make_char: MakeChar) -> None:
    """選雙手武器：穿著的副手收進背包（同換主手的規則）；防具照穿。"""
    world = make_world()
    shield, body = _item(library, "offhand"), _item(library, "body")
    played = _fast_played(library, make_char, gear=(shield, body))
    for piece in (shield, body):
        played = _step(library, played, EquipAction(item=piece.id), world).char
    assert set(played.equipment) == {"off_hand", "body"} and played.gear == ()
    assert library.weapons["greatsword"].two_handed
    action = OpeningConfirmAction(weapon="greatsword", keywords=("prone", "ignite"))
    chosen = _step(library, played, action, world).char
    assert set(chosen.equipment) == {"body"} and chosen.gear == (shield,)
    assert not library.weapons["one_handed_sword"].two_handed
    action = OpeningConfirmAction(weapon="one_handed_sword", keywords=("prone", "ignite"))
    one_handed = _step(library, played, action, world).char
    assert set(one_handed.equipment) == {"off_hand", "body"} and one_handed.gear == ()


def test_choice_refused_with_reason_when_bag_is_full(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """21.5「OB-2 補充」：副手收不進背包就不能選定，訊息寫明哪把武器、為什麼、差幾格；角色不變。
    騰出一格之後就能選。"""
    world = make_world()
    rules = library.world_economy.rules
    assert rules is not None
    shield = _item(library, "offhand")
    played = _fast_played(library, make_char, gear=(shield,))
    played = _step(library, played, EquipAction(item=shield.id), world).char
    full = played.model_copy(update={"bag": {"item_coarse_material": 20 * rules.bag_slots}})
    action = OpeningConfirmAction(weapon="greatsword", keywords=("prone", "ignite"))
    before = dumps_char(full)
    with pytest.raises(WorldActionError) as refused:
        _step(library, full, action, world)
    name = library.weapons["greatsword"].name_zh
    slots = rules.bag_slots
    assert str(refused.value) == (
        f"不能選{name}：它占用副手，副手要收進背包，"
        f"但背包放不下（需要 {slots + 1} 格，只有 {slots} 格）"
    )
    assert dumps_char(full) == before
    # 單手武器不占副手：背包滿也能選
    one_handed = OpeningConfirmAction(weapon="one_handed_sword", keywords=("prone", "ignite"))
    assert _step(library, full, one_handed, world).char.equipment["off_hand"] == shield
    roomy = full.model_copy(update={"bag": {"item_coarse_material": 20 * (slots - 1)}})
    assert _step(library, roomy, action, world).char.gear == (shield,)


# ---------------------------------------------------------------------------
# 關鍵字推薦（#150 第 4 點）
# ---------------------------------------------------------------------------


def _with_uses(char: CharacterState, uses: dict[str, int]) -> CharacterState:
    usage = {k: SkillUsage(uses=n) for k, n in sorted(uses.items())}
    return char.model_copy(update={"skill_usage": usage})


def _exclusive(library: ContentLibrary, skill_id: str) -> tuple[str, ...]:
    """一招的專屬關鍵字：製造的在前、利用的在後。"""
    own = derive_keywords(library.skills[skill_id], library.keywords, exclusive_only=True)
    return tuple(dict.fromkeys((*own.makes, *own.uses)))


@pytest.mark.parametrize("cls", sorted(CHOICES))
def test_recommended_first_keyword_follows_usage(
    library: ContentLibrary, make_char: MakeChar, cls: str
) -> None:
    """第 1 個＝用最多次那招的專屬關鍵字（製造優先）；同次數取前面那招；那招沒有就看另一招；
    兩招都沒有就不推薦。全部從資料推，不寫死招。"""
    char = _starter(library, make_char, cls)
    one, two = range_content(library).demos[cls]  # type: ignore[index]
    weapon = char.hero.weapon
    keys = {s: _exclusive(library, s) for s in (one, two)}
    for uses, order in (
        ({one: 3, two: 1}, (one, two)),
        ({one: 1, two: 3}, (two, one)),
        ({one: 2, two: 2}, (one, two)),
        ({}, (one, two)),
    ):
        got = recommended_keywords(library, _with_uses(char, uses), weapon)
        wanted = next((keys[s][0] for s in order if keys[s]), None)
        if wanted is None:
            assert got == ()
        else:
            assert got and got[0] == wanted, (uses, got)
            assert len(got) <= 2 and len(set(got)) == len(got)


def test_recommended_second_keyword_links_with_first(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    """第 2 個＝照關鍵字表順序，第一個和第 1 個一起選時起始兩招互相觸發的；結果就是正式選定會給的
    那兩招之間有觸發關係。"""
    seen_pair = False
    for cls in sorted(CHOICES):
        char = _starter(library, make_char, cls)
        assert char.opening is not None
        for weapon in ("one_handed_sword", "bow", "fire_staff"):
            got = recommended_keywords(library, char, weapon)
            assert got == recommended_keywords(library, char, weapon)  # 純函式
            if len(got) < 2:
                continue
            seen_pair = True
            first, second = pick_starters(library, weapon, got, char.opening.seed)
            assert links_between(library, first, second)
            order = list(library.keywords.start_ids())
            for earlier in order[: order.index(got[1])]:
                if earlier == got[0]:
                    continue
                pair = pick_starters(library, weapon, (got[0], earlier), char.opening.seed)
                assert not links_between(library, pair[0], pair[1])
    assert seen_pair


def test_recommended_keywords_only_in_starter_stage(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    assert recommended_keywords(library, make_char(), "bow") == ()  # 舊角色
    assert recommended_keywords(library, _pending(library, make_char), "bow") == ()
    starter = _starter(library, make_char, "focus")
    assert recommended_keywords(library, starter, "no_such_weapon") == ()
    assert "bow" in start_weapons(library)
    chosen = _step(library, _fast_played(library, make_char), _confirm("melee"), make_world()).char
    assert recommended_keywords(library, chosen, "bow") == ()  # 入門招已收回


# ---------------------------------------------------------------------------
# 影子：入門期不寫入、選定後寫入
# ---------------------------------------------------------------------------


def test_shadow_saved_only_after_formal_choice(
    library: ContentLibrary, make_char: MakeChar
) -> None:
    world = make_world()
    pending = _pending(library, make_char)
    result = _step(library, pending, OpeningClassAction(weapon_class="melee"), world)
    assert result.world.shadow_of("alice") is None
    played = _fast_played(library, make_char)
    for action in (RestAction(), AllocateAction(attributes={Attribute.CON: 1})):
        char = played
        if isinstance(action, AllocateAction):
            char = _step(library, played, RespecAction(), world).char
        result = _step(library, char, action, world)
        assert result.world.shadow_of("alice") is None
        assert not any(isinstance(e, ShadowSavedEvent) for e in result.events)
    char = _step(library, played, _confirm("melee"), world).char
    for _ in range(2):
        char = _step(library, char, OfferPickAction(), world).char
    result = _step(library, char, RestAction(), world)
    assert any(isinstance(e, ShadowSavedEvent) for e in result.events)
    saved = result.world.shadow_of("alice")
    assert saved is not None and saved.snapshot.hero.weapon == CHOICES["melee"][0]
    # 舊角色照舊
    old = _step(library, make_char("bob"), RestAction(), world)
    assert old.world.shadow_of("bob") is not None


# ---------------------------------------------------------------------------
# 世界日誌重播：選大類 → 打新手第 2 步 → 回鎮 → 正式選定 → 選三選一 → 休息
# ---------------------------------------------------------------------------


def test_full_flow_log_replays_identically(calm: ContentLibrary, make_char: MakeChar) -> None:
    base = _with_quest(_pending(calm, make_char, mercenaries=PARTY), QUEST, steps_done=1)
    start, fight = base, FightAction(steps=())
    for seed in range(MAX_FIGHT_SEEDS):
        start = _fixed_fight(base, STEP_PLACES[1], seed)
        ready = world_step(calm, make_world(), start, OpeningClassAction(weapon_class="focus"), 1)
        fight = FightAction(steps=auto_steps(calm, ready.char))
        fought = world_step(calm, ready.world, ready.char, fight, 2)
        if any(isinstance(e, BattleEndedEvent) and e.won for e in fought.events):
            break
    else:
        pytest.fail("找不到會贏的種子")
    actions: list[WorldAction] = [
        OpeningClassAction(weapon_class="focus"),
        fight,
        TravelAction(to="ferry_steps"),
        TravelAction(to="mist_ferry"),
        RestAction(),  # 入門期：不存影子
        _confirm("focus"),
        OfferPickAction(pick=1),
        RestAction(),  # 選定後：存影子
    ]
    world = make_world()
    char = start
    entries: list[WorldLogEntry] = []
    for index, action in enumerate(actions):
        now = NOON + 60 * (index + 1)
        result = world_step(calm, world, char, action, now)
        char, world = result.char, result.world
        entries.append(WorldLogEntry(seq=index + 1, now=now, character_id="alice", action=action))
        if index == 4:
            assert world.shadow_of("alice") is None
    assert char.opening is not None and char.opening.stage == "chosen"
    assert char.opening.deferred_offers == (DeferredOffer(quest=QUEST, step=1),)
    assert len(char.opening.granted_skills) == 3
    assert char.hero.weapon == CHOICES["focus"][0]
    assert world.shadow_of("alice") is not None
    first = replay(calm, make_world(), {"alice": start}, entries)
    second = replay(calm, make_world(), {"alice": start}, loads_log(dumps_log(entries)))
    assert dumps_char(first.characters["alice"]) == dumps_char(char)
    assert dumps_char(second.characters["alice"]) == dumps_char(char)
    assert dumps_world(first.world) == dumps_world(world) == dumps_world(second.world)
    assert first.events == second.events
