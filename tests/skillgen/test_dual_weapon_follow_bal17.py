"""BAL-17：雙屬性武器的「跟主屬性」與候選偏離數。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.roguelite import new_keyword_run
from trpg.roguelite.offers import make_offer
from trpg.shared.types import Attribute as A
from trpg.skillgen.candidates import follows_attr

LIB = library()
ARCANE = (A.STR, A.INT)


def test_dual_weapon_makes_spells_of_either_weapon_attribute_follow() -> None:
    fire = LIB.skills["skill_fire_bolt"]  # 法術，智力
    assert fire.scaling_attr is A.INT
    assert follows_attr(fire, A.STR, ARCANE)  # 力量最高：智力法術也算同路線
    assert follows_attr(fire, A.INT, ARCANE)
    assert not follows_attr(fire, A.STR, ())  # 沒有武器資訊：照技能自己的


def test_dual_weapon_does_not_cover_other_attributes() -> None:
    soul = next(
        s
        for s in LIB.skills.values()
        if s.category != "weapon" and s.scaling_attr is A.WIL and s.secondary_scaling_attr is None
    )
    assert not follows_attr(soul, A.STR, ARCANE)  # 意志法術仍偏離
    assert not follows_attr(soul, A.INT, ARCANE)
    assert follows_attr(soul, A.WIL, ARCANE)  # 最高屬性不在武器裡：維持原本的判定


def test_single_attribute_weapon_is_unchanged() -> None:
    fire = LIB.skills["skill_fire_bolt"]
    sword = (A.STR,)
    assert not follows_attr(fire, A.STR, sword)
    assert follows_attr(fire, A.INT, sword)


def test_arcane_blade_start_has_at_most_two_off_route_candidates() -> None:
    """魔導劍（力量 14）開局的第一次與第二次升級三選一：偏離的不超過 2 張，平均接近 1。"""
    counts: list[int] = []
    for seed in range(12):
        run = new_keyword_run(LIB, "arcane_blade", ("charged", "concealed"), seed, {A.STR: 4})
        for made in range(2):
            offer = make_offer(LIB, run.model_copy(update={"offers_made": made}), "level_up")
            counts.append(len(offer.off_route))
    assert max(counts) <= 2
    assert sum(counts) / len(counts) <= 1.5
