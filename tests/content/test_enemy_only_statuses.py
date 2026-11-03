"""只給敵人的狀態（Phase 5F-5c；玩法 PM 2026-11-03 代決）。

熔核爆裂、寒燼爆裂（與殼縫熔核）承載荒原敵人的傷害倍率（5F-5b ×2.25／×1.5），不能給玩家、影子、
傭兵，也不能進技能池（生成器、候選、閃現、工坊、LLM 可選清單）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trpg.content.library import ContentLibrary, load_library, skill_reference_problems
from trpg.skillgen.proposal import budget_statuses, rarity_statuses

ENEMY_ONLY = ("frost_ember_burst", "heart_ember_burst", "molten_burst")
CONTENT = Path(__file__).resolve().parents[2] / "content"
PLAYER_SIDE_FILES = (
    "sim/builds.yaml",
    "world/mercenaries.yaml",
    "dev_starters.yaml",
    "races.yaml",
    "origins.yaml",
)
"""玩家這一邊的單位與 build（主角、影子的底稿、傭兵、劇情夥伴、開發用起始角色、種族、出身）。"""


@pytest.fixture(scope="module")
def library() -> ContentLibrary:
    return load_library()


def test_the_burst_statuses_are_enemy_only(library: ContentLibrary) -> None:
    rules = library.ruleset
    assert sorted(rules.enemy_only_statuses()) == list(ENEMY_ONLY)
    for sid in ENEMY_ONLY:
        assert rules.status_def(sid).budget_points is None


def test_enemy_only_statuses_never_reach_a_skill_list(library: ContentLibrary) -> None:
    for rarity in ("common", "rare", "epic", "legendary"):
        assert not set(ENEMY_ONLY) & set(rarity_statuses(library, rarity))
    assert not set(ENEMY_ONLY) & set(budget_statuses(library))


def test_a_skill_that_uses_an_enemy_only_status_is_rejected(library: ContentLibrary) -> None:
    skill = next(
        s
        for s in sorted(library.skills.values(), key=lambda s: s.id)
        if any(e.status is not None for e in s.effects)
    )
    effects = tuple(
        e.model_copy(update={"status": "molten_burst"}) if e.status is not None else e
        for e in skill.effects
    )
    bad = skill.model_copy(update={"effects": effects})
    problems = skill_reference_problems(bad, library.ruleset, library.skills)
    assert any("molten_burst 只給敵人" in p for p in problems)
    assert not skill_reference_problems(skill, library.ruleset, library.skills)


def test_no_content_skill_uses_an_enemy_only_status(library: ContentLibrary) -> None:
    for path in sorted((CONTENT / "skills").rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        assert not [s for s in ENEMY_ONLY if s in text], path


def test_enemy_only_statuses_stay_on_enemy_unit_templates(library: ContentLibrary) -> None:
    """內容裡只有 ``statuses.yaml`` 與敵方單位範本（``units/``）提到它們，那些單位不在玩家這邊。"""
    holders: list[str] = []
    for path in sorted(CONTENT.rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if not any(s in text for s in ENEMY_ONLY):
            continue
        rel = path.relative_to(CONTENT).as_posix()
        if rel == "statuses.yaml":
            continue
        assert rel.startswith("units/"), rel
        holders.append(path.stem)
    assert holders
    for rel in PLAYER_SIDE_FILES:
        text = (CONTENT / rel).read_text(encoding="utf-8")
        assert not [u for u in holders if u in text], rel
    season = library.world_season
    assert season is not None and season.league is not None
    league = (*season.league.opening_statuses, *season.league.first_opening_statuses)
    assert not set(ENEMY_ONLY) & set(league)
