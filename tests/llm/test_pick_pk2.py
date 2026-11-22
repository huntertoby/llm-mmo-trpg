"""PK-2：打分的「這招有沒有料」、挑選模式加嚴的名稱與描述檢查（高處、地形、墜落、打擊、形狀、單字
元素）。"""

from __future__ import annotations

from functools import cache
from typing import Any

from trpg.content.effect_words import load_effect_words
from trpg.content.library import ContentLibrary, load_library
from trpg.content.skills import SkillDef
from trpg.llm.consistency import check_added, check_mentions, skill_facts, strict_facts
from trpg.llm.naming import NamingText, check_consistency
from trpg.skillgen.pick_player import PickPlayer
from trpg.skillgen.skill_pick import (
    THIN_CONDITIONAL,
    THIN_FEW,
    THIN_HOLLOW,
    PickCandidate,
    design_key,
    is_nondamage,
    score_candidate,
    thin_reasons,
)


@cache
def _lib() -> ContentLibrary:
    return load_library()


def _skill(**changes: Any) -> SkillDef:
    data = _lib().skills["skill_hex_bolt"].model_dump(mode="json")
    data.update(changes)
    return SkillDef.model_validate(data)


DAMAGE = {"type": "damage", "dice": "1d8", "element": "shadow"}
MARK = {"type": "apply_status", "status": "marked", "duration": 3}
PUSH = {"type": "push", "distance": 2}
HIGH = {"type": "height_advantage"}


def test_thin_reasons_cases() -> None:
    few = _lib().skill_pick.weights.thin_epic_min_effects  # HC-5b：拿掉程式預設 2
    assert few == 2
    assert thin_reasons(_skill(effects=[MARK]), epic_min_effects=few) == (
        THIN_HOLLOW,
    )  # Q16：只有標記
    assert thin_reasons(
        _skill(effects=[{"type": "reveal", "radius": 2}]), epic_min_effects=few
    ) == (THIN_HOLLOW,)
    assert thin_reasons(_skill(effects=[DAMAGE, MARK]), epic_min_effects=few) == ()
    # Q8：只有條件式的推開
    assert thin_reasons(_skill(effects=[{**PUSH, "condition": HIGH}]), epic_min_effects=few) == (
        THIN_CONDITIONAL,
    )
    assert thin_reasons(_skill(effects=[PUSH], condition=HIGH), epic_min_effects=few) == (
        THIN_CONDITIONAL,
    )
    assert thin_reasons(_skill(effects=[PUSH]), epic_min_effects=few) == ()
    # 條件式的傷害不算單薄（利用者白板）
    assert thin_reasons(_skill(effects=[{**DAMAGE, "condition": HIGH}]), epic_min_effects=few) == ()
    # Q12：史詩只有一個有作用的效果（標記不算）
    epic = _skill(rarity="epic", effects=[MARK])
    assert thin_reasons(epic, epic_min_effects=few) == (THIN_HOLLOW, THIN_FEW)
    assert thin_reasons(_skill(rarity="epic", effects=[DAMAGE, MARK]), epic_min_effects=few) == (
        THIN_FEW,
    )
    assert thin_reasons(_skill(rarity="epic", effects=[DAMAGE, PUSH]), epic_min_effects=few) == ()
    assert thin_reasons(_skill(rarity="epic", effects=[DAMAGE]), epic_min_effects=1) == ()


def test_thin_penalty_in_score_and_workshop_weight() -> None:
    lib = _lib()
    weights = lib.skill_pick.weights
    thin = _skill(effects=[MARK])
    full = _skill(effects=[DAMAGE, MARK])
    player = PickPlayer()

    def score(skill: SkillDef, w: Any = weights) -> dict[str, int]:
        cand = PickCandidate(skill, "composer", 1, design_key(skill))
        return dict(score_candidate(lib, cand, player, w, keywords=()).parts)

    assert score(thin)["thin"] == -weights.thin_penalty
    assert score(full)["thin"] == 0
    zero = weights.model_copy(update={"thin_penalty": 0})
    assert score(thin, zero)["thin"] == 0


def test_is_nondamage() -> None:
    assert is_nondamage(_skill(effects=[MARK]))
    assert is_nondamage(_skill(effects=[PUSH]))
    assert not is_nondamage(_skill(effects=[DAMAGE]))
    assert not is_nondamage(_skill(effects=[PUSH, {**DAMAGE, "condition": HIGH}]))


def test_strict_groups_only_in_pick_mode() -> None:
    """加嚴詞組只有 ``strict=True`` 才看：閃現、自由設計的命名照舊；閃現加上的效果也不要求提到。"""
    lib = _lib()
    words = load_effect_words()
    plain = _skill(effects=[DAMAGE])
    facts = skill_facts(lib, plain)
    assert check_mentions("name_zh", "高處墜落之擊", facts, words) == []
    found = check_mentions("name_zh", "高處墜落之擊", strict_facts(lib, plain), words, strict=True)
    assert [e.code for e in found] == ["name_zh.effect_mismatch"]
    assert "高處" in found[0].message and "墜落" in found[0].message
    added = frozenset({"shape:cone", "condition:height_advantage"})
    assert check_added(["沒提到"], added, words, code="x") == []


def test_x2_style_name_is_caught() -> None:
    """PK-1b 的 X2：反應技「被攻擊命中時，居高臨下時拉近 1 格＋沉默」。高處有對應（條件），
    「墜落」「之擊」沒有（沒有墜落類效果、沒有傷害），挑選模式要擋下。"""
    lib = _lib()
    words = load_effect_words()
    x2 = _skill(
        effects=[{"type": "pull", "distance": 1}, {**MARK, "status": "silenced", "duration": 2}],
        condition=HIGH,
    )
    facts = strict_facts(lib, x2)
    assert "condition:height_advantage" in facts
    text = NamingText(name_zh="高處墜落之擊", concept="站在高處拉近敵人。", cast_flavor="拉近。")
    errors = check_consistency(text, facts, words, strict=True)
    assert [e.code for e in errors] == ["name_zh.effect_mismatch"]
    assert "墜落" in errors[0].message and "之擊" in errors[0].message
    assert "高處" not in errors[0].message
    ok = NamingText(name_zh="居高鎖喉", concept="站在高處拉近敵人。", cast_flavor="拉近。")
    assert check_consistency(ok, facts, words, strict=True) == []


def test_strict_shape_and_element_words() -> None:
    lib = _lib()
    words = load_effect_words()
    single = _skill(effects=[DAMAGE])
    facts = strict_facts(lib, single)
    assert "shape:single" in facts
    assert check_mentions("concept", "扇形掃過前方。", facts, words, strict=True)
    assert check_mentions("concept", "一道風捲起。", facts, words, strict=True)  # 風：元素不對
    assert check_mentions("concept", "風格獨特。", facts, words, strict=True) == []  # ignore
    assert check_mentions("concept", "暗影纏身。", facts, words, strict=True) == []
