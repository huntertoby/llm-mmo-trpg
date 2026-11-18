"""PK-3（玩法 PM 4.1.23）：組合器不再產生「非傷害效果只在第一輪生效」與「有條件的刻紋」；驗證器照舊
不擋（手寫的每場一次開場招保留）；挑選打分的怪條件扣分留著當保險。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.content.skills import SkillDef
from trpg.shared.rng import Rng
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.skill_pick import ODD_FIRST_ROUND, ODD_INSCRIBE, odd_conditions
from trpg.skillgen.validate import validate_skill

KEYWORDS = (None, "ignite", "wet", "marked", "prone", "frozen", "charged")


def _sample(per: int) -> list[SkillDef]:
    lib = library()
    rng = Rng(4123)
    out: list[SkillDef] = []
    for rarity in ("rare", "epic"):
        for keyword in KEYWORDS:
            for _ in range(per):
                try:
                    out.append(
                        compose_random_skill(
                            rng.next_u32(), tier=1, rarity=rarity, library=lib, keyword=keyword
                        )
                    )
                except ComposeError:
                    continue
    return out


def test_composer_makes_no_odd_conditions() -> None:
    """固定種子抽樣（稀有、史詩，常見關鍵字）：一招都沒有怪條件，但條件本身照樣會出現。"""
    skills = _sample(25)
    assert len(skills) > 200
    assert [s.id for s in skills if odd_conditions(s)] == []
    assert any(s.condition is not None for s in skills)
    assert any(getattr(e, "condition", None) is not None for s in skills for e in s.effects)


def test_validator_still_accepts_handwritten_opening_ambush() -> None:
    """驗證器不改：手寫的「第 1 輪才能用」非傷害招（霧影分身，每場最多一次）照樣合法。"""
    lib = library()
    shade = lib.skills["skill_summon_mist_shade"]
    assert shade.condition is not None and shade.condition.type == "first_round"
    assert not validate_skill(shade, lib)


def test_pick_score_penalty_kept_as_safety_net() -> None:
    """打分的怪條件判定照舊（其他路徑產生時照樣扣分）。"""
    lib = library()
    shade = lib.skills["skill_summon_mist_shade"]
    assert odd_conditions(shade) == (ODD_FIRST_ROUND,)
    rune = next(
        s
        for s in lib.skills.values()
        if any(e.type == "inscribe" for e in s.effects)
        and not any(e.type in ("damage", "delayed_damage") for e in s.effects)
    )
    conditioned = rune.model_copy(update={"condition": shade.condition})
    assert ODD_INSCRIBE in odd_conditions(conditioned)
