"""NW-2b 前端需要的兩個小補充：骰子／倍率階梯端點、單位表單的招式組選單資料。

讀專案內建 ``content/`` 的服務一律 ``git = None``（不可能寫回）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from trpg.api.app import create_app
from trpg.api.tuning.service import TuningService
from trpg.api.tuning.skills import GROUP_PRESETS, _matches
from trpg.content.skills import weapon_problem
from trpg.skillgen.composer_parts import dice_ladder


def test_ladders_route_matches_the_composer(read_service: TuningService) -> None:
    library = read_service._rules_library()
    app = create_app(tuning=True)
    app.state.tuning = read_service
    with TestClient(app) as client:
        body = client.get("/api/tuning/skills/ladders").json()
    assert body["dice"] == list(dice_ladder(library.composer.dice))
    assert body["multipliers"] == list(library.composer.multiplier_ladder())
    # 由弱到強：武器倍率遞增；骰子平均值不遞減
    assert body["multipliers"] == sorted(body["multipliers"])
    means = [int(c) * (int(s) + 1) for c, s in (d.split("d") for d in body["dice"])]
    assert means == sorted(means)


def test_unit_detail_lists_incompatible_moves(read_service: TuningService) -> None:
    library = read_service._rules_library()
    detail = read_service.object("unit", "ashen_heart")
    picker = detail.unit_skills
    assert picker is not None
    weapon = library.weapons[library.units["ashen_heart"].weapon]
    assert weapon.name_zh in picker.weapon_zh
    assert "主動" in picker.slots_zh
    # 和載入檢查同一個判定：每一招有原因 ⇔ weapon_problem 不是 None
    for skill_id, skill in sorted(library.skills.items()):
        if skill_id.startswith("skill_gear_"):
            assert skill_id not in picker.problems
            continue
        expected = weapon_problem(skill, weapon.weapon_class, {weapon.id: weapon.name_zh})
        assert (skill_id in picker.problems) == (expected is not None), skill_id
    # 灰燼之心是法器：遠程武器技一定不相容
    assert "skill_fire_arrow" in picker.problems
    # 自己裝的招一定相容
    for skill_id in library.units["ashen_heart"].skills:
        assert skill_id not in picker.problems
    # 技能對象沒有這個欄位
    assert read_service.object("skill", "skill_fire_arrow").unit_skills is None


def test_list_facets_agree_with_the_group_filter(read_service: TuningService) -> None:
    """清單的分類欄位（前端篩選用）和分組改的 ``_matches`` 對每個預設組選到同一批招。"""
    library = read_service._rules_library()
    summaries = read_service.objects("skill")
    for preset in GROUP_PRESETS:
        f = preset.filter
        by_facets = set()
        for o in summaries:
            facets = o.skill
            assert facets is not None
            ok = (
                (not f.tier or facets.tier in f.tier)
                and (not f.category or facets.category in f.category)
                and (not f.weapon_req or facets.weapon_req in f.weapon_req)
                and (not f.ap_cost or facets.ap_cost in f.ap_cost)
                and (not f.kind or facets.kind in f.kind)
                and (not f.shape or facets.shape in f.shape)
                and set(f.tags or ()) <= set(facets.tags)
                and (f.enemy_only is None or facets.enemy_only == f.enemy_only)
                and (f.has_condition is None or facets.has_condition == f.has_condition)
                and (f.ranged is None or facets.ranged == f.ranged)
                and (f.single_damage is None or facets.single_damage == f.single_damage)
            )
            if ok:
                by_facets.add(o.id)
        by_rule = {o.id for o in summaries if _matches(library.skills[o.id], f)}
        assert by_facets == by_rule, preset.key
        assert by_rule, preset.key
