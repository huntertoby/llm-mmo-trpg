"""TF-1（#159，06 6.34.5）：召喚技、輔助技的 1 階轉型——伴生、護主、庇佑、援手。

- 資料：四個模板、大標（玩法 PM 定）。
- 出題：召喚技、輔助技第 3 次閃現有轉型選項；種子在做得出來的種類間挑。
- 套用：轉出來的技能通過驗證器與預算，結構照設計。
- 既有能轉的招（帶敵對效果）轉型種類清單不變。
- 實戰：伴生開場召出、援手作用在友方。
"""

from __future__ import annotations

from collections import Counter

import pytest

from tests.engine.helpers import (
    caster_template,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
)
from tests.engine.skill_helpers import FLAT7, U1
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.shared.types import Team
from trpg.skillgen.flash_category import is_support_skill
from trpg.skillgen.flash_derive import FlashError, derive_skill
from trpg.skillgen.flash_major import transform_variations
from trpg.skillgen.flash_offer import FlashRequest, make_offer
from trpg.skillgen.flash_state import FlashRecord, SkillFlash, Variation
from trpg.skillgen.summon_evolution import is_summon_skill
from trpg.skillgen.usage import SkillUsage
from trpg.skillgen.validate import validate_skill

COMPANION = "to_passive_companion"
GUARDIAN = "to_reaction_guardian"
BLESSING = "to_passive_blessing"
AID = "to_reaction_aid"
NEW = (COMPANION, GUARDIAN, BLESSING, AID)
OLD = ("to_passive_on_hit", "to_reaction_melee", "to_summon", "to_trap", "to_stance")
WOLF_SKILL = "skill_summon_war_wolf"
SKELETON_SKILL = "skill_raise_skeleton"
HEAL_SKILL = "skill_radiant_mend"
SHIELD_SKILL = "skill_guardian_aegis"
MINOR = Variation(source="minor", template="range_plus", category="area")


def _transform(template: str) -> Variation:
    return Variation(source="transform", template=template, category="transform")


def _derived(base_id: str, template: str, seed: int = 11) -> SkillDef:
    lib = library()
    state = SkillFlash(
        base_id=base_id,
        records=(FlashRecord(nth=3, variation=_transform(template)),),
        used=True,
    )
    return derive_skill(lib, lib.skills[base_id], state, seed)


def _summons() -> list[SkillDef]:
    lib = library()
    return [
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active" and is_summon_skill(s)
    ]


def _supports() -> list[SkillDef]:
    lib = library()
    return [
        s
        for s in sorted(lib.skills.values(), key=lambda s: s.id)
        if s.kind == "active" and is_support_skill(s, lib.flash) and not is_summon_skill(s)
    ]


# ---------------------------------------------------------------------------
# 資料
# ---------------------------------------------------------------------------


def test_the_four_tier_one_transforms_and_their_headlines() -> None:
    table = library().flash
    found = {t.id: t for t in table.transforms}
    assert {i: (found[i].source, found[i].to, found[i].min_tier) for i in NEW} == {
        COMPANION: ("summon", "passive", 1),
        GUARDIAN: ("summon", "reaction", 1),
        BLESSING: ("support", "passive", 1),
        AID: ("support", "reaction", 1),
    }
    assert {i: found[i].headline_zh for i in NEW} == {
        COMPANION: "變成被動：每場開打時身邊就跟著一隻",
        GUARDIAN: "變成反應：被近戰攻擊時召出一隻替你反咬",
        BLESSING: "變成被動：每回合開始照顧身邊最虛弱的隊友",
        AID: "變成反應：身邊隊友被盯上時自動幫他",
    }
    assert all(found[i].say_zh for i in NEW)
    # 新模板排在既有模板之後（既有能轉的招的種子挑法不變）
    ids = [t.id for t in table.transforms]
    assert max(ids.index(i) for i in OLD) < min(ids.index(i) for i in NEW)


# ---------------------------------------------------------------------------
# 候選與出題
# ---------------------------------------------------------------------------


def test_hostile_skills_keep_their_transform_list() -> None:
    lib = library()
    fire = lib.skills["skill_fire_bolt"]
    for tier in (1, 2, 3):
        got = transform_variations(lib, fire, tier=tier, rng=Rng(5))
        assert not {v.template for v in got} & set(NEW)


@pytest.mark.parametrize("tier", [1, 2])
def test_summon_skills_can_become_companion_or_guardian(tier: int) -> None:
    lib = library()
    wolf = lib.skills[WOLF_SKILL]
    got = [v.template for v in transform_variations(lib, wolf, tier=tier, rng=Rng(3))]
    assert COMPANION in got and GUARDIAN in got
    assert "to_passive_on_hit" not in got and "to_reaction_melee" not in got  # 做不出來的先拿掉


def test_support_skills_can_become_blessing_or_aid() -> None:
    lib = library()
    mend = lib.skills[HEAL_SKILL]
    got = [v.template for v in transform_variations(lib, mend, tier=1, rng=Rng(3))]
    assert set(got) == {BLESSING, AID}


def _legal(skill: SkillDef, tier: int) -> list[str]:
    """這招在角色階級 ``tier`` 做得出來的新轉型（直接套用第 3 次，不經前兩次小變化）。"""
    lib = library()
    out = []
    for v in transform_variations(lib, skill, tier=tier, rng=Rng(1)):
        if v.template not in NEW:
            continue
        try:
            _derived(skill.id, v.template)
        except FlashError:
            continue
        out.append(v.template)
    return out


def test_most_summon_and_support_skills_get_a_tier_one_transform() -> None:
    """1 階角色（被動、反應）：召喚技、輔助技大多有合法的新轉型；四種都出現得了。沒有的
    （預算窗外）列在報告的平衡疑慮。"""
    seen: Counter[str] = Counter()
    summons = [s for s in _summons() if _legal(s, 1)]
    supports = [s for s in _supports() if _legal(s, 1)]
    for skill in [*_summons(), *_supports()]:
        seen.update(_legal(skill, 1))
    assert set(seen) >= set(NEW), seen
    assert len(summons) * 2 >= len(_summons())
    assert len(supports) * 3 >= len(_supports())


def test_third_flash_offer_includes_the_new_transform() -> None:
    lib = library()
    picked: set[str] = set()
    for base in ("skill_sum_war_howl", "skill_raise_skeleton", HEAL_SKILL):
        skill = lib.skills[base]
        for seed in range(1, 9):
            state = SkillFlash(
                base_id=base,
                records=(FlashRecord(nth=1, variation=MINOR), FlashRecord(nth=2, variation=MINOR)),
                used=True,
            )
            offer = make_offer(lib, FlashRequest(skill, state, SkillUsage(), seed, tier=1))
            found = [
                o.variation.template for o in offer.options if o.variation.source == "transform"
            ]
            assert len(found) == 1, (base, seed)
            picked.update(found)
    assert picked <= set(NEW)
    assert len(picked) >= 3  # 種子在做得出來的種類間挑


# ---------------------------------------------------------------------------
# 套用後的結構
# ---------------------------------------------------------------------------


def test_companion_is_a_battle_start_passive_that_summons_beside_you() -> None:
    lib = library()
    done = _derived(WOLF_SKILL, COMPANION)
    assert validate_skill(done, lib) == []
    assert done.kind == "passive" and done.trigger is not None
    assert done.trigger.event == "on_battle_start"
    (effect,) = done.effects
    assert effect.type == "summon_beside" and effect.unit == "summon_war_wolf"
    assert effect.duration == lib.budget.flash_transform.companion_duration
    assert effect.power_permille is not None and effect.power_permille < 1000  # 縮小版
    assert done.name_zh.startswith("伴生")


def test_guardian_is_a_melee_reaction_that_bites_back() -> None:
    lib = library()
    done = _derived(SKELETON_SKILL, GUARDIAN)
    assert validate_skill(done, lib) == []
    assert done.reaction is not None and done.reaction.event == "hit_by_melee"
    (effect,) = done.effects
    assert effect.type == "summon_beside" and effect.strike_other
    assert effect.duration == lib.budget.flash_transform.guardian_duration == 1


@pytest.mark.parametrize(
    ("base", "event"), [(HEAL_SKILL, "ally_hit_near"), (SHIELD_SKILL, "ally_targeted")]
)
def test_aid_shields_before_and_heals_after_the_hit(base: str, event: str) -> None:
    lib = library()
    done = _derived(base, AID)
    assert validate_skill(done, lib) == []
    assert done.reaction is not None
    assert (done.reaction.event, done.reaction.aid) == (event, True)
    assert all(e.affects == "allies" for e in done.effects)


def test_blessing_targets_the_weakest_ally_within_one_tile() -> None:
    lib = library()
    done = _derived(HEAL_SKILL, BLESSING)
    assert validate_skill(done, lib) == []
    assert done.trigger is not None
    assert (done.trigger.event, done.trigger.target, done.trigger.max_distance) == (
        "on_turn_start",
        "weakest_ally",
        1,
    )
    (heal,) = done.effects
    assert heal.type == "heal" and heal.affects == "allies"


# ---------------------------------------------------------------------------
# 實戰
# ---------------------------------------------------------------------------


def test_a_derived_companion_summons_at_the_start_of_a_battle() -> None:
    done = _derived(WOLF_SKILL, COMPANION)
    m = make_map(FLAT7, ally=[(3, 3)], enemy=[(6, 6)])
    hero = caster_template([done.id], base="hero_mage", max_hp=60)
    spawns = [spawn(Team.ALLY, (3, 3), hero), spawn(Team.ENEMY, (6, 6), no_reactions(max_hp=99))]
    state = make_state(m, spawns, skills=[done])
    pets = [u for u in state.units_sorted() if u.owner_id == U1]
    assert [p.template_id for p in pets] == ["summon_war_wolf"]
