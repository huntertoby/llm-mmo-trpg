"""Phase 4-L8b：候選產生器的 LLM 題目也出反應技題（比例在 ``roguelite.yaml``）。

不需要網路與模型。"""

from __future__ import annotations

from functools import cache

from tests.engine.helpers import library
from trpg.content.library import ContentLibrary
from trpg.llm.candidate_source import mock_proposer
from trpg.skillgen.proposal_subset import select_subset
from trpg.skillgen.proposal_topic import TopicRequest, make_topic


@cache
def _lib() -> ContentLibrary:
    return library()


def _kinds(permille: int, keywords: tuple[str, ...] = (), seeds: int = 80) -> list[str]:
    out: list[str] = []
    for seed in range(seeds):
        made = make_topic(_lib(), TopicRequest(1, keywords, seed, {}, reaction_permille=permille))
        assert made is not None
        request = made[0]
        out.append(select_subset(_lib(), request).kind)  # 一定出得了子集
    return out


def test_ratio_lives_in_content() -> None:
    assert _lib().roguelite.candidates.llm_reaction_permille == 100


def test_zero_means_never_reaction_and_matches_old_topics() -> None:
    assert "reaction" not in _kinds(0)
    for seed in range(20):
        old = make_topic(_lib(), TopicRequest(1, (), seed, {}))
        assert old == make_topic(_lib(), TopicRequest(1, (), seed, {}, reaction_permille=0))


def test_all_reaction_when_permille_is_full() -> None:
    kinds = _kinds(1000)
    assert set(kinds) == {"reaction"}


def test_mixed_ratio_is_roughly_the_setting() -> None:
    kinds = _kinds(300, seeds=200)
    share = kinds.count("reaction") / len(kinds)
    assert 0.15 < share < 0.45, share


def test_topic_is_deterministic() -> None:
    topic = TopicRequest(1, (), 5, {}, reaction_permille=500)
    assert make_topic(_lib(), topic) == make_topic(_lib(), topic)


def test_falls_back_to_active_when_no_reaction_topic_exists() -> None:
    """題目關鍵字沒有可用的反應骨架時改出主動技能題（不回 None）。"""
    for keyword in _lib().keywords.ids():
        keywords = (keyword,)
        if not _lib().keywords.by_id()[keyword].composable:
            continue
        made = make_topic(_lib(), TopicRequest(1, keywords, 3, {}, reaction_permille=1000))
        if made is not None:
            assert select_subset(_lib(), made[0]).kind in ("active", "reaction")


def test_mock_proposer_answers_reaction_topics() -> None:
    propose = mock_proposer(_lib())
    kinds = []
    for seed in range(12):
        made = make_topic(_lib(), TopicRequest(1, (), seed, {}, reaction_permille=1000))
        assert made is not None
        request, ctx, topic_seed = made
        attempt = propose(request, ctx, topic_seed)
        if attempt.skill is not None:
            kinds.append(attempt.skill.kind)
    assert kinds
    assert set(kinds) == {"reaction"}
