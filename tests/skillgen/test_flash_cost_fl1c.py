"""FL-1c：06 6.34「費用方向」第 5～7 點（FL-1a 後補，玩法 PM 822106148）。

- 第 5 點：輕巧的「少付」以卡片上的實付值為準；法力 ×0.8 四捨五入後實付沒變就不出輕巧，
  不改試別的項目。
- 第 6 點：增益也算「狀態」：暫時給技能（展翼）、只對友方的持續區域（戰歌）的回合可以被蓄力加、
  被輕巧降。
- 第 7 點：沒有任何閃現選項的招，伺服器事先算好（:func:`has_options`），面板不給按。
"""

from __future__ import annotations

import pytest

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.skillgen.flash_cost import _has_rounds, strength_moves
from trpg.skillgen.flash_derive import FlashError, derive_skill
from trpg.skillgen.flash_offer import FlashRequest, has_options, make_offer
from trpg.skillgen.flash_ops import _light_cost_drafts
from trpg.skillgen.flash_state import Variation, acquire, with_flash
from trpg.skillgen.usage import SkillUsage

LIB = library()
SEED = 12345
CHARGE = Variation(source="minor", template="cost_charge", category="cost")
LIGHT = Variation(source="minor", template="cost_light", category="cost")

MANA_ONLY_LIGHT = (
    "skill_flight",
    "skill_hex_bolt",
    "skill_rime_touch",
    "skill_soul_reap",
    "skill_static_palm",
    "skill_wil_cinder_hex",
    "skill_wil_storm_hex",
)
"""FL-1a 報告第 6 節第 2 點：輕巧只減法力、實付沒變的 7 招。"""
STILL_NO_OPTIONS = (
    "skill_afterimage_vow",
    "skill_bloodwake_stride",
    "skill_gust_blow",
    "skill_kindred_flame",
    "skill_mirror_cast",
    "skill_mountain_mover",
    "skill_taunting_roar",
    "skill_wing_spread",
)
"""補完第 5、6 點後仍然沒有任何閃現選項的 1 階主動技（FL-1c 掃描；FL-1e 起輕巧回合每次最多 −1，
展翼的輕巧不出，蓄力本來就不出，變成沒有選項）。"""


def _flash(base: SkillDef, *variations: Variation) -> SkillDef:
    state = acquire(base.id)
    for variation in variations:
        state = with_flash(state, variation)
    return derive_skill(LIB, base, state, SEED, tier=1)


def _request(skill: SkillDef) -> FlashRequest:
    state = acquire(skill.id).model_copy(update={"used": True})
    return FlashRequest(base=skill, state=state, usage=SkillUsage(), seed=SEED, tier=1)


# ---------------------------------------------------------------------------
# 第 5 點：實付值
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", MANA_ONLY_LIGHT)
def test_light_is_not_offered_when_the_paid_mana_stays_the_same(skill_id: str) -> None:
    base = LIB.skills[skill_id]
    core = LIB.ruleset.core
    assert base.ap_cost == 1
    mana = base.cost.mana
    assert core.mana_cost(mana - 1) == core.mana_cost(mana)  # 例：3 → 2 實付都是 2
    with pytest.raises(FlashError):
        _flash(base, LIGHT)


def test_unchanged_paid_mana_stops_instead_of_trying_the_next_field() -> None:
    """法力減 1 實付不變時不出草稿，也不改試後面的耐力（「不改試別的項目」）。"""
    base = LIB.skills["skill_rime_touch"]
    both = base.model_copy(update={"cost": base.cost.model_copy(update={"stamina": 3})})
    assert _light_cost_drafts(both, ("mana", "stamina"), LIB) == []
    # 實付會變的法力照舊出草稿
    big = base.model_copy(update={"cost": base.cost.model_copy(update={"mana": 6})})
    drafts = _light_cost_drafts(big, ("mana",), LIB)
    assert [d[0]["cost"]["mana"] for d in drafts] == [5]


# ---------------------------------------------------------------------------
# 第 6 點：增益也算狀態
# ---------------------------------------------------------------------------


def test_war_hymn_charge_lengthens_the_aura() -> None:
    base = LIB.skills["skill_war_hymn"]
    charged = _flash(base, CHARGE)
    assert base.effects[0].duration == 3
    assert charged.effects[0].duration == 4
    assert charged.cost.cooldown == 5
    assert strength_moves(base, charged) == (True, False)


@pytest.mark.parametrize("skill_id", ["skill_wing_spread", "skill_wing_gift"])
def test_wing_light_is_not_offered(skill_id: str) -> None:
    """FL-1c 時飛行回合 3 → 1；FL-1e 起每次最多 −1，飛行 2 回合比例仍高於合格區間，不出輕巧。"""
    with pytest.raises(FlashError):
        _flash(LIB.skills[skill_id], LIGHT)


def test_enemy_zone_rounds_are_not_a_buff() -> None:
    """只有對友方的區域算增益；火牆（對敵方）的區域回合不在蓄力、輕巧的退路裡。"""
    fire_wall = LIB.skills["skill_fire_wall"].effects[0].model_dump(mode="json", exclude_none=True)
    hymn = LIB.skills["skill_war_hymn"].effects[0].model_dump(mode="json", exclude_none=True)
    assert not _has_rounds(fire_wall)
    assert _has_rounds(hymn)


# ---------------------------------------------------------------------------
# 第 7 點：事先判斷有沒有選項
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("skill_id", STILL_NO_OPTIONS)
def test_skills_without_any_option_are_known_in_advance(skill_id: str) -> None:
    request = _request(LIB.skills[skill_id])
    assert not has_options(LIB, request)
    assert make_offer(LIB, request).options == ()


@pytest.mark.parametrize(
    "skill_id", ["skill_war_hymn", "skill_wing_gift", "skill_rime_touch", "skill_flight"]
)
def test_skills_with_options_are_known_in_advance(skill_id: str) -> None:
    request = _request(LIB.skills[skill_id])
    assert has_options(LIB, request)
    assert make_offer(LIB, request).options


def test_the_answer_is_cached_on_the_library() -> None:
    request = _request(LIB.skills["skill_afterimage_vow"])
    has_options(LIB, request)
    assert False in LIB.flash_option_cache.values()


@pytest.mark.slow
def test_scan_has_options_matches_the_offer() -> None:
    """1 階主動技（內容檔）第 1 次閃現：事先判斷與實際出題一致；沒有選項的正好是上面那幾招。"""
    skills = sorted(
        (s for s in LIB.skills.values() if s.tier == 1 and s.kind == "active" and not s.enemy_only),
        key=lambda s: s.id,
    )
    none: list[str] = []
    for skill in skills:
        request = _request(skill)
        found = has_options(LIB, request)
        assert found == bool(make_offer(LIB, request).options), skill.id
        if not found:
            none.append(skill.id)
    assert tuple(none) == STILL_NO_OPTIONS
