"""候選產生器的區域偏向、白板組成與被動保底（Phase 5B-4b；Phase5計畫 19.4、19.5）。

- 區域偏向：「新方向」優先挑玩家還沒有的區域關鍵字；玩家全部都有或沒傳時照原樣。
- 組成：新手鏈 加深／橋接／新方向 1／0／2（07 7.6）。
- 被動保底：至少 ``min_passive`` 張被動。
- 預設輸入＝原候選逐字相同（原型 roguelite 不變）。
"""

from __future__ import annotations

from dataclasses import replace

from tests.engine.helpers import library
from trpg.skillgen.candidates import CandidateRequest, generate_candidates, region_first
from trpg.skillgen.whiteboard_candidates import generate_whiteboard_candidates

LIB = library()
REGION = ("wet", "charged", "concealed")
HELD = {"ignite": 2, "marked": 1}
SEEDS = range(40)


def _request(counts: dict[str, int], seed: int, **extra: object) -> CandidateRequest:
    base = CandidateRequest(keyword_counts=counts, weapon_class="melee", seed=seed, tier=1)
    return replace(base, **extra)  # type: ignore[arg-type]


def _new_keywords(found: tuple[object, ...]) -> list[str]:
    out: list[str] = []
    for c in found:
        if getattr(c, "kind", None) == "new":
            out += list(c.keywords)  # type: ignore[attr-defined]
    return out


def test_region_first_orders_region_keywords_first() -> None:
    assert region_first(["a", "b", "c", "d"], ("c", "a")) == ["a", "c", "b", "d"]
    assert region_first(["a", "b"], ()) == ["a", "b"]


def test_default_inputs_keep_the_original_candidates() -> None:
    """新欄位都是預設值時，白板與完整版產生器的候選與原本逐字相同（同一個請求物件建兩次）。"""
    for seed in range(10):
        plain = CandidateRequest(keyword_counts=HELD, weapon_class="melee", seed=seed, tier=1)
        same = _request(HELD, seed, region_keywords=(), mix=(1, 1, 1), min_passive=0)
        assert generate_whiteboard_candidates(LIB, plain) == generate_whiteboard_candidates(
            LIB, same
        )
        assert generate_candidates(LIB, plain) == generate_candidates(LIB, same)


def test_whiteboard_new_direction_prefers_unheld_region_keywords() -> None:
    biased = 0
    plain = 0
    total = 0
    for seed in SEEDS:
        found = generate_whiteboard_candidates(LIB, _request(HELD, seed, region_keywords=REGION))
        keywords = _new_keywords(found)
        if not keywords:
            continue  # 通用池白板（#55）照舊
        total += 1
        biased += keywords[0] in REGION
        base = _new_keywords(generate_whiteboard_candidates(LIB, _request(HELD, seed)))
        plain += bool(base) and base[0] in REGION
    assert total >= 30
    assert biased == total
    assert plain < total  # 沒有偏向時不一定挑區域關鍵字


def test_region_bias_ignored_when_all_region_keywords_are_held() -> None:
    counts = {"wet": 1, "charged": 1, "concealed": 1}
    for seed in range(10):
        biased = generate_whiteboard_candidates(LIB, _request(counts, seed, region_keywords=REGION))
        assert biased == generate_whiteboard_candidates(LIB, _request(counts, seed))


def test_complete_generator_also_biases_new_direction() -> None:
    hits = 0
    total = 0
    for seed in range(20):
        found = generate_candidates(LIB, _request(HELD, seed, region_keywords=REGION))
        keywords = _new_keywords(found)
        if not keywords:
            continue
        total += 1
        hits += keywords[0] in REGION
    assert total >= 10
    assert hits == total


def test_starter_mix_is_one_deepen_two_new() -> None:
    for seed in SEEDS:
        found = generate_whiteboard_candidates(LIB, _request(HELD, seed, mix=(1, 0, 2)))
        assert [c.kind for c in found] == ["deepen", "new", "new"]
        keyed = [c.keywords for c in found if c.keywords]
        assert len(set(keyed)) == len(keyed)  # 兩張新方向不同關鍵字
        assert len({c.skill.id for c in found}) == 3


def test_min_passive_guarantees_a_passive_candidate() -> None:
    without = 0
    for seed in SEEDS:
        request = _request(HELD, seed, mix=(1, 0, 2), min_passive=1)
        found = generate_whiteboard_candidates(LIB, request)
        assert len(found) == 3
        assert any(c.skill.kind == "passive" for c in found), seed
        assert found == generate_whiteboard_candidates(LIB, request)  # 確定性
        plain = generate_whiteboard_candidates(LIB, _request(HELD, seed, mix=(1, 0, 2)))
        without += not any(c.skill.kind == "passive" for c in plain)
    assert without > 0  # 沒有保底時本來會有一組沒被動


def test_min_passive_keeps_candidates_with_enough_passives() -> None:
    for seed in SEEDS:
        plain = generate_whiteboard_candidates(LIB, _request(HELD, seed, mix=(1, 0, 2)))
        if any(c.skill.kind == "passive" for c in plain):
            guarded = _request(HELD, seed, mix=(1, 0, 2), min_passive=1)
            assert generate_whiteboard_candidates(LIB, guarded) == plain
