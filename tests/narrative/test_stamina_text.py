"""耐力說明文字（Phase 3H-5）：回復點數與戰後回滿都由資料產生，不寫死。"""

from __future__ import annotations

from tests.engine.helpers import library
from trpg.api.run_presenter import resource_rule_text
from trpg.content.rules import CoreRules
from trpg.narrative.action_info import action_texts


def _lines(core: CoreRules, refill: tuple[str, ...] = ()) -> str:
    return "".join(next(t for t in action_texts(core, refill) if t.id == "stamina").lines_zh)


def test_stamina_card_follows_the_regen_and_refill_data() -> None:
    core = library().ruleset.core
    assert "每回合開始回復 5 點" in _lines(core) and "戰鬥之間不回復" in _lines(core)
    assert "每場打贏後回滿" in _lines(core, ("stamina",))
    more = core.model_copy(
        update={"resources": core.resources.model_copy(update={"stamina_regen": 8})}
    )
    assert "每回合開始回復 8 點" in _lines(more)


def test_run_rule_sentence_comes_from_the_data() -> None:
    lib = library()
    text = resource_rule_text(lib, test_mode=False)
    assert "每場打贏後耐力回滿" in text and "耐力每回合開始回復 5 點" in text
    assert "HP、法力不會在戰鬥之間回復" in text
