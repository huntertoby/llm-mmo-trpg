"""SK-4 第 1 項：組合器的吸血配方（玩法交接 4.1.34 第 10 點；06 6.18 A）。

打擊、範圍骨架（``structure.lifesteal_skeletons``）的傷害以 ``structure.lifesteal_permille``
的機率附上 ``lifesteal_permille``（值 ``structure.lifesteal_amount_permille``）。用獨立亂數串流，
預算照吸血計價、旋鈕重調；許願池的「傷害＋治療」因此有組合器的候選。聖光雙效照舊只靠手寫。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.skillgen.helpers import lib
from trpg.content.library import load_library
from trpg.content.loader import bundled_content_dir
from trpg.content.skills import SkillDef
from trpg.shared.errors import ContentError
from trpg.skillgen.budget import skill_budget
from trpg.skillgen.random_composer import ComposeError, compose_random_skill
from trpg.skillgen.validate import validate_skill
from trpg.skillgen.wish_pick import skill_tag_ids


def _lifesteal(skill: SkillDef) -> list[int]:
    return [e.lifesteal_permille for e in skill.effects if e.lifesteal_permille is not None]


def _composed(skeleton: str, seeds: range) -> list[SkillDef]:
    library = lib()
    out: list[SkillDef] = []
    for seed in seeds:
        try:
            out.append(compose_random_skill(seed, skeleton=skeleton, library=library))
        except ComposeError:
            continue
    return out


def test_rules_are_initial_values_in_skill_composer() -> None:
    rules = lib().composer.structure
    assert rules.lifesteal_skeletons == ("strike", "area")
    assert 0 < rules.lifesteal_permille <= 1000
    assert 1 <= rules.lifesteal_amount_permille <= 500


@pytest.mark.parametrize("skeleton", ["strike", "area"])
def test_strike_and_area_damage_can_carry_lifesteal(skeleton: str) -> None:
    library = lib()
    amount = library.composer.structure.lifesteal_amount_permille
    found = [s for s in _composed(skeleton, range(200)) if _lifesteal(s)]
    assert found, f"{skeleton} 前 200 個種子沒有吸血"
    for skill in found:
        assert not validate_skill(skill, library)
        # 只附在一個對敵的傷害效果上，值照設定
        assert _lifesteal(skill) == [amount]
        damage = next(e for e in skill.effects if e.lifesteal_permille is not None)
        assert damage.type == "damage"
        assert damage.affects in (None, "enemies")
        assert not damage.split_heal
        # 預算照吸血計價
        report = skill_budget(skill, library)
        assert any("吸血" in e.note for e in report.effects)
        # 許願命中「傷害＋治療」
        tags = skill_tag_ids(library, skill)
        assert {"damage", "heal"} <= set(tags.effects)


@pytest.mark.parametrize("skeleton", ["control", "displace", "combo", "aura", "builder_finisher"])
def test_other_skeletons_never_get_lifesteal(skeleton: str) -> None:
    assert not any(_lifesteal(s) for s in _composed(skeleton, range(80)))


def test_unknown_lifesteal_skeleton_fails_to_load(tmp_path: Path) -> None:
    content = tmp_path / "content"
    shutil.copytree(bundled_content_dir(), content)
    path = content / "skill_composer.yaml"
    text = path.read_text(encoding="utf-8")
    line = "lifesteal_skeletons: [strike, area]"
    assert line in text
    path.write_text(text.replace(line, "lifesteal_skeletons: [strike, no_such_skeleton]"), "utf-8")
    with pytest.raises(ContentError, match="no_such_skeleton"):
        load_library(content)
