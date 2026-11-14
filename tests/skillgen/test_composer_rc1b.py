"""RC-1b（``docs/玩法PM交接.md`` 4.1.20）：伴生、護主的關鍵字推導、目標型條件只配作用在另一方的
被動、知道種類的呼叫端把種類傳給組合器。"""

from __future__ import annotations

import pytest

from trpg.content.skills import CASTER_CONDITIONS, SkillRarity
from trpg.skillgen.candidates import composer_kinds
from trpg.skillgen.composer_recipes import beside_keywords, unit_keywords
from trpg.skillgen.keywords import derive_keywords, has_keyword
from trpg.skillgen.random_composer import ComposeError, compose_with_stats, default_library

SEEDS = range(24)
TARGET_CONDITIONS = frozenset(
    {"height_advantage", "target_has_status", "target_on_surface", "target_prone"}
)


# ---------------------------------------------------------------------------
# 第 1 點：召喚到身邊的推導鏡像召喚
# ---------------------------------------------------------------------------


def test_summon_beside_mirrors_summon_keywords() -> None:
    """每個在推導表出現的召喚物：``summon_beside`` 推出的關鍵字和 ``summon`` 完全一樣。"""
    lib = default_library()
    units = sorted(
        {r.unit for k in lib.keywords.keywords for r in k.makes if r.effect == "summon" and r.unit}
    )
    assert units
    for unit in units:
        assert unit_keywords(lib, unit, "summon_beside") == unit_keywords(lib, unit), unit
        assert "summon" in unit_keywords(lib, unit, "summon_beside")


def test_companion_card_makes_summon() -> None:
    """伴生、護主（TF-1 轉型同樣的寫法）推得出「製造：召喚物」與召喚物的固有關鍵字。"""
    lib = default_library()
    skill = compose_with_stats(
        0, tier=2, rarity="epic", skeleton="passive", keyword="summon", library=lib
    ).skill
    effect = skill.effects[0]
    assert effect.type == "summon_beside"
    found = derive_keywords(skill, lib.keywords, exclusive_only=True)
    assert "summon" in found.makes
    assert set(unit_keywords(lib, str(effect.unit), "summon_beside")) <= set(found.makes)


@pytest.mark.parametrize("keyword", ["ignite", "wet", "marked", "high_ground"])
def test_companion_reaches_unit_keywords(keyword: str) -> None:
    """召喚物的固有關鍵字（例：火靈＝點燃）也帶得到：被動、反應的配方清單列得到它。"""
    lib = default_library()
    assert keyword in beside_keywords(lib, 2)


# ---------------------------------------------------------------------------
# 第 3 點：目標型條件只配效果作用在另一方的被動
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", ["high_ground", "prone", "marked", "wet"])
@pytest.mark.parametrize("tier", [1, 3])
def test_self_passives_never_get_target_conditions(keyword: str, tier: int) -> None:
    """效果作用在自己（``trigger.target: self``）的被動不會抽到目標型條件（居高臨下、目標倒地、
    目標被標記、目標站在水裡）；高處只用 ``self_on_high_ground``。"""
    lib = default_library()
    seen_self = 0
    for seed in SEEDS:
        skill = compose_with_stats(
            seed, tier=tier, rarity="epic", skeleton="passive", keyword=keyword, library=lib
        ).skill
        assert skill.trigger is not None
        condition = skill.condition
        if condition is None:
            continue
        is_target = condition.type not in CASTER_CONDITIONS
        if condition.type in TARGET_CONDITIONS:
            assert is_target, condition.type
        if skill.trigger.target == "self":
            seen_self += 1
            assert not is_target, (seed, condition.type)
        if condition.type == "height_advantage":
            assert skill.trigger.target == "other"
    if keyword == "high_ground":
        assert seen_self  # 高處被動作用在自己的確實出現（只用 self_on_high_ground）


# ---------------------------------------------------------------------------
# 第 4 點：知道種類的呼叫端把種類傳給組合器
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("keyword", ["marked", "ignite", "summon", "high_ground", "fury"])
def test_active_kind_never_returns_passive_or_reaction(keyword: str) -> None:
    lib = default_library()
    for seed in SEEDS:
        skill = compose_with_stats(
            seed, tier=1, rarity="epic", keyword=keyword, library=lib, kinds=("active",)
        ).skill
        assert skill.kind == "active", seed
        assert has_keyword(skill, keyword, lib.keywords, exclusive_only=True)


@pytest.mark.parametrize(("kind", "rarity"), [("passive", "epic"), ("reaction", "rare")])
def test_kind_picks_the_same_named_skeleton(kind: str, rarity: SkillRarity) -> None:
    lib = default_library()
    for seed in range(8):
        skill = compose_with_stats(
            seed, tier=2, rarity=rarity, keyword="marked", library=lib, kinds=(kind,)
        ).skill
        assert skill.kind == kind


def test_kind_is_same_as_explicit_skeleton() -> None:
    """只有一種、不是主動的種類＝同名骨架：結果和明確傳骨架逐字相同。"""
    lib = default_library()
    for seed in range(8):
        by_kind = compose_with_stats(seed, tier=2, rarity="epic", library=lib, kinds=("passive",))
        by_skeleton = compose_with_stats(
            seed, tier=2, rarity="epic", skeleton="passive", library=lib
        )
        assert by_kind.skill == by_skeleton.skill


def test_no_kind_is_unchanged() -> None:
    """不傳種類＝原行為（和明確傳 ``None`` 相同）。"""
    lib = default_library()
    for seed in range(8):
        a = compose_with_stats(seed, tier=2, keyword="marked", library=lib).skill
        b = compose_with_stats(seed, tier=2, keyword="marked", library=lib, kinds=None).skill
        assert a == b


def test_plain_compose_rejects_other_kinds() -> None:
    """不指定關鍵字時，結果種類不在指定種類內就丟 ``ComposeError``（例：傳說）。"""
    lib = default_library()
    with pytest.raises(ComposeError):
        compose_with_stats(0, tier=2, rarity="legendary", library=lib, kinds=("reaction",))


def test_three_choice_kind_ratio() -> None:
    """三選一的組合器候選照 70／20／10 擲種類（獨立串流，同種子同結果）。"""
    lib = default_library()
    counts = {"active": 0, "passive": 0, "reaction": 0}
    for seed in range(2000):
        kinds = composer_kinds(lib, seed, "deepen")
        assert kinds == composer_kinds(lib, seed, "deepen")
        counts["active" if "active" in kinds else kinds[0]] += 1
    assert 1250 <= counts["active"] <= 1550
    assert 300 <= counts["passive"] <= 500
    assert 120 <= counts["reaction"] <= 280
