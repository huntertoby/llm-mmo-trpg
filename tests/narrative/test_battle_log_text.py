"""戰鬥紀錄的數字加得起來（Phase 3-41b，清單 10.1～10.4）：傷害事件帶著組成（骰、屬性加成、固定值、
倍率），重組出來的數字等於實際傷害；紀錄文字把組成與判定寫清楚。"""

from __future__ import annotations

import pytest

from tests.engine.helpers import DEMO_ALLIES, DEMO_ENEMIES, library
from trpg.engine import build_setup
from trpg.engine.events import AttackRolled, DamageDealt, StatusSaveRolled
from trpg.engine.runner import run_battle
from trpg.narrative.events import describe_event

_PERMILLE = 1000
_PPM = 1_000_000


def _damage_from_parts(e: DamageDealt) -> int:
    raw = (sum(e.rolls) + e.flat) * _PERMILLE + e.scaled_permille
    scaled = (
        raw
        * e.element_mod_ppm
        * e.weather_permille
        * e.multiplier_permille
        * e.status_ppm
        // (_PERMILLE * _PPM * _PERMILLE * _PERMILLE * _PPM)
    )
    return max(scaled, 1)


@pytest.mark.parametrize("seed", [0, 3, 7])
def test_logged_damage_parts_add_up(seed: int) -> None:
    setup = build_setup(library(), "test_heights_8x8", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    run = run_battle(setup, seed)
    damages = [
        e for e in run.events if isinstance(e, DamageDealt) and e.cause == "attack" and e.rolls
    ]
    assert damages
    for e in damages:
        assert e.amount == _damage_from_parts(e), e
        assert e.block_permille <= _PERMILLE  # 格擋只會減傷，且已包含在 multiplier 裡


def test_text_names_every_part() -> None:
    setup = build_setup(library(), "test_heights_8x8", DEMO_ALLIES, DEMO_ENEMIES, max_rounds=30)
    run = run_battle(setup, 0)
    state = run.state
    texts = [describe_event(e, state) for e in run.events]
    joined = "\n".join(t for t in texts if t)
    assert "加成" in joined and "［骰 " in joined
    assert "（目標 " not in joined and "格擋/加成" not in joined
    for e in run.events:
        if isinstance(e, AttackRolled):
            text = describe_event(e, state) or ""
            assert "攻防修正" in text and "需 ≥ 11" in text
        if isinstance(e, StatusSaveRolled):
            text = describe_event(e, state) or ""
            assert "攻防修正" in text and "需 ≥ 11" in text
