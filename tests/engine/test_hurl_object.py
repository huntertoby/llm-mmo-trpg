"""投擲物件 ``hurl_object``（Phase 3C-5a，``docs/phases/Phase3C計畫.md`` 7A.2）。

技能選兩個目標：射程內的一個 ``pushable`` 物件（``target_object_id``）與落點（``target_pos``）。
落點被命中的單位受 ``dice`` 物理傷害；物件落地後 ``explosive`` 爆炸、``breakable`` 碎掉、其他放在
落點或附近最近的空格，沒有空格就摧毀。
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.engine.helpers import (
    caster_template,
    give_turn,
    library,
    make_map,
    make_setup,
    make_skill,
    no_reactions,
    spawn,
)
from trpg.cli.battle import cmd_replay
from trpg.cli.main import main
from trpg.content.environment import ObjectDef, ObjectTable
from trpg.content.skills import SkillDef, SkillTable
from trpg.engine import BattleState, Interact, UseSkill, legal_actions, resolve, start_battle
from trpg.engine.events import (
    AttackRolled,
    DamageDealt,
    EventBase,
    ObjectDestroyed,
    ObjectExploded,
    ObjectHurled,
    StatusApplied,
)
from trpg.shared.errors import IllegalActionError
from trpg.shared.rng import Rng
from trpg.shared.types import ObjectId, Pos, Surface, Team, UnitId
from trpg.skillgen.budget import skill_budget

U1, U2, U3 = UnitId("unit_0001"), UnitId("unit_0002"), UnitId("unit_0003")
O1 = ObjectId("obj_0001")
ROW = "0000000"
FLAT = "\n".join([ROW] * 7)
HERO = (0, 3)
FOE = (3, 3)
TELEKINESIS = "skill_telekinetic_hurl"

HURL = make_skill(
    "skill_test_hurl",
    {"type": "object_then_tile", "range": 4},
    [{"type": "hurl_object", "range": 3, "dice": "2d6"}],
)
BOULDER = ObjectDef.model_validate(
    {"id": "boulder", "name_zh": "巨石", "glyph": "o", "tags": ["blocks_move", "pushable"]}
)
"""測試專用：可推動、不可破壞的物件（內容裡的可推動物件都可以破壞）。"""


def of[E: EventBase](events: Sequence[EventBase], kind: type[E]) -> list[E]:
    return [e for e in events if isinstance(e, kind)]


def always(monkeypatch: pytest.MonkeyPatch, die: int = 4) -> None:
    """d20 一律 19（命中、不暴擊）、其他骰子一律 ``die``。"""
    monkeypatch.setattr(Rng, "roll", lambda self, sides: 19 if sides == 20 else min(die, sides))


def arena(
    *,
    objects: Sequence[tuple[int, int, str]] = ((1, 3, "crate"),),
    foes: Sequence[tuple[int, int]] = (FOE,),
    allies: Sequence[tuple[int, int]] = (),
    terrain: str | None = None,
    skill: SkillDef | str = HURL,
) -> BattleState:
    """U1 法師（在 ``HERO``，裝備 ``skill``）；之後依序是 ``foes``（不反應、HP 200）與 ``allies``。
    規則集多一個測試專用的「巨石」（可推動、不可破壞）。"""
    m = make_map(FLAT, terrain, ally=[HERO, *allies], enemy=list(foes), objects=objects)
    spawns = [spawn(Team.ALLY, HERO, caster_template([skill]))]
    spawns += [spawn(Team.ENEMY, xy, no_reactions(max_hp=200)) for xy in foes]
    spawns += [spawn(Team.ALLY, xy, no_reactions(max_hp=200)) for xy in allies]
    extra = [skill] if isinstance(skill, SkillDef) and skill.id != HURL.id else []
    setup = make_setup(m, spawns, skills=[HURL, *extra])
    rs = setup.ruleset
    rs = rs.model_copy(update={"objects": ObjectTable(objects=(*rs.objects.objects, BOULDER))})
    rs.model_post_init(None)
    return give_turn(start_battle(setup.model_copy(update={"ruleset": rs}), 0), U1)


def hurl(target: tuple[int, int], obj: ObjectId = O1, skill: str = HURL.id) -> UseSkill:
    return UseSkill(
        unit_id=U1,
        skill_id=skill,
        target_object_id=obj,
        target_pos=Pos(x=target[0], y=target[1]),
    )


# ---------------------------------------------------------------------------
# 落點
# ---------------------------------------------------------------------------


def test_the_unit_at_the_landing_tile_is_hit_and_the_crate_shatters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(arena(), hurl(FOE))
    (roll,) = of(result.events, AttackRolled)
    assert (roll.target_id, roll.hit, roll.skill_id) == (U2, True, HURL.id)
    (dmg,) = [d for d in of(result.events, DamageDealt) if d.target_id == U2]
    assert (dmg.cause, dmg.element.value, dmg.rolls, dmg.source_id) == (
        "attack",
        "physical",
        (4, 4),
        U1,
    )
    (thrown,) = of(result.events, ObjectHurled)
    assert (thrown.outcome, thrown.from_pos, thrown.to_pos) == (
        "shattered",
        Pos(x=1, y=3),
        Pos(x=3, y=3),
    )
    (gone,) = of(result.events, ObjectDestroyed)
    assert (gone.cause, gone.pos) == ("hurled", Pos(x=3, y=3))
    state = result.state
    assert state.objects[O1].destroyed and state.object_at(1, 3) is None
    assert state.object_at(3, 3) is None
    # 事件順序：命中 → 傷害 → 物件落地
    kinds = [type(e) for e in result.events if isinstance(e, AttackRolled | ObjectHurled)]
    assert kinds == [AttackRolled, ObjectHurled]


def test_an_empty_landing_tile_has_no_roll_and_keeps_the_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    result = resolve(arena(objects=[(1, 3, "boulder")]), hurl((2, 1)))
    assert not of(result.events, AttackRolled)
    (thrown,) = of(result.events, ObjectHurled)
    assert (thrown.outcome, thrown.placed_pos) == ("placed", Pos(x=2, y=1))
    state = result.state
    assert state.object_at(1, 3) is None
    assert state.object_at(2, 1) is not None and state.object_at(2, 1).id == O1  # type: ignore[union-attr]
    assert not state.objects[O1].destroyed


FIRE_HURL = HURL.model_copy(update={"id": "skill_test_fire_hurl", "tags": ("fire", "spell")})
"""投擲技能帶火標籤（例：改造型「燃燒投擲」）。"""
OIL_CROSS = [(3, 3), (3, 2), (4, 3), (3, 4), (2, 3)]


def surfaces(state: BattleState, tiles: Sequence[tuple[int, int]]) -> list[str]:
    return [state.tile(*xy).surface.value for xy in tiles]


def test_a_hurled_oil_barrel_spills_oil_and_does_not_explode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3D-3（玩法 PM #4）：油桶摔破漏油（落點與上下左右 4 格變成油），不爆炸。"""
    always(monkeypatch)
    result = resolve(arena(objects=[(1, 3, "oil_barrel")], foes=[FOE, (4, 4)]), hurl(FOE))
    (thrown,) = of(result.events, ObjectHurled)
    assert thrown.outcome == "shattered"
    assert not of(result.events, ObjectExploded)
    assert not [d for d in of(result.events, DamageDealt) if d.cause == "explosion"]
    (gone,) = of(result.events, ObjectDestroyed)
    assert (gone.cause, gone.pos) == ("hurled", Pos(x=3, y=3))
    assert result.state.objects[O1].destroyed and result.state.object_at(1, 3) is None
    assert surfaces(result.state, OIL_CROSS) == ["oil"] * 5
    assert result.state.tile(4, 4).surface.value == "none"  # 斜角不會漏到
    # 落點的單位照樣被砸（物理傷害），旁邊（4, 4）的敵人沒事
    hurt = {d.target_id for d in of(result.events, DamageDealt)}
    assert hurt == {U2}


def test_a_hurled_oil_barrel_explodes_when_it_lands_on_fire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(objects=[(1, 3, "oil_barrel")], foes=[FOE, (4, 4)])
    state.set_tile(*FOE, replace(state.tile(*FOE), surface=Surface.FIRE, surface_remaining=2))
    result = resolve(state, hurl(FOE))
    (thrown,) = of(result.events, ObjectHurled)
    assert thrown.outcome == "exploded"
    (boom,) = of(result.events, ObjectExploded)
    assert (boom.pos, boom.source_id) == (Pos(x=3, y=3), U1)
    blasted = {d.target_id for d in of(result.events, DamageDealt) if d.cause == "explosion"}
    assert blasted == {U2, U3}  # 落點與斜角相鄰（3×3）的敵人
    (gone,) = of(result.events, ObjectDestroyed)
    assert gone.cause == "explosion" and result.state.objects[O1].destroyed
    assert result.state.object_at(1, 3) is None


def test_a_fire_element_hurl_makes_the_oil_barrel_explode(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    state = arena(objects=[(1, 3, "oil_barrel")], foes=[FOE, (4, 4)], skill=FIRE_HURL)
    result = resolve(state, hurl(FOE, skill=FIRE_HURL.id))
    (thrown,) = of(result.events, ObjectHurled)
    assert thrown.outcome == "exploded"
    blasted = {d.target_id for d in of(result.events, DamageDealt) if d.cause == "explosion"}
    assert blasted == {U2, U3}
    assert result.state.objects[O1].destroyed


def test_a_fire_damage_effect_in_the_skill_also_counts_as_fire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    burning = make_skill(
        "skill_test_burning_hurl",
        {"type": "object_then_tile", "range": 4},
        [
            {"type": "hurl_object", "range": 3, "dice": "2d6"},
            {"type": "damage", "dice": "1d6", "element": "fire"},
        ],
    )
    state = arena(objects=[(1, 3, "oil_barrel")], skill=burning)
    result = resolve(state, hurl(FOE, skill=burning.id))
    assert of(result.events, ObjectHurled)[0].outcome == "exploded"


def test_a_modifier_that_turns_damage_to_fire_makes_the_barrel_explode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    state = arena(objects=[(1, 3, "oil_barrel")], skill=HURL)
    state.units[U1].skills = (*state.units[U1].skills, "skill_test_fire_hand")
    hand = SkillDef.model_validate(
        {
            "id": "skill_test_fire_hand",
            "name_zh": "測試火手",
            "tier": 1,
            "rarity": "epic",
            "kind": "modifier",
            "skeleton": "modifier",
            "category": "spell",
            "weapon_req": "any",
            "scaling_attr": "int",
            "shape": {"type": "self"},
            "effects": [],
            "modifiers": [{"applies_to": {"all_skills": True}, "change": {"add_element": "fire"}}],
        }
    )
    rs = state.ruleset
    rs = rs.model_copy(update={"skills": SkillTable(skills=(*rs.skills.skills, hand))})
    rs.model_post_init(None)
    state.ruleset = rs
    result = resolve(state, hurl(FOE))
    assert of(result.events, ObjectHurled)[0].outcome == "exploded"


def test_a_crate_still_just_shatters_without_oil(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(arena(objects=[(1, 3, "crate")]), hurl(FOE))
    assert surfaces(result.state, OIL_CROSS) == ["none"] * 5


def test_an_occupied_landing_tile_puts_the_object_on_the_nearest_free_tile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    always(monkeypatch)
    # 距離 1 的候選依 (y, x)：(3, 2)、(2, 3)、(4, 3)、(3, 4)；(3, 2) 有巨石、(2, 3) 有隊友
    state = arena(objects=[(1, 3, "boulder"), (3, 2, "boulder")], foes=[FOE], allies=[(2, 3)])
    result = resolve(state, hurl(FOE))
    (thrown,) = of(result.events, ObjectHurled)
    assert (thrown.outcome, thrown.placed_pos) == ("placed", Pos(x=4, y=3))
    assert result.state.object_at(4, 3) is not None
    assert result.state.object_at(4, 3).id == O1  # type: ignore[union-attr]


def test_no_free_tile_nearby_destroys_the_object(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    crowd = [(3, 2), (2, 3), (4, 3), (3, 4)]
    state = arena(objects=[(1, 3, "boulder")], foes=[FOE, *crowd])
    result = resolve(state, hurl(FOE))
    (thrown,) = of(result.events, ObjectHurled)
    assert (thrown.outcome, thrown.placed_pos) == ("lost", None)
    (gone,) = of(result.events, ObjectDestroyed)
    assert (gone.cause, gone.pos) == ("hurled", Pos(x=3, y=3))
    assert result.state.objects[O1].destroyed and result.state.object_at(1, 3) is None


def test_landing_in_a_chasm_destroys_the_object(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    rows = ["......."] * 7
    rows[1] = "..x...."
    result = resolve(arena(objects=[(1, 3, "boulder")], terrain="\n".join(rows)), hurl((2, 1)))
    (thrown,) = of(result.events, ObjectHurled)
    assert thrown.outcome == "lost"
    (gone,) = of(result.events, ObjectDestroyed)
    assert gone.cause == "fell"


def test_a_knocked_down_target_with_the_demo_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    always(monkeypatch)
    result = resolve(arena(skill=TELEKINESIS), hurl(FOE, skill=TELEKINESIS))
    assert any(
        s.target_id == U2 and s.status_id == "prone" for s in of(result.events, StatusApplied)
    )
    assert [d.rolls for d in of(result.events, DamageDealt) if d.target_id == U2] == [(4, 4, 4)]


# ---------------------------------------------------------------------------
# 選取
# ---------------------------------------------------------------------------


def test_the_flight_is_not_blocked_but_the_landing_must_be_in_sight() -> None:
    # (1, 3) 是牆：木箱 (1, 1) 飛越它落到 (1, 5)（施放者看得到兩者）不受影響；
    # 但施放者看不到牆後的 (2, 3)，不能當落點
    rows = ["......."] * 7
    rows[3] = ".#....."
    state = arena(objects=[(1, 1, "crate")], terrain="\n".join(rows), foes=[(6, 6)])
    result = resolve(state, hurl((1, 5)))
    (thrown,) = of(result.events, ObjectHurled)
    assert thrown.to_pos == Pos(x=1, y=5)
    with pytest.raises(IllegalActionError, match="視線被阻擋"):
        resolve(state, hurl((2, 3)))


def test_hurl_selection_rejections() -> None:
    state = arena(objects=[(1, 3, "crate"), (5, 3, "crate"), (1, 1, "low_wall")], foes=[(6, 6)])
    with pytest.raises(IllegalActionError, match="超出投擲距離"):
        resolve(state, hurl((2, 3), obj=ObjectId("obj_0002")))  # 距離 5 > 3
    with pytest.raises(IllegalActionError, match="無法投擲"):
        resolve(state, hurl((2, 3), obj=ObjectId("obj_0003")))  # 矮牆不是 pushable
    with pytest.raises(IllegalActionError, match="落點不能是物件原本的格子"):
        resolve(state, hurl((1, 3)))
    with pytest.raises(IllegalActionError, match="目標超出射程"):
        resolve(state, hurl((5, 4)))  # 距施放者 6 > 4
    with pytest.raises(IllegalActionError, match="同時指定"):
        resolve(state, UseSkill(unit_id=U1, skill_id=HURL.id, target_object_id=O1))
    with pytest.raises(IllegalActionError, match="不能指定：direction"):
        resolve(state, hurl((2, 3)).model_copy(update={"direction": "east"}))


def test_legal_actions_list_object_and_landing_pairs() -> None:
    state = arena(objects=[(1, 3, "crate"), (5, 3, "crate")], foes=[(6, 6)])
    hurls = [a for a in legal_actions(state) if isinstance(a, UseSkill) and a.skill_id == HURL.id]
    assert hurls and {a.target_object_id for a in hurls} == {O1}  # 第二個木箱太遠
    assert all(a.target_pos is not None and a.target_pos != Pos(x=1, y=3) for a in hurls)
    assert hurl((3, 3)) in hurls


def test_basic_actions_cannot_hurl() -> None:
    state = arena(foes=[(6, 6)])
    with pytest.raises(ValidationError):
        Interact.model_validate({"unit_id": U1, "object_id": O1, "target_pos": {"x": 3, "y": 3}})
    others = [a for a in legal_actions(state) if not isinstance(a, UseSkill)]
    assert not any(getattr(a, "target_pos", None) is not None for a in others)
    # 其他技能也不能同時帶物件與落點
    bolt = make_skill(
        "skill_test_bolt",
        {"type": "single", "range": 5},
        [{"type": "damage", "dice": "1d6", "element": "fire"}],
    )
    m = make_map(FLAT, ally=[HERO], enemy=[(6, 6)], objects=[(1, 3, "crate")])
    setup = make_setup(
        m,
        [
            spawn(Team.ALLY, HERO, caster_template([bolt])),
            spawn(Team.ENEMY, (6, 6), no_reactions()),
        ],
        skills=[bolt],
    )
    plain = give_turn(start_battle(setup, 0), U1)
    with pytest.raises(IllegalActionError, match="不能指定"):
        resolve(plain, hurl((3, 3), skill=bolt.id))


# ---------------------------------------------------------------------------
# 資料、預算與重播
# ---------------------------------------------------------------------------


def test_hurl_object_and_its_shape_must_come_together() -> None:
    with pytest.raises(ValidationError, match="object_then_tile"):
        make_skill(
            "skill_test_bad1",
            {"type": "single", "range": 4},
            [{"type": "hurl_object", "range": 3, "dice": "2d6"}],
        )
    with pytest.raises(ValidationError, match="hurl_object"):
        make_skill(
            "skill_test_bad2",
            {"type": "object_then_tile", "range": 4},
            [{"type": "damage", "dice": "2d6", "element": "fire"}],
        )


def test_the_demo_skill_budget_discounts_the_dice_and_adds_the_knockdown() -> None:
    lib = library()
    report = skill_budget(lib.skills[TELEKINESIS], lib)
    (effect,) = report.effects
    # 3d6 平均 10.5 × 800‰ ＝ 8.4，擊倒 ＋3
    assert effect.points == pytest.approx(11.4)
    assert report.ok


def test_an_ai_battle_hurls_objects_and_replays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """build_telekinesis 在 narrow_halls 種子 11：AI 丟出物件（油桶摔破漏油），紀錄重播一致。"""
    log = tmp_path / "hurl.json"
    # 3-24a1：弓有拋射，AI 軌跡改變，種子 5 → 11
    argv = ["battle", "--map", "narrow_halls", "--seed", "11", "--ally-build", "build_telekinesis"]
    assert main([*argv, "--log-json", str(log)]) == 0
    out = capsys.readouterr().out
    assert "丟向" in out and "出現了油" in out
    assert '"object_hurled"' in log.read_text(encoding="utf-8")
    replayed = io.StringIO()
    assert cmd_replay(log, replayed) == 0
    assert "重播驗證通過" in replayed.getvalue()
