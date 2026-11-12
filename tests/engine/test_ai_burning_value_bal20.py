"""BAL-20：AI 估值表補燃燒（``status_values.burning``）後，T1 餘燼啃咬的分數高於同目標普攻。

T1 的 ``skill_ember_bite`` 和 ``fangs`` 普攻同傷害（1000‰），只多一個燃燒；燃燒沒列在估值表時，
莽夫（``status`` 權重 0）給它 0 分，啃咬就比普攻少了技能代價（耐力 10 × 500‰ ＋ 冷卻 1 ＝ 6 分）。
這裡實際跑 ``score_action``（``engine/ai/utility/scoring.py``），燃燒的價值一律從內容檔讀，不寫死。
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

import yaml

from tests.engine.helpers import (
    PROJECT_ROOT,
    give_turn,
    library,
    make_map,
    make_state,
    no_reactions,
    spawn,
    template,
)
from tests.engine.skill_helpers import FLAT7, U1, U2
from trpg.content.environment import AiProfile
from trpg.engine import Attack, UseSkill, legal_actions
from trpg.engine.ai.utility import UtilityAI, score_action
from trpg.engine.state import BattleState
from trpg.shared.types import Team

BITE = "skill_ember_bite"


def _content_burning() -> Any:
    raw = yaml.safe_load((PROJECT_ROOT / "content" / "ai_profiles.yaml").read_text("utf-8"))
    return raw["status_values"].get("burning")


def _lizard_next_to_hero() -> BattleState:
    """U1 是我方戰士 (1, 3)（HP 夠多、一擊打不倒），U2 是緊貼著的 T1 餘燼蜥；輪到 U2。"""
    m = make_map(FLAT7, ally=[(1, 3)], enemy=[(2, 3)])
    spawns = [
        spawn(Team.ALLY, (1, 3), no_reactions("hero_fighter", max_hp=200)),
        spawn(Team.ENEMY, (2, 3), template("ember_lizard", reactions=[])),
    ]
    return give_turn(make_state(m, spawns), U2)


def _profile(state: BattleState) -> AiProfile:
    return UtilityAI(library().ai_profiles).profile_for(state.units[U2])


def _scores(state: BattleState, profile: AiProfile) -> tuple[Fraction, Fraction]:
    bite = UseSkill(unit_id=U2, skill_id=BITE, target_id=U1)
    attack = Attack(unit_id=U2, target_id=U1)
    legal = legal_actions(state)
    assert bite in legal
    assert attack in legal
    return score_action(state, bite, profile).score, score_action(state, attack, profile).score


def test_the_table_reads_burning_from_the_content_file() -> None:
    value = _content_burning()
    assert isinstance(value, int)
    assert value > 0
    assert library().ai_profiles.status_values["burning"] == value
    # 每個行為模式都拿到同一張表（環境的 status_values 由表層級填入）
    for p in library().ai_profiles.profiles:
        assert p.status_values.get("burning") == value, p.id


def test_t1_ember_bite_outscores_a_plain_attack_on_the_same_target() -> None:
    state = _lizard_next_to_hero()
    assert state.units[U2].ai_profile == "brute"
    assert BITE in state.units[U2].all_skills  # 範本的招是 T1（沒有 _t2 後綴）
    profile = _profile(state)
    assert profile.weights.status == 0  # 莽夫：沒列在估值表的狀態值 0 分
    bite, attack = _scores(state, profile)
    assert bite > attack


def test_without_the_burning_entry_the_bite_loses_by_its_cost() -> None:
    """對照組：拿掉 ``burning`` 就回到 BAL-20 前的情況——啃咬比同目標普攻低，差距就是技能代價。"""
    state = _lizard_next_to_hero()
    profile = _profile(state)
    values = {k: v for k, v in profile.status_values.items() if k != "burning"}
    bare = profile.model_copy(update={"status_values": values})
    bite, attack = _scores(state, bare)
    w = profile.weights
    skill = library().ruleset.skill_def(BITE)
    cost = (
        Fraction(skill.cost.stamina * w.stamina_permille, 1000)
        + (skill.cost.cooldown or 0) * w.cooldown
    )
    assert cost > 0
    assert attack - bite == cost
