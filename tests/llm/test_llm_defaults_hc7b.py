"""HC-7 b.2：LLM 呼叫設定只留 ``LLMConfig`` 的 schema 預設一份；挑選模式的時間預算在內容。"""

from __future__ import annotations

from pathlib import Path

from trpg.api.llm_source import DEFAULT_ALERT_PERMILLE, DEFAULT_PROBE_TIMEOUT_S
from trpg.content.library import ContentLibrary
from trpg.llm.client import MockLLMClient
from trpg.llm.config import LLM_DEFAULTS, LLMConfig, client_config, load_llm_config
from trpg.llm.flash_propose import DEFAULT_FLASH_ATTEMPTS
from trpg.llm.pick import DEFAULT_PICK_ATTEMPTS
from trpg.llm.propose import DEFAULT_MAX_ATTEMPTS
from trpg.llm.situation import DEFAULT_SITUATION_ATTEMPTS
from trpg.llm.story_skill import DEFAULT_STORY_ATTEMPTS as STORY_SKILL_ATTEMPTS
from trpg.llm.wish import DEFAULT_WISH_ATTEMPTS, wish_max_keywords
from trpg.narrative.storyteller import DEFAULT_STORY_ATTEMPTS

ROOT = Path(__file__).resolve().parents[2]


def test_defaults_equal_the_old_numbers() -> None:
    """搬家前寫死的值：重試 3、情境 2、說書人 2、提醒 200‰、連線檢查 3 秒。"""
    assert (
        LLM_DEFAULTS.max_retries,
        LLM_DEFAULTS.situation_attempts,
        LLM_DEFAULTS.story_attempts,
    ) == (
        3,
        2,
        2,
    )
    assert LLM_DEFAULTS.fallback_alert_permille == DEFAULT_ALERT_PERMILLE == 200
    assert LLM_DEFAULTS.probe_timeout_s == DEFAULT_PROBE_TIMEOUT_S == 3.0
    retries = {
        DEFAULT_FLASH_ATTEMPTS,
        DEFAULT_PICK_ATTEMPTS,
        DEFAULT_MAX_ATTEMPTS,
        STORY_SKILL_ATTEMPTS,
        DEFAULT_WISH_ATTEMPTS,
    }
    assert retries == {LLM_DEFAULTS.max_retries}
    assert LLM_DEFAULTS.situation_attempts == DEFAULT_SITUATION_ATTEMPTS
    assert LLM_DEFAULTS.story_attempts == DEFAULT_STORY_ATTEMPTS


def test_repo_config_keeps_its_values_and_new_keys_default() -> None:
    """``config/llm.toml`` 沒有加鍵：新鍵照 schema 預設。"""
    config = load_llm_config(ROOT / "config" / "llm.toml", env={})
    assert config.probe_timeout_s == LLM_DEFAULTS.probe_timeout_s
    assert config.situation_attempts == LLM_DEFAULTS.situation_attempts
    assert config.story_attempts == LLM_DEFAULTS.story_attempts


def test_client_config_falls_back_to_defaults() -> None:
    assert client_config(MockLLMClient([])) is LLM_DEFAULTS

    class _WithConfig:
        config = LLMConfig(story_attempts=5)

    assert client_config(_WithConfig()).story_attempts == 5


def test_pick_budgets_and_wish_keywords_come_from_content(library: ContentLibrary) -> None:
    budget = library.skill_pick.budget_seconds
    assert (budget.flash, budget.offer, budget.wish) == (10.0, 10.0, 10.0)
    pregen = library.skill_pick.pregen
    assert (pregen.wait_seconds, pregen.story_wait_seconds) == (10.0, 2.0)
    assert (pregen.flash_limit, pregen.story_limit) == (3, 2)
    assert library.world_rules is not None
    assert wish_max_keywords(library) == library.world_rules.wish.max_keywords == 2
